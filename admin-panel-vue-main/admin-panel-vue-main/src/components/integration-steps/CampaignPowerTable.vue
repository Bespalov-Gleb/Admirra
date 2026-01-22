<template>
  <div class="space-y-4">
    <!-- Loading Banner -->
    <div v-if="loading" class="bg-blue-50 border border-blue-200 rounded-2xl p-4 flex items-center gap-3">
      <div class="w-8 h-8 border-3 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
      <div>
        <p class="text-sm font-bold text-blue-900">Синхронизация данных...</p>
        <p class="text-xs text-blue-600">Загружаем кампании из Яндекс.Директ</p>
      </div>
    </div>

    <!-- Filters Header -->
    <div class="flex flex-col md:flex-row gap-4 items-center">
      <div class="relative group flex-grow w-full">
        <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
          <MagnifyingGlassIcon class="h-4 w-4 text-gray-400 group-focus-within:text-blue-500 transition-colors" />
        </div>
        <input 
          type="text" 
          v-model="searchQuery"
          placeholder="Поиск по названию или ID..."
          class="block w-full pl-11 pr-4 py-3 bg-white border border-gray-100 rounded-2xl text-[13px] font-bold text-gray-900 placeholder-gray-400 focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all shadow-sm"
        >
      </div>

      <div class="flex items-center gap-2 w-full md:w-auto">
        <!-- Status Filter -->
        <div class="relative flex-grow md:w-48">
          <select 
            v-model="statusFilter"
            class="block w-full px-4 py-3 bg-white border border-gray-100 rounded-2xl text-[12px] font-black text-gray-700 appearance-none focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all cursor-pointer shadow-sm uppercase tracking-tight"
          >
            <option value="ALL">Все статусы</option>
            <option value="ON">Активные</option>
            <option value="SUSPENDED">Пауза</option>
            <option value="ENDED">Завершены</option>
            <option value="ARCHIVED">Архив</option>
          </select>
          <div class="absolute inset-y-0 right-0 pr-4 flex items-center pointer-events-none">
            <ChevronDownIcon class="h-4 w-4 text-gray-400" />
          </div>
        </div>

        <!-- Type Filter -->
        <div class="relative flex-grow md:w-48">
          <select 
            v-model="typeFilter"
            class="block w-full px-4 py-3 bg-white border border-gray-100 rounded-2xl text-[12px] font-black text-gray-700 appearance-none focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all cursor-pointer shadow-sm uppercase tracking-tight"
          >
            <option value="ALL">Все типы</option>
            <option value="TEXT_CAMPAIGN">Текстовые</option>
            <option value="DYNAMIC_TEXT_CAMPAIGN">Динамические</option>
            <option value="MOBILE_APP_CAMPAIGN">Моб. прилож.</option>
            <option value="SMART_CAMPAIGN">Смарт-баннеры</option>
          </select>
          <div class="absolute inset-y-0 right-0 pr-4 flex items-center pointer-events-none">
            <ChevronDownIcon class="h-4 w-4 text-gray-400" />
          </div>
        </div>

      </div>
    </div>

    <!-- Quick Action Buttons -->
    <div class="flex flex-wrap gap-2">
      <button 
        @click="selectActive"
        class="inline-flex items-center gap-1.5 px-3 py-2 bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200 rounded-xl text-[10px] font-black uppercase tracking-wider text-green-700 hover:from-green-100 hover:to-emerald-100 transition-all shadow-sm"
      >
        <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd"/>
        </svg>
        Только активные
      </button>
    </div>

    <!-- Power Table -->
    <div class="bg-white border border-gray-200 rounded-2xl overflow-hidden shadow-sm">
      <table class="w-full text-left border-collapse">
        <thead>
          <tr class="bg-gray-50 border-b border-gray-100">
            <th class="w-10 px-4 py-3">
              <div 
                @click="toggleSelectAllFiltered"
                class="w-5 h-5 rounded-md border-2 flex items-center justify-center transition-all bg-white cursor-pointer" 
                :class="isAllFilteredSelected ? 'bg-blue-600 border-blue-600' : 'border-gray-200 hover:border-blue-400'"
              >
                <CheckIcon v-if="isAllFilteredSelected" class="w-3.5 h-3.5 text-white" stroke-width="4" />
                <div v-else-if="isAnyFilteredSelected" class="w-2 h-0.5 bg-gray-400 rounded-full"></div>
              </div>
            </th>
            <th class="px-3 py-3 text-[10px] font-black text-gray-400 uppercase tracking-widest leading-tight">Статус</th>
            <th class="px-3 py-3 text-[10px] font-black text-gray-400 uppercase tracking-widest leading-tight">Название / ID</th>
          </tr>
        </thead>
        <tbody>
          <template v-if="loading">
            <tr v-for="i in 5" :key="i" class="border-b border-gray-50">
              <td class="px-4 py-4"><Skeleton width="5" height="5" rounded="md" /></td>
              <td class="px-3 py-4"><Skeleton width="10" height="3" /></td>
              <td class="px-3 py-4"><Skeleton width="32" height="4" /></td>
            </tr>
          </template>
          
          <template v-else>
            <tr 
              v-for="campaign in filteredCampaigns" 
            :key="campaign.id"
            class="border-b border-gray-50 last:border-none group hover:bg-blue-50/30 transition-all cursor-pointer"
            :class="{ 'bg-blue-50/50': selectedIds.includes(campaign.id) }"
            @click="$emit('toggle', campaign.id)"
          >
            <td class="px-4 py-3">
              <div class="w-5 h-5 rounded-md border-2 flex items-center justify-center transition-all bg-white" :class="selectedIds.includes(campaign.id) ? 'bg-blue-600 border-blue-600' : 'border-gray-200 group-hover:border-gray-400'">
                <CheckIcon v-if="selectedIds.includes(campaign.id)" class="w-3.5 h-3.5 text-white" stroke-width="4" />
              </div>
            </td>
            <td class="px-3 py-3">
              <div class="flex items-center gap-2">
                 <div 
                  class="w-2 h-2 rounded-full relative"
                  :class="stateDotClass(campaign.state)"
                >
                  <div v-if="campaign.state === 'ON'" class="absolute inset-0 rounded-full bg-green-500 animate-ping opacity-25"></div>
                </div>
                <span 
                  class="px-1.5 py-0.5 rounded-md text-[8px] font-black uppercase tracking-tighter shadow-sm whitespace-nowrap"
                  :class="stateBadgeClass(campaign.state)"
                >
                  {{ stateLabel(campaign.state) }}
                </span>
              </div>
            </td>
            <td class="px-3 py-3">
              <div class="flex flex-col">
                <div class="flex items-start gap-2 mb-0.5">
                  <span class="text-[11px] font-black text-gray-800 line-clamp-1 leading-tight group-hover:text-blue-600 transition-colors flex-grow">{{ campaign.name }}</span>
                  
                </div>
                <span class="text-[9px] text-gray-400 font-bold uppercase tracking-wider">ID: {{ campaign.external_id || campaign.id }}</span>
              </div>
            </td>
          </tr>
        </template>
        
        <tr v-if="!loading && filteredCampaigns.length === 0">
            <td colspan="3" class="py-12 text-center">
              <div class="flex flex-col items-center gap-3">
                <div class="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center">
                  <svg class="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <div>
                  <p class="text-sm font-bold text-gray-600 mb-1">Кампании не найдены</p>
                  <p class="text-xs text-gray-400">Данные синхронизируются в фоне. Попробуйте обновить через несколько секунд.</p>
                </div>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ChevronDownIcon, MagnifyingGlassIcon } from '@heroicons/vue/20/solid'
