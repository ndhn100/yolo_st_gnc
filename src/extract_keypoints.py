"""Bước 1: Trích xuất khung xương bằng YOLO-Pose từ các file zip UP-Fall.

Đọc trực tiếp khung hình PNG từ trong zip (không cần giải nén ra đĩa),
chạy YOLO-Pose theo batch trên GPU, chọn người có confidence cao nhất
(UP-Fall chỉ có 1 người/khung hình), lưu kết quả mỗi trial thành 1 file npz:

    data/keypoints/Subject{S}Activity{A}Trial{T}.npz
        kpts   : (T, 17, 3) float32 — x, y (pixel), confidence
        fps    : float — ước lượng từ timestamp trong tên file ảnh
        width, height, subject, activity, trial

Chạy:  python src/extract_keypoints.py [--raw-dir ...] [--limit N]
"""
import argparse
import re
import zipfile
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import torch
from tqdm import tqdm
from ultralytics import YOLO

from config import (KEYPOINTS_DIR, RAW_DATA_DIR, YOLO_BATCH, YOLO_CONF,
                    YOLO_POSE_WEIGHTS)
from skeleton_utils import select_person

ZIP_RE = re.compile(r"Subject(\d+)Activity(\d+)Trial(\d+)Camera(\d+)\.zip$", re.I)
TS_RE = re.compile(r"(\d{4}-\d{2}-\d{2})T(\d{2})_(\d{2})_(\d{2}(?:\.\d+)?)")


def parse_timestamp(name):
    """'2018-07-04T12_04_17.738369.png' → giây (float) hoặc None."""
    m = TS_RE.search(name)
    if not m:
        return None
    date_str, hh, mm, ss = m.groups()
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.timestamp() + int(hh) * 3600 + int(mm) * 60 + float(ss)


def estimate_fps(names):
    ts = [parse_timestamp(n) for n in names]
    ts = [t for t in ts if t is not None]
    if len(ts) < 2:
        return 18.0  # mặc định của UP-Fall
    dts = np.diff(sorted(ts))
    dts = dts[(dts > 1e-4) & (dts < 1.0)]
    return float(1.0 / np.median(dts)) if len(dts) else 18.0


def process_zip(zip_path, model, device):
    with zipfile.ZipFile(zip_path) as zf:
        names = sorted(n for n in zf.namelist() if n.lower().endswith(".png"))
        if not names:
            return None
        fps = estimate_fps(names)

        all_kpts = []
        width = height = 0
        prev_center = None
        for i in range(0, len(names), YOLO_BATCH):
            batch_names = names[i:i + YOLO_BATCH]
            frames = []
            for n in batch_names:
                buf = np.frombuffer(zf.read(n), dtype=np.uint8)
                img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
                if img is None:  # ảnh hỏng → khung đen cùng kích thước
                    img = np.zeros((height or 480, width or 640, 3), np.uint8)
                height, width = img.shape[:2]
                frames.append(img)

            img_diag = float(np.hypot(width, height))
            results = model(frames, conf=YOLO_CONF, device=device, verbose=False)
            for r in results:
                kpts, prev_center = select_person(r, prev_center, img_diag)
                all_kpts.append(kpts)

    return {
        "kpts": np.stack(all_kpts),
        "fps": fps,
        "width": width,
        "height": height,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, default=RAW_DATA_DIR)
    parser.add_argument("--limit", type=int, default=0, help="chỉ xử lý N zip đầu (debug)")
    args = parser.parse_args()

    KEYPOINTS_DIR.mkdir(parents=True, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Thiết bị: {device}")
    model = YOLO(YOLO_POSE_WEIGHTS)

    zips = sorted(p for p in args.raw_dir.iterdir() if ZIP_RE.search(p.name))
    if args.limit:
        zips = zips[:args.limit]
    print(f"Tìm thấy {len(zips)} file zip trong {args.raw_dir}")

    skipped, done = 0, 0
    for zp in tqdm(zips, desc="Trích xuất keypoints"):
        m = ZIP_RE.search(zp.name)
        subject, activity, trial, camera = map(int, m.groups())
        out_path = KEYPOINTS_DIR / f"Subject{subject}Activity{activity}Trial{trial}.npz"
        if out_path.exists():
            skipped += 1
            continue

        data = process_zip(zp, model, device)
        if data is None:
            tqdm.write(f"[BỎ QUA] {zp.name}: không có ảnh PNG")
            continue

        np.savez_compressed(
            out_path,
            kpts=data["kpts"], fps=data["fps"],
            width=data["width"], height=data["height"],
            subject=subject, activity=activity, trial=trial,
        )
        done += 1

    print(f"Hoàn tất: {done} trial mới, {skipped} trial đã có sẵn (bỏ qua).")
    print(f"Kết quả lưu tại: {KEYPOINTS_DIR}")


if __name__ == "__main__":
    main()
