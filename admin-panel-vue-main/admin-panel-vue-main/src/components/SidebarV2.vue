<template>
  <!-- Overlay для мобильных -->
  <div
    v-if="isMobileMenuOpen"
    @click="closeMobileMenu"
    class="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
  ></div>

  <aside
    :class="[
      'fixed left-0 top-0 h-screen text-white transition-all duration-300 z-50 main-bg-color border-r border-gray-800 flex flex-col',
      isCollapsed ? 'w-20' : 'w-[280px]',
      'lg:translate-x-0',
      isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
    ]"
  >
    <!-- Брендинг -->
    <div class="flex items-center h-20 px-6 border-b border-gray-800">
      <div v-if="!isCollapsed" class="flex items-center gap-3">
        <div class="w-8 h-8 rounded-lg bg-white flex items-center justify-center">
          <span class="text-gray-900 font-bold text-xl">T</span>
        </div>
        <span class="text-lg font-bold tracking-tight">TRAFFIC AGENT</span>
      </div>
      <div v-else class="w-full flex justify-center">
        <div class="w-10 h-10 rounded-lg bg-white flex items-center justify-center">
          <span class="text-gray-900 font-bold text-xl">T</span>
        </div>
      </div>
    </div>

    <!-- Навигация -->
    <div class="flex-1 overflow-y-auto py-6 px-3 custom-scrollbar">
      <div v-for="(group, gIdx) in navigationGroups" :key="gIdx" class="mb-8">
        <p v-if="!isCollapsed" class="px-4 mb-3 text-[10px] font-bold text-gray-500 uppercase tracking-widest">
          {{ group.title }}
        </p>
        
        <div class="space-y-1">
          <template v-for="item in group.items" :key="item.name">
            <!-- Обычная ссылка -->
            <router-link
              v-if="!item.children"
              :to="item.path"
              @click="closeMobileMenu"
              class="flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group relative"
              :class="[
                isActive(item.path) 
                  ? 'bg-white/10 text-white font-medium shadow-sm' 
                  : 'text-gray-400 hover:bg-white/5 hover:text-white'
              ]"
            >
              <component :is="item.icon" class="w-5 h-5 flex-shrink-0" />
              <span v-if="!isCollapsed" class="flex-1">{{ item.name }}</span>
              <div v-if="isActive(item.path)" class="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-white rounded-r-full"></div>
            </router-link>

            <!-- Группа с подменю (Дашборд) -->
            <div v-else>
              <div 
                class="flex items-center w-full rounded-xl transition-all duration-200 text-gray-400 hover:bg-white/5 hover:text-white group relative"
                :class="[isGroupActive(item) && 'text-white bg-white/5']"
              >
                <router-link
                  :to="item.children[0].path"
                  class="flex-1 flex items-center gap-3 px-4 py-3"
                  @click="closeMobileMenu"
                >
                  <component :is="item.icon" class="w-5 h-5 flex-shrink-0" />
                  <span v-if="!isCollapsed" class="flex-1">{{ item.name }}</span>
                </router-link>
                <button
                  v-if="!isCollapsed"
                  @click.stop="toggleGroup(item.name)"
                  class="p-3 hover:text-white transition-colors"
                >
                  <ChevronDownIcon
                    class="w-4 h-4 transition-transform duration-200"
                    :class="[openGroups.includes(item.name) && 'rotate-180']"
                  />
                </button>
              </div>
              
              <div v-if="!isCollapsed && openGroups.includes(item.name)" class="mt-1 space-y-1 ml-4 border-l border-gray-800">
                <router-link
                  v-for="subItem in item.children"
                  :key="subItem.path"
                  :to="subItem.path"
                  @click="closeMobileMenu"
                  class="flex items-center gap-3 px-8 py-2.5 rounded-xl transition-all duration-200"
                  :class="[
                    isActive(subItem.path)
                      ? 'text-white font-medium'
                      : 'text-gray-500 hover:text-white'
                  ]"
                >
                  <div class="w-1.5 h-1.5 rounded-full" :class="[isActive(subItem.path) ? 'bg-white' : 'bg-gray-700']"></div>
                  <span class="text-sm">{{ subItem.name }}</span>
                </router-link>
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>

    <!-- Футер сайдбара -->
    <div class="p-4 border-t border-gray-800 bg-black/20">
      <button
        @click="handleLogoutClick"
        class="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-red-400 hover:bg-red-400/10 transition-all duration-200"
        :class="[isCollapsed && 'justify-center']"
      >
        <ArrowRightOnRectangleIcon class="w-5 h-5 flex-shrink-0" />
        <span v-if="!isCollapsed" class="font-medium">Выйти</span>
      </button>
    </div>

    <!-- Кнопка сворачивания -->
    <button
      @click="toggleCollapse"
      class="hidden lg:flex absolute -right-4 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full items-center justify-center bg-gray-800 border border-gray-700 text-gray-400 hover:text-white hover:bg-gray-700 transition-all shadow-lg"
    >
      <ChevronLeftIcon :class="['w-4 h-4 transition-transform', isCollapsed && 'rotate-180']" />
    </button>
  </aside>

  <ConfirmModal
    v-model:is-open="showLogoutModal"
    title="Подтверждение выхода"
    message="Вы уверены, что хотите выйти из системы?"
    @confirm="handleLogout"
  />
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  Squares2X2Icon,
  Bars3Icon,
  ShareIcon,
  UserGroupIcon,
  ClockIcon,
  FolderIcon,
  BriefcaseIcon,
  Cog6ToothIcon,
  ArrowRightOnRectangleIcon,
  ChevronDownIcon,
  ChevronLeftIcon,
  QuestionMarkCircleIcon,
  EnvelopeIcon
} from '@heroicons/vue/24/outline'
import { useSidebar } from '../composables/useSidebar'
import { useAuth } from '../composables/useAuth'
import ConfirmModal from './ConfirmModal.vue'

