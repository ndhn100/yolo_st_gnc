"""PyTorch Dataset cho các cửa sổ khung xương + tăng cường dữ liệu khi train."""
import numpy as np
import torch
from torch.utils.data import Dataset

from skeleton_utils import FLIP_PAIRS


class SkeletonWindowDataset(Dataset):
    """X: (N, C=3, T, V=17) đã chuẩn hóa; y: (N,).

    Augmentation (chỉ khi train):
    - Lật ngang: đổi dấu x + hoán đổi các khớp trái/phải.
    - Xoay nhẹ ±10° và co giãn ±10% trong mặt phẳng ảnh.
    - Nhiễu Gauss nhỏ trên tọa độ.

    Ghi chú thực nghiệm (2026-07-14): đã thử thêm 3 augmentation chống học tủ
    tư thế tĩnh (đóng băng cửa sổ thành mẫu âm, hoán đổi góc nhìn trước/sau,
    bóp bề ngang) — tất cả đều làm GIẢM F1 té ngã trên test (0.75 → 0.67-0.71)
    vì mô hình mất bớt recall. Giải pháp hiệu quả nằm ở tiền xử lý
    (skeleton_utils.normalize_window: điền khớp bị che bằng khớp đối xứng).
    """

    def __init__(self, X, y, augment=False):
        self.X = torch.from_numpy(X.astype(np.float32))
        self.y = torch.from_numpy(y.astype(np.int64))
        self.augment = augment

    def __len__(self):
        return len(self.y)

    def _augment(self, x):
        # x: (C, T, V) — clone để không sửa dữ liệu gốc
        x = x.clone()

        if torch.rand(1).item() < 0.5:  # lật ngang
            x[0] = -x[0]
            for a, b in FLIP_PAIRS:
                x[:, :, [a, b]] = x[:, :, [b, a]]

        angle = (torch.rand(1).item() - 0.5) * (20 * np.pi / 180)  # ±10°
        scale = 1.0 + (torch.rand(1).item() - 0.5) * 0.2           # ±10%
        cos_a, sin_a = np.cos(angle) * scale, np.sin(angle) * scale
        px, py = x[0].clone(), x[1].clone()
        x[0] = cos_a * px - sin_a * py
        x[1] = sin_a * px + cos_a * py

        x[:2] += torch.randn_like(x[:2]) * 0.02  # nhiễu nhỏ
        return x

    def __getitem__(self, idx):
        x = self.X[idx]
        if self.augment:
            x = self._augment(x)
        return x, self.y[idx]
