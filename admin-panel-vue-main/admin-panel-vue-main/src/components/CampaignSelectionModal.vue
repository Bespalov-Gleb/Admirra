<template>
  <div v-if="isOpen" class="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4 z-[200] animate-fade-in" @click.self="$emit('close')">
    <div class="bg-white rounded-[2rem] p-0.5 w-full max-w-sm shadow-[0_20px_50px_rgba(0,0,0,0.25)] transform transition-all animate-modal-in border border-gray-100 relative overflow-hidden">
      <div class="relative z-10 flex flex-col max-h-[70vh] p-6">
        <div class="flex items-center justify-between mb-6">
          <h3 class="text-lg font-black text-black tracking-tight uppercase">Выберите кампании</h3>
          <button @click="$emit('close')" class="p-2 bg-gray-50 text-gray-400 hover:text-black transition-all rounded-full">
            <XMarkIcon class="w-5 h-5" />
          </button>
        </div>

        <div v-if="loading" class="py-12 flex flex-col items-center justify-center gap-4">
          <div class="w-10 h-10 border-4 border-gray-100 border-t-blue-600 rounded-full animate-spin"></div>
          <span class="text-[10px] font-black text-gray-400 uppercase tracking-widest">Загрузка кампаний...</span>
        </div>

        <template v-else>
          <div class="mb-4 relative group">
            <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
              <MagnifyingGlassIcon class="h-4 w-4 text-gray-400 group-focus-within:text-blue-500 transition-colors" />
            </div>
            <input 
              type="text" 
              v-model="searchQuery"
              placeholder="Поиск кампании..."
              class="block w-full pl-11 pr-4 py-3 bg-gray-50 border-none rounded-2xl text-[13px] font-bold text-gray-900 placeholder-gray-400 focus:ring-2 focus:ring-blue-500/20 transition-all"
            >
          </div>

          <CustomScroll class="flex-grow">
            <div class="space-y-2 pr-1">
              <button 
                v-for="campaign in filteredCampaigns" 
              :key="campaign.id"
              @click="$emit('toggle', campaign.id)"
              class="w-full px-5 py-4 text-left flex items-center justify-between hover:bg-gray-50 rounded-2xl transition-all border border-transparent hover:border-gray-100 group"
              :class="{ 'bg-blue-50 border-blue-100': selectedIds.includes(campaign.id) }"
            >
              <div class="flex items-center gap-3">
                <div class="w-6 h-6 rounded-md border-2 flex items-center justify-center transition-all" :class="selectedIds.includes(campaign.id) ? 'bg-blue-600 border-blue-600' : 'border-gray-200 group-hover:border-gray-400'">
                  <CheckIcon v-if="selectedIds.includes(campaign.id)" class="w-4 h-4 text-white" stroke-width="4" />
                </div>
                <div class="text-left">
                  <span class="block text-[14px] font-black group-hover:text-black" :class="{ 'text-blue-600': selectedIds.includes(campaign.id) }">
                    {{ campaign.name }}
                  </span>
                  <div class="flex items-center gap-2">
                    <span class="text-[10px] text-gray-400 font-bold uppercase tracking-wider">ID: {{ campaign.external_id }}</span>
                    <span 
                      v-if="campaign.status" 
                      class="px-1.5 py-0.5 rounded-md text-[8px] font-black uppercase tracking-tighter shadow-sm"
                      :class="campaign.status === 'ACCEPTED' || campaign.status === 'ON' ? 'bg-green-100 text-green-600' : 'bg-gray-100 text-gray-400'"
                    >
                      {{ campaign.status === 'ACCEPTED' || campaign.status === 'ON' ? 'Активна' : 'Пауза' }}
                    </span>
                  </div>
                </div>
              </div>
            </button>

              <div v-if="filteredCampaigns.length === 0" class="py-12 text-center">
                <p class="text-[11px] font-black text-gray-400 uppercase tracking-widest">Кампании не найдены</p>
              </div>
            </div>
          </CustomScroll>
        </template>

        <div class="mt-6">
          <button 
            @click="$emit('close')"
            class="w-full py-4 bg-gray-900 text-white rounded-2xl font-black text-[12px] uppercase tracking-widest transition-all shadow-lg hover:-translate-y-0.5"
          >
            Готово
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { 
  XMarkIcon, 
  CheckIcon,
  MagnifyingGlassIcon
} from '@heroicons/vue/24/outline'
import CustomScroll from './ui/CustomScroll.vue'

const props = defineProps({
  isOpen: Boolean,
  campaigns: Array,
  selectedIds: Array,
  loading: Boolean
})

defineEmits(['close', 'toggle'])

const searchQuery = ref('')

const filteredCampaigns = computed(() => {
  if (!searchQuery.value) return props.campaigns
  const q = searchQuery.value.toLowerCase()
  return props.campaigns.filter(c => 
    (c.name && c.name.toLowerCase().includes(q)) || 
    (c.external_id && c.external_id.toString().includes(q))
  )
})
</script>

<style scoped>
.animate-fade-in {
  animation: fadeIn 0.3s ease-out;
}
.animate-modal-in {
  animation: modalIn 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}
@keyframes fadeIn {
  from { opacity: 0; backdrop-filter: blur(0); }
  to { opacity: 1; backdrop-filter: blur(4px); }
}
@keyframes modalIn {
  from { opacity: 0; transform: scale(0.95) translateY(20px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}
</style>
