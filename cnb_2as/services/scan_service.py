# Copyright (c) 2025, antruong and contributors
# For license information, please see license.txt

"""Service layer for phiếu đánh giá scan operations.

Provides all helper functions for file reading (DOCX, PDF, HTML),
OCR/Vision extraction, XML building, and session management.
Called by: api/scan_phieu.py
"""

"""
scan_phieu.py – Đọc phiếu đánh giá thử việc từ file scan (PDF/ảnh/HTML/DOCX)
Luồng đọc: OCR API (ctpai.vn) → GPT-4o Vision (chữ viết tay) → Docling text layer

Endpoints:
  POST /api/method/cnb_2as.api.scan_phieu.scan_extract   – Upload → trích xuất fields
  POST /api/method/cnb_2as.api.scan_phieu.scan_analyze   – Xác nhận → AI phân tích
"""
import base64, io, json, os, re, subprocess, sys, tempfile, uuid
from datetime import date
from pathlib import Path

import frappe

from cnb_2as.services.scan_readers import (
    _call_ocr_api,
    _pdf_to_images,
    _call_vision_ocr,
    _read_with_docling,
    _sanitize_markdown_tables,
    _read_html_text,
    _read_docx_text,
    _read_docx_structured,
    _merge_ocr_vision,
    _extract_text,
)

from cnb_2as.services.prompts import (
    _MERGE_PROMPT,
    _EXTRACT_PROMPT,
    _ANALYZE_PROMPT,
    VISION_JSON_PROMPT,
    HOI_NHAP_PROMPT,
    KPI_PROMPT,
    SAN_PHAM_PROMPT,
)

from openai import OpenAI

# ── OpenAI client ──────────────────────────────────────────────────────────────
_client = None



def _get_client() -> OpenAI:
    global _client
    if _client is None:
        key = os.getenv("OPENAI_API_KEY", "") or getattr(frappe.conf, "openai_api_key", "")
        if not key:
            frappe.throw("Chưa cấu hình OPENAI_API_KEY")
        _client = OpenAI(api_key=frappe.conf.get("openai_api_key", ""))
    return _client


# ── Session namespace ──────────────────────────────────────────────────────────
_NS = "cnb_scan_phieu"


def _save_session(sid: str, data: dict):

    frappe.cache().set_value(f"{_NS}:{sid}", json.dumps(data, ensure_ascii=False), expires_in_sec=3600)


def _load_session(sid: str) -> dict:
    raw = frappe.cache().get_value(f"{_NS}:{sid}")
    if not raw:
        frappe.throw(f"Session không tồn tại hoặc đã hết hạn: {sid}")
    return json.loads(raw)


def _escape_xml(s: str) -> str:
    """Escape các ký tự đặc biệt trong XML."""
    if not s:
        return ""
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;")
             .replace("'", "&apos;"))


