<template>
  <div class="space-y-6">
    <!-- Заголовок -->
    <div class="flex items-center justify-between">
      <h1 class="text-2xl sm:text-3xl font-bold text-gray-900">Профиль</h1>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Левая колонка - Аватар и основная информация -->
      <div class="lg:col-span-1">
        <div class="bg-white rounded-lg  p-6">
          <!-- Аватар -->
          <div class="flex flex-col items-center mb-6">
            <div class="relative mb-4">
              <div class="w-24 h-24 sm:w-32 sm:h-32 rounded-full bg-gray-200 flex items-center justify-center overflow-hidden">
                <UserIcon class="w-12 h-12 sm:w-16 sm:h-16 text-gray-600" />
              </div>
              <button
                @click="showAvatarUpload = true"
                class="absolute bottom-0 right-0 w-8 h-8 sm:w-10 sm:h-10 bg-blue-600 rounded-full flex items-center justify-center hover:bg-blue-700 transition-colors shadow-lg"
              >
                <CameraIcon class="w-4 h-4 sm:w-5 sm:h-5 text-white" />
              </button>
            </div>
            <h2 class="text-xl sm:text-2xl font-bold text-gray-900">{{ userData.fullName }}</h2>
            <p class="text-sm text-gray-500 mt-1">{{ userData.email }}</p>
            <span class="mt-2 px-3 py-1 bg-blue-100 text-blue-800 text-xs font-medium rounded-full">
              {{ userData.role }}
            </span>
          </div>

          <!-- Статистика -->
          <div class=" pt-6 space-y-4">
            <div class="flex items-center justify-between">
              <span class="text-sm text-gray-600">Проектов</span>
              <span class="text-lg font-semibold text-gray-900">{{ stats.projects }}</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-sm text-gray-600">Активных</span>
              <span class="text-lg font-semibold text-green-600">{{ stats.active }}</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-sm text-gray-600">Завершенных</span>
              <span class="text-lg font-semibold text-gray-900">{{ stats.completed }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Правая колонка - Детальная информация -->
      <div class="lg:col-span-2 space-y-6">
        <!-- Личная информация -->
        <div class="bg-white rounded-lg p-6">
          <div class="flex items-center justify-between mb-6">
            <h2 class="text-xl font-bold text-gray-900">Личная информация</h2>
            <button
              @click="toggleEditMode"
              class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
            >
              {{ isEditMode ? 'Отмена' : 'Редактировать' }}
            </button>
          </div>

          <div class="space-y-4">
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                v-model="userData.firstName"
                label="Имя"
                placeholder="Введите имя"
                :readonly="!isEditMode"
              />
              <Input
                v-model="userData.lastName"
                label="Фамилия"
                placeholder="Введите фамилию"
                :readonly="!isEditMode"
              />
            </div>

            <Input
              v-model="userData.email"
              label="Email"
              type="email"
              placeholder="Введите email"
              :readonly="true"
            />

            <Input
              v-model="userData.username"
              label="Логин"
              placeholder="Введите логин"
              :readonly="!isEditMode"
            />

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">FinanceToken для Яндекс.Директа</label>
              <textarea
                v-model="userData.yandexFinanceToken"
                :readonly="!isEditMode"
                rows="3"
                placeholder="Вставьте сюда ваш FinanceToken из настроек Яндекс.Директа"
                :class="[
                  'w-full px-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2 transition-colors resize-none font-mono text-xs',
                  isEditMode
                    ? 'border-gray-300 focus:ring-blue-500 focus:border-blue-500 bg-white'
                    : 'border-gray-300 bg-gray-100 cursor-not-allowed'
                ]"
              ></textarea>
              <p class="mt-1 text-xs text-gray-500">
                Токен будет использоваться только для чтения баланса через AccountManagement API.
              </p>
            </div>
          </div>

          <div v-if="isEditMode" class="mt-6 flex justify-end gap-3">
            <button
              @click="cancelEdit"
              class="px-6 py-2.5 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
            >
              Отмена
            </button>
            <button
              @click="saveChanges"
              class="px-6 py-2.5 text-sm font-medium text-white bg-gray-900 rounded-lg hover:bg-gray-800 transition-colors"
            >
              Сохранить изменения
            </button>
          </div>
        </div>

        <!-- Безопасность -->
        <div class="bg-white rounded-lg p-6">
          <h2 class="text-xl font-bold text-gray-900 mb-6">Безопасность</h2>

          <div class="space-y-4">
            <div class="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
              <div>
                <p class="text-sm font-medium text-gray-900">Пароль</p>
                <p class="text-xs text-gray-500 mt-1">Последнее изменение: {{ userData.lastPasswordChange }}</p>
              </div>
              <button
                @click="showChangePasswordModal = true"
                class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Изменить пароль
              </button>
            </div>

            <div class="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
              <div>
                <p class="text-sm font-medium text-gray-900">Двухфакторная аутентификация</p>
                <p class="text-xs text-gray-500 mt-1">
                  {{ userData.twoFactorEnabled ? 'Включена' : 'Отключена' }}
                </p>
              </div>
              <button
                @click="toggleTwoFactor"
                :class="[
                  'px-4 py-2 text-sm font-medium rounded-lg transition-colors',
                  userData.twoFactorEnabled
                    ? 'text-gray-700 bg-white border border-gray-300 hover:bg-gray-50'
                    : 'text-white bg-gray-900 hover:bg-gray-800'
                ]"
              >
                {{ userData.twoFactorEnabled ? 'Отключить' : 'Включить' }}
              </button>
            </div>
          </div>
        </div>

        <!-- Настройки уведомлений (заглушка, пока без бэкенда) -->
        <div class="bg-white rounded-lg p-6">
          <h2 class="text-xl font-bold text-gray-900 mb-6">Уведомления</h2>
          <p class="text-sm text-gray-500">Настройки уведомлений будут доступны в следующей версии.</p>
        </div>
      </div>
    </div>

    <!-- Модалка изменения пароля -->
    <ChangePasswordModal
      :is-open="showChangePasswordModal"
      @update:is-open="showChangePasswordModal = $event"
    />

    <!-- Alert -->
    <Alert
      :show="showAlert"
      type="success"
      :message="alertMessage"
    />

    <!-- Модалка загрузки аватара -->
    <Modal
      v-if="showAvatarUpload"
      :is-open="showAvatarUpload"
      title="Загрузить аватар"
      @close="showAvatarUpload = false"
    >
      <div class="space-y-4">
        <div class="flex flex-col items-center">
          <div class="w-32 h-32 rounded-full bg-gray-200 flex items-center justify-center overflow-hidden mb-4">
            <UserIcon class="w-16 h-16 text-gray-600" />
          </div>
          <input
            type="file"
            accept="image/*"
            @change="handleAvatarUpload"
            class="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-gray-900 file:text-white hover:file:bg-gray-800 cursor-pointer"
          />
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <button
            @click="showAvatarUpload = false"
            class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
          >
            Отмена
          </button>
          <button
            @click="uploadAvatar"
            class="px-4 py-2 text-sm font-medium text-white bg-gray-900 rounded-lg hover:bg-gray-800 transition-colors"
          >
            Загрузить
          </button>
        </div>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { UserIcon } from '@heroicons/vue/24/outline'
