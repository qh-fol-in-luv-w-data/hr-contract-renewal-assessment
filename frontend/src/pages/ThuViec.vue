<template>
  <div class="app-layout">
    <!-- SIDEBAR -->
    <aside class="sidebar">
      <div class="sb-top">
        <div class="sidebar-header">
          <router-link to="/" class="sb-back">←</router-link>
          <div class="sb-title">
            <div class="sb-title-main">{{ t('welcome_tv').replace('AI ', '') }}</div>
            <div class="sb-title-sub">CT Group</div>
          </div>
          <button class="sb-reload" title="Tạo đánh giá mới / Tải lại" @click="reloadPage">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 2v6h-6"/><path d="M3 12a9 9 0 1 0 2.13-5.83L21 8"/></svg>
          </button>
        </div>
      </div>

      <div class="sb-body">
        <!-- Loại đánh giá: Học việc / Thử việc (ĐẶT LÊN TRƯỚC) -->
        <div class="sb-section">
          <div class="sb-section-title">Loại đánh giá</div>
          <div class="eval-type-toggle">
            <button class="etype-btn" :class="{active: evalType==='thu_viec'}" @click="evalType='thu_viec'">🎯 Thử việc</button>
            <button class="etype-btn" :class="{active: evalType==='hoc_viec'}" @click="evalType='hoc_viec'">🎓 Học việc</button>
          </div>
        </div>

        <!-- Input Mode Toggle -->
        <div class="sb-section">
          <div class="sb-section-title">{{ t('input_mode') }}</div>
          <div class="mode-toggle">
            <button class="mode-btn" :class="{active: inputMode==='default'}" @click="inputMode='default'">
              <span class="mode-icon">📄</span>
              {{ t('mode_default') }}
            </button>
            <button class="mode-btn" :class="{active: inputMode==='scan'}" @click="inputMode='scan'">
              <span class="mode-icon">📷</span>
              {{ t('mode_scan') }}
            </button>
          </div>
        </div>

        <div class="sb-section">
          <div class="sb-section-title">{{ t('eval_docs') }}</div>

          <div class="sb-upload-card" :class="{filled: docxFile, err: !docxFile&&tried}"
            @dragover.prevent @drop.prevent="drop($event,'docx')" @click="$refs.rDocx.click()">
            <input ref="rDocx" type="file" :accept="inputMode==='scan'?'.pdf':'.docx,.pdf'" hidden @change="e=>docxFile=e.target.files[0]||null"/>
            <div class="upc-icon">{{ docxFile?'📝':'📄' }}</div>
            <div class="upc-info" :title="docxFile ? docxFile.name : ''">
              <div class="upc-label">{{ t('file_docx_title') }}</div>
              <div class="upc-val" :class="docxFile?'ok':'empty'">
                {{ docxFile ? docxFile.name : t('click_to_select') }}
              </div>
              <div v-if="!docxFile" class="upc-hint">{{ inputMode==='scan' ? t('scan_pdf_hint') : t('file_docx_desc') }}</div>
            </div>
            <button v-if="docxFile" class="upc-rm" @click.stop="docxFile=null">✕</button>
          </div>

          <div class="sb-upload-card" :class="{filled: xlsxFile, err: !xlsxFile&&tried}"
            @dragover.prevent @drop.prevent="drop($event,'xlsx')" @click="$refs.rXlsx.click()">
            <input ref="rXlsx" type="file" :accept="inputMode==='scan'?'.pdf':'.xlsx,.pdf'" hidden @change="e=>xlsxFile=e.target.files[0]||null"/>
            <div class="upc-icon">{{ xlsxFile?'📊':'📋' }}</div>
            <div class="upc-info" :title="xlsxFile ? xlsxFile.name : ''">
              <div class="upc-label">{{ t('file_xlsx_title') }}</div>
              <div class="upc-val" :class="xlsxFile?'ok':'empty'">
                {{ xlsxFile ? xlsxFile.name : t('click_to_select') }}
              </div>
              <div v-if="!xlsxFile" class="upc-hint">{{ inputMode==='scan' ? t('scan_pdf_hint') : t('file_xlsx_desc') }}</div>
            </div>
            <button v-if="xlsxFile" class="upc-rm" @click.stop="xlsxFile=null">✕</button>
          </div>

          <!-- Upload thứ 3: Báo cáo ngày (tùy chọn) -->
          <div class="sb-upload-divider"><span>Tùy chọn</span></div>
          <div class="sb-upload-card sb-upload-optional"
            @dragover.prevent @drop.prevent="drop($event,'daily')" @click="$refs.rDaily.click()">
            <input ref="rDaily" type="file" accept=".xlsx,.xls,.docx,.pdf" hidden @change="e=>dailyReportFile=e.target.files[0]||null"/>
            <div class="upc-icon">{{ dailyReportFile?'📅':'📆' }}</div>
            <div class="upc-info" :title="dailyReportFile ? dailyReportFile.name : ''">
              <div class="upc-label">Báo cáo ngày <span class="optional-badge">Tùy chọn</span></div>
              <div class="upc-val" :class="dailyReportFile?'ok':'empty'">
                {{ dailyReportFile ? dailyReportFile.name : 'Chọn file báo cáo ngày' }}
              </div>
              <div v-if="!dailyReportFile" class="upc-hint">Excel/Word – AI kiểm tra đầy đủ ngày báo cáo</div>
            </div>
            <button v-if="dailyReportFile" class="upc-rm" @click.stop="dailyReportFile=null">✕</button>
          </div>
          <!-- Date range cho báo cáo ngày -->
          <div v-if="dailyReportFile" class="daily-date-range">
            <div class="ddr-row">
              <label class="ddr-label">Từ ngày</label>
              <div class="ddr-input-wrap">
                <input type="text" v-model="ngayBD" class="ddr-input" placeholder="dd/mm/yyyy" maxlength="10"
                  @input="e => ngayBD = fmtDateInput(e.target.value)"/>
                <input type="date" class="ddr-date-hidden" ref="rDateBD"
                  @change="e => { if(e.target.value) { const [y,m,d]=e.target.value.split('-'); ngayBD=d+'/'+m+'/'+y } }"/>
                <button class="ddr-cal-btn" @click.prevent="$refs.rDateBD.showPicker?.()" title="Chọn ngày">📅</button>
              </div>
            </div>
            <div class="ddr-row">
              <label class="ddr-label">Đến ngày</label>
              <div class="ddr-input-wrap">
                <input type="text" v-model="ngayKT" class="ddr-input" placeholder="dd/mm/yyyy" maxlength="10"
                  @input="e => ngayKT = fmtDateInput(e.target.value)"/>
                <input type="date" class="ddr-date-hidden" ref="rDateKT"
                  @change="e => { if(e.target.value) { const [y,m,d]=e.target.value.split('-'); ngayKT=d+'/'+m+'/'+y } }"/>
                <button class="ddr-cal-btn" @click.prevent="$refs.rDateKT.showPicker?.()" title="Chọn ngày">📅</button>
              </div>
            </div>
            <div v-if="ngayBD && ngayKT && soNgayLamViec > 0" class="ddr-calc">
              📅 <b>{{ soNgayLamViec }}</b> ngày làm việc (đã trừ T7, CN)
            </div>
          </div>


          <p v-if="tried&&(!docxFile||!xlsxFile)" class="sb-err">{{ t('need_2_files') }}</p>

          <button class="sb-btn-primary" :disabled="loading" @click="inputMode==='scan'?doScan():doReview()">
            <span v-if="loading" class="spinner"></span>
            <svg v-else width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
            {{ loading ? (inputMode==='scan'? scanMsg : t('analyzing')) : (inputMode==='scan' ? t('scan_analyze_btn') : t('analyze_btn')) }}
          </button>
        </div>

        <!-- Scan sidebar summary -->
        <div v-if="scanStep===2" class="sb-section">
          <div class="sb-section-title">📊 {{ t('scan_result') }}</div>
          <div v-if="scanPhieuResult" class="sb-result-block">
            <div class="srb-title">📋 {{ evalType==='hoc_viec' ? '🎓 Học việc' : '🎯 Thử việc' }}</div>
            <div class="srb-badge" :class="scanPhieuResult.mau_de_xuat==='green'?'srb-green':scanPhieuResult.mau_de_xuat==='red'?'srb-red':'srb-amber'">{{ scanPhieuResult.de_xuat || '...' }}</div>
          </div>
          <div v-if="scanMonths.length" class="sb-result-block">
            <div class="srb-title">📊 {{ t('scan_sxkd') }}</div>
            <div v-for="(m,i) in scanMonths" :key="i" class="srb-month">
              <span class="srb-month-label">{{ extractMonth(m.tieu_de) }}</span>
              <span class="srb-kq">{{ m.ty_le_dat_ket_qua || '—' }}</span>
            </div>
          </div>
          <button class="sb-btn-eval" :disabled="loadingEval" @click="sendScanToEval">
            <span v-if="loadingEval" class="spinner"></span>
            <svg v-else width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
            {{ loadingEval ? t('scan_sending') : 'Xác nhận & Đánh giá' }}
          </button>
          <div v-if="evalError" class="sb-err">{{ evalError }}</div>
          <button class="sb-btn-ghost" @click="resetScan">{{ t('scan_reset') }}</button>
        </div>

        <!-- Results summary in sidebar -->
        <div v-if="result" class="sb-section">
          <div class="sb-section-title">{{ t('result') }}</div>
          <div class="sb-badge" :class="result.status==='ĐẠT'?'badge-pass':'badge-fail'">
            <div class="badge-icon">{{ result.status==='ĐẠT'?'✓':'!' }}</div>
            <div class="badge-text">{{ result.status==='ĐẠT'?(store.lang==='en'?'Passed':'Hồ sơ đạt yêu cầu'):(store.lang==='en'?'Needs Update':'Cần bổ sung thêm') }}</div>
          </div>
          <div class="sb-counts">
            <div class="sc"><div class="sc-val warn">{{ result.van_de?.length ?? 0 }}</div><div class="sc-lbl">{{ t('issues') }}</div></div>
            <div class="sc"><div class="sc-val ok">{{ result.xlsx_kpi?.filter(r=>r.status==='OK').length??0 }}</div><div class="sc-lbl">{{ t('kpi_pass') }}</div></div>
            <div class="sc"><div class="sc-val bad">{{ (result.xlsx_kpi?.filter(r=>r.status==='THIẾU').length??0)+(result.xlsx_kpi?.filter(r=>r.status==='CẢNH BÁO').length??0) }}</div><div class="sc-lbl">{{ t('kpi_miss') }}</div></div>
          </div>
          <button class="sb-btn-secondary" @click="exportReport">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            {{ t('export_pdf') }}
          </button>
        </div>
      </div>
    </aside>

    <!-- MAIN RESULT PANEL -->
    <main class="result-panel">
      <!-- Welcome screen -->
      <div v-if="!result && !loading && scanStep!==2" class="welcome">
        <div class="welcome-icon">
          <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
            <rect width="48" height="48" rx="16" fill="url(#wg)"/>
            <text x="24" y="32" text-anchor="middle" font-size="22">🎯</text>
            <defs><linearGradient id="wg" x1="0" y1="0" x2="48" y2="48"><stop stop-color="#6366f1"/><stop offset="1" stop-color="#8b5cf6"/></linearGradient></defs>
          </svg>
        </div>
        <h1>{{ t('welcome_tv') }}</h1>
        <p>{{ t('welcome_tv_desc') }}</p>
        <div class="welcome-features">
          <div class="wf"><div class="wf-icon">📝</div><div>{{ t('tv_f1') }}</div></div>
          <div class="wf"><div class="wf-icon">📊</div><div>{{ t('tv_f2') }}</div></div>
          <div class="wf"><div class="wf-icon">📅</div><div>{{ t('tv_f3') }}</div></div>
        </div>
      </div>

      <!-- Scan Loading -->
      <div v-if="loading && inputMode==='scan'" class="loading-screen">
        <div class="loading-rings">
          <div class="ring ring-1"></div>
          <div class="ring ring-2"></div>
          <div class="ring-center">🤖</div>
        </div>
        <p class="loading-msg">{{ scanMsg }}</p>
        <div class="loading-tasks">
          <div class="lt" :class="scanPhieuDone?'lt-done':(loading?'lt-running':'')">
            <span class="lt-icon">{{ scanPhieuDone?'✅':(loading && docxFile?'⏳':'⬜') }}</span>
            {{ t('scan_task_phieu') }}
          </div>
          <div class="lt" :class="scanSxkdDone?'lt-done':(loading?'lt-running':'')">
            <span class="lt-icon">{{ scanSxkdDone?'✅':(loading && xlsxFile?'⏳':'⬜') }}</span>
            {{ t('scan_task_sxkd') }}
          </div>
        </div>
      </div>

      <!-- Scan Results (2 tabs) -->
      <div v-if="scanStep===2 && !loading" class="results-scroll ocr-review-screen">
        <!-- Tab Switcher -->
        <div v-if="scanPhieuResult && scanMonths.length" class="scan-tabs">
          <button class="scan-tab" :class="{active: scanTab==='phieu'}" @click="scanTab='phieu'">
            📋 {{ t('scan_phieu_tab') }}
          </button>
          <button class="scan-tab" :class="{active: scanTab==='sxkd'}" @click="scanTab='sxkd'">
            📊 {{ t('scan_sxkd_tab') }}
          </button>
        </div>

        <!-- Phiếu results -->
        <template v-if="scanPhieuResult && (scanTab==='phieu' || !scanMonths.length)">
          <div class="phieu-doc">
            <div class="phieu-title">PHIỀU ĐÁNH GIÁ HOÀN THÀNH {{ evalType==='hoc_viec' ? 'HỌC VIỆC' : 'THỬ VIỆC' }}</div>
            <div class="phieu-subtitle">CT Group – CTG-GO-NLCD-QT16-BM01</div>

            <div class="phieu-section-head">A. THÔNG TIN CHUNG</div>
            <table class="phieu-table">
              <thead><tr>
                <th style="width:28%">Nội dung</th><th>CBNV được đánh giá</th>
              </tr></thead>
              <tbody>
                <tr><td class="pl">Họ và tên</td><td><input class="pe-input" v-model="scanEf.ho_ten"/></td></tr>
                <tr><td class="pl">Mã NV</td><td><input class="pe-input" v-model="scanEf.ma_nhan_su"/></td></tr>
                <tr><td class="pl">Chức danh</td><td><input class="pe-input" v-model="scanEf.chuc_danh"/></td></tr>
                <tr><td class="pl">Đơn vị</td><td><input class="pe-input" v-model="scanEf.phong_ban"/></td></tr>
                <tr><td class="pl">Ngày nhận việc</td><td><input class="pe-input" v-model="scanEf.ngay_nhan_viec"/></td></tr>
                <tr><td class="pl">Ngày hết hạn TV</td><td><input class="pe-input" v-model="scanEf.ngay_het_han"/></td></tr>
              </tbody>
            </table>

            <div class="phieu-section-head">PHẦN II: KẾT QUẢ KPI</div>
            <table class="phieu-table">
              <thead><tr><th>Tuần</th><th style="width:90px">% KPI (NV)</th></tr></thead>
              <tbody>
                <tr v-for="i in nTuan" :key="'kpi'+i">
                  <td class="pl">Tuần thứ {{ i }}</td>
                  <td><input class="pe-input" style="text-align:center" v-model="scanEf['kpi_tuan_'+i+'_ty_le']"/></td>
                </tr>
                <tr style="background:rgba(99,102,241,.06)">
                  <td class="pl" style="font-weight:700">TBC KPI (bình quân {{ nTuan }} tuần)</td>
                  <td><input class="pe-input" style="text-align:center;font-weight:700" v-model="scanEf.diem_tbc_kpi_nv"/></td>
                </tr>
              </tbody>
            </table>

            <div class="phieu-section-head">1.6. CÔNG VIỆC ĐƯỢC GIAO &amp; KẾT QUẢ</div>
            <table class="phieu-table">
              <thead><tr>
                <th>Nhiệm vụ được giao &amp; Kết quả thực tế đạt được</th>
                <th style="width:130px">% Hoàn thành từng nhiệm vụ</th>
              </tr></thead>
              <tbody><tr>
                <td><textarea class="pe-ta" v-model="scanEf.cong_viec_duoc_giao" rows="10"></textarea></td>
                <td style="vertical-align:top;padding:6px 8px;min-width:120px">
                  <div v-for="(cv, ci) in cvList" :key="'cv'+ci" class="cv-pct-row">
                    <span class="cv-pct-num">{{ ci+1 }}</span>
                    <input class="pe-input cv-pct-input" v-model="cv.ty_le" :placeholder="`NV${ci+1} %`"/>
                    <button class="cv-rm-btn" @click="cvList.splice(ci,1)" title="Xoá">✕</button>
                  </div>
                  <div class="cv-pct-total-row">
                    <span class="cv-pct-num" style="color:#6366f1;font-weight:800">Σ</span>
                    <input class="pe-input cv-pct-input" style="font-weight:800;color:#6366f1" v-model="scanEf.ty_le_hoan_thanh_16" placeholder="Tổng %"/>
                  </div>
                  <button class="cv-add-btn" @click="addCvRow">+ Thêm</button>
                </td>
              </tr></tbody>
            </table>

            <!-- Sản phẩm dynamic tuần -->
            <div class="phieu-section-head">2. SẢN PHẨM NGHIỆM THU ({{ nTuan }} TUẦN)</div>
            <div v-for="i in nTuan" :key="'sp'+i" class="sp-card" :class="{' sp-empty': !scanEf[`san_pham_${i}`] && !scanEf[`kpi_sp_tuan_${i}`]}">
              <div class="sp-head">
                Tuần {{ i }}
                <span class="sp-kpi" :class="kpiClass(scanEf[`kpi_sp_tuan_${i}`])">{{ scanEf[`kpi_sp_tuan_${i}`] || '—' }}</span>
                <span v-if="!scanEf[`san_pham_${i}`]" class="sp-missing-badge">⚠ Thiếu sản phẩm</span>
              </div>
              <table class="phieu-table" style="margin-top:6px">
                <tbody>
                  <tr><td class="pl" style="width:24%">Sản phẩm</td><td colspan="2"><textarea class="pe-ta" :class="{' pe-warn': !scanEf[`san_pham_${i}`]}" v-model="scanEf[`san_pham_${i}`]" rows="2" :placeholder="`Tuần ${i}: Nhập mô tả sản phẩm...`"></textarea></td></tr>
                  <tr><td class="pl">Số lượng file</td><td><input class="pe-input" v-model="scanEf[`so_luong_file_${i}`]" style="width:80px" placeholder="0"/></td><td class="pl" style="width:30%">% KPI: <input class="pe-input" :class="{' pe-warn': !scanEf[`kpi_sp_tuan_${i}`]}" v-model="scanEf[`kpi_sp_tuan_${i}`]" style="width:60px;display:inline" placeholder="0%"/></td></tr>
                  <tr><td class="pl">🔗 Link đính kèm</td><td colspan="2"><textarea class="pe-ta" style="color:#60a5fa;font-family:monospace;font-size:.78rem" v-model="scanEf[`link_dinh_kem_${i}`]" rows="2"></textarea></td></tr>
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
                  <td><textarea class="pe-ta" v-model="scanEf[r.nvKey]" rows="2"></textarea></td>
                  <td><textarea v-if="r.hodKey" class="pe-ta pe-hod" v-model="scanEf[r.hodKey]" rows="2"></textarea></td>
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
                      Ký HĐ: <input class="pe-input pe-hod" v-model="scanEf.de_xuat_ky_hd" @click.stop placeholder="HĐNV 4 tháng..."/>
                      <input class="pe-input" v-model="scanEf.de_xuat_tang_thu_nhap" @click.stop placeholder="Tăng thu nhập..." style="margin-top:4px"/>
                    </span>
                    <span v-else-if="row.id==='rtd'">
                      Ý kiến RTD: <textarea class="pe-ta" v-model="scanEf.y_kien_rtd" @click.stop rows="2"></textarea>
                    </span>
                    <span v-else>{{ row.de_xuat }}</span>
                  </td>
                  <td v-if="row.id==='dat'" rowspan="4">
                    <textarea class="pe-ta" v-model="scanEf.de_nghi_phoi_hop" @click.stop rows="8"></textarea>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>

        <!-- SXKD results -->
        <template v-if="scanMonths.length && (scanTab==='sxkd' || !scanPhieuResult)">
          <div class="section-sep">
            <div class="sep-line"></div>
            <div class="sep-label sep-sxkd">📊 Kế Hoạch SXKD Tháng</div>
            <div class="sep-line"></div>
          </div>

          <div v-for="(m, mi) in scanMonths" :key="mi" class="sxkd-month-block">
            <div class="sxkd-doc">
              <div class="sxkd-title">{{ m.tieu_de }}</div>
              <div class="sxkd-section-label">BẢNG KẾ HOẠCH VÀ KẾT QUẢ CÔNG VIỆC</div>
              <div class="sxkd-table-wrap">
                <table class="sxkd-table">
                  <thead>
                    <tr class="sth">
                      <th rowspan="2" class="th-stt">STT</th>
                      <th rowspan="2" class="th-mang">CÁC MẢNG CÔNG TÁC</th>
                      <th rowspan="2" class="th-mota">MÔ TẢ SẢN PHẨM</th>
                      <th colspan="3" class="thg th-kh">KẾ HOẠCH</th>
                      <th colspan="3" class="thg th-kq">KẾT QUẢ</th>
                      <th rowspan="2" class="th-link">LINK SP</th>
                    </tr>
                    <tr class="sth">
                      <th class="ths">TỶ TRỌNG</th><th class="ths">KPI</th><th class="ths">BOD</th>
                      <th class="ths th-kq-col">TỶ LỆ KPI</th><th class="ths th-kq-col">KQ KPI</th><th class="ths th-kq-col">BOD</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="cv in m.cong_viec" :key="mi+'-'+cv.stt" class="sxkd-row">
                      <td class="td-stt">{{ cv.stt }}</td>
                      <td class="td-mang"><input class="sc-input" v-model="cv.mang_cong_tac"/></td>
                      <td class="td-mota"><textarea class="sc-ta" v-model="cv.mo_ta_san_pham" rows="4"></textarea></td>
                      <td class="td-num"><input class="sc-input tc" v-model="cv.ty_trong"/></td>
                      <td class="td-num"><input class="sc-input tc" v-model="cv.kpi_ke_hoach"/></td>
                      <td class="td-bod"><input class="sc-input" v-model="cv.bod_ke_hoach"/></td>
                      <td class="td-num kqc"><input class="sc-input tc" v-model="cv.ty_le_kpi_ket_qua"/></td>
                      <td class="td-num kqc"><input class="sc-input tc kqb" v-model="cv.ket_qua_kpi"/></td>
                      <td class="td-bod kqc"><input class="sc-input" v-model="cv.bod_ket_qua"/></td>
                      <td class="td-link"><textarea class="sc-ta link-ta" v-model="cv.link_san_pham" rows="3"></textarea></td>
                    </tr>
                    <tr class="total-row">
                      <td colspan="3" class="total-label">TỶ LỆ ĐẠT</td>
                      <td class="td-num tc">{{ m.ty_le_dat_ke_hoach || '100%' }}</td>
                      <td colspan="2"></td>
                      <td colspan="2" class="td-num tc kqb">{{ m.ty_le_dat_ket_qua }}</td>
                      <td colspan="2"></td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <!-- Nội quy -->
              <template v-if="m.noi_quy && m.noi_quy.length">
                <div class="sxkd-section-label" style="margin-top: 24px;">NỘI QUY BẮT BUỘC</div>
                <div style="color: #64748b; font-size: .85rem; margin-bottom: 8px;">(Vi phạm sẽ bị khấu trừ KPI)</div>
                <div class="sxkd-table-wrap">
                  <table class="sxkd-table">
                    <thead><tr class="sth"><th class="th-stt">STT</th><th>NỘI DUNG</th><th class="ths" style="width:12%">KẾ HOẠCH</th><th class="ths" style="width:12%">KẾT QUẢ</th><th style="width:15%">XÁC NHẬN</th><th style="width:15%">GHI CHÚ</th></tr></thead>
                    <tbody>
                      <tr v-for="(nq, idx) in m.noi_quy" :key="'nq'+idx" class="sxkd-row">
                        <td class="td-stt">{{ nq.stt || idx+1 }}</td>
                        <td><input class="sc-input" v-model="nq.noi_dung" /></td>
                        <td class="td-num tc"><input class="sc-input tc" v-model="nq.ke_hoach" /></td>
                        <td class="td-num tc kqc"><input class="sc-input tc" v-model="nq.ket_qua" /></td>
                        <td><input class="sc-input" v-model="nq.xac_nhan" /></td>
                        <td><input class="sc-input" v-model="nq.ghi_chu" /></td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </template>

              <!-- Chỉ đạo -->
              <template v-if="m.chi_dao && m.chi_dao.length">
                <div class="sxkd-section-label" style="margin-top: 24px;">CHỈ ĐẠO CỦA BAN LÃNH ĐẠO (Nếu có)</div>
                <div class="sxkd-table-wrap">
                  <table class="sxkd-table">
                    <thead><tr class="sth"><th class="th-stt">STT</th><th>NỘI DUNG CHỈ ĐẠO</th><th style="width:20%">KẾT QUẢ THỰC HIỆN</th><th style="width:20%">BOD XÉT DUYỆT</th><th style="width:20%">GHI CHÚ</th></tr></thead>
                    <tbody>
                      <tr v-for="(cd, idx) in m.chi_dao" :key="'cd'+idx" class="sxkd-row">
                        <td class="td-stt">{{ cd.stt || idx+1 }}</td>
                        <td><input class="sc-input" v-model="cd.noi_dung" /></td>
                        <td><input class="sc-input" v-model="cd.ket_qua" /></td>
                        <td><input class="sc-input" v-model="cd.bod_xet_duyet" /></td>
                        <td><input class="sc-input" v-model="cd.ghi_chu" /></td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </template>

              <!-- Xét duyệt -->
              <template v-if="m.xet_duyet">
                <div class="sxkd-section-label" style="margin-top: 24px; color: #1e293b;">PHẦN TRÌNH VÀ XÉT DUYỆT</div>
                <table style="width: 100%; border-collapse: collapse; margin-bottom: 10px; border-radius: 8px; overflow: hidden; border: 1px solid #cbd5e1;">
                  <thead><tr style="background: #f1f5f9; text-align: left;"><th style="padding: 10px 12px; border-bottom: 1px solid #cbd5e1; border-right: 1px solid #cbd5e1; color: #475569; font-size: .85rem;">XÉT DUYỆT</th><th style="padding: 10px 12px; border-bottom: 1px solid #cbd5e1; border-right: 1px solid #cbd5e1; color: #475569; font-size: .85rem;">Ý KIẾN</th><th style="padding: 10px 12px; border-bottom: 1px solid #cbd5e1; width: 120px; color: #475569; font-size: .85rem;">Ranking</th></tr></thead>
                  <tbody>
                    <tr>
                      <td style="padding: 10px 12px; border-right: 1px solid #cbd5e1; border-bottom: 1px solid #cbd5e1; font-weight: 600;">HOD</td>
                      <td style="padding: 0; border-right: 1px solid #cbd5e1; border-bottom: 1px solid #cbd5e1;"><input class="sc-input" style="padding: 10px 12px;" v-model="m.xet_duyet.hod_y_kien" /></td>
                      <td rowspan="2" style="padding: 0; vertical-align: middle;"><input class="sc-input tc" style="height: 100%; min-height: 80px; font-weight: bold; font-size: 1.2rem; color: #10b981;" v-model="m.xet_duyet.ranking" /></td>
                    </tr>
                    <tr>
                      <td style="padding: 10px 12px; border-right: 1px solid #cbd5e1; font-weight: 600;">BOD</td>
                      <td style="padding: 0; border-right: 1px solid #cbd5e1;"><input class="sc-input" style="padding: 10px 12px;" v-model="m.xet_duyet.bod_y_kien" /></td>
                    </tr>
                  </tbody>
                </table>
              </template>
            </div>
          </div>
        </template>
      </div>

      <!-- Default Loading -->
      <div v-if="loading && inputMode!=='scan'" class="loading-screen">
        <div class="loading-spinner"></div>
        <p>{{ store.lang==='en'?'AI is analyzing profile...':`AI đang phân tích hồ sơ ${evalType==='hoc_viec'?'học việc':'thử việc'}...` }}</p>
        <p class="loading-sub">{{ store.lang==='en'?'This might take 30-60 seconds':'Quá trình này có thể mất 30–60 giây' }}</p>
      </div>

      <!-- Error -->
      <div v-if="error" class="error-card">
        <div class="error-icon">❌</div>
        <p>{{ error }}</p>
      </div>

      <!-- Results (default mode) -->
      <div v-if="result && !loading" class="results-scroll">
        <!-- From-scan banner -->
        <div v-if="fromScan" class="from-scan-banner">
          <span class="fs-icon">🔍</span>
          <div>
            <div class="fs-title">Kết quả từ Scan OCR</div>
            <div class="fs-sub">Dữ liệu được trích xuất từ ScanCombined và phân tích bởi AI</div>
          </div>
        </div>
        <!-- Overview -->
        <div class="result-card rc-overview" :class="result.status==='ĐẠT'?'rc-pass':'rc-fail'">
          <div class="rc-status">
            <span class="rc-badge-big">{{ result.status==='ĐẠT'?(store.lang==='en'?'✓ PASS':'✓ ĐẠT'):(store.lang==='en'?'✗ FAIL':'✗ CHƯA ĐẠT') }}</span>
          </div>
          <p class="rc-summary">{{ result.tong_quan }}</p>
        </div>

        <!-- Issues -->
        <div v-if="result.van_de?.length" class="result-card">
          <div class="rc-header rc-h-warn" @click="toggle('issues')">
            <span>⚠️ {{ result.van_de.length }} {{ store.lang==='en'?'issues found':'vấn đề cần bổ sung' }}</span>
            <span class="rc-arrow" :class="{open:sec.issues}">›</span>
          </div>
          <div v-if="sec.issues" class="rc-body">
            <div v-for="(v,vi) in result.van_de" :key="vi" class="issue-item">
              <div class="ii-tags">
                <span class="ii-tag" :class="v.loai==='WORD'?'tag-word':v.loai==='EXCEL'?'tag-excel':'tag-chung'">{{ v.loai }}</span>
                <span v-if="v.nhom_tieu_chi" class="ii-tag tag-criteria">{{ v.nhom_tieu_chi }}</span>
                <span class="ii-section">{{ v.muc }}</span>
              </div>
              <div class="ii-problem">{{ v.van_de }}</div>
              <div class="ii-fix"><strong>→ {{ store.lang==='en'?'Action required:':'Cần làm:' }}</strong> {{ v.yeu_cau }}</div>
            </div>
          </div>
        </div>

        <!-- KPI Table -->
        <div v-if="result.xlsx_kpi?.length" class="result-card">
          <div class="rc-header rc-h-blue" @click="toggle('kpi')">
            <span>📊 {{ store.lang==='en'?'KPI Table':'Bảng KPI' }} – {{ result.xlsx_kpi.length }} {{ store.lang==='en'?'items':'mục' }}</span>
            <div class="kpi-pills">
              <span class="kp ok">{{ result.xlsx_kpi.filter(r=>r.status==='OK').length }} {{ store.lang==='en'?'pass':'đạt' }}</span>
              <span class="kp miss">{{ result.xlsx_kpi.filter(r=>r.status==='THIẾU').length }} {{ store.lang==='en'?'miss':'thiếu' }}</span>
            </div>
            <span class="rc-arrow" :class="{open:sec.kpi}">›</span>
          </div>
          <div v-if="sec.kpi" class="rc-body">
            <div v-for="r in result.xlsx_kpi" :key="r.stt" class="kpi-item" :class="r.status==='THIẾU'?'ki-miss':r.status==='CẢNH BÁO'?'ki-warn':'ki-ok'">
              <div class="ki-row1">
                <span class="ki-stt">{{ r.stt }}</span>
                <span class="ki-name">{{ r.cong_viec }}</span>
                <span class="ki-chip" :class="r.status==='OK'?'kc-ok':r.status==='CẢNH BÁO'?'kc-warn':'kc-miss'">{{ r.status }}</span>
              </div>
              <div class="ki-row2">
                <span>{{ store.lang==='en'?'Ratio':'Tỷ lệ' }}: <b>{{ r.ty_le_thuc_hien!=null?(r.ty_le_thuc_hien*100).toFixed(0)+'%':'—' }}</b></span>
                <span>{{ store.lang==='en'?'Result':'KQ' }}: <b>{{ r.ket_qua||'—' }}</b></span>
                <span v-if="r.link_minh_chung?.startsWith('http')"><a :href="r.link_minh_chung" target="_blank" class="ki-lnk">🔗 {{ store.lang==='en'?'Evidence':'Minh chứng' }}</a></span>
                <span v-else-if="r.link_minh_chung" class="ki-lnk-ok">✅ {{ r.link_minh_chung?.slice(0,30) }}</span>
                <span v-else class="ki-no-lnk">❌ {{ store.lang==='en'?'Missing':'Chưa có' }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Strengths -->
        <div v-if="result.uu_diem?.length" class="result-card">
          <div class="rc-header rc-h-green" @click="toggle('good')">
            <span>✅ {{ result.uu_diem.length }} {{ store.lang==='en'?'Strengths':'điểm tốt' }}</span>
            <span class="rc-arrow" :class="{open:sec.good}">›</span>
          </div>
          <div v-if="sec.good" class="rc-body">
            <ul class="good-list">
              <li v-for="(g,gi) in result.uu_diem" :key="gi">{{ g }}</li>
            </ul>
            <div v-if="result.luu_y_chung" class="note-box">📌 {{ result.luu_y_chung }}</div>
          </div>
        </div>

        <!-- 2AS Analysis -->
        <div v-if="result.phan_tich_2as?.length" class="result-card">
          <div class="rc-header rc-h-2as" @click="toggle('as2')">
            <span>🔍 Phân tích theo tiêu chí 2AS – {{ result.phan_tich_2as.length }} tiêu chí</span>
            <div class="kpi-pills">
              <span class="kp ok">{{ result.phan_tich_2as.filter(t=>t.ket_qua==='ĐẠT').length }} đạt</span>
              <span class="kp miss">{{ result.phan_tich_2as.filter(t=>t.ket_qua!=='ĐẠT').length }} cần xem</span>
            </div>
            <span class="rc-arrow" :class="{open:sec.as2}">›</span>
          </div>
          <div v-if="sec.as2" class="rc-body">
            <div v-for="tc in result.phan_tich_2as" :key="tc.ma" class="tc2as-item"
              :class="tc.ket_qua==='ĐẠT'?'tc-ok':tc.ket_qua==='CẦN BỔ SUNG'?'tc-warn':'tc-fail'">
              <div class="tc2as-header">
                <span class="tc2as-ma">{{ tc.ma }}</span>
                <span class="tc2as-name">{{ tc.tieu_chi }}</span>
                <span class="tc2as-badge" :class="tc.ket_qua==='ĐẠT'?'tb-ok':tc.ket_qua==='CẦN BỔ SUNG'?'tb-warn':'tb-fail'">{{ tc.ket_qua }}</span>
              </div>
              <div class="tc2as-nhanxet">{{ tc.nhan_xet }}</div>
            </div>
          </div>
        </div>

        <!-- 2AS Warnings -->
        <div v-if="result.canh_bao_2as?.length" class="result-card">
          <div class="rc-header rc-h-warn2" @click="toggle('warn2as')">
            <span>⚠️ Cảnh báo 2AS – {{ result.canh_bao_2as.length }} lưu ý</span>
            <span class="rc-arrow" :class="{open:sec.warn2as}">›</span>
          </div>
          <div v-if="sec.warn2as" class="rc-body">
            <ul class="warn2as-list">
              <li v-for="(w,wi) in result.canh_bao_2as" :key="wi">⚠️ {{ w }}</li>
            </ul>
          </div>
        </div>

        <!-- ── Đề xuất xử lý ────────────────────────────────────── -->
        <div v-if="result" class="result-card dexuat-card">
          <div class="rc-header rc-h-dexuat" @click="toggle('dexuat')">
            <span>📋 Đề xuất xử lý {{ evalType==='hoc_viec' ? 'học việc' : 'thử việc' }}</span>
            <span v-if="aiDx?.ket_qua_tv" class="dx-chip" :class="deXuatChipCls">{{ aiDx.ket_qua_tv }}</span>
            <span class="rc-arrow" :class="{open:sec.dexuat}">›</span>
          </div>
          <div v-if="sec.dexuat" class="rc-body dexuat-body">

            <!-- Cảnh báo thời hạn hồ sơ (AI) -->
            <div v-if="aiHan?.tinh_trang && aiHan.tinh_trang !== 'Không xác định'"
              class="dxg-deadline"
              :class="aiHan.tinh_trang==='Đã trễ hạn'?'dl-overdue':aiHan.tinh_trang.includes('Sắp')?'dl-urgent':'dl-ok'">
              <span class="dxg-dl-icon">{{ aiHan.tinh_trang==='Đã trễ hạn'?'🔴':aiHan.tinh_trang.includes('Sắp')?'🟠':'🟢' }}</span>
              <div>
                <div class="dxg-dl-title">{{ aiHan.tinh_trang }}<span v-if="aiHan.ngay_het_han" style="margin-left:8px;font-weight:400;font-size:.8rem">· Hết hạn: {{ aiHan.ngay_het_han }}</span></div>
                <div class="dxg-dl-sub">{{ aiHan.mo_ta }}</div>
              </div>
            </div>

            <!-- Kết quả TV & Mức độ (AI) -->
            <div class="dx-ai-row">
              <div class="dx-ai-block">
                <div class="dxg-label">Kết quả {{ evalType==='hoc_viec' ? 'học việc' : 'thử việc' }} (2AS đề xuất)</div>
                <div class="dx-ai-badge" :class="aiDx?.ket_qua_tv?.includes('Đạt')?'dxb-pass':aiDx?.ket_qua_tv?.includes('Gia hạn')?'dxb-extend':'dxb-fail'">
                  {{ aiDx?.ket_qua_tv?.includes('Đạt') ? '✅' : aiDx?.ket_qua_tv?.includes('Gia hạn') ? '🔄' : '❌' }}
                  {{ aiDx?.ket_qua_tv || '—' }}
                </div>
              </div>
              <div class="dx-ai-block">
                <div class="dxg-label">Mức độ đề xuất</div>
                <div class="dx-ai-badge" :class="aiDx?.muc_do?.includes('Đồng ý')?'md-pass':aiDx?.muc_do?.includes('Chưa')?'md-warn':aiDx?.muc_do?.includes('Cần')?'md-info':'md-fail'">
                  {{ aiDx?.muc_do || '—' }}
                </div>
              </div>
            </div>

            <!-- Lý do AI -->
            <div v-if="aiDx?.ly_do" style="margin-top:10px">
              <div class="dxg-label">Căn cứ / Lý do</div>
              <div class="dx-ly-do">{{ aiDx.ly_do }}</div>
            </div>

            <!-- Điểm mạnh & cần cải thiện -->
            <div class="dx-2col" style="margin-top:10px">
              <div v-if="aiDx?.diem_manh?.length">
                <div class="dxg-label">💪 Điểm mạnh</div>
                <ul class="dx-list dx-list-green">
                  <li v-for="d in aiDx.diem_manh" :key="d">{{ d }}</li>
                </ul>
              </div>
              <div v-if="aiDx?.diem_can_cai_thien?.length">
                <div class="dxg-label">🔧 Cần cải thiện</div>
                <ul class="dx-list dx-list-amber">
                  <li v-for="d in aiDx.diem_can_cai_thien" :key="d">{{ d }}</li>
                </ul>
              </div>
            </div>

          </div>
        </div>

        <!-- ── Bảng Tỷ Trọng + Chấm Điểm (AI gen) ─────────────── -->
        <div v-if="result?.bang_ty_trong?.tieu_chi?.length" class="result-card">
          <div class="rc-header rc-h-blue" @click="toggle('tytrong')">
            <span>📊 Bảng Tỷ Trọng Năng Lực – AI Chấm Điểm</span>
            <span v-if="result.bang_ty_trong.diem_tong" class="dx-chip" style="background:rgba(16,185,129,.12);color:#10b981">Điểm: {{ result.bang_ty_trong.diem_tong?.toFixed(1) }}</span>
            <span class="rc-arrow" :class="{open:sec.tytrong}">›</span>
          </div>
          <div v-if="sec.tytrong" class="rc-body">
            <table class="ty-trong-table">
              <thead>
                <tr><th style="width:40px">STT</th><th>Năng lực</th><th style="width:90px">Trọng số</th><th style="width:70px">Điểm</th></tr>
              </thead>
              <tbody>
                <tr v-for="(tc, i) in result.bang_ty_trong.tieu_chi" :key="i">
                  <td>{{ i+1 }}</td>
                  <td>{{ tc.ten }}</td>
                  <td>{{ typeof tc.trong_so === 'number' ? (tc.trong_so <= 1 ? (tc.trong_so*100).toFixed(0)+'%' : tc.trong_so.toFixed(0)+'%') : tc.trong_so }}</td>
                  <td><b>{{ tc.diem != null ? Number(tc.diem).toFixed(1) : '—' }}</b></td>
                </tr>
              </tbody>
              <tfoot>
                <tr class="ty-trong-total">
                  <td colspan="2"><b>ĐIỂM TỔNG</b></td>
                  <td><b>100%</b></td>
                  <td><b>{{ result.bang_ty_trong.diem_tong?.toFixed(1) ?? '—' }}</b></td>
                </tr>
              </tfoot>
            </table>
            <div v-if="result.bang_ty_trong.ghi_chu" class="ty-trong-note">📌 {{ result.bang_ty_trong.ghi_chu }}</div>
          </div>
        </div>

        <!-- ── Báo cáo ngày stats ────────────────────────────────── -->
        <div v-if="result?.bao_cao_ngay" class="result-card">
          <div class="rc-header rc-h-daily" @click="toggle('daily')">
            <span>📅 Báo cáo ngày</span>
            <span class="daily-progress-chip">{{ result.bao_cao_ngay.so_ngay_da_bc ?? '?' }}/{{ result.bao_cao_ngay.so_ngay_can_bc ?? '?' }} ngày</span>
            <span class="rc-arrow" :class="{open:sec.daily}">›</span>
          </div>
          <div v-if="sec.daily" class="rc-body">
            <div class="daily-bar-wrap">
              <div class="daily-bar">
                <div class="daily-bar-fill" :style="{width: Math.min(100,(result.bao_cao_ngay.so_ngay_da_bc||0)/(result.bao_cao_ngay.so_ngay_can_bc||1)*100)+'%'}"></div>
              </div>
              <span class="daily-bar-pct">{{ Math.round((result.bao_cao_ngay.so_ngay_da_bc||0)/(result.bao_cao_ngay.so_ngay_can_bc||1)*100) }}%</span>
            </div>
            <div class="daily-stats">
              <div v-if="result.bao_cao_ngay.so_ngay_du_hang_muc != null" class="ds-item ds-ok">✅ Đủ hạng mục: <b>{{ result.bao_cao_ngay.so_ngay_du_hang_muc }}</b> ngày</div>
              <div v-if="result.bao_cao_ngay.ngay_thieu_hang_muc?.length" class="ds-item ds-warn">⚠️ Thiếu hạng mục: <b>{{ result.bao_cao_ngay.ngay_thieu_hang_muc.length }}</b> ngày <span class="ds-dates">({{ result.bao_cao_ngay.ngay_thieu_hang_muc.join(', ') }})</span></div>
              <div v-if="result.bao_cao_ngay.ngay_thieu_bao_cao?.length" class="ds-item ds-bad">❌ Thiếu báo cáo: <b>{{ result.bao_cao_ngay.ngay_thieu_bao_cao.length }}</b> ngày <span class="ds-dates">({{ result.bao_cao_ngay.ngay_thieu_bao_cao.join(', ') }})</span></div>
            </div>
            <div v-if="result.bao_cao_ngay.nhan_xet" class="ty-trong-note">📌 {{ result.bao_cao_ngay.nhan_xet }}</div>
          </div>
        </div>

        <!-- ── Đánh giá đề xuất của Quản lý ─────────────────────── -->
        <div v-if="result?.danh_gia_quan_ly" class="result-card">
          <div class="rc-header" :class="result.danh_gia_quan_ly.hop_ly ? 'rc-h-green' : 'rc-h-warn'" @click="toggle('quanly')">
            <span>👔 Đánh giá đề xuất quản lý</span>
            <span class="dx-chip" :class="result.danh_gia_quan_ly.hop_ly ? 'chip-pass' : 'chip-extend'">{{ result.danh_gia_quan_ly.muc_do_dong_y || (result.danh_gia_quan_ly.hop_ly ? '✅ Đồng ý' : '⚠️ Cần xem xét') }}</span>
            <span class="rc-arrow" :class="{open:sec.quanly}">›</span>
          </div>
          <div v-if="sec.quanly" class="rc-body">
            <!-- Đề xuất gốc của quản lý -->
            <div class="dx-ai-row">
              <div class="dx-ai-block" style="flex:2">
                <div class="dxg-label">Đề xuất của Quản lý / TBP / HOD</div>
                <div class="dx-ly-do" style="font-weight:600;font-style:italic;color:#1e3a5f">{{ result.danh_gia_quan_ly.de_xuat_quan_ly || '—' }}</div>
              </div>
              <div class="dx-ai-block" style="flex:1">
                <div class="dxg-label">Mức độ đồng ý</div>
                <div class="dx-ai-badge" :class="result.danh_gia_quan_ly.hop_ly ? 'dxb-pass' : 'dxb-fail'">
                  {{ result.danh_gia_quan_ly.muc_do_dong_y || (result.danh_gia_quan_ly.hop_ly ? '✅ Đồng ý hoàn toàn' : '⚠️ Không đồng ý') }}
                </div>
              </div>
            </div>
            <!-- Lý do chính -->
            <div v-if="result.danh_gia_quan_ly.ly_do_chinh" style="margin-top:10px;padding:10px 12px;background:#f0f9ff;border-left:3px solid #0ea5e9;border-radius:6px">
              <div class="dxg-label">Lý do chính</div>
              <div class="dx-ly-do" style="font-weight:600;color:#0c4a6e">{{ result.danh_gia_quan_ly.ly_do_chinh }}</div>
            </div>
            <!-- Phân tích chi tiết -->
            <div v-if="result.danh_gia_quan_ly.phan_tich_chi_tiet" style="margin-top:10px">
              <div class="dxg-label">Phân tích chi tiết</div>
              <div class="dx-ly-do" style="line-height:1.75;color:#374151">{{ result.danh_gia_quan_ly.phan_tich_chi_tiet }}</div>
            </div>
            <!-- Nhận xét tổng thể -->
            <div v-if="result.danh_gia_quan_ly.nhan_xet" style="margin-top:10px;padding:10px 12px;background:#f8fafc;border-radius:6px;border:1px solid #e2e8f0">
              <div class="dxg-label">Nhận xét của chuyên gia</div>
              <div class="dx-ly-do" style="color:#334155">{{ result.danh_gia_quan_ly.nhan_xet }}</div>
            </div>
            <!-- Khuyến nghị xử lý -->
            <div v-if="result.danh_gia_quan_ly.khuyen_nghi_xu_ly" style="margin-top:10px;padding:10px 12px;background:#fefce8;border-left:3px solid #eab308;border-radius:6px">
              <div class="dxg-label">Khuyến nghị xử lý</div>
              <div class="dx-ly-do" style="font-weight:600;color:#78350f">{{ result.danh_gia_quan_ly.khuyen_nghi_xu_ly }}</div>
            </div>
          </div>
        </div>

        <!-- ── Việc cần làm tiếp theo (AI) ──────────────────────── -->
        <div v-if="result" class="result-card nextstep-card">
          <div class="rc-header rc-h-next" @click="toggle('next')">
            <span>✅ Việc cần làm tiếp theo</span>
            <span class="ns-count">{{ nextStepsAI.filter(s=>!s.done).length }} chưa xong</span>
            <span class="rc-arrow" :class="{open:sec.next}">›</span>
          </div>
          <div v-if="sec.next" class="rc-body">
            <div v-for="(s, si) in nextStepsAI" :key="si" class="ns-item" :class="{done:s.done,'ns-urgent-item':s.urgent}" @click="s.done=!s.done">
              <span class="ns-num">{{ si+1 }}</span>
              <div style="flex:1">
                <div class="ns-title">{{ s.title }}</div>
                <div v-if="s.mo_ta" class="ns-sub">{{ s.mo_ta }}</div>
              </div>
              <span v-if="s.urgent" class="ns-urgent">Gấp</span>
            </div>
            <div v-if="!nextStepsAI.length" class="ns-empty">AI chưa tạo danh sách việc cần làm</div>
            <div class="ns-footer">
              <button class="ns-reset" @click.stop="nextStepsAI.forEach(s=>s.done=false)">↺ Reset</button>
              <button class="ns-export" @click.stop="exportReport">⬇ Xuất báo cáo</button>
            </div>
          </div>
        </div>

        <!-- ── Gợi ý JD ── -->
        <JdGoiY
          v-if="result?.jd_goi_y"
          :jd="result.jd_goi_y"
          :expanded="sec.jd"
          @toggle="sec.jd = !sec.jd"
        />

      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import JdGoiY from '../components/JdGoiY.vue'
import { store, t } from '../store'

const docxFile = ref(null), xlsxFile = ref(null)
const evalType = ref('thu_viec')
const dailyReportFile = ref(null), ngayBD = ref(''), ngayKT = ref('')
const tried = ref(false), loading = ref(false)
const result = ref(null), error = ref('')
const fromScan = ref(false)
const inputMode = ref('default')
const sec = reactive({ issues: true, kpi: false, good: false, as2: false, warn2as: false, dexuat: true, next: true, tytrong: true, daily: true, quanly: true, jd: true })

// ── AI-generated output accessors ───────────────────────────────────
const aiDx = computed(() => result.value?.de_xuat_xu_ly || {})
const aiHan = computed(() => result.value?.canh_bao_han || {})
const nextStepsAI = ref([])

// ── Tính số ngày làm việc (trừ T7, CN) ────────────────────────────
// Parse dd/mm/yyyy hoặc yyyy-mm-dd → Date
function parseDMY(s) {
  if (!s) return null
  const m1 = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/)
  if (m1) return new Date(+m1[3], +m1[2] - 1, +m1[1])
  const m2 = s.match(/^(\d{4})-(\d{2})-(\d{2})$/)
  if (m2) return new Date(+m2[1], +m2[2] - 1, +m2[3])
  return null
}
// Auto-format khi gõ: thêm / sau dd và mm
function fmtDateInput(v) {
  const digits = v.replace(/\D/g, '').slice(0, 8)
  if (digits.length <= 2) return digits
  if (digits.length <= 4) return digits.slice(0,2) + '/' + digits.slice(2)
  return digits.slice(0,2) + '/' + digits.slice(2,4) + '/' + digits.slice(4)
}
const soNgayLamViec = computed(() => {
  const start = parseDMY(ngayBD.value)
  const end = parseDMY(ngayKT.value)
  if (!start || !end || end < start) return 0
  let count = 0
  const cur = new Date(start)
  while (cur <= end) {
    const dow = cur.getDay() // 0=CN, 6=T7
    if (dow !== 0 && dow !== 6) count++
    cur.setDate(cur.getDate() + 1)
  }
  return count
})


