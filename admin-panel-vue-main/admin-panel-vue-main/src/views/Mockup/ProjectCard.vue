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
    <div v-else class="projects-tile-grid mb-[2.0833rem]">
      <div v-for="project in filteredProjects" :key="project.id" class="project-card project-card--tile bg-white rounded-[1.0417rem]">

        <div class="project-tile-main">
          <div class="project-tile-header">
            <div class="project-tile-identity">
              <button type="button" class="project-avatar project-avatar--editable" :aria-label="`Загрузить аватарку проекта ${project.name}`" @click.stop="openAvatarModal(project)">
                <img v-if="projectAvatarUrl(project)" :src="projectAvatarUrl(project)" :alt="project.name" class="w-full h-full object-cover" />
                <span v-else class="project-avatar__initials">{{ projectInitials(project) }}</span>
                <span :class="['project-avatar__edit', projectAvatarUrl(project) ? 'project-avatar__edit--hover' : 'project-avatar__edit--default']" aria-hidden="true">
                  <svg viewBox="0 0 16 16" fill="none">
                    <path d="M9.7 3.2 12.8 6.3M2.8 13.2l3.1-.6 7.25-7.25a2.17 2.17 0 0 0-3.07-3.07L2.8 9.55v3.65Z" stroke="currentColor" stroke-width="1.45" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                </span>
              </button>
              <div class="project-tile-title-block">
                <button
                  type="button"
                  class="project-title-link project-title-link--tile"
                  @click="openProject(project)"
                >
                  {{ project.name }}
                </button>
                <p class="project-tile-description">{{ project.description || 'Без описания' }}</p>
                <button type="button" class="project-tile-id" @click.stop="copyProjectId(project)">
                  ID {{ projectSupportId(project) }}
                </button>
              </div>
            </div>
            <div class="project-tile-actions">
              <button class="analytics-open-btn flex-shrink-0" @click="openProject(project)" title="Открыть аналитику">
                <span>Аналитика</span>
                <svg width="8" height="8" viewBox="0 0 13 13" fill="none">
                  <path d="M1 12L12 1M12 1H4.5M12 1V8.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </button>
            </div>
          </div>

          <div class="project-tile-stats">
            <div v-for="stat in projectStats(project)" :key="stat.label" class="stat-box">
              <span class="stat-box__label">{{ stat.label }}</span>
              <b class="stat-box__value">{{ stat.value }}</b>
              <span :class="trendBadgeClass(getProjectMetric(project.id), stat.key)">
                {{ stat.change }}
              </span>
            </div>
          </div>

          <div class="project-goals-section">
            <button type="button" class="project-goals-title" @click="toggleProjectGoals(project.id)">
              <span>Целевые действия по каналам</span>
              <span class="project-goals-title__action">
                {{ isProjectGoalsExpanded(project.id) ? 'Свернуть' : 'Развернуть' }}
                <svg :class="{ 'project-goals-title__icon--open': isProjectGoalsExpanded(project.id) }" class="project-goals-title__icon" width="11" height="7" viewBox="0 0 12 8" fill="none">
                <path d="M1 1.5 6 6.5 11 1.5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              </span>
            </button>

            <div class="project-channel-list" :class="{ 'project-channel-list--expanded': isProjectGoalsExpanded(project.id) }">
              <div v-for="channel in projectChannelSummaries(project)" :key="channel.code" class="project-channel-card">
                <div class="project-channel-row">
                  <span class="project-channel-icon" :class="`project-channel-icon--${channel.code}`">
                    <img :src="channel.icon" :alt="channel.name" />
                  </span>
                  <div class="project-channel-main">
                    <strong>{{ channel.name }}</strong>
                    <span>{{ channel.summaryText }}</span>
                  </div>
                  <div class="project-channel-spend">
                    <strong>{{ formatMoney(withVat(channel.expenses)) }}</strong>
                    <span>расход</span>
                  </div>
                </div>
                <div v-if="isProjectGoalsExpanded(project.id)" class="project-goal-detail-list">
                  <div v-for="goal in channel.goals" :key="goal.id || goal.name" class="project-goal-detail-row">
                    <span>{{ goal.name }}</span>
                    <strong>{{ formatNumber(goal.count) }} шт</strong>
                    <b>{{ formatGoalCpl(goal) }}</b>
                    <em v-if="goal.hasCost" :class="goalTrendClass(goal.trend)">{{ trendTextFromValue(goal.trend) }}</em>
                  </div>
                  <div v-if="!channel.goals.length" class="project-goal-empty">Цели за период не найдены</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="project-tile-footer">
          <div class="project-balance-area">
            <div class="project-balance-title">Баланс в кабинетах</div>
            <div class="project-balance-strip">
              <div
                v-for="balance in projectBalances(project)"
                :key="balance.code"
                class="balance-chip"
                :class="`balance-chip--${balance.code}`"
              >
                <img :src="balance.icon" :alt="balance.name" />
                <span>{{ balance.name }}</span>
                <strong>{{ balance.value }}</strong>
              </div>
            </div>
          </div>
          <div class="project-footer-actions">
            <button type="button" class="settings-btn" @click.stop="openSettings(project)">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z"/>
              </svg>
              Настройки
            </button>
            <button type="button" class="ai-audit-btn" @click.stop="openAiAudit(project)">
              <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                <path d="M8.5 1.6 9.8 5.1l3.5 1.3-3.5 1.3-1.3 3.5-1.3-3.5-3.5-1.3 3.5-1.3 1.3-3.5ZM3.4 9.9l.6 1.7 1.7.6-1.7.6-.6 1.7-.6-1.7-1.7-.6 1.7-.6.6-1.7Z"/>
              </svg>
              AI-аудит
            </button>
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

    <ProjectSettingsModal
      v-if="settingsProject"
      :project="settingsProject"
      @close="settingsProject = null"
      @saved="handleSettingsSaved"
      @avatar-saved="handleAvatarSaved"
      @deleted="handleProjectDeleted"
      @add-channel="handleSettingsAddChannel"
      @configure-channel="handleSettingsConfigureChannel"
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
import ProjectSettingsModal from '../../components/ProjectSettingsModal.vue'

