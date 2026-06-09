<template>
  <!-- Gợi ý JD (Job Description) -->
  <div class="jd-card">
    <div class="jd-header" @click="$emit('toggle')">
      <div style="display:flex;align-items:center;gap:10px">
        <span style="font-size:1.2rem">📄</span>
        <div>
          <div class="jd-title">Gợi ý Mô tả Công việc (JD)</div>
          <div class="jd-subtitle" v-if="jd.chuc_danh">{{ jd.chuc_danh }}<span v-if="jd.cap_bac"> · {{ jd.cap_bac }}</span></div>
        </div>
      </div>
      <span class="jd-arrow" :class="{open: expanded}">›</span>
    </div>

    <div v-if="expanded" class="jd-body">
      <!-- Meta row -->
      <div class="jd-meta-row">
        <div v-if="jd.chuc_danh" class="jd-meta-chip jd-chip-blue">
          <span class="jd-chip-icon">👤</span>{{ jd.chuc_danh }}
        </div>
        <div v-if="jd.phong_ban" class="jd-meta-chip jd-chip-purple">
          <span class="jd-chip-icon">🏢</span>{{ jd.phong_ban }}
        </div>
        <div v-if="jd.cap_bac" class="jd-meta-chip jd-chip-teal">
          <span class="jd-chip-icon">⭐</span>{{ jd.cap_bac }}
        </div>
      </div>

      <!-- Tóm tắt vị trí -->
      <div v-if="jd.tom_tat" class="jd-section">
        <div class="jd-section-title">📋 Mô tả vị trí</div>
        <p class="jd-paragraph">{{ jd.tom_tat }}</p>
      </div>

      <!-- Nhiệm vụ chính -->
      <div v-if="jd.nhiem_vu_chinh?.length" class="jd-section">
        <div class="jd-section-title">✅ Nhiệm vụ chính</div>
        <ul class="jd-list">
          <li v-for="(nv, i) in jd.nhiem_vu_chinh" :key="i">{{ nv }}</li>
        </ul>
      </div>

      <!-- Yêu cầu năng lực -->
      <div v-if="jd.yeu_cau_nang_luc?.length" class="jd-section">
        <div class="jd-section-title">🎯 Yêu cầu năng lực</div>
        <div class="jd-nang-luc-grid">
          <div v-for="(nl, i) in jd.yeu_cau_nang_luc" :key="i" class="jd-nl-card" :class="nlClass(nl.loai)">
            <div class="jd-nl-loai">{{ nl.loai }}</div>
            <div class="jd-nl-mota">{{ nl.mo_ta }}</div>
          </div>
        </div>
      </div>

      <!-- Kinh nghiệm + Học vấn -->
      <div v-if="jd.yeu_cau_kinh_nghiem || jd.trinh_do_hoc_van" class="jd-section">
        <div class="jd-section-title">📚 Yêu cầu chung</div>
        <div class="jd-req-row">
          <div v-if="jd.yeu_cau_kinh_nghiem" class="jd-req-item">
            <span class="jd-req-icon">⏱️</span>
            <div>
              <div class="jd-req-label">Kinh nghiệm</div>
              <div class="jd-req-val">{{ jd.yeu_cau_kinh_nghiem }}</div>
            </div>
          </div>
          <div v-if="jd.trinh_do_hoc_van" class="jd-req-item">
            <span class="jd-req-icon">🎓</span>
            <div>
              <div class="jd-req-label">Trình độ học vấn</div>
              <div class="jd-req-val">{{ jd.trinh_do_hoc_van }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- KPI tham chiếu -->
      <div v-if="jd.kpi_tham_chieu?.length" class="jd-section">
        <div class="jd-section-title">📊 KPI tham chiếu</div>
        <ul class="jd-kpi-list">
          <li v-for="(kpi, i) in jd.kpi_tham_chieu" :key="i">
            <span class="jd-kpi-dot">▸</span>{{ kpi }}
          </li>
        </ul>
      </div>

      <!-- Ghi chú -->
      <div v-if="jd.ghi_chu" class="jd-note">
        <span style="font-weight:700;color:#7c3aed">📝 Ghi chú: </span>{{ jd.ghi_chu }}
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({ jd: { type: Object, required: true }, expanded: { type: Boolean, default: true } })
defineEmits(['toggle'])

const nlClass = (loai) => {
  if (!loai) return 'jd-nl-default'
  const l = loai.toLowerCase()
  if (l.includes('chuyên') || l.includes('mon')) return 'jd-nl-blue'
  if (l.includes('kỹ') || l.includes('ky') || l.includes('skill')) return 'jd-nl-green'
  return 'jd-nl-orange'
}
</script>

<style scoped>
.jd-card { background: #fff; border: 1px solid #e2e8f0; border-radius: 14px; overflow: hidden; margin-bottom: 14px; box-shadow: 0 2px 8px rgba(0,0,0,.04); }

.jd-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 18px; cursor: pointer;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff; user-select: none;
}
.jd-title  { font-size: .9rem; font-weight: 800; letter-spacing: .02em; }
.jd-subtitle { font-size: .75rem; opacity: .85; margin-top: 2px; }
.jd-arrow  { font-size: 1.4rem; transition: transform .25s; opacity: .8; }
.jd-arrow.open { transform: rotate(90deg); }

.jd-body { padding: 16px 18px; }

.jd-meta-row { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 14px; }
.jd-meta-chip { display: flex; align-items: center; gap: 5px; padding: 4px 10px; border-radius: 20px; font-size: .75rem; font-weight: 700; }
.jd-chip-icon { font-size: .85rem; }
.jd-chip-blue   { background: rgba(99,102,241,.12); color: #4f46e5; }
.jd-chip-purple { background: rgba(139,92,246,.12);  color: #7c3aed; }
.jd-chip-teal   { background: rgba(20,184,166,.12);  color: #0d9488; }

.jd-section { margin-bottom: 14px; }
.jd-section-title { font-size: .72rem; font-weight: 800; text-transform: uppercase; letter-spacing: .07em; color: #64748b; margin-bottom: 7px; }
.jd-paragraph { font-size: .86rem; color: #334155; line-height: 1.7; margin: 0; }

.jd-list { margin: 0; padding-left: 18px; }
.jd-list li { font-size: .85rem; color: #334155; line-height: 1.6; margin-bottom: 4px; }

.jd-nang-luc-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 8px; }
.jd-nl-card { padding: 10px 12px; border-radius: 8px; border-left: 3px solid; }
.jd-nl-loai { font-size: .68rem; font-weight: 800; text-transform: uppercase; letter-spacing: .05em; margin-bottom: 4px; }
.jd-nl-mota { font-size: .8rem; line-height: 1.5; }
.jd-nl-blue   { background: #eff6ff; border-color: #3b82f6; } .jd-nl-blue .jd-nl-loai   { color: #2563eb; }
.jd-nl-green  { background: #f0fdf4; border-color: #22c55e; } .jd-nl-green .jd-nl-loai  { color: #16a34a; }
.jd-nl-orange { background: #fff7ed; border-color: #f59e0b; } .jd-nl-orange .jd-nl-loai { color: #d97706; }
.jd-nl-default { background: #f8fafc; border-color: #94a3b8; } .jd-nl-default .jd-nl-loai { color: #475569; }

.jd-req-row { display: flex; gap: 10px; flex-wrap: wrap; }
.jd-req-item { display: flex; align-items: flex-start; gap: 8px; padding: 8px 12px; background: #f8fafc; border-radius: 8px; flex: 1; min-width: 180px; }
.jd-req-icon { font-size: 1.1rem; flex-shrink: 0; }
.jd-req-label { font-size: .65rem; font-weight: 700; text-transform: uppercase; color: #64748b; margin-bottom: 2px; }
.jd-req-val { font-size: .82rem; color: #1e293b; font-weight: 600; }

.jd-kpi-list { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: 1fr 1fr; gap: 5px; }
.jd-kpi-list li { display: flex; align-items: flex-start; gap: 5px; font-size: .82rem; color: #334155; padding: 4px 6px; background: #f8fafc; border-radius: 5px; }
.jd-kpi-dot { color: #6366f1; font-weight: 700; flex-shrink: 0; }

.jd-note { padding: 10px 12px; background: #faf5ff; border-radius: 8px; border-left: 3px solid #8b5cf6; font-size: .83rem; color: #334155; line-height: 1.6; }
</style>
