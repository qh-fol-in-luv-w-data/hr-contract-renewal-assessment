# Copyright (c) 2025, antruong and contributors
# For license information, please see license.txt

"""OCR Service for converting scanned PDF files to Markdown.

Uses OpenAI GPT-4o Vision to extract text from scanned PDF pages.
PDF pages are converted to images, then sent to GPT-4o for OCR.

Requires:
    - openai_api_key configured in site_config.json
    - pdf2image package (pip install pdf2image)
    - poppler-utils system package (apt install poppler-utils)
"""

import base64
import io
import os
import time

import frappe


# Maximum file size for OCR: 20MB
MAX_OCR_FILE_SIZE_BYTES = 20 * 1024 * 1024
# Allowed extensions for OCR input
ALLOWED_OCR_EXTENSIONS = {".pdf"}
# Max pages to process (to control costs)
MAX_PAGES = 20


def get_ocr_api_url():
	"""Legacy function kept for backward compatibility.

	Returns:
		Empty string (no longer used, OCR is via OpenAI).
	"""
	return "openai-vision"


def validate_ocr_input(file_path):
	"""Validate that the file is suitable for OCR processing.

	Args:
		file_path: Absolute path to the file.

	Raises:
		ValueError: If file is invalid for OCR.
	"""
	if not os.path.exists(file_path):
		raise ValueError("File không tồn tại")

	ext = os.path.splitext(file_path)[1].lower()
	if ext not in ALLOWED_OCR_EXTENSIONS:
		raise ValueError(
			f"OCR chỉ hỗ trợ file PDF. Loại file hiện tại: {ext}"
		)

	file_size = os.path.getsize(file_path)
	if file_size > MAX_OCR_FILE_SIZE_BYTES:
		raise ValueError(
			f"File quá lớn cho OCR ({file_size / 1024 / 1024:.1f}MB). "
			f"Giới hạn: {MAX_OCR_FILE_SIZE_BYTES / 1024 / 1024:.0f}MB"
		)

	if file_size == 0:
		raise ValueError("File rỗng, không thể xử lý OCR")


def _pdf_to_base64_images(file_path, dpi=200, max_pages=MAX_PAGES):
	"""Convert PDF pages to base64-encoded JPEG images using PyMuPDF.

	Uses high-resolution rendering (3x zoom) and CamScanner watermark cropping
	for better OCR accuracy on scanned documents.

	Args:
		file_path: Absolute path to the PDF file.
		dpi: Resolution for rendering (ignored, uses 3x zoom for consistency).
		max_pages: Maximum number of pages to process.

	Returns:
		List of base64-encoded JPEG strings.
	"""
	import fitz  # PyMuPDF
	from PIL import Image

	doc = fitz.open(file_path)
	base64_images = []

	# Use 3x zoom (same as scan_sxkd) for high-res OCR on scanned documents
	mat = fitz.Matrix(3.0, 3.0)

	for page_num in range(min(len(doc), max_pages)):
		page = doc[page_num]
		pix = page.get_pixmap(matrix=mat)

		img = Image.open(io.BytesIO(pix.tobytes("png")))

		# Crop bottom-right CamScanner watermark area (common in scanned PDFs)
		w, h = img.size
		img = img.crop((0, 0, int(w * 0.96), int(h * 0.94)))

		buffer = io.BytesIO()
		img.save(buffer, format="JPEG", quality=90)
		b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
		base64_images.append(b64)

	doc.close()
	return base64_images


