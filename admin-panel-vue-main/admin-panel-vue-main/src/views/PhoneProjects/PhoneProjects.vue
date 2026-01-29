<template>
  <div class="space-y-6 overflow-x-hidden w-full">
    <!-- Заголовок с кнопкой создания -->
    <div class="flex flex-col xl:flex-row xl:items-center justify-between gap-6 py-5 px-6 sm:px-8 bg-white/60 backdrop-blur-xl rounded-[32px] border border-white/80 shadow-sm transition-all hover:shadow-md">
      <div class="min-w-0 flex-shrink-0">
        <label class="text-[9px] font-black text-gray-400 uppercase tracking-widest ml-1 opacity-70">
          Телефония
        </label>
        <div class="flex items-center gap-3 mt-0.5">
          <div class="p-2 bg-blue-600 rounded-xl shadow-lg shadow-blue-200 hidden xs:block">
            <PhoneIcon class="w-4 h-4 text-white" />
          </div>
          <div class="flex flex-col min-w-0">
            <h1 class="text-xl sm:text-2xl font-black text-gray-900 tracking-tight truncate">
              Проекты телефонии
            </h1>
            <div class="flex items-center gap-1.5 mt-0.5">
              <div class="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse flex-shrink-0"></div>
              <p class="text-[9px] font-bold text-gray-400 uppercase tracking-wider truncate">
                Управление проектами для валидации телефонов
              </p>
            </div>
          </div>
        </div>
      </div>
      <div class="flex items-center gap-3">
        <button
          @click="showCreateModal = true"
          class="px-4 py-2.5 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-all shadow-sm hover:shadow-md flex items-center gap-2 font-semibold text-sm"
        >
          <PlusIcon class="w-5 h-5" />
          Создать проект
        </button>
      </div>
    </div>

    <!-- Список проектов -->
    <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div v-for="i in 3" :key="i" class="bg-white rounded-[40px] p-8 animate-pulse">
        <div class="h-6 bg-gray-200 rounded-lg mb-4"></div>
        <div class="h-4 bg-gray-200 rounded-lg mb-6"></div>
        <div class="space-y-3">
          <div class="h-4 bg-gray-200 rounded"></div>
          <div class="h-4 bg-gray-200 rounded"></div>
        </div>
      </div>
    </div>

    <div v-else-if="projects.length === 0" class="text-center py-16 bg-white/60 backdrop-blur-xl rounded-[32px] border border-white/80 shadow-sm">
      <div class="w-20 h-20 mx-auto mb-6 bg-blue-100 rounded-full flex items-center justify-center">
        <PhoneIcon class="w-10 h-10 text-blue-600" />
      </div>
      <h3 class="text-xl font-bold text-gray-900 mb-2">Нет проектов</h3>
      <p class="text-gray-600 mb-6 max-w-md mx-auto">Создайте первый проект для валидации телефонов и начните получать качественные лиды</p>
      <button
        @click="showCreateModal = true"
        class="px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-all shadow-sm hover:shadow-md font-semibold flex items-center gap-2 mx-auto"
      >
        <PlusIcon class="w-5 h-5" />
        Создать проект
      </button>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div
        v-for="project in projects"
        :key="project.id"
        class="bg-white rounded-[40px] border border-gray-100 shadow-sm hover:shadow-md transition-all p-8"
      >
        <div class="flex items-start justify-between mb-6">
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-2">
              <div class="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center flex-shrink-0">
                <PhoneIcon class="w-5 h-5 text-blue-600" />
              </div>
              <h3 class="text-lg font-bold text-gray-900 truncate">{{ project.name }}</h3>
            </div>
            <p v-if="project.description" class="text-sm text-gray-600 line-clamp-2">{{ project.description }}</p>
          </div>
          <span
            :class="project.is_active ? 'bg-green-100 text-green-700 border-green-200' : 'bg-gray-100 text-gray-700 border-gray-200'"
            class="px-3 py-1 text-xs font-semibold rounded-full border flex-shrink-0"
          >
            {{ project.is_active ? 'Активен' : 'Неактивен' }}
          </span>
        </div>

        <!-- Настройки проекта -->
        <div class="space-y-3 mb-6">
          <div class="flex items-center gap-2 text-sm text-gray-600 bg-gray-50 rounded-xl p-3">
            <LinkIcon class="w-4 h-4 text-gray-400 flex-shrink-0" />
            <span v-if="project.webhook_url" class="truncate text-xs font-mono">{{ project.webhook_url }}</span>
            <span v-else class="text-gray-400 text-xs">Webhook не настроен</span>
          </div>
          <div class="flex flex-wrap gap-2">
            <span
              v-if="project.enable_social_check"
              class="px-3 py-1 text-xs font-semibold bg-blue-100 text-blue-700 rounded-full"
            >
              Соцсети
            </span>
            <span
              v-if="project.enable_gosuslugi_check"
              class="px-3 py-1 text-xs font-semibold bg-purple-100 text-purple-700 rounded-full"
            >
              Госуслуги
            </span>
            <span
              v-if="project.enable_metrica_export"
              class="px-3 py-1 text-xs font-semibold bg-yellow-100 text-yellow-700 rounded-full"
            >
              Метрика
            </span>
          </div>
        </div>

        <!-- Действия -->
        <div class="flex items-center gap-2 pt-6 border-t border-gray-200">
          <button
            @click="viewProject(project)"
            class="flex-1 px-4 py-2.5 text-sm font-semibold text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-xl transition-all"
          >
            Просмотр
          </button>
          <button
            @click="editProject(project)"
            class="flex-1 px-4 py-2.5 text-sm font-semibold text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-xl transition-all"
          >
            Редактировать
          </button>
          <button
            @click="deleteProject(project)"
            class="px-4 py-2.5 text-sm font-semibold text-red-600 bg-red-50 hover:bg-red-100 rounded-xl transition-all"
          >
            <TrashIcon class="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>

    <!-- Модальное окно создания/редактирования -->
    <div
      v-if="showCreateModal || editingProject"
      class="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      @click.self="closeModal"
    >
      <div class="bg-white rounded-[32px] shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div class="p-8">
          <div class="flex items-center justify-between mb-6">
            <div>
              <h2 class="text-2xl font-black text-gray-900">
                {{ editingProject ? 'Редактировать проект' : 'Создать проект' }}
              </h2>
              <p class="text-sm text-gray-500 mt-1">
                {{ editingProject ? 'Обновите настройки проекта' : 'Настройте новый проект для валидации лидов' }}
              </p>
            </div>
            <button
              @click="closeModal"
              class="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <XMarkIcon class="w-6 h-6" />
            </button>
          </div>

          <form @submit.prevent="saveProject" class="space-y-6">
            <div>
              <label class="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">
                Название проекта <span class="text-red-500">*</span>
              </label>
              <input
                v-model="projectForm.name"
                type="text"
                required
                placeholder="Введите название проекта"
                class="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
              />
            </div>

            <div>
              <label class="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">
                Описание
              </label>
              <textarea
                v-model="projectForm.description"
                rows="3"
                placeholder="Описание проекта (необязательно)"
                class="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition resize-none"
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

            <div class="flex items-center justify-end gap-3 pt-6 border-t border-gray-200">
              <button
                type="button"
                @click="closeModal"
                class="px-6 py-3 text-gray-700 bg-gray-100 rounded-xl hover:bg-gray-200 transition-all font-semibold"
              >
                Отмена
              </button>
              <button
                type="submit"
                :disabled="saving"
                class="px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-all disabled:opacity-50 font-semibold shadow-sm hover:shadow-md flex items-center gap-2"
              >
                <span v-if="saving" class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
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
      class="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      @click.self="viewingProject = null"
    >
      <div class="bg-white rounded-[32px] shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <div class="p-8">
          <div class="flex items-center justify-between mb-6">
            <div>
              <h2 class="text-2xl font-black text-gray-900">{{ viewingProject.name }}</h2>
              <p v-if="viewingProject.description" class="text-sm text-gray-500 mt-1">{{ viewingProject.description }}</p>
            </div>
            <button
              @click="viewingProject = null"
              class="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <XMarkIcon class="w-6 h-6" />
            </button>
          </div>

          <!-- Вкладки -->
          <div class="border-b border-gray-200 mb-6">
            <div class="flex gap-1">
              <button
                @click="activeTab = 'info'"
                :class="activeTab === 'info' ? 'bg-blue-50 text-blue-700 border-blue-200' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'"
                class="px-4 py-2.5 border-b-2 font-semibold text-sm transition-all rounded-t-xl"
              >
                Информация
              </button>
              <button
                @click="activeTab = 'webhook'"
                :class="activeTab === 'webhook' ? 'bg-blue-50 text-blue-700 border-blue-200' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'"
                class="px-4 py-2.5 border-b-2 font-semibold text-sm transition-all rounded-t-xl"
              >
                Webhook
              </button>
              <button
                @click="activeTab = 'leads'"
                :class="activeTab === 'leads' ? 'bg-blue-50 text-blue-700 border-blue-200' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'"
                class="px-4 py-2.5 border-b-2 font-semibold text-sm transition-all rounded-t-xl"
              >
                Заявки
              </button>
              <button
                @click="activeTab = 'manual'"
                :class="activeTab === 'manual' ? 'bg-blue-50 text-blue-700 border-blue-200' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'"
                class="px-4 py-2.5 border-b-2 font-semibold text-sm transition-all rounded-t-xl"
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
                class="w-full px-4 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-all disabled:opacity-50 font-semibold shadow-sm hover:shadow-md flex items-center justify-center gap-2"
              >
                <span v-if="submittingManualLead" class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
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
import { PhoneIcon, PlusIcon, LinkIcon, TrashIcon, XMarkIcon } from '@heroicons/vue/24/outline'

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

