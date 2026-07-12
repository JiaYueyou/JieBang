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

// MSW 仅在未配置 VITE_API_BASE_URL 时启用（连真实后端时跳过 mock）
async function startMock() {
  if (import.meta.env.DEV && !import.meta.env.VITE_API_BASE_URL) {
    const { worker } = await import('./mock/browser')
    return worker.start({ onUnhandledRequest: 'bypass' })
  }
}

startMock().then(() => {
  app.mount('#app')
})
