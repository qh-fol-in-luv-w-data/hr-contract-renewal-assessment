<template>
  <div class="app-layout">
    <!-- ══ SIDEBAR ══════════════════════════════════════════════════ -->
    <aside class="sidebar">
      <div class="sb-top">
        <router-link to="/" class="sb-back" title="Về Portal">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M19 12H5m7-7-7 7 7 7"/></svg>
        </router-link>
        <div class="sb-logo">
          <div class="sb-logo-mark sb-logo-teal">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
          </div>
          <div>
            <div class="sb-name">Đánh giá Đề xuất</div>
            <div class="sb-org">Quản lý / HOD</div>
          </div>
        </div>
        <button class="sb-reload" title="Hồ sơ mới" @click="startNew">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        </button>
      </div>

      <div class="sb-body">

        <!-- ─ NEW: upload form ─ -->
        <template v-if="view === 'new'">
          <div class="sb-section">
            <div class="sb-section-title">Upload tờ trình</div>
            <div class="sb-upload-card" :class="{ filled: uploadFile, err: uploadError }"
                 @dragover.prevent @drop.prevent="handleDrop" @click="$refs.fileInput.click()">
              <input ref="fileInput" type="file" accept=".pdf,.png,.jpg,.jpeg,.docx,.doc" @change="handleFileSelect" hidden/>
              <div class="upc-icon">{{ uploadFile ? '✅' : '📄' }}</div>
              <div class="upc-info">
                <div class="upc-label">Tờ trình đề xuất</div>
                <div class="upc-val" :class="uploadFile ? 'ok' : 'empty'">{{ uploadFile ? uploadFile.name : 'Click hoặc kéo file vào đây' }}</div>
                <div class="upc-hint">{{ uploadFile ? fmtSize(uploadFile.size) : 'PDF · PNG · JPG · DOCX · ≤30MB' }}</div>
              </div>
              <button v-if="uploadFile" class="upc-rm" @click.stop="uploadFile = null">✕</button>
            </div>
            <p v-if="uploadError" class="sb-err">{{ uploadError }}</p>
            <button class="sb-btn-primary" :disabled="!uploadFile || uploading" @click="doUpload">
              <span v-if="uploading" class="spinner"></span>
              <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.39 18.39A5 5 0 0018 9h-1.26A8 8 0 103 16.3"/></svg>
              {{ uploading ? 'Đang upload...' : 'Upload & Bắt đầu' }}
            </button>
            <button class="sb-btn-secondary" @click="backToList">← Hủy</button>
          </div>
        </template>

        <!-- ─ DETAIL: step navigator + actions ─ -->
        <template v-else-if="view === 'detail' && evalDoc.name">
          <div class="sb-section">
            <!-- Record chip -->
            <div class="dx-record-chip">
              <span class="mono small">{{ evalDoc.name }}</span>
              <span class="dx-status-dot" :class="statusDotClass(evalDoc.status)"></span>
            </div>
            <div class="dx-emp-name">{{ evalDoc.employee_name || '(Chưa trích xuất)' }}</div>
            <div v-if="evalDoc.department" class="dx-emp-dept">{{ evalDoc.department }}</div>
          </div>

          <!-- Vertical stepper -->
          <div class="sb-section">
            <div class="vs-stepper">
              <div v-for="(s, i) in STEPS" :key="s.n" class="vs-item">
                <div class="vs-left">
                  <div class="vs-dot" :class="dotClass(s.n)">
                    <svg v-if="stepState(s.n)==='done'" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
                    <span v-else-if="stepState(s.n)==='active' && processing && currentStep===s.n" class="vs-spin"></span>
                    <span v-else>{{ s.n }}</span>
                  </div>
                  <div v-if="i < STEPS.length-1" class="vs-line" :class="stepState(s.n)==='done'?'vs-line-done':''"></div>
                </div>
                <div class="vs-text" :class="'vs-text-'+stepState(s.n)">{{ s.label }}</div>
              </div>
            </div>
          </div>

          <!-- Progress bar -->
          <div v-if="processing" class="sb-section">
            <div class="sb-progress-text">{{ progressMsg }}</div>
            <div class="sb-progress-bar"><div class="sb-progress-fill" :style="{ width: progressPct + '%' }"></div></div>
          </div>

          <!-- Error -->
          <p v-if="detailError" class="sb-err" style="margin: 0 0 8px">{{ detailError }}</p>

          <!-- Action buttons -->
          <div class="sb-section">
            <button v-if="currentStep === 2 && !processing" class="sb-btn-primary" @click="doExtract">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
              Trích xuất dữ liệu
            </button>

            <template v-if="currentStep === 3">
              <button class="sb-btn-secondary" :disabled="saving" @click="saveCorrections">
                <span v-if="saving" class="spinner spinner-dark"></span>
                <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/></svg>
                {{ saving ? 'Đang lưu...' : 'Lưu chỉnh sửa' }}
              </button>
              <button class="sb-btn-primary" :disabled="processing || saving" @click="doConfirm">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                Xác nhận dữ liệu
              </button>
            </template>

            <button v-if="currentStep === 4 && !processing" class="sb-btn-primary" @click="doEvaluate">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
              {{ evalDoc.status === 'Evaluated' ? 'Đánh giá lại' : 'Đánh giá đề xuất' }}
            </button>

            <button v-if="currentStep === 5" class="sb-btn-primary" :disabled="processing" @click="doGenerateReport">
              <span v-if="processing" class="spinner"></span>
              <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              {{ processing ? 'Đang tạo...' : (evalDoc.status==='Report Generated' ? 'Tải lại PDF' : 'Tải báo cáo PDF') }}
            </button>
          </div>

          <!-- Score summary (when evaluated) -->
          <div v-if="evalDoc.overall_score" class="sb-section">
            <div class="sb-score-box">
              <div class="sb-score-num" :class="scoreClass(evalDoc.overall_score)">{{ evalDoc.overall_score }}</div>
              <div class="sb-score-lbl">điểm / 100</div>
              <div class="dx-rec-badge" :class="recClass(evalDoc.recommendation)" style="margin-top:6px">{{ recLabel(evalDoc.recommendation) }}</div>
            </div>
          </div>

          <div class="sb-section">
            <button class="sb-btn-secondary" @click="backToList">← Danh sách</button>
          </div>
        </template>

        <!-- ─ LIST: record list ─ -->
        <template v-else>
          <div class="sb-section">
            <div class="sb-section-title">Hồ sơ gần đây ({{ totalCount }})</div>
            <div v-if="listLoading" class="sb-list-loading">
              <div class="spinner" style="border-color:rgba(13,148,136,.2);border-top-color:#0d9488"></div>
            </div>
            <div v-else-if="listItems.length" class="dx-list">
              <div v-for="item in listItems" :key="item.name"
                   class="dx-list-item" :class="{ active: evalDoc.name === item.name }"
                   @click="openEval(item.name)">
                <div class="dx-li-top">
                  <span class="dx-li-name">{{ item.employee_name || '—' }}</span>
                  <span class="dx-status-dot" :class="statusDotClass(item.status)"></span>
                </div>
                <div class="dx-li-meta">
                  <span class="mono small">{{ item.name }}</span>
                  <span v-if="item.overall_score" class="dx-li-score" :class="scoreClass(item.overall_score)">{{ item.overall_score }}đ</span>
                </div>
                <div class="dx-li-status">{{ item.status }}</div>
              </div>
            </div>
            <div v-else class="dx-list-empty">Chưa có hồ sơ nào</div>
            <button class="sb-btn-primary" @click="startNew" style="margin-top:12px">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
              Tạo hồ sơ mới
            </button>
          </div>
        </template>

      </div>
    </aside>

    <!-- ══ MAIN PANEL ════════════════════════════════════════════════ -->
    <main class="result-panel">

      <!-- Welcome list -->
      <div v-if="view === 'list'" class="welcome">
        <div class="welcome-icon">
          <svg width="56" height="56" viewBox="0 0 56 56" fill="none">
            <rect width="56" height="56" rx="18" fill="url(#dxg)"/>
            <text x="28" y="38" text-anchor="middle" font-size="26">📋</text>
            <defs><linearGradient id="dxg" x1="0" y1="0" x2="56" y2="56"><stop stop-color="#0d9488"/><stop offset="1" stop-color="#6366f1"/></linearGradient></defs>
          </svg>
        </div>
        <h1>Đánh giá Đề xuất Quản lý / HOD</h1>
        <p>Upload tờ trình đề xuất nhân sự. AI đọc, trích xuất cấu trúc, đánh giá độc lập từng đề xuất theo 7 tiêu chí 100 điểm.</p>
        <div class="welcome-features">
          <div class="wf"><div class="wf-icon">📤</div><div>Upload PDF / ảnh / DOCX</div></div>
          <div class="wf"><div class="wf-icon">🔍</div><div>OCR & trích xuất tự động</div></div>
          <div class="wf"><div class="wf-icon">⚖️</div><div>Đánh giá độc lập 7 tiêu chí</div></div>
          <div class="wf"><div class="wf-icon">📄</div><div>Báo cáo PDF A4</div></div>
        </div>
      </div>

      <!-- Welcome new -->
      <div v-if="view === 'new'" class="welcome">
        <div class="welcome-icon">
          <svg width="56" height="56" viewBox="0 0 56 56" fill="none">
            <rect width="56" height="56" rx="18" fill="url(#dxg3)"/>
            <text x="28" y="38" text-anchor="middle" font-size="26">📤</text>
            <defs><linearGradient id="dxg3" x1="0" y1="0" x2="56" y2="56"><stop stop-color="#0d9488"/><stop offset="1" stop-color="#0891b2"/></linearGradient></defs>
          </svg>
        </div>
        <h1>Chọn file tờ trình</h1>
        <p>Chọn file ở thanh bên trái rồi nhấn <b>Upload &amp; Bắt đầu</b>.<br/>Hỗ trợ PDF scan nhiều trang, PNG, JPG, DOCX. Tối đa 30MB.</p>
      </div>

      <!-- Wizard steps -->
      <div v-if="view === 'detail' && evalDoc.name" class="wizard-scroll">

        <!-- ── Step 1: File info ── -->
        <div class="wz-step wz-done">
          <div class="wz-head">
            <div class="wz-num wz-num-done">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
            </div>
            <div class="wz-title">Upload file tờ trình</div>
            <a v-if="evalDoc.source_file" :href="evalDoc.source_file" target="_blank" class="wz-link">Xem file ↗</a>
          </div>
          <div class="wz-body">
            <div class="wz-info-row"><span class="wz-lbl">File</span><span>{{ evalDoc.source_file_name || '—' }}</span></div>
            <div class="wz-info-row"><span class="wz-lbl">Loại</span><span>{{ evalDoc.source_file_type || '—' }}</span></div>
            <div class="wz-info-row"><span class="wz-lbl">Số trang</span><span>{{ evalDoc.page_count || '—' }}</span></div>
            <div class="wz-info-row"><span class="wz-lbl">Upload bởi</span><span>{{ evalDoc.uploaded_by || '—' }}</span></div>
          </div>
        </div>

        <!-- ── Step 2: Extract ── -->
        <div class="wz-step" :class="'wz-' + stepState(2)">
          <div class="wz-head">
            <div class="wz-num" :class="stepState(2)==='done'?'wz-num-done':stepState(2)==='active'?'wz-num-active':'wz-num-pending'">
              <svg v-if="stepState(2)==='done'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
              <span v-else-if="stepState(2)==='active' && processing"><span class="wz-spin"></span></span>
              <span v-else>2</span>
            </div>
            <div class="wz-title">Trích xuất dữ liệu</div>
            <div v-if="stepState(2)==='active' && !processing" class="wz-hint">← Nhấn nút bên trái</div>
          </div>
          <div v-if="stepState(2) !== 'pending'" class="wz-body">
            <div v-if="stepState(2)==='active' && processing" class="wz-loading">
              <div class="loading-spinner" style="width:28px;height:28px"></div>
              <span>{{ progressMsg }}</span>
            </div>
            <div v-else-if="stepState(2)==='active'" class="wz-prompt">
              Nhấn <b>Trích xuất dữ liệu</b> ở thanh bên để AI đọc và trích xuất nội dung tờ trình.
            </div>
            <template v-else-if="editData">
              <div class="wz-info-row"><span class="wz-lbl">Nhân sự</span><span>{{ editData.employee?.fullName || '—' }}</span></div>
              <div class="wz-info-row"><span class="wz-lbl">Phòng ban</span><span>{{ editData.employee?.department || '—' }}</span></div>
              <div class="wz-info-row"><span class="wz-lbl">Đề xuất</span><span>{{ editData.proposalItems?.length || 0 }} nội dung</span></div>
              <div v-if="warningList.length" class="wz-warn-row">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                {{ warningList.length }} cảnh báo OCR
              </div>
            </template>
          </div>
        </div>

        <!-- ── Step 3: Review & Edit ── -->
        <div class="wz-step" :class="'wz-' + stepState(3)">
          <div class="wz-head">
            <div class="wz-num" :class="stepState(3)==='done'?'wz-num-done':stepState(3)==='active'?'wz-num-active':'wz-num-pending'">
              <svg v-if="stepState(3)==='done'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
              <span v-else>3</span>
            </div>
            <div class="wz-title">Xem xét &amp; Chỉnh sửa dữ liệu</div>
            <div v-if="stepState(3)==='done'" class="wz-badge-done">Đã xác nhận</div>
          </div>
          <div v-if="stepState(3) !== 'pending' && editData" class="wz-body">

            <!-- Thông tin văn bản -->
            <div class="wz-sub-section">
              <div class="wz-sub-title" @click="toggleSection('doc')">
                📄 Thông tin văn bản
                <span class="wz-toggle">{{ openSections.doc ? '▲' : '▼' }}</span>
              </div>
              <div v-if="openSections.doc" class="dx-edit-grid">
                <div class="dx-ef"><label>Đơn vị</label><input v-model="editData.documentMetadata.unit" :disabled="stepState(3)==='done'"/></div>
                <div class="dx-ef"><label>Ngày lập</label><input v-model="editData.documentMetadata.documentDate" :disabled="stepState(3)==='done'"/></div>
                <div class="dx-ef dx-ef-full"><label>Về việc</label><input v-model="editData.documentMetadata.subject" :disabled="stepState(3)==='done'"/></div>
                <div class="dx-ef dx-ef-full"><label>Kính gửi</label><input v-model="editData.documentMetadata.recipient" :disabled="stepState(3)==='done'"/></div>
              </div>
            </div>

            <!-- Thông tin nhân sự -->
            <div class="wz-sub-section">
              <div class="wz-sub-title" @click="toggleSection('emp')">
                👤 Thông tin nhân sự
                <span class="wz-toggle">{{ openSections.emp ? '▲' : '▼' }}</span>
              </div>
              <div v-if="openSections.emp" class="dx-edit-grid">
                <div class="dx-ef"><label>Họ và tên <span class="req">*</span></label><input v-model="editData.employee.fullName" :disabled="stepState(3)==='done'"/></div>
                <div class="dx-ef"><label>Mã nhân viên</label><input v-model="editData.employee.employeeCode" :disabled="stepState(3)==='done'"/></div>
                <div class="dx-ef"><label>Phòng ban</label><input v-model="editData.employee.department" :disabled="stepState(3)==='done'"/></div>
                <div class="dx-ef"><label>Chức danh hiện tại</label><input v-model="editData.employee.currentTitle" :disabled="stepState(3)==='done'"/></div>
                <div class="dx-ef"><label>Cấp bậc</label><input v-model="editData.employee.currentGrade" :disabled="stepState(3)==='done'"/></div>
                <div class="dx-ef"><label>Lương hiện tại</label><input v-model="editData.employee.currentSalary" :disabled="stepState(3)==='done'" placeholder="VD: 18000000"/></div>
                <div class="dx-ef"><label>Thời gian làm việc</label><input v-model="editData.employee.workDuration" :disabled="stepState(3)==='done'"/></div>
                <div class="dx-ef"><label>Quản lý trực tiếp</label><input v-model="editData.employee.directManager" :disabled="stepState(3)==='done'"/></div>
              </div>
            </div>

            <!-- Nội dung đề xuất -->
            <div class="wz-sub-section">
              <div class="wz-sub-title" @click="toggleSection('proposals')">
                📝 Nội dung đề xuất ({{ editData.proposalItems?.length || 0 }})
                <span class="wz-toggle">{{ openSections.proposals ? '▲' : '▼' }}</span>
              </div>
              <div v-if="openSections.proposals">
                <div v-for="(item, idx) in editData.proposalItems" :key="idx" class="dx-pi-card">
                  <div class="dx-pi-head">
                    <select v-model="item.proposalType" :disabled="stepState(3)==='done'" class="dx-select">
                      <option value="SALARY_INCREASE">Tăng lương</option>
                      <option value="TITLE_APPOINTMENT">Bổ nhiệm chức danh</option>
                      <option value="TITLE_ADJUSTMENT">Điều chỉnh chức danh</option>
                      <option value="GRADE_CHANGE">Thay đổi cấp bậc</option>
                      <option value="BENEFIT_ADJUSTMENT">Điều chỉnh đãi ngộ</option>
                      <option value="ROLE_CHANGE">Điều chuyển vai trò</option>
                      <option value="OTHER">Khác</option>
                    </select>
                    <button v-if="stepState(3)==='active' && editData.proposalItems.length > 1" class="dx-rm-btn" @click="editData.proposalItems.splice(idx,1)">✕</button>
                  </div>
                  <div class="dx-edit-grid">
                    <div class="dx-ef"><label>Hiện tại</label><input v-model="item.currentValue" :disabled="stepState(3)==='done'"/></div>
                    <div class="dx-ef"><label>Đề xuất <span class="req">*</span></label><input v-model="item.proposedValue" :disabled="stepState(3)==='done'"/></div>
                    <div class="dx-ef"><label>Ngày áp dụng</label><input v-model="item.effectiveDate" :disabled="stepState(3)==='done'"/></div>
                    <div class="dx-ef dx-ef-full"><label>Lý do</label><textarea v-model="item.reason" rows="2" :disabled="stepState(3)==='done'"></textarea></div>
                  </div>
                  <div v-if="item.proposalType==='SALARY_INCREASE' && item.currentValue && item.proposedValue" class="dx-delta-row">
                    {{ computeDelta(item) }}
                  </div>
                </div>
                <button v-if="stepState(3)==='active'" class="wz-add-btn" @click="editData.proposalItems.push({ proposalType:'SALARY_INCREASE', currentValue:null, proposedValue:null })">+ Thêm đề xuất</button>
              </div>
            </div>

            <!-- KPI -->
            <div class="wz-sub-section">
              <div class="wz-sub-title" @click="toggleSection('kpi')">
                📊 KPI / Kết quả đánh giá
                <span class="wz-toggle">{{ openSections.kpi ? '▲' : '▼' }}</span>
              </div>
              <div v-if="openSections.kpi" class="dx-edit-grid">
                <div class="dx-ef"><label>Điểm KPI</label><input v-model="editData.evaluationContext.kpiScore" :disabled="stepState(3)==='done'"/></div>
                <div class="dx-ef"><label>Tỷ lệ KPI (%)</label><input v-model="editData.evaluationContext.kpiPercent" :disabled="stepState(3)==='done'" placeholder="VD: 87.5"/></div>
                <div class="dx-ef"><label>Tình trạng kỷ luật</label><input v-model="editData.evaluationContext.disciplineStatus" :disabled="stepState(3)==='done'"/></div>
                <div class="dx-ef"><label>Đào tạo</label><input v-model="editData.evaluationContext.trainingParticipation" :disabled="stepState(3)==='done'"/></div>
              </div>
            </div>

            <!-- Cảnh báo -->
            <div v-if="warningList.length" class="wz-sub-section">
              <div class="wz-sub-title warn">⚠ Cảnh báo OCR ({{ warningList.length }})</div>
              <ul class="dx-warn-list"><li v-for="(w,i) in warningList" :key="i">{{ w }}</li></ul>
            </div>

            <!-- Xác nhận đã done -->
            <div v-if="stepState(3)==='done'" class="wz-confirmed-row">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
              Xác nhận bởi {{ evalDoc.confirmed_by || '—' }}
            </div>
          </div>
        </div>

        <!-- ── Step 4: AI Evaluation ── -->
        <div class="wz-step" :class="'wz-' + stepState(4)">
          <div class="wz-head">
            <div class="wz-num" :class="stepState(4)==='done'?'wz-num-done':stepState(4)==='active'?'wz-num-active':'wz-num-pending'">
              <svg v-if="stepState(4)==='done'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
              <span v-else-if="stepState(4)==='active' && processing"><span class="wz-spin"></span></span>
              <span v-else>4</span>
            </div>
            <div class="wz-title">Đánh giá AI (7 tiêu chí / 100 điểm)</div>
            <div v-if="stepState(4)==='active' && !processing" class="wz-hint">← Nhấn nút bên trái</div>
          </div>
          <div v-if="stepState(4) !== 'pending'" class="wz-body">
            <div v-if="stepState(4)==='active' && processing" class="wz-loading">
              <div class="loading-spinner" style="width:28px;height:28px"></div>
              <span>{{ progressMsg }}</span>
            </div>
            <div v-else-if="stepState(4)==='active' && !evalResult" class="wz-prompt">
              Nhấn <b>Đánh giá đề xuất</b> ở thanh bên. AI sẽ đánh giá độc lập từng đề xuất theo 7 tiêu chí 100 điểm.
            </div>
            <template v-else-if="evalResult">
              <!-- Overall -->
              <div class="wz-overall">
                <div class="dx-score-circle" :class="scoreClass(evalDoc.overall_score)">{{ evalDoc.overall_score }}</div>
                <div>
                  <div class="wz-overall-lbl">Điểm tổng hợp / 100</div>
                  <div class="dx-rec-badge" :class="recClass(evalDoc.recommendation)">{{ recLabel(evalDoc.recommendation) }}</div>
                  <p v-if="evalResult.overallSummary" class="wz-summary">{{ evalResult.overallSummary }}</p>
                </div>
              </div>

              <!-- Independence note -->
              <div class="wz-note">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                {{ evalResult.independenceStatement || 'Kết quả đánh giá độc lập với kết quả tái ký hợp đồng.' }}
              </div>

              <!-- Per-proposal results -->
              <div v-for="(pe, idx) in evalResult.proposalEvaluations" :key="idx" class="wz-pe-card">
                <div class="wz-pe-head">
                  <span class="wz-pe-title">{{ idx+1 }}. {{ pe.proposalLabel || proposalLabel(pe.proposalType) }}</span>
                  <span class="dx-rec-badge" :class="recClass(pe.recommendation)" style="font-size:.72rem">{{ recLabel(pe.recommendation) }}</span>
                  <span class="wz-pe-score" :class="scoreClass(pe.score)">{{ pe.score }}/100</span>
                </div>
                <table class="comp-table">
                  <thead><tr><th>Tiêu chí</th><th style="text-align:center">Tối đa</th><th style="text-align:center">Điểm</th><th>Nhận xét</th></tr></thead>
                  <tbody>
                    <tr v-for="cs in pe.criteriaScores" :key="cs.criterionCode">
                      <td>{{ cs.criterionCode }}. {{ cs.criterionName }}</td>
                      <td style="text-align:center">{{ cs.maxScore }}</td>
                      <td style="text-align:center" :class="ctClass(cs)"><b>{{ cs.score }}</b></td>
                      <td style="font-size:.78rem">{{ cs.comment }}</td>
                    </tr>
                    <tr class="dx-total-row">
                      <td><b>Tổng</b></td><td style="text-align:center"><b>100</b></td>
                      <td style="text-align:center"><b>{{ pe.score }}</b></td><td></td>
                    </tr>
                  </tbody>
                </table>
                <div class="wz-reasons">
                  <div v-if="pe.reasonsForApproval?.length" class="wr-group">
                    <span class="wr-lbl pass">✓ Ủng hộ</span>
                    <ul><li v-for="r in pe.reasonsForApproval" :key="r">{{ r }}</li></ul>
                  </div>
                  <div v-if="pe.reasonsAgainstApproval?.length" class="wr-group">
                    <span class="wr-lbl fail">✗ Chưa đồng ý</span>
                    <ul><li v-for="r in pe.reasonsAgainstApproval" :key="r">{{ r }}</li></ul>
                  </div>
                  <div v-if="pe.risks?.length" class="wr-group">
                    <span class="wr-lbl warn">⚠ Rủi ro</span>
                    <ul><li v-for="r in pe.risks" :key="r">{{ r }}</li></ul>
                  </div>
                  <div v-if="pe.missingData?.length" class="wr-group">
                    <span class="wr-lbl info">○ Cần bổ sung</span>
                    <ul><li v-for="m in pe.missingData" :key="m">{{ m }}</li></ul>
                  </div>
                </div>
              </div>

              <!-- Final recommendation -->
              <div v-if="evalResult.finalRecommendation" class="wz-final-rec">
                <div class="wz-fr-title">Kiến nghị xử lý tổng thể</div>
                <div class="dx-rec-badge dx-rec-lg" :class="recClass(evalResult.finalRecommendation.decision)">{{ recLabel(evalResult.finalRecommendation.decision) }}</div>
                <p v-if="evalResult.finalRecommendation.summary" class="wz-summary">{{ evalResult.finalRecommendation.summary }}</p>
              </div>
            </template>
          </div>
        </div>

        <!-- ── Step 5: Report PDF ── -->
        <div class="wz-step" :class="'wz-' + stepState(5)">
          <div class="wz-head">
            <div class="wz-num" :class="stepState(5)==='done'?'wz-num-done':stepState(5)==='active'?'wz-num-active':'wz-num-pending'">
              <svg v-if="stepState(5)==='done'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
              <span v-else>5</span>
            </div>
            <div class="wz-title">Báo cáo PDF</div>
            <div v-if="stepState(5)==='done'" class="wz-badge-done">Đã xuất</div>
          </div>
          <div v-if="stepState(5) !== 'pending'" class="wz-body">
            <div v-if="stepState(5)==='active'" class="wz-prompt">
              Nhấn <b>Tải báo cáo PDF</b> ở thanh bên để sinh báo cáo A4 "Đánh giá tính hợp lý của đề xuất" bao gồm bảng so sánh, điểm từng tiêu chí và kiến nghị xử lý.
            </div>
            <div v-else class="wz-done-row">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
              Báo cáo đã được tải về
              <span v-if="evalDoc.report_generated_at" style="color:#94a3b8;font-size:.75rem;margin-left:8px">{{ evalDoc.report_generated_at }}</span>
            </div>
            <button class="wz-dl-btn" :disabled="processing" @click="doGenerateReport" style="margin-top:12px">
              <span v-if="processing" class="spinner spinner-dark"></span>
              <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              {{ processing ? 'Đang tạo PDF...' : (evalDoc.status==='Report Generated' ? 'Tải lại PDF' : 'Tải báo cáo PDF') }}
            </button>
          </div>
        </div>

      </div><!-- end wizard-scroll -->
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

