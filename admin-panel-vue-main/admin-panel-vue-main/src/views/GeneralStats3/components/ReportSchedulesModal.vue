<template>
  <Teleport to="body">
    <div class="rs-backdrop" @click.self="$emit('close')">
      <div class="rs-modal">
        <div class="rs-head">
          <div>
            <h3>Автоотправка отчётов</h3>
            <p>Настройте правила: какой отчёт, в каком составе, куда и когда отправлять.</p>
          </div>
          <button type="button" class="rs-close" aria-label="Закрыть" @click="$emit('close')">✕</button>
        </div>

        <!-- Вкладки -->
        <div v-if="!editing" class="rs-tabs">
          <button type="button" :class="{ active: tab === 'rules' }" @click="tab = 'rules'">
            Правила <em v-if="rules.length">{{ rules.length }}</em>
          </button>
          <button type="button" :class="{ active: tab === 'groups' }" @click="tab = 'groups'">
            Группы и чаты <em v-if="targets.length">{{ targets.length }}</em>
          </button>
        </div>

        <!-- ═══ Вкладка: Правила ═══ -->
        <template v-if="!editing && tab === 'rules'">
          <div v-if="loading" class="rs-empty">Загружаем правила…</div>
          <div v-else-if="!rules.length" class="rs-empty">
            <strong>Правил пока нет</strong>
            <span>Создайте первое правило — и отчёты начнут приходить автоматически.</span>
          </div>
          <div v-else class="rs-list">
            <div v-for="rule in rules" :key="rule.id" class="rs-rule" :class="{ 'rs-rule--off': !rule.enabled }">
              <label class="rs-switch" :title="rule.enabled ? 'Выключить' : 'Включить'">
                <input type="checkbox" :checked="rule.enabled" @change="toggleRule(rule, $event.target.checked)" />
                <i></i>
              </label>
              <div class="rs-rule-main" @click="openEdit(rule)">
                <strong>{{ rule.name || rule.scope_label }}</strong>
                <span class="rs-rule-meta">
                  {{ rule.scope_label }} · {{ dayLabel(rule.day) }} в {{ rule.send_time }} МСК ·
                  {{ periodLabel(rule.period_days) }} · {{ rule.report_format === 'mobile' ? 'мобильный' : 'десктопный' }}
                </span>
                <span class="rs-rule-channels">
                  <em v-for="ch in rule.channels" :key="ch" class="rs-chip" :class="`rs-chip--${ch}`">{{ channelName(ch) }}</em>
                  <em v-for="tid in rule.chat_targets" :key="tid" class="rs-chip rs-chip--group">{{ targetTitle(tid) }}</em>
                  <em v-if="rule.last_sent_at" class="rs-last">последняя: {{ formatDateTime(rule.last_sent_at) }}</em>
                </span>
              </div>
              <div class="rs-rule-actions">
                <button type="button" class="rs-mini" :disabled="testingId === rule.id" title="Отправить сейчас (проверка)" @click="testRule(rule)">
                  {{ testingId === rule.id ? '…' : '▶ Сейчас' }}
                </button>
                <button type="button" class="rs-mini" @click="openEdit(rule)">Изменить</button>
                <button type="button" class="rs-mini rs-mini--danger" @click="removeRule(rule)">Удалить</button>
              </div>
            </div>
          </div>
          <div class="rs-footer">
            <button type="button" class="rs-primary" @click="openCreate">+ Новое правило</button>
          </div>
        </template>

        <!-- ═══ Вкладка: Группы и чаты ═══ -->
        <template v-else-if="!editing && tab === 'groups'">
          <p class="rs-groups-hint">
            Добавьте бота AdMirra в группу вашей команды (Telegram или MAX) — и отчёты будут приходить прямо в общий чат.
            Подключённые группы можно выбирать в правилах в разделе «Куда отправляем».
          </p>

          <div v-if="targets.length" class="rs-list rs-list--targets">
            <div v-for="t in targets" :key="t.id" class="rs-target">
              <span class="rs-chip" :class="t.kind === 'telegram' ? 'rs-chip--telegram' : 'rs-chip--max'">{{ channelName(t.kind) }}</span>
              <strong>{{ t.title || `Чат ${t.chat_id}` }}</strong>
              <span class="rs-target-id">ID {{ t.chat_id }}</span>
              <button type="button" class="rs-mini rs-mini--danger" @click="removeTarget(t)">Отключить</button>
            </div>
          </div>
          <div v-else class="rs-empty rs-empty--small">Подключённых групп пока нет</div>

          <div class="rs-connect-box">
            <div class="rs-connect-head">Подключить группу</div>
            <div class="rs-row">
              <button type="button" class="rs-secondary" :disabled="linkLoading" @click="createLinkCode('telegram')">
                <span class="rs-brand-dot rs-brand-dot--tg"></span> Группа Telegram
              </button>
              <button type="button" class="rs-secondary" :disabled="linkLoading" @click="createLinkCode('max')">
                <span class="rs-brand-dot rs-brand-dot--max"></span> Группа MAX
              </button>
              <button v-if="linkInfo" type="button" class="rs-mini" @click="refreshTargets">Проверить подключение</button>
            </div>
            <div v-if="linkInfo" class="rs-link-steps">
              <template v-if="linkInfo.kind === 'telegram' && linkInfo.group_link">
                <div class="rs-step">
                  <i>1</i>
                  <a class="rs-add-bot-link" :href="linkInfo.group_link" target="_blank" rel="noopener">
                    Добавить бота @{{ linkInfo.bot }} в группу →
                  </a>
                  <small>откроется Telegram с выбором группы; привязка произойдёт автоматически</small>
                </div>
                <div class="rs-step rs-step--alt">
                  <i>2</i> Если бот уже в группе — просто отправьте там:
                  <code class="rs-code" @click="copyCommand">{{ linkInfo.command }} <span>копировать</span></code>
                </div>
                <div class="rs-step"><i>3</i> Нажмите «Проверить подключение» — группа появится в списке (код действует 30 минут)</div>
              </template>
              <template v-else>
                <div class="rs-step"><i>1</i> Добавьте бота <strong>{{ linkInfo.bot ? '@' + linkInfo.bot : 'AdMirra (см. настройки MAX)' }}</strong> в вашу группу {{ linkInfo.kind === 'telegram' ? 'Telegram' : 'MAX' }}</div>
                <div class="rs-step">
                  <i>2</i> Отправьте в группе команду:
                  <code class="rs-code" @click="copyCommand">{{ linkInfo.command }} <span>копировать</span></code>
                </div>
                <div class="rs-step"><i>3</i> Нажмите «Проверить подключение» — группа появится в списке (код действует 30 минут)</div>
              </template>
            </div>
          </div>
        </template>

        <!-- ═══ Конструктор правила ═══ -->
        <template v-else>
          <div class="rs-form">
            <label class="rs-field">
              <span>Название <small>(необязательно)</small></span>
              <input v-model="form.name" type="text" class="rs-input" maxlength="60" placeholder="Например: Яндекс — вечерний отчёт" />
            </label>

            <div class="rs-field">
              <span>Что отправляем</span>
              <div class="rs-row">
                <div class="rs-dd rs-grow" :class="{ open: openDd === 'scope' }" v-click-outside="() => closeDd('scope')">
                  <button type="button" class="rs-dd-head" @click="toggleDd('scope')">
                    <span class="rs-dd-current">{{ scopeLabel }}</span>
                    <span class="rs-select-arrow"></span>
                  </button>
                  <div v-if="openDd === 'scope'" class="rs-dd-list">
                    <template v-for="opt in scopeOptions" :key="opt.value || opt.label">
                      <div v-if="opt.group" class="rs-dd-group">{{ opt.label }}</div>
                      <button v-else type="button" class="rs-dd-option" :class="{ selected: form.scope === opt.value }" @click="pickDd('scope', opt.value)">
                        {{ opt.label }}
                        <svg v-if="form.scope === opt.value" class="rs-dd-check" viewBox="0 0 18 14" fill="none"><path d="M1.5 7.2 6.5 12 16.5 1.5" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                      </button>
                    </template>
                  </div>
                </div>
                <div class="rs-dd rs-fix-13" :class="{ open: openDd === 'platform' }" v-click-outside="() => closeDd('platform')">
                  <button type="button" class="rs-dd-head" @click="toggleDd('platform')">
                    <span class="rs-dd-current">{{ optLabel(PLATFORM_OPTIONS, form.platform) }}</span>
                    <span class="rs-select-arrow"></span>
                  </button>
                  <div v-if="openDd === 'platform'" class="rs-dd-list">
                    <button v-for="opt in PLATFORM_OPTIONS" :key="opt.value" type="button" class="rs-dd-option" :class="{ selected: form.platform === opt.value }" @click="pickDd('platform', opt.value)">
                      {{ opt.label }}
                      <svg v-if="form.platform === opt.value" class="rs-dd-check" viewBox="0 0 18 14" fill="none"><path d="M1.5 7.2 6.5 12 16.5 1.5" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <div class="rs-field">
              <span>Куда отправляем</span>
              <div class="rs-row rs-row--wrap">
                <label class="rs-check" :class="{ 'rs-check--off': !bound.telegram, 'rs-check--on': form.channels.includes('telegram') }">
                  <input type="checkbox" value="telegram" v-model="form.channels" :disabled="!bound.telegram" />
                  <span class="rs-box"><svg viewBox="0 0 12 10" fill="none"><path d="M1 5.2 4.4 8.6 11 1.4" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"/></svg></span>
                  Telegram <small v-if="!bound.telegram">(не подключён)</small>
                </label>
                <label class="rs-check" :class="{ 'rs-check--off': !bound.max, 'rs-check--on': form.channels.includes('max') }">
                  <input type="checkbox" value="max" v-model="form.channels" :disabled="!bound.max" />
                  <span class="rs-box"><svg viewBox="0 0 12 10" fill="none"><path d="M1 5.2 4.4 8.6 11 1.4" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"/></svg></span>
                  MAX <small v-if="!bound.max">(не подключён)</small>
                </label>
                <label class="rs-check rs-check--off" title="Почта временно недоступна">
                  <input type="checkbox" disabled />
                  <span class="rs-box"></span>
                  Email <small>(временно недоступна)</small>
                </label>
              </div>
              <template v-if="targets.length">
                <span class="rs-subfield">Группы и чаты команды</span>
                <div class="rs-row rs-row--wrap">
                  <label v-for="t in targets" :key="t.id" class="rs-check" :class="{ 'rs-check--on': form.chat_targets.includes(t.id) }">
                    <input type="checkbox" :value="t.id" v-model="form.chat_targets" />
                    <span class="rs-box"><svg viewBox="0 0 12 10" fill="none"><path d="M1 5.2 4.4 8.6 11 1.4" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"/></svg></span>
                    👥 {{ t.title || `Чат ${t.chat_id}` }}
                    <small>{{ channelName(t.kind) }}</small>
                  </label>
                </div>
              </template>
              <small v-if="!bound.telegram && !bound.max && !targets.length" class="rs-hint-warn">
                Подключите Telegram или MAX (лично — в блоке «Отчёты» на дашборде, группу — во вкладке «Группы и чаты»).
              </small>
              <small v-else class="rs-hint-note">Можно выбрать только группу — в личку тогда приходить не будет.</small>
            </div>

            <div class="rs-field">
              <span>Когда</span>
              <div class="rs-row">
                <div class="rs-dd rs-grow" :class="{ open: openDd === 'day' }" v-click-outside="() => closeDd('day')">
                  <button type="button" class="rs-dd-head" @click="toggleDd('day')">
                    <span class="rs-dd-current">{{ optLabel(DAY_OPTIONS, form.day) }}</span>
                    <span class="rs-select-arrow"></span>
                  </button>
                  <div v-if="openDd === 'day'" class="rs-dd-list">
                    <button v-for="opt in DAY_OPTIONS" :key="opt.value" type="button" class="rs-dd-option" :class="{ selected: form.day === opt.value }" @click="pickDd('day', opt.value)">
                      {{ opt.label }}
                      <svg v-if="form.day === opt.value" class="rs-dd-check" viewBox="0 0 18 14" fill="none"><path d="M1.5 7.2 6.5 12 16.5 1.5" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                    </button>
                  </div>
                </div>
                <div class="rs-time-wrap">
                  <input v-model="form.send_time" type="text" class="rs-time" inputmode="numeric" maxlength="5" placeholder="16:00" />
                  <span class="rs-msk">МСК</span>
                </div>
              </div>
            </div>

            <div class="rs-field">
              <span>Состав отчёта</span>
              <div class="rs-chips">
                <button
                  v-for="opt in SECTION_OPTIONS"
                  :key="opt.value"
                  type="button"
                  class="rs-chip-toggle"
                  :class="{ active: form.sections.includes(opt.value) }"
                  @click="toggleFromList(form.sections, opt.value, 1)"
                >{{ opt.label }}</button>
                <button
                  type="button"
                  class="rs-chip-toggle"
                  :class="{ active: form.include_dynamics }"
                  @click="form.include_dynamics = !form.include_dynamics"
                >Динамика</button>
              </div>

              <template v-if="form.sections.includes('chart')">
                <span class="rs-subfield">Графики <small>— отдельный график на каждый показатель, сверху вниз</small></span>
                <div class="rs-chips">
                  <button
                    v-for="opt in METRIC_OPTIONS"
                    :key="opt.value"
                    type="button"
                    class="rs-chip-toggle rs-chip-toggle--metric"
                    :class="{ active: form.chart_metrics.includes(opt.value) }"
                    @click="toggleFromList(form.chart_metrics, opt.value, 1)"
                  ><i class="rs-metric-dot" :style="{ background: opt.color }"></i>{{ opt.label }}</button>
                </div>
              </template>

              <template v-if="form.include_dynamics">
                <span class="rs-subfield">Показатели динамики <small>— отдельный график по месяцам на каждый</small></span>
                <div class="rs-chips">
                  <button
                    v-for="opt in METRIC_OPTIONS"
                    :key="'dyn-' + opt.value"
                    type="button"
                    class="rs-chip-toggle rs-chip-toggle--metric"
                    :class="{ active: form.dynamics_metrics.includes(opt.value) }"
                    @click="toggleFromList(form.dynamics_metrics, opt.value, 1)"
                  ><i class="rs-metric-dot" :style="{ background: opt.color }"></i>{{ opt.label }}</button>
                </div>
              </template>
            </div>

            <div class="rs-field">
              <span>Данные и формат</span>
              <div class="rs-row rs-row--wrap">
                <div class="rs-dd rs-fix-10" :class="{ open: openDd === 'period' }" v-click-outside="() => closeDd('period')">
                  <button type="button" class="rs-dd-head" @click="toggleDd('period')">
                    <span class="rs-dd-current">{{ optLabel(PERIOD_OPTIONS, form.period_days) }}</span>
                    <span class="rs-select-arrow"></span>
                  </button>
                  <div v-if="openDd === 'period'" class="rs-dd-list">
                    <button v-for="opt in PERIOD_OPTIONS" :key="opt.value" type="button" class="rs-dd-option" :class="{ selected: form.period_days === opt.value }" @click="pickDd('period', opt.value)">
                      {{ opt.label }}
                      <svg v-if="form.period_days === opt.value" class="rs-dd-check" viewBox="0 0 18 14" fill="none"><path d="M1.5 7.2 6.5 12 16.5 1.5" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                    </button>
                  </div>
                </div>
                <div class="rs-seg">
                  <button type="button" :class="{ active: form.report_format === 'desktop' }" @click="form.report_format = 'desktop'">🖥 Десктопный</button>
                  <button type="button" :class="{ active: form.report_format === 'mobile' }" @click="form.report_format = 'mobile'">📱 Мобильный</button>
                </div>
              </div>
            </div>

            <div class="rs-form-footer">
              <button type="button" class="rs-secondary" @click="editing = null">← Назад</button>
              <span class="rs-flex"></span>
              <button type="button" class="rs-primary" :disabled="saving || (!form.channels.length && !form.chat_targets.length)" @click="saveRule">
                {{ saving ? 'Сохраняем…' : (editing === 'new' ? 'Создать правило' : 'Сохранить') }}
              </button>
            </div>
          </div>
        </template>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import api from '@/api/axios'
