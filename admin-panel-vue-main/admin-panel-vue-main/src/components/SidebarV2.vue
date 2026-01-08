<template>
  <!-- Overlay для мобильных -->
  <div
    v-if="isMobileMenuOpen"
    @click="closeMobileMenu"
    class="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
  ></div>

  <aside
    :class="[
      'fixed left-0 top-0 h-screen text-white transition-all duration-300 z-50 main-bg-color',
      isCollapsed ? 'w-20' : 'w-[260px]',
      'lg:translate-x-0',
      isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
    ]"
  >
    <!-- Брендинг -->
    <div class="flex items-center justify-between p-5">
      <div v-if="!isCollapsed" @click="handleBrandClick" class="flex items-center gap-2 cursor-pointer hover:opacity-80">
        <img :src="logoFull" alt="Logo" class="h-12 w-auto" />
      </div>
      <div v-else @click="handleBrandClick" class="cursor-pointer hover:opacity-80 mx-auto">
        <img :src="logoFav" alt="Logo" class="h-8 w-8" />
      </div>
      <!-- Кнопка сворачивания в заголовке -->
      <button
        v-if="!isCollapsed"
        @click="handleToggleCollapse"
        class="p-1 hover:bg-gray-700 rounded"
      >
        <MenuArrow />
      </button>
    </div>

    <!-- Кнопка создания проекта -->
    <div class="px-4 mb-2">
      <router-link
        to="/projects/create"
        @click="closeMobileMenu"
        :class="[
          'flex items-center gap-3 w-full bg-blue-600 hover:bg-blue-700 text-white rounded-[16px] transition-all overflow-hidden shadow-lg shadow-blue-900/30 group/create-btn',
          isCollapsed ? 'p-3.5 justify-center' : 'px-5 py-3.5'
        ]"
      >
        <PlusIcon class="w-5 h-5 flex-shrink-0 transition-transform group-hover/create-btn:rotate-90" />
        <span v-if="!isCollapsed" class="text-sm font-black uppercase tracking-widest whitespace-nowrap">Создать проект</span>
      </router-link>
    </div>

    <!-- Навигация -->
    <div class="overflow-y-auto scrollbar-hide h-[calc(100vh-180px)]">
      <nav class="py-4">
        <div v-for="item in menuItems" :key="item.name" class="relative group">
          <!-- Кнопка меню -->
          <button
            @click="item.children ? toggleDashboard() : handleLinkClick(item.path)"
            :class="[
              'relative w-full flex items-center gap-2.5 px-5 py-2.5 text-left',
              isCollapsed && 'justify-center',
              (!item.children && isActive(item.path)) ? 'bg-active-menu' : ''
            ]"
          >
            <ActiveIndicator v-if="!item.children" :is-active="isActive(item.path)" />
            <component :is="item.icon" class="w-4 h-4 flex-shrink-0" />
            <span v-if="!isCollapsed" class="flex-1 text-sm">{{ item.name }}</span>
            <ChevronUpIcon
              v-if="!isCollapsed && item.children"
              :class="[
                'w-4 h-4 transition-transform',
                !isSubmenuOpen && 'rotate-180'
              ]"
            />
          </button>

          <!-- Tooltip для свернутого меню -->
          <div
            v-if="isCollapsed"
            class="absolute left-full ml-2 top-1/2 -translate-y-1/2 px-3 py-2 bg-gray-900 text-white text-sm rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50"
          >
            {{ item.name }}
            <div class="absolute right-full top-1/2 -translate-y-1/2 w-0 h-0 border-t-4 border-b-4 border-r-4 border-transparent border-r-gray-900"></div>
          </div>

          <!-- Выпадающее меню -->
          <div v-if="item.children && !isCollapsed && isSubmenuOpen">
            <button
              v-for="child in item.children"
              :key="child.path"
              @click="handleLinkClick(child.path)"
              :class="[
                'relative w-full flex items-center gap-2.5 px-3 py-2.5 pl-14 text-left',
                isActive(child.path) ? 'bg-active-menu' : ''
              ]"
            >
              <ActiveIndicator :is-active="isActive(child.path)" />
              <Bars3Icon class="w-4 h-4" />
              <span class="text-sm">{{ child.name }}</span>
            </button>
          </div>
        </div>
      </nav>
    </div>

    <!-- Нижние ссылки (Fixed absolute bottom) -->
    <div class="absolute bottom-0 left-0 right-0 pb-10 pointer-events-auto bg-inherit">
      <nav>
        <div class="relative group">
          <router-link
            to="/help"
            @click="closeMobileMenu"
            :class="[
              'relative flex items-center gap-2.5 px-5 py-2.5',
              isCollapsed && 'justify-center',
              isActive('/help') && 'bg-active-menu'
            ]"
          >
            <ActiveIndicator :is-active="isActive('/help')" />
            <span v-if="!isCollapsed" class="text-sm">Помощь</span>
          </router-link>
           <div v-if="isCollapsed" class="absolute left-full ml-2 top-1/2 -translate-y-1/2 px-3 py-2 bg-gray-900 text-white text-sm rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50">
            Помощь
            <div class="absolute right-full top-1/2 -translate-y-1/2 w-0 h-0 border-t-4 border-b-4 border-r-4 border-transparent border-r-gray-900"></div>
          </div>
        </div>

        <div class="relative group">
          <router-link
            to="/contact"
            @click="closeMobileMenu"
            :class="[
              'relative flex items-center gap-2.5 px-5 py-2.5',
              isCollapsed && 'justify-center',
              isActive('/contact') && 'bg-active-menu'
            ]"
          >
            <ActiveIndicator :is-active="isActive('/contact')" />
            <span v-if="!isCollapsed" class="text-sm">Тех. поддержка</span>
          </router-link>
           <div v-if="isCollapsed" class="absolute left-full ml-2 top-1/2 -translate-y-1/2 px-3 py-2 bg-gray-900 text-white text-sm rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50">
            Тех. поддержка
            <div class="absolute right-full top-1/2 -translate-y-1/2 w-0 h-0 border-t-4 border-b-4 border-r-4 border-transparent border-r-gray-900"></div>
          </div>
        </div>

        <div class="relative group">
          <button
            @click="handleLogoutClick"
            :class="[
              'relative w-full flex items-center gap-2.5 px-5 py-2.5 text-left',
              isCollapsed && 'justify-center'
            ]"
          >
            <ActiveIndicator :is-active="false" />
            <ArrowRightOnRectangleIcon class="w-4 h-4 flex-shrink-0" />
            <span v-if="!isCollapsed" class="text-sm">Выход</span>
          </button>
           <div v-if="isCollapsed" class="absolute left-full ml-2 top-1/2 -translate-y-1/2 px-3 py-2 bg-gray-900 text-white text-sm rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50">
            Выход
            <div class="absolute right-full top-1/2 -translate-y-1/2 w-0 h-0 border-t-4 border-b-4 border-r-4 border-transparent border-r-gray-900"></div>
          </div>
        </div>
      </nav>
    </div>

  </aside>

  <!-- Модалка подтверждения выхода -->
  <ConfirmModal
    v-model:is-open="showLogoutModal"
    title="Подтверждение выхода"
    message="Вы уверены, что хотите выйти из системы?"
    @confirm="handleLogout"
  />
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Squares2X2Icon,
  Bars3Icon,
  ChevronUpIcon,
  ArrowRightOnRectangleIcon,
  PlusIcon,
} from '@heroicons/vue/24/outline'
import { useSidebar } from '../composables/useSidebar'
import { useAuth } from '../composables/useAuth'
import ConfirmModal from './ConfirmModal.vue'
import ActiveIndicator from './ActiveIndicator.vue'
import logoFull from '../assets/imgs/logo/AdMirra.png'
import logoFav from '../assets/imgs/logo/Fav.png'
import MenuArrow from '../assets/icons/menu-arrow.vue'

