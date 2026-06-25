<template>
  <div class="dyn">
    <!-- Контролы: гранулярность + горизонт -->
    <div class="dyn-controls">
      <div class="dyn-controls__row">
        <div class="dyn-controls__left">
          <div class="dyn-control-group">
            <span class="dyn-control-label">Период</span>
            <div class="dyn-seg" role="tablist" aria-label="Гранулярность">
              <button
                v-for="g in granularities"
                :key="g.value"
                type="button"
                class="dyn-seg__btn"
                :class="{ 'dyn-seg__btn--active': granularity === g.value }"
                @click="setGranularity(g.value)"
              >{{ g.label }}</button>
            </div>
          </div>
          <div class="dyn-control-group">
            <span class="dyn-control-label">Горизонт</span>
            <div class="dyn-seg" role="tablist" aria-label="Горизонт">
              <button
                v-for="h in horizons"
                :key="h.value"
                type="button"
                class="dyn-seg__btn"
                :class="{ 'dyn-seg__btn--active': horizon === h.value }"
                @click="setHorizon(h.value)"
              >{{ h.label }}</button>
            </div>
          </div>
        </div>

        <div class="dyn-controls__right">
          <button
            type="button"
            class="dyn-backfill__btn"
            :class="{ 'dyn-backfill__btn--busy': backfillBusy }"
            :disabled="backfillBusy || backfill.in_cooldown || !clientId"
            @click="startBackfill"
          >
            <span v-if="backfillBusy" class="dyn-backfill__spinner" aria-hidden="true"></span>
            {{ backfillLabel }}
          </button>

          <div class="dyn-export" :class="{ 'dyn-export--open': exportOpen }">
            <button
              type="button"
              class="dyn-export__btn"
              :disabled="!periods.length"
              @click="exportOpen = !exportOpen"
            >
              Экспорт динамики
              <span class="dyn-export__chev">▾</span>
            </button>
            <div v-if="exportOpen" class="dyn-export__menu">
              <button type="button" @click="doExport('csv')">CSV</button>
              <button type="button" @click="doExport('xlsx')">XLSX</button>
              <button type="button" @click="doExport('png')">PNG (изображение)</button>
            </div>
          </div>
        </div>
      </div>

      <div v-if="backfillHint" class="dyn-controls__status">
        <span class="dyn-controls__status-dot"></span>
        <span>{{ backfillHint }}</span>
      </div>
    </div>

    <div ref="dynExportRef" class="dyn-capture">
    <!-- График -->
    <section class="panel dyn-chart-panel">
      <div class="dyn-chart-head">
        <h2>Динамика</h2>
        <div class="dyn-metric-chips">
          <button
            v-for="m in metrics"
            :key="m.key"
            type="button"
            class="dyn-metric-chip"
            :class="{ 'dyn-metric-chip--active': metric === m.key }"
            @click="metric = m.key"
          >
            <span class="dyn-metric-dot" :style="{ background: m.color }"></span>
            {{ m.label }}
          </button>
        </div>
      </div>

      <div v-if="loading" class="dyn-empty">Загрузка…</div>
      <div v-else-if="!periods.length" class="dyn-empty">
        Накапливаем данные — динамика появится по мере истории.
      </div>
      <template v-else>
        <div ref="dynChartWrapRef" class="dyn-chart-wrap" @mouseleave="hideBarTooltip">
          <svg class="dyn-chart" :viewBox="`0 0 ${CW} ${CH}`" role="img" aria-label="График динамики">
            <defs>
              <pattern :id="hatchId" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
                <rect width="6" height="6" :fill="activeColor" opacity="0.18" />
                <line x1="0" y1="0" x2="0" y2="6" :stroke="activeColor" stroke-width="2" opacity="0.6" />
              </pattern>
            </defs>
            <g v-for="(p, i) in periods" :key="p.start">
              <rect
                :x="barX(i)" :y="barY(i)" :width="barW" :height="barH(i)"
                rx="3"
                class="dyn-bar-rect"
                :fill="p.incomplete ? `url(#${hatchId})` : activeColor"
                :stroke="p.incomplete ? activeColor : 'none'"
                :stroke-dasharray="p.incomplete ? '3 3' : '0'"
                @mouseenter="showBarTooltip($event, p)"
                @mousemove="showBarTooltip($event, p)"
                @focus="showBarTooltip($event, p)"
                @blur="hideBarTooltip"
              />
              <text
                v-if="shouldShowAxisLabel(i)"
                :x="barX(i) + barW / 2"
                :y="CH - 6"
                text-anchor="middle"
                class="dyn-bar-label"
                :class="{ 'dyn-bar-label--dense': periods.length > 12 }"
              >
                {{ shortAxisLabel(p.label) }}
              </text>
              <text
                v-if="shouldShowValueLabel(i)"
                :x="barX(i) + barW / 2"
                :y="barY(i) - 4"
                text-anchor="middle"
                class="dyn-bar-value"
                :class="{ 'dyn-bar-value--dense': periods.length > 8 }"
              >
                {{ fmtMetricCompact(metricValue(p)) }}
              </text>
            </g>
          </svg>
          <div
            v-if="barTooltip"
            class="dyn-bar-tooltip"
            :style="{ left: `${barTooltip.x}px`, top: `${barTooltip.y}px` }"
          >
            <span>{{ barTooltip.period }}</span>
            <strong>{{ activeMetricLabel }}: {{ barTooltip.value }}</strong>
          </div>
        </div>
        <div class="dyn-chart-note">
          <span class="dyn-metric-dot" :style="{ background: activeColor }"></span>
          Цвет столбцов — по выбранной метрике. Штриховка — неполный (текущий) период.
        </div>
      </template>
    </section>

    <!-- Таблица периодов -->
    <section v-if="periods.length" class="panel dyn-table-panel">
      <div class="dyn-table-head">
        <div>
          <h2>История по периодам</h2>
          <p>Значения и динамика к предыдущему периоду</p>
        </div>
      </div>
      <div class="dyn-table-wrap">
        <table class="dyn-table">
          <thead>
            <tr>
              <th class="dyn-th-sticky">Период</th>
              <th>Расход</th>
              <th>Показы</th>
              <th>Клики</th>
              <th>CTR</th>
              <th>CPC</th>
              <th v-if="hasYandexSummary" class="dyn-th-group">Конверсии Я</th>
              <th v-if="hasYandexSummary">CPL Я</th>
              <template v-for="g in goals" :key="g.id">
                <th class="dyn-th-goal">{{ g.name }}</th>
                <th class="dyn-th-goal">{{ g.name }} CPA</th>
              </template>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in periods" :key="p.start" :class="{ 'dyn-row--incomplete': p.incomplete }">
              <td class="dyn-td-sticky">
                {{ p.label }}
                <em v-if="p.incomplete" class="dyn-incomplete-badge">неполный</em>
              </td>
              <td v-html="cell(adjCost(p), p.deltas.cost, 'volume', 'money')"></td>
              <td v-html="cell(p.impressions, p.deltas.impressions, 'volume', 'int')"></td>
              <td v-html="cell(p.clicks, p.deltas.clicks, 'volume', 'int')"></td>
              <td v-html="cell(p.ctr, p.deltas.ctr, 'conv', 'pct')"></td>
              <td v-html="cell(adjCpc(p), p.deltas.cpc, 'rate', 'money')"></td>
              <td v-if="hasYandexSummary" v-html="cell(p.yandex_summary && p.yandex_summary.conversions, deltaOf(p,'ys_conv'), 'conv', 'int')"></td>
              <td v-if="hasYandexSummary" v-html="cell(adjCpl(p), deltaOf(p,'ys_cpl'), 'rate', 'money')"></td>
              <template v-for="g in goals" :key="g.id">
                <td class="dyn-td-goal" v-html="goalCountCell(p, g.id)"></td>
                <td class="dyn-td-goal" v-html="goalCpaCell(p, g.id)"></td>
              </template>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import api from '@/api/axios'
