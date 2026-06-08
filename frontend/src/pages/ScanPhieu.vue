<template>
  <div class="app-layout">
    <!-- SIDEBAR -->
    <aside class="sidebar">
      <div class="sb-top">
        <button class="sb-back" title="Về chế độ Word/Excel" @click="$emit('back')">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M19 12H5m7-7l-7 7 7 7"/></svg>
        </button>
        <div class="sb-logo">
          <div class="sb-logo-mark">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5"><path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
          </div>
          <div>
            <div class="sb-name">Đánh Giá từ Scan</div>
            <div class="sb-org">CT Group · 2AS</div>
          </div>
        </div>
      </div>

      <div class="sb-body">
        <!-- BƯỚC 1: Upload -->
        <div v-if="step === 1" class="sb-section">
          <div class="sb-section-title">📂 Upload phiếu đánh giá</div>

          <div class="sb-upload-card" :class="{filled: scanFile, err: !scanFile && tried}"
            @dragover.prevent @drop.prevent="onDrop" @click="$refs.rFile.click()">
            <input ref="rFile" type="file" accept=".pdf,.docx,.html,.htm" hidden
              @change="e => scanFile = e.target.files[0] || null"/>
            <div class="upc-icon">{{ scanFile ? '📄' : '🗂️' }}</div>
            <div class="upc-info" :title="scanFile ? scanFile.name : ''">
              <div class="upc-label">Phiếu đánh giá thử việc</div>
              <div class="upc-val" :class="scanFile ? 'ok' : 'empty'">
                {{ scanFile ? scanFile.name : 'Click hoặc kéo thả file' }}
              </div>
              <div v-if="!scanFile" class="upc-hint">Định dạng: .pdf, .docx, .html</div>
            </div>
            <button v-if="scanFile" class="upc-rm" @click.stop="scanFile = null">✕</button>
          </div>

          <p v-if="tried && !scanFile" class="sb-err">Vui lòng chọn file</p>

          <button class="sb-btn-primary" :disabled="loading" @click="doExtract">
            <span v-if="loading" class="spinner"></span>
            <svg v-else width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
            {{ loading ? loadingMsg : 'Quét & Trích xuất phiếu' }}
          </button>

          <div v-if="error" class="sb-err-box">{{ error }}</div>
        </div>

        <!-- BƯỚC 3: Kết quả -->
        <div v-if="step === 3" class="sb-section">
          <div class="sb-section-title">📊 Kết quả</div>
          <div v-if="result" class="sb-badge" :class="badgeCls">
            <div class="badge-icon">{{ badgeIcon }}</div>
            <div class="badge-text">{{ result.de_xuat }}</div>
          </div>
          <div v-if="result?.deadline_alert" class="sb-deadline-warn">
            ⏰ Còn {{ result.so_ngay_con_lai }} ngày đến hạn!
          </div>

          <div v-if="hasHandwriting" class="hw-badge" style="margin:8px 0">✍️ Có chữ viết tay HOD</div>

          <button v-if="phieuDirty" class="sb-btn-primary" :disabled="loading" @click="savePhieu">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
            Lưu thay đổi
          </button>

          <button v-if="scanSessionId" class="sb-btn-docx" :disabled="loadingDocx" @click="downloadDocx">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><path d="M16 13H8M16 17H8M10 9H8"/></svg>
            {{ loadingDocx ? 'Đang tạo...' : 'Tải DOCX' }}
          </button>
          <button class="sb-btn-secondary" @click="exportReport">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            Xuất báo cáo PDF
          </button>
          <button class="sb-btn-ghost" @click="resetAll">
            ↩ Đánh giá phiếu khác
          </button>
        </div>
      </div>
    </aside>

    <!-- MAIN PANEL -->
    <main class="result-panel">

      <!-- BƯỚC 1: Welcome -->
      <div v-if="step === 1 && !loading" class="welcome">
        <div class="welcome-icon">
          <svg width="56" height="56" viewBox="0 0 56 56" fill="none">
            <rect width="56" height="56" rx="18" fill="url(#wg)"/>
            <text x="28" y="38" text-anchor="middle" font-size="26">📋</text>
            <defs><linearGradient id="wg" x1="0" y1="0" x2="56" y2="56">
              <stop stop-color="#6366f1"/><stop offset="1" stop-color="#8b5cf6"/>
            </linearGradient></defs>
          </svg>
        </div>
        <h1>Đánh Giá Phiếu Thử Việc từ Scan</h1>
        <p>Upload phiếu đánh giá dạng PDF/DOCX/HTML. AI sẽ tự động đọc toàn bộ nội dung, điền vào bảng đánh giá đầy đủ — bao gồm chữ viết tay của HOD.</p>
        <div class="welcome-features">
          <div class="wf"><div class="wf-icon">📄</div><div>Đọc PDF, DOCX, HTML</div></div>
          <div class="wf"><div class="wf-icon">✍️</div><div>Nhận diện chữ viết tay HOD</div></div>
          <div class="wf"><div class="wf-icon">✏️</div><div>Sửa trực tiếp trên phiếu</div></div>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="loading-screen">
        <div class="loading-spinner"></div>
        <p>{{ loadingMsg }}</p>
        <p class="loading-sub">Quá trình này có thể mất 1–3 phút tùy số trang</p>
      </div>

      <!-- BƯỚC 3: Phiếu + Phân tích -->
      <div v-if="step === 3 && result && !loading" class="results-scroll">

        <!-- Tab bar -->
        <div class="result-tabs">
          <button class="rtab" :class="{rtab__active: activeTab==='phieu'}" @click="activeTab='phieu'">
            📋 Phiếu Đánh Giá
          </button>
          <button class="rtab" :class="{rtab__active: activeTab==='analysis'}" @click="activeTab='analysis'">
            🤖 Phân Tích AI
          </button>
        </div>

        <!-- ── PHIẾU ĐÁNH GIÁ ────────────────────────────── -->
        <div v-if="activeTab==='phieu'" class="phieu-view">
          <div class="phieu-title">PHIẾU ĐÁNH GIÁ HOÀN THÀNH THỬ VIỆC</div>
          <div class="phieu-subtitle">CT Group – CTG-GO-NLCD-QT16-BM01</div>

          <!-- Dirty bar -->
          <div v-if="phieuDirty" class="phieu-dirty-bar">
            ⚠️ Có thay đổi chưa lưu
            <button class="db-save" @click="savePhieu">💾 Lưu</button>
            <button class="db-cancel" @click="cancelEdit">✕ Huỷ</button>
          </div>

          <!-- A. THÔNG TIN CHUNG -->
          <div class="phieu-section-head">A. THÔNG TIN CHUNG – THÀNH PHẦN THAM DỰ</div>
          <table class="phieu-table">
            <thead><tr>
              <th style="width:30%">Nội dung</th>
              <th>CBNV được đánh giá</th>
              <th style="width:28%">HOD / Người được UQ đánh giá</th>
              <th style="width:8%">RTD</th>
              <th style="width:8%">GAD</th>
            </tr></thead>
            <tbody>
              <tr>
                <td class="phieu-label">Họ và tên</td>
                <td><input class="pe-input" v-model="ef.ho_ten"/></td>
                <td><input class="pe-input pe-hod" v-model="ef.ten_hod" placeholder="Tên HOD (viết tay)"/></td>
                <td></td><td></td>
              </tr>
              <tr>
                <td class="phieu-label">Mã NV</td>
                <td><input class="pe-input" v-model="ef.ma_nhan_su"/></td>
                <td><input class="pe-input pe-hod" v-model="ef.ma_hod" placeholder="Mã HOD"/></td>
                <td></td><td></td>
              </tr>
              <tr>
                <td class="phieu-label">Chức danh</td>
                <td><input class="pe-input" v-model="ef.chuc_danh"/></td>
                <td><input class="pe-input pe-hod" v-model="ef.chuc_danh_hod" placeholder="Chức danh HOD"/></td>
                <td></td><td></td>
              </tr>
              <tr>
                <td class="phieu-label">Đơn vị</td>
                <td><input class="pe-input" v-model="ef.phong_ban"/></td>
                <td><input class="pe-input pe-hod" v-model="ef.don_vi_hod" placeholder="Đơn vị HOD"/></td>
                <td></td><td></td>
              </tr>
              <tr>
                <td class="phieu-label">Ngày nhận việc</td>
                <td><input class="pe-input" v-model="ef.ngay_nhan_viec"/></td>
                <td></td><td></td><td></td>
              </tr>
              <tr>
                <td class="phieu-label">Ngày hết hạn thử việc</td>
                <td><input class="pe-input" v-model="ef.ngay_het_han"/></td>
                <td></td><td></td><td></td>
              </tr>
            </tbody>
          </table>

          <!-- B. PHẦN I – NHẬN XÉT CHUNG -->
          <div class="phieu-section-head">B. NỘI DUNG ĐÁNH GIÁ – PHẦN I: NHẬN XÉT CHUNG</div>
          <table class="phieu-table">
            <thead><tr>
              <th style="width:30px">STT</th>
              <th style="width:28%">Nội dung</th>
              <th>Ứng viên tự đánh giá</th>
              <th style="width:24%">HOD đánh giá <small style="color:#fbbf24">✍</small></th>
            </tr></thead>
            <tbody>
              <tr v-for="r in nhanXetRows" :key="'nx'+r.stt">
                <td class="phieu-center phieu-label">{{ r.stt }}</td>
                <td class="phieu-label" style="white-space:normal;font-size:.8rem">{{ r.cau_hoi }}</td>
                <td><textarea class="pe-textarea" v-model="ef[r.nvKey]" rows="4"></textarea></td>
                <td><textarea class="pe-textarea pe-hod" v-model="ef[r.hodKey]" rows="4" placeholder="HOD viết tay..."></textarea></td>
              </tr>
            </tbody>
          </table>

          <!-- PHẦN II - KPI -->
          <div class="phieu-section-head">PHẦN II: KẾT QUẢ THỰC HIỆN KPI</div>
          <table class="phieu-table">
            <thead><tr>
              <th>Tuần</th>
              <th style="width:80px">% KPI (NV)</th>
            </tr></thead>
            <tbody>
              <tr v-for="i in nTuan" :key="'kpi'+i">
                <td class="phieu-label">Tuần thứ {{ i }}</td>
                <td><input class="pe-input" style="text-align:center" :value="ef[`kpi_tuan_${i}_ty_le`]" @input="ef[`kpi_tuan_${i}_ty_le`]=$event.target.value"/></td>
              </tr>
              <tr style="background:rgba(99,102,241,.06)">
                <td class="phieu-label" style="font-weight:700">1.5. Điểm TBC KPI (bình quân {{ nTuan }} tuần)</td>
                <td><input class="pe-input" style="text-align:center;font-weight:700" v-model="ef.diem_tbc_kpi_nv"/></td>
              </tr>
              <tr style="background:rgba(251,191,36,.06)">
                <td class="phieu-label" style="color:#fbbf24">↳ HOD ghi điểm TBC (viết tay)</td>
                <td><input class="pe-input pe-hod" style="text-align:center" v-model="ef.diem_tbc_kpi_hod" placeholder="81%..."/></td>
              </tr>
            </tbody>
          </table>

          <!-- 1.6 Cong viec duoc giao -->
          <div class="phieu-section-head">1.6. CÔNG VIỆC ĐƯỢC GIAO &amp; KẾT QUẢ THỰC HIỆN</div>
          <table class="phieu-table">
            <thead><tr>
              <th style="width:28px">STT</th>
              <th>Nội dung nhiệm vụ được giao</th>
              <th>Kết quả thực tế đạt được</th>
              <th style="width:80px">% Hoàn thành</th>
              <th style="width:120px">HOD nhận xét <small style="color:#fbbf24">✍</small></th>
            </tr></thead>
            <tbody>
              <tr v-for="i in nNhiemVu" :key="'nv'+i">
                <td class="phieu-center phieu-label">{{ i }}</td>
                <td><textarea class="pe-textarea" :value="ef[`nhiem_vu_${i}_noi_dung`]" @input="ef[`nhiem_vu_${i}_noi_dung`]=$event.target.value" rows="3" placeholder="Nội dung nhiệm vụ..."></textarea></td>
                <td><textarea class="pe-textarea" :value="ef[`nhiem_vu_${i}_ket_qua`]" @input="ef[`nhiem_vu_${i}_ket_qua`]=$event.target.value" rows="3" placeholder="Kết quả thực tế..."></textarea></td>
                <td><input class="pe-input" style="text-align:center;font-weight:700" :value="ef[`nhiem_vu_${i}_ty_le`]" @input="ef[`nhiem_vu_${i}_ty_le`]=$event.target.value" placeholder="90%"/></td>
                <td><textarea class="pe-textarea pe-hod" :value="ef[`nhiem_vu_${i}_hod`]" @input="ef[`nhiem_vu_${i}_hod`]=$event.target.value" rows="3" placeholder="HOD ghi..."></textarea></td>
              </tr>
              <tr style="background:rgba(99,102,241,.06)">
                <td colspan="3" class="phieu-label" style="font-weight:700;text-align:right">% Hoàn thành chung:</td>
                <td><input class="pe-input" style="text-align:center;font-weight:800" v-model="ef.ty_le_hoan_thanh_16" placeholder="90%"/></td>
                <td></td>
              </tr>
            </tbody>
          </table>

          <!-- 2. Sản phẩm nghiệm thu -->
          <div class="phieu-section-head">2. SẢN PHẨM NGHIỆM THU ({{ nTuan }} TUẦN)</div>
          <div v-for="i in nTuan" :key="'sp'+i" class="sp-card">
            <div class="sp-head">
              Tuần {{ i }}
              <span class="sp-kpi" :class="kpiClass(ef[`kpi_sp_tuan_${i}`])">{{ ef[`kpi_sp_tuan_${i}`] || '—' }}</span>
            </div>
            <table class="phieu-table" style="margin-top:6px">
              <tbody>
                <tr>
                  <td class="phieu-label" style="width:26%">Sản phẩm</td>
                  <td colspan="2"><textarea class="pe-textarea" :value="ef[`san_pham_${i}`]" @input="ef[`san_pham_${i}`]=$event.target.value" rows="3" placeholder="+ Tên sản phẩm..."></textarea></td>
                </tr>
                <tr>
                  <td class="phieu-label">Số lượng file</td>
                  <td><input class="pe-input" :value="ef[`so_luong_file_${i}`]" @input="ef[`so_luong_file_${i}`]=$event.target.value" style="width:80px"/></td>
                  <td class="phieu-label" style="width:30%">% KPI tuần {{ i }}: <input class="pe-input" :value="ef[`kpi_sp_tuan_${i}`]" @input="ef[`kpi_sp_tuan_${i}`]=$event.target.value" style="width:60px;display:inline"/></td>
                </tr>
                <tr>
                  <td class="phieu-label">🔗 Đường link đính kèm</td>
                  <td colspan="2"><textarea class="pe-textarea pe-link-main" :value="ef[`link_dinh_kem_${i}`]" @input="ef[`link_dinh_kem_${i}`]=$event.target.value" rows="3" placeholder="DAIT-Thư ký tập sự-Nguyễn Thị Thanh Bình-TênFile.xlsx&#10;(mỗi file một dòng)"></textarea></td>
                </tr>
                <tr>
                  <td class="phieu-label">Số lần vi phạm upload</td>
                  <td colspan="2"><input class="pe-input" :value="ef[`vi_pham_upload_${i}`]" @input="ef[`vi_pham_upload_${i}`]=$event.target.value" placeholder="VD: 1 – 12/6/2025"/></td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- PHẦN III – HỘI NHẬP -->
          <div class="phieu-section-head">PHẦN III: MỨC ĐỘ HỘI NHẬP TRONG GIAI ĐOẠN THỬ VIỆC</div>
          <table class="phieu-table">
            <thead><tr>
              <th style="width:30px">STT</th>
              <th style="width:26%">Câu hỏi</th>
              <th>Ứng viên tự đánh giá</th>
              <th style="width:22%">HOD đánh giá <small style="color:#fbbf24">✍</small></th>
            </tr></thead>
            <tbody>
              <tr v-for="r in hoiNhapEditRows" :key="'hn'+r.stt">
                <td class="phieu-center phieu-label">{{ r.stt }}</td>
                <td class="phieu-label" style="white-space:normal;font-size:.8rem">{{ r.cau_hoi }}</td>
                <td><textarea class="pe-textarea" v-model="ef[r.nvKey]" rows="3"></textarea></td>
                <td><textarea class="pe-textarea pe-hod" v-model="ef[r.hodKey]" rows="3" :placeholder="ef[r.hodKey] ? '' : 'HOD đánh giá...'"></textarea></td>
              </tr>
            </tbody>
          </table>

          <!-- C. KẾT LUẬN -->
          <div class="phieu-section-head">C. KẾT LUẬN VÀ ĐỀ XUẤT</div>
          <table class="phieu-table">
            <thead><tr>
              <th style="width:35%">Kết luận</th>
              <th>Đề xuất</th>
              <th style="width:20%">Đề nghị phối hợp</th>
            </tr></thead>
            <tbody>
              <tr v-for="row in ketLuanRows" :key="row.id" @click="selectKetLuan(row)" style="cursor:pointer">
                <td :class="{'phieu-selected': row.selected}">
                  <span class="phieu-checkbox">{{ row.selected ? '☑' : '☐' }}</span>
                  {{ row.ket_luan }}
                </td>
                <td>
                  <span v-if="row.id==='dat'">
                    Ký hợp đồng:
                    <input class="pe-input pe-hod" v-model="ef.de_xuat_ky_hd" placeholder="VD: HĐNV 4 tháng, part-time..." @click.stop/>
                    <input class="pe-input" v-model="ef.de_xuat_tang_thu_nhap" placeholder="Tăng thu nhập: ..." @click.stop style="margin-top:4px"/>
                  </span>
                  <span v-else>{{ row.de_xuat }}</span>
                </td>
                <td><textarea class="pe-textarea" v-model="ef.de_nghi_phoi_hop" rows="2" @click.stop></textarea></td>
              </tr>
            </tbody>
          </table>

          <!-- Bảng ký -->
          <div class="phieu-section-head">KÝ XÁC NHẬN</div>
          <table class="phieu-table">
            <thead><tr>
              <th>Trách nhiệm</th>
              <th>HOD / Người được UQ đánh giá</th>
              <th>Đại diện RTD</th>
              <th>Đại diện GAD</th>
              <th>Phê duyệt</th>
            </tr></thead>
            <tbody>
              <tr>
                <td class="phieu-label">Ý kiến</td>
                <td><textarea class="pe-textarea pe-hod" v-model="ef.y_kien_hod" rows="2"></textarea></td>
                <td><textarea class="pe-textarea" v-model="ef.y_kien_rtd" rows="2"></textarea></td>
                <td></td>
                <td class="phieu-label" style="text-align:center">Tổng Giám đốc</td>
              </tr>
              <tr>
                <td class="phieu-label">Ngày ký</td>
                <td><input class="pe-input" v-model="ef.ngay_ky"/></td>
                <td></td><td></td><td></td>
              </tr>
              <tr>
                <td class="phieu-label">Họ tên (ký)</td>
                <td><input class="pe-input pe-hod" v-model="ef.ten_hod_ky" placeholder="Tên HOD ký..."/></td>
                <td></td><td></td><td></td>
              </tr>
            </tbody>
          </table>
        </div><!-- /phieu-view -->

        <!-- ── PHÂN TÍCH AI ────────────────────────────────────── -->
        <div v-if="activeTab==='analysis'" class="result-card">
          <div class="rc-overview">
            <div v-if="result.analysis" class="analysis-content">
              <div class="de-xuat-badge" :class="result.analysis.mau_de_xuat">{{ result.analysis.de_xuat }}</div>
              <p class="tong-quan">{{ result.analysis.tong_quan }}</p>
              <div v-for="item in result.analysis.phan_tich" :key="item.tieu_chi" class="phan-tich-row">
                <span class="tc-label">{{ item.tieu_chi }}</span>
                <span class="tc-danh-gia" :class="item.danh_gia==='Đạt'?'green':'amber'">{{ item.danh_gia }}</span>
                <p class="tc-nhan-xet">{{ item.nhan_xet }}</p>
              </div>
            </div>
            <div v-else class="no-analysis">Chưa có phân tích AI. Nhấn Scan để phân tích.</div>
          </div>
        </div>

      </div><!-- /results-scroll -->
    </main>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
