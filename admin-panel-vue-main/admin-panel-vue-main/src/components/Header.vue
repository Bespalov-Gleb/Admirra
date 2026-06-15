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
          <div v-if="isProjectMenuOpen" class="absolute left-1/2 top-full z-50 mt-2 w-[21rem] -translate-x-1/2">
            <div class="hd-panel">
              <div class="hd-section-label">Мои проекты</div>
              <ul class="hd-menu-list">
                <li>
                  <button @click="handleProjectSelect(null)" :class="['hd-menu-item', !currentProjectId ? 'hd-menu-item--active' : '']">
                    <span class="hd-project-avatar">
                      <svg viewBox="0 0 16 16" fill="none" class="w-[0.8333rem] h-[0.8333rem]"><rect x="1.5" y="1.5" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.4"/><rect x="9.5" y="1.5" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.4"/><rect x="1.5" y="9.5" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.4"/><rect x="9.5" y="9.5" width="5" height="5" rx="1" stroke="currentColor" stroke-width="1.4"/></svg>
                    </span>
                    <span class="hd-menu-item-label">Все проекты</span>
                  </button>
                </li>
                <li v-for="project in projects" :key="project.id">
                  <button @click="handleProjectSelect(project.id)" :class="['hd-menu-item', currentProjectId === project.id ? 'hd-menu-item--active' : '']">
                    <span class="hd-project-avatar">
                      <img v-if="projectAvatarUrl(project)" class="h-full w-full object-cover" :src="projectAvatarUrl(project)" :alt="project.name" />
                      <span v-else class="text-[0.625rem] font-bold">{{ projectInitials(project) }}</span>
                    </span>
                    <span class="hd-menu-item-label min-w-0 truncate">{{ project.name }}</span>
                  </button>
                </li>
              </ul>
              <div class="hd-divider"></div>
              <button @click="router.push('/projects/create'); isProjectMenuOpen = false" class="hd-create-item">
                <span class="hd-create-icon">
                  <svg class="w-[0.75rem] h-[0.75rem]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"/></svg>
                </span>
                Создать проект
              </button>
            </div>
          </div>
        </Transition>
      </div>

      <!-- Subscription info (xxl+) -->
      <div class="hidden items-center gap-1.5 border-l border-black/5 pl-1.5 dark:border-white/10 2xl:flex 2xl:gap-4 2xl:pl-4">
        <button
          @click="router.push('/settings?tab=tariff')"
          class="text-left bg-transparent border-0 p-0 cursor-pointer transition-opacity hover:opacity-80"
        >
          <div class="whitespace-nowrap text-[0.6944rem] font-medium text-gray-500 dark:text-white/55 2xl:text-[0.9028rem]">
            Ваш тариф: <b class="font-bold text-gray-800 dark:text-gray-100">{{ subscription.planName }}</b>
          </div>
          <div v-if="subscription.expiresAtLabel" class="hidden text-[0.7639rem] text-gray-400 2xl:block">
            Действует до {{ subscription.expiresAtLabel }}
          </div>
        </button>
        <button
          @click="router.push('/settings?tab=tariff')"
          class="flex min-h-[3.1944rem] flex-shrink-0 items-center justify-center rounded-[0.8333rem] border border-[#e1e1e1] dark:border-white/20 dark:hover:border-white/40 px-[0.625rem] py-2 text-[0.6944rem] font-medium leading-none transition-all duration-500 hover:border-[#2563eb] 2xl:px-[1.1806rem] 2xl:text-[0.9028rem]"
        >
          <span class="bg-[linear-gradient(270deg,#06b5d4_0.35%,#1f9de4_32.08%,#2563eb_96.51%)] bg-clip-text text-transparent">
            Продлить
          </span>
        </button>
      </div>

      <!-- Usage chip -->
      <div
        ref="usageChipRef"
        class="relative hidden items-center min-[1180px]:flex"
        @mouseenter="openUsagePopover"
        @mouseleave="scheduleCloseUsagePopover"
      >
        <button
          @click="toggleUsagePopover"
          @focus="openUsagePopover"
          @keydown.esc.stop="closeUsagePopover"
          :aria-expanded="showUsagePopover ? 'true' : 'false'"
          aria-haspopup="dialog"
          aria-label="Использование лимитов тарифа"
          class="usage-chip"
        >
          <span :class="['usage-gauge', projectsAtLimit ? 'usage-gauge--amber' : '']">
            <svg class="usage-icon" viewBox="0 0 16 16" fill="none"><path d="M2.5 5.2V4.1c0-.7.5-1.2 1.2-1.2h3l1.2 1.3h4.4c.7 0 1.2.5 1.2 1.2v6.4c0 .7-.5 1.2-1.2 1.2H3.7c-.7 0-1.2-.5-1.2-1.2V5.2Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>
            <span class="usage-num">{{ usage.projectsUsed }} / {{ usage.projectsLimit }}</span>
            <span class="usage-label">проекты</span>
          </span>
          <span :class="['usage-gauge', aiAtLimit ? 'usage-gauge--amber' : '']">
            <svg class="usage-icon usage-icon--ai" viewBox="0 0 16 16" fill="none"><path d="M8 1.8l1.1 2.9 2.9 1.1-2.9 1.1L8 9.8 6.9 6.9 4 5.8l2.9-1.1L8 1.8Z" stroke="currentColor" stroke-width="1.35" stroke-linejoin="round"/><path d="M12.4 9.4l.5 1.2 1.2.5-1.2.5-.5 1.2-.5-1.2-1.2-.5 1.2-.5.5-1.2Z" stroke="currentColor" stroke-width="1.1" stroke-linejoin="round"/></svg>
            <span class="usage-num">{{ usage.aiRemaining }}</span>
            <span class="usage-label">AI осталось</span>
          </span>
        </button>

        <!-- Popover -->
        <Transition name="dropdown">
          <div
            v-if="showUsagePopover"
            class="absolute top-full left-1/2 -translate-x-1/2 z-50 mt-[0.6944rem] w-[23rem]"
          >
            <div class="usage-popover hd-panel" style="padding:1.3889rem 1.3889rem 1.1111rem;">
              <div class="usage-popover-header">
                <span>Тариф «{{ subscription.planName }}»</span>
                <span v-if="expiresShort" class="usage-popover-date">{{ expiresShort }}</span>
              </div>

              <div class="usage-popover-row">
                <div class="flex items-center justify-between mb-[0.4167rem]">
                  <span class="text-[0.9028rem] font-semibold text-[#444] dark:text-white/75">Проекты</span>
                  <span class="text-[0.9028rem] font-bold" :class="projectsAtLimit ? 'text-[#d97706]' : 'text-[#111827] dark:text-white/88'">{{ usage.projectsUsed }} / {{ usage.projectsLimit }}</span>
                </div>
                <div class="usage-bar">
                  <div class="usage-bar-fill" :class="projectsAtLimit ? 'usage-bar-fill--amber' : ''" :style="{ width: projectsPct + '%', animationDelay: '0.05s' }"></div>
                </div>
              </div>

              <div class="usage-popover-row">
                <div class="flex items-center justify-between mb-[0.4167rem]">
                  <span class="text-[0.9028rem] font-semibold text-[#444] dark:text-white/75">AI-запросы</span>
                  <span class="text-[0.9028rem] font-bold" :class="aiAtLimit ? 'text-[#d97706]' : 'text-[#111827] dark:text-white/88'">{{ usage.aiUsed }} / {{ usage.aiLimit }}</span>
                </div>
                <div class="usage-bar">
                  <div class="usage-bar-fill" :class="aiAtLimit ? 'usage-bar-fill--amber' : ''" :style="{ width: aiPct + '%', animationDelay: '0.18s' }"></div>
                </div>
                <div class="flex items-center justify-between mt-[0.3472rem]">
                  <span class="text-[0.7778rem] font-medium text-[#696969]/60 dark:text-white/38">осталось {{ usage.aiRemaining }}</span>
                  <span v-if="usage.aiResetDate" class="text-[0.7778rem] font-medium text-[#696969]/60 dark:text-white/38">сброс {{ usage.aiResetDate }}</span>
                </div>
              </div>

              <button @click="router.push('/settings?tab=tariff'); showUsagePopover = false" class="usage-popover-link">
                Управление тарифом
                <svg class="w-[0.8333rem] h-[0.8333rem]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6"/></svg>
              </button>
            </div>
          </div>
        </Transition>
      </div>

      <!-- Spacer -->
      <div class="min-w-1 flex-1" />

      <!-- Right actions -->
      <div class="flex flex-shrink-0 items-center gap-1.5 2xl:gap-2">

        <!-- Add project -->
        <button
          @click="router.push('/projects/create')"
          class="group relative hidden min-h-[3.1944rem] items-center justify-center overflow-hidden rounded-[0.8333rem] bg-[linear-gradient(270deg,#ff8a2a_0%,#ff6a3d_48%,#f25b2a_100%)] px-[1.25rem] py-2 text-center text-[0.6944rem] font-semibold leading-none text-white transition-all duration-700 after:absolute after:inset-0 after:rounded-[0.8333rem] after:bg-[linear-gradient(270deg,#ffb067_0%,#ff7f52_48%,#ff6637_100%)] after:opacity-0 after:transition-opacity after:duration-1000 hover:scale-[1.03] hover:text-white hover:after:opacity-100 active:scale-[0.97] min-[1360px]:inline-flex 2xl:px-[1.6667rem] 2xl:text-[0.9028rem]"
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
            <div class="flex h-[2.0833rem] w-[2.0833rem] flex-shrink-0 items-center justify-center overflow-hidden rounded-full bg-[#ecf3fe] dark:bg-white/10">
              <img v-if="avatarUrl" class="h-full w-full object-cover" :src="avatarUrl" alt="" />
              <span v-else class="text-[0.8333rem] font-semibold text-[#2563eb] dark:text-[#4A7AFF]">{{ avatarInitial }}</span>
            </div>
            <span class="hidden max-w-[4.7222rem] truncate text-[0.6944rem] font-medium text-[#515151] dark:text-gray-100 min-[1280px]:block 2xl:max-w-[10.4167rem] 2xl:text-[0.9722rem]">{{ displayName }}</span>
            <span class="header-arrow-circle ml-auto flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-white transition-all duration-500 dark:bg-white/15">
              <svg class="h-[0.625rem] w-[0.625rem] text-gray-500 transition-transform duration-500 dark:text-white/75" :class="isProfileMenuOpen ? 'rotate-180' : ''" fill="none" viewBox="0 0 10 6">
                <path d="M1 1l4 4 4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </span>
          </button>

          <Transition name="dropdown">
            <div v-if="isProfileMenuOpen" class="absolute top-full right-0 z-50 w-[18rem] mt-2">
              <div class="hd-panel">
                <div class="hd-profile-header">
                  <div class="hd-profile-avatar">
                    <img v-if="avatarUrl" :src="avatarUrl" alt="" />
                    <template v-else>{{ avatarInitial }}</template>
                  </div>
                  <div class="min-w-0">
                    <div class="hd-profile-name truncate">{{ displayName }}</div>
                    <div class="hd-profile-email truncate">{{ user?.email }}</div>
                  </div>
                </div>
                <div class="hd-divider"></div>
                <div>
                  <button @click.prevent="toggleTheme" class="hd-menu-item">
                    <span class="hd-menu-icon">
                      <svg class="h-[1.0417rem] w-[1.0417rem] fill-current" viewBox="0 0 20 20"><use href="/admirra/img/svg/sprite.svg#moon"></use></svg>
                    </span>
                    <span class="flex-1 text-left">{{ isDarkMode ? 'Светлая тема' : 'Темная тема' }}</span>
                    <span :class="['hd-toggle', isDarkMode ? 'hd-toggle--on' : '']"></span>
                  </button>
                  <button @click="router.push('/profile'); closeProfileMenu()" class="hd-menu-item">
                    <span class="hd-menu-icon">
                      <svg class="h-[1.0417rem] w-[1.0417rem] fill-none stroke-current" viewBox="0 0 20 20"><use href="/admirra/img/svg/sprite.svg#user"></use></svg>
                    </span>
                    <span>Профиль</span>
                  </button>
                  <button @click="router.push('/settings'); closeProfileMenu()" class="hd-menu-item">
                    <span class="hd-menu-icon">
                      <svg class="h-[1.0417rem] w-[1.0417rem] fill-current" viewBox="0 0 20 20"><use href="/admirra/img/svg/sprite.svg#setting"></use></svg>
                    </span>
                    <span>Настройки</span>
                  </button>
                  <div class="hd-divider"></div>
                  <button @click="handleLogoutClick" class="hd-menu-item hd-menu-item--danger">
                    <span class="hd-menu-icon">
                      <svg class="h-[1.0417rem] w-[1.0417rem] fill-current" viewBox="0 0 20 20"><use href="/admirra/img/svg/sprite.svg#exit"></use></svg>
                    </span>
                    <span>Выход</span>
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
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
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
const usage = ref({ projectsUsed: 0, projectsLimit: 1, aiUsed: 0, aiLimit: 30, aiRemaining: 30, aiResetDate: '' })
const showUsagePopover = ref(false)
const usageChipRef = ref(null)
let usageCloseTimer = null

