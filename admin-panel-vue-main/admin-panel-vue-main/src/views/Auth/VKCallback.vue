<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50">
    <div class="bg-white p-8 rounded-2xl shadow-lg max-w-md w-full text-center space-y-4">
      <div v-if="loading" class="flex flex-col items-center">
        <div class="w-12 h-12 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mb-4"></div>
        <h2 class="text-xl font-bold text-gray-900">{{ isClientLink ? 'Проверяем доступ…' : 'Подключение VK Ads...' }}</h2>
        <p class="text-gray-500">{{ isClientLink ? 'Пожалуйста, подождите немного.' : 'Пожалуйста, подождите, мы настраиваем интеграцию.' }}</p>
      </div>

      <div v-else-if="clientLinkOutcome === 'authorized'" class="flex flex-col items-center">
        <div class="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mb-4 text-green-600 text-2xl">✓</div>
        <h2 class="text-xl font-bold text-gray-900">Доступ предоставлен</h2>
        <p class="text-gray-500 text-sm mt-2">Вы разрешили агентству получать статистику рекламного кабинета VK Ads. Доступ только на чтение — управлять кампаниями через AdMirra нельзя.</p>
        <p class="text-gray-400 text-sm mt-4">Можно закрыть эту страницу.</p>
      </div>

      <div v-else-if="clientLinkOutcome === 'declined'" class="flex flex-col items-center">
        <div class="w-12 h-12 bg-amber-100 rounded-full flex items-center justify-center mb-4 text-amber-600 text-2xl">!</div>
        <h2 class="text-xl font-bold text-gray-900">Доступ не был предоставлен</h2>
        <p class="text-gray-500 text-sm mt-2">Если передумаете — откройте ссылку ещё раз, пока она действует.</p>
      </div>

      <div v-else-if="clientLinkOutcome === 'invalid'" class="flex flex-col items-center">
        <div class="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mb-4 text-red-600 text-2xl">×</div>
        <h2 class="text-xl font-bold text-gray-900">Ссылка недействительна</h2>
        <p class="text-gray-500 text-sm mt-2">Срок действия ссылки истёк или она уже была использована. Попросите агентство отправить новую ссылку.</p>
        <p class="text-gray-400 text-sm mt-4">Ничего страшного не произошло.</p>
      </div>

      <div v-else-if="clientLinkOutcome === 'error'" class="flex flex-col items-center">
        <div class="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mb-4 text-red-600 text-2xl">×</div>
        <h2 class="text-xl font-bold text-gray-900">Не удалось подтвердить доступ</h2>
        <p class="text-gray-500 text-sm mt-2">Попробуйте открыть ссылку ещё раз. Если ошибка повторится, попросите агентство перевыпустить ссылку.</p>
      </div>

      <div v-else-if="error" class="flex flex-col items-center">
        <div class="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mb-4 text-red-600">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
        </div>
        <h2 class="text-xl font-bold text-gray-900">Ошибка подключения</h2>
        <p class="text-red-500 text-sm mb-6">{{ error }}</p>
        <router-link
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
import { ADMIRRA_PUBLIC_ORIGIN } from '../../config/admirraPublic'
import { oauthLoginProviderFromState } from '../../utils/oauthLoginState'

const route = useRoute()
const router = useRouter()
const toaster = useToaster()

const loading = ref(true)
const error = ref(null)
const clientLinkOutcome = ref(null)
const isClientLink = ref(false)

const hasVkClientLinkState = (state) => {
  if (typeof state !== 'string') return false
  const firstDot = state.indexOf('.')
  return firstDot > 0 && state.indexOf('.', firstDot + 1) === -1 && state.length - firstDot - 1 === 64
}

onMounted(async () => {
  const code = route.query.code
  const state = route.query.state

  // Если state принадлежит VK ID site-login, это не наш callback — он обрабатывается OAuthLoginCallback.vue
  if (oauthLoginProviderFromState(state) === 'vk') {
    sessionStorage.removeItem('oauth_site_login')
    router.replace({ path: '/auth/login/vk/callback', query: route.query })
    return
  }

  // Устаревший sessionStorage-флаг — тоже редиректим
  if (sessionStorage.getItem('oauth_site_login') === 'vk') {
    sessionStorage.removeItem('oauth_site_login')
    router.replace({ path: '/auth/login/vk/callback', query: route.query })
    return
  }

  const errorParam = route.query.error
  const errorDescription = route.query.error_description
  const user_id = route.query.user_id

  // Personal VK cabinet link: this callback is intentionally public. The
  // backend validates the HMAC state, TTL and one-time token; the browser only
  // renders a neutral completion page for a client without an AdMirra account.
  if (hasVkClientLinkState(state)) {
    isClientLink.value = true
    try {
      const { data } = await api.post('integrations/vk/link/callback', {
        code,
        state,
        error: errorParam,
        error_description: errorDescription,
      })
      clientLinkOutcome.value = ['authorized', 'declined', 'invalid'].includes(data?.outcome)
        ? data.outcome
        : 'error'
    } catch (err) {
      console.warn('[VKCallback] Client-link callback failed', err)
      clientLinkOutcome.value = 'error'
    } finally {
      loading.value = false
    }
    return
  }

  console.log('[VKCallback] Query params:', { code, state, errorParam, errorDescription, user_id })
  console.log('[VKCallback] Full query:', route.query)

  if (errorParam) {
    const vkAdsMessages = {
      invalid_client:
        'Неверный client_id. Проверьте VK_CLIENT_ID в .env и настройки приложения VK Ads.',
      invalid_redirect_uri: `redirect_uri не совпадает с настройками приложения. В VK Ads укажите: ${ADMIRRA_PUBLIC_ORIGIN}/auth/vk/callback`,
      invalid_scope:
        'Неверные права доступа. В .env задайте VK_ADS_OAUTH_SCOPE (как для интеграции) и те же scope в кабинете приложения.',
      access_denied: 'Вы отклонили запрос прав доступа. Попробуйте снова и разрешите доступ.',
      invalid_grant: 'Код авторизации истёк или уже использован. Начните вход заново.',
      invalid_request:
        errorDescription ||
        'Запрос отклонён VK Ads. Проверьте redirect_uri, client_id и scope.',
    }
    const errorMessage =
      vkAdsMessages[errorParam] ||
      errorDescription ||
      `Ошибка авторизации VK Ads: ${errorParam}`
    console.error('[VKCallback] VK OAuth error:', errorParam, errorDescription)
    error.value = errorMessage
    loading.value = false
    sessionStorage.removeItem('oauth_site_login')
    localStorage.removeItem('vk_auth_state')
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
