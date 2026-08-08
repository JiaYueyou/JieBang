import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './assets/styles/global.scss'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElementPlus, { size: 'default' })

for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// 启动 MSW（仅开发环境且未连接真实后端时）
async function startApp() {
  if (import.meta.env.DEV && !import.meta.env.VITE_API_BASE_URL) {
    const { worker } = await import('./mock/browser')
    await worker.start({
      onUnhandledRequest(req) {
        if (req.url.includes('/api/')) {
          console.warn('[MSW] 未处理的 API 请求:', req.url)
        }
        // 其他请求（导航、静态资源等）直接放行
      },
    })
  }
  app.mount('#app')
}

startApp()
