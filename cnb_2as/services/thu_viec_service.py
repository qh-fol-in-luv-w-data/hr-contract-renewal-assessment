# Copyright (c) 2025, antruong and contributors
# For license information, please see license.txt

"""Service layer for thu-viec (probation/traineeship) evaluation workflows.

Provides parsing, session management, KPI analysis, and prompt building.
Public API endpoints remain in api/thu_viec.py.
"""

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

from cnb_2as.services.thu_viec_parsers import (
    _parse_pdf_for_docx,
    _parse_pdf_for_xlsx,
    _parse_docx,
    _extract_nhanvien_from_docx,
    _parse_xlsx,
    _extract_nhanvien_from_xlsx,
    _extract_sections,
)

from cnb_2as.services.prompts import (
    _SYSTEM_PROMPT,
    _CHAT_SYSTEM,
)


# ── Session constants ─────────────────────────────────────────────────────────
_SESSION_PREFIX = "cnb_thu_viec_session:"
_SESSION_TTL    = 86400  # 24 giờ

# ── Tiêu chí được phép (7 mã) ─────────────────────────────────────────────────
_ALLOWED_CRITERIA = {"W1", "W2", "W3", "E1", "E2", "E3", "X1"}

# ── OpenAI client ─────────────────────────────────────────────────────────────
_client: OpenAI | None = None



_RECHECK_PROMPT_TPL = """Nhân viên đã chỉnh sửa và upload file mới. Nhiệm vụ: Dựa vào PHẦN THAY ĐỔI (diff) giữa file cũ và file mới, xác định TỪNG VẤN ĐỀ gốc đã được khắc phục chưa.
TUYỆT ĐỐI không tìm thêm lỗi mới. Chỉ đánh giá đúng các vấn đề được liệt kê.

CÁCH ĐỌC DIFF:
- Dòng bắt đầu bằng "+" = nội dung MỚI được thêm vào.
- Dòng bắt đầu bằng "-" = nội dung CŨ bị xóa đi.
- Dòng không có prefix = context (không thay đổi, dùng để định vị).
- Nếu diff hiện "(Nội dung KHÔNG THAY ĐỔI)" → file đó không được chỉnh sửa.

CÁCH KIỂM TRA TỪNG VẤN ĐỀ:
1. Đọc mô tả vấn đề gốc có gán [ID-N].
2. Tìm trong DIFF xem phần liên quan đến vấn đề đó có thay đổi không.
3. Đọc nội dung MỚI (+) ở phần thay đổi đó — đây là bằng chứng sửa đổi.
4. So sánh: nội dung mới có giải quyết đúng yêu cầu không?
5. Chỉ "đã khắc phục" khi có BẰNG CHỨNG RÕ RÀNG trong diff (dòng "+"). Nếu nghi ngờ → vẫn giữ lỗi.

DANH SÁCH VẤN ĐỀ GỐC CẦN KIỂM TRA LẠI (MỖI VẤN ĐỀ CÓ [ID-N] — KHÔNG ĐƯỢC BỎ SÓT BẤT KỲ ID NÀO):
{pending_issues_text}

════════════════════════════════════════
DIFF FILE WORD – TỔNG QUAN (cũ → mới):
════════════════════════════════════════
{docx_diff}

════════════════════════════════════════
DIFF FILE WORD – THEO TỪNG TUẦN (quan trọng cho W3):
════════════════════════════════════════
{weekly_diff}

════════════════════════════════════════
DIFF FILE EXCEL – BẢNG KPI (cũ → mới):
════════════════════════════════════════
{xlsx_diff}

════════════════════════════════════════
TOÀN VĂN FILE WORD MỚI (đọc thêm nếu cần context):
════════════════════════════════════════
{docx_text}

════════════════════════════════════════
TOÀN BỘ BẢNG KPI EXCEL MỚI (đọc thêm nếu cần):
════════════════════════════════════════
{xlsx_text}

════════════════════════════════════════
PHÂN TÍCH SƠ BỘ EXCEL MỚI:
════════════════════════════════════════
{kpi_summary}

QUY TẮC NGHIÊM NGẶT:
- Với mỗi vấn đề: phải tìm trong DIFF xem phần đó có thay đổi không, trích dẫn dòng "+" làm bằng chứng.
- Nếu đã khắc phục RÕ RÀNG và CÓ BẰNG CHỨNG (dòng "+") → đưa ID đó vào "da_fix_ids", KHÔNG đưa vào van_de.
- Nếu CHƯA khắc phục, sửa sai chỗ, hoặc diff không thay đổi ở vị trí đó → KHÔNG đưa ID vào "da_fix_ids", GIỮ NGUYÊN trong van_de.
- Nếu diff hiện "(Nội dung KHÔNG THAY ĐỔI)" hoặc "(KHÔNG THAY ĐỔI)" → coi tất cả lỗi loại đó là CHƯA khắc phục.
- KHÔNG thêm vấn đề mới ngoài danh sách gốc trên.
- Lỗi Word chỉ fix được bằng diff Word mới. Lỗi Excel chỉ fix được bằng diff Excel mới.
- Với lỗi W3 (tuần): kiểm tra "DIFF THEO TỪNG TUẦN". Tuần X "KHÔNG THAY ĐỔI" → lỗi W3 của tuần X CHƯA fix.
  Chỉ cho pass lỗi W3 tuần X khi thấy dòng "+" trong diff của tuần X đó.

Trả về JSON (ĐẦY ĐỦ, KHÔNG bỏ sót field nào):
{{
  "status": "ĐẠT" | "CHƯA ĐẠT – CẦN BỔ SUNG",
  "tong_quan": "Nhận xét ngắn: đã fix được gì (trích dẫn dòng + từ diff), còn gì chưa",
  "van_de": [ ... (chỉ các vấn đề CHƯA được khắc phục, ghi rõ lý do) ],
  "uu_diem": [ ... ],
  "luu_y_chung": "...",
  "da_fix_ids": [1, 3, 5],
  "chi_tiet_kiem_tra": [
    {{
      "id": 1,
      "da_khac_phuc": true,
      "bang_chung": "Trích dẫn dòng '+' từ diff chứng minh đã fix"
    }},
    {{
      "id": 2,
      "da_khac_phuc": false,
      "ly_do": "Không thấy thay đổi liên quan trong diff / nội dung vẫn sai"
    }}
  ]
}}

QUAN TRỌNG:
- "da_fix_ids": chỉ liệt kê ID số đã được khắc phục CÓ BẰNG CHỨNG trong diff. ID nào KHÔNG có → tự động giữ lại là lỗi.
- "chi_tiet_kiem_tra": PHẢI có entry cho TẤT CẢ các ID từ danh sách gốc. Không được bỏ sót ID nào.
- Nếu tất cả vấn đề đã được khắc phục: status = "ĐẠT", van_de = [], da_fix_ids chứa tất cả ID.
"""