const router = useRouter()
const toaster = useToaster()
const { projects, isLoading, fetchProjects, setCurrentProject } = useProjects()

const projectFilter = ref('all')
const periodKey = ref('last_7_days')
const customPeriodRange = ref({ start: null, end: null })
const search = ref('')
const openSelect = ref(null)
const metricsByProjectId = ref({})
const projectInsightsById = ref({})
const expandedGoalsByProjectId = ref({})
const periodTriggerRef = ref(null)
const periodPopoverRef = ref(null)
const periodOptions = projectPeriodOptions
const avatarProject = ref(null)
const settingsProject = ref(null)

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
const emptyProjectInsights = () => ({
  all: emptyMetric(),
  yandex: emptyMetric(),
  vk: emptyMetric(),
  goals: {
    yandex: [],
    vk: [],
  },
})
const getProjectInsights = (projectId) => projectInsightsById.value[projectId] || emptyProjectInsights()

const VAT_RATE = 1.22
const formatNumber = (num) => new Intl.NumberFormat('ru-RU').format(Number(num || 0))
const formatMoney = (num) => `${new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 2 }).format(Number(num || 0))} ₽`
const withVat = (num) => (Number(num) || 0) * VAT_RATE

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
    { key: 'impressions', label: 'Показы', value: formatNumber(metric.impressions) },
    { key: 'clicks', label: 'Клики', value: formatNumber(metric.clicks) },
    { key: 'expenses', label: 'Расход', value: formatMoney(withVat(metric.expenses)) },
    { key: 'cpc', label: 'CPC', value: formatMoney(withVat(metric.cpc)) },
  ].map((item) => ({ ...item, change: trendText(metric, item.key) }))
}

const platformConfig = {
  yandex: {
    code: 'yandex',
    short: 'Я',
    name: 'Яндекс Директ',
    balanceName: 'Yandex Direct',
    icon: '/admirra/img/icons/yandex-direct.png',
  },
  vk: {
    code: 'vk',
    short: 'ВК',
    name: 'VK Реклама',
    balanceName: 'VK Ads',
    icon: '/admirra/img/icons/vk-ads.png',
  },
}

