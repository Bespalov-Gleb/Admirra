<template>
  <div class="main-layout">
    <MockupSidebar :is-collapsed="sidebarCollapsed" @toggle="sidebarCollapsed = !sidebarCollapsed" />

    <div class="content-wrapper">
      <MockupHeader
        :project-menu-open="projectMenuOpen"
        @toggle-sidebar-size="sidebarCollapsed = !sidebarCollapsed"
        @toggle-project-menu="projectMenuOpen = !projectMenuOpen"
        @select-project="projectMenuOpen = false"
        @create-project="$router.push('/create')"
        @renew-tariff="$router.push('/tariffs')"
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
import { ref, onMounted, onUnmounted } from 'vue'
import MockupHeader from '../components/mockup/MockupHeader.vue'
import MockupSidebar from '../components/mockup/MockupSidebar.vue'
import MockupSidebarPanel from '../components/mockup/MockupSidebarPanel.vue'

const sidebarCollapsed = ref(false)
const sidebarPanelOpen = ref(false)
const projectMenuOpen = ref(false)

onMounted(() => {
  document.documentElement.classList.add('mockup-page')
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
  padding: 0;
}

.main__lightBg {
  position: absolute;
  z-index: -1;
  pointer-events: none;
}
</style>
