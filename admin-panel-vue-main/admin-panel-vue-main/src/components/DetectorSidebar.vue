<template>
  <Teleport to="body">
    <transition name="det-sidebar-fade">
      <div v-if="open" class="det-sidebar-overlay" @click="$emit('close')"></div>
    </transition>
    <transition name="det-sidebar-slide">
      <aside v-if="open" class="det-sidebar" role="dialog" aria-label="Отклонения проекта">
        <header class="det-sidebar__head">
          <div class="det-sidebar__title">
            <span class="det-sidebar__title-ic" :class="`det-sidebar__title-ic--${headSeverity}`" aria-hidden="true">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l7 3v5c0 4.8-3 8.6-7 10-4-1.4-7-5.2-7-10V6l7-3z"/></svg>
            </span>
            <div>
              <strong>Отклонения проекта</strong>
              <span class="det-sidebar__count">{{ totalActive }} {{ declOtkl(totalActive) }}{{ hiddenAlerts.length ? ` · скрыто ${hiddenAlerts.length}` : '' }}</span>
            </div>
          </div>
          <button type="button" class="det-sidebar__close" aria-label="Закрыть" @click="$emit('close')">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>
          </button>
        </header>

        <div class="det-sidebar__body">
          <div v-if="!totalActive && !hiddenAlerts.length" class="det-sidebar__empty">
            <span class="det-sidebar__empty-ic" aria-hidden="true">
              <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6L9 17l-5-5"/></svg>
            </span>
            <p>Отклонений нет — проект в норме.</p>
          </div>

          <section v-for="group in visibleGroups" :key="group.key" class="det-group">
            <div class="det-group__label" :class="`det-group__label--${group.tone}`">
              <span>{{ group.title }}</span>
              <span class="det-group__badge">{{ group.items.length }}</span>
            </div>

            <article
              v-for="alert in group.items"
              :key="alert.id"
              class="det-alert"
              :class="[`det-alert--${alert.severity || 'warning'}`, { 'det-alert--hidden': group.key === 'hidden' }]"
            >
              <div class="det-alert__main">
                <span v-if="noveltyBadge(alert)" class="det-alert__novelty" :class="`det-alert__novelty--${alert.novelty}`">{{ noveltyBadge(alert) }}</span>
                <p class="det-alert__lead"><b>{{ leadParts(alert).bold }}</b>{{ leadParts(alert).rest }}</p>
                <p v-if="changedLine(alert)" class="det-alert__changed">{{ changedLine(alert) }}</p>
                <p v-if="metaLine(alert)" class="det-alert__meta">{{ metaLine(alert) }}</p>

                <!-- Контекст: короткая форма + разворот -->
                <div v-if="hasContext(alert)" class="det-alert__context">
                  <button type="button" class="det-alert__context-toggle" @click="toggleExpand(alert.id)">
                    <span>{{ expandedId === alert.id ? 'Свернуть' : 'Подробнее' }}</span>
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" :style="expandedId === alert.id ? 'transform:rotate(180deg)' : ''"><polyline points="6 9 12 15 18 9"/></svg>
                  </button>
                  <template v-if="expandedId !== alert.id">
                    <p class="det-alert__context-short">{{ contextShort(alert) }}</p>
                  </template>
                  <template v-else>
                    <p v-for="(rel, i) in relatedList(alert)" :key="`r-${i}`" class="det-alert__exp">{{ rel.full }}</p>
                    <p v-if="diagnosisText(alert)" class="det-alert__exp">{{ diagnosisText(alert) }}</p>
                    <p v-for="(c, i) in contributors(alert)" :key="`c-${i}`" class="det-alert__exp"><span class="det-alert__contrib">«{{ c.name }}»</span> — {{ c.metrics }}</p>
                    <p v-if="contributorsExtra(alert)" class="det-alert__exp det-alert__exp--muted">и ещё {{ contributorsExtra(alert) }} {{ campaignsWord(contributorsExtra(alert)) }}</p>
                  </template>
                </div>
              </div>

              <!-- Действия -->
              <div v-if="group.key !== 'hidden'" class="det-alert__actions">
                <button type="button" class="det-alert__ai" @click="$emit('ask-ai', alert)">Спросить AI</button>
                <button type="button" class="det-alert__btn" @click="$emit('acknowledge', alert)">Понятно</button>
                <span class="det-alert__snooze" :class="{ open: openSnoozeId === alert.id }">
                  <button type="button" class="det-alert__btn" @click.stop="toggleSnooze(alert.id)">Скрыть…</button>
                  <span class="det-alert__menu">
                    <button type="button" @click="snooze(alert, 'week')">На неделю</button>
                    <button v-if="periodEndLabel" type="button" @click="snooze(alert, 'period_end')">До конца периода ({{ periodEndLabel }})</button>
                  </span>
                </span>
                <button type="button" class="det-alert__ghost" @click="$emit('not-problem', alert)">Не проблема</button>
              </div>
              <div v-else class="det-alert__actions det-alert__actions--hidden">
                <span class="det-alert__hidden-meta">{{ hiddenMeta(alert) }}</span>
                <button type="button" class="det-alert__btn" @click="$emit('restore', alert)">Показать сейчас</button>
              </div>
            </article>
          </section>
        </div>
      </aside>
    </transition>
  </Teleport>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  alerts: { type: Array, default: () => [] },
  hiddenAlerts: { type: Array, default: () => [] },
  visibleFrom: { type: [String, Number, Date], default: null },
  activePeriodEnd: { type: [String, Number, Date], default: null },
})

