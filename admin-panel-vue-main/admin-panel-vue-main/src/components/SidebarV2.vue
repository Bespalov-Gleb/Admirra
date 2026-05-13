<template>
  <!-- Mobile overlay -->
  <div
    v-if="isMobileMenuOpen"
    @click="closeMobileMenu"
    class="fixed inset-0 bg-black/50 z-40 min-[1920px]:hidden"
  />

  <aside
    :class="[
      'fixed left-0 top-0 h-screen flex flex-col z-50 transition-all duration-300',
      'bg-white dark:bg-[#2C2F3D]',
      'border-r border-black/5 dark:border-white/10',
      isCollapsed ? 'w-[72px]' : 'w-[270px]',
      isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full min-[1920px]:translate-x-0',
    ]"
  >
    <!-- Logo header — matches header__aside height (76px) -->
    <div
      :class="[
        'flex items-center justify-between flex-shrink-0 border-b border-black/5 dark:border-white/10',
        'h-[76px]',
        isCollapsed ? 'px-[14px]' : 'px-6',
      ]"
    >
      <div @click="handleBrandClick" class="cursor-pointer hover:opacity-80 transition-opacity">
        <img
          :src="logoSrc"
          alt="AdMirra"
          :class="isCollapsed ? 'h-8 w-8 object-contain' : 'h-[31px] w-[144px] object-contain object-left'"
        />
      </div>
    </div>

    <button
      @click="handleToggleCollapse"
      class="absolute left-full top-[38px] z-10 -ml-3 hidden h-6 w-6 -translate-y-1/2 items-center justify-center rounded-full bg-[#f5f7f9] transition-colors active:bg-[#5187ff] dark:bg-[#2C2F3D] min-[1920px]:flex"
    >
      <ChevronDownIcon
        :class="[
          'h-3 w-3 text-[#696969]/75 transition-transform duration-500 active:text-white dark:text-gray-400 dark:active:text-white',
          isCollapsed ? 'rotate-90' : '-rotate-90',
        ]"
      />
    </button>

    <!-- Main navigation -->
    <div class="flex-1 overflow-y-auto scrollbar-hide py-[15px]">
      <nav class="px-[11px] space-y-[10px]">
        <div v-for="item in menuItems" :key="item.name" class="relative">

          <!-- Item with submenu -->
          <template v-if="item.children">
            <div class="relative">
              <!-- Active left indicator -->
              <div
                v-if="isSubmenuActive(item)"
                class="absolute left-0 top-[7px] bottom-[7px] w-[3px] rounded-full bg-[#2563eb] dark:bg-[#4A7AFF]"
              />
              <button
                @click="toggleSubmenu(item.submenuKey)"
                :class="[
                  'group w-full flex items-center min-h-[46px] rounded-xl transition-all duration-500 text-left',
                  isSubmenuActive(item)
                    ? 'bg-[#ecf3fe] dark:bg-white/10'
                    : 'hover:bg-[#ecf3fe]/60 dark:hover:bg-white/5',
                ]"
              >
                <!-- Icon area: 49px wide -->
                <span class="w-[49px] flex-shrink-0 flex items-center justify-center">
                  <component
                    :is="item.icon"
                    class="w-5 h-5 transition-colors duration-500"
                    :class="isSubmenuActive(item) ? 'text-[#2563eb] dark:text-[#4A7AFF]' : 'text-[#696969]/75 group-hover:text-[#2563eb] dark:text-gray-400 dark:group-hover:text-[#4A7AFF]'"
                  />
                </span>
                <template v-if="!isCollapsed">
                  <span
                    class="flex-1 text-[14px] font-semibold leading-none transition-colors duration-500"
                    :class="isSubmenuActive(item) ? 'text-[#2563eb] dark:text-[#4A7AFF]' : 'text-[#696969]/75 group-hover:text-[#2563eb] dark:text-gray-400 dark:group-hover:text-[#4A7AFF]'"
                  >{{ item.name }}</span>
                  <!-- Arrow -->
                  <span
                    :class="[
                      'mr-[18px] ml-[10px] w-6 h-6 flex items-center justify-center rounded-full flex-shrink-0 transition-all duration-500',
                      isSubmenuActive(item) ? 'bg-white dark:bg-white/10' : 'bg-[#f5f7f9] dark:bg-white/5',
                    ]"
                  >
                    <ChevronDownIcon
                      class="w-3 h-3 transition-transform duration-500"
                      :class="[
                        isSubmenuActive(item) ? 'text-[#2563eb] dark:text-[#4A7AFF]' : 'text-[#696969]/75 dark:text-gray-400',
                        isSubmenuOpenForKey(item.submenuKey) ? 'rotate-180' : '',
                      ]"
                    />
                  </span>
                </template>
              </button>
            </div>

            <!-- Submenu -->
            <div
              :class="[
                'grid transition-[grid-template-rows,opacity,padding-top] duration-300 ease-out',
                !isCollapsed && isSubmenuOpenForKey(item.submenuKey) ? 'grid-rows-[1fr] opacity-100 pt-[10px]' : 'grid-rows-[0fr] opacity-0 pt-0',
              ]"
            >
              <div class="min-h-0 overflow-hidden pl-[33px] flex flex-col gap-[10px]">
                <div
                  v-for="child in item.children"
                  :key="child.path"
                  class="relative before:content-[''] before:absolute before:left-[-15px] before:bottom-1/2 before:w-[10px] before:h-[120px] before:border-l before:border-b before:border-[#e7e7e7] before:dark:border-white/20 before:rounded-bl-[10px]"
                >
                  <button
                    @click="handleLinkClick(child.path)"
                    :class="[
                      'inline-flex items-center min-h-[33px] px-[12px] py-[7px] rounded-xl text-left transition-all duration-500',
                      isActive(child.path)
                        ? 'bg-[#ecf3fe] text-[#2563eb] dark:bg-white/10 dark:text-[#4A7AFF]'
                        : 'text-[#696969]/75 hover:bg-[#ecf3fe] hover:text-[#2563eb] dark:text-gray-400 dark:hover:bg-white/5 dark:hover:text-[#4A7AFF]',
                    ]"
                  >
                    <span class="text-[12px] font-medium leading-none">{{ child.name }}</span>
                  </button>
                </div>
              </div>
            </div>
          </template>

          <!-- Regular item -->
          <template v-else>
            <div class="relative">
              <div
                v-if="isActive(item.path)"
                class="absolute left-0 top-[7px] bottom-[7px] w-[3px] rounded-full bg-[#2563eb] dark:bg-[#4A7AFF]"
              />
              <button
                @click="handleLinkClick(item.path)"
                :class="[
                  'group w-full flex items-center min-h-[46px] rounded-xl transition-all duration-500 text-left',
                  isActive(item.path)
                    ? 'bg-[#ecf3fe] dark:bg-white/10'
                    : 'hover:bg-[#ecf3fe]/60 dark:hover:bg-white/5',
                ]"
              >
                <span class="w-[49px] flex-shrink-0 flex items-center justify-center">
                  <component
                    :is="item.icon"
                    class="w-5 h-5 transition-colors duration-500"
                    :class="isActive(item.path) ? 'text-[#2563eb] dark:text-[#4A7AFF]' : 'text-[#696969]/75 group-hover:text-[#2563eb] dark:text-gray-400 dark:group-hover:text-[#4A7AFF]'"
                  />
                </span>
                <span
                  v-if="!isCollapsed"
                  class="flex-1 text-[14px] font-semibold leading-none transition-colors duration-500"
                  :class="isActive(item.path) ? 'text-[#2563eb] dark:text-[#4A7AFF]' : 'text-[#696969]/75 group-hover:text-[#2563eb] dark:text-gray-400 dark:group-hover:text-[#4A7AFF]'"
                >{{ item.name }}</span>
              </button>
            </div>
          </template>

          <!-- Collapsed tooltip -->
          <div
            v-if="isCollapsed"
            class="absolute left-[72px] ml-2 top-0 px-3 py-2 bg-gray-900 dark:bg-[#1a1a2e] text-white text-xs rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50 hidden"
          >{{ item.name }}</div>

        </div>
      </nav>
    </div>

    <!-- Bottom: separator + support + logout -->
    <div class="flex-shrink-0 pb-4">
      <hr class="mx-[11px] border-black/5 dark:border-white/10 my-2" />
      <nav class="px-[11px] space-y-[10px]">
        <div v-for="link in bottomLinks" :key="link.name">
          <div class="relative">
            <div
              v-if="link.path && isActive(link.path)"
              class="absolute left-0 top-[7px] bottom-[7px] w-[3px] rounded-full bg-[#2563eb] dark:bg-[#4A7AFF]"
            />
            <button
              @click="link.action ? link.action() : handleLinkClick(link.path)"
              :class="[
                'group w-full flex items-center min-h-[46px] rounded-xl transition-all duration-500 text-left',
                link.path && isActive(link.path)
                  ? 'bg-[#ecf3fe] dark:bg-white/10'
                  : 'hover:bg-[#ecf3fe]/60 dark:hover:bg-white/5',
              ]"
            >
              <span class="w-[49px] flex-shrink-0 flex items-center justify-center">
                <component
                  :is="link.icon"
                class="w-5 h-5 transition-colors duration-500"
                  :class="link.path && isActive(link.path) ? 'text-[#2563eb] dark:text-[#4A7AFF]' : 'text-[#696969]/75 group-hover:text-[#2563eb] dark:text-gray-400 dark:group-hover:text-[#4A7AFF]'"
                />
              </span>
              <span
                v-if="!isCollapsed"
                class="flex-1 text-[14px] font-semibold leading-none transition-colors duration-500"
                :class="link.path && isActive(link.path) ? 'text-[#2563eb] dark:text-[#4A7AFF]' : 'text-[#696969]/75 group-hover:text-[#2563eb] dark:text-gray-400 dark:group-hover:text-[#4A7AFF]'"
              >{{ link.name }}</span>
            </button>
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
  ComputerDesktopIcon,
  Squares2X2Icon,
  ClockIcon,
  Cog6ToothIcon,
  UserGroupIcon,
  RectangleStackIcon,
  CreditCardIcon,
} from '@heroicons/vue/24/outline'
import { useSidebar } from '../composables/useSidebar'
import { useAuth } from '../composables/useAuth'
import { useTheme } from '../composables/useTheme'
import ConfirmModal from './ConfirmModal.vue'

