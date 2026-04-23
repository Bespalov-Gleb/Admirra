<template>
  <div class="flex flex-col overflow-x-hidden w-full min-h-[calc(100vh-8rem)] pb-8">
    <!-- Заголовок -->
    <div class="flex-shrink-0 mb-4">
      <h1 class="text-2xl sm:text-3xl font-bold text-gray-900">AI Анализ</h1>
      <p class="text-sm text-gray-500 mt-1">Аналитика и рекомендации на основе данных рекламных кампаний</p>
    </div>

    <!-- Проект + период + кнопки -->
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
      <input
        v-model="startDate"
        type="date"
        class="px-4 py-2.5 border border-gray-300 rounded-xl bg-white text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-violet-500"
      />
      <span class="text-gray-400">—</span>
      <input
        v-model="endDate"
        type="date"
        class="px-4 py-2.5 border border-gray-300 rounded-xl bg-white text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-violet-500"
      />
      <button
        class="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-violet-500 to-purple-600 text-white font-medium rounded-2xl shadow-lg shadow-violet-500/25 hover:shadow-violet-500/40 transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed"
        :disabled="generatingReport"
        @click="handleGenerateReport">
        <span v-if="generatingReport" class="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
        <DocumentTextIcon v-else class="w-5 h-5" />
        {{ generatingReport ? 'Генерация...' : 'Сформировать отчёт' }}
      </button>
      <button
        class="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-500 to-cyan-500 text-white font-medium rounded-2xl shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40 transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed"
        :disabled="generatingRecommendations"
        @click="handleGetRecommendations">
        <span v-if="generatingRecommendations" class="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
        <LightBulbIcon v-else class="w-5 h-5" />
        {{ generatingRecommendations ? 'Генерация...' : 'Получить рекомендации' }}
      </button>
      <!-- Отправка AI-отчёта -->
      <div class="flex items-center gap-2 ml-2 pl-4 border-l border-gray-200">
        <span class="text-xs text-gray-500">Отправить:</span>
        <button
          type="button"
          :disabled="sendingTg"
          class="p-2.5 rounded-xl bg-slate-100 hover:bg-blue-100 text-slate-600 hover:text-blue-600 transition-colors disabled:opacity-50"
          title="Отправить в Telegram"
          @click="handleTelegramSendClick"
        >
          <PaperAirplaneIcon class="w-5 h-5" />
        </button>
        <button
          type="button"
          :disabled="sendingEmail"
          class="p-2.5 rounded-xl bg-slate-100 hover:bg-blue-100 text-slate-600 hover:text-blue-600 transition-colors disabled:opacity-50"
          title="Отправить на Email"
          @click="showEmailModal = true"
        >
          <EnvelopeIcon class="w-5 h-5" />
        </button>
      </div>
    </div>

    <!-- Модалки отправки -->
    <div v-if="showTgLinkModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" @click.self="showTgLinkModal = false">
      <div class="bg-white rounded-2xl p-6 w-full max-w-md mx-4 shadow-xl">
        <h3 class="text-lg font-semibold text-gray-900 mb-2">Подключите Telegram</h3>
        <p class="text-sm text-gray-500 mb-4">
          В Telegram нажмите <strong>Start</strong> у бота, затем «Готово» — отчёт отправится автоматически.
        </p>
        <div class="flex gap-3">
          <button type="button" class="flex-1 py-2.5 rounded-xl bg-gray-100 text-gray-700 hover:bg-gray-200" @click="closeTgLinkModal">Отмена</button>
          <button
            type="button"
            class="flex-1 py-2.5 rounded-xl bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
            :disabled="tgLinkChecking"
            @click="confirmTgLinked"
          >
            {{ tgLinkChecking ? 'Проверка...' : 'Готово' }}
          </button>
        </div>
      </div>
    </div>
    <div v-if="showEmailModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" @click.self="showEmailModal = false">
      <div class="bg-white rounded-2xl p-6 w-full max-w-md mx-4 shadow-xl">
        <h3 class="text-lg font-semibold text-gray-900 mb-3">Отправить на Email</h3>
        <p class="text-sm text-gray-500 mb-4">AI-отчёт будет сгенерирован и отправлен на указанные адреса.</p>
        <input
          v-model="emailRecipients"
          type="text"
          placeholder="email1@example.com, email2@example.com"
          class="w-full px-4 py-2.5 border border-gray-200 rounded-xl text-sm mb-4"
        />
        <div class="flex gap-3">
          <button class="flex-1 py-2.5 rounded-xl bg-gray-100 text-gray-700 hover:bg-gray-200" @click="showEmailModal = false">Отмена</button>
          <button
            class="flex-1 py-2.5 rounded-xl bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
            :disabled="sendingEmail || !emailRecipients.trim()"
            @click="submitEmail"
          >
            {{ sendingEmail ? 'Отправка...' : 'Отправить' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Чат — растягивается до низа страницы с отступом -->
    <div class="flex-1 flex flex-col min-h-[320px]">
      <div class="h-full flex flex-col bg-white/80 backdrop-blur-xl rounded-[32px] border border-white/80 shadow-lg overflow-hidden min-h-0">
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
        <div ref="messagesContainer" class="flex-1 p-6 overflow-y-auto min-h-0">
          <div v-if="messages.length === 0 && !sendingMessage" class="flex flex-col items-center justify-center h-full min-h-[120px] text-center">
            <div class="w-14 h-14 rounded-2xl bg-gray-100 flex items-center justify-center mb-3">
              <ChatBubbleLeftRightIcon class="w-7 h-7 text-gray-400" />
            </div>
            <p class="text-gray-500 text-sm max-w-xs">
              Задайте вопрос в поле ниже или используйте кнопки выше для формирования отчёта или рекомендаций.
            </p>
          </div>
          <div v-else class="space-y-4">
            <div v-if="aiError" class="p-4 rounded-xl bg-red-50 text-red-600 text-sm">
              {{ aiError }}
            </div>
            <div
              v-for="(msg, idx) in messages"
              :key="idx"
              :class="[
                'p-4 rounded-xl text-sm',
                msg.role === 'user'
                  ? 'ml-8 bg-violet-50 text-gray-900'
                  : 'mr-8 bg-gray-50 text-gray-800 whitespace-pre-wrap'
              ]"
            >
              {{ msg.content }}
            </div>
            <div v-if="sendingMessage" class="p-4 rounded-xl bg-gray-50 text-gray-500 text-sm flex items-center gap-2">
              <span class="w-4 h-4 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
              Ответ генерируется...
            </div>
          </div>
        </div>

        <!-- Поле ввода -->
        <div class="p-4 border-t border-gray-100 bg-gray-50/50 flex-shrink-0">
          <form @submit.prevent="handleSendMessage" class="flex gap-3">
            <input
              v-model="inputMessage"
              type="text"
              placeholder="Введите сообщение..."
              :disabled="sendingMessage"
              class="flex-1 px-4 py-3 rounded-xl border border-gray-200 bg-white text-gray-900 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/20 focus:border-violet-500 placeholder-gray-400"
            />
            <button
              type="submit"
              :disabled="sendingMessage || !inputMessage.trim()"
              class="px-5 py-3 rounded-xl bg-violet-600 text-white font-medium text-sm hover:bg-violet-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Отправить
            </button>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import {
  DocumentTextIcon,
  LightBulbIcon,
  SparklesIcon,
  ChatBubbleLeftRightIcon,
  PaperAirplaneIcon,
  EnvelopeIcon
} from '@heroicons/vue/24/outline'
import api from '../../api/axios'
import { useProjects } from '../../composables/useProjects'
import { useToaster } from '../../composables/useToaster'
import { useTelegramReportLink } from '../../composables/useTelegramReportLink'

const toaster = useToaster()
const { openTelegramBotForLinking } = useTelegramReportLink()

const clients = ref([])
const selectedProjectId = ref('')
const { currentProjectId, setCurrentProject } = useProjects()

function getDefaultDates() {
  const end = new Date()
  const start = new Date()
  start.setDate(start.getDate() - 13)
  return {
    start: start.toISOString().slice(0, 10),
    end: end.toISOString().slice(0, 10)
  }
}

const defaults = getDefaultDates()
const endDate = ref(defaults.end)
const startDate = ref(defaults.start)

const generatingReport = ref(false)
const generatingRecommendations = ref(false)
const sendingMessage = ref(false)
const messages = ref([])
const inputMessage = ref('')
const aiError = ref('')
const messagesContainer = ref(null)

const showTgLinkModal = ref(false)
const tgLinkChecking = ref(false)
const pendingTgSend = ref(false)
const reportTelegramChatId = ref('')
const showEmailModal = ref(false)
const emailRecipients = ref('')
const sendingTg = ref(false)
const sendingEmail = ref(false)

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

onMounted(async () => {
  try {
    const [clientsRes, meRes] = await Promise.all([
      api.get('clients/'),
      api.get('/auth/me').catch(() => ({ data: {} }))
    ])
    clients.value = clientsRes.data || []
    reportTelegramChatId.value = meRes.data?.report_telegram_chat_id || ''
    emailRecipients.value = (meRes.data?.report_email_recipients || []).join(', ')
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

function addMessage(role, content) {
  messages.value.push({ role, content })
  aiError.value = ''
  scrollToBottom()
}

async function callGenerateReport(reportType) {
  aiError.value = ''
  const loading = reportType === 'full' ? generatingReport : generatingRecommendations
  loading.value = true
  try {
    const { data } = await api.post('ai/generate-report', {
      client_id: selectedProjectId.value || null,
      start_date: startDate.value,
      end_date: endDate.value,
      report_type: reportType
    })
    const text = data.text || ''
    addMessage('assistant', text)
  } catch (err) {
    aiError.value = err.response?.data?.detail || err.message || 'Ошибка при генерации отчёта'
  } finally {
    loading.value = false
  }
}

function handleGenerateReport() {
  callGenerateReport('full')
}

function handleGetRecommendations() {
  callGenerateReport('recommendations')
}

async function handleSendMessage() {
  const text = inputMessage.value.trim()
  if (!text || sendingMessage.value) return

  addMessage('user', text)
  inputMessage.value = ''
  sendingMessage.value = true
  aiError.value = ''

  const history = messages.value
    .slice(0, -1)
    .map(m => ({ role: m.role, content: m.content }))

  try {
    const { data } = await api.post('ai/chat', {
      client_id: selectedProjectId.value || null,
      start_date: startDate.value,
      end_date: endDate.value,
      message: text,
      history
    })
    addMessage('assistant', data.text || '')
  } catch (err) {
    aiError.value = err.response?.data?.detail || err.message || 'Ошибка при отправке сообщения'
    messages.value.pop()
  } finally {
    sendingMessage.value = false
  }
}

async function refreshTelegramChatFromServer() {
  try {
    const { data } = await api.get('/auth/me')
    reportTelegramChatId.value = data?.report_telegram_chat_id || ''
  } catch {
    /* ignore */
  }
}

async function submitTelegramWithChatId(chatId) {
  if (!chatId || sendingTg.value) return
  sendingTg.value = true
  try {
    await api.post('reports/send', {
      report_type: 'ai',
      channels: ['telegram'],
      telegram_chat_id: chatId,
      client_id: selectedProjectId.value || null,
      start_date: startDate.value,
      end_date: endDate.value
    })
    toaster.success('AI-отчёт отправлен в Telegram')
  } catch (err) {
    aiError.value = err.response?.data?.detail || 'Ошибка отправки в Telegram'
    toaster.error(err.response?.data?.detail || 'Ошибка отправки')
  } finally {
    sendingTg.value = false
  }
}

function closeTgLinkModal() {
  showTgLinkModal.value = false
  pendingTgSend.value = false
}

async function confirmTgLinked() {
  tgLinkChecking.value = true
  try {
    await refreshTelegramChatFromServer()
    const chatId = reportTelegramChatId.value.trim()
    if (!chatId) {
      toaster.error('Сначала нажмите Start в чате с ботом в Telegram')
      return
    }
    showTgLinkModal.value = false
    const sendNow = pendingTgSend.value
    pendingTgSend.value = false
    if (sendNow) {
      await submitTelegramWithChatId(chatId)
    }
  } finally {
    tgLinkChecking.value = false
  }
}

async function handleTelegramSendClick() {
  await refreshTelegramChatFromServer()
  const chatId = reportTelegramChatId.value.trim()
  if (chatId) {
    await submitTelegramWithChatId(chatId)
    return
  }
  try {
    await openTelegramBotForLinking()
    pendingTgSend.value = true
    showTgLinkModal.value = true
  } catch (err) {
    const d = err.response?.data?.detail
    toaster.error(typeof d === 'string' ? d : 'Не удалось открыть Telegram')
  }
}

async function submitEmail() {
  const emails = emailRecipients.value.split(/[,;\s]+/).map(e => e.trim()).filter(Boolean)
  if (!emails.length || sendingEmail.value) return
  sendingEmail.value = true
  try {
    const { data } = await api.post('reports/send', {
      report_type: 'ai',
      channels: ['email'],
      email_recipients: emails,
      client_id: selectedProjectId.value || null,
      start_date: startDate.value,
      end_date: endDate.value
    })
    if (data?.results?.email) {
      toaster.success('AI-отчёт отправлен на email')
      showEmailModal.value = false
    } else {
      const msg = data?.results?.email_error || 'Не удалось отправить email'
      aiError.value = msg
      toaster.error(msg)
    }
  } catch (err) {
    aiError.value = err.response?.data?.detail || 'Ошибка отправки на Email'
    toaster.error(err.response?.data?.detail || 'Ошибка отправки')
  } finally {
    sendingEmail.value = false
  }
}
</script>
