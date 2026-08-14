<template>
  <section class="assistant-page" :class="{ 'assistant-page--dark': isDarkMode }">
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
            v-for="chat in chats"
            :key="chat.id"
            type="button"
            class="rail-history__item"
            :class="{ 'is-active': chat.id === activeChatId }"
            :title="chat.title"
            @click="selectChat(chat.id)"
          >
            <span class="rail-history__title">{{ chat.title }}</span>
            <span class="rail-history__date">{{ formatChatDate(chat.ts) }}</span>
          </button>

          <div v-if="!chats.length" class="rail-history__empty">Здесь появятся ваши вопросы.</div>
        </div>

        <div class="assistant-projects-label">Основное</div>
        <div class="assistant-info-card">
          <button v-for="item in mainItems" :key="item.label" type="button">
            <span class="assistant-info-card__icon" v-html="item.icon"></span>
            <span>{{ item.label }}</span>
            <svg class="assistant-info-card__chevron" viewBox="0 0 24 24" aria-hidden="true"><path d="m9 6 6 6-6 6"/></svg>
          </button>
        </div>
      </div>
    </aside>

    <section class="assistant-stage" aria-label="AI-ассистент">
      <header class="assistant-stage__head">
        <h1>Ассистент</h1>
        <span class="assistant-limit">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 3 1.6 5.4L19 10l-5.4 1.6L12 17l-1.6-5.4L5 10l5.4-1.6L12 3Z"/><path d="m18.5 15 .65 2.15L21.3 18l-2.15.65L18.5 20.8l-.65-2.15L15.7 18l2.15-.85.65-2.15Z"/></svg>
          <b>{{ aiRemaining }}</b><span>из {{ aiLimit }} AI</span>
        </span>
      </header>

      <div v-if="!activeChat" class="assistant-empty">
        <div class="assistant-welcome">
          <span class="assistant-welcome__spark">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 3 1.6 5.4L19 10l-5.4 1.6L12 17l-1.6-5.4L5 10l5.4-1.6L12 3Z"/></svg>
          </span>
          <h2>Спросите про {{ projectContextTitle }}</h2>
          <p>{{ projectContextDescription }}</p>
        </div>

        <div class="assistant-context">
          <span class="assistant-context__chip">
            <i></i><b>{{ projectContextTitle }}</b>{{ currentProjectId ? ' · выбран в шапке' : '' }}
          </span>
          <span class="assistant-context__chip">Период укажите прямо в вопросе</span>
        </div>

        <div class="assistant-composer">
          <textarea
            ref="textarea"
            v-model="prompt"
            rows="1"
            aria-label="Запрос ассистенту"
            placeholder="Например: почему изменилась стоимость лида в этом месяце?"
            @input="autoGrow"
            @keydown.enter.exact.prevent="sendPrompt"
          ></textarea>
          <div class="assistant-composer__actions">
            <button class="composer-icon" type="button" aria-label="Добавить данные">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>
            </button>
            <button class="composer-icon" type="button" aria-label="Сохранить вопрос">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 4.5h10a1.5 1.5 0 0 1 1.5 1.5v13l-6.5-3.5L5.5 19V6A1.5 1.5 0 0 1 7 4.5Z"/></svg>
            </button>
            <span class="assistant-composer__hint">1 запрос из лимита</span>
            <div class="assistant-depth" aria-label="Глубина ответа">
              <button type="button" :class="{ 'is-active': responseMode === 'quick' }" @click="responseMode = 'quick'">Быстрый ответ</button>
              <button type="button" :class="{ 'is-active': responseMode === 'deep' }" @click="responseMode = 'deep'">Глубокий разбор · 3 запроса</button>
            </div>
            <button class="composer-send" type="button" aria-label="Отправить" :class="{ 'is-active': prompt.trim() }" @click="sendPrompt">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12 14-7-4.5 14-3-5-6.5-2Z"/><path d="m11.5 14 2.2-2.2"/></svg>
            </button>
          </div>
        </div>

        <div class="assistant-suggestions">
          <p class="assistant-suggestions__label">СЕЙЧАС В ПРОЕКТЕ</p>
          <button class="assistant-suggestion assistant-suggestion--alert" type="button" @click="useSuggestion('Разобрать активные отклонения и подсказать, что проверить в первую очередь')">
            <span class="assistant-suggestion__icon"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4.5 20 19H4L12 4.5Z"/><path d="M12 9v4.5M12 16.3h.01"/></svg></span>
            <span><b>Разобрать активные отклонения</b><small>Приоритет проблем и следующие действия по проекту</small></span>
            <em>Спросить →</em>
          </button>

          <p class="assistant-suggestions__label">СРЕЗЫ, КОТОРЫХ НЕТ В ДАШБОРДЕ</p>
          <div class="assistant-suggestions__grid">
            <button v-for="item in suggestions" :key="item.title" class="assistant-suggestion" type="button" @click="useSuggestion(item.question)">
              <span class="assistant-suggestion__icon" v-html="item.icon"></span>
              <span><b>{{ item.title }}</b><small>{{ item.description }}</small></span>
            </button>
          </div>
        </div>
      </div>

      <div v-else class="assistant-thread">
        <div class="assistant-thread__inner">
          <div v-for="message in activeChat.messages" :key="message.id" :class="['assistant-message', `assistant-message--${message.role}`]">
            <template v-if="message.role === 'assistant'">
              <span class="assistant-message__avatar"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 3 1.6 5.4L19 10l-5.4 1.6L12 17l-1.6-5.4L5 10l5.4-1.6L12 3Z"/></svg></span>
              <div>
                <div class="assistant-message__meta"><span>{{ projectContextTitle }}</span><span>Период указан в вопросе</span></div>
                <div class="assistant-message__bubble">
                  <b>{{ message.title }}</b>
                  <p>{{ message.text }}</p>
                  <div class="assistant-message__actions"><button type="button">Уточнить вопрос</button><button type="button">Сохранить</button></div>
                </div>
              </div>
            </template>
            <div v-else class="assistant-message__bubble">{{ message.text }}</div>
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
              <button class="composer-icon" type="button" aria-label="Добавить данные"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg></button>
              <span class="assistant-composer__hint">1 запрос из лимита</span>
              <div class="assistant-depth"><button type="button" :class="{ 'is-active': responseMode === 'quick' }" @click="responseMode = 'quick'">Быстрый ответ</button><button type="button" :class="{ 'is-active': responseMode === 'deep' }" @click="responseMode = 'deep'">Глубокий разбор · 3 запроса</button></div>
              <button class="composer-send" type="button" aria-label="Отправить" :class="{ 'is-active': prompt.trim() }" @click="sendPrompt"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12 14-7-4.5 14-3-5-6.5-2Z"/><path d="m11.5 14 2.2-2.2"/></svg></button>
            </div>
          </div>
          <p>Период меняется прямо в вопросе — отдельный календарь не нужен.</p>
        </div>
      </div>
    </section>
  </section>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import api from '@/api/axios'
