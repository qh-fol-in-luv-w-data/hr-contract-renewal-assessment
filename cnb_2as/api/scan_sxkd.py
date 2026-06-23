"""
scan_sxkd.py — OCR Kế hoạch SXKD tháng bằng GPT-4o Vision
Trả về JSON cấu trúc Excel + hỗ trợ download Excel đã điền.
"""
import frappe
import json
import base64
import io
import os
import glob
import fitz  # PyMuPDF
from PIL import Image

# ──────────────────────────────────────────────────────────────────
# Helper: lấy OpenAI key (from Agent Hub Settings → site_config → env)
# ──────────────────────────────────────────────────────────────────
from cnb_2as.services.openai_client import get_api_key, get_client as _get_openai_client


# ──────────────────────────────────────────────────────────────────
# Helper: PDF → list of base64 PNG (high-res, watermark cropped)
# ──────────────────────────────────────────────────────────────────
def _pdf_to_images(file_bytes: bytes) -> list[str]:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages_b64 = []
    for page in doc:
        mat = fitz.Matrix(3.0, 3.0)
        pix = page.get_pixmap(matrix=mat)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        w, h = img.size
        # Crop bottom-right CamScanner watermark area
        img = img.crop((0, 0, int(w * 0.96), int(h * 0.94)))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=90)
        pages_b64.append(base64.b64encode(buf.getvalue()).decode())
    return pages_b64


# ──────────────────────────────────────────────────────────────────
# GPT-4o Vision OCR — single page
# ──────────────────────────────────────────────────────────────────
SYSTEM_MSG = (
    "You are an expert OCR assistant for Vietnamese corporate HR documents. "
    "Your job is to accurately read and transcribe all text from scanned table images, "
    "returning complete structured JSON. Never skip any cell, always read Vietnamese diacritics carefully."
)

OCR_PROMPT = """Đọc toàn bộ bảng KẾ HOẠCH SXKD THÁNG / BÁO CÁO KẾT QUẢ THỰC HIỆN trong ảnh này.

Cấu trúc bảng gồm:
- Tiêu đề: "KẾ HOẠCH SXKD THÁNG X VÀ ĐÁNH GIÁ KẾT QUẢ THỰC HIỆN"
- Họ và tên
- Bảng công việc chính: STT | CÁC MẢNG CÔNG TÁC | MÔ TẢ SẢN PHẨM PHẢI HOÀN THÀNH TRONG THÁNG | KẾ HOẠCH THỰC HIỆN (TỶ TRỌNG, KPI, BOD XÉT DUYỆT) | KẾT QUẢ THỰC HIỆN (TỶ LỆ KPI, KẾT QUẢ KPI, BOD XÉT DUYỆT) | LINK SẢN PHẨM ĐÃ UPLOAD
- Dòng TỶ LỆ ĐẠT ở cuối bảng
- Phần NỘI QUY BẮT BUỘC (nếu có): STT | NỘI DUNG | KẾ HOẠCH | KẾT QUẢ | XÁC NHẬN | GHI CHÚ
- Phần CHỈ ĐẠO CỦA BAN LÃNH ĐẠO (nếu có)
- Phần XÉT DUYỆT (HOD, BOD, Ranking) (nếu có)

Trả về JSON với cấu trúc:
{
  "tieu_de": "KẾ HOẠCH SXKD THÁNG X VÀ ĐÁNH GIÁ KẾT QUẢ THỰC HIỆN",
  "ho_ten": "...",
  "cong_viec": [
    {
      "stt": 1,
      "mang_cong_tac": "...",
      "mo_ta_san_pham": "...",
      "ty_trong": "30%",
      "kpi_ke_hoach": "100%",
      "bod_ke_hoach": "",
      "ty_le_kpi_ket_qua": "90%",
      "ket_qua_kpi": "27%",
      "bod_ket_qua": "",
      "link_san_pham": "..."
    }
  ],
  "ty_le_dat_ke_hoach": "100%",
  "ty_le_dat_ket_qua": "86%",
  "noi_quy": [
    {"stt": 1, "noi_dung": "Upload data", "ke_hoach": "100%", "ket_qua": "100%", "xac_nhan": "", "ghi_chu": "..."}
  ],
  "chi_dao": [
    {"stt": 1, "noi_dung": "", "ket_qua": "", "bod_xet_duyet": "", "ghi_chu": ""}
  ],
  "xet_duyet": {
    "hod_y_kien": "",
    "bod_y_kien": "",
    "ranking": ""
  }
}

Đọc KỸ từng ô, không bỏ sót. Nếu ô trống thì để chuỗi rỗng "". Đọc số % chính xác."""


