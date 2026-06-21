<template>
<div class="pc-wrap">
  <!-- Header info -->
  <div class="pc-header">
    <div class="pc-info">
      <div class="pc-name">{{ person.ho_ten }}</div>
      <div class="pc-meta">{{ person.chuc_danh }} · {{ person.phong_ban }}</div>
      <div class="pc-meta">TG làm việc: {{ person.thoi_gian_lam_viec }} · Kỳ ĐG: {{ person.ky_danh_gia_tu }} – {{ person.ky_danh_gia_den }}</div>
      <div class="pc-meta">Ngày ĐG: {{ person.ngay_danh_gia }} · Người ĐG: {{ person.nguoi_danh_gia }} ({{ person.chuc_danh_nguoi_danh_gia }})</div>
    </div>
    <div class="pc-totals">
      <div class="pc-total-box nv-box">
        <div class="ptb-label">NV tự ĐG</div>
        <input class="ptb-score" :value="tot100(person.tu_danh_gia)"
          @input="e => setTot100(person.tu_danh_gia, e.target.value)" placeholder="—"/>
        <input class="ptb-xl" :value="normXl(xl(person.tu_danh_gia))"
          @input="e => setXl(person.tu_danh_gia, e.target.value)"
          :style="{ background: xlBg(xl(person.tu_danh_gia)) }" placeholder="XL"/>
      </div>
      <div class="pc-total-box hod-box">
        <div class="ptb-label">HOD ĐG</div>
        <input class="ptb-score" :value="tot100(person.hod)"
          @input="e => setTot100(person.hod, e.target.value)" placeholder="—"/>
        <input class="ptb-xl" :value="normXl(xl(person.hod))"
          @input="e => setXl(person.hod, e.target.value)"
          :style="{ background: xlBg(xl(person.hod)) }" placeholder="XL"/>
      </div>
    </div>
  </div>

  <!-- NHÓM A -->
  <div class="pc-group">
    <div class="pc-group-title group-a">Nhóm A – Tinh thần &amp; Thái độ làm việc (30%) · tối đa 25đ</div>
    <div class="pc-table-wrap">
      <table class="pc-table">
        <thead>
          <tr>
            <th style="width:42px">STT</th>
            <th style="min-width:160px">Tiêu chí</th>
            <th class="th-nv" style="width:70px">NV</th>
            <th class="th-hod" style="width:70px">HOD</th>
            <th class="th-nv" style="width:120px">Nhận xét NV</th>
            <th class="th-hod" style="width:120px">Nhận xét HOD</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="stt in TC_A" :key="stt" class="pc-row">
            <td class="td-stt">{{ stt }}</td>
            <td class="td-name">{{ tcName(person.hod || person.tu_danh_gia, 'nhom_A', stt) }}</td>
            <td class="td-score td-nv">
              <input class="score-input" type="number" min="1" max="5"
                :value="score(person.tu_danh_gia, 'nhom_A', stt)"
                @input="e => setScore(person.tu_danh_gia, 'nhom_A', stt, e.target.value)"/>
            </td>
            <td class="td-score td-hod">
              <input class="score-input" type="number" min="1" max="5"
                :value="score(person.hod, 'nhom_A', stt)"
                @input="e => setScore(person.hod, 'nhom_A', stt, e.target.value)"/>
            </td>
            <td class="td-note td-nv">
              <input class="note-input"
                :value="tcNote(person.tu_danh_gia, 'nhom_A', stt)"
                @input="e => setTcNote(person.tu_danh_gia, 'nhom_A', stt, e.target.value)"/>
            </td>
            <td class="td-note td-hod">
              <input class="note-input"
                :value="tcNote(person.hod, 'nhom_A', stt)"
                @input="e => setTcNote(person.hod, 'nhom_A', stt, e.target.value)"/>
            </td>
          </tr>
          <tr class="total-row">
            <td colspan="2" class="total-label">Tổng nhóm A (thô / quy đổi)</td>
            <td class="td-nv">
              <input class="score-input" :value="nhomTot(person.tu_danh_gia,'nhom_A')"
                @input="e=>setNhomTot(person.tu_danh_gia,'nhom_A',e.target.value)"/>
              <span class="sep">/</span>
              <input class="score-input" :value="nhomQD(person.tu_danh_gia,'nhom_A')"
                @input="e=>setNhomQD(person.tu_danh_gia,'nhom_A',e.target.value)"/>
            </td>
            <td class="td-hod">
              <input class="score-input" :value="nhomTot(person.hod,'nhom_A')"
                @input="e=>setNhomTot(person.hod,'nhom_A',e.target.value)"/>
              <span class="sep">/</span>
              <input class="score-input" :value="nhomQD(person.hod,'nhom_A')"
                @input="e=>setNhomQD(person.hod,'nhom_A',e.target.value)"/>
            </td>
            <td class="td-nv">
              <input class="note-input" :value="nhomRX(person.tu_danh_gia,'nhom_A')"
                @input="e=>setNhomRX(person.tu_danh_gia,'nhom_A',e.target.value)" placeholder="Nhận xét nhóm NV"/>
            </td>
            <td class="td-hod">
              <input class="note-input" :value="nhomRX(person.hod,'nhom_A')"
                @input="e=>setNhomRX(person.hod,'nhom_A',e.target.value)" placeholder="Nhận xét nhóm HOD"/>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>

  <!-- NHÓM B -->
  <div class="pc-group">
    <div class="pc-group-title group-b">Nhóm B – Hiệu quả &amp; Năng lực công việc (50%) · tối đa 35đ</div>
    <div class="pc-table-wrap">
      <table class="pc-table">
        <thead>
          <tr>
            <th style="width:42px">STT</th>
            <th style="min-width:160px">Tiêu chí</th>
            <th class="th-nv" style="width:70px">NV</th>
            <th class="th-hod" style="width:70px">HOD</th>
            <th class="th-nv" style="width:120px">Nhận xét NV</th>
            <th class="th-hod" style="width:120px">Nhận xét HOD</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="stt in TC_B" :key="stt" class="pc-row">
            <td class="td-stt">{{ stt }}</td>
            <td class="td-name">{{ tcName(person.hod || person.tu_danh_gia, 'nhom_B', stt) }}</td>
            <td class="td-score td-nv">
              <input class="score-input" type="number" min="1" max="5"
                :value="score(person.tu_danh_gia, 'nhom_B', stt)"
                @input="e => setScore(person.tu_danh_gia, 'nhom_B', stt, e.target.value)"/>
            </td>
            <td class="td-score td-hod">
              <input class="score-input" type="number" min="1" max="5"
                :value="score(person.hod, 'nhom_B', stt)"
                @input="e => setScore(person.hod, 'nhom_B', stt, e.target.value)"/>
            </td>
            <td class="td-note td-nv">
              <input class="note-input"
                :value="tcNote(person.tu_danh_gia, 'nhom_B', stt)"
                @input="e => setTcNote(person.tu_danh_gia, 'nhom_B', stt, e.target.value)"/>
            </td>
            <td class="td-note td-hod">
              <input class="note-input"
                :value="tcNote(person.hod, 'nhom_B', stt)"
                @input="e => setTcNote(person.hod, 'nhom_B', stt, e.target.value)"/>
            </td>
          </tr>
          <tr class="total-row">
            <td colspan="2" class="total-label">Tổng nhóm B (thô / quy đổi)</td>
            <td class="td-nv">
              <input class="score-input" :value="nhomTot(person.tu_danh_gia,'nhom_B')"
                @input="e=>setNhomTot(person.tu_danh_gia,'nhom_B',e.target.value)"/>
              <span class="sep">/</span>
              <input class="score-input" :value="nhomQD(person.tu_danh_gia,'nhom_B')"
                @input="e=>setNhomQD(person.tu_danh_gia,'nhom_B',e.target.value)"/>
            </td>
            <td class="td-hod">
              <input class="score-input" :value="nhomTot(person.hod,'nhom_B')"
                @input="e=>setNhomTot(person.hod,'nhom_B',e.target.value)"/>
              <span class="sep">/</span>
              <input class="score-input" :value="nhomQD(person.hod,'nhom_B')"
                @input="e=>setNhomQD(person.hod,'nhom_B',e.target.value)"/>
            </td>
            <td class="td-nv">
              <input class="note-input" :value="nhomRX(person.tu_danh_gia,'nhom_B')"
                @input="e=>setNhomRX(person.tu_danh_gia,'nhom_B',e.target.value)" placeholder="Nhận xét nhóm NV"/>
            </td>
            <td class="td-hod">
              <input class="note-input" :value="nhomRX(person.hod,'nhom_B')"
                @input="e=>setNhomRX(person.hod,'nhom_B',e.target.value)" placeholder="Nhận xét nhóm HOD"/>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>

  <!-- NHÓM C -->
  <div class="pc-group">
    <div class="pc-group-title group-c">Nhóm C – Tiềm năng &amp; Phù hợp tổ chức (20%) · NV /15đ · HOD /20đ</div>
    <div class="pc-table-wrap">
      <table class="pc-table">
        <thead>
          <tr>
            <th style="width:42px">STT</th>
            <th style="min-width:160px">Tiêu chí</th>
            <th class="th-nv" style="width:70px">NV (C1-C3)</th>
            <th class="th-hod" style="width:70px">HOD (C1-C4)</th>
            <th class="th-nv" style="width:120px">Nhận xét NV</th>
            <th class="th-hod" style="width:120px">Nhận xét HOD</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="stt in TC_C_HOD" :key="stt" class="pc-row"
            :class="{ 'hod-only': !TC_C_NV.includes(stt) }">
            <td class="td-stt">{{ stt }}</td>
            <td class="td-name">{{ tcName(person.hod || person.tu_danh_gia, 'nhom_C', stt) }}</td>
            <td class="td-score td-nv">
              <span v-if="!TC_C_NV.includes(stt)" class="na-cell">HOD only</span>
              <input v-else class="score-input" type="number" min="1" max="5"
                :value="score(person.tu_danh_gia, 'nhom_C', stt)"
                @input="e => setScore(person.tu_danh_gia, 'nhom_C', stt, e.target.value)"/>
            </td>
            <td class="td-score td-hod">
              <input class="score-input" type="number" min="1" max="5"
                :value="score(person.hod, 'nhom_C', stt)"
                @input="e => setScore(person.hod, 'nhom_C', stt, e.target.value)"/>
            </td>
            <td class="td-note td-nv">
              <span v-if="!TC_C_NV.includes(stt)"></span>
              <input v-else class="note-input"
                :value="tcNote(person.tu_danh_gia, 'nhom_C', stt)"
                @input="e => setTcNote(person.tu_danh_gia, 'nhom_C', stt, e.target.value)"/>
            </td>
            <td class="td-note td-hod">
              <input class="note-input"
                :value="tcNote(person.hod, 'nhom_C', stt)"
                @input="e => setTcNote(person.hod, 'nhom_C', stt, e.target.value)"/>
            </td>
          </tr>
          <tr class="total-row">
            <td colspan="2" class="total-label">Tổng nhóm C (thô / quy đổi)</td>
            <td class="td-nv">
              <input class="score-input" :value="nhomTot(person.tu_danh_gia,'nhom_C')"
                @input="e=>setNhomTot(person.tu_danh_gia,'nhom_C',e.target.value)"/>
              <span class="sep">/</span>
              <input class="score-input" :value="nhomQD(person.tu_danh_gia,'nhom_C')"
                @input="e=>setNhomQD(person.tu_danh_gia,'nhom_C',e.target.value)"/>
            </td>
            <td class="td-hod">
              <input class="score-input" :value="nhomTot(person.hod,'nhom_C')"
                @input="e=>setNhomTot(person.hod,'nhom_C',e.target.value)"/>
              <span class="sep">/</span>
              <input class="score-input" :value="nhomQD(person.hod,'nhom_C')"
                @input="e=>setNhomQD(person.hod,'nhom_C',e.target.value)"/>
            </td>
            <td class="td-nv">
              <input class="note-input" :value="nhomRX(person.tu_danh_gia,'nhom_C')"
                @input="e=>setNhomRX(person.tu_danh_gia,'nhom_C',e.target.value)" placeholder="Nhận xét nhóm NV"/>
            </td>
            <td class="td-hod">
              <input class="note-input" :value="nhomRX(person.hod,'nhom_C')"
                @input="e=>setNhomRX(person.hod,'nhom_C',e.target.value)" placeholder="Nhận xét nhóm HOD"/>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>

  <!-- Kết quả & Đề xuất -->
  <div class="pc-group">
    <div class="pc-group-title group-kq">Kết quả &amp; Đề xuất</div>
    <div class="pc-kq-grid">
      <div class="kq-col nv-col">
        <div class="kq-col-title">NV tự đánh giá</div>
        <label class="kq-label">Nguyện vọng NV</label>
        <textarea class="kq-ta"
          :value="person.tu_danh_gia?.ket_qua_va_de_xuat?.nguyen_vong_nhan_vien || ''"
          @input="e => { if(person.tu_danh_gia?.ket_qua_va_de_xuat) person.tu_danh_gia.ket_qua_va_de_xuat.nguyen_vong_nhan_vien=e.target.value; emit('dirty') }"/>
        <label class="kq-label">KH cải thiện</label>
        <textarea class="kq-ta"
          :value="person.tu_danh_gia?.ket_qua_va_de_xuat?.ke_hoach_cai_thien || ''"
          @input="e => { if(person.tu_danh_gia?.ket_qua_va_de_xuat) person.tu_danh_gia.ket_qua_va_de_xuat.ke_hoach_cai_thien=e.target.value; emit('dirty') }"/>
      </div>
      <div class="kq-col hod-col">
        <div class="kq-col-title">HOD đánh giá</div>
        <label class="kq-label">Nhận xét HOD</label>
        <textarea class="kq-ta"
          :value="person.hod?.ket_qua_va_de_xuat?.nhan_xet_hod || ''"
          @input="e => { if(person.hod?.ket_qua_va_de_xuat) person.hod.ket_qua_va_de_xuat.nhan_xet_hod=e.target.value; emit('dirty') }"/>
        <label class="kq-label">Đề xuất bố trí</label>
        <textarea class="kq-ta"
          :value="person.hod?.ket_qua_va_de_xuat?.de_xuat_bo_tri || ''"
          @input="e => { if(person.hod?.ket_qua_va_de_xuat) person.hod.ket_qua_va_de_xuat.de_xuat_bo_tri=e.target.value; emit('dirty') }"/>
        <label class="kq-label">KH cải thiện</label>
        <textarea class="kq-ta"
          :value="person.hod?.ket_qua_va_de_xuat?.ke_hoach_cai_thien || ''"
          @input="e => { if(person.hod?.ket_qua_va_de_xuat) person.hod.ket_qua_va_de_xuat.ke_hoach_cai_thien=e.target.value; emit('dirty') }"/>
      </div>
    </div>
  </div>

  <!-- Phần II–V: Kỷ luật / Đào tạo / Hoạt động / Báo cáo ngày -->
  <div v-for="sec in SECTIONS" :key="sec.id" class="pc-group">
    <div class="pc-group-title group-hr">{{ sec.title }}</div>
    <div class="pc-table-wrap">
      <table class="pc-table">
        <thead>
          <tr>
            <th style="width:38px">STT</th>
            <th>Nội dung</th>
            <th class="th-nv" style="width:100px">Kết quả<br>tự báo cáo</th>
            <th class="th-hr" style="width:100px">Đã được<br>HR xác nhận</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="f in sec.fields" :key="f.stt" class="pc-row">
            <td class="td-stt">{{ f.stt }}</td>
            <td class="td-name">{{ f.noi_dung }}</td>
            <td class="td-score td-nv">
              <input class="score-input" type="number" min="0"
                :value="nvTuBaoCao(person.tu_danh_gia, sec.id, f.stt)"
                @input="e => setNvTuBaoCao(person.tu_danh_gia, sec.id, f.stt, e.target.value)"/>
            </td>
            <td class="td-score td-hr">
              <input class="score-input" type="number" min="0"
                :value="person.hr_data?.[f.key] ?? ''"
                @input="e => { if (!person.hr_data) person.hr_data = {}; person.hr_data[f.key] = e.target.value === '' ? null : parseInt(e.target.value); emit('dirty') }"/>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>

  <!-- AI Overview -->
  <div v-if="overview" class="pc-group pc-ai-group">
    <div class="pc-group-title group-ai">🤖 Phân tích AI</div>
    <div class="pc-ai-grid">
      <div class="ai-item">
        <div class="ai-item-label">Nhận xét chung</div>
        <div class="ai-item-val">{{ overview.nhan_xet_chung || '—' }}</div>
      </div>
      <div class="ai-item">
        <div class="ai-item-label">Sự tương đồng đánh giá HOD và nhân viên</div>
        <div class="ai-item-val">{{ overview.lech_diem || '—' }}</div>
      </div>
      <div class="ai-item">
        <div class="ai-item-label">Điểm vs Đề xuất</div>
        <div class="ai-item-val">{{ overview.diem_vs_de_xuat || '—' }}</div>
      </div>
      <div class="ai-item">
        <div class="ai-item-label">Ưu tiên cải thiện</div>
        <div class="ai-item-val">{{ overview.uu_tien_cai_thien || '—' }}</div>
      </div>
    </div>
  </div>
  <div v-else class="pc-ai-placeholder">
    🤖 Chưa có phân tích AI — bấm "Phân tích AI" ở thanh bên trái sau khi chỉnh sửa xong.
  </div>
