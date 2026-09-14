



import argparse
import collections
import threading
import time
import zipfile
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import torch
from ultralytics import YOLO

from config import (ALERTS_DIR, CHECKPOINT_DIR, NUM_CLASSES, RT_ALERT_SECONDS,
                    RT_CONSECUTIVE, RT_FALL_THRESHOLD, RT_PRED_STRIDE,
                    WINDOW_SIZE, YOLO_CONF, YOLO_POSE_WEIGHTS)
from graph import COCO_EDGES
from skeleton_utils import (interpolate_missing, normalize_window,
                            select_person, window_to_tensor_layout)
from stgcn import STGCN


def frame_generator(source):
    if str(source).lower().endswith(".zip"):
        with zipfile.ZipFile(source) as zf:
            names = sorted(n for n in zf.namelist() if n.lower().endswith(".png"))
            for n in names:
                buf = np.frombuffer(zf.read(n), dtype=np.uint8)
                img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
                if img is not None:
                    yield img
                time.sleep(1 / 18)
    else:
        cap = cv2.VideoCapture(int(source) if str(source).isdigit() else source)
        if not cap.isOpened():
            raise SystemExit(f"Không mở được nguồn video: {source}")
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                yield frame
        finally:
            cap.release()


def beep_async():
    def _beep():
        try:
            import winsound
            winsound.Beep(1200, 600)
        except Exception:
            pass
    threading.Thread(target=_beep, daemon=True).start()


def draw_skeleton(frame, kpts, conf_th=0.3):
    for a, b in COCO_EDGES:
        if kpts[a, 2] >= conf_th and kpts[b, 2] >= conf_th:
            pa = tuple(kpts[a, :2].astype(int))
            pb = tuple(kpts[b, :2].astype(int))
            cv2.line(frame, pa, pb, (0, 255, 120), 2)
    for j in range(17):
        if kpts[j, 2] >= conf_th:
            cv2.circle(frame, tuple(kpts[j, :2].astype(int)), 3, (0, 140, 255), -1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="0", help="0=webcam | video | zip UP-Fall")
    parser.add_argument("--checkpoint", default=str(CHECKPOINT_DIR / "best.pt"))
    parser.add_argument("--threshold", type=float, default=RT_FALL_THRESHOLD)
    args = parser.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    pose_model = YOLO(YOLO_POSE_WEIGHTS)
    stgcn = STGCN(num_classes=NUM_CLASSES).to(device)
    ckpt = torch.load(args.checkpoint, map_location=device, weights_only=True)
    stgcn.load_state_dict(ckpt["model"])
    stgcn.eval()
    print(f"Đã nạp ST-GCN ({args.checkpoint}), thiết bị: {device}")

    ALERTS_DIR.mkdir(parents=True, exist_ok=True)

    buffer = collections.deque(maxlen=WINDOW_SIZE)
    fall_prob = 0.0
    consecutive = 0
    alert_until = 0.0
    frame_id = 0
    t_fps = time.time()
    fps = 0.0
    prev_center = None

    for frame in frame_generator(args.source):
        frame_id += 1

        results = pose_model(frame, conf=YOLO_CONF, device=device, verbose=False)
        h_img, w_img = frame.shape[:2]
        kpts, prev_center = select_person(results[0], prev_center,
                                          float(np.hypot(w_img, h_img)))
        buffer.append(kpts)
        draw_skeleton(frame, kpts)

        if len(buffer) == WINDOW_SIZE and frame_id % RT_PRED_STRIDE == 0:
            window = np.stack(buffer)
            if (window[:, :, 2] > 0.3).any():
                norm = normalize_window(interpolate_missing(window))
                x = torch.from_numpy(window_to_tensor_layout(norm)).unsqueeze(0).to(device)
                with torch.no_grad():
                    fall_prob = torch.softmax(stgcn(x), dim=1)[0, 1].item()
                consecutive = consecutive + 1 if fall_prob >= args.threshold else 0
                if consecutive >= RT_CONSECUTIVE and time.time() > alert_until:
                    alert_until = time.time() + RT_ALERT_SECONDS
                    beep_async()
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    out = ALERTS_DIR / f"fall_{ts}.jpg"
                    cv2.imwrite(str(out), frame)
                    print(f"[CẢNH BÁO] Phát hiện té ngã! p={fall_prob:.2f} → {out}")

        h, w = frame.shape[:2]
        bar_w = int(200 * fall_prob)
        color = (0, 0, 255) if fall_prob >= args.threshold else (0, 200, 0)
        cv2.rectangle(frame, (10, 10), (210, 30), (60, 60, 60), -1)
        cv2.rectangle(frame, (10, 10), (10 + bar_w, 30), color, -1)
        cv2.putText(frame, f"P(te nga)={fall_prob:.2f}", (220, 27),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        if frame_id % 10 == 0:
            now = time.time()
            fps = 10 / max(now - t_fps, 1e-6)
            t_fps = now
        cv2.putText(frame, f"FPS: {fps:.1f}", (10, h - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

        if time.time() < alert_until:
            cv2.rectangle(frame, (0, 0), (w, 60), (0, 0, 255), -1)
            cv2.putText(frame, "!!! PHAT HIEN TE NGA !!!", (w // 2 - 190, 42),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 3)

        cv2.imshow("Fall Detection - YOLO-Pose + ST-GCN (Q de thoat)", frame)
        if cv2.waitKey(1) & 0xFF in (ord("q"), ord("Q")):
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
