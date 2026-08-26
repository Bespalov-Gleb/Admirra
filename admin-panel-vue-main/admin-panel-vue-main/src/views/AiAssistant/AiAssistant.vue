<template>
  <section ref="pageRef" class="assistant-page" :class="{ 'assistant-page--dark': isDarkMode }">
    <aside class="assistant-rail" :class="{ 'assistant-rail--open': railOpen }" aria-label="История ассистента">
      <div v-if="!railOpen" class="assistant-rail__compact">
        <button class="rail-icon-button" type="button" title="Открыть историю" aria-label="Открыть историю" @click="railOpen = true">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 7h14M5 12h14M5 17h9"/></svg>
        </button>
        <button class="rail-icon-button" type="button" title="Новый диалог" aria-label="Новый диалог" @click="newChat">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>
        </button>
        <button class="rail-icon-button" type="button" title="Сохранённые вопросы" aria-label="Сохранённые вопросы">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 4.5h10a1.5 1.5 0 0 1 1.5 1.5v13l-6.5-3.5L5.5 19V6A1.5 1.5 0 0 1 7 4.5Z"/></svg>
        </button>
      </div>

      <div v-else class="assistant-rail__expanded">
        <div class="rail-heading">
          <span>История</span>
          <button class="rail-icon-button" type="button" title="Свернуть историю" aria-label="Свернуть историю" @click="railOpen = false">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m14.5 6-6 6 6 6"/></svg>
          </button>
        </div>

        <button class="rail-new-chat" type="button" @click="newChat">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>
          <span>Новый диалог</span>
        </button>

        <div class="rail-history">
          <button
            v-for="conv in conversations"
            :key="conv.id"
            type="button"
            class="rail-history__item"
            :class="{ 'is-active': conv.id === activeConversationId }"
            :title="conv.title"
            @click="selectConversation(conv.id)"
          >
            <span class="rail-history__title">{{ conv.title || 'Без названия' }}</span>
            <span class="rail-history__date">{{ formatChatDate(conv.updated_at) }}</span>
          </button>

          <div v-if="!conversations.length" class="rail-history__empty">Здесь появятся ваши вопросы.</div>
        </div>
      </div>
    </aside>

    <section class="assistant-stage" aria-label="AI-ассистент">
      <header class="assistant-stage__head">
        <h1>Ассистент</h1>
      </header>

      <div v-if="!hasThread" ref="emptyScroll" class="assistant-empty" @scroll="onEmptyScroll">
        <div class="assistant-hero">
          <span class="assistant-welcome__spark">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 3 1.6 5.4L19 10l-5.4 1.6L12 17l-1.6-5.4L5 10l5.4-1.6L12 3Z"/></svg>
          </span>
          <h2 class="assistant-hero__title">Спросите про свою рекламу</h2>
          <p class="assistant-hero__sub">{{ projectContextDescription }}</p>
          <p v-if="!configured" class="assistant-welcome__note">Ассистент скоро будет доступен — подключается модель.</p>

          <div class="assistant-composer">
            <textarea
              ref="textarea"
              v-model="prompt"
              rows="1"
              aria-label="Запрос ассистенту"
              placeholder="Назовите проект и задайте вопрос — например: посчитай CPL по Директу за июль"
              @input="autoGrow"
              @keydown.enter.exact.prevent="sendPrompt"
            ></textarea>
            <div class="assistant-composer__actions">
              <div class="assistant-model" v-click-outside="() => (modelMenuOpen = false)">
                <button type="button" class="assistant-model__btn" @click="modelMenuOpen = !modelMenuOpen">
                  <span>Модель · <b>{{ selectedModel.label }}</b></span>
                  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m7 10 5 5 5-5"/></svg>
                </button>
                <div v-if="modelMenuOpen" class="assistant-model__menu">
                  <button v-for="m in models" :key="m.id" type="button" :title="m.description" :class="{ 'is-active': m.id === selectedModelId }" @click="pickModel(m.id)">{{ m.label }}</button>
                </div>
              </div>
              <div v-if="selectedModel.reasoning" class="assistant-model" v-click-outside="() => (effortMenuOpen = false)">
                <button type="button" class="assistant-model__btn" @click="effortMenuOpen = !effortMenuOpen">
                  <span>Глубина · <b>{{ effortLabel }}</b></span>
                  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m7 10 5 5 5-5"/></svg>
                </button>
                <div v-if="effortMenuOpen" class="assistant-model__menu">
                  <button v-for="e in selectedModel.efforts" :key="e" type="button" :class="{ 'is-active': e === selectedEffort }" @click="pickEffort(e)">{{ effortName(e) }}</button>
                </div>
              </div>
              <button class="composer-send" type="button" aria-label="Отправить" :class="{ 'is-active': prompt.trim() && !sending }" :disabled="sending" @click="sendPrompt">
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12 14-7-4.5 14-3-5-6.5-2Z"/><path d="m11.5 14 2.2-2.2"/></svg>
              </button>
            </div>
          </div>

          <div class="assistant-sources">
            <span class="assistant-sources__label">Источники данных</span>
            <div class="assistant-sources__grid">
              <div v-for="s in dataSources" :key="s.name" class="source-chip" :class="{ 'source-chip--off': !s.available }">
                <span class="source-chip__mark" :style="{ background: s.color, color: s.ink }">{{ s.mark }}</span>
                <span class="source-chip__name">{{ s.name }}</span>
                <span class="source-chip__status">{{ s.available ? 'доступно' : 'скоро' }}</span>
              </div>
            </div>
          </div>

          <button type="button" class="assistant-scrollhint" @click="scrollToPrompts">
            <span>Готовые промпты</span>
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m7 10 5 5 5-5"/></svg>
          </button>
        </div>

        <div ref="promptsSection" class="assistant-prompts">
          <h3 class="assistant-prompts__title">Готовые промпты</h3>
          <div class="assistant-prompts__grid">
            <div
              v-for="(p, i) in readyPrompts"
              :key="i"
              class="prompt-tile"
              :class="{ 'is-visible': promptsVisible }"
              :style="{ transitionDelay: `${Math.min(i, 8) * 45}ms` }"
              role="button"
              tabindex="0"
              @click="fillPrompt(p.prompt)"
              @keydown.enter.prevent="fillPrompt(p.prompt)"
            >
              <div class="prompt-tile__head">
                <b class="prompt-tile__title">{{ p.title }}</b>
                <button
                  type="button"
                  class="prompt-tile__copy"
                  :class="{ 'is-copied': copiedIndex === i }"
                  :aria-label="copiedIndex === i ? 'Скопировано' : 'Скопировать промпт'"
                  @click.stop="copyPrompt(p.prompt, i)"
                >
                  <svg v-if="copiedIndex !== i" viewBox="0 0 24 24" aria-hidden="true"><rect x="9" y="9" width="11" height="11" rx="2.2"/><path d="M5 15V6.5A2.5 2.5 0 0 1 7.5 4H16"/></svg>
                  <svg v-else viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12.5 4.4 4.4L19 7.2"/></svg>
                </button>
              </div>
              <span class="prompt-tile__desc">{{ p.desc }}</span>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="assistant-thread">
        <div ref="threadInner" class="assistant-thread__inner">
          <div v-for="(message, i) in activeMessages" :key="i" :class="['assistant-message', `assistant-message--${message.role}`]">
            <template v-if="message.role === 'assistant'">
              <span class="assistant-message__avatar"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 3 1.6 5.4L19 10l-5.4 1.6L12 17l-1.6-5.4L5 10l5.4-1.6L12 3Z"/></svg></span>
              <div class="assistant-message__body">
                <div class="assistant-message__bubble">
                  <p class="assistant-message__text">{{ message.content }}<span v-if="message.pending && !message.content" class="assistant-caret">▍</span></p>
                  <div v-if="message.pending && toolActivity" class="assistant-tool-note">Смотрю данные: {{ toolActivity }}…</div>
                </div>
              </div>
            </template>
            <div v-else class="assistant-message__bubble">{{ message.content }}</div>
          </div>
        </div>

        <div class="assistant-thread__composer">
          <div class="assistant-composer">
            <textarea
              ref="threadTextarea"
              v-model="prompt"
              rows="1"
              aria-label="Уточнить вопрос"
              placeholder="Уточните: «за прошлую неделю», «только по Директу»…"
              @input="autoGrow"
              @keydown.enter.exact.prevent="sendPrompt"
            ></textarea>
            <div class="assistant-composer__actions">
              <div class="assistant-model" v-click-outside="() => (modelMenuOpen = false)">
                <button type="button" class="assistant-model__btn" @click="modelMenuOpen = !modelMenuOpen">
                  <span>Модель · <b>{{ selectedModel.label }}</b></span>
                  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m7 10 5 5 5-5"/></svg>
                </button>
                <div v-if="modelMenuOpen" class="assistant-model__menu assistant-model__menu--up">
                  <button v-for="m in models" :key="m.id" type="button" :title="m.description" :class="{ 'is-active': m.id === selectedModelId }" @click="pickModel(m.id)">{{ m.label }}</button>
                </div>
              </div>
              <div v-if="selectedModel.reasoning" class="assistant-model" v-click-outside="() => (effortMenuOpen = false)">
                <button type="button" class="assistant-model__btn" @click="effortMenuOpen = !effortMenuOpen">
                  <span>Глубина · <b>{{ effortLabel }}</b></span>
                  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m7 10 5 5 5-5"/></svg>
                </button>
                <div v-if="effortMenuOpen" class="assistant-model__menu assistant-model__menu--up">
                  <button v-for="e in selectedModel.efforts" :key="e" type="button" :class="{ 'is-active': e === selectedEffort }" @click="pickEffort(e)">{{ effortName(e) }}</button>
                </div>
              </div>
              <button class="composer-send" type="button" aria-label="Отправить" :class="{ 'is-active': prompt.trim() && !sending }" :disabled="sending" @click="sendPrompt"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12 14-7-4.5 14-3-5-6.5-2Z"/><path d="m11.5 14 2.2-2.2"/></svg></button>
            </div>
          </div>
        </div>
      </div>
    </section>
  </section>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useTheme } from '../../composables/useTheme'
