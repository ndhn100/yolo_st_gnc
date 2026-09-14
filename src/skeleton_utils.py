import numpy as np

from config import IN_CHANNELS, KPT_CONF_TH

L_SHOULDER, R_SHOULDER = 5, 6
L_HIP, R_HIP = 11, 12

FLIP_PAIRS = [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12), (13, 14), (15, 16)]
FLIP_MAP = {a: b for a, b in FLIP_PAIRS} | {b: a for a, b in FLIP_PAIRS}


def interpolate_missing(kpts, conf_th=KPT_CONF_TH):

    out = kpts.copy().astype(np.float32)
    T = out.shape[0]
    t_idx = np.arange(T)
    for j in range(out.shape[1]):
        valid = out[:, j, 2] >= conf_th
        if valid.sum() == 0:
            continue
        if valid.sum() < T:
            for c in range(2):
                out[:, j, c] = np.interp(t_idx, t_idx[valid], out[valid, j, c])
    return out


def valid_frame_mask(kpts, conf_th=KPT_CONF_TH):
    return (kpts[:, :, 2] >= conf_th).any(axis=1)


def smooth_1d(x, win=5):
    if len(x) < win:
        return x
    kernel = np.ones(win) / win
    return np.convolve(x, kernel, mode="same")


def hip_center(kpts):
    return (kpts[:, L_HIP, :2] + kpts[:, R_HIP, :2]) / 2.0


def shoulder_center(kpts):
    return (kpts[:, L_SHOULDER, :2] + kpts[:, R_SHOULDER, :2]) / 2.0


def locate_fall_center(kpts):

    y = smooth_1d(hip_center(kpts)[:, 1], win=5)
    vel = np.gradient(y)
    vel = smooth_1d(vel, win=5)
    return int(np.argmax(vel))


def normalize_window(window, fill="mirror"):


    out = window.copy().astype(np.float32)
    T = out.shape[0]

    center = hip_center(out)[T // 2]

    torso = np.linalg.norm(shoulder_center(out) - hip_center(out), axis=1)
    torso = torso[torso > 1.0]
    scale = float(np.median(torso)) if len(torso) > 0 else 1.0
    scale = max(scale, 1e-3)

    out[:, :, 0] = (out[:, :, 0] - center[0]) / scale
    out[:, :, 1] = (out[:, :, 1] - center[1]) / scale
    out[:, :, :2] = np.clip(out[:, :, :2], -6.0, 6.0)

    never_valid = (window[:, :, 2] < KPT_CONF_TH).all(axis=0)
    for j in np.where(never_valid)[0]:
        pair = FLIP_MAP.get(j)
        if fill == "mirror" and pair is not None and not never_valid[pair]:
            out[:, j, 0] = -out[:, pair, 0]
            out[:, j, 1] = out[:, pair, 1]
        else:
            out[:, j, 0] = 0.0
            out[:, j, 1] = 0.0
    return out


def window_to_tensor_layout(window):
    return np.transpose(window, (2, 0, 1))[:IN_CHANNELS].astype(np.float32)


def select_person(result, prev_center, img_diag):


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
