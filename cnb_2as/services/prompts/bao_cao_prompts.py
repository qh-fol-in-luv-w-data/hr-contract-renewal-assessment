"""Prompts cho OCR phiếu đánh giá nhân sự PAI và AI overview analysis."""

OCR_SYSTEM = (
    "Bạn là hệ thống OCR phiếu đánh giá nhân sự nội bộ doanh nghiệp (quy trình HR hợp lệ). "
    "Đọc chính xác mọi ô, giữ nguyên tiếng Việt có dấu. Trả JSON thuần, không wrap code block."
)

OCR_PROMPT = """Đây là phiếu đánh giá nhân sự PAI (4 trang). Đọc TOÀN BỘ mọi ô, mọi bảng.

PHÂN BIỆT 2 LOẠI PHIẾU (đọc tiêu đề / header trang 1):
- "tu_danh_gia": tiêu đề chứa "TỰ ĐÁNH GIÁ" hoặc "nhân viên tự" — nhân viên tự chấm
- "hod": tiêu đề chứa "ĐÁNH GIÁ NHÂN SỰ" (không có chữ "tự") hoặc "HOD" — quản lý chấm
→ Nhóm C: tu_danh_gia chỉ C1-C3 (diem_toi_da=15); hod có C1-C4 (diem_toi_da=20)

ĐỌC ĐÚNG NGƯỜI (quan trọng — đừng nhầm):
- thong_tin_nhan_vien.ho_ten = TÊN NHÂN VIÊN ĐƯỢC ĐÁNH GIÁ
  → Đọc từ dòng "Họ và tên:" hoặc "Nhân viên:" ở ĐẦU trang 1, KHÔNG phải chữ ký cuối
  → Đây là người được đánh giá, KHÔNG phải người đánh giá, KHÔNG phải HOD
- nguoi_danh_gia.ho_ten = tên người đánh giá
  → Đọc từ dòng "Người đánh giá:" hoặc "Trưởng bộ phận:" hoặc chữ ký "HOD" ở trang cuối
  → Đây là quản lý / HOD, KHÔNG phải nhân viên được đánh giá

CÁCH ĐỌC ĐIỂM:
Mỗi tiêu chí có 5 cột điểm (1, 2, 3, 4, 5). Điểm được đánh dấu bằng một trong các cách:
- Khoanh tròn (circle) xung quanh số
- Tô đậm / tô màu / fill vào ô hoặc số
- Đánh dấu X hoặc tick (✓) vào ô
- Gạch dưới hoặc ghi tay số vào ô
Xác định ô NÀO được đánh dấu và lấy con số đó (1–5) làm "diem".
Điểm trong bảng tương ứng với CHÍNH XÁC hàng của tiêu chí đó (A1, A2... B1... C1...).
KHÔNG đọc điểm của tiêu chí này gán sang tiêu chí khác.
Nếu không có ô nào được đánh dấu rõ ràng, để "diem": null.
KHÔNG tự ước đoán điểm khi không nhìn thấy dấu đánh.

Trả JSON theo cấu trúc:
{
  "loai_phieu": "tu_danh_gia",
  "thong_tin_nhan_vien": {
    "ho_ten": "", "chuc_danh": "", "phong_ban": "",
    "thoi_gian_lam_viec": "", "ky_danh_gia_tu": "", "ky_danh_gia_den": "",
    "ngay_danh_gia": ""
  },
  "nguoi_danh_gia": {"ho_ten": "", "chuc_danh": ""},
  "thang_diem": [
    {"diem": 5, "muc_do": "Xuất sắc", "mo_ta": ""},
    {"diem": 4, "muc_do": "Tốt", "mo_ta": ""},
    {"diem": 3, "muc_do": "Đạt yêu cầu", "mo_ta": ""},
    {"diem": 2, "muc_do": "Cần cải thiện", "mo_ta": ""},
    {"diem": 1, "muc_do": "Không đạt", "mo_ta": ""}
  ],
  "nhom_A": {
    "ten": "Tinh thần & Thái độ làm việc", "ty_trong": 30, "diem_toi_da": 25,
    "tieu_chi": [
      {"stt": "A1", "ten": "", "mo_ta": "", "diem": null, "nhan_xet": ""},
      {"stt": "A2", "ten": "", "mo_ta": "", "diem": null, "nhan_xet": ""},
      {"stt": "A3", "ten": "", "mo_ta": "", "diem": null, "nhan_xet": ""},
      {"stt": "A4", "ten": "", "mo_ta": "", "diem": null, "nhan_xet": ""},
      {"stt": "A5", "ten": "", "mo_ta": "", "diem": null, "nhan_xet": ""}
    ],
    "tong_diem_tho": null, "diem_quy_doi": null, "nhan_xet_nhom": ""
  },
  "nhom_B": {
    "ten": "Hiệu quả & Năng lực công việc", "ty_trong": 50, "diem_toi_da": 35,
    "tieu_chi": [
      {"stt": "B1", "ten": "", "mo_ta": "", "diem": null, "nhan_xet": ""},
      {"stt": "B2", "ten": "", "mo_ta": "", "diem": null, "nhan_xet": ""},
      {"stt": "B3", "ten": "", "mo_ta": "", "diem": null, "nhan_xet": ""},
      {"stt": "B4", "ten": "", "mo_ta": "", "diem": null, "nhan_xet": ""},
      {"stt": "B5", "ten": "", "mo_ta": "", "diem": null, "nhan_xet": ""},
      {"stt": "B6", "ten": "", "mo_ta": "", "diem": null, "nhan_xet": ""},
      {"stt": "B7", "ten": "", "mo_ta": "", "diem": null, "nhan_xet": ""}
    ],
    "tong_diem_tho": null, "diem_quy_doi": null, "nhan_xet_nhom": ""
  },
  "nhom_C": {
    "ten": "Tiềm năng & Mức độ phù hợp tổ chức", "ty_trong": 20, "diem_toi_da": 20,
    "tieu_chi": [
      {"stt": "C1", "ten": "", "mo_ta": "", "diem": null, "nhan_xet": ""},
      {"stt": "C2", "ten": "", "mo_ta": "", "diem": null, "nhan_xet": ""},
      {"stt": "C3", "ten": "", "mo_ta": "", "diem": null, "nhan_xet": ""},
      {"stt": "C4", "ten": "", "mo_ta": "", "diem": null, "nhan_xet": ""}
    ],
    "tong_diem_tho": null, "diem_quy_doi": null, "nhan_xet_nhom": ""
  },
  "tong_hop": {
    "bang_quy_doi": [
      {"nhom": "A", "ty_trong": 30, "diem_tho": null, "diem_toi_da": 25, "diem_quy_doi": null},
      {"nhom": "B", "ty_trong": 50, "diem_tho": null, "diem_toi_da": 35, "diem_quy_doi": null},
      {"nhom": "C", "ty_trong": 20, "diem_tho": null, "diem_toi_da": 20, "diem_quy_doi": null}
    ],
    "tong_diem_100": null, "xep_loai": ""
  },
  "bang_xep_loai": [
    {"loai": "A", "ten": "Xuất sắc", "diem_tu": 90, "diem_den": null, "mo_ta": ""},
    {"loai": "B", "ten": "Tốt",      "diem_tu": 80, "diem_den": 89,   "mo_ta": ""},
    {"loai": "C", "ten": "Khá",      "diem_tu": 71, "diem_den": 79,   "mo_ta": ""},
    {"loai": "D", "ten": "Cần cải thiện", "diem_tu": 60, "diem_den": 70, "mo_ta": ""},
    {"loai": "E", "ten": "Không đạt","diem_tu": null,"diem_den": 59,  "mo_ta": ""}
  ],
  "ket_qua_va_de_xuat": {
    "nhan_xet_hod": "", "nguyen_vong_nhan_vien": "",
    "de_xuat_bo_tri": "", "ly_do": "", "ke_hoach_cai_thien": ""
  },
  "xac_nhan": {"hod_ky": "", "phong_tong_vu_ky": "", "lanh_dao_ky": "", "ngay": ""},
  "ky_luat": [
    {"stt": 1, "noi_dung": "Số lần đi làm trễ",                                                                          "tu_bao_cao": null},
    {"stt": 2, "noi_dung": "Số lần về sớm",                                                                               "tu_bao_cao": null},
    {"stt": 3, "noi_dung": "Số ngày nghỉ không phép",                                                                     "tu_bao_cao": null},
    {"stt": 4, "noi_dung": "Số buổi sáng Thứ Bảy vắng mặt không phép",                                                   "tu_bao_cao": null},
    {"stt": 5, "noi_dung": "Số lần bị nhắc nhở vi phạm nội quy",                                                          "tu_bao_cao": null},
    {"stt": 6, "noi_dung": "Số bản giải trình / kiểm điểm / cam kết đã ký",                                               "tu_bao_cao": null},
    {"stt": 7, "noi_dung": "Số quyết định kỷ luật đã nhận (nếu có)",                                                      "tu_bao_cao": null}
  ],
  "dao_tao": [
    {"stt": 1, "noi_dung": "Tổng số chương trình đào tạo Công ty tổ chức trong kỳ",                                       "tu_bao_cao": null},
    {"stt": 2, "noi_dung": "Số chương trình đào tạo đã tham gia",                                                         "tu_bao_cao": null},
    {"stt": 3, "noi_dung": "Số chương đào tạo vắng mặt (có lý do chính đáng và được cấp thẩm quyền phê duyệt)",          "tu_bao_cao": null},
    {"stt": 4, "noi_dung": "Số chương trình đào tạo vắng mặt không lý do",                                                "tu_bao_cao": null},
    {"stt": 5, "noi_dung": "Số chương trình đào tạo nội bộ tham gia giảng dạy / chia sẻ",                                 "tu_bao_cao": null}
  ],
  "hoat_dong": [
    {"stt": 1, "noi_dung": "Tổng số sự kiện Công ty tổ chức trong kỳ",                                                    "tu_bao_cao": null},
    {"stt": 2, "noi_dung": "Số sự kiện đã tham gia",                                                                      "tu_bao_cao": null},
    {"stt": 3, "noi_dung": "Số sự kiện vắng mặt có lý do chính đáng và được cấp có thẩm quyền phê duyệt",                "tu_bao_cao": null},
    {"stt": 4, "noi_dung": "Số sự kiện vắng mặt không lý do",                                                             "tu_bao_cao": null},
    {"stt": 5, "noi_dung": "Số tuần không thực hiện like / share theo quy định",                                          "tu_bao_cao": null},
    {"stt": 6, "noi_dung": "Tổng số lượt like / share còn thiếu (nếu có)",                                                "tu_bao_cao": null}
  ],
  "bao_cao_ngay": [
    {"stt": 1, "noi_dung": "Tổng số báo cáo ngày phải thực hiện trong kỳ",                                                "tu_bao_cao": null},
    {"stt": 2, "noi_dung": "Số báo cáo ngày đã thực hiện đúng hạn",                                                       "tu_bao_cao": null},
    {"stt": 3, "noi_dung": "Số báo cáo ngày trễ hạn",                                                                     "tu_bao_cao": null},
    {"stt": 4, "noi_dung": "Số báo cáo ngày không thực hiện",                                                             "tu_bao_cao": null}
  ]
}

ĐỌC CHECKBOX — NGUYÊN TẮC QUAN TRỌNG:
Mỗi nhóm checkbox chỉ có ĐÚNG 1 ô được đánh dấu, còn lại là trống.
Ô được đánh dấu có thể là: ☑ hoặc ✓ hoặc ô bị tô đen/fill hoặc có dấu X bên trong.
Ô trống là □ hoặc ô vuông rỗng không có gì bên trong.
NẾU không thể xác định chắc chắn ô nào được tick → để trống "", KHÔNG đoán mò.

ĐỌC XẾP LOẠI TỔNG THỂ (tong_hop.xep_loai):
- Phiếu tu_danh_gia: dòng "Tự xếp loại tổng thể:" cuối trang 3
  → 5 ô inline: □ Xuất sắc  □ Tốt  □ Đạt yêu cầu  □ Cần cải thiện  □ Không đạt
  → Tìm ô duy nhất có dấu bên trong → trả tên đó, ví dụ: "Tốt"
  → Nếu không chắc → xep_loai = ""
- Phiếu hod: dòng "Xếp loại của nhân sự này:" trang 3
  → 5 ô: □ Loại A  □ Loại B  □ Loại C  □ Loại D  □ Loại E
  → Tìm ô được tick → trả "Loại B" (giữ nguyên text trên form)
  → Nếu không chắc → xep_loai = ""
- TUYỆT ĐỐI không tự suy xep_loai từ điểm số

ĐỌC NGUYỆN VỌNG / ĐỀ XUẤT BỐ TRÍ:
- nguyen_vong_nhan_vien (phiếu tu_danh_gia): bảng "Nguyện vọng bố trí công việc" mục VIII/IX
  → 3 dòng có checkbox ở cột đầu:
    "Tiếp tục làm việc tại phòng ban"
    "Mong muốn luân chuyển sang vị trí công việc khác"
    "Sẵn sàng theo sự điều phối của Công ty"
  → Trả text của dòng CÓ TICK, nếu không chắc → ""
- de_xuat_bo_tri (phiếu hod): bảng "Đề xuất bố trí nhân sự" mục VII
  → 3 dòng:
    "Tiếp tục làm việc tại phòng ban"
    "Luân chuyển sang vị trí công việc khác"
    "Đề xuất chấm dứt hợp tác"
  → Trả text của dòng CÓ TICK, nếu không chắc → ""

ĐỌC CÁC PHẦN II–V (chỉ có trong phiếu tu_danh_gia):
Phiếu NV tự đánh giá có 4 bảng dạng: STT | Nội dung | Kết quả tự báo cáo | Đã được HR xác nhận
→ Đọc cột "Kết quả tự báo cáo" (số nguyên) điền vào tu_bao_cao.
→ Cột "Đã được HR xác nhận" để trống (null) — HR sẽ điền sau.
- Phần II "Ý thức kỷ luật & Tuân thủ" → ky_luat (7 dòng)
- Phần III "Tham gia Đào tạo & Phát triển" → dao_tao (5 dòng)
- Phần IV "Tham gia Hoạt động tập thể & Quy định Truyền thông" → hoat_dong (6 dòng: 4 SK + 2 like/share)
- Phần V "Báo cáo ngày" → bao_cao_ngay (4 dòng)
Nếu phiếu hod không có các phần này → để mảng rỗng [].

ĐỌC BẢNG QUY ĐỔI ĐIỂM (trang 3 — quan trọng):
Cuối trang 3 có bảng tổng hợp dạng:
  | Nhóm | Điểm thô | Điểm tối đa | Tỷ trọng | Điểm quy đổi |
  | A    |    xx    |     25      |   30%    |     yy       |
  | B    |    xx    |     35      |   50%    |     yy       |
  | C    |    xx    |    15/20    |   20%    |     yy       |
  | TỔNG ĐIỂM /100  |                        |     zz       |
Đọc trực tiếp từ bảng này:
- nhom_A.tong_diem_tho, nhom_A.diem_quy_doi
- nhom_B.tong_diem_tho, nhom_B.diem_quy_doi
- nhom_C.tong_diem_tho, nhom_C.diem_quy_doi
- tong_hop.tong_diem_100 = ô "Tổng điểm /100"
KHÔNG tự tính — chỉ đọc số đã ghi trên form.

Lưu ý khác:
- "diem" tiêu chí là số nguyên 1-5, null nếu ô trống
- Phiếu tu_danh_gia: nhóm C chỉ C1-C3 (diem_toi_da=15), C4 diem=null
- Phiếu hod: nhóm C có C1-C4 (diem_toi_da=20)
- thoi_gian_lam_viec: ô "Thời gian làm việc" hoặc "Thâm niên" trang 1
- ky_danh_gia_tu / ky_danh_gia_den: ô "Kỳ đánh giá từ ... đến ..." trang 1
- ngay_danh_gia: ngày ký trang cuối
- Trả JSON thuần."""


