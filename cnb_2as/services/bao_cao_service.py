"""Service layer: OCR phiếu đánh giá nhân sự PAI + AI overview + build Excel tổng hợp."""
import base64, io, json, re, unicodedata
from concurrent.futures import ThreadPoolExecutor

import fitz
from PIL import Image

import frappe
from cnb_2as.services.openai_client import get_client
from cnb_2as.services.prompts.bao_cao_prompts import (
    OCR_SYSTEM as _OCR_SYS,
    OCR_PROMPT as _OCR_PROMPT,
    AI_OVERVIEW_SYSTEM as _AI_SYS,
    AI_OVERVIEW_PROMPT as _AI_PROMPT_TMPL,
)

# ── PDF → base64 images ───────────────────────────────────────────────
def _pdf_to_b64(file_bytes: bytes, dpi: int = 230, max_dim: int = 2048) -> list[str]:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    imgs = []
    mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)
    for page in doc:
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        if max(img.size) > max_dim:
            r = max_dim / max(img.size)
            img = img.resize((int(img.size[0] * r), int(img.size[1] * r)))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=90)
        imgs.append(base64.b64encode(buf.getvalue()).decode())
    doc.close()
    return imgs


# ── Name normalization ────────────────────────────────────────────────
def _norm_name(s: str) -> str:
    s = unicodedata.normalize("NFD", unicodedata.normalize("NFC", (s or "").strip()))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s.lower().strip())




def _ocr_one(client, file_bytes: bytes, session_name: str = "", action_name: str = "") -> dict:
    imgs = _pdf_to_b64(file_bytes)
    content = [{"type": "text", "text": _OCR_PROMPT}]
    for b in imgs:
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b}", "detail": "high"}})
    r = client.chat.completions.create(
        model="gpt-4o", temperature=0, max_tokens=12000,
        messages=[{"role": "system", "content": _OCR_SYS}, {"role": "user", "content": content}],
        response_format={"type": "json_object"},
    )
    try:
        from cnb_2as.services.thu_viec_service import _log_tokens
        _log_tokens(r, label="ocr_phieu", session_name=session_name, action_name=action_name)
    except Exception as e:
        frappe.logger("cnb_token").error(f"Lỗi log token ocr_phieu: {e}")
        
    return json.loads(r.choices[0].message.content)


# ── Normalize xep_loai (clean "Loại B", "Tốt", "Xuất sắc" etc. → "B", "A" …) ─
def _norm_xep_loai(raw: str) -> str:
    raw = (raw or "").strip()
    # Standalone letter first: "B", "Loại B", "loại b", "B+"
    m = re.search(r'\b([A-Ea-e])\b', raw)
    if m:
        return m.group(1).upper()
    # Vietnamese full-word labels (strip diacritics for matching)
    nfd = unicodedata.normalize("NFD", raw.lower())
    nd  = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    if "xuat sac" in nd:                    return "A"
    if "tot" in nd:                         return "B"
    if "kha" in nd or "dat yeu cau" in nd: return "C"
    if "can cai thien" in nd:              return "D"
    if "khong dat" in nd:                  return "E"
    # Fallback: any A-E character
    m = re.search(r'[A-Ea-e]', raw)
    return m.group().upper() if m else ""


# ── Normalize loai_phieu ("nhân viên tự đánh giá" → "tu_danh_gia" etc.)
def _norm_loai_phieu(raw: str) -> str:
    raw = (raw or "").lower()
    if "hod" in raw or "quản lý" in raw or "quan ly" in raw or "đánh giá nhân sự" in raw:
        return "hod"
    return "tu_danh_gia"


# ── Filename helpers ──────────────────────────────────────────────────
def _loai_from_filename(fname: str) -> str:
    """Detect loai_phieu from filename (more reliable than OCR classification)."""
    lower = (fname or "").lower()
    nfd = unicodedata.normalize("NFD", lower)
    nfd = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    if "tu danh gia" in nfd or "tu_danh_gia" in nfd:
        return "tu_danh_gia"
    if "danh gia nhan su" in nfd:
        return "hod"
    return ""


# ── Normalize OCR data (no auto-computation — raw OCR only) ───────────
def _calc_totals(data: dict) -> dict:
    data["loai_phieu"] = _norm_loai_phieu(data.get("loai_phieu", ""))

    for nhom_key in ("nhom_A", "nhom_B", "nhom_C"):
        nhom = data.get(nhom_key, {})
        tc = nhom.get("tieu_chi", [])
        # Normalize diem: "4" (str), 4.0 (float) → 4 (int); "-", "" → null
        for t in tc:
            raw = t.get("diem")
            if isinstance(raw, str):
                raw = raw.strip().lstrip("–-—").strip()
                t["diem"] = int(raw) if raw.isdigit() else None
            elif isinstance(raw, float):
                t["diem"] = int(raw)

        # Store tong_diem_tho per group (sum of individual criteria)
        if not nhom.get("tong_diem_tho"):
            vals = [t["diem"] for t in tc if isinstance(t.get("diem"), int)]
            if vals:
                nhom["tong_diem_tho"] = sum(vals)

    th = data.get("tong_hop", {})
    # Sync bang_quy_doi → nhom.tong_diem_tho if OCR filled the summary table
    bqd = {row.get("nhom", "").upper(): row for row in (th.get("bang_quy_doi") or [])}
    for nhom_key, letter in (("nhom_A", "A"), ("nhom_B", "B"), ("nhom_C", "C")):
        nhom = data.get(nhom_key, {})
        row = bqd.get(letter, {})
        if not nhom.get("tong_diem_tho") and row.get("diem_tho"):
            nhom["tong_diem_tho"] = row["diem_tho"]

    # Normalize xep_loai string only ("Loại B" → "B") — never fill from score
    if th.get("xep_loai"):
        th["xep_loai"] = _norm_xep_loai(th["xep_loai"])

    # tong_diem_100 = tổng raw tất cả tiêu chí / max_raw * 100
    # NV tự đánh giá: max_raw = 25+35+15 = 75  (nhóm C có 3 tiêu chí)
    # HOD:            max_raw = 25+35+20 = 80  (nhóm C có 4 tiêu chí)
    loai = data.get("loai_phieu", "")
    max_raw = 75 if loai == "tu_danh_gia" else 80
    raw_scores = []
    all_ok = True
    for nhom_key in ("nhom_A", "nhom_B", "nhom_C"):
        tho = data.get(nhom_key, {}).get("tong_diem_tho")
        if tho is not None:
            raw_scores.append(tho)
        else:
            all_ok = False
    if all_ok and raw_scores:
        th["tong_diem_100"] = round(sum(raw_scores) / max_raw * 100, 1)
    # If groups are incomplete, keep whatever OCR gave us (may be None)
    # xep_loai is NEVER auto-filled from score — must come from OCR (the ticked box)

    return data


