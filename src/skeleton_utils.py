"""Tiện ích xử lý chuỗi khung xương: nội suy khớp mất, định vị thời điểm ngã,
chuẩn hóa cửa sổ. Dùng chung cho build_dataset.py và realtime_demo.py để
đảm bảo dữ liệu huấn luyện và suy luận thời gian thực được xử lý giống nhau.
"""
import numpy as np

from config import IN_CHANNELS, KPT_CONF_TH

L_SHOULDER, R_SHOULDER = 5, 6
L_HIP, R_HIP = 11, 12

# Cặp khớp trái/phải để hoán đổi khi lật ngang (augmentation)
FLIP_PAIRS = [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12), (13, 14), (15, 16)]
# Tra cứu 2 chiều: khớp → khớp đối xứng (mũi 0 không có cặp)
FLIP_MAP = {a: b for a, b in FLIP_PAIRS} | {b: a for a, b in FLIP_PAIRS}


def interpolate_missing(kpts, conf_th=KPT_CONF_TH):
    """Nội suy tuyến tính theo thời gian các khớp có confidence thấp.

    kpts: (T, 17, 3) — trả về bản sao đã nội suy x, y (confidence giữ nguyên).
    """
    out = kpts.copy().astype(np.float32)
    T = out.shape[0]
    t_idx = np.arange(T)
    for j in range(out.shape[1]):
        valid = out[:, j, 2] >= conf_th
        if valid.sum() == 0:
            continue  # khớp không bao giờ xuất hiện — giữ nguyên 0
        if valid.sum() < T:
            for c in range(2):  # x và y
                out[:, j, c] = np.interp(t_idx, t_idx[valid], out[valid, j, c])
    return out


def valid_frame_mask(kpts, conf_th=KPT_CONF_TH):
    """Khung hình được coi là hợp lệ nếu phát hiện được ít nhất 1 khớp."""
    return (kpts[:, :, 2] >= conf_th).any(axis=1)


def smooth_1d(x, win=5):
    if len(x) < win:
        return x
    kernel = np.ones(win) / win
    return np.convolve(x, kernel, mode="same")


def hip_center(kpts):
    """Tọa độ trung điểm hai hông, shape (T, 2)."""
    return (kpts[:, L_HIP, :2] + kpts[:, R_HIP, :2]) / 2.0


def shoulder_center(kpts):
    return (kpts[:, L_SHOULDER, :2] + kpts[:, R_SHOULDER, :2]) / 2.0


def locate_fall_center(kpts):
    """Ước lượng khung hình xảy ra té ngã trong 1 trial.

    Ý tưởng: khi ngã, trọng tâm cơ thể (trung điểm hông) rơi xuống nhanh —
    trong tọa độ ảnh, y tăng nhanh. Lấy khung hình có vận tốc rơi lớn nhất.
    """
    y = smooth_1d(hip_center(kpts)[:, 1], win=5)
    vel = np.gradient(y)
    vel = smooth_1d(vel, win=5)
    return int(np.argmax(vel))


