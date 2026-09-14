import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "docs" / "assets_phantich"
OUT = ROOT / "docs" / "PhanTichHeThong_PhatHienTeNga.docx"

FONT = "Times New Roman"
NAVY = RGBColor(0x1F, 0x4E, 0x78)
BLACK = RGBColor(0x00, 0x00, 0x00)

doc = Document()

sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
sec.top_margin, sec.bottom_margin = Cm(2.0), Cm(2.0)
sec.left_margin, sec.right_margin = Cm(3.0), Cm(2.0)

normal = doc.styles["Normal"]
normal.font.name = FONT
normal.font.size = Pt(13)
normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
normal.paragraph_format.space_after = Pt(4)
normal.paragraph_format.line_spacing = 1.0


def _set_font(run, size=13, bold=False, italic=False, color=BLACK, name=FONT):
    run.font.name = name
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = color
    rpr = run._element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.append(rf)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(attr), name)


def para(text="", size=13, bold=False, italic=False, align="justify",
         color=BLACK, space_after=4, space_before=0, indent=0, name=FONT):
    p = doc.add_paragraph()
    p.alignment = {"justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
                   "center": WD_ALIGN_PARAGRAPH.CENTER,
                   "left": WD_ALIGN_PARAGRAPH.LEFT,
                   "right": WD_ALIGN_PARAGRAPH.RIGHT}[align]
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.space_before = Pt(space_before)
    if indent:
        p.paragraph_format.left_indent = Cm(indent)
    if text:
        _set_font(p.add_run(text), size, bold, italic, color, name)
    return p


PAGE_BREAK_PARTS = False


def h1(text):
    if PAGE_BREAK_PARTS:
        doc.add_page_break()
        p = para(text, size=15, bold=True, align="left", color=NAVY,
                 space_before=0, space_after=8)
    else:
        p = para(text, size=15, bold=True, align="left", color=NAVY,
                 space_before=20, space_after=8)
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.page_break_before = False
    return p


def h2(text):
    p = para(text, size=13.5, bold=True, align="left", color=NAVY,
             space_before=8, space_after=4)
    p.paragraph_format.keep_with_next = True
    return p


def h3(text):
    p = para(text, size=13, bold=True, align="left", color=NAVY,
             space_before=6, space_after=3)
    p.paragraph_format.keep_with_next = True
    return p


def bullet(text, size=13, indent=0.8):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.left_indent = Cm(indent)
    p.paragraph_format.first_line_indent = Cm(-0.5)
    p.paragraph_format.space_after = Pt(3)
    _set_font(p.add_run("– " + text), size)
    return p


def _shade(cell, fill):
    el = OxmlElement("w:shd")
    el.set(qn("w:fill"), fill)
    cell._tc.get_or_add_tcPr().append(el)


def _repeat_header(row):
    trPr = row._tr.get_or_add_trPr()
    el = OxmlElement("w:tblHeader")
    el.set(qn("w:val"), "true")
    trPr.append(el)


def _tight_cell_margins(t):
    tblPr = t._tbl.tblPr
    mar = OxmlElement("w:tblCellMar")
    for side_, val in (("top", 8), ("left", 72), ("bottom", 8), ("right", 72)):
        e = OxmlElement(f"w:{side_}")
        e.set(qn("w:w"), str(val))
        e.set(qn("w:type"), "dxa")
        mar.append(e)
    tblPr.append(mar)


def table(headers, rows, widths=None, fs=9.5, first_col_bold=False,
          align_first="left"):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    _tight_cell_margins(t)
    total = Cm(16.0)
    if widths:
        s = sum(widths)
        widths = [Cm(16.0 * w / s) for w in widths]
    else:
        widths = [Cm(16.0 / len(headers))] * len(headers)

    hdr = t.rows[0]
    for j, htext in enumerate(headers):
        c = hdr.cells[j]
        c.width = widths[j]
        c.text = ""
        c.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        _shade(c, "D4E6F1")
        p = c.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(1)
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.line_spacing = 1.0
        _set_font(p.add_run(htext), fs, bold=True, color=NAVY)
    _repeat_header(hdr)

    for r in rows:
        cells = t.add_row().cells
        for j, val in enumerate(r):
            c = cells[j]
            c.width = widths[j]
            c.text = ""
            c.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            lines = str(val).split("\n")
            for k, line in enumerate(lines):
                p = c.paragraphs[0] if k == 0 else c.add_paragraph()
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.line_spacing = 1.0
                if j == 0:
                    p.alignment = (WD_ALIGN_PARAGRAPH.CENTER
                                   if align_first == "center"
                                   else WD_ALIGN_PARAGRAPH.LEFT)
                else:
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                bold = first_col_bold and j == 0
                if line.startswith("**") and line.endswith("**"):
                    line, bold = line[2:-2], True
                _set_font(p.add_run(line), fs, bold=bold)
    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_after = Pt(0)
    spacer.paragraph_format.space_before = Pt(0)
    spacer.paragraph_format.line_spacing = 1.0
    _set_font(spacer.add_run(""), 4)
    return t


FIG_N = [0]


def figure(name, width_in, caption):
    FIG_N[0] += 1
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(1)
    p.paragraph_format.line_spacing = 1.0
    p.add_run().add_picture(str(ASSETS / name), width=Inches(width_in))
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_after = Pt(6)
    cap.paragraph_format.line_spacing = 1.0
    _set_font(cap.add_run(f"Hình {FIG_N[0]}. {caption}"), 11, italic=True)


TAB_N = [0]


def tcap(caption):
    TAB_N[0] += 1
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(5)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.0
    _set_font(p.add_run(f"Bảng {TAB_N[0]}. {caption}"), 11, italic=True)


def footer_page_number():
    for s in doc.sections:
        p = s.footer.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run()
        _set_font(run, 11)
        for instr, val in (("begin", None), (None, "PAGE"), ("end", None)):
            if instr == "begin":
                f = OxmlElement("w:fldChar"); f.set(qn("w:fldCharType"), "begin")
            elif instr == "end":
                f = OxmlElement("w:fldChar"); f.set(qn("w:fldCharType"), "end")
            else:
                f = OxmlElement("w:instrText"); f.set(qn("xml:space"), "preserve")
                f.text = " PAGE "
            run._r.append(f)


para("TRƯỜNG ĐẠI HỌC MỞ THÀNH PHỐ HỒ CHÍ MINH", 13, True, align="center", space_after=2)
para("KHOA ĐÀO TẠO ĐẶC BIỆT", 13, True, align="center", space_after=60)
para("ĐỒ ÁN NGÀNH", 15, True, align="center", color=NAVY, space_after=4)
para("BÁO CÁO GIAI ĐOẠN 3", 14, True, align="center", color=NAVY, space_after=40)
para("PHÂN TÍCH HỆ THỐNG", 20, True, align="center", color=NAVY, space_after=14)
para("HỆ THỐNG PHÁT HIỆN TÉ NGÃ Ở NGƯỜI CAO TUỔI", 15, True, align="center", space_after=4)
para("Dựa trên camera và phân tích chuyển động", 13, italic=True, align="center", space_after=60)
para("Sinh viên thực hiện: Nguyễn Đinh Hồng Ngọc", 13, align="center", space_after=3)
para("Mã số sinh viên: 2351010139", 13, align="center", space_after=3)
para("Giảng viên hướng dẫn: TS. Nguyễn Tiến Đạt", 13, align="center", space_after=3)
para("Học kỳ 3 – Năm học 2025–2026", 13, align="center", space_after=40)
para("Thành phố Hồ Chí Minh – 2026", 13, align="center")

doc.add_page_break()
h1("MỤC LỤC")
muc_luc = [
    ("PHẦN MỞ ĐẦU", True),
    ("0.1. Mục đích và vai trò của giai đoạn phân tích", False),
    ("0.2. Phương pháp và công cụ mô hình hoá được chọn", False),
    ("0.3. Tính kế thừa từ báo cáo Khảo sát hiện trạng", False),
    ("0.4. Phạm vi và giới hạn của tài liệu", False),
    ("PHẦN I. PHÂN TÍCH YÊU CẦU HỆ THỐNG", True),
    ("1.1. Sơ đồ ngữ cảnh và phạm vi hệ thống", False),
    ("1.2. Danh sách tác nhân", False),
    ("1.3. Yêu cầu chức năng", False),
    ("1.4. Yêu cầu phi chức năng", False),
    ("1.5. Quy tắc nghiệp vụ", False),
    ("1.6. Giả định và ràng buộc", False),
    ("PHẦN II. MÔ HÌNH USE CASE", True),
    ("2.1. Sơ đồ use case tổng thể", False),
    ("2.2. Danh sách use case và mức ưu tiên", False),
    ("2.3. Đặc tả use case chi tiết", False),
    ("PHẦN III. MÔ HÌNH XỬ LÝ", True),
    ("3.1. Quy trình giám sát và phát hiện", False),
    ("3.2. Quy trình xác nhận và leo thang cảnh báo", False),
    ("3.3. Máy trạng thái của Sự kiện té ngã", False),
    ("3.4. Sơ đồ tuần tự: từ khung hình đến người tiếp nhận", False),
    ("3.5. Quy trình xử lý trạng thái giám sát hạn chế", False),
    ("PHẦN IV. MÔ HÌNH DỮ LIỆU", True),
    ("4.1. Sơ đồ lớp mức phân tích", False),
    ("4.2. Từ điển lớp và thuộc tính", False),
    ("4.3. Các mối kết hợp và bản số", False),
    ("4.4. Ràng buộc toàn vẹn mức phân tích", False),
    ("4.5. Vòng đời dữ liệu và ranh giới riêng tư", False),
    ("PHẦN V. PHÂN TÍCH BÀI TOÁN DỮ LIỆU VÀ LỰA CHỌN MÔ HÌNH", True),
    ("5.1. Phát biểu bài toán học máy", False),
    ("5.2. Mô tả dữ liệu nguồn", False),
    ("5.3. Đơn vị mẫu, cách gán nhãn và phân bố lớp", False),
    ("5.4. Đặc trưng đầu vào và các kênh bị loại bỏ", False),
    ("5.5. Nguyên tắc chia dữ liệu theo người", False),
    ("5.6. Phân tích và lựa chọn mô hình", False),
    ("5.7. Cấu hình mô hình đã chọn", False),
    ("5.8. Tiêu chí đánh giá ba mức", False),
    ("5.9. Rủi ro mô hình học tắt và bằng chứng thực nghiệm", False),
    ("5.10. Kết quả tiền khả thi và phân tích lỗi", False),
    ("5.11. Chuỗi tiền xử lý dữ liệu", False),
    ("PHẦN VI. KIẾN TRÚC HỆ THỐNG MỨC PHÂN TÍCH", True),
    ("6.1. Sơ đồ thành phần", False),
    ("6.2. Trách nhiệm của từng thành phần", False),
    ("6.3. Sơ đồ triển khai", False),
    ("PHẦN VII. MA TRẬN TRUY VẾT VÀ TIÊU CHÍ CHẤP NHẬN", True),
    ("7.1. Ma trận truy vết", False),
    ("7.2. Tiêu chí chấp nhận", False),
    ("7.3. Rủi ro còn lại và giả định cần kiểm chứng", False),
    ("PHẦN VIII. KẾT LUẬN VÀ CHUYỂN GIAO SANG GIAI ĐOẠN THIẾT KẾ", True),
    ("8.1. Tóm tắt kết quả phân tích", False),
    ("8.2. Những điểm cần bổ sung ngược về Khảo sát hiện trạng", False),
    ("8.3. Đầu vào bàn giao cho bước Thiết kế", False),
    ("TÀI LIỆU THAM KHẢO", True),
]
for text, is_bold in muc_luc:
    para(text, 11, bold=is_bold, align="left",
         indent=0 if is_bold else 0.7, space_after=0,
         space_before=2 if is_bold else 0)

doc.add_page_break()
h1("PHẦN MỞ ĐẦU")

h2("0.1. Mục đích và vai trò của giai đoạn phân tích")
para("Báo cáo Khảo sát hiện trạng ở giai đoạn trước đã mô tả bằng văn viết toàn bộ bối "
     "cảnh của bài toán: người cao tuổi sống một mình có nguy cơ nằm chờ nhiều giờ sau "
     "khi ngã mà không ai biết; các giải pháp hiện có (nút bấm khẩn cấp, thiết bị đeo, "
     "cảm biến môi trường, camera phân tích chuyển động) đều có khoảng trống; và phương "
     "án được chọn để tiếp tục là tự xây dựng một hệ thống xử lý cục bộ bằng camera. "
     "Toàn bộ thông tin đó đang tồn tại dưới dạng tường thuật — dễ đọc nhưng khó kiểm "
     "tra tính đầy đủ, khó đối chiếu và khó chuyển giao.")
para("Nhiệm vụ của giai đoạn Phân tích là chuyển khối thông tin tường thuật ấy thành các "
     "mô hình tóm tắt, có cấu trúc và kiểm tra được: ai dùng hệ thống, hệ thống phải làm "
     "được những gì, dữ liệu nào cần quản lý, các quy trình xử lý diễn ra theo trình tự "
     "nào, và bài toán học máy bên trong được phát biểu ra sao. Kết quả của giai đoạn "
     "này chưa phải là bản vẽ thi công; nó là bộ hình vẽ để cả người đặt hàng và người "
     "làm hệ thống cùng nhìn vào, cùng xác nhận rằng hai bên đang hiểu giống nhau, và "
     "cùng chỉ ra chỗ nào còn thiếu hoặc chưa hợp lý.")
para("Vì vậy, mọi thành phần trong báo cáo này đều truy ngược được về một nội dung đã có "
     "trong Khảo sát hiện trạng; ngược lại, những chỗ khảo sát còn thiếu được ghi ở mục 8.2.")

h2("0.2. Phương pháp và công cụ mô hình hoá được chọn")
para("Đề tài sử dụng phương pháp hướng đối tượng (OO) với ngôn ngữ mô hình hoá UML làm "
     "phương pháp chính, thay vì SADT. Lý do là bản chất của hệ thống này thiên về các "
     "đối tượng có trạng thái và vòng đời rõ rệt — một Sự kiện té ngã đi qua chuỗi "
     "trạng thái nghi ngờ, chờ xác nhận, leo thang, đã tiếp nhận, đã đóng — chứ không "
     "phải là một chuỗi biến đổi dữ liệu tuyến tính. UML cho phép diễn tả trực tiếp "
     "vòng đời đó bằng máy trạng thái, điều mà lược đồ dòng dữ liệu của SADT không làm "
     "tự nhiên được.")
para("Vì đề tài đồng thời là một bài toán phân tích dữ liệu, báo cáo bổ sung Phần V "
     "dành riêng cho việc mô tả dữ liệu, phát biểu bài toán học máy, so sánh và lựa "
     "chọn mô hình — đây là phần tương ứng với yêu cầu dành cho nhóm phân tích dữ liệu. "
     "Các mô hình được dùng trong báo cáo gồm:")
tcap("Các mô hình sử dụng trong báo cáo và mục đích của từng mô hình")
table(
    ["Mô hình", "Dùng để trả lời câu hỏi", "Xuất hiện tại"],
    [
        ["Sơ đồ ngữ cảnh", "Hệ thống nằm ở đâu, ranh giới đến đâu, ai và cái gì trao đổi thông tin với nó?", "Mục 1.1"],
        ["Sơ đồ use case", "Hệ thống cung cấp những khối chức năng nào, cho ai?", "Mục 2.1"],
        ["Đặc tả use case", "Mỗi chức năng diễn ra theo các bước nào, ngoại lệ ra sao?", "Mục 2.3"],
        ["Sơ đồ hoạt động", "Trình tự và các nhánh rẽ của một quy trình nghiệp vụ?", "Mục 3.1, 3.2"],
        ["Máy trạng thái", "Một sự kiện cảnh báo có thể ở những trạng thái nào, chuyển đổi khi nào?", "Mục 3.3"],
        ["Sơ đồ tuần tự", "Các thành phần trao đổi thông điệp với nhau theo thứ tự nào?", "Mục 3.4"],
        ["Sơ đồ lớp", "Hệ thống quản lý những đối tượng dữ liệu nào, quan hệ và bản số ra sao?", "Mục 4.1"],
        ["Sơ đồ thành phần và triển khai", "Phần mềm chia thành các khối nào, đặt trên thiết bị nào?", "Mục 6.1, 6.3"],
        ["Bảng phân tích dữ liệu và ma trận quyết định", "Dữ liệu có đặc điểm gì, vì sao chọn mô hình học máy này?", "Phần V"],
    ],
    widths=[3.0, 6.5, 2.2], first_col_bold=True)

