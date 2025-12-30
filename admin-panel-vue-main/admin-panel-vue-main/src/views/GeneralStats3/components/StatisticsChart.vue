<template>
  <div class="bg-white w-full rounded-[40px] px-6 sm:px-10 py-6 sm:py-8 shadow-sm">
    <!-- Заголовок и селектор дат -->
    <div class="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-2">
      <div>
        <h3 class="text-xl font-bold text-gray-900 mb-6">Эффективность кампаний</h3>
        
        <!-- Легенда (теперь явно под заголовком как на фото) -->
        <div class="flex items-center gap-4 sm:gap-6 mb-6 flex-wrap">
          <div class="flex items-center gap-2">
            <div class="w-2.5 h-2.5 bg-blue-500 rounded-full"></div>
            <span class="text-xs font-semibold text-gray-500">Расход</span>
          </div>
          <div class="flex items-center gap-2">
            <div class="w-2.5 h-2.5 bg-orange-500 rounded-full"></div>
            <span class="text-xs font-semibold text-gray-500">Показы</span>
          </div>
          <div class="flex items-center gap-2">
            <div class="w-2.5 h-2.5 bg-green-500 rounded-full"></div>
            <span class="text-xs font-semibold text-gray-500">Переходы</span>
          </div>
          <div class="flex items-center gap-2">
            <div class="w-2.5 h-2.5 bg-purple-500 rounded-full"></div>
            <span class="text-xs font-semibold text-gray-500">Лиды</span>
          </div>
          <div class="flex items-center gap-2">
            <div class="w-2.5 h-2.5 bg-red-500 rounded-full"></div>
            <span class="text-xs font-semibold text-gray-500">CPC</span>
          </div>
          <div class="flex items-center gap-2">
            <div class="w-2.5 h-2.5 bg-pink-500 rounded-full"></div>
            <span class="text-xs font-semibold text-gray-500">CPA</span>
          </div>
        </div>
      </div>

      <div class="flex items-center self-end sm:self-auto">
        <div class="flex items-center bg-gray-50 rounded-xl p-1 shadow-inner">
          <button 
            v-for="day in [7, 14, 30]" 
            :key="day"
            :class="[
              'px-4 py-1.5 text-xs font-bold rounded-lg transition-all',
              selectedDays === day 
                ? 'bg-white text-gray-900 shadow-sm' 
                : 'text-gray-400 hover:text-gray-600'
            ]"
            @click="selectedDays = day"
          >
            {{ day }}
          </button>
        </div>
        <button class="ml-3 p-2 bg-gray-50 text-gray-400 hover:text-gray-600 rounded-xl transition-all shadow-sm">
          <img :src="calendarIcon" alt="Calendar" class="w-4 h-4 opacity-60" />
        </button>
      </div>
    </div>
    
    <div class="h-72 relative w-full pt-4">
      <Line
        :data="chartData"
        :options="chartOptions"
        :key="chartKey"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  LineController,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'
import calendarIcon from '../../../assets/dash/calendar.svg'

const props = defineProps({
  dynamics: {
    type: Object,
    required: true,
    default: () => ({
      labels: [],
      costs: [],
      clicks: []
    })
  }
})

const selectedDays = ref(7)

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  LineController,
  Tooltip,
  Legend,
  Filler
)

const isMobile = ref(window.innerWidth < 640)
const chartKey = ref(0)

// Перерисовываем график при изменении данных
watch(() => props.dynamics, () => {
  chartKey.value++
}, { deep: true })

// Data from props
const dateLabels = computed(() => props.dynamics.labels || [])
const expensesData = computed(() => props.dynamics.costs || [])
const clicksData = computed(() => props.dynamics.clicks || [])
const impressionsData = computed(() => props.dynamics.impressions || [])
const leadsData = computed(() => props.dynamics.leads || [])
const cpcData = computed(() => props.dynamics.cpc || [])
const cpaData = computed(() => props.dynamics.cpa || [])

