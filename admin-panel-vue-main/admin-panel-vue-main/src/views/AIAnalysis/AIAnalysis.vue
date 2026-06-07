<template>
  <main class="assistant-page">
    <header class="assistant-header">
      <div>
        <h1>Ассистент</h1>
        <p>Задавайте вопросы по выбранному проекту, периоду, целям, бюджетам и алертам.</p>
      </div>

      <div class="assistant-controls">
        <label class="control-field control-field--project">
          <span>Проект</span>
          <select v-model="selectedProjectId" :disabled="projectsLoading">
            <option v-if="!projects.length" value="">Нет проектов</option>
            <option v-for="project in projects" :key="project.id" :value="project.id">
              {{ project.name || project.title || 'Без названия' }}
            </option>
          </select>
        </label>

        <label class="control-field">
          <span>Период</span>
          <input v-model="startDate" type="date" />
        </label>
        <label class="control-field control-field--compact">
          <span>&nbsp;</span>
          <input v-model="endDate" type="date" />
        </label>

        <div class="quota-chip" :class="{ 'quota-chip--empty': quota.remaining <= 0 }">
          <SparklesIcon />
          <div>
            <strong>{{ quota.remaining }}</strong>
            <span>из {{ quota.limit }} AI</span>
          </div>
        </div>
      </div>
    </header>

    <section class="assistant-shell">
      <aside class="assistant-rail">
        <div class="rail-section">
          <div class="rail-title-row">
            <div>
              <h2>История</h2>
              <p>{{ currentProjectName }}</p>
            </div>
            <button type="button" class="icon-button" title="Новый диалог" @click="startNewDialog">
              <PlusIcon />
            </button>
          </div>

          <div v-if="loadingDialogs" class="rail-empty">Загружаем диалоги...</div>
          <button
            v-for="dialog in dialogs"
            :key="dialog.id"
            type="button"
            class="dialog-item"
            :class="{ 'dialog-item--active': dialog.id === activeDialogId }"
            @click="openDialog(dialog.id)"
          >
            <span>{{ dialog.title }}</span>
            <small>{{ formatDateTime(dialog.updated_at) }}</small>
          </button>
          <div v-if="!loadingDialogs && !dialogs.length" class="rail-empty">Диалогов по проекту пока нет</div>
        </div>

        <div class="rail-section rail-section--prompts">
          <div class="rail-title-row">
            <div>
              <h2>Мои промпты</h2>
              <p>Сохраняются для аккаунта</p>
            </div>
            <button type="button" class="icon-button" title="Добавить промпт" @click="openPromptModal()">
              <PlusIcon />
            </button>
          </div>

          <article v-for="prompt in prompts" :key="prompt.id" class="prompt-item">
            <button type="button" class="prompt-main" @click="sendPrompt(prompt)">
              <span>{{ prompt.title }}</span>
              <small>{{ prompt.text }}</small>
            </button>
            <div class="prompt-actions">
              <button type="button" title="Редактировать" @click="openPromptModal(prompt)">
                <PencilSquareIcon />
              </button>
              <button type="button" title="Удалить" @click="deletePrompt(prompt.id)">
                <TrashIcon />
              </button>
            </div>
          </article>
          <div v-if="!prompts.length" class="rail-empty">Сохранённых промптов нет</div>
        </div>
      </aside>

      <section class="assistant-chat">
        <div ref="messagesContainer" class="messages">
          <div v-if="contextError" class="state-card state-card--warning">
            {{ contextError }}
          </div>

          <div v-if="!activeDialogId && !messages.length" class="intro-card">
            <div class="assistant-avatar">
              <SparklesIcon />
            </div>
            <div>
              <h2>Смотрю проект за период {{ displayPeriod }}</h2>
              <p>
                Можно спросить про расходы, CPC, CPL/CPA, цели, план-факт бюджета и открытые алерты.
                Если нужен отчёт или аудит, я отправлю в соответствующий раздел.
              </p>
              <p v-if="!contextState.has_integrations" class="intro-note">
                У проекта пока нет подключенных каналов. Ответы будут ограничены настройками проекта.
              </p>
              <p v-else-if="!contextState.has_data" class="intro-note">
                За выбранный период мало данных. Я буду явно отмечать, где не хватает статистики.
              </p>
            </div>
          </div>

          <div v-if="!messages.length" class="suggestions">
            <button
              v-for="suggestion in suggestions"
              :key="suggestion"
              type="button"
              @click="inputMessage = suggestion"
            >
              {{ suggestion }}
            </button>
          </div>

          <article
            v-for="message in messages"
            :key="message.id || message.localId"
            class="message"
            :class="message.role === 'user' ? 'message--user' : 'message--assistant'"
          >
            <div class="message-bubble">
              <p>{{ message.content }}</p>
              <RouterLink
                v-if="message.redirect_target"
                class="redirect-link"
                :to="redirectPath(message.redirect_target)"
              >
                {{ redirectLabel(message.redirect_target) }}
                <ArrowUpRightIcon />
              </RouterLink>
            </div>
          </article>

          <article v-if="sending" class="message message--assistant">
            <div class="message-bubble typing-bubble">
              <span />
              <span />
              <span />
            </div>
          </article>
        </div>

        <footer class="composer">
          <div v-if="quota.remaining <= 0" class="limit-card">
            <div>
              <strong>Лимит AI-запросов закончился</strong>
              <span>Обновите тариф или дождитесь следующего периода.</span>
            </div>
            <RouterLink to="/settings?tab=billing">Перейти к тарифу</RouterLink>
          </div>

          <form v-else class="composer-form" @submit.prevent="sendMessage()">
            <textarea
              v-model="inputMessage"
              rows="1"
              :disabled="sending || !selectedProjectId"
              placeholder="Спросите, например: почему вырос CPL по заявкам?"
              @keydown.enter.exact.prevent="sendMessage()"
            />
            <button
              type="button"
              class="save-prompt-button"
              :disabled="!inputMessage.trim()"
              @click="openPromptModal(null, inputMessage)"
            >
              Сохранить как промпт
            </button>
            <button type="submit" class="send-button" :disabled="sending || !inputMessage.trim() || !selectedProjectId">
              <PaperAirplaneIcon />
            </button>
          </form>
          <p class="composer-hint">1 запрос из лимита тарифа за каждое отправленное сообщение.</p>
        </footer>
      </section>
    </section>

    <div v-if="promptModalOpen" class="modal-backdrop" @click.self="closePromptModal">
      <form class="prompt-modal" @submit.prevent="savePrompt">
        <h2>{{ editingPromptId ? 'Редактировать промпт' : 'Новый промпт' }}</h2>
        <p>Проект и период добавляются автоматически, переменные в тексте не нужны.</p>
        <label>
          <span>Название</span>
          <input v-model="promptForm.title" type="text" maxlength="120" placeholder="Например: Проверить CPL" />
        </label>
        <label>
          <span>Текст промпта</span>
          <textarea v-model="promptForm.text" rows="6" placeholder="Что нужно спросить у ассистента" />
        </label>
        <div class="modal-actions">
          <button type="button" @click="closePromptModal">Отмена</button>
          <button type="submit" :disabled="savingPrompt || !promptForm.title.trim() || !promptForm.text.trim()">
            {{ savingPrompt ? 'Сохраняем...' : 'Сохранить' }}
          </button>
        </div>
      </form>
    </div>
  </main>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import {
  ArrowUpRightIcon,
  PaperAirplaneIcon,
  PencilSquareIcon,
  PlusIcon,
  SparklesIcon,
  TrashIcon,
} from '@heroicons/vue/24/outline'
import api from '../../api/axios'
import { useProjects } from '../../composables/useProjects'
import { useToaster } from '../../composables/useToaster'

