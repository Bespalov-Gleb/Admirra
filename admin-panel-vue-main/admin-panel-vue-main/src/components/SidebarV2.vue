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
      isCollapsed ? 'w-20' : 'w-[280px]',
      'lg:translate-x-0',
      isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
    ]"
    
  >
    <!-- Брендинг -->
    <div class="flex items-center justify-between p-6 border-b border-gray-700">
      <div v-if="!isCollapsed" @click="handleBrandClick" class="flex items-center gap-2 cursor-pointer hover:opacity-80 transition-opacity">
        <img :src="logoFull" alt="Logo" class="h-10 w-auto" />
      </div>
      <div v-else @click="handleBrandClick" class="cursor-pointer hover:opacity-80 transition-opacity mx-auto">
        <img :src="logoFav" alt="Logo" class="h-10 w-10" />
      </div>
    </div>

    <!-- Навигация -->
    <nav class="py-4">
      <!-- Дашборд с выпадающим меню -->
      <div class="relative group">
        <button
          @click="toggleDashboard"
          :class="[
            'relative w-full flex items-center gap-3 px-6 py-3 text-left hover:bg-gray-700 transition-colors',
            isCollapsed && 'justify-center'
          ]"
        >
          <!-- Индикатор активного состояния для родителя, когда активен дочерний элемент -->
          <div
            v-if="isActive('/dashboard/general') || isActive('/dashboard/general-2') || isActive('/dashboard/general-3')"
            class="absolute left-0 top-0 h-full w-1.5 rounded-r-md bg-white"
          ></div>
          <Squares2X2Icon class="w-5 h-5 flex-shrink-0" />
          <span v-if="!isCollapsed" class="flex-1">Дашборд</span>
          <ChevronDownIcon
            v-if="!isCollapsed"
            :class="[
              'w-4 h-4 transition-transform',
              isDashboardOpen && 'rotate-180'
            ]"
          />
        </button>
        <!-- Tooltip для свернутого меню -->
        <div
          v-if="isCollapsed"
          class="absolute left-full ml-2 top-1/2 -translate-y-1/2 px-3 py-2 bg-gray-900 text-white text-sm rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50"
        >
          Дашборд
          <div class="absolute right-full top-1/2 -translate-y-1/2 w-0 h-0 border-t-4 border-b-4 border-r-4 border-transparent border-r-gray-900"></div>
        </div>
        
        <!-- Выпадающее меню -->
        <div
          v-if="!isCollapsed && isDashboardOpen"
        >
          <button
            @click="handleLinkClick('/dashboard/general')"
            :class="[
              'relative w-full flex items-center gap-3 px-3 py-3 pl-14 hover:bg-gray-700 transition-colors text-left',
              isActive('/dashboard/general') ? 'bg-gray-700' : ''
            ]"
          >
            <Bars3Icon class="w-5 h-5" />
            <span>Общая статистика v1</span>
          </button>
          <button
            @click="handleLinkClick('/dashboard/general-2')"
            :class="[
              'relative w-full flex items-center gap-3 px-3 py-3 pl-14 hover:bg-gray-700 transition-colors text-left',
              isActive('/dashboard/general-2') ? 'bg-gray-700' : ''
            ]"
          >
            <Bars3Icon class="w-5 h-5" />
            <span>Общая статистика v2</span>
          </button>
          <button
            @click="handleLinkClick('/dashboard/general-3')"
            :class="[
              'relative w-full flex items-center gap-3 px-3 py-3 pl-14 hover:bg-gray-700 transition-colors text-left',
              isActive('/dashboard/general-3') ? 'bg-gray-700' : ''
            ]"
          >
            <Bars3Icon class="w-5 h-5" />
            <span>Общая статистика v3</span>
          </button>
        </div>
      </div>

      <!-- Каналы -->
      <div class="relative group">
        <button
          @click="handleLinkClick('/channels')"
          :class="[
            'relative w-full flex items-center gap-3 px-6 py-3 hover:bg-gray-700 transition-colors text-left',
            isCollapsed && 'justify-center',
            isActive('/channels') ? 'bg-gray-700' : ''
          ]"
        >
          <!-- Индикатор активного состояния -->
          <div
            v-if="isActive('/channels')"
            class="absolute left-0 top-0 h-full w-1.5 rounded-r-md bg-white"
          ></div>
          <ShareIcon class="w-5 h-5 flex-shrink-0" />
          <span v-if="!isCollapsed">Каналы</span>
        </button>
        <!-- Tooltip для свернутого меню -->
        <div
          v-if="isCollapsed"
          class="absolute left-full ml-2 top-1/2 -translate-y-1/2 px-3 py-2 bg-gray-900 text-white text-sm rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50"
        >
          Каналы
          <div class="absolute right-full top-1/2 -translate-y-1/2 w-0 h-0 border-t-4 border-b-4 border-r-4 border-transparent border-r-gray-900"></div>
        </div>
      </div>

      <!-- Команда -->
      <div class="relative group">
        <button
          @click="handleLinkClick('/team')"
          :class="[
            'relative w-full flex items-center gap-3 px-6 py-3 hover:bg-gray-700 transition-colors text-left',
            isCollapsed && 'justify-center',
            isActive('/team') ? 'bg-gray-700' : ''
          ]"
        >
          <!-- Индикатор активного состояния -->
          <div
            v-if="isActive('/team')"
            class="absolute left-0 top-0 h-full w-1.5 rounded-r-md bg-white"
          ></div>
          <UserGroupIcon class="w-5 h-5 flex-shrink-0" />
          <span v-if="!isCollapsed">Команда</span>
        </button>
        <!-- Tooltip для свернутого меню -->
        <div
          v-if="isCollapsed"
          class="absolute left-full ml-2 top-1/2 -translate-y-1/2 px-3 py-2 bg-gray-900 text-white text-sm rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50"
        >
          Команда
          <div class="absolute right-full top-1/2 -translate-y-1/2 w-0 h-0 border-t-4 border-b-4 border-r-4 border-transparent border-r-gray-900"></div>
        </div>
      </div>

      <!-- История -->
      <div class="relative group">
        <button
          @click="handleLinkClick('/history')"
          :class="[
            'relative w-full flex items-center gap-3 px-6 py-3 hover:bg-gray-700 transition-colors text-left',
            isCollapsed && 'justify-center',
            isActive('/history') ? 'bg-gray-700' : ''
          ]"
        >
          <!-- Индикатор активного состояния -->
          <div
            v-if="isActive('/history')"
            class="absolute left-0 top-0 h-full w-1.5 rounded-r-md bg-white"
          ></div>
          <ClockIcon class="w-5 h-5 flex-shrink-0" />
          <span v-if="!isCollapsed">История</span>
        </button>
        <!-- Tooltip для свернутого меню -->
        <div
          v-if="isCollapsed"
          class="absolute left-full ml-2 top-1/2 -translate-y-1/2 px-3 py-2 bg-gray-900 text-white text-sm rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50"
        >
          История
          <div class="absolute right-full top-1/2 -translate-y-1/2 w-0 h-0 border-t-4 border-b-4 border-r-4 border-transparent border-r-gray-900"></div>
        </div>
      </div>

      <!-- Продукты -->
      <div class="relative group">
        <button
          @click="handleLinkClick('/products')"
          :class="[
            'relative w-full flex items-center gap-3 px-6 py-3 hover:bg-gray-700 transition-colors text-left',
            isCollapsed && 'justify-center',
            isActive('/products') ? 'bg-gray-700' : ''
          ]"
        >
          <!-- Индикатор активного состояния -->
          <div
            v-if="isActive('/products')"
            class="absolute left-0 top-0 h-full w-1.5 rounded-r-md bg-white"
          ></div>
          <FolderIcon class="w-5 h-5 flex-shrink-0" />
          <span v-if="!isCollapsed">Продукты</span>
        </button>
        <!-- Tooltip для свернутого меню -->
        <div
          v-if="isCollapsed"
          class="absolute left-full ml-2 top-1/2 -translate-y-1/2 px-3 py-2 bg-gray-900 text-white text-sm rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50"
        >
          Продукты
          <div class="absolute right-full top-1/2 -translate-y-1/2 w-0 h-0 border-t-4 border-b-4 border-r-4 border-transparent border-r-gray-900"></div>
        </div>
      </div>

      <!-- Проекты -->
      <div class="relative group">
        <button
          @click="handleLinkClick('/projects')"
          :class="[
            'relative w-full flex items-center gap-3 px-6 py-3 hover:bg-gray-700 transition-colors text-left',
            isCollapsed && 'justify-center',
            isActive('/projects') ? 'bg-gray-700' : ''
          ]"
        >
          <!-- Индикатор активного состояния -->
          <div
            v-if="isActive('/projects')"
            class="absolute left-0 top-0 h-full w-1.5 rounded-r-md bg-white"
          ></div>
          <BriefcaseIcon class="w-5 h-5 flex-shrink-0" />
          <span v-if="!isCollapsed">Проекты</span>
        </button>
        <!-- Tooltip для свернутого меню -->
        <div
          v-if="isCollapsed"
          class="absolute left-full ml-2 top-1/2 -translate-y-1/2 px-3 py-2 bg-gray-900 text-white text-sm rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50"
        >
          Проекты
          <div class="absolute right-full top-1/2 -translate-y-1/2 w-0 h-0 border-t-4 border-b-4 border-r-4 border-transparent border-r-gray-900"></div>
        </div>
      </div>
    </nav>

    <!-- Разделитель -->
    <div class="border-t border-gray-700 my-4"></div>

    <!-- Настройки -->
    <nav class="py-4">
      <div class="relative group">
        <button
          @click="handleLinkClick('/settings')"
          :class="[
            'relative w-full flex items-center gap-3 px-6 py-3 hover:bg-gray-700 transition-colors text-left',
            isCollapsed && 'justify-center',
            isActive('/settings') ? 'bg-gray-700' : ''
          ]"
        >
          <!-- Индикатор активного состояния -->
          <div
            v-if="isActive('/settings')"
            class="absolute left-0 top-0 h-full w-1.5 rounded-r-md bg-white"
          ></div>
          <Cog6ToothIcon class="w-5 h-5 flex-shrink-0" />
          <span v-if="!isCollapsed">Настройки</span>
        </button>
        <!-- Tooltip для свернутого меню -->
        <div
          v-if="isCollapsed"
          class="absolute left-full ml-2 top-1/2 -translate-y-1/2 px-3 py-2 bg-gray-900 text-white text-sm rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50"
        >
          Настройки
          <div class="absolute right-full top-1/2 -translate-y-1/2 w-0 h-0 border-t-4 border-b-4 border-r-4 border-transparent border-r-gray-900"></div>
        </div>
      </div>
    </nav>

    <!-- Нижние ссылки -->
    <div class="absolute bottom-0 left-0 right-0 pb-10">
      <nav>
        <div class="relative group">
          <router-link
            to="/help"
            @click="closeMobileMenu"
            :class="[
              'relative flex items-center gap-3 px-6 py-3 hover:bg-gray-700 transition-colors',
              isCollapsed && 'justify-center',
              isActive('/help') && 'bg-gray-700'
            ]"
          >
            <span v-if="!isCollapsed">Помощь</span>
          </router-link>
          <!-- Tooltip для свернутого меню -->
          <div
            v-if="isCollapsed"
            class="absolute left-full ml-2 top-1/2 -translate-y-1/2 px-3 py-2 bg-gray-900 text-white text-sm rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50"
          >
            Помощь
            <div class="absolute right-full top-1/2 -translate-y-1/2 w-0 h-0 border-t-4 border-b-4 border-r-4 border-transparent border-r-gray-900"></div>
          </div>
        </div>
        <div class="relative group">
          <router-link
            to="/contact"
            @click="closeMobileMenu"
            :class="[
              'relative flex items-center gap-3 px-6 py-3 hover:bg-gray-700 transition-colors',
              isCollapsed && 'justify-center',
              isActive('/contact') && 'bg-gray-700'
            ]"
          >
            <span v-if="!isCollapsed">Связать</span>
          </router-link>
          <!-- Tooltip для свернутого меню -->
          <div
            v-if="isCollapsed"
            class="absolute left-full ml-2 top-1/2 -translate-y-1/2 px-3 py-2 bg-gray-900 text-white text-sm rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50"
          >
            Связать
            <div class="absolute right-full top-1/2 -translate-y-1/2 w-0 h-0 border-t-4 border-b-4 border-r-4 border-transparent border-r-gray-900"></div>
          </div>
        </div>
        <div class="relative group">
          <button
            @click="handleLogoutClick"
            :class="[
              'relative flex items-center gap-3 w-full px-6 py-3 hover:bg-gray-700 transition-colors',
              isCollapsed && 'justify-center'
            ]"
          >
            <ArrowRightOnRectangleIcon class="w-5 h-5 flex-shrink-0" />
            <span v-if="!isCollapsed">Выход</span>
          </button>
          <!-- Tooltip для свернутого меню -->
          <div
            v-if="isCollapsed"
            class="absolute left-full ml-2 top-1/2 -translate-y-1/2 px-3 py-2 bg-gray-900 text-white text-sm rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50"
          >
            Выход
            <div class="absolute right-full top-1/2 -translate-y-1/2 w-0 h-0 border-t-4 border-b-4 border-r-4 border-transparent border-r-gray-900"></div>
          </div>
        </div>
      </nav>
    </div>

    <!-- Кнопка сворачивания -->
    <button
      @click="handleToggleCollapse"
      class="hidden lg:flex absolute right-0 bottom-24 translate-x-1/2 w-8 h-[70px] rounded-full items-center justify-center hover:bg-gray-700 transition-colors z-10 main-bg-color"
    >
      <ChevronLeftIcon
        :class="[
          'w-4 h-4 transition-transform',
          isCollapsed && 'rotate-180'
        ]"
      />
    </button>
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
  FunnelIcon,
  ShareIcon,
  UserGroupIcon,
  ClockIcon,
  FolderIcon,
  BriefcaseIcon,
  Cog6ToothIcon,
  ArrowRightOnRectangleIcon,
  ChevronDownIcon,
  ChevronLeftIcon
} from '@heroicons/vue/24/outline'
import { useSidebar } from '../composables/useSidebar'
import { useAuth } from '../composables/useAuth'
import ConfirmModal from './ConfirmModal.vue'
import logoFull from '../assets/imgs/logo/AdMirra.png'
import logoFav from '../assets/imgs/logo/Fav.png'