const projectPlatformCards = (project) => {
  const cards = []
  if (hasPlatform(project, 'YANDEX') || !hasAnyPlatform(project)) cards.push(platformConfig.yandex)
  if (hasPlatform(project, 'VK')) cards.push(platformConfig.vk)
  return cards
}

const normalizeGoalRows = (goals = []) => goals.map((goal) => {
  const count = Number(goal.count || 0)
  const hasCost = goal.cost !== null && goal.cost !== undefined
  const cost = hasCost ? Number(goal.cost || 0) : null
  return {
    id: goal.id,
    name: goal.name || 'Цель',
    count,
    trend: Number(goal.trend || 0),
    hasCost,
    cost,
    cpl: hasCost && count > 0 ? cost / count : null,
  }
})

const topGoalSummary = (goals) => {
  const total = goals.reduce((sum, goal) => sum + Number(goal.count || 0), 0)
  if (!total) return 'нет целей за период'
  const cplValues = goals.map((goal) => Number(goal.cpl || 0)).filter(Boolean)
  if (!cplValues.length) return `${formatNumber(total)} заявок`
  const avgCpl = cplValues.reduce((sum, value) => sum + value, 0) / cplValues.length
  return `${formatNumber(total)} заявок · CPL ${formatMoney(withVat(avgCpl))}`
}

const formatGoalCpl = (goal) => goal.hasCost ? formatMoney(withVat(goal.cpl)) : '—'

const projectChannelSummaries = (project) => {
  const insights = getProjectInsights(project.id)
  return projectPlatformCards(project).map((platform) => {
    const metric = insights[platform.code] || emptyMetric()
    const goals = normalizeGoalRows(insights.goals?.[platform.code] || [])
    return {
      ...platform,
      expenses: Number(metric.expenses || 0),
      goals,
      summaryText: topGoalSummary(goals),
    }
  })
}

const projectBalances = (project) => {
  const insights = getProjectInsights(project.id)
  return projectPlatformCards(project).map((platform) => {
    const value = Number(insights[platform.code]?.balance || 0)
    return {
      ...platform,
      name: platform.balanceName,
      value: formatMoney(value),
    }
  })
}

const isProjectGoalsExpanded = (projectId) => Boolean(expandedGoalsByProjectId.value[projectId])

const toggleProjectGoals = (projectId) => {
  expandedGoalsByProjectId.value = {
    ...expandedGoalsByProjectId.value,
    [projectId]: !expandedGoalsByProjectId.value[projectId],
  }
}

const trendTextFromValue = (value) => {
  const trend = Number(value || 0)
  const sign = trend >= 0 ? '+' : ''
  return `${sign}${trend.toFixed(0)}%`
}

const goalTrendClass = (value) => {
  const trend = Number(value || 0)
  if (trend > 0) return 'project-goal-trend project-goal-trend--up'
  if (trend < 0) return 'project-goal-trend project-goal-trend--down'
  return 'project-goal-trend'
}

const openAiAudit = (project) => {
  setCurrentProject(project.id)
  toaster.info('AI-аудит будет доступен позже.')
}

const loadProjectMetrics = async () => {
  const { startDate, endDate } = getProjectPeriodRange(periodKey.value, customPeriodRange.value)

  const entries = await Promise.all(
    projects.value.map(async (project) => {
      try {
        const data = await loadProjectInsight(project.id, startDate, endDate)
        return [project.id, data]
      } catch {
        return [project.id, emptyProjectInsights()]
      }
    })
  )
  const insights = Object.fromEntries(entries)
  projectInsightsById.value = insights
  metricsByProjectId.value = Object.fromEntries(entries.map(([projectId, data]) => [projectId, data.all || emptyMetric()]))
}

