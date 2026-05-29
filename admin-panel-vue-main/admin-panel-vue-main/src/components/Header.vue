<template>
  <header class="h-[5.2778rem] flex items-stretch bg-white dark:bg-[#1C1F2E] border-b border-black/5 dark:border-white/[0.07] flex-shrink-0 dark:shadow-[0_1px_0_rgba(255,255,255,0.04)]">
    <div class="flex-1 flex items-center px-[0.5556rem] py-[0.3472rem] gap-1.5 min-w-0 2xl:px-[1.7361rem] 2xl:gap-4">

      <!-- Left: Project selector -->
      <div class="relative flex-shrink-0" ref="projectMenuRef">
        <button
          @click="toggleProjectMenu"
          class="flex min-h-[3.1944rem] items-center gap-2 rounded-[0.8333rem] bg-[#f5f7f9] px-[0.6944rem] py-[0.6944rem] text-left transition-all duration-500 hover:bg-[#ecf3fe] dark:bg-white/10 dark:hover:bg-white/15 2xl:gap-5 2xl:px-[1.0417rem]"
        >
          <div class="flex h-8 w-8 flex-shrink-0 items-center justify-center overflow-hidden rounded-full bg-[#e8eef9] text-[0.7639rem] font-bold text-[#2563eb] 2xl:h-9 2xl:w-9">
            <img v-if="headerProjectAvatar" class="h-full w-full object-cover" :src="headerProjectAvatar" :alt="headerProjectName" />
            <span v-else>{{ headerProjectInitials }}</span>
          </div>
          <div class="hidden min-w-[4.5833rem] max-w-[7.2222rem] flex-col gap-[0.2083rem] text-left min-[1180px]:flex 2xl:min-w-[6.25rem] 2xl:max-w-none">
            <div class="truncate text-[0.8333rem] font-medium leading-none text-[#515151] dark:text-gray-100 2xl:text-[0.9722rem]">{{ headerProjectName }}</div>
            <div class="hidden pt-px text-[0.6944rem] leading-none text-[rgba(105,105,105,0.6)] dark:text-white/55 2xl:block">Отчеты агентства в одном месте</div>
          </div>
          <span class="header-arrow-circle ml-auto flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-white transition-all duration-500 dark:bg-white/15">
            <svg class="w-[0.625rem] h-[0.625rem] text-gray-500 transition-transform duration-500 dark:text-white/75" :class="isProjectMenuOpen ? 'rotate-180' : ''" fill="none" viewBox="0 0 10 6">
              <path d="M1 1l4 4 4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </span>
        </button>

        <!-- Project dropdown -->
        <Transition name="dropdown">
          <div
            v-if="isProjectMenuOpen"
            class="absolute left-1/2 top-full z-50 mt-2 min-w-[25rem] -translate-x-1/2 px-[2.0833rem] pb-[2.0833rem] pt-[0.6944rem]"
          >
            <div class="relative rounded-[0.8333rem] bg-white shadow-[0_0_15px_rgba(0,0,0,0.1)] dark:shadow-[0_8px_32px_rgba(0,0,0,0.45),0_0_0_1px_rgba(255,255,255,0.07),inset_0_1px_0_rgba(255,255,255,0.07)] after:absolute after:left-1/2 after:top-0 after:h-[0.9722rem] after:w-[0.9722rem] after:-translate-x-1/2 after:-translate-y-1/2 after:rotate-45 after:bg-white dark:bg-[#2C2F3D] dark:after:bg-[#2C2F3D]">
              <div class="px-4 pb-2 pt-4 font-medium">
                <div class="px-4 py-2 text-[0.8333rem] font-medium uppercase text-[rgba(105,105,105,0.56)] dark:text-white/55">Мои проекты</div>
                <ul class="mb-2 text-[0.9722rem]">
                  <li>
                    <button
                      @click="handleProjectSelect(null)"
                      :class="['w-full rounded-[0.8333rem] px-4 py-2.5 text-left transition-colors', !currentProjectId ? 'bg-[#ecf3fe] font-semibold text-[#2563eb] dark:bg-white/10 dark:text-[#4A7AFF]' : 'text-gray-700 hover:bg-[#f5f7f9] dark:text-white/75 dark:hover:bg-white/5']"
                    >Все проекты</button>
                  </li>
                  <li v-for="project in projects" :key="project.id">
                    <button
                      @click="handleProjectSelect(project.id)"
                      :class="['flex w-full items-center gap-3 rounded-[0.8333rem] px-4 py-2.5 text-left transition-colors', currentProjectId === project.id ? 'bg-[#ecf3fe] font-semibold text-[#2563eb] dark:bg-white/10 dark:text-[#4A7AFF]' : 'text-gray-700 hover:bg-[#f5f7f9] dark:text-white/75 dark:hover:bg-white/5']"
                    >
                      <span class="flex h-7 w-7 shrink-0 items-center justify-center overflow-hidden rounded-full bg-[#e8eef9] text-[0.6944rem] font-bold text-[#2563eb]">
                        <img v-if="projectAvatarUrl(project)" class="h-full w-full object-cover" :src="projectAvatarUrl(project)" :alt="project.name" />
                        <span v-else>{{ projectInitials(project) }}</span>
                      </span>
                      <span class="min-w-0 truncate">{{ project.name }}</span>
                    </button>
                  </li>
                </ul>
                <button
                  @click="router.push('/projects/create'); isProjectMenuOpen = false"
                  class="flex w-full items-center gap-2 rounded-[0.8333rem] px-4 py-3 text-[0.9028rem] font-medium text-[#2563eb] transition-colors hover:bg-[#ecf3fe] dark:text-[#4A7AFF] dark:hover:bg-white/5"
                >
                  <svg class="h-4 w-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/>
                  </svg>
                  Создать новый проект
                </button>
              </div>
            </div>
          </div>
        </Transition>
      </div>

      <!-- Subscription info (xxl+) -->
      <div class="hidden items-center gap-1.5 border-l border-black/5 pl-1.5 dark:border-white/10 2xl:flex 2xl:gap-4 2xl:pl-4">
        <div>
          <div class="whitespace-nowrap text-[0.6944rem] font-medium text-gray-500 dark:text-white/55 2xl:text-[0.9028rem]">
            Ваш тариф: <b class="font-bold text-gray-800 dark:text-gray-100">{{ subscription.planName }}</b>
          </div>
          <div v-if="subscription.expiresAtLabel" class="hidden text-[0.7639rem] text-gray-400 2xl:block">
            Действует до {{ subscription.expiresAtLabel }}
          </div>
        </div>
        <button
          @click="router.push('/tariffs')"
          class="flex min-h-[3.1944rem] flex-shrink-0 items-center justify-center rounded-[0.8333rem] border border-[#e1e1e1] dark:border-white/20 dark:hover:border-white/40 px-[0.625rem] py-2 text-[0.6944rem] font-medium leading-none transition-all duration-500 hover:border-[#2563eb] 2xl:px-[1.1806rem] 2xl:text-[0.9028rem]"
        >
          <span class="bg-[linear-gradient(270deg,#06b5d4_0.35%,#1f9de4_32.08%,#2563eb_96.51%)] bg-clip-text text-transparent">
            Продлить
          </span>
        </button>
      </div>

      <!-- Spacer -->
      <div class="min-w-1 flex-1" />

      <!-- Right actions -->
      <div class="flex flex-shrink-0 items-center gap-1.5 2xl:gap-2">

        <!-- Add project -->
        <button
          @click="router.push('/projects/create')"
          class="group relative hidden min-h-[3.1944rem] items-center justify-center overflow-hidden rounded-[0.8333rem] bg-[linear-gradient(270deg,#ff8a2a_0%,#ff6a3d_48%,#f25b2a_100%)] px-[0.625rem] py-2 text-center text-[0.6944rem] font-semibold leading-none text-white transition-all duration-700 after:absolute after:inset-0 after:rounded-[0.8333rem] after:bg-[linear-gradient(270deg,#ffb067_0%,#ff7f52_48%,#ff6637_100%)] after:opacity-0 after:transition-opacity after:duration-1000 hover:scale-[1.03] hover:text-white hover:after:opacity-100 active:scale-[0.97] min-[1360px]:inline-flex 2xl:px-[1.1806rem] 2xl:text-[0.9028rem]"
        >
          <span class="relative z-[1] flex items-center gap-1.5 whitespace-nowrap 2xl:gap-2.5">
            Добавить проект
            <span class="relative inline-flex h-[0.9722rem] w-[0.9722rem] flex-shrink-0 items-center justify-center rounded-full bg-white/20 2xl:h-[1.0417rem] 2xl:w-[1.0417rem]">
              <span class="absolute left-1/2 top-1/2 h-px w-[0.3472rem] -translate-x-1/2 -translate-y-1/2 rounded-full bg-white"></span>
              <span class="absolute left-1/2 top-1/2 h-[0.3472rem] w-px -translate-x-1/2 -translate-y-1/2 rounded-full bg-white"></span>
            </span>
          </span>
        </button>

        <!-- Notifications bell -->
        <div class="relative">
          <button
            data-notifications-button
            @click="toggleNotifications"
            class="relative flex min-h-[3.1944rem] min-w-[3.1944rem] items-center justify-center rounded-[0.8333rem] bg-[#f5f7f9] transition-colors duration-500 hover:bg-[#ecf3fe] dark:bg-white/10 dark:hover:bg-white/15"
          >
            <svg class="h-[1.1806rem] w-[1.1806rem] fill-[#afafaf]">
              <use href="/admirra/img/svg/sprite.svg#bell"></use>
            </svg>
            <span
              v-if="unreadCount > 0"
              class="absolute left-1/2 top-1/2 flex min-h-[0.9028rem] min-w-[0.9028rem] items-center justify-center rounded-[0.1389rem] bg-[#82d944] px-[0.2083rem] text-[0.5556rem] leading-[0.9028rem] text-white"
            >{{ unreadCount }}</span>
          </button>

          <Transition name="dropdown">
            <div
              v-if="showNotifications"
              class="absolute top-full z-50 min-w-[25rem] w-[calc(100%+5.5556rem)] right-[-2.0833rem] px-[2.0833rem] pb-[2.0833rem] pt-[0.6944rem]"
            >
              <div class="relative rounded-[0.8333rem] bg-white shadow-[0_0_15px_rgba(0,0,0,0.1)] dark:shadow-[0_8px_32px_rgba(0,0,0,0.45),0_0_0_1px_rgba(255,255,255,0.07),inset_0_1px_0_rgba(255,255,255,0.07)] after:absolute after:bottom-full after:right-8 after:border-x-[0.4861rem] after:border-b-[0.4861rem] after:border-x-transparent after:border-b-white dark:bg-[#2C2F3D] dark:after:border-b-[#2C2F3D]">
                <div class="p-4 text-[1.1111rem] font-semibold text-gray-800 dark:text-gray-100">Уведомления</div>
                <hr class="border-black/5 dark:border-white/10" />
                <div v-if="notifications.length === 0" class="p-5 text-center text-[0.8333rem] text-[#696969] dark:text-white/55">Нет уведомлений</div>
                <div v-else class="max-h-80 overflow-y-auto py-2">
                  <a
                    v-for="notification in notifications"
                    :key="notification.id"
                    @click.prevent="markAsRead(notification.id)"
                    href="#"
                    :class="['flex w-full items-center px-0 py-1 text-[0.9722rem] transition-colors hover:text-[#2563eb]', !notification.is_read ? 'text-[#2563eb]' : 'text-[#696969] dark:text-white/75']"
                  >
                    <div class="flex h-[3.0556rem] w-[3.0556rem] flex-shrink-0 items-center justify-center">
                      <svg class="h-5 w-5 fill-[#afafaf]">
                        <use href="/admirra/img/svg/sprite.svg#bell"></use>
                      </svg>
                    </div>
                    <div class="min-w-0 flex-1 pr-3">
                      <div class="font-medium leading-snug">{{ notification.title }}</div>
                      <div v-if="notification.body" class="mt-1 text-[0.7639rem] leading-snug text-[#696969]/75">{{ notification.body }}</div>
                      <div class="mt-1 text-[0.7639rem] text-[#696969]/75">{{ formatTime(notification.created_at) }}</div>
                    </div>
                    <div v-if="!notification.is_read" class="mr-4 h-2 w-2 flex-shrink-0 rounded-full bg-[#2563eb]" />
                  </a>
                </div>
                <template v-if="notifications.length > 0 && unreadCount > 0">
                  <hr class="border-black/5 dark:border-white/10" />
                  <div class="p-3 text-center">
                    <button @click.prevent="markAllAsRead" class="text-[0.8333rem] font-medium text-[#2563eb] hover:underline">
                      Отметить все как прочитанные
                    </button>
                  </div>
                </template>
              </div>
            </div>
          </Transition>
        </div>

        <!-- User menu -->
        <div class="relative">
          <button
            data-profile-button
            @click="toggleProfileMenu"
            class="flex min-h-[3.1944rem] items-center gap-2 rounded-[0.8333rem] bg-[#f5f7f9] px-[0.6944rem] py-[0.6944rem] text-left transition-all duration-500 hover:bg-[#ecf3fe] dark:bg-white/10 dark:hover:bg-white/15 2xl:gap-5 2xl:px-[1.0417rem]"
          >
            <div class="h-[2.0833rem] w-[2.0833rem] flex-shrink-0 overflow-hidden rounded-full bg-[#ecf3fe] dark:bg-white/10">
              <img class="h-full w-full object-cover" src="/admirra/img/avatars/avatar-30x30.png" alt="#" />
            </div>
            <span class="hidden max-w-[4.7222rem] truncate text-[0.6944rem] font-medium text-[#515151] dark:text-gray-100 min-[1280px]:block 2xl:max-w-[10.4167rem] 2xl:text-[0.9722rem]">{{ displayName }}</span>
            <span class="header-arrow-circle ml-auto flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-white transition-all duration-500 dark:bg-white/15">
              <svg class="h-[0.625rem] w-[0.625rem] text-gray-500 transition-transform duration-500 dark:text-white/75" :class="isProfileMenuOpen ? 'rotate-180' : ''" fill="none" viewBox="0 0 10 6">
                <path d="M1 1l4 4 4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </span>
          </button>

          <Transition name="dropdown">
            <div
              v-if="isProfileMenuOpen"
              class="absolute top-full z-50 min-w-[25rem] w-[calc(100%+5.5556rem)] right-[-2.0833rem] px-[2.0833rem] pb-[2.0833rem] pt-[0.6944rem]"
            >
              <div class="relative rounded-[0.8333rem] bg-white shadow-[0_0_15px_rgba(0,0,0,0.1)] dark:shadow-[0_8px_32px_rgba(0,0,0,0.45),0_0_0_1px_rgba(255,255,255,0.07),inset_0_1px_0_rgba(255,255,255,0.07)] after:absolute after:bottom-full after:right-8 after:border-x-[0.4861rem] after:border-b-[0.4861rem] after:border-x-transparent after:border-b-white dark:bg-[#2C2F3D] dark:after:border-b-[#2C2F3D]">
                <div class="p-4">
                  <div class="mb-1 text-[1.0417rem] font-semibold text-gray-800 dark:text-gray-100">{{ displayName }}</div>
                  <div class="text-[0.8333rem] text-[rgba(105,105,105,0.75)] dark:text-white/55">{{ user?.email }}</div>
                </div>
                <hr class="border-black/5 dark:border-white/10" />
                <div class="py-3">
                  <button
                    @click.prevent="toggleTheme"
                    class="flex w-full items-center py-1 text-[0.9722rem] text-[#696969] transition-colors hover:text-[#2563eb] dark:text-white/75 dark:hover:text-[#4A7AFF]"
                  >
                    <span class="flex h-[3.0556rem] w-[3.0556rem] items-center justify-center">
                      <svg class="h-5 w-5 fill-[#afafaf]">
                        <use href="/admirra/img/svg/sprite.svg#moon"></use>
                      </svg>
                    </span>
                    <span class="flex-1 pr-3 text-left">{{ isDarkMode ? 'Светлая тема' : 'Темная тема' }}</span>
                    <span :class="['relative mr-4 inline-flex h-5 w-9 flex-shrink-0 rounded-full transition-colors duration-300', isDarkMode ? 'bg-[#2563eb]' : 'bg-gray-200']">
                      <span :class="['absolute left-0.5 top-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform duration-300', isDarkMode ? 'translate-x-4' : 'translate-x-0']" />
                    </span>
                  </button>
                  <button
                    @click="router.push('/profile'); closeProfileMenu()"
                    class="flex w-full items-center py-1 text-[0.9722rem] text-[#696969] transition-colors hover:text-[#2563eb] dark:text-white/75 dark:hover:text-[#4A7AFF]"
                  >
                    <span class="flex h-[3.0556rem] w-[3.0556rem] items-center justify-center">
                      <svg class="h-5 w-5 fill-none stroke-[#afafaf]">
                        <use href="/admirra/img/svg/sprite.svg#user"></use>
                      </svg>
                    </span>
                    <span class="pr-3">Профиль</span>
                  </button>
                  <button
                    @click="router.push('/settings'); closeProfileMenu()"
                    class="flex w-full items-center py-1 text-[0.9722rem] text-[#696969] transition-colors hover:text-[#2563eb] dark:text-white/75 dark:hover:text-[#4A7AFF]"
                  >
                    <span class="flex h-[3.0556rem] w-[3.0556rem] items-center justify-center">
                      <svg class="h-5 w-5 fill-[#afafaf]">
                        <use href="/admirra/img/svg/sprite.svg#setting"></use>
                      </svg>
                    </span>
                    <span class="pr-3">Настройки</span>
                  </button>
                  <button
                    @click="handleLogoutClick"
                    class="flex w-full items-center py-1 text-[0.9722rem] text-[#dc3545] transition-colors hover:text-[#2563eb]"
                  >
                    <span class="flex h-[3.0556rem] w-[3.0556rem] items-center justify-center">
                      <svg class="h-5 w-5 fill-[#dc3545]">
                        <use href="/admirra/img/svg/sprite.svg#exit"></use>
                      </svg>
                    </span>
                    <span class="pr-3">Выход</span>
                  </button>
                </div>
              </div>
            </div>
          </Transition>
        </div>

        <!-- Burger (tablet/mobile only) -->
        <button
          @click="toggleMobileMenu"
          :class="[
            'flex h-[3.1944rem] w-[3.1944rem] flex-shrink-0 items-center justify-center rounded-[0.8333rem] bg-[#f5f7f9] transition-colors duration-500 hover:bg-[#ecf3fe] dark:bg-white/10 dark:hover:bg-white/15 min-[1024px]:hidden',
            isMobileMenuOpen ? 'is-active' : '',
          ]"
        >
          <span class="burger-lines relative block h-[1.0417rem] w-6">
            <span class="burger-line burger-line-top" />
            <span class="burger-line burger-line-center" />
            <span class="burger-line burger-line-bottom" />
          </span>
        </button>

      </div>
    </div>
  </header>

  <ConfirmModal
    v-model:is-open="showLogoutModal"
    title="Подтверждение выхода"
    message="Вы уверены, что хотите выйти из системы?"
    @confirm="handleLogout"
  />
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api/axios'
import ConfirmModal from './ConfirmModal.vue'
import { useSidebar } from '../composables/useSidebar'
import { useAuth } from '../composables/useAuth'
import { useTheme } from '../composables/useTheme'
import { useProjects } from '../composables/useProjects'
import { projectAvatarUrl, projectInitials } from '../utils/projectAvatar'

