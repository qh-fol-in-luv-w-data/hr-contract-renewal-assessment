# Copyright (c) 2026, antruong and contributors
# For license information, please see license.txt

"""PDF Generator for Manager Proposal Evaluation Report.

Generates BÁO CÁO ĐÁNH GIÁ TÍNH HỢP LÝ CỦA ĐỀ XUẤT QUẢN LÝ/HOD
as an A4 PDF optimized for B&W printing.

Report sections:
  1. Thông tin chung
  2. Tóm tắt nhanh đề xuất (comparison table)
  3. Tóm tắt căn cứ từ tờ trình
  4. Kết quả đánh giá từng đề xuất (criteria table + scores)
  5. Nhận định độc lập với kết quả ký/tái ký hợp đồng
  6. Kiến nghị xử lý
  7. Phụ lục
"""

import io

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

# ── Colour palette (B&W-friendly) ──────────────────────────────────────────────
_BLACK = colors.HexColor("#1a1a1a")
_DARK = colors.HexColor("#333333")
_MEDIUM = colors.HexColor("#666666")
_LIGHT = colors.HexColor("#888888")
_BORDER = colors.HexColor("#cccccc")
_BG_HEADER = colors.HexColor("#f0f0f0")
_BG_ALT = colors.HexColor("#f8f8f8")
_WHITE = colors.white
_GREEN = colors.HexColor("#15803d")
_GREEN_BORDER = colors.HexColor("#16a34a")
_GREEN_BG = colors.HexColor("#f0fdf4")

_FONT = "Helvetica"
_FONT_BOLD = "Helvetica-Bold"
_REGISTERED = False


def _ensure_font():
    global _REGISTERED, _FONT, _FONT_BOLD
    if _REGISTERED:
        return
    _REGISTERED = True
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        import os

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

        fp = next((p for p in font_paths if os.path.exists(p)), None)
        bp = next((p for p in bold_paths if os.path.exists(p)), None)

        if fp and bp:
            pdfmetrics.registerFont(TTFont("DejaVuSans", fp))
            pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", bp))
            _FONT = "DejaVuSans"
            _FONT_BOLD = "DejaVuSans-Bold"
    except Exception:
        pass


def _styles():
    _ensure_font()
    base = getSampleStyleSheet()

    def S(name, parent="Normal", **kwargs):
        kwargs.setdefault("fontName", _FONT)
        return ParagraphStyle(name, parent=base[parent], **kwargs)

    return {
        "doc_title": S("doc_title", fontSize=15, fontName=_FONT_BOLD,
                       textColor=_BLACK, alignment=TA_CENTER, spaceAfter=4),
        "doc_sub": S("doc_sub", fontSize=9, textColor=_MEDIUM,
                     alignment=TA_CENTER, spaceAfter=12),
        "section": S("section", fontSize=10, fontName=_FONT_BOLD,
                     textColor=_WHITE, spaceBefore=0, spaceAfter=0),
        "subsection": S("subsection", fontSize=10, fontName=_FONT_BOLD,
                        textColor=_DARK, spaceBefore=8, spaceAfter=4),
        "body": S("body", fontSize=9, textColor=_DARK,
                  leading=14, spaceAfter=4),
        "label": S("label", fontSize=8, textColor=_LIGHT,
                   fontName=_FONT_BOLD),
        "cell": S("cell", fontSize=8, textColor=_DARK, leading=11),
        "cell_bold": S("cell_bold", fontSize=8, textColor=_BLACK,
                       fontName=_FONT_BOLD, leading=11),
        "cell_center": S("cell_center", fontSize=8, textColor=_DARK,
                         leading=11, alignment=TA_CENTER),
        "score_big": S("score_big", fontSize=15, fontName=_FONT_BOLD,
                       textColor=_BLACK, alignment=TA_CENTER),
        "footer": S("footer", fontSize=7, textColor=_LIGHT,
                    alignment=TA_CENTER),
        "indent": S("indent", fontSize=9, textColor=_DARK,
                    leading=13, leftIndent=16, spaceAfter=3),
        "independence": S("independence", fontSize=8, textColor=_MEDIUM,
                          leading=13, leftIndent=8, rightIndent=8, spaceAfter=6),
        "rec_verdict": S("rec_verdict", fontSize=16, fontName=_FONT_BOLD,
                         textColor=_GREEN, alignment=TA_CENTER, spaceAfter=4),
        "rec_body": S("rec_body", fontSize=9, textColor=_GREEN,
                      leading=14, spaceAfter=4, alignment=TA_CENTER),
        "rec_label": S("rec_label", fontSize=8, textColor=_GREEN,
                       fontName=_FONT_BOLD, alignment=TA_CENTER),
    }


