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
    _HOP_DONG_SYSTEM,
    _DE_XUAT_NHAN_SU_SYSTEM,
    _JD_SUGGESTION_SYSTEM,
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

		# ── Deterministic counting (code-based) for Vision JSON ──
		pre_computed = None  # will be dict if computed
		if is_vision_json:
			import re as _re
			from datetime import date, timedelta

			bao_cao_list = vision_obj.get("bao_cao", [])

			# Parse ngay strings "DD/MM/YYYY" → date objects
			def _parse_ngay(s):
				m = _re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", str(s).strip())
				if m:
					try:
						return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
					except ValueError:
						return None
				return None

			# Collect all unique reported dates
			reported_dates = set()
			for item in bao_cao_list:
				d = _parse_ngay(item.get("ngay", ""))
				if d:
					reported_dates.add(d)

			# Build full working-day set in range
			working_days = set()
			if ngay_bd and ngay_kt:
				try:
					d_start = date.fromisoformat(ngay_bd)
					d_end = date.fromisoformat(ngay_kt)
					cur = d_start
					while cur <= d_end:
						if cur.weekday() < 5:  # Mon–Fri
							working_days.add(cur)
						cur += timedelta(days=1)
				except ValueError:
					pass

			# Missing days = working days not in reported set
			missing_dates = sorted(working_days - reported_dates) if working_days else []

			so_ngay_can = int(so_ngay_can_bc) if so_ngay_can_bc and str(so_ngay_can_bc).isdigit() else len(working_days)
			so_ngay_da = len(reported_dates)
			ngay_thieu_list = [f"{d.day:02d}/{d.month:02d}" for d in missing_dates]

			# Days with hang_muc filled: at least 1 hang_muc entry with non-empty cong_viec
			def _has_hang_muc(item):
				hm = item.get("hang_muc", [])
				if not hm:
					return False
				return any(str(h.get("cong_viec", "")).strip() for h in hm)

			so_ngay_du_hm = sum(1 for item in bao_cao_list if _parse_ngay(item.get("ngay", "")) and _has_hang_muc(item))

			# Days in bao_cao_list but with missing/empty hang_muc
			ngay_thieu_hm = []
			for item in bao_cao_list:
				d = _parse_ngay(item.get("ngay", ""))
				if d and not _has_hang_muc(item):
					ngay_thieu_hm.append(f"{d.day:02d}/{d.month:02d}")

			pre_computed = {
				"so_ngay_da_bc": so_ngay_da,
				"so_ngay_can_bc": so_ngay_can,
				"so_ngay_du_hang_muc": so_ngay_du_hm,
				"ngay_thieu_bao_cao": ngay_thieu_list,
				"ngay_thieu_hang_muc": sorted(ngay_thieu_hm),
			}

			# Slim down bao_cao for AI prompt: only send first 15 entries, summarised
			slim_bao_cao = []
			for item in bao_cao_list[:15]:
				slim_bao_cao.append({
					"ngay": item.get("ngay", ""),
					"hang_muc": [h.get("hang_muc", "") for h in (item.get("hang_muc") or [])],
				})

			context_note = (
				f"[ĐÃ TÍNH TỪ CODE] Số ngày đã báo cáo: {so_ngay_da}/{so_ngay_can}. "
				f"Ngày thiếu báo cáo: {ngay_thieu_list or 'không có'}. "
				f"Ngày thiếu hạng mục: {sorted(ngay_thieu_hm) or 'không có'}.\n"
				f"Dữ liệu hạng mục (tóm tắt {len(slim_bao_cao)} ngày đầu):\n"
				+ json.dumps(slim_bao_cao, ensure_ascii=False)
			)
		else:
			context_note = f"Số ngày làm việc cần báo cáo (T2–T6): {so_ngay_can_bc or '?'}"
			slim_bao_cao = None

		daily_content_for_prompt = daily_report_content[:8000] if not is_vision_json else ""

		prompt = f"""Phân tích báo cáo công việc hàng ngày trong khoảng thời gian:
- Từ ngày: {ngay_bd or 'không rõ'}
- Đến ngày: {ngay_kt or 'không rõ'}
- {context_note}

NỘI DUNG PHIẾU ĐÁNH GIÁ (nhiệm vụ tuần tương ứng để đối chiếu hạng mục):
---
{eval_content[:3000]}
---
{"DỮ LIỆU BÁO CÁO NGÀY:" + chr(10) + "---" + chr(10) + daily_content_for_prompt + chr(10) + "---" if daily_content_for_prompt else ""}

{"QUAN TRỌNG: Các trường so_ngay_da_bc, so_ngay_can_bc, ngay_thieu_bao_cao, ngay_thieu_hang_muc, so_ngay_du_hang_muc đã được TÍNH SẴN bằng code ở trên. Bạn PHẢI sử dụng đúng các con số đó, KHÔNG tự đếm lại." if pre_computed else "Phân tích: đếm số ngày đã báo cáo, xác định ngày thiếu báo cáo, đối chiếu hạng mục với phiếu."}
Chỉ cần: đối chiếu hạng mục với nhiệm vụ trong phiếu (doi_chieu_cong_viec) và viết nhan_xet.
Trả về JSON theo schema đã cho."""

		ai_result = chat_completion_json(_DAILY_REPORT_SYSTEM, prompt)

		# Merge pre-computed counts into AI result (override unreliable AI counts)
		if pre_computed and isinstance(ai_result, dict):
			ai_result.update(pre_computed)

		return ai_result
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
# SUB-AGENT C: Contract Evaluation (Hợp đồng)
# ============================================================


