<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50">
    <div class="bg-white p-8 rounded-2xl shadow-lg max-w-md w-full text-center space-y-4">
      <div v-if="loading" class="flex flex-col items-center">
        <div class="w-12 h-12 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mb-4"></div>
        <h2 class="text-xl font-bold text-gray-900">
          {{ siteLoginFlow ? 'Вход через Яндекс...' : 'Подключение Яндекс Директ...' }}
        </h2>
        <p class="text-gray-500">
          {{ siteLoginFlow ? 'Завершаем авторизацию.' : 'Пожалуйста, подождите, мы настраиваем интеграцию.' }}
        </p>
      </div>

      <div v-else-if="error" class="flex flex-col items-center">
        <div class="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mb-4 text-red-600">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
        </div>
        <h2 class="text-xl font-bold text-gray-900">{{ siteLoginFlow ? 'Не удалось войти' : 'Ошибка подключения' }}</h2>
        <p class="text-red-500 text-sm mb-6">{{ error }}</p>
        <router-link
          v-if="siteLoginFlow"
          to="/signin"
          class="px-6 py-2 bg-gray-900 text-white rounded-lg hover:bg-black transition-colors"
        >
          На страницу входа
        </router-link>
        <router-link
          v-else
          to="/settings"
          class="px-6 py-2 bg-gray-900 text-white rounded-lg hover:bg-black transition-colors"
        >
          Вернуться в настройки
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../../api/axios'
import { useToaster } from '../../composables/useToaster'
import { useAuth } from '../../composables/useAuth'
import { DEFAULT_DASHBOARD_PATH } from '../../constants/config'
import { setAuthProvider } from '../../utils/authToken'
import { oauthLoginProviderFromState } from '../../utils/oauthLoginState'

const route = useRoute()
const router = useRouter()
const toaster = useToaster()
const { setToken, fetchCurrentUser, getErrorMessage } = useAuth()

const loading = ref(true)
const error = ref(null)
const siteLoginFlow = ref(false)

const logger = {
  info: (msg) => console.log(`[YandexCallback] ${msg}`)
}

onMounted(async () => {
  const stateParam = route.query.state
  const fromSession = sessionStorage.getItem('oauth_site_login') === 'yandex'
  const fromJwtState = oauthLoginProviderFromState(stateParam) === 'yandex'
  const siteLogin = fromSession || fromJwtState

  if (siteLogin) {
    siteLoginFlow.value = true
  }

  const code = route.query.code
  const redirectUri = `${window.location.origin}/auth/yandex/callback`

  if (siteLogin) {
    sessionStorage.removeItem('oauth_site_login')

    if (route.query.error) {
      error.value = String(route.query.error_description || route.query.error || 'Вход отменён')
      loading.value = false
      return
    }

    if (!code) {
      error.value = 'Код авторизации не найден'
      loading.value = false
      return
    }

    const state = stateParam
    if (!state) {
      error.value = 'Параметр state не найден. Попробуйте войти снова.'
      loading.value = false
      return
    }

    try {
      const { data } = await api.post('auth/oauth/yandex/callback', {
        code: String(code),
        state: String(state),
        redirect_uri: redirectUri
      })
      setToken(data.access_token)
      setAuthProvider('yandex')
      const userResult = await fetchCurrentUser()
      if (!userResult.success) {
        throw new Error('Не удалось загрузить профиль')
      }
      router.push(DEFAULT_DASHBOARD_PATH)
    } catch (err) {
      console.error(err)
      const d = err.response?.data?.detail
      error.value = getErrorMessage(err, typeof d === 'string' ? d : 'Не удалось войти через Яндекс')
    } finally {
      loading.value = false
    }
    return
  }

  if (!code) {
    error.value = 'Код авторизации не найден'
    loading.value = false
    return
  }

  try {
    const clientName = localStorage.getItem('yandex_auth_client_name')
    const clientId = localStorage.getItem('yandex_auth_client_id')
    const forAvito = localStorage.getItem('yandex_auth_for_avito') === 'true'

    const payload = {
      code,
      redirect_uri: redirectUri,
      client_name: clientName,
      client_id: clientId,
      platform: forAvito ? 'YANDEX_METRIKA' : 'YANDEX_DIRECT'
    }

    const response = await api.post('integrations/yandex/exchange', payload)

    const isAgency = response.data.is_agency

    localStorage.removeItem('yandex_auth_client_name')
    localStorage.removeItem('yandex_auth_client_id')
    localStorage.removeItem('yandex_auth_for_avito')

    if (forAvito) {
      const avitoIntegrationId = localStorage.getItem('avito_integration_id')
      localStorage.removeItem('avito_integration_id')
      if (response.data.integration_id) {
        localStorage.setItem('metrika_integration_id', response.data.integration_id)
      }
      toaster.success('Яндекс Метрика подключена для лидов Avito')
      router.push({
        path: '/integrations/wizard',
        query: {
          resume_integration_id: avitoIntegrationId,
          initial_step: 3,
          metrika_connected: '1'
        }
      })
      return
    }

    if (isAgency) {
      logger.info('Agency account detected, but proceeding to wizard')
    }

    toaster.success('Яндекс Директ успешно подключен!')
    router.push({
      path: '/integrations/wizard',
      query: {
        resume_integration_id: response.data.integration_id,
        initial_step: 2
      }
    })
  } catch (err) {
    console.error(err)
    error.value = err.response?.data?.detail || 'Не удалось завершить подключение'
  } finally {
    loading.value = false
  }
})
</script>
