<template>
  <div v-if="isOpen" class="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4 z-[100] animate-fade-in" @click.self="close">
    <div class="bg-white rounded-[2rem] p-0.5 w-full max-w-2xl shadow-2xl transform transition-all animate-modal-in border border-gray-100 relative overflow-hidden flex flex-col max-h-[90vh]">
      
      <!-- Header -->
      <div class="p-6 border-b border-gray-100 flex items-center justify-between bg-white z-10">
        <div>
          <h3 class="text-xl font-black text-black uppercase">Импорт клиентов агентства</h3>
          <p class="text-xs text-gray-400 font-medium mt-1">Выберите клиентов для подключения из Яндекс Директ</p>
        </div>
        <button @click="close" class="p-2 bg-gray-50 text-gray-400 hover:text-black rounded-xl transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
        </button>
      </div>

      <!-- Step 1: Auth -->
      <div v-if="step === 'AUTH'" class="p-10 flex flex-col items-center justify-center text-center flex-grow">
        <div class="w-16 h-16 bg-red-500 text-white rounded-2xl flex items-center justify-center font-black text-2xl mb-6 shadow-lg shadow-red-200">
          ЯD
        </div>
        <h4 class="text-lg font-bold mb-2">Авторизация представителя</h4>
        <p class="text-sm text-gray-500 max-w-sm mb-8">
          Чтобы загрузить список клиентов, войдите в аккаунт главного представителя агентства в Яндекс.Директ.
        </p>
        <button
          @click="initAuth"
          :disabled="loading"
          class="px-8 py-4 bg-[#FC3F1D] text-white rounded-2xl hover:bg-[#e63212] transition-all font-black text-xs uppercase tracking-widest shadow-xl hover:-translate-y-1"
        >
          <span v-if="loading">Ожидание...</span>
          <span v-else>Войти через Яндекс ID</span>
        </button>
      </div>

      <!-- Step 2: Selection -->
      <div v-else-if="step === 'SELECT'" class="flex-grow flex flex-col min-h-0">
        <div class="p-4 bg-gray-50 border-b border-gray-100 flex items-center gap-4">
            <input 
              v-model="searchQuery" 
              type="text" 
              placeholder="Поиск клиента..." 
              class="flex-grow px-4 py-2 bg-white border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-blue-100 outline-none"
            >
            <div class="text-xs font-bold text-gray-500 whitespace-nowrap">
                Выбрано: {{ selectedClients.length }}
            </div>
        </div>

        <div class="overflow-y-auto p-2 space-y-1 bg-white flex-grow">
            <div v-if="loadingClients" class="p-8 text-center text-gray-400 text-sm">
                Загрузка списка клиентов...
            </div>
            
            <label 
              v-for="client in filteredClients" 
              :key="client.login"
              class="flex items-center gap-4 p-3 hover:bg-gray-50 rounded-xl cursor-pointer transition-colors border border-transparent hover:border-blue-100 group"
              :class="{'bg-blue-50/30 border-blue-100': isSelected(client)}"
            >
              <div class="relative flex-shrink-0">
                <input 
                  type="checkbox" 
                  :value="client" 
                  v-model="selectedClients"
                  class="peer items-center justify-center appearance-none w-5 h-5 border-2 border-gray-300 rounded-md checked:bg-blue-600 checked:border-blue-600 focus:outline-none transition-colors"
                />
                 <svg class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-3.5 h-3.5 text-white pointer-events-none opacity-0 peer-checked:opacity-100 transition-opacity" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"></path></svg>
              </div>
              
              <div class="flex-grow min-w-0">
                <div class="flex items-center gap-2">
                    <span class="font-bold text-sm text-gray-800 truncate">{{ client.name }}</span>
                    <span class="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded font-mono">{{ client.login }}</span>
                </div>
                <p class="text-xs text-gray-400 mt-0.5 truncate">{{ client.fio }}</p>
              </div>
            </label>
        </div>

        <div class="p-4 border-t border-gray-100 bg-white flex gap-3">
            <button @click="step = 'AUTH'" class="px-6 py-3 border border-gray-200 rounded-xl text-xs font-bold uppercase text-gray-500 hover:bg-gray-50">Назад</button>
            <button 
              @click="importSelected" 
              :disabled="selectedClients.length === 0 || importing"
              class="flex-grow px-6 py-3 bg-gray-900 text-white rounded-xl text-xs font-black uppercase tracking-widest hover:bg-black disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
            >
                <span v-if="importing">Импорт ({{ importProgress }}/{{ selectedClients.length }})...</span>
                <span v-else>Импортировать ({{ selectedClients.length }})</span>
            </button>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../api/axios'

