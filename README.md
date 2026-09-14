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

## 9. Giao diện tải video lên

Giao diện **FallSense** chạy tại **http://127.0.0.1:8000** trên máy có mô hình.
Tải một video, chọn **Phân tích video**, rồi xem kết luận, biểu đồ điểm té ngã,
các mốc thời gian và ảnh khung xương minh chứng. Nhấn một mốc để xem lại video.

```powershell
# Cài thêm thư viện web vào môi trường hiện có (chỉ cần làm một lần)
.\venv\Scripts\python.exe -m pip install -r requirements.txt

# Khởi động giao diện và bộ xử lý video; giữ cửa sổ này mở
.\venv\Scripts\python.exe src\web_app.py

# Hoặc dùng trình khởi động PowerShell
.\start_frontend.ps1
```

Mở địa chỉ trên bằng trình duyệt. Nếu cổng 8000 đã được dùng, chạy
`python src\web_app.py --port 8001` trong môi trường đã kích hoạt.
Nhấn Ctrl+C trong cửa sổ chạy máy chủ để dừng.

### Camera trực tiếp

Nhấn **Bật camera** ở đầu trang để mở webcam mặc định của máy chạy ứng dụng.
Giữ người trong khung hình, nên thấy rõ toàn thân. Sau khoảng 2 giây thu thập
chuyển động, giao diện hiển thị **Không phát hiện té ngã** hoặc cảnh báo đỏ
**PHÁT HIỆN TÉ NGÃ!** kèm tiếng báo. Cảnh báo được giữ khoảng 3 giây để dễ
nhận biết; một cửa sổ đạt ngưỡng 0,85 là đủ kích hoạt, không yêu cầu hai lần.

Nhấn **Tắt tiếng báo** nếu muốn chỉ xem cảnh báo hình ảnh và **Tắt camera**
để ngừng theo dõi. Khi chưa thấy rõ người hoặc chưa đủ dữ liệu, camera hiện
trạng thái chờ thay vì kết luận không té ngã. Không cần huấn luyện lại:
camera dùng chính `best.pt` đang nạp, YOLO và cách chuẩn hóa như video tải lên.

Camera được xử lý trên máy chủ cục bộ, hình ảnh và khung xương chỉ nằm trong
bộ nhớ. Tắt camera sẽ giải phóng thiết bị; nếu đóng trang hoặc mất kết nối,
camera tự dừng sau tối đa khoảng 15 giây không nhận được tín hiệu từ trang.
Trong lúc camera hoạt động, phần tải video được tạm khóa để tránh chạy hai
nguồn đồng thời trên cùng mô hình. Nếu mở camera thất bại, đóng ứng dụng
khác đang dùng webcam và kiểm tra quyền Camera của Windows cho ứng dụng desktop.

Phần trực tiếp nằm trong `src/live_camera.py` và `web/camera.js`.

- **Trọng số:** YOLO dùng `yolov8n-pose.pt`; ST-GCN dùng
  `checkpoints/best.pt`, không dùng `last.pt`. Checkpoint hiện tại ở epoch 16,
  F1 validation = 0,993377. Quy tắc trong `train.py` chọn F1 validation cao
  nhất; khi bằng nhau, chọn validation loss thấp hơn. Giao diện đọc thông tin
  trực tiếp từ checkpoint đang nạp. F1 validation không phải độ tin cậy của
  từng video.
- **Cách đọc kết quả:** chỉ số chính là số sự kiện đủ điều kiện xác nhận.
  Mở **Xem điểm mô hình theo từng đoạn** để xem điểm thô trên thang 0–100,
  số đoạn vượt ngưỡng và tua đến đoạn đạt điểm cao nhất. Điểm cực đại của
  một đoạn không phải xác suất té ngã của cả video; một đoạn ngồi/xổm cũng
  có thể bị mô hình cho điểm cao. Theo cấu hình hiện tại, chỉ một đoạn
  đạt ngưỡng cũng được đánh dấu; trọng số mô hình giữ nguyên.
- **Xử lý thật trên máy:** video → theo dõi một người chính → khung xương
  COCO-17 → lấy mẫu về 18 FPS → chuẩn hóa như pipeline suy luận hiện có →
  ST-GCN. Dùng CUDA nếu có, nếu không dùng CPU. Không cần tải trọng số qua mạng.
- **Kết luận trên giao diện web:** đánh dấu té ngã khi có ít nhất một cửa sổ
  đạt điểm ≥ 0,85 (32 khung/cửa sổ, bước 4). Giữ kết quả phát hiện dù người đứng
  dậy ở cuối video. Video quá ngắn, không thấy rõ người hoặc thiếu dữ liệu
  trả về **Chưa đủ dữ liệu để kết luận**. Kết quả áp dụng cho người chính
  được theo dõi, chưa phải phân tích đồng thời mọi người trong cảnh.
- **Video đầu vào:** MP4, MOV, AVI, MKV, WebM, M4V; tối đa 250 MB và 10 phút.
  Nên thấy rõ toàn thân trong ít nhất 2 giây. Khả năng phát xem trước phụ
  thuộc codec của trình duyệt; lỗi xem trước không ngăn mô hình thử đọc tệp.
- **Lưu tạm:** video nguồn được xóa sau xử lý; ảnh minh chứng được lưu trong
  `web_uploads/` đến khi đổi video/xóa kết quả, tự dọn sau khoảng một giờ,
  hoặc khi vượt giới hạn 12 lượt lưu. Các tệp này được loại khỏi Git.
  Máy chủ chỉ lắng nghe trên máy hiện tại.

Các thành phần mới: `web/` chứa giao diện; `src/web_app.py` phục vụ trang và
quản lý tác vụ nền; `src/video_inference.py` chạy mô hình, tạo kết luận và
minh chứng. Mỗi lần chỉ một tác vụ chạy mô hình để dùng GPU ổn định.

```powershell
# Kiểm tra API và các trường hợp suy luận, không cần tải mô hình để chạy test
.\venv\Scripts\python.exe -m unittest discover -s tests -v
```
