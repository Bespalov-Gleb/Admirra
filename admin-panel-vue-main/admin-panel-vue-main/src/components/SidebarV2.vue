<template>
  <!-- Overlay для мобильных -->
  <div
    v-if="isMobileMenuOpen"
    @click="closeMobileMenu"
    class="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
  ></div>

  <aside
    :class="[
      'fixed left-0 top-0 h-screen flex flex-col text-white transition-all duration-300 z-50 main-bg-color',
      isCollapsed ? 'w-20' : 'w-[260px]',
      'lg:translate-x-0',
      isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
    ]"
  >
    <!-- Брендинг + селектор контекста -->
    <div class="px-4 pt-5 pb-3">
      <div class="flex items-center justify-between">
        <div @click="handleBrandClick" class="flex items-center gap-2 cursor-pointer hover:opacity-80">
          <img :src="isCollapsed ? logoFav : logoFull" :alt="'Logo'" :class="isCollapsed ? 'h-8 w-8 mx-auto' : 'h-10 w-auto'" />
        </div>
        <button
          v-if="!isCollapsed"
          @click="handleToggleCollapse"
          class="p-1.5 hover:bg-white/10 rounded text-gray-400 hover:text-white transition-colors"
        >
          <MenuArrow />
        </button>
      </div>
      <!-- Селектор контекста (Трафик агентство / Проект) -->
      <div v-if="!isCollapsed" ref="contextSelectorRef" class="mt-3 relative">
        <button
          @click="handleContextSelect"
          class="w-full flex items-center justify-between px-3 py-2 rounded-lg text-left text-sm text-gray-400 hover:bg-white/5 hover:text-gray-300 transition-colors"
        >
          <span class="truncate">{{ contextLabel }}</span>
          <ChevronDownIcon class="w-4 h-4 flex-shrink-0 transition-transform" :class="{ 'rotate-180': showContextDropdown }" />
        </button>
        <!-- Выпадающий список проектов -->
        <div
          v-if="showContextDropdown"
          class="absolute left-0 right-0 top-full mt-1 py-2 bg-[#1e293b] rounded-lg shadow-xl border border-white/10 z-50 max-h-48 overflow-y-auto"
        >
          <button
            @click="handleProjectSelect(null)"
            class="w-full px-4 py-2 text-left text-sm hover:bg-white/5 flex items-center justify-between"
            :class="!currentProjectId ? 'text-blue-400' : 'text-gray-300'"
          >
            <span>Все проекты</span>
            <CheckIcon v-if="!currentProjectId" class="w-4 h-4 text-blue-400" />
          </button>
          <button
            v-for="p in projects"
            :key="p.id"
            @click="handleProjectSelect(p.id)"
            class="w-full px-4 py-2 text-left text-sm hover:bg-white/5 flex items-center justify-between truncate"
            :class="currentProjectId === p.id ? 'text-blue-400' : 'text-gray-300'"
          >
            <span class="truncate">{{ p.name }}</span>
            <CheckIcon v-if="currentProjectId === p.id" class="w-4 h-4 text-blue-400 flex-shrink-0" />
          </button>
          <div class="border-t border-white/10 my-2"></div>
          <router-link
            to="/projects/create"
            @click="showContextDropdown = false; closeMobileMenu()"
            class="flex items-center gap-2 px-4 py-2 text-sm text-blue-400 hover:bg-white/5"
          >
            <PlusIcon class="w-4 h-4" />
            Создать проект
          </router-link>
        </div>
      </div>
    </div>

    <!-- Разделитель -->
    <div class="mx-4 border-t border-white/12 sidebar-separator"></div>

    <!-- Навигация -->
    <div class="flex-1 min-h-0 overflow-y-auto scrollbar-hide py-3">
      <nav class="space-y-0.5">
        <template v-for="(section, sectionIdx) in menuSections" :key="section.title">
          <div
            v-if="sectionIdx > 0"
            class="mx-4 my-3 border-t border-white/12 sidebar-separator"
          ></div>
          <div v-for="item in section.items" :key="item.name" class="relative group">
            <!-- Кнопка меню -->
            <button
              @click="item.children ? toggleSubmenu(item.submenuKey) : handleLinkClick(item.path)"
              :class="[
                'relative w-full flex items-center gap-2.5 px-5 py-2.5 text-left text-sm transition-colors',
                isCollapsed && 'justify-center',
                (!item.children && isActive(item.path)) ? 'bg-active-menu text-white' : 'text-gray-400 hover:bg-white/5 hover:text-gray-300'
              ]"
            >
              <ActiveIndicator v-if="!item.children" :is-active="isActive(item.path)" />
              <component :is="item.icon" class="w-4 h-4 flex-shrink-0" />
              <span v-if="!isCollapsed" class="flex-1 text-sm font-medium">{{ item.name }}</span>
              <ChevronDownIcon
                v-if="!isCollapsed && item.children"
                :class="[
                  'w-4 h-4 transition-transform text-blue-400',
                  !isSubmenuOpenForKey(item.submenuKey) && '-rotate-90'
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
            <div v-if="item.children && !isCollapsed && isSubmenuOpenForKey(item.submenuKey)">
              <button
                v-for="child in item.children"
                :key="child.path"
                @click="handleLinkClick(child.path)"
                :class="[
                  'relative w-full flex items-center gap-2.5 px-3 py-2.5 pl-14 text-left text-sm transition-colors',
                  isActive(child.path) ? 'bg-active-menu text-white' : 'text-gray-400 hover:bg-white/5 hover:text-gray-300'
                ]"
              >
                <ActiveIndicator :is-active="isActive(child.path)" />
                <Bars3Icon class="w-4 h-4" />
                <span class="text-sm font-medium">{{ child.name }}</span>
              </button>
            </div>
          </div>
        </template>
      </nav>
    </div>

    <!-- Разделитель перед нижним блоком -->
    <div class="mx-4 border-t border-white/12 sidebar-separator"></div>

    <!-- Промо-карточка -->
    <div v-if="!isCollapsed" class="px-4 py-3">
      <div class="rounded-xl bg-[#1e3a5f] p-4">
        <h4 class="text-sm font-bold text-white mb-1">Повысить до премиум</h4>
        <p class="text-xs text-white/80 mb-3">Расширенные отчёты и аналитика</p>
        <router-link
          to="/settings"
          @click="closeMobileMenu"
          class="block w-full py-2 text-center text-xs font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-lg transition-colors"
        >
          Смотреть тарифы
        </router-link>
      </div>
    </div>

    <!-- Нижние ссылки -->
    <div class="px-0 pb-4 pt-2">
      <nav class="space-y-0.5">
        <div class="relative group">
          <router-link
            to="/history"
            @click="closeMobileMenu"
            :class="[
              'relative flex items-center gap-2.5 px-5 py-2.5 text-sm',
              isCollapsed && 'justify-center',
              isActive('/history') ? 'bg-active-menu text-white' : 'text-gray-400 hover:bg-white/5 hover:text-gray-300'
            ]"
          >
            <ActiveIndicator :is-active="isActive('/history')" />
            <Clock class="w-4 h-4 flex-shrink-0" />
            <span v-if="!isCollapsed">История</span>
          </router-link>
          <div v-if="isCollapsed" class="absolute left-full ml-2 top-1/2 -translate-y-1/2 px-3 py-2 bg-gray-900 text-white text-sm rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50">
            История
            <div class="absolute right-full top-1/2 -translate-y-1/2 w-0 h-0 border-t-4 border-b-4 border-r-4 border-transparent border-r-gray-900"></div>
          </div>
        </div>
        <div class="relative group">
          <router-link
            to="/settings"
            @click="closeMobileMenu"
            :class="[
              'relative flex items-center gap-2.5 px-5 py-2.5 text-sm',
              isCollapsed && 'justify-center',
              isActive('/settings') ? 'bg-active-menu text-white' : 'text-gray-400 hover:bg-white/5 hover:text-gray-300'
            ]"
          >
            <ActiveIndicator :is-active="isActive('/settings')" />
            <Setting class="w-4 h-4 flex-shrink-0" />
            <span v-if="!isCollapsed">Настройки</span>
          </router-link>
          <div v-if="isCollapsed" class="absolute left-full ml-2 top-1/2 -translate-y-1/2 px-3 py-2 bg-gray-900 text-white text-sm rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50">
            Настройки
            <div class="absolute right-full top-1/2 -translate-y-1/2 w-0 h-0 border-t-4 border-b-4 border-r-4 border-transparent border-r-gray-900"></div>
          </div>
        </div>
        <div class="mx-4 my-2 border-t border-white/12 sidebar-separator"></div>
        <div class="relative group">
          <router-link
            to="/help"
            @click="closeMobileMenu"
            :class="[
              'relative flex items-center gap-2.5 px-5 py-2.5 text-sm',
              isCollapsed && 'justify-center',
              isActive('/help') ? 'bg-active-menu text-white' : 'text-gray-400 hover:bg-white/5 hover:text-gray-300'
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
              'relative flex items-center gap-2.5 px-5 py-2.5 text-sm',
              isCollapsed && 'justify-center',
              isActive('/contact') ? 'bg-active-menu text-white' : 'text-gray-400 hover:bg-white/5 hover:text-gray-300'
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
              'relative w-full flex items-center gap-2.5 px-5 py-2.5 text-left text-sm text-gray-400 hover:bg-white/5 hover:text-gray-300',
              isCollapsed && 'justify-center'
            ]"
          >
            <ArrowRightOnRectangleIcon class="w-4 h-4 flex-shrink-0" />
            <span v-if="!isCollapsed">Выход</span>
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
import { ref, watch, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ChartBarIcon,
  Bars3Icon,
  ChevronDownIcon,
  ArrowRightOnRectangleIcon,
  PlusIcon,
  PhoneIcon,
  SparklesIcon,
} from '@heroicons/vue/24/outline'
import { CheckIcon } from '@heroicons/vue/24/solid'
import { useSidebar } from '../composables/useSidebar'
import { useAuth } from '../composables/useAuth'
import { useProjects } from '../composables/useProjects'
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
const { currentProjectName, currentProjectId, projects, setCurrentProject, fetchProjects } = useProjects()

