<template>
  <header class="header">
    <div class="header__inner">
      <div class="header__content">
        <div class="row gy-2">
          <div class="col-auto">
            <div class="row gy-2 align-items-center">
              <div class="col-auto">
                <div class="dropdown" ref="projectMenuRef">
                  <button class="dropdown-head" @click="toggleProjectMenu">
                    <div class="avatar-36x36"><img class="img-cover" :src="'/admirra/img/avatars/avatar-36x36.png'" alt="#" /></div>
                    <div class="dropdown-head__info">
                      <div>{{ currentProjectName }}</div>
                      <div class="_subtext">Отчеты агентства в одном месте</div>
                    </div>
                    <div class="circle-arrow"><svg><use href="/admirra/img/svg/sprite.svg#arrow"></use></svg></div>
                  </button>
                  <div v-if="isProjectMenuOpen" class="dropdown-body" style="display:block">
                    <div class="dropdown-block pt-4 pb-2 weight-500">
                      <h6 class="text-12 uppercase gray56 px-4 py-2">Мои проекты</h6>
                      <ul class="dropdown-menu text-14 mb-2">
                        <li><a class="dropdown-menu__link" :class="{ active: !currentProjectId }" href="#" @click.prevent="handleProjectSelect(null)"><span>Все проекты</span></a></li>
                        <li v-for="project in projects" :key="project.id">
                          <a class="dropdown-menu__link" :class="{ active: currentProjectId === project.id }" href="#" @click.prevent="handleProjectSelect(project.id)"><span>{{ project.name }}</span></a>
                        </li>
                      </ul>
                      <a class="dropdown-link" href="#" @click.prevent="router.push('/projects/create'); isProjectMenuOpen = false">
                        <svg class="dropdown-link__icon _stroke"><use href="/admirra/img/svg/sprite.svg#plus"></use></svg>
                        <span>Создать новый проект</span>
                      </a>
                    </div>
                  </div>
                </div>
              </div>
              <div class="col-auto d-none d-xxl-block">
                <div class="d-flex align-items-center">
                  <div class="px-4">
                    <div class="mb-1 weight-500 gray500">Ваш тариф: <b class="weight-700">{{ subscription.planName }}</b></div>
                    <div class="text-10 gray60" v-if="subscription.expiresAtLabel">Действует до {{ subscription.expiresAtLabel }}</div>
                  </div>
                  <div class="ps-2 ms-1">
                    <a class="btn _outline-primary" href="#" @click.prevent="router.push('/tariffs')"><div class="btn__inner"><span class="btn__text">Продлить</span></div></a>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="col-auto align-self-center ms-auto">
            <div class="row gy-2 align-items-center">
              <div class="col-auto d-none d-lg-block">
                <a class="btn" href="#" @click.prevent="router.push('/contact')">
                  <div class="btn__inner"><span class="btn__text">Предложить идею</span><div class="btn__icon"><svg><use href="/admirra/img/svg/sprite.svg#idea"></use></svg></div></div>
                </a>
              </div>
              <div class="col-auto d-none d-xxxl-block">
                <a class="btn _primary" href="#" @click.prevent="router.push('/projects/create')">
                  <div class="btn__inner"><span class="btn__text">Перейти на тариф Старт</span><div class="btn__icon-plus">+</div></div>
                </a>
              </div>
              <div class="col-auto">
                <div class="dropdown">
                  <button class="dropdown-head _no-style" data-notifications-button @click="toggleNotifications">
                    <div class="btn-ui">
                      <div class="btn-ui__icon"><svg><use href="/admirra/img/svg/sprite.svg#bell"></use></svg></div>
                      <div v-if="unreadCount > 0" class="btn-ui__helper">{{ unreadCount }}</div>
                    </div>
                  </button>
                  <div v-if="showNotifications" class="dropdown-body _right" style="display:block">
                    <div class="dropdown-block">
                      <div class="p-4 weight-600 text-16">Уведомления</div>
                      <hr class="hr-line" />
                      <div v-if="notifications.length === 0" class="p-5 text-center text-12 gray">Нет уведомлений</div>
                      <div v-else class="py-2">
                        <a
                          v-for="notification in notifications"
                          :key="notification.id"
                          class="dropdown-menu-item"
                          :class="{ '_unread': !notification.is_read }"
                          href="#"
                          @click.prevent="markAsRead(notification.id)"
                        >
                          <div class="dropdown-menu-item__icon"><svg><use href="/admirra/img/svg/sprite.svg#bell"></use></svg></div>
                          <div class="pe-3">
                            <div>{{ notification.title }}</div>
                            <div v-if="notification.body" class="text-11 gray75 mt-1">{{ notification.body }}</div>
                            <div class="text-11 gray75 mt-1">{{ formatTime(notification.created_at) }}</div>
                          </div>
                        </a>
                      </div>
                      <hr v-if="notifications.length > 0 && unreadCount > 0" class="hr-line" />
                      <div v-if="unreadCount > 0" class="p-3 text-center">
                        <a href="#" class="text-12 weight-500" @click.prevent="markAllAsRead">Отметить все как прочитанные</a>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div class="col-auto">
                <div class="dropdown _normal">
                  <button class="dropdown-head" data-profile-button @click="toggleProfileMenu">
                    <div class="avatar-30x30"><div class="img-cover d-flex align-items-center justify-content-center bg-light"><ProfileHeader class="w-4 h-4 text-[#2E6BFF]" /></div></div>
                    <div class="dropdown-head__info d-none d-md-flex">{{ displayName }}</div>
                    <div class="circle-arrow"><svg><use href="/admirra/img/svg/sprite.svg#arrow"></use></svg></div>
                  </button>
                  <div v-if="isProfileMenuOpen" class="dropdown-body _right" style="display:block">
                    <div class="dropdown-block">
                      <div class="p-4">
                        <div class="text-15 weight-600 mb-1">{{ displayName }}</div>
                        <div class="text-12 gray75">{{ user?.email }}</div>
                      </div>
                      <hr class="hr-line" />
                      <div class="py-3">
                        <a class="dropdown-menu-item _darkmode" href="#" @click.prevent="toggleTheme">
                          <div class="dropdown-menu-item__icon"><svg class="_moon"><use href="/admirra/img/svg/sprite.svg#moon"></use></svg></div>
                          <span class="pe-3">{{ isDarkMode ? 'Светлая тема' : 'Темная тема' }}</span>
                        </a>
                        <a class="dropdown-menu-item" href="#" @click.prevent="router.push('/profile'); closeProfileMenu()">
                          <div class="dropdown-menu-item__icon"><svg class="_stroke"><use href="/admirra/img/svg/sprite.svg#user"></use></svg></div>
                          <span class="pe-3">Профиль</span>
                        </a>
                        <a class="dropdown-menu-item" href="#" @click.prevent="router.push('/settings'); closeProfileMenu()">
                          <div class="dropdown-menu-item__icon"><svg><use href="/admirra/img/svg/sprite.svg#setting"></use></svg></div>
                          <span class="pe-3">Настройки</span>
                        </a>
                        <a class="dropdown-menu-item _danger" href="#" @click.prevent="handleLogoutClick">
                          <div class="dropdown-menu-item__icon"><svg class="_exit"><use href="/admirra/img/svg/sprite.svg#exit"></use></svg></div>
                          <span class="pe-3">Выход</span>
                        </a>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div class="col-auto d-xxxl-none">
                <div class="burger" @click="toggleMobileMenu">
                  <div class="burger__icon"><div class="_top"></div><div class="_center"></div><div class="_bottom"></div></div>
                </div>
              </div>
            </div>
          </div>
        </div>
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
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api/axios'
import ProfileHeader from '../assets/icons/profile-header.vue'
import ConfirmModal from './ConfirmModal.vue'
import { useSidebar } from '../composables/useSidebar'
import { useAuth } from '../composables/useAuth'
import { useTheme } from '../composables/useTheme'
import { useProjects } from '../composables/useProjects'

