<template>
  <FullScreenLayout>
    <div class="relative p-6 bg-white z-1 sm:p-0">
      <div
        class="relative flex flex-col justify-center w-full h-screen lg:flex-row bg-white"
      >
        <div class="flex flex-col flex-1 w-full lg:w-1/2 bg-white">
          <!-- Логотип в верхнем левом углу -->
          <div class="absolute top-6 left-6 sm:top-8 sm:left-8 z-10">
            <router-link to="/">
              <img :src="logoAdMirra" alt="AdMirra" class="h-10 sm:h-12" />
            </router-link>
          </div>
          <div class="flex flex-col justify-center flex-1 w-full max-w-md mx-auto pt-10">
            <div>
              <div class="mb-5 sm:mb-8">
                <h1
                  class="mb-2 font-semibold text-gray-800 text-title-sm dark:text-white/90 sm:text-title-md"
                >
                  Восстановление пароля
                </h1>
                <p class="text-sm text-gray-500 dark:text-gray-400">
                  Введите ваш email, и мы отправим вам ссылку для сброса пароля
                </p>
              </div>
              <div>
                <form @submit.prevent="handleResetPassword">
                  <div class="space-y-5">
                    <!-- Email -->
                    <div>
                      <label
                        for="email"
                        class="mb-1.5 block text-sm font-medium text-gray-700"
                      >
                        Email<span class="text-red-500">*</span>
                      </label>
                      <input
                        v-model="resetForm.email"
                        type="email"
                        id="email"
                        name="email"
                        placeholder="Введите ваш email"
                        class="h-11 w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 shadow-sm placeholder:text-gray-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                      />
                    </div>
                    <!-- Button -->
                    <div>
                      <button
                        type="submit"
                        :disabled="loading || emailSent"
                        class="flex items-center justify-center w-full px-4 py-3 text-sm font-semibold text-white transition rounded-lg bg-brand-500 shadow-md hover:bg-brand-600 hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <span v-if="loading" class="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></span>
                        {{ loading ? 'Отправка...' : emailSent ? 'Письмо отправлено' : 'Отправить ссылку для сброса' }}
                      </button>
                    </div>
                  </div>
                </form>
                <div v-if="emailSent" class="mt-5 p-4 rounded-lg bg-green-50 border border-green-200">
                  <p class="text-sm text-green-800">
                    Мы отправили ссылку для сброса пароля на {{ resetForm.email }}
                  </p>
                </div>
                <div class="mt-5">
                  <p
                    class="text-sm font-normal text-center text-gray-700 sm:text-start"
                  >
                    Вспомнили пароль?
                    <router-link
                      to="/signin"
                      class="text-brand-500 hover:text-brand-600 font-medium"
                      >Войти</router-link
                    >
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div
          class="relative items-center hidden w-full h-full lg:w-1/2 bg-gradient-to-br from-blue-50 via-blue-50 to-blue-100 lg:flex overflow-hidden"
        >
          <div class="absolute inset-0 z-0">
            <CommonGridShape />
          </div>
          <div class="relative z-10 w-full h-full flex flex-col justify-between px-12 py-16">
            <!-- Текст в верхней части -->
            <div class="max-w-lg">
              <h2 class="text-3xl sm:text-4xl font-bold text-blue-900 mb-6 leading-tight">
                Анализируйте и оптимизируйте Ваши рекламные кампании
              </h2>
              <p class="text-base text-blue-800 leading-relaxed">
                Онлайн-сервис для маркетологов, который превращает сырые цифры в понятные, сильные отчёты с глубоким AI-анализом.
              </p>
            </div>
            <!-- Иллюстрация в нижней части -->
            <div class="flex items-end justify-end mt-auto">
              <img :src="loginImage" alt="Illustration" class="h-[500px] sm:h-[600px] w-auto max-w-full object-contain object-right-bottom" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </FullScreenLayout>
</template>

<script setup>
import { ref, reactive } from 'vue'
import FullScreenLayout from '@/layouts/FullScreenLayout.vue'
import CommonGridShape from '@/components/common/CommonGridShape.vue'
import logoAdMirra from '@/assets/imgs/logo/logo-dark.png'
import loginImage from '@/assets/imgs/logo/login.svg'
import api from '../../api/axios'

const loading = ref(false)
const emailSent = ref(false)

const resetForm = reactive({
  email: ''
})

const isValidEmail = (email) => {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
}

const handleResetPassword = async () => {
  if (!resetForm.email) return
  if (!isValidEmail(resetForm.email)) return

  loading.value = true
  
  try {
    // TODO: Реализовать API endpoint для сброса пароля
    // await api.post('auth/reset-password', { email: resetForm.email })
    
    // Временная заглушка
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    emailSent.value = true
  } catch (error) {
    console.error('Ошибка при отправке письма:', error)
  } finally {
    loading.value = false
  }
}
</script>