// ── Constants ──────────────────────────────────────────────────────────────────
const STEPS = [
  { n: 1, label: 'Upload file' },
  { n: 2, label: 'Trích xuất dữ liệu' },
  { n: 3, label: 'Xem xét & Chỉnh sửa' },
  { n: 4, label: 'Đánh giá AI' },
  { n: 5, label: 'Báo cáo PDF' },
]

// ── State ──────────────────────────────────────────────────────────────────────
const view = ref('list')
const listItems = ref([])
const listLoading = ref(false)
const totalCount = ref(0)

const uploadFile = ref(null)
const uploading = ref(false)
const uploadError = ref('')

const evalDoc = ref({})
const editData = ref(null)
const evalResult = ref(null)
const warningList = ref([])
const missingList = ref([])
const processing = ref(false)
const saving = ref(false)
const progressMsg = ref('')
const progressPct = ref(0)
const detailError = ref('')

const openSections = ref({ doc: true, emp: true, proposals: true, kpi: true })
function toggleSection(k) { openSections.value[k] = !openSections.value[k] }

// ── Step logic ─────────────────────────────────────────────────────────────────
const currentStep = computed(() => {
  const s = evalDoc.value.status
  if (!s || s === 'Uploaded') return 2
  if (s === 'Extracting') return 2
  if (s === 'Pending Review') return 3
  if (s === 'Confirmed') return 4
  if (s === 'Evaluating') return 4
  if (s === 'Evaluated') return 5
  if (s === 'Report Generated') return 5
  if (s === 'Failed') return 2
  return 2
})

