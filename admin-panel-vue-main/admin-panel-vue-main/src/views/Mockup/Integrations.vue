<template>
  <div class="relative z-[2] flex min-h-full flex-col overflow-hidden px-[1.7361rem] py-[2.0833rem]">

    <!-- Platform quick-add buttons -->
    <div class="flex flex-wrap gap-[0.6944rem] mb-[2.0833rem]">
      <button
        v-for="p in platforms"
        :key="p.id"
        class="platform-btn"
        @click="$router.push('/integrations/wizard?platform=' + p.id)"
      >
        <div class="platform-btn__icon">
          <img :src="p.icon" :alt="p.name" />
        </div>
        <span class="platform-btn__label" :style="{ color: p.color }">{{ p.name }}</span>
        <span class="platform-btn__plus" aria-hidden="true">
          <span></span>
          <span></span>
        </span>
      </button>
    </div>

    <!-- Heading -->
    <div class="pt-[1.0417rem] pb-[1.0417rem] mb-[0.6944rem]">
      <h3 class="text-[2.0833rem] font-semibold leading-none text-[#171717] dark:text-white">Активные интеграции</h3>
    </div>

    <!-- Toolbar -->
    <div class="flex flex-wrap items-center gap-[0.6944rem] mb-[2.0833rem]">
      <button class="add-btn" @click="$router.push('/integrations/wizard')">
        <span>Добавить подключение</span>
        <span class="icon-plus" aria-hidden="true">
          <span></span>
          <span></span>
        </span>
      </button>
      <div class="search-wrap">
        <input
          v-model="search"
          class="search-input dark:!bg-[#2C2F3D] dark:!text-white/90 dark:!shadow-[inset_0_0_0_1px_rgba(255,255,255,0.1)] dark:placeholder:!text-white/45"
          type="text"
          placeholder="Поиск интеграций"
        />
        <div class="search-icon dark:!bg-white/10">
          <svg width="7" height="7" viewBox="0 0 16 16" fill="none">
            <circle cx="7" cy="7" r="5.5" stroke="#696969" stroke-width="1.5"/>
            <path d="M11 11L14 14" stroke="#696969" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
        </div>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="flex items-center justify-center py-[4.1667rem] text-[0.9028rem] text-[rgba(105,105,105,0.56)] dark:text-white/55">
      Загрузка…
    </div>

    <!-- Empty -->
    <div v-else-if="filteredIntegrations.length === 0" class="flex items-center justify-center py-[4.1667rem] text-[0.9028rem] text-[rgba(105,105,105,0.56)] dark:text-white/55">
      {{ search ? 'Ничего не найдено' : 'Нет активных интеграций. Добавьте первое подключение.' }}
    </div>

    <!-- Cards grid -->
    <div v-else class="grid grid-cols-1 xl:grid-cols-2 gap-[1.0417rem]">
      <div
        v-for="item in filteredIntegrations"
        :key="item.id"
        :data-int-id="item.id"
        class="int-card"
      >
        <!-- Card header -->
        <div class="int-card__header">
          <div class="flex items-center gap-[0.8333rem] min-w-0 flex-1">
            <div class="proj-avatar flex-shrink-0">
              <span>{{ projectInitials(projectName(item)) }}</span>
            </div>
            <div class="min-w-0">
              <div class="text-[0.7639rem] text-[rgba(105,105,105,0.72)] font-medium leading-none mb-[0.2778rem]">Проект</div>
              <div class="text-[1.0417rem] font-semibold text-[#171717] leading-tight truncate dark:text-white">{{ projectName(item) }}</div>
              <div v-if="projectDisplayId(item)" class="project-public-id">ID проекта {{ projectDisplayId(item) }}</div>
            </div>
          </div>
          <div class="channel-badge flex-shrink-0">{{ channelCount(item) }} {{ getPlural(channelCount(item), ['канал', 'канала', 'каналов']) }}</div>
        </div>

        <!-- Card body -->
        <div class="int-card__body">
          <div class="integration-body-row flex items-start justify-between gap-[1.25rem]">
            <div class="flex items-start gap-[0.9722rem] min-w-0 flex-1">
              <div class="platform-avatar flex-shrink-0">
                <img
                  :src="platformIcon(item.platform)"
                  :alt="item.platform"
                  class="w-full h-full object-contain"
                />
              </div>

              <div class="min-w-0 flex-1">
                <div class="flex flex-wrap items-center gap-[0.625rem] mb-[0.8333rem]">
                  <div class="integration-title">{{ platformLabel(item.platform) }}</div>
                  <span class="status-badge" :class="syncBadgeClass(item.sync_status)" :title="item.error_message || ''">
                    {{ syncLabel(item.sync_status) }}
                  </span>
                  <span
                    v-if="isAvitoIntegration(item)"
                    class="metrika-source-badge"
                    title="Лиды и цели Avito берутся из выбранного счётчика Яндекс Метрики"
                  >
                    <img src="/admirra/img/integrations/yandex-metrika.png" alt="" />
                    Метрика
                  </span>
                </div>

                <div class="sync-meta-grid">
                  <div>
                    <div class="sync-meta-label">Последняя синхронизация</div>
                    <div class="sync-meta-value">
                      {{ formatSyncDate(item.last_sync_at) }}
                      <span v-if="item.last_sync_trigger === 'auto'" class="sync-auto-badge" title="Выполнена ночным автосинхроном">авто</span>
                    </div>
                  </div>
                  <div>
                    <div class="sync-meta-label">Следующая</div>
                    <div class="sync-meta-value">{{ formatNextSync(item) }}</div>
                  </div>
                </div>

                <div class="auto-sync-line">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="M12 6v6l4 2m6-2a10 10 0 1 1-20 0 10 10 0 0 1 20 0Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                  <span>{{ formatAutoSyncText(item) }}</span>
                </div>

                <div class="integration-id-row">
                  <span>{{ integrationIdLabel(item) }}: {{ integrationDisplayId(item) }}</span>
                  <button
                    type="button"
                    class="copy-id-btn"
                    :title="`Скопировать ${integrationIdLabel(item).toLowerCase()}`"
                    @click="copyIntegrationId(integrationDisplayId(item), integrationIdLabel(item))"
                  >
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                      <path d="M8 8h10a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V10a2 2 0 0 1 2-2Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
                      <path d="M16 8V4a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                    </svg>
                  </button>
                </div>
              </div>
            </div>

            <div class="integration-actions flex flex-col items-stretch gap-[0.625rem] flex-shrink-0">
              <button class="sync-now-btn" :disabled="syncingId === item.id || isSyncingIntegration(item.id)" @click="syncNow(item)">
                <svg :class="{ 'animate-spin': syncingId === item.id || isSyncingIntegration(item.id) }" width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M4 4v5h5M20 20v-5h-5M6.5 17.5a8 8 0 0 0 12-2.5M17.5 6.5a8 8 0 0 0-12 2.5" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                <span>{{ syncingId === item.id || isSyncingIntegration(item.id) ? 'Синхронизация…' : 'Синхронизировать сейчас' }}</span>
              </button>
              <button class="configure-btn" :class="{ 'configure-btn--active': isPanelOpenFor(item) }" @click="toggleSettings(item)">{{ isPanelOpenFor(item) ? 'Свернуть' : 'Настроить' }}</button>
            </div>
          </div>
        </div>
      </div>
      <!-- Panel inside grid, positioned below the clicked card, card width -->
      <div
        v-if="settingsOpen && selectedIntegration"
        :style="panelWrapperStyle"
      >
        <div :style="{ gridColumn: String(panelColumn) }">
          <IntegrationSettingsPanel
            :integration="selectedIntegration"
            @close="closeSettings"
            @save="saveIntegrationSettings"
            @delete="deleteIntegration"
          />
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import api from '../../api/axios'
import { useProjects } from '../../composables/useProjects'
import { useToaster } from '../../composables/useToaster'
import { useSyncStatus } from '../../composables/useSyncStatus'
import IntegrationSettingsPanel from './IntegrationSettingsPanel.vue'