import html2canvas from 'html2canvas'

const props = defineProps({
  clientId: { type: String, default: '' },
  channel: { type: String, default: 'all' },     // platform: all|yandex|vk|avito
  campaignIds: { type: Array, default: () => [] }, // фильтр направления
  includeVat: { type: Boolean, default: true },
})

const VAT = 1.22
const granularities = [
  { value: 'month', label: 'Месяцы' },
  { value: 'week', label: 'Недели' },
]
const horizons = [
  { value: 1, label: '1 мес' },
  { value: 3, label: '3 мес' },
  { value: 6, label: '6 мес' },
  { value: 12, label: '12 мес' },
]
const metrics = [
  { key: 'cost', label: 'Расход', color: '#2563eb', money: true },
  { key: 'impressions', label: 'Показы', color: '#f59e0b', money: false },
  { key: 'clicks', label: 'Клики', color: '#38bdf8', money: false },
  { key: 'cpc', label: 'CPC', color: '#8b5cf6', money: true },
  { key: 'cpl', label: 'CPL', color: '#f97373', money: true },
  { key: 'leads', label: 'Конверсии', color: '#22c55e', money: false },
]

const granularity = ref('month')
const horizon = ref(3)
const metric = ref('cost')
const loading = ref(false)
const periods = ref([])
const goals = ref([])
const meta = ref({ history_from: null, requested_from: null, needs_backfill: false, suggested_granularity: null })
const userTouchedGranularity = ref(false)
const dynChartWrapRef = ref(null)
const barTooltip = ref(null)

