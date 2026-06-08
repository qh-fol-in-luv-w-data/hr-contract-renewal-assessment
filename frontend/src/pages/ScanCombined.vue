<template>
  <div class="app-layout">
    <!-- SIDEBAR -->
    <aside class="sidebar">
      <div class="sb-top">
        <router-link to="/thu-viec" class="sb-back" title="Về Phiếu Thử Việc">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M19 12H5m7-7l-7 7 7 7"/></svg>
        </router-link>
        <div class="sb-logo">
          <div class="sb-logo-mark">🔍</div>
          <div>
            <div class="sb-name">Scan & OCR</div>
            <div class="sb-org">CT Group · 2AS</div>
          </div>
        </div>
      </div>

      <div class="sb-body">
        <!-- Upload section -->
        <div v-if="step === 1" class="sb-section">
          <div class="sb-section-title">📂 Upload 2 file để scan</div>

          <!-- Phiếu -->
          <div class="upl-group-label">📋 Phiếu đánh giá thử việc</div>
          <div class="sb-upload-card" :class="{filled: phieuFile, err: !phieuFile && tried}"
            @dragover.prevent @drop.prevent="onDrop($event,'phieu')" @click="$refs.rPhieu.click()">
            <input ref="rPhieu" type="file" accept=".pdf,.docx,.html,.htm" hidden
              @change="e => phieuFile = e.target.files[0] || null"/>
            <div class="upc-icon">{{ phieuFile ? '📄' : '🗂️' }}</div>
            <div class="upc-info" :title="phieuFile ? phieuFile.name : ''">
              <div class="upc-val" :class="phieuFile ? 'ok' : 'empty'">
                {{ phieuFile ? phieuFile.name : 'PDF / DOCX / HTML' }}
              </div>
            </div>
            <button v-if="phieuFile" class="upc-rm" @click.stop="phieuFile=null">✕</button>
          </div>

          <!-- SXKD -->
          <div class="upl-group-label" style="margin-top:10px">📊 Kế hoạch SXKD tháng</div>
          <div class="sb-upload-card" :class="{filled: sxkdFile, err: !sxkdFile && tried}"
            @dragover.prevent @drop.prevent="onDrop($event,'sxkd')" @click="$refs.rSXKD.click()">
            <input ref="rSXKD" type="file" accept=".pdf" hidden
              @change="e => sxkdFile = e.target.files[0] || null"/>
            <div class="upc-icon">{{ sxkdFile ? '📄' : '🗂️' }}</div>
            <div class="upc-info" :title="sxkdFile ? sxkdFile.name : ''">
              <div class="upc-val" :class="sxkdFile ? 'ok' : 'empty'">
                {{ sxkdFile ? sxkdFile.name : 'PDF scan từ CamScanner' }}
              </div>
            </div>
            <button v-if="sxkdFile" class="upc-rm" @click.stop="sxkdFile=null">✕</button>
          </div>

          <p v-if="tried && !phieuFile && !sxkdFile" class="sb-err">Cần ít nhất 1 file</p>

          <button class="sb-btn-primary" :disabled="loading || (!phieuFile && !sxkdFile)" @click="doScan">
            <span v-if="loading" class="spinner"></span>
            <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
            {{ loading ? loadingMsg : 'Quét cả 2 file' }}
          </button>

          <div v-if="error" class="sb-err-box">{{ error }}</div>
        </div>

        <!-- Results summary -->
        <div v-if="step === 2" class="sb-section">
          <div class="sb-section-title">📊 Kết quả scan</div>

          <!-- Phiếu summary -->
          <div v-if="phieuResult" class="sb-result-block">
            <div class="srb-title">📋 Phiếu đánh giá</div>
            <div class="srb-badge" :class="badgeCls">{{ phieuResult.de_xuat || phieuResult.mau_de_xuat || '...' }}</div>
            <button v-if="scanSessionId" class="sb-btn-docx" :disabled="loadingDocx" @click="downloadDocx">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
              {{ loadingDocx ? 'Đang tạo...' : 'Tải DOCX' }}
            </button>
            <!-- Nút xuất PDF báo cáo 7 tiêu chí 2AS -->
            <button v-if="scanSessionId && phieuResult" class="sb-btn-pdf" :disabled="loadingPdf" @click="downloadPdf">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
              {{ loadingPdf ? 'Đang tạo PDF...' : '📊 Xuất PDF Báo cáo' }}
            </button>
            <div v-if="pdfError" class="sb-err">{{ pdfError }}</div>
          </div>

          <!-- SXKD summary -->
          <div v-if="months.length" class="sb-result-block sxkd-block">
            <div class="srb-title">📊 KH SXKD</div>
            <div v-for="(m,i) in months" :key="i" class="srb-month">
              <span class="srb-month-label">{{ extractMonthLabel(m.tieu_de) }}</span>
              <span class="srb-kq">{{ m.ty_le_dat_ket_qua || '—' }}</span>
              <button class="srb-dl-btn" :disabled="loadingExcel===i" @click="downloadExcel(i)">
                {{ loadingExcel===i ? '...' : '⬇' }}
              </button>
            </div>
          </div>

          <!-- → Gửi vào Đánh giá -->
          <div v-if="phieuResult || months.length" style="margin-top:10px">
            <button class="sb-btn-eval" :disabled="loadingEval" @click="sendToEval">
              <span v-if="loadingEval" class="spinner"></span>
              <svg v-else width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
              {{ loadingEval ? 'Đang phân tích...' : '→ Đánh giá 2AS (7 tiêu chí)' }}
            </button>
            <div v-if="evalError" class="sb-err">{{ evalError }}</div>
          </div>

          <button class="sb-btn-ghost" @click="resetAll">↩ Scan lại</button>
        </div>
      </div>
    </aside>

    <!-- MAIN PANEL -->
    <main class="result-panel">

      <!-- Welcome -->
      <div v-if="step === 1 && !loading" class="welcome">
        <div class="welcome-icon">
          <svg width="60" height="60" viewBox="0 0 60 60" fill="none">
            <rect width="60" height="60" rx="18" fill="url(#wg)"/>
            <text x="30" y="42" text-anchor="middle" font-size="30">🔍</text>
            <defs><linearGradient id="wg" x1="0" y1="0" x2="60" y2="60">
              <stop stop-color="#6366f1"/><stop offset="1" stop-color="#10b981"/>
            </linearGradient></defs>
          </svg>
        </div>
        <h1>Scan Phiếu & SXKD cùng lúc</h1>
        <p>Upload 2 file PDF cùng lúc. AI sẽ đọc đồng thời, kết quả hiển thị trải dọc — sửa trực tiếp, tải về ngay.</p>
        <div class="welcome-features">
          <div class="wf"><div class="wf-icon">📋</div><div>Phiếu thử việc → Word</div></div>
          <div class="wf"><div class="wf-icon">📊</div><div>KH SXKD → Excel</div></div>
          <div class="wf"><div class="wf-icon">🤖</div><div>GPT-4o Vision</div></div>
          <div class="wf"><div class="wf-icon">✏️</div><div>Sửa trực tiếp</div></div>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="loading-screen">
        <div class="loading-rings">
          <div class="ring ring-1"></div>
          <div class="ring ring-2"></div>
          <div class="ring-center">🤖</div>
        </div>
        <p class="loading-msg">{{ loadingMsg }}</p>
        <div class="loading-tasks">
          <div class="lt" :class="phieuDone ? 'lt-done' : (loading ? 'lt-running' : '')">
            <span class="lt-icon">{{ phieuDone ? '✅' : (loading && phieuFile ? '⏳' : '⬜') }}</span>
            Scan phiếu đánh giá
          </div>
          <div class="lt" :class="sxkdDone ? 'lt-done' : (loading ? 'lt-running' : '')">
            <span class="lt-icon">{{ sxkdDone ? '✅' : (loading && sxkdFile ? '⏳' : '⬜') }}</span>
            Scan KH SXKD
          </div>
        </div>
      </div>

      <!-- Results -->
      <div v-if="step === 2 && !loading" class="results-scroll">

        <!-- Tab Switcher -->
        <div v-if="phieuResult && months.length" class="scan-tabs">
          <button class="scan-tab" :class="{active: scanTab==='phieu'}" @click="scanTab='phieu'">
            📋 Phiếu Đánh Giá
          </button>
          <button class="scan-tab" :class="{active: scanTab==='sxkd'}" @click="scanTab='sxkd'">
            📊 KH SXKD
          </button>
        </div>

        <!-- ══ PHIẾU ĐÁNH GIÁ ══════════════════════════════════════ -->
        <template v-if="phieuResult && (scanTab==='phieu' || !months.length)">
          <div class="section-sep">
            <div class="sep-line"></div>
            <div class="sep-label sep-phieu">📋 Phiếu Đánh Giá Thử Việc</div>
            <div class="sep-line"></div>
          </div>

          <div class="phieu-doc">
            <div class="phieu-title">PHIẾU ĐÁNH GIÁ HOÀN THÀNH THỬ VIỆC</div>
            <div class="phieu-subtitle">CT Group – CTG-GO-NLCD-QT16-BM01</div>

            <div v-if="phieuDirty" class="dirty-bar">
              ⚠️ Có thay đổi chưa lưu
              <button class="db-save" @click="savePhieu">💾 Lưu</button>
              <button class="db-cancel" @click="cancelPhieu">✕ Huỷ</button>
            </div>

            <!-- A. Thông tin chung -->
            <div class="phieu-section-head">A. THÔNG TIN CHUNG</div>
            <table class="phieu-table">
              <thead><tr>
                <th style="width:28%">Nội dung</th>
                <th>CBNV được đánh giá</th>
                <th style="width:26%">HOD / Người được UQ đánh giá</th>
                <th style="width:7%">RTD</th><th style="width:7%">GAD</th>
              </tr></thead>
              <tbody>
                <tr><td class="pl">Họ và tên</td><td><input class="pe-input" v-model="ef.ho_ten" @input="phieuDirty=true"/></td><td><input class="pe-input pe-hod" v-model="ef.ten_hod" placeholder="Tên HOD"/></td><td></td><td></td></tr>
                <tr><td class="pl">Mã NV</td><td><input class="pe-input" v-model="ef.ma_nhan_su" @input="phieuDirty=true"/></td><td><input class="pe-input pe-hod" v-model="ef.ma_hod" placeholder="Mã HOD"/></td><td></td><td></td></tr>
                <tr><td class="pl">Chức danh</td><td><input class="pe-input" v-model="ef.chuc_danh" @input="phieuDirty=true"/></td><td><input class="pe-input pe-hod" v-model="ef.chuc_danh_hod" placeholder="Chức danh HOD"/></td><td></td><td></td></tr>
                <tr><td class="pl">Đơn vị</td><td><input class="pe-input" v-model="ef.phong_ban" @input="phieuDirty=true"/></td><td><input class="pe-input pe-hod" v-model="ef.don_vi_hod" placeholder="Đơn vị HOD"/></td><td></td><td></td></tr>
                <tr><td class="pl">Ngày nhận việc</td><td><input class="pe-input" v-model="ef.ngay_nhan_viec" @input="phieuDirty=true"/></td><td></td><td></td><td></td></tr>
                <tr><td class="pl">Ngày hết hạn TV</td><td><input class="pe-input" v-model="ef.ngay_het_han" @input="phieuDirty=true"/></td><td></td><td></td><td></td></tr>
              </tbody>
            </table>

            <!-- B. Phần I – Nhận xét chung -->
            <div class="phieu-section-head">B. PHẦN I: NHẬN XÉT CHUNG</div>
            <table class="phieu-table">
              <thead><tr>
                <th style="width:30px">STT</th><th style="width:26%">Nội dung</th>
                <th>Ứng viên tự đánh giá</th><th style="width:22%">HOD đánh giá ✍</th>
              </tr></thead>
              <tbody>
                <tr v-for="r in nhanXetRows" :key="'nx'+r.stt">
                  <td class="pc">{{ r.stt }}</td>
                  <td class="pl" style="white-space:normal;font-size:.8rem">{{ r.cau_hoi }}</td>
                  <td><textarea class="pe-ta" v-model="ef[r.nvKey]" rows="3" @input="phieuDirty=true"></textarea></td>
                  <td><textarea class="pe-ta pe-hod" v-model="ef[r.hodKey]" rows="3" placeholder="HOD..."></textarea></td>
                </tr>
              </tbody>
            </table>

            <!-- Phần II – KPI -->
            <div class="phieu-section-head">PHẦN II: KẾT QUẢ KPI</div>
            <table class="phieu-table">
              <thead><tr><th>Tuần</th><th style="width:90px">% KPI (NV)</th></tr></thead>
              <tbody>
                <tr v-for="i in nTuan" :key="'kpi'+i">
                  <td class="pl">Tuần thứ {{ i }}</td>
                  <td><input class="pe-input" style="text-align:center" :value="ef[`kpi_tuan_${i}_ty_le`]" @input="ef[`kpi_tuan_${i}_ty_le`]=$event.target.value;phieuDirty=true"/></td>
                </tr>
                <tr style="background:rgba(99,102,241,.06)">
                  <td class="pl" style="font-weight:700">TBC KPI (bình quân {{ nTuan }} tuần)</td>
                  <td><input class="pe-input" style="text-align:center;font-weight:700" v-model="ef.diem_tbc_kpi_nv" @input="phieuDirty=true"/></td>
                </tr>
                <tr style="background:rgba(251,191,36,.06)">
                  <td class="pl" style="color:#fbbf24">↳ HOD ghi điểm TBC</td>
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
                <th style="width:110px">HOD nhận xét <small style="color:#fbbf24">✍</small></th>
              </tr></thead>
              <tbody>
                <tr v-for="i in nNhiemVu" :key="'nv'+i">
                  <td class="pc pl">{{ i }}</td>
                  <td><textarea class="pe-ta" :value="ef[`nhiem_vu_${i}_noi_dung`]" @input="ef[`nhiem_vu_${i}_noi_dung`]=$event.target.value;phieuDirty=true" rows="3" placeholder="Nội dung nhiệm vụ..."></textarea></td>
                  <td><textarea class="pe-ta" :value="ef[`nhiem_vu_${i}_ket_qua`]" @input="ef[`nhiem_vu_${i}_ket_qua`]=$event.target.value;phieuDirty=true" rows="3" placeholder="Kết quả thực tế..."></textarea></td>
                  <td><input class="pe-input" style="text-align:center;font-weight:700" :value="ef[`nhiem_vu_${i}_ty_le`]" @input="ef[`nhiem_vu_${i}_ty_le`]=$event.target.value;phieuDirty=true" placeholder="90%"/></td>
                  <td><textarea class="pe-ta pe-hod" :value="ef[`nhiem_vu_${i}_hod`]" @input="ef[`nhiem_vu_${i}_hod`]=$event.target.value;phieuDirty=true" rows="3" placeholder="HOD ghi..."></textarea></td>
                </tr>
                <tr style="background:rgba(99,102,241,.06)">
                  <td colspan="3" class="pl" style="font-weight:700;text-align:right">% Hoàn thành chung:</td>
                  <td><input class="pe-input" style="text-align:center;font-weight:800" v-model="ef.ty_le_hoan_thanh_16" @input="phieuDirty=true" placeholder="90%"/></td>
                  <td></td>
                </tr>
              </tbody>
            </table>

            <!-- San pham nghiem thu -->
            <div class="phieu-section-head">2. SẢN PHẨM NGHIỆM THU ({{ nTuan }} TUẦN)</div>
            <div v-for="i in nTuan" :key="'sp'+i" class="sp-card">
              <div class="sp-head">Tuần {{ i }} <span class="sp-kpi" :class="kpiClass(ef[`kpi_sp_tuan_${i}`])">{{ ef[`kpi_sp_tuan_${i}`] || '—' }}</span></div>
              <table class="phieu-table" style="margin-top:6px">
                <tbody>
                  <tr><td class="pl" style="width:24%">Sản phẩm</td><td colspan="2"><textarea class="pe-ta" :value="ef[`san_pham_${i}`]" @input="ef[`san_pham_${i}`]=$event.target.value;phieuDirty=true" rows="2"></textarea></td></tr>
                  <tr><td class="pl">Số lượng file</td><td><input class="pe-input" :value="ef[`so_luong_file_${i}`]" @input="ef[`so_luong_file_${i}`]=$event.target.value" style="width:80px"/></td><td class="pl" style="width:30%">% KPI: <input class="pe-input" :value="ef[`kpi_sp_tuan_${i}`]" @input="ef[`kpi_sp_tuan_${i}`]=$event.target.value" style="width:60px;display:inline"/></td></tr>
                  <tr><td class="pl">🔗 Link đính kèm</td><td colspan="2"><textarea class="pe-ta" style="color:#60a5fa;font-family:monospace;font-size:.78rem" :value="ef[`link_dinh_kem_${i}`]" @input="ef[`link_dinh_kem_${i}`]=$event.target.value" rows="2"></textarea></td></tr>
                </tbody>
              </table>
            </div>

            <!-- Phần III – Hội nhập -->
            <div class="phieu-section-head">PHẦN III: MỨC ĐỘ HỘI NHẬP</div>
            <table class="phieu-table">
              <thead><tr><th style="width:30px">STT</th><th style="width:24%">Câu hỏi</th><th>Ứng viên</th><th style="width:20%">HOD ✍</th></tr></thead>
              <tbody>
                <tr v-for="r in hoiNhapEditRows" :key="'hn'+r.stt">
                  <td class="pc">{{ r.stt }}</td>
                  <td class="pl" style="white-space:normal;font-size:.78rem">{{ r.cau_hoi }}</td>
                  <td><textarea class="pe-ta" v-model="ef[r.nvKey]" rows="2" @input="phieuDirty=true"></textarea></td>
                  <td><textarea v-if="r.hodKey" class="pe-ta pe-hod" v-model="ef[r.hodKey]" rows="2"></textarea></td>
                </tr>
              </tbody>
            </table>

            <!-- C. Kết luận -->
            <div class="phieu-section-head">C. KẾT LUẬN VÀ ĐỀ XUẤT</div>
            <table class="phieu-table">
              <thead><tr><th style="width:35%">Kết luận</th><th>Đề xuất</th><th style="width:18%">Đề nghị phối hợp</th></tr></thead>
              <tbody>
                <tr v-for="row in ketLuanRows" :key="row.id" @click="selectKetLuan(row)" style="cursor:pointer">
                  <td :class="{'phieu-selected': row.selected}">
                    <span class="phieu-checkbox">{{ row.selected ? '☑' : '☐' }}</span>{{ row.ket_luan }}
                  </td>
                  <td>
                    <span v-if="row.id==='dat'">
                      Ký HĐ: <input class="pe-input pe-hod" v-model="ef.de_xuat_ky_hd" @click.stop placeholder="HĐNV 4 tháng..."/>
                      <input class="pe-input" v-model="ef.de_xuat_tang_thu_nhap" @click.stop placeholder="Tăng thu nhập..." style="margin-top:4px"/>
                    </span>
                    <span v-else>{{ row.de_xuat }}</span>
                  </td>
                  <td><textarea class="pe-ta" v-model="ef.de_nghi_phoi_hop" rows="2" @click.stop></textarea></td>
                </tr>
              </tbody>
            </table>

            <!-- Ký xác nhận -->
            <div class="phieu-section-head">KÝ XÁC NHẬN</div>
            <table class="phieu-table">
              <thead><tr><th>Trách nhiệm</th><th>HOD / Người UQ</th><th>Đại diện RTD</th><th>GAD</th><th>Phê duyệt</th></tr></thead>
              <tbody>
                <tr><td class="pl">Ý kiến</td><td><textarea class="pe-ta pe-hod" v-model="ef.y_kien_hod" rows="2"></textarea></td><td><textarea class="pe-ta" v-model="ef.y_kien_rtd" rows="2"></textarea></td><td></td><td class="pl" style="text-align:center">Tổng Giám đốc</td></tr>
                <tr><td class="pl">Ngày ký</td><td><input class="pe-input" v-model="ef.ngay_ky"/></td><td></td><td></td><td></td></tr>
                <tr><td class="pl">Họ tên (ký)</td><td><input class="pe-input pe-hod" v-model="ef.ten_hod_ky" placeholder="Tên HOD ký..."/></td><td></td><td></td><td></td></tr>
              </tbody>
            </table>

            <!-- Download actions -->
            <div class="block-actions">
              <button class="action-btn action-docx" v-if="scanSessionId" :disabled="loadingDocx" @click="downloadDocx">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                {{ loadingDocx ? 'Đang tạo...' : 'Tải DOCX Phiếu' }}
              </button>
            </div>
          </div>

          <!-- ══ ĐÁNH GIÁ 2AS ══════════════════════════════════════════════ -->
          <div v-if="phieuResult" class="eval-panel">
            <div class="eval-header">
              <div class="eval-title">🤖 Đánh giá 2AS</div>
              <div class="eval-badge" :class="`eval-badge-${phieuResult.mau_de_xuat || 'amber'}`">{{ phieuResult.de_xuat || '...' }}</div>
              <button class="btn-reeval" :disabled="loadingReeval" @click="reEvaluate">
                <span v-if="loadingReeval" class="spinner" style="width:12px;height:12px;border-width:2px"></span>
                <span v-else>🔄</span>
                {{ loadingReeval ? 'Đang xử lý...' : 'Đánh giá lại' }}
              </button>
            </div>
            <div v-if="phieuResult.tong_quan" class="eval-tong-quan">{{ phieuResult.tong_quan }}</div>
            <table v-if="phieuResult.phan_tich?.length" class="eval-table">
              <thead><tr><th style="width:24px">#</th><th style="width:30%">Tiêu chí</th><th style="width:18%">Đánh giá</th><th>Nhận xét</th></tr></thead>
              <tbody>
                <tr v-for="(tc, i) in phieuResult.phan_tich" :key="i">
                  <td class="pc">{{ i+1 }}</td>
                  <td class="eval-tc-name">{{ tc.tieu_chi }}</td>
                  <td><span class="eval-dg" :class="evalDgCls(tc.danh_gia)">{{ tc.danh_gia }}</span></td>
                  <td class="eval-nx">{{ tc.nhan_xet }}</td>
                </tr>
              </tbody>
            </table>
            <div v-if="phieuResult.uu_diem?.length" class="eval-section eval-good">
              <div class="eval-sec-title">✅ Ưu điểm</div>
              <ul class="eval-list"><li v-for="(u,i) in phieuResult.uu_diem" :key="i">{{ u }}</li></ul>
            </div>
            <div v-if="phieuResult.canh_bao?.length" class="eval-section eval-warn">
              <div class="eval-sec-title">⚠️ Cảnh báo</div>
              <ul class="eval-list"><li v-for="(c,i) in phieuResult.canh_bao" :key="i">{{ c }}</li></ul>
            </div>
            <div v-if="phieuResult.viec_can_lam?.length" class="eval-section eval-todo">
              <div class="eval-sec-title">📋 Việc cần làm</div>
              <ul class="eval-list">
                <li v-for="(v,i) in phieuResult.viec_can_lam" :key="i">
                  <span class="eval-prio" :class="`prio-${v.uu_tien}`">{{ (v.uu_tien||'').toUpperCase() }}</span>
                  {{ v.noi_dung }}
                </li>
              </ul>
            </div>
          </div>
        </template>

        <!-- ══ 2AS Review Result (inline, không redirect) ══════════════════ -->
        <template v-if="tvResult">
          <div class="section-sep" style="margin-top:24px">
            <div class="sep-line"></div>
            <div class="sep-label" style="color:#6366f1">🔍 Đánh giá 2AS – 7 Tiêu Chí</div>
            <div class="sep-line"></div>
          </div>
          <div class="eval-panel" style="margin-top:12px">
            <!-- Header -->
            <div class="eval-header">
              <span class="eval-title">Kết quả đánh giá hồ sơ</span>
              <span class="eval-badge" :class="tvResult.de_xuat_xu_ly?.muc_do==='Đồng ý'?'eval-badge-green':tvResult.de_xuat_xu_ly?.muc_do==='Cần bổ sung'||tvResult.de_xuat_xu_ly?.muc_do==='Chưa đủ cơ sở'?'eval-badge-amber':'eval-badge-red'">
                {{ tvResult.de_xuat_xu_ly?.ket_qua_tv || tvResult.status }}
              </span>
              <span class="eval-badge eval-badge-amber" style="margin-left:0">{{ tvResult.de_xuat_xu_ly?.muc_do }}</span>
              <button class="btn-reeval" @click="tvResult=null" title="Đóng panel đánh giá">✕ Đóng</button>
            </div>

            <!-- Lý do -->
            <div v-if="tvResult.de_xuat_xu_ly?.ly_do" class="eval-tong-quan">
              {{ tvResult.de_xuat_xu_ly.ly_do }}
            </div>

            <!-- Vấn đề cần bổ sung -->
            <div v-if="tvResult.van_de?.length" class="eval-section eval-warn" style="margin-bottom:12px">
              <div class="eval-sec-title">⚠ {{ tvResult.van_de.length }} vấn đề cần bổ sung</div>
              <ul class="eval-list">
                <li v-for="(v,i) in tvResult.van_de" :key="i">
                  <strong style="color:#d97706">[{{ v.nhom_tieu_chi }}]</strong>
                  {{ v.van_de }}
                  <span v-if="v.yeu_cau" style="color:#64748b;font-size:.75rem"> → {{ v.yeu_cau }}</span>
                </li>
              </ul>
            </div>

            <!-- 7 Tiêu chí 2AS -->
            <div v-if="tvResult.phan_tich_2as?.length">
              <table class="eval-table">
                <thead><tr><th>Mã</th><th>Tiêu chí</th><th>Nhận xét</th><th style="text-align:center">Kết quả</th></tr></thead>
                <tbody>
                  <tr v-for="(tc,i) in tvResult.phan_tich_2as" :key="i">
                    <td class="eval-tc-name">{{ tc.ma || `TC${i+1}` }}</td>
                    <td style="font-weight:600;font-size:.78rem">{{ tc.tieu_chi }}</td>
                    <td class="eval-nx">{{ tc.nhan_xet }}</td>
                    <td style="text-align:center">
                      <span class="eval-dg" :class="tc.ket_qua==='ĐẠT'?'dg-ok':tc.ket_qua?.includes('CẦN')||tc.ket_qua?.includes('BỔ SUNG')?'dg-na':'dg-fail'">
                        {{ tc.ket_qua }}
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- Việc cần làm -->
            <div v-if="tvResult.viec_can_lam?.length" class="eval-section eval-todo">
              <div class="eval-sec-title">📋 Việc cần làm ngay</div>
              <ul class="eval-list">
                <li v-for="(v,i) in tvResult.viec_can_lam" :key="i">
                  <span v-if="v.urgent" style="color:#dc2626;font-weight:700;margin-right:4px">⚡</span>
                  <strong>{{ v.title }}</strong>
                  <span v-if="v.mo_ta" style="color:#64748b;font-size:.75rem"> — {{ v.mo_ta }}</span>
                </li>
              </ul>
            </div>
          </div>
        </template>


        <!-- ══ SXKD ══════════════════════════════════════════════════ -->
        <template v-if="months.length && (scanTab==='sxkd' || !phieuResult)">

          <!-- Họ tên chung -->
          <div class="section-sep">
            <div class="sep-line"></div>
            <div class="sep-label sep-sxkd">📊 Kế Hoạch SXKD Tháng</div>
            <div class="sep-line"></div>
          </div>

          <div class="sxkd-doc" style="margin-bottom:16px">
            <div class="sxkd-subtitle">
              <span class="sxkd-field-label">Họ và tên:</span>
              <input class="sxkd-inline-input name-input" v-model="months[0].ho_ten" @input="sxkdDirty=true"/>
            </div>
          </div>

          <!-- Per-month công việc -->
          <div v-for="(m, mi) in months" :key="mi" class="sxkd-month-block">
            <div class="month-sep">
              <div class="month-sep-line"></div>
              <div class="month-sep-label">{{ extractMonthLabel(m.tieu_de) }}</div>
              <div class="month-sep-line"></div>
            </div>
            <div class="sxkd-doc">
              <div class="sxkd-title">{{ m.tieu_de }}</div>
              <div class="sxkd-section-label">BẢNG KẾ HOẠCH VÀ KẾT QUẢ CÔNG VIỆC</div>
              <div class="sxkd-table-wrap">
                <table class="sxkd-table">
                  <thead>
                    <tr class="sth">
                      <th rowspan="2" class="th-stt">STT</th>
                      <th rowspan="2" class="th-mang">CÁC MẢNG CÔNG TÁC</th>
                      <th rowspan="2" class="th-mota">MÔ TẢ SẢN PHẨM HOÀN THÀNH TRONG THÁNG</th>
                      <th colspan="3" class="thg th-kh">KẾ HOẠCH</th>
                      <th colspan="3" class="thg th-kq">KẾT QUẢ</th>
                      <th rowspan="2" class="th-link">LINK SẢN PHẨM</th>
                    </tr>
                    <tr class="sth">
                      <th class="ths">TỶ TRỌNG</th><th class="ths">KPI</th><th class="ths">BOD</th>
                      <th class="ths th-kq-col">TỶ LỆ KPI</th><th class="ths th-kq-col">KQ KPI</th><th class="ths th-kq-col">BOD</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="cv in m.cong_viec" :key="mi+'-'+cv.stt" class="sxkd-row">
                      <td class="td-stt">{{ cv.stt }}</td>
                      <td class="td-mang"><input class="sc-input" v-model="cv.mang_cong_tac" @input="sxkdDirty=true"/></td>
                      <td class="td-mota"><textarea class="sc-ta" v-model="cv.mo_ta_san_pham" rows="4" @input="sxkdDirty=true"></textarea></td>
                      <td class="td-num"><input class="sc-input tc" v-model="cv.ty_trong" @input="onTyTrongInput(m, cv)"/></td>
                      <td class="td-num"><input class="sc-input tc" v-model="cv.kpi_ke_hoach" @input="sxkdDirty=true"/></td>
                      <td class="td-bod"><input class="sc-input" v-model="cv.bod_ke_hoach" @input="sxkdDirty=true"/></td>
                      <td class="td-num kqc"><input class="sc-input tc" v-model="cv.ty_le_kpi_ket_qua" @input="onKpiKetQuaInput(m, cv)"/></td>
                      <td class="td-num kqc"><input class="sc-input tc kqb" v-model="cv.ket_qua_kpi" @input="onKetQuaKpiInput()"/></td>
                      <td class="td-bod kqc"><input class="sc-input" v-model="cv.bod_ket_qua" @input="sxkdDirty=true"/></td>
                      <td class="td-link"><textarea class="sc-ta link-ta" v-model="cv.link_san_pham" rows="3" @input="sxkdDirty=true"></textarea></td>
                    </tr>
                    <tr class="total-row">
                      <td colspan="3" class="total-label">TỶ LỆ ĐẠT</td>
                      <td class="td-num tc">{{ m.ty_le_dat_ke_hoach || '100%' }}</td>
                      <td colspan="2"></td>
                      <td colspan="2" class="td-num tc kqb">{{ computedMonthTotal(m) }}</td>
                      <td colspan="2"></td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div class="block-actions">
                <button class="action-btn action-excel" :disabled="loadingExcel===mi" @click="downloadExcel(mi)">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><path d="M8 13h2l2 4 2-4h2M8 10h8"/></svg>
                  {{ loadingExcel===mi ? 'Đang tạo...' : 'Tải Excel ' + extractMonthLabel(m.tieu_de) }}
                </button>
              </div>
            </div>
          </div>

          <!-- Phần chung: Nội quy + Chỉ đạo + Xét duyệt -->
          <div class="month-sep shared-sep">
            <div class="month-sep-line"></div>
            <div class="month-sep-label shared-label">Phần chung — tất cả tháng</div>
            <div class="month-sep-line"></div>
          </div>
          <div class="sxkd-doc">
            <div class="sxkd-section-label nq-label">NỘI QUY BẮT BUỘC</div>
            <div class="nq-note">(Vi phạm sẽ bị khấu trừ KPI)</div>
            <div class="sxkd-table-wrap">
              <table class="sxkd-table nq-table">
                <thead><tr class="sth"><th class="th-stt">STT</th><th>NỘI DUNG</th><th class="ths">KẾ HOẠCH</th><th class="ths">KẾT QUẢ</th><th>XÁC NHẬN</th><th>GHI CHÚ</th></tr></thead>
                <tbody>
                  <tr class="nq-hdr"><td colspan="6" class="nq-sub">THỰC HIỆN NỘI QUY</td></tr>
                  <tr v-for="nq in shared.noi_quy" :key="'nq'+nq.stt" class="sxkd-row">
                    <td class="td-stt">{{ nq.stt }}</td>
                    <td><input class="sc-input" v-model="nq.noi_dung" @input="sxkdDirty=true"/></td>
                    <td class="td-num tc"><input class="sc-input tc" v-model="nq.ke_hoach" @input="sxkdDirty=true"/></td>
                    <td class="td-num tc kqc"><input class="sc-input tc" v-model="nq.ket_qua" @input="sxkdDirty=true"/></td>
                    <td><input class="sc-input" v-model="nq.xac_nhan" @input="sxkdDirty=true"/></td>
                    <td><input class="sc-input" v-model="nq.ghi_chu" @input="sxkdDirty=true"/></td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div class="sxkd-section-label cd-label" style="margin-top:14px">CHỈ ĐẠO BAN LÃNH ĐẠO</div>
            <div class="sxkd-table-wrap">
              <table class="sxkd-table nq-table">
                <thead><tr class="sth"><th class="th-stt">STT</th><th>NỘI DUNG CHỈ ĐẠO</th><th class="ths kqc">KẾT QUẢ</th><th class="ths">BOD XÉT DUYỆT</th><th>GHI CHÚ</th></tr></thead>
                <tbody>
                  <tr v-for="cd in shared.chi_dao" :key="'cd'+cd.stt" class="sxkd-row">
                    <td class="td-stt">{{ cd.stt }}</td>
                    <td><input class="sc-input" v-model="cd.noi_dung" @input="sxkdDirty=true"/></td>
                    <td class="kqc"><input class="sc-input" v-model="cd.ket_qua" @input="sxkdDirty=true"/></td>
                    <td><input class="sc-input" v-model="cd.bod_xet_duyet" @input="sxkdDirty=true"/></td>
                    <td><input class="sc-input" v-model="cd.ghi_chu" @input="sxkdDirty=true"/></td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div class="sxkd-xetduyet">
              <div class="xd-title">PHẦN TRÌNH VÀ XÉT DUYỆT</div>
              <table class="xd-table">
                <thead><tr><th>XÉT DUYỆT</th><th>Ý KIẾN</th><th>Ranking</th></tr></thead>
                <tbody>
                  <tr><td class="xd-label">HOD</td><td><input class="sc-input" v-model="shared.xet_duyet.hod_y_kien"/></td><td rowspan="2" class="xd-ranking"><input class="sc-input tc ranking-input" v-model="shared.xet_duyet.ranking"/></td></tr>
                  <tr><td class="xd-label">BOD</td><td><input class="sc-input" v-model="shared.xet_duyet.bod_y_kien"/></td></tr>
                </tbody>
              </table>
            </div>
          </div>
        </template>

        <!-- Bottom reset -->
        <div class="bottom-reset">
          <button class="action-btn action-reset" @click="resetAll">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 102.13-9.36L1 10"/></svg>
            Scan lại từ đầu
          </button>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
