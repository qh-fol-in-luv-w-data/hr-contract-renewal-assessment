<template>
  <div class="app">

    <!-- ══ SIDEBAR ══ -->
    <aside class="sidebar">
      <div class="sb-top">
        <div class="sb-logo">
          <div class="sb-logo-mark">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5"><path d="M12 3L3 9v12h6v-6h6v6h6V9L12 3z"/></svg>
          </div>
          <div>
            <div class="sb-name">AI Thử Việc</div>
            <div class="sb-org">CT Group</div>
          </div>
        </div>
      </div>

      <nav class="sb-nav">
        <div class="sb-section">
          <div class="sb-section-title">Hồ sơ</div>

          <div class="sb-upload-card" :class="{upc__filled: docxFile, upc__err: !docxFile&&tried}"
            @dragover.prevent @drop.prevent="dropSb($event,'docx')" @click="$refs.rDocx.click()">
            <input ref="rDocx" type="file" accept=".docx" hidden @change="e=>docxFile=e.target.files[0]||null"/>
            <div class="upc-icon">{{ docxFile?'📝':'📄' }}</div>
            <div class="upc-info">
              <div class="upc-label">Phiếu đánh giá</div>
              <div class="upc-val" :class="docxFile?'upc-ok':'upc-empty'">{{ docxFile ? shortName(docxFile.name,22) : '.docx – Click để chọn' }}</div>
            </div>
            <button v-if="docxFile" class="upc-rm" @click.stop="docxFile=null">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
          </div>

          <div class="sb-upload-card" :class="{upc__filled: xlsxFile, upc__err: !xlsxFile&&tried}"
            @dragover.prevent @drop.prevent="dropSb($event,'xlsx')" @click="$refs.rXlsx.click()">
            <input ref="rXlsx" type="file" accept=".xlsx" hidden @change="e=>xlsxFile=e.target.files[0]||null"/>
            <div class="upc-icon">{{ xlsxFile?'📊':'📋' }}</div>
            <div class="upc-info">
              <div class="upc-label">Bảng KPI</div>
              <div class="upc-val" :class="xlsxFile?'upc-ok':'upc-empty'">{{ xlsxFile ? shortName(xlsxFile.name,22) : '.xlsx – Click để chọn' }}</div>
            </div>
            <button v-if="xlsxFile" class="upc-rm" @click.stop="xlsxFile=null">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
          </div>

          <p v-if="tried&&(!docxFile||!xlsxFile)" class="sb-err-msg">Cần upload đủ 2 file</p>

          <button class="sb-analyze-btn" :disabled="loading" @click="doReview">
            <span v-if="loading" class="btn-spin"></span>
            <svg v-else width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
            {{ loading ? 'Đang phân tích...' : 'Phân tích ngay' }}
          </button>
        </div>

        <div v-if="reviewResult" class="sb-section">
          <div class="sb-section-title">Kết quả</div>
          <div class="sb-result-badge" :class="reviewResult.status==='ĐẠT'?'rb-pass':'rb-fail'">
            <div class="rb-icon">{{ reviewResult.status==='ĐẠT'?'✓':'!' }}</div>
            <div class="rb-text">{{ reviewResult.status==='ĐẠT'?'Hồ sơ đạt yêu cầu':'Cần bổ sung thêm' }}</div>
          </div>
          <div class="sb-counts">
            <div class="sc-item">
              <div class="sc-val sc-warn">{{ reviewResult.van_de?.length ?? 0 }}</div>
              <div class="sc-lbl">Vấn đề</div>
            </div>
            <div class="sc-item">
              <div class="sc-val sc-ok">{{ reviewResult.xlsx_kpi?.filter(r=>r.status==='OK').length??0 }}</div>
              <div class="sc-lbl">KPI đạt</div>
            </div>
            <div class="sc-item">
              <div class="sc-val sc-bad">{{ (reviewResult.xlsx_kpi?.filter(r=>r.status==='THIẾU').length??0) + (reviewResult.xlsx_kpi?.filter(r=>r.status==='CẢNH BÁO').length??0) }}</div>
              <div class="sc-lbl">Thiếu MC</div>
            </div>
          </div>
          <button class="sb-pdf-btn" @click="exportPdf">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
            Xuất báo cáo PDF
          </button>
        </div>
      </nav>

      <div class="sb-footer">
        <div class="sb-session" :class="sessionId?'sf-on':'sf-off'">
          <div class="sf-dot"></div>
          <span>{{ sessionId ? 'Phiên đang hoạt động' : 'Chưa có phiên' }}</span>
        </div>
      </div>
    </aside>

    <!-- ══ CHAT ══ -->
    <main class="chat-area">

      <!-- Messages -->
      <div class="msg-list" ref="msgBox">

        <!-- Welcome -->
        <div v-if="!msgs.length" class="welcome-screen">
          <div class="ws-icon">
            <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
              <rect width="48" height="48" rx="16" fill="url(#wg)"/>
              <text x="24" y="32" text-anchor="middle" font-size="22">⚖️</text>
              <defs>
                <linearGradient id="wg" x1="0" y1="0" x2="48" y2="48">
                  <stop stop-color="#6366f1"/><stop offset="1" stop-color="#8b5cf6"/>
                </linearGradient>
              </defs>
            </svg>
          </div>
          <h1 class="ws-title">AI Đánh Giá Thử Việc</h1>
          <p class="ws-desc">Upload phiếu đánh giá và bảng KPI ở thanh bên, bấm <b>Phân tích ngay</b>.<br>AI sẽ kiểm tra và yêu cầu bổ sung cho đến khi hồ sơ hoàn thiện.</p>
          <div class="ws-features">
            <div class="wsf">
              <div class="wsf-icon">📝</div>
              <div class="wsf-text">Kiểm tra câu từ, ngữ nghĩa, số liệu cụ thể</div>
            </div>
            <div class="wsf">
              <div class="wsf-icon">📊</div>
              <div class="wsf-text">Kiểm tra KPI, tỷ lệ thực hiện, link minh chứng</div>
            </div>
            <div class="wsf">
              <div class="wsf-icon">🔄</div>
              <div class="wsf-text">Upload file đã chỉnh → AI kiểm tra lại ngay</div>
            </div>
          </div>
        </div>

        <!-- Messages -->
        <template v-for="(m,i) in msgs" :key="i">

          <!-- User -->
          <div v-if="m.role==='user'" class="bubble-row bubble-row--user">
            <div class="bubble bubble--user">
              <div v-if="m.files?.length" class="bubble-files">
                <div v-for="f in m.files" :key="f" class="bfile">
                  <div class="bfile-icon">{{ f.endsWith('.docx')?'📝':'📊' }}</div>
                  <div class="bfile-name">{{ f }}</div>
                </div>
              </div>
              <div v-if="m.text" class="bubble-text">{{ m.text }}</div>
            </div>
          </div>

          <!-- AI -->
          <div v-if="m.role==='ai'" class="bubble-row bubble-row--ai">
            <div class="ai-av">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5"><path d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z"/></svg>
            </div>
            <div class="ai-content">
              <div v-if="m.text" class="bubble bubble--ai" v-html="fmt(m.text)"></div>

              <div v-if="m.result" class="result-card">
                <!-- Verdict -->
                <div class="rc-top" :class="m.result.status==='ĐẠT'?'rct-pass':'rct-fail'">
                  <span class="rct-badge">{{ m.result.status==='ĐẠT'?'✓  ĐẠT':'✗  CHƯA ĐẠT – CẦN BỔ SUNG' }}</span>
                  <p class="rct-desc">{{ m.result.tong_quan }}</p>
                </div>

                <!-- Issues -->
                <div v-if="m.result.van_de?.length" class="rc-block">
                  <button class="rcb-toggle" @click="toggle(i,'issues')">
                    <span class="rcb-t-icon rcb-warn">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/></svg>
                    </span>
                    <span class="rcb-t-label">{{ m.result.van_de.length }} vấn đề cần bổ sung</span>
                    <span class="rcb-t-arrow" :class="{open:sec[i]?.issues}">›</span>
                  </button>
                  <transition name="acc"><div v-if="sec[i]?.issues" class="rcb-body">
                    <div v-for="(v,vi) in m.result.van_de" :key="vi" class="issue-item" :class="`ii-${(v.loai||'chung').toLowerCase()}`">
                      <div class="ii-meta">
                        <span class="ii-tag">{{ v.loai }}</span>
                        <span v-if="v.nhom_tieu_chi" class="ii-criteria-badge">{{ v.nhom_tieu_chi }}</span>
                        <span class="ii-section">{{ v.muc }}</span>
                      </div>
                      <div class="ii-problem">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" class="ii-prob-icon"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                        {{ v.van_de }}
                      </div>
                      <div class="ii-fix">
                        <span class="ii-arrow">→</span>
                        <span><strong>Cần làm:</strong> {{ v.yeu_cau }}</span>
                      </div>
                      <div class="ii-where">
                        <span class="ii-file-badge" :class="v.loai==='WORD'?'badge-word':v.loai==='EXCEL'?'badge-excel':'badge-chung'">{{ v.loai==='WORD'?'📝 Sửa ở file Word':v.loai==='EXCEL'?'📊 Sửa ở file Excel':'⚠️ Cả hai file' }}</span>
                        <span class="ii-reup-hint">→ Upload lại file ở ô chat bên dưới</span>
                      </div>
                    </div>
                  </div></transition>
                  <!-- ↑ Re-upload CTA after issues -->
                  <div v-if="m.result.van_de?.length" class="reup-cta">
                    <div class="reup-cta-left">
                      <div class="reup-cta-icon">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12"/></svg>
                      </div>
                      <div>
                        <div class="reup-cta-title">Đã sửa xong? Upload lại file tại đây ↓</div>
                        <div class="reup-cta-desc">Dùng nút 📎 ở ô chat bên dưới để đính kèm file Word/Excel đã chỉnh, rồi bấm gửi để AI kiểm tra lại.</div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- KPI -->
                <div v-if="m.result.xlsx_kpi?.length" class="rc-block">
                  <button class="rcb-toggle" @click="toggle(i,'kpi')">
                    <span class="rcb-t-icon rcb-blue">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2"/></svg>
                    </span>
                    <span class="rcb-t-label">Bảng KPI – {{ m.result.xlsx_kpi.length }} mục</span>
                    <span class="rcb-kpi-pills">
                      <span class="kp ok">{{ m.result.xlsx_kpi.filter(r=>r.status==='OK').length }} đạt</span>
                      <span class="kp miss">{{ m.result.xlsx_kpi.filter(r=>r.status==='THIẾU').length }} thiếu</span>
                      <span class="kp warn">{{ m.result.xlsx_kpi.filter(r=>r.status==='CẢNH BÁO').length }} cảnh báo</span>
                    </span>
                    <span class="rcb-t-arrow" :class="{open:sec[i]?.kpi}">›</span>
                  </button>
                  <transition name="acc"><div v-if="sec[i]?.kpi" class="rcb-body">
                    <div class="kpi-list">
                      <div v-for="r in m.result.xlsx_kpi" :key="r.stt" class="kpi-item" :class="r.status==='THIẾU'?'ki-miss':r.status==='CẢNH BÁO'?'ki-warn':'ki-ok'">
                        <div class="ki-row1">
                          <span class="ki-stt">{{ r.stt }}</span>
                          <span class="ki-name">{{ r.cong_viec }}</span>
                          <span class="ki-chip" :class="r.status==='OK'?'kc-ok':r.status==='CẢNH BÁO'?'kc-warn':'kc-miss'">{{ r.status }}</span>
                        </div>
                        <div class="ki-row2">
                          <span>Tỷ lệ: <b>{{ r.ty_le_thuc_hien!=null?(r.ty_le_thuc_hien*100).toFixed(0)+'%':'—' }}</b></span>
                          <span>KQ: <b>{{ r.ket_qua||'—' }}</b></span>
                          <span v-if="r.link_minh_chung?.startsWith('http')"><a :href="r.link_minh_chung" target="_blank" class="ki-lnk">🔗 Minh chứng</a></span>
                          <span v-else-if="r.link_minh_chung" class="ki-lnk">✅ {{ r.link_minh_chung.length > 30 ? r.link_minh_chung.slice(0,30)+'…' : r.link_minh_chung }}</span>
                          <span v-else class="ki-no-lnk">❌ Chưa có minh chứng</span>
                        </div>
                        <div v-if="r.issues?.length" class="ki-issues">
                          <span v-for="(iss,ii) in r.issues" :key="ii" class="ki-issue-chip">{{ iss }}</span>
                        </div>
                      </div>
                    </div>
                  </div></transition>
                </div>

                <!-- Strengths -->
                <div v-if="m.result.uu_diem?.length" class="rc-block">
                  <button class="rcb-toggle" @click="toggle(i,'good')">
                    <span class="rcb-t-icon rcb-green">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 13l4 4L19 7"/></svg>
                    </span>
                    <span class="rcb-t-label">{{ m.result.uu_diem.length }} điểm tốt</span>
                    <span class="rcb-t-arrow" :class="{open:sec[i]?.good}">›</span>
                  </button>
                  <transition name="acc"><div v-if="sec[i]?.good" class="rcb-body">
                    <ul class="good-ul">
                      <li v-for="(g,gi) in m.result.uu_diem" :key="gi">{{ g }}</li>
                    </ul>
                    <div v-if="m.result.luu_y_chung" class="note-ln">📌 {{ m.result.luu_y_chung }}</div>
                  </div></transition>
                </div>
              </div>
            </div>
          </div>

        </template>

        <!-- Typing -->
        <div v-if="loading||chatLoading" class="bubble-row bubble-row--ai">
          <div class="ai-av">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="1.5"><path d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z"/></svg>
          </div>
          <div class="typing-bubble">
            <span></span><span></span><span></span>
            <span class="typing-txt">{{ loading?'Đang phân tích hồ sơ…':'AI đang soạn phản hồi…' }}</span>
          </div>
        </div>
      </div>

      <!-- ══ INPUT BAR (GPT style) ══ -->
      <div class="input-area">
        <!-- File previews (GPT style) -->
        <div v-if="chatDocx||chatXlsx" class="file-previews">
          <div v-if="chatDocx" class="fp-item">
            <div class="fp-thumb fp-docx">📝</div>
            <div class="fp-meta">
              <div class="fp-name">{{ shortName(chatDocx.name,20) }}</div>
              <div class="fp-type">Word Document</div>
            </div>
            <button class="fp-rm" @click="chatDocx=null">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
          </div>
          <div v-if="chatXlsx" class="fp-item">
            <div class="fp-thumb fp-xlsx">📊</div>
            <div class="fp-meta">
              <div class="fp-name">{{ shortName(chatXlsx.name,20) }}</div>
              <div class="fp-type">Excel Spreadsheet</div>
            </div>
            <button class="fp-rm" @click="chatXlsx=null">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
          </div>
        </div>

        <!-- Input box -->
        <div class="input-box" :class="{'ib-focus': inputFocused}">
          <div class="ib-left">
            <!-- Attach -->
            <div class="attach-menu" v-if="sessionId">
              <button class="attach-btn" @click="showAttach=!showAttach" title="Đính kèm file">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"/></svg>
              </button>
              <div v-if="showAttach" class="attach-dropdown">
                <label class="attach-opt">
                  <input type="file" accept=".docx" hidden @change="e=>{chatDocx=e.target.files[0];showAttach=false}"/>
                  <span>📝</span> Word mới (.docx)
                </label>
                <label class="attach-opt">
                  <input type="file" accept=".xlsx" hidden @change="e=>{chatXlsx=e.target.files[0];showAttach=false}"/>
                  <span>📊</span> Excel mới (.xlsx)
                </label>
              </div>
            </div>
            <div v-else class="attach-btn attach-btn--off" title="Phân tích hồ sơ trước">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" opacity=".35"><path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"/></svg>
            </div>
          </div>

          <textarea
            v-model="chatMsg"
            class="ib-textarea"
            :disabled="!sessionId||chatLoading"
            :placeholder="sessionId?'Hỏi về hồ sơ hoặc để trống và đính kèm file đã chỉnh để kiểm tra lại...':'Phân tích hồ sơ trước để bắt đầu chat'"
            rows="1"
            @input="grow($event)"
            @focus="inputFocused=true;showAttach=false"
            @blur="inputFocused=false"
            @keydown.enter.exact.prevent="send"
          ></textarea>

          <button class="send-btn"
            :disabled="!sessionId||chatLoading||(!chatMsg.trim()&&!chatDocx&&!chatXlsx)"
            @click="send">
            <svg v-if="!chatLoading" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M3.478 2.405a.75.75 0 00-.926.94l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.405z"/></svg>
            <span v-else class="btn-spin btn-spin--sm"></span>
          </button>
        </div>
        <div class="ib-hint">AI hỗ trợ nhân viên kiểm tra hồ sơ trước khi nộp · CT Group 2026</div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, reactive, nextTick } from 'vue'

