<template>
  <div class="space-y-4 sm:space-y-6">
    <!-- Заголовок с кнопкой создания -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h1 class="text-2xl sm:text-3xl font-bold text-gray-900">Проекты телефонии</h1>
        <p class="text-sm text-gray-600 mt-1">Управление проектами для валидации телефонов</p>
      </div>
      <button
        @click="showCreateModal = true"
        class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        Создать проект
      </button>
    </div>

    <!-- Список проектов -->
    <div v-if="loading" class="text-center py-12">
      <div class="inline-block w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
      <p class="mt-4 text-gray-600">Загрузка проектов...</p>
    </div>

    <div v-else-if="projects.length === 0" class="text-center py-12 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
      <svg class="w-16 h-16 mx-auto text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
      </svg>
      <h3 class="text-lg font-semibold text-gray-900 mb-2">Нет проектов</h3>
      <p class="text-gray-600 mb-4">Создайте первый проект для валидации телефонов</p>
      <button
        @click="showCreateModal = true"
        class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
      >
        Создать проект
      </button>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div
        v-for="project in projects"
        :key="project.id"
        class="bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-shadow p-6"
      >
        <div class="flex items-start justify-between mb-4">
          <div class="flex-1">
            <h3 class="text-lg font-semibold text-gray-900 mb-1">{{ project.name }}</h3>
            <p v-if="project.description" class="text-sm text-gray-600">{{ project.description }}</p>
          </div>
          <div class="flex items-center gap-2">
            <span
              :class="project.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'"
              class="px-2 py-1 text-xs font-medium rounded"
            >
              {{ project.is_active ? 'Активен' : 'Неактивен' }}
            </span>
          </div>
        </div>

        <!-- Настройки проекта -->
        <div class="space-y-2 mb-4">
          <div class="flex items-center gap-2 text-sm text-gray-600">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
            <span v-if="project.webhook_url" class="truncate">{{ project.webhook_url }}</span>
            <span v-else class="text-gray-400">Webhook не настроен</span>
          </div>
          <div class="flex flex-wrap gap-2">
            <span
              v-if="project.enable_social_check"
              class="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded"
            >
              Соцсети
            </span>
            <span
              v-if="project.enable_gosuslugi_check"
              class="px-2 py-1 text-xs bg-purple-100 text-purple-800 rounded"
            >
              Госуслуги
            </span>
            <span
              v-if="project.enable_metrica_export"
              class="px-2 py-1 text-xs bg-yellow-100 text-yellow-800 rounded"
            >
              Метрика
            </span>
          </div>
        </div>

        <!-- Действия -->
        <div class="flex items-center gap-2 pt-4 border-t border-gray-200">
          <button
            @click="editProject(project)"
            class="flex-1 px-3 py-2 text-sm text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
          >
            Редактировать
          </button>
          <button
            @click="viewProject(project)"
            class="flex-1 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 rounded-lg transition-colors"
          >
            Просмотр
          </button>
          <button
            @click="deleteProject(project)"
            class="px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-lg transition-colors"
          >
            Удалить
          </button>
        </div>
      </div>
    </div>

    <!-- Модальное окно создания/редактирования -->
    <div
      v-if="showCreateModal || editingProject"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      @click.self="closeModal"
    >
      <div class="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div class="p-6">
          <h2 class="text-xl font-bold text-gray-900 mb-4">
            {{ editingProject ? 'Редактировать проект' : 'Создать проект' }}
          </h2>

          <form @submit.prevent="saveProject" class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Название проекта <span class="text-red-500">*</span>
              </label>
              <input
                v-model="projectForm.name"
                type="text"
                required
                placeholder="Введите название проекта"
                class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Описание
              </label>
              <textarea
                v-model="projectForm.description"
                rows="3"
                placeholder="Описание проекта (необязательно)"
                class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              ></textarea>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Связать с клиентом (опционально)
              </label>
              <select
                v-model="projectForm.client_id"
                class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option :value="null">Не привязывать</option>
                <option v-for="client in clients" :key="client.id" :value="client.id">
                  {{ client.name }}
                </option>
              </select>
            </div>

            <!-- Настройки выгрузки -->
            <div class="border-t pt-4">
              <h3 class="text-sm font-semibold text-gray-900 mb-3">Настройки выгрузки</h3>
              
              <div class="space-y-3">
                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-1">
                    CRM Webhook URL
                  </label>
                  <input
                    v-model="projectForm.crm_webhook_url"
                    type="url"
                    placeholder="https://example.com/webhook"
                    class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-1">
                    Email получатели (через запятую)
                  </label>
                  <input
                    v-model="emailRecipientsInput"
                    type="text"
                    placeholder="email1@example.com, email2@example.com"
                    class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-1">
                    Telegram Chat ID
                  </label>
                  <input
                    v-model="projectForm.telegram_chat_id"
                    type="text"
                    placeholder="123456789"
                    class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            </div>

            <!-- Настройки валидации -->
            <div class="border-t pt-4">
              <h3 class="text-sm font-semibold text-gray-900 mb-3">Настройки валидации</h3>
              
              <div class="space-y-2">
                <label class="flex items-center">
                  <input
                    v-model="projectForm.enable_social_check"
                    type="checkbox"
                    class="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <span class="ml-2 text-sm text-gray-700">Проверка соцсетей (TT, WA, MAKC, BK)</span>
                </label>

                <label class="flex items-center">
                  <input
                    v-model="projectForm.enable_gosuslugi_check"
                    type="checkbox"
                    class="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <span class="ml-2 text-sm text-gray-700">Проверка регистрации в Госуслугах</span>
                </label>

                <label class="flex items-center">
                  <input
                    v-model="projectForm.enable_metrica_export"
                    type="checkbox"
                    class="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <span class="ml-2 text-sm text-gray-700">Отправка в Яндекс.Метрику</span>
                </label>
              </div>
            </div>

            <div class="flex items-center justify-end gap-3 pt-4 border-t">
              <button
                type="button"
                @click="closeModal"
                class="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
              >
                Отмена
              </button>
              <button
                type="submit"
                :disabled="saving"
                class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
              >
                {{ saving ? 'Сохранение...' : (editingProject ? 'Сохранить' : 'Создать') }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Модальное окно просмотра проекта -->
    <div
      v-if="viewingProject"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      @click.self="viewingProject = null"
    >
      <div class="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <div class="p-6">
          <div class="flex items-center justify-between mb-4">
            <h2 class="text-xl font-bold text-gray-900">{{ viewingProject.name }}</h2>
            <button
              @click="viewingProject = null"
              class="text-gray-400 hover:text-gray-600"
            >
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <!-- Вкладки -->
          <div class="border-b mb-4">
            <div class="flex gap-4">
              <button
                @click="activeTab = 'info'"
                :class="activeTab === 'info' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-600'"
                class="px-4 py-2 border-b-2 font-medium transition-colors"
              >
                Информация
              </button>
              <button
                @click="activeTab = 'webhook'"
                :class="activeTab === 'webhook' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-600'"
                class="px-4 py-2 border-b-2 font-medium transition-colors"
              >
                Webhook
              </button>
              <button
                @click="activeTab = 'leads'"
                :class="activeTab === 'leads' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-600'"
                class="px-4 py-2 border-b-2 font-medium transition-colors"
              >
                Заявки
              </button>
              <button
                @click="activeTab = 'manual'"
                :class="activeTab === 'manual' ? 'border-blue-500 text-blue-600' : 'border-transparent text-gray-600'"
                class="px-4 py-2 border-b-2 font-medium transition-colors"
              >
                Ручной ввод
              </button>
            </div>
          </div>

          <!-- Контент вкладок -->
          <div v-if="activeTab === 'info'" class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Описание</label>
              <p class="text-gray-900">{{ viewingProject.description || 'Не указано' }}</p>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Статус</label>
              <span
                :class="viewingProject.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'"
                class="px-2 py-1 text-xs font-medium rounded"
              >
                {{ viewingProject.is_active ? 'Активен' : 'Неактивен' }}
              </span>
            </div>
          </div>

          <div v-if="activeTab === 'webhook'" class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Webhook URL</label>
              <div class="flex items-center gap-2">
                <input
                  :value="webhookFullUrl"
                  readonly
                  class="flex-1 px-4 py-2 border border-gray-300 rounded-lg bg-gray-50"
                />
                <button
                  @click="copyWebhookUrl"
                  class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Копировать
                </button>
              </div>
              <p class="text-xs text-gray-500 mt-1">Используйте этот URL для настройки webhook в Tilda, Marquiz и других сервисах</p>
            </div>
          </div>

          <div v-if="activeTab === 'leads'" class="space-y-4">
            <div class="text-center py-8 text-gray-500">
              <p>Список заявок будет здесь</p>
            </div>
          </div>

          <div v-if="activeTab === 'manual'" class="space-y-4">
            <form @submit.prevent="submitManualLead" class="space-y-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  Телефон <span class="text-red-500">*</span>
                </label>
                <input
                  v-model="manualLeadForm.phone"
                  type="tel"
                  required
                  placeholder="+79991234567"
                  class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  Email
                </label>
                <input
                  v-model="manualLeadForm.email"
                  type="email"
                  placeholder="email@example.com"
                  class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  Имя
                </label>
                <input
                  v-model="manualLeadForm.name"
                  type="text"
                  placeholder="Имя"
                  class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <button
                type="submit"
                :disabled="submittingManualLead"
                class="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
              >
                {{ submittingManualLead ? 'Проверка...' : 'Проверить' }}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useToaster } from '@/composables/useToaster'
