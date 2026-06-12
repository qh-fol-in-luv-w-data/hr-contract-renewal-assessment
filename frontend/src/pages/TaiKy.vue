<template>
  <div class="app-layout">
    <!-- SIDEBAR -->
    <aside class="sidebar">
      <div class="sb-top">
        <router-link to="/" class="sb-back" :title="t('back_portal')">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M19 12H5m7-7l-7 7 7 7"/></svg>
        </router-link>
        <div class="sb-logo">
          <div class="sb-logo-mark sb-logo-violet">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
          </div>
          <div>
            <div class="sb-name">{{ t('welcome_tk').replace('AI ', '') }}</div>
            <div class="sb-org">CT Group</div>
          </div>
        </div>
        <button class="sb-reload" title="Tạo đánh giá mới / Tải lại" @click="() => window.location.reload()">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 2v6h-6"/><path d="M3 12a9 9 0 109-9 9.75 9.75 0 00-6.74 2.74L3 8"/></svg>
        </button>
      </div>

      <div class="sb-body">
        <!-- Input Mode Toggle -->
        <div class="sb-section">
          <div class="sb-section-title">{{ t('input_mode') }}</div>
          <div class="mode-toggle">
            <button
              class="mode-btn"
              :class="{active: inputMode === 'default'}"
              @click="inputMode = 'default'"
            >
              <span class="mode-icon">📄</span>
              {{ t('mode_default') }}
            </button>
            <button
              class="mode-btn"
              :class="{active: inputMode === 'scan'}"
              @click="inputMode = 'scan'"
            >
              <span class="mode-icon">📷</span>
              {{ t('mode_scan') }}
            </button>
          </div>
        </div>

        <div class="sb-section">
          <div class="sb-section-title">{{ t('eval_docs') }}</div>

          <div class="sb-upload-card" :class="{filled: evalFile, err: !evalFile&&tried}"
            @dragover.prevent @drop.prevent="drop($event,'eval')" @click="$refs.rEval.click()">
            <input ref="rEval" type="file" :accept="inputMode==='scan'?'.pdf':'.docx,.pdf'" hidden @change="e=>pickFile(e,'eval')"/>
            <div class="upc-icon">📝</div>
            <div class="upc-info" :title="evalFile ? evalFileName : ''">
              <div class="upc-label">{{ t('file_eval_title') }}</div>
              <div class="upc-val" :class="evalFile?'ok':'empty'">
                {{ evalFile ? evalFileName : t('click_to_select') }}
              </div>
              <div v-if="!evalFile" class="upc-hint">{{ inputMode==='scan' ? 'PDF scan' : t('file_eval_desc') }}</div>
            </div>
            <button v-if="evalFile" class="upc-rm" @click.stop="evalFile=null;evalFileName=''">✕</button>
          </div>

          <div class="sb-upload-card" :class="{filled: reportFile, err: !reportFile&&tried}"
            @dragover.prevent @drop.prevent="drop($event,'report')" @click="$refs.rReport.click()">
            <input ref="rReport" type="file" :accept="inputMode==='scan'?'.pdf':'.xlsx,.pdf'" hidden @change="e=>pickFile(e,'report')"/>
            <div class="upc-icon">📊</div>
            <div class="upc-info" :title="reportFile ? reportFileName : ''">
              <div class="upc-label">{{ t('file_report_title') }}</div>
              <div class="upc-val" :class="reportFile?'ok':'empty'">
                {{ reportFile ? reportFileName : t('click_to_select') }}
              </div>
              <div v-if="!reportFile" class="upc-hint">{{ inputMode==='scan' ? 'PDF scan' : t('file_report_desc') }}</div>
            </div>
            <button v-if="reportFile" class="upc-rm" @click.stop="reportFile=null;reportFileName=''">✕</button>
          </div>

          <!-- Divider tùy chọn -->
          <div class="sb-opt-divider"><span>Tùy chọn</span></div>

          <!-- Báo cáo ngày (optional) -->
          <div class="sb-upload-card sb-upload-optional" @dragover.prevent @drop.prevent="drop($event,'daily')" @click="$refs.rDaily.click()">
            <input ref="rDaily" type="file" accept=".docx,.xlsx,.xls,.pdf" hidden @change="e=>pickFile(e,'daily')"/>
            <div class="upc-icon">📅</div>
            <div class="upc-info" :title="dailyReportFile ? dailyReportFileName : ''">
              <div class="upc-label">Báo cáo ngày <span class="upc-opt-badge">Tùy chọn</span></div>
              <div class="upc-val" :class="dailyReportFile?'ok':'empty'">
                {{ dailyReportFile ? dailyReportFileName : 'Click để chọn' }}
              </div>
              <div v-if="!dailyReportFile" class="upc-hint">.docx / .xlsx / .pdf</div>
            </div>
            <button v-if="dailyReportFile" class="upc-rm" @click.stop="dailyReportFile=null;dailyReportFileName=''">✕</button>
          </div>

          <!-- Date range (hiện khi chọn file báo cáo ngày) -->
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

          <p v-if="tried&&(!evalFile||!reportFile)" class="sb-err">{{ t('need_2_files') }}</p>

          <button class="sb-btn-primary" :disabled="loading" @click="doEvaluate">
            <span v-if="loading" class="spinner"></span>
            <svg v-else width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
            {{ loading ? t('analyzing') : t('analyze_btn') }}
          </button>
        </div>

        <!-- Results summary -->
        <div v-if="result" class="sb-section">
          <div class="sb-section-title">{{ t('result') }}</div>
          <div class="sb-badge" :class="result.recommendation?.includes('Tái ký')||result.recommendation?.includes('Đề xuất')?'badge-pass':'badge-fail'">
            <div class="badge-icon">{{ result.recommendation?.includes('Tái ký')||result.recommendation?.includes('Đề xuất')?'✓':'!' }}</div>
            <div class="badge-text">{{ result.recommendation || 'Đang xử lý' }}</div>
          </div>

          <!-- Kết quả ký hợp đồng (từ danh_gia_hop_dong) -->
          <div v-if="result.danh_gia_hop_dong" class="sb-contract-decision"
               :class="result.danh_gia_hop_dong.du_dieu_kien ? 'scd-yes' : 'scd-no'">
            <div class="scd-icon">{{ result.danh_gia_hop_dong.du_dieu_kien ? '✅' : '❌' }}</div>
            <div class="scd-info">
              <div class="scd-label">Kết quả ký hợp đồng</div>
              <div class="scd-value">{{ result.danh_gia_hop_dong.loai_hop_dong_de_xuat || (result.danh_gia_hop_dong.du_dieu_kien ? 'Đồng ý ký' : 'Không đồng ý ký') }}</div>
            </div>
          </div>

          <!-- Proposal & Urgency badges -->
          <div v-if="result.proposal_level" class="sb-mini-badges">
            <div class="sb-mini-badge" :class="'mb-'+proposalColor(result.proposal_level)">
              {{ t('proposal_level') }}: {{ result.proposal_level }}
            </div>
          </div>

          <div class="sb-counts">
            <div class="sc"><div class="sc-val score">{{ result.overall_score?.toFixed(1) || '—' }}</div><div class="sc-lbl">{{ t('score_total') }}</div></div>
            <div class="sc"><div class="sc-val ok">{{ result.competency_scores?.length || 0 }}</div><div class="sc-lbl">{{ t('competency') }}</div></div>
            <div class="sc"><div class="sc-val warn">{{ result.evidence?.length || 0 }}</div><div class="sc-lbl">{{ t('evidence') }}</div></div>
          </div>
          <button class="sb-btn-secondary" @click="downloadPdf">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            {{ t('export_pdf') }}
          </button>
        </div>

        <!-- Progress -->
        <div v-if="loading" class="sb-section">
          <div class="sb-section-title">{{ t('progress') }}</div>
          <p class="progress-text">{{ progress.message || t('analyzing') }}</p>
        </div>
      </div>
    </aside>

    <!-- MAIN RESULT PANEL -->
    <main class="result-panel">
      <!-- Welcome -->
      <div v-if="!result && !loading && !ocrReview" class="welcome">
        <div class="welcome-icon">
          <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
            <rect width="48" height="48" rx="16" fill="url(#tg)"/>
            <text x="24" y="32" text-anchor="middle" font-size="22">📝</text>
            <defs><linearGradient id="tg" x1="0" y1="0" x2="48" y2="48"><stop stop-color="#8b5cf6"/><stop offset="1" stop-color="#a855f7"/></linearGradient></defs>
          </svg>
        </div>
        <h1>{{ t('welcome_tk') }}</h1>
        <p>{{ t('welcome_tk_desc') }}</p>
        <div class="welcome-features">
          <div class="wf"><div class="wf-icon">📄</div><div>{{ t('tk_f1') }}</div></div>
          <div class="wf"><div class="wf-icon">📊</div><div>{{ t('tk_f2') }}</div></div>
          <div class="wf"><div class="wf-icon">✅</div><div>{{ t('tk_f3') }}</div></div>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="loading-screen">
        <div class="loading-spinner"></div>
        <p>{{ inputMode==='scan'&&!ocrReview ? t('ocr_processing') : (store.lang==='en'?'AI is analyzing contract renewal...':'AI đang phân tích hồ sơ tái ký...') }}</p>
        <p class="loading-sub">{{ store.lang==='en'?'This might take 30-60 seconds':'Quá trình này có thể mất 30–60 giây' }}</p>
      </div>

      <!-- Error -->
      <div v-if="error" class="error-card">
        <div class="error-icon">❌</div>
        <p>{{ error }}</p>
      </div>

      <!-- OCR Review Screen (show even after result, so user can edit and re-evaluate) -->
      <div v-if="ocrReview && !loading" class="results-scroll ocr-review-screen">

        <!-- Header Bar -->
        <div class="ocr-review-header">
          <div class="ocr-review-title">
            <div class="ocr-review-icon">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
            </div>
            <div>
              <h2>{{ t('review_ocr') }}</h2>
              <p class="ocr-review-subtitle">Kiểm tra và chỉnh sửa trực tiếp nội dung OCR</p>
            </div>
          </div>
          <button class="sb-btn-primary ocr-confirm-btn-top" :disabled="loading" @click="confirmOcr">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M20 6L9 17l-5-5"/></svg>
            {{ t('confirm_evaluate') }}
          </button>
        </div>

        <!-- Document Tabs -->
        <div class="ocr-doc-tabs">
          <button class="ocr-doc-tab" :class="{active: ocrTab==='eval'}" @click="ocrTab='eval'">
            <span class="ocr-doc-tab-icon">📝</span>
            <span class="ocr-doc-tab-label">{{ t('tab_eval') }}</span>
          </button>
          <button class="ocr-doc-tab" :class="{active: ocrTab==='report'}" @click="ocrTab='report'">
            <span class="ocr-doc-tab-icon">📊</span>
            <span class="ocr-doc-tab-label">{{ t('tab_report') }}</span>
          </button>
        </div>

        <!-- ========== TAB: PHIẾU ĐÁNH GIÁ TÁI KÝ ========== -->
        <div v-if="ocrTab==='eval'" class="ocr-content-card">

          <!-- Thông tin nhân viên (Extracted Fields) -->
          <div v-if="ocrExtractedFields.length" class="ocr-info-section">
            <div class="ocr-info-header">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/></svg>
              Thông tin nhân viên
            </div>
            <div class="ocr-info-grid">
              <div v-for="(field, fi) in ocrExtractedFields" :key="fi" class="ocr-info-row" :class="{'ocr-info-missing': !field.value}">
                <label class="ocr-info-label">
                  <span class="ocr-info-dot" :class="field.value ? 'dot-ok' : 'dot-warn'"></span>
                  {{ field.label }}
                </label>
                <input
                  type="text"
                  class="ocr-info-input"
                  :value="field.value"
                  :placeholder="'Chưa phát hiện — nhập thủ công'"
                  @input="updateExtractedField(fi, $event.target.value)"
                />
              </div>
            </div>
          </div>

          <!-- Nội dung phiếu đánh giá (Word Template) -->
          <div class="ocr-edit-section">
            <div class="ocr-edit-header">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
              Nội dung phiếu đánh giá
              <button class="ocr-toggle-edit" @click="ocrEditMode.eval = !ocrEditMode.eval">
                <template v-if="!ocrEditMode.eval">✏️ Sửa JSON gốc</template>
                <template v-else>👁️ Xem Form</template>
              </button>
            </div>
            
            <!-- Rendered Form (Word style) -->
            <div v-if="!ocrEditMode.eval" class="word-template-view">
              <div class="word-header">
                <h2>BÁO CÁO KẾT QUẢ CÔNG VIỆC (TÁI KÝ HỢP ĐỒNG)</h2>
              </div>
              
              <template v-if="ocrEvalContent && ocrEvalContent.thong_tin_nhan_vien">
                <table class="word-table">
                  <tr>
                    <td class="word-label">Họ và tên CBNV:</td>
                    <td><input type="text" v-model="ocrEvalContent.thong_tin_nhan_vien.ho_ten" class="word-input" /></td>
                    <td class="word-label">MSNV:</td>
                    <td><input type="text" v-model="ocrEvalContent.thong_tin_nhan_vien.msnv" class="word-input" /></td>
                  </tr>
                  <tr>
                    <td class="word-label">Vị trí công việc:</td>
                    <td><input type="text" v-model="ocrEvalContent.thong_tin_nhan_vien.vi_tri" class="word-input" /></td>
                    <td class="word-label">Phòng – Ban – LL/Khối:</td>
                    <td><input type="text" v-model="ocrEvalContent.thong_tin_nhan_vien.phong_ban" class="word-input" /></td>
                  </tr>
                  <tr>
                    <td class="word-label">Ngày nhận việc/Ngày tái TD:</td>
                    <td><input type="text" v-model="ocrEvalContent.thong_tin_nhan_vien.ngay_nhan_viec" class="word-input" /></td>
                    <td colspan="2"></td>
                  </tr>
                  <tr>
                    <td class="word-label">Ngày bắt đầu HĐ gần nhất:</td>
                    <td><input type="text" v-model="ocrEvalContent.thong_tin_nhan_vien.ngay_bat_dau_hd" class="word-input" /></td>
                    <td class="word-label">Ngày hết hạn HĐ:</td>
                    <td><input type="text" v-model="ocrEvalContent.thong_tin_nhan_vien.ngay_het_han_hd" class="word-input" /></td>
                  </tr>
                </table>

                <h3 class="word-h3">I. TUÂN THỦ VỀ QUẢN TRỊ NỘI BỘ</h3>
                <table class="word-table">
                  <tr>
                    <th class="word-th">Đánh giá mức độ tuân thủ</th>
                    <th class="word-th">Mức độ hoàn thành<br/>(Quản lý trực tiếp đánh giá)</th>
                  </tr>
                  <tr v-for="(item, idx) in ocrEvalContent.muc_1_tuan_thu" :key="'tuanthu'+idx">
                    <td><textarea v-model="item.noi_dung" class="word-textarea"></textarea></td>
                    <td><textarea v-model="item.muc_do_hoan_thanh" class="word-textarea"></textarea></td>
                  </tr>
                </table>

                <h3 class="word-h3">II. BÁO CÁO KẾT QUẢ CÔNG VIỆC</h3>
                <table class="word-table">
                  <tr>
                    <th class="word-th" style="width: 52%">Đánh giá thực hiện chỉ tiêu cam kết<br/>(liệt kê chi tiết công việc và kết quả)</th>
                    <th class="word-th" style="width: 12%" colspan="2">Nhân viên tự đánh giá<br/>(Mức độ hoàn thành | Tỷ lệ đạt)</th>
                    <th class="word-th" style="width: 12%" colspan="2">Quản lý trực tiếp đánh giá<br/>(Mức độ hoàn thành | Tỷ lệ đạt)</th>
                  </tr>
                  <tr v-for="(item, idx) in ocrEvalContent.muc_2_ket_qua_cong_viec" :key="'kq'+idx">
                    <td><textarea v-model="item.chi_tieu" class="word-textarea" style="min-height: 80px;"></textarea></td>
                    <td style="width: 6%; text-align: center;"><input type="text" v-model="item.nv_muc_do_hoan_thanh" class="word-input" style="text-align: center;" /></td>
                    <td style="width: 6%; text-align: center;"><input type="text" v-model="item.nv_ty_le_dat" class="word-input" style="text-align: center;" /></td>
                    <td style="width: 6%; text-align: center;"><input type="text" v-model="item.ql_muc_do_hoan_thanh" class="word-input" style="text-align: center;" /></td>
                    <td style="width: 6%; text-align: center;"><input type="text" v-model="item.ql_ty_le_dat" class="word-input" style="text-align: center;" /></td>
                  </tr>
                </table>

                <h3 class="word-h3">III. ĐÁNH GIÁ KẾT QUẢ CÔNG VIỆC (Phần này dành cho cán bộ quản lý trực tiếp)</h3>
                <table class="word-table" v-if="ocrEvalContent.muc_3_danh_gia_quan_ly">
                  <tr>
                    <th class="word-th" style="width: 40%">Nhận xét của Quản lý trực tiếp:</th>
                    <th class="word-th"></th>
                  </tr>
                  <tr>
                    <td>Nhận xét chi tiết kết quả CV CBNV đã thực hiện:</td>
                    <td><textarea v-model="ocrEvalContent.muc_3_danh_gia_quan_ly.nhan_xet_chi_tiet" class="word-textarea"></textarea></td>
                  </tr>
                  <tr>
                    <td>Ưu điểm của CBNV:</td>
                    <td><textarea v-model="ocrEvalContent.muc_3_danh_gia_quan_ly.uu_diem" class="word-textarea"></textarea></td>
                  </tr>
                  <tr>
                    <td>Hạn chế của CBNV:</td>
                    <td><textarea v-model="ocrEvalContent.muc_3_danh_gia_quan_ly.han_che" class="word-textarea"></textarea></td>
                  </tr>
                  <tr>
                    <td>Giải pháp, yêu cầu khắc phục trong thời gian tới:</td>
                    <td><textarea v-model="ocrEvalContent.muc_3_danh_gia_quan_ly.giai_phap" class="word-textarea"></textarea></td>
                  </tr>
                </table>

                <table class="word-table" v-if="ocrEvalContent.de_xuat">
                  <tr>
                    <td style="width: 50%;">
                      <strong>Đề xuất của Quản lý trực tiếp:</strong><br/>
                      <textarea v-model="ocrEvalContent.de_xuat.quan_ly_truc_tiep" class="word-textarea" style="min-height:80px;"></textarea>
                    </td>
                    <td style="width: 50%;">
                      <strong>Đề xuất của Lãnh đạo Ban/Lực lượng/Khối:</strong><br/>
                      <textarea v-model="ocrEvalContent.de_xuat.lanh_dao_ban" class="word-textarea" style="min-height:80px;"></textarea>
                    </td>
                  </tr>
                </table>
              </template>
              <div v-else style="text-align:center; padding: 40px; color:#94a3b8">
                Đang xử lý cấu trúc JSON...
              </div>
            </div>
            
            <!-- Raw Edit -->
            <textarea
              v-else
              :value="JSON.stringify(ocrEvalContent, null, 2)"
              @input="tryParseJson($event.target.value, 'eval')"
              class="ocr-edit-area"
              placeholder="Nội dung JSON phiếu đánh giá..."
              spellcheck="false"
            ></textarea>
          </div>

          <!-- Warning Status -->
          <div v-if="ocrWarnings.length" class="ocr-status-bar ocr-status-warn">
            <div class="ocr-status-content">
              <span class="ocr-status-icon">⚠️</span>
              <div class="ocr-status-text">
                <strong>{{ ocrWarnings.length }} trường cần kiểm tra</strong>
                <div class="ocr-warn-tags">
                  <span v-for="(w, wi) in ocrWarnings" :key="wi" class="ocr-warn-tag">{{ w }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- ========== TAB: BÁO CÁO KẾT QUẢ CÔNG VIỆC ========== -->
        <div v-if="ocrTab==='report'" class="ocr-content-card">
          <div class="ocr-edit-section">
            <div class="ocr-edit-header">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
              Nội dung báo cáo kết quả công việc
              <button class="ocr-toggle-edit" @click="ocrEditMode.report = !ocrEditMode.report">
                <template v-if="!ocrEditMode.report">✏️ Sửa JSON gốc</template>
                <template v-else>👁️ Xem Form</template>
              </button>
            </div>
            
            <!-- Rendered Form (Word style) -->
            <div v-if="!ocrEditMode.report" class="rpt-doc">
              <div class="rpt-title">{{ ocrReportContent.tieu_de || 'KẾ HOẠCH SXKD VÀ ĐÁNH GIÁ KẾT QUẢ THỰC HIỆN' }}</div>
              
              <!-- New scan_sxkd format (ho_ten, cong_viec at top level) -->
              <template v-if="ocrReportContent && (ocrReportContent.cong_viec || ocrReportContent.ho_ten)">
                <div class="rpt-info-row">
                  <span class="rpt-field-label">Họ và tên:</span>
                  <input class="rpt-inline-input rpt-name" v-model="ocrReportContent.ho_ten" />
                </div>

                <div class="rpt-section-label">BẢNG KẾ HOẠCH VÀ KẾT QUẢ CÔNG VIỆC</div>
                <div class="rpt-table-wrap">
                  <table class="rpt-table">
                    <thead>
                      <tr class="rpt-th">
                        <th rowspan="2" class="rpt-th-stt">STT</th>
                        <th rowspan="2" class="rpt-th-mang">CÁC MẢNG CÔNG TÁC</th>
                        <th rowspan="2" class="rpt-th-mota">MÔ TẢ SẢN PHẨM HOÀN THÀNH TRONG THÁNG</th>
                        <th colspan="3" class="rpt-thg rpt-th-kh">KẾ HOẠCH</th>
                        <th colspan="3" class="rpt-thg rpt-th-kq">KẾT QUẢ</th>
                        <th rowspan="2" class="rpt-th-link">LINK SẢN PHẨM</th>
                      </tr>
                      <tr class="rpt-th">
                        <th class="rpt-ths">TỶ TRỌNG</th><th class="rpt-ths">KPI</th><th class="rpt-ths">BOD</th>
                        <th class="rpt-ths rpt-kq-col">TỶ LỆ KPI</th><th class="rpt-ths rpt-kq-col">KQ KPI</th><th class="rpt-ths rpt-kq-col">BOD</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(item, idx) in ocrReportContent.cong_viec" :key="'sxkd_cv'+idx" class="rpt-row">
                        <td class="rpt-td-stt">{{ item.stt || idx+1 }}</td>
                        <td class="rpt-td-mang"><input class="rpt-input" v-model="item.mang_cong_tac" /></td>
                        <td class="rpt-td-mota"><textarea class="rpt-ta" v-model="item.mo_ta_san_pham" rows="3"></textarea></td>
                        <td class="rpt-td-num"><input class="rpt-input rpt-tc" v-model="item.ty_trong" /></td>
                        <td class="rpt-td-num"><input class="rpt-input rpt-tc" v-model="item.kpi_ke_hoach" /></td>
                        <td class="rpt-td-bod"><input class="rpt-input" v-model="item.bod_ke_hoach" /></td>
                        <td class="rpt-td-num rpt-kqc"><input class="rpt-input rpt-tc" v-model="item.ty_le_kpi_ket_qua" /></td>
                        <td class="rpt-td-num rpt-kqc"><input class="rpt-input rpt-tc rpt-kqb" v-model="item.ket_qua_kpi" /></td>
                        <td class="rpt-td-bod rpt-kqc"><input class="rpt-input" v-model="item.bod_ket_qua" /></td>
                        <td class="rpt-td-link"><textarea class="rpt-ta rpt-link-ta" v-model="item.link_san_pham" rows="2"></textarea></td>
                      </tr>
                      <tr class="rpt-total-row">
                        <td colspan="3" class="rpt-total-label">TỶ LỆ ĐẠT</td>
                        <td class="rpt-td-num rpt-tc">{{ ocrReportContent.ty_le_dat_ke_hoach || '100%' }}</td>
                        <td colspan="2"></td>
                        <td colspan="2" class="rpt-td-num rpt-tc rpt-kqb">{{ ocrReportContent.ty_le_dat_ket_qua || '' }}</td>
                        <td colspan="1"></td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <!-- Nội quy -->
                <template v-if="ocrReportContent.noi_quy && ocrReportContent.noi_quy.length">
                  <div class="rpt-section-label rpt-nq-label">NỘI QUY BẮT BUỘC</div>
                  <div class="rpt-nq-note">(Vi phạm sẽ bị khấu trừ KPI)</div>
                  <div class="rpt-table-wrap">
                    <table class="rpt-table rpt-nq-table">
                      <thead><tr class="rpt-th"><th class="rpt-th-stt">STT</th><th>NỘI DUNG</th><th class="rpt-ths">KẾ HOẠCH</th><th class="rpt-ths">KẾT QUẢ</th><th>XÁC NHẬN</th><th>GHI CHÚ</th></tr></thead>
                      <tbody>
                        <tr v-for="(nq, idx) in ocrReportContent.noi_quy" :key="'nq'+idx" class="rpt-row">
                          <td class="rpt-td-stt">{{ nq.stt || idx+1 }}</td>
                          <td><input class="rpt-input" v-model="nq.noi_dung" /></td>
                          <td class="rpt-td-num rpt-tc"><input class="rpt-input rpt-tc" v-model="nq.ke_hoach" /></td>
                          <td class="rpt-td-num rpt-tc rpt-kqc"><input class="rpt-input rpt-tc" v-model="nq.ket_qua" /></td>
                          <td><input class="rpt-input" v-model="nq.xac_nhan" /></td>
                          <td><input class="rpt-input" v-model="nq.ghi_chu" /></td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </template>

                <!-- Xét duyệt -->
                <template v-if="ocrReportContent.xet_duyet">
                  <div class="rpt-xd-title">PHẦN TRÌNH VÀ XÉT DUYỆT</div>
                  <table class="rpt-xd-table">
                    <thead><tr><th>XÉT DUYỆT</th><th>Ý KIẾN</th><th>Ranking</th></tr></thead>
                    <tbody>
                      <tr><td class="rpt-xd-label">HOD</td><td><input class="rpt-input" v-model="ocrReportContent.xet_duyet.hod_y_kien" /></td><td rowspan="2" class="rpt-xd-ranking"><input class="rpt-input rpt-tc rpt-ranking-input" v-model="ocrReportContent.xet_duyet.ranking" /></td></tr>
                      <tr><td class="rpt-xd-label">BOD</td><td><input class="rpt-input" v-model="ocrReportContent.xet_duyet.bod_y_kien" /></td></tr>
                    </tbody>
                  </table>
                </template>
              </template>

              <!-- Old format (thong_tin_chung / bang_cong_viec) -->
              <template v-else-if="ocrReportContent && ocrReportContent.thong_tin_chung">
                <div class="rpt-info-row">
                  <span class="rpt-field-label">Họ và tên:</span>
                  <input class="rpt-inline-input" v-model="ocrReportContent.thong_tin_chung.ho_ten" />
                  <span class="rpt-field-label" style="margin-left:20px">MSNV:</span>
                  <input class="rpt-inline-input" v-model="ocrReportContent.thong_tin_chung.msnv" style="max-width:120px" />
                </div>
                <div class="rpt-info-row">
                  <span class="rpt-field-label">Phòng ban:</span>
                  <input class="rpt-inline-input" v-model="ocrReportContent.thong_tin_chung.phong_ban" />
                  <span class="rpt-field-label" style="margin-left:20px">Vị trí:</span>
                  <input class="rpt-inline-input" v-model="ocrReportContent.thong_tin_chung.vi_tri" />
                </div>

                <div class="rpt-section-label">BẢNG KẾT QUẢ CÔNG VIỆC</div>
                <div class="rpt-table-wrap">
                  <table class="rpt-table rpt-nq-table">
                    <thead><tr class="rpt-th">
                      <th class="rpt-th-stt">STT</th>
                      <th style="width:52%">II. BÁO CÁO KẾT QUẢ CÔNG VIỆC</th>
                      <th class="rpt-ths">Nhân viên tự đánh giá<br/>(Mức độ hoàn thành | Tỷ lệ đạt)</th>
                      <th class="rpt-ths">Quản lý trực tiếp đánh giá<br/>(Mức độ hoàn thành | Tỷ lệ đạt)</th>
                    </tr></thead>
                    <tbody>
                      <tr v-for="(item, idx) in ocrReportContent.bang_cong_viec" :key="'report_kq'+idx" class="rpt-row">
                        <td class="rpt-td-stt">{{ item.stt || idx+1 }}</td>
                        <td><textarea class="rpt-ta" v-model="item.noi_dung_cong_viec" rows="3"></textarea></td>
                        <td class="rpt-td-num"><input class="rpt-input rpt-tc" v-model="item.tu_danh_gia" /></td>
                        <td class="rpt-td-num"><input class="rpt-input rpt-tc" v-model="item.quan_ly_danh_gia" /></td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <template v-if="ocrReportContent.tong_ket">
                  <div class="rpt-section-label" style="color:#10b981">TỔNG KẾT</div>
                  <div class="rpt-info-row">
                    <span class="rpt-field-label">Tổng tỷ trọng:</span>
                    <input class="rpt-inline-input" v-model="ocrReportContent.tong_ket.tong_ty_trong" style="max-width:100px" />
                    <span class="rpt-field-label" style="margin-left:16px">Tự ĐG:</span>
                    <input class="rpt-inline-input" v-model="ocrReportContent.tong_ket.diem_tu_danh_gia" style="max-width:100px" />
                    <span class="rpt-field-label" style="margin-left:16px">QL ĐG:</span>
                    <input class="rpt-inline-input" v-model="ocrReportContent.tong_ket.diem_quan_ly" style="max-width:100px" />
                  </div>
                </template>
              </template>

              <div v-else style="text-align:center; padding: 40px; color:#94a3b8">
                Đang xử lý cấu trúc JSON...
              </div>
            </div>
            
            <!-- Raw Edit -->
            <textarea
              v-else
              :value="JSON.stringify(ocrReportContent, null, 2)"
              @input="tryParseJson($event.target.value, 'report')"
              class="ocr-edit-area"
              placeholder="Nội dung JSON báo cáo công việc..."
              spellcheck="false"
            ></textarea>
          </div>
        </div>

        <!-- Bottom Confirm Button -->
        <div class="ocr-confirm-bottom">
          <button class="sb-btn-primary ocr-confirm-btn-lg" :disabled="loading" @click="confirmOcr">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M20 6L9 17l-5-5"/></svg>
            {{ loading ? t('analyzing') : (result ? '⚙️ Chỉnh sửa & Đánh giá lại' : t('confirm_evaluate')) }}
          </button>
          <p class="ocr-confirm-hint">{{ result ? 'Chỉnh sửa nội dung phía trên và gửi đánh giá lại' : 'AI sẽ sử dụng nội dung phía trên để đánh giá' }}</p>
        </div>

        <!-- Results shown inside OCR review (after confirm button) -->
        <template v-if="result && !loading">
          <div class="from-scan-banner" style="margin-top: 20px;">
            <span class="fs-icon">🔍</span>
            <div>
              <div class="fs-title" style="font-weight:700;font-size:.88rem;">Kết quả đánh giá từ Scan OCR</div>
              <div class="fs-sub" style="font-size:.78rem;color:#64748b;">Dữ liệu được trích xuất và phân tích bởi AI. Chỉnh sửa nội dung phía trên rồi bấm "Đánh giá lại" nếu cần.</div>
            </div>
          </div>
        </template>
      </div>

      <!-- Results -->
      <div v-if="result && !loading" class="results-scroll" :class="{'results-with-ocr': ocrReview}">
        <!-- Employee Info -->
        <div class="emp-info-card">
          <div class="emp-info-header">
            <div class="emp-avatar">{{ (result.employee_name || '?')[0] }}</div>
            <div>
              <div class="emp-info-title">{{ result.employee_name || 'Chưa xác định' }}</div>
              <div style="font-size: .78rem; color: #64748b">{{ result.job_title || '' }}</div>
            </div>
          </div>
          <div class="emp-info-grid">
            <div>
              <div class="emp-field-label">Họ tên</div>
              <div class="emp-field-value" :class="{'emp-field-empty': !result.employee_name}">{{ result.employee_name || 'Chưa trích xuất' }}</div>
            </div>
            <div>
              <div class="emp-field-label">Chức danh</div>
              <div class="emp-field-value" :class="{'emp-field-empty': !result.job_title}">{{ result.job_title || 'Chưa trích xuất' }}</div>
            </div>
            <div>
              <div class="emp-field-label">Phòng ban / Công ty</div>
              <div class="emp-field-value" :class="{'emp-field-empty': !result.department}">{{ result.department || 'Chưa trích xuất' }}</div>
            </div>
            <div>
              <div class="emp-field-label">Ngày đánh giá</div>
              <div class="emp-field-value" :class="{'emp-field-empty': !result.evaluation_date}">{{ result.evaluation_date || '—' }}</div>
            </div>
          </div>
        </div>

        <!-- Document Warnings -->
        <div class="result-card">
          <div class="rc-header" :class="docWarningsComplete && !hasValidationWarnings ? 'rc-h-green' : 'rc-h-warn'" @click="toggle('docwarn')">
            <span>{{ docWarningsComplete && !hasValidationWarnings ? '✅' : '⚠️' }} Tình trạng điền hồ sơ
              <span v-if="totalWarningsCount > 0" class="warn-count">({{ totalWarningsCount }})</span>
            </span>
            <span class="rc-arrow" :class="{open:sec.docwarn}">›</span>
          </div>
          <div v-if="sec.docwarn" class="rc-body">
            <!-- Document Completeness -->
            <div v-if="docWarningsComplete" class="doc-complete-badge">
              <span class="dc-icon">✅</span>
              <span>Hồ sơ đầy đủ: Đã điền đủ các thông tin bắt buộc.</span>
            </div>
            <div v-else>
              <div class="doc-incomplete-badge" style="margin-bottom: 12px;">
                <span class="di-icon">⚠️</span>
                <span>Hồ sơ cần bổ sung — Có trường thông tin bị để trống:</span>
              </div>
              <ul class="warn-list">
                <li v-for="(w, wi) in docWarningsList" :key="wi" class="warn-item">{{ typeof w === 'object' ? w.message : w }}</li>
              </ul>
            </div>

            <!-- Validation Warnings -->
            <div v-if="hasValidationWarnings" style="margin-top: 20px; padding-top: 16px; border-top: 1px solid #e2e8f0;">
              <div v-if="validationWarningsList.length" style="margin-bottom: 12px;">
                <div class="doc-incomplete-badge" style="margin-bottom: 8px;">
                  <span class="di-icon">⚠️</span>
                  <span>Cảnh báo dữ liệu đầu vào:</span>
                </div>
                <ul class="warn-list" style="margin-left: 12px;">
                  <li v-for="(w, wi) in validationWarningsList" :key="wi" class="warn-item">{{ typeof w === 'object' ? w.message : w }}</li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        <!-- 2AS Assessment / Nhận định của 2AS -->
        <div class="result-card">
          <div class="rc-header rc-h-violet" @click="toggle('assessment')">
            <span>🤖 Nhận định của 2AS & Đề xuất xử lý</span>
            <span class="rc-arrow" :class="{open:sec.assessment}">›</span>
          </div>
          <div v-if="sec.assessment" class="rc-body" style="padding-top: 16px;">
            <!-- Proposal Level -->
            <div style="display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap;">
              <div style="flex: 1; min-width: 200px; padding: 14px 16px; border-radius: 10px; border: 1px solid #e2e8f0; background: #fafbfc;">
                <div class="emp-field-label">Mức độ đề xuất</div>
                <div style="font-size: 1rem; font-weight: 700; margin-top: 4px;" :style="{color: proposalColor(result.proposal_level) === 'green' ? '#16a34a' : proposalColor(result.proposal_level) === 'yellow' ? '#ca8a04' : proposalColor(result.proposal_level) === 'red' ? '#dc2626' : '#64748b'}">
                  {{ result.proposal_level || 'Chưa xác định' }}
                </div>
              </div>
              <div style="flex: 1; min-width: 200px; padding: 14px 16px; border-radius: 10px; border: 1px solid #e2e8f0; background: #fafbfc;">
                <div class="emp-field-label">Điểm tổng</div>
                <div style="font-size: 1.4rem; font-weight: 800; margin-top: 4px; color: #7c3aed;">
                  {{ result.overall_score?.toFixed(1) || '—' }}<span style="font-size: .8rem; font-weight: 400; color: #94a3b8;">/10</span>
                </div>
              </div>
            </div>

            <!-- Recommendation -->
            <div style="padding: 14px 16px; border-radius: 10px; border: 1px solid #e2e8f0; background: #fafbfc; margin-bottom: 12px;">
              <div class="emp-field-label">Đề xuất của 2AS</div>
              <div style="font-size: .92rem; font-weight: 600; color: #1e293b; margin-top: 6px; line-height: 1.5;">
                {{ result.recommendation || 'Đang phân tích...' }}
              </div>
              <div v-if="result.recommendation_reasoning" style="font-size: .84rem; color: #64748b; margin-top: 8px; line-height: 1.5;">
                {{ result.recommendation_reasoning }}
              </div>
            </div>
          </div>
        </div>

        <!-- Competency Scores -->
        <div v-if="result.competency_scores?.length" class="result-card">
          <div class="rc-header rc-h-blue" @click="toggle('comp')">
            <span>📊 {{ store.lang==='en'?'Competency Scores':'Bảng năng lực' }} – {{ result.competency_scores.length }} mục</span>
            <span class="rc-arrow" :class="{open:sec.comp}">›</span>
          </div>
          <div v-if="sec.comp" class="rc-body">
            <table class="comp-table">
              <thead>
                <tr><th>STT</th><th>Năng lực</th><th>Trọng số</th><th>Điểm</th></tr>
              </thead>
              <tbody>
                <tr v-for="(c,ci) in result.competency_scores" :key="ci">
                  <td class="td-center">{{ ci+1 }}</td>
                  <td>{{ c.name || c.competency_name }}</td>
                  <td class="td-center">{{ c.weight }}%</td>
                  <td class="td-center td-score" :class="c.score>=7?'s-good':c.score>=5?'s-mid':'s-low'">{{ c.score?.toFixed(1) }}</td>
                </tr>
                <tr class="comp-total">
                  <td colspan="3"><strong>{{ store.lang==='en'?'TOTAL SCORE':'ĐIỂM TỔNG' }}</strong></td>
                  <td class="td-center td-score" :class="result.overall_score>=7?'s-good':'s-mid'"><strong>{{ result.overall_score?.toFixed(1) }}</strong></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Recommendation Details -->
        <div v-if="result.recommendation_details" class="result-card">
          <div class="rc-header rc-h-violet" @click="toggle('rec')">
            <span>📋 {{ store.lang==='en'?'Detailed Analysis':'Phân tích chi tiết' }}</span>
            <span class="rc-arrow" :class="{open:sec.rec}">›</span>
          </div>
          <div v-if="sec.rec" class="rc-body rec-body">
            <!-- Legacy support for string -->
            <div v-if="typeof result.recommendation_details === 'string'" v-html="formatRec(result.recommendation_details)"></div>

            <!-- Object rendering -->
            <div v-else>
              <p class="rd-text" style="margin-bottom: 15px;">{{ result.recommendation_details.reasoning }}</p>

              <div v-if="result.recommendation_details.strengths?.length" class="rd-section">
                <strong class="rd-label rd-label-green">Điểm mạnh</strong>
                <ul class="rd-list">
                  <li v-for="(s, i) in result.recommendation_details.strengths" :key="'s'+i">{{ s }}</li>
                </ul>
              </div>

              <div v-if="result.recommendation_details.improvements?.length" class="rd-section">
                <strong class="rd-label rd-label-yellow">Cần cải thiện</strong>
                <ul class="rd-list">
                  <li v-for="(s, i) in result.recommendation_details.improvements" :key="'i'+i">{{ s }}</li>
                </ul>
              </div>

              <div v-if="result.recommendation_details.development_potential" class="rd-section">
                <strong class="rd-label rd-label-blue">Tiềm năng phát triển</strong>
                <p class="rd-text">{{ result.recommendation_details.development_potential }}</p>
              </div>

              <div v-if="result.recommendation_details.risk_flags?.length" class="rd-section">
                <strong class="rd-label rd-label-red">Rủi ro cần lưu ý</strong>
                <ul class="rd-list">
                  <li v-for="(s, i) in result.recommendation_details.risk_flags" :key="'r'+i">{{ s }}</li>
                </ul>
              </div>

              <div v-if="result.recommendation_details.conditions_if_renew?.length" class="rd-section">
                <strong class="rd-label rd-label-purple">Điều kiện tái ký</strong>
                <ul class="rd-list">
                  <li v-for="(s, i) in result.recommendation_details.conditions_if_renew" :key="'c'+i">{{ s }}</li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        <!-- Next Steps -->
        <div v-if="nextStepsList.length" class="result-card">
          <div class="rc-header rc-h-cyan" @click="toggle('nextsteps')">
            <span>🔜 {{ t('next_steps') }} – {{ nextStepsList.length }} mục</span>
            <span class="rc-arrow" :class="{open:sec.nextsteps}">›</span>
          </div>
          <div v-if="sec.nextsteps" class="rc-body">
            <div v-for="(ns, nsi) in nextStepsList" :key="nsi" class="ns-item">
              <div class="ns-action">
                <span class="ns-num">{{ nsi + 1 }}</span>
                {{ ns.action }}
              </div>
              <div class="ns-meta">
                <span v-if="ns.priority" class="ns-tag" :class="'ns-'+ns.priority.toLowerCase()">{{ ns.priority }}</span>
                <span v-if="ns.responsible" class="ns-resp">👤 {{ ns.responsible }}</span>
                <span v-if="ns.deadline_note" class="ns-deadline">⏰ {{ ns.deadline_note }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Báo cáo ngày -->
        <div v-if="result.bao_cao_ngay" class="result-card">
          <div class="rc-header rc-h-daily" @click="toggle('bao_cao_ngay')">
            <span>📅 Báo cáo ngày</span>
            <span class="daily-progress-chip">{{ result.bao_cao_ngay.so_ngay_da_bc ?? '?' }}/{{ result.bao_cao_ngay.so_ngay_can_bc ?? '?' }} ngày</span>
            <span class="rc-arrow" :class="{open:sec.bao_cao_ngay}">›</span>
          </div>
          <div v-if="sec.bao_cao_ngay" class="rc-body">
            <div class="daily-bar-wrap">
              <div class="daily-bar">
                <div class="daily-bar-fill" :style="{width: Math.min(100,(result.bao_cao_ngay.so_ngay_da_bc||0)/(result.bao_cao_ngay.so_ngay_can_bc||1)*100)+'%'}"></div>
              </div>
              <span class="daily-bar-pct">{{ Math.round((result.bao_cao_ngay.so_ngay_da_bc||0)/(result.bao_cao_ngay.so_ngay_can_bc||1)*100) }}%</span>
            </div>
            <div class="daily-stats" style="margin-bottom:10px;">
              <div v-if="result.bao_cao_ngay.so_ngay_du_hang_muc != null" class="ds-item ds-ok">✅ Đủ hạng mục: <b>{{ result.bao_cao_ngay.so_ngay_du_hang_muc }}</b> ngày</div>
              <div v-if="result.bao_cao_ngay.ngay_thieu_hang_muc?.length" class="ds-item ds-warn">⚠️ Thiếu hạng mục: <b>{{ result.bao_cao_ngay.ngay_thieu_hang_muc.length }}</b> ngày <span class="ds-dates">({{ result.bao_cao_ngay.ngay_thieu_hang_muc.join(', ') }})</span></div>
              <div v-if="result.bao_cao_ngay.ngay_thieu_bao_cao?.length" class="ds-item ds-bad">❌ Thiếu báo cáo: <b>{{ result.bao_cao_ngay.ngay_thieu_bao_cao.length }}</b> ngày <span class="ds-dates">({{ result.bao_cao_ngay.ngay_thieu_bao_cao.join(', ') }})</span></div>
            </div>
            <div v-if="result.bao_cao_ngay.nhan_xet" class="ty-trong-note">📌 {{ result.bao_cao_ngay.nhan_xet }}</div>
            <!-- Bảng đối chiếu công việc -->
            <div v-if="result.bao_cao_ngay.doi_chieu_cong_viec?.length">
              <div style="font-size:.75rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px">📋 Đối chiếu nội dung với phiếu</div>
              <table style="width:100%;border-collapse:collapse;font-size:.8rem">
                <thead>
                  <tr style="background:#f1f5f9">
                    <th style="padding:6px 10px;text-align:left;border:1px solid #e2e8f0;color:#475569;font-weight:700">Hạng mục báo cáo</th>
                    <th style="padding:6px 8px;text-align:center;border:1px solid #e2e8f0;color:#475569;font-weight:700;width:80px">Có trong phiếu</th>
                    <th style="padding:6px 10px;text-align:left;border:1px solid #e2e8f0;color:#475569;font-weight:700">Ghi chú</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, ri) in result.bao_cao_ngay.doi_chieu_cong_viec" :key="ri"
                      :style="ri%2===0?'background:#fff':'background:#f8fafc'">
                    <td style="padding:6px 10px;border:1px solid #e2e8f0;color:#334155">{{ row.hang_muc }}</td>
                    <td style="padding:6px 8px;border:1px solid #e2e8f0;text-align:center">
                      <span :style="row.co_trong_phieu?'color:#16a34a;font-weight:700':'color:#dc2626;font-weight:700'">
                        {{ row.co_trong_phieu ? '✅' : '❌' }}
                      </span>
                    </td>
                    <td style="padding:6px 10px;border:1px solid #e2e8f0;color:#64748b;font-size:.77rem">{{ row.ghi_chu || '—' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- Đề xuất Quản lý -->
        <div v-if="result.danh_gia_quan_ly" class="result-card">
          <div class="rc-header" :class="result.danh_gia_quan_ly.hop_ly ? 'rc-h-green' : 'rc-h-warn'" @click="toggle('quan_ly')">
            <span>👔 Đánh giá đề xuất Quản lý</span>
            <span class="dx-chip" :class="result.danh_gia_quan_ly.hop_ly ? 'chip-pass' : 'chip-extend'">{{ result.danh_gia_quan_ly.muc_do_dong_y || (result.danh_gia_quan_ly.hop_ly ? '✅ Đồng ý' : '⚠️ Cần xem xét') }}</span>
            <span class="rc-arrow" :class="{open:sec.quan_ly}">›</span>
          </div>
          <div v-if="sec.quan_ly" class="rc-body">
            <div style="padding:12px 14px;background:#f8fafc;border-radius:8px;margin-bottom:10px;">
              <div class="emp-field-label">Đề xuất của Quản lý</div>
              <div style="font-size:.9rem;font-weight:600;color:#1e293b;margin-top:4px;">{{ result.danh_gia_quan_ly.de_xuat_quan_ly || '—' }}</div>
            </div>
            
            <div v-if="result.danh_gia_quan_ly.ly_do_chinh" style="margin-top:10px;padding:10px 12px;background:#f0f9ff;border-left:3px solid #0ea5e9;border-radius:6px">
              <div class="dx-ly-do" style="font-size:.85rem;font-weight:600;color:#0c4a6e">{{ result.danh_gia_quan_ly.ly_do_chinh }}</div>
            </div>

            <div v-if="result.danh_gia_quan_ly.phan_tich_chi_tiet" style="margin-top:10px">
              <div class="dx-ly-do" style="font-size:.85rem;line-height:1.75;color:#374151">{{ result.danh_gia_quan_ly.phan_tich_chi_tiet }}</div>
            </div>

            <div style="padding:12px 14px;border-radius:8px;margin-top:10px;" :style="result.danh_gia_quan_ly.hop_ly ? 'background:#f0fdf4;border:1px solid #bbf7d0' : 'background:#fff7ed;border:1px solid #fed7aa'">
              <div class="emp-field-label">Nhận xét của 2AS</div>
              <div style="font-size:.88rem;color:#1e293b;margin-top:4px;line-height:1.6;">{{ result.danh_gia_quan_ly.nhan_xet }}</div>
            </div>
            
            <div v-if="result.danh_gia_quan_ly.khuyen_nghi_xu_ly" style="margin-top:10px;padding:10px 12px;background:#fefce8;border-left:3px solid #eab308;border-radius:6px">
              <div class="dx-ly-do" style="font-size:.85rem;font-weight:600;color:#78350f">{{ result.danh_gia_quan_ly.khuyen_nghi_xu_ly }}</div>
            </div>
          </div>
        </div>

        <!-- ── Đánh giá điều kiện ký/tái ký hợp đồng ── -->
        <div v-if="result.danh_gia_hop_dong" class="result-card">
          <div class="rc-header" :class="result.danh_gia_hop_dong.du_dieu_kien ? 'rc-h-green' : 'rc-h-warn'" @click="toggle('hop_dong')">
            <span>{{ result.danh_gia_hop_dong.du_dieu_kien ? '✅' : '❌' }} Đánh giá Hợp đồng – {{ result.danh_gia_hop_dong.loai_hop_dong_de_xuat || 'Đang xử lý' }}</span>
            <span class="rc-arrow" :class="{open:sec.hop_dong}">›</span>
          </div>
          <div v-if="sec.hop_dong" class="rc-body">
            <!-- Kết luận -->
            <div style="display:flex;align-items:center;gap:12px;padding:12px 14px;border-radius:10px;margin-bottom:12px;"
                 :style="result.danh_gia_hop_dong.du_dieu_kien ? 'background:#f0fdf4;border:1px solid #bbf7d0' : 'background:#fef2f2;border:1px solid #fecaca'">
              <div style="font-size:2rem">{{ result.danh_gia_hop_dong.du_dieu_kien ? '📋' : '🚫' }}</div>
              <div>
                <div style="font-size:.8rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.05em">Loại hợp đồng đề xuất</div>
                <div style="font-size:1rem;font-weight:800;margin-top:2px;" :style="result.danh_gia_hop_dong.du_dieu_kien ? 'color:#16a34a' : 'color:#dc2626'">{{ result.danh_gia_hop_dong.loai_hop_dong_de_xuat }}</div>
              </div>
            </div>
            <!-- Bảng tiêu chí -->
            <div v-if="result.danh_gia_hop_dong.cac_tieu_chi?.length" style="margin-bottom:14px">
              <div style="font-size:.75rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px">📊 Đánh giá từng tiêu chí</div>
              <table style="width:100%;border-collapse:collapse;font-size:.82rem">
                <thead>
                  <tr style="background:#f1f5f9">
                    <th style="padding:7px 10px;text-align:left;border:1px solid #e2e8f0;color:#475569;font-weight:700">Tiêu chí</th>
                    <th style="padding:7px 8px;text-align:center;border:1px solid #e2e8f0;color:#475569;font-weight:700;width:70px">Đạt</th>
                    <th style="padding:7px 8px;text-align:center;border:1px solid #e2e8f0;color:#475569;font-weight:700;width:65px">Điểm</th>
                    <th style="padding:7px 10px;text-align:left;border:1px solid #e2e8f0;color:#475569;font-weight:700">Mô tả</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(tc, ti) in result.danh_gia_hop_dong.cac_tieu_chi" :key="ti"
                      :style="ti%2===0?'background:#fff':'background:#f8fafc'">
                    <td style="padding:7px 10px;border:1px solid #e2e8f0;font-weight:600;color:#1e293b">{{ tc.tieu_chi }}</td>
                    <td style="padding:7px 8px;border:1px solid #e2e8f0;text-align:center">
                      <span :style="tc.dat?'color:#16a34a;font-weight:700':'color:#dc2626;font-weight:700'">{{ tc.dat ? '✅' : '❌' }}</span>
                    </td>
                    <td style="padding:7px 8px;border:1px solid #e2e8f0;text-align:center">
                      <span v-if="tc.diem_so != null" style="font-weight:700" :style="tc.diem_so>=7?'color:#16a34a':tc.diem_so>=5?'color:#d97706':'color:#dc2626'">{{ typeof tc.diem_so === 'number' ? tc.diem_so.toFixed(1) : tc.diem_so }}/10</span>
                      <span v-else style="color:#94a3b8">—</span>
                    </td>
                    <td style="padding:7px 10px;border:1px solid #e2e8f0;color:#475569;font-size:.8rem">{{ tc.mo_ta }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <!-- Căn cứ -->
            <div v-if="result.danh_gia_hop_dong.can_cu_danh_gia?.length" style="margin-bottom:10px">
              <div style="font-size:.75rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px">📌 Căn cứ đánh giá</div>
              <ul style="margin:0;padding-left:18px">
                <li v-for="(cc, ci) in result.danh_gia_hop_dong.can_cu_danh_gia" :key="ci" style="font-size:.84rem;color:#334155;margin-bottom:3px">{{ cc }}</li>
              </ul>
            </div>
            <!-- Lý do & Khuyến nghị -->
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
              <div v-if="result.danh_gia_hop_dong.ly_do" style="padding:10px 12px;background:#f8fafc;border-radius:8px;border-left:3px solid #6366f1">
                <div style="font-size:.72rem;font-weight:700;color:#6366f1;text-transform:uppercase;margin-bottom:4px">Lý do</div>
                <div style="font-size:.84rem;color:#334155;line-height:1.6">{{ result.danh_gia_hop_dong.ly_do }}</div>
              </div>
              <div v-if="result.danh_gia_hop_dong.khuyen_nghi" :style="result.danh_gia_hop_dong.du_dieu_kien ? 'padding:10px 12px;background:#f0fdf4;border-radius:8px;border-left:3px solid #22c55e' : 'padding:10px 12px;background:#fff7ed;border-radius:8px;border-left:3px solid #f59e0b'">
                <div style="font-size:.72rem;font-weight:700;text-transform:uppercase;margin-bottom:4px" :style="result.danh_gia_hop_dong.du_dieu_kien ? 'color:#16a34a' : 'color:#d97706'">Khuyến nghị</div>
                <div style="font-size:.84rem;color:#334155;line-height:1.6">{{ result.danh_gia_hop_dong.khuyen_nghi }}</div>
              </div>
            </div>
          </div>
        </div>
        <!-- ── Đánh giá đề xuất nhân sự ── -->
        <div v-if="result.danh_gia_de_xuat_nhan_su" class="result-card">
          <div class="rc-header rc-h-violet" @click="toggle('de_xuat_ns')">
            <span>
              {{ result.danh_gia_de_xuat_nhan_su.co_de_xuat ? '📝' : '📭' }}
              Đề xuất Nhân sự –
              {{ result.danh_gia_de_xuat_nhan_su.co_de_xuat
                  ? result.danh_gia_de_xuat_nhan_su.de_xuat?.length + ' đề xuất'
                  : 'Không có đề xuất' }}
            </span>
            <span class="rc-arrow" :class="{open:sec.de_xuat_ns}">›</span>
          </div>
          <div v-if="sec.de_xuat_ns" class="rc-body">
            <!-- Không có đề xuất -->
            <div v-if="!result.danh_gia_de_xuat_nhan_su.co_de_xuat" style="text-align:center;padding:20px;color:#94a3b8;font-size:.88rem">
              Không tìm thấy đề xuất nhân sự nào trong phiếu đánh giá.
            </div>

            <!-- Danh sách đề xuất -->
            <div v-for="(dx, dxi) in result.danh_gia_de_xuat_nhan_su.de_xuat" :key="dxi"
                 style="border:1px solid #e2e8f0;border-radius:10px;padding:14px 16px;margin-bottom:12px;"
                 :style="dx.phu_hop ? 'border-left:4px solid #22c55e;background:#f0fdf4' : 'border-left:4px solid #f59e0b;background:#fff7ed'">
              <!-- Header đề xuất -->
              <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">
                <div>
                  <span style="font-size:.72rem;font-weight:700;padding:3px 8px;border-radius:5px;text-transform:uppercase;letter-spacing:.04em"
                        :style="dx.phu_hop ? 'background:rgba(34,197,94,.15);color:#16a34a' : 'background:rgba(245,158,11,.15);color:#d97706'">
                    {{ dx.loai }}
                  </span>
                </div>
                <span style="font-size:.82rem;font-weight:700" :style="dx.phu_hop ? 'color:#16a34a' : 'color:#d97706'">
                  {{ dx.phu_hop ? '✅ Phù hợp' : '⚠️ Cần xem lại' }}
                </span>
              </div>

              <!-- Nội dung đề xuất -->
              <div style="font-size:.9rem;font-weight:600;color:#1e293b;margin-bottom:10px">{{ dx.noi_dung }}</div>

              <!-- Chi tiết 3 trường -->
              <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px">
                <div v-if="dx.can_cu" style="padding:8px 10px;background:rgba(255,255,255,.7);border-radius:6px">
                  <div style="font-size:.68rem;font-weight:700;color:#64748b;text-transform:uppercase;margin-bottom:3px">📌 Căn cứ</div>
                  <div style="font-size:.8rem;color:#334155;line-height:1.5">{{ dx.can_cu }}</div>
                </div>
                <div v-if="dx.ly_do" style="padding:8px 10px;background:rgba(255,255,255,.7);border-radius:6px">
                  <div style="font-size:.68rem;font-weight:700;color:#64748b;text-transform:uppercase;margin-bottom:3px">💬 Lý do</div>
                  <div style="font-size:.8rem;color:#334155;line-height:1.5">{{ dx.ly_do }}</div>
                </div>
                <div v-if="dx.khuyen_nghi" style="padding:8px 10px;background:rgba(255,255,255,.7);border-radius:6px">
                  <div style="font-size:.68rem;font-weight:700;color:#64748b;text-transform:uppercase;margin-bottom:3px">🔜 Khuyến nghị</div>
                  <div style="font-size:.8rem;color:#334155;line-height:1.5">{{ dx.khuyen_nghi }}</div>
                </div>
              </div>
            </div>

            <!-- Nhận xét chung -->
            <div v-if="result.danh_gia_de_xuat_nhan_su.nhan_xet_chung" style="padding:10px 14px;background:#f8fafc;border-radius:8px;border-left:3px solid #8b5cf6;font-size:.84rem;color:#334155;line-height:1.6">
              <span style="font-weight:700;color:#7c3aed">Nhận xét chung: </span>{{ result.danh_gia_de_xuat_nhan_su.nhan_xet_chung }}
            </div>
          </div>
        </div>

        <!-- ── Gợi ý JD ── -->
        <JdGoiY
          v-if="result.jd_goi_y"
          :jd="result.jd_goi_y"
          :expanded="sec.jd"
          @toggle="toggle('jd')"
        />

        <!-- Evidence -->
        <div v-if="result.evidence?.length" class="result-card">
          <div class="rc-header rc-h-green" @click="toggle('evidence')">
            <span>🔍 {{ store.lang==='en'?'Extracted Evidence':'Bằng chứng trích xuất' }} – {{ result.evidence.length }} mục</span>
            <span class="rc-arrow" :class="{open:sec.evidence}">›</span>
          </div>
          <div v-if="sec.evidence" class="rc-body">
            <div v-for="(ev,ei) in result.evidence" :key="ei" class="ev-item">
              <div class="ev-comp">{{ ev.mapped_competency || ev.competency }}</div>
              <div class="ev-text">{{ ev.statement || ev.evidence_text }}</div>
              <div v-if="ev.source_document || ev.source" class="ev-src">📄 {{ ev.source_document || ev.source }}</div>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import JdGoiY from '../components/JdGoiY.vue'
import { store, t } from '../store'

const inputMode = ref('default') // 'default' or 'scan'
const evalFile = ref(null), evalFileName = ref('')
const reportFile = ref(null), reportFileName = ref('')
const dailyReportFile = ref(null), dailyReportFileName = ref('')
const ngayBD = ref(''), ngayKT = ref('')  // format DD/MM/YYYY

// Parse DD/MM/YYYY → Date
function parseDMY(s) {
  if (!s) return null
  const m = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/)
  if (!m) return null
  const d = new Date(+m[3], +m[2] - 1, +m[1])
  return isNaN(d) ? null : d
}
// Auto-format as user types DD/MM/YYYY
function fmtDateInput(v) {
  const digits = v.replace(/\D/g, '').slice(0, 8)
  if (digits.length <= 2) return digits
  if (digits.length <= 4) return digits.slice(0,2) + '/' + digits.slice(2)
  return digits.slice(0,2) + '/' + digits.slice(2,4) + '/' + digits.slice(4)
}
// Convert DD/MM/YYYY → YYYY-MM-DD for API
function toISODate(dmy) {
  const m = dmy?.match(/^(\d{2})\/(\d{2})\/(\d{4})$/)
  return m ? `${m[3]}-${m[2]}-${m[1]}` : ''
}

const soNgayLamViec = computed(() => {
  const start = parseDMY(ngayBD.value)
  const end = parseDMY(ngayKT.value)
  if (!start || !end || end < start) return 0
  let count = 0
  const cur = new Date(start)
  while (cur <= end) {
    const dow = cur.getDay()
    if (dow !== 0 && dow !== 6) count++
    cur.setDate(cur.getDate() + 1)
  }
  return count
})
const tried = ref(false), loading = ref(false)
const result = ref(null), error = ref('')
const progress = reactive({ step: 0, total: 5, message: 'Đang chuẩn bị...' })
const sec = reactive({ comp: true, rec: true, evidence: false, docwarn: true, nextsteps: true, assessment: true, bao_cao_ngay: true, quan_ly: true, hop_dong: true, de_xuat_ns: true, jd: true })
let evalName = ''
const uploadedDailyUrl = ref('')  // track uploaded daily report URL across confirm step

// OCR Review state
const ocrReview = ref(false)
const ocrEvalContent = ref({})
const ocrReportContent = ref({})
const ocrWarnings = ref([])
const ocrTab = ref('eval')
const ocrViewMode = ref('preview')
const ocrEditMode = reactive({ eval: false, report: false })
const ocrExtractedFields = ref([])

// Computed line counts not needed for JSON, but keep placeholders if used elsewhere
const ocrEvalLineCount = computed(() => 10)
const ocrReportLineCount = computed(() => 10)

// Update extracted field value and sync back to object content
function updateExtractedField(index, newValue) {
  const field = ocrExtractedFields.value[index]
  if (!field) return
  field.value = newValue

  // Sync to the JSON objects
  if (field.source === 'eval' && ocrEvalContent.value.thong_tin_nhan_vien) {
    if (field.key === 'Họ và tên') ocrEvalContent.value.thong_tin_nhan_vien.ho_ten = newValue
    if (field.key === 'MSNV') ocrEvalContent.value.thong_tin_nhan_vien.msnv = newValue
    if (field.key === 'Vị trí công việc') ocrEvalContent.value.thong_tin_nhan_vien.vi_tri = newValue
    if (field.key === 'Phòng ban') ocrEvalContent.value.thong_tin_nhan_vien.phong_ban = newValue
    if (field.key === 'Ngày bắt đầu HĐ') ocrEvalContent.value.thong_tin_nhan_vien.ngay_bat_dau_hd = newValue
    if (field.key === 'Ngày hết hạn HĐ') ocrEvalContent.value.thong_tin_nhan_vien.ngay_het_han_hd = newValue
  }
}

// Try to parse user edited JSON string
function tryParseJson(jsonString, docType) {
  try {
    const obj = JSON.parse(jsonString)
    if (docType === 'eval') ocrEvalContent.value = obj
    if (docType === 'report') ocrReportContent.value = obj
  } catch (e) {
    // Ignore parse error while typing
  }
}

// Parse extracted fields from OCR API response
function parseExtractedFields(evalFields, reportFields) {
  const fields = []
  const evalF = evalFields?.fields || {}
  const reportF = reportFields?.fields || {}

  // Eval form fields
  const evalLabels = [
    { key: 'Họ và tên', label: 'Họ và tên CBNV' },
    { key: 'MSNV', label: 'Mã số nhân viên (MSNV)' },
    { key: 'Vị trí công việc', label: 'Vị trí công việc' },
    { key: 'Phòng ban', label: 'Phòng – Ban – LL/Khối' },
    { key: 'Ngày bắt đầu HĐ', label: 'Ngày bắt đầu HĐ gần nhất' },
    { key: 'Ngày hết hạn HĐ', label: 'Ngày hết hạn HĐ' },
  ]
  for (const item of evalLabels) {
    fields.push({
      label: item.label,
      value: evalF[item.key] || '',
      key: item.key,
      source: 'eval',
    })
  }

  ocrExtractedFields.value = fields
}


// Computed for document warnings
const docWarningsList = computed(() => {
  if (!result.value?.document_warnings) return []
  return result.value.document_warnings.warnings || []
})
const docWarningsComplete = computed(() => {
  if (!result.value?.document_warnings) return true
  return result.value.document_warnings.is_complete === true
})

// Validation warnings
const validationWarningsList = computed(() => {
  if (!result.value?.validation_warnings) return []
  let val = result.value.validation_warnings
  if (typeof val === 'string') {
    try { val = JSON.parse(val) } catch(e) { val = [] }
  }
  return Array.isArray(val) ? val : []
})
const consistencyCheckWarnings = computed(() => {
  if (!result.value?.consistency_check) return {}
  let val = result.value.consistency_check
  if (typeof val === 'string') {
    try { val = JSON.parse(val) } catch(e) { val = {} }
  }
  return val || {}
})
const hasValidationWarnings = computed(() => {
  return validationWarningsList.value.length > 0
})
const totalWarningsCount = computed(() => {
  let cnt = 0
  if (!docWarningsComplete.value) {
    cnt += docWarningsList.value.length
  }
  if (validationWarningsList.value.length) cnt += validationWarningsList.value.length
  return cnt
})

// Computed for next steps
const nextStepsList = computed(() => {
  if (!result.value?.next_steps) return []
  // next_steps can be array or from recommendation_details
  if (Array.isArray(result.value.next_steps)) return result.value.next_steps
  // Try from recommendation_details
  const rd = result.value.recommendation_details
  if (rd && Array.isArray(rd.next_steps)) return rd.next_steps
  return []
})

function proposalColor(level) {
  if (level === 'Đồng ý') return 'green'
  if (level === 'Cần bổ sung') return 'yellow'
  if (level === 'Chưa đủ cơ sở') return 'orange'
  return 'red'
}
function urgencyColor(level) {
  if (level === 'Bình thường') return 'green'
  if (level === 'Cần xử lý sớm') return 'yellow'
  return 'red'
}

function drop(e, t) {
  const f = e.dataTransfer.files[0]
  if (!f) return
  if (t === 'eval') { evalFile.value = f; evalFileName.value = f.name }
  else if (t === 'daily') { dailyReportFile.value = f; dailyReportFileName.value = f.name }
  else { reportFile.value = f; reportFileName.value = f.name }
}
function pickFile(e, t) {
  const f = e.target.files[0]
  if (!f) return
  if (t === 'eval') { evalFile.value = f; evalFileName.value = f.name }
  else if (t === 'daily') { dailyReportFile.value = f; dailyReportFileName.value = f.name }
  else { reportFile.value = f; reportFileName.value = f.name }
}
function toggle(k) { sec[k] = !sec[k] }

const BASE = '/api/method/cnb_2as.api.evaluation'

// CSRF token cache
let csrfToken = ''

async function fetchCsrfToken() {
  // Try window.frappe first (if Frappe JS is loaded)
  if (window.frappe?.csrf_token) {
    csrfToken = window.frappe.csrf_token
    return csrfToken
  }
  // Try cookie
  const c = document.cookie.split('; ').find(r => r.startsWith('csrf_token='))
  if (c) {
    csrfToken = decodeURIComponent(c.split('=')[1])
    return csrfToken
  }
  // Dev mode: ignore_csrf is set, token not needed
  return ''
}

function csrf() {
  return csrfToken
}

const hdrs = () => ({ 'X-Frappe-CSRF-Token': csrf(), 'Content-Type': 'application/json', 'Accept': 'application/json' })

// Wrapper for fetch that always includes credentials (session cookie)
function apiFetch(url, opts = {}) {
  return fetch(url, { ...opts, credentials: 'include' })
}

async function uploadFile(file) {
  // Ensure CSRF token is available
  if (!csrfToken) await fetchCsrfToken()

  const fd = new FormData()
  fd.append('file', file)
  fd.append('is_private', '1')
  fd.append('folder', 'Home')
  const r = await apiFetch('/api/method/upload_file', {
    method: 'POST',
    body: fd,
    headers: { 'X-Frappe-CSRF-Token': csrf() },
  })
  const j = await r.json()
  if (!r.ok) throw new Error(j?.exception || 'Upload thất bại')
  return j.message
}

async function doEvaluate() {
  tried.value = true
  if (!evalFile.value || !reportFile.value) return
  loading.value = true; error.value = ''; result.value = null; ocrReview.value = false
  progress.step = 1; progress.message = store.lang==='en'?'Uploading files...':'Đang upload file...'

  try {
    // Upload required files
    const [f1, f2] = await Promise.all([uploadFile(evalFile.value), uploadFile(reportFile.value)])
    // Upload optional daily report
    let f3 = null
    if (dailyReportFile.value) {
      f3 = await uploadFile(dailyReportFile.value)
    }

    if (inputMode.value === 'scan') {
      // Scan mode: OCR via OpenAI Vision (fast, ~10-30s)
      progress.step = 2; progress.message = t('ocr_processing')

      const r1 = await apiFetch(`${BASE}.run_evaluation_scan`, {
        method: 'POST', headers: hdrs(),
        body: JSON.stringify({ eval_file: f1.file_url, work_report_file: f2.file_url })
      })
      const j1 = await r1.json()
      if (!r1.ok) throw new Error(j1?.exception || 'OCR thất bại')

      const data = j1.message
      evalName = data.evaluation_name
      try {
        ocrEvalContent.value = typeof data.ocr_eval_content === 'string' ? JSON.parse(data.ocr_eval_content || '{}') : (data.ocr_eval_content || {})
        ocrReportContent.value = typeof data.ocr_report_content === 'string' ? JSON.parse(data.ocr_report_content || '{}') : (data.ocr_report_content || {})
      } catch (e) {
        console.error("JSON parse error:", e)
        ocrEvalContent.value = {}
        ocrReportContent.value = {}
      }
      ocrWarnings.value = data.all_warnings || []
      parseExtractedFields(data.eval_fields, data.report_fields)
      ocrViewMode.value = 'preview'
      ocrReview.value = true
      loading.value = false
      // Save daily report URL so confirmOcr can pass it to backend
      uploadedDailyUrl.value = f3?.file_url || ''

    } else {
      // Default mode: direct evaluation
      progress.step = 2; progress.message = store.lang==='en'?'AI is scoring...':'AI đang phân tích...'

      const r1 = await apiFetch(`${BASE}.run_evaluation`, {
        method: 'POST', headers: hdrs(),
        body: JSON.stringify({
          eval_file: f1.file_url,
          work_report_file: f2.file_url,
          daily_report_file: f3?.file_url || '',
          ngay_bd: toISODate(ngayBD.value) || '',
          ngay_kt: toISODate(ngayKT.value) || '',
        })
      })
      const j1 = await r1.json()
      if (!r1.ok) throw new Error(j1?.exception || 'Tạo đánh giá thất bại')
      evalName = j1.message?.evaluation_name || j1.message?.name || j1.message

      await pollForResults()
    }
  } catch(e) { error.value = e.message; loading.value = false }
}

async function confirmOcr() {
  if (!evalName) return
  loading.value = true; error.value = ''
  // Giữ ocrReview = true để user vẫn thấy form chỉnh sửa phía trên và có thể sửa rồi gửi đánh giá lại
  progress.step = 1; progress.message = store.lang==='en'?'AI is analyzing...':'AI đang phân tích...'

  try {
    const r = await apiFetch(`${BASE}.confirm_ocr_and_evaluate`, {
      method: 'POST', headers: hdrs(),
      body: JSON.stringify({
        evaluation_name: evalName,
        ocr_eval_content: JSON.stringify(ocrEvalContent.value),
        ocr_report_content: JSON.stringify(ocrReportContent.value),
        daily_report_file: uploadedDailyUrl.value || '',
        ngay_bd: toISODate(ngayBD.value) || '',
        ngay_kt: toISODate(ngayKT.value) || '',
      })
    })
    const j = await r.json()
    if (!r.ok) throw new Error(j?.exception || 'Xác nhận OCR thất bại')

    await pollForResults()
  } catch(e) { error.value = e.message; loading.value = false }
}

async function pollForOcrResults() {
  progress.step = 2; progress.message = store.lang==='en'?'OCR processing in background...':'Đang OCR nền...'

  let attempts = 0
  const maxAttempts = 300 // 15 minutes max
  while (attempts < maxAttempts) {
    await new Promise(resolve => setTimeout(resolve, 3000))
    attempts++
    try {
      const r = await apiFetch(`${BASE}.get_ocr_preview`, {
        method: 'POST', headers: hdrs(),
        body: JSON.stringify({ evaluation_name: evalName })
      })
      const j = await r.json()
      if (!r.ok) continue
      const data = j.message
      if (data?.status === 'OCR Ready') {
        ocrEvalContent.value = data.ocr_eval_content || ''
        ocrReportContent.value = data.ocr_report_content || ''
        // Extract warnings from eval_fields + report_fields
        const evalWarns = data.eval_fields?.warnings || []
        const reportWarns = data.report_fields?.warnings || []
        ocrWarnings.value = [...evalWarns, ...reportWarns]
        parseExtractedFields(data.eval_fields, data.report_fields)
        ocrViewMode.value = 'preview'
        ocrReview.value = true
        loading.value = false
        return
      } else if (data?.status === 'Failed') {
        throw new Error(store.lang==='en'?'OCR processing failed':'OCR xử lý thất bại')
      }
    } catch(e) {
      if (e.message.includes('OCR')) throw e
      // Network error, keep trying
    }
    progress.message = store.lang==='en'?`OCR processing... (${attempts * 3}s)`:`Đang OCR... (${attempts * 3}s)`
  }
  throw new Error(store.lang==='en'?'OCR timeout':'OCR quá thời gian chờ')
}

async function pollForResults() {
  progress.step = 3; progress.message = store.lang==='en'?'Waiting for results...':'Đang chờ kết quả...'

  let attempts = 0
  const maxAttempts = 300 // 15 minutes max
  while (attempts < maxAttempts) {
    await new Promise(resolve => setTimeout(resolve, 3000))
    attempts++
    const r2 = await apiFetch(`${BASE}.get_evaluation_result`, {
      method: 'POST', headers: hdrs(),
      body: JSON.stringify({ evaluation_name: evalName })
    })
    const j2 = await r2.json()
    if (!r2.ok) continue
    const data = j2.message
    if (data?.status === 'Completed') {
      progress.step = 5; progress.message = store.lang==='en'?'Done!':'Hoàn tất!'
      result.value = data
      sec.comp = true; sec.rec = true; sec.evidence = false; sec.docwarn = true; sec.nextsteps = true
      break
    } else if (data?.status === 'Failed') {
      throw new Error(store.lang==='en'?'Evaluation failed':'Đánh giá thất bại')
    }
    progress.step = 3; progress.message = store.lang==='en'?`AI is analyzing... (${attempts})`:`AI đang phân tích... (${attempts})`
  }
  if (attempts >= maxAttempts) throw new Error(store.lang==='en'?'Timeout':'Quá thời gian chờ')
  loading.value = false
}

function formatRec(text) {
  if (!text) return ''
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
    .replace(/(ĐIỂM MẠNH|CẦN CẢI THIỆN|TIỀM NĂNG PHÁT TRIỂN|RỦI RO CẦN LƯU Ý|điểm mạnh|cần cải thiện|tiềm năng|rủi ro)/gi,
      '<span class="rec-label">$1</span>')
}

async function downloadPdf() {
  if (!result.value) return
  const r = result.value

  // ── Helper: escape HTML ──────────────────────────────────
  const esc = (s) => String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')

  // ── Helper: section heading (ThuViec style) ──────────────
  const secH3 = (title, extra='') =>
    `<div style="page-break-inside:avoid"><h3 style="margin-top:24px;border-left:4px solid #555;padding-left:10px;font-size:15px;color:#111">${title}${extra}</h3>`

  // ─────────────────────────────────────────────────────────
  // 1. HEADER + INFO TABLE
  // ─────────────────────────────────────────────────────────
  const evalDate = r.evaluation_date || new Date().toLocaleDateString('vi-VN', { day:'2-digit', month:'2-digit', year:'numeric' })
  let html = `
<div style="font-family:'Segoe UI',Arial,sans-serif;font-size:14px;color:#111;max-width:860px;margin:0 auto;padding:40px">
  <h2 style="border-bottom:2px solid #333;padding-bottom:10px;color:#111">BÁO CÁO ĐÁNH GIÁ TÁI KÝ HỢP ĐỒNG</h2>
  <p style="color:#555">CT Group · ${esc(evalDate)}</p>
  <table style="width:100%;border-collapse:collapse;margin:16px 0">
    <tr>
      <td style="padding:6px;background:#f5f5f5;width:130px;font-weight:600;border:1px solid #ddd">Họ và tên</td>
      <td style="padding:6px;border:1px solid #ddd">${esc(r.employee_name || '—')}</td>
      <td style="padding:6px;background:#f5f5f5;width:130px;font-weight:600;border:1px solid #ddd">Chức danh</td>
      <td style="padding:6px;border:1px solid #ddd">${esc(r.job_title || '—')}</td>
    </tr>
    <tr>
      <td style="padding:6px;background:#f5f5f5;font-weight:600;border:1px solid #ddd">Phòng ban / Đơn vị</td>
      <td style="padding:6px;border:1px solid #ddd">${esc(r.department || '—')}</td>
      <td style="padding:6px;background:#f5f5f5;font-weight:600;border:1px solid #ddd">Ngày đánh giá</td>
      <td style="padding:6px;border:1px solid #ddd">${esc(evalDate)}</td>
    </tr>
    <tr>
      <td style="padding:6px;background:#f5f5f5;font-weight:600;border:1px solid #ddd">Ngày bắt đầu HĐ</td>
      <td style="padding:6px;border:1px solid #ddd">${esc(r.contract_start_date || r.ngay_bat_dau_hd || '—')}</td>
      <td style="padding:6px;background:#f5f5f5;font-weight:600;border:1px solid #ddd">Ngày kết thúc HĐ</td>
      <td style="padding:6px;border:1px solid #ddd">${esc(r.contract_end_date || r.ngay_het_han_hd || '—')}</td>
    </tr>
  </table>

  <h3 style="color:#111">Kết quả đánh giá: <span style="font-weight:800">${esc(r.recommendation || '—')}</span>
    ${r.overall_score != null ? `<span style="margin-left:10px;font-size:13px;border:1px solid #ccc;padding:2px 10px;border-radius:4px;font-weight:700">Điểm tổng: ${Number(r.overall_score).toFixed(1)}</span>` : ''}
  </h3>
  <p style="background:#f5f5f5;padding:12px;border-radius:4px;line-height:1.7;border:1px solid #ddd">${esc(r.recommendation_reasoning || '—')}</p>
`

  // ─────────────────────────────────────────────────────────
  // 2. BẢNG ĐIỂM NĂNG LỰC
  // ─────────────────────────────────────────────────────────
  if (r.competency_scores?.length) {
    html += secH3('Bảng Điểm Năng Lực')
    html += `<table style="width:100%;border-collapse:collapse;margin-bottom:16px;font-size:13px;page-break-inside:avoid">
      <thead><tr style="background:#eee">
        <th style="padding:8px 10px;border:1px solid #ccc;width:40px;text-align:center">STT</th>
        <th style="padding:8px 10px;border:1px solid #ccc">Năng lực</th>
        <th style="padding:8px 10px;border:1px solid #ccc;width:90px;text-align:center">Trọng số (%)</th>
        <th style="padding:8px 10px;border:1px solid #ccc;width:70px;text-align:center">Điểm</th>
      </tr></thead>
      <tbody>`
    r.competency_scores.forEach((c, i) => {
      const score = typeof c.score === 'number' ? c.score.toFixed(1) : (c.score || '—')
      html += `<tr style="background:${i%2===0?'#f9f9f9':'#fff'}">
        <td style="padding:6px 10px;border:1px solid #ddd;text-align:center">${i+1}</td>
        <td style="padding:6px 10px;border:1px solid #ddd">${esc(c.name || c.competency_name)}</td>
        <td style="padding:6px 10px;border:1px solid #ddd;text-align:center">${c.weight}%</td>
        <td style="padding:6px 10px;border:1px solid #ddd;text-align:center;font-weight:700">${score}</td>
      </tr>`
    })
    html += `</tbody>
      <tfoot><tr style="background:#eee;font-weight:700">
        <td colspan="3" style="padding:8px 10px;border:1px solid #ccc;text-align:right">ĐIỂM TỔNG</td>
        <td style="padding:8px 10px;border:1px solid #ccc;text-align:center;font-size:16px">${r.overall_score?.toFixed(1) || '—'}</td>
      </tr></tfoot>
    </table>
    <div style="border-left:3px solid #999;padding:6px 10px;font-size:12px;margin-bottom:8px;font-style:italic">📌 Dựa trên vị trí/chuyên môn công việc để xác định tỷ trọng đánh giá phù hợp.</div>
    </div>`
  }

  // ─────────────────────────────────────────────────────────
  // 3. BÁO CÁO NGÀY
  // ─────────────────────────────────────────────────────────
  if (r.bao_cao_ngay) {
    const bc = r.bao_cao_ngay
    const pct = Math.min(100, Math.round((bc.so_ngay_da_bc||0) / (bc.so_ngay_can_bc||1) * 100))
    const barColor = pct >= 100 ? '#10b981' : pct >= 80 ? '#f59e0b' : '#ef4444'
    html += secH3('Báo cáo ngày',
      ` <span style="margin-left:8px;font-size:12px;background:#e0f2fe;color:#0369a1;padding:2px 10px;border-radius:999px;font-weight:700">${bc.so_ngay_da_bc??'?'}/${bc.so_ngay_can_bc??'?'} ngày</span>`)
    html += `<div style="border:1px solid #ccc;border-radius:4px;padding:14px;background:#f9f9f9">
      <!-- Progress bar -->
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
        <div style="flex:1;background:#e2e8f0;border-radius:999px;height:10px;overflow:hidden">
          <div style="height:100%;background:${barColor};width:${pct}%;border-radius:999px"></div>
        </div>
        <span style="font-size:12px;font-weight:700;color:${barColor};width:36px;text-align:right">${pct}%</span>
      </div>
      <!-- Stats -->
      <div style="display:flex;flex-direction:column;gap:5px;margin-bottom:10px">
        ${bc.so_ngay_du_hang_muc != null ? `<div style="font-size:12px;padding:5px 9px;border-radius:4px;background:rgba(16,185,129,.08);color:#065f46">✅ Đủ hạng mục: <b>${bc.so_ngay_du_hang_muc}</b> ngày</div>` : ''}
        ${bc.ngay_thieu_hang_muc?.length ? `<div style="font-size:12px;padding:5px 9px;border-radius:4px;background:rgba(245,158,11,.08);color:#92400e">⚠️ Thiếu hạng mục: <b>${bc.ngay_thieu_hang_muc.length}</b> ngày (${bc.ngay_thieu_hang_muc.join(', ')})</div>` : ''}
        ${bc.ngay_thieu_bao_cao?.length ? `<div style="font-size:12px;padding:5px 9px;border-radius:4px;background:rgba(239,68,68,.08);color:#991b1b">❌ Thiếu báo cáo: <b>${bc.ngay_thieu_bao_cao.length}</b> ngày (${bc.ngay_thieu_bao_cao.join(', ')})</div>` : ''}
      </div>
      ${bc.nhan_xet ? `<div style="font-size:13px;padding:8px 10px;border-left:3px solid #999;background:#fff;border-radius:2px;margin-bottom:10px">📌 ${esc(bc.nhan_xet)}</div>` : ''}
      ${bc.doi_chieu_cong_viec?.length ? `
        <div style="margin-top:10px">
          <div style="font-weight:700;font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:#555;margin-bottom:6px">📋 Đối chiếu nội dung báo cáo ngày vs Phiếu đánh giá</div>
          <table style="width:100%;border-collapse:collapse;font-size:12px">
            <thead><tr style="background:#eee">
              <th style="padding:6px 8px;border:1px solid #ccc">Hạng mục (Báo cáo ngày)</th>
              <th style="padding:6px 8px;border:1px solid #ccc;width:100px;text-align:center">Có trong phiếu</th>
              <th style="padding:6px 8px;border:1px solid #ccc">Ghi chú</th>
            </tr></thead>
            <tbody>
              ${bc.doi_chieu_cong_viec.map((d,i) => `<tr style="background:${i%2===0?'#f5f5f5':'#fff'}">
                <td style="padding:5px 8px;border:1px solid #ddd">${esc(d.hang_muc||'—')}</td>
                <td style="padding:5px 8px;border:1px solid #ddd;text-align:center;font-weight:700;color:${d.co_trong_phieu?'#16a34a':'#dc2626'}">${d.co_trong_phieu?'✅ Có':'❌ Không'}</td>
                <td style="padding:5px 8px;border:1px solid #ddd;color:#555;font-style:italic">${esc(d.ghi_chu||'—')}</td>
              </tr>`).join('')}
            </tbody>
          </table>
        </div>` : ''}
    </div></div>`
  }


  // ─────────────────────────────────────────────────────────
  // 4. ĐÁNH GIÁ ĐIỀU KIỆN HỢP ĐỒNG
  // ─────────────────────────────────────────────────────────
  if (r.danh_gia_hop_dong) {
    const hd = r.danh_gia_hop_dong
    html += secH3('Đánh giá điều kiện hợp đồng')
    html += `<div style="border:1px solid #ccc;border-radius:4px;padding:14px;background:#f9f9f9">
      <div style="font-weight:800;font-size:15px;margin-bottom:6px">${esc(hd.loai_hop_dong_de_xuat || '—')}
        ${hd.thoi_han_de_xuat ? ` · <span style="font-weight:400;font-size:13px">${esc(hd.thoi_han_de_xuat)}</span>` : ''}
      </div>
      ${hd.muc_do_khuyen_nghi ? `<div style="font-size:13px;margin-bottom:8px"><b>Mức độ khuyến nghị:</b> ${esc(hd.muc_do_khuyen_nghi)}</div>` : ''}
      ${hd.phan_tich_tong_the ? `<div style="font-size:13px;line-height:1.75;margin-bottom:10px;padding:8px 10px;background:#fff;border-left:3px solid #999;border-radius:2px">${esc(hd.phan_tich_tong_the)}</div>` : ''}`

    // Bảng tiêu chí
    if (hd.cac_tieu_chi?.length) {
      html += `<table style="width:100%;border-collapse:collapse;font-size:12px;margin-bottom:10px">
        <thead><tr style="background:#eee">
          <th style="padding:6px 10px;border:1px solid #ccc">Tiêu chí</th>
          <th style="padding:6px 8px;border:1px solid #ccc;width:55px;text-align:center">Đạt</th>
          <th style="padding:6px 8px;border:1px solid #ccc;width:70px;text-align:center">Điểm</th>
          <th style="padding:6px 10px;border:1px solid #ccc">Mô tả</th>
          <th style="padding:6px 10px;border:1px solid #ccc;width:28%">Căn cứ</th>
        </tr></thead>
        <tbody>
          ${hd.cac_tieu_chi.map((tc, i) => `<tr style="background:${i%2===0?'#f9f9f9':'#fff'};page-break-inside:avoid">
            <td style="padding:6px 10px;border:1px solid #ddd;font-weight:600">${esc(tc.tieu_chi)}</td>
            <td style="padding:6px 8px;border:1px solid #ddd;text-align:center;font-weight:700">${tc.dat ? 'Đạt' : 'Chưa đạt'}</td>
            <td style="padding:6px 8px;border:1px solid #ddd;text-align:center;font-weight:700">${typeof tc.diem_so === 'number' ? tc.diem_so.toFixed(1)+'/10' : '—'}</td>
            <td style="padding:6px 10px;border:1px solid #ddd">${esc(tc.mo_ta || '—')}</td>
            <td style="padding:6px 10px;border:1px solid #ddd;font-style:italic;color:#555">${esc(tc.can_cu || '—')}</td>
          </tr>`).join('')}
        </tbody>
      </table>`
    }

    // Lý do & Khuyến nghị
    if (hd.ly_do) {
      html += `<div style="margin-bottom:8px;padding:7px 10px;background:#fff;border-left:3px solid #999;border-radius:2px">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;margin-bottom:3px">Lý do</div>
        <div style="font-size:13px;line-height:1.75">${esc(hd.ly_do)}</div>
      </div>`
    }
    if (hd.khuyen_nghi) {
      html += `<div style="margin-bottom:8px;padding:7px 10px;background:#fff;border-left:3px solid #555;border-radius:2px">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;margin-bottom:3px">Khuyến nghị</div>
        <div style="font-size:13px;font-weight:600;line-height:1.75">${esc(hd.khuyen_nghi)}</div>
      </div>`
    }
    if (hd.dieu_kien_kem_theo) {
      html += `<div style="padding:7px 10px;background:#fff;border:1px solid #ddd;border-radius:2px">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;margin-bottom:3px">⚠ Điều kiện kèm theo</div>
        <div style="font-size:13px;line-height:1.6">${esc(hd.dieu_kien_kem_theo)}</div>
      </div>`
    }
    html += `</div></div>`
  }

  // ─────────────────────────────────────────────────────────
  // 5. ĐÁNH GIÁ ĐỀ XUẤT NHÂN SỰ
  // ─────────────────────────────────────────────────────────
  if (r.danh_gia_de_xuat_nhan_su) {
    const dxns = r.danh_gia_de_xuat_nhan_su
    html += secH3('Đánh giá đề xuất nhân sự')
    html += `<div style="border:1px solid #ccc;border-radius:4px;padding:14px;background:#f9f9f9">`
    if (!dxns.co_de_xuat || !dxns.de_xuat?.length) {
      html += `<div style="text-align:center;padding:12px;color:#999;font-style:italic">Không tìm thấy đề xuất nhân sự trong phiếu đánh giá.</div>`
    } else {
      dxns.de_xuat.forEach((dx, i) => {
        html += `<div style="border:1px solid #ddd;border-radius:4px;padding:10px;margin-bottom:8px;background:#fff">
          <div style="font-weight:700;font-size:13px;margin-bottom:6px">[${esc(dx.loai)}] ${esc(dx.noi_dung)}</div>
          <div style="font-size:13px;margin-bottom:4px"><b>Mức độ:</b> ${esc(dx.muc_do || '—')}${dx.uu_tien ? ` · <b>Ưu tiên:</b> ${esc(dx.uu_tien)}` : ''}</div>
          ${dx.can_cu ? `<div style="font-size:12px;margin-bottom:4px"><b>Căn cứ:</b> ${esc(dx.can_cu)}</div>` : ''}
          ${dx.ly_do ? `<div style="font-size:12px;margin-bottom:4px"><b>Lý do:</b> ${esc(dx.ly_do)}</div>` : ''}
          ${dx.khuyen_nghi ? `<div style="font-size:12px;margin-bottom:4px"><b>Khuyến nghị:</b> ${esc(dx.khuyen_nghi)}</div>` : ''}
          ${dx.tac_dong_du_kien ? `<div style="font-size:12px;border-left:3px solid #999;padding-left:8px;margin-top:4px"><i>Tác động dự kiến: ${esc(dx.tac_dong_du_kien)}</i></div>` : ''}
        </div>`
      })
      if (dxns.nhan_xet_chung) {
        html += `<div style="padding:8px 10px;border-left:3px solid #555;background:#fff;font-size:13px;line-height:1.7"><b>Nhận xét chung:</b> ${esc(dxns.nhan_xet_chung)}</div>`
      }
    }
    html += `</div></div>`
  }

  // ─────────────────────────────────────────────────────────
  // 6. ĐÁNH GIÁ ĐỀ XUẤT QUẢN LÝ
  // ─────────────────────────────────────────────────────────
  if (r.danh_gia_quan_ly) {
    const ql = r.danh_gia_quan_ly
    html += secH3('Đánh giá đề xuất quản lý',
      ql.hop_ly != null ? ` <span style="margin-left:8px;font-size:12px;border:1px solid #ccc;padding:2px 8px;border-radius:4px">${ql.muc_do_dong_y || (ql.hop_ly !== false ? 'Đồng ý' : 'Cần xem xét')}</span>` : '')
    html += `<div style="border:1px solid #ccc;border-radius:4px;padding:14px;background:#f9f9f9">
      ${ql.de_xuat_quan_ly ? `<div style="font-weight:700;font-size:13px;font-style:italic;margin-bottom:8px;padding-bottom:8px;border-bottom:1px solid #ddd">
        <span style="font-size:11px;font-weight:600;font-style:normal;display:block;margin-bottom:2px;text-transform:uppercase;letter-spacing:.04em">Đề xuất của Quản lý / TBP / HOD</span>
        ${esc(ql.de_xuat_quan_ly)}
      </div>` : ''}
      ${ql.ly_do_chinh ? `<div style="margin-bottom:8px;padding:7px 10px;background:#fff;border-left:3px solid #999;border-radius:2px">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;margin-bottom:3px">Lý do chính</div>
        <div style="font-size:13px;font-weight:600">${esc(ql.ly_do_chinh)}</div>
      </div>` : ''}
      ${ql.phan_tich_chi_tiet ? `<div style="margin-bottom:8px">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;margin-bottom:3px">Phân tích chi tiết</div>
        <div style="font-size:13px;line-height:1.75">${esc(ql.phan_tich_chi_tiet)}</div>
      </div>` : ''}
      ${ql.nhan_xet ? `<div style="margin-bottom:8px;padding:7px 10px;background:#fff;border:1px solid #ddd;border-radius:2px">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;margin-bottom:3px">Nhận xét</div>
        <div style="font-size:13px;line-height:1.7">${esc(ql.nhan_xet)}</div>
      </div>` : ''}
      ${ql.khuyen_nghi_xu_ly ? `<div style="padding:7px 10px;background:#fff;border-left:3px solid #555;border-radius:2px">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;margin-bottom:3px">Khuyến nghị xử lý</div>
        <div style="font-size:13px;font-weight:600">${esc(ql.khuyen_nghi_xu_ly)}</div>
      </div>` : ''}
    </div></div>`
  }

  // ─────────────────────────────────────────────────────────
  // 7. GỢI Ý JD
  // ─────────────────────────────────────────────────────────
  if (r.jd_goi_y) {
    const jd = r.jd_goi_y
    html += `<div style="page-break-inside:avoid;margin-top:28px">
    <h3 style="border-left:4px solid #333;padding-left:10px;font-size:15px;color:#111;margin-bottom:0">Gợi ý Mô tả Công việc (JD)</h3>
    <div style="border:1px solid #bbb;border-radius:4px;overflow:hidden;margin-top:10px">
      <div style="background:#333;color:#fff;padding:10px 16px;display:flex;justify-content:space-between;align-items:center">
        <div>
          <div style="font-size:14px;font-weight:700;letter-spacing:.02em">${esc(jd.chuc_danh||'—')}</div>
          ${jd.phong_ban?`<div style="font-size:11px;opacity:.8;margin-top:2px">${esc(jd.phong_ban)}</div>`:''}
        </div>
        ${jd.cap_bac?`<div style="font-size:11px;border:1px solid rgba(255,255,255,.5);padding:2px 10px;border-radius:3px">${esc(jd.cap_bac)}</div>`:''}
      </div>
      <div style="padding:16px;background:#fff">
        ${jd.tom_tat?`<p style="line-height:1.75;margin:0 0 16px;font-size:13px;color:#333;font-style:italic;border-bottom:1px solid #eee;padding-bottom:12px">${esc(jd.tom_tat)}</p>`:''}
        ${jd.nhiem_vu_chinh?.length?`
          <div style="margin-bottom:16px">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#555;margin-bottom:8px;padding-bottom:4px;border-bottom:1px solid #eee">Nhiệm vụ chính</div>
            <ol style="margin:0;padding-left:18px">
              ${jd.nhiem_vu_chinh.map(t=>`<li style="margin-bottom:5px;font-size:13px;line-height:1.6">${esc(t)}</li>`).join('')}
            </ol>
          </div>`:''}
        ${jd.yeu_cau_nang_luc?.length?`
          <div style="margin-bottom:16px">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#555;margin-bottom:8px;padding-bottom:4px;border-bottom:1px solid #eee">Yêu cầu năng lực</div>
            <table style="width:100%;border-collapse:collapse;font-size:13px">
              ${jd.yeu_cau_nang_luc.map((y,i)=>`
                <tr style="background:${i%2===0?'#f9f9f9':'#fff'}">
                  <td style="padding:6px 10px;border:1px solid #e5e5e5;font-weight:600;width:120px;vertical-align:top">${esc(y.loai)}</td>
                  <td style="padding:6px 10px;border:1px solid #e5e5e5;line-height:1.6">${esc(y.mo_ta)}</td>
                </tr>`).join('')}
            </table>
          </div>`:''}
        ${(jd.yeu_cau_kinh_nghiem||jd.trinh_do_hoc_van)?`
          <div style="margin-bottom:8px">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#555;margin-bottom:8px;padding-bottom:4px;border-bottom:1px solid #eee">Yêu cầu khác</div>
            <div style="display:flex;gap:24px;font-size:13px">
              ${jd.yeu_cau_kinh_nghiem?`<div><b>Kinh nghiệm:</b> ${esc(jd.yeu_cau_kinh_nghiem)}</div>`:''}
              ${jd.trinh_do_hoc_van?`<div><b>Học vấn:</b> ${esc(jd.trinh_do_hoc_van)}</div>`:''}
            </div>
          </div>`:''}
        ${jd.kpi_tham_chieu?.length?`
          <div style="margin-bottom:8px">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:#555;margin-bottom:6px;padding-bottom:4px;border-bottom:1px solid #eee">KPI tham chiếu</div>
            <ul style="margin:0;padding-left:18px">
              ${jd.kpi_tham_chieu.map(k=>`<li style="font-size:13px;margin-bottom:3px">${esc(k)}</li>`).join('')}
            </ul>
          </div>`:''}
        ${jd.ghi_chu?`<div style="margin-top:12px;padding:8px 12px;background:#f5f5f5;border-left:3px solid #999;font-size:12px;font-style:italic">${esc(jd.ghi_chu)}</div>`:''}
      </div>
    </div></div>`
  }

  // ─────────────────────────────────────────────────────────
  // 8. VIỆC CẦN LÀM TIẾP THEO
  // ─────────────────────────────────────────────────────────
  const nsList = nextStepsList.value
  if (nsList.length) {
    html += secH3('Việc cần làm tiếp theo')
    html += `<table style="width:100%;border-collapse:collapse;font-size:13px">
      <thead><tr style="background:#eee">
        <th style="padding:6px 8px;border:1px solid #ccc;width:36px">#</th>
        <th style="padding:6px 8px;border:1px solid #ccc">Nội dung</th>
        <th style="padding:6px 8px;border:1px solid #ccc;width:70px">Ưu tiên</th>
        <th style="padding:6px 8px;border:1px solid #ccc;width:90px">Người phụ trách</th>
      </tr></thead>
      <tbody>
        ${nsList.map((ns, i) => `<tr style="background:${i%2===0?'#f9f9f9':'#fff'}">
          <td style="padding:6px 8px;border:1px solid #ddd;text-align:center">${i+1}</td>
          <td style="padding:6px 8px;border:1px solid #ddd">${esc(ns.action)}${ns.deadline_note ? `<br><small style="color:#666">⏰ ${esc(ns.deadline_note)}</small>` : ''}</td>
          <td style="padding:6px 8px;border:1px solid #ddd;text-align:center">${esc(ns.priority || '')}</td>
          <td style="padding:6px 8px;border:1px solid #ddd;text-align:center">${esc(ns.responsible || '')}</td>
        </tr>`).join('')}
      </tbody>
    </table></div>`
  }

  // Close main div
  html += `</div>`

  // ─────────────────────────────────────────────────────────
  // RENDER PDF via html2pdf.js
  // ─────────────────────────────────────────────────────────
  if (!window.html2pdf) {
    await new Promise((resolve, reject) => {
      const s = document.createElement('script')
      s.src = 'https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.2/html2pdf.bundle.min.js'
      s.onload = resolve; s.onerror = () => reject(new Error('Không tải được thư viện PDF'))
      document.head.appendChild(s)
    })
  }

  const nvName = (r.employee_name || 'NhanVien').replace(/\s+/g, '_')
  const worker = window.html2pdf().set({
    margin: [14, 16, 20, 16],
    filename: `BaoCao_TaiKy_${nvName}_${new Date().toISOString().slice(0,10)}.pdf`,
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
      const contentLines = Array.isArray(pageText) ? pageText.filter(l => typeof l === 'string' && l.trim().length > 0) : []
      if (contentLines.length <= 2) {
        pdf.deletePage(p)
      } else {
        break
      }
    }
    const finalTotal = pdf.internal.getNumberOfPages()
    for (let p = 1; p <= finalTotal; p++) {
      pdf.setPage(p)
      pdf.setFontSize(8)
      pdf.setTextColor(150)
      pdf.text(`Trang ${p} / ${finalTotal}`, w / 2, h - 6, { align: 'center' })
    }
  }).save()
}

function onProgress(data) {
  if (data) {
    progress.step = data.step || progress.step
    progress.total = data.total || progress.total
    progress.message = data.message || progress.message
  }
}
onMounted(async () => {
  // Fetch CSRF token on page load
  await fetchCsrfToken()

  if (window.frappe?.realtime) {
    window.frappe.realtime.on('eval_progress', onProgress)
  }
})
onUnmounted(() => {
  if (window.frappe?.realtime) {
    window.frappe.realtime.off('eval_progress', onProgress)
  }
})
</script>

<style scoped>
.app-layout { display: flex; height: 100vh; overflow: hidden; background: #f8fafc }

/* ── SIDEBAR ── */
.sidebar { width: 340px; flex-shrink: 0; display: flex; flex-direction: column; overflow-y: auto; border-right: 1px solid #e2e8f0; background: #fff }
.sb-top { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 18px; border-bottom: 1px solid #e2e8f0; background: #fff }
.sb-reload { width: 32px; height: 32px; border-radius: 8px; border: 1px solid #e2e8f0; background: #f8fafc; color: #64748b; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all .2s; }
.sb-reload:hover { background: #f1f5f9; color: #3b82f6; border-color: #cbd5e1; }
.sb-back { display: flex; align-items: center; justify-content: center; width: 32px; height: 32px; border-radius: 8px; background: #f1f5f9; color: #64748b; text-decoration: none; transition: all .2s; flex-shrink: 0 }
.sb-logo { display: flex; align-items: center; gap: 10px }
.sb-logo-mark { width: 36px; height: 36px; border-radius: 10px; display: flex; align-items: center; justify-content: center }
.sb-logo-violet { background: linear-gradient(135deg,#8b5cf6,#a855f7) }
.sb-name { font-size: .88rem; font-weight: 700; color: #1e293b }
.sb-org { font-size: .72rem; color: #64748b }
.sb-body { padding: 16px 16px; flex-grow: 1 }
.sb-section { margin-bottom: 20px }
.sb-section-title { font-size: .72rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: .08em; margin-bottom: 12px }

/* Mode Toggle */
.mode-toggle { display: flex; gap: 6px; margin-bottom: 4px }
.mode-btn { flex: 1; padding: 8px 6px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fff; color: #64748b; font-size: .75rem; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 4px; justify-content: center; transition: all .2s }
.mode-btn:hover { border-color: rgba(139,92,246,.4); background: rgba(139,92,246,.04) }
.mode-btn.active { border-color: #8b5cf6; background: rgba(139,92,246,.08); color: #7c3aed }
.mode-icon { font-size: 14px }

.sb-upload-card { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 10px; border: 1px dashed #cbd5e1; background: #f8fafc; cursor: pointer; margin-bottom: 8px; transition: all .2s }
.sb-upload-card:hover { border-color: #8b5cf6; background: rgba(139,92,246,.04) }
.sb-upload-card.filled { border-style: solid; border-color: #22c55e; background: rgba(34,197,94,.06) }
.sb-upload-card.err { border-color: #ef4444; background: rgba(239,68,68,.06) }
.sb-upload-optional { border-color: #0d9488; border-style: dashed; background: rgba(13,148,136,.04) }
.sb-upload-optional:hover { border-color: #0d9488; background: rgba(13,148,136,.08) }
.upc-opt-badge { font-size: .6rem; font-weight: 600; background: #0d9488; color: #fff; border-radius: 4px; padding: 1px 5px; margin-left: 4px; vertical-align: middle }
.sb-opt-divider { display: flex; align-items: center; gap: 8px; margin: 10px 0 6px; font-size: .65rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: .06em }
.sb-opt-divider::before, .sb-opt-divider::after { content: ''; flex: 1; height: 1px; background: #e2e8f0 }
.sb-date-range { background: rgba(13,148,136,.05); border: 1px solid rgba(13,148,136,.2); border-radius: 8px; padding: 10px 12px; margin-bottom: 8px }
.sb-date-row { display: flex; align-items: center; gap: 8px; margin-bottom: 6px }
.sb-date-row label { font-size: .7rem; font-weight: 600; color: #64748b; width: 60px; flex-shrink: 0 }
.sb-date-input { flex: 1; border: 1px solid #e2e8f0; border-radius: 6px; padding: 4px 8px; font-size: .78rem; color: #334155; background: #fff; outline: none }
.sb-date-input:focus { border-color: #0d9488; box-shadow: 0 0 0 2px rgba(13,148,136,.12) }
.sb-days-badge { font-size: .72rem; font-weight: 600; color: #0d9488; background: rgba(13,148,136,.1); border-radius: 6px; padding: 4px 10px; text-align: center; margin-top: 4px }

/* ── Daily date-range picker (ddr-style, same as ThuViec) ── */
.daily-date-range { background: rgba(99,102,241,.04); border: 1px solid rgba(99,102,241,.12); border-radius: 8px; padding: 10px 12px; margin-top: 6px; display: flex; flex-direction: column; gap: 6px; }
.ddr-row { display: flex; align-items: center; gap: 8px; }
.ddr-label { font-size: .75rem; color: #94a3b8; font-weight: 600; width: 55px; flex-shrink: 0; }
.ddr-input { flex: 1; min-width: 0; width: 100%; padding: 5px 8px; border-radius: 6px; border: 1px solid rgba(99,102,241,.2); background: transparent; color: inherit; font-size: .8rem; }
.ddr-input-wrap { flex: 1; min-width: 0; display: flex; align-items: center; gap: 4px; position: relative; }
.ddr-date-hidden { position: absolute; width: 0; height: 0; opacity: 0; pointer-events: none; }
.ddr-cal-btn { width: 28px; height: 28px; border-radius: 6px; border: 1px solid rgba(99,102,241,.2); background: rgba(99,102,241,.06); color: inherit; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 14px; transition: all .2s; flex-shrink: 0; }
.ddr-cal-btn:hover { background: rgba(99,102,241,.15); border-color: rgba(99,102,241,.4); }
.ddr-calc { font-size: .78rem; color: #818cf8; font-weight: 600; text-align: center; padding-top: 2px; }

/* ── Daily report result card bar ── */
.rc-h-daily { background: linear-gradient(90deg,rgba(6,182,212,.08),rgba(99,102,241,.05)); }
.daily-progress-chip { font-size: .78rem; font-weight: 700; padding: 2px 10px; border-radius: 99px; background: rgba(6,182,212,.12); color: #0891b2; margin-left: auto; }
.daily-bar-wrap { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.daily-bar { flex: 1; height: 10px; background: rgba(99,102,241,.1); border-radius: 99px; overflow: hidden; }
.daily-bar-fill { height: 100%; background: linear-gradient(90deg,#06b6d4,#6366f1); border-radius: 99px; transition: width .4s ease; }
.daily-bar-pct { font-size: .8rem; font-weight: 700; color: #6366f1; width: 36px; text-align: right; }
body.theme-dark .daily-date-range { border-color: rgba(99,102,241,.2); }
body.theme-dark .ddr-input { color: #e2e8f0; border-color: rgba(99,102,241,.25); }
body.theme-dark .ddr-input:focus { border-color: #8b5cf6; }
body.theme-dark .ddr-cal-btn { border-color: rgba(99,102,241,.25); }
body.theme-dark .daily-progress-chip { color: #22d3ee; background: rgba(6,182,212,.15); }
body.theme-dark .daily-bar-pct { color: #818cf8; }

.upc-icon { font-size: 24px; flex-shrink: 0 }
.upc-info { flex-grow: 1; min-width: 0 }
.upc-label { font-size: .72rem; font-weight: 600; color: #64748b }
.upc-hint { font-size: .65rem; color: #94a3b8; margin-top: 2px }
.upc-val { font-size: .8rem; color: #475569; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; display: block; field-sizing: content }
.upc-val.ok { color: #16a34a }
.upc-val.empty { color: #94a3b8 }
.upc-rm { width: 24px; height: 24px; border: none; background: rgba(239,68,68,.1); color: #ef4444; border-radius: 6px; cursor: pointer; font-size: .7rem; display: flex; align-items: center; justify-content: center }

.sb-err { font-size: .78rem; color: #ef4444; margin: 4px 0 }

.sb-btn-primary { width: 100%; padding: 10px; border: none; border-radius: 10px; background: linear-gradient(135deg,#8b5cf6,#a855f7); color: #fff; font-weight: 600; font-size: .88rem; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; transition: opacity .2s; margin-top: 8px }
.sb-btn-primary:disabled { opacity: .5; cursor: not-allowed }
.sb-btn-secondary { width: 100%; padding: 9px; border: 1px solid #8b5cf6; border-radius: 10px; background: #fff; color: #7c3aed; font-weight: 600; font-size: .84rem; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; margin-top: 12px; transition: all .2s }
.sb-btn-secondary:hover { background: rgba(139,92,246,.06) }

.spinner { width: 16px; height: 16px; border: 2px solid rgba(255,255,255,.3); border-top-color: #fff; border-radius: 50%; animation: spin .6s linear infinite }
@keyframes spin { to { transform: rotate(360deg) } }

.sb-badge { padding: 10px 14px; border-radius: 10px; display: flex; align-items: center; gap: 10px; margin-bottom: 12px }
.badge-pass { background: rgba(34,197,94,.08); border: 1px solid rgba(34,197,94,.25) }
.badge-fail { background: rgba(245,158,11,.08); border: 1px solid rgba(245,158,11,.25) }
.badge-icon { width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: .9rem }
.badge-pass .badge-icon { background: rgba(34,197,94,.15); color: #16a34a }
.badge-fail .badge-icon { background: rgba(245,158,11,.15); color: #d97706 }
.badge-text { font-size: .82rem; font-weight: 600; line-height: 1.3; color: #334155 }

/* Mini badges for proposal/urgency */
.sb-mini-badges { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px }
.sb-mini-badge { padding: 4px 10px; border-radius: 6px; font-size: .72rem; font-weight: 600 }
.mb-green { background: rgba(34,197,94,.1); color: #16a34a; border: 1px solid rgba(34,197,94,.2) }
.mb-yellow { background: rgba(234,179,8,.1); color: #a16207; border: 1px solid rgba(234,179,8,.2) }
.mb-orange { background: rgba(249,115,22,.1); color: #c2410c; border: 1px solid rgba(249,115,22,.2) }
.mb-red { background: rgba(239,68,68,.1); color: #dc2626; border: 1px solid rgba(239,68,68,.2) }

/* Contract decision badge */
.sb-contract-decision { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 10px; margin-bottom: 10px; border: 1.5px solid; }
.scd-yes { background: rgba(16,185,129,.08); border-color: rgba(16,185,129,.3); }
.scd-no  { background: rgba(239,68,68,.07);  border-color: rgba(239,68,68,.25); }
.scd-icon { font-size: 1.4rem; flex-shrink: 0; }
.scd-info { flex: 1; min-width: 0; }
.scd-label { font-size: .65rem; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; color: #64748b; margin-bottom: 2px; }
.scd-value { font-size: .82rem; font-weight: 800; line-height: 1.3; }
.scd-yes .scd-value { color: #059669; }
.scd-no  .scd-value { color: #dc2626; }

.sb-counts { display: flex; gap: 8px; margin-bottom: 8px }
.sc { flex: 1; text-align: center; padding: 8px 4px; border-radius: 8px; background: #f1f5f9 }
.sc-val { font-size: 1.2rem; font-weight: 800 }
.sc-val.score { color: #7c3aed }
.sc-val.ok { color: #16a34a }
.sc-val.warn { color: #d97706 }
.sc-lbl { font-size: .68rem; color: #64748b; margin-top: 2px }

.progress-text { font-size: .78rem; color: #64748b }

/* ── RESULT PANEL ── */
.result-panel { flex: 1; overflow-y: auto; background: #f8fafc }
.welcome { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; padding: 40px; text-align: center }
.welcome-icon { margin-bottom: 20px }
.welcome h1 { font-size: 1.5rem; font-weight: 800; margin-bottom: 10px; color: #1e293b }
.welcome p { max-width: 500px; color: #64748b; line-height: 1.6 }
.welcome-features { display: flex; gap: 20px; margin-top: 32px; flex-wrap: wrap; justify-content: center }
.wf { display: flex; align-items: center; gap: 8px; padding: 10px 16px; border-radius: 10px; background: #fff; border: 1px solid #e2e8f0; font-size: .84rem; color: #475569; font-weight: 500 }
.wf-icon { font-size: 1.2rem }

.loading-screen { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; gap: 16px }
.loading-spinner { width: 40px; height: 40px; border: 3px solid rgba(139,92,246,.15); border-top-color: #8b5cf6; border-radius: 50%; animation: spin 1s linear infinite }
.loading-screen p { font-weight: 600; color: #334155 }
.loading-sub { font-weight: 400 !important; font-size: .84rem; color: #64748b !important }
.error-card { margin: 24px; padding: 16px 20px; border-radius: 10px; background: rgba(239,68,68,.06); border: 1px solid rgba(239,68,68,.15); color: #dc2626; display: flex; align-items: center; gap: 10px }
.error-icon { font-size: 1.2rem }

/* ── OCR REVIEW (Inline Edit) ── */
.ocr-review-screen { max-width: 100% !important; padding: 30px 40px !important }
.rpt-th-mang { width: 16%; }
.rpt-th-mota { width: 34%; }

/* Editable Cells & Inputs */
.ocr-review-header { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 16px; padding: 16px 20px; background: #fff; border-radius: 14px; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,.04) }
.ocr-review-title { display: flex; align-items: center; gap: 12px }
.ocr-review-icon { width: 40px; height: 40px; border-radius: 10px; background: linear-gradient(135deg, #8b5cf6, #a855f7); display: flex; align-items: center; justify-content: center; color: #fff; flex-shrink: 0 }
.ocr-review-header h2 { font-size: 1rem; font-weight: 800; color: #1e293b; margin: 0 }
.ocr-review-subtitle { font-size: .75rem; color: #64748b; margin-top: 2px }
.ocr-confirm-btn-top { width: auto; padding: 9px 20px; white-space: nowrap; flex-shrink: 0; font-size: .82rem }

/* Document Tabs */
.ocr-doc-tabs { display: flex; gap: 4px; margin-bottom: 0 }
.ocr-doc-tab { flex: 1; padding: 11px 14px; border: 1px solid #e2e8f0; border-bottom: none; border-radius: 10px 10px 0 0; background: #f8fafc; color: #64748b; font-size: .82rem; font-weight: 600; cursor: pointer; transition: all .2s; display: flex; align-items: center; gap: 8px; justify-content: center }
.ocr-doc-tab:hover { background: #f1f5f9; color: #475569 }
.ocr-doc-tab.active { background: #fff; border-color: #e2e8f0; color: #7c3aed; border-bottom-color: #fff; position: relative; z-index: 1; margin-bottom: -1px }
.ocr-doc-tab-icon { font-size: 1rem }
.ocr-doc-tab-label { font-weight: 700 }

/* Content Card */
.ocr-content-card { background: #fff; border: 1px solid #e2e8f0; border-radius: 0 0 14px 14px; overflow: hidden; margin-bottom: 16px; box-shadow: 0 2px 8px rgba(0,0,0,.03) }

/* Info Section (Employee fields) */
.ocr-info-section { padding: 16px 20px; border-bottom: 1px solid #f1f5f9 }
.ocr-info-header { display: flex; align-items: center; gap: 8px; font-size: .78rem; font-weight: 700; color: #7c3aed; margin-bottom: 12px }
.ocr-info-header svg { color: #8b5cf6 }
.ocr-info-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px }
.ocr-info-row { display: flex; flex-direction: column; gap: 3px }
.ocr-info-row.ocr-info-missing .ocr-info-input { border-color: rgba(234,179,8,.4); background: rgba(234,179,8,.04) }
.ocr-info-label { display: flex; align-items: center; gap: 5px; font-size: .68rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: .03em }
.ocr-info-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0 }
.ocr-info-dot.dot-ok { background: #22c55e }
.ocr-info-dot.dot-warn { background: #f59e0b }
.ocr-info-input { width: 100%; padding: 7px 10px; border: 1px solid #e2e8f0; border-radius: 7px; background: #fafbfc; color: #1e293b; font-size: .85rem; font-weight: 600; outline: none; transition: all .2s }
.ocr-info-input:focus { border-color: #8b5cf6; background: #fff; box-shadow: 0 0 0 2px rgba(139,92,246,.08) }
.ocr-info-input::placeholder { color: #cbd5e1; font-weight: 400; font-style: italic; font-size: .78rem }

/* Edit Section (Textarea) */
.ocr-edit-section { padding: 0 }
.ocr-edit-header { display: flex; align-items: center; gap: 8px; padding: 12px 20px; font-size: .78rem; font-weight: 700; color: #475569; background: #fafbfc; border-bottom: 1px solid #f1f5f9 }
.ocr-edit-header svg { color: #8b5cf6 }
.ocr-toggle-edit { margin-left: auto; padding: 4px 12px; border: 1px solid #e2e8f0; border-radius: 6px; background: #fff; color: #64748b; font-size: .72rem; font-weight: 600; cursor: pointer; transition: all .2s }
.ocr-toggle-edit:hover { border-color: #8b5cf6; color: #7c3aed; background: rgba(139,92,246,.04) }
.ocr-edit-area { width: 100%; min-height: 500px; padding: 20px; border: none; background: #fff; color: #334155; font-family: 'JetBrains Mono', 'Fira Code', 'SF Mono', monospace; font-size: .85rem; line-height: 1.7; resize: vertical; outline: none }
.ocr-edit-area:focus { background: #fefffe }
.ocr-edit-area::placeholder { color: #cbd5e1 }

/* Rendered View (tables, headings, etc.) */
.ocr-rendered-view { padding: 20px 24px; max-height: 600px; overflow-y: auto; font-size: .88rem; line-height: 1.7; color: #334155 }
.ocr-rendered-view :deep(.ocr-md-h1) { font-size: 1.15rem; font-weight: 800; color: #1e293b; margin: 18px 0 10px; padding-bottom: 6px; border-bottom: 2px solid rgba(139,92,246,.15) }
.ocr-rendered-view :deep(.ocr-md-h2) { font-size: 1rem; font-weight: 700; color: #334155; margin: 14px 0 8px }
.ocr-rendered-view :deep(.ocr-md-h3) { font-size: .92rem; font-weight: 700; color: #475569; margin: 12px 0 6px }
.ocr-rendered-view :deep(.ocr-md-h4) { font-size: .85rem; font-weight: 700; color: #64748b; margin: 10px 0 4px }
.ocr-rendered-view :deep(.ocr-md-p) { margin: 2px 0; padding: 2px 0 }
.ocr-rendered-view :deep(.ocr-md-hr) { border: none; border-top: 1px solid #e2e8f0; margin: 14px 0 }
.ocr-rendered-view :deep(.ocr-md-spacer) { height: 6px }
.ocr-rendered-view :deep(.ocr-table-wrap) { overflow-x: auto; margin: 10px 0; border-radius: 10px; border: 1px solid #e2e8f0 }
.ocr-rendered-view :deep(.ocr-md-table) { width: 100%; border-collapse: collapse; font-size: .82rem }
.ocr-rendered-view :deep(.ocr-md-table th) { padding: 8px 12px; background: linear-gradient(135deg, #f0ecf9, #ede9fe); font-weight: 700; color: #5b21b6; text-align: left; border-bottom: 2px solid #ddd6fe; white-space: nowrap }
.ocr-rendered-view :deep(.ocr-md-table td) { padding: 7px 12px; border-bottom: 1px solid #f1f5f9; color: #334155 }
.ocr-rendered-view :deep(.ocr-md-table tr:hover td) { background: rgba(139,92,246,.03) }
.ocr-rendered-view :deep(.ocr-md-table tr:last-child td) { border-bottom: none }
.ocr-rendered-view :deep(strong) { color: #1e293b }

/* Status Bar (warnings) */
.ocr-status-bar { padding: 12px 16px; border-radius: 10px; margin: 12px 20px 16px; transition: all .3s }
.ocr-status-warn { background: linear-gradient(135deg, rgba(245,158,11,.06), rgba(234,179,8,.08)); border: 1px solid rgba(234,179,8,.25) }
.ocr-status-content { display: flex; align-items: flex-start; gap: 10px }
.ocr-status-icon { font-size: 1.1rem; flex-shrink: 0 }
.ocr-status-text { flex: 1 }
.ocr-status-text strong { font-size: .82rem; color: #1e293b; display: block }
.ocr-warn-tags { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 6px }
.ocr-warn-tag { padding: 3px 8px; border-radius: 5px; background: rgba(234,179,8,.12); color: #92400e; font-size: .7rem; font-weight: 600; border: 1px solid rgba(234,179,8,.2) }

/* Word Template Styles (kept for eval tab) */
.word-template-view { padding: 40px; max-height: 800px; overflow-y: auto; background: #fff; color: #000; font-family: 'Times New Roman', Times, serif; font-size: 11pt; line-height: 1.6; box-shadow: inset 0 0 10px rgba(0,0,0,0.05); }
.word-header { text-align: center; margin-bottom: 24px; }
.word-header h2 { font-size: 1.25rem; font-weight: bold; margin: 0; text-transform: uppercase; color: #4338ca; }
.word-h3 { font-size: 1.1rem; font-weight: bold; margin: 15px 0 5px; text-transform: uppercase; color: #4338ca; }
.word-table { width: 100%; border-collapse: collapse; margin-bottom: 15px; }
.word-table td, .word-table th { border: 1px solid #cbd5e1; padding: 10px 12px; vertical-align: top; }
.word-th { font-weight: 600; text-align: left; background: #eef2ff; color: #4338ca; }
.word-label { font-weight: bold; white-space: nowrap; width: 1%; background: #f8fafc; color: #334155; }
.word-input { width: 100%; border: none; background: transparent; font-family: 'Times New Roman', Times, serif; font-size: 11pt; outline: none; padding: 0; field-sizing: content; }
.word-textarea { width: 100%; min-height: 36px; border: none; background: transparent; font-family: 'Times New Roman', Times, serif; font-size: 11pt; line-height: 1.6; outline: none; padding: 2px 0; resize: vertical; overflow-y: auto; field-sizing: content; }
.word-textarea::-webkit-scrollbar { width: 3px; }
.word-textarea::-webkit-scrollbar-thumb { background: rgba(0,0,0,0.15); border-radius: 3px; }
.word-textarea::-webkit-scrollbar-thumb:hover { background: rgba(0,0,0,0.3); }
.word-textarea:focus, .word-input:focus { background: rgba(139, 92, 246, 0.05); }

/* ── Report Tab (ScanCombined-style) ── */
.rpt-doc { background: #fff; border-radius: 14px; padding: 24px; box-shadow: 0 4px 20px rgba(0,0,0,.07); width: 100%; max-width: 1400px; margin: 0 auto; max-height: 800px; overflow-y: auto; }
.rpt-title { text-align: center; font-size: 1rem; font-weight: 800; text-transform: uppercase; color: #1e293b; margin-bottom: 12px; }
.rpt-info-row { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; padding-bottom: 8px; border-bottom: 2px solid #e2e8f0; flex-wrap: wrap; }
.rpt-field-label { font-weight: 700; font-size: .88rem; white-space: nowrap; color: #374151; }
.rpt-inline-input { border: none; border-bottom: 2px solid rgba(99,102,241,.3); background: transparent; outline: none; color: inherit; flex: 1; font-size: .9rem; padding: 2px 4px; min-width: 80px; }
.rpt-inline-input:focus { border-bottom-color: #6366f1; }
.rpt-name { font-weight: 700 !important; }
.rpt-section-label { font-size: .7rem; font-weight: 800; text-transform: uppercase; letter-spacing: .06em; color: #6366f1; margin: 14px 0 4px; }
.rpt-nq-label { color: #f59e0b; }
.rpt-nq-note { font-size: .7rem; color: #94a3b8; margin-bottom: 6px; }
.rpt-table-wrap { overflow-x: auto; margin-bottom: 4px; border-radius: 8px; border: 1.5px solid #e2e8f0; }
.rpt-table { width: 100%; border-collapse: collapse; min-width: 860px; }
.rpt-nq-table { min-width: 620px; }
.rpt-th th { background: #f1f5f9; font-size: .67rem; font-weight: 700; text-transform: uppercase; padding: 6px 7px; border: 1px solid #d1d5db; color: #374151; text-align: center; }
.rpt-ths { font-size: .65rem !important; }
.rpt-thg { border-bottom: none !important; }
.rpt-th-kh { background: rgba(99,102,241,.07) !important; color: #6366f1 !important; }
.rpt-th-kq { background: rgba(16,185,129,.07) !important; color: #059669 !important; }
.rpt-row td { border: 1px solid #e2e8f0; padding: 0; vertical-align: top; }
.rpt-td-stt { width: 30px; text-align: center; font-weight: 700; color: #6366f1; padding: 7px; vertical-align: middle; }
.rpt-td-mang { width: 110px; } .rpt-td-mota { width: 250px; } .rpt-td-num { width: 62px; } .rpt-td-bod { width: 70px; } .rpt-td-link { width: 130px; }
.rpt-kqc { background: rgba(16,185,129,.03) !important; }
.rpt-kqb { font-weight: 700 !important; color: #059669 !important; }
.rpt-tc { text-align: center !important; }
.rpt-total-row td { border: 1px solid #e2e8f0; padding: 7px; }
.rpt-total-label { text-align: center; font-weight: 800; font-size: .8rem; background: #f8fafc; }
.rpt-input { width: 100%; border: none; background: transparent; outline: none; color: inherit; font-size: .78rem; padding: 5px 7px; font-family: inherit; field-sizing: content; }
.rpt-input:focus { background: rgba(99,102,241,.04); }
.rpt-ta { width: 100%; border: none; background: transparent; outline: none; color: inherit; font-size: .77rem; padding: 5px 7px; font-family: inherit; resize: vertical; min-height: 52px; field-sizing: content; }
.rpt-ta:focus { background: rgba(99,102,241,.04); }
.rpt-link-ta { font-size: .71rem; color: #6366f1; }
.rpt-xd-title { text-align: center; font-weight: 800; font-size: .8rem; text-transform: uppercase; color: #374151; margin: 14px 0 8px; }
.rpt-xd-table { margin: 0 auto; width: 50%; min-width: 320px; border-collapse: collapse; }
.rpt-xd-table th { background: #f1f5f9; border: 1px solid #d1d5db; padding: 6px 10px; font-size: .75rem; font-weight: 700; text-align: center; }
.rpt-xd-table td { border: 1px solid #e2e8f0; }
.rpt-xd-label { text-align: center; font-weight: 700; font-size: .8rem; padding: 8px; width: 66px; }
.rpt-xd-ranking { text-align: center; vertical-align: middle; }
.rpt-ranking-input { font-size: 1.1rem !important; font-weight: 800 !important; color: #6366f1 !important; }

/* Thin scrollbar for report doc */
.rpt-doc::-webkit-scrollbar { width: 4px; }
.rpt-doc::-webkit-scrollbar-track { background: transparent; }
.rpt-doc::-webkit-scrollbar-thumb { background: rgba(99,102,241,.2); border-radius: 4px; }
.rpt-doc::-webkit-scrollbar-thumb:hover { background: rgba(99,102,241,.4); }

/* Global thin scrollbar */
.sidebar::-webkit-scrollbar, .result-panel::-webkit-scrollbar, .results-scroll::-webkit-scrollbar { width: 4px; }
.sidebar::-webkit-scrollbar-track, .result-panel::-webkit-scrollbar-track, .results-scroll::-webkit-scrollbar-track { background: transparent; }
.sidebar::-webkit-scrollbar-thumb, .result-panel::-webkit-scrollbar-thumb, .results-scroll::-webkit-scrollbar-thumb { background: rgba(99,102,241,.15); border-radius: 4px; }
.sidebar::-webkit-scrollbar-thumb:hover, .result-panel::-webkit-scrollbar-thumb:hover, .results-scroll::-webkit-scrollbar-thumb:hover { background: rgba(99,102,241,.3); }

body.theme-dark .rpt-info-row { border-bottom-color: rgba(255,255,255,.08); }
body.theme-dark .rpt-table-wrap { border-color: rgba(255,255,255,.08); }
body.theme-dark .rpt-th th { background: #1e2030; color: #94a3b8; border-color: rgba(255,255,255,.07); }
body.theme-dark .rpt-row td { border-color: rgba(255,255,255,.06); }
body.theme-dark .rpt-total-row td { border-color: rgba(255,255,255,.06); }
body.theme-dark .rpt-total-label { background: #1a1a28; color: #f1f5f9; }
body.theme-dark .rpt-xd-title { color: #f1f5f9; }
body.theme-dark .rpt-xd-table th { background: #1e2030; color: #94a3b8; border-color: rgba(255,255,255,.08); }
body.theme-dark .rpt-xd-table td { border-color: rgba(255,255,255,.06); }
body.theme-dark .rpt-nq-note { color: #64748b; }

/* Confirm Bottom */
.ocr-confirm-bottom { text-align: center; padding: 6px 0 20px }
.ocr-confirm-btn-lg { width: auto; display: inline-flex; padding: 12px 36px; font-size: .9rem; border-radius: 10px; gap: 8px; box-shadow: 0 4px 14px rgba(139,92,246,.25); transition: all .2s }
.ocr-confirm-btn-lg:hover:not(:disabled) { box-shadow: 0 6px 20px rgba(139,92,246,.35); transform: translateY(-1px) }
.ocr-confirm-hint { font-size: .72rem; color: #94a3b8; margin-top: 6px }

/* ── DOCUMENT WARNINGS ── */
.doc-complete-badge { display: flex; align-items: center; gap: 8px; padding: 10px 14px; border-radius: 8px; background: rgba(34,197,94,.06); border: 1px solid rgba(34,197,94,.2); color: #16a34a; font-weight: 600; font-size: .88rem }
.dc-icon { font-size: 1.1rem }
.doc-incomplete-badge { display: flex; align-items: center; gap: 8px; padding: 10px 14px; border-radius: 8px; background: rgba(234,179,8,.06); border: 1px solid rgba(234,179,8,.2); color: #92400e; font-weight: 600; font-size: .88rem; margin-bottom: 10px }
.di-icon { font-size: 1.1rem }
.warn-list { padding-left: 20px; margin: 0 }
.warn-item { font-size: .84rem; color: #92400e; padding: 3px 0; line-height: 1.5 }
.warn-count { font-size: .75rem; opacity: .7 }

/* ── NEXT STEPS ── */
.rc-h-cyan { color: #0891b2 }
.rc-h-teal { color: #0d9488 }

.ns-item { padding: 12px 0; border-bottom: 1px solid #f1f5f9 }
.ns-item:last-child { border-bottom: none }
.ns-action { font-size: .88rem; font-weight: 600; color: #1e293b; display: flex; align-items: flex-start; gap: 8px }
.ns-num { width: 22px; height: 22px; border-radius: 50%; background: rgba(6,182,212,.1); color: #0891b2; display: flex; align-items: center; justify-content: center; font-size: .72rem; font-weight: 800; flex-shrink: 0 }
.ns-meta { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 6px; padding-left: 30px }
.ns-tag { font-size: .7rem; font-weight: 700; padding: 2px 8px; border-radius: 4px; text-transform: uppercase; background: rgba(234,179,8,.1); color: #a16207 }
.ns-tag.ns-cao, .ns-tag.ns-high { background: rgba(239,68,68,.1); color: #dc2626 }
.ns-tag.ns-thấp, .ns-tag.ns-low { background: rgba(34,197,94,.1); color: #16a34a }
.ns-resp { font-size: .75rem; color: #64748b }
.ns-deadline { font-size: .75rem; color: #c2410c }

.results-scroll { padding: 24px; max-width: 900px; margin: 0 auto }
.result-card { border: 1px solid #e2e8f0; border-radius: 14px; margin-bottom: 16px; overflow: hidden; background: #fff }

.rc-header { padding: 14px 20px; cursor: pointer; display: flex; align-items: center; gap: 10px; font-weight: 600; font-size: .9rem; transition: background .2s; user-select: none; background: #fafbfc; color: #1e293b }
.rc-header:hover { background: #f1f5f9 }
.rc-h-blue { color: #2563eb }
.rc-h-violet { color: #7c3aed }
.rc-h-green { color: #16a34a }
.rc-h-warn { color: #d97706 }
.rc-arrow { font-size: 1.2rem; margin-left: auto; transition: transform .2s; color: #94a3b8 }
.rc-arrow.open { transform: rotate(90deg) }
.rc-body { padding: 0 20px 16px; border-top: 1px solid #f1f5f9; color: #334155 }

/* Chips */
.dx-chip { font-size: .72rem; font-weight: 700; padding: 3px 10px; border-radius: 99px; white-space: nowrap; flex-shrink: 0 }
.chip-pass   { background: rgba(16,185,129,.12); color: #065f46; border: 1px solid rgba(16,185,129,.25) }
.chip-extend { background: rgba(245,158,11,.12); color: #92400e; border: 1px solid rgba(245,158,11,.25) }
.chip-fail   { background: rgba(239,68,68,.10);  color: #991b1b; border: 1px solid rgba(239,68,68,.25) }

/* Employee Info Card */
.emp-info-card { background: #fff; border: 1px solid #e2e8f0; border-radius: 14px; padding: 20px 24px; margin-bottom: 16px }
.emp-info-header { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid #f1f5f9 }
.emp-avatar { width: 42px; height: 42px; border-radius: 50%; background: linear-gradient(135deg,#8b5cf6,#a855f7); display: flex; align-items: center; justify-content: center; font-size: 18px; color: #fff; font-weight: 700 }
.emp-info-title { font-size: 15px; font-weight: 700; color: #1e293b }
.emp-info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px }
.emp-field-label { font-size: .72rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: .03em; margin-bottom: 3px }
.emp-field-value { font-size: .88rem; font-weight: 600; color: #1e293b }
.emp-field-empty { color: #cbd5e1; font-style: italic; font-weight: 400 }

/* Competency Table */
.comp-table { width: 100%; border-collapse: collapse; font-size: .85rem; margin-top: 12px }
.comp-table th { padding: 8px 12px; text-align: left; font-weight: 700; font-size: .75rem; text-transform: uppercase; letter-spacing: .05em; color: #64748b; background: #f8fafc }
.comp-table td { padding: 8px 12px; border-bottom: 1px solid #f1f5f9; color: #334155 }
.td-center { text-align: center }
.td-score { font-weight: 800; font-size: .95rem }
.s-good { color: #16a34a }
.s-mid { color: #d97706 }
.s-low { color: #dc2626 }
.comp-total td { border-top: 2px solid rgba(139,92,246,.15); border-bottom: none; background: #faf5ff }

/* Recommendation */
.rec-body { padding-top: 12px !important; line-height: 1.8; font-size: .9rem; color: #334155 }
.rec-body :deep(.rec-label) { display: inline-block; font-weight: 800; color: #7c3aed; margin-top: 8px }

/* Section labels for recommendation_details */
.rd-section { margin-top: 20px }
.rd-label { font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: .5px; margin-bottom: 8px }
.rd-label-green { color: #16a34a }
.rd-label-yellow { color: #ca8a04 }
.rd-label-blue { color: #2563eb }
.rd-label-red { color: #dc2626 }
.rd-label-purple { color: #7c3aed }
.rd-list { margin-top: 8px; padding-left: 20px; color: #475569; line-height: 1.6 }
.rd-list li { margin-bottom: 4px }
.rd-text { margin-top: 8px; color: #475569; line-height: 1.6 }

/* Evidence */
.ev-item { padding: 10px 0; border-bottom: 1px solid #f1f5f9 }
.ev-item:last-child { border-bottom: none }
.ev-comp { font-size: .78rem; font-weight: 700; color: #6366f1; margin-bottom: 4px }
.ev-text { font-size: .88rem; line-height: 1.6; color: #334155 }
.ev-src { font-size: .75rem; color: #64748b; margin-top: 4px }

/* ══ COMPREHENSIVE DARK THEME ══ */
body.theme-dark .app-layout { background: #0f0f1a; }
body.theme-dark .sidebar { background: #14141f; border-right-color: rgba(255,255,255,.06); }
body.theme-dark .sb-name { color: #f1f5f9; }
body.theme-dark .mode-btn { background: rgba(99,102,241,.06); border-color: rgba(99,102,241,.15); color: #94a3b8; }
body.theme-dark .mode-btn:hover { background: rgba(99,102,241,.12); color: #818cf8; }
body.theme-dark .mode-btn.active { background: linear-gradient(135deg,#6366f1,#8b5cf6); color: #fff; border-color: transparent; }
body.theme-dark .sb-upload-card { background: rgba(99,102,241,.05); border-color: rgba(99,102,241,.18); }
body.theme-dark .sb-upload-card.filled { background: rgba(99,102,241,.08); border-color: rgba(99,102,241,.3); }
body.theme-dark .upc-val { color: #cbd5e1; }
body.theme-dark .upc-hint { color: #64748b; }
body.theme-dark .sb-btn-secondary { background: transparent; color: #a5b4fc; border-color: rgba(99,102,241,.3); }
body.theme-dark .sc { background: rgba(99,102,241,.08); }
body.theme-dark .result-panel { background: #0f0f1a; }
body.theme-dark .welcome h1 { color: #f1f5f9; }
body.theme-dark .wf { background: rgba(99,102,241,.06); border-color: rgba(99,102,241,.15); color: #94a3b8; }
body.theme-dark .result-card { background: #14141f; border-color: rgba(255,255,255,.06); }
body.theme-dark .rc-header:hover { background: rgba(99,102,241,.06); }
body.theme-dark .ocr-review-header { background: #14141f; border-color: rgba(255,255,255,.06); }
body.theme-dark .ocr-review-header h2 { color: #f1f5f9; }
body.theme-dark .ocr-doc-tab { background: rgba(99,102,241,.04); border-color: rgba(255,255,255,.06); color: #94a3b8; }
body.theme-dark .ocr-doc-tab:hover { background: rgba(99,102,241,.08); color: #a5b4fc; }
body.theme-dark .ocr-doc-tab.active { background: #14141f; color: #a78bfa; border-color: rgba(255,255,255,.08); border-bottom-color: #14141f; }
body.theme-dark .ocr-content-card { background: #14141f; border-color: rgba(255,255,255,.06); }
body.theme-dark .ocr-info-section { border-bottom-color: rgba(255,255,255,.06); }
body.theme-dark .ocr-info-input { background: rgba(99,102,241,.06); border-color: rgba(99,102,241,.2); color: #f1f5f9; }
body.theme-dark .ocr-info-input:focus { background: rgba(99,102,241,.1); border-color: #8b5cf6; }
body.theme-dark .ocr-edit-header { background: rgba(99,102,241,.04); border-bottom-color: rgba(255,255,255,.06); color: #94a3b8; }
body.theme-dark .ocr-toggle-edit { background: transparent; border-color: rgba(255,255,255,.1); color: #94a3b8; }
body.theme-dark .ocr-edit-area { background: #0f0f1a; color: #cbd5e1; }
body.theme-dark .ocr-rendered-view :deep(.ocr-md-h1) { color: #f1f5f9; border-bottom-color: rgba(139,92,246,.2); }
body.theme-dark .ocr-rendered-view :deep(.ocr-md-table th) { background: rgba(139,92,246,.12); color: #a78bfa; border-bottom-color: rgba(139,92,246,.2); }
body.theme-dark .ocr-rendered-view :deep(.ocr-md-table td) { border-bottom-color: rgba(255,255,255,.06); color: #cbd5e1; }
body.theme-dark .ocr-rendered-view :deep(strong) { color: #f1f5f9; }
body.theme-dark .ocr-status-text strong { color: #f1f5f9; }

/* ── Dark mode: Word template (eval scan tab) ── */
body.theme-dark .word-template-view { background: #14141f; color: #e2e8f0; }
body.theme-dark .word-h3 { color: #a78bfa; }
body.theme-dark .word-th { background: rgba(99,102,241,.08); color: #a78bfa; border-color: rgba(255,255,255,.08) }
body.theme-dark .word-table td, body.theme-dark .word-table th { border-color: rgba(255,255,255,.08); }
body.theme-dark .word-label { background: rgba(99,102,241,.05); color: #94a3b8; border-color: rgba(255,255,255,.08) }
body.theme-dark .word-input { color: #e2e8f0; background: transparent; }
body.theme-dark .word-textarea { color: #e2e8f0; background: transparent; }
body.theme-dark .word-input:focus, body.theme-dark .word-textarea:focus { background: rgba(139,92,246,.07); }
body.theme-dark .word-header h2 { color: #a78bfa; }

/* ── Dark mode: OCR info section header ── */
body.theme-dark .ocr-info-header { color: #a78bfa; }
body.theme-dark .ocr-info-label { color: #64748b; }
body.theme-dark .ocr-info-row { background: transparent; }

/* ── Dark mode: Report doc (report scan tab) ── */
body.theme-dark .rpt-doc { background: #14141f; border-color: rgba(255,255,255,.06); box-shadow: none; }
body.theme-dark .rpt-title { color: #f1f5f9; }
body.theme-dark .rpt-field-label { color: #94a3b8; }
body.theme-dark .rpt-inline-input { color: #e2e8f0; border-bottom-color: rgba(99,102,241,.3); }
body.theme-dark .rpt-inline-input:focus { border-bottom-color: #8b5cf6; }
body.theme-dark .rpt-section-label { color: #818cf8; }
body.theme-dark .rpt-nq-label { color: #fbbf24; }
body.theme-dark .rpt-nq-note { color: #64748b; }
body.theme-dark .rpt-input { color: #cbd5e1; }
body.theme-dark .rpt-ta { color: #cbd5e1; }
body.theme-dark .rpt-input:focus, body.theme-dark .rpt-ta:focus { background: rgba(99,102,241,.06); }
body.theme-dark .rpt-td-stt { color: #818cf8; }
body.theme-dark .rpt-kqb { color: #34d399 !important; }
body.theme-dark .rpt-link-ta { color: #818cf8; }
body.theme-dark .rpt-kqc { background: rgba(16,185,129,.04) !important; }
body.theme-dark .rpt-xd-label { color: #e2e8f0; }
body.theme-dark .rpt-ranking-input { color: #a78bfa !important; }

body.theme-dark .ns-item { border-bottom-color: rgba(255,255,255,.06); }

body.theme-dark .ns-action { color: #f1f5f9; }
body.theme-dark .rec-body { color: #cbd5e1; }
body.theme-dark .rd-list { color: #94a3b8; }
body.theme-dark .rd-text { color: #94a3b8; }
body.theme-dark .ev-text { color: #cbd5e1; }
body.theme-dark .ev-item { border-bottom-color: rgba(255,255,255,.06); }

/* ── Dark mode: result card internals ── */
body.theme-dark .rc-header { background: #1a1a2e; color: #e2e8f0 }
body.theme-dark .rc-header:hover { background: rgba(99,102,241,.08) }
body.theme-dark .rc-body { border-top-color: rgba(255,255,255,.06); color: #cbd5e1 }
body.theme-dark .emp-field-label { color: #64748b }
body.theme-dark .emp-field-value { color: #e2e8f0 }
body.theme-dark .emp-info-title { color: #f1f5f9 }
body.theme-dark .emp-info-card { background: #14141f; border-color: rgba(255,255,255,.06) }
body.theme-dark .comp-table { background: transparent }
body.theme-dark .comp-table th { background: #1e2030; color: #94a3b8 }
body.theme-dark .comp-table td { color: #cbd5e1; border-bottom-color: rgba(255,255,255,.06) }
body.theme-dark .comp-total td { background: rgba(139,92,246,.06); border-top-color: rgba(139,92,246,.15) }
body.theme-dark .doc-complete-badge { background: rgba(16,185,129,.08); border-color: rgba(16,185,129,.2); color: #6ee7b7 }
body.theme-dark .doc-incomplete-badge { background: rgba(245,158,11,.08); border-color: rgba(245,158,11,.2); color: #fcd34d }
body.theme-dark .warn-item { color: #fcd34d }
body.theme-dark .chip-pass   { background: rgba(16,185,129,.15); color: #6ee7b7; border-color: rgba(16,185,129,.3) }
body.theme-dark .chip-extend { background: rgba(245,158,11,.15); color: #fcd34d; border-color: rgba(245,158,11,.3) }
body.theme-dark .chip-fail   { background: rgba(239,68,68,.15);  color: #fca5a5; border-color: rgba(239,68,68,.3) }
body.theme-dark .sc { background: rgba(99,102,241,.1) }
body.theme-dark .sc-lbl { color: #94a3b8 }

/* ── Scan result banner ── */
.from-scan-banner { display: flex; align-items: center; gap: 12px; padding: 12px 16px; border-radius: 10px; background: rgba(99,102,241,.06); border: 1px solid rgba(99,102,241,.15); margin-bottom: 16px; }
.from-scan-banner .fs-icon { font-size: 24px; flex-shrink: 0; }
.from-scan-banner .fs-title { font-weight: 700; font-size: .88rem; color: #6366f1; }
.from-scan-banner .fs-sub { font-size: .78rem; color: #64748b; margin-top: 2px; }
.results-with-ocr { border-top: 2px solid rgba(99,102,241,.15); padding-top: 16px; }

/* ── Báo cáo ngày stats ── */
.daily-stats { display: flex; flex-direction: column; gap: 6px; }
.ds-item { font-size: .83rem; padding: 6px 10px; border-radius: 6px; }
.ds-ok  { background: rgba(16,185,129,.06); color: #065f46; }
.ds-warn{ background: rgba(245,158,11,.06); color: #92400e; }
.ds-bad { background: rgba(239,68,68,.06);  color: #991b1b; }
.ds-dates { font-size: .75rem; opacity: .8; margin-left: 4px; }
body.theme-dark .ds-ok  { background: rgba(16,185,129,.08); color: #6ee7b7; }
body.theme-dark .ds-warn { background: rgba(245,158,11,.08); color: #fcd34d; }
body.theme-dark .ds-bad  { background: rgba(239,68,68,.08);  color: #fca5a5; }

/* ── Dark mode: inline sub-containers ── */
body.theme-dark .rc-body [style*="background: #fafbfc"],
body.theme-dark .rc-body [style*="background:#fafbfc"],
body.theme-dark .rc-body [style*="background: #f8fafc"],
body.theme-dark .rc-body [style*="background:#f8fafc"] { background: rgba(99,102,241,.05) !important; border-color: rgba(255,255,255,.06) !important; }
body.theme-dark .rc-body [style*="background: #f0fdf4"],
body.theme-dark .rc-body [style*="background:#f0fdf4"] { background: rgba(16,185,129,.07) !important; border-color: rgba(16,185,129,.25) !important; }
body.theme-dark .rc-body [style*="background: #fef2f2"],
body.theme-dark .rc-body [style*="background:#fef2f2"] { background: rgba(239,68,68,.07) !important; border-color: rgba(239,68,68,.2) !important; }
body.theme-dark .rc-body [style*="background: #fff7ed"],
body.theme-dark .rc-body [style*="background:#fff7ed"] { background: rgba(245,158,11,.07) !important; border-color: rgba(245,158,11,.25) !important; }
body.theme-dark .rc-body [style*="background: #f0f9ff"],
body.theme-dark .rc-body [style*="background:#f0f9ff"] { background: rgba(14,165,233,.07) !important; border-color: rgba(14,165,233,.25) !important; }
body.theme-dark .rc-body [style*="background: #fefce8"],
body.theme-dark .rc-body [style*="background:#fefce8"] { background: rgba(234,179,8,.07) !important; border-color: rgba(234,179,8,.25) !important; }
body.theme-dark .rc-body [style*="background: #f1f5f9"],
body.theme-dark .rc-body [style*="background:#f1f5f9"] { background: #1e2030 !important; }

/* ── Dark mode: hardcoded dark text inside rc-body ── */
body.theme-dark .rc-body [style*="color: #1e293b"],
body.theme-dark .rc-body [style*="color:#1e293b"] { color: #e2e8f0 !important; }
body.theme-dark .rc-body [style*="color: #334155"],
body.theme-dark .rc-body [style*="color:#334155"] { color: #cbd5e1 !important; }
body.theme-dark .rc-body [style*="color: #374151"],
body.theme-dark .rc-body [style*="color:#374151"] { color: #cbd5e1 !important; }
body.theme-dark .rc-body [style*="color: #475569"],
body.theme-dark .rc-body [style*="color:#475569"] { color: #94a3b8 !important; }
body.theme-dark .rc-body [style*="color: #0c4a6e"],
body.theme-dark .rc-body [style*="color:#0c4a6e"] { color: #7dd3fc !important; }
body.theme-dark .rc-body [style*="color: #78350f"],
body.theme-dark .rc-body [style*="color:#78350f"] { color: #fcd34d !important; }
body.theme-dark .rc-body [style*="background: rgba(255,255,255"],
body.theme-dark .rc-body [style*="background:rgba(255,255,255"] { background: rgba(255,255,255,.04) !important; }
</style>