const docxFile = ref(null), xlsxFile = ref(null)
const tried = ref(false), loading = ref(false)
const sessionId = ref(''), reviewResult = ref(null)
const msgs = ref([])
const chatMsg = ref(''), chatDocx = ref(null), chatXlsx = ref(null)
const chatLoading = ref(false)
const msgBox = ref(null)
const sec = reactive({})
const showAttach = ref(false)
const inputFocused = ref(false)

function dropSb(e, t) {
  const f = e.dataTransfer.files[0]
  if (t === 'docx' && f?.name.endsWith('.docx')) docxFile.value = f
  if (t === 'xlsx' && f?.name.endsWith('.xlsx')) xlsxFile.value = f
}
function toggle(idx, key) {
  if (!sec[idx]) sec[idx] = {}
  sec[idx][key] = !sec[idx][key]
}

const BASE = '/api/method/ats_danhgiathuviec.api'
function csrf() { return document.cookie.split('; ').find(r => r.startsWith('csrf_token='))?.split('=')[1] || '' }
async function apiCall(ep, fd) {
  const r = await fetch(`${BASE}.${ep}`, { method: 'POST', body: fd, headers: { 'X-Frappe-CSRF-Token': csrf() } })
  let j
  try {
    const text = await r.text()
    j = text ? JSON.parse(text) : {}
  } catch {
    throw new Error(`Lỗi kết nối máy chủ (HTTP ${r.status}). Vui lòng thử lại.`)
  }
  if (!r.ok) throw new Error(j?.exception || j?.message || `HTTP ${r.status}`)
  return j.message ?? j
}

