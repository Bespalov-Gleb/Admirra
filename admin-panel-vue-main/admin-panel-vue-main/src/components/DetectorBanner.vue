<template>
  <transition name="detector-banner">
    <section v-if="visible" class="detector-banner" :class="bannerClass">
      <div class="detector-banner__top">
        <div class="detector-banner__icon" aria-hidden="true">
          <svg v-if="severity === 'problem'" width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="7.8" x2="12" y2="12.2"/><line x1="12" y1="16.2" x2="12.01" y2="16.2"/>
          </svg>
          <svg v-else width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M10.3 4.1 2.1 18.1A2 2 0 0 0 3.8 21h16.4a2 2 0 0 0 1.7-2.9L13.7 4.1a2 2 0 0 0-3.4 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
        </div>
        <div class="detector-banner__text">
          <span class="detector-banner__title">{{ title }}</span>
          <!-- Один алерт (в т.ч. составной P-1+P-2+P-3) — показываем полностью
               все пункты прямо в баннере: это и есть общий алерт на дашборде. -->
          <div
            v-if="bannerSections"
            class="detector-banner__hypothesis"
            :class="{ 'detector-banner__hypothesis--sectioned': bannerSections.length > 1 }"
          >
            <p v-for="(section, index) in bannerSections" :key="`banner-section-${index}`">{{ section }}</p>
            <span v-if="hiddenCount" class="detector-banner__hidden-note">Скрыто ещё {{ hiddenCount }}</span>
          </div>
          <span v-else-if="subtitle" class="detector-banner__hypothesis">{{ subtitle }}</span>
        </div>
        <button
          v-if="hasExpandableDetails"
          type="button"
          class="detector-banner__action"
          @click="expanded = !expanded"
        >
          {{ expanded ? 'Скрыть детали' : 'Смотреть все' }}
        </button>
        <button
          v-if="primaryAlert"
          type="button"
          class="detector-banner__action detector-banner__action--ai"
          @click="$emit('ask-ai', primaryAlert)"
        >
          Спросить AI
        </button>
        <!-- Один алерт: детали не разворачиваются (текст уже в баннере),
             поэтому «Скрыть» и «Не проблема» живут прямо в шапке -->
        <template v-if="singleAlert">
          <span class="detector-banner__snooze" :class="{ open: openSnoozeId === singleAlert.id }">
            <button type="button" class="detector-banner__action" @click.stop="openSnoozeId = openSnoozeId === singleAlert.id ? null : singleAlert.id">Скрыть</button>
            <span class="detector-banner__snooze-menu">
              <button type="button" @click="snooze(singleAlert, 1)">На 1 день</button>
              <button type="button" @click="snooze(singleAlert, 3)">На 3 дня</button>
              <button type="button" @click="snooze(singleAlert, 7)">На 7 дней</button>
            </span>
          </span>
          <button
            type="button"
            class="detector-banner__action detector-banner__action--soft"
            title="Скроется до конца отклонения, поможет настроить детектор"
            @click="$emit('not-problem', singleAlert)"
          >Не проблема</button>
        </template>
        <button type="button" class="detector-banner__close" title="Свернуть баннер" @click="$emit('collapse')">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M3.5 3.5 12.5 12.5M12.5 3.5 3.5 12.5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>
        </button>
      </div>

      <div v-if="expanded && hasExpandableDetails" class="detector-banner__details">
        <article
          v-for="alert in alerts"
          :key="alert.id"
          class="detector-alert-row"
          :class="`detector-alert-row--${alert.severity || 'warning'}`"
        >
          <span class="detector-alert-row__dot"></span>
          <div class="detector-alert-row__body">
            <div
              class="detector-alert-row__message"
              :class="{ 'detector-alert-row__message--sectioned': alertSections(alert).length > 1 }"
            >
              <p v-for="(section, index) in alertSections(alert)" :key="`${alert.id}-section-${index}`">{{ section }}</p>
            </div>
            <small>{{ alertMeta(alert) }}</small>
          </div>
          <div class="detector-alert-row__actions">
            <button type="button" class="detector-alert-row__ai" @click="$emit('ask-ai', alert)">Спросить AI</button>
            <span class="detector-alert-row__snooze" :class="{ open: openSnoozeId === alert.id }">
              <button type="button" @click.stop="openSnoozeId = openSnoozeId === alert.id ? null : alert.id">Скрыть</button>
              <span class="detector-alert-row__snooze-menu">
                <button type="button" @click="snooze(alert, 1)">На 1 день</button>
                <button type="button" @click="snooze(alert, 3)">На 3 дня</button>
                <button type="button" @click="snooze(alert, 7)">На 7 дней</button>
              </span>
            </span>
            <span class="detector-alert-row__divider" aria-hidden="true"></span>
            <button
              type="button"
              class="detector-alert-row__soft"
              title="Скроется до конца отклонения, поможет настроить детектор"
              @click="$emit('not-problem', alert)"
            >Не проблема</button>
          </div>
        </article>

        <article
          v-for="alert in hiddenAlerts"
          :key="`hidden-${alert.id}`"
          class="detector-alert-row detector-alert-row--hidden"
        >
          <span class="detector-alert-row__dot"></span>
          <div class="detector-alert-row__body">
            <div
              class="detector-alert-row__message"
              :class="{ 'detector-alert-row__message--sectioned': alertSections(alert).length > 1 }"
            >
              <p v-for="(section, index) in alertSections(alert)" :key="`${alert.id}-hidden-section-${index}`">{{ section }}</p>
            </div>
            <small>{{ hiddenMeta(alert) }}</small>
          </div>
          <div class="detector-alert-row__actions">
            <button type="button" @click="$emit('restore', alert)">Вернуть</button>
          </div>
        </article>
      </div>
    </section>
  </transition>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  warningCount: { type: Number, default: 0 },
  problemCount: { type: Number, default: 0 },
  hiddenCount: { type: Number, default: 0 },
  severity: { type: String, default: null },
  hypothesis: { type: String, default: '' },
  warmupStatus: { type: String, default: null },
  warmupDaysLeft: { type: Number, default: null },
  alerts: { type: Array, default: () => [] },
  hiddenAlerts: { type: Array, default: () => [] },
  syncIssues: { type: Array, default: () => [] },
})

