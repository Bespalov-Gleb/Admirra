import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import router from './router'
// Инициализация темы до монтирования (применяет сохранённую тёмную/светлую тему)
import './composables/useTheme'
import { useAuth } from './composables/useAuth'

const bootstrap = async () => {
  const app = createApp(App)
  app.use(router)

  try {
    // Мягкая прединициализация, чтобы уменьшить "мигание" layout при refresh
    await router.isReady()
    const { checkAuth } = useAuth()
    await checkAuth()
  } catch (err) {
    // Никогда не блокируем монтирование всего приложения
    console.error('Bootstrap init error:', err)
  } finally {
    app.mount('#app')
  }
}

bootstrap()
