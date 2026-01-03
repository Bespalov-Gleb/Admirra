<template>
  <div class="min-h-screen flex bg-white">
    <!-- Левая секция - Форма входа -->
    <div class="w-full lg:w-5/12 bg-white flex items-center justify-center px-4 sm:px-6 lg:px-12 py-12">
      <div class="w-full max-w-md">
        <!-- Логотип AdMirra -->
        <div class="mb-8 text-center">
          <img :src="logoAdMirra" alt="AdMirra" class="h-12 mb-6 mx-auto" />
        </div>

        <!-- Заголовок -->
        <h1 class="text-2xl sm:text-3xl font-bold text-gray-900 mb-8 text-center">Вход в систему</h1>

        <!-- Сообщение об ошибке -->
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
              <XMarkIcon class="w-4 h-4" />
            </button>
          </div>
        </Transition>

        <!-- Форма входа -->
        <form @submit.prevent="handleLogin" class="space-y-5">
          <!-- E-mail -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">E-mail</label>
            <input
              v-model="loginForm.email"
              type="email"
              required
              placeholder="E-mail"
              class="w-full px-4 py-3 border border-gray-300 rounded-lg bg-white text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <!-- Пароль -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Пароль</label>
            <div class="relative">
              <input
                v-model="loginForm.password"
                :type="showPassword ? 'text' : 'password'"
                required
                placeholder="Пароль"
                class="w-full px-4 py-3 pr-10 border border-gray-300 rounded-lg bg-white text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              <button
                type="button"
                @click="showPassword = !showPassword"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                <EyeIcon v-if="!showPassword" class="w-5 h-5" />
                <EyeSlashIcon v-else class="w-5 h-5" />
              </button>
            </div>
          </div>

          <!-- Запомнить меня и Забыли пароль -->
          <div class="flex items-center justify-between">
            <label class="flex items-center">
              <input
                v-model="loginForm.remember"
                type="checkbox"
                class="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              <span class="ml-2 text-sm text-gray-700">Запомнить меня</span>
            </label>
            <router-link
              to="/forgot-password"
              class="text-sm text-gray-900 hover:text-blue-600"
            >
              Забыли пароль?
            </router-link>
          </div>

          <!-- Кнопка входа -->
          <button
            type="submit"
            :disabled="loading"
            class="w-full py-3 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium text-base flex items-center justify-center gap-2"
          >
           <span v-if="loading" class="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
           {{ loading ? 'Вход...' : 'Войти' }}
          </button>

          <!-- Ссылка на регистрацию -->
          <div class="text-center mt-6 space-y-2">
            <div>
              <span class="text-sm text-gray-600">Нет аккаунта? </span>
              <router-link
                to="/register"
                class="text-sm text-blue-600 hover:text-blue-700 font-medium"
              >
                Зарегистрируйтесь
              </router-link>
            </div>
            <!-- Временная ссылка для тестирования -->
            <div class="pt-2 border-t border-gray-200">
              <router-link
                to="/reset-password"
                class="text-xs text-gray-500 hover:text-blue-600"
              >
                Тест: Установка нового пароля
              </router-link>
            </div>
          </div>
        </form>
      </div>
    </div>

    <!-- Правая секция - Промо-контент -->
    <div class="hidden lg:flex lg:w-7/12 bg-gradient-to-br from-blue-50 to-blue-100 relative overflow-hidden mt-[60px] mr-[60px] rounded-tl-[40px] rounded-tr-[40px]">
      <!-- Изображение как фон (уменьшено и позиционировано) -->
      <div class="absolute bottom-0 right-0 z-0 flex items-end justify-end">
        <img :src="loginImage" alt="Illustration" class="h-[600px] w-auto max-w-full object-contain scale-110 object-right-bottom" />
      </div>
      
      <!-- Текст поверх изображения -->
      <div class="w-full h-full flex flex-col justify-start px-12 py-16 relative z-10">
        <!-- Заголовок -->
        <h2 class="text-3xl font-bold text-blue-900 mb-6 leading-tight">
          Анализируйте и <br />
          оптимизируйте <br />
          Ваши рекламные кампании
        </h2>

        <!-- Описание -->
        <p class="text-base text-blue-800 leading-relaxed max-w-lg">
          Онлайн-сервис для маркетологов, который превращает сырые цифры в понятные, сильные отчёты с глубоким AI-анализом.
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ExclamationCircleIcon, XMarkIcon } from '@heroicons/vue/24/outline'
import EyeIcon from '@/assets/icons/eye.vue'
import EyeSlashIcon from '@/assets/icons/eye-slash.vue'
import { useAuth } from '@/composables/useAuth'
import logoAdMirra from '@/assets/imgs/logo/logo-dark.png'
import loginImage from '@/assets/imgs/logo/login.svg'

const router = useRouter()
const { login } = useAuth()
const showPassword = ref(false)
const loading = ref(false)
const errorMessage = ref('')
const errorShake = ref(false)

const loginForm = reactive({
  email: '',
  password: '',
  remember: false
})

const triggerError = (msg) => {
  errorMessage.value = msg
  errorShake.value = true
  setTimeout(() => {
    errorShake.value = false
  }, 500)
}

const isValidEmail = (email) => {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
}

const handleLogin = async () => {
  if (!loginForm.email) return triggerError('Пожалуйста, введите Email')
  if (!isValidEmail(loginForm.email)) return triggerError('Введите корректный Email адрес')
  if (!loginForm.password) return triggerError('Пожалуйста, введите пароль')

  loading.value = true
  errorMessage.value = ''
  
  const result = await login(loginForm.email, loginForm.password)
  
  loading.value = false
  if (result.success) {
    router.push('/dashboard/general-3')
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
  50% { transform: translate3d(-4px, 0, 0); }
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
</style>
