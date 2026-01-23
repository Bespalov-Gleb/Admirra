<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50">
    <div class="bg-white p-8 rounded-2xl shadow-lg max-w-md w-full text-center space-y-4">
      <div v-if="loading" class="flex flex-col items-center">
        <div class="w-12 h-12 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mb-4"></div>
        <h2 class="text-xl font-bold text-gray-900">Подключение VK Ads...</h2>
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
  
  if (!code) {
    error.value = 'Код авторизации не найден'
    loading.value = false
    return
  }

  try {
    const redirectUri = `${window.location.origin}/auth/vk/callback`
    const clientName = localStorage.getItem('vk_auth_client_name')
    const clientId = localStorage.getItem('vk_auth_client_id')
    
    const payload = { 
      code, 
      redirect_uri: redirectUri,
      client_name: clientName,
      client_id: clientId // CRITICAL: Pass client_id to link integration to correct project
    }
    
    const response = await api.post('integrations/vk/exchange', payload)
    const integrationId = response.data.integration_id
    
    // Clean up localStorage
    localStorage.removeItem('vk_auth_client_name')
    localStorage.removeItem('vk_auth_client_id')
    toaster.success('VK Ads успешно подключен!')
    
    // Redirect to integration wizard step 2 (campaigns, profile selection removed)
    router.push(`/integrations/wizard?resume_integration_id=${integrationId}&initial_step=2`) 
  } catch (err) {
    console.error(err)
    error.value = err.response?.data?.detail || 'Не удалось завершить подключение'
  } finally {
    loading.value = false
  }
})
</script>