const route = useRoute()
const toaster = useToaster()
const { projects, currentProjectId, fetchProjects, setCurrentProject, isLoading: projectsLoading } = useProjects()

const selectedProjectId = ref(currentProjectId.value || '')
const startDate = ref('')
const endDate = ref('')
const dialogs = ref([])
const prompts = ref([])
const messages = ref([])
const suggestions = ref([])
const activeDialogId = ref(null)
const inputMessage = ref('')
const sending = ref(false)
const loadingDialogs = ref(false)
const contextError = ref('')
const messagesContainer = ref(null)
const promptModalOpen = ref(false)
const editingPromptId = ref(null)
const savingPrompt = ref(false)

const quota = reactive({ used: 0, limit: 0, remaining: 0, reset_date: null })
const contextState = reactive({ has_data: true, has_integrations: true, alerts: [] })
const promptForm = reactive({ title: '', text: '' })

const currentProjectName = computed(() => {
  const project = projects.value.find((item) => item.id === selectedProjectId.value)
  return project?.name || project?.title || 'Проект не выбран'
})

const displayPeriod = computed(() => `${formatDate(startDate.value)} — ${formatDate(endDate.value)}`)

const setDefaultDates = () => {
  const end = new Date()
  const start = new Date()
  start.setDate(end.getDate() - 29)
  startDate.value = toInputDate(start)
  endDate.value = toInputDate(end)
}