defineEmits(['back'])

// ─ State ──────────────────────────────────────────────────────────────────────
const step = ref(1)
const scanFile = ref(null)
const tried = ref(false)
const loading = ref(false)
const loadingMsg = ref('Đang đọc file...')
const rawMarkdown = ref('')
const error = ref('')
const ocrNote = ref('')
const hasHandwriting = ref(false)
const scanSessionId = ref('')
const result = ref(null)
const extractedConfidence = ref({})
const sec = reactive({ criteria: true, warn: true, tasks: false })
const xmlOutput = ref('')
const activeTab = ref('phieu')

// ef = editable fields — theo đúng cấu trúc CTG-GO-NLCD-QT16-BM01
const ef = reactive({
  // A. Thông tin chung
  ho_ten:'', ma_nhan_su:'', chuc_danh:'', phong_ban:'', cong_ty:'',
  ngay_nhan_viec:'', ngay_het_han:'', thoi_gian_thu_viec:'', loai_hop_dong:'',
  ten_hod:'', ma_hod:'', chuc_danh_hod:'', don_vi_hod:'',

  // B. Phần I – Nhận xét chung (5 câu, NV + HOD)
  nhan_xet_1_nv:'', nhan_xet_1_hod:'',
  nhan_xet_2_nv:'', nhan_xet_2_hod:'',
  nhan_xet_3_nv:'', nhan_xet_3_hod:'',
  nhan_xet_4_nv:'', nhan_xet_4_hod:'',
  nhan_xet_5_nv:'', nhan_xet_5_hod:'',

  // C. Phần II – KPI tối đa 8 tuần + TBC
  kpi_tuan_1_ty_le:'', kpi_tuan_2_ty_le:'', kpi_tuan_3_ty_le:'', kpi_tuan_4_ty_le:'',
  kpi_tuan_5_ty_le:'', kpi_tuan_6_ty_le:'', kpi_tuan_7_ty_le:'', kpi_tuan_8_ty_le:'',
  diem_tbc_kpi_nv:'', diem_tbc_kpi_hod:'',
  cong_viec_duoc_giao:'',
  ty_le_hoan_thanh_16:'',
  // 1.6 Nhiệm vụ tối đa 8 (mỗi nhiệm vụ: nội dung + kết quả + % + HOD)
  nhiem_vu_1_noi_dung:'', nhiem_vu_1_ket_qua:'', nhiem_vu_1_ty_le:'', nhiem_vu_1_hod:'',
  nhiem_vu_2_noi_dung:'', nhiem_vu_2_ket_qua:'', nhiem_vu_2_ty_le:'', nhiem_vu_2_hod:'',
  nhiem_vu_3_noi_dung:'', nhiem_vu_3_ket_qua:'', nhiem_vu_3_ty_le:'', nhiem_vu_3_hod:'',
  nhiem_vu_4_noi_dung:'', nhiem_vu_4_ket_qua:'', nhiem_vu_4_ty_le:'', nhiem_vu_4_hod:'',
  nhiem_vu_5_noi_dung:'', nhiem_vu_5_ket_qua:'', nhiem_vu_5_ty_le:'', nhiem_vu_5_hod:'',
  nhiem_vu_6_noi_dung:'', nhiem_vu_6_ket_qua:'', nhiem_vu_6_ty_le:'', nhiem_vu_6_hod:'',
  nhiem_vu_7_noi_dung:'', nhiem_vu_7_ket_qua:'', nhiem_vu_7_ty_le:'', nhiem_vu_7_hod:'',
  nhiem_vu_8_noi_dung:'', nhiem_vu_8_ket_qua:'', nhiem_vu_8_ty_le:'', nhiem_vu_8_hod:'',

  // Sản phẩm tối đa 8 tuần
  san_pham_1:'', so_luong_file_1:'', link_dinh_kem_1:'', vi_pham_upload_1:'', kpi_sp_tuan_1:'',
  san_pham_2:'', so_luong_file_2:'', link_dinh_kem_2:'', vi_pham_upload_2:'', kpi_sp_tuan_2:'',
  san_pham_3:'', so_luong_file_3:'', link_dinh_kem_3:'', vi_pham_upload_3:'', kpi_sp_tuan_3:'',
  san_pham_4:'', so_luong_file_4:'', link_dinh_kem_4:'', vi_pham_upload_4:'', kpi_sp_tuan_4:'',
  san_pham_5:'', so_luong_file_5:'', link_dinh_kem_5:'', vi_pham_upload_5:'', kpi_sp_tuan_5:'',
  san_pham_6:'', so_luong_file_6:'', link_dinh_kem_6:'', vi_pham_upload_6:'', kpi_sp_tuan_6:'',
  san_pham_7:'', so_luong_file_7:'', link_dinh_kem_7:'', vi_pham_upload_7:'', kpi_sp_tuan_7:'',
  san_pham_8:'', so_luong_file_8:'', link_dinh_kem_8:'', vi_pham_upload_8:'', kpi_sp_tuan_8:'',

  // D. Phần III – Hội nhập (9 câu, mỗi câu NV + HOD)
  hoi_nhap_1_nv:'', hoi_nhap_1_hod:'',
  hoi_nhap_2_nv:'', hoi_nhap_2_hod:'',
  hoi_nhap_3_nv:'', hoi_nhap_3_hod:'',
  hoi_nhap_4_nv:'', hoi_nhap_4_hod:'',
  hoi_nhap_5_nv:'', hoi_nhap_5_hod:'',
  hoi_nhap_6_nv:'', hoi_nhap_6_hod:'',
  hoi_nhap_7_nv:'', hoi_nhap_7_hod:'',
  hoi_nhap_7_1_nv:'', hoi_nhap_7_2_nv:'', hoi_nhap_7_3_nv:'', hoi_nhap_7_4_nv:'', hoi_nhap_7_5_nv:'',
  hoi_nhap_8_nv:'', hoi_nhap_8_hod:'',
  hoi_nhap_9_nv:'', hoi_nhap_9_hod:'',

  // E. Kết luận
  ket_luan:'', de_xuat_ky_hd:'', de_xuat_tang_thu_nhap:'', de_nghi_phoi_hop:'',
  y_kien_hod:'', y_kien_rtd:'', ngay_ky:'', ten_hod_ky:'',
})


