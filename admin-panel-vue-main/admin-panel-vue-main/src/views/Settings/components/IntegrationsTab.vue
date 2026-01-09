<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h2 class="text-xl font-semibold text-gray-900">Активные интеграции</h2>
      <button 
        @click="showAddModal = true"
        class="px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors text-sm font-medium"
      >
        Добавить интеграцию
      </button>
    </div>

    <!-- Список интеграций -->
    <div v-if="loading" class="flex justify-center py-12">
      <div class="w-8 h-8 border-4 border-gray-900 border-t-transparent rounded-full animate-spin"></div>
    </div>
    
    <div v-else-if="integrations.length === 0" class="text-center py-12 border-2 border-dashed border-gray-200 rounded-xl">
      <p class="text-gray-500">У вас пока нет активных интеграций</p>
    </div>

    <div v-else class="grid grid-cols-1 gap-4">
      <div v-for="item in integrations" :key="item.id" class="p-4 border border-gray-200 rounded-xl bg-gray-50 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div class="flex items-center gap-3 min-w-0">
          <div class="w-12 h-12 flex-shrink-0 bg-white rounded-lg flex items-center justify-center border border-gray-100 overflow-hidden px-1">
            <span class="font-bold text-[10px] uppercase truncate text-gray-500">{{ item.platform }}</span>
          </div>
          <div class="min-w-0">
            <p class="font-semibold text-gray-900 truncate">
              {{ platformLabels[item.platform] || item.platform }}
            </p>
            <div class="flex items-center gap-2 mt-1">
              <p class="text-xs text-gray-500 truncate">ID: {{ item.account_id || 'Не указан' }}</p>
              <div v-if="item.sync_status" class="flex items-center gap-1">
                <span class="text-[10px] px-1.5 py-0.5 rounded-full font-bold uppercase tracking-tighter" :class="{
                  'bg-green-100 text-green-700': item.sync_status === 'success',
                  'bg-red-100 text-red-700': item.sync_status === 'failed',
                  'bg-yellow-100 text-yellow-700': item.sync_status === 'pending',
                  'bg-gray-100 text-gray-500': item.sync_status === 'never' || !item.sync_status
                }">
                  {{ item.sync_status === 'success' ? 'OK' : (item.sync_status === 'failed' ? 'ERROR' : (item.sync_status === 'pending' ? '...' : 'NONE')) }}
                </span>
              </div>
            </div>
          </div>
        </div>
        <div class="flex items-center gap-4 sm:flex-shrink-0">
          <button 
            @click="handleSync(item.id)" 
            :disabled="syncingId === item.id"
            class="text-blue-600 hover:text-blue-700 text-sm font-semibold disabled:opacity-50 transition-colors"
          >
            {{ syncingId === item.id ? 'Синхронизация...' : 'Синхронизировать' }}
          </button>
          <button 
            @click="deleteIntegration(item.id)" 
            class="text-red-500 hover:text-red-600 text-sm font-semibold transition-colors"
          >
            Удалить
          </button>
        </div>
      </div>
    </div>

    <!-- Модальное окно добавления (Единое) -->
    <UnifiedConnectModal
      v-model:is-open="showAddModal"
      @success="fetchIntegrations"
    />

    <!-- Модальное окно импорта агентства -->
    <AgencyImportModal
      ref="agencyModalRef"
      v-model:is-open="isAgencyModalOpen"
      @success="fetchIntegrations"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '../../../api/axios'
import UnifiedConnectModal from '../../../components/UnifiedConnectModal.vue'
import AgencyImportModal from '../../../components/AgencyImportModal.vue'
import { useToaster } from '../../../composables/useToaster'

const integrations = ref([])
const loading = ref(true)
const showAddModal = ref(false)
const syncingId = ref(null)

const platformLabels = {
  'YANDEX_DIRECT': 'Яндекс.Директ',
  'VK_ADS': 'VK Ads',
  'YANDEX_METRIKA': 'Яндекс.Метрика'
}

const isAgencyModalOpen = ref(false)
const agencyModalRef = ref(null)
const route = useRoute()

const fetchIntegrations = async () => {
  loading.value = true
  try {
    const response = await api.get('integrations/')
    integrations.value = response.data
  } catch (error) {
    console.error('Error fetching integrations:', error)
  } finally {
    loading.value = false
  }
}

const deleteIntegration = async (id) => {
  if (!confirm('Вы уверены, что хотите удалить эту интеграцию?')) return
  try {
    await api.delete(`integrations/${id}`)
    fetchIntegrations()
  } catch (error) {
    console.error('Error deleting integration:', error)
  }
}

const handleSync = async (id) => {
  syncingId.value = id
  const toaster = useToaster()
  try {
    await api.post(`integrations/${id}/sync`, { days: 730 })
    toaster.success('Синхронизация завершена успешно!')
    fetchIntegrations() // Refresh to show new status
  } catch (error) {
    toaster.error('Ошибка при синхронизации: ' + (error.response?.data?.detail || error.message))
  } finally {
    syncingId.value = null
  }
}

onMounted(() => {
  fetchIntegrations()
  
  if (route.query.trigger_agency_import === '1') {
    const token = localStorage.getItem('temp_agency_token')
    if (token) {
      isAgencyModalOpen.value = true
      setTimeout(() => {
        if (agencyModalRef.value) {
          agencyModalRef.value.handleToken(token)
        }
      }, 100)
    }
    // Clean up
    window.history.replaceState({}, '', window.location.pathname)
  }
})
</script>

<style scoped>
.animate-fade-in {
  animation: fadeIn 0.2s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
</style>
