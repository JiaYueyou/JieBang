import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  server: {
    proxy: {
      // AI 请求 → AI 服务（rewrite 去掉 v1，AI 服务路由不带 v1）
      '/api/v1/learning/assistant': {
        target: 'http://localhost:8003',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/v1/, '/api'),
      },
      '/api/v1/assistant': {
        target: 'http://localhost:8003',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/v1/, '/api'),
      },
      '/api/v1/tailor/optimize-phrase': {
        target: 'http://localhost:8003',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/v1/, '/api'),
      },
      // 数据请求 → 后端 8000（baseURL 和后端路由都含 v1，无需 rewrite）
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