</div>
</template>

<script setup>
defineProps(['person', 'idx', 'overview'])
const emit = defineEmits(['dirty'])

const SECTIONS = [
  { id: 'ky_luat', title: 'II. Ý THỨC KỶ LUẬT & TUÂN THỦ', fields: [
    { stt: 1, key: 'di_lam_tre',                noi_dung: 'Số lần đi làm trễ' },
    { stt: 2, key: 've_som',                     noi_dung: 'Số lần về sớm' },
    { stt: 3, key: 'nghi_khong_phep',            noi_dung: 'Số ngày nghỉ không phép' },
    { stt: 4, key: 'sang_t7_vang_khong_phep',    noi_dung: 'Số buổi sáng Thứ Bảy vắng mặt không phép' },
    { stt: 5, key: 'nhac_nho_vi_pham',           noi_dung: 'Số lần bị nhắc nhở vi phạm nội quy' },
    { stt: 6, key: 'ban_giai_trinh',             noi_dung: 'Số bản giải trình / kiểm điểm / cam kết đã ký' },
    { stt: 7, key: 'quyet_dinh_ky_luat',         noi_dung: 'Số quyết định kỷ luật đã nhận (nếu có)' },
  ]},
  { id: 'dao_tao', title: 'III. THAM GIA ĐÀO TẠO & PHÁT TRIỂN', fields: [
    { stt: 1, key: 'tong_chuong_trinh_dt',       noi_dung: 'Tổng số chương trình đào tạo Công ty tổ chức trong kỳ' },
    { stt: 2, key: 'tham_gia_dt',                noi_dung: 'Số chương trình đào tạo đã tham gia' },
    { stt: 3, key: 'vang_dt_co_ly_do',           noi_dung: 'Số chương đào tạo vắng mặt (có lý do chính đáng và được cấp thẩm quyền phê duyệt)' },
    { stt: 4, key: 'vang_dt_khong_ly_do',        noi_dung: 'Số chương trình đào tạo vắng mặt không lý do' },
    { stt: 5, key: 'giang_day_noi_bo',           noi_dung: 'Số chương trình đào tạo nội bộ tham gia giảng dạy / chia sẻ' },
  ]},
  { id: 'hoat_dong', title: 'IV. THAM GIA HOẠT ĐỘNG TẬP THỂ & QUY ĐỊNH TRUYỀN THÔNG', fields: [
    { stt: 1, key: 'tong_su_kien',               noi_dung: 'Tổng số sự kiện Công ty tổ chức trong kỳ' },
    { stt: 2, key: 'tham_gia_su_kien',           noi_dung: 'Số sự kiện đã tham gia' },
    { stt: 3, key: 'vang_sk_co_ly_do',           noi_dung: 'Số sự kiện vắng mặt có lý do chính đáng và được cấp có thẩm quyền phê duyệt' },
    { stt: 4, key: 'vang_sk_khong_ly_do',        noi_dung: 'Số sự kiện vắng mặt không lý do' },
    { stt: 5, key: 'tuan_khong_like_share',      noi_dung: 'Số tuần không thực hiện like / share theo quy định' },
    { stt: 6, key: 'tong_luot_thieu_like_share', noi_dung: 'Tổng số lượt like / share còn thiếu (nếu có)' },
  ]},
  { id: 'bao_cao_ngay', title: 'V. BÁO CÁO NGÀY', fields: [
    { stt: 1, key: 'tong_bao_cao_ngay',          noi_dung: 'Tổng số báo cáo ngày phải thực hiện trong kỳ' },
    { stt: 2, key: 'bao_cao_dung_han',           noi_dung: 'Số báo cáo ngày đã thực hiện đúng hạn' },
    { stt: 3, key: 'bao_cao_tre_han',            noi_dung: 'Số báo cáo ngày trễ hạn' },
    { stt: 4, key: 'bao_cao_khong_thuc_hien',    noi_dung: 'Số báo cáo ngày không thực hiện' },
  ]},
]

