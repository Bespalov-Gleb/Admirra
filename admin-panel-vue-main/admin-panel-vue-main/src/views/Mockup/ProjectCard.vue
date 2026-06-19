<template>
  <div class="relative z-[2] flex min-h-full flex-col overflow-visible px-[1.7361rem] py-[2.0833rem]">

    <!-- Heading -->
    <div class="pt-[1.0417rem] pb-[1.0417rem] mb-[0.6944rem]">
      <h3 class="text-[2.0833rem] font-semibold leading-none text-[#171717] dark:text-white">Проекты</h3>
    </div>

    <!-- Filters bar -->
    <div class="filters-bar">
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
      <div class="flex items-center gap-[1.1rem]">
        <label class="tile-nds-check-wrap">
          <input type="checkbox" v-model="includeVat" class="tile-nds-checkbox" />
          <span class="tile-nds-label">С НДС 22%</span>
        </label>

        <div class="project-sync-meta" v-if="projectSyncStatusText">{{ projectSyncStatusText }}</div>

        <button class="tile-sync-btn" type="button" :disabled="projectsSyncing" @click="handleSyncProjects">
          <svg :class="{ spinning: projectsSyncing }" width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M20 11a8.1 8.1 0 0 0-15.5-2M4 5v4h4M4 13a8.1 8.1 0 0 0 15.5 2M20 19v-4h-4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          {{ projectsSyncing ? 'Синхронизация...' : 'Синхронизировать' }}
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
      <div v-for="project in filteredProjects" :key="project.id" class="project-card project-card--tile bg-white rounded-[1.0417rem]" :class="{ 'project-card--syncing': isProjectSyncing(project) }">
        <div v-if="isProjectSyncing(project)" class="project-sync-overlay">
          <div class="project-sync-overlay__spinner"></div>
          <strong>Выполняется синхронизация</strong>
          <span>Пожалуйста, подождите. Данные обновятся автоматически.</span>
        </div>

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
              </div>
            </div>
            <div class="project-tile-actions">
              <div class="project-tile-actions__top">
                <span
                  v-if="detectorBadge(project)"
                  class="detector-badge"
                  :class="`detector-badge--${detectorBadge(project).type}`"
                  :title="detectorBadge(project).text"
                >
                  <svg v-if="detectorBadge(project).type === 'warmup'" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
                  <template v-else>{{ detectorBadge(project).count }}</template>
                </span>
                <button class="analytics-open-btn flex-shrink-0" @click="openProject(project)" title="Открыть аналитику">
                  <span>Аналитика</span>
                  <svg width="7" height="7" viewBox="0 0 13 13" fill="none">
                    <path d="M1 12L12 1M12 1H4.5M12 1V8.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                </button>
              </div>
              <button type="button" class="project-tile-id project-tile-id--corner" @click.stop="copyProjectId(project)" title="Копировать ID">
                <span>ID {{ projectSupportId(project) }}</span>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                  <rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                </svg>
              </button>
            </div>
          </div>

          <div class="project-tile-stats-wrap">
            <div v-if="isProjectWarmingUp(project)" class="project-warmup-pill">накопление данных</div>
            <div class="project-tile-stats">
              <div v-for="stat in projectStats(project)" :key="stat.label" class="stat-box">
                <div class="iconbox flex-shrink-0">
                  <svg width="12" height="12" fill="#2563eb" aria-hidden="true">
                    <use :href="stat.icon" />
                  </svg>
                </div>
                <div class="stat-box__copy">
                  <h4>{{ stat.label }}</h4>
                  <p>{{ stat.subtitle }}</p>
                </div>
                <b class="stat-box__value">{{ stat.value }}</b>
                <span :class="trendBadgeClass(getProjectMetric(project.id), stat.key)">
                  <svg :class="trendArrowClass(getProjectMetric(project.id), stat.key)" width="8" height="7" viewBox="0 0 12 9" fill="none" aria-hidden="true">
                    <path d="M1 8L6 2L11 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                  {{ stat.change }}
                </span>
              </div>
            </div>
          </div>

          <div class="project-goals-section">
            <div class="project-goals-title">
              <span class="project-goals-title__label">
                Целевые действия по каналам
                <button
                  type="button"
                  class="project-goals-info"
                  data-tooltip="Стоимость по каждой цели не показывается: расход кампании невозможно честно разделить между разными целевыми действиями одной сессии. Для Яндекса показан сводный CPL по всем конверсиям. Для ВК сводного CPL нет — типы кампаний разнородны."
                  aria-label="Пояснение по стоимости целей"
                  @click.stop
                >i</button>
              </span>
              <button type="button" class="project-goals-title__action" @click="toggleProjectGoals(project.id)">
                {{ isProjectGoalsExpanded(project.id) ? 'Свернуть' : 'Развернуть' }}
                <svg :class="{ 'project-goals-title__icon--open': isProjectGoalsExpanded(project.id) }" class="project-goals-title__icon" width="11" height="7" viewBox="0 0 12 8" fill="none">
                <path d="M1 1.5 6 6.5 11 1.5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              </button>
            </div>

            <div
              v-if="projectChannelSummaries(project).length"
              class="project-channel-list"
              :class="{ 'project-channel-list--expanded': isProjectGoalsExpanded(project.id) }"
            >
              <div v-for="channel in projectChannelSummaries(project)" :key="channel.code" class="project-channel-card">
                <div class="project-channel-row">
                  <span class="project-channel-icon" :class="`project-channel-icon--${channel.code}`">
                    <img :src="channel.icon" :alt="channel.name" />
                  </span>
                  <div class="project-channel-main">
                    <strong>{{ channel.name }}</strong>
                  </div>
                  <div class="project-channel-metrics">
                    <div class="project-channel-metric">
                      <strong>{{ formatNumber(channel.goalTotal) }}</strong>
                      <span>{{ capitalizeFirst(channel.goalNoun) }}</span>
                    </div>
                    <div class="project-channel-metric project-channel-metric--cpl">
                      <strong>{{ channel.avgCpl !== null ? formatMoney(withChannelVat(channel.avgCpl, channel.code)) : '—' }}</strong>
                      <span>Общий CPL</span>
                    </div>
                    <div class="project-channel-metric project-channel-metric--spend">
                      <strong>{{ formatMoney(withChannelVat(channel.expenses, channel.code)) }}</strong>
                      <span>Расход</span>
                    </div>
                  </div>
                </div>
                <div v-if="isProjectGoalsExpanded(project.id)" class="project-goal-detail-list">
                  <div
                    v-for="goal in channel.goals"
                    :key="goal.id || goal.name"
                    class="project-goal-detail-row"
                    :class="{ 'project-goal-detail-row--simple': channel.code === 'yandex' }"
                  >
                    <span>{{ goal.name }}</span>
                    <strong>{{ formatNumber(goal.count) }} шт</strong>
                    <template v-if="channel.code !== 'yandex'">
                      <b>{{ formatGoalCpl(goal, channel.code) }}</b>
                      <em v-if="goal.hasCost" :class="goalTrendClass(goal.trend)">{{ trendTextFromValue(goal.trend) }}</em>
                    </template>
                  </div>
                  <div v-if="!channel.goals.length" class="project-goal-empty">Цели за период не найдены</div>
                </div>
              </div>
            </div>
            <div v-else class="project-channel-empty">
              <div class="project-channel-empty__icon">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M10 13a5 5 0 0 0 7.54.54l2.2-2.2a5 5 0 0 0-7.07-7.07l-.95.95" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
                  <path d="M14 11a5 5 0 0 0-7.54-.54l-2.2 2.2a5 5 0 0 0 7.07 7.07l.95-.95" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </div>
              <div class="project-channel-empty__copy">
                <strong>Каналы не подключены</strong>
                <span>Подключите Яндекс Директ или VK Рекламу, чтобы увидеть цели, CPL и расходы.</span>
              </div>
              <button type="button" class="project-channel-empty__btn" @click.stop="openSettings(project)">Настроить</button>
            </div>
          </div>
        </div>

        <div class="project-tile-footer">
          <div class="project-balance-area">
            <div class="project-balance-title">Баланс в кабинетах</div>
            <div v-if="projectBalances(project).length" class="project-balance-strip">
              <div
                v-for="balance in projectBalances(project)"
                :key="balance.code"
                class="balance-chip"
                :class="`balance-chip--${balance.code}`"
              >
                <img :src="balance.icon" :alt="balance.name" />
                <strong>{{ balance.value }}</strong>
              </div>
            </div>
            <div v-else class="project-balance-empty">Нет подключённых кабинетов</div>
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
import { hasActiveProjectIntegration, hasProjectPlatform } from '../../utils/projectIntegrations'
import { getProjectPeriodLabel, getProjectPeriodRange, projectPeriodOptions } from '../../utils/projectPeriods'
import { projectAvatarUrl, projectInitials } from '../../utils/projectAvatar'
import DateRangePicker from '../../components/ui/DateRangePicker.vue'
import ProjectAvatarUploadModal from '../../components/ProjectAvatarUploadModal.vue'
import ProjectSettingsModal from '../../components/ProjectSettingsModal.vue'
import { useDetectorCrossProject } from '../../composables/useDetector'
import { useSyncStatus } from '../../composables/useSyncStatus'

