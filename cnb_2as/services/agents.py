# Copyright (c) 2025, antruong and contributors
# For license information, please see license.txt

"""AI Agents for HR Contract Evaluation Pipeline.

Implements a 5-agent chain for deep, neutral, evidence-based employee evaluation:
1. Role Analyzer - Extracts employee info, analyzes role expectations
2. Competency Generator - Generates tailored evaluation framework
3. Evidence Extractor - Deep analysis of self-evaluation vs actual performance
4. Scoring Agent - Neutral scoring with gap analysis
5. Recommendation Agent - Comprehensive strengths/weaknesses with actionable insights

All agents output structured JSON in Vietnamese.
"""

import json

import frappe
from cnb_2as.services.prompts import (
    ROLE_ANALYZER_SYSTEM,
    COMPETENCY_GENERATOR_SYSTEM,
    EVIDENCE_EXTRACTOR_SYSTEM,
    SCORING_AGENT_SYSTEM,
    RECOMMENDATION_AGENT_SYSTEM,
    _DAILY_REPORT_SYSTEM,
    _MANAGER_PROPOSAL_SYSTEM,
)


from cnb_2as.services.openai_client import chat_completion_json


# ============================================================
# AGENT 1: Role Analyzer (also extracts employee info)
# ============================================================


def agent_role_analyzer(eval_content, work_report_content):
	"""Agent 1: Extract employee info and analyze role from documents.

	Args:
		eval_content: Text content from the evaluation form (Word).
		work_report_content: Text from work report (Excel).

	Returns:
		Dict with extracted_info and role_analysis data.
	"""
	user_prompt = f"""Đọc kỹ các tài liệu sau và:
1. TRÍCH XUẤT chính xác thông tin nhân viên (tên, chức danh, phòng ban, mã NV, ngày HĐ...)
2. PHÂN TÍCH SÂU vai trò: xác định KỲ VỌNG cho vị trí này (responsibilities, skills, output level)
3. KIỂM TRA TÍNH ĐẦY ĐỦ: Liệt kê các ô, mục bị bỏ trống (chưa điền nội dung, chưa ký)

LƯU Ý:
- Kỳ vọng phải phù hợp cấp bậc (Junior vs Senior rất khác nhau)
- Ghi rõ jd_source = "Tự sinh từ chức vụ"
- Chú ý đọc kỹ để tránh báo cáo nhầm các mục đã được điền.

FILE ĐÁNH GIÁ TÁI KÝ:
---
{eval_content[:5000]}
---

FILE BÁO CÁO KẾT QUẢ CÔNG VIỆC:
---
{work_report_content[:3000]}
---

Trả về JSON theo schema đã cho."""

	return chat_completion_json(ROLE_ANALYZER_SYSTEM, user_prompt)


# ============================================================
# AGENT 2: Competency Generator
# ============================================================


def agent_competency_generator(role_analysis):
	"""Agent 2: Generate competency framework based on role analysis.

	Args:
		role_analysis: Dict from Agent 1 output.

	Returns:
		Dict with evaluation_framework data.
	"""
	user_prompt = f"""Dựa trên phân tích vai trò sau, sinh khung năng lực đánh giá PHÙ HỢP với cấp bậc và vai trò.

LƯU Ý:
- Measurable indicators phải CỤ THỂ, ĐỊNH LƯỢNG nếu có thể
- Weight phân bổ hợp lý: năng lực kỹ thuật > năng lực mềm (đối với vai trò kỹ thuật)
- Tổng weight PHẢI bằng 100

{json.dumps(role_analysis, ensure_ascii=False, indent=2)}

Trả về JSON theo schema đã cho."""

	return chat_completion_json(COMPETENCY_GENERATOR_SYSTEM, user_prompt)


# ============================================================
# AGENT 3: Evidence Extractor (Deep Analysis)
# ============================================================


