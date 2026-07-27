<template>
  <div>
    <PageHeader :title="article.title || 'Редактор статьи'" :description="saveStatus" eyebrow="SEO-редактор">
      <RouterLink to="/seo/blog" class="button button--ghost"><ArrowLeftIcon />К списку</RouterLink>
      <button class="button button--secondary" @click="save(true)"><CloudArrowUpIcon />Сохранить</button>
      <button class="button button--primary" @click="togglePublish">{{ article.status === 'published' ? 'Снять с публикации' : 'Опубликовать' }}</button>
    </PageHeader>
    <LoadingState v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <div v-else class="editor-layout">
      <section class="panel editor-main">
        <label class="editor-title"><span>Заголовок статьи</span><input v-model="article.title" @input="markDirty" /></label>
        <label class="field"><span>Slug</span><div class="slug-input"><span>/blog/</span><input v-model="article.slug" @input="markDirty" /></div></label>
        <div class="editor-toolbar">
          <button v-for="tool in tools" :key="tool.command" :title="tool.title" @click="exec(tool.command, tool.value)"><component :is="tool.icon" v-if="tool.icon" /><span v-else>{{ tool.label }}</span></button>
          <label class="editor-upload"><PhotoIcon /><input type="file" accept="image/*" @change="uploadInline" /></label>
        </div>
        <div ref="editor" class="wysiwyg" contenteditable="true" @input="editorInput" @blur="syncContent" />
      </section>
      <aside class="editor-side">
        <section class="panel seo-score">
          <div class="score-ring" :style="{ '--score': `${article.seo_score || 0}%` }"><strong>{{ article.seo_score || 0 }}</strong><small>/ 100</small></div>
          <div><h3>SEO-оценка</h3><p>Расчёт выполняется backend.</p></div>
        </section>
        <section class="panel">
          <div class="panel__header"><div><p class="eyebrow">Сниппет</p><h2>Метаданные</h2></div></div>
          <label class="field"><span>Meta Title <b>{{ (article.meta_title || '').length }}/65</b></span><input v-model="article.meta_title" maxlength="80" @input="markDirty" /></label>
          <label class="field"><span>Meta Description <b>{{ (article.meta_description || '').length }}/165</b></span><textarea v-model="article.meta_description" rows="5" maxlength="220" @input="markDirty" /></label>
          <label class="field"><span>Ключевые слова</span><input v-model="article.keywords" placeholder="аналитика, реклама, отчёты" @input="markDirty" /></label>
          <label class="field"><span>Категория</span><input v-model="article.category" @input="markDirty" /></label>
        </section>
        <section class="panel">
          <div class="panel__header"><div><p class="eyebrow">Проверка</p><h2>SEO-чеклист</h2></div></div>
          <ul class="checklist"><li v-for="issue in knownIssues" :key="issue.key" :class="{ done: !article.seo_issues?.includes(issue.key) }"><CheckCircleIcon v-if="!article.seo_issues?.includes(issue.key)" /><ExclamationCircleIcon v-else />{{ issue.label }}</li></ul>
        </section>
        <section class="panel">
          <label class="field"><span>Обложка</span><input v-model="article.cover_url" placeholder="/static/..." @input="markDirty" /></label>
          <label class="button button--secondary button--full file-button"><PhotoIcon />Загрузить изображение<input type="file" accept="image/*" @change="uploadCover" /></label>
          <img v-if="article.cover_url" :src="article.cover_url" class="cover-preview" alt="Обложка статьи" />
        </section>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeftIcon, CheckCircleIcon, CloudArrowUpIcon, ExclamationCircleIcon, LinkIcon, ListBulletIcon, PhotoIcon } from '@heroicons/vue/24/outline'
