# Copyright (c) 2025, antruong and contributors
# For license information, please see license.txt

"""API endpoints for HR Contract Evaluation.

Provides whitelisted methods for the frontend to trigger
evaluation and retrieve results. Employee info (name, job title,
department) is auto-extracted from uploaded files by the AI pipeline.
"""

import json

import frappe
from frappe.handler import upload_file as frappe_upload_file

from cnb_2as.services.agents import run_evaluation_pipeline
from cnb_2as.services.document_parser import (
    check_eval_docx_completeness,
    check_report_xlsx_completeness,
    count_working_days,
    extract_fields_from_markdown,
    get_file_path_from_url,
    parse_daily_report,
    parse_file,
    validate_cross_document_consistency,
    validate_xlsx_kpi_ratio,
    validate_xlsx_product_links,
)
from cnb_2as.services.ocr_service import ocr_pdf_to_json
from cnb_2as.services.pdf_generator import generate_pdf


@frappe.whitelist(methods=["POST"])
def upload_eval_file():
	"""Upload a file for evaluation.

	Custom wrapper around Frappe's upload_file that works
	with the SPA frontend (handles CSRF via session validation).

	Returns:
		Dict with file_url, file_name, and name.
	"""
	# Verify user is logged in
	if frappe.session.user == "Guest":
		frappe.throw("Vui lòng đăng nhập trước", frappe.AuthenticationError)

	ret = frappe_upload_file()
	return ret


@frappe.whitelist()
def run_evaluation(eval_file, work_report_file, daily_report_file="", ngay_bd="", ngay_kt=""):
	"""Start an AI evaluation from uploaded files (default mode).

	Args:
		eval_file: Frappe file URL for the evaluation form (Word).
		work_report_file: Frappe file URL for the work report (Excel).
		daily_report_file: Optional Frappe file URL for daily report.
		ngay_bd: Start date for daily report range (YYYY-MM-DD).
		ngay_kt: End date for daily report range (YYYY-MM-DD).

	Returns:
		Dict with the evaluation document name and status.
	"""
	# Input validation
	if not eval_file:
		frappe.throw("Vui lòng upload file Đánh giá tái ký")
	if not work_report_file:
		frappe.throw("Vui lòng upload file Báo cáo kết quả công việc")

	# Parse daily report content synchronously NOW (before enqueue)
	# This avoids file-access issues in background workers with private files.
	daily_report_content_cached = ""
	if daily_report_file:
		try:
			daily_report_content_cached = parse_daily_report(file_url=daily_report_file) or ""
			frappe.logger("cnb_eval").info(
				f"[run_evaluation] Daily report parsed: {len(daily_report_content_cached)} chars"
			)
		except Exception as _de:
			frappe.logger("cnb_eval").warning(
				f"[run_evaluation] Daily report parse error: {str(_de)[:200]}"
			)

	# Create evaluation record (employee info will be filled by AI)
	eval_doc = frappe.get_doc({
		"doctype": "Employee Evaluation",
		"employee_name": "(Đang trích xuất...)",
		"job_title": "(Đang trích xuất...)",
		"department": "",
		"jd_file": "",
		"eval_file": eval_file,
		"work_report_file": work_report_file,
		"input_mode": "default",
		"status": "Processing",
		# Store parsed daily report content in ocr_report_content (unused in default mode)
		# so the background worker can reliably access it without file-permission issues.
		"ocr_report_content": daily_report_content_cached,
	})
	eval_doc.insert(ignore_permissions=False)
	frappe.db.commit()

	# Get session_id from request
	session_id = ""
	if hasattr(frappe.local, "request") and frappe.local.request:
		session_id = frappe.request.headers.get("X-App-Session-Id") or frappe.request.headers.get("x-app-session-id") or ""

	# Enqueue background job (pass daily report params as kwargs)
	frappe.enqueue(
		"cnb_2as.api.evaluation.process_evaluation",
		queue="long",
		timeout=900,
		evaluation_name=eval_doc.name,
		daily_report_file=daily_report_file or "",
		ngay_bd=ngay_bd or "",
		ngay_kt=ngay_kt or "",
		session_id=session_id,
	)

	return {
		"evaluation_name": eval_doc.name,
		"status": "Processing",
		"message": "Đánh giá đang được xử lý. Vui lòng chờ...",
	}