const router = useRouter()
const { isMobileMenuOpen, toggleMobileMenu } = useSidebar()
const { user, logout } = useAuth()
const { isDarkMode, toggleTheme } = useTheme()
const { projects, currentProjectId, currentProject, currentProjectName, fetchProjects, setCurrentProject } = useProjects()

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

const subscription = ref({ planName: '—', expiresAt: null, expiresAtLabel: '' })

const displayName = computed(() => {
  if (!user.value) return 'Загрузка...'
  if (user.value.first_name || user.value.last_name) {
    return `${user.value.first_name || ''} ${user.value.last_name || ''}`.trim()
  }
  return user.value.username || user.value.email
})

const headerProjectName = computed(() => {
  return currentProjectId.value ? currentProjectName.value : 'Трафик агентство'
})

const headerProjectAvatar = computed(() => currentProjectId.value ? projectAvatarUrl(currentProject.value) : '')
const headerProjectInitials = computed(() => currentProjectId.value ? projectInitials(currentProject.value) : 'TA')

const notifications = ref([])
const unreadCount = computed(() => notifications.value.filter(n => !n.is_read).length)

let notificationsPollTimer = null

const fetchNotifications = async () => {
  try {
    const { data } = await api.get('notifications/')
    notifications.value = data
  } catch (e) { /* ignore */ }
}

