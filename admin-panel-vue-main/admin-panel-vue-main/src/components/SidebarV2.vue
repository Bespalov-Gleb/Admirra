<template>
  <!-- Overlay для мобильных -->
  <div
    v-if="isMobileMenuOpen"
    @click="closeMobileMenu"
    class="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
  ></div>

  <aside
    :class="[
      'fixed left-0 top-0 h-screen flex flex-col transition-all duration-300 z-50 bg-white border-r border-gray-100 font-[Inter]',
      isCollapsed ? 'w-20' : 'w-[270px]',
      'lg:translate-x-0',
      isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
    ]"
  >
    <!-- Логотип -->
    <div class="px-4 pt-5 pb-3">
      <div class="flex items-center justify-between">
        <div @click="handleBrandClick" class="flex items-center gap-2 cursor-pointer hover:opacity-80">
          <img :src="isCollapsed ? logoFav : logoFull" :alt="'AdMirra'" :class="isCollapsed ? 'h-8 w-8 mx-auto' : 'h-10 w-auto'" />
        </div>
        <button
          v-if="!isCollapsed"
          @click="handleToggleCollapse"
          class="p-1.5 hover:bg-gray-100 rounded-full text-gray-400 hover:text-gray-600 transition-colors"
        >
          <MenuArrow />
        </button>
      </div>
    </div>

    <div class="mx-4 border-t border-gray-200"></div>

    <!-- Основная навигация -->
    <div class="flex-1 min-h-0 overflow-y-auto scrollbar-hide py-3">
      <nav class="space-y-0.5">
        <div v-for="item in menuItems" :key="item.name" class="relative group">

          <!-- Пункт с подменю -->
          <button
            v-if="item.children"
            @click="toggleSubmenu(item.submenuKey)"
            :class="[
              'w-full flex items-center gap-3 px-5 py-[10px] text-left transition-colors rounded-none relative',
              isCollapsed ? 'justify-center' : '',
              isSubmenuActive(item) ? 'text-[#2563EB]' : 'text-[#696969]/[0.76] hover:text-[#2563EB]/80'
            ]"
          >
            <component :is="item.icon" class="w-[18px] h-[18px] flex-shrink-0" />
            <template v-if="!isCollapsed">
              <span
                class="flex-1 text-[12px] font-semibold tracking-[0px]"
                :class="isSubmenuActive(item) ? 'text-[#2563EB]' : 'text-[#696969]/[0.76]'"
              >{{ item.name }}</span>
              <ChevronDownIcon
                :class="[
                  'w-3.5 h-3.5 transition-transform',
                  isSubmenuActive(item) ? 'text-[#2563EB]' : 'text-[#696969]/[0.76]',
                  isSubmenuOpenForKey(item.submenuKey) ? 'rotate-180' : ''
                ]"
              />
            </template>
          </button>

          <!-- Обычный пункт -->
          <button
            v-else
            @click="handleLinkClick(item.path)"
            :class="[
              'w-full flex items-center gap-3 px-5 py-[10px] text-left transition-colors relative',
              isCollapsed ? 'justify-center' : '',
              isActive(item.path) ? 'text-[#2563EB]' : 'text-[#696969]/[0.76] hover:text-[#2563EB]/80'
            ]"
          >
            <!-- Синяя полоска активного -->
            <span
              v-if="isActive(item.path)"
              class="absolute left-0 top-1 bottom-1 w-[3px] bg-[#2563EB] rounded-r-full"
            />
            <component :is="item.icon" class="w-[18px] h-[18px] flex-shrink-0" />
            <span
              v-if="!isCollapsed"
              class="text-[12px] font-semibold"
              :class="isActive(item.path) ? 'text-[#2563EB]' : 'text-[#696969]/[0.76]'"
            >{{ item.name }}</span>
          </button>

          <!-- Tooltip свёрнутое -->
          <div
            v-if="isCollapsed"
            class="absolute left-full ml-2 top-1/2 -translate-y-1/2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50"
          >
            {{ item.name }}
            <div class="absolute right-full top-1/2 -translate-y-1/2 w-0 h-0 border-t-4 border-b-4 border-r-4 border-transparent border-r-gray-900"></div>
          </div>

          <!-- Подменю с соединяющими линиями -->
          <div v-if="item.children && !isCollapsed && isSubmenuOpenForKey(item.submenuKey)" class="pl-[38px] pr-3 pb-1">
            <!-- Вертикальная линия -->
            <div class="relative ml-[10px] border-l-2 border-[#4DB2FF]/30">
              <button
                v-for="child in item.children"
                :key="child.path"
                @click="handleLinkClick(child.path)"
                class="relative w-full flex items-center py-[7px] pl-4 pr-2 text-left transition-colors group/child rounded-r-lg"
                :class="isActive(child.path) ? 'bg-[#4DB2FF]/[0.08]' : 'hover:bg-gray-50'"
              >
                <!-- Горизонтальная соединяющая линия -->
                <span class="absolute left-0 top-1/2 -translate-y-1/2 w-4 h-[2px]"
                  :class="isActive(child.path) ? 'bg-[#2563EB]' : 'bg-[#4DB2FF]/30'"
                />
                <!-- Точка -->
                <span
                  class="w-[6px] h-[6px] rounded-full flex-shrink-0 mr-2.5"
                  :class="isActive(child.path) ? 'bg-[#2563EB]' : 'bg-[#8D8D8D]/50'"
                />
                <span
                  class="text-[11px] font-medium"
                  :class="isActive(child.path) ? 'text-[#2563EB] font-semibold' : 'text-[#696969]/[0.76] group-hover/child:text-[#2563EB]/80'"
                >{{ child.name }}</span>
              </button>
            </div>
          </div>

        </div>
      </nav>
    </div>

    <!-- Разделитель -->
    <div class="mx-4 border-t border-gray-200"></div>

    <!-- Вторичная навигация -->
    <div class="pb-4 pt-2">
      <nav class="space-y-0.5">
        <div v-for="link in bottomLinks" :key="link.name" class="relative group">
          <component
            :is="link.path ? 'button' : 'button'"
            @click="link.action ? link.action() : handleLinkClick(link.path)"
            :class="[
              'w-full flex items-center gap-3 px-5 py-[10px] text-left transition-colors relative',
              isCollapsed ? 'justify-center' : '',
              link.path && isActive(link.path) ? 'text-[#2563EB]' : 'text-[#696969]/[0.76] hover:text-[#2563EB]/80'
            ]"
          >
            <span
              v-if="link.path && isActive(link.path)"
              class="absolute left-0 top-1 bottom-1 w-[3px] bg-[#2563EB] rounded-r-full"
            />
            <component :is="link.icon" class="w-[18px] h-[18px] flex-shrink-0" />
            <span
              v-if="!isCollapsed"
              class="text-[12px] font-semibold"
              :class="link.path && isActive(link.path) ? 'text-[#2563EB]' : 'text-[#696969]/[0.76]'"
            >{{ link.name }}</span>
          </component>
          <div v-if="isCollapsed" class="absolute left-full ml-2 top-1/2 -translate-y-1/2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50">
            {{ link.name }}
            <div class="absolute right-full top-1/2 -translate-y-1/2 w-0 h-0 border-t-4 border-b-4 border-r-4 border-transparent border-r-gray-900"></div>
          </div>
        </div>
      </nav>
    </div>

    <!-- Промо-карточка -->
    <div v-if="!isCollapsed" class="px-4 py-3 mt-auto">
      <div class="rounded-xl bg-gradient-to-br from-[#1e3a5f] to-[#0f2744] p-4 relative overflow-hidden">
        <Cog6ToothIcon class="absolute top-3 left-3 w-4 h-4 text-white/40" />
        <h4 class="text-sm font-bold text-white mb-1">Повысить до премиум</h4>
        <p class="text-xs text-white/80 mb-3">Повысьте ваш аккаунт и разблокируйте все функции</p>
        <router-link
          to="/settings"
          @click="closeMobileMenu"
          class="block w-full py-2 text-center text-xs font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-lg transition-colors"
        >
          Смотреть тарифы
        </router-link>
      </div>
    </div>

  </aside>

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
  ChevronDownIcon,
  ArrowRightOnRectangleIcon,
  PhoneIcon,
  UserCircleIcon,
  ComputerDesktopIcon,
  SparklesIcon,
  Squares2X2Icon,
  ClockIcon,
  Cog6ToothIcon,
  UserGroupIcon,
  ArchiveBoxIcon,
  SignalIcon,
  ChartBarIcon,
  QuestionMarkCircleIcon,
} from '@heroicons/vue/24/outline'
import { useSidebar } from '../composables/useSidebar'
import { useAuth } from '../composables/useAuth'
import { useProjects } from '../composables/useProjects'
import ConfirmModal from './ConfirmModal.vue'
import logoFull from '../assets/imgs/logo/logo-dark.png'
import logoFav from '../assets/imgs/logo/Fav.png'
import MenuArrow from '../assets/icons/menu-arrow.vue'
import Project from '../assets/icons/menu/project.vue'