@frappe.whitelist()
def run_evaluation_scan(eval_file, work_report_file):
	"""OCR scanned PDF files using OpenAI Vision and return results for review.

	Uploads scanned PDFs, calls OpenAI GPT-4o Vision for OCR,
	saves results for user review before running AI pipeline.

	Args:
		eval_file: Frappe file URL for the scanned evaluation PDF.
		work_report_file: Frappe file URL for the scanned work report PDF.

	Returns:
		Dict with evaluation name, OCR content for review, and field warnings.
	"""

	if not eval_file:
		frappe.throw("Vui lòng upload file Đánh giá tái ký (PDF scan)")
	if not work_report_file:
		frappe.throw("Vui lòng upload file Báo cáo kết quả công việc (PDF scan)")

	# Create evaluation record in draft mode
	eval_doc = frappe.get_doc({
		"doctype": "Employee Evaluation",
		"employee_name": "(Đang OCR...)",
		"job_title": "(Đang OCR...)",
		"department": "",
		"jd_file": "",
		"eval_file": eval_file,
		"work_report_file": work_report_file,
		"input_mode": "scan",
		"status": "Processing",
	})
	eval_doc.insert(ignore_permissions=False)
	frappe.db.commit()

	try:
		frappe.publish_realtime(
			"eval_progress",
			{"step": 1, "total": 3, "message": "Đang OCR bằng OpenAI Vision..."},
			user=frappe.session.user,
		)

		# Resolve file paths
		eval_file_path = get_file_path_from_url(eval_file)
		report_file_path = get_file_path_from_url(work_report_file)


		# OCR both files (OpenAI Vision is fast, ~10-30s each)
		ocr_eval = ocr_pdf_to_json(eval_file_path, doc_type="eval")

		frappe.publish_realtime(
			"eval_progress",
			{"step": 2, "total": 3, "message": "OCR file 1 xong, đang xử lý file 2..."},
			user=frappe.session.user,
		)

		ocr_report = ocr_pdf_to_json(report_file_path, doc_type="report")

		frappe.publish_realtime(
			"eval_progress",
			{"step": 2, "total": 3, "message": "OCR hoàn tất, đang phân tích trường..."},
			user=frappe.session.user,
		)

		# Extract fields and check completeness
		eval_fields = extract_fields_from_markdown(ocr_eval, doc_type="eval")
		report_fields = extract_fields_from_markdown(ocr_report, doc_type="report")

		# Combine warnings
		all_warnings = eval_fields.get("warnings", []) + report_fields.get("warnings", [])

		# Save OCR results
		eval_doc.ocr_eval_content = ocr_eval
		eval_doc.ocr_report_content = ocr_report
		eval_doc.ocr_confirmed = 0
		eval_doc.status = "OCR Ready"

		# Update employee name from extracted fields if available
		extracted = eval_fields.get("fields", {})
		if extracted.get("Họ và tên"):
			eval_doc.employee_name = extracted["Họ và tên"]
		if extracted.get("Vị trí công việc"):
			eval_doc.job_title = extracted["Vị trí công việc"]
		if extracted.get("Phòng ban"):
			eval_doc.department = extracted["Phòng ban"]

		eval_doc.save(ignore_permissions=True)
		frappe.db.commit()

		frappe.publish_realtime(
			"eval_progress",
			{"step": 3, "total": 3, "message": "OCR hoàn tất! Vui lòng kiểm tra nội dung."},
			user=frappe.session.user,
		)

		return {
			"evaluation_name": eval_doc.name,
			"status": "OCR Ready",
			"ocr_eval_content": ocr_eval,
			"ocr_report_content": ocr_report,
			"eval_fields": eval_fields,
			"report_fields": report_fields,
			"all_warnings": all_warnings,
			"message": "OCR hoàn tất. Vui lòng kiểm tra và chỉnh sửa nội dung.",
		}

	except Exception as e:
		frappe.log_error(
			title=f"OCR Failed: {eval_doc.name}",
			message=frappe.get_traceback(),
		)
		eval_doc.status = "Failed"
		eval_doc.save(ignore_permissions=True)
		frappe.db.commit()

		frappe.publish_realtime(
			"eval_progress",
			{
				"step": -1, "total": 3,
				"message": f"Lỗi OCR: {str(e)[:200]}",
				"error": True,
			},
			user=frappe.session.user,
		)
		frappe.throw(f"Lỗi OCR: {str(e)[:200]}")


