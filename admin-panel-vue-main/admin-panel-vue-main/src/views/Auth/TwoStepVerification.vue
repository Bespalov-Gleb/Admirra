<template>
  <FullScreenLayout>
    <div class="relative p-6 bg-white z-1 sm:p-0">
      <div
        class="relative flex flex-col justify-center w-full h-screen lg:flex-row bg-white"
      >
        <div class="flex flex-col flex-1 w-full lg:w-1/2 bg-white">
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
                  Код для входа
                </h1>
                <p class="text-sm text-gray-500 dark:text-gray-400">
                  Введите 6-значный код из письма
                  <span v-if="emailMasked" class="font-medium text-gray-700"> ({{ emailMasked }})</span>.
                </p>
              </div>
              <div v-if="errorMessage" class="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                <p class="text-sm text-red-600">{{ errorMessage }}</p>
              </div>
              <div>
                <form @submit.prevent="handleVerify">
                  <div class="space-y-5">
                    <div>
                      <label
                        for="code"
                        class="mb-1.5 block text-sm font-medium text-gray-700"
                      >
                        Код<span class="text-red-500">*</span>
                      </label>
                      <input
                        v-model="verificationCode"
                        type="text"
                        id="code"
                        name="code"
                        placeholder="000000"
                        maxlength="6"
                        @input="handleCodeInput"
                        class="h-11 w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm text-gray-900 shadow-sm placeholder:text-gray-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 text-center text-2xl tracking-widest"
                      />
                    </div>
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
                    <router-link
                      to="/signin"
                      class="text-brand-500 hover:text-brand-600 font-medium"
                    >Вернуться ко входу</router-link>
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
            <div class="max-w-lg">
              <h2 class="text-3xl sm:text-4xl font-bold text-blue-900 mb-6 leading-tight">
                Анализируйте и оптимизируйте Ваши рекламные кампании
              </h2>
              <p class="text-base text-blue-800 leading-relaxed">
                Онлайн-сервис для маркетологов, который превращает сырые цифры в понятные, сильные отчёты с глубоким AI-анализом.
              </p>
            </div>
            <div class="flex items-end justify-end mt-auto">
              <img :src="loginImage" alt="Illustration" class="h-[34.7222rem] sm:h-[41.6667rem] w-auto max-w-full object-contain object-right-bottom" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </FullScreenLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import FullScreenLayout from '@/layouts/FullScreenLayout.vue'
import CommonGridShape from '@/components/common/CommonGridShape.vue'
import logoAdMirra from '@/assets/imgs/logo/logo-dark.png'
import loginImage from '@/assets/imgs/logo/login.svg'
import { DEFAULT_DASHBOARD_PATH } from '@/constants/config'
import { useAuth } from '@/composables/useAuth'

const router = useRouter()
const route = useRoute()
const { completeLoginWithOtp } = useAuth()

const verificationCode = ref('')
const loading = ref(false)
const errorMessage = ref('')

const emailMasked = computed(() => {
  const m = route.query.email_masked
  return typeof m === 'string' ? m : ''
})

const challengeId = computed(() => {
  const id = route.query.challenge_id
  return typeof id === 'string' ? id : ''
})

const rememberMe = computed(() => route.query.remember === '1' || route.query.remember === 'true')

const handleCodeInput = (e) => {
  verificationCode.value = e.target.value.replace(/\D/g, '').slice(0, 6)
}

onMounted(() => {
  if (route.query.mode !== 'otp' || !challengeId.value) {
    router.replace('/signin')
  }
})

const handleVerify = async () => {
  if (verificationCode.value.length !== 6) return

  if (!challengeId.value) {
    errorMessage.value = 'Нет данных для проверки кода. Войдите снова.'
    return
  }

  loading.value = true
  errorMessage.value = ''

  const result = await completeLoginWithOtp(challengeId.value, verificationCode.value, rememberMe.value)

  loading.value = false

  if (result.success) {
    router.push(DEFAULT_DASHBOARD_PATH)
  } else {
    errorMessage.value = result.message || 'Ошибка проверки кода'
  }
}
</script>