const TC_A = ['A1','A2','A3','A4','A5']
const TC_B = ['B1','B2','B3','B4','B5','B6','B7']
const TC_C_NV  = ['C1','C2','C3']
const TC_C_HOD = ['C1','C2','C3','C4']

function score(d, nhom, stt) {
  return (d?.[nhom]?.tieu_chi || []).find(t => t.stt === stt)?.diem ?? null
}
function setScore(d, nhom, stt, val) {
  if (!d?.[nhom]) return
  const tc = (d[nhom].tieu_chi || []).find(t => t.stt === stt)
  if (tc) { tc.diem = val === '' ? null : parseInt(val) || null; emit('dirty') }
}
function tcNote(d, nhom, stt) {
  return (d?.[nhom]?.tieu_chi || []).find(t => t.stt === stt)?.nhan_xet || ''
}
function setTcNote(d, nhom, stt, val) {
  if (!d?.[nhom]) return
  const tc = (d[nhom].tieu_chi || []).find(t => t.stt === stt)
  if (tc) { tc.nhan_xet = val; emit('dirty') }
}
function nhomTot(d, nhom) { return d?.[nhom]?.tong_diem_tho ?? '' }
function nhomQD(d, nhom)  { return d?.[nhom]?.diem_quy_doi ?? '' }
function nhomRX(d, nhom)  { return d?.[nhom]?.nhan_xet_nhom ?? '' }
// NV tự báo cáo (sections II–V từ OCR) — nhận nv = person.tu_danh_gia
function nvTuBaoCao(nv, secId, stt) {
  const arr = nv?.[secId]
  if (!Array.isArray(arr)) return ''
  return arr.find(r => r.stt === stt)?.tu_bao_cao ?? ''
}
function setNvTuBaoCao(nv, secId, stt, val) {
  if (!nv) return
  if (!Array.isArray(nv[secId])) nv[secId] = []
  let row = nv[secId].find(r => r.stt === stt)
  if (!row) { row = { stt }; nv[secId].push(row) }
  row.tu_bao_cao = val === '' ? null : parseInt(val)
  emit('dirty')
}

