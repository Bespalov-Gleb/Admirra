<template>
  <div class="bg-white rounded-2xl px-6 sm:px-10 py-8 shadow-sm border border-gray-100 overflow-hidden">
    <div class="mb-6">
      <h3 class="text-xl font-bold text-gray-900">Лучшие рекламные кампании</h3>
      <p class="text-xs font-medium text-gray-500 mt-1">По эффективности за период</p>
    </div>
    <div class="flex justify-end mb-4">
      <div class="relative">
        <input 
          v-model="searchQuery" 
          type="text" 
          placeholder="Поиск кампании..." 
          class="pl-10 pr-4 py-2 text-sm border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 bg-gray-50/50 transition-all w-64"
        />
        <MagnifyingGlassIcon class="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
      </div>
    </div>
    
    <div class="overflow-x-auto -mx-2">
      <table class="w-full text-left border-separate border-spacing-y-2">
        <thead>
          <tr class="text-[10px] font-black text-gray-400 uppercase tracking-widest">
            <th class="px-6 py-3">Название кампании</th>
            <th class="px-4 py-3 text-right">Расход</th>
            <th class="px-4 py-3 text-right">Показы</th>
            <th class="px-4 py-3 text-right">Клики</th>
            <th class="px-4 py-3 text-right">CPC</th>
            <th class="px-4 py-3 text-right">Лиды</th>
            <th class="px-6 py-3 text-right">CPA</th>
          </tr>
        </thead>
        <tbody class="divide-y-0">
          <tr v-if="loading" v-for="i in 3" :key="i">
            <td colspan="7" class="px-2">
              <div class="h-16 bg-gray-50/50 rounded-2xl animate-pulse"></div>
            </td>
          </tr>
          
          <tr v-else-if="filteredCampaigns.length === 0">
            <td colspan="7" class="px-6 py-10 text-center text-gray-400 font-medium">
              Кампании не найдены
            </td>
          </tr>

          <tr 
            v-for="(campaign, idx) in filteredCampaigns" 
            :key="campaign.name" 
            class="group transition-all cursor-default"
            :class="idx % 2 === 0 ? 'bg-amber-50/40' : 'bg-emerald-50/40'"
          >
            <td class="px-6 py-4 rounded-l-2xl">
              <div class="flex flex-col">
                <span class="text-sm font-bold text-gray-900 line-clamp-1" :title="campaign.name">
                  {{ campaign.name }}
                </span>
                <span class="text-[10px] font-bold text-gray-400 uppercase tracking-tighter">
                  {{ campaign.name?.includes('[VK]') ? 'ВКонтакте Ads' : 'Яндекс.Директ' }}
                </span>
              </div>
            </td>
            <td class="px-4 py-4 text-right">
              <div class="flex flex-col items-end">
                <span class="text-sm font-bold text-gray-900">{{ formatMoney(campaign.cost) }} ₽</span>
                <span v-if="campaign.trend_cost != null" class="text-[10px] font-bold text-green-600">+{{ campaign.trend_cost }}%</span>
              </div>
            </td>
            <td class="px-4 py-4 text-right">
              <div class="flex flex-col items-end">
                <span class="text-sm font-bold text-gray-600">{{ (campaign.impressions || 0).toLocaleString() }}</span>
                <span v-if="campaign.trend_impressions != null" class="text-[10px] font-bold text-green-600">+{{ campaign.trend_impressions }}%</span>
              </div>
            </td>
            <td class="px-4 py-4 text-right">
              <div class="flex flex-col items-end">
                <span class="text-sm font-bold text-gray-600">{{ (campaign.clicks || 0).toLocaleString() }}</span>
                <span v-if="campaign.trend_clicks != null" class="text-[10px] font-bold text-green-600">+{{ campaign.trend_clicks }}%</span>
              </div>
            </td>
            <td class="px-4 py-4 text-right">
              <div class="flex flex-col items-end">
                <span class="text-sm font-bold text-gray-600">{{ formatMoney(campaign.cpc) }} ₽</span>
                <span v-if="campaign.trend_cpc != null" class="text-[10px] font-bold text-green-600">+{{ campaign.trend_cpc }}%</span>
              </div>
            </td>
            <td class="px-4 py-4 text-right">
              <div class="flex flex-col items-end">
                <span class="text-sm font-bold text-gray-600">{{ (campaign.conversions || 0).toLocaleString() }} шт.</span>
                <span v-if="campaign.trend_conversions != null" class="text-[10px] font-bold text-green-600">+{{ campaign.trend_conversions }}%</span>
              </div>
            </td>
            <td class="px-6 py-4 text-right rounded-r-2xl">
              <div class="flex flex-col items-end gap-0.5">
                <span class="text-sm font-bold text-gray-900">{{ formatMoney(campaign.cpa) }} ₽</span>
                <span v-if="campaign.trend_cpa != null" class="text-[10px] font-bold text-green-600">+{{ campaign.trend_cpa }}%</span>
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
import { MagnifyingGlassIcon } from '@heroicons/vue/24/outline'

const props = defineProps({
  campaigns: {
    type: Array,
    required: true,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  }
})


const searchQuery = ref('')

const filteredCampaigns = computed(() => {
  if (!searchQuery.value) return props.campaigns
  const query = searchQuery.value.toLowerCase()
  return props.campaigns.filter(c => 
    (c.name || '').toLowerCase().includes(query)
  )
})

const formatMoney = (val) => {
  if (val == null || isNaN(val)) return '—'
  return new Intl.NumberFormat('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(val)
}
</script>
