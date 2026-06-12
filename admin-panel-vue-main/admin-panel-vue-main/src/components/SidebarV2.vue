<template>
  <!-- Mobile overlay -->
  <div
    v-if="isMobileMenuOpen"
    @click="closeMobileMenu"
    class="fixed inset-0 bg-black/50 z-40 min-[1024px]:hidden"
  />

  <aside
    :class="[
      'fixed left-0 top-0 h-screen flex flex-col z-50 transition-all duration-300',
      'bg-white dark:bg-[#1C1F2E]',
      'border-r border-black/5 dark:border-white/[0.07] dark:shadow-[2px_0_20px_rgba(0,0,0,0.32)]',
      isCollapsed ? 'w-[5rem]' : 'w-[18.75rem]',
      isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full min-[1024px]:translate-x-0',
    ]"
  >
    <!-- Logo header — matches header__aside height (5.2778rem) -->
    <div
      :class="[
        'flex items-center justify-between flex-shrink-0 border-b border-black/5 dark:border-white/10',
        'h-[5.2778rem]',
        isCollapsed ? 'px-[0.9722rem]' : 'px-6',
      ]"
    >
      <div @click="handleBrandClick" class="cursor-pointer hover:opacity-80 transition-opacity">
        <img
          :src="logoSrc"
          alt="AdMirra"
          :class="isCollapsed ? 'h-8 w-8 object-contain' : 'h-[2.1528rem] w-[10rem] object-contain object-left'"
        />
      </div>
    </div>

    <button
      @click="handleToggleCollapse"
      class="absolute left-full top-[2.6389rem] z-10 -ml-3 hidden h-6 w-6 -translate-y-1/2 items-center justify-center rounded-full bg-[#f5f7f9] transition-colors active:bg-[#5187ff] dark:bg-[#252840] dark:shadow-[0_0_0_1px_rgba(255,255,255,0.10)] min-[1024px]:flex"
    >
      <ChevronDownIcon
        :class="[
          'h-3 w-3 text-[#696969]/75 transition-transform duration-500 active:text-white dark:text-white/72 dark:active:text-white',
          isCollapsed ? 'rotate-90' : '-rotate-90',
        ]"
      />
    </button>

    <!-- Main navigation -->
    <div class="flex-1 overflow-y-auto scrollbar-hide py-[1.0417rem]">
      <nav class="px-[0.7639rem] space-y-[0.1389rem]">
        <div v-for="item in menuItems" :key="item.name" class="relative">

          <!-- Section label -->
          <div
            v-if="item.sectionLabel && !isCollapsed"
            :class="['px-[0.9722rem] text-[0.8333rem] font-semibold tracking-wide text-[#999] dark:text-white/38', menuItems.indexOf(item) === 0 ? 'pb-[0.2083rem]' : 'pt-[0.9722rem] pb-[0.2083rem]']"
          >{{ item.sectionLabel }}</div>

          <!-- Item with submenu -->
          <template v-if="item.children">
            <div class="relative">
              <!-- Active left indicator -->
              <div
                v-if="isSubmenuActive(item)"
                class="absolute left-0 top-[0.4861rem] bottom-[0.4861rem] w-[0.2083rem] rounded-full bg-[#2563eb] dark:bg-[#4A7AFF]"
              />
              <button
                @click="toggleSubmenu(item.submenuKey)"
                :class="[
                  'group w-full flex items-center min-h-[3.1944rem] rounded-xl transition-all duration-500 text-left',
                  isSubmenuActive(item)
                    ? 'bg-[#ecf3fe] dark:bg-white/10'
                    : 'hover:bg-[#ecf3fe]/60 dark:hover:bg-white/5',
                ]"
              >
                <!-- Icon area: 3.4028rem wide -->
                <span class="w-[3.4028rem] flex-shrink-0 flex items-center justify-center">
                  <component
                    :is="item.icon"
                    class="w-5 h-5 transition-colors duration-500"
                    :class="isSubmenuActive(item) ? 'text-[#2563eb] dark:text-[#4A7AFF]' : 'text-[#696969]/75 group-hover:text-[#2563eb] dark:text-white/72 dark:group-hover:text-[#4A7AFF]'"
                  />
                </span>
                <template v-if="!isCollapsed">
                  <span
                    class="flex-1 text-[0.9722rem] font-bold leading-none transition-colors duration-500"
                    :class="isSubmenuActive(item) ? 'text-[#2563eb] dark:text-[#4A7AFF]' : 'text-[#696969]/75 group-hover:text-[#2563eb] dark:text-white/72 dark:group-hover:text-[#4A7AFF]'"
                  >{{ item.name }}</span>
                  <!-- Arrow -->
                  <span
                    :class="[
                      'mr-[1.25rem] ml-[0.6944rem] w-6 h-6 flex items-center justify-center rounded-full flex-shrink-0 transition-all duration-500',
                      isSubmenuActive(item) ? 'bg-white dark:bg-white/10' : 'bg-[#f5f7f9] dark:bg-white/5',
                    ]"
                  >
                    <ChevronDownIcon
                      class="w-3 h-3 transition-transform duration-500"
                      :class="[
                        isSubmenuActive(item) ? 'text-[#2563eb] dark:text-[#4A7AFF]' : 'text-[#696969]/75 dark:text-white/72',
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
                !isCollapsed && isSubmenuOpenForKey(item.submenuKey) ? 'grid-rows-[1fr] opacity-100 pt-[0.6944rem]' : 'grid-rows-[0fr] opacity-0 pt-0',
              ]"
            >
              <div class="min-h-0 overflow-hidden pl-[2.2917rem] flex flex-col gap-[0.6944rem]">
                <div
                  v-for="child in item.children"
                  :key="child.path"
                  class="relative before:content-[''] before:absolute before:left-[-1.0417rem] before:bottom-1/2 before:w-[0.6944rem] before:h-[8.3333rem] before:border-l before:border-b before:border-[#e7e7e7] before:dark:border-white/20 before:rounded-bl-[0.6944rem]"
                >
                  <button
                    @click="handleLinkClick(child.path)"
                    :class="[
                      'inline-flex items-center min-h-[2.2917rem] px-[0.8333rem] py-[0.4861rem] rounded-xl text-left transition-all duration-500',
                      isActive(child.path)
                        ? 'bg-[#ecf3fe] text-[#2563eb] dark:bg-white/10 dark:text-[#4A7AFF]'
                        : 'text-[#696969]/75 hover:bg-[#ecf3fe] hover:text-[#2563eb] dark:text-white/72 dark:hover:bg-white/5 dark:hover:text-[#4A7AFF]',
                    ]"
                  >
                    <span class="text-[0.8333rem] font-medium leading-none">{{ child.name }}</span>
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
                class="absolute left-0 top-[0.4861rem] bottom-[0.4861rem] w-[0.2083rem] rounded-full bg-[#2563eb] dark:bg-[#4A7AFF]"
              />
              <button
                @click="handleLinkClick(item.path)"
                :class="[
                  'group w-full flex items-center min-h-[3.1944rem] rounded-xl transition-all duration-500 text-left',
                  isActive(item.path)
                    ? 'bg-[#ecf3fe] dark:bg-white/10'
                    : 'hover:bg-[#ecf3fe]/60 dark:hover:bg-white/5',
                ]"
              >
                <span class="w-[3.4028rem] flex-shrink-0 flex items-center justify-center">
                  <component
                    :is="item.icon"
                    class="w-5 h-5 transition-colors duration-500"
                    :class="isActive(item.path) ? 'text-[#2563eb] dark:text-[#4A7AFF]' : 'text-[#696969]/75 group-hover:text-[#2563eb] dark:text-white/72 dark:group-hover:text-[#4A7AFF]'"
                  />
                </span>
                <span
                  v-if="!isCollapsed"
                  class="flex-1 text-[0.9722rem] font-bold leading-none transition-colors duration-500"
                  :class="isActive(item.path) ? 'text-[#2563eb] dark:text-[#4A7AFF]' : 'text-[#696969]/75 group-hover:text-[#2563eb] dark:text-white/72 dark:group-hover:text-[#4A7AFF]'"
                >{{ item.name }}</span>
              </button>
            </div>
          </template>

          <!-- Collapsed tooltip -->
          <div
            v-if="isCollapsed"
            class="absolute left-[5rem] ml-2 top-0 px-3 py-2 bg-gray-900 dark:bg-[#1a1a2e] text-white text-xs rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50 hidden"
          >{{ item.name }}</div>

        </div>
      </nav>
    </div>

    <!-- Bottom: separator + support + logout -->
    <div class="flex-shrink-0 pb-4">
      <hr class="mx-[0.7639rem] border-black/5 dark:border-white/10 my-2" />
      <nav class="px-[0.7639rem] space-y-[0.1389rem]">
        <div v-for="link in bottomLinks" :key="link.name">
          <div class="relative">
            <div
              v-if="link.path && isActive(link.path)"
              class="absolute left-0 top-[0.4861rem] bottom-[0.4861rem] w-[0.2083rem] rounded-full bg-[#2563eb] dark:bg-[#4A7AFF]"
            />
            <button
              @click="link.action ? link.action() : handleLinkClick(link.path)"
              :class="[
                'group w-full flex items-center min-h-[3.1944rem] rounded-xl transition-all duration-500 text-left',
                link.path && isActive(link.path)
                  ? 'bg-[#ecf3fe] dark:bg-white/10'
                  : 'hover:bg-[#ecf3fe]/60 dark:hover:bg-white/5',
              ]"
            >
              <span class="w-[3.4028rem] flex-shrink-0 flex items-center justify-center">
                <component
                  :is="link.icon"
                class="w-5 h-5 transition-colors duration-500"
                  :class="link.path && isActive(link.path) ? 'text-[#2563eb] dark:text-[#4A7AFF]' : 'text-[#696969]/75 group-hover:text-[#2563eb] dark:text-white/72 dark:group-hover:text-[#4A7AFF]'"
                />
              </span>
              <span
                v-if="!isCollapsed"
                class="flex-1 text-[0.9722rem] font-bold leading-none transition-colors duration-500"
                :class="link.path && isActive(link.path) ? 'text-[#2563eb] dark:text-[#4A7AFF]' : 'text-[#696969]/75 group-hover:text-[#2563eb] dark:text-white/72 dark:group-hover:text-[#4A7AFF]'"
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
  SparklesIcon,
  LightBulbIcon,
  LinkIcon,
} from '@heroicons/vue/24/outline'
import { useSidebar } from '../composables/useSidebar'
import { useAuth } from '../composables/useAuth'
import { useTheme } from '../composables/useTheme'
import ConfirmModal from './ConfirmModal.vue'