// ── Check sessionStorage on mount (from ScanCombined) ───────────────────
onMounted(() => {
  const raw = sessionStorage.getItem('scan_eval_result')
  if (raw) {
    try {
      const r = JSON.parse(raw)
      result.value = r
      fromScan.value = true
      loadNextSteps(r)
      sec.issues = true; sec.kpi = false; sec.good = false; sec.as2 = false
      sec.warn2as = false; sec.dexuat = true; sec.next = true
    } catch(e) { /* ignore */ }
    sessionStorage.removeItem('scan_eval_result')
  }
})

const deXuatChipCls = computed(() => {
  const v = aiDx.value?.ket_qua_tv || ''
  if (v.includes('Đạt')) return 'chip-pass'
  if (v.includes('Gia hạn')) return 'chip-extend'
  if (v.includes('Không')) return 'chip-fail'
  return ''
})

function loadNextSteps(r) {
  if (!r) return
  const raw = r.viec_can_lam || []
  nextStepsAI.value = raw.map(item => ({ ...item, done: false }))
}

function drop(e, t) {
  const f = e.dataTransfer.files[0]
  if (!f) return
  const n = f.name.toLowerCase()
  if (t==='docx' && (n.endsWith('.docx') || n.endsWith('.pdf'))) docxFile.value = f
  if (t==='xlsx' && (n.endsWith('.xlsx') || n.endsWith('.pdf'))) xlsxFile.value = f
  if (t==='daily') dailyReportFile.value = f
}
function toggle(k) { sec[k] = !sec[k] }

