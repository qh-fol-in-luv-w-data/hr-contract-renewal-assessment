# Copyright (c) 2025, antruong and contributors
# For license information, please see license.txt

"""AI prompt constants for phiếu {loai_danh_gia} scan."""


_MERGE_PROMPT = """Bạn nhận được 2 nguồn OCR của CÙNG 1 tài liệu scan:

SOURCE A – OCR API (chữ in tốt, cấu trúc bảng chính xác, nhưng chữ VIẾT TAY bị đọc sai → thành ký tự vô nghĩa):
---
{ocr_text}
---

SOURCE B – GPT-4o Vision (đọc được CẢ chữ in lẫn chữ viết tay, nhưng cấu trúc bảng có thể kém hơn):
---
{vision_text}
---

NHIỆM VỤ: Tạo ra 1 markdown DUYÊN NHẤT từ 2 nguồn trên.
QUY TẮC:
1. Dùng CẤU TRÚC BẢNG từ Source A (số cột, header, layout chính xác hơn)
2. Với nội dung CHỮ IN: ưu tiên Source A (chính xác hơn)
3. Với CÁC Ô bị garbled trong Source A (ký tự vô nghĩa, lẫn ký tự lạ, quá ngắn vô nghĩa như "& hyd", "Chi doy", "naN", ký tự Nhật/Hàn...): THAY bằng nội dung tương ứng từ Source B
4. Nếu Source B cũng không rõ → để nguyên ô Source A, thêm [?] cuối
5. Giữ tiếng Việt có dấu (Source B thường tốt hơn về dấu tiếng Việt)
6. Với ô HOD viết tay: thêm prefix [HT] (handwritten) trước nội dung đã merge
7. KHÔNG thêm bất kỳ giải thích hay comment nào — chỉ trả về markdown thuần

Trả về MARKDOWN THUẦN (không wrap trong code block)."""


_EXTRACT_PROMPT = """Bạn là AI chuyên đọc phiếu đánh giá {loai_danh_gia} CT Group. Trích xuất đầy đủ các trường sau. Trả về JSON thuần, không markdown. Nếu không tìm thấy → để "". KHÔNG bịa đặt.

{
  "ho_ten": "",
  "ma_nhan_su": "",
  "chuc_danh": "",
  "phong_ban": "",
  "cong_ty": "",
  "ngay_nhan_viec": "",
  "ngay_het_han": "",
  "thoi_gian_thu_viec": "",
  "loai_hop_dong": "",

  "ten_hod": "",
  "ma_hod": "",
  "chuc_danh_hod": "",
  "don_vi_hod": "",

  "nhan_xet_1_nv": "", "nhan_xet_1_hod": "",
  "nhan_xet_2_nv": "", "nhan_xet_2_hod": "",
  "nhan_xet_3_nv": "", "nhan_xet_3_hod": "",
  "nhan_xet_4_nv": "", "nhan_xet_4_hod": "",
  "nhan_xet_5_nv": "", "nhan_xet_5_hod": "",

  "kpi_tuan_1_ty_le": "", "kpi_tuan_2_ty_le": "", "kpi_tuan_3_ty_le": "", "kpi_tuan_4_ty_le": "",
  "kpi_tuan_5_ty_le": "", "kpi_tuan_6_ty_le": "", "kpi_tuan_7_ty_le": "", "kpi_tuan_8_ty_le": "",
  "diem_tbc_kpi_nv": "", "diem_tbc_kpi_hod": "",

  "cong_viec_duoc_giao": "",
  "ty_le_hoan_thanh_16": "",
  "nhiem_vu_1_noi_dung": "", "nhiem_vu_1_ket_qua": "", "nhiem_vu_1_ty_le": "", "nhiem_vu_1_hod": "",
  "nhiem_vu_2_noi_dung": "", "nhiem_vu_2_ket_qua": "", "nhiem_vu_2_ty_le": "", "nhiem_vu_2_hod": "",
  "nhiem_vu_3_noi_dung": "", "nhiem_vu_3_ket_qua": "", "nhiem_vu_3_ty_le": "", "nhiem_vu_3_hod": "",
  "nhiem_vu_4_noi_dung": "", "nhiem_vu_4_ket_qua": "", "nhiem_vu_4_ty_le": "", "nhiem_vu_4_hod": "",

  "san_pham_1": "", "so_luong_file_1": "", "link_dinh_kem_1": "", "vi_pham_upload_1": "", "kpi_sp_tuan_1": "",
  "san_pham_2": "", "so_luong_file_2": "", "link_dinh_kem_2": "", "vi_pham_upload_2": "", "kpi_sp_tuan_2": "",
  "san_pham_3": "", "so_luong_file_3": "", "link_dinh_kem_3": "", "vi_pham_upload_3": "", "kpi_sp_tuan_3": "",
  "san_pham_4": "", "so_luong_file_4": "", "link_dinh_kem_4": "", "vi_pham_upload_4": "", "kpi_sp_tuan_4": "",
  "san_pham_5": "", "so_luong_file_5": "", "link_dinh_kem_5": "", "vi_pham_upload_5": "", "kpi_sp_tuan_5": "",
  "san_pham_6": "", "so_luong_file_6": "", "link_dinh_kem_6": "", "vi_pham_upload_6": "", "kpi_sp_tuan_6": "",
  "san_pham_7": "", "so_luong_file_7": "", "link_dinh_kem_7": "", "vi_pham_upload_7": "", "kpi_sp_tuan_7": "",
  "san_pham_8": "", "so_luong_file_8": "", "link_dinh_kem_8": "", "vi_pham_upload_8": "", "kpi_sp_tuan_8": "",

  "hoi_nhap_1_nv": "", "hoi_nhap_1_hod": "",
  "hoi_nhap_2_nv": "", "hoi_nhap_2_hod": "",
  "hoi_nhap_3_nv": "", "hoi_nhap_3_hod": "",
  "hoi_nhap_4_nv": "", "hoi_nhap_4_hod": "",
  "hoi_nhap_5_nv": "", "hoi_nhap_5_hod": "",
  "hoi_nhap_6_nv": "", "hoi_nhap_6_hod": "",
  "hoi_nhap_7_nv": "", "hoi_nhap_7_hod": "",
  "hoi_nhap_7_1_nv": "", "hoi_nhap_7_1_hod": "",
  "hoi_nhap_7_2_nv": "", "hoi_nhap_7_2_hod": "",
  "hoi_nhap_7_3_nv": "", "hoi_nhap_7_3_hod": "",
  "hoi_nhap_7_4_nv": "", "hoi_nhap_7_4_hod": "",
  "hoi_nhap_7_5_nv": "", "hoi_nhap_7_5_hod": "",
  "hoi_nhap_8_nv": "", "hoi_nhap_8_hod": "",
  "hoi_nhap_9_nv": "", "hoi_nhap_9_hod": "",

  "ket_luan": "",
  "de_xuat_ky_hd": "",
  "de_xuat_tang_thu_nhap": "",
  "de_nghi_phoi_hop": "",
  "y_kien_hod": "",
  "y_kien_rtd": "",
  "ngay_ky": "",
  "ten_hod_ky": ""
}

GHI CHÚ QUAN TRỌNG:
- kpi_tuan_N_ty_le: chỉ điền những tuần CÓ trong tài liệu — không bịa tuần trống. Ví dụ: hợp đồng 4 tuần thì chỉ có kpi_tuan_1..4_ty_le, còn lại để "".
- nhiem_vu_X_ty_le: lấy đúng từ cột % KẾ BÊN dòng nhiệm vụ X trong bảng 1.6, KHÔNG lấy từ dòng/cột khác
- kpi_sp_tuan_X: % KPI cột kế bên hàng 2.X sản phẩm nghiệm thu tuần X
- Tất cả _nv / _hod: lấy NGUYÊN VĂN, không tóm tắt
- Ô trống → ""

VĂN BẢN TÀI LIỆU:
"""