import { useTheme } from '../../composables/useTheme'
import { useProjects } from '../../composables/useProjects'

const { isDarkMode } = useTheme()
const { currentProjectId, currentProjectName, fetchProjects } = useProjects()

const railOpen = ref(false)
const prompt = ref('')
const textarea = ref(null)
const threadTextarea = ref(null)
const responseMode = ref('quick')
const aiRemaining = ref(0)
const aiLimit = ref(0)

const projectContextTitle = computed(() => currentProjectId.value ? currentProjectName.value : 'все проекты')
const projectContextDescription = computed(() => currentProjectId.value
  ? 'Отвечаю по данным выбранного проекта: рекламные кабинеты, цели, Метрика и отклонения.'
  : 'Помогу сравнить рекламу по всем проектам, найти отклонения и подготовить следующий шаг.')

const icons = {
  link: '<svg viewBox="0 0 24 24"><path d="M9.5 14.5l5-5M10.5 6.8l1.3-1.3a3.6 3.6 0 0 1 5.1 5.1l-2 2M13.5 17.2l-1.3 1.3a3.6 3.6 0 0 1-5.1-5.1l2-2"/></svg>',
  stack: '<svg viewBox="0 0 24 24"><rect x="4" y="4.5" width="16" height="6" rx="1.6"/><rect x="4" y="13.5" width="16" height="6" rx="1.6"/></svg>',
  audience: '<svg viewBox="0 0 24 24"><circle cx="12" cy="8" r="3.2"/><path d="M5.5 19.5c.8-3.2 3-5 6.5-5s5.7 1.8 6.5 5"/></svg>',
  device: '<svg viewBox="0 0 24 24"><rect x="5" y="3.8" width="14" height="16.4" rx="2"/><path d="M9.5 17h5"/></svg>',
  campaign: '<svg viewBox="0 0 24 24"><path d="M5 5.5h14M5 12h14M5 18.5h14"/><circle cx="7.5" cy="5.5" r="1.1"/><circle cx="12" cy="12" r="1.1"/><circle cx="16.5" cy="18.5" r="1.1"/></svg>',
  compare: '<svg viewBox="0 0 24 24"><path d="M7 7h11l-3-3M17 17H6l3 3M18 7l-4 4M6 17l4-4"/></svg>',
}

