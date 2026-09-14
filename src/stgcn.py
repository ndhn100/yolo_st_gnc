

import torch
import torch.nn as nn

from config import DROPOUT, IN_CHANNELS, NUM_CLASSES
from graph import Graph


class SpatialGraphConv(nn.Module):

    def __init__(self, in_channels, out_channels, kernel_size):
        super().__init__()
        self.kernel_size = kernel_size
        self.conv = nn.Conv2d(in_channels, out_channels * kernel_size, kernel_size=1)

    def forward(self, x, A):
        x = self.conv(x)
        n, kc, t, v = x.size()
        x = x.view(n, self.kernel_size, kc // self.kernel_size, t, v)
        x = torch.einsum("nkctv,kvw->nctw", x, A)
        return x.contiguous()


class STGCNBlock(nn.Module):

    def __init__(self, in_channels, out_channels, A_size, temporal_kernel=9,
                 stride=1, dropout=0.5, residual=True):
        super().__init__()
        padding = (temporal_kernel - 1) // 2

        self.gcn = SpatialGraphConv(in_channels, out_channels, A_size[0])
        self.tcn = nn.Sequential(
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels,
                      kernel_size=(temporal_kernel, 1),
                      stride=(stride, 1),
                      padding=(padding, 0)),
            nn.BatchNorm2d(out_channels),
            nn.Dropout(dropout, inplace=True),
        )

        if not residual:
            self.residual = None
        elif in_channels == out_channels and stride == 1:
            self.residual = nn.Identity()
        else:
            self.residual = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=1, stride=(stride, 1)),
                nn.BatchNorm2d(out_channels),
            )
        self.relu = nn.ReLU(inplace=True)

        self.edge_importance = nn.Parameter(torch.ones(A_size))

    def forward(self, x, A):
        res = 0 if self.residual is None else self.residual(x)
        x = self.gcn(x, A * self.edge_importance)
        x = self.tcn(x) + res
        return self.relu(x)


class STGCN(nn.Module):
    def __init__(self, num_classes=NUM_CLASSES, in_channels=IN_CHANNELS,
                 dropout=DROPOUT):
        super().__init__()
        graph = Graph()
        A = torch.tensor(graph.A, dtype=torch.float32)
        self.register_buffer("A", A)
        self.num_joints = graph.num_nodes

        self.data_bn = nn.BatchNorm1d(in_channels * self.num_joints)

        cfg = [
            (in_channels, 64, 1),
            (64, 64, 1),
            (64, 64, 1),
            (64, 128, 2),
            (128, 128, 1),
            (128, 256, 2),
            (256, 256, 1),
        ]
        self.blocks = nn.ModuleList([
            STGCNBlock(c_in, c_out, A.size(), stride=s, dropout=dropout,
                       residual=(i != 0))
            for i, (c_in, c_out, s) in enumerate(cfg)
        ])

        self.head = nn.Linear(256, num_classes)

    def forward(self, x):
        n, c, t, v = x.size()
        x = x.permute(0, 3, 1, 2).contiguous().view(n, v * c, t)
        x = self.data_bn(x)
        x = x.view(n, v, c, t).permute(0, 2, 3, 1).contiguous()

        for block in self.blocks:
            x = block(x, self.A)

        x = x.mean(dim=[2, 3])
        return self.head(x)


if __name__ == "__main__":
    model = STGCN()
    dummy = torch.randn(4, IN_CHANNELS, 32, 17)
    out = model(dummy)
    n_params = sum(p.numel() for p in model.parameters())
    print(f"Output: {out.shape}, tham số: {n_params:,}")
