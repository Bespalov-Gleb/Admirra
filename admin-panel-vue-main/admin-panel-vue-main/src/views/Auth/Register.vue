<template>
  <div class="min-h-screen flex bg-white">
    <!-- Левая секция - Форма регистрации -->
    <div class="w-full lg:w-5/12 bg-white flex items-center justify-center px-4 sm:px-6 lg:px-12 py-12">
      <div class="w-full max-w-md">
        <!-- Логотип AdMirra -->
        <div class="mb-8 text-center">
          <img :src="logoAdMirra" alt="AdMirra" class="h-12 mb-6 mx-auto" />
        </div>

        <!-- Заголовок -->
        <h1 class="text-3xl sm:text-4xl font-bold text-gray-900 mb-8 text-center">Регистрация</h1>

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

        <!-- Кнопки соцрегистрации -->
        <div class="mb-6">
          <div class="flex items-center justify-center gap-4">
            <button
              class="flex items-center justify-center w-16 h-16 transition-all bg-white rounded-lg hover:bg-gray-50 hover:shadow-md border-none"
              type="button"
            >
              <svg
                width="32"
                height="32"
                viewBox="0 0 24 24"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  fill="#4285F4"
                />
                <path
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  fill="#34A853"
                />
                <path
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                  fill="#FBBC05"
                />
                <path
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                  fill="#EA4335"
                />
              </svg>
            </button>
            <button
              class="flex items-center justify-center w-16 h-16 transition-all bg-white rounded-lg hover:bg-gray-50 hover:shadow-md border-none"
              type="button"
            >
              <img src="/images/shape/yandex-logo-rus.svg" alt="Yandex" class="w-12 h-12" />
            </button>
            <button
              class="flex items-center justify-center w-16 h-16 transition-all bg-white rounded-lg hover:bg-gray-50 hover:shadow-md border-none"
              type="button"
            >
              <img src="/images/shape/vk-v2.svg" alt="VK" class="w-12 h-12" />
            </button>
          </div>
          <div class="relative py-3 sm:py-5">
            <div class="absolute inset-0 flex items-center">
              <div class="w-full border-t border-gray-300"></div>
            </div>
            <div class="relative flex justify-center text-sm">
              <span class="px-4 py-1 text-gray-500 bg-white rounded">Или</span>
            </div>
          </div>
        </div>

        <!-- Форма регистрации -->
        <form @submit.prevent="handleRegister" class="space-y-5">
          <!-- Имя -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Имя</label>
            <input
              v-model="registerForm.username"
              type="text"
              required
              placeholder="Введите имя"
              class="w-full px-4 py-3 border border-gray-300 rounded-lg bg-white text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <!-- E-mail -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">E-mail</label>
            <input
              v-model="registerForm.email"
              type="text"
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
                v-model="registerForm.password"
                :type="showPassword ? 'text' : 'password'"
                required
                placeholder="Пароль"
                minlength="6"
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

          <!-- Подтверждение пароля -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Подтвердите пароль</label>
            <div class="relative">
              <input
                v-model="registerForm.confirmPassword"
                :type="showConfirmPassword ? 'text' : 'password'"
                required
                placeholder="Подтвердите пароль"
                minlength="6"
                class="w-full px-4 py-3 pr-10 border border-gray-300 rounded-lg bg-white text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              <button
                type="button"
                @click="showConfirmPassword = !showConfirmPassword"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                <EyeIcon v-if="!showConfirmPassword" class="w-5 h-5" />
                <EyeSlashIcon v-else class="w-5 h-5" />
              </button>
            </div>
          </div>

          <!-- Согласие с условиями -->
          <div class="flex items-start">
            <input
              v-model="registerForm.agree"
              type="checkbox"
              required
              class="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 mt-0.5"
            />
            <span class="ml-2 text-sm text-gray-600">
              Я согласен с <a href="#" class="text-blue-600 hover:text-blue-700">условиями использования</a>
            </span>
          </div>

          <!-- Кнопка регистрации -->
          <button
            type="submit"
            :disabled="loading"
            class="w-full py-3 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium text-base flex items-center justify-center gap-2"
          >
           <span v-if="loading" class="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
           {{ loading ? 'Регистрация...' : 'Зарегистрироваться' }}
          </button>

          <!-- Ссылка на вход -->
          <div class="text-center mt-6">
            <span class="text-sm text-gray-600">Уже есть аккаунт? </span>
            <router-link
              to="/login"
              class="text-sm text-blue-600 hover:text-blue-700 font-medium"
            >
              Войти
            </router-link>
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
        <h2 class="text-4xl font-bold text-blue-900 mb-6 leading-tight">
          Анализируйте и <br />
          оптимизируйте <br />
          Ваши рекламные кампании
        </h2>

        <!-- Описание -->
        <p class="text-lg text-blue-800 leading-relaxed max-w-lg">
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
import { DEFAULT_DASHBOARD_PATH } from '@/constants/config'
import logoAdMirra from '@/assets/imgs/logo/logo-dark.png'
import loginImage from '@/assets/imgs/logo/login.svg'

const router = useRouter()
const { register } = useAuth()
const showPassword = ref(false)
const showConfirmPassword = ref(false)
const loading = ref(false)
const errorMessage = ref('')
const errorShake = ref(false)

const registerForm = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
  agree: false
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

const handleRegister = async () => {
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
    router.push(DEFAULT_DASHBOARD_PATH)
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
