<template>
  <div>
    <PageHeader title="Клиенты" description="Рабочая очередь пользователей и быстрый доступ к карточкам." eyebrow="Менеджер" />
    <LoadingState v-if="loading && !items.length" />
    <ErrorState v-else-if="error" :message="error" @retry="loadAll" />
    <template v-else>
      <div class="kpi-grid kpi-grid--3">
        <article class="kpi-card kpi-card--accent"><div class="kpi-card__top"><span>Всего клиентов</span><UsersIcon /></div><strong>{{ number(summary.total_users) }}</strong><small class="muted">Активные аккаунты</small></article>
        <article class="kpi-card"><div class="kpi-card__top"><span>Активны сегодня</span><SignalIcon /></div><strong>{{ number(summary.active_today) }}</strong><small :class="Number(summary.active_today_delta_vs_yesterday) >= 0 ? 'positive' : 'negative'">{{ signed(summary.active_today_delta_vs_yesterday) }} ко вчера</small></article>
        <article class="kpi-card"><div class="kpi-card__top"><span>Триал истекает</span><ClockIcon /></div><strong>{{ number(summary.trial_expiring_soon) }}</strong><small class="muted">В ближайшие 3 дня</small></article>
      </div>
      <section class="toolbar panel">
        <SearchInput v-model="filters.search" placeholder="Имя, email или ID проекта" @search="resetAndLoad" />
        <select v-model="filters.plan" @change="resetAndLoad"><option value="">Все тарифы</option><option value="start">Старт</option><option value="basic">Базовый</option><option value="standard">Стандарт</option><option value="white_label">White Label</option></select>
        <select v-model="filters.status" @change="resetAndLoad"><option value="">Все статусы</option><option value="active">Активные</option><option value="trial">Триал</option><option value="inactive">Неактивные</option></select>
      </section>
      <DataTable :columns="columns" :rows="items" :total="total" :page="page" :page-size="25" @page="changePage">
        <template #cell-user="{ row }"><RouterLink :to="`/manager/users/${row.user_id}`" class="user-cell"><span class="avatar avatar--small">{{ initials(row) }}</span><span><strong>{{ row.full_name }}</strong><small>{{ row.email }}</small></span></RouterLink></template>
        <template #cell-plan_code="{ row }"><UiBadge :label="planLabel(row.plan_code)" tone="info" /></template>
        <template #cell-projects="{ row }">{{ row.projects.used }} <span class="muted">/ {{ row.projects.limit }}</span></template>
        <template #cell-status="{ row }"><UiBadge :label="row.is_active ? 'Активен' : 'Заблокирован'" :tone="row.is_active ? 'success' : 'danger'" dot /></template>
        <template #cell-last_login_at="{ row }">{{ relativeTime(row.last_login_at) }}</template>
        <template #cell-actions="{ row }"><div class="row-actions"><button class="button button--tiny button--secondary" @click="impersonate(row)"><ArrowTopRightOnSquareIcon />Войти</button><RouterLink class="icon-button" :to="`/manager/users/${row.user_id}`"><ChevronRightIcon /></RouterLink></div></template>
      </DataTable>
    </template>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ArrowTopRightOnSquareIcon, ChevronRightIcon, ClockIcon, SignalIcon, UsersIcon } from '@heroicons/vue/24/outline'
import api, { apiError } from '../api/client'
import { number, planLabel, relativeTime } from '../utils/formatters'
import { useToast } from '../composables/useToast'
import { openImpersonatedCabinet } from '../utils/impersonation'
import PageHeader from '../components/PageHeader.vue'
import LoadingState from '../components/LoadingState.vue'
import ErrorState from '../components/ErrorState.vue'
import SearchInput from '../components/SearchInput.vue'
import DataTable from '../components/DataTable.vue'
import UiBadge from '../components/UiBadge.vue'
const toast = useToast()
const summary = ref({}); const items = ref([]); const total = ref(0); const page = ref(1); const loading = ref(true); const error = ref('')
const filters = reactive({ search: '', plan: '', status: '' })
const columns = [{ key: 'user', label: 'Пользователь' }, { key: 'plan_code', label: 'Тариф' }, { key: 'projects', label: 'Проекты' }, { key: 'status', label: 'Статус' }, { key: 'last_login_at', label: 'Последний вход' }, { key: 'actions', label: '', class: 'cell-actions' }]
const initials = (row) => (row.full_name || row.email || '?').split(/\s|@/).filter(Boolean).slice(0, 2).map((x) => x[0]).join('').toUpperCase()
const signed = (value) => `${Number(value) > 0 ? '+' : ''}${number(value || 0)}`
async function loadUsers() { const params = { page: page.value, limit: 25 }; Object.entries(filters).forEach(([k, v]) => { if (v) params[k] = v }); const { data } = await api.get('/manager/users', { params }); items.value = data.items || []; total.value = data.total || 0 }
async function loadAll() { loading.value = true; error.value = ''; try { const [summaryRes] = await Promise.all([api.get('/manager/dashboard/summary'), loadUsers()]); summary.value = summaryRes.data } catch (err) { error.value = apiError(err) } finally { loading.value = false } }
const resetAndLoad = () => { page.value = 1; loadUsers().catch((err) => { error.value = apiError(err) }) }
const changePage = (value) => { page.value = value; loadUsers().catch((err) => { error.value = apiError(err) }) }
async function impersonate(row) { try { await openImpersonatedCabinet(async () => (await api.post(`/manager/users/${row.user_id}/impersonate`)).data.access_token); toast.info(`Открываем кабинет ${row.email}`) } catch (err) { toast.error(apiError(err)) } }
onMounted(loadAll)
</script>