const emit = defineEmits(['close', 'ask-ai', 'acknowledge', 'snooze', 'not-problem', 'restore'])

const expandedId = ref(null)
const openSnoozeId = ref(null)

const activeAlerts = computed(() => props.alerts || [])
const hiddenAlerts = computed(() => props.hiddenAlerts || [])
const totalActive = computed(() => activeAlerts.value.length)

const declOtkl = (n) => (n === 1 ? 'отклонение' : n > 1 && n < 5 ? 'отклонения' : 'отклонений')

// Группировка по новизне (логика ит.4 не меняется — меняется только подача).
const ACTION = new Set(['action_required'])
const FRESH = new Set(['new', 'worsened', 'improved'])
const groups = computed(() => [
  { key: 'action', title: 'Требует действия', tone: 'problem', items: activeAlerts.value.filter((a) => ACTION.has(a.novelty)) },
  { key: 'fresh', title: 'Новое · изменилось', tone: 'warning', items: activeAlerts.value.filter((a) => FRESH.has(a.novelty)) },
  { key: 'known', title: 'Продолжается', tone: 'muted', items: activeAlerts.value.filter((a) => a.novelty === 'known') },
  { key: 'hidden', title: 'Скрыто', tone: 'muted', items: hiddenAlerts.value },
])
const visibleGroups = computed(() => groups.value.filter((g) => g.items.length))

const headSeverity = computed(() =>
  activeAlerts.value.some((a) => a.severity === 'problem') ? 'problem' : (activeAlerts.value.length ? 'warning' : 'muted')
)

const periodEndLabel = computed(() => {
  if (!props.activePeriodEnd) return ''
  const d = new Date(props.activePeriodEnd)
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' })
})

const visibleFromLabel = computed(() => {
  if (!props.visibleFrom) return ''
  const d = new Date(props.visibleFrom)
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' })
})

const noveltyBadge = (a) => {
  if (a?.novelty === 'new') return visibleFromLabel.value ? `новое · с ${visibleFromLabel.value}` : 'новое'
  if (a?.novelty === 'worsened') return 'ухудшилось'
  if (a?.novelty === 'improved') return 'стало лучше'
  return ''
}