const { currentProjectId } = useProjects()
const toaster = useToaster()
const {
  fetchSyncStatus,
  startIntegrationSync,
  waitForSyncJobs,
  isSyncingIntegration,
} = useSyncStatus()

const integrations = ref([])
const isLoading    = ref(false)
const search       = ref('')
const settingsOpen = ref(false)
const selectedIntegration = ref(null)
const selectedIndex = ref(-1)
const syncingId = ref(null)

const panelWrapperStyle = ref({})
const panelColumn = ref(1)

const isPanelOpenFor = (item) => settingsOpen.value && selectedIntegration.value?.id === item.id

const openSettings = async (item) => {
  selectedIntegration.value = item
  const idx = filteredIntegrations.value.indexOf(item)
  selectedIndex.value = idx
  const cols = window.innerWidth >= 1280 ? 2 : 1
  // Панель занимает свою строку под кликнутой карточкой, но шириной в одну карточку
  // (в той же колонке, что и карточка) — для этого вкладываем сетку внутрь.
  panelColumn.value = (idx % cols) + 1
  panelWrapperStyle.value = {
    gridColumn: '1 / -1',
    gridRow: String(Math.floor(idx / cols) + 2),
    display: 'grid',
    gridTemplateColumns: cols === 2 ? 'repeat(2, minmax(0, 1fr))' : '1fr',
    gap: '1.0417rem',
  }
  settingsOpen.value = true
  await nextTick()
  const cardEl = document.querySelector(`[data-int-id="${item.id}"]`)
  if (cardEl) cardEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
}