_ANALYZE_PROMPT = """Bạn là 2AS – AI Đánh Giá Nhân Sự CT Group.
Phân tích hồ sơ đánh giá {loai_danh_gia} và đưa ra đề xuất xử lý.

DỮ LIỆU NHÂN VIÊN (đã xác nhận):
{confirmed_fields_json}

Ngày hiện tại: {today}

══ XÁC ĐỊNH SỐ TUẦN THỰC TẾN ══
- Đếm số tuần thực tế dựa vào các field kpi_tuan_N_ty_le có giá trị (không rỗng)
- Ví dụ: nếu kpi_tuan_1..4_ty_le có giá trị, kpi_tuan_5..8_ty_le rỗng → hợp đồng 4 tuần
- CHỈ đánh giá những tuần CÓ trong phiếu. TUYỆT ĐỐI KHÔNG cảnh báo tuần 5–8 nếu hợp đồng chỉ có 4 tuần
- Tương tự với nhiem_vu_X: chỉ đánh giá những nhiệm vụ X có nhiem_vu_X_noi_dung không rỗng
- Tương tự với san_pham_X: chỉ đánh giá những tuần có san_pham_X không rỗng

══ PHÂN TÍCH THEO 6 TIÊU CHÍ ══
1. KẾT QUẢ CÔNG VIỆC – Có số liệu/kết quả cụ thể? Đạt mục tiêu? (chỉ tính các tuần thực tế có trong phiếu)
2. THÁI ĐỘ / KỶ LUẬT – Vi phạm nội quy? Ý thức chuyên cần?
3. NĂNG LỰC CHUYÊN MÔN – Thể hiện nền tảng & tiềm năng phát triển? ({loai_danh_gia} → không đòi thành thạo ngay; đánh giá thái độ học, tốc độ tiến bộ, chủ động giải quyết vấn đề)
4. MỨC ĐỘ PHÙ HỢP – Phù hợp vị trí, văn hóa, team?
5. NHẬN XÉT QUẢN LÝ – Đủ rõ ràng, có căn cứ?
6. TÌNH TRẠNG HỐ SƠ & THỚI HẠN – Đủ thông tin? Đúng hạn?

══ MỨC ĐỀ XUẤT ══
- ĐỒNG Ý KÝ HĐLĐ: Đủ căn cứ, không cảnh báo nghiêm trọng
- CẦN BỔ SUNG: Thiếu thông tin, cần làm rõ
- GIA HẠN THỮc VIỆC: Chưa đủ điều kiện, cần thêm thời gian
- KHÔNG ĐỀ XUẤT: Vi phạm nghiêm trọng hoặc không đạt

CẢNH BÁO BẮT BUỘC:
- Ngày hết hạn < hôm nay → TRỄ HẠN
- Ngày hết hạn ≤ 7 ngày → SẮP HẾT HẠN
- Thiếu y_kien_hod → cảnh báo
- Thiếu ket_luan → cảnh báo
- KHÔNG cảnh báo các tuần KPI/nhiệm vụ/sản phẩm trống nếu chúsng nằm ngoài phạm vi hợp đồng thực tế

Trả về JSON thuần:
{
  "so_tuan_thuc_te": 4,
  "de_xuat": "ĐỒNG Ý KÝ HĐLĐ | CẦN BỔ SUNG | GIA HẠN THỮc VIỆC | KHÔNG ĐỀ XUẤT",
  "mau_de_xuat": "green | amber | amber | red",
  "tong_quan": "Nhận xét tổng quan 2-3 câu, nêu rõ hợp đồng có bao nhiêu tuần (lưu ý dùng từ '{loai_danh_gia}' hoặc 'học việc' phù hợp với tiêu đề Phiếu)",
  "phan_tich": [
    {"tieu_chi": "KẾT QUẢ CÔNG VIỆC", "danh_gia": "Đạt | Chưa đạt | Không đủ dữ liệu", "nhan_xet": "..."},
    {"tieu_chi": "THÁI ĐỘ / KỶ LUẬT", "danh_gia": "...", "nhan_xet": "..."},
    {"tieu_chi": "NĂNG LỰC CHUYÊN MÔN", "danh_gia": "...", "nhan_xet": "..."},
    {"tieu_chi": "MỨC ĐỘ PHÙ HỢP", "danh_gia": "...", "nhan_xet": "..."},
    {"tieu_chi": "NHẬN XÉT QUẢN LÝ", "danh_gia": "...", "nhan_xet": "..."},
    {"tieu_chi": "TÌNH TRẠNG HỐ SƠ", "danh_gia": "...", "nhan_xet": "..."}
  ],
  "canh_bao": ["Cảnh báo 1 nếu có"],
  "uu_diem": ["Điểm tốt 1"],
  "viec_can_lam": [
    {"thu_tu": 1, "noi_dung": "Việc cần làm CỤ THỂ #1 (BẮT BUỘC – luôn đề xuất ít nhất 3 việc dù đề xuất là ĐỒNG Ý hay không)", "uu_tien": "cao"},
    {"thu_tu": 2, "noi_dung": "Việc cần làm CỤ THỂ #2", "uu_tien": "trung"},
    {"thu_tu": 3, "noi_dung": "Việc cần làm CỤ THỂ #3", "uu_tien": "thap"}
  ],
  "alert_deadline": false,
  "so_ngay_con_lai": null,
  "danh_gia_quan_ly": {
    "de_xuat_quan_ly": "Đề xuất của quản lý (BẮT BUỘC tổng hợp từ các trường 'ket_luan', 'de_xuat_ky_hd', 'de_xuat_tang_thu_nhap', 'de_nghi_phoi_hop', 'y_kien_hod', 'y_kien_rtd' trong dữ liệu nhân viên. Đọc nguyên văn nội dung chính).",
    "hop_ly": true,
    "muc_do_dong_y": "✅ Đồng ý hoàn toàn | ⚠️ Cần xem xét | ❌ Không đồng ý",
    "ly_do_chinh": "Lý do chính yếu",
    "phan_tich_chi_tiet": "Phân tích vì sao hợp lý hoặc không hợp lý (nếu có)",
    "nhan_xet": "Nhận xét tổng quan của AI về đề xuất này",
    "khuyen_nghi_xu_ly": "Khuyến nghị xử lý tiếp theo"
  }
}
"""


