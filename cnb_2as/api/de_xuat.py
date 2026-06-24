# Copyright (c) 2026, antruong and contributors
# For license information, please see license.txt

"""API endpoints for Manager Proposal Evaluation (Đánh giá đề xuất Quản lý/HOD).

Workflow:
  1. upload_file()       → Upload tờ trình → create ProposalEvaluation record
  2. extract_data()      → OCR + AI extraction → status: Pending Review
  3. update_extracted()  → Save user corrections
  4. confirm_data()      → Mark data confirmed → status: Confirmed
  5. evaluate()          → AI evaluation → status: Evaluated
  6. generate_report()   → Build PDF → status: Report Generated
  7. download_report()   → Stream PDF to browser
  8. list_evaluations()  → Paginated list
  9. delete_evaluation() → Delete record + files
"""

import json

import frappe
from frappe.handler import upload_file as frappe_upload_file

from cnb_2as.services.de_xuat_service import (
    evaluate_proposals,
    extract_proposal_data,
    get_file_path,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_doc(name: str):
    """Get ProposalEvaluation doc, raise if not found."""
    if not name:
        frappe.throw("Thiếu tên hồ sơ đề xuất")
    try:
        return frappe.get_doc("Proposal Evaluation", name)
    except frappe.DoesNotExistError:
        frappe.throw(f"Hồ sơ đề xuất không tồn tại: {name}")


def _publish(step: int, total: int, message: str, extra: dict = None):
    payload = {"step": step, "total": total, "message": message}
    if extra:
        payload.update(extra)
    frappe.publish_realtime("de_xuat_progress", payload, user=frappe.session.user)


# ── 1. Upload file ─────────────────────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def upload_file():
    """Upload a proposal document and create a ProposalEvaluation record.

    Expects multipart/form-data with the file.

    Returns:
        Dict with evaluation_name, file_url, status.
    """
    if frappe.session.user == "Guest":
        frappe.throw("Vui lòng đăng nhập trước", frappe.AuthenticationError)

    ret = frappe_upload_file()
    file_url = ret.get("file_url", "")
    file_name = ret.get("file_name", "")

    import os
    ext = os.path.splitext(file_name)[1].lower()
    if ext != ".pdf":
        frappe.throw("Chỉ hỗ trợ file PDF scan. Vui lòng upload file .pdf")

    doc = frappe.get_doc({
        "doctype": "Proposal Evaluation",
        "employee_name": "(Chưa trích xuất)",
        "status": "Uploaded",
        "uploaded_by": frappe.session.user,
        "source_file": file_url,
        "source_file_name": file_name,
        "source_file_type": ext,
    })
    doc.insert(ignore_permissions=False)
    frappe.db.commit()

    return {
        "evaluation_name": doc.name,
        "file_url": file_url,
        "file_name": file_name,
        "status": "Uploaded",
        "message": "Upload thành công. Nhấn 'Trích xuất dữ liệu' để bắt đầu OCR.",
    }


# ── 2. Extract data (OCR + AI) ─────────────────────────────────────────────────

@frappe.whitelist()
def extract_data(evaluation_name):
    """Enqueue OCR + AI extraction as a background job and return immediately.

    The frontend polls get_evaluation() to detect completion.
    Use the long queue with a 30-minute timeout to handle large PDFs.
    """
    doc = _get_doc(evaluation_name)

    if doc.status not in ("Uploaded", "Failed", "Pending Review", "Extracting"):
        frappe.throw(f"Không thể trích xuất ở trạng thái: {doc.status}")

    if not doc.source_file:
        frappe.throw("Chưa có file tờ trình. Vui lòng upload trước.")

    doc.status = "Extracting"
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    frappe.enqueue(
        "cnb_2as.api.de_xuat.run_extraction_job",
        evaluation_name=evaluation_name,
        user=frappe.session.user,
        queue="long",
        timeout=1800,
    )

    return {
        "evaluation_name": evaluation_name,
        "status": "Extracting",
        "message": "Đã bắt đầu xử lý OCR. Trang sẽ tự cập nhật khi hoàn tất.",
    }


def run_extraction_job(evaluation_name, user=None):
    """Background worker: OCR all pages in batches, save results to doc."""
    if user:
        frappe.set_user(user)

    doc = frappe.get_doc("Proposal Evaluation", evaluation_name)

    try:
        result = extract_proposal_data(doc.source_file)
        extracted = result["extracted"]

        doc.page_count = result.get("page_count", 1)
        doc.extracted_json = json.dumps(extracted, ensure_ascii=False, indent=2)
        doc.raw_ocr_json = doc.extracted_json
        doc.ocr_warnings = json.dumps(result.get("warnings", []), ensure_ascii=False)
        doc.missing_fields_json = json.dumps(result.get("missing_fields", []), ensure_ascii=False)

        emp = extracted.get("employee", {})
        if emp.get("fullName"):
            doc.employee_name = emp["fullName"]
        if emp.get("department"):
            doc.department = emp["department"]
        if emp.get("currentTitle"):
            doc.current_title = emp["currentTitle"]

        doc.status = "Pending Review"
        doc.save(ignore_permissions=True)
        frappe.db.commit()

        frappe.publish_realtime(
            "de_xuat_progress",
            {
                "step": 3, "total": 3,
                "message": "Trích xuất hoàn tất! Vui lòng kiểm tra dữ liệu.",
                "completed": True,
                "evaluation_name": evaluation_name,
            },
            user=user,
        )

    except Exception as e:
        frappe.log_error(
            title=f"DeXuat Extract Failed: {evaluation_name}",
            message=frappe.get_traceback(),
        )
        doc.status = "Failed"
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        frappe.publish_realtime(
            "de_xuat_progress",
            {
                "step": -1, "total": 3,
                "message": f"Lỗi: {str(e)[:200]}",
                "error": True,
                "evaluation_name": evaluation_name,
            },
            user=user,
        )


# ── 3. Update extracted data (user corrections) ────────────────────────────────

@frappe.whitelist()
def update_extracted(evaluation_name, corrected_json):
    """Save user-corrected extracted data.

    Args:
        evaluation_name: Name of the ProposalEvaluation document.
        corrected_json: JSON string of corrected extracted data.

    Returns:
        Dict with status.
    """
    doc = _get_doc(evaluation_name)

    if doc.status not in ("Pending Review", "Confirmed", "Failed"):
        frappe.throw(f"Không thể chỉnh sửa ở trạng thái: {doc.status}")

    # Validate JSON
    try:
        parsed = json.loads(corrected_json) if isinstance(corrected_json, str) else corrected_json
    except (json.JSONDecodeError, TypeError):
        frappe.throw("Dữ liệu JSON không hợp lệ")

    doc.user_corrected_json = json.dumps(parsed, ensure_ascii=False, indent=2)

    # Update basic employee info from corrected data
    emp = parsed.get("employee", {})
    if emp.get("fullName"):
        doc.employee_name = emp["fullName"]
    if emp.get("department"):
        doc.department = emp["department"]
    if emp.get("currentTitle"):
        doc.current_title = emp["currentTitle"]

    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "evaluation_name": evaluation_name,
        "status": doc.status,
        "message": "Đã lưu dữ liệu chỉnh sửa.",
    }


