

from __future__ import annotations

from collections import deque
import math
from pathlib import Path
import time
from typing import Callable

import cv2
import numpy as np
import torch
from ultralytics import YOLO

from config import (
    CHECKPOINT_DIR,
    KPT_CONF_TH,
    NUM_CLASSES,
    PROJECT_ROOT,
    RT_CONSECUTIVE,
    RT_FALL_THRESHOLD,
    RT_PRED_STRIDE,
    WINDOW_MIN_VALID,
    WINDOW_SIZE,
    YOLO_CONF,
)

from graph import COCO_EDGES
from skeleton_utils import (
    interpolate_missing,
    normalize_window,
    select_person,
    valid_frame_mask,
    window_to_tensor_layout,
)
from stgcn import STGCN


TARGET_FPS = 18.0
MAX_DURATION_SECONDS = 600
MAX_DECODED_FRAMES = 180_000
MAX_FRAME_PIXELS = 16_777_216
MAX_EVIDENCE_IMAGES = 3
MAX_TRACK_GAP_SECONDS = 0.5
MIN_NEGATIVE_COVERAGE = 0.8


def _valid_pose(keypoints: np.ndarray) -> bool:
    if keypoints.shape != (17, 3) or not np.isfinite(keypoints).all():
        return False

    visible = keypoints[:, 2] >= KPT_CONF_TH

    return bool(
        visible.sum() >= 5
        and visible[[5, 6, 11, 12]].sum() >= 2
    )


def _interpolate_pose(
    left: np.ndarray,
    right: np.ndarray,
    alpha: float,
) -> np.ndarray:

    if alpha <= 1e-7:
        return left.copy()

    if alpha >= 1 - 1e-7:
        return right.copy()

    pose = left.copy()

    pose[:, :2] = (
        left[:, :2] * (1 - alpha)
        + right[:, :2] * alpha
    )

    pose[:, 2] = np.minimum(
        left[:, 2],
        right[:, 2],
    )

    pose[
        pose[:, 2] < KPT_CONF_TH,
        :2
    ] = 0

    return pose