def _get_client() -> OpenAI:
    global _client
    if _client is None:
        key = os.getenv("OPENAI_API_KEY", "")
        # Fallback: đọc từ site_config.json nếu .env không có
        if not key:
            key = getattr(frappe.conf, "openai_api_key", "") or ""
        if not key:
            frappe.throw("Chưa cấu hình OPENAI_API_KEY trong .env hoặc site_config.json")
        _client = OpenAI(api_key=frappe.conf.get("openai_api_key", ""))
    return _client


def _log_tokens(resp, label: str = "") -> None:
    """In token usage ra console và frappe logger sau mỗi lần gọi OpenAI."""
    usage = resp.usage
    if not usage:
        return
    model = resp.model or os.getenv("OPENAI_MODEL", "gpt-4o")
    msg = (
        f"[TOKEN] {label} | model={model} "
        f"| prompt={usage.prompt_tokens} "
        f"| completion={usage.completion_tokens} "
        f"| total={usage.total_tokens}"
    )
    try:
        print(msg, flush=True)  # hiện trong terminal bench
    except BrokenPipeError:
        pass  # stdout pipe đóng khi dùng bench serve – bỏ qua, không ảnh hưởng response
    frappe.logger("cnb_token").info(msg)


def _compute_canh_bao_han_real(ngay_het_han_str: str) -> dict:
    """Override canh_bao_han từ LLM bằng giá trị tính toán thực tế từ ngày hôm nay."""
    import datetime
    if not ngay_het_han_str:
        return {"ngay_het_han": "", "tinh_trang": "Không xác định",
                "mo_ta": "Không tìm thấy ngày hết hạn thử việc trong hồ sơ."}
    for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"]:
        try:
            d = datetime.datetime.strptime(ngay_het_han_str.strip(), fmt).date()
            today = datetime.date.today()
            delta = (d - today).days
            if delta < 0:
                return {
                    "ngay_het_han": ngay_het_han_str,
                    "tinh_trang": "Đã trễ hạn",
                    "mo_ta": f"Ngày hết hạn thử việc {ngay_het_han_str} đã qua {abs(delta)} ngày. Cần xử lý quyết định nhân sự ngay.",
                }
            if delta <= 7:
                return {
                    "ngay_het_han": ngay_het_han_str,
                    "tinh_trang": "Sắp hết hạn (<7 ngày)",
                    "mo_ta": f"Còn {delta} ngày đến hạn thử việc ({ngay_het_han_str}). Cần hoàn tất thủ tục gấp.",
                }
            return {
                "ngay_het_han": ngay_het_han_str,
                "tinh_trang": "Còn thời gian",
                "mo_ta": f"Ngày hết hạn thử việc là {ngay_het_han_str}, còn {delta} ngày để hoàn tất các thủ tục cần thiết.",
            }
        except ValueError:
            continue
    return {"ngay_het_han": ngay_het_han_str, "tinh_trang": "Không xác định",
            "mo_ta": "Không đọc được định dạng ngày hết hạn."}


