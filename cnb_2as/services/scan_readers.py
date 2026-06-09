# Copyright (c) 2025, antruong and contributors
# For license information, please see license.txt

"""File reading and OCR utilities for phiếu đánh giá scan.

Handles DOCX text extraction, PDF→image conversion, OCR via GPT-4o Vision,
HTML parsing, and Docling (if available).
Called by: services/scan_service.py
"""

# Copyright (c) 2025, antruong and contributors
# For license information, please see license.txt

"""Service layer for phiếu đánh giá scan operations.

Provides all helper functions for file reading (DOCX, PDF, HTML),
OCR/Vision extraction, XML building, and session management.
Called by: api/scan_phieu.py
"""

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

# ── OCR API URL (ctpai.vn) ──────────────────────────────────────────────────────
_OCR_API_URL = os.getenv("CNB_OCR_API_URL", "https://ctpai.vn/api/ocr")


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        key = os.getenv("OPENAI_API_KEY", "") or getattr(frappe.conf, "openai_api_key", "")
        if not key:
            frappe.throw("Chưa cấu hình OPENAI_API_KEY")
        _client = OpenAI(api_key=key)
    return _client



def _call_ocr_api(file_bytes: bytes, filename: str) -> str:
    """
    Gửi file lên OCR API ctpai.vn, parse response → text.
    Trả về chuỗi rỗng nếu lỗi hoặc không kết nối được.
    """
    try:
        import requests as _req
    except ImportError:
        frappe.logger("cnb_scan").warning("[SCAN] requests chưa cài, bỏ qua OCR API")
        return ""

    fname_lower = filename.lower()
    if fname_lower.endswith(".pdf"):        mime = "application/pdf"
    elif fname_lower.endswith(".docx"):     mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif fname_lower.endswith(".png"):      mime = "image/png"
    elif fname_lower.endswith((".jpg", ".jpeg")): mime = "image/jpeg"
    elif fname_lower.endswith((".html", ".htm")):  mime = "text/html"
    else:                                   mime = "application/octet-stream"

    try:
        resp = _req.post(
            _OCR_API_URL,
            files={"file": (filename, file_bytes, mime)},
            headers={"accept": "application/json"},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        frappe.logger("cnb_scan").warning(f"[SCAN] OCR API lỗi: {e}")
        return ""

    # Parse response – thử nhiều key phổ biến
    for key in ("text", "content", "result", "output", "markdown", "extracted_text"):
        if key in data and isinstance(data[key], str) and data[key].strip():
            return data[key]

    # Response dạng list block
    if isinstance(data, list):
        texts = []
        for block in data:
            if isinstance(block, dict):
                for k in ("text", "content", "value"):
                    if k in block and isinstance(block[k], str):
                        texts.append(block[k])
                        break
            elif isinstance(block, str):
                texts.append(block)
        if texts:
            return "\n\n".join(texts)

    # Fallback: dump JSON
    return json.dumps(data, ensure_ascii=False, indent=2)


def _pdf_to_images(file_bytes: bytes) -> list[bytes]:
    """Chuyển PDF sang list ảnh PNG (mỗi trang). Dùng PyMuPDF.
    Zoom 2.0x (~144 DPI) — đủ rõ cho GPT-4o Vision, tránh OOM với phiếu nhiều trang.
    """
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        images = []
        # Giới hạn tối đa 40 trang để tránh OOM (phiếu thực tế không quá 30 trang)
        for i, page in enumerate(doc):
            if i >= 40:
                frappe.logger("cnb_scan").warning(f"[SCAN] PDF có {doc.page_count} trang, chỉ xử lý 40 trang đầu")
                break
            # 2.0x = ~144 DPI — đủ rõ cho Vision, tiết kiệm RAM ~3x so với 3.0x
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
            images.append(pix.tobytes("png"))
        doc.close()
        return images
    except Exception as e:
        frappe.logger("cnb_scan").warning(f"[SCAN] PyMuPDF lỗi: {e}")
        return []


def _call_vision_ocr(file_bytes: bytes, filename: str) -> str:
    """
    Dùng GPT-4o Vision để đọc ảnh/PDF (đặc biệt tốt với chữ viết tay).
    PDF → render từng trang → gửi tất cả lên Vision.
    Trả về text đầy đủ, bao gồm cả phần viết tay.
    """
    client = _get_client()
    fname_lower = filename.lower()

    # Build list ảnh base64 để gửi
    image_parts = []

    if fname_lower.endswith(".pdf"):
        page_images = _pdf_to_images(file_bytes)
        if not page_images:
            # Fallback: gửi thẳng PDF bytes không được Vision hỗ trợ → skip
            return ""
        # Scan toàn bộ trang (không giới hạn)
        for img_bytes in page_images:
            b64 = base64.b64encode(img_bytes).decode()
            image_parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "high"}
            })
    elif fname_lower.endswith((".png", ".jpg", ".jpeg", ".bmp", ".webp")):
        b64 = base64.b64encode(file_bytes).decode()
        ext = fname_lower.rsplit(".", 1)[-1]
        mime_map = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "bmp": "bmp", "webp": "webp"}
        mime = f"image/{mime_map.get(ext, 'png')}"
        image_parts.append({
            "type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{b64}", "detail": "high"}
        })
    else:
        # Không phải file ảnh/PDF → không dùng Vision
        return ""

    if not image_parts:
        return ""

    vision_prompt = """OCR tài liệu phiếu đánh giá thử việc CT Group. Quy tắc bắt buộc:
1. Chữ in → giữ nguyên
2. Chữ viết tay → thêm [VIẾT TAY] trước nội dung đó
3. Bảng → dùng markdown | col | col | NHƯNG nếu nội dung ô > 80 từ thì cắt gọn còn 2-3 câu tóm tắt
4. Đoạn văn dài (>80 từ) → dùng bullet points, KHÔNG nhét vào ô bảng
5. Tiêu đề → dùng # ## ###
6. Giữ tiếng Việt có dấu
7. KHÔNG lồng markdown table bên trong ô bảng khác"""

    messages = [
        {"role": "user", "content": [
            {"type": "text", "text": vision_prompt},
            *image_parts
        ]}
    ]

    try:
        # Process từng trang riêng để tránh ô bảng bị lồng
        all_pages_text = []
        for idx, part in enumerate(image_parts):
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": vision_prompt},
                    part
                ]}],
                max_tokens=4096,  # đủ cho 1 trang đầy nội dung
                temperature=0,
            )
            page_text = resp.choices[0].message.content or ""
            all_pages_text.append(_sanitize_markdown_tables(page_text))
        return "\n\n---\n\n".join(all_pages_text)
    except Exception as e:
        frappe.logger("cnb_scan").warning(f"[SCAN] GPT-4o Vision lỗi: {e}")
        return ""


