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
          <div class="chips-row">
            <button
              v-for="item in reportChannels"
              :key="item.name"
              class="chip"
              :class="{ active: selectedReportChannel === item.name }"
              :style="{ backgroundColor: getChipBackground(item) }"
              type="button"
              @click="selectedReportChannel = item.name"
            >
              <span class="chip-dot" :style="{ background: item.color }">
                <img
                  v-if="item.asset"
                  :src="item.asset"
                  alt=""
                  :class="['chip-img', item.imageClass]"
                />
                <span v-else-if="item.letter" class="chip-letter">{{ item.letter }}</span>
                <component v-else :is="item.icon" class="chip-icon" />
              </span>
              {{ item.name }}
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
          <div class="cs-list">
            <button
              v-for="option in scheduleOptions"
              :key="option"
              type="button"
              class="cs-option"
              :class="{ selected: selectedSchedule === option }"
              @click="selectSchedule(option)"
            >{{ option }}</button>
          </div>
        </div>

        <button class="primary-report" type="button" :disabled="sendingTg || sendingEmail" @click="handleSendSelectedReport">
          {{ sendingTg || sendingEmail ? 'Отправка...' : 'Отправить отчет' }}
          <ArrowPathRoundedSquareIcon />
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

        <button class="sync-btn" type="button" :disabled="syncingIntegrations" @click="handleSyncIntegrations">
          <ArrowPathIcon :class="{ spinning: syncingIntegrations }" />
          {{ syncingIntegrations ? 'Синхронизация...' : syncLabel }}
        </button>

        <div class="filter-wrap custom-select dashboard-select ml-auto export-select" :class="{ open: openMenu === 'export' }" v-click-outside="() => closeMenu('export')">
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
    </section>

    <section class="kpi-grid">
      <article v-for="metric in metrics" :key="metric.title" class="metric-card">
        <div class="metric-head">
          <span class="metric-icon">
            <component :is="metric.icon" />
          </span>
          <div>
            <h3>{{ metric.title }}</h3>
            <p>{{ metric.subtitle }}</p>
          </div>
          <button class="round-action" type="button">
            <ArrowUpRightIcon />
          </button>
        </div>
        <strong>{{ metric.value }}</strong>
        <div class="metric-foot">
          <span class="trend" :class="{ negative: metric.negative }">
            <ArrowTrendingDownIcon v-if="metric.negative" />
            <ArrowTrendingUpIcon v-else />
            {{ metric.trend }}
          </span>
          <span>{{ metric.delta }}</span>
        </div>
      </article>
    </section>

    <section class="chart-goals-grid">
      <article class="panel chart-panel">
        <div class="panel-title-row">
          <h2>Эффективность кампаний</h2>
          <div class="custom-select chart-period-select" :class="{ open: openMenu === 'chart-period' }" v-click-outside="() => closeMenu('chart-period')">
            <button class="month-select cs-head" type="button" @click="toggleMenu('chart-period')">
              <span class="cs-current">{{ selectedChartPeriod }}</span>
              <span class="cs-arrow">
                <ChevronDownIcon />
              </span>
            </button>
            <div class="cs-list">
              <button
                v-for="option in chartPeriodOptions"
                :key="option"
                type="button"
                class="cs-option"
                :class="{ selected: selectedChartPeriod === option }"
                @click="selectChartPeriod(option)"
              >{{ option }}</button>
            </div>
          </div>
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
            <div class="donut" :style="{ background: donutGradient }"></div>
            <span>{{ goalsTotalLabel }}</span>
          </div>
          <div class="goals-list">
            <div v-for="goal in goals" :key="goal.name" class="goal-item">
              <div>
                <span :style="{ background: goal.color }"></span>
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
        <button class="see-all" type="button">Смотреть все <ChevronDownIcon /></button>
      </div>
      <div class="campaign-table">
        <div class="campaign-row header">
          <span>Название кампании</span>
          <span>Расход</span>
          <span>Показы</span>
          <span>Клики</span>
          <span>CPC</span>
          <span>Лиды</span>
          <span>CPA</span>
        </div>
        <div v-for="(campaign, index) in campaignRows" :key="index" class="campaign-row" :class="campaign.tint">
          <span>{{ campaign.name }}</span>
          <span>{{ campaign.cost }} <b>{{ campaign.trendCost }}</b></span>
          <span>{{ campaign.impressions }} <b>{{ campaign.trendImpressions }}</b></span>
          <span>{{ campaign.clicks }} <b>{{ campaign.trendClicks }}</b></span>
          <span>{{ campaign.cpc }} <b>{{ campaign.trendCpc }}</b></span>
          <span>{{ campaign.leads }} <b>{{ campaign.trendLeads }}</b></span>
          <span>{{ campaign.cpa }} <b>{{ campaign.trendCpa }}</b></span>
        </div>
      </div>
    </section>

    <section class="bottom-grid">
      <article class="panel creatives-panel">
        <h2>Топ креативы за месяц</h2>
        <div class="creatives-row">
          <div v-for="creative in creatives" :key="creative.id || creative.title" class="creative-card">
            <div class="creative-image" :class="creative.class" :style="creative.imageUrl ? { backgroundImage: `linear-gradient(rgba(15, 23, 42, 0.2), rgba(15, 23, 42, 0.55)), url(${creative.imageUrl})` } : null">
              <span>{{ creative.badge }}</span>
              <strong>{{ creative.title }}</strong>
            </div>
            <p>Заголовок:</p>
            <em>{{ creative.heading }}</em>
            <p>Текст:</p>
            <em>{{ creative.text }}</em>
          </div>
        </div>
      </article>

      <article class="panel ai-panel">
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
          <div v-for="item in placements" :key="item.name" class="progress-line">
            <span><span class="place-dot"></span>{{ item.name }}</span>
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
        style="max-width:448px; border-radius:24px; padding:24px; box-shadow:0 25px 50px rgba(0,0,0,0.35)"
        :style="{ background: isDarkMode ? '#2a2d3c' : '#fff' }"
      >
        <h3 :style="{ fontSize:'18px', fontWeight:600, color: isDarkMode ? '#f3f4f6' : '#111827', marginBottom:'8px' }">
          Подключите Telegram
        </h3>
        <p :style="{ fontSize:'14px', color: isDarkMode ? 'rgba(255,255,255,0.5)' : '#6b7280', marginBottom:'16px' }">
          В Telegram нажмите <strong>Start</strong> у бота, затем «Готово» — отчёт отправится автоматически.
        </p>
        <div style="display:flex; gap:12px">
          <button
            type="button"
            :style="{ flex:1, padding:'10px', borderRadius:'12px', border:'none', cursor:'pointer', fontSize:'14px', background: isDarkMode ? 'rgba(255,255,255,0.08)' : '#f3f4f6', color: isDarkMode ? '#f3f4f6' : '#374151' }"
            @click="closeTgLinkModal"
          >Отмена</button>
          <button
            type="button"
            style="flex:1; padding:10px; border-radius:12px; background:#2563eb; color:#fff; border:none; cursor:pointer; font-size:14px"
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
  ArrowUpRightIcon,
  CalendarDaysIcon,
  ChartBarIcon,
  CheckBadgeIcon,
  ChevronDownIcon,
  CursorArrowRaysIcon,
  DevicePhoneMobileIcon,
  DocumentArrowDownIcon,
  EnvelopeIcon,
  LinkIcon,
  MagnifyingGlassIcon,
  PhotoIcon,
  PlayCircleIcon,
  SparklesIcon,
  WalletIcon
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
import { dashboardMockData } from './data/dashboardMockData'

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
const campaignQuery = ref('')
const selectedReportChannel = ref('Telegram')
const selectedReportTemplate = ref('Шаблон: Яндекс')
const selectedSchedule = ref('Ежедневно в 10:00')
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

