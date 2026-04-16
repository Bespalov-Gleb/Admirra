<template>
  <header class="bg-white dark:bg-[#2C2F3D] border-b border-gray-100 dark:border-white/10 px-4 sm:px-6 lg:px-8 py-3.5 z-30 font-[Inter]">
    <div class="flex items-center justify-between gap-4">
      <!-- Левая часть — Трафик агентство (по макету) -->
      <div class="flex items-center gap-3 flex-shrink-0">
        <button
          @click="toggleMobileMenu"
          class="lg:hidden p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-white/10 transition-colors text-gray-600 dark:text-gray-300"
          aria-label="Открыть меню"
        >
          <Bars3Icon class="w-6 h-6" />
        </button>
        
        <!-- Блок агентства: иконка + текст + dropdown -->
        <div class="relative" ref="projectMenuRef">
          <button 
            @click="toggleProjectMenu"
            class="flex items-center gap-3 px-4 py-2.5 rounded-xl bg-gray-50 dark:bg-white/10 hover:bg-gray-100 dark:hover:bg-white/15 transition-colors text-left"
          >
            <div class="w-10 h-10 rounded-lg bg-blue-100 dark:bg-blue-500/20 flex items-center justify-center flex-shrink-0">
              <ChartBarIcon class="w-5 h-5 text-blue-600 dark:text-[#4A7AFF]" />
            </div>
            <div>
              <p class="text-sm font-semibold text-gray-900 dark:text-white">{{ currentProjectName }}</p>
              <p class="text-xs text-gray-500 dark:text-gray-400">Отчёты агентства в одном месте</p>
            </div>
            <ChevronDownIcon class="w-4 h-4 text-gray-400 flex-shrink-0 ml-1" />
          </button>

          <div 
            v-if="isProjectMenuOpen"
            class="absolute top-full left-0 mt-2 w-64 bg-white dark:bg-[#2A2D3C] rounded-xl shadow-xl border border-gray-100 dark:border-white/10 py-2 z-50 text-gray-800 dark:text-gray-200"
          >
            <div class="px-3 py-2 border-b border-gray-100 dark:border-white/10 text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">
              Мои проекты
            </div>
            <div class="max-h-64 overflow-y-auto">
              <button
                @click="handleProjectSelect(null)"
                class="w-full text-left px-4 py-2.5 hover:bg-blue-50 dark:hover:bg-white/10 transition-colors flex items-center justify-between"
                :class="{'bg-blue-50/50 dark:bg-white/10 text-blue-600 dark:text-[#4A7AFF]': !currentProjectId}"
              >
                <span class="font-medium truncate">Все проекты</span>
                <CheckIcon v-if="!currentProjectId" class="w-4 h-4 text-blue-600 dark:text-[#4A7AFF]" />
              </button>
              <button
                v-for="project in projects"
                :key="project.id"
                @click="handleProjectSelect(project.id)"
                class="w-full text-left px-4 py-2.5 hover:bg-blue-50 dark:hover:bg-white/10 transition-colors flex items-center justify-between"
                :class="{'bg-blue-50/50 dark:bg-white/10 text-blue-600 dark:text-[#4A7AFF]': currentProjectId === project.id}"
              >
                <span class="font-medium truncate">{{ project.name }}</span>
                <CheckIcon v-if="currentProjectId === project.id" class="w-4 h-4 text-blue-600 dark:text-[#4A7AFF]" />
              </button>
            </div>
            <div class="p-2 border-t border-gray-100 dark:border-white/10">
              <router-link
                to="/projects/create"
                @click="isProjectMenuOpen = false"
                class="w-full flex items-center gap-2 px-3 py-2 text-sm text-blue-600 dark:text-[#4A7AFF] hover:bg-blue-50 dark:hover:bg-white/10 rounded-lg transition-colors"
              >
                <PlusIcon class="w-4 h-4" />
                Создать новый проект
              </router-link>
            </div>
          </div>
        </div>
      </div>

      <!-- Правая часть -->
      <div class="flex items-center gap-3 flex-shrink-0">
        <div class="hidden xl:flex items-center gap-3 px-4 py-2 rounded-xl bg-gray-50 dark:bg-white/10">
          <div class="text-xs text-gray-500 dark:text-gray-400">Ваш тариф:</div>
          <div class="text-sm font-semibold text-gray-900 dark:text-white">{{ subscription.planName }}</div>
          <div v-if="subscription.expiresAtLabel" class="text-xs text-gray-500 dark:text-gray-400">
            Действует до {{ subscription.expiresAtLabel }}
          </div>
          <button
            @click="() => router.push('/tariffs')"
            class="ml-2 px-3 py-1.5 rounded-lg border border-blue-200 text-blue-600 hover:bg-blue-50 dark:border-white/20 dark:text-[#4A7AFF] dark:hover:bg-white/10 transition-colors text-xs font-semibold"
          >
            Продлить
          </button>
        </div>

        <button
          @click="() => router.push('/contact')"
          class="hidden lg:flex items-center gap-2 px-4 py-2 bg-gray-50 dark:bg-white/10 rounded-xl hover:bg-gray-100 dark:hover:bg-white/15 transition-colors text-sm font-medium text-gray-700 dark:text-gray-300"
        >
          Предложить идею
        </button>

        <button
          @click="() => router.push('/projects/create')"
          class="flex items-center gap-2 px-4 py-2 bg-blue-600 dark:bg-[#4A7AFF] rounded-xl hover:bg-blue-700 dark:hover:bg-[#5A8BFF] transition-colors text-white text-sm font-medium"
        >
          <PlusIcon class="w-5 h-5" />
          Перейти на тариф Старт
        </button>

        <div class="relative">
          <button
            data-notifications-button
            @click="toggleNotifications"
            class="relative p-2.5 rounded-xl bg-gray-50 dark:bg-white/10 hover:bg-gray-100 dark:hover:bg-white/15 transition-colors"
            aria-label="Уведомления"
          >
            <BellIcon class="w-5 h-5 text-gray-600 dark:text-gray-400" />
            <span
              v-if="unreadCount > 0"
              class="absolute top-1 right-1 min-w-[18px] h-[18px] px-1 bg-green-500 text-white text-[10px] font-semibold rounded-md flex items-center justify-center"
            >
              {{ unreadCount }}
            </span>
          </button>
          <Teleport to="body">
            <div
              v-if="showNotifications"
              ref="notificationsRef"
              :style="getNotificationsStyle()"
              class="dropdown-menu fixed w-80 sm:w-96 bg-white dark:bg-[#2A2D3C] rounded-lg shadow-lg border border-gray-200 dark:border-white/10 z-50"
              @click.stop
            >
              <div class="p-4 border-b border-gray-200 dark:border-white/10 flex items-center justify-between">
                <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Уведомления</h3>
                <button
                  v-if="notifications.length > 0 && unreadCount > 0"
                  @click="markAllAsRead"
                  class="text-sm text-blue-600 hover:text-blue-700 font-medium"
                >
                  Отметить все как прочитанные
                </button>
              </div>

              <div class="max-h-96 overflow-y-auto">
                <div
                  v-if="notifications.length === 0"
                  class="p-8 text-center text-sm text-gray-500 dark:text-gray-400"
                >
                  Нет уведомлений
                </div>
                <div
                  v-for="notification in notifications"
                  :key="notification.id"
                  @click="markAsRead(notification.id)"
                  class="p-4 border-b border-gray-100 dark:border-white/10 hover:bg-gray-50 dark:hover:bg-white/5 transition-colors flex items-start gap-3 cursor-pointer"
                >
                  <div
                    v-if="!notification.read"
                    class="w-2 h-2 bg-blue-600 rounded-full mt-2 flex-shrink-0"
                  ></div>
                  <div v-else class="w-2 h-2 flex-shrink-0"></div>
                  <div class="flex-1 min-w-0">
                    <p class="text-sm font-medium text-gray-900 dark:text-gray-200">{{ notification.title }}</p>
                    <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">{{ notification.time }}</p>
                  </div>
                  <button
                    @click.stop="removeNotification(notification.id)"
                    class="text-gray-400 hover:text-gray-600 transition-colors flex-shrink-0"
                  >
                    <XMarkIcon class="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          </Teleport>
        </div>

        <!-- Профиль (по макету: аватар + имя + dropdown) -->
        <div class="relative">
          <button
            data-profile-button
            @click="toggleProfileMenu"
            class="flex items-center gap-3 px-3 py-2 rounded-xl bg-gray-50 dark:bg-white/10 hover:bg-gray-100 dark:hover:bg-white/15 transition-colors"
          >
            <div class="w-9 h-9 rounded-full bg-blue-100 dark:bg-blue-500/20 flex items-center justify-center overflow-hidden flex-shrink-0">
              <ProfileHeader class="w-5 h-5 text-blue-600 dark:text-[#4A7AFF]" />
            </div>
            <span class="text-sm font-medium text-gray-900 dark:text-white hidden sm:inline">{{ displayName }}</span>
            <ChevronDownIcon class="w-4 h-4 text-gray-400 flex-shrink-0" />
          </button>

          <!-- Выпадающее меню профиля -->
          <Teleport to="body">
            <div
              v-if="isProfileMenuOpen"
              ref="profileMenuRef"
              :style="getProfileMenuStyle()"
              class="dropdown-menu fixed w-72 bg-white dark:bg-[#2A2D3C] rounded-lg shadow-lg border border-gray-200 dark:border-white/10 py-2 z-50"
              @click.stop
            >
              <div class="px-4 py-3 border-b border-gray-200 dark:border-white/10">
                <p class="text-sm font-semibold text-gray-900 dark:text-white">{{ displayName }}</p>
                <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">{{ user?.email }}</p>
              </div>
              
              <!-- Переключатель темной темы -->
              <div class="flex items-center justify-between px-4 py-2 hover:bg-gray-100 dark:hover:bg-white/10 transition-colors">
                <div class="flex items-center gap-2">
                  <MoonIcon class="w-5 h-5 text-gray-600 dark:text-gray-400" />
                  <span class="text-sm text-gray-700 dark:text-gray-300">{{ isDarkMode ? 'Светлая тема' : 'Темная тема' }}</span>
                  <span class="px-1.5 py-0.5 bg-yellow-400 text-gray-900 text-[10px] font-medium rounded">Бета</span>
                </div>
                <button
                  @click="toggleTheme"
                  :class="[
                    'relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
                    isDarkMode ? 'bg-blue-600' : 'bg-gray-300'
                  ]"
                  role="switch"
                  :aria-checked="isDarkMode"
                >
                  <span
                    :class="[
                      'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
                      isDarkMode ? 'translate-x-4' : 'translate-x-0.5'
                    ]"
                  ></span>
                </button>
              </div>
              
              <router-link
                to="/profile"
                @click="closeProfileMenu"
                class="flex items-center gap-3 px-4 py-2 hover:bg-gray-100 dark:hover:bg-white/10 transition-colors text-sm text-gray-700 dark:text-gray-300"
              >
                <UserIcon class="w-5 h-5 text-gray-600 dark:text-gray-400" />
                <span>Профиль</span>
              </router-link>
              
              <router-link
                to="/settings"
                @click="closeProfileMenu"
                class="flex items-center gap-3 px-4 py-2 hover:bg-gray-100 dark:hover:bg-white/10 transition-colors text-sm text-gray-700 dark:text-gray-300"
              >
                <Cog6ToothIcon class="w-5 h-5 text-gray-600 dark:text-gray-400" />
                <span>Настройки</span>
              </router-link>
              
              <button
                @click="handleLogoutClick"
                class="w-full flex items-center gap-3 px-4 py-2 hover:bg-gray-100 transition-colors text-left text-sm text-red-600"
              >
                <ArrowRightOnRectangleIcon class="w-5 h-5" />
                <span>Выход</span>
              </button>
            </div>
          </Teleport>
        </div>

        <button
          @click="handleLogoutClick"
          class="px-4 py-2 rounded-xl border border-gray-200 bg-white text-gray-700 hover:bg-gray-50 dark:border-white/20 dark:bg-white/10 dark:text-gray-200 dark:hover:bg-white/15 transition-colors text-sm font-medium"
        >
          Выход
        </button>
      </div>
    </div>
  </header>

  <!-- Модалка подтверждения выхода -->
  <ConfirmModal
    v-model:is-open="showLogoutModal"
    title="Подтверждение выхода"
    message="Вы уверены, что хотите выйти из системы?"
    @confirm="handleLogout"
  />
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { Teleport } from 'vue'
import {
  UserIcon,
  Cog6ToothIcon,
  ArrowRightOnRectangleIcon,
  Bars3Icon,
  BellIcon,
  XMarkIcon,
  MoonIcon,
  ChevronDownIcon,
  CheckIcon,
  PlusIcon,
  ChartBarIcon
} from '@heroicons/vue/24/outline'
import ProfileHeader from '../assets/icons/profile-header.vue'
import ConfirmModal from './ConfirmModal.vue'
import { useSidebar } from '../composables/useSidebar'
import { useAuth } from '../composables/useAuth'
import { useTheme } from '../composables/useTheme'
import { useProjects } from '../composables/useProjects'
import api from '../api/axios'

