<template>
  <div class="app-layout">
    <!-- SIDEBAR -->
    <aside class="sidebar">
      <div class="sb-top">
        <button class="sb-back" title="Về Portal" @click="$router.push('/')">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M19 12H5m7-7l-7 7 7 7"/></svg>
        </button>
        <div class="sb-logo">
          <div class="sb-logo-mark">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5"><path d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7"/></svg>
          </div>
          <div>
            <div class="sb-name">Scan KH SXKD</div>
            <div class="sb-org">CT Group · 2AS</div>
          </div>
        </div>
      </div>

      <div class="sb-body">
        <!-- Step 1: Upload -->
        <div v-if="step === 1" class="sb-section">
          <div class="sb-section-title">📂 Upload kế hoạch SXKD</div>

          <div class="sb-upload-card" :class="{filled: pdfFile, err: !pdfFile && tried}"
            @dragover.prevent @drop.prevent="onDrop" @click="$refs.rFile.click()">
            <input ref="rFile" type="file" accept=".pdf" hidden @change="e => pdfFile = e.target.files[0] || null"/>
            <div class="upc-icon">{{ pdfFile ? '📄' : '🗂️' }}</div>
            <div class="upc-info" :title="pdfFile ? pdfFile.name : ''">
              <div class="upc-label">Kế hoạch SXKD tháng</div>
              <div class="upc-val" :class="pdfFile ? 'ok' : 'empty'">
                {{ pdfFile ? pdfFile.name : 'Click hoặc kéo thả PDF' }}
              </div>
              <div v-if="!pdfFile" class="upc-hint">Định dạng: .pdf (scan từ CamScanner)</div>
            </div>
            <button v-if="pdfFile" class="upc-rm" @click.stop="pdfFile = null">✕</button>
          </div>

          <p v-if="tried && !pdfFile" class="sb-err">Vui lòng chọn file PDF</p>

          <button class="sb-btn-primary" :disabled="loading" @click="doOCR">
            <span v-if="loading" class="spinner"></span>
            <svg v-else width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
            {{ loading ? loadingMsg : 'Quét & Trích xuất SXKD' }}
          </button>

          <div v-if="error" class="sb-err-box">{{ error }}</div>
        </div>

        <!-- Step 2: Sidebar summary -->
        <div v-if="step === 2" class="sb-section">
          <div class="sb-section-title">📊 Kết quả</div>

          <!-- Per-month stats -->
          <div v-for="(m, i) in months" :key="i" class="sb-month-stat">
            <div class="sb-month-stat-title">{{ extractMonthLabel(m.tieu_de) }}</div>
            <div class="sb-stat-row">
              <div class="sb-stat">
                <div class="stat-num">{{ m.cong_viec?.length || 0 }}</div>
                <div class="stat-lbl">Công việc</div>
              </div>
              <div class="sb-stat">
                <div class="stat-num kq-num">{{ m.ty_le_dat_ket_qua || '—' }}</div>
                <div class="stat-lbl">Tỷ lệ đạt</div>
              </div>
            </div>
          </div>

          <!-- Download buttons per month -->
          <div v-for="(m, i) in months" :key="'dl'+i" style="margin-bottom:8px">
            <button class="sb-btn-primary" :disabled="loadingExcel === i" @click="downloadExcel(i)">
              <span v-if="loadingExcel === i" class="spinner"></span>
              <svg v-else width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
              ⬇ Excel {{ extractMonthLabel(m.tieu_de) }}
            </button>
          </div>

          <button class="sb-btn-secondary" @click="resetAll">↩ Scan phiếu khác</button>
        </div>
      </div>
    </aside>

    <!-- MAIN PANEL -->
    <main class="result-panel">
      <!-- Welcome -->
      <div v-if="step === 1 && !loading" class="welcome">
        <div class="welcome-icon">
          <svg width="56" height="56" viewBox="0 0 56 56" fill="none">
            <rect width="56" height="56" rx="18" fill="url(#wg)"/>
            <text x="28" y="38" text-anchor="middle" font-size="26">📊</text>
            <defs><linearGradient id="wg" x1="0" y1="0" x2="56" y2="56">
              <stop stop-color="#10b981"/><stop offset="1" stop-color="#6366f1"/>
            </linearGradient></defs>
          </svg>
        </div>
        <h1>Scan Kế Hoạch SXKD Tháng</h1>
        <p>Upload PDF kế hoạch SXKD scan từ CamScanner. AI sẽ đọc toàn bộ, tách đúng từng tháng và hiển thị đầy đủ tất cả bảng theo thứ tự.</p>
        <div class="welcome-features">
          <div class="wf"><div class="wf-icon">📄</div><div>Đọc PDF CamScanner</div></div>
          <div class="wf"><div class="wf-icon">🤖</div><div>GPT-4o Vision OCR</div></div>
          <div class="wf"><div class="wf-icon">📅</div><div>Tách đúng từng tháng</div></div>
          <div class="wf"><div class="wf-icon">📊</div><div>Excel mẫu CT Group</div></div>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="loading-screen">
        <div class="loading-spinner"></div>
        <p>{{ loadingMsg }}</p>
        <p class="loading-sub">GPT-4o đang đọc từng trang PDF — có thể mất 30–90 giây</p>
      </div>

      <!-- Results: all months stacked -->
      <div v-if="step === 2 && months.length && !loading" class="results-scroll">
        <div v-if="isDirty" class="phieu-dirty-bar">
          ⚠️ Có thay đổi chưa lưu
          <button class="db-save" @click="isDirty=false">✓ Đã lưu</button>
        </div>

        <!-- Họ và tên (dùng chung) -->
        <div class="sxkd-doc" style="margin-bottom:20px">
          <div class="sxkd-subtitle">
            <span class="sxkd-field-label">Họ và tên:</span>
            <input class="sxkd-inline-input name-input" v-model="months[0].ho_ten" @input="isDirty=true"/>
          </div>
        </div>

        <!-- Mỗi tháng: chỉ có bảng công việc -->
        <div v-for="(m, mi) in months" :key="mi" class="sxkd-month-block">
          <div class="month-sep">
            <div class="month-sep-line"></div>
            <div class="month-sep-label">{{ extractMonthLabel(m.tieu_de) }}</div>
            <div class="month-sep-line"></div>
          </div>

          <div class="sxkd-doc">
            <div class="sxkd-title">{{ m.tieu_de || 'KẾ HOẠCH SXKD THÁNG' }}</div>

            <!-- ══ BẢNG CÔNG VIỆC ══ -->
            <div class="sxkd-section-label">BẢNG KẾ HOẠCH VÀ KẾT QUẢ CÔNG VIỆC</div>
            <div class="sxkd-table-wrap">
              <table class="sxkd-table">
                <thead>
                  <tr class="sxkd-th-row">
                    <th rowspan="2" class="th-stt">STT</th>
                    <th rowspan="2" class="th-mang">CÁC MẢNG CÔNG TÁC</th>
                    <th rowspan="2" class="th-mota">MÔ TẢ SẢN PHẨM PHẢI HOÀN THÀNH TRONG THÁNG</th>
                    <th colspan="3" class="th-group th-kh">KẾ HOẠCH THỰC HIỆN</th>
                    <th colspan="3" class="th-group th-kq">KẾT QUẢ THỰC HIỆN</th>
                    <th rowspan="2" class="th-link">LINK SẢN PHẨM ĐÃ UPLOAD</th>
                  </tr>
                  <tr class="sxkd-th-sub">
                    <th class="th-sub">TỶ TRỌNG</th>
                    <th class="th-sub">KPI</th>
                    <th class="th-sub">BOD XÉT DUYỆT</th>
                    <th class="th-sub th-kq-col">TỶ LỆ KPI</th>
                    <th class="th-sub th-kq-col">KẾT QUẢ KPI</th>
                    <th class="th-sub th-kq-col">BOD XÉT DUYỆT</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="cv in m.cong_viec" :key="mi+'-cv-'+cv.stt" class="sxkd-row">
                    <td class="td-stt">{{ cv.stt }}</td>
                    <td class="td-mang"><input class="sxkd-cell-input" v-model="cv.mang_cong_tac" @input="isDirty=true"/></td>
                    <td class="td-mota"><textarea class="sxkd-cell-ta" v-model="cv.mo_ta_san_pham" rows="5" @input="isDirty=true"></textarea></td>
                    <td class="td-num"><input class="sxkd-cell-input ta-center" v-model="cv.ty_trong" @input="isDirty=true"/></td>
                    <td class="td-num"><input class="sxkd-cell-input ta-center" v-model="cv.kpi_ke_hoach" @input="isDirty=true"/></td>
                    <td class="td-bod"><input class="sxkd-cell-input" v-model="cv.bod_ke_hoach" @input="isDirty=true"/></td>
                    <td class="td-num kq-cell"><input class="sxkd-cell-input ta-center" v-model="cv.ty_le_kpi_ket_qua" @input="isDirty=true"/></td>
                    <td class="td-num kq-cell"><input class="sxkd-cell-input ta-center kq-bold" v-model="cv.ket_qua_kpi" @input="isDirty=true"/></td>
                    <td class="td-bod kq-cell"><input class="sxkd-cell-input" v-model="cv.bod_ket_qua" @input="isDirty=true"/></td>
                    <td class="td-link"><textarea class="sxkd-cell-ta link-ta" v-model="cv.link_san_pham" rows="3" @input="isDirty=true"></textarea></td>
                  </tr>
                  <tr class="sxkd-total-row">
                    <td colspan="3" class="td-total-label">TỶ LỆ ĐẠT</td>
                    <td class="td-num ta-center">{{ m.ty_le_dat_ke_hoach || '100%' }}</td>
                    <td colspan="2"></td>
                    <td colspan="2" class="td-num ta-center kq-bold">{{ m.ty_le_dat_ket_qua }}</td>
                    <td colspan="2"></td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- Nút download Excel từng tháng -->
            <div class="sxkd-block-actions">
              <button class="action-btn action-excel" :disabled="loadingExcel === mi" @click="downloadExcel(mi)">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><path d="M8 13h2l2 4 2-4h2M8 10h8"/></svg>
                <span>{{ loadingExcel === mi ? 'Đang tạo...' : 'Tải Excel ' + extractMonthLabel(m.tieu_de) }}</span>
              </button>
            </div>
          </div>
        </div>

        <!-- ══ PHẦN CHUNG (1 lần cho tất cả tháng) ══ -->
        <div class="shared-sep">
          <div class="month-sep-line"></div>
          <div class="month-sep-label shared-label">Phần chung — tất cả tháng</div>
          <div class="month-sep-line"></div>
        </div>

        <div class="sxkd-doc">

          <!-- NỘI QUY BẮT BUỘC -->
          <div class="sxkd-section-label nq-label">NỘI QUY BẮT BUỘC VÀ CÁC CHỈ ĐẠO CẤP TRÊN</div>
          <div class="nq-note">(Mục bắt buộc này cần phải thực hiện, nếu vi phạm sẽ bị khấu trừ vào tổng KPI)</div>
          <div class="sxkd-table-wrap">
            <table class="sxkd-table nq-table">
              <thead>
                <tr class="sxkd-th-row">
                  <th class="th-stt">STT</th>
                  <th>NỘI DUNG</th>
                  <th class="th-sub">KẾ HOẠCH THỰC HIỆN</th>
                  <th class="th-sub">KẾT QUẢ THỰC HIỆN</th>
                  <th>XÁC NHẬN CỦA PHÒNG/BAN CHUYÊN MÔN</th>
                  <th>GHI CHÚ</th>
                </tr>
              </thead>
              <tbody>
                <tr class="nq-header-row"><td colspan="6" class="nq-sub-header">THỰC HIỆN NỘI QUY</td></tr>
                <tr v-for="nq in shared.noi_quy" :key="'nq-'+nq.stt" class="sxkd-row">
                  <td class="td-stt">{{ nq.stt }}</td>
                  <td><input class="sxkd-cell-input" v-model="nq.noi_dung" @input="isDirty=true"/></td>
                  <td class="td-num ta-center"><input class="sxkd-cell-input ta-center" v-model="nq.ke_hoach" @input="isDirty=true"/></td>
                  <td class="td-num ta-center kq-cell"><input class="sxkd-cell-input ta-center" v-model="nq.ket_qua" @input="isDirty=true"/></td>
                  <td><input class="sxkd-cell-input" v-model="nq.xac_nhan" @input="isDirty=true"/></td>
                  <td><input class="sxkd-cell-input" v-model="nq.ghi_chu" @input="isDirty=true"/></td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- CHỈ ĐẠO BAN LÃNH ĐẠO -->
          <div class="sxkd-section-label cd-label">CÁC CHỈ ĐẠO CỦA BAN LÃNH ĐẠO</div>
          <div class="nq-note">(Các chỉ đạo phát sinh trong tháng không ảnh hưởng đến tỷ trọng kế hoạch, nếu không thực hiện bị trừ vào tổng KPI)</div>
          <div class="sxkd-table-wrap">
            <table class="sxkd-table nq-table">
              <thead>
                <tr class="sxkd-th-row">
                  <th class="th-stt">STT</th>
                  <th>NỘI DUNG CHỈ ĐẠO</th>
                  <th class="th-sub kq-cell">KẾT QUẢ THỰC HIỆN</th>
                  <th class="th-sub">BOD XÉT DUYỆT</th>
                  <th>GHI CHÚ</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="cd in shared.chi_dao" :key="'cd-'+cd.stt" class="sxkd-row">
                  <td class="td-stt">{{ cd.stt }}</td>
                  <td><input class="sxkd-cell-input" v-model="cd.noi_dung" @input="isDirty=true"/></td>
                  <td class="kq-cell"><input class="sxkd-cell-input" v-model="cd.ket_qua" @input="isDirty=true"/></td>
                  <td><input class="sxkd-cell-input" v-model="cd.bod_xet_duyet" @input="isDirty=true"/></td>
                  <td><input class="sxkd-cell-input" v-model="cd.ghi_chu" @input="isDirty=true"/></td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- XÉT DUYỆT -->
          <div class="sxkd-xetduyet">
            <div class="xd-title">PHẦN TRÌNH VÀ XÉT DUYỆT</div>
            <table class="xd-table">
              <thead><tr><th>XÉT DUYỆT</th><th>Ý KIẾN</th><th>Ranking</th></tr></thead>
              <tbody>
                <tr>
                  <td class="xd-label">HOD</td>
                  <td><input class="sxkd-cell-input" v-model="shared.xet_duyet.hod_y_kien" @input="isDirty=true"/></td>
                  <td rowspan="2" class="xd-ranking">
                    <input class="sxkd-cell-input ta-center ranking-input" v-model="shared.xet_duyet.ranking" @input="isDirty=true"/>
                  </td>
                </tr>
                <tr>
                  <td class="xd-label">BOD</td>
                  <td><input class="sxkd-cell-input" v-model="shared.xet_duyet.bod_y_kien" @input="isDirty=true"/></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div><!-- end shared sxkd-doc -->

        <!-- Reset -->
        <div class="bottom-reset">
          <button class="action-btn action-reset" @click="resetAll">
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 102.13-9.36L1 10"/></svg>
            <span>Scan phiếu khác</span>
          </button>
        </div>
      </div><!-- end results-scroll -->
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'