def agent_evidence_extractor(eval_content, work_report_content, evaluation_framework):
	"""Agent 3: Extract evidence from documents mapped to competencies.

	Args:
		eval_content: Text from evaluation form.
		work_report_content: Text from work report file.
		evaluation_framework: List from Agent 2 output.

	Returns:
		Dict with evidence data.
	"""
	competencies = [c["competency_name"] for c in evaluation_framework]

	user_prompt = f"""PHÂN TÍCH SÂU các tài liệu sau. Trích xuất TẤT CẢ bằng chứng và map vào từng năng lực.

YÊU CẦU ĐẶC BIỆT:
- Tìm cả bằng chứng TÍCH CỰC lẫn TIÊU CỰC
- So sánh TỰ ĐÁNH GIÁ (mức % nhân viên tự cho) vs THỰC TẾ (số liệu/kết quả cụ thể)
- Ghi nhận năng lực nào THIẾU bằng chứng
- Trích dẫn CON SỐ CỤ THỂ (số lượng sản phẩm, % hoàn thành, số giờ, v.v.)

DANH SÁCH NĂNG LỰC CẦN MAP:
{json.dumps(competencies, ensure_ascii=False)}

NỘI DUNG FILE ĐÁNH GIÁ TÁI KÝ:
---
{eval_content[:6000]}
---

NỘI DUNG BÁO CÁO KẾT QUẢ CÔNG VIỆC:
---
{work_report_content[:8000]}
---

Trích xuất TẤT CẢ bằng chứng tìm thấy. Đặc biệt chú ý phân tích GAP giữa tự đánh giá và thực tế.
Trả về JSON theo schema đã cho."""

	return chat_completion_json(EVIDENCE_EXTRACTOR_SYSTEM, user_prompt)


# ============================================================
# AGENT 4: Scoring Agent (Neutral & Analytical)
# ============================================================


def agent_scoring(evaluation_framework, evidence):
	"""Agent 4: Score each competency based on evidence.

	Args:
		evaluation_framework: List from Agent 2.
		evidence: List from Agent 3.

	Returns:
		Dict with scores data.
	"""
	user_prompt = f"""Với vai trò đánh giá viên TRUNG LẬP, chấm điểm từng năng lực.

YÊU CẦU QUAN TRỌNG:
- Chấm điểm TRUNG THỰC dựa trên bằng chứng thực tế
- Mỗi năng lực phải có PHÂN TÍCH: điểm mạnh + điểm yếu + kết luận
- KHÔNG inflate điểm: "hoàn thành đúng yêu cầu" = 6-7 điểm, KHÔNG PHẢI 8-9
- Điểm 8+ chỉ khi có bằng chứng VƯỢT TRỘI rõ ràng
- PHÁT HIỆN mâu thuẫn giữa tự đánh giá và bằng chứng

KHUNG NĂNG LỰC:
{json.dumps(evaluation_framework, ensure_ascii=False, indent=2)}

BẰNG CHỨNG ĐÃ TRÍCH XUẤT:
{json.dumps(evidence, ensure_ascii=False, indent=2)}

Chấm điểm TRUNG LẬP dựa trên bằng chứng thực tế. Trả về JSON theo schema đã cho."""

	return chat_completion_json(SCORING_AGENT_SYSTEM, user_prompt)


# ============================================================
# AGENT 5: Recommendation Agent (Deep Analysis)
# ============================================================


def agent_recommendation(scores_data, role_analysis):
	"""Agent 5: Generate final recommendation based on scores.

	Args:
		scores_data: Dict from Agent 4.
		role_analysis: Dict from Agent 1 for context.

	Returns:
		Dict with recommendation data.
	"""
	user_prompt = f"""Với vai trò Senior HR Consultant, phân tích SÂU và đưa ra khuyến nghị tái ký hợp đồng.

YÊU CẦU PHÂN TÍCH:
1. Tổng hợp TOÀN DIỆN hiệu suất: không chỉ điểm số mà cả bối cảnh, xu hướng
2. Điểm mạnh phải CỤ THỂ: ghi rõ con số, sản phẩm, thành tựu thực tế
3. Điểm cần cải thiện phải CONSTRUCTIVE: kèm gợi ý hành động cụ thể
4. Đánh giá TIỀM NĂNG PHÁT TRIỂN: nhân viên này có thể đóng góp thêm gì?
5. TRUNG LẬP: không quá khắc nghiệt, cũng không quá dễ dãi

QUY TẮC NGÔN NGỮ (BẮT BUỘC):
- Viết 100% bằng tiếng Việt tự nhiên, dễ hiểu cho quản lý nhân sự
- TUYỆT ĐỐI KHÔNG dùng thuật ngữ kỹ thuật tiếng Anh như: overall_score, risk_flag, confidence, score, pipeline, framework...
- KHÔNG nhắc đến điểm số dạng "điểm tổng thể là X.XX" — thay vào đó hãy MÔ TẢ bằng ngôn ngữ tự nhiên (VD: "đạt kết quả tốt", "vượt kỳ vọng", "cần cải thiện")
- KHÔNG dùng từ "flag" hay "risk flag" — thay bằng "rủi ro cần lưu ý" hoặc "điểm cần chú ý"
- Nếu không có rủi ro, để mảng risk_flags rỗng [], KHÔNG viết "không có risk flag"
- Viết như một báo cáo nhân sự chuyên nghiệp mà giám đốc có thể đọc hiểu ngay

PHÂN TÍCH VAI TRÒ:
{json.dumps(role_analysis, ensure_ascii=False, indent=2)}

KẾT QUẢ CHẤM ĐIỂM:
{json.dumps(scores_data, ensure_ascii=False, indent=2)}

Trả về JSON theo schema đã cho. Reasoning tối thiểu 5 câu, phân tích sâu, viết tự nhiên như báo cáo nhân sự."""

	return chat_completion_json(RECOMMENDATION_AGENT_SYSTEM, user_prompt)