def _ocr_page_title(client, page_b64: str, page_num: int) -> dict:
    """Pass 1: Nhanh — chỉ đọc tiêu đề và họ tên để xác định tháng."""
    prompt = (
        f"Trang {page_num}: Đọc tiêu đề bảng kế hoạch (thường ở đầu trang).\n"
        'Trả về JSON: {"tieu_de": "KẾ HOẠCH SXKD THÁNG X VÀ...", "ho_ten": "..."}\n'
        "Nếu không có tiêu đề mới trên trang này, để tieu_de rỗng \"\".\n"
        "KHÔNG cần đọc nội dung bảng."
    )
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a Vietnamese document OCR assistant. Return valid JSON only."},
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{page_b64}", "detail": "low"}}
            ]}
        ],
        temperature=0, max_tokens=200,
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content
    try:
        from cnb_2as.services.thu_viec_service import _log_tokens
        _log_tokens(resp, "scan_sxkd._ocr_page_title")
    except Exception:
        pass
    if not raw:
        return {"tieu_de": "", "ho_ten": ""}
    try:
        return json.loads(raw)
    except Exception:
        return {"tieu_de": "", "ho_ten": ""}


def _ocr_page_full(client, page_b64: str, page_num: int, known_title: str = "") -> dict:
    """Pass 2: Đọc toàn bộ nội dung trang với tiêu đề đã biết."""
    title_hint = f'Tiêu đề của tháng này là: "{known_title}"\n' if known_title else ""
    prompt = title_hint + OCR_PROMPT
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_MSG},
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{page_b64}", "detail": "high"}}
            ]}
        ],
        temperature=0, max_tokens=6000,
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content
    try:
        from cnb_2as.services.thu_viec_service import _log_tokens
        _log_tokens(resp, "scan_sxkd._ocr_page_full")
    except Exception:
        pass
    if not raw:
        return {}
    try:
        result = json.loads(raw)
        if known_title and not result.get("tieu_de"):
            result["tieu_de"] = known_title
        return result
    except Exception:
        return {}




import re as _re

def _blank_month(tieu_de="", ho_ten=""):
    return {
        "tieu_de": tieu_de,
        "ho_ten": ho_ten,
        "cong_viec": [],
        "ty_le_dat_ke_hoach": "",
        "ty_le_dat_ket_qua": "",
        "noi_quy": [],
        "chi_dao": [
            {"stt": 1, "noi_dung": "", "ket_qua": "", "bod_xet_duyet": "", "ghi_chu": ""},
            {"stt": 2, "noi_dung": "", "ket_qua": "", "bod_xet_duyet": "", "ghi_chu": ""},
            {"stt": 3, "noi_dung": "", "ket_qua": "", "bod_xet_duyet": "", "ghi_chu": ""},
        ],
        "xet_duyet": {"hod_y_kien": "", "bod_y_kien": "", "ranking": ""}
    }


def _extract_month_num(title: str) -> str:
    """Extract 'THANG X' number from title string for comparison."""
    m = _re.search(r'TH[ÁA]NG\s+(\d+)', title.upper())
    return m.group(1) if m else ""


def _merge_into_month(month: dict, page: dict):
    """Merge a single page's data into an existing month dict (in-place)."""
    if page.get("tieu_de") and not month["tieu_de"]:
        month["tieu_de"] = page["tieu_de"]
    if page.get("ho_ten") and not month["ho_ten"]:
        month["ho_ten"] = page["ho_ten"]
    if page.get("ty_le_dat_ke_hoach") and not month["ty_le_dat_ke_hoach"]:
        month["ty_le_dat_ke_hoach"] = page["ty_le_dat_ke_hoach"]
    if page.get("ty_le_dat_ket_qua") and not month["ty_le_dat_ket_qua"]:
        month["ty_le_dat_ket_qua"] = page["ty_le_dat_ket_qua"]

    # Append new STTs only
    existing = {cv["stt"] for cv in month["cong_viec"]}
    for cv in page.get("cong_viec", []):
        if cv.get("stt") not in existing:
            month["cong_viec"].append(cv)
            existing.add(cv["stt"])

    # Nội quy
    existing_nq = {n["stt"] for n in month["noi_quy"]}
    for nq in page.get("noi_quy", []):
        if nq.get("stt") not in existing_nq:
            month["noi_quy"].append(nq)
            existing_nq.add(nq["stt"])

    # Chỉ đạo
    for i, cd in enumerate(page.get("chi_dao", [])):
        if i < len(month["chi_dao"]) and cd.get("noi_dung"):
            month["chi_dao"][i] = cd

    # Xét duyệt
    for k in ["hod_y_kien", "bod_y_kien", "ranking"]:
        if page.get("xet_duyet", {}).get(k) and not month["xet_duyet"].get(k):
            month["xet_duyet"][k] = page["xet_duyet"][k]