const closeSettings = () => {
  settingsOpen.value = false
  selectedIntegration.value = null
}

const toggleSettings = (item) => {
  if (isPanelOpenFor(item)) closeSettings()
  else openSettings(item)
}

// ── Platform definitions ──
const platformCatalog = [
  { id: 'YANDEX_DIRECT', name: 'Yandex Direct', icon: '/admirra/img/icons/yandex-direct.png', color: '#71663e' },
  { id: 'VK_ADS',        name: 'ВК Ads',         icon: '/admirra/img/icons/vk-ads.png',        color: '#254b78' },
  { id: 'AVITO_ADS',     name: 'Avito',           icon: '/admirra/img/icons/avito.svg',          color: '#579f75' },
  { id: 'GOOGLE_ADS',    name: 'Google Ads',      icon: '/admirra/img/icons/google-ads.png',     color: '#5e82bc' },
  { id: 'TELEGRAM',      name: 'Telegram',        icon: '/admirra/img/icons/telegram.png',        color: '#4d7c92' },
  { id: 'GOOGLE_SHEETS', name: 'Google Sheets',   icon: '/admirra/img/icons/google-sheets.png',  color: '#46725d' },
]
const visiblePlatformIds = new Set(['YANDEX_DIRECT', 'VK_ADS', 'AVITO_ADS'])
const platforms = platformCatalog.filter((platform) => visiblePlatformIds.has(platform.id))
const hiddenIntegrationPlatformIds = new Set(['YANDEX_METRIKA'])

// ── API ──
const fetchIntegrations = async () => {
  isLoading.value = true
  try {
    const params = {}
    if (currentProjectId.value) params.client_id = currentProjectId.value
    const { data } = await api.get('integrations/', { params })
    integrations.value = normalizeIntegrations(data)
    await fetchSyncStatus()
  } catch (err) {
    console.error('Failed to load integrations:', err)
    integrations.value = []
  } finally {
    isLoading.value = false
  }
}

onMounted(fetchIntegrations)

// Смена проекта в хедере — перезагружаем список без перезагрузки страницы
watch(currentProjectId, () => {
  closeSettings()
  search.value = ''
  fetchIntegrations()
})

const filteredIntegrations = computed(() => {
  if (!search.value.trim()) return integrations.value
  const q = search.value.toLowerCase()
  return integrations.value.filter(i =>
    i.client_name?.toLowerCase().includes(q) ||
    i.client?.name?.toLowerCase().includes(q) ||
    i.platform?.toLowerCase().includes(q)
  )
})

const normalizeIntegrations = (data) => {
  const list = Array.isArray(data)
    ? data
    : Array.isArray(data?.results)
      ? data.results
      : Array.isArray(data?.items)
        ? data.items
        : []

  return list.filter((item) => !hiddenIntegrationPlatformIds.has(normalizePlatform(item?.platform)))
}

const normalizePlatform = (platform) => {
  const key = platform?.toUpperCase()
  return ({
    YANDEX: 'YANDEX_DIRECT',
    VK: 'VK_ADS',
    AVITO: 'AVITO_ADS',
    MYTARGET: 'MYTARGET',
  }[key]) || key
}

