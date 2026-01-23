<template>
  <div class="bg-white rounded-[40px] p-10 sm:p-6 md:p-8 hover:shadow-sm transition-shadow cursor-pointer">
    <!-- Заголовок карточки -->
    <div class="flex items-center gap-2 sm:gap-3 mb-4 sm:mb-6 md:mb-8">
      <div class="w-10 h-10 sm:w-12 sm:h-12 rounded-full bg-gray-200 flex items-center justify-center flex-shrink-0">
        <UserIcon class="w-5 h-5 sm:w-6 sm:h-7 text-gray-600" />
      </div>
      <div>
        <p class="text-sm sm:text-base font-bold text-gray-900">Проект:</p>
        <p class="text-xs sm:text-sm text-gray-500">{{ project.description || 'описание проекта' }}</p>
      </div>
    </div>

    <!-- KPI метрики -->
    <div class="grid grid-cols-2 sm:grid-cols-3 gap-4 sm:gap-6 mb-6 sm:mb-8">
      <div>
        <p class="text-sm sm:text-base text-gray-500 mb-1 sm:mb-2">Показы</p>
        <p class="text-2xl sm:text-3xl font-bold text-gray-900 mb-1 sm:mb-2">{{ formatNumber(project.impressions) }}</p>
        <div class="flex items-center gap-1.5">
          <ArrowTrendingUpIcon
            :class="[
              'w-3 h-3 sm:w-4 sm:h-4',
              project.trend > 0 ? 'text-green-600' : 'text-red-600'
            ]"
          />
          <span
            :class="[
              'text-sm sm:text-base',
              project.trend > 0 ? 'text-green-600' : 'text-red-600'
            ]"
          >
            {{ project.trend > 0 ? '+' : '' }}{{ project.trend }}%
          </span>
        </div>
      </div>
      <div>
        <p class="text-sm sm:text-base text-gray-500 mb-1 sm:mb-2">Клики</p>
        <p class="text-2xl sm:text-3xl font-bold text-gray-900 mb-1 sm:mb-2">{{ formatNumber(project.clicks) }}</p>
        <div class="flex items-center gap-1.5">
          <ArrowTrendingUpIcon
            :class="[
              'w-3 h-3 sm:w-4 sm:h-4',
              project.trend > 0 ? 'text-green-600' : 'text-red-600'
            ]"
          />
          <span
            :class="[
              'text-sm sm:text-base',
              project.trend > 0 ? 'text-green-600' : 'text-red-600'
            ]"
          >
            {{ project.trend > 0 ? '+' : '' }}{{ project.trend }}%
          </span>
        </div>
      </div>
      <div>
        <p class="text-sm sm:text-base text-gray-500 mb-1 sm:mb-2">CPC</p>
        <p class="text-2xl sm:text-3xl font-bold text-gray-900 mb-1 sm:mb-2">{{ formatExpenses(project.cpc) }}</p>
        <div class="flex items-center gap-1.5">
          <ArrowTrendingUpIcon
            :class="[
              'w-3 h-3 sm:w-4 sm:h-4',
              project.trend > 0 ? 'text-green-600' : 'text-red-600'
            ]"
          />
          <span
            :class="[
              'text-sm sm:text-base',
              project.trend > 0 ? 'text-green-600' : 'text-red-600'
            ]"
          >
            {{ project.trend > 0 ? '+' : '' }}{{ project.trend }}%
          </span>
        </div>
      </div>
      <div>
        <p class="text-sm sm:text-base text-gray-500 mb-1 sm:mb-2">Расходы</p>
        <p class="text-2xl sm:text-3xl font-bold text-gray-900 mb-1 sm:mb-2">{{ formatExpenses(project.expenses) }}</p>
        <div class="flex items-center gap-1.5">
          <ArrowTrendingUpIcon
            :class="[
              'w-3 h-3 sm:w-4 sm:h-4',
              project.trend > 0 ? 'text-green-600' : 'text-red-600'
            ]"
          />
          <span
            :class="[
              'text-sm sm:text-base',
              project.trend > 0 ? 'text-green-600' : 'text-red-600'
            ]"
          >
            {{ project.trend > 0 ? '+' : '' }}{{ project.trend }}%
          </span>
        </div>
      </div>
      <div>
        <p class="text-sm sm:text-base text-gray-500 mb-1 sm:mb-2">Лидов</p>
        <p class="text-2xl sm:text-3xl font-bold text-gray-900 mb-1 sm:mb-2">{{ formatNumber(project.leads) }}</p>
        <div class="flex items-center gap-1.5">
          <ArrowTrendingUpIcon
            :class="[
              'w-3 h-3 sm:w-4 sm:h-4',
              project.trend > 0 ? 'text-green-600' : 'text-red-600'
            ]"
          />
          <span
            :class="[
              'text-sm sm:text-base',
              project.trend > 0 ? 'text-green-600' : 'text-red-600'
            ]"
          >
            {{ project.trend > 0 ? '+' : '' }}{{ project.trend }}%
          </span>
        </div>
      </div>
      <div>
        <p class="text-sm sm:text-base text-gray-500 mb-1 sm:mb-2">CPA</p>
        <p class="text-2xl sm:text-3xl font-bold text-gray-900 mb-1 sm:mb-2">{{ formatExpenses(project.cpa) }}</p>
        <div class="flex items-center gap-1.5">
          <ArrowTrendingUpIcon
            :class="[
              'w-3 h-3 sm:w-4 sm:h-4',
              project.trend > 0 ? 'text-green-600' : 'text-red-600'
            ]"
          />
          <span
            :class="[
              'text-sm sm:text-base',
              project.trend > 0 ? 'text-green-600' : 'text-red-600'
            ]"
          >
            {{ project.trend > 0 ? '+' : '' }}{{ project.trend }}%
          </span>
        </div>
      </div>
    </div>

    <!-- Бюджет и каналы -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-0 pt-4 sm:pt-6 border-t border-gray-200">
      <div class="flex items-center gap-2 flex-wrap">
        <span class="text-xs sm:text-sm text-gray-500">остаток бюджета:</span>
        <span class="text-sm sm:text-base font-medium text-gray-900 bg-gray-100 px-3 sm:px-4 py-1.5 sm:py-2 rounded-lg">
          {{ formatExpenses(project.budgetRemaining) }}
        </span>
      </div>
      <div class="flex items-center gap-2">
        <span class="text-xs sm:text-sm text-gray-500">каналы:</span>
        <div class="flex items-center gap-1.5">
          <div
            v-for="(channel, index) in project.channels"
            :key="index"
            class="w-6 h-6 sm:w-7 sm:h-7 rounded-full flex items-center justify-center text-xs sm:text-sm font-bold"
            :class="getChannelClass(channel)"
          >
            <span :class="getChannelTextClass(channel)">{{ getChannelIcon(channel) }}</span>
          </div>
        </div>
        <ChevronRightIcon class="w-5 h-5 sm:w-6 sm:h-6 text-gray-700 ml-1 sm:ml-2" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { UserIcon, ArrowTrendingUpIcon, ChevronRightIcon } from '@heroicons/vue/24/outline'