# ── 4. Confirm data ────────────────────────────────────────────────────────────

@frappe.whitelist()
def confirm_data(evaluation_name):
    """Mark extracted data as confirmed and ready for evaluation.

    Args:
        evaluation_name: Name of the ProposalEvaluation document.

    Returns:
        Dict with status.
    """
    doc = _get_doc(evaluation_name)

    if doc.status not in ("Pending Review", "Failed"):
        frappe.throw(f"Không thể xác nhận ở trạng thái: {doc.status}")

    # Use user-corrected JSON if available, else extracted JSON
    if not doc.user_corrected_json and not doc.extracted_json:
        frappe.throw("Chưa có dữ liệu trích xuất để xác nhận")

    doc.confirmed_by = frappe.session.user
    doc.status = "Confirmed"
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "evaluation_name": evaluation_name,
        "status": "Confirmed",
        "message": "Đã xác nhận dữ liệu. Nhấn 'Đánh giá đề xuất' để tiến hành đánh giá.",
    }


# ── 5. Evaluate ────────────────────────────────────────────────────────────────

@frappe.whitelist()
def evaluate(evaluation_name):
    """Run AI evaluation on confirmed extracted data.

    Args:
        evaluation_name: Name of the ProposalEvaluation document.

    Returns:
        Dict with evaluation results.
    """
    doc = _get_doc(evaluation_name)

    if doc.status not in ("Confirmed", "Failed", "Evaluated", "Evaluating"):
        frappe.throw(f"Không thể đánh giá ở trạng thái: {doc.status}")

    data_json = doc.user_corrected_json or doc.extracted_json
    if not data_json:
        frappe.throw("Chưa có dữ liệu đã xác nhận để đánh giá")

    doc.status = "Evaluating"
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    _publish(1, 3, "Đang đánh giá tính hợp lý của các đề xuất...")

    try:
        extracted = json.loads(data_json)
        eval_result = evaluate_proposals(extracted)

        doc.evaluation_result_json = json.dumps(eval_result, ensure_ascii=False, indent=2)
        doc.overall_score = eval_result.get("overallScore", 0)
        doc.recommendation = eval_result.get("overallRecommendation", "")
        doc.evaluated_at = frappe.utils.now_datetime()
        doc.status = "Evaluated"
        doc.save(ignore_permissions=True)
        frappe.db.commit()

        _publish(3, 3, "Đánh giá hoàn tất!", {
            "completed": True,
            "evaluation_name": evaluation_name,
        })

        return {
            "evaluation_name": evaluation_name,
            "status": "Evaluated",
            "evaluation_result": eval_result,
            "overall_score": doc.overall_score,
            "recommendation": doc.recommendation,
            "message": "Đánh giá hoàn tất. Nhấn 'Sinh báo cáo PDF' để tạo báo cáo.",
        }

    except Exception as e:
        frappe.log_error(
            title=f"DeXuat Evaluate Failed: {evaluation_name}",
            message=frappe.get_traceback(),
        )
        doc.status = "Failed"
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        _publish(-1, 3, f"Lỗi đánh giá: {str(e)[:200]}", {"error": True})
        frappe.throw(f"Lỗi đánh giá: {str(e)[:300]}")


