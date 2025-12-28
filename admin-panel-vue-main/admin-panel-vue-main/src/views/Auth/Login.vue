<template>
  <div class="min-h-screen bg-gray-100 flex items-center justify-center px-4 py-12">
    <div class="max-w-md w-full">
      <!-- Логотип и заголовок -->
      <div class="text-center mb-8">
        <div class="w-16 h-16 mx-auto mb-4 rounded-lg bg-gray-200 flex items-center justify-center">
          <UserIcon class="w-10 h-10 text-gray-600" />
        </div>
        <h1 class="text-3xl font-bold text-gray-900 mb-2">ТРАФИК АГЕНТСТВО</h1>
        <p class="text-sm text-gray-500">отчеты агентства в одном месте</p>
      </div>

      <!-- Форма -->
      <div class="bg-white rounded-lg p-6 sm:p-8">
        <!-- Переключатель входа/регистрации -->
        <div class="flex gap-2 mb-6 bg-gray-100 rounded-lg p-1">
          <button
            @click="isLogin = true"
            :class="[
              'flex-1 py-2.5 px-4 rounded-md text-sm font-medium transition-colors',
              isLogin
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            ]"
          >
            Вход
          </button>
          <button
            @click="isLogin = false"
            :class="[
              'flex-1 py-2.5 px-4 rounded-md text-sm font-medium transition-colors',
              !isLogin
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            ]"
          >
            Регистрация
          </button>
        </div>
        
        <!-- Сообщение об ошибке (Premium UI) -->
        <Transition name="fade-slide">
          <div 
            v-if="errorMessage" 
            :class="[
              'mb-6 p-4 rounded-xl flex items-start gap-3 border shadow-sm transition-all duration-300',
              'bg-red-50 border-red-100 text-red-800',
              { 'animate-shake': errorShake }
            ]"
          >
            <ExclamationCircleIcon class="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div class="flex-1 text-sm font-medium leading-relaxed">
              {{ errorMessage }}
            </div>
            <button 
              @click="errorMessage = ''" 
              class="text-red-400 hover:text-red-600 transition-colors"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </Transition>

        <!-- Форма входа -->
        <form v-if="isLogin" @submit.prevent="handleLogin" novalidate class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Email
            </label>
            <input
              v-model="loginForm.email"
              type="email"
              required
              placeholder="Введите email"
              class="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Пароль
            </label>
            <div class="relative">
              <input
                v-model="loginForm.password"
                :type="showLoginPassword ? 'text' : 'password'"
                required
                placeholder="Введите пароль"
                class="w-full px-4 py-2.5 pr-10 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              <button
                type="button"
                @click="showLoginPassword = !showLoginPassword"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
              >
                <EyeIcon v-if="!showLoginPassword" class="w-5 h-5" />
                <EyeSlashIcon v-else class="w-5 h-5" />
              </button>
            </div>
          </div>

          <div class="flex items-center justify-between">
            <label class="flex items-center">
              <input
                v-model="loginForm.remember"
                type="checkbox"
                class="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              <span class="ml-2 text-sm text-gray-600">Запомнить меня</span>
            </label>
            <a href="#" class="text-sm text-blue-600 hover:text-blue-700">
              Забыли пароль?
            </a>
          </div>

          <button
            type="submit"
            :disabled="loading"
            class="w-full py-2.5 px-4 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            <span v-if="loading" class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
            {{ loading ? 'Вход...' : 'Войти' }}
          </button>
        </form>

        <!-- Форма регистрации -->
        <form v-else @submit.prevent="handleRegister" novalidate class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Имя
            </label>
            <input
              v-model="registerForm.username"
              type="text"
              required
              placeholder="Введите имя"
              class="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Email
            </label>
            <input
              v-model="registerForm.email"
              type="email"
              required
              placeholder="Введите email"
              class="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Пароль
            </label>
            <div class="relative">
              <input
                v-model="registerForm.password"
                :type="showRegisterPassword ? 'text' : 'password'"
                required
                placeholder="Введите пароль"
                minlength="6"
                class="w-full px-4 py-2.5 pr-10 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              <button
                type="button"
                @click="showRegisterPassword = !showRegisterPassword"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
              >
                <EyeIcon v-if="!showRegisterPassword" class="w-5 h-5" />
                <EyeSlashIcon v-else class="w-5 h-5" />
              </button>
            </div>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Подтвердите пароль
            </label>
            <div class="relative">
              <input
                v-model="registerForm.confirmPassword"
                :type="showConfirmPassword ? 'text' : 'password'"
                required
                placeholder="Подтвердите пароль"
                minlength="6"
                class="w-full px-4 py-2.5 pr-10 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              <button
                type="button"
                @click="showConfirmPassword = !showConfirmPassword"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
              >
                <EyeIcon v-if="!showConfirmPassword" class="w-5 h-5" />
                <EyeSlashIcon v-else class="w-5 h-5" />
              </button>
            </div>
          </div>

          <div class="flex items-center">
            <input
              v-model="registerForm.agree"
              type="checkbox"
              required
              class="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
            <span class="ml-2 text-sm text-gray-600">
              Я согласен с <a href="#" class="text-blue-600 hover:text-blue-700">условиями использования</a>
            </span>
          </div>

          <button
            type="submit"
            :disabled="loading"
            class="w-full py-2.5 px-4 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            <span v-if="loading" class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
            {{ loading ? 'Регистрация...' : 'Зарегистрироваться' }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { UserIcon, EyeIcon, EyeSlashIcon, ExclamationCircleIcon } from '@heroicons/vue/24/outline'
import { useAuth } from '../../composables/useAuth'

const router = useRouter()
const { login, register } = useAuth()
const isLogin = ref(true)
const showLoginPassword = ref(false)
const showRegisterPassword = ref(false)
const showConfirmPassword = ref(false)
const loading = ref(false)
const errorMessage = ref('')
const errorShake = ref(false)

const triggerError = (msg) => {
  errorMessage.value = msg
  errorShake.value = true
  setTimeout(() => {
    errorShake.value = false
  }, 500)
}

const loginForm = reactive({
  email: '',
  password: '',
  remember: false
})

const registerForm = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
  agree: false
})