const loadProjectInsight = async (projectId, startDate, endDate) => {
  const summaryParams = (platform) => ({
    client_id: projectId,
    platform,
    start_date: startDate,
    end_date: endDate,
  })
  const goalParams = (platform) => ({
    client_id: projectId,
    platform,
    date_from: startDate,
    date_to: endDate,
  })

  const [all, yandex, vk, yandexGoals, vkGoals] = await Promise.all([
    api.get('dashboard/summary', { params: summaryParams('all') }).then((res) => res.data || emptyMetric()).catch(() => emptyMetric()),
    api.get('dashboard/summary', { params: summaryParams('yandex') }).then((res) => res.data || emptyMetric()).catch(() => emptyMetric()),
    api.get('dashboard/summary', { params: summaryParams('vk') }).then((res) => res.data || emptyMetric()).catch(() => emptyMetric()),
    api.get('dashboard/goals', { params: goalParams('yandex') }).then((res) => res.data || []).catch(() => []),
    api.get('dashboard/goals', { params: goalParams('vk') }).then((res) => res.data || []).catch(() => []),
  ])

  return {
    all,
    yandex,
    vk,
    goals: {
      yandex: yandexGoals,
      vk: vkGoals,
    },
  }
}

const openProject = (project) => {
  setCurrentProject(project.id)
  router.push('/dashboard/general-3')
}

function openSettings(project) {
  settingsProject.value = project
}

function handleSettingsSaved(updatedProject) {
  updateProjectInList(updatedProject)
  settingsProject.value = null
}

function handleProjectDeleted(projectId) {
  projects.value = projects.value.filter((p) => p.id !== projectId)
  settingsProject.value = null
}

function handleSettingsAddChannel() {
  const projectId = settingsProject.value?.id
  settingsProject.value = null
  router.push({ path: '/integrations/wizard', query: projectId ? { client_id: projectId } : {} })
}

function handleSettingsConfigureChannel(channel) {
  settingsProject.value = null
  router.push({
    path: '/integrations/wizard',
    query: { resume_integration_id: channel.id, initial_step: 2 },
  })
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

.projects-tile-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1.7361rem;
  align-items: start;
}

.project-card--tile {
  display: flex;
  min-height: 34.7222rem;
  flex-direction: column;
  border: 1px solid rgba(15, 23, 42, 0.06);
  box-shadow: 0 0.1389rem 0.4167rem rgba(15, 23, 42, 0.03);
  overflow: visible;
}

.project-tile-main {
  display: flex;
  flex: 1;
  flex-direction: column;
  padding: 1.7361rem;
}

.project-tile-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.4583rem;
}

.project-tile-identity {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 1.1806rem;
}

.project-tile-title-block {
  min-width: 0;
}

.project-title-link--tile {
  display: block;
  color: #171717;
  font-size: 1.3889rem;
  font-weight: 700;
  line-height: 1.12;
  max-width: 18rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-tile-description {
  margin-top: 0.4167rem;
  max-width: 18rem;
  color: rgba(105, 105, 105, 0.66);
  font-size: 1.0417rem;
  line-height: 1.25;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-tile-id {
  display: inline-flex;
  max-width: 18rem;
  margin-top: 0.2778rem;
  padding: 0;
  border: 0;
  background: transparent;
  color: rgba(105, 105, 105, 0.48);
  cursor: pointer;
  font-size: 0.9028rem;
  font-weight: 500;
  line-height: 1.15;
  overflow: hidden;
  text-align: left;
  text-overflow: ellipsis;
  transition: color 0.2s;
  white-space: nowrap;
}

.project-tile-id:hover {
  color: #2563eb;
}

.project-tile-actions {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  flex-shrink: 0;
}

.project-platform-chips {
  display: flex;
  align-items: center;
  gap: 0.3472rem;
}

.project-platform-chip,
.project-channel-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.2222rem;
  height: 2.2222rem;
  border-radius: 0.5556rem;
  flex-shrink: 0;
}

.project-platform-chip img,
.project-channel-icon img {
  display: block;
  width: 1.3194rem;
  height: 1.3194rem;
  object-fit: contain;
}

.project-platform-chip--yandex,
.project-channel-icon--yandex {
  background: #fff2e4;
}

.project-platform-chip--vk,
.project-channel-icon--vk {
  background: #f0f7ff;
}

.project-tile-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.8333rem;
  margin-bottom: 1.25rem;
}