h2("0.3. Tính kế thừa từ báo cáo Khảo sát hiện trạng")
para("Bảng dưới đây ánh xạ từng nội dung của báo cáo Khảo sát hiện trạng sang thành phần "
     "tương ứng trong báo cáo Phân tích. Bảng này cũng là cam kết rằng không có thực thể "
     "dữ liệu hay quy trình nào xuất hiện trong phân tích mà không có căn cứ ở khảo sát.")
tcap("Ánh xạ nội dung Khảo sát hiện trạng sang mô hình phân tích")
table(
    ["Nội dung trong Khảo sát hiện trạng", "Được chuyển thành", "Mục"],
    [
        ["A.1 Bối cảnh: khoảng trễ từ lúc ngã đến lúc được trợ giúp", "Mục tiêu chất lượng NFR-01 (độ trễ phát hiện) và tiêu chí đánh giá mức sự kiện", "1.4; 5.8"],
        ["A.2 Bốn nhóm người liên quan và nhu cầu của từng nhóm", "Bốn tác nhân trong sơ đồ ngữ cảnh và sơ đồ use case", "1.2; 2.1"],
        ["A.3 Hiện trạng phụ thuộc vào sự tình cờ", "UC-01 Giám sát và phát hiện té ngã (chạy liên tục, không cần thao tác)", "2.3"],
        ["A.5 Bốn ý tưởng: phát hiện chủ động, xử lý cục bộ, xác nhận tại chỗ, leo thang", "UC-01, UC-02, UC-03 và quy trình ở Phần III", "2.3; 3.1; 3.2"],
        ["A.6 Phương án xử lý cục bộ được chọn", "Sơ đồ thành phần và sơ đồ triển khai", "6.1; 6.3"],
        ["B.2 Chức năng theo vai trò", "Bảng yêu cầu chức năng FR-01 … FR-24", "1.3"],
        ["B.3 Bốn nhóm thông tin hệ thống cần quản lý", "Mười hai lớp trong sơ đồ lớp mức phân tích", "4.1; 4.2"],
        ["B.4.1 Giám sát và phát hiện; trạng thái « giám sát hạn chế »", "Sơ đồ hoạt động giám sát và bảng tình huống giám sát hạn chế", "3.1; 3.5"],
        ["B.4.2 Xác nhận và leo thang cảnh báo", "Sơ đồ hoạt động leo thang và máy trạng thái Sự kiện té ngã", "3.2; 3.3"],
        ["B.4.3 Phản hồi báo đúng / báo sai", "Lớp PhanHoiXuLy và UC-04", "2.3; 4.2"],
        ["B.5 Bốn yêu cầu chất lượng", "Bảng yêu cầu phi chức năng NFR-01 … NFR-12", "1.4"],
        ["C.1 Phát biểu bài toán dữ liệu", "Phát biểu bài toán học máy dạng hình thức", "5.1"],
        ["C.3, C.4 Nguồn dữ liệu và kiểm kê (12 người, 394 đoạn)", "Bảng mô tả dữ liệu nguồn và bảng phân bố cửa sổ", "5.2; 5.3"],
        ["C.5 Năm vấn đề cần xử lý trước khi học", "Chuỗi tiền xử lý và phân tích rủi ro học tắt", "5.9; 5.11"],
        ["C.6 Chia dữ liệu theo người và tiêu chí đánh giá", "Nguyên tắc chia dữ liệu và tiêu chí đánh giá ba mức", "5.5; 5.8"],
        ["D.2, D.3 Kết quả tiền khả thi và ba bài học", "Kết quả, phân tích lỗi và bảng thí nghiệm đối chứng", "5.9; 5.10"],
    ],
    widths=[5.2, 5.0, 1.5], fs=9.5)

h2("0.4. Phạm vi và giới hạn của tài liệu")
para("Tài liệu này dừng ở mức phân tích. Cụ thể, các nội dung sau đây thuộc giai đoạn "
     "Thiết kế và cố ý không được trình bày ở đây: lược đồ cơ sở dữ liệu vật lý sau khi "
     "chuẩn hoá về dạng chuẩn 3, kiểu dữ liệu và độ dài từng cột, mã giả chi tiết của "
     "từng thủ tục, bố cục màn hình và biểu mẫu, giao diện lập trình ứng dụng giữa các "
     "thành phần, cũng như kế hoạch kiểm thử chi tiết theo từng ca. Mục 8.3 liệt kê "
     "chính xác những gì bước Thiết kế sẽ nhận từ báo cáo này.")
para("Số liệu thực nghiệm trong Phần V lấy từ thử nghiệm tiền khả thi đã trình bày ở "
     "Khảo sát hiện trạng, chạy trên bộ UP-Fall Detection với hạt giống ngẫu nhiên cố "
     "định. Đây là dữ liệu diễn xuất trong phòng thí nghiệm: có giá trị định hướng lựa "
     "chọn mô hình nhưng không thay thế thử nghiệm tại nhà thật.")

h1("PHẦN I. PHÂN TÍCH YÊU CẦU HỆ THỐNG")

h2("1.1. Sơ đồ ngữ cảnh và phạm vi hệ thống")
para("Sơ đồ ngữ cảnh xác định ranh giới của hệ thống sẽ xây dựng. Bên trong ranh giới là "
     "phần mềm phát hiện té ngã và cảnh báo. Bên ngoài là bốn nhóm người dùng đã nhận "
     "diện trong khảo sát cùng hai hệ thống ngoài: camera IP (cung cấp hình ảnh) và dịch "
     "vụ thông báo (chuyển tin nhắn ra ngoài mạng nội bộ).")
figure("h01_ngu_canh.png", 5.6, "Sơ đồ ngữ cảnh của hệ thống phát hiện té ngã")
para("Hai ranh giới quan trọng cần nhấn mạnh. Thứ nhất, camera là hệ thống ngoài: hệ "
     "thống chỉ đọc luồng hình ảnh theo giao thức chuẩn, không chịu trách nhiệm về phần "
     "cứng camera. Thứ hai, dịch vụ thông báo cũng là hệ thống ngoài và chỉ nhận dữ liệu "
     "sự kiện (thời điểm, phòng, mức độ tin cậy), không nhận luồng video — đây là hệ quả "
     "trực tiếp của yêu cầu riêng tư đã nêu ở mục B.5 của Khảo sát hiện trạng.")

h2("1.2. Danh sách tác nhân")
para("Bốn nhóm người liên quan trong khảo sát trở thành bốn tác nhân chính. Camera được "
     "mô hình hoá thành một tác nhân phụ vì nó chủ động đẩy dữ liệu vào hệ thống chứ "
     "không chỉ là một thiết bị thụ động.")
tcap("Danh sách tác nhân và trách nhiệm")
table(
    ["Mã", "Tác nhân", "Mô tả và trách nhiệm chính", "Nguồn (KSHT)"],
    [
        ["TN-01", "Người cao tuổi\n(người được giám sát)", "Đối tượng được hệ thống theo dõi. Không phải thao tác gì để hệ thống hoạt động. Có thể xác nhận mình an toàn bằng một hành động đơn giản (đứng dậy hoặc bấm nút « Tôi ổn »).", "A.2"],
        ["TN-02", "Người thân /\nngười chăm sóc", "Nhận cảnh báo, xác nhận đã tiếp nhận, xem thông tin sự kiện, đánh dấu cảnh báo sai, xem lại lịch sử.", "A.2, B.2"],
        ["TN-03", "Nhân viên trực /\nđiều dưỡng", "Theo dõi nhiều phòng cùng lúc, sắp xếp ưu tiên cảnh báo, ghi nhận kết quả xử lý và bàn giao ca trực.", "A.2, B.2"],
        ["TN-04", "Kỹ thuật viên", "Khai báo người – phòng – camera, kiểm tra vùng quan sát, cấu hình quy tắc cảnh báo, theo dõi tình trạng thiết bị và hiệu chỉnh khi xuất hiện cảnh báo sai.", "A.2, B.2"],
        ["TN-05", "Camera IP\n(tác nhân phụ)", "Cung cấp luồng hình ảnh liên tục. Việc mất kết nối của tác nhân này là một sự kiện nghiệp vụ, không phải lỗi kỹ thuật im lặng.", "B.1, B.4.4"],
        ["TN-06", "Dịch vụ thông báo\n(hệ thống ngoài)", "Chuyển thông điệp cảnh báo tới người nhận qua tin nhắn, thông báo đẩy hoặc thư điện tử.", "B.4.2"],
    ],
    widths=[1.0, 2.6, 6.8, 1.4], fs=9.5)

h2("1.3. Yêu cầu chức năng")
para("Bảng yêu cầu chức năng được rút ra từ mục B.2 (chức năng theo vai trò) và các quy "
     "trình ở mục B.4 của Khảo sát hiện trạng. Cột cuối cùng ghi mức ưu tiên theo quy "
     "ước: B (bắt buộc — thiếu thì hệ thống không dùng được), N (nên có), C (có thể lùi "
     "sang giai đoạn mở rộng).")
tcap("Yêu cầu chức năng của hệ thống")
table(
    ["Mã", "Yêu cầu chức năng", "Tác nhân", "Ưu tiên"],
    [
        ["FR-01", "Đọc liên tục luồng hình ảnh từ một hoặc nhiều camera đã khai báo.", "TN-05", "B"],
        ["FR-02", "Phát hiện người trong khung hình và trích xuất toạ độ các khớp cơ thể.", "Hệ thống", "B"],
        ["FR-03", "Bám nhất quán một người cần giám sát qua các khung hình liên tiếp, kể cả khi khung hình có nhiều người.", "Hệ thống", "B"],
        ["FR-04", "Đánh giá chuỗi tư thế trong một cửa sổ thời gian ngắn và tính mức độ tin cậy của khả năng té ngã.", "Hệ thống", "B"],
        ["FR-05", "Tạo Sự kiện té ngã khi mức tin cậy vượt ngưỡng trong số lần liên tiếp đã cấu hình.", "Hệ thống", "B"],
        ["FR-06", "Phát âm báo và tín hiệu tại chỗ, đồng thời bắt đầu đếm ngược thời gian chờ xác nhận.", "TN-01", "B"],
        ["FR-07", "Cho phép người được giám sát tự xác nhận an toàn bằng hành động đơn giản; khi đó hạ mức sự kiện và lưu vào lịch sử.", "TN-01", "B"],
        ["FR-08", "Gửi cảnh báo cho người liên hệ theo thứ tự đã cấu hình, kèm thời điểm, phòng, mức tin cậy và ảnh minh hoạ được phép.", "TN-02, TN-03", "B"],
        ["FR-09", "Chuyển cảnh báo sang người liên hệ kế tiếp khi người hiện tại không xác nhận trong thời hạn.", "Hệ thống", "B"],
        ["FR-10", "Duy trì cảnh báo ở mức cao và thực hiện chỉ dẫn đã thống nhất trước khi hết danh sách liên hệ mà chưa ai tiếp nhận.", "Hệ thống", "B"],
        ["FR-11", "Cho phép người nhận xác nhận đã tiếp nhận cảnh báo; ghi lại người xác nhận và thời điểm.", "TN-02, TN-03", "B"],
        ["FR-12", "Cho phép ghi nhận kết quả xử lý: sự cố thật hoặc cảnh báo sai, kèm ghi chú.", "TN-02, TN-03", "B"],
        ["FR-13", "Lưu và cho phép tra cứu lịch sử sự kiện theo người, phòng, khoảng thời gian và trạng thái.", "TN-02, TN-03", "B"],
        ["FR-14", "Khai báo và quản lý danh sách người được giám sát, phòng và camera.", "TN-04", "B"],
        ["FR-15", "Khai báo vùng quan sát trên khung hình camera, bao gồm vùng giường/ghế và vùng loại trừ.", "TN-04", "N"],
        ["FR-16", "Cấu hình quy tắc cảnh báo: ngưỡng tin cậy, số lần liên tiếp, thời gian chờ xác nhận, khung giờ áp dụng.", "TN-04", "B"],
        ["FR-17", "Cấu hình danh sách và thứ tự người nhận cảnh báo cùng thời hạn phản hồi của từng bậc.", "TN-04", "B"],
        ["FR-18", "Lưu lịch sử thay đổi cấu hình để đối chiếu khi phân tích một sự cố đã qua.", "TN-04", "N"],
        ["FR-19", "Phát hiện và ghi nhận trạng thái « giám sát hạn chế » khi mất kết nối camera, mất điện, ảnh quá tối hoặc người bị che khuất quá nhiều.", "Hệ thống", "B"],
        ["FR-20", "Hiển thị trạng thái giám sát và tình trạng thiết bị trên màn hình quản trị, kèm thời điểm bắt đầu và kết thúc của mỗi khoảng hạn chế.", "TN-03, TN-04", "B"],
        ["FR-21", "Xếp thứ tự ưu tiên các cảnh báo đang mở khi nhân viên trực theo dõi nhiều phòng.", "TN-03", "N"],
        ["FR-22", "Cho phép bàn giao ca trực: đánh dấu các sự kiện chưa đóng và người tiếp nhận mới.", "TN-03", "C"],
        ["FR-23", "Hàng đợi thông báo: giữ lại và gửi lại khi kết nối ra ngoài được khôi phục.", "Hệ thống", "N"],
        ["FR-24", "Không tự động gọi cơ quan y tế khẩn cấp, trừ khi chủ sở hữu đã thiết lập trước và được phép theo quy định áp dụng.", "Hệ thống", "B"],
    ],
    widths=[1.0, 8.0, 1.7, 1.0], fs=9.5)

h2("1.4. Yêu cầu phi chức năng")
para("Bốn yêu cầu chất lượng ở mục B.5 của Khảo sát hiện trạng được cụ thể hoá thành các "
     "yêu cầu có thể đo được. Các con số trong cột « Chỉ tiêu » là mục tiêu đặt ra cho "
     "giai đoạn này; một số chỉ tiêu đã có kết quả đo sơ bộ ở Phần V, số còn lại sẽ được "
     "đo ở giai đoạn thi công.")
tcap("Yêu cầu phi chức năng")
table(
    ["Mã", "Nhóm", "Yêu cầu và chỉ tiêu", "Cách kiểm chứng"],
    [
        ["NFR-01", "Hiệu năng", "Độ trễ từ lúc kết thúc cú ngã đến lúc tạo cảnh báo không quá 3 giây.", "Đo trên tập đoạn video kiểm thử có mốc thời gian ngã."],
        ["NFR-02", "Hiệu năng", "Xử lý được ít nhất 15 khung hình mỗi giây cho một camera trên phần cứng dự kiến.", "Đo số khung hình xử lý mỗi giây khi chạy liên tục 30 phút."],
        ["NFR-03", "Độ chính xác", "Tỷ lệ phát hiện ca ngã ở mức sự kiện đạt tối thiểu 90%.", "Chạy lại toàn bộ đoạn video của tập kiểm thử độc lập."],
        ["NFR-04", "Độ chính xác", "Số cảnh báo sai không vượt quá 1 lần cho mỗi phòng trong 24 giờ giám sát liên tục.", "Đo trên dữ liệu sinh hoạt bình thường dài ngày."],
        ["NFR-05", "Độ tin cậy", "Chức năng phát hiện tiếp tục hoạt động khi mất kết nối Internet; thông báo được gửi lại khi kết nối khôi phục.", "Ngắt mạng có chủ đích trong khi chạy thử."],
        ["NFR-06", "Độ tin cậy", "Mọi khoảng thời gian giám sát bị hạn chế đều được ghi nhận và hiển thị, không được im lặng bỏ qua.", "Rút cáp camera, che ống kính, tắt đèn và kiểm tra nhật ký."],
        ["NFR-07", "Riêng tư", "Video thô không được truyền ra khỏi máy xử lý tại chỗ; chỉ dữ liệu sự kiện được gửi đi.", "Rà soát lưu lượng mạng đi ra trong một phiên chạy thử."],
        ["NFR-08", "Riêng tư", "Ảnh minh hoạ kèm cảnh báo chỉ được lưu khi có sự kiện và chỉ giữ trong thời hạn đã cấu hình.", "Kiểm tra kho lưu trữ sau khi hết thời hạn."],
        ["NFR-09", "Riêng tư", "Dữ liệu tư thế được ưu tiên lưu thay cho ảnh gốc.", "Rà soát nội dung kho dữ liệu cục bộ."],
        ["NFR-10", "Bảo mật", "Chỉ người có thẩm quyền được xem thông tin người được giám sát và lịch sử sự kiện.", "Thử truy cập bằng tài khoản không có quyền."],
        ["NFR-11", "Khả dụng", "Người cao tuổi không phải đeo, sạc hay thao tác với bất kỳ thiết bị nào để được bảo vệ.", "Rà soát lại luồng thao tác của tác nhân TN-01."],
        ["NFR-12", "Khả bảo trì", "Toàn bộ tham số vận hành tập trung ở một nơi khai báo, không rải rác trong mã nguồn.", "Rà soát cấu hình khi thay đổi ngưỡng."],
    ],
    widths=[1.0, 1.5, 6.5, 4.0], fs=9.5)

