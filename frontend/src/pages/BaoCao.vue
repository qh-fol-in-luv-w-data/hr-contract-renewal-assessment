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
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
          </div>
          <div>
            <div class="sb-name">Báo cáo ĐG Nhân sự</div>
            <div class="sb-org">CT Group · 2AS</div>
          </div>
        </div>
      </div>

      <div class="sb-body">
        <!-- Step 1: Upload -->
        <div v-if="step === 1" class="sb-section">
          <div class="sb-section-title">📂 Upload phiếu đánh giá</div>

          <div class="sb-field">
            <label class="sb-label">Phòng ban / Đơn vị</label>
            <input type="text" v-model="phongBan" class="sb-input"
              placeholder="VD: Phòng Kỹ thuật..." />
          </div>

          <!-- Drop zone: kéo folder hoặc file vào -->
          <div class="sb-upload-multi" :class="{ filled: files.length > 0, err: tried && !files.length, dropping: isDragging }"
            @dragover.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false"
            @drop.prevent="onDrop"
            @click="$refs.rFolder.click()">
            <input ref="rFolder" type="file" webkitdirectory hidden @change="onFolderChange"/>
            <div v-if="!files.length" class="upm-empty">
              <div class="upm-icon">🗂️</div>
              <div class="upm-hint">Kéo thả folder vào đây<br>hoặc click để chọn folder</div>
            </div>
            <div v-else class="upm-list">
              <div v-for="(f, i) in files" :key="i" class="upm-item">
                <span class="upm-item-name" :title="f.name">{{ shortName(f.name) }}</span>
                <button class="upm-rm" @click.stop="removeFile(i)">✕</button>
              </div>
            </div>
          </div>

          <div v-if="files.length" class="sb-file-count">
            <span class="fc-badge">{{ files.length }}</span> file đã chọn
            <button class="fc-clear" @click="files = []">Xóa tất cả</button>
          </div>

          <p v-if="tried && !files.length" class="sb-err">Vui lòng chọn ít nhất 1 file PDF</p>

          <div class="sb-field" style="margin-top:10px">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px">
              <label class="sb-label" style="margin:0">Excel HR (tùy chọn)</label>
              <button class="hr-tmpl-link" @click="downloadHrTemplate">⬇ Template</button>
            </div>
            <!-- HR multi-file zone: drop folder hr_danh_gia hoặc chọn nhiều .xlsx -->
            <div class="hr-drop-zone" :class="{ 'hr-has-files': hrFiles.length, 'hr-dropping': isHrDragging }"
              @dragover.prevent="isHrDragging = true"
              @dragleave.prevent="isHrDragging = false"
              @drop.prevent="onHrDrop"
              @click="$refs.rHrFiles.click()">
              <input ref="rHrFiles" type="file" accept=".xlsx,.xls" multiple style="display:none"
                @change="onHrFilesChange">
              <div v-if="!hrFiles.length" class="hr-empty-hint">
                + Chọn nhiều file .xlsx<br><small>hoặc kéo folder hr_danh_gia</small>
              </div>
              <div v-else class="hr-file-list">
                <div v-for="(f, i) in hrFiles" :key="i" class="hr-file-item">
                  <span class="hr-file-name" :title="f.name">📊 {{ shortHrName(f.name) }}</span>
                  <button class="hr-rm" @click.stop="removeHrFile(i)">✕</button>
                </div>
              </div>
            </div>
            <div v-if="hrFiles.length" class="hr-count-line">
              {{ hrFiles.length }} file Excel HR đã chọn
              <button class="fc-clear" @click="hrFiles = []">Xóa</button>
            </div>
          </div>

          <button class="sb-btn-primary" :disabled="loading" @click="doOCR">
            <span v-if="loading" class="spinner"></span>
            <svg v-else width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
            {{ loading ? loadingMsg : 'Quét & Trích xuất' }}
          </button>

          <div v-if="error" class="sb-err-box">{{ error }}</div>
        </div>

        <!-- Step 2: Sidebar summary -->
        <div v-if="step === 2" class="sb-section">
          <div class="sb-section-title">📊 Kết quả OCR</div>

          <div class="sb-field" style="margin-bottom:10px">
            <label class="sb-label">Phòng ban / Đơn vị</label>
            <input type="text" v-model="phongBan" class="sb-input"
              placeholder="VD: Phòng Kỹ thuật..." />
          </div>

          <div v-for="(p, i) in persons" :key="i" class="sb-person-stat"
            :class="{ active: activePerson === i }" @click="activePerson = i">
            <div class="sps-name">{{ p.ho_ten || '—' }}</div>
            <div class="sps-row">
              <span class="sps-badge nv-badge">NV {{ scoreBadge(p.tu_danh_gia) }}</span>
              <span class="sps-badge hod-badge">HOD {{ scoreBadge(p.hod) }}</span>
            </div>
            <div v-if="overviews[i]" class="sps-ai-done">✓ AI đã phân tích</div>
          </div>

          <div class="sb-divider"></div>

          <!-- AI analysis step -->
          <button class="sb-btn-ai" :disabled="loadingAI" @click="analyzeAI">
            <span v-if="loadingAI" class="spinner"></span>
            <span v-else>🤖</span>
            {{ loadingAI ? aiMsg : (overviews.length ? '↻ Phân tích AI lại' : 'Phân tích AI') }}
          </button>
          <div class="ai-hint-line" v-if="!loadingAI && !overviews.length">
            Chỉnh sửa bảng xong rồi bấm phân tích AI (~20–30s)
          </div>
          <div class="ai-hint-line ai-done" v-if="!loadingAI && overviews.length">
            ✓ {{ overviews.length }} người đã được phân tích AI
          </div>

          <div class="sb-divider"></div>

          <button class="sb-btn-primary" :disabled="loadingExcel" @click="downloadExcel">
            <span v-if="loadingExcel" class="spinner"></span>
            <svg v-else width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            {{ loadingExcel ? excelMsg : '⬇ Xuất Excel tổng hợp' }}
          </button>

          <button class="sb-btn-secondary" @click="resetAll">↩ Scan lại</button>
        </div>
      </div>
    </aside>

    <!-- MAIN PANEL -->
    <main class="result-panel">
      <!-- Welcome -->
      <div v-if="step === 1 && !loading" class="welcome">
        <div class="welcome-icon">
          <svg width="56" height="56" viewBox="0 0 56 56" fill="none">
            <rect width="56" height="56" rx="18" fill="url(#wg2)"/>
            <text x="28" y="38" text-anchor="middle" font-size="26">👥</text>
            <defs><linearGradient id="wg2" x1="0" y1="0" x2="56" y2="56">
              <stop stop-color="#6366f1"/><stop offset="1" stop-color="#8b5cf6"/>
            </linearGradient></defs>
          </svg>
        </div>
        <h1>Báo Cáo Đánh Giá Nhân Sự</h1>
        <p>Upload tất cả phiếu đánh giá (file scan PDF). AI sẽ đọc từng phiếu, ghép NV tự đánh giá với HOD đánh giá, hiển thị đầy đủ từng tiêu chí A1–A5, B1–B7, C1–C4.</p>
        <div class="welcome-features">
          <div class="wf"><div class="wf-icon">📄</div><div>OCR GPT-4o Vision</div></div>
          <div class="wf"><div class="wf-icon">👥</div><div>Match NV ↔ HOD</div></div>
          <div class="wf"><div class="wf-icon">✏️</div><div>Chỉnh sửa bảng</div></div>
          <div class="wf"><div class="wf-icon">📊</div><div>Xuất Excel tổng hợp</div></div>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="loading-screen">
        <div class="loading-spinner"></div>
        <p>{{ loadingMsg }}</p>
        <p class="loading-sub">GPT-4o đang đọc {{ files.length }} file — khoảng {{ Math.round(files.length * 25 / 6) }}–{{ Math.round(files.length * 35 / 6) }} giây</p>
      </div>

      <!-- Results -->
      <div v-if="step === 2 && persons.length && !loading" class="results-scroll">
        <div v-if="isDirty" class="phieu-dirty-bar">
          ⚠️ Có thay đổi chưa lưu
          <button class="db-save" @click="isDirty = false">✓ Đã lưu</button>
        </div>

        <!-- Person tabs -->
        <div class="person-tabs">
          <button v-for="(p, i) in persons" :key="i"
            class="person-tab" :class="{ active: activePerson === i }"
            @click="activePerson = i">
            {{ p.ho_ten || `Người ${i+1}` }}
            <span class="ptab-xl" :class="xlClass((p.hod || p.tu_danh_gia || {})?.tong_hop?.xep_loai)">
              {{ normXl((p.hod || p.tu_danh_gia || {})?.tong_hop?.xep_loai) || '?' }}
            </span>
          </button>
        </div>

        <!-- Current person detail -->
        <div v-if="persons[activePerson]" class="person-detail">
          <PersonCard
            :person="persons[activePerson]"
            :idx="activePerson"
            :overview="overviews[activePerson] || null"
            @dirty="isDirty = true"
          />
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import PersonCard from './PersonCard.vue'