.stat-box__label {
  display: block;
  color: rgba(105, 105, 105, 0.76);
  font-size: 1.0417rem;
  line-height: 1.1;
}

.stat-box__value {
  display: block;
  margin-top: 0.3472rem;
  color: #171717;
  font-size: 1.5278rem;
  font-weight: 700;
  line-height: 1.1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-goals-section {
  margin-top: 0;
}

.project-goals-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.8333rem;
  width: 100%;
  margin-bottom: 0.6944rem;
  padding: 0;
  border: 0;
  background: transparent;
  color: rgba(105, 105, 105, 0.62);
  cursor: pointer;
  font-size: 0.8333rem;
  font-weight: 700;
  letter-spacing: 0;
  line-height: 1.1;
  text-transform: uppercase;
}

.project-goals-title__action {
  display: inline-flex;
  align-items: center;
  gap: 0.3472rem;
  min-height: 1.6667rem;
  padding: 0;
  border-radius: 0;
  background: transparent;
  color: rgba(105, 105, 105, 0.68);
  font-size: 0.7639rem;
  font-weight: 700;
  text-transform: none;
  white-space: nowrap;
  transition: background 0.2s, color 0.2s;
}

.project-goals-title:hover .project-goals-title__action {
  color: #2563eb;
}

.project-goals-title__icon {
  color: currentColor;
  transition: transform 0.2s;
}

.project-goals-title__icon--open {
  transform: rotate(180deg);
}

.project-channel-list {
  display: flex;
  flex-direction: column;
  gap: 0.5556rem;
}

.project-channel-card {
  border-radius: 0.6944rem;
  background: #f8fafb;
  overflow: visible;
}

.project-channel-row {
  display: grid;
  grid-template-columns: 2.2222rem minmax(0, 1fr) auto;
  align-items: center;
  gap: 0.8333rem;
  min-height: 3.75rem;
  padding: 0.6944rem 0.9722rem;
}

.project-channel-main {
  min-width: 0;
}

.project-channel-main strong,
.project-channel-main span {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-channel-main strong {
  color: #171717;
  font-size: 0.9722rem;
  font-weight: 700;
  line-height: 1.15;
}

.project-channel-main span {
  margin-top: 0.1389rem;
  color: rgba(105, 105, 105, 0.7);
  font-size: 0.8333rem;
  line-height: 1.15;
}

.project-channel-spend {
  min-width: 6.25rem;
  text-align: right;
}

.project-channel-spend strong,
.project-channel-spend span {
  display: block;
}

.project-channel-spend strong {
  color: #171717;
  font-size: 0.9722rem;
  font-weight: 700;
  line-height: 1.15;
}

.project-channel-spend span {
  margin-top: 0.1389rem;
  color: rgba(105, 105, 105, 0.5);
  font-size: 0.7639rem;
}

.project-goal-detail-list {
  padding: 0 0.9722rem 0.7639rem 4.0278rem;
}

.project-goal-detail-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 3.8194rem 4.8611rem 3.3333rem;
  align-items: center;
  gap: 0.625rem;
  min-height: 2.2222rem;
  border-top: 1px solid rgba(15, 23, 42, 0.06);
  color: #171717;
  font-size: 0.9028rem;
}

.project-goal-detail-row span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-goal-detail-row strong,
.project-goal-detail-row b {
  font-weight: 600;
  text-align: right;
  white-space: nowrap;
}

.project-goal-trend {
  display: inline-flex;
  justify-content: center;
  padding: 0.1389rem 0.4167rem;
  border-radius: 999px;
  background: rgba(105, 105, 105, 0.08);
  color: rgba(105, 105, 105, 0.72);
  font-style: normal;
  font-weight: 700;
  line-height: 1.1;
}

.project-goal-trend--up {
  background: rgba(239, 68, 68, 0.1);
  color: #dc2626;
}

.project-goal-trend--down {
  background: rgba(34, 197, 94, 0.12);
  color: #16a34a;
}