const displayName = computed(() => {
  if (!user.value) return 'Загрузка...'
  if (user.value.first_name || user.value.last_name) {
    return `${user.value.first_name || ''} ${user.value.last_name || ''}`.trim()
  }
  return user.value.username || user.value.email
})

const avatarUrl = computed(() => user.value?.avatar_url || '')
const avatarInitial = computed(() => (displayName.value || '?').charAt(0).toUpperCase())

const headerProjectName = computed(() => {
  return currentProjectId.value ? currentProjectName.value : 'Трафик агентство'
})

const headerProjectAvatar = computed(() => currentProjectId.value ? projectAvatarUrl(currentProject.value) : '')
const headerProjectInitials = computed(() => currentProjectId.value ? projectInitials(currentProject.value) : 'TA')

const notifications = ref([])
const unreadCount = computed(() => notifications.value.filter(n => !n.is_read).length)

let notificationsPollTimer = null
let subscriptionPollTimer = null

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
    usage.value = {
      projectsUsed: data?.projects_used ?? 0,
      projectsLimit: data?.max_projects ?? 1,
      aiUsed: data?.ai_requests_used ?? 0,
      aiLimit: data?.max_ai_requests_per_period ?? 30,
      aiRemaining: data?.ai_requests_remaining ?? 30,
      aiResetDate: data?.ai_reset_date || '',
    }
  } catch {
    subscription.value = { planName: '—', expiresAt: null, expiresAtLabel: '' }
  }
}

