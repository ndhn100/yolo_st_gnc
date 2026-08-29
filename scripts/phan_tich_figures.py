# -*- coding: utf-8 -*-
"""Sinh các hình minh hoạ cho báo cáo Phân tích hệ thống.

Chạy:  venv\\Scripts\\python.exe scripts\\phan_tich_figures.py
Kết quả: docs/assets_phantich/*.png
"""
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import (Circle, Ellipse, FancyArrowPatch, FancyBboxPatch,
                                Polygon, Rectangle)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "assets_phantich"
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams["font.family"] = "DejaVu Sans"

NAVY = "#1F4E78"
FILL = "#EAF2F8"
FILL2 = "#FDEBD0"
FILL3 = "#E8F6EF"
ORANGE = "#B9770E"
RED = "#C0392B"
REDF = "#FADBD8"
GREEN = "#1E8449"
GRAY = "#566573"
GRAYF = "#EAECEE"


def new_ax(w, h, xlim=(0, 100), ylim=(0, 100)):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.axis("off")
    ax.invert_yaxis()
    return fig, ax


def box(ax, x, y, w, h, text, fc=FILL, ec=NAVY, fs=8.5, bold=False, lw=1.6,
        rounding=1.6, tc=None, z=2):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle=f"round,pad=0,rounding_size={rounding}",
                                fc=fc, ec=ec, lw=lw, zorder=z))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            fontweight="bold" if bold else "normal",
            color=tc or "#17365D", zorder=z + 1, linespacing=1.35)
    return (x, y, w, h)


def side(b, where):
    x, y, w, h = b
    return {"t": (x + w / 2, y), "b": (x + w / 2, y + h),
            "l": (x, y + h / 2), "r": (x + w, y + h / 2),
            "c": (x + w / 2, y + h / 2)}[where]


def arrow(ax, p1, p2, color=NAVY, lw=1.6, style="-|>", ls="-", rad=0.0,
          text=None, fs=7.5, toff=(0, -1.8), tcolor=None, z=6):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle=style, mutation_scale=13,
                                 color=color, lw=lw, linestyle=ls, zorder=z,
                                 connectionstyle=f"arc3,rad={rad}",
                                 shrinkA=0.5, shrinkB=0.5))
    if text:
        mx = (p1[0] + p2[0]) / 2 + toff[0]
        my = (p1[1] + p2[1]) / 2 + toff[1]
        ax.text(mx, my, text, ha="center", va="center", fontsize=fs,
                color=tcolor or color, zorder=z + 2,
                bbox=dict(fc="white", ec="none", pad=0.8), linespacing=1.25)


def path(ax, pts, color=NAVY, lw=1.6, ls="-", head=True, text=None,
         text_at=None, fs=7.5, tcolor=None, z=6):
    """Đường gấp khúc qua danh sách điểm, đầu mũi tên ở đoạn cuối."""
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    ax.plot(xs[:-1] + [xs[-1]], ys[:-1] + [ys[-1]], color=color, lw=lw,
            ls=ls, zorder=z, solid_joinstyle="round")
    if head:
        ax.add_patch(FancyArrowPatch(pts[-2], pts[-1], arrowstyle="-|>",
                                     mutation_scale=13, color=color, lw=lw,
                                     linestyle=ls, zorder=z, shrinkA=0, shrinkB=0))
    if text:
        tx, ty = text_at if text_at else pts[len(pts) // 2]
        ax.text(tx, ty, text, ha="center", va="center", fontsize=fs,
                color=tcolor or color, zorder=z + 2,
                bbox=dict(fc="white", ec="none", pad=0.8), linespacing=1.25)


def actor(ax, x, y, name, s=1.0, color=NAVY):
    ax.add_patch(Circle((x, y), 1.7 * s, fc="white", ec=color, lw=1.6, zorder=3))
    ax.plot([x, x], [y + 1.7 * s, y + 6.2 * s], color=color, lw=1.6, zorder=3)
    ax.plot([x - 3.2 * s, x + 3.2 * s], [y + 3.2 * s, y + 3.2 * s], color=color, lw=1.6, zorder=3)
    ax.plot([x, x - 2.8 * s], [y + 6.2 * s, y + 10.5 * s], color=color, lw=1.6, zorder=3)
    ax.plot([x, x + 2.8 * s], [y + 6.2 * s, y + 10.5 * s], color=color, lw=1.6, zorder=3)
    ax.text(x, y + 13.5 * s, name, ha="center", va="top", fontsize=8.5,
            fontweight="bold", color=color, linespacing=1.3)


def start_node(ax, x, y, r=2.0):
    ax.add_patch(Circle((x, y), r, fc=NAVY, ec=NAVY, zorder=4))


def end_node(ax, x, y, r=2.6):
    ax.add_patch(Circle((x, y), r, fc="white", ec=NAVY, lw=1.6, zorder=4))
    ax.add_patch(Circle((x, y), r * 0.55, fc=NAVY, ec=NAVY, zorder=5))


def diamond(ax, cx, cy, hw, hh, text, fs=7.8):
    ax.add_patch(Polygon([(cx, cy - hh), (cx + hw, cy), (cx, cy + hh), (cx - hw, cy)],
                         closed=True, fc=FILL2, ec=ORANGE, lw=1.6, zorder=2))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fs, color="#7E5109",
            zorder=3, linespacing=1.3)