const emit = defineEmits(['collapse', 'ask-ai', 'snooze', 'not-problem', 'restore'])

const expanded = ref(false)
// «Скрыть…» — дропдаун 1/3/7 дней на строке алерта
const openSnoozeId = ref(null)

const snooze = (alert, days) => {
  openSnoozeId.value = null
  emit('snooze', alert, days)
}

watch(() => [props.warningCount, props.problemCount, props.hiddenCount], () => {
  if (!props.warningCount && !props.problemCount) expanded.value = false
})

const visible = computed(() => {
  if (props.syncIssues.length) return true
  if (props.warmupStatus === 'warming_up') return true
  return props.warningCount > 0 || props.problemCount > 0 || props.hiddenCount > 0
})

const hasAlertRows = computed(() => props.alerts.length > 0 || props.hiddenAlerts.length > 0)
// For one alert the full diagnosis is already shown in the banner itself.
// A second identical row below only wastes space and makes it look like two
// different alerts. Details are useful when there are several items or hidden
// items to manage.
const hasExpandableDetails = computed(() => props.alerts.length + props.hiddenAlerts.length > 1)
const primaryAlert = computed(() => props.alerts[0] || null)
// Ровно один видимый алерт и нечего разворачивать — действия переезжают в шапку
const singleAlert = computed(() => (!hasExpandableDetails.value ? primaryAlert.value : null))

// Составной алерт (один эпизод, несколько проверок) выводим на дашборд
// целиком — все пункты. При нескольких алертах шапка остаётся короткой,
// а полный список раскрывается по «Смотреть все».
const bannerSections = computed(() => {
  if (!props.warningCount && !props.problemCount) return null
  if (!singleAlert.value) return null
  return alertSections(singleAlert.value)
})

