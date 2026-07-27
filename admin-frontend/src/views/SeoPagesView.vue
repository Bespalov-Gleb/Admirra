<template>
  <div>
    <PageHeader title="Мета-страницы" description="Title и Description системных страниц сайта." eyebrow="SEO" />
    <LoadingState v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <div v-else class="meta-page-list">
      <article v-for="page in pages" :key="page.id" class="panel meta-page">
        <header><div><UiBadge :label="page.path" tone="neutral" /><h2>{{ page.title || page.path }}</h2></div><UiBadge :label="page.meta_issues?.length ? `${page.meta_issues.length} замечания` : 'Готово'" :tone="page.meta_issues?.length ? 'warning' : 'success'" /></header>
        <div class="meta-page__body">
          <div class="meta-form"><label class="field"><span>Meta Title <b>{{ (page.meta_title || '').length }}/65</b></span><input v-model="page.meta_title" /></label><label class="field"><span>Meta Description <b>{{ (page.meta_description || '').length }}/165</b></span><textarea v-model="page.meta_description" rows="4" /></label><button class="button button--primary" @click="save(page)">Сохранить</button></div>
          <div class="snippet"><small>{{ host }}{{ page.path }}</small><h3>{{ page.meta_title || page.title || 'Заголовок страницы' }}</h3><p>{{ page.meta_description || 'Описание страницы появится здесь.' }}</p></div>
        </div>
      </article>
      <EmptyState v-if="!pages.length" title="Страницы не найдены" />
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import api, { apiError } from '../api/client'
import { useToast } from '../composables/useToast'
import PageHeader from '../components/PageHeader.vue'
import LoadingState from '../components/LoadingState.vue'
import ErrorState from '../components/ErrorState.vue'
import EmptyState from '../components/EmptyState.vue'
import UiBadge from '../components/UiBadge.vue'
const toast = useToast(); const pages = ref([]); const loading = ref(true); const error = ref(''); const host = 'https://admirra.ru'
async function load() { loading.value = true; error.value = ''; try { pages.value = (await api.get('/seo/pages')).data.items || [] } catch (err) { error.value = apiError(err) } finally { loading.value = false } }
async function save(page) { try { await api.patch(`/seo/pages/${page.id}`, { meta_title: page.meta_title || null, meta_description: page.meta_description || null, title: page.title || null }); toast.success(`Страница ${page.path} сохранена`) } catch (err) { toast.error(apiError(err)) } }
onMounted(load)
</script>
