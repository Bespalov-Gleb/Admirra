<template>
  <div class="kimi-shell" :class="{ 'kimi-shell--ready': mounted, 'kimi-shell--collapsed': sideCollapsed, 'kimi-shell--dark': isDarkMode }">
    <aside class="kimi-sidebar">
      <div class="kimi-sidebar__brand-row">
        <div class="kimi-brand-group">
          <button class="kimi-icon-button kimi-back" type="button" aria-label="К дашборду" title="К дашборду" @click="goBack">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 5l-7 7 7 7"/></svg>
          </button>
          <span v-if="planName" class="kimi-plan-badge" :title="`Тариф: ${planName}`">
            <svg class="kimi-plan-badge__spark" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3l1.9 4.7L18.5 9l-4.6 1.3L12 15l-1.9-4.7L5.5 9z"/></svg>
            <span class="kimi-plan-badge__name">{{ planName }}</span>
          </span>
        </div>
        <button
          class="kimi-icon-button kimi-sidebar__toggle"
          type="button"
          :aria-label="sideCollapsed ? 'Развернуть меню' : 'Свернуть меню'"
          @click="sideCollapsed = !sideCollapsed"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="4" width="16" height="16" rx="2.5"/><path d="M10 4v16"/></svg>
        </button>
      </div>

      <button class="kimi-new-chat" type="button" @click="newChat">
        <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="8.25"/><path d="M12 8.5v7M8.5 12h7"/></svg>
        <span>Новый чат</span>
      </button>

      <!-- История чатов: занимает всё место до блока «Основное», скроллится,
           у нижнего края — лёгкий фейд последнего чата (mask-image). -->
      <div class="kimi-history" aria-label="История чатов">
        <button
          v-for="chat in chats"
          :key="chat.id"
          type="button"
          class="kimi-history__item"
          :class="{ 'is-active': chat.id === activeChatId }"
          :title="chat.title"
          @click="selectChat(chat.id)"
        >
          <span class="kimi-history__title">{{ chat.title }}</span>
        </button>
      </div>

      <div class="kimi-projects-label">Основное</div>

      <div class="kimi-info-card">
        <button v-for="item in mainItems" :key="item.label" type="button">
          <span class="kimi-info-card__icon" v-html="item.icon"></span>
          <span>{{ item.label }}</span>
          <svg class="kimi-info-card__chevron" viewBox="0 0 24 24" aria-hidden="true"><path d="m9 6 6 6-6 6"/></svg>
        </button>
      </div>

      <div class="kimi-sidebar__footer">
        <button class="kimi-account" type="button" :title="displayName">
          <span class="kimi-account__avatar">
            <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8.5" r="3.2"/><path d="M5.5 19.5c.8-3.2 3-5 6.5-5s5.7 1.8 6.5 5"/></svg>
          </span>
          <span>{{ displayName }}</span>
        </button>
      </div>
    </aside>

    <main class="kimi-main">
      <section class="kimi-stage">
        <div class="kimi-center">
          <div class="kimi-wordmark-space" aria-hidden="true"></div>

          <div class="kimi-composer">
            <textarea
              ref="textarea"
              v-model="prompt"
              rows="1"
              aria-label="Запрос ассистенту"
              placeholder="Спросите что угодно или поручите задачу…"
              @input="autoGrow"
              @keydown.enter.exact.prevent="sendPrompt"
            ></textarea>
            <div class="kimi-composer__actions">
              <button class="kimi-plus" type="button" aria-label="Добавить">
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>
              </button>
              <div class="kimi-composer__right">
                <button class="kimi-model" type="button">
                  <span>Instant</span><strong>High</strong>
                  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m7 10 5 5 5-5"/></svg>
                </button>
                <button class="kimi-send" type="button" aria-label="Отправить" :class="{ 'kimi-send--active': prompt.trim() }" @click="sendPrompt">
                  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 18V6m0 0-5 5m5-5 5 5"/></svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api/axios'