def normalize_window(window, fill="mirror"):
    """Chuẩn hóa 1 cửa sổ (T, 17, 3) pixel → tọa độ tương đối bất biến
    với vị trí đứng và khoảng cách tới camera.

    - Tịnh tiến: trừ tâm hông của KHUNG HÌNH GIỮA cửa sổ (dùng 1 mốc cố định
      cho cả cửa sổ để giữ lại chuyển động rơi — nếu trừ tâm từng khung hình
      sẽ xóa mất tín hiệu té ngã).
    - Tỉ lệ: chia cho độ dài thân (vai→hông) trung vị trong cửa sổ.

    fill: cách xử lý khớp bị che suốt cửa sổ.
    - "mirror": lật khớp đối xứng qua (mặc định) — dùng cho SUY LUẬN/EVALUATE.
    - "origin": ghim về gốc (tâm hông) — CHỈ dùng để build dataset HUẤN LUYỆN.
      Cặp (train trên "origin", suy luận trên "mirror") là cấu hình cho kết
      quả tốt nhất đã kiểm chứng (test F1 té ngã 0,876); train thẳng trên
      "mirror" làm mô hình học shortcut mới, F1 tụt còn 0,67-0,74.
    """
    out = window.copy().astype(np.float32)
    T = out.shape[0]

    center = hip_center(out)[T // 2]  # (2,)

    torso = np.linalg.norm(shoulder_center(out) - hip_center(out), axis=1)
    torso = torso[torso > 1.0]
    scale = float(np.median(torso)) if len(torso) > 0 else 1.0
    scale = max(scale, 1e-3)

    out[:, :, 0] = (out[:, :, 0] - center[0]) / scale
    out[:, :, 1] = (out[:, :, 1] - center[1]) / scale
    out[:, :, :2] = np.clip(out[:, :, :2], -6.0, 6.0)

    # Khớp không xuất hiện ở bất kỳ khung hình nào trong cửa sổ: tọa độ thô
    # là 0 → sau chuẩn hóa thành điểm rác phụ thuộc vị trí người.
    # Ưu tiên lấy vị trí gương của khớp đối xứng trái/phải (vd tai phải bị
    # che → lật tai trái qua). Ghim về gốc (tâm hông) sẽ tạo hình học
    # "khớp đầu ngang hông" giống người đang ngã → báo giả hàng loạt trên
    # subject đứng quay lưng (S13-Activity7: 103 FP → 17 FP khi sửa).
    never_valid = (window[:, :, 2] < KPT_CONF_TH).all(axis=0)
    for j in np.where(never_valid)[0]:
        pair = FLIP_MAP.get(j)
        if fill == "mirror" and pair is not None and not never_valid[pair]:
            out[:, j, 0] = -out[:, pair, 0]
            out[:, j, 1] = out[:, pair, 1]
        else:  # fill="origin", cả cặp cùng mất, hoặc mũi: ghim về gốc
            out[:, j, 0] = 0.0
            out[:, j, 1] = 0.0
    return out


def window_to_tensor_layout(window):
    """(T, V, C) → (C, T, V) cho ST-GCN, chỉ giữ IN_CHANNELS kênh đầu (x, y)."""
    return np.transpose(window, (2, 0, 1))[:IN_CHANNELS].astype(np.float32)


def select_person(result, prev_center, img_diag):
    """Chọn đúng người cần theo dõi trong kết quả YOLO-Pose 1 khung hình.

    Cảnh quay có thể có nhiều người (người đi phía sau vách kính, ảnh phản
    chiếu...). Nếu chọn đơn thuần theo confidence, khung xương có thể "nhảy"
    sang người khác giữa chừng — cú nhảy tọa độ đó giống hệt một cú ngã và
    gây báo động giả. Quy tắc:
    - Có vị trí khung hình trước: ưu tiên người gần vị trí đó (trong bán kính
      15% đường chéo ảnh); trong nhóm đó lấy người confidence cao nhất.
    - Chưa có (hoặc mất dấu): lấy người có confidence * sqrt(diện tích box)
      lớn nhất — subject luôn là người lớn nhất/rõ nhất trong khung hình.

    Trả về (kpts (17,3), center (2,) hoặc None).
    """
    boxes = result.boxes
    if boxes is None or len(boxes) == 0:
        return np.zeros((17, 3), dtype=np.float32), prev_center

    xyxy = boxes.xyxy.cpu().numpy()
    conf = boxes.conf.cpu().numpy()
    centers = np.stack([(xyxy[:, 0] + xyxy[:, 2]) / 2,
                        (xyxy[:, 1] + xyxy[:, 3]) / 2], axis=1)

    idx = None
    if prev_center is not None:
        dist = np.linalg.norm(centers - prev_center, axis=1)
        near = dist < 0.15 * img_diag
        if near.any():
            cand = np.where(near)[0]
            idx = int(cand[conf[cand].argmax()])
    if idx is None:
        area = (xyxy[:, 2] - xyxy[:, 0]) * (xyxy[:, 3] - xyxy[:, 1])
        idx = int((conf * np.sqrt(np.maximum(area, 1))).argmax())

    kpts = result.keypoints.data[idx].cpu().numpy().astype(np.float32)
    return kpts, centers[idx]
