<template>
  <div class="bg-white dark:bg-[#2A2D3C] rounded-[0.6944rem] px-6 sm:px-8 py-6 shadow-sm border border-gray-100 dark:border-white/10 overflow-hidden font-[Inter]">
    <div class="mb-5">
      <h3 class="text-[1.3889rem] font-normal text-gray-900 dark:text-white">Лучшие рекламные кампании</h3>
      <p class="text-[1.0417rem] font-normal text-gray-400 dark:text-gray-500 mt-0.5">По эффективности за период</p>
    </div>

    <div class="overflow-x-auto">
      <table class="w-full text-left border-separate border-spacing-y-2">
        <thead>
          <tr>
            <th class="px-4 py-3 text-left w-[26%] text-[1.0417rem] font-normal text-gray-400 dark:text-gray-500">Название кампании</th>
            <th class="px-4 py-3 text-left w-[12%] text-[1.0417rem] font-normal text-gray-400 dark:text-gray-500">Расход</th>
            <th class="px-4 py-3 text-left w-[12%] text-[1.0417rem] font-normal text-gray-400 dark:text-gray-500">Показы</th>
            <th class="px-4 py-3 text-left w-[10%] text-[1.0417rem] font-normal text-gray-400 dark:text-gray-500">Клики</th>
            <th class="px-4 py-3 text-left w-[10%] text-[1.0417rem] font-normal text-gray-400 dark:text-gray-500">СРС</th>
            <th class="px-4 py-3 text-left w-[10%] text-[1.0417rem] font-normal text-gray-400 dark:text-gray-500">Лиды</th>
            <th class="px-4 py-3 text-left w-[10%] text-[1.0417rem] font-normal text-gray-400 dark:text-gray-500">СРА</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading" v-for="i in 3" :key="i">
            <td colspan="7" class="px-2 py-1">
              <div class="h-14 bg-gray-100 dark:bg-white/10 rounded-[0.6944rem] animate-pulse"></div>
            </td>
          </tr>

          <tr v-else-if="filteredCampaigns.length === 0">
            <td colspan="7" class="px-6 py-12 text-center">
              <p class="text-[1.0417rem] font-normal text-gray-400 dark:text-gray-500">Кампании не найдены</p>
            </td>
          </tr>

          <tr
            v-for="(campaign, idx) in filteredCampaigns"
            :key="campaign.name"
            :class="rowBgClass(idx)"
          >
            <td class="px-4 py-4 rounded-l-[0.6944rem]">
              <span class="text-[1.0417rem] font-normal text-gray-900 dark:text-gray-200 line-clamp-1" :title="campaign.name">
                {{ campaign.name }}
              </span>
            </td>
            <td class="px-4 py-4">
              <div class="flex items-center gap-2 flex-nowrap">
                <span class="text-[1.0417rem] font-normal text-gray-900 dark:text-gray-200 tabular-nums">{{ formatMoney(withVat(campaign.cost)) }} ₽</span>
                <TrendBadge :val="campaign.trend_cost ?? getDemoTrend(idx, 0)" metric="cost" />
              </div>
            </td>
            <td class="px-4 py-4">
              <div class="flex items-center gap-2 flex-nowrap">
                <span class="text-[1.0417rem] font-normal text-gray-900 dark:text-gray-200 tabular-nums">{{ (campaign.impressions || 0).toLocaleString('ru-RU') }}</span>
                <TrendBadge :val="campaign.trend_impressions ?? getDemoTrend(idx, 1)" metric="impressions" />
              </div>
            </td>
            <td class="px-4 py-4">
              <div class="flex items-center gap-2 flex-nowrap">
                <span class="text-[1.0417rem] font-normal text-gray-900 dark:text-gray-200 tabular-nums">{{ (campaign.clicks || 0).toLocaleString('ru-RU') }}</span>
                <TrendBadge :val="campaign.trend_clicks ?? getDemoTrend(idx, 2)" metric="clicks" />
              </div>
            </td>
            <td class="px-4 py-4">
              <div class="flex items-center gap-2 flex-nowrap">
                <span class="text-[1.0417rem] font-normal text-gray-900 dark:text-gray-200 tabular-nums">{{ formatMoney(withVat(campaign.cpc)) }} ₽</span>
                <TrendBadge :val="campaign.trend_cpc ?? getDemoTrend(idx, 3)" metric="cpc" />
              </div>
            </td>
            <td class="px-4 py-4">
              <div class="flex items-center gap-2 flex-nowrap">
                <span class="text-[1.0417rem] font-normal text-gray-900 dark:text-gray-200 tabular-nums">{{ (campaign.conversions || 0).toLocaleString('ru-RU') }} шт.</span>
                <TrendBadge :val="campaign.trend_conversions ?? getDemoTrend(idx, 4)" metric="leads" />
              </div>
            </td>
            <td class="px-4 py-4 rounded-r-[0.6944rem]">
              <div class="flex items-center gap-2 flex-nowrap">
                <span class="text-[1.0417rem] font-normal text-gray-900 dark:text-gray-200 tabular-nums">{{ formatMoney(withVat(campaign.cpa)) }} ₽</span>
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
  },
  includeVat: {
    type: Boolean,
    default: false
  }
})

const filteredCampaigns = computed(() => props.campaigns)
const VAT_FACTOR = 1.22

const withVat = (val) => {
  const num = Number(val || 0)
  return props.includeVat ? num * VAT_FACTOR : num
}

const formatMoney = (val) => {
  if (val == null || isNaN(val)) return '—'
  return new Intl.NumberFormat('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(val)
}

const rowBgClass = (idx) => {
  const light = ['bg-[#FFF7ED]', 'bg-[#FBFCE1]', 'bg-[#F0FAE1]', 'bg-[#EFF7FC]', 'bg-[#F7EDFC]']
  const dark = ['dark:bg-white/[0.05]', 'dark:bg-white/[0.06]', 'dark:bg-white/[0.05]', 'dark:bg-white/[0.06]', 'dark:bg-white/[0.05]']
  return `${light[idx % 5]} ${dark[idx % 5]}`
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
        'inline-flex items-center gap-0.5 text-[0.625rem] font-normal px-1.5 py-0.5 rounded-[0.4167rem] shrink-0',
        isPositive ? 'bg-[#EBFDF2] dark:bg-green-500/20 text-[#38B35A] dark:text-[#66BB6A]' : 'bg-[#FCEBED] dark:bg-red-500/20 text-[#EB5757] dark:text-[#EF5350]'
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
