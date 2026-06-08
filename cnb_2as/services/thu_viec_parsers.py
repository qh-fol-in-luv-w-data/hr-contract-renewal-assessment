# Copyright (c) 2025, antruong and contributors
# For license information, please see license.txt

"""DOCX/XLSX/PDF parsers for thu-viec evaluation files.

Handles reading and extracting structured data from evaluation documents:
- Word phiếu đánh giá thử việc (DOCX)
- Excel KPI plan (XLSX)
- PDF fallback parsing via OCR
Called by: services/thu_viec_service.py
"""

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
from cnb_2as.services.prompts import (
    _SYSTEM_PROMPT,
    _CHAT_SYSTEM,
)


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
