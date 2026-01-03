<template>
  <div class="!bg-white rounded-[40px] p-6 shadow-sm">
    <div class="flex items-center justify-between mb-6">
      <h3 class="text-lg font-semibold text-gray-900">Топ проектов по Р</h3>
    </div>
    <div class="flex flex-col items-center">
      <!-- Donut Chart -->
      <div class="relative w-48 h-48 mb-6">
        <canvas ref="chartCanvas"></canvas>
        <div class="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div class="text-center">
            <p class="text-2xl font-bold text-gray-900">6.2k</p>
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
            <div :class="['w-4 h-4 rounded', item.color]"></div>
            <span class="text-sm text-gray-700">{{ item.label }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { ChevronRightIcon } from '@heroicons/vue/24/outline'
import {
  Chart,
  ArcElement,
  DoughnutController,
  Tooltip,
  Legend
} from 'chart.js'

Chart.register(ArcElement, DoughnutController, Tooltip, Legend)

const chartCanvas = ref(null)
let chartInstance = null

const legendItems = [
  { label: 'КСИ СТРОЙ', color: 'bg-gray-800' },
  { label: 'Ноутбуки', color: 'bg-gray-400' },
  { label: 'Телефоны', color: 'bg-gray-200' }
]

onMounted(() => {
  if (chartCanvas.value) {
    chartInstance = new Chart(chartCanvas.value, {
      type: 'doughnut',
      data: {
        labels: ['КСИ СТРОЙ', 'Ноутбуки', 'Телефоны'],
        datasets: [{
          data: [60, 30, 10],
          backgroundColor: ['#1f2937', '#9ca3af', '#e5e7eb'],
          borderWidth: 0,
          cutout: '70%'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            enabled: false
          }
        }
      }
    })
  }
})

onUnmounted(() => {
  if (chartInstance) {
    chartInstance.destroy()
  }
})
</script>