// Валидация Email
const isValidEmail = (email) => {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
}

const handleLogin = async () => {
  // Базовая валидация
  if (!loginForm.email) return triggerError('Пожалуйста, введите Email')
  if (!isValidEmail(loginForm.email)) return triggerError('Введите корректный Email адрес')
  if (!loginForm.password) return triggerError('Пожалуйста, введите пароль')

  loading.value = true
  errorMessage.value = ''
  
  const result = await login(loginForm.email, loginForm.password)
  
  loading.value = false
  if (result.success) {
    router.push('/dashboard/general')
  } else {
    triggerError(result.message)
  }
}

const handleRegister = async () => {
  // Валидация полей
  if (!registerForm.username) return triggerError('Введите ваше имя')
  if (!registerForm.email) return triggerError('Введите Email')
  if (!isValidEmail(registerForm.email)) return triggerError('Введите корректный Email')
  if (!registerForm.password) return triggerError('Введите пароль')
  if (registerForm.password.length < 6) return triggerError('Пароль должен быть не менее 6 символов')
  
  if (registerForm.password !== registerForm.confirmPassword) {
    triggerError('Пароли не совпадают')
    return
  }

  if (!registerForm.agree) return triggerError('Вы должны согласиться с условиями')

  loading.value = true
  errorMessage.value = ''
  
  const result = await register(registerForm.email, registerForm.password, registerForm.username)
  
  loading.value = false
  if (result.success) {
    router.push('/dashboard/general')
  } else {
    triggerError(result.message)
  }
}
</script>

<style scoped>
.animate-shake {
  animation: shake 0.5s cubic-bezier(.36,.07,.19,.97) both;
}

@keyframes shake {
  10%, 90% { transform: translate3d(-1px, 0, 0); }
  20%, 80% { transform: translate3d(2px, 0, 0); }
  30%, 50%, 70% { transform: translate3d(-4px, 0, 0); }
  40%, 60% { transform: translate3d(4px, 0, 0); }
}

.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.3s ease;
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(-10px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* Изменение дизайна кнопок для большей премиальности */
.bg-gray-900 {
  background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

.bg-gray-900:hover {
  background: linear-gradient(135deg, #374151 0%, #1f2937 100%);
  transform: translateY(-1px);
}

input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.1);
}
</style>