import api from '../../api/axios'
import { getAccessToken } from '../../utils/authToken'

const { isDarkMode } = useTheme()

const railOpen = ref(false)
const prompt = ref('')
const pageRef = ref(null)
const textarea = ref(null)
const threadTextarea = ref(null)
const threadInner = ref(null)
const sending = ref(false)
const toolActivity = ref('')

// ── Модели и режим размышлений (из GET /assistant/models) ────────────────────
const models = ref([])
const configured = ref(true)
const selectedModelId = ref('')
const modelMenuOpen = ref(false)
const effortMenuOpen = ref(false)
const selectedEffort = ref('medium')
const FALLBACK_MODEL = { id: '', label: '—', description: '', reasoning: false, efforts: [], default_effort: null }
const selectedModel = computed(() => models.value.find((m) => m.id === selectedModelId.value) || models.value[0] || FALLBACK_MODEL)
const EFFORT_LABELS = { none: 'Выкл', low: 'Низкая', medium: 'Средняя', high: 'Высокая' }
const effortName = (e) => EFFORT_LABELS[e] || e
const effortLabel = computed(() => effortName(selectedEffort.value))

const syncEffortToModel = () => {
  const m = selectedModel.value
  if (!m.reasoning) { selectedEffort.value = 'none'; return }
  if (!m.efforts.includes(selectedEffort.value)) selectedEffort.value = m.default_effort || 'medium'
}
const pickModel = (id) => { selectedModelId.value = id; modelMenuOpen.value = false; syncEffortToModel() }
const pickEffort = (e) => { selectedEffort.value = e; effortMenuOpen.value = false }

