<template>
  <div class="mockup-layout">
    <MockupHeader />
    <main class="main">
      <div class="main-container">
        <MockupSidebar />
        <router-view />
      </div>
      
      <div class="main__lightBg _pos1"><div class="lightBlurBg"></div></div>
      <div class="main__lightBg _pos2"><div class="lightBlurBg"></div></div>
      <div class="main__lightBg _pos3"><div class="lightBlurBg"></div></div>
    </main>
    <MockupSidebarPanel />
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import MockupHeader from '../components/mockup/MockupHeader.vue'
import MockupSidebar from '../components/mockup/MockupSidebar.vue'
import MockupSidebarPanel from '../components/mockup/MockupSidebarPanel.vue'

// Функция для динамической загрузки CSS
const loadCSS = (href, id) => {
  if (document.getElementById(id)) return
  const link = document.createElement('link')
  link.id = id
  link.rel = 'stylesheet'
  link.href = href
  document.head.appendChild(link)
}

// Функция для удаления CSS
const removeCSS = (id) => {
  const link = document.getElementById(id)
  if (link) link.remove()
}

onMounted(() => {
  // Добавляем класс к body для изоляции стилей, если нужно
  document.body.classList.add('mockup-active')
  
  // Загружаем стили нового дизайна
  loadCSS('/admirra/css/normalize.css', 'mockup-normalize')
  loadCSS('/admirra/css/reset.css', 'mockup-reset')
  loadCSS('/admirra/css/grid.css', 'mockup-grid')
  loadCSS('/admirra/css/base.css', 'mockup-base')
  loadCSS('/admirra/css/blocks.css', 'mockup-blocks')
  loadCSS('/admirra/css/components.css', 'mockup-components')
  loadCSS('/admirra/css/ui.css', 'mockup-ui')
  loadCSS('/admirra/css/media.css', 'mockup-media')
  loadCSS('/admirra/css/darkmode.css', 'mockup-darkmode')
  loadCSS('/admirra/css/style.css', 'mockup-style')
  
  // Загружаем скрипты
  const script = document.createElement('script')
  script.src = '/admirra/js/jquery.js'
  script.id = 'mockup-jquery'
  document.body.appendChild(script)
  
  script.onload = () => {
    const ns = document.createElement('script')
    ns.src = '/admirra/js/nice-select.js'
    ns.id = 'mockup-nice-select'
    document.body.appendChild(ns)
  }
})

onUnmounted(() => {
  document.body.classList.remove('mockup-active')
  // Мы можем оставить CSS, если планируем переходить полностью, 
  // но для теста лучше удалять при уходе с этих страниц
  // removeCSS('mockup-normalize')
  // ... и т.д.
})
</script>

<style>
/* Можно добавить специфичные стили для этого лейаута здесь */
.mockup-active {
  /* Чтобы Tailwind не перебивал некоторые базовые вещи */
}
</style>
