<template>
  <transition name="detector-banner">
    <!-- ЖИВАЯ ПЛАШКА: контейнер блоков-эпизодов (правка 1) -->
    <section v-if="activeAlerts.length" class="detector-banner" :class="`detector-banner--${bannerSeverity}`">
      <div class="detector-banner__head">
        <span class="detector-banner__head-ic" aria-hidden="true">
          <svg v-if="bannerSeverity === 'problem'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="7.8" x2="12" y2="12.2"/><line x1="12" y1="16.2" x2="12.01" y2="16.2"/></svg>
          <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.3 4.1 2.1 18.1A2 2 0 0 0 3.8 21h16.4a2 2 0 0 0 1.7-2.9L13.7 4.1a2 2 0 0 0-3.4 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
        </span>
        <span class="detector-banner__title">{{ title }}</span>
      </div>

      <div class="detector-blocks">
        <article
          v-for="alert in activeAlerts"
          :key="alert.id"
          class="detector-block"
          :class="`detector-block--${alert.severity || 'warning'}`"
        >
          <span class="detector-block__dot"></span>
          <div class="detector-block__body">
            <p class="detector-block__lead">{{ leadPhrase(alert) }}</p>

            <!-- Строка контекста: короткие формы + один переключатель в конце -->
            <p v-if="hasDetails(alert)" class="detector-block__related">
              <template v-if="contextShort(alert)">
                <span class="detector-block__related-label">Связано:</span>
                <span class="detector-block__related-text">{{ contextShort(alert) }}</span>
              </template>
              <button
                type="button"
                class="detector-block__more-link"
                @click="toggleExpand(alert.id)"
              >{{ toggleLabel(alert) }}</button>
            </p>

            <!-- Развёрнутый контент: связанные → диагностика → виновники -->
            <div v-if="expandedId === alert.id && hasDetails(alert)" class="detector-block__expanded">
              <p
                v-for="(rel, i) in relatedList(alert)"
                :key="`rel-${i}`"
                class="detector-block__exp-line"
              >{{ rel.full }}</p>
              <p v-if="diagnosisText(alert)" class="detector-block__exp-line">{{ diagnosisText(alert) }}</p>
              <div v-if="contributors(alert).length" class="detector-block__contrib">
                <template v-if="contributorsInline(alert)">
                  <p class="detector-block__exp-line">
                    <span class="detector-block__contrib-label">Основной вклад:</span>
                    <span v-for="(c, i) in contributors(alert)" :key="`ci-${i}`">
                      <template v-if="i">&nbsp;·&nbsp;</template>«{{ c.name }}» — {{ c.metrics }}</span>
                    <template v-if="contributorsExtra(alert)">&nbsp;·&nbsp;и ещё {{ contributorsExtra(alert) }} {{ campaignsWord(contributorsExtra(alert)) }}</template>
                  </p>
                </template>
                <template v-else>
                  <p class="detector-block__contrib-label detector-block__contrib-label--own">Основной вклад:</p>
                  <p
                    v-for="(c, i) in contributors(alert)"
                    :key="`cl-${i}`"
                    class="detector-block__contrib-item"
                  ><span class="detector-block__contrib-name">«{{ c.name }}»</span> — {{ c.metrics }}</p>
                  <p v-if="contributorsExtra(alert)" class="detector-block__contrib-item detector-block__contrib-more">и ещё {{ contributorsExtra(alert) }} {{ campaignsWord(contributorsExtra(alert)) }}</p>
                </template>
              </div>
            </div>
          </div>

          <!-- Всегда три кнопки: «Спросить AI» · «Скрыть…» · «Не проблема» -->
          <div class="detector-block__actions">
            <button type="button" class="detector-block__ai" @click="$emit('ask-ai', alert)">Спросить AI</button>
            <span class="detector-block__snooze" :class="{ open: openSnoozeId === alert.id }">
              <button type="button" @click.stop="toggleSnooze(alert.id)">Скрыть…</button>
              <span class="detector-block__menu">
                <button type="button" @click="snooze(alert, 1)">Скрыть на 1 день</button>
                <button type="button" @click="snooze(alert, 3)">Скрыть на 3 дня</button>
                <button type="button" @click="snooze(alert, 7)">Скрыть на 7 дней</button>
              </span>
            </span>
            <button
              type="button"
              class="detector-block__notproblem"
              title="Скроется до конца отклонения, поможет настроить детектор"
              @click="notProblem(alert)"
            >Не проблема</button>
          </div>
        </article>
      </div>

      <!-- Состояние 2 (правка 2): футер скрытых внутри живой плашки -->
      <div v-if="hiddenAlerts.length" class="detector-banner__hidden-foot">
        <button type="button" class="detector-hidden-link" @click="hiddenListOpen = !hiddenListOpen">
          Скрыто ещё: {{ hiddenAlerts.length }}{{ nearestHiddenDate ? ` до ${nearestHiddenDate}` : '' }} · Показать
        </button>
        <div v-if="hiddenListOpen" class="detector-hidden-list">
          <div v-for="alert in hiddenAlerts" :key="`hf-${alert.id}`" class="detector-hidden-item">
            <span class="detector-hidden-item__text">{{ leadPhrase(alert) }}</span>
            <span class="detector-hidden-item__meta">{{ hiddenAuthorMeta(alert) }}</span>
            <button type="button" @click="$emit('restore', alert)">Показать сейчас</button>
          </div>
        </div>
      </div>
    </section>

    <!-- Нейтральные статусы: прогрев / нет данных синхронизации -->
    <section v-else-if="warmupStatus === 'warming_up' || syncIssues.length" class="detector-banner" :class="bannerClass">
      <div class="detector-banner__head">
        <span class="detector-banner__head-ic" aria-hidden="true">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>
        </span>
        <div class="detector-banner__text">
          <span class="detector-banner__title">{{ neutralTitle }}</span>
          <span class="detector-banner__hypothesis">{{ neutralSubtitle }}</span>
        </div>
      </div>
    </section>

    <!-- Состояние 1 (правка 2): все алерты скрыты — серый чип на позиции плашки -->
    <div v-else-if="hiddenAlerts.length" class="detector-hidden-chip-wrap">
      <button type="button" class="detector-hidden-chip" @click="hiddenListOpen = !hiddenListOpen">
        <span class="detector-hidden-chip__dot"></span>
        Скрыто: {{ hiddenAlerts.length }} {{ hiddenWord }}{{ nearestHiddenDate ? ` до ${nearestHiddenDate}` : '' }} · Показать
      </button>
      <div v-if="hiddenListOpen" class="detector-hidden-list detector-hidden-list--chip">
        <div v-for="alert in hiddenAlerts" :key="`hc-${alert.id}`" class="detector-hidden-item">
          <span class="detector-hidden-item__text">{{ leadPhrase(alert) }}</span>
          <span class="detector-hidden-item__meta">{{ hiddenAuthorMeta(alert) }}</span>
          <button type="button" @click="$emit('restore', alert)">Показать сейчас</button>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { computed, ref } from 'vue'

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