@frappe.whitelist()
def confirm_ocr_and_evaluate(evaluation_name, ocr_eval_content, ocr_report_content,
							  daily_report_file="", ngay_bd="", ngay_kt=""):
	"""Confirm edited OCR content and start AI evaluation pipeline.

	Called after user reviews and edits OCR output. Saves the confirmed
	content and enqueues the AI evaluation.

	Args:
		evaluation_name: Name of the Employee Evaluation document.
		ocr_eval_content: Confirmed/edited Markdown of evaluation form.
		ocr_report_content: Confirmed/edited Markdown of work report.
		daily_report_file: Optional Frappe file URL for daily report.
		ngay_bd: Start date for daily report range (YYYY-MM-DD).
		ngay_kt: End date for daily report range (YYYY-MM-DD).

	Returns:
		Dict with status information.
	"""
	if not evaluation_name:
		frappe.throw("Evaluation name không được để trống")
	if not ocr_eval_content:
		frappe.throw("Nội dung phiếu đánh giá không được để trống")
	if not ocr_report_content:
		frappe.throw("Nội dung báo cáo công việc không được để trống")

	eval_doc = frappe.get_doc("Employee Evaluation", evaluation_name)

	if eval_doc.status not in ("OCR Ready", "Failed"):
		frappe.throw("Trạng thái đánh giá không hợp lệ để xác nhận OCR")

	# Save confirmed OCR content
	eval_doc.ocr_eval_content = ocr_eval_content
	eval_doc.ocr_report_content = ocr_report_content
	eval_doc.ocr_confirmed = 1
	eval_doc.status = "Processing"
	eval_doc.save(ignore_permissions=True)
	frappe.db.commit()

	# Get session_id from request
	session_id = ""
	if hasattr(frappe.local, "request") and frappe.local.request:
		session_id = frappe.request.headers.get("X-App-Session-Id") or frappe.request.headers.get("x-app-session-id") or ""

	# Enqueue AI evaluation with OCR content + daily report info
	frappe.enqueue(
		"cnb_2as.api.evaluation.process_evaluation_from_ocr",
		queue="long",
		timeout=900,
		evaluation_name=evaluation_name,
		daily_report_file=daily_report_file or "",
		ngay_bd=ngay_bd or "",
		ngay_kt=ngay_kt or "",
		session_id=session_id,
	)

	return {
		"evaluation_name": evaluation_name,
		"status": "Processing",
		"message": "Đánh giá AI đang được xử lý. Vui lòng chờ...",
	}


@frappe.whitelist()
def get_ocr_preview(evaluation_name):
	"""Retrieve OCR content for review.

	Returns the stored OCR Markdown content and field warnings
	for an evaluation that is in 'OCR Ready' status.

	Args:
		evaluation_name: Name of the Employee Evaluation document.

	Returns:
		Dict with OCR content and field analysis.
	"""
	if not evaluation_name:
		frappe.throw("Evaluation name không được để trống")

	eval_doc = frappe.get_doc("Employee Evaluation", evaluation_name)


	eval_fields = extract_fields_from_markdown(
		eval_doc.ocr_eval_content or "", doc_type="eval"
	)
	report_fields = extract_fields_from_markdown(
		eval_doc.ocr_report_content or "", doc_type="report"
	)

	return {
		"evaluation_name": eval_doc.name,
		"status": eval_doc.status,
		"ocr_eval_content": eval_doc.ocr_eval_content or "",
		"ocr_report_content": eval_doc.ocr_report_content or "",
		"eval_fields": eval_fields,
		"report_fields": report_fields,
		"ocr_confirmed": eval_doc.ocr_confirmed,
	}


