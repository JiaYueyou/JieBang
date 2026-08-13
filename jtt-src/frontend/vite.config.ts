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
      '/api/assistant': {
        target: 'http://localhost:8003',
        changeOrigin: true,
      },
      '/api/tailor/optimize-phrase': {
        target: 'http://localhost:8003',
        changeOrigin: true,
      },
      '/api/learning/assistant': {
        target: 'http://localhost:8003',
        changeOrigin: true,
      },
      '/api/v1/assistant': {
        target: 'http://localhost:8003',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/v1/, '/api'),
      },
      '/api': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,

      },
    },
  },
})
