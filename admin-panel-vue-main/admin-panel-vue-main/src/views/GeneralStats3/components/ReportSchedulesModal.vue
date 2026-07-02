<template>
  <Teleport to="body">
    <div class="rs-backdrop" @click.self="$emit('close')">
      <div class="rs-modal">
        <div class="rs-head">
          <div>
            <h3>Автоотправка отчётов</h3>
            <p>Правила: какой отчёт, куда и когда отправлять. Можно несколько правил — например, Яндекс проекта в 16:00 в Telegram и Авито в 16:30 в MAX.</p>
          </div>
          <button type="button" class="rs-close" aria-label="Закрыть" @click="$emit('close')">✕</button>
        </div>

        <!-- ═══ Список правил ═══ -->
        <template v-if="!editing">
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
                  {{ periodLabel(rule.period_days) }} · {{ rule.report_format === 'mobile' ? 'моб.' : 'десктоп' }}
                  <template v-if="rule.include_dynamics"> · +динамика</template>
                </span>
                <span class="rs-rule-channels">
                  <em v-for="ch in rule.channels" :key="ch" class="rs-chip" :class="`rs-chip--${ch}`">{{ channelName(ch) }}</em>
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

        <!-- ═══ Конструктор правила ═══ -->
        <template v-else>
          <div class="rs-form">
            <label class="rs-field">
              <span>Название (необязательно)</span>
              <input v-model="form.name" type="text" maxlength="60" placeholder="Например: Яндекс — вечерний отчёт" />
            </label>

            <div class="rs-field">
              <span>Что отправляем</span>
              <div class="rs-row">
                <select v-model="form.scope" class="rs-select">
                  <option value="all">Все проекты</option>
                  <optgroup v-if="folders.length" label="Папки">
                    <option v-for="f in folders" :key="f.id" :value="`folder:${f.id}`">Папка «{{ f.name }}»</option>
                  </optgroup>
                  <optgroup label="Проекты">
                    <option v-for="c in clients" :key="c.id" :value="`client:${c.id}`">{{ c.name }}</option>
                  </optgroup>
                </select>
                <select v-model="form.platform" class="rs-select rs-select--platform">
                  <option value="all">Все каналы</option>
                  <option value="yandex">Яндекс Директ</option>
                  <option value="vk">VK Реклама</option>
                  <option value="avito">Avito</option>
                </select>
              </div>
            </div>

            <div class="rs-field">
              <span>Куда отправляем</span>
              <div class="rs-row rs-row--wrap">
                <label class="rs-check" :class="{ 'rs-check--off': !bound.telegram }">
                  <input type="checkbox" value="telegram" v-model="form.channels" :disabled="!bound.telegram" />
                  Telegram <small v-if="!bound.telegram">(не подключён)</small>
                </label>
                <label class="rs-check" :class="{ 'rs-check--off': !bound.max }">
                  <input type="checkbox" value="max" v-model="form.channels" :disabled="!bound.max" />
                  MAX <small v-if="!bound.max">(не подключён)</small>
                </label>
                <label class="rs-check rs-check--off" title="Почта временно недоступна">
                  <input type="checkbox" disabled />
                  Email <small>(временно недоступна)</small>
                </label>
              </div>
              <small v-if="!bound.telegram && !bound.max" class="rs-hint-warn">
                Подключите Telegram или MAX в блоке «Отчёты» на дашборде — без этого отправлять некуда.
              </small>
            </div>

            <div class="rs-field">
              <span>Когда</span>
              <div class="rs-row rs-row--wrap">
                <select v-model="form.day" class="rs-select">
                  <option value="daily">Ежедневно</option>
                  <option value="weekdays">По будням</option>
                  <option value="monday">Понедельник</option>
                  <option value="tuesday">Вторник</option>
                  <option value="wednesday">Среда</option>
                  <option value="thursday">Четверг</option>
                  <option value="friday">Пятница</option>
                  <option value="saturday">Суббота</option>
                  <option value="sunday">Воскресенье</option>
                </select>
                <input v-model="form.send_time" type="text" class="rs-time" inputmode="numeric" maxlength="5" placeholder="16:00" />
                <span class="rs-msk">МСК</span>
              </div>
            </div>

            <div class="rs-field">
              <span>Данные и формат</span>
              <div class="rs-row rs-row--wrap">
                <select v-model.number="form.period_days" class="rs-select">
                  <option :value="1">За вчера/сегодня (1 день)</option>
                  <option :value="7">За 7 дней</option>
                  <option :value="14">За 14 дней</option>
                  <option :value="30">За 30 дней</option>
                </select>
                <div class="rs-seg">
                  <button type="button" :class="{ active: form.report_format === 'desktop' }" @click="form.report_format = 'desktop'">🖥 Десктопный</button>
                  <button type="button" :class="{ active: form.report_format === 'mobile' }" @click="form.report_format = 'mobile'">📱 Мобильный</button>
                </div>
                <label class="rs-check">
                  <input type="checkbox" v-model="form.include_dynamics" />
                  Блок «Динамика»
                </label>
              </div>
            </div>

            <div class="rs-form-footer">
              <button type="button" class="rs-secondary" @click="editing = null">← Назад</button>
              <span class="rs-flex"></span>
              <button type="button" class="rs-primary" :disabled="saving || !form.channels.length" @click="saveRule">
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
const rules = ref([])
const folders = ref([])
const loading = ref(true)
const saving = ref(false)
const testingId = ref(null)
const editing = ref(null) // null | 'new' | rule.id
const form = ref(defaultForm())

