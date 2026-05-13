<template>
  <div class="space-y-6">
    <!-- Сообщение при синхронизации -->
    <div v-if="dataHiddenBySync" class="flex items-center justify-center min-h-[50vh] px-4">
      <div class="max-w-md w-full text-center py-12 px-8 bg-white/80 backdrop-blur-sm rounded-3xl border border-gray-100 shadow-lg">
        <div class="w-14 h-14 mx-auto mb-4 rounded-2xl bg-blue-50 flex items-center justify-center">
          <svg class="w-7 h-7 text-blue-500 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        </div>
        <h3 class="text-base font-bold text-gray-800 mb-2">Идёт синхронизация</h3>
        <p class="text-sm text-gray-500">Данные обновляются. Статистика появится через несколько минут.</p>
      </div>
    </div>

    <!-- Загрузка -->
    <!-- Skeleton Loaders -->
    <div v-else-if="loading" class="space-y-6">
      <div class="flex justify-between items-center">
        <Skeleton width="13.8889rem" height="2.7778rem" />
        <div class="flex gap-2">
          <Skeleton width="10.4167rem" height="2.7778rem" />
          <Skeleton width="10.4167rem" height="2.7778rem" />
        </div>
      </div>
      <div class="grid grid-cols-5 gap-4">
        <Skeleton customClass="col-span-4" height="20.8333rem" />
        <Skeleton customClass="col-span-1" height="20.8333rem" />
      </div>
      <div class="grid grid-cols-3 gap-6">
        <Skeleton v-for="i in 6" :key="i" height="10.4167rem" />
      </div>
    </div>
    
    <template v-else>
    <!-- Заголовок с фильтрами -->
    <div class="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-6">
      <div>
        <h1 class="text-2xl sm:text-3xl font-bold text-gray-900 mb-1">Отчет по проекту:</h1>
        <p class="text-sm text-gray-500">описание проекта</p>
      </div>
      <div class="flex flex-wrap gap-2">
        <select 
          v-model="filters.channel"
          class="px-4 py-2.5 border border-gray-300 rounded-lg bg-white text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 appearance-none cursor-pointer pr-10"
        >
          <option value="all">Все каналы</option>
          <option value="yandex">Яндекс.Директ</option>
          <option value="vk">ВКонтакте</option>
        </select>
        <select 
          v-model="filters.period"
          @change="handlePeriodChange"
          class="px-4 py-2.5 border border-gray-300 rounded-lg bg-white text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 appearance-none cursor-pointer pr-10"
        >
          <option value="14">Последние 14 дней</option>
          <option value="7">Последние 7 дней</option>
          <option value="30">Последние 30 дней</option>
          <option value="90">Последние 90 дней</option>
        </select>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-4">
        <div class="md:col-span-2 xl:col-span-4">
          <StatisticsChart :labels="dynamics.labels" :costs="dynamics.costs" :clicks="dynamics.clicks" />
        </div>
        <div class="md:col-span-2 xl:col-span-1 xl:col-start-5 flex flex-col gap-4">
            <!-- Подключенные каналы -->
            <ConnectedChannels :integrations="integrations" />
            
            <!-- Отправка отчетов -->
            <ReportDelivery />
        </div>
    </div>
    
    <!-- Карточки KPI -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <Card
        title="Расходы"
        subtitle="за период"
        :value="summary.expenses.toLocaleString() + ' ₽'"
        :trend="0"
        change-text="данные из API"
        :icon="ShoppingBagIcon"
        :is-dark="true"
      />
      <Card
        title="Показы"
        subtitle="по всем каналам"
        :value="summary.impressions.toLocaleString()"
        :trend="0"
        change-text="данные из API"
        :icon="EyeIcon"
        :is-dark="false"
      />
      <Card
        title="Клики"
        subtitle="все переходы"
        :value="summary.clicks.toLocaleString()"
        :trend="0"
        change-text="данные из API"
        :icon="CursorArrowRaysIcon"
        :is-dark="false"
      />
      <Card
        title="CPC"
        subtitle="стоимость клика"
        :value="summary.cpc.toLocaleString() + ' ₽'"
        :trend="0"
        change-text="среднее"
        :icon="CurrencyDollarIcon"
        :is-dark="false"
      />
      <Card
        title="Лиды"
        subtitle="по всем каналам"
        :value="summary.leads.toLocaleString()"
        :trend="0"
        change-text="данные из API"
        :icon="UserIcon"
        :is-dark="false"
      />
      <Card
        title="CPA"
        subtitle="стоимость лида"
        :value="summary.cpa.toLocaleString() + ' ₽'"
        :trend="0"
        change-text="среднее"
        :icon="ArrowPathIcon"
        :is-dark="false"
      />
    </div>

    <!-- Статистика по ключевым целям -->
    <KeyGoalsStats :goals="goals" />

    <!-- Комментарии к отчету -->
    <ReportComments />

  </template>