def save(fig, name):
    fig.savefig(OUT / name, dpi=200, bbox_inches="tight", pad_inches=0.08,
                facecolor="white")
    plt.close(fig)
    print("  ->", name)


# ================================================================ H1 ngữ cảnh
def fig_context():
    fig, ax = new_ax(11, 5.6)
    core = box(ax, 34, 34, 32, 26,
               "HỆ THỐNG PHÁT HIỆN\nTÉ NGÃ Ở NGƯỜI CAO TUỔI\n(phạm vi xây dựng)",
               fc="#D4E6F1", fs=11, bold=True, lw=2.4, rounding=2)
    actor(ax, 8, 12, "Người cao tuổi\n(người được giám sát)")
    actor(ax, 8, 62, "Người thân /\nngười chăm sóc")
    actor(ax, 92, 12, "Nhân viên trực\n(điều dưỡng)")
    actor(ax, 92, 62, "Kỹ thuật viên")

    cam = box(ax, 40, 6, 20, 11, "Camera IP\n(hệ thống ngoài)", fc=GRAYF, ec=GRAY)
    kenh = box(ax, 38, 78, 24, 11, "Dịch vụ thông báo\n(SMS / push / email)", fc=GRAYF, ec=GRAY)

    arrow(ax, (55, 17), (52, 34), text="luồng hình ảnh", toff=(9, 0))
    arrow(ax, side(core, "b"), side(kenh, "t"), text="yêu cầu gửi cảnh báo", toff=(0, 2.4))
    arrow(ax, (14, 20), (34, 40), text="âm báo, xác nhận tại chỗ", toff=(1, -2.6))
    arrow(ax, (14, 66), (34, 52), text="tiếp nhận / đánh dấu báo sai", toff=(2, 2.8))
    arrow(ax, (86, 20), (66, 40), text="theo dõi nhiều phòng", toff=(-1, -2.6))
    arrow(ax, (86, 66), (66, 52), text="khai báo, hiệu chỉnh", toff=(-2, 2.8))
    save(fig, "h01_ngu_canh.png")


# ================================================================ H2 use case
def fig_usecase():
    fig, ax = new_ax(11.5, 7.4)
    ax.add_patch(Rectangle((20, 3), 70, 94, fc="#FBFDFE", ec=NAVY, lw=2, zorder=0))
    ax.text(55, 7, "Hệ thống phát hiện té ngã", ha="center", va="center",
            fontsize=11, fontweight="bold", color=NAVY, zorder=3)

    def uc(cx, cy, w, label):
        ax.add_patch(Ellipse((cx, cy), w, 9.5, fc=FILL, ec=NAVY, lw=1.5, zorder=2))
        ax.text(cx, cy, label, ha="center", va="center", fontsize=8.2,
                color="#17365D", zorder=3, linespacing=1.3)
        return (cx, cy, w / 2)

    u1 = uc(40, 18, 32, "UC-01\nGiám sát và\nphát hiện té ngã")
    u2 = uc(40, 40, 32, "UC-02\nXác nhận tại chỗ")
    u3 = uc(40, 62, 32, "UC-03\nLeo thang cảnh báo")
    u4 = uc(40, 84, 32, "UC-04\nTiếp nhận và\nphản hồi cảnh báo")
    u5 = uc(74, 18, 28, "UC-05\nXem lịch sử sự kiện")
    u6 = uc(74, 40, 28, "UC-06\nKhai báo\nngười – phòng – camera")
    u7 = uc(74, 62, 28, "UC-07\nCấu hình\nquy tắc cảnh báo")
    u8 = uc(74, 84, 28, "UC-08\nTheo dõi\ntrạng thái giám sát")

    actor(ax, 6, 14, "Người\ncao tuổi", s=0.85)
    actor(ax, 6, 52, "Người thân /\nnhân viên trực", s=0.85)
    actor(ax, 96, 34, "Kỹ thuật\nviên", s=0.85)
    actor(ax, 6, 84, "Camera\n(tác nhân phụ)", s=0.85)

    def link(ax_, ap, u, ls="-"):
        ax_.plot([ap[0], u[0] - u[2]], [ap[1], u[1]], color=NAVY, lw=1.2,
                 ls=ls, zorder=1)

    link(ax, (10, 20), u1)
    link(ax, (10, 20), u2)
    link(ax, (10, 90), u1, ls=":")
    for u in (u3, u4, u5, u8):
        link(ax, (10, 58), u)
    for u in (u6, u7, u8):
        ax.plot([92, u[0] + u[2]], [40, u[1]], color=NAVY, lw=1.2, zorder=1)

    arrow(ax, (40, 22.8), (40, 35.2), color=GRAY, ls="--", lw=1.2,
          text="«include»", fs=7.2, toff=(0, 0), tcolor=GRAY)
    arrow(ax, (40, 57.2), (40, 44.8), color=GRAY, ls="--", lw=1.2,
          text="«extend»", fs=7.2, toff=(0, 0), tcolor=GRAY)
    arrow(ax, (40, 66.8), (40, 79.2), color=GRAY, ls="--", lw=1.2,
          text="«include»", fs=7.2, toff=(0, 0), tcolor=GRAY)
    save(fig, "h02_use_case.png")