const contextLabel = computed(() => currentProjectName.value || 'Трафик агентство')
const showContextDropdown = ref(false)

const handleContextSelect = () => {
  showContextDropdown.value = !showContextDropdown.value
  if (showContextDropdown.value) fetchProjects()
}

const handleProjectSelect = (id) => {
  setCurrentProject(id)
  showContextDropdown.value = false
}

const contextSelectorRef = ref(null)
const handleClickOutsideContext = (e) => {
  if (contextSelectorRef.value && !contextSelectorRef.value.contains(e.target)) {
    showContextDropdown.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutsideContext)
})
onUnmounted(() => {
  document.removeEventListener('click', handleClickOutsideContext)
})
const route = useRoute()
const router = useRouter()
const isDashboardSubmenuOpen = ref(false)
const isPhoneSubmenuOpen = ref(false)
const showLogoutModal = ref(false)

const menuSections = [
  {
    title: 'ОСНОВНОЕ',
    items: [
      {
        name: 'AI Анализ',
        path: '/ai-analysis',
        icon: SparklesIcon
      },
      {
        name: 'Аналитика',
        icon: ChartBarIcon,
        path: '/dashboard',
        submenuKey: 'dashboard',
        children: [
          { name: 'Аналитика проекта', path: '/dashboard/general-3' },
          { name: 'Сформировать отчет', path: '/dashboard/general-2' },
          { name: 'Общая статистика', path: '/dashboard/general' },
        ]
      },
      {
        name: 'Проекты',
        path: '/projects',
        icon: Project
      }
    ]
  },
  {
    title: 'УПРАВЛЕНИЕ',
    items: [
      { name: 'Команда', path: '/team', icon: Group },
      { name: 'Продукты', path: '/products', icon: Product },
      { name: 'Каналы', path: '/channels', icon: Channels },
      {
        name: 'Телефония',
        icon: PhoneIcon,
        path: '/phone',
        submenuKey: 'phone',
        children: [
          { name: 'Проекты', path: '/phone-projects' },
          { name: 'Квалификатор', path: '/phone-api' },
          { name: 'Интеграция', path: '/phone-integration' },
          { name: 'Лиды', path: '/phone-leads' },
          { name: 'Статистика', path: '/phone-stats' },
          { name: 'Отчёты', path: '/phone-reports' },
        ]
      },
    ]
  },
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
  if (path && path.startsWith('/dashboard')) {
    isDashboardSubmenuOpen.value = true
  } else {
    isDashboardSubmenuOpen.value = false
  }
  
  if (path && path.startsWith('/phone')) {
    isPhoneSubmenuOpen.value = true
  } else {
    isPhoneSubmenuOpen.value = false
  }
}, { immediate: true })

