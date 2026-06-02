<template>
  <div class="integrations-page">
    <div class="page-head">
      <div>
        <h3>Активные интеграции</h3>
        <p>Подключения рекламных кабинетов по всем проектам агентства.</p>
      </div>
      <button class="add-btn" type="button" @click="openWizard()">
        <span>Добавить подключение</span>
        <span class="icon-plus" aria-hidden="true"><span></span><span></span></span>
      </button>
    </div>

    <div class="toolbar">
      <div class="search-wrap">
        <input
          v-model="search"
          class="search-input dark:!bg-[#2C2F3D] dark:!text-white/90 dark:!shadow-[inset_0_0_0_1px_rgba(255,255,255,0.1)] dark:placeholder:!text-white/45"
          type="text"
          placeholder="Поиск по проекту, каналу или кабинету"
        />
        <div class="search-icon dark:!bg-white/10">
          <svg width="7" height="7" viewBox="0 0 16 16" fill="none">
            <circle cx="7" cy="7" r="5.5" stroke="#696969" stroke-width="1.5"/>
            <path d="M11 11L14 14" stroke="#696969" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
        </div>
      </div>
      <div class="sync-note">Автообновление раз в сутки, время указано в МСК.</div>
    </div>

    <div v-if="isLoading" class="empty-state">Загрузка…</div>
    <div v-else-if="groupedIntegrations.length === 0" class="empty-state">
      {{ search ? 'Ничего не найдено' : 'Нет активных интеграций. Добавьте первое подключение.' }}
    </div>

    <div v-else class="project-groups">
      <section v-for="group in groupedIntegrations" :key="group.projectId" class="project-group">
        <div class="project-group__head">
          <div class="project-avatar">{{ group.projectName.slice(0, 2).toUpperCase() }}</div>
          <div>
            <h4>{{ group.projectName }}</h4>
            <p>{{ group.items.length }} {{ plural(group.items.length, ['канал', 'канала', 'каналов']) }}</p>
          </div>
        </div>

        <div class="integration-list">
          <article v-for="item in group.items" :key="item.id" class="int-card">
            <div class="int-card__main">
              <img class="channel-icon" :src="platformIcon(item.platform)" :alt="platformLabel(item.platform)" />
              <div class="int-card__title">
                <h5>{{ platformLabel(item.platform) }}</h5>
                <p>{{ item.account_name || item.account_id || 'Кабинет не выбран' }}</p>
              </div>
            </div>

            <div class="status-stack">
              <span class="status-pill" :class="statusClass(item)">
                <span></span>
                {{ statusLabel(item) }}
              </span>
              <button
                v-if="goalDriftLabel(item)"
                class="goal-drift-chip"
                type="button"
                @click="openEdit(item.id)"
              >
                {{ goalDriftLabel(item) }}
              </button>
              <small>Обновляется раз в сутки</small>
            </div>

            <div class="sync-times">
              <div>
                <span>Последняя</span>
                <strong>{{ formatDate(item.last_sync_at) || 'ещё не было' }}</strong>
              </div>
              <div>
                <span>Следующая</span>
                <strong>{{ nextSyncLabel(item) }}</strong>
              </div>
            </div>

            <button
              class="sync-btn"
              type="button"
              :disabled="syncingIds.has(item.id) || item.sync_status === 'PENDING'"
              @click="syncNow(item)"
            >
              <svg :class="{ spinning: syncingIds.has(item.id) }" width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M20 12a8 8 0 0 1-14.5 4.7M4 12A8 8 0 0 1 18.5 7.3M18.5 3v4.3H14M5.5 21v-4.3H10" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              {{ syncingIds.has(item.id) || item.sync_status === 'PENDING' ? 'Синхронизируется…' : 'Синхронизировать сейчас' }}
            </button>

            <button class="configure-btn" type="button" @click="openEdit(item.id)">Настроить</button>

            <button class="id-chip" type="button" title="Скопировать ID" @click="copyId(item.id)">
              <span>ID {{ shortId(item.id) }}</span>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <rect x="8" y="8" width="11" height="11" rx="2" stroke="currentColor" stroke-width="1.8"/>
                <path d="M5 15H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v1" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
              </svg>
            </button>
          </article>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api/axios'