const projectName = (integration) => integration.client_name || integration.client?.name || '—'

const projectDisplayId = (integration) =>
  integration?.client_display_id || integration?.client?.display_id || null

const integrationDisplayId = (integration) =>
  integration?.account_id || integration?.external_account_id || integration?.id || '—'

const integrationIdLabel = (integration) =>
  integration?.account_id || integration?.external_account_id ? 'ID кабинета' : 'ID интеграции'

const channelCount = (integration) => {
  if (typeof integration.channels === 'number') return integration.channels
  if (Array.isArray(integration.channels)) return integration.channels.length
  return 1
}

const getPlural = (n, forms) => {
  n = Math.abs(Number(n) || 0) % 100
  const n1 = n % 10
  if (n > 10 && n < 20) return forms[2]
  if (n1 > 1 && n1 < 5) return forms[1]
  if (n1 === 1) return forms[0]
  return forms[2]
}

const projectInitials = (name = '') => {
  const parts = String(name || '').trim().split(/\s+/).filter(Boolean)
  if (!parts.length) return '—'
  return parts.slice(0, 2).map((part) => part[0]).join('').toUpperCase()
}

const platformLabel = (platform) => {
  const p = platformCatalog.find(x => x.id === normalizePlatform(platform))
  if (normalizePlatform(platform) === 'MYTARGET') return 'MyTarget'
  return p?.name || platform || '—'
}

const platformIcon = (platform) => {
  const p = platformCatalog.find(x => x.id === normalizePlatform(platform))
  if (normalizePlatform(platform) === 'MYTARGET') return '/admirra/img/icons/target.png'
  return p?.icon || '/admirra/img/icons/yandex-direct.png'
}

const isAvitoIntegration = (integration) =>
  normalizePlatform(integration?.platform) === 'AVITO_ADS'

const syncClass = (status) => ({
  'sync-dot--success': status === 'SUCCESS',
  'sync-dot--danger':  status === 'FAILED',
  'sync-dot--warning': status === 'PENDING',
})

const syncLabel = (status) => ({
  SUCCESS: 'Активно',
  FAILED:  'Ошибка',
  PENDING: 'В процессе',
  NEVER:   'Не синхронизировано',
}[status] || status || 'Неизвестно')

const syncBadgeClass = (status) => ({
  'status-badge--success': status === 'SUCCESS',
  'status-badge--danger': status === 'FAILED',
  'status-badge--warning': status === 'PENDING',
  'status-badge--muted': !status || status === 'NEVER',
})

const formatSyncDate = (dateStr) => {
  if (!dateStr) return 'ещё не было'
  const date = new Date(dateStr)
  if (Number.isNaN(date.getTime())) return '—'
  const day = date.toLocaleDateString('ru-RU', { day: '2-digit', month: 'short', timeZone: 'Europe/Moscow' }).replace('.', '')
  const time = date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Moscow' })
  return `${day}, ${time} МСК`
}

// Автосинхронизация — фиксированный ночной cron (см. AUTO_SYNC_HOUR_MSK в automation/main.py).
// Следующий синк не зависит от ручных запусков — это всегда ближайшее 03:00 МСК.
const AUTO_SYNC_HOUR_MSK = 3
const MSK_OFFSET_MS = 3 * 60 * 60 * 1000 // Москва стабильно UTC+3, без перехода на летнее время

const formatNextSync = (item) => {
  if (!item.auto_sync) return 'авто выключено'

  const now = new Date()
  // «Стенные» часы МСК = UTC + 3ч; берём дату в этой системе
  const mskNow = new Date(now.getTime() + MSK_OFFSET_MS)
  const y = mskNow.getUTCFullYear()
  const m = mskNow.getUTCMonth()
  const d = mskNow.getUTCDate()
  // 03:00 МСК сегодня как реальный UTC-момент
  let targetUtc = Date.UTC(y, m, d, AUTO_SYNC_HOUR_MSK, 0, 0) - MSK_OFFSET_MS
  if (targetUtc <= now.getTime()) {
    // окно сегодня уже прошло — берём завтра
    targetUtc = Date.UTC(y, m, d + 1, AUTO_SYNC_HOUR_MSK, 0, 0) - MSK_OFFSET_MS
  }
  const nextSync = new Date(targetUtc)
  const time = nextSync.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Moscow' })

  const todayMskDay = mskNow.getUTCDate()
  const nextMskDay = new Date(nextSync.getTime() + MSK_OFFSET_MS).getUTCDate()
  if (nextMskDay === todayMskDay) return `сегодня, ${time} МСК`
  return `завтра, ${time} МСК`
}