// ── State ─────────────────────────────────────────────────────────────
const step = ref(1)
const files = ref([])
const tried = ref(false)
const loading = ref(false)
const loadingMsg = ref('Đang quét phiếu...')
const loadingExcel = ref(false)
const excelMsg = ref('Đang xuất Excel...')
const loadingAI = ref(false)
const aiMsg = ref('AI đang phân tích...')
const error = ref('')
const persons = ref([])
const overviews = ref([])
const activePerson = ref(0)
const isDirty = ref(false)
const isDragging = ref(false)
const isHrDragging = ref(false)
const phongBan = ref('')
const hrFiles = ref([])

// ── File handling ──────────────────────────────────────────────────────
function addFiles(newFiles) {
  const pdfs = newFiles.filter(f => f.name.toLowerCase().endsWith('.pdf'))
  const existing = new Set(files.value.map(f => f.name))
  const fresh = pdfs.filter(f => !existing.has(f.name))
  files.value = [...files.value, ...fresh]
}

function onFolderChange(e) {
  addFiles(Array.from(e.target.files || []))
  e.target.value = ''
}

// Đọc đệ quy entries từ DataTransferItem (hỗ trợ folder drop)
async function _readEntry(entry) {
  if (entry.isFile) {
    return new Promise(resolve => entry.file(resolve, () => resolve(null)))
  }
  if (entry.isDirectory) {
    const reader = entry.createReader()
    const allFiles = []
    await new Promise(resolve => {
      function readBatch() {
        reader.readEntries(async entries => {
          if (!entries.length) { resolve(); return }
          for (const e of entries) {
            const result = await _readEntry(e)
            if (Array.isArray(result)) allFiles.push(...result)
            else if (result) allFiles.push(result)
          }
          readBatch()
        }, resolve)
      }
      readBatch()
    })
    return allFiles
  }
  return null
}