import { useProjects } from '../../composables/useProjects'
import { useToaster } from '../../composables/useToaster'

const router = useRouter()
const toaster = useToaster()
const { currentProjectId } = useProjects()

const integrations = ref([])
const isLoading = ref(false)
const search = ref('')
const syncingIds = ref(new Set())

const platformCatalog = [
  { id: 'YANDEX_DIRECT', name: 'Yandex Direct', icon: '/admirra/img/icons/yandex-direct.png' },
  { id: 'VK_ADS', name: 'VK Ads', icon: '/admirra/img/icons/vk-ads.png' },
  { id: 'MYTARGET', name: 'MyTarget', icon: '/admirra/img/icons/target.png' },
]

onMounted(fetchIntegrations)

async function fetchIntegrations() {
  isLoading.value = true
  try {
    const { data } = await api.get('integrations/')
    integrations.value = normalizeIntegrations(data)
  } catch (err) {
    console.error('Failed to load integrations:', err)
    integrations.value = []
    toaster.error('Не удалось загрузить интеграции.')
  } finally {
    isLoading.value = false
  }
}

const filteredIntegrations = computed(() => {
  const items = integrations.value
  const q = search.value.trim().toLowerCase()
  if (!q) return items
  return items.filter((item) =>
    projectName(item).toLowerCase().includes(q) ||
    platformLabel(item.platform).toLowerCase().includes(q) ||
    String(item.account_name || item.account_id || '').toLowerCase().includes(q)
  )
})

const groupedIntegrations = computed(() => {
  const map = new Map()
  filteredIntegrations.value.forEach((item) => {
    const projectId = item.client_id || 'unknown'
    if (!map.has(projectId)) {
      map.set(projectId, {
        projectId,
        projectName: projectName(item),
        items: [],
      })
    }
    map.get(projectId).items.push(item)
  })
  return Array.from(map.values()).sort((a, b) => a.projectName.localeCompare(b.projectName, 'ru'))
})

function normalizeIntegrations(data) {
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.results)) return data.results
  if (Array.isArray(data?.items)) return data.items
  return []
}

function normalizePlatform(platform) {
  const key = String(platform || '').toUpperCase()
  return ({ YANDEX: 'YANDEX_DIRECT', VK: 'VK_ADS', MYTARGET: 'MYTARGET' }[key]) || key
}

function projectName(item) {
  return item.client_name || item.client?.name || 'Без проекта'
}

function platformLabel(platform) {
  const item = platformCatalog.find((p) => p.id === normalizePlatform(platform))
  return item?.name || platform || 'Интеграция'
}

function platformIcon(platform) {
  const item = platformCatalog.find((p) => p.id === normalizePlatform(platform))
  return item?.icon || '/admirra/img/icons/yandex-direct.png'
}

function statusLabel(item) {
  const status = String(item.sync_status || '').toUpperCase()
  if (status === 'SUCCESS') return 'Активно'
  if (status === 'FAILED') return 'Ошибка'
  if (status === 'PENDING') return 'Синхронизируется'
  if (status === 'NEVER') return 'Не синхронизировано'
  return 'Активно'
}

function statusClass(item) {
  const status = String(item.sync_status || '').toUpperCase()
  return {
    'status-pill--success': status === 'SUCCESS',
    'status-pill--danger': status === 'FAILED',
    'status-pill--warning': status === 'PENDING' || status === 'NEVER',
  }
}

function goalDriftLabel(item) {
  const missing = Number(item.missing_goals_count || 0)
  const fresh = Number(item.new_goals_count || 0)
  if (missing > 0) return `${missing} ${plural(missing, ['цель не приходит', 'цели не приходят', 'целей не приходит'])}`
  if (fresh > 0) return `${fresh} ${plural(fresh, ['новая цель', 'новые цели', 'новых целей'])}`
  return ''
}

function formatDate(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleString('ru-RU', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'Europe/Moscow',
  }) + ' МСК'
}

function nextSyncLabel(item) {
  if (!item.auto_sync) return 'выключена'
  const value = item.next_sync_at || (item.last_sync_at ? new Date(new Date(item.last_sync_at).getTime() + Number(item.sync_interval || 1440) * 60000) : null)
  if (!value) return 'сегодня ~04:00 МСК'
  return formatDate(value)
}

