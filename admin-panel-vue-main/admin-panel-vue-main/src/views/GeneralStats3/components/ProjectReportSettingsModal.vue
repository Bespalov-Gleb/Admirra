<template>
  <Teleport to="body">
    <div class="project-report-backdrop" @click.self="$emit('close')">
      <section class="project-report-modal" :class="{ 'is-dark': isDarkMode }">
        <header class="project-report-head">
          <div>
            <p>Отчёты проекта</p>
            <h3>{{ settings.scope_label || title }}</h3>
            <span>Каналы доставки, автоотправка и проверка перед отправкой</span>
          </div>
          <button type="button" class="project-report-close" @click="$emit('close')">×</button>
        </header>

        <div class="project-report-tabs">
          <button type="button" :class="{ active: tab === 'channels' }" @click="tab = 'channels'">Каналы</button>
          <button type="button" :class="{ active: tab === 'auto' }" @click="tab = 'auto'">Автоотправка</button>
        </div>

        <div v-if="loading" class="project-report-loading">Загружаем настройки…</div>

        <template v-else>
          <div v-if="tab === 'channels'" class="project-report-section">
            <div class="project-report-card">
              <div>
                <h4>Личные каналы аккаунта</h4>
                <p>Используются для ручной отправки и автоотправки, если включены ниже.</p>
              </div>
              <div class="channel-list">
                <label v-for="channel in personalChannels" :key="channel.value" class="channel-row">
                  <input v-model="settings.channels" type="checkbox" :value="channel.value" :disabled="!channel.connected" />
                  <span>
                    <strong>{{ channel.label }}</strong>
                    <small>{{ channel.connected ? 'Подключён' : 'Не подключён в профиле' }}</small>
                  </span>
                </label>
              </div>
            </div>

            <div class="project-report-card">
              <div class="project-report-card-head">
                <div>
                  <h4>Группы проекта</h4>
                  <p>Клиентская ссылка привязывает чат к этому проекту или папке.</p>
                </div>
                <button type="button" class="project-report-light-btn" :disabled="linkLoading" @click="createLink">
                  {{ linkLoading ? 'Создаём...' : 'Создать ссылку' }}
                </button>
              </div>
              <div v-if="inviteLink" class="project-report-link">
                <span>{{ inviteLink }}</span>
                <button type="button" @click="copyInvite">Скопировать</button>
              </div>
              <div class="target-list">
                <label v-for="target in settings.available_chat_targets" :key="target.id" class="target-row">
                  <input v-model="settings.chat_targets" type="checkbox" :value="target.id" />
                  <span>
                    <strong>{{ target.title || target.chat_id }}</strong>
                    <small>{{ target.kind === 'max' ? 'MAX' : 'Telegram' }}</small>
                  </span>
                </label>
                <div v-if="!settings.available_chat_targets?.length" class="project-report-empty">
                  Группы ещё не привязаны
                </div>
              </div>
            </div>
          </div>

          <div v-else class="project-report-section">
            <div class="project-report-card project-report-grid">
              <label class="project-field project-field--toggle">
                <span>
                  <strong>Автоотправка</strong>
                  <small>Один набор настроек для текущего проекта</small>
                </span>
                <input v-model="settings.enabled" type="checkbox" />
              </label>
              <label class="project-field">
                <span>День</span>
                <select v-model="settings.day">
                  <option value="daily">Ежедневно</option>
                  <option value="weekdays">По будням</option>
                  <option value="monday">Понедельник</option>
                  <option value="friday">Пятница</option>
                </select>
              </label>
              <label class="project-field">
                <span>Время по МСК</span>
                <input v-model="settings.send_time" type="time" />
              </label>
              <label class="project-field">
                <span>Период</span>
                <select v-model.number="settings.period_days">
                  <option :value="1">1 день</option>
                  <option :value="7">7 дней</option>
                  <option :value="14">14 дней</option>
                  <option :value="30">30 дней</option>
                </select>
              </label>
              <label class="project-field">
                <span>Рекламный канал</span>
                <select v-model="settings.platform">
                  <option value="all">Все каналы</option>
                  <option value="yandex">Яндекс Директ</option>
                  <option value="vk">VK Реклама</option>
                  <option value="avito">Avito Ads</option>
                </select>
              </label>
              <label class="project-field">
                <span>Формат</span>
                <select v-model="settings.report_format">
                  <option value="desktop">Десктоп</option>
                  <option value="mobile">Мобильный</option>
                </select>
              </label>
            </div>

            <div class="project-report-card">
              <h4>Состав отчёта</h4>
              <div class="report-tags">
                <button
                  v-for="tag in sectionTags"
                  :key="tag.value"
                  type="button"
                  class="report-tag"
                  :class="{ on: isSectionOn(tag) }"
                  @click="toggleSection(tag)"
                >{{ tag.label }}</button>
              </div>
            </div>

            <div class="project-report-card">
              <h4>Режим отправки</h4>
              <label class="project-radio">
                <input type="radio" name="approval-mode" :value="true" v-model="settings.approval_required" />
                <span>
                  <strong>С проверкой <em class="project-radio__default">по умолчанию</em></strong>
                  <small>Отчёт ждёт вашего одобрения</small>
                </span>
              </label>
              <label class="project-radio">
                <input type="radio" name="approval-mode" :value="false" v-model="settings.approval_required" />
                <span>
                  <strong>Без проверки</strong>
                  <small>Уходит сам · при аномалии детектора всё равно ждёт вас</small>
                </span>
              </label>
              <label class="project-check project-check--indent">
                <input v-model="settings.include_ai_comment" type="checkbox" />
                <span>Включать AI-комментарий в авто-отчёт</span>
              </label>
            </div>
          </div>
        </template>

        <footer class="project-report-actions">
          <button type="button" class="project-report-secondary" @click="$emit('close')">Отмена</button>
          <button type="button" class="project-report-primary" :disabled="saving || loading" @click="save">
            {{ saving ? 'Сохраняем...' : 'Сохранить настройки' }}
          </button>
        </footer>
      </section>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
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