async function onDrop(e) {
  isDragging.value = false
  const items = Array.from(e.dataTransfer.items || [])
  if (items.length && items[0].webkitGetAsEntry) {
    const collected = []
    for (const item of items) {
      const entry = item.webkitGetAsEntry()
      if (!entry) continue
      const result = await _readEntry(entry)
      if (Array.isArray(result)) collected.push(...result)
      else if (result) collected.push(result)
    }
    addFiles(collected)
  } else {
    addFiles(Array.from(e.dataTransfer.files || []))
  }
}

function removeFile(i) { files.value.splice(i, 1) }

function onHrFilesChange(e) {
  const newXlsx = Array.from(e.target.files || [])
    .filter(f => f.name.toLowerCase().endsWith('.xlsx') || f.name.toLowerCase().endsWith('.xls'))
  const existing = new Set(hrFiles.value.map(f => f.name))
  hrFiles.value = [...hrFiles.value, ...newXlsx.filter(f => !existing.has(f.name))]
  e.target.value = ''
}

async function onHrDrop(e) {
  isHrDragging.value = false
  const items = Array.from(e.dataTransfer.items || [])
  const collected = []
  if (items.length && items[0].webkitGetAsEntry) {
    for (const item of items) {
      const entry = item.webkitGetAsEntry()
      if (!entry) continue
      const result = await _readEntry(entry)
      if (Array.isArray(result)) collected.push(...result)
      else if (result) collected.push(result)
    }
  } else {
    collected.push(...Array.from(e.dataTransfer.files || []))
  }
  const xlsx = collected.filter(f => f.name.toLowerCase().endsWith('.xlsx') || f.name.toLowerCase().endsWith('.xls'))
  const existing = new Set(hrFiles.value.map(f => f.name))
  hrFiles.value = [...hrFiles.value, ...xlsx.filter(f => !existing.has(f.name))]
}