const { isCollapsed, toggleCollapse, isMobileViewport, isMobileMenuOpen, closeMobileMenu, toggleMobileMenu } = useSidebar()
const { isDarkMode } = useTheme()
const { logout } = useAuth()

const route = useRoute()
const router = useRouter()
const isAISubmenuOpen = ref(false)
const showLogoutModal = ref(false)

const logoSrc = computed(() => {
  if (isCollapsed.value) return '/admirra/img/favicon/favicon-96x96.png'
  return isDarkMode.value ? '/admirra/img/logo-white.png' : '/admirra/img/logo.png'
})

const menuItems = computed(() => [
  { name: 'Проекты', path: '/project-card', icon: RectangleStackIcon, sectionLabel: 'Работа' },
  { name: 'Аналитика', path: '/dashboard/general-3', icon: Squares2X2Icon },
  {
    name: 'AI',
    icon: SparklesIcon,
    submenuKey: 'ai',
    children: [
      { name: 'Ассистент', path: '/ai-analysis' },
      { name: 'Аудит', path: '/ai-audit' },
      { name: 'Отчёты', path: '/reports' },
    ],
  },
  { name: 'Интеграции', path: '/integrations', icon: LinkIcon, sectionLabel: 'Подключения' },
  { name: 'История', path: '/history', icon: ClockIcon, sectionLabel: 'Аккаунт' },
  { name: 'Команда', path: '/team', icon: UserGroupIcon },
  { name: 'Тарифы', path: '/settings', icon: Cog6ToothIcon },
])

