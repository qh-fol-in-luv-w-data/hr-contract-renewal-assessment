"""
ATS Đánh Giá Thử Việc – API
Endpoints:
  POST /api/method/cnb_2as.api.thu_viec.review_files   – Upload DOCX + XLSX → AI review
  POST /api/method/cnb_2as.api.thu_viec.chat_review    – Chat follow-up trong cùng session
"""
import difflib, io, json, os, uuid
from pathlib import Path

from docx import Document as DocxDocument
import openpyxl
from pypdf import PdfReader
from openai import OpenAI

from dotenv import load_dotenv

# ── Load env từ nhiều vị trí có thể ──────────────────────────────────────────
_THIS_FILE = Path(__file__).resolve()
# subpackage dir: .../apps/ats_danhgiathuviec/ats_danhgiathuviec/
_SUB_DIR = _THIS_FILE.parent
# app root dir: .../apps/ats_danhgiathuviec/
_APP_ROOT = _SUB_DIR.parent
# bench root: .../frappe-bench/
_BENCH_ROOT = _APP_ROOT.parent.parent

# Thứ tự ưu tiên: subpackage → app root → bench root → ai_ats (fallback)
for _env_path in [
    _SUB_DIR / ".env",
    _APP_ROOT / ".env",
    _BENCH_ROOT / "apps" / "ai_ats" / "ai_ats" / ".env",
    _BENCH_ROOT / "apps" / "ai_ats" / ".env",
]:
    if _env_path.exists():
        load_dotenv(_env_path, override=False)

# ── Frappe (import sau dotenv để key đã sẵn) ──────────────────────────────────
import frappe

from cnb_2as.services.thu_viec_service import (
    _RECHECK_PROMPT_TPL,
    _get_client,
    _log_tokens,
    _compute_canh_bao_han_real,
    _ensure_viec_can_lam,
    _compute_text_diff,
    _compute_kpi_diff,
    _compute_weekly_diff,
    _extract_sections,
    _parse_pdf_for_docx,
    _parse_pdf_for_xlsx,
    _parse_docx,
    _extract_nhanvien_from_docx,
    _parse_xlsx,
    _extract_nhanvien_from_xlsx,
    _check_e1_deterministic,
    _filter_result,
    _filter_recheck_issues,
    _get_session,
    _save_session,
    _build_kpi_summary,
    _build_review_prompt,
)

from cnb_2as.services.prompts import (
    _SYSTEM_PROMPT,
    _CHAT_SYSTEM,
)


# ── OpenAI client ─────────────────────────────────────────────────────────────
_client: OpenAI | None = None


# ══════════════════════════════════════════════════════════════════════════════
# Deadline helpers – tính server-side vì LLM không biết ngày hôm nay
# ══════════════════════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════════════════════
# Diff helpers – so sánh file cũ và mới để AI recheck chính xác hơn
# ══════════════════════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════════════════════
# File parsers
# ══════════════════════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════════════════════
# System prompt
# ══════════════════════════════════════════════════════════════════════════════








# ══════════════════════════════════════════════════════════════════════════════
# Session store – dùng Frappe cache (Redis) để chia sẻ giữa các worker process
# ══════════════════════════════════════════════════════════════════════════════

_SESSION_TTL = 86400  # 24 giờ
_SESSION_PREFIX = "ats_session:"