def process_evaluation_from_ocr(evaluation_name, daily_report_file="", ngay_bd="", ngay_kt="", session_id=""):
	"""Background job: Run AI evaluation from confirmed OCR content.

	Similar to process_evaluation but uses OCR Markdown content
	instead of parsing files directly.

	Args:
		evaluation_name: Name of the Employee Evaluation document.
		daily_report_file: Optional Frappe file URL for daily report.
		ngay_bd: Start date string for daily report range (YYYY-MM-DD).
		ngay_kt: End date string for daily report range (YYYY-MM-DD).
		session_id: The session string from the request headers to keep logs grouped.
	"""
	if session_id:
		frappe.local.session_id = session_id

	try:
		eval_doc = frappe.get_doc("Employee Evaluation", evaluation_name)

		frappe.publish_realtime(
			"eval_progress",
			{"step": 1, "total": 6, "message": "Đang phân tích nội dung OCR..."},
			user=frappe.session.user,
		)

		eval_content = eval_doc.ocr_eval_content or ""
		work_report_content = eval_doc.ocr_report_content or ""

		if not eval_content.strip():
			frappe.throw("Nội dung OCR phiếu đánh giá rỗng")
		if not work_report_content.strip():
			frappe.throw("Nội dung OCR báo cáo công việc rỗng")

		# Run direct file completeness checks (if original files exist)
		doc_warnings = []
		if eval_doc.eval_file:
			try:
				doc_warnings += check_eval_docx_completeness(eval_doc.eval_file)
			except Exception:
				pass
		if eval_doc.work_report_file:
			try:
				doc_warnings += check_report_xlsx_completeness(eval_doc.work_report_file)
			except Exception:
				pass

		# Parse daily report if provided (via OCR flow)
		daily_report_content = ""
		so_ngay_can_bc = ""
		if daily_report_file:
			frappe.publish_realtime(
				"eval_progress",
				{"step": 2, "total": 6, "message": "Đang đọc báo cáo ngày..."},
				user=frappe.session.user,
			)
			try:
				daily_report_content = parse_daily_report(file_url=daily_report_file) or ""
				frappe.logger("cnb_eval").info(
					f"[process_evaluation_from_ocr] Daily report parsed: {len(daily_report_content)} chars"
				)
			except Exception as _e:
				frappe.logger("cnb_eval").warning(
					f"[process_evaluation_from_ocr] Daily report parse failed: {_e}"
				)
		if ngay_bd and ngay_kt:
			so_ngay_can_bc = str(count_working_days(ngay_bd, ngay_kt))

		# Run AI pipeline
		result = run_evaluation_pipeline(
			eval_content=eval_content,
			work_report_content=work_report_content,
			daily_report_content=daily_report_content,
			ngay_bd=ngay_bd or "",
			ngay_kt=ngay_kt or "",
			so_ngay_can_bc=so_ngay_can_bc,
		)

		# Merge code-based + AI-based warnings
		ai_warnings = result.get("document_completeness", [])
		code_warning_set = set(w.lower() for w in doc_warnings)
		for aw in ai_warnings:
			aw_lower = str(aw).lower()
			is_duplicate = any(cw in aw_lower or aw_lower in cw for cw in code_warning_set)
			if not is_duplicate:
				doc_warnings.append(str(aw))

		result["doc_completeness_warnings"] = doc_warnings
		result["doc_is_complete"] = len(doc_warnings) == 0
		_save_evaluation_results(eval_doc, result)

		frappe.publish_realtime(
			"eval_progress",
			{
				"step": 6, "total": 6,
				"message": "Hoàn thành!",
				"completed": True,
				"evaluation_name": evaluation_name,
			},
			user=frappe.session.user,
		)

	except Exception as e:
		frappe.log_error(
			title=f"Evaluation Failed (OCR): {evaluation_name}",
			message=frappe.get_traceback(),
		)
		eval_doc = frappe.get_doc("Employee Evaluation", evaluation_name)
		eval_doc.status = "Failed"
		eval_doc.save(ignore_permissions=True)
		frappe.db.commit()

		frappe.publish_realtime(
			"eval_progress",
			{
				"step": -1, "total": 6,
				"message": f"Lỗi: {str(e)[:200]}",
				"error": True,
				"evaluation_name": evaluation_name,
			},
			user=frappe.session.user,
		)