async function doReview() {
  tried.value = true
  if (!docxFile.value || !xlsxFile.value) return
  loading.value = true
  // Reset session & messages → mỗi lần upload là 1 session mới hoàn toàn
  sessionId.value = ''
  msgs.value = []
  const names = [docxFile.value.name, xlsxFile.value.name]
  msgs.value.push({ role: 'user', text: 'Phân tích hồ sơ thử việc', files: names })
  await scroll()
  try {
    const fd = new FormData()
    fd.append('docx_file', docxFile.value)
    fd.append('xlsx_file', xlsxFile.value)
    // Không gửi session_id → server luôn tạo session mới
    const d = await apiCall('review_files', fd)
    sessionId.value = d.session_id
    reviewResult.value = d
    const idx = msgs.value.length
    msgs.value.push({ role: 'ai', text: '', result: d })
    sec[idx] = { issues: true, kpi: false, good: false }
  } catch (e) { msgs.value.push({ role: 'ai', text: '❌ Lỗi: ' + e.message }) }
  finally { loading.value = false; await scroll() }
}

async function send() {
  if (!sessionId.value) return
  const msg = chatMsg.value.trim()
  if (!msg && !chatDocx.value && !chatXlsx.value) return
  const att = []
  if (chatDocx.value) att.push(chatDocx.value.name)
  if (chatXlsx.value) att.push(chatXlsx.value.name)
  msgs.value.push({ role: 'user', text: msg || '', files: att })
  chatMsg.value = ''; chatLoading.value = true; await scroll()
  try {
    const fd = new FormData()
    fd.append('session_id', sessionId.value)
    if (msg) fd.append('message', msg)
    if (chatDocx.value) fd.append('docx_file', chatDocx.value)
    if (chatXlsx.value) fd.append('xlsx_file', chatXlsx.value)
    const d = await apiCall('chat_review', fd)
    const idx = msgs.value.length
    if (d.re_review) {
      reviewResult.value = { ...reviewResult.value, ...d.re_review }
      msgs.value.push({ role: 'ai', text: d.reply || '', result: d.re_review })
      sec[idx] = { issues: true, kpi: false, good: false }
    } else {
      msgs.value.push({ role: 'ai', text: d.reply || '' })
    }
    chatDocx.value = null; chatXlsx.value = null
  } catch (e) { msgs.value.push({ role: 'ai', text: '❌ Lỗi: ' + e.message }) }
  finally { chatLoading.value = false; await scroll() }
}

async function scroll() { await nextTick(); if (msgBox.value) msgBox.value.scrollTop = msgBox.value.scrollHeight }
function fmt(t) { return (t || '').replace(/\n/g, '<br>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') }
function shortName(n, len = 18) { return n.length > len ? n.slice(0, len - 2) + '…' : n }
function grow(e) {
  e.target.style.height = 'auto'
  e.target.style.height = Math.min(e.target.scrollHeight, 160) + 'px'
}