# ============================================================
# SUB-AGENT: Daily Report Analyzer
# ============================================================


def _analyze_daily_report(daily_report_content, eval_content, ngay_bd, ngay_kt, so_ngay_can_bc):
	"""Sub-agent: Analyze daily report stats vs weekly tasks in phiếu."""
	try:
		# Detect if content is Vision JSON (from ocr_daily_report_from_docx)
		try:
			vision_obj = json.loads(daily_report_content)
			is_vision_json = isinstance(vision_obj, dict) and "bao_cao" in vision_obj
		except Exception:
			is_vision_json = False

		if is_vision_json:
			so_ngay_found = vision_obj.get("so_ngay_tim_thay", len(vision_obj.get("bao_cao", [])))
			ngay_dau_found = vision_obj.get("ngay_dau", "")
			ngay_cuoi_found = vision_obj.get("ngay_cuoi", "")
			context_note = (
				f"Dữ liệu đã được Vision API trích xuất: {so_ngay_found} ngày báo cáo "
				f"từ {ngay_dau_found} đến {ngay_cuoi_found}.\n"
				f"Số ngày làm việc cần báo cáo (T2-T6, ngày_bd→ngày_kt): {so_ngay_can_bc or '?'}"
			)
			daily_content_for_prompt = daily_report_content[:10000]
		else:
			context_note = f"Số ngày làm việc cần báo cáo (T2–T6): {so_ngay_can_bc or '?'}"
			daily_content_for_prompt = daily_report_content[:8000]

		prompt = f"""Phân tích báo cáo công việc hàng ngày trong khoảng thời gian:
- Từ ngày: {ngay_bd or 'không rõ'}
- Đến ngày: {ngay_kt or 'không rõ'}
- {context_note}

NỘI DUNG PHIẾU ĐÁNH GIÁ (nhiệm vụ tuần tương ứng để đối chiếu hạng mục):
---
{eval_content[:3000]}
---

DỮ LIỆU BÁO CÁO NGÀY:
---
{daily_content_for_prompt}
---

Phân tích: đếm số ngày đã báo cáo, xác định ngày thiếu báo cáo, đối chiếu hạng mục với phiếu.
Trả về JSON theo schema đã cho."""
		return chat_completion_json(_DAILY_REPORT_SYSTEM, prompt)
	except Exception:
		return None


# ============================================================
# SUB-AGENT: Manager Proposal Evaluator
# ============================================================


def _evaluate_manager_proposal(eval_content, recommendation_data):
	"""Sub-agent: Evaluate manager proposal vs AI recommendation."""
	try:
		rec_summary = json.dumps({
			"recommendation": recommendation_data.get("recommendation", ""),
			"proposal_level": recommendation_data.get("proposal_level", ""),
			"overall_score_note": recommendation_data.get("reasoning", "")[:300],
		}, ensure_ascii=False)
		prompt = f"""Đọc phiếu đánh giá và so sánh đề xuất của quản lý với kết quả AI.

NỘI DUNG PHIẾU ĐÁNH GIÁ TÁI KÝ (tìm phần đề xuất của Quản lý / TBP / HOD / Lãnh đạo):
---
{eval_content[:6000]}
---

KẾT QUẢ ĐÁNH GIÁ CỦA AI:
{rec_summary}

Trích đề xuất của quản lý, so sánh với kết quả AI, đánh giá tính hợp lý.
Trả về JSON theo schema đã cho."""
		return chat_completion_json(_MANAGER_PROPOSAL_SYSTEM, prompt)
	except Exception:
		return None