// ── Scan state ──────────────────────────────────────────────
const scanStep = ref(0)
const scanTab = ref('phieu')
const scanMsg = ref('')
const scanPhieuResult = ref(null)
const scanPhieuDone = ref(false)
const scanSxkdDone = ref(false)
const scanSessionId = ref('')
const scanMonths = ref([])
const scanShared = ref({ noi_quy: [], chi_dao: [], xet_duyet: { hod_y_kien:'', bod_y_kien:'', ranking:'' } })
const scanEf = reactive({
  ho_ten:'', ma_nhan_su:'', chuc_danh:'', phong_ban:'',
  ngay_nhan_viec:'', ngay_het_han:'',
  kpi_tuan_1_ty_le:'', kpi_tuan_2_ty_le:'', kpi_tuan_3_ty_le:'', kpi_tuan_4_ty_le:'',
  kpi_tuan_5_ty_le:'', kpi_tuan_6_ty_le:'', kpi_tuan_7_ty_le:'', kpi_tuan_8_ty_le:'',
  diem_tbc_kpi_nv:'', cong_viec_duoc_giao:'', ty_le_hoan_thanh_16:'',
  nhiem_vu_1_noi_dung:'', nhiem_vu_1_ket_qua:'', nhiem_vu_1_ty_le:'', nhiem_vu_1_hod:'',
  nhiem_vu_2_noi_dung:'', nhiem_vu_2_ket_qua:'', nhiem_vu_2_ty_le:'', nhiem_vu_2_hod:'',
  nhiem_vu_3_noi_dung:'', nhiem_vu_3_ket_qua:'', nhiem_vu_3_ty_le:'', nhiem_vu_3_hod:'',
  nhiem_vu_4_noi_dung:'', nhiem_vu_4_ket_qua:'', nhiem_vu_4_ty_le:'', nhiem_vu_4_hod:'',
  nhiem_vu_5_noi_dung:'', nhiem_vu_5_ket_qua:'', nhiem_vu_5_ty_le:'', nhiem_vu_5_hod:'',
  nhiem_vu_6_noi_dung:'', nhiem_vu_6_ket_qua:'', nhiem_vu_6_ty_le:'', nhiem_vu_6_hod:'',
  nhiem_vu_7_noi_dung:'', nhiem_vu_7_ket_qua:'', nhiem_vu_7_ty_le:'', nhiem_vu_7_hod:'',
  nhiem_vu_8_noi_dung:'', nhiem_vu_8_ket_qua:'', nhiem_vu_8_ty_le:'', nhiem_vu_8_hod:'',
  san_pham_1:'', so_luong_file_1:'', kpi_sp_tuan_1:'', link_dinh_kem_1:'',
  san_pham_2:'', so_luong_file_2:'', kpi_sp_tuan_2:'', link_dinh_kem_2:'',
  san_pham_3:'', so_luong_file_3:'', kpi_sp_tuan_3:'', link_dinh_kem_3:'',
  san_pham_4:'', so_luong_file_4:'', kpi_sp_tuan_4:'', link_dinh_kem_4:'',
  san_pham_5:'', so_luong_file_5:'', kpi_sp_tuan_5:'', link_dinh_kem_5:'',
  san_pham_6:'', so_luong_file_6:'', kpi_sp_tuan_6:'', link_dinh_kem_6:'',
  san_pham_7:'', so_luong_file_7:'', kpi_sp_tuan_7:'', link_dinh_kem_7:'',
  san_pham_8:'', so_luong_file_8:'', kpi_sp_tuan_8:'', link_dinh_kem_8:'',
  hoi_nhap_1_nv:'', hoi_nhap_1_hod:'', hoi_nhap_2_nv:'', hoi_nhap_2_hod:'',
  hoi_nhap_3_nv:'', hoi_nhap_3_hod:'', hoi_nhap_4_nv:'', hoi_nhap_4_hod:'',
  hoi_nhap_5_nv:'', hoi_nhap_5_hod:'', hoi_nhap_6_nv:'', hoi_nhap_6_hod:'',
  hoi_nhap_7_nv:'', hoi_nhap_7_hod:'', hoi_nhap_7_1_nv:'', hoi_nhap_7_1_hod:'',
  hoi_nhap_7_2_nv:'', hoi_nhap_7_2_hod:'', hoi_nhap_7_3_nv:'', hoi_nhap_7_3_hod:'',
  hoi_nhap_7_4_nv:'', hoi_nhap_7_4_hod:'', hoi_nhap_7_5_nv:'', hoi_nhap_7_5_hod:'',
  hoi_nhap_8_nv:'', hoi_nhap_8_hod:'', hoi_nhap_9_nv:'', hoi_nhap_9_hod:'',
  ket_luan:'', de_xuat_ky_hd:'', de_xuat_tang_thu_nhap:'', de_nghi_phoi_hop:'',
  y_kien_hod:'', y_kien_rtd:'', ngay_ky:'', ten_hod_ky:''
})

