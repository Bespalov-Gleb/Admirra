<template>
  <div class="space-y-6">
    <!-- Заголовок с фильтрами -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
      <h1 class="text-2xl sm:text-3xl font-bold text-gray-900 uppercase tracking-tight">Статистика по всем проектам</h1>
      <div class="flex flex-wrap gap-2">
        <select v-model="filters.channel" class="px-4 py-2.5 border border-gray-300 rounded-xl bg-white text-sm font-bold text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 appearance-none cursor-pointer pr-10 shadow-sm hover:border-gray-400 transition-all">
          <option value="all">Все каналы</option>
          <option value="google" disabled>Google Ads</option>
          <option value="yandex">Яндекс.Директ</option>
          <option value="facebook" disabled>Facebook Ads</option>
          <option value="instagram" disabled>Instagram</option>
          <option value="vk">ВКонтакте</option>
          <option value="telegram" disabled>Telegram</option>
        </select>

        <select v-model="filters.period" @change="handlePeriodChange" class="px-4 py-2.5 border border-gray-300 rounded-xl bg-white text-sm font-bold text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 appearance-none cursor-pointer pr-10 shadow-sm hover:border-gray-400 transition-all">
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
            class="px-4 py-2.5 border border-gray-300 rounded-xl bg-white text-sm font-bold text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm hover:border-gray-400 transition-all"
          >
          <input 
            type="date" 
            v-model="filters.end_date"
            class="px-4 py-2.5 border border-gray-300 rounded-xl bg-white text-sm font-bold text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm hover:border-gray-400 transition-all"
          >
        </template>

        <select v-model="filters.client_id" class="px-4 py-2.5 border border-gray-300 rounded-xl bg-white text-sm font-bold text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 appearance-none cursor-pointer pr-10 shadow-sm hover:border-gray-400 transition-all">
          <option value="">Все проекты</option>
          <option v-for="client in clients" :key="client.id" :value="client.id">
            {{ client.name }}
          </option>
        </select>
      </div>
    </div>

    <!-- Error Alert -->
    <div v-if="error" class="p-4 bg-red-50 border border-red-100 text-red-600 rounded-2xl flex items-center gap-3 animate-shake">
      <ExclamationTriangleIcon class="w-5 h-5" />
      <span class="text-sm font-bold">{{ error }}</span>
      <button @click="fetchStats" class="ml-auto text-xs bg-red-100 px-3 py-1 rounded-lg hover:bg-red-200 transition-all font-black uppercase tracking-widest">Повторить</button>
    </div>

    <!-- Карточки KPI -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <template v-if="loading">
        <div v-for="i in 6" :key="i" class="bg-white p-6 rounded-[2rem] border border-gray-100 shadow-sm space-y-4">
          <div class="flex items-center justify-between">
            <Skeleton width="40%" height="12px" />
            <Skeleton width="32px" height="32px" rounded="full" />
          </div>
          <Skeleton width="60%" height="32px" />
          <Skeleton width="100%" height="10px" />
        </div>
      </template>
      <template v-else>
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
      </template>
    </div>

    <!-- Графики -->
    <div class="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div class="lg:col-span-3">
            <div v-if="loading" class="bg-white p-6 rounded-[2rem] border border-gray-100 h-[400px] flex flex-col justify-between">
               <div class="flex justify-between items-center mb-4">
                  <Skeleton width="30%" height="20px" />
                  <Skeleton width="100px" height="32px" rounded="xl" />
               </div>
               <Skeleton width="100%" height="300px" rounded="2xl" />
            </div>
            <DynamicsChart 
              v-else
              :labels="dynamics.labels"
              :expenses="dynamics.costs"
              :clicks="dynamics.clicks"
            />
        </div>
        <div class="lg:col-span-2">
            <div v-if="loading" class="bg-white p-6 rounded-[2rem] border border-gray-100 h-[400px] flex flex-col items-center justify-center space-y-6">
               <Skeleton width="60%" height="20px" />
               <Skeleton width="200px" height="200px" rounded="full" />
               <div class="w-full space-y-2">
                 <Skeleton width="100%" height="20px" />
                 <Skeleton width="100%" height="20px" />
               </div>
            </div>
            <TopProjectsChart v-else :items="topClients" />
        </div>
    </div>

    <!-- Таблица кампаний -->
    <CampaignTable :campaigns="campaigns" :loading="loading || loadingCampaigns" />

  </div>
</template>

<script setup>
import {
  ShoppingBagIcon,
  UserIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon
} from '@heroicons/vue/24/outline'
import Card from './components/Card.vue'
import DynamicsChart from './components/DynamicsChart.vue'
import TopProjectsChart from './components/TopProjectsChart.vue'
import CampaignTable from './components/CampaignTable.vue'
import Skeleton from '../../components/ui/Skeleton.vue'
import { useDashboardStats } from '../../composables/useDashboardStats'

const {
  summary,
  dynamics,
  topClients,
  campaigns,
  clients,
  loading,
  loadingCampaigns,
  error,
  filters,
  handlePeriodChange,
  fetchStats
} = useDashboardStats()
</script>

<style scoped>
.animate-shake {
  animation: shake 0.5s cubic-bezier(.36,.07,.19,.97) both;
}

@keyframes shake {
  10%, 90% { transform: translate3d(-1px, 0, 0); }
  20%, 80% { transform: translate3d(2px, 0, 0); }
  30%, 50%, 70% { transform: translate3d(-4px, 0, 0); }
  40%, 60% { transform: translate3d(4px, 0, 0); }
}
</style>