import { useToaster } from '@/composables/useToaster'

const props = defineProps({
  clients: { type: Array, default: () => [] },
  telegramBound: { type: Boolean, default: false },
  maxBound: { type: Boolean, default: false },
})
defineEmits(['close'])

const toaster = useToaster()
const tab = ref('rules')
const rules = ref([])
const folders = ref([])
const targets = ref([])
const loading = ref(true)
const saving = ref(false)
const testingId = ref(null)
const editing = ref(null) // null | 'new' | rule.id
const linkInfo = ref(null) // { kind, code, command, bot }
const linkLoading = ref(false)
const form = ref(defaultForm())

const bound = computed(() => ({ telegram: props.telegramBound, max: props.maxBound }))

function defaultForm() {
  return {
    name: '',
    scope: 'all',
    platform: 'all',
    channels: [],
    chat_targets: [],
    day: 'daily',
    send_time: '10:00',
    period_days: 7,
    report_format: 'desktop',
    include_dynamics: false,
    sections: ['kpi', 'chart', 'channels', 'campaigns'],
    chart_metrics: ['cost', 'clicks'],
    dynamics_metrics: ['cost'],
  }
}

const SECTION_OPTIONS = [
  { value: 'kpi', label: 'KPI-карточки' },
  { value: 'chart', label: 'Графики' },
  { value: 'channels', label: 'Каналы' },
  { value: 'campaigns', label: 'Кампании' },
]

