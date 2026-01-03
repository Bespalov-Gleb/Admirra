<template>
  <div class="min-h-screen flex bg-white">
    <!-- Левая секция - Форма восстановления пароля -->
    <div class="w-full lg:w-5/12 bg-white flex items-center justify-center px-4 sm:px-6 lg:px-12 py-12">
      <div class="w-full max-w-md">
        <!-- Логотип AdMirra -->
        <div class="mb-8 text-center">
          <img :src="logoAdMirra" alt="AdMirra" class="h-12 mb-6 mx-auto" />
        </div>

        <!-- Заголовок -->
        <h1 class="text-3xl sm:text-4xl font-bold text-gray-900 mb-2 text-center">Восстановление пароля</h1>
        <p class="text-sm text-gray-500 mb-8 text-center">Введите email для восстановления пароля</p>

        <!-- Форма -->
        <form @submit.prevent="handleSubmit" class="space-y-5">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Email *
            </label>
            <input
              v-model="email"
              type="email"
              required
              placeholder="E-mail"
              class="w-full px-4 py-3 border border-gray-300 rounded-lg bg-white text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              :class="{ 'border-red-500': error }"
            />
            <p v-if="error" class="mt-2 text-sm text-red-600">{{ error }}</p>
            <p v-if="success" class="mt-2 text-sm text-green-600">{{ success }}</p>
          </div>

          <button
            type="submit"
            :disabled="isLoading"
            class="w-full py-3 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium text-base disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span v-if="isLoading">Отправка...</span>
            <span v-else>Отправить</span>
          </button>

          <div class="text-center space-y-2">
            <div v-if="success" class="mb-2">
              <router-link
                to="/reset-password"
                class="text-sm text-blue-600 hover:text-blue-700 font-medium underline"
              >
                Перейти к установке нового пароля
              </router-link>
            </div>
            <button
              type="button"
              @click="goToLogin"
              class="text-sm text-blue-600 hover:text-blue-700"
            >
              Вернуться к входу
            </button>
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
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import logoAdMirra from '../../assets/imgs/logo/logo-dark.png'
import loginImage from '../../assets/imgs/logo/login.svg'

const router = useRouter()
const email = ref('admin@gmail.com')
const error = ref('')
const success = ref('')
const isLoading = ref(false)

const validateEmail = (value) => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(value)
}

const handleSubmit = async () => {
  error.value = ''
  success.value = ''
  
  if (!email.value.trim()) {
    error.value = 'Пожалуйста, введите email'
    return
  }

  if (!validateEmail(email.value)) {
    error.value = 'Пожалуйста, введите корректный email'
    return
  }

  isLoading.value = true

  try {
    // Здесь должна быть логика отправки запроса на восстановление пароля
    // В реальном приложении это будет API вызов
    await new Promise(resolve => setTimeout(resolve, 1500)) // Имитация запроса
    
    success.value = 'Инструкции по восстановлению пароля отправлены на ваш email. Перейдите по ссылке из письма для установки нового пароля.'
  } catch (err) {
    error.value = 'Произошла ошибка. Пожалуйста, попробуйте еще раз.'
  } finally {
    isLoading.value = false
  }
}

const goToLogin = () => {
  router.push('/login')
}
</script>

