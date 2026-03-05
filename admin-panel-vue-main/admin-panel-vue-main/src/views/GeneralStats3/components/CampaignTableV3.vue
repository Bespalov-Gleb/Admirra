<template>
  <div class="bg-white rounded-3xl px-6 sm:px-10 py-8 shadow-md border border-gray-100 overflow-hidden">
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
      <div>
        <h3 class="text-xl font-black text-gray-900">Лучшие рекламные кампании</h3>
        <p class="text-xs font-semibold text-gray-500 uppercase tracking-wider mt-1">По эффективности за период</p>
      </div>
      <div class="relative">
        <input 
          v-model="searchQuery" 
          type="text" 
          placeholder="Поиск кампании" 
          class="pl-10 pr-4 py-2.5 text-sm border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-400 bg-gray-50/80 w-64 shadow-sm"
        />
        <MagnifyingGlassIcon class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
      </div>
    </div>
    
    <div class="overflow-x-auto -mx-1">
      <table class="w-full text-left border-separate border-spacing-y-3">
        <thead>
          <tr class="text-[10px] font-black text-gray-400 uppercase tracking-[0.15em]">
            <th class="px-6 py-4">Название кампании</th>
            <th class="px-4 py-4 text-right">Расход</th>
            <th class="px-4 py-4 text-right">Показы</th>
            <th class="px-4 py-4 text-right">Клики</th>
            <th class="px-4 py-4 text-right">СРС</th>
            <th class="px-4 py-4 text-right">Лиды</th>
            <th class="px-6 py-4 text-right">СРА</th>
          </tr>
        </thead>
        <tbody class="divide-y-0">
          <tr v-if="loading" v-for="i in 3" :key="i">
            <td colspan="7" class="px-2">
              <div class="h-16 bg-gray-100 rounded-2xl animate-pulse"></div>
            </td>
          </tr>
          
          <tr v-else-if="filteredCampaigns.length === 0">
            <td colspan="7" class="px-6 py-16 text-center">
              <p class="text-sm font-semibold text-gray-400">Кампании не найдены</p>
            </td>
          </tr>

          <tr 
            v-for="(campaign, idx) in filteredCampaigns" 
            :key="campaign.name" 
            class="group transition-all"
            :class="rowBgClass(idx)"
          >
            <td class="px-6 py-5 rounded-l-3xl">
              <div class="flex flex-col gap-0.5">
                <span class="text-sm font-bold text-gray-900 line-clamp-1" :title="campaign.name">
                  {{ campaign.name }}
                </span>
                <span class="text-[10px] font-semibold text-gray-400 uppercase tracking-tight">
                  {{ campaign.name?.includes('[VK]') ? 'ВКонтакте Ads' : 'Яндекс.Директ' }}
                </span>
              </div>
            </td>
            <td class="px-4 py-5 text-right">
              <div class="flex flex-row items-center justify-end gap-2 flex-wrap">
                <span class="text-sm font-bold text-gray-900 tabular-nums">{{ formatMoney(campaign.cost) }} ₽</span>
                <span v-if="campaign.trend_cost != null" :class="trendClass('cost', campaign.trend_cost)">
                  <ArrowTrendingUpIcon v-if="campaign.trend_cost >= 0" class="w-3 h-3" />
                  <ArrowTrendingDownIcon v-else class="w-3 h-3" />
                  {{ campaign.trend_cost >= 0 ? '+' : '' }}{{ campaign.trend_cost }}%
                </span>
              </div>
            </td>
            <td class="px-4 py-5 text-right">
              <div class="flex flex-row items-center justify-end gap-2 flex-wrap">
                <span class="text-sm font-bold text-gray-700 tabular-nums">{{ (campaign.impressions || 0).toLocaleString('ru-RU') }}</span>
                <span v-if="campaign.trend_impressions != null" :class="trendClass('impressions', campaign.trend_impressions)">
                  <ArrowTrendingUpIcon v-if="campaign.trend_impressions >= 0" class="w-3 h-3" />
                  <ArrowTrendingDownIcon v-else class="w-3 h-3" />
                  {{ campaign.trend_impressions >= 0 ? '+' : '' }}{{ campaign.trend_impressions }}%
                </span>
              </div>
            </td>
            <td class="px-4 py-5 text-right">
              <div class="flex flex-row items-center justify-end gap-2 flex-wrap">
                <span class="text-sm font-bold text-gray-700 tabular-nums">{{ (campaign.clicks || 0).toLocaleString('ru-RU') }}</span>
                <span v-if="campaign.trend_clicks != null" :class="trendClass('clicks', campaign.trend_clicks)">
                  <ArrowTrendingUpIcon v-if="campaign.trend_clicks >= 0" class="w-3 h-3" />
                  <ArrowTrendingDownIcon v-else class="w-3 h-3" />
                  {{ campaign.trend_clicks >= 0 ? '+' : '' }}{{ campaign.trend_clicks }}%
                </span>
              </div>
            </td>
            <td class="px-4 py-5 text-right">
              <div class="flex flex-row items-center justify-end gap-2 flex-wrap">
                <span class="text-sm font-bold text-gray-700 tabular-nums">{{ formatMoney(campaign.cpc) }} ₽</span>
                <span v-if="campaign.trend_cpc != null" :class="trendClass('cpc', campaign.trend_cpc)">
                  <ArrowTrendingUpIcon v-if="campaign.trend_cpc >= 0" class="w-3 h-3" />
                  <ArrowTrendingDownIcon v-else class="w-3 h-3" />
                  {{ campaign.trend_cpc >= 0 ? '+' : '' }}{{ campaign.trend_cpc }}%
                </span>
              </div>
            </td>
            <td class="px-4 py-5 text-right">
              <div class="flex flex-row items-center justify-end gap-2 flex-wrap">
                <span class="text-sm font-bold text-gray-700 tabular-nums">{{ (campaign.conversions || 0).toLocaleString('ru-RU') }} шт.</span>
                <span v-if="campaign.trend_conversions != null" :class="trendClass('leads', campaign.trend_conversions)">
                  <ArrowTrendingUpIcon v-if="campaign.trend_conversions >= 0" class="w-3 h-3" />
                  <ArrowTrendingDownIcon v-else class="w-3 h-3" />
                  {{ campaign.trend_conversions >= 0 ? '+' : '' }}{{ campaign.trend_conversions }}%
                </span>
              </div>
            </td>
            <td class="px-6 py-5 text-right rounded-r-3xl">
              <div class="flex flex-row items-center justify-end gap-2 flex-wrap">
                <span class="text-sm font-bold text-gray-900 tabular-nums">{{ formatMoney(campaign.cpa) }} ₽</span>
                <span v-if="campaign.trend_cpa != null" :class="trendClass('cpa', campaign.trend_cpa)">
                  <ArrowTrendingUpIcon v-if="campaign.trend_cpa >= 0" class="w-3 h-3" />
                  <ArrowTrendingDownIcon v-else class="w-3 h-3" />
                  {{ campaign.trend_cpa >= 0 ? '+' : '' }}{{ campaign.trend_cpa }}%
                </span>
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
import { ArrowTrendingUpIcon, ArrowTrendingDownIcon } from '@heroicons/vue/24/solid'

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

/** Пастельные фоны строк по макету: peach, lime, green, blue, purple */
const rowBgClass = (idx) => {
  const variants = ['bg-[#FFF7ED]', 'bg-[#FBFCE1]', 'bg-[#F0FAE1]', 'bg-[#EFF7FC]', 'bg-[#F7EDFC]']
  return variants[idx % 5]
}

/** Тренд: зелёный для хороших метрик (рост = хорошо), красный для CPA (рост = плохо) */
const trendClass = (metricKey, val) => {
  const isGood = val >= 0
  const isCpa = metricKey === 'cpa'
  const isPositive = isCpa ? !isGood : isGood
  return [
    'inline-flex items-center gap-0.5 text-[11px] font-bold px-2 py-1 rounded-lg',
    isPositive ? 'bg-[#EBFDF2] text-[#38B35A]' : 'bg-[#FCEBED] text-[#EB5757]'
  ]
}
</script>
