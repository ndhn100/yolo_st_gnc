# Hệ thống phát hiện té ngã: YOLO-Pose + ST-GCN (UP-Fall Detection Dataset)

Đề tài: **"Hệ thống phát hiện té ngã ở người cao tuổi dựa trên camera và học sâu"**.

Pipeline: video → **YOLO-Pose** trích xuất khung xương 17 khớp COCO →
**ST-GCN** (Spatial-Temporal Graph Convolutional Network) phân loại chuỗi
32 khung hình thành **Té ngã / Không té ngã** → cảnh báo thời gian thực.

So với hướng CNN+LSTM trên ảnh RGB, hướng khung xương có 2 ưu điểm đúng với
mục tiêu đề tài: **bảo vệ quyền riêng tư** (chỉ xử lý tọa độ khớp, không cần
lưu ảnh) và **nhẹ** (ST-GCN chỉ ~3 triệu tham số, suy luận ~vài ms).

## 1. Kiến trúc

```
Khung hình ──► YOLOv8n-Pose ──► 17 khớp (x, y, conf) ──► bộ đệm 32 khung
                                                             │
                     chuẩn hóa (tâm hông, độ dài thân)  ◄────┘
                                                             │
              ST-GCN: 7 block GCN không gian + TCN thời gian │
              (64→64→64→128→128→256→256) + edge importance   ▼
                                              P(té ngã) ──► cảnh báo
```

- **Đồ thị khung xương** ([src/graph.py](src/graph.py)): 17 đỉnh = khớp COCO,
  cạnh = liên kết xương; ma trận kề chia 3 nhóm theo chiến lược *spatial
  partitioning* (Yan et al., AAAI 2018).
- **ST-GCN** ([src/stgcn.py](src/stgcn.py)): mỗi block gồm tích chập đồ thị
  (quan hệ KHÔNG GIAN giữa các khớp) + tích chập thời gian kernel 9 (quan hệ
  THỜI GIAN giữa các khung hình) + residual + trọng số quan trọng của cạnh.

## 2. Dữ liệu: UP-Fall Detection Dataset (Camera 1)

Đặt các file zip gốc dạng `Subject{S}Activity{A}Trial{T}Camera1.zip` vào
thư mục khai báo ở `RAW_DATA_DIR` trong [src/config.py](src/config.py).
Mỗi zip chứa ~195 ảnh PNG (~18 fps, ~10 giây).

| Activity | Hoạt động | Nhãn |
|---|---|---|
| 1–5 | Ngã trước (tay/gối), ngã sau, ngã nghiêng, ngã khi ngồi ghế | **Té ngã** |
| 6–11 | Đi, đứng, ngồi, nhặt đồ, nhảy, nằm | Không té |

**Chia dữ liệu theo subject** (người trong tập test không có trong tập train —
đánh giá khách quan hơn chia ngẫu nhiên):

| Split | Subjects |
|---|---|
| Train | 1–8 |
| Validation | 9 |
| Test | 10, 11, 12, 13 |

> Subject 12 trong UP-Fall gốc bị thiếu dữ liệu (chỉ vài trial) — đó là lý do
> "12 subject" thường là S1–S11 + S13.

### Tạo mẫu huấn luyện (cửa sổ trượt)

- Trial **không té**: cửa sổ 32 khung, trượt bước 16 → nhãn 0.
- Trial **té ngã**: tự động định vị thời điểm ngã = khung hình có *vận tốc rơi
  của trung điểm hông* lớn nhất; lấy 5 cửa sổ quanh thời điểm đó (jitter ±8)
  → nhãn 1. Phần đi/đứng **trước khi ngã** được cắt làm mẫu nhãn 0.
- Chuẩn hóa mỗi cửa sổ: trừ tâm hông của khung giữa (giữ nguyên chuyển động
  rơi), chia cho độ dài thân trung vị → bất biến vị trí và khoảng cách camera.
- Khớp bị che/mất (conf < 0.3) được nội suy tuyến tính theo thời gian.

## 3. Cài đặt

```powershell
py -3.14 -m venv venv
venv\Scripts\activate
pip install torch --index-url https://download.pytorch.org/whl/cu126   # GPU
pip install -r requirements.txt
```

## 4. Chạy pipeline

```powershell
# Bước 1: YOLO-Pose trích keypoints từ 301 zip (~15-30 phút trên GPU, chạy lại sẽ bỏ qua file đã có)
python src\extract_keypoints.py

# Bước 2: tạo dataset cửa sổ trượt
python src\build_dataset.py

# Bước 3: huấn luyện ST-GCN (lưu checkpoints\best.pt theo val F1)
python src\train.py

# Bước 4: đánh giá trên tập test (subject 9, 10)
python src\evaluate.py

# Bước 5: demo thời gian thực
python src\realtime_demo.py --source 0                                  # webcam
python src\realtime_demo.py --source "duong\dan\video.mp4"              # video
python src\realtime_demo.py --source "...\Subject9Activity3Trial1Camera1.zip"  # phát lại clip UP-Fall
```

