# Copyright (c) 2025, antruong and contributors
# For license information, please see license.txt

"""PDF Generator for HR Contract Evaluation Results.

Generates a formatted A4 PDF report optimized for B&W printing:
light backgrounds, thin borders, clean professional layout.
"""

import datetime
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

# --- Color palette optimized for B&W printing ---
_CLR_BLACK = colors.HexColor("#1a1a1a")
_CLR_DARK = colors.HexColor("#333333")
_CLR_MEDIUM = colors.HexColor("#666666")
_CLR_LIGHT_TEXT = colors.HexColor("#888888")
_CLR_BORDER = colors.HexColor("#cccccc")
_CLR_BORDER_LIGHT = colors.HexColor("#e0e0e0")
_CLR_BG_HEADER = colors.HexColor("#f0f0f0")  # Very light gray for table headers
_CLR_BG_ALT = colors.HexColor("#f8f8f8")  # Subtle alternating row
_CLR_BG_SCORE = colors.HexColor("#f5f5f5")
_CLR_WHITE = colors.white

_FONT_NAME = "Helvetica"
_FONT_BOLD = "Helvetica-Bold"
_FONT_REGISTERED = False


def _register_vietnamese_font():
	"""Register DejaVuSans if available for proper Vietnamese rendering."""
	global _FONT_REGISTERED, _FONT_NAME, _FONT_BOLD

	if _FONT_REGISTERED:
		return

	_FONT_REGISTERED = True

	try:
		from reportlab.pdfbase import pdfmetrics
		from reportlab.pdfbase.ttfonts import TTFont

		font_paths = [
			"/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
			"/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf",
			"/usr/share/fonts/TTF/DejaVuSans.ttf",
		]
		bold_paths = [
			"/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
			"/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf",
			"/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
		]

		font_path = None
		for fp in font_paths:
			if os.path.exists(fp):
				font_path = fp
				break

		bold_path = None
		for bp in bold_paths:
			if os.path.exists(bp):
				bold_path = bp
				break

		if font_path:
			pdfmetrics.registerFont(TTFont("DejaVuSans", font_path))
			_FONT_NAME = "DejaVuSans"

			if bold_path:
				pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", bold_path))
				_FONT_BOLD = "DejaVuSans-Bold"
			else:
				_FONT_BOLD = "DejaVuSans"

	except Exception:
		_FONT_NAME = "Helvetica"
		_FONT_BOLD = "Helvetica-Bold"


