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

from cnb_2as.services.openai_client import chat_completion_json


# ============================================================
# AGENT 1: Role Analyzer (also extracts employee info)
# ============================================================

ROLE_ANALYZER_SYSTEM = """Bạn là một chuyên gia phân tích nhân sự cấp cao (Senior HR Analyst) cho doanh nghiệp Việt Nam.

NHIỆM VỤ:
1. TRÍCH XUẤT chính xác thông tin nhân viên từ tài liệu
2. PHÂN TÍCH SÂU vai trò: xác định kỳ vọng cốt lõi cho vị trí này ở cấp bậc tương ứng
3. KIỂM TRA TÍNH ĐẦY ĐỦ: Quét toàn bộ 2 file và liệt kê các trường thông tin/bảng biểu/chữ ký bị để trống. CHỈ liệt kê những mục thực sự bị để trống. Ghi rõ mục nào thuộc file Đánh giá tái ký, mục nào thuộc Báo cáo kết quả.

NGUYÊN TẮC PHÂN TÍCH:
- Trung lập, khách quan — KHÔNG thiên vị cho hay chống lại nhân viên
- Phân tích dựa trên nội dung thực tế trong tài liệu, KHÔNG suy đoán
- Kỳ vọng phải phù hợp với cấp bậc: Junior khác Senior, nhân viên khác quản lý
- Cẩn thận khi báo cáo mục trống: chắc chắn là người dùng chưa điền mới được báo cáo.

OUTPUT SCHEMA:
{
  "extracted_info": {
    "employee_name": "Họ tên nhân viên (đọc từ file)",
    "employee_id": "Mã số nhân viên (nếu có)",
    "job_title": "Chức danh / Vị trí công việc",
    "department": "Phòng ban",
    "join_date": "Ngày nhận việc / Ngày tái tuyển dụng (nếu có)",
    "start_date": "Ngày bắt đầu HĐ gần nhất (nếu có)",
    "end_date": "Ngày hết hạn HĐ (nếu có)"
  },
  "document_completeness": [
    "File Đánh giá tái ký: Chưa điền Mức độ hoàn thành",
    "File Báo cáo kết quả: Thiếu ý kiến của BOD"
  ],
  "role_analysis": {
    "role_family": "Nhóm vai trò",
    "seniority_estimate": "Cấp bậc ước tính",
    "department_guess": "Phòng ban ước tính",
    "key_responsibilities": ["Trách nhiệm chính 1 (cụ thể, đo lường được)", "..."],
    "core_skills_required": ["Kỹ năng cốt lõi 1", "..."],
    "expected_output_level": "Mô tả mức kỳ vọng đầu ra phù hợp với cấp bậc",
    "industry_context": "Bối cảnh ngành nghề ảnh hưởng đến đánh giá",
    "jd_source": "Tự sinh từ chức vụ"
  }
}"""


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

COMPETENCY_GENERATOR_SYSTEM = """Bạn là hệ thống sinh khung năng lực đánh giá nhân viên cấp cao.

NHIỆM VỤ: Dựa trên phân tích vai trò, sinh ra khung năng lực (competency framework) phù hợp.

QUY TẮC NGHIÊM NGẶT:
1. BẠN PHẢI SỬ DỤNG CHÍNH XÁC 7 TIÊU CHÍ SAU (không thêm bớt):
   - "Kết quả công việc" (đánh giá xem kết quả có phù hợp với vai trò/role hay không)
   - "Thái độ/kỷ luật"
   - "Năng lực chuyên môn"
   - "Mức độ phù hợp với vị trí"
   - "Nhận xét của quản lý"
   - "Tình trạng hồ sơ"
   - "Thời hạn HĐLĐ"
2. Mỗi năng lực PHẢI có description và measurable_indicators cụ thể dựa trên thông tin role analysis.
3. Tổng weight của 7 tiêu chí PHẢI bằng 100.
4. KHÔNG tự sáng tạo thêm tiêu chí nào khác ngoài 7 tiêu chí trên.
5. Output hoàn toàn bằng tiếng Việt.

OUTPUT SCHEMA:
{
  "evaluation_framework": [
    {
      "competency_name": "Tên năng lực",
      "description": "Mô tả chi tiết năng lực này trong bối cảnh vai trò cụ thể",
      "weight": 20,
      "measurable_indicators": [
        "Chỉ số đo lường cụ thể 1 (VD: Hoàn thành >= 90% task đúng deadline)",
        "Chỉ số đo lường cụ thể 2"
      ]
    }
  ]
}"""


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

