<template>
  <div class="relative z-[2] flex min-h-full flex-col overflow-visible px-[1.7361rem] py-[2.0833rem]">

    <!-- Heading -->
    <div class="pt-[1.0417rem] pb-[1.0417rem] mb-[0.6944rem]">
      <h3 class="text-[2.0833rem] font-semibold leading-none text-[#171717] dark:text-white">Проекты</h3>
    </div>

    <!-- Filters bar -->
    <div class="flex flex-wrap items-center justify-between gap-[0.6944rem] mb-[2.0833rem]">
      <!-- Left: selects + search -->
      <div class="flex flex-wrap items-center gap-[0.6944rem]">
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
        <div class="custom-select" :class="{ open: openSelect === 'period' }" v-click-outside="closePeriodSelect">
          <button ref="periodTriggerRef" class="cs-head dark:!border-white/10 dark:!bg-[#2C2F3D] dark:!text-white/70 dark:!shadow-[inset_0_0_0_1px_rgba(255,255,255,0.08)]" @click="toggleSelect('period')">
            <span class="cs-current">{{ periodLabel }}</span>
            <span class="cs-arrow dark:!bg-white/10"><svg width="5" height="4" viewBox="0 0 9 6" fill="none"><path d="M0.5 1L4.5 5L8.5 1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg></span>
          </button>
          <Teleport to="body">
            <div
              v-if="openSelect === 'period'"
              ref="periodPopoverRef"
              class="period-popover period-list"
              :style="periodPopoverStyle"
            >
              <template v-for="(opt, index) in periodOptions" :key="opt.value || `${opt.type}-${index}`">
                <DateRangePicker
                  v-if="opt.type === 'label'"
                  v-model="customPeriodRange"
                  class="project-period-custom-picker"
                  :trigger-text="opt.label"
                  @change="selectCustomPeriod"
                />
                <div v-else-if="opt.type === 'divider'" class="period-list__divider"></div>
                <button
                  v-else
                  type="button"
                  class="period-option"
                  :class="{ selected: periodKey === opt.value }"
                  @click="selectPeriod(opt.value)"
                >
                  <span>{{ opt.label }}</span>
                  <svg v-if="periodKey === opt.value" class="period-option__check" viewBox="0 0 18 14" fill="none" aria-hidden="true">
                    <path d="M1.5 7.2 6.5 12 16.5 1.5" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                </button>
              </template>
            </div>
          </Teleport>
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
      <div class="flex items-center gap-[0.6944rem]">
        <button class="bulk-btn" @click="openMassEdit">
          <span>Массовое редактирование</span>
          <span class="bulk-btn__icon">
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path d="M9.7 3.2 12.8 6.3M2.8 13.2l3.1-.6 7.25-7.25a2.17 2.17 0 0 0-3.07-3.07L2.8 9.55v3.65Z" stroke="currentColor" stroke-width="1.45" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M2.8 13.2h3.4" stroke="currentColor" stroke-width="1.45" stroke-linecap="round"/>
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

    <div v-if="isLoading" class="py-16 text-center text-[0.9722rem] text-gray-400">Загрузка проектов...</div>

    <div v-else-if="filteredProjects.length === 0" class="py-16 text-center text-[0.9722rem] text-gray-400">
      {{ search ? 'Проекты не найдены' : 'У вас пока нет проектов' }}
    </div>

    <!-- Projects grid -->
    <div v-else class="grid grid-cols-1 xl:grid-cols-2 gap-[1.0417rem] mb-[2.0833rem]">
      <div v-for="project in filteredProjects" :key="project.id" class="project-card bg-white rounded-[1.0417rem]">

        <!-- Card body -->
        <div class="p-[2.0833rem]">
          <!-- Project header row -->
          <div class="flex items-center justify-between pb-[0.6944rem] mb-[1.0417rem]">
            <div class="flex items-center">
              <button type="button" class="project-avatar project-avatar--editable" :aria-label="`Загрузить аватарку проекта ${project.name}`" @click.stop="openAvatarModal(project)">
                <img v-if="projectAvatarUrl(project)" :src="projectAvatarUrl(project)" :alt="project.name" class="w-full h-full object-cover" />
                <span v-else class="project-avatar__initials">{{ projectInitials(project) }}</span>
                <span :class="['project-avatar__edit', projectAvatarUrl(project) ? 'project-avatar__edit--hover' : 'project-avatar__edit--default']" aria-hidden="true">
                  <svg viewBox="0 0 16 16" fill="none">
                    <path d="M9.7 3.2 12.8 6.3M2.8 13.2l3.1-.6 7.25-7.25a2.17 2.17 0 0 0-3.07-3.07L2.8 9.55v3.65Z" stroke="currentColor" stroke-width="1.45" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                </span>
              </button>
              <div class="pl-[1.0417rem]">
                <button
                  type="button"
                  class="project-title-link text-[1.0417rem] text-[#696969] font-medium mb-[0.2083rem] leading-none"
                  @click="openProject(project)"
                >
                  {{ project.name }}
                </button>
                <p v-if="project.description" class="mb-[0.2778rem] text-[0.9028rem] text-[rgba(105,105,105,0.56)] leading-none">{{ project.description }}</p>
                <button type="button" class="project-id-link" @click.stop="copyProjectId(project)">ID: {{ projectSupportId(project) }}</button>
              </div>
            </div>
            <button class="circle-open-btn flex-shrink-0" @click="openProject(project)">
              <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                <path d="M1 12L12 1M12 1H4.5M12 1V8.5" stroke="#696969" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </button>
          </div>

          <!-- Stats grid -->
          <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-[1.0417rem]">
            <div v-for="stat in projectStats(project)" :key="stat.label" class="stat-box">
              <div class="flex items-start pb-[0.3472rem] mb-[1.0417rem]">
                <div class="iconbox flex-shrink-0">
                  <svg width="11" height="11" fill="#2563eb">
                    <use :href="stat.icon" />
                  </svg>
                </div>
                <div class="pl-[0.6944rem] self-center min-w-0">
                  <h4 class="text-[0.9028rem] text-[#696969] font-medium mb-[0.1389rem] leading-[1.1] truncate">{{ stat.label }}</h4>
                  <p class="text-[0.8333rem] text-[rgba(105,105,105,0.56)] leading-[1.1] truncate">{{ stat.subtitle }}</p>
                </div>
              </div>
              <div class="stat-value-row flex items-center mt-auto">
                <b class="min-w-0 truncate text-[1.3889rem] font-semibold leading-[1.1] text-[#2c2c2c]">{{ stat.value }}</b>
                <span :class="trendBadgeClass(getProjectMetric(project.id), stat.key)">
                  <svg :class="trendArrowClass(getProjectMetric(project.id), stat.key)" width="8" height="7" viewBox="0 0 12 9" fill="none">
                    <path d="M1 8L6 2L11 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
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
        <div class="p-[2.0833rem]">
          <p class="text-[0.9028rem] text-[#696969] mb-[0.6944rem]">Актуальный баланс в ЛК:</p>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-[1.0417rem]">
            <div
              v-for="balance in projectBalances(project)"
              :key="balance.name"
              :style="{ backgroundColor: balance.bg }"
              class="balance-tile rounded-[0.8333rem] p-[0.6944rem]"
            >
              <div class="flex min-w-0 items-center justify-center gap-[0.5556rem]">
                <img :src="balance.icon" :alt="balance.name" width="18" class="flex-shrink-0" />
                <span class="min-w-0 truncate text-[0.9028rem] font-medium" :style="{ color: balance.color }">{{ balance.name }}</span>
                <span class="badge-white shrink-0" :style="{ color: balance.color }">{{ balance.value }}</span>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>

    <ProjectAvatarUploadModal
      v-if="avatarProject"
      :project="avatarProject"
      @close="avatarProject = null"
      @saved="handleAvatarSaved"
    />

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api/axios'
import { useProjects } from '../../composables/useProjects'
import { useToaster } from '../../composables/useToaster'
import { hasActiveProjectIntegration, hasProjectPlatform, projectPlatforms } from '../../utils/projectIntegrations'
import { getProjectPeriodLabel, getProjectPeriodRange, projectPeriodOptions } from '../../utils/projectPeriods'
import { projectAvatarUrl, projectInitials } from '../../utils/projectAvatar'
import DateRangePicker from '../../components/ui/DateRangePicker.vue'
import ProjectAvatarUploadModal from '../../components/ProjectAvatarUploadModal.vue'

