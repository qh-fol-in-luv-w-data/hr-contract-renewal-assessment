"""
scan_phieu.py – Đọc phiếu đánh giá thử việc từ file scan (PDF/ảnh/HTML/DOCX)
Luồng đọc: OCR API (ctpai.vn) → GPT-4o Vision (chữ viết tay) → Docling text layer

Endpoints:
  POST /api/method/cnb_2as.api.scan_phieu.scan_extract   – Upload → trích xuất fields
  POST /api/method/cnb_2as.api.scan_phieu.scan_analyze   – Xác nhận → AI phân tích
"""
import base64, io, json, os, re, subprocess, sys, tempfile, uuid
from datetime import date
from pathlib import Path

import frappe

from cnb_2as.services.scan_service import (
    _get_client,
    _save_session,
    _load_session,
    _call_ocr_api,
    _pdf_to_images,
    _call_vision_ocr,
    _read_with_docling,
    _sanitize_markdown_tables,
    _read_html_text,
    _read_docx_text,
    _read_docx_structured,
    _merge_ocr_vision,
    _extract_text,
    _escape_xml,
    _build_xml_from_fields,
    _scan_extract_docx,
    _scan_extract_html,
    _scan_extract_pdf_image,
    _parse_xml_to_fields,
    _check_deadline,
)

from cnb_2as.services.prompts import (
    _MERGE_PROMPT,
    _EXTRACT_PROMPT,
    _ANALYZE_PROMPT,
    VISION_JSON_PROMPT,
    HOI_NHAP_PROMPT,
    KPI_PROMPT,
    SAN_PHAM_PROMPT,
)

from openai import OpenAI

# ── OpenAI client ──────────────────────────────────────────────────────────────
_client = None


# ── Session helpers ────────────────────────────────────────────────────────────
_NS = "cnb_scan_phieu"


# ══════════════════════════════════════════════════════════════════════════════
# TIER 1 – OCR API (app.ctpai.vn:8088)
# ══════════════════════════════════════════════════════════════════════════════
_OCR_API_URL = "http://app.ctpai.vn:8088/layout-parsing-file"


# ══════════════════════════════════════════════════════════════════════════════
# TIER 2 – GPT-4o Vision (đọc chữ in + chữ viết tay)
# ══════════════════════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════════════════════
# TIER 3 – Docling (text layer, không OCR/RapidOCR)
# ══════════════════════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════════════════════
# Sanitizer – dọn ô bảng quá dài
# ══════════════════════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════════════════════
# Các reader bổ sung (HTML, DOCX)
# ══════════════════════════════════════════════════════════════════════════════



# ══════════════════════════════════════════════════════════════════════════════
# MERGE – Kết hợp CTPAI skeleton + Vision handwriting
# ══════════════════════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR – chọn phương thức tốt nhất
# ══════════════════════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════════════════════
# AI Prompts
# ══════════════════════════════════════════════════════════════════════════════



# ══════════════════════════════════════════════════════════════════════════════
# XML Builder – Tạo XML từ extracted_fields
# ══════════════════════════════════════════════════════════════════════════════



# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 1 – scan_extract
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist(allow_guest=True)