# ── Map NV ↔ HOD per person ───────────────────────────────────────────
def map_phieu_list(phieu_list: list[dict]) -> list[dict]:
    by_person: dict[str, dict] = {}
    for data in phieu_list:
        data = _calc_totals(data)
        fname = data.get("_filename", "")

        # loai_phieu: filename is more reliable than OCR classification
        fname_loai = _loai_from_filename(fname)
        if fname_loai:
            data["loai_phieu"] = fname_loai
        loai = data.get("loai_phieu", "")

        tt = data.get("thong_tin_nhan_vien", {})
        ten = unicodedata.normalize("NFC", (tt.get("ho_ten") or "").strip())
        nten = _norm_name(ten)

        if nten not in by_person:
            by_person[nten] = {"ten": ten, "tu_danh_gia": None, "hod": None}
        if len(ten) > len(by_person[nten]["ten"]):
            by_person[nten]["ten"] = ten
        if loai == "tu_danh_gia":
            by_person[nten]["tu_danh_gia"] = data
        else:
            by_person[nten]["hod"] = data

    persons = []
    for nten, p in sorted(by_person.items()):
        nv = p["tu_danh_gia"] or {}
        hod = p["hod"] or {}
        tt_nv = nv.get("thong_tin_nhan_vien", {})
        tt_hod = hod.get("thong_tin_nhan_vien", {})
        ng = hod.get("nguoi_danh_gia", {})
        persons.append({
            "ho_ten": p["ten"],
            "chuc_danh": tt_hod.get("chuc_danh") or tt_nv.get("chuc_danh") or "",
            "phong_ban": tt_hod.get("phong_ban") or tt_nv.get("phong_ban") or "",
            "thoi_gian_lam_viec": tt_hod.get("thoi_gian_lam_viec") or tt_nv.get("thoi_gian_lam_viec") or "",
            "ky_danh_gia_tu": tt_hod.get("ky_danh_gia_tu") or tt_nv.get("ky_danh_gia_tu") or "",
            "ky_danh_gia_den": tt_hod.get("ky_danh_gia_den") or tt_nv.get("ky_danh_gia_den") or "",
            "ngay_danh_gia": tt_hod.get("ngay_danh_gia") or "",
            "nguoi_danh_gia": ng.get("ho_ten", ""),
            "chuc_danh_nguoi_danh_gia": ng.get("chuc_danh", ""),
            "tu_danh_gia": nv,
            "hod": hod,
        })
    return persons


# ── OCR batch (parallel) ──────────────────────────────────────────────
def ocr_batch(files_bytes: list[tuple[str, bytes]], session_name: str = "", action_name: str = "") -> list[dict]:
    client = get_client()
    site = getattr(frappe.local, "site", None)
    user = frappe.session.user if getattr(frappe, "session", None) else None

    def _process(args):
        if site:
            frappe.init(site)
            frappe.connect()
            if user:
                frappe.set_user(user)
        try:
            fname, fb = args
            result = _ocr_one(client, fb, session_name=session_name, action_name=action_name)
            result["_filename"] = fname
            return result
        finally:
            if site:
                frappe.destroy()

    with ThreadPoolExecutor(max_workers=6) as ex:
        results = list(ex.map(_process, files_bytes))

    return [r for r in results if r is not None]


# ── AI overview per person ────────────────────────────────────────────
def _criteria_summary(phieu: dict) -> str:
    """Tóm tắt tiêu chí I–VI: 'A: sum=21/ghi=21→qd=25 | B: ...'"""
    parts = []
    for nhom_key, lbl in [("nhom_A", "A"), ("nhom_B", "B"), ("nhom_C", "C")]:
        nhom = phieu.get(nhom_key, {})
        scored = [tc["diem"] for tc in nhom.get("tieu_chi", []) if tc.get("diem") is not None]
        if not scored:
            parts.append(f"{lbl}: —")
            continue
        s     = sum(scored)
        ghi   = nhom.get("tong_diem_tho", "?")
        qd_v  = nhom.get("diem_quy_doi", "?")
        parts.append(f"{lbl}: sum={s}/ghi={ghi}→qd={qd_v}")
    return " | ".join(parts)