const selectSchedule = (option) => {
  selectedSchedule.value = option
  closeMenu('report-schedule')
  handleReportSave(option)
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
  { name: 'VK Ads Manager', value: 'vk', color: '#2563eb', bg: '#f3f7ff', darkBg: 'rgba(74, 122, 255, 0.14)', asset: vkAdsIcon, imageClass: 'vk', icon: EyeIcon },
  { name: 'Avito Ads', value: 'avito', color: '#579f75', bg: '#eef8f1', darkBg: 'rgba(87, 159, 117, 0.14)', asset: '/admirra/img/integrations/avito.svg', imageClass: 'avito', icon: CursorArrowRippleIcon }
]

const reportChannels = [
  { name: 'Telegram', color: '#eef8ff', bg: '#f3f8ff', darkBg: 'rgba(42, 171, 238, 0.14)', asset: '/admirra/img/icons/telegram.png', imageClass: 'telegram' },
  { name: 'E-mail', color: '#2563eb', bg: '#fff', darkBg: 'transparent', icon: EnvelopeIcon },
  { name: 'Max', color: '#f4f7fb', bg: '#fff', darkBg: 'rgba(255, 255, 255, 0.06)', asset: '/admirra/img/icons/max.png', imageClass: 'max' }
]

const filterChannels = [
  { name: 'Все каналы', value: 'all', color: '#b3b3b3', icon: ChartBarIcon },
  ...channels
]

