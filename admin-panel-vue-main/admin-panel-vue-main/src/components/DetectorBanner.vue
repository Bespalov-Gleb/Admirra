<template>
  <transition name="detector-banner">
    <!-- Зона внимания (§1): условный блок. Рендерится только при красных или
         непросмотренных (новое/изменилось). Пустой зоны не существует. -->
    <section v-if="zoneVisible" class="detector-banner" :class="`detector-banner--${bannerSeverity}`">
      <div class="detector-banner__head">
        <span class="detector-banner__head-ic" aria-hidden="true">
          <svg v-if="bannerSeverity === 'problem'" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="7.8" x2="12" y2="12.2"/><line x1="12" y1="16.2" x2="12.01" y2="16.2"/></svg>
          <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.3 4.1 2.1 18.1A2 2 0 0 0 3.8 21h16.4a2 2 0 0 0 1.7-2.9L13.7 4.1a2 2 0 0 0-3.4 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
        </span>
        <span class="detector-banner__title">{{ bannerTitle }}</span>
      </div>

      <div class="detector-blocks">
        <article
          v-for="alert in zoneFullAlerts"
          :key="alert.id"
          class="detector-block"
          :class="`detector-block--${alert.severity || 'warning'}`"
        >
          <span class="detector-block__dot"></span>
          <div class="detector-block__body">
            <!-- Пометка новизны на строке алерта (§1): новое / ухудшилось / стало лучше -->
            <span v-if="noveltyBadge(alert)" class="detector-block__novelty" :class="`detector-block__novelty--${alert.novelty}`">{{ noveltyBadge(alert) }}</span>

            <!-- Ведущая фраза: жирным только до двоеточия (§4) -->
            <p class="detector-block__lead">
              <b>{{ leadParts(alert).bold }}</b>{{ leadParts(alert).rest }}
            </p>

            <!-- Снимок «было → стало» для изменившихся (§9.4) -->
            <p v-if="changedLine(alert)" class="detector-block__changed">{{ changedLine(alert) }}</p>

          </div>

          <!-- Действия (§8): AI акцентная · Понятно и Скрыть с обводкой · Не проблема призрачная -->
          <div class="detector-block__actions">
            <button type="button" class="detector-block__ai" @click="$emit('ask-ai', alert)">Спросить AI</button>
            <button type="button" class="detector-block__ack" @click="$emit('acknowledge', alert)">Понятно</button>
            <span class="detector-block__snooze" :class="{ open: openSnoozeId === alert.id }">
              <button type="button" @click.stop="toggleSnooze(alert.id)">Скрыть…</button>
              <span class="detector-block__menu">
                <button type="button" @click="snooze(alert, 'week')">На неделю</button>
                <button v-if="periodEndLabel" type="button" @click="snooze(alert, 'period_end')">До конца периода ({{ periodEndLabel }})</button>
              </span>
            </span>
            <button
              type="button"
              class="detector-block__notproblem"
              title="Скроется до конца отклонения, поможет настроить детектор"
              @click="$emit('not-problem', alert)"
            >Не проблема</button>
          </div>

          <!-- Строка контекста (§4) — самостоятельный второй ряд всей карточки,
               а не часть текстовой колонки рядом с кнопками. -->
          <div
            v-if="hasContext(alert)"
            class="detector-block__context"
            :class="{ 'is-open': expandedId === alert.id }"
            role="button"
            tabindex="0"
            @click="toggleExpand(alert.id)"
            @keydown.enter.prevent="toggleExpand(alert.id)"
            @keydown.space.prevent="toggleExpand(alert.id)"
          >
            <div class="detector-block__context-body">
              <template v-if="expandedId !== alert.id">
                <p class="detector-block__context-short">
                  <span v-if="showRelatedPrefix(alert)" class="detector-block__related-label">Связано:</span>
                  <span class="detector-block__related-text">{{ contextShort(alert) }}</span>
                </p>
              </template>
              <template v-else>
                <p
                  v-for="(rel, i) in relatedList(alert)"
                  :key="`rel-${i}`"
                  class="detector-block__exp-line"
                >{{ rel.full }}</p>
                <p v-if="diagnosisText(alert)" class="detector-block__exp-line">{{ diagnosisText(alert) }}</p>
                <template v-if="contributors(alert).length">
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
                </template>
              </template>
            </div>
            <span class="detector-block__chevron" :class="{ 'is-open': expandedId === alert.id }" aria-hidden="true">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
            </span>
          </div>
        </article>
      </div>

      <!-- «Продолжается: N» (§1, §3): просмотренные жёлтые + погашенные «Понятно»
           красные — серой строкой в подвале зоны, без действий и громкости. -->
      <div v-if="continuedAlerts.length" class="detector-banner__continued">
        Продолжается: {{ continuedAlerts.length }} {{ declOtklon(continuedAlerts.length) }} — {{ continuedSummary }}
      </div>

      <!-- Футер скрытых внутри живой зоны -->
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

    <!-- Все громкие погашены, но есть скрытые — серый чип на позиции зоны -->
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
  // Детектор ит.4: дата прошлого захода и конец активного периода (для снуза).
  visibleFrom: { type: [String, Number, Date], default: null },
  activePeriodEnd: { type: [String, Number, Date], default: null },
})