import { CheckIcon, ChartBarIcon } from '@heroicons/vue/24/outline'
import Skeleton from '../ui/Skeleton.vue'

const props = defineProps({
  campaigns: Array,
  selectedIds: Array,
  loading: Boolean,
  currency: {
    type: String,
    default: 'RUB'
  }
})

const emit = defineEmits(['toggle', 'bulkSelect', 'bulkDeselect'])

const searchQuery = ref('')
const statusFilter = ref('ALL')
const typeFilter = ref('ALL')

const formatMoney = (val) => {
  return new Intl.NumberFormat('ru-RU', { 
    style: 'currency', 
    currency: props.currency || 'RUB', 
    maximumFractionDigits: 0 
  }).format(val)
}

// Map backend state codes to human‑readable labels and styles
const stateLabel = (state) => {
  switch (state) {
    case 'ON':
      return 'Активна'
    case 'OFF':
      return 'Остановлена'
    case 'SUSPENDED':
      return 'Пауза'
    case 'ENDED':
      return 'Завершена'
    case 'ARCHIVED':
      return 'Архивная'
    default:
      return 'Неизвестно'
  }
}

const stateBadgeClass = (state) => {
  switch (state) {
    case 'ON':
      return 'bg-green-50 text-green-600 border border-green-100'
    case 'SUSPENDED':
      return 'bg-yellow-50 text-yellow-600 border border-yellow-100'
    case 'ENDED':
      return 'bg-gray-50 text-gray-500 border border-gray-200'
    case 'ARCHIVED':
      return 'bg-gray-100 text-gray-400 border border-gray-200'
    case 'OFF':
      return 'bg-gray-50 text-gray-400 border border-gray-100'
    default:
      return 'bg-gray-50 text-gray-400 border border-gray-100'
  }
}

