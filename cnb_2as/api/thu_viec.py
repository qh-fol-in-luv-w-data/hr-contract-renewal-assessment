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
from cnb_2as.services.prompts import (
    _SYSTEM_PROMPT,
    _CHAT_SYSTEM,
)


# ── OpenAI client ─────────────────────────────────────────────────────────────
_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        key = os.getenv("OPENAI_API_KEY", "")
        # Fallback: đọc từ site_config.json nếu .env không có
        if not key:
            key = getattr(frappe.conf, "openai_api_key", "") or ""
        if not key:
            frappe.throw("Chưa cấu hình OPENAI_API_KEY trong .env hoặc site_config.json")
        _client = OpenAI(api_key=key)
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


# ══════════════════════════════════════════════════════════════════════════════
# Deadline helpers – tính server-side vì LLM không biết ngày hôm nay
# ══════════════════════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════════════════════
# Diff helpers – so sánh file cũ và mới để AI recheck chính xác hơn
# ══════════════════════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════════════════════
# File parsers
# ══════════════════════════════════════════════════════════════════════════════

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


def _parse_pdf_for_docx(data: bytes) -> dict:
    """Parse PDF file and return a dict compatible with _parse_docx output.
    Extracts text from all pages and builds a minimal structure.
    """
    reader = PdfReader(io.BytesIO(data))
    pages_text = []
    for page in reader.pages:
        text = page.extract_text()
        if text and text.strip():
            pages_text.append(text.strip())
    full_text = "\n\n".join(pages_text)
    sections = _extract_sections(full_text)
    return {
        "paragraphs": pages_text,
        "tables": [],
        "full_text": full_text,
        "sections": sections,
        "nhan_vien_info": {},
    }


def _parse_pdf_for_xlsx(data: bytes) -> dict:
    """Parse PDF file and return a dict compatible with _parse_xlsx output.
    Since PDF doesn't have structured KPI rows, returns text-only data
    so AI can still process the content.
    """
    reader = PdfReader(io.BytesIO(data))
    pages_text = []
    for page in reader.pages:
        text = page.extract_text()
        if text and text.strip():
            pages_text.append(text.strip())
    full_text = "\n\n".join(pages_text)
    return {
        "headers": [],
        "rows": [],
        "missing_evidence": [],
        "full_text": full_text,
        "kpi_rows": [],
        "nhan_vien_info": {},
    }


