<template>
  <div class="relative z-[2] flex min-h-full flex-col overflow-hidden px-[1.7361rem] py-[2.0833rem]" >

    <!-- Header -->
    <div class="flex items-start justify-between gap-[1.0417rem] mb-[1.3889rem]">
      <div>
        <h3 class="text-[2.0833rem] font-semibold leading-none text-[#171717] dark:text-white">Ассистент</h3>
        <p class="text-[1.0417rem] font-medium text-[rgba(105,105,105,0.56)] dark:text-white/55 mt-[0.4861rem]">Задавайте вопросы по выбранному проекту, периоду, целям и алертам.</p>
      </div>

      <div class="flex items-center gap-[0.6944rem] flex-shrink-0 flex-wrap justify-end">
        <!-- Project select -->
        <div class="custom-select" :class="{ open: openSelect === 'project' }">
          <button type="button" class="cs-head dark:!border-white/10 dark:!bg-[#2C2F3D] dark:!text-white/70" @click="toggleSelect('project')">
            <span class="cs-current">{{ currentProjectName }}</span>
            <span class="cs-arrow dark:!bg-white/10">
              <svg width="5" height="4" viewBox="0 0 9 6" fill="none"><path d="M0.5 1L4.5 5L8.5 1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </span>
          </button>
          <div class="cs-list dark:!bg-[#2C2F3D]">
            <button
              v-for="project in projects"
              :key="project.id"
              type="button"
              class="cs-option dark:!text-white/70 dark:hover:!bg-white/5"
              :class="{ selected: selectedProjectId === project.id }"
              @click="selectedProjectId = project.id; openSelect = null"
            >{{ project.name || 'Без названия' }}</button>
          </div>
        </div>

        <!-- Period -->
        <DateRangePicker v-model="dateRange" @change="onDateRangeChange" />

        <!-- Quota badge -->
        <div class="ai-quota-badge" :class="{ 'ai-quota-badge--empty': quota.remaining <= 0 }">
          <svg class="w-[0.9722rem] h-[0.9722rem]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z"/></svg>
          <strong>{{ quota.remaining }}</strong>
          <span>из {{ quota.limit }} AI</span>
        </div>
      </div>
    </div>

    <!-- Shell: rail + chat -->
    <div class="ai-shell">
      <!-- Left rail -->
      <aside class="ai-rail">
        <div class="ai-rail-section">
          <div class="ai-rail-head">
            <div>
              <div class="text-[0.9722rem] font-bold text-[#171717] dark:text-white">История</div>
              <div class="text-[0.7639rem] text-[rgba(105,105,105,0.56)] dark:text-white/40">{{ currentProjectName }}</div>
            </div>
            <button type="button" class="ai-icon-btn" title="Новый диалог" @click="startNewDialog">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>
            </button>
          </div>

          <div v-if="loadingDialogs" class="ai-rail-empty">Загружаем…</div>
          <button
            v-for="dialog in dialogs"
            :key="dialog.id"
            type="button"
            class="ai-dialog-item"
            :class="{ 'ai-dialog-item--active': dialog.id === activeDialogId }"
            @click="openDialog(dialog.id)"
          >
            <span>{{ dialog.title }}</span>
            <small>{{ formatDateTime(dialog.updated_at) }}</small>
          </button>
          <div v-if="!loadingDialogs && !dialogs.length" class="ai-rail-empty">Диалогов по проекту пока нет</div>
        </div>

        <div class="ai-rail-section ai-rail-section--border">
          <div class="ai-rail-head">
            <div>
              <div class="text-[0.9722rem] font-bold text-[#171717] dark:text-white">Мои промпты</div>
              <div class="text-[0.7639rem] text-[rgba(105,105,105,0.56)] dark:text-white/40">Сохраняются для аккаунта</div>
            </div>
            <button type="button" class="ai-icon-btn" title="Добавить промпт" @click="openPromptModal()">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>
            </button>
          </div>

          <article v-for="prompt in prompts" :key="prompt.id" class="ai-prompt-item">
            <button type="button" class="ai-prompt-main" @click="sendPrompt(prompt)">
              <span>{{ prompt.title }}</span>
              <small>{{ prompt.text }}</small>
            </button>
            <div class="ai-prompt-actions">
              <button type="button" title="Редактировать" @click="openPromptModal(prompt)">
                <PencilSquareIcon />
              </button>
              <button type="button" title="Удалить" @click="deletePrompt(prompt.id)">
                <TrashIcon />
              </button>
            </div>
          </article>
          <div v-if="!prompts.length" class="ai-rail-empty">Сохранённых промптов нет</div>
        </div>
      </aside>

      <!-- Chat area -->
      <section class="ai-chat">
        <div ref="messagesContainer" class="ai-messages">
          <div v-if="contextError" class="ai-state-card ai-state-card--warning">{{ contextError }}</div>

          <div v-if="!activeDialogId && !messages.length" class="ai-intro-card">
            <div class="ai-avatar">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z"/></svg>
            </div>
            <div>
              <div class="text-[1.0417rem] font-bold text-[#171717] dark:text-white">Смотрю проект за период {{ displayPeriod }}</div>
              <p class="text-[0.9028rem] text-[rgba(105,105,105,0.56)] dark:text-white/55 mt-[0.3472rem] leading-[1.5]">
                Можно спросить про расходы, CPC, CPL/CPA, цели, план-факт бюджета и открытые алерты.
                Если нужен отчёт или аудит, я отправлю в соответствующий раздел.
              </p>
              <p v-if="!contextState.has_integrations" class="text-[0.9028rem] font-semibold text-[#2563eb] dark:text-[#4A7AFF] mt-[0.3472rem]">
                У проекта пока нет подключенных каналов.
              </p>
              <p v-else-if="!contextState.has_data" class="text-[0.9028rem] font-semibold text-[#2563eb] dark:text-[#4A7AFF] mt-[0.3472rem]">
                За выбранный период мало данных. Я буду явно отмечать, где не хватает статистики.
              </p>
            </div>
          </div>

          <div v-if="!messages.length" class="ai-suggestions">
            <button v-for="s in suggestions" :key="s" type="button" @click="inputMessage = s">{{ s }}</button>
          </div>

          <article
            v-for="message in messages"
            :key="message.id || message.localId"
            class="ai-msg"
            :class="message.role === 'user' ? 'ai-msg--user' : 'ai-msg--assistant'"
          >
            <div class="ai-msg-bubble">
              <p>{{ message.content }}</p>
              <RouterLink v-if="message.redirect_target" class="ai-redirect" :to="redirectPath(message.redirect_target)">
                {{ redirectLabel(message.redirect_target) }}
                <ArrowUpRightIcon />
              </RouterLink>
            </div>
          </article>

          <article v-if="sending" class="ai-msg ai-msg--assistant">
            <div class="ai-msg-bubble ai-typing"><span /><span /><span /></div>
          </article>
        </div>

        <!-- Composer -->
        <div class="ai-composer">
          <div v-if="quota.remaining <= 0" class="ai-limit-card">
            <div>
              <strong>Лимит AI-запросов закончился</strong>
              <span>Обновите тариф или дождитесь следующего периода.</span>
            </div>
            <RouterLink to="/settings?tab=tariff" class="ai-limit-btn">Перейти к тарифу</RouterLink>
          </div>

          <form v-else class="ai-composer-form" @submit.prevent="sendMessage()">
            <textarea
              v-model="inputMessage"
              rows="1"
              :disabled="sending || !selectedProjectId"
              placeholder="Спросите, например: почему вырос CPL по заявкам?"
              @keydown.enter.exact.prevent="sendMessage()"
            />
            <div class="ai-composer-toolbar">
              <button type="button" class="ai-save-prompt-btn" :disabled="!inputMessage.trim()" @click="openPromptModal(null, inputMessage)" title="Сохранить как промпт">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>
              </button>
              <span class="ai-composer-toolbar-spacer"></span>
              <button type="submit" class="ai-send-btn" :disabled="sending || !inputMessage.trim() || !selectedProjectId">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/></svg>
              </button>
            </div>
          </form>
          <p class="ai-composer-hint">1 запрос из лимита тарифа за каждое отправленное сообщение.</p>
        </div>
      </section>
    </div>

    <!-- Prompt modal -->
    <Teleport to="body">
      <div v-if="promptModalOpen" class="fixed inset-0 z-[9000] flex items-center justify-center bg-black/50 p-4" @click.self="closePromptModal">
        <form class="w-full max-w-[33.3333rem] rounded-[1.3889rem] bg-white dark:bg-[#2C2F3D] dark:border dark:border-white/10 p-[2.0833rem] shadow-[0_1.3889rem_3.4722rem_rgba(0,0,0,0.12)]" @submit.prevent="savePrompt">
          <h4 class="text-[1.3889rem] font-bold text-[#171717] dark:text-gray-100 mb-[0.3472rem]">{{ editingPromptId ? 'Редактировать промпт' : 'Новый промпт' }}</h4>
          <p class="text-[0.9028rem] text-[rgba(105,105,105,0.56)] dark:text-white/55 mb-[1.3889rem]">Проект и период добавляются автоматически.</p>
          <div class="flex flex-col gap-[1.0417rem] mb-[1.7361rem]">
            <div>
              <label class="block text-[0.9028rem] font-medium text-[#696969] dark:text-white/55 mb-[0.4861rem]">Название</label>
              <input v-model="promptForm.title" type="text" maxlength="120" class="ai-input w-full" placeholder="Например: Проверить CPL" />
            </div>
            <div>
              <label class="block text-[0.9028rem] font-medium text-[#696969] dark:text-white/55 mb-[0.4861rem]">Текст промпта</label>
              <textarea v-model="promptForm.text" rows="5" class="ai-input w-full resize-y" placeholder="Что нужно спросить у ассистента" />
            </div>
          </div>
          <div class="flex justify-end gap-[0.6944rem]">
            <button type="button" class="ai-btn-secondary" @click="closePromptModal">Отмена</button>
            <button type="submit" class="ai-btn-primary" :disabled="savingPrompt || !promptForm.title.trim() || !promptForm.text.trim()">
              {{ savingPrompt ? 'Сохраняем…' : 'Сохранить' }}
            </button>
          </div>
        </form>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import {
  ArrowUpRightIcon,
  PencilSquareIcon,
  PlusIcon,
  SparklesIcon,
  TrashIcon,
} from '@heroicons/vue/24/outline'
import api from '../../api/axios'
import { useProjects } from '../../composables/useProjects'
import { useToaster } from '../../composables/useToaster'
import DateRangePicker from '../../components/ui/DateRangePicker.vue'