const nTuan = computed(() => {
  for (let t = 8; t >= 5; t--) {
    if (scanEf[`kpi_tuan_${t}_ty_le`] || scanEf[`san_pham_${t}`] || scanEf[`kpi_sp_tuan_${t}`]) return t
  }
  return 4
})

const cvList = ref([{ ty_le: '' }])

function addCvRow() { cvList.value.push({ ty_le: '' }) }
function syncCvRows() {
  // Ưu tiên đọc nhiem_vu_X_ty_le từ scan result (NV1→NV8)
  const rows = []
  for (let i = 1; i <= 8; i++) {
    const nd = scanEf[`nhiem_vu_${i}_noi_dung`]
    const tl = scanEf[`nhiem_vu_${i}_ty_le`]
    if (nd || tl) rows.push({ ty_le: tl || '' })
  }
  if (rows.length > 0) {
    cvList.value = rows
    return
  }
  // Fallback: đếm dòng "Nhiệm vụ X:" đầu dòng trong cong_viec_duoc_giao
  const text = scanEf.cong_viec_duoc_giao || ''
  const n = Math.max((text.match(/^\+?\s*Nhiệm\s*vụ\s*\d+\s*[:.\-]/gim) || []).length, 1)
  while (cvList.value.length < n) cvList.value.push({ ty_le: '' })
}

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
  const kl = (scanEf.ket_luan || '').toLowerCase()
  return [
    { id:'dat', ket_luan:'Ứng viên đạt yêu cầu', de_xuat:'Ký HĐ:', selected: kl.includes('đạt') && !kl.includes('không') },
    { id:'khdat', ket_luan:'Không đạt và không có khả năng khắc phục', de_xuat:'Kết thúc thử việc', selected: kl.includes('không đạt') && kl.includes('không có') },
    { id:'giahan', ket_luan:'Không đạt nhưng có thể khắc phục', de_xuat:'Gia hạn thử việc', selected: kl.includes('gia hạn') },
    { id:'rtd', ket_luan:'Không đạt tại đây nhưng phù hợp vị trí khác', de_xuat:'RTD phỏng vấn', selected: kl.includes('rtd') || kl.includes('vị trí khác') },
  ]
})

function selectKetLuan(r) { scanEf.ket_luan = r.ket_luan }
function kpiClass(v) { const n=parseFloat((v||'').replace('%','')); if(isNaN(n)) return ''; return n>=90?'kpi-green':n>=75?'kpi-amber':'kpi-red' }
const loadingEval = ref(false)
const evalError = ref('')

function extractMonth(t) { const m=(t||'').match(/TH[\u00c1A]NG\s+(\d+)/i); return m?`Th\u00e1ng ${m[1]}`:(t||'').slice(0,12)||'Th\u00e1ng ?' }

function populateScanEf(fields) {
  if (!fields) return
  Object.keys(scanEf).forEach(k => { if (k in fields) scanEf[k] = fields[k] ?? '' })
  if (Array.isArray(fields.cong_viec_list) && fields.cong_viec_list.length) {
    cvList.value = fields.cong_viec_list.map(c => ({ ty_le: c.ty_le || '' }))
  } else {
    syncCvRows()
  }
}

