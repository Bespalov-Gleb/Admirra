<template>
  <div class="bg-white rounded-[10px] px-6 sm:px-8 py-6 shadow-sm border border-gray-100 overflow-hidden font-[Inter]">
    <div class="mb-5">
      <h3 class="text-[20px] font-normal text-gray-900">Лучшие рекламные кампании</h3>
      <p class="text-[15px] font-normal text-gray-400 mt-0.5">По эффективности за период</p>
    </div>

    <div class="overflow-x-auto">
      <table class="w-full text-left border-separate border-spacing-y-2">
        <thead>
          <tr>
            <th class="px-4 py-3 text-left w-[26%] text-[15px] font-normal text-gray-400">Название кампании</th>
            <th class="px-4 py-3 text-left w-[12%] text-[15px] font-normal text-gray-400">Расход</th>
            <th class="px-4 py-3 text-left w-[12%] text-[15px] font-normal text-gray-400">Показы</th>
            <th class="px-4 py-3 text-left w-[10%] text-[15px] font-normal text-gray-400">Клики</th>
            <th class="px-4 py-3 text-left w-[10%] text-[15px] font-normal text-gray-400">СРС</th>
            <th class="px-4 py-3 text-left w-[10%] text-[15px] font-normal text-gray-400">Лиды</th>
            <th class="px-4 py-3 text-left w-[10%] text-[15px] font-normal text-gray-400">СРА</th>
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
              <div class="flex items-center gap-2 flex-nowrap">
                <span class="text-[15px] font-normal text-gray-900 tabular-nums">{{ formatMoney(campaign.cost) }} ₽</span>
                <TrendBadge :val="campaign.trend_cost ?? getDemoTrend(idx, 0)" metric="cost" />
              </div>
            </td>
            <td class="px-4 py-4">
              <div class="flex items-center gap-2 flex-nowrap">
                <span class="text-[15px] font-normal text-gray-900 tabular-nums">{{ (campaign.impressions || 0).toLocaleString('ru-RU') }}</span>
                <TrendBadge :val="campaign.trend_impressions ?? getDemoTrend(idx, 1)" metric="impressions" />
              </div>
            </td>
            <td class="px-4 py-4">
              <div class="flex items-center gap-2 flex-nowrap">
                <span class="text-[15px] font-normal text-gray-900 tabular-nums">{{ (campaign.clicks || 0).toLocaleString('ru-RU') }}</span>
                <TrendBadge :val="campaign.trend_clicks ?? getDemoTrend(idx, 2)" metric="clicks" />
              </div>
            </td>
            <td class="px-4 py-4">
              <div class="flex items-center gap-2 flex-nowrap">
                <span class="text-[15px] font-normal text-gray-900 tabular-nums">{{ formatMoney(campaign.cpc) }} ₽</span>
                <TrendBadge :val="campaign.trend_cpc ?? getDemoTrend(idx, 3)" metric="cpc" />
              </div>
            </td>
            <td class="px-4 py-4">
              <div class="flex items-center gap-2 flex-nowrap">
                <span class="text-[15px] font-normal text-gray-900 tabular-nums">{{ (campaign.conversions || 0).toLocaleString('ru-RU') }} шт.</span>
                <TrendBadge :val="campaign.trend_conversions ?? getDemoTrend(idx, 4)" metric="leads" />
              </div>
            </td>
            <td class="px-4 py-4 rounded-r-[10px]">
              <div class="flex items-center gap-2 flex-nowrap">
                <span class="text-[15px] font-normal text-gray-900 tabular-nums">{{ formatMoney(campaign.cpa) }} ₽</span>
                <TrendBadge :val="campaign.trend_cpa ?? getDemoTrend(idx, 5)" metric="cpa" />
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { computed, h } from 'vue'
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

const filteredCampaigns = computed(() => props.campaigns)

const formatMoney = (val) => {
  if (val == null || isNaN(val)) return '—'
  return new Intl.NumberFormat('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(val)
}

const rowBgClass = (idx) => {
  const variants = ['bg-[#FFF7ED]', 'bg-[#FBFCE1]', 'bg-[#F0FAE1]', 'bg-[#EFF7FC]', 'bg-[#F7EDFC]']
  return variants[idx % 5]
}

const getDemoTrend = () => 0

// Inline component for trend badge
const TrendBadge = (props) => {
  const { val, metric } = props
  const isCostMetric = metric === 'cpa' || metric === 'cost' || metric === 'cpc'
  const isPositive = isCostMetric ? val < 0 : val >= 0
  const sign = val >= 0 ? '+' : ''
  const Icon = val >= 0 ? ArrowTrendingUpIcon : ArrowTrendingDownIcon
  return h(
    'span',
    {
      class: [
        'inline-flex items-center gap-0.5 text-[9px] font-normal px-1.5 py-0.5 rounded-[6px] shrink-0',
        isPositive ? 'bg-[#EBFDF2] text-[#38B35A]' : 'bg-[#FCEBED] text-[#EB5757]'
      ]
    },
    [
      h(Icon, { class: 'w-2.5 h-2.5 shrink-0' }),
      `${sign}${val}%`
    ]
  )
}
TrendBadge.props = ['val', 'metric']
</script>
