# Copyright (c) 2026, antruong and contributors
# For license information, please see license.txt

"""Service layer for Manager Proposal Evaluation (Đánh giá đề xuất Quản lý/HOD).

Handles OCR extraction from scanned PDF proposal documents (tờ trình đề xuất)
and AI evaluation of each proposal item against 7 criteria (100 points total).

Only scanned PDF files are supported.
"""

import base64
import io
import json
import os
import time

import frappe

from cnb_2as.services.openai_client import get_client as _get_client, get_model as _get_model
from cnb_2as.services.prompts.de_xuat_prompts import (
    EXTRACTION_SYSTEM,
    EXTRACTION_USER_PROMPT,
    EVALUATION_SYSTEM,
    build_evaluation_user_prompt,
)


_MAX_FILE_SIZE_BYTES = 30 * 1024 * 1024  # 30MB
_MAX_PAGES = 20


# ── File helpers ───────────────────────────────────────────────────────────────

def get_file_path(file_url: str) -> str:
    """Resolve a Frappe file URL to an absolute filesystem path."""
    file_doc = frappe.db.get_value(
        "File", {"file_url": file_url}, ["file_name", "is_private", "file_url", "name"], as_dict=True
    )
    if not file_doc:
        raise ValueError(f"File không tồn tại trong hệ thống: {file_url}")

    site_path = frappe.get_site_path()
    if file_doc.get("is_private"):
        return os.path.join(site_path, "private", "files", file_doc["file_name"])
    return os.path.join(site_path, "public", "files", file_doc["file_name"])


def _validate_file(file_path: str):
    if not os.path.exists(file_path):
        raise ValueError(f"File không tồn tại trên đĩa: {file_path}")
    ext = os.path.splitext(file_path)[1].lower()
    if ext != ".pdf":
        raise ValueError("Chỉ hỗ trợ file PDF scan. Vui lòng upload file .pdf")
    size = os.path.getsize(file_path)
    if size == 0:
        raise ValueError("File rỗng, không thể xử lý")
    if size > _MAX_FILE_SIZE_BYTES:
        raise ValueError(
            f"File quá lớn ({size / 1024 / 1024:.1f}MB). Giới hạn: {_MAX_FILE_SIZE_BYTES / 1024 / 1024:.0f}MB"
        )


def _pdf_to_base64_images(file_path: str, max_pages: int = _MAX_PAGES) -> list:
    """Convert scanned PDF pages to base64 JPEG images for vision LLM OCR.

    200 DPI is the sweet spot for vision LLM accuracy without payload bloat
    (higher DPI does not improve accuracy but increases size quadratically).
    Grayscale + contrast enhancement helps with faded/low-quality scans.
    """
    import fitz
    from PIL import Image, ImageEnhance

    doc = fitz.open(file_path)
    images = []

    for i in range(min(len(doc), max_pages)):
        page = doc[i]
        # 200 DPI: ~48% smaller than 3x matrix, same OCR accuracy for vision LLMs
        pix = page.get_pixmap(dpi=200)
        img = Image.open(io.BytesIO(pix.tobytes("png")))

        # Crop CamScanner watermark (bottom-right corner)
        w, h = img.size
        img = img.crop((0, 0, int(w * 0.96), int(h * 0.94)))

        # Contrast boost helps vision LLMs read faded or low-contrast scans
        gray = img.convert("L")
        img = ImageEnhance.Contrast(gray).enhance(1.4).convert("RGB")

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80, optimize=True)
        images.append(base64.b64encode(buf.getvalue()).decode("utf-8"))

    doc.close()
    return images


def _count_pages(file_path: str) -> int:
    """Return page count for a PDF file."""
    try:
        import fitz
        doc = fitz.open(file_path)
        n = len(doc)
        doc.close()
        return n
    except Exception:
        return 1