// ── CSRF helper ────────────────────────────────────────────────────
function csrf() {
  if (window.frappe?.csrf_token) return window.frappe.csrf_token
  const c = document.cookie.split('; ').find(r => r.startsWith('csrf_token='))?.split('=')[1]
  return c ? decodeURIComponent(c) : 'no-csrf'
}

async function callApi(url, opts = {}) {
  const headers = { 'X-Frappe-CSRF-Token': csrf(), ...opts.headers }
  const r = await fetch(url, { ...opts, headers })
  if (!r.ok) {
    let msg = `HTTP ${r.status}`
    try {
      const j = await r.json()
      msg = j.exc_type ? `${j.exc_type}: ${j.exception || j._error_message || ''}` : (j.message || msg)
    } catch {}
    throw new Error(msg)
  }
  return r
}

// ── State ──────────────────────────────────────────────────────────
const step = ref(1)
const pdfFile = ref(null)
const loading = ref(false)
const loadingMsg = ref('Đang khởi tạo...')
const loadingExcel = ref(null)
const tried = ref(false)
const error = ref('')
const isDirty = ref(false)
const months = ref([])   // per-month: tieu_de, cong_viec only

// Shared section (nội quy + chỉ đạo BLĐ + xét duyệt) — dùng chung cho tất cả tháng
const shared = ref({
  noi_quy: [
    { stt: 1, noi_dung: 'Upload data', ke_hoach: '100%', ket_qua: '', xac_nhan: '', ghi_chu: '' },
    { stt: 2, noi_dung: 'Học tập và áp dụng AI', ke_hoach: '100%', ket_qua: '', xac_nhan: '', ghi_chu: '' }
  ],
  chi_dao: [
    { stt: 1, noi_dung: '', ket_qua: '', bod_xet_duyet: '', ghi_chu: '' },
    { stt: 2, noi_dung: '', ket_qua: '', bod_xet_duyet: '', ghi_chu: '' },
    { stt: 3, noi_dung: '', ket_qua: '', bod_xet_duyet: '', ghi_chu: '' },
  ],
  xet_duyet: { hod_y_kien: '', bod_y_kien: '', ranking: '' }
})