function exportPdf() {
  const r = reviewResult.value
  if (!r) return
  const isPass = r.status === 'ĐẠT'
  const now = new Date().toLocaleDateString('vi-VN', { day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit' })
  const accentColor = isPass ? '#059669' : '#d97706'
  const accentLight = isPass ? '#ecfdf5' : '#fffbeb'
  const accentBorder = isPass ? '#a7f3d0' : '#fde68a'

  // ── Thông tin nhân viên & HOD ─────────────────────────────────────────────
  const nv = r.thong_tin_nhan_vien || {}
  const infoField = (label, val, icon = '') =>
    val ? `<div style="display:flex;gap:6px;align-items:baseline;font-size:.9rem;padding:5px 0;border-bottom:1px solid #f1f5f9">
      <span style="min-width:140px;color:#94a3b8;font-size:.8rem;font-weight:600;text-transform:uppercase;letter-spacing:.04em">${icon} ${label}</span>
      <span style="font-weight:600;color:#111827">${val}</span>
    </div>` : ''

  const nvBlock = (nv.ten_nhan_vien || nv.ma_nhan_vien || nv.chuc_danh || nv.don_vi) ? `
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:28px">
    <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:16px 20px">
      <div style="font-size:.75rem;font-weight:800;color:#6366f1;text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px">👤 Thông tin nhân viên</div>
      ${infoField('Họ và tên', nv.ten_nhan_vien)}
      ${infoField('Mã nhân viên', nv.ma_nhan_vien)}
      ${infoField('Chức danh', nv.chuc_danh)}
      ${infoField('Đơn vị', nv.don_vi)}
      ${infoField('Ngày nhận việc', nv.ngay_nhan_viec)}
      ${infoField('Ngày hết hạn thử việc', nv.ngay_het_han)}
    </div>
    <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:16px 20px">
      <div style="font-size:.75rem;font-weight:800;color:#7c3aed;text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px">🏢 Người đánh giá (HOD)</div>
      ${infoField('Họ và tên HOD', nv.ten_hod || '—')}
      ${infoField('Mã HOD', nv.ma_hod || '—')}
      ${infoField('Chức danh HOD', nv.chuc_danh_hod)}
    </div>
  </div>` : ''

  // ── helpers ──────────────────────────────────────────────────────────────
  const chip = (ok, yesLabel = 'Đạt', noLabel = 'Chưa đạt') =>
    ok
      ? `<span style="display:inline-flex;align-items:center;gap:5px;font-size:.78rem;font-weight:800;padding:3px 11px;border-radius:99px;background:#d1fae5;color:#065f46;border:1px solid #a7f3d0">✓ ${yesLabel}</span>`
      : `<span style="display:inline-flex;align-items:center;gap:5px;font-size:.78rem;font-weight:800;padding:3px 11px;border-radius:99px;background:#fef3c7;color:#92400e;border:1px solid #fde68a">⚠ ${noLabel}</span>`

  const sectionHeader = (num, icon, title) => `
    <div style="display:flex;align-items:center;gap:12px;margin:0 0 16px">
      <div style="width:32px;height:32px;border-radius:9px;background:linear-gradient(135deg,#6366f1,#8b5cf6);display:flex;align-items:center;justify-content:center;color:#fff;font-size:.9rem;font-weight:800;flex-shrink:0">${num}</div>
      <div style="font-size:1.05rem;font-weight:800;color:#111827">${icon} ${title}</div>
    </div>`

  const card = (body, extra = '') =>
    `<div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;padding:14px 18px;font-size:.94rem;line-height:1.8;color:#374151${extra}">${body}</div>`

  // ── Phần I: Câu hỏi / Thông tin chung ───────────────────────────────────
  const phanI_ok = r.phan_I_ok !== false
  const phanI_nx = r.phan_I_nhan_xet || '(Chưa có nhận xét)'
  const secI = `
    <div style="margin-bottom:32px">
      ${sectionHeader('I', '📋', 'Phần I – Thông tin & Câu hỏi phỏng vấn')}
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
        ${chip(phanI_ok, 'Đầy đủ', 'Còn thiếu')}
        <span style="font-size:.88rem;color:#6b7280">${phanI_ok ? 'Đã trả lời đầy đủ các câu hỏi' : 'Cần bổ sung thêm'}</span>
      </div>
      ${card(phanI_nx)}
    </div>`

  // ── Phần II: Nhiệm vụ đã thực hiện / Thông tin đã sửa ───────────────────
  const phanII_summary = r.phan_II_tom_tat || '(Không có thay đổi đáng chú ý)'
  const w2_issues = (r.van_de || []).filter(v => v.nhom_tieu_chi === 'W2' || v.nhom_tieu_chi === 'E3')
  const phanII_ok = w2_issues.length === 0
  const secII = `
    <div style="margin-bottom:32px">
      ${sectionHeader('II', '📝', 'Phần II – Nhiệm vụ đã thực hiện')}
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
        ${chip(phanII_ok, 'Hợp lệ', 'Có vấn đề')}
      </div>
      ${card(phanII_summary)}
      ${w2_issues.length ? `
      <div style="margin-top:10px;display:flex;flex-direction:column;gap:8px">
        ${w2_issues.map(v => `
          <div style="border-radius:8px;border:1px solid #fde68a;background:#fffbeb;padding:10px 14px">
            <div style="font-size:.82rem;font-weight:700;color:#92400e;margin-bottom:4px">${v.nhom_tieu_chi} · ${v.muc || ''}</div>
            <div style="font-size:.93rem;color:#b91c1c;line-height:1.65">${v.van_de}</div>
            <div style="font-size:.9rem;color:#374151;margin-top:5px"><strong style="color:#5b21b6">→ Cần làm:</strong> ${v.yeu_cau}</div>
          </div>`).join('')}
      </div>` : ''}
    </div>`

  // ── Phần III: Hội nhập ───────────────────────────────────────────────────
  const hoi_nhap_ok = r.hoi_nhap_ok !== false
  const hoi_nhap_nx = r.hoi_nhap_nhan_xet || '(Chưa có nhận xét)'
  const secIII = `
    <div style="margin-bottom:32px">
      ${sectionHeader('III', '🤝', 'Phần III – Hội nhập')}
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
        ${chip(hoi_nhap_ok, 'Hoàn thành', 'Chưa hoàn thành')}
      </div>
      ${card(hoi_nhap_nx)}
    </div>`

  // ── Phần IV: Người giao việc ─────────────────────────────────────────────
  const ngv = r.nguoi_giao_viec || {}
  const ngv_ok = ngv.giao_dung !== false
  const ngv_nx = ngv.nhan_xet || '(Chưa có nhận xét)'
  const secIV = `
    <div style="margin-bottom:32px">
      ${sectionHeader('IV', '👤', 'Người giao việc')}
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
        ${chip(ngv_ok, 'Giao đúng việc', 'Cần xem lại')}
      </div>
      ${card(ngv_nx)}
    </div>`

  // ── Phần V: Tổng hợp vấn đề & Điểm mạnh ────────────────────────────────
  const allIssues = (r.van_de || [])
  const issuesHtml = allIssues.map((v, i) => {
    const isWord = v.loai === 'WORD'
    const isExcel = v.loai === 'EXCEL'
    const tagBg = isWord ? '#ede9fe' : isExcel ? '#d1fae5' : '#fef3c7'
    const tagColor = isWord ? '#6d28d9' : isExcel ? '#065f46' : '#92400e'
    const fileBg = isWord ? '#eff6ff' : isExcel ? '#ecfdf5' : '#fffbeb'
    const fileColor = isWord ? '#1d4ed8' : isExcel ? '#065f46' : '#92400e'
    const fileBorder = isWord ? '#bfdbfe' : isExcel ? '#a7f3d0' : '#fde68a'
    const fileLabel = isWord ? '📝 Sửa ở file Word' : isExcel ? '📊 Sửa ở file Excel' : '⚠️ Cả hai file'
    return `
      <div style="border-radius:9px;overflow:hidden;border:1px solid #e5e7eb;margin-bottom:10px">
        <div style="background:#f9fafb;padding:8px 14px;display:flex;align-items:center;gap:8px;border-bottom:1px solid #f3f4f6;flex-wrap:wrap">
          <span style="font-size:.75rem;font-weight:800;padding:2px 9px;border-radius:5px;background:${tagBg};color:${tagColor};letter-spacing:.04em">${v.loai}</span>
          <span style="font-size:.74rem;font-weight:700;padding:2px 8px;border-radius:4px;background:#e0e7ff;color:#3730a3">${v.nhom_tieu_chi || ''}</span>
          <span style="font-size:.9rem;color:#6b7280;font-weight:500">${v.muc || ''}</span>
        </div>
        <div style="padding:10px 14px 5px;color:#b91c1c;font-size:.93rem;line-height:1.7">${v.van_de}</div>
        <div style="padding:4px 14px 9px;font-size:.9rem;color:#374151;line-height:1.65">
          <strong style="color:#5b21b6">→ Cần làm:</strong> ${v.yeu_cau}
        </div>
        <div style="padding:5px 14px 10px">
          <span style="font-size:.74rem;font-weight:700;padding:3px 10px;border-radius:99px;background:${fileBg};color:${fileColor};border:1px solid ${fileBorder}">${fileLabel}</span>
        </div>
      </div>`
  }).join('')

  const goodHtml = (r.uu_diem || []).map(g =>
    `<li style="margin-bottom:6px;padding-left:4px;display:flex;gap:10px"><span style="color:#059669;font-weight:700;flex-shrink:0">✓</span><span>${g}</span></li>`
  ).join('')

  const secV = `
    <div style="margin-bottom:32px">
      ${sectionHeader('V', '📊', `Tổng hợp – ${isPass ? 'Đạt yêu cầu' : `${allIssues.length} vấn đề cần bổ sung`}`)}
      ${allIssues.length ? `
      <div style="margin-bottom:18px">
        <div style="font-size:.88rem;font-weight:700;color:#374151;margin-bottom:10px;text-transform:uppercase;letter-spacing:.05em">⚠️ Vấn đề cần sửa (${allIssues.length})</div>
        ${issuesHtml}
      </div>` : `<div style="padding:12px 16px;background:#ecfdf5;border:1px solid #a7f3d0;border-radius:8px;color:#065f46;font-size:.94rem;margin-bottom:18px">✓ Không có vấn đề cần sửa</div>`}
      ${(r.uu_diem || []).length ? `
      <div>
        <div style="font-size:.88rem;font-weight:700;color:#374151;margin-bottom:10px;text-transform:uppercase;letter-spacing:.05em">✅ Điểm tốt (${r.uu_diem.length})</div>
        <ul style="list-style:none;background:#ecfdf5;border:1px solid #a7f3d0;border-radius:8px;padding:14px 18px;color:#065f46;line-height:1.85;margin:0">${goodHtml}</ul>
      </div>` : ''}
      ${r.luu_y_chung ? `<div style="margin-top:14px;padding:12px 16px;background:#fffbeb;border:1px solid #fde68a;border-radius:8px;font-size:.9rem;color:#92400e;line-height:1.7">📌 ${r.luu_y_chung}</div>` : ''}
    </div>`

  // ── KPI table ────────────────────────────────────────────────────────────
  const kpiRows = r.xlsx_kpi || []
  const kpiHtml = kpiRows.length ? `
    <div style="margin-bottom:32px">
      <div style="font-size:.85rem;font-weight:700;color:#374151;margin-bottom:10px;text-transform:uppercase;letter-spacing:.05em">📊 Chi tiết bảng KPI Excel</div>
      <table style="width:100%;border-collapse:collapse;font-size:.82rem">
        <thead>
          <tr style="background:#f3f4f6">
            <th style="padding:7px 10px;text-align:left;border:1px solid #e5e7eb;font-weight:700;color:#374151">STT</th>
            <th style="padding:7px 10px;text-align:left;border:1px solid #e5e7eb;font-weight:700;color:#374151">Công việc</th>
            <th style="padding:7px 10px;text-align:center;border:1px solid #e5e7eb;font-weight:700;color:#374151">Tỷ lệ</th>
            <th style="padding:7px 10px;text-align:center;border:1px solid #e5e7eb;font-weight:700;color:#374151">Trạng thái</th>
            <th style="padding:7px 10px;text-align:left;border:1px solid #e5e7eb;font-weight:700;color:#374151">Minh chứng</th>
          </tr>
        </thead>
        <tbody>
          ${kpiRows.map(r2 => {
            const bg = r2.status === 'THIẾU' ? '#fef2f2' : r2.status === 'CẢNH BÁO' ? '#fffbeb' : '#f0fdf4'
            const sc = r2.status === 'THIẾU' ? '#dc2626' : r2.status === 'CẢNH BÁO' ? '#b45309' : '#059669'
            const pct = r2.ty_le_thuc_hien != null ? `${(r2.ty_le_thuc_hien*100).toFixed(0)}%` : '—'
            const link = r2.link_minh_chung?.startsWith('http')
              ? `<a href="${r2.link_minh_chung}" style="color:#2563eb">🔗 Xem</a>`
              : r2.link_minh_chung
                ? `<span style="color:#059669">✅ ${r2.link_minh_chung.slice(0,40)}</span>`
                : '<span style="color:#dc2626">❌ Chưa có</span>'
            return `<tr style="background:${bg}">
              <td style="padding:6px 10px;border:1px solid #e5e7eb;color:#6b7280;font-weight:600">${r2.stt}</td>
              <td style="padding:6px 10px;border:1px solid #e5e7eb">${(r2.cong_viec || '').slice(0,50)}</td>
              <td style="padding:6px 10px;border:1px solid #e5e7eb;text-align:center;font-weight:700">${pct}</td>
              <td style="padding:6px 10px;border:1px solid #e5e7eb;text-align:center">
                <span style="font-size:.73rem;font-weight:800;padding:2px 8px;border-radius:99px;background:#fff;color:${sc};border:1px solid ${sc}">${r2.status}</span>
              </td>
              <td style="padding:6px 10px;border:1px solid #e5e7eb">${link}</td>
            </tr>`
          }).join('')}
        </tbody>
      </table>
    </div>` : ''

  // ── Bảng KPI Tuần (1.1→1.8, kiểm tra trung bình 1.9) ───────────────────
  const wkpi = r.weekly_kpi || {}
  const wRows = wkpi.rows || {}
  const wIssues = wkpi.issues || []
  const computedAvg = wkpi.computed_avg
  const statedAvg = wkpi.stated_avg
  const avgMatch = computedAvg != null && statedAvg != null && Math.abs(computedAvg - statedAvg) <= 0.5
  const avgError = computedAvg != null && statedAvg != null && Math.abs(computedAvg - statedAvg) > 0.5

  const weeklyHtml = Object.keys(wRows).length ? `
    <div style="margin-bottom:32px">
      <div style="font-size:.85rem;font-weight:700;color:#374151;margin-bottom:10px;text-transform:uppercase;letter-spacing:.05em">📅 Kết quả KPI theo tuần (1.1 → 1.9)</div>
      <table style="width:100%;border-collapse:collapse;font-size:.85rem">
        <thead>
          <tr style="background:#f3f4f6">
            <th style="padding:7px 12px;text-align:left;border:1px solid #e5e7eb;font-weight:700">Tuần</th>
            <th style="padding:7px 12px;text-align:center;border:1px solid #e5e7eb;font-weight:700">Kết quả KPI</th>
          </tr>
        </thead>
        <tbody>
          ${Object.entries(wRows).sort(([a],[b])=>parseFloat(a)-parseFloat(b)).map(([stt, pct]) => {
            const label = {1.1:'Tuần 1',1.2:'Tuần 2',1.3:'Tuần 3',1.4:'Tuần 4',1.5:'Tuần 5',1.6:'Tuần 6',1.7:'Tuần 7',1.8:'Tuần 8'}[parseFloat(stt)] || `Tuần ${stt}`
            return `<tr><td style="padding:6px 12px;border:1px solid #e5e7eb;color:#374151">${label}</td>
              <td style="padding:6px 12px;border:1px solid #e5e7eb;text-align:center;font-weight:700;color:#059669">${pct.toFixed(2)}%</td></tr>`
          }).join('')}
          <tr style="background:${avgError ? '#fef2f2' : avgMatch ? '#ecfdf5' : '#f9fafb'};border-top:2px solid ${avgError ? '#fca5a5' : avgMatch ? '#6ee7b7' : '#e5e7eb'}">
            <td style="padding:8px 12px;border:1px solid #e5e7eb;font-weight:800;color:#111827">
              1.9 &nbsp;Điểm trung bình (Bình quân 8 tuần)
              ${avgError ? '<span style="font-size:.72rem;background:#fef2f2;color:#dc2626;border:1px solid #fca5a5;padding:2px 7px;border-radius:5px;margin-left:6px;font-weight:700">⚠ SAI CÔNG THỨC</span>' : avgMatch ? '<span style="font-size:.72rem;background:#ecfdf5;color:#059669;border:1px solid #6ee7b7;padding:2px 7px;border-radius:5px;margin-left:6px;font-weight:700">✓ Chính xác</span>' : ''}
            </td>
            <td style="padding:8px 12px;border:1px solid #e5e7eb;text-align:center">
              ${statedAvg != null ? `<span style="font-weight:800;color:${avgError ? '#dc2626' : '#059669'}">${statedAvg.toFixed(2)}%</span>` : '<span style="color:#9ca3af">—</span>'}
              ${computedAvg != null ? `<span style="font-size:.8rem;color:#6b7280;margin-left:6px">(Tính đúng: ${computedAvg.toFixed(2)}%)</span>` : ''}
            </td>
          </tr>
        </tbody>
      </table>
      ${wIssues.length ? `
      <div style="margin-top:10px;padding:10px 14px;background:#fef2f2;border:1px solid #fca5a5;border-radius:8px;font-size:.88rem;color:#991b1b;line-height:1.7">
        ${wIssues.map(e => `⚠ ${e}`).join('<br>')}
      </div>` : `
      <div style="margin-top:8px;padding:8px 14px;background:#ecfdf5;border:1px solid #6ee7b7;border-radius:8px;font-size:.88rem;color:#065f46">
        ✓ Trung bình ${computedAvg != null ? computedAvg.toFixed(2)+'%' : ''} — khớp với ô 1.9
      </div>`}
    </div>` : ''

  const html = `<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<title>Báo cáo Đánh giá Thử việc – CT Group</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0 }
  body { font-family: 'Segoe UI', Arial, sans-serif; font-size: 14px; color: #111827; background: #fff }
  .page { max-width: 860px; margin: 0 auto; padding: 40px 44px }
  @media print {
    body { background: #fff }
    .page { padding: 0; max-width: 100% }
    @page { margin: 1.6cm 1.8cm; size: A4 }
  }
</style>
</head>
<body>
<div class="page">

  <!-- ── HEADER ── -->
  <div style="display:flex;align-items:center;justify-content:space-between;padding-bottom:20px;margin-bottom:28px;border-bottom:3px solid ${accentColor}">
    <div>
      <div style="font-size:1.5rem;font-weight:800;color:#5b5bd6;letter-spacing:-.02em">AI Đánh Giá Thử Việc</div>
      <div style="font-size:.88rem;color:#6b7280;margin-top:3px">CT Group · Báo cáo tự động · ${now}</div>
    </div>
    <div style="text-align:right">
      <div style="display:inline-flex;align-items:center;gap:10px;padding:10px 18px;border-radius:10px;background:${accentLight};border:2px solid ${accentBorder}">
        <span style="width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1.1rem;font-weight:900;background:${accentBorder};color:${accentColor}">${isPass ? '✓' : '!'}</span>
        <span style="font-size:1.1rem;font-weight:800;color:${accentColor}">${r.status}</span>
      </div>
    </div>
  </div>

  <!-- ── THÔNG TIN NHÂN VIÊN & HOD ── -->
  ${nvBlock}

  <!-- ── TỔNG QUAN ── -->
  <div style="background:linear-gradient(135deg,#f8fafc,#f1f5f9);border:1px solid #e2e8f0;border-radius:12px;padding:16px 20px;margin-bottom:32px">
    <div style="font-size:.8rem;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:.07em;margin-bottom:8px">Nhận xét tổng quan</div>
    <div style="font-size:1rem;line-height:1.8;color:#334155">${r.tong_quan || ''}</div>
  </div>

  <!-- ── 5 PHẦN ── -->
  ${secI}
  ${secII}
  ${secIII}
  ${secIV}
  ${secV}
  ${weeklyHtml}
  ${kpiHtml}

  <!-- ── FOOTER ── -->
  <div style="margin-top:36px;padding-top:14px;border-top:1px solid #e5e7eb;display:flex;justify-content:space-between;align-items:center;font-size:.76rem;color:#9ca3af">
    <span>Báo cáo AI · CT Group · ${now}</span>
    <span>Hệ thống Đánh Giá Thử Việc v2.0</span>
  </div>

</div>
</body>
</html>`

  const w = window.open('', '_blank', 'width=960,height=780')
  w.document.write(html)
  w.document.close()
  w.focus()
  setTimeout(() => w.print(), 500)
}


</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0 }
html, body, #app { height: 100%; overflow: hidden }
body { font-family: 'Inter', sans-serif; font-size: 16px; background: #f5f5f5; color: #111827 }

/* ══ ROOT VARS ══ */
:root {
  --sidebar-w: 360px;
  --primary: #5b5bd6;
  --primary-dk: #4b4bc4;
  --primary-bg: #ededfb;
  --surface: #ffffff;
  --border: #e5e7eb;
  --border-light: #f3f4f6;
  --text: #111827;
  --text-2: #374151;
  --text-3: #6b7280;
  --text-4: #9ca3af;
  --green: #059669;
  --green-bg: #ecfdf5;
  --green-border: #a7f3d0;
  --amber: #b45309;
  --amber-bg: #fffbeb;
  --amber-border: #fde68a;
  --red: #dc2626;
  --red-bg: #fef2f2;
  --red-border: #fecaca;
  --blue: #2563eb;
  --blue-bg: #eff6ff;
  --blue-border: #bfdbfe;
  --shadow: 0 1px 3px rgba(0,0,0,.08), 0 1px 2px rgba(0,0,0,.05);
  --shadow-md: 0 4px 6px rgba(0,0,0,.07), 0 2px 4px rgba(0,0,0,.05);
}

/* ══ APP ══ */
.app { display: flex; height: 100vh; overflow: hidden; background: #f9fafb }

/* ══ SIDEBAR ══ */
.sidebar {
  width: var(--sidebar-w); flex-shrink: 0;
  background: var(--surface); border-right: 1px solid var(--border);
  display: flex; flex-direction: column;
  overflow: hidden;
}
.sb-top { padding: 26px 22px 20px; border-bottom: 1px solid var(--border-light) }
.sb-logo { display: flex; align-items: center; gap: 14px }
.sb-logo-mark {
  width: 48px; height: 48px; border-radius: 13px; flex-shrink: 0;
  background: linear-gradient(135deg, var(--primary), #8b5cf6);
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 3px 10px rgba(91,91,214,.35);
}
.sb-name { font-size: 1.15rem; font-weight: 800; color: var(--text); line-height: 1.2 }
.sb-org { font-size: .88rem; color: var(--text-4); margin-top: 3px }

.sb-nav { flex: 1; overflow-y: auto; padding: 18px; display: flex; flex-direction: column; gap: 22px }
.sb-nav::-webkit-scrollbar { width: 4px }
.sb-nav::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px }

.sb-section { display: flex; flex-direction: column; gap: 10px }
.sb-section-title { font-size: .85rem; font-weight: 700; color: var(--text-4); letter-spacing: .07em; text-transform: uppercase; padding: 0 2px; margin-bottom: 2px }

/* Upload cards */
.sb-upload-card {
  display: flex; align-items: center; gap: 14px;
  padding: 14px 16px; border-radius: 14px;
  border: 1.5px dashed var(--border);
  cursor: pointer; transition: all .15s; background: var(--border-light);
}
.sb-upload-card:hover { border-color: var(--primary); background: var(--primary-bg) }
.upc__filled { border-style: solid; border-color: var(--green-border); background: var(--green-bg) }
.upc__err { border-color: var(--red-border); background: var(--red-bg) }
.upc-icon { font-size: 1.7rem; flex-shrink: 0 }
.upc-info { flex: 1; min-width: 0 }
.upc-label { font-size: .82rem; font-weight: 700; color: var(--text-3); text-transform: uppercase; letter-spacing: .05em }
.upc-val { font-size: .9rem; margin-top: 3px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap }
.upc-ok { color: var(--green); font-weight: 600 }
.upc-empty { color: var(--text-4) }
.upc-rm {
  background: none; border: none; cursor: pointer; padding: 4px;
  color: var(--text-4); border-radius: 5px; display: flex; flex-shrink: 0;
  transition: all .15s;
}
.upc-rm:hover { background: var(--red-bg); color: var(--red) }

.sb-err-msg { font-size: .88rem; color: var(--red); padding: 0 2px }

.sb-analyze-btn {
  width: 100%; padding: 14px 20px; border: none; border-radius: 12px;
  background: var(--primary); color: #fff;
  font-size: 1rem; font-weight: 700; cursor: pointer; font-family: inherit;
  display: flex; align-items: center; justify-content: center; gap: 10px;
  transition: all .15s; box-shadow: 0 3px 10px rgba(91,91,214,.35);
}
.sb-analyze-btn:hover:not(:disabled) { background: var(--primary-dk); box-shadow: 0 4px 14px rgba(91,91,214,.4) }
.sb-analyze-btn:disabled { opacity: .45; cursor: not-allowed }

.sb-result-badge {
  display: flex; align-items: center; gap: 12px;
  padding: 14px 16px; border-radius: 13px; border: 1.5px solid;
}
.rb-pass { background: var(--green-bg); border-color: var(--green-border) }
.rb-fail { background: var(--amber-bg); border-color: var(--amber-border) }
.rb-icon {
  width: 36px; height: 36px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.1rem; font-weight: 800;
}
.rb-pass .rb-icon { background: #a7f3d0; color: var(--green) }
.rb-fail .rb-icon { background: #fde68a; color: var(--amber) }
.rb-text { font-size: 1rem; font-weight: 700 }
.rb-pass .rb-text { color: var(--green) }
.rb-fail .rb-text { color: var(--amber) }

.sb-counts { display: flex; gap: 10px }
.sc-item { flex: 1; text-align: center; padding: 14px 6px; background: var(--border-light); border-radius: 12px; border: 1px solid var(--border) }
.sc-val { font-size: 1.9rem; font-weight: 800; line-height: 1 }
.sc-warn { color: var(--amber) }
.sc-ok { color: var(--green) }
.sc-bad { color: var(--red) }
.sc-lbl { font-size: .8rem; color: var(--text-4); margin-top: 5px; font-weight: 500 }

.sb-footer {
  padding: 16px 18px; border-top: 1px solid var(--border-light);
}
.sb-session { display: flex; align-items: center; gap: 8px; font-size: .92rem }
.sf-on { color: var(--green) }
.sf-off { color: var(--text-4) }
.sf-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; flex-shrink: 0 }
.sf-on .sf-dot { animation: sfpulse 1.5s infinite }
@keyframes sfpulse { 0%,100%{opacity:1} 50%{opacity:.4} }

/* ══ CHAT AREA ══ */
.chat-area {
  flex: 1; min-width: 0; display: flex; flex-direction: column;
  background: #f9fafb; overflow: hidden;
}

/* Messages */
.msg-list {
  flex: 1; overflow-y: auto; padding: 28px 0;
  display: flex; flex-direction: column;
  scroll-behavior: smooth;
}
.msg-list::-webkit-scrollbar { width: 6px }
.msg-list::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px }

/* Welcome screen */
.welcome-screen {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; min-height: 65vh;
  padding: 40px 24px; text-align: center;
}
.ws-icon { width: 72px; height: 72px; margin-bottom: 24px; border-radius: 20px; box-shadow: var(--shadow-md) }
.ws-title { font-size: 1.9rem; font-weight: 800; color: var(--text); margin-bottom: 12px; letter-spacing: -.02em }
.ws-desc { font-size: 1rem; color: var(--text-3); line-height: 1.8; margin-bottom: 32px }
.ws-desc b { color: var(--primary); font-weight: 600 }
.ws-features { display: flex; flex-direction: column; gap: 12px; width: 100%; max-width: 480px }
.wsf { display: flex; align-items: center; gap: 14px; padding: 14px 18px; background: var(--surface); border: 1px solid var(--border); border-radius: 14px; text-align: left; box-shadow: var(--shadow) }
.wsf-icon { font-size: 1.4rem; flex-shrink: 0 }
.wsf-text { font-size: .94rem; color: var(--text-2); line-height: 1.6 }

/* Bubble rows */
.bubble-row {
  padding: 8px max(24px, calc(50% - 480px));
  display: flex; gap: 12px; align-items: flex-start;
}
.bubble-row--user { justify-content: flex-end }
.bubble-row--ai { justify-content: flex-start }

/* User bubble */
.bubble--user {
  background: var(--primary); color: #fff;
  padding: 14px 20px; border-radius: 22px 4px 22px 22px;
  max-width: 75%; box-shadow: var(--shadow);
}
.bubble-files { display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px }
.bfile {
  display: flex; align-items: center; gap: 10px;
  background: rgba(255,255,255,.15); border-radius: 10px;
  padding: 8px 14px; border: 1px solid rgba(255,255,255,.2);
}
.bfile-icon { font-size: 1.4rem; flex-shrink: 0 }
.bfile-name { font-size: 1rem; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap }
.bubble-text { font-size: 1.05rem; line-height: 1.7; word-break: break-word }

/* AI area */
.ai-av {
  width: 40px; height: 40px; border-radius: 12px; flex-shrink: 0; margin-top: 2px;
  background: linear-gradient(135deg, var(--primary), #8b5cf6);
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 2px 8px rgba(91,91,214,.3);
}
.ai-content { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 12px }

.bubble--ai {
  background: var(--surface); border: 1px solid var(--border);
  padding: 16px 22px; border-radius: 4px 22px 22px 22px;
  font-size: 1.05rem; line-height: 1.8; color: var(--text-2);
  box-shadow: var(--shadow); max-width: 100%;
  word-break: break-word;
}

/* Result card */
.result-card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 16px; overflow: hidden; box-shadow: var(--shadow);
}

.rc-top {
  padding: 18px 20px; border-bottom: 1px solid var(--border);
}
.rct-pass { background: linear-gradient(135deg, var(--green-bg), #f0fdf4) }
.rct-fail { background: linear-gradient(135deg, var(--amber-bg), #fef9c3) }
.rct-badge {
  display: inline-block; font-size: .92rem; font-weight: 800;
  padding: 5px 14px; border-radius: 99px; margin-bottom: 10px; letter-spacing: .04em;
}
.rct-pass .rct-badge { background: #a7f3d0; color: var(--green) }
.rct-fail .rct-badge { background: #fde68a; color: var(--amber) }
.rct-desc { font-size: 1.05rem; color: var(--text-2); line-height: 1.8 }

/* Accordion blocks */
.rc-block { border-bottom: 1px solid var(--border-light) }
.rc-block:last-child { border-bottom: none }

.rcb-toggle {
  width: 100%; display: flex; align-items: center; gap: 12px;
  padding: 14px 20px; border: none; background: transparent;
  cursor: pointer; text-align: left; font-family: inherit; transition: background .15s;
}
.rcb-toggle:hover { background: var(--border-light) }

.rcb-t-icon {
  width: 30px; height: 30px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.rcb-warn { background: #fef3c7; color: #d97706 }
.rcb-blue { background: var(--blue-bg); color: var(--blue) }
.rcb-green { background: var(--green-bg); color: var(--green) }

.rcb-t-label { flex: 1; font-size: 1rem; font-weight: 600; color: var(--text) }
.rcb-kpi-pills { display: flex; gap: 6px }
.kp { font-size: .76rem; font-weight: 700; padding: 3px 9px; border-radius: 99px }
.kp.ok { background: var(--green-bg); color: var(--green); border: 1px solid var(--green-border) }
.kp.miss { background: var(--red-bg); color: var(--red); border: 1px solid var(--red-border) }
.rcb-t-arrow { color: var(--text-4); font-size: 1.1rem; transition: transform .2s; display: flex; align-items: center }
.rcb-t-arrow.open { transform: rotate(90deg) }

.rcb-body { padding: 6px 18px 16px; display: flex; flex-direction: column; gap: 8px }

/* Issue items */
.issue-item { border-radius: 9px; overflow: hidden; border: 1px solid }
.ii-word { background: #faf8ff; border-color: #e9d8fd }
.ii-excel { background: #f0fdf9; border-color: #99f6e4 }
.ii-chung { background: #fffdf4; border-color: #fde68a }

.ii-meta { display: flex; align-items: center; gap: 10px; padding: 9px 14px; background: rgba(0,0,0,.02); border-bottom: 1px solid rgba(0,0,0,.04) }
.ii-tag { font-size: .78rem; font-weight: 800; padding: 3px 10px; border-radius: 5px; letter-spacing: .06em }
.ii-word .ii-tag { background: #ede9fe; color: #6d28d9 }
.ii-excel .ii-tag { background: #d1fae5; color: #065f46 }
.ii-chung .ii-tag { background: #fef3c7; color: #92400e }
.ii-section { font-size: .95rem; color: var(--text-3); font-weight: 500 }
.ii-problem { padding: 10px 14px 5px; font-size: 1rem; color: #b91c1c; line-height: 1.7 }
.ii-fix { padding: 5px 14px 12px; font-size: 1rem; color: var(--text-2); line-height: 1.7; display: flex; gap: 7px }
.ii-fix strong { color: #5b21b6 }
.ii-arrow { color: var(--primary); flex-shrink: 0; margin-top: 1px }

/* KPI list */
.kpi-list { display: flex; flex-direction: column; gap: 5px }
.kpi-item { border-radius: 8px; padding: 8px 10px; border: 1px solid }
.ki-ok { background: var(--green-bg); border-color: var(--green-border) }
.ki-miss { background: var(--red-bg); border-color: var(--red-border) }
.ki-row1 { display: flex; align-items: center; gap: 7px; margin-bottom: 3px }
.ki-stt { font-size: .76rem; font-weight: 800; color: var(--text-4); width: 20px; flex-shrink: 0 }
.ki-name { flex: 1; font-size: .9rem; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap }
.ki-chip { font-size: .72rem; font-weight: 800; padding: 2px 8px; border-radius: 99px; flex-shrink: 0 }
.kc-ok { background: #a7f3d0; color: var(--green) }
.kc-miss { background: #fecaca; color: var(--red) }
.kc-warn { background: #fef3c7; color: #b45309 }
.ki-warn { background: #fffbeb; border-color: #fde68a }
.kp.warn { background: #fef3c7; color: #92400e; border: 1px solid #fde68a }
.ki-row2 { display: flex; align-items: center; gap: 14px; font-size: .84rem; color: var(--text-3) }
.ki-row2 b { color: var(--text) }
.ki-lnk { color: var(--primary); text-decoration: none; font-weight: 500 }
.ki-lnk:hover { text-decoration: underline }
.ki-no-lnk { color: var(--red); font-weight: 500 }
.ki-issues { margin-top: 4px; display: flex; flex-direction: column; gap: 3px }
.ki-issue-chip {
  display: block; font-size: .71rem; line-height: 1.5;
  padding: 2px 8px; border-radius: 5px;
  background: #fffbeb; color: #92400e; border: 1px solid #fde68a;
}
.ki-miss .ki-issue-chip { background: #fef2f2; color: #991b1b; border-color: #fecaca }

.ii-problem { display: flex; align-items: flex-start; gap: 7px; padding: 10px 14px 4px; font-size: .95rem; color: #b91c1c; line-height: 1.65 }
.ii-prob-icon { flex-shrink: 0; margin-top: 3px }
.ii-where { display: flex; align-items: center; gap: 10px; padding: 5px 14px 10px; flex-wrap: wrap }
.ii-file-badge { font-size: .76rem; font-weight: 700; padding: 3px 12px; border-radius: 99px }
.badge-word { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe }
.badge-excel { background: #ecfdf5; color: #065f46; border: 1px solid #a7f3d0 }
.badge-chung { background: #fffbeb; color: #92400e; border: 1px solid #fde68a }
.ii-criteria-badge {
  font-size: .62rem; font-weight: 800; padding: 2px 7px; border-radius: 4px;
  background: #e0e7ff; color: #3730a3; border: 1px solid #c7d2fe;
  letter-spacing: .04em; flex-shrink: 0;
}
.ii-reup-hint { font-size: .8rem; color: #9ca3af }

.reup-cta {
  margin: 2px 14px 10px; padding: 11px 14px;
  background: linear-gradient(135deg, #f0f9ff, #f0fdf4);
  border: 1.5px solid #93c5fd; border-radius: 10px;
}
.reup-cta-left { display: flex; align-items: flex-start; gap: 11px }
.reup-cta-icon {
  width: 34px; height: 34px; border-radius: 9px; flex-shrink: 0;
  background: #5b5bd6; color: #fff;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 2px 6px rgba(91,91,214,.3);
}
.reup-cta-title { font-size: .92rem; font-weight: 700; color: #5b5bd6; margin-bottom: 4px }
.reup-cta-desc { font-size: .86rem; color: #6b7280; line-height: 1.65 }


/* Good list */
.good-ul { list-style: none; display: flex; flex-direction: column; gap: 8px }
.good-ul li { display: flex; align-items: flex-start; gap: 12px; font-size: 1rem; color: var(--text-2); line-height: 1.75 }
.good-ul li::before { content: '✓'; color: var(--green); font-weight: 700; flex-shrink: 0; margin-top: 2px }
.note-ln { margin-top: 10px; padding: 12px 16px; background: var(--amber-bg); border: 1px solid var(--amber-border); border-radius: 10px; font-size: .95rem; color: #92400e; line-height: 1.75 }

/* Typing */
.typing-bubble {
  display: flex; align-items: center; gap: 5px;
  padding: 12px 18px; background: var(--surface); border: 1px solid var(--border);
  border-radius: 4px 20px 20px 20px; box-shadow: var(--shadow);
}
.typing-bubble span { width: 7px; height: 7px; border-radius: 50%; background: var(--primary); animation: tdot .9s infinite; opacity: .5 }
.typing-bubble span:nth-child(2) { animation-delay: .15s }
.typing-bubble span:nth-child(3) { animation-delay: .3s }
.typing-txt { font-size: .94rem; color: var(--text-3); margin-left: 10px }
@keyframes tdot { 0%,100%{transform:translateY(0);opacity:.4} 50%{transform:translateY(-4px);opacity:1} }

/* ══ INPUT AREA ══ */
.input-area {
  flex-shrink: 0; padding: 16px 28px 20px;
  background: #f9fafb; border-top: 1px solid var(--border);
}
/* File previews GPT style */
.file-previews {
  display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 8px;
}
.fp-item {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 10px; background: var(--surface);
  border: 1px solid var(--border); border-radius: 10px;
  box-shadow: var(--shadow); max-width: 240px;
}
.fp-thumb {
  width: 36px; height: 36px; border-radius: 7px;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.4rem; flex-shrink: 0;
}
.fp-docx { background: #eff6ff }
.fp-xlsx { background: #f0fdf4 }
.fp-meta { flex: 1; min-width: 0 }
.fp-name { font-size: .78rem; font-weight: 600; color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap }
.fp-type { font-size: .68rem; color: var(--text-4); margin-top: 1px }
.fp-rm {
  background: none; border: none; cursor: pointer;
  color: var(--text-4); padding: 4px; border-radius: 5px;
  display: flex; align-items: center; transition: all .15s; flex-shrink: 0;
}
.fp-rm:hover { background: var(--red-bg); color: var(--red) }

/* Input box */
.input-box {
  display: flex; align-items: flex-end; gap: 10px;
  background: var(--surface); border: 1.5px solid var(--border);
  border-radius: 16px; padding: 10px 12px;
  box-shadow: var(--shadow); transition: border-color .15s, box-shadow .15s;
  position: relative;
}
.ib-focus { border-color: var(--primary); box-shadow: 0 0 0 3px rgba(91,91,214,.12) }

.ib-left { display: flex; align-items: flex-end; position: relative }
.attach-btn {
  width: 34px; height: 34px; border-radius: 8px; border: none;
  background: transparent; cursor: pointer; color: var(--text-3);
  display: flex; align-items: center; justify-content: center;
  transition: all .15s;
}
.attach-btn:hover { background: var(--border-light); color: var(--text) }
.attach-btn--off { cursor: default }

/* Attach dropdown */
.attach-dropdown {
  position: absolute; bottom: calc(100% + 8px); left: 0;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 10px; box-shadow: 0 8px 24px rgba(0,0,0,.12);
  overflow: hidden; z-index: 50; min-width: 180px;
}
.attach-opt {
  display: flex; align-items: center; gap: 9px;
  padding: 10px 14px; cursor: pointer; font-size: .82rem; color: var(--text-2);
  transition: background .12s; font-family: inherit; font-weight: 500;
}
.attach-opt:hover { background: var(--border-light) }

.ib-textarea {
  flex: 1; border: none; outline: none; background: transparent;
  font-family: inherit; font-size: 1rem; color: var(--text);
  resize: none; line-height: 1.6; padding: 7px 6px;
  min-height: 26px; max-height: 180px;
}
.ib-textarea::placeholder { color: var(--text-4) }
.ib-textarea:disabled { cursor: not-allowed; color: var(--text-4) }

.send-btn {
  width: 34px; height: 34px; flex-shrink: 0; border-radius: 8px;
  background: var(--primary); border: none; color: #fff;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; transition: all .15s;
  box-shadow: 0 2px 6px rgba(91,91,214,.35);
}
.send-btn:hover:not(:disabled) { background: var(--primary-dk); transform: scale(1.05) }
.send-btn:disabled { opacity: .3; cursor: not-allowed; transform: none }

.ib-hint { text-align: center; font-size: .76rem; color: var(--text-4); margin-top: 8px }

/* Spinners */
.btn-spin {
  width: 14px; height: 14px; border: 2px solid rgba(255,255,255,.35);
  border-top-color: #fff; border-radius: 50%; animation: sp .65s linear infinite;
}
.btn-spin--sm { width: 12px; height: 12px }
@keyframes sp { to { transform: rotate(360deg) } }

/* Accordion */
.acc-enter-active, .acc-leave-active { transition: all .22s ease; overflow: hidden }
.acc-enter-from, .acc-leave-to { opacity: 0; max-height: 0 }
.acc-enter-to, .acc-leave-from { opacity: 1; max-height: 3000px }

/* Scrollbar */
* { scrollbar-width: thin; scrollbar-color: var(--border) transparent }

/* PDF Button */
.sb-pdf-btn {
  width: 100%; padding: 10px 16px; border: 1.5px solid var(--primary);
  border-radius: 10px; background: transparent; color: var(--primary);
  font-size: .88rem; font-weight: 700; cursor: pointer; font-family: inherit;
  display: flex; align-items: center; justify-content: center; gap: 8px;
  transition: all .15s; margin-top: 2px;
}
.sb-pdf-btn:hover { background: var(--primary); color: #fff }
</style>