// Существующий блок «Основное» сохранён намеренно: переходы подключим,
// когда согласуем их сценарии в ассистенте.
const mainItems = [
  { label: 'Интеграции', icon: icons.link },
  { label: 'Проекты', icon: icons.stack },
]

const suggestions = [
  { title: 'Какая аудитория приносит заявки?', description: 'Возраст и пол по конверсиям из Метрики', question: 'Какая аудитория приносит больше всего заявок и какая у неё стоимость лида?', icon: icons.audience },
  { title: 'С каких устройств конвертят?', description: 'Десктоп и мобильные по цене заявки', question: 'Сравни устройства по количеству лидов и стоимости заявки', icon: icons.device },
  { title: 'Какая кампания самая невыгодная?', description: 'По CPL относительно цели', question: 'Какая кампания сейчас самая невыгодная относительно целевой стоимости заявки?', icon: icons.campaign },
  { title: 'Сравни с прошлым месяцем', description: 'Расход, лиды и CPL — что изменилось', question: 'Сравни текущий месяц с прошлым: расход, лиды и стоимость заявки', icon: icons.compare },
]

const CHATS_KEY = 'admirra_ai_chats_v2'
const chats = ref([])
const activeChatId = ref(null)

const activeChat = computed(() => chats.value.find(chat => chat.id === activeChatId.value) || null)

const uid = () => `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 7)}`

const persistChats = () => {
  try { localStorage.setItem(CHATS_KEY, JSON.stringify(chats.value)) } catch { /* storage can be unavailable */ }
}

const loadChats = () => {
  try {
    const parsed = JSON.parse(localStorage.getItem(CHATS_KEY) || '[]')
    chats.value = Array.isArray(parsed) ? parsed.filter(chat => chat?.id && chat?.title) : []
  } catch { chats.value = [] }
}

const formatChatDate = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  const today = new Date()
  if (date.toDateString() === today.toDateString()) return 'сегодня'
  return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })
}

const newChat = async () => {
  activeChatId.value = null
  prompt.value = ''
  await nextTick()
  textarea.value?.focus()
}

const selectChat = (id) => {
  activeChatId.value = id
  railOpen.value = false
}

const autoGrow = () => {
  const element = textarea.value || threadTextarea.value
  if (!element) return
  element.style.height = 'auto'
  element.style.height = `${Math.min(element.scrollHeight, 104)}px`
}

const useSuggestion = (question) => {
  prompt.value = question
  sendPrompt()
}

const sendPrompt = async () => {
  const question = prompt.value.trim()
  if (!question) return

  let chat = activeChat.value
  if (!chat) {
    chat = { id: uid(), title: question.length > 46 ? `${question.slice(0, 46)}…` : question, ts: Date.now(), messages: [] }
    chats.value.unshift(chat)
    activeChatId.value = chat.id
  }

  if (!Array.isArray(chat.messages)) chat.messages = []
  chat.messages.push({ id: uid(), role: 'user', text: question })
  chat.messages.push({
    id: uid(),
    role: 'assistant',
    title: 'Запрос добавлен в диалог',
    text: 'Интерфейс нового ассистента готов. Подключение ответов по реальным данным проекта будет следующим этапом — без изменения выбранного в шапке проекта и без отдельного календаря.',
  })
  chat.ts = Date.now()
  chats.value = [chat, ...chats.value.filter(item => item.id !== chat.id)]
  prompt.value = ''
  persistChats()
  await nextTick()
  autoGrow()
  threadTextarea.value?.focus()
}

