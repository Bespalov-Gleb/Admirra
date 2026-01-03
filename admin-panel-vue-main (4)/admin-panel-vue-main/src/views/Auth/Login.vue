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
        <h1 class="text-3xl sm:text-4xl font-bold text-gray-900 mb-8 text-center">Вход в систему</h1>

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
            class="w-full py-3 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium text-base"
          >
            Войти
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
import EyeIcon from '../../assets/icons/eye.vue'
import EyeSlashIcon from '../../assets/icons/eye-slash.vue'
import { useAuth } from '../../composables/useAuth'
import logoAdMirra from '../../assets/imgs/logo/logo-dark.png'
import loginImage from '../../assets/imgs/logo/login.svg'

const router = useRouter()
const { setToken } = useAuth()
const showPassword = ref(false)

const loginForm = reactive({
  email: 'admin@gmail.com',
  password: 'password',
  remember: false
})

const handleLogin = () => {
  console.log('Login:', loginForm)
  const mockToken = 'mock_token_' + Date.now()
  setToken(mockToken)
  // Guard проверяет localStorage напрямую, поэтому можно переходить сразу
  router.push('/dashboard/general')
}
</script>
