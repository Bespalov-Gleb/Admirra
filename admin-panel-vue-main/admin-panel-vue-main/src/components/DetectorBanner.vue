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
          <span v-if="subtitle" class="detector-banner__hypothesis">{{ subtitle }}</span>
        </div>
        <button
          v-if="hasExpandableDetails"
          type="button"
          class="detector-banner__action"
          @click="expanded = !expanded"
        >
          {{ expanded ? 'Скрыть детали' : 'Что произошло' }}
        </button>
        <button
          v-if="primaryAlert"
          type="button"
          class="detector-banner__action detector-banner__action--ai"
          @click="$emit('ask-ai', primaryAlert)"
        >
          Спросить AI
        </button>
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
            <strong>{{ alertTitle(alert) }}</strong>
            <small>{{ alertMeta(alert) }}</small>
          </div>
          <div class="detector-alert-row__actions">
            <button type="button" @click="$emit('ask-ai', alert)">AI</button>
            <span class="detector-alert-row__snoozes">
              <button type="button" @click="$emit('snooze', alert, 1)">1 дн.</button>
              <button type="button" @click="$emit('snooze', alert, 3)">3 дн.</button>
              <button type="button" @click="$emit('snooze', alert, 7)">7 дн.</button>
            </span>
            <span class="detector-alert-row__divider" aria-hidden="true"></span>
            <button
              type="button"
              class="detector-alert-row__soft"
              title="Скроется до конца отклонения, поможет настроить детектор"
              @click="$emit('not-problem', alert)"
            >Не проблема<small>скроется до конца отклонения, поможет настроить детектор</small></button>
          </div>
        </article>

        <article
          v-for="alert in hiddenAlerts"
          :key="`hidden-${alert.id}`"
          class="detector-alert-row detector-alert-row--hidden"
        >
          <span class="detector-alert-row__dot"></span>
          <div class="detector-alert-row__body">
            <strong>{{ alertTitle(alert) }}</strong>
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

defineEmits(['collapse', 'ask-ai', 'snooze', 'not-problem', 'restore'])

const expanded = ref(false)

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

const alertMeta = (alert) => {
  const days = alert?.consecutive_days ? `${alert.consecutive_days} дн. подряд` : 'по истории проекта'
  const source = alert?.detection_level === 'campaign' ? 'кампания' : 'проект'
  return `${source} · ${days} · детектор, не AI`
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

.detector-alert-row__body strong {
  color: #1f2937;
  font-size: 0.86rem;
  font-weight: 850;
  line-height: 1.28;
  overflow-wrap: anywhere;
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
  padding: 0.4rem 0.55rem;
  background: #fff;
  color: #374151;
  font-size: 0.73rem;
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
  .detector-banner__hypothesis,
  .detector-alert-row__body strong {
    white-space: normal;
  }
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

.detector-alert-row__snoozes { display: inline-flex; gap: 0.3rem; }
.detector-alert-row__divider {
  width: 1px;
  align-self: stretch;
  background: rgba(15, 23, 42, 0.12);
  margin: 0 0.35rem;
}
.detector-alert-row__soft small {
  display: block;
  font-size: 0.58rem;
  font-weight: 500;
  color: #94a3b8;
  margin-top: 0.1rem;
  white-space: normal;
  max-width: 13rem;
  line-height: 1.25;
  text-align: left;
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
