<template>
  <div class="!bg-white rounded-[20px] sm:rounded-[40px] px-3 sm:px-6 py-4 sm:py-6 h-full shadow-sm">
    <h3 class="text-base sm:text-lg font-semibold text-gray-900 mb-4 sm:mb-6">Динамика</h3>
    <div class="h-48 sm:h-64 relative pl-6 sm:pl-10 pb-6">
      <Line
        :data="chartData"
        :options="chartOptions"
        :key="chartKey"
      />
      
      
      <!-- Шкала Y -->
      <div class="absolute left-0 top-0 bottom-8 sm:bottom-6 flex flex-col justify-between text-[10px] sm:text-xs text-gray-500 pointer-events-none">
        <span>60</span>
        <span class="hidden sm:inline">50</span>
        <span>40</span>
        <span class="hidden sm:inline">30</span>
        <span>20</span>
        <span class="hidden sm:inline">10</span>
        <span>0</span>
      </div>
    </div>
    
    <!-- Легенда -->
    <div class="flex items-center gap-3 sm:gap-6 mt-3 sm:mt-4 flex-wrap">
      <div class="flex items-center gap-1.5 sm:gap-2">
        <div class="w-2.5 h-2.5 sm:w-3 sm:h-3 bg-gray-800 rounded-full"></div>
        <span class="text-xs sm:text-sm text-gray-600">Расходы</span>
      </div>
      <div class="flex items-center gap-1.5 sm:gap-2">
        <div class="w-2.5 h-2.5 sm:w-3 sm:h-3 bg-gray-400 rounded-full"></div>
        <span class="text-xs sm:text-sm text-gray-600">Переходы</span>
      </div>
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

const dateLabels = ref(['03 Ср', '04 Чт', '05 Пт', '06 Сб', '07 Вс', '08 Пн', '09 Вт', '10 Ср', '11 Чт', '12 Пт', '13 Сб', '14 Вс', '15 Пн', '16 Вт'])

const expensesData = ref([30, 35, 45, 35, 40, 60, 50, 10, 35, 30, 25, 10, 40, 50])
const clicksData = ref([50, 20, 35, 20, 30, 40, 35, 20, 30, 40, 35, 20, 30, 30])

const chartKey = ref(0)

const chartData = computed(() => ({
  labels: dateLabels.value,
  datasets: [
    {
      label: 'Расходы',
      data: expensesData.value,
      borderColor: '#1f2937',
      backgroundColor: 'transparent',
      borderWidth: isMobile.value ? 2 : 2.5,
      pointRadius: isMobile.value ? 3 : 5,
      pointBackgroundColor: '#1f2937',
      pointBorderColor: '#ffffff',
      pointBorderWidth: isMobile.value ? 1.5 : 2,
      tension: 0.4,
      fill: false
    },
    {
      label: 'Переходы',
      data: clicksData.value,
      borderColor: '#9ca3af',
      backgroundColor: 'transparent',
      borderWidth: isMobile.value ? 2 : 2.5,
      pointRadius: isMobile.value ? 3 : 5,
      pointBackgroundColor: '#9ca3af',
      pointBorderColor: '#ffffff',
      pointBorderWidth: isMobile.value ? 1.5 : 2,
      tension: 0.4,
      fill: false
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
      backgroundColor: 'rgba(0, 0, 0, 0.8)',
      padding: 12,
      titleFont: {
        size: 12,
        weight: 'bold'
      },
      bodyFont: {
        size: 11
      },
      callbacks: {
        title: function(context) {
          return context[0].label || ''
        },
        label: function(context) {
          const label = context.dataset.label || ''
          const value = context.parsed.y
          return `${label}: ${value}`
        }
      }
    }
  },
  scales: {
    y: {
      beginAtZero: true,
      max: 60,
      ticks: {
        stepSize: 10,
        display: false
      },
      grid: {
        color: '#e5e7eb',
        display: true
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
        color: '#6b7280',
        maxRotation: 0,
        minRotation: 0
      }
    }
  }
}))
</script>