# ======================================================== H3 hoạt động phát hiện
def fig_act_detect():
    fig, ax = new_ax(7.4, 10.0, ylim=(0, 112))
    start_node(ax, 50, 4)
    y = 9
    steps = [
        ("Nhận khung hình từ camera", FILL, NAVY),
        ("Phát hiện người bằng YOLO-Pose\n(17 khớp cơ thể)", FILL, NAVY),
        ("Bám đúng người cần giám sát\ngiữa các khung hình", FILL, NAVY),
        ("Nội suy khớp bị che, đưa khung xương\nvào bộ đệm 32 khung", FILL, NAVY),
        ("Chuẩn hoá cửa sổ: tịnh tiến theo tâm hông,\nchia độ dài thân", FILL, NAVY),
        ("Phân loại chuỗi bằng ST-GCN → P(té ngã)", FILL3, GREEN),
    ]
    boxes = []
    for text, fc, ec in steps:
        boxes.append(box(ax, 16, y, 68, 8.6, text, fc=fc, ec=ec, fs=8.4))
        y += 12.2
    arrow(ax, (50, 6.2), side(boxes[0], "t"))
    for i in range(len(boxes) - 1):
        arrow(ax, side(boxes[i], "b"), side(boxes[i + 1], "t"))

    dy = y + 3
    diamond(ax, 50, dy + 6, 26, 6.5, "P ≥ ngưỡng 0,85\ntrong 2 lần liên tiếp?", fs=8.2)
    arrow(ax, side(boxes[-1], "b"), (50, dy - 0.5))

    b_no = box(ax, 2, dy + 18, 42, 9, "Ghi nhận trạng thái bình thường,\ntiếp tục giám sát",
               fc=GRAYF, ec=GRAY, fs=8.2)
    b_yes = box(ax, 56, dy + 18, 42, 9, "Tạo Sự kiện té ngã\ntrạng thái « Nghi ngờ »",
                fc=REDF, ec=RED, fs=8.2)
    path(ax, [(24, dy + 6), (23, dy + 6), (23, dy + 18)], color=GRAY,
         text="Không", text_at=(15, dy + 12), tcolor=GRAY)
    path(ax, [(76, dy + 6), (77, dy + 6), (77, dy + 18)], color=RED,
         text="Có", text_at=(85, dy + 12), tcolor=RED)

    b_lim = box(ax, 2, dy + 34, 42, 9,
                "Nếu mất kết nối / ảnh quá tối:\nchuyển « Giám sát hạn chế »",
                fc="#FCF3CF", ec=ORANGE, fs=8.2)
    arrow(ax, side(b_no, "b"), side(b_lim, "t"), color=GRAY)
    arrow(ax, side(b_yes, "b"), (77, dy + 36), color=RED)
    ax.text(77, dy + 39, "sang quy trình\nxác nhận – leo thang", ha="center",
            va="top", fontsize=8.4, color=RED, fontweight="bold", linespacing=1.3)
    save(fig, "h03_hoat_dong_phat_hien.png")


# ======================================================= H4 xác nhận / leo thang
def fig_act_escalate():
    fig, ax = new_ax(11, 7.2)
    lanes = [("Hệ thống", 0, 33), ("Người cao tuổi", 33, 27), ("Người nhận cảnh báo", 60, 40)]
    for name, x0, w in lanes:
        ax.add_patch(Rectangle((x0, 0), w, 100, fc="white", ec=NAVY, lw=1.4, zorder=0))
        ax.add_patch(Rectangle((x0, 0), w, 6, fc="#D4E6F1", ec=NAVY, lw=1.4, zorder=1))
        ax.text(x0 + w / 2, 3, name, ha="center", va="center", fontsize=9.5,
                fontweight="bold", color=NAVY, zorder=3)

    start_node(ax, 16, 10, 1.8)
    b1 = box(ax, 3, 13, 27, 8, "Phát âm báo tại chỗ,\nbật hẹn giờ chờ xác nhận", fs=8)
    b2 = box(ax, 35, 13, 23, 8, "Đứng dậy hoặc\nbấm « Tôi ổn »", fc=FILL3, ec=GREEN, fs=8)
    diamond(ax, 16, 30, 14, 6, "Có phản hồi\ntrong thời hạn?")
    b3 = box(ax, 3, 40, 27, 8, "Hạ mức sự kiện,\nghi vào lịch sử", fc=FILL3, ec=GREEN, fs=8)
    b4 = box(ax, 62, 24, 36, 8, "Nhận cảnh báo: thời điểm, phòng,\nmức tin cậy, ảnh minh hoạ",
             fc=REDF, ec=RED, fs=8)
    diamond(ax, 80, 42, 16, 6, "Xác nhận tiếp nhận\ntrong thời hạn?")
    b5 = box(ax, 62, 52, 36, 8, "Ghi « Đã tiếp nhận »,\nkèm người xử lý", fc=FILL3, ec=GREEN, fs=8)
    b6 = box(ax, 3, 60, 27, 9, "Chuyển sang người liên hệ\nkế tiếp theo thứ tự leo thang",
             fc=REDF, ec=RED, fs=8)
    b7 = box(ax, 3, 76, 27, 10, "Hết danh sách: duy trì mức cao,\nthực hiện chỉ dẫn\nđã thống nhất trước",
             fc=REDF, ec=RED, fs=8)
    b8 = box(ax, 62, 68, 36, 8, "Ghi nhận kết quả: sự cố thật /\nbáo sai + ghi chú", fs=8)

    arrow(ax, (16, 11.8), side(b1, "t"))
    arrow(ax, side(b1, "r"), side(b2, "l"), ls="--", color=GRAY)
    arrow(ax, side(b1, "b"), (16, 24))
    arrow(ax, side(b2, "b"), (22, 26.5), ls="--", color=GREEN, rad=0.25)
    arrow(ax, (16, 36), side(b3, "t"), text="Có", toff=(-3.5, 0), color=GREEN)
    path(ax, [(30, 30), (46, 30), (46, 28), (62, 28)], color=RED,
         text="Không / hết hạn", text_at=(46, 24.5), tcolor=RED)
    arrow(ax, side(b4, "b"), (80, 36))
    arrow(ax, (80, 48), side(b5, "t"), text="Có", toff=(-3.5, 0), color=GREEN)
    path(ax, [(64, 42), (48, 42), (48, 64), (30, 64)], color=RED,
         text="Không / hết hạn", text_at=(48, 55), tcolor=RED)
    arrow(ax, side(b6, "b"), side(b7, "t"), color=RED)
    arrow(ax, side(b5, "b"), side(b8, "t"), color=GREEN)
    arrow(ax, (30, 81), (62, 72), ls="--", color=GRAY)
    path(ax, [(3, 44), (1, 44), (1, 92), (13, 92)], color=GREEN, head=True)
    end_node(ax, 16, 92)
    arrow(ax, side(b7, "b"), (16, 89.4), color=RED)
    end_node(ax, 80, 84)
    arrow(ax, side(b8, "b"), (80, 81.4))
    save(fig, "h04_hoat_dong_leo_thang.png")