const router = useRouter()
const { toggleMobileMenu } = useSidebar()
const { user, forceLogout } = useAuth()
// Initialize theme
const { isDarkMode, toggleTheme } = useTheme()
const { projects, currentProjectId, currentProjectName, fetchProjects, setCurrentProject } = useProjects()

// Project Menu State
const isProjectMenuOpen = ref(false)
const projectMenuRef = ref(null)

const toggleProjectMenu = () => {
    isProjectMenuOpen.value = !isProjectMenuOpen.value
}

const handleProjectSelect = (id) => {
    setCurrentProject(id)
    isProjectMenuOpen.value = false
}

const isProfileMenuOpen = ref(false)
const showNotifications = ref(false)
const showLogoutModal = ref(false)
const profileMenuRef = ref(null)
const notificationsRef = ref(null)
const profileMenuPosition = ref({ top: '0px', right: '0px' })
const notificationsPosition = ref({ top: '0px', right: '0px' })
const notifications = ref([])
const unreadCount = computed(() => notifications.value.filter(n => !n.read).length)
const subscription = ref({
  planName: '—',
  expiresAt: null,
  expiresAtLabel: '',
})

const displayName = computed(() => {
  if (!user.value) return 'Загрузка...'
  if (user.value.first_name || user.value.last_name) {
    return `${user.value.first_name || ''} ${user.value.last_name || ''}`.trim()
  }
  return user.value.username || user.value.email
})

