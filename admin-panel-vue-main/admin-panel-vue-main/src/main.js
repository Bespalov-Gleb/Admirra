import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import router from './router'
// Инициализация темы до монтирования (применяет сохранённую тёмную/светлую тему)
import './composables/useTheme'
import { captureYclid } from './utils/metrika'

// Ловим yclid из URL первого захода (рекламный клик Директа) — для серверных конверсий
captureYclid()

const bootstrap = async () => {
  const app = createApp(App)
  app.use(router)
  app.mount('#app')
}

bootstrap()
