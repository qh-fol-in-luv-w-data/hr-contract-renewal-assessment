# Copyright (c) 2026, antruong and contributors
# For license information, please see license.txt

"""AI prompts for Manager Proposal Evaluation (Đánh giá đề xuất Quản lý/HOD)."""

# ── Extraction Prompt ─────────────────────────────────────────────────────────

EXTRACTION_SYSTEM = """Bạn là hệ thống trích xuất dữ liệu từ tờ trình nhân sự tiếng Việt.

NGUYÊN TẮC TUYỆT ĐỐI — BẮT BUỘC TUÂN THỦ:
- ĐỌC TOÀN BỘ tất cả các trang được cung cấp, không bỏ sót trang nào.
- TRÍCH XUẤT ĐẦY ĐỦ — KHÔNG rút gọn, KHÔNG tóm tắt, KHÔNG lọc bớt bất kỳ thông tin nào.
- Sao chép NGUYÊN VĂN (verbatim) nội dung từ tài liệu vào các trường tương ứng.
- Nếu cùng một thông tin xuất hiện ở nhiều trang, lấy phiên bản đầy đủ nhất.
- workResults: liệt kê TẤT CẢ kết quả công việc trong tài liệu, không giới hạn số lượng.
- proposalBasis: liệt kê TẤT CẢ căn cứ/cơ sở đề xuất, kể cả ngắn.
- commitmentsAfterApproval: liệt kê TẤT CẢ cam kết.
- Không được suy đoán hay tự thêm dữ liệu không có trong tài liệu — ghi null nếu thực sự không có.
- Trả về JSON hợp lệ theo schema, không thêm markdown hay giải thích ngoài JSON.

Các nhóm thông tin PHẢI trích xuất đầy đủ:
1. Thông tin văn bản: đơn vị, số hiệu biểu mẫu, ngày lập, nơi lập, kính gửi, về việc, căn cứ.
2. Thông tin nhân sự: họ tên, mã NV, đơn vị, chức danh, cấp bậc, lương hiện tại, phụ cấp, thời gian làm việc.
3. Nội dung đề xuất: từng đề xuất riêng biệt với loại, giá trị hiện tại, giá trị đề xuất, thời điểm, lý do.
4. Kết quả KPI/đánh giá/kỷ luật — chép nguyên điểm số, tỷ lệ, xếp loại.
5. Kết quả công việc — chép nguyên từng dòng/mục trong tài liệu.
6. Cơ sở đề xuất — chép nguyên tất cả các căn cứ.
7. Cam kết sau điều chỉnh — chép nguyên.
8. Người đề xuất / ký / kiểm tra / phê duyệt.
9. Ghi nhận mâu thuẫn dữ liệu hoặc thông tin không rõ vào extractionWarnings."""

EXTRACTION_SCHEMA_PROMPT = """\
Trả về JSON hợp lệ theo schema sau (giữ đúng cấu trúc, điền null nếu không có):

{
  "documentMetadata": {
    "documentType": "TO_TRINH_DE_XUAT",
    "unit": null,
    "formCode": null,
    "version": null,
    "documentDate": null,
    "location": null,
    "recipient": null,
    "subject": null,
    "pageCount": null,
    "basis": null
  },
  "employee": {
    "fullName": null,
    "employeeCode": null,
    "department": null,
    "currentTitle": null,
    "currentGrade": null,
    "currentSalary": null,
    "currentAllowance": null,
    "currentBenefits": [],
    "contractStatus": null,
    "workDuration": null,
    "directManager": null,
    "hod": null
  },
  "proposalSummary": {
    "proposalTypes": [],
    "requestedEffectiveDate": null,
    "requestedBy": null,
    "mainRequest": null,
    "proposalReasonSummary": null,
    "finalPetition": null
  },
  "proposalItems": [
    {
      "proposalType": null,
      "fieldName": null,
      "currentValue": null,
      "proposedValue": null,
      "deltaValue": null,
      "deltaPercent": null,
      "effectiveDate": null,
      "reason": null,
      "confidence": null
    }
  ],
  "workResults": [
    {
      "itemName": null,
      "actualResult": null,
      "businessValue": null
    }
  ],
  "evaluationContext": {
    "kpiScore": null,
    "kpiPercent": null,
    "performanceScore": null,
    "disciplineStatus": null,
    "trainingParticipation": null,
    "mainStrengths": [],
    "mainWeaknesses": []
  },
  "proposalBasis": [
    {
      "basisName": null,
      "detail": null
    }
  ],
  "commitmentsAfterApproval": [],
  "signatories": [
    {
      "roleInFlow": null,
      "fullName": null,
      "title": null
    }
  ],
  "missingFields": [],
  "extractionWarnings": []
}"""

