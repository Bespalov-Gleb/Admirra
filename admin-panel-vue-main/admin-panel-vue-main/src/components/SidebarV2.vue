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

    <!-- Основная навигация -->
    <div class="shrink min-h-0 overflow-y-auto scrollbar-hide py-3">
      <nav class="px-3 space-y-1.5">
        <div v-for="item in menuItems" :key="item.name" class="relative group">

          <!-- Пункт с подменю — обёртка только вокруг кнопки для позиционирования полоски -->
          <div v-if="item.children" class="relative">
            <div
              v-if="isSubmenuActive(item)"
              class="absolute left-0 top-1 bottom-1 w-[3px] rounded-full bg-[#2563EB] z-10"
            ></div>
            <button
              @click="toggleSubmenu(item.submenuKey)"
              :class="[
                'w-full flex items-center gap-3 pl-6 pr-4 py-3.5 text-left rounded-[10px] transition-all',
                isCollapsed ? 'justify-center' : '',
                isSubmenuActive(item) ? 'bg-[#EBF3FF]' : 'hover:bg-gray-100/70'
              ]"
            >
              <component
                :is="item.icon"
                class="w-6 h-6 flex-shrink-0"
                :class="isSubmenuActive(item) ? 'text-[#2563EB]' : 'text-[#696969]/[0.76]'"
              />
              <template v-if="!isCollapsed">
                <span
                  class="flex-1 text-[12px] font-semibold"
                  :class="isSubmenuActive(item) ? 'text-[#2563EB]' : 'text-[#696969]/[0.76]'"
                >{{ item.name }}</span>
                <ChevronDownIcon
                  class="w-3.5 h-3.5 transition-transform"
                  :class="[
                    isSubmenuActive(item) ? 'text-[#2563EB]' : 'text-[#696969]/[0.76]',
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
              class="absolute left-0 top-1 bottom-1 w-[3px] rounded-full bg-[#2563EB] z-10"
            ></div>
            <button
              @click="handleLinkClick(item.path)"
              :class="[
                'w-full flex items-center gap-3 pl-6 pr-8 py-3.5 text-left rounded-[10px] transition-all',
                isCollapsed ? 'justify-center' : '',
                isActive(item.path) ? 'bg-[#EBF3FF]' : 'hover:bg-gray-100/70'
              ]"
            >
              <component
                :is="item.icon"
                class="w-6 h-6 flex-shrink-0"
                :class="isActive(item.path) ? 'text-[#2563EB]' : 'text-[#696969]/[0.76]'"
              />
              <span
                v-if="!isCollapsed"
                class="text-[12px] font-semibold"
                :class="isActive(item.path) ? 'text-[#2563EB]' : 'text-[#696969]/[0.76]'"
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
                class="absolute left-[36px] top-0 bottom-0 w-[1.5px] bg-gray-200"
              ></div>

              <!-- Закруглённая ветка L-образная (верх → середина + горизонталь) -->
              <div
                class="absolute left-[36px] w-[14px] border-l-[1.5px] border-b-[1.5px] border-gray-200 rounded-bl-[6px]"
                style="top: 0; height: calc(50% + 1px);"
              ></div>

              <button
                @click="handleLinkClick(child.path)"
                class="w-full flex items-center py-[9px] px-3 text-left rounded-[8px] transition-all"
                :class="isActive(child.path) ? 'bg-[#EBF3FF]' : 'hover:bg-gray-100/70'"
              >
                <span
                  class="text-[11px] font-semibold"
                  :class="isActive(child.path) ? 'text-[#2563EB]' : 'text-[#696969]/[0.76]'"
                >{{ child.name }}</span>
              </button>
            </div>
          </div>

        </div>
      </nav>
    </div>

    <!-- Средняя навигация: История, Настройки -->
    <div class="shrink-0">
      <nav class="px-3 space-y-1.5 pt-4 pb-2">
        <div v-for="link in middleLinks" :key="link.name" class="relative group">
          <button
            @click="link.action ? link.action() : handleLinkClick(link.path)"
            :class="[
              'w-full flex items-center gap-3 pl-6 pr-8 py-3.5 text-left rounded-[10px] transition-all',
              isCollapsed ? 'justify-center' : '',
              link.path && isActive(link.path) ? 'bg-[#EBF3FF]' : 'hover:bg-gray-100/70'
            ]"
          >
            <component
              :is="link.icon"
              class="w-6 h-6 flex-shrink-0"
              :class="link.path && isActive(link.path) ? 'text-[#2563EB]' : 'text-[#696969]/[0.76]'"
            />
            <span
              v-if="!isCollapsed"
              class="text-[12px] font-semibold"
              :class="link.path && isActive(link.path) ? 'text-[#2563EB]' : 'text-[#696969]/[0.76]'"
            >{{ link.name }}</span>
          </button>
          <div v-if="isCollapsed" class="absolute left-full ml-2 top-1/2 -translate-y-1/2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50">
            {{ link.name }}
            <div class="absolute right-full top-1/2 -translate-y-1/2 w-0 h-0 border-t-4 border-b-4 border-r-4 border-transparent border-r-gray-900"></div>
          </div>
        </div>
      </nav>
    </div>

    <!-- Распорка -->
    <div class="flex-1"></div>

    <!-- Нижняя навигация: Помощь, Тех. поддержка -->
    <div class="shrink-0">
      <nav class="px-3 space-y-1.5 py-2">
        <div v-for="link in bottomLinks" :key="link.name" class="relative group">
          <button
            @click="link.action ? link.action() : handleLinkClick(link.path)"
            :class="[
              'w-full flex items-center gap-3 pl-6 pr-8 py-3.5 text-left rounded-[10px] transition-all',
              isCollapsed ? 'justify-center' : '',
              link.path && isActive(link.path) ? 'bg-[#EBF3FF]' : 'hover:bg-gray-100/70'
            ]"
          >
            <component
              :is="link.icon"
              class="w-6 h-6 flex-shrink-0"
              :class="link.path && isActive(link.path) ? 'text-[#2563EB]' : 'text-[#696969]/[0.76]'"
            />
            <span
              v-if="!isCollapsed"
              class="text-[12px] font-semibold"
              :class="link.path && isActive(link.path) ? 'text-[#2563EB]' : 'text-[#696969]/[0.76]'"
            >{{ link.name }}</span>
          </button>
          <div v-if="isCollapsed" class="absolute left-full ml-2 top-1/2 -translate-y-1/2 px-3 py-2 bg-gray-900 text-white text-xs rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50">
            {{ link.name }}
            <div class="absolute right-full top-1/2 -translate-y-1/2 w-0 h-0 border-t-4 border-b-4 border-r-4 border-transparent border-r-gray-900"></div>
          </div>
        </div>
      </nav>
    </div>

    <!-- Промо-карточка -->
    <div v-if="!isCollapsed" class="px-3 pb-3 pt-1">
      <div class="rounded-[16px] relative overflow-hidden p-4" style="background-color: #24252E;">
        <!-- Синий тонирующий слой -->
        <div class="absolute inset-0" style="background: rgba(37,99,235,0.32);"></div>
        <!-- Паттерн точек -->
        <div
          class="absolute inset-0"
          style="background-image: radial-gradient(circle, rgba(255,255,255,0.13) 1px, transparent 1px); background-size: 16px 16px;"
        ></div>

        <!-- Контент поверх слоёв -->
        <div class="relative z-10">
          <!-- Иконка -->
          <div
            class="w-8 h-8 rounded-[8px] flex items-center justify-center mb-2.5"
            style="background: linear-gradient(135deg, rgba(77,178,255,0.30), rgba(116,195,255,0.30));"
          >
            <CpuChipIcon class="w-4 h-4 text-white" />
          </div>

          <h4 class="text-[13px] font-bold text-white leading-snug mb-1">Повысить до премиум</h4>
          <p class="text-[11px] text-white/60 leading-relaxed mb-3">Повысте ваш аккаунт и разблокируйте все функции</p>

          <router-link
            to="/settings"
            @click="closeMobileMenu"
            class="block w-full py-2 text-center text-[12px] font-semibold text-white rounded-[10px] transition-colors hover:opacity-90"
            style="background-color: #2563EB;"
          >
            Смотреть тарифы
          </router-link>
        </div>
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
  CpuChipIcon,
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
    ]
  },
  { name: 'AI Отчет', path: '/ai-analysis', icon: SparklesIcon },
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

const middleLinks = computed(() => [
  { name: 'История', path: '/history', icon: ClockIcon },
  { name: 'Настройки', path: '/settings', icon: Cog6ToothIcon },
])

const bottomLinks = computed(() => [
  { name: 'Помощь', path: '/help', icon: QuestionMarkCircleIcon },
  { name: 'Тех. поддержка', path: '/contact', icon: ComputerDesktopIcon },
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
  if (path?.startsWith('/dashboard')) {
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
