<template>
  <div>
    <PageHeader title="История действий" description="События пользователей для работы поддержки." eyebrow="Менеджер" />
    <section class="toolbar panel">
      <SearchInput v-model="filters.search" placeholder="Поиск по описанию" @search="resetAndLoad" />
      <select v-model="filters.period" @change="resetAndLoad"><option value="today">Сегодня</option><option value="week">Неделя</option><option value="month">Месяц</option></select>
      <input v-model="filters.event_type" class="compact-input" placeholder="Тип события" @keyup.enter="resetAndLoad" />
      <input v-model="filters.user_id" class="compact-input" placeholder="UUID пользователя" @keyup.enter="resetAndLoad" />
    </section>
    <LoadingState v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <DataTable v-else :columns="columns" :rows="items" :total="items.length" :page="1" :page-size="50">
      <template #cell-created_at="{ row }">{{ moscowDateTime(row.created_at) }}</template>
      <template #cell-event_type="{ row }"><UiBadge :label="row.event_type || 'Событие'" tone="neutral" /></template>
      <template #cell-user_id="{ row }"><RouterLink v-if="row.user_id" :to="`/manager/users/${row.user_id}`" class="text-link">{{ row.user_id.slice(0, 8) }}…</RouterLink><span v-else>—</span></template>
    </DataTable>
    <div v-if="!loading && !error" class="simple-pager"><button class="button button--secondary" :disabled="page <= 1" @click="page -= 1; load()">Назад</button><span>Страница {{ page }}</span><button class="button button--secondary" :disabled="items.length < 50" @click="page += 1; load()">Далее</button></div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import api, { apiError } from '../api/client'
import { moscowDateTime } from '../utils/formatters'
import PageHeader from '../components/PageHeader.vue'
import SearchInput from '../components/SearchInput.vue'
import LoadingState from '../components/LoadingState.vue'
import ErrorState from '../components/ErrorState.vue'
import DataTable from '../components/DataTable.vue'
import UiBadge from '../components/UiBadge.vue'
const items = ref([]); const loading = ref(true); const error = ref(''); const page = ref(1)
const filters = reactive({ search: '', period: 'week', event_type: '', user_id: '' })
const columns = [{ key: 'created_at', label: 'Дата' }, { key: 'event_type', label: 'Тип' }, { key: 'description', label: 'Описание' }, { key: 'action', label: 'Действие' }, { key: 'user_id', label: 'Пользователь' }]
async function load() { loading.value = true; error.value = ''; try { const params = { period: filters.period, page: page.value, limit: 50 }; Object.entries(filters).forEach(([k, v]) => { if (v && k !== 'period') params[k] = v }); items.value = (await api.get('/manager/events', { params })).data.items || [] } catch (err) { error.value = apiError(err) } finally { loading.value = false } }
const resetAndLoad = () => { page.value = 1; load() }
onMounted(load)
</script>
