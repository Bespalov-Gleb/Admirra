<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50">
    <div class="bg-white p-8 rounded-2xl shadow-lg max-w-md w-full text-center space-y-4">
      <div v-if="loading" class="flex flex-col items-center">
        <div class="w-12 h-12 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mb-4" />
        <h2 class="text-xl font-semibold text-gray-900">Завершение входа...</h2>
        <p class="text-gray-500 text-sm">Пожалуйста, подождите.</p>
      </div>
      <div v-else-if="error" class="flex flex-col items-center">
        <div class="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mb-4 text-red-600">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </div>
        <h2 class="text-xl font-semibold text-gray-900">Не удалось войти</h2>
        <p class="text-red-500 text-sm mb-6">{{ error }}</p>
        <router-link
          to="/signin"
          class="px-6 py-2 bg-gray-900 text-white rounded-lg hover:bg-black transition-colors"
        >
          На страницу входа
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api, { refreshAccessToken } from '@/api/axios'
import { useAuth } from '@/composables/useAuth'
import { consumeVkPkceByState } from '@/composables/useOAuthLogin'
import { DEFAULT_DASHBOARD_PATH } from '@/constants/config'
import { setAuthProvider } from '@/utils/authToken'

const route = useRoute()
const router = useRouter()
const { setToken, fetchCurrentUser, getErrorMessage } = useAuth()

const loading = ref(true)
const error = ref(null)

const provider = route.meta.oauthProvider

function formatDetail(detail) {
  if (!detail) return 'Ошибка входа'
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((e) => e.msg || JSON.stringify(e)).join('. ')
  }
  return String(detail)
}

onMounted(async () => {
  if (provider !== 'yandex' && provider !== 'vk') {
    error.value = 'Неизвестный провайдер'
    loading.value = false
    return
  }

  if (route.query.error) {
    error.value =
      formatDetail(route.query.error_description) ||
      formatDetail(route.query.error) ||
      'Вход отменён'
    loading.value = false
    return
  }

  const code = route.query.code
  const state = route.query.state
  const deviceIdRaw = route.query.device_id
  if (!code || !state) {
    error.value = 'Нет кода авторизации. Вернитесь и попробуйте снова.'
    loading.value = false
    return
  }

  // Совпадает с URL, на который провайдер вернул браузер (должен совпадать с redirect_uri при authorize).
  const redirectUri = `${window.location.origin}${route.path}`
  const path =
    provider === 'yandex' ? 'auth/oauth/yandex/callback' : 'auth/oauth/vk/callback'

  try {
    const profileLinkProvider = sessionStorage.getItem('oauth_profile_link')
    if (profileLinkProvider === provider) {
      try {
        await refreshAccessToken()
      } catch {
        // Если refresh-cookie уже недействителен, backend вернёт обычную ошибку/логин-сценарий.
      }
    }
    const payload = {
      code: String(code),
      state: String(state),
      redirect_uri: redirectUri,
    }
    if (provider === 'vk') {
      const deviceId = Array.isArray(deviceIdRaw) ? deviceIdRaw[0] : deviceIdRaw
      const codeVerifier = consumeVkPkceByState(String(state))
      if (!deviceId || !String(deviceId).trim()) {
        throw new Error('VK ID не вернул device_id. Начните вход заново.')
      }
      if (!codeVerifier) {
        throw new Error('Не найден code_verifier для VK ID. Начните вход заново.')
      }
      payload.device_id = String(deviceId).trim()
      payload.code_verifier = codeVerifier
    }
    const { data } = await api.post(path, payload)
    setToken(data.access_token)
    setAuthProvider(provider)
    const userResult = await fetchCurrentUser()
    if (!userResult.success) {
      throw new Error('Не удалось загрузить профиль')
    }
    if (profileLinkProvider === provider) {
      sessionStorage.removeItem('oauth_profile_link')
      router.push('/profile')
    } else {
      router.push(DEFAULT_DASHBOARD_PATH)
    }
  } catch (err) {
    console.error('[OAuthLoginCallback]', err)
    const d = err.response?.data?.detail
    error.value = getErrorMessage(err, formatDetail(d))
  } finally {
    loading.value = false
  }
})
</script>
