<template>
  <div>
    <PageHeader title="Пользователи" description="Аккаунты клиентов, тарифы, проекты и использование AI." eyebrow="Управление">
      <UiBadge :label="`${number(total)} аккаунтов`" tone="info" />
    </PageHeader>
    <section class="toolbar panel">
      <SearchInput v-model="filters.search" placeholder="Имя, email или ID проекта" @search="resetAndLoad" />
      <select v-model="filters.plan" @change="resetAndLoad"><option value="">Все тарифы</option><option value="start">Старт</option><option value="basic">Базовый</option><option value="standard">Стандарт</option><option value="white_label">White Label</option></select>
      <select v-model="filters.status" @change="resetAndLoad"><option value="">Все статусы</option><option value="active">Активные</option><option value="blocked">Заблокированные</option></select>
      <button class="button button--secondary" @click="clearFilters"><XMarkIcon />Сбросить</button>
    </section>

    <LoadingState v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <DataTable v-else :columns="columns" :rows="items" :total="total" :page="page" :page-size="25" @page="changePage">
      <template #cell-user="{ row }">
        <RouterLink :to="`/users/${row.user_id}`" class="user-cell"><span class="avatar avatar--small">{{ initials(row.full_name, row.email) }}</span><span><strong>{{ row.full_name || 'Без имени' }}</strong><small>{{ row.email }}</small></span></RouterLink>
      </template>
      <template #cell-plan_code="{ row }"><UiBadge :label="planLabel(row.plan_code)" :tone="planTone(row.plan_code)" /></template>
      <template #cell-projects="{ row }"><strong>{{ row.projects_used }}</strong><span class="muted"> / {{ row.projects_limit }}</span></template>
      <template #cell-ai="{ row }"><ProgressBar :value="ratio(row.ai_used, row.ai_limit)" :label="`${number(row.ai_used)} / ${number(row.ai_limit)}`" /></template>
      <template #cell-status="{ row }"><UiBadge :label="row.is_active ? 'Активен' : 'Заблокирован'" :tone="row.is_active ? 'success' : 'danger'" dot /></template>
      <template #cell-last_login_at="{ row }"><span :title="moscowDateTime(row.last_login_at)">{{ relativeTime(row.last_login_at) }}</span></template>
      <template #cell-actions="{ row }">
        <div class="row-actions">
          <button class="icon-button" title="Войти как пользователь" @click="impersonate(row)"><ArrowTopRightOnSquareIcon /></button>
          <RouterLink class="icon-button" :to="`/users/${row.user_id}`" title="Открыть карточку"><ChevronRightIcon /></RouterLink>
          <button class="icon-button" :class="{ 'icon-button--danger': row.is_active }" :title="row.is_active ? 'Заблокировать' : 'Разблокировать'" @click="selected = row; confirmType = row.is_active ? 'block' : 'unblock'"><NoSymbolIcon v-if="row.is_active" /><CheckCircleIcon v-else /></button>
        </div>
      </template>
    </DataTable>

    <ConfirmDialog
      :open="Boolean(confirmType)"
      :title="confirmType === 'block' ? 'Заблокировать пользователя?' : 'Разблокировать пользователя?'"
      :description="confirmType === 'block' ? `Пользователь ${selected?.email} потеряет доступ к сервису.` : `Пользователь ${selected?.email} снова сможет войти в сервис.`"
      :confirm-label="confirmType === 'block' ? 'Заблокировать' : 'Разблокировать'"
      :require-reason="confirmType === 'block'"
      :danger="confirmType === 'block'"
      :loading="actionLoading"
      @close="confirmType = ''"
      @confirm="performStatusAction"
    />
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ArrowTopRightOnSquareIcon, CheckCircleIcon, ChevronRightIcon, NoSymbolIcon, XMarkIcon } from '@heroicons/vue/24/outline'
import api, { apiError } from '../api/client'
import { moscowDateTime, number, planLabel, relativeTime } from '../utils/formatters'
import { useToast } from '../composables/useToast'
import { openImpersonatedCabinet } from '../utils/impersonation'
import PageHeader from '../components/PageHeader.vue'
import UiBadge from '../components/UiBadge.vue'
import SearchInput from '../components/SearchInput.vue'
import DataTable from '../components/DataTable.vue'
import ProgressBar from '../components/ProgressBar.vue'
import LoadingState from '../components/LoadingState.vue'
import ErrorState from '../components/ErrorState.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'

const toast = useToast()
const items = ref([])
const total = ref(0)
const page = ref(1)
const loading = ref(true)
const actionLoading = ref(false)
const error = ref('')
const selected = ref(null)
const confirmType = ref('')
const filters = reactive({ search: '', plan: '', status: '' })
const columns = [
  { key: 'user', label: 'Пользователь' },
  { key: 'plan_code', label: 'Тариф' },
  { key: 'projects', label: 'Проекты' },
  { key: 'ai', label: 'AI-лимит', class: 'cell-progress' },
  { key: 'status', label: 'Статус' },
  { key: 'last_login_at', label: 'Последний вход' },
  { key: 'actions', label: '', class: 'cell-actions' },
]
const initials = (name, email) => (name || email || '?').split(/\s|@/).filter(Boolean).slice(0, 2).map((x) => x[0]).join('').toUpperCase()
const ratio = (used, limit) => Number(limit) ? Number(used || 0) * 100 / Number(limit) : 0
const planTone = (plan) => ({ standard: 'info', white_label: 'violet', basic: 'success', start: 'neutral' })[plan] || 'neutral'

async function load() {
  loading.value = true
  error.value = ''
  try {
    const params = { page: page.value, limit: 25 }
    Object.entries(filters).forEach(([key, value]) => { if (value) params[key] = value })
    const { data } = await api.get('/admin/users', { params })
    items.value = (data.items || []).map((item) => ({
      ...item,
      projects_used: item.projects_used ?? item.projects?.used ?? 0,
      projects_limit: item.projects_limit ?? item.projects?.limit ?? 0,
      ai_used: item.ai_used ?? item.ai_requests?.used ?? 0,
      ai_limit: item.ai_limit ?? item.ai_requests?.limit ?? 0,
    }))
    total.value = data.total || 0
  } catch (err) {
    error.value = apiError(err)
  } finally {
    loading.value = false
  }
}
const resetAndLoad = () => { page.value = 1; load() }
const changePage = (value) => { page.value = value; load() }
const clearFilters = () => { Object.assign(filters, { search: '', plan: '', status: '' }); resetAndLoad() }

async function impersonate(row) {
  try {
    await openImpersonatedCabinet(async () => {
      const { data } = await api.post(`/admin/users/${row.user_id}/impersonate`)
      return data.access_token
    })
    toast.info(`Открываем кабинет ${row.email} в новой вкладке`)
  } catch (err) { toast.error(apiError(err)) }
}

async function performStatusAction(reason) {
  actionLoading.value = true
  try {
    const id = selected.value.user_id
    if (confirmType.value === 'block') await api.post(`/admin/users/${id}/block`, { reason })
    else await api.post(`/admin/users/${id}/unblock`)
    toast.success(confirmType.value === 'block' ? 'Пользователь заблокирован' : 'Пользователь разблокирован')
    confirmType.value = ''
    await load()
  } catch (err) { toast.error(apiError(err)) } finally { actionLoading.value = false }
}
onMounted(load)
</script>