const toggleProfileMenu = async () => {
  if (isProfileMenuOpen.value) {
    isProfileMenuOpen.value = false
  } else {
    showNotifications.value = false
    isProfileMenuOpen.value = true
    await nextTick()
    updateProfileMenuPosition()
  }
}

const toggleNotifications = async () => {
  if (showNotifications.value) {
    showNotifications.value = false
  } else {
    isProfileMenuOpen.value = false
    showNotifications.value = true
    await nextTick()
    updateNotificationsPosition()
  }
}

const updateProfileMenuPosition = async () => {
  await nextTick()
  const button = document.querySelector('[data-profile-button]')
  if (button) {
    const rect = button.getBoundingClientRect()
    profileMenuPosition.value = {
      top: `${rect.bottom + 8}px`,
      right: `${window.innerWidth - rect.right}px`
    }
  }
}

const getProfileMenuStyle = () => {
  return {
    top: profileMenuPosition.value.top,
    right: profileMenuPosition.value.right
  }
}

const updateNotificationsPosition = async () => {
  await nextTick()
  const button = document.querySelector('[data-notifications-button]')
  if (button) {
    const rect = button.getBoundingClientRect()
    notificationsPosition.value = {
      top: `${rect.bottom + 8}px`,
      right: `${window.innerWidth - rect.right}px`
    }
  }
}

