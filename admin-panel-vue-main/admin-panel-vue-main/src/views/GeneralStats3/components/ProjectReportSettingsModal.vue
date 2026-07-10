<template>
  <Teleport to="body">
    <div class="rp-backdrop" @click.self="$emit('close')">
      <div class="rp-modal" :class="{ 'is-dark': isDarkMode }">
        <button type="button" class="rp-close" aria-label="Закрыть" @click="$emit('close')">
          <svg viewBox="0 0 14 14" fill="none"><path d="M2 2l10 10M12 2 2 12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
        </button>

        <h4>Настройки отчётов</h4>
        <p class="rp-hint">{{ settings.scope_label || title }} · каналы доставки и автоотправка этого проекта.</p>

        <div class="rp-tabs">
          <button type="button" :class="{ on: tab === 'channels' }" @click="tab = 'channels'">Каналы</button>
          <button type="button" :class="{ on: tab === 'auto' }" @click="tab = 'auto'">Автоотправка</button>
        </div>

        <div v-if="loading" class="rp-loading">Загружаем настройки…</div>

        <template v-else>
          <!-- ───── Вкладка «Каналы» ───── -->
          <div v-if="tab === 'channels'">
            <label class="rp-label">Личные каналы аккаунта</label>
            <p class="rp-sub">Куда отправлять отчёты лично вам. Привязка каналов — в профиле.</p>

            <div class="rp-capsules">
              <button
                v-for="ch in personalChannels"
                :key="ch.value"
                type="button"
                class="rp-capsule"
                :class="{ on: settings.channels.includes(ch.value), off: !ch.connected }"
                :title="ch.connected ? '' : 'Канал не привязан — подключите в профиле'"
                @click="toggleChannel(ch)"
              >
                <span class="rp-capsule__ic" :class="`rp-capsule__ic--${ch.value}`">
                  <svg v-if="ch.value === 'telegram'" viewBox="0 0 24 24" fill="none"><path d="M21.7 4.3c.3-1.1-.8-2-1.8-1.6L2.9 9.4c-1.1.4-1 2 .1 2.3l4.6 1.3 1.7 5.4c.3 1 1.6 1.3 2.3.5l2.4-2.6 4.7 3.4c.9.6 2.1.1 2.3-1l2.7-14.4ZM9.3 13.7l8.1-6.9-6.6 7.9-.2 2.4-1.3-3.4Z" fill="#fff"/></svg>
                  <svg v-else-if="ch.value === 'max'" viewBox="0 0 24 24" fill="none"><path d="M12 3.2c-4.9 0-8.8 3.4-8.8 7.7 0 2.4 1.2 4.5 3.1 5.9l-.7 3.5c-.1.4.4.8.8.6l3.7-1.8c.6.1 1.3.2 1.9.2 4.9 0 8.8-3.4 8.8-7.7S16.9 3.2 12 3.2Z" fill="#fff"/><path d="M8 10.7h8M8 13.4h5.2" stroke="#6C5CE7" stroke-width="1.6" stroke-linecap="round"/></svg>
                  <svg v-else viewBox="0 0 24 24" fill="none"><rect x="3" y="5.2" width="18" height="13.6" rx="2.4" fill="#fff"/><path d="m4.4 6.8 7.6 5.6 7.6-5.6" stroke="#8896AC" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>
                </span>
                <span class="rp-capsule__txt">
                  <strong>{{ ch.label }}</strong>
                  <small>{{ ch.connected ? (settings.channels.includes(ch.value) ? 'Включён' : 'Подключён') : 'Не подключён' }}</small>
                </span>
                <span class="rp-box rp-capsule__box">
                  <svg viewBox="0 0 12 10" fill="none"><path d="M1 5.2 4.4 8.6 11 1.4" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"/></svg>
                </span>
              </button>
            </div>

            <div class="rp-label-row">
              <label class="rp-label">Группы проекта</label>
              <button type="button" class="rp-mini-btn" :disabled="linkLoading" @click="createLink">
                {{ linkLoading ? 'Создаём…' : '+ Создать ссылку' }}
              </button>
            </div>
            <p class="rp-sub">Ссылка привязывает чат Telegram/MAX к этому проекту.</p>

            <div v-if="inviteLink" class="rp-invite">
              <span>{{ inviteLink }}</span>
              <button type="button" @click="copyInvite">Скопировать</button>
            </div>

            <div class="rp-list">
              <label
                v-for="target in settings.available_chat_targets"
                :key="target.id"
                class="rp-check"
                :class="{ on: settings.chat_targets.includes(target.id) }"
              >
                <input type="checkbox" :checked="settings.chat_targets.includes(target.id)" @change="toggleTarget(target.id)" />
                <span class="rp-box">
                  <svg viewBox="0 0 12 10" fill="none"><path d="M1 5.2 4.4 8.6 11 1.4" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"/></svg>
                </span>
                <span class="rp-check__name">{{ target.title || target.chat_id }}</span>
                <span class="rp-check__kind">{{ target.kind === 'max' ? 'MAX' : 'Telegram' }}</span>
              </label>
              <div v-if="!settings.available_chat_targets?.length" class="rp-empty">Группы ещё не привязаны</div>
            </div>
          </div>

          <!-- ───── Вкладка «Автоотправка» ───── -->
          <div v-else>
            <label class="rp-switch-row">
              <span class="rp-switch" :class="{ on: settings.enabled }">
                <input v-model="settings.enabled" type="checkbox" />
              </span>
              <span class="rp-switch-row__txt">
                <strong>Автоотправка включена</strong>
                <small>Отчёт формируется и отправляется по расписанию</small>
              </span>
            </label>

            <div class="rp-grid">
              <div class="rp-field">
                <label class="rp-label">День</label>
                <div class="rp-select" :class="{ open: openSelect === 'day' }" data-rp-select>
                  <button type="button" class="rp-select__head" @click="toggleSelect('day')">
                    <span>{{ optionLabel(dayOptions, settings.day) }}</span>
                    <span class="rp-select__arrow"><svg viewBox="0 0 10 6" fill="none"><path d="m1 1 4 4 4-4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg></span>
                  </button>
                  <div class="rp-select__list">
                    <button v-for="o in dayOptions" :key="o.value" type="button" :class="{ sel: settings.day === o.value }" @click="pick('day', o.value)">{{ o.label }}</button>
                  </div>
                </div>
              </div>

              <div class="rp-field">
                <label class="rp-label">Время по МСК</label>
                <input v-model="settings.send_time" type="time" class="rp-input" />
              </div>

              <div class="rp-field">
                <label class="rp-label">Период данных</label>
                <div class="rp-select" :class="{ open: openSelect === 'period' }" data-rp-select>
                  <button type="button" class="rp-select__head" @click="toggleSelect('period')">
                    <span>{{ optionLabel(periodOptions, settings.period_days) }}</span>
                    <span class="rp-select__arrow"><svg viewBox="0 0 10 6" fill="none"><path d="m1 1 4 4 4-4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg></span>
                  </button>
                  <div class="rp-select__list">
                    <button v-for="o in periodOptions" :key="o.value" type="button" :class="{ sel: settings.period_days === o.value }" @click="pick('period_days', o.value)">{{ o.label }}</button>
                  </div>
                </div>
              </div>

              <div class="rp-field">
                <label class="rp-label">Рекламный канал</label>
                <div class="rp-select" :class="{ open: openSelect === 'platform' }" data-rp-select>
                  <button type="button" class="rp-select__head" @click="toggleSelect('platform')">
                    <span>{{ optionLabel(platformOptions, settings.platform) }}</span>
                    <span class="rp-select__arrow"><svg viewBox="0 0 10 6" fill="none"><path d="m1 1 4 4 4-4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg></span>
                  </button>
                  <div class="rp-select__list">
                    <button v-for="o in platformOptions" :key="o.value" type="button" :class="{ sel: settings.platform === o.value }" @click="pick('platform', o.value)">{{ o.label }}</button>
                  </div>
                </div>
              </div>
            </div>

            <label class="rp-label">Формат</label>
            <div class="rp-pills">
              <button type="button" :class="{ on: settings.report_format === 'desktop' }" @click="settings.report_format = 'desktop'">Десктопный</button>
              <button type="button" :class="{ on: settings.report_format === 'mobile' }" @click="settings.report_format = 'mobile'">Мобильный</button>
            </div>

            <label class="rp-label">Состав отчёта</label>
            <div class="rp-tags">
              <button
                v-for="tag in sectionTags"
                :key="tag.value"
                type="button"
                class="rp-tag"
                :class="{ on: isSectionOn(tag) }"
                @click="toggleSection(tag)"
              >{{ tag.label }}</button>
            </div>

            <label class="rp-label">Режим отправки</label>
            <label class="rp-radio" :class="{ on: settings.approval_required }">
              <input type="radio" name="rp-approval" :value="true" v-model="settings.approval_required" />
              <span class="rp-dot"></span>
              <span class="rp-radio__txt">
                <strong>С проверкой <em>по умолчанию</em></strong>
                <small>Отчёт ждёт вашего одобрения в очереди</small>
              </span>
            </label>
            <label class="rp-radio" :class="{ on: !settings.approval_required }">
              <input type="radio" name="rp-approval" :value="false" v-model="settings.approval_required" />
              <span class="rp-dot"></span>
              <span class="rp-radio__txt">
                <strong>Без проверки</strong>
                <small>Уходит сам · при аномалии детектора всё равно ждёт вас</small>
              </span>
            </label>

            <label class="rp-check rp-check--plain" :class="{ on: settings.include_ai_comment }">
              <input v-model="settings.include_ai_comment" type="checkbox" />
              <span class="rp-box">
                <svg viewBox="0 0 12 10" fill="none"><path d="M1 5.2 4.4 8.6 11 1.4" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"/></svg>
              </span>
              <span class="rp-check__name">Включать AI-комментарий в авто-отчёт</span>
            </label>
          </div>
        </template>

        <div class="rp-footer">
          <span class="rp-flex1"></span>
          <button type="button" class="rp-cancel" @click="$emit('close')">Отмена</button>
          <button type="button" class="rp-save" :disabled="saving || loading" @click="save">
            {{ saving ? 'Сохраняем…' : 'Сохранить' }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import api from '@/api/axios'
import { useToaster } from '@/composables/useToaster'
import { useTheme } from '@/composables/useTheme'

const { isDarkMode } = useTheme()

const props = defineProps({
  clientId: { type: [String, null], default: null },
  folderId: { type: [String, null], default: null },
  title: { type: String, default: 'Текущий проект' },
})

const emit = defineEmits(['close', 'saved'])
const toaster = useToaster()
const loading = ref(false)
const saving = ref(false)
const linkLoading = ref(false)
const inviteLink = ref('')
const tab = ref('channels')
const openSelect = ref(null)

const settings = reactive({
  scope_label: '',
  connected_channels: [],
  available_chat_targets: [],
  enabled: false,
  platform: 'all',
  channels: [],
  chat_targets: [],
  day: 'daily',
  send_time: '10:00',
  period_days: 7,
  report_format: 'desktop',
  include_dynamics: false,
  approval_required: true,
  include_ai_comment: true,
  sections: ['kpi', 'chart', 'channels', 'campaigns'],
  chart_metrics: ['cost', 'clicks'],
  dynamics_metrics: ['cost'],
})

const dayOptions = [
  { value: 'daily', label: 'Ежедневно' },
  { value: 'weekdays', label: 'По будням' },
  { value: 'monday', label: 'Понедельник' },
  { value: 'friday', label: 'Пятница' },
]

const periodOptions = [
  { value: 1, label: '1 день' },
  { value: 7, label: '7 дней' },
  { value: 14, label: '14 дней' },
  { value: 30, label: '30 дней' },
]

const platformOptions = [
  { value: 'all', label: 'Все каналы' },
  { value: 'yandex', label: 'Яндекс Директ' },
  { value: 'vk', label: 'VK Реклама' },
  { value: 'avito', label: 'Avito Ads' },
]

const optionLabel = (options, value) => options.find((o) => o.value === value)?.label || String(value ?? '')

const toggleSelect = (key) => {
  openSelect.value = openSelect.value === key ? null : key
}

const pick = (field, value) => {
  settings[field] = value
  openSelect.value = null
}

const handleDocClick = (e) => {
  if (!openSelect.value) return
  if (!e.target.closest('[data-rp-select]')) openSelect.value = null
}

onMounted(() => document.addEventListener('mousedown', handleDocClick))
onBeforeUnmount(() => document.removeEventListener('mousedown', handleDocClick))

const params = computed(() => ({
  ...(props.clientId ? { client_id: props.clientId } : {}),
  ...(props.folderId ? { folder_id: props.folderId } : {}),
}))

const personalChannels = computed(() => [
  { value: 'telegram', label: 'Telegram', connected: settings.connected_channels.includes('telegram') },
  { value: 'max', label: 'MAX', connected: settings.connected_channels.includes('max') },
  { value: 'email', label: 'Email', connected: settings.connected_channels.includes('email') },
])

const toggleChannel = (ch) => {
  if (!ch.connected) return
  const idx = settings.channels.indexOf(ch.value)
  if (idx >= 0) settings.channels.splice(idx, 1)
  else settings.channels.push(ch.value)
}

const toggleTarget = (id) => {
  const idx = settings.chat_targets.indexOf(id)
  if (idx >= 0) settings.chat_targets.splice(idx, 1)
  else settings.chat_targets.push(id)
}

// Состав отчёта: секции + отдельный флаг «Динамика» (include_dynamics)
const sectionTags = [
  { value: 'kpi', label: 'KPI-карточки' },
  { value: 'chart', label: 'Графики' },
  { value: 'channels', label: 'Каналы' },
  { value: 'campaigns', label: 'Кампании' },
  { value: 'dynamics', label: 'Динамика', dynamics: true },
]

const isSectionOn = (tag) => (
  tag.dynamics ? Boolean(settings.include_dynamics) : (settings.sections || []).includes(tag.value)
)

const toggleSection = (tag) => {
  if (tag.dynamics) {
    settings.include_dynamics = !settings.include_dynamics
    return
  }
  const list = Array.isArray(settings.sections) ? [...settings.sections] : []
  const idx = list.indexOf(tag.value)
  if (idx >= 0) list.splice(idx, 1)
  else list.push(tag.value)
  settings.sections = list
}

const applySettings = (data = {}) => {
  Object.assign(settings, {
    scope_label: data.scope_label || '',
    connected_channels: data.connected_channels || [],
    available_chat_targets: data.available_chat_targets || [],
    enabled: Boolean(data.enabled),
    platform: data.platform || 'all',
    channels: Array.isArray(data.channels) ? data.channels : [],
    chat_targets: Array.isArray(data.chat_targets) ? data.chat_targets : [],
    day: data.day || 'daily',
    send_time: data.send_time || '10:00',
    period_days: Number(data.period_days || 7),
    report_format: data.report_format || 'desktop',
    include_dynamics: Boolean(data.include_dynamics),
    approval_required: data.approval_required !== false,
    include_ai_comment: data.include_ai_comment !== false,
    sections: data.sections || ['kpi', 'chart', 'channels', 'campaigns'],
    chart_metrics: data.chart_metrics || ['cost', 'clicks'],
    dynamics_metrics: data.dynamics_metrics || ['cost'],
  })
}

const load = async () => {
  loading.value = true
  try {
    const { data } = await api.get('reports/project-settings', { params: params.value })
    applySettings(data)
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Не удалось загрузить настройки')
  } finally {
    loading.value = false
  }
}

const save = async () => {
  saving.value = true
  try {
    const { data } = await api.put('reports/project-settings', {
      enabled: settings.enabled,
      platform: settings.platform,
      channels: settings.channels,
      chat_targets: settings.chat_targets,
      day: settings.day,
      send_time: settings.send_time,
      period_days: settings.period_days,
      report_format: settings.report_format,
      include_dynamics: settings.include_dynamics,
      approval_required: settings.approval_required,
      include_ai_comment: settings.include_ai_comment,
      sections: settings.sections,
      chart_metrics: settings.chart_metrics,
      dynamics_metrics: settings.dynamics_metrics,
    }, { params: params.value })
    applySettings(data)
    toaster.success('Настройки отчёта сохранены')
    emit('saved', data)
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Не удалось сохранить настройки')
  } finally {
    saving.value = false
  }
}

const createLink = async () => {
  linkLoading.value = true
  try {
    const { data } = await api.post('reports/chat-targets/link-code', { kind: 'telegram' }, { params: params.value })
    const path = data?.group_link || data?.telegram_url || data?.url || data?.code
    inviteLink.value = path ? String(path) : ''
    if (!inviteLink.value) throw new Error('empty link')
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Не удалось создать ссылку')
  } finally {
    linkLoading.value = false
  }
}

const copyInvite = async () => {
  try {
    await navigator.clipboard.writeText(inviteLink.value)
    toaster.success('Ссылка скопирована')
  } catch {
    toaster.error('Не удалось скопировать ссылку')
  }
}

watch(() => [props.clientId, props.folderId], load, { immediate: true })
</script>

<style scoped>
/* Стиль модалки папок (ProjectCard.vue) — компактная шкала, те же радиусы/кнопки */
.rp-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1190;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(15, 23, 42, 0.45);
  padding: 1rem;
}

