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

    fname = filename.lower()
    client = _get_client()
    method_note = ""

    if fname.endswith(".docx"):
        method_note = "DOCX – batch extraction (5 section)"
        fields, raw_text = _scan_extract_docx(file_bytes, filename, client)
    elif fname.endswith((".html", ".htm")):
        method_note = "HTML – đọc trực tiếp"
        fields, raw_text = _scan_extract_html(file_bytes, client)
    elif fname.endswith((".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".webp")):
        method_note = "GPT-4o Vision → JSON trực tiếp"
        fields, raw_text = _scan_extract_pdf_image(file_bytes, filename, client)
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
    })

    return {
        "scan_session_id": sid,
        "extracted_fields": fields,
        "ocr_note": method_note,
        "has_handwriting": has_handwriting,
        "raw_markdown": raw_text,
        "xml_output": xml_output,
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
    - xml_input: XML \u0111\u01b0\u1ee3c ng\u01b0\u1eddi d\u00f9ng s\u1eeda \u1edf b\u01b0\u1edbc 2 (uu ti\u00ean nh\u1ea5t, parse nhanh kh\u00f4ng c\u1ea7n AI)
    - edited_text: n\u1ed9i dung \u0111\u00e3 ch\u1ec9nh s\u1eeda trong Word editor (AI re-extract)
    - confirmed_fields: JSON fields \u0111\u00e3 x\u00e1c nh\u1eadn (legacy)
    Returns: ph\u00e2n t\u00edch 6 ti\u00eau ch\u00ed + \u0111\u1ec1 xu\u1ea5t
    """
    body = frappe.request.get_json(force=True) or {}
    sid = body.get("scan_session_id", "")
    xml_input   = body.get("xml_input", "")      # LUỒNG MỚI: user sửa XML
    edited_text = body.get("edited_text", "")
    confirmed = body.get("confirmed_fields", {})

    if not sid:
        frappe.throw("Thiếu scan_session_id")

    sess = _load_session(sid)
    client = _get_client()

    # ── Ưu tiên: xml_input > edited_text > confirmed_fields > session ───────────
    if xml_input and xml_input.strip():
        # Người dùng đã sửa XML ở bước 2 → parse trực tiếp, không cần AI
        confirmed = _parse_xml_to_fields(xml_input)
        if not confirmed:
            # Nếu parse thất bại → fallback session
            confirmed = sess.get("extracted_fields", {})
    elif edited_text and edited_text.strip():
        # Người dùng sửa text markdown → re-extract bằng AI
        extract_prompt = _EXTRACT_PROMPT + edited_text[:40000]
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
    prompt = (_ANALYZE_PROMPT
              .replace("{confirmed_fields_json}", fields_json)
              .replace("{today}", today_str))

    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=2500,
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

    # Lưu lại session
    sess["result"] = result
    sess["confirmed_fields"] = confirmed
    sess["xml_output"] = xml_output
    if edited_text:
        sess["edited_text"] = edited_text[:60000]
    _save_session(sid, sess)

    return result


# ── Deadline helper ────────────────────────────────────────────────────────────


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 3 – fill_docx
# Generate DOCX phiếu đánh giá thử việc từ confirmed_fields (không cần template)
# Scan theo đề mục, không hardcode row/table index
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist(allow_guest=True)
def fill_docx(scan_session_id: str):
    """
    Generate DOCX phiếu đánh giá thử việc từ confirmed_fields của session.
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
    h = doc.add_heading("PHIẾU ĐÁNH GIÁ HOÀN THÀNH THỬ VIỆC", level=1)
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub = doc.add_paragraph("CT Group – Trung tâm Phát triển AI")
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # ════════════════════════════════════════════════════════════════════════
    # A. THÔNG TIN NHÂN VIÊN
    # Scan theo field name (không hardcode row index)
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
        ("Hết hạn thử việc:", "ngay_het_han",     "",                ""),
    ]:
        r = t_info.add_row()
        _cell(r.cells[0], lbl_nv, bold=True)
        _cell(r.cells[1], f(key_nv))
        _cell(r.cells[2], lbl_hod, bold=bool(lbl_hod))
        _cell(r.cells[3], f(key_hod) if key_hod else "")

    doc.add_paragraph("")

    # ════════════════════════════════════════════════════════════════════════
    # PHẦN I – NHẬN XÉT CHUNG
    # Scan các field nhan_xet_{i} theo thứ tự đề mục 1-5
    # ════════════════════════════════════════════════════════════════════════
    doc.add_heading("PHAN I - NHAN XET CHUNG", level=2)
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
    doc.add_heading("PHAN II - KET QUA KPI", level=2)

    # ─── 1.1 – 1.8: KPI Từng Tuần ────────────────────────────────────────
    # Scan theo đề mục: kpi_tuan_{i}_ty_le (KHÔNG hardcode row index)
    doc.add_heading("1.1 - 1.8: KPI Tung Tuan", level=3)
    t_kpi = _new_table(doc,
        ["Tuan", "% KPI (NV tu danh gia)", "% KPI (HOD)", "Ghi chu"],
        [2, 6, 3, 8.5])
    for i in range(1, 9):
        nv_pct  = f(f"kpi_tuan_{i}_ty_le")
        hod_pct = f(f"hod_kpi_tuan_{i}")
        r = t_kpi.add_row()
        _cell(r.cells[0], f"Tuan {i}", bold=True)
        _cell(r.cells[1], nv_pct,  bold=bool(nv_pct))
        _cell(r.cells[2], hod_pct, bold=bool(hod_pct))
        _cell(r.cells[3], "")
    # Dòng TBC
    r_tbc = t_kpi.add_row()
    _cell(r_tbc.cells[0], "Diem TBC KPI", bold=True)
    _cell(r_tbc.cells[1], f("diem_tbc_kpi_nv"), bold=True)
    _cell(r_tbc.cells[2], f("diem_tbc_kpi_hod"), bold=True)
    _cell(r_tbc.cells[3], "")

    doc.add_paragraph("")

    # ─── 1.10: NHIỆM VỤ ĐƯỢC GIAO VÀ KẾT QUẢ THỰC TẾ ───────────────────
    # Scan theo đề mục nhiem_vu_{i} — dynamic rows, không hardcode số hàng
    doc.add_heading("1.10 - Nhiem Vu Duoc Giao va Ket Qua Thuc Te", level=3)

    cong_viec = f("cong_viec_duoc_giao")
    tong_tl   = f("ty_le_hoan_thanh_16")
    if cong_viec:
        doc.add_paragraph(f"Cong viec duoc giao:\n{cong_viec}")
    if tong_tl:
        doc.add_paragraph(f"Ty le hoan thanh tong 1.6: {tong_tl}")

    # Bảng nhiệm vụ — dynamic số hàng theo dữ liệu thực tế
    t_nv = _new_table(doc,
        ["STT", "Noi dung nhiem vu", "Ket qua dat duoc", "% Hoan thanh", "Nhan xet HOD"],
        [1.5, 6.5, 5, 2.5, 4])
    found_nv = False
    for i in range(1, 9):
        # Scan theo tên field đề mục nhiem_vu_X — không cần biết ở trang nào
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
        _cell(r.cells[0], "(Chua co du lieu nhiem vu)")

    doc.add_paragraph("")

    # ─── 2.1 – 2.8: SẢN PHẨM NGHIỆM THU ────────────────────────────────
    # Scan theo đề mục san_pham_{i} và link_dinh_kem_{i}
    # Dynamic: chỉ render tuần có dữ liệu
    doc.add_heading("2. San Pham Nghiem Thu Tung Tuan", level=3)
    t_sp = _new_table(doc,
        ["De muc", "San pham / Nhiem vu dat ra", "So file", "Link dinh kem", "Vi pham", "% KPI"],
        [2, 5.5, 1.5, 4.5, 2, 2])
    found_sp = False
    for i in range(1, 9):
        # Scan field theo tên đề mục — không hardcode trang/row
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
                sp_text = f"{sp}\nNhiem vu: {nt}" if sp else nt
            r = t_sp.add_row()
            _cell(r.cells[0], f"2.{i} - Tuan {i}", bold=True)
            _cell(r.cells[1], sp_text)
            _cell(r.cells[2], so_file, center=True)
            _cell(r.cells[3], link)
            _cell(r.cells[4], vi_ph)
            _cell(r.cells[5], kpi_sp, bold=bool(kpi_sp), center=True)
    if not found_sp:
        r = t_sp.add_row()
        _cell(r.cells[0], "(Chua co du lieu san pham)")

    doc.add_paragraph("")

    # ════════════════════════════════════════════════════════════════════════
    # PHẦN III – HỘI NHẬP
    # Scan theo đề mục hoi_nhap_{i}_nv / _hod — không hardcode row index
    # ════════════════════════════════════════════════════════════════════════
    doc.add_heading("PHAN III - HOI NHAP", level=2)
    hn_labels = [
        "7.1. Su menh Tap doan",
        "7.1. Su menh ban than",
        "7.2. Tam nhin Tap doan",
        "7.2. Tam nhin ban than",
        "7.3. Van hoa cot loi Tap doan",
        "7.3. Gia tri cot loi ban than",
        "7.4. Phu hop van hoa lam viec",
        "7.5. Van hoa kinh doanh",
        "7.6. Dong gop khac trong giai doan hoi nhap",
    ]
    t_hn = _new_table(doc,
        ["Noi dung", "NV tu danh gia", "Nhan xet HOD"],
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
    doc.add_heading("KET LUAN", level=2)
    t_kl = _new_table(doc, ["Muc", "Noi dung"], [4, 15.5])
    for muc, val in [
        ("Ket qua danh gia:", f("ket_luan")),
        ("De xuat cua NV:",   f("de_xuat_nv")),
        ("De xuat cua HOD:",  f("de_xuat_hod")),
    ]:
        r = t_kl.add_row()
        _cell(r.cells[0], muc, bold=True)
        _cell(r.cells[1], val)

    doc.add_paragraph("")

    # Chữ ký
    t_sign = _new_table(doc, ["Nhan vien ky xac nhan", "Nguoi quan ly (HOD)"])
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
    filename = f"PhieuDanhGiaThuViec_{ho_ten}.docx"

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
        "from_scan":           True,
    }

    # ── Generate PDF ──────────────────────────────────────────────────────────
    buffer = generate_thu_viec_pdf(eval_data)

    ho_ten = (confirmed_fields.get("ho_ten") or "NhanVien").replace(" ", "_")
    filename = f"BaoCao_ScanPhieu_{ho_ten}.pdf"

    frappe.response.filename = filename
    frappe.response.filecontent = buffer.getvalue()
    frappe.response.type = "pdf"

    filename = f"BaoCao_ScanPhieu_{ho_ten}.pdf"

    frappe.response.filename = filename
    frappe.response.filecontent = buffer.getvalue()
    frappe.response.type = "pdf"
