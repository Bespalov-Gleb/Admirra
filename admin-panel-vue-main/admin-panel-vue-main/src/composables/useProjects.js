import { ref, computed } from 'vue'
import axios from '../api/axios'

const projects = ref([])
const currentProjectId = ref(localStorage.getItem('currentProjectId') || null)
const isLoading = ref(false)

export function useProjects() {
  
  const fetchProjects = async () => {
    isLoading.value = true
    try {
      const { data } = await axios.get('/clients/')
      projects.value = data
      
      // If we have a selected project, check if it still exists
      if (currentProjectId.value && projects.value.length > 0) {
        const exists = projects.value.find(p => p.id === currentProjectId.value)
        if (!exists) {
            // If the project was deleted, we default to "All Projects"
            currentProjectId.value = null
            localStorage.removeItem('currentProjectId')
        }
      }
    } catch (error) {
      console.error('Failed to fetch projects:', error)
    } finally {
      isLoading.value = false
    }
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
