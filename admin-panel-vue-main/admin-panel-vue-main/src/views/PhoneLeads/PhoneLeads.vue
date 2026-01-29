<template>
  <div class="space-y-6 overflow-x-hidden w-full">
    <!-- Заголовок -->
    <div class="py-5 px-6 sm:px-8 bg-white/60 backdrop-blur-xl rounded-[32px] border border-white/80 shadow-sm transition-all hover:shadow-md">
      <label class="text-[9px] font-black text-gray-400 uppercase tracking-widest ml-1 opacity-70">
        Лиды
      </label>
      <div class="flex items-center gap-3 mt-0.5">
        <div class="p-2 bg-blue-600 rounded-xl shadow-lg shadow-blue-200 hidden xs:block">
          <UserGroupIcon class="w-4 h-4 text-white" />
        </div>
        <div class="flex flex-col min-w-0 flex-1">
          <h1 class="text-xl sm:text-2xl font-black text-gray-900 tracking-tight truncate">
            Список лидов
          </h1>
          <div class="flex items-center gap-1.5 mt-0.5">
            <div class="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse flex-shrink-0"></div>
            <p class="text-[9px] font-bold text-gray-400 uppercase tracking-wider truncate">
              Все заявки, прошедшие валидацию
            </p>
          </div>
        </div>
        <div class="flex items-center gap-3">
          <button
            @click="refreshLeads"
            :disabled="loading"
            class="px-4 py-2.5 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200 transition-all shadow-sm hover:shadow-md flex items-center gap-2 font-semibold text-sm"
          >
            <ArrowPathIcon :class="['w-5 h-5', loading && 'animate-spin']" />
            Обновить
          </button>
        </div>
      </div>
    </div>

    <!-- Фильтры -->
    <div class="bg-white/60 backdrop-blur-xl rounded-[32px] border border-white/80 shadow-sm p-6">
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div>
          <label class="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">
            Проект
          </label>
          <select
            v-model="filters.project_id"
            class="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition text-sm"
          >
            <option :value="null">Все проекты</option>
            <option v-for="project in projects" :key="project.id" :value="project.id">
              {{ project.name }}
            </option>
          </select>
        </div>
        <div>
          <label class="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">
            Статус
          </label>
          <select
            v-model="filters.status"
            class="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition text-sm"
          >
            <option value="all">Все</option>
            <option value="accepted">Приняты</option>
            <option value="rejected">Отклонены</option>
          </select>
        </div>
        <div>
          <label class="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">
            Дата от
          </label>
          <input
            v-model="filters.start_date"
            type="date"
            class="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition text-sm"
          />
        </div>
        <div>
          <label class="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">
            Дата до
          </label>
          <input
            v-model="filters.end_date"
            type="date"
            class="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition text-sm"
          />
        </div>
      </div>
    </div>

    <!-- Таблица лидов -->
    <div class="bg-white rounded-[32px] border border-gray-100 shadow-sm overflow-hidden">
      <div v-if="loading" class="p-12 text-center">
        <div class="inline-block w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
        <p class="mt-4 text-gray-600 text-sm">Загрузка лидов...</p>
      </div>

      <div v-else-if="leads.length === 0" class="p-12 text-center">
        <div class="w-16 h-16 mx-auto mb-4 bg-gray-100 rounded-full flex items-center justify-center">
          <UserGroupIcon class="w-8 h-8 text-gray-400" />
        </div>
        <h3 class="text-lg font-bold text-gray-900 mb-2">Нет лидов</h3>
        <p class="text-gray-600 text-sm">Лиды появятся здесь после прохождения валидации</p>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="w-full">
          <thead class="bg-gray-50 border-b border-gray-200">
            <tr>
              <th class="px-6 py-4 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Дата</th>
              <th class="px-6 py-4 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Телефон</th>
              <th class="px-6 py-4 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Email</th>
              <th class="px-6 py-4 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Имя</th>
              <th class="px-6 py-4 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Статус</th>
              <th class="px-6 py-4 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Причина</th>
              <th class="px-6 py-4 text-left text-xs font-bold text-gray-500 uppercase tracking-wider">Проект</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-200">
            <tr
              v-for="lead in leads"
              :key="lead.id"
              class="hover:bg-gray-50 transition-colors"
            >
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                {{ formatDate(lead.created_at) }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                {{ lead.phone }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                {{ lead.email || '-' }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                {{ lead.name || '-' }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span
                  :class="[
                    'px-3 py-1 text-xs font-semibold rounded-full',
                    lead.is_accepted ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                  ]"
                >
                  {{ lead.is_accepted ? 'Принят' : 'Отклонён' }}
                </span>
              </td>
              <td class="px-6 py-4 text-sm text-gray-600">
                {{ lead.rejection_reason || '-' }}
              </td>
              <td class="px-6 py-4 text-sm text-gray-600">
                {{ getProjectName(lead.phone_project_id) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { UserGroupIcon, ArrowPathIcon } from '@heroicons/vue/24/outline'
import api from '@/api/axios'
import { useToaster } from '@/composables/useToaster'

const toaster = useToaster()
const loading = ref(false)
const leads = ref([])
const projects = ref([])

const filters = ref({
  project_id: null,
  status: 'all',
  start_date: '',
  end_date: ''
})

onMounted(async () => {
  await Promise.all([fetchProjects(), fetchLeads()])
})

watch(() => filters.value, () => {
  fetchLeads()
}, { deep: true })

const fetchProjects = async () => {
  try {
    const response = await api.get('phone-projects/')
    projects.value = response.data
  } catch (error) {
    console.error('Error fetching projects:', error)
  }
}

const fetchLeads = async () => {
  try {
    loading.value = true
    const params = {}
    if (filters.value.project_id) params.project_id = filters.value.project_id
    if (filters.value.status !== 'all') {
      params.is_accepted = filters.value.status === 'accepted'
    }
    if (filters.value.start_date) params.start_date = filters.value.start_date
    if (filters.value.end_date) params.end_date = filters.value.end_date

    // TODO: Заменить на реальный API endpoint когда будет готов
    // const response = await api.get('leads/', { params })
    // leads.value = response.data
    
    // Временные данные для демонстрации
    leads.value = []
  } catch (error) {
    console.error('Error fetching leads:', error)
    toaster.error('Не удалось загрузить лиды')
  } finally {
    loading.value = false
  }
}

const refreshLeads = () => {
  fetchLeads()
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const getProjectName = (projectId) => {
  if (!projectId) return '-'
  const project = projects.value.find(p => p.id === projectId)
  return project?.name || '-'
}
</script>