const bottomLinks = computed(() => [
  { name: 'Что допилить?', path: '/contact', icon: LightBulbIcon },
  { name: 'Поддержка', path: '/support', icon: ComputerDesktopIcon },
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
  if (key === 'ai') return isAISubmenuOpen.value
  return false
}

const toggleSubmenu = (key) => {
  if (isCollapsed.value) {
    toggleCollapse()
    setTimeout(() => {
      if (key === 'ai') isAISubmenuOpen.value = true
    }, 100)
  } else {
    if (key === 'ai') isAISubmenuOpen.value = !isAISubmenuOpen.value
  }
}

watch(() => route?.path, (path) => {
  if (path?.startsWith('/ai-') || path === '/reports') {
    isAISubmenuOpen.value = true
  }
}, { immediate: true })

const handleLinkClick = (path) => {
  if (path) router.push(path)
  closeMobileMenu()
}

const handleToggleCollapse = () => {
  toggleCollapse()
  if (isCollapsed.value) {
    isAISubmenuOpen.value = false
  }
}

const handleBrandClick = () => {
  router.push('/project-card')
  if (isMobileViewport.value) closeMobileMenu()
}

function handleLogoutClick() {
  closeMobileMenu()
  showLogoutModal.value = true
}

const handleLogout = async () => {
  await logout()
  showLogoutModal.value = false
  router.push('/signin')
}
</script>