function stepState(n) {
  if (n === 1) return 'done'
  const cur = currentStep.value
  if (n < cur) return 'done'
  if (n === cur) return 'active'
  return 'pending'
}

function dotClass(n) {
  const s = stepState(n)
  return s === 'done' ? 'vs-dot-done' : s === 'active' ? 'vs-dot-active' : 'vs-dot-pending'
}

// ── Helpers ────────────────────────────────────────────────────────────────────
const PROPOSAL_LABELS = {
  SALARY_INCREASE:'Tăng lương', TITLE_APPOINTMENT:'Bổ nhiệm chức danh',
  TITLE_ADJUSTMENT:'Điều chỉnh chức danh', GRADE_CHANGE:'Thay đổi cấp bậc',
  BENEFIT_ADJUSTMENT:'Điều chỉnh đãi ngộ', ROLE_CHANGE:'Điều chuyển vai trò', OTHER:'Khác',
}
function proposalLabel(t) { return PROPOSAL_LABELS[t] || t || '—' }

const REC_LABELS = {
  APPROVE:'Phê duyệt', APPROVE_WITH_CONDITIONS:'Phê duyệt có điều kiện',
  PARTIALLY_APPROVE:'Phê duyệt một phần', REQUEST_MORE_INFO:'Cần bổ sung TT', REJECT:'Không phê duyệt',
}
function recLabel(r) { return REC_LABELS[r] || r || '—' }
function recClass(r) {
  return { APPROVE:'rec-green', APPROVE_WITH_CONDITIONS:'rec-blue', PARTIALLY_APPROVE:'rec-indigo',
           REQUEST_MORE_INFO:'rec-yellow', REJECT:'rec-red' }[r] || 'rec-gray'
}
function statusDotClass(s) {
  return { Uploaded:'dot-blue', Extracting:'dot-orange', 'Pending Review':'dot-yellow',
           Confirmed:'dot-indigo', Evaluating:'dot-orange', Evaluated:'dot-green',
           'Report Generated':'dot-emerald', Failed:'dot-red' }[s] || 'dot-gray'
}
function scoreClass(n) {
  if (!n && n !== 0) return ''
  if (n >= 85) return 'score-green'; if (n >= 70) return 'score-blue'
  if (n >= 55) return 'score-yellow'; return 'score-red'
}
function ctClass(cs) {
  if (!cs.maxScore) return ''
  const p = cs.score / cs.maxScore
  return p >= 0.8 ? 'ct-green' : p >= 0.6 ? 'ct-yellow' : 'ct-red'
}
function fmtSize(b) { return b < 1e6 ? `${(b/1024).toFixed(0)} KB` : `${(b/1e6).toFixed(1)} MB` }
function computeDelta(item) {
  const c = parseFloat(String(item.currentValue||'').replace(/\D/g,''))
  const p = parseFloat(String(item.proposedValue||'').replace(/\D/g,''))
  if (!isNaN(c) && !isNaN(p) && c > 0) {
    const d = p - c, pct = (d/c*100).toFixed(1)
    return `Chênh lệch: ${d>0?'+':''}${d.toLocaleString('vi-VN')}đ (${pct}%)`
  }
  return ''
}

