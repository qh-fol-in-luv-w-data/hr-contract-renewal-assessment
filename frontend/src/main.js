import { createApp } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import App from './App.vue'
import Portal from './pages/Portal.vue'
import ThuViec from './pages/ThuViec.vue'
import TaiKy from './pages/TaiKy.vue'
import ScanCombined from './pages/ScanCombined.vue'
import BaoCao from './pages/BaoCao.vue'
import { getSessionId, getCsrfToken } from './utils/session';

const originalFetch = window.fetch;
window.fetch = async (...args) => {
  let [resource, config] = args;
  config = config || {};
  config.headers = config.headers || {};

  const sid = getSessionId();
  const csrf = getCsrfToken() || (window.frappe && window.frappe.csrf_token) || '';

  if (config.headers instanceof Headers) {
    if (sid) config.headers.set('X-App-Session-Id', sid);
    if (csrf) config.headers.set('X-Frappe-CSRF-Token', csrf);
  } else {
    if (sid) config.headers['X-App-Session-Id'] = sid;
    if (csrf) config.headers['X-Frappe-CSRF-Token'] = csrf;
  }

  return originalFetch(resource, config);
};

const routes = [
  { path: '/', component: Portal },
  { path: '/portal', component: Portal },
  { path: '/thu-viec', component: ThuViec },
  { path: '/tai-ky', component: TaiKy },
  { path: '/scan-phieu', component: ScanCombined },
  { path: '/scan-sxkd', component: ScanCombined },
  { path: '/bao-cao', component: BaoCao },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

const app = createApp(App)
app.use(router)
app.mount('#app')