// Те же 6 показателей и цвета, что на графике дашборда
const METRIC_OPTIONS = [
  { value: 'cost', label: 'Расход', color: '#2563eb' },
  { value: 'impressions', label: 'Показы', color: '#F0926D' },
  { value: 'clicks', label: 'Клики', color: '#38BDF8' },
  { value: 'cpc', label: 'CPC', color: '#D38CFF' },
  { value: 'cpa', label: 'CPL', color: '#EB8525' },
  { value: 'leads', label: 'Конверсии', color: '#8ADA70' },
]

function toggleFromList(list, value, minCount = 0) {
  const idx = list.indexOf(value)
  if (idx === -1) list.push(value)
  else if (list.length > minCount) list.splice(idx, 1)
}

// ── Кастомные дропдауны (в стиле выпадашек дашборда) ──
const openDd = ref(null)
const toggleDd = (name) => { openDd.value = openDd.value === name ? null : name }
const closeDd = (name) => { if (openDd.value === name) openDd.value = null }
const pickDd = (name, value) => {
  if (name === 'scope') form.value.scope = value
  else if (name === 'platform') form.value.platform = value
  else if (name === 'day') form.value.day = value
  else if (name === 'period') form.value.period_days = value
  openDd.value = null
}
const optLabel = (options, value) => options.find((o) => o.value === value)?.label || '—'

