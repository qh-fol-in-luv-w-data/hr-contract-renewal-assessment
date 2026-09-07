# CNB 2AS – AI Đánh Giá Nhân Sự

Hệ thống AI hỗ trợ đánh giá **Thử việc / Học việc**, **Tái ký hợp đồng** và **Đề xuất Quản lý** dành cho CT Group.

- Repo: [qh-fol-in-luv-w-data/hr-contract-renewal-assessment](https://github.com/qh-fol-in-luv-w-data/hr-contract-renewal-assessment)
- Frappe app: `cnb_2as`

## Tính năng chính

### Đánh giá Thử việc / Học việc
- 2 chế độ đầu vào: file mặc định (DOCX + XLSX) hoặc file scan (PDF → OCR).
- AI multi-agent chấm điểm 7 tiêu chí 2AS, bảng tỷ trọng năng lực, đề xuất xử lý.
- Đối chiếu báo cáo ngày với phiếu / KPI, gợi ý JD tự sinh.
- Xuất báo cáo PDF đầy đủ.

### Đánh giá Tái ký Hợp đồng
- Nhập file mặc định hoặc scan PDF (OCR → chỉnh sửa → đánh giá lại).
- PDF gồm bảng năng lực, ghi chú tỷ trọng, ngày bắt đầu / kết thúc HĐ.

### Đánh giá Đề xuất Quản lý (HOD / TBP)
- Sub-agent riêng đánh giá đề xuất, mức độ đồng ý và phân tích chi tiết.

### Báo cáo Đánh giá Nhân sự (Batch)
- Upload nhiều phiếu PAI cùng lúc, OCR song song.
- Tự ghép phiếu tự đánh giá ↔ HOD, tính điểm chuẩn.
- Đối chiếu dữ liệu HR, export Excel 2 sheet.

## Yêu cầu

- Frappe Bench v15, Python 3.10+, Node.js 18+.
- `OPENAI_API_KEY` (khuyến nghị GPT-4o).

## Cài đặt

```bash
cd /path/to/frappe-bench
git clone https://github.com/qh-fol-in-luv-w-data/hr-contract-renewal-assessment.git apps/cnb_2as
bench --site <site> install-app cnb_2as
```

Cấu hình OpenAI:

```bash
bench --site <site> set-config openai_api_key "sk-..."
```

Build frontend:

```bash
cd apps/cnb_2as/frontend
npm install
npm run build
cd /path/to/frappe-bench
bench build --app cnb_2as
```

Chạy:

```bash
bench start
```

## Truy cập

| Trang | URL |
|---|---|
| Portal | `/aicenter/2as-employee-assessment/` |
| Đánh giá Thử việc | `.../#/thu-viec` |
| Đánh giá Tái ký | `.../#/tai-ky` |
| Scan OCR (Combined) | `.../#/scan` |
| Báo cáo ĐG Nhân sự | `.../#/bao-cao` |
| Đề xuất Quản lý | `.../#/de-xuat` |

Cần đăng nhập Frappe trước tại `http://localhost:8000/login`.

## Ghi chú

- File scan cần kết nối OpenAI Vision.
- Dev server frontend chạy port 5181, có proxy `vite.config.js` về `localhost:8000`.
- Chi tiết thao tác, xử lý lỗi và refactor: xem `HUONG_DAN_CHAY_HE_THONG.md` và `PLAN_REFACTOR_CNB2AS.md`.

## License

MIT © CT Group DAIT