// ── API ────────────────────────────────────────────────────────────────────────
function apiUrl(m) { return `/api/method/cnb_2as.api.de_xuat.${m}` }
async function apiGet(m, params={}) {
  const qs = new URLSearchParams(params).toString()
  const r = await fetch(`${apiUrl(m)}${qs?'?'+qs:''}`)
  const j = await r.json()
  if (j._error_message || j.exc) throw new Error(j._error_message || j.exc_type || 'Lỗi server')
  return j.message || j
}
async function apiPost(m, body={}) {
  const r = await fetch(apiUrl(m), { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body) })
  const j = await r.json()
  if (j._error_message || j.exc) throw new Error(j._error_message || j.exc_type || 'Lỗi server')
  return j.message || j
}

// ── Navigation ─────────────────────────────────────────────────────────────────
function backToList() { view.value='list'; evalDoc.value={}; editData.value=null; evalResult.value=null; detailError.value=''; loadList() }
function startNew() { view.value='new'; uploadFile.value=null; uploadError.value='' }
async function openEval(name) { view.value='detail'; detailError.value=''; await loadDetail(name) }

// ── List ───────────────────────────────────────────────────────────────────────
async function loadList() {
  listLoading.value = true
  try {
    const r = await apiGet('list_evaluations', { page:1, page_size:30 })
    listItems.value = r.items||[]; totalCount.value = r.total||0
  } catch(e) { console.error(e) } finally { listLoading.value=false }
}

