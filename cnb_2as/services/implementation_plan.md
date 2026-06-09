# Tái ký – Nâng cấp toàn diện đánh giá & PDF

## Mục tiêu
Nâng cấp Tái ký với 3 nhóm thay đổi:
1. **Prompt chi tiết hơn** cho `_HOP_DONG_SYSTEM` và `_DE_XUAT_NHAN_SU_SYSTEM`
2. **Sub-agent agents.py** truyền thêm JD context vào hop dong & de xuat
3. **PDF client-side** (html2pdf.js) thay server-side, đầy đủ tất cả sections

---

## Proposed Changes

### 1. `eval_prompts.py` — Upgrade 2 prompts

#### `_HOP_DONG_SYSTEM` (Đánh giá điều kiện hợp đồng)
Thêm fields vào schema:
- `phan_tich_tong_the` — phân tích 3-5 câu chi tiết căn cứ
- `thoi_han_de_xuat` — thời hạn HĐ đề xuất (VD: "12 tháng")
- `dieu_kien_kem_theo` — điều kiện kèm theo nếu có
- `muc_do_khuyen_nghi` — "Khuyến nghị mạnh / Đồng ý / Cần xem xét / Không đồng ý"
- `cac_tieu_chi` có thêm `can_cu` — trích số liệu cụ thể

#### `_DE_XUAT_NHAN_SU_SYSTEM` (Đề xuất nhân sự)
Thêm fields vào từng đề xuất:
- `muc_do` — "Đồng ý / Đồng ý có điều kiện / Không đồng ý"
- `tac_dong_du_kien` — tác động dự kiến khi thực hiện
- `uu_tien` — "Cao / Trung bình / Thấp"
- Prompt yêu cầu giọng chuyên gia, có căn cứ số liệu

---

### 2. `agents.py` — Cải thiện sub-agents

#### `_evaluate_hop_dong`
- Truyền thêm `jd_context` từ JD gợi ý (nếu có)
- Rõ ràng hơn về context "Tái ký" vs "Ký mới"

#### `_evaluate_de_xuat_nhan_su`
- Truyền thêm `jd_context` để đánh giá phù hợp JD
- Xây dựng context từ `role_analysis` nếu có

---

### 3. `TaiKy.vue` — PDF client-side đầy đủ

Thay `downloadPdf()` gọi server → thay bằng **html2pdf.js** giống ThuViec.

#### Sections trong PDF (monochrome, theo thứ tự):
1. **Header**: Tên, mã NV, chức danh, đơn vị, ngày đánh giá
2. **Tổng quan**: Kết quả chung, điểm tổng, recommendation
3. **Bảng điểm năng lực** (competency_scores)
4. **Báo cáo ngày** (bao_cao_ngay) — nếu có
5. **Đánh giá điều kiện Hợp đồng** (danh_gia_hop_dong) — SECTION ĐỘC LẬP
   - loai_hop_dong_de_xuat, du_dieu_kien
   - phan_tich_tong_the
   - Bảng cac_tieu_chi (STT / Tiêu chí / Điểm / Kết quả / Căn cứ)
   - ly_do + khuyen_nghi
6. **Đánh giá đề xuất nhân sự** (danh_gia_de_xuat_nhan_su) — SECTION ĐỘC LẬP
   - Từng đề xuất: loại, nội dung, mức độ, căn cứ, lý do, khuyến nghị
   - nhan_xet_chung
7. **Đánh giá đề xuất quản lý** (danh_gia_quan_ly)
8. **Gợi ý JD** (jd_goi_y) — format mới (dark header band)
9. **Việc cần làm tiếp theo** (next_steps)
10. **Footer**: Trang X / Y

---

## Verification Plan
- `npm run build` phải pass
- `python3 -m py_compile` trên các file Python
- Test thủ công: chạy evaluation → click PDF → verify all sections hiện đủ
