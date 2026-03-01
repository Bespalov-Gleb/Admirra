<template>
  <div class="flex flex-col overflow-x-hidden w-full min-h-[calc(100vh-8rem)]">
    <!-- Заголовок -->
    <div class="flex-shrink-0 mb-4">
      <h1 class="text-2xl sm:text-3xl font-bold text-gray-900">AI Анализ</h1>
      <p class="text-sm text-gray-500 mt-1">Аналитика и рекомендации на основе данных рекламных кампаний</p>
    </div>

    <!-- Проект + кнопки в один ряд -->
    <div class="flex flex-wrap items-center gap-3 mb-4 flex-shrink-0">
      <select
        v-model="selectedProjectId"
        class="px-4 py-2.5 border border-gray-300 rounded-xl bg-white text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-violet-500 appearance-none cursor-pointer"
      >
        <option value="">Все проекты</option>
        <option v-for="client in clients" :key="client.id" :value="client.id">
          {{ client.name }}
        </option>
      </select>
      <button
        class="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-violet-500 to-purple-600 text-white font-medium rounded-2xl shadow-lg shadow-violet-500/25 hover:shadow-violet-500/40 transition-all hover:scale-[1.02] active:scale-[0.98]"
      >
        <DocumentTextIcon class="w-5 h-5" />
        Сформировать отчёт
      </button>
      <button
        class="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-500 to-cyan-500 text-white font-medium rounded-2xl shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40 transition-all hover:scale-[1.02] active:scale-[0.98]"
      >
        <LightBulbIcon class="w-5 h-5" />
        Получить рекомендации
      </button>
    </div>

    <!-- Чат — растягивается до низа страницы -->
    <div class="flex-1 flex flex-col min-h-0">
      <div class="h-full flex flex-col bg-white/80 backdrop-blur-xl rounded-[32px] border border-white/80 shadow-lg overflow-hidden">
        <!-- Шапка чата -->
        <div class="px-6 py-3 border-b border-gray-100 bg-gradient-to-r from-gray-50/80 to-white/80 flex-shrink-0">
          <div class="flex items-center gap-3">
            <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center">
              <SparklesIcon class="w-4 h-4 text-white" />
            </div>
            <div>
              <h3 class="font-bold text-gray-900 text-sm">AI Ассистент</h3>
              <p class="text-xs text-gray-500">Задайте вопрос или выберите действие выше</p>
            </div>
          </div>
        </div>

        <!-- Область сообщений -->
        <div class="flex-1 p-6 overflow-y-auto min-h-0">
          <div class="flex flex-col items-center justify-center h-full min-h-[120px] text-center">
            <div class="w-14 h-14 rounded-2xl bg-gray-100 flex items-center justify-center mb-3">
              <ChatBubbleLeftRightIcon class="w-7 h-7 text-gray-400" />
            </div>
            <p class="text-gray-500 text-sm max-w-xs">
              Чат пока не активен. Используйте кнопки выше для формирования отчёта или получения рекомендаций.
            </p>
          </div>
        </div>

        <!-- Поле ввода — внизу страницы -->
        <div class="p-4 border-t border-gray-100 bg-gray-50/50 flex-shrink-0">
          <div class="flex gap-3">
            <input
              type="text"
              placeholder="Введите сообщение..."
              disabled
              class="flex-1 px-4 py-3 rounded-xl border border-gray-200 bg-white text-gray-400 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/20 cursor-not-allowed"
            />
            <button
              disabled
              class="px-5 py-3 rounded-xl bg-gray-200 text-gray-400 font-medium text-sm cursor-not-allowed"
            >
              Отправить
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import {
  DocumentTextIcon,
  LightBulbIcon,
  SparklesIcon,
  ChatBubbleLeftRightIcon
} from '@heroicons/vue/24/outline'
import api from '../../api/axios'
import { useProjects } from '../../composables/useProjects'

const clients = ref([])
const selectedProjectId = ref('')
const { currentProjectId, setCurrentProject } = useProjects()

onMounted(async () => {
  try {
    const { data } = await api.get('clients/')
    clients.value = data || []
  } catch {
    clients.value = []
  }
  selectedProjectId.value = currentProjectId.value || ''
})

watch(currentProjectId, (id) => {
  if (id && selectedProjectId.value !== id) selectedProjectId.value = id
}, { immediate: true })

watch(selectedProjectId, (id) => {
  if (currentProjectId.value !== id) setCurrentProject(id || null)
})
</script>