def process_evaluation(evaluation_name, daily_report_file="", ngay_bd="", ngay_kt="", session_id=""):
	"""Background job: Run the AI evaluation pipeline.

	Args:
		evaluation_name: Name of the Employee Evaluation document.
		daily_report_file: Optional URL of daily report file.
		ngay_bd: Start date string for daily report range.
		ngay_kt: End date string for daily report range.
		session_id: The session string from the request headers to keep logs grouped.
	"""
	if session_id:
		frappe.local.session_id = session_id
	try:
		eval_doc = frappe.get_doc("Employee Evaluation", evaluation_name)

		# Step 0: Validate input data
		frappe.publish_realtime(
			"eval_progress",
			{"step": 0, "total": 6, "message": "Đang kiểm tra dữ liệu đầu vào..."},
			user=frappe.session.user,
		)

		# Run validation checks
		all_warnings = []

		link_warnings = validate_xlsx_product_links(eval_doc.work_report_file)
		all_warnings.extend(link_warnings)

		kpi_warnings = validate_xlsx_kpi_ratio(eval_doc.work_report_file)
		all_warnings.extend(kpi_warnings)

		consistency_result = validate_cross_document_consistency(
			eval_doc.eval_file, eval_doc.work_report_file
		)

		# Save validation results early
		eval_doc.validation_warnings = json.dumps(
			all_warnings, ensure_ascii=False, indent=2
		) if all_warnings else ""
		eval_doc.consistency_check = json.dumps(
			consistency_result, ensure_ascii=False, indent=2
		)
		eval_doc.save(ignore_permissions=True)
		frappe.db.commit()

		# Send validation warnings via realtime
		if all_warnings or not consistency_result.get("is_consistent", True):
			frappe.publish_realtime(
				"eval_progress",
				{
					"step": 0,
					"total": 6,
					"message": (
						f"Phát hiện {len(all_warnings)} cảnh báo dữ liệu. "
						f"Đang tiếp tục đánh giá..."
					),
					"validation_warnings": all_warnings,
					"consistency_check": consistency_result,
				},
				user=frappe.session.user,
			)

		# Step 1: Parse files
		frappe.publish_realtime(
			"eval_progress",
			{"step": 1, "total": 6, "message": "Đang đọc tài liệu..."},
			user=frappe.session.user,
		)

		eval_content = parse_file(eval_doc.eval_file)
		work_report_content = parse_file(eval_doc.work_report_file)

		# Parse daily report (optional) — uses shared utility (Vision fallback included)
		# PRIMARY: use pre-parsed content cached in ocr_report_content by run_evaluation()
		# This avoids private-file permission issues when running as background worker.
		daily_report_content = ""
		so_ngay_can_bc = ""
		if daily_report_file:
			# Use cached content stored by run_evaluation() before enqueue (primary path)
			cached = (eval_doc.ocr_report_content or "").strip()
			if cached:
				daily_report_content = cached
				frappe.logger("cnb_eval").info(
					f"[process_evaluation] Using cached daily report content: {len(daily_report_content)} chars"
				)
			else:
				# Fallback: re-parse from file URL (e.g., when called directly without run_evaluation)
				try:
					daily_report_content = parse_daily_report(file_url=daily_report_file) or ""
					frappe.logger("cnb_eval").info(
						f"[process_evaluation] Re-parsed daily report from URL: {len(daily_report_content)} chars"
					)
				except Exception as _dpe:
					frappe.logger("cnb_eval").warning(
						f"[process_evaluation] Daily report parse failed: {str(_dpe)[:200]}"
					)
		so_ngay_can_bc = str(count_working_days(ngay_bd, ngay_kt)) if ngay_bd and ngay_kt else ""

		# Run document completeness check directly from file structure
		doc_warnings = []
		try:
			doc_warnings += check_eval_docx_completeness(eval_doc.eval_file)
		except Exception:
			pass
		try:
			doc_warnings += check_report_xlsx_completeness(eval_doc.work_report_file)
		except Exception:
			pass

		# Run AI pipeline (truyền đầy đủ daily report params)
		result = run_evaluation_pipeline(
			eval_content=eval_content,
			work_report_content=work_report_content,
			daily_report_content=daily_report_content,
			ngay_bd=ngay_bd or "",
			ngay_kt=ngay_kt or "",
			so_ngay_can_bc=so_ngay_can_bc,
		)

		# Merge: code-based warnings (accurate) + AI-based warnings (smart)
		ai_warnings = result.get("document_completeness", [])
		# Deduplicate: only add AI warnings that don't overlap with code warnings
		code_warning_set = set(w.lower() for w in doc_warnings)
		for aw in ai_warnings:
			aw_lower = str(aw).lower()
			is_duplicate = any(cw in aw_lower or aw_lower in cw for cw in code_warning_set)
			if not is_duplicate:
				doc_warnings.append(str(aw))

		result["doc_completeness_warnings"] = doc_warnings
		result["doc_is_complete"] = len(doc_warnings) == 0

		# Save results
		_save_evaluation_results(eval_doc, result)

		frappe.publish_realtime(
			"eval_progress",
			{
				"step": 6,
				"total": 6,
				"message": "Hoàn thành!",
				"completed": True,
				"evaluation_name": evaluation_name,
			},
			user=frappe.session.user,
		)

	except Exception as e:
		frappe.log_error(
			title=f"Evaluation Failed: {evaluation_name}",
			message=frappe.get_traceback(),
		)
		eval_doc = frappe.get_doc("Employee Evaluation", evaluation_name)
		eval_doc.status = "Failed"
		eval_doc.save(ignore_permissions=True)
		frappe.db.commit()

		frappe.publish_realtime(
			"eval_progress",
			{
				"step": -1,
				"total": 6,
				"message": f"Lỗi: {str(e)[:200]}",
				"error": True,
				"evaluation_name": evaluation_name,
			},
			user=frappe.session.user,
		)