const PLATFORM_OPTIONS = [
  { value: 'all', label: 'Все каналы' },
  { value: 'yandex', label: 'Яндекс Директ' },
  { value: 'vk', label: 'VK Реклама' },
  { value: 'avito', label: 'Avito' },
]
const DAY_OPTIONS = [
  { value: 'daily', label: 'Ежедневно' },
  { value: 'weekdays', label: 'По будням' },
  { value: 'monday', label: 'Понедельник' },
  { value: 'tuesday', label: 'Вторник' },
  { value: 'wednesday', label: 'Среда' },
  { value: 'thursday', label: 'Четверг' },
  { value: 'friday', label: 'Пятница' },
  { value: 'saturday', label: 'Суббота' },
  { value: 'sunday', label: 'Воскресенье' },
]
const PERIOD_OPTIONS = [
  { value: 1, label: 'За 1 день' },
  { value: 7, label: 'За 7 дней' },
  { value: 14, label: 'За 14 дней' },
  { value: 30, label: 'За 30 дней' },
]
const scopeOptions = computed(() => {
  const out = [{ value: 'all', label: 'Все проекты' }]
  if (folders.value.length) {
    out.push({ group: true, label: 'Папки' })
    for (const f of folders.value) out.push({ value: `folder:${f.id}`, label: `Папка «${f.name}»` })
  }
  if (props.clients.length) {
    out.push({ group: true, label: 'Проекты' })
    for (const c of props.clients) out.push({ value: `client:${c.id}`, label: c.name })
  }
  return out
})
const scopeLabel = computed(() => scopeOptions.value.find((o) => o.value === form.value.scope)?.label || 'Все проекты')

// Локальная директива клик-снаружи (как на дашборде)
const vClickOutside = {
  mounted(el, binding) {
    el._outsideHandler = (event) => {
      if (!el.contains(event.target)) binding.value(event)
    }
    document.addEventListener('mousedown', el._outsideHandler)
  },
  unmounted(el) {
    document.removeEventListener('mousedown', el._outsideHandler)
  },
}

