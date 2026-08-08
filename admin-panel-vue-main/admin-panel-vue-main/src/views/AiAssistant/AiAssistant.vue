<template>
  <!-- Полноэкранный чат-ассистент (макет). Раскладка чат-приложения:
       левый чат-сайдбар + центр (лого · приветствие · ввод · селектор проекта
       · чипы). Светлая/тёмная темы через класс `dark` на <html>. Функционала
       пока нет — только основа под будущий бэкенд-агент. -->
  <div class="ai-shell" :class="{ 'ai-shell--enter': mounted }">
    <!-- ── Левый сайдбар чатов ── -->
    <aside class="ai-side" :class="{ 'ai-side--collapsed': sideCollapsed }">
      <div class="ai-side__head">
        <div class="ai-brand">
          <span class="ai-brand__mark" aria-hidden="true">
            <svg viewBox="0 0 32 32" width="26" height="26"><rect width="32" height="32" rx="9" fill="url(#aiBrandG)"/><path d="M10 22 16 9l6 13M12.4 18.2h7.2" stroke="#fff" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round" fill="none"/><defs><linearGradient id="aiBrandG" x1="0" y1="0" x2="32" y2="32"><stop stop-color="#3b6ef6"/><stop offset="1" stop-color="#2348d6"/></linearGradient></defs></svg>
          </span>
          <span v-if="!sideCollapsed" class="ai-brand__name">AdMirra <b>AI</b></span>
        </div>
        <button type="button" class="ai-icon-btn" :title="sideCollapsed ? 'Развернуть' : 'Свернуть'" @click="sideCollapsed = !sideCollapsed">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="16" rx="2.5"/><line x1="9" y1="4" x2="9" y2="20"/></svg>
        </button>
      </div>

      <button type="button" class="ai-newchat">
        <span class="ai-newchat__ic"><svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg></span>
        <span v-if="!sideCollapsed" class="ai-newchat__label">Новый чат</span>
        <kbd v-if="!sideCollapsed" class="ai-kbd">⌘K</kbd>
      </button>

      <nav class="ai-nav">
        <a v-for="item in tools" :key="item.label" class="ai-nav__item" href="#" @click.prevent>
          <span class="ai-nav__ic" v-html="item.icon"></span>
          <span v-if="!sideCollapsed" class="ai-nav__label">{{ item.label }}</span>
          <span v-if="!sideCollapsed && item.badge" class="ai-nav__badge">{{ item.badge }}</span>
        </a>
      </nav>

      <div v-if="!sideCollapsed" class="ai-history">
        <div class="ai-history__label">Недавние</div>
        <a v-for="chat in recentChats" :key="chat" class="ai-history__item" href="#" @click.prevent>{{ chat }}</a>
      </div>

      <div class="ai-side__foot">
        <div class="ai-user">
          <span class="ai-user__avatar">A</span>
          <div v-if="!sideCollapsed" class="ai-user__meta">
            <span class="ai-user__name">Аккаунт</span>
            <span class="ai-user__plan">Тариф Pro</span>
          </div>
        </div>
      </div>
    </aside>

    <!-- ── Основная область ── -->
    <section class="ai-main">
      <div class="ai-topbar">
        <button type="button" class="ai-back" @click="goBack">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><path d="M15 6l-6 6 6 6"/></svg>
          <span>К дашборду</span>
        </button>
        <button type="button" class="ai-upgrade">
          <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l2.6 5.3 5.8.8-4.2 4.1 1 5.8L12 16.9 6.8 19l1-5.8L3.6 9.1l5.8-.8z"/></svg>
          Повысить план
        </button>
      </div>

      <div class="ai-center">
        <div class="ai-hero">
          <span class="ai-hero__mark ai-anim" style="--d:0ms" aria-hidden="true">
            <svg viewBox="0 0 32 32" width="46" height="46"><rect width="32" height="32" rx="10" fill="url(#aiHeroG)"/><path d="M10 22 16 9l6 13M12.4 18.2h7.2" stroke="#fff" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round" fill="none"/><defs><linearGradient id="aiHeroG" x1="0" y1="0" x2="32" y2="32"><stop stop-color="#3b6ef6"/><stop offset="1" stop-color="#2348d6"/></linearGradient></defs></svg>
          </span>
          <h1 class="ai-hero__title ai-anim" style="--d:60ms">Чем помочь по проекту?</h1>
          <p class="ai-hero__sub ai-anim" style="--d:110ms">Спросите про кампании, цели, отчёты — данные проекта уже подключены.</p>
        </div>

        <div class="ai-composer ai-anim" style="--d:170ms">
          <textarea
            class="ai-composer__input"
            rows="1"
            placeholder="Напишите запрос или введите «/» для команд…"
            @input="autoGrow"
            ref="ta"
          ></textarea>
          <div class="ai-composer__row">
            <button type="button" class="ai-attach" title="Прикрепить">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>
            </button>
            <div class="ai-composer__right">
              <button type="button" class="ai-mode">
                <span class="ai-mode__dim">Режим</span> Быстрый
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9l6 6 6-6"/></svg>
              </button>
              <button type="button" class="ai-send" title="Отправить">
                <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5M6 11l6-6 6 6"/></svg>
              </button>
            </div>
          </div>
        </div>

        <button type="button" class="ai-project ai-anim" style="--d:220ms">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7.5A2.5 2.5 0 0 1 5.5 5h3.6c.7 0 1.36.3 1.83.81l1.04 1.13c.28.31.69.49 1.11.49h5.42A2.5 2.5 0 0 1 21 9.93v6.57A2.5 2.5 0 0 1 18.5 19h-13A2.5 2.5 0 0 1 3 16.5v-9Z"/></svg>
          Выбрать проект
          <svg class="ai-project__chev" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9l6 6 6-6"/></svg>
        </button>

        <div class="ai-chips ai-anim" style="--d:280ms">
          <button v-for="chip in chips" :key="chip.label" type="button" class="ai-chip">
            <span class="ai-chip__ic" v-html="chip.icon"></span>{{ chip.label }}
          </button>
        </div>
      </div>

      <div class="ai-foot-hint ai-anim" style="--d:340ms">AdMirra AI может ошибаться — сверяйте важные цифры с дашбордом.</div>
    </section>
  </div>
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref, nextTick } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const mounted = ref(false)
const sideCollapsed = ref(false)
const ta = ref(null)