const emit = defineEmits(['ask-ai', 'snooze', 'acknowledge', 'not-problem', 'restore'])

const expandedId = ref(null)
const openSnoozeId = ref(null)
const hiddenListOpen = ref(false)

const activeAlerts = computed(() => props.alerts || [])
const hiddenAlerts = computed(() => props.hiddenAlerts || [])

// §1: место на экране = уровень + новизна. Громкие (в зоне) — новое, изменилось,
// красное-ещё-не-погашено. Продолжающиеся (просмотренные) — серой строкой.
const ZONE_FULL = new Set(['new', 'worsened', 'improved', 'action_required'])
const zoneFullAlerts = computed(() => activeAlerts.value.filter((a) => ZONE_FULL.has(a.novelty)))
const continuedAlerts = computed(() => activeAlerts.value.filter((a) => a.novelty === 'known'))
// Любой активный красный держит зону — даже погашенный «Понятно» (уходит в
// «Продолжается», но верх экрана остаётся, приёмка §11).
const anyActiveRed = computed(() => activeAlerts.value.some((a) => a.severity === 'problem'))
const zoneVisible = computed(() => zoneFullAlerts.value.length > 0 || anyActiveRed.value)

const bannerSeverity = computed(() =>
  anyActiveRed.value || zoneFullAlerts.value.some((a) => a.severity === 'problem') ? 'problem' : 'warning'
)

const declOtklon = (n) => (n === 1 ? 'отклонение' : n > 1 && n < 5 ? 'отклонения' : 'отклонений')

const visibleFromLabel = computed(() => {
  if (!props.visibleFrom) return ''
  const d = new Date(props.visibleFrom)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' })
})

const periodEndLabel = computed(() => {
  if (!props.activePeriodEnd) return ''
  const d = new Date(props.activePeriodEnd)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' })
})

// Заголовок зоны (§3): приоритет красное-действие > изменилось > новое.
const bannerTitle = computed(() => {
  const full = zoneFullAlerts.value
  if (full.some((a) => a.novelty === 'action_required')) return 'Требует действия сегодня'
  if (full.some((a) => a.novelty === 'worsened' || a.novelty === 'improved')) return 'Изменилось с прошлого захода'
  if (full.some((a) => a.novelty === 'new')) return visibleFromLabel.value ? `Новое с ${visibleFromLabel.value}` : 'Новое'
  return 'Обнаружены отклонения'
})

const noveltyBadge = (alert) => {
  if (alert?.novelty === 'new') return 'новое'
  if (alert?.novelty === 'worsened') return 'ухудшилось'
  if (alert?.novelty === 'improved') return 'стало лучше'
  return ''
}

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

// Ведущая фраза = первая секция hypothesis_text (до первого «•»).
const leadPhrase = (alert) => {
  const text = String(alert?.hypothesis_text || '').replace(/\r/g, '').trim()
  if (!text) return 'Отклонение в показателях'
  const first = text.split(/\n\s*•\s*/)[0].replace(/^\s*•\s*/, '').trim()
  return first || text
}

// §4: жирным до двоеточия после названия цели; остальное обычным весом.
const leadParts = (alert) => {
  const text = leadPhrase(alert)
  const idx = text.indexOf(':')
  if (idx === -1) return { bold: text, rest: '' }
  return { bold: text.slice(0, idx + 1), rest: text.slice(idx + 1) }
}

