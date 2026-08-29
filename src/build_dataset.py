"""Bước 2: Từ keypoints từng trial → dataset cửa sổ trượt đã chuẩn hóa.

Chiến lược tạo mẫu:
- Trial KHÔNG té ngã (Activity 6-11): cửa sổ trượt đều T=32, stride=16 → nhãn 0.
- Trial TÉ NGÃ (Activity 1-5):
    * Định vị thời điểm ngã = khung hình có vận tốc rơi của hông lớn nhất.
    * Lấy các cửa sổ có tâm quanh thời điểm ngã (jitter ±8 khung) → nhãn 1.
    * Phần ĐẦU trial (trước khi ngã) là đi/đứng bình thường → cắt cửa sổ
      trượt kết thúc trước thời điểm ngã làm mẫu nhãn 0 (hard negative).

Mỗi cửa sổ được chuẩn hóa (tịnh tiến theo tâm hông khung giữa, chia độ dài
thân) rồi lưu, chia THEO SUBJECT. Xuất ra HAI file chỉ khác cách điền khớp
bị che suốt cửa sổ:
- data/dataset.npz     (mirror-fill)  → dùng cho evaluate.py + demo.
- data/dataset_goc.npz (ghim về gốc)  → dùng cho train.py. Train trên bản
  ghim-gốc rồi suy luận trên mirror-fill là cấu hình tốt nhất đã kiểm chứng
  (test F1 té ngã 0,876); train thẳng trên mirror-fill → F1 tụt còn ~0,74.

Chạy:  python src/build_dataset.py
"""
import re
from collections import Counter
from pathlib import Path

import numpy as np

from config import (ADL_STRIDE, DATASET_FILE, DATASET_GOC_FILE,
                    FALL_ACTIVITIES, FALL_JITTER, IN_CHANNELS, KEYPOINTS_DIR,
                    MIN_VALID_RATIO, TEST_SUBJECTS, TRAIN_SUBJECTS,
                    VAL_SUBJECTS, WINDOW_MIN_VALID, WINDOW_SIZE)
from skeleton_utils import (interpolate_missing, locate_fall_center,
                            normalize_window, valid_frame_mask,
                            window_to_tensor_layout)

NPZ_RE = re.compile(r"Subject(\d+)Activity(\d+)Trial(\d+)\.npz$")


def windows_from_trial(kpts, activity, valid_mask):
    """Trả về list (window_raw, label) từ 1 trial.

    valid_mask (T,): khung hình có phát hiện được người hay không (trước nội
    suy). Cửa sổ có quá nhiều khung hình mất người (vd người nằm sàn quá lâu,
    YOLO không phát hiện được) sẽ bị bỏ vì dữ liệu nội suy không còn tin cậy.
    """
    T = kpts.shape[0]
    W = WINDOW_SIZE
    if T < W:
        return []

    def window_ok(start):
        return valid_mask[start:start + W].mean() >= WINDOW_MIN_VALID

    samples = []
    if activity in FALL_ACTIVITIES:
        fall_c = locate_fall_center(kpts)
        for jit in FALL_JITTER:
            start = int(np.clip(fall_c + jit - W // 2, 0, T - W))
            if window_ok(start):
                samples.append((kpts[start:start + W], 1))
        # Cửa sổ "trước khi ngã" làm mẫu âm (đi/đứng bình thường)
        fall_onset = fall_c - W // 2
        for start in range(0, T - W + 1, ADL_STRIDE):
            if start + W <= fall_onset - 5 and window_ok(start):
                samples.append((kpts[start:start + W], 0))
    else:
        for start in range(0, T - W + 1, ADL_STRIDE):
            if window_ok(start):
                samples.append((kpts[start:start + W], 0))
    return samples


def main():
    files = sorted(KEYPOINTS_DIR.glob("*.npz"))
    if not files:
        raise SystemExit(f"Chưa có keypoints trong {KEYPOINTS_DIR} — chạy "
                         "src/extract_keypoints.py trước.")

    splits = {"train": TRAIN_SUBJECTS, "val": VAL_SUBJECTS, "test": TEST_SUBJECTS}
    data = {name: {"X": [], "X_goc": [], "y": [], "subject": [], "activity": [],
                   "trial": []}
            for name in splits}
    dropped = []

    for f in files:
        m = NPZ_RE.search(f.name)
        if not m:
            continue
        subject, activity, trial = map(int, m.groups())
        split = next((name for name, subs in splits.items() if subject in subs), None)
        if split is None:
            continue

        npz = np.load(f)
        kpts = npz["kpts"].astype(np.float32)

        valid_mask = valid_frame_mask(kpts)
        if valid_mask.mean() < MIN_VALID_RATIO:
            dropped.append((f.name, valid_mask.mean()))
            continue

        kpts = interpolate_missing(kpts)

        for window, label in windows_from_trial(kpts, activity, valid_mask):
            norm = normalize_window(window, fill="mirror")
            norm_goc = normalize_window(window, fill="origin")
            data[split]["X"].append(window_to_tensor_layout(norm))  # (C,T,V)
            data[split]["X_goc"].append(window_to_tensor_layout(norm_goc))
            data[split]["y"].append(label)
            data[split]["subject"].append(subject)
            data[split]["activity"].append(activity)
            data[split]["trial"].append(trial)

    out, out_goc = {}, {}
    print(f"{'Split':<8}{'Cửa sổ':>8}{'Té ngã':>8}{'Không té':>10}  Subjects")
    for name, subs in splits.items():
        empty = np.zeros((0, IN_CHANNELS, WINDOW_SIZE, 17), np.float32)
        y = np.array(data[name]["y"], dtype=np.int64)
        out[f"X_{name}"] = np.stack(data[name]["X"]) if data[name]["X"] else empty
        out_goc[f"X_{name}"] = np.stack(data[name]["X_goc"]) if data[name]["X_goc"] else empty
        for key, dtype_arr in (("y", data[name]["y"]),
                               ("subject", data[name]["subject"]),
                               ("activity", data[name]["activity"]),
                               ("trial", data[name]["trial"])):
            arr = np.array(dtype_arr, dtype=np.int64)
            out[f"{key}_{name}"] = arr
            out_goc[f"{key}_{name}"] = arr
        c = Counter(y.tolist())
        print(f"{name:<8}{len(y):>8}{c.get(1, 0):>8}{c.get(0, 0):>10}  {subs}")

    if dropped:
        print(f"\nBỏ {len(dropped)} trial có tỉ lệ phát hiện người < {MIN_VALID_RATIO:.0%}:")
        for name, r in dropped:
            print(f"  - {name} ({r:.0%})")

    DATASET_FILE.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(DATASET_FILE, window_size=WINDOW_SIZE, **out)
    print(f"\nĐã lưu dataset mirror-fill (evaluate/demo): {DATASET_FILE}")
    np.savez_compressed(DATASET_GOC_FILE, window_size=WINDOW_SIZE, **out_goc)
    print(f"Đã lưu dataset ghim-gốc (train):             {DATASET_GOC_FILE}")


if __name__ == "__main__":
    main()