const router = useRouter()

// ── CSRF ──────────────────────────────────────────────────────────
function csrf() {
  if (window.frappe?.csrf_token) return window.frappe.csrf_token
  const c = document.cookie.split('; ').find(r => r.startsWith('csrf_token='))?.split('=')[1]
  return c ? decodeURIComponent(c) : 'no-csrf'
}
async function callApi(url, body) {
  const h = { 'X-Frappe-CSRF-Token': csrf() }
  const r = await fetch(url, { method: 'POST', headers: h, body })
  if (!r.ok) {
    let msg = `HTTP ${r.status}`
    try { const j = await r.json(); msg = j.exception || j.message || msg } catch {}
    throw new Error(msg)
  }
  const j = await r.json()
  return j.message ?? j
}

// ── State ─────────────────────────────────────────────────────────
const step = ref(1)
const phieuFile = ref(null)
const sxkdFile = ref(null)
const tried = ref(false)
const loading = ref(false)
const loadingMsg = ref('')
const error = ref('')

const phieuResult = ref(null)
const scanSessionId = ref('')
const phieuDirty = ref(false)
const loadingDocx = ref(false)
const loadingPdf = ref(false)
const pdfError = ref('')
const phieuDone = ref(false)

const months = ref([])
const shared = ref({ noi_quy: [], chi_dao: [], xet_duyet: { hod_y_kien:'', bod_y_kien:'', ranking:'' } })
const sxkdDirty = ref(false)
const loadingExcel = ref(null)
const sxkdDone = ref(false)
const scanTab = ref('phieu')

