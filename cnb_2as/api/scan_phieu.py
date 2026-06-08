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

def _get_client() -> OpenAI:
    global _client
    if _client is None:
        key = os.getenv("OPENAI_API_KEY", "") or getattr(frappe.conf, "openai_api_key", "")
        if not key:
            frappe.throw("Chưa cấu hình OPENAI_API_KEY")
        _client = OpenAI(api_key=key)
    return _client


# ── Session helpers ────────────────────────────────────────────────────────────
_NS = "cnb_scan_phieu"

def _save_session(sid: str, data: dict):
    frappe.cache().set_value(f"{_NS}:{sid}", json.dumps(data, ensure_ascii=False), expires_in_sec=3600)

def _load_session(sid: str) -> dict:
    raw = frappe.cache().get_value(f"{_NS}:{sid}")
    if not raw:
        frappe.throw(f"Session không tồn tại hoặc đã hết hạn: {sid}")
    return json.loads(raw)


# ══════════════════════════════════════════════════════════════════════════════
# TIER 1 – OCR API (app.ctpai.vn:8088)
# ══════════════════════════════════════════════════════════════════════════════
_OCR_API_URL = "http://app.ctpai.vn:8088/layout-parsing-file"

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


# ══════════════════════════════════════════════════════════════════════════════
# TIER 2 – GPT-4o Vision (đọc chữ in + chữ viết tay)
# ══════════════════════════════════════════════════════════════════════════════