const params = computed(() => ({
  ...(props.clientId ? { client_id: props.clientId } : {}),
  ...(props.folderId ? { folder_id: props.folderId } : {}),
}))

const personalChannels = computed(() => [
  { value: 'telegram', label: 'Telegram', connected: settings.connected_channels.includes('telegram') },
  { value: 'max', label: 'MAX', connected: settings.connected_channels.includes('max') },
  { value: 'email', label: 'Email', connected: settings.connected_channels.includes('email') },
])

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
.project-report-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1190;
  display: grid;
  place-items: center;
  padding: 2rem;
  background: rgba(15, 23, 42, 0.56);
  backdrop-filter: blur(0.6rem);
}

.project-report-modal {
  width: min(80rem, 100%);
  max-height: min(92rem, calc(100vh - 4rem));
  overflow: auto;
  border-radius: 2rem;
  background: #f5f7fb;
  border: 1px solid #ececf2;
  box-shadow: 0 2.4rem 6rem rgba(15, 23, 42, 0.22);
  padding: 2.2rem;
}

.project-report-modal.is-dark {
  background: #1d2030;
  border-color: rgba(255, 255, 255, 0.08);
  box-shadow: 0 2.4rem 6rem rgba(0, 0, 0, 0.5);
}

.project-report-head,
.project-report-card-head,
.project-report-actions {
  display: flex;
  justify-content: space-between;
  gap: 1.6rem;
}

.project-report-head {
  align-items: flex-start;
  margin-bottom: 1.8rem;
}

.project-report-head p {
  margin: 0 0 0.4rem;
  color: #2563eb;
  font-size: 1.2rem;
  font-weight: 750;
}

