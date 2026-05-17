<template>
  <div class="w-full font-[Inter]">
    <VueDraggable
      v-model="slotItems"
      :animation="150"
      :delay="120"
      :force-fallback="true"
      :fallback-on-body="true"
      filter=".no-drag"
      ghost-class="opacity-60"
      drag-class="cursor-grabbing"
      class="grid grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-5"
      item-key="slotKey"
      @end="emitSlotConfig"
    >
      <div
        v-for="(element, index) in slotItems"
        :key="element.slotKey"
        class="min-h-0"
      >
        <div
          v-if="element.value"
          class="relative group cursor-grab active:cursor-grabbing"
        >
          <!-- Hint: hold briefly then drag to reorder -->
          <div class="absolute left-2 top-2 w-6 h-6 rounded flex items-center justify-center text-gray-300 pointer-events-none" title="Удерживайте и перетащите для изменения порядка">
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <path d="M8 6h2v2H8V6zm0 4h2v2H8v-2zm0 4h2v2H8v-2zm4-8h2v2h-2V6zm0 4h2v2h-2v-2zm0 4h2v2h-2v-2z"/>
            </svg>
          </div>
          <CardV3
            class="pl-8"
            :title="metricsMap[element.value].title"
            :subtitle="metricsMap[element.value].subtitle"
            :value="metricsMap[element.value].value"
            :trend="metricsMap[element.value].trend"
            :trend-display="metricsMap[element.value].trendDisplay"
            :trend-absolute="metricsMap[element.value].trendAbsolute"
            :change-positive="metricsMap[element.value].changePositive"
            :icon="metricsMap[element.value].icon"
            :icon-color="metricsMap[element.value].iconColor"
            :is-selected="selectedMetrics.includes(element.value)"
            :chart-color="metricsMap[element.value].chartColor"
            @click="$emit('toggle-metric', element.value)"
          />
          <!-- Remove button (no-drag excludes from drag init) -->
          <button
            type="button"
            class="no-drag absolute top-3 right-3 w-6 h-6 rounded-full bg-gray-100 hover:bg-red-50 hover:text-red-500 flex items-center justify-center text-gray-400 transition-colors opacity-0 group-hover:opacity-100 z-20"
            @click.stop="$emit('remove-metric', index)"
            title="Удалить"
          >
            <XMarkIcon class="w-3.5 h-3.5" />
          </button>
        </div>
        <div
          v-else
          class="min-h-[16.6667rem] rounded-[0.6944rem] border-2 border-dashed border-gray-200 dark:border-white/20 hover:border-[#2563EB]/50 dark:hover:border-[#4A7AFF]/50 hover:bg-blue-50/30 dark:hover:bg-white/5 flex flex-col items-center justify-center gap-2 cursor-pointer transition-colors"
          @click="$emit('add-metric', index)"
        >
          <PlusIcon class="w-10 h-10 text-gray-300 dark:text-gray-500" />
          <span class="text-[0.9028rem] font-medium text-gray-400 dark:text-gray-500">Добавить метрику</span>
        </div>
      </div>
    </VueDraggable>
    <div v-if="loading" class="mt-2 h-0.5 bg-blue-500 rounded-full animate-pulse"></div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { VueDraggable } from 'vue-draggable-plus'
import { XMarkIcon, PlusIcon } from '@heroicons/vue/24/outline'
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
  slotConfig: {
    type: Array,
    required: true,
    default: () => ['expenses', 'impressions', 'clicks', 'cpc', 'leads', 'cpa']
  },
  selectedMetrics: {
    type: Array,
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

const emit = defineEmits(['toggle-metric', 'update:slot-config', 'remove-metric', 'add-metric'])

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

const metricsMap = computed(() => {
  const rawExpenses = props.summary.expenses || 0
  const vatFactor = props.includeVat ? 1.22 : 1
  const expensesValue = rawExpenses * vatFactor
  const currency = props.summary.currency === 'RUB' ? '₽' : props.summary.currency
  const t = props.summary.trends || {}

  const map = {}
  const items = [
    {
      id: 'expenses',
      title: 'Расходы',
      subtitle: 'За период',
      value: expensesValue.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' ' + currency,
      trend: t.expenses ?? 0,
      trendDisplay: `${(t.expenses ?? 0) >= 0 ? '+' : ''}${(t.expenses ?? 0).toFixed(1)}%`,
      trendAbsolute: formatAbsoluteChange(expensesValue, t.expenses ?? 0, { suffix: ' ' + currency, decimals: 2 }),
      changePositive: (t.expenses ?? 0) <= 0, // снижение расходов = хорошо = зелёный
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
      changePositive: (t.cpa ?? 0) <= 0, // снижение CPA = хорошо (дешевле лид) = зелёный
      icon: CheckBadgeIcon,
      iconColor: 'blue',
      chartColor: '#EB8525'
    }
  ]
  items.forEach(m => { map[m.id] = m })
  return map
})

// Slot items for VueDraggable: [{ slotKey, value }, ...]
const slotItems = ref([])

function syncFromSlotConfig() {
  const cfg = props.slotConfig
  const result = []
  for (let i = 0; i < 6; i++) {
    const v = cfg[i]
    result.push({
      slotKey: `slot-${i}-${v ?? 'empty'}`,
      value: v || null
    })
  }
  slotItems.value = result
}

function emitSlotConfig() {
  const values = slotItems.value.map(s => s.value)
  emit('update:slot-config', values)
}

watch(() => props.slotConfig, () => {
  syncFromSlotConfig()
}, { immediate: true, deep: true })
</script>
