<template>
  <div class="bg-white w-full rounded-[40px] px-6 sm:px-10 py-6 sm:py-8" >
    <!-- Заголовок и селектор дат -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
      <h3 class="text-lg font-semibold text-gray-900">Эффективность кампаний</h3>
      <div class="flex items-center">
        <div class="flex items-center overflow-hidden rounded-lg ">
          <button 
            v-for="(day, index) in [7, 14, 30]" 
            :key="day"
            :class="[
              'px-3 py-1.5 text-sm font-medium transition-colors',
              selectedDays === day 
                ? 'bg-gray-300 text-black' 
                : 'bg-gray-50 text-gray-700 hover:bg-gray-100',
              index > 0 ? '' : ''
            ]"
            @click="selectedDays = day"
          >
            {{ day }}
          </button>
        </div>
        <button class="ml-2 px-3 py-1.5 bg-gray-50 text-gray-700 hover:bg-gray-100 rounded-lg  transition-colors">
          <img :src="calendarIcon" alt="Calendar" class="w-4 h-4" />
        </button>
      </div>
    </div>
    
    <!-- Легенда -->
    <div class="flex items-center gap-4 sm:gap-6 mb-6 flex-wrap">
      <div class="flex items-center gap-2">
        <div class="w-3 h-3 bg-blue-500 rounded-full"></div>
        <span class="text-sm text-gray-600">Расход</span>
      </div>
      <div class="flex items-center gap-2">
        <div class="w-3 h-3 bg-orange-500 rounded-full"></div>
        <span class="text-sm text-gray-600">Показы</span>
      </div>
      <div class="flex items-center gap-2">
        <div class="w-3 h-3 bg-green-500 rounded-full"></div>
        <span class="text-sm text-gray-600">Переходы</span>
      </div>
      <div class="flex items-center gap-2">
        <div class="w-3 h-3 bg-purple-500 rounded-full"></div>
        <span class="text-sm text-gray-600">Лиды</span>
      </div>
      <div class="flex items-center gap-2">
        <div class="w-3 h-3 bg-red-500 rounded-full"></div>
        <span class="text-sm text-gray-600">CPC</span>
      </div>
      <div class="flex items-center gap-2">
        <div class="w-3 h-3 bg-pink-500 rounded-full"></div>
        <span class="text-sm text-gray-600">CPA</span>
      </div>
    </div>
    
    <div class="h-64 relative pb-6 w-full overflow-hidden">
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
// For other data that might not be in the basic dynamics, we hide them or show zeros for now
const impressionsData = ref([])
const leadsData = ref([])
const cpcData = ref([])
const cpaData = ref([])

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
      fill: false
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
      fill: false
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
      fill: false
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
      fill: false
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
      fill: false
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
      mode: 'index',
      intersect: false
    }
  },
  scales: {
    y: {
      beginAtZero: true,
      ticks: {
        display: false
      },
      grid: {
        color: '#e5e7eb',
        display: true,
        drawBorder: false,
        lineWidth: 1
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