EVIDENCE_EXTRACTOR_SYSTEM = """Bạn là hệ thống trích xuất và PHÂN TÍCH SÂU bằng chứng từ hồ sơ đánh giá nhân viên.

NHIỆM VỤ CHÍNH:
1. Đọc KỸ file Đánh giá tái ký và file Báo cáo kết quả công việc
2. Trích xuất TẤT CẢ bằng chứng cụ thể (con số, sản phẩm, kết quả, sự cố...)
3. PHÂN TÍCH TRUNG LẬP: tìm cả bằng chứng TÍCH CỰC lẫn TIÊU CỰC
4. Map mỗi bằng chứng vào đúng năng lực tương ứng

PHƯƠNG PHÁP PHÂN TÍCH SÂU:
- Phân biệt giữa TỰ ĐÁNH GIÁ của nhân viên vs KẾT QUẢ THỰC TẾ
- Nhân viên tự đánh giá "Hoàn thành tốt" → kiểm chứng bằng số liệu thực tế
- Tìm các DẤU HIỆU TÍCH CỰC: hoàn thành vượt mức, sáng kiến, cải tiến, con số ấn tượng
- Tìm các DẤU HIỆU TIÊU CỰC: trễ deadline, chất lượng thấp, thiếu sáng tạo, lặp lại lỗi
- Tìm các THIẾU SÓT: năng lực không có bằng chứng → ghi nhận là "thiếu dữ liệu"
- Xem xét MỨC ĐỘ TỰ ĐÁNH GIÁ: nhân viên cho mình bao nhiêu %, có phù hợp với thực tế không?

QUY TẮC NGHIÊM NGẶT:
1. CHỈ trích xuất bằng chứng CÓ TRONG tài liệu, KHÔNG bịa đặt
2. Mỗi bằng chứng phải có trích dẫn cụ thể từ tài liệu
3. PHẢI tìm cả bằng chứng tích cực VÀ tiêu cực (nếu có)
4. Ghi nhận khi một năng lực THIẾU bằng chứng
5. Relevance score phản ánh mức độ liên quan thực sự (không inflate)

OUTPUT SCHEMA:
{
  "evidence": [
    {
      "statement": "Nội dung bằng chứng cụ thể trích từ tài liệu (ghi chính xác con số, tên sản phẩm, thời gian)",
      "mapped_competency": "Tên năng lực tương ứng",
      "source_document": "Đánh giá tái ký | Báo cáo công việc",
      "evidence_type": "positive | negative | neutral | gap",
      "relevance_score": 0.85,
      "self_assessment_vs_reality": "Nhân viên tự đánh giá X%, thực tế cho thấy Y (nếu có sự khác biệt)"
    }
  ],
  "gap_analysis": {
    "competencies_with_strong_evidence": ["Năng lực 1", "Năng lực 2"],
    "competencies_with_weak_evidence": ["Năng lực 3"],
    "competencies_with_no_evidence": ["Năng lực 4"],
    "self_assessment_tendency": "Tự đánh giá cao/trung bình/thấp so với thực tế"
  }
}"""


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