def ocr_pdf_to_json(file_path, doc_type="eval"):
	"""Convert a scanned PDF file to structured JSON using OpenAI GPT-4o Vision.

	Uses per-page OCR (like scan_sxkd) for better accuracy on multi-page docs.

	Args:
		file_path: Absolute path to the PDF file.
		doc_type: "eval" for Phiếu đánh giá tái ký, "report" for Báo cáo kết quả công việc.

	Returns:
		String containing the JSON object extracted from the PDF.

	Raises:
		ValueError: If OCR processing fails.
	"""
	import json
	validate_ocr_input(file_path)

	filename = os.path.basename(file_path)
	file_size_mb = os.path.getsize(file_path) / 1024 / 1024

	print(f"[OCR] start: {filename} ({file_size_mb:.1f}MB) via OpenAI Vision ({doc_type})")
	start_time = time.time()

	try:
		print(f"[OCR] converting PDF to images...")
		base64_images = _pdf_to_base64_images(file_path)
		print(f"[OCR] got {len(base64_images)} page(s)")

		if not base64_images:
			raise ValueError("Không thể chuyển PDF thành hình ảnh")

		from cnb_2as.services.openai_client import get_client as _get_client

		client = _get_client()
		model = os.environ.get("OPENAI_MODEL", "gpt-4o")

		# ── Build prompts based on doc_type ──
		system_msg = (
			"You are an expert OCR assistant for Vietnamese corporate HR documents. "
			"Your job is to accurately read and transcribe all text from scanned table images, "
			"returning complete structured JSON. Never skip any cell, always read Vietnamese diacritics carefully."
		)

		if doc_type == "eval":
			ocr_prompt = """Đọc toàn bộ nội dung "Phiếu đánh giá tái ký hợp đồng" trong ảnh này.

QUAN TRỌNG:
- Đọc TOÀN BỘ nội dung trong mỗi ô, KHÔNG ĐƯỢC tóm tắt hay rút gọn
- Mỗi ô có thể chứa nhiều dòng text, phải đọc HẾT tất cả các dòng
- Đặc biệt mục "chi_tieu" trong phần II thường có nội dung rất dài (nhiều bullet points), phải đọc ĐẦY ĐỦ toàn bộ
- Nếu ô có gạch đầu dòng (-), phải giữ nguyên format gạch đầu dòng

Trả về JSON có cấu trúc chính xác như sau:
{
    "thong_tin_nhan_vien": {
        "ho_ten": "...",
        "msnv": "...",
        "vi_tri": "...",
        "phong_ban": "...",
        "ngay_nhan_viec": "...",
        "ngay_bat_dau_hd": "...",
        "ngay_het_han_hd": "..."
    },
    "muc_1_tuan_thu": [
        {
            "noi_dung": "...",
            "muc_do_hoan_thanh": "..."
        }
    ],
    "muc_2_ket_qua_cong_viec": [
        {
            "chi_tieu": "(ĐỌC TOÀN BỘ nội dung trong ô, bao gồm tất cả bullet points, không được bỏ sót hay tóm tắt)",
            "nv_muc_do_hoan_thanh": "...",
            "nv_ty_le_dat": "...",
            "ql_muc_do_hoan_thanh": "...",
            "ql_ty_le_dat": "..."
        }
    ],
    "muc_3_danh_gia_quan_ly": {
        "nhan_xet_chi_tiet": "...",
        "uu_diem": "...",
        "han_che": "...",
        "giai_phap": "..."
    },
    "de_xuat": {
        "quan_ly_truc_tiep": "...",
        "lanh_dao_ban": "..."
    }
}
Đọc KỸ từng ô, KHÔNG bỏ sót bất kỳ chữ nào. Nếu ô trống thì để chuỗi rỗng "". Đọc số % chính xác. GIỮ NGUYÊN toàn bộ nội dung gốc."""
		else:
			# report — dùng cấu trúc tương tự scan_sxkd
			ocr_prompt = """Đọc toàn bộ bảng KẾ HOẠCH SXKD THÁNG / BÁO CÁO KẾT QUẢ THỰC HIỆN trong ảnh này.

Cấu trúc bảng gồm:
- Tiêu đề: "KẾ HOẠCH SXKD THÁNG X VÀ ĐÁNH GIÁ KẾT QUẢ THỰC HIỆN"
- Họ và tên
- Bảng công việc chính: STT | CÁC MẢNG CÔNG TÁC | MÔ TẢ SẢN PHẨM PHẢI HOÀN THÀNH TRONG THÁNG | KẾ HOẠCH THỰC HIỆN (TỶ TRỌNG, KPI, BOD XÉT DUYỆT) | KẾT QUẢ THỰC HIỆN (TỶ LỆ KPI, KẾT QUẢ KPI, BOD XÉT DUYỆT) | LINK SẢN PHẨM ĐÃ UPLOAD
- Dòng TỶ LỆ ĐẠT ở cuối bảng
- Phần NỘI QUY BẮT BUỘC (nếu có): STT | NỘI DUNG | KẾ HOẠCH | KẾT QUẢ | XÁC NHẬN | GHI CHÚ
- Phần CHỈ ĐẠO CỦA BAN LÃNH ĐẠO (nếu có)
- Phần XÉT DUYỆT (HOD, BOD, Ranking) (nếu có)

Trả về JSON với cấu trúc:
{
  "tieu_de": "KẾ HOẠCH SXKD THÁNG X VÀ ĐÁNH GIÁ KẾT QUẢ THỰC HIỆN",
  "ho_ten": "...",
  "cong_viec": [
    {
      "stt": 1,
      "mang_cong_tac": "...",
      "mo_ta_san_pham": "...",
      "ty_trong": "30%",
      "kpi_ke_hoach": "100%",
      "bod_ke_hoach": "",
      "ty_le_kpi_ket_qua": "90%",
      "ket_qua_kpi": "27%",
      "bod_ket_qua": "",
      "link_san_pham": "..."
    }
  ],
  "ty_le_dat_ke_hoach": "100%",
  "ty_le_dat_ket_qua": "86%",
  "noi_quy": [
    {"stt": 1, "noi_dung": "Upload data", "ke_hoach": "100%", "ket_qua": "100%", "xac_nhan": "", "ghi_chu": "..."}
  ],
  "chi_dao": [
    {"stt": 1, "noi_dung": "", "ket_qua": "", "bod_xet_duyet": "", "ghi_chu": ""}
  ],
  "xet_duyet": {
    "hod_y_kien": "",
    "bod_y_kien": "",
    "ranking": ""
  }
}

Đọc KỸ từng ô, không bỏ sót. Nếu ô trống thì để chuỗi rỗng "". Đọc số % chính xác."""

		# ── Per-page OCR (like scan_sxkd) ──
		page_results = []
		total_tokens = 0

		for i, b64_img in enumerate(base64_images):
			print(f"[OCR] processing page {i+1}/{len(base64_images)}...")
			response = client.chat.completions.create(
				model=model,
				messages=[
					{"role": "system", "content": system_msg},
					{"role": "user", "content": [
						{"type": "text", "text": f"Trang {i+1}/{len(base64_images)}:\n{ocr_prompt}"},
						{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}", "detail": "high"}}
					]}
				],
				response_format={"type": "json_object"},
				max_tokens=10000,
				temperature=0,
			)

			raw = response.choices[0].message.content
			try:
				from cnb_2as.services.thu_viec_service import _log_tokens
				_log_tokens(response, label="ocr_service.ocr_pdf_to_json")
			except Exception:
				pass
			if response.usage:
				total_tokens += response.usage.total_tokens

			if raw and raw.strip():
				# Clean markdown wrapping
				md = raw.strip()
				if md.startswith("```json"):
					md = md[7:].strip()
				if md.startswith("```"):
					md = md[3:].strip()
				if md.endswith("```"):
					md = md[:-3].strip()
				try:
					page_results.append(json.loads(md))
				except json.JSONDecodeError:
					print(f"[OCR] page {i+1} returned invalid JSON, skipping")

		if not page_results:
			raise ValueError("OCR không trích xuất được nội dung từ file PDF")

		# ── Merge pages ──
		if doc_type == "eval":
			# For eval: merge all page results into one
			merged = page_results[0]
			for pr in page_results[1:]:
				# Merge muc_1_tuan_thu
				existing_tt = {item.get("noi_dung", "") for item in merged.get("muc_1_tuan_thu", [])}
				for item in pr.get("muc_1_tuan_thu", []):
					if item.get("noi_dung") not in existing_tt:
						merged.setdefault("muc_1_tuan_thu", []).append(item)

				# Merge muc_2_ket_qua
				existing_kq = {item.get("chi_tieu", "") for item in merged.get("muc_2_ket_qua_cong_viec", [])}
				for item in pr.get("muc_2_ket_qua_cong_viec", []):
					if item.get("chi_tieu") not in existing_kq:
						merged.setdefault("muc_2_ket_qua_cong_viec", []).append(item)

				# Fill empty fields from later pages
				for section in ["thong_tin_nhan_vien", "muc_3_danh_gia_quan_ly", "de_xuat"]:
					if isinstance(merged.get(section), dict):
						for k, v in pr.get(section, {}).items():
							if v and not merged[section].get(k):
								merged[section][k] = v
			result_json = json.dumps(merged, ensure_ascii=False)
		else:
			# For report (SXKD): merge like scan_sxkd — combine cong_viec from all pages
			merged = page_results[0]
			for pr in page_results[1:]:
				# Fill empty top-level fields
				if pr.get("tieu_de") and not merged.get("tieu_de"):
					merged["tieu_de"] = pr["tieu_de"]
				if pr.get("ho_ten") and not merged.get("ho_ten"):
					merged["ho_ten"] = pr["ho_ten"]
				if pr.get("ty_le_dat_ke_hoach") and not merged.get("ty_le_dat_ke_hoach"):
					merged["ty_le_dat_ke_hoach"] = pr["ty_le_dat_ke_hoach"]
				if pr.get("ty_le_dat_ket_qua") and not merged.get("ty_le_dat_ket_qua"):
					merged["ty_le_dat_ket_qua"] = pr["ty_le_dat_ket_qua"]

				# Append new STTs
				existing_stt = {cv.get("stt") for cv in merged.get("cong_viec", [])}
				for cv in pr.get("cong_viec", []):
					if cv.get("stt") not in existing_stt:
						merged.setdefault("cong_viec", []).append(cv)
						existing_stt.add(cv["stt"])

				# Nội quy
				existing_nq = {nq.get("stt") for nq in merged.get("noi_quy", [])}
				for nq in pr.get("noi_quy", []):
					if nq.get("stt") not in existing_nq:
						merged.setdefault("noi_quy", []).append(nq)

				# Xét duyệt
				for k in ["hod_y_kien", "bod_y_kien", "ranking"]:
					if pr.get("xet_duyet", {}).get(k) and not merged.get("xet_duyet", {}).get(k):
						merged.setdefault("xet_duyet", {})[k] = pr["xet_duyet"][k]

			# Sort cong_viec by STT
			if merged.get("cong_viec"):
				merged["cong_viec"].sort(key=lambda x: x.get("stt", 999))

			result_json = json.dumps(merged, ensure_ascii=False)

		elapsed = time.time() - start_time
		print(f"[OCR] done: {filename} — {elapsed:.1f}s, {len(result_json)} chars, {total_tokens} tokens, {len(page_results)} page(s)")

		# Cost tracking removed (openai_cost_tracker module not available)

		return result_json

	except ValueError:
		raise
	except Exception as e:
		elapsed = time.time() - start_time
		print(f"[OCR] FAILED: {filename} — {elapsed:.1f}s — {str(e)[:200]}")
		raise ValueError(f"Lỗi OCR (OpenAI): {str(e)[:300]}")