// Track dirty state
const efSnapshot = ref('')
const phieuDirty = computed(() => efSnapshot.value !== JSON.stringify(ef))

function populateEf(fields) {
  if (!fields) return
  Object.keys(ef).forEach(k => {
    if (k in fields) {
      if (typeof ef[k] === 'object' && typeof fields[k] === 'object') {
        Object.assign(ef[k], fields[k])
      } else {
        ef[k] = fields[k] ?? ''
      }
    }
  })
  // HOD viết tay: nếu có ghi_chu_viet_tay và chưa có hod_nhan_xet_chung thì đưa vào
  if (!ef.hod_nhan_xet_chung && ef.ghi_chu_viet_tay) {
    ef.hod_nhan_xet_chung = ef.ghi_chu_viet_tay
  }
  efSnapshot.value = JSON.stringify(ef)
}

// ─── Nhận xét chung rows ─────────────────────────────────────────────────────
const nhanXetRows = [
  { stt:'1', nvKey:'nhan_xet_1_nv', hodKey:'nhan_xet_1_hod', cau_hoi:'Những điểm ứng viên đã làm tốt trong quá trình thử việc?' },
  { stt:'2', nvKey:'nhan_xet_2_nv', hodKey:'nhan_xet_2_hod', cau_hoi:'Các kỹ năng nào của ứng viên đã đáp ứng yêu cầu công việc?' },
  { stt:'3', nvKey:'nhan_xet_3_nv', hodKey:'nhan_xet_3_hod', cau_hoi:'Ứng viên đã tích cực tham gia các hoạt động nào?' },
  { stt:'4', nvKey:'nhan_xet_4_nv', hodKey:'nhan_xet_4_hod', cau_hoi:'Những điểm ứng viên cần cải thiện căn cứ vào kết quả quá trình thử việc?' },
  { stt:'5', nvKey:'nhan_xet_5_nv', hodKey:'nhan_xet_5_hod', cau_hoi:'Để nâng cao hiệu quả công việc, ứng viên cần trau dồi thêm kỹ năng nào hoặc khắc phục hạn chế nào?' },
]