// ── Đánh giá lại (re-evaluate without re-scan) ────────────────────────────
const loadingReeval = ref(false)

async function reEvaluate() {
  if (!scanSessionId.value) return
  loadingReeval.value = true
  try {
    const body = JSON.stringify({
      scan_session_id: scanSessionId.value,
      confirmed_fields: { ...ef }
    })
    const d2 = await callApi('/api/method/cnb_2as.api.scan_phieu.scan_analyze', body)
    phieuResult.value = d2
    // KHÔNG gọi populateEf ở đây — giữ nguyên ef của user để sửa tiếp nhiều lần
  } catch(e) {
    alert('Lỗi đánh giá lại: ' + e.message)
  } finally {
    loadingReeval.value = false
  }
}

function evalDgCls(dg) {
  if (!dg) return ''
  const d = dg.toLowerCase()
  if (d.includes('đạt') && !d.includes('chưa') && !d.includes('không')) return 'dg-ok'
  if (d.includes('chưa') || d.includes('không đủ') || d.includes('không đạt')) return 'dg-fail'
  return 'dg-na'
}

// ── Auto-calc KPI SXKD ─────────────────────────────────────────────────────
function pct(s) { return parseFloat((s || '').replace('%','').replace(',','.')) || 0 }
function fmtPct(n) { return n ? (Math.round(n * 10) / 10) + '%' : '' }