const props = defineProps({
  isOpen: Boolean
})

const emit = defineEmits(['update:isOpen', 'success'])

const step = ref('AUTH') // AUTH, SELECT
const loading = ref(false)
const loadingClients = ref(false)
const importing = ref(false)
const importProgress = ref(0)
const clients = ref([])
const selectedClients = ref([])
const searchQuery = ref('')
const accessToken = ref('')

const filteredClients = computed(() => {
    if (!searchQuery.value) return clients.value
    const q = searchQuery.value.toLowerCase()
    return clients.value.filter(c => 
        c.name.toLowerCase().includes(q) || 
        c.login.toLowerCase().includes(q) ||
        (c.fio && c.fio.toLowerCase().includes(q))
    )
})

const isSelected = (client) => {
    return selectedClients.value.some(c => c.login === client.login)
}

const close = () => {
  emit('update:isOpen', false)
  // Reset state after delay
  setTimeout(() => {
      step.value = 'AUTH'
      selectedClients.value = []
      clients.value = []
  }, 300)
}

const initAuth = async () => {
    loading.value = true
    try {
        // We use a special redirect URI that this component will "catch" if we were using a real router flow.
        // But since we are hacking it a bit, let's use the popup method or standard redirect.
        // Problem: Standard redirect reloads the page.
        // Solution: Use the same flow as UnifiedConnectModal.
        
        // Wait! The user needs to get the token. 
        // Let's rely on the existing callback logic but store a flag "is_agency_import" in localStorage.
        localStorage.setItem('is_agency_import', 'true')
        
        const redirectUri = `${window.location.origin}/auth/yandex/callback`
        const { data } = await api.get(`integrations/yandex/auth-url?redirect_uri=${encodeURIComponent(redirectUri)}`)
        if (data.url) {
            window.location.href = data.url
        }
    } catch (e) {
        console.error(e)
        loading.value = false
    }
}

// Function to call from the parent/callback handler to inject the token
const handleToken = async (token) => {
    accessToken.value = token
    step.value = 'SELECT'
    loadingClients.value = true
    
    try {
        const { data } = await api.get(`integrations/yandex/agency-clients?access_token=${token}`)
        clients.value = data
    } catch (e) {
        console.error("Failed to load clients", e)
        alert("Не удалось загрузить список клиентов. Возможно, это не агентский аккаунт.")
        close()
    } finally {
        loadingClients.value = false
    }
}

const importSelected = async () => {
    importing.value = true
    importProgress.value = 0
    
    try {
        const payload = {
            access_token: accessToken.value,
            clients: selectedClients.value.map(c => ({
                login: c.login,
                name: c.name
            }))
        }
        
        await api.post('integrations/batch-import', payload)
        
        emit('success')
        close()
        window.location.reload() // Reload to show new projects
    } catch (e) {
        console.error(e)
        alert("Ошибка импорта")
    } finally {
        importing.value = false
    }
}

// Expose handleToken to be called by parent
defineExpose({ handleToken })
</script>

<style scoped>
.animate-fade-in { animation: fadeIn 0.2s ease-out; }
.animate-modal-in { animation: modalIn 0.3s cubic-bezier(0.16, 1, 0.3, 1); }

@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
@keyframes modalIn { from { opacity: 0; transform: scale(0.98) translateY(10px); } to { opacity: 1; transform: scale(1) translateY(0); } }
</style>
