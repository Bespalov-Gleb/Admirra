<template>
  <header class="header">
    <div class="header__inner">
      <!-- Левый блок: логотип + кнопка сворачивания сайдбара -->
      <div class="header__aside">
        <router-link class="logo" to="/main">AdMirra</router-link>
        <button class="header__aside-btn d-none d-xxxl-block" @click="$emit('toggle-sidebar-size')">
          <div class="circle-arrow _light">
            <svg><use href="/admirra/img/svg/sprite.svg#arrow"></use></svg>
          </div>
        </button>
      </div>

      <!-- Основной контент хедера -->
      <div class="header__content">
        <div class="row gy-2">
          <!-- Левая часть: проект + тариф -->
          <div class="col-auto">
            <div class="row gy-2 align-items-center">
              <div class="col-auto">
                <div class="dropdown" ref="projectMenuRef">
                  <button class="dropdown-head" @click="toggleProjectMenu">
                    <div class="avatar-36x36">
                      <img class="img-cover" src="/admirra/img/avatars/avatar-36x36.png" alt="#" />
                    </div>
                    <div class="dropdown-head__info">
                      <div>{{ currentProjectName }}</div>
                      <div class="_subtext">Отчеты агентства в одном месте</div>
                    </div>
                    <div class="circle-arrow">
                      <svg><use href="/admirra/img/svg/sprite.svg#arrow"></use></svg>
                    </div>
                  </button>
                  <div v-if="isProjectMenuOpen" class="dropdown-body" style="display:block">
                    <div class="dropdown-block pt-4 pb-2 weight-500">
                      <h6 class="text-12 uppercase gray56 px-4 py-2">Мои проекты</h6>
                      <ul class="dropdown-menu text-14 mb-2">
                        <li>
                          <a class="dropdown-menu__link" :class="{ active: !currentProjectId }" href="#"
                            @click.prevent="handleProjectSelect(null)">
                            <span>Все проекты</span>
                          </a>
                        </li>
                        <li v-for="project in projects" :key="project.id">
                          <a class="dropdown-menu__link" :class="{ active: currentProjectId === project.id }" href="#"
                            @click.prevent="handleProjectSelect(project.id)">
                            <span>{{ project.name }}</span>
                          </a>
                        </li>
                      </ul>
                      <a class="dropdown-link" href="#"
                        @click.prevent="router.push('/create'); isProjectMenuOpen = false">
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
                    <div class="mb-1 weight-500 gray500">
                      Ваш тариф: <b class="weight-700">{{ subscription.planName }}</b>
                    </div>
                    <div v-if="subscription.expiresAtLabel" class="text-10 gray60">
                      Действует до {{ subscription.expiresAtLabel }}
                    </div>
                  </div>
                  <div class="ps-2 ms-1">
                    <a class="btn _outline-primary" href="#" @click.prevent="router.push('/tariffs')">
                      <div class="btn__inner"><span class="btn__text">Продлить</span></div>
                    </a>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Правая часть: кнопки + уведомления + профиль -->
          <div class="col-auto align-self-center ms-auto">
            <div class="row gy-2 align-items-center">
              <div class="col-auto d-none d-lg-block">
                <a class="btn _primary" href="#" @click.prevent="router.push('/contact')">
                  <div class="btn__inner">
                    <span class="btn__text" style="color:#fff">Предложить идею</span>
                    <div class="btn__icon"><svg><use href="/admirra/img/svg/sprite.svg#idea"></use></svg></div>
                  </div>
                </a>
              </div>

              <!-- Уведомления -->
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
                      <div v-if="notifications.length === 0" class="p-5 text-center text-12 gray">
                        Нет уведомлений
                      </div>
                      <div v-else class="py-2">
                        <a v-for="notification in notifications" :key="notification.id"
                          class="dropdown-menu-item" :class="{ '_unread': !notification.is_read }"
                          href="#" @click.prevent="markAsRead(notification.id)">
                          <div class="dropdown-menu-item__icon">
                            <svg><use href="/admirra/img/svg/sprite.svg#bell"></use></svg>
                          </div>
                          <div class="pe-3">
                            <div>{{ notification.title }}</div>
                            <div v-if="notification.body" class="text-11 gray75 mt-1">{{ notification.body }}</div>
                            <div class="text-11 gray75 mt-1">{{ formatTime(notification.created_at) }}</div>
                          </div>
                        </a>
                      </div>
                      <template v-if="notifications.length > 0 && unreadCount > 0">
                        <hr class="hr-line" />
                        <div class="p-3 text-center">
                          <a href="#" class="text-12 weight-500" @click.prevent="markAllAsRead">
                            Отметить все как прочитанные
                          </a>
                        </div>
                      </template>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Профиль -->
              <div class="col-auto">
                <div class="dropdown _normal">
                  <button class="dropdown-head" data-profile-button @click="toggleProfileMenu">
                    <div class="avatar-30x30">
                      <div class="img-cover d-flex align-items-center justify-content-center bg-light">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#2E6BFF" stroke-width="2">
                          <circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/>
                        </svg>
                      </div>
                    </div>
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
                          <div class="dropdown-menu-item__icon">
                            <svg class="_moon"><use href="/admirra/img/svg/sprite.svg#moon"></use></svg>
                          </div>
                          <span class="pe-3">{{ isDarkMode ? 'Светлая тема' : 'Темная тема' }}</span>
                        </a>
                        <a class="dropdown-menu-item" href="#"
                          @click.prevent="router.push('/profile'); closeProfileMenu()">
                          <div class="dropdown-menu-item__icon">
                            <svg class="_stroke"><use href="/admirra/img/svg/sprite.svg#user"></use></svg>
                          </div>
                          <span class="pe-3">Профиль</span>
                        </a>
                        <a class="dropdown-menu-item" href="#"
                          @click.prevent="router.push('/settings'); closeProfileMenu()">
                          <div class="dropdown-menu-item__icon">
                            <svg><use href="/admirra/img/svg/sprite.svg#setting"></use></svg>
                          </div>
                          <span class="pe-3">Настройки</span>
                        </a>
                        <a class="dropdown-menu-item _danger" href="#" @click.prevent="handleLogoutClick">
                          <div class="dropdown-menu-item__icon">
                            <svg class="_exit"><use href="/admirra/img/svg/sprite.svg#exit"></use></svg>
                          </div>
                          <span class="pe-3">Выход</span>
                        </a>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Бургер (мобильное меню) -->
              <div class="col-auto d-xxxl-none">
                <div class="burger" @click="$emit('toggle-mobile-menu')">
                  <div class="burger__icon">
                    <div class="_top"></div>
                    <div class="_center"></div>
                    <div class="_bottom"></div>
                  </div>
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
import api from '../../api/axios'
import ConfirmModal from '../ConfirmModal.vue'
import { useAuth } from '../../composables/useAuth'
import { useTheme } from '../../composables/useTheme'
import { useProjects } from '../../composables/useProjects'

