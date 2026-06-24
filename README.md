# 🤖 CNB 2AS – AI Đánh Giá Nhân Sự

> Hệ thống AI đánh giá **Thử việc**, **Học việc** và **Tái ký hợp đồng** dành cho CT Group  
> **Kiến trúc**: Frappe App (Python backend) + Vue 3 SPA (Frontend)

---

## ✨ Tính năng

### 📋 Đánh giá Thử việc / Học việc

| Tính năng | Mô tả |
|-----------|-------|
| **2 loại đánh giá** | Chọn **Thử việc** hoặc **Học việc** — toàn bộ UI/PDF tự động đổi theo loại |
| **2 chế độ đầu vào** | **File mặc định** (DOCX + XLSX) hoặc **File Scan** (PDF scan → OCR) |
| **AI 5-Agent Pipeline** | Phân tích đa chiều: KPI, năng lực, hội nhập, đề xuất quản lý, JD gợi ý |
| **7 Tiêu chí 2AS** | Chấm điểm theo 7 tiêu chí đánh giá nội bộ CT Group |
| **Bảng Tỷ Trọng Năng Lực** | AI tự động chấm điểm theo trọng số vị trí |
| **Báo cáo ngày** | Upload báo cáo ngày → đếm ngày deterministic + AI đối chiếu nội dung vs Phiếu/KPI |
| **Đánh giá đề xuất quản lý** | Sub-agent riêng đánh giá đề xuất HOD/TBP, mức độ đồng ý, phân tích chi tiết |
| **Gợi ý JD** | AI tự động sinh Job Description chuẩn theo chức danh/vị trí |
| **Xuất PDF** | Báo cáo PDF đầy đủ (html2pdf.js) – tự xóa trang trắng thừa, page numbers |

### 📄 Đánh giá Tái ký Hợp đồng

| Tính năng | Mô tả |
|-----------|-------|
| **2 chế độ đầu vào** | **File mặc định** hoặc **File Scan** (PDF → OCR → chỉnh sửa → đánh giá) |
| **Scan OCR persist** | Sau đánh giá, form OCR vẫn hiển thị để chỉnh sửa & đánh giá lại |
| **Bảng năng lực + ghi chú** | PDF bao gồm bảng điểm năng lực với ghi chú tỷ trọng |
| **PDF layout chuẩn** | Header bảng + nội dung không bị tách trang, có ngày BĐ/KT hợp đồng |

### 📊 Báo cáo Đánh giá Nhân sự (Batch)

| Tính năng | Mô tả |
|-----------|-------|
| **Upload batch PDF** | Upload nhiều file PAI PDF (NV tự đánh giá + HOD) cùng lúc |
| **OCR song song** | GPT-4o Vision OCR đồng thời tối đa 6 file (ThreadPoolExecutor) |
| **Map NV ↔ HOD** | Tự động ghép phiếu tự đánh giá và HOD theo fuzzy name matching |
| **Tính điểm chuẩn** | Tổng raw (A+B+C) ÷ 75 × 100 (NV) hoặc ÷ 80 × 100 (HOD) |
| **AI Phân tích** | Nhận xét chênh lệch điểm, đề xuất HOD, lọt khung, tự khai vs HR |
| **Đối chiếu HR** | Upload file Excel HR → so sánh NV tự khai vs dữ liệu HR xác nhận |
| **Preview & chỉnh sửa** | Xem kết quả OCR, sửa trực tiếp trước khi xuất |
| **Export Excel 2 sheet** | Sheet 1: bảng tổng hợp toàn bộ NV; Sheet 2: danh sách CBNV chênh lệch vs HR |

### 🔍 Scan OCR (Chung)

| Tính năng | Mô tả |
|-----------|-------|
| **ScanCombined** | Upload PDF scan phiếu + SXKD → OpenAI Vision OCR |
| **Chỉnh sửa trước đánh giá** | OCR kết quả hiển thị editable form → user review → xác nhận đánh giá |
| **Hỗ trợ đa định dạng** | PDF, DOCX, XLSX, ảnh scan |

---

