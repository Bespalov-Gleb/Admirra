<template>
  <div>
    <PageHeader title="Активность" description="События клиентского сервиса в хронологическом порядке." eyebrow="Наблюдение" />
    <section class="toolbar panel">
      <SearchInput v-model="filters.q" placeholder="Поиск по описанию" @search="load" />
      <select v-model="filters.days" @change="load"><option :value="1">Сегодня</option><option :value="7">7 дней</option><option :value="30">30 дней</option><option :value="90">90 дней</option></select>
      <input v-model="filters.event_type" class="compact-input" placeholder="Тип события" @keyup.enter="load" />
      <button class="button button--secondary" @click="load"><ArrowPathIcon />Обновить</button>
    </section>
    <LoadingState v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <section v-else class="timeline panel">
      <article v-for="item in items" :key="item.id">
        <span class="timeline__dot" />
        <div><div class="timeline__meta"><UiBadge :label="item.event_type || item.action || 'Событие'" tone="neutral" /><time :title="moscowDateTime(item.created_at)">{{ relativeTime(item.created_at) }}</time></div><strong>{{ item.description || item.action || 'Без описания' }}</strong><small v-if="item.actor_email">{{ item.actor_email }}</small></div>
      </article>
      <EmptyState v-if="!items.length" title="Событий не найдено" description="За выбранный период событий нет." />
      <div v-if="items.length >= limit && limit < 500" class="load-more"><button class="button button--secondary" @click="limit = Math.min(limit + 100, 500); load()">Показать ещё</button></div>
    </section>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ArrowPathIcon } from '@heroicons/vue/24/outline'
import api, { apiError } from '../api/client'
import { moscowDateTime, relativeTime } from '../utils/formatters'
import PageHeader from '../components/PageHeader.vue'
import SearchInput from '../components/SearchInput.vue'
import LoadingState from '../components/LoadingState.vue'
import ErrorState from '../components/ErrorState.vue'
import EmptyState from '../components/EmptyState.vue'
import UiBadge from '../components/UiBadge.vue'
const items = ref([]); const loading = ref(true); const error = ref(''); const limit = ref(100)
const filters = reactive({ q: '', days: 7, event_type: '' })
async function load() { loading.value = true; error.value = ''; try { const params = { days: filters.days, limit: limit.value }; if (filters.q) params.q = filters.q; if (filters.event_type) params.event_type = filters.event_type; items.value = (await api.get('/admin/activity', { params })).data.items || [] } catch (err) { error.value = apiError(err) } finally { loading.value = false } }
onMounted(load)
</script>
