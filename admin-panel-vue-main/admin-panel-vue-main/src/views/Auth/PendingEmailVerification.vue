<template>
  <FullScreenLayout>
    <div class="relative p-6 bg-white z-1 sm:p-0">
      <div
        class="relative flex flex-col justify-center w-full min-h-screen lg:flex-row bg-white"
      >
        <div class="flex flex-col flex-1 w-full lg:w-1/2 bg-white">
          <div class="absolute top-6 left-6 sm:top-8 sm:left-8 z-10">
            <router-link to="/">
              <img :src="logoAdMirra" alt="AdMirra" class="h-10 sm:h-12" />
            </router-link>
          </div>
          <div class="flex flex-col justify-center flex-1 w-full max-w-md mx-auto pt-10">
            <div class="mb-8">
              <h1
                class="mb-3 font-semibold text-gray-800 text-title-sm dark:text-white/90 sm:text-title-md"
              >
                Проверьте почту
              </h1>
              <p class="text-sm text-gray-500 dark:text-gray-400">
                Мы отправили письмо со ссылкой для подтверждения на
                <span class="font-medium text-gray-700">{{ displayEmail }}</span>.
                Перейдите по ссылке в письме, чтобы завершить регистрацию или вход.
              </p>
            </div>
            <div v-if="infoMessage" class="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg">
              <p class="text-sm text-green-800">{{ infoMessage }}</p>
            </div>
            <div v-if="errorMessage" class="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p class="text-sm text-red-600">{{ errorMessage }}</p>
            </div>
            <div class="space-y-4">
              <button
                type="button"
                :disabled="resendLoading || resendCooldown > 0"
                @click="handleResend"
                class="flex items-center justify-center w-full px-4 py-3 text-sm font-semibold text-white transition rounded-lg bg-brand-500 shadow-md hover:bg-brand-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <span v-if="resendLoading" class="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                {{
                  resendCooldown > 0
                    ? `Отправить снова (${resendCooldown} с)`
                    : 'Отправить письмо снова'
                }}
              </button>
              <router-link
                to="/signin"
                class="block text-center text-sm text-brand-500 hover:text-brand-600 font-medium"
              >
                Вернуться ко входу
              </router-link>
            </div>
          </div>
        </div>
        <div
          class="relative items-center hidden w-full h-full min-h-screen lg:w-1/2 bg-gradient-to-br from-blue-50 via-blue-50 to-blue-100 lg:flex overflow-hidden"
        >
          <div class="relative z-10 w-full px-12 py-16">
            <h2 class="text-2xl font-bold text-blue-900 mb-4">
              Подтверждение email
            </h2>
            <p class="text-blue-800 text-sm leading-relaxed">
              Пока почта не подтверждена, доступ к кабинету недоступен. Если письма нет — проверьте папку «Спам».
            </p>
          </div>
        </div>
      </div>
    </div>
  </FullScreenLayout>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import FullScreenLayout from '@/layouts/FullScreenLayout.vue'
import logoAdMirra from '@/assets/imgs/logo/logo-dark.png'
import { useAuth } from '@/composables/useAuth'

const route = useRoute()
const { resendVerification } = useAuth()

const displayEmail = computed(() => {
  const q = route.query.email
  return typeof q === 'string' && q ? q : 'указанный адрес'
})

const resendLoading = ref(false)
const resendCooldown = ref(0)
const errorMessage = ref('')
const infoMessage = ref('')
let cooldownTimer = null

const startCooldown = (seconds) => {
  if (cooldownTimer) clearInterval(cooldownTimer)
  resendCooldown.value = seconds
  cooldownTimer = setInterval(() => {
    resendCooldown.value--
    if (resendCooldown.value <= 0 && cooldownTimer) {
      clearInterval(cooldownTimer)
      cooldownTimer = null
    }
  }, 1000)
}

const handleResend = async () => {
  const email = typeof route.query.email === 'string' ? route.query.email : ''
  if (!email) {
    errorMessage.value = 'Не указан email. Вернитесь на страницу входа или регистрации.'
    return
  }
  errorMessage.value = ''
  infoMessage.value = ''
  resendLoading.value = true
  try {
    const result = await resendVerification(email)
    if (result.success) {
      infoMessage.value = 'Если email зарегистрирован и не подтверждён, письмо отправлено.'
      startCooldown(60)
    } else {
      // Сервер вернул 429 с текстом "через N с." — парсим
      const msg = result.message || ''
      const match = msg.match(/через\s+(\d+)\s*с\./)
      if (match) {
        startCooldown(parseInt(match[1]))
      } else {
        errorMessage.value = msg || 'Не удалось отправить'
      }
    }
  } finally {
    resendLoading.value = false
  }
}

onUnmounted(() => {
  if (cooldownTimer) clearInterval(cooldownTimer)
})
</script>
