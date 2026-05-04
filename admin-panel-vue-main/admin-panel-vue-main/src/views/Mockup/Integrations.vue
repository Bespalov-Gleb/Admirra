<template>
  <div class="relative z-[2] flex min-h-full flex-col overflow-hidden px-[25px] py-[30px]">

    <!-- Platform quick-add buttons -->
    <div class="flex flex-wrap gap-[10px] mb-[30px]">
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
    <div class="pt-[15px] pb-[15px] mb-[10px]">
      <h3 class="text-[30px] font-semibold leading-none text-[#171717] dark:text-white">Активные интеграции</h3>
    </div>

    <!-- Toolbar -->
    <div class="flex flex-wrap items-center gap-[10px] mb-[30px]">
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
    <div v-if="isLoading" class="flex items-center justify-center py-[60px] text-[13px] text-[rgba(105,105,105,0.56)] dark:text-white/55">
      Загрузка…
    </div>

    <!-- Empty -->
    <div v-else-if="filteredIntegrations.length === 0" class="flex items-center justify-center py-[60px] text-[13px] text-[rgba(105,105,105,0.56)] dark:text-white/55">
      {{ search ? 'Ничего не найдено' : 'Нет активных интеграций. Добавьте первое подключение.' }}
    </div>

    <!-- Cards grid -->
    <div v-else class="grid grid-cols-1 xl:grid-cols-2 gap-[15px]">
      <div
        v-for="item in filteredIntegrations"
        :key="item.id"
        class="int-card"
      >
        <!-- Card header -->
        <div class="int-card__header">
          <div class="flex items-center gap-[12px] min-w-0 flex-1">
            <div class="proj-avatar flex-shrink-0">
              <span>{{ projectName(item).slice(0, 2).toUpperCase() }}</span>
            </div>
            <div class="min-w-0">
              <div class="text-[12px] text-[rgba(105,105,105,0.56)] font-medium leading-none mb-[5px]">Проект</div>
              <div class="text-[15px] font-medium text-[#696969] leading-none truncate">{{ projectName(item) }}</div>
            </div>
          </div>
          <div class="channel-badge flex-shrink-0">{{ channelCount(item) }}&nbsp;КАНАЛ</div>
        </div>

        <!-- Card body -->
        <div class="int-card__body">
          <div class="flex items-start gap-[15px]">
            <!-- Left: platform info + ID -->
            <div class="flex-1 min-w-0 flex flex-col gap-[16px]">
              <div class="flex items-center gap-[12px] min-w-0">
                <img
                  :src="platformIcon(item.platform)"
                  :alt="item.platform"
                  width="33"
                  height="33"
                  class="rounded-full flex-shrink-0 object-cover"
                />
                <div class="min-w-0">
                  <div class="text-[15px] text-[#696969] leading-none mb-[6px]">{{ platformLabel(item.platform) }}</div>
                  <div class="flex items-center flex-wrap gap-x-[6px] gap-y-[2px]">
                    <span class="sync-dot" :class="syncClass(item.sync_status)"></span>
                    <span class="text-[11px] text-[rgba(105,105,105,0.56)] uppercase tracking-wide font-medium">
                      {{ syncLabel(item.sync_status) }}
                    </span>
                    <template v-if="item.last_sync_at">
                      <span class="text-[10px] text-[rgba(105,105,105,0.4)]">|</span>
                      <time class="text-[11px] text-[rgba(44,44,44,0.4)]">Последняя: {{ formatDate(item.last_sync_at) }}</time>
                    </template>
                  </div>
                </div>
              </div>
              <div class="id-badge self-start">ID: {{ item.external_account_id || item.id }}</div>
            </div>
            <!-- Right column: 24ч + Настроить — правые края совпадают -->
            <div class="flex flex-col items-stretch gap-[12px] flex-shrink-0">
              <div class="sync-badge">
                <span class="font-medium">24 часа</span>
                <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
                  <path d="M2 8C2 11.31 4.69 14 8 14C11.31 14 14 11.31 14 8C14 4.69 11.31 2 8 2C5.8 2 3.85 3.1 2.75 4.75M2.75 4.75V2M2.75 4.75H5.25" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </div>
              <button class="configure-btn" @click="$router.push('/integrations/wizard')">Настроить</button>
            </div>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../../api/axios'