import { useTheme } from '../../composables/useTheme'
import { useAuth } from '../../composables/useAuth'

const router = useRouter()
const { isDarkMode } = useTheme()
const { user } = useAuth()
const mounted = ref(false)
const sideCollapsed = ref(false)
const prompt = ref('')
const textarea = ref(null)

// Текущий тариф пользователя — показываем бейджем в шапке сайдбара.
const planName = ref('')
const loadPlan = async () => {
  try {
    const { data } = await api.get('billing/subscription')
    planName.value = data?.plan_name || ''
  } catch (e) { /* бейдж просто не покажем */ }
}

const displayName = computed(() => {
  const u = user.value
  if (!u) return 'Профиль'
  if (u.first_name || u.last_name) return `${u.first_name || ''} ${u.last_name || ''}`.trim()
  return u.username || u.email || 'Профиль'
})

const icons = {
  smile: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="8.25"/><path d="M9 10h.01M15 10h.01M9 14.2c1.7 1.5 4.3 1.5 6 0"/></svg>',
  clock: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="8.25"/><path d="M12 7.5v5l3.3 2"/><path d="m5.5 4.8-1.7 1.7M18.5 4.8l1.7 1.7"/></svg>',
  swarm: '<svg viewBox="0 0 24 24"><circle cx="5" cy="7" r="1.7"/><circle cx="12" cy="5" r="1.7"/><circle cx="19" cy="7" r="1.7"/><path d="M5 8.8v4.5l3.5 2M19 8.8v4.5l-3.5 2M12 6.8V18"/></svg>',
  slides: '<svg viewBox="0 0 24 24"><rect x="4.5" y="5" width="15" height="11" rx="1.5"/><path d="M8 19l4-3 4 3M9 9h6M9 12h4"/></svg>',
  research: '<svg viewBox="0 0 24 24"><path d="M5 17.5 8 20l3-3-2.5-2.5L5 17.5Z"/><path d="m9 14 7.8-7.8 2 2L11 16M14 19H6"/><circle cx="17.5" cy="5.5" r="1.5"/></svg>',
  website: '<svg viewBox="0 0 24 24"><rect x="4" y="5" width="16" height="14" rx="2"/><path d="M4 9h16M8 7h.01"/></svg>',
  doc: '<svg viewBox="0 0 24 24"><path d="M7 3.8h7l4 4V20H7z"/><path d="M14 3.8V8h4M10 12h5M10 15h5"/></svg>',
  sheet: '<svg viewBox="0 0 24 24"><rect x="4.5" y="4" width="15" height="16" rx="2"/><path d="M4.5 9h15M4.5 14h15M10 9v11M15 9v11"/></svg>',
  design: '<svg viewBox="0 0 24 24"><path d="M4.5 18.5 7 12l5-5 5 5-5 5-6.5 2.5Z"/><path d="m13.5 5.5 2-2 5 5-2 2M7 12l5 5"/></svg>',
  monitor: '<svg viewBox="0 0 24 24"><rect x="3.5" y="4.5" width="17" height="12" rx="2"/><path d="M8 20h8M12 16.5V20"/></svg>',
  code: '<svg viewBox="0 0 24 24"><rect x="3.5" y="4.5" width="17" height="15" rx="2"/><path d="m8 10-2 2 2 2m8-4 2 2-2 2m-5 2 2-8"/></svg>',
  agent: '<svg viewBox="0 0 24 24"><path d="M8.5 18.5c-3.8 0-5.5-2.1-4-4.8.7-1.2 1.8-1.7 3.1-1.7-.4-3.6 1.4-6.5 4.7-6.5 2.8 0 4.5 2 4.6 4.5 2.4.1 3.6 1.4 3.6 3.4 0 2.4-1.9 4.1-4.7 4.1"/><path d="m10 14 2 2 4-5"/></svg>',
  download: '<svg viewBox="0 0 24 24"><path d="M12 4v10m0 0 4-4m-4 4-4-4M5 18h14"/></svg>',
  info: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="8.25"/><path d="M12 11v5M12 8h.01"/></svg>',
  language: '<svg viewBox="0 0 24 24"><path d="M4 5h9M8.5 3v2c0 4-1.6 7.3-4.5 9.5M7 9c1.2 2.1 2.8 3.7 4.8 4.9M13 20l3.5-9 3.5 9M14.2 17h4.6"/></svg>',
  help: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="8.25"/><path d="M9.7 9.3a2.5 2.5 0 0 1 4.8.9c0 1.8-2.5 2.1-2.5 4M12 17h.01"/></svg>',
  link: '<svg viewBox="0 0 24 24"><path d="M9.5 14.5l5-5M10.5 6.8l1.3-1.3a3.6 3.6 0 0 1 5.1 5.1l-2 2M13.5 17.2l-1.3 1.3a3.6 3.6 0 0 1-5.1-5.1l2-2"/></svg>',
  stack: '<svg viewBox="0 0 24 24"><rect x="4" y="4.5" width="16" height="6" rx="1.6"/><rect x="4" y="13.5" width="16" height="6" rx="1.6"/></svg>',
}