const projectsAtLimit = computed(() => usage.value.projectsUsed >= usage.value.projectsLimit)
const aiAtLimit = computed(() => usage.value.aiRemaining <= 0)
const projectsPct = computed(() => Math.min(100, Math.round((usage.value.projectsUsed / Math.max(usage.value.projectsLimit, 1)) * 100)))
const aiPct = computed(() => Math.min(100, Math.round((usage.value.aiUsed / Math.max(usage.value.aiLimit, 1)) * 100)))

const clearUsageCloseTimer = () => {
  if (usageCloseTimer) {
    clearTimeout(usageCloseTimer)
    usageCloseTimer = null
  }
}

const openUsagePopover = () => {
  clearUsageCloseTimer()
  showUsagePopover.value = true
  isProfileMenuOpen.value = false
  showNotifications.value = false
}

const closeUsagePopover = () => {
  clearUsageCloseTimer()
  showUsagePopover.value = false
}

const scheduleCloseUsagePopover = () => {
  clearUsageCloseTimer()
  usageCloseTimer = setTimeout(() => {
    showUsagePopover.value = false
    usageCloseTimer = null
  }, 140)
}

const toggleUsagePopover = () => {
  if (showUsagePopover.value) closeUsagePopover()
  else openUsagePopover()
}

const expiresShort = computed(() => {
  if (!subscription.value.expiresAt) return ''
  const d = new Date(subscription.value.expiresAt)
  if (Number.isNaN(d.getTime())) return ''
  return `до ${String(d.getDate()).padStart(2,'0')}.${String(d.getMonth()+1).padStart(2,'0')}`
})

