<template>
  <div class="space-y-4 sm:space-y-6">
    <!-- Заголовок с поиском и фильтрами -->
    <div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3 sm:gap-4">
      <!-- Заголовок -->
      <h1 class="text-xl sm:text-2xl md:text-3xl font-bold text-gray-900 flex-shrink-0">Проекты</h1>
      
      <!-- Поиск и фильтры -->
      <div class="flex flex-col sm:flex-row gap-2 sm:gap-3 flex-1 lg:flex-initial lg:justify-end">
        <!-- Поиск -->
        <div class="relative flex-1 sm:flex-initial sm:min-w-[200px] lg:min-w-[240px]">
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Найти проект"
            class="w-full px-3 sm:px-4 py-2 sm:py-2.5 pl-9 sm:pl-10 border border-gray-300 rounded-lg bg-white text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
          <MagnifyingGlassIcon class="absolute left-2.5 sm:left-3 top-1/2 -translate-y-1/2 w-4 h-4 sm:w-5 sm:h-5 text-gray-400" />
        </div>
        
        <!-- Фильтр по периоду -->
        <div class="relative flex-shrink-0">
          <select
            v-model="selectedPeriod"
            class="w-full sm:w-auto sm:min-w-[180px] px-3 sm:px-4 py-2 sm:py-2.5 border border-gray-300 rounded-lg bg-white text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 appearance-none cursor-pointer pr-8 sm:pr-10"
          >
            <option value="14">Последние 14 дней</option>
            <option value="7">Последние 7 дней</option>
            <option value="30">Последние 30 дней</option>
            <option value="90">Последние 90 дней</option>
            <option value="month">Текущий месяц</option>
            <option value="year">Текущий год</option>
          </select>
          <div class="absolute inset-y-0 right-0 flex items-center pr-2 sm:pr-3 pointer-events-none">
            <svg class="w-4 h-4 sm:w-5 sm:h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </div>
        
        <!-- Фильтр "Все" -->
        <div class="relative flex-shrink-0">
          <select
            v-model="selectedFilter"
            class="w-full sm:w-auto sm:min-w-[100px] px-3 sm:px-4 py-2 sm:py-2.5 border border-gray-300 rounded-lg bg-white text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 appearance-none cursor-pointer pr-8 sm:pr-10"
          >
            <option value="all">Все</option>
            <option value="active">Активные</option>
            <option value="paused">Приостановленные</option>
            <option value="completed">Завершенные</option>
          </select>
          <div class="absolute inset-y-0 right-0 flex items-center pr-2 sm:pr-3 pointer-events-none">
            <svg class="w-4 h-4 sm:w-5 sm:h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </div>
      </div>
    </div>

    <!-- Карточки проектов -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <ProjectCard
        v-for="project in filteredProjects"
        :key="project.id"
        :project="project"
      />
    </div>

    <!-- Пустое состояние -->
    <div v-if="filteredProjects.length === 0" class="text-center py-12">
      <p class="text-gray-500">Проекты не найдены</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { MagnifyingGlassIcon } from '@heroicons/vue/24/outline'
import ProjectCard from './components/ProjectCard.vue'

const searchQuery = ref('')
const selectedPeriod = ref('14')
const selectedFilter = ref('all')

const projects = ref([
  {
    id: 1,
    title: 'КСИ СТРОЙ',
    description: 'описание проекта',
    impressions: 120302,
    clicks: 12302,
    cpc: 12.3,
    expenses: 120000.3,
    leads: 125,
    cpa: 12.3,
    budgetRemaining: 12000.3,
    channels: ['Google Ads', 'Яндекс.Директ'],
    trend: 12.7
  },
  {
    id: 2,
    title: 'Laptops',
    description: 'описание проекта',
    impressions: 98000,
    clicks: 2100,
    cpc: 52.3,
    expenses: 109830,
    leads: 98,
    cpa: 1120,
    budgetRemaining: 390170,
    channels: ['Google Ads', 'Facebook Ads'],
    trend: -8.2
  },
  {
    id: 3,
    title: 'Phones',
    description: 'описание проекта',
    impressions: 156000,
    clicks: 4500,
    cpc: 38.9,
    expenses: 175050,
    leads: 234,
    cpa: 748,
    budgetRemaining: 224950,
    channels: ['Яндекс.Директ', 'ВКонтакте'],
    trend: 15.7
  },
  {
    id: 4,
    title: 'Проект 4',
    description: 'описание проекта',
    impressions: 87000,
    clicks: 1800,
    cpc: 48.2,
    expenses: 86760,
    leads: 87,
    cpa: 997,
    budgetRemaining: 413240,
    channels: ['Google Ads'],
    trend: 5.3
  },
  {
    id: 5,
    title: 'Проект 5',
    description: 'описание проекта',
    impressions: 112000,
    clicks: 2900,
    cpc: 42.1,
    expenses: 122090,
    leads: 134,
    cpa: 911,
    budgetRemaining: 377910,
    channels: ['Яндекс.Директ', 'Facebook Ads', 'ВКонтакте'],
    trend: -3.1
  }
])

const filteredProjects = computed(() => {
  let result = projects.value

  // Фильтр по поиску
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(project =>
      project.title.toLowerCase().includes(query)
    )
  }

  // Фильтр по статусу
  if (selectedFilter.value && selectedFilter.value !== 'all') {
    // Здесь можно добавить логику фильтрации по статусу
  }

  return result
})
</script>