const { isCollapsed, toggleCollapse, isMobileMenuOpen, closeMobileMenu, toggleMobileMenu } = useSidebar()
const { removeToken } = useAuth()
const route = useRoute()
const router = useRouter()
const isDashboardOpen = ref(false)
const showLogoutModal = ref(false)

// Закрывать мобильное меню при клике на ссылку
const handleLinkClick = (path) => {
  if (path) {
    router.push(path)
  }
  closeMobileMenu()
}

// Автоматически открывать выпадающее меню, если текущий маршрут в дашборде
watch(() => route?.path, (path) => {
  if (path && path.startsWith('/dashboard')) {
    isDashboardOpen.value = true
  }
}, { immediate: true })

// Также открывать меню для старого маршрута /projects
watch(() => route?.path, (path) => {
  if (path === '/projects') {
    isDashboardOpen.value = true
  }
}, { immediate: true })

// Вычисляемое свойство для проверки активного маршрута
const isActive = (path) => {
  if (!route?.path) return false
  if (path === '/dashboard/projects') {
    return route.path === '/dashboard/projects' || route.path === '/projects'
  }
  return route.path === path
}

const handleToggleCollapse = () => {
  toggleCollapse()
  if (isCollapsed.value) {
    isDashboardOpen.value = false
  }
}

const toggleDashboard = () => {
  // Если меню свернуто, разворачиваем его и открываем выпадающее меню
  if (isCollapsed.value) {
    toggleCollapse()
    // Используем nextTick, чтобы дождаться разворачивания меню
    setTimeout(() => {
      isDashboardOpen.value = true
    }, 100)
  } else {
    // Если меню развернуто, просто переключаем выпадающее меню
    isDashboardOpen.value = !isDashboardOpen.value
  }
}

const handleLogoutClick = () => {
  closeMobileMenu()
  showLogoutModal.value = true
}

const handleLogout = () => {
  removeToken()
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