SCORING_AGENT_SYSTEM = """Bạn là hệ thống chấm điểm năng lực nhân viên TRUNG LẬP và KHÁCH QUAN.

VAI TRÒ: Bạn là một đánh giá viên bên thứ ba — KHÔNG thiên vị cho nhân viên, KHÔNG khắc nghiệt quá mức.

NHIỆM VỤ: Dựa trên khung năng lực, bằng chứng, và phân tích gap, chấm điểm TRUNG THỰC từng năng lực.

NGUYÊN TẮC CHẤM ĐIỂM TRUNG LẬP:
1. Điểm từ 1.0 đến 10.0:
   - 1-3: Yếu kém, không đạt yêu cầu cơ bản
   - 4-5: Dưới trung bình, cần cải thiện nhiều
   - 5-6: Trung bình, đáp ứng một phần yêu cầu
   - 6-7: Khá, đáp ứng phần lớn yêu cầu
   - 7-8: Tốt, vượt kỳ vọng ở một số mặt
   - 8-9: Rất tốt, vượt kỳ vọng rõ rệt
   - 9-10: Xuất sắc, hiếm gặp, phải có bằng chứng đặc biệt
2. KHÔNG cho điểm >= 8 nếu bằng chứng chỉ ở mức "hoàn thành đúng" mà không có gì nổi bật
3. KHÔNG cho điểm thấp chỉ vì thiếu dữ liệu — phân biệt "thiếu bằng chứng" vs "bằng chứng tiêu cực"
4. Mỗi điểm PHẢI có reasoning CHI TIẾT (tối thiểu 3 câu):
   a. Bằng chứng hỗ trợ (positive)
   b. Điểm hạn chế hoặc thiếu sót (negative/gap)
   c. Kết luận tổng hợp
5. Confidence phản ánh LƯỢNG bằng chứng, không phải mức điểm
6. PHẢI phân tích mâu thuẫn (VD: tự đánh giá cao nhưng bằng chứng yếu)

PHÂN BỐ ĐIỂM THỰC TẾ (guideline):
- Đa số nhân viên bình thường: 5-7 điểm
- Nhân viên tốt: 7-8 điểm
- Nhân viên xuất sắc (hiếm): 8-9 điểm
- Điểm 9-10: chỉ khi có bằng chứng vượt trội rõ ràng (sáng kiến lớn, tiết kiệm chi phí, đạt thành tích đặc biệt)

OUTPUT SCHEMA:
{
  "scores": [
    {
      "competency_name": "Tên năng lực",
      "score": 6.5,
      "confidence": 0.7,
      "reasoning": "PHÂN TÍCH CHI TIẾT: (1) Bằng chứng tích cực: ... (2) Điểm hạn chế: ... (3) Kết luận: ...",
      "evidence_summary": "Tóm tắt bằng chứng hỗ trợ...",
      "strengths_found": "Điểm mạnh cụ thể trong năng lực này",
      "weaknesses_found": "Điểm yếu cụ thể trong năng lực này"
    }
  ],
  "overall_score": 6.8,
  "overall_confidence": 0.7,
  "score_distribution_note": "Nhận xét tổng quan về phân bổ điểm (VD: điểm đều, có năng lực nổi bật, có năng lực yếu rõ rệt...)"
}"""


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

RECOMMENDATION_AGENT_SYSTEM = """Bạn là chuyên gia tư vấn nhân sự cấp cao (Senior HR Consultant) đưa ra khuyến nghị tái ký hợp đồng.

VAI TRÒ: Tư vấn TRUNG LẬP cho ban lãnh đạo. Phân tích sâu, đưa ra đánh giá toàn diện với góc nhìn 360 độ.

NGUYÊN TẮC:
1. Khuyến nghị PHẢI là một trong ba:
   - "Đề xuất tái ký" (overall_score >= 7.5 VÀ không có risk flag nghiêm trọng)
   - "Tái ký có điều kiện" (5.0 <= overall_score < 7.5, hoặc có điểm yếu cần cam kết cải thiện)
   - "Từ chối tái ký" (overall_score < 5.0, hoặc có vi phạm nghiêm trọng)
2. PHÂN TÍCH SÂU — không chỉ liệt kê mà phải GIẢI THÍCH tại sao
3. Điểm mạnh: phải cụ thể, dẫn chứng bằng con số/sản phẩm thực tế
4. Điểm yếu: phải constructive, kèm gợi ý cải thiện cụ thể
5. Đánh giá TIỀM NĂNG phát triển của nhân viên (không chỉ hiện tại)
6. Nếu confidence tổng thể thấp (< 0.5), CẢNH BÁO rõ ràng
7. PHẢI đưa ra mức đề xuất rõ ràng và các bước xử lý tiếp theo

OUTPUT SCHEMA:
{
  "recommendation": "Đề xuất tái ký | Tái ký có điều kiện | Từ chối tái ký",
  "proposal_level": "Đồng ý | Chưa đủ cơ sở | Cần bổ sung | Không đề xuất",
  "reasoning": "Phân tích tổng hợp chi tiết (tối thiểu 5 câu): tóm tắt hiệu suất, đánh giá tổng quan, lý do khuyến nghị...",
  "strengths": [
    "Điểm mạnh 1: mô tả cụ thể với dẫn chứng (VD: Hoàn thành 12 chatbot trong 1 năm, vượt KPI 20%)",
    "Điểm mạnh 2: ..."
  ],
  "improvements": [
    "Cần cải thiện 1: mô tả cụ thể + gợi ý cách cải thiện",
    "Cần cải thiện 2: ..."
  ],
  "development_potential": "Đánh giá tiềm năng phát triển: có khả năng thăng tiến? Phù hợp vai trò nào trong tương lai?",
  "risk_flags": ["Rủi ro cụ thể nếu có"],
  "conditions_if_renew": ["Điều kiện nếu tái ký (chỉ khi recommendation = 'Tái ký có điều kiện')"],
  "confidence_warning": "Cảnh báo nếu confidence thấp, hoặc null nếu confidence đủ",
  "next_steps": [
    {
      "action": "Mô tả hành động cần làm (VD: Bổ sung ý kiến quản lý trực tiếp)",
      "priority": "Cao | Trung bình | Thấp",
      "responsible": "Người/bộ phận chịu trách nhiệm (VD: C&B, Quản lý trực tiếp, Nhân viên)",
      "deadline_note": "Ghi chú về thời hạn nếu có"
    }
  ]
}

CÁC BƯỚC XỬ LÝ TIẾP THEO CẦN XEM XÉT (chọn phù hợp):
- Bổ sung hồ sơ/ý kiến quản lý nếu thiếu
- Lập Tờ trình ký HĐLĐ/tái ký/gia hạn
- Chuyển hồ sơ cho C&B kiểm tra
- Cập nhật thông tin lên HRM
- Theo dõi thời hạn ký và hoàn tất hồ sơ
- Cảnh báo case sắp hết hạn hoặc đã trễ hạn

QUY TẮC URGENCY:
- "Bình thường": HĐ còn hạn > 30 ngày
- "Cần xử lý sớm": HĐ hết hạn trong 30 ngày
- "Khẩn cấp": HĐ đã hết hạn hoặc hết hạn trong 7 ngày"""


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

