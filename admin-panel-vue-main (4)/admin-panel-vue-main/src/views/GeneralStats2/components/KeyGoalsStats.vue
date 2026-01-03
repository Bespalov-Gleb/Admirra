<template>
  <div class="grid grid-cols-1 lg:grid-cols-12 gap-4">
    <!-- Левая панель - Статистика по ключевым целям -->
    <div class="lg:col-span-8 bg-gray-900 rounded-[40px] p-6 sm:p-8 text-white">
      <div class="flex items-center gap-3 mb-6">
        <div class="w-10 h-10 sm:w-12 sm:h-12 rounded-lg bg-gray-800 flex items-center justify-center flex-shrink-0">
          <ShoppingBagIcon class="w-6 h-6 sm:w-7 sm:h-7 text-gray-300" />
        </div>
        <div>
          <h3 class="text-base sm:text-lg font-semibold text-white">Статистика по ключевым целям:</h3>
          <p class="text-xs sm:text-sm text-gray-400">за период</p>
        </div>
      </div>

      <div class="space-y-4 sm:space-y-5 mb-6">
        <!-- Звонки -->
        <div class="flex items-center justify-between">
          <span class="text-lg sm:text-xl text-gray-300">Звонки: 14 шт</span>
          <div class="flex items-center gap-1.5">
            <ArrowTrendingUpIcon class="w-6 h-6 text-green-500" />
            <span class="text-lg sm:text-xl text-green-500 font-medium">+15.6%</span>
          </div>
        </div>

        <!-- Лиды с quiz -->
        <div class="flex items-center justify-between">
          <span class="text-lg sm:text-xl text-gray-300">Лиды с quiz: 39 шт</span>
          <div class="flex items-center gap-1.5">
            <ArrowTrendingUpIcon class="w-6 h-6 text-green-500" />
            <span class="text-lg sm:text-xl text-green-500 font-medium">+15.6%</span>
          </div>
        </div>

        <!-- Лиды с форм -->
        <div class="flex items-center justify-between">
          <span class="text-lg sm:text-xl text-gray-300">Лиды с форм: 20 шт</span>
          <div class="flex items-center gap-1.5">
            <ArrowTrendingUpIcon class="w-6 h-6 text-green-500" />
            <span class="text-lg sm:text-xl text-green-500 font-medium">+15.6%</span>
          </div>
        </div>
      </div>

      <!-- Итого -->
      <div class="text-right">
        <p class="text-3xl sm:text-4xl font-bold text-white">Итого: 130 шт</p>
      </div>
    </div>

    <!-- Правая панель - Разбивка по целям -->
    <div class="lg:col-span-4 !bg-white rounded-[40px] p-6 sm:p-8 shadow-sm">
      <h3 class="text-base sm:text-lg font-semibold text-gray-900 mb-6">Разбивка по целям</h3>
      
      <!-- Донат-чарт -->
      <div class="relative flex items-center justify-center mb-6">
        <div class="relative w-48 h-48 sm:w-56 sm:h-56">
          <canvas ref="chartCanvas"></canvas>
          <div class="absolute inset-0 flex items-center justify-center">
            <div class="text-center">
              <p class="text-2xl sm:text-3xl font-bold text-gray-900">130</p>
              <p class="text-xs sm:text-sm text-gray-500">шт</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Легенда -->
      <div class="space-y-2">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <div class="w-3 h-3 sm:w-4 sm:h-4 bg-gray-900 rounded"></div>
            <span class="text-xs sm:text-sm text-gray-700">Звонки</span>
          </div>
        </div>
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <div class="w-3 h-3 sm:w-4 sm:h-4 bg-gray-500 rounded"></div>
            <span class="text-xs sm:text-sm text-gray-700">Quiz</span>
          </div>
        </div>
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <div class="w-3 h-3 sm:w-4 sm:h-4 bg-gray-300 rounded"></div>
            <span class="text-xs sm:text-sm text-gray-700">Формы</span>
          </div>
          <ChevronRightIcon class="w-4 h-4 sm:w-5 sm:h-5 text-gray-400" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { Chart, registerables } from 'chart.js'
import {
  ShoppingBagIcon,
  ArrowTrendingUpIcon,
  ChevronRightIcon
} from '@heroicons/vue/24/outline'

Chart.register(...registerables)

const chartCanvas = ref(null)
let chartInstance = null

onMounted(() => {
  if (chartCanvas.value) {
    chartInstance = new Chart(chartCanvas.value, {
      type: 'doughnut',
      data: {
        labels: ['Звонки', 'Quiz', 'Формы'],
        datasets: [{
          data: [14, 39, 20],
          backgroundColor: ['#1f2937', '#6b7280', '#d1d5db'],
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