# ============================================================
# PIPELINE ORCHESTRATOR
# ============================================================

def run_evaluation_pipeline(
	eval_content,
	work_report_content,
	daily_report_content="",
	ngay_bd="",
	ngay_kt="",
	so_ngay_can_bc="",
):
	"""Run the full 5+2 agent evaluation pipeline.

	Args:
		eval_content: Parsed text from evaluation form (Word).
		work_report_content: Parsed text from work report (Excel).
		daily_report_content: Parsed text from daily report (optional).
		ngay_bd: Start date YYYY-MM-DD.
		ngay_kt: End date YYYY-MM-DD.
		so_ngay_can_bc: Expected working days as string.

	Returns:
		Dict with complete evaluation results from all agents.
	"""
	frappe.publish_realtime(
		"eval_progress",
		{"step": 1, "total": 5, "message": "Đang phân tích vai trò & trích xuất thông tin nhân viên..."},
	)

	# Agent 1: Role Analysis + Employee Info Extraction
	role_result = agent_role_analyzer(eval_content, work_report_content)
	role_analysis = role_result.get("role_analysis", role_result)
	extracted_info = role_result.get("extracted_info", {})

	frappe.publish_realtime(
		"eval_progress",
		{"step": 2, "total": 5, "message": "Đang sinh khung năng lực đánh giá..."},
	)

	# Agent 2: Competency Generation
	competency_result = agent_competency_generator(role_analysis)
	evaluation_framework = competency_result.get("evaluation_framework", [])

	if not evaluation_framework:
		frappe.throw("AI không thể sinh khung năng lực. Vui lòng thử lại.")

	frappe.publish_realtime(
		"eval_progress",
		{"step": 3, "total": 5, "message": "Đang phân tích sâu bằng chứng & đối chiếu tự đánh giá..."},
	)

	# Agent 3: Evidence Extraction (Deep Analysis)
	evidence_result = agent_evidence_extractor(eval_content, work_report_content, evaluation_framework)
	evidence = evidence_result.get("evidence", [])
	gap_analysis = evidence_result.get("gap_analysis", {})

	frappe.publish_realtime(
		"eval_progress",
		{"step": 4, "total": 5, "message": "Đang chấm điểm trung lập từng năng lực..."},
	)

	# Agent 4: Scoring (Neutral)
	scores_data = agent_scoring(evaluation_framework, evidence)

	frappe.publish_realtime(
		"eval_progress",
		{"step": 5, "total": 5, "message": "Đang phân tích tổng hợp & đưa ra khuyến nghị..."},
	)

	# Agent 5: Recommendation (Deep Analysis)
	recommendation_data = agent_recommendation(scores_data, role_analysis)

	# Sub-agent A: Daily report analysis (optional)
	bao_cao_ngay = None
	if daily_report_content and daily_report_content.strip():
		frappe.publish_realtime(
			"eval_progress",
			{"step": 5, "total": 5, "message": "Đang phân tích báo cáo ngày..."},
		)
		bao_cao_ngay = _analyze_daily_report(
			daily_report_content, eval_content, ngay_bd, ngay_kt, so_ngay_can_bc
		)

	# Sub-agent B: Manager proposal validation (luôn chạy)
	danh_gia_quan_ly = _evaluate_manager_proposal(eval_content, recommendation_data)

	return {
		"extracted_info": extracted_info,
		"document_completeness": role_result.get("document_completeness", []),
		"role_analysis": role_analysis,
		"evaluation_framework": evaluation_framework,
		"evidence": evidence,
		"gap_analysis": gap_analysis,
		"scores": scores_data,
		"recommendation": recommendation_data,
		"bao_cao_ngay": bao_cao_ngay,
		"danh_gia_quan_ly": danh_gia_quan_ly,
	}