def _build_xml_from_fields(fields: dict) -> str:
    """Tạo XML phiếu đánh giá từ fields dict (CTG-GO-NLCD-QT16-BM01)."""
    e = _escape_xml

    sec_a = (
        "\n  <ThongTinChung>\n"
        f"    <TenNhanVien>{e(fields.get('ho_ten',''))}</TenNhanVien>\n"
        f"    <MaNhanVien>{e(fields.get('ma_nhan_su',''))}</MaNhanVien>\n"
        f"    <ChucDanh>{e(fields.get('chuc_danh',''))}</ChucDanh>\n"
        f"    <DonVi>{e(fields.get('phong_ban',''))}</DonVi>\n"
        f"    <CongTy>{e(fields.get('cong_ty',''))}</CongTy>\n"
        f"    <NgayNhanViec>{e(fields.get('ngay_nhan_viec',''))}</NgayNhanViec>\n"
        f"    <NgayHetHan>{e(fields.get('ngay_het_han',''))}</NgayHetHan>\n"
        f"    <ThoiGianThuViec>{e(fields.get('thoi_gian_thu_viec',''))}</ThoiGianThuViec>\n"
        f"    <LoaiHopDong>{e(fields.get('loai_hop_dong',''))}</LoaiHopDong>\n"
        f"    <TenHOD>{e(fields.get('ten_hod',''))}</TenHOD>\n"
        f"    <MaHOD>{e(fields.get('ma_hod',''))}</MaHOD>\n"
        f"    <ChucDanhHOD>{e(fields.get('chuc_danh_hod',''))}</ChucDanhHOD>\n"
        f"    <DonViHOD>{e(fields.get('don_vi_hod',''))}</DonViHOD>\n"
        "  </ThongTinChung>"
    )

    # B. Phan I – Nhan xet chung (5 cau)
    nxet_labels = [
        "Những điểm làm tốt trong quá trình thử việc",
        "Các kỹ năng đáp ứng yêu cầu công việc",
        "Các hoạt động tích cực tham gia",
        "Những điểm cần cải thiện",
        "Kỹ năng cần nâng cao hoặc hạn chế cần khắc phục",
    ]
    nxet_items = []
    for i in range(1, 6):
        nv    = e(str(fields.get(f'nhan_xet_{i}_nv', '') or ''))
        hod   = e(str(fields.get(f'nhan_xet_{i}_hod', '') or ''))
        label = e(nxet_labels[i - 1])
        nxet_items.append(
            f'    <NhanXet stt="{i}" noiDung="{label}">\n'
            f'      <NV>{nv}</NV>\n'
            f'      <HOD>{hod}</HOD>\n'
            f'    </NhanXet>'
        )
    sec_b = "\n  <PhanI_NhanXetChung>\n" + "\n".join(nxet_items) + "\n  </PhanI_NhanXetChung>"

    # C. Phan II – KPI (dynamic weeks) + san pham (dynamic weeks)
    # Detect actual number of weeks from data (max 8)
    n_tuan = 4  # default
    for _t in range(8, 0, -1):
        if any([
            fields.get(f'kpi_tuan_{_t}_ty_le', ''),
            fields.get(f'san_pham_{_t}', ''),
            fields.get(f'kpi_tuan_{_t}', {}).get('ty_le', ''),
        ]):
            n_tuan = _t
            break

    kpi_items = []
    for i in range(1, n_tuan + 1):
        ty_le = e(str(fields.get(f'kpi_tuan_{i}_ty_le', '') or ''))
        kpi_items.append(f'    <Tuan so="{i}" tyLe="{ty_le}"/>')

    tbc_nv    = e(str(fields.get('diem_tbc_kpi_nv', '') or ''))
    tbc_hod   = e(str(fields.get('diem_tbc_kpi_hod', '') or ''))
    cong_viec = e(str(fields.get('cong_viec_duoc_giao', '') or ''))

    # 1.6 – Nhiệm vụ (dynamic, max 8)
    n_nv = 4  # default
    for _n in range(8, 0, -1):
        if fields.get(f'nhiem_vu_{_n}_noi_dung', '') or fields.get(f'nhiem_vu_{_n}_ket_qua', ''):
            n_nv = _n
            break

    nv_items = []
    for i in range(1, n_nv + 1):
        nd  = e(str(fields.get(f'nhiem_vu_{i}_noi_dung','') or ''))
        kq  = e(str(fields.get(f'nhiem_vu_{i}_ket_qua','') or ''))
        tl  = e(str(fields.get(f'nhiem_vu_{i}_ty_le','') or ''))
        hod = e(str(fields.get(f'nhiem_vu_{i}_hod','') or ''))
        nv_items.append(
            f'    <NhiemVu so="{i}" tyLe="{tl}">\n'
            f'      <NoiDung>{nd}</NoiDung>\n'
            f'      <KetQua>{kq}</KetQua>\n'
            f'      <HOD>{hod}</HOD>\n'
            f'    </NhiemVu>'
        )

    sp_items = []
    for i in range(1, n_tuan + 1):
        sp      = e(str(fields.get(f'san_pham_{i}', '') or ''))
        so_file = e(str(fields.get(f'so_luong_file_{i}', '') or ''))
        link    = e(str(fields.get(f'link_dinh_kem_{i}', '') or ''))
        vi_pham = e(str(fields.get(f'vi_pham_upload_{i}', '') or ''))
        kpi_sp  = e(str(fields.get(f'kpi_sp_tuan_{i}', '') or ''))
        sp_items.append(
            f'    <SanPham tuan="{i}" tyLeKPI="{kpi_sp}">\n'
            f'      <DanhSach>{sp}</DanhSach>\n'
            f'      <SoLuongFile>{so_file}</SoLuongFile>\n'
            f'      <DuongLinkDinhKem>{link}</DuongLinkDinhKem>\n'
            f'      <SoLanViPhamUpload>{vi_pham}</SoLanViPhamUpload>\n'
            f'    </SanPham>'
        )


    sec_c = (
        "\n  <PhanII_KPI>\n"
        + "\n".join(kpi_items)
        + f"\n    <DiemTBC_NV>{tbc_nv}</DiemTBC_NV>"
        + f"\n    <DiemTBC_HOD>{tbc_hod}</DiemTBC_HOD>"
        + f"\n    <CongViecDuocGiao>{cong_viec}</CongViecDuocGiao>"
        + "\n  </PhanII_KPI>"
        + "\n  <CongViecDuocGiao>\n"
        + "\n".join(nv_items)
        + "\n  </CongViecDuocGiao>"
        + "\n  <SanPhamNghiemThu>\n"
        + "\n".join(sp_items)
        + "\n  </SanPhamNghiemThu>"
    )

    # D. Phan III – Hoi nhap (9 cau)
    hn_labels = [
        "Sứ mệnh Tập đoàn", "Sứ mệnh bản thân",
        "Tầm nhìn Tập đoàn", "Tầm nhìn bản thân",
        "Văn hóa cốt lõi Tập đoàn", "Giá trị cốt lõi bản thân",
        "Sự phù hợp văn hóa làm việc",
        "Văn hóa kinh doanh", "Đóng góp khác trong giai đoạn hội nhập",
    ]
    hn_items = []
    for i in range(1, 10):
        nv    = e(str(fields.get(f'hoi_nhap_{i}_nv', '') or ''))
        hod   = e(str(fields.get(f'hoi_nhap_{i}_hod', '') or ''))
        label = e(hn_labels[i - 1])
        hn_items.append(
            f'    <CauHoi so="{i}" noiDung="{label}">\n'
            f'      <NV>{nv}</NV>\n'
            f'      <HOD>{hod}</HOD>\n'
            f'    </CauHoi>'
        )
    sub_labels = ["Hiệu quả", "Tốc độ", "Kỷ luật", "Học tập", "Chính trực"]
    sub_items  = []
    for j, sl in enumerate(sub_labels, 1):
        nv  = e(str(fields.get(f'hoi_nhap_7_{j}_nv',  '') or ''))
        hod = e(str(fields.get(f'hoi_nhap_7_{j}_hod', '') or ''))
        sub_items.append(f'      <Sub so="7.{j}" noiDung="{e(sl)}"><NV>{nv}</NV><HOD>{hod}</HOD></Sub>')

    sec_d = (
        "\n  <PhanIII_HoiNhap>\n"
        + "\n".join(hn_items)
        + "\n    <SubCau7>\n" + "\n".join(sub_items) + "\n    </SubCau7>"
        + "\n  </PhanIII_HoiNhap>"
    )

    # E. Ket luan
    sec_e = (
        "\n  <KetLuan>\n"
        f"    <KetQua>{e(fields.get('ket_luan',''))}</KetQua>\n"
        f"    <DeXuatKyHD>{e(fields.get('de_xuat_ky_hd',''))}</DeXuatKyHD>\n"
        f"    <DeXuatTangThuNhap>{e(fields.get('de_xuat_tang_thu_nhap',''))}</DeXuatTangThuNhap>\n"
        f"    <DeNghiPhoiHop>{e(fields.get('de_nghi_phoi_hop',''))}</DeNghiPhoiHop>\n"
        f"    <YKienHOD>{e(fields.get('y_kien_hod',''))}</YKienHOD>\n"
        f"    <YKienRTD>{e(fields.get('y_kien_rtd',''))}</YKienRTD>\n"
        f"    <NgayKy>{e(fields.get('ngay_ky',''))}</NgayKy>\n"
        f"    <TenHODKy>{e(fields.get('ten_hod_ky',''))}</TenHODKy>\n"
        "  </KetLuan>"
    )

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<PhieuDanhGiaThuViec>'
        + sec_a + sec_b + sec_c + sec_d + sec_e
        + '\n</PhieuDanhGiaThuViec>'
    )


