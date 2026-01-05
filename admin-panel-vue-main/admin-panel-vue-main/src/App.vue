<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuth } from './composables/useAuth'
import Toaster from './components/ui/Toaster.vue'
import AuthLayout from './layouts/AuthLayout.vue'
import MainLayout from './layouts/MainLayout.vue'

const route = useRoute()
const { checkAuth, isLoading } = useAuth()

onMounted(() => {
  checkAuth()
})

const layout = computed(() => {
  // Check for auth layout meta or fallback to MainLayout
  if (route.meta.layout === 'auth') {
    return AuthLayout
  }
  // Legacy support for paths if they are not in router meta yet
  const isPathAuth = ['/login', '/register', '/forgot-password', '/reset-password'].includes(route.path)
  if (isPathAuth) {
    return AuthLayout
  }
  
  return MainLayout
})
</script>

<template>
  <div id="app" class="min-h-screen main-bg-color">
    <!-- Индикатор загрузки при проверке сессии -->
    <div v-if="isLoading" class="fixed inset-0 flex items-center justify-center bg-gray-50 z-[1000]">
      <div class="flex flex-col items-center gap-4">
        <div class="w-10 h-10 border-4 border-gray-200 border-t-black rounded-full animate-spin"></div>
        <p class="text-[10px] font-black uppercase tracking-widest text-gray-400">Загрузка сессии...</p>
      </div>
    </div>

    <template v-else>
      <component :is="layout">
        <router-view :key="$route.fullPath" />
      </component>
    </template>
    
    <!-- Global Notifications -->
    <Toaster />
  </div>
</template>

<style>
#app {
  font-family: 'Play', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
</style>
