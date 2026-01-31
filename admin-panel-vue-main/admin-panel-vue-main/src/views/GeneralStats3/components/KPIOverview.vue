<template>
  <div class="w-full">
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-xs font-black text-gray-400 uppercase tracking-[0.2em]">{{ title }}</h2>
    </div>

    <div class="w-full overflow-hidden relative group/scroll">
      <div 
        ref="containerRef"
        class="flex gap-4 sm:gap-6 overflow-x-auto pb-4 custom-scrollbar select-none max-w-full"
        v-on="dragScrollHandlers"
      >
        <div v-for="metric in metrics" :key="metric.id" class="flex-shrink-0">
          <CardV3
            :title="metric.title"
            :value="metric.value"
            :trend="metric.trend"
            :change-positive="metric.changePositive"
            :icon="metric.icon"
            :icon-color="metric.iconColor"
            :is-selected="selectedMetrics.includes(metric.id)"
            @click="$emit('toggle-metric', metric.id)"
          />
        </div>
      </div>
      <!-- Progress Bar for loading -->
      <div v-if="loading" class="absolute bottom-0 left-0 h-0.5 bg-blue-600 animate-progress-fast z-20"></div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import {
  CurrencyDollarIcon,
  EyeIcon,
  ArrowPathIcon,
  UserGroupIcon,
  HandRaisedIcon,
  BanknotesIcon
} from '@heroicons/vue/24/solid'
import CardV3 from './CardV3.vue'
import { useDragScroll } from '../../../composables/useDragScroll'

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

const { containerRef, dragScrollHandlers } = useDragScroll()

const metrics = computed(() => {
  // CRITICAL: Check if balance is null, undefined, or 0 - show dash in that case
  const hasBalance = props.summary.balance !== null && props.summary.balance !== undefined
  let rawBalance = null
  
  if (hasBalance) {
    if (typeof props.summary.balance === 'number') {
      rawBalance = props.summary.balance
    } else {
      const parsed = parseFloat(props.summary.balance)
      rawBalance = isNaN(parsed) ? null : parsed
    }
    // CRITICAL: Если баланс равен 0, считаем его как отсутствующий
    if (rawBalance === 0 || rawBalance === 0.0) {
      rawBalance = null
    }
  }
  
  const rawExpenses = props.summary.expenses || 0
  const vatFactor = props.includeVat ? 1.22 : 1
  const balanceValue = rawBalance !== null ? rawBalance * vatFactor : null
  const expensesValue = rawExpenses * vatFactor
  const currency = props.summary.currency || 'RUB'
  const currencySymbol = currency === 'RUB' ? '₽' : currency
  
  // Format balance value: show dash if balance is null/undefined/0
  const balanceDisplayValue = balanceValue !== null && balanceValue !== 0
    ? balanceValue.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' ' + currencySymbol
    : '—' // Прочерк
  
  return [
  {
    id: 'balance',
    title: 'Баланс',
    value: balanceDisplayValue,
    trend: 0,
    changePositive: true,
    icon: BanknotesIcon,
    iconColor: 'blue'
  },
  {
    id: 'expenses',
    title: 'Расходы',
    value: expensesValue.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' ' + (props.summary.currency === 'RUB' ? '₽' : props.summary.currency),
    trend: Math.abs(props.summary.trends?.expenses || 0),
    changePositive: (props.summary.trends?.expenses || 0) <= 0,
    icon: CurrencyDollarIcon,
    iconColor: 'orange',
    chartColor: '#f97316' // Orange
  },
  {
    id: 'impressions',
    title: 'Показы',
    value: (props.summary.impressions || 0).toLocaleString(),
    trend: props.summary.trends?.impressions || 0,
    changePositive: (props.summary.trends?.impressions || 0) >= 0,
    icon: EyeIcon,
    iconColor: 'blue',
    chartColor: '#3b82f6' // Blue
  },
  {
    id: 'clicks',
    title: 'Переходы',
    value: (props.summary.clicks || 0).toLocaleString(),
    trend: props.summary.trends?.clicks || 0,
    changePositive: (props.summary.trends?.clicks || 0) >= 0,
    icon: ArrowPathIcon,
    iconColor: 'green',
    chartColor: '#22c55e' // Green
  },
  {
    id: 'leads',
    title: 'Лиды',
    value: (props.summary.leads || 0).toLocaleString(),
    trend: props.summary.trends?.leads || 0,
    changePositive: (props.summary.trends?.leads || 0) >= 0,
    icon: UserGroupIcon,
    iconColor: 'red',
    chartColor: '#ef4444' // Red
  },
  {
    id: 'cpc',
    title: 'Sр. CPC',
    value: (props.summary.cpc || 0).toLocaleString() + ' ' + (props.summary.currency === 'RUB' ? '₽' : props.summary.currency),
    trend: Math.abs(props.summary.trends?.cpc || 0),
    changePositive: (props.summary.trends?.cpc || 0) <= 0,
    icon: HandRaisedIcon,
    iconColor: 'purple',
    chartColor: '#a855f7' // Purple
  },
  {
    id: 'cpa',
    title: 'Sр. CPA',
    value: (props.summary.cpa || 0).toLocaleString() + ' ' + (props.summary.currency === 'RUB' ? '₽' : props.summary.currency),
    trend: Math.abs(props.summary.trends?.cpa || 0),
    changePositive: (props.summary.trends?.cpa || 0) <= 0,
    icon: BanknotesIcon,
    iconColor: 'pink'
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
