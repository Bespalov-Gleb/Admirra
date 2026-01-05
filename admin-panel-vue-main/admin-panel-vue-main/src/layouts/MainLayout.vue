<template>
  <div class="flex min-h-screen main-bg-color">
    <SidebarV2 />
    <div :class="[
      'flex-1 transition-all duration-300 ml-0 overflow-x-hidden',
      mainMargin
    ]">
      <Header />
      <main class="overflow-x-hidden bg-dashboard rounded-tl-[40px] mt-2 min-h-[calc(100vh-80px)]">
        <div class="p-8 overflow-x-hidden w-full">
          <router-view />
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import SidebarV2 from '../components/SidebarV2.vue'
import Header from '../components/Header.vue'
import { useSidebar } from '../composables/useSidebar'

const { isCollapsed } = useSidebar()

const mainMargin = computed(() => {
  if (isCollapsed.value) {
    return 'lg:ml-20'
  }
  return 'lg:ml-[260px]'
})
</script>
