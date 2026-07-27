<template>
  <div>
    <PageHeader title="Блог" description="Статьи, публикации и качество метаданных." eyebrow="SEO">
      <button class="button button--primary" :disabled="creating" @click="createArticle"><PlusIcon />Новая статья</button>
    </PageHeader>
    <LoadingState v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <template v-else>
      <div class="kpi-grid kpi-grid--4-compact">
        <article class="mini-kpi"><span>Опубликовано</span><strong>{{ number(summary.published_count) }}</strong></article>
        <article class="mini-kpi"><span>Черновики</span><strong>{{ number(summary.draft_count) }}</strong></article>
        <article class="mini-kpi"><span>Трафик / месяц</span><strong>{{ number(summary.traffic_monthly) }}</strong></article>
        <article class="mini-kpi mini-kpi--warning"><span>Без мета</span><strong>{{ number(summary.missing_meta_count) }}</strong></article>
      </div>
      <section class="toolbar panel">
        <SearchInput v-model="filters.q" placeholder="Поиск по заголовку" @search="loadArticles" />
        <select v-model="filters.status" @change="loadArticles"><option value="">Все статусы</option><option value="draft">Черновики</option><option value="review">На проверке</option><option value="published">Опубликовано</option><option value="archived">Архив</option></select>
      </section>
      <DataTable :columns="columns" :rows="articles" :total="articles.length" :page-size="100">
        <template #cell-title="{ row }"><RouterLink :to="`/seo/blog/${row.id}`" class="article-cell"><strong>{{ row.title }}</strong><small>/{{ row.slug }}</small></RouterLink></template>
        <template #cell-status="{ row }"><UiBadge :label="statusLabel(row.status)" :tone="statusTone(row.status)" dot /></template>
        <template #cell-meta="{ row }"><UiBadge :label="row.meta_issues?.length ? `${row.meta_issues.length} замечания` : 'Готово'" :tone="row.meta_issues?.length ? 'warning' : 'success'" /></template>
        <template #cell-traffic_monthly="{ row }">{{ number(row.traffic_monthly) }}</template>
        <template #cell-updated_at="{ row }">{{ relativeTime(row.updated_at) }}</template>
        <template #cell-actions="{ row }"><div class="row-actions"><button class="button button--tiny button--secondary" @click="togglePublish(row)">{{ row.status === 'published' ? 'Снять' : 'Опубликовать' }}</button><RouterLink :to="`/seo/blog/${row.id}`" class="icon-button"><PencilSquareIcon /></RouterLink></div></template>
      </DataTable>
    </template>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { PencilSquareIcon, PlusIcon } from '@heroicons/vue/24/outline'
import api, { apiError } from '../api/client'
import { number, relativeTime } from '../utils/formatters'
import { useToast } from '../composables/useToast'
import PageHeader from '../components/PageHeader.vue'
import LoadingState from '../components/LoadingState.vue'
import ErrorState from '../components/ErrorState.vue'
import SearchInput from '../components/SearchInput.vue'
import DataTable from '../components/DataTable.vue'
import UiBadge from '../components/UiBadge.vue'
const router = useRouter(); const toast = useToast()
const summary = ref({}); const articles = ref([]); const loading = ref(true); const creating = ref(false); const error = ref(''); const filters = reactive({ q: '', status: '' })
const columns = [{ key: 'title', label: 'Статья' }, { key: 'status', label: 'Статус' }, { key: 'meta', label: 'SEO' }, { key: 'traffic_monthly', label: 'Трафик' }, { key: 'updated_at', label: 'Обновлено' }, { key: 'actions', label: '', class: 'cell-actions' }]
const statusLabel = (value) => ({ draft: 'Черновик', review: 'На проверке', published: 'Опубликовано', archived: 'Архив' })[value] || value
const statusTone = (value) => ({ draft: 'neutral', review: 'warning', published: 'success', archived: 'violet' })[value] || 'neutral'
async function loadArticles() { const params = {}; if (filters.q) params.q = filters.q; if (filters.status) params.status = filters.status; articles.value = (await api.get('/seo/articles', { params })).data.items || [] }
async function load() { loading.value = true; error.value = ''; try { const [summaryRes] = await Promise.all([api.get('/seo/articles/summary'), loadArticles()]); summary.value = summaryRes.data } catch (err) { error.value = apiError(err) } finally { loading.value = false } }
async function createArticle() { creating.value = true; try { const seed = Date.now(); const { data } = await api.post('/seo/articles', { title: 'Новая статья', slug: `new-article-${seed}`, content_html: '' }); router.push(`/seo/blog/${data.id}`) } catch (err) { toast.error(apiError(err)) } finally { creating.value = false } }
async function togglePublish(row) { try { await api.post(`/seo/articles/${row.id}/${row.status === 'published' ? 'unpublish' : 'publish'}`); toast.success(row.status === 'published' ? 'Статья снята с публикации' : 'Статья опубликована'); await load() } catch (err) { toast.error(apiError(err)) } }
onMounted(load)
</script>