def _parse_docx(data: bytes) -> dict:
    """
    Đọc file DOCX phiếu đánh giá thử việc.
    Trả về dict gồm:
      - paragraphs: list text đoạn văn
      - tables: list table (mỗi table là list of rows, mỗi row là list cell text)
      - full_text: toàn bộ text ghép lại dễ gửi lên AI
      - sections: các phần quan trọng đã trích xuất
    """
    import re as _re_docx

    doc = DocxDocument(io.BytesIO(data))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

    tables = []
    for tbl in doc.tables:
        rows = []
        for row in tbl.rows:
            # Lấy text từng ô — giữ từng paragraph trong ô trên dòng riêng
            cells = []
            for c in row.cells:
                # Ghép các paragraph trong 1 ô bằng "\n" để không mất xuống hàng
                cell_lines = [p.text.strip() for p in c.paragraphs if p.text.strip()]
                cells.append("\n".join(cell_lines))
            # Bỏ các row toàn rỗng
            if any(c for c in cells):
                rows.append(cells)
        if rows:
            tables.append(rows)

    # Gộp thành full text — mỗi ô cách nhau bằng " | "
    # Dòng nhiều paragraph trong ô → giữ \n (AI đọc được)
    parts = list(paragraphs)
    for i, tbl in enumerate(tables):
        parts.append(f"\n[BẢNG {i+1}]")
        for row in tbl:
            # Chuẩn hóa: thay \n trong cell bằng "↵" khi join để không vỡ cấu trúc dòng
            row_display = " | ".join(c.replace("\n", " ↵ ") for c in row)
            parts.append(row_display)

    full_text = "\n".join(parts)

    # ── Parse dữ liệu KPI tuần từ bảng Word ──────────────────────────────
    # Hỗ trợ 2 format:
    #   Format A: Mỗi hàng là 1 tuần, cột "Nội dung" chứa "Tuần thứ N\n- Sản phẩm:...\nNhiệm vụ đặt ra:..."
    #   Format B: Bảng có cột riêng "Nhiệm vụ đặt ra" và "Sản phẩm đặt ra"
    weekly_table_data = {}
    # Hàng 1.10: danh sách nhiệm vụ + kết quả thực tế % (dùng cho X1 so Excel)
    nhiem_vu_ket_qua = []   # [{stt: "Nhiệm vụ 1", ten: "...", ket_qua_pct: "90%"}, ...]
    _log = frappe.logger("cnb_parse", allow_site=True)

    for tbl_idx, tbl_raw in enumerate(doc.tables):
        # Lấy rows, dedup merged cells
        raw_rows = []
        for row in tbl_raw.rows:
            seen_tc = set()
            cells_text = []
            for c in row.cells:
                tc_id = id(c._tc)
                if tc_id in seen_tc:
                    continue  # bỏ qua merged cell lặp lại
                seen_tc.add(tc_id)
                cell_lines = [p.text.strip() for p in c.paragraphs if p.text.strip()]
                cells_text.append("\n".join(cell_lines))
            if any(cells_text):
                raw_rows.append(cells_text)

        if not raw_rows:
            continue

        # ── Parse hàng 1.10: Danh sách nhiệm vụ + kết quả thực tế ──────────
        # Hàng có STT "1.10", Col1 = "Nhiệm vụ 1: ...\nNhiệm vụ 2: ...",
        #                       Col2 = "Kết quả thực tế: 90%\nKết quả thực tế: 90%..."
        for row in raw_rows:
            if not row or len(row) < 2:
                continue
            stt = row[0].strip()
            if not _re_docx.match(r"1\.10\.?$", stt):
                continue
            col1 = row[1]  # danh sách nhiệm vụ
            col2 = row[2] if len(row) > 2 else ""  # kết quả thực tế

            # Tách từng nhiệm vụ từ col1
            nv_lines = [l.strip() for l in col1.split("\n") if l.strip()]
            # Tách từng kết quả % từ col2
            pct_lines = [l.strip() for l in col2.split("\n") if l.strip()]

            nv_items = []
            for line in nv_lines:
                m = _re_docx.match(r"(Nhi\w*m\s*v\w*\s*\d+)\s*:\s*(.+)", line, _re_docx.IGNORECASE | _re_docx.UNICODE)
                if m:
                    nv_items.append({"stt": m.group(1).strip(), "ten": m.group(2).strip()})

            # Chỉ ghép các nhiệm vụ có kết quả % tương ứng trong col2
            # → Số lượng nhiệm vụ hợp lệ = số dòng có % trong col2
            for i, pct_line in enumerate(pct_lines):
                m_pct = _re_docx.search(r"(\d+(?:[.,]\d+)?)\s*%", pct_line)
                if not m_pct:
                    continue
                pct_str = m_pct.group(0).strip()
                if i < len(nv_items):
                    nv = nv_items[i]
                    nhiem_vu_ket_qua.append({
                        "stt": nv["stt"],
                        "ten": nv["ten"],
                        "ket_qua_pct": pct_str,
                    })

            _log.info(f"[PARSE] Hàng 1.10: {len(nv_items)} nhiệm vụ, {len(pct_lines)} kết quả → {len(nhiem_vu_ket_qua)} ghép được")
            break  # chỉ cần 1 hàng 1.10

        if not raw_rows:
            continue

        # ── Format 1.x: hàng STT "1.1"→"1.8" chứa nhiệm vụ + % kề bên ──────────
        # Cấu trúc: col[0]=STT(1.x), col[1]=Nội dung nhiệm vụ, col[2]=Tỷ lệ % (CHỈ đọc col này)
        # Nếu col[2] trống → bỏ qua, không scan sang cột khác
        for row in raw_rows:
            if not row:
                continue
            stt_cell = row[0].strip()
            m_stt_1x = _re_docx.match(r"1\.(\d+)\.?$", stt_cell)
            if not m_stt_1x:
                continue
            week_idx = int(m_stt_1x.group(1))
            if not (1 <= week_idx <= 8):
                continue

            # Nội dung nhiệm vụ ở col[1]
            content_cell = row[1] if len(row) > 1 else ""
            content_norm = content_cell.replace('\xa0', ' ')

            # Tỷ lệ % CHỈ đọc từ col[2] kề bên — nếu trống thì bỏ qua, KHÔNG scan lan sang col[3+]
            ty_le_str = ""
            if len(row) > 2 and row[2]:
                col2_val = row[2].strip()
                m_pct = _re_docx.search(r"(\d+(?:[.,]\d+)?)\s*%", col2_val)
                if m_pct:
                    ty_le_str = m_pct.group(0).strip()
                elif _re_docx.match(r"^0?\.\d+$", col2_val):
                    try:
                        ty_le_str = f"{float(col2_val) * 100:.0f}%"
                    except Exception:
                        pass
                # Nếu col[2] có text nhưng không phải % → bỏ qua (không scan col khác)

            # Lưu vào weekly_table_data với key = week_idx
            if week_idx not in weekly_table_data:
                weekly_table_data[week_idx] = {
                    "tuan_header": f"Tuần {week_idx}",
                    "nhiem_vu": content_norm,
                    "san_pham": "",
                    "ty_le": ty_le_str,
                    "full_content": content_norm,
                    "stt_word": f"1.{week_idx}",  # STT gốc trong Word để map với Excel
                }
            elif ty_le_str and not weekly_table_data[week_idx].get("ty_le"):
                weekly_table_data[week_idx]["ty_le"] = ty_le_str
            _log.info(f"[PARSE-1x] STT {stt_cell}: nv={len(content_norm)} ty_le={ty_le_str!r}")

        # ── Format A: tìm hàng có STT dạng "2.1" → "2.8" và cell chứa "Tuần thứ N" ──
        format_a_found = False
        for row in raw_rows:
            if not row:
                continue
            stt_cell = row[0].strip()
            # STT dạng "2.1", "2.2", ..., "2.8"
            m_stt = _re_docx.match(r"2\.(\d+)\.?$", stt_cell)
            if not m_stt:
                continue
            week_idx = int(m_stt.group(1))
            if not (1 <= week_idx <= 8):
                continue

            # Tìm cell chứa "Tuần thứ N" hoặc "Tuần N"
            content_cell = row[1] if len(row) > 1 else ""
            
            # Parse nội dung từ cell gộp (hỗ trợ nhiều dòng \n và \xa0 non-breaking space)
            # Format thực tế: "- Sản phẩm:\xa0[text]\n- Nhiệm vụ đặt ra:\xa0[text]\n..."
            # Chuẩn hóa: thay \xa0 → space để regex dễ match
            content_norm = content_cell.replace('\xa0', ' ')

            # Tìm "Nhiệm vụ đặt ra:" — sau sản phẩm, trước các mục chi tiết
            m_nv = _re_docx.search(
                r"-?\s*Nhi\w*m\s*v\w*\s*đặt\s*ra\s*:\s*(.+?)(?=\n\s*Chi\s*tiết|\n\s*-\s*S\w*\s*l[uư]|\n\s*-\s*[Đd]|\Z)",
                content_norm, _re_docx.IGNORECASE | _re_docx.DOTALL | _re_docx.UNICODE
            )
            nv_text = m_nv.group(1).strip() if m_nv else ""

            # Tìm "- Sản phẩm:" — nội dung có thể xuống hàng nhiều dòng
            m_sp = _re_docx.search(
                r"-?\s*S\w+\s+ph\w+\s*:\s*(.+?)(?=\n\s*-?\s*Nhi\w*m\s*v|\n\s*Chi\s*tiết|\n\s*-\s*S\w*\s*l[uư]|\Z)",
                content_norm, _re_docx.IGNORECASE | _re_docx.DOTALL | _re_docx.UNICODE
            )
            sp_text = m_sp.group(1).strip() if m_sp else ""

            # Nếu không tách được → lấy toàn bộ content (bỏ dòng đầu là header tuần)
            if not nv_text and not sp_text:
                lines = content_norm.split("\n")
                body_lines = [l for l in lines[1:] if l.strip()]
                sp_text = "\n".join(body_lines)

            m_tuan = _re_docx.search(r"tu\w*n\s*(?:th\w*\s*)?(\d+)", content_cell.lower(), _re_docx.UNICODE)
            if not m_tuan:
                continue

            tuan_num = int(m_tuan.group(1))
            if not (1 <= tuan_num <= 8):
                continue

            format_a_found = True

            # Lấy tỷ lệ % từ cột kề bên (Col2)
            ty_le_str = ""
            for col_val in row[2:]:
                if not col_val:
                    continue
                m_pct = _re_docx.search(r"(\d+(?:[.,]\d+)?)\s*%", col_val)
                if m_pct:
                    ty_le_str = m_pct.group(0).strip()
                    break
                # Số thập phân dạng 0.9 / 0.95
                m_dec = _re_docx.match(r"^0?\.\d+$", col_val.strip())
                if m_dec:
                    try:
                        ty_le_str = f"{float(col_val.strip()) * 100:.0f}%"
                    except Exception:
                        pass
                    break

            if tuan_num not in weekly_table_data:
                weekly_table_data[tuan_num] = {
                    "tuan_header": f"Tuần {tuan_num}",
                    "nhiem_vu": nv_text,
                    "san_pham": sp_text,
                    "ty_le": ty_le_str,
                    "full_content": content_norm,  # bản đã chuẩn hóa \xa0→space
                }
            _log.info(f"[PARSE-A] Tuần {tuan_num} (STT {stt_cell}): nv={len(nv_text)} sp={len(sp_text)} ty_le={ty_le_str}")

        if format_a_found:
            _log.info(f"[PARSE-A] Bảng {tbl_idx+1}: Format A, tìm được {len(weekly_table_data)} tuần")
            continue  # đã parse xong format A, bỏ qua format B cho bảng này


        # ── Format B: bảng có cột header "Nhiệm vụ đặt ra" / "Sản phẩm đặt ra" ──
        col_nhiem_vu = None
        col_san_pham = None
        header_row_idx = None
        for ri, row in enumerate(raw_rows):
            row_lower = [c.lower() for c in row]
            for ci, cell in enumerate(row_lower):
                if ("nhiệm vụ" in cell or "nhiem vu" in cell) and col_nhiem_vu is None:
                    col_nhiem_vu = ci
                if ("sản phẩm" in cell or "san pham" in cell) and col_san_pham is None:
                    col_san_pham = ci
            if col_nhiem_vu is not None or col_san_pham is not None:
                header_row_idx = ri
                break

        _log.info(f"[PARSE-B] Bảng {tbl_idx+1}: header_row={header_row_idx} col_nv={col_nhiem_vu} col_sp={col_san_pham}")

        if header_row_idx is None:
            continue

        current_tuan = None
        for ri in range(header_row_idx + 1, len(raw_rows)):
            row = raw_rows[ri]
            row_text_joined = " ".join(row).lower()

            m_tuan = _re_docx.search(r"tu\w*n\s*(?:th\w*\s*)?(\d+)", row_text_joined, _re_docx.UNICODE)
            if m_tuan:
                new_tuan = int(m_tuan.group(1))
                if 1 <= new_tuan <= 8:
                    current_tuan = new_tuan
                    if current_tuan not in weekly_table_data:
                        weekly_table_data[current_tuan] = {
                            "tuan_header": f"Tuần {current_tuan}",
                            "nhiem_vu": "", "san_pham": "", "full_content": "",
                        }
                    _log.info(f"[PARSE-B] Tuần {current_tuan} tại hàng {ri}")

            if current_tuan is None:
                continue

            nv_text = row[col_nhiem_vu].strip() if col_nhiem_vu is not None and col_nhiem_vu < len(row) else ""
            sp_text = row[col_san_pham].strip() if col_san_pham is not None and col_san_pham < len(row) else ""

            nv_lower = nv_text.lower()
            sp_lower = sp_text.lower()
            is_nv_label = ("nhiệm vụ" in nv_lower or "nhiem vu" in nv_lower) and len(nv_text) < 80
            is_sp_label = ("sản phẩm" in sp_lower or "san pham" in sp_lower) and len(sp_text) < 80

            if nv_text and not is_nv_label:
                existing = weekly_table_data[current_tuan]["nhiem_vu"]
                weekly_table_data[current_tuan]["nhiem_vu"] = (existing + "\n" + nv_text).strip()
            if sp_text and not is_sp_label:
                existing = weekly_table_data[current_tuan]["san_pham"]
                weekly_table_data[current_tuan]["san_pham"] = (existing + "\n" + sp_text).strip()


    # Bổ sung weekly_table_data vào full_text để AI đọc được rõ hơn
    if weekly_table_data:
        parts.append("\n[DỮ LIỆU TUẦN – TRÍCH TỪ BẢNG]")
        for tuan_num in sorted(weekly_table_data.keys()):
            d = weekly_table_data[tuan_num]
            stt_label = d.get("stt_word") or f"1.{tuan_num}"  # "1.1"→"1.8" để map với Excel
            parts.append(f"\n--- TUẦN {tuan_num} (STT Word: {stt_label}) ---")
            parts.append(f"Nhiệm vụ đặt ra: {d['nhiem_vu'] or '(trống)'}")
            parts.append(f"Sản phẩm đặt ra: {d['san_pham'] or '(trống)'}")
            if d.get("ty_le"):
                # % scan được từ Word → dùng để so với Excel row cùng STT
                parts.append(f"Tỷ lệ hoàn thành (Word STT {stt_label}): {d['ty_le']}")
        full_text = "\n".join(parts)

    # Log tổng kết kết quả parse tuần
    _log.info(f"[PARSE] Kết quả cuối: {len(weekly_table_data)} tuần tìm được: {sorted(weekly_table_data.keys())}")
    for tnum, d in sorted(weekly_table_data.items()):
        _log.info(
            f"[PARSE] Tuần {tnum}: "
            f"nv={len(d['nhiem_vu'])} chars = '{d['nhiem_vu'][:80]}' | "
            f"sp={len(d['san_pham'])} chars = '{d['san_pham'][:80]}'"
        )

    # Bổ sung nhiem_vu_ket_qua (hàng 1.10) vào full_text
    if nhiem_vu_ket_qua:
        parts.append("\n[NHIỆM VỤ VÀ KẾT QUẢ THỰC TẾ – DÙNG ĐỂ SO VỚI EXCEL]")
        for item in nhiem_vu_ket_qua:
            pct = f" | Kết quả: {item['ket_qua_pct']}" if item['ket_qua_pct'] else ""
            parts.append(f"  {item['stt']}: {item['ten']}{pct}")
        full_text = "\n".join(parts)
        _log.info(f"[PARSE] nhiem_vu_ket_qua: {len(nhiem_vu_ket_qua)} nhiệm vụ")

    sections = _extract_sections(full_text)
    # Gắn thêm dữ liệu tuần từ table parse vào sections để dùng sau
    sections["weekly_table"] = weekly_table_data
    # Gắn nhiem_vu_ket_qua để dùng cho X1 cross-check
    sections["nhiem_vu_ket_qua"] = nhiem_vu_ket_qua

    # Trích xuất thông tin nhân viên & HOD từ Table 1 của Word
    nhan_vien_info = _extract_nhanvien_from_docx(doc)

    return {
        "paragraphs": paragraphs,
        "tables": tables,
        "full_text": full_text,
        "sections": sections,
        "nhan_vien_info": nhan_vien_info,
    }