// ── Detail ─────────────────────────────────────────────────────────────────────
async function loadDetail(name) {
  try {
    const r = await apiGet('get_evaluation', { evaluation_name:name })
    evalDoc.value = r
    warningList.value = r.warnings||[]; missingList.value = r.missing_fields||[]
    const src = r.user_corrected || r.extracted
    if (src) {
      editData.value = JSON.parse(JSON.stringify(src))
      editData.value.documentMetadata = editData.value.documentMetadata||{}
      editData.value.employee = editData.value.employee||{}
      editData.value.proposalItems = editData.value.proposalItems||[]
      editData.value.evaluationContext = editData.value.evaluationContext||{}
    }
    evalResult.value = r.evaluation_result||null
  } catch(e) { detailError.value=`Lỗi: ${e.message}` }
}

// ── Upload ─────────────────────────────────────────────────────────────────────
function handleDrop(e) { if(e.dataTransfer.files.length) setFile(e.dataTransfer.files[0]) }
function handleFileSelect(e) { if(e.target.files.length) setFile(e.target.files[0]) }
function setFile(f) {
  const ext=f.name.split('.').pop().toLowerCase()
  if(!['pdf','png','jpg','jpeg','docx','doc'].includes(ext)) { uploadError.value=`Không hỗ trợ .${ext}`; return }
  if(f.size>30*1024*1024) { uploadError.value='File quá lớn (>30MB)'; return }
  uploadError.value=''; uploadFile.value=f
}
async function doUpload() {
  if(!uploadFile.value) return
  uploading.value=true; uploadError.value=''
  try {
    const fd=new FormData(); fd.append('file',uploadFile.value); fd.append('is_private','1')
    const r=await fetch(apiUrl('upload_file'),{method:'POST',body:fd})
    const j=await r.json()
    if(j._error_message||j.exc) throw new Error(j._error_message||'Lỗi upload')
    await openEval((j.message||j).evaluation_name)
  } catch(e) { uploadError.value=`Lỗi: ${e.message}` } finally { uploading.value=false }
}

// ── Extract ────────────────────────────────────────────────────────────────────
async function doExtract() {
  processing.value=true; progressMsg.value='AI đang đọc và trích xuất tờ trình...'; progressPct.value=30; detailError.value=''
  try {
    const r=await apiGet('extract_data',{evaluation_name:evalDoc.value.name})
    evalDoc.value.status=r.status; evalDoc.value.page_count=r.page_count
    const e=r.extracted; editData.value=JSON.parse(JSON.stringify(e))
    editData.value.documentMetadata=editData.value.documentMetadata||{}
    editData.value.employee=editData.value.employee||{}
    editData.value.proposalItems=editData.value.proposalItems||[]
    editData.value.evaluationContext=editData.value.evaluationContext||{}
    if(e.employee?.fullName) evalDoc.value.employee_name=e.employee.fullName
    if(e.employee?.department) evalDoc.value.department=e.employee.department
    warningList.value=r.warnings||[]; missingList.value=r.missing_fields||[]
  } catch(e) { detailError.value=`Lỗi trích xuất: ${e.message}`; evalDoc.value.status='Failed'
  } finally { processing.value=false; progressMsg.value=''; progressPct.value=0 }
}

// ── Save ───────────────────────────────────────────────────────────────────────
async function saveCorrections() {
  if(!editData.value) return
  saving.value=true
  try { await apiPost('update_extracted',{evaluation_name:evalDoc.value.name,corrected_json:JSON.stringify(editData.value)})
  } catch(e){ detailError.value=`Lỗi lưu: ${e.message}` } finally{ saving.value=false }
}

// ── Confirm ────────────────────────────────────────────────────────────────────
async function doConfirm() {
  processing.value=true; progressMsg.value='Đang xác nhận...'; progressPct.value=50; detailError.value=''
  try {
    await saveCorrections()
    const r=await apiGet('confirm_data',{evaluation_name:evalDoc.value.name})
    evalDoc.value.status=r.status; evalDoc.value.confirmed_by=r.confirmed_by
  } catch(e){ detailError.value=`Lỗi xác nhận: ${e.message}`
  } finally{ processing.value=false; progressMsg.value=''; progressPct.value=0 }
}

// ── Evaluate ───────────────────────────────────────────────────────────────────
async function doEvaluate() {
  processing.value=true; progressMsg.value='AI đang đánh giá đề xuất...'; progressPct.value=40; detailError.value=''
  try {
    const r=await apiGet('evaluate',{evaluation_name:evalDoc.value.name})
    evalDoc.value.status=r.status; evalDoc.value.overall_score=r.overall_score; evalDoc.value.recommendation=r.recommendation
    evalResult.value=r.evaluation_result
  } catch(e){ detailError.value=`Lỗi đánh giá: ${e.message}`; evalDoc.value.status='Failed'
  } finally{ processing.value=false; progressMsg.value=''; progressPct.value=0 }
}

