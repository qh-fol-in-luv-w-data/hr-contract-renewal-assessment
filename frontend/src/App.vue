<template>
  <div v-if="authState === 'authorized'">
    <router-view />
  </div>
  <CTAccessDenied v-else-if="authState === 'denied'" />
</template>

<script setup>
import { onMounted } from 'vue';
import { store } from './store';
import { useSession, initSession } from '@/utils/session';
import CTAccessDenied from '@/components/CTAccessDenied.vue';

const { authState } = useSession();

onMounted(async () => {
  await initSession('/api/method/cnb_2as.api.get_context');
});
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0 }
html, body, #app { height: 100%; overflow: hidden }
body { font-family: 'Inter', -apple-system, sans-serif; font-size: 15px; transition: background 0.3s, color 0.3s; }

/* THEME DARK */
body.theme-dark { background: #0f0f14; color: #e2e8f0; }
body.theme-dark .portal { background: #0a0a12; }
body.theme-dark .portal-title { color: #f8fafc; }
body.theme-dark .pcard-inner { background: rgba(30,32,48,.85); border-color: rgba(99,102,241,.15); }
body.theme-dark .pcard-body h3 { color: #f1f5f9; }
body.theme-dark .pcard-body p { color: #94a3b8; }
body.theme-dark .sidebar { background: #13131a; border-right-color: rgba(99,102,241,.1); }
body.theme-dark .sb-top { border-bottom-color: rgba(255,255,255,.06); }
body.theme-dark .result-panel { background: #0f0f14; }
body.theme-dark .welcome h1 { color: #f1f5f9; }
body.theme-dark .result-card { background: rgba(30,32,48,.6); border-color: rgba(99,102,241,.1); }
body.theme-dark .sb-name { color: #f1f5f9; }
body.theme-dark .rc-body { border-top-color: rgba(255,255,255,.04); }
body.theme-dark .comp-table th { background: rgba(99,102,241,.08); color: #94a3b8; }
body.theme-dark .comp-table td { border-bottom-color: rgba(255,255,255,.04); color: #cbd5e1; }
body.theme-dark .issue-item { border-bottom-color: rgba(255,255,255,.04); }
body.theme-dark .kpi-item { border-bottom-color: rgba(255,255,255,.04); }
body.theme-dark .ev-item { border-bottom-color: rgba(255,255,255,.04); }

/* THEME LIGHT */
body.theme-light { background: #f8fafc; color: #334155; }
body.theme-light .portal { background: #f1f5f9; }
body.theme-light .portal-title { color: #0f172a; }
body.theme-light .pcard-inner { background: rgba(255,255,255,.9); border-color: rgba(99,102,241,.3); box-shadow: 0 4px 6px -1px rgba(0,0,0,.05); }
body.theme-light .pcard-body h3 { color: #1e293b; }
body.theme-light .pcard-body p { color: #475569; }
body.theme-light .sidebar { background: #ffffff; border-right-color: #e2e8f0; }
body.theme-light .sb-top { border-bottom-color: #e2e8f0; }
body.theme-light .result-panel { background: #f8fafc; }
body.theme-light .welcome h1 { color: #0f172a; }
body.theme-light .result-card { background: #ffffff; border-color: #e2e8f0; box-shadow: 0 1px 3px 0 rgba(0,0,0,.05); }
body.theme-light .sb-name { color: #0f172a; }
body.theme-light .rc-body { border-top-color: #e2e8f0; }
body.theme-light .comp-table th { background: #f1f5f9; color: #475569; }
body.theme-light .comp-table td { border-bottom-color: #e2e8f0; color: #334155; }
body.theme-light .issue-item { border-bottom-color: #e2e8f0; }
body.theme-light .kpi-item { border-bottom-color: #e2e8f0; }
body.theme-light .ev-item { border-bottom-color: #e2e8f0; }
body.theme-light .sc { background: #f1f5f9; }
body.theme-light .rc-summary { color: #334155; }
body.theme-light .rc-header:hover { background: #f8fafc; }
body.theme-light .ii-fix { color: #334155; }
body.theme-light .ki-name { color: #1e293b; }
body.theme-light .ev-text { color: #334155; }
body.theme-light .rec-body { color: #334155; }
</style>
