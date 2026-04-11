<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50">
    <div class="bg-white p-8 rounded-2xl shadow-lg max-w-md w-full text-center space-y-4">
      <div v-if="loading" class="flex flex-col items-center">
        <div class="w-12 h-12 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mb-4"></div>
        <h2 class="text-xl font-bold text-gray-900">
          {{ siteLoginFlow ? 'Вход через VK...' : 'Подключение VK Ads...' }}
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
          to="/projects/create"
          class="px-6 py-2 bg-gray-900 text-white rounded-lg hover:bg-black transition-colors"
        >
          Вернуться на панель
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
import { ADMIRRA_PUBLIC_ORIGIN } from '../../config/admirraPublic'
import { oauthLoginProviderFromState } from '../../utils/oauthLoginState'

const route = useRoute()
const router = useRouter()
const toaster = useToaster()
const { setToken, fetchCurrentUser, getErrorMessage } = useAuth()

const loading = ref(true)
const error = ref(null)
const siteLoginFlow = ref(false)

onMounted(async () => {
  const code = route.query.code
  const state = route.query.state
  const fromSession = sessionStorage.getItem('oauth_site_login') === 'vk'
  const fromJwtState = oauthLoginProviderFromState(state) === 'vk'
  const siteLogin = fromSession || fromJwtState

  if (siteLogin) {
    siteLoginFlow.value = true
  }

  const errorParam = route.query.error
  const errorDescription = route.query.error_description
  const user_id = route.query.user_id // VK может вернуть user_id
  
  console.log('[VKCallback] Query params:', { code, state, errorParam, errorDescription, user_id })
  console.log('[VKCallback] Full query:', route.query)
  
  // Проверяем ошибки от VK OAuth (VK перенаправляет с ?error=...)
  if (errorParam) {
    const integrationMessages = {
      'invalid_client': 'Неверный client_id или client_secret. Проверьте настройки приложения в VK Ads и значения в .env файле.',
      'invalid_redirect_uri': `redirect_uri не совпадает с настройками приложения. В VK Ads должен быть указан: ${ADMIRRA_PUBLIC_ORIGIN}/auth/vk/callback`,
      'invalid_scope': 'Неверные права доступа. В настройках приложения VK Ads разрешите права из документации API (например read_ads, read_payments, create_ads).',
      'access_denied': 'Вы отклонили запрос прав доступа. Попробуйте авторизоваться снова и разрешите доступ.',
      'invalid_grant': 'Код авторизации истек. Попробуйте авторизоваться заново.',
    }
    const siteLoginMessages = {
      'invalid_client': 'Неверный client_id или защищённый ключ. Проверьте VK_LOGIN_CLIENT_ID / VK_LOGIN_CLIENT_SECRET (или VK_CLIENT_*) в .env и приложение на vk.com/apps.',
      'invalid_redirect_uri': `Добавьте в приложении ВКонтакте (vk.com → Мои приложения → Настройки) доверенный redirect URI: ${window.location.origin}/auth/vk/callback`,
      'invalid_scope': 'Неверный scope для входа. В .env задайте VK_LOGIN_SCOPE (по умолчанию на бэкенде — email) и включите те же права в настройках приложения VK.',
      'access_denied': 'Вы отклонили запрос прав доступа. Попробуйте войти снова и разрешите доступ.',
      'invalid_grant': 'Код авторизации истек или уже использован. Попробуйте войти снова.',
      'invalid_request': 'Запрос отклонён (часто это Security Error). Выйдите из аккаунта ВК в браузере и войдите снова; проверьте доверенный домен и redirect URI в vk.com/apps. Для oauth.vk.com нужен тип приложения «Веб»; чисто рекламное приложение VK Ads может не подойти — создайте отдельное приложение и VK_LOGIN_CLIENT_ID.',
    }
    const errorMessages = siteLogin ? siteLoginMessages : integrationMessages

    let errorMessage = errorMessages[errorParam] || errorDescription || `Ошибка авторизации VK: ${errorParam}`
    if (
      siteLogin &&
      errorParam === 'invalid_request' &&
      /security/i.test(String(errorDescription || ''))
    ) {
      errorMessage =
        'VK: Security Error — чаще всего устаревшая сессия: выйдите из ВК (vk.com → Выйти), войдите снова и повторите вход. Если не помогло: отдельное приложение «Веб» для входа (не только VK Ads), в настройках — базовый домен сайта и точный redirect_uri.'
    }
    console.error('[VKCallback] VK OAuth error:', errorParam, errorDescription)
    error.value = errorMessage
    loading.value = false
    sessionStorage.removeItem('oauth_site_login')
    // Clean up localStorage
    localStorage.removeItem('vk_auth_state')
    return
  }

  if (siteLogin) {
    sessionStorage.removeItem('oauth_site_login')
    localStorage.removeItem('vk_auth_state')

    if (!code || !state) {
      error.value = 'Нет кода или state авторизации. Попробуйте войти снова.'
      loading.value = false
      return
    }

    const redirectUri = `${window.location.origin}/auth/vk/callback`
    const rawUid = route.query.user_id
    const uid = Array.isArray(rawUid) ? rawUid[0] : rawUid
    try {
      const { data } = await api.post('auth/oauth/vk/callback', {
        code: String(code),
        state: String(state),
        redirect_uri: redirectUri,
        ...(uid != null && String(uid).trim() !== ''
          ? { vk_redirect_user_id: String(uid).trim() }
          : {})
      })
      setToken(data.access_token)
      const userResult = await fetchCurrentUser()
      if (!userResult.success) {
        throw new Error('Не удалось загрузить профиль')
      }
      router.push(DEFAULT_DASHBOARD_PATH)
    } catch (err) {
      console.error('[VKCallback] Site login error:', err)
      const d = err.response?.data?.detail
      error.value = getErrorMessage(err, typeof d === 'string' ? d : 'Не удалось войти через VK')
    } finally {
      loading.value = false
    }
    return
  }
  
  // Проверка CSRF защиты: сравниваем state из callback с сохраненным
  const savedState = localStorage.getItem('vk_auth_state')
  if (state && savedState && state !== savedState) {
    console.error('[VKCallback] State mismatch:', { received: state, saved: savedState })
    error.value = 'Ошибка безопасности: неверный state параметр. Попробуйте авторизоваться заново.'
    loading.value = false
    localStorage.removeItem('vk_auth_state')
    return
  }
  
  if (!code) {
    console.error('[VKCallback] No authorization code in query params')
    error.value = 'Код авторизации не найден. Возможно, вы не завершили процесс авторизации или произошла ошибка.'
    loading.value = false
    localStorage.removeItem('vk_auth_state')
    return
  }

  try {
    const redirectUri = `${window.location.origin}/auth/vk/callback`
    const clientName = localStorage.getItem('vk_auth_client_name')
    const clientId = localStorage.getItem('vk_auth_client_id')
    
    console.log('[VKCallback] Exchanging code for token...', { 
      code: code.substring(0, 10) + '...', 
      redirectUri, 
      clientName, 
      clientId
    })
    
    const payload = { 
      code, 
      redirect_uri: redirectUri,
      client_name: clientName,
      client_id: clientId // CRITICAL: Pass client_id to link integration to correct project
    }
    
    const response = await api.post('integrations/vk/exchange', payload)
    console.log('[VKCallback] Token exchange successful:', response.data)
    const integrationId = response.data.integration_id
    
    // Clean up localStorage
    localStorage.removeItem('vk_auth_client_name')
    localStorage.removeItem('vk_auth_client_id')
    localStorage.removeItem('vk_auth_state')
    toaster.success('VK Ads успешно подключен!')
    
    // Redirect to integration wizard step 2 (campaigns, profile selection removed)
    router.push(`/integrations/wizard?resume_integration_id=${integrationId}&initial_step=2`) 
  } catch (err) {
    console.error('[VKCallback] Token exchange error:', err)
    console.error('[VKCallback] Error response:', err.response)
    console.error('[VKCallback] Error data:', err.response?.data)
    
    // Более детальная обработка ошибок
    let errorMessage = 'Не удалось завершить подключение'
    if (err.response?.data?.detail) {
      errorMessage = err.response.data.detail
    } else if (err.response?.data?.error) {
      errorMessage = `Ошибка VK Ads: ${err.response.data.error}`
      if (err.response.data.error_description) {
        errorMessage += ` - ${err.response.data.error_description}`
      }
    } else if (err.message) {
      errorMessage = `Ошибка: ${err.message}`
    }
    
    error.value = errorMessage
    localStorage.removeItem('vk_auth_state')
  } finally {
    loading.value = false
  }
})
</script>