const { isCollapsed, toggleCollapse, isMobileMenuOpen, closeMobileMenu } = useSidebar()
const { removeToken } = useAuth()
const route = useRoute()
const router = useRouter()

const showLogoutModal = ref(false)
const openGroups = ref(['Дашборд'])

const navigationGroups = [
  {
    title: 'Главное',
    items: [
      {
        name: 'Дашборд',
        icon: Squares2X2Icon,
        children: [
          { name: 'Общая статистика', path: '/dashboard/general' },
          { name: 'Второй вариант', path: '/dashboard/general-2' }
        ]
      },
      { name: 'Проекты', path: '/projects', icon: BriefcaseIcon },
      { name: 'Каналы', path: '/channels', icon: ShareIcon }
    ]
  },
  {
    title: 'Управление',
    items: [
      { name: 'Команда', path: '/team', icon: UserGroupIcon },
      { name: 'Продукты', path: '/products', icon: FolderIcon },
      { name: 'История', path: '/history', icon: ClockIcon }
    ]
  },
  {
    title: 'Система',
    items: [
      { name: 'Настройки', path: '/settings', icon: Cog6ToothIcon },
      { name: 'Помощь', path: '/help', icon: QuestionMarkCircleIcon },
      { name: 'Контакты', path: '/contact', icon: EnvelopeIcon }
    ]
  }
]

const isActive = (path) => route.path === path

const isGroupActive = (item) => {
  if (!item.children) return isActive(item.path)
  return item.children.some(child => isActive(child.path))
}

const toggleGroup = (name) => {
  const index = openGroups.value.indexOf(name)
  if (index === -1) openGroups.value.push(name)
  else openGroups.value.splice(index, 1)
}

watch(() => route.path, (newPath) => {
  navigationGroups.forEach(group => {
    group.items.forEach(item => {
      if (item.children && item.children.some(child => child.path === newPath)) {
        if (!openGroups.value.includes(item.name)) openGroups.value.push(item.name)
      }
    })
  })
}, { immediate: true })

const handleLogoutClick = () => {
  closeMobileMenu()
  showLogoutModal.value = true
}

const handleLogout = () => {
  console.log('Logging out from Sidebar...')
  removeToken()
  showLogoutModal.value = false
  router.push('/login')
}
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 10px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
</style>