const title = computed(() => {
  if (!props.warningCount && !props.problemCount && props.syncIssues.length) return 'Нет свежих данных по подключению'
  if (!props.warningCount && !props.problemCount && props.warmupStatus === 'warming_up') {
    const days = props.warmupDaysLeft ?? '?'
    return `Детектор накапливает данные, заработает через ${days} дн.`
  }
  const total = props.warningCount + props.problemCount
  const word = total === 1 ? 'отклонение' : total > 1 && total < 5 ? 'отклонения' : 'отклонений'
  if (total === 0 && props.hiddenCount > 0) return `Скрыто ${props.hiddenCount} отклонений`
  return `Обнаружено ${total} ${word}`
})

const subtitle = computed(() => {
  if (!props.warningCount && !props.problemCount && props.syncIssues.length) return props.syncIssues.map(issue => issue.text).join(' ')
  if (!props.warningCount && !props.problemCount && props.warmupStatus === 'warming_up') return 'Сначала нужна история по проекту. Это нейтральный статус, не алерт.'
  const hidden = props.hiddenCount ? ` · скрыто ${props.hiddenCount}` : ''
  return `${props.hypothesis || 'Проверьте динамику проекта и кампаний.'}${hidden}`
})

const bannerClass = computed(() => {
  if (!props.warningCount && !props.problemCount && props.syncIssues.length) return 'detector-banner--sync'
  if (!props.warningCount && !props.problemCount && props.warmupStatus === 'warming_up') return 'detector-banner--warmup'
  if (props.severity === 'problem') return 'detector-banner--problem'
  return 'detector-banner--warning'
})

const alertTitle = (alert) => alert?.hypothesis_text || 'Отклонение в показателях'

// Составной P-алерт — одна сущность с несколькими проверками, разделёнными
// маркером «•». Рендерим их отдельными абзацами, а не одной простынёй текста.
const alertSections = (alert) => {
  const text = alertTitle(alert).replace(/\r/g, '').trim()
  if (!text) return ['Отклонение в показателях']
  const sections = text
    .split(/\n\s*•\s*/)
    .map((part) => part.replace(/^\s*•\s*/, '').trim())
    .filter(Boolean)
  return sections.length ? sections : [text]
}

const alertMeta = (alert) => {
  const days = alert?.consecutive_days ? `${alert.consecutive_days} дн. подряд` : 'по истории проекта'
  const source = alert?.detection_level === 'campaign' ? 'кампания' : 'проект'
  return `${source} · ${days}`
}

const hiddenMeta = (alert) => {
  if (alert?.snoozed_until) {
    return `отложено до ${new Date(alert.snoozed_until).toLocaleDateString('ru-RU')}`
  }
  if (alert?.not_problem_at || alert?.dismissed_at) return 'помечено как не проблема'
  return 'скрыто'
}
</script>

<style scoped>
.detector-banner {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  padding: 0.9rem 1.05rem;
  border-radius: 1.05rem;
  font-family: Inter, sans-serif;
  transition: all 0.25s ease;
}

.detector-banner__top {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-width: 0;
}

.detector-banner--warning {
  background: #fff8e8;
  border: 1px solid #f6d996;
  color: #8a5217;
}

.detector-banner--problem {
  background: #fff1f1;
  border: 1px solid #ffb9b9;
  color: #9c2323;
}

