<template>
  <!-- Overlay для мобильных -->
  <div
    v-if="isMobileMenuOpen"
    @click="closeMobileMenu"
    class="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
  ></div>

  <aside
    :class="[
      'fixed left-0 top-0 h-screen flex flex-col transition-all duration-300 z-50 font-[Inter]',
      'bg-white dark:bg-[#2C2F3D] border-r border-gray-100 dark:border-white/10',
      isCollapsed ? 'w-20' : 'w-[270px]',
      'lg:translate-x-0',
      isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
    ]"
  >
    <!-- Логотип -->
    <div class="px-4 pt-5 pb-3">
      <div class="flex items-center justify-between">
        <div @click="handleBrandClick" class="flex items-center gap-2 cursor-pointer hover:opacity-80">
          <img 
            :src="isCollapsed ? logoFav : (isDarkMode ? logoFullDark : logoFull)" 
            :alt="'AdMirra'" 
            :class="[
              isCollapsed ? 'h-8 w-8 mx-auto' : 'h-10 w-auto'
            ]" 
          />
        </div>
        <button
          v-if="!isCollapsed"
          @click="handleToggleCollapse"
          class="p-1.5 hover:bg-gray-100 dark:hover:bg-white/10 rounded-full text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
        >
          <MenuArrow />
        </button>
      </div>
    </div>

    <!-- Основная навигация -->
    <div class="shrink min-h-0 overflow-y-auto scrollbar-hide py-3">
      <nav class="px-3 space-y-1.5">
        <div v-for="item in menuItems" :key="item.name" class="relative group">

          <!-- Пункт с подменю — обёртка только вокруг кнопки для позиционирования полоски -->
          <div v-if="item.children" class="relative">
            <div
              v-if="isSubmenuActive(item)"
              class="absolute left-0 top-1 bottom-1 w-[3px] rounded-full bg-[#2563EB] dark:bg-[#4A7AFF] z-10"
            ></div>
            <button
              @click="toggleSubmenu(item.submenuKey)"
              :class="[
                'w-full flex items-center gap-3 pl-6 pr-4 py-3.5 text-left rounded-[10px] transition-all',
                isCollapsed ? 'justify-center' : '',
                isSubmenuActive(item) ? 'bg-[#EBF3FF] dark:bg-white/10' : 'hover:bg-gray-100/70 dark:hover:bg-white/5'
              ]"
            >
              <component
                :is="item.icon"
                class="w-6 h-6 flex-shrink-0"
                :class="isSubmenuActive(item) ? 'text-[#2563EB] dark:text-[#4A7AFF]' : 'text-[#696969]/[0.76] dark:text-gray-400'"
              />
              <template v-if="!isCollapsed">
                <span
                  class="flex-1 text-[12px] font-semibold"
                  :class="isSubmenuActive(item) ? 'text-[#2563EB] dark:text-[#4A7AFF]' : 'text-[#696969]/[0.76] dark:text-gray-400'"
                >{{ item.name }}</span>
                <ChevronDownIcon
                  class="w-3.5 h-3.5 transition-transform"
                  :class="[
                    isSubmenuActive(item) ? 'text-[#2563EB] dark:text-[#4A7AFF]' : 'text-[#696969]/[0.76] dark:text-gray-400',
                    isSubmenuOpenForKey(item.submenuKey) ? 'rotate-180' : ''
                  ]"
                />
              </template>
            </button>
          </div>

          <!-- Обычный пункт — обёртка только вокруг кнопки для позиционирования полоски -->
          <div v-else class="relative">
            <div
              v-if="isActive(item.path)"
              class="absolute left-0 top-1 bottom-1 w-[3px] rounded-full bg-[#2563EB] dark:bg-[#4A7AFF] z-10"
            ></div>
            <button
              @click="handleLinkClick(item.path)"
              :class="[
                'w-full flex items-center gap-3 pl-6 pr-8 py-3.5 text-left rounded-[10px] transition-all',
                isCollapsed ? 'justify-center' : '',
                isActive(item.path) ? 'bg-[#EBF3FF] dark:bg-white/10' : 'hover:bg-gray-100/70 dark:hover:bg-white/5'
              ]"
            >
              <component
                :is="item.icon"
                class="w-6 h-6 flex-shrink-0"
                :class="isActive(item.path) ? 'text-[#2563EB] dark:text-[#4A7AFF]' : 'text-[#696969]/[0.76] dark:text-gray-400'"
              />
              <span
                v-if="!isCollapsed"
                class="text-[12px] font-semibold"
                :class="isActive(item.path) ? 'text-[#2563EB] dark:text-[#4A7AFF]' : 'text-[#696969]/[0.76] dark:text-gray-400'"
              >{{ item.name }}</span>
            </button>
          </div>

          <!-- Tooltip свёрнутое -->
          <div
            v-if="isCollapsed"
            class="absolute left-full ml-2 top-1/2 -translate-y-1/2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50"
          >
            {{ item.name }}
            <div class="absolute right-full top-1/2 -translate-y-1/2 w-0 h-0 border-t-4 border-b-4 border-r-4 border-transparent border-r-gray-900"></div>
          </div>

          <!-- Подменю с соединяющими линиями -->
          <div v-if="item.children && !isCollapsed && isSubmenuOpenForKey(item.submenuKey)" class="relative pt-0.5 pb-1">
            <div
              v-for="(child, idx) in item.children"
              :key="child.path"
              class="relative pl-[56px] pr-0"
            >
              <!-- Вертикальный отрезок: от верха до низа, только для не-последних элементов -->
              <div
                v-if="idx < item.children.length - 1"
                class="absolute left-[36px] top-0 bottom-0 w-[1.5px] bg-gray-200 dark:bg-white/20"
              ></div>

              <!-- Закруглённая ветка L-образная (верх → середина + горизонталь) -->
              <div
                class="absolute left-[36px] w-[14px] border-l-[1.5px] border-b-[1.5px] border-gray-200 dark:border-white/20 rounded-bl-[6px]"
                style="top: 0; height: calc(50% + 1px);"
              ></div>

              <button
                @click="handleLinkClick(child.path)"
                class="w-full flex items-center py-[9px] px-3 text-left rounded-[8px] transition-all"
                :class="isActive(child.path) ? 'bg-[#EBF3FF] dark:bg-white/10' : 'hover:bg-gray-100/70 dark:hover:bg-white/5'"
              >
                <span
                  class="text-[11px] font-semibold"
                  :class="isActive(child.path) ? 'text-[#2563EB] dark:text-[#4A7AFF]' : 'text-[#696969]/[0.76] dark:text-gray-400'"
                >{{ child.name }}</span>
              </button>
            </div>
          </div>

        </div>
      </nav>
    </div>

    <!-- Нижняя навигация -->
    <div class="mt-auto shrink-0 pb-4">
      <nav class="px-3 space-y-1.5 py-2">
        <div v-for="link in bottomLinks" :key="link.name" class="relative group">
          <button
            @click="link.action ? link.action() : handleLinkClick(link.path)"
            :class="[
              'w-full flex items-center gap-3 pl-6 pr-8 py-3.5 text-left rounded-[10px] transition-all',
              isCollapsed ? 'justify-center' : '',
              link.path && isActive(link.path) ? 'bg-[#EBF3FF] dark:bg-white/10' : 'hover:bg-gray-100/70 dark:hover:bg-white/5'
            ]"
          >
            <component
              :is="link.icon"
              class="w-6 h-6 flex-shrink-0"
              :class="link.path && isActive(link.path) ? 'text-[#2563EB] dark:text-[#4A7AFF]' : 'text-[#696969]/[0.76] dark:text-gray-400'"
            />
            <span
              v-if="!isCollapsed"
              class="text-[12px] font-semibold"
              :class="link.path && isActive(link.path) ? 'text-[#2563EB] dark:text-[#4A7AFF]' : 'text-[#696969]/[0.76] dark:text-gray-400'"
            >{{ link.name }}</span>
          </button>
          <div v-if="isCollapsed" class="absolute left-full ml-2 top-1/2 -translate-y-1/2 px-3 py-2 bg-gray-900 dark:bg-[#2A2D3C] text-white text-xs rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50">
            {{ link.name }}
            <div class="absolute right-full top-1/2 -translate-y-1/2 w-0 h-0 border-t-4 border-b-4 border-r-4 border-transparent border-r-gray-900 dark:border-r-[#2A2D3C]"></div>
          </div>
        </div>
      </nav>
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
import { ref, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ChevronDownIcon,
  ArrowRightOnRectangleIcon,
  ComputerDesktopIcon,
  Squares2X2Icon,
  ArchiveBoxIcon,
  CpuChipIcon,
  LinkIcon,
  ClockIcon,
  Cog6ToothIcon,
  UserGroupIcon,
  RectangleStackIcon,
} from '@heroicons/vue/24/outline'
import { useSidebar } from '../composables/useSidebar'
import { useAuth } from '../composables/useAuth'
import { useTheme } from '../composables/useTheme'
import ConfirmModal from './ConfirmModal.vue'
import logoFull from '../assets/imgs/logo/logo-dark.png'
import logoFullDark from '../assets/imgs/logo/AdMirra.png'
import logoFav from '../assets/imgs/logo/Fav.png'
import MenuArrow from '../assets/icons/menu-arrow.vue'
import IconProject from '../assets/icons/menu/project.vue'
import { ADMIRRA_PUBLIC_HOST } from '../config/admirraPublic'