h2("1.5. Quy tắc nghiệp vụ")
para("Quy tắc nghiệp vụ là những luật cố định mà hệ thống phải tuân theo, tách riêng khỏi "
     "phần học máy. Khảo sát hiện trạng ở mục C.1 đã nêu rõ nguyên tắc: chỉ dùng học máy "
     "cho việc nhận biết chuyển động, còn thứ tự leo thang, vùng giám sát, danh sách "
     "người nhận và kiểm tra mất kết nối phải được xử lý bằng quy tắc rõ ràng, dễ kiểm "
     "soát. Bảng dưới đây hình thức hoá các quy tắc đó.")
tcap("Quy tắc nghiệp vụ")
table(
    ["Mã", "Nội dung quy tắc", "Tham số"],
    [
        ["BR-01", "Một sự kiện té ngã chỉ được tạo khi xác suất té ngã đạt hoặc vượt ngưỡng trong số lần suy luận liên tiếp đã cấu hình.", "ngưỡng = 0,85; số lần liên tiếp = 2"],
        ["BR-02", "Mô hình được chạy lại sau mỗi khoảng cố định số khung hình, trên cửa sổ các khung hình gần nhất.", "chạy mỗi 4 khung; cửa sổ 32 khung"],
        ["BR-03", "Sau khi tạo sự kiện, hệ thống luôn phát âm báo tại chỗ trước, rồi mới báo ra ngoài.", "thời gian chờ mặc định 20 giây"],
        ["BR-04", "Nếu người được giám sát phản hồi trong thời hạn chờ, sự kiện được hạ mức và ghi vào lịch sử, không gửi ra ngoài.", "—"],
        ["BR-05", "Khi không có phản hồi, cảnh báo được gửi lần lượt theo thứ tự ưu tiên trong danh sách người liên hệ.", "mỗi bậc chờ 120 giây"],
        ["BR-06", "Khi hết danh sách liên hệ mà chưa ai xác nhận, sự kiện giữ ở mức cao và hệ thống thực hiện chỉ dẫn đã thống nhất trước với hộ gia đình hoặc cơ sở.", "—"],
        ["BR-07", "Nếu khung hình có nhiều người và độ tin cậy gán sự cố cho một người không đủ, hệ thống chuyển sang trạng thái cần kiểm tra thay vì tự gán.", "—"],
        ["BR-08", "Cửa sổ có tỷ lệ khung hình phát hiện được người dưới ngưỡng tối thiểu thì không được dùng để kết luận.", "tối thiểu 50% số khung"],
        ["BR-09", "Vùng được khai báo là vùng loại trừ không sinh cảnh báo; vùng giường và ghế được áp dụng quy tắc riêng.", "—"],
        ["BR-10", "Hệ thống không tự quyết định gọi cơ quan y tế khẩn cấp.", "—"],
        ["BR-11", "Mọi chuyển trạng thái của sự kiện đều được ghi nhật ký kèm thời điểm và người thực hiện.", "—"],
        ["BR-12", "Khi camera mất kết nối hoặc điều kiện quan sát không bảo đảm, hệ thống chuyển sang trạng thái giám sát hạn chế và hiển thị công khai trạng thái đó.", "—"],
    ],
    widths=[1.0, 8.2, 2.8], fs=9.5)

h2("1.6. Giả định và ràng buộc")
para("Các giả định dưới đây được nêu rõ để nếu về sau chúng không đúng, cả hai bên biết "
     "phải xem lại phần nào của hệ thống.")
bullet("Mỗi phòng có ít nhất một camera đặt ở vị trí bao quát được khu vực sinh hoạt "
       "chính; hệ thống không giả định có nhiều góc quay đồng bộ như trong phòng thí nghiệm.")
bullet("Máy xử lý đặt tại nơi lắp đặt và luôn được cấp điện; trường hợp mất điện thuộc "
       "phạm vi trạng thái giám sát hạn chế chứ không phải hoạt động bình thường.")
bullet("Mạng nội bộ hoạt động ổn định giữa camera và máy xử lý; kết nối ra Internet có "
       "thể gián đoạn mà không làm mất chức năng phát hiện.")
bullet("Trong một phòng, tại một thời điểm thường chỉ có một người được giám sát. Trường "
       "hợp nhiều người là ngoại lệ và được xử lý theo quy tắc BR-07.")
bullet("Dữ liệu huấn luyện giai đoạn này là dữ liệu diễn xuất có kiểm soát; hệ thống phải "
       "được đánh giá lại khi có dữ liệu gần bối cảnh nhà thật.")
bullet("Người cao tuổi không bị yêu cầu đeo hay sạc thiết bị; nút gọi trợ giúp (nếu có) "
       "chỉ là kênh bổ sung, không phải điều kiện để hệ thống hoạt động.")

h1("PHẦN II. MÔ HÌNH USE CASE")

h2("2.1. Sơ đồ use case tổng thể")
para("Tám use case được chia thành hai nhóm. Nhóm vận hành thời gian thực (UC-01 đến "
     "UC-04) mô tả chuỗi việc xảy ra khi có nguy cơ té ngã; nhóm quản trị và tra cứu "
     "(UC-05 đến UC-08) mô tả các việc người dùng chủ động thực hiện.")
figure("h02_use_case.png", 5.5, "Sơ đồ use case tổng thể của hệ thống")
para("Ba quan hệ giữa các use case cần lưu ý. UC-01 luôn bao hàm (« include ») UC-02: "
     "mỗi lần nghi ngờ té ngã, hệ thống bắt buộc phải phát âm báo và chờ xác nhận tại "
     "chỗ trước, không được báo thẳng ra ngoài. UC-03 mở rộng (« extend ») UC-02: leo "
     "thang chỉ xảy ra khi điều kiện « không có phản hồi trong thời hạn » được thoả. "
     "UC-03 lại bao hàm UC-04 vì một cảnh báo đã gửi đi luôn cần được tiếp nhận và ghi "
     "nhận kết quả.")

h2("2.2. Danh sách use case và mức ưu tiên")
tcap("Danh sách use case")
table(
    ["Mã", "Tên use case", "Tác nhân chính", "Yêu cầu liên quan", "Ưu tiên"],
    [
        ["UC-01", "Giám sát và phát hiện té ngã", "Camera (TN-05)", "FR-01 … FR-05, FR-19", "B"],
        ["UC-02", "Xác nhận tại chỗ", "Người cao tuổi (TN-01)", "FR-06, FR-07", "B"],
        ["UC-03", "Leo thang cảnh báo", "Hệ thống", "FR-08, FR-09, FR-10, FR-23", "B"],
        ["UC-04", "Tiếp nhận và phản hồi cảnh báo", "Người thân, nhân viên trực", "FR-11, FR-12, FR-21", "B"],
        ["UC-05", "Xem lịch sử sự kiện", "Người thân, nhân viên trực", "FR-13", "B"],
        ["UC-06", "Khai báo người – phòng – camera", "Kỹ thuật viên", "FR-14, FR-15", "B"],
        ["UC-07", "Cấu hình quy tắc cảnh báo", "Kỹ thuật viên", "FR-16, FR-17, FR-18", "B"],
        ["UC-08", "Theo dõi trạng thái giám sát", "Nhân viên trực, kỹ thuật viên", "FR-19, FR-20", "B"],
    ],
    widths=[1.0, 3.6, 3.0, 3.4, 1.0], fs=9.5)

h2("2.3. Đặc tả use case chi tiết")
para("Bốn use case thuộc nhóm vận hành thời gian thực được đặc tả đầy đủ vì chúng chứa "
     "phần lớn logic nghiệp vụ và các ngoại lệ. Bốn use case còn lại được đặc tả rút gọn.")

h3("UC-01. Giám sát và phát hiện té ngã")
table(
    ["Mục", "Nội dung"],
    [
        ["Mã và tên", "UC-01 — Giám sát và phát hiện té ngã"],
        ["Tác nhân chính", "Camera IP (TN-05); hệ thống chạy tự động, không cần người khởi động"],
        ["Mục tiêu", "Nhận biết sớm một sự kiện té ngã từ diễn biến tư thế người trong khung hình"],
        ["Điều kiện trước", "Camera đã được khai báo và đang kết nối; quy tắc cảnh báo của phòng đã có hiệu lực"],
        ["Kích hoạt", "Hệ thống khởi động hoặc camera bắt đầu gửi hình ảnh"],
        ["Luồng chính",
         "1. Hệ thống đọc khung hình từ camera.\n"
         "2. Nếu không phát hiện người, hệ thống ghi nhận trạng thái phòng trống và quay lại bước 1.\n"
         "3. Hệ thống trích xuất toạ độ các khớp cơ thể của người trong khung hình.\n"
         "4. Hệ thống xác định đúng người cần giám sát dựa trên vị trí ở khung hình trước, bảo đảm chuỗi tư thế thuộc về một người duy nhất.\n"
         "5. Hệ thống nội suy các khớp bị che và đưa khung xương vào bộ đệm 32 khung hình gần nhất.\n"
         "6. Sau mỗi 4 khung hình, hệ thống chuẩn hoá cửa sổ hiện tại và tính xác suất té ngã.\n"
         "7. Nếu xác suất đạt ngưỡng trong số lần liên tiếp đã cấu hình (BR-01), hệ thống tạo Sự kiện té ngã ở trạng thái « Nghi ngờ » và chuyển sang UC-02.\n"
         "8. Nếu không, hệ thống ghi nhận trạng thái bình thường và quay lại bước 1."],
        ["Luồng thay thế",
         "4a. Khung hình có nhiều người và không xác định được người cần giám sát với độ tin cậy đủ: hệ thống chuyển sang trạng thái cần kiểm tra (BR-07), ghi nhật ký và không tạo sự kiện.\n"
         "6a. Cửa sổ có dưới 50% số khung hình phát hiện được người: bỏ qua cửa sổ, không kết luận (BR-08).\n"
         "7a. Người đang nằm trong vùng giường đã khai báo: áp dụng quy tắc riêng của vùng, không sinh cảnh báo (BR-09)."],
        ["Ngoại lệ",
         "E1. Mất kết nối camera: chuyển trạng thái « giám sát hạn chế », ghi thời điểm bắt đầu, thông báo cho màn hình quản trị (xem mục 3.5).\n"
         "E2. Ảnh quá tối hoặc vùng quan sát bị che khuất kéo dài: xử lý như E1.\n"
         "E3. Máy xử lý quá tải, không kịp tốc độ khung hình: giảm tải có kiểm soát và ghi nhật ký hiệu năng."],
        ["Điều kiện sau", "Hoặc một Sự kiện té ngã được tạo, hoặc trạng thái quan sát của phiên giám sát được cập nhật"],
        ["Tần suất", "Liên tục, khoảng 18 lần suy luận mỗi giây cho mỗi camera"],
        ["Quy tắc áp dụng", "BR-01, BR-02, BR-07, BR-08, BR-09, BR-12"],
    ],
    widths=[2.3, 9.7], fs=9.5, first_col_bold=True)

h3("UC-02. Xác nhận tại chỗ")
table(
    ["Mục", "Nội dung"],
    [
        ["Mã và tên", "UC-02 — Xác nhận tại chỗ"],
        ["Tác nhân chính", "Người cao tuổi (TN-01)"],
        ["Mục tiêu", "Cho người được giám sát cơ hội tự báo mình an toàn trước khi làm phiền người chăm sóc"],
        ["Điều kiện trước", "Đã có một Sự kiện té ngã ở trạng thái « Nghi ngờ »"],
        ["Kích hoạt", "UC-01 tạo sự kiện nghi ngờ"],
        ["Luồng chính",
         "1. Hệ thống phát âm báo và tín hiệu ánh sáng tại chỗ.\n"
         "2. Hệ thống bật đồng hồ đếm ngược theo thời gian chờ đã cấu hình.\n"
         "3. Người được giám sát đứng dậy hoặc bấm nút « Tôi ổn ».\n"
         "4. Hệ thống nhận phản hồi, chuyển sự kiện sang trạng thái « Đã tự xác nhận an toàn ».\n"
         "5. Hệ thống ghi sự kiện vào lịch sử để tham khảo và không gửi cảnh báo ra ngoài."],
        ["Luồng thay thế",
         "3a. Hệ thống tự nhận biết người đã đứng dậy trở lại từ diễn biến tư thế: coi như phản hồi hợp lệ."],
        ["Ngoại lệ",
         "E1. Hết thời gian chờ mà không có phản hồi: chuyển sang UC-03 (leo thang).\n"
         "E2. Loa hoặc đèn báo tại chỗ không hoạt động: ghi nhật ký thiết bị và rút ngắn thời gian chờ về không, chuyển thẳng sang UC-03."],
        ["Điều kiện sau", "Sự kiện được hạ mức và đóng, hoặc chuyển sang trạng thái leo thang"],
        ["Quy tắc áp dụng", "BR-03, BR-04, BR-11"],
    ],
    widths=[2.3, 9.7], fs=9.5, first_col_bold=True)

h3("UC-03. Leo thang cảnh báo")
table(
    ["Mục", "Nội dung"],
    [
        ["Mã và tên", "UC-03 — Leo thang cảnh báo"],
        ["Tác nhân chính", "Hệ thống (tự động); tác nhân phụ: dịch vụ thông báo (TN-06)"],
        ["Mục tiêu", "Bảo đảm luôn có người tiếp nhận cảnh báo, không để cảnh báo rơi vào khoảng trống"],
        ["Điều kiện trước", "Sự kiện té ngã không được xác nhận tại chỗ trong thời hạn"],
        ["Kích hoạt", "Ngoại lệ E1 của UC-02"],
        ["Luồng chính",
         "1. Hệ thống lấy danh sách người nhận cảnh báo theo thứ tự ưu tiên của phòng.\n"
         "2. Hệ thống gửi cảnh báo cho người liên hệ ở bậc hiện tại, kèm thời điểm, phòng, mức độ tin cậy và ảnh minh hoạ được phép.\n"
         "3. Hệ thống bật đồng hồ chờ phản hồi của bậc đó.\n"
         "4. Nếu người liên hệ xác nhận đã tiếp nhận, sự kiện chuyển sang trạng thái « Đã tiếp nhận » và chuyển sang UC-04.\n"
         "5. Nếu hết thời hạn mà không có xác nhận, hệ thống chuyển sang bậc kế tiếp và lặp lại từ bước 2."],
        ["Luồng thay thế",
         "2a. Không có kết nối ra Internet: hệ thống đưa thông báo vào hàng đợi, tiếp tục phát âm báo tại chỗ và gửi lại khi kết nối được khôi phục (FR-23)."],
        ["Ngoại lệ",
         "E1. Hết danh sách liên hệ mà chưa ai xác nhận: sự kiện giữ ở mức cao, hệ thống thực hiện chỉ dẫn đã thống nhất trước và tiếp tục ghi nhật ký (BR-06).\n"
         "E2. Dịch vụ thông báo trả về lỗi gửi: ghi nhận trạng thái gửi thất bại, thử lại theo số lần đã cấu hình rồi mới chuyển bậc."],
        ["Điều kiện sau", "Sự kiện ở trạng thái « Đã tiếp nhận » hoặc vẫn ở mức cao chờ xử lý; mọi lần gửi đều được lưu"],
        ["Quy tắc áp dụng", "BR-05, BR-06, BR-10, BR-11"],
    ],
    widths=[2.3, 9.7], fs=9.5, first_col_bold=True)

h3("UC-04. Tiếp nhận và phản hồi cảnh báo")
table(
    ["Mục", "Nội dung"],
    [
        ["Mã và tên", "UC-04 — Tiếp nhận và phản hồi cảnh báo"],
        ["Tác nhân chính", "Người thân (TN-02), nhân viên trực (TN-03)"],
        ["Mục tiêu", "Khép kín vòng cảnh báo và thu thập phản hồi để hiệu chỉnh hệ thống"],
        ["Điều kiện trước", "Người dùng đã nhận được một cảnh báo đang mở"],
        ["Kích hoạt", "Người dùng mở thông báo hoặc màn hình danh sách cảnh báo"],
        ["Luồng chính",
         "1. Người dùng xem thông tin sự kiện: thời điểm, phòng, người được giám sát, mức độ tin cậy, ảnh minh hoạ.\n"
         "2. Người dùng bấm xác nhận đã tiếp nhận; hệ thống ghi lại người xác nhận và thời điểm, dừng leo thang.\n"
         "3. Sau khi kiểm tra thực tế, người dùng ghi nhận kết quả: sự cố thật hoặc cảnh báo sai, kèm ghi chú.\n"
         "4. Hệ thống chuyển sự kiện sang trạng thái « Đã đóng » và lưu phản hồi."],
        ["Luồng thay thế",
         "1a. Nhân viên trực đang có nhiều cảnh báo mở: hệ thống sắp xếp theo mức độ tin cậy và thời gian chờ (FR-21).\n"
         "3a. Người dùng chưa kết luận được ngay: sự kiện giữ trạng thái « Đã tiếp nhận » và xuất hiện trong danh sách bàn giao ca."],
        ["Ngoại lệ",
         "E1. Hai người cùng xác nhận gần như đồng thời: hệ thống ghi nhận người xác nhận đầu tiên và thông báo cho người còn lại rằng cảnh báo đã có người tiếp nhận."],
        ["Điều kiện sau", "Sự kiện đã đóng, phản hồi đã được lưu và sẵn sàng dùng cho việc hiệu chỉnh"],
        ["Quy tắc áp dụng", "BR-11"],
    ],
    widths=[2.3, 9.7], fs=9.5, first_col_bold=True)