const fmtRatio = (value) => {
  const n = Number(value)
  if (!Number.isFinite(n)) return ''
  return n.toLocaleString('ru-RU', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
}

// §9.4: «было в 1,3 раза, стало в 2,1» для изменившихся алертов.
const changedLine = (alert) => {
  if (!alert || (alert.novelty !== 'worsened' && alert.novelty !== 'improved')) return ''
  const was = fmtRatio(alert.was_ratio)
  const now = fmtRatio(alert.now_ratio)
  if (!was || !now) return ''
  return `Было в ${was} раза, стало в ${now}`
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
// сводка виновников «основной вклад — N кампаний».
const contextShort = (alert) => {
  const parts = relatedList(alert).map((r) => (r?.short || '').trim()).filter(Boolean)
  const diagnosis = diagnosisText(alert)
  if (diagnosis) parts.push(diagnosis)
  const count = contributorsCount(alert)
  if (count > 0) parts.push(`основной вклад — ${count} ${campaignsWord(count)}`)
  return parts.join(' · ')
}

// Число компонентов контекста — от него зависит префикс «Связано:» (§153).
const contextComponents = (alert) => {
  let n = relatedList(alert).length
  if (diagnosisText(alert)) n += 1
  if (contributorsCount(alert) > 0) n += 1
  return n
}
// §153: «Связано:» только при двух и более компонентах; при одном — фраза без него.
const showRelatedPrefix = (alert) => contextComponents(alert) >= 2

const hasContext = (alert) =>
  relatedList(alert).length > 0 || Boolean(diagnosisText(alert)) || contributors(alert).length > 0

// Виновники в один абзац — только если оба имени короткие (≤25), иначе по строке.
const contributorsInline = (alert) => {
  const list = contributors(alert)
  return list.length > 0 && list.length <= 2 && list.every((c) => (c?.name || '').length <= 25)
}

// «Продолжается: N — <ведущие фразы>» (§3): краткая сводка просмотренных.
const continuedSummary = computed(() =>
  continuedAlerts.value
    .map((a) => leadPhrase(a).split(':')[0].trim().toLowerCase())
    .filter(Boolean)
    .join(' · ')
)

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

const snooze = (alert, mode) => { openSnoozeId.value = null; emit('snooze', alert, { mode }) }
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
.detector-banner__title { color: #1f2937; font-size: 0.8rem; font-weight: 900; letter-spacing: 0.02em; text-transform: uppercase; line-height: 1.25; }
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

/* Пометка новизны — маленький капс-чип над ведущей фразой */
.detector-block__novelty {
  align-self: flex-start;
  display: inline-flex;
  align-items: center;
  padding: 0.08rem 0.44rem;
  border-radius: 999px;
  font-size: 0.66rem;
  font-weight: 800;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.detector-block__novelty--new { background: #dbeafe; color: #1d4ed8; }
.detector-block__novelty--worsened { background: #fee2e2; color: #b91c1c; }
.detector-block__novelty--improved { background: #dcfce7; color: #15803d; }

.detector-block__lead {
  margin: 0;
  color: #1f2937;
  font-size: 0.88rem;
  font-weight: 500;
  line-height: 1.4;
  overflow-wrap: anywhere;
}
.detector-block__lead b { font-weight: 850; }

.detector-block__changed {
  margin: 0;
  color: #4b5563;
  font-size: 0.8rem;
  font-weight: 650;
  line-height: 1.4;
}

/* ───── Строка контекста (§4): отдельный ряд с полоской и шевроном справа ───── */
.detector-block__context {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: flex-start;
  gap: 0.5rem;
  margin-top: 0.35rem;
  padding-top: 0.5rem;
  border-top: 1px solid rgba(15, 23, 42, 0.1);
  cursor: pointer;
  border-radius: 0 0 0.3rem 0.3rem;
}
.detector-block__context:hover { background: rgba(15, 23, 42, 0.02); }
.detector-block__context:focus-visible { outline: 2px solid #2563eb; outline-offset: 2px; }
.detector-block__context-body { min-width: 0; display: flex; flex-direction: column; gap: 0.3rem; }
.detector-block__context-short {
  margin: 0;
  color: #6b7280;
  font-size: 0.8rem;
  font-weight: 600;
  line-height: 1.5;
  overflow-wrap: anywhere;
}
.detector-block__related-label { font-weight: 800; margin-right: 0.28rem; }
.detector-block__related-text { overflow-wrap: anywhere; }
/* Шеврон прижат к верху ряда (§4): при трёх строках не уплывает в середину. */
.detector-block__chevron {
  align-self: flex-start;
  margin-top: 0.05rem;
  display: grid;
  place-items: center;
  width: 1.35rem;
  height: 1.35rem;
  border-radius: 0.4rem;
  color: #2563eb;
  transition: transform 0.18s ease, background 0.15s ease;
}
.detector-block__context:hover .detector-block__chevron { background: rgba(37, 99, 235, 0.1); }
.detector-block__chevron.is-open { transform: rotate(180deg); }

.detector-block__exp-line {
  margin: 0;
  color: #4b5563;
  font-size: 0.8rem;
  font-weight: 600;
  line-height: 1.45;
  overflow-wrap: anywhere;
}
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
.detector-block__contrib-name { font-weight: 700; word-break: break-word; }
.detector-block__contrib-more { color: #6b7280; font-style: italic; }

/* ───── Действия на блоке (§8) ───── */
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
/* AI — единственная акцентная кнопка */
.detector-block__ai {
  border-color: #2563eb !important;
  background: #2563eb !important;
  color: #fff !important;
}
.detector-block__ai:hover { border-color: #1d4ed8 !important; background: #1d4ed8 !important; color: #fff !important; }
/* «Не проблема» — призрачная: без обводки, приглушённая */
.detector-block__notproblem {
  border-color: transparent !important;
  background: transparent !important;
  color: #9ca3af !important;
  font-weight: 700 !important;
}
.detector-block__notproblem:hover { color: #6b7280 !important; background: rgba(15, 23, 42, 0.04) !important; }

.detector-block__snooze { position: relative; }
.detector-block__menu {
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

/* ───── «Продолжается» (§3): серая строка в подвале зоны ───── */
.detector-banner__continued {
  margin-top: 0.1rem;
  padding-top: 0.5rem;
  border-top: 1px solid rgba(15, 23, 42, 0.08);
  color: #6b7280;
  font-size: 0.8rem;
  font-weight: 650;
  line-height: 1.4;
}

/* ───── Скрытые: чип и футер ───── */
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

/* §10: узкая ширина — ряд кнопок уходит под текст */
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