const router = useRouter()
const toaster = useToaster()
const { projects, isLoading, fetchProjects, setCurrentProject } = useProjects()
const { fetchCrossProject, getProjectStatus } = useDetectorCrossProject()
const {
  syncingIntegrations: globalSyncingIntegrations,
  isSyncingForProject,
  startIntegrationSync,
  waitForSyncJobs,
  fetchSyncStatus,
} = useSyncStatus()

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
const includeVat = ref(true)
const syncingIntegrations = ref(false)
const projectsSyncing = computed(() => syncingIntegrations.value || globalSyncingIntegrations.value.length > 0)

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
  if (q) {
    list = list.filter((p) =>
      p.name?.toLowerCase().includes(q) ||
      String(p.display_id || '').toLowerCase().includes(q) ||
      String(p.id || '').toLowerCase().includes(q) ||
      p.description?.toLowerCase().includes(q)
    )
  }
  return [...list].sort((a, b) => (a.name || '').localeCompare(b.name || '', 'ru'))
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

const formatMoscowSyncDate = (value) => {
  if (!value) return ''
  const date = new Date(value)
  if (!Number.isFinite(date.getTime())) return ''
  return date.toLocaleString('ru-RU', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'Europe/Moscow'
  }).replace('.', '')
}

const lastProjectSyncAt = computed(() => {
  const timestamps = projects.value
    .flatMap((project) => project.integrations || [])
    .map((integration) => Date.parse(integration.last_sync_at || ''))
    .filter(Number.isFinite)
  return timestamps.length ? Math.max(...timestamps) : null
})