VISION_JSON_PROMPT = """Bạn đang xem ảnh PHIẾU ĐÁNH GIÁ HOÀN THÀNH {loai_danh_gia_up} (CTG-GO-NLCD-QT16-BM01) của CT Group.
Đọc TOÀN BỘ nội dung — kể cả chữ nhỏ, chữ ở lề, góc trang. Điền vào JSON bên dưới.

=== QUY TẮC BẮT BUỘC ===
1. Chữ in → đọc nguyên văn
2. Chữ viết tay → đọc nguyên văn (KHÔNG thêm "[VT]" hay ghi chú)
3. Ô trống → ""
4. URL / tên file → giữ NGUYÊN VĂN đầy đủ
5. KHÔNG tóm tắt, KHÔNG rút gọn — lấy NGUYÊN VĂN toàn bộ
6. Nếu câu trả lời trải sang trang sau thì đọc tiếp → ghi tất cả vào đây

=== CẤU TRÚC PHIẾU ===

A. THÔNG TIN CHUNG (bảng trang 1):
  Cột CBNV: ho_ten, ma_nhan_su, chuc_danh, phong_ban, cong_ty, ngay_nhan_viec, ngay_het_han
  Cột HOD (viết tay): ten_hod, ma_hod, chuc_danh_hod, don_vi_hod


B. PHẦN I – NHẬN XÉT CHUNG (5 câu, 2 cột NV + HOD):
  Câu 1 "Những điểm làm tốt": nhan_xet_1_nv / nhan_xet_1_hod (viết tay)
  Câu 2 "Kỹ năng đáp ứng":    nhan_xet_2_nv / nhan_xet_2_hod
  Câu 3 "Hoạt động tham gia": nhan_xet_3_nv / nhan_xet_3_hod
  Câu 4 "Điểm cần cải thiện": nhan_xet_4_nv / nhan_xet_4_hod
  Câu 5 "Kỹ năng cần nâng cao": nhan_xet_5_nv / nhan_xet_5_hod

C. PHẦN II – KPI & SẢN PHẨM:
  1.1–1.8: kpi_tuan_1_ty_le .. kpi_tuan_8_ty_le (số %, cột NV) — đọc TẤT CẢ tuần có trong phiếu
  1.5 TBC: diem_tbc_kpi_nv (NV điền) / diem_tbc_kpi_hod (HOD viết tay)

  1.6 CÔNG VIỆC ĐƯỢC GIAO (trải nhiều trang, đọc TOÀN BỘ):
      cong_viec_duoc_giao: toàn bộ nội dung — nhiệm vụ 1-4 + kết quả thực tế từng nhiệm vụ (nguyên văn, không tóm tắt)
      ty_le_hoan_thanh_16: % hoàn thành chung của bảng 1.6 nếu có
      ⚠️ THÊM per-task: Mỗi nhiệm vụ trong bảng 1.6 phải được đọc vào:
        nhiem_vu_1_noi_dung / nhiem_vu_1_ket_qua / nhiem_vu_1_ty_le (% hoàn thành) / nhiem_vu_1_hod (HOD nhận xét)
        nhiem_vu_2_noi_dung / nhiem_vu_2_ket_qua / nhiem_vu_2_ty_le / nhiem_vu_2_hod
        nhiem_vu_3_noi_dung / nhiem_vu_3_ket_qua / nhiem_vu_3_ty_le / nhiem_vu_3_hod
        nhiem_vu_4_noi_dung / nhiem_vu_4_ket_qua / nhiem_vu_4_ty_le / nhiem_vu_4_hod

  2.1–2.8 SẢN PHẨM NGHIỆM THU mỗi tuần (có bao nhiêu tuần thì đọc bấy nhiêu, tối đa 8):
    san_pham_X: tên sản phẩm (danh sách, NGUYÊN VĂN đầy đủ)
    so_luong_file_X: số file
    link_dinh_kem_X: danh sách tên file đính kèm (mỗi file 1 dòng, giữ nguyên)
    vi_pham_upload_X: số lần + ngày vi phạm
    kpi_sp_tuan_X: % KPI tuần đó


D. PHẦN III – HỘI NHẬP (9 câu, trải trang 9-19):
  ⚠️ Các câu trả lời RẤT DÀI, trải nhiều trang — đọc NGUYÊN VĂN không tóm tắt!
  Câu 1 "Sứ mệnh Tập đoàn":      hoi_nhap_1_nv / hoi_nhap_1_hod
  Câu 2 "Sứ mệnh bản thân":      hoi_nhap_2_nv / hoi_nhap_2_hod
  Câu 3 "Tầm nhìn Tập đoàn":     hoi_nhap_3_nv / hoi_nhap_3_hod
  Câu 4 "Tầm nhìn bản thân":     hoi_nhap_4_nv / hoi_nhap_4_hod
  Câu 5 "Văn hóa cốt lõi":       hoi_nhap_5_nv / hoi_nhap_5_hod
  Câu 6 "Giá trị cốt lõi":       hoi_nhap_6_nv / hoi_nhap_6_hod
  Câu 7 "Phù hợp văn hóa làm việc" (gồm 7.1-7.5):
    hoi_nhap_7_nv / hoi_nhap_7_hod (phần tổng)
    hoi_nhap_7_1_nv / hoi_nhap_7_1_hod: Văn hóa Hiệu quả
    hoi_nhap_7_2_nv / hoi_nhap_7_2_hod: Văn hóa Tốc độ
    hoi_nhap_7_3_nv / hoi_nhap_7_3_hod: Văn hóa Kỷ luật
    hoi_nhap_7_4_nv / hoi_nhap_7_4_hod: Văn hóa Học tập (số giờ tự học, đào tạo, đóng góp)
    hoi_nhap_7_5_nv / hoi_nhap_7_5_hod: Văn hóa Chính trực
  Câu 8 "Văn hóa kinh doanh":    hoi_nhap_8_nv / hoi_nhap_8_hod
  Câu 9 "Đóng góp khác":         hoi_nhap_9_nv / hoi_nhap_9_hod

E. KẾT LUẬN (trang cuối):
  Tick chọn 1 trong 4 → ket_luan:
    "Đạt yêu cầu" | "Không đạt - không khắc phục" | "Không đạt - có thể khắc phục" | "Không đạt tại đơn vị này"
  HOD đề xuất ký HĐ: de_xuat_ky_hd
  HOD tăng thu nhập: de_xuat_tang_thu_nhap
  Đề nghị phối hợp: de_nghi_phoi_hop
  Ý kiến HOD: y_kien_hod / RTD: y_kien_rtd / Ngày ký: ngay_ky / Tên HOD ký: ten_hod_ky

TRẢ VỀ JSON THUẦN (KHÔNG markdown):
{
  "ho_ten": "",
  "ma_nhan_su": "",
  "chuc_danh": "",
  "phong_ban": "",
  "cong_ty": "",
  "ngay_nhan_viec": "",
  "ngay_het_han": "",
  "thoi_gian_thu_viec": "",
  "loai_hop_dong": "",
  "ten_hod": "",
  "ma_hod": "",
  "chuc_danh_hod": "",
  "don_vi_hod": "",
  "nhan_xet_1_nv": "",
  "nhan_xet_1_hod": "",
  "nhan_xet_2_nv": "",
  "nhan_xet_2_hod": "",
  "nhan_xet_3_nv": "",
  "nhan_xet_3_hod": "",
  "nhan_xet_4_nv": "",
  "nhan_xet_4_hod": "",
  "nhan_xet_5_nv": "",
  "nhan_xet_5_hod": "",
  "kpi_tuan_1_ty_le": "",
  "kpi_tuan_2_ty_le": "",
  "kpi_tuan_3_ty_le": "",
  "kpi_tuan_4_ty_le": "",
  "kpi_tuan_5_ty_le": "",
  "kpi_tuan_6_ty_le": "",
  "kpi_tuan_7_ty_le": "",
  "kpi_tuan_8_ty_le": "",
  "diem_tbc_kpi_nv": "",
  "diem_tbc_kpi_hod": "",
  "cong_viec_duoc_giao": "",
  "ty_le_hoan_thanh_16": "",
  "nhiem_vu_1_noi_dung": "", "nhiem_vu_1_ket_qua": "", "nhiem_vu_1_ty_le": "", "nhiem_vu_1_hod": "",
  "nhiem_vu_2_noi_dung": "", "nhiem_vu_2_ket_qua": "", "nhiem_vu_2_ty_le": "", "nhiem_vu_2_hod": "",
  "nhiem_vu_3_noi_dung": "", "nhiem_vu_3_ket_qua": "", "nhiem_vu_3_ty_le": "", "nhiem_vu_3_hod": "",
  "nhiem_vu_4_noi_dung": "", "nhiem_vu_4_ket_qua": "", "nhiem_vu_4_ty_le": "", "nhiem_vu_4_hod": "",
  "san_pham_1": "", "so_luong_file_1": "", "link_dinh_kem_1": "", "vi_pham_upload_1": "", "kpi_sp_tuan_1": "",
  "san_pham_2": "", "so_luong_file_2": "", "link_dinh_kem_2": "", "vi_pham_upload_2": "", "kpi_sp_tuan_2": "",
  "san_pham_3": "", "so_luong_file_3": "", "link_dinh_kem_3": "", "vi_pham_upload_3": "", "kpi_sp_tuan_3": "",
  "san_pham_4": "", "so_luong_file_4": "", "link_dinh_kem_4": "", "vi_pham_upload_4": "", "kpi_sp_tuan_4": "",
  "san_pham_5": "", "so_luong_file_5": "", "link_dinh_kem_5": "", "vi_pham_upload_5": "", "kpi_sp_tuan_5": "",
  "san_pham_6": "", "so_luong_file_6": "", "link_dinh_kem_6": "", "vi_pham_upload_6": "", "kpi_sp_tuan_6": "",
  "san_pham_7": "", "so_luong_file_7": "", "link_dinh_kem_7": "", "vi_pham_upload_7": "", "kpi_sp_tuan_7": "",
  "san_pham_8": "", "so_luong_file_8": "", "link_dinh_kem_8": "", "vi_pham_upload_8": "", "kpi_sp_tuan_8": "",
  "hoi_nhap_1_nv": "",
  "hoi_nhap_1_hod": "",
  "hoi_nhap_2_nv": "",
  "hoi_nhap_2_hod": "",
  "hoi_nhap_3_nv": "",
  "hoi_nhap_3_hod": "",
  "hoi_nhap_4_nv": "",
  "hoi_nhap_4_hod": "",
  "hoi_nhap_5_nv": "",
  "hoi_nhap_5_hod": "",
  "hoi_nhap_6_nv": "",
  "hoi_nhap_6_hod": "",
  "hoi_nhap_7_nv": "",
  "hoi_nhap_7_hod": "",
  "hoi_nhap_7_1_nv": "", "hoi_nhap_7_1_hod": "",
  "hoi_nhap_7_2_nv": "", "hoi_nhap_7_2_hod": "",
  "hoi_nhap_7_3_nv": "", "hoi_nhap_7_3_hod": "",
  "hoi_nhap_7_4_nv": "", "hoi_nhap_7_4_hod": "",
  "hoi_nhap_7_5_nv": "", "hoi_nhap_7_5_hod": "",
  "hoi_nhap_8_nv": "",
  "hoi_nhap_8_hod": "",
  "hoi_nhap_9_nv": "",
  "hoi_nhap_9_hod": "",
  "ket_luan": "",
  "de_xuat_ky_hd": "",
  "de_xuat_tang_thu_nhap": "",
  "de_nghi_phoi_hop": "",
  "y_kien_hod": "",
  "y_kien_rtd": "",
  "ngay_ky": "",
  "ten_hod_ky": ""
}"""


