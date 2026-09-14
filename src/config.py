import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_DATA_DIR = PROJECT_ROOT / "raw_data"

DATA_DIR = PROJECT_ROOT / "data"
KEYPOINTS_DIR = DATA_DIR / "keypoints"
DATASET_FILE = DATA_DIR / "dataset.npz"
DATASET_GOC_FILE = DATA_DIR / "dataset_goc.npz"
CHECKPOINT_DIR = PROJECT_ROOT / "checkpoints"
RESULTS_DIR = PROJECT_ROOT / "eval_results"
ALERTS_DIR = PROJECT_ROOT / "fall_alerts"

YOLO_POSE_WEIGHTS = "yolov8n-pose.pt"
YOLO_CONF = 0.25
YOLO_BATCH = 24

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

TRAIN_SUBJECTS = [1, 2, 3, 4, 5, 6, 7, 8]
VAL_SUBJECTS = [9]
TEST_SUBJECTS = [10, 11, 12, 13]

WINDOW_SIZE = 32
ADL_STRIDE = 16
FALL_JITTER = [-8, -4, 0, 4, 8]
KPT_CONF_TH = 0.30
MIN_VALID_RATIO = 0.10
WINDOW_MIN_VALID = 0.5

NUM_JOINTS = 17
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

RT_PRED_STRIDE = 4
RT_FALL_THRESHOLD = 0.85
RT_CONSECUTIVE = 2
RT_ALERT_SECONDS = 3.0