def _ensure_viec_can_lam(result: dict, ket_qua_tv: str = "") -> list:
    """Đảm bảo viec_can_lam luôn có ít nhất 3 mục. Generate từ van_de nếu LLM bỏ qua."""
    existing = result.get("viec_can_lam") or []
    if existing:
        return existing
    items = []
    # Từ danh sách van_de
    for vd in (result.get("van_de") or []):
        yeu_cau = vd.get("yeu_cau") or vd.get("van_de") or ""
        if yeu_cau:
            items.append({"title": yeu_cau, "urgent": bool(vd.get("urgent")),
                          "mo_ta": vd.get("van_de", "")})
    # Từ tiêu chí 2AS chưa đạt
    for tc in (result.get("phan_tich_2as") or []):
        kq = tc.get("ket_qua", "")
        if "CẦN" in kq or "CHƯA" in kq:
            items.append({"title": f"Bổ sung tiêu chí: {tc.get('tieu_chi', '')}",
                          "urgent": False, "mo_ta": tc.get("nhan_xet", "")})
    # Fallback defaults dựa trên kết quả đề xuất
    if not items:
        if "Đạt" in ket_qua_tv or not ket_qua_tv:
            items = [
                {"title": "Chuẩn bị và ký hợp đồng lao động chính thức", "urgent": True,
                 "mo_ta": "Liên hệ phòng Nhân sự để chuẩn bị ký HĐLĐ chính thức."},
                {"title": "Lưu hồ sơ thử việc vào hệ thống", "urgent": False,
                 "mo_ta": "Upload phiếu đánh giá đã ký và Excel KPI vào hệ thống lưu trữ nhân sự."},
                {"title": "Thông báo kết quả thử việc cho nhân viên", "urgent": False,
                 "mo_ta": "Gặp mặt hoặc gửi email thông báo chính thức kết quả thử việc."},
            ]
        else:
            items = [
                {"title": "Thu thập tài liệu bổ sung theo yêu cầu", "urgent": True,
                 "mo_ta": "Liên hệ nhân viên để bổ sung các giấy tờ còn thiếu trong hồ sơ."},
                {"title": "Lên kế hoạch gia hạn hoặc kết thúc thử việc", "urgent": True,
                 "mo_ta": "Họp với HOD để thống nhất phương án xử lý nhân sự phù hợp."},
                {"title": "Cập nhật trạng thái hồ sơ vào hệ thống", "urgent": False,
                 "mo_ta": "Đánh dấu trạng thái hồ sơ và ghi chú lý do trong hệ thống quản lý nhân sự."},
            ]
    return items[:5]


def _compute_text_diff(old_text: str, new_text: str, context_lines: int = 4) -> str:
    """Tính unified diff giữa nội dung Word cũ và mới.
    Trả về string diff (có +/- prefix) để đưa vào prompt.
    """
    if not old_text and not new_text:
        return "(Không có nội dung)"
    if not old_text:
        return "(Lần đầu upload — không có file cũ để so sánh)"
    if old_text == new_text:
        return "(Nội dung KHÔNG THAY ĐỔI so với lần trước)"

    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)
    diff_lines = list(difflib.unified_diff(
        old_lines, new_lines,
        fromfile="[File Word cũ]",
        tofile="[File Word mới]",
        lineterm="",
        n=context_lines,
    ))
    if not diff_lines:
        return "(Nội dung KHÔNG THAY ĐỔI so với lần trước)"

    diff_text = "\n".join(diff_lines)
    MAX = 7000
    if len(diff_text) > MAX:
        diff_text = diff_text[:MAX] + "\n... (diff bị cắt bớt do quá dài)"
    return diff_text


