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
            :is-selected="selectedMetric === metric.id"
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
  selectedMetric: {
    type: String,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: 'Общая статистика'
  }
})

defineEmits(['toggle-metric'])

const { containerRef, dragScrollHandlers } = useDragScroll()

const metrics = computed(() => {
  // CRITICAL: Ensure balance is properly converted to number and formatted
  const balanceValue = typeof props.summary.balance === 'number' 
    ? props.summary.balance 
    : parseFloat(props.summary.balance) || 0
  const currency = props.summary.currency || 'RUB'
  const currencySymbol = currency === 'RUB' ? '₽' : currency
  
  return [
  {
    id: 'balance',
    title: 'Баланс',
    value: balanceValue.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' ' + currencySymbol,
    trend: 0,
    changePositive: true,
    icon: BanknotesIcon,
    iconColor: 'blue'
  },
  {
    id: 'expenses',
    title: 'Расходы',
    value: (props.summary.expenses || 0).toLocaleString() + ' ' + (props.summary.currency === 'RUB' ? '₽' : props.summary.currency),
    trend: Math.abs(props.summary.trends?.expenses || 0),
    changePositive: (props.summary.trends?.expenses || 0) <= 0,
    icon: CurrencyDollarIcon,
    iconColor: 'orange'
  },
  {
    id: 'impressions',
    title: 'Показы',
    value: (props.summary.impressions || 0).toLocaleString(),
    trend: props.summary.trends?.impressions || 0,
    changePositive: (props.summary.trends?.impressions || 0) >= 0,
    icon: EyeIcon,
    iconColor: 'blue'
  },
  {
    id: 'clicks',
    title: 'Переходы',
    value: (props.summary.clicks || 0).toLocaleString(),
    trend: props.summary.trends?.clicks || 0,
    changePositive: (props.summary.trends?.clicks || 0) >= 0,
    icon: ArrowPathIcon,
    iconColor: 'green'
  },
  {
    id: 'leads',
    title: 'Лиды',
    value: (props.summary.leads || 0).toLocaleString(),
    trend: props.summary.trends?.leads || 0,
    changePositive: (props.summary.trends?.leads || 0) >= 0,
    icon: UserGroupIcon,
    iconColor: 'red'
  },
  {
    id: 'cpc',
    title: 'Sр. CPC',
    value: (props.summary.cpc || 0).toLocaleString() + ' ' + (props.summary.currency === 'RUB' ? '₽' : props.summary.currency),
    trend: Math.abs(props.summary.trends?.cpc || 0),
    changePositive: (props.summary.trends?.cpc || 0) <= 0,
    icon: HandRaisedIcon,
    iconColor: 'purple'
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
