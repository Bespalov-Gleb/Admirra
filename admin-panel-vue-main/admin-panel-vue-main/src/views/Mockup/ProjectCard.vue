<template>
  <div class="relative z-[2] flex min-h-full flex-col overflow-hidden px-[25px] py-[30px]">

    <!-- Heading -->
    <div class="pt-[15px] pb-[15px] mb-[10px]">
      <h3 class="text-[30px] font-semibold leading-none text-[#171717] dark:text-white">Проекты</h3>
    </div>

    <!-- Filters bar -->
    <div class="flex flex-wrap items-center justify-between gap-[10px] mb-[30px]">
      <!-- Left: selects + search -->
      <div class="flex flex-wrap items-center gap-[10px]">
        <!-- Dropdown: Все -->
        <div class="custom-select" :class="{ open: openSelect === 'type' }" v-click-outside="() => closeSelect('type')">
          <button class="cs-head dark:!border-white/10 dark:!bg-[#2C2F3D] dark:!text-white/70 dark:!shadow-[inset_0_0_0_1px_rgba(255,255,255,0.08)]" @click="toggleSelect('type')">
            <span class="cs-current">{{ projectFilterLabel }}</span>
            <span class="cs-arrow dark:!bg-white/10"><svg width="5" height="4" viewBox="0 0 9 6" fill="none"><path d="M0.5 1L4.5 5L8.5 1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg></span>
          </button>
          <div class="cs-list dark:!bg-[#2C2F3D] dark:!shadow-[0_0_0_1px_rgba(255,255,255,0.08)]">
            <div
              v-for="opt in projectFilterOptions"
              :key="opt.value"
              class="cs-option dark:!text-white/70 dark:hover:!bg-white/5"
              :class="{ selected: projectFilter === opt.value }"
              @click="selectProjectFilter(opt.value)"
            >{{ opt.label }}</div>
          </div>
        </div>

        <!-- Dropdown: Период -->
        <div class="custom-select" :class="{ open: openSelect === 'period' }" v-click-outside="() => closeSelect('period')">
          <button class="cs-head dark:!border-white/10 dark:!bg-[#2C2F3D] dark:!text-white/70 dark:!shadow-[inset_0_0_0_1px_rgba(255,255,255,0.08)]" @click="toggleSelect('period')">
            <span class="cs-current">{{ periodLabel }}</span>
            <span class="cs-arrow dark:!bg-white/10"><svg width="5" height="4" viewBox="0 0 9 6" fill="none"><path d="M0.5 1L4.5 5L8.5 1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg></span>
          </button>
          <div class="cs-list dark:!bg-[#2C2F3D] dark:!shadow-[0_0_0_1px_rgba(255,255,255,0.08)]">
            <div
              v-for="opt in periodOptions"
              :key="opt.value"
              class="cs-option dark:!text-white/70 dark:hover:!bg-white/5"
              :class="{ selected: periodDays === opt.value }"
              @click="selectPeriod(opt.value)"
            >{{ opt.label }}</div>
          </div>
        </div>

        <div class="search-wrap">
          <input
            v-model="search"
            type="text"
            class="search-input dark:!bg-[#2C2F3D] dark:!text-white/95 dark:!shadow-[inset_0_0_0_1px_rgba(255,255,255,0.12)] dark:placeholder:!text-white/55"
            placeholder="Поиск по проектам, номерам или доменам"
          />
          <div class="search-icon-circle dark:!bg-white/10">
            <svg width="7" height="7" viewBox="0 0 16 16" fill="none">
              <circle cx="6.5" cy="6.5" r="5.5" stroke="#ababab" stroke-width="1.8"/>
              <path d="M10.5 10.5L14 14" stroke="#ababab" stroke-width="1.8" stroke-linecap="round"/>
            </svg>
          </div>
        </div>
      </div>

      <!-- Right: bulk edit + view toggle -->
      <div class="flex items-center gap-[10px]">
        <button class="bulk-btn" @click="openMassEdit">
          <span>Массовое редактирование</span>
          <span class="bulk-btn__icon">
            <svg width="12" height="12" viewBox="0 0 14 14" fill="none">
              <path d="M1 13L5.5 8.5M13 1L8.5 5.5M5.5 8.5L8.5 5.5" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M2 12L1 13" stroke="white" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
          </span>
        </button>

        <div class="flex">
          <button class="view-btn _active dark:!bg-[#33405f] dark:!text-[#67a8ff]" aria-label="Карточки">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <rect x="1" y="1" width="6.5" height="6.5" rx="1.5" stroke="currentColor" stroke-width="1.5"/>
              <rect x="10.5" y="1" width="6.5" height="6.5" rx="1.5" stroke="currentColor" stroke-width="1.5"/>
              <rect x="1" y="10.5" width="6.5" height="6.5" rx="1.5" stroke="currentColor" stroke-width="1.5"/>
              <rect x="10.5" y="10.5" width="6.5" height="6.5" rx="1.5" stroke="currentColor" stroke-width="1.5"/>
            </svg>
          </button>
          <button class="view-btn dark:!text-white/35 dark:hover:!bg-white/5 dark:hover:!text-[#67a8ff]" aria-label="Строки" @click="router.push('/project-rows')">
            <svg width="18" height="14" viewBox="0 0 18 14" fill="none">
              <rect x="1" y="1" width="16" height="5" rx="1.5" stroke="currentColor" stroke-width="1.5"/>
              <rect x="1" y="8" width="16" height="5" rx="1.5" stroke="currentColor" stroke-width="1.5"/>
            </svg>
          </button>
        </div>
      </div>
    </div>

    <div v-if="isLoading" class="py-16 text-center text-[14px] text-gray-400">Загрузка проектов...</div>

    <div v-else-if="filteredProjects.length === 0" class="py-16 text-center text-[14px] text-gray-400">
      {{ search ? 'Проекты не найдены' : 'У вас пока нет проектов' }}
    </div>

    <!-- Projects grid -->
    <div v-else class="grid grid-cols-1 xl:grid-cols-2 gap-[15px] mb-[30px]">
      <div v-for="project in filteredProjects" :key="project.id" class="project-card bg-white rounded-[15px]">

        <!-- Card body -->
        <div class="p-[30px]">
          <!-- Project header row -->
          <div class="flex items-center justify-between pb-[10px] mb-[15px]">
            <div class="flex items-center">
              <div class="project-avatar">
                <img src="/admirra/img/avatars/avatar-40x40.png" :alt="project.name" class="w-full h-full object-cover" />
              </div>
              <div class="pl-[15px]">
                <h4 class="text-[15px] text-[#696969] font-medium mb-[3px] leading-none">{{ project.name }}</h4>
                <p class="text-[13px] text-[rgba(105,105,105,0.56)] leading-none">{{ project.description || `ID: ${shortId(project.id)}` }}</p>
              </div>
            </div>
            <button class="circle-open-btn flex-shrink-0" @click="openProject(project)">
              <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                <path d="M1 12L12 1M12 1H4.5M12 1V8.5" stroke="#696969" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </button>
          </div>

          <!-- Stats grid -->
          <div class="grid grid-cols-2 md:grid-cols-3 gap-[15px]">
            <div v-for="stat in projectStats(project)" :key="stat.label" class="stat-box">
              <div class="flex items-start pb-[5px] mb-[15px]">
                <div class="iconbox flex-shrink-0">
                  <svg width="11" height="11" fill="#2563eb">
                    <use :href="stat.icon" />
                  </svg>
                </div>
                <div class="pl-[10px] self-center">
                  <h4 class="text-[13px] text-[#696969] font-medium mb-[2px] leading-[1.1]">{{ stat.label }}</h4>
                  <p class="text-[12px] text-[rgba(105,105,105,0.56)] leading-[1.1]">{{ stat.subtitle }}</p>
                </div>
              </div>
              <div class="flex items-center mt-auto">
                <b class="text-[20px] font-semibold mr-[10px] leading-[1.1] text-[#2c2c2c]">{{ stat.value }}</b>
                <span class="badge-success">
                  <svg width="8" height="7" viewBox="0 0 12 9" fill="none">
                    <path d="M1 8L6 2L11 8" stroke="#16a34a" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                  {{ stat.change }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- Divider -->
        <hr class="project-divider m-0 border-0 border-t border-[rgba(0,0,0,0.05)]" />

        <!-- Balance section -->
        <div class="p-[30px]">
          <p class="text-[13px] text-[#696969] mb-[10px]">Актуальный баланс в ЛК:</p>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-[15px]">
            <div
              v-for="balance in projectBalances(project)"
              :key="balance.name"
              :style="{ backgroundColor: balance.bg }"
              class="balance-tile rounded-[12px] p-[10px]"
            >
              <div class="flex items-center justify-center">
                <img :src="balance.icon" :alt="balance.name" width="18" class="flex-shrink-0" />
                <span class="px-[10px] text-[13px] font-medium" :style="{ color: balance.color }">{{ balance.name }}</span>
                <span class="badge-white" :style="{ color: balance.color }">{{ balance.value }}</span>
              </div>
            </div>
          </div>
        </div>

      </div>
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
const { projects, isLoading, fetchProjects, setCurrentProject } = useProjects()

const projectFilter = ref('all')
const periodDays = ref(14)
const search = ref('')
const openSelect = ref(null)
const metricsByProjectId = ref({})

const projectFilterOptions = [
  { value: 'all', label: 'Все' },
  { value: 'active', label: 'Активные' },
  { value: 'inactive', label: 'Неактивные' },
]

const periodOptions = [
  { value: 14, label: '2 недели' },
  { value: 21, label: '3 недели' },
  { value: 28, label: '4 недели' },
  { value: 35, label: '5 недель' },
]

const filteredProjects = computed(() => {
  let list = projects.value
  if (projectFilter.value === 'active') {
    list = list.filter((p) => p.integrations?.some((i) => i.is_active))
  } else if (projectFilter.value === 'inactive') {
    list = list.filter((p) => !p.integrations?.some((i) => i.is_active))
  }
  const q = search.value.trim().toLowerCase()
  if (!q) return list
  return list.filter((p) =>
    p.name?.toLowerCase().includes(q) ||
    String(p.id || '').toLowerCase().includes(q) ||
    p.description?.toLowerCase().includes(q)
  )
})

const projectFilterLabel = computed(() => {
  return projectFilterOptions.find((option) => option.value === projectFilter.value)?.label || 'Все'
})

const periodLabel = computed(() => {
  return periodOptions.find((option) => option.value === periodDays.value)?.label || '2 недели'
})

function toggleSelect(name) {
  openSelect.value = openSelect.value === name ? null : name
}

function closeSelect(name) {
  if (openSelect.value === name) openSelect.value = null
}

function selectProjectFilter(value) {
  projectFilter.value = value
  openSelect.value = null
}

async function selectPeriod(value) {
  periodDays.value = value
  openSelect.value = null
  await loadProjectMetrics()
}

const vClickOutside = {
  mounted(el, binding) {
    el._outsideHandler = (event) => {
      if (!el.contains(event.target)) binding.value(event)
    }
    document.addEventListener('mousedown', el._outsideHandler)
  },
  unmounted(el) {
    document.removeEventListener('mousedown', el._outsideHandler)
  },
}

const emptyMetric = () => ({
  expenses: 0,
  impressions: 0,
  clicks: 0,
  leads: 0,
  cpc: 0,
  cpa: 0,
  balance: 0,
  trends: null,
})

const getProjectMetric = (projectId) => metricsByProjectId.value[projectId] || emptyMetric()

const formatNumber = (num) => new Intl.NumberFormat('ru-RU').format(Number(num || 0))
const formatMoney = (num) => `${new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 2 }).format(Number(num || 0))} ₽`

const trendText = (metric, key) => {
  const trend = Number(metric?.trends?.[key] || 0)
  const sign = trend >= 0 ? '+' : ''
  return `${sign}${trend.toFixed(1)}%`
}

const shortId = (id) => {
  const value = String(id || '')
  return value.length > 12 ? `${value.slice(0, 8)}...${value.slice(-4)}` : value || '-'
}

const integrationPlatforms = (project) => {
  const list = (project.integrations || []).map((i) => i.platform?.toUpperCase()).filter(Boolean)
  return Array.from(new Set(list))
}

const hasPlatform = (project, platform) => integrationPlatforms(project).includes(platform)

const projectStats = (project) => {
  const metric = getProjectMetric(project.id)
  return [
    { key: 'impressions', label: 'Показы', subtitle: 'По всем каналам', value: formatNumber(metric.impressions), icon: '/admirra/img/svg/sprite.svg#diagrama' },
    { key: 'clicks', label: 'Клики', subtitle: 'Все переходы', value: formatNumber(metric.clicks), icon: '/admirra/img/svg/sprite.svg#cursore' },
    { key: 'cpc', label: 'CPC', subtitle: 'Стоимость клика', value: formatMoney(metric.cpc), icon: '/admirra/img/svg/sprite.svg#diagrama-circle' },
    { key: 'expenses', label: 'Расходы', subtitle: 'За период', value: formatMoney(metric.expenses), icon: '/admirra/img/svg/sprite.svg#wallet' },
    { key: 'leads', label: 'Лиды', subtitle: 'По всем каналам', value: `${formatNumber(metric.leads)} шт.`, icon: '/admirra/img/svg/sprite.svg#calendar' },
    { key: 'cpa', label: 'CPA', subtitle: 'Стоимость лида', value: formatMoney(metric.cpa), icon: '/admirra/img/svg/sprite.svg#ok' },
  ].map((item) => ({ ...item, change: trendText(metric, item.key) }))
}

const projectBalances = (project) => {
  const metric = getProjectMetric(project.id)
  const balances = []
  if (hasPlatform(project, 'YANDEX') || !project.integrations?.length) {
    balances.push({
      name: 'Yandex Direct',
      value: formatMoney(metric.balance),
      icon: '/admirra/img/icons/yandex-direct.png',
      bg: '#fff2e4',
      color: '#71663e',
    })
  }
  if (hasPlatform(project, 'VK')) {
    balances.push({
      name: 'ВК Ads Manager',
      value: formatMoney(metric.balance),
      icon: '/admirra/img/icons/vk-ads.png',
      bg: '#f0f7ff',
      color: '#254b78',
    })
  }
  if (!balances.length) {
    balances.push({
      name: 'Шаблон канала',
      value: formatMoney(metric.balance),
      icon: '/admirra/img/icons/target.png',
      bg: '#fff0f1',
      color: '#662529',
    })
  }
  return balances
}

const loadProjectMetrics = async () => {
  const end = new Date()
  const start = new Date()
  start.setDate(end.getDate() - Number(periodDays.value || 14))
  const startDate = start.toISOString().slice(0, 10)
  const endDate = end.toISOString().slice(0, 10)

  const entries = await Promise.all(
    projects.value.map(async (project) => {
      try {
        const { data } = await api.get('dashboard/summary', {
          params: {
            client_id: project.id,
            platform: 'all',
            start_date: startDate,
            end_date: endDate,
          },
        })
        return [project.id, data || emptyMetric()]
      } catch {
        return [project.id, emptyMetric()]
      }
    })
  )
  metricsByProjectId.value = Object.fromEntries(entries)
}

const openProject = (project) => {
  setCurrentProject(project.id)
  router.push('/dashboard/general-3')
}

const openMassEdit = () => {
  toaster.info('Массовое редактирование доступно в табличном виде.')
  router.push('/project-rows')
}

onMounted(async () => {
  await fetchProjects()
  await loadProjectMetrics()
})
</script>

<style scoped>
/* ---- Custom Select ---- */
.custom-select {
  position: relative;
  display: inline-flex;
  flex-direction: column;
}
.cs-head {
  display: inline-flex;
  align-items: center;
  background-color: #fff;
  border-radius: 15px;
  min-height: 46px;
  padding: 8px 17px;
  font-size: 13px;
  font-weight: 500;
  color: rgba(0, 0, 0, 0.4);
  border: 1px solid transparent;
  cursor: pointer;
  outline: none;
  transition: border-color 0.2s;
  user-select: none;
  white-space: nowrap;
}
.custom-select.open .cs-head {
  border-color: rgba(0, 0, 0, 0.1);
}
.cs-current {
  margin-right: 25px;
}
.cs-arrow {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  background-color: #f5f7f9;
  border-radius: 50%;
  flex-shrink: 0;
  transition: transform 0.3s;
}
.custom-select.open .cs-arrow {
  transform: rotate(180deg);
}
.cs-list {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  min-width: 100%;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 0 0 1px rgba(68, 68, 68, 0.1);
  padding: 0;
  z-index: 99;
  overflow: hidden;
  /* closed */
  opacity: 0;
  pointer-events: none;
  transform-origin: 50% 0;
  transform: scale(0.75) translateY(-21px);
  transition: transform 0.2s cubic-bezier(0.5, 0, 0, 1.25), opacity 0.15s ease-out;
}
.custom-select.open .cs-list {
  opacity: 1;
  pointer-events: auto;
  transform: scale(1) translateY(0);
}
.cs-option {
  padding: 12px 25px 12px 17px;
  font-size: 13px;
  font-weight: 400;
  color: rgba(0, 0, 0, 0.7);
  cursor: pointer;
  transition: background-color 0.2s;
  white-space: nowrap;
}
.cs-option:hover { background-color: #f5f7f9; }
.cs-option.selected { font-weight: 600; }

/* ---- Search ---- */
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
  box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.08);
  transition: box-shadow 0.5s;
}
.search-input:focus { box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.24), 0 0 10px rgba(37, 99, 235, 0.15); }
.search-input::placeholder { color: rgba(0, 0, 0, 0.3); }
.search-icon-circle {
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

/* ---- Bulk edit button ---- */
.bulk-btn {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-height: 46px;
  padding: 8px 17px;
  font-size: 13px;
  font-weight: 500;
  color: #fff;
  background: linear-gradient(270deg, #06b5d4 0.35%, #1f9de4 32.08%, #2563eb 96.51%);
  border: none;
  border-radius: 15px;
  cursor: pointer;
  transition: transform 0.75s;
  white-space: nowrap;
}
.bulk-btn:hover { transform: scale(1.02); }
.bulk-btn:active { transform: scale(0.97); transition: transform 0s; }
.bulk-btn__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 6px;
  flex-shrink: 0;
}

/* ---- View toggle ---- */
.view-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 46px;
  height: 46px;
  border-radius: 12px;
  background-color: transparent;
  border: 0;
  cursor: pointer;
  color: #c9c9c9;
  transition: color 0.3s, background-color 0.3s;
}
.view-btn._active {
  background-color: #fff;
  color: #5187ff;
}
.view-btn:not(._active):hover { color: #5187ff; }

/* ---- Project avatar ---- */
.project-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  overflow: hidden;
  flex-shrink: 0;
}