// collapse больше не эмитим — плашки-крестика нет (правка 1).
const emit = defineEmits(['ask-ai', 'snooze', 'not-problem', 'restore'])

const expandedId = ref(null)
const openSnoozeId = ref(null)
const hiddenListOpen = ref(false)

const activeAlerts = computed(() => props.alerts || [])
const hiddenAlerts = computed(() => props.hiddenAlerts || [])

const bannerSeverity = computed(() =>
  activeAlerts.value.some((a) => a.severity === 'problem') ? 'problem' : 'warning'
)

const declOtklon = (n) => (n === 1 ? 'отклонение' : n > 1 && n < 5 ? 'отклонения' : 'отклонений')

// Заголовок: N = число блоков (правка 1).
const title = computed(() => {
  const n = activeAlerts.value.length
  return `Обнаружено ${n} ${declOtklon(n)}`
})

const hiddenWord = computed(() => declOtklon(hiddenAlerts.value.length))

const bannerClass = computed(() => {
  if (props.warmupStatus === 'warming_up') return 'detector-banner--warmup'
  if (props.syncIssues.length) return 'detector-banner--sync'
  return `detector-banner--${bannerSeverity.value}`
})

const neutralTitle = computed(() => {
  if (props.warmupStatus === 'warming_up') {
    const days = props.warmupDaysLeft ?? '?'
    return `Детектор накапливает данные, заработает через ${days} дн.`
  }
  return 'Нет свежих данных по подключению'
})
const neutralSubtitle = computed(() => {
  if (props.warmupStatus === 'warming_up') return 'Сначала нужна история по проекту. Это нейтральный статус, не алерт.'
  return props.syncIssues.map((issue) => issue.text).join(' ')
})