const activeColor = computed(() => (metrics.find((m) => m.key === metric.value) || metrics[0]).color)
const activeMetricLabel = computed(() => (metrics.find((m) => m.key === metric.value) || metrics[0]).label)
const hatchId = 'dyn-hatch'
const hasYandexSummary = computed(() => periods.value.some((p) => p.yandex_summary))

// ── НДС (как на дашборде): Яндекс/VK +22%, Авито уже с НДС ──
const withCostVat = (cbp, raw) => {
  if (!cbp) return Number(raw || 0)
  const y = Number(cbp.yandex || 0), v = Number(cbp.vk || 0), a = Number(cbp.avito || 0)
  return props.includeVat ? (y * VAT + v * VAT + a) : (y + v + a / VAT)
}
const adjCost = (p) => withCostVat(p.cost_by_platform, p.cost)
const adjCpc = (p) => (p.clicks > 0 ? adjCost(p) / p.clicks : 0)
const adjOverallCpl = (p) => {
  const leads = Number(p.leads || 0)
  return leads > 0 ? adjCost(p) / leads : 0
}
// Яндекс отдаёт расход без НДС → при НДС-режиме ×1.22, без НДС остаётся как есть.
const adjCpl = (p) => {
  const cpl = p.yandex_summary && p.yandex_summary.cpl
  if (cpl === null || cpl === undefined) return null
  return Number(cpl) * (props.includeVat ? VAT : 1)
}
const goalCpa = (p, count) => (count > 0 ? adjCost(p) / count : null)

// ── График ──
const CW = 1000, CH = 320, PAD_TOP = 30, PAD_BOTTOM = 22
const metricValue = (p) => {
  if (metric.value === 'cost') return adjCost(p)
  if (metric.value === 'cpc') return adjCpc(p)
  if (metric.value === 'cpl') return adjOverallCpl(p)
  return Number(p[metric.value] || 0)
}
const maxVal = computed(() => Math.max(1, ...periods.value.map(metricValue)))
const barW = computed(() => {
  const n = periods.value.length || 1
  return (CW / n) * 0.6
})
const barGap = computed(() => (CW / (periods.value.length || 1)))
const barX = (i) => barGap.value * i + (barGap.value - barW.value) / 2
const barH = (i) => {
  const v = metricValue(periods.value[i])
  return Math.max(2, (v / maxVal.value) * (CH - PAD_TOP - PAD_BOTTOM))
}
const barY = (i) => CH - PAD_BOTTOM - barH(i)
const axisLabelStep = computed(() => {
  const n = periods.value.length
  if (n <= 6) return 1
  if (n <= 12) return 2
  if (n <= 20) return 3
  if (n <= 32) return 4
  return Math.ceil(n / 7)
})
const valueLabelStep = computed(() => {
  const n = periods.value.length
  if (n <= 6) return 1
  if (n <= 12) return 2
  if (n <= 24) return 4
  return Math.ceil(n / 6)
})
const shouldShowAxisLabel = (index) => {
  const n = periods.value.length
  if (!n) return false
  return index === 0 || index === n - 1 || index % axisLabelStep.value === 0
}
const shouldShowValueLabel = (index) => {
  const n = periods.value.length
  if (!n) return false
  return index === 0 || index === n - 1 || index % valueLabelStep.value === 0
}
const showBarTooltip = (event, period) => {
  const wrap = dynChartWrapRef.value
  if (!wrap || !period) return
  const rect = wrap.getBoundingClientRect()
  const rawX = event.clientX - rect.left + 14
  const rawY = event.clientY - rect.top - 56
  const x = Math.max(12, Math.min(rawX, rect.width - 210))
  const y = Math.max(12, rawY)
  barTooltip.value = {
    x,
    y,
    period: period.label,
    value: fmtMetric(metricValue(period)),
  }
}
const hideBarTooltip = () => {
  barTooltip.value = null
}