.project-goal-empty {
  padding: 0.625rem 0;
  border-top: 1px solid rgba(15, 23, 42, 0.06);
  color: rgba(105, 105, 105, 0.55);
  font-size: 0.7639rem;
}

.project-tile-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.8333rem;
  min-height: 6.1111rem;
  padding: 1.0417rem 1.7361rem 1.3889rem;
  border-top: 1px solid rgba(15, 23, 42, 0.06);
}

.project-balance-area,
.project-balance-strip,
.project-footer-actions {
  display: flex;
  min-width: 0;
}

.project-balance-area {
  flex: 1;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.4861rem;
}

.project-balance-title {
  color: rgba(105, 105, 105, 0.62);
  font-size: 0.8333rem;
  font-weight: 700;
  letter-spacing: 0;
  line-height: 1.1;
  text-transform: uppercase;
}

.project-balance-strip {
  align-items: center;
  gap: 0.5556rem;
  flex-wrap: wrap;
}

.project-footer-actions {
  align-items: flex-end;
  gap: 0.5556rem;
  padding-top: 1.5972rem;
}

.balance-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.4167rem;
  min-height: 2.2222rem;
  max-width: 100%;
  padding: 0.3472rem 0.6944rem;
  border-radius: 0.8333rem;
  font-size: 0.9028rem;
  white-space: nowrap;
}

.balance-chip--yandex {
  background: #fff2e4;
  color: #71663e;
}

.balance-chip--vk {
  background: #f0f7ff;
  color: #254b78;
}

.balance-chip img {
  display: block;
  width: 1.25rem;
  height: 1.25rem;
  object-fit: contain;
  flex-shrink: 0;
}

.balance-chip span {
  flex-shrink: 0;
  font-weight: 500;
}

.balance-chip strong {
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
  min-height: 1.5278rem;
  padding: 0 0.5556rem;
  border-radius: 6.9444rem;
  background: #fff;
  font-size: 0.8333rem;
  font-weight: 600;
}

.ai-audit-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.3472rem;
  min-height: 2.0833rem;
  padding: 0 0.8333rem;
  border-radius: 0.5556rem;
  border: 1px solid rgba(37, 99, 235, 0.18);
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.08), rgba(6, 181, 212, 0.08));
  color: #2563eb;
  cursor: pointer;
  font-size: 0.9028rem;
  font-weight: 700;
  white-space: nowrap;
  transition: background 0.2s, border-color 0.2s;
}

.ai-audit-btn:hover {
  border-color: rgba(37, 99, 235, 0.34);
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.13), rgba(6, 181, 212, 0.13));
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
  width: 3.0556rem;
  height: 3.0556rem;
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

/* ---- Analytics open button ---- */
.analytics-open-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.4167rem;
  min-height: 2.0833rem;
  padding: 0 0.8333rem;
  border-radius: 0.5556rem;
  border: 1px solid rgba(169, 169, 169, 0.35);
  background: #fff;
  cursor: pointer;
  color: #696969;
  font-size: 0.8333rem;
  font-weight: 600;
  line-height: 1;
  white-space: nowrap;
  transition: border-color 0.25s, color 0.25s, background 0.25s, box-shadow 0.25s;
}

.analytics-open-btn:hover {
  border-color: rgba(37, 99, 235, 0.28);
  background: rgba(37, 99, 235, 0.04);
  color: #2563eb;
  box-shadow: 0 0.3472rem 1.0417rem rgba(37, 99, 235, 0.08);
}