def _scan_extract_docx(file_bytes, filename, client, eval_type):
    """
    Extract fields from DOCX using batch OpenAI calls (5-section strategy).

    Returns:
        tuple: (fields dict, raw_text str)
    """

    fields = {}
    raw_text = ""

    method_note = "DOCX – batch extraction (5 section)"
    frappe.logger("cnb_scan").info(f"[SCAN] DOCX structured batch: {filename}")

    sections = _read_docx_structured(file_bytes)
    if not sections:
        raw_text = _read_docx_text(file_bytes)
    else:
        raw_text = "\n\n".join(f"=== {k} ===\n{v}" for k, v in sections.items())

    BATCH_PROMPTS = {
        "A_thong_tin": """Trích xuất THONG TIN CHUNG + PHẦN I từ phần này. Trả JSON thuần:
{
  "ho_ten":"","ma_nhan_su":"","chuc_danh":"","phong_ban":"","cong_ty":"",
  "ngay_nhan_viec":"","ngay_het_han":"","thoi_gian_thu_viec":"","loai_hop_dong":"",
  "ten_hod":"","ma_hod":"","chuc_danh_hod":"","don_vi_hod":"",
  "nhan_xet_1_nv":"","nhan_xet_1_hod":"",
  "nhan_xet_2_nv":"","nhan_xet_2_hod":"",
  "nhan_xet_3_nv":"","nhan_xet_3_hod":"",
  "nhan_xet_4_nv":"","nhan_xet_4_hod":"",
  "nhan_xet_5_nv":"","nhan_xet_5_hod":""
}
Lấy NGUYÊN VĂN, không tóm tắt. Ô trống → "".""",
        "B_kpi": """Trích xuất PHẦN II KPI từ phần này. Trả JSON thuần:
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
  "nhiem_vu_8_noi_dung":"","nhiem_vu_8_ket_qua":"","nhiem_vu_8_ty_le":"","nhiem_vu_8_hod":""
}
Đọc tất cả tuần có trong tài liệu. % KPI theo từng tuần (1.1-1.8). NGUYÊN VĂN không tóm tắt.""",
        "C_san_pham": """Trích xuất SẢN PHẨM NGHIỆM THU từng tuần từ phần này. Trả JSON thuần:
{
  "san_pham_1":"","so_luong_file_1":"","link_dinh_kem_1":"","vi_pham_upload_1":"","kpi_sp_tuan_1":"",
  "san_pham_2":"","so_luong_file_2":"","link_dinh_kem_2":"","vi_pham_upload_2":"","kpi_sp_tuan_2":"",
  "san_pham_3":"","so_luong_file_3":"","link_dinh_kem_3":"","vi_pham_upload_3":"","kpi_sp_tuan_3":"",
  "san_pham_4":"","so_luong_file_4":"","link_dinh_kem_4":"","vi_pham_upload_4":"","kpi_sp_tuan_4":"",
  "san_pham_5":"","so_luong_file_5":"","link_dinh_kem_5":"","vi_pham_upload_5":"","kpi_sp_tuan_5":"",
  "san_pham_6":"","so_luong_file_6":"","link_dinh_kem_6":"","vi_pham_upload_6":"","kpi_sp_tuan_6":"",
  "san_pham_7":"","so_luong_file_7":"","link_dinh_kem_7":"","vi_pham_upload_7":"","kpi_sp_tuan_7":"",
  "san_pham_8":"","so_luong_file_8":"","link_dinh_kem_8":"","vi_pham_upload_8":"","kpi_sp_tuan_8":""
}
Lấy NGUYÊN VĂN toàn bộ tên sản phẩm và link. Ô trống → "".""",
        "D_hoi_nhap": """Trích xuất PHẦN III HỘI NHẬP (9 câu) từ phần này. Trả JSON thuần:
{
  "hoi_nhap_1_nv":"","hoi_nhap_1_hod":"",
  "hoi_nhap_2_nv":"","hoi_nhap_2_hod":"",
  "hoi_nhap_3_nv":"","hoi_nhap_3_hod":"",
  "hoi_nhap_4_nv":"","hoi_nhap_4_hod":"",
  "hoi_nhap_5_nv":"","hoi_nhap_5_hod":"",
  "hoi_nhap_6_nv":"","hoi_nhap_6_hod":"",
  "hoi_nhap_7_nv":"","hoi_nhap_7_hod":"",
  "hoi_nhap_7_1_nv":"","hoi_nhap_7_1_hod":"",
  "hoi_nhap_7_2_nv":"","hoi_nhap_7_2_hod":"",
  "hoi_nhap_7_3_nv":"","hoi_nhap_7_3_hod":"",
  "hoi_nhap_7_4_nv":"","hoi_nhap_7_4_hod":"",
  "hoi_nhap_7_5_nv":"","hoi_nhap_7_5_hod":"",
  "hoi_nhap_8_nv":"","hoi_nhap_8_hod":"",
  "hoi_nhap_9_nv":"","hoi_nhap_9_hod":""
}
Lấy NGUYÊN VĂN toàn bộ câu trả lời, không tóm tắt. Ô trống → "".""",
        "E_ket_luan": """Trích xuất KẾT LUẬN và ĐỀ XUẤT từ phần này. Trả JSON thuần:
{
  "ket_luan":"","de_xuat_ky_hd":"","de_xuat_tang_thu_nhap":"",
  "de_nghi_phoi_hop":"","y_kien_hod":"","y_kien_rtd":"",
  "ngay_ky":"","ten_hod_ky":""
}
Lấy NGUYÊN VĂN. Ô trống → ""."""
    }

    DOCX_APPENDABLE = {
        'cong_viec_duoc_giao',
        # Nhiem vu 1.6 - APPEND toan bo (noi_dung + ket_qua + ty_le + hod)
        'nhiem_vu_1_noi_dung','nhiem_vu_1_ket_qua','nhiem_vu_1_ty_le','nhiem_vu_1_hod',
        'nhiem_vu_2_noi_dung','nhiem_vu_2_ket_qua','nhiem_vu_2_ty_le','nhiem_vu_2_hod',
        'nhiem_vu_3_noi_dung','nhiem_vu_3_ket_qua','nhiem_vu_3_ty_le','nhiem_vu_3_hod',
        'nhiem_vu_4_noi_dung','nhiem_vu_4_ket_qua','nhiem_vu_4_ty_le','nhiem_vu_4_hod',
        'nhiem_vu_5_noi_dung','nhiem_vu_5_ket_qua','nhiem_vu_5_ty_le','nhiem_vu_5_hod',
        'nhiem_vu_6_noi_dung','nhiem_vu_6_ket_qua','nhiem_vu_6_ty_le','nhiem_vu_6_hod',
        'nhiem_vu_7_noi_dung','nhiem_vu_7_ket_qua','nhiem_vu_7_ty_le','nhiem_vu_7_hod',
        'nhiem_vu_8_noi_dung','nhiem_vu_8_ket_qua','nhiem_vu_8_ty_le','nhiem_vu_8_hod',
        'nhan_xet_1_nv','nhan_xet_2_nv','nhan_xet_3_nv','nhan_xet_4_nv','nhan_xet_5_nv',
        'nhan_xet_1_hod','nhan_xet_2_hod','nhan_xet_3_hod','nhan_xet_4_hod','nhan_xet_5_hod',
        'san_pham_1','san_pham_2','san_pham_3','san_pham_4',
        'san_pham_5','san_pham_6','san_pham_7','san_pham_8',
        'nhiem_vu_tuan_1','nhiem_vu_tuan_2','nhiem_vu_tuan_3','nhiem_vu_tuan_4',
        'nhiem_vu_tuan_5','nhiem_vu_tuan_6','nhiem_vu_tuan_7','nhiem_vu_tuan_8',
        'link_dinh_kem_1','link_dinh_kem_2','link_dinh_kem_3','link_dinh_kem_4',
        'link_dinh_kem_5','link_dinh_kem_6','link_dinh_kem_7','link_dinh_kem_8',
        'hoi_nhap_1_nv','hoi_nhap_2_nv','hoi_nhap_3_nv','hoi_nhap_4_nv',
        'hoi_nhap_5_nv','hoi_nhap_6_nv','hoi_nhap_7_nv',
        'hoi_nhap_7_1_nv','hoi_nhap_7_2_nv','hoi_nhap_7_3_nv',
        'hoi_nhap_7_4_nv','hoi_nhap_7_5_nv',
        'hoi_nhap_8_nv','hoi_nhap_9_nv',
    }

    def _merge_docx(base: dict, new: dict) -> dict:
        for k, v in new.items():
            if k == "confidence" or not v:
                continue
            if k in DOCX_APPENDABLE:
                existing = base.get(k, '')
                if existing:
                    nv = str(v).strip()
                    if nv and nv not in existing:
                        base[k] = existing.rstrip() + '\n' + nv
                else:
                    base[k] = v
            elif isinstance(v, dict) and isinstance(base.get(k), dict):
                for kk, vv in v.items():
                    if vv and not base[k].get(kk):
                        base[k][kk] = vv
            elif k not in base or not base[k]:
                base[k] = v
        return base

    if not sections:
        sections = {"A_thong_tin": raw_text}

    for sec_key, sec_text in sections.items():
        if not sec_text.strip():
            continue
        prompt = BATCH_PROMPTS.get(sec_key)
        if not prompt:
            continue
        batch_text = sec_text[:60000]
        frappe.logger("cnb_scan").info(f"[SCAN] DOCX batch {sec_key}: {len(batch_text)} chars")
        try:
            resp = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                messages=[{"role": "user", "content": prompt + "\n\nNỘI DUNG:\n" + batch_text}],
                temperature=0,
                max_tokens=16000,
                response_format={"type": "json_object"},
            )
            partial = json.loads(resp.choices[0].message.content or "{}")
            fields = _merge_docx(fields, partial)
        except Exception as e:
            frappe.logger("cnb_scan").warning(f"[SCAN] DOCX batch {sec_key} lỗi: {e}")


    return fields, raw_text