// Helper to normalize data for visual display
const normalizeDataset = (data, label, color, offset = 0) => {
  // Defensive check: ensure data is a valid array of numbers
  const cleanData = Array.isArray(data) ? data.map(v => Number(v) || 0) : []
  
  if (cleanData.length === 0) {
    return {
      label,
      data: [],
      borderColor: color,
      backgroundColor: 'transparent',
      borderWidth: isMobile.value ? 2 : 2.5,
      tension: 0.4,
      fill: false,
      yAxisID: 'y_normalized'
    }
  }

  const max = Math.max(...cleanData, 0)
  const safeMax = max === 0 ? 1 : max
  
  return {
    label,
    data: cleanData.map(val => ({
      y: (val / safeMax) * 0.4 + offset, // Scale down and add offset
      realValue: val
    })),
    borderColor: color,
    backgroundColor: 'transparent',
    borderWidth: isMobile.value ? 2 : 2.5,
    pointRadius: isMobile.value ? 3 : 4,
    pointBackgroundColor: color,
    pointBorderColor: '#ffffff',
    pointBorderWidth: isMobile.value ? 1.5 : 2,
    tension: 0.4,
    fill: false,
    yAxisID: 'y_normalized'
  }
}

const chartData = computed(() => {
  console.log('StatisticsChart: Received dynamics data:', props.dynamics)
  
  if (!props.dynamics || !props.dynamics.labels || props.dynamics.labels.length === 0) {
    return { labels: [], datasets: [] }
  }

  return {
    labels: props.dynamics.labels,
    datasets: [
      {
        ...normalizeDataset(props.dynamics.costs, 'Расход', '#3b82f6', 0.5),
        borderWidth: isMobile.value ? 2 : 3,
        pointRadius: isMobile.value ? 4 : 5,
      },
      normalizeDataset(props.dynamics.impressions, 'Показы', '#f97316', 0.4),
      normalizeDataset(props.dynamics.clicks, 'Переходы', '#22c55e', 0.3),
      normalizeDataset(props.dynamics.leads, 'Лиды', '#a855f7', 0.2),
      normalizeDataset(props.dynamics.cpc, 'CPC', '#ef4444', 0.1),
      normalizeDataset(props.dynamics.cpa, 'CPA', '#ec4899', 0),
    ]
  }
})

const handleResize = () => {
  isMobile.value = window.innerWidth < 640
  chartKey.value++
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    mode: 'index',
    intersect: false,
  },
  animation: {
    duration: 1000,
    easing: 'easeInOutQuart'
  },
  plugins: {
    legend: {
      display: false
    },
    tooltip: {
      enabled: true,
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      titleColor: '#111827',
      titleFont: { size: 14, weight: 'bold' },
      bodyColor: '#4b5563',
      bodyFont: { size: 12 },
      borderColor: '#e5e7eb',
      borderWidth: 1,
      padding: 12,
      boxPadding: 8,
      usePointStyle: true,
      callbacks: {
        label: function(context) {
          let label = context.dataset.label || '';
          if (label) {
            label += ': ';
          }
          const realValue = context.raw.realValue;
          if (realValue !== undefined) {
            if (['Расход', 'CPC', 'CPA'].includes(context.dataset.label)) {
              label += new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', minimumFractionDigits: 2 }).format(realValue);
            } else {
              label += new Intl.NumberFormat('ru-RU').format(realValue);
            }
          }
          return label;
        }
      }
    }
  },
  scales: {
    y_normalized: {
      type: 'linear',
      display: false,
      beginAtZero: true,
      max: 1.1, // Add some headroom at the top
      grid: {
        color: '#f3f4f6',
        drawBorder: false,
      }
    },
    x: {
      grid: {
        display: false
      },
      ticks: {
        display: true,
        autoSkip: true,
        maxTicksLimit: isMobile.value ? 5 : 10,
        font: {
          size: isMobile.value ? 9 : 11
        },
        color: '#9ca3af',
        maxRotation: 0,
        minRotation: 0
      }
    }
  }
}))
</script>