const bound = computed(() => ({ telegram: props.telegramBound, max: props.maxBound }))

function defaultForm() {
  return {
    name: '',
    scope: 'all',
    platform: 'all',
    channels: [],
    day: 'daily',
    send_time: '10:00',
    period_days: 7,
    report_format: 'desktop',
    include_dynamics: false,
  }
}

const DAY_LABELS = {
  daily: 'Ежедневно', weekdays: 'По будням', monday: 'Пн', tuesday: 'Вт', wednesday: 'Ср',
  thursday: 'Чт', friday: 'Пт', saturday: 'Сб', sunday: 'Вс',
}
const dayLabel = (d) => DAY_LABELS[d] || d
const periodLabel = (n) => (Number(n) === 1 ? 'за день' : `за ${n} дн.`)
const channelName = (ch) => ({ telegram: 'Telegram', max: 'MAX', email: 'Email' }[ch] || ch)
const formatDateTime = (iso) => {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

async function load() {
  loading.value = true
  try {
    const [rulesRes, foldersRes] = await Promise.allSettled([
      api.get('reports/schedules'),
      api.get('folders/'),
    ])
    rules.value = rulesRes.status === 'fulfilled' ? (rulesRes.value.data || []) : []
    folders.value = foldersRes.status === 'fulfilled' ? (foldersRes.value.data || []) : []
  } finally {
    loading.value = false
  }
}

function openCreate() {
  form.value = defaultForm()
  // По умолчанию включаем первый подключённый канал
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
    day: rule.day || 'daily',
    send_time: rule.send_time || '10:00',
    period_days: Number(rule.period_days || 7),
    report_format: rule.report_format || 'desktop',
    include_dynamics: Boolean(rule.include_dynamics),
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
    day: form.value.day,
    send_time: /^\d{1,2}:\d{2}$/.test(time) ? time.padStart(5, '0') : '10:00',
    period_days: form.value.period_days,
    report_format: form.value.report_format,
    include_dynamics: form.value.include_dynamics,
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
.rs-backdrop {
  position: fixed; inset: 0; z-index: 95;
  display: flex; align-items: center; justify-content: center;
  background: rgba(15, 23, 42, 0.45); padding: 1rem;
}
.rs-modal {
  width: min(44rem, 96vw); max-height: 90vh; overflow-y: auto;
  background: #fff; border-radius: 1.1rem; padding: 1.4rem 1.6rem;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.3);
}
.rs-head { display: flex; align-items: flex-start; gap: 1rem; margin-bottom: 1.1rem; }
.rs-head h3 { margin: 0 0 0.3rem; font-size: 1.25rem; font-weight: 800; color: #171717; }
.rs-head p { margin: 0; font-size: 0.83rem; color: rgba(105,105,105,0.75); line-height: 1.45; }
.rs-close { margin-left: auto; border: none; background: none; font-size: 1rem; color: #94a3b8; cursor: pointer; padding: 0.2rem; }
.rs-close:hover { color: #171717; }

.rs-empty { padding: 2.2rem 0; text-align: center; color: rgba(105,105,105,0.65); font-size: 0.9rem; display: flex; flex-direction: column; gap: 0.3rem; }
.rs-empty strong { color: #444; }

.rs-list { display: flex; flex-direction: column; gap: 0.6rem; }
.rs-rule {
  display: flex; align-items: center; gap: 0.8rem;
  padding: 0.8rem 0.9rem; border-radius: 0.8rem;
  background: #f8fafc; box-shadow: inset 0 0 0 1px rgba(15,23,42,0.05);
}
.rs-rule--off { opacity: 0.55; }
.rs-rule-main { flex: 1; min-width: 0; cursor: pointer; display: flex; flex-direction: column; gap: 0.15rem; }
.rs-rule-main strong { font-size: 0.92rem; color: #171717; }
.rs-rule-meta { font-size: 0.76rem; color: rgba(105,105,105,0.75); }
.rs-rule-channels { display: flex; gap: 0.35rem; align-items: center; flex-wrap: wrap; }
.rs-chip {
  font-style: normal; font-size: 0.68rem; font-weight: 700;
  padding: 0.1rem 0.5rem; border-radius: 99px;
  background: rgba(37,99,235,0.1); color: #2563eb;
}
.rs-chip--max { background: rgba(124,58,237,0.1); color: #7c3aed; }
.rs-chip--email { background: rgba(5,150,105,0.1); color: #059669; }
.rs-last { font-style: normal; font-size: 0.68rem; color: #94a3b8; }
.rs-rule-actions { display: flex; gap: 0.35rem; flex-shrink: 0; }
.rs-mini {
  border: none; background: rgba(15,23,42,0.05); color: #444;
  font-size: 0.72rem; font-weight: 700; padding: 0.35rem 0.6rem;
  border-radius: 0.5rem; cursor: pointer;
}
.rs-mini:hover { background: rgba(37,99,235,0.1); color: #2563eb; }
.rs-mini--danger:hover { background: rgba(220,38,38,0.1); color: #dc2626; }
.rs-mini:disabled { opacity: 0.6; cursor: default; }

.rs-switch { position: relative; display: inline-block; width: 2.1rem; height: 1.2rem; flex-shrink: 0; }
.rs-switch input { display: none; }
.rs-switch i {
  position: absolute; inset: 0; border-radius: 99px; background: #cbd5e1;
  transition: background 0.15s ease; cursor: pointer;
}
.rs-switch i::after {
  content: ''; position: absolute; top: 0.15rem; left: 0.15rem;
  width: 0.9rem; height: 0.9rem; border-radius: 50%; background: #fff;
  transition: transform 0.15s ease;
}
.rs-switch input:checked + i { background: #2563eb; }
.rs-switch input:checked + i::after { transform: translateX(0.9rem); }

.rs-footer { display: flex; justify-content: flex-end; margin-top: 1rem; }
.rs-primary {
  border: none; background: #2563eb; color: #fff;
  padding: 0.55rem 1.1rem; border-radius: 0.65rem;
  font-weight: 700; font-size: 0.85rem; cursor: pointer;
}
.rs-primary:disabled { opacity: 0.55; cursor: default; }
.rs-secondary {
  border: none; background: rgba(15,23,42,0.06); color: #444;
  padding: 0.55rem 1rem; border-radius: 0.65rem;
  font-weight: 700; font-size: 0.85rem; cursor: pointer;
}

.rs-form { display: flex; flex-direction: column; gap: 1rem; }
.rs-field { display: flex; flex-direction: column; gap: 0.4rem; }
.rs-field > span { font-size: 0.78rem; font-weight: 700; color: #444; }
.rs-field input[type="text"] {
  padding: 0.5rem 0.75rem; border-radius: 0.6rem;
  border: 1px solid rgba(15,23,42,0.14); font-size: 0.88rem; outline: none;
}
.rs-field input[type="text"]:focus { border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37,99,235,0.12); }
.rs-row { display: flex; gap: 0.6rem; align-items: center; }
.rs-row--wrap { flex-wrap: wrap; }
.rs-select {
  padding: 0.5rem 0.7rem; border-radius: 0.6rem;
  border: 1px solid rgba(15,23,42,0.14); font-size: 0.85rem;
  background: #fff; color: #171717; max-width: 100%;
}
.rs-select--platform { min-width: 10rem; }
.rs-time {
  width: 5.2rem; text-align: center;
  padding: 0.5rem 0.4rem; border-radius: 0.6rem;
  border: 1px solid rgba(15,23,42,0.14); font-size: 0.88rem;
  font-variant-numeric: tabular-nums;
}
.rs-msk { font-size: 0.78rem; color: #94a3b8; font-weight: 600; }
.rs-check {
  display: inline-flex; align-items: center; gap: 0.45rem;
  font-size: 0.85rem; color: #171717; cursor: pointer;
  padding: 0.4rem 0.7rem; border-radius: 0.6rem; background: rgba(15,23,42,0.04);
}
.rs-check input { accent-color: #2563eb; }
.rs-check small { color: #94a3b8; font-size: 0.7rem; }
.rs-check--off { opacity: 0.6; cursor: default; }
.rs-hint-warn { color: #b45309; font-size: 0.75rem; }
.rs-seg { display: inline-flex; background: rgba(15,23,42,0.05); border-radius: 0.6rem; padding: 0.18rem; }
.rs-seg button {
  border: none; background: none; padding: 0.35rem 0.7rem;
  border-radius: 0.45rem; font-size: 0.8rem; font-weight: 700; color: #64748b; cursor: pointer;
}
.rs-seg button.active { background: #fff; color: #2563eb; box-shadow: 0 1px 4px rgba(15,23,42,0.12); }
.rs-form-footer { display: flex; align-items: center; gap: 0.6rem; margin-top: 0.4rem; }
.rs-flex { flex: 1; }
</style>