def _get_styles():
	"""Build paragraph styles optimized for B&W printing."""
	_register_vietnamese_font()
	styles = getSampleStyleSheet()

	# Main title — centered, large, bold, dark
	styles.add(ParagraphStyle(
		"PDFTitle",
		fontName=_FONT_BOLD,
		fontSize=16,
		textColor=_CLR_BLACK,
		spaceAfter=3 * mm,
		alignment=TA_CENTER,
		leading=20,
	))

	# Subtitle — centered, smaller, gray
	styles.add(ParagraphStyle(
		"PDFSubtitle",
		fontName=_FONT_NAME,
		fontSize=9,
		textColor=_CLR_MEDIUM,
		spaceAfter=6 * mm,
		alignment=TA_CENTER,
	))

	# Section title — left aligned, uppercase feel, with underline effect
	styles.add(ParagraphStyle(
		"PDFSection",
		fontName=_FONT_BOLD,
		fontSize=11,
		textColor=colors.HexColor("#4f46e5"),  # Brand indigo color
		spaceBefore=8 * mm,
		spaceAfter=4 * mm,
		leading=14,
	))

	# Body text
	styles.add(ParagraphStyle(
		"PDFBody",
		fontName=_FONT_NAME,
		fontSize=9,
		textColor=_CLR_DARK,
		leading=13,
		spaceAfter=2 * mm,
	))

	# Body bold
	styles.add(ParagraphStyle(
		"PDFBodyBold",
		fontName=_FONT_BOLD,
		fontSize=9,
		textColor=_CLR_DARK,
		leading=13,
		spaceAfter=2 * mm,
	))

	# Small text (captions, notes)
	styles.add(ParagraphStyle(
		"PDFSmall",
		fontName=_FONT_NAME,
		fontSize=7.5,
		textColor=_CLR_LIGHT_TEXT,
		leading=10,
	))

	# Table cell text
	styles.add(ParagraphStyle(
		"PDFCell",
		fontName=_FONT_NAME,
		fontSize=8.5,
		textColor=_CLR_DARK,
		leading=11,
	))

	# Table cell bold
	styles.add(ParagraphStyle(
		"PDFCellBold",
		fontName=_FONT_BOLD,
		fontSize=8.5,
		textColor=_CLR_BLACK,
		leading=11,
	))

	# Table cell bold center
	styles.add(ParagraphStyle(
		"PDFCellBoldCenter",
		fontName=_FONT_BOLD,
		fontSize=9,
		textColor=_CLR_BLACK,
		alignment=TA_CENTER,
		leading=11,
	))

	# Table header
	styles.add(ParagraphStyle(
		"PDFTableHeader",
		fontName=_FONT_BOLD,
		fontSize=8,
		textColor=_CLR_DARK,
		leading=10,
		alignment=TA_CENTER,
	))

	# Score large
	styles.add(ParagraphStyle(
		"PDFScoreLarge",
		fontName=_FONT_BOLD,
		fontSize=18,
		textColor=_CLR_BLACK,
		alignment=TA_CENTER,
		leading=22,
	))

	# Score label
	styles.add(ParagraphStyle(
		"PDFScoreLabel",
		fontName=_FONT_NAME,
		fontSize=8,
		textColor=_CLR_MEDIUM,
		alignment=TA_CENTER,
	))

	# Warning text
	styles.add(ParagraphStyle(
		"PDFWarning",
		fontName=_FONT_NAME,
		fontSize=8,
		textColor=_CLR_DARK,
		leading=11,
		spaceAfter=1.5 * mm,
		leftIndent=12,
	))

	# Footer
	styles.add(ParagraphStyle(
		"PDFFooter",
		fontName=_FONT_NAME,
		fontSize=7,
		textColor=_CLR_LIGHT_TEXT,
		alignment=TA_CENTER,
		leading=9,
	))

	return styles


def _safe(text, max_len=300):
	"""Sanitize text for ReportLab Paragraph (escape XML entities)."""
	if not text:
		return ""
	t = str(text)[:max_len]
	t = t.replace("&", "&amp;")
	t = t.replace("<", "&lt;")
	t = t.replace(">", "&gt;")
	return t


def _section_divider():
	"""Create a thin horizontal line divider."""
	return HRFlowable(
		width="100%",
		thickness=0.5,
		color=_CLR_BORDER_LIGHT,
		spaceBefore=2 * mm,
		spaceAfter=2 * mm,
	)




def _render_pdf_header(eval_data, styles, current_time):
	"""Render pdf header section for the PDF.
	
	Returns:
		list: ReportLab story elements for this section.
	"""
	result = []
	# HEADER

	result.append(Spacer(1, 4 * mm))
	result.append(Paragraph(
		_safe("BÁO CÁO KẾT QUẢ ĐÁNH GIÁ TÁI KÝ HỢP ĐỒNG"),
		styles["PDFTitle"],
	))
	result.append(Paragraph(
		_safe("Hệ thống 2AS — Đánh giá AI Tự động và Khách quan"),
		styles["PDFSubtitle"],
	))
	result.append(Paragraph(
		_safe(f"Mã đánh giá: {eval_data.get('name', '—')} | Thời gian xuất: {current_time}"),
		styles["PDFSubtitle"],
	))
	result.append(_section_divider())

	return result


