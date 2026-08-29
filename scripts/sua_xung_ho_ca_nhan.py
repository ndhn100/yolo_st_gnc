from pathlib import Path
from docx import Document

path = Path(r"C:\Users\ndhng\Downloads\YOLO_Pose_and_ST_GCN\docs\KhaoSatHienTrangPhatHienTeNga_DaBoSung.docx")
doc = Document(path)
old = "nhóm khảo sát thêm một số sản phẩm đang được công bố và sử dụng"
new = "tôi khảo sát thêm một số sản phẩm đang được công bố và sử dụng"
count = 0
for paragraph in doc.paragraphs:
    if old in paragraph.text:
        for run in paragraph.runs:
            if old in run.text:
                run.text = run.text.replace(old, new)
                count += 1
        if old in paragraph.text:
            raise RuntimeError("Cụm từ cần thay nằm trên nhiều run; cần xử lý thủ công.")
if count != 1:
    raise RuntimeError(f"Số lần thay thế không đúng: {count}")
doc.save(path)
print(f"Đã thay {count} cụm từ trong {path}")