def _extract_nhanvien_from_docx(doc) -> dict:
    """
    Trích xuất thông tin nhân viên & HOD từ Table 1 (bảng THÔNG TIN CHUNG) của file Word.

    Cấu trúc chuẩn CT Group:
      Col 0: Label (Họ và tên, Mã NV, Chức danh, Đơn vị, Ngày nhận việc, ...)
      Col 1: Giá trị của CBNV được đánh giá
      Col 2: Giá trị của HOD/Người được uỷ quyền

    Ngoài ra lấy ngày nhận việc và ngày hết hạn thử việc (chỉ ở cột NV).
    """
    info = {
        "ten_nhan_vien": "",
        "ma_nhan_vien": "",
        "chuc_danh": "",
        "don_vi": "",
        "ngay_nhan_viec": "",
        "ngay_het_han": "",
        "ten_hod": "",
        "ma_hod": "",
        "chuc_danh_hod": "",
    }

    # Map label → key của NV và HOD
    LABEL_MAP = {
        # Tên NV
        "họ và tên":           ("ten_nhan_vien", "ten_hod"),
        "ho va ten":           ("ten_nhan_vien", "ten_hod"),
        "họ tên":              ("ten_nhan_vien", "ten_hod"),
        # Mã NV
        "mã nv":               ("ma_nhan_vien",  "ma_hod"),
        "mã nhân viên":        ("ma_nhan_vien",  "ma_hod"),
        "ma nv":               ("ma_nhan_vien",  "ma_hod"),
        # Chức danh
        "chức danh":           ("chuc_danh",     "chuc_danh_hod"),
        "chuc danh":           ("chuc_danh",     "chuc_danh_hod"),
        "chức vụ":             ("chuc_danh",     "chuc_danh_hod"),
        "vị trí":              ("chuc_danh",     "chuc_danh_hod"),
        # Đơn vị / Phòng ban
        "đơn vị":              ("don_vi",        None),
        "don vi":              ("don_vi",        None),
        "phòng ban":           ("don_vi",        None),
        "phong ban":           ("don_vi",        None),
        # Ngày (chỉ cột NV)
        "ngày nhận việc":      ("ngay_nhan_viec", None),
        "ngay nhan viec":      ("ngay_nhan_viec", None),
        "ngày hết hạn":        ("ngay_het_han",  None),
        "ngay het han":        ("ngay_het_han",  None),
        "ngày hết hạn thử việc": ("ngay_het_han", None),
    }

    if not doc.tables:
        return info

    # Quét tất cả bảng, ưu tiên bảng đầu có cột "CBNV" hoặc "HOD"
    target_table = None
    for tbl in doc.tables:
        # Kiểm tra header row (row 0)
        if not tbl.rows:
            continue
        header_cells = []
        seen = set()
        for c in tbl.rows[0].cells:
            if id(c._tc) in seen:
                continue
            seen.add(id(c._tc))
            header_cells.append(c.text.strip().lower())
        header_txt = " ".join(header_cells)
        if any(kw in header_txt for kw in ["cbnv", "hod", "được đánh giá", "thành phần"]):
            target_table = tbl
            break

    # Fallback: dùng bảng đầu tiên
    if target_table is None:
        target_table = doc.tables[0]

    for row in target_table.rows:
        # Lấy cells, dedup merged
        seen = set()
        cells_text = []
        for c in row.cells:
            if id(c._tc) in seen:
                continue
            seen.add(id(c._tc))
            cells_text.append(c.text.strip())

        if len(cells_text) < 2:
            continue

        label = cells_text[0].lower().strip().rstrip(":")
        # Loại bỏ chú thích trong ngoặc đơn
        import re as _re_nv2
        label = _re_nv2.sub(r'\s*\(.*?\)', '', label).strip()

        val_nv  = cells_text[1].strip() if len(cells_text) > 1 else ""
        val_hod = cells_text[2].strip() if len(cells_text) > 2 else ""

        # Tìm match trong LABEL_MAP
        for key, (field_nv, field_hod) in LABEL_MAP.items():
            if key in label:
                if field_nv and val_nv and not info.get(field_nv):
                    info[field_nv] = val_nv
                if field_hod and val_hod and not info.get(field_hod):
                    info[field_hod] = val_hod
                break

    return info


