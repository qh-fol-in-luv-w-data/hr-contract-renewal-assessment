# Copyright (c) 2026, antruong and contributors
# For license information, please see license.txt

"""Service layer for Manager Proposal Evaluation (Đánh giá đề xuất Quản lý/HOD).

Handles OCR extraction from uploaded proposal documents (tờ trình đề xuất)
and AI evaluation of each proposal item against 7 criteria (100 points total).
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


_ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".docx", ".doc"}
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
    if ext not in _ALLOWED_EXTENSIONS:
        raise ValueError(f"Định dạng file không được hỗ trợ: {ext}")
    size = os.path.getsize(file_path)
    if size == 0:
        raise ValueError("File rỗng, không thể xử lý")
    if size > _MAX_FILE_SIZE_BYTES:
        raise ValueError(
            f"File quá lớn ({size / 1024 / 1024:.1f}MB). Giới hạn: {_MAX_FILE_SIZE_BYTES / 1024 / 1024:.0f}MB"
        )


def _pdf_to_base64_images(file_path: str, max_pages: int = _MAX_PAGES) -> list:
    """Convert PDF pages to base64 JPEG images using PyMuPDF."""
    import fitz
    from PIL import Image

    doc = fitz.open(file_path)
    images = []
    mat = fitz.Matrix(3.0, 3.0)

    for i in range(min(len(doc), max_pages)):
        page = doc[i]
        pix = page.get_pixmap(matrix=mat)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        w, h = img.size
        # Crop CamScanner watermark bottom-right
        img = img.crop((0, 0, int(w * 0.96), int(h * 0.94)))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        images.append(base64.b64encode(buf.getvalue()).decode("utf-8"))

    doc.close()
    return images


def _image_to_base64(file_path: str) -> list:
    """Convert an image file to a base64 string (single-element list)."""
    from PIL import Image

    img = Image.open(file_path)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return [base64.b64encode(buf.getvalue()).decode("utf-8")]


def _docx_to_text(file_path: str) -> str:
    """Extract plain text from a DOCX file."""
    from docx import Document

    doc = Document(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def _count_pages(file_path: str) -> int:
    """Return page count for PDF, else 1."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        try:
            import fitz
            doc = fitz.open(file_path)
            n = len(doc)
            doc.close()
            return n
        except Exception:
            return 1
    return 1


def _log_tokens(response, label: str = "de_xuat_service"):
    """Log token usage to cnb_ai_call_log."""
    try:
        usage = response.usage
        if not usage:
            return
        frappe.get_doc({
            "doctype": "Cnb Ai Call Log",
            "model": getattr(response, "model", "gpt-4o"),
            "label": label,
            "tokens_in": usage.prompt_tokens,
            "tokens_out": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
        }).insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception:
        pass


# ── OCR + Extraction ───────────────────────────────────────────────────────────

def extract_proposal_data(file_url: str) -> dict:
    """OCR and extract structured data from a proposal document.

    Args:
        file_url: Frappe file URL for the uploaded proposal.

    Returns:
        Dict with keys:
          - raw_pages: list of raw OCR text per page
          - extracted: structured extracted JSON dict
          - page_count: number of pages processed
          - warnings: list of extraction warnings
          - missing_fields: list of missing field names
    """
    file_path = get_file_path(file_url)
    _validate_file(file_path)

    ext = os.path.splitext(file_path)[1].lower()
    page_count = _count_pages(file_path)

    print(f"[DeXuat] extract start: {os.path.basename(file_path)} ({ext}, {page_count}p)")
    start = time.time()

    client = _get_client()
    model = _get_model("gpt-4o")

    system_msg = EXTRACTION_SYSTEM
    user_prompt = EXTRACTION_USER_PROMPT

    # Build image list based on file type
    if ext == ".pdf":
        b64_images = _pdf_to_base64_images(file_path)
    elif ext in (".png", ".jpg", ".jpeg"):
        b64_images = _image_to_base64(file_path)
    else:
        # DOCX/DOC — extract text and send as text-only prompt
        text_content = _docx_to_text(file_path)
        return _extract_from_text(text_content, client, model, system_msg, user_prompt)

    # Single request with ALL pages — AI sees full document at once
    print(f"[DeXuat] OCR all {len(b64_images)} pages in one request...")
    content = [
        {
            "type": "text",
            "text": (
                f"Tờ trình gồm {len(b64_images)} trang (đính kèm bên dưới theo thứ tự).\n"
                f"Hãy đọc TẤT CẢ {len(b64_images)} trang, tổng hợp thông tin từ toàn bộ tài liệu "
                f"rồi trích xuất đầy đủ:\n\n{user_prompt}"
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
            {"role": "system", "content": system_msg},
            {"role": "user", "content": content},
        ],
        response_format={"type": "json_object"},
        max_tokens=16000,
        temperature=0,
    )
    _log_tokens(resp, label="de_xuat_service.extract_proposal_data")
    elapsed = time.time() - start
    tokens = resp.usage.total_tokens if resp.usage else 0
    print(f"[DeXuat] extract done: {elapsed:.1f}s, {tokens} tokens")

    raw = resp.choices[0].message.content or ""
    raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
    try:
        merged = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"AI trả về JSON không hợp lệ: {e}\nRaw (500 chars): {raw[:500]}")

    return _build_extraction_result(merged, page_count)