/* ---- Stat box ---- */
.stat-box {
  display: flex;
  flex-direction: column;
  min-height: 4.8611rem;
  padding: 0.6944rem 0.9722rem;
  background-color: #f8fafb;
  border-radius: 0.5556rem;
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
  align-self: flex-end;
  margin-top: auto;
  padding: 0.1389rem 0.4167rem;
  font-size: 0.8333rem;
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

/* ---- Settings button ---- */
.settings-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.4167rem;
  min-height: 2.0833rem;
  padding: 0 0.8333rem;
  font-size: 0.9028rem;
  font-weight: 500;
  color: rgba(105, 105, 105, 0.86);
  background: #fff;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 0.5556rem;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s;
  white-space: nowrap;
}
.settings-btn:hover { background: #f8fafb; border-color: rgba(37, 99, 235, 0.2); color: #2563eb; }
.settings-btn svg { flex-shrink: 0; }

@media (max-width: 88rem) {
  .projects-tile-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 42rem) {
  .project-card--tile {
    min-height: auto;
  }

  .project-tile-main,
  .project-tile-footer {
    padding-left: 1.1111rem;
    padding-right: 1.1111rem;
  }

  .project-tile-header,
  .project-tile-footer {
    align-items: flex-start;
    flex-direction: column;
  }

  .project-tile-stats {
    grid-template-columns: 1fr;
  }

  .project-channel-row {
    grid-template-columns: 2.0833rem minmax(0, 1fr);
  }

  .project-channel-spend {
    grid-column: 2;
    min-width: 0;
    text-align: left;
  }

  .project-goal-detail-row {
    grid-template-columns: minmax(0, 1fr) 3.6111rem 4.4444rem;
  }

  .project-goal-detail-row em {
    display: none;
  }
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
:global(.dark) .analytics-open-btn,
:global(.darkmode) .analytics-open-btn {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.18);
  color: rgba(255, 255, 255, 0.68);
}

:global(.dark) .analytics-open-btn:hover,
:global(.darkmode) .analytics-open-btn:hover {
  border-color: rgba(103, 168, 255, 0.32);
  background: rgba(103, 168, 255, 0.1);
  color: #67a8ff;
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

:global(.dark) .project-title-link--tile,
:global(.darkmode) .project-title-link--tile,
:global(.dark) .project-channel-main strong,
:global(.darkmode) .project-channel-main strong,
:global(.dark) .project-channel-spend strong,
:global(.darkmode) .project-channel-spend strong,
:global(.dark) .project-goal-detail-row,
:global(.darkmode) .project-goal-detail-row {
  color: rgba(255, 255, 255, 0.9);
}

:global(.dark) .project-goals-title,
:global(.darkmode) .project-goals-title,
:global(.dark) .project-balance-title,
:global(.darkmode) .project-balance-title,
:global(.dark) .project-channel-main span,
:global(.darkmode) .project-channel-main span,
:global(.dark) .project-channel-spend span,
:global(.darkmode) .project-channel-spend span,
:global(.dark) .project-goal-empty,
:global(.darkmode) .project-goal-empty {
  color: rgba(255, 255, 255, 0.52);
}

:global(.dark) .project-goals-title__action,
:global(.darkmode) .project-goals-title__action {
  background: transparent;
  color: rgba(255, 255, 255, 0.58);
}

:global(.dark) .project-goals-title:hover .project-goals-title__action,
:global(.darkmode) .project-goals-title:hover .project-goals-title__action {
  color: #67a8ff;
}

:global(.dark) .project-channel-card,
:global(.darkmode) .project-channel-card {
  background: rgba(255, 255, 255, 0.05);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.07);
}

:global(.dark) .project-tile-footer,
:global(.darkmode) .project-tile-footer,
:global(.dark) .project-goal-detail-row,
:global(.darkmode) .project-goal-detail-row,
:global(.dark) .project-goal-empty,
:global(.darkmode) .project-goal-empty {
  border-color: rgba(255, 255, 255, 0.08);
}

:global(.dark) .balance-chip--yandex,
:global(.darkmode) .balance-chip--yandex {
  background: #3a3128;
  color: #f0d99a;
}

:global(.dark) .balance-chip--vk,
:global(.darkmode) .balance-chip--vk {
  background: #213652;
  color: #8bb7ff;
}

:global(.dark) .balance-chip strong,
:global(.darkmode) .balance-chip strong {
  background: rgba(255, 255, 255, 0.1);
}

:global(.dark) .settings-btn,
:global(.darkmode) .settings-btn {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.72);
}

:global(.dark) .settings-btn:hover,
:global(.darkmode) .settings-btn:hover {
  border-color: rgba(103, 168, 255, 0.32);
  color: #67a8ff;
}
</style>