.detector-banner--warmup {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  color: #1e40af;
}
.detector-banner--sync { background:#f4f6f9;border:1px solid #dce3ed;color:#69758a; }

.detector-banner__icon {
  flex-shrink: 0;
  display: grid;
  place-items: center;
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 0.8rem;
  background: rgba(255, 255, 255, 0.72);
}

.detector-banner__text {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 0.18rem;
  min-width: 0;
}

.detector-banner__title {
  color: #1f2937;
  font-size: 0.98rem;
  font-weight: 900;
  line-height: 1.25;
}

.detector-banner__hypothesis {
  color: currentColor;
  font-size: 0.84rem;
  font-weight: 650;
  line-height: 1.35;
  opacity: 0.8;
  overflow-wrap: anywhere;
}

.detector-banner__hypothesis p { margin: 0; }
.detector-banner__hypothesis--sectioned {
  display: grid;
  gap: 0.28rem;
}
.detector-banner__hypothesis--sectioned p {
  position: relative;
  padding-left: 0.95rem;
}
.detector-banner__hypothesis--sectioned p::before {
  position: absolute;
  top: 0;
  left: 0.15rem;
  content: '•';
}
.detector-banner__hidden-note {
  font-size: 0.78rem;
  font-weight: 650;
  opacity: 0.7;
}

.detector-banner__action {
  flex-shrink: 0;
  border: 1px solid rgba(255, 255, 255, 0.65);
  border-radius: 999px;
  padding: 0.55rem 0.78rem;
  background: rgba(255, 255, 255, 0.72);
  color: currentColor;
  font-size: 0.8rem;
  font-weight: 900;
  cursor: pointer;
}

.detector-banner__action:hover {
  background: #fff;
}

.detector-banner__action--ai {
  color: #2563eb;
}

.detector-banner__close {
  flex-shrink: 0;
  display: grid;
  place-items: center;
  width: 2rem;
  height: 2rem;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: currentColor;
  cursor: pointer;
  opacity: 0.55;
}

.detector-banner__close:hover {
  background: rgba(255, 255, 255, 0.55);
  opacity: 1;
}

.detector-banner__details {
  display: grid;
  gap: 0.55rem;
}

.detector-alert-row {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 0.65rem;
  padding: 0.65rem 0.75rem;
  border-radius: 0.85rem;
  background: rgba(255, 255, 255, 0.72);
}

.detector-alert-row__dot {
  width: 0.58rem;
  height: 0.58rem;
  border-radius: 999px;
  background: currentColor;
  box-shadow: 0 0 0 0.24rem color-mix(in srgb, currentColor 14%, transparent);
}

.detector-alert-row__body {
  display: flex;
  flex-direction: column;
  gap: 0.16rem;
  min-width: 0;
}

.detector-alert-row__message {
  display: grid;
  gap: 0.38rem;
  color: #1f2937;
  font-size: 0.86rem;
  font-weight: 850;
  line-height: 1.38;
  overflow-wrap: anywhere;
}

.detector-alert-row__message p {
  margin: 0;
}

.detector-alert-row__message--sectioned p {
  position: relative;
  padding-left: 0.95rem;
}

.detector-alert-row__message--sectioned p::before {
  position: absolute;
  top: 0;
  left: 0.18rem;
  color: currentColor;
  content: '•';
}

.detector-alert-row__body small {
  color: #6b7280;
  font-size: 0.75rem;
  font-weight: 650;
}

.detector-alert-row__actions {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.detector-alert-row__actions button {
  border: 1px solid #e5e7eb;
  border-radius: 999px;
  min-height: 2.45rem;
  padding: 0.58rem 0.85rem;
  background: #fff;
  color: #374151;
  font-size: 0.8rem;
  font-weight: 850;
  cursor: pointer;
}

.detector-alert-row__actions button:hover {
  border-color: #bfdbfe;
  color: #2563eb;
}

.detector-alert-row__actions .detector-alert-row__soft {
  color: #6b7280;
}

.detector-alert-row--problem {
  color: #ef4444;
}

.detector-alert-row--warning {
  color: #f59e0b;
}

.detector-alert-row--hidden {
  color: #9ca3af;
  opacity: 0.72;
}

.detector-banner-enter-active,
.detector-banner-leave-active {
  transition: all 0.25s ease;
}
.detector-banner-enter-from,
.detector-banner-leave-to {
  opacity: 0;
  transform: translateY(-0.35rem);
}

@media (max-width: 760px) {
  .detector-banner {
    border-radius: 1.1rem;
  }
  .detector-banner__top,
  .detector-alert-row {
    align-items: flex-start;
  }
  .detector-banner__top,
  .detector-alert-row__actions {
    flex-wrap: wrap;
  }
  .detector-alert-row {
    grid-template-columns: auto minmax(0, 1fr);
  }
  .detector-alert-row__actions {
    grid-column: 2;
  }
  .detector-banner__hypothesis { white-space: normal; }
}

:root.dark .detector-banner--warning,
.dark .detector-banner--warning,
.darkmode .detector-banner--warning { background: rgba(251, 191, 36, 0.12); border-color: rgba(251, 191, 36, 0.28); color: #fbbf24; }
:root.dark .detector-banner--problem,
.dark .detector-banner--problem,
.darkmode .detector-banner--problem { background: rgba(239, 68, 68, 0.12); border-color: rgba(239, 68, 68, 0.28); color: #f87171; }
:root.dark .detector-banner--warmup,
.dark .detector-banner--warmup,
.darkmode .detector-banner--warmup { background: rgba(59, 130, 246, 0.12); border-color: rgba(59, 130, 246, 0.28); color: #60a5fa; }

/* Дропдаун «Скрыть…» в шапке баннера (кейс одного алерта) */
.detector-banner__snooze { position: relative; display: inline-flex; flex-shrink: 0; }

.detector-banner__snooze-menu {
  position: absolute;
  top: calc(100% + 0.3rem);
  right: 0;
  z-index: 6;
  display: none;
  flex-direction: column;
  min-width: 10.5rem;
  padding: 0.42rem;
  border: 1px solid #e5e7eb;
  border-radius: 0.7rem;
  background: #fff;
  box-shadow: 0 0.8rem 2rem rgba(15, 23, 42, 0.16);
}

.detector-banner__snooze.open .detector-banner__snooze-menu { display: flex; }

.detector-banner__snooze-menu button {
  border: 0;
  min-height: 2.55rem;
  padding: 0.6rem 0.8rem;
  border-radius: 0.5rem;
  background: transparent;
  color: #374151;
  font-size: 0.8rem;
  font-weight: 800;
  text-align: left;
  white-space: nowrap;
  cursor: pointer;
}

.detector-banner__snooze-menu button:hover { background: #f3f6fc; color: #2563eb; }

.detector-banner__action--soft { opacity: 0.75; }
.detector-banner__action--soft:hover { opacity: 1; }

/* Дропдаун «Скрыть…» на строке алерта */
.detector-alert-row__snooze { position: relative; display: inline-flex; }

.detector-alert-row__snooze-menu {
  position: absolute;
  top: calc(100% + 0.3rem);
  right: 0;
  z-index: 6;
  display: none;
  flex-direction: column;
  min-width: 10.5rem;
  padding: 0.42rem;
  border: 1px solid #e5e7eb;
  border-radius: 0.7rem;
  background: #fff;
  box-shadow: 0 0.8rem 2rem rgba(15, 23, 42, 0.16);
}

.detector-alert-row__snooze.open .detector-alert-row__snooze-menu { display: flex; }

.detector-alert-row__snooze-menu button {
  border: 0 !important;
  min-height: 2.55rem;
  padding: 0.6rem 0.8rem !important;
  text-align: left;
  white-space: nowrap;
}

.detector-alert-row__ai {
  color: #2563eb !important;
  border-color: rgba(37, 99, 235, 0.35) !important;
}
.detector-alert-row__divider {
  width: 1px;
  align-self: stretch;
  background: rgba(15, 23, 42, 0.12);
  margin: 0 0.35rem;
}
/* ТЗ ит.2 п.1.8: мобильная версия — баннер компактный, действия вертикально, тап ≥44px */
@media (max-width: 767px) {
  .detector-banner__head { flex-wrap: wrap; gap: 0.5rem; }
  .detector-alert-row { flex-direction: column; align-items: flex-start; gap: 0.5rem; }
  .detector-alert-row__actions {
    flex-direction: column;
    align-items: stretch;
    width: 100%;
    gap: 0.4rem;
  }
  .detector-alert-row__actions button { min-height: 44px; }
  .detector-alert-row__snoozes { display: flex; }
  .detector-alert-row__snoozes button { flex: 1; }
  .detector-alert-row__divider { width: 100%; height: 1px; margin: 0.2rem 0; }
}
</style>