import api from '@/api/axios'

const toaster = useToaster()
const projects = ref([])
const clients = ref([])
const loading = ref(true)
const saving = ref(false)
const showCreateModal = ref(false)
const editingProject = ref(null)
const viewingProject = ref(null)
const activeTab = ref('info')
const submittingManualLead = ref(false)
const emailRecipientsInput = ref('')

const projectForm = reactive({
  name: '',
  description: '',
  client_id: null,
  crm_webhook_url: '',
  email_recipients: [],
  telegram_chat_id: '',
  enable_social_check: false,
  enable_gosuslugi_check: false,
  enable_metrica_export: true
})

const manualLeadForm = reactive({
  phone: '',
  email: '',
  name: ''
})

const webhookFullUrl = computed(() => {
  if (!viewingProject?.webhook_url) return ''
  return `${window.location.origin}/api${viewingProject.webhook_url}`
})

onMounted(async () => {
  await Promise.all([fetchProjects(), fetchClients()])
})

const fetchProjects = async () => {
  try {
    loading.value = true
    const response = await api.get('phone-projects/')
    projects.value = response.data
  } catch (error) {
    console.error('Error fetching projects:', error)
    toaster.error('Не удалось загрузить проекты')
  } finally {
    loading.value = false
  }
}

const fetchClients = async () => {
  try {
    const response = await api.get('clients/')
    clients.value = response.data
  } catch (error) {
    console.error('Error fetching clients:', error)
  }
}