// ── Форматирование ──
const nf = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 })
const nf2 = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 2 })
const nfCompact = new Intl.NumberFormat('ru-RU', { notation: 'compact', maximumFractionDigits: 1 })
const fmtMoney = (v) => `${nf2.format(Number(v || 0))} ₽`
const fmtInt = (v) => nf.format(Number(v || 0))
const fmtPct = (v) => `${nf2.format(Number(v || 0))}%`
const fmtMetric = (v) => {
  const m = metrics.find((x) => x.key === metric.value)
  return m && m.money ? fmtMoney(v) : fmtInt(v)
}
const fmtCompact = (v) => {
  const num = Number(v || 0)
  return Math.abs(num) >= 10000 ? nfCompact.format(num) : nf.format(num)
}
const fmtMetricCompact = (v) => {
  const m = metrics.find((x) => x.key === metric.value)
  return m && m.money ? `${fmtCompact(v)} ₽` : fmtCompact(v)
}
const shortAxisLabel = (label) => {
  // «Июнь 2026» → «Июнь», недельный диапазон оставляем
  const parts = String(label).split(' ')
  return parts.length === 2 ? parts[0] : label
}

// ── Ячейка значение + дельта-чип ──
// kind: volume (серая дельта) | rate (CPC/CPL: вниз=хорошо) | conv (вверх=хорошо)
const fmtVal = (v, fmt) => {
  if (v === null || v === undefined) return '—'
  if (fmt === 'money') return fmtMoney(v)
  if (fmt === 'pct') return fmtPct(v)
  return fmtInt(v)
}
const deltaChip = (delta, kind) => {
  if (delta === null || delta === undefined) return ''
  const up = delta >= 0
  const arrow = up ? '▲' : '▼'
  let cls = 'dyn-delta--neutral'
  if (kind === 'rate') cls = up ? 'dyn-delta--bad' : 'dyn-delta--good'
  else if (kind === 'conv') cls = up ? 'dyn-delta--good' : 'dyn-delta--bad'
  const sign = up ? '+' : ''
  return `<span class="dyn-delta ${cls}">${arrow}${sign}${nf2.format(delta)}%</span>`
}
const cell = (value, delta, kind, fmt) => `<span class="dyn-cellval">${fmtVal(value, fmt)}</span>${deltaChip(delta, kind)}`

const deltaOf = (p, key) => {
  // дельты сводной Яндекса считаем на лету (бэк отдаёт по основным метрикам)
  const idx = periods.value.indexOf(p)
  if (idx <= 0) return null
  const prev = periods.value[idx - 1]
  const curr = p.yandex_summary
  const pr = prev.yandex_summary
  if (!curr || !pr) return null
  const a = key === 'ys_conv' ? curr.conversions : curr.cpl
  const b = key === 'ys_conv' ? pr.conversions : pr.cpl
  if (!b) return null
  return Math.round((Number(a || 0) - Number(b || 0)) / Number(b) * 1000) / 10
}

const goalCountCell = (p, gid) => {
  const g = (p.goals || {})[gid]
  if (!g) return '<span class="dyn-cellval">—</span>'
  const gd = (p.goal_deltas || {})[gid] || {}
  return `<span class="dyn-cellval">${fmtInt(g.count)}</span>${deltaChip(gd.count, 'conv')}`
}

const goalCpaCell = (p, gid) => {
  const g = (p.goals || {})[gid]
  if (!g) return '<span class="dyn-cellval">—</span>'
  const gd = (p.goal_deltas || {})[gid] || {}
  const cpaVal = goalCpa(p, g.count)
  return cpaVal != null
    ? `<span class="dyn-cellval">${fmtMoney(cpaVal)}</span>${deltaChip(gd.cpa, 'rate')}`
    : '<span class="dyn-cellval">—</span>'
}