// Локальная директива v-click-outside (глобально в проекте не зарегистрирована).
const vClickOutside = {
  mounted(el, binding) {
    el._outsideHandler = (event) => { if (!el.contains(event.target)) binding.value(event) }
    document.addEventListener('mousedown', el._outsideHandler)
  },
  unmounted(el) { document.removeEventListener('mousedown', el._outsideHandler) },
}

const projectContextDescription = 'Назовите проект или спросите, какие доступны — и я проанализирую его рекламу: расход, лиды, CPL, цели Метрики. Ещё умею Wordstat.'

// ── Экран приветствия: источники данных и готовые промпты ────────────────────
const dataSources = [
  { name: 'Яндекс Директ', mark: 'Д', color: '#ffcc00', ink: '#1b2437', available: true },
  { name: 'Яндекс Метрика', mark: 'М', color: '#ff5252', ink: '#ffffff', available: true },
  { name: 'Wordstat', mark: 'W', color: '#f2673d', ink: '#ffffff', available: true },
  { name: 'Avito', mark: 'A', color: '#00c2a8', ink: '#ffffff', available: false },
  { name: 'VK Реклама', mark: 'VK', color: '#0a7cff', ink: '#ffffff', available: false },
]

// Макетные готовые промпты (реальные добавим позже). Клик по плитке — вставить
// в поле ввода, кнопка копирования — скопировать текст промпта.
const readyPrompts = [
  { title: 'Аудит Директа', desc: 'Кампании, расход, CTR и явные проблемы за месяц.', prompt: 'Сделай аудит Яндекс.Директа за последний месяц: расход, клики, CTR и где явные проблемы.' },
  { title: 'Дорогие кампании по CPL', desc: 'Кампании с самым высоким CPL относительно цели.', prompt: 'Найди кампании Директа с самым высоким CPL за последний месяц и покажи их расход и лиды.' },
  { title: 'Динамика лидов', desc: 'Конверсии по дням за последние 30 дней.', prompt: 'Покажи динамику конверсий (лидов) по дням за последние 30 дней из Метрики.' },
  { title: 'Куда уходит бюджет', desc: 'Разбивка расхода по кампаниям, где отдача низкая.', prompt: 'Разбей расход Директа по кампаниям за месяц и выдели кампании с низкой отдачей.' },
  { title: 'Спрос по фразе · Wordstat', desc: 'Частотность, динамика и регионы по фразе.', prompt: 'Собери в Wordstat спрос по фразе «» — общую частотность, динамику и распределение по регионам.' },
  { title: 'Сравнение с прошлым месяцем', desc: 'Расход, лиды и CPL — что изменилось.', prompt: 'Сравни расход, лиды и CPL с прошлым месяцем и объясни ключевые изменения.' },
]

const emptyScroll = ref(null)
const promptsSection = ref(null)
const promptsVisible = ref(false)
const copiedIndex = ref(-1)
let _copyTimer = null

const onEmptyScroll = () => {
  if (!promptsVisible.value && emptyScroll.value && emptyScroll.value.scrollTop > 40) promptsVisible.value = true
}

const scrollToPrompts = () => {
  promptsVisible.value = true
  promptsSection.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const copyPrompt = async (text, i) => {
  try { await navigator.clipboard.writeText(text) } catch { /* clipboard может быть недоступен */ }
  copiedIndex.value = i
  clearTimeout(_copyTimer)
  _copyTimer = setTimeout(() => { copiedIndex.value = -1 }, 1600)
}

const fillPrompt = async (text) => {
  prompt.value = text
  emptyScroll.value?.scrollTo({ top: 0, behavior: 'smooth' })
  await nextTick(); autoGrow()
  textarea.value?.focus()
}

// ── Диалоги (серверная история) ──────────────────────────────────────────────
const conversations = ref([])
const activeConversationId = ref(null)
const activeMessages = ref([])
const hasThread = computed(() => activeMessages.value.length > 0)

const formatChatDate = (value) => {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const today = new Date()
  if (date.toDateString() === today.toDateString()) return 'сегодня'
  return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })
}

const loadModels = async () => {
  try {
    const { data } = await api.get('assistant/models')
    models.value = Array.isArray(data.models) ? data.models : []
    configured.value = !!data.configured
    selectedModelId.value = data.default_model || models.value[0]?.id || ''
    syncEffortToModel()
  } catch { /* пустой каталог — покажем недоступность */ }
}

const loadConversations = async () => {
  try {
    const { data } = await api.get('assistant/conversations')
    conversations.value = Array.isArray(data) ? data : []
  } catch { /* ignore */ }
}

const newChat = async () => {
  activeConversationId.value = null
  activeMessages.value = []
  prompt.value = ''
  railOpen.value = false
  await nextTick()
  textarea.value?.focus()
}

const selectConversation = async (id) => {
  railOpen.value = false
  try {
    const { data } = await api.get(`assistant/conversations/${id}`)
    activeConversationId.value = data.id
    activeMessages.value = (data.messages || []).map((m) => ({ role: m.role, content: m.content || '' }))
    await nextTick(); scrollThread()
  } catch { /* ignore */ }
}

const autoGrow = () => {
  const element = hasThread.value ? threadTextarea.value : textarea.value
  if (!element) return
  element.style.height = 'auto'
  element.style.height = `${Math.min(element.scrollHeight, 104)}px`
}

