<template>
  <div>
    <PageHeader :title="user.full_name || 'Карточка клиента'" :description="user.email" :eyebrow="isManager ? 'Клиент менеджера' : 'Пользователь SaaS'">
      <button class="button button--secondary" @click="impersonate"><ArrowTopRightOnSquareIcon />Войти как пользователь</button>
      <button class="button button--ghost" @click="resetSessions"><ArrowPathIcon />Сбросить сессии</button>
      <button v-if="user.is_active" class="button button--danger-soft" @click="confirmType = 'block'"><NoSymbolIcon />Заблокировать</button>
      <button v-else-if="!isManager" class="button button--secondary" @click="confirmType = 'unblock'"><CheckCircleIcon />Разблокировать</button>
      <UiBadge v-else label="Пользователь заблокирован" tone="danger" dot />
    </PageHeader>
    <LoadingState v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <template v-else>
      <section class="profile-summary panel">
        <div class="profile-summary__identity"><span class="avatar avatar--large">{{ initials }}</span><div><h2>{{ user.full_name }}</h2><p>{{ user.email }}</p><div><UiBadge :label="planLabel(user.plan_code)" tone="info" /><UiBadge :label="user.is_active ? 'Активен' : 'Заблокирован'" :tone="user.is_active ? 'success' : 'danger'" dot /></div></div></div>
        <dl><div><dt>Проекты</dt><dd>{{ user.projects?.used || 0 }} / {{ user.projects?.limit || 0 }}</dd></div><div><dt>AI-запросы</dt><dd>{{ number(user.ai_requests?.used) }} / {{ number(user.ai_requests?.limit) }}</dd></div><div><dt>Последний вход</dt><dd>{{ relativeTime(user.last_login_at) }}</dd></div><div><dt>Регистрация</dt><dd>{{ moscowDateTime(user.registered_at) }}</dd></div><div><dt>Источник</dt><dd>{{ user.registration_utm_source || '—' }}</dd></div></dl>
      </section>
      <div class="detail-grid">
        <section class="panel">
          <div class="panel__header"><div><p class="eyebrow">Подключения</p><h2>Интеграции</h2></div><UiBadge :label="String(integrations.length)" tone="neutral" /></div>
          <div class="integration-list">
            <article v-for="item in integrations" :key="item.id || `${item.platform}-${item.account_id}`"><span class="integration-icon">{{ item.platform === 'YANDEX_DIRECT' ? 'Я' : item.platform === 'VK_ADS' ? 'VK' : 'A' }}</span><div><strong>{{ platformLabel(item.platform) }}</strong><small>{{ item.account_id || 'ID не указан' }}</small></div><UiBadge :label="syncLabel(item.sync_status)" :tone="item.sync_status === 'SUCCESS' ? 'success' : item.sync_status === 'FAILED' ? 'danger' : 'neutral'" dot /></article>
          </div>
          <EmptyState v-if="!integrations.length" title="Нет подключений" />
        </section>
        <section class="panel">
          <div class="panel__header"><div><p class="eyebrow">История</p><h2>Последние события</h2></div></div>
          <div class="compact-timeline"><article v-for="(item, index) in history" :key="item.id || index"><span /><div><strong>{{ item.description || item.action || 'Событие' }}</strong><small>{{ relativeTime(item.created_at) }}</small></div></article></div>
          <EmptyState v-if="!history.length" title="История пуста" />
        </section>
      </div>
      <section v-if="isManager" class="panel">
        <div class="panel__header"><div><p class="eyebrow">Поддержка</p><h2>Заметки о клиенте</h2></div></div>
        <form class="note-form" @submit.prevent="addNote"><textarea v-model="newNote" rows="3" placeholder="Добавить внутреннюю заметку…" required /><button class="button button--primary" :disabled="!newNote.trim()">Добавить заметку</button></form>
        <div class="note-list">
          <article v-for="note in notes" :key="note.id">
            <div><strong>{{ note.author_email || 'Сотрудник' }}</strong><span><time>{{ moscowDateTime(note.created_at) }}</time><button v-if="note.can_edit" class="text-button" @click="beginEditNote(note)">Изменить</button></span></div>
            <template v-if="editingNoteId === note.id">
              <textarea v-model="editingNoteBody" rows="3" />
              <div class="row-actions"><button class="button button--tiny button--ghost" @click="editingNoteId = ''">Отмена</button><button class="button button--tiny button--primary" @click="saveNote(note)">Сохранить</button></div>
            </template>
            <p v-else>{{ note.body }}</p>
          </article>
        </div>
        <EmptyState v-if="!notes.length" title="Заметок пока нет" description="Добавьте важную информацию для команды поддержки." />
      </section>
    </template>
    <ConfirmDialog :open="Boolean(confirmType)" :title="confirmType === 'block' ? 'Заблокировать клиента?' : 'Разблокировать клиента?'" :description="confirmType === 'block' ? 'Клиент потеряет доступ к сервису.' : 'Доступ клиента будет восстановлен.'" :confirm-label="confirmType === 'block' ? 'Заблокировать' : 'Разблокировать'" :require-reason="confirmType === 'block'" :danger="confirmType === 'block'" @close="confirmType = ''" @confirm="changeStatus" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowPathIcon, ArrowTopRightOnSquareIcon, CheckCircleIcon, NoSymbolIcon } from '@heroicons/vue/24/outline'