import Project from '../assets/icons/menu/project.vue'
import Group from '../assets/icons/menu/group.vue'
import Product from '../assets/icons/menu/product.vue'
import Channels from '../assets/icons/menu/channels.vue'
import Clock from '../assets/icons/menu/clock.vue'
import Setting from '../assets/icons/menu/setting.vue'

const { isCollapsed, toggleCollapse, isMobileMenuOpen, closeMobileMenu, toggleMobileMenu } = useSidebar()
const { forceLogout } = useAuth()
const route = useRoute()
const router = useRouter()
const isSubmenuOpen = ref(false)
const showLogoutModal = ref(false)

const menuItems = [
  {
    name: 'Дашборд',
    icon: Squares2X2Icon,
    path: '/dashboard', // Base path for active check
    children: [
      { name: 'Статистика по проектам', path: '/dashboard/general' },
      { name: 'Отчет по проекту', path: '/dashboard/general-2' },
      { name: 'Общая статистика v3', path: '/dashboard/general-3' },
    ]
  },
  {
    name: 'Проекты',
    path: '/projects',
    icon: Project,
    children: [
      { name: 'Все проекты', path: '/projects' },
      { name: 'Создать проект', path: '/projects/create' },
    ]
  },
  { name: 'Команда', path: '/team', icon: Group },
  { name: 'Продукты', path: '/products', icon: Product },
  { name: 'Каналы', path: '/channels', icon: Channels },
  { name: 'История', path: '/history', icon: Clock },
  { name: 'Настройки', path: '/settings', icon: Setting },
]