const scrollThread = () => {
  const el = threadInner.value
  if (el) el.scrollTop = el.scrollHeight
}

const TOOL_LABELS = {
  list_projects: 'список проектов',
  use_project: 'выбор проекта',
  direct_get_campaigns: 'кампании Директа',
  direct_get_statistics: 'статистика Директа',
  direct_get_adgroups: 'группы объявлений',
  direct_get_ads: 'объявления Директа',
  direct_get_keywords: 'ключевые слова',
  metrika_get_counters: 'счётчики Метрики',
  metrika_get_goals: 'цели Метрики',
  metrika_get_report: 'отчёт Метрики',
  metrika_get_report_by_time: 'динамика Метрики',
  wordstat_top_requests: 'Wordstat: спрос',
  wordstat_dynamics: 'Wordstat: динамика',
  wordstat_regions: 'Wordstat: регионы',
}
const toolLabel = (name) => TOOL_LABELS[name] || name

const handleEvent = (ev, assistantMsg) => {
  switch (ev.type) {
    case 'meta':
      if (ev.conversation_id) activeConversationId.value = ev.conversation_id
      break
    case 'text':
      assistantMsg.content += ev.delta || ''
      scrollThread()
      break
    case 'tool':
      if (ev.status === 'start') toolActivity.value = toolLabel(ev.name)
      break
    case 'done':
      if (!assistantMsg.content && ev.content) assistantMsg.content = ev.content
      toolActivity.value = ''
      break
    case 'error':
      assistantMsg.content += (assistantMsg.content ? '\n\n' : '') + `⚠️ ${ev.error || 'Ошибка'}`
      toolActivity.value = ''
      break
    default:
      break
  }
}

const consumeSSE = async (stream, assistantMsg) => {
  const reader = stream.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    let idx
    while ((idx = buffer.indexOf('\n\n')) >= 0) {
      const chunk = buffer.slice(0, idx)
      buffer = buffer.slice(idx + 2)
      const line = chunk.split('\n').find((l) => l.startsWith('data:'))
      if (!line) continue
      let ev
      try { ev = JSON.parse(line.slice(5).trim()) } catch { continue }
      handleEvent(ev, assistantMsg)
    }
  }
}

const sendPrompt = async () => {
  const question = prompt.value.trim()
  if (!question || sending.value) return
  sending.value = true
  toolActivity.value = ''

  activeMessages.value.push({ role: 'user', content: question })
  // Берём реактивный прокси из массива — иначе мутации при стриме не обновят UI.
  activeMessages.value.push({ role: 'assistant', content: '', pending: true })
  const assistantMsg = activeMessages.value[activeMessages.value.length - 1]
  prompt.value = ''
  await nextTick(); autoGrow(); scrollThread()

  const token = getAccessToken()
  const body = {
    message: question,
    conversation_id: activeConversationId.value || undefined,
    model: selectedModelId.value || undefined,
    effort: selectedModel.value.reasoning ? selectedEffort.value : undefined,
  }
  try {
    const resp = await fetch('/api/assistant/chat', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: JSON.stringify(body),
    })
    if (!resp.ok || !resp.body) throw new Error(`HTTP ${resp.status}`)
    await consumeSSE(resp.body, assistantMsg)
  } catch {
    if (!assistantMsg.content) assistantMsg.content = 'Не удалось получить ответ. Попробуйте ещё раз.'
  } finally {
    assistantMsg.pending = false
    sending.value = false
    toolActivity.value = ''
    loadConversations()
    await nextTick(); scrollThread(); threadTextarea.value?.focus()
  }
}

// Растягиваем ассистента на всю рабочую область: гасим внутренние отступы
// обёртки <main> и отдаём ей полную высоту, чтобы окно касалось хедера и
// сайдбара без зазоров — при любой высоте хедера и при баннере поддержки.
// Правки держим внутри этого компонента (MainLayout не трогаем).
let _wrapEl = null
const _wrapPrev = { padding: '', height: '', display: '', flexDirection: '', minHeight: '' }

const applyFullBleed = () => {
  const wrap = pageRef.value?.parentElement
  if (!wrap) return
  _wrapEl = wrap
  _wrapPrev.padding = wrap.style.padding
  _wrapPrev.height = wrap.style.height
  _wrapPrev.display = wrap.style.display
  _wrapPrev.flexDirection = wrap.style.flexDirection
  _wrapPrev.minHeight = wrap.style.minHeight
  wrap.style.padding = '0'
  wrap.style.height = '100%'
  wrap.style.minHeight = '0'
  wrap.style.display = 'flex'
  wrap.style.flexDirection = 'column'
}

const clearFullBleed = () => {
  if (!_wrapEl) return
  _wrapEl.style.padding = _wrapPrev.padding
  _wrapEl.style.height = _wrapPrev.height
  _wrapEl.style.minHeight = _wrapPrev.minHeight
  _wrapEl.style.display = _wrapPrev.display
  _wrapEl.style.flexDirection = _wrapPrev.flexDirection
  _wrapEl = null
}

onMounted(() => {
  loadModels()
  loadConversations()
  applyFullBleed()
})

onUnmounted(() => {
  clearFullBleed()
  clearTimeout(_copyTimer)
})
</script>

<style scoped>
.assistant-page {
  --assistant-bg: #ffffff;
  --assistant-panel: #ffffff;
  --assistant-muted: #8d99ad;
  --assistant-text: #1b2437;
  --assistant-sub: #5c6b84;
  --assistant-line: #e6ebf2;
  --assistant-strong-line: #d8e0eb;
  --assistant-soft: #f5f7fa;
  --assistant-blue: #2f6bea;
  --assistant-blue-soft: #eaf0fe;
  --assistant-violet: #7c6ff0;
  --assistant-amber: #bd7d16;
  --assistant-amber-soft: #fff5df;
  --assistant-green: #1fa55b;
  --assistant-green-soft: rgba(31, 165, 91, .13);
  display: flex;
  width: auto;
  /* Full-bleed: padding обёртки <main> гасится в onMounted, а высоту берём
     100% от неё — окно касается хедера и сайдбара без зазоров. */
  margin: 0;
  flex: 1 1 auto;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  background: var(--assistant-bg);
  color: var(--assistant-text);
}