# ============================================================
# Daily Report DOCX with Embedded Images (Vision-based)
# ============================================================

def ocr_daily_report_from_docx(file_path):
	"""Extract daily report data from a DOCX containing embedded screenshots.

	Handles "Tổng hợp báo cáo ngày" files where each day's report is a
	PNG screenshot (Teams/Zalo message) embedded in the Word document.
	Sends each image to GPT-4o Vision and aggregates results.

	Args:
		file_path: Absolute path to the .docx file.

	Returns:
		JSON string with aggregated daily report data across all images.
	"""
	import json
	import zipfile
	import base64
	import re as _re

	if not os.path.exists(file_path):
		raise ValueError(f"File không tồn tại: {file_path}")

	ext = os.path.splitext(file_path)[1].lower()
	if ext not in (".docx", ".doc"):
		raise ValueError(f"ocr_daily_report_from_docx chỉ hỗ trợ .docx, nhận được: {ext}")

	print(f"[OCR-Daily] Trích xuất ảnh từ {os.path.basename(file_path)}...")
	start_time = time.time()

	# Extract embedded images from DOCX zip
	img_entries = []
	with zipfile.ZipFile(file_path) as z:
		media_names = sorted(
			[n for n in z.namelist() if n.startswith("word/media/") and
			 os.path.splitext(n)[1].lower() in (".png", ".jpg", ".jpeg")],
			key=lambda x: int(_re.search(r"\d+", os.path.basename(x)).group())
			if _re.search(r"\d+", os.path.basename(x)) else 0
		)
		for name in media_names:
			with z.open(name) as f:
				data = f.read()
			mime = "image/png" if name.lower().endswith(".png") else "image/jpeg"
			b64 = base64.b64encode(data).decode("utf-8")
			img_entries.append((name, mime, b64))

	if not img_entries:
		raise ValueError("Không tìm thấy ảnh nào trong file DOCX")

	print(f"[OCR-Daily] Tìm thấy {len(img_entries)} ảnh. Bắt đầu Vision API...")

	from cnb_2as.services.openai_client import get_client as _get_client

	client = _get_client()
	model = os.environ.get("OPENAI_MODEL", "gpt-4o")

	SYSTEM_MSG = (
		"Bạn là chuyên gia đọc báo cáo công việc hàng ngày của nhân viên từ screenshot. "
		"Trích xuất đầy đủ và chính xác. Trả về JSON hợp lệ."
	)

	DAILY_PROMPT = """Đọc báo cáo ngày trong ảnh này (screenshot từ Teams/Zalo/email).

Trích xuất:
- Ngày báo cáo (từ "BÁO CÁO DD/MM/YYYY" hoặc timestamp đầu ảnh)
- Số báo cáo (dạng T5/01/21, T5/02/21, v.v.)
- Họ tên người báo cáo
- Từng dòng trong bảng: Hạng mục | Công việc thực hiện | Kết quả
- Pending list (nếu có, để trống nếu không)
- Đổi mới sáng tạo (nếu có, để trống nếu không)

Trả về JSON:
{
  "ngay": "04/05/2026",
  "so_bao_cao": "T5/01/21",
  "nguoi_bao_cao": "[Họ tên người báo cáo]",
  "hang_muc": [
    {"hang_muc": "CT Worksuit AI Assistant", "cong_viec": "...", "ket_qua": "..."},
    {"hang_muc": "Data Platform", "cong_viec": "...", "ket_qua": "..."}
  ],
  "pending_list": "",
  "doi_moi_sang_tao": ""
}"""

	# Send each image to Vision
	bao_cao_list = []
	total_tokens = 0

	for idx, (name, mime, b64) in enumerate(img_entries):
		print(f"[OCR-Daily] Ảnh {idx+1}/{len(img_entries)}: {os.path.basename(name)}")
		try:
			response = client.chat.completions.create(
				model=model,
				messages=[
					{"role": "system", "content": SYSTEM_MSG},
					{
						"role": "user",
						"content": [
							{"type": "text", "text": DAILY_PROMPT},
							{"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}", "detail": "high"}}
						]
					}
				],
				response_format={"type": "json_object"},
				max_tokens=3000,
				temperature=0,
			)
			raw = response.choices[0].message.content
			try:
				from cnb_2as.services.thu_viec_service import _log_tokens
				_log_tokens(response, label="ocr_service.ocr_daily_report_from_docx")
			except Exception:
				pass
			if response.usage:
				total_tokens += response.usage.total_tokens
			if raw and raw.strip():
				try:
					day_data = json.loads(raw)
					bao_cao_list.append(day_data)
				except json.JSONDecodeError:
					print(f"[OCR-Daily] Ảnh {idx+1}: JSON không hợp lệ")
		except Exception as e:
			print(f"[OCR-Daily] Ảnh {idx+1}: Lỗi — {str(e)[:100]}")

	if not bao_cao_list:
		raise ValueError("OCR-Daily không đọc được nội dung nào từ các ảnh")

	# Sort by date
	def _sort_key(item):
		ngay = item.get("ngay", "")
		m = _re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", ngay)
		if m:
			return int(f"{m.group(3)}{int(m.group(2)):02d}{int(m.group(1)):02d}")
		return 0

	bao_cao_list.sort(key=_sort_key)

	ngay_dau = bao_cao_list[0].get("ngay", "") if bao_cao_list else ""
	ngay_cuoi = bao_cao_list[-1].get("ngay", "") if bao_cao_list else ""

	result = {
		"so_ngay_tim_thay": len(bao_cao_list),
		"ngay_dau": ngay_dau,
		"ngay_cuoi": ngay_cuoi,
		"bao_cao": bao_cao_list,
	}

	result_json = json.dumps(result, ensure_ascii=False, indent=2)
	elapsed = time.time() - start_time
	print(f"[OCR-Daily] Xong: {len(bao_cao_list)} ngày, {elapsed:.1f}s, {total_tokens} tokens")

	# Cost tracking removed (openai_cost_tracker module not available)


	return result_json


