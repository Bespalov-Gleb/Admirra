<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuth } from './composables/useAuth'
import Toaster from './components/ui/Toaster.vue'
import AuthLayout from './layouts/AuthLayout.vue'
import MainLayout from './layouts/MainLayout.vue'
import FullWidthLayout from './layouts/FullWidthLayout.vue'
import LandingLayout from './layouts/LandingLayout.vue'
import MockupLayout from './layouts/MockupLayout.vue'

const route = useRoute()
const { isLoading } = useAuth()

const layout = computed(() => {
  // Check for auth layout meta or fallback to MainLayout
  if (route.meta.layout === 'auth') {
    return AuthLayout
  }
  
  // Full width layout (no sidebar)
  if (route.meta.layout === 'fullwidth') {
    return FullWidthLayout
  }

  // Лендинг AdMirra
  if (route.meta.layout === 'landing') {
    return LandingLayout
  }

  // Mockup pages (13 new pages with new design)
  if (route.meta.layout === 'mockup') {
    return MockupLayout
  }
  
  // Legacy support for paths if they are not in router meta yet
  const isPathAuth = ['/login', '/register', '/forgot-password', '/reset-password', '/signin', '/signup', '/verify-email', '/pending-email-verification', '/two-step-verification'].includes(route.path)
  if (isPathAuth) {
    return AuthLayout
  }
  
  return MainLayout
})
</script>

<template>
  <div id="app" class="min-h-screen main-bg-color">
    <!-- Индикатор загрузки при проверке сессии -->
    <div v-if="isLoading" class="fixed inset-0 flex items-center justify-center bg-gray-50 dark:bg-[#1A1C2C] z-[1000]">
      <div class="flex flex-col items-center gap-4">
        <div class="w-10 h-10 border-4 border-gray-200 border-t-black rounded-full animate-spin"></div>
        <p class="text-[0.6944rem] font-black uppercase tracking-widest text-gray-400">Загрузка сессии...</p>
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
  font-family: 'Inter', 'Play', system-ui, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
</style>
