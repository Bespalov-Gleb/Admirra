<template>
  <header class="main-bg-color text-white  px-4 sm:px-6 lg:px-8 py-3.5 sticky top-0 z-30">
    <div class="flex items-center justify-between gap-4">
      <!-- Левая часть - Логотип и название -->
      <div class="flex items-center gap-3 flex-shrink-0">
        <!-- Кнопка меню для мобильных -->
        <button
          @click="toggleMobileMenu"
          class="lg:hidden p-2 rounded-lg hover:bg-gray-700 transition-colors"
          aria-label="Открыть меню"
        >
          <Bars3Icon class="w-6 h-6 text-white" />
        </button>
        
        <!-- Логотип -->
         <div class="bg-[#e5e7eb] p-1.5 rounded-lg">
          <logoFull  class="h- w-auto"/>
        </div>
        
        <!-- Название агентства -->
        <div class="hidden lg:block">
          <h1 class="text-sm sm:text-base md:text-lg font-bold text-white uppercase">ТРАФИК АГЕНТСТВО</h1>
          <p class="text-xs text-gray-400 hidden sm:block">отчеты агентства в одном месте</p>
        </div>
      </div>


      <!-- Правая часть - Кнопки и профиль -->
      <div class="flex items-center gap-3 flex-shrink-0 bg-white px-5 py-1.5 rounded-[16px] text">
        <!-- Кнопка "Добавить проект" -->
        <button
          @click="showAddProjectModal = true"
          class="flex items-center gap-2 px-4 py-1.5 bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
        >
        <AddProjectArrow />

          <span class="text-sm font-medium text-white">Добавить проект</span>
        </button>
        
        <!-- Уведомления -->
        <div class="relative">
          <button
            data-notifications-button
            @click="toggleNotifications"
            class="relative p-2 rounded-lg "
            aria-label="Уведомления"
          >
            <BellIcon class="w-5 h-5 text-main-bg-color" />
            <span
              v-if="unreadCount > 0"
              class="absolute top-0 right-0 w-[16px] h-[16px] bg-[#1c274c] text-white text-[10px] font-medium rounded-[4px] flex items-center justify-center"
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
        <div class="relative bg-[#E5E7EB] rounded-md">
          <button
            data-profile-button
            @click="toggleProfileMenu"
            class="p-2 rounded-lg"
          >
            <ProfileHeader class="w-5 h-5 text-main-bg-color" />
          </button>

          <!-- Выпадающее меню профиля -->
          <Teleport to="body">
            <div
              v-if="isProfileMenuOpen"
              ref="profileMenuRef"
              :style="getProfileMenuStyle()"
              class="dropdown-menu fixed w-72 bg-white rounded-lg shadow-lg border border-gray-200 py-2 z-50"
              @click.stop
            >
              <div class="px-4 py-3 border-b border-gray-200">
                <p class="text-sm font-semibold text-gray-900">Имя Фамилия</p>
                <p class="text-xs text-gray-500 mt-1">email@example.com</p>
              </div>
              
              <!-- Переключатель темной темы -->
              <div class="flex items-center justify-between px-4 py-2 hover:bg-gray-100 transition-colors">
                <div class="flex items-center gap-2">
                  <MoonIcon class="w-5 h-5 text-gray-600" />
                  <span class="text-sm text-gray-700">Темная тема</span>
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

  <!-- Модалка добавления проекта -->
  <AddProjectModal
    v-model:is-open="showAddProjectModal"
    @submit="handleAddProject"
  />
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { Teleport } from 'vue'
import {
  UserIcon,
  Cog6ToothIcon,
  ArrowRightOnRectangleIcon,
  Bars3Icon,
  BellIcon,
  XMarkIcon,
  MoonIcon
} from '@heroicons/vue/24/outline'
import logoFull from '../assets/icons/logo-header.vue'
import AddProjectArrow   from '../assets/icons/add-project-header.vue'
import ProfileHeader   from '../assets/icons/profile-header.vue'
import ConfirmModal from './ConfirmModal.vue'
import AddProjectModal from './AddProjectModal.vue'
import { useSidebar } from '../composables/useSidebar'
import { useAuth } from '../composables/useAuth'
import { useTheme } from '../composables/useTheme'

const router = useRouter()
const { toggleMobileMenu } = useSidebar()
const { removeToken } = useAuth()
const { isDarkMode, toggleTheme } = useTheme()
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
  removeToken()
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

const handleAddProject = (projectData) => {
  console.log('New project:', projectData)
  // Здесь можно добавить логику добавления проекта
  // Например, отправка на сервер или добавление в список проектов
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