def _evaluate_hop_dong(eval_content, work_report_content, recommendation_data, scores_data, bao_cao_ngay=None, role_analysis=None):
	"""Sub-agent C: Đánh giá điều kiện ký/tái ký/gia hạn hợp đồng lao động."""
	try:
		rec_summary = json.dumps({
			"recommendation": recommendation_data.get("recommendation", ""),
			"overall_score": recommendation_data.get("overall_score", 0),
			"proposal_level": recommendation_data.get("proposal_level", ""),
			"strengths": recommendation_data.get("strengths", []),
			"improvements": recommendation_data.get("improvements", []),
		}, ensure_ascii=False)
		scores_summary = json.dumps(
			[{"competency": s.get("competency"), "score": s.get("score"),
			  "justification": str(s.get("justification", ""))[:100]}
			 for s in (scores_data.get("competency_scores") or [])],
			ensure_ascii=False
		)[:3000]
		bao_cao_summary = ""
		if bao_cao_ngay and isinstance(bao_cao_ngay, dict):
			bao_cao_summary = (
				f"Báo cáo ngày: {bao_cao_ngay.get('so_ngay_da_bc', '?')}/{bao_cao_ngay.get('so_ngay_can_bc', '?')} ngày. "
				f"{bao_cao_ngay.get('nhan_xet', '')}"
			)
		# Build JD context from role_analysis if available
		jd_context = ""
		if role_analysis and isinstance(role_analysis, dict):
			chuc_danh = role_analysis.get("position_title") or role_analysis.get("chuc_danh") or ""
			expectations = role_analysis.get("role_expectations") or role_analysis.get("expected_competencies") or []
			if chuc_danh:
				jd_context = f"Chức danh đang đánh giá: {chuc_danh}.\n"
			if expectations:
				jd_ctx_str = json.dumps(expectations, ensure_ascii=False)[:500]
				jd_context += f"Kỳ vọng vai trò (từ JD): {jd_ctx_str}\n"
		prompt = (
			f"Đây là đánh giá TÁI KÝ hợp đồng (không phải ký mới). "
			f"Phân tích điều kiện tái ký dựa trên kết quả thực tế đã thể hiện trong kỳ HĐ vừa qua.\n\n"
			+ (f"THÔNG TIN JD / VAI TRÒ:\n{jd_context}\n" if jd_context else "")
			+ f"NỘI DUNG PHIẾU ĐÁNH GIÁ:\n---\n{eval_content[:5000]}\n---\n\n"
			+ f"KẾT QUẢ BÁO CÁO KPI / CÔNG VIỆC:\n---\n{work_report_content[:3000]}\n---\n\n"
			+ (f"THÔNG TIN BÁO CÁO NGÀY: {bao_cao_summary}\n\n" if bao_cao_summary else "")
			+ f"KẾT QUẢ ĐÁNH GIÁ AI:\n{rec_summary}\n\n"
			+ f"ĐIỂM NĂNG LỰC:\n{scores_summary}\n\n"
			+ "Đánh giá điều kiện tái ký/gia hạn hợp đồng theo từng tiêu chí. Trả về JSON theo schema."
		)
		return chat_completion_json(_HOP_DONG_SYSTEM, prompt)
	except Exception:
		return None


# ============================================================
# SUB-AGENT D: HR Proposal Evaluation (Đề xuất nhân sự)
# ============================================================


