<template>
  <div class="portal">
    <div class="portal-bg">
      <div class="portal-orb orb-1"></div>
      <div class="portal-orb orb-2"></div>
    </div>

    <!-- Theme & Lang Toggles -->
    <div class="top-toggles">
      <button @click="toggleTheme" class="toggle-btn" :title="t(store.theme==='dark'?'light_mode':'dark_mode')">
        {{ store.theme==='dark' ? '☀️' : '🌙' }}
      </button>
      <button @click="toggleLang" class="toggle-btn" :title="t(store.lang==='vi'?'english':'vietnamese')">
        {{ store.lang==='vi' ? 'EN' : 'VI' }}
      </button>
    </div>

    <div class="portal-content">
      <div class="portal-header">
        <div class="portal-logo">
          <svg width="40" height="40" viewBox="0 0 48 48" fill="none">
            <rect width="48" height="48" rx="14" fill="url(#pg)" />
            <text x="24" y="32" text-anchor="middle" font-size="22">⚡</text>
            <defs><linearGradient id="pg" x1="0" y1="0" x2="48" y2="48">
              <stop stop-color="#6366f1"/><stop offset="1" stop-color="#8b5cf6"/>
            </linearGradient></defs>
          </svg>
        </div>
        <h1 class="portal-title">{{ t('portal_title') }}</h1>
        <p class="portal-subtitle">{{ t('portal_sub') }}</p>
      </div>

      <div class="portal-cards">
        <router-link to="/thu-viec" class="pcard">
          <div class="pcard-glow glow-indigo"></div>
          <div class="pcard-inner">
            <div class="pcard-icon">🎯</div>
            <div class="pcard-body">
              <h3>{{ t('thuviec_title') }}</h3>
              <p>{{ t('thuviec_desc') }}</p>
            </div>
            <div class="pcard-footer">
              <span>{{ t('open_system') }}</span>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14m-7-7l7 7-7 7"/></svg>
            </div>
          </div>
        </router-link>

        <router-link to="/tai-ky" class="pcard">
          <div class="pcard-glow glow-violet"></div>
          <div class="pcard-inner">
            <div class="pcard-icon">📝</div>
            <div class="pcard-body">
              <h3>{{ t('taiky_title') }}</h3>
              <p>{{ t('taiky_desc') }}</p>
            </div>
            <div class="pcard-footer">
              <span>{{ t('open_system') }}</span>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14m-7-7l7 7-7 7"/></svg>
            </div>
          </div>
        </router-link>

        <router-link to="/bao-cao" class="pcard">
          <div class="pcard-glow glow-emerald"></div>
          <div class="pcard-inner">
            <div class="pcard-icon">👥</div>
            <div class="pcard-body">
              <h3>{{ t('baocao_title') }}</h3>
              <p>{{ t('baocao_desc') }}</p>
            </div>
            <div class="pcard-footer">
              <span>{{ t('open_system') }}</span>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14m-7-7l7 7-7 7"/></svg>
            </div>
          </div>
        </router-link>

        <router-link to="/de-xuat" class="pcard">
          <div class="pcard-glow glow-teal"></div>
          <div class="pcard-inner">
            <div class="pcard-icon">📋</div>
            <div class="pcard-body">
              <h3>{{ t('dexuat_title') }}</h3>
              <p>{{ t('dexuat_desc') }}</p>
            </div>
            <div class="pcard-footer">
              <span>{{ t('open_system') }}</span>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14m-7-7l7 7-7 7"/></svg>
            </div>
          </div>
        </router-link>
      </div>

      <div class="portal-footer">
        <span>CNB 2AS · CT Group · {{ new Date().getFullYear() }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { store, t } from '../store'

function toggleTheme() {
  store.theme = store.theme === 'dark' ? 'light' : 'dark'
}
function toggleLang() {
  store.lang = store.lang === 'vi' ? 'en' : 'vi'
}
</script>

<style scoped>
.portal { position: relative; height: 100vh; display: flex; align-items: center; justify-content: center; overflow: hidden; }
.portal-bg { position: absolute; inset: 0; pointer-events: none }
.portal-orb { position: absolute; border-radius: 50%; filter: blur(120px); opacity: .25 }
.orb-1 { width: 500px; height: 500px; background: #6366f1; top: -100px; left: -100px; animation: float 8s ease-in-out infinite }
.orb-2 { width: 400px; height: 400px; background: #8b5cf6; bottom: -80px; right: -80px; animation: float 10s ease-in-out infinite reverse }
@keyframes float { 0%,100%{transform:translate(0)} 50%{transform:translate(30px,20px)} }

.top-toggles { position: absolute; top: 20px; right: 24px; z-index: 10; display: flex; gap: 10px; }
.toggle-btn { width: 36px; height: 36px; border-radius: 50%; border: 1px solid rgba(99,102,241,.3); background: rgba(99,102,241,.1); color: inherit; cursor: pointer; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: .85rem; transition: all .2s; backdrop-filter: blur(4px); }
.toggle-btn:hover { background: rgba(99,102,241,.2); transform: scale(1.05); }

.portal-content { position: relative; z-index: 1; max-width: 780px; width: 100%; padding: 0 24px }
.portal-header { text-align: center; margin-bottom: 24px }

.portal-logo { display: flex; justify-content: center; margin-bottom: 10px }
.portal-title { font-size: 1.55rem; font-weight: 800; letter-spacing: -.02em }
.portal-subtitle { font-size: .88rem; color: #94a3b8; margin-top: 5px }

.portal-cards { display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px; }

.pcard {
  position: relative; text-decoration: none; color: inherit;
  border-radius: 16px; overflow: hidden; cursor: pointer;
  transition: transform .3s ease, box-shadow .3s ease;
}
.pcard:hover { transform: translateY(-4px); box-shadow: 0 16px 32px rgba(99,102,241,.15) }
.pcard-glow { position: absolute; inset: 0; opacity: 0; transition: opacity .4s }
.pcard:hover .pcard-glow { opacity: 1 }
.glow-indigo { background: linear-gradient(135deg, rgba(99,102,241,.08), rgba(139,92,246,.04)) }
.glow-violet { background: linear-gradient(135deg, rgba(139,92,246,.08), rgba(168,85,247,.04)) }
.glow-teal   { background: linear-gradient(135deg, rgba(20,184,166,.08), rgba(99,102,241,.04)) }
.glow-emerald { background: linear-gradient(135deg, rgba(16,185,129,.08), rgba(99,102,241,.04)) }

.pcard-inner {
  position: relative; z-index: 1;
  backdrop-filter: blur(16px);
  border: 1px solid transparent;
  border-radius: 16px; padding: 20px 22px;
  display: flex; flex-direction: column; height: 100%;
}

.pcard-icon { font-size: 26px; margin-bottom: 12px; width: 50px; height: 50px; display: flex; align-items: center; justify-content: center; background: rgba(99,102,241,.1); border-radius: 13px }
.pcard-body { flex-grow: 1 }
.pcard-body h3 { font-size: .97rem; font-weight: 700; margin-bottom: 6px }
.pcard-body p { font-size: .81rem; line-height: 1.55; }
.pcard-footer { margin-top: 14px; display: flex; align-items: center; justify-content: space-between; color: #818cf8; font-weight: 600; font-size: .81rem }
.pcard:hover .pcard-footer svg { transform: translateX(4px) }
.pcard-footer svg { transition: transform .3s }

.portal-footer { text-align: center; margin-top: 20px; font-size: .75rem; color: #475569 }

@media (max-width: 1100px) {
  .portal-cards { grid-template-columns: repeat(2, 1fr) }
}
@media (max-width: 600px) {
  .portal-cards { grid-template-columns: 1fr }
  .portal-title { font-size: 1.5rem }
}
</style>