const toggleProfileMenu = () => {
  isProfileMenuOpen.value = !isProfileMenuOpen.value
  if (isProfileMenuOpen.value) {
    showNotifications.value = false
    closeUsagePopover()
  }
}

const toggleNotifications = () => {
  showNotifications.value = !showNotifications.value
  if (showNotifications.value) {
    isProfileMenuOpen.value = false
    closeUsagePopover()
  }
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
  if (showUsagePopover.value && usageChipRef.value) {
    if (!usageChipRef.value.contains(target)) closeUsagePopover()
  }
  if (isProjectMenuOpen.value && projectMenuRef.value) {
    if (!projectMenuRef.value.contains(target)) isProjectMenuOpen.value = false
  }
}

const handleKeydown = (event) => {
  if (event.key === 'Escape') {
    closeProfileMenu()
    showNotifications.value = false
    closeUsagePopover()
    isProjectMenuOpen.value = false
  }
}

onMounted(() => {
  fetchProjects()
  loadSubscription()
  fetchNotifications()
  notificationsPollTimer = setInterval(fetchNotifications, 30_000)
  subscriptionPollTimer = setInterval(loadSubscription, 60_000)
  document.addEventListener('click', handleClickOutside)
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  document.removeEventListener('keydown', handleKeydown)
  clearUsageCloseTimer()
  if (notificationsPollTimer) clearInterval(notificationsPollTimer)
  if (subscriptionPollTimer) clearInterval(subscriptionPollTimer)
})

