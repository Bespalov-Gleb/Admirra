<template>
  <div>
    <PageHeader title="Сотрудники" description="Доступы внутренней команды и роли." eyebrow="Команда">
      <button class="button button--primary" @click="inviteOpen = true"><UserPlusIcon />Добавить сотрудника</button>
    </PageHeader>
    <LoadingState v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <DataTable v-else :columns="columns" :rows="items" :total="items.length" :page-size="100">
      <template #cell-user="{ row }"><div class="user-cell"><span class="avatar avatar--small">{{ initials(row) }}</span><span><strong>{{ row.full_name || 'Без имени' }}</strong><small>{{ row.email }}</small></span></div></template>
      <template #cell-role="{ row }"><select class="table-select" :value="row.role" :disabled="row.user_id === auth.user?.id" @change="changeRole(row, $event.target.value)"><option value="SUPERADMIN">Super Admin</option><option value="STAFF_MANAGER">Менеджер</option><option value="SEO">SEO</option></select></template>
      <template #cell-status="{ row }"><UiBadge :label="statusLabel(row.status)" :tone="statusTone(row.status)" dot /></template>
      <template #cell-sessions="{ row }">{{ number(row.active_sessions) }}</template>
      <template #cell-actions="{ row }"><div class="row-actions"><button v-if="row.status === 'pending'" class="button button--tiny button--secondary" @click="resend(row)">Повторить инвайт</button><button v-else-if="row.is_active" class="icon-button icon-button--danger" title="Отключить" :disabled="row.user_id === auth.user?.id" @click="toggle(row, false)"><NoSymbolIcon /></button><button v-else class="icon-button" title="Активировать" @click="toggle(row, true)"><CheckCircleIcon /></button></div></template>
    </DataTable>

    <AppModal :open="inviteOpen" title="Добавить сотрудника" eyebrow="Новый доступ" @close="inviteOpen = false">
      <form id="staff-invite-form" class="form-grid" @submit.prevent="invite">
        <label class="field"><span>Имя</span><input v-model.trim="inviteForm.first_name" required /></label>
        <label class="field"><span>Фамилия</span><input v-model.trim="inviteForm.last_name" /></label>
        <label class="field field--wide"><span>Рабочая почта</span><input v-model.trim="inviteForm.email" type="email" required /></label>
        <label class="field field--wide"><span>Роль</span><select v-model="inviteForm.role"><option value="STAFF_MANAGER">Менеджер</option><option value="SEO">SEO</option><option value="SUPERADMIN">Super Admin</option></select></label>
      </form>
      <template #footer><button class="button button--secondary" @click="inviteOpen = false">Отмена</button><button form="staff-invite-form" class="button button--primary" :disabled="actionLoading">{{ actionLoading ? 'Отправляем…' : 'Отправить приглашение' }}</button></template>
    </AppModal>

    <AppModal :open="Boolean(inviteResult)" title="Приглашение создано" eyebrow="Готово" @close="inviteResult = null">
      <p class="muted">Письмо {{ inviteResult?.email_sent ? 'отправлено' : 'не было отправлено автоматически' }}. Ссылку можно передать сотруднику вручную:</p>
      <div class="copy-field"><input :value="inviteResult?.invite_url" readonly /><button class="button button--secondary" @click="copyInvite">Скопировать</button></div>
    </AppModal>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { CheckCircleIcon, NoSymbolIcon, UserPlusIcon } from '@heroicons/vue/24/outline'
import api, { apiError } from '../api/client'
import { number } from '../utils/formatters'
import { useAuthStore } from '../stores/auth'
import { useToast } from '../composables/useToast'
import PageHeader from '../components/PageHeader.vue'
import LoadingState from '../components/LoadingState.vue'
import ErrorState from '../components/ErrorState.vue'
import DataTable from '../components/DataTable.vue'
import UiBadge from '../components/UiBadge.vue'
import AppModal from '../components/AppModal.vue'
const auth = useAuthStore()
const toast = useToast()
const items = ref([])
const loading = ref(true)
const error = ref('')
const inviteOpen = ref(false)
const inviteResult = ref(null)
const actionLoading = ref(false)
const inviteForm = reactive({ first_name: '', last_name: '', email: '', role: 'STAFF_MANAGER' })
const columns = [{ key: 'user', label: 'Сотрудник' }, { key: 'role', label: 'Роль' }, { key: 'status', label: 'Статус' }, { key: 'sessions', label: 'Активные сессии' }, { key: 'actions', label: '', class: 'cell-actions' }]
const initials = (row) => (row.full_name || row.email || '?').split(/\s|@/).filter(Boolean).slice(0, 2).map((x) => x[0]).join('').toUpperCase()
const statusLabel = (value) => ({ active: 'Активен', pending: 'Ожидает', inactive: 'Отключён' })[value] || value
const statusTone = (value) => ({ active: 'success', pending: 'warning', inactive: 'neutral' })[value] || 'neutral'
async function load() { loading.value = true; error.value = ''; try { items.value = (await api.get('/admin/staff')).data.items || [] } catch (err) { error.value = apiError(err) } finally { loading.value = false } }
async function invite() {
  actionLoading.value = true
  try {
    inviteResult.value = (await api.post('/admin/staff/invite', inviteForm)).data
    inviteOpen.value = false
    Object.assign(inviteForm, { first_name: '', last_name: '', email: '', role: 'STAFF_MANAGER' })
    await load()
  } catch (err) { toast.error(apiError(err)) } finally { actionLoading.value = false }
}
async function changeRole(row, role) { try { await api.patch(`/admin/staff/${row.user_id}/role`, { role }); toast.success('Роль обновлена'); await load() } catch (err) { toast.error(apiError(err)); await load() } }
async function toggle(row, active) { try { await api.post(`/admin/staff/${row.user_id}/${active ? 'reactivate' : 'deactivate'}`); toast.success(active ? 'Сотрудник активирован' : 'Сотрудник отключён'); await load() } catch (err) { toast.error(apiError(err)) } }
async function resend(row) { try { inviteResult.value = (await api.post(`/admin/staff/${row.user_id}/resend-invite`)).data; toast.success('Приглашение обновлено') } catch (err) { toast.error(apiError(err)) } }
async function copyInvite() { await navigator.clipboard.writeText(inviteResult.value.invite_url); toast.success('Ссылка скопирована') }
onMounted(load)
</script>
