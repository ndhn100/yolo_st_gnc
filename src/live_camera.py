
from collections import deque
import sys
import threading
import time

import cv2
import numpy as np

from config import (
    KPT_CONF_TH,
    RT_CONSECUTIVE,
    RT_FALL_THRESHOLD,
    RT_PRED_STRIDE,
    WINDOW_MIN_VALID,
    WINDOW_SIZE,
    YOLO_CONF,
)

from graph import COCO_EDGES
from skeleton_utils import select_person, valid_frame_mask
from video_inference import (
    TARGET_FPS,
    MAX_TRACK_GAP_SECONDS,
    _interpolate_pose,
    _valid_pose,
)


class LiveFallDetector:

    def __init__(self, analyzer):
        self.analyzer = analyzer

        self.buffer = deque(maxlen=WINDOW_SIZE)

        self.center = None
        self.previous_pose = None
        self.previous_time = None

        self.next_sample = None
        self.next_pose = 0.0

        self.last_valid = None

        self.segment_frames = 0
        self.frames = 0

        self.probability = None

        self.consecutive = 0

        self.alert_until = 0.0
        self.alert_id = 0

        self.pose = np.zeros(
            (17, 3),
            np.float32,
        )

        self.latest = self._state(
            "warming_up",
            "Đang thu thập chuyển động…",
        )

    def _state(self, status, label):
        return {
            "status": status,
            "label": label,
            "probability": self.probability,
            "threshold": RT_FALL_THRESHOLD,

            "consecutive": self.consecutive,
            "consecutive_required": RT_CONSECUTIVE,

            "buffer_frames": len(self.buffer),
            "window_size": WINDOW_SIZE,
            "frames_analyzed": self.frames,
            "alert_id": self.alert_id,
        }

    def _reset(self):

        self.buffer.clear()

        self.previous_pose = None
        self.previous_time = None
        self.next_sample = None

        self.segment_frames = 0

        self.probability = None

        self.consecutive = 0

    def process(self, frame, timestamp):

        if timestamp < self.next_pose:
            return dict(self.latest)

        self.next_pose = (
            timestamp
            + 0.8 / TARGET_FPS
        )

        if (
            self.previous_time is not None
            and timestamp - self.previous_time
            > MAX_TRACK_GAP_SECONDS
        ):
            self._reset()
            self.center = None

        result = self.analyzer.pose_model(
            frame,
            conf=YOLO_CONF,
            device=self.analyzer.device,
            verbose=False,
        )[0]

        diagonal = float(
            np.hypot(
                frame.shape[1],
                frame.shape[0],
            )
        )

        if (
            result.keypoints is None
            or result.boxes is None
            or not len(result.boxes)
        ):
            pose = np.zeros(
                (17, 3),
                np.float32,
            )

            center = self.center

        else:
            pose, center = select_person(
                result,
                self.center,
                diagonal,
            )

        valid = _valid_pose(pose)

        switched = (
            valid
            and self.center is not None
            and center is not None
            and np.linalg.norm(
                center - self.center
            )
            >= 0.15 * diagonal
        )

        returning = (
            valid
            and self.last_valid is not None
            and timestamp - self.last_valid
            > MAX_TRACK_GAP_SECONDS
        )

        if switched or returning:
            self._reset()

        if valid:
            self.center = center
            self.last_valid = timestamp

        else:
            pose = np.zeros(
                (17, 3),
                np.float32,
            )

            if (
                self.last_valid is not None
                and timestamp - self.last_valid
                > MAX_TRACK_GAP_SECONDS
            ):
                self._reset()
                self.center = None

        self.pose = pose

        if self.next_sample is None:
            self.next_sample = timestamp

        while (
            self.next_sample
            <= timestamp + 1e-7
        ):

            if self.previous_pose is None:
                sampled = pose.copy()

            else:
                alpha = (
                    self.next_sample
                    - self.previous_time
                ) / max(
                    timestamp
                    - self.previous_time,
                    1e-6,
                )

                sampled = _interpolate_pose(
                    self.previous_pose,
                    pose,
                    min(
                        1,
                        max(
                            0,
                            alpha,
                        ),
                    ),
                )

            self.buffer.append(sampled)

            self.frames += 1
            self.segment_frames += 1

            if (
                len(self.buffer) == WINDOW_SIZE
                and (
                    self.segment_frames
                    - WINDOW_SIZE
                )
                % RT_PRED_STRIDE
                == 0
            ):

                window = np.stack(
                    self.buffer
                )

                if (
                    valid
                    and valid_frame_mask(
                        window
                    ).mean()
                    >= WINDOW_MIN_VALID
                ):

                    self.probability = (
                        self.analyzer._predict(
                            window
                        )
                    )


                    if (
                        self.probability
                        >= RT_FALL_THRESHOLD
                    ):
                        self.consecutive += 1

                    else:
                        self.consecutive = 0

                    if (
                        self.consecutive
                        >= RT_CONSECUTIVE
                    ):

                        if (
                            timestamp
                            >= self.alert_until
                        ):
                            self.alert_id += 1

                        self.alert_until = (
                            timestamp + 3.0
                        )

                else:
                    self.probability = None

                    self.consecutive = 0

            self.next_sample += (
                1 / TARGET_FPS
            )

        self.previous_pose = pose
        self.previous_time = timestamp

        if timestamp < self.alert_until:

            self.latest = self._state(
                "fall",
                "PHÁT HIỆN TÉ NGÃ!",
            )

        elif not valid:

            self.probability = None

            self.latest = self._state(
                "no_person",
                "Chưa thấy rõ người trong camera",
            )

        elif self.probability is None:

            self.latest = self._state(
                "warming_up",
                "Đang thu thập chuyển động…",
            )

        else:

            self.latest = self._state(
                "no_fall",
                "Không phát hiện té ngã",
            )

        return dict(
            self.latest
        )

    def draw(self, frame):

        picture = frame.copy()

        for a, b in COCO_EDGES:

            if (
                self.pose[a, 2]
                >= KPT_CONF_TH
                and self.pose[b, 2]
                >= KPT_CONF_TH
            ):

                cv2.line(
                    picture,
                    tuple(
                        self.pose[
                            a,
                            :2,
                        ].astype(int)
                    ),
                    tuple(
                        self.pose[
                            b,
                            :2,
                        ].astype(int)
                    ),
                    (80, 230, 130),
                    2,
                )

        for x, y, confidence in self.pose:

            if (
                confidence
                >= KPT_CONF_TH
            ):

                cv2.circle(
                    picture,
                    (
                        int(x),
                        int(y),
                    ),
                    3,
                    (0, 190, 255),
                    -1,
                )

        return picture


