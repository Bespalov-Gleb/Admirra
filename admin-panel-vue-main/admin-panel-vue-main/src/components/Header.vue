<template>
  <header class="bg-white border-b border-gray-200 px-4 sm:px-6 lg:px-8 py-4 sticky top-0 z-30">
    <div class="flex items-center justify-between gap-4">
      <!-- Левая часть - Логотип и название -->
      <div class="flex items-center gap-3 flex-shrink-0">
        <!-- Кнопка меню для мобильных -->
        <button
          @click="toggleMobileMenu"
          class="lg:hidden p-2 rounded-lg hover:bg-gray-100 transition-colors"
          aria-label="Открыть меню"
        >
          <Bars3Icon class="w-6 h-6 text-gray-600" />
        </button>
        
        <!-- Логотип -->
        <div class="w-10 h-10 rounded-lg bg-gray-200 flex items-center justify-center flex-shrink-0">
          <UserIcon class="w-6 h-6 text-gray-600" />
        </div>
        
        <!-- Название агентства -->
        <div>
          <h1 class="text-sm sm:text-base md:text-lg font-bold text-gray-900 uppercase">ТРАФИК АГЕНТСТВО</h1>
          <p class="text-xs text-gray-500 hidden sm:block">отчеты агентства в одном месте</p>
        </div>
      </div>


      <!-- Правая часть - Уведомления и профиль -->
      <div class="flex items-center gap-4 flex-shrink-0">
        <button
          @click="showAddProjectModal = true"
          class="hidden lg:flex items-center gap-3 px-6 py-3 bg-white border border-gray-300 rounded-full hover:bg-gray-50 transition-colors"
        >
          <div class="w-8 h-8 rounded-lg bg-gray-200 flex items-center justify-center">
            <LinkIcon class="w-5 h-5 text-gray-600" />
          </div>
          <span class="text-sm font-medium text-gray-900">Добавить новый проект</span>
          <ChevronRightIcon class="w-5 h-5 text-gray-600" />
        </button>
        <!-- Уведомления -->
        <div class="relative">
          <button
            data-notifications-button
            @click="toggleNotifications"
            class="relative p-2 rounded-lg hover:bg-gray-100 transition-colors"
            aria-label="Уведомления"
          >
            <BellIcon class="w-6 h-6 text-gray-600" />
            <span
              v-if="unreadCount > 0"
              class="absolute top-0 right-0 w-5 h-5 bg-gray-900 text-white text-xs font-medium rounded-full flex items-center justify-center"
            >
              {{ unreadCount }}
            </span>
          </button>

          <!-- Выпадающее меню уведомлений -->
          <Teleport to="body">
            <div
              v-if="showNotifications"
              ref="notificationsRef"
              :style="getNotificationsStyle()"
              class="dropdown-menu fixed w-80 sm:w-96 bg-white rounded-lg shadow-lg border border-gray-200 z-50"
              @click.stop
            >
              <div class="p-4 border-b border-gray-200 flex items-center justify-between">
                <h3 class="text-lg font-semibold text-gray-900">Уведомления</h3>
                <button
                  @click="markAllAsRead"
                  class="text-sm text-blue-600 hover:text-blue-700 font-medium"
                >
                  Отметить все как прочитанные
                </button>
              </div>
              
              <div class="max-h-96 overflow-y-auto">
                <div
                  v-for="notification in notifications"
                  :key="notification.id"
                  @click="markAsRead(notification.id)"
                  class="p-4 border-b border-gray-100 hover:bg-gray-50 transition-colors flex items-start gap-3 cursor-pointer"
                >
                  <div
                    v-if="!notification.read"
                    class="w-2 h-2 bg-blue-600 rounded-full mt-2 flex-shrink-0"
                  ></div>
                  <div v-else class="w-2 h-2 flex-shrink-0"></div>
                  <div class="flex-1 min-w-0">
                    <p class="text-sm font-medium text-gray-900">{{ notification.title }}</p>
                    <p class="text-xs text-gray-500 mt-1">{{ notification.time }}</p>
                  </div>
                  <button
                    @click.stop="removeNotification(notification.id)"
                    class="text-gray-400 hover:text-gray-600 transition-colors flex-shrink-0"
                  >
                    <XMarkIcon class="w-4 h-4" />
                  </button>
                </div>
              </div>
              
              <div class="p-4 border-t border-gray-200">
                <button
                  class="w-full text-sm text-blue-600 hover:text-blue-700 font-medium text-center"
                >
                  Показать все уведомления
                </button>
              </div>
            </div>
          </Teleport>
        </div>

        <!-- Профиль -->
        <div class="relative">
          <button
            data-profile-button
            @click="toggleProfileMenu"
            class="flex items-center gap-2 sm:gap-3 p-2 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <div class="w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-gray-200 flex items-center justify-center">
              <UserIcon class="w-5 h-5 sm:w-6 sm:h-6 text-gray-600" />
            </div>
            <span class="hidden sm:block text-sm font-medium text-gray-900">{{ displayName }}</span>
            <ChevronDownIcon
              :class="[
                'w-4 h-4 sm:w-5 sm:h-5 text-gray-600 transition-transform hidden sm:block',
                isProfileMenuOpen && 'rotate-180'
              ]"
            />
          </button>

          <!-- Выпадающее меню профиля -->
          <Teleport to="body">
            <div
              v-if="isProfileMenuOpen"
              ref="profileMenuRef"
              :style="getProfileMenuStyle()"
              class="dropdown-menu fixed w-56 bg-white rounded-lg shadow-lg border border-gray-200 py-2 z-50"
              @click.stop
            >
              <div class="px-4 py-3 border-b border-gray-200">
                <p class="text-sm font-semibold text-gray-900">{{ displayName }}</p>
                <p class="text-xs text-gray-500 mt-1">{{ user?.email }}</p>
              </div>
              
              <router-link
                to="/profile"
                @click="closeProfileMenu"
                class="flex items-center gap-3 px-4 py-2 hover:bg-gray-100 transition-colors text-sm text-gray-700"
              >
                <UserIcon class="w-5 h-5 text-gray-600" />
                <span>Профиль</span>
              </router-link>
              
              <router-link
                to="/settings"
                @click="closeProfileMenu"
                class="flex items-center gap-3 px-4 py-2 hover:bg-gray-100 transition-colors text-sm text-gray-700"
              >
                <Cog6ToothIcon class="w-5 h-5 text-gray-600" />
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

  <!-- Модалка добавления проекта (Единая) -->
  <UnifiedConnectModal
    v-model:is-open="showAddProjectModal"
    @success="handleConnectSuccess"
  />
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { Teleport } from 'vue'
import {
  UserIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  Cog6ToothIcon,
  ArrowRightOnRectangleIcon,
  Bars3Icon,
  BellIcon,
  LinkIcon,
  XMarkIcon
} from '@heroicons/vue/24/outline'
import ConfirmModal from './ConfirmModal.vue'
import UnifiedConnectModal from './UnifiedConnectModal.vue'
import { useSidebar } from '../composables/useSidebar'
import { useAuth } from '../composables/useAuth'
import { useToaster } from '../composables/useToaster'

