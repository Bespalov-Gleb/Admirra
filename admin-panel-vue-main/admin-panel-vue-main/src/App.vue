<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuth } from './composables/useAuth'
import Toaster from './components/ui/Toaster.vue'
import OverflowModal from './components/OverflowModal.vue'
import OverflowBanner from './components/OverflowBanner.vue'
import AuthLayout from './layouts/AuthLayout.vue'
import MainLayout from './layouts/MainLayout.vue'
import FullWidthLayout from './layouts/FullWidthLayout.vue'
import LandingLayout from './layouts/LandingLayout.vue'
import MockupLayout from './layouts/MockupLayout.vue'
import FullScreenLayout from './layouts/FullScreenLayout.vue'

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

  // Полноэкранный чистый layout (AI-ассистент): без сайдбара и хедера.
  if (route.meta.layout === 'fullscreen') {
    return FullScreenLayout
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
      <OverflowBanner />
      <!-- Переход между шеллом дашборда и полноэкранным AI: шелл мягко уезжает,
           AI-страница собирается своими блоками (её собственная анимация). -->
      <transition name="ai-swap" mode="out-in">
        <component :is="layout">
          <router-view :key="$route.fullPath" />
        </component>
      </transition>
    </template>
    
    <!-- Global Notifications -->
    <Toaster />
    <!-- Модалка границы тарифа (§8.5): одна на приложение -->
    <OverflowModal />
  </div>
</template>

<style>
#app {
  font-family: 'Inter', 'Play', system-ui, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* Переход смены layout (шелл ↔ полноэкранный AI). Срабатывает только при смене
   самого layout — обычную навигацию внутри дашборда не трогает. */
.ai-swap-leave-active { transition: opacity 0.26s ease, transform 0.26s ease; }
.ai-swap-leave-to { opacity: 0; transform: translateX(-1.5%); }
.ai-swap-enter-active { transition: opacity 0.3s ease; }
.ai-swap-enter-from { opacity: 0; }
@media (prefers-reduced-motion: reduce) {
  .ai-swap-leave-active, .ai-swap-enter-active { transition: none; }
  .ai-swap-leave-to, .ai-swap-enter-from { opacity: 1; transform: none; }
}
</style>