def _compute_kpi_diff(old_rows: list, new_rows: list) -> str:
    """So sánh bảng KPI cũ và mới (theo STT).
    Trả về mô tả ngắn gọn những gì đã thay đổi.
    """
    if not old_rows:
        return "(Lần đầu upload Excel — không có dữ liệu cũ để so sánh)"

    old_map = {r["stt"]: r for r in old_rows}
    new_map = {r["stt"]: r for r in new_rows}

    lines = []
    all_stts = sorted(set(list(old_map.keys()) + list(new_map.keys())))
    changed = False

    for stt in all_stts:
        old = old_map.get(stt)
        new = new_map.get(stt)
        if old is None:
            lines.append(f"[MỚI THÊM] STT {stt} – {new.get('cong_viec', '')[:50]}")
            changed = True
            continue
        if new is None:
            lines.append(f"[ĐÃ XÓA] STT {stt} – {old.get('cong_viec', '')[:50]}")
            changed = True
            continue

        row_changes = []
        # So sánh link minh chứng
        old_link = (old.get("minh_chung") or old.get("link_minh_chung") or "").strip()
        new_link = (new.get("minh_chung") or new.get("link_minh_chung") or "").strip()
        if old_link != new_link:
            row_changes.append(
                f"  Link minh chứng: '{old_link or '(trống)'}' → '{new_link or '(trống)'}'"
            )
        # So sánh tỷ lệ
        if old.get("ty_le_thuc_hien") != new.get("ty_le_thuc_hien"):
            row_changes.append(
                f"  Tỷ lệ KPI: {old.get('ty_le_thuc_hien')} → {new.get('ty_le_thuc_hien')}"
            )
        # So sánh kết quả
        old_kq = (str(old.get("ket_qua") or "")).strip()
        new_kq = (str(new.get("ket_qua") or "")).strip()
        if old_kq != new_kq:
            row_changes.append(
                f"  Kết quả KPI: '{old_kq or '(trống)'}' → '{new_kq or '(trống)'}'"
            )
        # So sánh trạng thái
        old_status = old.get("status", "")
        new_status = new.get("status", "")
        if old_status != new_status:
            row_changes.append(f"  Trạng thái: {old_status} → {new_status}")

        if row_changes:
            lines.append(f"STT {stt} – {new.get('cong_viec', '')[:50]}:")
            lines.extend(row_changes)
            changed = True

    if not changed:
        return "(Bảng KPI KHÔNG THAY ĐỔI so với lần trước)"
    return "\n".join(lines)


def _compute_weekly_diff(old_sections: dict, new_sections: dict) -> str:
    """So sánh nội dung từng tuần (Tuần 1-8) giữa file Word cũ và mới.
    Trả về mô tả chi tiết những gì thay đổi theo từng tuần.
    """
    old_tuan_list = old_sections.get("ds_tuan") or []
    new_tuan_list = new_sections.get("ds_tuan") or []
    all_tuans = sorted(set(old_tuan_list + new_tuan_list))

    if not all_tuans:
        return "(Không tìm thấy dữ liệu tuần trong file Word)"

    lines = []
    changed = False

    for t in all_tuans:
        key = f"tuan_{t}"
        old_content = (old_sections.get(key) or "").strip()
        new_content = (new_sections.get(key) or "").strip()

        if not old_content and not new_content:
            continue
        if not old_content:
            lines.append(f"[TUẦN {t}] MỚI THÊM:")
            lines.append(new_content[:800])
            changed = True
            continue
        if not new_content:
            lines.append(f"[TUẦN {t}] ĐÃ XÓA (không còn trong file mới)")
            changed = True
            continue
        if old_content == new_content:
            lines.append(f"[TUẦN {t}] KHÔNG THAY ĐỔI")
            continue

        # Có thay đổi → hiện unified diff ngắn
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        import difflib
        diff_lines = list(difflib.unified_diff(
            old_lines, new_lines,
            fromfile=f"Tuần {t} cũ",
            tofile=f"Tuần {t} mới",
            lineterm="",
            n=2,
        ))
        if diff_lines:
            lines.append(f"[TUẦN {t}] ĐÃ THAY ĐỔI:")
            lines.append("\n".join(diff_lines[:40]))  # giới hạn 40 dòng diff mỗi tuần
            changed = True
        else:
            lines.append(f"[TUẦN {t}] KHÔNG THAY ĐỔI")

    if not changed:
        return "(Tất cả các tuần KHÔNG THAY ĐỔI so với lần trước)"

    return "\n\n".join(lines)