// ── Загрузка ──
const horizonDates = () => {
  const end = new Date()
  const start = new Date()
  start.setMonth(start.getMonth() - horizon.value)
  const iso = (d) => d.toISOString().slice(0, 10)
  return { start: iso(start), end: iso(end) }
}
const fetchSeries = async () => {
  if (!props.clientId) { periods.value = []; goals.value = []; return }
  loading.value = true
  try {
    const { start, end } = horizonDates()
    const params = {
      client_id: props.clientId,
      platform: props.channel || 'all',
      granularity: granularity.value,
      start_date: start,
      end_date: end,
    }
    if (props.campaignIds && props.campaignIds.length) params.campaign_ids = props.campaignIds
    const { data } = await api.get('dashboard/dynamics-series', { params })
    periods.value = Array.isArray(data?.periods) ? data.periods : []
    goals.value = Array.isArray(data?.goals) ? data.goals : []
    meta.value = {
      history_from: data?.history_from || null,
      requested_from: data?.requested_from || start,
      needs_backfill: Boolean(data?.needs_backfill),
      suggested_granularity: data?.suggested_granularity || null,
    }
    if (!userTouchedGranularity.value && data?.suggested_granularity && data.suggested_granularity !== granularity.value) {
      granularity.value = data.suggested_granularity
      await fetchSeries()
    }
  } catch (e) {
    periods.value = []; goals.value = []
  } finally {
    loading.value = false
  }
}
const setGranularity = (g) => { userTouchedGranularity.value = true; granularity.value = g; fetchSeries() }
const setHorizon = (h) => { horizon.value = h; fetchSeries() }

// ── Бэкафилл истории (Phase 2) ──
const backfill = ref({ status: 'idle', running: false, progress: 0, in_cooldown: false, history_from: null, message: null })
let backfillTimer = null

const fmtDate = (iso) => {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString('ru-RU', { day: '2-digit', month: 'short', year: 'numeric' })
}
const backfillBusy = computed(() => backfill.value.running)
const backfillLabel = computed(() => {
  const b = backfill.value
  if (b.running) return `Загрузка истории… ${b.progress || 0}%`
  if (b.in_cooldown) return 'История обновлена'
  return 'Загрузить историю за 12 мес'
})
const backfillHint = computed(() => {
  const b = backfill.value
  if (b.running && b.message) return b.message
  if (meta.value.needs_backfill && meta.value.history_from) {
    return `Данные до ${fmtDate(meta.value.history_from)} не загружены. Нажмите «Загрузить историю», чтобы догрузить период.`
  }
  if (b.history_from) return `Данные в системе с ${fmtDate(b.history_from)}`
  if (meta.value.history_from) return `Данные в системе с ${fmtDate(meta.value.history_from)}`
  return ''
})

const fetchBackfillStatus = async () => {
  if (!props.clientId) return
  try {
    const { data } = await api.get('dashboard/dynamics/backfill-status', { params: { client_id: props.clientId } })
    backfill.value = data || backfill.value
    if (backfill.value.running) {
      ensureBackfillPolling()
    } else {
      stopBackfillPolling()
    }
  } catch (e) { /* нет статуса — не критично */ }
}
const ensureBackfillPolling = () => {
  if (backfillTimer) return
  backfillTimer = setInterval(async () => {
    const wasRunning = backfill.value.running
    await fetchBackfillStatus()
    // прогон завершился — подтянуть свежий ряд
    if (wasRunning && !backfill.value.running) fetchSeries()
  }, 8000)
}
const stopBackfillPolling = () => {
  if (backfillTimer) { clearInterval(backfillTimer); backfillTimer = null }
}
const startBackfill = async () => {
  if (!props.clientId || backfill.value.running || backfill.value.in_cooldown) return
  try {
    const { data } = await api.post('dashboard/dynamics/backfill', null, { params: { client_id: props.clientId } })
    if (data && data.started === false && data.reason === 'cooldown') {
      backfill.value = { ...backfill.value, in_cooldown: true, cooldown_until: data.cooldown_until }
      return
    }
    backfill.value = { ...backfill.value, ...(data || {}), running: true, status: 'running' }
    ensureBackfillPolling()
  } catch (e) { /* запуск не удался — оставляем как есть */ }
}

// ── Экспорт динамики (Phase 3): CSV/XLSX через бэк, PNG — снимок экрана ──
const exportOpen = ref(false)
const dynExportRef = ref(null)

