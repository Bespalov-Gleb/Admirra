<template>
  <Teleport to="body">
    <div class="project-report-backdrop" @click.self="$emit('close')">
      <section class="project-report-modal">
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
              <h4>Проверка перед отправкой</h4>
              <label class="project-check">
                <input v-model="settings.approval_required" type="checkbox" />
                <span>Отправлять сначала на проверку</span>
              </label>
              <label class="project-check">
                <input v-model="settings.include_ai_comment" type="checkbox" />
                <span>Добавлять AI-комментарий</span>
              </label>
              <label class="project-check">
                <input v-model="settings.include_dynamics" type="checkbox" />
                <span>Включить блок «Динамика»</span>
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
  padding: 24px;
  background: rgba(15, 23, 42, 0.34);
  backdrop-filter: blur(10px);
}

.project-report-modal {
  width: min(860px, 100%);
  max-height: min(900px, calc(100vh - 48px));
  overflow: auto;
  border-radius: 26px;
  background: #f8fafc;
  border: 1px solid rgba(148, 163, 184, 0.22);
  box-shadow: 0 28px 80px rgba(15, 23, 42, 0.2);
  padding: 24px;
}

.project-report-head,
.project-report-card-head,
.project-report-actions {
  display: flex;
  justify-content: space-between;
  gap: 18px;
}

.project-report-head {
  align-items: flex-start;
  margin-bottom: 18px;
}

.project-report-head p {
  margin: 0 0 4px;
  color: #2563eb;
  font-weight: 800;
}

.project-report-head h3 {
  margin: 0;
  color: #172033;
  font-size: 1.42rem;
  font-weight: 850;
}

.project-report-head span,
.project-report-card p,
.project-field small,
.channel-row small,
.target-row small {
  color: #8a93a3;
  font-size: 0.9rem;
}

.project-report-close {
  width: 36px;
  height: 36px;
  border: 1px solid rgba(148, 163, 184, 0.25);
  border-radius: 12px;
  background: #fff;
  color: #64748b;
  font-size: 24px;
}

.project-report-tabs {
  display: inline-flex;
  padding: 5px;
  border-radius: 16px;
  background: #eef3fb;
  margin-bottom: 18px;
}

.project-report-tabs button {
  min-height: 38px;
  padding: 0 18px;
  border-radius: 12px;
  color: #64748b;
  font-weight: 760;
}

.project-report-tabs button.active {
  background: #fff;
  color: #2563eb;
  box-shadow: 0 8px 20px rgba(37, 99, 235, 0.12);
}

.project-report-section {
  display: grid;
  gap: 14px;
}

.project-report-card {
  padding: 18px;
  border-radius: 20px;
  background: #fff;
  border: 1px solid rgba(148, 163, 184, 0.16);
}

.project-report-card h4 {
  margin: 0 0 5px;
  color: #172033;
  font-size: 1.05rem;
  font-weight: 820;
}

.channel-list,
.target-list {
  display: grid;
  gap: 10px;
  margin-top: 14px;
}

.channel-row,
.target-row,
.project-check,
.project-field--toggle {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 52px;
  padding: 12px;
  border-radius: 16px;
  background: #f7f9fc;
}

.channel-row strong,
.target-row strong {
  display: block;
  color: #172033;
}

.project-report-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.project-field {
  display: grid;
  gap: 7px;
}

.project-field span {
  color: #64748b;
  font-size: 0.84rem;
  font-weight: 780;
}

.project-field input:not([type="checkbox"]),
.project-field select {
  height: 46px;
  border-radius: 14px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  background: #fff;
  padding: 0 13px;
}

.project-report-link {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-top: 14px;
  padding: 11px;
  border-radius: 14px;
  background: #eff6ff;
  color: #1d4ed8;
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
  min-height: 42px;
  border-radius: 14px;
  padding: 0 18px;
  font-weight: 760;
}

.project-report-light-btn,
.project-report-secondary {
  background: #fff;
  border: 1px solid rgba(148, 163, 184, 0.26);
  color: #2563eb;
}

.project-report-link button,
.project-report-primary {
  background: linear-gradient(135deg, #2563eb, #10b8c9);
  color: #fff;
}

.project-report-actions {
  align-items: center;
  justify-content: flex-end;
  margin-top: 18px;
}

.project-report-empty,
.project-report-loading {
  padding: 18px;
  border-radius: 18px;
  background: #fff;
  color: #94a3b8;
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