watch(
  () => projects.value.map((project) => `${project.id}:${project.status || ''}`).join('|'),
  () => loadSubscription(),
)
</script>

<style scoped>
.dropdown-enter-active,
.dropdown-leave-active {
  transition: opacity 0.2s cubic-bezier(0.16, 1, 0.3, 1), transform 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}
.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  --tw-translate-y: -0.4rem;
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

/* ── Usage chip ── */
.usage-chip {
  display: inline-flex;
  align-items: center;
  gap: 0;
  min-height: 2.75rem;
  padding: 0;
  border-radius: 0.875rem;
  background: #fff;
  border: 1px solid rgba(120, 120, 120, 0.24);
  cursor: pointer;
  overflow: hidden;
  transition: border-color 0.2s, box-shadow 0.2s, transform 0.2s;
  white-space: nowrap;
  font-size: 0.75rem;
  box-shadow: 0 0.2778rem 0.8333rem rgba(15, 23, 42, 0.03);
}
.usage-chip:hover {
  border-color: rgba(37,99,235,0.24);
  box-shadow: 0 0.5556rem 1.3889rem rgba(15, 23, 42, 0.07);
}
.usage-chip:focus-visible {
  outline: none;
  border-color: rgba(37,99,235,0.5);
  box-shadow: 0 0 0 0.2083rem rgba(37,99,235,0.12), 0 0.5556rem 1.3889rem rgba(15, 23, 42, 0.07);
}
:global(.dark) .usage-chip {
  background: rgba(255,255,255,0.06);
  border-color: rgba(255,255,255,0.12);
}
:global(.dark) .usage-chip:hover {
  border-color: rgba(74,122,255,0.2);
}

.usage-gauge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.4375rem;
  min-height: 2.75rem;
  padding: 0 1rem;
  color: #6b7280;
  transition: background-color 0.2s, color 0.2s;
}
:global(.dark) .usage-gauge { color: rgba(255,255,255,0.65); }
.usage-gauge + .usage-gauge {
  border-left: 1px solid rgba(120, 120, 120, 0.20);
}
:global(.dark) .usage-gauge + .usage-gauge {
  border-left-color: rgba(255,255,255,0.10);
}
.usage-gauge--amber {
  background: #fff7e8;
  color: #7a4f0a;
}
:global(.dark) .usage-gauge--amber {
  background: rgba(217,119,6,0.14);
  color: #fbbf24;
}

