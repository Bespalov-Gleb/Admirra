import { ref, watch } from 'vue'

// Инициализируем тему из localStorage
const savedTheme = localStorage.getItem('darkMode')
const isDarkMode = ref(savedTheme === 'true')

// Применяем тему к документу
const applyTheme = () => {
  if (typeof document !== 'undefined') {
    if (isDarkMode.value) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }
}

// Применяем тему при загрузке
if (typeof document !== 'undefined') {
  applyTheme()
}

export function useTheme() {
  // Переключаем тему
  const toggleTheme = () => {
    isDarkMode.value = !isDarkMode.value
    localStorage.setItem('darkMode', isDarkMode.value.toString())
    applyTheme()
  }

  // Следим за изменениями темы
  watch(isDarkMode, () => {
    applyTheme()
  })

  return {
    isDarkMode,
    toggleTheme
  }
}