.assistant-page--dark {
  --assistant-bg: #202332;
  --assistant-panel: #1a1d29;
  --assistant-muted: #9ca6ba;
  --assistant-text: #f2f4fb;
  --assistant-sub: #c1c9d8;
  --assistant-line: rgba(255,255,255,.09);
  --assistant-strong-line: rgba(255,255,255,.16);
  --assistant-soft: #282c3d;
  --assistant-blue-soft: rgba(74, 122, 255, .17);
  --assistant-amber-soft: rgba(187, 125, 22, .16);
  --assistant-green: #34c37d;
  --assistant-green-soft: rgba(52, 195, 125, .16);
}

.assistant-rail {
  width: 4rem;
  flex: 0 0 4rem;
  min-width: 0;
  overflow: hidden;
  border-right: 1px solid var(--assistant-line);
  background: var(--assistant-panel);
  transition: width .18s ease, flex-basis .18s ease;
}

.assistant-rail--open { width: 18.5rem; flex-basis: 18.5rem; }
.assistant-rail__compact { display: flex; flex-direction: column; align-items: center; gap: .45rem; padding-top: 1rem; }
.assistant-rail__expanded { display: flex; flex-direction: column; height: 100%; padding: 1rem .85rem .85rem; }

.rail-icon-button,
.composer-icon,
.composer-send,
.assistant-depth button,
.assistant-info-card button,
.assistant-suggestion,
.assistant-message__actions button {
  border: 0;
  font: inherit;
  cursor: pointer;
}

.rail-icon-button { display: grid; width: 2.55rem; height: 2.55rem; place-items: center; border-radius: .7rem; background: transparent; color: var(--assistant-sub); }
.rail-icon-button:hover { background: var(--assistant-soft); color: var(--assistant-text); }
.rail-icon-button svg, .rail-new-chat svg, .assistant-info-card svg, .composer-icon svg, .composer-send svg, .assistant-welcome__spark svg, .assistant-limit svg, .assistant-suggestion__icon :deep(svg), .assistant-message__avatar svg { width: 1.1rem; height: 1.1rem; fill: none; stroke: currentColor; stroke-width: 1.65; stroke-linecap: round; stroke-linejoin: round; }

/* Выбор модели в композере */
.assistant-model { position: relative; margin-left: auto; }
.assistant-model__btn { display: inline-flex; align-items: center; gap: .35rem; height: 2.2rem; padding: 0 .5rem 0 .72rem; border: 1px solid var(--assistant-line); border-radius: .62rem; background: var(--assistant-soft); color: var(--assistant-sub); font: 500 .82rem/1 Inter, sans-serif; cursor: pointer; }
.assistant-model__btn:hover { border-color: var(--assistant-strong-line); }
.assistant-model__btn b { color: var(--assistant-text); font-weight: 600; }
.assistant-model__btn svg { width: .95rem; height: .95rem; flex-shrink: 0; fill: none; stroke: currentColor; stroke-width: 1.7; stroke-linecap: round; stroke-linejoin: round; }
.assistant-model__menu { position: absolute; right: 0; top: calc(100% + .35rem); min-width: 11rem; padding: .3rem; border: 1px solid var(--assistant-strong-line); border-radius: .7rem; background: var(--assistant-panel); box-shadow: 0 .5rem 1.6rem rgba(27,36,55,.16); z-index: 30; display: flex; flex-direction: column; gap: .12rem; }
.assistant-model__menu--up { top: auto; bottom: calc(100% + .35rem); }
.assistant-model__menu button { display: flex; width: 100%; padding: .5rem .6rem; border: 0; border-radius: .5rem; background: transparent; color: var(--assistant-text); font: 500 .85rem/1.2 Inter, sans-serif; text-align: left; cursor: pointer; }
.assistant-model__menu button:hover { background: var(--assistant-soft); }
.assistant-model__menu button.is-active { background: var(--assistant-blue-soft); color: var(--assistant-blue); font-weight: 600; }
/* Второй селектор (глубина) стоит вплотную к первому — auto только у первого. */
.assistant-model + .assistant-model { margin-left: .42rem; }
.composer-send:disabled { opacity: .55; cursor: default; }

/* Потоковый ответ */
.assistant-message__body { min-width: 0; }
.assistant-message__text { margin: 0; white-space: pre-wrap; overflow-wrap: anywhere; }
.assistant-caret { display: inline-block; width: .5ch; animation: assistant-blink 1s steps(2, start) infinite; }
@keyframes assistant-blink { to { opacity: 0; } }
.assistant-tool-note { margin-top: .5rem; color: var(--assistant-muted); font-size: .8rem; font-style: italic; }
.assistant-welcome__note { margin-top: .65rem; color: var(--assistant-amber); font-size: .88rem; }