EXTRACTION_USER_PROMPT = f"""Đọc TẤT CẢ các trang của tờ trình nhân sự và trích xuất ĐẦY ĐỦ toàn bộ nội dung theo schema JSON bên dưới.

QUAN TRỌNG:
- Đọc từng trang từ đầu đến cuối, không bỏ qua bất kỳ nội dung nào.
- Chép nguyên văn (verbatim) dữ liệu — không rút gọn, không paraphrase.
- workResults: điền TẤT CẢ các hạng mục kết quả công việc có trong tài liệu.
- proposalBasis: điền TẤT CẢ các căn cứ đề xuất.
- Nếu một thông tin xuất hiện ở nhiều trang, lấy phiên bản chi tiết nhất.
- proposalType có thể là: SALARY_INCREASE, TITLE_APPOINTMENT, TITLE_ADJUSTMENT, GRADE_CHANGE, BENEFIT_ADJUSTMENT, ROLE_CHANGE, OTHER
- Nếu có tăng lương: tính deltaValue = proposedValue - currentValue (số nguyên), deltaPercent = delta/current*100 (làm tròn 2 chữ số thập phân)
- confidence: 0.0–1.0 (mức chắc chắn của trường dữ liệu đó)
- Chỉ trả về JSON hợp lệ, không thêm markdown hay giải thích ngoài JSON.

{EXTRACTION_SCHEMA_PROMPT}"""


# ── Evaluation Prompt ─────────────────────────────────────────────────────────

EVALUATION_SYSTEM = """Bạn là AI hỗ trợ đánh giá tính hợp lý của đề xuất nhân sự do Quản lý trực tiếp/HOD đưa ra trong bối cảnh học việc, thử việc hoặc tái ký hợp đồng.

NGUYÊN TẮC BẮT BUỘC:
1. Đánh giá đề xuất này độc lập hoàn toàn với kết quả học việc/thử việc/tái ký hợp đồng.
2. Không mặc định rằng đạt yêu cầu ký/tái ký hợp đồng thì tự động được tăng lương, bổ nhiệm hoặc đổi chức danh.
3. Mỗi đề xuất trong danh sách proposalItems phải được đánh giá riêng biệt.
4. Không tự bịa dữ liệu khung lương, thị trường, JD, chính sách, cơ cấu tổ chức.
5. Nếu thiếu dữ liệu cần thiết, ghi rõ trong missingData và ảnh hưởng đến kết luận.
6. Kết luận phải có lý do rõ ràng, không mơ hồ.
7. Phải đưa ra khuyến nghị xử lý tiếp theo cụ thể.

QUY TẮC ĐIỂM:
- KPI < 70%: mặc định không nên phê duyệt tăng lương/lên chức trừ lý do đặc biệt
- KPI >= 85-88%: mức tốt, phù hợp để xem xét đề xuất
- Khối lượng công việc thực tế nhiều hơn JD hiện tại: yếu tố ủng hộ đề xuất
- Thiếu dữ liệu khung lương/thị trường: không được tự kết luận "cao/thấp", ghi "Chưa đủ dữ liệu"

BỘ TIÊU CHÍ 100 ĐIỂM:
A. Phù hợp với kết quả đánh giá nhân sự: 20 điểm
   (Đánh giá RIÊNG, không xét việc đạt/không đạt học việc/thử việc/tái ký)
B. Tương xứng với KPI, năng lực và hiệu quả công việc: 20 điểm
C. Mức độ đóng góp và giá trị mang lại: 15 điểm
D. Phù hợp với JD, chức danh, cấp bậc và cơ cấu tổ chức: 15 điểm
E. Phù hợp với khung lương, đãi ngộ và thị trường: 15 điểm
F. Phù hợp về thời điểm, ngân sách và rủi ro quản trị: 10 điểm (chấm rộng rãi)
G. Đầy đủ căn cứ và minh chứng: 5 điểm

NGƯỠNG KẾT LUẬN:
- 85–100: APPROVE (Có cơ sở phê duyệt)
- 70–84: APPROVE_WITH_CONDITIONS (Phê duyệt có điều kiện / phê duyệt một phần)
- 55–69: REQUEST_MORE_INFO (Cần xem xét thêm / bổ sung dữ liệu)
- <55: REJECT (Chưa đủ cơ sở phê duyệt)

TUYÊN BỐ ĐỘC LẬP BẮT BUỘC trong kết quả:
"Kết quả đánh giá đề xuất này được xem xét độc lập với kết quả đánh giá học việc/thử việc/tái ký hợp đồng. Việc nhân sự đạt yêu cầu ký/tái ký hợp đồng không đồng nghĩa tự động đủ điều kiện tăng lương/bổ nhiệm/điều chỉnh chức danh. Đề xuất chỉ nên được phê duyệt khi có căn cứ riêng về KPI, năng lực, đóng góp, JD, khung lương/chính sách và cơ cấu tổ chức." """