import api, { apiError } from '../api/client'
import { moscowDateTime, number, planLabel, platformLabel, relativeTime } from '../utils/formatters'
import { useToast } from '../composables/useToast'
import { openImpersonatedCabinet } from '../utils/impersonation'
import PageHeader from '../components/PageHeader.vue'
import LoadingState from '../components/LoadingState.vue'
import ErrorState from '../components/ErrorState.vue'
import EmptyState from '../components/EmptyState.vue'
import UiBadge from '../components/UiBadge.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
const route = useRoute(); const toast = useToast(); const isManager = computed(() => route.meta.manager === true)
const user = ref({}); const integrations = ref([]); const history = ref([]); const notes = ref([]); const loading = ref(true); const error = ref(''); const newNote = ref(''); const confirmType = ref(''); const editingNoteId = ref(''); const editingNoteBody = ref('')
const base = computed(() => isManager.value ? '/manager' : '/admin')
const initials = computed(() => (user.value.full_name || user.value.email || '?').split(/\s|@/).filter(Boolean).slice(0, 2).map((x) => x[0]).join('').toUpperCase())
const syncLabel = (value) => ({ SUCCESS: 'Синхронизировано', FAILED: 'Ошибка', PENDING: 'Ожидание', IN_PROGRESS: 'Синхронизация' })[value] || value || 'Неизвестно'
async function load() { loading.value = true; error.value = ''; try { const { data } = await api.get(`${base.value}/users/${route.params.id}`); user.value = data.user || {}; integrations.value = data.integrations || []; history.value = data.history || []; notes.value = data.notes || [] } catch (err) { error.value = apiError(err) } finally { loading.value = false } }
async function impersonate() { try { await openImpersonatedCabinet(async () => (await api.post(`${base.value}/users/${route.params.id}/impersonate`)).data.access_token); toast.info('Кабинет открыт в новой вкладке') } catch (err) { toast.error(apiError(err)) } }
async function resetSessions() { try { await api.post(`${base.value}/users/${route.params.id}/reset-sessions`); toast.success('Команда сброса сессий отправлена') } catch (err) { toast.error(apiError(err)) } }
async function changeStatus(reason) { try { if (confirmType.value === 'block') await api.post(`${base.value}/users/${route.params.id}/block`, { reason }); else await api.post(`${base.value}/users/${route.params.id}/unblock`); toast.success('Статус обновлён'); confirmType.value = ''; await load() } catch (err) { toast.error(apiError(err)) } }
async function addNote() { try { const { data } = await api.post(`/manager/users/${route.params.id}/notes`, { body: newNote.value }); notes.value.unshift(data); newNote.value = ''; toast.success('Заметка добавлена') } catch (err) { toast.error(apiError(err)) } }
function beginEditNote(note) { editingNoteId.value = note.id; editingNoteBody.value = note.body }
async function saveNote(note) { try { await api.patch(`/manager/notes/${note.id}`, { body: editingNoteBody.value }); note.body = editingNoteBody.value; editingNoteId.value = ''; toast.success('Заметка обновлена') } catch (err) { toast.error(apiError(err)) } }
onMounted(load)
</script>