function calcRowKQ(cv) {
  const tt = pct(cv.ty_trong), tl = pct(cv.ty_le_kpi_ket_qua)
  return (tt && tl) ? fmtPct(tt * tl / 100) : ''
}

function computedMonthTotal(m) {
  const rows = m.cong_viec || []
  const total = rows.reduce((s, cv) => s + pct(cv.ket_qua_kpi || calcRowKQ(cv)), 0)
  return total > 0 ? fmtPct(total) : ''
}

function onKpiKetQuaInput(m, cv) {
  sxkdDirty.value = true
  const kq = calcRowKQ(cv)
  if (kq) cv.ket_qua_kpi = kq
}

function onTyTrongInput(m, cv) {
  sxkdDirty.value = true
  const kq = calcRowKQ(cv)
  if (kq) cv.ket_qua_kpi = kq
}

function onKetQuaKpiInput() {
  sxkdDirty.value = true
}

// ── Gửi vào Đánh giá 2AS ────────────────────────────────────────────────────
const loadingEval = ref(false)
const evalError = ref('')
const tvResult = ref(null)


async function sendToEval() {
  loadingEval.value = true
  evalError.value = ''
  try {
    const payload = {
      ef:       { ...ef },
      months:   months.value,
      shared:   shared.value,
      cv_list:  cvList.value,
    }
    const BASE = '/api/method/cnb_2as.api.thu_viec'
    const resp = await fetch(`${BASE}.review_from_scan`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Frappe-CSRF-Token': csrf(),
      },
      body: JSON.stringify(payload),
    })
    const j = await resp.json()
    if (!resp.ok) throw new Error(j?.exception || j?.message || `HTTP ${resp.status}`)
    const result = j.message ?? j
    // Hiển thị inline, không redirect
    tvResult.value = result
    // Vẫn lưu sessionStorage để user có thể mở ThuViec sau nếu cần
    sessionStorage.setItem('scan_eval_result', JSON.stringify(result))
  } catch(e) {
    evalError.value = e.message
  } finally {
    loadingEval.value = false
  }
}

// Phiếu editable fields
const ef = reactive({
  ho_ten:'', ma_nhan_su:'', chuc_danh:'', phong_ban:'', cong_ty:'',
  ngay_nhan_viec:'', ngay_het_han:'', thoi_gian_thu_viec:'', loai_hop_dong:'',
  ten_hod:'', ma_hod:'', chuc_danh_hod:'', don_vi_hod:'',
  nhan_xet_1_nv:'', nhan_xet_1_hod:'', nhan_xet_2_nv:'', nhan_xet_2_hod:'',
  nhan_xet_3_nv:'', nhan_xet_3_hod:'', nhan_xet_4_nv:'', nhan_xet_4_hod:'',
  nhan_xet_5_nv:'', nhan_xet_5_hod:'',
  kpi_tuan_1_ty_le:'', kpi_tuan_2_ty_le:'', kpi_tuan_3_ty_le:'', kpi_tuan_4_ty_le:'',
  kpi_tuan_5_ty_le:'', kpi_tuan_6_ty_le:'', kpi_tuan_7_ty_le:'', kpi_tuan_8_ty_le:'',
  diem_tbc_kpi_nv:'', diem_tbc_kpi_hod:'', cong_viec_duoc_giao:'', ty_le_hoan_thanh_16:'',
  nhiem_vu_1_noi_dung:'', nhiem_vu_1_ket_qua:'', nhiem_vu_1_ty_le:'', nhiem_vu_1_hod:'',
  nhiem_vu_2_noi_dung:'', nhiem_vu_2_ket_qua:'', nhiem_vu_2_ty_le:'', nhiem_vu_2_hod:'',
  nhiem_vu_3_noi_dung:'', nhiem_vu_3_ket_qua:'', nhiem_vu_3_ty_le:'', nhiem_vu_3_hod:'',
  nhiem_vu_4_noi_dung:'', nhiem_vu_4_ket_qua:'', nhiem_vu_4_ty_le:'', nhiem_vu_4_hod:'',
  nhiem_vu_5_noi_dung:'', nhiem_vu_5_ket_qua:'', nhiem_vu_5_ty_le:'', nhiem_vu_5_hod:'',
  nhiem_vu_6_noi_dung:'', nhiem_vu_6_ket_qua:'', nhiem_vu_6_ty_le:'', nhiem_vu_6_hod:'',
  nhiem_vu_7_noi_dung:'', nhiem_vu_7_ket_qua:'', nhiem_vu_7_ty_le:'', nhiem_vu_7_hod:'',
  nhiem_vu_8_noi_dung:'', nhiem_vu_8_ket_qua:'', nhiem_vu_8_ty_le:'', nhiem_vu_8_hod:'',
  san_pham_1:'', so_luong_file_1:'', link_dinh_kem_1:'', vi_pham_upload_1:'', kpi_sp_tuan_1:'',
  san_pham_2:'', so_luong_file_2:'', link_dinh_kem_2:'', vi_pham_upload_2:'', kpi_sp_tuan_2:'',
  san_pham_3:'', so_luong_file_3:'', link_dinh_kem_3:'', vi_pham_upload_3:'', kpi_sp_tuan_3:'',
  san_pham_4:'', so_luong_file_4:'', link_dinh_kem_4:'', vi_pham_upload_4:'', kpi_sp_tuan_4:'',
  san_pham_5:'', so_luong_file_5:'', link_dinh_kem_5:'', vi_pham_upload_5:'', kpi_sp_tuan_5:'',
  san_pham_6:'', so_luong_file_6:'', link_dinh_kem_6:'', vi_pham_upload_6:'', kpi_sp_tuan_6:'',
  san_pham_7:'', so_luong_file_7:'', link_dinh_kem_7:'', vi_pham_upload_7:'', kpi_sp_tuan_7:'',
  san_pham_8:'', so_luong_file_8:'', link_dinh_kem_8:'', vi_pham_upload_8:'', kpi_sp_tuan_8:'',
  hoi_nhap_1_nv:'', hoi_nhap_1_hod:'', hoi_nhap_2_nv:'', hoi_nhap_2_hod:'',
  hoi_nhap_3_nv:'', hoi_nhap_3_hod:'', hoi_nhap_4_nv:'', hoi_nhap_4_hod:'',
  hoi_nhap_5_nv:'', hoi_nhap_5_hod:'', hoi_nhap_6_nv:'', hoi_nhap_6_hod:'',
  hoi_nhap_7_nv:'', hoi_nhap_7_hod:'',
  hoi_nhap_7_1_nv:'', hoi_nhap_7_2_nv:'', hoi_nhap_7_3_nv:'', hoi_nhap_7_4_nv:'', hoi_nhap_7_5_nv:'',
  hoi_nhap_8_nv:'', hoi_nhap_8_hod:'', hoi_nhap_9_nv:'', hoi_nhap_9_hod:'',
  ket_luan:'', de_xuat_ky_hd:'', de_xuat_tang_thu_nhap:'', de_nghi_phoi_hop:'',
  y_kien_hod:'', y_kien_rtd:'', ngay_ky:'', ten_hod_ky:''
})
const efSnapshot = ref('')
const cvList = ref([{ ty_le: '' }])   // kept for backward compat