def _extract_sections(full_text: str) -> dict:
    """
    Trích xuất các phần quan trọng từ text Word để AI dễ cross-check:
    - nhiem_vu_thuc_hien: phần mô tả công việc đã làm
    - kpi_tuan: toàn bộ phần KPI tuần (tất cả các tuần)
    - tuan_{n}: nội dung riêng của từng tuần (Tuần 1 → 8)
    - so_tuan: số tuần phát hiện được
    """
    import re as _re_sec
    text_lower = full_text.lower()
    sections = {}

    # ― Phần nhiệm vụ đã thực hiện ―
    kw_nhiem_vu = [
        "các công việc ứng viên đã thực hiện được",
        "công việc ứng viên đã thực hiện",
        "nhiệm vụ đã thực hiện",
        "công việc đã thực hiện",
        "các công việc đã làm",
        "nội dung công việc đã thực hiện",
        "các đầu việc đã thực hiện",
        "kết quả công việc",
        "nhiệm vụ, kết quả thực tế",
    ]
    for kw in kw_nhiem_vu:
        idx = text_lower.find(kw)
        if idx != -1:
            sections["nhiem_vu_thuc_hien"] = full_text[max(0, idx - 50):idx + 5000]
            break

    # ― Phần KPI tuần – tìm điểm bắt đầu ―
    kw_kpi_tuan = [
        "kpi tuần", "kết quả kpi tuần", "báo cáo kpi tuần",
        "tuần 1", "tuần thứ 1", "tuần thứnhất",
        "nhiệm vụ đặt ra", "sản phẩm đặt ra",
        "kế hoạch tuần",
    ]
    kpi_tuan_start = -1
    for kw in kw_kpi_tuan:
        idx = text_lower.find(kw)
        if idx != -1:
            kpi_tuan_start = max(0, idx - 50)
            break

    if kpi_tuan_start != -1:
        # Lấy tối đa 12000 ký tự để bắt đủ 8 tuần
        sections["kpi_tuan"] = full_text[kpi_tuan_start:kpi_tuan_start + 12000]

    # ― Parse từng tuần riêng biệt (Tuần 1 → 8) ―
    # Nhận diện header tuần theo nhiều dạng: "Tuần 1", "TUẦN 1", "Tuần thứ 1", "Tuần thứ nhất"...
    tuan_patterns = [
        r"tu\w*n\s*(?:th\w*\s*)?(\d+)",            # "tuần 1", "tuần thứ 1", "tuần thứ1", "tuan 1"
        r"tu\w*n\s*(?:th\w*\s*)?(?:nh\w*t|m\w*t)\b",  # "tuần nhất", "tuần thứ nhất"
        r"week\s*(\d+)",                                # "week 1" (phòng có tiếng Anh)
    ]
    # Số từ chữ → số
    word_to_num = {
        "nhất": 1, "một": 1, "hai": 2, "ba": 3, "bốn": 4,
        "năm": 5, "sáu": 6, "bảy": 7, "tám": 8, "chín": 9,
    }

    # Tìm tất cả vị trí header tuần trong full_text
    tuan_positions = []  # list of (tuan_num, start_idx)
    seen_nums = set()
    for pattern in tuan_patterns:
        for m in _re_sec.finditer(pattern, text_lower, _re_sec.UNICODE):
            g1 = m.group(1) if m.lastindex and m.group(1) else None
            if g1 and g1.isdigit():
                tuan_num = int(g1)
            else:
                # thử parse chữ
                matched_word = m.group(0).split()[-1]
                tuan_num = word_to_num.get(matched_word, None)
            if tuan_num and 1 <= tuan_num <= 8 and tuan_num not in seen_nums:
                seen_nums.add(tuan_num)
                tuan_positions.append((tuan_num, m.start()))

    # Sắp xếp theo vị trí trong văn bản
    tuan_positions.sort(key=lambda x: x[1])

    # Cắt nội dung từng tuần: từ header tuần N đến header tuần N+1 (hoặc cuối đoạn kpi)
    kpi_end = kpi_tuan_start + 12000 if kpi_tuan_start != -1 else len(full_text)
    for i, (tuan_num, start) in enumerate(tuan_positions):
        if i + 1 < len(tuan_positions):
            end = tuan_positions[i + 1][1]
        else:
            end = min(start + 3000, kpi_end)  # tuần cuối: lấy tối đa 3000 ký tự
        sections[f"tuan_{tuan_num}"] = full_text[start:end].strip()

    sections["so_tuan"] = len(tuan_positions)
    sections["ds_tuan"] = sorted(seen_nums)  # danh sách tuần tìm được

    return sections


