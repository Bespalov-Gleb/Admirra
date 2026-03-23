<template>
  <FullScreenLayout>
    <div class="relative p-6 bg-white z-1 sm:p-0 min-h-screen flex items-center justify-center">
      <div class="text-center max-w-md px-4">
        <img :src="logoAdMirra" alt="AdMirra" class="h-10 mx-auto mb-6" />
        <div v-if="status === 'loading'" class="space-y-4">
          <div class="w-10 h-10 border-4 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p class="text-gray-600">Подтверждаем email…</p>
        </div>
        <div v-else-if="status === 'error'" class="space-y-4">
          <p class="text-red-600">{{ errorMessage }}</p>
          <router-link
            to="/signin"
            class="inline-block text-brand-500 hover:text-brand-600 font-medium"
          >На страницу входа</router-link>
        </div>
        <div v-else class="space-y-4">
          <p class="text-gray-700">Email подтверждён. Перенаправляем…</p>
        </div>
      </div>
    </div>
  </FullScreenLayout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import FullScreenLayout from '@/layouts/FullScreenLayout.vue'
import logoAdMirra from '@/assets/imgs/logo/logo-dark.png'
import { useAuth } from '@/composables/useAuth'
import { DEFAULT_DASHBOARD_PATH } from '@/constants/config'

const route = useRoute()
const router = useRouter()
const { verifyEmailWithToken } = useAuth()

const status = ref('loading')
const errorMessage = ref('')

onMounted(async () => {
  const token = route.query.token
  if (!token || typeof token !== 'string') {
    status.value = 'error'
    errorMessage.value = 'Ссылка неполная. Откройте письмо из почты и перейдите по ссылке снова.'
    return
  }

  const result = await verifyEmailWithToken(token)
  if (result.success) {
    status.value = 'ok'
    await router.replace(DEFAULT_DASHBOARD_PATH)
  } else {
    status.value = 'error'
    errorMessage.value = result.message || 'Не удалось подтвердить email'
  }
})
</script>