const getNotificationsStyle = () => {
  return {
    top: notificationsPosition.value.top,
    right: notificationsPosition.value.right
  }
}

const closeProfileMenu = () => {
  isProfileMenuOpen.value = false
}

const handleLogoutClick = () => {
  closeProfileMenu()
  showLogoutModal.value = true
}

const handleLogout = () => {
  forceLogout()
  showLogoutModal.value = false
  router.push('/signin')
}

const formatDate = (iso) => {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleDateString('ru-RU')
}

const formatAgo = (iso) => {
  if (!iso) return 'Недавно'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return 'Недавно'
  const diffMin = Math.floor((Date.now() - d.getTime()) / 60000)
  if (diffMin < 1) return 'Только что'
  if (diffMin < 60) return `${diffMin} мин назад`
  const diffH = Math.floor(diffMin / 60)
  if (diffH < 24) return `${diffH} ч назад`
  const diffD = Math.floor(diffH / 24)
  return `${diffD} дн назад`
}

const loadSubscription = async () => {
  try {
    const { data } = await api.get('billing/subscription')
    subscription.value = {
      planName: data?.plan_name || data?.plan_code || '—',
      expiresAt: data?.subscription_expires_at || null,
      expiresAtLabel: formatDate(data?.subscription_expires_at),
    }
  } catch {
    subscription.value = {
      planName: '—',
      expiresAt: null,
      expiresAtLabel: '',
    }
  }
}