const DAY_LABELS = {
  daily: 'Ежедневно', weekdays: 'По будням', monday: 'Пн', tuesday: 'Вт', wednesday: 'Ср',
  thursday: 'Чт', friday: 'Пт', saturday: 'Сб', sunday: 'Вс',
}
const dayLabel = (d) => DAY_LABELS[d] || d
const periodLabel = (n) => (Number(n) === 1 ? 'за день' : `за ${n} дн.`)
const channelName = (ch) => ({ telegram: 'Telegram', max: 'MAX', email: 'Email' }[ch] || ch)
const targetTitle = (tid) => {
  const t = targets.value.find((x) => x.id === tid)
  return t ? `👥 ${t.title || 'Чат'}` : '👥 Группа'
}
const formatDateTime = (iso) => {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

async function load() {
  loading.value = true
  try {
    const [rulesRes, foldersRes, targetsRes] = await Promise.allSettled([
      api.get('reports/schedules'),
      api.get('folders/'),
      api.get('reports/chat-targets'),
    ])
    rules.value = rulesRes.status === 'fulfilled' ? (rulesRes.value.data || []) : []
    folders.value = foldersRes.status === 'fulfilled' ? (foldersRes.value.data || []) : []
    targets.value = targetsRes.status === 'fulfilled' ? (targetsRes.value.data || []) : []
  } finally {
    loading.value = false
  }
}

async function refreshTargets() {
  try {
    const { data } = await api.get('reports/chat-targets')
    const before = targets.value.length
    targets.value = data || []
    if (targets.value.length > before) {
      toaster.success('Группа подключена!')
      linkInfo.value = null
    } else {
      toaster.info('Пока не видно новой группы — проверьте, что команда отправлена в чат')
    }
  } catch { /* ignore */ }
}

async function createLinkCode(kind) {
  linkLoading.value = true
  try {
    const { data } = await api.post('reports/chat-targets/link-code', { kind })
    linkInfo.value = { ...data, kind }
  } catch (e) {
    const d = e?.response?.data?.detail
    toaster.error(typeof d === 'string' ? d : 'Не удалось создать код подключения')
  } finally {
    linkLoading.value = false
  }
}

async function copyCommand() {
  try {
    await navigator.clipboard.writeText(linkInfo.value.command)
    toaster.success('Команда скопирована — отправьте её в группе')
  } catch { /* ignore */ }
}

async function removeTarget(t) {
  if (!confirm(`Отключить «${t.title || t.chat_id}»? Отчёты в этот чат приходить перестанут.`)) return
  try {
    await api.delete(`reports/chat-targets/${t.id}`)
    targets.value = targets.value.filter((x) => x.id !== t.id)
    toaster.success('Чат отключён')
  } catch {
    toaster.error('Не удалось отключить чат')
  }
}

function openCreate() {
  form.value = defaultForm()
  if (bound.value.telegram) form.value.channels = ['telegram']
  else if (bound.value.max) form.value.channels = ['max']
  editing.value = 'new'
}

function openEdit(rule) {
  form.value = {
    name: rule.name || '',
    scope: rule.scope_folder_id ? `folder:${rule.scope_folder_id}` : (rule.scope_client_id ? `client:${rule.scope_client_id}` : 'all'),
    platform: rule.platform || 'all',
    channels: [...(rule.channels || [])],
    chat_targets: [...(rule.chat_targets || [])],
    day: rule.day || 'daily',
    send_time: rule.send_time || '10:00',
    period_days: Number(rule.period_days || 7),
    report_format: rule.report_format || 'desktop',
    include_dynamics: Boolean(rule.include_dynamics),
    sections: [...(rule.sections?.length ? rule.sections : ['kpi', 'chart', 'channels', 'campaigns'])],
    chart_metrics: [...(rule.chart_metrics?.length ? rule.chart_metrics : ['cost', 'clicks'])],
    dynamics_metrics: [...(rule.dynamics_metrics?.length ? rule.dynamics_metrics : ['cost'])],
  }
  editing.value = rule.id
}

function buildPayload() {
  const [kind, id] = String(form.value.scope).split(':')
  const time = String(form.value.send_time || '').trim()
  return {
    name: form.value.name?.trim() || null,
    enabled: true,
    scope_client_id: kind === 'client' ? id : null,
    scope_folder_id: kind === 'folder' ? id : null,
    platform: form.value.platform,
    channels: form.value.channels,
    chat_targets: form.value.chat_targets,
    day: form.value.day,
    send_time: /^\d{1,2}:\d{2}$/.test(time) ? time.padStart(5, '0') : '10:00',
    period_days: form.value.period_days,
    report_format: form.value.report_format,
    include_dynamics: form.value.include_dynamics,
    sections: form.value.sections,
    chart_metrics: form.value.chart_metrics,
    dynamics_metrics: form.value.dynamics_metrics,
  }
}

async function saveRule() {
  saving.value = true
  try {
    const payload = buildPayload()
    if (editing.value === 'new') {
      await api.post('reports/schedules', payload)
      toaster.success('Правило создано — отчёты будут приходить по расписанию')
    } else {
      await api.put(`reports/schedules/${editing.value}`, payload)
      toaster.success('Правило обновлено')
    }
    editing.value = null
    await load()
  } catch (e) {
    const d = e?.response?.data?.detail
    toaster.error(typeof d === 'string' ? d : 'Не удалось сохранить правило')
  } finally {
    saving.value = false
  }
}

async function toggleRule(rule, enabled) {
  try {
    await api.put(`reports/schedules/${rule.id}`, { enabled })
    rule.enabled = enabled
  } catch {
    toaster.error('Не удалось изменить правило')
  }
}

async function removeRule(rule) {
  if (!confirm(`Удалить правило «${rule.name || rule.scope_label}»?`)) return
  try {
    await api.delete(`reports/schedules/${rule.id}`)
    rules.value = rules.value.filter((r) => r.id !== rule.id)
    toaster.success('Правило удалено')
  } catch {
    toaster.error('Не удалось удалить правило')
  }
}

async function testRule(rule) {
  testingId.value = rule.id
  try {
    const { data } = await api.post(`reports/schedules/${rule.id}/test`)
    const r = data?.results || {}
    const sent = Object.entries(r).filter(([, v]) => v === true).map(([k]) => channelName(k))
    if (r.groups) sent.push(`группы ${r.groups}`)
    if (sent.length) toaster.success(`Отчёт отправлен: ${sent.join(', ')}`)
    else toaster.warning('Отправка не удалась — проверьте подключение каналов')
    await load()
  } catch (e) {
    const d = e?.response?.data?.detail
    toaster.error(typeof d === 'string' ? d : 'Не удалось отправить отчёт')
  } finally {
    testingId.value = null
  }
}

onMounted(load)
</script>

<style scoped>
/* ── Профессиональная модалка в стиле проекта (базовый масштаб +20%) ── */
.rs-backdrop {
  position: fixed; inset: 0; z-index: 95;
  display: flex; align-items: center; justify-content: center;
  background: rgba(9, 24, 63, 0.5);
  backdrop-filter: blur(3px);
  padding: 1rem;
}
.rs-modal {
  width: min(56rem, 96vw); max-height: 92vh; overflow-y: auto;
  background: #fff; border-radius: 1.4rem; padding: 1.9rem 2.1rem 1.7rem;
  box-shadow: 0 32px 90px rgba(9, 24, 63, 0.35);
}
.rs-head { display: flex; align-items: flex-start; gap: 1rem; margin-bottom: 1.1rem; }
.rs-head h3 { margin: 0 0 0.35rem; font-size: 1.55rem; font-weight: 800; color: #171717; letter-spacing: -0.01em; }
.rs-head p { margin: 0; font-size: 0.98rem; color: rgba(105,105,105,0.75); line-height: 1.5; }
.rs-close {
  margin-left: auto; border: none; background: rgba(15,23,42,0.05);
  width: 2.2rem; height: 2.2rem; border-radius: 0.7rem;
  font-size: 1rem; color: #64748b; cursor: pointer; flex-shrink: 0;
}
.rs-close:hover { background: rgba(15,23,42,0.1); color: #171717; }

/* Вкладки */
.rs-tabs { display: flex; gap: 0.3rem; margin-bottom: 1.2rem; background: rgba(15,23,42,0.045); border-radius: 0.85rem; padding: 0.28rem; width: fit-content; }
.rs-tabs button {
  border: none; background: none; cursor: pointer;
  padding: 0.55rem 1.15rem; border-radius: 0.65rem;
  font-size: 0.95rem; font-weight: 700; color: #64748b;
  display: inline-flex; align-items: center; gap: 0.45rem;
}
.rs-tabs button.active { background: #fff; color: #2563eb; box-shadow: 0 2px 8px rgba(15,23,42,0.1); }
.rs-tabs button em {
  font-style: normal; font-size: 0.72rem; font-weight: 800;
  background: rgba(37,99,235,0.12); color: #2563eb;
  padding: 0.08rem 0.5rem; border-radius: 99px;
}

.rs-empty { padding: 2.6rem 0; text-align: center; color: rgba(105,105,105,0.65); font-size: 1rem; display: flex; flex-direction: column; gap: 0.35rem; }
.rs-empty strong { color: #444; }
.rs-empty--small { padding: 1.2rem 0; }

.rs-list { display: flex; flex-direction: column; gap: 0.7rem; }
.rs-rule {
  display: flex; align-items: center; gap: 0.95rem;
  padding: 1rem 1.1rem; border-radius: 1rem;
  background: #f8fafc; box-shadow: inset 0 0 0 1px rgba(15,23,42,0.05);
  transition: box-shadow 0.15s ease;
}
.rs-rule:hover { box-shadow: inset 0 0 0 1px rgba(37,99,235,0.25); }
.rs-rule--off { opacity: 0.55; }
.rs-rule-main { flex: 1; min-width: 0; cursor: pointer; display: flex; flex-direction: column; gap: 0.2rem; }
.rs-rule-main strong { font-size: 1.05rem; color: #171717; }
.rs-rule-meta { font-size: 0.85rem; color: rgba(105,105,105,0.75); }
.rs-rule-channels { display: flex; gap: 0.4rem; align-items: center; flex-wrap: wrap; }
.rs-chip {
  font-style: normal; font-size: 0.76rem; font-weight: 700;
  padding: 0.14rem 0.6rem; border-radius: 99px;
  background: rgba(37,99,235,0.1); color: #2563eb;
}
.rs-chip--max { background: rgba(124,58,237,0.1); color: #7c3aed; }
.rs-chip--email { background: rgba(5,150,105,0.1); color: #059669; }
.rs-chip--group { background: rgba(234,153,66,0.14); color: #b45309; }
.rs-last { font-style: normal; font-size: 0.76rem; color: #94a3b8; }
.rs-rule-actions { display: flex; gap: 0.4rem; flex-shrink: 0; }
.rs-mini {
  border: none; background: rgba(15,23,42,0.05); color: #444;
  font-size: 0.82rem; font-weight: 700; padding: 0.45rem 0.75rem;
  border-radius: 0.6rem; cursor: pointer;
}
.rs-mini:hover { background: rgba(37,99,235,0.1); color: #2563eb; }
.rs-mini--danger:hover { background: rgba(220,38,38,0.1); color: #dc2626; }
.rs-mini:disabled { opacity: 0.6; cursor: default; }

.rs-switch { position: relative; display: inline-block; width: 2.5rem; height: 1.4rem; flex-shrink: 0; }
.rs-switch input { display: none; }
.rs-switch i {
  position: absolute; inset: 0; border-radius: 99px; background: #cbd5e1;
  transition: background 0.15s ease; cursor: pointer;
}
.rs-switch i::after {
  content: ''; position: absolute; top: 0.18rem; left: 0.18rem;
  width: 1.05rem; height: 1.05rem; border-radius: 50%; background: #fff;
  box-shadow: 0 1px 3px rgba(15,23,42,0.25);
  transition: transform 0.15s ease;
}
.rs-switch input:checked + i { background: #2563eb; }
.rs-switch input:checked + i::after { transform: translateX(1.08rem); }

.rs-footer { display: flex; justify-content: flex-end; margin-top: 1.2rem; }
.rs-primary {
  border: none; background: #2563eb; color: #fff;
  padding: 0.7rem 1.35rem; border-radius: 0.8rem;
  font-weight: 700; font-size: 0.98rem; cursor: pointer;
  transition: background 0.15s ease, box-shadow 0.15s ease;
}
.rs-primary:hover:not(:disabled) { background: #1d4ed8; box-shadow: 0 6px 18px rgba(37,99,235,0.35); }
.rs-primary:disabled { opacity: 0.55; cursor: default; }
.rs-secondary {
  border: none; background: rgba(15,23,42,0.06); color: #444;
  padding: 0.7rem 1.15rem; border-radius: 0.8rem;
  font-weight: 700; font-size: 0.95rem; cursor: pointer;
  display: inline-flex; align-items: center; gap: 0.5rem;
}
.rs-secondary:hover:not(:disabled) { background: rgba(15,23,42,0.1); }

/* Группы */
.rs-groups-hint { margin: 0 0 1rem; font-size: 0.95rem; color: rgba(105,105,105,0.8); line-height: 1.55; }
.rs-target {
  display: flex; align-items: center; gap: 0.7rem;
  padding: 0.8rem 1rem; border-radius: 0.9rem;
  background: #f8fafc; box-shadow: inset 0 0 0 1px rgba(15,23,42,0.05);
}
.rs-target strong { flex: 1; font-size: 0.98rem; color: #171717; }
.rs-target-id { font-size: 0.78rem; color: #94a3b8; }
.rs-connect-box {
  margin-top: 1.2rem; padding: 1.1rem 1.2rem;
  border-radius: 1rem; border: 1.5px dashed rgba(37,99,235,0.3);
  background: rgba(37,99,235,0.03);
}
.rs-connect-head { font-size: 0.95rem; font-weight: 800; color: #171717; margin-bottom: 0.7rem; }
.rs-brand-dot { width: 0.75rem; height: 0.75rem; border-radius: 50%; display: inline-block; }
.rs-brand-dot--tg { background: #2AABEE; }
.rs-brand-dot--max { background: #7c3aed; }
.rs-link-steps { margin-top: 1rem; display: flex; flex-direction: column; gap: 0.55rem; }
.rs-step { display: flex; align-items: center; gap: 0.6rem; font-size: 0.92rem; color: #333; flex-wrap: wrap; }
.rs-step i {
  font-style: normal; width: 1.45rem; height: 1.45rem; border-radius: 50%;
  background: #2563eb; color: #fff; font-size: 0.78rem; font-weight: 800;
  display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.rs-code {
  background: #0f172a; color: #7dd3fc;
  padding: 0.35rem 0.75rem; border-radius: 0.55rem;
  font-size: 0.9rem; font-weight: 700; cursor: pointer;
}
.rs-code span { color: #64748b; font-size: 0.72rem; font-weight: 600; margin-left: 0.5rem; }
.rs-code:hover span { color: #94a3b8; }
.rs-add-bot-link {
  display: inline-flex; align-items: center;
  background: #2AABEE; color: #fff; text-decoration: none;
  padding: 0.45rem 0.95rem; border-radius: 0.65rem;
  font-size: 0.92rem; font-weight: 700;
}
.rs-add-bot-link:hover { background: #1e96d6; }
.rs-step small { color: #94a3b8; font-size: 0.78rem; }
.rs-step--alt { opacity: 0.85; }

/* Конструктор */
.rs-form { display: flex; flex-direction: column; gap: 1.25rem; }
.rs-field { display: flex; flex-direction: column; gap: 0.5rem; }
.rs-field > span { font-size: 0.9rem; font-weight: 800; color: #333; }
.rs-field > span small, .rs-subfield small { font-weight: 500; color: #94a3b8; font-size: 0.78rem; }
.rs-input {
  height: 2.9rem; padding: 0 0.95rem; border-radius: 0.75rem;
  border: 1px solid rgba(15,23,42,0.12); font-size: 0.95rem; font-weight: 600; outline: none;
  transition: border-color 0.13s ease, box-shadow 0.13s ease;
  box-sizing: border-box;
}
.rs-input::placeholder { font-weight: 500; color: #b3bcc9; }
.rs-input:focus { border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37,99,235,0.12); }
.rs-row { display: flex; gap: 0.7rem; align-items: center; }
.rs-row--wrap { flex-wrap: wrap; }
.rs-select {
  flex: 1; min-width: 0;
  height: 2.9rem;
  padding: 0 0.85rem; border-radius: 0.75rem;
  border: 1px solid rgba(15,23,42,0.14); font-size: 0.95rem;
  background: #fff; color: #171717;
}
.rs-select--platform { flex: 0 0 13rem; }
.rs-select--period { flex: 0 0 10rem; }
/* Поле времени — той же высоты, что селекты (было «толстым») */
.rs-time-wrap { display: inline-flex; align-items: center; gap: 0.5rem; }
.rs-time {
  width: 5.6rem; height: 2.9rem; text-align: center;
  padding: 0; border-radius: 0.75rem;
  border: 1px solid rgba(15,23,42,0.14); font-size: 0.98rem; font-weight: 700;
  font-variant-numeric: tabular-nums; outline: none;
}
.rs-time:focus { border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37,99,235,0.12); }
.rs-msk { font-size: 0.88rem; color: #94a3b8; font-weight: 700; }
/* Кастомный чекбокс: скрытый input + стилизованный бокс с галочкой */
.rs-check {
  display: inline-flex; align-items: center; gap: 0.55rem;
  font-size: 0.95rem; font-weight: 600; color: #171717; cursor: pointer;
  height: 2.9rem; padding: 0 1rem; border-radius: 0.75rem;
  background: #fff; border: 1px solid rgba(15,23,42,0.12);
  transition: border-color 0.13s ease, background 0.13s ease;
}
.rs-check:hover:not(.rs-check--off) { border-color: rgba(37,99,235,0.4); }
.rs-check--on { border-color: #2563eb; background: rgba(37,99,235,0.06); }
.rs-check input { display: none; }
.rs-box {
  width: 1.15rem; height: 1.15rem; border-radius: 0.35rem;
  border: 1.5px solid rgba(15,23,42,0.25); background: #fff;
  display: inline-flex; align-items: center; justify-content: center;
  color: #fff; flex-shrink: 0;
  transition: background 0.13s ease, border-color 0.13s ease;
}
.rs-box svg { width: 0.7rem; height: 0.6rem; opacity: 0; transition: opacity 0.1s ease; }
.rs-check--on .rs-box { background: #2563eb; border-color: #2563eb; }
.rs-check--on .rs-box svg { opacity: 1; }
.rs-check small { color: #94a3b8; font-size: 0.78rem; font-weight: 500; }
.rs-check--off { opacity: 0.55; cursor: default; }
.rs-hint-note { color: #94a3b8; font-size: 0.82rem; }
.rs-hint-warn { color: #b45309; font-size: 0.85rem; }
.rs-seg { display: inline-flex; background: rgba(15,23,42,0.05); border-radius: 0.75rem; padding: 0.22rem; height: 2.9rem; box-sizing: border-box; }
.rs-seg button {
  border: none; background: none; padding: 0 0.95rem;
  border-radius: 0.55rem; font-size: 0.9rem; font-weight: 700; color: #64748b; cursor: pointer;
}
.rs-seg button.active { background: #fff; color: #2563eb; box-shadow: 0 1px 5px rgba(15,23,42,0.14); }

.rs-chips { display: flex; gap: 0.45rem; flex-wrap: wrap; }
.rs-chip-toggle {
  border: 1px solid rgba(15,23,42,0.12);
  background: #fff; color: #64748b;
  font-size: 0.9rem; font-weight: 700;
  padding: 0.5rem 0.95rem; border-radius: 99px; cursor: pointer;
  transition: all 0.13s ease;
  display: inline-flex; align-items: center; gap: 0.45rem;
}
.rs-chip-toggle:hover { border-color: rgba(37,99,235,0.4); }
.rs-chip-toggle.active {
  border-color: #2563eb; background: rgba(37,99,235,0.08); color: #2563eb;
}
.rs-metric-dot { width: 0.6rem; height: 0.6rem; border-radius: 50%; display: inline-block; opacity: 0.45; }
.rs-chip-toggle.active .rs-metric-dot { opacity: 1; }
.rs-subfield { font-size: 0.85rem; font-weight: 700; color: #64748b; margin-top: 0.35rem; }

.rs-form-footer { display: flex; align-items: center; gap: 0.7rem; margin-top: 0.5rem; }
.rs-flex { flex: 1; }
</style>