// Integration point: replace dashboardMockData with an API-backed state object
// that keeps the same field names used below.
const reportTemplateOptions = dashboardMockData.reportTemplateOptions
const scheduleOptions = dashboardMockData.scheduleOptions
const chartPeriodOptions = dashboardMockData.chartPeriodOptions

const getChipBackground = (item) => (isDarkMode.value ? (item.darkBg ?? item.bg) : item.bg)

const filteredCampaigns = computed(() => {
  const query = campaignQuery.value.trim().toLowerCase()
  const items = allCampaigns.value.length ? allCampaigns.value : dashboardMockData.campaigns.map((name, id) => ({ id: `mock-${id}`, name }))
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
  const values = {
    expenses: formatMoney(withVat(data.expenses)),
    impressions: formatNumber(data.impressions),
    clicks: formatNumber(data.clicks),
    cpc: formatMoney(withVat(data.cpc)),
    leads: `${formatNumber(data.leads)} шт.`,
    cpa: formatMoney(withVat(data.cpa))
  }
  return dashboardMockData.metrics.map((metric) => {
    const trendRaw = Number(trends[metric.key] ?? metric.trend ?? 0)
    return {
    ...metric,
    value: values[metric.key] || metric.value,
    trend: formatTrend(trendRaw),
    negative: trendRaw < 0,
    delta: 'за выбранный период',
    icon: metricIcons[metric.icon] || ChartBarIcon
  }
  })
})

const chartSourceValues = computed(() => {
  const values = dynamics.value?.costs || []
  return values.length ? values.map((value) => withVat(value)) : dashboardMockData.chart.previewPoints.map((point) => 226 - point.y)
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
const dateLabels = computed(() => dynamics.value?.labels?.length ? dynamics.value.labels : dashboardMockData.chart.labels)

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
  const colors = ['#3f63f6', '#f39a72', '#dff9e7', '#8ada70', '#d38cff']
  if (!reportGoals.value.length) {
    return dashboardMockData.goals.map((g) => {
      const pct = parseFloat(g.value.match(/\(([0-9.]+)%\)/)?.[1] ?? 0)
      return { ...g, pct }
    })
  }
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
  if (!items.length) return 'conic-gradient(#e5e7eb 0 100%)'
  let offset = 0
  const segments = items.map((goal) => {
    const start = offset.toFixed(2)
    offset += goal.pct ?? 0
    return `${goal.color} ${start}% ${offset.toFixed(2)}%`
  })
  if (offset < 99.9) segments.push(`#e5e7eb ${offset.toFixed(2)}% 100%`)
  return `conic-gradient(${segments.join(', ')})`
})

const goalsTotalLabel = computed(() => {
  const total = reportGoals.value.reduce((sum, item) => sum + Number(item.count ?? item.conversions ?? item.value ?? 0), 0)
  return `${formatNumber(total || summary.value?.leads || 0)} шт.`
})

const campaignRows = computed(() => {
  const rows = campaigns.value?.length ? campaigns.value : []
  if (!rows.length) return dashboardMockData.campaignRows
  return rows.slice(0, 5).map((campaign, index) => ({
    name: campaign.name || `Кампания ${index + 1}`,
    tint: index % 3 === 2 ? 'blue' : 'green',
    cost: formatMoney(withVat(campaign.cost)),
    impressions: formatNumber(campaign.impressions),
    clicks: formatNumber(campaign.clicks),
    cpc: formatMoney(withVat(campaign.cpc)),
    leads: `${formatNumber(campaign.conversions ?? campaign.leads)} шт.`,
    cpa: formatMoney(withVat(campaign.cpa)),
    trendCost: formatTrend(campaign.trend_cost ?? 0),
    trendImpressions: formatTrend(campaign.trend_impressions ?? 0),
    trendClicks: formatTrend(campaign.trend_clicks ?? 0),
    trendCpc: formatTrend(campaign.trend_cpc ?? 0),
    trendLeads: formatTrend(campaign.trend_conversions ?? 0),
    trendCpa: formatTrend(campaign.trend_cpa ?? 0)
  }))
})