.rail-heading { display: flex; align-items: center; justify-content: space-between; padding: 0 .25rem; margin-bottom: .7rem; font-size: .9rem; font-weight: 700; }
.rail-new-chat { display: flex; align-items: center; gap: .58rem; width: 100%; height: 2.85rem; padding: 0 .8rem; border: 1.5px dashed var(--assistant-strong-line); border-radius: .72rem; background: transparent; color: var(--assistant-sub); font: 500 .9rem/1 Inter, sans-serif; cursor: pointer; }
.rail-new-chat:hover { border-color: var(--assistant-blue); color: var(--assistant-blue); }
.rail-history { display: flex; flex: 1; flex-direction: column; min-height: 0; gap: .25rem; margin-top: .8rem; overflow-y: auto; scrollbar-width: none; }
.rail-history::-webkit-scrollbar { width: 0; }
.rail-history__item { display: flex; flex-direction: column; gap: .2rem; width: 100%; padding: .66rem .72rem; border: 0; border-radius: .7rem; background: transparent; color: var(--assistant-text); text-align: left; cursor: pointer; }
.rail-history__item:hover, .rail-history__item.is-active { background: var(--assistant-soft); }
.rail-history__title { overflow: hidden; font-size: .85rem; font-weight: 500; line-height: 1.25; text-overflow: ellipsis; white-space: nowrap; }
.rail-history__date, .rail-history__empty { color: var(--assistant-muted); font-size: .74rem; }
.rail-history__empty { padding: .6rem; line-height: 1.4; }

.assistant-projects-label { padding: .7rem .58rem .4rem; color: var(--assistant-muted); font-size: .8rem; font-weight: 600; }
.assistant-info-card { padding: .48rem; border: 1px solid var(--assistant-strong-line); border-radius: 1rem; background: var(--assistant-soft); box-shadow: 0 .12rem .35rem rgba(27,36,55,.06); }
.assistant-info-card button { display: flex; align-items: center; gap: .56rem; width: 100%; height: 2.5rem; padding: 0 .52rem; border-radius: .6rem; background: transparent; color: var(--assistant-text); font-size: .86rem; text-align: left; }
.assistant-info-card button:hover { background: var(--assistant-panel); }
.assistant-info-card__icon { display: grid; width: 1rem; height: 1rem; place-items: center; color: var(--assistant-sub); }
.assistant-info-card__icon svg { width: 1rem; height: 1rem; }
.assistant-info-card__chevron { width: .9rem !important; height: .9rem !important; margin-left: auto; color: var(--assistant-muted); }