h3("UC-05 đến UC-08 (đặc tả rút gọn)")
tcap("Đặc tả rút gọn các use case quản trị và tra cứu")
table(
    ["Mã", "Luồng chính", "Ngoại lệ chính"],
    [
        ["UC-05\nXem lịch sử sự kiện",
         "1. Người dùng chọn tiêu chí lọc: người được giám sát, phòng, khoảng thời gian, trạng thái.\n"
         "2. Hệ thống hiển thị danh sách sự kiện kèm kết quả xử lý.\n"
         "3. Người dùng mở một sự kiện để xem chi tiết diễn biến và các lần gửi thông báo.",
         "Người dùng không đủ quyền xem thông tin của người được giám sát: hệ thống chỉ hiển thị thông tin đã ẩn danh."],
        ["UC-06\nKhai báo người – phòng – camera",
         "1. Kỹ thuật viên khai báo phòng và người được giám sát ở phòng đó.\n"
         "2. Kỹ thuật viên thêm camera, nhập đường dẫn luồng và kiểm tra hình ảnh thu được.\n"
         "3. Kỹ thuật viên vẽ vùng quan sát, vùng giường/ghế và vùng loại trừ trên khung hình mẫu.\n"
         "4. Hệ thống lưu cấu hình và bắt đầu phiên giám sát.",
         "Không kết nối được camera khi kiểm tra: hệ thống báo lỗi rõ ràng và không cho lưu trạng thái « đang giám sát »."],
        ["UC-07\nCấu hình quy tắc cảnh báo",
         "1. Kỹ thuật viên chọn phòng cần cấu hình.\n"
         "2. Kỹ thuật viên đặt ngưỡng tin cậy, số lần liên tiếp, thời gian chờ xác nhận và khung giờ áp dụng.\n"
         "3. Kỹ thuật viên sắp xếp danh sách người nhận cảnh báo và thời hạn phản hồi từng bậc.\n"
         "4. Hệ thống lưu bản cấu hình mới kèm thời điểm hiệu lực, giữ lại bản cũ trong lịch sử.",
         "Danh sách người nhận rỗng: hệ thống không cho lưu vì sẽ tạo ra cảnh báo không đến được ai."],
        ["UC-08\nTheo dõi trạng thái giám sát",
         "1. Người dùng mở màn hình tổng quan các phòng.\n"
         "2. Hệ thống hiển thị với mỗi phòng: trạng thái giám sát, tình trạng camera, thời điểm cập nhật gần nhất.\n"
         "3. Người dùng mở nhật ký thiết bị của một phòng để xem các khoảng giám sát hạn chế đã xảy ra.",
         "Máy xử lý không phản hồi: màn hình hiển thị rõ « không rõ trạng thái » thay vì hiển thị trạng thái cũ."],
    ],
    widths=[2.6, 7.0, 3.4], fs=9.5, first_col_bold=True)

h1("PHẦN III. MÔ HÌNH XỬ LÝ")

h2("3.1. Quy trình giám sát và phát hiện")
para("Sơ đồ hoạt động dưới đây chi tiết hoá luồng chính của UC-01. Điểm cần chú ý là "
     "nhánh bên trái: khi kết quả là « không phát hiện té ngã », hệ thống không mặc "
     "nhiên coi mọi thứ đều bình thường mà còn phải kiểm tra điều kiện quan sát. Đây là "
     "cách hình thức hoá yêu cầu « không tạo cảm giác an toàn giả » ở mục B.5 của Khảo "
     "sát hiện trạng.")
figure("h03_hoat_dong_phat_hien.png", 3.7,
       "Sơ đồ hoạt động của quy trình giám sát và phát hiện té ngã")

h2("3.2. Quy trình xác nhận và leo thang cảnh báo")
para("Sơ đồ hoạt động có phân làn dưới đây thể hiện rõ trách nhiệm của từng bên trong "
     "chuỗi UC-02 → UC-03 → UC-04. Ba làn tương ứng ba chủ thể: hệ thống, người được "
     "giám sát và người nhận cảnh báo. Hai điểm quyết định (« Có phản hồi trong thời "
     "hạn? » và « Xác nhận tiếp nhận trong thời hạn? ») chính là hai đồng hồ đếm ngược "
     "được cấu hình ở UC-07.")
figure("h04_hoat_dong_leo_thang.png", 5.8,
       "Sơ đồ hoạt động của quy trình xác nhận tại chỗ và leo thang cảnh báo")
para("Cần phân biệt rõ hai loại thời hạn để tránh nhầm lẫn khi thiết kế: thời gian chờ "
     "xác nhận tại chỗ (áp dụng một lần, cho người được giám sát) và thời hạn phản hồi "
     "của mỗi bậc leo thang (áp dụng lặp lại, cho từng người nhận cảnh báo). Hai tham số "
     "này thuộc hai lớp dữ liệu khác nhau: tham số thứ nhất nằm ở lớp QuyTacCanhBao, "
     "tham số thứ hai nằm ở lớp ThuTuLeoThang.")

h2("3.3. Máy trạng thái của Sự kiện té ngã")
para("Sự kiện té ngã là đối tượng trung tâm của hệ thống. Việc mô hình hoá vòng đời của "
     "nó bằng máy trạng thái giúp trả lời chính xác câu hỏi mà nhân viên trực quan tâm "
     "nhất: cảnh báo này đang ở đâu trong quy trình, và đã có người tiếp nhận hay chưa.")
figure("h05_trang_thai_su_kien.png", 5.8, "Máy trạng thái của đối tượng Sự kiện té ngã")
tcap("Bảng chuyển trạng thái của Sự kiện té ngã")
table(
    ["Trạng thái hiện tại", "Sự kiện kích hoạt", "Điều kiện", "Trạng thái tiếp theo"],
    [
        ["(khởi tạo)", "Vượt ngưỡng tin cậy", "BR-01 thoả", "Nghi ngờ"],
        ["Nghi ngờ", "Phát âm báo tại chỗ", "Loa/đèn hoạt động", "Chờ xác nhận tại chỗ"],
        ["Chờ xác nhận tại chỗ", "Người phản hồi", "Trong thời gian chờ", "Đã tự xác nhận an toàn"],
        ["Chờ xác nhận tại chỗ", "Hết thời gian chờ", "Không có phản hồi", "Đang leo thang"],
        ["Đang leo thang", "Hết thời hạn của bậc", "Còn người liên hệ kế tiếp", "Đang leo thang (bậc kế tiếp)"],
        ["Đang leo thang", "Người nhận xác nhận", "—", "Đã tiếp nhận"],
        ["Đang leo thang", "Hết danh sách liên hệ", "Chưa ai xác nhận", "Đang leo thang (mức cao, BR-06)"],
        ["Đã tiếp nhận", "Ghi kết quả xử lý", "Có kết luận thật / báo sai", "Đã đóng"],
        ["Đã tự xác nhận an toàn", "Lưu lịch sử tự động", "—", "Đã đóng"],
    ],
    widths=[3.4, 3.0, 3.0, 3.6], fs=9.5)

h2("3.4. Sơ đồ tuần tự: từ khung hình đến người tiếp nhận")
para("Sơ đồ tuần tự dưới đây mô tả một kịch bản thành công đầy đủ, cho thấy thứ tự trao "
     "đổi thông điệp giữa các thành phần bên trong hệ thống. Sơ đồ này là cầu nối giữa "
     "mô hình xử lý (Phần III) và mô hình kiến trúc (Phần VI).")
figure("h06_tuan_tu_canh_bao.png", 5.8,
       "Sơ đồ tuần tự của một kịch bản phát hiện và xử lý cảnh báo thành công")
para("Hai thông điệp tự gọi (số 4 và số 6) là nơi đặt toàn bộ logic quy tắc nghiệp vụ. "
     "Mô hình học máy chỉ trả về một con số xác suất; quyết định « có phải cảnh báo hay "
     "không » thuộc về quy tắc BR-01 và BR-02. Nhờ tách bạch như vậy, có thể hiệu chỉnh "
     "độ nhạy của hệ thống mà không phải huấn luyện lại mô hình.")

h2("3.5. Quy trình xử lý trạng thái giám sát hạn chế")
para("Mục B.4.4 của Khảo sát hiện trạng yêu cầu tách bạch hai việc: chức năng phát hiện "
     "cục bộ chỉ tiếp tục khi camera và máy xử lý còn hoạt động, còn việc gửi thông báo "
     "ra ngoài có thể chờ mạng khôi phục. Bảng dưới đây hình thức hoá từng tình huống.")
tcap("Xử lý các tình huống giám sát hạn chế")
table(
    ["Tình huống", "Phát hiện cục bộ", "Thông báo ra ngoài", "Hành vi hệ thống"],
    [
        ["Mất kết nối camera", "Dừng", "Vẫn gửi được", "Ghi thời điểm bắt đầu, hiển thị « giám sát hạn chế », báo cho kỹ thuật viên"],
        ["Mất kết nối Internet", "Tiếp tục", "Đưa vào hàng đợi", "Vẫn phát âm báo tại chỗ; gửi lại toàn bộ hàng đợi khi có mạng"],
        ["Mất điện máy xử lý", "Dừng", "Dừng", "Khi khôi phục, ghi nhận khoảng thời gian gián đoạn vào nhật ký thiết bị"],
        ["Ảnh quá tối", "Suy giảm", "Vẫn gửi được", "Hạ mức tin cậy, hiển thị « giám sát hạn chế », không im lặng bỏ qua"],
        ["Người bị che khuất kéo dài", "Suy giảm", "Vẫn gửi được", "Áp dụng BR-08, không kết luận trên cửa sổ thiếu dữ liệu"],
        ["Máy xử lý quá tải", "Suy giảm", "Vẫn gửi được", "Giảm tần suất suy luận có kiểm soát và ghi nhật ký hiệu năng"],
    ],
    widths=[3.0, 1.8, 2.0, 6.2], fs=9.5, first_col_bold=True)
para("Nguyên tắc chung xuyên suốt bảng trên: mọi khoảng thời gian mà hệ thống không thể "
     "tin cậy hoàn toàn đều phải có thời điểm bắt đầu và thời điểm kết thúc trong nhật "
     "ký, để sau này người dùng biết được khoảng nào không nên tin vào cơ chế tự động.")

h1("PHẦN IV. MÔ HÌNH DỮ LIỆU")

h2("4.1. Sơ đồ lớp mức phân tích")
para("Bốn nhóm thông tin nêu ở mục B.3 của Khảo sát hiện trạng — người và không gian "
     "giám sát, cấu hình vận hành, dữ liệu quan sát, sự kiện và nhật ký — được triển "
     "khai thành mười hai lớp. Sơ đồ ở mức phân tích nên chỉ liệt kê các thuộc tính có "
     "ý nghĩa nghiệp vụ; kiểu dữ liệu, độ dài và khoá ngoại thuộc về bước Thiết kế.")
figure("h07_so_do_lop.png", 6.3, "Sơ đồ lớp mức phân tích")

h2("4.2. Từ điển lớp và thuộc tính")
para("Từ điển gồm hai phần: bảng vai trò nghiệp vụ của từng lớp và bảng chi tiết thuộc "
     "tính. Thuộc tính định danh được đánh dấu bằng ký hiệu « định danh »; thuộc tính "
     "phức hợp (có thể tách nhỏ) được ghi chú rõ để bước Thiết kế xử lý.")

CLASSES = [
    ("NguoiDuocGiamSat", "Người cao tuổi được hệ thống theo dõi. Đây là dữ liệu nhạy cảm, chỉ người có thẩm quyền được xem (NFR-10).",
     [["maNguoi", "định danh", "Mã phân biệt từng người được giám sát"],
      ["hoTen", "thường", "Họ tên đầy đủ; hiển thị rút gọn trên màn hình chung"],
      ["namSinh", "thường", "Dùng để ước lượng nhóm nguy cơ"],
      ["ghiChuNguyCoNga", "thường", "Ghi chú của người chăm sóc về tiền sử ngã, bệnh lý ảnh hưởng dáng đi"],
      ["trangThaiTheoDoi", "thường", "Đang theo dõi / tạm dừng theo dõi"]]),
    ("Phong", "Không gian vật lý được giám sát; là đơn vị áp dụng quy tắc cảnh báo.",
     [["maPhong", "định danh", "Mã phòng"],
      ["tenPhong", "thường", "Tên gọi quen thuộc, ví dụ « phòng khách », « phòng 204 »"],
      ["loaiKhongGian", "thường", "Hộ gia đình hay cơ sở chăm sóc; ảnh hưởng đến quy trình leo thang"],
      ["diaDiem", "phức hợp", "Địa chỉ, tầng, khu; sẽ tách thành nhiều cột ở bước Thiết kế"]]),
    ("Camera", "Thiết bị thu hình đã khai báo. Trạng thái kết nối của lớp này là nguồn dữ liệu cho trạng thái giám sát hạn chế.",
     [["maCamera", "định danh", "Mã camera"],
      ["tenCamera", "thường", "Tên gợi nhớ vị trí đặt"],
      ["duongDanLuong", "thường", "Địa chỉ luồng hình ảnh trong mạng nội bộ"],
      ["doPhanGiai", "thường", "Kích thước khung hình; ảnh hưởng đến khả năng trích khung xương"],
      ["gocDat", "thường", "Mô tả góc đặt, dùng khi hiệu chỉnh cảnh báo sai"],
      ["trangThaiKetNoi", "thường", "Đang kết nối / mất kết nối / chưa kiểm tra"]]),
    ("VungQuanSat", "Vùng đa giác vẽ trên khung hình camera, cho phép áp dụng quy tắc khác nhau theo khu vực.",
     [["maVung", "định danh", "Mã vùng"],
      ["loaiVung", "thường", "Giường / ghế / loại trừ; quyết định cách áp dụng BR-09"],
      ["toaDoDaGiac", "phức hợp", "Danh sách đỉnh của đa giác trên khung hình"]]),
    ("QuyTacCanhBao", "Bản cấu hình vận hành của một phòng. Mỗi lần thay đổi tạo một bản mới, bản cũ được giữ lại để đối chiếu (FR-18).",
     [["maQuyTac", "định danh", "Mã bản cấu hình"],
      ["nguongTinCay", "thường", "Xác suất tối thiểu để tính một lần dương tính (mặc định 0,85)"],
      ["soLanLienTiep", "thường", "Số lần dương tính liên tiếp để phát cảnh báo (mặc định 2)"],
      ["thoiGianChoXacNhan", "thường", "Thời gian chờ người được giám sát tự xác nhận"],
      ["khungGioApDung", "phức hợp", "Các khoảng giờ trong ngày mà quy tắc có hiệu lực"],
      ["hieuLucTu", "thường", "Thời điểm bản cấu hình bắt đầu có hiệu lực"]]),
    ("NguoiNhanCanhBao", "Người sẽ nhận thông báo khi có sự cố. Một người có thể nhận cảnh báo của nhiều phòng.",
     [["maNguoiNhan", "định danh", "Mã người nhận"],
      ["hoTen", "thường", "Họ tên"],
      ["vaiTro", "thường", "Người thân / điều dưỡng / kỹ thuật viên"],
      ["kenhLienLac", "thường", "Tin nhắn, thông báo đẩy hoặc thư điện tử"],
      ["diaChiLienLac", "thường", "Số điện thoại hoặc địa chỉ thư tương ứng với kênh"]]),
    ("ThuTuLeoThang", "Lớp kết hợp giữa QuyTacCanhBao và NguoiNhanCanhBao: nó mang thuộc tính của chính mối quan hệ, không thuộc về riêng lớp nào.",
     [["thuTuUuTien", "định danh cục bộ", "Bậc thứ mấy trong chuỗi leo thang"],
      ["thoiHanPhanHoi", "thường", "Thời gian chờ xác nhận của riêng bậc này"],
      ["trangThaiApDung", "thường", "Đang áp dụng / tạm ngừng (ví dụ người nhận đang đi vắng)"]]),
    ("PhienGiamSat", "Một khoảng thời gian camera hoạt động liên tục. Phiên kết thúc khi mất kết nối hoặc dừng giám sát chủ động.",
     [["maPhien", "định danh", "Mã phiên"],
      ["thoiDiemBatDau", "thường", "Thời điểm bắt đầu phiên"],
      ["thoiDiemKetThuc", "thường", "Rỗng nếu phiên đang chạy"],
      ["trangThaiGiamSat", "thường", "Bình thường / hạn chế / dừng; là thuộc tính hiển thị ở UC-08"]]),
    ("KetQuaNhanDang", "Kết quả một lần chạy mô hình trên một cửa sổ thời gian. Đây là dữ liệu quan sát, chỉ giữ trong thời hạn tối thiểu cần thiết (NFR-09).",
     [["maKetQua", "định danh", "Mã kết quả"],
      ["thoiDiem", "thường", "Thời điểm cửa sổ kết thúc"],
      ["xacSuatTeNga", "thường", "Giá trị từ 0 đến 1 do mô hình trả về"],
      ["nhanDuDoan", "thường", "Té ngã / không té ngã sau khi áp ngưỡng"]]),
    ("SuKienTeNga", "Đối tượng trung tâm, có vòng đời đã mô tả ở mục 3.3.",
     [["maSuKien", "định danh", "Mã sự kiện"],
      ["thoiDiemPhatHien", "thường", "Thời điểm sự kiện được tạo"],
      ["mucDoTinCay", "thường", "Xác suất cao nhất trong chuỗi cửa sổ đã kích hoạt sự kiện"],
      ["trangThai", "thường", "Một trong sáu trạng thái ở bảng 12"],
      ["anhMinhHoa", "thường", "Ảnh tại thời điểm phát cảnh báo; chỉ lưu khi có sự kiện (NFR-08)"]]),
    ("ThongBao", "Một lần gửi cảnh báo tới một người nhận. Một sự kiện có thể sinh nhiều thông báo qua các bậc leo thang.",
     [["maThongBao", "định danh", "Mã thông báo"],
      ["thoiDiemGui", "thường", "Thời điểm hệ thống phát lệnh gửi"],
      ["kenhGui", "thường", "Kênh thực tế đã dùng"],
      ["trangThaiGui", "thường", "Đang chờ / đã gửi / thất bại; hỗ trợ hàng đợi ở FR-23"]]),
    ("PhanHoiXuLy", "Kết luận của người xử lý về một sự kiện. Đây là nguồn dữ liệu quan trọng nhất để hiệu chỉnh hệ thống ở các giai đoạn sau.",
     [["maPhanHoi", "định danh", "Mã phản hồi"],
      ["thoiDiemPhanHoi", "thường", "Thời điểm ghi nhận kết luận"],
      ["ketLuan", "thường", "Sự cố thật / cảnh báo sai"],
      ["ghiChu", "thường", "Mô tả bối cảnh, dùng khi rà soát nguyên nhân báo sai"]]),
]

