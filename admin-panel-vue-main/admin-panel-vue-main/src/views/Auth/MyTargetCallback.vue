<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50">
    <div class="bg-white p-8 rounded-2xl shadow-lg max-w-md w-full text-center space-y-4">
      <div v-if="loading" class="flex flex-col items-center">
        <div class="w-12 h-12 border-4 border-purple-200 border-t-purple-600 rounded-full animate-spin mb-4"></div>
        <h2 class="text-xl font-bold text-gray-900">Подключение myTarget...</h2>
        <p class="text-gray-500">Пожалуйста, подождите, мы настраиваем интеграцию.</p>
      </div>

      <div v-else-if="error" class="flex flex-col items-center">
        <div class="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mb-4 text-red-600">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
        </div>
        <h2 class="text-xl font-bold text-gray-900">Ошибка подключения</h2>
        <p class="text-red-500 text-sm mb-6">{{ error }}</p>
        <router-link to="/projects/create" class="px-6 py-2 bg-gray-900 text-white rounded-lg hover:bg-black transition-colors">
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

const route = useRoute()
const router = useRouter()
const toaster = useToaster()

const loading = ref(true)
const error = ref(null)

onMounted(async () => {
  const code = route.query.code
  const state = route.query.state
  const errorParam = route.query.error
  const errorDescription = route.query.error_description
  
  console.log('[MyTargetCallback] Query params:', { code, state, errorParam, errorDescription })
  console.log('[MyTargetCallback] Full query:', route.query)
  
  // Проверяем ошибки от myTarget OAuth
  if (errorParam) {
    const errorMessages = {
      'invalid_client': 'Неверный client_id или client_secret. Проверьте настройки приложения в myTarget и значения в .env файле.',
      'invalid_redirect_uri': 'redirect_uri не совпадает с настройками приложения. В myTarget должен быть указан правильный redirect_uri.',
      'invalid_scope': 'Неверные права доступа. Проверьте настройки приложения.',
      'access_denied': 'Вы отклонили запрос прав доступа. Попробуйте авторизоваться снова и разрешите доступ.',
      'invalid_grant': 'Код авторизации истек. Попробуйте авторизоваться заново.',
    }
    
    const errorMessage = errorMessages[errorParam] || errorDescription || `Ошибка авторизации myTarget: ${errorParam}`
    console.error('[MyTargetCallback] myTarget OAuth error:', errorParam, errorDescription)
    error.value = errorMessage
    loading.value = false
    // Clean up localStorage
    localStorage.removeItem('mytarget_auth_state')
    return
  }
  
  // Проверка CSRF защиты: сравниваем state из callback с сохраненным
  const savedState = localStorage.getItem('mytarget_auth_state')
  if (state && savedState && state !== savedState) {
    console.error('[MyTargetCallback] State mismatch:', { received: state, saved: savedState })
    error.value = 'Ошибка безопасности: неверный state параметр. Попробуйте авторизоваться заново.'
    loading.value = false
    localStorage.removeItem('mytarget_auth_state')
    return
  }
  
  if (!code) {
    console.error('[MyTargetCallback] No authorization code in query params')
    error.value = 'Код авторизации не найден. Возможно, вы не завершили процесс авторизации или произошла ошибка.'
    loading.value = false
    localStorage.removeItem('mytarget_auth_state')
    return
  }

  try {
    const redirectUri = `${window.location.origin}/auth/mytarget/callback`
    const clientName = localStorage.getItem('mytarget_auth_client_name')
    const clientId = localStorage.getItem('mytarget_auth_client_id')
    
    console.log('[MyTargetCallback] Exchanging code for token...', { 
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
    
    const response = await api.post('integrations/mytarget/exchange', payload)
    console.log('[MyTargetCallback] Token exchange successful:', response.data)
    const integrationId = response.data.integration_id
    
    // Clean up localStorage
    localStorage.removeItem('mytarget_auth_client_name')
    localStorage.removeItem('mytarget_auth_client_id')
    localStorage.removeItem('mytarget_auth_state')
    toaster.success('myTarget успешно подключен!')
    
    // Redirect to integration wizard step 2
    router.push(`/integrations/wizard?resume_integration_id=${integrationId}&initial_step=2`) 
  } catch (err) {
    console.error('[MyTargetCallback] Token exchange error:', err)
    console.error('[MyTargetCallback] Error response:', err.response)
    console.error('[MyTargetCallback] Error data:', err.response?.data)
    
    // Более детальная обработка ошибок
    let errorMessage = 'Не удалось завершить подключение'
    if (err.response?.data?.detail) {
      errorMessage = err.response.data.detail
    } else if (err.response?.data?.error) {
      errorMessage = `Ошибка myTarget: ${err.response.data.error}`
      if (err.response.data.error_description) {
        errorMessage += ` - ${err.response.data.error_description}`
      }
    } else if (err.message) {
      errorMessage = `Ошибка: ${err.message}`
    }
    
    error.value = errorMessage
    localStorage.removeItem('mytarget_auth_state')
  } finally {
    loading.value = false
  }
})
</script>