def _scan_extract_html(file_bytes, client, eval_type):
    """
    Extract fields from HTML using a single OpenAI call.

    Returns:
        tuple: (fields dict, raw_text str)
    """

    fields = {}

    raw_text = _read_html_text(file_bytes)
    method_note = "HTML – đọc trực tiếp"
    if raw_text.strip():
        try:
            _loai = "học việc" if eval_type == "hoc_viec" else "thử việc"
            _loai_up = "HỌC VIỆC" if eval_type == "hoc_viec" else "THỬ VIỆC"
            _loai_cap = "Học việc" if eval_type == "hoc_viec" else "Thử việc"
            prompt_content = _EXTRACT_PROMPT.replace("{loai_danh_gia}", _loai).replace("{loai_danh_gia_up}", _loai_up).replace("{loai_danh_gia_cap}", _loai_cap)
            resp = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o"),
                messages=[{"role": "user", "content": prompt_content + raw_text[:80000]}],
                temperature=0,
                max_tokens=8000,
                response_format={"type": "json_object"},
            )
            fields = json.loads(resp.choices[0].message.content or "{}")
        except Exception as e:
            frappe.logger("cnb_scan").warning(f"[SCAN] HTML extract lỗi: {e}")


    return fields, raw_text


def _scan_extract_pdf_image(file_bytes, filename, client, eval_type):
    """
    Extract fields from PDF/image using GPT-4o Vision with smart batching.

    Returns:
        tuple: (fields dict, raw_text str)
    """

    fields = {}
    raw_text = ""


    method_note = "GPT-4o Vision → JSON trực tiếp"
    frappe.logger("cnb_scan").info(f"[SCAN] Direct Vision→JSON: {filename}")

    # Build image parts
    fname = filename.lower()
    if fname.endswith(".pdf"):
        page_images = _pdf_to_images(file_bytes)
    else:
        ext = fname.rsplit(".", 1)[-1]
        mime_map = {"jpg":"jpeg","jpeg":"jpeg","png":"png","bmp":"bmp","webp":"webp"}
        page_images = [file_bytes]  # single image

    if not page_images:
        frappe.throw(f"Không thể đọc file '{filename}'. Vui lòng kiểm tra định dạng.")

    frappe.logger("cnb_scan").info(f"[SCAN] {len(page_images)} trang → Vision batches")

    # Prompt cho Vision → JSON trực tiếp

    def _build_image_part(img_bytes: bytes) -> dict:
        b64 = base64.b64encode(img_bytes).decode()
        return {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "high"}
        }

    # Các field dài trải nhiều trang → APPEND thay vì first-wins
    APPENDABLE = {
        'cong_viec_duoc_giao',
        # Nhiệm vụ 1.6 — APPEND toàn bộ (nội dung + kết quả + % + HOD)
        # 1.6 có thể trải 3-4 trang, cần append cả ty_le và hod
        'nhiem_vu_1_noi_dung','nhiem_vu_1_ket_qua','nhiem_vu_1_ty_le','nhiem_vu_1_hod',
        'nhiem_vu_2_noi_dung','nhiem_vu_2_ket_qua','nhiem_vu_2_ty_le','nhiem_vu_2_hod',
        'nhiem_vu_3_noi_dung','nhiem_vu_3_ket_qua','nhiem_vu_3_ty_le','nhiem_vu_3_hod',
        'nhiem_vu_4_noi_dung','nhiem_vu_4_ket_qua','nhiem_vu_4_ty_le','nhiem_vu_4_hod',
        'nhiem_vu_5_noi_dung','nhiem_vu_5_ket_qua','nhiem_vu_5_ty_le','nhiem_vu_5_hod',
        'nhiem_vu_6_noi_dung','nhiem_vu_6_ket_qua','nhiem_vu_6_ty_le','nhiem_vu_6_hod',
        'nhiem_vu_7_noi_dung','nhiem_vu_7_ket_qua','nhiem_vu_7_ty_le','nhiem_vu_7_hod',
        'nhiem_vu_8_noi_dung','nhiem_vu_8_ket_qua','nhiem_vu_8_ty_le','nhiem_vu_8_hod',
        # Nhận xét chung (5 câu NV + HOD)
        'nhan_xet_1_nv','nhan_xet_2_nv','nhan_xet_3_nv',
        'nhan_xet_4_nv','nhan_xet_5_nv',
        'nhan_xet_1_hod','nhan_xet_2_hod','nhan_xet_3_hod',
        'nhan_xet_4_hod','nhan_xet_5_hod',
        # Sản phẩm (trải nhiều trang)
        'san_pham_1','san_pham_2','san_pham_3','san_pham_4',
        'san_pham_5','san_pham_6','san_pham_7','san_pham_8',
        'link_dinh_kem_1','link_dinh_kem_2','link_dinh_kem_3','link_dinh_kem_4',
        'link_dinh_kem_5','link_dinh_kem_6','link_dinh_kem_7','link_dinh_kem_8',
        # Hội nhập (9 câu, trải 11 trang)
        'hoi_nhap_1_nv','hoi_nhap_2_nv','hoi_nhap_3_nv','hoi_nhap_4_nv',
        'hoi_nhap_5_nv','hoi_nhap_6_nv','hoi_nhap_7_nv',
        'hoi_nhap_7_1_nv','hoi_nhap_7_2_nv','hoi_nhap_7_3_nv',
        'hoi_nhap_7_4_nv','hoi_nhap_7_5_nv',
        'hoi_nhap_8_nv','hoi_nhap_9_nv',
        # HOD hội nhập
        'hoi_nhap_1_hod','hoi_nhap_2_hod','hoi_nhap_3_hod','hoi_nhap_4_hod',
        'hoi_nhap_5_hod','hoi_nhap_6_hod','hoi_nhap_7_hod',
        'hoi_nhap_7_1_hod','hoi_nhap_7_2_hod','hoi_nhap_7_3_hod',
        'hoi_nhap_7_4_hod','hoi_nhap_7_5_hod',
        'hoi_nhap_8_hod','hoi_nhap_9_hod',
    }

    def _merge_fields(base: dict, new: dict) -> dict:
        """Merge batch JSON vào base:
        - APPENDABLE fields: nối thêm nội dung mới (nhiều trang)
        - Các field khác: first-wins (chỉ lấy giá trị đầu tiên non-empty)
        """
        for k, v in new.items():
            if k == "confidence":
                continue
            if not v:  # bỏ qua giá trị rỗng
                continue
            if k in APPENDABLE:
                existing = base.get(k, '')
                if existing:
                    # Nối vào nếu nội dung mới khác (tránh duplicate)
                    new_v = str(v).strip()
                    if new_v and new_v not in existing:
                        base[k] = existing.rstrip() + '\n' + new_v
                else:
                    base[k] = v
            elif isinstance(v, dict) and isinstance(base.get(k), dict):
                for kk, vv in v.items():
                    if vv and not base[k].get(kk):
                        base[k][kk] = vv
            elif k not in base or not base[k]:
                base[k] = v
        return base

    fields = {}
    total_pages = len(page_images)

    # ── Prompt chuyên biệt cho phần Hội Nhập (trang 9 trở đi) ──────────────

    # ── Smart batching ────────────────────────────────────────────────────
    # Trang 1-8: batch 2 trang (thông tin chung, KPI, sản phẩm)
    # Trang 9+:  batch 4 trang với HOI_NHAP_PROMPT chuyên biệt
    SPLIT_PAGE = 8   # từ trang 9 trở đi là hội nhập
    HN_BATCH   = 4   # 4 trang/batch cho hội nhập

    def _call_batch(imgs, prompt, label):
        parts = [_build_image_part(img) for img in imgs]
        msg_content = [{"type": "text", "text": prompt}, *parts]
        try:
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": msg_content}],
                temperature=0,
                max_tokens=16000,
                response_format={"type": "json_object"},
            )
            txt = resp.choices[0].message.content or "{}"
            return txt, json.loads(txt)
        except Exception as e:
            frappe.logger("cnb_scan").warning(f"[SCAN] Batch {label} lỗi: {e}")
            return "{}", {}

    # ── Phase 0: Detect section trên từng trang (cheap – detail:low) ────────
    _loai = "học việc" if eval_type == "hoc_viec" else "thử việc"
    _loai_up = "HỌC VIỆC" if eval_type == "hoc_viec" else "THỬ VIỆC"
    _loai_cap = "Học việc" if eval_type == "hoc_viec" else "Thử việc"
    DETECT_PROMPT = (
        f'Nhìn vào trang phiếu đánh giá {_loai} CT Group này. '
        'Trả về JSON: {"section": "...", "page_label": "..."}\n'
        'section phải là 1 trong: "A_thong_tin", "I_nhan_xet", "II_kpi", '
        '"II_san_pham", "III_hoi_nhap", "C_ket_luan"\n'
        'page_label: số trang in trên phiếu, nếu không thấy để "".\n\n'
        'QUY TẮC (ưu tiên từ trên xuống):\n'
        '1. Thấy "HỘI NHẬP"/"Sứ mệnh"/"Tầm nhìn"/"Văn hóa"/"7.1"/"III." → III_hoi_nhap\n'
        '2. Tick chọn "ĐẠT"/"Không đạt"/"RTD"/"Kết luận" → C_ket_luan\n'
        '3. Thấy "Sản phẩm nghiệm thu"/cột "Link đính kèm"/"Tên sản phẩm" → II_san_pham\n'
        '4. Thấy "1.1"/"1.2"/"1.3"/"1.4"/"1.5"/"1.6"/"1.7"/"1.8"/"1.9"/"1.10"/'
        '"Điểm TBC"/"KPI"/"Công việc được giao"/"PHẦN II" → II_kpi\n'
        '5. Thấy bảng nhiều hàng với cột "Kết quả thực tế" + cột "%" '
        '(dù không có header 1.10 — đây là trang tiếp theo của 1.10) → II_kpi\n'
        '6. Thấy "PHẦN I"/"Nhận xét chung" → I_nhan_xet\n'
        '7. Bảng thông tin (họ tên, ngày nhận việc, bộ phận) → A_thong_tin\n'
        '⚠️ Bảng 1.10 trải nhiều trang: trang tiếp theo không có header '
        'nhưng có dòng nhiệm vụ + cột % → vẫn là II_kpi, KHÔNG phải II_san_pham.'
    )

    def _detect_section(img_bytes):
        b64 = base64.b64encode(img_bytes).decode()
        part = {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "low"}}
        try:
            r = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": [{"type": "text", "text": DETECT_PROMPT}, part]}],
                temperature=0, max_tokens=60,
                response_format={"type": "json_object"},
            )
            d = json.loads(r.choices[0].message.content or "{}")
            return d.get("section", "II_kpi"), d.get("page_label", "")
        except Exception:
            return "II_kpi", ""

    # Detect section cho từng trang
    page_sections = []
    for idx, img in enumerate(page_images):
        sec, lbl = _detect_section(img)
        page_sections.append(sec)
        frappe.logger("cnb_scan").info(f"[SCAN] Page {idx+1} → section={sec} label={lbl}")

    # ── Prompt chuyên biệt cho KPI (1.1–1.6) ───────────────────────────────



    # ── Prompt chuyên biệt cho KPI (1.1–1.10) ───────────────────────────────

    # ── Prompt chuyên biệt cho Sản Phẩm (2.1–2.8) ──────────────────────────

    # Map section → group_type
    HOI_NHAP_SECS  = {"III_hoi_nhap", "C_ket_luan"}
    KPI_SECS       = {"II_kpi"}
    SAN_PHAM_SECS  = {"II_san_pham"}

    def _sec_to_type(sec: str) -> str:
        if sec in HOI_NHAP_SECS: return "hoi_nhap"
        if sec in KPI_SECS:      return "kpi"
        if sec in SAN_PHAM_SECS: return "san_pham"
        return "general"

    # Batch sizes theo loại
    # kpi: tăng lên 3 trang — 1.6 có thể trải 3-4 trang, cần đủ context bảng
    BATCH_SIZES = {"hoi_nhap": 3, "kpi": 4, "san_pham": 4, "general": 2}
    PROMPT_MAP  = {
        "hoi_nhap": HOI_NHAP_PROMPT,
        "kpi":      KPI_PROMPT,
        "san_pham": SAN_PHAM_PROMPT,
        "general":  VISION_JSON_PROMPT,
    }

    # Smooth Pass 1: trang general kẹt giữa 2 hoi_nhap → III_hoi_nhap
    #                  trang GENERAL kẹt giữa 2 kpi → kpi (KHÔNG kéo san_pham vào kpi)
    for idx in range(1, len(page_sections) - 1):
        prev_t = _sec_to_type(page_sections[idx-1])
        cur_t  = _sec_to_type(page_sections[idx])
        nxt_t  = _sec_to_type(page_sections[idx+1])
        if cur_t == "general" and prev_t == "hoi_nhap" and nxt_t == "hoi_nhap":
            page_sections[idx] = "III_hoi_nhap"
            frappe.logger("cnb_scan").info(f"[SCAN] Page {idx+1} re-classified → III_hoi_nhap (sandwich)")
        elif cur_t == "general" and prev_t == "kpi" and nxt_t == "kpi":
            page_sections[idx] = "II_kpi"
            frappe.logger("cnb_scan").info(f"[SCAN] Page {idx+1} re-classified → II_kpi (sandwich general)")

    # Pass 2 - kpi → kpi nếu gặp general sau kpi (NV5-7 trải nhiều trang)
    for idx in range(1, len(page_sections)):
        prev_t = _sec_to_type(page_sections[idx-1])
        cur_t  = _sec_to_type(page_sections[idx])
        if prev_t == "kpi" and cur_t == "general":
            page_sections[idx] = "II_kpi"
            frappe.logger("cnb_scan").info(f"[SCAN] Page {idx+1} re-classified → II_kpi (forward-prop)")

    # Pass 3 - Zone-based fill (thay forward-prop san_pham → kpi):
    # Phát hiện vùng san_pham = [first_sp, last_sp].
    # Mọi trang kpi/general NẰM TRONG vùng đó → reclassify thành san_pham.
    # Điều này ổn định hơn forward-prop vì detect có thể sai ±1 trang.
    sp_indices = [i for i, s in enumerate(page_sections) if _sec_to_type(s) == "san_pham"]
    if sp_indices:
        first_sp = min(sp_indices)
        last_sp  = max(sp_indices)
        for idx in range(first_sp, last_sp + 1):
            if _sec_to_type(page_sections[idx]) == "kpi":
                page_sections[idx] = "II_san_pham"
                frappe.logger("cnb_scan").info(
                    f"[SCAN] Page {idx+1} re-classified → II_san_pham (zone-fill [{first_sp+1}-{last_sp+1}])"
                )

    # Nhóm trang liên tiếp cùng loại thành batches
    groups = []
    i = 0
    while i < total_pages:
        cur_type = _sec_to_type(page_sections[i])
        bs = BATCH_SIZES[cur_type]
        batch_imgs = []
        grp_start  = i + 1
        while i < total_pages and len(batch_imgs) < bs:
            if _sec_to_type(page_sections[i]) != cur_type:
                break
            batch_imgs.append(page_images[i])
            i += 1
        groups.append({"type": cur_type, "imgs": batch_imgs, "start": grp_start})

    # ── Bridge batch: KPI_PROMPT chạy thêm trên vùng giáp ranh kpi→san_pham ──
    # Bảng 1.10 (nhiệm vụ + %) thường nằm ngay sau vùng kpi → bị detect là
    # san_pham → SAN_PHAM_PROMPT xử lý sai → nhiem_vu_X_ty_le trống.
    # Bridge batch = [trang kpi cuối + 3 trang sp đầu] chạy KPI_PROMPT trước
    # để capture đủ % hoàn thành từng nhiệm vụ.
    _sp_idx  = [j for j, s in enumerate(page_sections) if _sec_to_type(s) == "san_pham"]
    _kpi_idx = [j for j, s in enumerate(page_sections) if _sec_to_type(s) == "kpi"]
    if _sp_idx and _kpi_idx:
        _first_sp = min(_sp_idx)
        _kpi_before = [k for k in _kpi_idx if k < _first_sp]
        if _kpi_before:
            _bridge_start = max(_kpi_before)          # trang kpi cuối trước san_pham
            _bridge_end   = min(_first_sp + 3, total_pages)  # +3 trang sp đầu
            bridge_imgs   = [page_images[j] for j in range(_bridge_start, _bridge_end)]
            bridge_pg_s   = _bridge_start + 1
            bridge_pg_e   = _bridge_end
            frappe.logger("cnb_scan").info(
                f"[SCAN] Bridge KPI batch: trang {bridge_pg_s}–{bridge_pg_e} "
                f"(bảng 1.10 boundary)"
            )
            _btxt, _bpart = _call_batch(bridge_imgs, PROMPT_MAP["kpi"].replace("{loai_danh_gia}", _loai).replace("{loai_danh_gia_up}", _loai_up).replace("{loai_danh_gia_cap}", _loai_cap),
                                         f"trang {bridge_pg_s}–{bridge_pg_e} [kpi-bridge]")
            raw_text += f"\n\n=== trang {bridge_pg_s}–{bridge_pg_e} [kpi-bridge] ===\n" + _btxt
            fields = _merge_fields(fields, _bpart)

    # ── Phase 1+2: Extract từng group với prompt chuyên biệt ─────────────
    for grp in groups:
        prompt = PROMPT_MAP[grp["type"]].replace("{loai_danh_gia}", _loai).replace("{loai_danh_gia_up}", _loai_up).replace("{loai_danh_gia_cap}", _loai_cap)
        pg_s   = grp["start"]
        pg_e   = grp["start"] + len(grp["imgs"]) - 1
        label  = f"trang {pg_s}–{pg_e}/{total_pages} [{grp['type']}]"
        frappe.logger("cnb_scan").info(f"[SCAN] Extract: {label}")
        txt, partial = _call_batch(grp["imgs"], prompt, label)
        raw_text += f"\n\n=== {label} ===\n" + txt
        fields = _merge_fields(fields, partial)

    return fields, raw_text