def _render_employee_info(eval_data, styles, page_width):
	"""Render employee info section for the PDF.
	
	Returns:
		list: ReportLab story elements for this section.
	"""
	result = []
	# 1. THÔNG TIN NHÂN VIÊN

	result.append(Paragraph("1. THÔNG TIN NHÂN VIÊN", styles["PDFSection"]))

	col_label_w = 3.2 * cm
	col_value_w = page_width / 2 - col_label_w

	ext_info = eval_data.get("extracted_info", {})
	
	info_left = [
		[
			Paragraph("Họ tên:", styles["PDFSmall"]),
			Paragraph(_safe(eval_data.get("employee_name", "—")), styles["PDFCellBold"]),
		],
		[
			Paragraph("Mã NV:", styles["PDFSmall"]),
			Paragraph(_safe(ext_info.get("employee_id", "—")), styles["PDFCell"]),
		],
		[
			Paragraph("Chức danh:", styles["PDFSmall"]),
			Paragraph(_safe(eval_data.get("job_title", "—")), styles["PDFCell"]),
		],
		[
			Paragraph("Ngày nhận việc:", styles["PDFSmall"]),
			Paragraph(_safe(ext_info.get("join_date", "—")), styles["PDFCell"]),
		],
	]
	info_right = [
		[
			Paragraph("Phòng ban:", styles["PDFSmall"]),
			Paragraph(_safe(eval_data.get("department", "—")), styles["PDFCell"]),
		],
		[
			Paragraph("Ngày đánh giá:", styles["PDFSmall"]),
			Paragraph(_safe(eval_data.get("evaluation_date", "—")), styles["PDFCell"]),
		],
		[
			Paragraph("Ngày BĐ HĐ:", styles["PDFSmall"]),
			Paragraph(_safe(ext_info.get("start_date", "—")), styles["PDFCell"]),
		],
		[
			Paragraph("Ngày HH HĐ:", styles["PDFSmall"]),
			Paragraph(_safe(ext_info.get("end_date", "—")), styles["PDFCell"]),
		],
	]

	info_data = []
	for i in range(len(info_left)):
		row = info_left[i] + info_right[i]
		info_data.append(row)

	info_table = Table(
		info_data,
		colWidths=[col_label_w, col_value_w, col_label_w, col_value_w],
	)
	info_table.setStyle(TableStyle([
		("FONTNAME", (0, 0), (-1, -1), _FONT_NAME),
		("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
		("TOPPADDING", (0, 0), (-1, -1), 4),
		("BOTTOMPADDING", (0, 0), (-1, -1), 4),
		("LINEBELOW", (0, 0), (-1, -1), 0.3, _CLR_BORDER_LIGHT),
	]))
	result.append(info_table)
	result.append(Spacer(1, 4 * mm))

	return result


def _render_data_check(eval_data, styles):
	"""Render data check section for the PDF.
	
	Returns:
		list: ReportLab story elements for this section.
	"""
	result = []
	# 2. KIỂM TRA HỒ SƠ & DỮ LIỆU

	doc_warnings = eval_data.get("document_warnings")
	if doc_warnings:
		if isinstance(doc_warnings, str):
			try:
				doc_warnings = json.loads(doc_warnings)
			except (json.JSONDecodeError, TypeError):
				doc_warnings = {}

	validation_warnings = eval_data.get("validation_warnings")
	consistency_check = eval_data.get("consistency_check")

	has_validation = False
	if validation_warnings:
		if isinstance(validation_warnings, str):
			try:
				validation_warnings = json.loads(validation_warnings)
			except (json.JSONDecodeError, TypeError):
				validation_warnings = []
		if validation_warnings:
			has_validation = True

	if consistency_check:
		if isinstance(consistency_check, str):
			try:
				consistency_check = json.loads(consistency_check)
			except (json.JSONDecodeError, TypeError):
				consistency_check = {}
		if consistency_check and consistency_check.get("warnings"):
			has_validation = True

	if doc_warnings or has_validation:
		result.append(_section_divider())
		result.append(Paragraph("2. KIỂM TRA HỒ SƠ & DỮ LIỆU", styles["PDFSection"]))

		# A. Tình trạng hồ sơ
		if doc_warnings:
			is_complete = doc_warnings.get("is_complete", True)
			warnings_list = doc_warnings.get("warnings", [])

			if is_complete:
				result.append(Paragraph(
					"✓ <b>Hồ sơ đầy đủ:</b> Đã điền đủ các thông tin bắt buộc.",
					styles["PDFBody"],
				))
			else:
				if warnings_list:
					result.append(Paragraph(
						f"<b>⚠ Hồ sơ cần bổ sung</b> — Có trường thông tin bị để trống:",
						styles["PDFBody"],
					))
					result.append(Spacer(1, 1 * mm))
					for w in warnings_list:
						msg = _safe(w.get("message", "") if isinstance(w, dict) else str(w), 200)
						result.append(Paragraph("  •  " + msg, styles["PDFWarning"]))
				
				result.append(Spacer(1, 3 * mm))

		# B. Kết quả kiểm tra dữ liệu
		if has_validation:
			if validation_warnings:
				result.append(Paragraph("<b>⚠ Cảnh báo dữ liệu đầu vào:</b>", styles["PDFBody"]))
				for w in validation_warnings:
					msg = _safe(w.get("message", "") if isinstance(w, dict) else str(w), 200)
					result.append(Paragraph("  !  " + msg, styles["PDFWarning"]))
				result.append(Spacer(1, 3 * mm))

	return result


def _render_assessment(eval_data, styles, page_width):
	"""Render assessment section for the PDF.
	
	Returns:
		list: ReportLab story elements for this section.
	"""
	result = []
	# 3. NHẬN ĐỊNH CỦA 2AS & ĐỀ XUẤT XỬ LÝ

	result.append(_section_divider())
	result.append(Paragraph("3. NHẬN ĐỊNH CỦA 2AS & ĐỀ XUẤT XỬ LÝ", styles["PDFSection"]))

	overall_score = eval_data.get("overall_score", 0)
	recommendation = eval_data.get("recommendation", "—")
	proposal_level = eval_data.get("proposal_level", "—")

	# Score + Proposal in a 2-column card
	overview_data = [
		[
			Paragraph("Điểm tổng", styles["PDFScoreLabel"]),
			Paragraph("Mức đề xuất", styles["PDFScoreLabel"]),
		],
		[
			Paragraph(
				f"{overall_score:.1f} / 10" if overall_score else "—",
				styles["PDFScoreLarge"],
			),
			Paragraph(
				_safe(proposal_level),
				styles["PDFCellBoldCenter"],
			),
		],
	]

	col_w = page_width / 3
	overview_table = Table(overview_data, colWidths=[col_w, col_w, col_w])
	overview_table.setStyle(TableStyle([
		("ALIGN", (0, 0), (-1, -1), "CENTER"),
		("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
		("TOPPADDING", (0, 0), (-1, 0), 8),
		("BOTTOMPADDING", (0, 0), (-1, 0), 3),
		("TOPPADDING", (0, 1), (-1, 1), 3),
		("BOTTOMPADDING", (0, 1), (-1, 1), 10),
		("BACKGROUND", (0, 0), (-1, -1), _CLR_BG_SCORE),
		("BOX", (0, 0), (-1, -1), 0.5, _CLR_BORDER),
		("LINEBEFORE", (1, 0), (1, -1), 0.3, _CLR_BORDER_LIGHT),
		("LINEBEFORE", (2, 0), (2, -1), 0.3, _CLR_BORDER_LIGHT),
	]))
	result.append(overview_table)
	result.append(Spacer(1, 4 * mm))

	# Recommendation text
	result.append(Paragraph(
		"<b>Đề xuất của 2AS:</b> " + _safe(recommendation, 600),
		styles["PDFBody"],
	))

	# Reasoning paragraph
	reasoning = eval_data.get("recommendation_reasoning", "")
	if reasoning:
		result.append(Paragraph(
			"<b>Lý do:</b> " + _safe(reasoning, 600),
			styles["PDFBody"],
		))

	return result


def _render_competency_table(eval_data, styles, page_width):
	"""Render competency table section for the PDF.
	
	Returns:
		list: ReportLab story elements for this section.
	"""
	result = []
	# 4. BẢNG NĂNG LỰC

	competency_scores = eval_data.get("competency_scores", [])
	if competency_scores:
		result.append(_section_divider())
		result.append(Paragraph(
			f"4. CHI TIẾT NĂNG LỰC ({len(competency_scores)} tiêu chí)",
			styles["PDFSection"],
		))

		col_stt_w = page_width * 0.06
		col_name_w = page_width * 0.54
		col_weight_w = page_width * 0.20
		col_score_w = page_width * 0.20

		style_cell_center = ParagraphStyle(
			"_CellCenter",
			parent=styles["PDFCell"],
			alignment=TA_CENTER,
		)
		style_cell_center_bold = ParagraphStyle(
			"_CellCenterBold",
			parent=styles["PDFCellBold"],
			alignment=TA_CENTER,
		)

		comp_data = [
			[
				Paragraph("STT", styles["PDFTableHeader"]),
				Paragraph("Năng lực", styles["PDFTableHeader"]),
				Paragraph("Trọng số", styles["PDFTableHeader"]),
				Paragraph("Điểm", styles["PDFTableHeader"]),
			]
		]

		total_weight = 0
		weighted_score = 0

		for idx, cs in enumerate(competency_scores, 1):
			score_val = cs.get("score", 0)
			weight_val = cs.get("weight", 0)
			total_weight += weight_val
			weighted_score += score_val * weight_val / 100.0

			comp_data.append([
				Paragraph(str(idx), style_cell_center),
				Paragraph(
					_safe(cs.get("competency_name", ""), 80),
					styles["PDFCell"],
				),
				Paragraph(f"{weight_val}%", style_cell_center),
				Paragraph(f"{score_val:.1f}", style_cell_center_bold),
			])

		# Total row
		overall = eval_data.get("overall_score", weighted_score)
		comp_data.append([
			Paragraph("", styles["PDFCell"]),
			Paragraph("ĐIỂM TỔNG", styles["PDFCellBold"]),
			Paragraph(f"{total_weight}%", style_cell_center_bold),
			Paragraph(f"{overall:.1f}", style_cell_center_bold),
		])

		comp_table = Table(
			comp_data,
			colWidths=[col_stt_w, col_name_w, col_weight_w, col_score_w],
		)

		total_row_idx = len(comp_data) - 1

		table_cmds = [
			("FONTNAME", (0, 0), (-1, -1), _FONT_NAME),
			("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
			("TOPPADDING", (0, 0), (-1, -1), 6),
			("BOTTOMPADDING", (0, 0), (-1, -1), 6),
			("BACKGROUND", (0, 0), (-1, 0), _CLR_BG_HEADER),
			("LINEBELOW", (0, 0), (-1, 0), 0.8, _CLR_BORDER),
			("BOX", (0, 0), (-1, -1), 0.5, _CLR_BORDER),
			("LINEBELOW", (0, 1), (-1, total_row_idx - 1), 0.3, _CLR_BORDER_LIGHT),
			("LINEBEFORE", (1, 0), (1, -1), 0.3, _CLR_BORDER_LIGHT),
			("LINEBEFORE", (2, 0), (2, -1), 0.3, _CLR_BORDER_LIGHT),
			("LINEBEFORE", (3, 0), (3, -1), 0.3, _CLR_BORDER_LIGHT),
			("LINEABOVE", (0, total_row_idx), (-1, total_row_idx), 1, _CLR_BORDER),
			("BACKGROUND", (0, total_row_idx), (-1, total_row_idx), _CLR_BG_HEADER),
		]

		for i in range(1, total_row_idx):
			if i % 2 == 0:
				table_cmds.append(
					("BACKGROUND", (0, i), (-1, i), _CLR_BG_ALT)
				)

		comp_table.setStyle(TableStyle(table_cmds))
		result.append(comp_table)

	return result


def _render_detail_analysis(eval_data, styles):
	"""Render detail analysis section for the PDF.
	
	Returns:
		list: ReportLab story elements for this section.
	"""
	result = []
	# 4. PHÂN TÍCH CHI TIẾT

	rec_details = eval_data.get("recommendation_details")
	if rec_details and isinstance(rec_details, dict):
		result.append(_section_divider())
		result.append(Paragraph("4. PHÂN TÍCH CHI TIẾT", styles["PDFSection"]))

		# Reasoning
		rec_reasoning = rec_details.get("reasoning", "")
		if rec_reasoning:
			result.append(Paragraph(
				_safe(rec_reasoning, 600),
				styles["PDFBody"],
			))
			result.append(Spacer(1, 2 * mm))

		# Strengths
		strengths = rec_details.get("strengths", [])
		if strengths:
			result.append(Paragraph(
				"<b>ĐIỂM MẠNH</b>", styles["PDFBodyBold"],
			))
			result.append(Spacer(1, 1 * mm))
			for s in strengths[:8]:
				result.append(Paragraph(
					"  •  " + _safe(s, 300), styles["PDFBody"],
				))

		# Improvements
		improvements = rec_details.get("improvements", [])
		if improvements:
			result.append(Spacer(1, 3 * mm))
			result.append(Paragraph(
				"<b>CẦN CẢI THIỆN</b>", styles["PDFBodyBold"],
			))
			result.append(Spacer(1, 1 * mm))
			for s in improvements[:8]:
				result.append(Paragraph(
					"  •  " + _safe(s, 300), styles["PDFBody"],
				))

		# Development potential
		potential = rec_details.get("development_potential", "")
		if potential:
			result.append(Spacer(1, 3 * mm))
			result.append(Paragraph(
				"<b>TIỀM NĂNG PHÁT TRIỂN</b>", styles["PDFBodyBold"],
			))
			result.append(Spacer(1, 1 * mm))
			result.append(Paragraph(
				_safe(potential, 500),
				styles["PDFBody"],
			))

		# Risk flags
		risks = rec_details.get("risk_flags", [])
		if risks:
			result.append(Spacer(1, 3 * mm))
			result.append(Paragraph(
				"<b>RỦI RO CẦN LƯU Ý</b>", styles["PDFBodyBold"],
			))
			result.append(Spacer(1, 1 * mm))
			for r in risks[:5]:
				result.append(Paragraph(
					"  •  " + _safe(r, 300), styles["PDFBody"],
				))

		# Conditions if renew
		conditions = rec_details.get("conditions_if_renew", [])
		if conditions:
			result.append(Spacer(1, 3 * mm))
			result.append(Paragraph(
				"<b>ĐIỀU KIỆN TÁI KÝ</b>", styles["PDFBodyBold"],
			))
			result.append(Spacer(1, 1 * mm))
			for c in conditions[:5]:
				result.append(Paragraph(
					"  •  " + _safe(c, 300), styles["PDFBody"],
				))

	return result


def _render_manager_evaluation(eval_data, styles, page_width):
	"""Render manager evaluation section for the PDF.
	
	Returns:
		list: ReportLab story elements for this section.
	"""
	result = []
	ql = eval_data.get("danh_gia_quan_ly", {})
	if ql and isinstance(ql, dict):
		result.append(_section_divider())
		result.append(Paragraph("5. ĐÁNH GIÁ ĐỀ XUẤT QUẢN LÝ", styles["PDFSection"]))

		col_lbl = 3.2 * cm
		col_val = page_width - col_lbl

		ql_rows = [
			[Paragraph("Đề xuất quản lý", styles["PDFSmall"]),
			 Paragraph(_safe(ql.get("de_xuat_quan_ly", "—"), 800), styles["PDFCellBold"])],
			[Paragraph("Mức độ đồng ý", styles["PDFSmall"]),
			 Paragraph(_safe(ql.get("muc_do_dong_y", "—")), styles["PDFCellBold"])],
			[Paragraph("Lý do chính", styles["PDFSmall"]),
			 Paragraph(_safe(ql.get("ly_do_chinh", "—"), 800), styles["PDFBody"])],
			[Paragraph("Phân tích AI", styles["PDFSmall"]),
			 Paragraph(_safe(ql.get("phan_tich_chi_tiet", "—"), 800), styles["PDFBody"])],
			[Paragraph("Nhận xét chung", styles["PDFSmall"]),
			 Paragraph(_safe(ql.get("nhan_xet", "—"), 800), styles["PDFBody"])],
			[Paragraph("Khuyến nghị", styles["PDFSmall"]),
			 Paragraph(_safe(ql.get("khuyen_nghi_xu_ly", "—"), 800), styles["PDFBodyBold"])],
		]

		ql_table = Table(ql_rows, colWidths=[col_lbl, col_val])
		ql_table.setStyle(TableStyle([
			("BACKGROUND", (0, 0), (-1, -1), _CLR_BG_ALT),
			("BOX", (0, 0), (-1, -1), 0.5, _CLR_BORDER),
			("LINEBELOW", (0, 0), (-1, -1), 0.3, _CLR_BORDER_LIGHT),
			("VALIGN", (0, 0), (-1, -1), "TOP"),
			("TOPPADDING", (0, 0), (-1, -1), 6),
			("BOTTOMPADDING", (0, 0), (-1, -1), 6),
			("LEFTPADDING", (0, 0), (0, -1), 8),
		]))
		result.append(ql_table)
		result.append(Spacer(1, 4 * mm))

	return result


def _render_next_steps(eval_data, styles):
	"""Render next steps section for the PDF.
	
	Returns:
		list: ReportLab story elements for this section.
	"""
	result = []
	# 5. BƯỚC XỬ LÝ TIẾP THEO

	next_steps = eval_data.get("next_steps")
	if next_steps:
		if isinstance(next_steps, str):
			try:
				next_steps = json.loads(next_steps)
			except (json.JSONDecodeError, TypeError):
				next_steps = []

	if next_steps and isinstance(next_steps, list) and len(next_steps) > 0:
		result.append(_section_divider())
		result.append(Paragraph(
			f"6. BƯỚC XỬ LÝ TIẾP THEO ({len(next_steps)} mục)",
			styles["PDFSection"],
		))

		for idx, step in enumerate(next_steps, 1):
			if isinstance(step, dict):
				action = _safe(step.get("action", ""), 300)
				priority = _safe(step.get("priority", ""), 20)
				responsible = _safe(step.get("responsible", ""), 50)
				deadline = _safe(step.get("deadline", ""), 30)

				step_text = f"<b>{idx}.</b> {action}"
				meta_parts = []
				if priority:
					meta_parts.append(f"Ưu tiên: {priority}")
				if responsible:
					meta_parts.append(f"Phụ trách: {responsible}")
				if deadline:
					meta_parts.append(f"Thời hạn: {deadline}")
				meta = " | ".join(meta_parts)

				result.append(Paragraph(step_text, styles["PDFBody"]))
				if meta:
					result.append(Paragraph(
						f"    <i>{meta}</i>",
						styles["PDFSmall"],
					))
				result.append(Spacer(1, 1 * mm))
			else:
				result.append(Paragraph(
					f"<b>{idx}.</b> " + _safe(str(step), 300),
					styles["PDFBody"],
				))

	return result


def _render_evidence(eval_data, styles):
	"""Render evidence section for the PDF.
	
	Returns:
		list: ReportLab story elements for this section.
	"""
	result = []
	# 6. BẰNG CHỨNG TRÍCH XUẤT

	evidence_list = eval_data.get("evidence", [])
	if evidence_list:
		result.append(_section_divider())
		result.append(Paragraph(
			f"7. BẰNG CHỨNG TRÍCH XUẤT ({len(evidence_list)} mục)",
			styles["PDFSection"],
		))

		for idx, ev in enumerate(evidence_list[:15]):
			statement = _safe(ev.get("statement", ""), 300)
			comp = _safe(ev.get("mapped_competency", ""), 50)
			source = _safe(ev.get("source_document", ""), 50)

			prefix = f"<b>{idx + 1}.</b> "
			suffix_parts = []
			if comp:
				suffix_parts.append(f"[{comp}]")
			if source:
				suffix_parts.append(f"({source})")
			suffix = " — " + " ".join(suffix_parts) if suffix_parts else ""

			result.append(Paragraph(
				prefix + statement + suffix,
				styles["PDFBody"],
			))

	return result


def _render_footer(styles):
	"""Render footer section for the PDF.
	
	Returns:
		list: ReportLab story elements for this section.
	"""
	result = []
	# FOOTER NOTE

	result.append(Spacer(1, 12 * mm))
	result.append(_section_divider())
	result.append(Paragraph(
		_safe(
			"Báo cáo được tạo tự động bởi Hệ thống 2AS — Đánh giá AI. "
			"Kết quả mang tính tham khảo và cần được xem xét bởi cấp quản lý trước khi quyết định."
		),
		styles["PDFFooter"],
	))

	return result


def generate_pdf(eval_data):
	"""Generate a clean, B&W-print-friendly PDF from evaluation data.

	Matches the UI output with all sections:
	1. Thông tin nhân viên
	2. Tình trạng hồ sơ
	3. Nhận định của 2AS & Đề xuất xử lý
	4. Bảng năng lực
	5. Phân tích chi tiết
	6. Bước xử lý tiếp theo
	7. Bằng chứng trích xuất
	8. Kết quả kiểm tra dữ liệu

	Args:
		eval_data: Dict containing all evaluation results.

	Returns:
		BytesIO buffer containing the generated PDF.
	"""
	buffer = io.BytesIO()
	styles = _get_styles()

	doc = SimpleDocTemplate(
		buffer,
		pagesize=A4,
		leftMargin=2 * cm,
		rightMargin=2 * cm,
		topMargin=1.8 * cm,
		bottomMargin=1.8 * cm,
		title="Ket Qua Danh Gia Tai Ky Hop Dong",
		author="HR Contract Evaluation System - 2AS",
	)

	page_width = A4[0] - 4 * cm  # usable width

	current_time = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

	# ============================================================
	
	elements = []
	elements.extend(_render_pdf_header(eval_data, styles, current_time))
	elements.extend(_render_employee_info(eval_data, styles, page_width))
	elements.extend(_render_data_check(eval_data, styles))
	elements.extend(_render_assessment(eval_data, styles, page_width))
	elements.extend(_render_competency_table(eval_data, styles, page_width))
	elements.extend(_render_detail_analysis(eval_data, styles))
	elements.extend(_render_manager_evaluation(eval_data, styles, page_width))
	elements.extend(_render_next_steps(eval_data, styles))
	elements.extend(_render_evidence(eval_data, styles))
	elements.extend(_render_footer(styles))

	def _add_page_number(canvas, doc):
		"""Draw page number on the bottom right corner."""
		page_num = canvas.getPageNumber()
		text = f"Trang {page_num}"
		canvas.saveState()
		canvas.setFont(_FONT_NAME, 8)
		canvas.setFillColor(_CLR_MEDIUM)
		canvas.drawRightString(A4[0] - 2 * cm, 1 * cm, text)
		canvas.restoreState()

	# Build PDF
	doc.build(
		elements,
		onFirstPage=_add_page_number,
		onLaterPages=_add_page_number,
	)
	buffer.seek(0)
	return buffer

# ── Re-export for backwards compatibility ──────────────────────────────────────
from cnb_2as.services.thu_viec_pdf import generate_thu_viec_pdf  # noqa: F401, E402
