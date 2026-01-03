<template>
  <div class="!bg-white rounded-[40px] px-10 py-20 h-full shadow-sm">
    <h3 class="text-lg font-semibold text-gray-900 mb-6">Статистика за период</h3>
    <div class="h-64 relative pl-10 pb-6">
      <Line
        :data="chartData"
        :options="chartOptions"
        :key="chartKey"
      />
      
      <!-- Шкала Y -->
      <div class="absolute left-0 top-0 bottom-6 flex flex-col justify-between text-xs text-gray-500 pointer-events-none">
        <span>60</span>
        <span>50</span>
        <span>40</span>
        <span>30</span>
        <span>20</span>
        <span>10</span>
        <span>0</span>
      </div>
    </div>
    
    <!-- Легенда -->
    <div class="flex items-center gap-6 mt-4">
      <div class="flex items-center gap-2">
        <div class="w-3 h-3 bg-gray-800 rounded-full"></div>
        <span class="text-sm text-gray-600">Расходы</span>
      </div>
      <div class="flex items-center gap-2">
        <div class="w-3 h-3 bg-gray-400 rounded-full"></div>
        <span class="text-sm text-gray-600">Переходы</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
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

const dateLabels = ref(['03 Ср', '04 Чт', '05 Пт', '06 Сб', '07 Вс', '08 Пн', '09 Вт', '10 Ср', '11 Чт', '12 Пт', '13 Сб', '14 Вс', '15 Пн', '16 Вт'])

const earningsData = ref([30, 35, 45, 35, 40, 60, 50, 10, 35, 30, 25, 10, 40, 50])
const costsData = ref([50, 20, 35, 20, 30, 40, 35, 20, 30, 40, 35, 20, 30, 30])

const chartKey = ref(0)

const chartData = computed(() => ({
  labels: dateLabels.value,
  datasets: [
    {
      label: 'Расходы',
      data: earningsData.value,
      borderColor: '#1f2937',
      backgroundColor: 'transparent',
      borderWidth: 2.5,
      pointRadius: 5,
      pointBackgroundColor: '#1f2937',
      pointBorderColor: '#ffffff',
      pointBorderWidth: 2,
      tension: 0.4,
      fill: false
    },
    {
      label: 'Переходы',
      data: costsData.value,
      borderColor: '#9ca3af',
      backgroundColor: 'transparent',
      borderWidth: 2.5,
      pointRadius: 5,
      pointBackgroundColor: '#9ca3af',
      pointBorderColor: '#ffffff',
      pointBorderWidth: 2,
      tension: 0.4,
      fill: false
    }
  ]
}))

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
          size: 11
        },
        color: '#6b7280',
        maxRotation: 0,
        minRotation: 0
      }
    }
  }
}))
</script>