# ==================================================== H5 máy trạng thái sự kiện
def fig_state():
    fig, ax = new_ax(11, 5.4, ylim=(0, 106))
    start_node(ax, 3, 33)
    s1 = box(ax, 8, 26, 20, 14, "Nghi ngờ", fc=FILL2, ec=ORANGE, fs=10.5, bold=True)
    s2 = box(ax, 34, 26, 22, 14, "Chờ xác nhận\ntại chỗ", fc=FILL2, ec=ORANGE, fs=10, bold=True)
    s3 = box(ax, 64, 4, 22, 14, "Đang leo thang", fc=REDF, ec=RED, fs=10, bold=True)
    s5 = box(ax, 64, 30, 22, 14, "Đã tiếp nhận", fc=FILL3, ec=GREEN, fs=10, bold=True)
    s4 = box(ax, 64, 56, 22, 14, "Đã tự xác nhận\nan toàn", fc=FILL3, ec=GREEN, fs=9.5, bold=True)
    s6 = box(ax, 30, 76, 24, 14, "Đã đóng\n(sự cố thật / báo sai)", fc=GRAYF, ec=GRAY, fs=9.5, bold=True)

    arrow(ax, (5, 33), side(s1, "l"))
    arrow(ax, side(s1, "r"), side(s2, "l"), text="phát âm báo", toff=(0, -2.6))
    path(ax, [(56, 33), (60, 33), (60, 11), (64, 11)], color=RED,
         text="hết thời hạn chờ", text_at=(60, 20), tcolor=RED)
    path(ax, [(56, 33), (60, 33), (60, 63), (64, 63)], color=GREEN,
         text="người dùng phản hồi", text_at=(60, 48), tcolor=GREEN)
    arrow(ax, side(s3, "b"), side(s5, "t"), color=GREEN,
          text="người nhận xác nhận", toff=(0, 0))
    path(ax, [(86, 37), (95, 37), (95, 72), (42, 72), (42, 76)], color=NAVY,
         text="ghi kết quả xử lý", text_at=(70, 69.5))
    path(ax, [(75, 70), (75, 95), (42, 95), (42, 90)], color=GREEN,
         text="tự động lưu lịch sử", text_at=(58, 95), tcolor=GREEN)
    end_node(ax, 14, 83)
    arrow(ax, side(s6, "l"), (16.6, 83))
    ax.text(50, 103, "Mọi chuyển trạng thái đều được ghi nhật ký kèm thời điểm và người thực hiện",
            ha="center", fontsize=8.5, style="italic", color=GRAY)
    save(fig, "h05_trang_thai_su_kien.png")