// Источник самой свежей синхронизации (auto | manual | null) для индикатора
const lastProjectSyncTrigger = computed(() => {
  let latest = null
  let trigger = null
  for (const project of projects.value) {
    for (const integration of project.integrations || []) {
      const ts = Date.parse(integration.last_sync_at || '')
      if (Number.isFinite(ts) && (latest === null || ts > latest)) {
        latest = ts
        trigger = integration.last_sync_trigger || null
      }
    }
  }
  return trigger
})

const projectSyncStatusText = computed(() => {
  if (projectsSyncing.value) return 'Выполняется синхронизация, пожалуйста подождите'
  const formatted = formatMoscowSyncDate(lastProjectSyncAt.value)
  if (!formatted) return ''
  const suffix = lastProjectSyncTrigger.value === 'auto' ? ' · авто' : ''
  return `Последняя синхронизация: ${formatted} МСК${suffix}`
})

const isProjectSyncing = (project) => syncingIntegrations.value || isSyncingForProject(project.id)

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
const withVat = (num) => (Number(num) || 0) * (includeVat.value ? VAT_RATE : 1)
const channelHasVatIncluded = (platformCode) => String(platformCode || '').toLowerCase() === 'avito'
const withChannelVat = (num, platformCode) => {
  const value = Number(num) || 0
  if (channelHasVatIncluded(platformCode)) {
    // Авито: из API уже с НДС → «с НДС» как есть, «без НДС» вычитаем налог
    return includeVat.value ? value : value / VAT_RATE
  }
  return includeVat.value ? value * VAT_RATE : value
}
const withCostBreakdownVat = (num, costByPlatform) => {
  if (!costByPlatform || typeof costByPlatform !== 'object') return Number(num || 0)
  const yandex = Number(costByPlatform.yandex || 0)
  const vk = Number(costByPlatform.vk || 0)
  const avito = Number(costByPlatform.avito || 0)
  if (includeVat.value) {
    return (yandex * VAT_RATE) + (vk * VAT_RATE) + avito
  }
  // «без НДС»: Яндекс/VK как есть, у Авито вычитаем НДС
  return yandex + vk + (avito / VAT_RATE)
}

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
const isAvitoOnlyProject = (project) =>
  hasPlatform(project, 'AVITO') && !hasPlatform(project, 'YANDEX') && !hasPlatform(project, 'VK')