def _parse_xlsx(data: bytes) -> dict:
    """
    Đọc file XLSX kế hoạch SXKD / KPI.
    Trả về dict gồm:
      - headers: list tên cột (hàng header)
      - rows: list dict (mỗi hàng KPI)
      - missing_evidence: list index hàng thiếu link minh chứng
      - full_text: text dạng bảng để gửi AI
    """
    wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
    ws = wb.active

    all_rows = list(ws.iter_rows(values_only=True))
    if not all_rows:
        return {"headers": [], "rows": [], "missing_evidence": [], "full_text": ""}

    # Collect rows có ảnh nhúng (OneCellAnchor hoặc TwoCellAnchor)
    image_rows = set()
    for img in getattr(ws, '_images', []):
        anchor = getattr(img, 'anchor', None)
        if anchor is None:
            continue
        # TwoCellAnchor: anchor._from.row (0-indexed)
        fr = getattr(getattr(anchor, '_from', None), 'row', None)
        if fr is not None:
            image_rows.add(fr + 1)  # chuyển sang 1-indexed
        # OneCellAnchor: anchor.row
        r = getattr(anchor, 'row', None)
        if r is not None:
            image_rows.add(r + 1)

    # Tìm hàng header (hàng đầu có dữ liệu text)
    # File mẫu: row 3 là header chính (STT, CÁC MẢNG CÔNG TÁC,...)
    rows_data = []
    missing_evidence = []
    full_text_lines = []

    for ri, row in enumerate(all_rows):
        if any(v is not None for v in row):
            line = " | ".join(str(v) if v is not None else "" for v in row)
            full_text_lines.append(f"Hàng {ri+1}: {line}")

    # Nhận diện các hàng KPI (có STT số nguyên) và check link
    # CHỈ đọc bảng đầu tiên – dừng khi gặp hàng tổng "TỶ LỆ ĐẠT" hoặc hàng trống hoàn toàn sau dữ liệu
    kpi_rows = []
    found_first_table = False
    first_table_done = False
    for ri, row in enumerate(all_rows):
        # Dừng ngay nếu đã xử lý xong bảng đầu
        if first_table_done:
            break

        # Phát hiện hàng tổng cuối bảng đầu (TỶ LỆ ĐẠT)
        row_text = " ".join(str(v or "").lower() for v in row)
        if any(kw in row_text for kw in ["tỷ lệ đạt", "tổng cộng", "tỷ lệ hoàn thành"]):
            if found_first_table:
                first_table_done = True
                break

        # STT ở cột 0
        stt = row[0] if row else None
        if isinstance(stt, (int, float)) and stt == int(stt) and 1 <= int(stt) <= 50:
            # Phải có ty_trong (cột 3) – bảng chính mới có cột TỶ TRỌNG
            ty_trong_val = row[3] if len(row) > 3 else None
            if ty_trong_val is None:
                continue  # bỏ qua hàng không thuộc bảng chính
            found_first_table = True
            cong_viec = str(row[1] or "").strip() if len(row) > 1 else ""
            mo_ta = str(row[2] or "").strip() if len(row) > 2 else ""
            ty_trong = row[3] if len(row) > 3 else None
            kpi = row[4] if len(row) > 4 else None
            ty_le = row[6] if len(row) > 6 else None
            ket_qua = row[7] if len(row) > 7 else None

            # Tìm minh chứng: cột 9 trở đi (text), hoặc ảnh nhúng trong sheet
            _INVALID = {"", "`", "~", "-", "_", "none", "null", "n/a"}
            minh_chung_cells = [
                str(v or "").strip()
                for v in row[9:]
                if v is not None and str(v).strip().lower() not in _INVALID
            ]
            minh_chung_text = minh_chung_cells[0] if minh_chung_cells else ""

            # Ảnh nhúng: kiểm tra row chính và các row liền kề (ảnh có thể span nhiều row)
            row_1indexed = ri + 1
            has_image = any(r in image_rows for r in range(row_1indexed, row_1indexed + 3))

            has_evidence = bool(minh_chung_text) or has_image
            minh_chung_display = minh_chung_text or ("(ảnh đính kèm)" if has_image else "")

            issues = []
            if not has_evidence:
                issues.append("Thiếu minh chứng (link hoặc ảnh đính kèm)")
            if ty_le is None or (isinstance(ty_le, (int, float)) and ty_le == 0):
                issues.append("Tỷ lệ thực hiện chưa cập nhật")
            if ket_qua is None or str(ket_qua).startswith("="):
                issues.append("Kết quả KPI chưa điền (còn công thức hoặc trống)")

            kpi_rows.append({
                "row_index": ri + 1,
                "stt": int(stt),
                "cong_viec": cong_viec,
                "mo_ta": mo_ta,
                "ty_trong": ty_trong,
                "kpi": kpi,
                "ty_le_thuc_hien": ty_le,
                "ket_qua": str(ket_qua) if ket_qua is not None else "",
                "minh_chung": minh_chung_display,
                "link_minh_chung": minh_chung_display,  # alias cho frontend tương thích
                "has_image": has_image,
                "issues": issues,
                "status": "THIẾU" if issues else "OK",
            })

    # ── Parse bảng "Kết quả thực hiện KPI theo tuần" (mục 1.1→1.8 và TB 1.9) ─
    # Tìm các hàng có STT dạng float 1.1, 1.2, ..., 1.8 và hàng tổng 1.9
    import re as _re_kpi
    weekly_rows = {}   # {1.1: pct, 1.2: pct, ...}
    stated_avg = None  # giá trị được điền ở ô 1.9
    for ri, row in enumerate(all_rows):
        stt_val = row[0] if row else None
        # Nhận diện STT dạng 1.1 → 1.9 (float)
        if isinstance(stt_val, float) and 1.0 < stt_val <= 1.9:
            stt_round = round(stt_val, 1)
            # Tìm % trong row: ưu tiên cột có kiểu số
            pct = None
            for v in row[1:]:
                if isinstance(v, (int, float)) and v is not None:
                    # Convert: 0.95 → 95%, 95 → 95%
                    pct = float(v) * 100 if float(v) <= 1 else float(v)
                    break
                if isinstance(v, str):
                    m = _re_kpi.search(r'(\d+(?:[.,]\d+)?)\s*%', v)
                    if m:
                        pct = float(m.group(1).replace(',', '.'))
                        break
            if stt_round <= 1.8 and pct is not None:
                weekly_rows[stt_round] = pct
            elif abs(stt_round - 1.9) < 0.01 and pct is not None:
                stated_avg = pct

    # Tính trung bình thực tế từ 1.1→1.8
    weekly_issues = []
    computed_avg = None
    if weekly_rows:
        computed_avg = round(sum(weekly_rows.values()) / len(weekly_rows), 2)
        week_count = len(weekly_rows)
        # Kiểm tra 1: có đủ 8 tuần không
        expected_weeks = {round(1.0 + i * 0.1, 1) for i in range(1, 9)}  # 1.1→1.8
        missing_weeks = sorted(expected_weeks - set(weekly_rows.keys()))
        if missing_weeks:
            weekly_issues.append(
                f"Thiếu kết quả KPI {len(missing_weeks)} tuần: {[f'1.{round((k-1)*10):.0f}' for k in missing_weeks]}"
            )
        # Kiểm tra 2: ô 1.9 có khớp trung bình tính toán không
        if stated_avg is not None:
            diff = abs(stated_avg - computed_avg)
            if diff > 0.5:  # chênh hơn 0.5% → sai
                weekly_issues.append(
                    f"Điểm trung bình 1.9 ({stated_avg:.2f}%) KHÔNG khớp với trung bình tính từ {week_count} tuần ({computed_avg:.2f}%). "
                    f"Công thức đúng: ({' + '.join(f'{v:.0f}%' for v in sorted(weekly_rows.items(), key=lambda x: x[0])[-8:])}) / {week_count} = {computed_avg:.2f}%"
                )
        elif weekly_rows:
            weekly_issues.append(
                f"Không tìm thấy ô điểm trung bình (1.9). Trung bình tính từ {week_count} tuần = {computed_avg:.2f}%"
            )

    # ── Trích xuất thông tin nhân viên từ các hàng đầu XLSX ──────────────────
    nhan_vien_info = _extract_nhanvien_from_xlsx(all_rows)

    return {
        "kpi_rows": kpi_rows,
        "missing_evidence": missing_evidence,
        "full_text": "\n".join(full_text_lines),
        "weekly_kpi": {
            "rows": weekly_rows,            # {1.1: 95.0, 1.2: 90.0, ...}
            "computed_avg": computed_avg,   # trung bình thực tế
            "stated_avg": stated_avg,       # giá trị ô 1.9
            "issues": weekly_issues,        # list lỗi phát hiện được
        },
        "nhan_vien_info": nhan_vien_info,
    }