import { useProjects } from '../../composables/useProjects'

const { currentProjectId } = useProjects()

const integrations = ref([])
const isLoading    = ref(false)
const search       = ref('')

// ── Platform definitions ──
const platforms = [
  { id: 'YANDEX_DIRECT', name: 'Yandex Direct', icon: '/admirra/img/icons/yandex-direct.png', color: '#71663e' },
  { id: 'VK_ADS',        name: 'ВК Ads',         icon: '/admirra/img/icons/vk-ads.png',        color: '#254b78' },
  { id: 'AVITO',         name: 'Avito',           icon: '/admirra/img/icons/avito.png',          color: '#579f75' },
  { id: 'GOOGLE_ADS',    name: 'Google Ads',      icon: '/admirra/img/icons/google-ads.png',     color: '#5e82bc' },
  { id: 'TELEGRAM',      name: 'Telegram',        icon: '/admirra/img/icons/telegram.png',        color: '#4d7c92' },
  { id: 'GOOGLE_SHEETS', name: 'Google Sheets',   icon: '/admirra/img/icons/google-sheets.png',  color: '#46725d' },
]

// ── API ──
const fetchIntegrations = async () => {
  isLoading.value = true
  try {
    const params = {}
    if (currentProjectId.value) params.client_id = currentProjectId.value
    const { data } = await api.get('integrations/', { params })
    integrations.value = normalizeIntegrations(data)
  } catch (err) {
    console.error('Failed to load integrations:', err)
    integrations.value = []
  } finally {
    isLoading.value = false
  }
}

onMounted(fetchIntegrations)

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
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.results)) return data.results
  if (Array.isArray(data?.items)) return data.items
  return []
}

const normalizePlatform = (platform) => {
  const key = platform?.toUpperCase()
  return ({
    YANDEX: 'YANDEX_DIRECT',
    VK: 'VK_ADS',
    MYTARGET: 'MYTARGET',
  }[key]) || key
}

const projectName = (integration) => integration.client_name || integration.client?.name || '—'

const channelCount = (integration) => {
  if (typeof integration.channels === 'number') return integration.channels
  if (Array.isArray(integration.channels)) return integration.channels.length
  return 1
}

const platformLabel = (platform) => {
  const p = platforms.find(x => x.id === normalizePlatform(platform))
  if (normalizePlatform(platform) === 'MYTARGET') return 'MyTarget'
  return p?.name || platform || '—'
}

const platformIcon = (platform) => {
  const p = platforms.find(x => x.id === normalizePlatform(platform))
  if (normalizePlatform(platform) === 'MYTARGET') return '/admirra/img/icons/target.png'
  return p?.icon || '/admirra/img/icons/yandex-direct.png'
}

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

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleString('ru-RU', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: 'short' })
}
</script>

<style scoped>
/* ── Platform buttons ── */
.platform-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 40px;
  padding: 6px 13px 6px 8px;
  border-radius: 40px;
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
  width: 14px;
  height: 14px;
  border-radius: 50%;
  overflow: hidden;
  background: #eee;
  flex-shrink: 0;
}
.platform-btn__icon img { width: 100%; height: 100%; object-fit: cover; }

.platform-btn__label {
  font-size: 13px;
  font-weight: 400;
}

