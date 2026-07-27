<template>
  <div>
    <PageHeader title="Безопасность и настройки" description="Сессии команды, политика доступа и журнал действий." eyebrow="Контроль доступа" />
    <div class="tabs">
      <button v-for="item in tabs" :key="item.id" :class="{ active: tab === item.id }" @click="tab = item.id">{{ item.label }}</button>
    </div>
    <LoadingState v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="loadCurrent" />

    <section v-else-if="tab === 'sessions'" class="panel">
      <div class="panel__header"><div><p class="eyebrow">Активные устройства</p><h2>Сессии команды</h2></div><UiBadge :label="`${sessions.length} активных`" tone="info" /></div>
      <DataTable :columns="sessionColumns" :rows="sessions" :total="sessions.length" :page-size="100">
        <template #cell-staff="{ row }"><div class="user-cell"><span class="avatar avatar--small">{{ (row.staff_name || row.staff_email || '?')[0].toUpperCase() }}</span><span><strong>{{ row.staff_name || row.staff_email }}</strong><small>{{ row.staff_email }}</small></span></div></template>
        <template #cell-device="{ row }"><span class="device-cell"><ComputerDesktopIcon />{{ deviceName(row.user_agent) }}</span></template>
        <template #cell-location="{ row }">{{ row.city || '—' }}<small class="block muted">{{ row.ip_address || 'IP неизвестен' }}</small></template>
        <template #cell-last_seen_at="{ row }"><span :title="moscowDateTime(row.last_seen_at)">{{ relativeTime(row.last_seen_at) }}</span></template>
        <template #cell-actions="{ row }"><button class="button button--tiny button--danger-soft" @click="revokeSession(row)">Завершить</button></template>
      </DataTable>
    </section>

    <section v-else-if="tab === 'settings'" class="settings-layout">
      <div class="panel">
        <div class="panel__header"><div><p class="eyebrow">Политика доступа</p><h2>Команда и безопасность</h2></div></div>
        <div class="setting-list">
          <label class="switch-row"><span><strong>Обязательная 2FA</strong><small>Требовать второй фактор от сотрудников</small></span><input v-model="settings.team_2fa_required" type="checkbox" /><i /></label>
          <label class="switch-row"><span><strong>Impersonation менеджеров</strong><small>Разрешить вход в клиентские аккаунты</small></span><input v-model="settings.support_impersonation_allowed" type="checkbox" /><i /></label>
          <label class="switch-row"><span><strong>Логирование сессий</strong><small>Записывать устройства и IP сотрудников</small></span><input v-model="settings.session_logging_enabled" type="checkbox" /><i /></label>
          <label class="switch-row"><span><strong>Белый список IP</strong><small>Ограничить доступ доверенными адресами</small></span><input v-model="settings.ip_whitelist_enabled" type="checkbox" /><i /></label>
          <label v-if="settings.ip_whitelist_enabled" class="field"><span>IP-адреса, по одному в строке</span><textarea v-model="ipWhitelistText" rows="4" /></label>
        </div>
      </div>
      <div class="panel">
        <div class="panel__header"><div><p class="eyebrow">Сервис</p><h2>Режимы работы</h2></div></div>
        <div class="setting-list">
          <label class="switch-row"><span><strong>Технические работы</strong><small>Maintenance mode</small></span><input v-model="settings.maintenance_mode" type="checkbox" /><i /></label>
          <label class="switch-row"><span><strong>Регистрация пользователей</strong><small>Разрешить новые регистрации</small></span><input v-model="settings.registration_enabled" type="checkbox" /><i /></label>
          <label class="switch-row"><span><strong>Email-уведомления команды</strong><small>Системные алерты на почту</small></span><input v-model="settings.team_email_alerts_enabled" type="checkbox" /><i /></label>
          <div class="form-grid">
            <label class="field"><span>Дней триала</span><input v-model.number="settings.trial_days" type="number" min="0" /></label>
            <label class="field"><span>Баланс OpenAI, $</span><input v-model.number="settings.openai_balance_usd" type="number" step="0.01" /></label>
            <label class="field"><span>Порог алерта, $</span><input v-model.number="settings.openai_alert_threshold_usd" type="number" step="0.01" /></label>
          </div>
        </div>
      </div>
      <div class="settings-footer"><span class="muted">Настройки сохраняются в БД. Часть переключателей пока не влияет на runtime сервиса.</span><button class="button button--primary" :disabled="saving" @click="saveSettings">{{ saving ? 'Сохраняем…' : 'Сохранить настройки' }}</button></div>
    </section>

    <section v-else class="panel">
      <div class="panel__header"><div><p class="eyebrow">Журнал</p><h2>Аудит действий</h2></div></div>
      <div class="toolbar toolbar--embedded">
        <input v-model="auditFilters.staff_email" class="compact-input" placeholder="Email сотрудника" @keyup.enter="loadAudit" />
        <input v-model="auditFilters.action" class="compact-input" placeholder="Тип действия" @keyup.enter="loadAudit" />
        <button class="button button--secondary" @click="loadAudit">Применить</button>
      </div>
      <DataTable :columns="auditColumns" :rows="audit" :total="audit.length" :page-size="50">
        <template #cell-created_at="{ row }">{{ moscowDateTime(row.created_at) }}</template>
        <template #cell-action="{ row }"><UiBadge :label="row.action" tone="neutral" /></template>
        <template #cell-target="{ row }">{{ row.target_type || '—' }}<small class="block muted">{{ row.target_id || '' }}</small></template>
      </DataTable>
      <div class="simple-pager"><button class="button button--secondary" :disabled="auditPage <= 1" @click="auditPage -= 1; loadAudit()">Назад</button><span>Страница {{ auditPage }}</span><button class="button button--secondary" :disabled="audit.length < 50" @click="auditPage += 1; loadAudit()">Далее</button></div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ComputerDesktopIcon } from '@heroicons/vue/24/outline'