const creatives = computed(() => {
  if (!topAds.value.length) return dashboardMockData.creatives
  const classes = ['city', 'blue', 'house']
  return topAds.value.slice(0, 3).map((post, index) => ({
    id: post.id || `${post.title}-${index}`,
    badge: post.subtitle || (post.platform === 'yandex' ? 'Яндекс.Директ' : post.platform === 'avito' ? 'Avito Ads' : 'VK Ads'),
    title: post.title || 'Креатив',
    heading: post.heading || post.title || '—',
    text: post.text || post.description || `${formatNumber(post.impressions)} показов, ${formatNumber(post.clicks)} кликов, CTR ${post.ctr ?? '—'}%`,
    imageUrl: post.image_url || post.imageUrl || '',
    class: classes[index % classes.length]
  }))
})
const aiComments = computed(() => {
  if (!reportComment.value) return dashboardMockData.aiComments
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

const handleReportSave = async (schedule) => {
  try {
    await api.patch('/auth/me', { report_schedule: schedule })
    userReportSettings.value.report_schedule = schedule
    toaster.success('Расписание сохранено')
  } catch {
    toaster.error('Не удалось сохранить расписание')
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
  refreshUserReportSettings()
  fetchIntegrations()
  fetchReportGoals()
  fetchTopAds()
})
</script>

<style scoped>
.figma-dashboard {
  width: 100%;
  max-width: 1590px;
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
  border-radius: 999px;
  color: #fff;
}

.chip-icon {
  width: 0.9rem;
  height: 0.9rem;
}

.panel-reports {
  display: grid;
  grid-template-columns: minmax(28rem, 1fr) 21rem 22.8rem 16.9rem;
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
  padding: 0 1.8rem;
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
}

.dashboard-date-picker :deep(.date-range-picker-container) {
  width: 100%;
}

:global(.calendar-popup) {
  width: min(560px, calc(100vw - 24px)) !important;
  max-height: min(520px, calc(100vh - 24px));
  overflow: auto;
  padding: 16px !important;
  border: 1px solid #ebebeb !important;
  border-radius: 14px !important;
  background: #fff !important;
  box-shadow: 0 18px 48px rgba(15, 23, 42, 0.12) !important;
}

:global(.calendar-popup .drp-quick-row) {
  gap: 6px !important;
  margin: 0 0 14px !important;
  padding: 0 0 12px !important;
  border-bottom: 1px solid #eef0f3 !important;
  align-items: center !important;
}

:global(.calendar-popup .drp-quick) {
  height: 28px !important;
  min-height: 0 !important;
  padding: 0 10px !important;
  border: 1px solid #eef0f3 !important;
  border-radius: 9px !important;
  background: #f7f8fa !important;
  color: #4b5563 !important;
  font-size: 12px !important;
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
  gap: 22px !important;
}

:global(.calendar-popup .drp-month-head) {
  margin-bottom: 10px !important;
}

:global(.calendar-popup .drp-month-head h3) {
  color: #111827 !important;
  font-size: 15px !important;
  line-height: 1.2 !important;
  font-weight: 700 !important;
  letter-spacing: 0 !important;
}

:global(.calendar-popup .drp-nav) {
  width: 24px !important;
  height: 24px !important;
  min-height: 24px !important;
  padding: 0 !important;
  border-radius: 999px !important;
  color: #4b5563 !important;
  background: transparent !important;
}

:global(.calendar-popup .drp-nav:hover) {
  background: #f3f6fb !important;
}

:global(.calendar-popup .drp-nav svg) {
  width: 14px !important;
  height: 14px !important;
  color: currentColor !important;
}

:global(.calendar-popup .drp-weekdays) {
  gap: 4px !important;
  margin-bottom: 4px !important;
}

:global(.calendar-popup .drp-weekday) {
  padding: 0 !important;
  color: #6b7280 !important;
  font-size: 10px !important;
  line-height: 20px !important;
  font-weight: 600 !important;
  letter-spacing: 0 !important;
  text-transform: lowercase !important;
}

:global(.calendar-popup .drp-weekday.text-red-500) {
  color: #ef4444 !important;
}

:global(.calendar-popup .drp-days) {
  gap: 4px !important;
}

:global(.calendar-popup .drp-day) {
  width: 30px !important;
  height: 30px !important;
  min-height: 30px !important;
  padding: 0 !important;
  border-radius: 8px !important;
  border: 0 !important;
  font-size: 12px !important;
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
  border-radius: 8px !important;
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
  gap: 10px !important;
  margin-top: 16px !important;
  padding-top: 12px !important;
  border-top: 1px solid #eef0f3 !important;
  align-items: end !important;
}

:global(.calendar-popup .drp-label) {
  margin: 0 0 6px !important;
  color: #6b7280 !important;
  font-size: 11px !important;
  line-height: 1 !important;
  font-weight: 600 !important;
  letter-spacing: 0 !important;
  text-transform: none !important;
}

:global(.calendar-popup .drp-input) {
  height: 38px !important;
  padding: 0 12px !important;
  border: 1px solid #d9dee6 !important;
  border-radius: 10px !important;
  background: #fff !important;
  color: #374151 !important;
  font-size: 12px !important;
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
  padding-bottom: 10px !important;
  color: #9ca3af !important;
  font-size: 16px !important;
}

:global(.calendar-popup .drp-apply) {
  height: 38px !important;
  min-height: 38px !important;
  margin: 0 !important;
  padding: 0 18px !important;
  border-radius: 9px !important;
  background: #2563eb !important;
  color: #fff !important;
  font-size: 12px !important;
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

@media (max-width: 640px) {
  :global(.calendar-popup) {
    width: min(320px, calc(100vw - 16px)) !important;
    max-height: calc(100vh - 16px);
    padding: 14px !important;
  }

  :global(.calendar-popup .drp-quick-row) {
    gap: 6px !important;
    margin-bottom: 12px !important;
    padding-bottom: 10px !important;
  }

  :global(.calendar-popup .drp-quick) {
    height: 28px !important;
    padding: 0 8px !important;
    font-size: 11px !important;
  }

  :global(.calendar-popup .drp-month-grid) {
    grid-template-columns: 1fr !important;
    gap: 16px !important;
  }

  :global(.calendar-popup .drp-month-head h3) {
    font-size: 15px !important;
  }

  :global(.calendar-popup .drp-weekdays),
  :global(.calendar-popup .drp-days) {
    gap: 4px !important;
  }

  :global(.calendar-popup .drp-day) {
    width: 34px !important;
    height: 34px !important;
    min-height: 34px !important;
    font-size: 12px !important;
    border-radius: 8px !important;
  }

  :global(.calendar-popup .drp-weekday) {
    font-size: 10px !important;
    line-height: 20px !important;
  }

  :global(.calendar-popup .drp-fields) {
    display: grid !important;
    grid-template-columns: 1fr !important;
    gap: 8px !important;
    margin-top: 14px !important;
    padding-top: 12px !important;
  }

  :global(.calendar-popup .drp-fields > .text-gray-400) {
    display: none !important;
  }

  :global(.calendar-popup .drp-label) {
    font-size: 11px !important;
  }

  :global(.calendar-popup .drp-input) {
    height: 38px !important;
    font-size: 12px !important;
  }

  :global(.calendar-popup .drp-apply) {
    width: 100% !important;
    height: 38px !important;
    margin-top: 4px !important;
    font-size: 12px !important;
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
  gap: 2rem;
  margin-top: 3rem;
}

.metric-card {
  min-height: 23.9rem;
  padding: 3rem;
  border-radius: 1.5rem;
  background: #fff;
}

.metric-head {
  display: grid;
  grid-template-columns: 5.2rem 1fr 4rem;
  gap: 2.3rem;
  align-items: start;
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

.metric-card h3 {
  margin: 0;
  font-size: 2rem;
  font-weight: 500;
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
  border-radius: 999px;
  background: #fff;
  color: #b3b3b3;
}

.metric-card strong {
  display: block;
  margin-top: 3.5rem;
  font-size: 3rem;
  font-weight: 700;
  line-height: 1;
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
}

.trend.negative {
  background: #fef2f2;
  color: #ef4444;
}

.trend svg {
  width: 1.8rem;
  height: 1.8rem;
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
  border-radius: 999px;
  background: conic-gradient(#3f63f6 0 52%, #f39a72 52% 78%, #dff9e7 78% 100%);
  -webkit-mask: radial-gradient(circle, transparent 0 34%, #000 35%);
  mask: radial-gradient(circle, transparent 0 34%, #000 35%);
}

.donut-wrap::after {
  content: '';
  position: absolute;
  width: 13.4rem;
  height: 13.4rem;
  border-radius: 999px;
  background: #fff;
  box-shadow: 0 1rem 2rem rgba(15, 23, 42, 0.05);
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
  border: 1px solid #f0f0f0;
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
  border-radius: 999px;
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

.campaign-row.green {
  background: #fbfff6;
}

.campaign-row.blue {
  background: #f7f9ff;
}

.campaign-row b {
  display: inline-flex;
  margin-left: 0.8rem;
  padding: 0.4rem 0.6rem;
  border-radius: 0.4rem;
  background: #e5fbea;
  color: #18b44d;
  font-size: 0.9rem;
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
  border-radius: 999px;
  background: #e9e9e9;
  overflow: hidden;
}

.progress-line i {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: #2563eb;
}

.progress-line b {
  font-weight: 400;
  text-align: right;
}

.place-dot {
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 999px;
  background: #ef4444;
}

@media (max-width: 1500px) {
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

@media (max-width: 820px) {
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
  padding: 30px 25px;
  overflow: hidden;
}

.panel {
  border-radius: 15px;
  box-shadow: none;
}

.top-grid {
  grid-template-columns: minmax(320px, 494px) minmax(0, 1fr);
  gap: 20px;
}

.panel-channels,
.panel-reports {
  min-height: 131px;
  padding: 25px;
}

.panel h2,
.panel-channels h2,
.panel-reports h2 {
  font-size: 20px;
}

.chips-row {
  gap: 15px;
  margin-top: 20px;
}

.chip {
  height: 46px;
  gap: 10px;
  padding: 0 15px;
  border-radius: 12px;
  font-size: 13px;
}

.chip-dot {
  width: 14px;
  height: 14px;
}

.chip-icon {
  width: 9px;
  height: 9px;
}

.panel-reports {
  grid-template-columns: minmax(260px, 1fr) minmax(160px, 210px) minmax(190px, 228px) auto;
  gap: 20px;
}

.report-schedule p {
  margin-bottom: 20px;
  font-size: 13px;
}

.select-like,
.filter-btn,
.export-btn {
  height: 46px;
  gap: 12px;
  padding: 0 15px;
  border-radius: 12px;
  font-size: 13px;
}

.dashboard-date-picker {
  flex-basis: auto;
}

.select-like svg,
.filter-btn svg,
.export-btn svg,
.primary-report svg,
.sync-btn svg,
.see-all svg,
.month-select svg {
  width: 16px;
  height: 16px;
}

.primary-report {
  height: 46px;
  gap: 10px;
  padding: 0 18px;
  border-radius: 12px;
  font-size: 13px;
}

.heading-section {
  margin-top: 45px;
}

.heading-section h1 {
  margin-bottom: 24px;
  font-size: 28px;
}

.filters-row {
  gap: 10px;
}

.filters-row .filter-btn {
  min-width: 140px;
}

.date-btn {
  min-width: 257px;
}

.sync-btn {
  min-height: 46px;
  gap: 10px;
  padding: 0 14px;
  font-size: 13px;
}

.export-btn {
  min-width: 160px;
}

.dropdown-panel {
  top: calc(100% + 8px);
  min-width: 220px;
  padding: 10px;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(15, 23, 42, 0.12);
}

.dropdown-panel button {
  gap: 10px;
  padding: 10px;
  border-radius: 8px;
  font-size: 13px;
}

.dropdown-panel button svg {
  width: 16px;
  height: 16px;
}

.campaigns {
  min-width: 360px;
}

.search-box {
  gap: 10px;
  height: 44px;
  margin-bottom: 8px;
  padding: 0 12px;
  border-radius: 10px;
}

.search-box svg {
  width: 18px;
  height: 18px;
}

.search-box input {
  font-size: 13px;
}

.kpi-grid {
  gap: 15px;
  margin-top: 25px;
}

.metric-card {
  min-height: 174px;
  padding: 25px;
  border-radius: 15px;
}

.metric-head {
  grid-template-columns: 44px 1fr 34px;
  gap: 16px;
}

.metric-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
}

.metric-icon svg,
.round-action svg,
.ai-title svg {
  width: 18px;
  height: 18px;
}

.metric-card h3 {
  font-size: 16px;
}

.metric-card p {
  margin-top: 9px;
  font-size: 12px;
}

.round-action {
  width: 34px;
  height: 34px;
}

.metric-card strong {
  margin-top: 25px;
  font-size: 24px;
}

.metric-foot {
  gap: 14px;
  margin-top: 20px;
  font-size: 13px;
}

.trend {
  height: 28px;
  gap: 5px;
  padding: 0 8px;
  border-radius: 4px;
}

.trend svg {
  width: 14px;
  height: 14px;
}

.chart-goals-grid {
  grid-template-columns: minmax(0, 1.5fr) minmax(360px, 0.9fr);
  gap: 20px;
  margin-top: 20px;
}

.chart-panel,
.goals-panel {
  min-height: 360px;
  padding: 25px;
}

.panel-title-row {
  gap: 20px;
}

.month-select,
.see-all {
  height: 35px;
  gap: 10px;
  padding: 0 14px;
  border-radius: 12px;
  font-size: 13px;
}

.chart-area {
  height: 265px;
  margin-top: 24px;
}

.axis-labels text,
.tooltip-pin text {
  font-size: 11px;
}

.goals-content {
  grid-template-columns: minmax(180px, 240px) minmax(0, 1fr);
  gap: 24px;
  margin-top: 24px;
}

.donut-wrap {
  width: 220px;
  height: 220px;
}

.donut-wrap::after {
  width: 104px;
  height: 104px;
}

.donut-wrap span {
  font-size: 16px;
}

.goals-list {
  gap: 15px;
}

.goal-item {
  border-radius: 8px;
}

.goal-item div {
  gap: 12px;
  min-height: 41px;
  padding: 0 16px;
  font-size: 13px;
}

.goal-item div span {
  width: 9px;
  height: 9px;
}

.goal-item p {
  padding: 12px 16px;
  font-size: 13px;
}

.campaigns-panel {
  margin-top: 20px;
  padding: 25px;
}

.campaign-table {
  gap: 12px;
  margin-top: 20px;
}

.campaign-row {
  grid-template-columns: minmax(260px, 2.1fr) repeat(6, minmax(105px, 1fr));
  min-width: 1120px;
  min-height: 50px;
  padding: 0 20px;
  border-radius: 10px;
  font-size: 12px;
}

.campaign-row b {
  margin-left: 6px;
  padding: 3px 5px;
  font-size: 9px;
}

.bottom-grid {
  grid-template-columns: minmax(430px, 0.95fr) minmax(400px, 1fr) minmax(270px, 0.55fr);
  gap: 20px;
  margin-top: 20px;
}

.creatives-panel,
.ai-panel {
  min-height: 360px;
  padding: 25px;
}

.creatives-row {
  gap: 13px;
  margin-top: 22px;
}

.creative-card {
  flex-basis: 160px;
}

.creative-image {
  min-height: 150px;
  padding: 14px;
  border-radius: 16px;
}

.creative-image span {
  font-size: 9px;
}

.creative-image strong {
  margin-top: 8px;
  font-size: 14px;
}

.creative-card p {
  margin: 16px 0 7px;
  font-size: 12px;
}

.creative-card em {
  font-size: 12px;
}

.ai-title {
  gap: 16px;
}

.ai-title span {
  width: 36px;
  height: 36px;
  border-radius: 8px;
}

.ai-panel ul {
  gap: 14px;
  margin-top: 20px;
  padding-left: 20px;
  font-size: 13px;
}

.ai-panel > p {
  margin-top: 22px;
  font-size: 12px;
}

.side-stat-stack {
  gap: 20px;
}

.mini-stat-panel {
  min-height: 170px;
  padding: 25px;
}

.mini-stat-panel h2 {
  margin-bottom: 22px;
}

.progress-line {
  grid-template-columns: minmax(82px, 1fr) 86px 42px;
  gap: 10px;
  margin-top: 15px;
  font-size: 12px;
}

.progress-line span {
  gap: 8px;
}

.progress-line span svg,
.place-dot {
  width: 14px;
  height: 14px;
}

.progress-line div {
  height: 5px;
}

@media (max-width: 1600px) {
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

@media (max-width: 1180px) {
  .kpi-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .figma-dashboard {
    padding: 20px 15px;
  }

  .kpi-grid {
    grid-template-columns: 1fr;
  }

  .metric-card {
    min-height: 160px;
  }

  .goals-content {
    grid-template-columns: 1fr;
  }

  .donut-wrap {
    width: 200px;
    height: 200px;
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

  .ml-auto {
    margin-left: 0;
  }

  .campaign-row {
    min-width: 1060px;
  }
}

/* Figma top-panel alignment */
.top-grid {
  grid-template-columns: minmax(360px, 494px) minmax(760px, 1fr);
  gap: 20px;
  align-items: start;
}

.panel-channels,
.panel-reports {
  height: 131px;
  min-height: 131px;
  padding: 25px;
  overflow: visible;
}

.panel-reports {
  display: grid;
  grid-template-columns: minmax(340px, 1fr) 209px 228px 169px;
  column-gap: 20px;
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
  height: 20px;
  line-height: 1;
}

.panel-channels .chips-row,
.panel-reports .chips-row {
  flex-wrap: nowrap;
  gap: 15px;
  margin-top: 20px;
}

.panel-channels .chip,
.panel-reports .chip {
  flex: 0 0 auto;
  height: 46px;
  gap: 10px;
  padding: 0 15px;
  border-radius: 999px;
  box-shadow: none;
  color: #4b4b4b;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  line-height: 1;
  transition: background-color 0.5s, border-color 0.25s, box-shadow 0.25s, transform 0.75s;
}

.panel-channels .chip:hover,
.panel-reports .chip:hover {
  box-shadow: 0 10px 22px rgba(15, 23, 42, 0.06);
  transform: translateY(-1px);
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
  width: 14px;
  height: 14px;
  object-fit: contain;
}

.chip-img.vk {
  transform: scale(1.35);
}

.chip-img.telegram,
.chip-img.max {
  width: 18px;
  height: 18px;
}

.chip-letter {
  color: #fff;
  font-size: 9px;
  font-weight: 700;
  line-height: 1;
}

.report-schedule p {
  display: flex;
  align-items: center;
  height: 20px;
  margin: 0 0 20px;
  color: #b3b3b3;
  font-size: 13px;
  line-height: 1;
}

.select-like {
  width: 100%;
  height: 46px;
  border-color: #ebebeb;
  border-radius: 15px;
  background: #fff;
  color: #b3b3b3;
  cursor: pointer;
  line-height: 1;
  transition: border-color 0.2s, box-shadow 0.25s, transform 0.75s;
}

.top-select .select-like {
  margin-top: 20px;
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
  width: 169px;
  height: 46px;
  padding: 0 15px;
  justify-content: center;
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
  width: 24px;
  height: 24px;
  margin-left: auto;
  border-radius: 999px;
  background: #f5f7f9;
  color: #b3b3b3;
  flex: 0 0 auto;
  transition: transform 0.3s;
}

.custom-select .cs-arrow svg {
  width: 14px;
  height: 14px;
}

.custom-select.open .cs-arrow {
  transform: rotate(180deg);
}

.custom-select .cs-list {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  z-index: 99;
  display: flex;
  min-width: 100%;
  flex-direction: column;
  overflow: hidden;
  padding: 0;
  border-radius: 8px;
  background-color: #fff;
  box-shadow: 0 0 0 1px rgba(68, 68, 68, 0.1);
  opacity: 0;
  pointer-events: none;
  transform: scale(0.75) translateY(-21px);
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
  min-height: 43px;
  gap: 10px;
  padding: 12px 25px 12px 17px;
  border: 0;
  background: transparent;
  color: rgba(0, 0, 0, 0.7);
  cursor: pointer;
  font-size: 13px;
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

.dashboard-select .cs-list {
  min-width: 230px;
}

.campaigns.cs-list {
  min-width: 360px;
}

.export-select .cs-list {
  right: 0;
  left: auto;
}

.heading-section h1 {
  font-weight: 600;
}

.dashboard-select .cs-arrow {
  width: 16px;
  height: 16px;
  background: #f5f7f9;
}

.dashboard-select .cs-arrow svg {
  width: 10px;
  height: 10px;
}

.top-select .cs-arrow {
  width: 24px;
  height: 24px;
}

.top-select .cs-arrow svg {
  width: 14px;
  height: 14px;
}

.export-select .cs-arrow {
  width: 24px;
  height: 24px;
  background: #1f55d9;
  color: #fff;
}

.export-select .cs-arrow svg {
  width: 12px;
  height: 12px;
}

.export-select.open .cs-arrow {
  background: #1748bf;
}

.custom-select .cs-option svg {
  width: 16px;
  height: 16px;
  flex: 0 0 16px;
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

@media (max-width: 1500px) {
  .top-grid {
    grid-template-columns: 1fr;
  }

  .panel-reports {
    height: auto;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    row-gap: 20px;
  }

  .primary-report {
    width: 100%;
  }
}

@media (max-width: 760px) {
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

.figma-dashboard.is-dark .trend.negative {
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
  box-shadow: 0 1rem 2rem rgba(0, 0, 0, 0.12);
}

.figma-dashboard.is-dark .goal-item {
  border-color: rgba(255, 255, 255, 0.08);
}

.figma-dashboard.is-dark .goal-item p {
  background: rgba(0, 0, 0, 0.08);
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
  min-height: 260px;
  aspect-ratio: 880 / 300;
  overflow-x: auto;
  overflow-y: visible;
  overscroll-behavior-x: contain;
}

.chart-area svg {
  flex: 0 0 auto;
  display: block;
  width: max(720px, 100%);
  height: auto;
  aspect-ratio: 880 / 260;
  max-height: 100%;
}

.goals-content {
  grid-template-columns: minmax(180px, 240px) minmax(0, 1fr);
  min-width: 0;
}

.donut-wrap {
  width: clamp(180px, 18vw, 240px);
  height: clamp(180px, 18vw, 240px);
  max-width: 100%;
}

.donut-wrap::after {
  width: 48%;
  height: 48%;
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

.bottom-grid,
.side-stat-stack,
.mini-stat-panel {
  min-width: 0;
}

.progress-line {
  grid-template-columns: minmax(0, 1fr) minmax(72px, 120px) auto;
  min-width: 0;
}

.progress-line span {
  min-width: 0;
}

@media (max-width: 1180px) {
  .chart-area {
    min-height: 260px;
  }

  .bottom-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .chart-panel,
  .goals-panel,
  .campaigns-panel,
  .creatives-panel,
  .ai-panel,
  .mini-stat-panel {
    padding: 20px;
  }

  .panel-title-row {
    align-items: flex-start;
    flex-direction: column;
  }

  .chart-area {
    min-height: 260px;
    aspect-ratio: auto;
    margin-top: 18px;
  }

  .chart-area svg {
    width: 680px;
  }

  .goals-content {
    justify-items: center;
  }

  .goals-list {
    width: 100%;
  }

  .donut-wrap {
    width: min(220px, 72vw);
    height: min(220px, 72vw);
  }
}
</style>