.platform-btn__plus {
  position: relative;
  display: inline-flex;
  width: 15px;
  height: 15px;
  border-radius: 50%;
  background-color: rgba(0,0,0,0.12);
  flex-shrink: 0;
  margin-left: 4px;
}
.platform-btn__plus span {
  position: absolute;
  left: 50%;
  top: 50%;
  border-radius: 999px;
  background: rgba(0,0,0,0.45);
  transform: translate(-50%, -50%);
}
.platform-btn__plus span:first-child {
  width: 5.5px;
  height: 1px;
}
.platform-btn__plus span:last-child {
  width: 1px;
  height: 5.5px;
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
  gap: 10px;
  min-height: 46px;
  padding: 8px 17px;
  border-radius: 15px;
  background: linear-gradient(270deg, #06b5d4 0.35%, #1f9de4 32.08%, #2563eb 96.51%);
  color: #fff;
  font-size: 13px;
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
  width: 22px;
  height: 22px;
  border-radius: 6px;
  background: rgba(255,255,255,0.2);
  flex-shrink: 0;
}
.icon-plus span {
  position: absolute;
  left: 50%;
  top: 50%;
  border-radius: 999px;
  background: #fff;
  transform: translate(-50%, -50%);
}
.icon-plus span:first-child {
  width: 7px;
  height: 1px;
}
.icon-plus span:last-child {
  width: 1px;
  height: 7px;
}

/* ── Search (стиль как в ProjectCard) ── */
.search-wrap { position: relative; }
.search-input {
  width: 354px;
  height: 46px;
  padding: 0 45px 0 17px;
  font-size: 13px;
  color: #2c2c2c;
  background-color: #fff;
  border: none;
  border-radius: 12px;
  outline: none;
  box-shadow: inset 0 0 0 1px rgba(0,0,0,0.08);
  transition: box-shadow 0.5s;
}
.search-input:focus { box-shadow: inset 0 0 0 1px rgba(37,99,235,0.24), 0 0 10px rgba(37,99,235,0.15); }
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
  width: 16px;
  height: 16px;
  background-color: #f5f7f9;
  border-radius: 50%;
  position: absolute;
  right: 17px;
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
  gap: 30px;
  padding: 30px;
  background-color: #fff;
  border-radius: 15px;
}
:global(.dark) .int-card,
:global(.darkmode) .int-card {
  background-color: #2C2F3D;
  border: 1px solid rgba(255,255,255,0.08);
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
  gap: 15px;
}

/* ── Project avatar ── */
.proj-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #e8eef9;
  display: flex;
  align-items: center;
  justify-content: center;
}
.proj-avatar span {
  font-size: 12px;
  font-weight: 700;
  color: #4b6fa0;
  line-height: 1;
}

/* ── Channel badge (caption _light _md) ── */
.channel-badge {
  display: inline-block;
  padding: 9px 17px;
  border-radius: 12px;
  background-color: rgba(0,110,255,0.03);
  border: 1px solid #adc7ff;
  color: #2563eb;
  font-size: 11px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  white-space: nowrap;
}

/* ── Card body ── */
.int-card__body {
  padding: 20px;
  background-color: #f9fcff;
  border-radius: 15px;
  border: 1px solid #e9e9e9;
}
:global(.dark) .int-card__body,
:global(.darkmode) .int-card__body {
  background-color: rgba(255,255,255,0.04);
  border-color: rgba(255,255,255,0.10);
}

/* ── Sync dot ── */
.sync-dot {
  flex-shrink: 0;
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: #2563eb;
}
.sync-dot--success { background-color: #5bff7c; }
.sync-dot--danger  { background-color: #ef4444; }
.sync-dot--warning { background-color: #f97316; }

/* ── Sync badge (badge-text _md) — скругление как было у Настроить ── */
.sync-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 9px 17px;
  border-radius: 18px;
  background: linear-gradient(270deg, #06b5d4 0.35%, #1f9de4 32.08%, #2563eb 96.51%);
  color: #fff;
  font-size: 13px;
  white-space: nowrap;
}

/* ── ID badge (caption) ── */
.id-badge {
  display: inline-block;
  padding: 8px 15px;
  background-color: #f9fcff;
  border: 1px solid #e9e9e9;
  border-radius: 8px;
  color: #c2c2c2;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
:global(.dark) .id-badge,
:global(.darkmode) .id-badge {
  background-color: rgba(255,255,255,0.05);
  border-color: rgba(255,255,255,0.10);
  color: rgba(255,255,255,0.45);
}

/* ── Configure button — скругление как было у badge, hover синий ── */
.configure-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 40px;
  padding: 8px 22px;
  border-radius: 12px;
  background-color: #fff;
  border: 1px solid rgba(105,105,105,0.15);
  color: #71663e;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  transition: background-color 0.5s, border-color 0.5s, color 0.5s, transform 0.75s;
}
.configure-btn:hover  { background-color: #2563eb; border-color: #2563eb; color: #fff; transform: scale(1.03); }
.configure-btn:active { transform: scale(0.97); transition: transform 0s; }
:global(.dark) .configure-btn,
:global(.darkmode) .configure-btn {
  background-color: rgba(255,255,255,0.06);
  border-color: rgba(255,255,255,0.12);
  color: rgba(255,255,255,0.75);
}
</style>