const leadPhrase = (a) => {
  const text = String(a?.hypothesis_text || '').replace(/\r/g, '').trim()
  if (!text) return 'Отклонение в показателях'
  const first = text.split(/\n\s*•\s*/)[0].replace(/^\s*•\s*/, '').trim()
  return first || text
}
const leadParts = (a) => {
  const text = leadPhrase(a)
  const idx = text.indexOf(':')
  if (idx === -1) return { bold: text, rest: '' }
  return { bold: text.slice(0, idx + 1), rest: text.slice(idx + 1) }
}

const fmtRatio = (v) => {
  const n = Number(v)
  return Number.isFinite(n) ? n.toLocaleString('ru-RU', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) : ''
}
const changedLine = (a) => {
  if (!a || (a.novelty !== 'worsened' && a.novelty !== 'improved')) return ''
  const w = fmtRatio(a.was_ratio); const n = fmtRatio(a.now_ratio)
  return w && n ? `Было в ${w} раза, стало в ${n}` : ''
}

// Длительность + просмотрено — приглушённой строкой.
const metaLine = (a) => {
  const parts = []
  if (a?.duration_label) parts.push(a.duration_label)
  if (a?.seen && a.novelty === 'known') parts.push('просмотрено')
  return parts.join(' · ')
}

const campaignsWord = (n) => {
  const abs = Math.abs(Number(n) || 0)
  if (abs % 100 >= 11 && abs % 100 <= 14) return 'кампаний'
  const d = abs % 10
  if (d === 1) return 'кампания'
  if (d >= 2 && d <= 4) return 'кампании'
  return 'кампаний'
}

const relatedList = (a) => (a?.meta && Array.isArray(a.meta.related) ? a.meta.related : [])
const diagnosisText = (a) => (a?.meta && a.meta.diagnosis ? String(a.meta.diagnosis).trim() : '')
const contributors = (a) => (a?.meta && Array.isArray(a.meta.contributors) ? a.meta.contributors : [])
const contributorsExtra = (a) => Number(a?.meta?.contributors_extra || 0)
const contributorsCount = (a) => Number(a?.meta?.contributors_count || contributors(a).length)

const contextShort = (a) => {
  const parts = relatedList(a).map((r) => (r?.short || '').trim()).filter(Boolean)
  const diag = diagnosisText(a)
  if (diag) parts.push(diag)
  const count = contributorsCount(a)
  if (count > 0) parts.push(`основной вклад — ${count} ${campaignsWord(count)}`)
  return parts.join(' · ')
}
const hasContext = (a) => relatedList(a).length > 0 || Boolean(diagnosisText(a)) || contributors(a).length > 0

const hiddenMeta = (a) => {
  const who = a?.snoozed_by_name || a?.dismissed_by_name || ''
  if (a?.not_problem_at || a?.dismissed_at) return who ? `${who} · не проблема` : 'не проблема'
  if (a?.snoozed_until) {
    const d = new Date(a.snoozed_until).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' })
    return who ? `${who} · до ${d}` : `скрыто до ${d}`
  }
  return 'скрыто'
}

const toggleExpand = (id) => { expandedId.value = expandedId.value === id ? null : id }
const toggleSnooze = (id) => { openSnoozeId.value = openSnoozeId.value === id ? null : id }
const snooze = (alert, mode) => { openSnoozeId.value = null; emit('snooze', alert, { mode }) }
</script>

<style scoped>
.det-sidebar-overlay {
  position: fixed;
  inset: 0;
  z-index: 2147483000;
  background: rgba(15, 23, 42, 0.34);
  backdrop-filter: blur(2px);
}
.det-sidebar {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  z-index: 2147483001;
  width: clamp(20rem, 33vw, 34rem);
  max-width: 100vw;
  display: flex;
  flex-direction: column;
  background: #fff;
  box-shadow: -1.5rem 0 3.5rem rgba(15, 23, 42, 0.18);
  font-family: Inter, sans-serif;
}

