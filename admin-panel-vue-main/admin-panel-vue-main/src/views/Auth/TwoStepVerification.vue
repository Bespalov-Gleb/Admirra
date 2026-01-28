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
                  Подтверждение регистрации
                </h1>
                <p class="text-sm text-gray-500 dark:text-gray-400">
                  Мы отправили код подтверждения на ваш email. Пожалуйста, введите код из письма.
                </p>
              </div>
              <div>
                <form @submit.prevent="handleVerify">
                  <div class="space-y-5">
                    <!-- Verification Code -->
                    <div>
                      <label
                        for="code"
                        class="mb-1.5 block text-sm font-medium text-gray-700"
                      >
                        Код подтверждения<span class="text-red-500">*</span>
                      </label>
                      <input
                        v-model="verificationCode"
                        type="text"
                        id="code"
                        name="code"
                        placeholder="Введите 6-значный код"
                        maxlength="6"
                        @input="handleCodeInput"
                        class="h-11 w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 shadow-sm placeholder:text-gray-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 text-center text-2xl tracking-widest"
                      />
                    </div>
                    <!-- Button -->
                    <div>
                      <button
                        type="submit"
                        :disabled="loading || verificationCode.length !== 6"
                        class="flex items-center justify-center w-full px-4 py-3 text-sm font-semibold text-white transition rounded-lg bg-brand-500 shadow-md hover:bg-brand-600 hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <span v-if="loading" class="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></span>
                        {{ loading ? 'Проверка...' : 'Подтвердить' }}
                      </button>
                    </div>
                  </div>
                </form>
                <div class="mt-5 text-center">
                  <p class="text-sm text-gray-600">
                    Не получили код?
                    <button
                      @click="handleResend"
                      :disabled="resendLoading || resendCooldown > 0"
                      class="text-brand-500 hover:text-brand-600 font-medium disabled:opacity-50"
                    >
                      {{ resendCooldown > 0 ? `Отправить снова (${resendCooldown}с)` : 'Отправить снова' }}
                    </button>
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
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import FullScreenLayout from '@/layouts/FullScreenLayout.vue'
import CommonGridShape from '@/components/common/CommonGridShape.vue'
import logoAdMirra from '@/assets/imgs/logo/logo-dark.png'
import loginImage from '@/assets/imgs/logo/login.svg'
import { DEFAULT_DASHBOARD_PATH } from '@/constants/config'
import api from '../../api/axios'

const router = useRouter()
const verificationCode = ref('')
const loading = ref(false)
const resendLoading = ref(false)
const resendCooldown = ref(0)

const handleCodeInput = (e) => {
  verificationCode.value = e.target.value.replace(/\D/g, '').slice(0, 6)
}

const handleVerify = async () => {
  if (verificationCode.value.length !== 6) return

  loading.value = true
  
  try {
    // TODO: Реализовать API endpoint для подтверждения email
    // await api.post('auth/verify-email', { code: verificationCode.value })
    
    // Временная заглушка
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    router.push(DEFAULT_DASHBOARD_PATH)
  } catch (error) {
    console.error('Ошибка при подтверждении:', error)
  } finally {
    loading.value = false
  }
}

const handleResend = async () => {
  if (resendCooldown.value > 0) return

  resendLoading.value = true
  
  try {
    // TODO: Реализовать API endpoint для повторной отправки кода
    // await api.post('auth/resend-verification-code')
    
    // Временная заглушка
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    resendCooldown.value = 60
    const interval = setInterval(() => {
      resendCooldown.value--
      if (resendCooldown.value <= 0) {
        clearInterval(interval)
      }
    }, 1000)
  } catch (error) {
    console.error('Ошибка при отправке кода:', error)
  } finally {
    resendLoading.value = false
  }
}
</script>
