
import numpy as np

COCO_EDGES = [
    (0, 1), (0, 2), (1, 3), (2, 4),
    (0, 5), (0, 6), (5, 6),
    (5, 7), (7, 9), (6, 8), (8, 10),
    (5, 11), (6, 12), (11, 12),
    (11, 13), (13, 15), (12, 14), (14, 16),
]

NUM_NODES = 17
CENTER = 0


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
    degree = adj.sum(0)
    dn = np.zeros_like(adj)
    for i in range(adj.shape[0]):
        if degree[i] > 0:
            dn[i, i] = degree[i] ** (-1)
    return adj @ dn


class Graph:

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
        return np.stack(A).astype(np.float32)


if __name__ == "__main__":
    import config
    g = Graph()
    print("A shape:", g.A.shape)
    print("Tổng mỗi partition:", g.A.sum(axis=(1, 2)))