const formatAutoSyncText = (item) => {
  if (!item.auto_sync) return 'Автоматическая синхронизация выключена'
  const interval = Number(item.sync_interval || 1440)
  if (interval === 1440) return 'Обновляется автоматически раз в сутки'
  if (interval < 60) return `Обновляется автоматически раз в ${interval} ${getPlural(interval, ['минуту', 'минуты', 'минут'])}`
  const hours = Math.round(interval / 60)
  return `Обновляется автоматически раз в ${hours} ${getPlural(hours, ['час', 'часа', 'часов'])}`
}

const copyIntegrationId = async (id, label = 'ID интеграции') => {
  try {
    await navigator.clipboard.writeText(String(id || ''))
    toaster.success(`${label} скопирован`)
  } catch {
    toaster.error('Не удалось скопировать ID')
  }
}

const syncNow = async (item) => {
  if (syncingId.value || isSyncingIntegration(item.id)) return
  syncingId.value = item.id
  try {
    const data = await startIntegrationSync(item.id, { days: 90, forceFull: false })
    const jobId = data?.job_id
    toaster.info('Синхронизация запущена. Данные обновятся автоматически.')
    await fetchIntegrations()
    if (jobId) {
      const result = await waitForSyncJobs([jobId])
      await fetchIntegrations()
      if (result.failed?.length) {
        toaster.warning('Синхронизация завершена с ошибкой. Проверьте статус интеграции.')
      } else {
        toaster.success('Синхронизация завершена. Данные обновлены.')
      }
    }
  } catch (err) {
    toaster.error('Ошибка при синхронизации: ' + (err.response?.data?.detail || err.message))
  } finally {
    syncingId.value = null
  }
}

const saveIntegrationSettings = async (payload = {}) => {
  if (!selectedIntegration.value?.id) return
  try {
    const { data } = await api.patch(`integrations/${selectedIntegration.value.id}`, payload)
    selectedIntegration.value = data
    await fetchIntegrations()
    settingsOpen.value = false
    toaster.success('Настройки интеграции сохранены.')
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Не удалось сохранить настройки интеграции.')
  }
}

const deleteIntegration = async () => {
  if (!selectedIntegration.value?.id) return
  try {
    await api.delete(`integrations/${selectedIntegration.value.id}`)
    settingsOpen.value = false
    selectedIntegration.value = null
    await fetchIntegrations()
    toaster.success('Интеграция удалена.')
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Не удалось удалить интеграцию.')
  }
}
</script>