def _save_evaluation_results(eval_doc, result):
	"""Save AI pipeline results to the Employee Evaluation document.

	Args:
		eval_doc: Employee Evaluation document object.
		result: Dict with all pipeline results.
	"""
	scores_data = result.get("scores", {})
	recommendation_data = result.get("recommendation", {})
	role_analysis = result.get("role_analysis", {})

	# Update employee info from AI extraction
	extracted_info = result.get("extracted_info", {})
	eval_doc.employee_name = extracted_info.get("employee_name", "Không rõ")
	eval_doc.job_title = extracted_info.get("job_title", "Không rõ")
	eval_doc.department = extracted_info.get("department", "")

	# Set overall scores
	eval_doc.overall_score = scores_data.get("overall_score", 0)
	eval_doc.confidence_score = scores_data.get("overall_confidence", 0)
	eval_doc.recommendation = recommendation_data.get("recommendation", "")
	eval_doc.recommendation_reasoning = recommendation_data.get("reasoning", "")

	# Save new fields: proposal level, urgency, next steps
	eval_doc.proposal_level = recommendation_data.get("proposal_level", "")
	eval_doc.urgency_level = recommendation_data.get("urgency_level", "")

	next_steps = recommendation_data.get("next_steps", [])
	eval_doc.next_steps = json.dumps(
		next_steps, ensure_ascii=False, indent=2
	) if next_steps else ""

	# Save document completeness warnings
	doc_warnings = result.get("doc_completeness_warnings", [])
	doc_is_complete = result.get("doc_is_complete", True)

	doc_warning_data = {
		"warnings": doc_warnings,
		"is_complete": doc_is_complete,
	}
	eval_doc.document_warnings = json.dumps(
		doc_warning_data, ensure_ascii=False, indent=2
	)

	# Save role analysis as JSON
	eval_doc.role_analysis = json.dumps(
		role_analysis, ensure_ascii=False, indent=2
	)

	# Save raw AI response
	eval_doc.raw_ai_response = json.dumps(result, ensure_ascii=False, indent=2)

	# Clear existing child tables
	eval_doc.competency_scores = []
	eval_doc.evaluation_evidences = []

	# Add competency scores
	framework = result.get("evaluation_framework", [])
	score_details = scores_data.get("scores", [])

	# Create a lookup for scores by competency name (normalized for fuzzy matching)
	import unicodedata as _ud
	def _norm_comp(s):
		"""Normalize competency name for matching: lowercase, strip, remove accents."""
		s = str(s).strip().lower()
		# Remove Vietnamese diacritics for comparison
		nfkd = _ud.normalize('NFKD', s)
		return ''.join(c for c in nfkd if not _ud.combining(c)).replace('/', ' ').replace('-', ' ').replace('  ', ' ').strip()

	score_lookup = {}
	score_lookup_norm = {}
	for s in score_details:
		name = s.get("competency_name", "")
		score_lookup[name] = s
		score_lookup_norm[_norm_comp(name)] = s

	def _find_score(comp_name):
		"""Find score for a competency, trying exact match then normalized match then substring."""
		# 1. Exact match
		if comp_name in score_lookup:
			return score_lookup[comp_name]
		# 2. Normalized match
		norm = _norm_comp(comp_name)
		if norm in score_lookup_norm:
			return score_lookup_norm[norm]
		# 3. Substring/partial match (e.g. "Kết quả công việc" in "Năng lực: Kết quả công việc")
		for sn, sv in score_lookup_norm.items():
			if norm in sn or sn in norm:
				return sv
		return {}

	for comp in framework:
		comp_name = comp.get("competency_name", "")
		score_info = _find_score(comp_name)

		eval_doc.append("competency_scores", {
			"competency_name": comp_name,
			"description": comp.get("description", ""),
			"weight": comp.get("weight", 0),
			"score": score_info.get("score", 0),
			"confidence": score_info.get("confidence", 0),
			"measurable_indicators": "\n".join(comp.get("measurable_indicators", [])),
			"evidence_summary": score_info.get("evidence_summary", ""),
		})

	# Add evidence
	evidence_list = result.get("evidence", [])
	for ev in evidence_list:
		eval_doc.append("evaluation_evidences", {
			"statement": ev.get("statement", ""),
			"mapped_competency": ev.get("mapped_competency", ""),
			"source_document": ev.get("source_document", ""),
			"relevance_score": ev.get("relevance_score", 0),
		})

	eval_doc.status = "Completed"
	eval_doc.save(ignore_permissions=True)
	frappe.db.commit()