_REC_LABELS = {
    "APPROVE": "PHÊ DUYỆT",
    "APPROVE_WITH_CONDITIONS": "PHÊ DUYỆT CÓ ĐIỀU KIỆN",
    "PARTIALLY_APPROVE": "PHÊ DUYỆT MỘT PHẦN",
    "REQUEST_MORE_INFO": "CẦN BỔ SUNG THÔNG TIN",
    "REJECT": "KHÔNG PHÊ DUYỆT",
}

_PROPOSAL_LABELS = {
    "SALARY_INCREASE": "Tăng lương",
    "TITLE_APPOINTMENT": "Bổ nhiệm chức danh",
    "TITLE_ADJUSTMENT": "Điều chỉnh chức danh",
    "GRADE_CHANGE": "Thay đổi cấp bậc",
    "BENEFIT_ADJUSTMENT": "Điều chỉnh đãi ngộ / phụ cấp",
    "ROLE_CHANGE": "Điều chuyển vai trò",
    "OTHER": "Đề xuất khác",
}

_CRITERIA_LABELS = {
    "A": "Phù hợp với kết quả đánh giá nhân sự",
    "B": "Tương xứng với KPI, năng lực và hiệu quả công việc",
    "C": "Mức độ đóng góp và giá trị mang lại",
    "D": "Phù hợp với JD, chức danh, cấp bậc và cơ cấu tổ chức",
    "E": "Phù hợp với khung lương, đãi ngộ và thị trường",
    "F": "Phù hợp về thời điểm, ngân sách và rủi ro quản trị",
    "G": "Đầy đủ căn cứ và minh chứng",
}


def _fmt(val):
    if val is None:
        return "—"
    if isinstance(val, list):
        return "; ".join(str(x) for x in val) if val else "—"
    s = str(val).strip()
    return s if s else "—"


