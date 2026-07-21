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
            <div class="rp-label-row">
              <div>
                <label class="rp-label">Получатели проекта</label>
                <p class="rp-sub">Они доступны только для этого проекта. Выбор автоотправки — на соседней вкладке.</p>
              </div>
              <div class="rp-recipient-menu" data-recipient-menu>
                <button type="button" class="rp-mini-btn" @click="toggleRecipientMenu($event)">+ Добавить получателя</button>
                <Teleport to="body">
                  <div v-if="recipientMenuOpen" class="rp-recipient-menu__list rp-recipient-menu__list--float" :class="{ 'is-dark': isDarkMode }" :style="recipientMenuStyle" data-recipient-menu>
                    <button type="button" :disabled="linkLoading" @click="startLink('telegram', 'group')">Группа Telegram</button>
                    <button type="button" :disabled="linkLoading" @click="startLink('max', 'group')">Группа MAX</button>
                    <button type="button" :disabled="linkLoading" @click="startLink('telegram', 'client')">Личный чат клиента · TG</button>
                    <button type="button" :disabled="linkLoading" @click="startLink('max', 'client')">Личный чат клиента · MAX</button>
                    <button type="button" @click="showEmailInput = true; recipientMenuOpen = false">Email</button>
                  </div>
                </Teleport>
              </div>
            </div>

            <div v-if="showEmailInput" class="rp-email-add">
              <input v-model.trim="newEmail" class="rp-input" type="email" placeholder="client@example.ru" @keyup.enter="addEmail" />
              <button type="button" class="rp-mini-btn" @click="addEmail">Добавить</button>
            </div>

            <div v-if="inviteLink" class="rp-invite">
              <span>{{ inviteLink }}</span>
              <button type="button" @click="copyInvite">Скопировать</button>
            </div>
            <p v-if="inviteInstruction" class="rp-sub rp-invite-instruction">{{ inviteInstruction }}</p>

            <div class="rp-list rp-recipient-list">
              <div v-for="target in settings.available_chat_targets" :key="target.id" class="rp-check on" :class="{ 'rp-check--unavailable': target.status === 'unavailable' }">
                <span class="rp-capsule__ic" :class="`rp-capsule__ic--${target.kind}`">{{ target.kind === 'max' ? 'M' : 'T' }}</span>
                <span class="rp-check__name">{{ target.title || target.chat_id }}<small>{{ target.kind === 'max' ? 'MAX' : 'Telegram' }} · {{ target.target_type === 'client' ? 'личный чат клиента' : 'группа' }}</small></span>
                <span class="rp-recipient-status">{{ target.status === 'unavailable' ? 'Временно недоступен' : 'Активен' }}</span>
                <button type="button" class="rp-target-unlink" @click="unlinkTarget(target)">Отвязать</button>
              </div>
              <div v-for="email in settings.available_email_recipients" :key="email.id" class="rp-check on" :class="{ 'rp-check--unavailable': email.status === 'unavailable' }">
                <span class="rp-capsule__ic rp-capsule__ic--email">@</span>
                <span class="rp-check__name">{{ email.title || email.email }}<small>{{ email.email }}</small></span>
                <span class="rp-recipient-status">{{ email.status === 'unavailable' ? 'Временно недоступен' : 'Активен' }}</span>
                <button type="button" class="rp-target-unlink" @click="removeEmail(email)">Отвязать</button>
              </div>
              <div v-if="!settings.available_chat_targets?.length && !settings.available_email_recipients?.length" class="rp-empty">Получатели ещё не добавлены</div>
            </div>
          </div>

          <!-- ───── Вкладка «Автоотправка» ───── -->
          <div v-else>
            <label class="rp-switch-row">
              <span class="rp-switch" :class="{ on: settings.enabled }">
                <input v-model="settings.enabled" type="checkbox" />
              </span>
              <span class="rp-switch-row__txt">
                <strong>{{ settings.enabled ? 'Автоотправка включена' : 'Автоотправка выключена' }}</strong>
                <small>Отчёт формируется и отправляется по расписанию</small>
              </span>
            </label>

            <div class="rp-label-row">
              <label class="rp-label">Куда</label>
            </div>
            <p class="rp-sub">Отметьте адресные каналы, которые получат этот автоматический отчёт.</p>
            <div class="rp-list rp-auto-recipients">
              <label v-for="ch in personalChannels" :key="ch.value" class="rp-check" :class="{ on: settings.channels.includes(ch.value), 'rp-check--unavailable': !ch.connected }">
                <input v-if="ch.connected" v-model="settings.channels" type="checkbox" :value="ch.value" />
                <span v-if="ch.connected" class="rp-box"><svg viewBox="0 0 12 10" fill="none"><path d="M1 5.2 4.4 8.6 11 1.4" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"/></svg></span>
                <span class="rp-check__name">{{ ch.label }} — мне лично<small>{{ ch.connected ? 'Только этот проект' : 'Канал не привязан' }}</small></span>
                <button v-if="!ch.connected" type="button" class="rp-mini-btn" @click.prevent="emit('link-personal', ch.value)">Привязать</button>
              </label>
              <label v-for="target in settings.available_chat_targets" :key="target.id" class="rp-check" :class="{ on: settings.chat_targets.includes(target.id), 'rp-check--unavailable': target.status === 'unavailable' }">
                <input v-model="settings.chat_targets" type="checkbox" :value="target.id" :disabled="target.status === 'unavailable'" />
                <span class="rp-box"><svg viewBox="0 0 12 10" fill="none"><path d="M1 5.2 4.4 8.6 11 1.4" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"/></svg></span>
                <span class="rp-check__name">{{ target.title || target.chat_id }}<small>{{ target.status === 'unavailable' ? 'Временно недоступен' : (target.kind === 'max' ? 'MAX' : 'Telegram') }}</small></span>
              </label>
              <label v-for="email in settings.available_email_recipients" :key="email.id" class="rp-check" :class="{ on: settings.email_recipients.includes(email.email), 'rp-check--unavailable': email.status === 'unavailable' }">
                <input v-model="settings.email_recipients" type="checkbox" :value="email.email" :disabled="email.status === 'unavailable'" @change="syncEmailChannel" />
                <span class="rp-box"><svg viewBox="0 0 12 10" fill="none"><path d="M1 5.2 4.4 8.6 11 1.4" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"/></svg></span>
                <span class="rp-check__name">{{ email.title || email.email }}<small>{{ email.status === 'unavailable' ? 'Временно недоступен' : email.email }}</small></span>
              </label>
            </div>

            <div class="rp-grid">
              <div class="rp-field">
                <label class="rp-label">День</label>
                <div class="rp-select" :class="{ open: openSelect === 'day' }" data-rp-select>
                  <button type="button" class="rp-select__head" @click="toggleSelect('day', $event)">
                    <span>{{ optionLabel(dayOptions, settings.day) }}</span>
                    <span class="rp-select__arrow"><svg viewBox="0 0 10 6" fill="none"><path d="m1 1 4 4 4-4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg></span>
                  </button>
                  <Teleport to="body">
                    <div v-if="openSelect === 'day'" class="rp-select__list rp-select__list--float" :class="{ 'is-dark': isDarkMode }" :style="selectStyle" data-rp-select>
                      <button v-for="o in dayOptions" :key="o.value" type="button" :class="{ sel: settings.day === o.value }" @click="pick('day', o.value)">{{ o.label }}</button>
                    </div>
                  </Teleport>
                </div>
              </div>

              <div class="rp-field">
                <label class="rp-label">Время по МСК</label>
                <input v-model="settings.send_time" type="time" class="rp-input" />
              </div>

              <div class="rp-field">
                <label class="rp-label">Период данных</label>
                <div class="rp-select" :class="{ open: openSelect === 'period' }" data-rp-select>
                  <button type="button" class="rp-select__head" @click="toggleSelect('period', $event)">
                    <span>{{ optionLabel(periodOptions, settings.period_days) }}</span>
                    <span class="rp-select__arrow"><svg viewBox="0 0 10 6" fill="none"><path d="m1 1 4 4 4-4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg></span>
                  </button>
                  <Teleport to="body">
                    <div v-if="openSelect === 'period'" class="rp-select__list rp-select__list--float" :class="{ 'is-dark': isDarkMode }" :style="selectStyle" data-rp-select>
                      <button v-for="o in periodOptions" :key="o.value" type="button" :class="{ sel: settings.period_days === o.value }" @click="pick('period_days', o.value)">{{ o.label }}</button>
                    </div>
                  </Teleport>
                </div>
              </div>

              <div class="rp-field">
                <label class="rp-label">Шаблон</label>
                <div class="rp-select" :class="{ open: openSelect === 'platform' }" data-rp-select>
                  <button type="button" class="rp-select__head" @click="toggleSelect('platform', $event)">
                    <span>{{ optionLabel(platformOptions, settings.platform) }}</span>
                    <span class="rp-select__arrow"><svg viewBox="0 0 10 6" fill="none"><path d="m1 1 4 4 4-4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg></span>
                  </button>
                  <Teleport to="body">
                    <div v-if="openSelect === 'platform'" class="rp-select__list rp-select__list--float" :class="{ 'is-dark': isDarkMode }" :style="selectStyle" data-rp-select>
                      <button v-for="o in platformOptions" :key="o.value" type="button" :class="{ sel: settings.platform === o.value }" @click="pick('platform', o.value)">{{ o.label }}</button>
                    </div>
                  </Teleport>
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
                :class="{ on: isSectionOn(tag), disabled: tag.dynamics }"
                :disabled="tag.dynamics"
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

        <div v-if="tab === 'auto'" class="rp-footer">
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