const projectStats = (project) => {
  const metric = getProjectMetric(project.id)
  const withProjectVat = (value) => (isAvitoOnlyProject(project) ? withChannelVat(value, 'avito') : withVat(value))
  const platforms = projectPlatformCards(project)
  const insights = getProjectInsights(project.id)
  const adjustedExpenses = metric.cost_by_platform
    ? withCostBreakdownVat(metric.expenses, metric.cost_by_platform)
    : platforms.length
      ? platforms.reduce((sum, platform) => sum + withChannelVat(insights[platform.code]?.expenses || 0, platform.code), 0)
      : withProjectVat(metric.expenses)
  const adjustedClicks = platforms.length
    ? platforms.reduce((sum, platform) => sum + Number(insights[platform.code]?.clicks || 0), 0)
    : Number(metric.clicks || 0)
  const adjustedCpc = adjustedClicks > 0 ? adjustedExpenses / adjustedClicks : withProjectVat(metric.cpc)
  return [
    { key: 'impressions', label: 'Показы', subtitle: 'По всем каналам', value: formatNumber(metric.impressions), icon: '/admirra/img/svg/sprite.svg#diagrama' },
    { key: 'clicks', label: 'Клики', subtitle: 'Все переходы', value: formatNumber(metric.clicks), icon: '/admirra/img/svg/sprite.svg#cursore' },
    { key: 'cpc', label: 'CPC', subtitle: 'Стоимость клика', value: formatMoney(adjustedCpc), icon: '/admirra/img/svg/sprite.svg#diagrama-circle' },
    { key: 'expenses', label: 'Расходы', subtitle: 'За период', value: formatMoney(adjustedExpenses), icon: '/admirra/img/svg/sprite.svg#wallet' },
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
  avito: {
    code: 'avito',
    short: 'A',
    name: 'Avito Ads',
    balanceName: 'Avito Ads',
    icon: '/admirra/img/icons/avito.svg',
  },
}

const projectPlatformCards = (project) => {
  const cards = []
  if (hasPlatform(project, 'YANDEX')) cards.push(platformConfig.yandex)
  if (hasPlatform(project, 'VK')) cards.push(platformConfig.vk)
  if (hasPlatform(project, 'AVITO')) cards.push(platformConfig.avito)
  return cards
}

const normalizeGoalRows = (goals = []) => goals
  .map((goal) => {
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
      syncing: Boolean(goal.syncing),
      missingInMetrika: Boolean(goal.missing_in_metrika),
    }
  })

const goalNoun = (count) => {
  const value = Math.abs(Number(count || 0))
  const lastTwo = value % 100
  const last = value % 10
  if (lastTwo >= 11 && lastTwo <= 14) return 'заявок'
  if (last === 1) return 'заявка'
  if (last >= 2 && last <= 4) return 'заявки'
  return 'заявок'
}

const capitalizeFirst = (value) => {
  const text = String(value || '')
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : ''
}

const topGoalSummary = (goals, platformCode, expenses) => {
  if (goals.some((goal) => goal.syncing)) {
    return {
      total: 0,
      noun: 'заявок',
      avgCpl: null,
      text: 'цели синхронизируются',
    }
  }
  const total = goals.reduce((sum, goal) => sum + Number(goal.count || 0), 0)
  const noun = goalNoun(total)
  const avgCpl = ['yandex', 'avito'].includes(platformCode) && total > 0 ? Number(expenses || 0) / total : null
  if (!total) {
    return {
      total: 0,
      noun,
      avgCpl,
      text: 'нет целей за период',
    }
  }
  if (!avgCpl) {
    return {
      total,
      noun,
      avgCpl,
      text: `${formatNumber(total)} ${noun}`,
    }
  }
  return {
    total,
    noun,
    avgCpl,
    text: `${formatNumber(total)} ${noun} · CPL ${formatMoney(withChannelVat(avgCpl, platformCode))}`,
  }
}

const formatGoalCpl = (goal, platformCode) => goal.hasCost ? formatMoney(withChannelVat(goal.cpl, platformCode)) : '—'