def _read_with_docling(file_bytes: bytes, filename: str) -> str:
    """Docling đọc text layer PDF trong subprocess (không RapidOCR)."""
    suffix = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    script = f"""
import sys
try:
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.datamodel.base_models import InputFormat
    opts = PdfPipelineOptions()
    opts.do_ocr = False
    opts.do_table_structure = True
    opts.generate_page_images = False
    opts.generate_table_images = False
    conv = DocumentConverter(
        format_options={{InputFormat.PDF: PdfFormatOption(pipeline_options=opts)}}
    )
    result = conv.convert({tmp_path!r})
    print(result.document.export_to_markdown(), end='')
    sys.exit(0)
except Exception as e:
    print(f"ERR:{{e}}", file=sys.stderr)
    sys.exit(1)
"""
    try:
        proc = subprocess.run([sys.executable, "-c", script],
                              capture_output=True, text=True, timeout=120)
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout
    except Exception:
        pass
    finally:
        try: os.unlink(tmp_path)
        except Exception: pass
    return ""


def _sanitize_markdown_tables(text: str) -> str:
    """
    Duyệt từng dòng markdown. Nếu 1 ô bảng > MAX_CELL_WORDS từ,
    cắt gọn và chuyển nội dung dài ra ngoài thành đoạn văn bullet.
    """
    MAX_CELL_WORDS = 50
    lines = text.splitlines()
    result = []
    overflow_blocks = []

    for line in lines:
        if not line.strip().startswith('|'):
            result.append(line)
            continue

        # Parse cells
        cells = line.split('|')
        new_cells = []
        for cell in cells:
            stripped = cell.strip()
            word_count = len(stripped.split())
            if word_count > MAX_CELL_WORDS:
                # Cắt còn 40 từ + dấu ...
                short = ' '.join(stripped.split()[:40]) + '...'
                ref = f"[xem bên dưới #{len(overflow_blocks)+1}]"
                overflow_blocks.append((len(overflow_blocks)+1, stripped))
                new_cells.append(f" {short} {ref} ")
            else:
                new_cells.append(cell)
        result.append('|'.join(new_cells))

    # Thêm overflow blocks ra ngoài bảng
    for idx, content in overflow_blocks:
        result.append(f"\n**[Nội dung #{idx}]** {content}\n")

    return '\n'.join(result)