## 📁 Cấu trúc thư mục

```
cnb_2as/
├── frontend/                            # Vue 3 SPA (Vite)
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Portal.vue               # Trang chủ chọn loại đánh giá
│   │   │   ├── ThuViec.vue              # Đánh giá thử việc / học việc
│   │   │   ├── TaiKy.vue                # Đánh giá tái ký hợp đồng
│   │   │   ├── ScanCombined.vue         # Scan + OCR review (phiếu + SXKD)
│   │   │   ├── BaoCao.vue               # Báo cáo đánh giá nhân sự (batch OCR + Excel)
│   │   │   ├── PersonCard.vue           # Card chi tiết từng nhân viên
│   │   │   ├── ScanPhieu.vue            # Scan phiếu đánh giá riêng
│   │   │   └── ScanSXKD.vue             # Scan SXKD riêng
│   │   ├── components/
│   │   │   └── JdGoiY.vue               # Component hiển thị gợi ý JD
│   │   ├── store.js                     # Global state + i18n (VI/EN)
│   │   ├── main.js                      # Vue Router setup
│   │   └── App.vue
│   ├── package.json
│   └── vite.config.js
│
├── cnb_2as/                             # Frappe Python App
│   ├── api/
│   │   ├── thu_viec.py                  # API: review_files, review_from_scan, chat_review
│   │   ├── evaluation.py               # API: đánh giá tái ký
│   │   ├── scan_phieu.py               # API: OCR scan phiếu
│   │   ├── scan_sxkd.py                # API: OCR scan SXKD
│   │   └── bao_cao_danh_gia.py         # API: báo cáo đánh giá nhân sự batch
│   ├── services/
│   │   ├── agents.py                    # Multi-agent pipeline (manager proposal, etc.)
│   │   ├── openai_client.py             # OpenAI client wrapper
│   │   ├── document_parser.py           # Parse daily report (DOCX/XLSX/PDF/image)
│   │   ├── thu_viec_parsers.py          # Parse phiếu DOCX + Excel KPI chi tiết
│   │   ├── thu_viec_service.py          # Business logic thử việc (prompts, filters)
│   │   ├── thu_viec_pdf.py              # PDF generation thử việc
│   │   ├── ocr_service.py               # OCR via OpenAI Vision
│   │   ├── ocr_report_to_excel.py       # Chuyển OCR report → Excel format
│   │   ├── scan_service.py              # Scan flow orchestration
│   │   ├── scan_readers.py              # Đọc & parse scan PDF
│   │   ├── pdf_generator.py             # PDF generation tái ký
│   │   ├── bao_cao_service.py           # OCR batch + map + AI overview + Excel export
│   │   ├── validators.py                # Input validation & E1 check
│   │   └── prompts/
│   │       ├── __init__.py              # Export shared prompts
│   │       ├── eval_prompts.py          # Prompts cho đánh giá tái ký
│   │       ├── review_prompts.py        # Prompts cho đánh giá thử việc
│   │       ├── scan_prompts.py          # Prompts cho OCR scan
│   │       └── bao_cao_prompts.py       # Prompts cho báo cáo đánh giá nhân sự
│   ├── hooks.py
│   ├── modules.txt
│   └── public/frontend/                 # ⚡ Vite build output (auto-generated)
│
├── note/
│   └── update-code.md                   # Ghi chú yêu cầu cập nhật
├── pyproject.toml
└── README.md
```

---

## 🔧 Yêu cầu hệ thống

| Thành phần | Version |
|-----------|---------|
| **Python** | ≥ 3.10 |
| **Node.js** | ≥ 18 |
| **Frappe Bench** | ≥ 5.x |
| **OpenAI API Key** | GPT-4o (khuyến nghị) |

---

## 🚀 Cài đặt & Chạy

### Bước 1: Chuẩn bị Frappe Bench