</div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import api from '../../api/axios'
import {
  ShoppingBagIcon,
  EyeIcon,
  CursorArrowRaysIcon,
  CurrencyDollarIcon,
  UserIcon,
  ArrowPathIcon
} from '@heroicons/vue/24/outline'
import Card from '../GeneralStats/components/Card.vue'
import StatisticsChart from './components/StatisticsChart.vue'
import ConnectedChannels from './components/ConnectedChannels.vue'
import ReportDelivery from './components/ReportDelivery.vue'
import ReportComments from './components/ReportComments.vue'
import KeyGoalsStats from './components/KeyGoalsStats.vue'
import Skeleton from '../../components/ui/Skeleton.vue'
import { useProjects } from '../../composables/useProjects'
import { useSyncStatus } from '../../composables/useSyncStatus'

const { isSyncingForProject } = useSyncStatus()

const summary = ref({
  expenses: 0,
  impressions: 0,
  clicks: 0,
  leads: 0,
  cpc: 0,
  cpa: 0
})

const dynamics = ref({
  labels: [],
  costs: [],
  clicks: []
})

const goals = ref([])
const integrations = ref([])
const loading = ref(true)

// CRITICAL: Get current project from global state
const { currentProjectId } = useProjects()

const filters = reactive({
  channel: 'all',
  period: '14',
  client_id: null,  // NEW: Add client_id filter
  start_date: '',
  end_date: new Date().toISOString().split('T')[0]
})

const dataHiddenBySync = computed(() => isSyncingForProject(filters.client_id || null))

// CRITICAL: Sync with global project selection
watch(currentProjectId, (newId) => {
  if (filters.client_id !== newId) {
    filters.client_id = newId
  }
}, { immediate: true })

const setInitialDates = () => {
  const end = new Date()
  const start = new Date()
  start.setDate(end.getDate() - 14)
  filters.start_date = start.toISOString().split('T')[0]
  filters.end_date = end.toISOString().split('T')[0]
}

const handlePeriodChange = () => {
  const end = new Date()
  const start = new Date()
  const periodDays = parseInt(filters.period)
  start.setDate(end.getDate() - periodDays)
  filters.start_date = start.toISOString().split('T')[0]
  filters.end_date = end.toISOString().split('T')[0]
  // fetchStats вызовется через watch при смене filters; бэкенд сам проверит наличие данных
  // и запустит синк только если данных за период нет
}

const fetchStats = async () => {
  loading.value = true
  try {
    const params = {
      start_date: filters.start_date,
      end_date: filters.end_date,
      platform: filters.channel,
      // CRITICAL: Add client_id to filter by project
      client_id: filters.client_id || undefined
    }

    const [summaryRes, dynamicsRes, goalsRes, integrationsRes] = await Promise.all([
      api.get('dashboard/summary', { params }),
      api.get('dashboard/dynamics', { params }),
      api.get('dashboard/goals', { params }),
      api.get('dashboard/integrations')
    ])

    summary.value = summaryRes.data
    dynamics.value = dynamicsRes.data
    goals.value = goalsRes.data
    integrations.value = integrationsRes.data
  } catch (error) {
    console.error('Error fetching GeneralStats2 data:', error)
  } finally {
    loading.value = false
  }
}

// CRITICAL: Watch for changes in filters including client_id
watch(() => [filters.start_date, filters.end_date, filters.channel, filters.client_id], fetchStats)

onMounted(() => {
  setInitialDates()
  fetchStats()
})
</script>

