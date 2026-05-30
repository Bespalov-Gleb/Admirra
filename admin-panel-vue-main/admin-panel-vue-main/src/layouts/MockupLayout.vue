<template>
  <div class="flex min-h-screen bg-[#F4F6F8] dark:bg-[#1A1C2C] dark:text-white font-[Inter]">
    <SidebarV2 />
    <div :class="[
      'flex-1 flex flex-col h-screen min-w-0 transition-all duration-300 ml-0',
      mainMargin
    ]">
      <header class="flex-shrink-0">
        <Header />
      </header>
      <main class="flex-1 min-h-0 overflow-y-auto overflow-x-hidden bg-[#F4F6F8] dark:bg-[#232637]">
        <slot />
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
  return isCollapsed.value ? 'min-[1024px]:ml-[5rem]' : 'min-[1024px]:ml-[18.75rem]'
})
</script>