def _evaluate_de_xuat_nhan_su(eval_content, recommendation_data, scores_data, role_analysis=None):
	"""Sub-agent D: Đánh giá các đề xuất nhân sự (tăng lương, bổ nhiệm, điều chỉnh...)."""
	try:
		rec_summary = json.dumps({
			"recommendation": recommendation_data.get("recommendation", ""),
			"overall_score": recommendation_data.get("overall_score", 0),
			"proposal_level": recommendation_data.get("proposal_level", ""),
		}, ensure_ascii=False)
		scores_summary = json.dumps(
			[{"competency": s.get("competency"), "score": s.get("score")}
			 for s in (scores_data.get("competency_scores") or [])],
			ensure_ascii=False
		)[:2000]
		# Build JD context from role_analysis to evaluate proposal fit
		jd_context = ""
		if role_analysis and isinstance(role_analysis, dict):
			chuc_danh = role_analysis.get("position_title") or role_analysis.get("chuc_danh") or ""
			cap_bac = role_analysis.get("level") or role_analysis.get("cap_bac") or ""
			expectations = role_analysis.get("role_expectations") or role_analysis.get("expected_competencies") or []
			if chuc_danh:
				jd_context = f"Chức danh hiện tại: {chuc_danh}. Cấp bậc: {cap_bac}.\n"
			if expectations:
				jd_ctx_str = json.dumps(expectations, ensure_ascii=False)[:400]
				jd_context += f"Kỳ vọng JD hiện tại: {jd_ctx_str}\n"
		prompt = (
			f"Tìm kiếm và đánh giá các đề xuất nhân sự trong phiếu đánh giá tái ký hợp đồng.\n\n"
			+ (f"THÔNG TIN JD / CẤP BẬC HIỆN TẠI:\n{jd_context}\n" if jd_context else "")
			+ f"NỘI DUNG PHIẾU ĐÁNH GIÁ (tìm các đề xuất tăng lương, bổ nhiệm, điều chỉnh chức danh,\n"
			+ "thay đổi cấp bậc, điều chỉnh chế độ đãi ngộ v.v.):\n---\n"
			+ f"{eval_content[:6000]}\n---\n\n"
			+ f"KẾT QUẢ ĐÁNH GIÁ AI:\n{rec_summary}\n\n"
			+ f"ĐIỂM NĂNG LỰC:\n{scores_summary}\n\n"
			+ "Phân tích tính phù hợp từng đề xuất, đánh giá mức độ ưu tiên và tác động. Trả về JSON theo schema."
		)
		return chat_completion_json(_DE_XUAT_NHAN_SU_SYSTEM, prompt)
	except Exception:
		return None


# ============================================================
# SUB-AGENT E: JD Suggestion (Gợi ý Job Description)
# ============================================================


def _generate_jd_suggestion(eval_content, work_report_content, role_analysis, scores_data):
	"""Sub-agent E: Gợi ý JD (Job Description) theo chức danh/vị trí được đánh giá."""
	try:
		# Extract key role info
		chuc_danh = ""
		if isinstance(role_analysis, dict):
			chuc_danh = (
				role_analysis.get("position_title") or
				role_analysis.get("chuc_danh") or
				role_analysis.get("role") or ""
			)
		scores_summary = json.dumps(
			[{"competency": s.get("competency"), "score": s.get("score")}
			 for s in (scores_data.get("competency_scores") or [])],
			ensure_ascii=False
		)[:2000]
		prompt = (
			f"Xây dựng gợi ý Job Description (Mô tả công việc) cho vị trí sau.\n\n"
			f"CHỨC DANH/VỊ TRÍ: {chuc_danh}\n\n"
			f"NỘI DUNG PHIẾU ĐÁNH GIÁ (bao gồm thông tin nhân viên, JD hiện tại nếu có, công việc thực tế):\n---\n"
			f"{eval_content[:4000]}\n---\n\n"
			f"KẼT QUẢ KPI / CÔNG VIỆC THỰC TẼ:\n---\n{work_report_content[:2500]}\n---\n\n"
			f"PHIẼU NĂNG LỰC (từ AI):\n{scores_summary}\n\n"
			"Dựa trên toàn bộ thông tin trên, ghi ra một bản JD gợi ý chuẩn theo schema."
		)
		return chat_completion_json(_JD_SUGGESTION_SYSTEM, prompt)
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

	# Sub-agent C: Contract conditions evaluation (luôn chạy)
	frappe.publish_realtime(
		"eval_progress",
		{"step": 5, "total": 8, "message": "Đang đánh giá điều kiện ký/tái ký hợp đồng..."},
	)
	danh_gia_hop_dong = _evaluate_hop_dong(
		eval_content, work_report_content, recommendation_data, scores_data, bao_cao_ngay,
		role_analysis=role_analysis,
	)

	# Sub-agent D: HR proposals evaluation (luôn chạy)
	frappe.publish_realtime(
		"eval_progress",
		{"step": 6, "total": 8, "message": "Đang đánh giá đề xuất nhân sự..."},
	)
	danh_gia_de_xuat_nhan_su = _evaluate_de_xuat_nhan_su(
		eval_content, recommendation_data, scores_data, role_analysis=role_analysis
	)

	# Sub-agent E: JD suggestion (luôn chạy)
	frappe.publish_realtime(
		"eval_progress",
		{"step": 7, "total": 8, "message": "Đang xây dựng gợi ý JD..."},
	)
	jd_goi_y = _generate_jd_suggestion(eval_content, work_report_content, role_analysis, scores_data)

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
		"danh_gia_hop_dong": danh_gia_hop_dong,
		"danh_gia_de_xuat_nhan_su": danh_gia_de_xuat_nhan_su,
		"jd_goi_y": jd_goi_y,
	}