HOI_NHAP_PROMPT = """Bạn đang xem các trang cuối phần II và/hoặc PHẦN III – MỨC ĐỘ HỘI NHẬP của PHIẾU ĐÁNH GIÁ {loai_danh_gia_up} CT Group.

NHIỆM VỤ: Đọc TOÀN BỘ và điền NGUYÊN VĂN không tóm tắt vào đúng field.
Các câu trả lời RẤT DÀI và TRẢI NHIỀU TRANG — ghi tất cả vào đây.

CÁC CÂU HỎI VÀ FIELD TƯƠNG ỨNG:
  Câu 1 → hoi_nhap_1_nv: "Ứng viên hiểu gì về Sứ mệnh của Tập đoàn?"
  Câu 2 → hoi_nhap_2_nv: "Sứ mệnh của bản thân ứng viên là gì?"
  Câu 3 → hoi_nhap_3_nv: "Ứng viên hiểu gì về Tầm nhìn của Tập đoàn? (2025 & 2052)"
  Câu 4 → hoi_nhap_4_nv: "Tầm nhìn bản thân ứng viên là gì?"
  Câu 5 → hoi_nhap_5_nv: "Ứng viên hiểu gì về Văn hóa cốt lõi của Tập đoàn?"
  Câu 6 → hoi_nhap_6_nv: "Giá trị cốt lõi bản thân ứng viên là gì?"
  Câu 7 → hoi_nhap_7_nv: "Sự phù hợp với Văn hóa làm việc của Tập đoàn?"
    + hoi_nhap_7_1_nv: Văn hóa Hiệu quả (7.1)
    + hoi_nhap_7_2_nv: Văn hóa Tốc độ (7.2)
    + hoi_nhap_7_3_nv: Văn hóa Kỷ luật (7.3)
    + hoi_nhap_7_4_nv: Văn hóa Học tập (7.4) — số giờ, đóng góp
    + hoi_nhap_7_5_nv: Văn hóa Chính trực (7.5)
  Câu 8 → hoi_nhap_8_nv: "Ứng viên hiểu gì về Văn hóa kinh doanh của Tập đoàn?"
  Câu 9 → hoi_nhap_9_nv: "Các đóng góp khác trong thời gian hội nhập?"

NẾU GẶP TRANG CHUYỂN TIẾP (vừa có sản phẩm cuối vừa có câu hỏi đầu tiên):
  → Đọc cả sản phẩm (san_pham_X, link_dinh_kem_X) VÀ câu hỏi hội nhập đầu tiên.

NẾU TRANG NÀY CHỈ CÓ PHẦN TIẾP THEO của câu trả lời (không có số thứ tự câu hỏi mới):
  → Nhìn vào nội dung để xác định thuộc câu hỏi nào và điền vào đúng field đó.
  → Ví dụ: nếu thấy tiếp tục nói về "sứ mệnh CT Group" thì là hoi_nhap_1_nv.

HOD viết tay nhận xét → hoi_nhap_X_hod tương ứng.
Phần kết luận cuối cùng → ket_luan, de_xuat_ky_hd, ten_hod_ky, ngay_ky.

TRẢ VỀ JSON THUẦN:
{
  "hoi_nhap_1_nv": "", "hoi_nhap_1_hod": "",
  "hoi_nhap_2_nv": "", "hoi_nhap_2_hod": "",
  "hoi_nhap_3_nv": "", "hoi_nhap_3_hod": "",
  "hoi_nhap_4_nv": "", "hoi_nhap_4_hod": "",
  "hoi_nhap_5_nv": "", "hoi_nhap_5_hod": "",
  "hoi_nhap_6_nv": "", "hoi_nhap_6_hod": "",
  "hoi_nhap_7_nv": "", "hoi_nhap_7_hod": "",
  "hoi_nhap_7_1_nv": "", "hoi_nhap_7_1_hod": "",
  "hoi_nhap_7_2_nv": "", "hoi_nhap_7_2_hod": "",
  "hoi_nhap_7_3_nv": "", "hoi_nhap_7_3_hod": "",
  "hoi_nhap_7_4_nv": "", "hoi_nhap_7_4_hod": "",
  "hoi_nhap_7_5_nv": "", "hoi_nhap_7_5_hod": "",
  "hoi_nhap_8_nv": "", "hoi_nhap_8_hod": "",
  "hoi_nhap_9_nv": "", "hoi_nhap_9_hod": "",
  "ket_luan": "", "de_xuat_ky_hd": "", "de_xuat_tang_thu_nhap": "",
  "de_nghi_phoi_hop": "", "y_kien_hod": "", "y_kien_rtd": "",
  "ngay_ky": "", "ten_hod_ky": "",
  "san_pham_1": "", "so_luong_file_1": "", "link_dinh_kem_1": "", "vi_pham_upload_1": "", "kpi_sp_tuan_1": "",
  "san_pham_2": "", "so_luong_file_2": "", "link_dinh_kem_2": "", "vi_pham_upload_2": "", "kpi_sp_tuan_2": "",
  "san_pham_3": "", "so_luong_file_3": "", "link_dinh_kem_3": "", "vi_pham_upload_3": "", "kpi_sp_tuan_3": "",
  "san_pham_4": "", "so_luong_file_4": "", "link_dinh_kem_4": "", "vi_pham_upload_4": "", "kpi_sp_tuan_4": "",
  "san_pham_5": "", "so_luong_file_5": "", "link_dinh_kem_5": "", "vi_pham_upload_5": "", "kpi_sp_tuan_5": "",
  "san_pham_6": "", "so_luong_file_6": "", "link_dinh_kem_6": "", "vi_pham_upload_6": "", "kpi_sp_tuan_6": "",
  "san_pham_7": "", "so_luong_file_7": "", "link_dinh_kem_7": "", "vi_pham_upload_7": "", "kpi_sp_tuan_7": "",
  "san_pham_8": "", "so_luong_file_8": "", "link_dinh_kem_8": "", "vi_pham_upload_8": "", "kpi_sp_tuan_8": ""
}"""