const exportFilename = () => {
  const { start, end } = horizonDates()
  return `dynamics_${start}_${end}`
}
const triggerDownload = (blob, name) => {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = name
  document.body.appendChild(a); a.click(); a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
const exportPng = async () => {
  if (!dynExportRef.value) return
  const canvas = await html2canvas(dynExportRef.value, { backgroundColor: '#ffffff', scale: 2, useCORS: true })
  canvas.toBlob((blob) => { if (blob) triggerDownload(blob, `${exportFilename()}.png`) })
}
const doExport = async (fmt) => {
  exportOpen.value = false
  try {
    if (fmt === 'png') { await exportPng(); return }
    const { start, end } = horizonDates()
    const params = {
      client_id: props.clientId,
      platform: props.channel || 'all',
      granularity: granularity.value,
      start_date: start,
      end_date: end,
      fmt,
      include_vat: props.includeVat,
    }
    if (props.campaignIds && props.campaignIds.length) params.campaign_ids = props.campaignIds
    const resp = await api.get('dashboard/dynamics/export', { params, responseType: 'blob' })
    triggerDownload(resp.data, `${exportFilename()}.${fmt === 'xlsx' ? 'xlsx' : 'csv'}`)
  } catch (e) { /* экспорт не удался — молча */ }
}
const onDocMousedown = (e) => {
  if (exportOpen.value && e.target && !e.target.closest('.dyn-export')) exportOpen.value = false
}

watch(() => props.clientId, () => { userTouchedGranularity.value = false })
watch(() => [props.clientId, props.channel, props.campaignIds], () => { fetchSeries(); fetchBackfillStatus() }, { deep: true })
onMounted(() => { fetchSeries(); fetchBackfillStatus(); document.addEventListener('mousedown', onDocMousedown) })
onUnmounted(() => { stopBackfillPolling(); document.removeEventListener('mousedown', onDocMousedown) })
</script>

<style scoped>
.dyn {
  display: flex;
  flex-direction: column;
  gap: 1.65rem;
  margin-top: 1.25rem;
}

.dyn-controls {
  display: grid;
  gap: 0.85rem;
  padding: 1.25rem 1.35rem 1.15rem;
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 1.35rem;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(250, 252, 255, 0.9)),
    #fff;
  box-shadow: 0 0.75rem 1.9rem rgba(15, 23, 42, 0.045);
}

.dyn-controls__row {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 1.35rem;
  flex-wrap: wrap;
}

.dyn-controls__left {
  display: flex;
  align-items: end;
  gap: 1.25rem;
  flex-wrap: wrap;
  min-width: 0;
}

.dyn-control-group {
  display: grid;
  gap: 0.58rem;
  min-width: 0;
}

.dyn-control-label {
  padding-left: 0.2rem;
  color: #9aa3b2;
  font-size: 0.78rem;
  font-weight: 800;
  line-height: 1;
  text-transform: uppercase;
  letter-spacing: 0;
}

.dyn-seg {
  display: inline-flex;
  gap: 0.28rem;
  padding: 0.32rem;
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 999px;
  background: rgba(244, 247, 251, 0.92);
}

.dyn-seg__btn {
  min-height: 2.35rem;
  padding: 0 1rem;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: #8d95a5;
  font-size: 0.92rem;
  font-weight: 800;
  cursor: pointer;
  transition: background 0.18s ease, color 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease;
}

.dyn-seg__btn:hover {
  color: #2563eb;
}

.dyn-seg__btn--active {
  background: #fff;
  color: #2563eb;
  box-shadow: 0 0.35rem 0.95rem rgba(37, 99, 235, 0.12);
}

.dyn-controls__right {
  display: inline-flex;
  align-items: end;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-left: auto;
  flex-wrap: wrap;
}

.dyn-controls__status {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  min-height: 1.35rem;
  padding-left: 0.2rem;
  color: #9aa3b2;
  font-size: 0.84rem;
  font-weight: 700;
  line-height: 1.3;
}

.dyn-controls__status-dot {
  width: 0.42rem;
  height: 0.42rem;
  border-radius: 999px;
  background: #8fb3ff;
  box-shadow: 0 0 0 0.22rem rgba(37, 99, 235, 0.09);
  flex: 0 0 auto;
}

.dyn-capture {
  display: flex;
  flex-direction: column;
  gap: 1.65rem;
}

.dyn-export {
  position: relative;
}

.dyn-export__btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  min-height: 2.95rem;
  padding: 0 1.28rem;
  border: 1px solid rgba(148, 163, 184, 0.26);
  border-radius: 999px;
  background: #fff;
  color: #172033;
  font-size: 0.92rem;
  font-weight: 800;
  cursor: pointer;
  box-shadow: 0 0.35rem 1rem rgba(15, 23, 42, 0.045);
  transition: background 0.16s ease, border-color 0.16s ease, box-shadow 0.16s ease, color 0.16s ease;
}

.dyn-export__btn:hover:not(:disabled) {
  border-color: rgba(37, 99, 235, 0.24);
  background: rgba(37, 99, 235, 0.04);
  color: #2563eb;
}

.dyn-export__btn:disabled {
  opacity: 0.5;
  cursor: default;
}

.dyn-export__chev {
  font-size: 0.8rem;
  color: #8d95a5;
  transition: transform 0.16s ease;
}

