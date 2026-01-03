<template>
  <div class="space-y-6">
    <!-- Заголовок с фильтрами -->
    <div class="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-6">
      <div>
        <h1 class="text-2xl sm:text-3xl font-bold text-gray-900 mb-1">Отчет по проекту:</h1>
        <p class="text-sm text-gray-500">описание проекта</p>
      </div>
      <div class="flex flex-wrap gap-2">
        <select class="px-4 py-2.5 border border-gray-300 rounded-lg bg-white text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 appearance-none cursor-pointer pr-10">
          <option value="all">Все каналы</option>
          <option value="google">Google Ads</option>
          <option value="yandex">Яндекс.Директ</option>
          <option value="facebook">Facebook Ads</option>
          <option value="instagram">Instagram</option>
          <option value="vk">ВКонтакте</option>
          <option value="telegram">Telegram</option>
        </select>
        <select class="px-4 py-2.5 border border-gray-300 rounded-lg bg-white text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 appearance-none cursor-pointer pr-10">
          <option value="14">Последние 14 дней</option>
          <option value="7">Последние 7 дней</option>
          <option value="30">Последние 30 дней</option>
          <option value="90">Последние 90 дней</option>
          <option value="month">Текущий месяц</option>
          <option value="year">Текущий год</option>
        </select>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-4">
        <div class="md:col-span-2 xl:col-span-4">
          <StatisticsChart />
        </div>
        <div class="md:col-span-2 xl:col-span-1 xl:col-start-5 flex flex-col gap-4">
            <!-- Подключенные каналы -->
            <ConnectedChannels />
            
            <!-- Отправка отчетов -->
            <ReportDelivery />
        </div>
    </div>
    
    <!-- Карточки KPI -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <Card
        title="Расходы"
        subtitle="за период"
        value="90,328.55 ₽"
        :trend="15.6"
        change-text="+1.4k this week"
        :icon="ShoppingBagIcon"
        :is-dark="true"
      />
      <Card
        title="Показы"
        subtitle="по всем каналам"
        value="120,302"
        :trend="12.7"
        change-text="+1.2k this week"
        :icon="EyeIcon"
        :is-dark="false"
      />
      <Card
        title="Клики"
        subtitle="все переходы"
        value="963"
        :trend="-12.7"
        change-text="-213"
        :icon="CursorArrowRaysIcon"
        :is-dark="false"
      />
      <Card
        title="CPC"
        subtitle="стоимость клика"
        value="9,63 ₽"
        :trend="12.7"
        change-text="+1.2k this week"
        :icon="CurrencyDollarIcon"
        :is-dark="false"
      />
      <Card
        title="Лиды"
        subtitle="по всем каналам"
        value="12,302"
        :trend="12.7"
        change-text="+1.2k this week"
        :icon="UserIcon"
        :is-dark="false"
      />
      <Card
        title="CPA"
        subtitle="стоимость лида"
        value="963 ₽"
        :trend="-12.7"
        change-text="-213"
        :icon="ArrowPathIcon"
        :is-dark="false"
      />
    </div>

    <!-- Статистика по ключевым целям -->
    <KeyGoalsStats />

    <!-- Комментарии к отчету -->
    <ReportComments />

  </div>
</template>

<script setup>
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
</script>

