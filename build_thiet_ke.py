from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_BREAK
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'docs' / 'ThietKeHeThong_PhatHienTeNga_v1.docx'
ASSETS = ROOT / 'docs' / 'assets_thietke'
ASSETS.mkdir(exist_ok=True)

BLUE = '1F4D78'; BLUE2 = '2E74B5'; LIGHT = 'E8EEF5'; GRAY = 'F2F4F7'; DARK = '0B2545'; GREEN = '276749'

def diagram(path, title, boxes, arrows):
    scale=12; image=Image.new('RGB',(1200,660),'white'); draw=ImageDraw.Draw(image)
    font_title=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 28); font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 18); small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 15)
    draw.text((600,24),title,anchor='ma',font=font_title,fill='#0B2545')
    for x,y,w,h,text,color in boxes:
        xy=(x*scale,(55-y-h)*scale,(x+w)*scale,(55-y)*scale)
        draw.rounded_rectangle(xy,radius=14,fill=color,outline='#1F4D78',width=3)
        lines=text.split('\n'); cy=(xy[1]+xy[3])/2-(len(lines)*11)
        for line in lines: draw.text(((xy[0]+xy[2])/2,cy),line,anchor='ma',font=font,fill='#102A43'); cy+=23
    for x1,y1,x2,y2,label in arrows:
        a=(x1*scale,(55-y1)*scale); b=(x2*scale,(55-y2)*scale); draw.line([a,b],fill='#4A5568',width=3); draw.polygon([(b[0],b[1]),(b[0]-10,b[1]-5),(b[0]-10,b[1]+5)],fill='#4A5568')
        if label: draw.text(((a[0]+b[0])/2,(a[1]+b[1])/2-16),label,anchor='ma',font=small,fill='#4A5568')
    image.save(path)

diagram(ASSETS/'kien_truc.png', 'Kiến trúc triển khai cục bộ', [
    (2,20,16,13,'Camera IP / Webcam\nRTSP hoặc USB','#F2F4F7'),
    (25,20,18,13,'Dịch vụ suy luận\nYOLOv8n-Pose + ST-GCN','#E8EEF5'),
    (50,34,18,11,'API & điều phối\ncảnh báo','#E8EEF5'),
    (50,13,18,11,'SQLite\nSự kiện & cấu hình','#F2F4F7'),
    (75,34,20,11,'Trình duyệt web\nNgười thân / trực / kỹ thuật','#F2F4F7'),
    (75,13,20,11,'Dịch vụ thông báo\nEmail/Telegram (tùy chọn)','#F2F4F7')], [
    (18,26,25,26,'khung hình'),(43,26,50,39,'sự kiện ứng viên'),(59,34,59,24,'ghi/đọc'),(68,39,75,39,'HTTPS nội bộ'),(68,38,75,19,'gửi cảnh báo')])
diagram(ASSETS/'sequence.png', 'Luồng xử lý thời gian thực', [
    (3,22,16,12,'1. Nhận khung hình','#F2F4F7'),(23,22,16,12,'2. Trích 17 khớp','#E8EEF5'),
    (43,22,16,12,'3. Đệm 32 khung\n+ chuẩn hóa','#E8EEF5'),(63,22,16,12,'4. ST-GCN\nP(té ngã)','#E8EEF5'),
    (83,22,14,12,'5. Xác minh\n& cảnh báo','#FCE8E6')], [(19,28,23,28,''),(39,28,43,28,''),(59,28,63,28,''),(79,28,83,28,'')])
diagram(ASSETS/'er.png', 'Mô hình dữ liệu logic (rút gọn)', [
    (4,33,18,10,'NguoiDung\nuser_id, role','#E8EEF5'),(4,10,18,10,'Phong\nroom_id','#E8EEF5'),
    (35,33,18,10,'Camera\ncamera_id, room_id','#F2F4F7'),(35,10,18,10,'SuKienTeNga\nevent_id, camera_id','#FCE8E6'),
    (69,33,23,10,'NguoiNhanCanhBao\nevent_id, user_id','#F2F4F7'),(69,10,23,10,'NhatKyHeThong\nlog_id, camera_id','#F2F4F7')],
    [(22,38,35,38,'1-n'),(22,15,35,15,'1-n'),(53,15,69,15,'1-n'),(53,38,69,38,'1-n'),(44,20,44,33,'1-n')])

