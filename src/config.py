"""Cấu hình trung tâm cho pipeline YOLO-Pose + ST-GCN (UP-Fall Detection Dataset)."""
import sys
from pathlib import Path

# Console Windows mặc định dùng cp1252 → lỗi khi in tiếng Việt
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

# ----------------------------------------------------------------------------
# Đường dẫn
# ----------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Thư mục chứa các file zip gốc: Subject{S}Activity{A}Trial{T}Camera{C}.zip
RAW_DATA_DIR = PROJECT_ROOT / "raw_data"

DATA_DIR = PROJECT_ROOT / "data"
KEYPOINTS_DIR = DATA_DIR / "keypoints"      # npz keypoints từng trial
# Hai bản dataset chỉ khác cách điền khớp bị che suốt cửa sổ
# (xem skeleton_utils.normalize_window). build_dataset.py tạo cả hai:
DATASET_FILE = DATA_DIR / "dataset.npz"         # mirror-fill → evaluate/demo
DATASET_GOC_FILE = DATA_DIR / "dataset_goc.npz"  # ghim về gốc → CHỈ để train
CHECKPOINT_DIR = PROJECT_ROOT / "checkpoints"
RESULTS_DIR = PROJECT_ROOT / "eval_results"
ALERTS_DIR = PROJECT_ROOT / "fall_alerts"

# ----------------------------------------------------------------------------
# YOLO-Pose
# ----------------------------------------------------------------------------
YOLO_POSE_WEIGHTS = "yolov8n-pose.pt"   # tự động tải về lần chạy đầu
YOLO_CONF = 0.25                        # ngưỡng confidence phát hiện người
YOLO_BATCH = 24                         # số khung hình suy luận mỗi batch

# ----------------------------------------------------------------------------
# Nhãn UP-Fall: Activity 1-5 là té ngã, 6-11 là sinh hoạt bình thường (ADL)
# ----------------------------------------------------------------------------
FALL_ACTIVITIES = {1, 2, 3, 4, 5}
ACTIVITY_NAMES = {
    1: "Nga ve truoc, chong tay",
    2: "Nga ve truoc, chong goi",
    3: "Nga ve sau",
    4: "Nga sang ben",
    5: "Nga khi ngoi ghe",
    6: "Di bo",
    7: "Dung",
    8: "Ngoi",
    9: "Nhat do vat",
    10: "Nhay",
    11: "Nam",
}
CLASS_NAMES = ["Khong te nga", "Te nga"]

# ----------------------------------------------------------------------------
# Chia dữ liệu THEO SUBJECT (subject-independent — người trong tập test
# không xuất hiện trong tập train)
# ----------------------------------------------------------------------------
TRAIN_SUBJECTS = [1, 2, 3, 4, 5, 6, 7, 8]
VAL_SUBJECTS = [9]
TEST_SUBJECTS = [10, 11, 12, 13]

# ----------------------------------------------------------------------------
# Cửa sổ trượt trên chuỗi khung xương
# ----------------------------------------------------------------------------
WINDOW_SIZE = 32          # số khung hình mỗi cửa sổ (~1.7 giây ở 18fps)
ADL_STRIDE = 16           # bước trượt cho các trial không té ngã
FALL_JITTER = [-8, -4, 0, 4, 8]  # dịch tâm cửa sổ quanh thời điểm ngã (tăng cường dữ liệu)
KPT_CONF_TH = 0.30        # dưới ngưỡng này coi là khớp bị mất → nội suy
MIN_VALID_RATIO = 0.10    # trial có < 10% khung hình phát hiện được người → bỏ hẳn
WINDOW_MIN_VALID = 0.5    # cửa sổ phải có ≥ 50% khung hình phát hiện được người

# ----------------------------------------------------------------------------
# Huấn luyện ST-GCN
# ----------------------------------------------------------------------------
NUM_JOINTS = 17           # COCO keypoints
# Chỉ dùng (x, y) — KHÔNG đưa kênh confidence vào mô hình: thực nghiệm cho
# thấy ST-GCN "học tủ" mẫu confidence theo khớp (phụ thuộc hướng đứng của
# từng người) thay vì học chuyển động, làm sập precision trên subject mới.
IN_CHANNELS = 2
NUM_CLASSES = 2
EPOCHS = 70
BATCH_SIZE = 64
LR = 1e-3
WEIGHT_DECAY = 1e-4
WARMUP_EPOCHS = 5
DROPOUT = 0.5
EARLY_STOP_PATIENCE = 20
SEED = 42

# ----------------------------------------------------------------------------
# Demo thời gian thực
# ----------------------------------------------------------------------------
RT_PRED_STRIDE = 4        # chạy ST-GCN mỗi 4 khung hình
# Đo lại 2026-07-14 (mô hình cuối + mirror-fill, trượt stride 4 trên toàn bộ
# trial test): 42/45 ca ngã, 10/54 trial ADL báo giả. Quét lưới ngưỡng
# 0.5-0.9 × 2-4 lần liên tiếp cho thấy 42/45 là kịch trần (3 ca sót không
# cứu được bằng hạ ngưỡng) và (0.85, 2) nằm trên biên tối ưu.
RT_FALL_THRESHOLD = 0.85  # xác suất té ngã để tính 1 lần "dương tính"
RT_CONSECUTIVE = 2        # số lần dương tính liên tiếp để phát cảnh báo
RT_ALERT_SECONDS = 3.0    # thời gian hiển thị cảnh báo