// Ведущая фраза = первая секция hypothesis_text (до первого «•»). Всё остальное
// (связанные проверки, диагностика, виновники) баннер берёт из структурного meta,
// чтобы не дублировать (эталон §3) и показывать короткие формы с прогнозом (§2).
const leadPhrase = (alert) => {
  const text = String(alert?.hypothesis_text || '').replace(/\r/g, '').trim()
  if (!text) return 'Отклонение в показателях'
  const first = text.split(/\n\s*•\s*/)[0].replace(/^\s*•\s*/, '').trim()
  return first || text
}

const campaignsWord = (n) => {
  const abs = Math.abs(Number(n) || 0)
  if (abs % 100 >= 11 && abs % 100 <= 14) return 'кампаний'
  const d = abs % 10
  if (d === 1) return 'кампания'
  if (d >= 2 && d <= 4) return 'кампании'
  return 'кампаний'
}

const relatedList = (alert) => (alert?.meta && Array.isArray(alert.meta.related) ? alert.meta.related : [])
const diagnosisText = (alert) => (alert?.meta && alert.meta.diagnosis ? String(alert.meta.diagnosis).trim() : '')
const contributors = (alert) => (alert?.meta && Array.isArray(alert.meta.contributors) ? alert.meta.contributors : [])
const contributorsExtra = (alert) => Number(alert?.meta?.contributors_extra || 0)
const contributorsCount = (alert) =>
  Number(alert?.meta?.contributors_count || contributors(alert).length)

// Короткая форма для строки «Связано:»: связанные проверки (с прогнозом) +
// сводка виновников «основной вклад — N кампаний» (сами имена в короткой не видны).
const contextShort = (alert) => {
  const parts = relatedList(alert).map((r) => (r?.short || '').trim()).filter(Boolean)
  const count = contributorsCount(alert)
  if (count > 0) parts.push(`основной вклад — ${count} ${campaignsWord(count)}`)
  return parts.join(' · ')
}

const hasDetails = (alert) =>
  relatedList(alert).length > 0 || Boolean(diagnosisText(alert)) || contributors(alert).length > 0

// Ярлык переключателя: «Диагностика ▾» когда единственный контент — диагностика
// (эталон §5, без «Связано:»); иначе «Подробнее ▾».
const toggleLabel = (alert) => {
  if (expandedId.value === alert.id) return 'Свернуть ▴'
  const diagnosisOnly = !contextShort(alert) && diagnosisText(alert)
  return diagnosisOnly ? 'Диагностика ▾' : 'Подробнее ▾'
}

// Виновники в один абзац через « · » — только если оба имени короткие (≤25),
// иначе по строке на кампанию (§4).
const contributorsInline = (alert) => {
  const list = contributors(alert)
  return list.length > 0 && list.length <= 2 && list.every((c) => (c?.name || '').length <= 25)
}

const nearestHiddenDate = computed(() => {
  const dates = hiddenAlerts.value
    .map((a) => (a?.snoozed_until ? new Date(a.snoozed_until) : null))
    .filter((d) => d && !Number.isNaN(d.getTime()))
  if (!dates.length) return ''
  const min = new Date(Math.min(...dates.map((d) => d.getTime())))
  return min.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' })
})

const hiddenAuthorMeta = (alert) => {
  const who = alert?.snoozed_by_name || alert?.dismissed_by_name || alert?.hidden_by_name || ''
  if (alert?.not_problem_at || alert?.dismissed_at) {
    return who ? `${who} · не проблема` : 'не проблема'
  }
  if (alert?.snoozed_until) {
    const date = new Date(alert.snoozed_until).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' })
    return who ? `${who} · до ${date}` : `до ${date}`
  }
  return who || 'скрыто'
}

const toggleExpand = (id) => { expandedId.value = expandedId.value === id ? null : id }
const toggleSnooze = (id) => { openSnoozeId.value = openSnoozeId.value === id ? null : id }

const snooze = (alert, days) => { openSnoozeId.value = null; emit('snooze', alert, days) }
const notProblem = (alert) => { openSnoozeId.value = null; emit('not-problem', alert) }
</script>

<style scoped>
.detector-banner {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 0.95rem 1.1rem;
  border-radius: 1.05rem;
  font-family: Inter, sans-serif;
  transition: all 0.25s ease;
}

