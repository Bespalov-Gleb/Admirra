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
import { computed, onBeforeUnmount, onMounted } from 'vue'
import SidebarV2 from '../components/SidebarV2.vue'
import Header from '../components/Header.vue'
import { useSidebar } from '../composables/useSidebar'

const { isCollapsed } = useSidebar()

const mainMargin = computed(() => {
  return isCollapsed.value ? 'min-[1024px]:ml-[5rem]' : 'min-[1024px]:ml-[18.75rem]'
})

// Основные разделы открываются из одного сайдбара. Vite загружает их отдельными
// чанками, поэтому первый переход раньше ждал скачивания и разбора JS. После
// отрисовки текущей страницы заранее прогреваем только три наиболее частых
// раздела; на медленных соединениях или с включённой экономией трафика этого не
// делаем. Данные самих страниц по-прежнему догружаются их скелетонами.
let idleHandle = null
const prefetchPrimaryViews = () => {
  const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection
  if (connection?.saveData || ['slow-2g', '2g'].includes(connection?.effectiveType)) return
  void Promise.allSettled([
    import('../views/GeneralStats3/GeneralStats3.vue'),
    import('../views/Mockup/ProjectCard.vue'),
    import('../views/Reports/Reports.vue'),
  ])
}

onMounted(() => {
  if (typeof window === 'undefined') return
  if (typeof window.requestIdleCallback === 'function') {
    idleHandle = window.requestIdleCallback(prefetchPrimaryViews, { timeout: 2500 })
  } else {
    idleHandle = window.setTimeout(prefetchPrimaryViews, 800)
  }
})

onBeforeUnmount(() => {
  if (idleHandle == null || typeof window === 'undefined') return
  if (typeof window.cancelIdleCallback === 'function') window.cancelIdleCallback(idleHandle)
  else window.clearTimeout(idleHandle)
})
</script>
