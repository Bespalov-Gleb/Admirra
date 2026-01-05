<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50">
    <div class="bg-white p-8 rounded-2xl shadow-lg max-w-md w-full text-center space-y-4">
      <div v-if="loading" class="flex flex-col items-center">
        <div class="w-12 h-12 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mb-4"></div>
        <h2 class="text-xl font-bold text-gray-900">Подключение Яндекс Директ...</h2>
        <p class="text-gray-500">Пожалуйста, подождите, мы настраиваем интеграцию.</p>
      </div>

      <div v-else-if="error" class="flex flex-col items-center">
        <div class="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mb-4 text-red-600">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
        </div>
        <h2 class="text-xl font-bold text-gray-900">Ошибка подключения</h2>
        <p class="text-red-500 text-sm mb-6">{{ error }}</p>
        <router-link to="/settings" class="px-6 py-2 bg-gray-900 text-white rounded-lg hover:bg-black transition-colors">
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

const route = useRoute()
const router = useRouter()
const toaster = useToaster()

const loading = ref(true)
const error = ref(null)

onMounted(async () => {
  const code = route.query.code
  
  if (!code) {
    error.value = 'Код авторизации не найден'
    loading.value = false
    return
  }

  try {
    // Determine redirect URI used during auth
    const redirectUri = `${window.location.origin}/auth/yandex/callback`
    
    // Retrieve client name if saved
    const clientName = localStorage.getItem('yandex_auth_client_name')
    
    const payload = { 
      code, 
      redirect_uri: redirectUri,
      client_name: clientName // Pass it to backend
    }
    
    const response = await api.post('integrations/yandex/exchange', payload)
    
    // Clean up
    localStorage.removeItem('yandex_auth_client_name')
    
    // AGENCY MODE: If this was an agency import, redirect back with a flag
    if (localStorage.getItem('is_agency_import') === 'true') {
        localStorage.removeItem('is_agency_import')
        localStorage.setItem('temp_yandex_agency_token', response.data.access_token)
        router.push('/dashboard/general-3?agency_import=success')
        return
    }

    // Show success message
    toaster.success('Яндекс Директ успешно подключен!')
    
    // Redirect to the main dashboard
    router.push('/dashboard/general-3') 
  } catch (err) {
    console.error(err)
    error.value = err.response?.data?.detail || 'Не удалось завершить подключение'
  } finally {
    loading.value = false
  }
})
</script>