// Вычисляемое свойство для проверки активного маршрута
const isActive = (path) => {
  if (!route?.path) return false
  // Для родительских элементов с submenu не подсвечиваем их
  // Подсвечиваем только если это точное совпадение пути
  return route.path === path
}

const handleToggleCollapse = () => {
  toggleCollapse()
  if (isCollapsed.value) {
    isDashboardSubmenuOpen.value = false
    isPhoneSubmenuOpen.value = false
  }
}

// Проверка, открыто ли submenu для данного ключа
const isSubmenuOpenForKey = (key) => {
  if (key === 'dashboard') return isDashboardSubmenuOpen.value
  if (key === 'phone') return isPhoneSubmenuOpen.value
  return false
}

// Переключение submenu для данного ключа
const toggleSubmenu = (key) => {
  // Если меню свернуто, разворачиваем его и открываем выпадающее меню
  if (isCollapsed.value) {
    toggleCollapse()
    // Используем setTimeout, чтобы дождаться разворачивания меню
    setTimeout(() => {
      if (key === 'dashboard') isDashboardSubmenuOpen.value = true
      if (key === 'phone') isPhoneSubmenuOpen.value = true
    }, 100)
  } else {
    // Если меню развернуто, просто переключаем выпадающее меню
    if (key === 'dashboard') {
      isDashboardSubmenuOpen.value = !isDashboardSubmenuOpen.value
    }
    if (key === 'phone') {
      isPhoneSubmenuOpen.value = !isPhoneSubmenuOpen.value
    }
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