const toInputDate = (date) => date.toISOString().slice(0, 10)

const formatDate = (value) => {
  if (!value) return '—'
  const date = new Date(`${value}T00:00:00`)
  return date.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

const formatDateTime = (value) => {
  if (!value) return ''
  return new Date(value).toLocaleDateString('ru-RU', { day: '2-digit', month: 'short' })
}

const applyQuota = (data) => {
  quota.used = Number(data?.used || 0)
  quota.limit = Number(data?.limit || 0)
  quota.remaining = Number(data?.remaining || 0)
  quota.reset_date = data?.reset_date || null
}

const loadContext = async () => {
  if (!selectedProjectId.value || !startDate.value || !endDate.value) return
  contextError.value = ''
  try {
    const { data } = await api.get('ai/context', {
      params: {
        client_id: selectedProjectId.value,
        start_date: startDate.value,
        end_date: endDate.value,
      },
    })
    applyQuota(data.quota)
    suggestions.value = data.suggestions || []
    contextState.has_data = Boolean(data.has_data)
    contextState.has_integrations = Boolean(data.has_integrations)
    contextState.alerts = data.alerts || []
  } catch (error) {
    contextError.value = error.response?.data?.detail || 'Не удалось загрузить контекст ассистента.'
  }
}

const loadDialogs = async () => {
  if (!selectedProjectId.value) return
  loadingDialogs.value = true
  try {
    const { data } = await api.get('ai/dialogs', { params: { client_id: selectedProjectId.value } })
    dialogs.value = data || []
  } catch (error) {
    toaster.error(error.response?.data?.detail || 'Не удалось загрузить историю AI.')
  } finally {
    loadingDialogs.value = false
  }
}

const loadPrompts = async () => {
  try {
    const { data } = await api.get('ai/prompts')
    prompts.value = data || []
  } catch (error) {
    toaster.error(error.response?.data?.detail || 'Не удалось загрузить промпты.')
  }
}

const openDialog = async (id) => {
  try {
    const { data } = await api.get(`ai/dialogs/${id}`)
    activeDialogId.value = data.id
    messages.value = data.messages || []
    if (data.period_start) startDate.value = data.period_start
    if (data.period_end) endDate.value = data.period_end
    await scrollToBottom()
  } catch (error) {
    toaster.error(error.response?.data?.detail || 'Не удалось открыть диалог.')
  }
}

const startNewDialog = () => {
  activeDialogId.value = null
  messages.value = []
  inputMessage.value = ''
}

const sendPrompt = (prompt) => {
  inputMessage.value = prompt.text
  sendMessage()
}

const sendMessage = async () => {
  const text = inputMessage.value.trim()
  if (!text || sending.value || !selectedProjectId.value || quota.remaining <= 0) return

  sending.value = true
  contextError.value = ''
  inputMessage.value = ''
  const optimistic = {
    localId: `local-${Date.now()}`,
    role: 'user',
    content: text,
  }
  messages.value.push(optimistic)
  await scrollToBottom()

  try {
    const { data } = await api.post('ai/chat', {
      client_id: selectedProjectId.value,
      start_date: startDate.value,
      end_date: endDate.value,
      dialog_id: activeDialogId.value,
      message: text,
    })
    activeDialogId.value = data.dialog_id
    const index = messages.value.findIndex((item) => item.localId === optimistic.localId)
    if (index >= 0) messages.value.splice(index, 1, data.user_message)
    messages.value.push(data.assistant_message)
    applyQuota(data.quota)
    await loadDialogs()
  } catch (error) {
    messages.value = messages.value.filter((item) => item.localId !== optimistic.localId)
    const message = error.response?.data?.detail || 'Не удалось получить ответ ассистента.'
    contextError.value = message
    toaster.error(message)
  } finally {
    sending.value = false
    await scrollToBottom()
  }
}

const openPromptModal = (prompt = null, text = '') => {
  editingPromptId.value = prompt?.id || null
  promptForm.title = prompt?.title || (text ? text.slice(0, 48) : '')
  promptForm.text = prompt?.text || text || ''
  promptModalOpen.value = true
}

const closePromptModal = () => {
  promptModalOpen.value = false
  editingPromptId.value = null
  promptForm.title = ''
  promptForm.text = ''
}

const savePrompt = async () => {
  if (!promptForm.title.trim() || !promptForm.text.trim()) return
  savingPrompt.value = true
  const payload = { title: promptForm.title.trim(), text: promptForm.text.trim() }
  try {
    if (editingPromptId.value) {
      await api.put(`ai/prompts/${editingPromptId.value}`, payload)
    } else {
      await api.post('ai/prompts', payload)
    }
    await loadPrompts()
    closePromptModal()
    toaster.success('Промпт сохранён')
  } catch (error) {
    toaster.error(error.response?.data?.detail || 'Не удалось сохранить промпт.')
  } finally {
    savingPrompt.value = false
  }
}

const deletePrompt = async (id) => {
  try {
    await api.delete(`ai/prompts/${id}`)
    prompts.value = prompts.value.filter((item) => item.id !== id)
  } catch (error) {
    toaster.error(error.response?.data?.detail || 'Не удалось удалить промпт.')
  }
}

const redirectPath = (target) => {
  if (target === 'audit') return '/ai-audit'
  if (target === 'reports') return '/reports'
  return '/ai-analysis'
}

const redirectLabel = (target) => {
  if (target === 'audit') return 'Открыть AI-аудит'
  if (target === 'reports') return 'Открыть отчёты'
  return 'Открыть раздел'
}

const scrollToBottom = async () => {
  await nextTick()
  const el = messagesContainer.value
  if (el) el.scrollTop = el.scrollHeight
}

watch(selectedProjectId, async (value, oldValue) => {
  if (!value || value === oldValue) return
  setCurrentProject(value)
  startNewDialog()
  await Promise.all([loadContext(), loadDialogs()])
})

watch([startDate, endDate], async () => {
  await loadContext()
})

onMounted(async () => {
  setDefaultDates()
  await fetchProjects()
  if (typeof route.query.project === 'string') {
    selectedProjectId.value = route.query.project
  }
  if (typeof route.query.start_date === 'string') {
    startDate.value = route.query.start_date
  }
  if (typeof route.query.end_date === 'string') {
    endDate.value = route.query.end_date
  }
  const selectedExists = projects.value.some((project) => project.id === selectedProjectId.value)
  if ((!selectedProjectId.value || !selectedExists) && projects.value.length) {
    selectedProjectId.value = projects.value[0].id
    setCurrentProject(selectedProjectId.value)
  }
  inputMessage.value = typeof route.query.question === 'string' ? route.query.question : ''
  await Promise.all([loadContext(), loadDialogs(), loadPrompts()])
})
</script>

<style scoped>
.assistant-page {
  min-height: calc(100vh - 5.5556rem);
  padding: 2rem;
  background: #f4f7fb;
  color: #1f2937;
}

.assistant-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}