const { isCollapsed, toggleCollapse, isMobileViewport, isMobileMenuOpen, closeMobileMenu, toggleMobileMenu } = useSidebar()
const { isDarkMode } = useTheme()
const { forceLogout } = useAuth()

const route = useRoute()
const router = useRouter()
const isDashboardSubmenuOpen = ref(false)
const showLogoutModal = ref(false)

const logoSrc = computed(() => {
  if (isCollapsed.value) return '/admirra/img/favicon/favicon-96x96.png'
  return isDarkMode.value ? '/admirra/img/logo-white.png' : '/admirra/img/logo.png'
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
    { name: 'Проекты', path: '/project-card', icon: RectangleStackIcon },
    { name: 'Интеграции', path: '/integrations', icon: RectangleStackIcon },
  ]

  items.push(
    { name: 'Команда', path: '/team', icon: UserGroupIcon },
    { name: 'История', path: '/history', icon: ClockIcon },
    { name: 'Тарифы', path: '/tariffs', icon: CreditCardIcon },
    { name: 'Настройки', path: '/settings', icon: Cog6ToothIcon },
  )

  return items
})

const bottomLinks = computed(() => [
  { name: 'Поддержка', path: '/contact', icon: ComputerDesktopIcon },
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
  if (isMobileViewport.value) {
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