AI_OVERVIEW_SYSTEM = (
    "Bạn là chuyên gia HR phân tích đánh giá nhân sự. "
    "Trả JSON thuần, không wrap code block, ngắn gọn, tiếng Việt."
)

AI_OVERVIEW_PROMPT = """Dữ liệu đánh giá nhân sự bên dưới. Phân tích ngắn gọn, thực tế.

Nhân viên: {ho_ten} | Chức danh: {chuc_danh}

NV tự đánh giá — điểm quy đổi: A={nv_A}, B={nv_B}, C={nv_C} | Tổng: {nv_tot} | Xếp loại: {nv_xl}
HOD đánh giá   — điểm quy đổi: A={hod_A}, B={hod_B}, C={hod_C} | Tổng: {hod_tot} | Xếp loại: {hod_xl}

Chi tiết nhóm (để phân tích lệch điểm):
NV:  {nv_criteria}
HOD: {hod_criteria}
(format: NhomX: sum tiêu chí / ghi tong_diem_tho → quy đổi)

So sánh tự khai (II–V) vs dữ liệu HR:
{hr_diffs_text}

Khung xếp loại: A ≥ 90đ (Xuất sắc) | B 80–89đ (Tốt) | C 71–79đ (Khá) | D 60–70đ (Cần cải thiện) | E < 60đ (Không đạt)

Lệch tổng NV vs HOD: {lech}
Đề xuất bố trí (HOD): {de_xuat}
Kế hoạch cải thiện: {ke_hoach}
Nhận xét HOD nhóm B: {rx_b}

Trả JSON:
{{
  "lech_diem": "...",
  "diem_vs_de_xuat": "...",
  "lot_khung": "...",
  "nhat_quan": "..."
}}

Giải thích:
- lech_diem: Nêu mức độ chênh lệch điểm số (tính theo %) giữa HOD và NV, và chỉ rõ ai đánh giá cao hơn. Tuyệt đối không nhắc đến các ngưỡng số (như 20% hay báo động).
- diem_vs_de_xuat: Điểm NV và HOD có khớp với đề xuất bố trí không? Có bất hợp lý nào không?
- lot_khung: Kiểm tra tính nhất quán giữa điểm tổng và ô xếp loại đã đánh dấu trong phiếu. NV cộng điểm ra {nv_tot}đ nhưng đánh vô ô "{nv_xl}" — đúng hay sai? HOD chấm {hod_tot}đ đánh vô ô "{hod_xl}" — đúng hay sai? Nêu rõ từng phía, nếu sai thì đúng ra phải đánh vào ô nào.
- nhat_quan: Nhận xét 1 câu văn xuôi về mức độ khớp giữa NV tự khai (phần II–V) và dữ liệu HR đã xác nhận. Xem mục "So sánh tự khai vs HR" ở trên. Nếu khớp hết → "Tự khai khớp tốt với dữ liệu HR." Nếu lệch 1–2 tiêu chí nhỏ → nêu ngắn. Nếu lệch nhiều (≥ 3) → "Lệch đáng kể (X tiêu chí), cần HR xác minh lại." Nếu không có HR → "Chưa có dữ liệu HR để đối chiếu." """
