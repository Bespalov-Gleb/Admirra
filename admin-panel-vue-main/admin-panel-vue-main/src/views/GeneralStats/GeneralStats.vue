<template>
  <div class="space-y-6">
    <!-- Заголовок с фильтрами -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
      <h1 class="text-2xl sm:text-3xl font-bold text-gray-900">Статистика по всем проектам</h1>
      <div class="flex flex-wrap gap-2">
        <select v-model="filters.channel" class="px-4 py-2.5 border border-gray-300 rounded-lg bg-white text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 appearance-none cursor-pointer pr-10">
          <option value="all">Все каналы</option>
          <option value="google" disabled>Google Ads</option>
          <option value="yandex">Яндекс.Директ</option>
          <option value="facebook" disabled>Facebook Ads</option>
          <option value="instagram" disabled>Instagram</option>
          <option value="vk">ВКонтакте</option>
          <option value="telegram" disabled>Telegram</option>
        </select>

        <select v-model="filters.period" @change="handlePeriodChange" class="px-4 py-2.5 border border-gray-300 rounded-lg bg-white text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 appearance-none cursor-pointer pr-10">
          <option value="7">Последние 7 дней</option>
          <option value="14">Последние 14 дней</option>
          <option value="30">Последние 30 дней</option>
          <option value="90">Последние 90 дней</option>
          <option value="custom">Произвольно</option>
        </select>
        
        <!-- Custom Date Range -->
        <template v-if="filters.period === 'custom'">
          <input 
            type="date" 
            v-model="filters.start_date"
            class="px-4 py-2.5 border border-gray-300 rounded-lg bg-white text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm"
          >
          <input 
            type="date" 
            v-model="filters.end_date"
            class="px-4 py-2.5 border border-gray-300 rounded-lg bg-white text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm"
          >
        </template>

        <select v-model="filters.client_id" class="px-4 py-2.5 border border-gray-300 rounded-lg bg-white text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 appearance-none cursor-pointer pr-10">
          <option value="">Все проекты</option>
          <option v-for="client in clients" :key="client.id" :value="client.id">
            {{ client.name }}
          </option>
        </select>
      </div>
    </div>

    <!-- Карточки KPI -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <Card
        title="Расходы"
        subtitle="за период"
        :value="summary.expenses.toLocaleString() + ' Р'"
        :trend="0"
        change-text="данные из API"
        :icon="ShoppingBagIcon"
        :is-dark="true"
      />
      <Card
        title="Переходы"
        subtitle="по всем каналам"
        :value="summary.clicks.toLocaleString()"
        :trend="0"
        change-text="данные из API"
        :icon="UserIcon"
        :is-dark="false"
      />
      <Card
        title="Лиды"
        subtitle="все виды CPA"
        :value="summary.leads.toLocaleString()"
        :trend="0"
        change-text="данные из API"
        :icon="ArrowPathIcon"
        :is-dark="false"
      />
      <Card
        title="Показы"
        subtitle="охват кампаний"
        :value="summary.impressions.toLocaleString()"
        :trend="0"
        change-text="данные из API"
        :icon="UserIcon"
        :is-dark="false"
      />
      <Card
        title="CPC"
        subtitle="цена клика"
        :value="summary.cpc.toLocaleString() + ' Р'"
        :trend="0"
        change-text="среднее"
        :icon="ShoppingBagIcon"
        :is-dark="false"
      />
      <Card
        title="CPA"
        subtitle="цена лида"
        :value="summary.cpa.toLocaleString() + ' Р'"
        :trend="0"
        change-text="целевое действие"
        :icon="ArrowPathIcon"
        :is-dark="false"
      />
    </div>
    <!-- Графики -->
    <div class="grid grid-cols-1 md:grid-cols-5 gap-4">
        <div class="md:col-span-3">
            <DynamicsChart 
              :labels="dynamics.labels"
              :expenses="dynamics.costs"
              :clicks="dynamics.clicks"
            />
        </div>
        <div class="md:col-span-2 md:col-start-4">
            <TopProjectsChart :items="topClients" />
        </div>
    </div>

    <!-- Таблица кампаний -->
    <CampaignTable :campaigns="campaigns" :loading="loadingCampaigns" />

  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import {
  ShoppingBagIcon,
  UserIcon,
  ArrowPathIcon
} from '@heroicons/vue/24/outline'
import Card from './components/Card.vue'
import DynamicsChart from './components/DynamicsChart.vue'
import TopProjectsChart from './components/TopProjectsChart.vue'
import CampaignTable from './components/CampaignTable.vue'
import api from '../../api/axios'

// Состояние данных
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

const topClients = ref([])
const campaigns = ref([])
const clients = ref([])
const loading = ref(true)
const loadingCampaigns = ref(false)

// Фильтры
const filters = reactive({
  channel: 'all',
  period: '14',
  client_id: '',
  start_date: '',
  end_date: new Date().toISOString().split('T')[0]
})

// Установка начальной даты для "14 дней"
const setInitialDates = () => {
  const end = new Date()
  const start = new Date()
  start.setDate(end.getDate() - 14)
  filters.start_date = start.toISOString().split('T')[0]
  filters.end_date = end.toISOString().split('T')[0]
}

const handlePeriodChange = () => {
  if (filters.period === 'custom') return
  
  const end = new Date()
  const start = new Date()
  start.setDate(end.getDate() - parseInt(filters.period))
  filters.start_date = start.toISOString().split('T')[0]
  filters.end_date = end.toISOString().split('T')[0]
}

// Загрузка списка клиентов
const fetchClients = async () => {
  try {
    const response = await api.get('clients/')
    clients.value = response.data
  } catch (error) {
    console.error('Error fetching clients:', error)
  }
}

// Загрузка статистики
const fetchStats = async () => {
  loading.value = true
  loadingCampaigns.value = true
  try {
    const params = {
      start_date: filters.start_date,
      end_date: filters.end_date,
      platform: filters.channel
    }
    if (filters.client_id) params.client_id = filters.client_id

    // Параллельные запросы
    const [summaryRes, dynamicsRes, topRes, campaignsRes] = await Promise.all([
      api.get('dashboard/summary', { params }),
      api.get('dashboard/dynamics', { params }),
      api.get('dashboard/top-clients'),
      api.get('dashboard/campaigns', { params })
    ])

    summary.value = summaryRes.data
    dynamics.value = dynamicsRes.data
    topClients.value = topRes.data
    campaigns.value = campaignsRes.data
  } catch (error) {
    console.error('Error fetching stats:', error)
  } finally {
    loading.value = false
    loadingCampaigns.value = false
  }
}

// Следим за изменением фильтров
watch(() => [filters.start_date, filters.end_date, filters.client_id, filters.channel], () => {
  // Меняем селект на "custom", если даты меняются вручную
  const duration = (new Date(filters.end_date) - new Date(filters.start_date)) / (1000 * 60 * 60 * 24)
  const knownPeriods = ['7', '14', '30', '90']
  if (!knownPeriods.includes(duration.toString())) {
    // filters.period = 'custom' // Это может вызвать лишний вызов, пока отложим
  }
  fetchStats()
})

onMounted(() => {
  setInitialDates()
  fetchClients()
  fetchStats()
})
</script>