// ─── Hội nhập rows (9 câu + sub 7.1-7.5) ─────────────────────────────────────
const hoiNhapEditRows = [
  { stt:'1',   nvKey:'hoi_nhap_1_nv',   hodKey:'hoi_nhap_1_hod',   cau_hoi:'Ứng viên hiểu gì về Sứ mệnh của Tập đoàn?' },
  { stt:'2',   nvKey:'hoi_nhap_2_nv',   hodKey:'hoi_nhap_2_hod',   cau_hoi:'Sứ mệnh của bản thân ứng viên là gì từ nhận thức về Sứ mệnh Tập đoàn?' },
  { stt:'3',   nvKey:'hoi_nhap_3_nv',   hodKey:'hoi_nhap_3_hod',   cau_hoi:'Ứng viên hiểu gì về Tầm nhìn của Tập đoàn? (Tầm nhìn 2025 và 2052)' },
  { stt:'4',   nvKey:'hoi_nhap_4_nv',   hodKey:'hoi_nhap_4_hod',   cau_hoi:'Tầm nhìn của bản thân ứng viên là gì từ nhận thức về Tầm nhìn Tập đoàn?' },
  { stt:'5',   nvKey:'hoi_nhap_5_nv',   hodKey:'hoi_nhap_5_hod',   cau_hoi:'Ứng viên hiểu gì về Văn hoá cốt lõi của Tập đoàn?' },
  { stt:'6',   nvKey:'hoi_nhap_6_nv',   hodKey:'hoi_nhap_6_hod',   cau_hoi:'Giá trị cốt lõi của bản thân ứng viên là gì từ nhận thức về GTCL Tập đoàn?' },
  { stt:'7',   nvKey:'hoi_nhap_7_nv',   hodKey:'hoi_nhap_7_hod',   cau_hoi:'Sự phù hợp của ứng viên đối với Văn hoá làm việc của Tập đoàn?' },
  { stt:'7.1', nvKey:'hoi_nhap_7_1_nv', hodKey:'',                 cau_hoi:'  → Văn hóa Hiệu quả: KPIs, con số, thái độ, tư duy hiệu quả' },
  { stt:'7.2', nvKey:'hoi_nhap_7_2_nv', hodKey:'',                 cau_hoi:'  → Văn hóa Tốc độ' },
  { stt:'7.3', nvKey:'hoi_nhap_7_3_nv', hodKey:'',                 cau_hoi:'  → Văn hóa Kỷ luật: tuân thủ QTQD, Quy chế, Chính sách' },
  { stt:'7.4', nvKey:'hoi_nhap_7_4_nv', hodKey:'',                 cau_hoi:'  → Văn hóa Học tập: số giờ tự học, đào tạo, giảng dạy, đóng góp' },
  { stt:'7.5', nvKey:'hoi_nhap_7_5_nv', hodKey:'',                 cau_hoi:'  → Văn hóa Chính trực' },
  { stt:'8',   nvKey:'hoi_nhap_8_nv',   hodKey:'hoi_nhap_8_hod',   cau_hoi:'Ứng viên hiểu gì về Văn hoá kinh doanh của Tập đoàn?' },
  { stt:'9',   nvKey:'hoi_nhap_9_nv',   hodKey:'hoi_nhap_9_hod',   cau_hoi:'Các đóng góp khác của ứng viên trong thời gian hội nhập?' },
]

// ─── Computed: số tuần thực tế (dựa vào kpi_tuan_N_ty_le có giá trị, min 4)
const nTuan = computed(() => {
  let n = 0
  for (let i = 8; i >= 1; i--) {
    if (ef[`kpi_tuan_${i}_ty_le`] || ef[`san_pham_${i}`]) { n = i; break }
  }
  return Math.max(n, 4) // hiển tối thiểu 4 để trống vẫn hiển thị
})

// ─── Computed: số nhiệm vụ thực tế ở 1.6 (min 1)
const nNhiemVu = computed(() => {
  let n = 0
  for (let i = 8; i >= 1; i--) {
    if (ef[`nhiem_vu_${i}_noi_dung`] || ef[`nhiem_vu_${i}_ket_qua`]) { n = i; break }
  }
  return Math.max(n, 1)
})

function kpiClass(val) {
  const n = parseFloat((val || '').replace('%','').trim())
  if (isNaN(n)) return ''
  if (n >= 90) return 'kpi-green'
  if (n >= 75) return 'kpi-amber'
  return 'kpi-red'
}

// ─── Kết luận checkbox ────────────────────────────────────────────────────────
const ketLuanRows = computed(() => {
  const kl = (ef.ket_luan || ef.ket_qua_danh_gia || '').toLowerCase()
  const dx = ef.de_xuat_ky_hd || ef.hod_de_xuat || ''
  return [
    { id:'dat', ket_luan:'Ứng viên đạt yêu cầu', de_xuat:`Ký hợp đồng: ${dx}`,
      selected: kl.includes('đạt') && !kl.includes('không') },
    { id:'khdat_nokha', ket_luan:'Không đạt yêu cầu và không có khả năng khắc phục, cải thiện trong thời gian ngắn',
      de_xuat:'Kết thúc thử việc với ứng viên',
      selected: kl.includes('không đạt') && kl.includes('không có khả năng') },
    { id:'giahan', ket_luan:'Không đạt yêu cầu nhưng có khả năng khắc phục, cải thiện trong thời gian ngắn',
      de_xuat:`Gia hạn thời gian thử việc: ${ef.thoi_gian_thu_viec_ghihan||''}`,
      selected: kl.includes('gia hạn') },
    { id:'rtd', ket_luan:'Không đạt yêu cầu tại đơn vị nhưng có thể phù hợp ở vị trí khác',
      de_xuat:'RTD phỏng vấn ứng viên ở vị trí mới',
      selected: kl.includes('rtd') || kl.includes('vị trí khác') },
  ]
})

function selectKetLuan(row) {
  ef.ket_luan = row.ket_luan
  ef.ket_qua_danh_gia = row.ket_luan
}



// ─── Lưu phiếu ────────────────────────────────────────────────────────────────
function savePhieu() {
  if (result.value) {
    result.value.confirmed_fields = { ...result.value.confirmed_fields, ...JSON.parse(JSON.stringify(ef)) }
  }
  efSnapshot.value = JSON.stringify(ef)
}
function resetPhieu() {
  if (result.value?.confirmed_fields) populateEf(result.value.confirmed_fields)
}

// ─── Display fields ───────────────────────────────────────────────────────────
const nvDisplayFields = [
  { key: 'ho_ten', label: 'Họ tên' },
  { key: 'ma_nhan_su', label: 'Mã NV' },
  { key: 'chuc_danh', label: 'Chức danh' },
  { key: 'phong_ban', label: 'Đơn vị' },
  { key: 'ngay_het_han', label: 'Hết hạn TV' },
]

const badgeCls = computed(() => {
  const m = result.value?.mau_de_xuat
  if (m === 'green') return 'badge-green'
  if (m === 'red') return 'badge-red'
  return 'badge-amber'
})
const badgeIcon = computed(() => {
  const m = result.value?.mau_de_xuat
  if (m === 'green') return '✓'
  if (m === 'red') return '✗'
  return '!'
})

function toggle(k) { sec[k] = !sec[k] }

function onDrop(e) {
  const f = e.dataTransfer.files[0]
  if (!f) return
  const n = f.name.toLowerCase()
  if (n.endsWith('.pdf') || n.endsWith('.docx') || n.endsWith('.html') || n.endsWith('.htm'))
    scanFile.value = f
}

function resetAll() {
  step.value = 1
  scanFile.value = null
  tried.value = false
  error.value = ''
  result.value = null
  ocrNote.value = ''
  scanSessionId.value = ''
  xmlOutput.value = ''
  activeTab.value = 'phieu'
  Object.keys(ef).forEach(k => {
    if (typeof ef[k] === 'object' && ef[k] !== null) Object.assign(ef[k], {ty_le:'',nhiem_vu:'',san_pham:'',vi_pham_upload:''})
    else ef[k] = ''
  })
}

