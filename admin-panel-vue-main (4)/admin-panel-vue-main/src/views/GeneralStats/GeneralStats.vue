<template>
  <div class="space-y-6">
    <!-- Заголовок с фильтрами -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
      <h1 class="text-2xl sm:text-3xl font-bold text-gray-900">Статистика по всем проектам</h1>
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
        <select class="px-4 py-2.5 border border-gray-300 rounded-lg bg-white text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 appearance-none cursor-pointer pr-10">
          <option value="">Выбрать проект</option>
          <option value="project1">КСИ СТРОЙ</option>
          <option value="project2">Laptops</option>
          <option value="project3">Phones</option>
          <option value="project4">Проект 4</option>
          <option value="project5">Проект 5</option>
        </select>
      </div>
    </div>

    <!-- Карточки KPI -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <Card
        title="Расходы"
        subtitle="за период"
        value="90,328.55 Р"
        :trend="15.6"
        change-text="+1.4k this week"
        :icon="ShoppingBagIcon"
        :is-dark="true"
      />
      <Card
        title="Переходы"
        subtitle="по всем каналам"
        value="12,302"
        :trend="12.7"
        change-text="+1.2k this week"
        :icon="UserIcon"
        :is-dark="false"
      />
      <Card
        title="Лиды"
        subtitle="все виды CPA"
        value="963"
        :trend="-12.7"
        change-text="-213"
        :icon="ArrowPathIcon"
        :is-dark="false"
      />
    </div>
    <!-- Графики -->
    <div class="grid grid-cols-1 md:grid-cols-5 gap-4">
        <div class="md:col-span-3">
            <DynamicsChart />
        </div>
        <div class="md:col-span-2 md:col-start-4">
            <TopProjectsChart />
        </div>
    </div>

  </div>
</template>

<script setup>
import {
  ShoppingBagIcon,
  UserIcon,
  ArrowPathIcon
} from '@heroicons/vue/24/outline'
import Card from './components/Card.vue'
import DynamicsChart from './components/DynamicsChart.vue'
import TopProjectsChart from './components/TopProjectsChart.vue'
</script>