function removeHrFile(i) { hrFiles.value.splice(i, 1) }
function shortHrName(name) { return name.length <= 28 ? name : '…' + name.slice(-25) }

function shortName(name) {
  if (name.length <= 32) return name
  return '…' + name.slice(-29)
}

// ── CSRF ──────────────────────────────────────────────────────────────
function csrf() {
  return document.cookie.split(';').find(c => c.trim().startsWith('X-Frappe-CSRF-Token='))
    ?.split('=')[1]?.trim() || ''
}

async function callApi(url, opts) {
  const r = await fetch(url, opts)
  if (!r.ok) {
    let msg = `HTTP ${r.status}`
    try { const j = await r.json(); msg = j._server_messages || j.message || msg } catch {}
    throw new Error(msg)
  }
  return r.json()
}

// ── OCR batch ─────────────────────────────────────────────────────────
async function doOCR() {
  tried.value = true
  if (!files.value.length) return
  loading.value = true
  error.value = ''
  loadingMsg.value = `Đang upload ${files.value.length} file...`
  try {
    const fd = new FormData()
    files.value.forEach((f, i) => fd.append(`file${i}`, f, f.name))
    hrFiles.value.forEach((f, i) => fd.append(`file_hr_${i}`, f, f.name))
    loadingMsg.value = `GPT-4o đang đọc ${files.value.length} phiếu song song...`
    const res = await callApi(
      '/api/method/cnb_2as.api.bao_cao_danh_gia.ocr_batch_upload',
      { method: 'POST', headers: { 'X-Frappe-CSRF-Token': csrf() }, body: fd }
    )
    if (!res.message?.ok) throw new Error(res.message?.error || 'OCR thất bại')
    persons.value = res.message.persons
    activePerson.value = 0
    step.value = 2
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

// ── AI analyze step ───────────────────────────────────────────────────
async function analyzeAI() {
  loadingAI.value = true
  aiMsg.value = `AI đang phân tích ${persons.value.length} người...`
  try {
    const fd = new FormData()
    fd.append('data', JSON.stringify(persons.value))
    const res = await callApi(
      '/api/method/cnb_2as.api.bao_cao_danh_gia.analyze_ai',
      { method: 'POST', headers: { 'X-Frappe-CSRF-Token': csrf() }, body: fd }
    )
    if (!res.message?.ok) throw new Error(res.message?.error || 'Phân tích thất bại')
    overviews.value = res.message.overviews
  } catch (e) {
    alert(`Lỗi phân tích AI: ${e.message}`)
  } finally {
    loadingAI.value = false
  }
}

// ── Excel export ──────────────────────────────────────────────────────
async function downloadExcel() {
  loadingExcel.value = true
  excelMsg.value = 'Đang xuất Excel...'
  try {
    const fd = new FormData()
    fd.append('data', JSON.stringify(persons.value))
    if (overviews.value.length) {
      fd.append('overviews', JSON.stringify(overviews.value))
    }
    if (phongBan.value) fd.append('phong_ban', phongBan.value)
    hrFiles.value.forEach((f, i) => fd.append(`file_hr_${i}`, f, f.name))
    const r = await fetch('/api/method/cnb_2as.api.bao_cao_danh_gia.export_excel', {
      method: 'POST',
      headers: { 'X-Frappe-CSRF-Token': csrf() },
      body: fd
    })
    if (!r.ok) throw new Error(`HTTP ${r.status}`)
    excelMsg.value = 'Đang tải file...'
    const blob = await r.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const slug = phongBan.value ? `_${phongBan.value.replace(/\s+/g, '_')}` : ''
    a.download = `bao_cao_danh_gia${slug}.xlsx`
    document.body.appendChild(a); a.click(); a.remove()
    URL.revokeObjectURL(url)
  } catch (e) {
    alert(`Lỗi tải Excel: ${e.message}`)
  } finally {
    loadingExcel.value = false
  }
}

// ── HR template download (pre-filled với tên từ scan) ────────────────
async function downloadHrTemplate() {
  try {
    const fd = new FormData()
    if (persons.value.length) fd.append('data', JSON.stringify(persons.value))
    const r = await fetch('/api/method/cnb_2as.api.bao_cao_danh_gia.download_hr_template', {
      method: 'POST',
      headers: { 'X-Frappe-CSRF-Token': csrf() },
      body: fd
    })
    if (!r.ok) throw new Error(`HTTP ${r.status}`)
    const blob = await r.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'template_hr_data.xlsx'
    document.body.appendChild(a); a.click(); a.remove()
    URL.revokeObjectURL(url)
  } catch (e) {
    alert(`Lỗi tải template: ${e.message}`)
  }
}

// ── Helpers ───────────────────────────────────────────────────────────
function normXl(v) {
  if (!v) return ''
  const m = String(v).match(/[A-Ea-e]/)
  return m ? m[0].toUpperCase() : v
}
function scoreBadge(d) {
  const t = d?.tong_hop?.tong_diem_100
  const xl = normXl(d?.tong_hop?.xep_loai)
  if (t == null && !xl) return '—'
  return t != null ? `${t}đ ${xl}` : xl
}
function xlClass(v) {
  return { A: 'xl-a', B: 'xl-b', C: 'xl-c', D: 'xl-d', E: 'xl-e' }[normXl(v)] || ''
}

function resetAll() {
  step.value = 1
  files.value = []
  hrFiles.value = []
  tried.value = false
  error.value = ''
  isDirty.value = false
  isDragging.value = false
  isHrDragging.value = false
  persons.value = []
  overviews.value = []
  activePerson.value = 0
}
</script>

<style scoped>
/* ── Layout ───────────────────────────────────────────────────────── */
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
.sb-logo-mark { width: 34px; height: 34px; background: linear-gradient(135deg,#6366f1,#8b5cf6); border-radius: 10px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.sb-name { font-weight: 700; font-size: .84rem; }
.sb-org { font-size: .7rem; color: #64748b; }

.sb-body { flex: 1; overflow-y: auto; padding: 14px; }
.sb-section-title { font-size: .78rem; font-weight: 700; color: #6366f1; text-transform: uppercase; letter-spacing: .05em; margin-bottom: 12px; }

/* Multi-file upload */
.sb-upload-multi {
  border: 2px dashed rgba(99,102,241,.3); border-radius: 12px; min-height: 100px;
  cursor: pointer; transition: all .2s; margin-bottom: 8px; padding: 12px;
}
.sb-upload-multi:hover { border-color: #6366f1; background: rgba(99,102,241,.05); }
.sb-upload-multi.filled { border-style: solid; border-color: #6366f1; background: rgba(99,102,241,.04); }
.sb-upload-multi.err { border-color: #ef4444; }

.sb-upload-multi.dropping { border-color: #6366f1; background: rgba(99,102,241,.1); transform: scale(1.01); }

.upm-empty { display: flex; flex-direction: column; align-items: center; gap: 7px; padding: 14px 0; }
.upm-icon { font-size: 26px; }
.upm-hint { font-size: .74rem; color: #94a3b8; text-align: center; line-height: 1.5; }

.upm-list { display: flex; flex-direction: column; gap: 4px; max-height: 200px; overflow-y: auto; }
.upm-item { display: flex; align-items: center; gap: 6px; padding: 4px 6px; background: rgba(99,102,241,.06); border-radius: 6px; }
.upm-item-name { font-size: .71rem; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #a5b4fc; }
.upm-rm { background: none; border: none; cursor: pointer; color: #ef4444; font-size: 11px; flex-shrink: 0; }

.sb-file-count { display: flex; align-items: center; gap: 7px; font-size: .74rem; color: #94a3b8; margin-bottom: 8px; }
.fc-badge { background: #6366f1; color: white; border-radius: 10px; padding: 1px 7px; font-size: .7rem; font-weight: 700; }
.fc-clear { background: none; border: none; color: #ef4444; cursor: pointer; font-size: .72rem; margin-left: auto; }

.sb-btn-primary {
  width: 100%; padding: 9px 12px; border-radius: 10px; border: none; cursor: pointer;
  background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white;
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

.sb-divider { height: 1px; background: rgba(99,102,241,.12); margin: 10px 0; }
body.theme-light .sb-divider { background: #e2e8f0; }

.sps-ai-done { font-size: .66rem; color: #34d399; margin-top: 4px; }

.sb-btn-ai {
  width: 100%; padding: 9px 12px; border-radius: 10px; border: 1.5px solid rgba(251,191,36,.4);
  cursor: pointer; background: rgba(251,191,36,.1); color: #92400e;
  font-weight: 700; font-size: .84rem; display: flex; align-items: center; justify-content: center;
  gap: 7px; transition: all .2s; margin-bottom: 5px;
}
body.theme-dark .sb-btn-ai { color: #fbbf24; background: rgba(251,191,36,.08); }
.sb-btn-ai:hover:not(:disabled) { background: rgba(251,191,36,.18); border-color: #fbbf24; }
.sb-btn-ai:disabled { opacity: .6; cursor: not-allowed; }

.ai-hint-line { font-size: .7rem; color: #64748b; text-align: center; margin-bottom: 6px; padding: 0 4px; line-height: 1.5; }
.ai-hint-line.ai-done { color: #34d399; font-weight: 600; }

.sb-err { color: #ef4444; font-size: .76rem; margin-top: 4px; }
.sb-err-box { margin-top: 8px; padding: 9px; background: rgba(239,68,68,.1); border-radius: 8px; color: #ef4444; font-size: .78rem; }
.spinner { width: 13px; height: 13px; border: 2px solid rgba(255,255,255,.3); border-top-color: #fff; border-radius: 50%; animation: spin .7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg) } }

/* Person stats in sidebar */
.sb-person-stat {
  margin-bottom: 8px; padding: 9px 10px; background: rgba(99,102,241,.05);
  border-radius: 10px; cursor: pointer; border: 1px solid transparent; transition: all .2s;
}
.sb-person-stat.active { border-color: #6366f1; background: rgba(99,102,241,.12); }
.sb-person-stat:hover { border-color: rgba(99,102,241,.3); }
.sps-name { font-size: .8rem; font-weight: 700; margin-bottom: 5px; }
.sps-row { display: flex; gap: 5px; }
.sps-badge { font-size: .65rem; font-weight: 700; padding: 2px 7px; border-radius: 8px; }
.nv-badge { background: rgba(59,130,246,.15); color: #60a5fa; }
.hod-badge { background: rgba(16,185,129,.15); color: #34d399; }

/* ── Main panel ───────────────────────────────────────────────────── */
.result-panel { flex: 1; overflow: hidden; display: flex; flex-direction: column; }

.welcome { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 40px; text-align: center; }
.welcome-icon { margin-bottom: 22px; }
.welcome h1 { font-size: 1.7rem; font-weight: 800; margin-bottom: 10px; }
.welcome p { color: #94a3b8; max-width: 460px; line-height: 1.7; margin-bottom: 24px; }
.welcome-features { display: flex; gap: 10px; flex-wrap: wrap; justify-content: center; }
.wf { display: flex; align-items: center; gap: 7px; background: rgba(99,102,241,.08); padding: 9px 14px; border-radius: 10px; font-size: .8rem; font-weight: 600; }
.wf-icon { font-size: 17px; }

.loading-screen { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 14px; }
.loading-spinner { width: 48px; height: 48px; border: 4px solid rgba(99,102,241,.2); border-top-color: #6366f1; border-radius: 50%; animation: spin .9s linear infinite; }
.loading-sub { color: #64748b; font-size: .84rem; }

.results-scroll { flex: 1; overflow-y: auto; padding: 16px 24px 48px; }

.phieu-dirty-bar {
  position: sticky; top: -16px; z-index: 10;
  background: rgba(251,191,36,.15); border: 1px solid rgba(251,191,36,.4);
  border-radius: 10px; padding: 9px 14px; margin-bottom: 12px;
  display: flex; align-items: center; gap: 10px; font-size: .84rem; font-weight: 600;
}
.db-save { background: #6366f1; color: white; border: none; border-radius: 6px; padding: 3px 10px; cursor: pointer; font-size: .8rem; }

/* Person tabs */
.person-tabs { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 16px; }
.person-tab {
  padding: 7px 14px; border-radius: 20px; border: 1px solid rgba(99,102,241,.25);
  background: rgba(99,102,241,.05); cursor: pointer; font-size: .82rem; font-weight: 600;
  color: inherit; transition: all .2s; display: flex; align-items: center; gap: 7px;
}
.person-tab.active { background: #6366f1; color: white; border-color: #6366f1; }
.person-tab:hover:not(.active) { border-color: #6366f1; background: rgba(99,102,241,.1); }
.ptab-xl { font-size: .7rem; font-weight: 800; padding: 1px 6px; border-radius: 6px; }
.xl-a { background: #d1fae5; color: #065f46; }
.xl-b { background: #dbeafe; color: #1e3a8a; }
.xl-c { background: #fef9c3; color: #713f12; }
.xl-d { background: #fee2e2; color: #7f1d1d; }
.xl-e { background: #f3f4f6; color: #374151; }
.person-tab.active .ptab-xl { background: rgba(255,255,255,.25); color: white; }

/* ── Phòng ban input ──────────────────────────────────────────────── */
.sb-field { margin-bottom: 12px; }
.sb-label { display: block; font-size: .72rem; font-weight: 600; color: #6366f1; margin-bottom: 5px; letter-spacing: .04em; text-transform: uppercase; }
.sb-input {
  width: 100%; padding: 7px 10px; border-radius: 8px; border: 1px solid rgba(99,102,241,.3);
  background: rgba(99,102,241,.05); color: inherit; font-size: .82rem; outline: none;
  transition: border-color .2s; box-sizing: border-box;
}
.sb-input:focus { border-color: #6366f1; background: rgba(99,102,241,.08); }
.sb-input::placeholder { color: #64748b; }
body.theme-light .sb-input { background: #f8fafc; border-color: #e2e8f0; }
body.theme-light .sb-input:focus { border-color: #6366f1; background: #fff; }
.hr-tmpl-link { font-size: .7rem; color: #6366f1; text-decoration: none; opacity: .8; background: none; border: none; cursor: pointer; }
.hr-tmpl-link:hover { opacity: 1; text-decoration: underline; }

.hr-drop-zone {
  border: 1.5px dashed rgba(99,102,241,.3); border-radius: 8px; cursor: pointer;
  padding: 8px 10px; min-height: 44px; transition: all .2s; background: rgba(99,102,241,.03);
  box-sizing: border-box;
}
.hr-drop-zone:hover { border-color: #6366f1; background: rgba(99,102,241,.07); }
.hr-drop-zone.hr-has-files { border-style: solid; border-color: rgba(99,102,241,.45); }
.hr-drop-zone.hr-dropping { border-color: #6366f1; background: rgba(99,102,241,.1); transform: scale(1.01); }
.hr-empty-hint { font-size: .72rem; color: #64748b; text-align: center; line-height: 1.6; padding: 4px 0; }
.hr-empty-hint small { font-size: .67rem; color: #475569; }
.hr-file-list { display: flex; flex-direction: column; gap: 3px; }
.hr-file-item { display: flex; align-items: center; gap: 5px; padding: 2px 4px; background: rgba(99,102,241,.06); border-radius: 5px; }
.hr-file-name { font-size: .7rem; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #a5b4fc; }
.hr-rm { background: none; border: none; color: #f87171; cursor: pointer; font-size: .7rem; padding: 0 2px; flex-shrink: 0; }
.hr-count-line { font-size: .7rem; color: #64748b; display: flex; align-items: center; gap: 6px; margin-top: 4px; }
/* ── PersonCard component styles (injected globally to pierce scoped) ── */
</style>

