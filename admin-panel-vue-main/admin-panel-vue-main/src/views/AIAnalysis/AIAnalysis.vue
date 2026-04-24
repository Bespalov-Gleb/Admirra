<template>
  <div class="flex flex-col overflow-x-hidden w-full h-full pb-6 px-8 pt-8" style="min-height: calc(100vh - 80px); font-size: 16px">
    <!-- Заголовок -->
    <div class="flex-shrink-0 mb-4">
      <h1 :style="`font-size:28px; font-weight:700; color:${c.titleColor}; margin-bottom:4px`">AI Анализ</h1>
      <p :style="`font-size:14px; color:${c.subtitleColor}`">Аналитика и рекомендации на основе данных рекламных кампаний</p>
    </div>

    <!-- Проект + период + кнопки -->
    <div class="flex flex-wrap items-center gap-3 mb-4 flex-shrink-0">
      <select
        v-model="selectedProjectId"
        :style="`font-size:14px; padding:10px 14px; border:1px solid ${c.inputBorder}; border-radius:12px; background:${c.inputBg}; color:${c.inputColor}; outline:none; cursor:pointer; min-width:140px`"
      >
        <option value="">Все проекты</option>
        <option v-for="client in clients" :key="client.id" :value="client.id">
          {{ client.name }}
        </option>
      </select>
      <input
        v-model="startDate"
        type="date"
        :style="`font-size:14px; padding:10px 14px; border:1px solid ${c.inputBorder}; border-radius:12px; background:${c.inputBg}; color:${c.inputColor}; outline:none`"
      />
      <span :style="`color:${c.subtitleColor}; font-size:16px`">—</span>
      <input
        v-model="endDate"
        type="date"
        :style="`font-size:14px; padding:10px 14px; border:1px solid ${c.inputBorder}; border-radius:12px; background:${c.inputBg}; color:${c.inputColor}; outline:none`"
      />
      <button
        style="display:inline-flex; align-items:center; gap:8px; padding:12px 24px; background:linear-gradient(to right,#8b5cf6,#9333ea); color:#fff; font-size:15px; font-weight:500; border-radius:16px; border:none; cursor:pointer; box-shadow:0 4px 15px rgba(139,92,246,.3)"
        :disabled="generatingReport"
        :style="generatingReport ? 'opacity:.6;cursor:not-allowed' : ''"
        @click="handleGenerateReport">
        <span v-if="generatingReport" class="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
        <DocumentTextIcon v-else style="width:20px;height:20px" />
        {{ generatingReport ? 'Генерация...' : 'Сформировать отчёт' }}
      </button>
      <button
        style="display:inline-flex; align-items:center; gap:8px; padding:12px 24px; background:linear-gradient(to right,#3b82f6,#06b6d4); color:#fff; font-size:15px; font-weight:500; border-radius:16px; border:none; cursor:pointer; box-shadow:0 4px 15px rgba(59,130,246,.3)"
        :disabled="generatingRecommendations"
        :style="generatingRecommendations ? 'opacity:.6;cursor:not-allowed' : ''"
        @click="handleGetRecommendations">
        <span v-if="generatingRecommendations" class="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
        <LightBulbIcon v-else style="width:20px;height:20px" />
        {{ generatingRecommendations ? 'Генерация...' : 'Получить рекомендации' }}
      </button>
      <!-- Отправка AI-отчёта -->
      <div :style="`display:flex; align-items:center; gap:8px; margin-left:8px; padding-left:16px; border-left:1px solid ${c.dividerColor}`">
        <span :style="`font-size:13px; color:${c.dividerText}`">Отправить:</span>
        <button
          type="button"
          :disabled="sendingTg"
          :style="`padding:10px; border-radius:12px; background:${c.sendBtnBg}; border:none; cursor:pointer; color:${c.sendBtnColor}; display:flex`"
          title="Отправить в Telegram"
          @click="handleTelegramSendClick"
        >
          <PaperAirplaneIcon style="width:20px;height:20px" />
        </button>
        <button
          type="button"
          :disabled="sendingEmail"
          :style="`padding:10px; border-radius:12px; background:${c.sendBtnBg}; border:none; cursor:pointer; color:${c.sendBtnColor}; display:flex`"
          title="Отправить на Email"
          @click="showEmailModal = true"
        >
          <EnvelopeIcon style="width:20px;height:20px" />
        </button>
      </div>
    </div>

    <!-- Модалки отправки -->
    <div v-if="showTgLinkModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" @click.self="showTgLinkModal = false">
      <div :style="`background:${c.modalBg}; border-radius:24px; padding:24px; width:100%; max-width:448px; margin:0 16px; box-shadow:0 25px 50px rgba(0,0,0,0.35)`">
        <h3 :style="`font-size:18px; font-weight:600; color:${c.modalText}; margin-bottom:8px`">Подключите Telegram</h3>
        <p :style="`font-size:14px; color:${c.modalSubText}; margin-bottom:16px`">
          В Telegram нажмите <strong>Start</strong> у бота, затем «Готово» — отчёт отправится автоматически.
        </p>
        <div style="display:flex; gap:12px">
          <button type="button" :style="`flex:1; padding:10px; border-radius:12px; background:${isDarkMode?'rgba(255,255,255,0.08)':'#f3f4f6'}; color:${c.modalText}; border:none; cursor:pointer; font-size:14px`" @click="closeTgLinkModal">Отмена</button>
          <button
            type="button"
            style="flex:1; padding:10px; border-radius:12px; background:#2563eb; color:#fff; border:none; cursor:pointer; font-size:14px"
            :disabled="tgLinkChecking"
            @click="confirmTgLinked"
          >
            {{ tgLinkChecking ? 'Проверка...' : 'Готово' }}
          </button>
        </div>
      </div>
    </div>
    <div v-if="showEmailModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" @click.self="showEmailModal = false">
      <div :style="`background:${c.modalBg}; border-radius:24px; padding:24px; width:100%; max-width:448px; margin:0 16px; box-shadow:0 25px 50px rgba(0,0,0,0.35)`">
        <h3 :style="`font-size:18px; font-weight:600; color:${c.modalText}; margin-bottom:12px`">Отправить на Email</h3>
        <p :style="`font-size:14px; color:${c.modalSubText}; margin-bottom:16px`">AI-отчёт будет сгенерирован и отправлен на указанные адреса.</p>
        <input
          v-model="emailRecipients"
          type="text"
          placeholder="email1@example.com, email2@example.com"
          :style="`width:100%; padding:10px 16px; border:1px solid ${c.inputBorder}; border-radius:12px; font-size:14px; background:${c.inputBg}; color:${c.inputColor}; margin-bottom:16px; box-sizing:border-box`"
        />
        <div style="display:flex; gap:12px">
          <button :style="`flex:1; padding:10px; border-radius:12px; background:${isDarkMode?'rgba(255,255,255,0.08)':'#f3f4f6'}; color:${c.modalText}; border:none; cursor:pointer; font-size:14px`" @click="showEmailModal = false">Отмена</button>
          <button
            style="flex:1; padding:10px; border-radius:12px; background:#2563eb; color:#fff; border:none; cursor:pointer; font-size:14px"
            :disabled="sendingEmail || !emailRecipients.trim()"
            @click="submitEmail"
          >
            {{ sendingEmail ? 'Отправка...' : 'Отправить' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Чат — растягивается до низа страницы с отступом -->
    <div class="flex-1 flex flex-col" style="min-height: 400px">
      <div
        class="h-full flex flex-col overflow-hidden min-h-0"
        :style="`min-height:400px; border-radius:24px; background:${c.chatBg}; border:1px solid ${c.chatBorder}; backdrop-filter:blur(20px); box-shadow:0 4px 24px rgba(0,0,0,${isDarkMode?'.25':'.07'})`"
      >
        <!-- Шапка чата -->
        <div :style="`padding:16px 24px; border-bottom:1px solid ${c.chatHeaderBorder}; background:${c.chatHeaderBg}; flex-shrink:0`">
          <div style="display:flex; align-items:center; gap:12px">
            <div style="width:36px;height:36px;border-radius:12px;background:linear-gradient(135deg,#8b5cf6,#9333ea);display:flex;align-items:center;justify-content:center;flex-shrink:0">
              <SparklesIcon style="width:18px;height:18px;color:#fff" />
            </div>
            <div>
              <div :style="`font-size:15px; font-weight:700; color:${c.titleColor}`">AI Ассистент</div>
              <div :style="`font-size:13px; color:${c.subtitleColor}`">Задайте вопрос или выберите действие выше</div>
            </div>
          </div>
        </div>

        <!-- Область сообщений -->
        <div ref="messagesContainer" style="flex:1; padding:24px; overflow-y:auto; min-height:0">
          <div v-if="messages.length === 0 && !sendingMessage" style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;min-height:160px;text-align:center">
            <div :style="`width:56px;height:56px;border-radius:16px;background:${c.emptyIconBg};display:flex;align-items:center;justify-content:center;margin-bottom:12px`">
              <ChatBubbleLeftRightIcon :style="`width:28px;height:28px;color:${c.emptyTextColor}`" />
            </div>
            <p :style="`font-size:14px; color:${c.emptyTextColor}; max-width:280px; line-height:1.5`">
              Задайте вопрос в поле ниже или используйте кнопки выше для формирования отчёта или рекомендаций.
            </p>
          </div>
          <div v-else style="display:flex;flex-direction:column;gap:16px">
            <div v-if="aiError" style="padding:16px;border-radius:12px;background:#fef2f2;color:#dc2626;font-size:14px">
              {{ aiError }}
            </div>
            <div
              v-for="(msg, idx) in messages"
              :key="idx"
              :style="msg.role === 'user'
                ? `margin-left:10%;padding:16px;border-radius:12px;background:${c.msgUserBg};color:${c.msgUserColor};font-size:14px;line-height:1.6`
                : `margin-right:10%;padding:16px;border-radius:12px;background:${c.msgAiBg};color:${c.msgAiColor};font-size:14px;line-height:1.6;white-space:pre-wrap`"
            >
              {{ msg.content }}
            </div>
            <div v-if="sendingMessage" :style="`padding:16px;border-radius:12px;background:${c.msgAiBg};color:${c.emptyTextColor};font-size:14px;display:flex;align-items:center;gap:8px`">
              <span class="w-4 h-4 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
              Ответ генерируется...
            </div>
          </div>
        </div>

        <!-- Поле ввода -->
        <div :style="`padding:16px; border-top:1px solid ${c.chatFooterBorder}; background:${c.chatFooterBg}; flex-shrink:0`">
          <form @submit.prevent="handleSendMessage" style="display:flex; gap:12px">
            <input
              v-model="inputMessage"
              type="text"
              placeholder="Введите сообщение..."
              :disabled="sendingMessage"
              :style="`flex:1; font-size:14px; padding:14px 16px; border-radius:12px; border:1px solid ${c.inputBorder}; background:${c.inputBg}; color:${c.inputColor}; outline:none`"
            />
            <button
              type="submit"
              :disabled="sendingMessage || !inputMessage.trim()"
              :style="`padding:14px 20px; border-radius:12px; background:#7c3aed; color:#fff; font-size:15px; font-weight:500; border:none; cursor:pointer; opacity:${(sendingMessage || !inputMessage.trim()) ? '.5' : '1'}`"
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
import { ref, computed, onMounted, watch, nextTick } from 'vue'
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
import { useTheme } from '../../composables/useTheme'

const { isDarkMode } = useTheme()

// Цветовые токены для тёмной/светлой темы
const c = computed(() => isDarkMode.value ? {
  pageBg: 'transparent',
  titleColor: '#ffffff',
  subtitleColor: 'rgba(255,255,255,0.6)',
  inputBg: 'rgba(255,255,255,0.07)',
  inputBorder: 'rgba(255,255,255,0.15)',
  inputColor: '#ffffff',
  chatBg: 'rgba(255,255,255,0.04)',
  chatBorder: 'rgba(255,255,255,0.08)',
  chatHeaderBg: 'rgba(255,255,255,0.06)',
  chatHeaderBorder: 'rgba(255,255,255,0.08)',
  chatFooterBg: 'rgba(255,255,255,0.03)',
  chatFooterBorder: 'rgba(255,255,255,0.08)',
  msgUserBg: 'rgba(139,92,246,0.18)',
  msgUserColor: '#e5d9ff',
  msgAiBg: 'rgba(255,255,255,0.06)',
  msgAiColor: 'rgba(255,255,255,0.85)',
  emptyIconBg: 'rgba(255,255,255,0.08)',
  emptyTextColor: 'rgba(255,255,255,0.45)',
  sendBtnBg: '#f1f5f9',
  sendBtnColor: '#475569',
  dividerColor: 'rgba(255,255,255,0.08)',
  dividerText: 'rgba(255,255,255,0.45)',
  modalBg: '#2a2b38',
  modalText: '#ffffff',
  modalSubText: 'rgba(255,255,255,0.55)',
} : {
  pageBg: 'transparent',
  titleColor: '#171717',
  subtitleColor: '#696969',
  inputBg: '#ffffff',
  inputBorder: '#d1d5db',
  inputColor: '#374151',
  chatBg: 'rgba(255,255,255,0.8)',
  chatBorder: 'rgba(255,255,255,0.8)',
  chatHeaderBg: 'linear-gradient(to right,rgba(249,250,251,.8),rgba(255,255,255,.8))',
  chatHeaderBorder: '#f3f4f6',
  chatFooterBg: 'rgba(249,250,251,.5)',
  chatFooterBorder: '#f3f4f6',
  msgUserBg: '#f5f3ff',
  msgUserColor: '#111827',
  msgAiBg: '#f9fafb',
  msgAiColor: '#1f2937',
  emptyIconBg: '#f3f4f6',
  emptyTextColor: '#6b7280',
  sendBtnBg: '#f1f5f9',
  sendBtnColor: '#475569',
  dividerColor: '#e5e7eb',
  dividerText: '#6b7280',
  modalBg: '#ffffff',
  modalText: '#111827',
  modalSubText: '#6b7280',
})

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