def _group_pages_by_month(pages: list[dict]) -> list[dict]:
    """
    Group OCR pages by month (tieu_de).
    Each time a new month title appears, start a fresh bucket.
    Pages with no title are merged into the most recent bucket.
    Returns a list of month dicts, sorted by month number.
    """
    buckets: list[dict] = []  # list of month dicts
    month_nums: list[str] = []  # parallel list of month numbers

    for page in pages:
        if not page:
            continue

        page_title = page.get("tieu_de", "")
        page_month = _extract_month_num(page_title) if page_title else ""

        if page_title and page_month:
            # Check if this month already has a bucket
            if page_month in month_nums:
                idx = month_nums.index(page_month)
                _merge_into_month(buckets[idx], page)
            else:
                # New month — create new bucket
                bucket = _blank_month()
                _merge_into_month(bucket, page)
                buckets.append(bucket)
                month_nums.append(page_month)
        else:
            # No month title — merge into last bucket
            if buckets:
                _merge_into_month(buckets[-1], page)

    # Sort each bucket's cong_viec by STT
    for b in buckets:
        b["cong_viec"].sort(key=lambda x: x.get("stt", 999))

    return buckets


# ──────────────────────────────────────────────────────────────────
# Điền Excel template
# ──────────────────────────────────────────────────────────────────
def _get_template_path():
    """Find SXKD Excel template - searches relative to this file's app dir."""
    # This file is at: cnb_2as/cnb_2as/api/scan_sxkd.py
    # Template is at:  2as-employee-assessment/ISO-MẪU-...
    here = os.path.dirname(os.path.abspath(__file__))
    # Go up: api/ -> cnb_2as/ -> cnb_2as/ -> 2as-employee-assessment/
    app_root = os.path.dirname(os.path.dirname(os.path.dirname(here)))
    tpl = os.path.join(app_root, "ISO-MẪU-KẾ HOẠCH SXKD THÁNG VÀ BÁO CÁO KẾT QUẢ THỰC HIỆN_1.xlsx")
    if not os.path.exists(tpl):
        frappe.throw(f"Không tìm thấy Excel template tại: {tpl}")
    return tpl

def _fill_excel(data: dict) -> bytes:
    """Điền data vào Excel template, trả về bytes."""
    import openpyxl

    template = _get_template_path()
    wb = openpyxl.load_workbook(template)
    ws = wb.active

    def sv(coord, val):
        ws[coord] = val

    cvs = data.get("cong_viec", [])
    ho_ten = data.get("ho_ten", "").replace("Họ và tên:", "").strip()
    tieu_de = data.get("tieu_de", "KẾ HOẠCH SXKD")

    # ── Header ──
    sv('A1', tieu_de)
    sv('A2', f"Họ và tên: {ho_ten}")

    # ── Rows công việc (tối đa 3 cho T4 block, rows 5/8/11) ──
    row_slots = [5, 8, 11]
    for i, cv in enumerate(cvs[:3]):
        r = row_slots[i]
        sv(f'A{r}', cv.get("stt", i + 1))
        sv(f'B{r}', cv.get("mang_cong_tac", ""))
        sv(f'C{r}', cv.get("mo_ta_san_pham", ""))
        tt_raw = cv.get("ty_trong", "0%").replace("%", "").strip()
        kpi_raw = cv.get("kpi_ke_hoach", "100%").replace("%", "").strip()
        kq_raw = cv.get("ty_le_kpi_ket_qua", "0%").replace("%", "").strip()
        try:
            sv(f'D{r}', float(tt_raw) / 100)
        except:
            sv(f'D{r}', tt_raw)
        try:
            sv(f'E{r}', float(kpi_raw) / 100)
        except:
            sv(f'E{r}', kpi_raw)
        sv(f'F{r}', cv.get("bod_ke_hoach", ""))
        try:
            sv(f'G{r}', float(kq_raw) / 100)
        except:
            sv(f'G{r}', kq_raw)
        sv(f'H{r}', f'=G{r}*D{r}/E{r}')
        sv(f'I{r}', cv.get("bod_ket_qua", ""))
        sv(f'J{r}', cv.get("link_san_pham", ""))

    # Tỷ lệ đạt
    sv('B12', 'TỶ LỆ ĐẠT')
    sv('D12', '=SUM(D5:D11)')
    sv('H12', '=SUM(H5:H11)')

    # ── Nội quy ──
    nq_slots = [27, 28]
    noi_quy = data.get("noi_quy", [])
    for i, nq in enumerate(noi_quy[:2]):
        r = nq_slots[i]
        sv(f'A{r}', nq.get("stt", i + 1))
        sv(f'B{r}', nq.get("noi_dung", ""))
        kh_raw = nq.get("ke_hoach", "1").replace("%", "").strip()
        kq_raw2 = nq.get("ket_qua", "1").replace("%", "").strip()
        try:
            sv(f'D{r}', float(kh_raw) / 100 if "%" in nq.get("ke_hoach", "") else float(kh_raw))
        except:
            sv(f'D{r}', kh_raw)
        try:
            sv(f'G{r}', float(kq_raw2) / 100 if "%" in nq.get("ket_qua", "") else float(kq_raw2))
        except:
            sv(f'G{r}', kq_raw2)
        sv(f'J{r}', nq.get("ghi_chu", ""))

    # ── Chỉ đạo ──
    cd_slots = [33, 34, 35]
    chi_dao = data.get("chi_dao", [])
    for i, cd in enumerate(chi_dao[:3]):
        r = cd_slots[i]
        sv(f'A{r}', cd.get("stt", i + 1))
        sv(f'B{r}', cd.get("noi_dung", ""))
        sv(f'G{r}', cd.get("ket_qua", ""))
        sv(f'I{r}', cd.get("bod_xet_duyet", ""))
        sv(f'J{r}', cd.get("ghi_chu", ""))

    # ── Xét duyệt ──
    xd = data.get("xet_duyet", {})
    sv('D40', xd.get("hod_y_kien", ""))
    sv('H40', xd.get("ranking", ""))
    sv('D41', xd.get("bod_y_kien", ""))

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


