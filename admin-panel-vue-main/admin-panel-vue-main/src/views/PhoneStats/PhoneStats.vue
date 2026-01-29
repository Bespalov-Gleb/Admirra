<template>
  <div class="space-y-6 overflow-x-hidden w-full">
    <!-- Заголовок -->
    <div class="py-5 px-6 sm:px-8 bg-white/60 backdrop-blur-xl rounded-[32px] border border-white/80 shadow-sm transition-all hover:shadow-md">
      <label class="text-[9px] font-black text-gray-400 uppercase tracking-widest ml-1 opacity-70">
        Статистика
      </label>
      <div class="flex items-center gap-3 mt-0.5">
        <div class="p-2 bg-blue-600 rounded-xl shadow-lg shadow-blue-200 hidden xs:block">
          <ChartBarIcon class="w-4 h-4 text-white" />
        </div>
        <div class="flex flex-col min-w-0 flex-1">
          <h1 class="text-xl sm:text-2xl font-black text-gray-900 tracking-tight truncate">
            Статистика телефонии
          </h1>
          <div class="flex items-center gap-1.5 mt-0.5">
            <div class="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse flex-shrink-0"></div>
            <p class="text-[9px] font-bold text-gray-400 uppercase tracking-wider truncate">
              Аналитика по проектам валидации лидов
            </p>
          </div>
        </div>
        <div class="flex items-center gap-3">
          <select
            v-model="selectedPeriod"
            class="px-4 py-2.5 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition text-sm bg-white"
          >
            <option value="7">7 дней</option>
            <option value="14">14 дней</option>
            <option value="30">30 дней</option>
            <option value="90">90 дней</option>
          </select>
        </div>
      </div>
    </div>

    <!-- KPI карточки -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
      <div
        v-for="stat in statsCards"
        :key="stat.label"
        class="bg-white rounded-[32px] p-6 border border-gray-100 shadow-sm hover:shadow-md transition-all"
      >
        <div class="flex items-center justify-between mb-4">
          <div class="w-12 h-12 rounded-xl flex items-center justify-center" :class="stat.bgColor">
            <component :is="stat.icon" class="w-6 h-6" :class="stat.iconColor" />
          </div>
          <span
            v-if="stat.trend"
            :class="[
              'text-xs font-semibold',
              stat.trend > 0 ? 'text-green-600' : 'text-red-600'
            ]"
          >
            {{ stat.trend > 0 ? '+' : '' }}{{ stat.trend }}%
          </span>
        </div>
        <p class="text-xs font-bold text-gray-500 uppercase tracking-wider mb-1">{{ stat.label }}</p>
        <p class="text-2xl font-black text-gray-900">{{ stat.value }}</p>
      </div>
    </div>

    <!-- График статистики -->
    <div class="bg-white rounded-[32px] border border-gray-100 shadow-sm p-8">
      <h2 class="text-lg font-bold text-gray-900 mb-6">Динамика заявок</h2>
      <div v-if="loading" class="h-64 flex items-center justify-center">
        <div class="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
      </div>
      <div v-else class="h-64 flex items-center justify-center text-gray-400">
        <p>График будет здесь (требуется интеграция с Chart.js)</p>
      </div>
    </div>

    <!-- Статистика по проектам -->
    <div class="bg-white rounded-[32px] border border-gray-100 shadow-sm overflow-hidden">
      <div class="p-6 border-b border-gray-200">
        <h2 class="text-lg font-bold text-gray-900">Статистика по проектам</h2>
      </div>
      <div v-if="loading" class="p-12 text-center">
        <div class="inline-block w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
      </div>
      <div v-else-if="projectStats.length === 0" class="p-12 text-center text-gray-500">
        <p>Нет данных</p>
      </div>
      <div v-else class="overflow-x-auto">
        <table class="w-full">
          <thead class="bg-gray-50 border-b border-gray-200">
            <tr>
              <th class="px-6 py-4 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Проект</th>
              <th class="px-6 py-4 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Всего заявок</th>
              <th class="px-6 py-4 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Принято</th>
              <th class="px-6 py-4 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Отклонено</th>
              <th class="px-6 py-4 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">% принятия</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200">
            <tr
              v-for="stat in projectStats"
              :key="stat.project_id"
              class="hover:bg-gray-50 transition-colors"
            >
              <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                {{ stat.project_name }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                {{ stat.total }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-green-600 font-semibold">
                {{ stat.accepted }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-red-600 font-semibold">
                {{ stat.rejected }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                {{ stat.acceptance_rate }}%
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ChartBarIcon, CheckCircleIcon, XCircleIcon, PhoneIcon } from '@heroicons/vue/24/outline'
import api from '@/api/axios'
import { useToaster } from '@/composables/useToaster'

const toaster = useToaster()
const loading = ref(false)
const selectedPeriod = ref('7')
const stats = ref({
  total: 0,
  accepted: 0,
  rejected: 0,
  rejection_rate: 0
})
const projectStats = ref([])

const statsCards = computed(() => [
  {
    label: 'Всего заявок',
    value: stats.value.total.toLocaleString('ru-RU'),
    icon: PhoneIcon,
    bgColor: 'bg-blue-100',
    iconColor: 'text-blue-600',
    trend: null
  },
  {
    label: 'Принято',
    value: stats.value.accepted.toLocaleString('ru-RU'),
    icon: CheckCircleIcon,
    bgColor: 'bg-green-100',
    iconColor: 'text-green-600',
    trend: null
  },
  {
    label: 'Отклонено',
    value: stats.value.rejected.toLocaleString('ru-RU'),
    icon: XCircleIcon,
    bgColor: 'bg-red-100',
    iconColor: 'text-red-600',
    trend: null
  },
  {
    label: 'Процент принятия',
    value: `${(100 - stats.value.rejection_rate).toFixed(1)}%`,
    icon: ChartBarIcon,
    bgColor: 'bg-purple-100',
    iconColor: 'text-purple-600',
    trend: null
  }
])

onMounted(() => {
  fetchStats()
})

watch(selectedPeriod, () => {
  fetchStats()
})

const fetchStats = async () => {
  try {
    loading.value = true
    // TODO: Заменить на реальный API endpoint когда будет готов
    // const response = await api.get('lead/stats', {
    //   params: { days: selectedPeriod.value }
    // })
    // stats.value = response.data
    
    // Временные данные для демонстрации
    stats.value = {
      total: 0,
      accepted: 0,
      rejected: 0,
      rejection_rate: 0
    }
    projectStats.value = []
  } catch (error) {
    console.error('Error fetching stats:', error)
    toaster.error('Не удалось загрузить статистику')
  } finally {
    loading.value = false
  }
}
</script>