class CameraMonitor:

    def __init__(
        self,
        analyzer,
        capture_factory=None,
    ):
        self.analyzer = analyzer

        self.capture_factory = (
            capture_factory
            or self._open_capture
        )

        self.condition = threading.Condition(
            threading.RLock()
        )

        self.stop_event = (
            threading.Event()
        )

        self.thread = None

        self.jpeg = None

        self.sequence = 0

        self.last_seen = 0.0

        self.state = {
            "running": False,
            "status": "stopped",
            "label": "Camera đang tắt",
            "alert_id": 0,
        }

    @staticmethod
    def _open_capture():

        capture = cv2.VideoCapture(
            0,
            (
                cv2.CAP_DSHOW
                if sys.platform == "win32"
                else cv2.CAP_ANY
            ),
        )

        if not capture.isOpened():
            capture.release()

            capture = (
                cv2.VideoCapture(0)
            )

        capture.set(
            cv2.CAP_PROP_FRAME_WIDTH,
            640,
        )

        capture.set(
            cv2.CAP_PROP_FRAME_HEIGHT,
            480,
        )

        capture.set(
            cv2.CAP_PROP_FPS,
            30,
        )

        return capture

    def is_running(self):

        with self.condition:
            return bool(
                self.thread
                and self.thread.is_alive()
            )

    def snapshot(self, touch=True):

        with self.condition:

            if touch:
                self.last_seen = (
                    time.monotonic()
                )

            return dict(
                self.state
            )

    def start(self):

        with self.condition:

            self.last_seen = (
                time.monotonic()
            )

            if self.is_running():
                return dict(
                    self.state
                )

            self.stop_event.clear()

            self.jpeg = None

            self.state = {
                "running": True,
                "status": "starting",
                "label": "Đang mở camera…",
                "alert_id": 0,
            }

            self.thread = (
                threading.Thread(
                    target=self._run,
                    name="live-camera",
                    daemon=True,
                )
            )

            self.thread.start()

            return dict(
                self.state
            )

    def stop(self):

        with self.condition:

            self.stop_event.set()

            thread = self.thread

            if (
                thread
                and thread.is_alive()
            ):

                self.state.update(
                    status="stopping",
                    label="Đang tắt camera…",
                )

            self.condition.notify_all()

        if (
            thread
            and thread
            is not threading.current_thread()
        ):

            thread.join(
                timeout=3
            )

        return self.snapshot(
            touch=False
        )

    def _run(self):

        capture = None
        error = None

        try:
            capture = (
                self.capture_factory()
            )

            if not capture.isOpened():

                raise ValueError(
                    "Không mở được camera. "
                    "Kiểm tra camera có đang được ứng dụng khác "
                    "sử dụng hoặc bị chặn quyền truy cập không."
                )

            detector = LiveFallDetector(
                self.analyzer
            )

            t0 = time.monotonic()

            frame_count = 0

            while (
                not self.stop_event.is_set()
            ):

                if (
                    time.monotonic()
                    - self.last_seen
                    > 15
                ):
                    break

                ok, frame = (
                    capture.read()
                )

                if not ok:

                    raise ValueError(
                        "Mất kết nối với camera. "
                        "Hãy kiểm tra thiết bị rồi bật lại camera."
                    )

                if (
                    max(
                        frame.shape[:2]
                    )
                    > 960
                ):

                    ratio = (
                        960
                        / max(
                            frame.shape[:2]
                        )
                    )

                    frame = cv2.resize(
                        frame,
                        None,
                        fx=ratio,
                        fy=ratio,
                    )

                now = (
                    time.monotonic()
                )

                state = detector.process(
                    frame,
                    now,
                )

                picture = detector.draw(
                    frame
                )

                ok, encoded = cv2.imencode(
                    ".jpg",
                    picture,
                    [
                        cv2.IMWRITE_JPEG_QUALITY,
                        78,
                    ],
                )

                if not ok:
                    continue

                frame_count += 1

                with self.condition:

                    self.jpeg = (
                        encoded.tobytes()
                    )

                    self.sequence += 1

                    fps = round(
                        frame_count
                        / max(
                            now - t0,
                            0.001,
                        ),
                        1,
                    )

                    self.state = {
                        **state,
                        "running": True,
                        "fps": fps,
                    }

                    self.condition.notify_all()

        except ValueError as exc:

            error = str(exc)

        except Exception:

            import logging

            logging.getLogger(
                __name__
            ).exception(
                "Live camera failed"
            )

            error = (
                "Camera gặp lỗi khi phân tích. "
                "Hãy tắt và bật lại camera."
            )

        finally:

            if capture is not None:
                capture.release()

            with self.condition:

                self.jpeg = None

                self.state = {
                    "running": False,
                    "status": (
                        "error"
                        if error
                        else "stopped"
                    ),
                    "label": (
                        error
                        or "Camera đang tắt"
                    ),
                    "error": error,
                    "alert_id": 0,
                }

                self.condition.notify_all()

    def stream(self):

        seen = -1

        while True:

            with self.condition:

                self.condition.wait_for(
                    lambda:
                        self.sequence != seen
                        or not self.state[
                            "running"
                        ],
                    timeout=2,
                )

                if not self.state[
                    "running"
                ]:
                    return

                if (
                    not self.jpeg
                    or self.sequence == seen
                ):
                    seen = self.sequence
                    continue

                seen = self.sequence

                jpeg = self.jpeg

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n"
                b"\r\n"
                + jpeg
                + b"\r\n"
            )