// Блок «Основное» — пока без переходов (заглушки).
const mainItems = [
  { label: 'Интеграции', icon: icons.link },
  { label: 'Проекты', icon: icons.stack },
]

// ── История чатов (пока фронт-мокап на localStorage; позже — бэкенд) ──────────
const CHATS_KEY = 'admirra_ai_chats_v2'
const chats = ref([])
const activeChatId = ref(null)

const uid = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 7)

const persistChats = () => {
  try { localStorage.setItem(CHATS_KEY, JSON.stringify(chats.value)) } catch (e) { /* ignore */ }
}

const loadChats = () => {
  try {
    const raw = localStorage.getItem(CHATS_KEY)
    const parsed = raw ? JSON.parse(raw) : null
    if (Array.isArray(parsed)) { chats.value = parsed }
  } catch (e) { /* ignore */ }
}

const newChat = () => {
  const chat = { id: uid(), title: 'Новый чат', ts: Date.now() }
  chats.value.unshift(chat)
  activeChatId.value = chat.id
  prompt.value = ''
  persistChats()
  nextTick(() => textarea.value?.focus())
}

const selectChat = (id) => { activeChatId.value = id }

const sendPrompt = () => {
  const text = prompt.value.trim()
  if (!text) return
  let chat = chats.value.find((c) => c.id === activeChatId.value)
  if (!chat) {
    chat = { id: uid(), title: '', ts: Date.now() }
    chats.value.unshift(chat)
    activeChatId.value = chat.id
  }
  if (!chat.title || chat.title === 'Новый чат') {
    chat.title = text.length > 42 ? `${text.slice(0, 42)}…` : text
  }
  chat.ts = Date.now()
  // Активный чат всплывает наверх истории.
  chats.value = [chat, ...chats.value.filter((c) => c.id !== chat.id)]
  prompt.value = ''
  autoGrow()
  persistChats()
}

const autoGrow = () => {
  const element = textarea.value
  if (!element) return
  element.style.height = 'auto'
  element.style.height = `${Math.min(element.scrollHeight, 80)}px`
}

const goBack = () => router.push('/dashboard/general-3')

let previousOverflow = ''
onMounted(async () => {
  loadChats()
  loadPlan()
  previousOverflow = document.documentElement.style.overflow
  document.documentElement.style.overflow = 'hidden'
  await nextTick()
  requestAnimationFrame(() => { mounted.value = true })
})

onBeforeUnmount(() => {
  document.documentElement.style.overflow = previousOverflow
})
</script>