tcap("Vai trò nghiệp vụ của từng lớp")
table(["Lớp", "Vai trò nghiệp vụ"],
      [[c, m] for c, m, _ in CLASSES],
      widths=[3.0, 9.0], fs=9.5, first_col_bold=True)

tcap("Từ điển thuộc tính của các lớp")
_attr_rows = []
for cls, _, rows in CLASSES:
    for k, r in enumerate(rows):
        _attr_rows.append([f"**{cls}**" if k == 0 else "", r[0], r[1], r[2]])
table(["Lớp", "Thuộc tính", "Loại", "Ý nghĩa nghiệp vụ"], _attr_rows,
      widths=[2.4, 2.4, 1.6, 5.6], fs=9.5)

h2("4.3. Các mối kết hợp và bản số")
tcap("Danh sách mối kết hợp giữa các lớp")
table(
    ["Lớp A", "Mối kết hợp", "Lớp B", "Bản số", "Diễn giải"],
    [
        ["NguoiDuocGiamSat", "ở tại", "Phong", "0..* – 1", "Một phòng có thể có nhiều người được giám sát; mỗi người thuộc một phòng tại một thời điểm"],
        ["Phong", "được lắp", "Camera", "1 – 1..*", "Một phòng phải có ít nhất một camera thì mới giám sát được"],
        ["Camera", "khai báo", "VungQuanSat", "1 – 0..*", "Vùng quan sát là tuỳ chọn; không khai báo thì áp dụng toàn khung hình"],
        ["Camera", "ghi nhận", "PhienGiamSat", "1 – 0..*", "Mỗi lần camera bắt đầu hoạt động sinh một phiên mới"],
        ["Phong", "áp dụng", "QuyTacCanhBao", "1 – 1", "Mỗi phòng luôn có đúng một bản cấu hình đang hiệu lực"],
        ["QuyTacCanhBao", "nhận theo", "NguoiNhanCanhBao", "1 – 1..*", "Một quy tắc phải có ít nhất một người nhận, nếu không cảnh báo sẽ không đến được ai"],
        ["NguoiNhanCanhBao", "sắp thứ tự", "ThuTuLeoThang", "1 – 0..*", "Lớp kết hợp mang thứ tự ưu tiên và thời hạn phản hồi của từng bậc"],
        ["PhienGiamSat", "sinh ra", "KetQuaNhanDang", "1 – 0..*", "Mỗi lần suy luận tạo một kết quả gắn với phiên đang chạy"],
        ["KetQuaNhanDang", "kích hoạt", "SuKienTeNga", "1..* – 0..1", "Phải có ít nhất hai kết quả dương tính liên tiếp mới sinh một sự kiện (BR-01)"],
        ["SuKienTeNga", "phát sinh", "ThongBao", "1 – 0..*", "Không gửi thông báo nào nếu sự kiện được tự xác nhận an toàn"],
        ["ThongBao", "gửi tới", "ThuTuLeoThang", "0..* – 1", "Mỗi thông báo gắn với đúng một bậc leo thang"],
        ["SuKienTeNga", "được xử lý", "PhanHoiXuLy", "1 – 0..*", "Sự kiện chưa đóng thì chưa có phản hồi nào"],
    ],
    widths=[2.4, 1.6, 2.2, 1.4, 4.4], fs=9.5)

h2("4.4. Ràng buộc toàn vẹn mức phân tích")
para("Các ràng buộc dưới đây là những điều kiện luôn phải đúng, bất kể hệ thống được cài "
     "đặt bằng công nghệ nào. Bước Thiết kế sẽ chuyển chúng thành ràng buộc miền giá "
     "trị, ràng buộc liên thuộc tính và ràng buộc liên bảng.")
tcap("Ràng buộc toàn vẹn")
table(
    ["Mã", "Ràng buộc", "Loại"],
    [
        ["RB-01", "nguongTinCay phải nằm trong khoảng từ 0 đến 1.", "Miền giá trị"],
        ["RB-02", "soLanLienTiep phải là số nguyên dương, tối thiểu bằng 2.", "Miền giá trị"],
        ["RB-03", "thoiGianChoXacNhan và thoiHanPhanHoi phải lớn hơn 0 giây.", "Miền giá trị"],
        ["RB-04", "thoiDiemKetThuc của một phiên giám sát phải lớn hơn thoiDiemBatDau, hoặc để rỗng nếu phiên đang chạy.", "Liên thuộc tính"],
        ["RB-05", "thoiDiemPhanHoi phải lớn hơn hoặc bằng thoiDiemPhatHien của sự kiện tương ứng.", "Liên thuộc tính"],
        ["RB-06", "Mỗi QuyTacCanhBao phải liên kết tới ít nhất một NguoiNhanCanhBao qua ThuTuLeoThang.", "Liên bảng"],
        ["RB-07", "Trong một QuyTacCanhBao, thuTuUuTien không được trùng nhau.", "Liên bộ"],
        ["RB-08", "Một SuKienTeNga chỉ được chuyển sang trạng thái « Đã đóng » khi đã có PhanHoiXuLy, trừ trường hợp tự xác nhận an toàn.", "Liên bảng"],
        ["RB-09", "Một Phong tại một thời điểm chỉ có đúng một QuyTacCanhBao đang hiệu lực.", "Liên bộ"],
        ["RB-10", "anhMinhHoa chỉ tồn tại khi sự kiện đã được gửi ra ngoài; sự kiện tự xác nhận an toàn không lưu ảnh.", "Liên thuộc tính"],
        ["RB-11", "Một ThongBao không thể có trangThaiGui là « đã gửi » nếu thoiDiemGui còn rỗng.", "Liên thuộc tính"],
        ["RB-12", "VungQuanSat phải thuộc về một Camera đang tồn tại và toạ độ đa giác phải nằm trong kích thước khung hình của camera đó.", "Liên bảng"],
    ],
    widths=[1.0, 8.5, 2.5], fs=9.5)

h2("4.5. Vòng đời dữ liệu và ranh giới riêng tư")
para("Mục C.7 của Khảo sát hiện trạng đặt quyền riêng tư là điều kiện của quá trình xây "
     "dựng chứ không phải một tính năng thêm vào. Bảng dưới đây cụ thể hoá điều đó thành "
     "chính sách lưu trữ cho từng loại dữ liệu.")
tcap("Vòng đời và phạm vi lưu trữ của từng loại dữ liệu")
table(
    ["Loại dữ liệu", "Nơi tồn tại", "Thời gian giữ", "Có rời khỏi máy tại chỗ không?"],
    [
        ["Khung hình thô", "Chỉ trong bộ nhớ tạm", "Vài giây, đủ để trích khung xương", "Không"],
        ["Toạ độ khung xương", "Bộ đệm 32 khung trong bộ nhớ", "Đến khi cửa sổ trượt qua", "Không"],
        ["KetQuaNhanDang", "Kho dữ liệu cục bộ", "Theo thời hạn cấu hình, mặc định 7 ngày", "Không"],
        ["SuKienTeNga", "Kho dữ liệu cục bộ", "Dài hạn, phục vụ tra cứu lịch sử", "Chỉ phần tóm tắt"],
        ["anhMinhHoa", "Kho dữ liệu cục bộ", "Theo thời hạn cấu hình, mặc định 30 ngày", "Chỉ khi người dùng được phép xem"],
        ["ThongBao", "Kho dữ liệu cục bộ", "Dài hạn", "Nội dung tóm tắt gửi qua dịch vụ ngoài"],
        ["PhanHoiXuLy", "Kho dữ liệu cục bộ", "Dài hạn", "Không"],
        ["Nhật ký thiết bị", "Kho dữ liệu cục bộ", "Dài hạn", "Không"],
    ],
    widths=[2.6, 2.8, 3.4, 3.2], fs=9.5, first_col_bold=True)

h1("PHẦN V. PHÂN TÍCH BÀI TOÁN DỮ LIỆU VÀ LỰA CHỌN MÔ HÌNH")

h2("5.1. Phát biểu bài toán học máy")
para("Mục C.1 của Khảo sát hiện trạng đã phát biểu bài toán bằng lời. Ở đây, phát biểu "
     "đó được viết lại dưới dạng hình thức để có thể chuyển thẳng sang bước Thiết kế.")
para("Cho một chuỗi khung xương liên tiếp thu được từ một camera, trong đó mỗi khung "
     "hình được biểu diễn bằng toạ độ của 17 khớp cơ thể, hãy xác định xem cửa sổ thời "
     "gian đang xét có chứa một sự kiện té ngã hay không.", indent=0.8, italic=True)
tcap("Phát biểu hình thức bài toán học máy")
table(
    ["Thành phần", "Nội dung"],
    [
        ["Loại bài toán", "Phân loại nhị phân trên dữ liệu chuỗi thời gian có cấu trúc đồ thị"],
        ["Đơn vị mẫu", "Một cửa sổ gồm 32 khung hình liên tiếp (khoảng 1,8 giây ở tốc độ 18 hình/giây)"],
        ["Đầu vào", "Tensor kích thước 2 × 32 × 17: hai kênh toạ độ (x, y) × 32 khung hình × 17 khớp cơ thể"],
        ["Đầu ra", "Xác suất thuộc lớp « té ngã », giá trị trong khoảng từ 0 đến 1"],
        ["Lớp dương", "Cửa sổ chứa thời điểm té ngã"],
        ["Lớp âm", "Cửa sổ chứa hoạt động sinh hoạt bình thường, kể cả các hoạt động dễ gây nhầm lẫn"],
        ["Ràng buộc thời gian", "Suy luận phải hoàn tất trong thời gian ngắn hơn khoảng cách giữa hai lần chạy (4 khung hình, khoảng 0,22 giây)"],
        ["Ràng buộc riêng tư", "Mô hình chỉ được nhận toạ độ khớp, không nhận ảnh gốc"],
    ],
    widths=[3.0, 9.0], fs=9.5, first_col_bold=True)
para("Cần nhắc lại một lần nữa ranh giới đã nêu ở mục C.1 của khảo sát: học máy chỉ đảm "
     "nhận việc nhận biết chuyển động. Thứ tự leo thang, vùng giám sát, danh sách người "
     "nhận và việc phát hiện mất kết nối đều là quy tắc tường minh, được xử lý ở tầng "
     "quyết định như đã mô tả ở mục 1.5. Ranh giới này giúp hệ thống có thể được hiệu "
     "chỉnh và giải thích, thay vì trở thành một hộp đen.")

h2("5.2. Mô tả dữ liệu nguồn")
para("Bộ dữ liệu chính là UP-Fall Detection Dataset, đã được lựa chọn và lập luận ở mục "
     "C.3 của Khảo sát hiện trạng vì có nhiều kiểu ngã, có các hoạt động thường ngày dễ "
     "gây nhầm lẫn, có mã số người tham gia và có dữ liệu từ camera đặt trong phòng. Đề "
     "tài chỉ dùng một góc camera — điều này làm bài toán khó hơn nhưng gần với bối cảnh "
     "hộ gia đình, nơi mỗi phòng thường chỉ có một camera.")
tcap("Kiểm kê dữ liệu nguồn thực tế")
table(
    ["Hạng mục", "Số liệu", "Ghi chú"],
    [
        ["Số người tham gia", "12 người", "Mã số 1–11 và 13; người số 12 thiếu dữ liệu trong bộ gốc"],
        ["Số đoạn video", "394 đoạn", "Thiếu 2 đoạn so với con số lý thuyết 396"],
        ["Số loại hoạt động", "11 hoạt động", "5 kiểu ngã và 6 hoạt động sinh hoạt"],
        ["Số camera sử dụng", "1 góc camera", "Camera 1, đặt trong phòng"],
        ["Độ dài mỗi đoạn", "Khoảng 10 giây", "Khoảng 195 khung hình ở tốc độ ~18 hình/giây"],
        ["Bối cảnh ghi hình", "Phòng thí nghiệm", "Diễn viên trẻ, khoẻ; các kiểu ngã diễn trên đệm"],
    ],
    widths=[3.0, 2.6, 6.4], fs=9.5, first_col_bold=True)
tcap("Danh sách hoạt động và nhãn tương ứng")
table(
    ["Mã hoạt động", "Tên hoạt động", "Nhãn", "Vai trò trong bài toán"],
    [
        ["1", "Ngã về trước, chống tay", "Té ngã", "Kiểu ngã phổ biến nhất khi trượt chân"],
        ["2", "Ngã về trước, chống gối", "Té ngã", "Biến thể của kiểu ngã về trước"],
        ["3", "Ngã ra sau", "Té ngã", "Kiểu ngã nguy hiểm nhất, cũng là kiểu khó nhận biết nhất"],
        ["4", "Ngã sang bên", "Té ngã", "Kiểu ngã thường gặp khi mất thăng bằng"],
        ["5", "Ngã khi đang ngồi ghế", "Té ngã", "Kiểu ngã có biên độ chuyển động nhỏ hơn"],
        ["6", "Đi bộ", "Không té", "Hoạt động nền phổ biến nhất"],
        ["7", "Đứng", "Không té", "Nguồn cảnh báo sai chính (xem mục 5.10)"],
        ["8", "Ngồi", "Không té", "Dễ nhầm với ngã khi ngồi xuống nhanh"],
        ["9", "Nhặt đồ vật", "Không té", "Dễ nhầm vì thân người hạ thấp đột ngột"],
        ["10", "Nhảy", "Không té", "Dễ nhầm vì có gia tốc theo phương thẳng đứng"],
        ["11", "Nằm", "Không té", "Dễ nhầm vì tư thế cuối giống hệt sau khi ngã"],
    ],
    widths=[1.8, 3.6, 1.6, 5.0], fs=9.5, align_first="center")