// Закрывать мобильное меню при клике на ссылку
const handleLinkClick = (path) => {
  if (path) {
    router.push(path)
  }
  closeMobileMenu()
}

// Автоматически открывать выпадающее меню, если текущий маршрут имеет вложенность
watch(() => route?.path, (path) => {
  if (path && (path.startsWith('/dashboard') || path.startsWith('/projects'))) {
    isSubmenuOpen.value = true
  } else {
    isSubmenuOpen.value = false
  }
}, { immediate: true })

// Вычисляемое свойство для проверки активного маршрута
const isActive = (path) => {
  if (!route?.path) return false
  if (path === '/dashboard') {
     // Parent activation check
     return route.path.startsWith('/dashboard')
  }
  if (path === '/dashboard/projects') {
    return route.path === '/dashboard/projects' || route.path === '/projects'
  }
  return route.path === path
}

const handleToggleCollapse = () => {
  toggleCollapse()
  if (isCollapsed.value) {
    isSubmenuOpen.value = false
  }
}

const toggleDashboard = () => {
  // Если меню свернуто, разворачиваем его и открываем выпадающее меню
  if (isCollapsed.value) {
    toggleCollapse()
    // Используем nextTick, чтобы дождаться разворачивания меню
    setTimeout(() => {
      isSubmenuOpen.value = true
    }, 100)
  } else {
    // Если меню развернуто, просто переключаем выпадающее меню
    isSubmenuOpen.value = !isSubmenuOpen.value
  }
}

const handleLogoutClick = () => {
  closeMobileMenu()
  showLogoutModal.value = true
}

const handleLogout = () => {
  forceLogout()
  showLogoutModal.value = false
  router.push('/login')
}

// Обработчик клика на "@" - открывает меню, если оно закрыто
const handleBrandClick = () => {
  // На мобильных устройствах: если меню закрыто, открываем его
  if (window.innerWidth < 1024) {
    if (!isMobileMenuOpen.value) {
      toggleMobileMenu()
    }
  } else {
    // На десктопе: если меню свернуто, разворачиваем его
    if (isCollapsed.value) {
      toggleCollapse()
    }
  }
}
</script>
