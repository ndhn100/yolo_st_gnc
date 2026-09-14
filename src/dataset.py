import numpy as np
import torch
from torch.utils.data import Dataset

from skeleton_utils import FLIP_PAIRS


class SkeletonWindowDataset(Dataset):



    def __init__(self, X, y, augment=False):
        self.X = torch.from_numpy(X.astype(np.float32))
        self.y = torch.from_numpy(y.astype(np.int64))
        self.augment = augment

    def __len__(self):
        return len(self.y)

    def _augment(self, x):
        x = x.clone()

        if torch.rand(1).item() < 0.5:
            x[0] = -x[0]
            for a, b in FLIP_PAIRS:
                x[:, :, [a, b]] = x[:, :, [b, a]]

        angle = (torch.rand(1).item() - 0.5) * (20 * np.pi / 180)
        scale = 1.0 + (torch.rand(1).item() - 0.5) * 0.2
        cos_a, sin_a = np.cos(angle) * scale, np.sin(angle) * scale
        px, py = x[0].clone(), x[1].clone()
        x[0] = cos_a * px - sin_a * py
        x[1] = sin_a * px + cos_a * py

        x[:2] += torch.randn_like(x[:2]) * 0.02
        return x

    def __getitem__(self, idx):
        x = self.X[idx]
        if self.augment:
            x = self._augment(x)
        return x, self.y[idx]