def _extract_from_text(text_content: str, client, model: str, system_msg: str, user_prompt: str) -> dict:
    """Extract from plain text content (DOCX)."""
    start = time.time()
    print("[DeXuat] extracting from DOCX text content...")

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": f"Nội dung tờ trình:\n\n{text_content}\n\n{user_prompt}"},
        ],
        response_format={"type": "json_object"},
        max_tokens=16000,
        temperature=0,
    )
    _log_tokens(resp, label="de_xuat_service.extract_from_text")

    raw = resp.choices[0].message.content or ""
    raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
    try:
        extracted = json.loads(raw)
    except json.JSONDecodeError:
        raise ValueError("GPT trả về JSON không hợp lệ khi trích xuất từ DOCX")

    elapsed = time.time() - start
    print(f"[DeXuat] DOCX extract done: {elapsed:.1f}s")
    return _build_extraction_result(extracted, 1)


def _merge_page_results(pages: list) -> dict:
    """Merge extracted data from multiple pages into one dict."""
    if not pages:
        return {}
    merged = pages[0]

    for page in pages[1:]:
        # Merge proposalItems (deduplicate by proposalType+fieldName)
        existing_items = {
            f"{x.get('proposalType')}|{x.get('fieldName')}": True
            for x in merged.get("proposalItems", [])
        }
        for item in page.get("proposalItems", []):
            key = f"{item.get('proposalType')}|{item.get('fieldName')}"
            if key not in existing_items:
                merged.setdefault("proposalItems", []).append(item)

        # Merge workResults
        existing_results = {x.get("itemName", ""): True for x in merged.get("workResults", [])}
        for wr in page.get("workResults", []):
            if wr.get("itemName") not in existing_results:
                merged.setdefault("workResults", []).append(wr)

        # Fill empty scalar fields from later pages
        for section in ["documentMetadata", "employee", "proposalSummary", "evaluationContext"]:
            if isinstance(merged.get(section), dict) and isinstance(page.get(section), dict):
                for k, v in page[section].items():
                    if v is not None and not merged[section].get(k):
                        merged[section][k] = v

        # Merge warnings and missing fields
        for key in ["extractionWarnings", "missingFields", "proposalBasis", "commitmentsAfterApproval", "signatories"]:
            existing = set(str(x) for x in merged.get(key, []))
            for item in page.get(key, []):
                if str(item) not in existing:
                    merged.setdefault(key, []).append(item)

    return merged


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

def evaluate_proposals(extracted_data: dict, reference_data: dict = None) -> dict:
    """Evaluate proposal items against 7 criteria (100 points).

    Args:
        extracted_data: Confirmed extracted proposal data.
        reference_data: Optional internal reference data (JD, salary bands, etc.).

    Returns:
        Evaluation result dict matching the output schema.
    """
    # Compute salary deltas before evaluation
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
    _log_tokens(resp, label="de_xuat_service.evaluate_proposals")

    raw = resp.choices[0].message.content or ""
    raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        raise ValueError("GPT trả về JSON không hợp lệ khi đánh giá đề xuất")

    elapsed = time.time() - start
    print(f"[DeXuat] evaluation done: {elapsed:.1f}s")

    # Compute overall score from proposalEvaluations
    evals = result.get("proposalEvaluations", [])
    if evals:
        result["overallScore"] = round(sum(e.get("score", 0) for e in evals) / len(evals), 1)
        # Overall recommendation = worst recommendation across all proposals
        _rec_order = ["REJECT", "REQUEST_MORE_INFO", "PARTIALLY_APPROVE", "APPROVE_WITH_CONDITIONS", "APPROVE"]
        recs = [e.get("recommendation", "REJECT") for e in evals]
        result["overallRecommendation"] = min(recs, key=lambda r: _rec_order.index(r) if r in _rec_order else 0)
    else:
        result["overallScore"] = 0
        result["overallRecommendation"] = "REQUEST_MORE_INFO"

    return result