# ================================================================= H6 tuần tự
def fig_sequence():
    fig, ax = new_ax(11.5, 6.4)
    objs = [("Camera", 8), ("Bộ trích\nkhung xương", 24), ("Bộ phân loại\nST-GCN", 41),
            ("Bộ quyết định\ncảnh báo", 58), ("Kho dữ liệu", 74), ("Người nhận\ncảnh báo", 91)]
    for name, x in objs:
        box(ax, x - 7.4, 2, 14.8, 8, name, fc="#D4E6F1", fs=8, bold=True)
        ax.plot([x, x], [10, 96], color=GRAY, lw=1.0, ls="--", zorder=0)

    for x, y0, y1 in [(24, 14, 30), (41, 24, 40), (58, 34, 96),
                      (74, 53, 59), (91, 71, 86), (74, 89, 95)]:
        ax.add_patch(Rectangle((x - 1.3, y0), 2.6, y1 - y0, fc="#AED6F1",
                               ec=NAVY, lw=1.0, zorder=2))

    msgs = [
        (8, 24, 16, "1: khung hình (≈18 hình/giây)"),
        (24, 41, 26, "2: cửa sổ 32 khung đã chuẩn hoá"),
        (41, 58, 36, "3: P(té ngã) = 0,93"),
        (58, 74, 55, "5: tạo Sự kiện té ngã « Nghi ngờ »"),
        (58, 91, 73, "7: gửi cảnh báo cho người liên hệ thứ nhất"),
        (91, 58, 84, "8: xác nhận đã tiếp nhận"),
        (58, 74, 91, "9: cập nhật trạng thái + ghi nhật ký"),
    ]
    for x1, x2, y, text in msgs:
        d = 1.4 if x2 > x1 else -1.4
        arrow(ax, (x1 + d, y), (x2 - d, y), lw=1.3, z=8)
        ax.text((x1 + x2) / 2, y - 2.4, text, ha="center", fontsize=7.6,
                color="#17365D", zorder=9,
                bbox=dict(fc="white", ec="none", pad=0.6))
    for y, text in [(43, "4: kiểm tra ngưỡng × số lần liên tiếp"),
                    (62, "6: bật loa/đèn tại chỗ, chờ xác nhận hết thời hạn")]:
        ax.add_patch(FancyArrowPatch((59.4, y), (59.4, y + 5),
                                     connectionstyle="arc3,rad=-2.0",
                                     arrowstyle="-|>", mutation_scale=11, color=NAVY,
                                     lw=1.3, zorder=8))
        ax.text(67, y + 2, text, fontsize=7.6, va="center", color="#17365D", zorder=9)
    ax.text(50, 100, "Đường nét đứt = thời gian sống của thành phần;  thanh đậm = khoảng thời gian đang xử lý",
            ha="center", fontsize=8, style="italic", color=GRAY)
    save(fig, "h06_tuan_tu_canh_bao.png")


# =================================================================== H7 lớp
def uml_class(ax, x, y, w, title, attrs, fc=FILL, ec=NAVY, fs=7.2):
    hh, lh = 5.2, 3.1
    ah = lh * len(attrs) + 1.8
    ax.add_patch(Rectangle((x, y), w, hh, fc="#D4E6F1", ec=ec, lw=1.5, zorder=2))
    ax.text(x + w / 2, y + hh / 2, title, ha="center", va="center", fontsize=fs + 1.1,
            fontweight="bold", color="#17365D", zorder=3)
    ax.add_patch(Rectangle((x, y + hh), w, ah, fc=fc, ec=ec, lw=1.5, zorder=2))
    ty = y + hh + 2.0
    for a in attrs:
        ax.text(x + 1.4, ty, "• " + a, ha="left", va="center", fontsize=fs,
                color="#17365D", zorder=3)
        ty += lh
    return (x, y, w, hh + ah)