def _check_e1_deterministic(e1_issues: list, new_kpi_rows: list) -> tuple:
    """Kiểm tra xác định (KHÔNG dùng AI) các lỗi E1 (thiếu minh chứng).
    So sánh trực tiếp với dữ liệu parser từ Excel mới.
    Trả về (da_fix: list, van_de: list).
    """
    import re as _re2
    new_kpi_map = {r["stt"]: r for r in new_kpi_rows}
    da_fix = []
    van_de = []

    for issue in e1_issues:
        muc = str(issue.get("muc", ""))
        # Parse STT từ muc: "STT 1 – tên" hoặc "STT 1"
        stt = None
        m = _re2.match(r"STT\s*(\d+)", muc)
        if m:
            stt = int(m.group(1))

        if stt is not None and stt in new_kpi_map:
            row = new_kpi_map[stt]
            link = (row.get("minh_chung") or row.get("link_minh_chung") or "").strip()
            has_link = bool(link) and link not in ("", "`", "None", "-", "_", "N/A")
            if has_link:
                da_fix.append(issue)
            else:
                van_de.append(issue)
        else:
            # Không tìm được STT → giữ nguyên là lỗi (an toàn)
            van_de.append(issue)

    return da_fix, van_de


def _filter_result(result: dict) -> dict:
    """Lọc cứng: chỉ giữ lại các vấn đề thuộc đúng 7 mã tiêu chí đã chốt.
    Bất kỳ mã nào ngoài _ALLOWED_CRITERIA đều bị xóa khỏi kết quả.
    Bổ sung: deduplicate X1 — cùng task name chỉ giữ 1 issue.
    (Không dùng string-matching/regex để phán đoán nội dung — để AI quyết định.)
    """
    if not isinstance(result, dict):
        return result
    van_de = result.get("van_de", [])
    if not van_de:
        return result

    def _is_allowed(v: dict) -> bool:
        if not isinstance(v, dict):
            return False
        ntc = str(v.get("nhom_tieu_chi", "")).upper().strip().rstrip(".")
        return ntc in _ALLOWED_CRITERIA

    filtered = [v for v in van_de if _is_allowed(v)]

    # ── X1 dedup: cùng task name (muc) chỉ giữ 1 issue ────────────────
    x1_seen_tasks: set = set()
    final: list = []
    for v in filtered:
        ntc = str(v.get("nhom_tieu_chi", "")).upper().strip().rstrip(".")
        if ntc != "X1":
            final.append(v)
            continue
        task_key = str(v.get("muc") or "").strip().lower()[:60]
        if task_key and task_key in x1_seen_tasks:
            continue  # đã có issue cho task này rồi — bỏ duplicate
        x1_seen_tasks.add(task_key)
        final.append(v)

    result["van_de"] = final
    return result


def _filter_recheck_issues(re_review: dict, original_issues: list) -> dict:
    """Hard filter: sau khi AI recheck, chỉ giữ lại issue có nhom_tieu_chi
    khớp với ít nhất một issue trong danh sách gốc (pending_issues).
    Ngăn AI tự thêm lỗi mới khi recheck dù system prompt đã cấm.
    """
    if not isinstance(re_review, dict) or not original_issues:
        return re_review
    # Tập hợp các (nhom_tieu_chi) có trong pending gốc
    allowed_ntc = {
        str(v.get("nhom_tieu_chi", "")).upper().strip().rstrip(".")
        for v in original_issues
        if isinstance(v, dict)
    }
    van_de = re_review.get("van_de", [])
    re_review["van_de"] = [
        v for v in van_de
        if str(v.get("nhom_tieu_chi", "")).upper().strip().rstrip(".") in allowed_ntc
    ]
    return re_review


def _get_session(session_id: str) -> dict:
    """Lấy session từ Redis cache. Tạo mới nếu chưa tồn tại."""
    key = _SESSION_PREFIX + session_id
    raw = frappe.cache().get_value(key)

    # frappe.cache() đôi khi trả về string JSON thay vì dict → parse lại
    if raw is None:
        data = None
    elif isinstance(raw, str):
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            data = None
    elif isinstance(raw, dict):
        data = raw
    else:
        data = None

    if data is None:
        data = {
            "docx_text": "",
            "xlsx_data": {},
            "review": None,
            "history": [],
            "pending_issues": None,  # None = chưa review lần nào; [] = đã review, không có lỗi
        }
    return data


def _save_session(session_id: str, data: dict) -> None:
    """Lưu session vào Redis cache với TTL 24 giờ.
    Dùng json.dumps để đảm bảo consistent serialization.
    """
    key = _SESSION_PREFIX + session_id
    # Serialize tường minh → luôn là string JSON trong Redis
    frappe.cache().set_value(key, json.dumps(data, ensure_ascii=False, default=str), expires_in_sec=_SESSION_TTL)