KPI_PROMPT = """Bạn đang xem trang PHẦN II – KPI của PHIẾU ĐÁNH GIÁ {loai_danh_gia_up} CT Group.

NHIỆM VỤ CHÍNH: Đọc chính xác % và nội dung nhiệm vụ.

QUY TẮC:
1. NGUYÊN VĂN — không tóm tắt, không bỏ sót
2. Ô trống → ""
3. % phải đọc từ CỘT % KẾ BÊN TƯƠNG ỨNG của từng dòng

CÁC MỤC CẦN ĐỌC:

[KPI TỪNG TUẦN] — hàng đánh số 1.1 / 1.2 / ... tương ứng Tuần thứ 1, 2, ...:
  - Mỗi hàng có CỘT % riêng kế bên → đọc ĐÚNG CỘT ĐÓ
  - kpi_tuan_1_ty_le → % cột kế bên hàng tuần 1 (1.1)
  - kpi_tuan_2_ty_le → % cột kế bên hàng tuần 2 (1.2)
  - tương tự đến kpi_tuan_8_ty_le (tối đa 8 tuần)
  - Chỉ điền những tuần CÓ trong phiếu, để trống các tuần không có

[ĐIỂM TBC] — hàng "Điểm trung bình" hoặc "Điểm TBC" (ký hiệu 1.5/1.9/1.X tuỳ phiếu):
  - diem_tbc_kpi_nv → % TBC nhân viên ghi
  - diem_tbc_kpi_hod → HOD viết tay vào ô TBC

[CÔNG VIỆC ĐƯỢC GIAO] — có thể ký hiệu là 1.6 HOẶC 1.10 tuỳ phiếu:
  Bảng liệt kê TỪNG NHIỆM VỤ + kết quả + % hoàn thành.

  LAYOUT HAI CỘT PHỔ BIẾN:
    Cột trái: Nội dung nhiệm vụ (dạng "+ Nhiệm vụ X: ...")
    Cột phải: Kết quả thực tế: XX% (ví dụ "Kết quả thực tế: 90%")
  HOẶC bảng 4 cột: Nhiệm vụ | Kết quả thực tế | % hoàn thành | HOD nhận xét

  ĐỌC TUẦN TỰ từng nhiệm vụ, map vào:
    nhiem_vu_1_noi_dung = nội dung nhiệm vụ 1 (NGUYÊN VĂN đầy đủ)
    nhiem_vu_1_ket_qua  = kết quả thực tế NV1 (nếu có cột/phần riêng)
    nhiem_vu_1_ty_le    = % NV1 — tìm "Kết quả thực tế: X%" hoặc cột % kề dòng đó
    nhiem_vu_1_hod      = HOD nhận xét NV1
    (tương tự nhiem_vu_2 → nhiem_vu_8, điền bao nhiêu NV có bấy nhiêu)

  cong_viec_duoc_giao = toàn bộ nội dung phần 1.6/1.10 (nguyên văn, gộp hết)
  ty_le_hoan_thanh_16 = % TỔNG hoàn thành chung (nếu có dòng tổng)

  NGUYÊN TẮC:
  - nhiem_vu_X_ty_le: lấy % ở cột phải cùng dòng/khối NV X
    VD: dòng NV1 có "Kết quả thực tế: 90%" ở cột phải → nhiem_vu_1_ty_le = "90%"
  - KHÔNG để trống nếu thấy % ở cột phải cùng dòng NV đó
  - Đọc NGUYÊN VĂN đầy đủ, không tóm tắt, không bỏ NV nào

[SẢN PHẨM NGHIỆM THU TUẦN] — bảng đánh số 2.1 / 2.2 / ... (nếu có trong trang):
  Bảng 2.X thường có các cột: STT | Sản phẩm / Nhiệm vụ | Số lượng file | Link đính kèm | Vi phạm | % KPI

  QUY TẮC ĐỌC TỪNG CỘT (theo đúng cột, không lẫn lộn):
  - san_pham_X   = nội dung ô "Sản phẩm" hoặc "Sản phẩm:" tuần X (NGUYÊN VĂN toàn bộ)
  - nhiem_vu_tuan_X = nội dung "Nhiệm vụ đặt ra:" tuần X (NGUYÊN VĂN, "" nếu không có)
  - so_luong_file_X = số ở CỘT "Số lượng file" tuần X (chỉ là số, VD: "3", "0")
  - link_dinh_kem_X = nội dung ô CỘT "Link đính kèm" tuần X:
      * Nếu có URL (http://... / https://...) → copy NGUYÊN VĂN toàn bộ URL, mỗi link 1 dòng
      * Nếu có tên file → copy NGUYÊN VĂN đầy đủ
      * Nếu ô trống hoặc chỉ có "-" → ""
      * ⚠️ KHÔNG nhầm với cột "Số lượng file" — link KHÔNG phải số "0", "1", "2"...
  - vi_pham_upload_X = số lần vi phạm + ngày cụ thể tuần X
  - kpi_sp_tuan_X   = % ở CỘT % KPI kế bên hàng 2.X (VD: "90%")

  Nếu trang không có bảng 2.X → để trống san_pham_X, link_dinh_kem_X, nhiem_vu_tuan_X.
  ⚠️ TUYỆT ĐỐI: link ≠ số nguyên. Nếu chỉ thấy số như "0" ở cột link → để "" (ô trống, không phải link).

TRẢ VỀ JSON THUẦN:
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
  "nhiem_vu_8_noi_dung":"","nhiem_vu_8_ket_qua":"","nhiem_vu_8_ty_le":"","nhiem_vu_8_hod":"",
  "san_pham_1":"","nhiem_vu_tuan_1":"","so_luong_file_1":"","link_dinh_kem_1":"","vi_pham_upload_1":"","kpi_sp_tuan_1":"",
  "san_pham_2":"","nhiem_vu_tuan_2":"","so_luong_file_2":"","link_dinh_kem_2":"","vi_pham_upload_2":"","kpi_sp_tuan_2":"",
  "san_pham_3":"","nhiem_vu_tuan_3":"","so_luong_file_3":"","link_dinh_kem_3":"","vi_pham_upload_3":"","kpi_sp_tuan_3":"",
  "san_pham_4":"","nhiem_vu_tuan_4":"","so_luong_file_4":"","link_dinh_kem_4":"","vi_pham_upload_4":"","kpi_sp_tuan_4":"",
  "san_pham_5":"","nhiem_vu_tuan_5":"","so_luong_file_5":"","link_dinh_kem_5":"","vi_pham_upload_5":"","kpi_sp_tuan_5":"",
  "san_pham_6":"","nhiem_vu_tuan_6":"","so_luong_file_6":"","link_dinh_kem_6":"","vi_pham_upload_6":"","kpi_sp_tuan_6":"",
  "san_pham_7":"","nhiem_vu_tuan_7":"","so_luong_file_7":"","link_dinh_kem_7":"","vi_pham_upload_7":"","kpi_sp_tuan_7":"",
  "san_pham_8":"","nhiem_vu_tuan_8":"","so_luong_file_8":"","link_dinh_kem_8":"","vi_pham_upload_8":"","kpi_sp_tuan_8":""
}"""