# ── 6. Generate PDF report ─────────────────────────────────────────────────────

@frappe.whitelist()
def generate_report(evaluation_name):
    """Generate PDF report for an evaluated proposal.

    Args:
        evaluation_name: Name of the ProposalEvaluation document.

    Returns:
        PDF file as HTTP response (inline download).
    """
    doc = _get_doc(evaluation_name)

    if doc.status not in ("Evaluated", "Report Generated"):
        frappe.throw("Chỉ có thể sinh báo cáo sau khi đã đánh giá xong")

    if not doc.evaluation_result_json:
        frappe.throw("Không có dữ liệu đánh giá để sinh báo cáo")

    from cnb_2as.services.de_xuat_pdf import generate_proposal_pdf

    data_json = doc.user_corrected_json or doc.extracted_json or "{}"
    extracted = json.loads(data_json)
    eval_result = json.loads(doc.evaluation_result_json)

    report_data = {
        "evaluation_name": doc.name,
        "employee_name": doc.employee_name or "",
        "department": doc.department or "",
        "current_title": doc.current_title or "",
        "status": doc.status,
        "source_file_name": doc.source_file_name or "",
        "uploaded_by": doc.uploaded_by or "",
        "confirmed_by": doc.confirmed_by or "",
        "evaluated_at": doc.evaluated_at.strftime("%d/%m/%Y %H:%M") if doc.evaluated_at else "",
        "overall_score": doc.overall_score or 0,
        "recommendation": doc.recommendation or "",
        "extracted": extracted,
        "evaluation": eval_result,
    }

    pdf_buffer = generate_proposal_pdf(report_data)

    # Update status
    import frappe.utils
    doc.status = "Report Generated"
    doc.report_generated_at = frappe.utils.now_datetime()
    doc.save(ignore_permissions=True)
    frappe.db.commit()

    # Build filename
    safe_name = "".join(
        c for c in (doc.employee_name or "unknown")
        if c.isalnum() or c in (" ", "_", "-")
    ).strip().replace(" ", "_") or "BaoCao"
    filename = f"DanhGiaDXuat_{safe_name}_{doc.name}.pdf"

    frappe.local.response.filename = filename
    frappe.local.response.filecontent = pdf_buffer.getvalue()
    frappe.local.response.type = "pdf"