@frappe.whitelist()
def get_evaluation_result(evaluation_name):
	"""Get the full evaluation result for display.

	Args:
		evaluation_name: Name of the Employee Evaluation document.

	Returns:
		Dict with all evaluation data for the frontend.
	"""
	if not evaluation_name:
		frappe.throw("Evaluation name không được để trống")

	eval_doc = frappe.get_doc("Employee Evaluation", evaluation_name)

	# Build response
	result = {
		"name": eval_doc.name,
		"employee_name": eval_doc.employee_name,
		"job_title": eval_doc.job_title,
		"department": eval_doc.department,
		"evaluation_date": str(eval_doc.evaluation_date) if eval_doc.evaluation_date else "",
		"status": eval_doc.status,
		"input_mode": eval_doc.input_mode or "default",
		"overall_score": eval_doc.overall_score,
		"confidence_score": eval_doc.confidence_score,
		"recommendation": eval_doc.recommendation,
		"recommendation_reasoning": eval_doc.recommendation_reasoning,
		"proposal_level": eval_doc.proposal_level or "",
		"urgency_level": eval_doc.urgency_level or "",
		"competency_scores": [],
		"evidence": [],
		"role_analysis": None,
		"recommendation_details": None,
		"validation_warnings": None,
		"consistency_check": None,
		"document_warnings": None,
		"next_steps": None,
	}

	# Competency scores
	for cs in eval_doc.competency_scores:
		result["competency_scores"].append({
			"competency_name": cs.competency_name,
			"description": cs.description,
			"weight": cs.weight,
			"score": cs.score,
			"confidence": cs.confidence,
			"measurable_indicators": cs.measurable_indicators,
			"evidence_summary": cs.evidence_summary,
		})

	# Evidence
	for ev in eval_doc.evaluation_evidences:
		result["evidence"].append({
			"statement": ev.statement,
			"mapped_competency": ev.mapped_competency,
			"source_document": ev.source_document,
			"relevance_score": ev.relevance_score,
		})

	# Parse JSON fields
	if eval_doc.role_analysis:
		try:
			result["role_analysis"] = json.loads(eval_doc.role_analysis)
		except json.JSONDecodeError:
			result["role_analysis"] = None

	# Validation data
	if eval_doc.validation_warnings:
		try:
			result["validation_warnings"] = json.loads(eval_doc.validation_warnings)
		except json.JSONDecodeError:
			result["validation_warnings"] = None

	if eval_doc.consistency_check:
		try:
			result["consistency_check"] = json.loads(eval_doc.consistency_check)
		except json.JSONDecodeError:
			result["consistency_check"] = None

	# Document warnings
	if eval_doc.document_warnings:
		try:
			result["document_warnings"] = json.loads(eval_doc.document_warnings)
		except json.JSONDecodeError:
			result["document_warnings"] = None

	# Next steps
	if eval_doc.next_steps:
		try:
			result["next_steps"] = json.loads(eval_doc.next_steps)
		except json.JSONDecodeError:
			result["next_steps"] = None

	if eval_doc.raw_ai_response:
		try:
			raw = json.loads(eval_doc.raw_ai_response)
			result["recommendation_details"] = raw.get("recommendation", None)
			_ext_info = raw.get("extracted_info", {})
			result["extracted_info"] = _ext_info
			# Map contract dates to top-level for frontend PDF export
			result["contract_start_date"] = (
				_ext_info.get("contract_start_date") or
				_ext_info.get("start_date") or
				_ext_info.get("ngay_bat_dau_hd") or
				_ext_info.get("ngay_bat_dau") or ""
			)
			result["contract_end_date"] = (
				_ext_info.get("contract_end_date") or
				_ext_info.get("end_date") or
				_ext_info.get("ngay_het_han_hd") or
				_ext_info.get("ngay_het_han") or ""
			)
			result["bao_cao_ngay"] = raw.get("bao_cao_ngay", None)
			result["danh_gia_quan_ly"] = raw.get("danh_gia_quan_ly", None)
			result["danh_gia_hop_dong"] = raw.get("danh_gia_hop_dong", None)
			result["danh_gia_de_xuat_nhan_su"] = raw.get("danh_gia_de_xuat_nhan_su", None)
			result["jd_goi_y"] = raw.get("jd_goi_y", None)
		except json.JSONDecodeError:
			pass

	return result