def _parse_xml_to_fields(xml_str: str) -> dict:
    """Parse XML phiếu → dict fields (theo cấu trúc thực tế CTG-GO-NLCD-QT16-BM01)."""
    import xml.etree.ElementTree as ET

    def txt(el, tag, default=""):
        node = el.find(tag) if el is not None else None
        return (node.text or "").strip() if node is not None and node.text else default

    def attr(el, tag, att, default=""):
        node = el.find(tag) if el is not None else None
        return (node.get(att) or default).strip() if node is not None else default

    try:
        root = ET.fromstring(xml_str)
    except Exception:
        return {}

    fields = {}

    # A. Thông tin chung
    tc = root.find('ThongTinChung')
    fields['ho_ten']           = txt(tc, 'TenNhanVien')
    fields['ma_nhan_su']       = txt(tc, 'MaNhanVien')
    fields['chuc_danh']        = txt(tc, 'ChucDanh')
    fields['phong_ban']        = txt(tc, 'DonVi')
    fields['cong_ty']          = txt(tc, 'CongTy')
    fields['ngay_nhan_viec']   = txt(tc, 'NgayNhanViec')
    fields['ngay_het_han']     = txt(tc, 'NgayHetHan')
    fields['thoi_gian_thu_viec'] = txt(tc, 'ThoiGianThuViec')
    fields['loai_hop_dong']    = txt(tc, 'LoaiHopDong')
    fields['ten_hod']          = txt(tc, 'TenHOD')
    fields['ma_hod']           = txt(tc, 'MaHOD')
    fields['chuc_danh_hod']    = txt(tc, 'ChucDanhHOD')
    fields['don_vi_hod']       = txt(tc, 'DonViHOD')

    # B. Phần I – Nhận xét chung
    p1 = root.find('PhanI_NhanXetChung')
    if p1 is not None:
        for nx in p1.findall('NhanXet'):
            i = nx.get('stt','')
            fields[f'nhan_xet_{i}_nv']  = txt(nx, 'NV')
            fields[f'nhan_xet_{i}_hod'] = txt(nx, 'HOD')

    # C. Phần II – KPI
    p2 = root.find('PhanII_KPI')
    if p2 is not None:
        for tuan in p2.findall('Tuan'):
            i = tuan.get('so','')
            fields[f'kpi_tuan_{i}_ty_le'] = tuan.get('tyLe','')
        fields['diem_tbc_kpi_nv']   = txt(p2, 'DiemTBC_NV')
        fields['diem_tbc_kpi_hod']  = txt(p2, 'DiemTBC_HOD')
        fields['cong_viec_duoc_giao'] = txt(p2, 'CongViecDuocGiao')

    # C2. Nhiệm vụ – nằm trong root-level <CongViecDuocGiao> (KHÔNG phải trong PhanII_KPI)
    cvdg = root.find('CongViecDuocGiao')
    if cvdg is not None:
        for nv in cvdg.findall('NhiemVu'):
            i = nv.get('so', '')
            if not i:
                continue
            fields[f'nhiem_vu_{i}_noi_dung'] = txt(nv, 'NoiDung')
            fields[f'nhiem_vu_{i}_ket_qua']  = txt(nv, 'KetQua')
            fields[f'nhiem_vu_{i}_ty_le']     = nv.get('tyLe', '')
            fields[f'nhiem_vu_{i}_hod']       = txt(nv, 'HOD')

    sp_root = root.find('SanPhamNghiemThu')
    if sp_root is not None:
        for sp in sp_root.findall('SanPham'):
            i = sp.get('tuan','')
            fields[f'san_pham_{i}']       = txt(sp, 'DanhSach')
            fields[f'so_luong_file_{i}']  = txt(sp, 'SoLuongFile')
            fields[f'link_dinh_kem_{i}']  = txt(sp, 'DuongLinkDinhKem')
            fields[f'vi_pham_upload_{i}'] = txt(sp, 'SoLanViPhamUpload')
            fields[f'kpi_sp_tuan_{i}']    = sp.get('tyLeKPI','')

    # D. Phần III – Hội nhập
    p3 = root.find('PhanIII_HoiNhap')
    if p3 is not None:
        for cau in p3.findall('CauHoi'):
            i = cau.get('so','')
            fields[f'hoi_nhap_{i}_nv']  = txt(cau, 'NV')
            fields[f'hoi_nhap_{i}_hod'] = txt(cau, 'HOD')
        sub7 = p3.find('SubCau7')
        if sub7 is not None:
            for sub in sub7.findall('Sub'):
                so = sub.get('so','').replace('.','_')
                nv  = sub.find('NV')
                hod = sub.find('HOD')
                fields[f'hoi_nhap_{so}_nv']  = (nv.text  or '').strip() if nv  is not None else ''
                fields[f'hoi_nhap_{so}_hod'] = (hod.text or '').strip() if hod is not None else ''

    # E. Kết luận
    kl = root.find('KetLuan')
    fields['ket_luan']              = txt(kl, 'KetQua')
    fields['de_xuat_ky_hd']         = txt(kl, 'DeXuatKyHD')
    fields['de_xuat_tang_thu_nhap'] = txt(kl, 'DeXuatTangThuNhap')
    fields['de_nghi_phoi_hop']      = txt(kl, 'DeNghiPhoiHop')
    fields['y_kien_hod']            = txt(kl, 'YKienHOD')
    fields['y_kien_rtd']            = txt(kl, 'YKienRTD')
    fields['ngay_ky']               = txt(kl, 'NgayKy')
    fields['ten_hod_ky']            = txt(kl, 'TenHODKy')

    return fields


def _check_deadline(date_str: str) -> dict:
    import datetime
    if not date_str:
        return {"deadline_alert": False, "so_ngay_con_lai": None, "ngay_het_han_parsed": None}
    for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"]:
        try:
            d = datetime.datetime.strptime(date_str.strip(), fmt).date()
            delta = (d - date.today()).days
            return {
                "deadline_alert": delta <= 7,
                "so_ngay_con_lai": delta,
                "ngay_het_han_parsed": d.isoformat(),
            }
        except ValueError:
            continue
    return {"deadline_alert": False, "so_ngay_con_lai": None, "ngay_het_han_parsed": None}