def fig_class():
    fig, ax = new_ax(13.5, 9.6, ylim=(0, 108))
    C1, C2, C3 = 1, 37, 71
    W1, W2, W3 = 26, 26, 25
    R1, R2, R3, R4 = 2, 29, 56, 83

    c_ng = uml_class(ax, C1, R1, W1, "NguoiDuocGiamSat",
                     ["maNguoi «định danh»", "hoTen", "namSinh", "ghiChuNguyCoNga"])
    c_ph = uml_class(ax, C2, R1, W2, "Phong",
                     ["maPhong «định danh»", "tenPhong", "loaiKhongGian", "diaDiem"])
    c_cam = uml_class(ax, C3, R1, W3, "Camera",
                      ["maCamera «định danh»", "tenCamera", "duongDanLuong",
                       "gocDat", "trangThaiKetNoi"])
    c_nn = uml_class(ax, C1, R2, W1, "NguoiNhanCanhBao",
                     ["maNguoiNhan «định danh»", "hoTen", "vaiTro", "kenhLienLac"])
    c_qt = uml_class(ax, C2, R2, W2, "QuyTacCanhBao",
                     ["maQuyTac «định danh»", "nguongTinCay", "soLanLienTiep",
                      "thoiGianChoXacNhan", "khungGioApDung"])
    c_pg = uml_class(ax, C3, R2, W3, "PhienGiamSat",
                     ["maPhien «định danh»", "thoiDiemBatDau", "thoiDiemKetThuc",
                      "trangThaiGiamSat"])
    c_lt = uml_class(ax, C1, R3, W1, "ThuTuLeoThang",
                     ["thuTuUuTien", "thoiHanPhanHoi", "trangThaiApDung"],
                     fc=FILL2, ec=ORANGE)
    c_kq = uml_class(ax, C2, R3, W2, "KetQuaNhanDang",
                     ["maKetQua «định danh»", "thoiDiem", "xacSuatTeNga", "nhanDuDoan"],
                     fc=FILL3, ec=GREEN)
    c_vq = uml_class(ax, C3, R3, W3, "VungQuanSat",
                     ["maVung «định danh»", "loaiVung {giường|ghế|", "   loại trừ}",
                      "toaDoDaGiac"])
    c_tb = uml_class(ax, C1, R4, W1, "ThongBao",
                     ["maThongBao «định danh»", "thoiDiemGui", "kenhGui", "trangThaiGui"],
                     fc=REDF, ec=RED)
    c_sk = uml_class(ax, C2, R4, W2, "SuKienTeNga",
                     ["maSuKien «định danh»", "thoiDiemPhatHien", "mucDoTinCay",
                      "trangThai", "anhMinhHoa"], fc=REDF, ec=RED)
    c_ph2 = uml_class(ax, C3, R4, W3, "PhanHoiXuLy",
                      ["maPhanHoi «định danh»", "thoiDiemPhanHoi",
                       "ketLuan {thật|báo sai}", "ghiChu"], fc=FILL3, ec=GREEN)

    def hlink(a, b, m1, m2, name, y):
        x1, x2 = a[0] + a[2], b[0]
        ax.plot([x1, x2], [y, y], color=NAVY, lw=1.3, zorder=1)
        ax.text(x1 + 1.6, y - 1.6, m1, fontsize=7, color=GRAY, ha="left")
        ax.text(x2 - 1.6, y - 1.6, m2, fontsize=7, color=GRAY, ha="right")
        ax.text((x1 + x2) / 2, y + 2.0, name, fontsize=7, color=NAVY, ha="center",
                bbox=dict(fc="white", ec="none", pad=0.6))

    def vlink(a, b, m1, m2, name, x, ls="-"):
        y1, y2 = a[1] + a[3], b[1]
        ax.plot([x, x], [y1, y2], color=NAVY, lw=1.3, ls=ls, zorder=1)
        ax.text(x + 1.2, y1 + 1.4, m1, fontsize=7, color=GRAY, ha="left")
        ax.text(x + 1.2, y2 - 1.4, m2, fontsize=7, color=GRAY, ha="left")
        ax.text(x, (y1 + y2) / 2, name, fontsize=7, color=NAVY, ha="center",
                bbox=dict(fc="white", ec="none", pad=0.6))

    hlink(c_ng, c_ph, "0..*", "1", "ở tại", 14)
    hlink(c_ph, c_cam, "1", "1..*", "được lắp", 14)
    hlink(c_nn, c_qt, "1..*", "1", "nhận theo", 41)
    hlink(c_tb, c_sk, "0..*", "1", "phát sinh từ", 95)
    hlink(c_sk, c_ph2, "1", "0..*", "được xử lý", 95)
    vlink(c_ph, c_qt, "1", "1", "áp dụng", 50)
    vlink(c_cam, c_pg, "1", "0..*", "ghi nhận", 83.5)
    vlink(c_pg, c_vq, "", "", "", 83.5, ls="")
    vlink(c_nn, c_lt, "1", "0..*", "sắp thứ tự", 14)
    vlink(c_lt, c_tb, "1", "0..*", "gửi tới", 14)
    vlink(c_kq, c_sk, "1..*", "0..1", "kích hoạt", 50)

    # Camera – VungQuanSat: định tuyến vòng bên phải
    path(ax, [(C3 + W3, 12), (99, 12), (99, R3 + 10), (C3 + W3, R3 + 10)],
         color=NAVY, lw=1.3, head=False)
    ax.text(99, (12 + R3 + 10) / 2, "khai báo\n1 → 0..*", fontsize=7, color=NAVY,
            ha="center", rotation=90, bbox=dict(fc="white", ec="none", pad=0.6))
    # PhienGiamSat – KetQuaNhanDang
    ax.plot([C3, C2 + W2], [R2 + 12, R3 + 8], color=NAVY, lw=1.3, zorder=1)
    ax.text(68, 51, "sinh ra   1 → 0..*", fontsize=7, color=NAVY, ha="center",
            bbox=dict(fc="white", ec="none", pad=0.6))
    ax.text(C1 + 1, R3 - 1.6, "lớp kết hợp", fontsize=7, color=ORANGE, ha="left",
            fontweight="bold")
    save(fig, "h07_so_do_lop.png")


