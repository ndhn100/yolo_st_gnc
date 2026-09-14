


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
            data[split]["X"].append(window_to_tensor_layout(norm))
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