class VideoAnalyzer:

    def __init__(
        self,
        checkpoint: Path | None = None,
    ):
        self.checkpoint = Path(
            checkpoint or CHECKPOINT_DIR / "best.pt"
        ).resolve()

        self.pose_weights = (
            PROJECT_ROOT / "yolov8n-pose.pt"
        )

        if not self.checkpoint.is_file():
            raise FileNotFoundError(
                "Không tìm thấy checkpoint ST-GCN: "
                + str(self.checkpoint)
            )

        if not self.pose_weights.is_file():
            raise FileNotFoundError(
                "Không tìm thấy trọng số YOLO cục bộ: "
                "yolov8n-pose.pt"
            )

        self.device = (
            "cuda"
            if torch.cuda.is_available()
            else "cpu"
        )

        saved = torch.load(
            self.checkpoint,
            map_location=self.device,
            weights_only=True,
        )

        self.stgcn = STGCN(
            num_classes=NUM_CLASSES
        ).to(self.device)

        self.stgcn.load_state_dict(
            saved["model"]
        )

        self.stgcn.eval()

        self.pose_model = YOLO(
            str(self.pose_weights)
        )

        self.epoch = (
            int(saved["epoch"])
            if "epoch" in saved
            else None
        )

        self.val_f1 = (
            float(saved["val_f1"])
            if "val_f1" in saved
            else None
        )

    def metadata(self) -> dict:
        try:
            checkpoint_name = (
                self.checkpoint
                .relative_to(PROJECT_ROOT)
                .as_posix()
            )
        except ValueError:
            checkpoint_name = (
                self.checkpoint.name
            )

        return {
            "name": "YOLO-Pose + ST-GCN",

            "checkpoint": checkpoint_name,

            "epoch": self.epoch,

            "val_f1": self.val_f1,

            "validation_f1": self.val_f1,

            "selection_metric":
                "F1 lớp té ngã trên tập validation; "
                "hòa F1 chọn loss thấp hơn",

            "pose_model":
                self.pose_weights.name,

            "device":
                self.device,

            "window_size":
                WINDOW_SIZE,

            "stride":
                RT_PRED_STRIDE,

            "target_fps":
                TARGET_FPS,

            "threshold":
                RT_FALL_THRESHOLD,

            "decision_rule":
                f"{RT_CONSECUTIVE}_consecutive_windows",

            "consecutive_windows":
                RT_CONSECUTIVE,

            "single_person":
                True,

            "scope":
                "Theo dõi một người chính trong mỗi cảnh; "
                "chưa kết luận cho mọi người trong video.",

            "probability_note":
                "Điểm đầu ra của mô hình, "
                "không phải độ chính xác bảo đảm.",
        }

    def _predict(
        self,
        window: np.ndarray,
    ) -> float:

        normalized = normalize_window(
            interpolate_missing(window),
            fill="mirror",
        )

        tensor = torch.from_numpy(
            window_to_tensor_layout(
                normalized
            )
        ).unsqueeze(0)

        with torch.inference_mode():
            score = torch.softmax(
                self.stgcn(
                    tensor.to(self.device)
                ),
                dim=1,
            )[0, 1].item()

        if not math.isfinite(score):
            raise RuntimeError(
                "Mô hình trả về điểm không hợp lệ. "
                "Vui lòng thử video khác."
            )

        return float(score)

    @staticmethod
    def _write_evidence(
        path: Path,
        frame: np.ndarray,
        pose: np.ndarray,
        timestamp: float,
        probability: float,
    ) -> None:

        picture = frame.copy()

        for a, b in COCO_EDGES:

            if (
                pose[a, 2] >= KPT_CONF_TH
                and pose[b, 2] >= KPT_CONF_TH
            ):

                cv2.line(
                    picture,
                    tuple(
                        pose[a, :2].astype(int)
                    ),
                    tuple(
                        pose[b, :2].astype(int)
                    ),
                    (100, 235, 130),
                    2,
                )

        for x, y, confidence in pose:

            if confidence >= KPT_CONF_TH:

                cv2.circle(
                    picture,
                    (
                        int(x),
                        int(y),
                    ),
                    3,
                    (30, 210, 255),
                    -1,
                )

        cv2.rectangle(
            picture,
            (0, 0),
            (
                picture.shape[1],
                34,
            ),
            (35, 35, 55),
            -1,
        )

        cv2.putText(
            picture,
            (
                f"FALL | "
                f"{timestamp:.2f}s | "
                f"score {probability:.3f}"
            ),
            (10, 23),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.58,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

        success, encoded = cv2.imencode(
            ".jpg",
            picture,
            [
                cv2.IMWRITE_JPEG_QUALITY,
                86,
            ],
        )

        if not success:
            raise RuntimeError(
                "Không thể tạo ảnh bằng chứng."
            )

        encoded.tofile(
            str(path)
        )

    def analyze(
        self,
        video_path: Path,
        output_dir: Path,
        progress: Callable[[dict], None] | None = None,
    ) -> dict:

        start_clock = time.monotonic()

        video_path = Path(
            video_path
        )

        output_dir = Path(
            output_dir
        )

        if not video_path.is_file():
            raise ValueError(
                "Không tìm thấy video đã tải lên."
            )

        capture = cv2.VideoCapture(
            str(video_path)
        )

        if not capture.isOpened():

            capture.release()

            raise ValueError(
                "Không đọc được video. "
                "Hãy thử tệp MP4, MOV, AVI "
                "hoặc WebM hợp lệ."
            )

        source_fps = float(
            capture.get(
                cv2.CAP_PROP_FPS
            )
        )

        total_frames = int(
            max(
                0,
                capture.get(
                    cv2.CAP_PROP_FRAME_COUNT
                ),
            )
        )

        width = capture.get(
            cv2.CAP_PROP_FRAME_WIDTH
        )

        height = capture.get(
            cv2.CAP_PROP_FRAME_HEIGHT
        )

        if (
            not math.isfinite(source_fps)
            or source_fps <= 0
            or source_fps > 1000
        ):

            capture.release()

            raise ValueError(
                "Video không có tốc độ khung hình "
                "hợp lệ để phân tích chuyển động."
            )

        estimated_duration = (
            total_frames
            / source_fps
        )

        if (
            estimated_duration
            > MAX_DURATION_SECONDS
            + 1 / source_fps
        ):

            capture.release()

            raise ValueError(
                f"Video dài quá "
                f"{MAX_DURATION_SECONDS // 60} phút. "
                "Hãy cắt ngắn video."
            )

        if (
            width * height
            > MAX_FRAME_PIXELS
        ):

            capture.release()

            raise ValueError(
                "Độ phân giải video quá lớn. "
                "Hãy giảm xuống 4K hoặc thấp hơn."
            )

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        buffer: deque = deque(
            maxlen=WINDOW_SIZE
        )

        times: deque = deque(
            maxlen=WINDOW_SIZE
        )

        timeline: list[dict] = []

        events: list[dict] = []

        frames_analyzed = 0
        valid_frames = 0
        decoded_frames = 0
        segment_frames = 0

        skipped_windows = 0
        multi_person_frames = 0
        track_resets = 0
        windows_analyzed = 0

        longest_missing = 0
        missing_count = 0

        previous_center = None

        previous_pose = None
        previous_pose_time = None

        previous_timestamp = -1.0

        timestamp_origin = 0.0

        last_valid_time = None

        next_pose_time = 0.0
        next_sample_time = 0.0

        active_event = None

        consecutive = 0

        last_progress_clock = 0.0

        max_probability = None

        source_interval = (
            1.0 / source_fps
        )

        def report(
            fraction: float,
            stage: str,
        ):
            if progress is not None:

                progress({
                    "progress": round(
                        100
                        * max(
                            0.0,
                            min(
                                1.0,
                                fraction,
                            ),
                        ),
                        2,
                    ),

                    "stage":
                        stage,

                    "frames_analyzed":
                        frames_analyzed,
                })

        def reset_sequence():

            nonlocal segment_frames
            nonlocal active_event
            nonlocal consecutive
            nonlocal previous_pose
            nonlocal previous_pose_time

            buffer.clear()

            times.clear()

            segment_frames = 0

            active_event = None

            consecutive = 0

            previous_pose = None

            previous_pose_time = None

        def consume(
            pose: np.ndarray,
            timestamp: float,
            frame: np.ndarray,
            evidence_pose: np.ndarray,
            evidence_time: float,
        ):

            nonlocal frames_analyzed
            nonlocal valid_frames
            nonlocal segment_frames

            nonlocal skipped_windows
            nonlocal windows_analyzed

            nonlocal missing_count
            nonlocal longest_missing

            nonlocal max_probability
            nonlocal active_event

            nonlocal consecutive

            frames_analyzed += 1

            segment_frames += 1

            is_valid = _valid_pose(
                pose
            )

            valid_frames += int(
                is_valid
            )

            missing_count = (
                0
                if is_valid
                else missing_count + 1
            )

            longest_missing = max(
                longest_missing,
                missing_count,
            )

            buffer.append(
                pose
                if is_valid
                else np.zeros(
                    (17, 3),
                    np.float32,
                )
            )

            times.append(
                timestamp
            )

            if (
                len(buffer)
                < WINDOW_SIZE
            ):
                return

            if (
                (
                    segment_frames
                    - WINDOW_SIZE
                )
                % RT_PRED_STRIDE
            ):
                return

            window = np.stack(
                buffer
            )

            if (
                valid_frame_mask(
                    window
                ).mean()
                < WINDOW_MIN_VALID
            ):

                skipped_windows += 1

                timeline.append({
                    "time_seconds":
                        round(
                            timestamp,
                            4,
                        ),

                    "probability":
                        None,
                })

                consecutive = 0
                active_event = None

                return

            probability = self._predict(
                window
            )

            windows_analyzed += 1

            max_probability = (
                probability
                if max_probability is None
                else max(
                    max_probability,
                    probability,
                )
            )

            timeline.append({
                "time_seconds":
                    round(
                        timestamp,
                        4,
                    ),

                "probability":
                    round(
                        probability,
                        6,
                    ),
            })


            if (
                probability
                >= RT_FALL_THRESHOLD
            ):

                consecutive += 1

            else:

                consecutive = 0

                active_event = None

                return

            if (
                consecutive
                < RT_CONSECUTIVE
            ):
                return


            window_start = float(
                times[0]
            )

            if active_event is None:

                if (
                    events
                    and window_start
                    <= (
                        events[-1][
                            "end_seconds"
                        ]
                        + 0.25
                    )
                ):

                    active_event = (
                        events[-1]
                    )

                else:

                    active_event = {
                        "start_seconds":
                            round(
                                window_start,
                                4,
                            ),

                        "end_seconds":
                            round(
                                timestamp,
                                4,
                            ),

                        "peak_probability":
                            0.0,
                    }

                    if (
                        len(events)
                        < MAX_EVIDENCE_IMAGES
                    ):

                        active_event[
                            "evidence_file"
                        ] = (
                            f"fall_"
                            f"{len(events) + 1:02d}"
                            f".jpg"
                        )

                    events.append(
                        active_event
                    )

            active_event[
                "end_seconds"
            ] = round(
                timestamp,
                4,
            )

            if (
                probability
                > active_event[
                    "peak_probability"
                ]
            ):

                active_event[
                    "peak_probability"
                ] = round(
                    probability,
                    6,
                )

                active_event[
                    "peak_seconds"
                ] = round(
                    evidence_time,
                    4,
                )

                if (
                    "evidence_file"
                    in active_event
                ):

                    self._write_evidence(
                        output_dir
                        / active_event[
                            "evidence_file"
                        ],

                        frame,

                        evidence_pose,

                        evidence_time,

                        probability,
                    )

        report(
            0.01,
            "Đang đọc video và nhận diện khung xương",
        )

        try:

            while True:

                ok, frame = (
                    capture.read()
                )

                if not ok:
                    break

                frame_index = (
                    decoded_frames
                )

                decoded_frames += 1

                if (
                    decoded_frames
                    > MAX_DECODED_FRAMES
                ):

                    raise ValueError(
                        "Video có quá nhiều khung hình. "
                        "Hãy giảm thời lượng hoặc FPS."
                    )

                if (
                    frame.shape[0]
                    * frame.shape[1]
                    > MAX_FRAME_PIXELS
                ):

                    raise ValueError(
                        "Độ phân giải video quá lớn. "
                        "Hãy giảm xuống 4K hoặc thấp hơn."
                    )

                pts = float(
                    capture.get(
                        cv2.CAP_PROP_POS_MSEC
                    )
                ) / 1000.0

                fallback = (
                    frame_index
                    / source_fps
                )

                if (
                    frame_index == 0
                    and math.isfinite(pts)
                    and pts >= 0
                ):

                    timestamp_origin = (
                        pts
                    )

                if (
                    math.isfinite(pts)
                    and pts >= timestamp_origin
                ):

                    timestamp = (
                        pts
                        - timestamp_origin
                    )

                else:

                    timestamp = (
                        fallback
                    )

                if (
                    timestamp
                    <= previous_timestamp
                ):

                    timestamp = max(
                        fallback,
                        previous_timestamp
                        + source_interval,
                    )

                if (
                    timestamp
                    > MAX_DURATION_SECONDS
                ):

                    raise ValueError(
                        f"Video dài quá "
                        f"{MAX_DURATION_SECONDS // 60} phút. "
                        "Hãy cắt ngắn video."
                    )

                previous_timestamp = (
                    timestamp
                )

                if (
                    timestamp + 1e-7
                    < next_pose_time
                ):

                    continue

                next_pose_time = (
                    math.floor(
                        timestamp
                        * TARGET_FPS
                        + 1e-7
                    )
                    + 1
                ) / TARGET_FPS

                if (
                    max(
                        frame.shape[:2]
                    )
                    > 1280
                ):

                    scale = (
                        1280.0
                        / max(
                            frame.shape[:2]
                        )
                    )

                    frame = cv2.resize(
                        frame,
                        None,
                        fx=scale,
                        fy=scale,
                        interpolation=cv2.INTER_AREA,
                    )

                result = self.pose_model(
                    frame,
                    conf=YOLO_CONF,
                    device=self.device,
                    verbose=False,
                )[0]

                if (
                    result.boxes is not None
                    and len(
                        result.boxes
                    ) > 1
                ):

                    multi_person_frames += 1

                diag = float(
                    np.hypot(
                        frame.shape[1],
                        frame.shape[0],
                    )
                )

                if (
                    result.keypoints is None
                    or result.boxes is None
                    or not len(
                        result.boxes
                    )
                ):

                    pose = np.zeros(
                        (17, 3),
                        np.float32,
                    )

                    center = (
                        previous_center
                    )

                else:

                    pose, center = (
                        select_person(
                            result,
                            previous_center,
                            diag,
                        )
                    )

                is_valid = _valid_pose(
                    pose
                )

                if not is_valid:

                    pose = np.zeros(
                        (17, 3),
                        np.float32,
                    )

                switched = (
                    is_valid
                    and previous_center is not None
                    and center is not None
                    and np.linalg.norm(
                        center
                        - previous_center
                    )
                    >= 0.15 * diag
                )

                long_gap = (
                    last_valid_time is not None
                    and timestamp
                    - last_valid_time
                    > MAX_TRACK_GAP_SECONDS
                )

                if (
                    switched
                    or (
                        is_valid
                        and long_gap
                    )
                ):

                    reset_sequence()

                    track_resets += 1

                    timeline.append({
                        "time_seconds":
                            round(
                                timestamp,
                                4,
                            ),

                        "probability":
                            None,
                    })

                    next_sample_time = (
                        math.ceil(
                            timestamp
                            * TARGET_FPS
                            - 1e-7
                        )
                        / TARGET_FPS
                    )

                if is_valid:

                    previous_center = (
                        center
                    )

                    last_valid_time = (
                        timestamp
                    )

                elif long_gap:

                    previous_center = (
                        None
                    )

                if previous_pose is None:

                    if (
                        abs(
                            timestamp
                            - next_sample_time
                        )
                        < 1e-6
                    ):

                        consume(
                            pose,
                            next_sample_time,
                            frame,
                            pose,
                            timestamp,
                        )

                        next_sample_time += (
                            1 / TARGET_FPS
                        )

                else:

                    gap = (
                        timestamp
                        - previous_pose_time
                    )

                    while (
                        next_sample_time
                        <= timestamp + 1e-7
                    ):

                        if (
                            gap
                            > MAX_TRACK_GAP_SECONDS
                        ):

                            sampled = np.zeros(
                                (17, 3),
                                np.float32,
                            )

                        else:

                            alpha = min(
                                1.0,
                                max(
                                    0.0,
                                    (
                                        next_sample_time
                                        - previous_pose_time
                                    )
                                    / gap,
                                ),
                            )

                            sampled = (
                                _interpolate_pose(
                                    previous_pose,
                                    pose,
                                    alpha,
                                )
                            )

                        consume(
                            sampled,
                            next_sample_time,
                            frame,
                            pose,
                            timestamp,
                        )

                        next_sample_time += (
                            1 / TARGET_FPS
                        )

                previous_pose = (
                    pose
                )

                previous_pose_time = (
                    timestamp
                )

                now = (
                    time.monotonic()
                )

                if (
                    now
                    - last_progress_clock
                    >= 0.4
                ):

                    if estimated_duration:

                        fraction = (
                            timestamp
                            / estimated_duration
                        )

                    else:

                        fraction = (
                            decoded_frames
                            / (
                                decoded_frames
                                + 250
                            )
                        )

                    report(
                        0.02
                        + 0.96
                        * min(
                            1.0,
                            fraction,
                        ),

                        "Đang phân tích chuyển động",
                    )

                    last_progress_clock = (
                        now
                    )

        finally:

            capture.release()

        if decoded_frames == 0:

            raise ValueError(
                "Video không có khung hình đọc được "
                "hoặc định dạng không được hỗ trợ."
            )

        duration = max(
            0.0,
            previous_timestamp
            + source_interval,
        )

        truncated = (
            total_frames > 0
            and decoded_frames
            < (
                total_frames
                - max(
                    2,
                    int(
                        source_fps * 0.1
                    ),
                )
            )
        )

        valid_ratio = (
            valid_frames
            / max(
                frames_analyzed,
                1,
            )
        )

        warnings = [
            self.metadata()[
                "scope"
            ]
        ]

        if (
            source_fps
            < TARGET_FPS - 0.5
        ):

            warnings.append(
                "Video FPS thấp: tọa độ khung xương "
                "được nội suy về 18 FPS; "
                "chuyển động nhanh có thể thiếu chi tiết."
            )

        if multi_person_frames:

            warnings.append(
                "Có nhiều người trong một số khung hình; "
                "kết quả chỉ áp dụng cho người chính "
                "được theo dõi."
            )

        if truncated:

            warnings.append(
                "Không đọc được toàn bộ khung hình của video; "
                "phần còn lại chưa được phân tích."
            )

        if track_resets:

            warnings.append(
                "Đã bắt đầu lại chuỗi khi mất dấu hoặc đổi người "
                "để tránh nối nhầm chuyển động."
            )

        if (
            valid_ratio
            < MIN_NEGATIVE_COVERAGE
            or (
                longest_missing
                / TARGET_FPS
                > MAX_TRACK_GAP_SECONDS
            )
        ):

            warnings.append(
                "Một phần video không nhìn rõ đủ khớp cơ thể "
                "để kết luận."
            )

        if events:

            status = "fall"

            label = (
                "Phát hiện té ngã"
            )

            summary = (
                f"Phát hiện {len(events)} khoảng "
                f"có dấu hiệu té ngã sau khi điểm "
                f"vượt ngưỡng "
                f"{RT_FALL_THRESHOLD * 100:g}/100 "
                f"liên tiếp ít nhất "
                f"{RT_CONSECUTIVE} lần."
            )

        elif (
            frames_analyzed
            < WINDOW_SIZE
        ):

            status = (
                "inconclusive"
            )

            label = (
                "Chưa đủ dữ liệu để kết luận"
            )

            summary = (
                "Video quá ngắn hoặc chuỗi theo dõi quá ngắn. "
                "Cần đủ dữ liệu chuyển động để tạo "
                f"cửa sổ {WINDOW_SIZE} khung hình."
            )

        elif (
            windows_analyzed == 0
            or valid_ratio
            < MIN_NEGATIVE_COVERAGE
            or skipped_windows
            or truncated
            or track_resets
            or source_fps < 6
            or (
                longest_missing
                / TARGET_FPS
                > MAX_TRACK_GAP_SECONDS
            )
        ):

            status = (
                "inconclusive"
            )

            label = (
                "Chưa đủ dữ liệu để kết luận"
            )

            summary = (
                "Không có cảnh té ngã được xác nhận, "
                "nhưng dữ liệu chuyển động chưa đủ rõ "
                "hoặc đầy đủ để kết luận không té ngã."
            )

        else:

            status = (
                "no_fall"
            )

            label = (
                "Không phát hiện té ngã"
            )

            summary = (
                "Không phát hiện chuỗi chuyển động "
                "đạt tiêu chí té ngã ở người được theo dõi."
            )

        result = {

            "status":
                status,

            "label":
                label,

            "summary":
                summary,

            "max_probability":
                (
                    round(
                        max_probability,
                        6,
                    )
                    if max_probability
                    is not None
                    else None
                ),

            "threshold":
                RT_FALL_THRESHOLD,

            "consecutive_required":
                RT_CONSECUTIVE,

            "events":
                events,

            "timeline":
                timeline,

            "stats": {

                "duration_seconds":
                    round(
                        duration,
                        4,
                    ),

                "source_fps":
                    round(
                        source_fps,
                        4,
                    ),

                "sampled_fps":
                    TARGET_FPS,

                "frames_analyzed":
                    frames_analyzed,

                "valid_frames":
                    valid_frames,

                "windows_analyzed":
                    windows_analyzed,

                "processing_seconds":
                    round(
                        time.monotonic()
                        - start_clock,
                        3,
                    ),

                "valid_ratio":
                    round(
                        valid_ratio,
                        4,
                    ),

                "skipped_windows":
                    skipped_windows,

                "multi_person_frames":
                    multi_person_frames,

                "track_resets":
                    track_resets,
            },

            "model":
                self.metadata(),

            "warnings":
                warnings,
        }

        report(
            1.0,
            "Phân tích hoàn tất",
        )

        return result