def _read_html_text(file_bytes: bytes) -> str:
    try: html = file_bytes.decode("utf-8", errors="replace")
    except Exception: html = file_bytes.decode("latin-1", errors="replace")
    html = re.sub(r'(?is)<(script|style)[^>]*>.*?</\1>', ' ', html)
    html = re.sub(r'<!--.*?-->', ' ', html, flags=re.DOTALL)
    html = re.sub(r'(?i)<(br|p|div|tr|li|h[1-6])[^>]*>', '\n', html)
    html = re.sub(r'<[^>]+>', ' ', html)
    html = html.replace('&nbsp;', ' ').replace('&amp;', '&') \
               .replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')
    return '\n'.join(l.strip() for l in html.splitlines() if l.strip())


def _read_docx_text(file_bytes: bytes) -> str:
    """Basic DOCX text extraction (fallback)."""
    try:
        from docx import Document
        doc = Document(io.BytesIO(file_bytes))
        parts = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        for tbl in doc.tables:
            for row in tbl.rows:
                cells = [c.text.strip() for c in row.cells if c.text.strip()]
                if cells:
                    parts.append(" | ".join(cells))
        return "\n".join(parts)
    except Exception:
        return ""


def _read_docx_structured(file_bytes: bytes) -> dict[str, str]:
    """
    Đọc DOCX và tách thành các section rõ ràng theo heading / nội dung.
    Trả về dict: {section_label: text_content}
    Section:
      A_thong_tin  – Bảng thông tin chung + Phần I nhận xét
      B_kpi        – Phần II KPI tuần (1.1-1.8), TBC, 1.6 công việc
      C_san_pham   – Sản phẩm nghiệm thu tuần (2.1-2.8)
      D_hoi_nhap   – Phần III Hội nhập (câu 1-9)
      E_ket_luan   – Kết luận + đề xuất
    """
    try:
        from docx import Document
        doc = Document(io.BytesIO(file_bytes))
    except Exception:
        return {}

    def _cell_text(cell):
        """Lấy text từng ô (giữ xuống dòng bên trong)."""
        return "\n".join(p.text.strip() for p in cell.paragraphs if p.text.strip())

    def _table_to_text(tbl) -> str:
        """Convert table → text dạng | col1 | col2 | (dedup merged cells)."""
        lines = []
        for row in tbl.rows:
            seen = set()
            cells_text = []
            for c in row.cells:
                tc_id = id(c._tc)
                if tc_id in seen:
                    continue
                seen.add(tc_id)
                cells_text.append(_cell_text(c))
            if any(t.strip() for t in cells_text):
                # Thay newline trong ô bằng " | " để giữ cấu trúc
                cells_joined = " | ".join(t.replace("\n", " ↵ ") for t in cells_text)
                lines.append(cells_joined)
        return "\n".join(lines)

    # Thu thập toàn bộ nội dung theo thứ tự xuất hiện trong doc
    # docx phần tử (paragraph / table) nằm trong body
    from docx.oxml.ns import qn
    body_elems = []
    for elem in doc.element.body:
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag == "p":
            # paragraph
            text = "".join(r.text or "" for r in elem.iter(qn("w:t")))
            if text.strip():
                body_elems.append(("p", text.strip()))
        elif tag == "tbl":
            # find matching Table object
            for tbl in doc.tables:
                if tbl._tbl is elem:
                    t_text = _table_to_text(tbl)
                    if t_text.strip():
                        body_elems.append(("tbl", t_text))
                    break

    # Phân loại section dựa trên keyword
    SEC_A = "A_thong_tin"
    SEC_B = "B_kpi"
    SEC_C = "C_san_pham"
    SEC_D = "D_hoi_nhap"
    SEC_E = "E_ket_luan"

    def _detect_section(text: str) -> str | None:
        t = text.lower()
        if any(k in t for k in ["phần i", "phan i", "nhận xét chung", "nhẫn xet chung",
                                  "những điểm làm tốt", "kỹ năng đáp ứng"]):
            return SEC_A
        if any(k in t for k in ["kết quả thực hiện kpi", "kết qua thuc hien kpi",
                                  "1.1", "1.2", "điểm tbc", "1.6", "công việc được giao"]):
            return SEC_B
        if any(k in t for k in ["sản phẩm nghiệm thu", "san pham nghiem thu",
                                  "2.1", "2.2", "số lượng file", "link đính kèm"]):
            return SEC_C
        if any(k in t for k in ["hội nhập", "hoi nhap", "sứ mệnh", "tầm nhìn",
                                  "văn hóa cốt lõi", "7.1", "7.2", "7.3", "7.4", "7.5"]):
            return SEC_D
        if any(k in t for k in ["đạt yêu cầu", "không đạt", "kết luận", "đề xuất ký",
                                  "rtd", "y kiến hod", "y kiến rtd"]):
            return SEC_E
        return None

    sections: dict[str, list[str]] = {
        SEC_A: [], SEC_B: [], SEC_C: [], SEC_D: [], SEC_E: []
    }
    current_sec = SEC_A  # default bắt đầu từ A

    for kind, text in body_elems:
        detected = _detect_section(text)
        if detected:
            current_sec = detected
        sections[current_sec].append(text)

    # Convert mỗi section thành text
    return {k: "\n".join(v) for k, v in sections.items() if v}