const emit = defineEmits(['close', 'saved', 'link-personal'])
const toaster = useToaster()
const loading = ref(false)
const saving = ref(false)
const linkLoading = ref(false)
const inviteLink = ref('')
const inviteInstruction = ref('')
const newEmail = ref('')
const recipientMenuOpen = ref(false)
const showEmailInput = ref(false)
let invitePollTimer = null
let inviteBaselineIds = new Set()
const tab = ref('channels')
const openSelect = ref(null)

const settings = reactive({
  scope_label: '',
  connected_channels: [],
  available_chat_targets: [],
  available_email_recipients: [],
  enabled: false,
  platform: 'all',
  channels: [],
  email_recipients: [],
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

// Список опций рендерим телепортом в body с fixed-позицией: внутри модалки
// с overflow-y:auto абсолютный дропдаун распирал прокрутку и создавал
// неудобный скролл. Позицию берём из прямоугольника кнопки-заголовка.
const selectStyle = ref({})

const positionSelect = (headEl) => {
  const r = headEl.getBoundingClientRect()
  selectStyle.value = {
    position: 'fixed',
    top: `${r.bottom + 4}px`,
    left: `${r.left}px`,
    width: `${r.width}px`,
  }
}

const toggleSelect = (key, ev) => {
  if (openSelect.value === key) {
    openSelect.value = null
    return
  }
  if (ev?.currentTarget) positionSelect(ev.currentTarget)
  openSelect.value = key
}

const pick = (field, value) => {
  settings[field] = value
  openSelect.value = null
}

// Меню «Добавить получателя» — тоже телепортом в body (fixed), выравнивание по
// правому краю кнопки, иначе внутри модалки распирало скролл.
const recipientMenuStyle = ref({})
const toggleRecipientMenu = (ev) => {
  if (recipientMenuOpen.value) {
    recipientMenuOpen.value = false
    return
  }
  const r = ev.currentTarget.getBoundingClientRect()
  recipientMenuStyle.value = {
    position: 'fixed',
    top: `${r.bottom + 4}px`,
    right: `${Math.max(8, window.innerWidth - r.right)}px`,
  }
  recipientMenuOpen.value = true
}

const handleDocClick = (e) => {
  if (openSelect.value && !e.target.closest('[data-rp-select]')) openSelect.value = null
  if (recipientMenuOpen.value && !e.target.closest('[data-recipient-menu]')) recipientMenuOpen.value = false
}

// При прокрутке/ресайзе fixed-дропдаун разъедется с кнопкой — просто закрываем.
const closeOpenSelect = () => { openSelect.value = null; recipientMenuOpen.value = false }

onMounted(() => {
  document.addEventListener('mousedown', handleDocClick)
  window.addEventListener('scroll', closeOpenSelect, true)
  window.addEventListener('resize', closeOpenSelect)
})
onBeforeUnmount(() => {
  document.removeEventListener('mousedown', handleDocClick)
  window.removeEventListener('scroll', closeOpenSelect, true)
  window.removeEventListener('resize', closeOpenSelect)
  if (invitePollTimer) clearInterval(invitePollTimer)
})

const params = computed(() => ({
  ...(props.clientId ? { client_id: props.clientId } : {}),
  ...(props.folderId ? { folder_id: props.folderId } : {}),
}))

const personalChannels = computed(() => [
  { value: 'telegram', label: 'Telegram', connected: settings.connected_channels.includes('telegram') },
  { value: 'max', label: 'MAX', connected: settings.connected_channels.includes('max') },
])

const recipientsSummary = computed(() => {
  const labels = []
  if (settings.channels.includes('telegram')) labels.push('Telegram — мне лично')
  if (settings.channels.includes('max')) labels.push('MAX — мне лично')
  if (settings.channels.includes('email')) labels.push(`Email · ${settings.email_recipients.length}`)
  if (settings.chat_targets.length) labels.push(`чаты проекта · ${settings.chat_targets.length}`)
  return labels.length ? labels.join(' · ') : 'Получатели не выбраны'
})

const toggleChannel = (ch) => {
  if (!ch.connected) {
    emit('link-personal', ch.value)
    return
  }
  const idx = settings.channels.indexOf(ch.value)
  if (idx >= 0) settings.channels.splice(idx, 1)
  else settings.channels.push(ch.value)
}

const syncEmailChannel = () => {
  const hasEmails = settings.email_recipients.length > 0
  if (hasEmails && !settings.channels.includes('email')) settings.channels.push('email')
  if (!hasEmails) settings.channels = settings.channels.filter((value) => value !== 'email')
}

const addEmail = async () => {
  const value = newEmail.value.trim().toLowerCase()
  if (!/^\S+@\S+\.\S+$/.test(value)) {
    toaster.error('Введите корректный email')
    return
  }
  try {
    const { data } = await api.post('reports/email-recipients', { email: value }, { params: params.value })
    if (!settings.available_email_recipients.some((item) => item.id === data.id)) settings.available_email_recipients.push(data)
    if (!settings.email_recipients.includes(value)) settings.email_recipients.push(value)
    syncEmailChannel()
    newEmail.value = ''
    showEmailInput.value = false
    await saveRecipients()
    toaster.success('Email-получатель добавлен')
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Не удалось добавить email')
  }
}

const removeEmail = async (recipient) => {
  try {
    await api.delete(`reports/email-recipients/${recipient.id}`)
    settings.available_email_recipients = settings.available_email_recipients.filter((item) => item.id !== recipient.id)
    settings.email_recipients = settings.email_recipients.filter((value) => value !== recipient.email)
    syncEmailChannel()
    toaster.success('Email-получатель отвязан')
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Не удалось отвязать email')
  }
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
  if (tag.dynamics) return
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
    available_email_recipients: data.available_email_recipients || [],
    enabled: Boolean(data.enabled),
    platform: data.platform || 'all',
    channels: Array.isArray(data.channels) ? data.channels : [],
    email_recipients: Array.isArray(data.email_recipients) ? data.email_recipients : [],
    chat_targets: Array.isArray(data.chat_targets) ? data.chat_targets : [],
    day: data.day || 'daily',
    send_time: data.send_time || '10:00',
    period_days: Number(data.period_days || 7),
    report_format: data.report_format || 'desktop',
    // Блок «Динамика» пока показан только как будущая возможность и не
    // включается в отправляемые отчёты.
    include_dynamics: false,
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

const payload = () => ({
  enabled: settings.enabled,
  platform: settings.platform,
  channels: settings.channels,
  email_recipients: settings.email_recipients,
  chat_targets: settings.chat_targets,
  day: settings.day,
  send_time: settings.send_time,
  period_days: settings.period_days,
  report_format: settings.report_format,
  include_dynamics: false,
  approval_required: settings.approval_required,
  include_ai_comment: settings.include_ai_comment,
  sections: settings.sections,
  chart_metrics: settings.chart_metrics,
  dynamics_metrics: settings.dynamics_metrics,
})

const saveRecipients = async () => {
  const { data } = await api.put('reports/project-settings', payload(), { params: params.value })
  applySettings(data)
  emit('saved', data)
}

const save = async () => {
  if (settings.enabled && !settings.channels.length && !settings.chat_targets.length) {
    toaster.error('Добавьте хотя бы одного получателя перед включением автоотправки')
    tab.value = 'channels'
    return
  }
  saving.value = true
  try {
    await saveRecipients()
    toaster.success('Настройки отчёта сохранены')
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Не удалось сохранить настройки')
  } finally {
    saving.value = false
  }
}

const startLink = (kind, targetType) => {
  recipientMenuOpen.value = false
  return createLink(kind, targetType)
}

const createLink = async (kind, targetType) => {
  linkLoading.value = true
  try {
    const { data } = await api.post('reports/chat-targets/link-code', { kind, target_type: targetType }, { params: params.value })
    const path = data?.group_link || data?.telegram_url || data?.url || (kind === 'max' && targetType === 'group' ? data?.command : data?.code)
    inviteLink.value = path ? String(path) : ''
    if (!inviteLink.value) throw new Error('empty link')
    inviteInstruction.value = targetType === 'client'
      ? 'Отправьте ссылку клиенту. После Start его личный чат появится только в этом проекте.'
      : (kind === 'max' ? `Добавьте бота ${data?.bot || ''} в группу и отправьте команду ${data?.command || ''}` : 'Откройте ссылку и выберите нужную группу.')
    inviteBaselineIds = new Set((settings.available_chat_targets || []).map((item) => String(item.id)))
    if (invitePollTimer) clearInterval(invitePollTimer)
    invitePollTimer = setInterval(async () => {
      try {
        const response = await api.get('reports/project-settings', { params: params.value })
        const targets = Array.isArray(response.data?.available_chat_targets) ? response.data.available_chat_targets : []
        const added = targets.find((item) => !inviteBaselineIds.has(String(item.id)))
        if (!added) return
        settings.available_chat_targets = targets
        if (!settings.chat_targets.includes(added.id)) settings.chat_targets.push(added.id)
        await saveRecipients()
        inviteLink.value = ''
        inviteInstruction.value = ''
        clearInterval(invitePollTimer)
        invitePollTimer = null
        toaster.success('Получатель подключён к проекту')
      } catch {
        // Следующая проверка через 5 секунд.
      }
    }, 5000)
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Не удалось создать ссылку')
  } finally {
    linkLoading.value = false
  }
}

const unlinkTarget = async (target) => {
  try {
    await api.delete(`reports/chat-targets/${target.id}`)
    settings.available_chat_targets = settings.available_chat_targets.filter((item) => item.id !== target.id)
    settings.chat_targets = settings.chat_targets.filter((id) => id !== target.id)
    toaster.success('Получатель отвязан')
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Не удалось отвязать получателя')
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
  width: min(51rem, 94vw);
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

/* ── Капсулы личных каналов (списком) ── */
.rp-capsules {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.rp-capsule {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.65rem 0.85rem;
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
  width: 2.3rem;
  height: 2.3rem;
  border-radius: 0.7rem;
  flex-shrink: 0;
}

.rp-capsule__ic--telegram { background: linear-gradient(135deg, #2f6df6 0%, #14b8d5 100%); }
.rp-capsule__ic--max { background: linear-gradient(135deg, #6d3df5 0%, #a45cf0 100%); }
.rp-capsule__ic--email { background: linear-gradient(135deg, #64748b 0%, #94a3b8 100%); }

.rp-email-add { display: flex; gap: 0.6rem; margin-bottom: 0.7rem; }
.rp-email-add .rp-input { flex: 1; }
.rp-link-actions { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 0.4rem; }
.rp-target-unlink { margin-left: auto; border: 0; background: transparent; color: #94a3b8; font-size: 0.75rem; cursor: pointer; }
.rp-target-unlink:hover { color: #dc2626; }
.rp-invite-instruction { margin-top: 0.4rem; }
.rp-recipient-menu { position: relative; }
.rp-recipient-menu__list { position: absolute; right: 0; top: calc(100% + 0.35rem); z-index: 3; min-width: 12.5rem; padding: 0.35rem; border: 1px solid rgba(15, 23, 42, 0.12); border-radius: 0.7rem; background: #fff; box-shadow: 0 0.8rem 2rem rgba(15, 23, 42, 0.16); }
.rp-recipient-menu__list button { display: block; width: 100%; border: 0; border-radius: 0.45rem; padding: 0.52rem 0.65rem; background: transparent; color: #334155; font: inherit; font-size: 0.8rem; text-align: left; cursor: pointer; }
.rp-recipient-menu__list button:hover { background: #f1f5f9; }
.rp-recipient-status { margin-left: auto; color: #15803d; font-size: 0.72rem; font-weight: 700; white-space: nowrap; }
.rp-check--unavailable { opacity: 0.6; }
.rp-check--unavailable .rp-recipient-status { color: #b45309; }
.rp-check__name small { display: block; margin-top: 0.12rem; color: rgba(105, 105, 105, 0.62); font-size: 0.74rem; font-weight: 500; }
.rp-auto-recipients { margin-bottom: 0.9rem; }
.rp-modal.is-dark .rp-recipient-menu__list { background: #303445; border-color: rgba(255,255,255,0.12); }
.rp-modal.is-dark .rp-recipient-menu__list button { color: rgba(255,255,255,0.85); }
.rp-modal.is-dark .rp-recipient-menu__list button:hover { background: rgba(255,255,255,0.08); }

/* Плавающее меню получателей (телепорт в body): fixed-позиция инлайном,
   z-index выше модалки. */
.rp-recipient-menu__list--float { z-index: 1300; }
.rp-recipient-menu__list--float.is-dark { background: #303445; border-color: rgba(255,255,255,0.12); }
.rp-recipient-menu__list--float.is-dark button { color: rgba(255,255,255,0.85); }
.rp-recipient-menu__list--float.is-dark button:hover { background: rgba(255,255,255,0.08); }

/* Фирменные mask-иконки каналов (как на дашборде) */
.rp-mask {
  display: block;
  background: #fff;
  flex: 0 0 auto;
}

.rp-mask--telegram {
  width: 1.2rem;
  height: 1.2rem;
  transform: translateX(-0.08rem);
  -webkit-mask: url("data:image/svg+xml,%3Csvg width='21' height='21' viewBox='0 0 21 21' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M18.42 3.05 2.54 9.17c-1.08.43-1.07 1.03-.2 1.3l4.08 1.27 1.56 4.79c.2.55.1.77.68.77.45 0 .65-.2.9-.45l2.16-2.1 4.5 3.32c.83.46 1.43.22 1.64-.77l2.97-13.98c.3-1.22-.47-1.77-1.41-1.27ZM6.95 11.45l9.47-5.97c.47-.28.9-.13.55.18l-8.1 7.3-.31 3.31-1.61-4.82Z' fill='black'/%3E%3C/svg%3E") center / contain no-repeat;
  mask: url("data:image/svg+xml,%3Csvg width='21' height='21' viewBox='0 0 21 21' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M18.42 3.05 2.54 9.17c-1.08.43-1.07 1.03-.2 1.3l4.08 1.27 1.56 4.79c.2.55.1.77.68.77.45 0 .65-.2.9-.45l2.16-2.1 4.5 3.32c.83.46 1.43.22 1.64-.77l2.97-13.98c.3-1.22-.47-1.77-1.41-1.27ZM6.95 11.45l9.47-5.97c.47-.28.9-.13.55.18l-8.1 7.3-.31 3.31-1.61-4.82Z' fill='black'/%3E%3C/svg%3E") center / contain no-repeat;
}

.rp-mask--max {
  width: 1.4rem;
  height: 1.4rem;
  -webkit-mask: url("data:image/svg+xml,%3Csvg width='23' height='23' viewBox='0 0 23 23' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath fill-rule='evenodd' clip-rule='evenodd' d='M11.3262 0.526703C9.97595 0.644538 9.03042 0.858842 7.96223 1.28911C4.58971 2.64757 2.17288 5.63667 1.5882 9.17233C1.46913 9.89246 1.44765 10.1918 1.45045 11.0932C1.45635 13.0195 1.63889 14.1725 2.40714 17.1368C2.76373 18.5127 2.9304 19.5394 2.9304 20.3602C2.9304 20.9016 3.20825 21.2516 3.73877 21.3784C4.01264 21.4438 4.54202 21.4188 4.92334 21.3224C5.78836 21.1037 6.61078 20.6623 7.15586 20.1242C7.29619 19.9857 7.41359 19.8723 7.41673 19.8723C7.41989 19.8722 7.5789 19.9796 7.77008 20.111C9.10923 21.0308 9.9351 21.2986 11.5948 21.3512C14.4847 21.4427 17.1617 20.3757 19.1852 18.3258C21.6244 15.8548 22.6485 12.3498 21.9555 8.84481C21.5449 6.76834 20.5412 4.89959 19.0401 3.41648C17.4445 1.83999 15.5146 0.897223 13.2626 0.59407C12.8572 0.539506 11.6576 0.497774 11.3262 0.526703ZM11.3121 5.65698C10.2161 5.75895 9.1042 6.28998 8.31739 7.08719C7.04926 8.37209 6.45516 10.2727 6.57709 12.6546C6.64454 13.9728 6.86458 15.0956 7.19728 15.8193C7.32036 16.087 7.42922 16.2273 7.55541 16.2807C7.68149 16.3341 7.8597 16.2766 8.13184 16.0949C8.35149 15.9482 8.82063 15.5607 8.96161 15.4096L9.04223 15.3231L9.21603 15.4376C9.47259 15.6068 10.0304 15.8764 10.3364 15.9792C11.3635 16.3241 12.443 16.3182 13.4976 15.9618C14.3646 15.6688 15.2018 15.1074 15.7963 14.4203C16.7195 13.3535 17.208 11.9255 17.0986 10.6135C17.0368 9.87193 16.8818 9.29636 16.5722 8.65863C15.7542 6.97365 14.1951 5.87211 12.3379 5.66715C12.0796 5.63862 11.5643 5.63352 11.3121 5.65698Z' fill='black'/%3E%3C/svg%3E") center / contain no-repeat;
  mask: url("data:image/svg+xml,%3Csvg width='23' height='23' viewBox='0 0 23 23' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath fill-rule='evenodd' clip-rule='evenodd' d='M11.3262 0.526703C9.97595 0.644538 9.03042 0.858842 7.96223 1.28911C4.58971 2.64757 2.17288 5.63667 1.5882 9.17233C1.46913 9.89246 1.44765 10.1918 1.45045 11.0932C1.45635 13.0195 1.63889 14.1725 2.40714 17.1368C2.76373 18.5127 2.9304 19.5394 2.9304 20.3602C2.9304 20.9016 3.20825 21.2516 3.73877 21.3784C4.01264 21.4438 4.54202 21.4188 4.92334 21.3224C5.78836 21.1037 6.61078 20.6623 7.15586 20.1242C7.29619 19.9857 7.41359 19.8723 7.41673 19.8723C7.41989 19.8722 7.5789 19.9796 7.77008 20.111C9.10923 21.0308 9.9351 21.2986 11.5948 21.3512C14.4847 21.4427 17.1617 20.3757 19.1852 18.3258C21.6244 15.8548 22.6485 12.3498 21.9555 8.84481C21.5449 6.76834 20.5412 4.89959 19.0401 3.41648C17.4445 1.83999 15.5146 0.897223 13.2626 0.59407C12.8572 0.539506 11.6576 0.497774 11.3262 0.526703ZM11.3121 5.65698C10.2161 5.75895 9.1042 6.28998 8.31739 7.08719C7.04926 8.37209 6.45516 10.2727 6.57709 12.6546C6.64454 13.9728 6.86458 15.0956 7.19728 15.8193C7.32036 16.087 7.42922 16.2273 7.55541 16.2807C7.68149 16.3341 7.8597 16.2766 8.13184 16.0949C8.35149 15.9482 8.82063 15.5607 8.96161 15.4096L9.04223 15.3231L9.21603 15.4376C9.47259 15.6068 10.0304 15.8764 10.3364 15.9792C11.3635 16.3241 12.443 16.3182 13.4976 15.9618C14.3646 15.6688 15.2018 15.1074 15.7963 14.4203C16.7195 13.3535 17.208 11.9255 17.0986 10.6135C17.0368 9.87193 16.8818 9.29636 16.5722 8.65863C15.7542 6.97365 14.1951 5.87211 12.3379 5.66715C12.0796 5.63862 11.5643 5.63352 11.3121 5.65698Z' fill='black'/%3E%3C/svg%3E") center / contain no-repeat;
}

.rp-mask--email {
  width: 1.3rem;
  height: 0.96rem;
  -webkit-mask: url("data:image/svg+xml,%3Csvg width='26' height='19' viewBox='0 0 26 19' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M2.25 0H23.14C24.38 0 25.39 1.01 25.39 2.25V16.56C25.39 17.8 24.38 18.81 23.14 18.81H2.25C1.01 18.81 0 17.8 0 16.56V2.25C0 1.01 1.01 0 2.25 0ZM2.12 2.52V16.3C2.12 16.55 2.32 16.75 2.57 16.75H22.82C23.07 16.75 23.27 16.55 23.27 16.3V2.52L13.56 10.4C13.06 10.81 12.33 10.81 11.83 10.4L2.12 2.52ZM21.02 2.06H4.36L12.69 8.8L21.02 2.06Z' fill='black'/%3E%3C/svg%3E") center / contain no-repeat;
  mask: url("data:image/svg+xml,%3Csvg width='26' height='19' viewBox='0 0 26 19' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M2.25 0H23.14C24.38 0 25.39 1.01 25.39 2.25V16.56C25.39 17.8 24.38 18.81 23.14 18.81H2.25C1.01 18.81 0 17.8 0 16.56V2.25C0 1.01 1.01 0 2.25 0ZM2.12 2.52V16.3C2.12 16.55 2.32 16.75 2.57 16.75H22.82C23.07 16.75 23.27 16.55 23.27 16.3V2.52L13.56 10.4C13.06 10.81 12.33 10.81 11.83 10.4L2.12 2.52ZM21.02 2.06H4.36L12.69 8.8L21.02 2.06Z' fill='black'/%3E%3C/svg%3E") center / contain no-repeat;
}

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

/* Плавающий список (телепорт в body): fixed-позиция задаётся инлайн-стилем,
   видимость — сразу (рендерится по v-if), скролл только внутри самого списка. */
.rp-select__list--float {
  right: auto;
  z-index: 1300;
  max-height: 15rem;
  overflow-y: auto;
  opacity: 1;
  pointer-events: auto;
  transform: none;
}
.rp-select__list--float.is-dark {
  background: #2c2f42;
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.1), 0 12px 32px rgba(0, 0, 0, 0.45);
}
.rp-select__list--float.is-dark button { color: rgba(255, 255, 255, 0.78); }
.rp-select__list--float.is-dark button:hover { background: rgba(255, 255, 255, 0.07); }
.rp-select__list--float.is-dark button.sel { color: #8fb0ff; }

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

.rp-tag.disabled,
.rp-tag:disabled {
  opacity: 0.48;
  cursor: not-allowed;
  border-color: rgba(15, 23, 42, 0.1);
  background: #f8fafc;
}
.rp-tag.disabled:hover { border-color: rgba(15, 23, 42, 0.1); }

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
  .rp-grid { grid-template-columns: 1fr; }
}
</style>