const formatTime = (isoStr) => {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

const formatDate = (iso) => {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleDateString('ru-RU')
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
    subscription.value = { planName: '—', expiresAt: null, expiresAtLabel: '' }
  }
}

const toggleProfileMenu = () => {
  isProfileMenuOpen.value = !isProfileMenuOpen.value
  if (isProfileMenuOpen.value) showNotifications.value = false
}

const toggleNotifications = () => {
  showNotifications.value = !showNotifications.value
  if (showNotifications.value) isProfileMenuOpen.value = false
}

const closeProfileMenu = () => { isProfileMenuOpen.value = false }

const handleLogoutClick = () => {
  closeProfileMenu()
  showLogoutModal.value = true
}

const handleLogout = async () => {
  await logout()
  showLogoutModal.value = false
  router.push('/signin')
}

const markAsRead = async (id) => {
  const notification = notifications.value.find(n => n.id === id)
  if (notification && !notification.is_read) {
    notification.is_read = true
    try { await api.post(`notifications/${id}/read`) } catch (e) { /* ignore */ }
  }
}

const markAllAsRead = async () => {
  notifications.value.forEach(n => { n.is_read = true })
  try { await api.post('notifications/read-all') } catch (e) { /* ignore */ }
}

const handleClickOutside = (event) => {
  const target = event.target
  if (isProfileMenuOpen.value) {
    const profileButton = target.closest('[data-profile-button]')
    const profileDropdown = target.closest('.absolute')
    if (!profileButton && !profileDropdown) closeProfileMenu()
  }
  if (showNotifications.value) {
    const notificationsButton = target.closest('[data-notifications-button]')
    const notificationsDropdown = target.closest('.absolute')
    if (!notificationsButton && !notificationsDropdown) showNotifications.value = false
  }
  if (isProjectMenuOpen.value && projectMenuRef.value) {
    if (!projectMenuRef.value.contains(target)) isProjectMenuOpen.value = false
  }
}