// Computed: số tuần thực tế (min 4)
const nTuan = computed(() => {
  let n = 0
  for (let i = 8; i >= 1; i--) {
    if (ef[`kpi_tuan_${i}_ty_le`] || ef[`san_pham_${i}`]) { n = i; break }
  }
  return Math.max(n, 4)
})

// Computed: số nhiệm vụ 1.6 (min 1)
const nNhiemVu = computed(() => {
  let n = 0
  for (let i = 8; i >= 1; i--) {
    if (ef[`nhiem_vu_${i}_noi_dung`] || ef[`nhiem_vu_${i}_ket_qua`]) { n = i; break }
  }
  return Math.max(n, 1)
})

function addCvRow() {
  cvList.value.push({ ty_le: '' })
  phieuDirty.value = true
}

function syncCvRows() {}  // no-op, kept for compat


const nhanXetRows = [
  { stt:'1', nvKey:'nhan_xet_1_nv', hodKey:'nhan_xet_1_hod', cau_hoi:'Những điểm ứng viên đã làm tốt trong quá trình thử việc?' },
  { stt:'2', nvKey:'nhan_xet_2_nv', hodKey:'nhan_xet_2_hod', cau_hoi:'Các kỹ năng nào đã đáp ứng yêu cầu công việc?' },
  { stt:'3', nvKey:'nhan_xet_3_nv', hodKey:'nhan_xet_3_hod', cau_hoi:'Ứng viên đã tích cực tham gia các hoạt động nào?' },
  { stt:'4', nvKey:'nhan_xet_4_nv', hodKey:'nhan_xet_4_hod', cau_hoi:'Những điểm cần cải thiện?' },
  { stt:'5', nvKey:'nhan_xet_5_nv', hodKey:'nhan_xet_5_hod', cau_hoi:'Kỹ năng cần trau dồi thêm?' },
]
const hoiNhapEditRows = [
  { stt:'1', nvKey:'hoi_nhap_1_nv', hodKey:'hoi_nhap_1_hod', cau_hoi:'Sứ mệnh của Tập đoàn?' },
  { stt:'2', nvKey:'hoi_nhap_2_nv', hodKey:'hoi_nhap_2_hod', cau_hoi:'Sứ mệnh bản thân từ nhận thức về Tập đoàn?' },
  { stt:'3', nvKey:'hoi_nhap_3_nv', hodKey:'hoi_nhap_3_hod', cau_hoi:'Tầm nhìn 2025 và 2052?' },
  { stt:'4', nvKey:'hoi_nhap_4_nv', hodKey:'hoi_nhap_4_hod', cau_hoi:'Tầm nhìn bản thân?' },
  { stt:'5', nvKey:'hoi_nhap_5_nv', hodKey:'hoi_nhap_5_hod', cau_hoi:'Văn hoá cốt lõi Tập đoàn?' },
  { stt:'6', nvKey:'hoi_nhap_6_nv', hodKey:'hoi_nhap_6_hod', cau_hoi:'Giá trị cốt lõi bản thân?' },
  { stt:'7', nvKey:'hoi_nhap_7_nv', hodKey:'hoi_nhap_7_hod', cau_hoi:'Phù hợp với Văn hoá Tập đoàn?' },
  { stt:'7.1', nvKey:'hoi_nhap_7_1_nv', hodKey:'hoi_nhap_7_1_hod', cau_hoi:'  → VH Hiệu quả: KPIs, tư duy hiệu quả' },
  { stt:'7.2', nvKey:'hoi_nhap_7_2_nv', hodKey:'hoi_nhap_7_2_hod', cau_hoi:'  → VH Tốc độ' },
  { stt:'7.3', nvKey:'hoi_nhap_7_3_nv', hodKey:'hoi_nhap_7_3_hod', cau_hoi:'  → VH Kỷ luật: QTQD, Quy chế' },
  { stt:'7.4', nvKey:'hoi_nhap_7_4_nv', hodKey:'hoi_nhap_7_4_hod', cau_hoi:'  → VH Học tập' },
  { stt:'7.5', nvKey:'hoi_nhap_7_5_nv', hodKey:'hoi_nhap_7_5_hod', cau_hoi:'  → VH Chính trực' },
  { stt:'8', nvKey:'hoi_nhap_8_nv', hodKey:'hoi_nhap_8_hod', cau_hoi:'Văn hoá kinh doanh Tập đoàn?' },
  { stt:'9', nvKey:'hoi_nhap_9_nv', hodKey:'hoi_nhap_9_hod', cau_hoi:'Đóng góp khác trong giai đoạn hội nhập?' },
]

const ketLuanRows = computed(() => {
  const kl = (ef.ket_luan || '').toLowerCase()
  return [
    { id:'dat', ket_luan:'Ứng viên đạt yêu cầu', de_xuat:'Ký HĐ:', selected: kl.includes('đạt') && !kl.includes('không') },
    { id:'khdat', ket_luan:'Không đạt và không có khả năng khắc phục', de_xuat:'Kết thúc thử việc', selected: kl.includes('không đạt') && kl.includes('không có') },
    { id:'giahan', ket_luan:'Không đạt nhưng có thể khắc phục', de_xuat:'Gia hạn thử việc', selected: kl.includes('gia hạn') },
    { id:'rtd', ket_luan:'Không đạt tại đây nhưng phù hợp vị trí khác', de_xuat:'RTD phỏng vấn', selected: kl.includes('rtd') || kl.includes('vị trí khác') },
  ]
})

function selectKetLuan(r) { ef.ket_luan = r.ket_luan }
function kpiClass(v) { const n=parseFloat((v||'').replace('%','')); if(isNaN(n)) return ''; return n>=90?'kpi-green':n>=75?'kpi-amber':'kpi-red' }
function extractMonthLabel(t) { const m=(t||'').match(/TH[ÁA]NG\s+(\d+)/i); return m?`Tháng ${m[1]}`:(t||'').slice(0,12)||'Tháng ?' }

const badgeCls = computed(() => {
  const m = phieuResult.value?.mau_de_xuat
  return m==='green'?'srb-green':m==='red'?'srb-red':'srb-amber'
})

function populateEf(fields) {
  if (!fields) return
  Object.keys(ef).forEach(k => { if (k in fields) ef[k] = fields[k] ?? '' })
  // Sync % rows after populate
  if (Array.isArray(fields.cong_viec_list) && fields.cong_viec_list.length) {
    cvList.value = fields.cong_viec_list.map(c => ({ ty_le: c.ty_le || '' }))
  } else {
    syncCvRows()
  }
  efSnapshot.value = JSON.stringify({ ...ef })
}

function savePhieu() { efSnapshot.value = JSON.stringify({ ...ef }); phieuDirty.value = false }
function cancelPhieu() { populateEf(JSON.parse(efSnapshot.value)); phieuDirty.value = false }

function onDrop(e, type) {
  const f = e.dataTransfer.files[0]; if (!f) return
  if (type === 'phieu') phieuFile.value = f
  else sxkdFile.value = f
}

// ── SCAN (đồng thời) ─────────────────────────────────────────────
async function doScan() {
  tried.value = true
  if (!phieuFile.value && !sxkdFile.value) return
  loading.value = true; error.value = ''
  phieuDone.value = false; sxkdDone.value = false

  const tasks = []

  if (phieuFile.value) {
    loadingMsg.value = 'GPT-4o đang đọc phiếu & KH SXKD song song...'
    const fd = new FormData(); fd.append('scan_file', phieuFile.value)
    tasks.push(
      callApi('/api/method/cnb_2as.api.scan_phieu.scan_extract', fd)
        .then(async d => {
          const sessionId = d.scan_session_id || ''
          const d2 = await callApi('/api/method/cnb_2as.api.scan_phieu.scan_analyze', JSON.stringify({ scan_session_id: sessionId, xml_input: d.xml_output || '' }))
          phieuResult.value = d2
          scanSessionId.value = sessionId
          populateEf(d2.confirmed_fields || d.extracted_fields || {})
          phieuDone.value = true
        })
        .catch(e => { error.value += `\nPhiếu: ${e.message}` })
    )
  }

  if (sxkdFile.value) {
    const fd2 = new FormData(); fd2.append('file', sxkdFile.value)
    tasks.push(
      callApi('/api/method/cnb_2as.api.scan_sxkd.ocr_sxkd', fd2)
        .then(msg => {
          const raw = msg.months ?? (msg.data ? [msg.data] : [msg])
          months.value = raw.map(m => ({
            tieu_de: m.tieu_de||'', ho_ten: (m.ho_ten||'').replace(/Họ và tên:\s*/i,'').trim(),
            cong_viec: m.cong_viec||[], ty_le_dat_ke_hoach: m.ty_le_dat_ke_hoach||'100%', ty_le_dat_ket_qua: m.ty_le_dat_ket_qua||''
          }))
          const src = raw.find(m => m.noi_quy?.length) || raw[0] || {}
          shared.value = {
            noi_quy: src.noi_quy?.length ? src.noi_quy : [
              { stt:1, noi_dung:'Upload data', ke_hoach:'100%', ket_qua:'', xac_nhan:'', ghi_chu:'' },
              { stt:2, noi_dung:'Học tập và áp dụng AI', ke_hoach:'100%', ket_qua:'', xac_nhan:'', ghi_chu:'' }
            ],
            chi_dao: src.chi_dao?.length ? src.chi_dao : [
              { stt:1, noi_dung:'', ket_qua:'', bod_xet_duyet:'', ghi_chu:'' },
              { stt:2, noi_dung:'', ket_qua:'', bod_xet_duyet:'', ghi_chu:'' },
              { stt:3, noi_dung:'', ket_qua:'', bod_xet_duyet:'', ghi_chu:'' },
            ],
            xet_duyet: src.xet_duyet || { hod_y_kien:'', bod_y_kien:'', ranking:'' }
          }
          sxkdDone.value = true
        })
        .catch(e => { error.value += `\nSXKD: ${e.message}` })
    )
  }

  await Promise.all(tasks)
  loading.value = false
  step.value = 2
}

