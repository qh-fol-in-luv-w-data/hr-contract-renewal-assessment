# 🤖 CNB 2AS – AI Đánh Giá Nhân Sự

> Hệ thống AI đánh giá **Thử việc**, **Học việc** và **Tái ký hợp đồng** dành cho CT Group  
> **Kiến trúc**: Frappe App (Python backend) + Vue 3 SPA (Frontend)

---

## ✨ Tính năng

| Module | Mô tả |
|--------|-------|
| **Đánh giá Thử việc / Học việc** | Upload phiếu đánh giá (DOCX) + báo cáo KPI (XLSX/PDF) → AI phân tích 5 agents, chấm điểm, khuyến nghị |
| **Đánh giá Tái ký HĐ** | Upload phiếu tái ký + báo cáo công việc → AI đánh giá điều kiện hợp đồng, đề xuất nhân sự |
| **Scan bằng OCR** | Chụp/upload PDF scan → OpenAI Vision OCR → review → đánh giá AI |
| **Báo cáo ngày** | Tùy chọn upload báo cáo ngày → AI đối chiếu, thống kê tần suất báo cáo |
| **Xuất PDF** | Xuất báo cáo PDF đầy đủ client-side (html2pdf.js) |
| **Gợi ý JD** | AI tự động sinh Job Description chuẩn theo chức danh |

---

## 📁 Cấu trúc thư mục

```
2as-employee-assessment/
├── frontend/                        # Vue 3 SPA (Vite)
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Portal.vue           # Trang chủ chọn loại đánh giá
│   │   │   ├── ThuViec.vue          # Đánh giá thử việc / học việc
│   │   │   ├── TaiKy.vue            # Đánh giá tái ký hợp đồng
│   │   │   └── ScanCombined.vue     # Scan + OCR review
│   │   ├── components/
│   │   │   └── JdGoiY.vue           # Component hiển thị gợi ý JD
│   │   ├── store.js                 # Global state (ngôn ngữ, config)
│   │   ├── main.js                  # Vue Router setup
│   │   └── App.vue
│   ├── package.json
│   └── vite.config.js
│
├── cnb_2as/                         # Frappe Python App
│   ├── api/
│   │   ├── evaluation.py            # API endpoints đánh giá tái ký
│   │   ├── thu_viec.py              # API endpoints đánh giá thử việc
│   │   └── scan_phieu.py            # API OCR scan
│   ├── services/
│   │   ├── agents.py                # 5+N AI Agent pipeline (OpenAI)
│   │   ├── openai_client.py         # OpenAI client wrapper
│   │   ├── document_parser.py       # Parse DOCX / XLSX / PDF
│   │   ├── ocr_service.py           # OCR via OpenAI Vision
│   │   ├── scan_service.py          # Scan flow orchestration
│   │   ├── thu_viec_service.py      # Thử việc evaluation logic
│   │   ├── validators.py            # Input validation
│   │   └── prompts/
│   │       ├── eval_prompts.py      # Prompts cho đánh giá tái ký
│   │       ├── review_prompts.py    # Prompts cho đánh giá thử việc
│   │       └── scan_prompts.py      # Prompts cho OCR scan
│   ├── hooks.py
│   ├── modules.txt
│   └── public/frontend/             # ⚡ Vite build output (auto-generated)
│
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
pip install openai python-docx openpyxl pypdf PyMuPDF
```

### Bước 4: Cấu hình OpenAI API Key

```bash
cd /path/to/frappe-bench

# Cách 1: Qua bench config (khuyến nghị)
bench --site mysite.localhost set-config openai_api_key "sk-xxxxxxxxxxxxxxxxxxxxxxxx"

# Cách 2: Sửa trực tiếp file
nano sites/mysite.localhost/site_config.json
# Thêm: "openai_api_key": "sk-xxxxxxxxxxxxxxxxxxxxxxxx"
```

### Bước 5: Build Frontend

```bash
cd /path/to/frappe-bench/apps/cnb_2as/frontend

# Cài Node dependencies
npm install
# hoặc: yarn install

# Build production → output vào cnb_2as/public/frontend/
npm run build
# hoặc: yarn build

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
| Đánh giá Thử việc | `http://localhost:8000/assets/cnb_2as/frontend/index.html#/thu-viec` |
| Đánh giá Tái ký | `http://localhost:8000/assets/cnb_2as/frontend/index.html#/tai-ky` |

> **Dev mode** (Vite dev server): `http://localhost:5181`

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
Frappe tự động reload khi `bench start` đang chạy.

### Kiểm tra syntax Python

```bash
python3 -m py_compile cnb_2as/services/agents.py
python3 -m py_compile cnb_2as/services/prompts/eval_prompts.py
```

---

## ⚙️ Cấu hình nâng cao

### Thay đổi AI model

Trong `cnb_2as/services/openai_client.py`, tìm và sửa:

```python
MODEL = "gpt-4o"        # Đổi thành gpt-4o-mini để tiết kiệm chi phí
```

### Timeout và retry

Trong `openai_client.py`:

```python
MAX_RETRIES = 3
TIMEOUT = 120  # seconds
```

---

## 📦 Dependencies

### Python (Backend)

| Package | Mục đích |
|---------|----------|
| `openai` | Gọi API OpenAI (GPT-4o) |
| `python-docx` | Parse file Word (.docx) |
| `openpyxl` | Parse file Excel (.xlsx) |
| `pypdf` | Parse file PDF |
| `PyMuPDF` | OCR/đọc PDF nâng cao |

### Node.js (Frontend)

| Package | Mục đích |
|---------|----------|
| `vue` | Framework UI |
| `vue-router` | Routing SPA |
| `vite` | Build tool |
| `@vitejs/plugin-vue` | Vue plugin cho Vite |
| `html2pdf.js` | Xuất PDF client-side (CDN) |

---

## 🐛 Troubleshooting

### Lỗi "openai_api_key not configured"

```bash
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

### Frappe không nhận API mới

```bash
bench --site mysite.localhost clear-cache
bench restart
```

---

## 📄 License

MIT © CT Group DAIT