# ============================================================== H8 thành phần
def fig_component():
    fig, ax = new_ax(11.5, 6.4)
    ax.add_patch(Rectangle((2, 10), 58, 82, fc="#FBFDFE", ec=NAVY, lw=2, zorder=0))
    ax.text(31, 6, "MÁY XỬ LÝ ĐẶT TẠI CHỖ  —  video thô không rời khỏi thiết bị này",
            ha="center", fontsize=9.5, fontweight="bold", color=NAVY)

    chain = [
        ("Bộ thu hình (đọc luồng RTSP)", FILL, NAVY),
        ("Bộ trích khung xương\nYOLOv8n-Pose", FILL, NAVY),
        ("Bộ bám người + nội suy khớp bị che", FILL, NAVY),
        ("Bộ đệm & chuẩn hoá cửa sổ 32 khung", FILL, NAVY),
        ("Bộ phân loại ST-GCN\n(2,04 triệu tham số)", FILL3, GREEN),
        ("Bộ quyết định cảnh báo\n(ngưỡng · số lần liên tiếp · vùng)", FILL2, ORANGE),
        ("Bộ leo thang & hẹn giờ", REDF, RED),
    ]
    ys = [14, 25, 36, 46, 56, 68, 80]
    hs = [7.5, 9, 7.5, 7.5, 9, 9, 7.5]
    bs = []
    for (text, fc, ec), yy, hh in zip(chain, ys, hs):
        bs.append(box(ax, 5, yy, 34, hh, text, fc=fc, ec=ec, fs=8.1))
    for i in range(len(bs) - 1):
        arrow(ax, side(bs[i], "b"), side(bs[i + 1], "t"), lw=1.5)

    b8 = box(ax, 43, 25, 15, 16, "Bộ giám sát\nsức khoẻ\nthiết bị", fs=8.1)
    box(ax, 43, 56, 15, 22, "Kho dữ liệu\ncục bộ\n\ncấu hình\nsự kiện\nnhật ký",
        fc=GRAYF, ec=GRAY, fs=8.1)
    path(ax, [(39, 19), (50.5, 19), (50.5, 25)], ls="--", color=GRAY, lw=1.4)
    path(ax, [(50.5, 41), (50.5, 56)], ls="--", color=GRAY, lw=1.4)
    path(ax, [(39, 72.5), (41, 72.5), (41, 62), (43, 62)], lw=1.4)

    box(ax, 70, 14, 28, 8, "Camera IP trong phòng", fc=GRAYF, ec=GRAY, fs=8.1)
    box(ax, 70, 34, 28, 9, "Loa / đèn báo tại chỗ", fc=FILL2, ec=ORANGE, fs=8.1)
    box(ax, 70, 52, 28, 12, "Giao diện web\n(người thân · nhân viên trực\n· kỹ thuật viên)", fs=8.1)
    box(ax, 70, 76, 28, 11, "Dịch vụ thông báo ngoài\n(SMS / push / email)",
        fc=GRAYF, ec=GRAY, fs=8.1)

    path(ax, [(70, 18), (64, 18), (64, 17.7), (39, 17.7)], lw=1.5,
         text="RTSP", text_at=(56, 15.2))
    path(ax, [(39, 83.7), (66.5, 83.7), (66.5, 81.5), (70, 81.5)], color=RED, lw=1.5,
         text="chỉ dữ liệu sự kiện", text_at=(54, 86.5), tcolor=RED)
    path(ax, [(39, 82), (63, 82), (63, 38.5), (70, 38.5)], color=ORANGE, lw=1.5,
         text="âm báo\ntại chỗ", text_at=(63, 30), tcolor=ORANGE)
    path(ax, [(58, 67), (60.5, 67), (60.5, 58), (70, 58)], lw=1.5,
         text="HTTPS nội bộ", text_at=(66, 55.5))
    save(fig, "h08_thanh_phan.png")


# ================================================================= H9 dữ liệu
def fig_data():
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.0))

    ax = axes[0]
    splits = ["Huấn luyện\n(S1–S8)", "Theo dõi\n(S9)", "Kiểm thử\n(S10, S11, S13)"]
    neg, pos = [6399, 874, 2428], [598, 75, 225]
    x = np.arange(3)
    ax.bar(x, neg, 0.55, label="Không té ngã", color="#5DADE2", ec=NAVY)
    ax.bar(x, pos, 0.55, bottom=neg, label="Té ngã", color=RED, ec="#7B241C")
    for i, (n, p) in enumerate(zip(neg, pos)):
        ax.text(i, n / 2, f"{n:,}".replace(",", "."), ha="center", va="center",
                fontsize=9.5, color="white", fontweight="bold")
        ax.text(i, n + p + 200, f"{p} cửa sổ té ngã\n({p/(n+p)*100:.1f}%)".replace(".", ","),
                ha="center", va="bottom", fontsize=8.5, color=RED, fontweight="bold")
    ax.set_xticks(x, splits, fontsize=9)
    ax.set_ylabel("Số cửa sổ 32 khung hình", fontsize=9)
    ax.set_title("Phân bố mẫu theo tập dữ liệu và theo lớp", fontsize=10.5,
                 fontweight="bold", color=NAVY)
    ax.legend(fontsize=8.5, loc="upper right")
    ax.set_ylim(0, 8800)
    ax.spines[["top", "right"]].set_visible(False)

    ax = axes[1]
    acts = ["Ngã trước\nchống tay", "Ngã trước\nchống gối", "Ngã\nra sau",
            "Ngã\nsang bên", "Ngã khi\nngồi ghế"]
    rec = [88.9, 100.0, 75.6, 100.0, 100.0]
    bars = ax.bar(acts, rec, 0.6, color=[RED if r < 90 else GREEN for r in rec],
                  ec="#17365D", alpha=0.88)
    for b, r in zip(bars, rec):
        ax.text(b.get_x() + b.get_width() / 2, r + 1.5, f"{r:.1f}%".replace(".", ","),
                ha="center", fontsize=9, fontweight="bold", color="#17365D")
    ax.axhline(90, color=GRAY, ls="--", lw=1.2)
    ax.text(-0.42, 84, "mức mong muốn 90%", ha="left", fontsize=8, color=GRAY)
    ax.set_ylim(0, 112)
    ax.set_ylabel("Tỷ lệ phát hiện (recall) mức cửa sổ", fontsize=9)
    ax.set_title("Độ nhạy theo từng kiểu ngã trên tập kiểm thử", fontsize=10.5,
                 fontweight="bold", color=NAVY)
    ax.tick_params(axis="x", labelsize=8)
    ax.spines[["top", "right"]].set_visible(False)

    fig.tight_layout(pad=1.0)
    save(fig, "h09_du_lieu.png")