def _extract_nhanvien_from_xlsx(all_rows: list) -> dict:
    """
    Trích xuất thông tin nhân viên và HOD từ các hàng đầu của file XLSX.
    Thường file có dạng:
      Hàng 1: "Họ và tên nhân viên:" | <tên>   "Mã nhân viên:" | <mã>
      Hàng 2: "Tên HOD:" | <tên>               "Mã HOD:" | <mã>
    Hoặc dạng khác nhau — dùng regex để tìm.
    """
    import re as _re_nv

    info = {
        "ten_nhan_vien": "",
        "ma_nhan_vien": "",
        "ten_hod": "",
        "ma_hod": "",
        "chuc_vu": "",
        "phong_ban": "",
    }

    # Ghép toàn bộ text từ 20 hàng đầu để tìm thông tin
    header_text = ""
    for ri, row in enumerate(all_rows[:20]):
        row_vals = [str(v or "").strip() for v in row]
        header_text += " | ".join(row_vals) + "\n"

    def find_val(patterns, text):
        """Tìm giá trị theo danh sách pattern regex."""
        for pat in patterns:
            m = _re_nv.search(pat, text, _re_nv.IGNORECASE | _re_nv.UNICODE)
            if m:
                val = m.group(1).strip().strip(":")
                if val and val.lower() not in ("", "none", "null"):
                    return val
        return ""

    # Tên nhân viên
    info["ten_nhan_vien"] = find_val([
        r"h[oọ]\s*v[aà]\s*t[eê]n\s*(?:nh[aâ]n\s*vi[eê]n)?\s*[:\-]?\s*([\w\s\u00C0-\u024F]{2,50}?)\s*(?:\||$|m[aã]\s*nh[aâ]n)",
        r"t[eê]n\s*nh[aâ]n\s*vi[eê]n\s*[:\-]?\s*([\w\s\u00C0-\u024F]{2,50}?)\s*(?:\||$)",
        r"nh[aâ]n\s*vi[eê]n\s*[:\-]?\s*([\w\s\u00C0-\u024F]{2,50}?)\s*(?:\||$|m[aã])",
        r"full[_\s]?name\s*[:\-]?\s*([\w\s]{2,50}?)\s*(?:\||$)",
    ], header_text)

    # Mã nhân viên
    info["ma_nhan_vien"] = find_val([
        r"m[aã]\s*(?:nh[aâ]n\s*vi[eê]n|nv)\s*[:\-]?\s*([A-Za-z0-9\-_\.]{2,20})\s*(?:\||$)",
        r"employee[_\s]?(?:id|code)\s*[:\-]?\s*([A-Za-z0-9\-_\.]{2,20})\s*(?:\||$)",
        r"m[aã]\s*nh[aâ]n\s*vi[eê]n\s*[:\-]?\s*([A-Za-z0-9\-_\.]{2,20})",
    ], header_text)

    # Tên HOD
    info["ten_hod"] = find_val([
        r"t[eê]n\s*(?:hod|qu[aả]n\s*l[yý]|trư[oở]ng\s*b[oộ]\s*ph[aâ]n)\s*[:\-]?\s*([\w\s\u00C0-\u024F]{2,50}?)\s*(?:\||$|m[aã]\s*hod)",
        r"hod\s*[:\-]?\s*([\w\s\u00C0-\u024F]{2,50}?)\s*(?:\||$|m[aã])",
        r"ng[uư][oờ]i\s*đ[aá]nh\s*gi[aá]\s*[:\-]?\s*([\w\s\u00C0-\u024F]{2,50}?)\s*(?:\||$)",
    ], header_text)

    # Mã HOD
    info["ma_hod"] = find_val([
        r"m[aã]\s*hod\s*[:\-]?\s*([A-Za-z0-9\-_\.]{2,20})\s*(?:\||$)",
        r"hod[_\s]?(?:id|code)\s*[:\-]?\s*([A-Za-z0-9\-_\.]{2,20})",
        r"m[aã]\s*qu[aả]n\s*l[yý]\s*[:\-]?\s*([A-Za-z0-9\-_\.]{2,20})",
    ], header_text)

    # Chức vụ / Vị trí thử việc
    info["chuc_vu"] = find_val([
        r"v[iị]\s*tr[ií]\s*(?:th[uử]\s*vi[eệ]c|[uứ]ng\s*tuy[eể]n)?\s*[:\-]?\s*([\w\s\u00C0-\u024F]{2,60}?)\s*(?:\||$)",
        r"ch[uứ]c\s*v[uụ]\s*[:\-]?\s*([\w\s\u00C0-\u024F]{2,60}?)\s*(?:\||$)",
        r"position\s*[:\-]?\s*([\w\s]{2,60}?)\s*(?:\||$)",
        r"th[uử]\s*vi[eệ]c\s*(?:v[iị]\s*tr[ií])?\s*[:\-]?\s*([\w\s\u00C0-\u024F]{2,60}?)\s*(?:\||$)",
    ], header_text)

    # Phòng ban
    info["phong_ban"] = find_val([
        r"ph[oò]ng\s*(?:ban)?\s*[:\-]?\s*([\w\s\u00C0-\u024F]{2,60}?)\s*(?:\||$)",
        r"b[oộ]\s*ph[aâ]n\s*[:\-]?\s*([\w\s\u00C0-\u024F]{2,60}?)\s*(?:\||$)",
        r"department\s*[:\-]?\s*([\w\s]{2,60}?)\s*(?:\||$)",
    ], header_text)

    # Fallback: quét từng ô riêng lẻ nếu không tìm được
    if not info["ten_nhan_vien"] or not info["ten_hod"]:
        for ri, row in enumerate(all_rows[:15]):
            for ci, cell in enumerate(row):
                cell_str = str(cell or "").strip()
                if not cell_str:
                    continue
                cell_lower = cell_str.lower()
                # Ô là label → lấy ô kế tiếp cùng hàng làm giá trị
                next_val = str(row[ci + 1] or "").strip() if ci + 1 < len(row) else ""
                if not info["ten_nhan_vien"] and any(k in cell_lower for k in ["họ và tên", "tên nhân viên", "tên nv", "ho va ten"]):
                    if next_val and len(next_val) < 60:
                        info["ten_nhan_vien"] = next_val
                if not info["ma_nhan_vien"] and any(k in cell_lower for k in ["mã nv", "mã nhân viên", "ma nhan vien", "employee id"]):
                    if next_val and len(next_val) < 20:
                        info["ma_nhan_vien"] = next_val
                if not info["ten_hod"] and any(k in cell_lower for k in ["tên hod", "ten hod", "hod", "quản lý", "trưởng bộ phận", "người đánh giá"]):
                    if next_val and len(next_val) < 60:
                        info["ten_hod"] = next_val
                if not info["ma_hod"] and any(k in cell_lower for k in ["mã hod", "ma hod", "hod id", "mã ql"]):
                    if next_val and len(next_val) < 20:
                        info["ma_hod"] = next_val
                if not info["chuc_vu"] and any(k in cell_lower for k in ["vị trí", "chức vụ", "vi tri", "position", "thử việc"]):
                    if next_val and len(next_val) < 80:
                        info["chuc_vu"] = next_val
                if not info["phong_ban"] and any(k in cell_lower for k in ["phòng ban", "bộ phận", "phòng", "department"]):
                    if next_val and len(next_val) < 60:
                        info["phong_ban"] = next_val

    return info


