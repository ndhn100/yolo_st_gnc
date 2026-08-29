"""Đồ thị khung xương COCO-17 cho ST-GCN.

Xây dựng ma trận kề A theo chiến lược "spatial configuration partitioning"
(Yan et al., AAAI 2018): với mỗi đỉnh, tập lân cận 1-hop được chia thành
3 nhóm — chính nó (root), nhóm hướng tâm (gần trọng tâm hơn) và nhóm ly tâm
(xa trọng tâm hơn) — tạo ra tensor A có shape (3, V, V).
"""
import numpy as np

# Thứ tự 17 keypoints COCO của YOLO-Pose:
# 0:mũi 1:mắt trái 2:mắt phải 3:tai trái 4:tai phải 5:vai trái 6:vai phải
# 7:khuỷu trái 8:khuỷu phải 9:cổ tay trái 10:cổ tay phải 11:hông trái
# 12:hông phải 13:gối trái 14:gối phải 15:cổ chân trái 16:cổ chân phải
COCO_EDGES = [
    (0, 1), (0, 2), (1, 3), (2, 4),          # đầu
    (0, 5), (0, 6), (5, 6),                  # cổ - vai
    (5, 7), (7, 9), (6, 8), (8, 10),         # tay
    (5, 11), (6, 12), (11, 12),              # thân
    (11, 13), (13, 15), (12, 14), (14, 16),  # chân
]

NUM_NODES = 17
CENTER = 0  # đỉnh trung tâm dùng để phân nhóm hướng tâm / ly tâm


def get_hop_distance(num_nodes, edges, max_hop=1):
    adj = np.zeros((num_nodes, num_nodes))
    for i, j in edges:
        adj[i, j] = 1
        adj[j, i] = 1
    hop_dis = np.full((num_nodes, num_nodes), np.inf)
    transfer_mat = [np.linalg.matrix_power(adj + np.eye(num_nodes), d) > 0
                    for d in range(max_hop + 1)]
    arrive_mat = np.stack(transfer_mat)
    for d in range(max_hop, -1, -1):
        hop_dis[arrive_mat[d]] = d
    return hop_dis


def normalize_digraph(adj):
    """Chuẩn hóa D^-1 * A."""
    degree = adj.sum(0)
    dn = np.zeros_like(adj)
    for i in range(adj.shape[0]):
        if degree[i] > 0:
            dn[i, i] = degree[i] ** (-1)
    return adj @ dn


class Graph:
    """Đồ thị khung xương với chiến lược phân nhóm spatial."""

    def __init__(self, max_hop=1):
        self.max_hop = max_hop
        self.num_nodes = NUM_NODES
        self.edges = COCO_EDGES
        self.center = CENTER
        self.hop_dis = get_hop_distance(self.num_nodes, self.edges, max_hop)
        self.A = self._build_spatial_adjacency()

    def _build_spatial_adjacency(self):
        valid_hop = range(0, self.max_hop + 1)
        adjacency = np.zeros((self.num_nodes, self.num_nodes))
        for hop in valid_hop:
            adjacency[self.hop_dis == hop] = 1
        norm_adj = normalize_digraph(adjacency)

        A = []
        for hop in valid_hop:
            a_root = np.zeros((self.num_nodes, self.num_nodes))
            a_close = np.zeros((self.num_nodes, self.num_nodes))
            a_further = np.zeros((self.num_nodes, self.num_nodes))
            for i in range(self.num_nodes):
                for j in range(self.num_nodes):
                    if self.hop_dis[j, i] == hop:
                        if self.hop_dis[j, self.center] == self.hop_dis[i, self.center]:
                            a_root[j, i] = norm_adj[j, i]
                        elif self.hop_dis[j, self.center] > self.hop_dis[i, self.center]:
                            a_close[j, i] = norm_adj[j, i]
                        else:
                            a_further[j, i] = norm_adj[j, i]
            if hop == 0:
                A.append(a_root)
            else:
                A.append(a_root + a_close)
                A.append(a_further)
        return np.stack(A).astype(np.float32)  # (3, V, V) với max_hop=1


if __name__ == "__main__":
    import config  # noqa: F401 (bật UTF-8 cho console)
    g = Graph()
    print("A shape:", g.A.shape)
    print("Tổng mỗi partition:", g.A.sum(axis=(1, 2)))