.assistant-stage { display: flex; flex: 1; flex-direction: column; min-width: 0; background: var(--assistant-bg); }
.assistant-stage__head { display: flex; align-items: center; gap: 1rem; padding: 1.5rem 2.25rem .25rem; }
.assistant-stage__head h1 { margin: 0; font-size: 1.65rem; font-weight: 700; letter-spacing: -.025em; }
.assistant-limit { display: inline-flex; align-items: center; gap: .48rem; margin-left: auto; padding: .58rem .92rem; border-radius: .78rem; background: linear-gradient(105deg, #5b8def, #7c6ff0); color: #fff; font-size: .85rem; }
.assistant-limit svg { width: 1rem; height: 1rem; stroke-width: 1.9; }
.assistant-limit b { font-size: .92rem; }.assistant-limit span { opacity: .88; }

/* Экран приветствия: колонка со скроллом — герой на первый экран, промпты ниже */
.assistant-empty { display: flex; flex: 1; flex-direction: column; align-items: center; justify-content: flex-start; min-height: 0; padding: 0; overflow-y: auto; }
.assistant-hero { box-sizing: border-box; display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%; max-width: 54rem; min-height: 100%; padding: 2.4rem 1.5rem 2rem; text-align: center; }
.assistant-welcome__spark { display: inline-grid; width: 3.3rem; height: 3.3rem; margin-bottom: .9rem; place-items: center; border-radius: .95rem; background: linear-gradient(135deg, #5b8def, #7c6ff0); color: #fff; box-shadow: 0 .5rem 1.2rem rgba(92,111,240,.28); }
.assistant-welcome__spark svg { width: 1.55rem; height: 1.55rem; stroke-width: 1.9; }
.assistant-hero__title { margin: 0; font-size: 1.95rem; font-weight: 700; letter-spacing: -.03em; text-wrap: balance; }
.assistant-hero__sub { margin: .55rem auto 0; max-width: 34rem; color: var(--assistant-sub); font-size: 1rem; line-height: 1.5; }
.assistant-hero .assistant-composer { width: min(44rem, 100%); margin-top: 1.6rem; text-align: left; }

/* Источники данных */
.assistant-sources { width: min(44rem, 100%); margin-top: 1.4rem; text-align: left; }
.assistant-sources__label { display: block; margin-bottom: .55rem; color: var(--assistant-muted); font-size: .7rem; font-weight: 700; letter-spacing: .09em; text-transform: uppercase; }
.assistant-sources__grid { display: flex; flex-wrap: wrap; gap: .5rem; }
.source-chip { display: inline-flex; align-items: center; gap: .5rem; padding: .4rem .72rem .4rem .4rem; border: 1px solid var(--assistant-line); border-radius: .75rem; background: var(--assistant-panel); }
.source-chip__mark { display: grid; width: 1.6rem; height: 1.6rem; place-items: center; border-radius: .5rem; font-size: .72rem; font-weight: 800; letter-spacing: -.02em; }
.source-chip__name { font-size: .86rem; font-weight: 600; color: var(--assistant-text); }
.source-chip__status { color: var(--assistant-green); font-size: .72rem; font-weight: 600; }
.source-chip--off { opacity: .72; }
.source-chip--off .source-chip__mark { filter: grayscale(.5); }
.source-chip--off .source-chip__status { color: var(--assistant-muted); }

/* Подсказка к готовым промптам */
.assistant-scrollhint { display: inline-flex; align-items: center; gap: .4rem; margin-top: 1.9rem; padding: .5rem .95rem; border: 1px solid var(--assistant-line); border-radius: 999px; background: var(--assistant-soft); color: var(--assistant-sub); font: 600 .8rem/1 Inter, sans-serif; cursor: pointer; }
.assistant-scrollhint:hover { color: var(--assistant-text); border-color: var(--assistant-strong-line); }
.assistant-scrollhint svg { width: 1rem; height: 1rem; fill: none; stroke: currentColor; stroke-width: 1.9; stroke-linecap: round; stroke-linejoin: round; animation: hint-bounce 1.6s ease-in-out infinite; }
@keyframes hint-bounce { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(3px); } }

/* Готовые промпты */
.assistant-prompts { width: 100%; max-width: 68rem; padding: .5rem 1.5rem 3rem; }
.assistant-prompts__title { margin: 0 0 1rem; font-size: 1.2rem; font-weight: 700; letter-spacing: -.02em; }
.assistant-prompts__grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(19rem, 1fr)); gap: .75rem; }
.prompt-tile { display: flex; flex-direction: column; gap: .3rem; padding: .95rem 1rem 1.05rem; border: 1px solid var(--assistant-line); border-radius: 1rem; background: var(--assistant-panel); text-align: left; cursor: pointer; opacity: 0; transform: translateY(14px); transition: opacity .5s ease, transform .5s cubic-bezier(.22,.8,.3,1), border-color .15s ease, box-shadow .15s ease; }
.prompt-tile.is-visible { opacity: 1; transform: none; }
.prompt-tile:hover { border-color: var(--assistant-blue); box-shadow: 0 .4rem 1.1rem rgba(47,107,234,.09); }
.prompt-tile:focus-visible { outline: 2px solid var(--assistant-blue); outline-offset: 2px; }
.prompt-tile__head { display: flex; align-items: flex-start; justify-content: space-between; gap: .6rem; }
.prompt-tile__title { font-size: .95rem; font-weight: 700; color: var(--assistant-text); line-height: 1.3; }
.prompt-tile__desc { color: var(--assistant-sub); font-size: .83rem; line-height: 1.4; }
.prompt-tile__copy { flex-shrink: 0; display: grid; width: 2rem; height: 2rem; place-items: center; border: 0; border-radius: .6rem; background: var(--assistant-soft); color: var(--assistant-muted); cursor: pointer; transition: background .25s ease, color .25s ease, transform .2s ease; }
.prompt-tile__copy:hover { color: var(--assistant-sub); background: var(--assistant-strong-line); }
.prompt-tile__copy svg { width: 1.05rem; height: 1.05rem; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
.prompt-tile__copy.is-copied { background: var(--assistant-green-soft); color: var(--assistant-green); animation: copy-pop .32s ease; }
@keyframes copy-pop { 0% { transform: scale(.7); } 55% { transform: scale(1.14); } 100% { transform: scale(1); } }
.assistant-context { display: flex; justify-content: center; gap: .6rem; flex-wrap: wrap; max-width: 68rem; margin: 1.2rem 0; }
.assistant-context__chip { display: inline-flex; align-items: center; gap: .45rem; padding: .48rem .78rem; border: 1px solid var(--assistant-strong-line); border-radius: 1rem; background: var(--assistant-panel); color: var(--assistant-sub); font-size: .85rem; }
.assistant-context__chip b { color: var(--assistant-text); font-weight: 600; }.assistant-context__chip i { width: .42rem; height: .42rem; border-radius: 50%; background: #1fa55b; }

.assistant-composer { width: min(68rem, 100%); padding: 1.15rem 1.2rem .92rem; border: 1px solid var(--assistant-strong-line); border-radius: 1.2rem; background: var(--assistant-panel); box-shadow: 0 .45rem 1.75rem rgba(27,36,55,.07); }
.assistant-composer textarea { width: 100%; min-height: 4rem; max-height: 7.5rem; padding: 0; border: 0; outline: 0; resize: none; overflow-y: auto; background: transparent; color: var(--assistant-text); font: 400 1.05rem/1.45 Inter, sans-serif; }
.assistant-composer textarea::placeholder { color: var(--assistant-muted); }
.assistant-composer__actions { display: flex; align-items: center; gap: .42rem; margin-top: .45rem; }
.composer-icon { display: grid; width: 2.35rem; height: 2.35rem; place-items: center; border-radius: .65rem; background: transparent; color: var(--assistant-muted); }.composer-icon:hover { background: var(--assistant-soft); color: var(--assistant-sub); }
.composer-icon svg { width: 1.18rem; height: 1.18rem; }
.assistant-composer__hint { margin-left: .3rem; color: var(--assistant-muted); font-size: .75rem; white-space: nowrap; }
.assistant-depth { display: inline-flex; gap: .12rem; margin-left: auto; padding: .2rem; border-radius: .65rem; background: var(--assistant-soft); }
.assistant-depth button { padding: .42rem .72rem; border-radius: .5rem; background: transparent; color: var(--assistant-sub); font-size: .77rem; white-space: nowrap; }.assistant-depth button.is-active { background: var(--assistant-panel); color: var(--assistant-text); font-weight: 600; box-shadow: 0 .06rem .18rem rgba(27,36,55,.12); }
.composer-send { display: grid; width: 2.7rem; height: 2.7rem; margin-left: .25rem; place-items: center; border-radius: .85rem; background: var(--assistant-soft); color: var(--assistant-muted); transition: transform .18s ease, box-shadow .2s ease, background .2s ease, color .2s ease; }.composer-send.is-active { background: linear-gradient(135deg, #5b8def, #7c6ff0); color: #fff; box-shadow: 0 .35rem .9rem rgba(92,111,240,.35); }.composer-send.is-active:hover { transform: translateY(-1px) scale(1.03); box-shadow: 0 .5rem 1.1rem rgba(92,111,240,.42); }.composer-send:disabled { opacity: .5; cursor: default; }.composer-send svg { width: 1.25rem; height: 1.25rem; }

.assistant-suggestions { width: min(68rem, 100%); margin-top: 1.25rem; }.assistant-suggestions__label { margin: 1rem .2rem .55rem; color: var(--assistant-muted); font-size: .73rem; font-weight: 700; letter-spacing: .09em; }.assistant-suggestions__label:first-child { margin-top: 0; }
.assistant-suggestions__grid { display: grid; grid-template-columns: 1fr 1fr; gap: .65rem; }
.assistant-suggestion { display: flex; align-items: flex-start; gap: .8rem; width: 100%; padding: .95rem 1rem; border: 1px solid var(--assistant-line); border-radius: .95rem; background: var(--assistant-panel); color: var(--assistant-text); text-align: left; transition: border-color .15s ease, box-shadow .15s ease; }.assistant-suggestion:hover { border-color: var(--assistant-blue); box-shadow: 0 .25rem .85rem rgba(47,107,234,.1); }
.assistant-suggestion--alert { border-color: #f2dfb8; background: var(--assistant-amber-soft); }.assistant-suggestion--alert:hover { border-color: #e7ad46; box-shadow: 0 .25rem .85rem rgba(239,168,39,.15); }
.assistant-suggestion__icon { display: grid; width: 2.25rem; height: 2.25rem; flex: 0 0 2.25rem; place-items: center; border-radius: .7rem; background: var(--assistant-blue-soft); color: var(--assistant-blue); }.assistant-suggestion--alert .assistant-suggestion__icon { background: var(--assistant-panel); color: var(--assistant-amber); }
.assistant-suggestion b, .assistant-suggestion small { display: block; }.assistant-suggestion b { font-size: .9rem; line-height: 1.3; }.assistant-suggestion small { margin-top: .18rem; color: var(--assistant-muted); font-size: .78rem; line-height: 1.3; }.assistant-suggestion--alert small { color: var(--assistant-amber); }.assistant-suggestion em { align-self: center; margin-left: auto; color: var(--assistant-blue); font-size: .8rem; font-style: normal; font-weight: 600; white-space: nowrap; }.assistant-suggestion--alert em { color: var(--assistant-amber); }

.assistant-thread { display: flex; flex: 1; flex-direction: column; min-height: 0; }.assistant-thread__inner { display: flex; flex: 1; flex-direction: column; gap: 1rem; width: min(68rem, 100%); margin: 0 auto; padding: 1.6rem 2.25rem; overflow-y: auto; }.assistant-message { display: flex; gap: .78rem; }.assistant-message--user { justify-content: flex-end; }.assistant-message--user .assistant-message__bubble { max-width: 78%; border-radius: 1.12rem 1.12rem .34rem 1.12rem; background: var(--assistant-blue); color: #fff; }.assistant-message--assistant { max-width: 94%; }.assistant-message__avatar { display: grid; width: 2.4rem; height: 2.4rem; flex: 0 0 2.4rem; margin-top: .1rem; place-items: center; border-radius: .7rem; background: linear-gradient(135deg, #5b8def, #7c6ff0); color: #fff; }.assistant-message__avatar svg { width: 1.2rem; height: 1.2rem; stroke-width: 1.8; }.assistant-message__meta { display: flex; gap: .42rem; flex-wrap: wrap; margin-bottom: .45rem; }.assistant-message__meta span { padding: .28rem .6rem; border-radius: 1rem; background: var(--assistant-blue-soft); color: var(--assistant-blue); font-size: .74rem; font-weight: 600; }.assistant-message__meta span+span { background: var(--assistant-soft); color: var(--assistant-sub); font-weight: 500; }.assistant-message__bubble { padding: .95rem 1.1rem; border: 1px solid var(--assistant-line); border-radius: .34rem 1.12rem 1.12rem 1.12rem; background: var(--assistant-panel); font-size: .96rem; line-height: 1.5; }.assistant-message__bubble b { display: block; margin-bottom: .35rem; }.assistant-message__bubble p { margin: 0; color: var(--assistant-sub); }.assistant-message__actions { display: flex; gap: .42rem; margin-top: .75rem; }.assistant-message__actions button { padding: .38rem .62rem; border-radius: .5rem; background: var(--assistant-soft); color: var(--assistant-sub); font-size: .75rem; }.assistant-message__actions button:hover { color: var(--assistant-blue); }
.assistant-thread__composer { flex: 0 0 auto; padding: .8rem 2.25rem 1.2rem; border-top: 1px solid var(--assistant-line); }.assistant-thread__composer .assistant-composer { margin: 0 auto; box-shadow: 0 .25rem 1rem rgba(27,36,55,.05); }.assistant-thread__composer p { width: min(68rem, 100%); margin: .45rem auto 0; color: var(--assistant-muted); font-size: .75rem; }

@media (max-width: 1180px) { .assistant-rail:not(.assistant-rail--open) { width: 3.5rem; flex-basis: 3.5rem; }.assistant-depth button:last-child { display: none; } }
@media (max-width: 820px) { .assistant-stage__head { padding-inline: 1rem; }.assistant-hero { padding-inline: 1.1rem; }.assistant-prompts { padding-inline: 1.1rem; }.assistant-prompts__grid { grid-template-columns: 1fr; }.assistant-thread__inner, .assistant-thread__composer { padding-inline: 1rem; } }
@media (max-width: 560px) { .assistant-rail { display: none; }.assistant-stage__head { padding-top: .85rem; }.assistant-hero__title { font-size: 1.4rem; } }
@media (prefers-reduced-motion: reduce) { .assistant-scrollhint svg { animation: none; }.prompt-tile { transition: opacity .2s ease; transform: none; }.prompt-tile__copy.is-copied { animation: none; } }
@media (prefers-reduced-motion: reduce) { .assistant-rail, .assistant-suggestion { transition: none; } }
</style>