.project-report-modal.is-dark .project-report-head p { color: #6f9bff; }

.project-report-head h3 {
  margin: 0;
  color: #171717;
  font-size: 1.7rem;
  font-weight: 750;
}

.project-report-modal.is-dark .project-report-head h3 { color: #f8fafc; }

.project-report-head span,
.project-report-card p,
.project-field small,
.channel-row small,
.target-row small {
  color: #767676;
  font-size: 1.2rem;
}

.project-report-modal.is-dark .project-report-head span,
.project-report-modal.is-dark .project-report-card p,
.project-report-modal.is-dark .channel-row small,
.project-report-modal.is-dark .target-row small { color: rgba(255, 255, 255, 0.5); }

.project-report-close {
  width: 3.2rem;
  height: 3.2rem;
  border: 0;
  border-radius: 999px;
  background: #eef1f6;
  color: #697586;
  font-size: 2rem;
  flex-shrink: 0;
}

.project-report-modal.is-dark .project-report-close {
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.72);
}

.project-report-tabs {
  display: inline-flex;
  padding: 0.35rem;
  border-radius: 1.2rem;
  background: #e9eefaee;
  margin-bottom: 1.8rem;
  gap: 0.2rem;
}

.project-report-modal.is-dark .project-report-tabs { background: rgba(255, 255, 255, 0.06); }

.project-report-tabs button {
  min-height: 3.6rem;
  padding: 0 1.8rem;
  border-radius: 0.9rem;
  color: #64748b;
  font-size: 1.25rem;
  font-weight: 680;
}

.project-report-tabs button.active {
  background: #fff;
  color: #2563eb;
  box-shadow: 0 0.6rem 1.6rem rgba(37, 99, 235, 0.12);
}

.project-report-modal.is-dark .project-report-tabs button { color: rgba(255, 255, 255, 0.6); }
.project-report-modal.is-dark .project-report-tabs button.active {
  background: rgba(74, 122, 255, 0.2);
  color: #6f9bff;
  box-shadow: none;
}

.project-report-section {
  display: grid;
  gap: 1.4rem;
}

.project-report-card {
  padding: 1.8rem;
  border-radius: 1.6rem;
  background: #fff;
  border: 1px solid #ececf2;
}

.project-report-modal.is-dark .project-report-card {
  background: #252838;
  border-color: rgba(255, 255, 255, 0.08);
}

.project-report-card h4 {
  margin: 0 0 0.5rem;
  color: #171717;
  font-size: 1.35rem;
  font-weight: 720;
}

.project-report-modal.is-dark .project-report-card h4 { color: #f1f5f9; }

.channel-list,
.target-list {
  display: grid;
  gap: 1rem;
  margin-top: 1.4rem;
}

.channel-row,
.target-row,
.project-check,
.project-field--toggle {
  display: flex;
  align-items: center;
  gap: 1.2rem;
  min-height: 5rem;
  padding: 1.2rem;
  border-radius: 1.4rem;
  background: #f7f9fc;
  font-size: 1.3rem;
}

.project-report-modal.is-dark .channel-row,
.project-report-modal.is-dark .target-row,
.project-report-modal.is-dark .project-check,
.project-report-modal.is-dark .project-field--toggle {
  background: rgba(255, 255, 255, 0.04);
  color: #e6ebf3;
}

.channel-row input,
.target-row input,
.project-check input,
.project-field--toggle input {
  width: 1.8rem;
  height: 1.8rem;
  accent-color: #2563eb;
  flex-shrink: 0;
}

.channel-row strong,
.target-row strong {
  display: block;
  color: #171717;
  font-size: 1.3rem;
}

.project-report-modal.is-dark .channel-row strong,
.project-report-modal.is-dark .target-row strong { color: #f1f5f9; }

.project-report-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1.4rem;
}

.project-field {
  display: grid;
  gap: 0.7rem;
}

.project-field span {
  color: #64748b;
  font-size: 1.15rem;
  font-weight: 700;
}

.project-report-modal.is-dark .project-field span { color: rgba(255, 255, 255, 0.6); }

.project-field input:not([type="checkbox"]),
.project-field select {
  height: 4.4rem;
  border-radius: 1.2rem;
  border: 1px solid #e5e7eb;
  background: #fff;
  padding: 0 1.3rem;
  font-size: 1.3rem;
  color: #171717;
}

.project-report-modal.is-dark .project-field input:not([type="checkbox"]),
.project-report-modal.is-dark .project-field select {
  background: rgba(0, 0, 0, 0.2);
  border-color: rgba(255, 255, 255, 0.12);
  color: #f1f5f9;
}

.report-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.8rem;
  margin-top: 1.2rem;
}

.report-tag {
  padding: 0.6rem 1.4rem;
  border-radius: 1.6rem;
  border: 1.5px solid rgba(148, 163, 184, 0.5);
  color: #64748b;
  font-size: 1.2rem;
  font-weight: 620;
  background: #fff;
  transition: all 0.15s;
}

.report-tag.on {
  border-color: #2563eb;
  color: #2563eb;
  background: #eef4ff;
  font-weight: 700;
}

.project-report-modal.is-dark .report-tag {
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(255, 255, 255, 0.16);
  color: rgba(255, 255, 255, 0.6);
}

.project-report-modal.is-dark .report-tag.on {
  border-color: #6f9bff;
  color: #6f9bff;
  background: rgba(74, 122, 255, 0.16);
}

.project-radio {
  display: flex;
  align-items: flex-start;
  gap: 1.1rem;
  padding: 1.2rem;
  border-radius: 1.4rem;
  background: #f7f9fc;
  margin-top: 1rem;
  cursor: pointer;
}

.project-report-modal.is-dark .project-radio { background: rgba(255, 255, 255, 0.04); }

.project-radio input {
  margin-top: 0.3rem;
  width: 1.7rem;
  height: 1.7rem;
  accent-color: #2563eb;
  flex-shrink: 0;
}

.project-radio span {
  display: grid;
  gap: 0.3rem;
}

.project-radio strong {
  color: #171717;
  font-size: 1.3rem;
  display: inline-flex;
  align-items: center;
  gap: 0.7rem;
}

.project-report-modal.is-dark .project-radio strong { color: #f1f5f9; }

.project-radio__default {
  font-style: normal;
  font-size: 1rem;
  font-weight: 700;
  color: #1e4fc0;
  background: #eaf0fe;
  border-radius: 0.7rem;
  padding: 0.2rem 0.8rem;
}

.project-report-modal.is-dark .project-radio__default {
  color: #6f9bff;
  background: rgba(74, 122, 255, 0.2);
}

.project-radio small {
  color: #8a93a3;
  font-size: 1.15rem;
}

.project-report-modal.is-dark .project-radio small { color: rgba(255, 255, 255, 0.45); }

.project-check--indent {
  margin-top: 1rem;
  margin-left: 0.4rem;
}

.project-report-link {
  display: flex;
  gap: 1rem;
  align-items: center;
  margin-top: 1.4rem;
  padding: 1.1rem;
  border-radius: 1.2rem;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 1.25rem;
}

.project-report-modal.is-dark .project-report-link {
  background: rgba(74, 122, 255, 0.12);
  color: #a9c4ff;
}

.project-report-link span {
  min-width: 0;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-report-light-btn,
.project-report-link button,
.project-report-secondary,
.project-report-primary {
  min-height: 4.2rem;
  border-radius: 1.2rem;
  padding: 0 1.8rem;
  font-size: 1.3rem;
  font-weight: 680;
}

.project-report-light-btn,
.project-report-secondary {
  background: #fff;
  border: 1px solid #e5e7eb;
  color: #2563eb;
}

.project-report-modal.is-dark .project-report-light-btn,
.project-report-modal.is-dark .project-report-secondary {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.12);
  color: #6f9bff;
}

.project-report-link button,
.project-report-primary {
  background: linear-gradient(135deg, #2f6df6, #14b8d5);
  color: #fff;
  border: 0;
}

.project-report-actions {
  align-items: center;
  justify-content: flex-end;
  margin-top: 1.8rem;
}

.project-report-empty,
.project-report-loading {
  padding: 1.8rem;
  border-radius: 1.5rem;
  background: #fff;
  color: #94a3b8;
  font-size: 1.25rem;
}

.project-report-modal.is-dark .project-report-empty,
.project-report-modal.is-dark .project-report-loading {
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.4);
}

@media (max-width: 760px) {
  .project-report-grid {
    grid-template-columns: 1fr;
  }
  .project-report-card-head {
    flex-direction: column;
  }
}
</style>