<style scoped>
/* ── Platform buttons ── */
.platform-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5556rem;
  min-height: 2.7778rem;
  padding: 0.4167rem 0.9028rem 0.4167rem 0.5556rem;
  border-radius: 2.7778rem;
  background-color: #fff;
  border: none;
  cursor: pointer;
  transition: background-color 0.5s, transform 0.75s;
  white-space: nowrap;
}
.platform-btn:hover  { background-color: #2563eb; transform: scale(1.03); }
.platform-btn:hover .platform-btn__label { color: #fff !important; }
.platform-btn:active { transform: scale(0.97); transition: transform 0s; }
:global(.dark) .platform-btn,
:global(.darkmode) .platform-btn {
  background-color: #2C2F3D;
  box-shadow: inset 0 0 0 1px rgba(255,255,255,0.08);
}
:global(.dark) .platform-btn__label,
:global(.darkmode) .platform-btn__label {
  color: rgba(255,255,255,0.78) !important;
}
:global(.dark) .platform-btn:hover,
:global(.darkmode) .platform-btn:hover {
  background-color: #2563eb;
}

.platform-btn__icon {
  width: 0.9722rem;
  height: 0.9722rem;
  border-radius: 50%;
  overflow: hidden;
  background: #eee;
  flex-shrink: 0;
}
.platform-btn__icon img { width: 100%; height: 100%; object-fit: cover; }

.platform-btn__label {
  font-size: 0.9028rem;
  font-weight: 400;
}

.platform-btn__plus {
  position: relative;
  display: inline-flex;
  width: 1.0417rem;
  height: 1.0417rem;
  border-radius: 50%;
  background-color: rgba(0,0,0,0.12);
  flex-shrink: 0;
  margin-left: 0.2778rem;
}
.platform-btn__plus span {
  position: absolute;
  left: 50%;
  top: 50%;
  border-radius: 69.375rem;
  background: rgba(0,0,0,0.45);
  transform: translate(-50%, -50%);
}
.platform-btn__plus span:first-child {
  width: 0.3819rem;
  height: 1px;
}
.platform-btn__plus span:last-child {
  width: 1px;
  height: 0.3819rem;
}
:global(.dark) .platform-btn__plus,
:global(.darkmode) .platform-btn__plus {
  background-color: rgba(255,255,255,0.16);
}
:global(.dark) .platform-btn__plus span,
:global(.darkmode) .platform-btn__plus span {
  background: rgba(255,255,255,0.7);
}

/* ── Add button (стиль как bulk-btn в ProjectCard) ── */
.add-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.6944rem;
  min-height: 3.1944rem;
  padding: 0.5556rem 1.1806rem;
  border-radius: 1.0417rem;
  background: linear-gradient(270deg, #06b5d4 0.35%, #1f9de4 32.08%, #2563eb 96.51%);
  color: #fff;
  font-size: 0.9028rem;
  font-weight: 500;
  border: none;
  cursor: pointer;
  white-space: nowrap;
  transition: transform 0.75s;
}
.add-btn:hover  { transform: scale(1.02); }
.add-btn:active { transform: scale(0.97); transition: transform 0s; }

.icon-plus {
  position: relative;
  display: inline-flex;
  width: 1.5278rem;
  height: 1.5278rem;
  border-radius: 0.4167rem;
  background: rgba(255,255,255,0.2);
  flex-shrink: 0;
}
.icon-plus span {
  position: absolute;
  left: 50%;
  top: 50%;
  border-radius: 69.375rem;
  background: #fff;
  transform: translate(-50%, -50%);
}
.icon-plus span:first-child {
  width: 0.4861rem;
  height: 1px;
}
.icon-plus span:last-child {
  width: 1px;
  height: 0.4861rem;
}

/* ── Search (стиль как в ProjectCard) ── */
.search-wrap {
  position: relative;
  max-width: 100%;
}
.search-input {
  width: min(24.5833rem, 100%);
  height: 3.1944rem;
  padding: 0 3.125rem 0 1.1806rem;
  font-size: 0.9028rem;
  color: #2c2c2c;
  background-color: #fff;
  border: none;
  border-radius: 0.8333rem;
  outline: none;
  box-shadow: inset 0 0 0 1px rgba(0,0,0,0.08);
  transition: box-shadow 0.5s;
}
.search-input:focus { box-shadow: inset 0 0 0 1px rgba(37,99,235,0.24), 0 0 0.6944rem rgba(37,99,235,0.15); }
.search-input::placeholder { color: rgba(0,0,0,0.3); }
:global(.dark) .search-input,
:global(.darkmode) .search-input {
  background-color: #2C2F3D;
  color: rgba(255,255,255,0.86);
  box-shadow: inset 0 0 0 1px rgba(255,255,255,0.10);
}
:global(.dark) .search-input::placeholder,
:global(.darkmode) .search-input::placeholder {
  color: rgba(255,255,255,0.42);
}
.search-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.1111rem;
  height: 1.1111rem;
  background-color: #f5f7f9;
  border-radius: 50%;
  position: absolute;
  right: 1.1806rem;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
}
:global(.dark) .search-icon,
:global(.darkmode) .search-icon {
  background-color: rgba(255,255,255,0.08);
}

/* ── Integration card ── */
.int-card {
  display: flex;
  flex-direction: column;
  gap: 1.0417rem;
  padding: 1.3889rem;
  background: #fff;
  border: 1px solid rgba(15, 23, 42, 0.06);
  border-radius: 1.25rem;
  box-shadow: 0 0.1389rem 0.4167rem rgba(15, 23, 42, 0.03);
}
:global(.dark) .int-card,
:global(.darkmode) .int-card {
  background-color: #2C2F3D;
  border: 1px solid rgba(255,255,255,0.08);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.28), inset 0 1px 0 rgba(255, 255, 255, 0.07);
}
:global(.dark) .int-card .text-\[\#696969\],
:global(.darkmode) .int-card .text-\[\#696969\] {
  color: rgba(255,255,255,0.82) !important;
}
:global(.dark) .int-card .text-\[rgba\(105\,105\,105\,0\.56\)\],
:global(.darkmode) .int-card .text-\[rgba\(105\,105\,105\,0\.56\)\],
:global(.dark) .int-card .text-\[rgba\(44\,44\,44\,0\.4\)\],
:global(.darkmode) .int-card .text-\[rgba\(44\,44\,44\,0\.4\)\] {
  color: rgba(255,255,255,0.55) !important;
}

/* ── Card header ── */
.int-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.0417rem;
}