onMounted(() => {
  fetchProjects()
  loadSubscription()
  fetchNotifications()
  notificationsPollTimer = setInterval(fetchNotifications, 30_000)
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  if (notificationsPollTimer) clearInterval(notificationsPollTimer)
})
</script>

<style scoped>
.dropdown-enter-active,
.dropdown-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-0.2778rem);
}

.burger-line {
  position: absolute;
  left: 0;
  height: 1px;
  border-radius: 69.375rem;
  background: #afafaf;
  transition: 0.3s ease-in-out;
}

.burger-line-top {
  top: 0;
  width: 100%;
}

.burger-line-center {
  top: 50%;
  left: 10%;
  width: 80%;
}

.burger-line-bottom {
  bottom: 0;
  width: 100%;
}

.is-active .burger-line-top {
  top: 0.4861rem;
  transform: rotate(-45deg);
}

.is-active .burger-line-center {
  left: 0;
  top: 0.4861rem;
  width: 100%;
  transform: rotate(45deg);
}

.is-active .burger-line-bottom {
  opacity: 0;
}

:global(.dark) .header-arrow-circle,
:global(.darkmode) .header-arrow-circle {
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.08);
}

:global(.dark) [data-notifications-button] svg,
:global(.darkmode) [data-notifications-button] svg {
  fill: rgba(255, 255, 255, 0.88);
}

:global(.dark) [data-profile-button] + .dropdown-enter-active svg,
:global(.darkmode) [data-profile-button] + .dropdown-enter-active svg,
:global(.dark) [data-profile-button] + .dropdown-leave-active svg,
:global(.darkmode) [data-profile-button] + .dropdown-leave-active svg {
  color: rgba(255, 255, 255, 0.88);
}

:global(.dark) header svg.fill-\[\#afafaf\],
:global(.darkmode) header svg.fill-\[\#afafaf\] {
  fill: rgba(255, 255, 255, 0.88);
}

:global(.dark) header svg.stroke-\[\#afafaf\],
:global(.darkmode) header svg.stroke-\[\#afafaf\] {
  stroke: rgba(255, 255, 255, 0.88);
}

:global(.dark) .burger-line,
:global(.darkmode) .burger-line {
  background: rgba(255, 255, 255, 0.88);
}
</style>