# ══════════════════════════════════════════════════════════════════════════════
# Endpoint 1b: review_from_scan  (nhận text từ ScanCombined, không cần file)
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist(allow_guest=True)
def review_from_scan():
    """
    POST application/json:
      - ef: dict — phiếu editable fields từ ScanCombined
      - months: list — SXKD months data từ ScanCombined
      - shared: dict — SXKD shared section (noi_quy, chi_dao, xet_duyet)
      - cv_list: list — danh sách % hoàn thành 1.6
    Trả về cùng schema với review_files.
    """
    import uuid
    body = frappe.form_dict or {}
    if frappe.request and frappe.request.data:
        try:
            body = json.loads(frappe.request.data)
        except Exception:
            pass

    ef = body.get("ef") or {}
    months = body.get("months") or []
    shared = body.get("shared") or {}
    cv_list = body.get("cv_list") or []

    # ── Serialize phiếu → word_raw text ──────────────────────────────────────
    def _yn(v): return "Có" if str(v).strip() else "(trống)"

    lines_word = ["=== PHIẾU ĐÁNH GIÁ HOÀN THÀNH THỬ VIỆC (từ Scan OCR) ===\n"]

    # Thông tin nhân viên
    lines_word.append("I. THÔNG TIN NHÂN VIÊN")
    lines_word.append(f"Họ và tên: {ef.get('ho_ten','')}")
    lines_word.append(f"Mã NV: {ef.get('ma_nhan_su','')}")
    lines_word.append(f"Chức danh: {ef.get('chuc_danh','')}")
    lines_word.append(f"Đơn vị: {ef.get('phong_ban','')}")
    lines_word.append(f"Ngày nhận việc: {ef.get('ngay_nhan_viec','')}")
    lines_word.append(f"Ngày hết hạn thử việc: {ef.get('ngay_het_han','')}")
    lines_word.append(f"HOD: {ef.get('ten_hod','')} – {ef.get('chuc_danh_hod','')}")
    lines_word.append("")

    # Nhận xét 1-5
    lines_word.append("II. NHẬN XÉT ĐÁNH GIÁ")
    for i in range(1, 6):
        nv = ef.get(f"nhan_xet_{i}_nv", "")
        hod = ef.get(f"nhan_xet_{i}_hod", "")
        if nv or hod:
            lines_word.append(f"  Câu {i} – NV: {nv}")
            lines_word.append(f"  Câu {i} – HOD: {hod}")
    lines_word.append("")

    # KPI tuần (1.1-1.8)
    lines_word.append("III. KẾT QUẢ KPI TỪNG TUẦN (1.1–1.8)")
    for t in range(1, 9):
        ty_le = ef.get(f"kpi_tuan_{t}_ty_le", "")
        if ty_le:
            lines_word.append(f"  Tuần {t}: {ty_le}")
    lines_word.append(f"  Điểm TBC KPI (NV): {ef.get('diem_tbc_kpi_nv','')}")
    lines_word.append(f"  Điểm TBC KPI (HOD): {ef.get('diem_tbc_kpi_hod','')}")
    lines_word.append("")

    # Công việc được giao (1.10)
    lines_word.append("IV. NHIỆM VỤ VÀ KẾT QUẢ THỰC TẾ (1.10)")
    lines_word.append(ef.get("cong_viec_duoc_giao", ""))
    lines_word.append(f"  Tỷ lệ hoàn thành tổng: {ef.get('ty_le_hoan_thanh_16','')}")
    for idx, cv in enumerate(cv_list):
        if cv.get("ty_le"):
            lines_word.append(f"  Nhiệm vụ {idx+1}: {cv.get('ty_le','')}")
    lines_word.append("")

    # Kế hoạch từng tuần (2.1-2.8)
    lines_word.append("V. KẾ HOẠCH TỪNG TUẦN (2.1–2.8)")
    for t in range(1, 9):
        sp = ef.get(f"san_pham_{t}", "")
        ldk = ef.get(f"link_dinh_kem_{t}", "")
        kpi = ef.get(f"kpi_sp_tuan_{t}", "")
        if sp or ldk:
            lines_word.append(f"  Tuần {t}:")
            lines_word.append(f"    - Sản phẩm đặt ra: {sp or '(trống)'}")
            lines_word.append(f"    - Nhiệm vụ đặt ra: {sp or '(trống)'}")
            lines_word.append(f"    - Link đính kèm: {ldk or '(trống)'}")
            lines_word.append(f"    - % KPI: {kpi or '(trống)'}")
    lines_word.append("")

    # Hội nhập
    lines_word.append("VI. HỘI NHẬP")
    for i in range(1, 10):
        nv = ef.get(f"hoi_nhap_{i}_nv", "")
        hod = ef.get(f"hoi_nhap_{i}_hod", "")
        if nv or hod:
            lines_word.append(f"  {i} – NV: {nv}  |  HOD: {hod}")
    lines_word.append("")
    # Kết luận
    lines_word.append("VII. KẾT LUẬN & ĐỀ XUẤT")
    lines_word.append(f"  Kết luận: {ef.get('ket_luan','')}")
    lines_word.append(f"  Đề xuất ký HĐ: {ef.get('de_xuat_ky_hd','')}")
    lines_word.append(f"  Ý kiến HOD: {ef.get('y_kien_hod','')}")
    lines_word.append(f"  Ý kiến RTD: {ef.get('y_kien_rtd','')}")

    word_raw = "\n".join(lines_word)

    # ── Serialize SXKD → excel_raw text + kpi_rows structure ─────────────────
    kpi_rows = []
    stt = 1
    lines_xl = ["=== KẾ HOẠCH SXKD (từ Scan OCR) ===\n"]

    for mi, month in enumerate(months):
        ten_thang = month.get("tieu_de") or month.get("ten_thang", f"Tháng {mi+1}")
        lines_xl.append(f"\n--- {ten_thang} ---")
        for cv in (month.get("cong_viec") or []):
            mo_ta   = cv.get("mo_ta_san_pham", "") or cv.get("mo_ta","")
            link    = cv.get("link_san_pham","") or cv.get("link","")
            mang    = cv.get("mang_cong_tac","") or cv.get("cong_viec","") or cv.get("ten","") or cv.get("mang","")
            ty_trong_raw = cv.get("ty_trong","") or ""
            kpi_raw      = cv.get("kpi_ke_hoach","") or ""
            ty_le_raw    = cv.get("ty_le_kpi_ket_qua","") or cv.get("ty_le","") or cv.get("ty_le_thuc_hien","")
            ket_qua_raw  = cv.get("ket_qua_kpi","") or cv.get("ket_qua","")
            try:
                ty_le_f = float(str(ty_le_raw).replace("%","").strip()) / 100
            except Exception:
                ty_le_f = None
            lines_xl.append(
                f"  STT {stt} [{mang}]: {mo_ta[:80]}"
                f" | TỶ TRỌNG: {ty_trong_raw}"
                f" | KPI KH: {kpi_raw}"
                f" | TỶ LỆ TH: {ty_le_raw}"
                f" | KQ KPI: {ket_qua_raw}"
                f" | Link: {link[:60] or '(trống)'}"
            )
            kpi_rows.append({
                "stt": stt,
                "cong_viec": mang,
                "mo_ta": mo_ta,
                "ty_trong": ty_trong_raw,
                "kpi": kpi_raw,
                "ty_le_thuc_hien": ty_le_f,
                "ket_qua_kpi": ket_qua_raw,
                "minh_chung": link,
                "has_image": bool(link.strip()),
                "link_minh_chung": link,
                "status": "OK" if link.strip() else "THIẾU",
                "issues": [] if link.strip() else ["Thiếu minh chứng"],
            })
            stt += 1

    excel_raw = "\n".join(lines_xl)

    # Shared nội quy / chỉ đạo
    noi_quy_text = "\n".join(
        f"  NQ{r.get('stt','')}: {r.get('ten_hanh_vi','')} – Vi phạm: {r.get('so_lan_vi_pham',0)}"
        for r in (shared.get("noi_quy") or [])
    )
    chi_dao_text = "\n".join(
        f"  CD{r.get('stt','')}: {r.get('noi_dung','')} – Hoàn thành: {r.get('muc_do','')}"
        for r in (shared.get("chi_dao") or [])
    )
    if noi_quy_text: excel_raw += f"\n\nNỘI QUY:\n{noi_quy_text}"
    if chi_dao_text: excel_raw += f"\n\nCHỈ ĐẠO:\n{chi_dao_text}"

    # ── Dummy docx_parsed / xlsx_parsed structures cho pipeline ─────────────
    docx_parsed = {
        "nhan_vien_info": {
            "ten_nhan_vien": ef.get("ho_ten",""),
            "ma_nhan_vien":  ef.get("ma_nhan_su",""),
            "chuc_danh":     ef.get("chuc_danh",""),
            "don_vi":        ef.get("phong_ban",""),
            "ngay_nhan_viec":ef.get("ngay_nhan_viec",""),
            "ngay_het_han":  ef.get("ngay_het_han",""),
            "ten_hod":       ef.get("ten_hod",""),
        },
        "sections": {
            "nhiem_vu_ket_qua": [
                {"ten": item, "ket_qua_pct": ""}
                for item in (ef.get("cong_viec_duoc_giao","") or "").split("\n")
                if item.strip()
            ],
            "weekly_table": {
                t: {
                    "san_pham": ef.get(f"san_pham_{t}",""),
                    "nhiem_vu": ef.get(f"nhiem_vu_tuan_{t}", ef.get(f"san_pham_{t}","")),
                }
                for t in range(1, 9)
            },
        },
    }
    xlsx_parsed = {
        "kpi_rows": kpi_rows,
        "nhan_vien_info": {},
        "weekly_kpi": {"rows": {}, "computed_avg": None, "stated_avg": None, "issues": []},
    }

    kpi_summary = _build_kpi_summary(xlsx_parsed)

    # ── Tái dùng user_msg format như review_files ────────────────────────────
    user_msg = f"""
═══ FILE WORD – PHIẾU ĐÁNH GIÁ (TỪ SCAN OCR) ═══
{word_raw[:14000]}

═══ FILE EXCEL – KẾ HOẠCH KPI (TÓM TẮT) ═══
{kpi_summary}

═══ FILE EXCEL – TOÀN BỘ NỘI DUNG ═══
{excel_raw[:6000]}

═══ YÊU CẦU KIỂM TRA ═══
Đây là dữ liệu từ scan OCR (không phải file gốc). Đọc TOÀN BỘ nội dung ở trên và thực hiện đúng các kiểm tra theo bộ tiêu chí.

CẤU TRÚC FILE WORD – ĐỌC KỸ:
● Phần V (Tuần 1-8) = nguồn chính để check W3 (Sản phẩm đặt ra, Nhiệm vụ đặt ra).

═══ KẾT QUẢ KIỂM TRA W3 (ĐÃ TÍNH SẴN – DÙNG NGUYÊN, KHÔNG TỰ PHÁN ĐOÁN) ═══
Dưới đây là kết quả đã kiểm tra từng tuần trong bảng 2.1–2.8 của file (từ scan OCR).
TUYỆT ĐỐI chỉ dùng kết quả này cho W3. KHÔNG đọc bảng 1.1–1.8 để check W3.

{chr(10).join(
    f"TUẦN {t}: " + (
        ("❌ THIẾU Sản phẩm đặt ra | " if not ef.get(f"san_pham_{t}","").strip() else "✅ Sản phẩm đặt ra: CÓ | ") +
        ("❌ THIẾU Nhiệm vụ đặt ra" if not ef.get(f"nhiem_vu_tuan_{t}", ef.get(f"san_pham_{t}","")).strip() else "✅ Nhiệm vụ đặt ra: CÓ")
    )
    for t in range(1, 9)
)}

QUY TẮC: Chỉ báo lỗi W3 khi dòng trên hiện ❌. Nếu ✅ → KHÔNG báo lỗi, dù raw text có vẻ thiếu.

═══ KẾT QUẢ KIỂM TRA E1 (ĐÃ TÍNH SẴN) ═══
{chr(10).join(
    f"STT {r['stt']} [{r['cong_viec'][:35]}]: " + (
        f"✅ CÓ minh chứng: {r.get('minh_chung','')[:60]}"
        if r.get("minh_chung","") else "❌ TRỐNG – Thiếu minh chứng"
    )
    for r in kpi_rows
)}

Trả về JSON theo đúng schema.
"""

    session_id = str(uuid.uuid4())
    client = _get_client()
    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": user_msg},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=8000,
    )
    result = json.loads(resp.choices[0].message.content)
    result = _filter_result(result)
    _log_tokens(resp, "review_from_scan")

    sess = _get_session(session_id)
    sess["review"] = result
    sess["pending_issues"] = list(result.get("van_de", []))
    sess["history"] = [
        {"role": "system",    "content": _CHAT_SYSTEM},
        {"role": "user",      "content": user_msg},
        {"role": "assistant", "content": json.dumps(result, ensure_ascii=False)},
    ]
    _save_session(session_id, sess)

    weekly_kpi = xlsx_parsed.get("weekly_kpi") or {}
    return {
        "session_id":      session_id,
        "status":          result.get("status", ""),
        "tong_quan":       result.get("tong_quan", ""),
        "van_de":          result.get("van_de", []),
        "uu_diem":         result.get("uu_diem", []),
        "luu_y_chung":     result.get("luu_y_chung", ""),
        "phan_I_ok":       result.get("phan_I_ok", True),
        "phan_I_nhan_xet": result.get("phan_I_nhan_xet", ""),
        "phan_II_tom_tat": result.get("phan_II_tom_tat", ""),
        "hoi_nhap_ok":     result.get("hoi_nhap_ok", True),
        "hoi_nhap_nhan_xet": result.get("hoi_nhap_nhan_xet", ""),
        "nguoi_giao_viec": result.get("nguoi_giao_viec", {}),
        "xlsx_kpi":        kpi_rows,
        "weekly_kpi":      {"rows": {}, "computed_avg": None, "stated_avg": None, "issues": []},
        "thong_tin_nhan_vien": docx_parsed["nhan_vien_info"],
        "phan_tich_2as":   result.get("phan_tich_2as", []),
        "canh_bao_2as":    result.get("canh_bao_2as", []),
        "de_xuat_xu_ly":   result.get("de_xuat_xu_ly", {}),
        "viec_can_lam":    _ensure_viec_can_lam(result, (result.get("de_xuat_xu_ly") or {}).get("ket_qua_tv", "")),
        "canh_bao_han":    _compute_canh_bao_han_real(
            ef.get("ngay_het_han") or
            (result.get("canh_bao_han") or {}).get("ngay_het_han", "")
        ),
        "from_scan":       True,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Endpoint 1: review_files
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist(allow_guest=True)


def review_files():
    """
    POST multipart/form-data:
      - docx_file: file Word phiếu đánh giá thử việc
      - xlsx_file: file Excel kế hoạch KPI
      - session_id: (optional) để tiếp tục session cũ

    Response JSON:
      - session_id: để dùng cho chat_review
      - status: "ĐẠT" | "CHƯA ĐẠT – CẦN BỔ SUNG"
      - tong_quan, van_de[], uu_diem[], luu_y_chung
      - xlsx_kpi: parsed KPI rows với status từng hàng
    """
    files = frappe.request.files if frappe.request else {}
    form = frappe.request.form if frappe.request else {}


    session_id = form.get("session_id") or str(uuid.uuid4())
    sess = _get_session(session_id)

    # ── Validate file type ─────────────────────────────────────────────────────
    # Kiểm tra đúng định dạng file trước khi xử lý
    _DOCX_ALLOWED = (".docx", ".pdf")
    _XLSX_ALLOWED = (".xlsx", ".xls", ".pdf")
    for field, allowed, label in [("docx_file", _DOCX_ALLOWED, "Word (.docx) hoặc PDF (.pdf)"), ("xlsx_file", _XLSX_ALLOWED, "Excel (.xlsx) hoặc PDF (.pdf)")]:
        if field in files:
            fname = (files[field].filename or "").lower()
            if not any(fname.endswith(ext) for ext in allowed):
                frappe.throw(f"File không đúng định dạng. Vui lòng upload đúng file {label}.")

    # ── Parse DOCX ────────────────────────────────────────────────────────────
    docx_parsed = {"full_text": sess.get("docx_text", ""), "tables": [], "sections": {}}
    if "docx_file" in files:
        raw = files["docx_file"].stream.read()
        fname = (files["docx_file"].filename or "").lower()
        if fname.endswith(".pdf"):
            docx_parsed = _parse_pdf_for_docx(raw)
        else:
            docx_parsed = _parse_docx(raw)
        sess["docx_text"] = docx_parsed["full_text"]
        sess["docx_sections"] = docx_parsed.get("sections", {})
        # Reset review cũ vì file đã thay đổi
        sess["review"] = None
        sess["pending_issues"] = None
        sess["history"] = []
    elif sess.get("docx_text"):
        # Dùng lại text từ session nhưng cần reconstruct sections
        docx_parsed["full_text"] = sess["docx_text"]
        docx_parsed["sections"] = sess.get("docx_sections", _extract_sections(sess["docx_text"]))
    else:
        frappe.throw("Vui lòng upload file Word (.docx) phiếu đánh giá thử việc.")

    # ── Parse XLSX ────────────────────────────────────────────────────────────
    xlsx_parsed = sess.get("xlsx_data", {})
    if "xlsx_file" in files:
        raw = files["xlsx_file"].stream.read()
        fname = (files["xlsx_file"].filename or "").lower()
        if fname.endswith(".pdf"):
            xlsx_parsed = _parse_pdf_for_xlsx(raw)
        else:
            xlsx_parsed = _parse_xlsx(raw)
        sess["xlsx_data"] = xlsx_parsed
        # Reset review cũ vì file đã thay đổi
        sess["review"] = None
        sess["pending_issues"] = None
        sess["history"] = []
    elif not xlsx_parsed:
        frappe.throw("Vui lòng upload file Excel (.xlsx) kế hoạch KPI.")

    # ── Nhận thêm params mới (eval_type, báo cáo ngày, date range) ─────────────
    eval_type = form.get("eval_type", "thu_viec")  # 'thu_viec' | 'hoc_viec'
    ngay_bd = form.get("ngay_bd", "")
    ngay_kt = form.get("ngay_kt", "")
    so_ngay_can_bc_str = form.get("so_ngay_can_bc", "")

    # Parse file báo cáo ngày (nếu có) — shared utility, Vision fallback included
    daily_report_text = ""
    if "daily_report_file" in files:
        from cnb_2as.services.document_parser import parse_daily_report
        raw_daily = files["daily_report_file"].stream.read()
        fname_daily = files["daily_report_file"].filename or ""
        daily_report_text = parse_daily_report(raw_bytes=raw_daily, filename=fname_daily)

    # Tính số ngày làm việc từ date range — shared utility
    if not so_ngay_can_bc_str and ngay_bd and ngay_kt:
        from cnb_2as.services.document_parser import count_working_days
        _cnt = count_working_days(ngay_bd, ngay_kt)
        if _cnt:
            so_ngay_can_bc_str = str(_cnt)


    pending = sess.get("pending_issues") or []
    if pending:
        has_word_errors = any(v.get("loai") == "WORD" or str(v.get("nhom_tieu_chi", "")).startswith("W") for v in pending)
        has_excel_errors = any(v.get("loai") == "EXCEL" or str(v.get("nhom_tieu_chi", "")).startswith("E") for v in pending)
        if has_word_errors and "docx_file" not in files:
            frappe.throw("Còn lỗi ở file Word. Vui lòng upload lại file Word đã chỉnh sửa.")
        if has_excel_errors and "xlsx_file" not in files:
            frappe.throw("Còn lỗi ở file Excel. Vui lòng upload lại file Excel đã chỉnh sửa.")

    # ── Xây dựng prompt ──────────────────────────────────────────────────────────────────
    user_msg = _build_review_prompt(eval_type, docx_parsed, xlsx_parsed,
                                     daily_report_text=daily_report_text,
                                     so_ngay_can_bc=so_ngay_can_bc_str)
    # ── Gọi OpenAI ────────────────────────────────────────────────────────────

    client = _get_client()
    try:
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=14000,
        )
    except Exception as openai_err:
        err_str = str(openai_err)
        if "insufficient_quota" in err_str or "429" in err_str:
            frappe.throw(
                "❌ API OpenAI đã hết quota (429). "
                "Vui lòng nạp thêm credits tại platform.openai.com/billing "
                "hoặc liên hệ admin để đổi API key."
            )
        elif "authentication" in err_str.lower() or "401" in err_str:
            frappe.throw("❌ API key OpenAI không hợp lệ. Vui lòng kiểm tra lại cấu hình.")
        else:
            frappe.throw(f"❌ Lỗi khi gọi OpenAI: {err_str[:200]}")
    result = json.loads(resp.choices[0].message.content)
    result = _filter_result(result)  # Xóa bất kỳ E1 nào AI tự sinh ra
    _log_tokens(resp, "review_files")

    # ── Debug: log sự có mặt của các field quan trọng ──────────────────────────
    _logger = frappe.logger("cnb_review", allow_site=True)
    _logger.info(
        f"[RESULT_FIELDS] bang_ty_trong={'CÓ' if result.get('bang_ty_trong') else 'THIẾU'} "
        f"| bao_cao_ngay={'CÓ' if result.get('bao_cao_ngay') else 'THIẾU'} "
        f"| danh_gia_quan_ly={'CÓ' if result.get('danh_gia_quan_ly') else 'THIẾU'} "
        f"| daily_text_len={len(daily_report_text)} "
        f"| total_tokens={resp.usage.total_tokens if resp.usage else '?'}"
    )


    # Lưu vào session (Redis cache – dùng chung giữa các worker)
    sess["review"] = result
    # pending_issues chỉ được set 1 lần duy nhất từ lần review đầu tiên (None = chưa set)
    # Các lần upload sau KHÔNG ghi đè — recheck chỉ check trên lỗi gốc
    if sess["pending_issues"] is None:
        ai_issues = list(result.get("van_de", []))
        # ── Bổ sung lỗi E1 từ parser mà AI có thể bỏ sót ──────────────────────
        # AI đôi khi không báo E1 (thiếu minh chứng) dù parser phát hiện.
        # → Merge: nếu STT đã có trong ai_issues → bỏ qua; nếu chưa có → thêm vào.
        existing_e1_stts = {
            str(v.get("muc", "")).split("–")[0].strip()
            for v in ai_issues
            if str(v.get("nhom_tieu_chi", "")).startswith("E")
        }
        for kpi_row in xlsx_parsed.get("kpi_rows", []):
            if kpi_row.get("status") == "THIẾU":
                stt_key = f"STT {kpi_row['stt']}"
                if stt_key not in existing_e1_stts:
                    for issue_desc in kpi_row.get("issues", []):
                        ai_issues.append({
                            "loai": "EXCEL",
                            "nhom_tieu_chi": "E1",
                            "muc": f"STT {kpi_row['stt']} – {kpi_row.get('cong_viec', '')[:50]}",
                            "van_de": issue_desc,
                            "yeu_cau": "Bổ sung minh chứng (link hoặc hình ảnh) vào cột tương ứng trong file Excel.",
                        })
        # ── Bổ sung lỗi tính trung bình tuần nếu sai ───────────────────────
        weekly_kpi = xlsx_parsed.get("weekly_kpi") or {}
        for w_issue in weekly_kpi.get("issues", []):
            ai_issues.append({
                "loai": "EXCEL",
                "nhom_tieu_chi": "E4",
                "muc": "Mục 1.9 – Điểm trung bình KPI",
                "van_de": w_issue,
                "yeu_cau": "Kiểm tra lại công thức tính trung bình ở ô 1.9 và đảm bảo điền đủ kết quả 8 tuần.",
            })
        sess["pending_issues"] = ai_issues
    sess["history"] = [
        {"role": "system", "content": _CHAT_SYSTEM},
        {"role": "user", "content": user_msg},
        {"role": "assistant", "content": json.dumps(result, ensure_ascii=False)},
    ]
    _save_session(session_id, sess)

    weekly_kpi = xlsx_parsed.get("weekly_kpi") or {}
    return {
        "session_id": session_id,
        "status": result.get("status", ""),
        "tong_quan": result.get("tong_quan", ""),
        "van_de": result.get("van_de", []),
        "uu_diem": result.get("uu_diem", []),
        "luu_y_chung": result.get("luu_y_chung", ""),
        "phan_I_ok": result.get("phan_I_ok", True),
        "phan_I_nhan_xet": result.get("phan_I_nhan_xet", ""),
        "phan_II_tom_tat": result.get("phan_II_tom_tat", ""),
        "hoi_nhap_ok": result.get("hoi_nhap_ok", True),
        "hoi_nhap_nhan_xet": result.get("hoi_nhap_nhan_xet", ""),
        "nguoi_giao_viec": result.get("nguoi_giao_viec", {}),
        "xlsx_kpi": xlsx_parsed.get("kpi_rows", []),
        "weekly_kpi": {
            "rows": weekly_kpi.get("rows", {}),
            "computed_avg": weekly_kpi.get("computed_avg"),
            "stated_avg": weekly_kpi.get("stated_avg"),
            "issues": weekly_kpi.get("issues", []),
        },
        "thong_tin_nhan_vien": docx_parsed.get("nhan_vien_info") or xlsx_parsed.get("nhan_vien_info", {}),
        "phan_tich_2as": result.get("phan_tich_2as", []),
        "canh_bao_2as": result.get("canh_bao_2as", []),
        "de_xuat_xu_ly": result.get("de_xuat_xu_ly", {}),
        "viec_can_lam":  _ensure_viec_can_lam(result, (result.get("de_xuat_xu_ly") or {}).get("ket_qua_tv", "")),
        "canh_bao_han":  _compute_canh_bao_han_real(
            (result.get("canh_bao_han") or {}).get("ngay_het_han", "") or
            str((docx_parsed.get("nhan_vien_info") or {}).get("ngay_het_han_thu_viec", ""))
        ),
        "bang_ty_trong": result.get("bang_ty_trong", None),
        "bao_cao_ngay": result.get("bao_cao_ngay", None),
        "danh_gia_quan_ly": result.get("danh_gia_quan_ly", None),
        "eval_type": eval_type,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Endpoint 2: chat_review
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist(allow_guest=True)
def chat_review():
    """
    POST JSON hoặc form-data:
      - session_id: bắt buộc
      - message: câu hỏi / thông tin bổ sung của user
      - docx_file: (optional) file Word mới upload để re-check
      - xlsx_file: (optional) file Excel mới upload để re-check

    Response JSON:
      - reply: câu trả lời của AI
      - re_review: (optional) kết quả review lại nếu có file mới
    """
    files = frappe.request.files if frappe.request else {}
    # Support cả JSON và form-data
    if frappe.request and frappe.request.is_json:
        body = frappe.request.get_json(force=True) or {}
    else:
        body = frappe.request.form or {}

    session_id = body.get("session_id", "")
    message = body.get("message", "").strip()

    if not session_id:
        frappe.throw("session_id là bắt buộc.")
    if not message and not files:
        frappe.throw("Vui lòng nhập câu hỏi hoặc upload file mới.")

    sess = _get_session(session_id)
    if not sess.get("review"):
        frappe.throw("Chưa có kết quả review. Vui lòng review_files trước.")

    # Nếu có file mới upload → re-parse và re-check nghiêm ngặt từng lỗi gốc
    re_review = None
    if "docx_file" in files or "xlsx_file" in files:
        # Validate file type
        _DOCX_ALLOWED = (".docx", ".pdf")
        _XLSX_ALLOWED = (".xlsx", ".xls", ".pdf")
        for field, allowed, label in [("docx_file", _DOCX_ALLOWED, "Word (.docx) hoặc PDF (.pdf)"), ("xlsx_file", _XLSX_ALLOWED, "Excel (.xlsx) hoặc PDF (.pdf)")]:
            if field in files:
                fname = (files[field].filename or "").lower()
                if not any(fname.endswith(ext) for ext in allowed):
                    frappe.throw(f"File không đúng định dạng. Vui lòng upload đúng file {label}.")

        # ── Lưu nội dung CŨ trước khi overwrite (dùng để tính diff) ──────────────
        old_docx_text = sess.get("docx_text", "") or ""
        old_docx_sections = dict(sess.get("docx_sections") or {})   # snapshot từng tuần cũ
        old_kpi_rows = (sess.get("xlsx_data") or {}).get("kpi_rows", [])

        if "docx_file" in files:
            raw = files["docx_file"].stream.read()
            fname = (files["docx_file"].filename or "").lower()
            if fname.endswith(".pdf"):
                parsed = _parse_pdf_for_docx(raw)
            else:
                parsed = _parse_docx(raw)
            sess["docx_text"] = parsed["full_text"]
            sess["docx_sections"] = parsed.get("sections", {})
        if "xlsx_file" in files:
            raw = files["xlsx_file"].stream.read()
            fname = (files["xlsx_file"].filename or "").lower()
            if fname.endswith(".pdf"):
                sess["xlsx_data"] = _parse_pdf_for_xlsx(raw)
            else:
                sess["xlsx_data"] = _parse_xlsx(raw)

        # Lấy pending_issues GỐC (không bao giờ bị overwrite từ lần đầu review)
        # Dùng copy để tránh mutation side-effects
        current_issues = list(sess.get("pending_issues") or [])

        # ── Bổ sung lỗi E1 từ parser nếu AI đã bỏ sót ──────────────────────
        # Chỉ thêm nếu chưa có trong current_issues — dùng full muc key để tránh duplicate.
        xlsx_data_cur = sess.get("xlsx_data") or {}
        existing_e1_mucs = {
            str(v.get("muc", "")).strip()
            for v in current_issues
            if str(v.get("nhom_tieu_chi", "")).upper() == "E1"
        }
        for kpi_row in xlsx_data_cur.get("kpi_rows", []):
            if kpi_row.get("status") == "THIẾU":
                muc_key = f"STT {kpi_row['stt']} – {kpi_row.get('cong_viec', '')[:50]}"
                if muc_key not in existing_e1_mucs:
                    for issue_desc in kpi_row.get("issues", []):
                        if "minh chứng" in issue_desc.lower():  # chỉ thêm E1, không thêm lỗi khác
                            current_issues.append({
                                "loai": "EXCEL",
                                "nhom_tieu_chi": "E1",
                                "muc": muc_key,
                                "van_de": issue_desc,
                                "yeu_cau": "Bổ sung minh chứng (link hoặc hình ảnh) vào cột tương ứng trong file Excel.",
                            })
                            existing_e1_mucs.add(muc_key)  # ngăn thêm trùng trong cùng loop

        # Kiểm tra: lỗi Word phải được fix bằng file Word mới, lỗi Excel bằng file Excel mới
        word_issues = [v for v in current_issues
                       if v.get("loai") == "WORD" or str(v.get("nhom_tieu_chi", "")).startswith("W")]
        excel_issues = [v for v in current_issues
                        if v.get("loai") == "EXCEL" or str(v.get("nhom_tieu_chi", "")).startswith("E")]
        cross_issues = [v for v in current_issues
                        if str(v.get("nhom_tieu_chi", "")).startswith("X")]
        # Lỗi CHUNG (X1) → recheck khi có cả 2 file hoặc ít nhất 1 file mới
        other_issues = [v for v in current_issues if v not in word_issues and v not in excel_issues and v not in cross_issues]

        # Xác định lỗi nào được recheck và lỗi nào giữ nguyên
        issues_to_recheck = []
        issues_kept_as_is = []  # lỗi thuộc file chưa upload → giữ 100% không thay đổi

        if "docx_file" in files:
            issues_to_recheck.extend(word_issues)
        else:
            issues_kept_as_is.extend(word_issues)  # chưa có Word mới → giữ nguyên

        if "xlsx_file" in files:
            issues_to_recheck.extend(excel_issues)
        else:
            issues_kept_as_is.extend(excel_issues)  # chưa có Excel mới → giữ nguyên

        # Cross-check (X1) → recheck nếu có ít nhất 1 trong 2 file mới
        issues_to_recheck.extend(cross_issues)
        issues_to_recheck.extend(other_issues)

        if not current_issues:
            # Không còn lỗi pending nào → trả thẳng ĐẠT
            re_review = {
                "status": "ĐẠT",
                "tong_quan": "Tất cả vấn đề đã được khắc phục. Hồ sơ đạt yêu cầu.",
                "van_de": [],
                "uu_diem": sess["review"].get("uu_diem", []),
                "luu_y_chung": "",
            }
        elif not issues_to_recheck:
            # Tất cả lỗi đều thuộc file chưa upload → nhắc upload đúng file
            missing_files = []
            if word_issues and "docx_file" not in files:
                missing_files.append(f"Word (.docx) – còn {len(word_issues)} lỗi")
            if excel_issues and "xlsx_file" not in files:
                missing_files.append(f"Excel (.xlsx) – còn {len(excel_issues)} lỗi")
            frappe.throw(
                "Bạn cần upload đúng file đã sửa để hệ thống có thể kiểm tra:\n"
                + "\n".join(f"• {m}" for m in missing_files)
            )
        else:
            # ── Tính diff (TRƯỚC KHI phân loại để dùng làm cơ sở hard-lock) ────────
            new_docx_text = sess.get("docx_text", "") or ""
            new_docx_sections = sess.get("docx_sections") or {}
            new_kpi_rows = (sess.get("xlsx_data") or {}).get("kpi_rows", [])
            docx_diff = _compute_text_diff(old_docx_text, new_docx_text) if "docx_file" in files else "(Không upload file Word mới)"
            xlsx_diff = _compute_kpi_diff(old_kpi_rows, new_kpi_rows) if "xlsx_file" in files else "(Không upload file Excel mới)"
            # Diff theo từng tuần (dùng cho W3 recheck)
            weekly_diff = _compute_weekly_diff(old_docx_sections, new_docx_sections) if "docx_file" in files else "(Không upload file Word mới)"

            UNCHANGED_SIGNALS = (
                "(Nội dung KHÔNG THAY ĐỔI so với lần trước)",
                "(Bảng KPI KHÔNG THAY ĐỔI so với lần trước)",
                "(Lần đầu upload",
            )
            docx_unchanged = any(docx_diff.startswith(s) for s in UNCHANGED_SIGNALS)
            xlsx_unchanged = any(xlsx_diff.startswith(s) for s in UNCHANGED_SIGNALS)

            # ── Hard-lock: nếu diff = không thay đổi → giữ NGUYÊN tất cả lỗi loại đó ──
            # Không cần hỏi AI — không có gì thay đổi thì không có gì được fix.
            if docx_unchanged and "docx_file" in files:
                # File Word giống hệt lần trước → lock tất cả word/cross issues
                # Dùng id() để tránh duplicate khi issues_to_recheck đã có rồi
                locked_ids = {id(v) for v in word_issues + cross_issues + other_issues}
                # Thêm vào kept chỉ những issue chưa có trong kept (tránh trùng)
                existing_kept_ids = {id(v) for v in issues_kept_as_is}
                for v in word_issues + cross_issues + other_issues:
                    if id(v) not in existing_kept_ids:
                        issues_kept_as_is.append(v)
                        existing_kept_ids.add(id(v))
                # Xóa khỏi issues_to_recheck
                issues_to_recheck = [v for v in issues_to_recheck if id(v) not in locked_ids]
            else:
                # Word có thay đổi → kiểm tra từng W3 issue theo tuần:
                # Nếu weekly_diff của tuần X là "KHÔNG THAY ĐỔI" → lock issue W3 của tuần X đó
                import re as _re_hl
                for issue in list(issues_to_recheck):
                    ntc = str(issue.get("nhom_tieu_chi", "")).upper()
                    if ntc != "W3":
                        continue
                    muc = str(issue.get("muc", ""))
                    m = _re_hl.search(r"tu\w*n\s*(\d+)", muc.lower(), _re_hl.UNICODE)
                    if not m:
                        continue
                    tuan_num = int(m.group(1))
                    tuan_key = f"tuan_{tuan_num}"
                    old_tuan = (old_docx_sections.get(tuan_key) or "").strip()
                    new_tuan = (new_docx_sections.get(tuan_key) or "").strip()
                    if old_tuan == new_tuan and old_tuan:
                        # Tuần này không thay đổi → lock ngay, không hỏi AI
                        issues_to_recheck.remove(issue)
                        issues_kept_as_is.append(issue)

            if xlsx_unchanged and "xlsx_file" in files:
                # File Excel giống hệt → lock tất cả excel issues
                locked_excel = [v for v in issues_to_recheck
                                if v.get("loai") == "EXCEL" or str(v.get("nhom_tieu_chi", "")).startswith("E")]
                issues_to_recheck = [v for v in issues_to_recheck if v not in locked_excel]
                issues_kept_as_is.extend(locked_excel)

            # ── Deterministic check cho E1 (không cần AI) ─────────────────────────
            # E1 = thiếu minh chứng: chỉ cần parser xác nhận link có/không → 100% chắc chắn
            e1_to_check = [v for v in issues_to_recheck
                           if str(v.get("nhom_tieu_chi", "")).upper() == "E1"
                           and "xlsx_file" in files
                           and not xlsx_unchanged]
            non_e1_to_recheck = [v for v in issues_to_recheck
                                  if v not in e1_to_check]

            e1_fixed, e1_still_pending = _check_e1_deterministic(e1_to_check, new_kpi_rows)
            # E1 đã fix → bỏ ra khỏi issues; E1 chưa fix → giữ lại
            issues_kept_as_is.extend(e1_still_pending)
            # non_e1 và e1_fixed sẽ được xử lý bình thường (non_e1 qua AI, e1_fixed đã xong)

            # issues_to_recheck lúc này chỉ còn lỗi cần AI đọc (không có E1)
            issues_to_recheck = non_e1_to_recheck

            # Nếu sau khi hard-lock và deterministic check, không còn gì cần AI → skip OpenAI call
            if not issues_to_recheck:
                re_review = {
                    "status": "PLACEHOLDER",
                    "tong_quan": f"Đã kiểm tra xác định: {len(e1_fixed)} lỗi minh chứng đã được bổ sung.",
                    "van_de": [],
                    "uu_diem": sess["review"].get("uu_diem", []),
                    "luu_y_chung": "",
                    "da_fix_ids": [],
                    "chi_tiet_kiem_tra": [],
                }
                da_fix_ids = set()
                chi_tiet = {}
            else:
                # Xây dựng danh sách lỗi cần re-check với ID rõ ràng — AI phải xác nhận từng cái
                pending_lines = []
                for idx, v in enumerate(issues_to_recheck, 1):
                    pending_lines.append(
                        f"[ID-{idx}] [{v.get('nhom_tieu_chi', v.get('loai', '?'))}] "
                        f"Mục: {v.get('muc', '')} | "
                        f"Vấn đề gốc: {v.get('van_de', '')} | "
                        f"Yêu cầu cần sửa: {v.get('yeu_cau', '')} | "
                        f"Loại file: {v.get('loai', 'CHUNG')}"
                    )
                pending_issues_text = "\n".join(pending_lines)

                # Lấy sections Word để recheck X1 chính xác hơn
                sections = sess.get("docx_sections") or _extract_sections(sess.get("docx_text", ""))
                nhiem_vu_text = sections.get("nhiem_vu_thuc_hien") or "(Không tìm thấy phần nhiệm vụ)"
                kpi_tuan_text = sections.get("kpi_tuan") or "(Không tìm thấy phần KPI tuần)"
                kpi_summary = _build_kpi_summary(sess["xlsx_data"])

                recheck_msg = _RECHECK_PROMPT_TPL.format(
                    pending_issues_text=pending_issues_text,
                    docx_diff=docx_diff,
                    weekly_diff=weekly_diff,
                    xlsx_diff=xlsx_diff,
                    docx_text=(
                        f"=== PHẦN A – NHIỆM VỤ ĐÃ THỰC HIỆN ===\n{nhiem_vu_text[:3000]}\n\n"
                        f"=== PHẦN B – KPI TỪNG TUẦN ===\n{kpi_tuan_text[:3000]}\n\n"
                        f"=== TOÀN VĂN WORD ===\n{sess['docx_text'][:5000]}"
                    ),
                    xlsx_text=sess["xlsx_data"].get("full_text", "")[:5000],
                    kpi_summary=kpi_summary,
                )

                client = _get_client()
                resp = client.chat.completions.create(
                    model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Bạn là AI kiểm tra hồ sơ thử việc CT Group. "
                                "Chỉ dựa vào DIFF (phần thay đổi) để xác định lỗi đã fix chưa. "
                                "Nếu diff không có thay đổi ở phần liên quan → lỗi đó CHƯA fix, KHÔNG được cho pass. "
                                "Chỉ cho 'đã khắc phục' (đưa vào da_fix_ids) khi thấy dòng '+' trong diff chứng minh rõ ràng."
                            )
                        },
                        {"role": "user", "content": recheck_msg},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.05,
                    max_tokens=6000,
                )
                re_review = json.loads(resp.choices[0].message.content)
                re_review = _filter_result(re_review)
                # Ngăn AI tự thêm lỗi mới ngoài danh sách gốc khi recheck
                re_review = _filter_recheck_issues(re_review, issues_to_recheck)
                _log_tokens(resp, "recheck")

                da_fix_ids = set(re_review.get("da_fix_ids") or [])
                chi_tiet = {int(c["id"]): c for c in (re_review.get("chi_tiet_kiem_tra") or []) if isinstance(c, dict) and "id" in c}

            # —— Xác định lỗi nào thực sự đã fix từ AI response ——
            # Cross-check da_fix_ids với chi_tiet_kiem_tra để loại bỏ mâu thuẫn
            for cid, cval in chi_tiet.items():
                if cval.get("da_khac_phuc") is True and cid not in da_fix_ids:
                    da_fix_ids.add(cid)
            for cid, cval in chi_tiet.items():
                if cval.get("da_khac_phuc") is False and cid in da_fix_ids:
                    da_fix_ids.discard(cid)

            # Chỉ xoá khỏi issues_to_recheck những mục AI xác nhận đã fix theo ID
            still_pending_from_recheck = [
                issue for idx, issue in enumerate(issues_to_recheck, 1)
                if idx not in da_fix_ids
            ]

            # Van_de AI trả về chỉ dùng để lấy nội dung mô tả mới (updated yeu_cau, van_de text)
            # Map theo nhom_tieu_chi + muc để cập nhật nội dung mới nếu có
            ai_van_de_map = {}
            for v in (re_review.get("van_de") or []):
                key = (str(v.get("nhom_tieu_chi", "")), str(v.get("muc", "")))
                ai_van_de_map[key] = v

            # Cập nhật nội dung mô tả từ AI (nếu AI có update yêu cầu mới)
            updated_still_pending = []
            for issue in still_pending_from_recheck:
                key = (str(issue.get("nhom_tieu_chi", "")), str(issue.get("muc", "")))
                if key in ai_van_de_map:
                    # Dùng nội dung AI update (yêu cầu cụ thể hơn)
                    updated_still_pending.append(ai_van_de_map[key])
                else:
                    # Giữ nguyên nội dung gốc
                    updated_still_pending.append(issue)

            # Ghập lại: lỗi chưa fix + lỗi giữ nguyên (thuộc file chưa upload)
            remaining = updated_still_pending + issues_kept_as_is
            re_review["van_de"] = remaining
            re_review["status"] = "ĐẠT" if not remaining else "CHƯA ĐẠT – CẦN BỔ SUNG"
            if issues_kept_as_is:
                note = f" (Còn {len(issues_kept_as_is)} lỗi chưa kiểm tra vì chưa upload file tương ứng.)"
                re_review["luu_y_chung"] = (re_review.get("luu_y_chung") or "") + note

            # Cập nhật pending_issues = tất cả lỗi chưa được khắc phục
            sess["pending_issues"] = remaining

        sess["review"] = re_review
        # Cập nhật history với context re-check
        sess["history"] = [
            {"role": "system", "content": _CHAT_SYSTEM},
            {"role": "user", "content": f"[Re-check file mới, còn {len(current_issues)} vấn đề cần kiểm tra]"},
            {"role": "assistant", "content": json.dumps(re_review, ensure_ascii=False)},
        ]
        _save_session(session_id, sess)


    # Chat Q&A
    reply_text = ""
    if message:
        history = sess.get("history", [])
        history.append({"role": "user", "content": message})

        client = _get_client()
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            messages=history,
            temperature=0.2,
            max_tokens=1500,
        )
        reply_text = resp.choices[0].message.content
        _log_tokens(resp, "chat_qa")
        history.append({"role": "assistant", "content": reply_text})
        sess["history"] = history[-20:]  # giữ 20 turns gần nhất
        _save_session(session_id, sess)

    result = {"reply": reply_text}
    if re_review:
        result["re_review"] = {
            "status": re_review.get("status", ""),
            "tong_quan": re_review.get("tong_quan", ""),
            "van_de": re_review.get("van_de", []),
            "uu_diem": re_review.get("uu_diem", []),
            "luu_y_chung": re_review.get("luu_y_chung", ""),
            "xlsx_kpi": sess["xlsx_data"].get("kpi_rows", []),
        }
    return result

@frappe.whitelist()
def export_thu_viec_pdf(eval_data, filename="BaoCao_ThuViec"):
    """
    Tạo PDF từ eval_data sử dụng reportlab thay cho wkhtmltopdf.
    """
    import json
    from cnb_2as.services.pdf_generator import generate_thu_viec_pdf
    
    if isinstance(eval_data, str):
        try:
            eval_data = json.loads(eval_data)
        except:
            eval_data = {}
            
    pdf_bytes = generate_thu_viec_pdf(eval_data)
    
    frappe.response.filename = f"{filename}.pdf"
    frappe.response.filecontent = pdf_bytes.getvalue()
    frappe.response.type = "pdf"