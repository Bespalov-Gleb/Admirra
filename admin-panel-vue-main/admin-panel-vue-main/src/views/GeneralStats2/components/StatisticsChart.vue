<script setup>
import { computed } from 'vue'
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

const props = defineProps({
  labels: {
    type: Array,
    default: () => []
  },
  costs: {
    type: Array,
    default: () => []
  },
  clicks: {
    type: Array,
    default: () => []
  }
})

const chartData = computed(() => ({
  labels: props.labels,
  datasets: [
    {
      label: 'Расходы',
      data: props.costs,
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
      data: props.clicks,
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

const chartOptions = computed(() => {
  const maxVal = Math.max(...props.costs, ...props.clicks, 60)
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: { enabled: true }
    },
    scales: {
      y: {
        beginAtZero: true,
        suggestedMax: maxVal + 10,
        grid: { color: '#e5e7eb' },
        ticks: { display: false }
      },
      x: {
        grid: { display: false },
        ticks: { display: false }
      }
    }
  }
})
</script>

<template>
  <div class="bg-white rounded-[40px] px-10 py-20 h-full">
    <h3 class="text-lg font-semibold text-gray-900 mb-6">Статистика за период</h3>
    <div class="h-64 relative pl-10 pb-6">
      <Line
        :data="chartData"
        :options="chartOptions"
      />
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