def scan_extract():
    """
    POST /api/method/cnb_2as.api.scan_phieu.scan_extract
    Form-data: scan_file (PDF / DOCX / ảnh / HTML)

    Routes to appropriate branch by file extension:
    - .docx         → _scan_extract_docx  (5-section batch)
    - .html/.htm    → _scan_extract_html  (single call)
    - .pdf / images → _scan_extract_pdf_image (Vision + smart batching)
    """
    file_obj = frappe.request.files.get("scan_file")
    if not file_obj:
        frappe.throw("Thiếu file (field: scan_file)")

    filename = file_obj.filename
    file_bytes = file_obj.read()
    if not file_bytes:
        frappe.throw("File rỗng")

    # Loại đánh giá: 'thu_viec' (default) hoặc 'hoc_viec'
    eval_type = str(frappe.form_dict.get("eval_type") or "thu_viec")

    fname = filename.lower()
    client = _get_client()
    method_note = ""

    if fname.endswith(".docx"):
        method_note = "DOCX – batch extraction (5 section)"
        fields, raw_text = _scan_extract_docx(file_bytes, filename, client, eval_type)
    elif fname.endswith((".html", ".htm")):
        method_note = "HTML – đọc trực tiếp"
        fields, raw_text = _scan_extract_html(file_bytes, client, eval_type)
    elif fname.endswith((".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".webp")):
        method_note = "GPT-4o Vision → JSON trực tiếp"
        fields, raw_text = _scan_extract_pdf_image(file_bytes, filename, client, eval_type)
    else:
        frappe.throw(f"Định dạng file không hỗ trợ: {filename}")

    if not fields:
        frappe.throw("Không trích xuất được thông tin từ file. Vui lòng kiểm tra lại file.")

    has_handwriting = bool(fields.get("ghi_chu_viet_tay") or fields.get("hod_nhan_xet_chung"))
    deadline_info = _check_deadline(fields.get("ngay_het_han", ""))

    xml_output = _build_xml_from_fields(fields)

    sid = str(uuid.uuid4())
    _save_session(sid, {
        "filename": filename,
        "raw_text": raw_text,
        "raw_markdown": raw_text,
        "extracted_fields": fields,
        "method": method_note,
        "xml_output": xml_output,
        "eval_type": eval_type,
    })

    return {
        "scan_session_id": sid,
        "extracted_fields": fields,
        "ocr_note": method_note,
        "has_handwriting": has_handwriting,
        "raw_markdown": raw_text,
        "xml_output": xml_output,
        "eval_type": eval_type,
        **deadline_info,
    }



# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 2 – scan_analyze
# ══════════════════════════════════════════════════════════════════════════════


@frappe.whitelist(allow_guest=True)
def scan_analyze():
    """
    POST /api/method/cnb_2as.api.scan_phieu.scan_analyze
    Body JSON: { scan_session_id, xml_input? | edited_text? | confirmed_fields? }
    - xml_input: XML được người dùng sửa ở bước 2 (ưu tiên nhất, parse nhanh không cần AI)
    - edited_text: nội dung đã chỉnh sửa trong Word editor (AI re-extract)
    - confirmed_fields: JSON fields đã xác nhận (legacy)
    Returns: phân tích 6 tiêu chí + đề xuất
    """
    body = frappe.request.get_json(force=True) or {}
    sid = body.get("scan_session_id", "")
    xml_input   = body.get("xml_input", "")      # LUỒNG MỚI: user sửa XML
    edited_text = body.get("edited_text", "")
    confirmed = body.get("confirmed_fields", {})

    # Optional params – client có thể truyền hoặc lấy từ session đã lưu trước
    daily_report_text = body.get("daily_report_text", "")
    so_ngay_can_bc    = body.get("so_ngay_can_bc", "")
    ti_trong          = body.get("ti_trong", None)
    ngay_bd           = body.get("ngay_bd", "")
    ngay_kt           = body.get("ngay_kt", "")

    if not sid:
        frappe.throw("Thiếu scan_session_id")

    sess = _load_session(sid)
    client = _get_client()
    eval_type = sess.get("eval_type", "thu_viec")  # lấy từ session scan_extract

    # ── Ưu tiên: xml_input > edited_text > confirmed_fields > session ───────────
    if xml_input and xml_input.strip():
        # Người dùng đã sửa XML ở bước 2 → parse trực tiếp, không cần AI
        confirmed = _parse_xml_to_fields(xml_input)
        if not confirmed:
            # Nếu parse thất bại → fallback session
            confirmed = sess.get("extracted_fields", {})
    elif edited_text and edited_text.strip():
        # Người dùng sửa text markdown → re-extract bằng AI
        extract_prompt = _EXTRACT_PROMPT.replace("{loai_danh_gia}", "học việc" if eval_type == "hoc_viec" else "thử việc").replace("{loai_danh_gia_up}", "HỌC VIỆC" if eval_type == "hoc_viec" else "THỬ VIỆC").replace("{loai_danh_gia_cap}", "Học việc" if eval_type == "hoc_viec" else "Thử việc") + edited_text[:40000]
        try:
            er = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                messages=[{"role": "user", "content": extract_prompt}],
                temperature=0,
                max_tokens=2000,
                response_format={"type": "json_object"},
            )
            confirmed = json.loads(er.choices[0].message.content)
        except Exception:
            confirmed = sess.get("extracted_fields", {})
    elif not confirmed:
        confirmed = sess.get("extracted_fields", {})

    today_str = date.today().strftime("%d/%m/%Y")
    fields_json = json.dumps(confirmed, ensure_ascii=False, indent=2)

    # ── Build daily report section ──────────────────────────────────────────
    daily_report_section = ''
    if daily_report_text and daily_report_text.strip():
        so_ngay_label = f" (cần báo cáo: {so_ngay_can_bc} ngày)" if so_ngay_can_bc else ''
        daily_report_section = (
            f"\n══ BÁO CÁO NGÀY{so_ngay_label} ══\n"
            f"{daily_report_text[:8000]}\n\n"
            "Đánh giá số ngày đã báo cáo vs số ngày cần báo cáo.\n"
            "Nếu thiếu báo cáo ngày → thêm cảnh báo vào canh_bao.\n"
            "Bổ sung field \"bao_cao_ngay\" vào JSON kết quả: "
            '{"so_ngay_da_bc": N, "so_ngay_can_bc": M, "ty_le_bc": "N/M"}\n'
        )

    # ── Build tỉ trọng section ──────────────────────────────────────────────
    ti_trong_section = ''
    if ti_trong:
        ti_trong_section = (
            f"\n══ TỈ TRỌNG ĐÁNH GIÁ ══\n"
            f"{json.dumps(ti_trong, ensure_ascii=False)}\n"
            "Dùng tỉ trọng này để tính điểm tổng hợp (0-100).\n"
            "Bổ sung field \"diem_tong_hop\" vào JSON kết quả: "
            '{"kpi": N, "hoi_nhap": N, "san_pham": N, "bao_cao_ngay": N, "tong": N}\n'
        )

    _loai_label = "HỌC VIỆC" if eval_type == "hoc_viec" else "THỬ VIỆC"
    prompt = (f"Loại phiếu: ĐÁNH GIÁ {_loai_label}\n\n"
              + _ANALYZE_PROMPT
              .replace("{confirmed_fields_json}", fields_json)
              .replace("{today}", today_str)
              .replace("{daily_report_section}", daily_report_section).replace("{loai_danh_gia}", "học việc" if eval_type == "hoc_viec" else "thử việc").replace("{loai_danh_gia_up}", "HỌC VIỆC" if eval_type == "hoc_viec" else "THỬ VIỆC").replace("{loai_danh_gia_cap}", "Học việc" if eval_type == "hoc_viec" else "Thử việc")
              .replace("{ti_trong_section}", ti_trong_section))

    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=3500,
        response_format={"type": "json_object"},
    )

    try:
        result = json.loads(resp.choices[0].message.content)
    except json.JSONDecodeError:
        result = {
            "de_xuat": "CẦN BỔ SUNG", "mau_de_xuat": "amber",
            "tong_quan": "Không phân tích được",
            "phan_tich": [], "canh_bao": [], "uu_diem": [], "viec_can_lam": [],
            "alert_deadline": False, "so_ngay_con_lai": None,
        }

    deadline_info = _check_deadline(confirmed.get("ngay_het_han", ""))
    result.update(deadline_info)
    result["confirmed_fields"] = confirmed

    # Tạo XML từ confirmed fields (đã qua re-extract nếu có edited_text)
    xml_output = _build_xml_from_fields(confirmed)
    result["xml_output"] = xml_output

    # Lưu thêm context vào session
    sess["result"] = result
    sess["confirmed_fields"] = confirmed
    sess["xml_output"] = xml_output
    sess["ti_trong"] = ti_trong
    sess["ngay_bd"] = ngay_bd
    sess["ngay_kt"] = ngay_kt
    if daily_report_text:
        sess["daily_report_text"] = daily_report_text[:60000]
    if edited_text:
        sess["edited_text"] = edited_text[:60000]
    _save_session(sid, sess)

    result["eval_type"] = eval_type
    return result