def _build_review_prompt(eval_type, docx_parsed, xlsx_parsed,
                          daily_report_text: str = "", so_ngay_can_bc: str = ""):
    """Build the OpenAI user message prompt for thu-viec/hoc-viec review.

    Args:
        eval_type: "thu_viec" | "hoc_viec"
        docx_parsed: parsed DOCX dict (full_text, sections)
        xlsx_parsed: parsed XLSX dict (kpi_rows, full_text)
        daily_report_text: extracted text from daily report file (optional)
        so_ngay_can_bc: number of working days required as string (optional)

    Returns:
        str: formatted prompt string for the OpenAI user message
    """
    n_kpi = len(xlsx_parsed.get("kpi_rows", []))
    kpi_summary = _build_kpi_summary(xlsx_parsed)

    logger = frappe.logger("cnb_review", allow_site=True)
    logger.info(f"[REVIEW] n_kpi={n_kpi} | docx_len={len(docx_parsed.get('full_text',''))} | xlsx_len={len(xlsx_parsed.get('full_text',''))}")

    word_raw = docx_parsed.get("full_text", "")
    excel_raw = xlsx_parsed.get("full_text", "")

    user_msg = f"""
NHIỆM VỤ: Kiểm tra TOÀN BỘ hồ sơ {"học việc" if eval_type == "hoc_viec" else "thử việc"} dựa trên các file dưới đây. {n_kpi} hàng KPI Excel cần kiểm tra.


═══ FILE WORD – PHIẾU ĐÁNH GIÁ THỬ VIỆC ═══
{word_raw[:14000]}

═══ FILE EXCEL – KẾ HOẠCH KPI (TÓM TẮT) ═══
{kpi_summary}

═══ FILE EXCEL – TOÀN BỘ NỘI DUNG ═══
{excel_raw[:6000]}

═══ YÊU CẦU KIỂM TRA ═══
Đọc TOÀN BỘ nội dung Word và Excel ở trên, sau đó thực hiện ĐÚNG các kiểm tra theo bộ tiêu chí đã được cung cấp trong system prompt.

CẤU TRÚC FILE WORD – ĐỌC KỸ TRƯỚC KHI CHECK:

● Bảng trên – STT 1.1 đến 1.8:
  → CHỈ chứa % điểm KPI của từng tuần (ví dụ: "Tuần thứ 1 | 95%").
  → KHÔNG có mục "Sản phẩm đặt ra" hay "Nhiệm vụ đặt ra".
  → TUYỆT ĐỐI KHÔNG dùng bảng này để check W3.
  → KHÔNG báo "thiếu Sản phẩm đặt ra" hay "thiếu Nhiệm vụ đặt ra" dựa trên bảng này.

● Hàng 1.10 – NHIỆM VỤ VÀ KẾT QUẢ THỰC TẾ:
{chr(10).join(f"  [{i+1}] {item['ten']} | Kết quả: {item['ket_qua_pct']}" for i, item in enumerate(docx_parsed.get("sections", {}).get("nhiem_vu_ket_qua", [])))}

● Bảng dưới – STT 2.1 đến 2.8:
  → Mới có đầy đủ nội dung: "- Sản phẩm: ..." và "- Nhiệm vụ đặt ra: ...".
  → ĐÂY LÀ NGUỒN CHÍNH XÁC để check W3 (kiểm tra từng tuần có NV và SP không).
  → Chỉ báo "thiếu" khi mục đó TRỐNG HOÀN TOÀN trong bảng này.

═══ KẾT QUẢ KIỂM TRA W3 (ĐÃ TÍNH SẴN – DÙNG NGUYÊN, KHÔNG TỰ PHÁN ĐOÁN) ═══
Dưới đây là kết quả đã kiểm tra từng tuần trong bảng 2.1–2.8 của file Word.
TUYỆT ĐỐI chỉ dùng kết quả này cho W3. KHÔNG đọc bảng 1.1–1.8 để check W3.

{chr(10).join(
    (
        f"TUẦN {t}: " + (
            ("❌ THIẾU Sản phẩm đặt ra | " if not d.get('san_pham','').strip() else "✅ Sản phẩm đặt ra: CÓ | ") +
            ("❌ THIẾU Nhiệm vụ đặt ra" if not d.get('nhiem_vu','').strip() else "✅ Nhiệm vụ đặt ra: CÓ")
        ) if d else f"TUẦN {t}: ❌ KHÔNG TÌM THẤY TRONG FILE"
    )
    for t in range(1, 9)
    for d in [docx_parsed.get("sections", {}).get("weekly_table", {}).get(t)]
)}

QUY TẮC: Chỉ báo lỗi W3 khi dòng trên hiện ❌. Nếu ✅ → KHÔNG báo lỗi, dù raw text có vẻ thiếu.

═══ KẾT QUẢ KIỂM TRA E1 (ĐÃ TÍNH SẴN – DÙNG NGUYÊN, KHÔNG TỰ PHÁN ĐOÁN) ═══
Dưới đây là kết quả kiểm tra minh chứng từng STT trong Excel.
TUYỆT ĐỐI chỉ dùng kết quả này cho E1. KHÔNG tự đọc lại Excel để phán đoán.

{chr(10).join(
    f"Excel STT {r['stt']} [{r['cong_viec'][:35]}]: " + (
        f"✅ CÓ minh chứng: {r.get('minh_chung','')[:60]}"
        if (r.get('minh_chung','') or r.get('has_image'))
        else "❌ TRỐNG – Thiếu minh chứng"
    )
    for r in xlsx_parsed.get("kpi_rows", [])
)}

QUY TẮC: Chỉ báo lỗi E1 khi dòng trên hiện ❌. Nếu ✅ → KHÔNG báo lỗi E1 cho STT đó.

═══ X1 – CROSS-CHECK NHIỆM VỤ WORD ↔ EXCEL ═══
QUAN TRỌNG: Thứ tự nhiệm vụ trong Word 1.10 KHÁC thứ tự STT trong Excel.
PHẢI match theo TÊN/NỘI DUNG công việc, KHÔNG match theo index/số thứ tự.

Excel KPI (STT | Tên mảng | Mô tả sản phẩm | % thực hiện):
{chr(10).join(f"  Excel STT {r['stt']}: [{r['cong_viec']}] – {str(r.get('mo_ta',''))[:80]} | {round(float(r['ty_le_thuc_hien'])*100) if r['ty_le_thuc_hien'] else '?'}%" for r in xlsx_parsed.get("kpi_rows", []))}

Cách match: Tìm Excel STT tương ứng với mỗi Nhiệm vụ Word bằng cách so sánh nội dung.
Ví dụ: Word "Xây dựng AI Agent chấm điểm CV" ↔ Excel STT 2 "AI chấm điểm CV".

Trả về JSON theo đúng schema.
"""

    # ── Nhúc thêm phần báo cáo ngày nếu có ─────────────────────────────────────
    if daily_report_text and daily_report_text.strip():
        so_ngay_label = f"(cần có: {so_ngay_can_bc} ngày làm việc)" if so_ngay_can_bc else ""
        user_msg += f"""

═══ FILE BÁO CÁO NGÀY {so_ngay_label} ═══
{daily_report_text[:8000]}

YÊu CẦU KIỂM TRA BÁO CÁO NGÀY:
- Đếm số ngày đã có báo cáo (so_ngay_da_bc)
- So sánh với số ngày cần báo cáo {so_ngay_can_bc or "(tính từ phạm vi thử việc)"} (so_ngay_can_bc)
- Liệt kê ngày thiếu báo cáo hoàn toàn (ngay_thieu_bao_cao)
- Liệt kê ngày có báo cáo nhưng thiếu hạng mục cần thiết (ngay_thieu_hang_muc)
- Điền số ngày đầy đủ hạng mục (so_ngay_du_hang_muc)
- Nhan_xet ngắn gọn về kểt quả báo cáo ngày
"""
    else:
        user_msg += """

═══ BÁO CÁO NGÀY ═══
Không có file báo cáo ngày — đặt bao_cao_ngay = null trong kết quả.
"""

    return user_msg


