import { ref, computed } from 'vue'
import axios from '../api/axios'
import { getAccessToken } from '@/utils/authToken'

const projects = ref([])
const currentProjectId = ref(localStorage.getItem('currentProjectId') || null)
const isLoading = ref(false)
let projectsLoadedAt = 0
let projectsRequest = null

// Список проектов меняется только после явных действий пользователя
// (создание/удаление/настройки). На переходах между разделами можно безопасно
// переиспользовать его недолгое время: это убирает лишний запрос и позволяет
// открыть каркас следующей страницы сразу. Обычный вызов fetchProjects() по
// умолчанию по-прежнему запрашивает свежие данные — это важно после изменений.
const PROJECTS_CACHE_TTL_MS = 30_000

export function useProjects() {
  
  const fetchProjects = async ({ preferCache = false } = {}) => {
    // Проверяем наличие токена перед запросом
    const token = getAccessToken()
    if (!token) {
      console.log('[useProjects] No auth token, skipping projects fetch')
      return
    }

    const cacheIsFresh = projects.value.length > 0
      && (Date.now() - projectsLoadedAt) < PROJECTS_CACHE_TTL_MS
    if (preferCache && cacheIsFresh) return projects.value

    // Одновременные потребители списка (шапка, сайдбар, открываемая страница)
    // используют один HTTP-запрос, а не дублируют его.
    if (projectsRequest) return projectsRequest

    isLoading.value = true
    projectsRequest = axios.get('/clients/')
      .then(({ data }) => {
        projects.value = Array.isArray(data) ? data : []
        projectsLoadedAt = Date.now()

        // If we have a selected project, check if it still exists
        if (currentProjectId.value && projects.value.length > 0) {
          const exists = projects.value.find(p => p.id === currentProjectId.value)
          if (!exists) {
            // If the project was deleted, we default to "All Projects"
            currentProjectId.value = null
            localStorage.removeItem('currentProjectId')
          }
        }
        return projects.value
      })
      .catch((error) => {
        // Игнорируем 401 ошибки (неавторизованный пользователь)
        if (error.response?.status === 401) {
          console.log('[useProjects] Unauthorized, skipping projects fetch')
          return projects.value
        }
        console.error('Failed to fetch projects:', error)
        return projects.value
      })
      .finally(() => {
        isLoading.value = false
        projectsRequest = null
      })

    return projectsRequest
  }

  const setCurrentProject = (id) => {
    currentProjectId.value = id
    if (id) {
        localStorage.setItem('currentProjectId', id)
    } else {
        localStorage.removeItem('currentProjectId')
    }
  }

  const currentProject = computed(() => {
    if (!currentProjectId.value) return null
    return projects.value.find(p => p.id === currentProjectId.value) || null
  })

  const currentProjectName = computed(() => {
    return currentProject.value?.name || 'ВСЕ ПРОЕКТЫ'
  })

  return {
    projects,
    currentProjectId,
    currentProject,
    currentProjectName,
    isLoading,
    fetchProjects,
    setCurrentProject
  }
}