function extractMonthLabel(title) {
  const m = (title || '').match(/TH[ÁA]NG\s+(\d+)/i)
  return m ? `Tháng ${m[1]}` : (title ? title.slice(0, 14) : 'Tháng ?')
}

// ── Helpers ────────────────────────────────────────────────────────
function onDrop(e) {
  const f = e.dataTransfer.files[0]
  if (f && f.name.endsWith('.pdf')) pdfFile.value = f
}

function blankMonthDefaults(m) {
  return {
    tieu_de: m.tieu_de || '',
    ho_ten: (m.ho_ten || '').replace(/Họ và tên:\s*/i, '').trim(),
    cong_viec: m.cong_viec || [],
    ty_le_dat_ke_hoach: m.ty_le_dat_ke_hoach || '100%',
    ty_le_dat_ket_qua: m.ty_le_dat_ket_qua || '',
    noi_quy: m.noi_quy?.length ? m.noi_quy : [
      { stt: 1, noi_dung: 'Upload data', ke_hoach: '100%', ket_qua: '', xac_nhan: '', ghi_chu: '' },
      { stt: 2, noi_dung: 'Học tập và áp dụng AI', ke_hoach: '100%', ket_qua: '', xac_nhan: '', ghi_chu: '' }
    ],
    chi_dao: m.chi_dao?.length ? m.chi_dao : [
      { stt: 1, noi_dung: '', ket_qua: '', bod_xet_duyet: '', ghi_chu: '' },
      { stt: 2, noi_dung: '', ket_qua: '', bod_xet_duyet: '', ghi_chu: '' },
      { stt: 3, noi_dung: '', ket_qua: '', bod_xet_duyet: '', ghi_chu: '' },
    ],
    xet_duyet: m.xet_duyet || { hod_y_kien: '', bod_y_kien: '', ranking: '' }
  }
}