defineProps({
  project: {
    type: Object,
    required: true
  }
})

const formatNumber = (num) => {
  return new Intl.NumberFormat('ru-RU').format(num)
}

const formatExpenses = (num) => {
  return new Intl.NumberFormat('ru-RU', { 
    style: 'currency', 
    currency: 'RUB', 
    minimumFractionDigits: 1,
    maximumFractionDigits: 1
  }).format(num)
}

const getChannelClass = (channel) => {
  const classes = {
    'Google Ads': 'bg-yellow-400',
    'Яндекс.Директ': 'bg-blue-600',
    'Facebook Ads': 'bg-blue-500',
    'ВКонтакте': 'bg-blue-400'
  }
  return classes[channel] || 'bg-gray-300'
}

const getChannelTextClass = (channel) => {
  const classes = {
    'Google Ads': 'text-blue-900',
    'Яндекс.Директ': 'text-blue-200',
    'Facebook Ads': 'text-white',
    'ВКонтакте': 'text-white'
  }
  return classes[channel] || 'text-gray-700'
}

const getChannelIcon = (channel) => {
  const icons = {
    'Google Ads': 'G',
    'Яндекс.Директ': 'Я',
    'Facebook Ads': 'F',
    'ВКонтакте': 'VK'
  }
  return icons[channel] || '?'
}
</script>
