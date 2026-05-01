<template>
  <header class="h-[76px] flex items-stretch bg-white dark:bg-[#2C2F3D] border-b border-black/5 dark:border-white/10 flex-shrink-0">
    <div class="flex-1 flex items-center px-[25px] py-[5px] gap-4 min-w-0">

      <!-- Left: Project selector -->
      <div class="relative flex-shrink-0" ref="projectMenuRef">
        <button
          @click="toggleProjectMenu"
          class="flex min-h-[46px] items-center gap-5 rounded-[12px] bg-[#f5f7f9] px-[15px] py-[10px] text-left transition-all duration-500 hover:bg-[#ecf3fe] dark:bg-white/10 dark:hover:bg-white/15"
        >
          <div class="w-9 h-9 rounded-full overflow-hidden flex-shrink-0 bg-gray-100">
            <img class="w-full h-full object-cover" src="/admirra/img/avatars/avatar-36x36.png" alt="#" />
          </div>
          <div class="hidden min-w-[90px] flex-col gap-[3px] text-left xl:flex">
            <div class="text-[14px] font-medium leading-none text-[#515151] dark:text-gray-100">{{ headerProjectName }}</div>
            <div class="pt-px text-[10px] leading-none text-[rgba(105,105,105,0.6)] dark:text-gray-400">Отчеты агентства в одном месте</div>
          </div>
          <span class="ml-auto flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-white transition-all duration-500 dark:bg-white/10">
            <svg class="w-[9px] h-[9px] text-gray-500 transition-transform duration-500" :class="isProjectMenuOpen ? 'rotate-180' : ''" fill="none" viewBox="0 0 10 6">
              <path d="M1 1l4 4 4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </span>
        </button>

        <!-- Project dropdown -->
        <Transition name="dropdown">
          <div
            v-if="isProjectMenuOpen"
            class="absolute left-1/2 top-full z-50 mt-2 min-w-[360px] -translate-x-1/2 px-[30px] pb-[30px] pt-[10px]"
          >
            <div class="relative rounded-[12px] bg-white shadow-[0_0_15px_rgba(0,0,0,0.1)] after:absolute after:left-1/2 after:top-0 after:h-[14px] after:w-[14px] after:-translate-x-1/2 after:-translate-y-1/2 after:rotate-45 after:bg-white dark:bg-[#2C2F3D] dark:after:bg-[#2C2F3D]">
              <div class="px-4 pb-2 pt-4 font-medium">
                <div class="px-4 py-2 text-[12px] font-medium uppercase text-[rgba(105,105,105,0.56)] dark:text-gray-400">Мои проекты</div>
                <ul class="mb-2 text-[14px]">
                  <li>
                    <button
                      @click="handleProjectSelect(null)"
                      :class="['w-full rounded-[12px] px-4 py-2.5 text-left transition-colors', !currentProjectId ? 'bg-[#ecf3fe] font-semibold text-[#2563eb]' : 'text-gray-700 hover:bg-[#f5f7f9] dark:text-gray-300 dark:hover:bg-white/5']"
                    >Все проекты</button>
                  </li>
                  <li v-for="project in projects" :key="project.id">
                    <button
                      @click="handleProjectSelect(project.id)"
                      :class="['w-full rounded-[12px] px-4 py-2.5 text-left transition-colors', currentProjectId === project.id ? 'bg-[#ecf3fe] font-semibold text-[#2563eb]' : 'text-gray-700 hover:bg-[#f5f7f9] dark:text-gray-300 dark:hover:bg-white/5']"
                    >{{ project.name }}</button>
                  </li>
                </ul>
                <button
                  @click="router.push('/projects/create'); isProjectMenuOpen = false"
                  class="flex w-full items-center gap-2 rounded-[12px] px-4 py-3 text-[13px] font-medium text-[#2563eb] transition-colors hover:bg-[#ecf3fe]"
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
      <div class="hidden 2xl:flex items-center gap-4 pl-4 border-l border-black/5 dark:border-white/10">
        <div>
          <div class="text-[13px] font-medium text-gray-500 dark:text-gray-400">
            Ваш тариф: <b class="font-bold text-gray-800 dark:text-gray-100">{{ subscription.planName }}</b>
          </div>
          <div v-if="subscription.expiresAtLabel" class="text-[11px] text-gray-400">
            Действует до {{ subscription.expiresAtLabel }}
          </div>
        </div>
        <button
          @click="router.push('/tariffs')"
          class="flex min-h-[46px] flex-shrink-0 items-center justify-center rounded-[12px] border border-[#e1e1e1] px-[17px] py-2 text-[13px] font-medium leading-none transition-all duration-500 hover:border-[#2563eb]"
        >
          <span class="bg-[linear-gradient(270deg,#06b5d4_0.35%,#1f9de4_32.08%,#2563eb_96.51%)] bg-clip-text text-transparent">
            Продлить
          </span>
        </button>
      </div>

      <!-- Spacer -->
      <div class="flex-1" />

      <!-- Right actions -->
      <div class="flex items-center gap-2">

        <!-- "Предложить идею" (lg+) -->
        <button
          @click="router.push('/contact')"
          class="group relative hidden min-h-[46px] items-center justify-center overflow-hidden rounded-[12px] bg-[linear-gradient(270deg,#06b5d4_0.35%,#1f9de4_32.08%,#2563eb_96.51%)] px-[17px] py-2 text-center text-[13px] font-medium leading-none text-white transition-all duration-700 after:absolute after:inset-0 after:rounded-[12px] after:bg-[linear-gradient(270deg,#38e1ff_0.35%,#4abeff_32.08%,#5187ff_96.51%)] after:opacity-0 after:transition-opacity after:duration-1000 hover:scale-[1.03] hover:text-white hover:after:opacity-100 active:scale-[0.97] xl:inline-flex"
        >
          <span class="relative z-[1] flex items-center gap-2.5">
            Предложить идею
            <svg class="h-4 w-4 fill-white" viewBox="0 0 24 24">
              <use href="/admirra/img/svg/sprite.svg#idea"></use>
            </svg>
          </span>
        </button>

        <!-- Upgrade button (xxxl only = 2xl+) -->
        <button
          @click="router.push('/projects/create')"
          class="hidden min-h-[46px] items-center justify-center rounded-[12px] bg-[#2563eb] px-[17px] py-2 text-[13px] font-medium leading-none text-white transition-all duration-500 hover:scale-[1.03] hover:bg-[#5187ff] active:scale-[0.97] 2xl:flex"
        >
          <span class="flex items-center gap-2.5">
            Перейти на тариф Старт
            <span class="grid h-[15px] w-[15px] place-items-center rounded-full bg-black/20 text-[10px] font-medium leading-none">
              <span class="-translate-y-px">+</span>
            </span>
          </span>
        </button>

        <!-- Notifications bell -->
        <div class="relative">
          <button
            data-notifications-button
            @click="toggleNotifications"
            class="relative flex min-h-[46px] min-w-[46px] items-center justify-center rounded-[12px] bg-[#f5f7f9] transition-colors duration-500 hover:bg-[#ecf3fe] dark:bg-white/10 dark:hover:bg-white/15"
          >
            <svg class="h-[17px] w-[17px] fill-[#afafaf]">
              <use href="/admirra/img/svg/sprite.svg#bell"></use>
            </svg>
            <span
              v-if="unreadCount > 0"
              class="absolute left-1/2 top-1/2 flex min-h-[13px] min-w-[13px] items-center justify-center rounded-[2px] bg-[#82d944] px-[3px] text-[8px] leading-[13px] text-white"
            >{{ unreadCount }}</span>
          </button>

          <Transition name="dropdown">
            <div
              v-if="showNotifications"
              class="absolute top-full z-50 min-w-[360px] w-[calc(100%+80px)] right-[-30px] px-[30px] pb-[30px] pt-[10px]"
            >
              <div class="relative rounded-[12px] bg-white shadow-[0_0_15px_rgba(0,0,0,0.1)] after:absolute after:bottom-full after:right-8 after:border-x-[7px] after:border-b-[7px] after:border-x-transparent after:border-b-white dark:bg-[#2C2F3D] dark:after:border-b-[#2C2F3D]">
                <div class="p-4 text-[16px] font-semibold text-gray-800 dark:text-gray-100">Уведомления</div>
                <hr class="border-black/5 dark:border-white/10" />
                <div v-if="notifications.length === 0" class="p-5 text-center text-[12px] text-[#696969] dark:text-gray-400">Нет уведомлений</div>
                <div v-else class="max-h-80 overflow-y-auto py-2">
                  <a
                    v-for="notification in notifications"
                    :key="notification.id"
                    @click.prevent="markAsRead(notification.id)"
                    href="#"
                    :class="['flex w-full items-center px-0 py-1 text-[14px] transition-colors hover:text-[#2563eb]', !notification.is_read ? 'text-[#2563eb]' : 'text-[#696969] dark:text-gray-300']"
                  >
                    <div class="flex h-[44px] w-[44px] flex-shrink-0 items-center justify-center">
                      <svg class="h-5 w-5 fill-[#afafaf]">
                        <use href="/admirra/img/svg/sprite.svg#bell"></use>
                      </svg>
                    </div>
                    <div class="min-w-0 flex-1 pr-3">
                      <div class="font-medium leading-snug">{{ notification.title }}</div>
                      <div v-if="notification.body" class="mt-1 text-[11px] leading-snug text-[#696969]/75">{{ notification.body }}</div>
                      <div class="mt-1 text-[11px] text-[#696969]/75">{{ formatTime(notification.created_at) }}</div>
                    </div>
                    <div v-if="!notification.is_read" class="mr-4 h-2 w-2 flex-shrink-0 rounded-full bg-[#2563eb]" />
                  </a>
                </div>
                <template v-if="notifications.length > 0 && unreadCount > 0">
                  <hr class="border-black/5 dark:border-white/10" />
                  <div class="p-3 text-center">
                    <button @click.prevent="markAllAsRead" class="text-[12px] font-medium text-[#2563eb] hover:underline">
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
            class="flex min-h-[46px] items-center gap-5 rounded-[12px] bg-[#f5f7f9] px-[15px] py-[10px] text-left transition-all duration-500 hover:bg-[#ecf3fe] dark:bg-white/10 dark:hover:bg-white/15"
          >
            <div class="h-[30px] w-[30px] flex-shrink-0 overflow-hidden rounded-full bg-[#ecf3fe] dark:bg-white/10">
              <img class="h-full w-full object-cover" src="/admirra/img/avatars/avatar-30x30.png" alt="#" />
            </div>
            <span class="hidden max-w-[150px] truncate text-[14px] font-medium text-[#515151] dark:text-gray-100 md:block">{{ displayName }}</span>
            <span class="ml-auto flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-white transition-all duration-500 dark:bg-white/10">
              <svg class="h-[9px] w-[9px] text-gray-500 transition-transform duration-500" :class="isProfileMenuOpen ? 'rotate-180' : ''" fill="none" viewBox="0 0 10 6">
                <path d="M1 1l4 4 4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </span>
          </button>

          <Transition name="dropdown">
            <div
              v-if="isProfileMenuOpen"
              class="absolute top-full z-50 min-w-[360px] w-[calc(100%+80px)] right-[-30px] px-[30px] pb-[30px] pt-[10px]"
            >
              <div class="relative rounded-[12px] bg-white shadow-[0_0_15px_rgba(0,0,0,0.1)] after:absolute after:bottom-full after:right-8 after:border-x-[7px] after:border-b-[7px] after:border-x-transparent after:border-b-white dark:bg-[#2C2F3D] dark:after:border-b-[#2C2F3D]">
                <div class="p-4">
                  <div class="mb-1 text-[15px] font-semibold text-gray-800 dark:text-gray-100">{{ displayName }}</div>
                  <div class="text-[12px] text-[rgba(105,105,105,0.75)] dark:text-gray-400">{{ user?.email }}</div>
                </div>
                <hr class="border-black/5 dark:border-white/10" />
                <div class="py-3">
                  <button
                    @click.prevent="toggleTheme"
                    class="flex w-full items-center py-1 text-[14px] text-[#696969] transition-colors hover:text-[#2563eb] dark:text-gray-300 dark:hover:text-[#4A7AFF]"
                  >
                    <span class="flex h-[44px] w-[44px] items-center justify-center">
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
                    class="flex w-full items-center py-1 text-[14px] text-[#696969] transition-colors hover:text-[#2563eb] dark:text-gray-300 dark:hover:text-[#4A7AFF]"
                  >
                    <span class="flex h-[44px] w-[44px] items-center justify-center">
                      <svg class="h-5 w-5 fill-none stroke-[#afafaf]">
                        <use href="/admirra/img/svg/sprite.svg#user"></use>
                      </svg>
                    </span>
                    <span class="pr-3">Профиль</span>
                  </button>
                  <button
                    @click="router.push('/settings'); closeProfileMenu()"
                    class="flex w-full items-center py-1 text-[14px] text-[#696969] transition-colors hover:text-[#2563eb] dark:text-gray-300 dark:hover:text-[#4A7AFF]"
                  >
                    <span class="flex h-[44px] w-[44px] items-center justify-center">
                      <svg class="h-5 w-5 fill-[#afafaf]">
                        <use href="/admirra/img/svg/sprite.svg#setting"></use>
                      </svg>
                    </span>
                    <span class="pr-3">Настройки</span>
                  </button>
                  <button
                    @click="handleLogoutClick"
                    class="flex w-full items-center py-1 text-[14px] text-[#dc3545] transition-colors hover:text-[#2563eb]"
                  >
                    <span class="flex h-[44px] w-[44px] items-center justify-center">
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

        <!-- Burger (mobile, hidden on lg+) -->
        <button
          @click="toggleMobileMenu"
          :class="[
            'flex h-[46px] w-[46px] flex-shrink-0 items-center justify-center rounded-[12px] bg-[#f5f7f9] transition-colors duration-500 hover:bg-[#ecf3fe] dark:bg-white/10 dark:hover:bg-white/15 min-[1920px]:hidden',
            isMobileMenuOpen ? 'is-active' : '',
          ]"
        >
          <span class="burger-lines relative block h-[15px] w-6">
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

const router = useRouter()
const { isMobileMenuOpen, toggleMobileMenu } = useSidebar()
const { user, forceLogout } = useAuth()
const { isDarkMode, toggleTheme } = useTheme()
const { projects, currentProjectId, currentProjectName, fetchProjects, setCurrentProject } = useProjects()

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

const handleLogout = () => {
  forceLogout()
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
  transform: translateY(-4px);
}

.burger-line {
  position: absolute;
  left: 0;
  height: 1px;
  border-radius: 999px;
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
  top: 7px;
  transform: rotate(-45deg);
}

.is-active .burger-line-center {
  left: 0;
  top: 7px;
  width: 100%;
  transform: rotate(45deg);
}

.is-active .burger-line-bottom {
  opacity: 0;
}
</style>