const { isCollapsed, toggleCollapse, isMobileMenuOpen, closeMobileMenu, toggleMobileMenu } = useSidebar()
const { isDarkMode } = useTheme()
const { forceLogout } = useAuth()

const route = useRoute()
const router = useRouter()
const isDashboardSubmenuOpen = ref(false)
const showLogoutModal = ref(false)

const currentHost = computed(() => {
  if (typeof window !== 'undefined' && window.location?.hostname) {
    return window.location.hostname.toLowerCase()
  }
  return (ADMIRRA_PUBLIC_HOST || '').toLowerCase()
})

const showQualifierLink = computed(() => {
  const host = currentHost.value
  return !!host && !host.endsWith('.ru') && host !== 'admirra.ru'
})

const menuItems = computed(() => {
  const items = [
    {
      name: 'Аналитика',
      icon: Squares2X2Icon,
      submenuKey: 'dashboard',
      children: [
        { name: 'Аналитика проекта', path: '/dashboard/general-3' },
        { name: 'AI отчет по проекту', path: '/ai-analysis' },
      ]
    },
    { name: 'Проекты', path: '/projects', icon: IconProject },
    { name: 'Интеграции', path: '/integrations/wizard', icon: RectangleStackIcon },
  ]

  if (showQualifierLink.value) {
    items.push({ name: 'Квалификатор', path: '/phone-api', icon: ArchiveBoxIcon })
  }

  items.push(
    { name: 'Команда', path: '/team', icon: UserGroupIcon },
    { name: 'История', path: '/history', icon: ClockIcon },
    { name: 'Настройки', path: '/settings', icon: Cog6ToothIcon },
    { name: 'Тарифы', path: '/tariffs', icon: CpuChipIcon },
  )

  return items
})

const bottomLinks = computed(() => [
  { name: 'Поддержка', path: '/contact', icon: ComputerDesktopIcon },
  { name: 'Выход', action: handleLogoutClick, icon: ArrowRightOnRectangleIcon },
])

const isActive = (path) => {
  if (!route?.path || !path) return false
  return route.path === path || route.path.startsWith(`${path}/`)
}

const isSubmenuActive = (item) => {
  if (!item.children) return false
  return item.children.some(c => isActive(c.path)) || isSubmenuOpenForKey(item.submenuKey)
}

const isSubmenuOpenForKey = (key) => {
  if (key === 'dashboard') return isDashboardSubmenuOpen.value
  return false
}

const toggleSubmenu = (key) => {
  if (isCollapsed.value) {
    toggleCollapse()
    setTimeout(() => {
      if (key === 'dashboard') isDashboardSubmenuOpen.value = true
    }, 100)
  } else {
    if (key === 'dashboard') isDashboardSubmenuOpen.value = !isDashboardSubmenuOpen.value
  }
}

watch(() => route?.path, (path) => {
  if (path?.startsWith('/dashboard')) {
    isDashboardSubmenuOpen.value = true
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
  router.push('/signin')
}
</script>