.dyn-export--open .dyn-export__chev {
  transform: rotate(180deg);
}

.dyn-export__menu {
  position: absolute;
  top: calc(100% + 0.55rem);
  right: 0;
  z-index: 20;
  min-width: 14rem;
  display: flex;
  flex-direction: column;
  padding: 0.42rem;
  border-radius: 0.95rem;
  background: #fff;
  box-shadow: 0 1rem 2.4rem rgba(15, 23, 42, 0.16);
  border: 1px solid rgba(148, 163, 184, 0.16);
}

.dyn-export__menu button {
  text-align: left;
  min-height: 2.55rem;
  padding: 0 0.9rem;
  border: 0;
  border-radius: 0.65rem;
  background: transparent;
  color: #172033;
  font-size: 0.92rem;
  font-weight: 700;
  cursor: pointer;
}

.dyn-export__menu button:hover {
  background: rgba(37, 99, 235, 0.08);
  color: #2563eb;
}

.dyn-backfill__btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.55rem;
  min-height: 2.95rem;
  padding: 0 1.28rem;
  border: 1px solid rgba(37, 99, 235, 0.26);
  border-radius: 999px;
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.08), rgba(20, 184, 166, 0.08));
  color: #2563eb;
  font-size: 0.92rem;
  font-weight: 800;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.16s ease, opacity 0.16s ease, border-color 0.16s ease, box-shadow 0.16s ease;
}

.dyn-backfill__btn:hover:not(:disabled) {
  border-color: rgba(37, 99, 235, 0.38);
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.12), rgba(20, 184, 166, 0.12));
  box-shadow: 0 0.45rem 1.1rem rgba(37, 99, 235, 0.12);
}

.dyn-backfill__btn:disabled {
  opacity: 0.55;
  cursor: default;
}

.dyn-backfill__btn--busy {
  color: #64748b;
}
.dyn-backfill__spinner {
  width: 1.1rem; height: 1.1rem; border-radius: 999px;
  border: 2px solid rgba(37, 99, 235, 0.25); border-top-color: #2563eb;
  animation: dyn-spin 0.8s linear infinite;
}
@keyframes dyn-spin { to { transform: rotate(360deg); } }

.panel {
  background: #fff;
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 1.45rem;
  padding: 1.85rem 2rem;
  box-shadow: 0 0.9rem 2rem rgba(15, 23, 42, 0.035);
}

.dyn-chart-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1.35rem;
  flex-wrap: wrap;
  margin-bottom: 1.35rem;
}

.dyn-chart-head h2,
.dyn-table-head h2 {
  margin: 0;
  font-size: 1.38rem;
  font-weight: 900;
  color: #172033;
}

.dyn-table-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
}

.dyn-table-head p {
  margin: 0.32rem 0 0;
  color: #9aa3b2;
  font-size: 0.94rem;
  font-weight: 700;
}

.dyn-metric-chips {
  display: inline-flex;
  gap: 0.45rem;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.dyn-metric-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  min-height: 2.35rem;
  padding: 0 0.9rem;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 999px;
  background: #fff;
  color: #64748b;
  font-size: 0.9rem;
  font-weight: 800;
  cursor: pointer;
  transition: border-color 0.16s ease, background 0.16s ease, color 0.16s ease, box-shadow 0.16s ease;
}

.dyn-metric-chip:hover {
  border-color: rgba(37, 99, 235, 0.24);
  color: #2563eb;
}

.dyn-metric-chip--active {
  border-color: transparent;
  background: rgba(37, 99, 235, 0.08);
  color: #172033;
  box-shadow: 0 0.25rem 0.8rem rgba(37, 99, 235, 0.1);
}
.dyn-metric-dot { width: 0.7rem; height: 0.7rem; border-radius: 999px; flex: 0 0 auto; }

.dyn-chart-wrap {
  position: relative;
}

