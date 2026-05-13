<template>
  <div class="flex min-h-screen bg-[#F4F6F8] dark:bg-[#1A1C2C] font-[Inter]">
    <SidebarV2 />
    <div :class="[
      'flex-1 flex flex-col min-h-screen min-w-0 transition-all duration-300 ml-0',
      mainMargin
    ]">
      <header class="flex-shrink-0">
        <Header />
      </header>
      <main class="flex-1 min-h-0 overflow-y-auto overflow-x-hidden bg-[#F4F6F8] dark:bg-[#232637]">
        <div class="w-full px-4 py-5 sm:px-6 sm:py-6 lg:px-8 lg:py-7">
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
    return 'min-[1024px]:ml-20'
  }
  return 'min-[1024px]:ml-[18.75rem]'
})
</script>