.usage-icon {
  width: 1rem;
  height: 1rem;
  flex-shrink: 0;
  color: currentColor;
}
.usage-icon--ai {
  color: #2563eb;
}
.usage-gauge--amber .usage-icon--ai {
  color: currentColor;
}
.usage-num {
  color: #111827;
  font-weight: 800;
  font-size: 1rem;
  line-height: 1;
}
:global(.dark) .usage-num { color: rgba(255,255,255,0.92); }
.usage-gauge--amber .usage-num { color: #5d3d08; }
.usage-label {
  color: #6b7280;
  font-weight: 700;
  font-size: 0.8125rem;
}
:global(.dark) .usage-label { color: rgba(255,255,255,0.58); }
.usage-gauge--amber .usage-label { color: #a16207; }
@media (max-width: 1200px) { .usage-label { display: none; } }

/* ── Usage popover ── */
.usage-popover {
  background: #fff;
  border-radius: 1.1111rem;
  padding: 1.3889rem;
  box-shadow: 0 4px 6px -1px rgba(0,0,0,0.06), 0 12px 28px rgba(0,0,0,0.12), 0 0 0 1px rgba(0,0,0,0.04);
}
:global(.dark) .usage-popover {
  background: #2C2F3D;
  box-shadow: 0 12px 36px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.08), inset 0 1px 0 rgba(255,255,255,0.05);
}

.usage-popover-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.6944rem;
  font-size: 1.0417rem;
  font-weight: 700;
  color: #111827;
  margin-bottom: 1.1111rem;
}
:global(.dark) .usage-popover-header { color: rgba(255,255,255,0.9); }

.usage-popover-date {
  font-weight: 600;
  font-size: 0.8333rem;
  color: #9ca3af;
  white-space: nowrap;
}
:global(.dark) .usage-popover-date { color: rgba(255,255,255,0.35); }

.usage-popover-row { margin-bottom: 1rem; }

.usage-bar {
  height: 0.4167rem;
  border-radius: 2.7778rem;
  background: rgba(0,0,0,0.07);
  overflow: hidden;
}
:global(.dark) .usage-bar { background: rgba(255,255,255,0.08); }

@keyframes usage-bar-grow {
  from { transform: scaleX(0); }
}

