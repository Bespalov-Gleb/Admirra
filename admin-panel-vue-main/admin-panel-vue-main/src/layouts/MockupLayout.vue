<template>
  <div class="main-layout">
    <MockupSidebar :is-collapsed="sidebarCollapsed" />

    <div class="content-wrapper">
      <MockupHeader
        @toggle-sidebar-size="sidebarCollapsed = !sidebarCollapsed"
        @toggle-mobile-menu="sidebarPanelOpen = !sidebarPanelOpen"
      />

      <main class="main-content">
        <slot />
      </main>

      <div class="main__lightBg _pos1"><div class="lightBlurBg"></div></div>
      <div class="main__lightBg _pos2"><div class="lightBlurBg"></div></div>
      <div class="main__lightBg _pos3"><div class="lightBlurBg"></div></div>
    </div>

    <MockupSidebarPanel v-if="sidebarPanelOpen" @close="sidebarPanelOpen = false" />
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import MockupHeader from '../components/mockup/MockupHeader.vue'
import MockupSidebar from '../components/mockup/MockupSidebar.vue'
import MockupSidebarPanel from '../components/mockup/MockupSidebarPanel.vue'
import { useTheme } from '../composables/useTheme'

const sidebarCollapsed = ref(false)
const sidebarPanelOpen = ref(false)
const { isDarkMode } = useTheme()

onMounted(() => {
  document.documentElement.classList.add('mockup-page')
  // Переприменяем тему после добавления mockup-page, чтобы darkmode-класс не слетал
  if (isDarkMode.value) {
    document.documentElement.classList.add('darkmode')
    document.documentElement.classList.add('dark')
  }
})

// При переключении темы внутри mockup-страниц — сразу применяем/снимаем класс
watch(isDarkMode, (dark) => {
  if (dark) {
    document.documentElement.classList.add('darkmode')
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('darkmode')
    document.documentElement.classList.remove('dark')
  }
})

onUnmounted(() => {
  document.documentElement.classList.remove('mockup-page')
})
</script>

<style scoped>
.main-layout {
  display: flex;
  min-height: 100vh;
  position: relative;
  overflow-x: hidden;
}

.content-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  position: relative;
}

.main-content {
  flex: 1;
  /* Небольшой общий зазор от сайдбара и правого края */
  padding: 0 12px;
}

.main__lightBg {
  position: absolute;
  z-index: -1;
  pointer-events: none;
}
</style>