para("Bốn hoạt động 8, 9, 10 và 11 là các hoạt động đối chiếu quan trọng nhất. Chính vì "
     "chúng tồn tại trong bộ dữ liệu mà kết quả đánh giá mới có ý nghĩa: một mô hình chỉ "
     "phân biệt được ngã với đi bộ thì không dùng được trong nhà thật.")

h2("5.3. Đơn vị mẫu, cách gán nhãn và phân bố lớp")
para("Vấn đề đầu tiên nêu ở mục C.5 của khảo sát là nhãn theo đoạn: một đoạn được gán "
     "nhãn « ngã » vẫn có phần người đang đứng hoặc đi bình thường ở đầu đoạn. Nếu gán "
     "nhãn dương cho toàn bộ đoạn, mô hình sẽ học nhầm rằng « người đang đi trong một "
     "đoạn có ngã » cũng là ngã. Cách xử lý là chuyển đơn vị mẫu từ đoạn sang cửa sổ.")
tcap("Quy tắc sinh mẫu từ mỗi đoạn video")
table(
    ["Loại đoạn", "Cách cắt cửa sổ", "Nhãn"],
    [
        ["Đoạn sinh hoạt bình thường\n(hoạt động 6–11)", "Cửa sổ trượt đều 32 khung, bước nhảy 16 khung", "0 (không té ngã)"],
        ["Đoạn té ngã\n(hoạt động 1–5)", "Xác định thời điểm ngã là khung hình có vận tốc rơi của tâm hông lớn nhất; lấy 5 cửa sổ có tâm quanh thời điểm đó với độ lệch ±8 khung", "1 (té ngã)"],
        ["Phần đầu của đoạn té ngã", "Cửa sổ trượt kết thúc trước thời điểm ngã ít nhất 5 khung", "0 (mẫu âm khó)"],
    ],
    widths=[3.2, 6.8, 2.0], fs=9.5, first_col_bold=True)
para("Phần đầu của đoạn té ngã được dùng làm mẫu âm khó là một lựa chọn có chủ đích: đó "
     "chính là những cửa sổ mà mô hình dễ nhầm nhất, vì chúng có cùng người, cùng bối "
     "cảnh, cùng ánh sáng với cửa sổ dương ngay sau đó. Đưa chúng vào tập huấn luyện "
     "buộc mô hình phải học chuyển động thay vì học bối cảnh.")
tcap("Phân bố mẫu sau khi cắt cửa sổ")
table(
    ["Tập dữ liệu", "Người tham gia", "Tổng số cửa sổ", "Cửa sổ té ngã", "Cửa sổ không té", "Tỷ lệ dương"],
    [
        ["Huấn luyện", "1 – 8", "6.997", "598", "6.399", "8,5%"],
        ["Theo dõi", "9", "949", "75", "874", "7,9%"],
        ["Kiểm thử", "10, 11, 13", "2.653", "225", "2.428", "8,5%"],
        ["**Tổng cộng**", "**12 người**", "**10.599**", "**898**", "**9.701**", "**8,5%**"],
    ],
    widths=[2.2, 2.0, 2.2, 2.0, 2.2, 1.6], fs=9.5)
figure("h09_du_lieu.png", 6.0,
       "Phân bố mẫu theo tập dữ liệu (trái) và độ nhạy theo từng kiểu ngã (phải)")
para("Tỷ lệ mẫu dương chỉ khoảng 8,5% ở cả ba tập. Đây chính là vấn đề mất cân bằng lớp "
     "đã cảnh báo ở mục C.4 của khảo sát: một mô hình luôn dự đoán « không ngã » sẽ đạt "
     "độ chính xác chung khoảng 91,5% mà hoàn toàn vô dụng. Hệ quả trực tiếp là không "
     "được dùng độ chính xác chung làm chỉ số chính, và trong quá trình huấn luyện phải "
     "bù mất cân bằng bằng trọng số lớp trong hàm mất mát.")

h2("5.4. Đặc trưng đầu vào và các kênh bị loại bỏ")
para("Bộ trích khung xương trả về, với mỗi khớp, ba giá trị: hoành độ, tung độ và độ tin "
     "cậy của khớp đó. Trực giác ban đầu là đưa cả ba kênh vào mô hình vì càng nhiều "
     "thông tin càng tốt. Thực nghiệm cho thấy điều ngược lại, và đây là bài học thứ "
     "nhất đã ghi ở mục D.3 của Khảo sát hiện trạng.")
tcap("Các kênh dữ liệu và quyết định sử dụng")
table(
    ["Kênh", "Ý nghĩa", "Quyết định", "Lý do"],
    [
        ["x, y", "Toạ độ khớp trên khung hình sau chuẩn hoá", "Sử dụng", "Mang trực tiếp thông tin về hình dáng và chuyển động của cơ thể"],
        ["Độ tin cậy khớp", "Mức chắc chắn của bộ trích khung xương về từng khớp", "Loại bỏ", "Mẫu che khuất phụ thuộc vào hướng đứng của từng người; mô hình học theo mẫu này thay vì học chuyển động, làm sập độ chính xác trên người mới"],
    ],
    widths=[2.0, 3.4, 1.6, 5.0], fs=9.5, first_col_bold=True)
para("Độ tin cậy khớp không bị vứt bỏ hoàn toàn — nó vẫn được dùng ở tầng tiền xử lý để "
     "quyết định khớp nào cần nội suy và cửa sổ nào không đủ dữ liệu để kết luận. Điểm "
     "khác biệt là nó không được đưa vào làm đặc trưng đầu vào của mô hình.")
para("Chuẩn hoá toạ độ cũng là một quyết định phân tích quan trọng: mỗi cửa sổ được tịnh "
     "tiến theo tâm hông của khung hình giữa — dùng một mốc cố định cho cả cửa sổ, vì trừ "
     "tâm hông theo từng khung sẽ xoá mất chính chuyển động rơi cần nhận biết — rồi chia "
     "cho độ dài thân trung vị, khiến đặc trưng bất biến với vị trí đứng và khoảng cách "
     "tới camera.")

h2("5.5. Nguyên tắc chia dữ liệu theo người")
para("Dữ liệu được chia theo người, không chia ngẫu nhiên theo khung hình. Một người chỉ "
     "thuộc đúng một trong ba tập. Nguyên tắc này đã nêu ở mục C.6 của khảo sát và được "
     "giữ nguyên vì nó là điều kiện để kết quả đánh giá có ý nghĩa.")
tcap("So sánh hai cách chia dữ liệu")
table(
    ["Tiêu chí", "Chia ngẫu nhiên theo cửa sổ", "Chia theo người (đã chọn)"],
    [
        ["Câu hỏi mà kết quả trả lời", "Mô hình có nhận ra được cú ngã của một người mà nó đã thấy trong lúc huấn luyện không?", "Mô hình có nhận ra được cú ngã của một người hoàn toàn mới không?"],
        ["Rủi ro rò rỉ dữ liệu", "Cao: cùng một lần diễn có thể xuất hiện ở cả tập huấn luyện và tập kiểm thử", "Thấp: người trong tập kiểm thử chưa từng xuất hiện"],
        ["Kết quả thu được", "Cao hơn nhưng lạc quan giả", "Thấp hơn nhưng phản ánh đúng tình huống triển khai thực tế"],
        ["Phù hợp với mục tiêu đề tài", "Không", "Có"],
    ],
    widths=[2.6, 4.7, 4.7], fs=9.5, first_col_bold=True)
para("Tập kiểm thử gồm người số 10, 11 và 13 — ba người này không xuất hiện trong tập "
     "huấn luyện lẫn tập theo dõi. Mọi con số ở mục 5.10 đều đo trên tập này.")

h2("5.6. Phân tích và lựa chọn mô hình")
para("Năm phương án được cân nhắc. Việc so sánh không chỉ dựa trên độ chính xác đã công "
     "bố trong tài liệu, mà còn dựa trên bốn ràng buộc thực tế của đề tài: yêu cầu riêng "
     "tư (mục B.5 của khảo sát), yêu cầu chạy thời gian thực trên phần cứng giá thấp "
     "(mục A.6), lượng dữ liệu có được, và khả năng gỡ lỗi khi hệ thống báo sai.")
tcap("So sánh các phương án mô hình")
table(
    ["Phương án", "Đầu vào", "Điểm mạnh", "Điểm yếu với đề tài này"],
    [
        ["Đặc trưng hình học + SVM", "Tỷ lệ khung bao, tốc độ trọng tâm", "Rất nhẹ, dễ giải thích", "Độ chính xác thấp, rất nhạy với góc camera và ánh sáng"],
        ["CNN 2D/3D trên ảnh màu", "Toàn bộ khung hình", "Độ chính xác cao nhất trong các công bố", "Phải xử lý ảnh gốc, xung đột trực tiếp với yêu cầu riêng tư; nặng, khó chạy thời gian thực trên máy rẻ"],
        ["Khung xương + LSTM/GRU", "Chuỗi toạ độ khớp làm phẳng", "Bảo vệ riêng tư, nhẹ", "Làm phẳng khung xương làm mất cấu trúc kết nối giữa các khớp"],
        ["Khung xương + Transformer", "Chuỗi toạ độ khớp", "Bắt được quan hệ xa trong chuỗi", "Cần nhiều dữ liệu hơn hẳn để hội tụ; nặng hơn khi suy luận"],
        ["**Khung xương + ST-GCN**", "Đồ thị 17 khớp × 32 khung hình", "Giữ được đồng thời quan hệ không gian giữa các khớp và quan hệ thời gian giữa các khung; nhẹ; bảo vệ riêng tư", "Cần xây dựng ma trận kề của đồ thị khung xương; nhạy với chất lượng khung xương đầu vào"],
    ],
    widths=[2.6, 2.4, 3.5, 4.5], fs=9.5, first_col_bold=True)
para("Để lựa chọn không mang tính cảm tính, năm phương án được chấm điểm theo năm tiêu "
     "chí có trọng số. Thang điểm từ 1 (kém) đến 5 (tốt); trọng số phản ánh mức độ quan "
     "trọng của từng tiêu chí đối với mục tiêu đề tài.")
tcap("Ma trận quyết định lựa chọn mô hình")
table(
    ["Tiêu chí (trọng số)", "Hình học\n+ SVM", "CNN\ntrên ảnh", "Xương\n+ LSTM", "Xương\n+ Transformer", "Xương\n+ ST-GCN"],
    [
        ["Bảo vệ riêng tư (25%)", "4", "1", "5", "5", "5"],
        ["Chạy thời gian thực trên máy giá thấp (25%)", "5", "2", "4", "3", "4"],
        ["Độ chính xác kỳ vọng với lượng dữ liệu hiện có (25%)", "2", "5", "3", "4", "4"],
        ["Khả năng gỡ lỗi và giải thích (15%)", "4", "2", "3", "2", "4"],
        ["Chi phí dữ liệu và huấn luyện (10%)", "5", "2", "4", "2", "4"],
        ["**Tổng điểm có trọng số**", "**3,85**", "**2,50**", "**3,85**", "**3,50**", "**4,25**"],
    ],
    widths=[5.0, 1.4, 1.4, 1.4, 1.4, 1.4], fs=9.5, first_col_bold=True)
para("Phương án khung xương kết hợp ST-GCN đạt điểm cao nhất. Điều đáng nói là phương án "
     "này không thắng ở tiêu chí độ chính xác — mạng tích chập trên ảnh màu vẫn cho kết "
     "quả cao hơn trong các công bố — mà thắng nhờ cân bằng tốt giữa riêng tư, tốc độ và "
     "khả năng gỡ lỗi. Đây là ví dụ cho thấy vì sao việc chọn mô hình phải bám vào yêu "
     "cầu hệ thống chứ không chỉ nhìn vào bảng xếp hạng độ chính xác.")
para("Chuỗi xử lý gồm hai mô hình nối tiếp: bộ trích khung xương (YOLO-Pose) chuyển ảnh "
     "thành toạ độ khớp, bộ phân loại chuỗi (ST-GCN) chuyển chuỗi toạ độ thành xác suất "
     "té ngã. Hệ quả quan trọng: chất lượng bộ phân loại bị chặn trên bởi chất lượng bộ "
     "trích khung xương — khi người bị che khuất, bộ phân loại không có cách nào bù lại.")

h2("5.7. Cấu hình mô hình đã chọn")
para("ST-GCN biểu diễn khung xương thành một đồ thị: mỗi đỉnh là một khớp, mỗi cạnh là "
     "một liên kết xương. Trên đồ thị đó, mô hình thực hiện đồng thời hai phép tích "
     "chập: tích chập đồ thị theo không gian (học quan hệ giữa các khớp trong cùng một "
     "khung hình) và tích chập một chiều theo thời gian (học quan hệ giữa các khung hình "
     "liên tiếp).")
tcap("Cấu hình mô hình và tham số huấn luyện")
table(
    ["Hạng mục", "Giá trị", "Ghi chú"],
    [
        ["Số đỉnh đồ thị", "17 khớp", "Bộ khớp chuẩn COCO do bộ trích khung xương trả về"],
        ["Số cạnh đồ thị", "18 liên kết xương", "Đầu, cổ – vai, tay, thân, chân"],
        ["Chiến lược phân nhóm lân cận", "3 nhóm", "Chính nó, nhóm hướng tâm và nhóm ly tâm"],
        ["Số khối ST-GCN", "7 khối", "Số kênh: 64, 64, 64, 128, 128, 256, 256"],
        ["Bề rộng tích chập thời gian", "9 khung hình", "Khoảng 0,5 giây ở tốc độ 18 hình/giây"],
        ["Tổng số tham số", "2.035.195", "Khoảng 2,04 triệu — đủ nhẹ để suy luận trên thiết bị biên"],
        ["Hàm mất mát", "Entropy chéo có trọng số lớp", "Bù tỷ lệ mẫu dương chỉ 8,5%"],
        ["Thuật toán tối ưu", "AdamW", "Tốc độ học 0,001; suy giảm trọng số 0,0001"],
        ["Lịch tốc độ học", "5 epoch khởi động + suy giảm cosine", "Tổng tối đa 70 epoch"],
        ["Kích thước lô", "64 cửa sổ", "—"],
        ["Điều kiện dừng sớm", "20 epoch không cải thiện", "Theo dõi chỉ số F1 của lớp té ngã trên tập theo dõi"],
        ["Chống quá khớp", "Dropout 0,5 + tăng cường dữ liệu", "Lật ngang, xoay ±10°, co giãn ±10%, nhiễu nhỏ"],
        ["Hạt giống ngẫu nhiên", "42, bật chế độ tất định", "Bảo đảm chạy lại cho kết quả giống nhau"],
    ],
    widths=[3.4, 3.4, 5.2], fs=9.5, first_col_bold=True)

h2("5.8. Tiêu chí đánh giá ba mức")
para("Mục C.6 của Khảo sát hiện trạng đã yêu cầu đánh giá ở ba mức. Bảng dưới đây cụ thể "
     "hoá từng chỉ số, kèm lý do vì sao chỉ số đó cần thiết.")
tcap("Tiêu chí đánh giá ở ba mức")
table(
    ["Mức", "Chỉ số", "Ý nghĩa với người dùng", "Mục tiêu"],
    [
        ["Cửa sổ", "Tỷ lệ phát hiện (recall)", "Trong các cửa sổ thực sự có ngã, mô hình bắt được bao nhiêu phần trăm", "≥ 90%"],
        ["Cửa sổ", "Độ chính xác khi cảnh báo (precision)", "Trong các cửa sổ mô hình báo ngã, bao nhiêu phần trăm là ngã thật", "≥ 80%"],
        ["Cửa sổ", "Chỉ số F1 của lớp té ngã", "Chỉ số cân bằng giữa hai đại lượng trên", "≥ 0,85"],
        ["Cửa sổ", "Tỷ lệ phát hiện theo từng kiểu ngã", "Cho biết kiểu ngã nào đang bị bỏ sót", "Không kiểu nào dưới 80%"],
        ["Sự kiện", "Số ca ngã phát hiện được trên tổng số ca", "Con số mà người chăm sóc thực sự quan tâm", "≥ 90%"],
        ["Sự kiện", "Số cảnh báo giả trên thời gian giám sát", "Quyết định người dùng có còn tin hệ thống hay không", "≤ 1 lần/phòng/24 giờ"],
        ["Sự kiện", "Độ trễ từ lúc ngã đến lúc tạo cảnh báo", "Thời gian vàng để cấp cứu", "≤ 3 giây"],
        ["Vận hành", "Số khung hình xử lý mỗi giây", "Khả năng theo kịp luồng camera", "≥ 15 hình/giây"],
        ["Vận hành", "Khả năng chạy lại cho kết quả nhất quán", "Điều kiện để so sánh các thí nghiệm", "Bắt buộc"],
        ["Vận hành", "Trạng thái hoạt động của thiết bị", "Bảo đảm không có khoảng mù im lặng", "Bắt buộc"],
    ],
    widths=[1.6, 3.4, 5.0, 2.0], fs=9.5)