def _ai_overview_one(client, person: dict, session_name: str = "", action_name: str = "") -> dict:
    """Tạo nhận xét tổng quan cho 1 người dựa trên chênh lệch tự khai vs HOD."""
    nv  = person.get("tu_danh_gia") or {}
    hod = person.get("hod") or {}

    def qd(d, nhom): return d.get(nhom, {}).get("diem_quy_doi") or "?"
    def tot(d): return d.get("tong_hop", {}).get("tong_diem_100") or "?"
    def xl(d):  return d.get("tong_hop", {}).get("xep_loai") or "?"

    nv_tot  = tot(nv)
    hod_tot = tot(hod)
    try:
        lech_pct = f"{round((float(hod_tot) - float(nv_tot)) / float(nv_tot) * 100, 1):+.1f}%"
    except Exception:
        lech_pct = "?"

    # HR diffs summary for nhat_quan field
    hr_row = person.get("hr_data") or {}
    if not hr_row:
        hr_diffs_text = "Chưa có dữ liệu HR"
    else:
        diffs = _compare_nv_hr(nv, hr_row)
        if not diffs:
            hr_diffs_text = "Khớp toàn bộ"
        else:
            lines = [f"Lệch {len(diffs)}/{len(NV_HR_FIELDS)} tiêu chí:"]
            for d in diffs:
                lines.append(f"  • {d['noi_dung']}: NV={d['nv_val']}, HR={d['hr_val']}")
            hr_diffs_text = "\n".join(lines)

    prompt = _AI_PROMPT_TMPL.format(
        ho_ten=person.get("ho_ten", ""),
        chuc_danh=person.get("chuc_danh", ""),
        nv_A=qd(nv, "nhom_A"), nv_B=qd(nv, "nhom_B"), nv_C=qd(nv, "nhom_C"),
        nv_tot=nv_tot, nv_xl=xl(nv),
        hod_A=qd(hod, "nhom_A"), hod_B=qd(hod, "nhom_B"), hod_C=qd(hod, "nhom_C"),
        hod_tot=hod_tot, hod_xl=xl(hod),
        lech=lech_pct,
        de_xuat=(hod.get("ket_qua_va_de_xuat") or {}).get("de_xuat_bo_tri") or "—",
        ke_hoach=(hod.get("ket_qua_va_de_xuat") or {}).get("ke_hoach_cai_thien") or "—",
        rx_b=hod.get("nhom_B", {}).get("nhan_xet_nhom") or "—",
        nv_criteria=_criteria_summary(nv),
        hod_criteria=_criteria_summary(hod),
        hr_diffs_text=hr_diffs_text,
    )

    r = client.chat.completions.create(
        model="gpt-4o", temperature=0.2, max_tokens=800,
        messages=[
            {"role": "system", "content": _AI_SYS},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )
    try:
        from cnb_2as.services.thu_viec_service import _log_tokens
        _log_tokens(r, label="ai_overview_phieu", session_name=session_name, action_name=action_name)
    except Exception as e:
        frappe.logger("cnb_token").error(f"Lỗi log token ai_overview: {e}")
        
    return json.loads(r.choices[0].message.content)


def ai_overviews_batch(persons: list[dict], session_name: str = "", action_name: str = "") -> list[dict]:
    """Chạy AI overview song song cho tất cả persons. Trả list dict cùng thứ tự."""
    client = get_client()
    site = getattr(frappe.local, "site", None)
    user = frappe.session.user if getattr(frappe, "session", None) else None

    def _run(person):
        if site:
            frappe.init(site)
            frappe.connect()
            if user:
                frappe.set_user(user)
        try:
            return _ai_overview_one(client, person, session_name=session_name, action_name=action_name)
        except Exception as e:
            frappe.log_error(title="AI Overview Error", message=str(e))
            return {"lech_diem": "", "diem_vs_de_xuat": "", "lot_khung": "", "nhat_quan": ""}
        finally:
            if site:
                frappe.destroy()

    with ThreadPoolExecutor(max_workers=6) as ex:
        return list(ex.map(_run, persons))


# ── HR data fields (key, full_header, short_header) ──────────────────
HR_FIELDS = [
    ("di_lam_tre",                "Số lần đi làm trễ",                                                                          "Trễ\n(lần)"),
    ("ve_som",                    "Số lần về sớm",                                                                               "Về sớm\n(lần)"),
    ("nghi_khong_phep",           "Số ngày nghỉ không phép",                                                                     "Nghỉ\nK.Phép"),
    ("sang_t7_vang_khong_phep",   "Số buổi sáng Thứ Bảy vắng mặt không phép",                                                   "T7 vắng\nK.Phép"),
    ("nhac_nho_vi_pham",          "Số lần bị nhắc nhở vi phạm nội quy",                                                          "Nhắc nhở\nVI phạm"),
    ("ban_giai_trinh",            "Số bản giải trình / kiểm điểm / cam kết đã ký",                                               "Giải\ntrình"),
    ("quyet_dinh_ky_luat",        "Số quyết định kỷ luật đã nhận (nếu có)",                                                      "QĐ\nKỷ luật"),
    ("tong_chuong_trinh_dt",      "Tổng số chương trình đào tạo Công ty tổ chức trong kỳ",                                       "Tổng\nĐT"),
    ("tham_gia_dt",               "Số chương trình đào tạo đã tham gia",                                                         "TG\nĐT"),
    ("vang_dt_co_ly_do",          "Số chương trình đào tạo vắng mặt (có lý do chính đáng và được cấp thẩm quyền phê duyệt)",    "Vắng ĐT\nC.L.Do"),
    ("vang_dt_khong_ly_do",       "Số chương trình đào tạo vắng mặt không lý do",                                                "Vắng ĐT\nK.L.Do"),
    ("giang_day_noi_bo",          "Số chương trình đào tạo nội bộ tham gia giảng dạy / chia sẻ",                                 "Giảng\nNội bộ"),
    ("tong_su_kien",              "Tổng số sự kiện Công ty tổ chức trong kỳ",                                                    "Tổng\nSK"),
    ("tham_gia_su_kien",          "Số sự kiện đã tham gia",                                                                      "TG\nSK"),
    ("vang_sk_co_ly_do",          "Số sự kiện vắng mặt có lý do chính đáng và được cấp có thẩm quyền phê duyệt",                "Vắng SK\nC.L.Do"),
    ("vang_sk_khong_ly_do",       "Số sự kiện vắng mặt không lý do",                                                            "Vắng SK\nK.L.Do"),
    ("tuan_khong_like_share",     "Số tuần không thực hiện like / share theo quy định",                                          "T.K.\nL/S"),
    ("tong_luot_thieu_like_share","Tổng số lượt like / share còn thiếu (nếu có)",                                                "Thiếu\nL/S"),
    ("tong_bao_cao_ngay",         "Tổng số báo cáo ngày phải thực hiện trong kỳ",                                                "Tổng\nBC ngày"),
    ("bao_cao_dung_han",          "Số báo cáo ngày đã thực hiện đúng hạn",                                                       "BC\nĐúng hạn"),
    ("bao_cao_tre_han",           "Số báo cáo ngày trễ hạn",                                                                     "BC\nTrễ hạn"),
    ("bao_cao_khong_thuc_hien",   "Số báo cáo ngày không thực hiện",                                                             "BC\nK.T.hiện"),
]
HR_COLS = len(HR_FIELDS)  # 22

# ── NV self-report ↔ HR field mapping (sections II–V) ─────────────────
# (section_id, stt, hr_field_key, noi_dung)
NV_HR_FIELDS = [
    ("ky_luat",      1, "di_lam_tre",                "Số lần đi làm trễ"),
    ("ky_luat",      2, "ve_som",                    "Số lần về sớm"),
    ("ky_luat",      3, "nghi_khong_phep",            "Số ngày nghỉ không phép"),
    ("ky_luat",      4, "sang_t7_vang_khong_phep",    "Số buổi sáng T7 vắng không phép"),
    ("ky_luat",      5, "nhac_nho_vi_pham",           "Số lần bị nhắc nhở vi phạm"),
    ("ky_luat",      6, "ban_giai_trinh",             "Số bản giải trình đã ký"),
    ("ky_luat",      7, "quyet_dinh_ky_luat",         "Số quyết định kỷ luật"),
    ("dao_tao",      1, "tong_chuong_trinh_dt",       "Tổng số chương trình đào tạo"),
    ("dao_tao",      2, "tham_gia_dt",                "Số CT đào tạo đã tham gia"),
    ("dao_tao",      3, "vang_dt_co_ly_do",           "Số CT đào tạo vắng có lý do"),
    ("dao_tao",      4, "vang_dt_khong_ly_do",        "Số CT đào tạo vắng không lý do"),
    ("dao_tao",      5, "giang_day_noi_bo",           "Số CT nội bộ tham gia giảng dạy"),
    ("hoat_dong",    1, "tong_su_kien",               "Tổng số sự kiện"),
    ("hoat_dong",    2, "tham_gia_su_kien",           "Số sự kiện đã tham gia"),
    ("hoat_dong",    3, "vang_sk_co_ly_do",           "Số SK vắng có lý do"),
    ("hoat_dong",    4, "vang_sk_khong_ly_do",        "Số SK vắng không lý do"),
    ("hoat_dong",    5, "tuan_khong_like_share",      "Số tuần không like/share"),
    ("hoat_dong",    6, "tong_luot_thieu_like_share", "Tổng lượt like/share còn thiếu"),
    ("bao_cao_ngay", 1, "tong_bao_cao_ngay",          "Tổng số báo cáo ngày"),
    ("bao_cao_ngay", 2, "bao_cao_dung_han",           "Số BC ngày đúng hạn"),
    ("bao_cao_ngay", 3, "bao_cao_tre_han",            "Số BC ngày trễ hạn"),
    ("bao_cao_ngay", 4, "bao_cao_khong_thuc_hien",    "Số BC ngày không thực hiện"),
]


def _compare_nv_hr(nv_data: dict, hr_row: dict) -> list[dict]:
    """So sánh NV tự khai (II–V) vs HR. Trả list chênh lệch."""
    diffs = []
    for sec_id, stt, fkey, noi_dung in NV_HR_FIELDS:
        arr = nv_data.get(sec_id)
        if not isinstance(arr, list):
            continue
        row = next((r for r in arr if r.get("stt") == stt), None)
        nv_val = row.get("tu_bao_cao") if row else None
        hr_val = hr_row.get(fkey)
        if nv_val is None or hr_val is None:
            continue
        try:
            if int(nv_val) != int(hr_val):
                chenh = int(nv_val) - int(hr_val)
                diffs.append({
                    "noi_dung": noi_dung,
                    "nv_val": int(nv_val),
                    "hr_val": int(hr_val),
                    "chenh": chenh,
                })
        except (TypeError, ValueError):
            if str(nv_val) != str(hr_val):
                diffs.append({"noi_dung": noi_dung, "nv_val": nv_val, "hr_val": hr_val, "chenh": None})
    return diffs


def _norm_hr_header(s: str) -> str:
    """Normalize header for matching: strip diacritics, lowercase, alphanumeric only."""
    nfd = unicodedata.normalize("NFD", (s or "").lower())
    nd = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", nd)


# Alias map: normalized real-HR column name → field_key
# Dùng cho 4 file HR thật có tên cột khác HR_FIELDS
_HR_ALIASES = {
    "tongitre":         "di_lam_tre",               # "Tổng đi trễ" ("đ" stripped → "tongitre")
    "tongvesom":        "ve_som",                    # "Tổng về sớm"
    "tongluotthamgia":  "tham_gia_dt",               # "Tổng lượt tham gia"
    "tongthieu":        "tong_luot_thieu_like_share", # "Tổng thiếu" (like/share)
    # BC ngày file: short column names (đúng → ung vì đ bị strip)
    "baocaounghan":     "bao_cao_dung_han",          # "Báo cáo đúng hạn"
    "baocaotrehan":     "bao_cao_tre_han",           # "Báo cáo trễ hạn"
    "bckhongthuchien":  "bao_cao_khong_thuc_hien",   # "BC không thực hiện" (tránh nhầm tier-1 vs tuan_khong)
    # Sự kiện file: dùng "SK" để tránh nhầm với vang_dt_* (match cùng "vangmat")
    "vangskcolydo":     "vang_sk_co_ly_do",          # "Vắng SK có lý do"
    "vangskkhonglydo":  "vang_sk_khong_ly_do",       # "Vắng SK không lý do"
}
_TUAN_THIEU_KEY = "__tuan_thieu__"  # marker cho cột "Tuần X - Thiếu"


def parse_hr_excel(file_bytes: bytes) -> dict:
    """Parse HR data Excel (cả format hr_danh_gia/ lẫn file HR thật).
    Returns dict keyed by _norm_name(ho_ten) → {field_key: value}.
    """
    from openpyxl import load_workbook
    wb = load_workbook(filename=io.BytesIO(file_bytes), read_only=True, data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        wb.close()
        return {}

    # Tìm header row: dòng đầu tiên có "Họ và tên" / "họ tên"
    header_row_idx = 0
    for i, row in enumerate(rows):
        cells = [_norm_hr_header(str(c or "")) for c in row]
        if any("hoten" in c or ("ho" in c and "ten" in c) for c in cells):
            header_row_idx = i
            break

    header_raw  = [str(c or "") for c in rows[header_row_idx]]
    header_norm = [_norm_hr_header(h) for h in header_raw]

    field_norm = {_norm_hr_header(full): key for key, full, _ in HR_FIELDS}

    col_map = {}   # col_index → field_key  (or _TUAN_THIEU_KEY)
    name_col = None
    for ci, h in enumerate(header_norm):
        # Cột tên người
        if "hoten" in h or (h.startswith("ho") and "ten" in h):
            name_col = ci
            continue

        # Tier 1: khớp HR_FIELDS (substring, yêu cầu cả 2 >= 8 ký tự để tránh false positive)
        matched = False
        for nf, key in field_norm.items():
            if len(h) >= 8 and len(nf) >= 8 and (nf in h or h in nf):
                col_map[ci] = key; matched = True; break
            elif h == nf:
                col_map[ci] = key; matched = True; break

        if matched:
            continue

        # Tier 2: alias cho tên cột file HR thật
        alias = _HR_ALIASES.get(h)
        if alias:
            col_map[ci] = alias
            continue

        # Tier 3: cột "Tuần X - Thiếu" trong file like/share
        if re.match(r"tuan\d", h) and h.endswith("thieu"):
            col_map[ci] = _TUAN_THIEU_KEY

    if name_col is None:
        wb.close()
        return {}

    # Phát hiện file đào tạo: đếm cột khoá học individual nằm giữa name_col và tham_gia_dt_col
    # → derive tong_chuong_trinh_dt và vang_dt_khong_ly_do (gán toàn bộ là "không lý do"
    #   vì file HR không lưu lý do vắng từng lớp)
    tham_gia_dt_col = next((ci for ci, k in col_map.items() if k == "tham_gia_dt"), None)
    n_course_cols = 0
    if tham_gia_dt_col is not None and name_col is not None:
        n_course_cols = sum(
            1 for ci, h in enumerate(header_norm)
            if name_col < ci < tham_gia_dt_col
            and ci not in col_map
            and len(h) >= 8   # lọc "email", "chuvu", "congty" ... (quá ngắn)
        )

    result = {}
    for row in rows[header_row_idx + 1:]:
        if not row or all(c is None for c in row):
            continue
        name_raw = str(row[name_col] or "").strip()
        if not name_raw:
            continue
        nkey = _norm_name(name_raw)
        person_data = {}
        tuan_thieu_count = 0
        for ci, fkey in col_map.items():
            if ci >= len(row) or row[ci] is None:
                continue
            if fkey == _TUAN_THIEU_KEY:
                try:
                    if int(float(str(row[ci]))) > 0:
                        tuan_thieu_count += 1
                except (ValueError, TypeError):
                    pass
            else:
                try:
                    person_data[fkey] = int(float(str(row[ci])))
                except (ValueError, TypeError):
                    person_data[fkey] = 0
        if tuan_thieu_count:
            person_data["tuan_khong_like_share"] = tuan_thieu_count
        # Derive đào tạo: tổng + vắng = tong_ct - tham_gia (gán vắng không lý do)
        if n_course_cols > 0 and "tham_gia_dt" in person_data:
            person_data["tong_chuong_trinh_dt"] = n_course_cols
            person_data["vang_dt_khong_ly_do"] = max(0, n_course_cols - person_data["tham_gia_dt"])
        result[nkey] = person_data

    wb.close()
    return result


def parse_hr_files(files_bytes_list: list[bytes]) -> dict:
    """Merge nhiều file Excel HR (mỗi file 1 mục II–V). Returns {_norm_name: {field_key: int}}."""
    merged = {}
    for fb in files_bytes_list:
        partial = parse_hr_excel(fb)
        for name_key, fields in partial.items():
            if name_key not in merged:
                merged[name_key] = {}
            merged[name_key].update(fields)
    return merged


def build_hr_template_excel(persons: list[dict] | None = None) -> bytes:
    """Tạo file Excel template HR. Nếu truyền persons, pre-fill tên + chức danh từ scan."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter as gcl
    wb = Workbook()
    ws = wb.active
    ws.title = "Dữ liệu HR"

    fill_hdr  = PatternFill("solid", fgColor="1E40AF")
    fill_name = PatternFill("solid", fgColor="EFF6FF")
    font_hdr  = Font(name="Arial", bold=True, size=9, color="FFFFFF")
    font_name = Font(name="Arial", bold=True, size=9)
    font_data = Font(name="Arial", size=9)
    align_c = Alignment(horizontal="center", vertical="center", wrap_text=True)
    align_l = Alignment(horizontal="left", vertical="center")
    thin = Side(style="thin", color="CCCCCC")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    headers = ["STT", "Họ và tên", "Chức vụ"] + [full for _, full, _ in HR_FIELDS]
    ws.append(headers)

    for ci, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=ci)
        cell.fill = fill_hdr
        cell.font = font_hdr
        cell.alignment = align_c
        cell.border = border

    ws.row_dimensions[1].height = 60

    # Pre-fill từ persons nếu có
    for pi, person in enumerate(persons or [], 1):
        ten = person.get("ho_ten") or person.get("ten") or ""
        chuc_danh = person.get("chuc_danh") or ""
        row_vals = [pi, ten, chuc_danh] + [""] * len(HR_FIELDS)
        ws.append(row_vals)
        r = pi + 1
        for ci, val in enumerate(row_vals, 1):
            cell = ws.cell(row=r, column=ci)
            cell.border = border
            cell.alignment = align_c if ci != 2 else align_l
            if ci <= 3:
                cell.fill = fill_name
                cell.font = font_name
            else:
                cell.font = font_data
        ws.row_dimensions[r].height = 18

    ws.column_dimensions["A"].width = 5
    ws.column_dimensions["B"].width = 24
    ws.column_dimensions["C"].width = 20
    for ci in range(4, len(headers) + 1):
        ws.column_dimensions[gcl(ci)].width = 13

    ws.freeze_panes = "D2"

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


# ── Build Excel tổng hợp ──────────────────────────────────────────────
def build_excel(persons: list[dict], overviews: list[dict] | None = None,
                phong_ban: str = "", hr_data: dict | None = None) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
    from openpyxl.utils import get_column_letter

    if overviews is None:
        overviews = [{} for _ in persons]

    wb = Workbook()
    ws = wb.active
    ws.title = "Báo cáo ĐG Nhân sự"

    # ── Style helpers ──────────────────────────────────────────────────
    def _font(bold=False, size=10, color="000000"):
        return Font(name="Arial", bold=bold, size=size, color=color)
    def _fill(hex_color):
        return PatternFill(start_color=hex_color, end_color=hex_color, fill_type="solid")
    def _border():
        s = Side(style="thin")
        return Border(left=s, right=s, top=s, bottom=s)
    def _align(h="left", v="center", wrap=False):
        return Alignment(horizontal=h, vertical=v, wrap_text=wrap)

    FILL_TITLE  = _fill("312E81")
    FILL_HEADER = _fill("4F46E5")
    FILL_SUBHDR = _fill("E0E7FF")
    FILL_NV     = _fill("EFF6FF")
    FILL_HOD    = _fill("F0FDF4")
    FILL_AI     = _fill("FFF7ED")
    xl_fills = {
        "A": _fill("D1FAE5"), "B": _fill("DBEAFE"), "C": _fill("FEF9C3"),
        "D": _fill("FEE2E2"), "E": _fill("F3F4F6"),
    }

    def _hcell(ws, row, col, value, fill=None, bold=True, size=9, h="center", color="FFFFFF", wrap=True):
        c = ws.cell(row=row, column=col, value=value)
        c.font = _font(bold=bold, size=size, color=color)
        c.alignment = _align(h=h, wrap=wrap)
        c.border = _border()
        if fill: c.fill = fill
        return c

    def _dcell(ws, row, col, value, fill=None, bold=False, size=9, h="center", wrap=True):
        c = ws.cell(row=row, column=col, value=value)
        c.font = _font(bold=bold, size=size, color="1E293B")
        c.alignment = _align(h=h, wrap=wrap)
        c.border = _border()
        if fill: c.fill = fill
        return c

    def _qd(d, nhom):
        v = (d or {}).get(nhom, {}).get("diem_quy_doi")
        return v if v is not None else ""

    # ── Xếp loại counts ───────────────────────────────────────────────
    xl_info = [
        ("A", "Xuất sắc ≥ 90đ"),
        ("B", "Tốt 80–89đ"),
        ("C", "Khá 71–79đ"),
        ("D", "Cần cải thiện 60–70đ"),
        ("E", "Không đạt < 60đ"),
    ]
    nv_counts  = {xl: 0 for xl, _ in xl_info}
    hod_counts = {xl: 0 for xl, _ in xl_info}
    for p in persons:
        nv_xl  = (p.get("tu_danh_gia") or {}).get("tong_hop", {}).get("xep_loai", "")
        hod_xl = (p.get("hod") or {}).get("tong_hop", {}).get("xep_loai", "")
        if nv_xl  in nv_counts:  nv_counts[nv_xl]   += 1
        if hod_xl in hod_counts: hod_counts[hod_xl] += 1

    total_persons = len(persons)

    # ══════════════════════════════════════════════════════════════════
    # PHẦN 1 (rows 1–9): THỐNG KÊ XẾP LOẠI
    # ══════════════════════════════════════════════════════════════════
    LAST_COL_LETTER = "T"  # col 20 = COL_AI + 3 (final col)

    title1 = "BÁO CÁO ĐÁNH GIÁ NHÂN SỰ ĐỊNH KỲ"
    if phong_ban:
        title1 += f"  —  {phong_ban.upper()}"
    ws.merge_cells(f"A1:{LAST_COL_LETTER}1")
    c = ws.cell(row=1, column=1, value=title1)
    c.font = _font(bold=True, size=14, color="FFFFFF")
    c.alignment = _align(h="center", wrap=False)
    c.fill = FILL_TITLE
    ws.row_dimensions[1].height = 32

    dept_part = f"Phòng ban: {phong_ban}  ·  " if phong_ban else ""
    ws.merge_cells(f"A2:{LAST_COL_LETTER}2")
    c = ws.cell(row=2, column=1, value=f"{dept_part}THỐNG KÊ XẾP LOẠI  ·  Tổng số nhân viên: {total_persons}")
    c.font = _font(bold=True, size=10, color="312E81")
    c.alignment = _align(h="center")
    c.fill = FILL_SUBHDR
    ws.row_dimensions[2].height = 20

    _hcell(ws, 3, 1, "Xếp loại",     FILL_HEADER, size=8)
    _hcell(ws, 3, 2, "Mô tả",        FILL_HEADER, size=8)
    _hcell(ws, 3, 3, "NV tự ĐG",     FILL_NV,  size=8, color="1D4ED8")
    _hcell(ws, 3, 4, "% NV",         FILL_NV,  size=8, color="1D4ED8")
    _hcell(ws, 3, 5, "HOD đánh giá", FILL_HOD, size=8, color="065F46")
    _hcell(ws, 3, 6, "% HOD",        FILL_HOD, size=8, color="065F46")

    for i, (xl, mo_ta) in enumerate(xl_info, 4):
        nv_c  = nv_counts[xl]
        hod_c = hod_counts[xl]
        fill = xl_fills.get(xl)
        _dcell(ws, i, 1, xl,    fill=fill, bold=True, h="center")
        _dcell(ws, i, 2, mo_ta, fill=fill, h="left")
        _dcell(ws, i, 3, nv_c,  fill=FILL_NV,  bold=True, h="center")
        pct_nv  = f"{nv_c/total_persons*100:.0f}%" if total_persons else "—"
        pct_hod = f"{hod_c/total_persons*100:.0f}%" if total_persons else "—"
        _dcell(ws, i, 4, pct_nv,  fill=FILL_NV,  h="center")
        _dcell(ws, i, 5, hod_c, fill=FILL_HOD, bold=True, h="center")
        _dcell(ws, i, 6, pct_hod, fill=FILL_HOD, h="center")
        ws.row_dimensions[i].height = 18

    ws.row_dimensions[9].height = 8  # spacer

    # ══════════════════════════════════════════════════════════════════
    # PHẦN 2 (rows 10+): BẢNG CHI TIẾT
    # ══════════════════════════════════════════════════════════════════
    # Layout (1-indexed):
    #  1-10 : Info
    # 11-12 : NV tự đánh giá (Xếp loại, Nguyện vọng bố trí)
    # 13-15 : HOD đánh giá   (Tổng điểm, Xếp loại, Đề xuất bố trí)
    # 16    : HR đánh giá (trống — bổ sung sau)
    # 17-19 : Tổng quan AI (Điểm vs đề xuất | Lệch A/B/C ≥20% | CBNV vs HR)

    def _expected_xl(score):
        if score is None: return None
        try:
            s = float(score)
        except (TypeError, ValueError):
            return None
        if s >= 90: return "A"
        if s >= 80: return "B"
        if s >= 71: return "C"
        if s >= 60: return "D"
        return "E"

    def _xl_check(tot, xl_ocr):
        expected = _expected_xl(tot)
        xl_norm  = _norm_xep_loai(xl_ocr) if xl_ocr else ""
        if expected is None or not xl_norm:
            return ""
        if expected == xl_norm:
            return f"Khớp ({xl_norm}, {tot}đ)"
        return f"{tot}đ → đúng ra là '{expected}', nhưng phiếu ghi nhận '{xl_norm}'"

    INFO    = 10
    COL_NV  = 11   # 3 cols: Tổng điểm, Xếp loại, Nguyện vọng
    COL_HOD = 14   # 3 cols: Tổng điểm, Xếp loại, Đề xuất
    COL_AI  = 17   # 4 cols: AI tổng quan
    AI_COLS = 4

    HEADER_ROW = 10
    SUBHDR_ROW = 11
    DATA_START = 12

    # ── Row 10: Info merged 2 rows, section headers ───────────────────
    INFO_HEADERS = [
        "STT", "Họ và tên", "Chức danh", "Phòng ban",
        "Thời gian\nlàm việc", "Kỳ đánh giá\ntừ", "Kỳ đánh giá\nđến",
        "Ngày đánh giá", "Người đánh giá", "Chức danh\nngười đánh giá",
    ]
    for ci in range(1, INFO + 1):
        ws.merge_cells(start_row=HEADER_ROW, start_column=ci,
                       end_row=SUBHDR_ROW,   end_column=ci)
        _hcell(ws, HEADER_ROW, ci, INFO_HEADERS[ci - 1], FILL_HEADER, size=8)

    # NV section (cols 11-13)
    ws.merge_cells(start_row=HEADER_ROW, start_column=COL_NV,
                   end_row=HEADER_ROW,   end_column=COL_NV + 2)
    _hcell(ws, HEADER_ROW, COL_NV,
           "Nhân viên tự đánh giá", FILL_NV, size=9, bold=True, color="1D4ED8")

    # HOD section (cols 13-15)
    ws.merge_cells(start_row=HEADER_ROW, start_column=COL_HOD,
                   end_row=HEADER_ROW,   end_column=COL_HOD + 2)
    _hcell(ws, HEADER_ROW, COL_HOD,
           "HOD đánh giá", FILL_HOD, size=9, bold=True, color="065F46")

    # AI section header
    ws.merge_cells(start_row=HEADER_ROW, start_column=COL_AI,
                   end_row=HEADER_ROW,   end_column=COL_AI + AI_COLS - 1)
    _hcell(ws, HEADER_ROW, COL_AI,
           "PHÂN TÍCH AI", FILL_AI, size=9, bold=True, color="92400E")

    # ── Row 11: sub-headers ───────────────────────────────────────────
    _hcell(ws, SUBHDR_ROW, COL_NV,     "Tổng điểm\n(/100đ)",    FILL_NV, size=8, color="1D4ED8")
    _hcell(ws, SUBHDR_ROW, COL_NV + 1, "Xếp loại\ntổng thể",   FILL_NV, size=8, color="1D4ED8")
    _hcell(ws, SUBHDR_ROW, COL_NV + 2, "Nguyện vọng\nbố trí",  FILL_NV, size=8, color="1D4ED8")

    _hcell(ws, SUBHDR_ROW, COL_HOD,     "Tổng điểm\n(/100đ)",   FILL_HOD, size=8, color="065F46")
    _hcell(ws, SUBHDR_ROW, COL_HOD + 1, "Xếp loại\ntổng thể",  FILL_HOD, size=8, color="065F46")
    _hcell(ws, SUBHDR_ROW, COL_HOD + 2, "Đề xuất\nbố trí",     FILL_HOD, size=8, color="065F46")

    _hcell(ws, SUBHDR_ROW, COL_AI,     "Điểm &\nĐề xuất HOD",       FILL_AI, size=8, color="92400E")
    _hcell(ws, SUBHDR_ROW, COL_AI + 1, "Sự tương đồng đánh giá\nHOD và nhân viên", FILL_AI, size=8, color="92400E")
    _hcell(ws, SUBHDR_ROW, COL_AI + 2, "Xếp loại &\nLọt khung",    FILL_AI, size=8, color="92400E")
    _hcell(ws, SUBHDR_ROW, COL_AI + 3, "Tự khai\nvs HR",            FILL_AI, size=8, color="92400E")

    ws.row_dimensions[HEADER_ROW].height = 26
    ws.row_dimensions[SUBHDR_ROW].height = 34

    # ── Data rows ──────────────────────────────────────────────────────
    for pi, (person, ov) in enumerate(zip(persons, overviews)):
        r = DATA_START + pi
        nv  = person.get("tu_danh_gia") or {}
        hod = person.get("hod") or {}

        # Info
        _dcell(ws, r,  1, pi + 1, bold=True, h="center")
        _dcell(ws, r,  2, person.get("ho_ten", ""), bold=True, h="left")
        _dcell(ws, r,  3, person.get("chuc_danh", ""), h="left", wrap=True)
        _dcell(ws, r,  4, person.get("phong_ban", ""), h="left", wrap=True)
        _dcell(ws, r,  5, person.get("thoi_gian_lam_viec", ""), h="center", size=8)
        _dcell(ws, r,  6, person.get("ky_danh_gia_tu", ""), h="center", size=8)
        _dcell(ws, r,  7, person.get("ky_danh_gia_den", ""), h="center", size=8)
        _dcell(ws, r,  8, person.get("ngay_danh_gia", ""), h="center", size=8)
        _dcell(ws, r,  9, person.get("nguoi_danh_gia", ""), h="left", wrap=True)
        _dcell(ws, r, 10, person.get("chuc_danh_nguoi_danh_gia", ""), h="left", wrap=True, size=8)

        # NV tự đánh giá
        nv_tot = nv.get("tong_hop", {}).get("tong_diem_100")
        nv_xl  = nv.get("tong_hop", {}).get("xep_loai", "")
        nv_nv  = (nv.get("ket_qua_va_de_xuat") or {}).get("nguyen_vong_nhan_vien", "")
        _dcell(ws, r, COL_NV,
               nv_tot if nv_tot is not None else "",
               fill=xl_fills.get(nv_xl, FILL_NV), bold=True, h="center")
        _dcell(ws, r, COL_NV + 1,
               nv_xl, fill=xl_fills.get(nv_xl, FILL_NV), bold=True, h="center")
        _dcell(ws, r, COL_NV + 2,
               nv_nv, fill=FILL_NV, h="left", wrap=True, size=8)

        # HOD đánh giá
        hod_tot = hod.get("tong_hop", {}).get("tong_diem_100")
        hod_xl  = hod.get("tong_hop", {}).get("xep_loai", "")
        hod_dx  = (hod.get("ket_qua_va_de_xuat") or {}).get("de_xuat_bo_tri", "")
        _dcell(ws, r, COL_HOD,
               hod_tot if hod_tot is not None else "",
               fill=xl_fills.get(hod_xl, FILL_HOD), bold=True, h="center")
        _dcell(ws, r, COL_HOD + 1,
               hod_xl, fill=xl_fills.get(hod_xl, FILL_HOD), bold=True, h="center")
        _dcell(ws, r, COL_HOD + 2,
               hod_dx, fill=FILL_HOD, h="left", wrap=True, size=8)

        # AI overview
        nv_th  = nv.get("tong_hop", {})
        hod_th = hod.get("tong_hop", {})
        nv_xl_check  = _xl_check(nv_th.get("tong_diem_100"),  nv_th.get("xep_loai"))
        hod_xl_check = _xl_check(hod_th.get("tong_diem_100"), hod_th.get("xep_loai"))
        xl_check_text = "\n".join(filter(None, [
            f"NV: {nv_xl_check}"   if nv_xl_check  else "",
            f"HOD: {hod_xl_check}" if hod_xl_check else "",
        ]))
        lot_khung_text = ov.get("lot_khung", "")
        khop_khung = "\n".join(filter(None, [xl_check_text, lot_khung_text]))

        _dcell(ws, r, COL_AI,     ov.get("diem_vs_de_xuat", ""), fill=FILL_AI, h="left", wrap=True, size=8)
        _dcell(ws, r, COL_AI + 1, ov.get("lech_diem", ""),        fill=FILL_AI, h="left", wrap=True, size=8)
        _dcell(ws, r, COL_AI + 2, khop_khung,                      fill=FILL_AI, h="left", wrap=True, size=8)
        _dcell(ws, r, COL_AI + 3, ov.get("nhat_quan", ""),         fill=FILL_AI, h="left", wrap=True, size=8)

        ws.row_dimensions[r].height = 48

    # ── Column widths ──────────────────────────────────────────────────
    INFO_WIDTHS = [5, 22, 18, 14, 14, 12, 12, 13, 20, 16]
    for ci, w in enumerate(INFO_WIDTHS, 1):
        ws.column_dimensions[get_column_letter(ci)].width = w
    ws.column_dimensions[get_column_letter(COL_NV)].width     = 11
    ws.column_dimensions[get_column_letter(COL_NV + 1)].width = 10
    ws.column_dimensions[get_column_letter(COL_NV + 2)].width = 22
    ws.column_dimensions[get_column_letter(COL_HOD)].width     = 11
    ws.column_dimensions[get_column_letter(COL_HOD + 1)].width = 10
    ws.column_dimensions[get_column_letter(COL_HOD + 2)].width = 22
    for i in range(AI_COLS):
        ws.column_dimensions[get_column_letter(COL_AI + i)].width = 28

    ws.freeze_panes = f"C{DATA_START}"

    # ── Sheet 2: CBNV tu khai vs HR chenh lech ────────────────────────
    if hr_data:
        ws2 = wb.create_sheet("Chênh lệch CBNV vs HR")

        ws2.merge_cells("A1:F1")
        c = ws2.cell(row=1, column=1,
                     value="DANH SÁCH CBNV TỰ KHAI KHÔNG KHỚP DỮ LIỆU HR")
        c.font      = _font(bold=True, size=12, color="FFFFFF")
        c.alignment = _align(h="center")
        c.fill      = FILL_TITLE
        ws2.row_dimensions[1].height = 28

        s2_hdrs   = ["STT", "Họ và tên", "Chỉ tiêu", "CBNV tự khai", "HR xác nhận", "Ghi chú (chênh lệch)"]
        s2_fills  = [FILL_HEADER, FILL_HEADER, FILL_HEADER, FILL_NV, FILL_HOD, FILL_AI]
        s2_colors = ["FFFFFF",    "FFFFFF",     "FFFFFF",    "1D4ED8", "065F46",  "92400E"]
        for ci2, (hdr2, f2, col2) in enumerate(zip(s2_hdrs, s2_fills, s2_colors), 1):
            c2 = ws2.cell(row=2, column=ci2, value=hdr2)
            c2.font      = _font(bold=True, size=9, color=col2)
            c2.alignment = _align(h="center")
            c2.border    = _border()
            c2.fill      = f2
        ws2.row_dimensions[2].height = 22

        row2 = 3
        stt2 = 0
        for person2 in persons:
            ho_ten2  = person2.get("ho_ten", "")
            hr_row2  = hr_data.get(_norm_name(ho_ten2), {})
            if not hr_row2:
                continue
            nv_data2 = person2.get("tu_danh_gia") or {}
            diffs2   = _compare_nv_hr(nv_data2, hr_row2)
            if not diffs2:
                continue
            stt2 += 1
            first_r = row2
            for d in diffs2:
                nv_v  = d["nv_val"]
                hr_v  = d["hr_val"]
                ch    = d.get("chenh")
                if ch is not None:
                    direction = "NV khai cao hơn" if ch > 0 else "NV khai thấp hơn"
                    ghi_chu = f"Chênh {abs(ch)} ({direction})"
                else:
                    ghi_chu = f"NV: {nv_v} / HR: {hr_v}"

                for ci2 in range(1, 7):
                    c2 = ws2.cell(row=row2, column=ci2)
                    c2.border    = _border()
                    c2.font      = _font(size=9)
                    c2.alignment = _align(h="left" if ci2 in (3, 6) else "center")
                ws2.cell(row=row2, column=3).value = d["noi_dung"]
                nv_c = ws2.cell(row=row2, column=4)
                nv_c.value = nv_v; nv_c.fill = FILL_NV; nv_c.font = _font(size=9, bold=True)
                hr_c = ws2.cell(row=row2, column=5)
                hr_c.value = hr_v; hr_c.fill = FILL_HOD; hr_c.font = _font(size=9, bold=True)
                gc_c = ws2.cell(row=row2, column=6)
                gc_c.value = ghi_chu; gc_c.fill = FILL_AI
                ws2.row_dimensions[row2].height = 18
                row2 += 1

            if row2 - first_r > 1:
                ws2.merge_cells(start_row=first_r, start_column=1,
                                end_row=row2 - 1, end_column=1)
                ws2.merge_cells(start_row=first_r, start_column=2,
                                end_row=row2 - 1, end_column=2)
            c_stt = ws2.cell(row=first_r, column=1)
            c_stt.value = stt2; c_stt.font = _font(bold=True, size=9)
            c_stt.alignment = _align(h="center", v="center")
            c_stt.fill = _fill("F0F9FF"); c_stt.border = _border()
            c_nm = ws2.cell(row=first_r, column=2)
            c_nm.value = ho_ten2; c_nm.font = _font(bold=True, size=9)
            c_nm.alignment = _align(h="left", v="top")
            c_nm.fill = _fill("F0F9FF"); c_nm.border = _border()

        if stt2 == 0:
            ws2.merge_cells("A3:F3")
            c = ws2.cell(row=3, column=1, value="Tất cả CBNV tự khai khớp với dữ liệu HR")
            c.font = _font(bold=True, size=10, color="065F46")
            c.alignment = _align(h="center")
            c.fill = _fill("D1FAE5")

        for ci2, w2 in enumerate([6, 24, 44, 12, 12, 34], 1):
            ws2.column_dimensions[get_column_letter(ci2)].width = w2
        ws2.freeze_panes = "C3"

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()