<style scoped>
.kimi-shell {
  --sidebar-bg: #fafafa;
  --panel-bg: #fff;
  --composer-bg: #fff;
  --utility-bg: #fff;
  --hover-bg: #f2f2f2;
  --text: #202020;
  --muted: #8b8b8b;
  --soft: #a7a7a7;
  --line: #e8e8e8;
  --strong-line: #d8d8d8;
  position: fixed;
  inset: 0;
  z-index: 60;
  display: flex;
  overflow: hidden;
  background: var(--sidebar-bg);
  color: var(--text);
  font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
  font-size: 14px;
  opacity: 0;
  transition: opacity 180ms ease;
}

.kimi-shell--ready { opacity: 1; }

.kimi-shell--dark {
  --sidebar-bg: #181817;
  --panel-bg: #111;
  --composer-bg: #1f1f1f;
  --utility-bg: #292929;
  --hover-bg: #242424;
  --text: #e7e7e7;
  --muted: #929292;
  --soft: #777;
  --line: #303030;
  --strong-line: #414141;
}

.kimi-sidebar {
  width: 240px;
  flex: 0 0 240px;
  min-width: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 12px 8px 9px;
  overflow: hidden;
  background: var(--sidebar-bg);
  opacity: 0;
  transform: translateX(-14px);
  transition: width 220ms ease, flex-basis 220ms ease;
}

.kimi-shell--ready .kimi-sidebar {
  animation: kimi-sidebar-enter 450ms cubic-bezier(0.22, 1, 0.36, 1) 50ms forwards;
}

.kimi-sidebar__brand-row {
  height: 38px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 8px;
}

.kimi-brand-group { display: flex; align-items: center; gap: 6px; min-width: 0; }
.kimi-back svg { transform: translateX(-0.5px); }