para("Việc tách mức cửa sổ khỏi mức sự kiện là điểm quan trọng. Một cửa sổ dương giả đơn "
     "lẻ không tạo ra cảnh báo, vì quy tắc BR-01 đòi hỏi hai lần dương tính liên tiếp. "
     "Do đó độ chính xác ở mức cửa sổ luôn thấp hơn ở mức sự kiện, và chỉ có con số ở "
     "mức sự kiện mới phản ánh đúng trải nghiệm của người dùng.")

h2("5.9. Rủi ro mô hình học tắt và bằng chứng thực nghiệm")
para("Mục D.3 của Khảo sát hiện trạng đã ghi ba bài học rút ra từ thử nghiệm tiền khả "
     "thi. Ở giai đoạn phân tích, ba bài học đó được nâng lên thành ba rủi ro cần kiểm "
     "soát, kèm bằng chứng đối chứng cụ thể. « Học tắt » ở đây có nghĩa là mô hình tìm "
     "được một dấu hiệu tương quan với nhãn nhưng không phải là nguyên nhân — dấu hiệu "
     "ấy hoạt động tốt trên tập huấn luyện và sụp đổ trên người mới.")
tcap("Ba rủi ro học tắt đã phát hiện và biện pháp xử lý")
table(
    ["Rủi ro", "Biểu hiện", "Biện pháp", "Bằng chứng đối chứng"],
    [
        ["Học theo mẫu che khuất thay vì học chuyển động",
         "Mô hình dựa vào kênh độ tin cậy của khớp; mẫu che khuất phụ thuộc hướng đứng của từng người",
         "Loại kênh độ tin cậy khỏi đầu vào, chỉ giữ hai kênh toạ độ",
         "F1 trên tập kiểm thử tăng từ 0,42 lên 0,67"],
        ["Khung xương « nhảy » giữa nhiều người",
         "Phòng quay có vách kính, bộ trích khung xương thấy cả người đi phía sau; chọn người theo độ tin cậy ở từng khung hình độc lập làm chuỗi tư thế nhảy giữa hai người",
         "Bám người theo vị trí ở khung hình trước, chỉ đổi người khi mất dấu",
         "F1 trên tập kiểm thử tăng từ 0,67 lên 0,87"],
        ["Quy tắc điền khớp bị che tạo ra hình dáng giống tư thế ngã",
         "Khớp không xuất hiện suốt cửa sổ bị ghim về gốc toạ độ, tạo ra hình « khớp đầu ngang hông » giống người đang ngã",
         "Lấy vị trí gương của khớp đối xứng trái/phải khi suy luận",
         "Riêng người số 13 ở hoạt động « đứng »: số cửa sổ báo giả giảm từ 103 xuống 17"],
    ],
    widths=[2.8, 4.2, 2.6, 2.4], fs=9.5, first_col_bold=True)
para("Một thí nghiệm đối chứng thứ tư cũng đáng ghi lại vì nó cho kết quả ngược với dự "
     "đoán. Ba phép tăng cường dữ liệu được thiết kế riêng để chống việc học tủ tư thế "
     "tĩnh — đóng băng cửa sổ thành mẫu âm, hoán đổi góc nhìn trước/sau, và bóp bề ngang "
     "khung xương — đều làm chỉ số F1 giảm chứ không tăng, vì mô hình mất bớt độ nhạy. "
     "Giải pháp hiệu quả nằm ở tầng tiền xử lý chứ không ở tầng tăng cường dữ liệu.")
tcap("Tổng hợp các thí nghiệm đối chứng đã thực hiện")
table(
    ["Thí nghiệm", "Thay đổi", "F1 lớp té ngã trên tập kiểm thử"],
    [
        ["Mốc ban đầu", "Ba kênh đầu vào, chọn người theo độ tin cậy từng khung, ghim khớp che về gốc", "0,42"],
        ["Thí nghiệm 1", "Bỏ kênh độ tin cậy", "0,67"],
        ["Thí nghiệm 2", "Thêm cơ chế bám người theo vị trí", "0,87"],
        ["Thí nghiệm 3", "Điền khớp bị che bằng khớp đối xứng khi suy luận", "**0,876**"],
        ["Thí nghiệm 4", "Thêm ba phép tăng cường dữ liệu chống học tủ tư thế tĩnh", "0,67 – 0,71 (giảm, đã loại bỏ)"],
    ],
    widths=[2.4, 6.6, 3.0], fs=9.5, first_col_bold=True)
para("Bài học phương pháp: không thể chỉ nhìn vào con số đánh giá. Cả ba rủi ro trên đều "
     "được phát hiện nhờ xem lại mẫu dự đoán sai, trực quan hoá dữ liệu đầu vào và chạy "
     "thí nghiệm đối chứng, chứ không phải nhờ tối ưu tham số.")

h2("5.10. Kết quả tiền khả thi và phân tích lỗi")
para("Các con số dưới đây đo trên tập kiểm thử gồm người số 10, 11 và 13 — những người "
     "chưa từng xuất hiện trong quá trình huấn luyện. Tổng cộng 2.653 cửa sổ, trong đó "
     "225 cửa sổ có nhãn té ngã.")
tcap("Ma trận nhầm lẫn trên tập kiểm thử")
table(
    ["", "Dự đoán: Không té ngã", "Dự đoán: Té ngã", "Tổng"],
    [
        ["**Thực tế: Không té ngã**", "2.385", "43", "2.428"],
        ["**Thực tế: Té ngã**", "16", "209", "225"],
        ["**Tổng**", "2.401", "252", "2.653"],
    ],
    widths=[3.6, 3.2, 2.8, 2.4], fs=9.5, align_first="left")
tcap("Kết quả tổng hợp trên tập kiểm thử độc lập")
table(
    ["Chỉ số", "Giá trị", "Mục tiêu (mục 5.8)", "Đạt?"],
    [
        ["Độ chính xác chung", "97,8%", "không dùng làm chỉ số chính", "—"],
        ["Tỷ lệ phát hiện (recall)", "92,9%", "≥ 90%", "Đạt"],
        ["Độ chính xác khi cảnh báo (precision)", "82,9%", "≥ 80%", "Đạt"],
        ["Chỉ số F1 lớp té ngã", "0,876", "≥ 0,85", "Đạt"],
        ["Kết quả mức sự kiện", "42/45 ca ngã được phát hiện (93,3%)", "≥ 90%", "Đạt"],
        ["Cảnh báo giả mức sự kiện", "10/54 đoạn sinh hoạt (18,5%)", "≤ 1 lần/phòng/24 giờ", "Chưa kết luận được"],
        ["Độ trễ suy luận của bộ phân loại", "khoảng 3 mili-giây mỗi cửa sổ", "≤ 3 giây tổng thể", "Đạt"],
        ["Chỉ số F1 trên tập theo dõi (người số 9)", "0,993", "tham khảo", "—"],
    ],
    widths=[4.4, 3.6, 2.6, 1.4], fs=9.5, first_col_bold=True)
para("Kết quả mức sự kiện cần được đọc thận trọng. Con số 10/54 đoạn sinh hoạt gây cảnh "
     "báo giả không thể quy đổi trực tiếp thành « bao nhiêu lần báo giả mỗi ngày », vì "
     "mỗi đoạn chỉ dài khoảng 10 giây và được diễn liên tục. Đây chính là chỉ tiêu chưa "
     "kết luận được ở giai đoạn này và cần dữ liệu sinh hoạt dài ngày để đo, như đã ghi "
     "ở mục D.4 của Khảo sát hiện trạng.")

h3("Phân tích 16 trường hợp bỏ sót")
tcap("Phân bố các trường hợp bỏ sót theo kiểu ngã")
table(
    ["Kiểu ngã", "Số cửa sổ dương", "Số bỏ sót", "Tỷ lệ phát hiện"],
    [
        ["Ngã về trước, chống tay", "45", "5", "88,9%"],
        ["Ngã về trước, chống gối", "45", "0", "100%"],
        ["**Ngã ra sau**", "**45**", "**11**", "**75,6%**"],
        ["Ngã sang bên", "45", "0", "100%"],
        ["Ngã khi ngồi ghế", "45", "0", "100%"],
    ],
    widths=[4.0, 2.6, 2.4, 3.0], fs=9.5, first_col_bold=True)
para("Toàn bộ 16 trường hợp bỏ sót đều tập trung ở hai kiểu ngã về trước chống tay và "
     "ngã ra sau, trong đó riêng ngã ra sau chiếm 11 trường hợp. Nguyên nhân đã được xác "
     "định từ giai đoạn khảo sát: khi ngã ngửa, thân người hạ thấp và phần lớn các khớp "
     "phía trước bị chính cơ thể che khuất, làm chất lượng khung xương giảm mạnh. Đây là "
     "biểu hiện của giới hạn đã nêu ở mục 5.6 — chất lượng bộ phân loại bị chặn trên bởi "
     "chất lượng bộ trích khung xương.")
para("Đây lại đúng là kiểu ngã nguy hiểm nhất — ngã ngửa thường gây chấn thương vùng đầu "
     "và cột sống — nên nhóm này được đặt làm ưu tiên cải thiện số một, thay vì cố nâng "
     "chỉ số trung bình chung.")

h3("Phân tích 43 trường hợp cảnh báo giả")
tcap("Phân bố cảnh báo giả theo hoạt động và theo người")
table(
    ["Hoạt động gây cảnh báo giả", "Số cửa sổ", "Nguyên nhân phân tích được"],
    [
        ["Đứng (hoạt động 7)", "17", "Người đứng quay lưng làm nhiều khớp phía trước bị che suốt cửa sổ; quy tắc điền khớp tạo ra hình dáng gần giống tư thế ngã"],
        ["Nằm (hoạt động 11)", "11", "Tư thế cuối giống hệt tư thế sau khi ngã; phân biệt được hay không phụ thuộc vào giai đoạn chuyển tiếp có nằm trong cửa sổ hay không"],
        ["Phần trước khi ngã của đoạn ngã ra sau", "8", "Ranh giới thời điểm bắt đầu ngã khó xác định chính xác đến từng khung hình"],
        ["Nhặt đồ vật (hoạt động 9)", "5", "Thân người hạ thấp nhanh, giống pha đầu của cú ngã về trước"],
        ["Nhảy (hoạt động 10)", "2", "Có gia tốc theo phương thẳng đứng"],
    ],
    widths=[3.8, 1.8, 6.4], fs=9.5, first_col_bold=True)
para("Xét theo người, cảnh báo giả phân bố rất lệch: người số 13 chiếm 25 trường hợp, "
     "người số 10 chiếm 11 và người số 11 chiếm 7. Sự lệch này không phải nhiễu ngẫu "
     "nhiên mà có nguyên nhân cụ thể — người số 13 có tư thế đứng quay lưng lại camera "
     "trong nhiều đoạn. Điều này củng cố kết luận ở mục 5.5: nếu chia dữ liệu ngẫu nhiên "
     "theo cửa sổ, đặc điểm riêng của người số 13 đã xuất hiện trong tập huấn luyện và "
     "toàn bộ nhóm lỗi này sẽ bị che giấu.")
para("Hai nhóm nguyên nhân lớn nhất — người đứng quay lưng và người nằm — đều gợi ý cùng "
     "một hướng khắc phục ở mức hệ thống chứ không phải ở mức mô hình: khai báo vùng "
     "giường và vùng ghế (quy tắc BR-09) sẽ loại bỏ phần lớn nhóm « nằm », còn việc kiểm "
     "tra góc đặt camera khi lắp đặt (UC-06) sẽ giảm nhóm « đứng quay lưng ». Đây là ví "
     "dụ cho thấy vì sao phân tích hệ thống không được tách rời phân tích mô hình.")

h2("5.11. Chuỗi tiền xử lý dữ liệu")
para("Sơ đồ dưới đây tổng hợp toàn bộ các bước biến đổi dữ liệu từ khung hình thô đến "
     "đầu vào của mô hình. Đây là bản mô tả ở mức phân tích; chi tiết từng phép biến đổi "
     "sẽ được đặc tả ở bước Thiết kế.")
figure("h10_pipeline_du_lieu.png", 6.0, "Chuỗi tiền xử lý dữ liệu từ video đến đầu vào mô hình")
para("Ràng buộc bắt buộc: chuỗi tiền xử lý lúc huấn luyện và lúc chạy thực tế phải giống "
     "hệt nhau. Lệch dù chỉ một bước — chẳng hạn chuẩn hoá theo tâm hông của khung hình "
     "đầu thay vì khung hình giữa — là mô hình nhận đầu vào có phân bố khác lúc học. Ở "
     "bước Thiết kế, ràng buộc này được bảo đảm bằng cách cho cả hai luồng dùng chung "
     "một mô-đun xử lý duy nhất.")

h1("PHẦN VI. KIẾN TRÚC HỆ THỐNG MỨC PHÂN TÍCH")

h2("6.1. Sơ đồ thành phần")
para("Phương án xử lý cục bộ đã chọn ở mục A.6 của Khảo sát hiện trạng được cụ thể hoá "
     "thành các khối chức năng. Ranh giới quan trọng nhất trong sơ đồ là đường bao của "
     "máy xử lý đặt tại chỗ: mọi thứ liên quan đến hình ảnh nằm bên trong, chỉ dữ liệu "
     "sự kiện mới được phép đi ra.")
figure("h08_thanh_phan.png", 5.9, "Sơ đồ thành phần của hệ thống")

h2("6.2. Trách nhiệm của từng thành phần")
tcap("Trách nhiệm và dữ liệu của từng thành phần")
table(
    ["Thành phần", "Trách nhiệm", "Đầu vào → Đầu ra", "Yêu cầu liên quan"],
    [
        ["Bộ thu hình", "Đọc luồng hình ảnh, phát hiện mất kết nối", "Luồng camera → khung hình", "FR-01, FR-19"],
        ["Bộ trích khung xương", "Phát hiện người và trích toạ độ 17 khớp", "Khung hình → danh sách khớp", "FR-02"],
        ["Bộ bám người", "Chọn đúng người cần giám sát, nội suy khớp bị che", "Danh sách khớp → khung xương của một người", "FR-03"],
        ["Bộ đệm và chuẩn hoá", "Giữ 32 khung gần nhất, chuẩn hoá cửa sổ", "Khung xương → cửa sổ đã chuẩn hoá", "FR-04"],
        ["Bộ phân loại ST-GCN", "Tính xác suất té ngã của cửa sổ", "Cửa sổ → xác suất", "FR-04"],
        ["Bộ quyết định cảnh báo", "Áp dụng ngưỡng, số lần liên tiếp và quy tắc vùng", "Xác suất → quyết định tạo sự kiện", "FR-05, BR-01, BR-09"],
        ["Bộ leo thang và hẹn giờ", "Quản lý đồng hồ chờ, gửi thông báo theo bậc", "Sự kiện → thông báo", "FR-06 … FR-10, FR-23"],
        ["Bộ giám sát sức khoẻ thiết bị", "Theo dõi kết nối camera, tải máy, điều kiện ánh sáng", "Tín hiệu thiết bị → trạng thái giám sát", "FR-19, FR-20"],
        ["Kho dữ liệu cục bộ", "Lưu cấu hình, sự kiện, nhật ký, ảnh minh hoạ", "—", "FR-13, FR-18, NFR-08"],
        ["Giao diện web", "Màn hình cho người thân, nhân viên trực và kỹ thuật viên", "—", "FR-11 … FR-17, FR-20, FR-21"],
    ],
    widths=[2.8, 3.6, 3.6, 2.0], fs=9.5, first_col_bold=True)
para("Điểm cần lưu ý ở bước Thiết kế: bộ quyết định cảnh báo được tách hẳn khỏi bộ phân "
     "loại. Nhờ vậy, khi cần giảm cảnh báo giả cho một phòng cụ thể, kỹ thuật viên chỉ "
     "chỉnh tham số của bộ quyết định mà không phải huấn luyện lại mô hình.")

h2("6.3. Sơ đồ triển khai")
para("Sơ đồ triển khai cho biết mỗi thành phần phần mềm chạy trên thiết bị vật lý nào và "
     "các thiết bị trao đổi với nhau qua giao thức gì. Đây cũng là nơi thể hiện rõ nhất "
     "ranh giới riêng tư đã cam kết ở NFR-07.")