// ── Download DOCX ─────────────────────────────────────────────────
async function downloadDocx() {
  if (!scanSessionId.value) return
  loadingDocx.value = true
  try {
    const data = await callApi('/api/method/cnb_2as.api.scan_phieu.fill_docx', JSON.stringify({ scan_session_id: scanSessionId.value }))
    const binary = atob(data.content_b64)
    const bytes = new Uint8Array(binary.length)
    for (let i=0;i<binary.length;i++) bytes[i]=binary.charCodeAt(i)
    const blob = new Blob([bytes], { type: data.content_type })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); a.href=url; a.download=data.filename
    document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url)
  } catch(e) { alert('Lỗi DOCX: '+e.message) }
  finally { loadingDocx.value = false }
}

// ── Download PDF Báo cáo 7 tiêu chí 2AS ──────────────────────────
async function downloadPdf() {
  if (!scanSessionId.value || !phieuResult.value) return
  loadingPdf.value = true
  pdfError.value = ''
  try {
    const payload = {
      scan_session_id: scanSessionId.value,
      analyze_result: phieuResult.value,
    }
    const r = await fetch('/api/method/cnb_2as.api.scan_phieu.download_pdf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Frappe-CSRF-Token': csrf() },
      body: JSON.stringify(payload),
    })
    if (!r.ok) {
      let msg = `HTTP ${r.status}`
      try { const j = await r.json(); msg = j.exception || j.message || msg } catch {}
      throw new Error(msg)
    }
    const blob = await r.blob()
    const url = URL.createObjectURL(blob)
    const ho = (ef.ho_ten || 'ScanPhieu').replace(/[\s/\\]+/g, '_')
    const a = document.createElement('a')
    a.href = url
    a.download = `BaoCao_ScanPhieu_${ho}_${new Date().toISOString().slice(0,10)}.pdf`
    document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url)
  } catch(e) { pdfError.value = 'Lỗi PDF: ' + e.message }
  finally { loadingPdf.value = false }
}

// ── Download Excel (SXKD) ─────────────────────────────────────────
async function downloadExcel(mi) {
  const m = months.value[mi]; if(!m) return
  loadingExcel.value = mi
  try {
    const fd = new FormData()
    fd.append('data', JSON.stringify({ ...m, noi_quy: shared.value.noi_quy, chi_dao: shared.value.chi_dao, xet_duyet: shared.value.xet_duyet }))
    const r = await fetch('/api/method/cnb_2as.api.scan_sxkd.export_excel', { method:'POST', headers:{'X-Frappe-CSRF-Token':csrf()}, body:fd })
    if (!r.ok) throw new Error(`HTTP ${r.status}`)
    const blob = await r.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); const ho = (m.ho_ten||'SXKD').replace(/[\s/\\]+/g,'_')
    const thang = (m.tieu_de||'').match(/TH[ÁA]NG\s+(\d+)/i)?.[1]||String(mi+1)
    a.href=url; a.download=`SXKD_${ho}_T${thang}.xlsx`
    document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url)
  } catch(e) { alert('Lỗi Excel: '+e.message) }
  finally { loadingExcel.value = null }
}

function resetAll() {
  step.value=1; phieuFile.value=null; sxkdFile.value=null; tried.value=false; error.value=''
  phieuResult.value=null; scanSessionId.value=''; phieuDirty.value=false; phieuDone.value=false
  months.value=[]; sxkdDirty.value=false; sxkdDone.value=false
  shared.value={ noi_quy:[], chi_dao:[], xet_duyet:{ hod_y_kien:'', bod_y_kien:'', ranking:'' } }
  cvList.value = [{ noi_dung:'', ty_le:'' }]
  Object.keys(ef).forEach(k=>ef[k]='')
}
</script>