defineEmits(['toggle-sidebar-size', 'toggle-mobile-menu'])

const router = useRouter()
const { user, forceLogout } = useAuth()
const { isDarkMode, toggleTheme } = useTheme()
const { projects, currentProjectId, currentProjectName, fetchProjects, setCurrentProject } = useProjects()

// --- Проект ---
const isProjectMenuOpen = ref(false)
const projectMenuRef = ref(null)

const toggleProjectMenu = () => {
  isProjectMenuOpen.value = !isProjectMenuOpen.value
}

const handleProjectSelect = (id) => {
  setCurrentProject(id)
  isProjectMenuOpen.value = false
}

// --- Подписка ---
const subscription = ref({ planName: '—', expiresAt: null, expiresAtLabel: '' })

const formatDate = (iso) => {
  if (!iso) return ''
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString('ru-RU')
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

// --- Уведомления ---
const notifications = ref([])
const showNotifications = ref(false)
const unreadCount = computed(() => notifications.value.filter(n => !n.is_read).length)
let notificationsPollTimer = null

const fetchNotifications = async () => {
  try {
    const { data } = await api.get('notifications/')
    notifications.value = data
  } catch { /* тихо игнорируем */ }
}

const formatTime = (isoStr) => {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  return Number.isNaN(d.getTime()) ? '' :
    d.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

const markAsRead = async (id) => {
  const n = notifications.value.find(n => n.id === id)
  if (n && !n.is_read) {
    n.is_read = true
    try { await api.post(`notifications/${id}/read`) } catch { /* ignore */ }
  }
}

const markAllAsRead = async () => {
  notifications.value.forEach(n => { n.is_read = true })
  try { await api.post('notifications/read-all') } catch { /* ignore */ }
}

const toggleNotifications = () => {
  showNotifications.value = !showNotifications.value
  if (showNotifications.value) isProfileMenuOpen.value = false
}

// --- Профиль ---
const isProfileMenuOpen = ref(false)
const showLogoutModal = ref(false)

const displayName = computed(() => {
  if (!user.value) return '...'
  if (user.value.first_name || user.value.last_name) {
    return `${user.value.first_name || ''} ${user.value.last_name || ''}`.trim()
  }
  return user.value.username || user.value.email || 'Пользователь'
})

const toggleProfileMenu = () => {
  isProfileMenuOpen.value = !isProfileMenuOpen.value
  if (isProfileMenuOpen.value) showNotifications.value = false
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

// --- Закрытие дропдаунов по клику вне ---
const handleClickOutside = (event) => {
  const target = event.target

  if (isProfileMenuOpen.value) {
    if (!target.closest('[data-profile-button]') && !target.closest('.dropdown-body')) {
      closeProfileMenu()
    }
  }

  if (showNotifications.value) {
    if (!target.closest('[data-notifications-button]') && !target.closest('.dropdown-body')) {
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

<style scoped>
:deep(.header) {
  background-color: var(--bgLayout) !important;
}

/* Сбрасываем "лендинговый" pill-стиль у header__inner */
:deep(.header__inner) {
  max-width: 1920px !important;
  margin: 0 auto !important;
  display: flex !important;
  background: transparent !important;
  border-radius: 0 !important;
  padding: 0 !important;
  min-height: 0 !important;
  column-gap: 0 !important;
}

/* Явный тёмный фон для шапки в обоих режимах проставления класса */
:global(html.darkmode) :deep(.header),
:global(body.darkmode) :deep(.header) {
  background-color: rgba(255, 255, 255, 0.05) !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06) !important;
}

.dropdown-menu__link {
  display: block;
  width: 100%;
  text-align: left;
  background: none;
  border: none;
  cursor: pointer;
}
.dropdown-link {
  background: none;
  border: none;
  width: 100%;
  text-align: left;
  cursor: pointer;
  display: flex;
  align-items: center;
}
</style>