function setNhomTot(d, nhom, val) { if (d?.[nhom]) { d[nhom].tong_diem_tho = val; emit('dirty') } }
function setNhomQD(d, nhom, val)  { if (d?.[nhom]) { d[nhom].diem_quy_doi = val; emit('dirty') } }
function setNhomRX(d, nhom, val)  { if (d?.[nhom]) { d[nhom].nhan_xet_nhom = val; emit('dirty') } }
function tot100(d) { return d?.tong_hop?.tong_diem_100 ?? '' }
function xl(d)     { return d?.tong_hop?.xep_loai ?? '' }
function setTot100(d, val) { if (d?.tong_hop) { d.tong_hop.tong_diem_100 = val; emit('dirty') } }
function setXl(d, val)     { if (d?.tong_hop) { d.tong_hop.xep_loai = val; emit('dirty') } }
function tcName(d, nhom, stt) {
  return (d?.[nhom]?.tieu_chi || []).find(t => t.stt === stt)?.ten || stt
}
function normXl(v) {
  if (!v) return ''
  const m = String(v).match(/[A-Ea-e]/)
  return m ? m[0].toUpperCase() : v
}
function xlBg(v) {
  return {A:'#d1fae5',B:'#dbeafe',C:'#fef9c3',D:'#fee2e2',E:'#f3f4f6'}[normXl(v)] || ''
}
</script>