const goBack = () => router.push('/dashboard/general-3')

// Мок-данные (без бэкенда).
const tools = [
  { label: 'Отчёт по проекту', icon: '<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19V5M4 19h16M8 15v-4M12 15V9M16 15v-6"/></svg>' },
  { label: 'Аудит кампаний', icon: '<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.2-3.2"/></svg>' },
  { label: 'Динамика', icon: '<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 17l5-5 4 3 6-7"/><path d="M14 8h5v5"/></svg>' },
  { label: 'Экспорт в таблицу', icon: '<svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3.5" y="4.5" width="17" height="15" rx="2"/><path d="M3.5 9.5h17M9 9.5v10M15 9.5v10"/></svg>', badge: 'Beta' },
]
const recentChats = [
  'Почему CPL вырос на этой неделе',
  'Сравнение направлений за месяц',
  'Кто из кампаний просел',
]
const chips = [
  { label: 'Сделай отчёт за месяц', icon: '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19V5M4 19h16M8 15v-4M12 15V9M16 15v-6"/></svg>' },
  { label: 'Проверь аномалии', icon: '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l9 16H3z"/><path d="M12 10v4M12 17h.01"/></svg>' },
  { label: 'Где сливается бюджет', icon: '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v6M12 22a7 7 0 0 0 7-7c0-3-3-6-7-11C8 9 5 12 5 15a7 7 0 0 0 7 7Z"/></svg>' },
  { label: 'Топ кампаний по CPL', icon: '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M8 21V10M4 21V6M12 21V4M16 21v-8M20 21v-5"/></svg>' },
]

const autoGrow = () => {
  const el = ta.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 200) + 'px'
}

let savedOverflow = ''
onMounted(async () => {
  savedOverflow = document.documentElement.style.overflow
  document.documentElement.style.overflow = 'hidden'
  await nextTick()
  requestAnimationFrame(() => { mounted.value = true })
})
onBeforeUnmount(() => {
  document.documentElement.style.overflow = savedOverflow
})
</script>

