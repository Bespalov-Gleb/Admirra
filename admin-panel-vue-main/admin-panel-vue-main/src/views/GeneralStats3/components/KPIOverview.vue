<template>
  <div class="w-full">
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-xs font-bold text-gray-500 uppercase tracking-wider">{{ title }}</h2>
    </div>

    <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
      <div v-for="metric in metrics" :key="metric.id">
        <CardV3
          :title="metric.title"
          :value="metric.value"
          :trend="metric.trend"
          :change-positive="metric.changePositive"
          :change-text="metric.changeText"
          :icon="metric.icon"
          :icon-color="metric.iconColor"
          :is-selected="selectedMetrics.includes(metric.id)"
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
  CurrencyDollarIcon,
  EyeIcon,
  ArrowPathIcon,
  UserGroupIcon,
  HandRaisedIcon,
  BanknotesIcon
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

const metrics = computed(() => {
  const rawExpenses = props.summary.expenses || 0
  const vatFactor = props.includeVat ? 1.22 : 1
  const expensesValue = rawExpenses * vatFactor
  const changeText = 'за эту неделю'
  return [
  {
    id: 'expenses',
    title: 'Расходы',
    value: expensesValue.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' ' + (props.summary.currency === 'RUB' ? '₽' : props.summary.currency),
    trend: Math.abs(props.summary.trends?.expenses || 0),
    changePositive: (props.summary.trends?.expenses || 0) <= 0,
    changeText,
    icon: CurrencyDollarIcon,
    iconColor: 'blue',
    chartColor: '#3b82f6'
  },
  {
    id: 'impressions',
    title: 'Показы',
    value: (props.summary.impressions || 0).toLocaleString(),
    trend: props.summary.trends?.impressions || 0,
    changePositive: (props.summary.trends?.impressions || 0) >= 0,
    changeText,
    icon: EyeIcon,
    iconColor: 'blue',
    chartColor: '#3b82f6'
  },
  {
    id: 'clicks',
    title: 'Клики',
    value: (props.summary.clicks || 0).toLocaleString(),
    trend: props.summary.trends?.clicks || 0,
    changePositive: (props.summary.trends?.clicks || 0) >= 0,
    changeText,
    icon: ArrowPathIcon,
    iconColor: 'blue',
    chartColor: '#3b82f6'
  },
  {
    id: 'cpc',
    title: 'CPC',
    value: (props.summary.cpc || 0).toLocaleString() + ' ' + (props.summary.currency === 'RUB' ? '₽' : props.summary.currency),
    trend: Math.abs(props.summary.trends?.cpc || 0),
    changePositive: (props.summary.trends?.cpc || 0) <= 0,
    changeText,
    icon: HandRaisedIcon,
    iconColor: 'blue',
    chartColor: '#3b82f6'
  },
  {
    id: 'leads',
    title: 'Лиды',
    value: (props.summary.leads || 0).toLocaleString() + ' шт.',
    trend: props.summary.trends?.leads || 0,
    changePositive: (props.summary.trends?.leads || 0) >= 0,
    changeText,
    icon: UserGroupIcon,
    iconColor: 'blue',
    chartColor: '#3b82f6'
  },
  {
    id: 'cpa',
    title: 'CPA',
    value: (props.summary.cpa || 0).toLocaleString() + ' ' + (props.summary.currency === 'RUB' ? '₽' : props.summary.currency),
    trend: Math.abs(props.summary.trends?.cpa || 0),
    changePositive: (props.summary.trends?.cpa || 0) <= 0,
    changeText,
    icon: BanknotesIcon,
    iconColor: 'blue',
    chartColor: '#3b82f6'
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