const router = useRouter()
const toaster = useToaster()
const { projects, isLoading, fetchProjects, setCurrentProject } = useProjects()

const projectFilter = ref('all')
const periodKey = ref('last_7_days')
const customPeriodRange = ref({ start: null, end: null })
const search = ref('')
const openSelect = ref(null)
const metricsByProjectId = ref({})
const periodTriggerRef = ref(null)
const periodPopoverRef = ref(null)
const periodOptions = projectPeriodOptions
const avatarProject = ref(null)

const projectFilterOptions = [
  { value: 'all', label: 'Все' },
  { value: 'active', label: 'Активные' },
  { value: 'inactive', label: 'Неактивные' },
]

const filteredProjects = computed(() => {
  let list = projects.value
  if (projectFilter.value === 'active') {
    list = list.filter(hasActiveProjectIntegration)
  } else if (projectFilter.value === 'inactive') {
    list = list.filter((p) => !hasActiveProjectIntegration(p))
  }
  const q = search.value.trim().toLowerCase()
  if (!q) return list
  return list.filter((p) =>
    p.name?.toLowerCase().includes(q) ||
    String(p.display_id || '').toLowerCase().includes(q) ||
    String(p.id || '').toLowerCase().includes(q) ||
    p.description?.toLowerCase().includes(q)
  )
})