<style scoped>
/* ── Каркас ── */
.ai-shell {
  position: fixed;
  inset: 0;
  z-index: 40;
  display: flex;
  background: #f6f7f9;
  color: #1f2430;
  font-family: Inter, system-ui, sans-serif;
  opacity: 0;
  transition: opacity 0.35s ease;
}
.ai-shell--enter { opacity: 1; }
:global(html.dark) .ai-shell { background: #171922; color: #e6e8ee; }

/* ── Сайдбар ── */
.ai-side {
  flex-shrink: 0;
  width: 17rem;
  display: flex;
  flex-direction: column;
  padding: 0.85rem 0.7rem;
  border-right: 1px solid #ecedf1;
  background: #fbfbfc;
  transform: translateX(-14px);
  opacity: 0;
  transition: transform 0.45s cubic-bezier(0.22, 1, 0.36, 1) 0.05s, opacity 0.45s ease 0.05s, width 0.28s ease;
}
.ai-shell--enter .ai-side { transform: none; opacity: 1; }
.ai-side--collapsed { width: 4.4rem; }
:global(html.dark) .ai-side { background: #1b1e29; border-right-color: rgba(255, 255, 255, 0.06); }

.ai-side__head { display: flex; align-items: center; justify-content: space-between; gap: 0.4rem; padding: 0.3rem 0.35rem 0.7rem; }
.ai-brand { display: flex; align-items: center; gap: 0.55rem; min-width: 0; }
.ai-brand__mark { flex-shrink: 0; display: grid; place-items: center; }
.ai-brand__name { font-size: 1rem; font-weight: 650; letter-spacing: -0.01em; white-space: nowrap; }
.ai-brand__name b { font-weight: 850; color: #2348d6; }
:global(html.dark) .ai-brand__name b { color: #7d9bff; }

.ai-icon-btn { display: grid; place-items: center; width: 2rem; height: 2rem; border: 0; border-radius: 0.6rem; background: transparent; color: #8b93a3; cursor: pointer; transition: background 0.15s, color 0.15s; }
.ai-icon-btn:hover { background: rgba(15, 23, 42, 0.05); color: #4b5563; }
:global(html.dark) .ai-icon-btn:hover { background: rgba(255, 255, 255, 0.06); color: #cdd3df; }

.ai-newchat { display: flex; align-items: center; gap: 0.6rem; width: 100%; padding: 0.62rem 0.7rem; border: 1px solid #e6e8ee; border-radius: 0.75rem; background: #fff; color: #1f2430; font-size: 0.9rem; font-weight: 650; cursor: pointer; transition: border-color 0.15s, box-shadow 0.15s, background 0.15s; }
.ai-newchat:hover { border-color: #cdd6ea; box-shadow: 0 1px 0 rgba(15, 23, 42, 0.03); }
:global(html.dark) .ai-newchat { background: #232735; border-color: rgba(255, 255, 255, 0.07); color: #e6e8ee; }
:global(html.dark) .ai-newchat:hover { border-color: rgba(125, 155, 255, 0.4); }
.ai-newchat__ic { display: grid; place-items: center; color: #2348d6; }
:global(html.dark) .ai-newchat__ic { color: #7d9bff; }
.ai-newchat__label { flex: 1; text-align: left; }
.ai-kbd { padding: 0.1rem 0.35rem; border-radius: 0.35rem; background: rgba(15, 23, 42, 0.05); color: #8b93a3; font-size: 0.68rem; font-weight: 700; }
:global(html.dark) .ai-kbd { background: rgba(255, 255, 255, 0.07); color: #9aa2b2; }

.ai-nav { display: flex; flex-direction: column; gap: 0.1rem; margin-top: 0.9rem; }
.ai-nav__item { display: flex; align-items: center; gap: 0.65rem; padding: 0.5rem 0.6rem; border-radius: 0.6rem; color: #4b5468; font-size: 0.88rem; font-weight: 550; text-decoration: none; cursor: pointer; transition: background 0.15s, color 0.15s; }
.ai-nav__item:hover { background: rgba(15, 23, 42, 0.045); color: #1f2430; }
:global(html.dark) .ai-nav__item { color: #aab2c2; }
:global(html.dark) .ai-nav__item:hover { background: rgba(255, 255, 255, 0.05); color: #e6e8ee; }
.ai-nav__ic { flex-shrink: 0; display: grid; place-items: center; color: #8b93a3; }
.ai-nav__item:hover .ai-nav__ic { color: #2348d6; }
:global(html.dark) .ai-nav__item:hover .ai-nav__ic { color: #7d9bff; }
.ai-nav__label { flex: 1; }
.ai-nav__badge { padding: 0.05rem 0.35rem; border-radius: 0.35rem; background: #e9efff; color: #2348d6; font-size: 0.62rem; font-weight: 800; letter-spacing: 0.02em; }
:global(html.dark) .ai-nav__badge { background: rgba(125, 155, 255, 0.16); color: #9db6ff; }

.ai-history { margin-top: 1.1rem; overflow-y: auto; flex: 1; min-height: 0; }
.ai-history__label { padding: 0 0.6rem 0.4rem; font-size: 0.7rem; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase; color: #a0a7b5; }
.ai-history__item { display: block; padding: 0.48rem 0.6rem; border-radius: 0.55rem; color: #5b6474; font-size: 0.86rem; text-decoration: none; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; cursor: pointer; transition: background 0.15s, color 0.15s; }
.ai-history__item:hover { background: rgba(15, 23, 42, 0.045); color: #1f2430; }
:global(html.dark) .ai-history__item { color: #97a0b0; }
:global(html.dark) .ai-history__item:hover { background: rgba(255, 255, 255, 0.05); color: #e6e8ee; }

.ai-side__foot { margin-top: auto; padding-top: 0.6rem; border-top: 1px solid #ecedf1; }
:global(html.dark) .ai-side__foot { border-top-color: rgba(255, 255, 255, 0.06); }
.ai-user { display: flex; align-items: center; gap: 0.6rem; padding: 0.4rem 0.35rem; border-radius: 0.6rem; cursor: pointer; }
.ai-user:hover { background: rgba(15, 23, 42, 0.045); }
:global(html.dark) .ai-user:hover { background: rgba(255, 255, 255, 0.05); }
.ai-user__avatar { flex-shrink: 0; display: grid; place-items: center; width: 2rem; height: 2rem; border-radius: 999px; background: #2348d6; color: #fff; font-size: 0.85rem; font-weight: 800; }
.ai-user__meta { display: flex; flex-direction: column; min-width: 0; }
.ai-user__name { font-size: 0.86rem; font-weight: 650; }
.ai-user__plan { font-size: 0.72rem; color: #9aa2b2; }

/* ── Основное ── */
.ai-main { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.ai-topbar { display: flex; align-items: center; justify-content: space-between; padding: 0.85rem 1.25rem; }
.ai-back { display: inline-flex; align-items: center; gap: 0.35rem; padding: 0.42rem 0.7rem; border: 0; border-radius: 0.65rem; background: transparent; color: #6b7280; font-size: 0.85rem; font-weight: 600; cursor: pointer; transition: background 0.15s, color 0.15s; }
.ai-back:hover { background: rgba(15, 23, 42, 0.05); color: #1f2430; }
:global(html.dark) .ai-back { color: #97a0b0; }
:global(html.dark) .ai-back:hover { background: rgba(255, 255, 255, 0.05); color: #e6e8ee; }
.ai-upgrade { display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.46rem 0.9rem; border: 1px solid #d5deff; border-radius: 999px; background: #eef3ff; color: #2348d6; font-size: 0.83rem; font-weight: 750; cursor: pointer; transition: background 0.15s, border-color 0.15s; }
.ai-upgrade:hover { background: #e3ebff; border-color: #b9c8ff; }
:global(html.dark) .ai-upgrade { background: rgba(125, 155, 255, 0.12); border-color: rgba(125, 155, 255, 0.3); color: #a9c0ff; }

.ai-center { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 1rem 1.25rem; }
.ai-center > * { width: min(46rem, 100%); }

.ai-hero { text-align: center; margin-bottom: 1.6rem; display: flex; flex-direction: column; align-items: center; gap: 0.5rem; }
.ai-hero__mark { display: inline-grid; place-items: center; }
.ai-hero__title { margin: 0.2rem 0 0; font-size: 1.7rem; font-weight: 800; letter-spacing: -0.02em; text-wrap: balance; }
.ai-hero__sub { margin: 0; color: #7a8496; font-size: 0.96rem; max-width: 34rem; }
:global(html.dark) .ai-hero__sub { color: #8b93a3; }

/* Композер */
.ai-composer { border: 1px solid #e4e7ee; border-radius: 1.15rem; background: #fff; box-shadow: 0 2px 14px rgba(15, 23, 42, 0.04); padding: 0.9rem 1rem 0.7rem; transition: border-color 0.18s, box-shadow 0.18s; }
.ai-composer:focus-within { border-color: #b9c8ff; box-shadow: 0 4px 22px rgba(35, 72, 214, 0.09); }
:global(html.dark) .ai-composer { background: #232735; border-color: rgba(255, 255, 255, 0.08); box-shadow: none; }
:global(html.dark) .ai-composer:focus-within { border-color: rgba(125, 155, 255, 0.5); }
.ai-composer__input { width: 100%; border: 0; outline: 0; resize: none; background: transparent; color: inherit; font-family: inherit; font-size: 1rem; line-height: 1.5; max-height: 200px; }
.ai-composer__input::placeholder { color: #a3abba; }
.ai-composer__row { display: flex; align-items: center; justify-content: space-between; margin-top: 0.55rem; }
.ai-attach { display: grid; place-items: center; width: 2.3rem; height: 2.3rem; border: 1px solid #e6e8ee; border-radius: 0.7rem; background: #fff; color: #6b7280; cursor: pointer; transition: border-color 0.15s, color 0.15s, background 0.15s; }
.ai-attach:hover { border-color: #cdd6ea; color: #2348d6; }
:global(html.dark) .ai-attach { background: transparent; border-color: rgba(255, 255, 255, 0.1); color: #97a0b0; }
.ai-composer__right { display: flex; align-items: center; gap: 0.5rem; }
.ai-mode { display: inline-flex; align-items: center; gap: 0.32rem; padding: 0.48rem 0.7rem; border: 1px solid #e6e8ee; border-radius: 0.7rem; background: #fff; color: #4b5468; font-size: 0.83rem; font-weight: 650; cursor: pointer; transition: border-color 0.15s; }
.ai-mode:hover { border-color: #cdd6ea; }
.ai-mode__dim { color: #a3abba; font-weight: 550; }
:global(html.dark) .ai-mode { background: transparent; border-color: rgba(255, 255, 255, 0.1); color: #b8c0d0; }
.ai-send { display: grid; place-items: center; width: 2.3rem; height: 2.3rem; border: 0; border-radius: 0.7rem; background: #2348d6; color: #fff; cursor: pointer; transition: background 0.15s, transform 0.1s; }
.ai-send:hover { background: #1c3cbb; }
.ai-send:active { transform: scale(0.94); }

.ai-project { display: inline-flex; align-self: flex-start; align-items: center; gap: 0.45rem; margin-top: 0.85rem; padding: 0.5rem 0.8rem; border: 1px solid #e6e8ee; border-radius: 0.75rem; background: #fbfbfc; color: #4b5468; font-size: 0.86rem; font-weight: 650; cursor: pointer; transition: border-color 0.15s, background 0.15s; }
.ai-project:hover { border-color: #cdd6ea; background: #fff; }
:global(html.dark) .ai-project { background: rgba(255, 255, 255, 0.04); border-color: rgba(255, 255, 255, 0.1); color: #b8c0d0; }
.ai-project__chev { color: #a3abba; }

.ai-chips { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 1.4rem; justify-content: center; }
.ai-chip { display: inline-flex; align-items: center; gap: 0.45rem; padding: 0.5rem 0.85rem; border: 1px solid #e6e8ee; border-radius: 999px; background: #fff; color: #4b5468; font-size: 0.85rem; font-weight: 600; cursor: pointer; transition: border-color 0.15s, color 0.15s, background 0.15s; }
.ai-chip:hover { border-color: #b9c8ff; color: #2348d6; background: #f6f8ff; }
.ai-chip__ic { display: grid; place-items: center; color: #9aa2b2; }
.ai-chip:hover .ai-chip__ic { color: #2348d6; }
:global(html.dark) .ai-chip { background: rgba(255, 255, 255, 0.03); border-color: rgba(255, 255, 255, 0.09); color: #aab2c2; }
:global(html.dark) .ai-chip:hover { border-color: rgba(125, 155, 255, 0.5); color: #cbd7ff; background: rgba(125, 155, 255, 0.08); }

.ai-foot-hint { padding: 0.9rem 1.25rem 1.1rem; text-align: center; color: #a3abba; font-size: 0.78rem; }

/* ── Появление блоков (staggered) ── */
.ai-anim { opacity: 0; transform: translateY(10px); }
.ai-shell--enter .ai-anim { animation: ai-rise 0.5s cubic-bezier(0.22, 1, 0.36, 1) forwards; animation-delay: var(--d, 0ms); }
@keyframes ai-rise { to { opacity: 1; transform: none; } }

@media (prefers-reduced-motion: reduce) {
  .ai-shell, .ai-side, .ai-anim { transition: none !important; animation: none !important; opacity: 1 !important; transform: none !important; }
}

@media (max-width: 860px) {
  .ai-side { position: absolute; left: 0; top: 0; bottom: 0; z-index: 5; box-shadow: 0 0 40px rgba(15, 23, 42, 0.15); }
  .ai-side--collapsed { transform: translateX(-100%); width: 17rem; }
}
</style>
