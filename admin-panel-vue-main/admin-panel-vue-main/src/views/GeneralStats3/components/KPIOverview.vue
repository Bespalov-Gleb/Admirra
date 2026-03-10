<template>
  <div class="w-full font-[Inter]">
    <div class="grid grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-5">
      <div v-for="metric in metrics" :key="metric.id">
        <CardV3
          :title="metric.title"
          :subtitle="metric.subtitle"
          :value="metric.value"
          :trend="metric.trend"
          :trend-display="metric.trendDisplay"
          :trend-absolute="metric.trendAbsolute"
          :change-positive="metric.changePositive"
          :icon="metric.icon"
          :icon-color="metric.iconColor"
          :is-selected="selectedMetrics.includes(metric.id)"
          :chart-color="metric.chartColor"
          @click="$emit('toggle-metric', metric.id)"
        />
      </div>
    </div>
    <div v-if="loading" class="mt-2 h-0.5 bg-blue-500 rounded-full animate-pulse"></div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import {
  WalletIcon,
  ChartBarIcon,
  CursorArrowRaysIcon,
  GlobeAltIcon,
  BriefcaseIcon,
  CheckBadgeIcon
} from '@heroicons/vue/24/solid'
import CardV3 from './CardV3.vue'

const props = defineProps({
  summary: {
    type: Object,
    required: true
  },
  selectedMetrics: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: 'Общая статистика'
  },
  includeVat: {
    type: Boolean,
    default: false
  }
})

defineEmits(['toggle-metric'])

/** Вычисляет абсолютное изменение из текущего значения и процента тренда */
function formatAbsoluteChange(current, trendPct, options = {}) {
  if (trendPct === 0 || trendPct == null) return ''
  const absChange = current * trendPct / (100 + trendPct)
  const suffix = options.suffix || ''
  const decimals = options.decimals ?? 0
  let formatted
  if (Math.abs(absChange) >= 1000) {
    formatted = (absChange / 1000).toLocaleString('ru-RU', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + 'k'
  } else {
    formatted = absChange.toLocaleString('ru-RU', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
  }
  const sign = absChange >= 0 ? '+' : ''
  return `${sign}${formatted}${suffix} за эту неделю`
}

const metrics = computed(() => {
  const rawExpenses = props.summary.expenses || 0
  const vatFactor = props.includeVat ? 1.22 : 1
  const expensesValue = rawExpenses * vatFactor
  const currency = props.summary.currency === 'RUB' ? '₽' : props.summary.currency
  const t = props.summary.trends || {}

  return [
    {
      id: 'expenses',
      title: 'Расходы',
      subtitle: 'За период',
      value: expensesValue.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' ' + currency,
      trend: t.expenses ?? 0,
      trendDisplay: `${(t.expenses ?? 0) >= 0 ? '+' : ''}${(t.expenses ?? 0).toFixed(1)}%`,
      trendAbsolute: formatAbsoluteChange(expensesValue, t.expenses ?? 0, { suffix: ' ' + currency, decimals: 2 }),
      changePositive: (t.expenses ?? 0) <= 0,
      icon: WalletIcon,
      iconColor: 'blue',
      chartColor: '#3464F3'
    },
    {
      id: 'impressions',
      title: 'Показы',
      subtitle: 'По всем каналам',
      value: (props.summary.impressions || 0).toLocaleString(),
      trend: t.impressions ?? 0,
      trendDisplay: `${(t.impressions ?? 0) >= 0 ? '+' : ''}${(t.impressions ?? 0).toFixed(1)}%`,
      trendAbsolute: formatAbsoluteChange(props.summary.impressions || 0, t.impressions ?? 0),
      changePositive: (t.impressions ?? 0) >= 0,
      icon: ChartBarIcon,
      iconColor: 'blue',
      chartColor: '#F0926D'
    },
    {
      id: 'clicks',
      title: 'Клики',
      subtitle: 'Все переходы',
      value: (props.summary.clicks || 0).toLocaleString(),
      trend: t.clicks ?? 0,
      trendDisplay: `${(t.clicks ?? 0) >= 0 ? '+' : ''}${(t.clicks ?? 0).toFixed(1)}%`,
      trendAbsolute: formatAbsoluteChange(props.summary.clicks || 0, t.clicks ?? 0),
      changePositive: (t.clicks ?? 0) >= 0,
      icon: CursorArrowRaysIcon,
      iconColor: 'blue',
      chartColor: '#C2EECF'
    },
    {
      id: 'cpc',
      title: 'CPC',
      subtitle: 'Стоимость клика',
      value: ((props.summary.cpc || 0) * vatFactor).toLocaleString() + ' ' + currency,
      trend: t.cpc ?? 0,
      trendDisplay: `${(t.cpc ?? 0) >= 0 ? '+' : ''}${(t.cpc ?? 0).toFixed(1)}%`,
      trendAbsolute: formatAbsoluteChange((props.summary.cpc || 0) * vatFactor, t.cpc ?? 0, { suffix: ' ' + currency, decimals: 2 }),
      changePositive: (t.cpc ?? 0) <= 0,
      icon: GlobeAltIcon,
      iconColor: 'blue',
      chartColor: '#D38CFF'
    },
    {
      id: 'leads',
      title: 'Лиды',
      subtitle: 'По всем каналам',
      value: (props.summary.leads || 0).toLocaleString() + ' шт.',
      trend: t.leads ?? 0,
      trendDisplay: `${(t.leads ?? 0) >= 0 ? '+' : ''}${(t.leads ?? 0).toFixed(1)}%`,
      trendAbsolute: formatAbsoluteChange(props.summary.leads || 0, t.leads ?? 0, { suffix: ' шт.' }),
      changePositive: (t.leads ?? 0) >= 0,
      icon: BriefcaseIcon,
      iconColor: 'blue',
      chartColor: '#8ADA70'
    },
    {
      id: 'cpa',
      title: 'CPA',
      subtitle: 'Стоимость лида',
      value: ((props.summary.cpa || 0) * vatFactor).toLocaleString() + ' ' + currency,
      trend: t.cpa ?? 0,
      trendDisplay: `${(t.cpa ?? 0) >= 0 ? '+' : ''}${(t.cpa ?? 0).toFixed(1)}%`,
      trendAbsolute: formatAbsoluteChange((props.summary.cpa || 0) * vatFactor, t.cpa ?? 0, { suffix: ' ' + currency, decimals: 2 }),
      changePositive: (t.cpa ?? 0) <= 0,
      icon: CheckBadgeIcon,
      iconColor: 'blue',
      chartColor: '#EB8525'
    }
  ]
})
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  height: 0px;
  background: transparent;
}
.custom-scrollbar {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
</style>
