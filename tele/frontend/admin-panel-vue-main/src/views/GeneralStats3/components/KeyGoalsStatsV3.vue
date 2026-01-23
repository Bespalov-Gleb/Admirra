<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { Chart, registerables } from 'chart.js'
import {
  ShoppingBagIcon,
  ArrowTrendingUpIcon,
  ChevronRightIcon
} from '@heroicons/vue/24/solid'

Chart.register(...registerables)

const props = defineProps({
  goals: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const chartCanvas = ref(null)
let chartInstance = null

const totalConversions = computed(() => props.goals.reduce((sum, g) => sum + (g.count || 0), 0))

const updateChart = () => {
  if (!chartCanvas.value) return
  
  if (chartInstance) {
    chartInstance.destroy()
  }

  if (!props.goals || props.goals.length === 0) return

  chartInstance = new Chart(chartCanvas.value, {
    type: 'doughnut',
    data: {
      labels: props.goals.map(g => g.name),
      datasets: [{
        data: props.goals.map(g => g.count),
        backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'],
        borderWidth: 4,
        borderColor: '#ffffff',
        hoverOffset: 10,
        backgroundColor: [
          'rgba(59, 130, 246, 0.8)',
          'rgba(16, 185, 129, 0.8)',
          'rgba(245, 158, 11, 0.8)',
          'rgba(239, 68, 68, 0.8)',
          'rgba(139, 92, 246, 0.8)',
          'rgba(236, 72, 153, 0.8)'
        ]
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '75%',
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#1f2937',
          padding: 12,
          cornerRadius: 12,
          titleFont: { size: 12, weight: 'bold' },
          bodyFont: { size: 12 }
        }
      }
    }
  })
}

onMounted(() => {
  setTimeout(updateChart, 100)
})

watch(() => props.goals, () => {
  setTimeout(updateChart, 100)
}, { deep: true })

onUnmounted(() => {
  if (chartInstance) {
    chartInstance.destroy()
  }
})

const colors = [
  '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'
]
</script>

<template>
  <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 w-full">
    <!-- Левая панель - Статистика по ключевым целям -->
    <div class="lg:col-span-8 bg-gray-900 rounded-[40px] p-8 sm:p-10 text-white shadow-xl relative overflow-hidden group">
      <!-- Background Glow decor -->
      <div class="absolute -top-24 -right-24 w-64 h-64 bg-blue-600/20 rounded-full blur-[100px] group-hover:bg-blue-600/30 transition-all"></div>
      
      <div class="relative z-10">
        <div class="flex items-center gap-4 mb-10">
          <div class="w-12 h-12 sm:w-14 sm:h-14 rounded-2xl bg-white/10 backdrop-blur-md flex items-center justify-center flex-shrink-0 border border-white/10">
            <ShoppingBagIcon class="w-6 h-6 sm:w-8 sm:h-8 text-blue-400" />
          </div>
          <div>
            <h3 class="text-lg sm:text-xl font-black text-white uppercase tracking-wider">Ключевые цели</h3>
            <p class="text-xs font-bold text-gray-500 uppercase tracking-widest">данные Яндекс.Метрики</p>
          </div>
        </div>

        <div v-if="loading" class="space-y-6 mb-10">
          <div v-for="i in 3" :key="i" class="h-8 bg-white/5 rounded-xl animate-pulse"></div>
        </div>

        <div v-else-if="goals.length === 0" class="py-10 text-center text-gray-500 font-bold uppercase tracking-widest">
          Цели не настроены
        </div>

        <div v-else class="space-y-6 sm:space-y-8 mb-10">
          <div 
            v-for="(goal, index) in goals" 
            :key="goal.name" 
            class="flex items-center justify-between group/item"
          >
            <div class="flex items-center gap-4">
               <div 
                class="w-1.5 h-6 rounded-full"
                :style="{ backgroundColor: colors[index % colors.length] }"
              ></div>
              <span class="text-base sm:text-lg font-bold text-gray-300 group-hover/item:text-white transition-colors">
                {{ goal.name }}
              </span>
            </div>
            <div class="flex items-center gap-6">
              <span class="text-lg sm:text-xl font-black">{{ (goal.count || 0).toLocaleString() }}</span>
              <div class="flex items-center gap-1 min-w-[70px] justify-end" v-if="goal.trend">
                <ArrowTrendingUpIcon class="w-4 h-4 text-green-400" />
                <span class="text-sm font-black text-green-400">+{{ goal.trend }}%</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Итого -->
        <div class="flex items-center justify-between pt-8 border-t border-white/5">
          <span class="text-sm font-black text-gray-500 uppercase tracking-[0.3em]">Суммарный результат</span>
          <p class="text-3xl sm:text-5xl font-black text-transparent bg-clip-text bg-gradient-to-r from-white to-gray-500">
            {{ totalConversions.toLocaleString() }}
          </p>
        </div>
      </div>
    </div>

    <!-- Правая панель - Разбивка по целям -->
    <div class="lg:col-span-4 bg-white rounded-[40px] p-8 sm:p-10 shadow-sm border border-gray-50 flex flex-col items-center">
      <h3 class="text-xs font-black text-gray-400 uppercase tracking-[0.2em] mb-10 self-start">Распределение</h3>
      
      <!-- Донат-чарт -->
      <div class="relative flex items-center justify-center mb-10 w-full flex-grow">
        <div class="relative w-48 h-48 sm:w-64 sm:h-64">
          <canvas ref="chartCanvas"></canvas>
          <div class="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div class="text-center">
              <p class="text-3xl sm:text-5xl font-black text-gray-900 leading-none mb-1">{{ totalConversions }}</p>
              <p class="text-[10px] sm:text-[11px] font-black text-gray-400 uppercase tracking-[0.2em]">КОНВЕРСИЙ</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Легенда -->
      <div class="w-full space-y-3">
        <div 
          v-for="(goal, index) in goals" 
          :key="goal.name" 
          class="flex items-center justify-between p-3 rounded-2xl hover:bg-gray-50 transition-all group"
        >
          <div class="flex items-center gap-3 overflow-hidden">
            <div 
              class="w-3 h-3 rounded-full flex-shrink-0 shadow-sm"
              :style="{ backgroundColor: colors[index % colors.length] }"
            ></div>
            <span class="text-sm font-bold text-gray-600 truncate group-hover:text-gray-900">{{ goal.name }}</span>
          </div>
          <ChevronRightIcon class="w-4 h-4 text-gray-300 group-hover:translate-x-1 transition-transform" />
        </div>
      </div>
    </div>
  </div>
</template>
