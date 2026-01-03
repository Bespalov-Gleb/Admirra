<script setup>
import { computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import SidebarV2 from './components/SidebarV2.vue'
import Header from './components/Header.vue'
import { useSidebar } from './composables/useSidebar'
import { useAuth } from './composables/useAuth'

const route = useRoute()
const { isCollapsed } = useSidebar()
const { checkAuth, isAuthenticated } = useAuth()

// Проверяем аутентификацию при загрузке
onMounted(() => {
  checkAuth()
})

// Проверяем аутентификацию при изменении маршрута
watch(() => route.path, () => {
  checkAuth()
}, { immediate: true })

const isAuthPage = computed(() => {
  if (!route) return true
  const path = route.path
  const name = route.name
  
  // Проверяем токен напрямую из localStorage для более надежной проверки
  const token = localStorage.getItem('auth_token')
  const isAuth = !!token
  
  // Если не авторизован, показываем страницы авторизации
  if (!isAuth) {
    return path === '/login' || path === '/' || path === '/register' || path === '/forgot-password' || path === '/reset-password' || name === 'Login' || name === 'Register' || name === 'ForgotPassword' || name === 'ResetPassword'
  }
  // Если авторизован, не показываем страницы авторизации
  return false
})

const mainMargin = computed(() => {
  if (isCollapsed.value) {
    return 'lg:ml-20'
  }
  return 'lg:ml-[260px]'
})
</script>

<template>
  <div id="app" class="min-h-screen main-bg-color">
    <!-- Страница логина -->
    <router-view v-if="isAuthPage" />

    <!-- Основное приложение с сайдбаром и хедером -->
    <div v-else class="flex min-h-screen">
      <SidebarV2 />
      <div :class="[
        'flex-1 transition-all duration-300 ml-0 overflow-x-hidden',
        mainMargin
      ]">
        <Header />
        <main class="overflow-x-hidden bg-[#F4F7FE] rounded-tl-[40px] mt-2 min-h-[calc(100vh-80px)]">
          <div class="p-8 overflow-x-hidden w-full">
            <router-view />
          </div>
        </main>
      </div>
    </div>
  </div>
</template>

<style>
#app {
  font-family: 'Play', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
</style>