<style scoped>
/* ── Layout ─────────────────────────────────────────────────────── */
.app-layout { display:flex; height:100vh; overflow:hidden; }
.sidebar { width:230px; min-width:200px; display:flex; flex-direction:column; border-right:1px solid rgba(99,102,241,.15); background:#13131a; overflow-y:auto; }
body.theme-light .sidebar { background:#fff; }

.sb-top { padding:14px; display:flex; align-items:center; gap:10px; border-bottom:1px solid rgba(255,255,255,.06); }
.sb-back { width:30px; height:30px; border-radius:8px; background:rgba(99,102,241,.1); display:flex; align-items:center; justify-content:center; color:#818cf8; text-decoration:none; transition:background .2s; }
.sb-back:hover { background:rgba(99,102,241,.2); }
.sb-logo { display:flex; align-items:center; gap:8px; }
.sb-logo-mark { font-size:22px; }
.sb-name { font-size:.86rem; font-weight:700; }
.sb-org { font-size:.7rem; color:#64748b; }
.sb-body { flex:1; overflow-y:auto; padding:14px; }
.sb-section { margin-bottom:18px; }
.sb-section-title { font-size:.72rem; font-weight:700; color:#6366f1; text-transform:uppercase; letter-spacing:.06em; margin-bottom:12px; }
.upl-group-label { font-size:.74rem; font-weight:700; color:#94a3b8; margin-bottom:5px; }

.sb-upload-card { display:flex; align-items:center; gap:8px; padding:9px 11px; border-radius:10px; border:1.5px dashed rgba(99,102,241,.3); background:rgba(99,102,241,.04); cursor:pointer; margin-bottom:6px; transition:all .2s; }
.sb-upload-card:hover { border-color:rgba(99,102,241,.5); background:rgba(99,102,241,.07); }
.sb-upload-card.filled { border-style:solid; border-color:#10b981; background:rgba(16,185,129,.05); }
.sb-upload-card.err { border-color:#ef4444; }
.upc-icon { font-size:18px; flex-shrink:0; }
.upc-info { flex:1; min-width:0; }
.upc-val { font-size:.76rem; font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; color:#94a3b8; }
.upc-val.ok { color:#10b981; }
.upc-val.empty { color:#64748b; }
.upc-rm { background:none; border:none; cursor:pointer; color:#ef4444; font-size:12px; flex-shrink:0; }

.sb-btn-primary { width:100%; padding:10px; border-radius:10px; border:none; cursor:pointer; background:linear-gradient(135deg,#10b981,#6366f1); color:white; font-weight:700; font-size:.84rem; display:flex; align-items:center; justify-content:center; gap:7px; transition:all .2s; margin-top:10px; }
.sb-btn-primary:hover:not(:disabled) { opacity:.9; }
.sb-btn-primary:disabled { opacity:.5; cursor:not-allowed; }
.sb-btn-ghost { width:100%; padding:8px; border:none; background:transparent; color:#64748b; font-size:.82rem; cursor:pointer; margin-top:8px; border-radius:8px; }
.sb-btn-ghost:hover { color:#94a3b8; background:rgba(99,102,241,.05); }
.sb-btn-eval { width:100%; padding:10px 14px; border:none; border-radius:10px; background:linear-gradient(135deg,#10b981,#059669); color:#fff; font-weight:700; font-size:.86rem; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:7px; transition:opacity .2s, transform .15s; box-shadow:0 4px 14px rgba(16,185,129,.25); }
.sb-btn-eval:hover:not(:disabled) { opacity:.9; transform:translateY(-1px); }
.sb-btn-eval:disabled { opacity:.55; cursor:not-allowed; }

.sb-btn-docx { width:100%; padding:8px; border:1px solid rgba(16,185,129,.4); border-radius:9px; background:rgba(16,185,129,.08); color:#10b981; font-weight:700; font-size:.8rem; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:6px; margin-top:7px; transition:all .2s; }
.sb-btn-docx:hover:not(:disabled) { background:rgba(16,185,129,.16); }
.sb-btn-docx:disabled { opacity:.5; cursor:not-allowed; }
.sb-btn-pdf { width:100%; padding:8px; border:1px solid rgba(99,102,241,.4); border-radius:9px; background:rgba(99,102,241,.08); color:#818cf8; font-weight:700; font-size:.8rem; cursor:pointer; display:flex; align-items:center; justify-content:center; gap:6px; margin-top:6px; transition:all .2s; }
.sb-btn-pdf:hover:not(:disabled) { background:rgba(99,102,241,.18); color:#6366f1; }
.sb-btn-pdf:disabled { opacity:.5; cursor:not-allowed; }

.sb-result-block { padding:10px; background:rgba(99,102,241,.06); border-radius:10px; margin-bottom:10px; border:1px solid rgba(99,102,241,.12); }
.srb-title { font-size:.72rem; font-weight:700; color:#6366f1; text-transform:uppercase; margin-bottom:7px; }
.srb-badge { display:inline-block; padding:3px 10px; border-radius:6px; font-size:.78rem; font-weight:700; margin-bottom:6px; }
.srb-green { background:rgba(16,185,129,.15); color:#10b981; }
.srb-amber { background:rgba(245,158,11,.15); color:#f59e0b; }
.srb-red   { background:rgba(239,68,68,.15); color:#ef4444; }
.sxkd-block { border-color:rgba(16,185,129,.15); background:rgba(16,185,129,.04); }
.srb-month { display:flex; align-items:center; gap:7px; padding:4px 0; font-size:.78rem; }
.srb-month-label { flex:1; font-weight:600; }
.srb-kq { color:#10b981; font-weight:700; }
.srb-dl-btn { background:rgba(16,185,129,.15); border:none; color:#10b981; border-radius:5px; width:22px; height:22px; cursor:pointer; font-size:.76rem; display:flex; align-items:center; justify-content:center; }

.sb-err { color:#ef4444; font-size:.76rem; margin-top:4px; }
.sb-err-box { margin-top:8px; padding:9px; background:rgba(239,68,68,.08); border-radius:8px; color:#ef4444; font-size:.78rem; }
.spinner { width:13px; height:13px; border:2px solid rgba(255,255,255,.3); border-top-color:#fff; border-radius:50%; animation:spin .7s linear infinite; }
@keyframes spin { to { transform:rotate(360deg); } }

/* ── Main ────────────────────────────────────────────────────────── */
.result-panel { flex:1; overflow:hidden; display:flex; flex-direction:column; }
.welcome { flex:1; display:flex; flex-direction:column; align-items:center; justify-content:center; padding:40px; text-align:center; }
.welcome-icon { margin-bottom:22px; }
.welcome h1 { font-size:1.6rem; font-weight:800; margin-bottom:10px; }
.welcome p { color:#94a3b8; max-width:420px; line-height:1.7; margin-bottom:24px; }
.welcome-features { display:flex; gap:10px; flex-wrap:wrap; justify-content:center; }
.wf { display:flex; align-items:center; gap:7px; background:rgba(99,102,241,.08); padding:9px 14px; border-radius:10px; font-size:.8rem; font-weight:600; }
.wf-icon { font-size:17px; }

/* Loading */
.loading-screen { flex:1; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:18px; }
.loading-rings { position:relative; width:70px; height:70px; display:flex; align-items:center; justify-content:center; }
.ring { position:absolute; border-radius:50%; border:3px solid transparent; }
.ring-1 { width:70px; height:70px; border-top-color:#6366f1; animation:spin .9s linear infinite; }
.ring-2 { width:50px; height:50px; border-top-color:#10b981; animation:spin 1.2s linear infinite reverse; }
.ring-center { font-size:22px; z-index:1; }
.loading-msg { font-weight:600; color:#a5b4fc; }
.loading-tasks { display:flex; flex-direction:column; gap:8px; }
.lt { display:flex; align-items:center; gap:8px; font-size:.84rem; color:#94a3b8; }
.lt-done { color:#10b981; }
.lt-icon { font-size:15px; }

/* Results scroll */
.results-scroll { flex:1; overflow-y:auto; padding:20px 28px 60px; }

/* Tab Switcher */
.scan-tabs { display:flex; gap:4px; padding:4px; background:rgba(99,102,241,.06); border-radius:12px; margin-bottom:20px; border:1px solid rgba(99,102,241,.12); }
.scan-tab { flex:1; padding:10px 16px; border:none; border-radius:9px; background:transparent; color:#94a3b8; font-size:.84rem; font-weight:600; cursor:pointer; transition:all .2s; display:flex; align-items:center; justify-content:center; gap:6px; }
.scan-tab:hover { background:rgba(99,102,241,.08); color:#818cf8; }
.scan-tab.active { background:#6366f1; color:#fff; box-shadow:0 2px 8px rgba(99,102,241,.3); }

/* Thin scrollbar */
.sidebar::-webkit-scrollbar, .sb-body::-webkit-scrollbar, .results-scroll::-webkit-scrollbar { width:4px; }
.sidebar::-webkit-scrollbar-track, .sb-body::-webkit-scrollbar-track, .results-scroll::-webkit-scrollbar-track { background:transparent; }
.sidebar::-webkit-scrollbar-thumb, .sb-body::-webkit-scrollbar-thumb, .results-scroll::-webkit-scrollbar-thumb { background:rgba(99,102,241,.15); border-radius:4px; }
.sidebar::-webkit-scrollbar-thumb:hover, .sb-body::-webkit-scrollbar-thumb:hover, .results-scroll::-webkit-scrollbar-thumb:hover { background:rgba(99,102,241,.3); }
.pe-ta::-webkit-scrollbar, .sc-ta::-webkit-scrollbar { width:3px; }
.pe-ta::-webkit-scrollbar-thumb, .sc-ta::-webkit-scrollbar-thumb { background:rgba(99,102,241,.2); border-radius:3px; }
.pe-ta::-webkit-scrollbar-thumb:hover, .sc-ta::-webkit-scrollbar-thumb:hover { background:rgba(99,102,241,.35); }

/* Separators */
.section-sep { display:flex; align-items:center; gap:14px; margin:24px 0 16px; }
.sep-line { flex:1; height:2px; background:linear-gradient(90deg,transparent,rgba(99,102,241,.25),transparent); }
.sep-label { font-size:.9rem; font-weight:800; text-transform:uppercase; letter-spacing:.07em; white-space:nowrap; padding:6px 18px; border-radius:20px; }
.sep-phieu { color:#818cf8; background:rgba(99,102,241,.08); border:1px solid rgba(99,102,241,.2); }
.sep-sxkd { color:#10b981; background:rgba(16,185,129,.07); border:1px solid rgba(16,185,129,.2); }

/* ── Phiếu document ────────────────────────────────────────────── */
.phieu-doc { background:white; border-radius:14px; padding:24px; box-shadow:0 4px 20px rgba(0,0,0,.07); max-width:1050px; margin:0 auto; }
body.theme-dark .phieu-doc { background:#1a1a28; }
.phieu-title { text-align:center; font-size:1rem; font-weight:800; text-transform:uppercase; color:#1e293b; margin-bottom:4px; }
body.theme-dark .phieu-title { color:#f1f5f9; }
.phieu-subtitle { text-align:center; font-size:.8rem; color:#94a3b8; margin-bottom:18px; }
.phieu-section-head { background:linear-gradient(90deg,rgba(99,102,241,.15),rgba(99,102,241,.03)); border-left:3px solid #6366f1; padding:6px 12px; font-size:.75rem; font-weight:700; letter-spacing:.05em; color:#818cf8; text-transform:uppercase; margin:14px 0 6px; border-radius:0 6px 6px 0; }
.phieu-table { width:100%; border-collapse:collapse; margin-bottom:6px; font-size:.83rem; }
.phieu-table th { background:#f1f5f9; color:#374151; font-weight:700; padding:6px 9px; text-align:left; border:1px solid #d1d5db; font-size:.76rem; }
body.theme-dark .phieu-table th { background:#1e2030; color:#94a3b8; border-color:rgba(255,255,255,.08); }
.phieu-table td { padding:6px 9px; border:1px solid #e2e8f0; vertical-align:top; line-height:1.5; }
body.theme-dark .phieu-table td { border-color:rgba(255,255,255,.07); }
.pl { font-weight:600; color:#6366f1; white-space:nowrap; }
.pc { text-align:center; font-weight:600; color:#6366f1; }
.phieu-selected { background:rgba(16,185,129,.08) !important; }
.phieu-checkbox { margin-right:5px; }
.sp-card { border:1px solid rgba(99,102,241,.15); border-radius:10px; padding:10px 12px; margin-bottom:10px; }
.sp-head { display:flex; align-items:center; gap:8px; font-weight:700; color:#818cf8; font-size:.86rem; margin-bottom:4px; }
.sp-kpi { padding:2px 8px; border-radius:20px; font-size:.76rem; font-weight:700; }
.kpi-green { background:rgba(16,185,129,.15); color:#10b981; }
.kpi-amber { background:rgba(245,158,11,.15); color:#f59e0b; }
.kpi-red   { background:rgba(239,68,68,.15); color:#ef4444; }

.pe-input {
  width: 100%; box-sizing: border-box;
  background: rgba(99,102,241,.03);
  border: 1.5px solid rgba(99,102,241,.18);
  border-radius: 7px;
  color: inherit;
  font-size: .83rem;
  padding: 5px 9px;
  outline: none;
  transition: border-color .18s, background .18s, box-shadow .18s;
  font-family: inherit;
}
.pe-input:hover { border-color: rgba(99,102,241,.35); background: rgba(99,102,241,.05); }
.pe-input:focus {
  border-color: #6366f1;
  background: rgba(99,102,241,.07);
  box-shadow: 0 0 0 3px rgba(99,102,241,.12);
}
.pe-ta {
  width: 100%; box-sizing: border-box;
  background: rgba(99,102,241,.03);
  border: 1.5px solid rgba(99,102,241,.18);
  border-radius: 7px;
  color: inherit;
  font-size: .83rem;
  padding: 6px 9px;
  outline: none;
  resize: vertical;
  font-family: inherit;
  line-height: 1.6;
  transition: border-color .18s, background .18s, box-shadow .18s;
  min-height: 52px;
}
.pe-ta:hover { border-color: rgba(99,102,241,.35); background: rgba(99,102,241,.05); }
.pe-ta:focus {
  border-color: #6366f1;
  background: rgba(99,102,241,.07);
  box-shadow: 0 0 0 3px rgba(99,102,241,.12);
}
/* HOD fields — amber tint */
.pe-hod {
  border-color: rgba(245,158,11,.3);
  background: rgba(245,158,11,.04);
}
.pe-hod:hover { border-color: rgba(245,158,11,.5); background: rgba(245,158,11,.07); }
.pe-hod:focus {
  border-color: #f59e0b;
  background: rgba(245,158,11,.08);
  box-shadow: 0 0 0 3px rgba(245,158,11,.12);
}
.pe-hod::placeholder { color: rgba(245,158,11,.45); }


.dirty-bar { display:flex; align-items:center; gap:10px; padding:8px 14px; margin-bottom:12px; background:rgba(251,191,36,.08); border:1px solid rgba(251,191,36,.2); border-radius:8px; font-size:.82rem; color:#f59e0b; font-weight:600; }
.db-save { background:#6366f1; color:white; border:none; border-radius:6px; padding:3px 10px; cursor:pointer; font-size:.78rem; }
.db-cancel { background:transparent; border:1px solid rgba(255,255,255,.15); color:#94a3b8; border-radius:6px; padding:3px 10px; cursor:pointer; font-size:.78rem; }

/* ── SXKD document ─────────────────────────────────────────────── */
.sxkd-month-block { margin-bottom:30px; }
.month-sep { display:flex; align-items:center; gap:12px; margin:20px 0 14px; }
.month-sep-line { flex:1; height:1.5px; background:linear-gradient(90deg,transparent,rgba(99,102,241,.25),transparent); }
.month-sep-label { font-size:.84rem; font-weight:800; color:#6366f1; text-transform:uppercase; letter-spacing:.07em; white-space:nowrap; padding:4px 14px; background:rgba(99,102,241,.07); border-radius:18px; border:1px solid rgba(99,102,241,.18); }
.shared-sep { margin:28px 0 16px; }
.shared-label { color:#10b981 !important; border-color:rgba(16,185,129,.2) !important; background:rgba(16,185,129,.06) !important; }

.sxkd-doc { background:white; border-radius:12px; padding:22px; box-shadow:0 3px 16px rgba(0,0,0,.06); max-width:1050px; margin:0 auto; }
body.theme-dark .sxkd-doc { background:#1a1a28; }
.sxkd-title { text-align:center; font-size:.95rem; font-weight:800; text-transform:uppercase; color:#1e293b; margin-bottom:10px; }
body.theme-dark .sxkd-title { color:#f1f5f9; }
.sxkd-subtitle { display:flex; align-items:center; gap:10px; margin-bottom:12px; padding-bottom:10px; border-bottom:2px solid #e2e8f0; }
body.theme-dark .sxkd-subtitle { border-bottom-color:rgba(255,255,255,.08); }
.sxkd-field-label { font-weight:700; font-size:.88rem; white-space:nowrap; }
.sxkd-inline-input { border:none; border-bottom:2px solid rgba(99,102,241,.3); background:transparent; outline:none; color:inherit; flex:1; font-size:.9rem; padding:2px 4px; }
.sxkd-inline-input:focus { border-bottom-color:#6366f1; }
.name-input { font-weight:700 !important; }
.sxkd-section-label { font-size:.7rem; font-weight:800; text-transform:uppercase; letter-spacing:.06em; color:#6366f1; margin:14px 0 4px; }
.nq-label { color:#f59e0b; }
.cd-label { color:#ef4444; }
.nq-note { font-size:.7rem; color:#94a3b8; margin-bottom:6px; }

.sxkd-table-wrap { overflow-x:auto; margin-bottom:4px; border-radius:8px; border:1.5px solid #e2e8f0; }
body.theme-dark .sxkd-table-wrap { border-color:rgba(255,255,255,.08); }
.sxkd-table { width:100%; border-collapse:collapse; min-width:860px; }
.nq-table { min-width:620px; }
.sth th { background:#f1f5f9; font-size:.67rem; font-weight:700; text-transform:uppercase; padding:6px 7px; border:1px solid #d1d5db; color:#374151; text-align:center; }
body.theme-dark .sth th { background:#1e2030; color:#94a3b8; border-color:rgba(255,255,255,.07); }
.ths { font-size:.65rem !important; }
.thg { border-bottom:none !important; }
.th-kh { background:rgba(99,102,241,.07) !important; color:#6366f1 !important; }
.th-kq { background:rgba(16,185,129,.07) !important; color:#059669 !important; }
.sxkd-row td { border:1px solid #e2e8f0; padding:0; vertical-align:top; }
body.theme-dark .sxkd-row td { border-color:rgba(255,255,255,.06); }
.td-stt { width:30px; text-align:center; font-weight:700; color:#6366f1; padding:7px; vertical-align:middle; }
.td-mang { width:110px; } .td-mota { width:250px; } .td-num { width:62px; } .td-bod { width:70px; } .td-link { width:130px; }
.kqc { background:rgba(16,185,129,.03) !important; }
.kqb { font-weight:700 !important; color:#059669 !important; }
.tc { text-align:center !important; }
.total-row td { border:1px solid #e2e8f0; padding:7px; }
body.theme-dark .total-row td { border-color:rgba(255,255,255,.06); }
.total-label { text-align:center; font-weight:800; font-size:.8rem; background:#f8fafc; }
body.theme-dark .total-label { background:#1a1a28; }
.sc-input { width:100%; border:none; background:transparent; outline:none; color:inherit; font-size:.78rem; padding:5px 7px; font-family:inherit; }
.sc-input:focus { background:rgba(99,102,241,.04); }
.sc-ta { width:100%; border:none; background:transparent; outline:none; color:inherit; font-size:.77rem; padding:5px 7px; font-family:inherit; resize:vertical; min-height:65px; }
.sc-ta:focus { background:rgba(99,102,241,.04); }
.link-ta { font-size:.71rem; color:#6366f1; }
.nq-hdr td { background:#fef3c7; color:#92400e; font-weight:700; font-size:.75rem; padding:4px 10px; border:1px solid #e2e8f0; }
body.theme-dark .nq-hdr td { background:rgba(245,158,11,.1); color:#fbbf24; }
.nq-sub { text-align:left; }
.sxkd-xetduyet { margin-top:14px; }
.xd-title { text-align:center; font-weight:800; font-size:.8rem; text-transform:uppercase; color:#374151; margin-bottom:8px; }
body.theme-dark .xd-title { color:#f1f5f9; }
.xd-table { margin:0 auto; width:50%; min-width:320px; border-collapse:collapse; }
.xd-table th { background:#f1f5f9; border:1px solid #d1d5db; padding:6px 10px; font-size:.75rem; font-weight:700; text-align:center; }
body.theme-dark .xd-table th { background:#1e2030; border-color:rgba(255,255,255,.08); color:#94a3b8; }
.xd-table td { border:1px solid #e2e8f0; }
body.theme-dark .xd-table td { border-color:rgba(255,255,255,.06); }
.xd-label { text-align:center; font-weight:700; font-size:.8rem; padding:8px; width:66px; }
.xd-ranking { text-align:center; vertical-align:middle; }
.ranking-input { font-size:1.1rem !important; font-weight:800 !important; color:#6366f1 !important; }

/* Block actions */
.block-actions { display:flex; gap:10px; margin-top:18px; padding-top:16px; border-top:1.5px solid #e2e8f0; }
body.theme-dark .block-actions { border-top-color:rgba(255,255,255,.07); }
.action-btn { display:flex; align-items:center; gap:8px; padding:11px 20px; border-radius:10px; border:none; cursor:pointer; font-size:.88rem; font-weight:700; transition:all .2s; }
.action-btn:hover:not(:disabled) { transform:translateY(-2px); }
.action-btn:disabled { opacity:.6; cursor:not-allowed; }
.action-docx { background:linear-gradient(135deg,#4f46e5,#7c3aed); color:white; box-shadow:0 3px 10px rgba(99,102,241,.28); }
.action-excel { background:linear-gradient(135deg,#059669,#10b981); color:white; box-shadow:0 3px 10px rgba(16,185,129,.28); }
.action-reset { background:rgba(99,102,241,.08); color:#6366f1; border:1.5px solid rgba(99,102,241,.25); }
.action-reset:hover { background:rgba(99,102,241,.15); }
.bottom-reset { display:flex; justify-content:center; margin-top:20px; padding-top:24px; border-top:2px solid rgba(99,102,241,.08); }
/* 1.6 compact % column */
.cv-pct-row { display:flex; align-items:center; gap:4px; margin-bottom:5px; }
.cv-pct-total-row { display:flex; align-items:center; gap:4px; margin-top:6px; padding-top:6px; border-top:1.5px solid rgba(99,102,241,.15); }
.cv-pct-num { font-size:.74rem; font-weight:700; color:#6366f1; min-width:18px; text-align:center; }
.cv-pct-input { width:68px !important; text-align:center; font-size:.82rem; padding:4px 5px !important; }
.cv-rm-btn { background:none; border:none; color:#ef4444; cursor:pointer; font-size:.7rem; padding:2px 4px; border-radius:4px; flex-shrink:0; }
.cv-rm-btn:hover { background:rgba(239,68,68,.1); }
.cv-add-btn { display:inline-flex; align-items:center; gap:4px; margin-top:7px; padding:4px 10px; border-radius:7px; border:1.5px dashed rgba(99,102,241,.3); background:rgba(99,102,241,.04); color:#818cf8; font-size:.76rem; font-weight:600; cursor:pointer; transition:all .2s; white-space:nowrap; }
.cv-add-btn:hover { background:rgba(99,102,241,.1); border-color:#6366f1; }

/* ── Evaluation Panel ─────────────────────────────────────────────────────── */
.eval-panel { margin-top:24px; padding:18px 20px; border-radius:14px; border:1.5px solid rgba(99,102,241,.2); background:rgba(99,102,241,.04); }
body.theme-dark .eval-panel { border-color:rgba(99,102,241,.25); background:rgba(99,102,241,.06); }
.eval-header { display:flex; align-items:center; gap:10px; margin-bottom:14px; flex-wrap:wrap; }
.eval-title { font-size:.95rem; font-weight:800; color:#6366f1; }
.eval-badge { padding:4px 12px; border-radius:20px; font-size:.78rem; font-weight:800; }
.eval-badge-green { background:rgba(16,185,129,.15); color:#059669; border:1.5px solid rgba(16,185,129,.3); }
.eval-badge-amber { background:rgba(251,191,36,.15); color:#d97706; border:1.5px solid rgba(251,191,36,.3); }
.eval-badge-red { background:rgba(239,68,68,.12); color:#dc2626; border:1.5px solid rgba(239,68,68,.25); }
body.theme-dark .eval-badge-green { background:rgba(16,185,129,.12); color:#34d399; }
body.theme-dark .eval-badge-amber { background:rgba(251,191,36,.1); color:#fbbf24; }
body.theme-dark .eval-badge-red { background:rgba(239,68,68,.1); color:#f87171; }
.btn-reeval { margin-left:auto; display:flex; align-items:center; gap:6px; padding:6px 14px; border-radius:8px; border:1.5px solid rgba(99,102,241,.35); background:rgba(99,102,241,.08); color:#6366f1; font-size:.8rem; font-weight:700; cursor:pointer; transition:all .2s; }
.btn-reeval:hover:not(:disabled) { background:rgba(99,102,241,.18); transform:translateY(-1px); }
.btn-reeval:disabled { opacity:.55; cursor:not-allowed; }
.eval-tong-quan { font-size:.84rem; line-height:1.65; color:#475569; padding:10px 14px; background:rgba(255,255,255,.5); border-radius:9px; margin-bottom:12px; }
body.theme-dark .eval-tong-quan { background:rgba(255,255,255,.05); color:#94a3b8; }
.eval-table { width:100%; border-collapse:collapse; font-size:.8rem; margin-bottom:12px; }
.eval-table th { background:rgba(99,102,241,.08); padding:7px 10px; text-align:left; font-size:.74rem; font-weight:700; color:#64748b; border-bottom:1.5px solid rgba(99,102,241,.15); }
.eval-table td { padding:7px 10px; border-bottom:1px solid rgba(99,102,241,.08); vertical-align:top; }
body.theme-dark .eval-table th { background:rgba(99,102,241,.12); color:#94a3b8; border-color:rgba(99,102,241,.2); }
body.theme-dark .eval-table td { border-color:rgba(99,102,241,.08); }
.eval-tc-name { font-weight:700; font-size:.78rem; color:#334155; white-space:nowrap; }
body.theme-dark .eval-tc-name { color:#cbd5e1; }
.eval-dg { display:inline-block; padding:2px 8px; border-radius:5px; font-size:.72rem; font-weight:700; }
.dg-ok { background:rgba(16,185,129,.12); color:#059669; }
.dg-fail { background:rgba(239,68,68,.1); color:#dc2626; }
.dg-na { background:rgba(148,163,184,.12); color:#64748b; }
.eval-nx { font-size:.78rem; color:#475569; line-height:1.5; }
body.theme-dark .eval-nx { color:#94a3b8; }
.eval-section { padding:10px 14px; border-radius:9px; margin-bottom:8px; }
.eval-sec-title { font-size:.78rem; font-weight:800; margin-bottom:6px; }
.eval-good { background:rgba(16,185,129,.07); }
.eval-good .eval-sec-title { color:#059669; }
.eval-warn { background:rgba(251,191,36,.07); }
.eval-warn .eval-sec-title { color:#d97706; }
.eval-todo { background:rgba(99,102,241,.06); }
.eval-todo .eval-sec-title { color:#6366f1; }
.eval-list { margin:0; padding-left:18px; }
.eval-list li { font-size:.8rem; color:#475569; line-height:1.6; }
body.theme-dark .eval-list li { color:#94a3b8; }
.eval-prio { display:inline-block; padding:1px 6px; border-radius:4px; font-size:.65rem; font-weight:800; margin-right:5px; }
.prio-cao { background:rgba(239,68,68,.12); color:#dc2626; }
.prio-trung { background:rgba(251,191,36,.12); color:#d97706; }
.prio-thap { background:rgba(16,185,129,.1); color:#059669; }
/* Sidebar Đánh giá lại button */
.sb-btn-reeval { display:flex; align-items:center; gap:6px; width:100%; padding:9px 12px; border-radius:9px; border:1.5px solid rgba(99,102,241,.3); background:rgba(99,102,241,.06); color:#818cf8; font-size:.8rem; font-weight:700; cursor:pointer; transition:all .2s; margin-top:6px; }
.sb-btn-reeval:hover:not(:disabled) { background:rgba(99,102,241,.15); }
.sb-btn-reeval:disabled { opacity:.5; cursor:not-allowed; }
</style>