figure("h11_trien_khai.png", 5.6, "Sơ đồ triển khai của hệ thống")
tcap("Luồng dữ liệu qua các ranh giới")
table(
    ["Ranh giới", "Dữ liệu đi qua", "Dữ liệu KHÔNG được đi qua"],
    [
        ["Camera → máy xử lý (mạng nội bộ)", "Luồng hình ảnh nén", "—"],
        ["Máy xử lý → loa/đèn tại chỗ", "Lệnh phát âm báo", "—"],
        ["Máy xử lý → máy trạm nhân viên trực (mạng nội bộ)", "Danh sách sự kiện, trạng thái phòng, ảnh minh hoạ khi được phép", "Luồng video liên tục"],
        ["Máy xử lý → dịch vụ thông báo (ra Internet)", "Thời điểm, phòng, mức độ tin cậy, mã sự kiện", "Ảnh, khung xương, video, thông tin cá nhân chi tiết"],
    ],
    widths=[4.0, 4.5, 3.5], fs=9.5, first_col_bold=True)

h1("PHẦN VII. MA TRẬN TRUY VẾT VÀ TIÊU CHÍ CHẤP NHẬN")

h2("7.1. Ma trận truy vết")
para("Ma trận truy vết cho phép kiểm tra hai chiều: mỗi yêu cầu đều có ít nhất một use "
     "case và một lớp dữ liệu hiện thực hoá nó; và ngược lại, mỗi lớp dữ liệu đều phục "
     "vụ một yêu cầu có nguồn gốc từ Khảo sát hiện trạng.")
tcap("Ma trận truy vết từ khảo sát đến mô hình dữ liệu")
table(
    ["Nguồn (KSHT)", "Yêu cầu", "Use case", "Lớp dữ liệu liên quan"],
    [
        ["A.3, B.4.1", "FR-01 … FR-05", "UC-01", "Camera, PhienGiamSat, KetQuaNhanDang, SuKienTeNga"],
        ["A.5, B.4.2", "FR-06, FR-07", "UC-02", "SuKienTeNga, QuyTacCanhBao"],
        ["B.4.2", "FR-08 … FR-10, FR-23", "UC-03", "ThongBao, ThuTuLeoThang, NguoiNhanCanhBao"],
        ["B.4.3", "FR-11, FR-12, FR-21", "UC-04", "SuKienTeNga, PhanHoiXuLy"],
        ["B.3", "FR-13", "UC-05", "SuKienTeNga, ThongBao, PhanHoiXuLy"],
        ["B.3, A.2", "FR-14, FR-15", "UC-06", "NguoiDuocGiamSat, Phong, Camera, VungQuanSat"],
        ["B.3, B.4.2", "FR-16 … FR-18", "UC-07", "QuyTacCanhBao, ThuTuLeoThang, NguoiNhanCanhBao"],
        ["A.5, B.4.4", "FR-19, FR-20", "UC-08", "PhienGiamSat, Camera"],
        ["B.5", "NFR-01 … NFR-12", "xuyên suốt", "toàn bộ"],
        ["C.1, C.5, C.6", "FR-04 (phần mô hình)", "UC-01", "KetQuaNhanDang"],
        ["D.3", "NFR-03, NFR-04", "UC-01", "KetQuaNhanDang, PhanHoiXuLy"],
    ],
    widths=[2.2, 3.0, 1.8, 5.0], fs=9.5)

h2("7.2. Tiêu chí chấp nhận")
para("Tiêu chí chấp nhận là điều kiện để hai bên thống nhất rằng một nhóm yêu cầu đã "
     "được hiện thực hoá đúng. Chúng được viết ở dạng có thể kiểm tra được, không dùng "
     "từ ngữ định tính như « nhanh » hay « chính xác ».")
tcap("Tiêu chí chấp nhận theo nhóm chức năng")
table(
    ["Nhóm", "Tiêu chí chấp nhận"],
    [
        ["Phát hiện",
         "1. Chạy lại toàn bộ đoạn video kiểm thử, hệ thống phát hiện được ít nhất 90% số ca ngã.\n"
         "2. Với mỗi ca phát hiện được, khoảng cách từ thời điểm ngã đến thời điểm tạo sự kiện không quá 3 giây.\n"
         "3. Không kiểu ngã nào có tỷ lệ phát hiện dưới 80%."],
        ["Cảnh báo",
         "1. Khi người được giám sát phản hồi trong thời gian chờ, hệ thống không gửi bất kỳ thông báo nào ra ngoài.\n"
         "2. Khi không có phản hồi, thông báo tới người liên hệ bậc một được phát trong vòng 2 giây sau khi hết thời gian chờ.\n"
         "3. Khi người bậc một không xác nhận trong thời hạn, hệ thống tự chuyển sang bậc hai mà không cần thao tác."],
        ["Giám sát hạn chế",
         "1. Rút cáp camera: trong vòng 10 giây, màn hình quản trị hiển thị trạng thái « giám sát hạn chế » và nhật ký ghi thời điểm bắt đầu.\n"
         "2. Cắm lại cáp: nhật ký ghi thời điểm kết thúc và trạng thái trở lại bình thường.\n"
         "3. Ngắt Internet: chức năng phát hiện vẫn hoạt động, thông báo được gửi lại đầy đủ khi có mạng."],
        ["Riêng tư",
         "1. Rà soát lưu lượng mạng đi ra trong một phiên chạy 30 phút: không có gói dữ liệu nào chứa khung hình hoặc luồng video.\n"
         "2. Ảnh minh hoạ chỉ tồn tại với các sự kiện đã gửi ra ngoài.\n"
         "3. Tài khoản không có quyền không xem được thông tin người được giám sát."],
        ["Cấu hình",
         "1. Không lưu được quy tắc cảnh báo có danh sách người nhận rỗng.\n"
         "2. Sau khi đổi ngưỡng, bản cấu hình cũ vẫn tra cứu được kèm thời điểm hiệu lực.\n"
         "3. Vùng loại trừ đã khai báo không sinh cảnh báo trong ít nhất 50 cửa sổ liên tiếp có người trong vùng đó."],
    ],
    widths=[2.4, 9.6], fs=9.5, first_col_bold=True)

h2("7.3. Rủi ro còn lại và giả định cần kiểm chứng")
tcap("Rủi ro còn lại sau giai đoạn phân tích")
table(
    ["Rủi ro", "Mức độ", "Cách ứng phó ở giai đoạn sau"],
    [
        ["Dữ liệu diễn xuất chưa đại diện cho ngã thật của người cao tuổi", "Cao", "Nêu rõ giới hạn trong mọi kết luận; bổ sung cảnh báo nằm lâu bất thường; thu thập dữ liệu diễn xuất gần bối cảnh nhà thật"],
        ["Tỷ lệ ngã ra sau bị bỏ sót còn 24,4%", "Cao", "Ưu tiên cải thiện nhóm này: bổ sung dữ liệu, thử bộ trích khung xương mạnh hơn, đánh giá riêng cho nhóm"],
        ["Số cảnh báo giả trong nhà thật có thể cao hơn trong phòng thí nghiệm", "Cao", "Đo số báo giả theo ngày trên dữ liệu dài; kết hợp khai báo vùng giường/ghế và cơ chế xác nhận tại chỗ"],
        ["Camera có vùng mù hoặc chất lượng hình ảnh kém", "Trung bình", "Hỗ trợ kiểm tra góc đặt khi lắp, khai báo vùng mù, thông báo khi giám sát bị hạn chế"],
        ["Phần cứng giá thấp chưa chắc đáp ứng thời gian thực", "Trung bình", "Đo hiệu năng sớm trên phần cứng dự kiến; chuẩn bị phương án giảm tải có kiểm soát"],
        ["Người dùng tắt hệ thống vì phiền", "Trung bình", "Thiết kế xác nhận tại chỗ ngắn gọn; cho phép đánh dấu báo sai để hiệu chỉnh"],
        ["Chuỗi tiền xử lý lúc huấn luyện và lúc chạy bị lệch nhau", "Trung bình", "Bắt buộc dùng chung một mô-đun xử lý; kiểm thử đối chiếu đầu ra hai luồng"],
    ],
    widths=[4.2, 1.6, 6.2], fs=9.5, first_col_bold=True)

h1("PHẦN VIII. KẾT LUẬN VÀ CHUYỂN GIAO SANG GIAI ĐOẠN THIẾT KẾ")

h2("8.1. Tóm tắt kết quả phân tích")
para("Giai đoạn phân tích đã chuyển toàn bộ nội dung tường thuật của Khảo sát hiện trạng "
     "thành các mô hình có cấu trúc: sáu tác nhân, hai mươi bốn yêu cầu chức năng, mười "
     "hai yêu cầu phi chức năng, mười hai quy tắc nghiệp vụ, tám use case, năm mô hình "
     "xử lý và mười hai lớp dữ liệu. Mỗi thành phần đều truy ngược được về một mục cụ "
     "thể trong khảo sát, như ma trận ở mục 7.1 thể hiện.")
para("Về phần dữ liệu, bài toán học máy đã được phát biểu ở dạng hình thức, dữ liệu "
     "nguồn đã được kiểm kê và phân tích đặc điểm, năm phương án mô hình đã được so sánh "
     "theo ma trận quyết định có trọng số, và phương án khung xương kết hợp ST-GCN được "
     "chọn với lập luận rõ ràng. Kết quả tiền khả thi đạt các chỉ tiêu đặt ra ở mức cửa "
     "sổ và mức sự kiện, ngoại trừ chỉ tiêu số cảnh báo giả theo ngày chưa đủ dữ liệu để "
     "kết luận.")
para("Ba rủi ro học tắt đã được phát hiện và xử lý ngay ở giai đoạn này, với bằng chứng "
     "đối chứng cụ thể. Nếu không phát hiện, hệ thống vẫn cho ra con số đánh giá trông "
     "chấp nhận được nhưng sẽ hỏng khi gặp người dùng thật.")

h2("8.2. Những điểm cần bổ sung ngược về Khảo sát hiện trạng")
para("Đúng theo tinh thần « nếu phân tích thấy chưa ổn thì phải quay lại bổ sung khảo "
     "sát », quá trình mô hình hoá đã phát hiện một số chỗ mà bản khảo sát hiện tại còn "
     "chưa đủ chi tiết để mô hình hoá chắc chắn.")
tcap("Nội dung cần bổ sung vào bản Khảo sát hiện trạng kế tiếp")
table(
    ["Nội dung còn thiếu", "Vì sao cần", "Ảnh hưởng tới mô hình nào"],
    [
        ["Quy trình bàn giao ca trực ở viện dưỡng lão diễn ra cụ thể như thế nào", "Đang phải giả định khi đặc tả FR-22 và UC-04", "Use case UC-04, lớp PhanHoiXuLy"],
        ["Ai được xem ảnh minh hoạ và trong bao lâu", "Đang phải tự đặt mặc định 30 ngày cho NFR-08", "Ràng buộc RB-10, chính sách lưu trữ mục 4.5"],
        ["« Chỉ dẫn đã thống nhất trước » ở BR-06 gồm những bước nào", "Hiện chỉ nêu ví dụ gọi điện trực tiếp, chưa đủ để đặc tả", "Use case UC-03, máy trạng thái mục 3.3"],
        ["Một người được giám sát có thể ở nhiều phòng trong ngày không", "Ảnh hưởng trực tiếp đến bản số của mối kết hợp « ở tại »", "Sơ đồ lớp mục 4.1, ràng buộc RB-09"],
        ["Số phòng tối đa mà một nhân viên trực theo dõi cùng lúc", "Quyết định cách sắp xếp ưu tiên ở FR-21 và thiết kế màn hình", "Yêu cầu FR-21, use case UC-08"],
        ["Người cao tuổi phản hồi « Tôi ổn » bằng cách nào là khả thi nhất", "Nút bấm, giọng nói hay cử chỉ đều có ưu nhược khác nhau", "Use case UC-02, yêu cầu NFR-11"],
    ],
    widths=[4.0, 4.4, 3.6], fs=9.5, first_col_bold=True)

h2("8.3. Đầu vào bàn giao cho bước Thiết kế")
para("Bảng dưới đây liệt kê chính xác những gì bước Thiết kế nhận được từ báo cáo này và "
     "sẽ chuyển thành sản phẩm gì. Đây là đường nối giữa hai giai đoạn, tương tự cách "
     "kiến trúc sư dùng bản vẽ ý tưởng để vẽ ra bản vẽ thi công.")
tcap("Ánh xạ từ kết quả phân tích sang sản phẩm của bước Thiết kế")
table(
    ["Kết quả phân tích", "Sản phẩm tương ứng ở bước Thiết kế"],
    [
        ["Sơ đồ lớp và từ điển lớp (mục 4.1, 4.2)", "Lược đồ cơ sở dữ liệu sau khi phân rã về dạng chuẩn 3: tên bảng, khoá chính, kiểu và độ dài từng cột"],
        ["Bảng mối kết hợp và bản số (mục 4.3)", "Khoá ngoại, bảng trung gian cho quan hệ nhiều–nhiều, chỉ mục truy vấn"],
        ["Ràng buộc toàn vẹn (mục 4.4)", "Ràng buộc miền giá trị, liên thuộc tính, liên bộ và liên bảng ở mức cơ sở dữ liệu"],
        ["Đặc tả use case (mục 2.3)", "Mã giả của từng thủ tục xử lý, bảng quyết định cho các nhánh rẽ phức tạp"],
        ["Máy trạng thái Sự kiện té ngã (mục 3.3)", "Bảng chuyển trạng thái cài đặt được, kèm điều kiện bảo vệ từng chuyển đổi"],
        ["Sơ đồ hoạt động và tuần tự (mục 3.1, 3.2, 3.4)", "Thiết kế màn hình, biểu mẫu và các thông báo hiển thị cho người dùng"],
        ["Chuỗi tiền xử lý dữ liệu (mục 5.11)", "Đặc tả chi tiết từng phép biến đổi: công thức chuẩn hoá, quy tắc nội suy, quy tắc điền khớp bị che"],
        ["Cấu hình mô hình (mục 5.7)", "Thiết kế mô-đun huấn luyện và mô-đun suy luận, cách lưu và nạp trọng số"],
        ["Tiêu chí đánh giá ba mức (mục 5.8)", "Thiết kế bộ chỉ số và báo cáo đánh giá tự động"],
        ["Sơ đồ thành phần và triển khai (mục 6.1, 6.3)", "Giao diện lập trình giữa các mô-đun, cấu hình triển khai, kịch bản cài đặt"],
        ["Tiêu chí chấp nhận (mục 7.2)", "Bộ ca kiểm thử chi tiết và kịch bản kiểm thử chấp nhận"],
    ],
    widths=[4.6, 7.4], fs=9.5, first_col_bold=True)
para("Sau bước Thiết kế, các sản phẩm ở cột bên phải sẽ được chuyển cho giai đoạn thi "
     "công. Ở giai đoạn đó, báo cáo sẽ ghi nhận kết quả thực nghiệm thực tế và đối chiếu "
     "với các chỉ tiêu đã cam kết ở mục 1.4 và mục 5.8 của tài liệu này.")

h1("TÀI LIỆU THAM KHẢO")
for ref in [
    "[1] Nguyễn Đinh Hồng Ngọc. Khảo sát hiện trạng — Hệ thống phát hiện té ngã ở người "
    "cao tuổi dựa trên camera và phân tích chuyển động. Đồ án ngành, Trường Đại học Mở "
    "Thành phố Hồ Chí Minh, 2026.",
    "[2] Yan, S., Xiong, Y., Lin, D. Spatial Temporal Graph Convolutional Networks for "
    "Skeleton-Based Action Recognition. AAAI, 2018.",
    "[3] Martínez-Villaseñor, L. và cộng sự. UP-Fall Detection Dataset: A Multimodal "
    "Approach. Sensors, 19(9), 1988, 2019.",
    "[4] World Health Organization. Falls. 2021.",
    "[5] Vision-based human fall detection systems using deep learning: A review. "
    "Engineering Applications of Artificial Intelligence, 2024.",
    "[6] Artificial intelligence for fall detection in older adults: A comprehensive "
    "survey of machine learning, deep learning approaches, and future directions. 2025.",
    "[7] Ultralytics. YOLOv8 Pose Estimation — tài liệu kỹ thuật chính thức. "
    "https://docs.ultralytics.com/tasks/pose/",
    "[8] Booch, G., Rumbaugh, J., Jacobson, I. The Unified Modeling Language User Guide. "
    "Addison-Wesley, tái bản lần 2.",
    "[9] Larman, C. Applying UML and Patterns: An Introduction to Object-Oriented "
    "Analysis and Design and Iterative Development. Prentice Hall, tái bản lần 3.",
    "[10] Kwolek, B., Kepski, M. Human fall detection on embedded platform using depth "
    "maps and wireless accelerometer.",
]:
    para(ref, 12.5, align="justify", indent=0.5, space_after=5)

footer_page_number()
OUT.parent.mkdir(parents=True, exist_ok=True)
doc.save(OUT)
print(f"Đã tạo: {OUT}")
print(f"Số hình: {FIG_N[0]} | Số bảng: {TAB_N[0]}")