# ── 7. Get evaluation detail ───────────────────────────────────────────────────

@frappe.whitelist()
def get_evaluation(evaluation_name):
    """Get full evaluation data for display.

    Args:
        evaluation_name: Name of the ProposalEvaluation document.

    Returns:
        Dict with all evaluation data.
    """
    doc = _get_doc(evaluation_name)

    result = {
        "name": doc.name,
        "employee_name": doc.employee_name or "",
        "department": doc.department or "",
        "current_title": doc.current_title or "",
        "status": doc.status,
        "uploaded_by": doc.uploaded_by or "",
        "confirmed_by": doc.confirmed_by or "",
        "source_file": doc.source_file or "",
        "source_file_name": doc.source_file_name or "",
        "source_file_type": doc.source_file_type or "",
        "page_count": doc.page_count or 0,
        "overall_score": doc.overall_score or 0,
        "recommendation": doc.recommendation or "",
        "evaluated_at": doc.evaluated_at.strftime("%d/%m/%Y %H:%M") if doc.evaluated_at else "",
        "report_generated_at": str(doc.report_generated_at) if doc.report_generated_at else "",
        "extracted": None,
        "user_corrected": None,
        "evaluation_result": None,
        "warnings": [],
        "missing_fields": [],
    }

    for field, key in [
        ("extracted_json", "extracted"),
        ("user_corrected_json", "user_corrected"),
        ("evaluation_result_json", "evaluation_result"),
    ]:
        raw = getattr(doc, field, "") or ""
        if raw:
            try:
                result[key] = json.loads(raw)
            except json.JSONDecodeError:
                pass

    for field, key in [
        ("ocr_warnings", "warnings"),
        ("missing_fields_json", "missing_fields"),
    ]:
        raw = getattr(doc, field, "") or ""
        if raw:
            try:
                result[key] = json.loads(raw)
            except json.JSONDecodeError:
                result[key] = []

    return result


# ── 8. List evaluations ────────────────────────────────────────────────────────

@frappe.whitelist()
def list_evaluations(page=1, page_size=20, status_filter=""):
    """List ProposalEvaluation records with pagination.

    Args:
        page: Page number (1-based).
        page_size: Records per page.
        status_filter: Optional status to filter by.

    Returns:
        Dict with items list and total count.
    """
    page = int(page or 1)
    page_size = int(page_size or 20)
    limit_start = (page - 1) * page_size

    filters = {}
    if status_filter:
        filters["status"] = status_filter

    fields = [
        "name", "employee_name", "department", "current_title",
        "status", "overall_score", "recommendation",
        "uploaded_by", "evaluated_at", "creation", "modified",
        "source_file_name",
    ]

    items = frappe.db.get_all(
        "Proposal Evaluation",
        filters=filters,
        fields=fields,
        order_by="modified desc",
        limit_start=limit_start,
        limit_page_length=page_size,
    )

    total = frappe.db.count("Proposal Evaluation", filters=filters)

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


# ── 9. Delete evaluation ───────────────────────────────────────────────────────

@frappe.whitelist(methods=["POST"])
def save_manager_notes(evaluation_name, notes):
    doc = _get_doc(evaluation_name)
    doc.manager_notes = notes
    doc.save(ignore_permissions=False)
    frappe.db.commit()
    return {"status": "ok"}


@frappe.whitelist(methods=["POST"])
def delete_evaluation(evaluation_name):
    """Delete a ProposalEvaluation record.

    Args:
        evaluation_name: Name of the ProposalEvaluation document.

    Returns:
        Dict with status.
    """
    doc = _get_doc(evaluation_name)

    # Check permission (only uploader or System Manager can delete)
    if doc.uploaded_by != frappe.session.user and "System Manager" not in frappe.get_roles():
        frappe.throw("Bạn không có quyền xóa hồ sơ này", frappe.PermissionError)

    frappe.delete_doc("Proposal Evaluation", evaluation_name, ignore_permissions=False)
    frappe.db.commit()

    return {
        "evaluation_name": evaluation_name,
        "status": "deleted",
        "message": "Đã xóa hồ sơ đánh giá đề xuất.",
    }