# =============================================================== H10 pipeline
def fig_pipeline():
    fig, ax = new_ax(12, 3.0, ylim=(0, 88))
    steps = [
        ("Video\n≈18 hình/giây", FILL, NAVY),
        ("YOLO-Pose\n17 khớp\n(x, y, tin cậy)", FILL, NAVY),
        ("Bám người\n+ nội suy\nkhớp bị che", FILL2, ORANGE),
        ("Cắt cửa sổ\n32 khung\n(~1,8 giây)", FILL2, ORANGE),
        ("Chuẩn hoá\ntâm hông ·\nđộ dài thân", FILL2, ORANGE),
        ("Bỏ kênh tin cậy\ncòn 2 kênh\n(x, y)", FILL3, GREEN),
        ("ST-GCN\n→ P(té ngã)", FILL3, GREEN),
    ]
    w, gap, x, prev = 12.2, 2.1, 1, None
    for text, fc, ec in steps:
        b = box(ax, x, 22, w, 34, text, fc=fc, ec=ec, fs=8.0)
        if prev:
            arrow(ax, side(prev, "r"), side(b, "l"), lw=1.8)
        prev = b
        x += w + gap
    ax.text(19.5, 16, "trích đặc trưng", ha="center", fontsize=8.8, color=NAVY, fontweight="bold")
    ax.text(52, 16, "làm sạch & chuẩn hoá", ha="center", fontsize=8.8, color=ORANGE, fontweight="bold")
    ax.text(84, 16, "học máy", ha="center", fontsize=8.8, color=GREEN, fontweight="bold")
    ax.text(50, 66, "Chuỗi tiền xử lý này phải giống hệt nhau giữa lúc huấn luyện và lúc chạy thực tế",
            ha="center", fontsize=9, style="italic", color=GRAY)
    save(fig, "h10_pipeline_du_lieu.png")


# ============================================================== H11 triển khai
def fig_deploy():
    fig, ax = new_ax(11, 4.6)
    box(ax, 2, 26, 24, 30, "«thiết bị»\nCamera IP\n\nRTSP / H.264\n1–2 chiếc mỗi phòng",
        fc=GRAYF, ec=GRAY, fs=8.5)
    box(ax, 34, 8, 32, 66,
        "«thiết bị» MÁY XỬ LÝ TẠI CHỖ\n(mini-PC có GPU / Jetson)\n\n"
        "«môi trường» Python 3.14\n– YOLOv8n-Pose\n– ST-GCN (2,04 triệu tham số)\n"
        "– Dịch vụ cảnh báo & leo thang\n\n«CSDL» Kho dữ liệu cục bộ",
        fc="#D4E6F1", fs=8.5)
    box(ax, 34, 84, 32, 12, "«thiết bị» Loa – đèn báo tại chỗ", fc=FILL2, ec=ORANGE, fs=8.5)
    box(ax, 74, 8, 24, 16, "«dịch vụ ngoài»\nCổng SMS / push", fc=GRAYF, ec=GRAY, fs=8.5)
    box(ax, 74, 32, 24, 18, "«thiết bị»\nĐiện thoại người thân\n\nứng dụng / trình duyệt", fs=8.5)
    box(ax, 74, 58, 24, 18, "«thiết bị»\nMáy trạm nhân viên trực\n\ntrình duyệt web", fs=8.5)

    path(ax, [(26, 41), (34, 41)], head=False, lw=1.6,
         text="RTSP\n(mạng nội bộ)", text_at=(30, 34))
    path(ax, [(50, 74), (50, 84)], head=False, lw=1.6, color=ORANGE)
    path(ax, [(66, 16), (74, 16)], head=False, lw=1.6,
         text="HTTPS ra Internet\n(chỉ dữ liệu sự kiện,\nkhông có video)", text_at=(70, 26), fs=7.2)
    path(ax, [(86, 24), (86, 32)], head=False, lw=1.6, color=GRAY,
         text="SMS / push", text_at=(86, 28), fs=7.2, tcolor=GRAY)
    path(ax, [(66, 67), (74, 67)], head=False, lw=1.6,
         text="HTTPS\nmạng nội bộ", text_at=(70, 60), fs=7.2)
    save(fig, "h11_trien_khai.png")


if __name__ == "__main__":
    print("Sinh hình cho báo cáo Phân tích hệ thống:")
    for fn in (fig_context, fig_usecase, fig_act_detect, fig_act_escalate,
               fig_state, fig_sequence, fig_class, fig_component, fig_data,
               fig_pipeline, fig_deploy):
        fn()
    print(f"Xong. Thư mục: {OUT}")
