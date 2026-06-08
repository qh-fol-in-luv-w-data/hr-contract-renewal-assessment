# CNB 2AS – AI Đánh Giá Nhân Sự

Hệ thống sử dụng AI (OpenAI) để đánh giá **Thử việc** và **Tái ký hợp đồng** cho nhân viên.

> **Kiến trúc**: Frappe App (Python backend) + Vue 3 SPA (Frontend tĩnh)

---

## 📁 Cấu trúc thư mục

```
cnb_2as/
├── frontend/                    # Vue 3 SPA (Vite)
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Portal.vue       # Trang chủ chọn loại đánh giá
│   │   │   ├── ThuViec.vue      # Đánh giá thử việc
│   │   │   └── TaiKy.vue        # Đánh giá tái ký hợp đồng
│   │   ├── main.js              # Vue Router (Hash History)
│   │   └── App.vue              # Layout chính
│   ├── index.html               # Entry point (Vite tự inject JS/CSS)
│   ├── vite.config.js
│   └── package.json
│
├── cnb_2as/                     # Frappe Python App
│   ├── api/
│   │   ├── evaluation.py        # API đánh giá tái ký
│   │   └── thu_viec.py          # API đánh giá thử việc
│   ├── services/
│   │   ├── agents.py            # AI Agent logic
│   │   ├── openai_client.py     # OpenAI client wrapper
│   │   ├── document_parser.py   # Parse DOCX/XLSX/PDF
│   │   └── pdf_generator.py     # Tạo PDF báo cáo (ReportLab)
│   ├── hooks.py
│   └── public/frontend/         # ⚡ Build output (Vite → đây)
│       ├── index.html            #    Tự động có hash JS/CSS mới
│       └── assets/               #    JS/CSS đã minify
│
├── pyproject.toml
└── README.md
```

---

## 🚀 Hướng dẫn cài đặt

### Yêu cầu

- **Frappe Bench** đã được cài đặt ([hướng dẫn](https://frappeframework.com/docs/user/en/installation))
- **Python** >= 3.10
- **Node.js** >= 18
- **OpenAI API Key** (để chạy AI đánh giá)

### Bước 1: Cài app vào Frappe Bench

```bash
cd /path/to/frappe-bench

# Clone và cài app
bench get-app https://github.com/<your-org>/cnb_2as.git --branch develop
bench --site <your-site> install-app cnb_2as
```

### Bước 2: Cài thư viện Python phụ thuộc

```bash
cd /path/to/frappe-bench

# Kích hoạt môi trường ảo của bench
source env/bin/activate

# Cài các package cần thiết
pip install openai python-dotenv python-docx openpyxl pypdf reportlab PyMuPDF
```

### Bước 3: Cấu hình OpenAI API Key

Cấu hình trực tiếp vào `site_config.json` của site bạn đang dùng:

```bash
cd /path/to/frappe-bench
bench --site <your-site> set-config openai_api_key "sk-xxxxxxxxxxxxxxxxxxxxxxxx"
```

### Bước 4: Build Frontend

```bash
# Di chuyển đến thư mục frontend của app
cd /path/to/frappe-bench/apps/cnb_2as/frontend

# Cài Node dependencies (Khuyến nghị dùng yarn)
yarn install

# Build production (output → cnb_2as/public/frontend/)
yarn build

# Quay về bench root và build static assets cho Frappe
cd /path/to/frappe-bench
bench build --app cnb_2as
```

### Bước 5: Chạy

```bash
cd /path/to/frappe-bench
bench start
```

---

## 🌐 Truy cập ứng dụng

Frontend là một SPA tĩnh, truy cập trực tiếp qua đường dẫn file:

| Trang | URL |
|-------|-----|
| Portal (Trang chủ) | `http://localhost:8000/assets/cnb_2as/frontend/index.html` |
| Đánh giá Thử việc | `http://localhost:8000/assets/cnb_2as/frontend/index.html#/thu-viec` |
| Đánh giá Tái ký | `http://localhost:8000/assets/cnb_2as/frontend/index.html#/tai-ky` |

> **Lưu ý**: Bạn cần đăng nhập vào Frappe trước (ở `/login`) để các API call có quyền truy cập.

---

## 🔄 Quy trình phát triển (Development)

### Sửa Frontend (Vue)

```bash
cd /path/to/frappe-bench/apps/cnb_2as/frontend

# Chạy dev server với Hot Reload (port 5180)
yarn dev
```

Khi dev xong, build lại:

```bash
yarn build
cd /path/to/frappe-bench
bench build --app cnb_2as
```

> **Quan trọng**: Vite tự động inject hash JS/CSS mới vào `index.html` mỗi lần build.
> Bạn KHÔNG cần sửa hash bằng tay ở bất kỳ file nào.

### Sửa Backend (Python)

Sửa trực tiếp các file trong `cnb_2as/api/` hoặc `cnb_2as/services/`.
Frappe sẽ tự động reload khi `bench start` đang chạy.

---

## 📦 Thư viện phụ thuộc

### Python (Backend)
| Package | Mục đích |
|---------|----------|
| `openai` | Gọi API OpenAI (GPT) |
| `python-dotenv` | Đọc biến môi trường từ `.env` |
| `python-docx` | Parse file Word (.docx) |
| `openpyxl` | Parse file Excel (.xlsx) |
| `pypdf` | Parse file PDF |
| `reportlab` | Tạo file PDF báo cáo |

### Node.js (Frontend)
| Package | Mục đích |
|---------|----------|
| `vue` | Framework UI |
| `vue-router` | Routing SPA |
| `vite` | Build tool |
| `@vitejs/plugin-vue` | Vite plugin cho Vue |

---

## 📄 License

MIT
