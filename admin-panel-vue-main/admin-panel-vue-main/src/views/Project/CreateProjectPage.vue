<template>
  <div class="flex items-center justify-center min-h-[calc(100vh-160px)] px-4">
    <CreateProjectBanner 
      :loading="loading"
      @create="handleCreate"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api/axios'
import { useProjects } from '../../composables/useProjects'
import CreateProjectBanner from '../Dashboard/components/CreateProjectBanner.vue'

const { setCurrentProject, fetchProjects } = useProjects()
const router = useRouter()
const loading = ref(false)

const handleCreate = async (name) => {
  if (!name.trim()) return
  
  loading.value = true
  try {
    const { data } = await api.post('clients/', { name: name.trim() })
    if (data && data.id) {
      setCurrentProject(data.id)
    }
    
    // Refresh global projects list
    await fetchProjects()
    
    // After success, we redirect to the dashboard
    router.push('/dashboard/general-3')
  } catch (err) {
    console.error('Error creating project:', err)
  } finally {
    loading.value = false
  }
}
</script>