# ══════════════════════════════════════════════════════════════════════════════
# System prompt
# ══════════════════════════════════════════════════════════════════════════════







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


# ══════════════════════════════════════════════════════════════════════════════
# Session store – dùng Frappe cache (Redis) để chia sẻ giữa các worker process
# ══════════════════════════════════════════════════════════════════════════════

_SESSION_TTL = 86400  # 24 giờ
_SESSION_PREFIX = "ats_session:"


# Chỉ cho phép đúng 7 mã tiêu chí này. Mọi mã khác đều bị lọc cứng.
_ALLOWED_CRITERIA = {"W1", "W2", "W3", "E1", "E2", "E3", "X1"}




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


def _build_review_prompt(eval_type, docx_parsed, xlsx_parsed):
    """Build the OpenAI user message prompt for thu-viec/hoc-viec review.

    Args:
        eval_type: "thu_viec" | "hoc_viec"
        docx_parsed: parsed DOCX dict (full_text, sections)
        xlsx_parsed: parsed XLSX dict (kpi_rows, full_text)

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


    return user_msg


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
    user_msg = _build_review_prompt(eval_type, docx_parsed, xlsx_parsed)
    # ── Gọi OpenAI ────────────────────────────────────────────────────────────

    client = _get_client()
    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o"),
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
        max_tokens=8000,
    )
    result = json.loads(resp.choices[0].message.content)
    result = _filter_result(result)  # Xóa bất kỳ E1 nào AI tự sinh ra
    _log_tokens(resp, "review_files")

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
        "bao_cao_ngay": result.get("bao_cao_ngay", None) if daily_report_text else None,
        "danh_gia_quan_ly": result.get("danh_gia_quan_ly", None),
        "eval_type": eval_type,
    }


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