## 5. Cấu trúc project

```
src/
  config.py            # mọi tham số cấu hình tập trung tại đây
  graph.py             # đồ thị khung xương COCO-17 + ma trận kề
  stgcn.py             # mô hình ST-GCN
  skeleton_utils.py    # nội suy, định vị thời điểm ngã, chuẩn hóa cửa sổ
  extract_keypoints.py # bước 1: YOLO-Pose → npz
  build_dataset.py     # bước 2: cửa sổ trượt → dataset.npz
  dataset.py           # PyTorch Dataset + augmentation (lật, xoay, nhiễu)
  train.py             # bước 3: huấn luyện
  evaluate.py          # bước 4: đánh giá + confusion matrix
  realtime_demo.py     # bước 5: demo thời gian thực + cảnh báo
data/keypoints/        # keypoints từng trial (sinh ra ở bước 1)
data/dataset.npz       # dataset cửa sổ (sinh ra ở bước 2)
checkpoints/           # best.pt, last.pt
eval_results/          # biểu đồ huấn luyện, confusion matrix, mẫu sai
fall_alerts/           # ảnh chụp thời điểm phát cảnh báo
```

## 6. Cảnh báo thời gian thực

Suy luận ST-GCN mỗi 4 khung hình trên bộ đệm 32 khung gần nhất; phát cảnh báo
khi `P(té ngã) ≥ 0.6` trong **2 lần liên tiếp** (giảm cảnh báo giả). Khi cảnh
báo: banner đỏ + tiếng beep + lưu ảnh vào `fall_alerts/`. Ngưỡng chỉnh trong
`config.py` (`RT_FALL_THRESHOLD`, `RT_CONSECUTIVE`).

## 7. Kết quả thực nghiệm (test = subject 10, 11, 13 — chưa từng thấy khi train)

Mức cửa sổ (2.653 cửa sổ 32 khung hình — kết quả tái lập được với seed 42,
cuDNN deterministic):

| Chỉ số | Giá trị |
|---|---|
| Accuracy | **94,6%** |
| Precision (té ngã) | 61,7% |
| Recall / độ nhạy (té ngã) | **95,1%** |
| F1 (té ngã) | 74,8% |
| Độ trễ suy luận ST-GCN | ~3 ms/cửa sổ (GPU) |

Mức sự kiện (theo trial, tính "phát cảnh báo" khi trial có ≥2 cửa sổ dương —
xấp xỉ luật cảnh báo 2 lần liên tiếp của demo, ngưỡng 0,85):
**45/45 ca ngã được phát hiện (100%)**, 5/54 trial sinh hoạt bình thường gây
báo động giả (9,3%). Validation (subject 9): F1 = 0,993.

> Precision mức cửa sổ thấp hơn recall là đánh đổi có chủ đích: với hệ thống
> cảnh báo té ngã, bỏ sót nguy hiểm hơn báo nhầm. Các cửa sổ dương giả nằm
> rải rác nên bị luật "≥2 cửa sổ liên tiếp" lọc gần hết ở mức sự kiện, trong
> khi cú ngã thật tạo chuỗi cửa sổ dương liên tiếp xác suất cao.

Hai bài học quan trọng rút ra trong quá trình thực nghiệm (nên đưa vào báo cáo):

1. **Không đưa kênh confidence của keypoint vào mô hình** — ST-GCN sẽ "học tủ"
   mẫu che khuất theo khớp (phụ thuộc hướng đứng của từng người) thay vì học
   chuyển động, làm precision sập trên subject mới (thí nghiệm: F1 test
   0,42 → 0,67 khi bỏ kênh conf).
2. **Phải bám (track) đúng người giữa các khung hình** — phòng quay UP-Fall có
   vách kính, YOLO thấy cả người đi phía sau; nếu chọn người theo confidence
   từng khung hình độc lập, khung xương "nhảy" người tạo tín hiệu giống cú ngã
   (F1 test 0,67 → 0,87 sau khi thêm tracking theo vị trí).

## 8. Tài liệu tham khảo chính

- Yan S., Xiong Y., Lin D. (2018). *Spatial Temporal Graph Convolutional
  Networks for Skeleton-Based Action Recognition*. AAAI 2018.
- Martínez-Villaseñor L. et al. (2019). *UP-Fall Detection Dataset: A
  Multimodal Approach*. Sensors 19(9).
- Ultralytics YOLOv8 Pose: https://docs.ultralytics.com/tasks/pose/
