<template>
  <div class="flex min-h-screen bg-gray-50 font-[Inter]">
    <SidebarV2 />
    <div :class="[
      'flex-1 flex flex-col min-h-screen min-w-0 transition-all duration-300 ml-0',
      mainMargin
    ]">
      <header class="flex-shrink-0">
        <Header />
      </header>
      <main class="flex-1 min-h-0 overflow-y-auto overflow-x-hidden bg-[#F5F7F9]">
        <div class="p-6 pl-9 sm:p-8 sm:pl-12 w-full">
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
  return 'lg:ml-[270px]'
})
</script>