const { isCollapsed, toggleCollapse, isMobileMenuOpen, closeMobileMenu, toggleMobileMenu } = useSidebar()
const { forceLogout } = useAuth()
const { currentProjectName, setCurrentProject, fetchProjects } = useProjects()

const route = useRoute()
const router = useRouter()
const isDashboardSubmenuOpen = ref(false)
const isPhoneSubmenuOpen = ref(false)
const showLogoutModal = ref(false)

const menuItems = [
  {
    name: 'Аналитика',
    icon: Squares2X2Icon,
    submenuKey: 'dashboard',
    children: [
      { name: 'Аналитика проекта', path: '/dashboard/general-3' },
      { name: 'Общая статистика', path: '/dashboard/general' },
      { name: 'AI Отчет', path: '/ai-analysis' },
    ]
  },
  { name: 'Проекты', path: '/projects', icon: Project },
  { name: 'Команда', path: '/team', icon: UserGroupIcon },
  { name: 'Продукты', path: '/products', icon: ArchiveBoxIcon },
  { name: 'Каналы', path: '/channels', icon: ChartBarIcon },
  {
    name: 'Телефония',
    icon: PhoneIcon,
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

const bottomLinks = computed(() => [
  { name: 'История', path: '/history', icon: ClockIcon },
  { name: 'Настройки', path: '/settings', icon: Cog6ToothIcon },
  { name: 'Помощь', path: '/help', icon: QuestionMarkCircleIcon },
  { name: 'Тех. поддержка', path: '/contact', icon: ComputerDesktopIcon },
  { name: 'Выход', path: null, icon: ArrowRightOnRectangleIcon, action: handleLogoutClick },
])

const isActive = (path) => {
  if (!route?.path || !path) return false
  return route.path === path
}

const isSubmenuActive = (item) => {
  if (!item.children) return false
  return item.children.some(c => isActive(c.path)) || isSubmenuOpenForKey(item.submenuKey)
}

const isSubmenuOpenForKey = (key) => {
  if (key === 'dashboard') return isDashboardSubmenuOpen.value
  if (key === 'phone') return isPhoneSubmenuOpen.value
  return false
}

const toggleSubmenu = (key) => {
  if (isCollapsed.value) {
    toggleCollapse()
    setTimeout(() => {
      if (key === 'dashboard') isDashboardSubmenuOpen.value = true
      if (key === 'phone') isPhoneSubmenuOpen.value = true
    }, 100)
  } else {
    if (key === 'dashboard') isDashboardSubmenuOpen.value = !isDashboardSubmenuOpen.value
    if (key === 'phone') isPhoneSubmenuOpen.value = !isPhoneSubmenuOpen.value
  }
}

watch(() => route?.path, (path) => {
  if (path?.startsWith('/dashboard') || path === '/ai-analysis') {
    isDashboardSubmenuOpen.value = true
  }
  if (path?.startsWith('/phone')) {
    isPhoneSubmenuOpen.value = true
  }
}, { immediate: true })

const handleLinkClick = (path) => {
  if (path) router.push(path)
  closeMobileMenu()
}

const handleToggleCollapse = () => {
  toggleCollapse()
  if (isCollapsed.value) {
    isDashboardSubmenuOpen.value = false
    isPhoneSubmenuOpen.value = false
  }
}

const handleBrandClick = () => {
  if (window.innerWidth < 1024) {
    if (!isMobileMenuOpen.value) toggleMobileMenu()
  } else {
    if (isCollapsed.value) toggleCollapse()
  }
}

function handleLogoutClick() {
  closeMobileMenu()
  showLogoutModal.value = true
}

const handleLogout = () => {
  forceLogout()
  showLogoutModal.value = false
  router.push('/login')
}
</script>
