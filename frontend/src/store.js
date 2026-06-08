import { reactive, watch } from 'vue'

const savedTheme = localStorage.getItem('cnb_theme') || 'dark'
const savedLang = localStorage.getItem('cnb_lang') || 'vi'

export const store = reactive({
  theme: savedTheme, // 'dark' | 'light'
  lang: savedLang, // 'vi' | 'en'
})

watch(() => store.theme, (val) => {
  localStorage.setItem('cnb_theme', val)
  document.body.className = val === 'light' ? 'theme-light' : 'theme-dark'
})

watch(() => store.lang, (val) => {
  localStorage.setItem('cnb_lang', val)
})

// Initial setup
document.body.className = store.theme === 'light' ? 'theme-light' : 'theme-dark'

export const dict = {
  vi: {
    portal_title: 'CỔNG THÔNG TIN NHÂN SỰ',
    portal_sub: 'Hệ thống AI đánh giá nhân sự – CT Group',
    thuviec_title: 'Đánh giá Hoàn thành Thử việc',
    thuviec_desc: 'AI kiểm tra phiếu đánh giá và bảng KPI, phát hiện thiếu sót, yêu cầu bổ sung cho đến khi hồ sơ hoàn thiện.',
    taiky_title: 'Đánh giá Tái ký Hợp đồng',
    taiky_desc: 'Tự động trích xuất bằng chứng từ báo cáo, chấm điểm năng lực theo trọng số và đưa ra khuyến nghị tái ký hợp đồng.',
    scan_title: 'Đánh giá từ Phiếu Scan',
    scan_desc: 'Upload phiếu đánh giá dạng PDF/DOCX/HTML. AI đọc, trích xuất thông tin và phân tích hồ sơ theo 6 tiêu chí CNB.',
    open_system: 'Mở hệ thống',
    
    back_portal: 'Về Portal',
    eval_docs: 'Hồ sơ đánh giá',
    file_docx_title: 'Phiếu đánh giá',
    file_xlsx_title: 'Bảng KPI',
    file_docx_desc: 'Định dạng hỗ trợ: .docx, .pdf',
    file_xlsx_desc: 'Định dạng hỗ trợ: .xlsx, .pdf',
    file_eval_title: 'Phiếu đánh giá tái ký',
    file_eval_desc: 'Định dạng hỗ trợ: .docx, .pdf',
    file_report_title: 'Báo cáo kết quả công việc',
    file_report_desc: 'Định dạng hỗ trợ: .xlsx, .pdf',
    click_to_select: 'Click để chọn file',
    need_2_files: 'Cần upload đủ 2 file',
    analyze_btn: 'Phân tích ngay',
    analyzing: 'Đang phân tích...',
    
    result: 'Kết quả',
    export_pdf: 'Xuất báo cáo PDF',
    issues: 'Vấn đề',
    kpi_pass: 'KPI đạt',
    kpi_miss: 'Thiếu MC',
    score_total: 'Điểm tổng',
    competency: 'Năng lực',
    evidence: 'Bằng chứng',
    progress: 'Tiến trình',
    
    welcome_tv: 'AI Đánh Giá Thử Việc',
    welcome_tv_desc: 'Upload phiếu đánh giá (.docx) và bảng KPI (.xlsx) ở thanh bên trái, bấm Phân tích ngay để AI kiểm tra hồ sơ.',
    welcome_tk: 'AI Đánh Giá Tái Ký Hợp Đồng',
    welcome_tk_desc: 'Upload phiếu đánh giá tái ký và báo cáo kết quả công việc ở thanh bên trái, bấm Phân tích ngay để AI chấm điểm.',
    
    tv_f1: 'Kiểm tra câu từ, ngữ nghĩa, số liệu',
    tv_f2: 'Kiểm tra KPI, tỷ lệ, link minh chứng',
    tv_f3: 'Phân tích KPI theo tuần (1→8)',
    tk_f1: 'Trích xuất bằng chứng tự động',
    tk_f2: 'Chấm điểm năng lực theo trọng số',
    tk_f3: 'Khuyến nghị tái ký hợp đồng',
    
    light_mode: 'Chế độ Sáng',
    dark_mode: 'Chế độ Tối',
    vietnamese: 'Tiếng Việt',
    english: 'English',

    // OCR Scan
    input_mode: 'Loại file đầu vào',
    mode_default: 'File mặc định (.docx/.xlsx)',
    mode_scan: 'File scan (PDF)',
    ocr_processing: 'Đang phân tích file scan...',
    ocr_complete: 'OCR hoàn tất',
    review_ocr: 'Kiểm tra nội dung OCR',
    tab_eval: 'Phiếu đánh giá tái ký',
    tab_report: 'Bảng kết quả công việc',
    confirm_evaluate: 'Xác nhận & Đánh giá',
    edit_content: 'Chỉnh sửa nội dung',
    field_missing: 'Thiếu thông tin',
    field_ok: 'Đầy đủ',

    // Scan mode (ThuViec)
    scan_analyze_btn: 'Scan & Phân tích',
    scan_analyzing: 'GPT-4o đang đọc phiếu & KH SXKD song song...',
    scan_result: 'Kết quả scan',
    scan_phieu: 'Phiếu đánh giá',
    scan_sxkd: 'KH SXKD',
    scan_send_eval: '→ Gửi vào Đánh giá',
    scan_sending: 'Đang phân tích...',
    scan_reset: '↩ Scan lại',
    scan_phieu_tab: 'Phiếu Đánh Giá',
    scan_sxkd_tab: 'KH SXKD',
    scan_task_phieu: 'Scan phiếu đánh giá',
    scan_task_sxkd: 'Scan KH SXKD',
    scan_pdf_hint: 'PDF scan',

    // Document Warnings
    doc_warnings: 'Cảnh báo hồ sơ',
    doc_complete: 'Hồ sơ đầy đủ',
    doc_incomplete: 'Hồ sơ cần bổ sung',

    // Proposal & Urgency
    proposal_level: 'Mức độ đề xuất',
    urgency_level: 'Mức độ khẩn cấp',
    next_steps: 'Bước xử lý tiếp theo',
    priority: 'Độ ưu tiên',
    responsible: 'Trách nhiệm',
  },
  en: {
    portal_title: 'HR INFORMATION PORTAL',
    portal_sub: 'AI Personnel Evaluation System – CT Group',
    thuviec_title: 'Probation Completion Evaluation',
    thuviec_desc: 'AI checks evaluation forms and KPI tables, detects omissions, and requests updates until the profile is complete.',
    taiky_title: 'Contract Renewal Evaluation',
    taiky_desc: 'Automatically extracts evidence from reports, scores competencies by weight, and provides renewal recommendations.',
    scan_title: 'Evaluation from Scanned Form',
    scan_desc: 'Upload evaluation forms as PDF/DOCX/HTML. AI reads, extracts info and analyzes the profile against 6 CNB criteria.',
    open_system: 'Open System',
    
    back_portal: 'Back to Portal',
    eval_docs: 'Evaluation Documents',
    file_docx_title: 'Evaluation Form',
    file_xlsx_title: 'KPI Table',
    file_docx_desc: 'Supported formats: .docx, .pdf',
    file_xlsx_desc: 'Supported formats: .xlsx, .pdf',
    file_eval_title: 'Renewal Evaluation Form',
    file_eval_desc: 'Supported formats: .docx, .pdf',
    file_report_title: 'Work Result Report',
    file_report_desc: 'Supported formats: .xlsx, .pdf',
    click_to_select: 'Click to select file',
    need_2_files: '2 files are required',
    analyze_btn: 'Analyze Now',
    analyzing: 'Analyzing...',
    
    result: 'Results',
    export_pdf: 'Export PDF Report',
    issues: 'Issues',
    kpi_pass: 'KPI Pass',
    kpi_miss: 'Missing Ev.',
    score_total: 'Total Score',
    competency: 'Competency',
    evidence: 'Evidence',
    progress: 'Progress',
    
    welcome_tv: 'AI Probation Evaluation',
    welcome_tv_desc: 'Upload the evaluation form (.docx) and KPI table (.xlsx) on the left sidebar, click Analyze Now to let AI review.',
    welcome_tk: 'AI Contract Renewal Evaluation',
    welcome_tk_desc: 'Upload the renewal form and work report on the left sidebar, click Analyze Now to let AI score.',
    
    tv_f1: 'Check wording, semantics, metrics',
    tv_f2: 'Check KPIs, ratios, evidence links',
    tv_f3: 'Analyze KPIs weekly (1→8)',
    tk_f1: 'Automatic evidence extraction',
    tk_f2: 'Weighted competency scoring',
    tk_f3: 'Contract renewal recommendations',
    
    light_mode: 'Light Mode',
    dark_mode: 'Dark Mode',
    vietnamese: 'Tiếng Việt',
    english: 'English',

    // OCR Scan
    input_mode: 'Input file type',
    mode_default: 'Default files (.docx/.xlsx)',
    mode_scan: 'Scanned files (PDF)',
    ocr_processing: 'Analyzing scanned files...',
    ocr_complete: 'OCR completed',
    review_ocr: 'Review OCR content',
    tab_eval: 'Renewal Evaluation Form',
    tab_report: 'Work Result Report',
    confirm_evaluate: 'Confirm & Evaluate',
    edit_content: 'Edit content',
    field_missing: 'Missing info',
    field_ok: 'Complete',

    // Scan mode (ThuViec)
    scan_analyze_btn: 'Scan & Analyze',
    scan_analyzing: 'GPT-4o is reading evaluation form & SXKD plan...',
    scan_result: 'Scan Results',
    scan_phieu: 'Evaluation Form',
    scan_sxkd: 'SXKD Plan',
    scan_send_eval: '→ Send to Evaluation',
    scan_sending: 'Analyzing...',
    scan_reset: '↩ Re-scan',
    scan_phieu_tab: 'Evaluation Form',
    scan_sxkd_tab: 'SXKD Plan',
    scan_task_phieu: 'Scanning evaluation form',
    scan_task_sxkd: 'Scanning SXKD plan',
    scan_pdf_hint: 'PDF scan',

    // Document Warnings
    doc_warnings: 'Document Warnings',
    doc_complete: 'Documents are complete',
    doc_incomplete: 'Documents need updates',

    // Proposal & Urgency
    proposal_level: 'Proposal Level',
    urgency_level: 'Urgency Level',
    next_steps: 'Next Steps',
    priority: 'Priority',
    responsible: 'Responsible',
  }
}

export function t(key) {
  return dict[store.lang][key] || key
}
