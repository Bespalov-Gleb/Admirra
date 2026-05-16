<template>
  <div class="space-y-4 sm:space-y-6">
    <!-- Заголовок с фильтрами и переключателем вида -->
    <div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3 sm:gap-4">
      <!-- Заголовок -->
      <h1 class="text-xl sm:text-2xl md:text-3xl font-bold text-gray-900 flex-shrink-0">Проекты</h1>
      
      <!-- Фильтры и переключатель вида -->
      <div class="flex flex-col sm:flex-row gap-2 sm:gap-3 flex-1 lg:flex-initial lg:justify-end">
        <!-- Фильтр по периоду -->
        <div class="relative flex-shrink-0">
          <select
            v-model="selectedPeriod"
            class="w-full sm:w-auto sm:min-w-[12.5rem] px-3 sm:px-4 py-2 sm:py-2.5 border border-gray-300 rounded-lg bg-white text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 appearance-none cursor-pointer pr-8 sm:pr-10"
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
            class="w-full sm:w-auto sm:min-w-[6.9444rem] px-3 sm:px-4 py-2 sm:py-2.5 border border-gray-300 rounded-lg bg-white text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 appearance-none cursor-pointer pr-8 sm:pr-10"
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

        <!-- Переключатель вида -->
        <div class="flex items-center gap-1 bg-gray-100 rounded-lg p-1">
          <button 
            @click="viewMode = 'cards'"
            class="p-2 rounded transition-all"
            :class="viewMode === 'cards' ? 'bg-white shadow-sm' : 'hover:bg-gray-50'"
            title="Карточки"
          >
            <ViewColumnsIcon class="w-5 h-5" :class="viewMode === 'cards' ? 'text-blue-600' : 'text-gray-500'" />
          </button>
          <button 
            @click="viewMode = 'table'"
            class="p-2 rounded transition-all"
            :class="viewMode === 'table' ? 'bg-white shadow-sm' : 'hover:bg-gray-50'"
            title="Таблица"
          >
            <Bars3Icon class="w-5 h-5" :class="viewMode === 'table' ? 'text-blue-600' : 'text-gray-500'" />
          </button>
        </div>
      </div>
    </div>

    <!-- Карточки проектов -->
    <div v-if="viewMode === 'cards'" class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <ProjectCard
        v-for="project in filteredProjects"
        :key="project.id"
        :project="project"
      />
    </div>

    <!-- Таблица проектов -->
    <ProjectsTable 
      v-else
      :projects="enrichedProjects"
      :loading="loading"
      :search-query="searchQuery"
      @add-project="handleAddProject"
      @view-project="handleViewProject"
      @edit-project="handleEditProject"
      @delete-project="handleDeleteProject"
    />

    <!-- Пустое состояние для карточек -->
    <div v-if="viewMode === 'cards' && filteredProjects.length === 0" class="text-center py-12">
      <p class="text-gray-500">Проекты не найдены</p>
    </div>

    <ConfirmModal
      v-model:is-open="deleteConfirmOpen"
      title="Удалить проект?"
      :message="deleteConfirmMessage"
      @confirm="confirmDeleteProject"
    />

    <EditProjectModal
      v-if="editingProject"
      :project="editingProject"
      @close="editingProject = null"
      @saved="handleEditSaved"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { MagnifyingGlassIcon, ViewColumnsIcon, Bars3Icon } from '@heroicons/vue/24/outline'
import ProjectCard from './components/ProjectCard.vue'
import ProjectsTable from './components/ProjectsTable.vue'
import ConfirmModal from '../../components/ConfirmModal.vue'
import EditProjectModal from '../../components/EditProjectModal.vue'
import api from '../../api/axios'
import { useRouter } from 'vue-router'
import { useToaster } from '../../composables/useToaster'

const router = useRouter()
const toaster = useToaster()

const searchQuery = ref('')
const selectedPeriod = ref('14')
const selectedFilter = ref('all')
const loading = ref(true)
const projects = ref([])
const viewMode = ref('table') // 'cards' or 'table'
const deleteTarget = ref(null)
const editingProject = ref(null)

const deleteConfirmOpen = computed({
  get: () => Boolean(deleteTarget.value),
  set: (value) => {
    if (!value) deleteTarget.value = null
  }
})

const deleteConfirmMessage = computed(() => {
  const name = deleteTarget.value?.title || 'проект'
  return `Проект «${name}» и связанные данные будут удалены безвозвратно.`
})

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
      display_id: client.display_id,
      title: client.name,
      description: client.description,
      avatar_url: client.avatar_url,
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
      project.title.toLowerCase().includes(query) ||
      String(project.display_id || '').includes(query) ||
      String(project.id || '').toLowerCase().includes(query)
    )
  }

  // Фильтр по статусу
  if (selectedFilter.value && selectedFilter.value !== 'all') {
    // Здесь можно добавить логику фильтрации по статусу
  }

  return result
})

// Enriched projects with additional fields for table view
const enrichedProjects = computed(() => {
  return filteredProjects.value.map(project => ({
    ...project,
    tag: 'A',
    status: 'active',
    globalLimit: 50,
    limit: 10,
    sitesCount: 7,
    dealsReceived: 0,
    dealsToday: 0,
    providers: [],
    created_at: new Date().toISOString()
  }))
})

// Event handlers for table actions
const handleAddProject = () => {
  router.push('/integrations')
}

const handleViewProject = (projectId) => {
  router.push(`/projects/${projectId}`)
}

const handleEditProject = (projectId) => {
  const project = projects.value.find(p => p.id === projectId)
  if (project) {
    editingProject.value = { ...project, name: project.title }
  }
}

const handleEditSaved = (updatedProject) => {
  const idx = projects.value.findIndex(p => p.id === updatedProject.id)
  if (idx !== -1) {
    projects.value[idx] = {
      ...projects.value[idx],
      title: updatedProject.name,
      description: updatedProject.description,
      avatar_url: updatedProject.avatar_url,
    }
  }
  toaster.success('Проект обновлён')
}

const handleDeleteProject = async (projectId) => {
  deleteTarget.value = projects.value.find((project) => project.id === projectId) || { id: projectId, title: 'проект' }
}

const confirmDeleteProject = async () => {
  const project = deleteTarget.value
  if (!project?.id) return
  try {
    await api.delete(`clients/${project.id}`)
    projects.value = projects.value.filter(p => p.id !== project.id)
    toaster.success('Проект удален')
  } catch (error) {
    console.error('❌ Ошибка при удалении проекта:', error)
    toaster.error('Не удалось удалить проект')
  } finally {
    deleteTarget.value = null
  }
}
</script>