def _build_kpi_summary(xlsx_data: dict) -> str:
    """Tóm tắt tình trạng từng hàng KPI để đưa vào prompt, bao gồm mô tả để AI cross-check với Word."""
    rows = xlsx_data.get("kpi_rows", [])
    if not rows:
        return "Không tìm thấy dữ liệu KPI."
    lines = []
    for r in rows:
        status = r["status"]
        issues = ", ".join(r["issues"]) if r["issues"] else "OK"
        ty_le_raw = r['ty_le_thuc_hien']
        if ty_le_raw is None:
            ty_le_str = "(trống)"
        elif isinstance(ty_le_raw, float) and ty_le_raw <= 1:
            ty_le_str = f"{round(ty_le_raw * 100)}%"
        else:
            ty_le_str = f"{ty_le_raw}"
        mo_ta_str = r['mo_ta'] or "(không có mô tả)"
        minh_chung = r.get('minh_chung') or r.get('link_minh_chung') or "(trống)"
        lines.append(
            f"STT {r['stt']} – {r['cong_viec'][:60]}:\n"
            f"  Mô tả sản phẩm: {mo_ta_str[:150]}\n"
            f"  TY_LE_KPI: {ty_le_str}\n"
            f"  Minh chứng: {minh_chung} | [{status}] {issues}"
        )
    return "\n\n".join(lines)