.usage-bar-fill {
  height: 100%;
  border-radius: 2.7778rem;
  background: linear-gradient(90deg, #2563eb 0%, #14b8d5 100%);
  transform-origin: left center;
  animation: usage-bar-grow 0.65s cubic-bezier(0.16, 1, 0.3, 1) both;
  transition: width 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}
.usage-bar-fill--amber { background: linear-gradient(90deg, #d97706 0%, #f59e0b 100%); }

.usage-popover-link {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 0.4167rem;
  width: 100%;
  padding: 0.8333rem 0 0;
  margin-top: 0.8333rem;
  border: none;
  border-top: 1px solid rgba(0,0,0,0.06);
  border-radius: 0;
  font-size: 0.9028rem;
  font-weight: 700;
  color: #2563eb;
  background: transparent;
  cursor: pointer;
  transition: color 0.15s;
}
.usage-popover-link:hover { color: #1d4ed8; }
:global(.dark) .usage-popover-link { color: #4A7AFF; border-top-color: rgba(255,255,255,0.07); }

/* ── Dropdown panel system ── */
.hd-panel {
  background: #fff;
  border-radius: 1.0417rem;
  box-shadow: 0 4px 6px -1px rgba(0,0,0,0.06), 0 12px 28px rgba(0,0,0,0.12), 0 0 0 1px rgba(0,0,0,0.04);
  overflow: hidden;
  padding: 0.4167rem;
}
:global(.dark) .hd-panel {
  background: #2C2F3D;
  box-shadow: 0 12px 36px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.08), inset 0 1px 0 rgba(255,255,255,0.05);
}

.hd-section-label {
  padding: 0.5rem 0.75rem 0.3rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: rgba(105,105,105,0.5);
  letter-spacing: 0.015em;
}
:global(.dark) .hd-section-label { color: rgba(255,255,255,0.3); }

.hd-menu-list { list-style: none; padding: 0; margin: 0; }

.hd-menu-item {
  display: flex;
  align-items: center;
  gap: 0.6944rem;
  width: 100%;
  padding: 0.6111rem 0.75rem;
  border: none;
  border-radius: 0.75rem;
  background: transparent;
  text-align: left;
  font-size: 0.9722rem;
  color: #374151;
  cursor: pointer;
  transition: background 0.12s, color 0.12s;
}
.hd-menu-item:hover { background: rgba(37,99,235,0.06); color: #1d4ed8; }
.hd-menu-item--active { background: rgba(37,99,235,0.08); color: #2563eb; font-weight: 600; }
:global(.dark) .hd-menu-item { color: rgba(255,255,255,0.75); }
:global(.dark) .hd-menu-item:hover { background: rgba(255,255,255,0.06); color: rgba(255,255,255,0.95); }
:global(.dark) .hd-menu-item--active { background: rgba(74,122,255,0.15); color: #4A7AFF; }
.hd-menu-item--danger { color: #dc3545; }
.hd-menu-item--danger:hover { background: rgba(220,53,69,0.06); color: #dc3545; }
:global(.dark) .hd-menu-item--danger { color: #f87171; }
:global(.dark) .hd-menu-item--danger:hover { background: rgba(248,113,113,0.08); color: #f87171; }

.hd-menu-icon {
  width: 1.7rem;
  height: 1.7rem;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: #9ca3af;
}
:global(.dark) .hd-menu-icon { color: rgba(255,255,255,0.38); }
.hd-menu-item:hover .hd-menu-icon,
.hd-menu-item--active .hd-menu-icon { color: currentColor; opacity: 0.8; }

.hd-menu-item-label { min-width: 0; }

.hd-project-avatar {
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  flex-shrink: 0;
  background: #e8eef9;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  color: #2563eb;
}
.hd-menu-item--active .hd-project-avatar { background: rgba(37,99,235,0.12); }
:global(.dark) .hd-project-avatar { background: rgba(255,255,255,0.1); color: #4A7AFF; }

.hd-divider {
  height: 1px;
  background: rgba(0,0,0,0.06);
  margin: 0.3333rem 0.25rem;
}
:global(.dark) .hd-divider { background: rgba(255,255,255,0.07); }

.hd-create-item {
  display: flex;
  align-items: center;
  gap: 0.6944rem;
  width: 100%;
  padding: 0.6111rem 0.75rem;
  border: none;
  border-radius: 0.75rem;
  background: transparent;
  font-size: 0.9722rem;
  font-weight: 500;
  color: #2563eb;
  cursor: pointer;
  transition: background 0.12s;
}
.hd-create-item:hover { background: rgba(37,99,235,0.06); }
:global(.dark) .hd-create-item { color: #4A7AFF; }
:global(.dark) .hd-create-item:hover { background: rgba(74,122,255,0.1); }

.hd-create-icon {
  width: 1.7rem;
  height: 1.7rem;
  border-radius: 50%;
  background: rgba(37,99,235,0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #2563eb;
  flex-shrink: 0;
}
:global(.dark) .hd-create-icon { background: rgba(74,122,255,0.15); color: #4A7AFF; }

.hd-profile-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 0.75rem 0.8333rem;
}
.hd-profile-avatar {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 50%;
  background: linear-gradient(135deg, #2f6df6 0%, #14b8d5 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.9028rem;
  font-weight: 700;
  color: #fff;
  flex-shrink: 0;
  overflow: hidden;
}
.hd-profile-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.hd-profile-name {
  font-size: 0.9722rem;
  font-weight: 600;
  color: #111827;
  line-height: 1.3;
}
:global(.dark) .hd-profile-name { color: rgba(255,255,255,0.92); }
.hd-profile-email {
  font-size: 0.75rem;
  color: rgba(105,105,105,0.6);
  margin-top: 0.1111rem;
}
:global(.dark) .hd-profile-email { color: rgba(255,255,255,0.38); }

.hd-toggle {
  position: relative;
  display: inline-flex;
  width: 2.0833rem;
  height: 1.1111rem;
  border-radius: 9999px;
  background: #e5e7eb;
  flex-shrink: 0;
  transition: background 0.25s;
}
.hd-toggle::after {
  content: '';
  position: absolute;
  left: 0.1389rem;
  top: 0.1389rem;
  width: 0.8333rem;
  height: 0.8333rem;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.25);
  transition: transform 0.25s cubic-bezier(0.16,1,0.3,1);
}
.hd-toggle--on { background: #2563eb; }
.hd-toggle--on::after { transform: translateX(0.9444rem); }
:global(.dark) .hd-toggle { background: rgba(255,255,255,0.12); }
:global(.dark) .hd-toggle--on { background: #2563eb; }
</style>
