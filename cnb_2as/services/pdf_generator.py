# Copyright (c) 2025, antruong and contributors
# For license information, please see license.txt

"""PDF Generator for HR Contract Evaluation Results.

Generates a formatted A4 PDF report optimized for B&W printing:
light backgrounds, thin borders, clean professional layout.
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

	elements = []
	page_width = A4[0] - 4 * cm  # usable width

	import datetime
	current_time = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

	# ============================================================
	# HEADER
	# ============================================================

	elements.append(Spacer(1, 4 * mm))
	elements.append(Paragraph(
		_safe("BÁO CÁO KẾT QUẢ ĐÁNH GIÁ TÁI KÝ HỢP ĐỒNG"),
		styles["PDFTitle"],
	))
	elements.append(Paragraph(
		_safe("Hệ thống 2AS — Đánh giá AI Tự động và Khách quan"),
		styles["PDFSubtitle"],
	))
	elements.append(Paragraph(
		_safe(f"Mã đánh giá: {eval_data.get('name', '—')} | Thời gian xuất: {current_time}"),
		styles["PDFSubtitle"],
	))
	elements.append(_section_divider())

	# ============================================================
	# 1. THÔNG TIN NHÂN VIÊN
	# ============================================================

	elements.append(Paragraph("1. THÔNG TIN NHÂN VIÊN", styles["PDFSection"]))

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
	elements.append(info_table)
	elements.append(Spacer(1, 4 * mm))

	# ============================================================
	# 2. KIỂM TRA HỒ SƠ & DỮ LIỆU
	# ============================================================

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
		elements.append(_section_divider())
		elements.append(Paragraph("2. KIỂM TRA HỒ SƠ & DỮ LIỆU", styles["PDFSection"]))

		# A. Tình trạng hồ sơ
		if doc_warnings:
			is_complete = doc_warnings.get("is_complete", True)
			warnings_list = doc_warnings.get("warnings", [])

			if is_complete:
				elements.append(Paragraph(
					"✓ <b>Hồ sơ đầy đủ:</b> Đã điền đủ các thông tin bắt buộc.",
					styles["PDFBody"],
				))
			else:
				if warnings_list:
					elements.append(Paragraph(
						f"<b>⚠ Hồ sơ cần bổ sung</b> — Có trường thông tin bị để trống:",
						styles["PDFBody"],
					))
					elements.append(Spacer(1, 1 * mm))
					for w in warnings_list:
						msg = _safe(w.get("message", "") if isinstance(w, dict) else str(w), 200)
						elements.append(Paragraph("  •  " + msg, styles["PDFWarning"]))
				
				elements.append(Spacer(1, 3 * mm))

		# B. Kết quả kiểm tra dữ liệu
		if has_validation:
			if validation_warnings:
				elements.append(Paragraph("<b>⚠ Cảnh báo dữ liệu đầu vào:</b>", styles["PDFBody"]))
				for w in validation_warnings:
					msg = _safe(w.get("message", "") if isinstance(w, dict) else str(w), 200)
					elements.append(Paragraph("  !  " + msg, styles["PDFWarning"]))
				elements.append(Spacer(1, 3 * mm))

	# ============================================================
	# 3. NHẬN ĐỊNH CỦA 2AS & ĐỀ XUẤT XỬ LÝ
	# ============================================================

	elements.append(_section_divider())
	elements.append(Paragraph("3. NHẬN ĐỊNH CỦA 2AS & ĐỀ XUẤT XỬ LÝ", styles["PDFSection"]))

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
	elements.append(overview_table)
	elements.append(Spacer(1, 4 * mm))

	# Recommendation text
	elements.append(Paragraph(
		"<b>Đề xuất của 2AS:</b> " + _safe(recommendation, 600),
		styles["PDFBody"],
	))

	# Reasoning paragraph
	reasoning = eval_data.get("recommendation_reasoning", "")
	if reasoning:
		elements.append(Paragraph(
			"<b>Lý do:</b> " + _safe(reasoning, 600),
			styles["PDFBody"],
		))

	# ============================================================
	# 4. BẢNG NĂNG LỰC
	# ============================================================

	competency_scores = eval_data.get("competency_scores", [])
	if competency_scores:
		elements.append(_section_divider())
		elements.append(Paragraph(
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
		elements.append(comp_table)

	# ============================================================
	# 4. PHÂN TÍCH CHI TIẾT
	# ============================================================

	rec_details = eval_data.get("recommendation_details")
	if rec_details and isinstance(rec_details, dict):
		elements.append(_section_divider())
		elements.append(Paragraph("4. PHÂN TÍCH CHI TIẾT", styles["PDFSection"]))

		# Reasoning
		rec_reasoning = rec_details.get("reasoning", "")
		if rec_reasoning:
			elements.append(Paragraph(
				_safe(rec_reasoning, 600),
				styles["PDFBody"],
			))
			elements.append(Spacer(1, 2 * mm))

		# Strengths
		strengths = rec_details.get("strengths", [])
		if strengths:
			elements.append(Paragraph(
				"<b>ĐIỂM MẠNH</b>", styles["PDFBodyBold"],
			))
			elements.append(Spacer(1, 1 * mm))
			for s in strengths[:8]:
				elements.append(Paragraph(
					"  •  " + _safe(s, 300), styles["PDFBody"],
				))

		# Improvements
		improvements = rec_details.get("improvements", [])
		if improvements:
			elements.append(Spacer(1, 3 * mm))
			elements.append(Paragraph(
				"<b>CẦN CẢI THIỆN</b>", styles["PDFBodyBold"],
			))
			elements.append(Spacer(1, 1 * mm))
			for s in improvements[:8]:
				elements.append(Paragraph(
					"  •  " + _safe(s, 300), styles["PDFBody"],
				))

		# Development potential
		potential = rec_details.get("development_potential", "")
		if potential:
			elements.append(Spacer(1, 3 * mm))
			elements.append(Paragraph(
				"<b>TIỀM NĂNG PHÁT TRIỂN</b>", styles["PDFBodyBold"],
			))
			elements.append(Spacer(1, 1 * mm))
			elements.append(Paragraph(
				_safe(potential, 500),
				styles["PDFBody"],
			))

		# Risk flags
		risks = rec_details.get("risk_flags", [])
		if risks:
			elements.append(Spacer(1, 3 * mm))
			elements.append(Paragraph(
				"<b>RỦI RO CẦN LƯU Ý</b>", styles["PDFBodyBold"],
			))
			elements.append(Spacer(1, 1 * mm))
			for r in risks[:5]:
				elements.append(Paragraph(
					"  •  " + _safe(r, 300), styles["PDFBody"],
				))

		# Conditions if renew
		conditions = rec_details.get("conditions_if_renew", [])
		if conditions:
			elements.append(Spacer(1, 3 * mm))
			elements.append(Paragraph(
				"<b>ĐIỀU KIỆN TÁI KÝ</b>", styles["PDFBodyBold"],
			))
			elements.append(Spacer(1, 1 * mm))
			for c in conditions[:5]:
				elements.append(Paragraph(
					"  •  " + _safe(c, 300), styles["PDFBody"],
				))

	# ============================================================
	# 5. BƯỚC XỬ LÝ TIẾP THEO
	# ============================================================

	next_steps = eval_data.get("next_steps")
	if next_steps:
		if isinstance(next_steps, str):
			try:
				next_steps = json.loads(next_steps)
			except (json.JSONDecodeError, TypeError):
				next_steps = []

	if next_steps and isinstance(next_steps, list) and len(next_steps) > 0:
		elements.append(_section_divider())
		elements.append(Paragraph(
			f"5. BƯỚC XỬ LÝ TIẾP THEO ({len(next_steps)} mục)",
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

				elements.append(Paragraph(step_text, styles["PDFBody"]))
				if meta:
					elements.append(Paragraph(
						f"    <i>{meta}</i>",
						styles["PDFSmall"],
					))
				elements.append(Spacer(1, 1 * mm))
			else:
				elements.append(Paragraph(
					f"<b>{idx}.</b> " + _safe(str(step), 300),
					styles["PDFBody"],
				))

	# ============================================================
	# 6. BẰNG CHỨNG TRÍCH XUẤT
	# ============================================================

	evidence_list = eval_data.get("evidence", [])
	if evidence_list:
		elements.append(_section_divider())
		elements.append(Paragraph(
			f"6. BẰNG CHỨNG TRÍCH XUẤT ({len(evidence_list)} mục)",
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

			elements.append(Paragraph(
				prefix + statement + suffix,
				styles["PDFBody"],
			))

	# ============================================================
	# FOOTER NOTE
	# ============================================================

	elements.append(Spacer(1, 12 * mm))
	elements.append(_section_divider())
	elements.append(Paragraph(
		_safe(
			"Báo cáo được tạo tự động bởi Hệ thống 2AS — Đánh giá AI. "
			"Kết quả mang tính tham khảo và cần được xem xét bởi cấp quản lý trước khi quyết định."
		),
		styles["PDFFooter"],
	))

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


def generate_thu_viec_pdf(eval_data):
	"""Generate a professional PDF for Thu Viec evaluation.

	Layout: Header CT Group → Thông tin NV → Status badge → Tổng quan
	        → 7 tiêu chí 2AS → Đề xuất xử lý → Việc cần làm → Footer
	"""
	import datetime
	buffer = io.BytesIO()
	_register_vietnamese_font()
	styles = _get_styles()

	doc = SimpleDocTemplate(
		buffer, pagesize=A4,
		leftMargin=2*cm, rightMargin=2*cm,
		topMargin=2*cm, bottomMargin=2*cm,
		title="Bao Cao Danh Gia Thu Viec",
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
		[[Paragraph("CT GROUP  ·  BÁO CÁO ĐÁNH GIÁ THỬ VIỆC", brand_style), Paragraph(f"Ngày xuất: {now_str}", date_style)]],
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
			[Paragraph("Kết quả thử việc", ParagraphStyle("_dxlbl", fontName=_FONT_BOLD, fontSize=8, textColor=CLR_GRAY)),
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

	# ── 7. VIỆC CẦN LÀM ──────────────────────────────────────────────────────
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

	# ── 8. FOOTER ─────────────────────────────────────────────────────────────
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
		canvas.drawString(2*cm, 1.2*cm, "CT Group – Báo cáo đánh giá thử việc")
		canvas.restoreState()

	doc.build(elements, onFirstPage=_page_num, onLaterPages=_page_num)
	buffer.seek(0)
	return buffer
	import datetime
	buffer = io.BytesIO()
	styles = _get_styles()

	doc = SimpleDocTemplate(
		buffer, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
		topMargin=1.8*cm, bottomMargin=1.8*cm,
		title="Ket Qua Danh Gia Thu Viec",
	)

	elements = []
	page_width = A4[0] - 4*cm
	current_time = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

	elements.append(Spacer(1, 4 * mm))
	elements.append(Paragraph(_safe("BÁO CÁO KẾT QUẢ ĐÁNH GIÁ THỬ VIỆC"), styles["PDFTitle"]))
	elements.append(Paragraph(_safe("Hệ thống Đánh giá AI — Tự động và Khách quan"), styles["PDFSubtitle"]))
	elements.append(Paragraph(_safe(f"Thời gian xuất báo cáo: {current_time}"), styles["PDFSubtitle"]))
	elements.append(_section_divider())

	r = eval_data.get("re_review", {}) if "re_review" in eval_data else eval_data
	nv = eval_data.get("nhan_vien", {})

	# Status
	status = r.get("status", "CHƯA RÕ")
	elements.append(Paragraph(f"KẾT QUẢ: <b>{status}</b>", styles["PDFSection"]))
	elements.append(Spacer(1, 4*mm))

	col_label_w = 3.2 * cm
	col_value_w = page_width / 2 - col_label_w
	info_left = [
		[Paragraph("Họ tên NV:", styles["PDFSmall"]), Paragraph(_safe(nv.get("ten_nhan_vien", "—")), styles["PDFCellBold"])],
		[Paragraph("Mã NV:", styles["PDFSmall"]), Paragraph(_safe(nv.get("ma_nhan_vien", "—")), styles["PDFCell"])],
		[Paragraph("Chức danh:", styles["PDFSmall"]), Paragraph(_safe(nv.get("chuc_danh", "—")), styles["PDFCell"])],
		[Paragraph("Đơn vị:", styles["PDFSmall"]), Paragraph(_safe(nv.get("don_vi", "—")), styles["PDFCell"])],
	]
	info_right = [
		[Paragraph("Họ tên QL:", styles["PDFSmall"]), Paragraph(_safe(nv.get("ten_hod", "—")), styles["PDFCellBold"])],
		[Paragraph("Mã QL:", styles["PDFSmall"]), Paragraph(_safe(nv.get("ma_hod", "—")), styles["PDFCell"])],
		[Paragraph("Chức danh:", styles["PDFSmall"]), Paragraph(_safe(nv.get("chuc_danh_hod", "—")), styles["PDFCell"])],
		[Paragraph("", styles["PDFSmall"]), Paragraph("", styles["PDFCell"])],
	]
	info_data = []
	for i in range(len(info_left)):
		info_data.append(info_left[i] + info_right[i])
	info_table = Table(info_data, colWidths=[col_label_w, col_value_w, col_label_w, col_value_w])
	info_table.setStyle(TableStyle([
		("FONTNAME", (0, 0), (-1, -1), _FONT_NAME),
		("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
		("TOPPADDING", (0, 0), (-1, -1), 4),
		("BOTTOMPADDING", (0, 0), (-1, -1), 4),
		("LINEBELOW", (0, 0), (-1, -1), 0.3, _CLR_BORDER_LIGHT),
	]))
	elements.append(info_table)

	tong_quan = r.get("tong_quan", "")
	if tong_quan:
		elements.append(_section_divider())
		elements.append(Paragraph("NHẬN XÉT TỔNG QUAN", styles["PDFSection"]))
		elements.append(Paragraph(_safe(tong_quan, 1000), styles["PDFBody"]))

	kpi_rows = r.get("xlsx_kpi", [])
	if kpi_rows:
		elements.append(_section_divider())
		elements.append(Paragraph("BẢNG KPI", styles["PDFSection"]))
		kpi_data = [[
			Paragraph("STT", styles["PDFTableHeader"]),
			Paragraph("Công việc", styles["PDFTableHeader"]),
			Paragraph("Tỷ lệ", styles["PDFTableHeader"]),
			Paragraph("Trạng thái", styles["PDFTableHeader"])
		]]
		style_cell_center = ParagraphStyle("_CellCenter", parent=styles["PDFCell"], alignment=TA_CENTER)
		for k in kpi_rows:
			pct = "—"
			if k.get("ty_le_thuc_hien") is not None:
				try:
					pct = f"{float(k['ty_le_thuc_hien']) * 100:.0f}%"
				except (ValueError, TypeError):
					pass
			kpi_data.append([
				Paragraph(str(k.get("stt", "")), style_cell_center),
				Paragraph(_safe(k.get("cong_viec", ""), 150), styles["PDFCell"]),
				Paragraph(pct, style_cell_center),
				Paragraph(str(k.get("status", "")), style_cell_center),
			])
		kpi_table = Table(kpi_data, colWidths=[page_width*0.08, page_width*0.62, page_width*0.15, page_width*0.15])
		kpi_table.setStyle(TableStyle([
			("FONTNAME", (0, 0), (-1, -1), _FONT_NAME),
			("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
			("BACKGROUND", (0, 0), (-1, 0), _CLR_BG_HEADER),
			("BOX", (0, 0), (-1, -1), 0.5, _CLR_BORDER),
			("LINEBELOW", (0, 0), (-1, -1), 0.3, _CLR_BORDER_LIGHT),
			("LINEBEFORE", (1, 0), (-1, -1), 0.3, _CLR_BORDER_LIGHT),
		]))
		elements.append(kpi_table)

	uu_diem = r.get("uu_diem", [])
	if uu_diem:
		elements.append(_section_divider())
		elements.append(Paragraph("ĐIỂM TỐT", styles["PDFSection"]))
		for u in uu_diem:
			elements.append(Paragraph("• " + _safe(u, 300), styles["PDFBody"]))

	van_de = r.get("van_de", [])
	if van_de:
		elements.append(_section_divider())
		elements.append(Paragraph("VẤN ĐỀ CẦN SỬA", styles["PDFSection"]))
		for v in van_de:
			loai = v.get("loai", "")
			ntc = v.get("nhom_tieu_chi", "")
			lbl = f"[{loai}] " + (f"[{ntc}] " if ntc else "")
			elements.append(Paragraph("<b>" + _safe(lbl) + "</b> " + _safe(v.get("van_de", ""), 300), styles["PDFBody"]))
			elements.append(Paragraph("<i>→ Cần làm:</i> " + _safe(v.get("yeu_cau", ""), 300), styles["PDFWarning"]))
			elements.append(Spacer(1, 2*mm))

	elements.append(Spacer(1, 12 * mm))
	elements.append(_section_divider())
	elements.append(Paragraph(_safe("Báo cáo được tạo tự động bởi Hệ thống Đánh giá AI. Kết quả mang tính tham khảo và cần được xem xét bởi cấp quản lý."), styles["PDFFooter"]))

	def _add_page_number(canvas, doc):
		page_num = canvas.getPageNumber()
		text = f"Trang {page_num}"
		canvas.saveState()
		canvas.setFont(_FONT_NAME, 8)
		canvas.setFillColor(_CLR_MEDIUM)
		canvas.drawRightString(A4[0] - 2 * cm, 1 * cm, text)
		canvas.restoreState()

	doc.build(elements, onFirstPage=_add_page_number, onLaterPages=_add_page_number)
	buffer.seek(0)
	return buffer