// ── OCR ───────────────────────────────────────────────────────────
async function doOCR() {
  tried.value = true
  if (!pdfFile.value) return
  loading.value = true
  error.value = ''

  const msgs = [
    'Đang tải PDF lên server...',
    'Pass 1: GPT-4o quét tiêu đề từng trang...',
    'Pass 2: Đọc chi tiết từng tháng...',
    'Trích xuất nội quy và chỉ đạo BLĐ...',
    'Hoàn thiện kết quả...'
  ]
  let msgIdx = 0
  loadingMsg.value = msgs[0]
  const msgInterval = setInterval(() => {
    msgIdx = (msgIdx + 1) % msgs.length
    loadingMsg.value = msgs[msgIdx]
  }, 5000)

  try {
    const fd = new FormData()
    fd.append('file', pdfFile.value)

    const resp = await callApi('/api/method/cnb_2as.api.scan_sxkd.ocr_sxkd', {
      method: 'POST', body: fd,
    })

    const json = await resp.json()
    const msg = json.message ?? json
    const rawMonths = msg.months ?? (msg.data ? [msg.data] : [msg])

    months.value = rawMonths.map(m => ({
      tieu_de: m.tieu_de || '',
      ho_ten: (m.ho_ten || '').replace(/Họ và tên:\s*/i, '').trim(),
      cong_viec: m.cong_viec || [],
      ty_le_dat_ke_hoach: m.ty_le_dat_ke_hoach || '100%',
      ty_le_dat_ket_qua: m.ty_le_dat_ket_qua || '',
    }))

    // Shared section: lấy từ tháng đầu tiên có nội quy, fallback default
    const src = rawMonths.find(m => m.noi_quy?.length) || rawMonths[0] || {}
    shared.value = {
      noi_quy: src.noi_quy?.length ? src.noi_quy : [
        { stt: 1, noi_dung: 'Upload data', ke_hoach: '100%', ket_qua: '', xac_nhan: '', ghi_chu: '' },
        { stt: 2, noi_dung: 'Học tập và áp dụng AI', ke_hoach: '100%', ket_qua: '', xac_nhan: '', ghi_chu: '' }
      ],
      chi_dao: src.chi_dao?.length ? src.chi_dao : [
        { stt: 1, noi_dung: '', ket_qua: '', bod_xet_duyet: '', ghi_chu: '' },
        { stt: 2, noi_dung: '', ket_qua: '', bod_xet_duyet: '', ghi_chu: '' },
        { stt: 3, noi_dung: '', ket_qua: '', bod_xet_duyet: '', ghi_chu: '' },
      ],
      xet_duyet: src.xet_duyet || { hod_y_kien: '', bod_y_kien: '', ranking: '' }
    }
    step.value = 2
  } catch (e) {
    error.value = `Lỗi: ${e.message}`
  } finally {
    clearInterval(msgInterval)
    loading.value = false
  }
}

