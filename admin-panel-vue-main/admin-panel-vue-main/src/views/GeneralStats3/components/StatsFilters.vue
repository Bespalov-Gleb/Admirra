<template>
  <div class="flex flex-wrap items-end gap-3 lg:gap-4">
    <!-- Main Selections Group -->
    <div class="flex flex-wrap items-center gap-3 bg-gray-50/50 p-1.5 rounded-[24px] border border-gray-100/50">
      <!-- Project Select -->
      <div class="flex flex-col gap-1 min-w-[140px] sm:min-w-[180px]">
        <label class="text-[8px] font-black text-gray-400 uppercase tracking-widest ml-2">Проект</label>
        <div class="relative group">
          <select 
            v-model="filters.client_id"
            class="w-full h-9 pl-3 pr-8 bg-white border border-gray-100 rounded-[14px] text-xs font-bold text-gray-700 outline-none appearance-none transition-all focus:border-blue-500 focus:ring-4 focus:ring-blue-500/5 group-hover:border-gray-200"
          >
            <option value="">Все проекты</option>
            <option v-for="client in clients" :key="client.id" :value="client.id">
              {{ client.name }}
            </option>
          </select>
          <ChevronDownIcon class="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400 pointer-events-none group-hover:text-gray-600 transition-colors" />
        </div>
      </div>

      <div class="w-[1px] h-8 bg-gray-200/50 hidden sm:block"></div>

      <!-- Channel Select -->
      <div class="flex flex-col gap-1 min-w-[110px] sm:min-w-[140px]">
        <label class="text-[8px] font-black text-gray-400 uppercase tracking-widest ml-2">Канал</label>
        <div class="relative group">
          <select 
            v-model="filters.channel"
            class="w-full h-9 pl-3 pr-8 bg-white border border-gray-100 rounded-[14px] text-xs font-bold text-gray-700 outline-none appearance-none transition-all focus:border-blue-500 focus:ring-4 focus:ring-blue-500/5 group-hover:border-gray-200"
          >
            <option value="all">Все каналы</option>
            <option value="yandex">Yandex Direct</option>
            <option value="vk">VK Ads</option>
          </select>
          <ChevronDownIcon class="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400 pointer-events-none group-hover:text-gray-600 transition-colors" />
        </div>
      </div>

      <div class="w-[1px] h-8 bg-gray-200/50 hidden lg:block"></div>

      <!-- Campaign Select -->
      <div class="flex flex-col gap-1 min-w-[140px] sm:min-w-[180px]">
        <label class="text-[8px] font-black text-gray-400 uppercase tracking-widest ml-2">Кампания</label>
        <div class="relative group">
          <select 
            v-model="selectedCampaignId"
            class="w-full h-9 pl-3 pr-8 bg-white border border-gray-100 rounded-[14px] text-xs font-bold text-gray-700 outline-none appearance-none transition-all focus:border-blue-500 focus:ring-4 focus:ring-blue-500/5 group-hover:border-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="loadingCampaigns || !filters.client_id"
          >
            <template v-if="!filters.client_id">
              <option value="">Сначала проект</option>
            </template>
            <template v-else-if="loadingCampaigns">
              <option value="">Загрузка...</option>
            </template>
            <template v-else-if="!allCampaigns.length">
              <option value="">Нет кампаний</option>
            </template>
            <template v-else>
              <option value="">Все кампании ({{ allCampaigns.length }})</option>
              <option v-for="campaign in allCampaigns" :key="campaign.id" :value="campaign.id">
                {{ campaign.name }}
              </option>
            </template>
          </select>
          <div v-if="loadingCampaigns" class="absolute right-8 top-1/2 -translate-y-1/2">
            <div class="w-3 h-3 border-2 border-blue-600/20 border-t-blue-600 rounded-full animate-spin"></div>
          </div>
          <ChevronDownIcon class="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400 pointer-events-none group-hover:text-gray-600 transition-colors" />
        </div>
      </div>
    </div>

    <!-- Time & Action Group -->
    <div class="flex items-center gap-3 ml-auto">
      <!-- Period Select -->
      <div class="flex flex-col gap-1 w-[110px]">
        <label class="text-[8px] font-black text-gray-400 uppercase tracking-widest ml-2">Период</label>
        <div class="relative group">
          <select 
            v-model="filters.period"
            @change="$emit('period-change')"
            class="w-full h-9 pl-3 pr-8 bg-white/50 border border-gray-100 rounded-[14px] text-xs font-bold text-gray-700 outline-none appearance-none transition-all focus:border-blue-500 focus:ring-4 focus:ring-blue-500/5 group-hover:border-gray-200"
          >
            <option value="7">7 дней</option>
            <option value="14">14 дней</option>
            <option value="30">30 дней</option>
            <option value="90">90 дней</option>
            <option value="custom">Свой период</option>
          </select>
          <ChevronDownIcon class="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400 pointer-events-none group-hover:text-gray-600 transition-colors" />
        </div>
      </div>

      <!-- Custom Date Inputs -->
      <div v-if="filters.period === 'custom'" class="flex flex-col gap-1">
        <label class="text-[8px] font-black text-gray-400 uppercase tracking-widest ml-2">Даты</label>
        <div class="flex items-center gap-1.5 p-1 bg-white border border-gray-100 rounded-[14px]">
          <input 
            type="date" 
            v-model="filters.start_date"
            class="h-7 w-[105px] px-2 bg-gray-50/50 text-[10px] font-bold text-gray-700 outline-none rounded-lg hover:bg-gray-100 transition-colors"
          />
          <div class="w-1.5 h-[1px] bg-gray-300"></div>
          <input 
            type="date" 
            v-model="filters.end_date"
            class="h-7 w-[105px] px-2 bg-gray-50/50 text-[10px] font-bold text-gray-700 outline-none rounded-lg hover:bg-gray-100 transition-colors"
          />
        </div>
      </div>

      <!-- Export Button -->
      <div class="flex flex-col gap-1 self-end">
        <button 
          @click="$emit('export')"
          class="h-9 px-4 bg-gray-900 text-white rounded-[14px] text-[10px] font-black uppercase tracking-widest hover:bg-blue-600 hover:shadow-lg hover:shadow-blue-200 transition-all flex items-center gap-2 active:scale-95"
          title="Скачать CSV"
        >
          <ArrowDownTrayIcon class="w-3.5 h-3.5" />
          <span class="hidden sm:inline">CSV</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ArrowDownTrayIcon, ChevronDownIcon } from '@heroicons/vue/24/solid'

const props = defineProps({
  filters: {
    type: Object,
    required: true
  },
  clients: {
    type: Array,
    default: () => []
  },
  allCampaigns: {
    type: Array,
    default: () => []
  },
  loadingCampaigns: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['period-change', 'export', 'update:campaign-ids'])

const selectedCampaignId = computed({
  get: () => {
    const ids = props.filters.campaign_ids
    return (ids && ids.length > 0) ? ids[0] : ''
  },
  set: (val) => {
    if (val === undefined || val === null) return
    const current = (props.filters.campaign_ids && props.filters.campaign_ids.length > 0) ? props.filters.campaign_ids[0] : ''
    if (val !== current) {
      emit('update:campaign-ids', val ? [val] : [])
    }
  }
})
</script>
