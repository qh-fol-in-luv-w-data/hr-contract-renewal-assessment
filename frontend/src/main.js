import { createApp } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import App from './App.vue'
import Portal from './pages/Portal.vue'
import ThuViec from './pages/ThuViec.vue'
import TaiKy from './pages/TaiKy.vue'
import ScanCombined from './pages/ScanCombined.vue'

const routes = [
  { path: '/', component: Portal },
  { path: '/portal', component: Portal },
  { path: '/thu-viec', component: ThuViec },
  { path: '/tai-ky', component: TaiKy },
  { path: '/scan-phieu', component: ScanCombined },
  { path: '/scan-sxkd', component: ScanCombined },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

const app = createApp(App)
app.use(router)
app.mount('#app')