<style scoped>
.pc-wrap { max-width: 1100px; }

.pc-header {
  display: flex; align-items: flex-start; justify-content: space-between; gap: 20px;
  background: white; border-radius: 14px; padding: 18px 22px; margin-bottom: 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,.06);
}
:global(body.theme-dark) .pc-header { background: #1a1a28; box-shadow: 0 2px 12px rgba(0,0,0,.3); }

.pc-name { font-size: 1.25rem; font-weight: 800; margin-bottom: 4px; }
.pc-meta { font-size: .82rem; color: #64748b; margin-bottom: 2px; }

.pc-totals { display: flex; gap: 10px; flex-shrink: 0; }
.pc-total-box { text-align: center; padding: 12px 14px; border-radius: 12px; min-width: 100px; }
.nv-box { background: #eff6ff; border: 1.5px solid #bfdbfe; }
.hod-box { background: #f0fdf4; border: 1.5px solid #bbf7d0; }
:global(body.theme-dark) .nv-box { background: rgba(59,130,246,.12); border-color: rgba(59,130,246,.25); }
:global(body.theme-dark) .hod-box { background: rgba(16,185,129,.12); border-color: rgba(16,185,129,.25); }
.ptb-label { font-size: .68rem; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; color: #64748b; margin-bottom: 6px; }
.ptb-score { width: 52px; padding: 4px 6px; border-radius: 6px; border: 1.5px solid #e2e8f0; background: transparent; text-align: center; font-size: 1rem; font-weight: 800; color: inherit; outline: none; }
.ptb-score:focus { border-color: #6366f1; }
.ptb-xl { display: block; margin: 5px auto 0; width: 36px; padding: 3px; border-radius: 6px; border: 1.5px solid #e2e8f0; text-align: center; font-size: .8rem; font-weight: 800; color: #1e293b; outline: none; }

.pc-group { margin-bottom: 18px; background: white; border-radius: 14px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,.06); }
:global(body.theme-dark) .pc-group { background: #1a1a28; box-shadow: 0 2px 12px rgba(0,0,0,.3); }
.pc-group-title { padding: 11px 18px; font-size: .78rem; font-weight: 800; text-transform: uppercase; letter-spacing: .06em; border-bottom: 1px solid #f1f5f9; }
:global(body.theme-dark) .pc-group-title { border-bottom-color: rgba(255,255,255,.08); }
.group-a { color: #7c3aed; background: rgba(124,58,237,.05); }
.group-b { color: #1d4ed8; background: rgba(29,78,216,.05); }
.group-c { color: #047857; background: rgba(4,120,87,.05); }
.group-kq { color: #b45309; background: rgba(180,83,9,.05); }
.group-ai { color: #92400e; background: rgba(251,191,36,.07); }
:global(body.theme-dark) .group-ai { color: #fbbf24; background: rgba(251,191,36,.06); }

.pc-table-wrap { overflow-x: auto; }
.pc-table { width: 100%; border-collapse: collapse; min-width: 560px; }

.pc-table thead th {
  padding: 7px 10px; font-size: .68rem; font-weight: 700; text-transform: uppercase;
  border-bottom: 1.5px solid #e2e8f0; text-align: center;
  background: #f8fafc; color: #374151;
}
:global(body.theme-dark) .pc-table thead th { background: #1e2030; color: #94a3b8; border-bottom-color: rgba(255,255,255,.08); }
.th-nv { background: #eff6ff !important; color: #1d4ed8 !important; }
.th-hod { background: #f0fdf4 !important; color: #065f46 !important; }
:global(body.theme-dark) .th-nv { background: rgba(59,130,246,.12) !important; }
:global(body.theme-dark) .th-hod { background: rgba(16,185,129,.12) !important; }

.pc-row td { border-bottom: 1px solid #f1f5f9; vertical-align: middle; }
:global(body.theme-dark) .pc-row td { border-bottom-color: rgba(255,255,255,.05); }
.pc-row:hover td { background: rgba(99,102,241,.02); }
.hod-only td { background: rgba(16,185,129,.03); }

.total-row td { background: #fafafa; font-weight: 700; }
:global(body.theme-dark) .total-row td { background: rgba(255,255,255,.03); }
.total-label { padding: 8px 10px; font-size: .8rem; font-weight: 700; color: #374151; text-align: center; }
:global(body.theme-dark) .total-label { color: #94a3b8; }

.td-stt { width: 42px; text-align: center; font-weight: 700; font-size: .8rem; color: #6366f1; padding: 8px; }
.td-name { padding: 7px 10px; font-size: .8rem; color: inherit; }
.td-score { text-align: center; padding: 6px 8px; }
.td-nv { background: rgba(239,246,255,.4); }
.td-hod { background: rgba(240,253,244,.4); }
:global(body.theme-dark) .td-nv { background: rgba(59,130,246,.05); }
:global(body.theme-dark) .td-hod { background: rgba(16,185,129,.05); }
.td-note { padding: 4px 6px; }

.score-input {
  width: 44px; height: 28px; border: 1.5px solid #e2e8f0; border-radius: 6px;
  text-align: center; font-size: .88rem; font-weight: 700; background: transparent;
  color: inherit; outline: none; transition: border-color .15s;
}
.score-input:focus { border-color: #6366f1; }
:global(body.theme-dark) .score-input { border-color: rgba(255,255,255,.1); }

.note-input {
  width: 100%; border: none; border-bottom: 1px solid rgba(99,102,241,.2); background: transparent;
  font-size: .75rem; color: inherit; outline: none; padding: 3px 4px;
}
.note-input:focus { border-bottom-color: #6366f1; }

.sep { color: #94a3b8; margin: 0 2px; font-size: .8rem; }
.na-cell { font-size: .68rem; color: #94a3b8; font-style: italic; }

/* KQ */
.pc-kq-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0; }
.kq-col { padding: 14px 18px; }
.nv-col { border-right: 1px solid #f1f5f9; background: rgba(239,246,255,.3); }
.hod-col { background: rgba(240,253,244,.3); }
:global(body.theme-dark) .nv-col { background: rgba(59,130,246,.04); border-right-color: rgba(255,255,255,.06); }
:global(body.theme-dark) .hod-col { background: rgba(16,185,129,.04); }
.kq-col-title { font-size: .72rem; font-weight: 800; text-transform: uppercase; letter-spacing: .06em; margin-bottom: 10px; color: #6366f1; }
.kq-label { display: block; font-size: .7rem; font-weight: 700; color: #64748b; margin-bottom: 3px; margin-top: 8px; }
.kq-ta {
  width: 100%; min-height: 52px; padding: 6px 8px; border-radius: 7px;
  border: 1px solid #e2e8f0; background: transparent; font-size: .78rem;
  color: inherit; outline: none; resize: vertical; font-family: inherit;
}
:global(body.theme-dark) .kq-ta { border-color: rgba(255,255,255,.1); }
.kq-ta:focus { border-color: #6366f1; }

/* AI section */
.pc-ai-group { border: 1.5px solid rgba(251,191,36,.3); }
.pc-ai-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0; }
.ai-item { padding: 12px 18px; border-right: 1px solid #f1f5f9; border-bottom: 1px solid #f1f5f9; }
:global(body.theme-dark) .ai-item { border-right-color: rgba(255,255,255,.06); border-bottom-color: rgba(255,255,255,.06); }
.ai-item:nth-child(even) { border-right: none; }
.ai-item:nth-child(n+3) { border-bottom: none; }
.ai-item-label { font-size: .68rem; font-weight: 800; text-transform: uppercase; letter-spacing: .05em; color: #92400e; margin-bottom: 5px; }
:global(body.theme-dark) .ai-item-label { color: #fbbf24; }
.ai-item-val { font-size: .82rem; line-height: 1.6; color: inherit; }

.pc-ai-placeholder {
  margin-bottom: 18px; padding: 14px 18px; border-radius: 14px;
  border: 1.5px dashed rgba(251,191,36,.25); background: rgba(251,191,36,.04);
  font-size: .8rem; color: #64748b; text-align: center; line-height: 1.6;
}
.group-hr { background: linear-gradient(90deg,#1e40af,#2563eb); color:#fff; }
.th-hr { background: rgba(30,64,175,.15) !important; color: #1e40af !important; }
.td-hr { background: rgba(30,64,175,.06); }
.hr-grp-row .hr-grp-cell {
  background: rgba(30,64,175,.08); color: #1e40af; font-size: .72rem;
  font-weight: 700; text-transform: uppercase; letter-spacing: .04em;
  padding: 5px 10px;
}
</style>