def _merge_ocr_vision(ocr_text: str, vision_text: str) -> str:
    """
    Dùng GPT-4o để merge CTPAI OCR (cấu trúc tốt) với Vision (chữ viết tay).
    Kết quả: 1 markdown duy nhất với bảng đúng + chữ viết tay điền đúng ô.
    Fallback: trả về ocr_text + vision_text nếu merge fail.
    """
    try:
        client = _get_client()
        # Giới hạn token để tránh quá dài
        ocr_truncated = ocr_text[:12000]
        vision_truncated = vision_text[:12000]

        prompt = _MERGE_PROMPT.format(
            ocr_text=ocr_truncated,
            vision_text=vision_truncated,
        )

        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=8000,
        )
        merged = resp.choices[0].message.content or ""
        if merged.strip():
            frappe.logger("cnb_scan").info(f"[SCAN] Merge OK: {len(merged)} chars")
            return merged.strip()
    except Exception as e:
        frappe.logger("cnb_scan").warning(f"[SCAN] Merge fail: {e}")

    # Fallback: ghép thô nếu GPT-4o fail
    return (
        "=== OCR (chữ in) ===\n" + ocr_text.strip() +
        "\n\n=== VISION (chữ viết tay) ===\n" + vision_text.strip()
    )


def _extract_text(file_bytes: bytes, filename: str) -> tuple[str, str]:
    """
    Trả về (text, method_note).
    Thứ tự ưu tiên:
      HTML  → đọc trực tiếp
      DOCX  → đọc trực tiếp
      PDF/ảnh:
        1. OCR API (ctpai.vn) – nhanh, tiếng Việt tốt
        2. GPT-4o Vision – đọc chữ viết tay, kết hợp với OCR API
        3. Docling text layer – fallback khi PDF có text nhúng
    """
    fname = filename.lower()

    # ── HTML ──────────────────────────────────────────────────────────────────
    if fname.endswith((".html", ".htm")):
        text = _read_html_text(file_bytes)
        if text.strip():
            return text, "HTML – đọc trực tiếp"

    # ── DOCX ──────────────────────────────────────────────────────────────────
    if fname.endswith(".docx"):
        text = _read_docx_text(file_bytes)
        if text.strip():
            return text, "DOCX – đọc trực tiếp"

    # ── PDF / Ảnh scan → dùng GPT-4o Vision trực tiếp (đầy đủ nhất) ─────────
    if fname.endswith((".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".webp")):
        frappe.logger("cnb_scan").info(f"[SCAN] GPT-4o Vision: {filename}")
        vision_text = _call_vision_ocr(file_bytes, filename)
        if vision_text.strip():
            frappe.logger("cnb_scan").info(f"[SCAN] Vision: {len(vision_text)} chars")
            return vision_text, "GPT-4o Vision (chữ viết tay)"

    return "", "Không đọc được nội dung file"