import api, { apiError } from '../api/client'
import { useToast } from '../composables/useToast'
import PageHeader from '../components/PageHeader.vue'
import LoadingState from '../components/LoadingState.vue'
import ErrorState from '../components/ErrorState.vue'
const route = useRoute(); const toast = useToast(); const article = ref({}); const editor = ref(null); const loading = ref(true); const error = ref(''); const dirty = ref(false); const saveStatus = ref('Загрузка…'); let timer
const tools = [{ command: 'bold', label: 'B', title: 'Жирный' }, { command: 'italic', label: 'I', title: 'Курсив' }, { command: 'underline', label: 'U', title: 'Подчёркнутый' }, { command: 'formatBlock', value: 'H2', label: 'H2', title: 'Заголовок H2' }, { command: 'formatBlock', value: 'H3', label: 'H3', title: 'Заголовок H3' }, { command: 'insertUnorderedList', icon: ListBulletIcon, title: 'Маркированный список' }, { command: 'insertOrderedList', label: '1.', title: 'Нумерованный список' }, { command: 'formatBlock', value: 'BLOCKQUOTE', label: '❝', title: 'Цитата' }, { command: 'callout', label: '!', title: 'Callout-блок' }, { command: 'createLink', icon: LinkIcon, title: 'Ссылка' }]
const knownIssues = [{ key: 'no_title', label: 'Meta Title заполнен' }, { key: 'short_title', label: 'Meta Title достаточной длины' }, { key: 'long_title', label: 'Meta Title не слишком длинный' }, { key: 'no_description', label: 'Meta Description заполнен' }, { key: 'short_description', label: 'Description достаточной длины' }, { key: 'long_description', label: 'Description не слишком длинный' }]
async function load() { loading.value = true; error.value = ''; try { article.value = (await api.get(`/seo/articles/${route.params.id}`)).data; await nextTick(); editor.value.innerHTML = article.value.content_html || ''; saveStatus.value = 'Все изменения сохранены' } catch (err) { error.value = apiError(err) } finally { loading.value = false } }
const markDirty = () => { dirty.value = true; saveStatus.value = 'Есть несохранённые изменения' }
const editorInput = () => { markDirty() }
const syncContent = () => { if (editor.value) article.value.content_html = editor.value.innerHTML }
function exec(command, value) { if (command === 'createLink') value = window.prompt('Адрес ссылки') || ''; if (command === 'callout') document.execCommand('insertHTML', false, '<aside class="callout"><strong>Важно:</strong> текст примечания</aside>'); else if (value || command !== 'createLink') document.execCommand(command, false, value); editor.value?.focus(); syncContent(); markDirty() }
async function save(manual = false) { if (!dirty.value && !manual) return; syncContent(); saveStatus.value = 'Сохраняем…'; try { const payload = {}; ['slug', 'title', 'content_html', 'category', 'meta_title', 'meta_description', 'keywords', 'cover_url'].forEach((key) => { payload[key] = article.value[key] ?? null }); await api.patch(`/seo/articles/${route.params.id}`, payload); dirty.value = false; saveStatus.value = `Сохранено ${new Intl.DateTimeFormat('ru-RU', { hour: '2-digit', minute: '2-digit' }).format(new Date())}`; if (manual) toast.success('Статья сохранена') } catch (err) { saveStatus.value = 'Ошибка сохранения'; toast.error(apiError(err)) } }
async function togglePublish() { await save(true); try { const action = article.value.status === 'published' ? 'unpublish' : 'publish'; const { data } = await api.post(`/seo/articles/${route.params.id}/${action}`); article.value.status = data.status; toast.success(action === 'publish' ? 'Статья опубликована' : 'Статья снята с публикации') } catch (err) { toast.error(apiError(err)) } }
async function upload(file) { const form = new FormData(); form.append('file', file); return (await api.post('/seo/upload/image', form)).data.url }
async function uploadCover(event) { const file = event.target.files?.[0]; if (!file) return; try { article.value.cover_url = await upload(file); markDirty(); toast.success('Обложка загружена') } catch (err) { toast.error(apiError(err)) } }
async function uploadInline(event) { const file = event.target.files?.[0]; if (!file) return; try { const url = await upload(file); const alt = window.prompt('Alt-текст изображения') || ''; document.execCommand('insertHTML', false, `<img src="${url}" alt="${alt.replaceAll('"', '&quot;')}">`); syncContent(); markDirty() } catch (err) { toast.error(apiError(err)) } }
onMounted(() => { load(); timer = window.setInterval(() => save(false), 10000) })
onBeforeUnmount(() => { window.clearInterval(timer); if (dirty.value) save(false) })
</script>