const projectFilterLabel = computed(() => {
  return projectFilterOptions.find((option) => option.value === projectFilter.value)?.label || 'Все'
})

const periodLabel = computed(() => {
  if (periodKey.value === 'custom' && customPeriodRange.value.start && customPeriodRange.value.end) {
    return `${formatPeriodDate(customPeriodRange.value.start)} — ${formatPeriodDate(customPeriodRange.value.end)}`
  }
  return getProjectPeriodLabel(periodKey.value)
})

const periodPopoverStyle = computed(() => {
  if (openSelect.value !== 'period' || !periodTriggerRef.value || typeof window === 'undefined') return {}
  const rect = periodTriggerRef.value.getBoundingClientRect()
  const width = Math.max(rect.width, 302)
  const viewportPadding = 12
  const left = Math.min(
    Math.max(viewportPadding, rect.left),
    Math.max(viewportPadding, window.innerWidth - width - viewportPadding)
  )
  return {
    top: `${rect.bottom + 4}px`,
    left: `${left}px`,
    minWidth: `${width}px`
  }
})

function toggleSelect(name) {
  openSelect.value = openSelect.value === name ? null : name
}

function closeSelect(name) {
  if (openSelect.value === name) openSelect.value = null
}

function closePeriodSelect(event) {
  if (periodPopoverRef.value?.contains(event.target)) return
  if (event.target?.closest?.('.calendar-popup')) return
  closeSelect('period')
}

function selectProjectFilter(value) {
  projectFilter.value = value
  openSelect.value = null
}

async function selectPeriod(value) {
  periodKey.value = value
  openSelect.value = null
  await loadProjectMetrics()
}

async function selectCustomPeriod(range) {
  if (!range?.start || !range?.end) return
  customPeriodRange.value = { start: range.start, end: range.end }
  periodKey.value = 'custom'
  openSelect.value = null
  await loadProjectMetrics()
}

