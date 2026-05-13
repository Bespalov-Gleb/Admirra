<template>
  <div class="figma-dashboard" :class="{ 'is-dark': isDarkMode }">
    <section class="top-grid">
      <div class="panel panel-channels">
        <h2>Подключенные каналы</h2>
        <div class="chips-row">
          <button
            v-for="channel in channels"
            :key="channel.name"
            class="chip"
            :class="{ active: selectedChannel === channel.name }"
            :style="{ backgroundColor: getChipBackground(channel) }"
            type="button"
            @click="selectConnectedChannel(channel)"
          >
            <span class="chip-dot" :style="{ background: channel.color }">
              <img
                v-if="channel.asset"
                :src="channel.asset"
                alt=""
                :class="['chip-img', channel.imageClass]"
              />
              <span v-else-if="channel.letter" class="chip-letter">{{ channel.letter }}</span>
              <component v-else :is="channel.icon" class="chip-icon" />
            </span>
            {{ channel.name }}
          </button>
        </div>
      </div>

      <div class="panel panel-reports">
        <div class="report-col report-main">
          <h2>Отчеты и уведомления</h2>
          <div class="chips-row report-icons-row">
            <button
              v-for="item in reportChannels"
              :key="item.name"
              class="report-icon-btn"
              :class="{ active: selectedReportChannel === item.name }"
              type="button"
              @click="selectedReportChannel = item.name"
            >
              <span class="report-icon-circle" :style="{ '--report-bg': getChipBackground(item) }">
                <span v-if="item.iconClass" :class="['report-mask-icon', item.iconClass]"></span>
                <img
                  v-else-if="item.asset"
                  :src="item.asset"
                  alt=""
                  :class="['chip-img', item.imageClass]"
                />
                <span v-else-if="item.letter" class="chip-letter">{{ item.letter }}</span>
                <component v-else :is="item.icon" class="chip-icon" />
              </span>
            </button>
          </div>
        </div>

        <div class="report-col report-template custom-select top-select" :class="{ open: openMenu === 'report-template' }" v-click-outside="() => closeMenu('report-template')">
          <h2>Шаблон отчета</h2>
          <button class="select-like cs-head" type="button" @click="toggleMenu('report-template')">
            <span class="cs-current">{{ selectedReportTemplate }}</span>
            <span class="cs-arrow">
              <ChevronDownIcon />
            </span>
          </button>
          <div class="cs-list">
            <button
              v-for="option in reportTemplateOptions"
              :key="option"
              type="button"
              class="cs-option"
              :class="{ selected: selectedReportTemplate === option }"
              @click="selectReportTemplate(option)"
            >{{ option }}</button>
          </div>
        </div>

        <div class="report-col report-schedule custom-select top-select" :class="{ open: openMenu === 'report-schedule' }" v-click-outside="() => closeMenu('report-schedule')">
          <p>График отправки</p>
          <button class="select-like cs-head" type="button" @click="toggleMenu('report-schedule')">
            <span class="cs-current">{{ selectedSchedule }}</span>
            <span class="cs-arrow">
              <ChevronDownIcon />
            </span>
          </button>
          <div class="cs-list schedule-menu" @click.stop>
            <div class="schedule-field-group">
              <span>День отправки</span>
              <div class="schedule-day-list" role="listbox" aria-label="День отправки">
                <button
                  v-for="option in scheduleDayOptions"
                  :key="option.value"
                  type="button"
                  class="schedule-day-option"
                  :class="{ selected: reportSchedule.day === option.value, 'schedule-day-option--wide': option.value === 'daily' }"
                  role="option"
                  :aria-selected="reportSchedule.day === option.value"
                  @click="setScheduleDay(option.value)"
                >
                  <span>{{ option.label }}</span>
                  <span class="schedule-day-check">
                    <CheckCircleIcon v-if="reportSchedule.day === option.value" />
                  </span>
                </button>
              </div>
            </div>
            <label class="schedule-field-group">
              <span>Время по МСК</span>
              <input
                :value="reportSchedule.time"
                class="schedule-field"
                type="text"
                inputmode="numeric"
                maxlength="5"
                placeholder="10:00"
                @input="updateScheduleTime"
              />
            </label>
            <div class="schedule-actions">
              <button type="button" class="schedule-secondary" @click="resetReportSchedule">Сбросить</button>
              <button type="button" class="schedule-primary" @click="saveReportSchedule">Сохранить</button>
            </div>
          </div>
        </div>

        <button class="primary-report" type="button" :disabled="sendingTg || sendingEmail" @click="handleSendSelectedReport">
          {{ sendingTg || sendingEmail ? 'Отправка...' : 'Отправить отчет сейчас' }}
          <CheckCircleIcon />
        </button>
      </div>
    </section>

    <section class="heading-section">
      <h1>{{ dashboardTitle }}</h1>
      <div class="filters-row">
        <div class="filter-wrap custom-select dashboard-select" :class="{ open: openMenu === 'channels' }" v-click-outside="() => closeMenu('channels')">
          <button class="filter-btn cs-head" type="button" @click="toggleMenu('channels')">
            <span class="cs-current">{{ selectedFilterChannelLabel }}</span>
            <span class="cs-arrow">
              <ChevronDownIcon />
            </span>
          </button>
          <div class="cs-list dropdown-panel small">
            <button
              v-for="channel in filterChannels"
              :key="channel.name"
              type="button"
              class="cs-option"
              :class="{ selected: filters.channel === channel.value }"
              @click="selectFilterChannel(channel)"
            >
              <span class="chip-dot" :style="{ background: channel.color }">
                <img
                  v-if="channel.asset"
                  :src="channel.asset"
                  alt=""
                  :class="['chip-img', channel.imageClass]"
                />
                <component v-else :is="channel.icon" class="chip-icon" />
              </span>
              {{ channel.name }}
            </button>
          </div>
        </div>

        <div class="filter-wrap custom-select dashboard-select" :class="{ open: openMenu === 'campaigns' }" v-click-outside="() => closeMenu('campaigns')">
          <button class="filter-btn cs-head" type="button" @click="toggleMenu('campaigns')">
            <span class="cs-current">{{ selectedCampaignLabel }}</span>
            <span class="cs-arrow">
              <ChevronDownIcon />
            </span>
          </button>
          <div class="cs-list dropdown-panel campaigns" @click.stop>
            <label class="search-box">
              <MagnifyingGlassIcon />
              <input v-model="campaignQuery" type="search" placeholder="Поиск кампании" />
            </label>
            <button
              v-for="campaign in filteredCampaigns"
              :key="campaign.id || campaign.name"
              type="button"
              class="cs-option"
              :class="{ selected: isCampaignSelected(campaign) }"
              @click="selectCampaign(campaign)"
            >
              {{ campaign.name }}
            </button>
          </div>
        </div>

        <DateRangePicker
          class="dashboard-date-picker"
          :model-value="{ start: filters.start_date, end: filters.end_date }"
          @change="handleDateRangeChange"
        />

        <span class="sync-status-label">
          <ArrowPathIcon :class="{ spinning: syncingIntegrations }" />
          {{ syncingIntegrations ? 'Синхронизация...' : 'Синхронизация: сегодня, 10:30' }}
        </span>

        <div class="filter-right-group">
          <label class="nds-check-wrap">
            <input type="checkbox" v-model="includeVat" class="nds-checkbox" />
            <span class="nds-label">НДС 22%</span>
          </label>

          <button class="sync-btn sync-btn-blue" type="button" :disabled="syncingIntegrations" @click="handleSyncIntegrations">
            <ArrowPathIcon :class="{ spinning: syncingIntegrations }" />
            {{ syncingIntegrations ? 'Синхронизация...' : 'Синхронизация' }}
          </button>

          <div class="filter-wrap custom-select dashboard-select export-select" :class="{ open: openMenu === 'export' }" v-click-outside="() => closeMenu('export')">
            <button class="export-btn cs-head" type="button" @click="toggleMenu('export')">
              <span class="cs-current">Экспорт отчета</span>
              <span class="cs-arrow">
                <ChevronDownIcon />
              </span>
            </button>
            <div class="cs-list dropdown-panel export">
              <button type="button" class="cs-option" @click="handleExportAction('pdf')"><DocumentArrowDownIcon /> Скачать в PDF</button>
              <button type="button" class="cs-option" @click="handleExportAction('png')"><PhotoIcon /> Скачать PNG</button>
              <button type="button" class="cs-option" @click="handleExportAction('link')"><LinkIcon /> Получить ссылку</button>
            </div>
          </div>
        </div>
      </div>
    </section>

    <VueDraggable
      v-model="visibleSlots"
      tag="section"
      class="kpi-grid"
      :animation="150"
      handle=".drag-handle"
      draggable=".metric-card-item"
      @end="saveKpiConfig"
    >
      <article v-for="key in visibleSlots" :key="key" class="metric-card metric-card-item">
        <div class="metric-head">
          <span class="metric-icon drag-handle" title="Перетащить">
            <component :is="metricsMap[key]?.icon" />
          </span>
          <div class="metric-text">
            <h3>{{ metricsMap[key]?.title }}</h3>
            <strong>{{ metricsMap[key]?.value }}</strong>
          </div>
          <span v-if="metricsMap[key]?.trend" class="trend" :class="{ negative: metricsMap[key]?.negative }">
            <ArrowTrendingUpIcon v-if="metricsMap[key]?.trendUp" class="trend-icon" />
            <ArrowTrendingDownIcon v-else class="trend-icon" />
            {{ metricsMap[key]?.trend }}
          </span>
          <button class="card-delete-btn" type="button" @click.stop="hideCard(key)" title="Скрыть">
            <XMarkIcon />
          </button>
        </div>
      </article>
      <div
        v-if="hiddenCardKeys.length"
        class="metric-card metric-card--add"
        v-click-outside="() => showAddMenu = false"
        @click.stop="showAddMenu = !showAddMenu"
      >
        <div class="add-card-inner">
          <PlusCircleIcon class="placeholder-plus" />
          <span>Добавить карточку</span>
        </div>
        <div v-if="showAddMenu" class="add-card-dropdown" @click.stop>
          <button v-for="k in hiddenCardKeys" :key="k" class="add-card-item" @click="restoreCard(k)">
            <component :is="metricsMap[k]?.icon" class="add-card-icon" />
            <span>{{ metricsMap[k]?.title }}</span>
          </button>
        </div>
      </div>
    </VueDraggable>

    <section class="chart-goals-grid">
      <article class="panel chart-panel">
        <div class="panel-title-row">
          <h2>Эффективность кампаний</h2>
        </div>
        <div class="chart-area">
          <svg viewBox="0 0 880 260" preserveAspectRatio="xMidYMid meet" role="img" aria-label="График эффективности кампаний">
            <defs>
              <linearGradient id="lineFill" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stop-color="#2563eb" stop-opacity="0.2" />
                <stop offset="100%" stop-color="#2563eb" stop-opacity="0" />
              </linearGradient>
            </defs>
            <g class="grid-lines">
              <line v-for="y in [34, 82, 130, 178, 226]" :key="y" x1="46" :y1="y" x2="858" :y2="y" />
            </g>
            <path class="chart-fill" :d="chartFillPath" />
            <path class="chart-line" :d="chartPath" />
            <g>
              <circle v-for="point in chartPoints" :key="`${point.x}-${point.y}`" :cx="point.x" :cy="point.y" r="3.5" />
            </g>
            <g class="axis-labels">
              <text text-anchor="end" x="42" y="38">{{ chartYLabels[0] }}</text>
              <text text-anchor="end" x="42" y="86">{{ chartYLabels[1] }}</text>
              <text text-anchor="end" x="42" y="134">{{ chartYLabels[2] }}</text>
              <text text-anchor="end" x="42" y="182">{{ chartYLabels[3] }}</text>
              <text text-anchor="end" x="42" y="230">{{ chartYLabels[4] }}</text>
              <text v-for="(label, index) in dateLabels" :key="label" :x="62 + index * 61" y="252">{{ label }}</text>
            </g>
            <g class="tooltip-pin">
              <rect x="415" y="6" width="58" height="27" rx="5" />
              <text x="444" y="23">{{ chartTooltipLabel }}</text>
            </g>
          </svg>
        </div>
      </article>

      <article class="panel goals-panel">
        <h2>Разбивка по целям</h2>
        <div class="goals-content">
          <div class="donut-wrap">
            <div
              class="donut"
              :style="{ '--donut-outer': donutGradient, '--donut-inner': innerDonutGradient }"
            ></div>
            <span>{{ goalsTotalLabel }}</span>
          </div>
          <div class="goals-list">
            <div
              v-for="goal in goals"
              :key="goal.name"
              class="goal-item"
              :style="{ '--goal-color': goal.color, '--goal-bg': goal.legendBg || goal.color + '24', '--goal-border': goal.color + '24' }"
            >
              <div>
                <span :style="{ background: goal.dotColor || goal.color }"></span>
                {{ goal.name }}
              </div>
              <p>{{ goal.value }}</p>
            </div>
          </div>
        </div>
      </article>
    </section>

    <section class="panel campaigns-panel">
      <div class="panel-title-row">
        <h2>Лучшие рекламные компании</h2>
      </div>
      <div class="campaign-table">
        <div class="campaign-row header">
          <span>Название кампании</span>
          <span>Расход</span>
          <span>Показы</span>
          <span>Клики</span>
          <span>CPC</span>
          <span>Лиды</span>
          <span>CPL</span>
        </div>
        <div v-for="(campaign, index) in campaignRows" :key="index" class="campaign-row" :class="campaign.tint">
          <span>{{ campaign.name }}</span>
          <span>{{ campaign.cost }} <b :class="{ negative: campaign.trendCost.negative }"><component :is="campaign.trendCost.icon" />{{ campaign.trendCost.text }}</b></span>
          <span>{{ campaign.impressions }} <b :class="{ negative: campaign.trendImpressions.negative }"><component :is="campaign.trendImpressions.icon" />{{ campaign.trendImpressions.text }}</b></span>
          <span>{{ campaign.clicks }} <b :class="{ negative: campaign.trendClicks.negative }"><component :is="campaign.trendClicks.icon" />{{ campaign.trendClicks.text }}</b></span>
          <span>{{ campaign.cpc }} <b :class="{ negative: campaign.trendCpc.negative }"><component :is="campaign.trendCpc.icon" />{{ campaign.trendCpc.text }}</b></span>
          <span>{{ campaign.leads }} <b :class="{ negative: campaign.trendLeads.negative }"><component :is="campaign.trendLeads.icon" />{{ campaign.trendLeads.text }}</b></span>
          <span>{{ campaign.cpa }} <b :class="{ negative: campaign.trendCpa.negative }"><component :is="campaign.trendCpa.icon" />{{ campaign.trendCpa.text }}</b></span>
        </div>
      </div>
    </section>

    <section class="bottom-grid">
      <article v-if="creatives.length" class="panel creatives-panel">
        <h2>Топ креативы</h2>
        <div class="creatives-row">
          <div v-for="creative in creatives" :key="creative.id || creative.title" class="creative-card">
            <div class="creative-image" :class="creative.class" :style="creative.imageUrl ? { backgroundImage: `url(${creative.imageUrl})` } : null">
              <span v-if="creative.badge">{{ creative.badge }}</span>
            </div>
            <p>Заголовок:</p>
            <em>{{ creative.heading }}</em>
            <p>Текст:</p>
            <em>{{ creative.text }}</em>
          </div>
        </div>
      </article>

      <article v-if="aiComments.length" class="panel ai-panel">
        <div class="ai-title">
          <span><SparklesIcon /></span>
          <h2>AI комментарии к отчету</h2>
        </div>
        <ul>
          <li v-for="comment in aiComments" :key="comment">{{ comment }}</li>
        </ul>
        <p>Комментарий сгенерирован AI на основе данных за период {{ dateRangeLabel }}</p>
      </article>

      <div class="side-stat-stack">
        <article class="panel mini-stat-panel">
          <h2>Типы устройств</h2>
          <div v-for="item in deviceStats" :key="item.name" class="progress-line">
            <span><component :is="item.icon" />{{ item.name }}</span>
            <div><i :style="{ width: item.width }"></i></div>
            <b>{{ item.value }}</b>
          </div>
        </article>

        <article class="panel mini-stat-panel">
          <h2>Плейсменты</h2>
          <div v-for="item in placements" :key="item.name" class="progress-line placement-line">
            <span>
              <span class="placement-icon" :class="item.name === 'РСЯ' ? 'placement-icon--rsya' : 'placement-icon--search'">
                <img v-if="item.name === 'РСЯ'" :src="yandexDirectIcon" alt="РСЯ" class="placement-icon-img" />
                <MagnifyingGlassIcon v-else />
              </span>
              {{ item.name }}
            </span>
            <div><i :style="{ width: item.width }"></i></div>
            <b>{{ item.value }}</b>
          </div>
        </article>
      </div>
    </section>

    <!-- Telegram link modal -->
    <div
      v-if="showTgLinkModal"
      class="fixed inset-0 z-[99999] flex items-center justify-center"
      style="background: rgba(0,0,0,0.5)"
      @click.self="closeTgLinkModal"
    >
      <div
        class="w-full mx-4"
        style="max-width:31.1111rem; border-radius:1.6667rem; padding:1.6667rem; box-shadow:0 25px 50px rgba(0,0,0,0.35)"
        :style="{ background: isDarkMode ? '#2a2d3c' : '#fff' }"
      >
        <h3 :style="{ fontSize:'1.25rem', fontWeight:600, color: isDarkMode ? '#f3f4f6' : '#111827', marginBottom:'0.5556rem' }">
          Подключите Telegram
        </h3>
        <p :style="{ fontSize:'0.9722rem', color: isDarkMode ? 'rgba(255,255,255,0.5)' : '#6b7280', marginBottom:'1.1111rem' }">
          В Telegram нажмите <strong>Start</strong> у бота, затем «Готово» — отчёт отправится автоматически.
        </p>
        <div style="display:flex; gap:0.8333rem">
          <button
            type="button"
            :style="{ flex:1, padding:'0.6944rem', borderRadius:'0.8333rem', border:'none', cursor:'pointer', fontSize:'0.9722rem', background: isDarkMode ? 'rgba(255,255,255,0.08)' : '#f3f4f6', color: isDarkMode ? '#f3f4f6' : '#374151' }"
            @click="closeTgLinkModal"
          >Отмена</button>
          <button
            type="button"
            style="flex:1; padding:0.6944rem; border-radius:0.8333rem; background:#2563eb; color:#fff; border:none; cursor:pointer; font-size:0.9722rem"
            :disabled="tgLinkChecking"
            @click="confirmTgLinked"
          >{{ tgLinkChecking ? 'Проверка...' : 'Готово' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import {
  ArrowPathIcon,
  ArrowPathRoundedSquareIcon,
  ArrowTrendingDownIcon,
  ArrowTrendingUpIcon,
  CheckCircleIcon,
  ArrowUpRightIcon,
  CalendarDaysIcon,
  ChartBarIcon,
  CheckBadgeIcon,
  ChevronDownIcon,
  CursorArrowRaysIcon,
  DevicePhoneMobileIcon,
  DocumentArrowDownIcon,
  LinkIcon,
  MagnifyingGlassIcon,
  PhotoIcon,
  PlayCircleIcon,
  PlusCircleIcon,
  SparklesIcon,
  WalletIcon,
  XMarkIcon
} from '@heroicons/vue/24/outline'
import { BuildingOfficeIcon, ComputerDesktopIcon, CursorArrowRippleIcon, EyeIcon } from '@heroicons/vue/24/solid'
import yandexDirectIcon from '@/assets/icons/yandex-direct.svg'
import vkAdsIcon from '@/assets/icons/vk-ads.png'
import { useTheme } from '@/composables/useTheme'
import { useDashboardStats } from '@/composables/useDashboardStats'
import { useProjects } from '@/composables/useProjects'
import { useTelegramReportLink } from '@/composables/useTelegramReportLink'
import { useToaster } from '@/composables/useToaster'
import api from '@/api/axios'
import DateRangePicker from '@/components/ui/DateRangePicker.vue'
import { VueDraggable } from 'vue-draggable-plus'

const { isDarkMode } = useTheme()
const toaster = useToaster()
const { currentProjectId, setCurrentProject } = useProjects()
const { openTelegramBotForLinking } = useTelegramReportLink()
const {
  summary,
  dynamics,
  campaigns,
  clients,
  allCampaigns,
  loading,
  filters,
  handlePeriodChange,
  fetchStats,
  fetchAllCampaignsForGoalsTab,
  loadingCampaigns,
  deviceStats: deviceStatsRaw,
  placements: placementsRaw
} = useDashboardStats()

const openMenu = ref('')

const METRIC_CONFIG = [
  { key: 'expenses',    title: 'Расходы',       subtitle: 'За период',       icon: 'wallet',   costMetric: false },
  { key: 'impressions', title: 'Показы',         subtitle: 'По всем каналам', icon: 'chart',    costMetric: false },
  { key: 'clicks',      title: 'Клики',          subtitle: 'Все переходы',    icon: 'cursor',   costMetric: false },
  { key: 'cpc',         title: 'СРС',            subtitle: 'Стоимость клика', icon: 'play',     costMetric: true  },
  { key: 'leads',       title: 'Лиды',           subtitle: 'По всем каналам', icon: 'calendar', costMetric: false },
  { key: 'cpa',         title: 'CPL',            subtitle: 'Стоимость лида',  icon: 'badge',    costMetric: true  },
]

// KPI cards drag & hide
const KPI_CONFIG_KEY = 'dashboard_kpi_config'
const _loadKpiConfig = () => { try { const s = localStorage.getItem(KPI_CONFIG_KEY); return s ? JSON.parse(s) : null } catch { return null } }
const _savedKpi = _loadKpiConfig()
const _defaultOrder = METRIC_CONFIG.map(m => m.key)
const kpiOrder = ref(_savedKpi?.order || [..._defaultOrder])
const kpiHiddenSet = ref(new Set(_savedKpi?.hidden || []))

const visibleSlots = computed({
  get: () => kpiOrder.value.filter(k => !kpiHiddenSet.value.has(k)),
  set: (newOrder) => {
    const hidden = kpiOrder.value.filter(k => kpiHiddenSet.value.has(k))
    kpiOrder.value = [...newOrder, ...hidden]
    saveKpiConfig()
  }
})
const hiddenCardKeys = computed(() => kpiOrder.value.filter(k => kpiHiddenSet.value.has(k)))

const saveKpiConfig = () => {
  localStorage.setItem(KPI_CONFIG_KEY, JSON.stringify({ order: kpiOrder.value, hidden: [...kpiHiddenSet.value] }))
}
const hideCard = (key) => {
  kpiHiddenSet.value = new Set([...kpiHiddenSet.value, key])
  saveKpiConfig()
}
const restoreCard = (key) => {
  const s = new Set(kpiHiddenSet.value); s.delete(key); kpiHiddenSet.value = s
  saveKpiConfig()
  showAddMenu.value = false
}
const showAddMenu = ref(false)
const metricsMap = computed(() => { const m = {}; metrics.value.forEach(x => { m[x.key] = x }); return m })
const campaignQuery = ref('')
const selectedReportChannel = ref('Telegram')
const selectedReportTemplate = ref('Шаблон: Яндекс')
const REPORT_SCHEDULE_STORAGE_KEY = 'admirra:dashboard-report-schedule'
const defaultReportSchedule = { day: 'daily', time: '10:00' }
const reportSchedule = ref({ ...defaultReportSchedule })
const selectedChartPeriod = ref('Месяц')
const includeVat = ref(true)
const syncingIntegrations = ref(false)
const sendingExport = ref(false)
const sendingTg = ref(false)
const sendingEmail = ref(false)
const showTgLinkModal = ref(false)
const pendingTgSendAfterLink = ref(false)
const tgLinkChecking = ref(false)
const userReportSettings = ref({ telegram_chat_id: '', email_recipients: [], report_schedule: '' })
const reportComment = ref('')
const reportGoals = ref([])
const integrations = ref([])
const topAds = ref([])

const toggleMenu = (name) => {
  openMenu.value = openMenu.value === name ? '' : name
}

const closeMenu = (name) => {
  if (openMenu.value === name) openMenu.value = ''
}

const selectReportTemplate = (option) => {
  selectedReportTemplate.value = option
  closeMenu('report-template')
}

const selectFilterChannel = (channel) => {
  filters.channel = channel.value
  filters.campaign_ids = []
  closeMenu('channels')
}

const selectCampaign = (campaign) => {
  filters.campaign_ids = campaign?.id ? [campaign.id] : []
  closeMenu('campaigns')
}

const selectChartPeriod = (option) => {
  selectedChartPeriod.value = option
  const periodMap = { Неделя: '7', Месяц: '30', Квартал: '90', Год: '365' }
  filters.period = periodMap[option] || filters.period
  handlePeriodChange()
  closeMenu('chart-period')
}

const handleDateRangeChange = (range) => {
  if (range?.start) filters.start_date = range.start
  if (range?.end) filters.end_date = range.end
  filters.period = 'custom'
  fetchStats()
}

const selectConnectedChannel = (channel) => {
  selectFilterChannel(channel)
}

const vClickOutside = {
  mounted(el, binding) {
    el.__clickOutside__ = (event) => {
      if (!(el === event.target || el.contains(event.target))) {
        binding.value(event)
      }
    }
    document.addEventListener('click', el.__clickOutside__)
  },
  unmounted(el) {
    document.removeEventListener('click', el.__clickOutside__)
  }
}

const channels = [
  { name: 'Yandex Direct', value: 'yandex', color: '#ffd426', bg: '#fff8e7', darkBg: 'rgba(255, 212, 38, 0.14)', asset: yandexDirectIcon, icon: CursorArrowRippleIcon },
  { name: 'VK Ads Manager', value: 'vk', color: '#2563eb', bg: '#f3f7ff', darkBg: 'rgba(74, 122, 255, 0.14)', asset: vkAdsIcon, imageClass: 'vk', icon: EyeIcon }
]

const reportChannels = [
  { name: 'Telegram', bg: '#f3f5f7', darkBg: 'rgba(255, 255, 255, 0.08)', iconClass: 'telegram-icon' },
  { name: 'E-mail', bg: '#f3f5f7', darkBg: 'rgba(255, 255, 255, 0.08)', iconClass: 'email-icon' },
  { name: 'Max', bg: '#f3f5f7', darkBg: 'rgba(255, 255, 255, 0.08)', iconClass: 'max-icon' }
]

const filterChannels = [
  { name: 'Все каналы', value: 'all', color: '#b3b3b3', icon: ChartBarIcon },
  ...channels
]

const reportTemplateOptions = ['Шаблон: Яндекс', 'Шаблон: VK Ads']
const scheduleDayOptions = [
  { value: 'daily', label: 'Ежедневно', short: 'ежедневно' },
  { value: 'monday', label: 'Понедельник', short: 'ПН' },
  { value: 'tuesday', label: 'Вторник', short: 'ВТ' },
  { value: 'wednesday', label: 'Среда', short: 'СР' },
  { value: 'thursday', label: 'Четверг', short: 'ЧТ' },
  { value: 'friday', label: 'Пятница', short: 'ПТ' },
  { value: 'saturday', label: 'Суббота', short: 'СБ' },
  { value: 'sunday', label: 'Воскресенье', short: 'ВС' },
]
const chartPeriodOptions = ['Неделя', 'Месяц', 'Квартал', 'Год']

const normalizeScheduleTime = (value) => {
  const match = String(value || '').match(/^(\d{2}):(\d{2})$/)
  if (!match) return defaultReportSchedule.time
  const hours = Number(match[1])
  const minutes = Number(match[2])
  if (hours > 23 || minutes > 59) return defaultReportSchedule.time
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`
}

const normalizeReportSchedule = (value = {}) => {
  const validDays = new Set(scheduleDayOptions.map((option) => option.value))
  const day = validDays.has(value.day) ? value.day : defaultReportSchedule.day
  const time = normalizeScheduleTime(value.time)
  return { day, time }
}

const formatReportSchedule = (value) => {
  const schedule = normalizeReportSchedule(value)
  if (schedule.day === 'daily') return `Ежедневно в ${schedule.time} по МСК`
  const day = scheduleDayOptions.find((option) => option.value === schedule.day)?.short || 'ПН'
  return `${day} в ${schedule.time} по МСК`
}

const selectedSchedule = computed(() => formatReportSchedule(reportSchedule.value))

const readStoredReportSchedule = () => {
  if (typeof window === 'undefined') return { ...defaultReportSchedule }
  try {
    const raw = window.localStorage.getItem(REPORT_SCHEDULE_STORAGE_KEY)
    return raw ? normalizeReportSchedule(JSON.parse(raw)) : { ...defaultReportSchedule }
  } catch {
    return { ...defaultReportSchedule }
  }
}

const persistReportSchedule = (value) => {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(REPORT_SCHEDULE_STORAGE_KEY, JSON.stringify(normalizeReportSchedule(value)))
}

const updateScheduleTime = (event) => {
  const digits = String(event.target.value || '').replace(/\D/g, '').slice(0, 4)
  const value = digits.length > 2 ? `${digits.slice(0, 2)}:${digits.slice(2)}` : digits
  reportSchedule.value = { ...reportSchedule.value, time: value }
}

const setScheduleDay = (day) => {
  reportSchedule.value = { ...reportSchedule.value, day }
}

const loadReportSchedule = () => {
  reportSchedule.value = readStoredReportSchedule()
}

const saveReportSchedule = () => {
  const normalized = normalizeReportSchedule(reportSchedule.value)
  reportSchedule.value = normalized
  persistReportSchedule(normalized)
  userReportSettings.value.report_schedule = JSON.stringify(normalized)
  closeMenu('report-schedule')
  toaster.success('График отправки сохранен')
}

const resetReportSchedule = () => {
  reportSchedule.value = { ...defaultReportSchedule }
  saveReportSchedule()
}

const getChipBackground = (item) => (isDarkMode.value ? (item.darkBg ?? item.bg) : item.bg)

const filteredCampaigns = computed(() => {
  const query = campaignQuery.value.trim().toLowerCase()
  const items = allCampaigns.value
  if (!query) return items
  return items.filter((item) => item.name.toLowerCase().includes(query))
})

const metricIcons = {
  wallet: WalletIcon,
  chart: ChartBarIcon,
  cursor: CursorArrowRaysIcon,
  play: PlayCircleIcon,
  calendar: CalendarDaysIcon,
  badge: CheckBadgeIcon
}

const statIcons = {
  mobile: DevicePhoneMobileIcon,
  desktop: ComputerDesktopIcon
}

const formatNumber = (value, digits = 0) => new Intl.NumberFormat('ru-RU', {
  minimumFractionDigits: digits,
  maximumFractionDigits: digits
}).format(Number(value) || 0)

const formatMoney = (value) => `${formatNumber(value, 2)} ₽`

const withVat = (value) => {
  const num = Number(value) || 0
  return includeVat.value ? num * 1.2 : num
}

const formatTrend = (value) => {
  const num = Number(value)
  if (!Number.isFinite(num)) return '+0%'
  return `${num > 0 ? '+' : ''}${formatNumber(num, 1)}%`
}

const costTrendMetrics = new Set(['cpc', 'cpa'])

const campaignTrend = (value, metric) => {
  const num = Number(value)
  const safeNum = Number.isFinite(num) ? num : 0
  const isCostMetric = costTrendMetrics.has(metric)
  return {
    text: formatTrend(safeNum),
    icon: safeNum >= 0 ? ArrowTrendingUpIcon : ArrowTrendingDownIcon,
    negative: isCostMetric ? safeNum > 0 : safeNum < 0,
  }
}

const selectedChannel = computed(() => filterChannels.find((item) => item.value === filters.channel)?.name || 'Все каналы')
const selectedFilterChannelLabel = computed(() => selectedChannel.value)

const selectedCampaignLabel = computed(() => {
  if (!filters.client_id) return 'Сначала проект'
  if (loadingCampaigns.value) return 'Загрузка...'
  if (!filters.campaign_ids?.length) return 'Кампании'
  if (filters.campaign_ids.length > 1) return `Кампании (${filters.campaign_ids.length})`
  const found = allCampaigns.value.find((campaign) => campaign.id === filters.campaign_ids[0])
  return found?.name || 'Кампания'
})

const isCampaignSelected = (campaign) => filters.campaign_ids?.includes(campaign.id)

const dateRangeLabel = computed(() => {
  const format = (date) => {
    if (!date) return ''
    const [year, month, day] = String(date).split('-')
    return day && month && year ? `${day}.${month}.${year}` : date
  }
  return `${format(filters.start_date)} - ${format(filters.end_date)}`
})

const dashboardTitle = computed(() => {
  if (filters.campaign_ids?.length) {
    const campaign = allCampaigns.value.find((item) => item.id === filters.campaign_ids[0])
    return campaign ? `Отчет по кампании: ${campaign.name}` : `Отчет по кампаниям (${filters.campaign_ids.length})`
  }
  if (filters.client_id) {
    const client = clients.value.find((item) => item.id === filters.client_id)
    return client ? `Отчет по проекту: ${client.name}` : 'Отчет по проекту'
  }
  if (filters.channel !== 'all') return `Отчет: ${selectedFilterChannelLabel.value}`
  return 'Отчет по всем проектам'
})

const metrics = computed(() => {
  const data = summary.value || {}
  const trends = data.trends || {}
  const hasData = !!summary.value
  const values = {
    expenses:    hasData ? formatMoney(withVat(data.expenses))                    : '—',
    impressions: hasData ? formatNumber(data.impressions)                         : '—',
    clicks:      hasData ? formatNumber(data.clicks)                              : '—',
    cpc:         hasData ? formatMoney(withVat(data.cpc))                        : '—',
    leads:       hasData ? `${formatNumber(data.leads)} шт.`                     : '—',
    cpa:         hasData ? formatMoney(withVat(data.cpa))                        : '—',
  }
  return METRIC_CONFIG.map((metric) => {
    const rawTrend = Number(trends[metric.key] ?? 0)
    const trendRaw = Number.isFinite(rawTrend) ? rawTrend : 0
    return {
      ...metric,
      value: values[metric.key],
      trend: hasData ? formatTrend(trendRaw) : null,
      trendUp: trendRaw >= 0,
      negative: metric.costMetric ? trendRaw > 0 : trendRaw < 0,
      icon: metricIcons[metric.icon] || ChartBarIcon
    }
  })
})

const chartSourceValues = computed(() => {
  const values = dynamics.value?.costs || []
  return values.map((value) => withVat(value))
})

const chartPoints = computed(() => {
  const values = chartSourceValues.value
  const max = Math.max(...values, 1)
  const min = Math.min(...values, 0)
  const span = Math.max(max - min, 1)
  const left = 56
  const right = 846
  const top = 35
  const bottom = 224
  return values.map((value, index) => ({
    x: values.length === 1 ? left : left + ((right - left) / (values.length - 1)) * index,
    y: bottom - ((value - min) / span) * (bottom - top),
    value
  }))
})

const chartPath = computed(() => `M ${chartPoints.value.map((point) => `${point.x} ${point.y}`).join(' L ')}`)
const chartFillPath = computed(() => {
  const points = chartPoints.value
  const first = points[0] || { x: 56 }
  const last = points[points.length - 1] || { x: 846 }
  return `${chartPath.value} L ${last.x} 226 L ${first.x} 226 Z`
})

const dateLabels = computed(() => dynamics.value?.labels || [])

const chartYLabels = computed(() => {
  const values = chartSourceValues.value
  const rawMax = Math.max(...values, 0)
  if (rawMax === 0) return ['0', '0', '0', '0', '0']
  const magnitude = Math.pow(10, Math.floor(Math.log10(rawMax)))
  const niceMax = Math.ceil(rawMax / magnitude) * magnitude
  const fmt = (v) => {
    if (v === 0) return '0'
    if (v >= 1_000_000) return `${+(v / 1_000_000).toFixed(1)}M`
    if (v >= 1_000) return `${+(v / 1_000).toFixed(1)}k`
    return String(Math.round(v))
  }
  return [
    fmt(niceMax),
    fmt(niceMax * 0.75),
    fmt(niceMax * 0.5),
    fmt(niceMax * 0.25),
    '0'
  ]
})
const chartTooltipLabel = computed(() => {
  const last = chartSourceValues.value[chartSourceValues.value.length - 1]
  return last ? formatNumber(last, 0) : 'API'
})

const goals = computed(() => {
  const colors = ['#3f63f6', '#f39a72', '#6ee7b7', '#8ada70', '#d38cff']
  if (!reportGoals.value.length) return []
  const total = reportGoals.value.reduce((sum, item) => sum + Number(item.count ?? item.conversions ?? item.value ?? 0), 0) || 1
  return reportGoals.value.slice(0, 5).map((goal, index) => {
    const count = Number(goal.count ?? goal.conversions ?? goal.value ?? 0)
    const pct = (count / total) * 100
    return {
      name: goal.name || goal.goal_name || `Цель ${index + 1}`,
      value: `${formatNumber(count)} шт. (${formatNumber(pct, 1)}%)`,
      color: goal.color || colors[index % colors.length],
      pct
    }
  })
})

const donutGradient = computed(() => {
  const items = goals.value
  if (!items.length) return 'conic-gradient(from -90deg, #e5e7eb 0 100%)'
  const blue = items[0]?.color || '#5677f6'
  const orange = items[1]?.color || '#f2a988'
  const green = items[2]?.color || '#e8fdec'
  return `conic-gradient(from -90deg, ${blue} 0 50%, ${orange} 50% 75%, ${green} 75% 100%)`
})

const innerDonutGradient = computed(() => {
  const items = goals.value
  if (!items.length) return 'conic-gradient(from -90deg, #d1d5db 0 100%)'
  const blue = items[0]?.innerColor || items[0]?.color || '#3d5fdf'
  const orange = items[1]?.innerColor || items[1]?.color || '#e39674'
  const green = items[2]?.innerColor || items[2]?.color || '#cbedd1'
  return `conic-gradient(from -90deg, ${blue} 0 50%, ${orange} 50% 75%, ${green} 75% 100%)`
})

const goalsTotalLabel = computed(() => {
  const total = reportGoals.value.reduce((sum, item) => sum + Number(item.count ?? item.conversions ?? item.value ?? 0), 0)
  return `${formatNumber(total || summary.value?.leads || 0)} шт.`
})

const campaignRows = computed(() => {
  const rows = campaigns.value?.length ? campaigns.value : []
  if (!rows.length) return []
  const tints = ['orange', 'green', 'blue']
  return rows.slice(0, 5).map((campaign, index) => ({
    name: campaign.name || `Кампания ${index + 1}`,
    tint: tints[index % tints.length],
    cost: formatMoney(withVat(campaign.cost)),
    impressions: formatNumber(campaign.impressions),
    clicks: formatNumber(campaign.clicks),
    cpc: formatMoney(withVat(campaign.cpc)),
    leads: `${formatNumber(campaign.conversions ?? campaign.leads)} шт.`,
    cpa: formatMoney(withVat(campaign.cpa)),
    trendCost: campaignTrend(campaign.trend_cost, 'cost'),
    trendImpressions: campaignTrend(campaign.trend_impressions, 'impressions'),
    trendClicks: campaignTrend(campaign.trend_clicks, 'clicks'),
    trendCpc: campaignTrend(campaign.trend_cpc, 'cpc'),
    trendLeads: campaignTrend(campaign.trend_conversions, 'leads'),
    trendCpa: campaignTrend(campaign.trend_cpa, 'cpa')
  }))
})

const creatives = computed(() => {
  if (!topAds.value.length) return []
  const classes = ['city', 'blue', 'house']
  return topAds.value.slice(0, 3).map((post, index) => ({
    id: post.id || `${post.title}-${index}`,
    badge: post.subtitle || (post.platform === 'yandex' ? 'Яндекс.Директ' : 'VK Ads'),
    title: post.title || 'Креатив',
    heading: post.heading || post.title || '—',
    text: post.text || post.description || `${formatNumber(post.impressions)} показов, ${formatNumber(post.clicks)} кликов, CTR ${post.ctr ?? '—'}%`,
    imageUrl: post.image_url || post.imageUrl || '',
    class: classes[index % classes.length]
  }))
})
const aiComments = computed(() => {
  if (!reportComment.value) return []
  return reportComment.value
    .split(/\n+|(?<=[.!?])\s+/)
    .map((item) => item.trim())
    .filter(Boolean)
    .slice(0, 4)
})
const deviceStats = computed(() =>
  deviceStatsRaw.value.map((item) => ({
    ...item,
    icon: statIcons[item.icon] || ComputerDesktopIcon
  }))
)
const placements = computed(() => placementsRaw.value)

const syncLabel = computed(() => integrations.value.length ? 'Синхронизировать данные' : 'Нет подключенных каналов')

const getStatsParams = () => ({
  start_date: filters.start_date,
  end_date: filters.end_date,
  platform: filters.channel,
  client_id: filters.client_id || undefined,
  campaign_ids: filters.campaign_ids?.length ? filters.campaign_ids : undefined,
  goal_action_ids: filters.channel === 'vk' && filters.vk_goal_action_ids?.length ? filters.vk_goal_action_ids : undefined
})

const fetchReportGoals = async () => {
  if (!filters.start_date || !filters.end_date) return
  try {
    const params = {
      client_id: filters.client_id || undefined,
      date_from: filters.start_date,
      date_to: filters.end_date,
      platform: filters.channel !== 'all' ? filters.channel : undefined,
      campaign_ids: filters.campaign_ids?.length ? filters.campaign_ids.join(',') : undefined
    }
    const { data } = await api.get('dashboard/goals', { params })
    reportGoals.value = Array.isArray(data) ? data : (data?.goals || [])
  } catch {
    reportGoals.value = []
  }
}

const fetchTopAds = async () => {
  if (!filters.start_date || !filters.end_date) return
  try {
    const params = getStatsParams()
    const { data } = await api.get('dashboard/top-ads', { params })
    topAds.value = Array.isArray(data) ? data : []
  } catch {
    topAds.value = []
  }
}

const fetchIntegrations = async () => {
  try {
    const params = filters.client_id ? { client_id: filters.client_id } : {}
    const { data } = await api.get('dashboard/integrations', { params })
    integrations.value = data || []
  } catch {
    integrations.value = []
  }
}

const handleSyncIntegrations = async () => {
  if (syncingIntegrations.value) return
  syncingIntegrations.value = true
  try {
    const params = filters.client_id ? { client_id: filters.client_id } : {}
    const { data: list } = await api.get('integrations/', { params })
    if (!list?.length) {
      toaster.info('Нет подключенных интеграций для синхронизации')
      return
    }
    for (const integration of list) {
      await api.post(`integrations/${integration.id}/sync`, { days: 90 })
    }
    toaster.info(`Синхронизация запущена для ${list.length} каналов`)
    fetchIntegrations()
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Не удалось запустить синхронизацию')
  } finally {
    syncingIntegrations.value = false
  }
}

const refreshUserReportSettings = async () => {
  try {
    const { data } = await api.get('/auth/me')
    userReportSettings.value.telegram_chat_id = data.report_telegram_chat_id || ''
    userReportSettings.value.email_recipients = data.report_email_recipients || []
    userReportSettings.value.report_schedule = data.report_schedule || 'mon_10'
  } catch {
    /* ignore */
  }
}

const handleGenerateReport = async () => {
  try {
    const { data } = await api.post('ai/generate-report', {
      client_id: filters.client_id || null,
      start_date: filters.start_date,
      end_date: filters.end_date,
      report_type: 'full'
    })
    reportComment.value = data?.text || ''
    return reportComment.value
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Не удалось сгенерировать отчет')
    return ''
  }
}

const getOrGenerateComment = async () => reportComment.value || await handleGenerateReport()

const downloadBlob = (blob, filename) => {
  const url = window.URL.createObjectURL(new Blob([blob]))
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', filename)
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

const getReportPayload = () => ({
  start_date: filters.start_date,
  end_date: filters.end_date,
  client_id: filters.client_id || undefined,
  ai: true,
  ...(reportComment.value?.trim() ? { comment: reportComment.value.trim() } : {})
})

const handleDownloadPdf = async () => {
  sendingExport.value = true
  try {
    const payload = getReportPayload()
    const response = reportComment.value?.trim()
      ? await api.post('reports/pdf', payload, { responseType: 'blob' })
      : await api.get('reports/pdf', { params: payload, responseType: 'blob' })
    downloadBlob(response.data, `report_${filters.start_date}_${filters.end_date}.pdf`)
    toaster.success('Отчет скачан')
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Не удалось скачать PDF')
  } finally {
    sendingExport.value = false
  }
}

const handleDownloadPng = async () => {
  sendingExport.value = true
  try {
    const payload = getReportPayload()
    const response = reportComment.value?.trim()
      ? await api.post('reports/png', payload, { responseType: 'blob' })
      : await api.get('reports/png', { params: payload, responseType: 'blob' })
    downloadBlob(response.data, `report_${filters.start_date}_${filters.end_date}.png`)
    toaster.success('PNG скачан')
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Не удалось скачать PNG')
  } finally {
    sendingExport.value = false
  }
}

const handleGetLink = async () => {
  sendingExport.value = true
  try {
    const { data } = await api.post('reports/link', {
      start_date: filters.start_date,
      end_date: filters.end_date,
      client_id: filters.client_id || null,
      comment: reportComment.value?.trim() || null
    })
    const base = window.location.origin
    const fullUrl = `${base}${data.url.startsWith('/') ? '' : '/'}${data.url}`
    await navigator.clipboard.writeText(fullUrl)
    window.open(fullUrl, '_blank', 'noopener,noreferrer')
    toaster.success('Ссылка скопирована')
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Не удалось создать ссылку')
  } finally {
    sendingExport.value = false
  }
}

const handleExportAction = async (type) => {
  closeMenu('export')
  if (type === 'pdf') return handleDownloadPdf()
  if (type === 'png') return handleDownloadPng()
  return handleGetLink()
}

const executeTelegramReportSend = async (chatId) => {
  sendingTg.value = true
  try {
    const text = await getOrGenerateComment()
    await api.post('reports/send', {
      report_type: 'ai',
      channels: ['telegram'],
      telegram_chat_id: chatId,
      client_id: filters.client_id || null,
      start_date: filters.start_date,
      end_date: filters.end_date,
      ...(text ? { comment: text } : {})
    })
    toaster.success('Отчет отправлен в Telegram')
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Ошибка отправки')
  } finally {
    sendingTg.value = false
  }
}

const handleSendTelegram = async () => {
  const existing = (userReportSettings.value.telegram_chat_id || '').trim()
  if (existing) return executeTelegramReportSend(existing)
  try {
    await openTelegramBotForLinking()
    pendingTgSendAfterLink.value = true
    showTgLinkModal.value = true
    toaster.info('Откройте бота и нажмите Start')
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Не удалось открыть Telegram')
  }
}

const handleSendEmail = async () => {
  const emails = userReportSettings.value.email_recipients || []
  if (!emails.length) {
    toaster.error('Email получатели не настроены')
    return
  }
  sendingEmail.value = true
  try {
    const text = await getOrGenerateComment()
    await api.post('reports/send', {
      report_type: 'ai',
      channels: ['email'],
      email_recipients: emails,
      client_id: filters.client_id || null,
      start_date: filters.start_date,
      end_date: filters.end_date,
      ...(text ? { comment: text } : {})
    })
    toaster.success('Отчет отправлен на email')
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Ошибка отправки')
  } finally {
    sendingEmail.value = false
  }
}

const handleSendSelectedReport = () => {
  if (selectedReportChannel.value === 'E-mail') return handleSendEmail()
  return handleSendTelegram()
}

const refreshTelegramChatFromServer = async () => {
  try {
    const { data } = await api.get('/auth/me')
    userReportSettings.value.telegram_chat_id = data?.report_telegram_chat_id || ''
  } catch { /* ignore */ }
}

function closeTgLinkModal() {
  showTgLinkModal.value = false
  pendingTgSendAfterLink.value = false
}

async function confirmTgLinked() {
  tgLinkChecking.value = true
  try {
    await refreshTelegramChatFromServer()
    const chatId = (userReportSettings.value.telegram_chat_id || '').trim()
    if (!chatId) {
      toaster.error('Сначала нажмите Start в чате с ботом в Telegram')
      return
    }
    showTgLinkModal.value = false
    const sendNow = pendingTgSendAfterLink.value
    pendingTgSendAfterLink.value = false
    if (sendNow) await executeTelegramReportSend(chatId)
  } finally {
    tgLinkChecking.value = false
  }
}

watch(currentProjectId, (newId) => {
  if (filters.client_id !== newId) filters.client_id = newId
}, { immediate: true })

watch(() => filters.client_id, (newId) => {
  if (currentProjectId.value !== newId) setCurrentProject(newId)
  fetchIntegrations()
}, { immediate: true })

watch(() => [filters.start_date, filters.end_date, filters.client_id, filters.channel, filters.campaign_ids, filters.vk_goal_action_ids], () => {
  fetchReportGoals()
  fetchTopAds()
}, { deep: true })

watch(() => filters.period, (period) => {
  const labelMap = { 7: 'Неделя', 14: 'Неделя', 30: 'Месяц', 90: 'Квартал', 365: 'Год' }
  selectedChartPeriod.value = labelMap[period] || selectedChartPeriod.value
}, { immediate: true })

watch(() => filters.channel, (channel) => {
  if (channel === 'vk') fetchAllCampaignsForGoalsTab()
})

onMounted(() => {
  loadReportSchedule()
  refreshUserReportSettings()
  fetchIntegrations()
  fetchReportGoals()
  fetchTopAds()
})
</script>

<style scoped>
.figma-dashboard {
  width: 100%;
  max-width: 110.4167rem;
  margin: 0 auto;
  padding: 5rem 0 3rem;
  color: #171717;
  font-family: Inter, system-ui, sans-serif;
}

.panel {
  background: #fff;
  border: 1px solid rgba(235, 235, 235, 0.8);
  border-radius: 1.5rem;
  box-shadow: 0 0.8rem 2.6rem rgba(15, 23, 42, 0.025);
}

.top-grid {
  display: grid;
  grid-template-columns: 49.4rem 1fr;
  gap: 2rem;
  align-items: stretch;
}

.panel-channels,
.panel-reports {
  min-height: 13.1rem;
  padding: 2.5rem;
}

.panel h2,
.panel-channels h2,
.panel-reports h2 {
  margin: 0;
  font-size: 2rem;
  font-weight: 500;
  line-height: 1;
}

.chips-row {
  display: flex;
  flex-wrap: wrap;
  gap: 1.5rem;
  margin-top: 2rem;
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 1rem;
  height: 4.6rem;
  padding: 0 1.5rem;
  border: 0;
  border-radius: 1.2rem;
  background: #f7f9ff;
  color: #4b4b4b;
  font-size: 1.3rem;
  font-weight: 500;
  white-space: nowrap;
}

.chip-dot {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.4rem;
  height: 1.4rem;
  border-radius: 69.375rem;
  color: #fff;
}

.chip-icon {
  width: 0.9rem;
  height: 0.9rem;
}

.panel-reports {
  display: grid;
  grid-template-columns: minmax(30rem, auto) minmax(17rem, auto) minmax(25rem, auto) auto;
  gap: 2rem;
  align-items: end;
}

.report-schedule p {
  margin: 0 0 2rem;
  color: #b3b3b3;
  font-size: 1.3rem;
  font-weight: 500;
}

.select-like,
.filter-btn,
.export-btn {
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.2rem;
  width: 100%;
  height: 4.6rem;
  padding: 0 1.5rem;
  border: 1px solid #ebebeb;
  border-radius: 1.2rem;
  background: #fff;
  color: #b3b3b3;
  font-size: 1.3rem;
  font-weight: 500;
}

.select-like svg,
.filter-btn svg,
.export-btn svg,
.primary-report svg,
.sync-btn svg,
.see-all svg,
.month-select svg {
  width: 1.6rem;
  height: 1.6rem;
  flex: 0 0 auto;
}

.primary-report {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  height: 4.6rem;
  padding: 0 1rem;
  border: 0;
  border-radius: 1.2rem;
  background: #2563eb;
  color: #fff;
  font-size: 1.3rem;
  font-weight: 600;
  white-space: nowrap;
}

.heading-section {
  margin-top: 6.5rem;
}

.heading-section h1 {
  margin: 0 0 2.4rem;
  color: #171717;
  font-size: 2.8rem;
  font-weight: 700;
  line-height: 1;
}

.filters-row {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  align-items: center;
}

.filter-wrap {
  position: relative;
}

.filters-row .filter-btn {
  width: auto;
  min-width: 14rem;
}

.date-btn {
  min-width: 25.7rem;
}

.dashboard-date-picker {
  flex: 0 0 auto;
  width: 26rem;
}

.filter-right-group {
  display: flex;
  align-items: center;
  gap: 1.6rem;
  margin-left: auto;
  flex-shrink: 0;
}

.dashboard-date-picker :deep(.date-range-picker-container) {
  width: 100%;
}

.dashboard-date-picker :deep(.drp-trigger .truncate) {
  color: #b3b3b3;
  font-weight: 500;
}

.sync-status-label {
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  font-size: 1.3rem;
  color: #b3b3b3;
  white-space: nowrap;
  flex-shrink: 0;
}

.sync-status-label svg {
  width: 1.4rem;
  height: 1.4rem;
  flex-shrink: 0;
}

:global(.calendar-popup) {
  width: min(38.8889rem, calc(100vw - 1.6667rem)) !important;
  max-height: min(36.1111rem, calc(100vh - 1.6667rem));
  overflow: auto;
  padding: 1.1111rem !important;
  border: 1px solid #ebebeb !important;
  border-radius: 0.9722rem !important;
  background: #fff !important;
  box-shadow: 0 18px 48px rgba(15, 23, 42, 0.12) !important;
}

:global(.calendar-popup .drp-quick-row) {
  gap: 0.4167rem !important;
  margin: 0 0 0.9722rem !important;
  padding: 0 0 0.8333rem !important;
  border-bottom: 1px solid #eef0f3 !important;
  align-items: center !important;
}

:global(.calendar-popup .drp-quick) {
  height: 1.9444rem !important;
  min-height: 0 !important;
  padding: 0 0.6944rem !important;
  border: 1px solid #eef0f3 !important;
  border-radius: 0.625rem !important;
  background: #f7f8fa !important;
  color: #4b5563 !important;
  font-size: 0.8333rem !important;
  line-height: 1 !important;
  font-weight: 600 !important;
  letter-spacing: 0 !important;
}

:global(.calendar-popup .drp-quick:hover),
:global(.calendar-popup .drp-quick.text-blue-600) {
  color: #2563eb !important;
  border-color: #dbeafe !important;
  background: #eff6ff !important;
}

:global(.calendar-popup .drp-month-grid) {
  gap: 1.5278rem !important;
}

:global(.calendar-popup .drp-month-head) {
  margin-bottom: 0.6944rem !important;
}

:global(.calendar-popup .drp-month-head h3) {
  color: #111827 !important;
  font-size: 1.0417rem !important;
  line-height: 1.2 !important;
  font-weight: 700 !important;
  letter-spacing: 0 !important;
}

:global(.calendar-popup .drp-nav) {
  width: 1.6667rem !important;
  height: 1.6667rem !important;
  min-height: 1.6667rem !important;
  padding: 0 !important;
  border-radius: 69.375rem !important;
  color: #4b5563 !important;
  background: transparent !important;
}

:global(.calendar-popup .drp-nav:hover) {
  background: #f3f6fb !important;
}

:global(.calendar-popup .drp-nav svg) {
  width: 0.9722rem !important;
  height: 0.9722rem !important;
  color: currentColor !important;
}

:global(.calendar-popup .drp-weekdays) {
  gap: 0.2778rem !important;
  margin-bottom: 0.2778rem !important;
}

:global(.calendar-popup .drp-weekday) {
  padding: 0 !important;
  color: #6b7280 !important;
  font-size: 0.6944rem !important;
  line-height: 1.3889rem !important;
  font-weight: 600 !important;
  letter-spacing: 0 !important;
  text-transform: lowercase !important;
}

:global(.calendar-popup .drp-weekday.text-red-500) {
  color: #ef4444 !important;
}

:global(.calendar-popup .drp-days) {
  gap: 0.2778rem !important;
}

:global(.calendar-popup .drp-day) {
  width: 2.0833rem !important;
  height: 2.0833rem !important;
  min-height: 2.0833rem !important;
  padding: 0 !important;
  border-radius: 0.5556rem !important;
  border: 0 !important;
  font-size: 0.8333rem !important;
  line-height: 1 !important;
  font-weight: 600 !important;
  letter-spacing: 0 !important;
}

:global(.calendar-popup .drp-day:hover:not(:disabled)) {
  background: #edf4ff !important;
  color: #2563eb !important;
}

:global(.calendar-popup .drp-day.bg-blue-600),
:global(.calendar-popup .drp-day.bg-red-500) {
  color: #fff !important;
  background: #2563eb !important;
  border-radius: 0.5556rem !important;
}

:global(.calendar-popup .drp-day.bg-red-500) {
  background: #ef4444 !important;
}

:global(.calendar-popup .drp-day.bg-blue-100) {
  background: #dbeafe !important;
  color: #2563eb !important;
}

:global(.calendar-popup .drp-day.text-gray-300) {
  color: #c9cfd8 !important;
}

:global(.calendar-popup .drp-fields) {
  gap: 0.6944rem !important;
  margin-top: 1.1111rem !important;
  padding-top: 0.8333rem !important;
  border-top: 1px solid #eef0f3 !important;
  align-items: end !important;
}

:global(.calendar-popup .drp-label) {
  margin: 0 0 0.4167rem !important;
  color: #6b7280 !important;
  font-size: 0.7639rem !important;
  line-height: 1 !important;
  font-weight: 600 !important;
  letter-spacing: 0 !important;
  text-transform: none !important;
}

:global(.calendar-popup .drp-input) {
  height: 2.6389rem !important;
  padding: 0 0.8333rem !important;
  border: 1px solid #d9dee6 !important;
  border-radius: 0.6944rem !important;
  background: #fff !important;
  color: #374151 !important;
  font-size: 0.8333rem !important;
  line-height: 1 !important;
  font-weight: 600 !important;
  letter-spacing: 0 !important;
  box-shadow: none !important;
}

:global(.calendar-popup .drp-input:focus) {
  border-color: #2563eb !important;
  box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.1) !important;
}

:global(.calendar-popup .drp-fields > .text-gray-400) {
  padding-bottom: 0.6944rem !important;
  color: #9ca3af !important;
  font-size: 1.1111rem !important;
}

:global(.calendar-popup .drp-apply) {
  height: 2.6389rem !important;
  min-height: 2.6389rem !important;
  margin: 0 !important;
  padding: 0 1.25rem !important;
  border-radius: 0.625rem !important;
  background: #2563eb !important;
  color: #fff !important;
  font-size: 0.8333rem !important;
  line-height: 1 !important;
  font-weight: 600 !important;
}

:global(.calendar-popup .drp-apply:hover) {
  background: #1d4ed8 !important;
}

:global(html.dark .calendar-popup),
:global(html.darkmode .calendar-popup) {
  border-color: rgba(255, 255, 255, 0.1) !important;
  background: #2c2f3d !important;
  box-shadow: 0 20px 54px rgba(0, 0, 0, 0.34) !important;
}

:global(html.dark .calendar-popup .drp-quick-row),
:global(html.darkmode .calendar-popup .drp-quick-row),
:global(html.dark .calendar-popup .drp-fields),
:global(html.darkmode .calendar-popup .drp-fields) {
  border-color: rgba(255, 255, 255, 0.1) !important;
}

:global(html.dark .calendar-popup .drp-quick),
:global(html.darkmode .calendar-popup .drp-quick) {
  background: rgba(255, 255, 255, 0.06) !important;
  color: rgba(255, 255, 255, 0.72) !important;
}

:global(html.dark .calendar-popup .drp-quick:hover),
:global(html.darkmode .calendar-popup .drp-quick:hover),
:global(html.dark .calendar-popup .drp-quick.text-blue-600),
:global(html.darkmode .calendar-popup .drp-quick.text-blue-600) {
  border-color: rgba(74, 122, 255, 0.28) !important;
  background: rgba(74, 122, 255, 0.14) !important;
  color: #8fb0ff !important;
}

:global(html.dark .calendar-popup .drp-month-head h3),
:global(html.darkmode .calendar-popup .drp-month-head h3) {
  color: #f8fafc !important;
}

:global(html.dark .calendar-popup .drp-nav),
:global(html.darkmode .calendar-popup .drp-nav),
:global(html.dark .calendar-popup .drp-weekday),
:global(html.darkmode .calendar-popup .drp-weekday),
:global(html.dark .calendar-popup .drp-label),
:global(html.darkmode .calendar-popup .drp-label),
:global(html.dark .calendar-popup .drp-fields > .text-gray-400),
:global(html.darkmode .calendar-popup .drp-fields > .text-gray-400) {
  color: rgba(255, 255, 255, 0.58) !important;
}

:global(html.dark .calendar-popup .drp-nav:hover),
:global(html.darkmode .calendar-popup .drp-nav:hover),
:global(html.dark .calendar-popup .drp-day:hover:not(:disabled)),
:global(html.darkmode .calendar-popup .drp-day:hover:not(:disabled)) {
  background: rgba(74, 122, 255, 0.14) !important;
  color: #8fb0ff !important;
}

:global(html.dark .calendar-popup .drp-day),
:global(html.darkmode .calendar-popup .drp-day) {
  color: rgba(255, 255, 255, 0.82) !important;
}

:global(html.dark .calendar-popup .drp-day.text-gray-300),
:global(html.darkmode .calendar-popup .drp-day.text-gray-300) {
  color: rgba(255, 255, 255, 0.24) !important;
}

:global(html.dark .calendar-popup .drp-day.bg-blue-100),
:global(html.darkmode .calendar-popup .drp-day.bg-blue-100) {
  background: rgba(74, 122, 255, 0.18) !important;
  color: #8fb0ff !important;
}

:global(html.dark .calendar-popup .drp-input),
:global(html.darkmode .calendar-popup .drp-input) {
  border-color: rgba(255, 255, 255, 0.12) !important;
  background: #232637 !important;
  color: rgba(255, 255, 255, 0.84) !important;
}

@media (max-width: 480px) {
  :global(.calendar-popup) {
    width: min(22.2222rem, calc(100vw - 1.1111rem)) !important;
    max-height: calc(100vh - 1.1111rem);
    padding: 0.9722rem !important;
  }

  :global(.calendar-popup .drp-quick-row) {
    gap: 0.4167rem !important;
    margin-bottom: 0.8333rem !important;
    padding-bottom: 0.6944rem !important;
  }

  :global(.calendar-popup .drp-quick) {
    height: 1.9444rem !important;
    padding: 0 0.5556rem !important;
    font-size: 0.7639rem !important;
  }

  :global(.calendar-popup .drp-month-grid) {
    grid-template-columns: 1fr !important;
    gap: 1.1111rem !important;
  }

  :global(.calendar-popup .drp-month-head h3) {
    font-size: 1.0417rem !important;
  }

  :global(.calendar-popup .drp-weekdays),
  :global(.calendar-popup .drp-days) {
    gap: 0.2778rem !important;
  }

  :global(.calendar-popup .drp-day) {
    width: 2.3611rem !important;
    height: 2.3611rem !important;
    min-height: 2.3611rem !important;
    font-size: 0.8333rem !important;
    border-radius: 0.5556rem !important;
  }

  :global(.calendar-popup .drp-weekday) {
    font-size: 0.6944rem !important;
    line-height: 1.3889rem !important;
  }

  :global(.calendar-popup .drp-fields) {
    display: grid !important;
    grid-template-columns: 1fr !important;
    gap: 0.5556rem !important;
    margin-top: 0.9722rem !important;
    padding-top: 0.8333rem !important;
  }

  :global(.calendar-popup .drp-fields > .text-gray-400) {
    display: none !important;
  }

  :global(.calendar-popup .drp-label) {
    font-size: 0.7639rem !important;
  }

  :global(.calendar-popup .drp-input) {
    height: 2.6389rem !important;
    font-size: 0.8333rem !important;
  }

  :global(.calendar-popup .drp-apply) {
    width: 100% !important;
    height: 2.6389rem !important;
    margin-top: 0.2778rem !important;
    font-size: 0.8333rem !important;
  }
}

.sync-btn {
  display: inline-flex;
  align-items: center;
  gap: 1rem;
  min-height: 4.6rem;
  padding: 0 1.4rem;
  border: 0;
  background: transparent;
  color: #b3b3b3;
  font-size: 1.3rem;
  font-weight: 500;
}

.sync-btn-blue {
  background: #2563eb;
  color: #fff;
  border-radius: 1.2rem;
  padding: 0 2rem;
}

.sync-btn-blue:hover:not(:disabled) {
  background: #1d4ed8;
}

.nds-check-wrap {
  display: inline-flex;
  align-items: center;
  gap: 0.8rem;
  cursor: pointer;
  user-select: none;
}

.nds-checkbox {
  appearance: none;
  -webkit-appearance: none;
  width: 1.25rem;
  height: 1.25rem;
  border: 2px solid #d1d5db;
  border-radius: 0.2778rem;
  background: #fff;
  cursor: pointer;
  flex-shrink: 0;
  transition: background 0.15s, border-color 0.15s;
}

.nds-checkbox:checked {
  background-color: #2563eb;
  border-color: #2563eb;
  background-image: url("data:image/svg+xml,%3csvg viewBox='0 0 16 16' fill='white' xmlns='http://www.w3.org/2000/svg'%3e%3cpath d='M12.207 4.793a1 1 0 010 1.414l-5 5a1 1 0 01-1.414 0l-2-2a1 1 0 011.414-1.414L6.5 9.086l4.293-4.293a1 1 0 011.414 0z'/%3e%3c/svg%3e");
  background-size: 0.8333rem 0.8333rem;
  background-repeat: no-repeat;
  background-position: center;
}

.nds-label {
  font-size: 1.3rem;
  font-weight: 500;
  color: #374151;
  white-space: nowrap;
}

.report-icons-row {
  gap: 1.2rem;
  margin-top: 2rem;
}

.report-icon-btn {
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  border-radius: 69.375rem;
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.report-icon-btn:hover {
  opacity: 0.92;
  transform: translateY(-0.0694rem);
}

.report-icon-btn:hover .report-icon-circle {
  box-shadow: 0 10px 22px rgba(37, 99, 235, 0.12);
  transform: scale(1.04);
}

.report-icon-btn.active .report-icon-circle {
  background: linear-gradient(135deg, #2f6df6 0%, #14b8d5 100%);
  color: #fff;
  box-shadow: none;
}

.report-icon-circle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 4.6rem;
  height: 4.6rem;
  border-radius: 69.375rem;
  background: var(--report-bg, #f3f5f7);
  color: #9a9a9a;
  transition: background 0.2s ease, color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
  line-height: 0;
}

.report-icon-circle svg {
  display: block;
  width: 1.8rem;
  height: 1.8rem;
  flex: 0 0 auto;
}

.report-mask-icon {
  display: block;
  width: 1.8rem;
  height: 1.8rem;
  background: currentColor;
  flex: 0 0 auto;
  transition: transform 0.2s ease;
}

.telegram-icon {
  width: 1.44rem;
  height: 1.44rem;
  transform: translate(-0.14rem, 0.06rem);
  -webkit-mask: url("data:image/svg+xml,%3Csvg width='21' height='21' viewBox='0 0 21 21' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M18.42 3.05 2.54 9.17c-1.08.43-1.07 1.03-.2 1.3l4.08 1.27 1.56 4.79c.2.55.1.77.68.77.45 0 .65-.2.9-.45l2.16-2.1 4.5 3.32c.83.46 1.43.22 1.64-.77l2.97-13.98c.3-1.22-.47-1.77-1.41-1.27ZM6.95 11.45l9.47-5.97c.47-.28.9-.13.55.18l-8.1 7.3-.31 3.31-1.61-4.82Z' fill='black'/%3E%3C/svg%3E") center / contain no-repeat;
  mask: url("data:image/svg+xml,%3Csvg width='21' height='21' viewBox='0 0 21 21' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M18.42 3.05 2.54 9.17c-1.08.43-1.07 1.03-.2 1.3l4.08 1.27 1.56 4.79c.2.55.1.77.68.77.45 0 .65-.2.9-.45l2.16-2.1 4.5 3.32c.83.46 1.43.22 1.64-.77l2.97-13.98c.3-1.22-.47-1.77-1.41-1.27ZM6.95 11.45l9.47-5.97c.47-.28.9-.13.55.18l-8.1 7.3-.31 3.31-1.61-4.82Z' fill='black'/%3E%3C/svg%3E") center / contain no-repeat;
}

.email-icon {
  width: 2rem;
  height: 1.48rem;
  -webkit-mask: url("data:image/svg+xml,%3Csvg width='26' height='19' viewBox='0 0 26 19' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M2.25 0H23.14C24.38 0 25.39 1.01 25.39 2.25V16.56C25.39 17.8 24.38 18.81 23.14 18.81H2.25C1.01 18.81 0 17.8 0 16.56V2.25C0 1.01 1.01 0 2.25 0ZM2.12 2.52V16.3C2.12 16.55 2.32 16.75 2.57 16.75H22.82C23.07 16.75 23.27 16.55 23.27 16.3V2.52L13.56 10.4C13.06 10.81 12.33 10.81 11.83 10.4L2.12 2.52ZM21.02 2.06H4.36L12.69 8.8L21.02 2.06Z' fill='black'/%3E%3C/svg%3E") center / contain no-repeat;
  mask: url("data:image/svg+xml,%3Csvg width='26' height='19' viewBox='0 0 26 19' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M2.25 0H23.14C24.38 0 25.39 1.01 25.39 2.25V16.56C25.39 17.8 24.38 18.81 23.14 18.81H2.25C1.01 18.81 0 17.8 0 16.56V2.25C0 1.01 1.01 0 2.25 0ZM2.12 2.52V16.3C2.12 16.55 2.32 16.75 2.57 16.75H22.82C23.07 16.75 23.27 16.55 23.27 16.3V2.52L13.56 10.4C13.06 10.81 12.33 10.81 11.83 10.4L2.12 2.52ZM21.02 2.06H4.36L12.69 8.8L21.02 2.06Z' fill='black'/%3E%3C/svg%3E") center / contain no-repeat;
}

.max-icon {
  width: 1.75rem;
  height: 1.75rem;
  -webkit-mask: url("data:image/svg+xml,%3Csvg width='23' height='23' viewBox='0 0 23 23' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath fill-rule='evenodd' clip-rule='evenodd' d='M-1.75746 0.402423C-1.75483 2.155 -1.74827 3.53735 -1.74287 3.47433C-1.62835 2.13813 -1.05642 0.729807 -0.213224 -0.292158C0.271161 -0.879273 0.899602 -1.42898 1.51662 -1.80529C2.38365 -2.33405 3.24308 -2.62429 4.35797 -2.76478C4.40461 -2.77065 3.04667 -2.77741 1.34028 -2.77976L-1.76221 -2.78406L-1.75746 0.402423ZM19.2414 -2.76461C20.4922 -2.63472 21.664 -2.17099 22.6902 -1.39976C23.0356 -1.14018 23.7533 -0.412972 24.0095 -0.0630181C24.7695 0.97513 25.2285 2.166 25.3566 3.43137C25.3621 3.48651 25.3687 2.11061 25.3712 0.37378L25.3757 -2.78406L22.2591 -2.77947C20.545 -2.77695 19.187 -2.77025 19.2414 -2.76461ZM11.3262 0.526703C9.97595 0.644538 9.03042 0.858842 7.96223 1.28911C4.58971 2.64757 2.17288 5.63667 1.5882 9.17233C1.46913 9.89246 1.44765 10.1918 1.45045 11.0932C1.45635 13.0195 1.63889 14.1725 2.40714 17.1368C2.76373 18.5127 2.9304 19.5394 2.9304 20.3602C2.9304 20.9016 3.20825 21.2516 3.73877 21.3784C4.01264 21.4438 4.54202 21.4188 4.92334 21.3224C5.78836 21.1037 6.61078 20.6623 7.15586 20.1242C7.29619 19.9857 7.41359 19.8723 7.41673 19.8723C7.41989 19.8722 7.5789 19.9796 7.77008 20.111C9.10923 21.0308 9.9351 21.2986 11.5948 21.3512C14.4847 21.4427 17.1617 20.3757 19.1852 18.3258C21.6244 15.8548 22.6485 12.3498 21.9555 8.84481C21.5449 6.76834 20.5412 4.89959 19.0401 3.41648C17.4445 1.83999 15.5146 0.897223 13.2626 0.59407C12.8572 0.539506 11.6576 0.497774 11.3262 0.526703ZM11.3121 5.65698C10.2161 5.75895 9.1042 6.28998 8.31739 7.08719C7.04926 8.37209 6.45516 10.2727 6.57709 12.6546C6.64454 13.9728 6.86458 15.0956 7.19728 15.8193C7.32036 16.087 7.42922 16.2273 7.55541 16.2807C7.68149 16.3341 7.8597 16.2766 8.13184 16.0949C8.35149 15.9482 8.82063 15.5607 8.96161 15.4096L9.04223 15.3231L9.21603 15.4376C9.47259 15.6068 10.0304 15.8764 10.3364 15.9792C11.3635 16.3241 12.443 16.3182 13.4976 15.9618C14.3646 15.6688 15.2018 15.1074 15.7963 14.4203C16.7195 13.3535 17.208 11.9255 17.0986 10.6135C17.0368 9.87193 16.8818 9.29636 16.5722 8.65863C15.7542 6.97365 14.1951 5.87211 12.3379 5.66715C12.0796 5.63862 11.5643 5.63352 11.3121 5.65698ZM-1.75768 21.4976L-1.76221 24.7128L1.41095 24.708C3.15621 24.7053 4.53323 24.6986 4.47104 24.6931C2.08208 24.4819 -0.0147773 23.0384 -1.05509 20.889C-1.44642 20.0805 -1.65391 19.3252 -1.74361 18.3828C-1.74886 18.3276 -1.7552 19.7293 -1.75768 21.4976ZM25.3475 18.5231C25.3475 18.5846 25.3218 18.7876 25.2904 18.9743C25.1057 20.073 24.68 21.0758 24.0095 21.9917C23.7533 22.3417 23.0356 23.0689 22.6902 23.3285C21.6625 24.1008 20.4941 24.5632 19.2414 24.6933C19.187 24.699 20.545 24.7057 22.2591 24.7082L25.3757 24.7128V21.5621C25.3757 19.8292 25.3694 18.4114 25.3616 18.4114C25.3538 18.4114 25.3475 18.4617 25.3475 18.5231Z' fill='black'/%3E%3C/svg%3E") center / contain no-repeat;
  mask: url("data:image/svg+xml,%3Csvg width='23' height='23' viewBox='0 0 23 23' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath fill-rule='evenodd' clip-rule='evenodd' d='M-1.75746 0.402423C-1.75483 2.155 -1.74827 3.53735 -1.74287 3.47433C-1.62835 2.13813 -1.05642 0.729807 -0.213224 -0.292158C0.271161 -0.879273 0.899602 -1.42898 1.51662 -1.80529C2.38365 -2.33405 3.24308 -2.62429 4.35797 -2.76478C4.40461 -2.77065 3.04667 -2.77741 1.34028 -2.77976L-1.76221 -2.78406L-1.75746 0.402423ZM19.2414 -2.76461C20.4922 -2.63472 21.664 -2.17099 22.6902 -1.39976C23.0356 -1.14018 23.7533 -0.412972 24.0095 -0.0630181C24.7695 0.97513 25.2285 2.166 25.3566 3.43137C25.3621 3.48651 25.3687 2.11061 25.3712 0.37378L25.3757 -2.78406L22.2591 -2.77947C20.545 -2.77695 19.187 -2.77025 19.2414 -2.76461ZM11.3262 0.526703C9.97595 0.644538 9.03042 0.858842 7.96223 1.28911C4.58971 2.64757 2.17288 5.63667 1.5882 9.17233C1.46913 9.89246 1.44765 10.1918 1.45045 11.0932C1.45635 13.0195 1.63889 14.1725 2.40714 17.1368C2.76373 18.5127 2.9304 19.5394 2.9304 20.3602C2.9304 20.9016 3.20825 21.2516 3.73877 21.3784C4.01264 21.4438 4.54202 21.4188 4.92334 21.3224C5.78836 21.1037 6.61078 20.6623 7.15586 20.1242C7.29619 19.9857 7.41359 19.8723 7.41673 19.8723C7.41989 19.8722 7.5789 19.9796 7.77008 20.111C9.10923 21.0308 9.9351 21.2986 11.5948 21.3512C14.4847 21.4427 17.1617 20.3757 19.1852 18.3258C21.6244 15.8548 22.6485 12.3498 21.9555 8.84481C21.5449 6.76834 20.5412 4.89959 19.0401 3.41648C17.4445 1.83999 15.5146 0.897223 13.2626 0.59407C12.8572 0.539506 11.6576 0.497774 11.3262 0.526703ZM11.3121 5.65698C10.2161 5.75895 9.1042 6.28998 8.31739 7.08719C7.04926 8.37209 6.45516 10.2727 6.57709 12.6546C6.64454 13.9728 6.86458 15.0956 7.19728 15.8193C7.32036 16.087 7.42922 16.2273 7.55541 16.2807C7.68149 16.3341 7.8597 16.2766 8.13184 16.0949C8.35149 15.9482 8.82063 15.5607 8.96161 15.4096L9.04223 15.3231L9.21603 15.4376C9.47259 15.6068 10.0304 15.8764 10.3364 15.9792C11.3635 16.3241 12.443 16.3182 13.4976 15.9618C14.3646 15.6688 15.2018 15.1074 15.7963 14.4203C16.7195 13.3535 17.208 11.9255 17.0986 10.6135C17.0368 9.87193 16.8818 9.29636 16.5722 8.65863C15.7542 6.97365 14.1951 5.87211 12.3379 5.66715C12.0796 5.63862 11.5643 5.63352 11.3121 5.65698ZM-1.75768 21.4976L-1.76221 24.7128L1.41095 24.708C3.15621 24.7053 4.53323 24.6986 4.47104 24.6931C2.08208 24.4819 -0.0147773 23.0384 -1.05509 20.889C-1.44642 20.0805 -1.65391 19.3252 -1.74361 18.3828C-1.74886 18.3276 -1.7552 19.7293 -1.75768 21.4976ZM25.3475 18.5231C25.3475 18.5846 25.3218 18.7876 25.2904 18.9743C25.1057 20.073 24.68 21.0758 24.0095 21.9917C23.7533 22.3417 23.0356 23.0689 22.6902 23.3285C21.6625 24.1008 20.4941 24.5632 19.2414 24.6933C19.187 24.699 20.545 24.7057 22.2591 24.7082L25.3757 24.7128V21.5621C25.3757 19.8292 25.3694 18.4114 25.3616 18.4114C25.3538 18.4114 25.3475 18.4617 25.3475 18.5231Z' fill='black'/%3E%3C/svg%3E") center / contain no-repeat;
}

.sync-btn svg.spinning {
  animation: dashboard-spin 1s linear infinite;
}

@keyframes dashboard-spin {
  to {
    transform: rotate(360deg);
  }
}

.ml-auto {
  margin-left: auto;
}

.export-btn {
  min-width: 16rem;
  border: 0;
  background: #2563eb;
  color: #fff;
}

.dropdown-panel {
  position: absolute;
  top: calc(100% + 0.8rem);
  left: 0;
  z-index: 30;
  min-width: 22rem;
  padding: 1rem;
  border: 1px solid #ebebeb;
  border-radius: 1.2rem;
  background: #fff;
  box-shadow: 0 2rem 6rem rgba(15, 23, 42, 0.12);
}

.dropdown-panel.export {
  right: 0;
  left: auto;
}

.dropdown-panel button {
  display: flex;
  align-items: center;
  gap: 1rem;
  width: 100%;
  padding: 1rem;
  border: 0;
  border-radius: 0.8rem;
  background: transparent;
  color: #4b4b4b;
  font-size: 1.3rem;
  text-align: left;
}

.dropdown-panel button:hover {
  background: #f7f9ff;
}

.dropdown-panel button svg {
  width: 1.6rem;
  height: 1.6rem;
}

.campaigns {
  min-width: 36rem;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 1rem;
  height: 4.4rem;
  margin-bottom: 0.8rem;
  padding: 0 1.2rem;
  border: 1px solid #ebebeb;
  border-radius: 1rem;
}

.search-box svg {
  width: 1.8rem;
  height: 1.8rem;
  color: #b3b3b3;
}

.search-box input {
  width: 100%;
  border: 0;
  outline: 0;
  color: #4b4b4b;
  font-size: 1.3rem;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  grid-auto-rows: 10.4rem;
  gap: 2rem;
  margin-top: 3rem;
}

.metric-card {
  padding: 2.5rem;
  border-radius: 1.5rem;
  background: #fff;
  display: flex;
  align-items: center;
  border: 2px solid transparent;
  overflow: hidden;
}
.metric-card.metric-card--add {
  background: transparent;
  border-style: dashed;
  border-color: #d1d5db;
  overflow: visible;
}

.metric-head {
  display: flex;
  align-items: center;
  gap: 2rem;
  width: 100%;
}

.metric-icon {
  display: grid;
  place-items: center;
  width: 5.2rem;
  height: 5.2rem;
  border-radius: 1.2rem;
  background: #f6f6f6;
  color: #2563eb;
}

.metric-icon svg,
.round-action svg,
.ai-title svg {
  width: 2rem;
  height: 2rem;
}

.metric-text {
  flex: 1;
  min-width: 0;
}

.metric-card h3 {
  margin: 0;
  font-size: 1.3rem;
  font-weight: 500;
  color: #ababab;
  line-height: 1;
}

.metric-card p {
  margin: 1.4rem 0 0;
  color: #ababab;
  font-size: 1.3rem;
}

.round-action {
  display: grid;
  place-items: center;
  width: 4rem;
  height: 4rem;
  border: 1px solid #ebebeb;
  border-radius: 69.375rem;
  background: #fff;
  color: #b3b3b3;
}

.metric-card strong {
  display: block;
  margin-top: 0.6rem;
  font-size: 2.6rem;
  font-weight: 700;
  line-height: 1;
}

.metric-card--add {
  background: transparent;
  border: 2px dashed #d1d5db;
  cursor: pointer;
  justify-content: center;
  align-items: center;
  color: #c3c3c3;
  position: relative;
  transition: border-color 0.2s, background 0.2s, color 0.2s;
  user-select: none;
}
.metric-card--add:hover {
  border-color: #2563eb;
  background: #f0f5ff;
  color: #2563eb;
}
.add-card-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  pointer-events: none;
}
.add-card-inner span {
  font-size: 1.1rem;
  font-weight: 500;
  line-height: 1;
}
.placeholder-plus {
  width: 2rem;
  height: 2rem;
}
.add-card-dropdown {
  position: absolute;
  bottom: calc(100% + 0.8rem);
  left: 50%;
  transform: translateX(-50%);
  background: #fff;
  border: 1px solid #ebebeb;
  border-radius: 1.2rem;
  box-shadow: 0 4px 24px rgba(0,0,0,0.10);
  padding: 0.6rem;
  min-width: 20rem;
  z-index: 100;
}
.add-card-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  width: 100%;
  padding: 0.8rem 1.2rem;
  border: none;
  background: transparent;
  border-radius: 0.8rem;
  cursor: pointer;
  font-size: 1.3rem;
  color: #374151;
  text-align: left;
  transition: background 0.15s, color 0.15s;
}
.add-card-item:hover {
  background: #f0f5ff;
  color: #2563eb;
}
.add-card-icon {
  width: 1.6rem;
  height: 1.6rem;
  flex-shrink: 0;
}
.drag-handle {
  cursor: grab;
  user-select: none;
}
.drag-handle:active {
  cursor: grabbing;
}
.card-delete-btn {
  opacity: 0;
  display: grid;
  place-items: center;
  width: 2.6rem;
  height: 2.6rem;
  border-radius: 50%;
  background: transparent;
  border: none;
  color: #b3b3b3;
  cursor: pointer;
  flex-shrink: 0;
  transition: opacity 0.15s, background 0.15s, color 0.15s;
}
.metric-card:hover .card-delete-btn {
  opacity: 1;
}
.card-delete-btn:hover {
  background: #fee2e2;
  color: #ef4444;
}
.card-delete-btn svg,
.trend-icon {
  width: 1.4rem;
  height: 1.4rem;
  flex-shrink: 0;
}
.trend {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.metric-foot {
  display: flex;
  align-items: center;
  gap: 2.5rem;
  margin-top: 3.5rem;
  color: #7e7e7e;
  font-size: 1.5rem;
}

.trend {
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  height: 3.5rem;
  padding: 0 1rem;
  border-radius: 0.4rem;
  background: #e5fbea;
  color: #18b44d;
  font-weight: 700;
  flex-shrink: 0;
  white-space: nowrap;
}

.trend.negative {
  background: #fef2f2;
  color: #ef4444;
}

.chart-goals-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 63.2rem;
  gap: 2rem;
  margin-top: 2rem;
}

.chart-panel,
.goals-panel {
  min-height: 38.2rem;
  padding: 3rem;
}

.panel-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 2rem;
}

.month-select,
.see-all {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  height: 3.5rem;
  padding: 0 1.7rem;
  border: 1px solid #ebebeb;
  border-radius: 1.2rem;
  background: #fff;
  color: #b3b3b3;
  font-size: 1.3rem;
}

.chart-period-select {
  min-width: 12.4rem;
}

.chart-period-select .month-select {
  width: 100%;
}

.chart-period-select .cs-list {
  right: 0;
  left: auto;
  min-width: 15rem;
}

.chart-period-select .cs-arrow {
  width: 2.4rem;
  height: 2.4rem;
}

.chart-period-select .cs-arrow svg {
  width: 1.2rem;
  height: 1.2rem;
}

.chart-area {
  height: 29rem;
  margin-top: 2.8rem;
}

.chart-area svg {
  width: 100%;
  height: 100%;
  overflow: visible;
}

.grid-lines line {
  stroke: #f0f1f4;
  stroke-width: 1;
}

.chart-fill {
  fill: url(#lineFill);
}

.chart-line {
  fill: none;
  stroke: #2563eb;
  stroke-width: 2.4;
  stroke-linejoin: round;
  stroke-linecap: round;
}

.chart-area circle {
  fill: #2563eb;
  stroke: #fff;
  stroke-width: 1.5;
}

.axis-labels text {
  fill: rgba(43, 48, 52, 0.4);
  font-size: 1.1rem;
}

.tooltip-pin rect {
  fill: #2563eb;
}

.tooltip-pin text {
  fill: #fff;
  font-size: 1.1rem;
  font-weight: 700;
  text-anchor: middle;
}

.goals-content {
  display: grid;
  grid-template-columns: 27.5rem 1fr;
  gap: 3rem;
  align-items: center;
  margin-top: 2.5rem;
}

.donut-wrap {
  position: relative;
  display: grid;
  place-items: center;
  width: 27.5rem;
  height: 27.5rem;
}

.donut {
  width: 100%;
  height: 100%;
  border-radius: 69.375rem;
  background: conic-gradient(#3f63f6 0 52%, #f39a72 52% 78%, #6ee7b7 78% 100%);
  -webkit-mask: radial-gradient(circle, transparent 0 34%, #000 35%);
  mask: radial-gradient(circle, transparent 0 34%, #000 35%);
}

.donut-wrap::after {
  content: '';
  position: absolute;
  width: 13.4rem;
  height: 13.4rem;
  border-radius: 69.375rem;
  background: #fff;
}

.donut-wrap span {
  position: absolute;
  z-index: 2;
  font-size: 1.8rem;
  font-weight: 700;
}

.goals-list {
  display: grid;
  gap: 2rem;
}

.goal-item {
  overflow: hidden;
  border: 1px solid transparent;
  border-radius: 0.8rem;
}

.goal-item div {
  display: flex;
  align-items: center;
  gap: 1.3rem;
  min-height: 4.1rem;
  padding: 0 1.6rem;
  font-size: 1.3rem;
}

.goal-item div span {
  width: 0.9rem;
  height: 0.9rem;
  border-radius: 69.375rem;
}

.goal-item p {
  margin: 0;
  padding: 1.4rem 1.6rem;
  color: #4b4b4b;
  font-size: 1.3rem;
}

.campaigns-panel {
  margin-top: 2rem;
  padding: 3rem;
}

.see-all {
  color: #2563eb;
}

.campaign-table {
  display: grid;
  gap: 1.5rem;
  margin-top: 2.5rem;
  overflow-x: auto;
}

.campaign-row {
  display: grid;
  grid-template-columns: minmax(28rem, 2.3fr) repeat(6, minmax(10rem, 1fr));
  align-items: center;
  min-width: 128rem;
  min-height: 5.6rem;
  padding: 0 2.5rem;
  border-radius: 1rem;
  color: #4b4b4b;
  font-size: 1.3rem;
}

.campaign-row.header {
  min-height: auto;
  color: #b3b3b3;
  background: transparent;
}

.campaign-row.orange {
  background: #fff4ee;
}

.campaign-row.green {
  background: #eafcf0;
}

.campaign-row.blue {
  background: #e8eefc;
}

.campaign-row b {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  margin-left: 0.8rem;
  padding: 0.4rem 0.6rem;
  border-radius: 0.4rem;
  background: #fff;
  color: #0fa84a;
  font-size: 0.9rem;
  font-weight: 700;
}

.campaign-row b.negative {
  color: #f02d2d;
}

.campaign-row b svg {
  display: block;
  width: 1rem;
  height: 1rem;
  flex: 0 0 auto;
}

.bottom-grid {
  display: grid;
  grid-template-columns: 67.1rem minmax(42rem, 1fr) 33.3rem;
  gap: 2rem;
  margin-top: 2rem;
}

.creatives-panel,
.ai-panel {
  min-height: 40.4rem;
  padding: 3rem;
}

.creatives-row {
  display: flex;
  gap: 1.3rem;
  margin-top: 2.5rem;
  overflow-x: auto;
}

.creative-card {
  flex: 0 0 19.5rem;
}

.creative-image {
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-height: 19rem;
  padding: 1.6rem;
  border-radius: 2rem;
  overflow: hidden;
  color: #fff;
  background: linear-gradient(135deg, #38bdf8, #2563eb);
  background-position: center;
  background-size: cover;
}

.creative-image.city {
  background: linear-gradient(rgba(37, 99, 235, 0.2), rgba(37, 99, 235, 0.42)), linear-gradient(135deg, #dbeafe, #60a5fa 52%, #2563eb);
}

.creative-image.blue {
  background: radial-gradient(circle at 80% 70%, #1e3a8a 0 18%, transparent 19%), linear-gradient(135deg, #38bdf8, #2563eb);
}

.creative-image.house {
  background: linear-gradient(135deg, #93c5fd, #1d4ed8 65%);
}

.creative-image span {
  font-size: 1rem;
  font-weight: 700;
  text-transform: uppercase;
}

.creative-image strong {
  margin-top: 1rem;
  font-size: 1.7rem;
  line-height: 1.05;
}

.creative-card p {
  margin: 2rem 0 0.8rem;
  color: #4b4b4b;
  font-size: 1.3rem;
}

.creative-card em {
  display: block;
  color: #ababab;
  font-size: 1.3rem;
  font-style: normal;
  line-height: 1.35;
}

.ai-title {
  display: flex;
  align-items: center;
  gap: 2rem;
}

.ai-title span {
  display: grid;
  place-items: center;
  width: 3.6rem;
  height: 3.6rem;
  border-radius: 0.8rem;
  background: #f6f6f6;
  color: #2563eb;
}

.ai-panel ul {
  display: grid;
  gap: 2rem;
  margin: 2.4rem 0 0;
  padding-left: 2.2rem;
  color: #4b4b4b;
  font-size: 1.5rem;
  line-height: 1.35;
}

.ai-panel > p {
  margin: 2.8rem 0 0;
  color: #ababab;
  font-size: 1.5rem;
  line-height: 1.35;
}

.side-stat-stack {
  display: grid;
  gap: 2rem;
}

.mini-stat-panel {
  min-height: 19.2rem;
  padding: 3rem;
}

.mini-stat-panel h2 {
  margin-bottom: 2.5rem;
}

.progress-line {
  display: grid;
  grid-template-columns: minmax(8rem, 1fr) 10rem 4.4rem;
  gap: 1rem;
  align-items: center;
  margin-top: 1.8rem;
  color: #4b4b4b;
  font-size: 1.5rem;
}

.progress-line span {
  display: inline-flex;
  align-items: center;
  gap: 0.9rem;
  min-width: 0;
}

.progress-line span svg {
  width: 1.5rem;
  height: 1.5rem;
  color: #2563eb;
}

.progress-line div {
  height: 0.5rem;
  border-radius: 69.375rem;
  background: #e9e9e9;
  overflow: hidden;
}

.progress-line i {
  display: block;
  height: 100%;
  border-radius: 69.375rem;
  background: #2563eb;
}

.progress-line b {
  font-weight: 400;
  text-align: right;
}

.place-dot {
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 69.375rem;
  background: #ef4444;
}

.progress-line span.placement-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0;
  min-width: 2rem;
  width: 2rem;
  height: 2rem;
  border-radius: 69.375rem;
  flex: 0 0 auto;
  line-height: 0;
}
.placement-icon--search {
  background: #fff4e5;
}
.placement-icon--rsya {
  background: #fff4e5;
  padding: 0.3rem;
}
.progress-line .placement-icon svg {
  display: block;
  width: 1.1rem;
  height: 1.1rem;
  color: #f59e0b;
}
.placement-icon-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

@media (max-width: 1125px) {
  .top-grid,
  .panel-reports,
  .chart-goals-grid,
  .bottom-grid {
    grid-template-columns: 1fr;
  }

  .kpi-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .goals-content {
    grid-template-columns: 27.5rem 1fr;
  }
}

@media (max-width: 615px) {
  .figma-dashboard {
    padding-top: 2rem;
  }

  .kpi-grid {
    grid-template-columns: 1fr;
  }

  .metric-card {
    min-height: 18rem;
  }

  .goals-content {
    grid-template-columns: 1fr;
  }

  .donut-wrap {
    width: 22rem;
    height: 22rem;
  }

  .filters-row > *,
  .filters-row .filter-btn,
  .export-btn,
  .date-btn,
  .dashboard-date-picker {
    flex-basis: auto;
    max-width: none;
    width: 100%;
  }

  .sync-status-label,
  .nds-check-wrap,
  .filter-right-group {
    width: 100%;
    margin-left: 0;
  }

  .filter-right-group {
    flex-wrap: wrap;
  }

  .ml-auto {
    margin-left: 0;
  }

  .campaign-row {
    min-width: 120rem;
  }
}

/* Project-scale overrides: this app's mockup pages use px-based density. */
.figma-dashboard {
  position: relative;
  z-index: 2;
  display: flex;
  min-height: 100%;
  width: 100%;
  max-width: none;
  flex-direction: column;
  margin: 0;
  padding: 2.0833rem 1.7361rem;
  overflow: hidden;
}

.panel {
  border-radius: 1.0417rem;
  box-shadow: none;
}

.top-grid {
  grid-template-columns: minmax(22.2222rem, 34.3056rem) minmax(0, 1fr);
  gap: 1.3889rem;
}

.panel-channels,
.panel-reports {
  min-height: 9.0972rem;
  padding: 1.7361rem;
}

.panel h2,
.panel-channels h2,
.panel-reports h2 {
  font-size: 1.3889rem;
}

.chips-row {
  gap: 1.0417rem;
  margin-top: 1.3889rem;
}

.chip {
  height: 3.1944rem;
  gap: 0.6944rem;
  padding: 0 1.0417rem;
  border-radius: 0.8333rem;
  font-size: 0.9028rem;
}

.chip-dot {
  width: 0.9722rem;
  height: 0.9722rem;
}

.chip-icon {
  width: 0.625rem;
  height: 0.625rem;
}

.panel-reports {
  grid-template-columns: minmax(19.4444rem, auto) minmax(10.0694rem, 12.1528rem) minmax(15.9722rem, 18.0556rem) auto;
  gap: 1.3889rem;
}

.report-schedule p {
  margin-bottom: 1.3889rem;
  font-size: 0.9028rem;
}

.select-like,
.filter-btn,
.export-btn {
  height: 3.1944rem;
  gap: 0.8333rem;
  padding: 0 1.0417rem;
  border-radius: 0.8333rem;
  font-size: 0.9028rem;
}

.dashboard-date-picker {
  flex-basis: auto;
  width: 17.7083rem;
}

.filter-right-group {
  gap: 1.1111rem;
}

.sync-status-label {
  gap: 0.4167rem;
  font-size: 0.9028rem;
}

.sync-status-label svg {
  width: 0.9722rem;
  height: 0.9722rem;
}

.select-like svg,
.filter-btn svg,
.export-btn svg,
.primary-report svg,
.sync-btn svg,
.see-all svg,
.month-select svg {
  width: 1.1111rem;
  height: 1.1111rem;
}

.primary-report {
  height: 3.1944rem;
  gap: 0.5556rem;
  padding: 0 0.6944rem;
  border-radius: 0.8333rem;
  font-size: 0.9028rem;
}

.heading-section {
  margin-top: 3.125rem;
}

.heading-section h1 {
  margin-bottom: 1.6667rem;
  font-size: 1.9444rem;
}

.filters-row {
  gap: 0.6944rem;
}

.filters-row .filter-btn {
  min-width: 9.7222rem;
}

.date-btn {
  min-width: 17.8472rem;
}

.sync-btn {
  min-height: 3.1944rem;
  gap: 0.6944rem;
  padding: 0 0.9722rem;
  font-size: 0.9028rem;
}

.sync-btn-blue {
  border-radius: 0.8333rem;
  padding: 0 1.25rem;
}

.nds-label {
  font-size: 0.9028rem;
}

.report-icon-circle {
  width: 3.1944rem;
  height: 3.1944rem;
}

.goal-item {
  border-radius: 0.5556rem;
}

.export-btn {
  min-width: 11.1111rem;
}

.dropdown-panel {
  top: calc(100% + 0.5556rem);
  min-width: 15.2778rem;
  padding: 0.6944rem;
  border-radius: 0.8333rem;
  box-shadow: 0 20px 60px rgba(15, 23, 42, 0.12);
}

.dropdown-panel button {
  gap: 0.6944rem;
  padding: 0.6944rem;
  border-radius: 0.5556rem;
  font-size: 0.9028rem;
}

.dropdown-panel button svg {
  width: 1.1111rem;
  height: 1.1111rem;
}

.campaigns {
  min-width: 25rem;
}

.search-box {
  gap: 0.6944rem;
  height: 3.0556rem;
  margin-bottom: 0.5556rem;
  padding: 0 0.8333rem;
  border-radius: 0.6944rem;
}

.search-box svg {
  width: 1.25rem;
  height: 1.25rem;
}

.search-box input {
  font-size: 0.9028rem;
}

.kpi-grid {
  gap: 1.0417rem;
  margin-top: 1.7361rem;
  grid-auto-rows: 6.1111rem;
}

.metric-card {
  padding: 1.3889rem 1.7361rem;
  border-radius: 1.0417rem;
  border: 2px solid transparent;
  overflow: hidden;
}
.metric-card.metric-card--add {
  border-style: dashed;
  border-color: #d1d5db;
  overflow: visible;
}

.metric-head {
  gap: 1.1111rem;
}

.metric-icon {
  width: 3.0556rem;
  height: 3.0556rem;
  border-radius: 0.6944rem;
}

.metric-icon svg,
.round-action svg,
.ai-title svg {
  width: 1.25rem;
  height: 1.25rem;
}

.metric-text {
  flex: 1;
  min-width: 0;
}

.metric-card h3 {
  font-size: 0.9028rem;
  color: #ababab;
}

.metric-card p {
  margin-top: 0.625rem;
  font-size: 0.8333rem;
}

.metric-card strong {
  margin-top: 0.3472rem;
  font-size: 1.6667rem;
}

.metric-foot {
  gap: 0.9722rem;
  margin-top: 1.3889rem;
  font-size: 0.9028rem;
}

.trend {
  height: 1.9444rem;
  gap: 0.3472rem;
  padding: 0 0.5556rem;
  border-radius: 0.2778rem;
  font-size: 0.9028rem;
  align-self: center;
}

.chart-goals-grid {
  grid-template-columns: minmax(0, 1.5fr) minmax(25rem, 0.9fr);
  gap: 1.3889rem;
  margin-top: 1.3889rem;
}

.chart-panel,
.goals-panel {
  min-height: 25rem;
  padding: 1.7361rem;
}

.panel-title-row {
  gap: 1.3889rem;
}

.month-select,
.see-all {
  height: 2.4306rem;
  gap: 0.6944rem;
  padding: 0 0.9722rem;
  border-radius: 0.8333rem;
  font-size: 0.9028rem;
}

.chart-area {
  height: 18.4028rem;
  margin-top: 1.6667rem;
}

.axis-labels text,
.tooltip-pin text {
  font-size: 0.7639rem;
}

.goals-content {
  grid-template-columns: minmax(12.5rem, 16.6667rem) minmax(0, 1fr);
  gap: 1.6667rem;
  margin-top: 1.6667rem;
}

.donut-wrap {
  width: 15.2778rem;
  height: 15.2778rem;
}

.donut-wrap::after {
  width: 7.2222rem;
  height: 7.2222rem;
}

.donut-wrap span {
  font-size: 1.1111rem;
}

.goals-list {
  gap: 1.0417rem;
}

.goal-item {
  border-radius: 0.5556rem;
}

.goal-item div {
  gap: 0.8333rem;
  min-height: 2.8472rem;
  padding: 0 1.1111rem;
  font-size: 0.9028rem;
}

.goal-item div span {
  width: 0.625rem;
  height: 0.625rem;
}

.goal-item p {
  padding: 0.8333rem 1.1111rem;
  font-size: 0.9028rem;
}

.campaigns-panel {
  margin-top: 1.3889rem;
  padding: 1.7361rem;
}

.campaign-table {
  gap: 0.8333rem;
  margin-top: 1.3889rem;
}

.campaign-row {
  grid-template-columns: minmax(18.0556rem, 2.1fr) repeat(6, minmax(7.2917rem, 1fr));
  min-width: 77.7778rem;
  min-height: 3.4722rem;
  padding: 0 1.3889rem;
  border-radius: 0.6944rem;
  font-size: 0.8333rem;
}

.campaign-row b {
  margin-left: 0.4167rem;
  padding: 0.2083rem 0.3472rem;
  font-size: 0.625rem;
}

.campaign-row b svg {
  width: 0.6944rem;
  height: 0.6944rem;
}

.bottom-grid {
  grid-template-columns: minmax(29.8611rem, 0.95fr) minmax(27.7778rem, 1fr) minmax(18.75rem, 0.55fr);
  gap: 1.3889rem;
  margin-top: 1.3889rem;
}

.creatives-panel,
.ai-panel {
  min-height: 25rem;
  padding: 1.7361rem;
}

.creatives-row {
  gap: 0.9028rem;
  margin-top: 1.5278rem;
}

.creative-card {
  flex-basis: 11.1111rem;
}

.creative-image {
  min-height: 10.4167rem;
  padding: 0.9722rem;
  border-radius: 1.1111rem;
}

.creative-image span {
  font-size: 0.625rem;
}

.creative-image strong {
  margin-top: 0.5556rem;
  font-size: 0.9722rem;
}

.creative-card p {
  margin: 1.1111rem 0 0.4861rem;
  font-size: 0.8333rem;
}

.creative-card em {
  font-size: 0.8333rem;
}

.ai-title {
  gap: 1.1111rem;
}

.ai-title span {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 0.5556rem;
}

.ai-panel ul {
  gap: 0.9722rem;
  margin-top: 1.3889rem;
  padding-left: 1.3889rem;
  font-size: 0.9028rem;
}

.ai-panel > p {
  margin-top: 1.5278rem;
  font-size: 0.8333rem;
}

.side-stat-stack {
  gap: 1.3889rem;
}

.mini-stat-panel {
  min-height: 11.8056rem;
  padding: 1.7361rem;
}

.mini-stat-panel h2 {
  margin-bottom: 1.5278rem;
}

.progress-line {
  grid-template-columns: minmax(5.6944rem, 1fr) 5.9722rem 2.9167rem;
  gap: 0.6944rem;
  margin-top: 1.0417rem;
  font-size: 0.8333rem;
}

.progress-line span {
  gap: 0.5556rem;
}

.progress-line span svg,
.place-dot {
  width: 0.9722rem;
  height: 0.9722rem;
}

.progress-line span.placement-icon {
  min-width: 1.5278rem;
  width: 1.5278rem;
  height: 1.5278rem;
}

.progress-line .placement-icon svg {
  width: 0.7639rem;
  height: 0.7639rem;
  color: #f59e0b;
}

.progress-line div {
  height: 0.3472rem;
}

@media (max-width: 1200px) {
  .top-grid,
  .panel-reports,
  .chart-goals-grid,
  .bottom-grid {
    grid-template-columns: 1fr;
  }

  .panel-reports {
    align-items: start;
  }
}

@media (max-width: 885px) {
  .kpi-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 570px) {
  .figma-dashboard {
    padding: 1.3889rem 1.0417rem;
  }

  .kpi-grid {
    grid-template-columns: 1fr;
  }

  .metric-card {
    min-height: 11.1111rem;
  }

  .goals-content {
    grid-template-columns: 1fr;
  }

  .donut-wrap {
    width: 13.8889rem;
    height: 13.8889rem;
  }

  .filters-row > *,
  .filters-row .filter-btn,
  .export-btn,
  .date-btn,
  .dashboard-date-picker {
    flex-basis: auto;
    max-width: none;
    width: 100%;
  }

  .sync-status-label,
  .nds-check-wrap,
  .filter-right-group {
    width: 100%;
    margin-left: 0;
  }

  .filter-right-group {
    flex-wrap: wrap;
  }

  .ml-auto {
    margin-left: 0;
  }

  .campaign-row {
    min-width: 73.6111rem;
  }
}

/* Figma top-panel alignment */
.top-grid {
  grid-template-columns: minmax(25rem, 34.3056rem) minmax(52.7778rem, 1fr);
  gap: 1.3889rem;
  align-items: start;
}

.panel-channels,
.panel-reports {
  height: 9.0972rem;
  min-height: 9.0972rem;
  padding: 1.7361rem;
  overflow: visible;
}

.panel-reports {
  display: grid;
  grid-template-columns: minmax(20.8333rem, auto) 12.8472rem 17.7083rem auto;
  column-gap: 1.3889rem;
  row-gap: 0;
  align-items: start;
}

.report-main,
.report-template,
.report-schedule {
  min-width: 0;
}

.report-main h2,
.report-template h2 {
  display: flex;
  align-items: center;
  height: 1.3889rem;
  line-height: 1;
}

.panel-channels .chips-row,
.panel-reports .chips-row {
  flex-wrap: nowrap;
  gap: 1.0417rem;
  margin-top: 1.3889rem;
}

.panel-channels .chip,
.panel-reports .chip {
  flex: 0 0 auto;
  height: 3.1944rem;
  gap: 0.6944rem;
  padding: 0 1.0417rem;
  border-radius: 69.375rem;
  box-shadow: none;
  color: #4b4b4b;
  cursor: pointer;
  font-size: 0.9028rem;
  font-weight: 500;
  line-height: 1;
  transition: background-color 0.5s, border-color 0.25s, box-shadow 0.25s, transform 0.75s;
}

.panel-channels .chip:hover,
.panel-reports .chip:hover {
  box-shadow: 0 10px 22px rgba(15, 23, 42, 0.06);
  transform: translateY(-0.0694rem);
}

.panel-channels .chip:active,
.panel-reports .chip:active,
.select-like:active,
.filter-btn:active,
.export-btn:active,
.primary-report:active,
.sync-btn:active {
  transform: scale(0.97);
  transition: transform 0s;
}

.panel-channels .chip.active {
  box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.1);
}

.panel-reports .chip {
  border: 1px solid #ebebeb;
}

.panel-reports .chip.active {
  border-color: transparent;
  background-color: #f5f7f9 !important;
}

.chip-dot {
  overflow: hidden;
}

.chip-img {
  display: block;
  width: 0.9722rem;
  height: 0.9722rem;
  object-fit: contain;
}

.chip-img.vk {
  transform: scale(1.35);
}

.chip-img.telegram,
.chip-img.max {
  width: 1.25rem;
  height: 1.25rem;
}

.chip-letter {
  color: #fff;
  font-size: 0.625rem;
  font-weight: 700;
  line-height: 1;
}

.report-schedule p {
  display: flex;
  align-items: center;
  height: 1.3889rem;
  margin: 0 0 1.3889rem;
  color: #b3b3b3;
  font-size: 0.9028rem;
  line-height: 1;
}

.select-like {
  width: 100%;
  height: 3.1944rem;
  border-color: #ebebeb;
  border-radius: 1.0417rem;
  background: #fff;
  color: #b3b3b3;
  cursor: pointer;
  line-height: 1;
  transition: border-color 0.2s, box-shadow 0.25s, transform 0.75s;
}

.top-select .select-like {
  margin-top: 1.3889rem;
}

.report-schedule .select-like {
  margin-top: 0;
}

.select-like:hover,
.filter-btn:hover,
.export-btn:hover {
  border-color: rgba(0, 0, 0, 0.1);
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.04);
}

.primary-report {
  align-self: end;
  width: auto;
  height: 3.1944rem;
  padding: 0 0.6944rem;
  justify-content: center;
  white-space: nowrap;
  line-height: 1;
  transition: background-color 0.25s, box-shadow 0.25s, transform 0.75s;
}

.primary-report:hover {
  background: #1d4ed8;
  box-shadow: 0 12px 24px rgba(37, 99, 235, 0.24);
}

.custom-select {
  position: relative;
  display: inline-flex;
  flex-direction: column;
}

.custom-select .cs-head {
  user-select: none;
}

.custom-select.open .cs-head {
  border-color: rgba(0, 0, 0, 0.1);
}

.custom-select .cs-current {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.custom-select .cs-arrow {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.6667rem;
  height: 1.6667rem;
  margin-left: auto;
  border-radius: 69.375rem;
  background: #f5f7f9;
  color: #b3b3b3;
  flex: 0 0 auto;
  transition: transform 0.3s;
}

.custom-select .cs-arrow svg {
  width: 0.9722rem;
  height: 0.9722rem;
}

.custom-select.open .cs-arrow {
  transform: rotate(180deg);
}

.custom-select .cs-list {
  position: absolute;
  top: calc(100% + 0.2778rem);
  left: 0;
  z-index: 99;
  display: flex;
  min-width: 100%;
  flex-direction: column;
  overflow: hidden;
  padding: 0;
  border-radius: 0.5556rem;
  background-color: #fff;
  box-shadow: 0 0 0 1px rgba(68, 68, 68, 0.1);
  opacity: 0;
  pointer-events: none;
  transform: scale(0.75) translateY(-1.4583rem);
  transform-origin: 50% 0;
  transition: transform 0.2s cubic-bezier(0.5, 0, 0, 1.25), opacity 0.15s ease-out;
}

.custom-select.open .cs-list {
  opacity: 1;
  pointer-events: auto;
  transform: scale(1) translateY(0);
}

.custom-select .cs-option {
  display: flex;
  align-items: center;
  width: 100%;
  min-height: 2.9861rem;
  gap: 0.6944rem;
  padding: 0.8333rem 1.7361rem 0.8333rem 1.1806rem;
  border: 0;
  background: transparent;
  color: rgba(0, 0, 0, 0.7);
  cursor: pointer;
  font-size: 0.9028rem;
  font-weight: 400;
  line-height: 1.2;
  text-align: left;
  white-space: nowrap;
  transition: background-color 0.2s, color 0.2s;
}

.custom-select .cs-option:hover {
  background-color: #f5f7f9;
}

.custom-select .cs-option.selected {
  font-weight: 600;
}

.top-select .cs-list {
  min-width: 100%;
}

.top-select .schedule-menu {
  width: 20.8333rem;
  padding: 0.8333rem;
  gap: 0.8333rem;
  overflow: visible;
}

.schedule-field-group {
  display: flex;
  flex-direction: column;
  gap: 0.4167rem;
  color: #6b7280;
  font-size: 0.7639rem;
  font-weight: 600;
}

.schedule-day-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.2778rem;
  padding: 0.2778rem;
  border: 1px solid #ebebeb;
  border-radius: 0.6944rem;
  background: #fff;
}

.schedule-day-option {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 1.1111rem;
  align-items: center;
  gap: 0.4167rem;
  min-height: 2.5rem;
  padding: 0 0.5556rem 0 0.6944rem;
  border: 0;
  border-radius: 0.5556rem;
  background: transparent;
  color: #171717;
  cursor: pointer;
  font-size: 0.8333rem;
  font-weight: 650;
  line-height: 1;
  text-align: left;
  transition: background-color 0.2s, color 0.2s;
}

.schedule-day-option--wide {
  grid-column: 1 / -1;
}

.schedule-day-option:hover,
.schedule-day-option.selected {
  background: #f3f7ff;
  color: #2563eb;
}

.schedule-day-check {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.1111rem;
  height: 1.1111rem;
  color: #2563eb;
}

.schedule-day-check svg {
  width: 1.1111rem;
  height: 1.1111rem;
  stroke-width: 2;
}

.schedule-field {
  width: 100%;
  height: 2.6389rem;
  padding: 0 0.8333rem;
  border: 1px solid #ebebeb;
  border-radius: 0.6944rem;
  background: #fff;
  color: #171717;
  font-size: 0.9028rem;
  font-weight: 600;
  outline: none;
}

.schedule-field:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.schedule-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5556rem;
}

.schedule-secondary,
.schedule-primary {
  height: 2.6389rem;
  border: 0;
  border-radius: 0.6944rem;
  cursor: pointer;
  font-size: 0.8333rem;
  font-weight: 700;
}

.schedule-secondary {
  background: #f5f7f9;
  color: #6b7280;
}

.schedule-primary {
  background: #2563eb;
  color: #fff;
}

.dashboard-select .cs-list {
  min-width: 15.9722rem;
}

.campaigns.cs-list {
  min-width: 25rem;
}

.export-select .cs-list {
  right: 0;
  left: auto;
}

.heading-section h1 {
  font-weight: 600;
}

.dashboard-select .cs-arrow {
  width: 1.1111rem;
  height: 1.1111rem;
  background: #f5f7f9;
}

.dashboard-select .cs-arrow svg {
  width: 0.6944rem;
  height: 0.6944rem;
}

.top-select .cs-arrow {
  width: 1.6667rem;
  height: 1.6667rem;
}

.top-select .cs-arrow svg {
  width: 0.9722rem;
  height: 0.9722rem;
}

.export-select .cs-arrow {
  width: 1.6667rem;
  height: 1.6667rem;
  background: #1f55d9;
  color: #fff;
}

.export-select .cs-arrow svg {
  width: 0.8333rem;
  height: 0.8333rem;
}

.export-select.open .cs-arrow {
  background: #1748bf;
}

.custom-select .cs-option svg {
  width: 1.1111rem;
  height: 1.1111rem;
  flex: 0 0 1.1111rem;
}

.filter-btn,
.export-btn,
.sync-btn {
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.25s, transform 0.75s, background-color 0.25s;
}

/* Dark theme for the static dashboard mockup */
:global(.dark) .figma-dashboard,
:global(.darkmode) .figma-dashboard {
  color: #f3f4f6;
}

:global(.dark) .panel,
:global(.darkmode) .panel,
:global(.dark) .metric-card,
:global(.darkmode) .metric-card {
  border-color: rgba(255, 255, 255, 0.08);
  background: #2a2d3c;
  box-shadow: none;
}

:global(.dark) .panel h2,
:global(.darkmode) .panel h2,
:global(.dark) .panel-channels h2,
:global(.darkmode) .panel-channels h2,
:global(.dark) .panel-reports h2,
:global(.darkmode) .panel-reports h2,
:global(.dark) .heading-section h1,
:global(.darkmode) .heading-section h1,
:global(.dark) .metric-card h3,
:global(.darkmode) .metric-card h3,
:global(.dark) .metric-card strong,
:global(.darkmode) .metric-card strong,
:global(.dark) .panel-title-row h2,
:global(.darkmode) .panel-title-row h2,
:global(.dark) .mini-stat-panel h2,
:global(.darkmode) .mini-stat-panel h2,
:global(.dark) .ai-title h2,
:global(.darkmode) .ai-title h2 {
  color: #f3f4f6;
}

:global(.dark) .chip,
:global(.darkmode) .chip,
:global(.dark) .campaign-row,
:global(.darkmode) .campaign-row,
:global(.dark) .goal-item p,
:global(.darkmode) .goal-item p,
:global(.dark) .creative-card p,
:global(.darkmode) .creative-card p,
:global(.dark) .ai-panel ul,
:global(.darkmode) .ai-panel ul,
:global(.dark) .progress-line,
:global(.darkmode) .progress-line {
  color: rgba(255, 255, 255, 0.78);
}

:global(.dark) .panel-reports .chip,
:global(.darkmode) .panel-reports .chip {
  border-color: rgba(255, 255, 255, 0.12);
}

:global(.dark) .panel-reports .chip.active,
:global(.darkmode) .panel-reports .chip.active {
  border-color: transparent;
  background-color: rgba(255, 255, 255, 0.08) !important;
}

:global(.dark) .panel-channels .chip.active,
:global(.darkmode) .panel-channels .chip.active {
  box-shadow: inset 0 0 0 1px rgba(74, 122, 255, 0.22);
}

:global(.dark) .chip:hover,
:global(.darkmode) .chip:hover {
  box-shadow: 0 10px 22px rgba(0, 0, 0, 0.12);
}

:global(.dark) .report-schedule p,
:global(.darkmode) .report-schedule p,
:global(.dark) .sync-btn,
:global(.darkmode) .sync-btn,
:global(.dark) .metric-card p,
:global(.darkmode) .metric-card p,
:global(.dark) .campaign-row.header,
:global(.darkmode) .campaign-row.header,
:global(.dark) .creative-card em,
:global(.darkmode) .creative-card em,
:global(.dark) .ai-panel > p,
:global(.darkmode) .ai-panel > p {
  color: rgba(255, 255, 255, 0.48);
}

:global(.dark) .select-like,
:global(.darkmode) .select-like,
:global(.dark) .filter-btn,
:global(.darkmode) .filter-btn,
:global(.dark) .month-select,
:global(.darkmode) .month-select,
:global(.dark) .see-all,
:global(.darkmode) .see-all,
:global(.dark) .round-action,
:global(.darkmode) .round-action {
  border-color: rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.58);
}

:global(.dark) .select-like:hover,
:global(.darkmode) .select-like:hover,
:global(.dark) .filter-btn:hover,
:global(.darkmode) .filter-btn:hover,
:global(.dark) .month-select:hover,
:global(.darkmode) .month-select:hover,
:global(.dark) .see-all:hover,
:global(.darkmode) .see-all:hover {
  border-color: rgba(255, 255, 255, 0.18);
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.12);
}

:global(.dark) .custom-select .cs-arrow,
:global(.darkmode) .custom-select .cs-arrow {
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.62);
}

:global(.dark) .export-select .cs-arrow,
:global(.darkmode) .export-select .cs-arrow {
  background: #1f55d9;
  color: #fff;
}

:global(.dark) .custom-select .cs-list,
:global(.darkmode) .custom-select .cs-list,
:global(.dark) .dropdown-panel,
:global(.darkmode) .dropdown-panel {
  border-color: rgba(255, 255, 255, 0.08);
  background: #2c2f3d;
  box-shadow: 0 18px 42px rgba(0, 0, 0, 0.28);
}

:global(.dark) .schedule-field-group,
:global(.darkmode) .schedule-field-group {
  color: rgba(255, 255, 255, 0.58);
}

:global(.dark) .schedule-field,
:global(.darkmode) .schedule-field {
  border-color: rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.86);
}

:global(.dark) .schedule-day-list,
:global(.darkmode) .schedule-day-list {
  border-color: rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.04);
}

:global(.dark) .schedule-day-option,
:global(.darkmode) .schedule-day-option {
  color: rgba(255, 255, 255, 0.78);
}

:global(.dark) .schedule-day-option:hover,
:global(.darkmode) .schedule-day-option:hover,
:global(.dark) .schedule-day-option.selected,
:global(.darkmode) .schedule-day-option.selected {
  background: rgba(74, 122, 255, 0.16);
  color: #67a8ff;
}

:global(.dark) .schedule-day-check,
:global(.darkmode) .schedule-day-check {
  color: #67a8ff;
}

:global(.dark) .schedule-secondary,
:global(.darkmode) .schedule-secondary {
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.72);
}

:global(.dark) .custom-select .cs-option,
:global(.darkmode) .custom-select .cs-option,
:global(.dark) .dropdown-panel button,
:global(.darkmode) .dropdown-panel button {
  color: rgba(255, 255, 255, 0.72);
}

:global(.dark) .custom-select .cs-option:hover,
:global(.darkmode) .custom-select .cs-option:hover,
:global(.dark) .dropdown-panel button:hover,
:global(.darkmode) .dropdown-panel button:hover,
:global(.dark) .custom-select .cs-option.selected,
:global(.darkmode) .custom-select .cs-option.selected {
  background: rgba(255, 255, 255, 0.06);
  color: #fff;
}

:global(.dark) .search-box,
:global(.darkmode) .search-box {
  border-color: rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
}

:global(.dark) .search-box input,
:global(.darkmode) .search-box input {
  background: transparent;
  color: #f3f4f6;
}

:global(.dark) .search-box input::placeholder,
:global(.darkmode) .search-box input::placeholder {
  color: rgba(255, 255, 255, 0.42);
}

:global(.dark) .metric-icon,
:global(.darkmode) .metric-icon,
:global(.dark) .ai-title span,
:global(.darkmode) .ai-title span {
  background: rgba(255, 255, 255, 0.06);
  color: #4a7aff;
}

:global(.dark) .round-action,
:global(.darkmode) .round-action {
  color: rgba(255, 255, 255, 0.5);
}

:global(.dark) .trend,
:global(.darkmode) .trend,
:global(.dark) .campaign-row b,
:global(.darkmode) .campaign-row b {
  background: rgba(34, 197, 94, 0.16);
  color: #66bb6a;
}

:global(.dark) .trend.negative,
:global(.darkmode) .trend.negative,
:global(.dark) .campaign-row b.negative,
:global(.darkmode) .campaign-row b.negative {
  background: rgba(239, 68, 68, 0.16);
  color: #f87171;
}

:global(.dark) .grid-lines line,
:global(.darkmode) .grid-lines line {
  stroke: rgba(255, 255, 255, 0.08);
}

:global(.dark) .chart-area circle,
:global(.darkmode) .chart-area circle {
  stroke: #2a2d3c;
}

:global(.dark) .axis-labels text,
:global(.darkmode) .axis-labels text {
  fill: rgba(255, 255, 255, 0.42);
}

:global(.dark) .donut-wrap::after,
:global(.darkmode) .donut-wrap::after {
  background: #2a2d3c;
  box-shadow: 0 1rem 2rem rgba(0, 0, 0, 0.12);
}

:global(.dark) .goal-item,
:global(.darkmode) .goal-item {
  border-color: rgba(255, 255, 255, 0.08);
}

:global(.dark) .goal-item p,
:global(.darkmode) .goal-item p {
  background: rgba(0, 0, 0, 0.08);
}

:global(.dark) .campaign-row.orange,
:global(.darkmode) .campaign-row.orange {
  background: rgba(242, 169, 136, 0.1);
}

:global(.dark) .campaign-row.green,
:global(.darkmode) .campaign-row.green {
  background: rgba(34, 197, 94, 0.08);
}

:global(.dark) .campaign-row.blue,
:global(.darkmode) .campaign-row.blue {
  background: rgba(74, 122, 255, 0.08);
}

:global(.dark) .progress-line div,
:global(.darkmode) .progress-line div {
  background: rgba(255, 255, 255, 0.12);
}

:global(.dark) .see-all,
:global(.darkmode) .see-all {
  color: #4a7aff;
}

@media (max-width: 1125px) {
  .top-grid {
    grid-template-columns: 1fr;
  }

  .panel-reports {
    height: auto;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    row-gap: 1.3889rem;
  }

  .primary-report {
    width: 100%;
  }
}

@media (max-width: 570px) {
  .panel-channels,
  .panel-reports {
    height: auto;
  }

  .panel-channels .chips-row,
  .panel-reports .chips-row {
    flex-wrap: wrap;
  }

  .panel-reports {
    grid-template-columns: 1fr;
  }
}

.figma-dashboard.is-dark {
  color: #f3f4f6;
}

.figma-dashboard.is-dark .panel,
.figma-dashboard.is-dark .metric-card {
  border-color: rgba(255, 255, 255, 0.08);
  background: #2a2d3c;
  box-shadow: none;
}
.figma-dashboard.is-dark .metric-card--add {
  background: transparent;
  border-color: rgba(255, 255, 255, 0.15);
}
.figma-dashboard.is-dark .metric-card--add:hover {
  background: rgba(74, 122, 255, 0.1);
  border-color: #4a7aff;
  color: #4a7aff;
}
.figma-dashboard.is-dark .add-card-dropdown {
  background: #2a2d3c;
  border-color: rgba(255,255,255,0.1);
}
.figma-dashboard.is-dark .add-card-item {
  color: #e0e0e0;
}
.figma-dashboard.is-dark .add-card-item:hover {
  background: rgba(74,122,255,0.15);
  color: #4a7aff;
}

.figma-dashboard.is-dark h1,
.figma-dashboard.is-dark h2,
.figma-dashboard.is-dark h3,
.figma-dashboard.is-dark strong,
.figma-dashboard.is-dark .donut-wrap span {
  color: #f3f4f6;
}

.figma-dashboard.is-dark .chip,
.figma-dashboard.is-dark .campaign-row,
.figma-dashboard.is-dark .goal-item p,
.figma-dashboard.is-dark .creative-card p,
.figma-dashboard.is-dark .ai-panel ul,
.figma-dashboard.is-dark .progress-line {
  color: rgba(255, 255, 255, 0.78);
}

.figma-dashboard.is-dark .panel-reports .chip {
  border-color: rgba(255, 255, 255, 0.12);
}

.figma-dashboard.is-dark .panel-reports .chip.active {
  border-color: transparent;
  background-color: rgba(255, 255, 255, 0.08) !important;
}

.figma-dashboard.is-dark .panel-channels .chip.active {
  box-shadow: inset 0 0 0 1px rgba(74, 122, 255, 0.22);
}

.figma-dashboard.is-dark .chip:hover {
  box-shadow: 0 10px 22px rgba(0, 0, 0, 0.14);
}

.figma-dashboard.is-dark .report-schedule p,
.figma-dashboard.is-dark .sync-btn,
.figma-dashboard.is-dark .metric-card p,
.figma-dashboard.is-dark .metric-foot,
.figma-dashboard.is-dark .campaign-row.header,
.figma-dashboard.is-dark .creative-card em,
.figma-dashboard.is-dark .ai-panel > p {
  color: rgba(255, 255, 255, 0.5);
}

.figma-dashboard.is-dark .select-like,
.figma-dashboard.is-dark .filter-btn,
.figma-dashboard.is-dark .dashboard-date-picker :deep(.date-range-picker-container > button),
.figma-dashboard.is-dark .month-select,
.figma-dashboard.is-dark .see-all,
.figma-dashboard.is-dark .round-action {
  border-color: rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.62);
}

.figma-dashboard.is-dark .select-like:hover,
.figma-dashboard.is-dark .filter-btn:hover,
.figma-dashboard.is-dark .dashboard-date-picker :deep(.date-range-picker-container > button:hover),
.figma-dashboard.is-dark .month-select:hover,
.figma-dashboard.is-dark .see-all:hover {
  border-color: rgba(255, 255, 255, 0.18);
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.12);
}

.figma-dashboard.is-dark .export-btn,
.figma-dashboard.is-dark .primary-report {
  background: #2563eb;
  color: #fff;
}

.figma-dashboard.is-dark .primary-report:hover {
  background: #1d4ed8;
  box-shadow: 0 12px 24px rgba(37, 99, 235, 0.28);
}

.figma-dashboard.is-dark .custom-select .cs-arrow {
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.66);
}

.figma-dashboard.is-dark .export-select .cs-arrow {
  background: #1f55d9;
  color: #fff;
}

.figma-dashboard.is-dark .export-select.open .cs-arrow {
  background: #1748bf;
}

.figma-dashboard.is-dark .custom-select .cs-list,
.figma-dashboard.is-dark .dropdown-panel {
  border-color: rgba(255, 255, 255, 0.08);
  background: #2c2f3d;
  box-shadow: 0 18px 42px rgba(0, 0, 0, 0.28);
}

.figma-dashboard.is-dark .custom-select .cs-option,
.figma-dashboard.is-dark .dropdown-panel button {
  color: rgba(255, 255, 255, 0.72);
}

.figma-dashboard.is-dark .custom-select .cs-option:hover,
.figma-dashboard.is-dark .dropdown-panel button:hover,
.figma-dashboard.is-dark .custom-select .cs-option.selected {
  background: rgba(255, 255, 255, 0.06);
  color: #fff;
}

.figma-dashboard.is-dark .search-box {
  border-color: rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
}

.figma-dashboard.is-dark .search-box input {
  background: transparent;
  color: #f3f4f6;
}

.figma-dashboard.is-dark .search-box input::placeholder {
  color: rgba(255, 255, 255, 0.42);
}

.figma-dashboard.is-dark .metric-icon,
.figma-dashboard.is-dark .ai-title span {
  background: rgba(255, 255, 255, 0.06);
  color: #4a7aff;
}

.figma-dashboard.is-dark .round-action {
  color: rgba(255, 255, 255, 0.5);
}

.figma-dashboard.is-dark .trend,
.figma-dashboard.is-dark .campaign-row b {
  background: rgba(34, 197, 94, 0.16);
  color: #66bb6a;
}

.figma-dashboard.is-dark .trend.negative,
.figma-dashboard.is-dark .campaign-row b.negative {
  background: rgba(239, 68, 68, 0.16);
  color: #f87171;
}

.figma-dashboard.is-dark .grid-lines line {
  stroke: rgba(255, 255, 255, 0.08);
}

.figma-dashboard.is-dark .chart-area circle {
  stroke: #2a2d3c;
}

.figma-dashboard.is-dark .axis-labels text {
  fill: rgba(255, 255, 255, 0.42);
}

.figma-dashboard.is-dark .donut-wrap::after {
  background: #2a2d3c;
}

.figma-dashboard.is-dark .goal-item {
  border-color: rgba(255, 255, 255, 0.08);
}

.figma-dashboard.is-dark .goal-item p {
  background: rgba(0, 0, 0, 0.08);
}

.figma-dashboard.is-dark .campaign-row.orange {
  background: rgba(242, 169, 136, 0.1);
}

.figma-dashboard.is-dark .campaign-row.green {
  background: rgba(34, 197, 94, 0.08);
}

.figma-dashboard.is-dark .campaign-row.blue {
  background: rgba(74, 122, 255, 0.08);
}

.figma-dashboard.is-dark .progress-line div {
  background: rgba(255, 255, 255, 0.12);
}

.figma-dashboard.is-dark .see-all {
  color: #4a7aff;
}

/* Chart responsiveness pass: keep plots readable instead of squeezing them. */
.chart-panel {
  min-width: 0;
}

.chart-area {
  display: flex;
  align-items: center;
  width: 100%;
  min-height: 18.0556rem;
  aspect-ratio: 880 / 300;
  overflow-x: auto;
  overflow-y: visible;
  overscroll-behavior-x: contain;
}

.chart-area svg {
  flex: 0 0 auto;
  display: block;
  width: max(50rem, 100%);
  height: auto;
  aspect-ratio: 880 / 260;
  max-height: 100%;
}

.goals-content {
  grid-template-columns: minmax(12.5rem, 16.6667rem) minmax(0, 1fr);
  min-width: 0;
}

.donut-wrap {
  width: clamp(12.5rem, 18vw, 16.6667rem);
  height: clamp(12.5rem, 18vw, 16.6667rem);
  max-width: 100%;
}

.donut {
  position: relative;
  overflow: hidden;
  background: transparent;
  -webkit-mask: none;
  mask: none;
}

.donut::before,
.donut::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 69.375rem;
}

.donut::before {
  background: var(--donut-outer);
  -webkit-mask: radial-gradient(circle, transparent 0 46%, #000 46.1%);
  mask: radial-gradient(circle, transparent 0 46%, #000 46.1%);
}

.donut::after {
  background: var(--donut-inner);
  -webkit-mask: radial-gradient(circle, transparent 0 31%, #000 31.1% 46.1%, transparent 46.2%);
  mask: radial-gradient(circle, transparent 0 31%, #000 31.1% 46.1%, transparent 46.2%);
}

.donut-wrap::after {
  width: 31%;
  height: 31%;
}

.goals-list,
.goal-item,
.goal-item div,
.goal-item p {
  min-width: 0;
}

.goal-item div,
.goal-item p {
  overflow-wrap: anywhere;
}

.goal-item {
  border-color: var(--goal-border);
  background: #fff;
  box-shadow: 0 0.4rem 1rem rgba(15, 23, 42, 0.018);
}

.goal-item div {
  margin: -0.0694rem -0.0694rem 0;
  border-radius: 0.8rem;
  background: var(--goal-bg);
  color: #3f3f3f;
  font-weight: 500;
}

.goal-item p {
  background: #fff;
  color: #171717;
}

.bottom-grid,
.side-stat-stack,
.mini-stat-panel {
  min-width: 0;
}

.bottom-grid {
  align-items: stretch;
}

.creatives-panel,
.ai-panel,
.mini-stat-panel {
  box-shadow: 0 0.8rem 2.6rem rgba(15, 23, 42, 0.025);
}

.creatives-panel h2,
.ai-panel h2,
.mini-stat-panel h2 {
  font-weight: 600;
}

.side-stat-stack {
  grid-template-rows: minmax(0, 1fr) minmax(0, 1fr);
}

.progress-line {
  grid-template-columns: minmax(0, 1fr) minmax(5rem, 8.3333rem) auto;
  min-width: 0;
}

.progress-line span {
  min-width: 0;
}

@media (max-width: 885px) {
  .chart-area {
    min-height: 18.0556rem;
  }

  .bottom-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 570px) {
  .chart-panel,
  .goals-panel,
  .campaigns-panel,
  .creatives-panel,
  .ai-panel,
  .mini-stat-panel {
    padding: 1.3889rem;
  }

  .panel-title-row {
    align-items: flex-start;
    flex-direction: column;
  }

  .chart-area {
    min-height: 18.0556rem;
    aspect-ratio: auto;
    margin-top: 1.25rem;
  }

  .chart-area svg {
    width: 47.2222rem;
  }

  .goals-content {
    justify-items: center;
  }

  .goals-list {
    width: 100%;
  }

  .donut-wrap {
    width: min(15.2778rem, 72vw);
    height: min(15.2778rem, 72vw);
  }
}
</style>