function csrf() {
  if (window.frappe?.csrf_token) return window.frappe.csrf_token
  const c = document.cookie.split('; ').find(r => r.startsWith('csrf_token='))?.split('=')[1]
  return c ? decodeURIComponent(c) : ''
}

async function apiCall(method, body) {
  const url = `/api/method/cnb_2as.api.scan_phieu.${method}`
  const opts = { method: 'POST', headers: { 'X-Frappe-CSRF-Token': csrf() } }
  if (body instanceof FormData) {
    opts.body = body
  } else {
    opts.headers['Content-Type'] = 'application/json'
    opts.body = JSON.stringify(body)
  }
  const r = await fetch(url, opts)
  const j = await r.json()
  if (!r.ok) throw new Error(j?.exception || j?.message || `HTTP ${r.status}`)
  return j.message ?? j
}

// ─ Actions ────────────────────────────────────────────────────────────────────
async function doExtract() {
  tried.value = true
  if (!scanFile.value) return
  loading.value = true
  error.value = ''
  loadingMsg.value = '📄 AI đang đọc file (Vision OCR)...'
  try {
    const fd = new FormData()
    fd.append('scan_file', scanFile.value)
    const d = await apiCall('scan_extract', fd)
    scanSessionId.value = d.scan_session_id || ''
    ocrNote.value = d.ocr_note || ''
    hasHandwriting.value = d.has_handwriting || false
    rawMarkdown.value = d.raw_markdown || ''
    if (d.xml_output) xmlOutput.value = d.xml_output
    extractedConfidence.value = (d.extracted_fields || {}).confidence || {}

    // Tự động phân tích ngay
    loadingMsg.value = '🧠 AI đang phân tích và lập bảng đánh giá...'
    const d2 = await apiCall('scan_analyze', {
      scan_session_id: scanSessionId.value,
      xml_input: d.xml_output || '',
    })
    result.value = d2
    if (d2.xml_output) xmlOutput.value = d2.xml_output
    // Populate editable form
    populateEf(d2.confirmed_fields || d.extracted_fields || {})
    step.value = 3
    activeTab.value = 'phieu'
    sec.criteria = true; sec.warn = true; sec.tasks = false
  } catch (e) {
    error.value = '❌ ' + e.message
  } finally {
    loading.value = false
  }
}