const router = useRouter()
const { toggleMobileMenu } = useSidebar()
const { user, forceLogout } = useAuth()
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

// --- Уведомления (real API) ---
const notifications = ref([])
const unreadCount = computed(() => notifications.value.filter(n => !n.is_read).length)

let notificationsPollTimer = null

const fetchNotifications = async () => {
  try {
    const { data } = await api.get('notifications/')
    notifications.value = data
  } catch (e) {
    // Тихо игнорируем (пользователь может быть не авторизован)
  }
}

const formatTime = (isoStr) => {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

// --- Подписка ---
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

// --- Дропдауны ---
const toggleProfileMenu = () => {
  isProfileMenuOpen.value = !isProfileMenuOpen.value
  if (isProfileMenuOpen.value) showNotifications.value = false
}

const toggleNotifications = () => {
  showNotifications.value = !showNotifications.value
  if (showNotifications.value) isProfileMenuOpen.value = false
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

const markAsRead = async (id) => {
  const notification = notifications.value.find(n => n.id === id)
  if (notification && !notification.is_read) {
    notification.is_read = true
    try {
      await api.post(`notifications/${id}/read`)
    } catch (e) { /* ignore */ }
  }
}

const markAllAsRead = async () => {
  notifications.value.forEach(n => { n.is_read = true })
  try {
    await api.post('notifications/read-all')
  } catch (e) { /* ignore */ }
}

// Закрытие dropdown при клике вне его
const handleClickOutside = (event) => {
  const target = event.target

  if (isProfileMenuOpen.value) {
    const profileButton = target.closest('[data-profile-button]')
    const profileDropdown = target.closest('.dropdown-body')
    if (!profileButton && !profileDropdown) {
      closeProfileMenu()
    }
  }

  if (showNotifications.value) {
    const notificationsButton = target.closest('[data-notifications-button]')
    const notificationsDropdown = target.closest('.dropdown-body')
    if (!notificationsButton && !notificationsDropdown) {
      showNotifications.value = false
    }
  }

  if (isProjectMenuOpen.value && projectMenuRef.value) {
    if (!projectMenuRef.value.contains(target)) {
      isProjectMenuOpen.value = false
    }
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
