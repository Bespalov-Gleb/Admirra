<template>
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-5 w-full font-[Inter]">

    <!-- Объединённая карточка: Статистика + Итого (2 колонки) -->
    <div class="lg:col-span-2 bg-white rounded-[10px] shadow-sm border border-gray-100 min-h-[300px] flex overflow-hidden">

      <!-- Левая часть: Статистика -->
      <div class="flex-1 p-6 flex flex-col">
        <div class="flex items-center gap-3 mb-5">
          <div class="w-10 h-10 rounded-[10px] bg-[#EFF6FF] flex items-center justify-center">
            <ChartBarIcon class="w-5 h-5 text-[#2563EB]" />
          </div>
          <div>
            <h3 class="text-[20px] font-bold text-[#09183F]">Статистика по ключевым целям</h3>
            <p class="text-[15px] font-normal text-gray-500 mt-0.5">За период</p>
          </div>
        </div>

        <div v-if="loading || localLoading" class="flex-1 flex flex-col justify-evenly gap-3">
          <div v-for="i in 3" :key="i" class="h-12 bg-gray-100 rounded-[10px] animate-pulse" />
        </div>

        <div v-else-if="topGoals.length === 0" class="flex-1 flex items-center justify-center text-gray-500 text-[14px] font-medium">
          Цели не настроены
        </div>

        <div v-else class="flex-1 flex flex-col justify-evenly">
          <div
            v-for="(goal, index) in topGoals"
            :key="goal.id || goal.name"
            class="flex items-center gap-2 py-2 border-b border-gray-100 last:border-0"
          >
            <span class="text-[20px] font-normal text-gray-500 whitespace-nowrap">{{ formatGoalName(goal.name) }}:</span>
            <div class="flex-1 border-b border-dashed border-gray-300 self-end mb-[7px]" />
            <div class="flex items-center gap-1.5 flex-shrink-0">
              <span class="text-[21px] font-bold text-[#09183F] tabular-nums whitespace-nowrap">{{ (goal.count || 0).toLocaleString('ru-RU') }} шт.</span>
              <span
                v-if="goal.trend != null"
                class="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-[11px] font-semibold whitespace-nowrap"
                :class="goal.trend >= 0 ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-500'"
              >
                <ArrowTrendingUpIcon v-if="goal.trend >= 0" class="w-3 h-3 flex-shrink-0" />
                <ArrowTrendingDownIcon v-else class="w-3 h-3 flex-shrink-0" />
                {{ goal.trend >= 0 ? '+' : '' }}{{ goal.trend }}%
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Правая часть: синий блок Итого — full-height, ml-3, без вертикальных отступов -->
      <div
        class="w-[42%] ml-3 self-stretch rounded-l-[10px] flex flex-col relative overflow-hidden"
        style="background-color: #BFDBFE; background-image: radial-gradient(circle, rgba(255,255,255,0.55) 1.5px, transparent 1.5px); background-size: 14px 14px;"
      >
        <h3 class="text-[23px] font-normal text-white p-5 pb-0">Итого:</h3>
        <!-- Число абсолютно прижато к нижней границе, по центру -->
        <div class="absolute bottom-0 left-0 right-0 flex items-end justify-center overflow-hidden" style="height: 60%;">
          <div class="flex items-baseline gap-2" style="line-height: 0.78; margin-bottom: 0;">
            <span class="font-black text-white tabular-nums tracking-tight" style="font-size: 150px; line-height: 0.78;">{{ totalConversions.toLocaleString('ru-RU') }}</span>
            <span class="font-bold text-white" style="font-size: 54px; line-height: 0.78;">шт.</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Правая: Разбивка по целям (белая карточка) -->
    <div class="bg-white rounded-[10px] p-6 shadow-sm border border-gray-100 min-h-[280px] flex flex-col">
      <h3 class="text-[15px] font-bold text-[#09183F] mb-4">Разбивка по целям</h3>

      <!-- Диаграмма слева + легенда справа -->
      <div class="flex-1 flex items-center gap-4">

        <!-- Donut chart -->
        <div class="relative flex-shrink-0" style="width: 140px; height: 140px;">
          <canvas ref="chartCanvas" class="w-full h-full" />
          <div class="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div class="text-center">
              <p class="text-[15px] font-bold text-[#09183F] tabular-nums leading-tight">{{ totalConversions.toLocaleString('ru-RU') }} шт.</p>
            </div>
          </div>
        </div>

        <!-- Легенда: таблетки справа -->
        <div class="flex-1 flex flex-col gap-2">
          <div
            v-for="(goal, index) in topGoals"
            :key="goal.id || goal.name"
            class="flex items-center gap-2.5 px-3 py-2 rounded-[8px] bg-gray-50"
          >
            <div
              class="w-3 h-3 rounded-full flex-shrink-0"
              :style="{ backgroundColor: donutColors[index] }"
            />
            <span class="text-[13px] font-normal text-[#09183F] truncate">{{ formatGoalName(goal.name) }}</span>
          </div>

          <!-- Dropdown под легендой -->
          <div class="mt-1 relative">
            <select class="w-full h-9 pl-3 pr-8 bg-white border border-gray-200 rounded-[10px] text-[12px] font-normal text-gray-500 outline-none appearance-none focus:border-[#2563EB]">
              <option>Функциональная</option>
            </select>
            <svg class="absolute right-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed, nextTick } from 'vue'