const loadUsage = async () => {
  try {
    const { data } = await api.get('billing/subscription')
    aiRemaining.value = data?.ai_requests_remaining ?? 0
    aiLimit.value = data?.max_ai_requests_per_period ?? 0
  } catch {
    aiRemaining.value = 0
    aiLimit.value = 0
  }
}

onMounted(() => {
  loadChats()
  fetchProjects({ preferCache: true })
  loadUsage()
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
  display: flex;
  width: 100%;
  /* Ровно вся доступная высота: 84 px Header + 56 px внешние отступы MainLayout. */
  height: calc(100vh - 8.8rem);
  min-height: min(38rem, calc(100vh - 8.8rem));
  overflow: hidden;
  border: 1px solid var(--assistant-line);
  border-radius: 1rem;
  background: var(--assistant-bg);
  color: var(--assistant-text);
  box-shadow: 0 .4rem 1.4rem rgba(36, 54, 89, .05);
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

.assistant-empty { display: flex; flex: 1; flex-direction: column; align-items: center; justify-content: center; min-height: 0; padding: 1.75rem 2.5rem 3.25rem; overflow-y: auto; }
.assistant-welcome { max-width: 68rem; text-align: center; }
.assistant-welcome__spark { display: inline-grid; width: 3.3rem; height: 3.3rem; margin-bottom: .85rem; place-items: center; border-radius: .95rem; background: linear-gradient(135deg, #5b8def, #7c6ff0); color: #fff; }
.assistant-welcome__spark svg { width: 1.55rem; height: 1.55rem; stroke-width: 1.9; }
.assistant-welcome h2 { margin: 0; font-size: 2rem; letter-spacing: -.03em; }
.assistant-welcome p { margin: .5rem 0 0; color: var(--assistant-sub); font-size: 1rem; }
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
.composer-send { display: grid; width: 2.65rem; height: 2.65rem; margin-left: .2rem; place-items: center; border-radius: .78rem; background: #dfe4ea; color: #fff; }.composer-send.is-active { background: var(--assistant-blue); }.composer-send svg { width: 1.28rem; height: 1.28rem; }

.assistant-suggestions { width: min(68rem, 100%); margin-top: 1.25rem; }.assistant-suggestions__label { margin: 1rem .2rem .55rem; color: var(--assistant-muted); font-size: .73rem; font-weight: 700; letter-spacing: .09em; }.assistant-suggestions__label:first-child { margin-top: 0; }
.assistant-suggestions__grid { display: grid; grid-template-columns: 1fr 1fr; gap: .65rem; }
.assistant-suggestion { display: flex; align-items: flex-start; gap: .8rem; width: 100%; padding: .95rem 1rem; border: 1px solid var(--assistant-line); border-radius: .95rem; background: var(--assistant-panel); color: var(--assistant-text); text-align: left; transition: border-color .15s ease, box-shadow .15s ease; }.assistant-suggestion:hover { border-color: var(--assistant-blue); box-shadow: 0 .25rem .85rem rgba(47,107,234,.1); }
.assistant-suggestion--alert { border-color: #f2dfb8; background: var(--assistant-amber-soft); }.assistant-suggestion--alert:hover { border-color: #e7ad46; box-shadow: 0 .25rem .85rem rgba(239,168,39,.15); }
.assistant-suggestion__icon { display: grid; width: 2.25rem; height: 2.25rem; flex: 0 0 2.25rem; place-items: center; border-radius: .7rem; background: var(--assistant-blue-soft); color: var(--assistant-blue); }.assistant-suggestion--alert .assistant-suggestion__icon { background: var(--assistant-panel); color: var(--assistant-amber); }
.assistant-suggestion b, .assistant-suggestion small { display: block; }.assistant-suggestion b { font-size: .9rem; line-height: 1.3; }.assistant-suggestion small { margin-top: .18rem; color: var(--assistant-muted); font-size: .78rem; line-height: 1.3; }.assistant-suggestion--alert small { color: var(--assistant-amber); }.assistant-suggestion em { align-self: center; margin-left: auto; color: var(--assistant-blue); font-size: .8rem; font-style: normal; font-weight: 600; white-space: nowrap; }.assistant-suggestion--alert em { color: var(--assistant-amber); }

.assistant-thread { display: flex; flex: 1; flex-direction: column; min-height: 0; }.assistant-thread__inner { display: flex; flex: 1; flex-direction: column; gap: 1rem; width: min(68rem, 100%); margin: 0 auto; padding: 1.6rem 2.25rem; overflow-y: auto; }.assistant-message { display: flex; gap: .78rem; }.assistant-message--user { justify-content: flex-end; }.assistant-message--user .assistant-message__bubble { max-width: 78%; border-radius: 1.12rem 1.12rem .34rem 1.12rem; background: var(--assistant-blue); color: #fff; }.assistant-message--assistant { max-width: 94%; }.assistant-message__avatar { display: grid; width: 2.4rem; height: 2.4rem; flex: 0 0 2.4rem; margin-top: .1rem; place-items: center; border-radius: .7rem; background: linear-gradient(135deg, #5b8def, #7c6ff0); color: #fff; }.assistant-message__avatar svg { width: 1.2rem; height: 1.2rem; stroke-width: 1.8; }.assistant-message__meta { display: flex; gap: .42rem; flex-wrap: wrap; margin-bottom: .45rem; }.assistant-message__meta span { padding: .28rem .6rem; border-radius: 1rem; background: var(--assistant-blue-soft); color: var(--assistant-blue); font-size: .74rem; font-weight: 600; }.assistant-message__meta span+span { background: var(--assistant-soft); color: var(--assistant-sub); font-weight: 500; }.assistant-message__bubble { padding: .95rem 1.1rem; border: 1px solid var(--assistant-line); border-radius: .34rem 1.12rem 1.12rem 1.12rem; background: var(--assistant-panel); font-size: .96rem; line-height: 1.5; }.assistant-message__bubble b { display: block; margin-bottom: .35rem; }.assistant-message__bubble p { margin: 0; color: var(--assistant-sub); }.assistant-message__actions { display: flex; gap: .42rem; margin-top: .75rem; }.assistant-message__actions button { padding: .38rem .62rem; border-radius: .5rem; background: var(--assistant-soft); color: var(--assistant-sub); font-size: .75rem; }.assistant-message__actions button:hover { color: var(--assistant-blue); }
.assistant-thread__composer { flex: 0 0 auto; padding: .8rem 2.25rem 1.2rem; border-top: 1px solid var(--assistant-line); }.assistant-thread__composer .assistant-composer { margin: 0 auto; box-shadow: 0 .25rem 1rem rgba(27,36,55,.05); }.assistant-thread__composer p { width: min(68rem, 100%); margin: .45rem auto 0; color: var(--assistant-muted); font-size: .75rem; }

@media (max-width: 1180px) { .assistant-rail:not(.assistant-rail--open) { width: 3.5rem; flex-basis: 3.5rem; }.assistant-page { min-height: min(34rem, calc(100vh - 8.8rem)); }.assistant-depth button:last-child { display: none; } }
@media (max-width: 820px) { .assistant-page { height: calc(100vh - 7.7rem); min-height: 32rem; border-radius: .8rem; }.assistant-stage__head { padding-inline: 1rem; }.assistant-empty { padding-inline: 1rem; }.assistant-suggestions__grid { grid-template-columns: 1fr; }.assistant-depth { display: none; }.assistant-composer__hint { margin-left: auto; }.assistant-thread__inner, .assistant-thread__composer { padding-inline: 1rem; }.assistant-limit span { display: none; } }
@media (max-width: 560px) { .assistant-rail { display: none; }.assistant-stage__head { padding-top: .85rem; }.assistant-welcome h2 { font-size: 1.15rem; }.assistant-context { display: none; }.assistant-empty { justify-content: flex-start; padding-top: 2.3rem; }.assistant-suggestion--alert em { display: none; } }
@media (prefers-reduced-motion: reduce) { .assistant-rail, .assistant-suggestion { transition: none; } }
</style>
