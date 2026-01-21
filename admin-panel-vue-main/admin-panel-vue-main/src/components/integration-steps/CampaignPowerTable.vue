<template>
  <div class="space-y-4">
    <!-- Loading Banner -->
    <div v-if="loading" class="bg-blue-50 border border-blue-200 rounded-2xl p-4 flex items-center gap-3">
      <div class="w-8 h-8 border-3 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
      <div>
        <p class="text-sm font-bold text-blue-900">Синхронизация данных...</p>
        <p class="text-xs text-blue-600">Загружаем кампании и статистику за последние 7 дней</p>
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

        <!-- Stats Toggle -->
        <button 
          @click="showOnlyWithStats = !showOnlyWithStats"
          class="px-4 py-3 border rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all shadow-sm flex items-center gap-2 whitespace-nowrap"
          :class="showOnlyWithStats ? 'bg-blue-600 border-blue-600 text-white' : 'bg-white border-gray-100 text-gray-400 hover:text-gray-600 hover:border-gray-200'"
        >
          <ChartBarIcon class="w-3.5 h-3.5" />
          Статистика
        </button>
      </div>
    </div>

    <!-- NEW: Quick Action Buttons -->
    <div class="flex flex-wrap gap-2">
      <button 
        @click="selectRecommended"
        class="inline-flex items-center gap-1.5 px-3 py-2 bg-gradient-to-r from-purple-50 to-violet-50 border border-purple-200 rounded-xl text-[10px] font-black uppercase tracking-wider text-purple-700 hover:from-purple-100 hover:to-violet-100 transition-all shadow-sm"
      >
        <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
        </svg>
        Выбрать рекомендуемые
      </button>
      
      <button 
        @click="selectActive"
        class="inline-flex items-center gap-1.5 px-3 py-2 bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200 rounded-xl text-[10px] font-black uppercase tracking-wider text-green-700 hover:from-green-100 hover:to-emerald-100 transition-all shadow-sm"
      >
        <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd"/>
        </svg>
        Только активные
      </button>
      
      <button 
        @click="selectByBudget"
        class="inline-flex items-center gap-1.5 px-3 py-2 bg-gradient-to-r from-blue-50 to-cyan-50 border border-blue-200 rounded-xl text-[10px] font-black uppercase tracking-wider text-blue-700 hover:from-blue-100 hover:to-cyan-100 transition-all shadow-sm"
      >
        <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
          <path d="M8.433 7.418c.155-.103.346-.196.567-.267v1.698a2.305 2.305 0 01-.567-.267C8.07 8.34 8 8.114 8 8c0-.114.07-.34.433-.582zM11 12.849v-1.698c.22.071.412.164.567.267.364.243.433.468.433.582 0 .114-.07.34-.433.582a2.305 2.305 0 01-.567.267z"/>
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-13a1 1 0 10-2 0v.092a4.535 4.535 0 00-1.676.662C6.602 6.234 6 7.009 6 8c0 .99.602 1.765 1.324 2.246.48.32 1.054.545 1.676.662v1.941c-.391-.127-.68-.317-.843-.504a1 1 0 10-1.51 1.31c.562.649 1.413 1.076 2.353 1.253V15a1 1 0 102 0v-.092a4.535 4.535 0 001.676-.662C13.398 13.766 14 12.991 14 12c0-.99-.602-1.765-1.324-2.246A4.535 4.535 0 0011 9.092V7.151c.391.127.68.317.843.504a1 1 0 101.511-1.31c-.563-.649-1.413-1.076-2.354-1.253V5z" clip-rule="evenodd"/>
        </svg>
        С бюджетом > 10,000
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
            <th class="px-3 py-3 text-[10px] font-black text-gray-400 uppercase tracking-widest leading-tight text-right">Показы</th>
            <th class="px-3 py-3 text-[10px] font-black text-gray-400 uppercase tracking-widest leading-tight text-right">Клики</th>
            <th class="px-3 py-3 text-[10px] font-black text-gray-400 uppercase tracking-widest leading-tight text-right">Расход</th>
            <th class="px-3 py-3 text-[10px] font-black text-gray-400 uppercase tracking-widest leading-tight text-right">Конв.</th>
            <th class="px-3 py-3 text-[10px] font-black text-gray-400 uppercase tracking-widest leading-tight text-right">CTR</th>
          </tr>
        </thead>
        <tbody>
          <template v-if="loading">
            <tr v-for="i in 5" :key="i" class="border-b border-gray-50">
              <td class="px-4 py-4"><Skeleton width="5" height="5" rounded="md" /></td>
              <td class="px-3 py-4"><Skeleton width="10" height="3" /></td>
              <td class="px-3 py-4"><Skeleton width="32" height="4" /></td>
              <td class="px-3 py-4" v-for="j in 5" :key="j"><Skeleton width="12" height="3" class="ml-auto" /></td>
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
                  
                  <!-- ENHANCED: Performance Badges with Icons -->
                  <div class="flex flex-wrap gap-1 items-center">
                    <!-- Top CTR Badge -->
                    <span 
                      v-if="getCTR(campaign) > 5" 
                      class="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-gradient-to-r from-green-50 to-emerald-50 text-green-700 text-[7px] font-black uppercase rounded-md border border-green-200 shadow-sm"
                      title="CTR выше 5%"
                    >
                      <svg class="w-2.5 h-2.5" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M2 10.5a1.5 1.5 0 113 0v6a1.5 1.5 0 01-3 0v-6zM6 10.333v5.43a2 2 0 001.106 1.79l.05.025A4 4 0 008.943 18h5.416a2 2 0 001.962-1.608l1.2-6A2 2 0 0015.56 8H12V4a2 2 0 00-2-2 1 1 0 00-1 1v.667a4 4 0 01-.8 2.4L6.8 7.933a4 4 0 00-.8 2.4z"/>
                      </svg>
                      Top CTR
                    </span>
                    
                    <!-- Эффективно Badge (High Conversion) -->
                    <span 
                      v-if="campaign.conversions > 0 && getConversionRate(campaign) > 3" 
                      class="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-gradient-to-r from-purple-50 to-violet-50 text-purple-700 text-[7px] font-black uppercase rounded-md border border-purple-200 shadow-sm"
                      title="Коэффициент конверсии выше 3%"
                    >
                      <svg class="w-2.5 h-2.5" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
                      </svg>
                      Эффективно
                    </span>
                    
                    <!-- Охват + Badge (High Impressions) -->
                    <span 
                      v-if="campaign.impressions > 100000" 
                      class="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-gradient-to-r from-blue-50 to-cyan-50 text-blue-700 text-[7px] font-black uppercase rounded-md border border-blue-200 shadow-sm"
                      title="Более 100,000 показов"
                    >
                      <svg class="w-2.5 h-2.5" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M10 12a2 2 0 100-4 2 2 0 000 4z"/>
                        <path fill-rule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clip-rule="evenodd"/>
                      </svg>
                      Охват +
                    </span>
                    
                    <!-- NEW: Требует внимания Badge (Low Performance) -->
                    <span 
                      v-if="needsAttention(campaign)" 
                      class="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-gradient-to-r from-yellow-50 to-amber-50 text-yellow-700 text-[7px] font-black uppercase rounded-md border border-yellow-200 shadow-sm animate-pulse"
                      title="Низкий CTR при высоких расходах"
                    >
                      <svg class="w-2.5 h-2.5" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
                      </svg>
                      Требует внимания
                    </span>
                  </div>
                </div>
                <span class="text-[9px] text-gray-400 font-bold uppercase tracking-wider">ID: {{ campaign.external_id || campaign.id }}</span>
              </div>
            </td>
            
            <td class="px-3 py-3 text-right">
              <span class="text-[11px] font-bold text-gray-600">{{ campaign.impressions || 0 }}</span>
            </td>
            <td class="px-3 py-3 text-right">
              <span class="text-[11px] font-bold text-gray-600">{{ campaign.clicks || 0 }}</span>
            </td>
            <td class="px-3 py-3 text-right">
              <span class="text-[11px] font-black text-gray-900">{{ formatMoney(campaign.cost || 0) }}</span>
            </td>
            <td class="px-3 py-3 text-right">
              <span class="text-[11px] font-black text-blue-600">{{ campaign.conversions || 0 }}</span>
            </td>
            <td class="px-3 py-3 text-right">
              <span class="text-[11px] font-bold" :class="(campaign.clicks / (campaign.impressions || 1)) > 0.05 ? 'text-green-600' : 'text-gray-400'">
                {{ campaign.impressions ? ((campaign.clicks / campaign.impressions) * 100).toFixed(2) : '0.00' }}%
              </span>
            </td>
          </tr>
        </template>
        
        <tr v-if="!loading && filteredCampaigns.length === 0">
            <td colspan="8" class="py-12 text-center">
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
const showOnlyWithStats = ref(false)

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

  // Stats Filter
  if (showOnlyWithStats.value) {
    list = list.filter(c => (c.impressions > 0 || c.cost > 0 || c.conversions > 0))
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

// NEW: Helper functions for badge logic
const getCTR = (campaign) => {
  if (!campaign.impressions || campaign.impressions === 0) return 0
  return (campaign.clicks / campaign.impressions) * 100
}

const getConversionRate = (campaign) => {
  if (!campaign.clicks || campaign.clicks === 0) return 0
  return (campaign.conversions / campaign.clicks) * 100
}

const needsAttention = (campaign) => {
  // Campaign needs attention if:
  // 1. Has significant spend (> 1000 in any currency)
  // 2. Low CTR (< 1%)
  // 3. Is currently active
  const hasSignificantSpend = (campaign.cost || 0) > 1000
  const hasLowCTR = getCTR(campaign) < 1
  const isActive = campaign.state === 'ON'
  
  return hasSignificantSpend && hasLowCTR && isActive
}

// NEW: Quick action functions
const selectRecommended = () => {
  console.log('🟣 [CampaignPowerTable] selectRecommended clicked!')
  console.log('📊 Total campaigns:', filteredCampaigns.value.length)
  
  // Debug: Log all campaigns with their stats
  filteredCampaigns.value.forEach(c => {
    const ctr = getCTR(c)
    console.log(`   Campaign "${c.name}": CTR=${ctr.toFixed(2)}%, Conversions=${c.conversions || 0}, Impressions=${c.impressions || 0}, State=${c.state}`)
  })
  
  // Select campaigns with good performance:
  // - High CTR (> 3%) OR
  // - Has conversions OR
  // - High impressions (> 50000)
  const recommended = filteredCampaigns.value.filter(c => {
    const hasGoodCTR = getCTR(c) > 3
    const hasConversions = (c.conversions || 0) > 0
    const hasGoodReach = (c.impressions || 0) > 50000
    return hasGoodCTR || hasConversions || hasGoodReach
  })
  
  const ids = recommended.map(c => c.id)
  console.log(`🟣 [CampaignPowerTable] Emitting bulkSelect with ${ids.length} campaign IDs:`, ids)
  emit('bulkSelect', ids)
}

const selectActive = () => {
  console.log('🟢 [CampaignPowerTable] selectActive clicked!')
  console.log('📊 Total campaigns:', filteredCampaigns.value.length)
  
  // Debug: Log campaign states
  filteredCampaigns.value.forEach(c => {
    console.log(`   Campaign "${c.name}": State=${c.state}`)
  })
  
  // Select only active campaigns
  const active = filteredCampaigns.value.filter(c => c.state === 'ON')
  const ids = active.map(c => c.id)
  console.log(`🟢 [CampaignPowerTable] Emitting bulkSelect with ${ids.length} active campaign IDs:`, ids)
  emit('bulkSelect', ids)
}

const selectByBudget = () => {
  console.log('🔵 [CampaignPowerTable] selectByBudget clicked!')
  console.log('📊 Total campaigns:', filteredCampaigns.value.length)
  
  // Debug: Log campaign costs
  filteredCampaigns.value.forEach(c => {
    console.log(`   Campaign "${c.name}": Cost=${c.cost || 0}`)
  })
  
  // Select campaigns with cost > 10000
  const highBudget = filteredCampaigns.value.filter(c => (c.cost || 0) > 10000)
  const ids = highBudget.map(c => c.id)
  console.log(`🔵 [CampaignPowerTable] Emitting bulkSelect with ${ids.length} high-budget campaign IDs:`, ids)
  emit('bulkSelect', ids)
}
</script>