/* ---- Circle open button ---- */
.circle-open-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 1px solid rgba(169, 169, 169, 0.35);
  background: transparent;
  cursor: pointer;
  transition: border-color 0.3s;
}
.circle-open-btn:hover { border-color: rgba(37, 99, 235, 0.4); }

/* ---- Stat box ---- */
.stat-box {
  display: flex;
  flex-direction: column;
  padding: 15px;
  background-color: #f8fafb;
  border-radius: 12px;
  line-height: 1.1;
}

/* ---- Icon box ---- */
.iconbox {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: #fff;
  border-radius: 6px;
}

/* ---- Badges ---- */
.badge-success {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 3px 7px;
  background-color: rgba(0, 255, 78, 0.1);
  color: #16a34a;
  font-size: 11px;
  font-weight: 500;
  border-radius: 100px;
  white-space: nowrap;
}
.badge-white {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  padding: 0 8px;
  background: #fff;
  border-radius: 100px;
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
}

:global(.dark) .cs-head,
:global(.darkmode) .cs-head,
:global(.dark) .cs-list,
:global(.darkmode) .cs-list {
  background-color: #2c2f3d;
  color: rgba(255, 255, 255, 0.65);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.08);
}
:global(.dark) .custom-select.open .cs-head,
:global(.darkmode) .custom-select.open .cs-head {
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.14);
}
:global(.dark) .cs-arrow,
:global(.darkmode) .cs-arrow,
:global(.dark) .search-icon-circle,
:global(.darkmode) .search-icon-circle {
  background-color: rgba(255, 255, 255, 0.08);
}
:global(.dark) .cs-arrow path,
:global(.darkmode) .cs-arrow path {
  stroke: rgba(255, 255, 255, 0.65);
}
:global(.dark) .cs-option,
:global(.darkmode) .cs-option {
  color: rgba(255, 255, 255, 0.72);
}
:global(.dark) .cs-option:hover,
:global(.darkmode) .cs-option:hover,
:global(.dark) .cs-option.selected,
:global(.darkmode) .cs-option.selected {
  background-color: rgba(255, 255, 255, 0.06);
}
:global(.dark) .search-input,
:global(.darkmode) .search-input {
  background-color: #2c2f3d;
  color: rgba(255, 255, 255, 0.88);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.08);
}
:global(.dark) .search-input::placeholder,
:global(.darkmode) .search-input::placeholder {
  color: rgba(255, 255, 255, 0.55) !important;
  -webkit-text-fill-color: rgba(255, 255, 255, 0.55) !important;
}
:global(.dark) .view-btn._active,
:global(.darkmode) .view-btn._active {
  background-color: rgba(74, 122, 255, 0.14);
  color: #67a8ff;
}
:global(.dark) .project-card,
:global(.darkmode) .project-card {
  background-color: #2c2f3d;
}
:global(.dark) .view-btn:not(._active),
:global(.darkmode) .view-btn:not(._active) {
  color: rgba(255, 255, 255, 0.32);
}
:global(.dark) .view-btn:not(._active):hover,
:global(.darkmode) .view-btn:not(._active):hover {
  color: #67a8ff;
  background-color: rgba(255, 255, 255, 0.06);
}
:global(.dark) .project-card h4,
:global(.darkmode) .project-card h4 {
  color: rgba(255, 255, 255, 0.82);
}
:global(.dark) .project-card p,
:global(.darkmode) .project-card p {
  color: rgba(255, 255, 255, 0.5);
}
:global(.dark) .project-divider,
:global(.darkmode) .project-divider {
  border-top-color: rgba(255, 255, 255, 0.1);
}
:global(.dark) .circle-open-btn,
:global(.darkmode) .circle-open-btn {
  border-color: rgba(255, 255, 255, 0.18);
}
:global(.dark) .circle-open-btn path,
:global(.darkmode) .circle-open-btn path {
  stroke: rgba(255, 255, 255, 0.65);
}
:global(.dark) .stat-box,
:global(.darkmode) .stat-box {
  background-color: rgba(255, 255, 255, 0.05);
}
:global(.dark) .iconbox,
:global(.darkmode) .iconbox,
:global(.dark) .badge-white,
:global(.darkmode) .badge-white {
  background-color: rgba(255, 255, 255, 0.08);
}
:global(.dark) .balance-tile,
:global(.darkmode) .balance-tile {
  background-color: rgba(255, 255, 255, 0.05) !important;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.08);
}
:global(.dark) .stat-box b,
:global(.darkmode) .stat-box b {
  color: rgba(255, 255, 255, 0.9);
}
</style>