SAN_PHAM_PROMPT = """Bạn đang xem trang PHẦN II – SẢN PHẨM NGHIỆM THU của PHIẾU ĐÁNH GIÁ {loai_danh_gia_up} CT Group.

NHIỆM VỤ: Đọc đầy đủ thông tin từng tuần (2.1 → 2.8).

QUY TẮC:
1. NGUYÊN VĂN — không tóm tắt, không rút gọn
2. Đọc TẤT CẢ tuần có trong trang (có thể có 1 đến nhiều tuần)
3. Mỗi tuần 2.X tương ứng với các field san_pham_X, so_luong_file_X, link_dinh_kem_X, vi_pham_upload_X, kpi_sp_tuan_X
4. Tên file / link → giữ NGUYÊN VĂN đầy đủ
5. Ô trống → ""

CẤU TRÚC TỪNG TUẦN (ví dụ tuần 1 = hàng 2.1):
  san_pham_1:        tên sản phẩm / danh sách file nộp (NGUYÊN VĂN từ ô "Sản phẩm:")
  nhiem_vu_tuan_1:   nội dung "Nhiệm vụ đặt ra:" trong cùng hàng 2.1 (NGUYÊN VĂN, để "" nếu không có)
  so_luong_file_1:   số lượng file
  link_dinh_kem_1:   TOÀN BỘ link / tên file đính kèm — ghi NGUYÊN VĂN ĐẦYĐỦ từng cái, mỗi link/file 1 dòng, KHÔNG bỏ sót, KHÔNG rút ngắn
  vi_pham_upload_1:  số lần vi phạm upload + ngày cụ thể
  kpi_sp_tuan_1:     % KPI tuần đó — đọc từ CỘT % KẾ BÊN hàng 2.1

(tương tự cho tuần 2→8)

TRẢ VỀ JSON THUẦN:
{
  "san_pham_1":"","nhiem_vu_tuan_1":"","so_luong_file_1":"","link_dinh_kem_1":"","vi_pham_upload_1":"","kpi_sp_tuan_1":"",
  "san_pham_2":"","nhiem_vu_tuan_2":"","so_luong_file_2":"","link_dinh_kem_2":"","vi_pham_upload_2":"","kpi_sp_tuan_2":"",
  "san_pham_3":"","nhiem_vu_tuan_3":"","so_luong_file_3":"","link_dinh_kem_3":"","vi_pham_upload_3":"","kpi_sp_tuan_3":"",
  "san_pham_4":"","nhiem_vu_tuan_4":"","so_luong_file_4":"","link_dinh_kem_4":"","vi_pham_upload_4":"","kpi_sp_tuan_4":"",
  "san_pham_5":"","nhiem_vu_tuan_5":"","so_luong_file_5":"","link_dinh_kem_5":"","vi_pham_upload_5":"","kpi_sp_tuan_5":"",
  "san_pham_6":"","nhiem_vu_tuan_6":"","so_luong_file_6":"","link_dinh_kem_6":"","vi_pham_upload_6":"","kpi_sp_tuan_6":"",
  "san_pham_7":"","nhiem_vu_tuan_7":"","so_luong_file_7":"","link_dinh_kem_7":"","vi_pham_upload_7":"","kpi_sp_tuan_7":"",
  "san_pham_8":"","nhiem_vu_tuan_8":"","so_luong_file_8":"","link_dinh_kem_8":"","vi_pham_upload_8":"","kpi_sp_tuan_8":""
}"""