@frappe.whitelist()
def check_evaluation_status(evaluation_name):
	"""Check the current status of an evaluation.

	Args:
		evaluation_name: Name of the Employee Evaluation document.

	Returns:
		Dict with status information.
	"""
	if not evaluation_name:
		frappe.throw("Evaluation name không được để trống")

	status = frappe.db.get_value(
		"Employee Evaluation", evaluation_name, "status"
	)

	return {"evaluation_name": evaluation_name, "status": status}


@frappe.whitelist()
def export_evaluation_pdf(evaluation_name):
	"""Generate and return a PDF report for a completed evaluation.

	Args:
		evaluation_name: Name of the Employee Evaluation document.

	Returns:
		PDF file as HTTP response.
	"""
	if not evaluation_name:
		frappe.throw("Evaluation name không được để trống")

	# Get full evaluation data using existing function
	eval_data = get_evaluation_result(evaluation_name)

	if eval_data.get("status") != "Completed":
		frappe.throw("Chỉ có thể xuất PDF khi đánh giá đã hoàn thành")


	pdf_buffer = generate_pdf(eval_data)

	# Build safe filename
	employee_name = eval_data.get("employee_name", "unknown")
	# Remove characters unsafe for filenames
	safe_name = "".join(
		c for c in employee_name
		if c.isalnum() or c in (" ", "_", "-")
	).strip().replace(" ", "_")
	if not safe_name:
		safe_name = "evaluation"
	filename = f"DanhGia_{safe_name}_{evaluation_name}.pdf"

	frappe.local.response.filename = filename
	frappe.local.response.filecontent = pdf_buffer.getvalue()
	frappe.local.response.type = "pdf"

