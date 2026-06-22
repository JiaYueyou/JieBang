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

// MSW will be conditionally started in dev
async function startMock() {
  if (import.meta.env.DEV) {
    const { worker } = await import('./mock/browser')
    return worker.start({ onUnhandledRequest: 'bypass' })
  }
}

startMock().then(() => {
  app.mount('#app')
})
