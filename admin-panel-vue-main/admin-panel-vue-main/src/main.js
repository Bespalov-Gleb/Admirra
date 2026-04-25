import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import router from './router'
// Инициализация темы до монтирования (применяет сохранённую тёмную/светлую тему)
import './composables/useTheme'
import { useAuth } from './composables/useAuth'

const app = createApp(App)
app.use(router)

// Важно: монтируем приложение только после готовности роутера и проверки сессии,
// чтобы избежать краткого рендера "старого" layout при перезагрузке.
await router.isReady()
const { checkAuth } = useAuth()
await checkAuth()

app.mount('#app')