/* ── Шапка ── */
.det-sidebar__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 1.15rem 1.25rem;
  border-bottom: 1px solid #eef1f6;
}
.det-sidebar__title { display: flex; align-items: center; gap: 0.7rem; min-width: 0; }
.det-sidebar__title-ic {
  flex-shrink: 0;
  display: grid;
  place-items: center;
  width: 2.15rem;
  height: 2.15rem;
  border-radius: 0.7rem;
}
.det-sidebar__title-ic--problem { background: #fff0f0; color: #dc2626; }
.det-sidebar__title-ic--warning { background: #fff7e6; color: #b45309; }
.det-sidebar__title-ic--muted { background: #f2f5f9; color: #8a93a3; }
.det-sidebar__title strong { display: block; color: #1f2937; font-size: 1rem; font-weight: 850; line-height: 1.2; }
.det-sidebar__count { display: block; margin-top: 0.1rem; color: #98a2b6; font-size: 0.8rem; font-weight: 600; }
.det-sidebar__close {
  flex-shrink: 0;
  display: grid;
  place-items: center;
  width: 2.2rem;
  height: 2.2rem;
  border: 1px solid #eef1f6;
  border-radius: 0.7rem;
  background: #fff;
  color: #6b7280;
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s;
}
.det-sidebar__close:hover { color: #dc2626; border-color: #f2b8b8; }

/* ── Тело ── */
.det-sidebar__body { flex: 1; overflow-y: auto; padding: 1rem 1.25rem 2rem; }
.det-sidebar__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.9rem;
  padding: 4rem 1rem;
  text-align: center;
}
.det-sidebar__empty-ic { display: grid; place-items: center; width: 3.4rem; height: 3.4rem; border-radius: 999px; background: #edf9f1; color: #2f9e58; }
.det-sidebar__empty p { margin: 0; color: #6b7280; font-size: 0.92rem; font-weight: 600; }

/* ── Группа ── */
.det-group { margin-bottom: 1.4rem; }
.det-group__label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.6rem;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.det-group__label--problem { color: #dc2626; }
.det-group__label--warning { color: #b45309; }
.det-group__label--muted { color: #98a2b6; }
.det-group__badge {
  display: inline-grid;
  place-items: center;
  min-width: 1.3rem;
  height: 1.3rem;
  padding: 0 0.35rem;
  border-radius: 999px;
  background: currentColor;
  color: #fff;
  font-size: 0.7rem;
  font-weight: 800;
}
.det-group__label--problem .det-group__badge { color: #fff; background: #ef4444; }
.det-group__label--warning .det-group__badge { color: #fff; background: #f59e0b; }
.det-group__label--muted .det-group__badge { color: #fff; background: #b8c0cc; }

/* ── Карточка алерта ── */
.det-alert {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
  margin-bottom: 0.6rem;
  padding: 0.9rem 1rem 0.9rem 1.15rem;
  border: 1px solid #eef1f6;
  border-radius: 0.9rem;
  background: #fff;
  overflow: hidden;
}
.det-alert::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 4px;
}
.det-alert--problem::before { background: #ef4444; }
.det-alert--warning::before { background: #f59e0b; }
.det-alert--hidden { background: #fafbfc; }
.det-alert--hidden::before { background: #cbd2dc; }

.det-alert__main { display: flex; flex-direction: column; gap: 0.35rem; min-width: 0; }
.det-alert__novelty {
  align-self: flex-start;
  padding: 0.1rem 0.5rem;
  border-radius: 999px;
  font-size: 0.66rem;
  font-weight: 800;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}
.det-alert__novelty--new { background: #dbeafe; color: #1d4ed8; }
.det-alert__novelty--worsened { background: #fee2e2; color: #b91c1c; }
.det-alert__novelty--improved { background: #dcfce7; color: #15803d; }
.det-alert__lead { margin: 0; color: #1f2937; font-size: 0.9rem; font-weight: 500; line-height: 1.42; overflow-wrap: anywhere; }
.det-alert__lead b { font-weight: 850; }
.det-alert__changed { margin: 0; color: #4b5563; font-size: 0.82rem; font-weight: 650; line-height: 1.4; }
.det-alert__meta { margin: 0; color: #98a2b6; font-size: 0.76rem; font-weight: 600; }

/* контекст */
.det-alert__context { display: flex; flex-direction: column; gap: 0.35rem; }
.det-alert__context-toggle {
  align-self: flex-start;
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  border: 0;
  background: none;
  padding: 0.1rem 0;
  color: #2563eb;
  font-size: 0.78rem;
  font-weight: 750;
  cursor: pointer;
}
.det-alert__context-toggle svg { transition: transform 0.18s ease; }
.det-alert__context-short { margin: 0; color: #6b7280; font-size: 0.8rem; font-weight: 600; line-height: 1.5; overflow-wrap: anywhere; }
.det-alert__exp { margin: 0; color: #4b5563; font-size: 0.8rem; font-weight: 600; line-height: 1.45; overflow-wrap: anywhere; }
.det-alert__exp--muted { color: #98a2b6; font-style: italic; }
.det-alert__contrib { font-weight: 750; }

/* действия */
.det-alert__actions { display: flex; flex-wrap: wrap; align-items: center; gap: 0.4rem; }
.det-alert__actions--hidden { justify-content: space-between; }
.det-alert__hidden-meta { color: #98a2b6; font-size: 0.76rem; font-weight: 600; }
.det-alert__ai, .det-alert__btn, .det-alert__ghost, .det-alert__actions button {
  min-height: 2.25rem;
  padding: 0.46rem 0.7rem;
  border: 1px solid #e5e7eb;
  border-radius: 999px;
  background: #fff;
  color: #374151;
  font-size: 0.78rem;
  font-weight: 800;
  line-height: 1;
  white-space: nowrap;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s, background 0.15s;
}
.det-alert__btn:hover { border-color: #bfdbfe; color: #2563eb; }
.det-alert__ai { border-color: #2563eb; background: #2563eb; color: #fff; }
.det-alert__ai:hover { border-color: #1d4ed8; background: #1d4ed8; }
.det-alert__ghost { border-color: transparent; background: transparent; color: #9ca3af; font-weight: 700; }
.det-alert__ghost:hover { color: #6b7280; background: rgba(15, 23, 42, 0.04); }

.det-alert__snooze { position: relative; }
.det-alert__menu {
  position: absolute;
  top: calc(100% + 0.3rem);
  left: 0;
  z-index: 5;
  display: none;
  flex-direction: column;
  min-width: 12rem;
  padding: 0.3rem;
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 0.6rem;
  background: #fff;
  box-shadow: 0 0.7rem 1.8rem rgba(15, 23, 42, 0.16);
}
.det-alert__snooze.open .det-alert__menu { display: flex; }
.det-alert__menu button {
  min-height: auto;
  border: 0;
  border-radius: 0.4rem;
  padding: 0.5rem 0.6rem;
  background: transparent;
  color: #334155;
  text-align: left;
  font-weight: 700;
  font-size: 0.78rem;
  cursor: pointer;
}
.det-alert__menu button:hover { background: #f1f5f9; }

/* ── Анимации ── */
.det-sidebar-fade-enter-active, .det-sidebar-fade-leave-active { transition: opacity 0.25s ease; }
.det-sidebar-fade-enter-from, .det-sidebar-fade-leave-to { opacity: 0; }
.det-sidebar-slide-enter-active, .det-sidebar-slide-leave-active { transition: transform 0.28s cubic-bezier(0.22, 1, 0.36, 1); }
.det-sidebar-slide-enter-from, .det-sidebar-slide-leave-to { transform: translateX(100%); }

@media (max-width: 620px) {
  .det-sidebar { width: 100vw; }
}
</style>