.dyn-chart { width: 100%; height: auto; aspect-ratio: 1000 / 320; display: block; overflow: visible; }
.dyn-bar-rect {
  cursor: default;
  transition: opacity 0.16s ease, filter 0.16s ease;
}
.dyn-bar-rect:hover {
  filter: brightness(1.04);
  opacity: 0.92;
}
.dyn-bar-label { font-size: 11px; fill: #9aa3b2; font-weight: 700; }
.dyn-bar-label--dense { font-size: 10px; }
.dyn-bar-value { font-size: 10px; fill: #64748b; font-weight: 800; }
.dyn-bar-value--dense { font-size: 9px; }
.dyn-bar-tooltip {
  position: absolute;
  z-index: 8;
  min-width: 12rem;
  max-width: 14rem;
  padding: 0.7rem 0.82rem;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 0.9rem;
  background: rgba(255, 255, 255, 0.97);
  box-shadow: 0 1rem 2.2rem rgba(15, 23, 42, 0.14);
  pointer-events: none;
}
.dyn-bar-tooltip span {
  display: block;
  margin-bottom: 0.28rem;
  color: #8d95a5;
  font-size: 0.78rem;
  font-weight: 800;
  line-height: 1.2;
}
.dyn-bar-tooltip strong {
  display: block;
  color: #172033;
  font-size: 0.96rem;
  font-weight: 900;
  line-height: 1.2;
}
.dyn-chart-note {
  margin-top: 0.9rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #9aa3b2;
  font-size: 0.86rem;
  font-weight: 700;
}
.dyn-empty { padding: 4rem 0; text-align: center; color: #9aa3b2; font-size: 1rem; font-weight: 600; }

.dyn-table-wrap {
  overflow-x: auto;
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 1rem;
  background: #fff;
}

.dyn-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 1rem;
}

.dyn-table th,
.dyn-table td {
  padding: 0.9rem 1rem;
  text-align: left;
  white-space: nowrap;
}

.dyn-table thead th {
  color: #8d95a5;
  font-weight: 800;
  font-size: 0.86rem;
  background: rgba(247, 249, 252, 0.92);
  border-bottom: 1px solid rgba(148, 163, 184, 0.14);
}

.dyn-table tbody tr {
  border-bottom: 1px solid rgba(148, 163, 184, 0.08);
}

.dyn-table tbody tr:hover {
  background: rgba(37, 99, 235, 0.025);
}

.dyn-table tbody tr:not(:last-child) td {
  border-bottom: 1px solid rgba(148, 163, 184, 0.08);
}

.dyn-th-sticky,
.dyn-td-sticky {
  position: sticky;
  left: 0;
  z-index: 1;
  font-weight: 800;
  color: #172033;
}

.dyn-th-sticky {
  background: #f7f9fc;
}

.dyn-td-sticky {
  background: #fff;
}

.dyn-table tbody tr:hover .dyn-td-sticky,
.dyn-row--incomplete .dyn-td-sticky {
  background: #f7faff;
}
.dyn-th-goal, .dyn-td-goal { border-left: 1px solid rgba(148, 163, 184, 0.14); }
.dyn-th-group { border-left: 1px solid rgba(148, 163, 184, 0.14); }
.dyn-row--incomplete { background: rgba(37, 99, 235, 0.035); }
.dyn-incomplete-badge {
  margin-left: 0.5rem; padding: 0.1rem 0.5rem; border-radius: 0.5rem; font-style: normal;
  font-size: 0.74rem; font-weight: 700; color: #2563eb; background: rgba(37, 99, 235, 0.1);
}
:deep(.dyn-cellval) { color: #4b4b4b; font-weight: 600; }
:deep(.dyn-goal-cpa) { color: #9aa3b2; font-size: 0.82rem; font-weight: 600; }
:deep(.dyn-delta) { margin-left: 0.4rem; font-size: 0.8rem; font-weight: 700; }
:deep(.dyn-delta--neutral) { color: #9aa3b2; }
:deep(.dyn-delta--good) { color: #22a85a; }
:deep(.dyn-delta--bad) { color: #ef4444; }

@media (max-width: 980px) {
  .dyn-controls,
  .dyn-controls__row,
  .dyn-controls__left,
  .dyn-controls__right {
    width: 100%;
  }

  .dyn-controls__row {
    align-items: stretch;
  }

  .dyn-controls__right {
    justify-content: flex-start;
    margin-left: 0;
  }

  .dyn-chart-head {
    align-items: stretch;
  }

  .dyn-metric-chips {
    justify-content: flex-start;
  }
}

@media (max-width: 640px) {
  .dyn-controls {
    padding: 0.85rem;
    border-radius: 1rem;
  }

  .dyn-control-group,
  .dyn-seg,
  .dyn-backfill__btn,
  .dyn-export,
  .dyn-export__btn {
    width: 100%;
  }

  .dyn-seg {
    justify-content: space-between;
  }

  .dyn-seg__btn {
    flex: 1;
    padding: 0 0.7rem;
  }

  .panel {
    padding: 1.25rem;
    border-radius: 1.1rem;
  }
}
</style>