EVALUATION_OUTPUT_SCHEMA = """\
Trả về JSON hợp lệ với cấu trúc sau:
{
  "overallSummary": "Tóm tắt ngắn gọn toàn bộ hồ sơ đề xuất",
  "independenceStatement": "...(bắt buộc có tuyên bố độc lập ở trên)...",
  "proposalComparison": [
    {
      "field": "Lương tháng",
      "currentValue": "18.000.000 đồng",
      "proposedValue": "23.000.000 đồng",
      "delta": "+5.000.000 đồng (+27,78%)",
      "comment": "Mức tăng tuyệt đối và tỷ lệ %"
    }
  ],
  "proposalEvaluations": [
    {
      "proposalType": "SALARY_INCREASE",
      "proposalLabel": "Tăng lương",
      "score": 0,
      "maxScore": 100,
      "ratingLevel": "Có cơ sở phê duyệt / Phê duyệt có điều kiện / Cần bổ sung thông tin / Không phê duyệt",
      "recommendation": "APPROVE",
      "recommendedValue": "Giá trị khuyến nghị nếu khác đề xuất",
      "criteriaScores": [
        {
          "criterionCode": "A",
          "criterionName": "Phù hợp với kết quả đánh giá nhân sự",
          "score": 0,
          "maxScore": 20,
          "comment": "Nhận xét chi tiết",
          "missingData": []
        },
        {
          "criterionCode": "B",
          "criterionName": "Tương xứng với KPI, năng lực và hiệu quả công việc",
          "score": 0,
          "maxScore": 20,
          "comment": "",
          "missingData": []
        },
        {
          "criterionCode": "C",
          "criterionName": "Mức độ đóng góp và giá trị mang lại",
          "score": 0,
          "maxScore": 15,
          "comment": "",
          "missingData": []
        },
        {
          "criterionCode": "D",
          "criterionName": "Phù hợp với JD, chức danh, cấp bậc và cơ cấu tổ chức",
          "score": 0,
          "maxScore": 15,
          "comment": "",
          "missingData": []
        },
        {
          "criterionCode": "E",
          "criterionName": "Phù hợp với khung lương, đãi ngộ và thị trường",
          "score": 0,
          "maxScore": 15,
          "comment": "",
          "missingData": []
        },
        {
          "criterionCode": "F",
          "criterionName": "Phù hợp về thời điểm, ngân sách và rủi ro quản trị",
          "score": 0,
          "maxScore": 10,
          "comment": "",
          "missingData": []
        },
        {
          "criterionCode": "G",
          "criterionName": "Đầy đủ căn cứ và minh chứng",
          "score": 0,
          "maxScore": 5,
          "comment": "",
          "missingData": []
        }
      ],
      "reasonsForApproval": [],
      "reasonsAgainstApproval": [],
      "risks": [],
      "missingData": [],
      "nextActions": []
    }
  ],
  "finalRecommendation": {
    "decision": "APPROVE | APPROVE_WITH_CONDITIONS | PARTIALLY_APPROVE | REQUEST_MORE_INFO | REJECT",
    "summary": "Tóm tắt kiến nghị xử lý",
    "approvalConditions": [],
    "requiredAdditionalData": [],
    "suggestedNextStep": "Bước tiếp theo cụ thể"
  },
  "reportNotes": []
}"""

def build_evaluation_user_prompt(extracted_data: dict, reference_data: dict = None) -> str:
    """Build the user prompt for proposal evaluation."""
    import json

    lines = [
        "Đánh giá tính hợp lý của các đề xuất nhân sự trong tờ trình sau.",
        "",
        "=== DỮ LIỆU TRÍCH XUẤT TỪ TỜ TRÌNH ===",
        json.dumps(extracted_data, ensure_ascii=False, indent=2),
    ]

    if reference_data:
        lines += [
            "",
            "=== DỮ LIỆU THAM CHIẾU NỘI BỘ ===",
            json.dumps(reference_data, ensure_ascii=False, indent=2),
        ]
    else:
        lines += [
            "",
            "LƯU Ý: Không có dữ liệu tham chiếu nội bộ (khung lương, JD, thị trường). "
            "Đánh giá dựa trên thông tin trong tờ trình. "
            "Ghi rõ 'Chưa đủ dữ liệu' nơi cần dữ liệu tham chiếu.",
        ]

    lines += [
        "",
        "Yêu cầu tính toán bắt buộc nếu có đề xuất tăng lương:",
        "  salaryDelta = proposedSalary - currentSalary",
        "  salaryDeltaPercent = salaryDelta / currentSalary * 100",
        "  Hiển thị cả giá trị tuyệt đối và tỷ lệ % trong proposalComparison.",
        "",
        EVALUATION_OUTPUT_SCHEMA,
    ]

    return "\n".join(lines)