def _pdf_to_images(file_bytes: bytes) -> list[bytes]:
    """Chuyển PDF sang list ảnh PNG (mỗi trang). Dùng PyMuPDF."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        images = []
        for page in doc:
            # Render 3x để chữ nhỏ / viết tay rõ hơn cho Vision
            mat = fitz.Matrix(3.0, 3.0)
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


# ══════════════════════════════════════════════════════════════════════════════
# TIER 3 – Docling (text layer, không OCR/RapidOCR)
# ══════════════════════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════════════════════
# Sanitizer – dọn ô bảng quá dài
# ══════════════════════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════════════════════
# Các reader bổ sung (HTML, DOCX)
# ══════════════════════════════════════════════════════════════════════════════

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



# ══════════════════════════════════════════════════════════════════════════════
# MERGE – Kết hợp CTPAI skeleton + Vision handwriting
# ══════════════════════════════════════════════════════════════════════════════


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


# ══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR – chọn phương thức tốt nhất
# ══════════════════════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════════════════════
# AI Prompts
# ══════════════════════════════════════════════════════════════════════════════



# ══════════════════════════════════════════════════════════════════════════════
# XML Builder – Tạo XML từ extracted_fields
# ══════════════════════════════════════════════════════════════════════════════

def _escape_xml(s: str) -> str:
    """Escape các ký tự đặc biệt trong XML."""
    if not s:
        return ""
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;")
             .replace("'", "&apos;"))


def _build_xml_from_fields(fields: dict) -> str:
    """Tạo XML phiếu đánh giá từ fields dict (CTG-GO-NLCD-QT16-BM01)."""
    e = _escape_xml

    sec_a = (
        "\n  <ThongTinChung>\n"
        f"    <TenNhanVien>{e(fields.get('ho_ten',''))}</TenNhanVien>\n"
        f"    <MaNhanVien>{e(fields.get('ma_nhan_su',''))}</MaNhanVien>\n"
        f"    <ChucDanh>{e(fields.get('chuc_danh',''))}</ChucDanh>\n"
        f"    <DonVi>{e(fields.get('phong_ban',''))}</DonVi>\n"
        f"    <CongTy>{e(fields.get('cong_ty',''))}</CongTy>\n"
        f"    <NgayNhanViec>{e(fields.get('ngay_nhan_viec',''))}</NgayNhanViec>\n"
        f"    <NgayHetHan>{e(fields.get('ngay_het_han',''))}</NgayHetHan>\n"
        f"    <ThoiGianThuViec>{e(fields.get('thoi_gian_thu_viec',''))}</ThoiGianThuViec>\n"
        f"    <LoaiHopDong>{e(fields.get('loai_hop_dong',''))}</LoaiHopDong>\n"
        f"    <TenHOD>{e(fields.get('ten_hod',''))}</TenHOD>\n"
        f"    <MaHOD>{e(fields.get('ma_hod',''))}</MaHOD>\n"
        f"    <ChucDanhHOD>{e(fields.get('chuc_danh_hod',''))}</ChucDanhHOD>\n"
        f"    <DonViHOD>{e(fields.get('don_vi_hod',''))}</DonViHOD>\n"
        "  </ThongTinChung>"
    )

    # B. Phan I – Nhan xet chung (5 cau)
    nxet_labels = [
        "Những điểm làm tốt trong quá trình thử việc",
        "Các kỹ năng đáp ứng yêu cầu công việc",
        "Các hoạt động tích cực tham gia",
        "Những điểm cần cải thiện",
        "Kỹ năng cần nâng cao hoặc hạn chế cần khắc phục",
    ]
    nxet_items = []
    for i in range(1, 6):
        nv    = e(str(fields.get(f'nhan_xet_{i}_nv', '') or ''))
        hod   = e(str(fields.get(f'nhan_xet_{i}_hod', '') or ''))
        label = e(nxet_labels[i - 1])
        nxet_items.append(
            f'    <NhanXet stt="{i}" noiDung="{label}">\n'
            f'      <NV>{nv}</NV>\n'
            f'      <HOD>{hod}</HOD>\n'
            f'    </NhanXet>'
        )
    sec_b = "\n  <PhanI_NhanXetChung>\n" + "\n".join(nxet_items) + "\n  </PhanI_NhanXetChung>"

    # C. Phan II – KPI (dynamic weeks) + san pham (dynamic weeks)
    # Detect actual number of weeks from data (max 8)
    n_tuan = 4  # default
    for _t in range(8, 0, -1):
        if any([
            fields.get(f'kpi_tuan_{_t}_ty_le', ''),
            fields.get(f'san_pham_{_t}', ''),
            fields.get(f'kpi_tuan_{_t}', {}).get('ty_le', ''),
        ]):
            n_tuan = _t
            break

    kpi_items = []
    for i in range(1, n_tuan + 1):
        ty_le = e(str(fields.get(f'kpi_tuan_{i}_ty_le', '') or ''))
        kpi_items.append(f'    <Tuan so="{i}" tyLe="{ty_le}"/>')

    tbc_nv    = e(str(fields.get('diem_tbc_kpi_nv', '') or ''))
    tbc_hod   = e(str(fields.get('diem_tbc_kpi_hod', '') or ''))
    cong_viec = e(str(fields.get('cong_viec_duoc_giao', '') or ''))

    # 1.6 – Nhiệm vụ (dynamic, max 8)
    n_nv = 4  # default
    for _n in range(8, 0, -1):
        if fields.get(f'nhiem_vu_{_n}_noi_dung', '') or fields.get(f'nhiem_vu_{_n}_ket_qua', ''):
            n_nv = _n
            break

    nv_items = []
    for i in range(1, n_nv + 1):
        nd  = e(str(fields.get(f'nhiem_vu_{i}_noi_dung','') or ''))
        kq  = e(str(fields.get(f'nhiem_vu_{i}_ket_qua','') or ''))
        tl  = e(str(fields.get(f'nhiem_vu_{i}_ty_le','') or ''))
        hod = e(str(fields.get(f'nhiem_vu_{i}_hod','') or ''))
        nv_items.append(
            f'    <NhiemVu so="{i}" tyLe="{tl}">\n'
            f'      <NoiDung>{nd}</NoiDung>\n'
            f'      <KetQua>{kq}</KetQua>\n'
            f'      <HOD>{hod}</HOD>\n'
            f'    </NhiemVu>'
        )

    sp_items = []
    for i in range(1, n_tuan + 1):
        sp      = e(str(fields.get(f'san_pham_{i}', '') or ''))
        so_file = e(str(fields.get(f'so_luong_file_{i}', '') or ''))
        link    = e(str(fields.get(f'link_dinh_kem_{i}', '') or ''))
        vi_pham = e(str(fields.get(f'vi_pham_upload_{i}', '') or ''))
        kpi_sp  = e(str(fields.get(f'kpi_sp_tuan_{i}', '') or ''))
        sp_items.append(
            f'    <SanPham tuan="{i}" tyLeKPI="{kpi_sp}">\n'
            f'      <DanhSach>{sp}</DanhSach>\n'
            f'      <SoLuongFile>{so_file}</SoLuongFile>\n'
            f'      <DuongLinkDinhKem>{link}</DuongLinkDinhKem>\n'
            f'      <SoLanViPhamUpload>{vi_pham}</SoLanViPhamUpload>\n'
            f'    </SanPham>'
        )


    sec_c = (
        "\n  <PhanII_KPI>\n"
        + "\n".join(kpi_items)
        + f"\n    <DiemTBC_NV>{tbc_nv}</DiemTBC_NV>"
        + f"\n    <DiemTBC_HOD>{tbc_hod}</DiemTBC_HOD>"
        + f"\n    <CongViecDuocGiao>{cong_viec}</CongViecDuocGiao>"
        + "\n  </PhanII_KPI>"
        + "\n  <CongViecDuocGiao>\n"
        + "\n".join(nv_items)
        + "\n  </CongViecDuocGiao>"
        + "\n  <SanPhamNghiemThu>\n"
        + "\n".join(sp_items)
        + "\n  </SanPhamNghiemThu>"
    )

    # D. Phan III – Hoi nhap (9 cau)
    hn_labels = [
        "Sứ mệnh Tập đoàn", "Sứ mệnh bản thân",
        "Tầm nhìn Tập đoàn", "Tầm nhìn bản thân",
        "Văn hóa cốt lõi Tập đoàn", "Giá trị cốt lõi bản thân",
        "Sự phù hợp văn hóa làm việc",
        "Văn hóa kinh doanh", "Đóng góp khác trong giai đoạn hội nhập",
    ]
    hn_items = []
    for i in range(1, 10):
        nv    = e(str(fields.get(f'hoi_nhap_{i}_nv', '') or ''))
        hod   = e(str(fields.get(f'hoi_nhap_{i}_hod', '') or ''))
        label = e(hn_labels[i - 1])
        hn_items.append(
            f'    <CauHoi so="{i}" noiDung="{label}">\n'
            f'      <NV>{nv}</NV>\n'
            f'      <HOD>{hod}</HOD>\n'
            f'    </CauHoi>'
        )
    sub_labels = ["Hiệu quả", "Tốc độ", "Kỷ luật", "Học tập", "Chính trực"]
    sub_items  = []
    for j, sl in enumerate(sub_labels, 1):
        nv  = e(str(fields.get(f'hoi_nhap_7_{j}_nv',  '') or ''))
        hod = e(str(fields.get(f'hoi_nhap_7_{j}_hod', '') or ''))
        sub_items.append(f'      <Sub so="7.{j}" noiDung="{e(sl)}"><NV>{nv}</NV><HOD>{hod}</HOD></Sub>')

    sec_d = (
        "\n  <PhanIII_HoiNhap>\n"
        + "\n".join(hn_items)
        + "\n    <SubCau7>\n" + "\n".join(sub_items) + "\n    </SubCau7>"
        + "\n  </PhanIII_HoiNhap>"
    )

    # E. Ket luan
    sec_e = (
        "\n  <KetLuan>\n"
        f"    <KetQua>{e(fields.get('ket_luan',''))}</KetQua>\n"
        f"    <DeXuatKyHD>{e(fields.get('de_xuat_ky_hd',''))}</DeXuatKyHD>\n"
        f"    <DeXuatTangThuNhap>{e(fields.get('de_xuat_tang_thu_nhap',''))}</DeXuatTangThuNhap>\n"
        f"    <DeNghiPhoiHop>{e(fields.get('de_nghi_phoi_hop',''))}</DeNghiPhoiHop>\n"
        f"    <YKienHOD>{e(fields.get('y_kien_hod',''))}</YKienHOD>\n"
        f"    <YKienRTD>{e(fields.get('y_kien_rtd',''))}</YKienRTD>\n"
        f"    <NgayKy>{e(fields.get('ngay_ky',''))}</NgayKy>\n"
        f"    <TenHODKy>{e(fields.get('ten_hod_ky',''))}</TenHODKy>\n"
        "  </KetLuan>"
    )

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<PhieuDanhGiaThuViec>'
        + sec_a + sec_b + sec_c + sec_d + sec_e
        + '\n</PhieuDanhGiaThuViec>'
    )



# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 1 – scan_extract
# ══════════════════════════════════════════════════════════════════════════════

@frappe.whitelist(allow_guest=True)
def _scan_extract_docx(file_bytes, filename, client):
    """
    Extract fields from DOCX using batch OpenAI calls (5-section strategy).

    Returns:
        tuple: (fields dict, raw_text str)
    """

    fields = {}
    raw_text = ""

    method_note = "DOCX – batch extraction (5 section)"
    frappe.logger("cnb_scan").info(f"[SCAN] DOCX structured batch: {filename}")

    sections = _read_docx_structured(file_bytes)
    if not sections:
        raw_text = _read_docx_text(file_bytes)
    else:
        raw_text = "\n\n".join(f"=== {k} ===\n{v}" for k, v in sections.items())

    BATCH_PROMPTS = {
        "A_thong_tin": """Trích xuất THONG TIN CHUNG + PHẦN I từ phần này. Trả JSON thuần:
{
  "ho_ten":"","ma_nhan_su":"","chuc_danh":"","phong_ban":"","cong_ty":"",
  "ngay_nhan_viec":"","ngay_het_han":"","thoi_gian_thu_viec":"","loai_hop_dong":"",
  "ten_hod":"","ma_hod":"","chuc_danh_hod":"","don_vi_hod":"",
  "nhan_xet_1_nv":"","nhan_xet_1_hod":"",
  "nhan_xet_2_nv":"","nhan_xet_2_hod":"",
  "nhan_xet_3_nv":"","nhan_xet_3_hod":"",
  "nhan_xet_4_nv":"","nhan_xet_4_hod":"",
  "nhan_xet_5_nv":"","nhan_xet_5_hod":""
}
Lấy NGUYÊN VĂN, không tóm tắt. Ô trống → "".""",
        "B_kpi": """Trích xuất PHẦN II KPI từ phần này. Trả JSON thuần:
{
  "kpi_tuan_1_ty_le":"","kpi_tuan_2_ty_le":"","kpi_tuan_3_ty_le":"","kpi_tuan_4_ty_le":"",
  "kpi_tuan_5_ty_le":"","kpi_tuan_6_ty_le":"","kpi_tuan_7_ty_le":"","kpi_tuan_8_ty_le":"",
  "diem_tbc_kpi_nv":"","diem_tbc_kpi_hod":"",
  "cong_viec_duoc_giao":"","ty_le_hoan_thanh_16":"",
  "nhiem_vu_1_noi_dung":"","nhiem_vu_1_ket_qua":"","nhiem_vu_1_ty_le":"","nhiem_vu_1_hod":"",
  "nhiem_vu_2_noi_dung":"","nhiem_vu_2_ket_qua":"","nhiem_vu_2_ty_le":"","nhiem_vu_2_hod":"",
  "nhiem_vu_3_noi_dung":"","nhiem_vu_3_ket_qua":"","nhiem_vu_3_ty_le":"","nhiem_vu_3_hod":"",
  "nhiem_vu_4_noi_dung":"","nhiem_vu_4_ket_qua":"","nhiem_vu_4_ty_le":"","nhiem_vu_4_hod":"",
  "nhiem_vu_5_noi_dung":"","nhiem_vu_5_ket_qua":"","nhiem_vu_5_ty_le":"","nhiem_vu_5_hod":"",
  "nhiem_vu_6_noi_dung":"","nhiem_vu_6_ket_qua":"","nhiem_vu_6_ty_le":"","nhiem_vu_6_hod":"",
  "nhiem_vu_7_noi_dung":"","nhiem_vu_7_ket_qua":"","nhiem_vu_7_ty_le":"","nhiem_vu_7_hod":"",
  "nhiem_vu_8_noi_dung":"","nhiem_vu_8_ket_qua":"","nhiem_vu_8_ty_le":"","nhiem_vu_8_hod":""
}
Đọc tất cả tuần có trong tài liệu. % KPI theo từng tuần (1.1-1.8). NGUYÊN VĂN không tóm tắt.""",
        "C_san_pham": """Trích xuất SẢN PHẨM NGHIỆM THU từng tuần từ phần này. Trả JSON thuần:
{
  "san_pham_1":"","so_luong_file_1":"","link_dinh_kem_1":"","vi_pham_upload_1":"","kpi_sp_tuan_1":"",
  "san_pham_2":"","so_luong_file_2":"","link_dinh_kem_2":"","vi_pham_upload_2":"","kpi_sp_tuan_2":"",
  "san_pham_3":"","so_luong_file_3":"","link_dinh_kem_3":"","vi_pham_upload_3":"","kpi_sp_tuan_3":"",
  "san_pham_4":"","so_luong_file_4":"","link_dinh_kem_4":"","vi_pham_upload_4":"","kpi_sp_tuan_4":"",
  "san_pham_5":"","so_luong_file_5":"","link_dinh_kem_5":"","vi_pham_upload_5":"","kpi_sp_tuan_5":"",
  "san_pham_6":"","so_luong_file_6":"","link_dinh_kem_6":"","vi_pham_upload_6":"","kpi_sp_tuan_6":"",
  "san_pham_7":"","so_luong_file_7":"","link_dinh_kem_7":"","vi_pham_upload_7":"","kpi_sp_tuan_7":"",
  "san_pham_8":"","so_luong_file_8":"","link_dinh_kem_8":"","vi_pham_upload_8":"","kpi_sp_tuan_8":""
}
Lấy NGUYÊN VĂN toàn bộ tên sản phẩm và link. Ô trống → "".""",
        "D_hoi_nhap": """Trích xuất PHẦN III HỘI NHẬP (9 câu) từ phần này. Trả JSON thuần:
{
  "hoi_nhap_1_nv":"","hoi_nhap_1_hod":"",
  "hoi_nhap_2_nv":"","hoi_nhap_2_hod":"",
  "hoi_nhap_3_nv":"","hoi_nhap_3_hod":"",
  "hoi_nhap_4_nv":"","hoi_nhap_4_hod":"",
  "hoi_nhap_5_nv":"","hoi_nhap_5_hod":"",
  "hoi_nhap_6_nv":"","hoi_nhap_6_hod":"",
  "hoi_nhap_7_nv":"","hoi_nhap_7_hod":"",
  "hoi_nhap_7_1_nv":"","hoi_nhap_7_1_hod":"",
  "hoi_nhap_7_2_nv":"","hoi_nhap_7_2_hod":"",
  "hoi_nhap_7_3_nv":"","hoi_nhap_7_3_hod":"",
  "hoi_nhap_7_4_nv":"","hoi_nhap_7_4_hod":"",
  "hoi_nhap_7_5_nv":"","hoi_nhap_7_5_hod":"",
  "hoi_nhap_8_nv":"","hoi_nhap_8_hod":"",
  "hoi_nhap_9_nv":"","hoi_nhap_9_hod":""
}
Lấy NGUYÊN VĂN toàn bộ câu trả lời, không tóm tắt. Ô trống → "".""",
        "E_ket_luan": """Trích xuất KẾT LUẬN và ĐỀ XUẤT từ phần này. Trả JSON thuần:
{
  "ket_luan":"","de_xuat_ky_hd":"","de_xuat_tang_thu_nhap":"",
  "de_nghi_phoi_hop":"","y_kien_hod":"","y_kien_rtd":"",
  "ngay_ky":"","ten_hod_ky":""
}
Lấy NGUYÊN VĂN. Ô trống → ""."""
    }

    DOCX_APPENDABLE = {
        'cong_viec_duoc_giao',
        # Nhiem vu 1.6 - APPEND toan bo (noi_dung + ket_qua + ty_le + hod)
        'nhiem_vu_1_noi_dung','nhiem_vu_1_ket_qua','nhiem_vu_1_ty_le','nhiem_vu_1_hod',
        'nhiem_vu_2_noi_dung','nhiem_vu_2_ket_qua','nhiem_vu_2_ty_le','nhiem_vu_2_hod',
        'nhiem_vu_3_noi_dung','nhiem_vu_3_ket_qua','nhiem_vu_3_ty_le','nhiem_vu_3_hod',
        'nhiem_vu_4_noi_dung','nhiem_vu_4_ket_qua','nhiem_vu_4_ty_le','nhiem_vu_4_hod',
        'nhiem_vu_5_noi_dung','nhiem_vu_5_ket_qua','nhiem_vu_5_ty_le','nhiem_vu_5_hod',
        'nhiem_vu_6_noi_dung','nhiem_vu_6_ket_qua','nhiem_vu_6_ty_le','nhiem_vu_6_hod',
        'nhiem_vu_7_noi_dung','nhiem_vu_7_ket_qua','nhiem_vu_7_ty_le','nhiem_vu_7_hod',
        'nhiem_vu_8_noi_dung','nhiem_vu_8_ket_qua','nhiem_vu_8_ty_le','nhiem_vu_8_hod',
        'nhan_xet_1_nv','nhan_xet_2_nv','nhan_xet_3_nv','nhan_xet_4_nv','nhan_xet_5_nv',
        'nhan_xet_1_hod','nhan_xet_2_hod','nhan_xet_3_hod','nhan_xet_4_hod','nhan_xet_5_hod',
        'san_pham_1','san_pham_2','san_pham_3','san_pham_4',
        'san_pham_5','san_pham_6','san_pham_7','san_pham_8',
        'nhiem_vu_tuan_1','nhiem_vu_tuan_2','nhiem_vu_tuan_3','nhiem_vu_tuan_4',
        'nhiem_vu_tuan_5','nhiem_vu_tuan_6','nhiem_vu_tuan_7','nhiem_vu_tuan_8',
        'link_dinh_kem_1','link_dinh_kem_2','link_dinh_kem_3','link_dinh_kem_4',
        'link_dinh_kem_5','link_dinh_kem_6','link_dinh_kem_7','link_dinh_kem_8',
        'hoi_nhap_1_nv','hoi_nhap_2_nv','hoi_nhap_3_nv','hoi_nhap_4_nv',
        'hoi_nhap_5_nv','hoi_nhap_6_nv','hoi_nhap_7_nv',
        'hoi_nhap_7_1_nv','hoi_nhap_7_2_nv','hoi_nhap_7_3_nv',
        'hoi_nhap_7_4_nv','hoi_nhap_7_5_nv',
        'hoi_nhap_8_nv','hoi_nhap_9_nv',
    }

    def _merge_docx(base: dict, new: dict) -> dict:
        for k, v in new.items():
            if k == "confidence" or not v:
                continue
            if k in DOCX_APPENDABLE:
                existing = base.get(k, '')
                if existing:
                    nv = str(v).strip()
                    if nv and nv not in existing:
                        base[k] = existing.rstrip() + '\n' + nv
                else:
                    base[k] = v
            elif isinstance(v, dict) and isinstance(base.get(k), dict):
                for kk, vv in v.items():
                    if vv and not base[k].get(kk):
                        base[k][kk] = vv
            elif k not in base or not base[k]:
                base[k] = v
        return base

    if not sections:
        sections = {"A_thong_tin": raw_text}

    for sec_key, sec_text in sections.items():
        if not sec_text.strip():
            continue
        prompt = BATCH_PROMPTS.get(sec_key)
        if not prompt:
            continue
        batch_text = sec_text[:60000]
        frappe.logger("cnb_scan").info(f"[SCAN] DOCX batch {sec_key}: {len(batch_text)} chars")
        try:
            resp = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                messages=[{"role": "user", "content": prompt + "\n\nNỘI DUNG:\n" + batch_text}],
                temperature=0,
                max_tokens=16000,
                response_format={"type": "json_object"},
            )
            partial = json.loads(resp.choices[0].message.content or "{}")
            fields = _merge_docx(fields, partial)
        except Exception as e:
            frappe.logger("cnb_scan").warning(f"[SCAN] DOCX batch {sec_key} lỗi: {e}")


    return fields, raw_text


def _scan_extract_html(file_bytes, client):
    """
    Extract fields from HTML using a single OpenAI call.

    Returns:
        tuple: (fields dict, raw_text str)
    """

    fields = {}

    raw_text = _read_html_text(file_bytes)
    method_note = "HTML – đọc trực tiếp"
    if raw_text.strip():
        try:
            resp = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                messages=[{"role": "user", "content": _EXTRACT_PROMPT + raw_text[:80000]}],
                temperature=0,
                max_tokens=8000,
                response_format={"type": "json_object"},
            )
            fields = json.loads(resp.choices[0].message.content or "{}")
        except Exception as e:
            frappe.logger("cnb_scan").warning(f"[SCAN] HTML extract lỗi: {e}")


    return fields, raw_text


def _scan_extract_pdf_image(file_bytes, filename, client):
    """
    Extract fields from PDF/image using GPT-4o Vision with smart batching.

    Returns:
        tuple: (fields dict, raw_text str)
    """

    fields = {}
    raw_text = ""


    method_note = "GPT-4o Vision → JSON trực tiếp"
    frappe.logger("cnb_scan").info(f"[SCAN] Direct Vision→JSON: {filename}")

    # Build image parts
    if fname.endswith(".pdf"):
        page_images = _pdf_to_images(file_bytes)
    else:
        ext = fname.rsplit(".", 1)[-1]
        mime_map = {"jpg":"jpeg","jpeg":"jpeg","png":"png","bmp":"bmp","webp":"webp"}
        page_images = [file_bytes]  # single image

    if not page_images:
        frappe.throw(f"Không thể đọc file '{filename}'. Vui lòng kiểm tra định dạng.")

    frappe.logger("cnb_scan").info(f"[SCAN] {len(page_images)} trang → Vision batches")

    # Prompt cho Vision → JSON trực tiếp

    def _build_image_part(img_bytes: bytes) -> dict:
        b64 = base64.b64encode(img_bytes).decode()
        return {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "high"}
        }

    # Các field dài trải nhiều trang → APPEND thay vì first-wins
    APPENDABLE = {
        'cong_viec_duoc_giao',
        # Nhiệm vụ 1.6 — APPEND toàn bộ (nội dung + kết quả + % + HOD)
        # 1.6 có thể trải 3-4 trang, cần append cả ty_le và hod
        'nhiem_vu_1_noi_dung','nhiem_vu_1_ket_qua','nhiem_vu_1_ty_le','nhiem_vu_1_hod',
        'nhiem_vu_2_noi_dung','nhiem_vu_2_ket_qua','nhiem_vu_2_ty_le','nhiem_vu_2_hod',
        'nhiem_vu_3_noi_dung','nhiem_vu_3_ket_qua','nhiem_vu_3_ty_le','nhiem_vu_3_hod',
        'nhiem_vu_4_noi_dung','nhiem_vu_4_ket_qua','nhiem_vu_4_ty_le','nhiem_vu_4_hod',
        'nhiem_vu_5_noi_dung','nhiem_vu_5_ket_qua','nhiem_vu_5_ty_le','nhiem_vu_5_hod',
        'nhiem_vu_6_noi_dung','nhiem_vu_6_ket_qua','nhiem_vu_6_ty_le','nhiem_vu_6_hod',
        'nhiem_vu_7_noi_dung','nhiem_vu_7_ket_qua','nhiem_vu_7_ty_le','nhiem_vu_7_hod',
        'nhiem_vu_8_noi_dung','nhiem_vu_8_ket_qua','nhiem_vu_8_ty_le','nhiem_vu_8_hod',
        # Nhận xét chung (5 câu NV + HOD)
        'nhan_xet_1_nv','nhan_xet_2_nv','nhan_xet_3_nv',
        'nhan_xet_4_nv','nhan_xet_5_nv',
        'nhan_xet_1_hod','nhan_xet_2_hod','nhan_xet_3_hod',
        'nhan_xet_4_hod','nhan_xet_5_hod',
        # Sản phẩm (trải nhiều trang)
        'san_pham_1','san_pham_2','san_pham_3','san_pham_4',
        'san_pham_5','san_pham_6','san_pham_7','san_pham_8',
        'link_dinh_kem_1','link_dinh_kem_2','link_dinh_kem_3','link_dinh_kem_4',
        'link_dinh_kem_5','link_dinh_kem_6','link_dinh_kem_7','link_dinh_kem_8',
        # Hội nhập (9 câu, trải 11 trang)
        'hoi_nhap_1_nv','hoi_nhap_2_nv','hoi_nhap_3_nv','hoi_nhap_4_nv',
        'hoi_nhap_5_nv','hoi_nhap_6_nv','hoi_nhap_7_nv',
        'hoi_nhap_7_1_nv','hoi_nhap_7_2_nv','hoi_nhap_7_3_nv',
        'hoi_nhap_7_4_nv','hoi_nhap_7_5_nv',
        'hoi_nhap_8_nv','hoi_nhap_9_nv',
        # HOD hội nhập
        'hoi_nhap_1_hod','hoi_nhap_2_hod','hoi_nhap_3_hod','hoi_nhap_4_hod',
        'hoi_nhap_5_hod','hoi_nhap_6_hod','hoi_nhap_7_hod',
        'hoi_nhap_7_1_hod','hoi_nhap_7_2_hod','hoi_nhap_7_3_hod',
        'hoi_nhap_7_4_hod','hoi_nhap_7_5_hod',
        'hoi_nhap_8_hod','hoi_nhap_9_hod',
    }

    def _merge_fields(base: dict, new: dict) -> dict:
        """Merge batch JSON vào base:
        - APPENDABLE fields: nối thêm nội dung mới (nhiều trang)
        - Các field khác: first-wins (chỉ lấy giá trị đầu tiên non-empty)
        """
        for k, v in new.items():
            if k == "confidence":
                continue
            if not v:  # bỏ qua giá trị rỗng
                continue
            if k in APPENDABLE:
                existing = base.get(k, '')
                if existing:
                    # Nối vào nếu nội dung mới khác (tránh duplicate)
                    new_v = str(v).strip()
                    if new_v and new_v not in existing:
                        base[k] = existing.rstrip() + '\n' + new_v
                else:
                    base[k] = v
            elif isinstance(v, dict) and isinstance(base.get(k), dict):
                for kk, vv in v.items():
                    if vv and not base[k].get(kk):
                        base[k][kk] = vv
            elif k not in base or not base[k]:
                base[k] = v
        return base

    fields = {}
    total_pages = len(page_images)

    # ── Prompt chuyên biệt cho phần Hội Nhập (trang 9 trở đi) ──────────────

    # ── Smart batching ────────────────────────────────────────────────────
    # Trang 1-8: batch 2 trang (thông tin chung, KPI, sản phẩm)
    # Trang 9+:  batch 4 trang với HOI_NHAP_PROMPT chuyên biệt
    SPLIT_PAGE = 8   # từ trang 9 trở đi là hội nhập
    HN_BATCH   = 4   # 4 trang/batch cho hội nhập

    def _call_batch(imgs, prompt, label):
        parts = [_build_image_part(img) for img in imgs]
        msg_content = [{"type": "text", "text": prompt}, *parts]
        try:
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": msg_content}],
                temperature=0,
                max_tokens=16000,
                response_format={"type": "json_object"},
            )
            txt = resp.choices[0].message.content or "{}"
            return txt, json.loads(txt)
        except Exception as e:
            frappe.logger("cnb_scan").warning(f"[SCAN] Batch {label} lỗi: {e}")
            return "{}", {}

    # ── Phase 0: Detect section trên từng trang (cheap – detail:low) ────────
    DETECT_PROMPT = (
        'Nhìn vào trang phiếu đánh giá thử việc CT Group này. '
        'Trả về JSON: {"section": "...", "page_label": "..."}\n'
        'section phải là 1 trong: "A_thong_tin", "I_nhan_xet", "II_kpi", '
        '"II_san_pham", "III_hoi_nhap", "C_ket_luan"\n'
        'page_label: số trang in trên phiếu, nếu không thấy để "".\n\n'
        'QUY TẮC (ưu tiên từ trên xuống):\n'
        '1. Thấy "HỘI NHẬP"/"Sứ mệnh"/"Tầm nhìn"/"Văn hóa"/"7.1"/"III." → III_hoi_nhap\n'
        '2. Tick chọn "ĐẠT"/"Không đạt"/"RTD"/"Kết luận" → C_ket_luan\n'
        '3. Thấy "Sản phẩm nghiệm thu"/cột "Link đính kèm"/"Tên sản phẩm" → II_san_pham\n'
        '4. Thấy "1.1"/"1.2"/"1.3"/"1.4"/"1.5"/"1.6"/"1.7"/"1.8"/"1.9"/"1.10"/'
        '"Điểm TBC"/"KPI"/"Công việc được giao"/"PHẦN II" → II_kpi\n'
        '5. Thấy bảng nhiều hàng với cột "Kết quả thực tế" + cột "%" '
        '(dù không có header 1.10 — đây là trang tiếp theo của 1.10) → II_kpi\n'
        '6. Thấy "PHẦN I"/"Nhận xét chung" → I_nhan_xet\n'
        '7. Bảng thông tin (họ tên, ngày nhận việc, bộ phận) → A_thong_tin\n'
        '⚠️ Bảng 1.10 trải nhiều trang: trang tiếp theo không có header '
        'nhưng có dòng nhiệm vụ + cột % → vẫn là II_kpi, KHÔNG phải II_san_pham.'
    )

    def _detect_section(img_bytes):
        b64 = base64.b64encode(img_bytes).decode()
        part = {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "low"}}
        try:
            r = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": [{"type": "text", "text": DETECT_PROMPT}, part]}],
                temperature=0, max_tokens=60,
                response_format={"type": "json_object"},
            )
            d = json.loads(r.choices[0].message.content or "{}")
            return d.get("section", "II_kpi"), d.get("page_label", "")
        except Exception:
            return "II_kpi", ""

    # Detect section cho từng trang
    page_sections = []
    for idx, img in enumerate(page_images):
        sec, lbl = _detect_section(img)
        page_sections.append(sec)
        frappe.logger("cnb_scan").info(f"[SCAN] Page {idx+1} → section={sec} label={lbl}")

    # ── Prompt chuyên biệt cho KPI (1.1–1.6) ───────────────────────────────



    # ── Prompt chuyên biệt cho KPI (1.1–1.10) ───────────────────────────────

    # ── Prompt chuyên biệt cho Sản Phẩm (2.1–2.8) ──────────────────────────

    # Map section → group_type
    HOI_NHAP_SECS  = {"III_hoi_nhap", "C_ket_luan"}
    KPI_SECS       = {"II_kpi"}
    SAN_PHAM_SECS  = {"II_san_pham"}

    def _sec_to_type(sec: str) -> str:
        if sec in HOI_NHAP_SECS: return "hoi_nhap"
        if sec in KPI_SECS:      return "kpi"
        if sec in SAN_PHAM_SECS: return "san_pham"
        return "general"

    # Batch sizes theo loại
    # kpi: tăng lên 3 trang — 1.6 có thể trải 3-4 trang, cần đủ context bảng
    BATCH_SIZES = {"hoi_nhap": 3, "kpi": 4, "san_pham": 4, "general": 2}
    PROMPT_MAP  = {
        "hoi_nhap": HOI_NHAP_PROMPT,
        "kpi":      KPI_PROMPT,
        "san_pham": SAN_PHAM_PROMPT,
        "general":  VISION_JSON_PROMPT,
    }

    # Smooth Pass 1: trang general kẹt giữa 2 hoi_nhap → III_hoi_nhap
    #                  trang GENERAL kẹt giữa 2 kpi → kpi (KHÔNG kéo san_pham vào kpi)
    for idx in range(1, len(page_sections) - 1):
        prev_t = _sec_to_type(page_sections[idx-1])
        cur_t  = _sec_to_type(page_sections[idx])
        nxt_t  = _sec_to_type(page_sections[idx+1])
        if cur_t == "general" and prev_t == "hoi_nhap" and nxt_t == "hoi_nhap":
            page_sections[idx] = "III_hoi_nhap"
            frappe.logger("cnb_scan").info(f"[SCAN] Page {idx+1} re-classified → III_hoi_nhap (sandwich)")
        elif cur_t == "general" and prev_t == "kpi" and nxt_t == "kpi":
            page_sections[idx] = "II_kpi"
            frappe.logger("cnb_scan").info(f"[SCAN] Page {idx+1} re-classified → II_kpi (sandwich general)")

    # Pass 2 - kpi → kpi nếu gặp general sau kpi (NV5-7 trải nhiều trang)
    for idx in range(1, len(page_sections)):
        prev_t = _sec_to_type(page_sections[idx-1])
        cur_t  = _sec_to_type(page_sections[idx])
        if prev_t == "kpi" and cur_t == "general":
            page_sections[idx] = "II_kpi"
            frappe.logger("cnb_scan").info(f"[SCAN] Page {idx+1} re-classified → II_kpi (forward-prop)")

    # Pass 3 - Zone-based fill (thay forward-prop san_pham → kpi):
    # Phát hiện vùng san_pham = [first_sp, last_sp].
    # Mọi trang kpi/general NẰM TRONG vùng đó → reclassify thành san_pham.
    # Điều này ổn định hơn forward-prop vì detect có thể sai ±1 trang.
    sp_indices = [i for i, s in enumerate(page_sections) if _sec_to_type(s) == "san_pham"]
    if sp_indices:
        first_sp = min(sp_indices)
        last_sp  = max(sp_indices)
        for idx in range(first_sp, last_sp + 1):
            if _sec_to_type(page_sections[idx]) == "kpi":
                page_sections[idx] = "II_san_pham"
                frappe.logger("cnb_scan").info(
                    f"[SCAN] Page {idx+1} re-classified → II_san_pham (zone-fill [{first_sp+1}-{last_sp+1}])"
                )

    # Nhóm trang liên tiếp cùng loại thành batches
    groups = []
    i = 0
    while i < total_pages:
        cur_type = _sec_to_type(page_sections[i])
        bs = BATCH_SIZES[cur_type]
        batch_imgs = []
        grp_start  = i + 1
        while i < total_pages and len(batch_imgs) < bs:
            if _sec_to_type(page_sections[i]) != cur_type:
                break
            batch_imgs.append(page_images[i])
            i += 1
        groups.append({"type": cur_type, "imgs": batch_imgs, "start": grp_start})

    # ── Bridge batch: KPI_PROMPT chạy thêm trên vùng giáp ranh kpi→san_pham ──
    # Bảng 1.10 (nhiệm vụ + %) thường nằm ngay sau vùng kpi → bị detect là
    # san_pham → SAN_PHAM_PROMPT xử lý sai → nhiem_vu_X_ty_le trống.
    # Bridge batch = [trang kpi cuối + 3 trang sp đầu] chạy KPI_PROMPT trước
    # để capture đủ % hoàn thành từng nhiệm vụ.
    _sp_idx  = [j for j, s in enumerate(page_sections) if _sec_to_type(s) == "san_pham"]
    _kpi_idx = [j for j, s in enumerate(page_sections) if _sec_to_type(s) == "kpi"]
    if _sp_idx and _kpi_idx:
        _first_sp = min(_sp_idx)
        _kpi_before = [k for k in _kpi_idx if k < _first_sp]
        if _kpi_before:
            _bridge_start = max(_kpi_before)          # trang kpi cuối trước san_pham
            _bridge_end   = min(_first_sp + 3, total_pages)  # +3 trang sp đầu
            bridge_imgs   = [page_images[j] for j in range(_bridge_start, _bridge_end)]
            bridge_pg_s   = _bridge_start + 1
            bridge_pg_e   = _bridge_end
            frappe.logger("cnb_scan").info(
                f"[SCAN] Bridge KPI batch: trang {bridge_pg_s}–{bridge_pg_e} "
                f"(bảng 1.10 boundary)"
            )
            _btxt, _bpart = _call_batch(bridge_imgs, PROMPT_MAP["kpi"],
                                         f"trang {bridge_pg_s}–{bridge_pg_e} [kpi-bridge]")
            raw_text += f"\n\n=== trang {bridge_pg_s}–{bridge_pg_e} [kpi-bridge] ===\n" + _btxt
            fields = _merge_fields(fields, _bpart)

    # ── Phase 1+2: Extract từng group với prompt chuyên biệt ─────────────
    for grp in groups:
        prompt = PROMPT_MAP[grp["type"]]
        pg_s   = grp["start"]
        pg_e   = grp["start"] + len(grp["imgs"]) - 1
        label  = f"trang {pg_s}–{pg_e}/{total_pages} [{grp['type']}]"
        frappe.logger("cnb_scan").info(f"[SCAN] Extract: {label}")
        txt, partial = _call_batch(grp["imgs"], prompt, label)
        raw_text += f"\n\n=== {label} ===\n" + txt
        fields = _merge_fields(fields, partial)

    return fields, raw_text


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

def _parse_xml_to_fields(xml_str: str) -> dict:
    """Parse XML phiếu → dict fields (theo cấu trúc thực tế CTG-GO-NLCD-QT16-BM01)."""
    import xml.etree.ElementTree as ET

    def txt(el, tag, default=""):
        node = el.find(tag) if el is not None else None
        return (node.text or "").strip() if node is not None and node.text else default

    def attr(el, tag, att, default=""):
        node = el.find(tag) if el is not None else None
        return (node.get(att) or default).strip() if node is not None else default

    try:
        root = ET.fromstring(xml_str)
    except Exception:
        return {}

    fields = {}

    # A. Thông tin chung
    tc = root.find('ThongTinChung')
    fields['ho_ten']           = txt(tc, 'TenNhanVien')
    fields['ma_nhan_su']       = txt(tc, 'MaNhanVien')
    fields['chuc_danh']        = txt(tc, 'ChucDanh')
    fields['phong_ban']        = txt(tc, 'DonVi')
    fields['cong_ty']          = txt(tc, 'CongTy')
    fields['ngay_nhan_viec']   = txt(tc, 'NgayNhanViec')
    fields['ngay_het_han']     = txt(tc, 'NgayHetHan')
    fields['thoi_gian_thu_viec'] = txt(tc, 'ThoiGianThuViec')
    fields['loai_hop_dong']    = txt(tc, 'LoaiHopDong')
    fields['ten_hod']          = txt(tc, 'TenHOD')
    fields['ma_hod']           = txt(tc, 'MaHOD')
    fields['chuc_danh_hod']    = txt(tc, 'ChucDanhHOD')
    fields['don_vi_hod']       = txt(tc, 'DonViHOD')

    # B. Phần I – Nhận xét chung
    p1 = root.find('PhanI_NhanXetChung')
    if p1 is not None:
        for nx in p1.findall('NhanXet'):
            i = nx.get('stt','')
            fields[f'nhan_xet_{i}_nv']  = txt(nx, 'NV')
            fields[f'nhan_xet_{i}_hod'] = txt(nx, 'HOD')

    # C. Phần II – KPI
    p2 = root.find('PhanII_KPI')
    if p2 is not None:
        for tuan in p2.findall('Tuan'):
            i = tuan.get('so','')
            fields[f'kpi_tuan_{i}_ty_le'] = tuan.get('tyLe','')
        fields['diem_tbc_kpi_nv']   = txt(p2, 'DiemTBC_NV')
        fields['diem_tbc_kpi_hod']  = txt(p2, 'DiemTBC_HOD')
        fields['cong_viec_duoc_giao'] = txt(p2, 'CongViecDuocGiao')

    # C2. Nhiệm vụ – nằm trong root-level <CongViecDuocGiao> (KHÔNG phải trong PhanII_KPI)
    cvdg = root.find('CongViecDuocGiao')
    if cvdg is not None:
        for nv in cvdg.findall('NhiemVu'):
            i = nv.get('so', '')
            if not i:
                continue
            fields[f'nhiem_vu_{i}_noi_dung'] = txt(nv, 'NoiDung')
            fields[f'nhiem_vu_{i}_ket_qua']  = txt(nv, 'KetQua')
            fields[f'nhiem_vu_{i}_ty_le']     = nv.get('tyLe', '')
            fields[f'nhiem_vu_{i}_hod']       = txt(nv, 'HOD')

    sp_root = root.find('SanPhamNghiemThu')
    if sp_root is not None:
        for sp in sp_root.findall('SanPham'):
            i = sp.get('tuan','')
            fields[f'san_pham_{i}']       = txt(sp, 'DanhSach')
            fields[f'so_luong_file_{i}']  = txt(sp, 'SoLuongFile')
            fields[f'link_dinh_kem_{i}']  = txt(sp, 'DuongLinkDinhKem')
            fields[f'vi_pham_upload_{i}'] = txt(sp, 'SoLanViPhamUpload')
            fields[f'kpi_sp_tuan_{i}']    = sp.get('tyLeKPI','')

    # D. Phần III – Hội nhập
    p3 = root.find('PhanIII_HoiNhap')
    if p3 is not None:
        for cau in p3.findall('CauHoi'):
            i = cau.get('so','')
            fields[f'hoi_nhap_{i}_nv']  = txt(cau, 'NV')
            fields[f'hoi_nhap_{i}_hod'] = txt(cau, 'HOD')
        sub7 = p3.find('SubCau7')
        if sub7 is not None:
            for sub in sub7.findall('Sub'):
                so = sub.get('so','').replace('.','_')
                nv  = sub.find('NV')
                hod = sub.find('HOD')
                fields[f'hoi_nhap_{so}_nv']  = (nv.text  or '').strip() if nv  is not None else ''
                fields[f'hoi_nhap_{so}_hod'] = (hod.text or '').strip() if hod is not None else ''

    # E. Kết luận
    kl = root.find('KetLuan')
    fields['ket_luan']              = txt(kl, 'KetQua')
    fields['de_xuat_ky_hd']         = txt(kl, 'DeXuatKyHD')
    fields['de_xuat_tang_thu_nhap'] = txt(kl, 'DeXuatTangThuNhap')
    fields['de_nghi_phoi_hop']      = txt(kl, 'DeNghiPhoiHop')
    fields['y_kien_hod']            = txt(kl, 'YKienHOD')
    fields['y_kien_rtd']            = txt(kl, 'YKienRTD')
    fields['ngay_ky']               = txt(kl, 'NgayKy')
    fields['ten_hod_ky']            = txt(kl, 'TenHODKy')

    return fields


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

def _check_deadline(date_str: str) -> dict:
    import datetime
    if not date_str:
        return {"deadline_alert": False, "so_ngay_con_lai": None, "ngay_het_han_parsed": None}
    for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"]:
        try:
            d = datetime.datetime.strptime(date_str.strip(), fmt).date()
            delta = (d - date.today()).days
            return {
                "deadline_alert": delta <= 7,
                "so_ngay_con_lai": delta,
                "ngay_het_han_parsed": d.isoformat(),
            }
        except ValueError:
            continue
    return {"deadline_alert": False, "so_ngay_con_lai": None, "ngay_het_han_parsed": None}


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