const stateDotClass = (state) => {
  switch (state) {
    case 'ON':
      return 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.4)]'
    case 'SUSPENDED':
      return 'bg-yellow-400 shadow-[0_0_8px_rgba(250,204,21,0.5)]'
    case 'ARCHIVED':
      return 'bg-gray-300'
    case 'ENDED':
      return 'bg-gray-400'
    case 'OFF':
      return 'bg-gray-300'
    default:
      return 'bg-gray-300'
  }
}

const filteredCampaigns = computed(() => {
  let list = props.campaigns || []
  
  // Status Filter
  if (statusFilter.value !== 'ALL') {
    list = list.filter(c => c.state === statusFilter.value)
  }

  // Type Filter
  if (typeFilter.value !== 'ALL') {
    list = list.filter(c => c.type === typeFilter.value)
  }


  // Search Filter
  if (!searchQuery.value) return list
  const q = searchQuery.value.toLowerCase()
  return list.filter(c => 
    (c.name && c.name.toLowerCase().includes(q)) || 
    (c.external_id && c.external_id.toString().includes(q)) ||
    (c.id && c.id.toString().includes(q))
  )
})
const isAllFilteredSelected = computed(() => {
  if (filteredCampaigns.value.length === 0) return false
  return filteredCampaigns.value.every(c => props.selectedIds.includes(c.id))
})

const isAnyFilteredSelected = computed(() => {
  return filteredCampaigns.value.some(c => props.selectedIds.includes(c.id))
})

const toggleSelectAllFiltered = () => {
  const ids = filteredCampaigns.value.map(c => c.id)
  if (isAllFilteredSelected.value) {
    emit('bulkDeselect', ids)
  } else {
    emit('bulkSelect', ids)
  }
}

const formatStrategy = (s) => {
  if (!s) return 'АВТОМАТИЧЕСКАЯ'
  const labels = {
    'AVERAGE_CPA': 'СРЕДНЯЯ ЦЕНА КОНВЕРСИИ',
    'AVERAGE_CPC': 'СРЕДНЯЯ ЦЕНА КЛИКА',
    'WEEKLY_BUDGET': 'НЕДЕЛЬНЫЙ БЮДЖЕТ',
    'HIGHEST_RETURN_ON_AD_SPEND': 'МАКСИМАЛЬНЫЙ ДОХОД',
    'UNKNOWN': 'ПО УМОЛЧАНИЮ'
  }
  return labels[s] || s.replace(/_/g, ' ')
}

// Quick action function
const selectActive = () => {
  // Select only active campaigns
  const active = filteredCampaigns.value.filter(c => c.state === 'ON')
  const ids = active.map(c => c.id)
  emit('bulkSelect', ids)
}
</script>