const saveProject = async () => {
  try {
    saving.value = true
    
    // Преобразуем email_recipients из строки в массив
    const emailRecipients = emailRecipientsInput.value
      .split(',')
      .map(email => email.trim())
      .filter(email => email)
    
    const payload = {
      ...projectForm,
      email_recipients: emailRecipients.length > 0 ? emailRecipients : null
    }

    if (editingProject.value) {
      await api.put(`phone-projects/${editingProject.value.id}`, payload)
      toaster.success('Проект обновлен')
    } else {
      await api.post('phone-projects/', payload)
      toaster.success('Проект создан')
    }

    closeModal()
    await fetchProjects()
  } catch (error) {
    console.error('Error saving project:', error)
    toaster.error(error.response?.data?.detail || 'Не удалось сохранить проект')
  } finally {
    saving.value = false
  }
}

const editProject = (project) => {
  editingProject.value = project
  projectForm.name = project.name
  projectForm.description = project.description || ''
  projectForm.client_id = project.client_id
  projectForm.crm_webhook_url = project.crm_webhook_url || ''
  projectForm.email_recipients = project.email_recipients || []
  emailRecipientsInput.value = project.email_recipients?.join(', ') || ''
  projectForm.telegram_chat_id = project.telegram_chat_id || ''
  projectForm.enable_social_check = project.enable_social_check || false
  projectForm.enable_gosuslugi_check = project.enable_gosuslugi_check || false
  projectForm.enable_metrica_export = project.enable_metrica_export !== false
  showCreateModal.value = true
}

const viewProject = (project) => {
  viewingProject.value = project
  activeTab.value = 'info'
}

const deleteProject = async (project) => {
  if (!confirm(`Вы уверены, что хотите удалить проект "${project.name}"?`)) {
    return
  }

  try {
    await api.delete(`phone-projects/${project.id}`)
    toaster.success('Проект удален')
    await fetchProjects()
  } catch (error) {
    console.error('Error deleting project:', error)
    toaster.error('Не удалось удалить проект')
  }
}

const closeModal = () => {
  showCreateModal.value = false
  editingProject.value = null
  // Сброс формы
  Object.assign(projectForm, {
    name: '',
    description: '',
    client_id: null,
    crm_webhook_url: '',
    email_recipients: [],
    telegram_chat_id: '',
    enable_social_check: false,
    enable_gosuslugi_check: false,
    enable_metrica_export: true
  })
  emailRecipientsInput.value = ''
}

const copyWebhookUrl = async () => {
  try {
    await navigator.clipboard.writeText(webhookFullUrl.value)
    toaster.success('Webhook URL скопирован в буфер обмена')
  } catch (error) {
    toaster.error('Не удалось скопировать URL')
  }
}

const submitManualLead = async () => {
  if (!manualLeadForm.phone) {
    toaster.error('Введите телефон')
    return
  }

  try {
    submittingManualLead.value = true
    
    // Отправляем на webhook проекта
    const webhookUrl = viewingProject.value?.webhook_url
    if (!webhookUrl) {
      toaster.error('Webhook URL не настроен для этого проекта')
      return
    }

    const payload = {
      phone: manualLeadForm.phone,
      email: manualLeadForm.email || undefined,
      name: manualLeadForm.name || undefined
    }

    await api.post(`webhook${webhookUrl}`, payload)
    toaster.success('Заявка отправлена на проверку')
    
    // Сброс формы
    Object.assign(manualLeadForm, {
      phone: '',
      email: '',
      name: ''
    })
  } catch (error) {
    console.error('Error submitting manual lead:', error)
    toaster.error(error.response?.data?.detail || 'Не удалось отправить заявку')
  } finally {
    submittingManualLead.value = false
  }
}
</script>