// ── Download Excel (per month) ─────────────────────────────────────
async function downloadExcel(monthIdx) {
  const m = months.value[monthIdx]
  if (!m) return
  loadingExcel.value = monthIdx
  try {
    const fd = new FormData()
    fd.append('data', JSON.stringify(m))

    const resp = await callApi('/api/method/cnb_2as.api.scan_sxkd.export_excel', {
      method: 'POST', body: fd,
    })

    const blob = await resp.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    const ho_ten = (m.ho_ten || 'SXKD').replace(/[\s/\\]+/g, '_')
    const thang = (m.tieu_de || '').match(/TH[ÁA]NG\s+(\d+)/i)?.[1] || String(monthIdx + 1)
    a.href = url
    a.download = `SXKD_${ho_ten}_T${thang}.xlsx`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  } catch (e) {
    alert(`Lỗi tải Excel: ${e.message}`)
  } finally {
    loadingExcel.value = null
  }
}

function resetAll() {
  step.value = 1
  pdfFile.value = null
  tried.value = false
  error.value = ''
  isDirty.value = false
  months.value = []
  shared.value = {
    noi_quy: [
      { stt: 1, noi_dung: 'Upload data', ke_hoach: '100%', ket_qua: '', xac_nhan: '', ghi_chu: '' },
      { stt: 2, noi_dung: 'Học tập và áp dụng AI', ke_hoach: '100%', ket_qua: '', xac_nhan: '', ghi_chu: '' }
    ],
    chi_dao: [
      { stt: 1, noi_dung: '', ket_qua: '', bod_xet_duyet: '', ghi_chu: '' },
      { stt: 2, noi_dung: '', ket_qua: '', bod_xet_duyet: '', ghi_chu: '' },
      { stt: 3, noi_dung: '', ket_qua: '', bod_xet_duyet: '', ghi_chu: '' },
    ],
    xet_duyet: { hod_y_kien: '', bod_y_kien: '', ranking: '' }
  }
}
</script>

