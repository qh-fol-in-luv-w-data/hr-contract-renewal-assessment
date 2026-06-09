import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig(({ command }) => ({
  plugins: [vue()],
  // Khi build: assets phải nằm ở /assets/cnb_2as/frontend/ để Frappe serve đúng
  // Khi dev: dùng '/' vì proxy tự handle
  base: command === 'build' ? '/assets/cnb_2as/frontend/' : '/',
  build: {
    outDir: resolve(__dirname, '../cnb_2as/public/frontend'),
    emptyOutDir: true,
  },
  server: {
    host: true,
    port: 5180,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        timeout: 180000,
        proxyTimeout: 180000,
      },
    },
  },
}))
