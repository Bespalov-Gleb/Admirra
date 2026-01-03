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
        <h1 class="text-3xl sm:text-4xl font-bold text-gray-900 mb-8 text-center">
          {{ isLogin ? 'Вход в систему' : 'Регистрация' }}
        </h1>

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
        <form v-if="isLogin" @submit.prevent="handleLogin" class="space-y-5">
          <!-- E-mail -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">E-mail</label>
            <input
              v-model="loginForm.email"
              type="email"
              required
              placeholder="E-mail"
              class="w-full px-4 py-3 border border-gray-300 rounded-lg bg-white text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all font-medium"
            />
          </div>

          <!-- Пароль -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Пароль</label>
            <div class="relative">
              <input
                v-model="loginForm.password"
                :type="showLoginPassword ? 'text' : 'password'"
                required
                placeholder="Пароль"
                class="w-full px-4 py-3 pr-10 border border-gray-300 rounded-lg bg-white text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all font-medium"
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

          <!-- Запомнить меня и Забыли пароль -->
          <div class="flex items-center justify-between">
            <label class="flex items-center cursor-pointer">
              <input
                v-model="loginForm.remember"
                type="checkbox"
                class="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              <span class="ml-2 text-sm text-gray-700">Запомнить меня</span>
            </label>
            <a href="#" class="text-sm text-gray-900 hover:text-blue-600 font-medium transition-colors">
              Забыли пароль?
            </a>
          </div>

          <!-- Кнопка входа -->
          <button
            type="submit"
            :disabled="loading"
            class="w-full py-3 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-all font-medium text-base shadow-sm hover:shadow-md disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
           <span v-if="loading" class="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
           {{ loading ? 'Вход...' : 'Войти' }}
          </button>

          <!-- Ссылка на регистрацию -->
          <div class="text-center mt-6">
            <span class="text-sm text-gray-600">Нет аккаунта? </span>
            <button
              type="button"
              @click="toggleMode"
              class="text-sm text-blue-600 hover:text-blue-700 font-bold transition-colors"
            >
              Зарегистрируйтесь
            </button>
          </div>
        </form>

        <!-- Форма регистрации -->
        <form v-else @submit.prevent="handleRegister" class="space-y-5">
           <!-- Имя -->
           <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Имя</label>
            <input
              v-model="registerForm.username"
              type="text"
              required
              placeholder="Ваше имя"
              class="w-full px-4 py-3 border border-gray-300 rounded-lg bg-white text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all font-medium"
            />
          </div>

          <!-- E-mail -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">E-mail</label>
            <input
              v-model="registerForm.email"
              type="email"
              required
              placeholder="E-mail"
              class="w-full px-4 py-3 border border-gray-300 rounded-lg bg-white text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all font-medium"
            />
          </div>

          <!-- Пароль -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Пароль</label>
            <div class="relative">
              <input
                v-model="registerForm.password"
                :type="showRegisterPassword ? 'text' : 'password'"
                required
                placeholder="Придумайте пароль"
                class="w-full px-4 py-3 pr-10 border border-gray-300 rounded-lg bg-white text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all font-medium"
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

          <!-- Подтверждение пароля -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Подтвердите пароль</label>
            <div class="relative">
              <input
                v-model="registerForm.confirmPassword"
                :type="showConfirmPassword ? 'text' : 'password'"
                required
                placeholder="Повторите пароль"
                class="w-full px-4 py-3 pr-10 border border-gray-300 rounded-lg bg-white text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all font-medium"
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
          
           <!-- Согласие -->
          <div class="flex items-center">
            <label class="flex items-center cursor-pointer">
                <input
                v-model="registerForm.agree"
                type="checkbox"
                class="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
                <span class="ml-2 text-sm text-gray-600">
                Я согласен с <a href="#" class="text-blue-600 hover:text-blue-700 font-medium">условиями использования</a>
                </span>
            </label>
          </div>

          <!-- Кнопка регистрации -->
          <button
            type="submit"
            :disabled="loading"
            class="w-full py-3 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-all font-medium text-base shadow-sm hover:shadow-md disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
           <span v-if="loading" class="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
           {{ loading ? 'Регистрация...' : 'Зарегистрироваться' }}
          </button>

          <!-- Ссылка на вход -->
          <div class="text-center mt-6">
            <span class="text-sm text-gray-600">Уже есть аккаунт? </span>
            <button
              type="button"
              @click="toggleMode"
              class="text-sm text-blue-600 hover:text-blue-700 font-bold transition-colors"
            >
              Войти
            </button>
          </div>
        </form>

      </div>
    </div>

    <!-- Правая секция - Промо-контент -->
    <div class="hidden lg:flex lg:w-7/12 bg-gradient-to-br from-blue-50 to-blue-100 relative overflow-hidden mt-[30px] mr-[30px] mb-[30px] rounded-[40px] border border-blue-100 shadow-sm">
      <!-- Изображение как фон -->
      <div class="absolute bottom-0 right-0 z-0 flex items-end justify-end w-full h-full pointer-events-none">
        <img :src="loginImage" alt="Illustration" class="h-[85%] w-auto object-contain object-right-bottom mr-[-5%]" />
      </div>
      
      <!-- Текст поверх изображения -->
      <div class="w-full h-full flex flex-col justify-start px-16 py-20 relative z-10">
        <!-- Заголовок -->
        <h2 class="text-5xl font-bold text-blue-900 mb-8 leading-tight tracking-tight">
          Анализируйте и <br />
          оптимизируйте <br />
          Ваши кампании
        </h2>

        <!-- Описание -->
        <p class="text-xl text-blue-700/80 leading-relaxed max-w-lg font-medium">
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
import EyeIcon from '../../assets/icons/eye.vue'
import EyeSlashIcon from '../../assets/icons/eye-slash.vue'
import { useAuth } from '../../composables/useAuth'
import logoAdMirra from '../../assets/imgs/logo/logo-dark.png'
import loginImage from '../../assets/imgs/logo/login.svg'

const router = useRouter()
const { login, register } = useAuth()

const isLogin = ref(true)
const showLoginPassword = ref(false)
const showRegisterPassword = ref(false)
const showConfirmPassword = ref(false)
const loading = ref(false)
const errorMessage = ref('')
const errorShake = ref(false)

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

const toggleMode = () => {
    isLogin.value = !isLogin.value
    errorMessage.value = ''
    loginForm.email = ''
    loginForm.password = ''
    registerForm.username = ''
    registerForm.email = ''
    registerForm.password = ''
    registerForm.confirmPassword = ''
}

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