<style scoped>
/* ── Layout ─────────────────────────────────────────────────────── */
.app-layout { display: flex; height: 100vh; overflow: hidden; }

.sidebar {
  width: 256px; min-width: 220px; display: flex; flex-direction: column;
  border-right: 1px solid rgba(99,102,241,.15); background: #13131a;
}
body.theme-light .sidebar { background: #fff; border-right-color: #e2e8f0; }

.sb-top { padding: 14px; display: flex; align-items: center; gap: 10px; border-bottom: 1px solid rgba(255,255,255,.06); }
body.theme-light .sb-top { border-bottom-color: #e2e8f0; }

.sb-back {
  width: 30px; height: 30px; border-radius: 8px; border: 1px solid rgba(99,102,241,.3);
  background: rgba(99,102,241,.1); color: inherit; cursor: pointer; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center; transition: all .2s;
}
.sb-back:hover { background: rgba(99,102,241,.2); }

.sb-logo { display: flex; align-items: center; gap: 9px; }
.sb-logo-mark { width: 34px; height: 34px; background: linear-gradient(135deg,#10b981,#6366f1); border-radius: 10px; display: flex; align-items: center; justify-content: center; }
.sb-name { font-weight: 700; font-size: .88rem; }
.sb-org { font-size: .7rem; color: #64748b; }

.sb-body { flex: 1; overflow-y: auto; padding: 14px; }
.sb-section-title { font-size: .78rem; font-weight: 700; color: #6366f1; text-transform: uppercase; letter-spacing: .05em; margin-bottom: 12px; }

/* Upload card */
.sb-upload-card {
  border: 2px dashed rgba(99,102,241,.3); border-radius: 12px; padding: 14px;
  cursor: pointer; transition: all .2s; margin-bottom: 12px;
  display: flex; align-items: center; gap: 10px;
}
.sb-upload-card:hover { border-color: #6366f1; background: rgba(99,102,241,.05); }
.sb-upload-card.filled { border-style: solid; border-color: #10b981; background: rgba(16,185,129,.05); }
.sb-upload-card.err { border-color: #ef4444; }
.upc-icon { font-size: 22px; flex-shrink: 0; }
.upc-info { flex: 1; min-width: 0; }
.upc-label { font-size: .7rem; color: #64748b; font-weight: 600; }
.upc-val { font-size: .78rem; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.upc-val.ok { color: #10b981; }
.upc-val.empty { color: #94a3b8; }
.upc-hint { font-size: .67rem; color: #64748b; margin-top: 2px; }
.upc-rm { background: none; border: none; cursor: pointer; color: #ef4444; font-size: 13px; flex-shrink: 0; }

.sb-btn-primary {
  width: 100%; padding: 9px 12px; border-radius: 10px; border: none; cursor: pointer;
  background: linear-gradient(135deg, #10b981, #6366f1); color: white;
  font-weight: 600; font-size: .84rem; display: flex; align-items: center; justify-content: center;
  gap: 7px; transition: all .2s; margin-bottom: 8px;
}
.sb-btn-primary:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 4px 14px rgba(99,102,241,.3); }
.sb-btn-primary:disabled { opacity: .6; cursor: not-allowed; }

.sb-btn-secondary {
  width: 100%; padding: 8px; border-radius: 10px; border: 1px solid rgba(99,102,241,.3);
  background: transparent; color: inherit; cursor: pointer; font-size: .82rem; font-weight: 600; transition: all .2s;
}
.sb-btn-secondary:hover { background: rgba(99,102,241,.08); }

/* Month stats in sidebar */
.sb-month-stat { margin-bottom: 12px; padding: 10px; background: rgba(99,102,241,.06); border-radius: 10px; }
.sb-month-stat-title { font-size: .74rem; font-weight: 700; color: #6366f1; margin-bottom: 8px; text-transform: uppercase; letter-spacing: .04em; }
.sb-stat-row { display: flex; gap: 8px; }
.sb-stat { flex: 1; text-align: center; }
.stat-num { font-size: 1.3rem; font-weight: 800; color: #6366f1; }
.stat-num.kq-num { color: #10b981; }
.stat-lbl { font-size: .66rem; color: #64748b; font-weight: 600; }

.sb-err { color: #ef4444; font-size: .76rem; margin-top: 4px; }
.sb-err-box { margin-top: 8px; padding: 9px; background: rgba(239,68,68,.1); border-radius: 8px; color: #ef4444; font-size: .78rem; }
.spinner { width: 13px; height: 13px; border: 2px solid rgba(255,255,255,.3); border-top-color: #fff; border-radius: 50%; animation: spin .7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg) } }

/* ── Main panel ──────────────────────────────────────────────────── */
.result-panel { flex: 1; overflow: hidden; display: flex; flex-direction: column; }

.welcome { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 40px; text-align: center; }
.welcome-icon { margin-bottom: 22px; }
.welcome h1 { font-size: 1.7rem; font-weight: 800; margin-bottom: 10px; }
.welcome p { color: #94a3b8; max-width: 440px; line-height: 1.7; margin-bottom: 24px; }
.welcome-features { display: flex; gap: 10px; flex-wrap: wrap; justify-content: center; }
.wf { display: flex; align-items: center; gap: 7px; background: rgba(99,102,241,.08); padding: 9px 14px; border-radius: 10px; font-size: .8rem; font-weight: 600; }
.wf-icon { font-size: 17px; }

.loading-screen { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 14px; }
.loading-spinner { width: 48px; height: 48px; border: 4px solid rgba(99,102,241,.2); border-top-color: #6366f1; border-radius: 50%; animation: spin .9s linear infinite; }
.loading-sub { color: #64748b; font-size: .84rem; }

.results-scroll { flex: 1; overflow-y: auto; padding: 20px 28px 48px; }

/* Dirty bar */
.phieu-dirty-bar {
  position: sticky; top: -20px; z-index: 10;
  background: rgba(251,191,36,.15); border: 1px solid rgba(251,191,36,.4);
  border-radius: 10px; padding: 9px 14px; margin-bottom: 14px;
  display: flex; align-items: center; gap: 10px; font-size: .84rem; font-weight: 600;
}
.db-save { background: #6366f1; color: white; border: none; border-radius: 6px; padding: 3px 10px; cursor: pointer; font-size: .8rem; }

.shared-sep { margin: 28px 0 16px; }
.shared-label { color: #10b981 !important; border-color: rgba(16,185,129,.25) !important; background: rgba(16,185,129,.07) !important; }

.sxkd-month-block { margin-bottom: 40px; }
.month-sep {
  display: flex; align-items: center; gap: 14px; margin-bottom: 16px;
}
.month-sep-line { flex: 1; height: 2px; background: linear-gradient(90deg, transparent, rgba(99,102,241,.3), transparent); }
.month-sep-label {
  font-size: .88rem; font-weight: 800; color: #6366f1; text-transform: uppercase;
  letter-spacing: .08em; white-space: nowrap;
  padding: 5px 16px; background: rgba(99,102,241,.08); border-radius: 20px;
  border: 1px solid rgba(99,102,241,.2);
}

/* ── SXKD Document ────────────────────────────────────────────── */
.sxkd-doc { background: white; border-radius: 14px; padding: 26px; box-shadow: 0 4px 20px rgba(0,0,0,.07); max-width: 1100px; margin: 0 auto; }
body.theme-dark .sxkd-doc { background: #1a1a28; box-shadow: 0 4px 24px rgba(0,0,0,.4); }

.sxkd-title { text-align: center; font-size: 1rem; font-weight: 800; text-transform: uppercase; color: #1e293b; margin-bottom: 10px; }
body.theme-dark .sxkd-title { color: #f1f5f9; }

.sxkd-subtitle { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 2px solid #e2e8f0; }
body.theme-dark .sxkd-subtitle { border-bottom-color: rgba(255,255,255,.1); }
.sxkd-field-label { font-weight: 700; font-size: .88rem; white-space: nowrap; }
.name-input { font-weight: 700 !important; font-size: .95rem !important; }

.sxkd-inline-input { border: none; border-bottom: 2px solid rgba(99,102,241,.3); background: transparent; outline: none; color: inherit; flex: 1; font-size: .92rem; padding: 2px 4px; }
.sxkd-inline-input:focus { border-bottom-color: #6366f1; }

.sxkd-section-label { font-size: .72rem; font-weight: 800; text-transform: uppercase; letter-spacing: .07em; color: #6366f1; margin: 16px 0 4px; }
.nq-label { color: #f59e0b; }
.cd-label { color: #ef4444; }
.nq-note { font-size: .72rem; color: #94a3b8; margin-bottom: 7px; }

/* Tables */
.sxkd-table-wrap { overflow-x: auto; margin-bottom: 4px; border-radius: 9px; border: 1.5px solid #e2e8f0; }
body.theme-dark .sxkd-table-wrap { border-color: rgba(255,255,255,.1); }
.sxkd-table { width: 100%; border-collapse: collapse; min-width: 900px; }
.nq-table { min-width: 680px; }

.sxkd-th-row th { background: #f1f5f9; font-size: .69rem; font-weight: 700; text-transform: uppercase; padding: 7px 8px; border: 1px solid #d1d5db; color: #374151; text-align: center; }
body.theme-dark .sxkd-th-row th { background: #1e2030; color: #94a3b8; border-color: rgba(255,255,255,.08); }
.sxkd-th-sub { font-size: .65rem !important; }
.th-group { border-bottom: none !important; }
.th-kh { background: rgba(99,102,241,.08) !important; color: #6366f1 !important; }
.th-kq { background: rgba(16,185,129,.08) !important; color: #059669 !important; }

.sxkd-row td { border: 1px solid #e2e8f0; padding: 0; vertical-align: top; }
body.theme-dark .sxkd-row td { border-color: rgba(255,255,255,.07); }
.sxkd-row:hover td { background: rgba(99,102,241,.02); }

.td-stt { width: 32px; text-align: center; font-weight: 700; vertical-align: middle; color: #6366f1; padding: 8px; }
.td-mang { width: 120px; }
.td-mota { width: 270px; }
.td-num { width: 66px; }
.td-bod { width: 74px; }
.td-link { width: 145px; }
.td-total-label { text-align: center; font-weight: 800; font-size: .82rem; background: #f8fafc; padding: 9px; }
body.theme-dark .td-total-label { background: #1a1a28; }
.sxkd-total-row td { border: 1px solid #e2e8f0; padding: 7px; }
body.theme-dark .sxkd-total-row td { border-color: rgba(255,255,255,.07); }

.kq-cell { background: rgba(16,185,129,.04) !important; }
.kq-bold { font-weight: 700 !important; color: #059669 !important; }
.ta-center { text-align: center !important; }

.sxkd-cell-input { width: 100%; border: none; background: transparent; outline: none; color: inherit; font-size: .8rem; padding: 6px 7px; font-family: inherit; transition: background .15s; }
.sxkd-cell-input:focus { background: rgba(99,102,241,.05); }
.sxkd-cell-ta { width: 100%; border: none; background: transparent; outline: none; color: inherit; font-size: .78rem; padding: 6px 7px; font-family: inherit; resize: vertical; min-height: 76px; transition: background .15s; }
.sxkd-cell-ta:focus { background: rgba(99,102,241,.05); }
.link-ta { font-size: .72rem; color: #6366f1; min-height: 52px; }

.nq-header-row td { background: #fef3c7; color: #92400e; font-weight: 700; font-size: .76rem; padding: 5px 10px; }
body.theme-dark .nq-header-row td { background: rgba(245,158,11,.1); color: #fbbf24; }
.nq-sub-header { text-align: left; border: 1px solid #e2e8f0; }

/* Xét duyệt */
.sxkd-xetduyet { margin-top: 16px; }
.xd-title { text-align: center; font-weight: 800; font-size: .82rem; text-transform: uppercase; color: #374151; margin-bottom: 9px; }
body.theme-dark .xd-title { color: #f1f5f9; }
.xd-table { margin: 0 auto; width: 54%; min-width: 360px; border-collapse: collapse; }
.xd-table th { background: #f1f5f9; border: 1px solid #d1d5db; padding: 7px 12px; font-size: .76rem; font-weight: 700; text-align: center; }
body.theme-dark .xd-table th { background: #1e2030; border-color: rgba(255,255,255,.1); color: #94a3b8; }
.xd-table td { border: 1px solid #e2e8f0; }
body.theme-dark .xd-table td { border-color: rgba(255,255,255,.07); }
.xd-label { text-align: center; font-weight: 700; font-size: .82rem; padding: 9px; width: 72px; }
.xd-ranking { text-align: center; vertical-align: middle; }
.ranking-input { font-size: 1.15rem !important; font-weight: 800 !important; color: #6366f1 !important; }

/* Block actions (per month) */
.sxkd-block-actions { display: flex; gap: 12px; margin-top: 20px; padding-top: 18px; border-top: 1.5px solid #e2e8f0; }
body.theme-dark .sxkd-block-actions { border-top-color: rgba(255,255,255,.08); }

.action-btn { display: flex; align-items: center; gap: 9px; padding: 12px 22px; border-radius: 11px; border: none; cursor: pointer; font-size: .9rem; font-weight: 700; transition: all .22s; }
.action-btn:hover:not(:disabled) { transform: translateY(-2px); }
.action-btn:disabled { opacity: .6; cursor: not-allowed; }
.action-excel { background: linear-gradient(135deg, #059669, #10b981); color: white; box-shadow: 0 3px 12px rgba(16,185,129,.28); }
.action-excel:hover:not(:disabled) { box-shadow: 0 7px 20px rgba(16,185,129,.38); }
.action-reset { background: rgba(99,102,241,.1); color: #6366f1; border: 1.5px solid rgba(99,102,241,.3); }
.action-reset:hover { background: rgba(99,102,241,.18); }

/* Bottom reset */
.bottom-reset { display: flex; justify-content: center; margin-top: 16px; padding-top: 24px; border-top: 2px solid rgba(99,102,241,.1); }
</style>