.integration-body-row {
  min-width: 0;
}

/* ── Project avatar ── */
.proj-avatar {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 50%;
  background: #f5f7f9;
  border: 1px solid rgba(15, 23, 42, 0.06);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0.3472rem 0.9722rem rgba(18, 24, 40, 0.04);
}
.proj-avatar span {
  font-size: 0.8333rem;
  font-weight: 700;
  color: #374151;
  line-height: 1;
}
:global(.dark) .proj-avatar,
:global(.darkmode) .proj-avatar {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.12);
}
:global(.dark) .proj-avatar span,
:global(.darkmode) .proj-avatar span {
  color: rgba(255, 255, 255, 0.82);
}
.project-public-id {
  margin-top: 0.3472rem;
  font-size: 0.7639rem;
  font-weight: 600;
  line-height: 1;
  color: rgba(105, 105, 105, 0.58);
}
:global(.dark) .project-public-id,
:global(.darkmode) .project-public-id {
  color: rgba(255, 255, 255, 0.45);
}

/* ── Channel badge (caption _light _md) ── */
.channel-badge {
  display: inline-block;
  padding: 0.4861rem 0.9028rem;
  border-radius: 0.7639rem;
  background-color: rgba(37, 99, 235, 0.06);
  border: 1px solid rgba(37,99,235,0.72);
  color: #2563eb;
  font-size: 0.7639rem;
  font-weight: 600;
  white-space: nowrap;
}

/* ── Card body ── */
.int-card__body {
  padding: 1.1806rem 1.3889rem;
  background-color: #f5f7f9;
  border-radius: 1.0417rem;
  border: 1px solid rgba(0, 0, 0, 0.05);
  box-shadow: 0 0.2083rem 0.8333rem rgba(18, 24, 40, 0.025);
}
:global(.dark) .int-card__body,
:global(.darkmode) .int-card__body {
  background-color: rgba(255,255,255,0.04);
  border-color: rgba(255,255,255,0.10);
}

.platform-avatar {
  width: 3.3333rem;
  height: 3.3333rem;
  border-radius: 50%;
  overflow: hidden;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0.2778rem 0.9722rem rgba(18, 24, 40, 0.05);
}