Nếu chưa có Frappe Bench, cài đặt theo [hướng dẫn chính thức](https://frappeframework.com/docs/user/en/installation):

```bash
pip install frappe-bench
bench init frappe-bench --frappe-branch version-15
cd frappe-bench
bench new-site mysite.localhost
```

### Bước 2: Clone và cài app

```bash
cd /path/to/frappe-bench

# Clone repo vào thư mục apps
git clone https://github.com/CTGroup-DAIT/2as-employee-assessment.git apps/cnb_2as

# Cài app vào site
bench --site mysite.localhost install-app cnb_2as
```

### Bước 3: Cài Python dependencies

```bash
cd /path/to/frappe-bench

# Kích hoạt virtualenv của bench
source env/bin/activate

# Cài các thư viện cần thiết
pip install openai python-docx openpyxl pypdf PyMuPDF python-dotenv
```

### Bước 4: Cấu hình OpenAI API Key

Tạo file `.env` tại thư mục app:

```bash
# Cách 1: File .env (khuyến nghị)
cat > apps/cnb_2as/cnb_2as/.env << 'EOF'
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-4o
EOF

# Cách 2: Qua bench config
bench --site mysite.localhost set-config openai_api_key "sk-xxxxxxxxxxxxxxxxxxxxxxxx"
```

### Bước 5: Build Frontend

```bash
cd /path/to/frappe-bench/apps/cnb_2as/frontend

# Cài Node dependencies
npm install

# Build production → output vào cnb_2as/public/frontend/
npm run build

# Về bench root và build static assets
cd /path/to/frappe-bench
bench build --app cnb_2as
```

### Bước 6: Chạy ứng dụng

```bash
cd /path/to/frappe-bench
bench start
```

---

## 🌐 Truy cập ứng dụng

> ⚠️ **Lưu ý**: Cần đăng nhập Frappe trước tại `http://localhost:8000/login`

| Trang | URL |
|-------|-----|
| Portal (Trang chủ) | `http://localhost:8000/assets/cnb_2as/frontend/index.html` |
| Đánh giá Thử việc/Học việc | `http://localhost:8000/assets/cnb_2as/frontend/index.html#/thu-viec` |
| Đánh giá Tái ký | `http://localhost:8000/assets/cnb_2as/frontend/index.html#/tai-ky` |
| Scan OCR (Combined) | `http://localhost:8000/assets/cnb_2as/frontend/index.html#/scan` |
| Báo cáo ĐG Nhân sự | `http://localhost:8000/assets/cnb_2as/frontend/index.html#/bao-cao` |
| Đánh giá Đề xuất QM/HOD | `http://localhost:8000/assets/cnb_2as/frontend/index.html#/de-xuat` |

> **Dev mode** (Vite dev server): `http://localhost:5181`

---

## 🏗️ Kiến trúc AI Pipeline

### Đánh giá Thử việc / Học việc

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Input                               │
│  File mặc định: DOCX + XLSX          File Scan: PDF → OCR       │
│  (review_files API)                   (review_from_scan API)    │
└─────────────────┬───────────────────────────┬───────────────────┘
                  │                           │
                  ▼                           ▼
         ┌────────────────────────────────────────────┐
         │         Main AI Review (GPT-4o)            │
         │  • Phân tích phiếu + KPI                   │
         │  • 7 Tiêu chí 2AS                          │
         │  • Bảng tỷ trọng năng lực                  │
         │  • Đề xuất xử lý                           │
         │  • Vấn đề + Ưu điểm                        │
         └────────────────┬───────────────────────────┘
                          │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
    ┌──────────────┐ ┌──────────┐ ┌──────────────┐
    │ Báo cáo ngày │ │ Đánh giá │ │  JD Gợi ý    │
    │ Deterministic│ │ Đề xuất  │ │ (GPT-4o)     │
    │ + CrossCheck │ │ Quản lý  │ │              │
    │   (GPT-4o)   │ │ (GPT-4o) │ │              │
    └──────────────┘ └──────────┘ └──────────────┘
```

### Kết quả trả về (cả 2 mode)

| Field | Mô tả |
|-------|-------|
| `status` | ĐẠT / CHƯA ĐẠT |
| `tong_quan` | Tổng quan nhận xét |
| `van_de` | Danh sách vấn đề cần bổ sung |
| `uu_diem` | Danh sách điểm tốt |
| `phan_tich_2as` | 7 tiêu chí đánh giá 2AS |
| `bang_ty_trong` | Bảng tỷ trọng năng lực + điểm |
| `de_xuat_xu_ly` | Đề xuất xử lý (ký HĐ / gia hạn / ...) |
| `bao_cao_ngay` | Thống kê + đối chiếu báo cáo ngày |
| `danh_gia_quan_ly` | Đánh giá đề xuất HOD/TBP |
| `jd_goi_y` | Gợi ý Job Description theo vị trí |
| `canh_bao_han` | Cảnh báo thời hạn hồ sơ |
| `xlsx_kpi` | Bảng KPI chi tiết (minh chứng, tỷ lệ) |

---

## 🔄 Development Workflow

### Chỉnh sửa Frontend (Vue)

```bash
cd /path/to/frappe-bench/apps/cnb_2as/frontend

# Chạy dev server với Hot Module Reload (port 5181)
npm run dev

# Khi done, build production
npm run build
cd /path/to/frappe-bench
bench build --app cnb_2as
```

### Chỉnh sửa Backend (Python)

Sửa trực tiếp các file trong `cnb_2as/api/` hoặc `cnb_2as/services/`.  
Frappe tự động reload khi `bench start` đang chạy (dev mode).

### Kiểm tra syntax Python

```bash
python3 -m py_compile cnb_2as/api/thu_viec.py
python3 -m py_compile cnb_2as/services/agents.py
python3 -m py_compile cnb_2as/services/prompts/eval_prompts.py
```

---

## ⚙️ Cấu hình nâng cao

### Thay đổi AI model

Trong file `.env` hoặc environment variables:

```bash
OPENAI_MODEL=gpt-4o          # Mặc định
OPENAI_MODEL=gpt-4o-mini     # Tiết kiệm chi phí
```

### Timeout và retry

Trong `cnb_2as/services/openai_client.py`:

```python
MAX_RETRIES = 3
TIMEOUT = 120  # seconds
```

---

## 📦 Dependencies

### Python (Backend)

| Package | Mục đích |
|---------|----------|
| `openai` | Gọi API OpenAI (GPT-4o, Vision) |
| `python-docx` | Parse file Word (.docx) |
| `openpyxl` | Parse file Excel (.xlsx) |
| `pypdf` | Parse file PDF |
| `PyMuPDF` | OCR / đọc PDF nâng cao |
| `python-dotenv` | Load biến môi trường từ .env |

### Node.js (Frontend)

| Package | Mục đích |
|---------|----------|
| `vue` (3.x) | Framework UI |
| `vue-router` | Routing SPA |
| `vite` | Build tool |
| `@vitejs/plugin-vue` | Vue plugin cho Vite |
| `html2pdf.js` | Xuất PDF client-side (CDN) |

---

## 🐛 Troubleshooting

### Lỗi "openai_api_key not configured"

```bash
# Kiểm tra file .env
cat apps/cnb_2as/cnb_2as/.env

# Hoặc set qua bench
bench --site mysite.localhost set-config openai_api_key "sk-..."
bench restart
```

### Lỗi CORS khi chạy dev

Trong `vite.config.js`, proxy đã được cấu hình sẵn về `localhost:8000`.  
Đảm bảo `bench start` đang chạy trước khi chạy `npm run dev`.

### Build frontend thất bại

```bash
rm -rf frontend/node_modules frontend/.vite
cd frontend && npm install && npm run build
```

### Backend code không reload

```bash
# Frappe auto-reload khi detect file changes
# Nếu không tự reload, restart bench:
# Ctrl+C bench start → chạy lại bench start

# Clear cache nếu cần:
bench --site mysite.localhost clear-cache
```

### PDF xuất bị lỗi layout

- Đảm bảo kết nối internet (html2pdf.js load từ CDN)
- Thử hard refresh (Ctrl+Shift+R) trình duyệt
- Kiểm tra browser console cho lỗi JavaScript

---

## 📄 License

MIT © CT Group DAIT
