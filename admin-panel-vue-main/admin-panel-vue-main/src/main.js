import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import router from './router'
// Инициализация темы до монтирования (применяет сохранённую тёмную/светлую тему)
import './composables/useTheme'

const bootstrap = async () => {
  const app = createApp(App)
  app.use(router)
  app.mount('#app')
}

bootstrap()