# ── Deadline helper ────────────────────────────────────────────────────────────


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 3 – fill_docx
# Generate DOCX phiếu đánh giá thử việc từ confirmed_fields (không cần template)
# Scan theo đề mục, không hardcode row/table index
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist()
def fill_docx(scan_session_id: str):
    """
    Generate DOCX phiếu đánh giá từ confirmed_fields của session.
    Không dùng template file, generate toàn bộ nội dung theo đề mục.
    Trả về: { filename, content_b64, content_type, ho_ten, ma_nhan_su }
    """
    try:
        from docx import Document as _DocxDoc
        from docx.shared import Pt, Cm
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml.ns import qn
        from docx.oxml import OxmlElement
    except ImportError:
        frappe.throw("Thiếu thư viện python-docx. Cài: pip install python-docx")

    # ── Load session ──────────────────────────────────────────────────────────
    sess   = _load_session(scan_session_id)
    fields = sess.get("confirmed_fields") or sess.get("extracted_fields") or {}
    eval_type = sess.get("eval_type", "thu_viec")
    _loai = "học việc" if eval_type == "hoc_viec" else "thử việc"
    _loai_up = "HỌC VIỆC" if eval_type == "hoc_viec" else "THỬ VIỆC"
    _loai_cap = "Học việc" if eval_type == "hoc_viec" else "Thử việc"

    if not fields:
        frappe.throw("Session chưa có dữ liệu. Hãy scan_extract trước.")

    # ── Helpers ───────────────────────────────────────────────────────────────
    def f(key, default=""):
        """Lấy field an toàn, tránh None."""
        v = fields.get(key)
        if v is None: return default
        if isinstance(v, dict): return "\n".join(str(vv) for vv in v.values() if vv)
        return str(v).strip()

    def _add_borders(tbl_elem):
        """Thêm border single cho table."""
        tblPr = tbl_elem.find(qn('w:tblPr'))
        if tblPr is None:
            tblPr = OxmlElement('w:tblPr')
            tbl_elem.insert(0, tblPr)
        bdr = OxmlElement('w:tblBorders')
        for side in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
            el = OxmlElement(f'w:{side}')
            el.set(qn('w:val'), 'single')
            el.set(qn('w:sz'), '4')
            el.set(qn('w:space'), '0')
            el.set(qn('w:color'), '000000')
            bdr.append(el)
        tblPr.append(bdr)

    def _cell(cell, text, bold=False, size=9, center=False):
        """Điền text vào cell."""
        cell.text = ""
        p = cell.paragraphs[0]
        if center:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(str(text or ""))
        run.bold = bold
        run.font.size = Pt(size)

    def _new_table(doc, headers, widths_cm=None):
        """Tạo table với header row và borders."""
        t = doc.add_table(rows=1, cols=len(headers))
        t.style = 'Table Grid'
        _add_borders(t._tbl)
        hdr_row = t.rows[0]
        for i, hdr in enumerate(headers):
            _cell(hdr_row.cells[i], hdr, bold=True, size=9)
            if widths_cm and i < len(widths_cm):
                hdr_row.cells[i].width = Cm(widths_cm[i])
        return t

    def _add_data_row(table, *vals, bold_idxs=()):
        row = table.add_row()
        for i, val in enumerate(vals):
            if i < len(row.cells):
                _cell(row.cells[i], val, bold=(i in bold_idxs))
        return row

    # ── Khởi tạo Document A4 ─────────────────────────────────────────────────
    doc = _DocxDoc()
    sec = doc.sections[0]
    sec.page_width  = Cm(21)
    sec.page_height = Cm(29.7)
    sec.left_margin = sec.right_margin = Cm(1.5)
    sec.top_margin  = sec.bottom_margin = Cm(1.5)

    # ════════════════════════════════════════════════════════════════════════
    # TIÊU ĐỀ
    # ════════════════════════════════════════════════════════════════════════
    h = doc.add_heading(f"PHIẾU ĐÁNH GIÁ HOÀN THÀNH {_loai_up}", level=1)
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub = doc.add_paragraph("CT Group – Trung tâm Phát triển AI")
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # ════════════════════════════════════════════════════════════════════════
    # A. THÔNG TIN NHÂN VIÊN
    # ════════════════════════════════════════════════════════════════════════
    doc.add_heading("A. THÔNG TIN NHÂN VIÊN", level=2)
    t_info = _new_table(doc,
        ["Thông tin", "Nhân viên", "Thông tin", "Người quản lý (HOD)"],
        [4, 6, 4, 6])
    for lbl_nv, key_nv, lbl_hod, key_hod in [
        ("Họ và tên:",        "ho_ten",         "Họ và tên HOD:",  "ten_hod"),
        ("Mã nhân viên:",     "ma_nhan_su",      "Mã HOD:",         "ma_hod"),
        ("Chức danh:",        "chuc_danh",        "Chức danh HOD:",  "chuc_danh_hod"),
        ("Phòng ban:",        "phong_ban",        "",                ""),
        ("Ngày nhận việc:",   "ngay_nhan_viec",   "",                ""),
        (f"Hết hạn {_loai}:", "ngay_het_han",     "",                ""),
    ]:
        r = t_info.add_row()
        _cell(r.cells[0], lbl_nv, bold=True)
        _cell(r.cells[1], f(key_nv))
        _cell(r.cells[2], lbl_hod, bold=bool(lbl_hod))
        _cell(r.cells[3], f(key_hod) if key_hod else "")

    doc.add_paragraph("")

    # ════════════════════════════════════════════════════════════════════════
    # PHẦN I – NHẬN XÉT CHUNG
    # ════════════════════════════════════════════════════════════════════════
    doc.add_heading("PHẦN I - NHẬN XÉT CHUNG", level=2)
    nx_items = [
        ("1. Những việc làm tốt / thành tích nổi bật", "tu_danh_gia_lam_tot",   "nhan_xet_1_hod"),
        ("2. Kỹ năng và hoạt động cần cải thiện",       "tu_danh_gia_ky_nang",   "nhan_xet_2_hod"),
        ("3. Hoạt động hỗ trợ / kiến nghị",             "tu_danh_gia_hoat_dong", "nhan_xet_3_hod"),
        ("4. Những điểm cần cải thiện",                  "tu_danh_gia_can_cai",   "nhan_xet_4_hod"),
        ("5. Định hướng nâng cao năng lực",              "tu_danh_gia_nang_cao",  "nhan_xet_5_hod"),
    ]
    t_nx = _new_table(doc,
        ["Nội dung đánh giá", "Tự đánh giá (NV)", "Nhận xét HOD"],
        [5.5, 7, 7])
    for label, nv_key, hod_key in nx_items:
        r = t_nx.add_row()
        _cell(r.cells[0], label, bold=True)
        _cell(r.cells[1], f(nv_key))
        _cell(r.cells[2], f(hod_key))

    doc.add_paragraph("")

    # ════════════════════════════════════════════════════════════════════════
    # PHẦN II – KẾT QUẢ KPI
    # ════════════════════════════════════════════════════════════════════════
    doc.add_heading("PHẦN II - KẾT QUẢ KPI", level=2)

    # ─── 1.1 – 1.8: KPI Từng Tuần ────────────────────────────────────────
    doc.add_heading("1.1 - 1.8: KPI Từng Tuần", level=3)
    t_kpi = _new_table(doc,
        ["Tuần", "% KPI (NV)", "% KPI (HOD)", "Ghi chú"],
        [2, 6, 3, 8.5])
    for i in range(1, 9):
        nv_pct  = f(f"kpi_tuan_{i}_ty_le")
        hod_pct = f(f"hod_kpi_tuan_{i}")
        r = t_kpi.add_row()
        _cell(r.cells[0], f"Tuần {i}", bold=True)
        _cell(r.cells[1], nv_pct,  bold=bool(nv_pct))
        _cell(r.cells[2], hod_pct, bold=bool(hod_pct))
        _cell(r.cells[3], "")
    # Dòng TBC
    r_tbc = t_kpi.add_row()
    _cell(r_tbc.cells[0], "Điểm TBC KPI", bold=True)
    _cell(r_tbc.cells[1], f("diem_tbc_kpi_nv"), bold=True)
    _cell(r_tbc.cells[2], f("diem_tbc_kpi_hod"), bold=True)
    _cell(r_tbc.cells[3], "")

    doc.add_paragraph("")

    # ─── 1.10: NHIỆM VỤ ĐƯỢC GIAO VÀ KẾT QUẢ THỰC TẾ ───────────────────
    doc.add_heading("1.10 - Nhiệm vụ được giao và Kết quả thực tế", level=3)

    cong_viec = f("cong_viec_duoc_giao")
    tong_tl   = f("ty_le_hoan_thanh_16")
    if cong_viec:
        doc.add_paragraph(f"Công việc được giao:\n{cong_viec}")
    if tong_tl:
        doc.add_paragraph(f"Tỷ lệ hoàn thành tổng 1.6: {tong_tl}")

    t_nv = _new_table(doc,
        ["STT", "Nội dung nhiệm vụ", "Kết quả đạt được", "% Hoàn thành", "Nhận xét HOD"],
        [1.5, 6.5, 5, 2.5, 4])
    found_nv = False
    for i in range(1, 9):
        noi_dung = f(f"nhiem_vu_{i}_noi_dung")
        ket_qua  = f(f"nhiem_vu_{i}_ket_qua")
        ty_le    = f(f"nhiem_vu_{i}_ty_le")
        hod_nx   = f(f"nhiem_vu_{i}_hod")
        if noi_dung or ty_le:
            found_nv = True
            r = t_nv.add_row()
            _cell(r.cells[0], f"NV {i}", bold=True)
            _cell(r.cells[1], noi_dung)
            _cell(r.cells[2], ket_qua)
            _cell(r.cells[3], ty_le, bold=bool(ty_le))
            _cell(r.cells[4], hod_nx)
    if not found_nv:
        r = t_nv.add_row()
        _cell(r.cells[0], "(Chưa có dữ liệu nhiệm vụ)")

    doc.add_paragraph("")

    # ─── 2.1 – 2.8: SẢN PHẨM NGHIỆM THU ────────────────────────────────
    doc.add_heading("2. Sản phẩm nghiệm thu từng tuần", level=3)
    t_sp = _new_table(doc,
        ["Đề mục", "Sản phẩm / Nhiệm vụ", "Số file", "Link", "Vi phạm", "% KPI"],
        [2, 5.5, 1.5, 4.5, 2, 2])
    found_sp = False
    for i in range(1, 9):
        sp      = f(f"san_pham_{i}")
        nt      = f(f"nhiem_vu_tuan_{i}")
        so_file = f(f"so_luong_file_{i}")
        link    = f(f"link_dinh_kem_{i}")
        vi_ph   = f(f"vi_pham_upload_{i}")
        kpi_sp  = f(f"kpi_sp_tuan_{i}")
        if sp or nt or kpi_sp:
            found_sp = True
            sp_text = sp
            if nt and nt != sp:
                sp_text = f"{sp}\nNhiệm vụ: {nt}" if sp else nt
            r = t_sp.add_row()
            _cell(r.cells[0], f"2.{i} - T {i}", bold=True)
            _cell(r.cells[1], sp_text)
            _cell(r.cells[2], so_file, center=True)
            _cell(r.cells[3], link)
            _cell(r.cells[4], vi_ph)
            _cell(r.cells[5], kpi_sp, bold=bool(kpi_sp), center=True)
    if not found_sp:
        r = t_sp.add_row()
        _cell(r.cells[0], "(Chưa có dữ liệu sản phẩm)")

    doc.add_paragraph("")

    # ════════════════════════════════════════════════════════════════════════
    # PHẦN III – HỘI NHẬP
    # ════════════════════════════════════════════════════════════════════════
    doc.add_heading("PHẦN III - HỘI NHẬP", level=2)
    hn_labels = [
        "7.1. Sứ mệnh Tập đoàn",
        "7.1. Sứ mệnh bản thân",
        "7.2. Tầm nhìn Tập đoàn",
        "7.2. Tầm nhìn bản thân",
        "7.3. Văn hóa cốt lõi Tập đoàn",
        "7.3. Giá trị cốt lõi bản thân",
        "7.4. Phù hợp văn hóa làm việc",
        "7.5. Văn hóa kinh doanh",
        "7.6. Đóng góp khác trong giai đoạn hội nhập",
    ]
    t_hn = _new_table(doc,
        ["Nội dung", "NV tự đánh giá", "Nhận xét HOD"],
        [5, 7, 7.5])
    for i, label in enumerate(hn_labels, 1):
        nv  = f(f"hoi_nhap_{i}_nv")
        hod = f(f"hoi_nhap_{i}_hod")
        r = t_hn.add_row()
        _cell(r.cells[0], label, bold=True)
        _cell(r.cells[1], nv)
        _cell(r.cells[2], hod)

    doc.add_paragraph("")

    # ════════════════════════════════════════════════════════════════════════
    # KẾT LUẬN
    # ════════════════════════════════════════════════════════════════════════
    doc.add_heading("KẾT LUẬN", level=2)
    t_kl = _new_table(doc, ["Mục", "Nội dung"], [4, 15.5])
    for muc, val in [
        ("Kết quả đánh giá:", f("ket_luan")),
        ("Đề xuất của NV:",   f("de_xuat_nv")),
        ("Đề xuất của HOD:",  f("de_xuat_hod")),
    ]:
        r = t_kl.add_row()
        _cell(r.cells[0], muc, bold=True)
        _cell(r.cells[1], val)

    doc.add_paragraph("")

    # Chữ ký
    t_sign = _new_table(doc, ["Nhân viên ký xác nhận", "Người quản lý (HOD)"])
    r_sp2 = t_sign.add_row()
    _cell(r_sp2.cells[0], "\n\n\n\n")
    _cell(r_sp2.cells[1], "\n\n\n\n")
    r_nm = t_sign.add_row()
    _cell(r_nm.cells[0], f("ho_ten"),   center=True)
    _cell(r_nm.cells[1], f("ten_hod"),  center=True)

    # ── Xuất bytes base64 ────────────────────────────────────────────────────
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    content_b64 = base64.b64encode(buf.read()).decode()

    ho_ten   = f("ho_ten", "NhanVien").replace(" ", "_")
    filename = f"PhieuDanhGia_{_loai_cap}_{ho_ten}.docx"

    return {
        "filename":     filename,
        "content_b64":  content_b64,
        "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "ho_ten":       f("ho_ten"),
        "ma_nhan_su":   f("ma_nhan_su"),
    }



# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 4 – download_pdf
# Tạo PDF báo cáo phân tích scan phiếu đánh giá thử việc
# bao gồm 7 tiêu chí đánh giá 2AS và đề xuất xử lý
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist(allow_guest=True)
def download_pdf():
    """
    POST /api/method/cnb_2as.api.scan_phieu.download_pdf
    Body JSON: { scan_session_id, analyze_result? }
    - scan_session_id: session ID từ scan_extract
    - analyze_result: (optional) kết quả scan_analyze để dùng trực tiếp

    Trả về: PDF bytes (application/pdf)
    Yêu cầu: session đã qua scan_analyze (có result lưu trong session).
    """
    from cnb_2as.services.pdf_generator import generate_thu_viec_pdf

    body = frappe.request.get_json(force=True) or {}
    sid = body.get("scan_session_id", "")
    analyze_result_input = body.get("analyze_result")

    if not sid and not analyze_result_input:
        frappe.throw("Thiếu scan_session_id hoặc analyze_result")

    # ── Lấy dữ liệu session ──────────────────────────────────────────────────
    if sid:
        sess = _load_session(sid)
        analyze_result = sess.get("result") or analyze_result_input or {}
        confirmed_fields = sess.get("confirmed_fields") or sess.get("extracted_fields") or {}
    else:
        analyze_result = analyze_result_input or {}
        confirmed_fields = {}

    if not analyze_result and not confirmed_fields:
        frappe.throw("Session chưa có kết quả phân tích. Hãy chạy scan_analyze trước.")

    # ── Xây dựng eval_data cho pdf_generator ─────────────────────────────────
    # Lấy phan_tich (7 tiêu chí) và de_xuat_xu_ly từ analyze_result
    phan_tich_2as = analyze_result.get("phan_tich") or []
    # Chuẩn hóa format phan_tich sang schema pdf_generator (ma, tieu_chi, nhan_xet, ket_qua)
    phan_tich_normalized = []
    for i, tc in enumerate(phan_tich_2as):
        phan_tich_normalized.append({
            "ma":       tc.get("ma") or f"TC{i+1}",
            "tieu_chi": tc.get("tieu_chi") or tc.get("ten") or "",
            "nhan_xet": tc.get("nhan_xet") or tc.get("mo_ta") or "",
            "ket_qua":  tc.get("danh_gia") or tc.get("ket_qua") or "",
        })

    de_xuat_xu_ly = {}
    de_xuat_raw = analyze_result.get("de_xuat") or ""
    if de_xuat_raw:
        de_xuat_xu_ly = {
            "ket_qua_tv": de_xuat_raw,
            "muc_do": analyze_result.get("mau_de_xuat") or "",
            "ly_do": analyze_result.get("tong_quan") or "",
            "diem_manh": analyze_result.get("uu_diem") or [],
            "diem_can_cai_thien": [
                c.get("noi_dung","") for c in (analyze_result.get("viec_can_lam") or [])
            ] if analyze_result.get("viec_can_lam") else [],
        }

    # Thông tin nhân viên từ confirmed_fields
    thong_tin_nv = {
        "ten_nhan_vien": confirmed_fields.get("ho_ten", ""),
        "ma_nhan_vien":  confirmed_fields.get("ma_nhan_su", ""),
        "chuc_danh":     confirmed_fields.get("chuc_danh", ""),
        "don_vi":        confirmed_fields.get("phong_ban", ""),
        "ngay_nhan_viec": confirmed_fields.get("ngay_nhan_viec", ""),
        "ngay_het_han":  confirmed_fields.get("ngay_het_han", ""),
        "ten_hod":       confirmed_fields.get("ten_hod", ""),
    }

    # Cảnh báo từ analyze_result
    canh_bao_2as = analyze_result.get("canh_bao") or []

    # Việc cần làm
    viec_can_lam = []
    for item in (analyze_result.get("viec_can_lam") or []):
        viec_can_lam.append({
            "title":   item.get("noi_dung") or item.get("title") or "",
            "mo_ta":   "",
            "urgent":  str(item.get("uu_tien","")).lower() in ("cao","high","urgent"),
            "done":    False,
        })

    eval_data = {
        "status":              ("ĐẠT" if (de_xuat_raw or "").upper().startswith("ĐỒNG Ý") else "CHƯA ĐẠT – CẦN BỔ SUNG"),
        "tong_quan":           analyze_result.get("tong_quan", ""),
        "thong_tin_nhan_vien": thong_tin_nv,
        "van_de":              [],
        "uu_diem":             analyze_result.get("uu_diem", []),
        "phan_tich_2as":       phan_tich_normalized,
        "canh_bao_2as":        canh_bao_2as,
        "de_xuat_xu_ly":       de_xuat_xu_ly,
        "viec_can_lam":        viec_can_lam,
        "xlsx_kpi":            [],
        "danh_gia_quan_ly":    analyze_result.get("danh_gia_quan_ly", {}),
        "from_scan":           True,
    }

    # ── Generate PDF ──────────────────────────────────────────────────────────
    eval_data["eval_type"] = sess.get("eval_type", "thu_viec")
    buffer = generate_thu_viec_pdf(eval_data)

    ho_ten = (confirmed_fields.get("ho_ten") or "NhanVien").replace(" ", "_")
    filename = f"BaoCao_ScanPhieu_{ho_ten}.pdf"

    frappe.response.filename = filename
    frappe.response.filecontent = buffer.getvalue()
    filename = f"BaoCao_ScanPhieu_{ho_ten}.pdf"

    frappe.response.filename = filename
    frappe.response.filecontent = buffer.getvalue()
    frappe.response.type = "pdf"