import api, { apiError } from '../api/client'
import { moscowDateTime, relativeTime } from '../utils/formatters'
import { useToast } from '../composables/useToast'
import PageHeader from '../components/PageHeader.vue'
import UiBadge from '../components/UiBadge.vue'
import DataTable from '../components/DataTable.vue'
import LoadingState from '../components/LoadingState.vue'
import ErrorState from '../components/ErrorState.vue'
const toast = useToast()
const tab = ref('sessions'); const loading = ref(true); const saving = ref(false); const error = ref(''); const sessions = ref([]); const audit = ref([]); const auditPage = ref(1); const settings = reactive({})
const auditFilters = reactive({ staff_email: '', action: '' })
const tabs = [{ id: 'sessions', label: 'Сессии' }, { id: 'settings', label: 'Настройки' }, { id: 'audit', label: 'Аудит-лог' }]
const sessionColumns = [{ key: 'staff', label: 'Сотрудник' }, { key: 'device', label: 'Устройство' }, { key: 'location', label: 'География' }, { key: 'last_seen_at', label: 'Последняя активность' }, { key: 'actions', label: '', class: 'cell-actions' }]
const auditColumns = [{ key: 'created_at', label: 'Дата' }, { key: 'staff_email', label: 'Сотрудник' }, { key: 'action', label: 'Действие' }, { key: 'description', label: 'Описание' }, { key: 'target', label: 'Объект' }]
const ipWhitelistText = computed({ get: () => (settings.ip_whitelist || []).join('\n'), set: (value) => { settings.ip_whitelist = value.split('\n').map((x) => x.trim()).filter(Boolean) } })
const deviceName = (ua = '') => `${/Mac/i.test(ua) ? 'macOS' : /Windows/i.test(ua) ? 'Windows' : /Linux/i.test(ua) ? 'Linux' : 'Устройство'} · ${/Chrome/i.test(ua) ? 'Chrome' : /Safari/i.test(ua) ? 'Safari' : /Firefox/i.test(ua) ? 'Firefox' : 'Браузер'}`
async function loadSessions() { sessions.value = (await api.get('/admin/security/sessions')).data.items || [] }
async function loadSettings() { Object.assign(settings, (await api.get('/admin/settings')).data) }
async function loadAudit() { const params = { page: auditPage.value, limit: 50 }; Object.entries(auditFilters).forEach(([k, v]) => { if (v) params[k] = v }); audit.value = (await api.get('/admin/audit-log', { params })).data.items || [] }
async function loadCurrent() { loading.value = true; error.value = ''; try { if (tab.value === 'sessions') await loadSessions(); else if (tab.value === 'settings') await loadSettings(); else await loadAudit() } catch (err) { error.value = apiError(err) } finally { loading.value = false } }
async function revokeSession(row) { try { await api.post(`/admin/security/sessions/${row.id}/revoke`); toast.success('Сессия завершена'); await loadSessions() } catch (err) { toast.error(apiError(err)) } }
async function saveSettings() { saving.value = true; try { const payload = { ...settings }; delete payload.team_2fa_stats; await api.patch('/admin/settings', payload); toast.success('Настройки сохранены') } catch (err) { toast.error(apiError(err)) } finally { saving.value = false } }
watch(tab, loadCurrent)
onMounted(loadCurrent)
</script>