.detector-banner--warning { background: #fff8e8; border: 1px solid #f6d996; color: #8a5217; }
.detector-banner--problem { background: #fff1f1; border: 1px solid #ffb9b9; color: #9c2323; }
.detector-banner--warmup { background: #eff6ff; border: 1px solid #bfdbfe; color: #1e40af; }
.detector-banner--sync { background: #f4f6f9; border: 1px solid #dce3ed; color: #69758a; }

.detector-banner__head { display: flex; align-items: center; gap: 0.6rem; }
.detector-banner__head-ic {
  flex-shrink: 0;
  display: grid;
  place-items: center;
  width: 2rem;
  height: 2rem;
  border-radius: 0.7rem;
  background: rgba(255, 255, 255, 0.72);
}
.detector-banner__title { color: #1f2937; font-size: 0.98rem; font-weight: 900; line-height: 1.25; }
.detector-banner__text { display: flex; flex-direction: column; gap: 0.15rem; }
.detector-banner__hypothesis { color: currentColor; font-size: 0.84rem; font-weight: 650; opacity: 0.82; line-height: 1.35; }

/* ───── Блок-эпизод ───── */
.detector-blocks { display: flex; flex-direction: column; gap: 0.55rem; container-type: inline-size; }
.detector-block {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: flex-start;
  gap: 0.65rem;
  padding: 0.75rem 0.85rem;
  border-radius: 0.85rem;
  background: rgba(255, 255, 255, 0.72);
}
.detector-block--problem { --block-accent: #ef4444; }
.detector-block--warning { --block-accent: #f59e0b; }
.detector-block__dot {
  margin-top: 0.42rem;
  width: 0.55rem;
  height: 0.55rem;
  border-radius: 999px;
  background: var(--block-accent, #f59e0b);
  box-shadow: 0 0 0 0.22rem color-mix(in srgb, var(--block-accent, #f59e0b) 16%, transparent);
  flex-shrink: 0;
}
.detector-block__body { min-width: 0; display: flex; flex-direction: column; gap: 0.28rem; }
.detector-block__lead {
  margin: 0;
  color: #1f2937;
  font-size: 0.88rem;
  font-weight: 850;
  line-height: 1.4;
  overflow-wrap: anywhere;
}
.detector-block__related {
  margin: 0;
  color: #6b7280;
  font-size: 0.8rem;
  font-weight: 600;
  line-height: 1.4;
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.3rem;
}
.detector-block__related-label { font-weight: 800; flex-shrink: 0; }
/* §2: короткая строка не обрезается многоточием — при нехватке места
   переносится, переключатель прижат к концу текста. */
.detector-block__related-text {
  min-width: 0;
  overflow-wrap: anywhere;
}
.detector-block__more-link {
  flex-shrink: 0;
  border: 0;
  background: none;
  padding: 0;
  color: #2563eb;
  font-size: 0.8rem;
  font-weight: 800;
  cursor: pointer;
  white-space: nowrap;
}
.detector-block__more-link:hover { text-decoration: underline; }

/* ───── Развёрнутый контент (эталон §3): порядок связанные → диагностика → виновники ───── */
.detector-block__expanded {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  margin-top: 0.1rem;
}
.detector-block__exp-line {
  margin: 0;
  color: #4b5563;
  font-size: 0.8rem;
  font-weight: 600;
  line-height: 1.45;
  overflow-wrap: anywhere;
}
.detector-block__contrib { display: flex; flex-direction: column; gap: 0.15rem; }
.detector-block__contrib-label { font-weight: 800; color: #4b5563; }
.detector-block__contrib-label--own { margin: 0; font-size: 0.8rem; line-height: 1.45; }
.detector-block__contrib-item {
  margin: 0;
  color: #4b5563;
  font-size: 0.8rem;
  font-weight: 600;
  line-height: 1.45;
  overflow-wrap: anywhere;
}
/* §4: имя кампании можно переносить внутри, многоточие запрещено. */
.detector-block__contrib-name { font-weight: 700; word-break: break-word; }
.detector-block__contrib-more { color: #6b7280; font-style: italic; }

/* ───── Действия на блоке ───── */
.detector-block__actions { display: flex; align-items: center; gap: 0.35rem; }
.detector-block__actions button {
  border: 1px solid #e5e7eb;
  border-radius: 999px;
  min-height: 2.35rem;
  padding: 0.5rem 0.8rem;
  background: #fff;
  color: #374151;
  font-size: 0.8rem;
  font-weight: 850;
  cursor: pointer;
  white-space: nowrap;
}
.detector-block__actions button:hover { border-color: #bfdbfe; color: #2563eb; }
.detector-block__ai { color: #2563eb !important; }

.detector-block__snooze { position: relative; }
.detector-block__menu {
  position: absolute;
  top: calc(100% + 0.3rem);
  left: 0;
  z-index: 5;
  display: none;
  flex-direction: column;
  min-width: 8.5rem;
  padding: 0.3rem;
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 0.6rem;
  background: #fff;
  box-shadow: 0 0.7rem 1.8rem rgba(15, 23, 42, 0.16);
}
.detector-block__menu--right { left: auto; right: 0; }
.detector-block__snooze.open .detector-block__menu { display: flex; }
.detector-block__menu button {
  min-height: auto !important;
  border: 0 !important;
  border-radius: 0.4rem !important;
  padding: 0.5rem 0.6rem !important;
  background: transparent !important;
  color: #334155 !important;
  text-align: left;
  font-weight: 700;
}
.detector-block__menu button:hover { background: #f1f5f9 !important; }

/* ───── Скрытые: чип (состояние 1) и футер (состояние 2) ───── */
.detector-hidden-chip-wrap { position: relative; align-self: flex-start; }
.detector-hidden-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.5rem 0.85rem;
  border: 1px solid #e5e7eb;
  border-radius: 999px;
  background: #f6f7f9;
  color: #6b7280;
  font-size: 0.82rem;
  font-weight: 700;
  cursor: pointer;
}
.detector-hidden-chip:hover { background: #eef0f3; color: #374151; }
.detector-hidden-chip__dot { width: 0.5rem; height: 0.5rem; border-radius: 999px; background: #9ca3af; }

.detector-banner__hidden-foot { margin-top: 0.1rem; padding-top: 0.55rem; border-top: 1px solid rgba(15, 23, 42, 0.08); }
.detector-hidden-link {
  border: 0;
  background: none;
  padding: 0;
  color: #6b7280;
  font-size: 0.8rem;
  font-weight: 700;
  cursor: pointer;
}
.detector-hidden-link:hover { color: #374151; text-decoration: underline; }

.detector-hidden-list {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  margin-top: 0.55rem;
}
.detector-hidden-list--chip {
  position: absolute;
  top: calc(100% + 0.4rem);
  left: 0;
  z-index: 6;
  min-width: 22rem;
  max-width: 32rem;
  padding: 0.55rem;
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 0.7rem;
  background: #fff;
  box-shadow: 0 0.8rem 2rem rgba(15, 23, 42, 0.16);
}
.detector-hidden-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 0.5rem 0.9rem;
  padding: 0.5rem 0.6rem;
  border-radius: 0.55rem;
  background: rgba(15, 23, 42, 0.03);
  font-size: 0.8rem;
}
.detector-hidden-item__text { color: #374151; font-weight: 700; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.detector-hidden-item__meta { color: #9ca3af; font-weight: 650; white-space: nowrap; }
.detector-hidden-item button {
  border: 1px solid #e5e7eb;
  border-radius: 999px;
  padding: 0.4rem 0.7rem;
  background: #fff;
  color: #2563eb;
  font-size: 0.76rem;
  font-weight: 800;
  cursor: pointer;
  white-space: nowrap;
}
.detector-hidden-item button:hover { border-color: #bfdbfe; }

.detector-banner-enter-active, .detector-banner-leave-active { transition: all 0.25s ease; }
.detector-banner-enter-from, .detector-banner-leave-to { opacity: 0; transform: translateY(-0.35rem); }

/* §10: контентная ширина < ~680px — ряд кнопок целиком уходит под текст,
   влево, с отступом = ширина точки + gap (колонка текста в сетке). Кнопки
   не сжимаются, порядок сохраняется. */
@container (max-width: 680px) {
  .detector-block { grid-template-columns: auto minmax(0, 1fr); }
  .detector-block__actions {
    grid-column: 2 / 3;
    margin-top: 0.5rem;
    flex-wrap: wrap;
    justify-content: flex-start;
  }
}

@media (max-width: 760px) {
  .detector-hidden-list--chip { min-width: min(90vw, 22rem); }
  .detector-hidden-item { grid-template-columns: 1fr; gap: 0.25rem; }
}
</style>