const loadingDocx = ref(false)
async function downloadDocx() {
  if (!scanSessionId.value) return
  loadingDocx.value = true
  try {
    const data = await apiCall('fill_docx', { scan_session_id: scanSessionId.value })
    const binary = atob(data.content_b64)
    const bytes = new Uint8Array(binary.length)
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
    const blob = new Blob([bytes], { type: data.content_type })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = data.filename
    document.body.appendChild(a); a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (e) {
    alert('❌ Lỗi tạo DOCX: ' + (e.message || e))
  } finally {
    loadingDocx.value = false
  }
}

function exportReport() {
  const r = result.value
  if (!r) return
  const cfr = r.confirmed_fields || ef
  const now = new Date().toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' })
  const colorMap = { green: '#059669', amber: '#d97706', red: '#dc2626' }
  const mau = r.mau_de_xuat || 'amber'
  const color = colorMap[mau] || colorMap.amber
  const field = (label, val) => val ? `<div style="display:flex;gap:8px;padding:4px 0;border-bottom:1px solid #f1f5f9"><span style="min-width:150px;color:#94a3b8;font-size:.8rem;font-weight:600">${label}</span><span style="font-weight:600">${val}</span></div>` : ''
  const html = `<!DOCTYPE html><html><body style="font-family:'Segoe UI',sans-serif;font-size:14px;max-width:860px;margin:0 auto;padding:40px">
    <h2 style="color:${color}">Báo cáo đánh giá thử việc – ${cfr.ho_ten || ''}</h2>
    <p style="color:#6b7280">${now} · CT Group 2AS</p>
    <div style="padding:12px;background:#f8fafc;border-radius:8px;margin:16px 0">
      ${field('Họ tên', cfr.ho_ten)}${field('Mã NV', cfr.ma_nhan_su)}${field('Chức danh', cfr.chuc_danh)}${field('Đơn vị', cfr.phong_ban)}${field('Ngày hết hạn', cfr.ngay_het_han)}
    </div>
    <div style="padding:16px;background:#ecfdf5;border-radius:8px;margin:16px 0;font-size:1.1rem;font-weight:700;color:${color}">${r.de_xuat}</div>
    <p>${r.tong_quan || ''}</p>
    ${(r.phan_tich||[]).map((tc,i) => `<div style="padding:10px 0;border-bottom:1px solid #f3f4f6"><strong>${i+1}. ${tc.tieu_chi}</strong> — <span style="color:${tc.danh_gia?.includes('Đạt') ? '#059669' : '#dc2626'}">${tc.danh_gia}</span><br/><span style="color:#374151">${tc.nhan_xet}</span></div>`).join('')}
  </body></html>`
  const w = window.open('', '_blank', 'width=960,height=780')
  if (w) { w.document.write(html); w.document.close(); setTimeout(() => w.print(), 800) }
}
</script>

<style scoped>
.app-layout { display: flex; height: 100vh; overflow: hidden }

/* ── SIDEBAR ── */
.sidebar { width: 220px; flex-shrink: 0; display: flex; flex-direction: column; overflow-y: auto; border-right: 1px solid rgba(99,102,241,.12); }
.sb-top { padding: 14px 16px; display: flex; align-items: center; gap: 10px; border-bottom: 1px solid transparent; }
.sb-back { width: 30px; height: 30px; border-radius: 8px; background: rgba(99,102,241,.1); display: flex; align-items: center; justify-content: center; color: #818cf8; text-decoration: none; transition: background .2s }
.sb-back:hover { background: rgba(99,102,241,.2) }
.sb-logo { display: flex; align-items: center; gap: 10px }
.sb-logo-mark { width: 34px; height: 34px; border-radius: 10px; background: linear-gradient(135deg,#6366f1,#8b5cf6); display: flex; align-items: center; justify-content: center }
.sb-name { font-size: .85rem; font-weight: 700 }
.sb-org { font-size: .7rem; color: #64748b }
.sb-body { padding: 14px; flex-grow: 1 }
.sb-section { margin-bottom: 18px }
.sb-section-title { font-size: .7rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: .08em; margin-bottom: 12px }

.sb-upload-card { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 10px; border: 1px dashed rgba(99,102,241,.3); background: rgba(99,102,241,.04); cursor: pointer; margin-bottom: 8px; transition: all .2s }
.sb-upload-card:hover { border-color: rgba(99,102,241,.5) }
.sb-upload-card.filled { border-style: solid; border-color: rgba(34,197,94,.4); background: rgba(34,197,94,.06) }
.sb-upload-card.err { border-color: rgba(239,68,68,.4); background: rgba(239,68,68,.06) }
.upc-icon { font-size: 22px; flex-shrink: 0 }
.upc-info { flex-grow: 1; min-width: 0 }
.upc-label { font-size: .7rem; font-weight: 600; color: #94a3b8 }
.upc-hint { font-size: .65rem; color: #cbd5e1; margin-top: 2px }
.upc-val { font-size: .78rem; color: #64748b; white-space: nowrap; overflow: hidden; text-overflow: ellipsis }
.upc-val.ok { color: #4ade80 }
.upc-rm { width: 22px; height: 22px; border: none; background: rgba(239,68,68,.15); color: #f87171; border-radius: 6px; cursor: pointer; font-size: .7rem }

.sb-btn-primary { width: 100%; padding: 10px; border: none; border-radius: 10px; background: linear-gradient(135deg,#6366f1,#8b5cf6); color: #fff; font-weight: 600; font-size: .86rem; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; transition: opacity .2s; margin-top: 8px }
.sb-btn-primary:disabled { opacity: .5; cursor: not-allowed }
.sb-btn-primary:hover:not(:disabled) { opacity: .9 }
.sb-btn-secondary { width: 100%; padding: 9px; border: 1px solid rgba(99,102,241,.4); border-radius: 10px; background: transparent; color: #818cf8; font-weight: 600; font-size: .82rem; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px; margin-top: 8px; transition: all .2s }
.sb-btn-secondary:hover { background: rgba(99,102,241,.1) }
.sb-btn-ghost { width: 100%; padding: 8px; border: none; border-radius: 10px; background: transparent; color: #64748b; font-size: .82rem; cursor: pointer; margin-top: 6px }
.sb-btn-ghost:hover { color: #94a3b8 }
.sb-btn-docx { width: 100%; padding: 9px; border: 1px solid rgba(16,185,129,.5); border-radius: 10px; background: rgba(16,185,129,.12); color: #10b981; font-weight: 700; font-size: .82rem; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px; margin-top: 8px; transition: all .2s }
.sb-btn-docx:hover:not(:disabled) { background: rgba(16,185,129,.22); border-color: #10b981 }
.sb-btn-docx:disabled { opacity: .5; cursor: not-allowed }

/* ─── Phiếu View – Word-like table display ──────────────────────────────── */
.phieu-view { padding: 20px; font-family: 'Inter', sans-serif; font-size: .88rem; color: #e2e8f0 }
.phieu-title { text-align: center; font-size: 1.1rem; font-weight: 800; letter-spacing: .04em; color: #c7d2fe; text-transform: uppercase; margin-bottom: 4px }
.phieu-subtitle { text-align: center; font-size: .82rem; color: #94a3b8; margin-bottom: 20px }
.phieu-section-head {
  background: linear-gradient(90deg, rgba(99,102,241,.25), rgba(99,102,241,.05));
  border-left: 3px solid #6366f1;
  padding: 7px 12px;
  font-size: .78rem;
  font-weight: 700;
  letter-spacing: .06em;
  color: #a5b4fc;
  text-transform: uppercase;
  margin: 18px 0 6px;
  border-radius: 0 6px 6px 0;
}
.phieu-table { width: 100%; border-collapse: collapse; margin-bottom: 8px; font-size: .84rem }
.phieu-table th {
  background: rgba(99,102,241,.18);
  color: #c7d2fe;
  font-weight: 700;
  padding: 7px 10px;
  text-align: left;
  border: 1px solid rgba(99,102,241,.25);
  font-size: .78rem;
  letter-spacing: .04em;
}
.phieu-table td {
  padding: 7px 10px;
  border: 1px solid rgba(99,102,241,.15);
  vertical-align: top;
  line-height: 1.55;
}
.phieu-table tr:nth-child(even) td { background: rgba(99,102,241,.04) }
.phieu-table tr:hover td { background: rgba(99,102,241,.09) }
.phieu-label { font-weight: 600; color: #c7d2fe; white-space: nowrap }
.phieu-center { text-align: center }
.phieu-pre { white-space: pre-wrap; line-height: 1.6 }
.phieu-tbc-row td { font-weight: 700; background: rgba(99,102,241,.12) !important; border-top: 2px solid rgba(99,102,241,.4) }
.phieu-kpi { font-weight: 800; font-size: .95rem }
.kpi-green { color: #34d399 }
.kpi-amber { color: #fbbf24 }
.kpi-red   { color: #f87171 }
.phieu-section-row td { background: rgba(99,102,241,.08) !important }
.phieu-subsection { font-size: .78rem; letter-spacing: .04em; color: #a5b4fc; padding: 6px 10px }
.phieu-selected { background: rgba(16,185,129,.12) !important }
.phieu-checkbox { margin-right: 6px; font-size: 1rem }
.phieu-note-box { margin-top: 16px; padding: 12px 16px; border: 1px solid rgba(251,191,36,.3); border-radius: 10px; background: rgba(251,191,36,.06) }
.phieu-note-label { font-size: .78rem; font-weight: 700; color: #fbbf24; margin-bottom: 6px }

/* ── Editable phieu inputs ── */
.pe-input {
  width: 100%; box-sizing: border-box;
  background: rgba(255,255,255,.04);
  border: 1px solid rgba(99,102,241,.2);
  border-radius: 5px;
  color: #e2e8f0;
  font-size: .84rem;
  padding: 4px 7px;
  outline: none;
  transition: border-color .15s, background .15s;
}
.pe-input:focus { border-color: rgba(99,102,241,.6); background: rgba(99,102,241,.08) }
.pe-center { text-align: center }

.pe-textarea {
  width: 100%; box-sizing: border-box;
  background: rgba(255,255,255,.04);
  border: 1px solid rgba(99,102,241,.2);
  border-radius: 5px;
  color: #e2e8f0;
  font-size: .84rem;
  padding: 5px 7px;
  outline: none;
  resize: vertical;
  font-family: inherit;
  line-height: 1.55;
  transition: border-color .15s, background .15s;
}
.pe-textarea:focus { border-color: rgba(99,102,241,.6); background: rgba(99,102,241,.08) }
.pe-handwriting { border-color: rgba(192,132,252,.4); background: rgba(192,132,252,.04) }
.pe-handwriting:focus { border-color: rgba(192,132,252,.7); background: rgba(192,132,252,.08) }

/* HOD textarea — màu amber để phân biệt */
.pe-hod { border-color: rgba(251,191,36,.35); background: rgba(251,191,36,.04) }
.pe-hod:focus { border-color: rgba(251,191,36,.7); background: rgba(251,191,36,.08) }
.pe-hod::placeholder { color: rgba(251,191,36,.5) }
.pe-link-main { font-size:.82rem; color:#60a5fa; font-family:monospace }
.pe-link-main:focus { border-color:rgba(96,165,250,.6); background:rgba(96,165,250,.06) }

/* sp-card: sản phẩm tuần */
.sp-card { border:1px solid rgba(99,102,241,.2); border-radius:10px; padding:10px 12px; margin-bottom:12px; background:rgba(99,102,241,.02) }
.sp-head { display:flex; align-items:center; gap:10px; font-weight:700; color:#818cf8; font-size:.88rem; margin-bottom:4px }
.sp-kpi { padding:2px 8px; border-radius:20px; font-size:.8rem; font-weight:700 }
.kpi-green { background:rgba(5,150,105,.15); color:#34d399 }
.kpi-amber { background:rgba(245,158,11,.15); color:#fbbf24 }
.kpi-red   { background:rgba(239,68,68,.15);  color:#f87171 }

/* Analysis */
.de-xuat-badge { display:inline-block; padding:6px 16px; border-radius:20px; font-weight:700; font-size:.9rem; margin-bottom:12px }
.de-xuat-badge.green { background:rgba(5,150,105,.2); color:#34d399 }
.de-xuat-badge.amber { background:rgba(245,158,11,.2); color:#fbbf24 }
.de-xuat-badge.red   { background:rgba(239,68,68,.2);  color:#f87171 }
.tong-quan { color:#94a3b8; margin-bottom:16px; line-height:1.6 }
.phan-tich-row { border-bottom:1px solid rgba(255,255,255,.06); padding:10px 0 }
.tc-label { font-weight:700; color:#818cf8; font-size:.8rem }
.tc-danh-gia { float:right; padding:1px 8px; border-radius:10px; font-size:.78rem; font-weight:700 }
.tc-danh-gia.green { background:rgba(5,150,105,.15); color:#34d399 }
.tc-danh-gia.amber { background:rgba(245,158,11,.15); color:#fbbf24 }
.tc-nhan-xet { color:#94a3b8; font-size:.83rem; margin-top:4px; clear:both }
.no-analysis { color:#64748b; font-size:.88rem; padding:20px; text-align:center }



/* Dirty bar */
.phieu-dirty-bar {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 14px; margin-bottom: 12px;
  background: rgba(251,191,36,.1); border: 1px solid rgba(251,191,36,.3);
  border-radius: 8px; font-size: .82rem; color: #fbbf24; font-weight: 600;
}
.phieu-save-btn {
  padding: 4px 14px; border-radius: 6px; border: none; cursor: pointer;
  background: #6366f1; color: #fff; font-size: .8rem; font-weight: 700;
}
.phieu-save-btn:hover { background: #4f46e5 }
.phieu-reset-btn {
  padding: 4px 10px; border-radius: 6px; border: 1px solid rgba(255,255,255,.15); cursor: pointer;
  background: transparent; color: #94a3b8; font-size: .8rem;
}
.phieu-hw-note {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 12px; margin-bottom: 10px;
  background: rgba(192,132,252,.08); border: 1px solid rgba(192,132,252,.25);
  border-radius: 7px; font-size: .78rem; color: #c084fc; font-weight: 600;
}
.ci-ok   { background: rgba(5,150,105,.12); color: #34d399 }
.ci-fail { background: rgba(220,38,38,.12);  color: #f87171 }

.spinner { width: 15px; height: 15px; border: 2px solid rgba(255,255,255,.3); border-top-color: #fff; border-radius: 50%; animation: spin .6s linear infinite }
@keyframes spin { to { transform: rotate(360deg) } }

.sb-err { font-size: .78rem; color: #f87171; margin: 4px 0 }
.sb-err-box { margin-top: 10px; padding: 10px 12px; border-radius: 8px; background: rgba(239,68,68,.08); border: 1px solid rgba(239,68,68,.2); color: #f87171; font-size: .82rem; line-height: 1.5 }
.sb-ocr-note { font-size: .75rem; color: #64748b; background: rgba(99,102,241,.06); border-radius: 8px; padding: 8px 10px; margin-bottom: 10px }
.ocr-method-label { font-size: .68rem; color: #64748b; margin-bottom: 6px; font-weight: 600 }
.ocr-pills { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 6px }
.ocr-pill { font-size: .68rem; font-weight: 700; padding: 2px 8px; border-radius: 99px }
.pill-api     { background: rgba(16,185,129,.15); color: #34d399 }
.pill-vision  { background: rgba(139,92,246,.15);  color: #a78bfa }
.pill-docling { background: rgba(59,130,246,.15);  color: #60a5fa }
.pill-direct  { background: rgba(245,158,11,.15);  color: #fbbf24 }
.hw-badge { font-size: .72rem; font-weight: 700; color: #c084fc; background: rgba(192,132,252,.1); border: 1px solid rgba(192,132,252,.2); border-radius: 6px; padding: 3px 8px; display: inline-block }
.sb-deadline-warn { background: rgba(245,158,11,.1); border: 1px solid rgba(245,158,11,.3); border-radius: 8px; padding: 8px 12px; font-size: .8rem; font-weight: 600; color: #fbbf24; margin-bottom: 10px }
.sb-badge { padding: 10px 14px; border-radius: 10px; display: flex; align-items: center; gap: 10px; margin-bottom: 12px }
.badge-green { background: rgba(5,150,105,.1); border: 1px solid rgba(5,150,105,.3) }
.badge-amber { background: rgba(245,158,11,.1); border: 1px solid rgba(245,158,11,.3) }
.badge-red { background: rgba(220,38,38,.1); border: 1px solid rgba(220,38,38,.3) }
.badge-icon { width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 800 }
.badge-green .badge-icon { background: rgba(5,150,105,.2); color: #34d399 }
.badge-amber .badge-icon { background: rgba(245,158,11,.2); color: #fbbf24 }
.badge-red .badge-icon { background: rgba(220,38,38,.2); color: #f87171 }
.badge-text { font-size: .82rem; font-weight: 700 }

/* ── MAIN PANEL ── */
.result-panel { flex: 1; overflow-y: auto; display: flex; flex-direction: column }

/* ── WORD EDITOR (Step 2) ── */
.word-editor-wrap { flex: 1; display: flex; flex-direction: column; overflow: hidden }

.we-toolbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 16px; border-bottom: 1px solid rgba(255,255,255,.06);
  background: rgba(15,15,30,.6); backdrop-filter: blur(10px);
  position: sticky; top: 0; z-index: 10; flex-shrink: 0;
}
.we-toolbar-left { display: flex; align-items: center; gap: 10px }
.we-doc-name { font-size: .8rem; font-weight: 600; color: #94a3b8; max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap }
.we-badge { display: flex; gap: 6px; font-size: .72rem; color: #64748b }
.hw-badge-inline { color: #c084fc; font-weight: 700 }
.we-toolbar-actions { display: flex; align-items: center; gap: 4px }
.we-btn { padding: 4px 10px; border: 1px solid rgba(255,255,255,.08); border-radius: 6px; background: transparent; color: #94a3b8; cursor: pointer; font-size: .82rem; transition: all .15s }
.we-btn:hover { background: rgba(99,102,241,.15); color: #e2e8f0; border-color: rgba(99,102,241,.3) }
.we-sep { width: 1px; height: 18px; background: rgba(255,255,255,.1); margin: 0 4px }

/* A4 scroll area */
.we-scroll { flex: 1; overflow-y: auto; background: #1a1a2e; padding: 32px 24px }

/* A4 page */
.we-page {
  max-width: 860px; margin: 0 auto;
  background: #12121e;
  border: 1px solid rgba(99,102,241,.15);
  border-radius: 8px;
  box-shadow: 0 20px 60px rgba(0,0,0,.5);
  padding: 48px 56px;
  font-family: 'Times New Roman', Times, serif;
}

/* Doc header stamp */
.we-header-stamp {
  display: flex; align-items: center; gap: 16px;
  padding-bottom: 20px; margin-bottom: 24px;
  border-bottom: 3px solid rgba(99,102,241,.4);
}
.we-logo { height: 40px; object-fit: contain }
.we-doc-title { font-size: 1rem; font-weight: 800; color: #e2e8f0; letter-spacing: .04em }
.we-doc-sub { font-size: .75rem; color: #64748b; margin-top: 2px }

/* Editable content area */
.we-body {
  outline: none;
  font-size: .9rem; line-height: 1.8; color: #e2e8f0;
  min-height: 500px;
  caret-color: #818cf8;
}
.we-body:focus { outline: none }

/* Headings */
.we-body h1 { font-size: 1.1rem; font-weight: 800; text-align: center; margin: 20px 0 14px; color: #f1f5f9; text-transform: uppercase; letter-spacing: .06em }
.we-body h2 { font-size: .95rem; font-weight: 700; margin: 18px 0 10px; color: #c7d2fe; border-bottom: 1px solid rgba(99,102,241,.2); padding-bottom: 4px }
.we-body h3 { font-size: .88rem; font-weight: 700; margin: 14px 0 8px; color: #a5b4fc }
.we-body p { margin: 6px 0 }
.we-body ul, .we-body ol { margin: 6px 0 6px 20px; padding: 0 }
.we-body li { margin: 3px 0 }
.we-body hr { border: none; border-top: 1px solid rgba(99,102,241,.2); margin: 20px 0 }
.we-body strong { font-weight: 700; color: #f1f5f9 }

/* Word-style table */
.dp-body .word-table th {
  background: rgba(99,102,241,.12); color: inherit;
  padding: 6px 10px; text-align: left; font-weight: 700;
  border: 1px solid rgba(255,255,255,.1); font-size: .75rem;
}
.dp-body .word-table td {
  padding: 5px 10px; border: 1px solid rgba(255,255,255,.08);
  vertical-align: top;
}
.dp-body .word-table tr:nth-child(even) td { background: rgba(99,102,241,.04) }
.dp-body .word-table strong { font-weight: 700; }

/* Handwriting highlight */
.hw-tag { font-size: .7rem; font-weight: 800; color: #c084fc; background: rgba(192,132,252,.15); padding: 1px 6px; border-radius: 4px; white-space: nowrap }

/* Light theme */
:global(body.theme-light) .doc-preview { background: #fafafa; border-right-color: #e2e8f0 }
:global(body.theme-light) .dp-header { background: rgba(248,250,252,.9); border-bottom-color: #e2e8f0 }
:global(body.theme-light) .dp-body .word-table th { background: #e8eaf6; color: #1e293b; border-color: #c5cae9 }
:global(body.theme-light) .dp-body .word-table td { border-color: #e2e8f0 }
:global(body.theme-light) .dp-body .word-table tr:nth-child(even) td { background: #f1f5f9 }

.form-panel { flex: 1; overflow-y: auto }
.welcome { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; padding: 40px; text-align: center }
.welcome-icon { margin-bottom: 20px }
.welcome h1 { font-size: 1.4rem; font-weight: 800; margin-bottom: 12px }
.welcome p { max-width: 500px; color: #94a3b8; line-height: 1.6; font-size: .92rem }
.welcome-features { display: flex; gap: 16px; margin-top: 28px; flex-wrap: wrap; justify-content: center }
.wf { display: flex; align-items: center; gap: 8px; padding: 10px 16px; border-radius: 10px; background: rgba(99,102,241,.06); border: 1px solid rgba(99,102,241,.12); font-size: .84rem; color: #64748b; font-weight: 500 }
.wf-icon { font-size: 1.2rem }

.loading-screen { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; gap: 16px }
.loading-spinner { width: 40px; height: 40px; border: 3px solid rgba(99,102,241,.2); border-top-color: #6366f1; border-radius: 50%; animation: spin 1s linear infinite }
.loading-screen p { font-weight: 600 }
.loading-sub { font-weight: 400 !important; font-size: .84rem; color: #64748b }

/* ── FORM ── */
.form-panel { flex: 1; overflow-y: auto; padding: 24px; max-width: 800px }
.fp-header { margin-bottom: 20px }
.fp-header h2 { font-size: 1.1rem; font-weight: 700; margin-bottom: 6px }
.fp-header p { font-size: .88rem; color: #64748b; line-height: 1.5 }

.deadline-alert { display: flex; align-items: center; gap: 8px; padding: 10px 14px; border-radius: 10px; font-weight: 600; font-size: .86rem; margin-bottom: 16px }
.dl-expired { background: rgba(220,38,38,.1); border: 1px solid rgba(220,38,38,.3); color: #f87171 }
.dl-today   { background: rgba(220,38,38,.1); border: 1px solid rgba(220,38,38,.3); color: #f87171 }
.dl-urgent  { background: rgba(245,158,11,.1); border: 1px solid rgba(245,158,11,.3); color: #fbbf24 }
.dl-soon    { background: rgba(99,102,241,.08); border: 1px solid rgba(99,102,241,.2); color: #818cf8 }

.sf-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px }
.sf-field { display: flex; flex-direction: column; gap: 5px }
.sf-field.sf-full { grid-column: 1 / -1 }
.sf-label { font-size: .78rem; font-weight: 600; color: #94a3b8; display: flex; align-items: center; gap: 6px }
.sf-conf-warn { font-size: .7rem; font-weight: 700; padding: 1px 6px; border-radius: 4px; background: rgba(245,158,11,.15); color: #fbbf24 }
.sf-input { padding: 8px 12px; border-radius: 8px; border: 1px solid transparent; background: rgba(255,255,255,.06); color: inherit; font-size: .88rem; font-family: inherit; outline: none; transition: border-color .2s }
.sf-input:focus { border-color: rgba(99,102,241,.5) }
.sfi-textarea { resize: vertical; min-height: 72px; line-height: 1.6 }
.sf-low-conf .sf-input { border-color: rgba(245,158,11,.4) !important; background: rgba(245,158,11,.04) }

/* ── RESULTS ── */
.results-scroll { padding: 16px 24px; width: 100%; box-sizing: border-box }
.result-card { border: 1px solid transparent; border-radius: 14px; margin-bottom: 16px; overflow: hidden }
.rc-overview { padding: 20px 24px }
.rc-green { border-color: rgba(5,150,105,.3) !important }
.rc-amber { border-color: rgba(245,158,11,.3) !important }
.rc-red   { border-color: rgba(220,38,38,.3) !important }

.rc-badge-row { display: flex; align-items: center; gap: 12px; margin-bottom: 12px }
.rc-badge-big { font-size: .95rem; font-weight: 800; padding: 6px 16px; border-radius: 8px; background: rgba(99,102,241,.1); color: #818cf8 }
.rc-deadline-chip { font-size: .8rem; font-weight: 700; padding: 4px 12px; border-radius: 99px; background: rgba(245,158,11,.15); color: #fbbf24 }
.rc-summary { line-height: 1.7; font-size: .92rem; margin-bottom: 16px }

.rc-nv-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 8px }
.rc-nv-item { display: flex; flex-direction: column; gap: 2px }
.rc-nv-label { font-size: .7rem; color: #64748b; font-weight: 600 }
.rc-nv-val { font-size: .85rem; font-weight: 700 }

.rc-header { padding: 14px 20px; cursor: pointer; display: flex; align-items: center; gap: 10px; font-weight: 600; font-size: .9rem; transition: background .2s; user-select: none }
.rc-h-blue { color: #60a5fa }
.rc-h-warn { color: #fbbf24 }
.rc-h-green { color: #4ade80 }
.rc-arrow { font-size: 1.2rem; margin-left: auto; transition: transform .2s; color: #64748b }
.rc-arrow.open { transform: rotate(90deg) }
.rc-body { padding: 0 20px 16px }

.criteria-item { padding: 12px 0; border-bottom: 1px solid rgba(255,255,255,.04) }
.criteria-item:last-child { border-bottom: none }
.ci-header { display: flex; align-items: center; gap: 10px; margin-bottom: 8px }
.ci-num { width: 24px; height: 24px; border-radius: 50%; background: rgba(99,102,241,.15); color: #818cf8; display: flex; align-items: center; justify-content: center; font-size: .8rem; font-weight: 800; flex-shrink: 0 }
.ci-name { flex: 1; font-weight: 600; font-size: .9rem }
.ci-badge { font-size: .75rem; font-weight: 700; padding: 2px 10px; border-radius: 99px }
.badge-ok { background: rgba(5,150,105,.12); color: #34d399 }
.badge-warn { background: rgba(245,158,11,.12); color: #fbbf24 }
.badge-miss { background: rgba(220,38,38,.12); color: #f87171 }
.ci-nhanxet { font-size: .87rem; line-height: 1.65; color: #94a3b8; padding-left: 34px }

.warn-item { padding: 7px 0; font-size: .88rem; color: #fbbf24; display: flex; gap: 8px }
.warn-dot { flex-shrink: 0 }

.task-item { padding: 8px 0; display: flex; align-items: flex-start; gap: 10px; font-size: .88rem }
.task-num { width: 22px; height: 22px; border-radius: 50%; background: rgba(5,150,105,.15); color: #34d399; display: flex; align-items: center; justify-content: center; font-size: .75rem; font-weight: 800; flex-shrink: 0 }

.sb-xml-hint { font-size: .75rem; color: #64748b; background: rgba(99,102,241,.06); border-radius: 8px; padding: 7px 10px; margin-bottom: 10px; line-height: 1.5 }

/* ── XML EDITOR (Step 2) ── */
.xml-editor-wrap { flex: 1; display: flex; flex-direction: column; overflow: hidden }

.xe-toolbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 16px; border-bottom: 1px solid rgba(99,102,241,.12);
  background: rgba(15,15,30,.7); backdrop-filter: blur(10px);
  flex-shrink: 0;
}
.xe-toolbar-left { display: flex; align-items: center; gap: 10px }
.xe-doc-name {
  display: flex; align-items: center; gap: 6px;
  font-size: .8rem; font-weight: 700; color: #94a3b8;
  font-family: 'Fira Code', 'JetBrains Mono', monospace;
}
.xe-badge {
  font-size: .68rem; font-weight: 700; padding: 2px 8px; border-radius: 99px;
  background: rgba(99,102,241,.12); color: #818cf8;
}
.xe-badge-hw { background: rgba(192,132,252,.12); color: #c084fc }
.xe-toolbar-actions { display: flex; align-items: center; gap: 6px }
.xe-btn {
  display: flex; align-items: center; gap: 5px;
  padding: 5px 11px; border: 1px solid rgba(99,102,241,.25); border-radius: 7px;
  background: rgba(99,102,241,.07); color: #818cf8;
  font-size: .76rem; font-weight: 600; cursor: pointer; transition: all .18s;
}
.xe-btn:hover { background: rgba(99,102,241,.18); border-color: rgba(99,102,241,.5) }
.xe-btn.copied { background: rgba(34,197,94,.1); border-color: rgba(34,197,94,.4); color: #4ade80 }

.xe-scroll { flex: 1; overflow: hidden; display: flex; padding: 0 }
.xe-textarea {
  flex: 1;
  width: 100%; height: 100%;
  resize: none;
  background: #0a0a18;
  color: #e2e8f0;
  font-family: 'Fira Code', 'JetBrains Mono', 'Consolas', monospace;
  font-size: .82rem;
  line-height: 1.7;
  padding: 24px 28px;
  border: none;
  outline: none;
  tab-size: 2;
  caret-color: #818cf8;
}
.xe-textarea::selection { background: rgba(99,102,241,.3) }
.result-tabs {
  display: flex; gap: 4px; padding: 0 24px 0; margin-bottom: 0;
  border-bottom: 1px solid rgba(99,102,241,.15);
  position: sticky; top: 0; z-index: 5;
  background: var(--bg, #0d0d1a);
  backdrop-filter: blur(12px);
}
.rtab {
  padding: 10px 16px 9px; border: none; background: transparent;
  color: #64748b; font-size: .82rem; font-weight: 600; cursor: pointer;
  border-bottom: 2px solid transparent; margin-bottom: -1px;
  transition: all .2s; display: flex; align-items: center; gap: 6px;
  position: relative;
}
.rtab:hover { color: #818cf8 }
.rtab__active { color: #818cf8; border-bottom-color: #6366f1 }
.rtab:disabled { opacity: .4; cursor: not-allowed }
.rtab-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: #4ade80; display: inline-block;
  animation: pulse-dot 2s ease-in-out infinite;
}
@keyframes pulse-dot {
  0%,100% { opacity: 1 }
  50%      { opacity: .4 }
}

/* ── XML PANEL ── */
.xml-panel {
  display: flex; flex-direction: column;
  background: rgba(10,10,25,.8);
  border: 1px solid rgba(99,102,241,.15);
  border-radius: 12px;
  margin: 20px 24px;
  overflow: hidden;
}
.xml-toolbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 16px; border-bottom: 1px solid rgba(99,102,241,.12);
  background: rgba(99,102,241,.06);
}
.xml-title {
  display: flex; align-items: center; gap: 8px;
  font-size: .8rem; font-weight: 700; color: #94a3b8;
  font-family: 'Fira Code', 'JetBrains Mono', monospace;
}
.xml-actions { display: flex; gap: 8px }
.xml-btn {
  display: flex; align-items: center; gap: 6px;
  padding: 5px 12px; border: 1px solid rgba(99,102,241,.3); border-radius: 7px;
  background: rgba(99,102,241,.08); color: #818cf8;
  font-size: .77rem; font-weight: 600; cursor: pointer; transition: all .18s;
}
.xml-btn:hover { background: rgba(99,102,241,.18); border-color: rgba(99,102,241,.5) }
.xml-btn.copied { background: rgba(34,197,94,.1); border-color: rgba(34,197,94,.4); color: #4ade80 }
.xml-code-wrap { overflow: auto; max-height: 520px; padding: 20px 24px }
.xml-code {
  margin: 0; font-family: 'Fira Code', 'JetBrains Mono', 'Consolas', monospace;
  font-size: .8rem; line-height: 1.75; color: #cbd5e1;
  white-space: pre; tab-size: 2;
}
/* Syntax colors */
:deep(.xml-decl)    { color: #64748b; font-style: italic }
:deep(.xml-bracket) { color: #60a5fa }
:deep(.xml-tag)     { color: #c084fc; font-weight: 600 }
:deep(.xml-attr)    { color: #fbbf24 }
:deep(.xml-eq)      { color: #94a3b8 }
:deep(.xml-attrval) { color: #34d399 }
:deep(.xml-val)     { color: #f1f5f9 }

/* Light theme overrides */
:global(body.theme-light) .sf-input { background: #f8fafc; border-color: #e2e8f0; color: #111827 }
:global(body.theme-light) .sf-input:focus { border-color: #6366f1; background: #fff }
:global(body.theme-light) .result-card { background: #fff; border-color: #e2e8f0 }
:global(body.theme-light) .rc-body { border-top-color: #e2e8f0 }
:global(body.theme-light) .criteria-item { border-bottom-color: #e2e8f0 }
:global(body.theme-light) .ci-nhanxet { color: #475569 }
:global(body.theme-light) .rc-summary { color: #334155 }
</style>
