import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import router from './router'
// Инициализация темы до монтирования (применяет сохранённую тёмную/светлую тему)
import './composables/useTheme'

createApp(App).use(router).mount('#app')