def _log_tokens(
    response,
    evaluation_name: str,
    label: str = "de_xuat_service",
    is_ocr: bool = False,
    session_id: str = "",
):
    """Log token usage using ActivityLogger to link with a CNB Session."""
    try:
        usage = response.usage
        if not usage:
            return
            
        from cnb_2as.utils.activity_logger import ActivityLogger
        logger = ActivityLogger(prefix="CNB", module="Proposal Evaluation")
        
        resolved_session_id = session_id or f"de_xuat_{evaluation_name}"
        session_name = frappe.db.get_value(
            "CNB Session",
            {"session_id": resolved_session_id},
        )
        if not session_name:
            session_name = logger.create_session(
                session_id=resolved_session_id,
                dept="HR",
            )

        action_name = logger.start_action(session_name, action_type=label)
        ai_model = getattr(response, "model", "gpt-4o")
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)

        logger.log_ai_call(
            session_name=session_name,
            action_name=action_name,
            call_type=label,
            ai_model=ai_model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            status="success",
            is_ocr=is_ocr,
        )

        logger.finish_action(
            action_name,
            status="success",
            ai_model=ai_model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
    except Exception as e:
        try:
            frappe.db.rollback()
        except Exception:
            pass
        try:
            frappe.log_error(
                title=f"DeXuat token logging failed: {label}",
                message=frappe.get_traceback() or str(e),
            )
        except Exception:
            pass


# ── OCR + Extraction ───────────────────────────────────────────────────────────

def extract_proposal_data(
    file_url: str,
    evaluation_name: str = "",
    session_id: str = "",
) -> dict:
    """OCR and extract structured data from a scanned PDF proposal.

    Sends all pages in a single request so the model sees full document context.
    Image size is kept under payload limits by using 200 DPI + JPEG quality 80.

    Returns:
        Dict with keys: extracted, page_count, warnings, missing_fields.
    """
    file_path = get_file_path(file_url)
    _validate_file(file_path)

    page_count = _count_pages(file_path)
    print(f"[DeXuat] extract start: {os.path.basename(file_path)} (.pdf, {page_count}p)")
    start = time.time()

    b64_images = _pdf_to_base64_images(file_path)
    client = _get_client()
    model = _get_model("gpt-4o")

    print(f"[DeXuat] OCR {len(b64_images)} trang trong 1 request...")
    content = [
        {
            "type": "text",
            "text": (
                f"Tờ trình gồm {len(b64_images)} trang (đính kèm theo thứ tự).\n"
                f"Đọc TẤT CẢ {len(b64_images)} trang, tổng hợp toàn bộ rồi trích xuất:\n\n{EXTRACTION_USER_PROMPT}"
            ),
        }
    ]
    for i, b64 in enumerate(b64_images):
        content.append({"type": "text", "text": f"[Trang {i + 1}/{len(b64_images)}]"})
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": "high"},
        })

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": EXTRACTION_SYSTEM},
            {"role": "user", "content": content},
        ],
        response_format={"type": "json_object"},
        max_tokens=16000,
        temperature=0,
    )
    _log_tokens(
        resp,
        evaluation_name=evaluation_name,
        label="extract_proposal_ocr",
        is_ocr=True,
        session_id=session_id,
    )

    elapsed = time.time() - start
    tokens = resp.usage.total_tokens if resp.usage else 0
    print(f"[DeXuat] extract done: {elapsed:.1f}s, {tokens} tokens")

    raw = (resp.choices[0].message.content or "").strip()
    raw = raw.lstrip("```json").lstrip("```").rstrip("```").strip()
    try:
        extracted = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"AI trả về JSON không hợp lệ: {e}\nRaw: {raw[:500]}")

    return _build_extraction_result(extracted, page_count)



def _build_extraction_result(extracted: dict, page_count: int) -> dict:
    """Wrap extracted data with metadata."""
    return {
        "extracted": extracted,
        "page_count": page_count,
        "warnings": extracted.get("extractionWarnings", []),
        "missing_fields": extracted.get("missingFields", []),
    }


# ── Salary computation ─────────────────────────────────────────────────────────

def compute_salary_delta(proposal_items: list) -> list:
    """Compute deltaValue and deltaPercent for SALARY_INCREASE items."""
    for item in proposal_items:
        if item.get("proposalType") == "SALARY_INCREASE":
            try:
                current = _parse_salary(item.get("currentValue"))
                proposed = _parse_salary(item.get("proposedValue"))
                if current and proposed:
                    delta = proposed - current
                    pct = round(delta / current * 100, 2)
                    item["deltaValue"] = str(int(delta))
                    item["deltaPercent"] = pct
            except (TypeError, ValueError, ZeroDivisionError):
                pass
    return proposal_items


def _parse_salary(val) -> float:
    """Parse salary value from string or number."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    cleaned = str(val).replace(",", "").replace(".", "").replace(" ", "").replace("đồng", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


# ── Evaluation ─────────────────────────────────────────────────────────────────

def evaluate_proposals(
    extracted_data: dict,
    reference_data: dict = None,
    evaluation_name: str = "",
    session_id: str = "",
) -> dict:
    """Evaluate proposal items against 7 criteria (100 points).

    Args:
        extracted_data: Confirmed extracted proposal data.
        reference_data: Optional internal reference data (JD, salary bands, etc.).

    Returns:
        Evaluation result dict matching the output schema.
    """
    if "proposalItems" in extracted_data:
        extracted_data["proposalItems"] = compute_salary_delta(
            extracted_data["proposalItems"]
        )

    client = _get_client()
    model = _get_model("gpt-4o")

    user_prompt = build_evaluation_user_prompt(extracted_data, reference_data)

    print("[DeXuat] evaluating proposals...")
    start = time.time()

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": EVALUATION_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        max_tokens=16000,
        temperature=0,
    )
    _log_tokens(
        resp,
        evaluation_name=evaluation_name,
        label="evaluate_proposal",
        is_ocr=False,
        session_id=session_id,
    )

    raw = (resp.choices[0].message.content or "").strip()
    raw = raw.lstrip("```json").lstrip("```").rstrip("```").strip()
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        raise ValueError("GPT trả về JSON không hợp lệ khi đánh giá đề xuất")

    elapsed = time.time() - start
    print(f"[DeXuat] evaluation done: {elapsed:.1f}s")

    evals = result.get("proposalEvaluations", [])
    if evals:
        result["overallScore"] = round(sum(e.get("score", 0) for e in evals) / len(evals), 1)
        _rec_order = ["REJECT", "REQUEST_MORE_INFO", "PARTIALLY_APPROVE", "APPROVE_WITH_CONDITIONS", "APPROVE"]
        recs = [e.get("recommendation", "REJECT") for e in evals]
        result["overallRecommendation"] = min(recs, key=lambda r: _rec_order.index(r) if r in _rec_order else 0)
    else:
        result["overallScore"] = 0
        result["overallRecommendation"] = "REQUEST_MORE_INFO"

    return result