function formatPeriodDate(value) {
  const [year, month, day] = String(value).split('-')
  if (!year || !month || !day) return value
  return `${day}.${month}.${year}`
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

const costTrendKeys = new Set(['cpc', 'cpa'])

const isNegativeTrend = (metric, key) => {
  const trend = Number(metric?.trends?.[key] || 0)
  return costTrendKeys.has(key) ? trend > 0 : trend < 0
}

const isTrendDown = (metric, key) => Number(metric?.trends?.[key] || 0) < 0

const trendBadgeClass = (metric, key) => [
  'trend-badge shrink-0',
  isNegativeTrend(metric, key)
    ? 'trend-badge--negative'
    : 'trend-badge--positive'
]

const trendArrowClass = (metric, key) => [
  'trend-arrow',
  isTrendDown(metric, key) ? 'trend-arrow--down' : ''
]

const shortId = (id) => {
  const value = String(id || '')
  return value.length > 12 ? `${value.slice(0, 8)}...${value.slice(-4)}` : value || '-'
}

const projectSupportId = (project) => project?.display_id || shortId(project?.id)

async function copyProjectId(project) {
  const value = String(project?.display_id || project?.id || '')
  if (!value) return
  try {
    await navigator.clipboard.writeText(value)
    toaster.success('ID проекта скопирован')
  } catch {
    toaster.error('Не удалось скопировать ID')
  }
}

const hasPlatform = (project, platform) => hasProjectPlatform(project, platform)
const hasAnyPlatform = (project) => projectPlatforms(project).length > 0

const projectStats = (project) => {
  const metric = getProjectMetric(project.id)
  return [
    { key: 'impressions', label: 'Показы', subtitle: 'По всем каналам', value: formatNumber(metric.impressions), icon: '/admirra/img/svg/sprite.svg#diagrama' },
    { key: 'clicks', label: 'Клики', subtitle: 'Все переходы', value: formatNumber(metric.clicks), icon: '/admirra/img/svg/sprite.svg#cursore' },
    { key: 'cpc', label: 'CPC', subtitle: 'Стоимость клика', value: formatMoney(metric.cpc), icon: '/admirra/img/svg/sprite.svg#diagrama-circle' },
    { key: 'expenses', label: 'Расходы', subtitle: 'За период', value: formatMoney(metric.expenses), icon: '/admirra/img/svg/sprite.svg#wallet' },
    { key: 'leads', label: 'Лиды', subtitle: 'По всем каналам', value: `${formatNumber(metric.leads)} шт.`, icon: '/admirra/img/svg/sprite.svg#calendar' },
    { key: 'cpa', label: 'CPL', subtitle: 'Стоимость лида', value: formatMoney(metric.cpa), icon: '/admirra/img/svg/sprite.svg#ok' },
  ].map((item) => ({ ...item, change: trendText(metric, item.key) }))
}

const projectBalances = (project) => {
  const metric = getProjectMetric(project.id)
  const balances = []
  if (hasPlatform(project, 'YANDEX') || !hasAnyPlatform(project)) {
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
  const { startDate, endDate } = getProjectPeriodRange(periodKey.value, customPeriodRange.value)

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

function openAvatarModal(project) {
  avatarProject.value = project
}

function updateProjectInList(updatedProject) {
  const index = projects.value.findIndex((project) => project.id === updatedProject.id)
  if (index !== -1) {
    projects.value[index] = { ...projects.value[index], ...updatedProject }
  }
}

function handleAvatarSaved(updatedProject) {
  updateProjectInList(updatedProject)
  toaster.success('Аватарка проекта обновлена.')
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
  border-radius: 1.0417rem;
  min-height: 3.1944rem;
  padding: 0.5556rem 1.1806rem;
  font-size: 0.9028rem;
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
  margin-right: 1.7361rem;
}
.cs-arrow {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.1111rem;
  height: 1.1111rem;
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
  top: calc(100% + 0.2778rem);
  left: 0;
  min-width: 100%;
  background-color: #fff;
  border-radius: 0.5556rem;
  box-shadow: 0 0 0 1px rgba(68, 68, 68, 0.1);
  padding: 0;
  z-index: 99;
  overflow: hidden;
  /* closed */
  opacity: 0;
  pointer-events: none;
  transform-origin: 50% 0;
  transform: scale(0.75) translateY(-1.4583rem);
  transition: transform 0.2s cubic-bezier(0.5, 0, 0, 1.25), opacity 0.15s ease-out;
}
.custom-select.open .cs-list {
  opacity: 1;
  pointer-events: auto;
  transform: scale(1) translateY(0);
}
.cs-option {
  padding: 0.8333rem 1.7361rem 0.8333rem 1.1806rem;
  font-size: 0.9028rem;
  font-weight: 400;
  color: rgba(0, 0, 0, 0.7);
  cursor: pointer;
  transition: background-color 0.2s;
  white-space: nowrap;
}
.cs-option:hover { background-color: #f5f7f9; }
.cs-option.selected { font-weight: 600; }

.period-list {
  position: fixed;
  z-index: 5000;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 0;
  background-color: #fff;
  min-width: 21rem;
  border-radius: 1.0417rem;
  box-shadow: 0 1.3889rem 3.4722rem rgba(15, 23, 42, 0.14), 0 0 0 1px rgba(68, 68, 68, 0.08);
}

.period-list__title {
  padding: 1.1806rem 1.5278rem;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  color: #171717;
  font-size: 1.1111rem;
  font-weight: 600;
  line-height: 1.15;
  white-space: nowrap;
}

.project-period-custom-picker :deep(.drp-trigger) {
  height: auto;
  min-height: 3.8194rem;
  justify-content: flex-start;
  border: 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 0;
  padding: 1.1806rem 1.5278rem;
  background: transparent;
  box-shadow: none;
  color: #171717;
  font-size: 1.1111rem;
  line-height: 1.15;
}

.project-period-custom-picker :deep(.drp-trigger:hover) {
  background: #f5f7f9;
  border-color: rgba(0, 0, 0, 0.06);
  box-shadow: none;
}

.project-period-custom-picker :deep(.drp-trigger .truncate) {
  color: #171717;
  font-weight: 600;
}

.project-period-custom-picker :deep(.drp-trigger svg),
.project-period-custom-picker :deep(.drp-trigger > span) {
  display: none;
}

.period-list__divider {
  height: 1px;
  margin: 0.3472rem 0;
  background: rgba(0, 0, 0, 0.06);
}

.period-option {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 1.25rem;
  align-items: center;
  gap: 1.25rem;
  width: 100%;
  min-height: 3.4722rem;
  padding: 0.8333rem 1.5278rem;
  border: 0;
  background: transparent;
  color: rgba(0, 0, 0, 0.78);
  cursor: pointer;
  font-size: 1.0417rem;
  line-height: 1.2;
  text-align: left;
  white-space: nowrap;
  transition: background-color 0.2s;
}

.period-option:hover,
.period-option.selected {
  background-color: #f5f7f9;
}

.period-option__check {
  width: 1.25rem;
  height: 1.25rem;
  color: #171717;
}

/* ---- Search ---- */
.search-wrap { position: relative; }
.search-input {
  width: 24.5833rem;
  height: 3.1944rem;
  padding: 0 3.125rem 0 1.1806rem;
  font-size: 0.9028rem;
  color: #2c2c2c;
  background-color: #fff;
  border: none;
  border-radius: 0.8333rem;
  outline: none;
  box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.08);
  transition: box-shadow 0.5s;
}
.search-input:focus { box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.24), 0 0 0.6944rem rgba(37, 99, 235, 0.15); }
.search-input::placeholder { color: rgba(0, 0, 0, 0.3); }
.search-icon-circle {
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

/* ---- Bulk edit button ---- */
.bulk-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.6944rem;
  min-height: 3.1944rem;
  padding: 0.5556rem 1.1806rem;
  font-size: 0.9028rem;
  font-weight: 500;
  color: #fff;
  background: linear-gradient(270deg, #06b5d4 0.35%, #1f9de4 32.08%, #2563eb 96.51%);
  border: none;
  border-radius: 1.0417rem;
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
  width: 1.5278rem;
  height: 1.5278rem;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 0.4167rem;
  flex-shrink: 0;
  color: #fff;
}
.bulk-btn__icon svg {
  display: block;
  width: 0.9722rem;
  height: 0.9722rem;
}

/* ---- View toggle ---- */
.view-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 3.1944rem;
  height: 3.1944rem;
  border-radius: 0.8333rem;
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

.project-title-link {
  display: block;
  max-width: 100%;
  padding: 0;
  border: 0;
  background: transparent;
  text-align: left;
  cursor: pointer;
  transition: color 0.2s;
}

.project-title-link:hover {
  color: #2563eb;
}

.project-id-link {
  display: inline-flex;
  max-width: 100%;
  padding: 0;
  border: 0;
  background: transparent;
  color: rgba(105, 105, 105, 0.56);
  cursor: pointer;
  font-size: 0.9028rem;
  line-height: 1;
  text-align: left;
  transition: color 0.2s;
}

.project-id-link:hover {
  color: #2563eb;
}

/* ---- Project avatar ---- */
.project-avatar {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.7778rem;
  height: 2.7778rem;
  border: 0;
  border-radius: 50%;
  background: #e8eef9;
  color: #2563eb;
  font-size: 0.9028rem;
  font-weight: 700;
  overflow: visible;
  flex-shrink: 0;
}

.project-avatar--editable {
  cursor: pointer;
}

.project-avatar--editable img {
  border-radius: 50%;
  transition: filter 0.2s;
}

.project-avatar__initials {
  line-height: 1;
}

.project-avatar__edit {
  position: absolute;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  pointer-events: none;
  transition: opacity 0.2s, background-color 0.2s, border-color 0.2s;
}

.project-avatar__edit--default {
  right: -0.0694rem;
  bottom: -0.0694rem;
  width: 1.1111rem;
  height: 1.1111rem;
  background: #2563eb;
  color: #fff;
  box-shadow: 0 0 0 0.1389rem #fff;
}

.project-avatar__edit--hover {
  inset: 0;
  width: 100%;
  height: 100%;
  border: 1px dashed rgba(107, 114, 128, 0.72);
  background: rgba(243, 244, 246, 0.72);
  color: #6b7280;
  opacity: 0;
  backdrop-filter: blur(1px);
}

.project-avatar--editable:hover .project-avatar__edit--hover {
  opacity: 1;
}

.project-avatar--editable:hover img + .project-avatar__edit--hover {
  opacity: 1;
}

.project-avatar--editable:hover img {
  filter: grayscale(0.12) brightness(0.96);
}

.project-avatar__edit svg {
  width: 0.625rem;
  height: 0.625rem;
}

.project-avatar__edit--hover svg {
  width: 1rem;
  height: 1rem;
}

/* ---- Circle open button ---- */
.circle-open-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.7778rem;
  height: 2.7778rem;
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
  padding: 1.0417rem;
  background-color: #f8fafb;
  border-radius: 0.8333rem;
  line-height: 1.1;
}

/* ---- Icon box ---- */
.iconbox {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.2222rem;
  height: 2.2222rem;
  background: #fff;
  border-radius: 0.4167rem;
}

/* ---- Badges ---- */
.badge-success {
  display: inline-flex;
  align-items: center;
  gap: 0.2083rem;
  padding: 0.2083rem 0.4861rem;
  background-color: rgba(0, 255, 78, 0.1);
  color: #16a34a;
  font-size: 0.7639rem;
  font-weight: 500;
  border-radius: 6.9444rem;
  white-space: nowrap;
}

.trend-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.2083rem;
  padding: 0.2083rem 0.4861rem;
  font-size: 0.7639rem;
  font-weight: 500;
  border-radius: 6.9444rem;
  white-space: nowrap;
}

.trend-badge--positive {
  background-color: rgba(0, 255, 78, 0.1);
  color: #16a34a;
}

.trend-badge--negative {
  background-color: rgba(239, 68, 68, 0.1);
  color: #dc2626;
}

.trend-arrow {
  transition: transform 0.2s;
}

.trend-arrow--down {
  transform: rotate(180deg);
}

.stat-value-row {
  min-width: 0;
  gap: 0.5556rem;
}

.badge-white {
  display: inline-flex;
  align-items: center;
  min-height: 1.5278rem;
  padding: 0 0.5556rem;
  background: #fff;
  border-radius: 6.9444rem;
  font-size: 0.9028rem;
  font-weight: 500;
  white-space: nowrap;
  max-width: 100%;
}

.balance-tile {
  min-width: 0;
}

@media (max-width: 322.5px) {
  .stat-value-row {
    align-items: flex-start;
    flex-direction: column;
  }

  .badge-success,
  .trend-badge {
    max-width: 100%;
  }

  .balance-tile > div {
    justify-content: flex-start;
  }
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
:global(.dark) .period-list__title,
:global(.darkmode) .period-list__title {
  border-bottom-color: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.9);
}
:global(.dark) .period-popover,
:global(.darkmode) .period-popover {
  background-color: #2c2f3d;
  box-shadow: 0 1.3889rem 3.4722rem rgba(0, 0, 0, 0.32), 0 0 0 1px rgba(255, 255, 255, 0.08);
}
:global(.dark) .period-list__divider,
:global(.darkmode) .period-list__divider {
  background: rgba(255, 255, 255, 0.08);
}
:global(.dark) .period-option,
:global(.darkmode) .period-option {
  color: rgba(255, 255, 255, 0.72);
}
:global(.dark) .period-option:hover,
:global(.darkmode) .period-option:hover,
:global(.dark) .period-option.selected,
:global(.darkmode) .period-option.selected {
  background: rgba(255, 255, 255, 0.06);
}
:global(.dark) .period-option__check,
:global(.darkmode) .period-option__check {
  color: rgba(255, 255, 255, 0.9);
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
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.28), inset 0 1px 0 rgba(255, 255, 255, 0.07);
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
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.07);
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