# ──────────────────────────────────────────────────────────────────
# Whitelist API: scan & OCR
# ──────────────────────────────────────────────────────────────────
@frappe.whitelist()
def ocr_sxkd():
    """
    POST /api/method/cnb_2as.api.scan_sxkd.ocr_sxkd
    Form data: file (PDF)
    Returns: JSON với data đã OCR
    """
    if "file" not in frappe.request.files:
        frappe.throw("Thiếu file PDF")

    file_obj = frappe.request.files["file"]
    file_bytes = file_obj.read()

    client = _get_openai_client()

    # Convert PDF pages to images
    pages_b64 = _pdf_to_images(file_bytes)

    # ── PASS 1: Scan nhanh lấy tieu_de từng trang ──────────────────
    page_titles = []
    for i, b64 in enumerate(pages_b64):
        info = _ocr_page_title(client, b64, page_num=i+1)
        page_titles.append(info)

    # Fill-forward: trang không có tiêu đề kế thừa tiêu đề tháng gần nhất
    last_title, last_ho_ten = "", ""
    resolved = []
    for info in page_titles:
        t = info.get("tieu_de", "").strip()
        h = info.get("ho_ten", "").strip()
        if t and _extract_month_num(t):
            last_title = t
        if h:
            last_ho_ten = h
        resolved.append({"tieu_de": last_title, "ho_ten": last_ho_ten})

    # ── PASS 2: OCR full mỗi trang với tiêu đề đã biết ─────────────
    page_results = []
    for i, b64 in enumerate(pages_b64):
        known_title = resolved[i]["tieu_de"]
        result = _ocr_page_full(client, b64, page_num=i+1, known_title=known_title)
        if not result.get("tieu_de"):
            result["tieu_de"] = resolved[i]["tieu_de"]
        if not result.get("ho_ten"):
            result["ho_ten"] = resolved[i]["ho_ten"]
        page_results.append(result)

    # ── Group theo tháng ─────────────────────────────────────────────
    months = _group_pages_by_month(page_results)
    if not months:
        months = [_blank_month()]

    return {"ok": True, "months": months}



@frappe.whitelist()
def export_excel():
    """
    POST /api/method/cnb_2as.api.scan_sxkd.export_excel
    Form data: data (JSON string)
    Returns: Excel file download
    """
    import re
    # Frontend sends as FormData with field 'data'
    data_raw = frappe.form_dict.get("data", "")
    if not data_raw:
        # Fallback: raw body
        data_raw = frappe.request.get_data(as_text=True)
    if not data_raw:
        frappe.throw("Thiếu dữ liệu để export")

    if isinstance(data_raw, str):
        data = json.loads(data_raw)
    else:
        data = data_raw

    excel_bytes = _fill_excel(data)
    ho_ten = data.get("ho_ten", "NhanVien").replace("Họ và tên:", "").strip().replace(" ", "_")
    tieu_de = data.get("tieu_de", "SXKD")
    m = re.search(r'TH\u00c1NG\s+(\d+)', tieu_de)
    thang = f"T{m.group(1)}" if m else "T"

    filename = f"SXKD_{ho_ten}_{thang}.xlsx"
    frappe.response.filename = filename
    frappe.response.filecontent = excel_bytes
    frappe.response.type = "download"