const router = useRouter()
const { toggleMobileMenu } = useSidebar()
const { user, removeToken } = useAuth()

const displayName = computed(() => {
  if (!user.value) return 'Загрузка...'
  if (user.value.first_name || user.value.last_name) {
    return `${user.value.first_name || ''} ${user.value.last_name || ''}`.trim()
  }
  return user.value.username || user.value.email
})

const isProfileMenuOpen = ref(false)
const showNotifications = ref(false)
const showLogoutModal = ref(false)
const showAddProjectModal = ref(false)
const profileMenuRef = ref(null)
const notificationsRef = ref(null)
const notificationsButtonRef = ref(null)

const notifications = ref([
  { id: 1, title: 'Новый проект добавлен', time: '5 минут назад', read: false },
  { id: 2, title: 'Обновление статистики', time: '1 час назад', read: false },
  { id: 3, title: 'Новое сообщение от команды', time: '2 часа назад', read: true },
  { id: 4, title: 'Завершен проект "КСИ СТРОЙ"', time: '3 часа назад', read: true }
])

const unreadCount = ref(2)

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

const profileMenuPosition = ref({ top: '0px', right: '0px' })
const notificationsPosition = ref({ top: '0px', right: '0px' })

const getProfileMenuStyle = () => {
  return {
    top: profileMenuPosition.value.top,
    right: profileMenuPosition.value.right
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
  console.log('Logging out from Header...')
  removeToken()
  showLogoutModal.value = false
  router.push('/login')
}

const markAsRead = (id) => {
  const notification = notifications.value.find(n => n.id === id)
  if (notification && !notification.read) {
    notification.read = true
    unreadCount.value = Math.max(0, unreadCount.value - 1)
  }
}

const markAllAsRead = () => {
  notifications.value.forEach(n => {
    if (!n.read) {
      n.read = true
    }
  })
  unreadCount.value = 0
}

const removeNotification = (id) => {
  const notification = notifications.value.find(n => n.id === id)
  if (notification && !notification.read) {
    unreadCount.value = Math.max(0, unreadCount.value - 1)
  }
  notifications.value = notifications.value.filter(n => n.id !== id)
}

const handleConnectSuccess = (data) => {
  console.log('Successfully connected:', data)
  showAddProjectModal.value = false
  const toaster = useToaster()
  toaster.success(`Интеграция ${data.platform} успешно добавлена!`)
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
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>