/* Бейдж текущего тарифа вместо логотипа. */
.kimi-plan-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 27px;
  max-width: 118px;
  padding: 0 10px 0 8px;
  border-radius: 9px;
  background: linear-gradient(135deg, #3d7bff, #7a5cff);
  color: #fff;
  font: 600 12.5px/1 Inter, sans-serif;
  letter-spacing: 0.01em;
  box-shadow: 0 2px 7px rgba(64, 108, 255, 0.30);
}
.kimi-plan-badge__spark { width: 14px; height: 14px; flex: 0 0 14px; fill: #fff; stroke: none; opacity: 0.95; }
.kimi-plan-badge__name { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.kimi-shell--dark .kimi-plan-badge { box-shadow: 0 2px 9px rgba(64, 108, 255, 0.40); }

.kimi-brand {
  position: relative;
  width: 29px;
  height: 29px;
  flex: 0 0 29px;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: 8px;
  background: #090909;
  color: #fff;
  font: 800 18px/1 Inter, sans-serif;
  letter-spacing: -1px;
  cursor: default;
}

.kimi-shell--dark .kimi-brand { background: #f5f5f5; color: #111; }
.kimi-brand i { position: absolute; top: 5px; right: 5px; width: 4px; height: 4px; border-radius: 50%; background: #3979ff; }

.kimi-icon-button {
  width: 31px;
  height: 31px;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: #6f6f6f;
  cursor: pointer;
}

.kimi-icon-button:hover { background: var(--hover-bg); color: var(--text); }
.kimi-icon-button svg { width: 18px; height: 18px; fill: none; stroke: currentColor; stroke-width: 1.75; stroke-linecap: round; stroke-linejoin: round; }

.kimi-new-chat {
  width: 100%;
  height: 47px;
  flex: 0 0 47px;
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 0 9px;
  border: 1px solid var(--strong-line);
  border-radius: 12px;
  background: var(--utility-bg);
  color: var(--text);
  font: 500 14px/1 Inter, sans-serif;
  cursor: pointer;
}

.kimi-new-chat:hover { background: var(--hover-bg); }
.kimi-new-chat > svg { width: 18px; height: 18px; fill: none; stroke: currentColor; stroke-width: 1.65; stroke-linecap: round; stroke-linejoin: round; }
.kimi-new-chat > span { flex: 1; text-align: left; white-space: nowrap; }
.kimi-new-chat kbd { display: flex; gap: 4px; font-family: inherit; }
.kimi-new-chat kbd b { width: 20px; height: 20px; display: grid; place-items: center; border-radius: 4px; background: var(--hover-bg); color: var(--muted); font-size: 12px; font-weight: 500; }

.kimi-nav { display: flex; flex-direction: column; }
.kimi-nav--primary { margin-top: 10px; }
.kimi-nav--secondary { margin-top: 4px; }

.kimi-nav__item {
  width: 100%;
  height: 40px;
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 0 9px;
  border: 0;
  border-radius: 9px;
  background: transparent;
  color: var(--text);
  font: 400 14px/1 Inter, sans-serif;
  text-align: left;
  cursor: pointer;
}

.kimi-nav__item:hover { background: var(--hover-bg); }
.kimi-nav__icon { width: 18px; height: 18px; flex: 0 0 18px; display: grid; place-items: center; }
.kimi-nav__icon :deep(svg), .kimi-info-card__icon :deep(svg), .kimi-pill :deep(svg) { width: 18px; height: 18px; fill: none; stroke: currentColor; stroke-width: 1.65; stroke-linecap: round; stroke-linejoin: round; }
.kimi-nav__text { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.kimi-beta { margin-left: 1px; padding: 3px 5px; border-radius: 4px; background: #e7f2ff; color: #1683ea; font-size: 11px; line-height: 1; }
.kimi-shell--dark .kimi-beta { background: #0b304e; color: #58aef5; }

.kimi-collapse-row {
  width: 100%;
  height: 32px;
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 0 9px;
  border: 0;
  background: transparent;
  color: var(--muted);
  font: 400 14px/1 Inter, sans-serif;
  cursor: pointer;
}

.kimi-collapse-row__dots { width: 18px; color: var(--muted); letter-spacing: 2px; transform: translateY(-2px); }
.kimi-collapse-row svg { width: 16px; height: 16px; margin-left: auto; fill: none; stroke: currentColor; stroke-width: 1.6; stroke-linecap: round; stroke-linejoin: round; transition: transform 180ms ease; }
.kimi-collapse-row svg.is-closed { transform: rotate(-90deg); }

/* История чатов: flex:1 забирает всё место до «Основного», скроллится,
   нижние ~26px маскируются градиентом — последний чат мягко угасает. */
.kimi-history {
  flex: 1;
  min-height: 0;
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 1px;
  overflow-y: auto;
  scrollbar-width: none;
  padding-bottom: 6px;
  -webkit-mask-image: linear-gradient(to bottom, #000 calc(100% - 26px), transparent);
  mask-image: linear-gradient(to bottom, #000 calc(100% - 26px), transparent);
}
.kimi-history::-webkit-scrollbar { width: 0; height: 0; }
.kimi-history__item {
  width: 100%;
  height: 38px;
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  padding: 0 9px;
  border: 0;
  border-radius: 9px;
  background: transparent;
  color: var(--text);
  font: 400 14px/1 Inter, sans-serif;
  text-align: left;
  cursor: pointer;
}
.kimi-history__item:hover { background: var(--hover-bg); }
.kimi-history__item.is-active { background: var(--hover-bg); font-weight: 500; }
.kimi-history__title { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.kimi-projects-label { padding: 4px 8px 4px; color: var(--muted); font-size: 14px; line-height: 18px; }

.kimi-info-card {
  width: 100%;
  flex: 0 0 auto;
  padding: 8px;
  border: 1px solid var(--strong-line);
  border-radius: 16px;
  background: var(--utility-bg);
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.08);
}

.kimi-info-card button {
  width: 100%;
  height: 36px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 8px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--text);
  font: 400 14px/1 Inter, sans-serif;
  cursor: pointer;
}

.kimi-info-card button:hover { background: var(--hover-bg); }
.kimi-info-card__icon { width: 17px; height: 17px; display: grid; place-items: center; }
.kimi-info-card__icon :deep(svg) { width: 17px; height: 17px; }
.kimi-info-card__chevron { width: 15px; height: 15px; margin-left: auto; fill: none; stroke: var(--muted); stroke-width: 1.6; stroke-linecap: round; stroke-linejoin: round; }

.kimi-sidebar__footer { width: 240px; height: 60px; flex: 0 0 60px; margin: 0 -8px -9px; display: flex; align-items: center; padding: 0 8px; background: var(--sidebar-bg); }
.kimi-account { min-width: 0; height: 44px; flex: 1 1 auto; display: flex; align-items: center; gap: 9px; padding: 8px; border: 0; border-radius: 12px; background: transparent; color: var(--text); font: 400 14px/1 Inter, sans-serif; cursor: pointer; }
.kimi-account:hover { background: var(--hover-bg); }
.kimi-account__avatar { width: 28px; height: 28px; flex: 0 0 28px; display: grid; place-items: center; border-radius: 50%; background: #e8e8e8; color: #aaa; }
.kimi-shell--dark .kimi-account__avatar { background: #3b3b3b; color: #777; }
.kimi-account__avatar svg { width: 20px; height: 20px; fill: currentColor; stroke: none; }
.kimi-account > span:last-child { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.kimi-download { width: 30px; height: 30px; margin-left: auto; display: grid; place-items: center; border: 0; border-radius: 8px; background: transparent; color: var(--muted); cursor: pointer; }
.kimi-download:hover { background: var(--hover-bg); }
.kimi-download svg { width: 17px; height: 17px; fill: none; stroke: currentColor; stroke-width: 1.65; stroke-linecap: round; stroke-linejoin: round; }

.kimi-main {
  flex: 1;
  min-width: 0;
  padding: 6px 6px 6px 0;
  background: var(--sidebar-bg);
}

.kimi-stage {
  position: relative;
  width: 100%;
  height: 100%;
  min-width: 0;
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--panel-bg);
  opacity: 0;
  transform: translateY(4px);
}

.kimi-shell--ready .kimi-stage {
  animation: kimi-stage-enter 360ms cubic-bezier(0.22, 1, 0.36, 1) 40ms forwards;
}

.kimi-center {
  position: absolute;
  top: 50%;
  left: 50%;
  width: min(768px, calc(100% - 64px));
  transform: translate(-50%, -60%) translateY(1px);
}

.kimi-wordmark-space { height: 78px; }

.kimi-composer {
  height: 130px;
  padding: 14px 10px 9px 18px;
  display: flex;
  flex-direction: column;
  border: 1px solid #d5d5d5;
  border-radius: 24px;
  background: var(--composer-bg);
  box-shadow: 0 5px 12px rgba(0, 0, 0, 0.08);
  opacity: 0;
  transform: translateY(10px);
}

.kimi-shell--ready .kimi-composer {
  animation: kimi-rise 500ms cubic-bezier(0.22, 1, 0.36, 1) 120ms forwards;
}

.kimi-shell--dark .kimi-composer { border-color: #424242; box-shadow: 0 5px 14px rgba(0, 0, 0, 0.25); }

.kimi-composer textarea {
  width: 100%;
  min-height: 54px;
  max-height: 80px;
  flex: 1;
  padding: 0;
  border: 0;
  outline: 0;
  resize: none;
  overflow-y: auto;
  background: transparent;
  color: var(--text);
  font: 400 16px/1.45 Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.kimi-composer textarea::placeholder { color: #999; opacity: 1; }
.kimi-shell--dark .kimi-composer textarea::placeholder { color: #858585; }

.kimi-composer__actions { height: 39px; display: flex; align-items: center; justify-content: space-between; }
.kimi-plus { width: 34px; height: 34px; margin-left: -10px; display: grid; place-items: center; border: 0; border-radius: 50%; background: transparent; color: #555; cursor: pointer; }
.kimi-plus:hover { background: var(--hover-bg); }
.kimi-shell--dark .kimi-plus { color: #aaa; }
.kimi-plus svg { width: 21px; height: 21px; fill: none; stroke: currentColor; stroke-width: 1.5; stroke-linecap: round; }
.kimi-composer__right { display: flex; align-items: center; gap: 12px; }
.kimi-model { height: 34px; display: inline-flex; align-items: center; gap: 5px; padding: 0 2px 0 8px; border: 0; background: transparent; color: #313131; font: 400 14px/1 Inter, sans-serif; cursor: pointer; }
.kimi-shell--dark .kimi-model { color: #ddd; }
.kimi-model strong { color: var(--muted); font-weight: 400; }
.kimi-model svg { width: 15px; height: 15px; fill: none; stroke: var(--muted); stroke-width: 1.5; stroke-linecap: round; stroke-linejoin: round; }
.kimi-send { width: 37px; height: 37px; display: grid; place-items: center; border: 0; border-radius: 50%; background: #dedede; color: #fff; cursor: default; transition: background 120ms ease; }
.kimi-shell--dark .kimi-send { background: #4b4b4b; color: #202020; }
.kimi-send--active { background: #111; color: #fff; cursor: pointer; }
.kimi-shell--dark .kimi-send--active { background: #f1f1f1; color: #111; }
.kimi-send svg { width: 19px; height: 19px; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }

.kimi-shell--collapsed .kimi-sidebar { width: 64px; flex-basis: 64px; }
.kimi-shell--collapsed .kimi-sidebar__brand-row { padding: 0 9px; justify-content: center; }
.kimi-shell--collapsed .kimi-back,
.kimi-shell--collapsed .kimi-sidebar__toggle,
.kimi-shell--collapsed .kimi-new-chat > span,
.kimi-shell--collapsed .kimi-new-chat kbd,
.kimi-shell--collapsed .kimi-history,
.kimi-shell--collapsed .kimi-projects-label,
.kimi-shell--collapsed .kimi-info-card,
.kimi-shell--collapsed .kimi-account > span:last-child { display: none; }
.kimi-shell--collapsed .kimi-new-chat { width: 43px; margin-inline: auto; justify-content: center; padding: 0; }
.kimi-shell--collapsed .kimi-sidebar__footer { justify-content: center; padding-inline: 0; }
.kimi-shell--collapsed .kimi-account { flex: 0 0 auto; }

@keyframes kimi-stage-enter {
  to { opacity: 1; transform: none; }
}

@keyframes kimi-sidebar-enter {
  to { opacity: 1; transform: none; }
}

@keyframes kimi-rise {
  to { opacity: 1; transform: none; }
}

@media (max-height: 760px) {
  .kimi-info-card button { height: 31px; }
  .kimi-center { transform: translate(-50%, -54%); }
}

@media (max-width: 900px) {
  .kimi-sidebar { width: 64px; flex-basis: 64px; }
  .kimi-sidebar__brand-row { padding: 0 9px; justify-content: center; }
  .kimi-back, .kimi-sidebar__toggle, .kimi-new-chat > span, .kimi-new-chat kbd, .kimi-history,
  .kimi-projects-label, .kimi-info-card,
  .kimi-account > span:last-child { display: none; }
  .kimi-new-chat { width: 43px; margin-inline: auto; justify-content: center; padding: 0; }
  .kimi-sidebar__footer { justify-content: center; padding-inline: 0; }
  .kimi-account { flex: 0 0 auto; }
  .kimi-center { width: calc(100% - 40px); }
}

@media (prefers-reduced-motion: reduce) {
  .kimi-shell,
  .kimi-sidebar,
  .kimi-stage,
  .kimi-composer {
    transition: none !important;
    animation: none !important;
    opacity: 1 !important;
  }

  .kimi-sidebar,
  .kimi-stage,
  .kimi-composer { transform: none !important; }
}
</style>