// ── Generate PDF ───────────────────────────────────────────────────────────────
async function doGenerateReport() {
  processing.value=true; progressMsg.value='Đang sinh báo cáo PDF...'; progressPct.value=60; detailError.value=''
  try {
    const url=`${apiUrl('generate_report')}?evaluation_name=${encodeURIComponent(evalDoc.value.name)}`
    const r=await fetch(url)
    if(!r.ok){ const j=await r.json().catch(()=>{}); throw new Error(j?._error_message||`HTTP ${r.status}`) }
    const blob=await r.blob(), bUrl=URL.createObjectURL(blob)
    const a=document.createElement('a')
    a.href=bUrl; a.download=`DanhGiaDXuat_${(evalDoc.value.employee_name||'BaoCao').replace(/\s+/g,'_')}_${evalDoc.value.name}.pdf`
    a.click(); URL.revokeObjectURL(bUrl)
    evalDoc.value.status='Report Generated'
  } catch(e){ detailError.value=`Lỗi PDF: ${e.message}`
  } finally{ processing.value=false; progressMsg.value=''; progressPct.value=0 }
}

onMounted(loadList)
</script>

<style scoped>
@keyframes spin { to { transform: rotate(360deg) } }

/* ── Base layout ─────────────────────────────────────────────────────── */
.app-layout { display: flex; height: 100vh; overflow: hidden; background: #f8fafc }
.sidebar { width: 300px; flex-shrink: 0; display: flex; flex-direction: column; overflow-y: auto; border-right: 1px solid #e2e8f0; background: #fff }
.result-panel { flex: 1; overflow-y: auto; background: #f8fafc }

.sb-top { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 16px; border-bottom: 1px solid #e2e8f0; background: #fff; flex-shrink: 0 }
.sb-reload { width: 30px; height: 30px; border-radius: 7px; border: 1px solid #e2e8f0; background: #f8fafc; color: #64748b; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all .2s }
.sb-reload:hover { background: #f1f5f9; color: #0d9488 }
.sb-back { display: flex; align-items: center; justify-content: center; width: 30px; height: 30px; border-radius: 7px; background: #f1f5f9; color: #64748b; text-decoration: none; transition: all .2s; flex-shrink: 0 }
.sb-back:hover { background: #e2e8f0; color: #334155 }
.sb-logo { display: flex; align-items: center; gap: 9px; flex: 1; min-width: 0 }
.sb-logo-mark { width: 32px; height: 32px; border-radius: 9px; display: flex; align-items: center; justify-content: center; flex-shrink: 0 }
.sb-logo-teal { background: linear-gradient(135deg,#0d9488,#0891b2) }
.sb-name { font-size: .83rem; font-weight: 700; color: #1e293b; white-space: nowrap; overflow: hidden; text-overflow: ellipsis }
.sb-org { font-size: .68rem; color: #94a3b8 }

.sb-body { padding: 14px; flex-grow: 1 }
.sb-section { margin-bottom: 18px }
.sb-section-title { font-size: .7rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: .08em; margin-bottom: 10px }

/* Upload card */
.sb-upload-card { display: flex; align-items: flex-start; gap: 9px; padding: 10px 11px; border-radius: 9px; border: 1.5px dashed #cbd5e1; background: #f8fafc; cursor: pointer; margin-bottom: 7px; transition: all .2s }
.sb-upload-card:hover { border-color: #0d9488; background: rgba(13,148,136,.04) }
.sb-upload-card.filled { border-style: solid; border-color: #22c55e; background: rgba(34,197,94,.05) }
.sb-upload-card.err { border-color: #ef4444; background: rgba(239,68,68,.05) }
.upc-icon { font-size: 18px; margin-top: 1px }
.upc-info { flex: 1; min-width: 0 }
.upc-label { font-size: .68rem; font-weight: 600; color: #64748b }
.upc-val { font-size: .78rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis }
.upc-val.ok { color: #16a34a }; .upc-val.empty { color: #94a3b8 }
.upc-hint { font-size: .65rem; color: #94a3b8; margin-top: 1px }
.upc-rm { background: none; border: none; color: #94a3b8; cursor: pointer; padding: 2px 4px; border-radius: 4px; font-size: 11px; flex-shrink: 0 }
.upc-rm:hover { background: #fee2e2; color: #ef4444 }
.sb-err { font-size: .75rem; color: #ef4444; margin: 4px 0 8px }

/* Buttons */
.sb-btn-primary { width: 100%; padding: 9px; border: none; border-radius: 9px; background: linear-gradient(135deg,#0d9488,#0891b2); color: #fff; font-weight: 600; font-size: .84rem; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 7px; transition: opacity .2s; margin-top: 6px }
.sb-btn-primary:disabled { opacity: .5; cursor: not-allowed }
.sb-btn-secondary { width: 100%; padding: 8px; border: 1px solid #0d9488; border-radius: 9px; background: #fff; color: #0d9488; font-weight: 600; font-size: .82rem; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 7px; margin-top: 6px; transition: all .2s }
.sb-btn-secondary:hover { background: rgba(13,148,136,.06) }
.spinner { width: 14px; height: 14px; border: 2px solid rgba(255,255,255,.3); border-top-color: #fff; border-radius: 50%; animation: spin .6s linear infinite; flex-shrink: 0 }
.spinner-dark { border-color: rgba(13,148,136,.25); border-top-color: #0d9488 }

/* Progress */
.sb-progress-text { font-size: .72rem; color: #64748b; margin-bottom: 5px }
.sb-progress-bar { height: 3px; background: #e2e8f0; border-radius: 2px; overflow: hidden }
.sb-progress-fill { height: 100%; background: linear-gradient(90deg,#0d9488,#6366f1); border-radius: 2px; transition: width .5s }

/* Record chip */
.dx-record-chip { display: flex; align-items: center; justify-content: space-between; margin-bottom: 3px }
.dx-emp-name { font-size: .86rem; font-weight: 700; color: #1e293b }
.dx-emp-dept { font-size: .72rem; color: #64748b; margin-bottom: 6px }
.mono { font-family: monospace }
.small { font-size: .72rem }

/* Score box */
.sb-score-box { padding: 12px; background: rgba(13,148,136,.06); border: 1px solid rgba(13,148,136,.18); border-radius: 10px; text-align: center }
.sb-score-num { font-size: 1.5rem; font-weight: 800; line-height: 1 }
.sb-score-lbl { font-size: .7rem; color: #64748b; margin-bottom: 6px }

/* Status dots */
.dx-status-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0 }
.dot-blue { background: #3b82f6 }; .dot-orange { background: #f97316 }; .dot-yellow { background: #eab308 }
.dot-indigo { background: #6366f1 }; .dot-green { background: #22c55e }; .dot-emerald { background: #10b981 }
.dot-red { background: #ef4444 }; .dot-gray { background: #94a3b8 }

/* ── Vertical stepper ─────────────────────────────────────────────── */
.vs-stepper { display: flex; flex-direction: column }
.vs-item { display: flex; gap: 10px; align-items: flex-start }
.vs-left { display: flex; flex-direction: column; align-items: center; width: 24px; flex-shrink: 0 }
.vs-dot { width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: .72rem; font-weight: 700; flex-shrink: 0 }
.vs-dot-done { background: #0d9488; color: #fff }
.vs-dot-active { background: #fff; border: 2px solid #0d9488; color: #0d9488 }
.vs-dot-pending { background: #f1f5f9; border: 1.5px solid #e2e8f0; color: #94a3b8 }
.vs-line { width: 2px; flex: 1; min-height: 12px; background: #e2e8f0; margin: 3px 0 }
.vs-line-done { background: #0d9488 }
.vs-text { padding: 4px 0 12px; font-size: .78rem; line-height: 1.3 }
.vs-text-done { color: #0d9488; font-weight: 600 }
.vs-text-active { color: #1e293b; font-weight: 700 }
.vs-text-pending { color: #94a3b8 }
.vs-spin { width: 10px; height: 10px; border: 1.5px solid rgba(13,148,136,.3); border-top-color: #0d9488; border-radius: 50%; animation: spin .7s linear infinite; display: block }

/* ── List ─────────────────────────────────────────────────────────── */
.sb-list-loading { display: flex; justify-content: center; padding: 16px 0 }
.dx-list { display: flex; flex-direction: column; gap: 3px; max-height: 320px; overflow-y: auto }
.dx-list-item { padding: 8px 10px; border-radius: 7px; cursor: pointer; border: 1px solid transparent; transition: all .15s }
.dx-list-item:hover { background: #f1f5f9; border-color: #e2e8f0 }
.dx-list-item.active { background: rgba(13,148,136,.06); border-color: rgba(13,148,136,.25) }
.dx-li-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 2px }
.dx-li-name { font-size: .8rem; font-weight: 600; color: #1e293b }
.dx-li-meta { display: flex; align-items: center; justify-content: space-between }
.dx-li-status { font-size: .65rem; color: #94a3b8; margin-top: 1px }
.dx-li-score { font-size: .7rem; font-weight: 700 }
.dx-list-empty { font-size: .8rem; color: #94a3b8; text-align: center; padding: 16px 0 }

/* ── Welcome ──────────────────────────────────────────────────────── */
.welcome { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; padding: 40px; text-align: center }
.welcome-icon { margin-bottom: 20px }
.welcome h1 { font-size: 1.4rem; font-weight: 800; margin-bottom: 10px; color: #1e293b }
.welcome p { max-width: 480px; color: #64748b; line-height: 1.6 }
.welcome-features { display: flex; gap: 16px; margin-top: 28px; flex-wrap: wrap; justify-content: center }
.wf { display: flex; flex-direction: column; align-items: center; gap: 6px; font-size: .8rem; color: #64748b; max-width: 110px; text-align: center }
.wf-icon { font-size: 22px }
.loading-spinner { border: 3px solid rgba(13,148,136,.15); border-top-color: #0d9488; border-radius: 50%; animation: spin 1s linear infinite }

/* ── Wizard scroll area ───────────────────────────────────────────── */
.wizard-scroll { padding: 24px 28px; max-width: 860px }

/* Step card */
.wz-step { background: #fff; border: 1px solid #e2e8f0; border-radius: 14px; margin-bottom: 14px; overflow: hidden; transition: all .2s }
.wz-active { border-color: #0d9488; box-shadow: 0 0 0 3px rgba(13,148,136,.08) }
.wz-done { border-color: #e2e8f0; opacity: 1 }
.wz-pending { opacity: .45; pointer-events: none }

.wz-head { display: flex; align-items: center; gap: 12px; padding: 14px 18px; background: #fafbfc }
.wz-active .wz-head { background: rgba(13,148,136,.04) }
.wz-done .wz-head { background: #fafbfc }
.wz-num { width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: .78rem; font-weight: 700; flex-shrink: 0 }
.wz-num-done { background: #0d9488; color: #fff }
.wz-num-active { background: #fff; border: 2px solid #0d9488; color: #0d9488 }
.wz-num-pending { background: #f1f5f9; border: 1.5px solid #e2e8f0; color: #94a3b8 }
.wz-title { flex: 1; font-weight: 700; font-size: .9rem; color: #1e293b }
.wz-hint { font-size: .74rem; color: #0d9488; white-space: nowrap }
.wz-badge-done { font-size: .72rem; font-weight: 700; color: #16a34a; background: rgba(34,197,94,.1); padding: 2px 8px; border-radius: 4px }
.wz-link { font-size: .75rem; color: #0d9488; text-decoration: none; white-space: nowrap }
.wz-link:hover { text-decoration: underline }

.wz-body { padding: 16px 18px; border-top: 1px solid #f1f5f9 }
.wz-active .wz-body { border-top-color: rgba(13,148,136,.15) }

/* Step body helpers */
.wz-info-row { display: flex; gap: 12px; margin-bottom: 6px; font-size: .84rem }
.wz-lbl { font-weight: 600; color: #64748b; width: 90px; flex-shrink: 0 }
.wz-loading { display: flex; align-items: center; gap: 12px; color: #64748b; font-size: .84rem; padding: 8px 0 }
.wz-prompt { font-size: .84rem; color: #64748b; line-height: 1.6; padding: 4px 0 }
.wz-warn-row { display: flex; align-items: center; gap: 6px; font-size: .78rem; color: #ca8a04; margin-top: 6px }
.wz-confirmed-row { display: flex; align-items: center; gap: 6px; font-size: .78rem; color: #16a34a; margin-top: 10px; padding-top: 10px; border-top: 1px solid #f1f5f9 }
.wz-done-row { display: flex; align-items: center; gap: 6px; font-size: .82rem; color: #16a34a }

/* Subsections */
.wz-sub-section { margin-bottom: 14px }
.wz-sub-title { font-size: .78rem; font-weight: 700; color: #475569; margin-bottom: 8px; display: flex; align-items: center; justify-content: space-between; cursor: pointer; user-select: none; padding: 6px 0; border-bottom: 1px solid #f1f5f9 }
.wz-sub-title.warn { color: #ca8a04 }
.wz-toggle { font-size: .7rem; color: #94a3b8 }
.wz-add-btn { padding: 5px 12px; border: 1px solid #0d9488; border-radius: 6px; background: transparent; color: #0d9488; font-size: .78rem; cursor: pointer; margin-top: 4px }
.wz-add-btn:hover { background: rgba(13,148,136,.06) }
.wz-spin { width: 12px; height: 12px; border: 2px solid rgba(13,148,136,.2); border-top-color: #0d9488; border-radius: 50%; animation: spin .7s linear infinite; display: block }

/* Edit form */
.dx-edit-grid { display: grid; grid-template-columns: repeat(2,1fr); gap: 8px }
.dx-ef { display: flex; flex-direction: column; gap: 3px }
.dx-ef-full { grid-column: 1/-1 }
.dx-ef label { font-size: .69rem; font-weight: 600; color: #64748b }
.req { color: #ef4444 }
.dx-ef input, .dx-ef textarea, .dx-ef select { padding: 6px 9px; border: 1px solid #e2e8f0; border-radius: 7px; font-size: .82rem; color: #334155; background: #fff; font-family: inherit; outline: none; transition: border .2s }
.dx-ef input:focus, .dx-ef textarea:focus { border-color: #0d9488 }
.dx-ef input:disabled, .dx-ef textarea:disabled, .dx-ef select:disabled { background: #f8fafc; color: #94a3b8; cursor: default }

.dx-pi-card { padding: 10px; border: 1px solid #e2e8f0; border-radius: 8px; margin-bottom: 8px; background: #fafbfc }
.dx-pi-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px }
.dx-select { padding: 5px 8px; border: 1px solid #e2e8f0; border-radius: 6px; font-size: .78rem; color: #334155; background: #fff }
.dx-rm-btn { background: none; border: none; color: #94a3b8; cursor: pointer; padding: 2px 6px; border-radius: 4px; font-size: 12px }
.dx-rm-btn:hover { background: #fee2e2; color: #ef4444 }
.dx-delta-row { font-size: .74rem; color: #0d9488; font-weight: 600; margin-top: 4px; padding: 4px 8px; background: rgba(13,148,136,.06); border-radius: 5px }

/* Warn list */
.dx-warn-list { padding-left: 14px; font-size: .8rem; color: #92400e; margin: 0 }
.dx-warn-list li { margin-bottom: 3px }

/* Overall score */
.wz-overall { display: flex; align-items: flex-start; gap: 14px; margin-bottom: 14px }
.dx-score-circle { width: 60px; height: 60px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; font-weight: 800; border: 3px solid currentColor; flex-shrink: 0 }
.score-green { color: #16a34a }; .score-blue { color: #2563eb }; .score-yellow { color: #ca8a04 }; .score-red { color: #dc2626 }
.wz-overall-lbl { font-size: .72rem; color: #64748b; margin-bottom: 5px }
.wz-summary { font-size: .82rem; color: #475569; line-height: 1.6; margin-top: 6px }

.wz-note { display: flex; gap: 7px; background: rgba(234,179,8,.06); border: 1px solid rgba(234,179,8,.2); border-radius: 8px; padding: 10px 12px; font-size: .78rem; color: #92400e; line-height: 1.5; margin-bottom: 14px }

/* Per-proposal eval card */
.wz-pe-card { border: 1px solid #e2e8f0; border-radius: 10px; margin-bottom: 12px; overflow: hidden }
.wz-pe-head { display: flex; align-items: center; gap: 8px; padding: 10px 14px; background: #f8fafc; flex-wrap: wrap }
.wz-pe-title { font-weight: 700; font-size: .86rem; flex: 1; min-width: 0 }
.wz-pe-score { font-weight: 800; font-size: .9rem; margin-left: auto }

/* Comp table */
.comp-table { width: 100%; border-collapse: collapse; font-size: .82rem }
.comp-table th { padding: 7px 10px; text-align: left; background: #f8fafc; color: #64748b; font-weight: 600; font-size: .75rem; border-bottom: 1px solid #e2e8f0 }
.comp-table td { padding: 8px 10px; border-bottom: 1px solid #f8fafc }
.ct-green { color: #16a34a }; .ct-yellow { color: #ca8a04 }; .ct-red { color: #dc2626 }
.dx-total-row td { background: #f8fafc; font-size: .84rem }

/* Reasons */
.wz-reasons { padding: 10px 14px; display: flex; flex-direction: column; gap: 8px }
.wr-group { font-size: .8rem }
.wr-lbl { font-weight: 700; display: block; margin-bottom: 3px }
.wr-lbl.pass { color: #16a34a }; .wr-lbl.fail { color: #dc2626 }; .wr-lbl.warn { color: #ca8a04 }; .wr-lbl.info { color: #2563eb }
.wr-group ul { margin: 0; padding-left: 14px; color: #475569 }
.wr-group li { margin-bottom: 2px; line-height: 1.45 }

/* Final rec */
.wz-final-rec { background: rgba(13,148,136,.04); border: 1px solid rgba(13,148,136,.15); border-radius: 10px; padding: 14px 16px; margin-top: 4px }
.wz-fr-title { font-size: .78rem; font-weight: 700; color: #64748b; margin-bottom: 8px }

/* Rec badges */
.dx-rec-badge { display: inline-block; padding: 3px 9px; border-radius: 5px; font-size: .74rem; font-weight: 700 }
.dx-rec-lg { padding: 7px 16px; font-size: .9rem; border-radius: 8px }
.rec-green  { background: rgba(34,197,94,.1);  color: #16a34a }
.rec-blue   { background: rgba(59,130,246,.1);  color: #2563eb }
.rec-indigo { background: rgba(99,102,241,.1);  color: #4f46e5 }
.rec-yellow { background: rgba(234,179,8,.1);   color: #ca8a04 }
.rec-red    { background: rgba(239,68,68,.1);   color: #dc2626 }
.rec-gray   { background: rgba(148,163,184,.1); color: #64748b }

/* DL button */
.wz-dl-btn { display: inline-flex; align-items: center; gap: 7px; padding: 9px 18px; background: linear-gradient(135deg,#0d9488,#0891b2); color: #fff; border: none; border-radius: 9px; font-weight: 600; font-size: .86rem; cursor: pointer; transition: opacity .2s }
.wz-dl-btn:disabled { opacity: .5; cursor: not-allowed }

/* ── Dark mode overrides ─────────────────────────────────────────── */
body.theme-dark .app-layout { background: #0f0f1a }
body.theme-dark .sidebar { background: #13131a; border-right-color: rgba(99,102,241,.1) }
body.theme-dark .sb-top { background: #13131a; border-bottom-color: rgba(255,255,255,.06) }
body.theme-dark .sb-back { background: rgba(255,255,255,.06); color: #94a3b8 }
body.theme-dark .sb-reload { background: rgba(255,255,255,.04); border-color: rgba(255,255,255,.08); color: #94a3b8 }
body.theme-dark .sb-name { color: #f1f5f9 }
body.theme-dark .sb-org { color: #64748b }
body.theme-dark .result-panel { background: #0f0f14 }
body.theme-dark .sb-btn-secondary { background: transparent; color: #2dd4bf; border-color: rgba(13,148,136,.3) }
body.theme-dark .sb-upload-card { background: rgba(255,255,255,.03); border-color: rgba(255,255,255,.1) }
body.theme-dark .sb-upload-card:hover { border-color: rgba(13,148,136,.4); background: rgba(13,148,136,.06) }
body.theme-dark .vs-dot-pending { background: rgba(255,255,255,.05); border-color: rgba(255,255,255,.1) }
body.theme-dark .vs-line { background: rgba(255,255,255,.08) }
body.theme-dark .vs-text-pending { color: #4b5563 }
body.theme-dark .vs-text-active { color: #f1f5f9 }
body.theme-dark .dx-li-name { color: #f1f5f9 }
body.theme-dark .dx-list-item:hover { background: rgba(255,255,255,.04); border-color: rgba(255,255,255,.06) }
body.theme-dark .dx-list-item.active { background: rgba(13,148,136,.1); border-color: rgba(13,148,136,.3) }
body.theme-dark .dx-emp-name { color: #f1f5f9 }
body.theme-dark .welcome h1 { color: #f1f5f9 }
body.theme-dark .welcome p { color: #94a3b8 }
body.theme-dark .wz-step { background: rgba(30,32,48,.6); border-color: rgba(99,102,241,.1) }
body.theme-dark .wz-active { border-color: #0d9488; box-shadow: 0 0 0 3px rgba(13,148,136,.12) }
body.theme-dark .wz-head { background: rgba(255,255,255,.02) }
body.theme-dark .wz-active .wz-head { background: rgba(13,148,136,.06) }
body.theme-dark .wz-title { color: #e2e8f0 }
body.theme-dark .wz-body { border-top-color: rgba(255,255,255,.05) }
body.theme-dark .wz-lbl { color: #94a3b8 }
body.theme-dark .wz-prompt { color: #94a3b8 }
body.theme-dark .wz-summary { color: #94a3b8 }
body.theme-dark .wz-info-row { color: #cbd5e1 }
body.theme-dark .wz-sub-title { color: #94a3b8; border-bottom-color: rgba(255,255,255,.06) }
body.theme-dark .wz-num-active { background: #13131a; border-color: #0d9488; color: #0d9488 }
body.theme-dark .dx-ef input, body.theme-dark .dx-ef textarea, body.theme-dark .dx-ef select { background: rgba(255,255,255,.05); border-color: rgba(255,255,255,.1); color: #e2e8f0 }
body.theme-dark .dx-ef input:disabled, body.theme-dark .dx-ef textarea:disabled { background: rgba(255,255,255,.02); color: #64748b }
body.theme-dark .dx-pi-card { background: rgba(255,255,255,.03); border-color: rgba(255,255,255,.08) }
body.theme-dark .wz-pe-card { border-color: rgba(255,255,255,.08) }
body.theme-dark .wz-pe-head { background: rgba(255,255,255,.03) }
body.theme-dark .comp-table th { background: rgba(99,102,241,.08); color: #94a3b8 }
body.theme-dark .comp-table td { border-bottom-color: rgba(255,255,255,.04); color: #cbd5e1 }
body.theme-dark .dx-total-row td { background: rgba(255,255,255,.04) }
body.theme-dark .wz-note { background: rgba(234,179,8,.06); border-color: rgba(234,179,8,.15); color: #ca8a04 }
body.theme-dark .wz-final-rec { background: rgba(13,148,136,.06); border-color: rgba(13,148,136,.2) }
body.theme-dark .wr-group ul { color: #94a3b8 }
body.theme-dark .sb-score-box { background: rgba(13,148,136,.08); border-color: rgba(13,148,136,.2) }
</style>