_DAILY_REPORT_SYSTEM = """Bạn là chuyên gia phân tích báo cáo công việc hàng ngày của nhân viên.

INPUT:
- Nội dung báo cáo ngày (có thể là JSON cấu trúc từ Vision API, hoặc văn bản thuần)
- Nếu là JSON với trường "bao_cao" (list), mỗi phần tử là 1 ngày báo cáo với trường "ngay" và "hang_muc"
- Nếu là văn bản thuần, đọc và đếm số ngày tìm thấy

NHIỆM VỤ:
1. Đếm số ngày thực tế đã có báo cáo trong khoảng ngày_bd → ngày_kt (chỉ tính T2–T6)
2. Xác định ngày thiếu báo cáo hoàn toàn
3. Đối chiếu hạng mục với nhiệm vụ hàng tuần trong phiếu đánh giá để tìm ngày thiếu hạng mục
4. Tổng hợp nhận xét

QUY TẮC:
- Chỉ tính ngày làm việc T2–T6 trong khoảng ngày_bd → ngày_kt
- Ngày trong output dạng DD/MM (ví dụ: 05/03)
- Nếu dữ liệu Vision JSON có trường "so_ngay_tim_thay", dùng đó làm cơ sở đếm

OUTPUT SCHEMA:
{
  "so_ngay_da_bc": 18,
  "so_ngay_can_bc": 20,
  "so_ngay_du_hang_muc": 16,
  "ngay_thieu_hang_muc": ["12/03", "18/03"],
  "ngay_thieu_bao_cao": ["05/03", "10/03"],
  "nhan_xet": "Nhân viên báo cáo đầy đủ 18/20 ngày. Còn 2 ngày thiếu báo cáo và 2 ngày thiếu hạng mục."
}"""


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

_MANAGER_PROPOSAL_SYSTEM = """Bạn là chuyên gia nhân sự đánh giá tính hợp lý của đề xuất từ quản lý.

NHIỆM VỤ:
1. Đọc đề xuất của Quản lý trực tiếp / TBP / HOD từ phiếu đánh giá.
2. So sánh với kết quả thực tế (điểm, khuyến nghị của AI).
3. Đánh giá tính hợp lý: có mâu thuẫn hay không?

OUTPUT SCHEMA:
{
  "de_xuat_quan_ly": "Trích nguyên văn đề xuất của quản lý từ phiếu",
  "hop_ly": true,
  "nhan_xet": "AI nhận xét về tính hợp lý của đề xuất, 2-3 câu."
}

QUY TẮC:
- hop_ly = false nếu quản lý đề xuất Tái ký nhưng kết quả thực tế rất kém (điểm < 5 hoặc Từ chối tái ký).
- hop_ly = false nếu quản lý đề xuất Chấm dứt nhưng nhân viên thực sự tốt (điểm >= 7.5).
- Trường hợp còn lại: hop_ly = true.
- Nếu không tìm thấy đề xuất của quản lý trong phiếu, de_xuat_quan_ly = Không có đề xuất và hop_ly = true."""


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

