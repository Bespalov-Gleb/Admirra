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
import { ref, computed, onMounted, onUnmounted } from 'vue'
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

// Data from props
const dateLabels = computed(() => props.dynamics.labels || [])
const expensesData = computed(() => props.dynamics.costs || [])
const clicksData = computed(() => props.dynamics.clicks || [])
const impressionsData = computed(() => props.dynamics.impressions || [])
const leadsData = computed(() => props.dynamics.leads || [])
const cpcData = computed(() => props.dynamics.cpc || [])
const cpaData = computed(() => props.dynamics.cpa || [])

const chartKey = ref(0)

const chartData = computed(() => ({
  labels: dateLabels.value,
  datasets: [
    {
      label: 'Расход',
      data: expensesData.value,
      borderColor: '#3b82f6', // blue-500
      backgroundColor: 'transparent',
      borderWidth: isMobile.value ? 2 : 3,
      pointRadius: isMobile.value ? 4 : 5,
      pointBackgroundColor: '#3b82f6',
      pointBorderColor: '#ffffff',
      pointBorderWidth: isMobile.value ? 2 : 2.5,
      tension: 0.4,
      fill: false,
      yAxisID: 'y_money'
    },
    {
      label: 'Показы',
      data: impressionsData.value,
      borderColor: '#f97316', // orange-500
      backgroundColor: 'transparent',
      borderWidth: isMobile.value ? 2 : 2.5,
      pointRadius: isMobile.value ? 3 : 4,
      pointBackgroundColor: '#f97316',
      pointBorderColor: '#ffffff',
      pointBorderWidth: isMobile.value ? 1.5 : 2,
      tension: 0.4,
      fill: false,
      yAxisID: 'y_count'
    },
    {
      label: 'Переходы',
      data: clicksData.value,
      borderColor: '#22c55e', // green-500
      backgroundColor: 'transparent',
      borderWidth: isMobile.value ? 2 : 2.5,
      pointRadius: isMobile.value ? 3 : 4,
      pointBackgroundColor: '#22c55e',
      pointBorderColor: '#ffffff',
      pointBorderWidth: isMobile.value ? 1.5 : 2,
      tension: 0.4,
      fill: false,
      yAxisID: 'y_count'
    },
    {
      label: 'Лиды',
      data: leadsData.value,
      borderColor: '#a855f7', // purple-500
      backgroundColor: 'transparent',
      borderWidth: isMobile.value ? 2 : 2.5,
      pointRadius: isMobile.value ? 3 : 4,
      pointBackgroundColor: '#a855f7',
      pointBorderColor: '#ffffff',
      pointBorderWidth: isMobile.value ? 1.5 : 2,
      tension: 0.4,
      fill: false,
      yAxisID: 'y_count'
    },
    {
      label: 'CPC',
      data: cpcData.value,
      borderColor: '#ef4444', // red-500
      backgroundColor: 'transparent',
      borderWidth: isMobile.value ? 2 : 2.5,
      pointRadius: isMobile.value ? 3 : 4,
      pointBackgroundColor: '#ef4444',
      pointBorderColor: '#ffffff',
      pointBorderWidth: isMobile.value ? 1.5 : 2,
      tension: 0.4,
      fill: false,
      yAxisID: 'y_money'
    },
    {
      label: 'CPA',
      data: cpaData.value,
      borderColor: '#ec4899', // pink-500
      backgroundColor: 'transparent',
      borderWidth: isMobile.value ? 2 : 2.5,
      pointRadius: isMobile.value ? 3 : 4,
      pointBackgroundColor: '#ec4899',
      pointBorderColor: '#ffffff',
      pointBorderWidth: isMobile.value ? 1.5 : 2,
      tension: 0.4,
      fill: false,
      yAxisID: 'y_money'
    }
  ]
}))

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
      backgroundColor: 'rgba(255, 255, 255, 0.9)',
      titleColor: '#111827',
      bodyColor: '#4b5563',
      borderColor: '#e5e7eb',
      borderWidth: 1,
      padding: 12,
      boxPadding: 6,
      usePointStyle: true,
      callbacks: {
        label: function(context) {
          let label = context.dataset.label || '';
          if (label) {
            label += ': ';
          }
          if (context.parsed.y !== null) {
            if (['Расход', 'CPC', 'CPA'].includes(context.dataset.label)) {
              label += new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB' }).format(context.parsed.y);
            } else {
              label += new Intl.NumberFormat('ru-RU').format(context.parsed.y);
            }
          }
          return label;
        }
      }
    }
  },
  scales: {
    y_money: {
      type: 'linear',
      display: false, // Мы скрываем оси как на картинке, оставляя только сетку
      position: 'left',
      beginAtZero: true,
      grid: {
        color: '#f3f4f6',
        drawBorder: false,
      }
    },
    y_count: {
      type: 'linear',
      display: false,
      position: 'right',
      beginAtZero: true,
      grid: {
        drawOnChartArea: false, // Отключаем дублирующуюся сетку
      }
    },
    x: {
      grid: {
        display: false
      },
      ticks: {
        display: true,
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