const buildNotificationsFromBackend = async () => {
  const rows = []
  try {
    const { data: integrations } = await api.get('integrations/')
    for (const integration of integrations || []) {
      try {
        const { data: status } = await api.get(`integrations/${integration.id}/sync-status`)
        const job = status?.job
        if (!job) continue
        const st = String(job.status || '').toUpperCase()
        if (st === 'FAILED') {
          rows.push({
            id: `sync-failed-${integration.id}-${job.id}`,
            title: `Ошибка синхронизации: ${integration.client_name || integration.platform}`,
            time: formatAgo(job.updated_at),
            read: false,
          })
        } else if (st === 'RUNNING' || st === 'QUEUED') {
          rows.push({
            id: `sync-running-${integration.id}-${job.id}`,
            title: `Синхронизация выполняется: ${integration.client_name || integration.platform}`,
            time: formatAgo(job.updated_at),
            read: false,
          })
        }
      } catch {
        // ignore one integration errors
      }
    }
  } catch {
    // ignore global errors
  }

  if (subscription.value.expiresAt) {
    const expires = new Date(subscription.value.expiresAt)
    const daysLeft = Math.ceil((expires.getTime() - Date.now()) / 86400000)
    if (Number.isFinite(daysLeft) && daysLeft >= 0 && daysLeft <= 7) {
      rows.push({
        id: 'subscription-expiring',
        title: `Подписка истекает через ${daysLeft} дн`,
        time: `До ${subscription.value.expiresAtLabel}`,
        read: false,
      })
    }
  }
  notifications.value = rows
}

const markAsRead = (id) => {
  const notification = notifications.value.find(n => n.id === id)
  if (notification && !notification.read) {
    notification.read = true
  }
}

const markAllAsRead = () => {
  notifications.value.forEach(n => { n.read = true })
}

const removeNotification = (id) => {
  notifications.value = notifications.value.filter(n => n.id !== id)
}

// Закрытие dropdown при клике вне его
const handleClickOutside = (event) => {
  const target = event.target
  
  // Проверяем профиль
  if (isProfileMenuOpen.value) {
    const profileButton = target.closest('[data-profile-button]')
    const profileDropdown = target.closest('.dropdown-menu')
    if (!profileButton && !profileDropdown) {
      closeProfileMenu()
    }
  }

  // Проверяем уведомления
  if (showNotifications.value) {
    const notificationsButton = target.closest('[data-notifications-button]')
    const notificationsDropdown = target.closest('.dropdown-menu')
    if (!notificationsButton && !notificationsDropdown) {
      showNotifications.value = false
    }
  }

  // Проверяем проектное меню
  if (isProjectMenuOpen.value && projectMenuRef.value) {
    if (!projectMenuRef.value.contains(target)) {
        isProjectMenuOpen.value = false
    }
  }
}

onMounted(() => {
  fetchProjects() // Ensure projects are loaded
  loadSubscription()
  buildNotificationsFromBackend()
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>