async function callScanApi(url, body) {
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

async function doScan() {
  tried.value = true
  if (!docxFile.value && !xlsxFile.value) return
  loading.value = true; error.value = ''
  scanPhieuDone.value = false; scanSxkdDone.value = false
  scanMsg.value = t('ocr_processing')

  const tasks = []

  if (docxFile.value) {
    const fd = new FormData()
    fd.append('scan_file', docxFile.value)
    fd.append('eval_type', evalType.value)
    tasks.push(
      callScanApi('/api/method/cnb_2as.api.scan_phieu.scan_extract', fd)
        .then(async d => {
          const sid = d.scan_session_id || ''
          const d2 = await callScanApi('/api/method/cnb_2as.api.scan_phieu.scan_analyze', JSON.stringify({ scan_session_id: sid, xml_input: d.xml_output || '' }))
          scanPhieuResult.value = d2
          scanSessionId.value = sid
          populateScanEf(d2.confirmed_fields || d.extracted_fields || {})
          scanPhieuDone.value = true
        })
        .catch(e => { error.value += `\nPhi\u1ebfu: ${e.message}` })
    )
  }

  if (xlsxFile.value) {
    const fd2 = new FormData(); fd2.append('file', xlsxFile.value)
    tasks.push(
      callScanApi('/api/method/cnb_2as.api.scan_sxkd.ocr_sxkd', fd2)
        .then(msg => {
          const raw = msg.months ?? (msg.data ? [msg.data] : [msg])
          scanMonths.value = raw.map(m => ({
            tieu_de: m.tieu_de||'', ho_ten: (m.ho_ten||'').replace(/H\u1ecd v\u00e0 t\u00ean:\s*/i,'').trim(),
            cong_viec: m.cong_viec||[], ty_le_dat_ke_hoach: m.ty_le_dat_ke_hoach||'100%', ty_le_dat_ket_qua: m.ty_le_dat_ket_qua||'',
            noi_quy: m.noi_quy||[], chi_dao: m.chi_dao||[], xet_duyet: m.xet_duyet||null
          }))
          const src = raw.find(m => m.noi_quy?.length) || raw[0] || {}
          scanShared.value = {
            noi_quy: src.noi_quy?.length ? src.noi_quy : [],
            chi_dao: src.chi_dao?.length ? src.chi_dao : [],
            xet_duyet: src.xet_duyet || { hod_y_kien:'', bod_y_kien:'', ranking:'' }
          }
          scanSxkdDone.value = true
        })
        .catch(e => { error.value += `\nSXKD: ${e.message}` })
    )
  }

  await Promise.all(tasks)
  loading.value = false
  scanStep.value = 2
}

async function sendScanToEval() {
  loadingEval.value = true; evalError.value = ''
  try {
    const payload = {
      ef: { ...scanEf },
      months: scanMonths.value,
      shared: scanShared.value,
      cv_list: cvList.value,
      eval_type: evalType.value,
      so_ngay_can_bc: soNgayLamViec.value || 0,
      ngay_bd: ngayBD.value ? (parseDMY(ngayBD.value)?.toISOString().slice(0,10) || ngayBD.value) : '',
      ngay_kt: ngayKT.value ? (parseDMY(ngayKT.value)?.toISOString().slice(0,10) || ngayKT.value) : '',
    }

    let fetchBody, fetchHeaders
    if (dailyReportFile.value) {
      // Có file → dùng FormData để backend parse .xlsx/.docx đúng cách
      const fd = new FormData()
      fd.append('ef', JSON.stringify(payload.ef))
      fd.append('months', JSON.stringify(payload.months))
      fd.append('shared', JSON.stringify(payload.shared))
      fd.append('cv_list', JSON.stringify(payload.cv_list))
      fd.append('eval_type', payload.eval_type)
      fd.append('so_ngay_can_bc', String(payload.so_ngay_can_bc))
      fd.append('ngay_bd', payload.ngay_bd)
      fd.append('ngay_kt', payload.ngay_kt)
      fd.append('daily_report_file', dailyReportFile.value)
      fetchBody = fd
      fetchHeaders = { 'X-Frappe-CSRF-Token': csrf() }
    } else {
      // Không có file → dùng JSON như cũ
      fetchBody = JSON.stringify(payload)
      fetchHeaders = { 'Content-Type': 'application/json', 'X-Frappe-CSRF-Token': csrf() }
    }

    const resp = await fetch(`${BASE}.review_from_scan`, {
      method: 'POST',
      headers: fetchHeaders,
      body: fetchBody,
    })
    const j = await resp.json()
    if (!resp.ok) throw new Error(j?.exception || j?.message || `HTTP ${resp.status}`)
    result.value = j.message ?? j
    fromScan.value = true
    loadNextSteps(result.value)  // populate viec_can_lam
    // Mở sections kết quả để user thấy ngay bên dưới form scan
    sec.dexuat = true; sec.next = true; sec.as2 = true
    sec.tytrong = true; sec.daily = !!(result.value?.bao_cao_ngay)
    // Giữ scanStep===2 để user vẫn thấy form scan và có thể sửa rồi đánh giá lại
  } catch(e) {
    evalError.value = e.message
  } finally {
    loadingEval.value = false
  }
}


async function exportReport() {
  const r = result.value; if (!r) return
  const _nvi = r.thong_tin_nhan_vien || {}
  const nv = {
    ten_nhan_vien: _nvi.ten_nhan_vien || scanEf.ho_ten || '—',
    ma_nhan_vien:  _nvi.ma_nhan_vien  || scanEf.ma_nhan_su || '—',
    chuc_danh:     _nvi.chuc_danh     || scanEf.chuc_danh || '—',
    don_vi:        _nvi.don_vi        || scanEf.phong_ban || '—',
    ngay_nhan_viec:_nvi.ngay_nhan_viec|| scanEf.ngay_nhan_viec || '—',
    ngay_het_han:  _nvi.ngay_het_han  || scanEf.ngay_het_han || '—',
  }
  const now = new Date().toLocaleDateString('vi-VN', { day:'2-digit', month:'2-digit', year:'numeric' })
  const nsSteps = nextStepsAI.value.map((s,i) =>
    `<tr><td style="padding:6px 8px;border:1px solid #e5e7eb;text-align:center">${i+1}</td>
     <td style="padding:6px 8px;border:1px solid #e5e7eb">${s.title}${s.mo_ta?'<br><small style="color:#6b7280">'+s.mo_ta+'</small>':''}</td>
     <td style="padding:6px 8px;border:1px solid #e5e7eb;text-align:center">${s.urgent?'Cao':''}</td>
     <td style="padding:6px 8px;border:1px solid #e5e7eb;text-align:center">${s.done?'X':''}</td></tr>`
  ).join('')

  // ── Phần 7 tiêu chí 2AS ──────────────────────────────────────────
  const tc2asHtml = (r.phan_tich_2as?.length) ? `
    <div style="page-break-inside:avoid">
    <h3 style="margin-top:28px;border-left:4px solid #555;padding-left:10px;font-size:15px;color:#111">
      Phân tích theo 7 Tiêu chí đánh giá 2AS
      <span style="font-size:12px;font-weight:400;color:#555;margin-left:8px">
        (${r.phan_tich_2as.filter(t=>t.ket_qua==='ĐẠT').length}/${r.phan_tich_2as.length} đạt)
      </span>
    </h3>
    <table style="width:100%;border-collapse:collapse;margin-bottom:16px;font-size:13px;page-break-inside:avoid">
      <thead><tr style="background:#eee">
        <th style="padding:8px 10px;border:1px solid #ccc;width:50px;text-align:center">#</th>
        <th style="padding:8px 10px;border:1px solid #ccc;width:20%">Tiêu chí</th>
        <th style="padding:8px 10px;border:1px solid #ccc">Nhận xét</th>
        <th style="padding:8px 10px;border:1px solid #ccc;width:95px;text-align:center">Kết quả</th>
      </tr></thead>
      <tbody>
        ${r.phan_tich_2as.map((tc,i)=>
          `<tr style="background:${i%2===0?'#f9f9f9':'#fff'};page-break-inside:avoid">
            <td style="padding:7px 10px;border:1px solid #ddd;text-align:center;font-weight:700">${tc.ma||i+1}</td>
            <td style="padding:7px 10px;border:1px solid #ddd;font-weight:600">${tc.tieu_chi||'—'}</td>
            <td style="padding:7px 10px;border:1px solid #ddd;line-height:1.6">${tc.nhan_xet||'—'}</td>
            <td style="padding:7px 10px;border:1px solid #ddd;text-align:center;font-weight:700;white-space:nowrap">${tc.ket_qua||'—'}</td>
          </tr>`
        ).join('')}
      </tbody>
    </table>
    </div>` : ''

  // ── Cảnh báo 2AS ─────────────────────────────────────────────────
  const canhBaoHtml = (r.canh_bao_2as?.length) ? `
    <div style="border:1px solid #ccc;border-radius:4px;padding:12px;margin-bottom:16px;page-break-inside:avoid">
      <div style="font-weight:700;margin-bottom:8px">Cảnh báo 2AS (${r.canh_bao_2as.length} lưu ý)</div>
      <ul style="margin:0;padding-left:20px">
        ${r.canh_bao_2as.map(w=>`<li style="margin-bottom:4px">${w}</li>`).join('')}
      </ul>
    </div>` : ''

  // ── Đề xuất xử lý ─────────────────────────────────────────────────
  const dx = r.de_xuat_xu_ly || {}
  const kqtv = dx.ket_qua_tv || ''
  const deXuatHtml = kqtv ? `
    <div style="page-break-inside:avoid">
    <h3 style="margin-top:24px;border-left:4px solid #555;padding-left:10px;font-size:15px;color:#111">Đề xuất xử lý</h3>
    <div style="border:1px solid #ccc;border-radius:4px;padding:14px;background:#f9f9f9">
      <div style="font-weight:800;font-size:15px">${kqtv}</div>
      ${dx.ly_do?`<div style="margin-top:8px">${dx.ly_do}</div>`:''}
      ${dx.diem_manh?.length?`<div style="margin-top:8px"><b>Điểm mạnh:</b><ul style="margin:4px 0 0 16px">${dx.diem_manh.map(d=>`<li>${d}</li>`).join('')}</ul></div>`:''}
      ${dx.diem_can_cai_thien?.length?`<div style="margin-top:6px"><b>Cần cải thiện:</b><ul style="margin:4px 0 0 16px">${dx.diem_can_cai_thien.map(d=>`<li>${d}</li>`).join('')}</ul></div>`:''}
    </div>
    </div>` : ''

  // ── Bảng Tỷ Trọng + Chấm Điểm ───────────────────────────────────────────────
  const ttData = r.bang_ty_trong || {}
  const bangTyTrongHtml = (ttData.tieu_chi?.length) ? `
    <div style="page-break-inside:avoid">
    <h3 style="margin-top:28px;border-left:4px solid #555;padding-left:10px;font-size:15px;color:#111">
      Bảng Tỷ Trọng Năng Lực – AI Chấm Điểm
      ${ttData.diem_tong != null ? `<span style="margin-left:10px;font-size:13px;border:1px solid #ccc;padding:2px 10px;border-radius:4px;font-weight:700">Điểm tổng: ${Number(ttData.diem_tong).toFixed(1)}</span>` : ''}
    </h3>
    <table style="width:100%;border-collapse:collapse;margin-bottom:16px;font-size:13px">
      <thead><tr style="background:#eee">
        <th style="padding:8px 10px;border:1px solid #ccc;width:40px;text-align:center">STT</th>
        <th style="padding:8px 10px;border:1px solid #ccc">Năng lực</th>
        <th style="padding:8px 10px;border:1px solid #ccc;width:90px;text-align:center">Trọng số</th>
        <th style="padding:8px 10px;border:1px solid #ccc;width:70px;text-align:center">Điểm</th>
      </tr></thead>
      <tbody>
        ${(ttData.tieu_chi||[]).map((tc,i)=>`<tr style="background:${i%2===0?'#f9f9f9':'#fff'}">
          <td style="padding:6px 10px;border:1px solid #ddd;text-align:center">${i+1}</td>
          <td style="padding:6px 10px;border:1px solid #ddd">${tc.ten||'—'}</td>
          <td style="padding:6px 10px;border:1px solid #ddd;text-align:center">${typeof tc.trong_so==='number'?(tc.trong_so<=1?(tc.trong_so*100).toFixed(0):tc.trong_so.toFixed(0))+'%':tc.trong_so||'—'}</td>
          <td style="padding:6px 10px;border:1px solid #ddd;text-align:center;font-weight:700">${tc.diem!=null?Number(tc.diem).toFixed(1):'—'}</td>
        </tr>`).join('')}
      </tbody>
      <tfoot><tr style="background:#eee;font-weight:700">
        <td colspan="2" style="padding:8px 10px;border:1px solid #ccc">ĐIỂM TỔNG</td>
        <td style="padding:8px 10px;border:1px solid #ccc;text-align:center">100%</td>
        <td style="padding:8px 10px;border:1px solid #ccc;text-align:center;font-size:16px">${ttData.diem_tong!=null?Number(ttData.diem_tong).toFixed(1):'—'}</td>
      </tr></tfoot>
    </table>
    ${ttData.ghi_chu?`<div style="border-left:3px solid #999;padding:6px 10px;font-size:12px;margin-bottom:8px">${ttData.ghi_chu}</div>`:''}
    </div>` : ''

  // ── Báo cáo ngày stats ────────────────────────────────────────────────
  const bc = r.bao_cao_ngay
  const baoCaoNgayHtml = bc ? `
    <div style="page-break-inside:avoid">
    <h3 style="margin-top:24px;border-left:4px solid #555;padding-left:10px;font-size:15px;color:#111">
      Báo cáo ngày
      <span style="margin-left:10px;font-size:12px;border:1px solid #ccc;padding:2px 8px;border-radius:4px">${bc.so_ngay_da_bc??'?'}/${bc.so_ngay_can_bc??'?'} ngày</span>
    </h3>
    <div style="border:1px solid #ccc;border-radius:4px;padding:14px;background:#f9f9f9">
      <div style="background:#fff;border:1px solid #ddd;border-radius:3px;height:10px;overflow:hidden;margin-bottom:10px">
        <div style="height:100%;background:#555;width:${Math.min(100,Math.round((bc.so_ngay_da_bc||0)/(bc.so_ngay_can_bc||1)*100))}%"></div>
      </div>
      ${bc.nhan_xet?`<div style="font-weight:600;margin-bottom:8px">${bc.nhan_xet}</div>`:''}
      ${bc.ngay_thieu_bao_cao?.length?`<div style="font-size:12px;margin-bottom:4px">Thiếu báo cáo: ${bc.ngay_thieu_bao_cao.join(', ')}</div>`:''}
      ${bc.ngay_thieu_hang_muc?.length?`<div style="font-size:12px;margin-bottom:8px">Thiếu hạng mục: ${bc.ngay_thieu_hang_muc.join(', ')}</div>`:''}
      ${bc.doi_chieu_cong_viec?.length ? `
        <div style="margin-top:10px">
          <div style="font-weight:700;font-size:13px;margin-bottom:6px">Đối chiếu nội dung báo cáo ngày vs Phiếu đánh giá</div>
          <table style="width:100%;border-collapse:collapse;font-size:12px">
            <thead><tr style="background:#eee">
              <th style="padding:6px 8px;border:1px solid #ccc">Hạng mục (Báo cáo ngày)</th>
              <th style="padding:6px 8px;border:1px solid #ccc;width:100px;text-align:center">Có trong phiếu</th>
              <th style="padding:6px 8px;border:1px solid #ccc">Ghi chú</th>
            </tr></thead>
            <tbody>
              ${bc.doi_chieu_cong_viec.map((d,i)=>{
                const ok = d.co_trong_phieu
                return `<tr style="background:${i%2===0?'#f5f5f5':'#fff'}">
                  <td style="padding:5px 8px;border:1px solid #ddd">${d.hang_muc||'—'}</td>
                  <td style="padding:5px 8px;border:1px solid #ddd;text-align:center;font-weight:700">${ok?'Có':'Không'}</td>
                  <td style="padding:5px 8px;border:1px solid #ddd">${d.ghi_chu||''}</td>
                </tr>`
              }).join('')}
            </tbody>
          </table>
        </div>` : ''}`
  + `</div>
    </div>` : ''

  // ── Đánh giá đề xuất Quản lý ─────────────────────────────────────────────
  const ql = r.danh_gia_quan_ly || {}
  const quanLyHtml = (ql.de_xuat_quan_ly || ql.nhan_xet || ql.phan_tich_chi_tiet) ? `
    <div style="page-break-inside:avoid">
    <h3 style="margin-top:24px;border-left:4px solid #555;padding-left:10px;font-size:15px;color:#111">
      Đánh giá đề xuất quản lý
      <span style="margin-left:8px;font-size:12px;border:1px solid #ccc;padding:2px 8px;border-radius:4px">
        ${ql.muc_do_dong_y || (ql.hop_ly!==false?'Đồng ý':'Cần xem xét')}
      </span>
    </h3>
    <div style="border:1px solid #ccc;border-radius:4px;padding:14px;background:#f9f9f9">
      ${ql.de_xuat_quan_ly?`<div style="font-weight:700;font-size:13px;font-style:italic;margin-bottom:8px;padding-bottom:8px;border-bottom:1px solid #ddd">
        <span style="font-size:11px;font-weight:600;font-style:normal;display:block;margin-bottom:2px;text-transform:uppercase;letter-spacing:.04em">Đề xuất của Quản lý / TBP / HOD</span>
        ${ql.de_xuat_quan_ly}
      </div>`:''}
      ${ql.ly_do_chinh?`<div style="margin-bottom:8px;padding:7px 10px;background:#fff;border-left:3px solid #999;border-radius:2px">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;margin-bottom:3px">Lý do chính</div>
        <div style="font-size:13px;font-weight:600">${ql.ly_do_chinh}</div>
      </div>`:''}
      ${ql.phan_tich_chi_tiet?`<div style="margin-bottom:8px">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;margin-bottom:3px">Phân tích chi tiết</div>
        <div style="font-size:13px;line-height:1.75">${ql.phan_tich_chi_tiet}</div>
      </div>`:''}
      ${ql.nhan_xet?`<div style="margin-bottom:8px;padding:7px 10px;background:#fff;border:1px solid #ddd;border-radius:2px">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;margin-bottom:3px">Nhận xét</div>
        <div style="font-size:13px;line-height:1.7">${ql.nhan_xet}</div>
      </div>`:''}
      ${ql.khuyen_nghi_xu_ly?`<div style="padding:7px 10px;background:#fff;border-left:3px solid #555;border-radius:2px">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;margin-bottom:3px">Khuyến nghị xử lý</div>
        <div style="font-size:13px;font-weight:600">${ql.khuyen_nghi_xu_ly}</div>
      </div>`:''}
    </div>
    </div>` : ''


  // ── Gợi ý JD ─────────────────────────────────────────────────────────
  const jd = r.jd_goi_y || {}
  const jdGoiYHtml = (jd.chuc_danh || jd.tom_tat) ? `
    <div style="page-break-inside:avoid;margin-top:28px">
    <h3 style="border-left:4px solid #333;padding-left:10px;font-size:15px;color:#111;margin-bottom:0">
      Gợi ý Mô tả Công việc (JD)
    </h3>
    <div style="border:1px solid #bbb;border-radius:4px;overflow:hidden;margin-top:10px">
      <!-- Header band -->
      <div style="background:#333;color:#fff;padding:10px 16px;display:flex;justify-content:space-between;align-items:center">
        <div>
          <div style="font-size:14px;font-weight:700;letter-spacing:.02em">${jd.chuc_danh||'—'}</div>
          ${jd.phong_ban?`<div style="font-size:11px;opacity:.8;margin-top:2px">${jd.phong_ban}</div>`:''}
        </div>
        ${jd.cap_bac?`<div style="font-size:11px;border:1px solid rgba(255,255,255,.5);padding:2px 10px;border-radius:3px">${jd.cap_bac}</div>`:''}
      </div>
      <!-- Body -->
      <div style="padding:16px;background:#fff">
        ${jd.tom_tat?`
          <p style="line-height:1.75;margin:0 0 16px;font-size:13px;color:#333;font-style:italic;border-bottom:1px solid #eee;padding-bottom:12px">${jd.tom_tat}</p>
        `:''}
        ${jd.nhiem_vu_chinh?.length?`
          <div style="margin-bottom:16px">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#555;margin-bottom:8px;padding-bottom:4px;border-bottom:1px solid #eee">Nhiệm vụ chính</div>
            <ol style="margin:0;padding-left:18px">
              ${jd.nhiem_vu_chinh.map((t,i)=>`<li style="margin-bottom:5px;font-size:13px;line-height:1.6">${t}</li>`).join('')}
            </ol>
          </div>
        `:''}`
  + `${jd.yeu_cau_nang_luc?.length?`
          <div style="margin-bottom:16px">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#555;margin-bottom:8px;padding-bottom:4px;border-bottom:1px solid #eee">Yêu cầu năng lực</div>
            <table style="width:100%;border-collapse:collapse;font-size:13px">
              ${jd.yeu_cau_nang_luc.map((y,i)=>`
                <tr style="background:${i%2===0?'#f9f9f9':'#fff'}">
                  <td style="padding:6px 10px;border:1px solid #e5e5e5;font-weight:600;width:120px;vertical-align:top">${y.loai}</td>
                  <td style="padding:6px 10px;border:1px solid #e5e5e5;line-height:1.6">${y.mo_ta}</td>
                </tr>`).join('')}
            </table>
          </div>
        `:''}`
  + `${(jd.yeu_cau_kinh_nghiem||jd.trinh_do_hoc_van)?`
          <div style="margin-bottom:8px">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#555;margin-bottom:8px;padding-bottom:4px;border-bottom:1px solid #eee">Yêu cầu khác</div>
            <div style="display:flex;gap:24px;font-size:13px">
              ${jd.yeu_cau_kinh_nghiem?`<div><b>Kinh nghiệm:</b> ${jd.yeu_cau_kinh_nghiem}</div>`:''}
              ${jd.trinh_do_hoc_van?`<div><b>Học vấn:</b> ${jd.trinh_do_hoc_van}</div>`:''}
            </div>
          </div>
        `:''}`
  + `${jd.ghi_chu?`
          <div style="margin-top:12px;padding:8px 12px;background:#f5f5f5;border-left:3px solid #999;font-size:12px;font-style:italic">${jd.ghi_chu}</div>
        `:''}`
  + `</div>
    </div>
    </div>` : ''

  const html = `<div style="font-family:'Segoe UI',Arial,sans-serif;font-size:14px;color:#111;max-width:860px;margin:0 auto;padding:40px">
    <h2 style="border-bottom:2px solid #333;padding-bottom:10px;color:#111">BÁO CÁO ĐÁNH GIÁ ${evalType.value==="hoc_viec"?"HỌC VIỆC":"THỬ VIỆC"}</h2>
    <p style="color:#555">CT Group · ${now}</p>
    <table style="width:100%;border-collapse:collapse;margin:16px 0">
      <tr><td style="padding:6px;background:#f5f5f5;width:130px;font-weight:600;border:1px solid #ddd">Họ tên</td><td style="padding:6px;border:1px solid #ddd">${nv.ten_nhan_vien||'—'}</td>
          <td style="padding:6px;background:#f5f5f5;width:130px;font-weight:600;border:1px solid #ddd">Mã NV</td><td style="padding:6px;border:1px solid #ddd">${nv.ma_nhan_vien||'—'}</td></tr>
      <tr><td style="padding:6px;background:#f5f5f5;font-weight:600;border:1px solid #ddd">Chức danh</td><td style="padding:6px;border:1px solid #ddd">${nv.chuc_danh||'—'}</td>
          <td style="padding:6px;background:#f5f5f5;font-weight:600;border:1px solid #ddd">Đơn vị</td><td style="padding:6px;border:1px solid #ddd">${nv.don_vi||'—'}</td></tr>
      <tr><td style="padding:6px;background:#f5f5f5;font-weight:600;border:1px solid #ddd">Ngày nhận việc</td><td style="padding:6px;border:1px solid #ddd">${nv.ngay_nhan_viec||'—'}</td>
          <td style="padding:6px;background:#f5f5f5;font-weight:600;border:1px solid #ddd">Thời hạn HĐ</td><td style="padding:6px;border:1px solid #ddd">${nv.ngay_het_han||'—'}</td></tr>
    </table>
    <h3 style="color:#111">Kết quả đánh giá: <span style="font-weight:800">${r.status}</span></h3>
    <p style="background:#f5f5f5;padding:12px;border-radius:4px;line-height:1.7;border:1px solid #ddd">${r.tong_quan||'—'}</p>

    ${tc2asHtml}
    ${canhBaoHtml}
    ${deXuatHtml}
    ${bangTyTrongHtml}
    ${baoCaoNgayHtml}
    ${quanLyHtml}
    ${jdGoiYHtml}

    <h3 style="margin-top:20px;color:#111">Việc cần làm tiếp theo</h3>
    <table style="width:100%;border-collapse:collapse">
      <thead><tr style="background:#eee">
        <th style="padding:6px 8px;border:1px solid #ccc;width:36px">#</th>
        <th style="padding:6px 8px;border:1px solid #ccc">Nội dung</th>
        <th style="padding:6px 8px;border:1px solid #ccc;width:70px">Ưu tiên</th>
        <th style="padding:6px 8px;border:1px solid #ccc;width:70px">Hoàn thành</th>
      </tr></thead><tbody>${nsSteps}</tbody></table>
    ${r.van_de?.length ? `<h3 style="margin-top:20px;color:#111">Vấn đề cần bổ sung (${r.van_de.length})</h3>${r.van_de.map(v=>`<div style="border:1px solid #ddd;border-radius:4px;padding:10px;margin-bottom:8px"><b>${v.muc}</b>: ${v.van_de}<br><i>→ ${v.yeu_cau}</i></div>`).join('')}` : ''}
  </div>`



  if (!window.html2pdf) {
    await new Promise((resolve,reject) => {
      const s = document.createElement('script')
      s.src = 'https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.2/html2pdf.bundle.min.js'
      s.onload = resolve; s.onerror = () => reject(new Error('Không tải được thư viện'))
      document.head.appendChild(s)
    })
  }
  const nvName = (nv.ten_nhan_vien||'NhanVien').replace(/\s+/g,'_')
  const worker = window.html2pdf().set({
    margin: [15, 18, 22, 18],
    filename: `BaoCao_${evalType.value==="hoc_viec"?"HocViec":"ThuViec"}_${nvName}_${new Date().toISOString().slice(0,10)}.pdf`,
    image: { type: 'jpeg', quality: .97 },
    html2canvas: { scale: 2, useCORS: true },
    jsPDF: { unit: 'mm', format: 'a4' },
    pagebreak: { mode: ['avoid-all', 'css', 'legacy'], avoid: ['div', 'table', 'tr', 'ul', 'li'] }
  })
  await worker.from(html).toPdf().get('pdf').then(pdf => {
    const total = pdf.internal.getNumberOfPages()
    const w = pdf.internal.pageSize.getWidth()
    const h = pdf.internal.pageSize.getHeight()
    // Remove blank trailing pages
    for (let p = total; p > 1; p--) {
      pdf.setPage(p)
      const pageText = pdf.internal.pages[p]
      // Check if page has minimal content (only page number footer or empty)
      const contentLines = Array.isArray(pageText) ? pageText.filter(l => typeof l === 'string' && l.trim().length > 0) : []
      if (contentLines.length <= 2) {
        pdf.deletePage(p)
      } else {
        break
      }
    }
    // Re-add page numbers after cleanup
    const finalTotal = pdf.internal.getNumberOfPages()
    for (let p = 1; p <= finalTotal; p++) {
      pdf.setPage(p)
      pdf.setFontSize(8)
      pdf.setTextColor(150)
      pdf.text(`Trang ${p} / ${finalTotal}`, w / 2, h - 6, { align: 'center' })
    }
  }).save()
}

function resetScan() {
  scanStep.value = 0; scanPhieuResult.value = null; scanMonths.value = []
  scanPhieuDone.value = false; scanSxkdDone.value = false; scanSessionId.value = ''
  Object.keys(scanEf).forEach(k => scanEf[k] = '')
}

function reloadPage() {
  window.location.reload()
}

const BASE = '/api/method/cnb_2as.api.thu_viec'
function csrf() {
  if (window.frappe?.csrf_token) return window.frappe.csrf_token
  const c = document.cookie.split('; ').find(r => r.startsWith('csrf_token='))?.split('=')[1]
  return c ? decodeURIComponent(c) : ''
}

async function doReview() {
  tried.value = true
  if (!docxFile.value || !xlsxFile.value) return
  loading.value = true; error.value = ''; result.value = null
  try {
    const fd = new FormData()
    fd.append('docx_file', docxFile.value)
    fd.append('xlsx_file', xlsxFile.value)
    fd.append('eval_type', evalType.value)
    if (dailyReportFile.value) fd.append('daily_report_file', dailyReportFile.value)
    if (ngayBD.value) fd.append('ngay_bd', ngayBD.value)
    if (ngayKT.value) fd.append('ngay_kt', ngayKT.value)
    if (soNgayLamViec.value > 0) fd.append('so_ngay_can_bc', String(soNgayLamViec.value))
    const r = await fetch(`${BASE}.review_files`, { method:'POST', body:fd, headers:{'X-Frappe-CSRF-Token':csrf()} })
    const j = await r.json()
    if (!r.ok) throw new Error(j?.exception || j?.message || `HTTP ${r.status}`)
    result.value = j.message ?? j
    loadNextSteps(result.value)
    sec.issues = true; sec.kpi = false; sec.good = false; sec.as2 = false; sec.warn2as = false
    sec.dexuat = true; sec.next = true
  } catch(e) { error.value = e.message }
  finally { loading.value = false }
}

</script>

<style scoped>
.app-layout { display: flex; height: 100vh; overflow: hidden }

/* ── SIDEBAR ── */
.sidebar { width: 340px; flex-shrink: 0; display: flex; flex-direction: column; overflow-y: auto; border-right: 1px solid rgba(0,0,0,.05); }
.sb-top { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 18px; border-bottom: 1px solid #e2e8f0; background: #fff }
.sidebar-header { display: flex; align-items: center; gap: 10px; width: 100%; }
.sb-title { flex: 1; min-width: 0; }
.sb-title-main { font-size: .88rem; font-weight: 700; }
.sb-title-sub { font-size: .72rem; color: #64748b; }
.sb-reload { width: 32px; height: 32px; border-radius: 8px; border: 1px solid #e2e8f0; background: #f8fafc; color: #64748b; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all .2s; }
.sb-reload:hover { background: #f1f5f9; color: #3b82f6; border-color: #cbd5e1; }
.sb-back { display: flex; align-items: center; justify-content: center; width: 32px; height: 32px; border-radius: 8px; background: #f1f5f9; color: #64748b; text-decoration: none; transition: all .2s; flex-shrink: 0 }
.sb-body { padding: 16px 16px; flex-grow: 1 }
.sb-section { margin-bottom: 20px }
.sb-section-title { font-size: .72rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: .08em; margin-bottom: 12px }

.sb-upload-card { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 10px; border: 1px dashed rgba(99,102,241,.3); background: rgba(99,102,241,.04); cursor: pointer; margin-bottom: 8px; transition: all .2s }
.sb-upload-card:hover { border-color: rgba(99,102,241,.5); background: rgba(99,102,241,.08) }
.sb-upload-card.filled { border-style: solid; border-color: rgba(34,197,94,.4); background: rgba(34,197,94,.08) }
.sb-upload-card.err { border-color: rgba(239,68,68,.4); background: rgba(239,68,68,.08) }
.upc-icon { font-size: 24px; flex-shrink: 0 }
.upc-info { flex-grow: 1; min-width: 0 }
.upc-label { font-size: .72rem; font-weight: 600; color: #94a3b8 }
.upc-hint { font-size: .65rem; color: #cbd5e1; margin-top: 2px; }
.upc-val { font-size: .8rem; color: #475569; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; display: block; field-sizing: content }
.upc-val.ok { color: #4ade80 }
.upc-rm { width: 24px; height: 24px; border: none; background: rgba(239,68,68,.15); color: #f87171; border-radius: 6px; cursor: pointer; font-size: .7rem; display: flex; align-items: center; justify-content: center }
.sb-err { font-size: .78rem; color: #f87171; margin: 4px 0 }

.sb-btn-primary { width: 100%; padding: 10px; border: none; border-radius: 10px; background: linear-gradient(135deg,#6366f1,#8b5cf6); color: #fff; font-weight: 600; font-size: .88rem; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; transition: opacity .2s; margin-top: 8px }
.sb-btn-primary:disabled { opacity: .5; cursor: not-allowed }
.sb-btn-primary:hover:not(:disabled) { opacity: .9 }
.sb-btn-secondary { width: 100%; padding: 9px; border: 1px solid rgba(99,102,241,.4); border-radius: 10px; background: transparent; color: #818cf8; font-weight: 600; font-size: .84rem; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; margin-top: 12px; transition: all .2s }
.sb-btn-secondary:hover { background: rgba(99,102,241,.1) }

.spinner { width: 16px; height: 16px; border: 2px solid rgba(255,255,255,.3); border-top-color: #fff; border-radius: 50%; animation: spin .6s linear infinite }
@keyframes spin { to { transform: rotate(360deg) } }

/* From-scan banner */
.from-scan-banner { display: flex; align-items: center; gap: 12px; padding: 10px 14px; border-radius: 11px; background: rgba(99,102,241,.08); border: 1px solid rgba(99,102,241,.2); margin-bottom: 16px; }
.fs-icon { font-size: 1.3rem; flex-shrink: 0; }
.fs-title { font-size: .84rem; font-weight: 700; color: #818cf8; }
.fs-sub { font-size: .72rem; color: #64748b; margin-top: 2px; }



.sb-badge { padding: 10px 14px; border-radius: 10px; display: flex; align-items: center; gap: 10px; margin-bottom: 12px }
.badge-pass { background: rgba(34,197,94,.1); border: 1px solid rgba(34,197,94,.25) }
.badge-fail { background: rgba(245,158,11,.1); border: 1px solid rgba(245,158,11,.25) }
.badge-icon { width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: .9rem }
.badge-pass .badge-icon { background: rgba(34,197,94,.2); color: #4ade80 }
.badge-fail .badge-icon { background: rgba(245,158,11,.2); color: #fbbf24 }
.badge-text { font-size: .84rem; font-weight: 600; }

.sb-counts { display: flex; gap: 8px; margin-bottom: 8px }
.sc { flex: 1; text-align: center; padding: 8px 4px; border-radius: 8px; background: rgba(255,255,255,.03) }
.sc-val { font-size: 1.2rem; font-weight: 800 }
.sc-val.warn { color: #fbbf24 }
.sc-val.ok { color: #4ade80 }
.sc-val.bad { color: #f87171 }
.sc-lbl { font-size: .68rem; color: #64748b; margin-top: 2px }

/* ── RESULT PANEL ── */
.result-panel { flex: 1; overflow-y: auto; }
.welcome { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; padding: 40px; text-align: center }
.welcome-icon { margin-bottom: 20px }
.welcome h1 { font-size: 1.5rem; font-weight: 800; margin-bottom: 10px }
.welcome p { max-width: 500px; color: #94a3b8; line-height: 1.6 }
.welcome-features { display: flex; gap: 20px; margin-top: 32px; flex-wrap: wrap; justify-content: center }
.wf { display: flex; align-items: center; gap: 8px; padding: 10px 16px; border-radius: 10px; background: rgba(99,102,241,.06); border: 1px solid rgba(99,102,241,.12); font-size: .84rem; color: #64748b; font-weight: 500 }
.wf-icon { font-size: 1.2rem }

.loading-screen { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; gap: 16px }
.loading-spinner { width: 40px; height: 40px; border: 3px solid rgba(99,102,241,.2); border-top-color: #6366f1; border-radius: 50%; animation: spin 1s linear infinite }
.loading-screen p { font-weight: 600 }
.loading-sub { font-weight: 400 !important; font-size: .84rem }
.error-card { margin: 24px; padding: 16px 20px; border-radius: 10px; background: rgba(239,68,68,.08); border: 1px solid rgba(239,68,68,.2); color: #f87171; display: flex; align-items: center; gap: 10px }
.error-icon { font-size: 1.2rem }

.results-scroll { padding: 24px; max-width: 900px; margin: 0 auto }
.ocr-review-screen { max-width: 100% !important; padding: 30px 40px !important; }
.th-mang { width: 16%; }
.th-mota { width: 34%; }
.result-card { border: 1px solid transparent; border-radius: 14px; margin-bottom: 16px; overflow: hidden }
.rc-overview { padding: 20px 24px }
.rc-pass { border-color: rgba(34,197,94,.3) !important; }
.rc-fail { border-color: rgba(245,158,11,.3) !important; }
.rc-status { margin-bottom: 10px }
.rc-badge-big { font-size: 1rem; font-weight: 800; padding: 6px 16px; border-radius: 8px }
.rc-pass .rc-badge-big { background: rgba(34,197,94,.1); color: #4ade80 }
.rc-fail .rc-badge-big { background: rgba(245,158,11,.1); color: #fbbf24 }
.rc-summary { line-height: 1.7; font-size: .92rem }

.rc-header { padding: 14px 20px; cursor: pointer; display: flex; align-items: center; gap: 10px; font-weight: 600; font-size: .9rem; transition: background .2s; user-select: none }
.rc-h-warn { color: #fbbf24 }
.rc-h-blue { color: #60a5fa }
.rc-h-green { color: #4ade80 }
.rc-arrow { font-size: 1.2rem; margin-left: auto; transition: transform .2s; color: #64748b }
.rc-arrow.open { transform: rotate(90deg) }
.rc-body { padding: 0 20px 16px; border-top: 1px solid transparent; }

.issue-item { padding: 12px 0; border-bottom: 1px solid transparent }
.issue-item:last-child { border-bottom: none }
.ii-tags { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 6px }
.ii-tag { font-size: .72rem; font-weight: 700; padding: 2px 8px; border-radius: 4px }
.tag-word { background: rgba(109,40,217,.15); color: #a78bfa }
.tag-excel { background: rgba(5,150,105,.15); color: #34d399 }
.tag-chung { background: rgba(245,158,11,.15); color: #fbbf24 }
.tag-criteria { background: rgba(99,102,241,.15); color: #818cf8 }
.ii-section { font-size: .78rem; color: #64748b }
.ii-problem { color: #fca5a5; font-size: .88rem; line-height: 1.6; margin-bottom: 4px }
.ii-fix { font-size: .85rem; line-height: 1.6 }
.ii-fix strong { color: #a78bfa }

.kpi-pills { display: flex; gap: 6px; margin-left: auto }
.kp { font-size: .72rem; font-weight: 700; padding: 2px 8px; border-radius: 99px }
.kp.ok { background: rgba(34,197,94,.12); color: #4ade80 }
.kp.miss { background: rgba(239,68,68,.12); color: #f87171 }

.kpi-item { padding: 10px 0; border-bottom: 1px solid transparent }
.kpi-item:last-child { border-bottom: none }
.ki-row1 { display: flex; align-items: center; gap: 8px; margin-bottom: 4px }
.ki-stt { font-size: .78rem; font-weight: 700; color: #64748b; min-width: 28px }
.ki-name { flex: 1; font-size: .88rem; }
.ki-chip { font-size: .7rem; font-weight: 700; padding: 2px 8px; border-radius: 99px }
.kc-ok { background: rgba(34,197,94,.12); color: #4ade80 }
.kc-warn { background: rgba(245,158,11,.12); color: #fbbf24 }
.kc-miss { background: rgba(239,68,68,.12); color: #f87171 }
.ki-row2 { display: flex; gap: 16px; font-size: .8rem; color: #94a3b8 }
.ki-lnk { color: #60a5fa; text-decoration: none }
.ki-lnk-ok { color: #4ade80 }
.ki-no-lnk { color: #f87171 }

.good-list { padding: 12px 0 12px 20px; color: #4ade80; line-height: 1.8; font-size: .88rem }
.good-list li { margin-bottom: 4px }
.note-box { margin-top: 10px; padding: 10px 14px; border-radius: 8px; background: rgba(245,158,11,.06); border: 1px solid rgba(245,158,11,.15); font-size: .84rem; color: #fbbf24; line-height: 1.6 }

/* Đề xuất xử lý */
.dexuat-card { border-color: rgba(99,102,241,.25) !important; }
.rc-h-dexuat { color: #a78bfa; }
.dexuat-body { padding-top: 8px; }
.dxg-label { font-size: .72rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: .06em; margin-bottom: 7px; }
.dxg-deadline { display: flex; align-items: flex-start; gap: 10px; padding: 10px 14px; border-radius: 9px; margin-bottom: 14px; }
.dl-overdue { background: rgba(239,68,68,.1); border: 1px solid rgba(239,68,68,.25); }
.dl-urgent  { background: rgba(245,158,11,.09); border: 1px solid rgba(245,158,11,.25); }
.dl-ok      { background: rgba(16,185,129,.07); border: 1px solid rgba(16,185,129,.2); }
.dxg-dl-icon { font-size: 1.2rem; flex-shrink: 0; margin-top: 1px; }
.dxg-dl-title { font-weight: 700; font-size: .88rem; }
.dxg-dl-sub { font-size: .78rem; color: #94a3b8; margin-top: 2px; }
.dx-chip { padding: 2px 9px; border-radius: 99px; font-size: .72rem; font-weight: 700; margin-left: auto; margin-right: 6px; }
.chip-pass   { background: rgba(34,197,94,.12); color: #4ade80; }
.chip-extend { background: rgba(245,158,11,.12); color: #fbbf24; }
.chip-fail   { background: rgba(239,68,68,.12); color: #f87171; }
/* AI display blocks */
.dx-ai-row { display: flex; gap: 14px; flex-wrap: wrap; margin-top: 10px; }
.dx-ai-block { flex: 1; min-width: 160px; }
.dx-ai-badge { display: inline-flex; align-items: center; gap: 7px; padding: 8px 14px; border-radius: 10px; font-weight: 700; font-size: .88rem; margin-top: 5px; border: 1.5px solid transparent; }
.dxb-pass   { background: rgba(34,197,94,.1);  border-color: rgba(34,197,94,.3);  color: #4ade80; }
.dxb-extend { background: rgba(245,158,11,.09); border-color: rgba(245,158,11,.3); color: #fbbf24; }
.dxb-fail   { background: rgba(239,68,68,.09);  border-color: rgba(239,68,68,.3);  color: #f87171; }
.md-pass    { background: rgba(34,197,94,.09);  border-color: rgba(34,197,94,.25);  color: #4ade80; }
.md-warn    { background: rgba(245,158,11,.08); border-color: rgba(245,158,11,.25); color: #fbbf24; }
.md-info    { background: rgba(99,102,241,.09); border-color: rgba(99,102,241,.25); color: #818cf8; }
.md-fail    { background: rgba(239,68,68,.08);  border-color: rgba(239,68,68,.25);  color: #f87171; }
.dx-ly-do { font-size: .85rem; color: #cbd5e1; line-height: 1.7; background: rgba(255,255,255,.03); border-radius: 8px; padding: 10px 12px; border-left: 3px solid rgba(99,102,241,.4); margin-top: 4px; }
.dx-2col { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.dx-list { margin: 4px 0 0 16px; padding: 0; }
.dx-list li { font-size: .82rem; line-height: 1.7; }
.dx-list-green li { color: #4ade80; }
.dx-list-amber li { color: #fbbf24; }


/* Next steps */
.nextstep-card { border-color: rgba(16,185,129,.2) !important; }
.rc-h-next { color: #34d399; }
.ns-count { font-size: .72rem; font-weight: 700; padding: 2px 8px; border-radius: 99px; background: rgba(16,185,129,.12); color: #34d399; margin-left: auto; margin-right: 6px; }
.ns-item { display: flex; align-items: flex-start; gap: 10px; padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,.05); cursor: pointer; transition: background .15s; border-radius: 6px; padding-left: 4px; }
.ns-item:hover { background: rgba(99,102,241,.04); }
.ns-item.done .ns-title { text-decoration: line-through; color: #64748b; }
.ns-num { min-width:20px;font-size:.85rem;font-weight:700;color:#374151;flex-shrink:0;margin-top:2px; }
.ns-item.done .ns-num { color:#94a3b8; }
.ns-title { font-size: .88rem; font-weight: 600; }
.ns-sub { font-size: .76rem; color: #64748b; margin-top: 2px; }
.ns-urgent { font-size: .7rem; font-weight: 700; padding: 2px 7px; border-radius: 99px; background: rgba(239,68,68,.1); color: #f87171; margin-left: auto; flex-shrink: 0; }
.ns-footer { display: flex; gap: 10px; margin-top: 14px; padding-top: 12px; border-top: 1px solid rgba(255,255,255,.06); }
.ns-reset { background: transparent; border: 1px solid rgba(255,255,255,.1); color: #64748b; border-radius: 7px; padding: 5px 12px; cursor: pointer; font-size: .78rem; transition: all .15s; }
.ns-reset:hover { color: #94a3b8; }
.ns-export { background: linear-gradient(135deg,#6366f1,#10b981); color: white; border: none; border-radius: 7px; padding: 5px 14px; cursor: pointer; font-size: .78rem; font-weight: 700; transition: opacity .15s; }
.ns-export:hover { opacity: .88; }


.rc-h-2as { color: #a78bfa }
.rc-h-warn2 { color: #fb923c }
.tc2as-item { padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,.05) }
.tc2as-item:last-child { border-bottom: none }
.tc2as-header { display: flex; align-items: center; gap: 8px; margin-bottom: 5px }
.tc2as-ma { font-size: .72rem; font-weight: 800; padding: 2px 7px; border-radius: 5px; background: rgba(139,92,246,.15); color: #a78bfa; min-width: 36px; text-align: center }
.tc2as-name { flex: 1; font-size: .88rem; font-weight: 600 }
.tc2as-badge { font-size: .7rem; font-weight: 700; padding: 2px 9px; border-radius: 99px }
.tb-ok { background: rgba(34,197,94,.12); color: #4ade80 }
.tb-warn { background: rgba(245,158,11,.12); color: #fbbf24 }
.tb-fail { background: rgba(239,68,68,.12); color: #ef4444 }
.tc2as-nhanxet { font-size: .83rem; color: #94a3b8; line-height: 1.6; padding-left: 44px }
.tc-ok .tc2as-name { color: #4ade80 }
.tc-warn .tc2as-name { color: #fbbf24 }
.tc-fail .tc2as-name { color: #ef4444 }
.warn2as-list { padding: 10px 0 10px 20px; color: #fb923c; line-height: 1.9; font-size: .87rem }
.warn2as-list li { margin-bottom: 4px }

/* Theme support for hints/files */
:global(body.theme-light) .upc-hint { color: #94a3b8; }
:global(body.theme-light) .ii-problem { color: #ef4444; }
:global(body.theme-light) .ii-fix strong { color: #6366f1; }

/* Mode toggle */
.mode-toggle { display: flex; gap: 4px; padding: 3px; background: rgba(99,102,241,.06); border-radius: 10px; border: 1px solid rgba(99,102,241,.12); }
.mode-btn { flex: 1; padding: 8px 10px; border: none; border-radius: 8px; background: transparent; color: #94a3b8; font-size: .76rem; font-weight: 600; cursor: pointer; transition: all .2s; display: flex; align-items: center; gap: 5px; justify-content: center; }
.mode-btn:hover { background: rgba(99,102,241,.08); color: #818cf8; }
.mode-btn.active { background: linear-gradient(135deg,#6366f1,#8b5cf6); color: #fff; box-shadow: 0 2px 8px rgba(99,102,241,.3); }
.mode-icon { font-size: 14px; }

/* Thin scrollbar */
.sidebar::-webkit-scrollbar, .result-panel::-webkit-scrollbar, .results-scroll::-webkit-scrollbar { width: 4px; }
.sidebar::-webkit-scrollbar-track, .result-panel::-webkit-scrollbar-track, .results-scroll::-webkit-scrollbar-track { background: transparent; }
.sidebar::-webkit-scrollbar-thumb, .result-panel::-webkit-scrollbar-thumb, .results-scroll::-webkit-scrollbar-thumb { background: rgba(99,102,241,.15); border-radius: 4px; }
.sidebar::-webkit-scrollbar-thumb:hover, .result-panel::-webkit-scrollbar-thumb:hover, .results-scroll::-webkit-scrollbar-thumb:hover { background: rgba(99,102,241,.3); }

/* Tab Switcher */
.scan-tabs { display:flex; gap:4px; padding:4px; background:rgba(99,102,241,.06); border-radius:12px; margin-bottom:20px; border:1px solid rgba(99,102,241,.12); }
.scan-tab { flex:1; padding:10px 16px; border:none; border-radius:9px; background:transparent; color:#94a3b8; font-size:.84rem; font-weight:600; cursor:pointer; transition:all .2s; display:flex; align-items:center; justify-content:center; gap:6px; }
.scan-tab:hover { background:rgba(99,102,241,.08); color:#818cf8; }
.scan-tab.active { background:#6366f1; color:#fff; box-shadow:0 2px 8px rgba(99,102,241,.3); }

/* Loading rings */
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
@keyframes spin { to { transform:rotate(360deg); } }

/* Separators */
.section-sep { display:flex; align-items:center; gap:14px; margin:24px 0 16px; }
.sep-line { flex:1; height:2px; background:linear-gradient(90deg,transparent,rgba(99,102,241,.25),transparent); }
.sep-label { font-size:.9rem; font-weight:800; text-transform:uppercase; letter-spacing:.07em; white-space:nowrap; padding:6px 18px; border-radius:20px; }
.sep-sxkd { color:#10b981; background:rgba(16,185,129,.07); border:1px solid rgba(16,185,129,.2); }

/* Phiếu document */
.phieu-doc { background:white; border-radius:14px; padding:24px; box-shadow:0 4px 20px rgba(0,0,0,.07); width: 100%; max-width:1400px; margin:0 auto; }
:global(body.theme-dark) .phieu-doc { background:#1a1a28; }
.phieu-title { text-align:center; font-size:1rem; font-weight:800; text-transform:uppercase; color:#1e293b; margin-bottom:4px; }
:global(body.theme-dark) .phieu-title { color:#f1f5f9; }
.phieu-subtitle { text-align:center; font-size:.8rem; color:#94a3b8; margin-bottom:18px; }
.phieu-section-head { background:linear-gradient(90deg,rgba(99,102,241,.15),rgba(99,102,241,.03)); border-left:3px solid #6366f1; padding:6px 12px; font-size:.75rem; font-weight:700; letter-spacing:.05em; color:#818cf8; text-transform:uppercase; margin:14px 0 6px; border-radius:0 6px 6px 0; }
.phieu-table { width:100%; border-collapse:collapse; margin-bottom:6px; font-size:.83rem; }
.phieu-table th { background:#f1f5f9; color:#374151; font-weight:700; padding:6px 9px; text-align:left; border:1px solid #d1d5db; font-size:.76rem; }
:global(body.theme-dark) .phieu-table th { background:#1e2030; color:#94a3b8; border-color:rgba(255,255,255,.08); }
.phieu-table td { padding:6px 9px; border:1px solid #e2e8f0; vertical-align:top; line-height:1.5; color:#1e293b; }
:global(body.theme-dark) .phieu-table td { border-color:rgba(255,255,255,.07); color:#e2e8f0; }

.pl { font-weight:600; color:#6366f1; white-space:nowrap; }
.pe-input { width:100%; box-sizing:border-box; background:rgba(99,102,241,.03); border:1.5px solid rgba(99,102,241,.18); border-radius:7px; color:#1e293b; font-size:.83rem; padding:5px 9px; outline:none; transition:border-color .18s,background .18s; font-family:inherit; field-sizing: content; }
:global(body.theme-dark) .pe-input { color:#e2e8f0; background:rgba(99,102,241,.06); border-color:rgba(99,102,241,.25); }

.pe-input:hover { border-color:rgba(99,102,241,.35); background:rgba(99,102,241,.05); }
.pe-input:focus { border-color:#6366f1; background:rgba(99,102,241,.07); box-shadow:0 0 0 3px rgba(99,102,241,.12); }
.pe-ta { width:100%; box-sizing:border-box; background:rgba(99,102,241,.03); border:1.5px solid rgba(99,102,241,.18); border-radius:7px; color:#1e293b; font-size:.83rem; padding:6px 9px; outline:none; resize:vertical; font-family:inherit; line-height:1.6; min-height:52px; field-sizing: content; }
:global(body.theme-dark) .pe-ta { color:#e2e8f0; background:rgba(99,102,241,.06); border-color:rgba(99,102,241,.25); }

.pe-ta:hover { border-color:rgba(99,102,241,.35); }
.pe-ta:focus { border-color:#6366f1; background:rgba(99,102,241,.07); box-shadow:0 0 0 3px rgba(99,102,241,.12); }

/* ── Missing field highlights ── */
.sp-card.sp-empty { border-color:rgba(239,68,68,.35) !important; background:rgba(239,68,68,.03) !important; }
.sp-missing-badge { display:inline-flex; align-items:center; gap:4px; margin-left:8px; padding:1px 8px; border-radius:20px; font-size:.68rem; font-weight:700; background:rgba(239,68,68,.12); color:#ef4444; }
.pe-warn { border-color:rgba(245,158,11,.5) !important; background:rgba(245,158,11,.04) !important; }
.pe-warn:focus { border-color:#f59e0b !important; background:rgba(245,158,11,.08) !important; box-shadow:0 0 0 3px rgba(245,158,11,.15) !important; }
.pe-warn::placeholder { color:rgba(245,158,11,.6); }

/* SXKD document */
.sxkd-month-block { margin-bottom:30px; }
.sxkd-doc { background:white; border-radius:12px; padding:22px; box-shadow:0 3px 16px rgba(0,0,0,.06); width:100%; max-width:1400px; margin:0 auto; }
:global(body.theme-dark) .sxkd-doc { background:#1a1a28; }
.sxkd-title { text-align:center; font-size:.95rem; font-weight:800; text-transform:uppercase; color:#1e293b; margin-bottom:10px; }
:global(body.theme-dark) .sxkd-title { color:#f1f5f9; }
.sxkd-section-label { font-size:.7rem; font-weight:800; text-transform:uppercase; letter-spacing:.06em; color:#6366f1; margin:14px 0 4px; }
.sxkd-table-wrap { overflow-x:auto; margin-bottom:4px; border-radius:8px; border:1.5px solid #e2e8f0; }
:global(body.theme-dark) .sxkd-table-wrap { border-color:rgba(255,255,255,.08); }
.sxkd-table { width:100%; border-collapse:collapse; min-width:860px; }
.sth th { background:#f1f5f9; font-size:.67rem; font-weight:700; text-transform:uppercase; padding:6px 7px; border:1px solid #d1d5db; color:#374151; text-align:center; }
:global(body.theme-dark) .sth th { background:#1e2030; color:#94a3b8; border-color:rgba(255,255,255,.07); }
.ths { font-size:.65rem !important; }
.thg { border-bottom:none !important; }
.th-kh { background:rgba(99,102,241,.07) !important; color:#6366f1 !important; }
.th-kq { background:rgba(16,185,129,.07) !important; color:#059669 !important; }
.sxkd-row td { border:1px solid #e2e8f0; padding:0; vertical-align:top; color:#1e293b; }
:global(body.theme-dark) .sxkd-row td { border-color:rgba(255,255,255,.06); color:#e2e8f0; }

.td-stt { width:30px; text-align:center; font-weight:700; color:#6366f1; padding:7px; vertical-align:middle; }
.td-mang { width:80px; } .td-mota { width:350px; } .td-num { width:62px; } .td-bod { width:70px; } .td-link { width:130px; }
.kqc { background:rgba(16,185,129,.03) !important; }
.kqb { font-weight:700 !important; color:#059669 !important; }
.tc { text-align:center !important; }
.total-row td { border:1px solid #e2e8f0; padding:7px; }
.total-label { text-align:center; font-weight:800; font-size:.8rem; background:#f8fafc; }
.sc-input { width:100%; border:none; background:transparent; outline:none; color:#1e293b; font-size:.78rem; padding:5px 7px; font-family:inherit; field-sizing: content; }
:global(body.theme-dark) .sc-input { color:#e2e8f0; }
.sc-input:focus { background:rgba(99,102,241,.04); }
.sc-ta { width:100%; border:none; background:transparent; outline:none; color:#1e293b; font-size:.77rem; padding:5px 7px; font-family:inherit; resize:vertical; min-height:65px; field-sizing: content; }
:global(body.theme-dark) .sc-ta { color:#e2e8f0; }
.sc-ta:focus { background:rgba(99,102,241,.04); }

.link-ta { font-size:.71rem; color:#6366f1; }

/* Sidebar scan summary */
.sb-result-block { padding:8px 10px; background:rgba(99,102,241,.05); border-radius:8px; margin-bottom:6px; border:1px solid rgba(99,102,241,.12); }
.srb-title { font-size:.78rem; font-weight:700; color:#818cf8; margin-bottom:4px; }
.srb-badge { font-size:.72rem; font-weight:700; padding:4px 10px; border-radius:6px; text-align:center; }
.srb-green { background:rgba(16,185,129,.15); color:#10b981; }
.srb-amber { background:rgba(245,158,11,.12); color:#f59e0b; }
.srb-red { background:rgba(239,68,68,.12); color:#ef4444; }
.srb-month { display:flex; align-items:center; gap:7px; padding:3px 0; font-size:.76rem; }
.srb-month-label { flex:1; font-weight:600; }
.srb-kq { color:#10b981; font-weight:700; }
.sb-btn-eval { width:100%; padding:10px; border-radius:10px; border:none; cursor:pointer; background:linear-gradient(135deg,#8b5cf6,#6366f1); color:white; font-weight:700; font-size:.84rem; display:flex; align-items:center; justify-content:center; gap:8px; margin-top:10px; transition:all .2s; }
.sb-btn-eval:hover:not(:disabled) { box-shadow:0 4px 14px rgba(139,92,246,.3); transform:translateY(-1px); }
.sb-btn-eval:disabled { opacity:.6; cursor:not-allowed; }
.sb-btn-ghost { width:100%; padding:8px; border-radius:8px; border:1px solid rgba(99,102,241,.2); background:transparent; color:#818cf8; font-weight:600; font-size:.78rem; cursor:pointer; margin-top:6px; transition:all .2s; }
.sb-btn-ghost:hover { background:rgba(99,102,241,.08); }

/* ── Dark theme overrides ── */
:global(body.theme-dark) .total-row td { border-color:rgba(255,255,255,.06); }
:global(body.theme-dark) .total-label { background:#1a1a28; color:#f1f5f9; }
:global(body.theme-dark) .scan-tabs { background:rgba(99,102,241,.1); border-color:rgba(99,102,241,.2); }
:global(body.theme-dark) .phieu-subtitle { color:#64748b; }
:global(body.theme-dark) .pe-input { background:rgba(99,102,241,.06); border-color:rgba(99,102,241,.25); }
:global(body.theme-dark) .pe-input:hover { background:rgba(99,102,241,.1); }
:global(body.theme-dark) .pe-input:focus { background:rgba(99,102,241,.12); }
:global(body.theme-dark) .pe-ta { background:rgba(99,102,241,.06); border-color:rgba(99,102,241,.25); }
:global(body.theme-dark) .pe-ta:hover { background:rgba(99,102,241,.1); }
:global(body.theme-dark) .pe-ta:focus { background:rgba(99,102,241,.12); }
:global(body.theme-dark) .app-layout { background: #0f0f1a; }
:global(body.theme-dark) .sidebar { background: #14141f; border-right-color: rgba(255,255,255,.06); }
:global(body.theme-dark) .sb-name { color: #f1f5f9; }
:global(body.theme-dark) .sb-top { background: #14141f; border-bottom-color: rgba(255,255,255,.06); }
:global(body.theme-dark) .sb-reload { background: transparent; border-color: rgba(255,255,255,.1); color: #94a3b8; }
:global(body.theme-dark) .sb-reload:hover { background: rgba(99,102,241,.1); color: #818cf8; }
:global(body.theme-dark) .sb-back { background: rgba(255,255,255,.05); color: #94a3b8; }
:global(body.theme-dark) .mode-btn { background: rgba(99,102,241,.06); border-color: rgba(99,102,241,.15); color: #94a3b8; }
:global(body.theme-dark) .mode-btn:hover { background: rgba(99,102,241,.12); color: #818cf8; }
:global(body.theme-dark) .mode-btn.active { background: linear-gradient(135deg,#6366f1,#8b5cf6); color: #fff; border-color: transparent; }
:global(body.theme-dark) .sb-upload-card { background: rgba(99,102,241,.05); border-color: rgba(99,102,241,.18); }
:global(body.theme-dark) .sb-upload-card.filled { background: rgba(99,102,241,.08); border-color: rgba(99,102,241,.3); }
:global(body.theme-dark) .upc-val { color: #cbd5e1; }
:global(body.theme-dark) .upc-hint { color: #64748b; }
:global(body.theme-dark) .sb-btn-secondary { background: transparent; color: #a5b4fc; border-color: rgba(99,102,241,.3); }
:global(body.theme-dark) .sc { background: rgba(99,102,241,.08); }
:global(body.theme-dark) .result-panel { background: #0f0f1a; }
:global(body.theme-dark) .welcome h1 { color: #f1f5f9; }
:global(body.theme-dark) .wf { background: rgba(99,102,241,.06); border-color: rgba(99,102,241,.15); color: #94a3b8; }
:global(body.theme-dark) .result-card { background: #14141f; border-color: rgba(255,255,255,.06); }
:global(body.theme-dark) .rc-header:hover { background: rgba(99,102,241,.06); }
/* ── Eval Type Toggle ──────────────────────────────── */
.eval-type-toggle { display: flex; gap: 6px; }
.etype-btn { flex: 1; padding: 7px 8px; border-radius: 8px; border: 1px solid rgba(99,102,241,.2); background: transparent; color: inherit; cursor: pointer; font-size: .82rem; font-weight: 600; transition: all .2s; }
.etype-btn:hover { background: rgba(99,102,241,.08); }
.etype-btn.active { background: linear-gradient(135deg,#6366f1,#8b5cf6); color: #fff; border-color: transparent; }

/* ── Daily Report Upload ───────────────────────────── */
.sb-upload-divider { display: flex; align-items: center; gap: 8px; margin: 10px 0 6px; }
.sb-upload-divider::before,.sb-upload-divider::after { content:''; flex:1; height:1px; background: rgba(99,102,241,.15); }
.sb-upload-divider span { font-size: .72rem; color: #94a3b8; font-weight: 600; letter-spacing: .05em; }
.sb-upload-optional { border-style: dashed !important; opacity: .9; }
.optional-badge { font-size: .65rem; padding: 1px 6px; border-radius: 99px; background: rgba(99,102,241,.12); color: #818cf8; font-weight: 600; margin-left: 4px; vertical-align: middle; }
.daily-date-range { background: rgba(99,102,241,.04); border: 1px solid rgba(99,102,241,.12); border-radius: 8px; padding: 10px 12px; margin-top: 6px; display: flex; flex-direction: column; gap: 6px; }
.ddr-row { display: flex; align-items: center; gap: 8px; }
.ddr-label { font-size: .75rem; color: #94a3b8; font-weight: 600; width: 55px; flex-shrink: 0; }
.ddr-input { flex: 1; padding: 5px 8px; border-radius: 6px; border: 1px solid rgba(99,102,241,.2); background: transparent; color: inherit; font-size: .8rem; }
.ddr-input-wrap { flex: 1; display: flex; align-items: center; gap: 4px; position: relative; }
.ddr-date-hidden { position: absolute; width: 0; height: 0; opacity: 0; pointer-events: none; }
.ddr-cal-btn { width: 28px; height: 28px; border-radius: 6px; border: 1px solid rgba(99,102,241,.2); background: rgba(99,102,241,.06); color: inherit; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 14px; transition: all .2s; flex-shrink: 0; }
.ddr-cal-btn:hover { background: rgba(99,102,241,.15); border-color: rgba(99,102,241,.4); }
.ddr-calc { font-size: .78rem; color: #818cf8; font-weight: 600; text-align: center; padding-top: 2px; }

/* ── Bảng Tỷ Trọng ─────────────────────────────────── */
.ty-trong-table { width: 100%; border-collapse: collapse; font-size: .85rem; }
.ty-trong-table th { background: rgba(99,102,241,.08); padding: 8px 10px; text-align: left; font-weight: 700; font-size: .78rem; color: #6366f1; border-bottom: 2px solid rgba(99,102,241,.15); }
.ty-trong-table td { padding: 8px 10px; border-bottom: 1px solid rgba(99,102,241,.08); }
.ty-trong-table tbody tr:hover { background: rgba(99,102,241,.03); }
.ty-trong-total td { background: rgba(99,102,241,.06); font-weight: 700; border-top: 2px solid rgba(99,102,241,.2); }
.ty-trong-note { margin-top: 12px; padding: 10px 14px; background: rgba(251,191,36,.06); border-left: 3px solid #f59e0b; border-radius: 0 6px 6px 0; font-size: .83rem; color: #92400e; line-height: 1.5; }

/* ── Daily Report Stats ────────────────────────────── */
.rc-h-daily { background: linear-gradient(90deg,rgba(6,182,212,.08),rgba(99,102,241,.05)); }
.daily-progress-chip { font-size: .78rem; font-weight: 700; padding: 2px 10px; border-radius: 99px; background: rgba(6,182,212,.12); color: #0891b2; margin-left: auto; }
.daily-bar-wrap { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.daily-bar { flex: 1; height: 10px; background: rgba(99,102,241,.1); border-radius: 99px; overflow: hidden; }
.daily-bar-fill { height: 100%; background: linear-gradient(90deg,#06b6d4,#6366f1); border-radius: 99px; transition: width .4s ease; }
.daily-bar-pct { font-size: .8rem; font-weight: 700; color: #6366f1; width: 36px; text-align: right; }
.daily-stats { display: flex; flex-direction: column; gap: 6px; }
.ds-item { font-size: .83rem; padding: 6px 10px; border-radius: 6px; }
.ds-ok  { background: rgba(16,185,129,.06); color: #065f46; }
.ds-warn{ background: rgba(245,158,11,.06); color: #92400e; }
.ds-bad { background: rgba(239,68,68,.06);  color: #991b1b; }
.ds-dates { font-size: .75rem; opacity: .8; margin-left: 4px; }
:global(body.theme-dark) .ty-trong-table th { color: #818cf8; }
:global(body.theme-dark) .ty-trong-note { color: #fbbf24; background: rgba(251,191,36,.06); }
:global(body.theme-dark) .ds-ok  { background: rgba(16,185,129,.08); color: #6ee7b7; }
:global(body.theme-dark) .ds-warn { background: rgba(245,158,11,.08); color: #fcd34d; }
:global(body.theme-dark) .ds-bad  { background: rgba(239,68,68,.08);  color: #fca5a5; }
:global(body.theme-dark) .ddr-input { background: rgba(255,255,255,.04); border-color: rgba(99,102,241,.2); color: #e2e8f0; }
</style>