def _table_style(headers=True, alt_rows=True):
    ts = [
        ("FONTNAME", (0, 0), (-1, -1), _FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (-1, -1), _DARK),
        ("GRID", (0, 0), (-1, -1), 0.5, _BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]
    if headers:
        ts += [
            ("BACKGROUND", (0, 0), (-1, 0), _BG_HEADER),
            ("FONTNAME", (0, 0), (-1, 0), _FONT_BOLD),
            ("TEXTCOLOR", (0, 0), (-1, 0), _BLACK),
        ]
    if alt_rows:
        ts += [("BACKGROUND", (0, 2), (-1, 2), _BG_ALT)]
    return TableStyle(ts)


def _page_number_canvas(canvas, doc):
    canvas.saveState()
    canvas.setFont(_FONT, 7)
    canvas.setFillColor(_LIGHT)
    canvas.drawRightString(
        A4[0] - 1.5 * cm,
        0.8 * cm,
        f"Trang {doc.page}",
    )
    canvas.drawString(
        1.5 * cm,
        0.8 * cm,
        "BÁO CÁO ĐÁNH GIÁ ĐỀ XUẤT NHÂN SỰ",
    )
    canvas.restoreState()


def _section_block(title: str, W, S):
    """Return a full-width dark-background section header as a Table."""
    t = Table([[Paragraph(title, S["section"])]], colWidths=[W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _DARK),
        ("TEXTCOLOR", (0, 0), (-1, -1), _WHITE),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


# ── Main builder ───────────────────────────────────────────────────────────────

def generate_proposal_pdf(report_data: dict) -> io.BytesIO:
    """Generate the proposal evaluation PDF report.

    Args:
        report_data: Dict with keys from de_xuat.generate_report():
            evaluation_name, employee_name, department, current_title,
            uploaded_by, confirmed_by, evaluated_at, overall_score,
            recommendation, extracted (dict), evaluation (dict).

    Returns:
        BytesIO buffer with the PDF content.
    """
    _ensure_font()
    S = _styles()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=2 * cm,
        bottomMargin=1.8 * cm,
    )

    story = []

    extracted = report_data.get("extracted") or {}
    evaluation = report_data.get("evaluation") or {}
    emp = extracted.get("employee") or {}
    doc_meta = extracted.get("documentMetadata") or {}
    proposal_summary = extracted.get("proposalSummary") or {}
    proposal_items = extracted.get("proposalItems") or []
    work_results = extracted.get("workResults") or []
    eval_context = extracted.get("evaluationContext") or {}
    basis_list = extracted.get("proposalBasis") or []
    commitments = extracted.get("commitmentsAfterApproval") or []
    missing_fields = extracted.get("missingFields") or []
    ocr_warnings = extracted.get("extractionWarnings") or []

    proposal_evals = evaluation.get("proposalEvaluations") or []
    proposal_comparison = evaluation.get("proposalComparison") or []
    final_rec = evaluation.get("finalRecommendation") or {}

    W = doc.width

    # ── Title ──────────────────────────────────────────────────────────────────
    story.append(Paragraph(
        "BÁO CÁO ĐÁNH GIÁ ĐỀ XUẤT NHÂN SỰ", S["doc_title"]
    ))
    story.append(Paragraph(
        f"{report_data.get('employee_name', '—')}  ·  {report_data.get('department', '—')}",
        S["doc_sub"]
    ))
    story.append(HRFlowable(width=W, thickness=1, color=_BORDER, spaceAfter=6))

    # ── Kiến nghị xử lý (green box — at the top) ──────────────────────────────
    rec_decision = final_rec.get("decision") or report_data.get("recommendation", "")
    rec_label_top = _REC_LABELS.get(rec_decision, rec_decision)
    rec_summary = final_rec.get("summary", "")
    conditions = final_rec.get("approvalConditions") or []
    required_data = final_rec.get("requiredAdditionalData") or []
    next_step = final_rec.get("suggestedNextStep", "")

    detail_parts = []
    if rec_summary:
        detail_parts.append(rec_summary)
    if next_step:
        detail_parts.append(f"Bước tiếp theo: {next_step}")
    if conditions:
        detail_parts.append("Điều kiện: " + " | ".join(_fmt(c) for c in conditions))

    rec_rows = [
        [Paragraph("KIẾN NGHỊ XỬ LÝ", S["rec_label"])],
        [Paragraph(rec_label_top, S["rec_verdict"])],
    ]
    if detail_parts:
        rec_rows.append([Paragraph("<br/>".join(detail_parts), S["rec_body"])])

    rec_table = Table(rec_rows, colWidths=[W])
    rec_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _GREEN_BG),
        ("BOX", (0, 0), (-1, -1), 1.5, _GREEN_BORDER),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (0, 0), 12),
        ("BOTTOMPADDING", (0, 0), (0, 0), 2),
        ("TOPPADDING", (0, 1), (0, 1), 4),
        ("BOTTOMPADDING", (0, 1), (0, 1), 8),
        ("TOPPADDING", (0, 2), (0, 2), 0),
        ("BOTTOMPADDING", (0, 2), (0, 2), 12),
        ("LEFTPADDING", (0, 0), (-1, -1), 16),
        ("RIGHTPADDING", (0, 0), (-1, -1), 16),
    ]))
    story.append(rec_table)
    story.append(Spacer(1, 12))

    # ── Phần 1: Thông tin chung ────────────────────────────────────────────────
    story.append(Spacer(1, 8))
    story.append(_section_block("PHẦN 1: THÔNG TIN CHUNG", W, S))

    eval_display_name = report_data.get("evaluation_name", "").replace("PROP-", "")

    raw_types = proposal_summary.get("proposalTypes") or []
    if isinstance(raw_types, list):
        types_vn = ", ".join(_PROPOSAL_LABELS.get(t, t) for t in raw_types) if raw_types else "—"
    elif isinstance(raw_types, str):
        types_vn = _PROPOSAL_LABELS.get(raw_types, raw_types)
    else:
        types_vn = "—"

    info_rows = [
        ["Mã đánh giá:", eval_display_name, "Ngày đánh giá:", report_data.get("evaluated_at", "—")],
        ["Nhân sự:", report_data.get("employee_name", "—"), "Mã nhân viên:", _fmt(emp.get("employeeCode"))],
        ["Đơn vị:", report_data.get("department", "—"), "Chức danh:", report_data.get("current_title", "—")],
        ["Loại đề xuất:", types_vn, "Ngày tờ trình:", _fmt(doc_meta.get("documentDate"))],
        ["Người đề xuất:", _fmt(proposal_summary.get("requestedBy")), "", ""],
    ]

    info_col_widths = [W * 0.18, W * 0.32, W * 0.18, W * 0.32]
    info_table = Table(
        [[Paragraph(c, S["cell_bold"] if i % 2 == 0 else S["cell"]) for i, c in enumerate(row)] for row in info_rows],
        colWidths=info_col_widths,
    )
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), _FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, _BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("BACKGROUND", (0, 0), (0, -1), _BG_ALT),
        ("BACKGROUND", (2, 0), (2, -1), _BG_ALT),
        ("FONTNAME", (0, 0), (0, -1), _FONT_BOLD),
        ("FONTNAME", (2, 0), (2, -1), _FONT_BOLD),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 8))

    # ── Phần 2: Tóm tắt nhanh đề xuất ────────────────────────────────────────
    story.append(Spacer(1, 8))
    story.append(_section_block("PHẦN 2: TÓM TẮT NHANH ĐỀ XUẤT", W, S))

    cmp_header = ["Nội dung", "Thông tin hiện tại", "Thông tin đề xuất", "Chênh lệch / Ghi chú"]
    cmp_rows = [cmp_header]

    if proposal_comparison:
        for cmp in proposal_comparison:
            cmp_rows.append([
                _fmt(cmp.get("field")),
                _fmt(cmp.get("currentValue")),
                _fmt(cmp.get("proposedValue")),
                _fmt(cmp.get("delta") or cmp.get("comment")),
            ])
    elif proposal_items:
        for item in proposal_items:
            label = _PROPOSAL_LABELS.get(item.get("proposalType", ""), item.get("proposalType", "—"))
            field = _fmt(item.get("fieldName") or label)
            current = _fmt(item.get("currentValue"))
            proposed = _fmt(item.get("proposedValue"))
            delta_v = item.get("deltaValue")
            delta_p = item.get("deltaPercent")
            if delta_v and delta_p:
                delta_str = f"+{delta_v} ({delta_p:+.1f}%)" if float(delta_p) > 0 else f"{delta_v} ({delta_p:.1f}%)"
            elif delta_v:
                delta_str = str(delta_v)
            else:
                delta_str = "—"
            cmp_rows.append([field, current, proposed, delta_str])
    else:
        cmp_rows.append(["Không có dữ liệu so sánh", "—", "—", "—"])

    cmp_col_w = [W * 0.22, W * 0.25, W * 0.25, W * 0.28]
    cmp_table = Table(
        [[Paragraph(str(c), S["cell_bold"] if i == 0 else S["cell"]) for i, c in enumerate(row)] for row in cmp_rows],
        colWidths=cmp_col_w,
    )
    cmp_style = _table_style(headers=True, alt_rows=False)
    # Alternate data rows
    for r in range(2, len(cmp_rows), 2):
        cmp_style.add("BACKGROUND", (0, r), (-1, r), _BG_ALT)
    cmp_table.setStyle(cmp_style)
    story.append(cmp_table)
    story.append(Spacer(1, 8))

    # ── Phần 3: Kết quả đánh giá từng đề xuất ────────────────────────────────
    story.append(Spacer(1, 8))
    story.append(_section_block("PHẦN 3: KẾT QUẢ ĐÁNH GIÁ TỪNG ĐỀ XUẤT", W, S))

    if not proposal_evals:
        story.append(Paragraph("Chưa có kết quả đánh giá.", S["body"]))
    else:
        for idx, pe in enumerate(proposal_evals, 1):
            ptype = pe.get("proposalType", "")
            plabel = pe.get("proposalLabel") or _PROPOSAL_LABELS.get(ptype, ptype)
            criteria_scores_list = pe.get("criteriaScores", [])
            score = sum(cs.get("score", 0) for cs in criteria_scores_list) if criteria_scores_list else pe.get("score", 0)
            rec = pe.get("recommendation", "")
            rec_label = _REC_LABELS.get(rec, rec)
            rating = pe.get("ratingLevel", "")

            story.append(Paragraph(
                f"3.{idx}. Đánh giá đề xuất: {plabel}", S["subsection"]
            ))

            # Score + verdict header row
            score_row_data = [
                [
                    Paragraph(f"<b>Điểm tổng</b>", S["cell_bold"]),
                    Paragraph(f"{score}/100", S["score_big"]),
                    Paragraph(f"<b>Kết luận</b>", S["cell_bold"]),
                    Paragraph(rec_label, S["cell_bold"]),
                ],
            ]
            if pe.get("recommendedValue"):
                score_row_data.append([
                    Paragraph("<b>Giá trị khuyến nghị</b>", S["cell_bold"]),
                    Paragraph(_fmt(pe["recommendedValue"]), S["cell"]),
                    Paragraph("<b>Mức đánh giá</b>", S["cell_bold"]),
                    Paragraph(_fmt(rating), S["cell"]),
                ])
            score_table = Table(score_row_data, colWidths=[W * 0.2, W * 0.3, W * 0.2, W * 0.3])
            score_table.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.5, _BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 0), (1, 0), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("BACKGROUND", (0, 0), (0, -1), _BG_ALT),
                ("BACKGROUND", (2, 0), (2, -1), _BG_ALT),
            ]))
            story.append(score_table)
            story.append(Spacer(1, 6))

            # Criteria table
            criteria_header = ["Nhóm tiêu chí", "Trọng số", "Điểm", "Nhận xét"]
            criteria_rows = [criteria_header]
            total_score = 0
            total_max = 100
            for cs in pe.get("criteriaScores", []):
                code = cs.get("criterionCode", "")
                name = _CRITERIA_LABELS.get(code, cs.get("criterionName", code))
                max_s = cs.get("maxScore", 0)
                s = cs.get("score", 0)
                total_score += s
                comment = cs.get("comment", "—")
                missing = cs.get("missingData", [])
                if missing:
                    comment += f" [Cần bổ sung: {', '.join(missing[:2])}]"
                criteria_rows.append([
                    f"{code}. {name}",
                    str(max_s),
                    str(s),
                    comment[:200],
                ])
            criteria_rows.append(["TỔNG", str(total_max), str(total_score), ""])

            col_w = [W * 0.37, W * 0.13, W * 0.09, W * 0.41]
            ct = Table(
                [[Paragraph(str(c), S["cell_bold"] if row_i in (0, len(criteria_rows)-1) else S["cell"])
                  for c in row] for row_i, row in enumerate(criteria_rows)],
                colWidths=col_w,
                splitByRow=False,
            )
            ct_style = _table_style(headers=True, alt_rows=False)
            for r in range(2, len(criteria_rows) - 1, 2):
                ct_style.add("BACKGROUND", (0, r), (-1, r), _BG_ALT)
            ct_style.add("BACKGROUND", (0, len(criteria_rows)-1), (-1, len(criteria_rows)-1), _BG_HEADER)
            ct_style.add("FONTNAME", (0, len(criteria_rows)-1), (-1, len(criteria_rows)-1), _FONT_BOLD)
            ct.setStyle(ct_style)
            story.append(ct)
            story.append(Spacer(1, 6))

            # Key points only
            reasons_against = pe.get("reasonsAgainstApproval") or []
            risks = pe.get("risks") or []
            next_actions = pe.get("nextActions") or []

            if reasons_against:
                story.append(Paragraph("<b>Điểm chưa đáp ứng:</b>", S["body"]))
                for r in reasons_against[:4]:
                    story.append(Paragraph(f"✗ {_fmt(r)}", S["indent"]))

            if risks:
                story.append(Paragraph("<b>Rủi ro:</b>", S["body"]))
                for r in risks[:3]:
                    story.append(Paragraph(f"⚠ {_fmt(r)}", S["indent"]))

            if next_actions:
                story.append(Paragraph("<b>Hành động tiếp theo:</b>", S["body"]))
                for a in next_actions[:3]:
                    story.append(Paragraph(f"→ {_fmt(a)}", S["indent"]))

            story.append(Spacer(1, 10))

    # ── Phần 4: Tóm tắt căn cứ từ tờ trình ───────────────────────────────────
    story.append(Spacer(1, 8))
    story.append(_section_block("PHẦN 4: TÓM TẮT CĂN CỨ TỪ TỜ TRÌNH", W, S))

    kpi_val = eval_context.get("kpiScore") or eval_context.get("kpiPercent")
    if kpi_val:
        story.append(Paragraph(f"<b>KPI / Kết quả đánh giá:</b> {kpi_val}", S["body"]))

    if work_results:
        story.append(Paragraph("<b>Kết quả công việc nổi bật:</b>", S["body"]))
        for wr in work_results[:5]:
            story.append(Paragraph(
                f"• {_fmt(wr.get('itemName'))}: {_fmt(wr.get('actualResult'))}",
                S["indent"]
            ))

    if basis_list:
        story.append(Paragraph("<b>Cơ sở đề xuất:</b>", S["body"]))
        for b in basis_list[:5]:
            story.append(Paragraph(
                f"• {_fmt(b.get('basisName'))}: {_fmt(b.get('detail'))}",
                S["indent"]
            ))

    if commitments:
        story.append(Paragraph("<b>Cam kết sau điều chỉnh:</b>", S["body"]))
        for c in commitments[:4]:
            story.append(Paragraph(f"• {_fmt(c)}", S["indent"]))

    if evaluation.get("overallSummary"):
        story.append(Paragraph(
            f"<b>Nhận định tổng quan:</b> {evaluation['overallSummary']}", S["body"]
        ))

    story.append(Spacer(1, 8))

    # Footer note
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width=W, thickness=0.5, color=_BORDER, spaceAfter=4))
    story.append(Paragraph(
        f"Ngày đánh giá: {report_data.get('evaluated_at', '—')}",
        S["footer"],
    ))

    doc.build(story, onFirstPage=_page_number_canvas, onLaterPages=_page_number_canvas)
    buf.seek(0)
    return buf
