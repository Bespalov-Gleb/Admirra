<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import SidebarV2 from './components/SidebarV2.vue'
import Header from './components/Header.vue'
import { useSidebar } from './composables/useSidebar'
import { useAuth } from './composables/useAuth'
import Toaster from './components/ui/Toaster.vue'

const route = useRoute()
const { isCollapsed } = useSidebar()
const { checkAuth, isAuthenticated, isLoading } = useAuth()

// Проверяем аутентификацию при загрузке
onMounted(() => {
  checkAuth()
})

const isAuthPage = computed(() => {
  if (!route) return true
  const path = route.path
  const name = route.name
  // Если не авторизован, показываем страницу логина
  if (!isAuthenticated.value) {
    return path === '/login' || path === '/' || name === 'Login'
  }
  // Если авторизован, не показываем страницу логина
  return false
})

const mainMargin = computed(() => {
  if (isCollapsed.value) {
    return 'lg:ml-20'
  }
  return 'lg:ml-[280px]'
})
</script>

<template>
  <div id="app" class="min-h-screen bg-gray-100">
    <!-- Индикатор загрузки при проверке сессии -->
    <div v-if="isLoading" class="fixed inset-0 flex items-center justify-center bg-gray-50 z-[1000]">
      <div class="flex flex-col items-center gap-4">
        <div class="w-10 h-10 border-4 border-gray-200 border-t-black rounded-full animate-spin"></div>
        <p class="text-[10px] font-black uppercase tracking-widest text-gray-400">Загрузка сессии...</p>
      </div>
    </div>

    <template v-else>
      <!-- Страница логина -->
      <router-view v-if="isAuthPage" :key="$route.path" />

      <!-- Основное приложение с сайдбаром и хедером -->
      <div v-else class="flex min-h-screen">
        <SidebarV2 />
        <div :class="[
          'flex-1 transition-all duration-300 ml-0',
          mainMargin
        ]">
          <Header />
          <main>
            <div class="p-8">
              <router-view :key="$route.fullPath" />
            </div>
          </main>
        </div>
      </div>
    </template>
    
    <!-- Global Notifications -->
    <Toaster />
  </div>
</template>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
</style>
