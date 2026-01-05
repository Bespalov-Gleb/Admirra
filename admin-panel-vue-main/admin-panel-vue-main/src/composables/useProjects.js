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
      
      // If we have projects but none selected (or selected one is invalid)
      if (projects.value.length > 0) {
        const exists = projects.value.find(p => p.id === currentProjectId.value)
        if (!currentProjectId.value || !exists) {
            currentProjectId.value = projects.value[0].id
            localStorage.setItem('currentProjectId', currentProjectId.value)
        }
      } else {
        currentProjectId.value = null
        localStorage.removeItem('currentProjectId')
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
        // Trigger page refresh or data reload if needed
        window.location.reload() 
    } else {
        localStorage.removeItem('currentProjectId')
    }
  }

  const currentProject = computed(() => {
    return projects.value.find(p => p.id === currentProjectId.value) || null
  })

  return {
    projects,
    currentProjectId,
    currentProject,
    isLoading,
    fetchProjects,
    setCurrentProject
  }
}