.integration-title {
  color: #171717;
  font-size: 1.0417rem;
  font-weight: 650;
  line-height: 1;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  min-height: 1.5278rem;
  padding: 0.2778rem 0.7639rem;
  border-radius: 999px;
  font-size: 0.7639rem;
  font-weight: 600;
}
.status-badge--success { background: #e8f2dc; color: #2f6b2b; }
.status-badge--danger { background: #fee2e2; color: #b91c1c; }
.status-badge--warning { background: #fff7ed; color: #c2410c; }
.status-badge--muted { background: #f1f3f5; color: #697386; }

.metrika-source-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.3472rem;
  min-height: 1.5278rem;
  padding: 0.2083rem 0.625rem 0.2083rem 0.3472rem;
  border-radius: 999px;
  background: #fff9e8;
  color: #80662d;
  border: 1px solid rgba(242, 190, 60, 0.35);
  font-size: 0.6944rem;
  font-weight: 700;
  line-height: 1;
  white-space: nowrap;
}
.metrika-source-badge img {
  width: 0.9028rem;
  height: 0.9028rem;
  object-fit: contain;
  border-radius: 50%;
}
:global(.dark) .metrika-source-badge,
:global(.darkmode) .metrika-source-badge {
  background: rgba(255, 249, 232, 0.08);
  color: #f1d28b;
  border-color: rgba(242, 190, 60, 0.24);
}

.sync-meta-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(8.3333rem, 1fr));
  gap: 1.1111rem;
  margin-bottom: 0.7639rem;
  max-width: 23.6111rem;
}
.sync-meta-label {
  color: #777973;
  font-size: 0.7639rem;
  font-weight: 600;
  margin-bottom: 0.2778rem;
}
.sync-meta-value {
  color: #171717;
  font-size: 0.9028rem;
  font-weight: 650;
  line-height: 1.25;
}
.sync-auto-badge {
  display: inline-block;
  margin-left: 0.3472rem;
  padding: 0.0694rem 0.3472rem;
  border-radius: 0.4167rem;
  background: rgba(37, 99, 235, 0.08);
  color: #2563eb;
  font-size: 0.6944rem;
  font-weight: 700;
  vertical-align: middle;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.auto-sync-line {
  display: inline-flex;
  align-items: center;
  gap: 0.4167rem;
  color: #777973;
  font-size: 0.8333rem;
  font-weight: 600;
  margin-bottom: 0.5556rem;
}

.integration-id-row {
  display: flex;
  align-items: center;
  gap: 0.4167rem;
  color: #777973;
  font-size: 0.7639rem;
  font-weight: 600;
  min-width: 0;
  overflow-wrap: anywhere;
}
.copy-id-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.25rem;
  height: 1.25rem;
  border: 0;
  border-radius: 0.4167rem;
  color: #777973;
  background: transparent;
  cursor: pointer;
  transition: background-color 0.2s, color 0.2s;
}
.copy-id-btn:hover {
  background: #f1f4f9;
  color: #2563eb;
}

.sync-now-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.4861rem;
  min-height: 2.7778rem;
  padding: 0.5556rem 1.1111rem;
  border-radius: 0.8333rem;
  background: #fff;
  border: 1px solid rgba(105,105,105,0.26);
  color: #171717;
  font-size: 0.9028rem;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: background-color 0.25s, border-color 0.25s, color 0.25s, transform 0.25s;
}
.sync-now-btn:hover {
  background-color: #f4f8ff;
  border-color: #2563eb;
  color: #2563eb;
}
.sync-now-btn:active { transform: scale(0.98); }
.sync-now-btn:disabled {
  cursor: not-allowed;
  opacity: 0.64;
  transform: none;
}

/* ── Configure button — скругление как было у badge, hover синий ── */
.configure-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 2.7778rem;
  padding: 0.5556rem 1.25rem;
  border-radius: 0.8333rem;
  background-color: #e9f2ff;
  border: 1px solid #60a5fa;
  color: #2f5f9f;
  font-size: 0.9028rem;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: background-color 0.5s, border-color 0.5s, color 0.5s, transform 0.75s;
}
.configure-btn:hover  { background-color: #dbeafe; border-color: #2563eb; color: #1d4ed8; transform: scale(1.02); }
.configure-btn:active { transform: scale(0.97); transition: transform 0s; }
.configure-btn--active { background-color: #2563eb; border-color: #2563eb; color: #fff; }
.configure-btn--active:hover { background-color: #1d4ed8; border-color: #1d4ed8; color: #fff; }
:global(.dark) .configure-btn,
:global(.darkmode) .configure-btn {
  background-color: rgba(255,255,255,0.06);
  border-color: rgba(255,255,255,0.12);
  color: rgba(255,255,255,0.75);
}

@media (max-width: 479.25px) {
  .platform-btn,
  .add-btn,
  .search-wrap,
  .search-input {
    width: 100%;
  }

  .int-card {
    padding: 1.3889rem;
    gap: 1.3889rem;
  }

  .int-card__header,
  .integration-body-row {
    align-items: stretch;
    flex-direction: column;
  }

  .integration-actions {
    flex-direction: row;
    flex-wrap: wrap;
    width: 100%;
  }

  .integration-actions > * {
    flex: 1 1 9.7222rem;
  }
}
</style>