.rp-modal {
  position: relative;
  width: min(38rem, 94vw);
  max-height: 90vh;
  overflow-y: auto;
  background: #fff;
  border-radius: 1.3rem;
  padding: 1.8rem 1.9rem 1.6rem;
  box-shadow: 0 32px 80px rgba(9, 24, 63, 0.32);
}

.rp-modal.is-dark {
  background: #252838;
  box-shadow: 0 32px 80px rgba(0, 0, 0, 0.5);
}

.rp-close {
  position: absolute;
  top: 1.05rem;
  right: 1.05rem;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border: 0;
  border-radius: 999px;
  background: #f3f5f7;
  color: #697586;
  cursor: pointer;
}

.rp-close svg { width: 0.85rem; height: 0.85rem; }

.rp-modal.is-dark .rp-close {
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.72);
}

.rp-modal h4 {
  margin: 0 0 0.45rem;
  font-size: 1.45rem;
  font-weight: 800;
  color: #171717;
  letter-spacing: -0.01em;
}

.rp-modal.is-dark h4 { color: #f8fafc; }

.rp-hint {
  margin: 0 0 1.15rem;
  font-size: 0.95rem;
  color: rgba(105, 105, 105, 0.75);
  line-height: 1.5;
}

.rp-modal.is-dark .rp-hint { color: rgba(255, 255, 255, 0.48); }

.rp-tabs {
  display: inline-flex;
  background: #f2f5f9;
  border-radius: 0.8rem;
  padding: 0.28rem;
  gap: 0.2rem;
  margin-bottom: 0.4rem;
}

.rp-modal.is-dark .rp-tabs { background: rgba(255, 255, 255, 0.06); }

.rp-tabs button {
  padding: 0.5rem 1.3rem;
  border: 0;
  border-radius: 0.6rem;
  background: transparent;
  color: #64748b;
  font-size: 0.95rem;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.13s, color 0.13s;
}

.rp-tabs button.on {
  background: #fff;
  color: #2563eb;
  box-shadow: 0 1px 4px rgba(20, 30, 55, 0.12);
}

.rp-modal.is-dark .rp-tabs button { color: rgba(255, 255, 255, 0.55); }
.rp-modal.is-dark .rp-tabs button.on {
  background: rgba(74, 122, 255, 0.22);
  color: #8fb0ff;
  box-shadow: none;
}

.rp-loading {
  padding: 1.2rem 0;
  font-size: 0.95rem;
  color: rgba(105, 105, 105, 0.7);
}

.rp-label {
  display: block;
  margin: 1.1rem 0 0.45rem;
  font-size: 0.9rem;
  font-weight: 800;
  color: #333;
}

.rp-modal.is-dark .rp-label { color: rgba(255, 255, 255, 0.82); }

.rp-sub {
  margin: -0.15rem 0 0.55rem;
  font-size: 0.82rem;
  color: rgba(105, 105, 105, 0.62);
}

.rp-modal.is-dark .rp-sub { color: rgba(255, 255, 255, 0.4); }

.rp-label-row {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 0.7rem;
  margin-top: 1.3rem;
}

.rp-label-row .rp-label { margin: 0; }

.rp-mini-btn {
  border: 0;
  background: rgba(37, 99, 235, 0.08);
  color: #2563eb;
  padding: 0.4rem 0.85rem;
  border-radius: 0.6rem;
  font-size: 0.85rem;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.13s;
}

.rp-mini-btn:hover:not(:disabled) { background: rgba(37, 99, 235, 0.14); }
.rp-mini-btn:disabled { opacity: 0.6; cursor: default; }

/* ── Капсулы личных каналов ── */
.rp-capsules {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.55rem;
}

.rp-capsule {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.62rem 0.7rem;
  border: 1.5px solid rgba(15, 23, 42, 0.1);
  border-radius: 0.85rem;
  background: #fff;
  cursor: pointer;
  text-align: left;
  transition: border-color 0.13s, background 0.13s;
}

.rp-capsule:hover:not(.off) { border-color: rgba(37, 99, 235, 0.45); }

.rp-capsule.on {
  border-color: #2563eb;
  background: rgba(37, 99, 235, 0.06);
}

.rp-capsule.off {
  opacity: 0.55;
  border-style: dashed;
  cursor: default;
}

.rp-modal.is-dark .rp-capsule {
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(255, 255, 255, 0.12);
}

.rp-modal.is-dark .rp-capsule.on {
  border-color: #6f9bff;
  background: rgba(74, 122, 255, 0.14);
}

.rp-capsule__ic {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.1rem;
  height: 2.1rem;
  border-radius: 0.65rem;
  flex-shrink: 0;
}

.rp-capsule__ic svg { width: 1.25rem; height: 1.25rem; }
.rp-capsule__ic--telegram { background: #2aa5e0; }
.rp-capsule__ic--max { background: #6c5ce7; }
.rp-capsule__ic--email { background: #8896ac; }

.rp-capsule__txt {
  display: grid;
  gap: 0.05rem;
  min-width: 0;
  flex: 1;
}

.rp-capsule__txt strong {
  font-size: 0.92rem;
  font-weight: 750;
  color: #171717;
  line-height: 1.2;
}

.rp-modal.is-dark .rp-capsule__txt strong { color: #f1f5f9; }

.rp-capsule__txt small {
  font-size: 0.74rem;
  color: rgba(105, 105, 105, 0.65);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.rp-capsule.on .rp-capsule__txt small { color: #2563eb; }
.rp-modal.is-dark .rp-capsule__txt small { color: rgba(255, 255, 255, 0.42); }
.rp-modal.is-dark .rp-capsule.on .rp-capsule__txt small { color: #8fb0ff; }

.rp-capsule__box { margin-left: auto; }
.rp-capsule.off .rp-capsule__box { visibility: hidden; }

/* ── Кастомный чекбокс (fp-box из модалки папок) ── */
.rp-box {
  width: 1.15rem;
  height: 1.15rem;
  border-radius: 0.35rem;
  border: 1.5px solid rgba(15, 23, 42, 0.25);
  background: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
  transition: background 0.13s, border-color 0.13s;
}

.rp-box svg { width: 0.7rem; height: 0.6rem; opacity: 0; }

.rp-capsule.on .rp-box,
.rp-check.on .rp-box {
  background: #2563eb;
  border-color: #2563eb;
}

.rp-capsule.on .rp-box svg,
.rp-check.on .rp-box svg { opacity: 1; }

.rp-modal.is-dark .rp-box {
  background: transparent;
  border-color: rgba(255, 255, 255, 0.3);
}

.rp-modal.is-dark .rp-capsule.on .rp-box,
.rp-modal.is-dark .rp-check.on .rp-box {
  background: #4a7aff;
  border-color: #4a7aff;
}

/* ── Список групп ── */
.rp-list {
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 0.8rem;
  padding: 0.4rem;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  max-height: 12rem;
  overflow-y: auto;
}

.rp-modal.is-dark .rp-list { border-color: rgba(255, 255, 255, 0.1); }

.rp-check {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding: 0.6rem 0.7rem;
  border-radius: 0.6rem;
  font-size: 0.95rem;
  font-weight: 600;
  color: #171717;
  cursor: pointer;
  transition: background 0.12s;
}

.rp-check:hover { background: rgba(37, 99, 235, 0.06); }
.rp-check.on { background: rgba(37, 99, 235, 0.07); }
.rp-check input { display: none; }

.rp-modal.is-dark .rp-check { color: #e6ebf3; }
.rp-modal.is-dark .rp-check:hover { background: rgba(74, 122, 255, 0.1); }
.rp-modal.is-dark .rp-check.on { background: rgba(74, 122, 255, 0.12); }

.rp-check--plain {
  margin-top: 0.55rem;
  padding: 0.45rem 0.2rem;
  font-size: 0.92rem;
}

.rp-check--plain:hover,
.rp-check--plain.on { background: transparent; }

.rp-check__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rp-check__kind {
  margin-left: auto;
  font-size: 0.78rem;
  font-weight: 700;
  color: rgba(105, 105, 105, 0.6);
}

.rp-modal.is-dark .rp-check__kind { color: rgba(255, 255, 255, 0.4); }

.rp-empty {
  padding: 0.9rem 0.7rem;
  font-size: 0.9rem;
  color: rgba(105, 105, 105, 0.6);
}

.rp-invite {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  margin: 0 0 0.55rem;
  padding: 0.55rem 0.75rem;
  border-radius: 0.7rem;
  background: rgba(37, 99, 235, 0.07);
  color: #1d4ed8;
  font-size: 0.88rem;
  font-weight: 600;
}

.rp-invite span {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rp-invite button {
  border: 0;
  background: #2563eb;
  color: #fff;
  padding: 0.4rem 0.85rem;
  border-radius: 0.55rem;
  font-size: 0.82rem;
  font-weight: 700;
  cursor: pointer;
}

.rp-modal.is-dark .rp-invite { background: rgba(74, 122, 255, 0.14); color: #a9c4ff; }

/* ── Переключатель автоотправки ── */
.rp-switch-row {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  padding: 0.75rem 0.85rem;
  margin-top: 1rem;
  border-radius: 0.85rem;
  background: #f7f9fc;
  cursor: pointer;
}

.rp-modal.is-dark .rp-switch-row { background: rgba(255, 255, 255, 0.04); }

.rp-switch {
  position: relative;
  width: 2.5rem;
  height: 1.4rem;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.18);
  flex-shrink: 0;
  transition: background 0.15s;
}

.rp-switch.on { background: #2563eb; }
.rp-switch input { display: none; }

.rp-switch::after {
  content: '';
  position: absolute;
  top: 0.14rem;
  left: 0.14rem;
  width: 1.12rem;
  height: 1.12rem;
  border-radius: 50%;
  background: #fff;
  transition: transform 0.16s ease;
}

.rp-switch.on::after { transform: translateX(1.1rem); }

.rp-switch-row__txt { display: grid; gap: 0.05rem; }

.rp-switch-row__txt strong {
  font-size: 0.95rem;
  font-weight: 750;
  color: #171717;
}

.rp-modal.is-dark .rp-switch-row__txt strong { color: #f1f5f9; }

.rp-switch-row__txt small {
  font-size: 0.8rem;
  color: rgba(105, 105, 105, 0.65);
}

.rp-modal.is-dark .rp-switch-row__txt small { color: rgba(255, 255, 255, 0.42); }

/* ── Сетка полей и кастомный селект ── */
.rp-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 0.8rem;
}

.rp-field { min-width: 0; }

.rp-input {
  width: 100%;
  height: 2.9rem;
  padding: 0 0.95rem;
  border-radius: 0.75rem;
  border: 1px solid rgba(15, 23, 42, 0.12);
  font-size: 0.98rem;
  font-weight: 600;
  color: #171717;
  background: #fff;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.13s ease, box-shadow 0.13s ease;
}

.rp-input:focus { border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12); }

.rp-modal.is-dark .rp-input {
  background: rgba(0, 0, 0, 0.2);
  border-color: rgba(255, 255, 255, 0.14);
  color: #f1f5f9;
}

.rp-select { position: relative; }

.rp-select__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.7rem;
  width: 100%;
  height: 2.9rem;
  padding: 0 0.6rem 0 0.95rem;
  border-radius: 0.75rem;
  border: 1px solid rgba(15, 23, 42, 0.12);
  background: #fff;
  font-size: 0.98rem;
  font-weight: 600;
  color: #171717;
  cursor: pointer;
  transition: border-color 0.13s ease, box-shadow 0.13s ease;
}

.rp-select.open .rp-select__head {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.rp-modal.is-dark .rp-select__head {
  background: rgba(0, 0, 0, 0.2);
  border-color: rgba(255, 255, 255, 0.14);
  color: #f1f5f9;
}

.rp-select__head span:first-child {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rp-select__arrow {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 999px;
  background: #f5f7f9;
  color: #8a93a3;
  flex-shrink: 0;
  transition: transform 0.2s;
}

.rp-select__arrow svg { width: 0.65rem; height: 0.42rem; }
.rp-select.open .rp-select__arrow { transform: rotate(180deg); }

.rp-modal.is-dark .rp-select__arrow {
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.6);
}

.rp-select__list {
  position: absolute;
  top: calc(100% + 0.3rem);
  left: 0;
  right: 0;
  z-index: 20;
  display: flex;
  flex-direction: column;
  padding: 0.3rem;
  border-radius: 0.7rem;
  background: #fff;
  box-shadow: 0 0 0 1px rgba(68, 68, 68, 0.1), 0 12px 32px rgba(15, 23, 42, 0.14);
  opacity: 0;
  pointer-events: none;
  transform: scale(0.92) translateY(-0.4rem);
  transform-origin: 50% 0;
  transition: transform 0.16s ease, opacity 0.13s ease;
}

.rp-select.open .rp-select__list {
  opacity: 1;
  pointer-events: auto;
  transform: scale(1) translateY(0);
}

.rp-modal.is-dark .rp-select__list {
  background: #2c2f42;
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.1), 0 12px 32px rgba(0, 0, 0, 0.45);
}

.rp-select__list button {
  border: 0;
  background: transparent;
  text-align: left;
  padding: 0.55rem 0.8rem;
  border-radius: 0.5rem;
  font-size: 0.95rem;
  font-weight: 600;
  color: #333;
  cursor: pointer;
  transition: background 0.12s;
}

.rp-select__list button:hover { background: #f5f7f9; }
.rp-select__list button.sel { color: #2563eb; font-weight: 750; }

.rp-modal.is-dark .rp-select__list button { color: rgba(255, 255, 255, 0.78); }
.rp-modal.is-dark .rp-select__list button:hover { background: rgba(255, 255, 255, 0.07); }
.rp-modal.is-dark .rp-select__list button.sel { color: #8fb0ff; }

/* ── Формат: пара пилюль ── */
.rp-pills {
  display: inline-flex;
  background: #f2f5f9;
  border-radius: 0.8rem;
  padding: 0.28rem;
  gap: 0.2rem;
}

.rp-modal.is-dark .rp-pills { background: rgba(255, 255, 255, 0.06); }

.rp-pills button {
  padding: 0.45rem 1.15rem;
  border: 0;
  border-radius: 0.6rem;
  background: transparent;
  color: #64748b;
  font-size: 0.92rem;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.13s, color 0.13s;
}

.rp-pills button.on {
  background: #fff;
  color: #2563eb;
  box-shadow: 0 1px 4px rgba(20, 30, 55, 0.12);
}

.rp-modal.is-dark .rp-pills button { color: rgba(255, 255, 255, 0.55); }
.rp-modal.is-dark .rp-pills button.on {
  background: rgba(74, 122, 255, 0.22);
  color: #8fb0ff;
  box-shadow: none;
}

/* ── Теги состава ── */
.rp-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}

.rp-tag {
  padding: 0.42rem 1rem;
  border-radius: 999px;
  border: 1.5px solid rgba(15, 23, 42, 0.14);
  background: #fff;
  color: #64748b;
  font-size: 0.9rem;
  font-weight: 650;
  cursor: pointer;
  transition: border-color 0.13s, background 0.13s, color 0.13s;
}

.rp-tag:hover { border-color: rgba(37, 99, 235, 0.4); }

.rp-tag.on {
  border-color: #2563eb;
  background: rgba(37, 99, 235, 0.07);
  color: #2563eb;
  font-weight: 750;
}

.rp-modal.is-dark .rp-tag {
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(255, 255, 255, 0.14);
  color: rgba(255, 255, 255, 0.6);
}

.rp-modal.is-dark .rp-tag.on {
  border-color: #6f9bff;
  background: rgba(74, 122, 255, 0.14);
  color: #8fb0ff;
}

/* ── Радио режима отправки ── */
.rp-radio {
  display: flex;
  align-items: flex-start;
  gap: 0.65rem;
  padding: 0.7rem 0.8rem;
  border-radius: 0.85rem;
  border: 1.5px solid rgba(15, 23, 42, 0.08);
  background: #fff;
  cursor: pointer;
  margin-bottom: 0.5rem;
  transition: border-color 0.13s, background 0.13s;
}

.rp-radio.on {
  border-color: rgba(37, 99, 235, 0.55);
  background: rgba(37, 99, 235, 0.05);
}

.rp-radio input { display: none; }

.rp-modal.is-dark .rp-radio {
  background: rgba(255, 255, 255, 0.03);
  border-color: rgba(255, 255, 255, 0.1);
}

.rp-modal.is-dark .rp-radio.on {
  border-color: rgba(111, 155, 255, 0.6);
  background: rgba(74, 122, 255, 0.1);
}

.rp-dot {
  width: 1.15rem;
  height: 1.15rem;
  border-radius: 50%;
  border: 1.5px solid rgba(15, 23, 42, 0.25);
  background: #fff;
  flex-shrink: 0;
  margin-top: 0.1rem;
  transition: border 0.13s;
}

.rp-radio.on .rp-dot { border: 0.36rem solid #2563eb; }

.rp-modal.is-dark .rp-dot {
  background: transparent;
  border-color: rgba(255, 255, 255, 0.3);
}

.rp-modal.is-dark .rp-radio.on .rp-dot { border-color: #4a7aff; }

.rp-radio__txt { display: grid; gap: 0.1rem; min-width: 0; }

.rp-radio__txt strong {
  font-size: 0.95rem;
  font-weight: 750;
  color: #171717;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.rp-modal.is-dark .rp-radio__txt strong { color: #f1f5f9; }

.rp-radio__txt strong em {
  font-style: normal;
  font-size: 0.72rem;
  font-weight: 750;
  color: #1e4fc0;
  background: rgba(37, 99, 235, 0.1);
  border-radius: 0.5rem;
  padding: 0.12rem 0.55rem;
}

.rp-modal.is-dark .rp-radio__txt strong em {
  color: #8fb0ff;
  background: rgba(74, 122, 255, 0.2);
}

.rp-radio__txt small {
  font-size: 0.8rem;
  color: rgba(105, 105, 105, 0.68);
  line-height: 1.4;
}

.rp-modal.is-dark .rp-radio__txt small { color: rgba(255, 255, 255, 0.42); }

/* ── Футер ── */
.rp-footer {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  margin-top: 1.5rem;
}

.rp-flex1 { flex: 1; }

.rp-cancel {
  border: none;
  background: rgba(15, 23, 42, 0.06);
  color: #444;
  padding: 0.65rem 1.2rem;
  border-radius: 0.75rem;
  font-weight: 700;
  font-size: 0.95rem;
  cursor: pointer;
  transition: background 0.13s;
}

.rp-cancel:hover { background: rgba(15, 23, 42, 0.1); }

.rp-modal.is-dark .rp-cancel {
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.75);
}

.rp-save {
  border: none;
  background: #2563eb;
  color: #fff;
  padding: 0.65rem 1.35rem;
  border-radius: 0.75rem;
  font-weight: 700;
  font-size: 0.95rem;
  cursor: pointer;
  transition: background 0.13s ease, box-shadow 0.13s ease;
}

.rp-save:hover:not(:disabled) { background: #1d4ed8; box-shadow: 0 6px 18px rgba(37, 99, 235, 0.35); }
.rp-save:disabled { opacity: 0.6; cursor: default; }

@media (max-width: 620px) {
  .rp-capsules { grid-template-columns: 1fr; }
  .rp-grid { grid-template-columns: 1fr; }
}
</style>