const projectChannelSummaries = (project) => {
  const insights = getProjectInsights(project.id)
  return projectPlatformCards(project).map((platform) => {
    const metric = insights[platform.code] || emptyMetric()
    const goals = normalizeGoalRows(insights.goals?.[platform.code] || [])
    const summary = topGoalSummary(goals, platform.code, metric.expenses)
    return {
      ...platform,
      expenses: Number(metric.expenses || 0),
      goals,
      goalTotal: summary.total,
      goalNoun: summary.noun,
      avgCpl: summary.avgCpl,
      summaryText: summary.text,
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
      value: formatMoney(withChannelVat(value, platform.code)),
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

  const [all, yandex, vk, avito, yandexGoals, vkGoals, avitoGoals] = await Promise.all([
    api.get('dashboard/summary', { params: summaryParams('all') }).then((res) => res.data || emptyMetric()).catch(() => emptyMetric()),
    api.get('dashboard/summary', { params: summaryParams('yandex') }).then((res) => res.data || emptyMetric()).catch(() => emptyMetric()),
    api.get('dashboard/summary', { params: summaryParams('vk') }).then((res) => res.data || emptyMetric()).catch(() => emptyMetric()),
    api.get('dashboard/summary', { params: summaryParams('avito') }).then((res) => res.data || emptyMetric()).catch(() => emptyMetric()),
    api.get('dashboard/goals', { params: goalParams('yandex') }).then((res) => res.data || []).catch(() => []),
    api.get('dashboard/goals', { params: goalParams('vk') }).then((res) => res.data || []).catch(() => []),
    api.get('dashboard/goals', { params: goalParams('avito') }).then((res) => res.data || []).catch(() => []),
  ])

  return {
    all,
    yandex,
    vk,
    avito,
    goals: {
      yandex: yandexGoals,
      vk: vkGoals,
      avito: avitoGoals,
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

const handleSyncProjects = async () => {
  if (syncingIntegrations.value) return

  const integrations = projects.value.flatMap((project) => project.integrations || [])
  const uniqueIntegrations = Array.from(
    new Map(integrations.filter((integration) => integration?.id).map((integration) => [integration.id, integration])).values()
  )

  if (!uniqueIntegrations.length) {
    toaster.info('Нет подключённых каналов для синхронизации.')
    return
  }

  syncingIntegrations.value = true
  try {
    const results = await Promise.allSettled(uniqueIntegrations.map((integration) => startIntegrationSync(integration.id, { days: 90, forceFull: false })))
    const jobIds = results
      .filter((result) => result.status === 'fulfilled')
      .map((result) => result.value?.job_id)
      .filter(Boolean)
    if (!jobIds.length) throw new Error('Не удалось запустить синхронизацию.')
    toaster.info(`Синхронизация запущена для ${jobIds.length} ${jobIds.length === 1 ? 'канала' : 'каналов'}.`)
    await Promise.all([fetchProjects(), fetchSyncStatus()])
    const result = await waitForSyncJobs(jobIds)
    await Promise.all([fetchProjects(), loadProjectMetrics(), fetchCrossProject(), fetchSyncStatus()])
    if (result.failed?.length) toaster.warning(`Синхронизация завершена с ошибками: ${result.failed.length}`)
    else toaster.success('Синхронизация завершена. Данные обновлены.')
  } catch (err) {
    console.error(err)
    toaster.error(err.response?.data?.detail || err.message || 'Не удалось запустить синхронизацию.')
  } finally {
    syncingIntegrations.value = false
  }
}

const detectorBadge = (project) => {
  const status = getProjectStatus(project.id)
  if (!status) return null
  if (status.warmup_status === 'warming_up') return { type: 'warmup', text: 'Детектор накапливает данные' }
  const total = (status.warning_count || 0) + (status.problem_count || 0)
  if (!total) return null
  return {
    type: status.max_severity || 'warning',
    text: `${total} ${total === 1 ? 'отклонение' : total < 5 ? 'отклонения' : 'отклонений'}`,
    count: total,
  }
}

const isProjectWarmingUp = (project) => detectorBadge(project)?.type === 'warmup'

onMounted(async () => {
  await fetchProjects()
  await Promise.all([loadProjectMetrics(), fetchCrossProject()])
})
</script>

<style scoped>
/* ---- Filters bar (sticky) ---- */
.filters-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.6944rem;
  margin-bottom: 1.4rem;
  position: sticky;
  top: 0;
  z-index: 20;
  background: rgba(245, 247, 249, 0.95);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  padding: 0.9rem 1.7361rem;
  margin-left: -1.7361rem;
  margin-right: -1.7361rem;
  border-bottom: 1px solid transparent;
  transition: border-color 0.15s;
}

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
.tile-nds-check-wrap,
.tile-sync-btn {
  display: inline-flex;
  align-items: center;
  min-height: 3.1944rem;
  border-radius: 1.0417rem;
  white-space: nowrap;
}

.tile-nds-check-wrap {
  gap: 0.5556rem;
  padding: 0.5556rem 0.2778rem;
  background: transparent;
  color: rgba(0, 0, 0, 0.58);
  cursor: pointer;
  font-size: 0.9028rem;
  font-weight: 600;
  user-select: none;
}

.tile-nds-checkbox {
  width: 1.0417rem;
  height: 1.0417rem;
  margin: 0;
  accent-color: #2563eb;
  cursor: pointer;
}

.tile-nds-label {
  line-height: 1;
}

.tile-sync-btn {
  gap: 0.4rem;
  padding: 0.5556rem 0.8rem;
  border: none;
  border-radius: 1.0417rem;
  background: transparent;
  color: rgba(105, 105, 105, 0.62);
  cursor: pointer;
  font-size: 0.9028rem;
  font-weight: 500;
  transition: background 0.2s, color 0.2s;
}

.tile-sync-btn:hover:not(:disabled) {
  background: rgba(37, 99, 235, 0.04);
  color: rgba(105, 105, 105, 0.82);
}

.tile-sync-btn:disabled {
  cursor: wait;
  opacity: 0.72;
}

.spinning {
  animation: tile-spin 0.9s linear infinite;
}

@keyframes tile-spin {
  to {
    transform: rotate(360deg);
  }
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
  position: relative;
}

.project-sync-meta {
  color: rgba(105, 105, 105, 0.72);
  font-size: 0.7639rem;
  font-weight: 600;
  white-space: nowrap;
}

.project-sync-overlay {
  position: absolute;
  inset: 0;
  z-index: 12;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 1.5rem;
  border-radius: inherit;
  background: rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(5px);
  text-align: center;
  color: #334155;
}
.project-sync-overlay strong {
  font-size: 0.9722rem;
  font-weight: 700;
}
.project-sync-overlay span {
  max-width: 22rem;
  font-size: 0.8333rem;
  color: rgba(51, 65, 85, 0.72);
}
.project-sync-overlay__spinner {
  width: 1.75rem;
  height: 1.75rem;
  border-radius: 999px;
  border: 3px solid rgba(37, 99, 235, 0.16);
  border-top-color: #2563eb;
  animation: tile-spin 0.8s linear infinite;
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
  flex-direction: column;
  align-items: flex-end;
  gap: 0.4167rem;
  flex-shrink: 0;
}

.project-tile-actions__top {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.625rem;
}

.project-tile-id--corner {
  align-items: center;
  justify-content: flex-end;
  gap: 0.3472rem;
  max-width: 12rem;
  margin-top: 0;
  font-size: 0.7639rem;
  text-align: right;
}

.project-tile-id--corner svg {
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

.project-tile-stats-wrap {
  position: relative;
  margin-bottom: 1.25rem;
}

.project-warmup-pill {
  position: absolute;
  top: -0.6944rem;
  left: 50%;
  z-index: 2;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 1.7361rem;
  padding: 0.2778rem 0.6944rem;
  border-radius: 999px;
  background: rgba(239, 246, 255, 0.96);
  color: #1d4ed8;
  font-size: 0.7639rem;
  font-weight: 800;
  line-height: 1;
  pointer-events: none;
  transform: translateX(-50%);
  white-space: nowrap;
  box-shadow: 0 0.4167rem 1.0417rem rgba(37, 99, 235, 0.14);
}

.project-tile-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.7639rem;
  margin-bottom: 0;
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
  cursor: default;
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
  border: 0;
  border-radius: 0;
  background: transparent;
  color: rgba(105, 105, 105, 0.68);
  cursor: pointer;
  font-size: 0.7639rem;
  font-weight: 700;
  text-transform: none;
  white-space: nowrap;
  transition: background 0.2s, color 0.2s;
}

.project-goals-title:hover .project-goals-title__action {
  color: #2563eb;
}

.project-goals-title__label {
  display: inline-flex;
  align-items: center;
  gap: 0.4167rem;
  min-width: 0;
}

.project-goals-info {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.0417rem;
  height: 1.0417rem;
  border-radius: 50%;
  background: rgba(37, 99, 235, 0.1);
  color: #2563eb;
  font-size: 0.625rem;
  font-weight: 800;
  line-height: 1;
  text-transform: none;
  border: 0;
  cursor: help;
}

.project-goals-info::before,
.project-goals-info::after {
  position: absolute;
  left: 50%;
  z-index: 30;
  opacity: 0;
  pointer-events: none;
  transform: translate(-50%, 0.4167rem);
  transition: opacity 0.16s ease, transform 0.16s ease;
}

.project-goals-info::before {
  top: calc(100% + 0.2778rem);
  width: 0.6944rem;
  height: 0.6944rem;
  background: #111827;
  content: "";
  transform: translate(-50%, 0.4167rem) rotate(45deg);
}

.project-goals-info::after {
  top: calc(100% + 0.5556rem);
  width: min(24rem, 72vw);
  padding: 0.6944rem 0.8333rem;
  border-radius: 0.6944rem;
  background: #111827;
  box-shadow: 0 0.8333rem 2.0833rem rgba(15, 23, 42, 0.18);
  color: #fff;
  content: attr(data-tooltip);
  font-size: 0.8333rem;
  font-weight: 500;
  line-height: 1.35;
  text-align: left;
  text-transform: none;
  white-space: normal;
}

.project-goals-info:hover::before,
.project-goals-info:hover::after,
.project-goals-info:focus-visible::before,
.project-goals-info:focus-visible::after {
  opacity: 1;
  transform: translate(-50%, 0) rotate(45deg);
}

.project-goals-info:hover::after,
.project-goals-info:focus-visible::after {
  transform: translate(-50%, 0);
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
  background: linear-gradient(90deg, rgba(255, 249, 232, 0.98) 0%, rgba(255, 243, 205, 0.98) 100%);
  overflow: hidden;
  box-shadow: inset 0 0 0 1px rgba(245, 158, 11, 0.18);
}

.project-channel-empty {
  display: grid;
  grid-template-columns: 2.2222rem minmax(0, 1fr) auto;
  align-items: center;
  gap: 0.8333rem;
  min-height: 4.5833rem;
  padding: 0.8333rem 0.9722rem;
  border: 1px dashed rgba(37, 99, 235, 0.18);
  border-radius: 0.6944rem;
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.055), rgba(6, 181, 212, 0.035));
}

.project-channel-empty__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.2222rem;
  height: 2.2222rem;
  border-radius: 0.5556rem;
  background: rgba(37, 99, 235, 0.09);
  color: #2563eb;
}

.project-channel-empty__copy {
  min-width: 0;
}

.project-channel-empty__copy strong,
.project-channel-empty__copy span {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-channel-empty__copy strong {
  color: #171717;
  font-size: 0.9722rem;
  font-weight: 800;
  line-height: 1.15;
}

.project-channel-empty__copy span {
  margin-top: 0.2083rem;
  color: rgba(105, 105, 105, 0.62);
  font-size: 0.7639rem;
  line-height: 1.2;
}

.project-channel-empty__btn {
  min-height: 2.0833rem;
  padding: 0.4167rem 0.7639rem;
  border: 0;
  border-radius: 0.5556rem;
  background: #fff;
  color: #2563eb;
  cursor: pointer;
  font-size: 0.7639rem;
  font-weight: 800;
  box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.14);
  transition: background 0.2s, color 0.2s;
}

.project-channel-empty__btn:hover {
  background: #eff6ff;
  color: #1d4ed8;
}

.project-channel-row {
  display: grid;
  grid-template-columns: 2.2222rem minmax(0, 0.85fr) minmax(19rem, 1fr);
  align-items: center;
  gap: 0.8333rem;
  min-height: 4.1667rem;
  padding: 0.7639rem 0.9722rem;
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

.project-channel-metrics {
  display: grid;
  grid-template-columns: minmax(4rem, 0.7fr) minmax(6.2rem, 1fr) minmax(6.2rem, 1fr);
  align-self: stretch;
  min-width: 0;
  overflow: hidden;
  border-left: 1px solid rgba(245, 158, 11, 0.14);
}

.project-channel-metric {
  display: flex;
  min-width: 0;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.2083rem;
  padding: 0.1389rem 0.4rem;
  border-left: 1px solid rgba(245, 158, 11, 0.14);
  text-align: center;
}

.project-channel-metric:first-child {
  border-left: 0;
}

.project-channel-metric strong {
  display: block;
  max-width: 100%;
  overflow: hidden;
  color: #171717;
  font-size: 1.1111rem;
  font-weight: 800;
  line-height: 1.05;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-channel-metric span {
  display: block;
  max-width: 100%;
  overflow: hidden;
  color: rgba(105, 105, 105, 0.5);
  font-size: 0.7639rem;
  font-weight: 600;
  line-height: 1.05;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-channel-metric--cpl {
  background: rgba(255, 255, 255, 0.18);
}

.project-channel-metric--cpl strong {
  color: #171717;
  font-size: 1.1111rem;
  font-weight: 800;
}

.project-channel-metric--cpl span {
  color: rgba(138, 90, 0, 0.7);
  font-weight: 600;
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

.project-goal-detail-row--simple {
  grid-template-columns: minmax(0, 1fr) 4.1667rem;
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

.project-balance-empty {
  color: rgba(105, 105, 105, 0.55);
  font-size: 0.8333rem;
  line-height: 1.2;
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

.balance-chip--avito {
  background: #ecfdf5;
  color: #047857;
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
  align-items: center;
  gap: 0.7rem;
  min-height: 4.6rem;
  padding: 0.7rem 1rem;
  background-color: #f8fafb;
  border-radius: 0.6944rem;
  line-height: 1.1;
}

.stat-box__copy {
  min-width: 0;
  flex-shrink: 1;
}

.stat-box__copy h4,
.stat-box__copy p {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.stat-box__copy h4 {
  margin: 0 0 0.15rem;
  color: #696969;
  font-size: 0.9028rem;
  font-weight: 600;
  line-height: 1.15;
}

.stat-box__copy p {
  margin: 0;
  color: rgba(105, 105, 105, 0.56);
  font-size: 0.7639rem;
  line-height: 1.15;
}

.stat-box__value {
  margin-left: auto;
  min-width: 0;
  overflow: hidden;
  color: #2c2c2c;
  font-size: 1.25rem;
  font-weight: 700;
  line-height: 1.1;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex-shrink: 0;
}

/* ---- Icon box ---- */
.iconbox {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.9444rem;
  height: 1.9444rem;
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
  padding: 0.1389rem 0.4167rem;
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
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-width: 0;
  gap: 0.4861rem;
  margin-top: auto;
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

.detector-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1.6667rem;
  height: 1.6667rem;
  padding: 0 0.4167rem;
  border-radius: 0.5556rem;
  font-size: 0.7639rem;
  font-weight: 700;
  flex-shrink: 0;
  white-space: nowrap;
}
.detector-badge--warning {
  background: #fef3c7;
  color: #92400e;
  border: 1px solid #fcd34d;
}
.detector-badge--problem {
  background: #fee2e2;
  color: #991b1b;
  border: 1px solid #fca5a5;
}
.detector-badge--warmup {
  background: #eff6ff;
  color: #1e40af;
  border: 1px solid #bfdbfe;
}

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

  .project-channel-metrics {
    grid-column: 2;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    min-width: 0;
    border-top: 1px solid rgba(245, 158, 11, 0.13);
    border-left: 0;
    padding-top: 0.5556rem;
  }

  .project-channel-metric:first-child {
    border-left: 0;
  }

  .project-goal-detail-row {
    grid-template-columns: minmax(0, 1fr) 3.6111rem 4.4444rem;
  }

  .project-goal-detail-row--simple {
    grid-template-columns: minmax(0, 1fr) 3.6111rem;
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
:global(.dark) .project-channel-metric strong,
:global(.darkmode) .project-channel-metric strong,
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
:global(.dark) .project-channel-metric span,
:global(.darkmode) .project-channel-metric span,
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

:global(.dark) .tile-nds-check-wrap,
:global(.darkmode) .tile-nds-check-wrap,
:global(.dark) .tile-sync-btn,
:global(.darkmode) .tile-sync-btn {
  background: transparent;
  box-shadow: none;
}

:global(.dark) .tile-nds-check-wrap,
:global(.darkmode) .tile-nds-check-wrap {
  color: rgba(255, 255, 255, 0.72);
}

:global(.dark) .tile-sync-btn,
:global(.darkmode) .tile-sync-btn {
  color: rgba(255, 255, 255, 0.45);
  background: transparent;
}

:global(.dark) .tile-sync-btn:hover:not(:disabled),
:global(.darkmode) .tile-sync-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.65);
}

:global(.dark) .filters-bar,
:global(.darkmode) .filters-bar {
  background: rgba(30, 32, 44, 0.92);
}

:global(.dark) .project-channel-metric--cpl,
:global(.darkmode) .project-channel-metric--cpl {
  background: rgba(251, 191, 36, 0.16);
}

:global(.dark) .project-channel-metric--cpl strong,
:global(.darkmode) .project-channel-metric--cpl strong,
:global(.dark) .project-channel-empty__copy strong,
:global(.darkmode) .project-channel-empty__copy strong {
  color: rgba(255, 255, 255, 0.92);
}

:global(.dark) .project-channel-empty,
:global(.darkmode) .project-channel-empty {
  border-color: rgba(103, 168, 255, 0.18);
  background: rgba(255, 255, 255, 0.05);
}

:global(.dark) .project-channel-empty__icon,
:global(.darkmode) .project-channel-empty__icon,
:global(.dark) .project-channel-empty__btn,
:global(.darkmode) .project-channel-empty__btn {
  background: rgba(103, 168, 255, 0.1);
  color: #67a8ff;
  box-shadow: inset 0 0 0 1px rgba(103, 168, 255, 0.14);
}

:global(.dark) .project-warmup-pill,
:global(.darkmode) .project-warmup-pill {
  background: rgba(37, 99, 235, 0.24);
  color: #bfdbfe;
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

:global(.dark) .balance-chip--avito,
:global(.darkmode) .balance-chip--avito {
  background: #183629;
  color: #7dd3a8;
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

:global(.dark) .detector-badge--warning,
:global(.darkmode) .detector-badge--warning {
  background: rgba(251, 191, 36, 0.12);
  border-color: rgba(251, 191, 36, 0.3);
  color: #fbbf24;
}
:global(.dark) .detector-badge--problem,
:global(.darkmode) .detector-badge--problem {
  background: rgba(239, 68, 68, 0.12);
  border-color: rgba(239, 68, 68, 0.3);
  color: #ef4444;
}
:global(.dark) .detector-badge--warmup,
:global(.darkmode) .detector-badge--warmup {
  background: rgba(59, 130, 246, 0.12);
  border-color: rgba(59, 130, 246, 0.3);
  color: #60a5fa;
}
</style>
