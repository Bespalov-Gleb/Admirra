<template>
  <div class="bg-white rounded-[10px] px-6 sm:px-8 py-6 shadow-sm border border-gray-100 overflow-hidden font-[Inter]">
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-5">
      <div>
        <h3 class="text-[20px] font-normal text-gray-900">Лучшие рекламные кампании</h3>
        <p class="text-[15px] font-normal text-gray-400 mt-0.5">По эффективности за период</p>
      </div>
      <div class="relative">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Поиск кампании"
          class="pl-10 pr-4 py-2 text-[14px] font-normal border border-gray-200 rounded-[10px] focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 bg-gray-50 w-56"
        />
        <MagnifyingGlassIcon class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
      </div>
    </div>

    <div class="overflow-x-auto">
      <table class="w-full text-left border-separate border-spacing-y-2">
        <thead>
          <tr class="text-[15px] font-normal text-gray-400">
            <th class="px-4 py-3 text-left w-[26%]">Название кампании</th>
            <th class="px-4 py-3 text-left w-[12%]">Расход</th>
            <th class="px-4 py-3 text-left w-[12%]">Показы</th>
            <th class="px-4 py-3 text-left w-[10%]">Клики</th>
            <th class="px-4 py-3 text-left w-[10%]">СРС</th>
            <th class="px-4 py-3 text-left w-[10%]">Лиды</th>
            <th class="px-4 py-3 text-left w-[10%]">СРА</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading" v-for="i in 3" :key="i">
            <td colspan="7" class="px-2 py-1">
              <div class="h-14 bg-gray-100 rounded-[10px] animate-pulse"></div>
            </td>
          </tr>

          <tr v-else-if="filteredCampaigns.length === 0">
            <td colspan="7" class="px-6 py-12 text-center">
              <p class="text-[15px] font-normal text-gray-400">Кампании не найдены</p>
            </td>
          </tr>

          <tr
            v-for="(campaign, idx) in filteredCampaigns"
            :key="campaign.name"
            :class="rowBgClass(idx)"
          >
            <td class="px-4 py-4 rounded-l-[10px]">
              <span class="text-[15px] font-normal text-gray-900 line-clamp-1" :title="campaign.name">
                {{ campaign.name }}
              </span>
            </td>
            <td class="px-4 py-4">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-[15px] font-normal text-gray-900 tabular-nums">{{ formatMoney(campaign.cost) }} ₽</span>
                <span v-if="campaign.trend_cost != null" :class="trendClass('cost', campaign.trend_cost)">
                  <ArrowTrendingUpIcon v-if="campaign.trend_cost >= 0" class="w-3 h-3" />
                  <ArrowTrendingDownIcon v-else class="w-3 h-3" />
                  {{ campaign.trend_cost >= 0 ? '+' : '' }}{{ campaign.trend_cost }}%
                </span>
              </div>
            </td>
            <td class="px-4 py-4">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-[15px] font-normal text-gray-900 tabular-nums">{{ (campaign.impressions || 0).toLocaleString('ru-RU') }}</span>
                <span v-if="campaign.trend_impressions != null" :class="trendClass('impressions', campaign.trend_impressions)">
                  <ArrowTrendingUpIcon v-if="campaign.trend_impressions >= 0" class="w-3 h-3" />
                  <ArrowTrendingDownIcon v-else class="w-3 h-3" />
                  {{ campaign.trend_impressions >= 0 ? '+' : '' }}{{ campaign.trend_impressions }}%
                </span>
              </div>
            </td>
            <td class="px-4 py-4">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-[15px] font-normal text-gray-900 tabular-nums">{{ (campaign.clicks || 0).toLocaleString('ru-RU') }}</span>
                <span v-if="campaign.trend_clicks != null" :class="trendClass('clicks', campaign.trend_clicks)">
                  <ArrowTrendingUpIcon v-if="campaign.trend_clicks >= 0" class="w-3 h-3" />
                  <ArrowTrendingDownIcon v-else class="w-3 h-3" />
                  {{ campaign.trend_clicks >= 0 ? '+' : '' }}{{ campaign.trend_clicks }}%
                </span>
              </div>
            </td>
            <td class="px-4 py-4">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-[15px] font-normal text-gray-900 tabular-nums">{{ formatMoney(campaign.cpc) }} ₽</span>
                <span v-if="campaign.trend_cpc != null" :class="trendClass('cpc', campaign.trend_cpc)">
                  <ArrowTrendingUpIcon v-if="campaign.trend_cpc >= 0" class="w-3 h-3" />
                  <ArrowTrendingDownIcon v-else class="w-3 h-3" />
                  {{ campaign.trend_cpc >= 0 ? '+' : '' }}{{ campaign.trend_cpc }}%
                </span>
              </div>
            </td>
            <td class="px-4 py-4">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-[15px] font-normal text-gray-900 tabular-nums">{{ (campaign.conversions || 0).toLocaleString('ru-RU') }} шт.</span>
                <span v-if="campaign.trend_conversions != null" :class="trendClass('leads', campaign.trend_conversions)">
                  <ArrowTrendingUpIcon v-if="campaign.trend_conversions >= 0" class="w-3 h-3" />
                  <ArrowTrendingDownIcon v-else class="w-3 h-3" />
                  {{ campaign.trend_conversions >= 0 ? '+' : '' }}{{ campaign.trend_conversions }}%
                </span>
              </div>
            </td>
            <td class="px-4 py-4 rounded-r-[10px]">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-[15px] font-normal text-gray-900 tabular-nums">{{ formatMoney(campaign.cpa) }} ₽</span>
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

const rowBgClass = (idx) => {
  const variants = ['bg-[#FFF7ED]', 'bg-[#FBFCE1]', 'bg-[#F0FAE1]', 'bg-[#EFF7FC]', 'bg-[#F7EDFC]']
  return variants[idx % 5]
}

const trendClass = (metricKey, val) => {
  const isGood = val >= 0
  const isCost = metricKey === 'cpa' || metricKey === 'cost' || metricKey === 'cpc'
  const isPositive = isCost ? !isGood : isGood
  return [
    'inline-flex items-center gap-0.5 text-[12px] font-normal px-2 py-0.5 rounded-[6px]',
    isPositive ? 'bg-[#EBFDF2] text-[#38B35A]' : 'bg-[#FCEBED] text-[#EB5757]'
  ]
}
</script>