def set_cell_shading(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr(); shd = OxmlElement('w:shd'); shd.set(qn('w:fill'), fill); tcPr.append(shd)
def set_cell_margins(cell, top=80, start=120, bottom=80, end=120):
    tc = cell._tc; tcPr = tc.get_or_add_tcPr(); tcMar = tcPr.first_child_found_in('w:tcMar')
    if tcMar is None: tcMar = OxmlElement('w:tcMar'); tcPr.append(tcMar)
    for m,v in [('top',top),('start',start),('bottom',bottom),('end',end)]:
        node = tcMar.find(qn('w:'+m))
        if node is None: node=OxmlElement('w:'+m); tcMar.append(node)
        node.set(qn('w:w'), str(v)); node.set(qn('w:type'),'dxa')
def set_repeat_table_header(row):
    trPr=row._tr.get_or_add_trPr(); e=OxmlElement('w:tblHeader'); e.set(qn('w:val'),'true'); trPr.append(e)
def set_table_width(table, widths):
    table.autofit=False
    tblPr=table._tbl.tblPr; tblW=tblPr.first_child_found_in('w:tblW'); tblW.set(qn('w:w'),'9360'); tblW.set(qn('w:type'),'dxa')
    for row in table.rows:
        for i,cell in enumerate(row.cells): cell.width=Inches(widths[i])
def set_font(run, size=11, bold=False, color='000000', italic=False):
    run.font.name='Calibri'; run._element.rPr.rFonts.set(qn('w:ascii'),'Calibri'); run._element.rPr.rFonts.set(qn('w:hAnsi'),'Calibri'); run.font.size=Pt(size); run.bold=bold; run.italic=italic; run.font.color.rgb=RGBColor.from_string(color)

doc=Document(); sec=doc.sections[0]; sec.top_margin=Inches(.8); sec.bottom_margin=Inches(.75); sec.left_margin=Inches(.85); sec.right_margin=Inches(.85); sec.header_distance=Inches(.35); sec.footer_distance=Inches(.35)
styles=doc.styles
normal=styles['Normal']; normal.font.name='Calibri'; normal._element.rPr.rFonts.set(qn('w:ascii'),'Calibri'); normal._element.rPr.rFonts.set(qn('w:hAnsi'),'Calibri'); normal.font.size=Pt(11); normal.paragraph_format.space_after=Pt(6); normal.paragraph_format.line_spacing=1.15
for name,size,color,before,after in [('Heading 1',16,BLUE2,16,8),('Heading 2',13,BLUE2,12,6),('Heading 3',11.5,BLUE,8,4)]:
    s=styles[name]; s.font.name='Calibri'; s._element.rPr.rFonts.set(qn('w:ascii'),'Calibri'); s._element.rPr.rFonts.set(qn('w:hAnsi'),'Calibri'); s.font.size=Pt(size); s.font.bold=True; s.font.color.rgb=RGBColor.from_string(color); s.paragraph_format.space_before=Pt(before); s.paragraph_format.space_after=Pt(after); s.paragraph_format.keep_with_next=True
header=sec.header.paragraphs[0]; header.text='ĐỒ ÁN NGÀNH | THIẾT KẾ HỆ THỐNG'; header.alignment=WD_ALIGN_PARAGRAPH.RIGHT
for r in header.runs: set_font(r,8,False,'6B7280')
footer=sec.footer.paragraphs[0]; footer.alignment=WD_ALIGN_PARAGRAPH.CENTER; r=footer.add_run('Hệ thống phát hiện té ngã ở người cao tuổi | '); set_font(r,8,False,'6B7280')
fld=OxmlElement('w:fldSimple'); fld.set(qn('w:instr'),'PAGE'); footer._p.append(fld)

def p(text='', style=None, align=None, boldlead=None):
    para=doc.add_paragraph(style=style)
    if align: para.alignment=align
    if boldlead and text.startswith(boldlead):
        a=para.add_run(boldlead); set_font(a,11,True); b=para.add_run(text[len(boldlead):]); set_font(b,11)
    else:
        r=para.add_run(text); set_font(r,11)
    return para
def heading(text, level=1): return doc.add_paragraph(text, style=f'Heading {level}')
def bullet(text):
    para=doc.add_paragraph(style='List Bullet'); para.paragraph_format.space_after=Pt(3); r=para.add_run(text); set_font(r,11); return para
def num(text):
    para=doc.add_paragraph(style='List Number'); para.paragraph_format.space_after=Pt(3); r=para.add_run(text); set_font(r,11); return para
def table(headers, rows, widths=None):
    t=doc.add_table(rows=1, cols=len(headers)); t.alignment=WD_TABLE_ALIGNMENT.LEFT; t.style='Table Grid'
    hdr=t.rows[0]; set_repeat_table_header(hdr)
    for i,h in enumerate(headers):
        c=hdr.cells[i]; c.text=''; set_cell_shading(c,GRAY); set_cell_margins(c); c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER; rr=c.paragraphs[0].add_run(h); set_font(rr,9.5,True,DARK)
    for row in rows:
        cells=t.add_row().cells
        for i,val in enumerate(row):
            cells[i].text=''; set_cell_margins(cells[i]); cells[i].vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER; rr=cells[i].paragraphs[0].add_run(str(val)); set_font(rr,9.3)
    if widths: set_table_width(t,widths)
    doc.add_paragraph().paragraph_format.space_after=Pt(2)
    return t
def caption(text):
    q=doc.add_paragraph(); q.alignment=WD_ALIGN_PARAGRAPH.CENTER; q.paragraph_format.space_after=Pt(7); r=q.add_run(text); set_font(r,9,False,'555555',True)

for _ in range(3): p('')
for line,size,bold in [('TRƯỜNG ĐẠI HỌC MỞ THÀNH PHỐ HỒ CHÍ MINH',13,True),('KHOA ĐÀO TẠO ĐẶC BIỆT',13,True),('',12,False),('ĐỒ ÁN NGÀNH',16,True),('BÁO CÁO GIAI ĐOẠN 4',16,True),('',12,False),('THIẾT KẾ HỆ THỐNG',22,True),('HỆ THỐNG PHÁT HIỆN TÉ NGÃ Ở NGƯỜI CAO TUỔI',17,True),('Dựa trên camera, YOLOv8n-Pose và ST-GCN',12,False)]:
    q=p('',align=WD_ALIGN_PARAGRAPH.CENTER); q.paragraph_format.space_after=Pt(5); r=q.add_run(line); set_font(r,size,bold,BLUE if size>=17 else DARK)
for _ in range(7): p('')
for line in ['Sinh viên thực hiện: Nguyễn Đinh Hồng Ngọc','Mã số sinh viên: 2351010139','Giảng viên hướng dẫn: TS. Nguyễn Tiến Đạt','Học kỳ 3 – Năm học 2025–2026','Thành phố Hồ Chí Minh – 2026']:
    q=p('',align=WD_ALIGN_PARAGRAPH.CENTER); r=q.add_run(line); set_font(r,11)
doc.add_page_break()

heading('MỤC LỤC',1)
p('Tài liệu được tổ chức theo tuyến chuyển đổi từ Phân tích sang Thiết kế: kiến trúc → dữ liệu → xử lý → giao diện → triển khai và kiểm thử. Mục lục tự động có thể được cập nhật trong Word nếu cần.')
for s in ['PHẦN MỞ ĐẦU','PHẦN I. THIẾT KẾ KIẾN TRÚC HỆ THỐNG','PHẦN II. THIẾT KẾ DỮ LIỆU','PHẦN III. THIẾT KẾ XỬ LÝ VÀ MÔ-ĐUN HỌC MÁY','PHẦN IV. THIẾT KẾ GIAO DIỆN VÀ TƯƠNG TÁC','PHẦN V. THIẾT KẾ TRIỂN KHAI, BẢO MẬT VÀ KIỂM THỬ','KẾT LUẬN','PHỤ LỤC']:
    p(s)
heading('PHẦN MỞ ĐẦU',1)
heading('1. Mục tiêu và phạm vi thiết kế',2)
p('Tài liệu này chuyển các yêu cầu đã phân tích thành bản thiết kế có thể cài đặt cho phiên bản đồ án. Hệ thống nhận luồng hình ảnh từ một camera trong một phòng, trích xuất khung xương người, phân loại nguy cơ té ngã và tạo cảnh báo cho người chăm sóc. Thiết kế ưu tiên chạy cục bộ, không lưu video mặc định và không đặt mục tiêu thay thế thiết bị y tế.')
bullet('Phạm vi phiên bản đồ án: một nguồn camera/webcam; một người được theo dõi chính; màn hình giám sát tối giản; lưu sự kiện và nhật ký; cảnh báo tại chỗ và kênh thông báo cấu hình được.')
bullet('Ngoài phạm vi: nhận diện danh tính khuôn mặt, chẩn đoán y khoa, gọi cấp cứu tự động, đồng bộ đám mây bắt buộc, nhiều camera đồng bộ và học liên tục từ dữ liệu nhà thật.')
heading('2. Nguyên tắc thiết kế',2)
table(['Nguyên tắc','Quyết định thiết kế'],[
('Tối giản và khả thi','Tách rõ lõi suy luận thời gian thực khỏi giao diện; dùng SQLite trong phạm vi một máy xử lý.'),
('Riêng tư theo mặc định','Khung hình chỉ nằm trong bộ nhớ phục vụ suy luận; cơ sở dữ liệu chỉ lưu metadata sự kiện. Ảnh minh chứng là tùy chọn.'),
('Giải thích được','Mô hình chỉ cung cấp xác suất; ngưỡng, chống lặp, xác nhận và leo thang được điều khiển bằng quy tắc tường minh.'),
('Khả năng thay thế','YOLO-Pose, ST-GCN và kênh thông báo đặt sau các giao diện mô-đun để có thể thay đổi mà ít ảnh hưởng phần còn lại.')], [1.6,4.9])

heading('PHẦN I. THIẾT KẾ KIẾN TRÚC HỆ THỐNG',1)
heading('1.1. Kiến trúc tổng thể',2)
p('Hệ thống áp dụng kiến trúc phân lớp trên một máy xử lý cục bộ. Tầng thu nhận và suy luận xử lý khung hình; tầng nghiệp vụ quyết định trạng thái sự kiện, lưu vết và cảnh báo; tầng trình bày cung cấp màn hình cho các vai trò. Camera và dịch vụ thông báo là hệ thống ngoài.')
doc.add_picture(str(ASSETS/'kien_truc.png'), width=Inches(6.55)); caption('Hình 1. Kiến trúc triển khai cục bộ của hệ thống')
heading('1.2. Các thành phần và trách nhiệm',2)
table(['Thành phần','Trách nhiệm','Đầu vào / đầu ra'],[
('VideoSource','Mở webcam hoặc RTSP, kiểm tra kết nối, cấp khung hình theo thời gian.','URL/thiết bị → frame BGR'),
('PoseExtractor','Gọi YOLOv8n-Pose, chọn người theo quy tắc nhất quán và trả về 17 khớp.','frame → keypoints + confidence'),
('SequenceBuffer','Nội suy thiếu ngắn hạn, chuẩn hóa tọa độ và giữ 32 khung mới nhất.','keypoints → tensor (2,32,17)'),
('FallClassifier','Nạp checkpoint ST-GCN, suy luận định kỳ mỗi 4 khung và trả xác suất ngã.','tensor → p_fall'),
('EventManager','Làm mượt kết quả, áp ngưỡng, chống lặp và quản lý vòng đời sự kiện.','p_fall → sự kiện/trạng thái'),
('AlertDispatcher','Hiển thị cảnh báo tại chỗ và gửi thông tin tối thiểu cho kênh đã cấu hình.','sự kiện → thông báo'),
('Web/API','Cho phép xem trạng thái, xác nhận, đánh dấu báo sai, cấu hình phòng/camera.','HTTP JSON ↔ UI'),
('Repository','Lưu cấu hình, sự kiện, người nhận và nhật ký vào SQLite.','đối tượng ↔ bảng dữ liệu')], [1.25,3.4,1.85])
heading('1.3. Thiết kế gói/mô-đun',2)
table(['Gói','Tệp/chức năng chính','Phụ thuộc'],[
('src.config','Thông số tập trung: ngưỡng YOLO, kích thước cửa sổ, stride, thư mục dữ liệu.','Không phụ thuộc nghiệp vụ.'),
('src.skeleton_utils','Chọn người, nội suy, chuẩn hóa, chuyển (T,V,C) sang tensor.','NumPy.'),
('src.graph, src.stgcn','Định nghĩa đồ thị COCO-17 và mạng ST-GCN 7 khối.','PyTorch.'),
('src.realtime_demo','Luồng suy luận thời gian thực; sẽ được tách thêm EventManager/Repository khi hoàn thiện app.','OpenCV, YOLO, ST-GCN.'),
('web (đề xuất)','Routes, template/màn hình, xác thực đơn giản theo vai trò.','API, Repository.'),
('data/checkpoints','Keypoint, mẫu cửa sổ, checkpoint mô hình; không là dữ liệu nghiệp vụ.','Pipeline huấn luyện.')], [1.4,3.5,1.6])

heading('PHẦN II. THIẾT KẾ DỮ LIỆU',1)
heading('2.1. Mô hình dữ liệu logic',2)
p('Mô hình dữ liệu được giản lược để đúng quy mô một điểm lắp đặt. Bảng SuKienTeNga là trung tâm; chỉ lưu dữ liệu cần truy vết việc phát hiện và xử lý, không lưu chuỗi ảnh hoặc khung xương đầy đủ.')
doc.add_picture(str(ASSETS/'er.png'), width=Inches(6.55)); caption('Hình 2. Mô hình dữ liệu logic')
heading('2.2. Lược đồ dữ liệu vật lý đề xuất',2)
table(['Bảng','Khóa chính / khóa ngoại','Thuộc tính chính','Ràng buộc'],[
('nguoi_dung','user_id','ho_ten, vai_tro, lien_he, trang_thai','vai_tro ∈ {THAN_NHAN, TRUC, KY_THUAT}'),
('phong','room_id','ten_phong, mo_ta, active','ten_phong không rỗng'),
('camera','camera_id; room_id → phong','ten_camera, source_uri, trang_thai, nguong','mỗi camera thuộc đúng một phòng'),
('su_kien_te_nga','event_id; camera_id → camera','bat_dau, phat_hien, p_max, trang_thai, ghi_chu','trạng thái theo vòng đời; p_max 0..1'),
('nguoi_nhan_canh_bao','recipient_id; event_id, user_id','kenh, gui_luc, trang_thai_gui, xac_nhan_luc','mỗi event-user-kênh là duy nhất'),
('nhat_ky_he_thong','log_id; camera_id?','thoi_gian, muc_do, ma_su_kien, noi_dung','không sửa nội dung sau khi ghi'),
('cau_hinh','config_key','config_value, updated_at','các khóa whitelist, có kiểm tra miền giá trị')], [1.25,1.7,2.5,1.4])
heading('2.3. Quy tắc dữ liệu và lưu trữ',2)
bullet('Mọi thời điểm lưu theo UTC; giao diện chuyển sang múi giờ Việt Nam (UTC+7).')
bullet('Không lưu ảnh/video mặc định. Nếu bật ảnh minh chứng, chỉ lưu đường dẫn cục bộ được mã hóa/quyền hạn chế và có thời hạn xóa cấu hình được.')
bullet('Không xóa cứng sự kiện trong thời gian đồ án; trạng thái “đã đóng” giữ lịch sử xử lý. Nhật ký hệ thống có thể quay vòng theo dung lượng.')
bullet('Chuỗi keypoint dùng cho suy luận tồn tại trong RAM và bị loại khi cửa sổ trượt; không ghi vào SQLite.')

heading('PHẦN III. THIẾT KẾ XỬ LÝ VÀ MÔ-ĐUN HỌC MÁY',1)
heading('3.1. Thiết kế luồng suy luận',2)
doc.add_picture(str(ASSETS/'sequence.png'), width=Inches(6.55)); caption('Hình 3. Luồng xử lý từ khung hình đến cảnh báo')
num('VideoSource đọc một khung hình; nếu nguồn bị gián đoạn, ghi nhật ký và đổi camera sang trạng thái GIAM_SAT_HAN_CHE.')
num('PoseExtractor dùng YOLOv8n-Pose với ngưỡng confidence cấu hình. Khi có nhiều người, chọn người gần nhất với khung xương của khung trước; không chọn lại đơn thuần theo confidence.')
num('SequenceBuffer chỉ giữ hai kênh x, y. Các khớp thiếu ngắn hạn được nội suy; cửa sổ kém chất lượng bị đánh dấu không đủ dữ liệu.')
num('Khi đủ 32 khung, FallClassifier chạy mỗi 4 khung. Tensor đầu vào có kích thước (N=1, C=2, T=32, V=17).')
num('EventManager tăng bộ đếm khi p_fall vượt ngưỡng; chỉ tạo sự kiện khi đủ số lần liên tiếp. Sự kiện đang mở không bị tạo trùng trong khoảng khóa cảnh báo.')
heading('3.2. Thiết kế ST-GCN và cấu hình',2)
table(['Hạng mục','Thiết kế chốt cho phiên bản đồ án'],[
('Đồ thị đầu vào','17 khớp COCO; cạnh tự thân, cạnh vật lý khung xương và phân vùng không gian như mô-đun graph.py.'),
('Đặc trưng','Chỉ dùng tọa độ x, y đã chuẩn hóa theo tâm hông khung giữa và độ dài thân trung vị; confidence chỉ dùng kiểm soát chất lượng.'),
('Mô hình','ST-GCN 7 khối với các kênh 64, 64, 64, 128, 128, 256, 256; lớp cuối trả hai lớp Không ngã / Té ngã.'),
('Checkpoint','Nạp checkpoints/best.pt; phiên bản checkpoint được ghi vào nhật ký khi khởi động.'),
('Ngưỡng','Ngưỡng phân loại và số lần liên tiếp đặt trong config.py; được hiệu chỉnh trên tập validation, không chỉnh theo tập test.'),
('Fallback','Không đủ khớp / buffer chưa đầy: hiển thị “đang thu thập dữ liệu”, không tạo cảnh báo.')], [1.55,4.9])
heading('3.3. Máy trạng thái sự kiện',2)
table(['Trạng thái','Điều kiện vào','Chuyển tiếp được phép'],[
('THEO_DOI','Không có sự kiện mở.','→ NGHI_NGO khi đạt ngưỡng sơ bộ.'),
('NGHI_NGO','Có xác suất cao nhưng chưa đủ điều kiện xác nhận.','→ CANH_BAO khi đủ số cửa sổ; → THEO_DOI khi xác suất giảm.'),
('CANH_BAO','Đã tạo sự kiện và gửi cảnh báo cấp 1.','→ DA_TIEP_NHAN khi người nhận xác nhận; → LEO_THANG khi quá hạn.'),
('LEO_THANG','Chưa có xác nhận sau thời hạn.','→ DA_TIEP_NHAN; → DA_DONG bởi người trực.'),
('DA_TIEP_NHAN','Có người nhận trách nhiệm xử lý.','→ DA_DONG hoặc BAO_SAI.'),
('BAO_SAI / DA_DONG','Kết thúc vòng đời.','Không tự chuyển tiếp; chỉ ghi chú bổ sung.')], [1.4,2.3,2.75])
heading('3.4. Thuật toán điều phối cảnh báo (mã giả)',2)
p('on_prediction(p, camera):\n  if quality_not_enough: return\n  consecutive = consecutive + 1 if p >= threshold else 0\n  if event_open(camera): update_max_probability(p); return\n  if consecutive >= required_consecutive and not in_cooldown(camera):\n      event = create_event(camera, now, p)\n      dispatch_alert(event, level=1)\n      start_ack_timer(event)\n\non_ack_timeout(event):\n  if not event.acknowledged:\n      dispatch_alert(event, level=2)\n      set_state(event, LEO_THANG)')
heading('3.5. API nội bộ đề xuất',2)
table(['Phương thức','Đường dẫn','Mục đích','Quyền'],[
('GET','/api/status','Tình trạng camera, mô hình, sự kiện đang mở.','Tất cả vai trò'),
('GET','/api/events?from=&to=&state=','Tra cứu lịch sử sự kiện.','Thân nhân, trực'),
('POST','/api/events/{id}/ack','Xác nhận đã tiếp nhận.','Thân nhân, trực'),
('POST','/api/events/{id}/close','Đóng sự kiện, ghi kết quả xử lý.','Trực'),
('POST','/api/events/{id}/false-alarm','Đánh dấu báo sai và ghi lý do.','Thân nhân, trực'),
('GET/PUT','/api/cameras/{id}','Xem hoặc điều chỉnh cấu hình camera/ngưỡng.','Kỹ thuật'),
('GET','/api/logs','Xem lỗi kết nối, lỗi mô hình, lỗi gửi tin.','Kỹ thuật')], [0.7,1.8,2.8,1.2])

heading('PHẦN IV. THIẾT KẾ GIAO DIỆN VÀ TƯƠNG TÁC',1)
heading('4.1. Nguyên tắc giao diện',2)
p('Giao diện web được thiết kế đơn giản, ưu tiên thao tác nhanh hơn trang trí. Màu đỏ chỉ xuất hiện khi có sự kiện cần chú ý; màu xanh/xám thể hiện trạng thái bình thường. Không hiển thị hoặc phát trực tiếp hình ảnh camera trong bản tối thiểu để bảo đảm riêng tư.')
heading('4.2. Các màn hình chính',2)
table(['Màn hình','Người dùng','Nội dung và thao tác'],[
('Tổng quan','Thân nhân, trực','Thẻ trạng thái từng phòng/camera; danh sách sự kiện đang mở; nút “Đã tiếp nhận”.'),
('Chi tiết sự kiện','Thân nhân, trực','Thời điểm, phòng, xác suất cao nhất, trạng thái gửi tin, lịch sử xử lý; xác nhận/đóng/báo sai.'),
('Lịch sử','Thân nhân, trực','Lọc theo ngày, phòng và trạng thái; chỉ xem dữ liệu sự kiện tối thiểu.'),
('Cấu hình camera','Kỹ thuật','Tên phòng, nguồn camera, vùng hoạt động (phiên bản mở rộng), ngưỡng, kiểm tra kết nối.'),
('Nhật ký kỹ thuật','Kỹ thuật','Mất kết nối, lỗi nạp mô hình, tốc độ xử lý, lỗi gửi thông báo.')], [1.5,1.55,3.45])
heading('4.3. Kịch bản thao tác chính',2)
table(['Kịch bản','Luồng giao diện'],[
('Tiếp nhận cảnh báo','Banner/notification → mở sự kiện → xem thông tin tối thiểu → nhấn “Đã tiếp nhận” → hệ thống ghi thời điểm và dừng leo thang.'),
('Đánh dấu báo sai','Mở sự kiện đã tiếp nhận → chọn “Báo sai” → chọn/nhập lý do → xác nhận → trạng thái đổi BAO_SAI, vẫn giữ nhật ký.'),
('Kiểm tra camera','Kỹ thuật mở cấu hình → kiểm tra trạng thái và FPS → thử kết nối → lưu cấu hình hợp lệ → ghi nhật ký thay đổi.')], [1.7,4.8])

heading('PHẦN V. THIẾT KẾ TRIỂN KHAI, BẢO MẬT VÀ KIỂM THỬ',1)
heading('5.1. Môi trường triển khai',2)
table(['Hạng mục','Thiết kế'],[
('Máy xử lý','PC/laptop hoặc máy mini đặt tại nhà; Python, PyTorch, Ultralytics YOLO, OpenCV. GPU là tùy chọn; cần đo hiệu năng trên thiết bị thực.'),
('Nguồn video','Webcam USB cho demo; camera IP qua RTSP khi triển khai. Kiểm tra quyền truy cập trước khi chạy.'),
('Lưu trữ','SQLite trên ổ đĩa cục bộ; checkpoint và cấu hình tách khỏi cơ sở dữ liệu nghiệp vụ.'),
('Mạng','Luồng camera trong LAN. Kênh thông báo ngoài LAN là tùy chọn, lỗi mạng không làm dừng phát hiện cục bộ.'),
('Vận hành','Tự ghi log khởi động/dừng, tình trạng camera và thời gian suy luận. Có hướng dẫn khởi động và sao lưu DB định kỳ.')], [1.55,4.95])
heading('5.2. Bảo mật và riêng tư',2)
table(['Rủi ro','Biện pháp thiết kế'],[
('Lộ hình ảnh riêng tư','Không lưu video mặc định; chỉ xử lý khung hình trong bộ nhớ. Ảnh minh chứng nếu bật phải có mục đích và thời hạn xóa.'),
('Truy cập trái phép','Tài khoản/phiên đăng nhập theo vai trò; API kiểm tra quyền; máy xử lý và tệp DB dùng tài khoản hệ điều hành hạn chế.'),
('Cảnh báo sai hoặc bỏ sót','Nêu rõ hệ thống hỗ trợ cảnh báo, không thay thế giám sát con người/y tế; có xác nhận và đánh dấu báo sai.'),
('Mất camera/mạng','Hiển thị GIAM_SAT_HAN_CHE, ghi log và gửi thông báo kỹ thuật nếu cấu hình; không giả vờ hệ thống vẫn giám sát.'),
('Thay đổi cấu hình không kiểm soát','Lưu nhật ký thay đổi ngưỡng/nguồn camera và chỉ cho vai trò kỹ thuật cập nhật.')], [1.9,4.6])
heading('5.3. Kế hoạch kiểm thử chấp nhận',2)
table(['Mã','Tiêu chí','Cách kiểm thử','Kết quả chấp nhận'],[
('AT-01','Xử lý cửa sổ','Nạp video mẫu; kiểm tra tensor đầu vào 2×32×17.','Không lỗi kích thước; bỏ qua cửa sổ thiếu dữ liệu.'),
('AT-02','Phát hiện','Chạy tập test tách theo người; tính sensitivity, precision, F1.','Báo cáo minh bạch số liệu theo tập test; không dùng accuracy đơn lẻ.'),
('AT-03','Chống báo lặp','Giả lập xác suất cao liên tiếp trong một sự cố.','Chỉ một sự kiện mở/camera trong khoảng cooldown.'),
('AT-04','Leo thang','Không xác nhận sự kiện trong thời hạn cấu hình.','Chuyển LEO_THANG và gửi cấp tiếp theo đúng một lần.'),
('AT-05','Xác nhận/báo sai','Thao tác trên giao diện/API.','Cập nhật trạng thái, người thực hiện, thời điểm và nhật ký.'),
('AT-06','Mất camera','Ngắt nguồn video khi chạy.','Trạng thái GIAM_SAT_HAN_CHE và có log; không treo ứng dụng.'),
('AT-07','Riêng tư','Kiểm tra thư mục lưu sau phiên chạy mặc định.','Không phát sinh video/ảnh hoặc keypoint lưu lâu ngoài chính sách.')], [0.65,1.35,2.9,1.6])
heading('5.4. Lộ trình thi công phù hợp thời gian đồ án',2)
table(['Ưu tiên','Công việc','Đầu ra'],[
('P1','Chuẩn hóa realtime_demo thành dịch vụ suy luận, quản lý buffer và trạng thái cảnh báo.','Demo webcam/video có cảnh báo chống lặp.'),
('P1','Tạo SQLite và EventManager; lưu sự kiện, log, xác nhận/báo sai.','CSDL và API tối thiểu.'),
('P2','Dựng web dashboard cho trạng thái, lịch sử, xác nhận.','Giao diện demo dùng được.'),
('P2','Tích hợp một kênh thông báo cấu hình được và xử lý mất kết nối.','Cảnh báo ngoài màn hình.'),
('P3','Hiệu chỉnh ngưỡng, đo FPS/độ trễ và hoàn thiện kiểm thử.','Báo cáo kết quả và giới hạn.')], [0.7,3.55,2.25])

heading('KẾT LUẬN',1)
p('Bản thiết kế chuyển yêu cầu phân tích thành một hệ thống cục bộ, mô-đun và vừa sức để hiện thực trong đồ án: video → khung xương → cửa sổ 32 khung → ST-GCN → quy tắc sự kiện → cảnh báo và lưu vết. Các nội dung cần ưu tiên khi lập trình là luồng thời gian thực, quản lý trạng thái sự kiện, lưu dữ liệu tối thiểu và giao diện xác nhận. Các chức năng mở rộng chỉ nên thực hiện sau khi lõi phát hiện và cảnh báo đã được kiểm thử ổn định.')
heading('PHỤ LỤC A. Ánh xạ yêu cầu sang mô-đun thiết kế',1)
table(['Nhóm yêu cầu','Mô-đun đáp ứng','Bằng chứng kiểm thử'],[
('Giám sát/phát hiện','VideoSource, PoseExtractor, SequenceBuffer, FallClassifier','AT-01, AT-02'),
('Cảnh báo/leo thang','EventManager, AlertDispatcher','AT-03, AT-04'),
('Xác nhận/lịch sử','Web/API, Repository','AT-05'),
('Tình trạng thiết bị','VideoSource, Web/API, NhatKyHeThong','AT-06'),
('Riêng tư','Repository, chính sách không lưu ảnh mặc định','AT-07')], [1.6,3.05,1.85])
heading('PHỤ LỤC B. Tham số cấu hình cần quản lý',1)
table(['Khóa','Ý nghĩa','Giá trị ban đầu / nguyên tắc'],[
('YOLO_CONF','Ngưỡng nhận người của YOLO-Pose.','0.25 theo config hiện có; hiệu chỉnh bằng dữ liệu validation.'),
('WINDOW_SIZE','Số khung trong một cửa sổ.','32; phải khớp checkpoint ST-GCN.'),
('RT_PRED_STRIDE','Chu kỳ suy luận ST-GCN.','4 khung; cân bằng độ trễ và tải xử lý.'),
('FALL_THRESHOLD','Ngưỡng xác suất tạo nghi ngờ.','Đặt sau đánh giá validation, không tự ý thay đổi khi vận hành.'),
('RT_CONSECUTIVE','Số lần liên tiếp để xác nhận.','Cấu hình được; dùng để giảm báo động giả.'),
('ALERT_COOLDOWN','Khoảng khóa cảnh báo cùng camera.','Cấu hình được; ngăn tạo sự kiện trùng.'),
('ACK_TIMEOUT','Thời hạn chờ tiếp nhận trước leo thang.','Cấu hình theo người chăm sóc thực tế.')], [1.6,2.6,2.3])

for shape, alt in zip(doc.inline_shapes, [
    'Sơ đồ kiến trúc triển khai cục bộ gồm camera, dịch vụ suy luận, API, cơ sở dữ liệu, giao diện web và dịch vụ thông báo.',
    'Sơ đồ mô hình dữ liệu logic liên kết người dùng, phòng, camera, sự kiện té ngã, người nhận cảnh báo và nhật ký.',
    'Sơ đồ luồng xử lý thời gian thực từ nhận khung hình, trích khớp, tạo cửa sổ, phân loại ST-GCN đến xác minh và cảnh báo.'
]):
    shape._inline.docPr.set('descr', alt)

doc.core_properties.title='Thiết kế hệ thống phát hiện té ngã ở người cao tuổi'
doc.core_properties.author='Nguyễn Đinh Hồng Ngọc'
doc.save(OUT)
print(OUT)
