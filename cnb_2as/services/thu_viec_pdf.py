# Copyright (c) 2025, antruong and contributors
# For license information, please see license.txt

"""PDF generator for thu-viec (probation) evaluation reports.

Generates formatted A4 PDF reports for probation period evaluations.
Separate from pdf_generator.py (which handles contract renewal reports).
"""

import io
import json
import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
	HRFlowable,
	Paragraph,
	SimpleDocTemplate,
	Spacer,
	Table,
	TableStyle,
)

# Shared utilities from pdf_generator
from cnb_2as.services.pdf_generator import (
	_CLR_BLACK, _CLR_DARK, _CLR_MEDIUM, _CLR_LIGHT_TEXT,
	_CLR_BORDER, _CLR_BORDER_LIGHT, _CLR_BG_HEADER, _CLR_BG_ALT,
	_CLR_BG_SCORE, _CLR_WHITE,
	_FONT_NAME, _FONT_BOLD,
	_get_styles, _safe, _section_divider, _register_vietnamese_font,
)


def generate_thu_viec_pdf(eval_data):
	"""Generate a professional PDF for Thu Viec evaluation.

	Layout: Header CT Group → Thông tin NV → Status badge → Tổng quan
	        → 7 tiêu chí 2AS → Đề xuất xử lý → Việc cần làm → Footer
	"""
	buffer = io.BytesIO()
	_register_vietnamese_font()
	styles = _get_styles()

	eval_type = eval_data.get("eval_type", "thu_viec")
	_loai_up = "HỌC VIỆC" if eval_type == "hoc_viec" else "THỬ VIỆC"
	_loai_cap = "Học việc" if eval_type == "hoc_viec" else "Thử việc"
	_loai = "học việc" if eval_type == "hoc_viec" else "thử việc"

	doc = SimpleDocTemplate(
		buffer, pagesize=A4,
		leftMargin=2*cm, rightMargin=2*cm,
		topMargin=2*cm, bottomMargin=2*cm,
		title=f"Bao Cao Danh Gia {_loai_cap}",
		author="CT Group – DAIT AI System",
	)

	elements = []
	pw = A4[0] - 4*cm
	now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

	r = eval_data.get("re_review") or eval_data
	nv = (
		r.get("thong_tin_nhan_vien")
		or eval_data.get("thong_tin_nhan_vien")
		or eval_data.get("nhan_vien")
		or {}
	)

	CLR_INDIGO   = colors.HexColor("#4f46e5")
	CLR_GREEN    = colors.HexColor("#15803d")
	CLR_GREEN_BG = colors.HexColor("#f0fdf4")
	CLR_AMBER    = colors.HexColor("#92400e")
	CLR_AMBER_BG = colors.HexColor("#fffbeb")
	CLR_RED      = colors.HexColor("#991b1b")
	CLR_RED_BG   = colors.HexColor("#fff1f2")
	CLR_GRAY     = colors.HexColor("#6b7280")
	CLR_BG_HDR   = colors.HexColor("#f1f5f9")

	# ── 1. HEADER ────────────────────────────────────────────────────────────
	brand_style = ParagraphStyle("_brand", fontName=_FONT_BOLD, fontSize=13, textColor=CLR_INDIGO, alignment=TA_LEFT)
	date_style  = ParagraphStyle("_date",  fontName=_FONT_NAME, fontSize=8,  textColor=CLR_GRAY,   alignment=TA_RIGHT)
	hdr_table = Table(
		[[Paragraph(f"CT GROUP  ·  BÁO CÁO ĐÁNH GIÁ {_loai_up}", brand_style), Paragraph(f"Ngày xuất: {now_str}", date_style)]],
		colWidths=[pw*0.65, pw*0.35]
	)
	hdr_table.setStyle(TableStyle([
		("VALIGN", (0,0), (-1,-1), "MIDDLE"),
		("LINEBELOW", (0,0), (-1,0), 1.5, CLR_INDIGO),
		("TOPPADDING", (0,0), (-1,-1), 4),
		("BOTTOMPADDING", (0,0), (-1,-1), 6),
	]))
	elements.append(hdr_table)
	elements.append(Spacer(1, 5*mm))

	# ── 2. THÔNG TIN NHÂN VIÊN ───────────────────────────────────────────────
	s_lbl  = ParagraphStyle("_lbl",  fontName=_FONT_BOLD, fontSize=7.5, textColor=CLR_GRAY)
	s_val  = ParagraphStyle("_val",  fontName=_FONT_NAME, fontSize=9,   textColor=_CLR_BLACK)
	s_valb = ParagraphStyle("_valb", fontName=_FONT_BOLD, fontSize=9,   textColor=_CLR_BLACK)
	col_lbl = 3*cm
	col_val = pw/2 - col_lbl
	nv_rows = [
		[Paragraph("Họ và tên", s_lbl), Paragraph(_safe(nv.get("ten_nhan_vien","—")), s_valb),
		 Paragraph("Mã nhân viên", s_lbl), Paragraph(_safe(nv.get("ma_nhan_vien","—")), s_val)],
		[Paragraph("Chức danh", s_lbl), Paragraph(_safe(nv.get("chuc_danh","—")), s_val),
		 Paragraph("Đơn vị", s_lbl), Paragraph(_safe(nv.get("don_vi","—")), s_val)],
		[Paragraph("Ngày nhận việc", s_lbl), Paragraph(_safe(nv.get("ngay_nhan_viec","—")), s_val),
		 Paragraph("Ngày hết hạn TV", s_lbl), Paragraph(_safe(nv.get("ngay_het_han","—")), s_val)],
		[Paragraph("HOD phụ trách", s_lbl), Paragraph(_safe(nv.get("ten_hod","—")), s_valb),
		 Paragraph("", s_lbl), Paragraph("", s_val)],
	]
	nv_table = Table(nv_rows, colWidths=[col_lbl, col_val, col_lbl, col_val])
	nv_table.setStyle(TableStyle([
		("BACKGROUND", (0,0), (-1,-1), CLR_BG_HDR),
		("LINEBELOW",  (0,0), (-1,-1), 0.3, _CLR_BORDER_LIGHT),
		("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
		("TOPPADDING", (0,0), (-1,-1), 5),
		("BOTTOMPADDING", (0,0), (-1,-1), 5),
		("LEFTPADDING", (0,0), (0,-1), 8),
		("LEFTPADDING", (2,0), (2,-1), 10),
	]))
	elements.append(nv_table)
	elements.append(Spacer(1, 6*mm))

	# ── 3. STATUS BADGE ──────────────────────────────────────────────────────
	status = str(r.get("status", eval_data.get("status", "CHƯA XÁC ĐỊNH")))
	is_pass = "ĐẠT" in status.upper() and "CHƯA" not in status.upper()
	st_bg  = CLR_GREEN_BG if is_pass else CLR_AMBER_BG
	st_clr = CLR_GREEN    if is_pass else CLR_AMBER
	st_table = Table(
		[[Paragraph("KẾT QUẢ ĐÁNH GIÁ", ParagraphStyle("_stl", fontName=_FONT_NAME, fontSize=8, textColor=CLR_GRAY, alignment=TA_CENTER))],
		 [Paragraph(("✓ " if is_pass else "⚠ ") + _safe(status), ParagraphStyle("_st", fontName=_FONT_BOLD, fontSize=14, textColor=st_clr, alignment=TA_CENTER))]],
		colWidths=[pw]
	)
	st_table.setStyle(TableStyle([
		("BACKGROUND",     (0,0), (-1,-1), st_bg),
		("BOX",           (0,0), (-1,-1), 1.5, st_clr),
		("TOPPADDING",    (0,0), (-1,-1), 7),
		("BOTTOMPADDING", (0,0), (-1,-1), 7),
		("ALIGN",         (0,0), (-1,-1), "CENTER"),
	]))
	elements.append(st_table)
	elements.append(Spacer(1, 5*mm))

	# ── 4. TỔNG QUAN ─────────────────────────────────────────────────────────
	tong_quan = r.get("tong_quan") or eval_data.get("tong_quan", "")
	if tong_quan:
		elements.append(Paragraph("▌ NHẬN XÉT TỔNG QUAN", ParagraphStyle(
			"_sec", fontName=_FONT_BOLD, fontSize=9.5, textColor=CLR_INDIGO, spaceBefore=4*mm, spaceAfter=2*mm, leading=13)))
		elements.append(Paragraph(_safe(tong_quan, 1200), ParagraphStyle(
			"_tq", fontName=_FONT_NAME, fontSize=9, textColor=_CLR_DARK, leading=14, leftIndent=4)))
		elements.append(Spacer(1, 4*mm))

	# ── 5. PHÂN TÍCH 7 TIÊU CHÍ 2AS ─────────────────────────────────────────
	phan_tich = r.get("phan_tich_2as") or eval_data.get("phan_tich_2as", [])
	if phan_tich:
		n_dat = sum(1 for tc in phan_tich if "ĐẠT" in str(tc.get("ket_qua","")).upper() and "CHƯA" not in str(tc.get("ket_qua","")).upper())
		elements.append(Paragraph(f"▌ PHÂN TÍCH THEO TIÊU CHÍ 2AS  —  {n_dat}/{len(phan_tich)} đạt", ParagraphStyle(
			"_sec2", fontName=_FONT_BOLD, fontSize=9.5, textColor=CLR_INDIGO, spaceBefore=2*mm, spaceAfter=2*mm, leading=13)))
		s_th = ParagraphStyle("_th2as", fontName=_FONT_BOLD, fontSize=8, textColor=_CLR_DARK, alignment=TA_CENTER)
		s_tc = ParagraphStyle("_tc2as", fontName=_FONT_BOLD, fontSize=8.5, textColor=_CLR_DARK)
		s_nx = ParagraphStyle("_nx2as", fontName=_FONT_NAME, fontSize=8.5, textColor=_CLR_DARK, leading=12)
		tc_data = [[Paragraph("#", s_th), Paragraph("Tiêu chí", s_th), Paragraph("Nhận xét", s_th), Paragraph("Kết quả", s_th)]]
		row_bg_cmds = []
		for idx, tc in enumerate(phan_tich):
			kq = str(tc.get("ket_qua","")).strip()
			is_tc_pass = "ĐẠT" in kq.upper() and "CHƯA" not in kq.upper()
			is_tc_warn = "BỔ SUNG" in kq.upper() or "CẦN" in kq.upper()
			bg  = CLR_GREEN_BG if is_tc_pass else (CLR_AMBER_BG if is_tc_warn else CLR_RED_BG)
			clr = CLR_GREEN    if is_tc_pass else (CLR_AMBER    if is_tc_warn else CLR_RED)
			tc_data.append([
				Paragraph(str(tc.get("ma", idx+1)), ParagraphStyle(f"_ma{idx}", fontName=_FONT_BOLD, fontSize=8, textColor=CLR_INDIGO, alignment=TA_CENTER)),
				Paragraph(_safe(tc.get("tieu_chi",""), 60), s_tc),
				Paragraph(_safe(tc.get("nhan_xet",""), 400), s_nx),
				Paragraph(_safe(kq or "—"), ParagraphStyle(f"_kq{idx}", fontName=_FONT_BOLD, fontSize=8, textColor=clr, alignment=TA_CENTER)),
			])
			row_bg_cmds.append(("BACKGROUND", (0, idx+1), (-1, idx+1), bg))
		tc_table = Table(tc_data, colWidths=[pw*0.06, pw*0.20, pw*0.56, pw*0.18])
		tc_table.setStyle(TableStyle([
			("FONTNAME", (0,0), (-1,-1), _FONT_NAME), ("VALIGN", (0,0), (-1,-1), "TOP"),
			("BACKGROUND", (0,0), (-1,0), _CLR_BG_HEADER), ("BOX", (0,0), (-1,-1), 0.5, _CLR_BORDER),
			("LINEBELOW", (0,0), (-1,-1), 0.3, _CLR_BORDER_LIGHT), ("LINEBEFORE", (1,0), (-1,-1), 0.3, _CLR_BORDER_LIGHT),
			("TOPPADDING", (0,0), (-1,-1), 6), ("BOTTOMPADDING", (0,0), (-1,-1), 6),
		] + row_bg_cmds))
		elements.append(tc_table)
		elements.append(Spacer(1, 5*mm))

	# ── 6. ĐỀ XUẤT XỬ LÝ ────────────────────────────────────────────────────
	dx = r.get("de_xuat_xu_ly") or eval_data.get("de_xuat_xu_ly", {})
	if dx and isinstance(dx, dict):
		elements.append(Paragraph("▌ ĐỀ XUẤT XỬ LÝ", ParagraphStyle(
			"_secdx", fontName=_FONT_BOLD, fontSize=9.5, textColor=CLR_INDIGO, spaceBefore=2*mm, spaceAfter=2*mm, leading=13)))
		kq_tv = str(dx.get("ket_qua_tv",""))
		is_dx_pass = "ĐẠT" in kq_tv.upper() or "KÝ HỢP ĐỒNG" in kq_tv.upper()
		is_dx_warn = "GIA HẠN" in kq_tv.upper()
		dx_bg  = CLR_GREEN_BG if is_dx_pass else (CLR_AMBER_BG if is_dx_warn else CLR_RED_BG)
		dx_clr = CLR_GREEN    if is_dx_pass else (CLR_AMBER    if is_dx_warn else CLR_RED)
		dx_rows = [
			[Paragraph(f"Kết quả {_loai}", ParagraphStyle("_dxlbl", fontName=_FONT_BOLD, fontSize=8, textColor=CLR_GRAY)),
			 Paragraph(_safe(kq_tv or "—"), ParagraphStyle("_dxkq", fontName=_FONT_BOLD, fontSize=10, textColor=dx_clr))],
			[Paragraph("Mức độ đề xuất",   ParagraphStyle("_dxlbl2", fontName=_FONT_BOLD, fontSize=8, textColor=CLR_GRAY)),
			 Paragraph(_safe(dx.get("muc_do","—")), ParagraphStyle("_dxmd", fontName=_FONT_NAME, fontSize=9, textColor=_CLR_DARK))],
			[Paragraph("Lý do",            ParagraphStyle("_dxlbl3", fontName=_FONT_BOLD, fontSize=8, textColor=CLR_GRAY)),
			 Paragraph(_safe(dx.get("ly_do","—"), 800), ParagraphStyle("_dxly", fontName=_FONT_NAME, fontSize=8.5, textColor=_CLR_DARK, leading=13))],
		]
		dx_table = Table(dx_rows, colWidths=[3.2*cm, pw-3.2*cm])
		dx_table.setStyle(TableStyle([
			("BACKGROUND", (0,0), (-1,-1), dx_bg), ("BOX", (0,0), (-1,-1), 0.8, dx_clr),
			("LINEBELOW", (0,0), (-1,-1), 0.3, _CLR_BORDER_LIGHT), ("VALIGN", (0,0), (-1,-1), "TOP"),
			("TOPPADDING", (0,0), (-1,-1), 6), ("BOTTOMPADDING", (0,0), (-1,-1), 6), ("LEFTPADDING", (0,0), (0,-1), 8),
		]))
		elements.append(dx_table)
		elements.append(Spacer(1, 5*mm))

	# ── 7. ĐÁNH GIÁ ĐỀ XUẤT QUẢN LÝ ──────────────────────────────────────────
	ql = r.get("danh_gia_quan_ly") or eval_data.get("danh_gia_quan_ly", {})
	if ql and isinstance(ql, dict):
		elements.append(Paragraph("▌ ĐÁNH GIÁ ĐỀ XUẤT QUẢN LÝ", ParagraphStyle(
			"_secql", fontName=_FONT_BOLD, fontSize=9.5, textColor=CLR_INDIGO, spaceBefore=2*mm, spaceAfter=2*mm, leading=13)))
		is_ql_pass = ql.get("hop_ly") is True
		is_ql_warn = ql.get("hop_ly") is None
		ql_bg  = CLR_GREEN_BG if is_ql_pass else (CLR_AMBER_BG if is_ql_warn else CLR_RED_BG)
		ql_clr = CLR_GREEN    if is_ql_pass else (CLR_AMBER    if is_ql_warn else CLR_RED)
		ql_rows = [
			[Paragraph("Đề xuất quản lý", ParagraphStyle("_qllbl", fontName=_FONT_BOLD, fontSize=8, textColor=CLR_GRAY)),
			 Paragraph(_safe(ql.get("de_xuat_quan_ly","—"), 800), ParagraphStyle("_qlval", fontName=_FONT_NAME, fontSize=9, textColor=_CLR_DARK))],
			[Paragraph("Mức độ đồng ý",   ParagraphStyle("_qllbl2", fontName=_FONT_BOLD, fontSize=8, textColor=CLR_GRAY)),
			 Paragraph(_safe(ql.get("muc_do_dong_y","—")), ParagraphStyle("_qlmd", fontName=_FONT_BOLD, fontSize=9, textColor=ql_clr))],
			[Paragraph("Lý do chính",            ParagraphStyle("_qllbl3", fontName=_FONT_BOLD, fontSize=8, textColor=CLR_GRAY)),
			 Paragraph(_safe(ql.get("ly_do_chinh","—"), 800), ParagraphStyle("_qlly", fontName=_FONT_NAME, fontSize=8.5, textColor=_CLR_DARK, leading=13))],
			[Paragraph("Phân tích AI",            ParagraphStyle("_qllbl4", fontName=_FONT_BOLD, fontSize=8, textColor=CLR_GRAY)),
			 Paragraph(_safe(ql.get("phan_tich_chi_tiet","—"), 800), ParagraphStyle("_qlpt", fontName=_FONT_NAME, fontSize=8.5, textColor=_CLR_DARK, leading=13))],
			[Paragraph("Nhận xét chung",            ParagraphStyle("_qllbl5", fontName=_FONT_BOLD, fontSize=8, textColor=CLR_GRAY)),
			 Paragraph(_safe(ql.get("nhan_xet","—"), 800), ParagraphStyle("_qlnx", fontName=_FONT_NAME, fontSize=8.5, textColor=_CLR_DARK, leading=13))],
			[Paragraph("Khuyến nghị",            ParagraphStyle("_qllbl6", fontName=_FONT_BOLD, fontSize=8, textColor=CLR_GRAY)),
			 Paragraph(_safe(ql.get("khuyen_nghi_xu_ly","—"), 800), ParagraphStyle("_qlkn", fontName=_FONT_BOLD, fontSize=8.5, textColor=_CLR_DARK, leading=13))],
		]
		ql_table = Table(ql_rows, colWidths=[3.2*cm, pw-3.2*cm])
		ql_table.setStyle(TableStyle([
			("BACKGROUND", (0,0), (-1,-1), ql_bg), ("BOX", (0,0), (-1,-1), 0.8, ql_clr),
			("LINEBELOW", (0,0), (-1,-1), 0.3, _CLR_BORDER_LIGHT), ("VALIGN", (0,0), (-1,-1), "TOP"),
			("TOPPADDING", (0,0), (-1,-1), 6), ("BOTTOMPADDING", (0,0), (-1,-1), 6), ("LEFTPADDING", (0,0), (0,-1), 8),
		]))
		elements.append(ql_table)
		elements.append(Spacer(1, 5*mm))

	# ── 8. VIỆC CẦN LÀM ──────────────────────────────────────────────────────
	viec = r.get("viec_can_lam") or eval_data.get("viec_can_lam", [])
	if viec:
		elements.append(Paragraph("▌ VIỆC CẦN LÀM TIẾP THEO", ParagraphStyle(
			"_secviec", fontName=_FONT_BOLD, fontSize=9.5, textColor=CLR_INDIGO, spaceBefore=2*mm, spaceAfter=2*mm, leading=13)))
		s_th_v   = ParagraphStyle("_thv",  fontName=_FONT_BOLD, fontSize=8, textColor=_CLR_DARK, alignment=TA_CENTER)
		s_ctr_v  = ParagraphStyle("_ctrv", fontName=_FONT_NAME, fontSize=9, textColor=_CLR_DARK, alignment=TA_CENTER)
		s_body_v = ParagraphStyle("_bv",   fontName=_FONT_NAME, fontSize=8.5, textColor=_CLR_DARK, leading=12)
		v_data = [[Paragraph("#", s_th_v), Paragraph("Nội dung", s_th_v), Paragraph("Ưu tiên", s_th_v), Paragraph("Trạng thái", s_th_v)]]
		for vi, s in enumerate(viec):
			title  = _safe(s.get("title") or s.get("hanh_dong") or "", 120)
			mo_ta  = _safe(s.get("mo_ta") or "", 100)
			urgent = s.get("urgent") or str(s.get("uu_tien","")).lower() in ("cao","high")
			done   = s.get("done", False)
			cell   = f"<b>{title}</b>"
			if mo_ta:
				cell += f"<br/><font size='7.5' color='#6b7280'>{mo_ta}</font>"
			v_data.append([
				Paragraph(str(vi+1), s_ctr_v),
				Paragraph(cell, s_body_v),
				Paragraph("⚡ Gấp" if urgent else "—", s_ctr_v),
				Paragraph("✓ Xong" if done else "□", s_ctr_v),
			])
		v_table = Table(v_data, colWidths=[pw*0.06, pw*0.65, pw*0.14, pw*0.15])
		v_table.setStyle(TableStyle([
			("FONTNAME", (0,0), (-1,-1), _FONT_NAME), ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
			("BACKGROUND", (0,0), (-1,0), _CLR_BG_HEADER), ("BOX", (0,0), (-1,-1), 0.5, _CLR_BORDER),
			("LINEBELOW", (0,0), (-1,-1), 0.3, _CLR_BORDER_LIGHT), ("LINEBEFORE", (1,0), (-1,-1), 0.3, _CLR_BORDER_LIGHT),
			("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
		]))
		elements.append(v_table)
		elements.append(Spacer(1, 5*mm))

	# ── 9. FOOTER ─────────────────────────────────────────────────────────────
	elements.append(Spacer(1, 10*mm))
	elements.append(HRFlowable(width="100%", thickness=0.5, color=_CLR_BORDER_LIGHT, spaceBefore=2*mm, spaceAfter=3*mm))
	elements.append(Paragraph(
		_safe("Báo cáo được tạo tự động bởi Hệ thống Đánh giá AI – CT Group · DAIT.  Kết quả mang tính tham khảo và cần được xem xét bởi cấp quản lý."),
		ParagraphStyle("_footer2", fontName=_FONT_NAME, fontSize=7.5, textColor=CLR_GRAY, alignment=TA_CENTER)))

	def _page_num(canvas, doc):
		pn = canvas.getPageNumber()
		canvas.saveState()
		canvas.setFont(_FONT_NAME, 7.5)
		canvas.setFillColor(CLR_GRAY)
		canvas.drawRightString(A4[0]-2*cm, 1.2*cm, f"Trang {pn}")
		canvas.drawString(2*cm, 1.2*cm, f"CT Group – Báo cáo đánh giá {_loai}")
		canvas.restoreState()

	doc.build(elements, onFirstPage=_page_num, onLaterPages=_page_num)
	buffer.seek(0)
	return buffer
