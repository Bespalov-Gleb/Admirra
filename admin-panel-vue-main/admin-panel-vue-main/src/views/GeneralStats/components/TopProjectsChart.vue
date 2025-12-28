<template>
  <div class="bg-white rounded-[40px] p-6">
    <div class="flex items-center justify-between mb-6">
      <h3 class="text-lg font-semibold text-gray-900">Топ проектов по Р</h3>
    </div>
    <div class="flex flex-col items-center">
      <!-- Donut Chart -->
      <div class="relative w-48 h-48 mb-6">
        <canvas ref="chartCanvas"></canvas>
        <div class="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div class="text-center">
            <p class="text-2xl font-bold text-gray-900">{{ totalValue }}</p>
            <p class="text-xs text-gray-500">Р</p>
          </div>
        </div>
      </div>
      
      <!-- Легенда -->
      <div class="space-y-3 w-full">
        <div
          v-for="(item, index) in legendItems"
          :key="index"
          class="flex items-center justify-between hover:bg-gray-50 p-2 rounded cursor-pointer transition-colors"
        >
          <div class="flex items-center gap-2">
            <div :class="['w-4 h-4 rounded', colors[index % colors.length]]"></div>
            <span class="text-sm text-gray-700">{{ item.name }}</span>
          </div>
          <span class="text-sm font-semibold text-gray-900">{{ item.percentage }}%</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import {
  Chart,
  ArcElement,
  DoughnutController,
  Tooltip,
  Legend
} from 'chart.js'

Chart.register(ArcElement, DoughnutController, Tooltip, Legend)

const props = defineProps({
  items: {
    type: Array,
    default: () => []
  }
})

const chartCanvas = ref(null)
let chartInstance = null
const colors = ['bg-gray-800', 'bg-gray-600', 'bg-gray-400', 'bg-gray-300', 'bg-gray-200']
const hexColors = ['#1f2937', '#4b5563', '#9ca3af', '#d1d5db', '#e5e7eb']

const totalValue = computed(() => {
  const sum = props.items.reduce((acc, item) => acc + item.expenses, 0)
  if (sum >= 1000) return (sum / 1000).toFixed(1) + 'k'
  return Math.round(sum).toLocaleString()
})

const legendItems = computed(() => props.items)

const initChart = () => {
  if (!chartCanvas.value) return
  
  const data = props.items.map(item => item.expenses)
  const labels = props.items.map(item => item.name)

  chartInstance = new Chart(chartCanvas.value, {
    type: 'doughnut',
    data: {
      labels: labels.length ? labels : ['Нет данных'],
      datasets: [{
        data: data.length ? data : [1],
        backgroundColor: data.length ? hexColors.slice(0, data.length) : ['#f3f4f6'],
        borderWidth: 0,
        cutout: '70%'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { enabled: true }
      }
    }
  })
}

watch(() => props.items, () => {
  if (chartInstance) {
    chartInstance.destroy()
    initChart()
  }
}, { deep: true })

onMounted(() => {
  initChart()
})

onUnmounted(() => {
  if (chartInstance) {
    chartInstance.destroy()
  }
})
</script>