import { CameraIcon } from '@heroicons/vue/24/solid'
import Input from '../Settings/components/Input.vue'
import Modal from '../../components/Modal.vue'
import ChangePasswordModal from '../Settings/components/ChangePasswordModal.vue'
import Alert from '../../components/Alert.vue'
import api from '../../api/axios'

const isEditMode = ref(false)
const showChangePasswordModal = ref(false)
const showAvatarUpload = ref(false)
const showAlert = ref(false)
const alertMessage = ref('')

const userData = ref({
  id: null,
  firstName: '',
  lastName: '',
  username: '',
  email: '',
  role: '',
  yandexFinanceToken: '',
  lastPasswordChange: '—',
  twoFactorEnabled: false
})

const stats = ref({
  projects: 0,
  active: 0,
  completed: 0
})

const toggleEditMode = () => {
  isEditMode.value = !isEditMode.value
}

const cancelEdit = () => {
  isEditMode.value = false
  // Перечитываем данные профиля с сервера
  loadProfile()
}

const saveChanges = async () => {
  try {
    const payload = {
      username: userData.value.username || null,
      first_name: userData.value.firstName || null,
      last_name: userData.value.lastName || null,
      yandex_finance_token: userData.value.yandexFinanceToken || null
    }
    const { data } = await api.put('/auth/me', payload)
    // Обновляем локальное состояние из ответа
    userData.value.firstName = data.first_name || ''
    userData.value.lastName = data.last_name || ''
    userData.value.username = data.username || ''
    userData.value.email = data.email
    userData.value.role = data.role
    userData.value.yandexFinanceToken = data.yandex_finance_token || ''

    isEditMode.value = false
    showAlertMessage('Изменения успешно сохранены')
  } catch (e) {
    console.error('Failed to save profile changes:', e)
    showAlertMessage('Не удалось сохранить изменения')
  }
}

const toggleTwoFactor = () => {
  userData.value.twoFactorEnabled = !userData.value.twoFactorEnabled
  showAlertMessage(
    userData.value.twoFactorEnabled
      ? 'Двухфакторная аутентификация включена'
      : 'Двухфакторная аутентификация отключена'
  )
}

const handleAvatarUpload = (event) => {
  const file = event.target.files[0]
  if (file) {
    // Здесь можно добавить логику загрузки
    console.log('Файл выбран:', file.name)
  }
}

const uploadAvatar = () => {
  // Здесь можно добавить логику загрузки
  showAvatarUpload.value = false
  showAlertMessage('Аватар успешно загружен')
}

const showAlertMessage = (message) => {
  alertMessage.value = message
  showAlert.value = true
  setTimeout(() => {
    showAlert.value = false
  }, 3000)
}

const loadProfile = async () => {
  try {
    const { data } = await api.get('/auth/me')
    userData.value.id = data.id
    userData.value.firstName = data.first_name || ''
    userData.value.lastName = data.last_name || ''
    userData.value.username = data.username || ''
    userData.value.email = data.email
    userData.value.role = data.role
    userData.value.yandexFinanceToken = data.yandex_finance_token || ''
  } catch (e) {
    console.error('Failed to load profile:', e)
  }
}

onMounted(() => {
  loadProfile()
})
</script>