.assistant-header h1 {
  margin: 0;
  font-size: 2rem;
  line-height: 1.15;
  font-weight: 750;
  color: #202124;
}

.assistant-header p {
  margin: 0.45rem 0 0;
  color: #9a9a9a;
  font-size: 1rem;
}

.assistant-controls {
  display: flex;
  align-items: end;
  gap: 0.75rem;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.control-field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  min-width: 9.25rem;
}

.control-field--project {
  min-width: 15rem;
}

.control-field--compact {
  min-width: 8.8rem;
}

.control-field span {
  color: #9a9a9a;
  font-weight: 650;
  font-size: 0.78rem;
}

.control-field select,
.control-field input {
  height: 2.8rem;
  border: 1px solid #e4e7ec;
  border-radius: 0.9rem;
  background: #fff;
  color: #202124;
  padding: 0 0.9rem;
  outline: none;
  font-weight: 650;
}

.quota-chip {
  height: 2.8rem;
  display: inline-flex;
  align-items: center;
  gap: 0.65rem;
  border-radius: 0.9rem;
  padding: 0 0.9rem;
  background: linear-gradient(90deg, #2f67f2, #12b6c8);
  color: #fff;
  box-shadow: 0 0.75rem 1.8rem rgba(47, 103, 242, 0.18);
}

.quota-chip svg {
  width: 1.1rem;
  height: 1.1rem;
}

.quota-chip div {
  display: flex;
  flex-direction: column;
  line-height: 1.05;
}

.quota-chip strong {
  font-size: 1rem;
}

.quota-chip span {
  font-size: 0.72rem;
  opacity: 0.9;
}

.quota-chip--empty {
  background: #ef4444;
}

.assistant-shell {
  display: grid;
  grid-template-columns: 19rem minmax(0, 1fr);
  gap: 1.25rem;
  min-height: calc(100vh - 12rem);
}

.assistant-rail,
.assistant-chat {
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 1.35rem;
  box-shadow: 0 1rem 2.5rem rgba(15, 23, 42, 0.04);
}

.assistant-rail {
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 1.2rem;
  overflow: hidden;
}

.rail-section {
  min-height: 0;
}

.rail-section--prompts {
  border-top: 1px solid #edf0f5;
  padding-top: 1rem;
}

.rail-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.rail-title-row h2 {
  margin: 0;
  font-size: 1rem;
  font-weight: 750;
  color: #202124;
}

.rail-title-row p {
  margin: 0.2rem 0 0;
  color: #a1a1aa;
  font-size: 0.78rem;
}

.icon-button,
.prompt-actions button {
  width: 2rem;
  height: 2rem;
  border-radius: 0.65rem;
  border: 1px solid #e4e7ec;
  background: #f8fafc;
  color: #2f67f2;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.icon-button svg,
.prompt-actions svg {
  width: 1rem;
  height: 1rem;
}

.dialog-item {
  width: 100%;
  border: 0;
  border-radius: 0.9rem;
  background: transparent;
  padding: 0.8rem;
  text-align: left;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  cursor: pointer;
  color: #52525b;
}

.dialog-item:hover,
.dialog-item--active {
  background: #eef5ff;
  color: #2f67f2;
}

.dialog-item span {
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dialog-item small {
  color: #a1a1aa;
}

.prompt-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0.5rem;
  align-items: center;
  padding: 0.55rem;
  border-radius: 0.9rem;
}

.prompt-item:hover {
  background: #f8fafc;
}

.prompt-main {
  min-width: 0;
  border: 0;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.prompt-main span {
  display: block;
  color: #202124;
  font-weight: 750;
  font-size: 0.9rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.prompt-main small {
  display: block;
  margin-top: 0.2rem;
  color: #a1a1aa;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.prompt-actions {
  display: flex;
  gap: 0.25rem;
}

.prompt-actions button {
  width: 1.75rem;
  height: 1.75rem;
  background: #fff;
}

.rail-empty {
  padding: 0.75rem;
  border-radius: 0.8rem;
  color: #a1a1aa;
  background: #f8fafc;
  font-size: 0.86rem;
}

.assistant-chat {
  min-width: 0;
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  overflow: hidden;
}

.messages {
  min-height: 0;
  overflow-y: auto;
  padding: 1.4rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.intro-card,
.state-card {
  display: flex;
  gap: 1rem;
  padding: 1.2rem;
  border-radius: 1.1rem;
  background: linear-gradient(135deg, #eef5ff, #f6fbff);
  border: 1px solid #dcecff;
}

.state-card {
  display: block;
  background: #fff7ed;
  border-color: #fed7aa;
  color: #9a3412;
}

.assistant-avatar {
  width: 3rem;
  height: 3rem;
  border-radius: 1rem;
  background: linear-gradient(135deg, #2f67f2, #12b6c8);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.assistant-avatar svg {
  width: 1.45rem;
  height: 1.45rem;
}

.intro-card h2 {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 800;
}

.intro-card p {
  margin: 0.45rem 0 0;
  color: #74747a;
  line-height: 1.55;
}

.intro-note {
  font-weight: 700;
  color: #2f67f2 !important;
}

.suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
}

.suggestions button {
  border: 1px solid #dcecff;
  background: #fff;
  color: #2f67f2;
  border-radius: 999px;
  padding: 0.7rem 0.9rem;
  font-weight: 750;
  cursor: pointer;
}

.message {
  display: flex;
}

.message--user {
  justify-content: flex-end;
}

.message--assistant {
  justify-content: flex-start;
}

.message-bubble {
  max-width: min(46rem, 78%);
  border-radius: 1.1rem;
  padding: 0.95rem 1rem;
  line-height: 1.55;
  white-space: pre-wrap;
}

.message-bubble p {
  margin: 0;
}

.message--user .message-bubble {
  background: linear-gradient(90deg, #2f67f2, #12b6c8);
  color: #fff;
  border-bottom-right-radius: 0.35rem;
}

.message--assistant .message-bubble {
  background: #f5f7fb;
  color: #202124;
  border-bottom-left-radius: 0.35rem;
}

.redirect-link {
  margin-top: 0.8rem;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  color: #2f67f2;
  font-weight: 800;
  text-decoration: none;
}

.redirect-link svg {
  width: 0.95rem;
  height: 0.95rem;
}

.typing-bubble {
  display: inline-flex;
  gap: 0.35rem;
  align-items: center;
}

.typing-bubble span {
  width: 0.45rem;
  height: 0.45rem;
  border-radius: 50%;
  background: #2f67f2;
  animation: pulse 1s infinite ease-in-out;
}

.typing-bubble span:nth-child(2) {
  animation-delay: 0.15s;
}

.typing-bubble span:nth-child(3) {
  animation-delay: 0.3s;
}

.composer {
  border-top: 1px solid #edf0f5;
  padding: 1rem;
  background: #fff;
}

.composer-form {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  gap: 0.65rem;
  align-items: end;
}

.composer textarea {
  min-height: 3rem;
  max-height: 8rem;
  resize: vertical;
  border: 1px solid #e4e7ec;
  border-radius: 1rem;
  background: #f8fafc;
  color: #202124;
  padding: 0.9rem 1rem;
  outline: none;
  font: inherit;
}

.save-prompt-button,
.send-button,
.limit-card a,
.modal-actions button:last-child {
  border: 0;
  background: linear-gradient(90deg, #2f67f2, #12b6c8);
  color: #fff;
  border-radius: 0.9rem;
  font-weight: 800;
  cursor: pointer;
}

.save-prompt-button {
  height: 3rem;
  padding: 0 1rem;
}

.send-button {
  width: 3rem;
  height: 3rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.send-button svg {
  width: 1.15rem;
  height: 1.15rem;
}

.save-prompt-button:disabled,
.send-button:disabled,
.modal-actions button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.composer-hint {
  margin: 0.65rem 0 0;
  color: #a1a1aa;
  font-size: 0.83rem;
}

.limit-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  border-radius: 1rem;
  padding: 1rem;
  background: #fff7ed;
  color: #9a3412;
}

.limit-card strong,
.limit-card span {
  display: block;
}

.limit-card a {
  padding: 0.75rem 1rem;
  text-decoration: none;
  white-space: nowrap;
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 10000;
  background: rgba(15, 23, 42, 0.38);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}

.prompt-modal {
  width: min(34rem, 100%);
  background: #fff;
  border-radius: 1.35rem;
  padding: 1.4rem;
  box-shadow: 0 2rem 4rem rgba(15, 23, 42, 0.18);
}

.prompt-modal h2 {
  margin: 0;
  font-size: 1.35rem;
  font-weight: 850;
}

.prompt-modal p {
  margin: 0.4rem 0 1rem;
  color: #9a9a9a;
}

.prompt-modal label {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  margin-top: 0.9rem;
  color: #74747a;
  font-weight: 750;
}

.prompt-modal input,
.prompt-modal textarea {
  border: 1px solid #e4e7ec;
  border-radius: 0.9rem;
  background: #f8fafc;
  padding: 0.85rem 1rem;
  color: #202124;
  font: inherit;
  outline: none;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.7rem;
  margin-top: 1.1rem;
}

.modal-actions button {
  height: 2.8rem;
  padding: 0 1.2rem;
  border-radius: 0.9rem;
  border: 1px solid #e4e7ec;
  background: #fff;
  color: #52525b;
  font-weight: 800;
  cursor: pointer;
}

@keyframes pulse {
  0%,
  80%,
  100% {
    transform: scale(0.75);
    opacity: 0.45;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

@media (max-width: 1180px) {
  .assistant-header {
    flex-direction: column;
  }

  .assistant-controls {
    justify-content: flex-start;
    width: 100%;
  }
}

@media (max-width: 980px) {
  .assistant-page {
    padding: 1rem;
  }

  .assistant-shell {
    grid-template-columns: 1fr;
  }

  .assistant-rail {
    max-height: 28rem;
  }

  .composer-form {
    grid-template-columns: 1fr;
  }

  .save-prompt-button,
  .send-button {
    width: 100%;
  }

  .message-bubble {
    max-width: 92%;
  }
}
</style>