def ocr_daily_report_from_pdf(file_path, max_pages=25):
	"""Extract daily report data from a scanned PDF by rendering pages as images.

	Used when parse_pdf() returns empty text (image-only / scanned PDF).
	Renders each page via PyMuPDF and sends to GPT-4o Vision API.

	Args:
		file_path: Absolute path to the .pdf file.
		max_pages: Maximum number of pages to process (default 25).

	Returns:
		JSON string with aggregated daily report data across all pages.
	"""
	import json
	import base64
	import re as _re

	try:
		import fitz  # PyMuPDF
	except ImportError:
		raise ImportError("PyMuPDF (fitz) chưa được cài: pip install pymupdf")

	if not os.path.exists(file_path):
		raise ValueError(f"File không tồn tại: {file_path}")

	print(f"[OCR-PDF] Mở PDF {os.path.basename(file_path)}...")
	start_time = time.time()

	doc = fitz.open(file_path)
	n_pages = min(len(doc), max_pages)
	print(f"[OCR-PDF] Tổng {len(doc)} trang, xử lý {n_pages} trang...")

	# Render mỗi trang thành PNG (200 DPI – đủ cho chữ nhỏ và bảng dày)
	img_entries = []
	for page_num in range(n_pages):
		page = doc[page_num]
		mat = fitz.Matrix(200 / 72, 200 / 72)
		pix = page.get_pixmap(matrix=mat)
		img_bytes = pix.tobytes("png")
		b64 = base64.b64encode(img_bytes).decode("utf-8")
		img_entries.append((f"page_{page_num + 1}.png", "image/png", b64))
	doc.close()

	if not img_entries:
		raise ValueError("Không có trang nào trong PDF")

	from cnb_2as.services.openai_client import get_client as _get_client

	client = _get_client()
	model = os.environ.get("OPENAI_MODEL", "gpt-4o")

	SYSTEM_MSG = (
		"Bạn là chuyên gia đọc báo cáo công việc hàng ngày của nhân viên từ tài liệu scan. "
		"Trích xuất đầy đủ và chính xác. Trả về JSON hợp lệ."
	)

	DAILY_PROMPT = """Đọc TẤT CẢ các báo cáo ngày trong trang PDF này. PHẢI TRÍCH XUẤT ĐẦY ĐỦ.

MỘT TRANG CÓ THỂ CHỨA NHIỀU NGÀY BÁO CÁO. Hãy trích xuất TẤT CẢ.

Với mỗi báo cáo ngày, trích xuất:
- Ngày báo cáo (định dạng dd/mm/yyyy - Nếu không thấy ngày, hãy đoán dựa vào context xung quanh hoặc ghi 'Unknown')
- Số báo cáo (dạng T5/01/21, v.v. nếu có)
- Họ tên người báo cáo (Nếu không thấy tên, hãy kiểm tra phần Header hoặc Footer)
- Từng dòng trong bảng: Hạng mục | Công việc thực hiện | Kết quả – PHẢI TRÍCH HẾT, không được bỏ sót (ghi lại đầy đủ text, không viết tắt)
- Pending list (nếu có, để trống nếu không)
- Đổi mới sáng tạo (nếu có, để trống nếu không)

LƯU Ý QUAN TRỌNG:
• Đọc kỹ từng ô trong bảng, kể cả chữ nhỏ và handwriting
• Mỗi hạng mục phải có cong_viec và ket_qua đầy đủ, không được để trống nếu có nội dung
• Nếu 1 hạng mục có nhiều dòng, gộp lại thành 1 object với nội dung đầy đủ
• PHẢI TRÍCH XUẤT MỌI NGÀY BÁO CÁO có trên trang, KHÔNG bỏ qua bất kỳ mục nào
• Nếu bảng bị gãy hoặc cắt trang, hãy tự hiểu context để hoàn thiện nội dung

Trả về JSON với mảng bao_cao chứa TẤT CẢ các ngày tìm được:
{
  "bao_cao": [
    {
      "ngay": "04/05/2026",
      "so_bao_cao": "T5/01/21",
      "nguoi_bao_cao": "[Họ tên người báo cáo]",
      "hang_muc": [
        {"hang_muc": "...", "cong_viec": "...", "ket_qua": "..."}
      ],
      "pending_list": "...",
      "doi_moi_sang_tao": "..."
    }
  ]
}

Nếu trang không chứa báo cáo ngày nào, trả về {"bao_cao": []}."""

	bao_cao_list = []
	total_tokens = 0

	for idx, (name, mime, b64) in enumerate(img_entries):
		print(f"[OCR-PDF] Trang {idx + 1}/{len(img_entries)}: {name}")
		try:
			response = client.chat.completions.create(
				model=model,
				messages=[
					{"role": "system", "content": SYSTEM_MSG},
					{
						"role": "user",
						"content": [
							{"type": "text", "text": DAILY_PROMPT},
							{"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}", "detail": "high"}}
						]
					}
				],
				response_format={"type": "json_object"},
				max_tokens=6000,
				temperature=0,
			)
			raw = response.choices[0].message.content
			try:
				from cnb_2as.services.thu_viec_service import _log_tokens
				_log_tokens(response, label="ocr_service.ocr_daily_report_from_pdf")
			except Exception:
				pass
			if response.usage:
				total_tokens += response.usage.total_tokens
			if raw and raw.strip():
				try:
					page_data = json.loads(raw)
					# Hỗ trợ cả array trong bao_cao[] lẫn object đơn
					page_reports = page_data.get("bao_cao", [])
					if not page_reports and page_data.get("ngay"):
						# Fallback: response là single object
						page_reports = [page_data]
					for day_data in page_reports:
						if day_data.get("ngay"):  # chỉ cần có ngày là đủ
							bao_cao_list.append(day_data)
					print(f"[OCR-PDF] Trang {idx + 1}: {len(page_reports)} ngày → {[d.get('ngay','') for d in page_reports]}")
				except json.JSONDecodeError:
					print(f"[OCR-PDF] Trang {idx + 1}: JSON không hợp lệ")
		except Exception as e:
			print(f"[OCR-PDF] Trang {idx + 1}: Lỗi — {str(e)[:100]}")

	if not bao_cao_list:
		raise ValueError("OCR-PDF không đọc được nội dung báo cáo nào từ các trang")

	# Sắp xếp theo ngày
	def _sort_key(item):
		ngay = item.get("ngay", "")
		m = _re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", ngay)
		if m:
			return int(f"{m.group(3)}{int(m.group(2)):02d}{int(m.group(1)):02d}")
		return 0

	bao_cao_list.sort(key=_sort_key)

	# Dedup theo ngày: nếu cùng ngày có nhiều bản (multi-page), giữ bản có nhiều hang_muc nhất
	seen = {}
	for item in bao_cao_list:
		ngay = item.get("ngay", "").strip()
		if not ngay:
			continue
		if ngay not in seen:
			seen[ngay] = item
		else:
			# Giữ bản có nhiều hang_muc hơn
			if len(item.get("hang_muc") or []) > len(seen[ngay].get("hang_muc") or []):
				seen[ngay] = item
	bao_cao_list = list(seen.values())
	bao_cao_list.sort(key=_sort_key)

	ngay_dau = bao_cao_list[0].get("ngay", "") if bao_cao_list else ""
	ngay_cuoi = bao_cao_list[-1].get("ngay", "") if bao_cao_list else ""

	result = {
		"so_ngay_tim_thay": len(bao_cao_list),
		"ngay_dau": ngay_dau,
		"ngay_cuoi": ngay_cuoi,
		"bao_cao": bao_cao_list,
		"ngay_list": [item.get("ngay", "") for item in bao_cao_list],  # list ngày thật để đối chiếu
	}

	result_json = json.dumps(result, ensure_ascii=False, indent=2)
	elapsed = time.time() - start_time
	print(f"[OCR-PDF] Xong: {len(bao_cao_list)} ngày unique, {elapsed:.1f}s, {total_tokens} tokens")

	return result_json