const route = useRoute()
const toaster = useToaster()
const { projects, currentProjectId, fetchProjects, setCurrentProject, isLoading: projectsLoading } = useProjects()

const selectedProjectId = ref(currentProjectId.value || '')
const startDate = ref('')
const endDate = ref('')
const dateRange = ref({ start: null, end: null })
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
const openSelect = ref(null)

const quota = reactive({ used: 0, limit: 0, remaining: 0, reset_date: null })
const contextState = reactive({ has_data: true, has_integrations: true, alerts: [] })
const promptForm = reactive({ title: '', text: '' })

const currentProjectName = computed(() => {
  const project = projects.value.find((item) => item.id === selectedProjectId.value)
  return project?.name || project?.title || 'Проект не выбран'
})

const displayPeriod = computed(() => `${formatDate(startDate.value)} — ${formatDate(endDate.value)}`)

const toggleSelect = (name) => { openSelect.value = openSelect.value === name ? null : name }

const setDefaultDates = () => {
  const end = new Date()
  const start = new Date()
  start.setDate(end.getDate() - 29)
  startDate.value = toInputDate(start)
  endDate.value = toInputDate(end)
  dateRange.value = { start: toInputDate(start), end: toInputDate(end) }
}

const onDateRangeChange = (range) => {
  if (range?.start) startDate.value = range.start
  if (range?.end) endDate.value = range.end
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
      params: { client_id: selectedProjectId.value, start_date: startDate.value, end_date: endDate.value },
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

const startNewDialog = () => { activeDialogId.value = null; messages.value = []; inputMessage.value = '' }

const sendPrompt = (prompt) => { inputMessage.value = prompt.text; sendMessage() }

const sendMessage = async () => {
  const text = inputMessage.value.trim()
  if (!text || sending.value || !selectedProjectId.value || quota.remaining <= 0) return
  sending.value = true
  contextError.value = ''
  inputMessage.value = ''
  const optimistic = { localId: `local-${Date.now()}`, role: 'user', content: text }
  messages.value.push(optimistic)
  await scrollToBottom()
  try {
    const { data } = await api.post('ai/chat', {
      client_id: selectedProjectId.value, start_date: startDate.value, end_date: endDate.value,
      dialog_id: activeDialogId.value, message: text,
    })
    activeDialogId.value = data.dialog_id
    const index = messages.value.findIndex((item) => item.localId === optimistic.localId)
    if (index >= 0) messages.value.splice(index, 1, data.user_message)
    messages.value.push(data.assistant_message)
    applyQuota(data.quota)
    await loadDialogs()
  } catch (error) {
    messages.value = messages.value.filter((item) => item.localId !== optimistic.localId)
    contextError.value = error.response?.data?.detail || 'Не удалось получить ответ ассистента.'
    toaster.error(contextError.value)
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

const closePromptModal = () => { promptModalOpen.value = false; editingPromptId.value = null; promptForm.title = ''; promptForm.text = '' }

const savePrompt = async () => {
  if (!promptForm.title.trim() || !promptForm.text.trim()) return
  savingPrompt.value = true
  const payload = { title: promptForm.title.trim(), text: promptForm.text.trim() }
  try {
    if (editingPromptId.value) await api.put(`ai/prompts/${editingPromptId.value}`, payload)
    else await api.post('ai/prompts', payload)
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
  try { await api.delete(`ai/prompts/${id}`); prompts.value = prompts.value.filter((item) => item.id !== id) }
  catch (error) { toaster.error(error.response?.data?.detail || 'Не удалось удалить промпт.') }
}

const redirectPath = (target) => target === 'audit' ? '/ai-audit' : target === 'reports' ? '/reports' : '/ai-analysis'
const redirectLabel = (target) => target === 'audit' ? 'Открыть AI-аудит' : target === 'reports' ? 'Открыть отчёты' : 'Открыть раздел'

const scrollToBottom = async () => { await nextTick(); const el = messagesContainer.value; if (el) el.scrollTop = el.scrollHeight }

watch(selectedProjectId, async (value, oldValue) => {
  if (!value || value === oldValue) return
  setCurrentProject(value)
  startNewDialog()
  await Promise.all([loadContext(), loadDialogs()])
})

watch([startDate, endDate], async () => { await loadContext() })

onMounted(async () => {
  setDefaultDates()
  await fetchProjects()
  if (typeof route.query.project === 'string') selectedProjectId.value = route.query.project
  if (typeof route.query.start_date === 'string') startDate.value = route.query.start_date
  if (typeof route.query.end_date === 'string') endDate.value = route.query.end_date
  const selectedExists = projects.value.some((project) => project.id === selectedProjectId.value)
  if ((!selectedProjectId.value || !selectedExists) && projects.value.length) {
    selectedProjectId.value = projects.value[0].id
    setCurrentProject(selectedProjectId.value)
  }
  inputMessage.value = typeof route.query.question === 'string' ? route.query.question : ''
  await Promise.all([loadContext(), loadDialogs(), loadPrompts()])
})

const vClickOutside = {
  mounted(el, binding) { el._outsideHandler = (e) => { if (!el.contains(e.target)) binding.value(e) }; document.addEventListener('mousedown', el._outsideHandler) },
  unmounted(el) { document.removeEventListener('mousedown', el._outsideHandler) },
}
</script>

<style scoped>
/* Custom select (same as project pages) */
.custom-select { position: relative; display: inline-flex; flex-direction: column; }
.cs-head { display: inline-flex; align-items: center; min-height: 3.1944rem; padding: 0.5556rem 1.1806rem; font-size: 0.9028rem; font-weight: 500; color: rgba(0,0,0,0.4); background: #fff; border: 1px solid transparent; border-radius: 1.0417rem; cursor: pointer; outline: none; user-select: none; white-space: nowrap; transition: border-color 0.2s; }
.custom-select.open .cs-head { border-color: rgba(0,0,0,0.1); }
.cs-current { margin-right: 1.7361rem; }
.cs-arrow { display: flex; align-items: center; justify-content: center; width: 1.1111rem; height: 1.1111rem; background: #f5f7f9; border-radius: 50%; flex-shrink: 0; transition: transform 0.3s; }
.custom-select.open .cs-arrow { transform: rotate(180deg); }
.cs-list { position: absolute; top: calc(100% + 0.2778rem); left: 0; z-index: 99; display: flex; min-width: 100%; flex-direction: column; background: #fff; border-radius: 0.5556rem; box-shadow: 0 0 0 1px rgba(68,68,68,0.1); opacity: 0; pointer-events: none; transform: scale(0.75) translateY(-1.4583rem); transform-origin: 50% 0; transition: transform 0.2s cubic-bezier(0.5,0,0,1.25), opacity 0.15s ease-out; }
.custom-select.open .cs-list { opacity: 1; pointer-events: auto; transform: scale(1) translateY(0); }
.cs-option { padding: 0.8333rem 1.1806rem; font-size: 0.9028rem; font-weight: 400; color: rgba(0,0,0,0.7); text-align: left; white-space: nowrap; cursor: pointer; transition: background 0.2s; border: 0; background: transparent; }
.cs-option:hover { background: #f5f7f9; }
.cs-option.selected { font-weight: 600; }

/* Quota badge */
.ai-quota-badge { display: inline-flex; align-items: center; gap: 0.4861rem; min-height: 3.1944rem; padding: 0 1.0417rem; border-radius: 1.0417rem; background: linear-gradient(270deg, #06b5d4 0.35%, #1f9de4 32.08%, #2563eb 96.51%); color: #fff; font-size: 0.9028rem; white-space: nowrap; }
.ai-quota-badge strong { font-weight: 700; }
.ai-quota-badge span { opacity: 0.85; font-size: 0.7639rem; }
.ai-quota-badge--empty { background: #ef4444; }

/* Shell */
.ai-shell { display: grid; grid-template-columns: 17.3611rem minmax(0,1fr); gap: 1.0417rem; flex: 1; min-height: 0; }

/* Rail */
.ai-rail { background: #fff; border: 1px solid rgba(0,0,0,0.05); border-radius: 1.0417rem; padding: 0.8333rem; display: flex; flex-direction: column; gap: 0.6944rem; overflow-y: auto; }
:global(.dark) .ai-rail { background: #2C2F3D; border-color: rgba(255,255,255,0.08); }

.ai-rail-section--border { border-top: 1px solid rgba(0,0,0,0.06); padding-top: 0.6944rem; }
:global(.dark) .ai-rail-section--border { border-top-color: rgba(255,255,255,0.08); }

.ai-rail-head { display: flex; align-items: center; justify-content: space-between; gap: 0.5rem; margin-bottom: 0.4861rem; }

.ai-icon-btn { width: 1.6667rem; height: 1.6667rem; border-radius: 0.4861rem; border: 1px solid rgba(0,0,0,0.08); background: #f5f7f9; color: #2563eb; display: inline-flex; align-items: center; justify-content: center; cursor: pointer; transition: background 0.2s; }
.ai-icon-btn:hover { background: #ecf3fe; }
:global(.dark) .ai-icon-btn { background: rgba(255,255,255,0.08); border-color: rgba(255,255,255,0.1); color: #4A7AFF; }

.ai-dialog-item { width: 100%; border: 0; border-radius: 0.6944rem; background: transparent; padding: 0.5556rem 0.6944rem; text-align: left; display: flex; flex-direction: column; gap: 0.1389rem; cursor: pointer; color: #696969; font-size: 0.8333rem; transition: background 0.15s; }
.ai-dialog-item:hover, .ai-dialog-item--active { background: #ecf3fe; color: #2563eb; }
:global(.dark) .ai-dialog-item:hover, :global(.dark) .ai-dialog-item--active { background: rgba(255,255,255,0.08); color: #4A7AFF; }
.ai-dialog-item span { font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ai-dialog-item small { color: rgba(105,105,105,0.5); font-size: 0.7639rem; }

.ai-prompt-item { display: grid; grid-template-columns: minmax(0,1fr) auto; gap: 0.3472rem; align-items: center; padding: 0.3472rem; border-radius: 0.6944rem; }
.ai-prompt-item:hover { background: #f5f7f9; }
:global(.dark) .ai-prompt-item:hover { background: rgba(255,255,255,0.05); }
.ai-prompt-main { min-width: 0; border: 0; background: transparent; text-align: left; cursor: pointer; padding: 0.2778rem; }
.ai-prompt-main span { display: block; color: #171717; font-weight: 600; font-size: 0.8333rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
:global(.dark) .ai-prompt-main span { color: rgba(255,255,255,0.85); }
.ai-prompt-main small { display: block; margin-top: 0.1389rem; color: rgba(105,105,105,0.5); font-size: 0.7639rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ai-prompt-actions { display: flex; gap: 0.1389rem; }
.ai-prompt-actions button { width: 1.5278rem; height: 1.5278rem; border-radius: 0.3472rem; border: 1px solid rgba(0,0,0,0.06); background: #fff; color: #696969; display: inline-flex; align-items: center; justify-content: center; cursor: pointer; }
.ai-prompt-actions svg { width: 0.8333rem; height: 0.8333rem; }
:global(.dark) .ai-prompt-actions button { background: rgba(255,255,255,0.05); border-color: rgba(255,255,255,0.08); color: rgba(255,255,255,0.55); }

.ai-rail-empty { padding: 0.5556rem 0.6944rem; border-radius: 0.5556rem; color: rgba(105,105,105,0.5); background: #f5f7f9; font-size: 0.8333rem; }
:global(.dark) .ai-rail-empty { background: rgba(255,255,255,0.05); color: rgba(255,255,255,0.35); }

/* Chat */
.ai-chat { min-width: 0; display: grid; grid-template-rows: minmax(0,1fr) auto; overflow: hidden; background: #fff; border: 1px solid rgba(0,0,0,0.05); border-radius: 1.0417rem; }
:global(.dark) .ai-chat { background: #2C2F3D; border-color: rgba(255,255,255,0.08); }

.ai-messages { min-height: 0; overflow-y: auto; padding: 1.0417rem; display: flex; flex-direction: column; gap: 0.6944rem; }

.ai-intro-card { display: flex; gap: 0.8333rem; padding: 1.0417rem; border-radius: 0.8333rem; background: #f0f7ff; border: 1px solid #dcecff; }
:global(.dark) .ai-intro-card { background: rgba(37,99,235,0.08); border-color: rgba(37,99,235,0.15); }

.ai-avatar { width: 2.5rem; height: 2.5rem; border-radius: 0.6944rem; background: linear-gradient(270deg, #06b5d4 0.35%, #1f9de4 32.08%, #2563eb 96.51%); color: #fff; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }

.ai-state-card { padding: 0.8333rem 1.0417rem; border-radius: 0.6944rem; font-size: 0.9028rem; }
.ai-state-card--warning { background: #fff7ed; border: 1px solid #fed7aa; color: #9a3412; }
:global(.dark) .ai-state-card--warning { background: rgba(234,88,12,0.1); border-color: rgba(234,88,12,0.2); color: #fb923c; }

.ai-suggestions { display: flex; flex-wrap: wrap; gap: 0.4861rem; }
.ai-suggestions button { border: 1px solid #dcecff; background: #fff; color: #2563eb; border-radius: 2.7778rem; padding: 0.5556rem 1.0417rem; font-size: 0.9028rem; font-weight: 600; cursor: pointer; transition: background 0.2s, border-color 0.2s; }
.ai-suggestions button:hover { background: #ecf3fe; border-color: #2563eb; }
:global(.dark) .ai-suggestions button { background: rgba(255,255,255,0.05); border-color: rgba(255,255,255,0.1); color: #4A7AFF; }

.ai-msg { display: flex; }
.ai-msg--user { justify-content: flex-end; }
.ai-msg--assistant { justify-content: flex-start; }
.ai-msg-bubble { max-width: min(41.6667rem, 78%); border-radius: 0.8333rem; padding: 0.6944rem 1.0417rem; line-height: 1.5; white-space: pre-wrap; font-size: 0.9722rem; }
.ai-msg-bubble p { margin: 0; }
.ai-msg--user .ai-msg-bubble { background: linear-gradient(270deg, #06b5d4 0.35%, #1f9de4 32.08%, #2563eb 96.51%); color: #fff; border-bottom-right-radius: 0.2083rem; }
.ai-msg--assistant .ai-msg-bubble { background: #f5f7f9; color: #171717; border-bottom-left-radius: 0.2083rem; }
:global(.dark) .ai-msg--assistant .ai-msg-bubble { background: rgba(255,255,255,0.08); color: rgba(255,255,255,0.88); }

.ai-redirect { margin-top: 0.5556rem; display: inline-flex; align-items: center; gap: 0.2778rem; color: #2563eb; font-weight: 600; font-size: 0.9028rem; text-decoration: none; }
.ai-redirect svg { width: 0.8333rem; height: 0.8333rem; }
:global(.dark) .ai-redirect { color: #4A7AFF; }

.ai-typing { display: inline-flex; gap: 0.2778rem; align-items: center; padding: 0.8333rem 1.0417rem; }
.ai-typing span { width: 0.4167rem; height: 0.4167rem; border-radius: 50%; background: #2563eb; animation: ai-pulse 1s infinite ease-in-out; }
.ai-typing span:nth-child(2) { animation-delay: 0.15s; }
.ai-typing span:nth-child(3) { animation-delay: 0.3s; }

/* Composer */
.ai-composer { border-top: 1px solid rgba(0,0,0,0.06); padding: 0.8333rem 1.0417rem; }
:global(.dark) .ai-composer { border-top-color: rgba(255,255,255,0.08); }

.ai-composer-form { display: flex; flex-direction: column; border: 1.5px solid rgba(0,0,0,0.09); border-radius: 0.9722rem; background: #f8f9fb; overflow: hidden; transition: border-color 0.18s, box-shadow 0.18s; }
.ai-composer-form:focus-within { border-color: rgba(37,99,235,0.38); box-shadow: 0 0 0 3px rgba(37,99,235,0.08); }
:global(.dark) .ai-composer-form { background: rgba(255,255,255,0.06); border-color: rgba(255,255,255,0.1); }
:global(.dark) .ai-composer-form:focus-within { border-color: rgba(74,122,255,0.4); box-shadow: 0 0 0 3px rgba(74,122,255,0.1); }

.ai-composer-form textarea { flex: 1; min-height: 2.9167rem; max-height: 7.6389rem; resize: none; border: none; background: transparent; color: #171717; padding: 0.7639rem 0.9722rem; outline: none; font: inherit; font-size: 0.9028rem; line-height: 1.55; }
:global(.dark) .ai-composer-form textarea { color: rgba(255,255,255,0.88); }
.ai-composer-form textarea::placeholder { color: rgba(105,105,105,0.5); }
:global(.dark) .ai-composer-form textarea::placeholder { color: rgba(255,255,255,0.3); }

.ai-composer-toolbar { display: flex; align-items: center; gap: 0.3472rem; padding: 0.4167rem 0.5556rem; border-top: 1px solid rgba(0,0,0,0.06); }
:global(.dark) .ai-composer-toolbar { border-top-color: rgba(255,255,255,0.07); }
.ai-composer-toolbar-spacer { flex: 1; }

.ai-save-prompt-btn { display: flex; align-items: center; justify-content: center; width: 2.0833rem; height: 2.0833rem; border: none; border-radius: 0.5556rem; background: transparent; color: rgba(105,105,105,0.6); cursor: pointer; transition: background 0.15s, color 0.15s; flex-shrink: 0; }
.ai-save-prompt-btn:hover { background: rgba(37,99,235,0.08); color: #2563eb; }
.ai-save-prompt-btn:disabled { opacity: 0.35; cursor: not-allowed; }
:global(.dark) .ai-save-prompt-btn { color: rgba(255,255,255,0.4); }
:global(.dark) .ai-save-prompt-btn:hover { background: rgba(74,122,255,0.12); color: #4A7AFF; }

.ai-send-btn { display: flex; align-items: center; justify-content: center; width: 2.3611rem; height: 2.3611rem; border: none; border-radius: 0.6944rem; background: linear-gradient(270deg, #06b5d4 0.35%, #1f9de4 32.08%, #2563eb 96.51%); color: #fff; cursor: pointer; transition: opacity 0.15s, transform 0.2s cubic-bezier(0.16,1,0.3,1); flex-shrink: 0; }
.ai-send-btn:hover { opacity: 0.88; transform: scale(1.06); }
.ai-send-btn:disabled { opacity: 0.35; cursor: not-allowed; transform: none; }

.ai-composer-hint { margin: 0.4167rem 0 0; color: rgba(105,105,105,0.4); font-size: 0.7639rem; }
:global(.dark) .ai-composer-hint { color: rgba(255,255,255,0.28); }

.ai-limit-card { display: flex; align-items: center; justify-content: space-between; gap: 1.0417rem; border-radius: 0.8333rem; padding: 0.8333rem 1.0417rem; background: #fff7ed; color: #9a3412; }
:global(.dark) .ai-limit-card { background: rgba(234,88,12,0.1); color: #fb923c; }
.ai-limit-card strong, .ai-limit-card span { display: block; font-size: 0.9028rem; }
.ai-limit-card strong { font-weight: 700; }
.ai-limit-card span { font-weight: 400; opacity: 0.8; margin-top: 0.1389rem; }
.ai-limit-btn { display: inline-flex; align-items: center; min-height: 3.1944rem; padding: 0 1.3889rem; border-radius: 0.8333rem; background: linear-gradient(270deg, #06b5d4 0.35%, #1f9de4 32.08%, #2563eb 96.51%); color: #fff; font-weight: 600; font-size: 0.9028rem; text-decoration: none; white-space: nowrap; transition: transform 0.3s; }
.ai-limit-btn:hover { transform: scale(1.03); }

/* Inputs */
.ai-input { padding: 0.6944rem 0.8333rem; border-radius: 0.6944rem; font-size: 0.9028rem; background: #f5f7f9; border: 1px solid transparent; outline: none; color: #171717; transition: border-color 0.2s; font: inherit; }
.ai-input:focus { border-color: #2563eb; }
:global(.dark) .ai-input { background: rgba(255,255,255,0.08); color: rgba(255,255,255,0.88); }

.ai-btn-primary { display: inline-flex; align-items: center; justify-content: center; min-height: 3.0556rem; padding: 0 1.3889rem; border-radius: 0.8333rem; font-size: 0.9722rem; font-weight: 500; color: #fff; background: #2563eb; border: none; cursor: pointer; transition: background 0.2s; }
.ai-btn-primary:hover { background: #1d4ed8; }
.ai-btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.ai-btn-secondary { display: inline-flex; align-items: center; justify-content: center; min-height: 3.0556rem; padding: 0 1.3889rem; border-radius: 0.8333rem; font-size: 0.9722rem; font-weight: 500; color: #696969; background: #fff; border: 1px solid rgba(0,0,0,0.1); cursor: pointer; }
:global(.dark) .ai-btn-secondary { background: rgba(255,255,255,0.05); border-color: rgba(255,255,255,0.15); color: rgba(255,255,255,0.7); }

@keyframes ai-pulse { 0%,80%,100% { transform: scale(0.75); opacity: 0.45; } 40% { transform: scale(1); opacity: 1; } }

@media (max-width: 980px) {
  .ai-shell { grid-template-columns: 1fr; }
  .ai-rail { max-height: 20.8333rem; }
  .ai-composer-form { flex-direction: column; }
  .ai-msg-bubble { max-width: 92%; }
}
</style>