async function syncNow(item) {
  if (syncingIds.value.has(item.id)) return
  syncingIds.value = new Set([...syncingIds.value, item.id])
  try {
    await api.post(`integrations/${item.id}/sync`, { days: 90 })
    toaster.success('Синхронизация запущена.')
    await fetchIntegrations()
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Не удалось запустить синхронизацию.')
  } finally {
    const next = new Set(syncingIds.value)
    next.delete(item.id)
    syncingIds.value = next
  }
}

function openWizard() {
  const query = currentProjectId.value ? { client_id: currentProjectId.value } : {}
  router.push({ path: '/integrations/wizard', query })
}

function openEdit(id) {
  router.push(`/integrations/${id}/edit`)
}

async function copyId(id) {
  try {
    await navigator.clipboard.writeText(String(id))
    toaster.success('ID скопирован.')
  } catch {
    toaster.warning('Не удалось скопировать ID.')
  }
}

function shortId(id) {
  return String(id || '').slice(0, 8)
}

function plural(n, forms) {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return forms[0]
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return forms[1]
  return forms[2]
}
</script>

<style scoped>
.integrations-page {
  position: relative;
  z-index: 2;
  display: flex;
  min-height: 100%;
  flex-direction: column;
  overflow: hidden;
  padding: 2.0833rem 1.7361rem;
}
.page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1.3889rem;
  margin-bottom: 1.7361rem;
  padding-top: 1.0417rem;
}
.page-head h3 {
  margin: 0;
  color: #171717;
  font-size: 2.0833rem;
  font-weight: 600;
  line-height: 1;
}
.page-head p {
  margin: 0.6944rem 0 0;
  color: rgba(105, 105, 105, 0.56);
  font-size: 1.0417rem;
  font-weight: 500;
}
.add-btn,
.configure-btn,
.sync-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5556rem;
  min-height: 3.1944rem;
  padding: 0.5556rem 1.3889rem;
  border: 0;
  border-radius: 1.0417rem;
  background: linear-gradient(270deg, #06b5d4 0.35%, #1f9de4 32.08%, #2563eb 96.51%);
  color: #fff;
  font-size: 0.9028rem;
  font-weight: 600;
  white-space: nowrap;
  cursor: pointer;
  transition: transform 0.3s, opacity 0.3s;
}
.add-btn:hover,
.configure-btn:hover,
.sync-btn:hover {
  transform: translateY(-1px);
}
.sync-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  transform: none;
}
.sync-btn,
.configure-btn {
  min-height: 2.7778rem;
  border-radius: 0.8333rem;
  font-size: 0.8333rem;
}
.sync-btn {
  background: #f5f7f9;
  color: #2563eb;
}
.icon-plus {
  position: relative;
  width: 1.1111rem;
  height: 1.1111rem;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.18);
}
.icon-plus span {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 0.5556rem;
  height: 1.5px;
  border-radius: 99rem;
  background: currentColor;
  transform: translate(-50%, -50%);
}
.icon-plus span:last-child {
  transform: translate(-50%, -50%) rotate(90deg);
}
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.0417rem;
  margin-bottom: 1.7361rem;
}
.search-wrap {
  position: relative;
  width: min(100%, 30rem);
}
.search-input {
  width: 100%;
  height: 3.1944rem;
  padding: 0 3.125rem 0 1.25rem;
  border: 0;
  border-radius: 1.0417rem;
  background: #fff;
  color: #2c2c2c;
  font-size: 0.9028rem;
  outline: none;
}
.search-icon {
  position: absolute;
  right: 0.6944rem;
  top: 50%;
  display: flex;
  width: 1.8056rem;
  height: 1.8056rem;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #f5f7f9;
  transform: translateY(-50%);
}
.sync-note {
  color: rgba(105, 105, 105, 0.52);
  font-size: 0.9028rem;
  font-weight: 500;
}
.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 14rem;
  color: rgba(105, 105, 105, 0.56);
  font-size: 0.9028rem;
}
.project-groups {
  display: grid;
  gap: 1.3889rem;
}
.project-group {
  display: grid;
  gap: 0.8333rem;
}
.project-group__head {
  display: flex;
  align-items: center;
  gap: 0.8333rem;
}
.project-avatar {
  display: flex;
  width: 2.7778rem;
  height: 2.7778rem;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #eef4ff;
  color: #2563eb;
  font-size: 0.8333rem;
  font-weight: 700;
}
.project-group__head h4 {
  margin: 0;
  color: #171717;
  font-size: 1.1111rem;
  font-weight: 700;
}
.project-group__head p {
  margin: 0.2778rem 0 0;
  color: rgba(105, 105, 105, 0.56);
  font-size: 0.8333rem;
  font-weight: 500;
}
.integration-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(42rem, 1fr));
  gap: 1.0417rem;
}
.int-card {
  position: relative;
  display: grid;
  grid-template-columns: minmax(14rem, 1.2fr) minmax(11rem, 0.8fr) minmax(14rem, 1fr) auto auto;
  align-items: center;
  gap: 1.0417rem;
  min-height: 8.3333rem;
  padding: 1.3889rem;
  border-radius: 1.25rem;
  background: #fff;
}
.int-card__main {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: 0.8333rem;
}
.channel-icon {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 50%;
  object-fit: contain;
}
.int-card__title {
  min-width: 0;
}
.int-card__title h5 {
  margin: 0;
  color: #171717;
  font-size: 1.0417rem;
  font-weight: 700;
}
.int-card__title p {
  margin: 0.3472rem 0 0;
  overflow: hidden;
  color: rgba(105, 105, 105, 0.56);
  font-size: 0.8333rem;
  font-weight: 500;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.status-stack {
  display: grid;
  gap: 0.4167rem;
}
.status-stack small {
  color: rgba(105, 105, 105, 0.44);
  font-size: 0.7639rem;
  font-weight: 500;
}
.status-pill {
  display: inline-flex;
  width: max-content;
  align-items: center;
  gap: 0.4167rem;
  min-height: 1.8056rem;
  padding: 0 0.6944rem;
  border-radius: 99rem;
  background: #f5f7f9;
  color: #696969;
  font-size: 0.7639rem;
  font-weight: 700;
}
.status-pill span {
  width: 0.4167rem;
  height: 0.4167rem;
  border-radius: 50%;
  background: currentColor;
}
.status-pill--success {
  background: #e9fbf0;
  color: #13a548;
}
.status-pill--danger {
  background: #fff1f1;
  color: #ef4444;
}
.status-pill--warning {
  background: #fff7dd;
  color: #b45309;
}
.goal-drift-chip {
  width: max-content;
  max-width: 14rem;
  min-height: 1.8056rem;
  padding: 0 0.6944rem;
  border: 0;
  border-radius: 99rem;
  background: rgba(37, 99, 235, 0.08);
  color: #2563eb;
  font-size: 0.7639rem;
  font-weight: 700;
  cursor: pointer;
  text-align: left;
}
.goal-drift-chip:hover {
  background: rgba(37, 99, 235, 0.14);
}
.sync-times {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.6944rem;
}
.sync-times div {
  min-height: 3.1944rem;
  padding: 0.5556rem 0.6944rem;
  border-radius: 0.8333rem;
  background: #f8fafc;
}
.sync-times span {
  display: block;
  color: rgba(105, 105, 105, 0.48);
  font-size: 0.6944rem;
  font-weight: 700;
  text-transform: uppercase;
}
.sync-times strong {
  display: block;
  margin-top: 0.2778rem;
  color: #2c2c2c;
  font-size: 0.8333rem;
  font-weight: 600;
}
.id-chip {
  position: absolute;
  right: 1.3889rem;
  bottom: 0.8333rem;
  display: inline-flex;
  align-items: center;
  gap: 0.3472rem;
  border: 0;
  background: transparent;
  color: rgba(105, 105, 105, 0.42);
  font-size: 0.6944rem;
  font-weight: 600;
  cursor: pointer;
}
.spinning {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
@media (max-width: 1180px) {
  .int-card {
    grid-template-columns: 1fr;
    align-items: stretch;
  }
  .sync-times {
    grid-template-columns: 1fr;
  }
  .toolbar,
  .page-head {
    flex-direction: column;
  }
  .integration-list {
    grid-template-columns: 1fr;
  }
}
</style>
