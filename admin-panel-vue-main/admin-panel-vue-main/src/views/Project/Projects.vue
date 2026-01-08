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
import { ref, computed, onMounted, watch } from 'vue'
import { MagnifyingGlassIcon } from '@heroicons/vue/24/outline'
import ProjectCard from './components/ProjectCard.vue'
import api from '../../api/axios'

const searchQuery = ref('')
const selectedPeriod = ref('14')
const selectedFilter = ref('all')
const loading = ref(true)
const projects = ref([])

const fetchProjects = async () => {
  loading.value = true
  try {
    // Calculate dates based on selectedPeriod
    const end = new Date()
    const start = new Date()
    start.setDate(end.getDate() - (parseInt(selectedPeriod.value) - 1))
    
    const formatDate = (date) => date.toISOString().split('T')[0]
    
    const response = await api.get('clients/stats', {
      params: {
        start_date: formatDate(start),
        end_date: formatDate(end)
      }
    })
    
    projects.value = response.data.map(client => ({
      id: client.id,
      title: client.name,
      description: client.description,
      impressions: client.summary?.impressions || 0,
      clicks: client.summary?.clicks || 0,
      cpc: client.summary?.cpc || 0,
      expenses: client.summary?.expenses || 0,
      leads: client.summary?.leads || 0,
      cpa: client.summary?.cpa || 0,
      budgetRemaining: 0, 
      channels: (client.integrations || []).map(i => {
        const platformMap = {
          'YANDEX_DIRECT': 'Яндекс.Директ',
          'VK_ADS': 'ВКонтакте',
          'GOOGLE_ADS': 'Google Ads',
          'FACEBOOK_ADS': 'Facebook Ads'
        }
        return platformMap[i.platform] || i.platform
      }),
      trend: client.summary?.trends?.expenses || 0
    }))
  } catch (error) {
    console.error('Error fetching projects:', error)
  } finally {
    loading.value = false
  }
}

// Re-fetch when period changes
import { watch } from 'vue'
watch(selectedPeriod, () => {
  fetchProjects()
})

onMounted(() => {
  fetchProjects()
})

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