import { Chart, registerables } from 'chart.js'
import { ArrowTrendingUpIcon, ArrowTrendingDownIcon, ChartBarIcon } from '@heroicons/vue/24/solid'
import api from '../../../api/axios'

Chart.register(...registerables)

const props = defineProps({
  goals: { type: Array, default: () => [] },
  clientId: { type: String, default: '' },
  startDate: { type: String, default: '' },
  endDate: { type: String, default: '' },
  loading: { type: Boolean, default: false },
  /** Общее число лидов (summary.leads) — для центра «Итого» и donut */
  totalLeads: { type: Number, default: null }
})

const chartCanvas = ref(null)
let chartInstance = null

const formatGoalName = (name) => name || 'Цель'

const effectiveGoals = computed(() =>
  props.goals?.length > 0 ? props.goals : localGoals.value
)

/** Топ-3 цели по количеству конверсий (самые результативные) */
const topGoals = computed(() => {
  const goals = [...effectiveGoals.value]
  return goals
    .sort((a, b) => (b.count || 0) - (a.count || 0))
    .slice(0, 3)
})

/** Итого: сумма ВСЕХ целей, выбранных пользователем при интеграции (get_goals уже фильтрует по selected_goals) */
const totalConversions = computed(() => {
  return effectiveGoals.value.reduce((sum, g) => sum + (g.count || 0), 0)
})

/** Цвета: насыщенные для внутреннего кольца, пастельные для внешнего */
const donutColors = ['#3B82F6', '#FB923C', '#6EE7B7']
const donutColorsPastel = ['#BFDBFE', '#FED7AA', '#A7F3D0']

const updateChart = () => {
  if (!chartCanvas.value) return
  if (chartInstance) chartInstance.destroy()
  if (!topGoals.value.length || totalConversions.value === 0) return

  const data = topGoals.value.map(g => g.count || 0)
  chartInstance = new Chart(chartCanvas.value, {
    type: 'doughnut',
    data: {
      labels: topGoals.value.map(g => formatGoalName(g.name)),
      datasets: [
        {
          data,
          backgroundColor: topGoals.value.map((_, i) => donutColorsPastel[i]),
          borderWidth: 0,
          hoverOffset: 0,
          weight: 1.8
        },
        {
          data,
          backgroundColor: topGoals.value.map((_, i) => donutColors[i]),
          borderWidth: 0,
          hoverOffset: 4,
          weight: 3
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      cutout: '60%',
      spacing: 0,
      plugins: {
        legend: { display: false },
        datalabels: { display: false }
      },
      layout: { padding: 0 }
    }
  })
}

const fetchGoals = async () => {
  if (!props.clientId || !props.startDate || !props.endDate) return []
  try {
    const { data } = await api.get('dashboard/goals', {
      params: { client_id: props.clientId, date_from: props.startDate, date_to: props.endDate }
    })
    return data || []
  } catch {
    return []
  }
}

const localGoals = ref([])
const localLoading = ref(false)

watch([topGoals, totalConversions], () => {
  if (topGoals.value.length > 0) {
    nextTick(updateChart)
  }
}, { deep: true })

const loadGoals = async () => {
  if (props.goals?.length > 0) return
  if (!props.clientId) {
    localGoals.value = []
    return
  }
  localLoading.value = true
  try {
    localGoals.value = await fetchGoals()
    await nextTick()
    updateChart()
  } finally {
    localLoading.value = false
  }
}

watch(
  () => [props.clientId, props.startDate, props.endDate],
  loadGoals,
  { immediate: true }
)

onMounted(() => {
  if (topGoals.value.length > 0) setTimeout(updateChart, 100)
})

onUnmounted(() => {
  if (chartInstance) chartInstance.destroy()
})
</script>
