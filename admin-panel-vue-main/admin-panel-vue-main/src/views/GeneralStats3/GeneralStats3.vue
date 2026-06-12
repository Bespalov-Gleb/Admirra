<template>
  <div ref="dashboardRef" class="figma-dashboard" :class="{ 'is-dark': isDarkMode }">
    <section class="top-grid">
      <div class="panel panel-channels">
        <h2>Подключенные каналы</h2>
        <div class="channel-balance-block">
          <div v-if="channelBalances.length" class="channel-balance-list">
            <div
              v-for="balance in channelBalances"
              :key="balance.id"
              class="analytics-balance-tile"
              :style="{ '--balance-bg': balance.bg, '--balance-color': balance.color }"
            >
              <img :src="balance.asset" :alt="balance.name" class="analytics-balance-icon" />
              <span class="analytics-balance-name">{{ balance.name }}</span>
              <span class="analytics-balance-value">{{ balance.value }}</span>
            </div>
          </div>
          <div v-else class="channel-balance-empty">Нет подключенных РК</div>
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
              :data-channel="item.value"
              :class="{
                active: isReportChannelEnabled(item),
                connected: isReportChannelConnected(item),
                unlinked: item.linkable && !isReportChannelConnected(item),
                disabled: item.disabled
              }"
              type="button"
              :title="reportChannelTitle(item)"
              @click="handleReportChannelClick(item)"
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

        <button class="primary-report" type="button" :disabled="sendingTg || sendingEmail || sendingMax" @click="handleSendSelectedReport">
          {{ sendingTg || sendingEmail || sendingMax ? 'Отправка...' : 'Отправить отчет сейчас' }}
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

        <div
          v-if="directionsEnabled"
          class="filter-wrap custom-select dashboard-select"
          :class="{ open: openMenu === 'directions' }"
          v-click-outside="() => closeMenu('directions')"
        >
          <button class="filter-btn cs-head" type="button" :class="{ 'cs-head--active': selectedDirectionId }" @click="toggleMenu('directions')">
            <span class="cs-current">{{ selectedDirectionLabel }}</span>
            <span class="cs-arrow">
              <ChevronDownIcon />
            </span>
          </button>
          <div class="cs-list dropdown-panel directions-menu" @click.stop>
            <button type="button" class="cs-option" :class="{ selected: !selectedDirectionId }" @click="selectDirection(null)">
              Все {{ directionLabelLower }}
            </button>
            <button
              v-for="item in directionStats.items"
              :key="item.id"
              type="button"
              class="cs-option direction-option"
              :class="{ selected: selectedDirectionId === item.id }"
              @click="selectDirection(item)"
            >
              <span>{{ item.name }}</span>
              <small>{{ item.campaign_count }} камп.</small>
            </button>
            <div class="directions-menu__divider"></div>
            <button type="button" class="cs-option direction-action" @click="openDirectionEditor()">
              + Создать направление
            </button>
            <button type="button" class="cs-option direction-action" @click="openDirectionManager">
              Управление направлениями
            </button>
          </div>
        </div>

        <div class="filter-wrap custom-select dashboard-select" :class="{ open: openMenu === 'campaigns' }" v-click-outside="closeCampaignMenu">
          <button class="filter-btn cs-head" type="button" :class="{ 'cs-head--active': filters.campaign_ids.length > 0 }" @click="openCampaignMenu">
            <span class="cs-current">{{ selectedCampaignLabel }}</span>
            <span class="cs-arrow">
              <ChevronDownIcon />
            </span>
          </button>
          <div class="cs-list dropdown-panel campaigns-multiselect" @click.stop>
            <label class="search-box">
              <MagnifyingGlassIcon />
              <input v-model="campaignQuery" type="search" placeholder="Поиск кампании" />
            </label>
            <div class="cmp-mass-actions">
              <button type="button" class="cmp-mass-btn" @click="campaignSelectAll">Выбрать все</button>
              <button type="button" class="cmp-mass-btn" @click="campaignDeselectAll">Снять все</button>
            </div>
            <div class="cmp-scroll">
              <template v-if="campaignGroupActive.length">
                <div v-for="campaign in campaignGroupActive" :key="campaign.id" class="cmp-row" @click="togglePendingCampaign(campaign.id)">
                  <input type="checkbox" class="cmp-check" :checked="pendingCampaignIds.includes(campaign.id)" @click.stop="togglePendingCampaign(campaign.id)" />
                  <span class="cmp-status-dot" :class="`cmp-status-dot--${campaignPlatformStatus(campaign)}`" :title="campaignStatusTitle(campaign)"></span>
                  <span class="cmp-name">{{ campaign.name }}</span>
                </div>
              </template>
              <template v-if="campaignGroupArchive.length">
                <button type="button" class="cmp-group-header" @click="campaignArchiveOpen = !campaignArchiveOpen">
                  Архив ({{ campaignGroupArchive.length }})
                  <ChevronDownIcon class="cmp-group-chevron" :class="{ 'cmp-group-chevron--open': campaignArchiveVisible }" />
                </button>
                <template v-if="campaignArchiveVisible">
                  <div v-for="campaign in campaignGroupArchive" :key="campaign.id" class="cmp-row cmp-row--archive" @click="togglePendingCampaign(campaign.id)">
                    <input type="checkbox" class="cmp-check" :checked="pendingCampaignIds.includes(campaign.id)" @click.stop="togglePendingCampaign(campaign.id)" />
                    <span class="cmp-status-dot" :class="`cmp-status-dot--${campaignPlatformStatus(campaign)}`" :title="campaignStatusTitle(campaign)"></span>
                    <span class="cmp-name">{{ campaign.name }}</span>
                  </div>
                </template>
              </template>
              <div v-if="!campaignGroupActive.length && !campaignGroupArchive.length" class="cmp-empty">Нет кампаний</div>
            </div>
            <div class="cmp-footer">
              <button type="button" class="cmp-footer-btn cmp-footer-btn--reset" @click="campaignReset">Сбросить</button>
              <button type="button" class="cmp-footer-btn cmp-footer-btn--apply" @click="campaignApply">Применить</button>
            </div>
          </div>
        </div>

        <div class="filter-wrap custom-select dashboard-select dashboard-period-select" :class="{ open: openMenu === 'period' }" v-click-outside="closePeriodMenu">
          <button ref="periodTriggerRef" class="filter-btn cs-head" type="button" @click="toggleMenu('period')">
            <span class="cs-current">{{ periodLabel }}</span>
            <span class="cs-arrow">
              <ChevronDownIcon />
            </span>
          </button>
          <Teleport to="body">
            <div
              v-if="openMenu === 'period'"
              ref="periodPopoverRef"
              class="period-popover period-list"
              :style="periodPopoverStyle"
            >
              <template v-for="(opt, index) in projectPeriodOptions" :key="opt.value || `${opt.type}-${index}`">
                <DateRangePicker
                  v-if="opt.type === 'label'"
                  v-model="customPeriodRange"
                  class="project-period-custom-picker"
                  :trigger-text="opt.label"
                  @change="selectCustomDashboardPeriod"
                />
                <div v-else-if="opt.type === 'divider'" class="period-list__divider"></div>
                <button
                  v-else
                  type="button"
                  class="period-option"
                  :class="{ selected: periodKey === opt.value }"
                  @click="selectPeriodPreset(opt.value)"
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

        <span class="sync-status-label" :class="{ active: dashboardSyncInProgress }">
          <ArrowPathIcon :class="{ spinning: dashboardSyncInProgress }" />
          {{ syncStatusLabel }}
        </span>

        <div class="filter-right-group">
          <label class="nds-check-wrap">
            <input type="checkbox" v-model="includeVat" class="nds-checkbox" />
            <span class="nds-label">НДС 22%</span>
          </label>

          <button class="sync-btn sync-btn-ghost" type="button" :disabled="dashboardSyncInProgress" @click="handleSyncIntegrations">
            <ArrowPathIcon :class="{ spinning: dashboardSyncInProgress }" />
            {{ dashboardSyncInProgress ? 'Синхронизация...' : 'Синхронизация' }}
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

    <div v-if="filters.campaign_ids.length > 0" class="campaign-filter-banner">
      <span v-if="selectedDirection">Показаны данные по направлению «{{ selectedDirection.name }}» · {{ filters.campaign_ids.length }} камп.</span>
      <span v-else>Показаны данные по {{ filters.campaign_ids.length }} {{ filters.campaign_ids.length === 1 ? 'кампании' : 'кампаниям' }} из {{ allCampaigns.length }}</span>
      <button type="button" class="campaign-filter-banner__reset" @click="campaignReset">сбросить</button>
    </div>

    <div v-if="dashboardSyncInProgress" class="dashboard-sync-banner">
      <span class="dashboard-sync-banner__icon">
        <ArrowPathIcon class="spinning" />
      </span>
      <div>
        <strong>Выполняется синхронизация</strong>
        <p>{{ syncProgressLabel }}</p>
      </div>
    </div>

    <DetectorBanner
      v-if="filters.client_id && (detectorSummary?.warning_count > 0 || detectorSummary?.problem_count > 0 || detectorSummary?.warmup_status === 'warming_up')"
      :warning-count="detectorSummary?.warning_count || 0"
      :problem-count="detectorSummary?.problem_count || 0"
      :severity="detectorSummary?.max_severity"
      :hypothesis="detectorBannerHypothesis"
      :warmup-status="detectorSummary?.warmup_status"
      :warmup-days-left="detectorSummary?.warmup_days_left"
      :dismissible="Boolean(detectorBannerAlert)"
      :action-label="detectorBannerAlert ? 'Спросить AI' : ''"
      @action="openAssistantForDetectorAlert"
      @dismiss="handleDismissBanner"
      class="detector-banner-slot"
    />

    <div v-if="dashboardSyncInProgress" class="kpi-grid kpi-grid--sync">
      <article v-for="item in METRIC_CONFIG" :key="item.key" class="metric-card metric-card--skeleton">
        <span class="metric-skeleton-icon"></span>
        <div class="metric-skeleton-lines">
          <span></span>
          <strong></strong>
        </div>
        <em></em>
      </article>
    </div>

    <VueDraggable
      v-else
      v-model="visibleSlots"
      tag="section"
      class="kpi-grid"
      :animation="150"
      handle=".drag-handle"
      draggable=".metric-card-item"
      @end="saveKpiConfig"
    >
      <article v-for="key in visibleSlots" :key="key" class="metric-card metric-card-item" :class="metricAnomalyClass(key)">
        <span
          v-if="getMetricAnomaly(key)"
          class="anomaly-dot"
          :class="`anomaly-dot--${getMetricAnomaly(key).severity}`"
          :title="getMetricAnomalyTooltip(key)"
          @click.stop="handleDismissAnomaly(key)"
        ></span>
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

    <section
      v-if="directionsEnabled && !selectedDirectionId && directionStats.items.length"
      class="directions-panel panel"
      :class="{ 'panel--syncing': dashboardSyncInProgress }"
    >
      <div class="directions-head">
        <div>
          <p class="directions-kicker">Разбивка кампаний</p>
          <h2>{{ directionStats.label }}</h2>
        </div>
        <button type="button" class="directions-manage-btn" @click="openDirectionManager">
          Управлять
        </button>
      </div>
      <div v-if="directionStats.mode === 'table'" class="directions-table">
        <button
          v-for="item in directionStats.items"
          :key="item.id"
          type="button"
          class="direction-table-row"
          @click="selectDirection(item)"
        >
          <span class="direction-table-name">{{ item.name }}</span>
          <span>{{ formatMoney(withVat(item.expenses)) }}</span>
          <span>{{ formatNumber(item.budget_share, 1) }}%</span>
          <span>{{ formatNumber(item.leads) }} лидов</span>
          <strong>{{ formatMoney(withVat(item.cpl)) }}</strong>
        </button>
      </div>
      <div v-else class="directions-grid">
        <button
          v-for="item in directionStats.items"
          :key="item.id"
          type="button"
          class="direction-card"
          :class="{ 'direction-card--unassigned': item.is_unassigned }"
          @click="selectDirection(item)"
        >
          <div class="direction-card__top">
            <strong>{{ item.name }}</strong>
            <span>{{ item.campaign_count }} камп.</span>
          </div>
          <div class="direction-card__money">{{ formatMoney(withVat(item.expenses)) }}</div>
          <div class="direction-share">
            <span :style="{ width: `${Math.min(item.budget_share, 100)}%` }"></span>
          </div>
          <div class="direction-card__bottom">
            <span>{{ formatNumber(item.budget_share, 1) }}% бюджета</span>
            <strong>{{ formatNumber(item.leads) }} лидов · CPL {{ formatMoney(withVat(item.cpl)) }}</strong>
          </div>
        </button>
      </div>
      <div v-if="dashboardSyncInProgress" class="sync-panel-overlay">
        <ArrowPathIcon class="spinning" />
        <strong>Выполняется синхронизация</strong>
        <span>Направления обновятся автоматически.</span>
        <i></i><i></i><i></i>
      </div>
    </section>

    <section class="chart-goals-grid">
      <article class="panel chart-panel" :class="{ 'panel--syncing': dashboardSyncInProgress }">
        <div class="panel-title-row">
          <h2>Эффективность кампаний</h2>
        </div>
        <div class="chart-metric-chips">
          <button
            v-for="chip in chartMetricChips"
            :key="chip.key"
            type="button"
            class="chart-chip"
            :class="{ 'chart-chip--active': chartSelectedMetricKeys.includes(chip.key) }"
            :aria-pressed="chartSelectedMetricKeys.includes(chip.key)"
            @click="toggleChartMetric(chip.key)"
          >
            <span class="chart-chip__dot" :style="{ background: chip.color }"></span>
            {{ chip.label }}
          </button>
        </div>
        <div class="chart-area" @mousemove="handleChartHover" @mouseleave="chartHoverIndex = -1">
          <svg ref="chartSvgRef" :viewBox="`0 0 ${CHART_VIEWBOX_WIDTH} ${CHART_VIEWBOX_HEIGHT}`" preserveAspectRatio="xMidYMid meet" role="img" aria-label="График эффективности кампаний">
            <defs>
              <linearGradient
                v-for="series in chartSeries"
                :key="`grad-${series.key}`"
                :id="`cg-${series.key}`"
                x1="0" :y1="CHART_TOP" x2="0" :y2="CHART_BOTTOM"
                gradientUnits="userSpaceOnUse"
              >
                <stop offset="0%" :stop-color="series.color" stop-opacity="0.22" />
                <stop offset="85%" :stop-color="series.color" stop-opacity="0.03" />
                <stop offset="100%" :stop-color="series.color" stop-opacity="0" />
              </linearGradient>
            </defs>
            <g class="grid-lines">
              <line v-for="y in chartGridLines" :key="y" :x1="CHART_GRID_LEFT" :y1="y" :x2="CHART_GRID_RIGHT" :y2="y" />
            </g>
            <line class="axis-y-line" :x1="CHART_GRID_LEFT" :y1="CHART_TOP" :x2="CHART_GRID_LEFT" :y2="CHART_BOTTOM" />
            <path
              v-for="(series, si) in chartSeries"
              :key="`${series.key}-fill`"
              class="chart-fill"
              :d="series.fillPath"
              :style="{ fill: `url(#cg-${series.key})`, animationDelay: `${0.2 + si * 0.1}s` }"
            />
            <path
              v-for="(series, si) in chartSeries"
              :key="`${series.key}-line`"
              class="chart-line"
              :d="series.path"
              :style="{ stroke: series.color, animationDelay: `${si * 0.12}s` }"
            />
            <line v-if="chartHoverIndex >= 0 && chartHoverX !== null" class="chart-hover-line" :x1="chartHoverX" :y1="CHART_TOP" :x2="chartHoverX" :y2="CHART_BOTTOM" />
            <circle
              v-for="series in chartHoverSeries"
              :key="`${series.key}-dot`"
              class="chart-hover-dot"
              :cx="series.point.x"
              :cy="series.point.y"
              r="5.5"
              :style="{ fill: series.color }"
            />
            <g class="axis-labels">
              <text v-for="tick in chartYTicks" :key="tick.index" text-anchor="end" :x="CHART_Y_LABEL_X" :y="tick.y">{{ chartYLabels[tick.index] }}</text>
              <text v-for="label in chartDateAxisLabels" :key="`${label.text}-${label.index}`" :x="label.x" :y="CHART_DATE_LABEL_Y" :class="{ 'axis-label--active': chartHoverIndex === label.index }">{{ label.text }}</text>
            </g>
          </svg>
          <div v-if="chartHoverIndex >= 0 && chartTooltipData" class="chart-tooltip" :style="chartTooltipStyle">
            <div class="chart-tooltip__date">{{ chartTooltipData.date }}</div>
            <div v-for="item in chartTooltipData.main" :key="item.key" class="chart-tooltip__main">
              <span class="chart-tooltip__dot" :style="{ background: item.color }"></span>
              {{ item.label }} — {{ item.value }}
            </div>
            <div v-if="chartTooltipData.context.length" class="chart-tooltip__divider"></div>
            <div v-for="ctx in chartTooltipData.context" :key="ctx.label" class="chart-tooltip__ctx">
              {{ ctx.label }}: <strong>{{ ctx.value }}</strong>
            </div>
          </div>
        </div>
        <div v-if="dashboardSyncInProgress" class="sync-panel-overlay">
          <ArrowPathIcon class="spinning" />
          <strong>Выполняется синхронизация</strong>
          <span>График обновится сразу после завершения.</span>
          <i></i><i></i><i></i>
        </div>
      </article>

      <article class="panel goals-panel" :class="{ 'panel--syncing': dashboardSyncInProgress }">
        <div class="goals-panel__header">
          <h2>Целевые действия</h2>
        </div>
        <div class="goals-channel-block">
          <div class="goals-channel-header">
            <img :src="yandexMetrikaIcon" alt="Яндекс Метрика" class="goals-channel-icon" />
            <strong class="goals-channel-name">Яндекс Метрика</strong>
            <span class="goals-channel-expense">{{ formatMoney(withVat(summary?.expenses || 0)) }}</span>
          </div>
          <div v-if="goalBars.length" class="goals-bar-list">
            <div
              v-for="(bar, barIdx) in goalBars"
              :key="bar.id"
              class="goals-bar-row"
              :class="bar.alertClass"
              :title="bar.alertTitle"
            >
              <div class="goals-bar-left">
                <span class="goals-bar-name">
                  {{ bar.name }}
                  <span v-if="bar.alert" class="row-anomaly-dot" :class="`row-anomaly-dot--${bar.alert.severity}`"></span>
                </span>
                <div class="goals-bar-meta">
                  <strong class="goals-bar-count">{{ bar.countText }}</strong>
                  <span v-if="bar.trend !== null" class="goals-bar-trend" :class="bar.trendClass">{{ bar.trendText }}</span>
                </div>
              </div>
              <div class="goals-bar-track">
                <div class="goals-bar-fill" :style="{ width: bar.pct + '%', minWidth: bar.count > 0 ? '3px' : '0', background: bar.color, animationDelay: `${0.05 + barIdx * 0.07}s` }"></div>
              </div>
            </div>
          </div>
          <div v-else class="goals-bar-empty">Нет целей за период</div>
          <div class="goals-footer">
            <div v-if="goalBars.length" class="goals-summary-row goals-summary-row--accent">
              <span>Все конверсии · общий CPL</span>
              <strong>{{ goalsSummaryCpl }}</strong>
            </div>
            <div v-if="goalBars.length" class="goals-total-row">
              <span>Итого расход</span>
              <strong>{{ formatMoney(withVat(summary?.expenses || 0)) }}</strong>
            </div>
          </div>
        </div>
        <div v-if="dashboardSyncInProgress" class="sync-panel-overlay">
          <ArrowPathIcon class="spinning" />
          <strong>Выполняется синхронизация</strong>
          <span>Цели и CPL обновятся автоматически.</span>
          <i></i><i></i><i></i>
        </div>
      </article>
    </section>

    <section class="panel campaigns-panel" :class="{ 'panel--syncing': dashboardSyncInProgress }">
      <div class="panel-title-row">
        <h2>Лучшие рекламные компании</h2>
      </div>
      <div class="campaign-table">
        <div class="campaign-row header">
          <span>Название кампании</span>
          <span>Направление</span>
          <span>Расход</span>
          <span>Показы</span>
          <span>Клики</span>
          <span>CPC</span>
          <span>Лиды</span>
          <span>CPL</span>
        </div>
        <div v-for="(campaign, index) in campaignRows" :key="campaign.id || index" class="campaign-row" :class="[campaign.tint, campaign.alertClass]" :title="campaign.alertTitle">
          <span>
            {{ campaign.name }}
            <span v-if="campaign.alert" class="row-anomaly-dot" :class="`row-anomaly-dot--${campaign.alert.severity}`"></span>
          </span>
          <span><em class="campaign-direction-pill">{{ campaign.direction }}</em></span>
          <span>{{ campaign.cost }} <b :class="{ negative: campaign.trendCost.negative }"><component :is="campaign.trendCost.icon" />{{ campaign.trendCost.text }}</b></span>
          <span>{{ campaign.impressions }} <b :class="{ negative: campaign.trendImpressions.negative }"><component :is="campaign.trendImpressions.icon" />{{ campaign.trendImpressions.text }}</b></span>
          <span>{{ campaign.clicks }} <b :class="{ negative: campaign.trendClicks.negative }"><component :is="campaign.trendClicks.icon" />{{ campaign.trendClicks.text }}</b></span>
          <span>{{ campaign.cpc }} <b :class="{ negative: campaign.trendCpc.negative }"><component :is="campaign.trendCpc.icon" />{{ campaign.trendCpc.text }}</b></span>
          <span>{{ campaign.leads }} <b :class="{ negative: campaign.trendLeads.negative }"><component :is="campaign.trendLeads.icon" />{{ campaign.trendLeads.text }}</b></span>
          <span>{{ campaign.cpa }} <b :class="{ negative: campaign.trendCpa.negative }"><component :is="campaign.trendCpa.icon" />{{ campaign.trendCpa.text }}</b></span>
        </div>
      </div>
      <div v-if="dashboardSyncInProgress" class="sync-panel-overlay">
        <ArrowPathIcon class="spinning" />
        <strong>Выполняется синхронизация</strong>
        <span>Кампании обновятся автоматически.</span>
        <i></i><i></i><i></i>
      </div>
    </section>

    <section class="bottom-grid">
      <article class="panel creatives-panel" :class="{ 'panel--syncing': dashboardSyncInProgress }">
        <h2>Топ креативы</h2>
        <div v-if="topAdsLoading" class="creatives-row" aria-label="Загрузка креативов">
          <div v-for="item in 3" :key="item" class="creative-card creative-card--skeleton">
            <div class="creative-image creative-skeleton"></div>
            <div class="creative-skeleton-line creative-skeleton-line--short"></div>
            <div class="creative-skeleton-line"></div>
          </div>
        </div>
        <template v-else-if="creativeTabs.length">
          <div v-if="creativeTabs.length > 1" class="creative-tabs">
            <button
              v-for="tab in creativeTabs"
              :key="tab.key"
              type="button"
              class="creative-tab"
              :class="{ 'creative-tab--active': activeCreativeTab === tab.key }"
              @click="activeCreativeTab = tab.key"
            >{{ tab.label }} · {{ tab.count }}</button>
          </div>
          <div class="creatives-row">
            <div
              v-for="creative in activeCreativeCards"
              :key="creative.id"
              class="creative-card"
              @mouseenter="creative.isVideo ? ($event.currentTarget.querySelector('video')?.play()) : null"
              @mouseleave="creative.isVideo ? ($event.currentTarget.querySelector('video')?.pause()) : null"
            >
              <div class="creative-image-wrap">
                <template v-if="creative.isVideo && creative.thumbnailUrl">
                  <img :src="creative.thumbnailUrl" alt="" class="creative-image creative-image--cover" />
                  <video
                    v-if="creative.imageUrl"
                    :src="creative.imageUrl"
                    class="creative-image creative-image--video"
                    muted loop playsinline preload="none"
                  ></video>
                  <span class="creative-play-icon">▶</span>
                </template>
                <button
                  v-else-if="creative.imageUrl"
                  type="button"
                  class="creative-image creative-image-button"
                  :style="{ backgroundImage: `url(${creative.imageUrl})` }"
                  @click="openCreativeImage(creative)"
                ></button>
                <div v-else class="creative-image creative-image--placeholder"></div>
                <span v-if="creative.formatBadge" class="creative-format-badge">{{ creative.formatBadge }}</span>
              </div>
              <span class="creative-platform" :class="creative.platformClass">
                <img v-if="creative.platformIcon" :src="creative.platformIcon" alt="" />
                {{ creative.badge }}
              </span>
              <em class="creative-title">{{ creative.heading }}</em>
              <em v-if="creative.text" class="creative-text">{{ creative.text }}</em>
            </div>
          </div>
        </template>
        <div v-else class="creative-empty"></div>
        <div v-if="dashboardSyncInProgress" class="sync-panel-overlay">
          <ArrowPathIcon class="spinning" />
          <strong>Выполняется синхронизация</strong>
          <span>Топ креативы подтянутся заново.</span>
          <i></i><i></i><i></i>
        </div>
      </article>

      <article class="panel ai-panel" :class="{ 'panel--syncing': dashboardSyncInProgress }">
        <!-- Header with small button (only when comment exists or loading) -->
        <div v-if="loadingInitialComment || reportComment" class="ai-title">
          <span><SparklesIcon /></span>
          <h2>AI комментарии к отчету</h2>
          <button
            v-if="reportComment && !loadingInitialComment"
            class="ai-download-btn"
            type="button"
            title="Скачать комментарий"
            @click="downloadAiComment"
          >
            <DocumentArrowDownIcon />
          </button>
          <button
            class="ai-generate-btn"
            :disabled="loadingAiComment || dashboardSyncInProgress"
            @click="triggerAiComment"
          >
            <svg v-if="loadingAiComment" class="ai-generate-btn__spinner" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-dasharray="31.4 31.4" />
            </svg>
            <SparklesIcon v-else class="ai-generate-btn__icon" />
            {{ loadingAiComment ? 'Генерирую...' : 'Обновить' }}
          </button>
        </div>

        <!-- Skeleton while loading saved comment -->
        <div v-if="loadingInitialComment" class="ai-skeleton">
          <div class="ai-skeleton-line ai-skeleton-line--wide"></div>
          <div class="ai-skeleton-line"></div>
          <div class="ai-skeleton-line ai-skeleton-line--medium"></div>
          <div class="ai-skeleton-line ai-skeleton-line--wide"></div>
          <div class="ai-skeleton-line ai-skeleton-line--narrow"></div>
        </div>

        <!-- CTA: no comment yet -->
        <div v-else-if="!reportComment" class="ai-cta">
          <span class="ai-cta__icon"><SparklesIcon /></span>
          <h2 class="ai-cta__title">AI комментарии к отчёту</h2>
          <p class="ai-cta__desc">Краткий анализ эффективности кампаний за выбранный период: расходы, конверсии, топ кампаний и рекомендации.</p>
          <button
            class="ai-cta__btn"
            :disabled="loadingAiComment || dashboardSyncInProgress"
            @click="triggerAiComment"
          >
            <svg v-if="loadingAiComment" class="ai-generate-btn__spinner" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-dasharray="31.4 31.4" />
            </svg>
            <SparklesIcon v-else />
            {{ loadingAiComment ? 'Генерирую...' : dashboardSyncInProgress ? 'Дождитесь синхронизации' : 'Сгенерировать анализ' }}
          </button>
        </div>

        <!-- Rendered markdown report -->
        <div v-else class="ai-report-body" v-html="renderMarkdown(reportComment)"></div>
        <p v-if="reportComment && !loadingInitialComment">Сгенерировано AI · {{ dateRangeLabel }}</p>

        <div v-if="dashboardSyncInProgress" class="sync-panel-overlay">
          <ArrowPathIcon class="spinning" />
          <strong>Выполняется синхронизация</strong>
          <span>Комментарии обновятся после пересчёта данных.</span>
          <i></i><i></i><i></i>
        </div>
      </article>

      <div class="side-stat-stack">
        <article class="panel mini-stat-panel" :class="{ 'panel--syncing': dashboardSyncInProgress }">
          <h2>Типы устройств</h2>
          <div v-for="item in deviceStats" :key="item.name" class="progress-line">
            <span><component :is="item.icon" />{{ item.name }}</span>
            <div><i :style="{ width: item.width }"></i></div>
            <b>{{ item.value }}</b>
          </div>
          <div v-if="dashboardSyncInProgress" class="sync-panel-overlay sync-panel-overlay--compact">
            <ArrowPathIcon class="spinning" />
            <strong>Синхронизация</strong>
            <i></i><i></i>
          </div>
        </article>

        <article class="panel mini-stat-panel" :class="{ 'panel--syncing': dashboardSyncInProgress }">
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
          <div v-if="dashboardSyncInProgress" class="sync-panel-overlay sync-panel-overlay--compact">
            <ArrowPathIcon class="spinning" />
            <strong>Синхронизация</strong>
            <i></i><i></i>
          </div>
        </article>
      </div>
    </section>

    <div
      v-if="selectedCreativeImage"
      class="creative-modal"
      role="dialog"
      aria-modal="true"
      @click.self="closeCreativeImage"
    >
      <div class="creative-modal__content">
        <button type="button" class="creative-modal__close" aria-label="Закрыть" @click="closeCreativeImage">
          <XMarkIcon />
        </button>
        <img :src="selectedCreativeImage.imageUrl" :alt="selectedCreativeImage.heading || 'Креатив'" />
      </div>
    </div>

    <Teleport to="body">
      <div
        v-if="directionModalOpen"
        class="direction-modal-overlay"
        role="dialog"
        aria-modal="true"
        @click.self="closeDirectionModal"
      >
        <div class="direction-modal">
          <button type="button" class="direction-modal__close" aria-label="Закрыть" @click="closeDirectionModal">
            <XMarkIcon />
          </button>
          <div class="direction-modal__head">
            <p>{{ directionEditor.id ? 'Редактирование' : 'Новое направление' }}</p>
            <h3>{{ directionEditor.id ? directionEditor.name : `Создать ${directionLabelSingular}` }}</h3>
          </div>
          <label class="direction-field">
            <span>Название</span>
            <input v-model="directionEditor.name" type="text" placeholder="Например: iPhone" />
          </label>
          <label class="direction-field">
            <span>Ключевые слова</span>
            <input
              v-model="directionMaskInput"
              type="text"
              placeholder="Введите слово и нажмите Enter"
              @keydown.enter.prevent="addDirectionMask"
            />
          </label>
          <div class="direction-mask-list">
            <button
              v-for="mask in directionEditor.masks"
              :key="mask"
              type="button"
              class="direction-mask-chip"
              @click="removeDirectionMask(mask)"
            >
              {{ mask }} <XMarkIcon />
            </button>
          </div>
          <div class="direction-preview">
            <div class="direction-preview__summary">
              <strong>{{ directionPreview.matched_count || 0 }}</strong>
              <span>из {{ directionPreview.total_campaigns || 0 }} кампаний попадёт в направление</span>
            </div>
            <p v-if="directionPreview.conflict_count" class="direction-preview__warning">
              {{ directionPreview.conflict_count }} камп. уже попадают в направление выше по списку
            </p>
            <label class="direction-campaign-search">
              <MagnifyingGlassIcon />
              <input v-model="directionCampaignQuery" type="text" placeholder="Найти кампанию" />
            </label>
            <div class="direction-preview__list">
              <button
                v-for="campaign in filteredDirectionPreviewCampaigns"
                :key="campaign.id"
                type="button"
                class="direction-preview__row direction-campaign-option"
                :class="{
                  'direction-campaign-option--selected': campaign.selected,
                  'direction-campaign-option--conflict': campaign.conflict_direction_name
                }"
                @click="toggleDirectionCampaign(campaign)"
              >
                <span class="direction-campaign-option__check">{{ campaign.selected ? '✓' : '+' }}</span>
                <span class="direction-campaign-option__body">
                  <strong>{{ campaign.name }}</strong>
                  <small :class="{ 'direction-preview__conflict': campaign.conflict_direction_name }">
                    <template v-if="campaign.conflict_direction_name">
                      уже в «{{ campaign.conflict_direction_name }}»
                    </template>
                    <template v-else-if="campaign.matched_mask">
                      выбрано по «{{ campaign.matched_mask }}»
                    </template>
                    <template v-else>{{ platformLabel(campaign.platform) }}</template>
                  </small>
                </span>
                <span class="direction-campaign-option__meta">
                  <span class="direction-campaign-platform">{{ platformShortLabel(campaign.platform) }}</span>
                  <span class="direction-campaign-status" :class="`direction-campaign-status--${campaign.status || 'active'}`">
                    {{ campaign.status_label || 'Активна' }}
                  </span>
                </span>
              </button>
              <div v-if="!filteredDirectionPreviewCampaigns.length" class="direction-preview__empty">
                Кампании не найдены
              </div>
            </div>
          </div>
          <div class="direction-modal__actions">
            <button type="button" class="direction-secondary" @click="closeDirectionModal">Отмена</button>
            <button type="button" class="direction-primary" :disabled="directionSaving || !directionEditor.name.trim() || !directionEditor.masks.length" @click="saveDirection">
              {{ directionSaving ? 'Сохраняем...' : 'Сохранить' }}
            </button>
          </div>
        </div>
      </div>

      <div
        v-if="directionManagerOpen"
        class="direction-modal-overlay"
        role="dialog"
        aria-modal="true"
        @click.self="directionManagerOpen = false"
      >
        <div class="direction-modal direction-modal--manager">
          <button type="button" class="direction-modal__close" aria-label="Закрыть" @click="directionManagerOpen = false">
            <XMarkIcon />
          </button>
          <div class="direction-modal__head">
            <p>Управление</p>
            <h3>{{ directionStats.label }}</h3>
          </div>
          <div class="direction-label-setting">
            <div>
              <strong>Название блока</strong>
              <span>Можно адаптировать термин под проект: товары, услуги, бренды или регионы.</span>
            </div>
            <select v-model="selectedDirectionLabelKey" aria-label="Название блока направлений">
              <option v-for="option in directionLabelOptions" :key="option.key" :value="option.key">
                {{ option.label }}
              </option>
            </select>
            <button
              type="button"
              class="direction-secondary"
              :disabled="directionLabelSaving || selectedDirectionLabelKey === directionStats.label_key"
              @click="saveDirectionLabel"
            >
              {{ directionLabelSaving ? 'Сохраняем...' : 'Применить' }}
            </button>
          </div>
          <div class="direction-manager-actions">
            <button type="button" class="direction-primary" @click="openDirectionEditor()">Создать</button>
            <button type="button" class="direction-secondary" :disabled="directionSuggestionsLoading" @click="loadDirectionSuggestions()">
              {{ directionSuggestionsLoading ? 'Анализируем...' : 'Предложить автоматически' }}
            </button>
          </div>
          <div v-if="directionSuggestions.length" class="direction-suggestions">
            <button
              v-for="suggestion in directionSuggestions"
              :key="suggestion.name"
              type="button"
              class="direction-suggestion"
              @click="applyDirectionSuggestion(suggestion)"
            >
              <strong>{{ suggestion.name }}</strong>
              <span>{{ suggestion.matched_count }} камп. · {{ suggestion.masks.join(', ') }}</span>
            </button>
          </div>
          <div class="direction-manager-list">
            <div v-for="direction in directions" :key="direction.id" class="direction-manager-row">
              <div>
                <strong>{{ direction.name }}</strong>
                <span>{{ direction.masks.map((mask) => mask.mask).join(', ') }}</span>
              </div>
              <div class="direction-manager-row__actions">
                <button type="button" @click="moveDirection(direction, -1)">↑</button>
                <button type="button" @click="moveDirection(direction, 1)">↓</button>
                <button type="button" @click="openDirectionEditor(direction)">Править</button>
                <button type="button" class="danger" @click="deleteDirection(direction)">Удалить</button>
              </div>
            </div>
            <div v-if="!directions.length" class="direction-preview__empty">Направления пока не созданы</div>
          </div>
          <div v-if="unassignedDirection" class="direction-unassigned-note">
            <div>
              <strong>{{ unassignedDirection.name }}</strong>
              <span>{{ unassignedDirection.campaign_count }} кампаний не попали ни под одну маску</span>
            </div>
            <button type="button" class="direction-unassigned-action" :disabled="directionSuggestionsLoading" @click="loadDirectionSuggestions(true)">
              Распределить
            </button>
          </div>
        </div>
      </div>

      <!-- Report channel link modal -->
      <div
        v-if="reportLinkChannel"
        class="report-link-overlay"
        role="dialog"
        aria-modal="true"
        @click.self="closeReportLinkModal"
      >
        <div :class="['report-link-card', { 'is-dark': isDarkMode }]">
          <button type="button" class="report-link-close" aria-label="Закрыть" @click="closeReportLinkModal">
            <XMarkIcon />
          </button>

          <div class="report-link-head">
            <div class="report-link-logo">
              <span :class="['report-mask-icon', reportLinkChannel === 'max' ? 'max-icon' : 'telegram-icon']"></span>
            </div>
            <div>
              <p class="report-link-kicker">Канал отчётов</p>
              <h3>{{ reportLinkConnected ? 'Управление' : 'Привязать' }} {{ reportLinkChannelLabel }}</h3>
            </div>
          </div>

          <div v-if="reportLinkConnected" class="report-link-connected">
            <div class="report-link-account">
              <span>Привязан аккаунт</span>
              <strong>{{ reportLinkAccountLabel }}</strong>
            </div>
            <p>
              {{ reportLinkEnabled ? 'Отчёты по расписанию будут приходить в этот канал.' : 'Аккаунт привязан, но доставка по расписанию сейчас выключена.' }}
            </p>
          </div>

          <div v-else class="report-link-steps">
            <div class="report-link-step">
              <span>1</span>
              <p>Откройте бота по персональной ссылке</p>
            </div>
            <div class="report-link-step">
              <span>2</span>
              <p>Нажмите <strong>Start</strong> в {{ reportLinkChannelLabel }}</p>
            </div>
            <div class="report-link-step">
              <span>3</span>
              <p>Вернитесь сюда и проверьте привязку</p>
            </div>
          </div>

          <button
            v-if="!reportLinkConnected"
            type="button"
            class="report-link-primary"
            :disabled="reportLinkOpening"
            @click="openReportBotLink"
          >
            {{ reportLinkOpening ? 'Открываем...' : `Открыть ${reportLinkChannelLabel}` }}
          </button>

          <div v-if="!reportLinkConnected" class="report-link-actions">
            <button type="button" class="report-link-cancel" @click="closeReportLinkModal">Отмена</button>
            <button
              type="button"
              class="report-link-check"
              :disabled="reportLinkChecking"
              @click="confirmReportChannelLinked"
            >
              {{ reportLinkChecking ? 'Проверяем...' : 'Проверить привязку' }}
            </button>
          </div>

          <div v-else class="report-link-actions report-link-actions--manage">
            <button type="button" class="report-link-cancel" @click="closeReportLinkModal">Закрыть</button>
            <button
              type="button"
              class="report-link-check"
              :disabled="reportLinkChecking"
              @click="toggleReportChannelDelivery"
            >
              {{ reportLinkEnabled ? 'Выключить доставку' : 'Включить доставку' }}
            </button>
          </div>

          <button
            v-if="reportLinkConnected"
            type="button"
            class="report-link-unlink"
            :disabled="reportLinkChecking"
            @click="unlinkReportChannel"
          >
            Отвязать аккаунт
          </button>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
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
import yandexMetrikaIcon from '@/assets/icons/yandex-metrika.png'
import vkAdsIcon from '@/assets/icons/vk-ads.png'
import avitoAdsIcon from '@/assets/icons/avito.svg'
import { useTheme } from '@/composables/useTheme'
import { useDashboardStats } from '@/composables/useDashboardStats'
import { useProjects } from '@/composables/useProjects'
import { useTelegramReportLink } from '@/composables/useTelegramReportLink'
import { useToaster } from '@/composables/useToaster'
import api from '@/api/axios'
import DateRangePicker from '@/components/ui/DateRangePicker.vue'
import { projectPeriodOptions, getProjectPeriodLabel, getProjectPeriodRange } from '@/utils/projectPeriods'
import { VueDraggable } from 'vue-draggable-plus'
import DetectorBanner from '@/components/DetectorBanner.vue'
import { useDetector } from '@/composables/useDetector'
import html2canvas from 'html2canvas'

const { isDarkMode } = useTheme()
const router = useRouter()
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
  fetchCampaignPool,
  fetchAllCampaignsForGoalsTab,
  loadingCampaigns,
  deviceStats: deviceStatsRaw,
  placements: placementsRaw
} = useDashboardStats()

const {
  summary: detectorSummary,
  fetchSummary: fetchDetectorSummary,
  dismissAlert: dismissDetectorAlert,
  getAlertForMetric,
  getAlertForEntity,
} = useDetector()

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
const selectedReportTemplate = ref('Шаблон: Яндекс')
const defaultReportSchedule = { day: 'daily', time: '10:00' }
const reportSchedule = ref({ ...defaultReportSchedule })
const reportDeliveryChannels = ref([])
const selectedChartPeriod = ref('Месяц')
const chartSelectedMetricKeys = ref(['expenses'])
const chartHoverIndex = ref(-1)
const chartSvgRef = ref(null)
const dashboardRef = ref(null)
const periodKey = ref(
  filters.period === 'custom' ? 'custom'
    : (filters.period || 'last_7_days')
)
const customPeriodRange = ref(
  filters.period === 'custom' && filters.start_date && filters.end_date
    ? { start: filters.start_date, end: filters.end_date }
    : { start: null, end: null }
)
const periodTriggerRef = ref(null)
const periodPopoverRef = ref(null)
const includeVat = ref(true)
const manualSyncActive = ref(false)
const syncRefreshInProgress = ref(false)
const activeSyncJobIds = ref([])
const syncJobStatuses = ref({})
const lastSyncCompletedAt = ref(null)
const sendingExport = ref(false)
const sendingTg = ref(false)
const sendingEmail = ref(false)
const sendingMax = ref(false)
const reportLinkChannel = ref('')
const reportLinkOpening = ref(false)
const reportLinkChecking = ref(false)
const pendingSendAfterLink = ref(false)
const userReportSettings = ref({
  telegram_chat_id: '',
  max_chat_id: '',
  max_user_id: '',
  max_username: '',
  email_recipients: [],
  report_schedule: '',
  delivery_channels: []
})
const reportComment = ref('')
const loadingAiComment = ref(false)
const loadingInitialComment = ref(false)

const loadSavedComment = async () => {
  if (!filters.client_id) return
  loadingInitialComment.value = true
  try {
    const { data } = await api.get(`ai/comment?client_id=${filters.client_id}`)
    if (data?.text) reportComment.value = data.text
  } catch {
    // не критично — просто не показываем сохранённый
  } finally {
    loadingInitialComment.value = false
  }
}

const renderMarkdown = (text) => {
  if (!text) return ''
  let html = text
    // Tables: header row + separator + body rows
    .replace(/^\|(.+)\|\r?\n\|[-| :]+\|\r?\n((?:\|.+\|\r?\n?)*)/gm, (_, header, body) => {
      const ths = header.split('|').map(h => h.trim()).filter(Boolean)
        .map(h => `<th>${h}</th>`).join('')
      const rows = body.trim().split('\n').map(row => {
        const tds = row.split('|').map(c => c.trim()).filter(Boolean)
          .map(c => `<td>${c}</td>`).join('')
        return `<tr>${tds}</tr>`
      }).join('')
      return `<table class="ai-md-table"><thead><tr>${ths}</tr></thead><tbody>${rows}</tbody></table>`
    })
    // Headers
    .replace(/^### (.+)$/gm, '<h5 class="ai-md-h">$1</h5>')
    .replace(/^## (.+)$/gm, '<h4 class="ai-md-h">$1</h4>')
    .replace(/^# (.+)$/gm, '<h3 class="ai-md-h ai-md-h--1">$1</h3>')
    // Bold
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // Bullet lists
    .replace(/((?:^[*-] .+\n?)+)/gm, match => {
      const items = match.trim().split('\n')
        .map(l => `<li>${l.replace(/^[*-] /, '')}</li>`).join('')
      return `<ul class="ai-md-ul">${items}</ul>`
    })
    // Numbered lists
    .replace(/((?:^\d+\. .+\n?)+)/gm, match => {
      const items = match.trim().split('\n')
        .map(l => `<li>${l.replace(/^\d+\. /, '')}</li>`).join('')
      return `<ol class="ai-md-ol">${items}</ol>`
    })
    // Paragraph breaks
    .replace(/\n\n+/g, '</p><p class="ai-md-p">')
    .replace(/\n/g, '<br>')
  return `<p class="ai-md-p">${html}</p>`
}
const reportGoals = ref([])
const integrations = ref([])
const topAds = ref([])
const topAdsLoading = ref(false)
const selectedCreativeImage = ref(null)
const directions = ref([])
const directionStats = ref({ label: 'Направления', label_key: 'directions', mode: 'cards', total_expenses: 0, items: [] })
const selectedDirectionId = ref(null)
const directionModalOpen = ref(false)
const directionManagerOpen = ref(false)
const directionSaving = ref(false)
const directionMaskInput = ref('')
const directionCampaignQuery = ref('')
const directionPreview = ref({ total_campaigns: 0, matched_count: 0, conflict_count: 0, campaigns: [] })
const directionSuggestions = ref([])
const directionSuggestionsLoading = ref(false)
const directionLabelSaving = ref(false)
const selectedDirectionLabelKey = ref('directions')
const directionEditor = ref({ id: null, name: '', masks: [] })

const directionLabels = {
  directions: { plural: 'Направления', lower: 'направления', singular: 'направление' },
  categories: { plural: 'Категории', lower: 'категории', singular: 'категорию' },
  products: { plural: 'Товары', lower: 'товары', singular: 'товар' },
  services: { plural: 'Услуги', lower: 'услуги', singular: 'услугу' },
  brands: { plural: 'Бренды', lower: 'бренды', singular: 'бренд' },
  branches: { plural: 'Филиалы', lower: 'филиалы', singular: 'филиал' },
  regions: { plural: 'Регионы', lower: 'регионы', singular: 'регион' },
}
const directionLabelOptions = Object.entries(directionLabels).map(([key, meta]) => ({
  key,
  label: meta.plural,
}))

const SYNC_JOB_POLL_MS = 4000
const SYNC_INTEGRATION_POLL_MS = 5000
const SYNC_ACTIVE_STATUSES = new Set(['PENDING', 'QUEUED', 'RUNNING'])
const SYNC_TERMINAL_STATUSES = new Set(['SUCCESS', 'FAILED'])
let syncJobPollTimer = null
let integrationStatusPollTimer = null

const normalizeSyncStatus = (status) => String(status || '').trim().toUpperCase()

const dashboardIntegrationsSyncing = computed(() => (
  integrations.value.some((integration) => SYNC_ACTIVE_STATUSES.has(normalizeSyncStatus(integration.sync_status)))
))

const activeSyncJobCount = computed(() => (
  activeSyncJobIds.value.filter((jobId) => {
    const status = normalizeSyncStatus(syncJobStatuses.value[jobId]?.status)
    return !status || !SYNC_TERMINAL_STATUSES.has(status)
  }).length
))

const dashboardSyncInProgress = computed(() => (
  manualSyncActive.value
  || syncRefreshInProgress.value
  || activeSyncJobCount.value > 0
  || dashboardIntegrationsSyncing.value
))

const lastIntegrationSyncAt = computed(() => {
  const timestamps = integrations.value
    .map((integration) => Date.parse(integration.last_sync_at || ''))
    .filter((timestamp) => Number.isFinite(timestamp))
  return timestamps.length ? Math.max(...timestamps) : null
})

const formatSyncDateTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  if (!Number.isFinite(date.getTime())) return ''
  const tz = 'Europe/Moscow'
  const now = new Date()
  const sameDay = date.toLocaleDateString('ru-RU', { timeZone: tz }) === now.toLocaleDateString('ru-RU', { timeZone: tz })
  const time = date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', timeZone: tz })
  if (sameDay) return `сегодня, ${time} МСК`
  const datePart = date.toLocaleDateString('ru-RU', { day: '2-digit', month: 'short', timeZone: tz }).replace('.', '')
  return `${datePart}, ${time} МСК`
}

const syncProgressLabel = computed(() => {
  if (syncRefreshInProgress.value) return 'Синхронизация завершена. Обновляем статистику, цели, направления и топ креативы.'
  const jobsCount = activeSyncJobCount.value
  if (jobsCount > 0) return `Обрабатывается ${jobsCount} ${jobsCount === 1 ? 'канал' : 'канала'}. Данные обновятся автоматически.`
  if (dashboardIntegrationsSyncing.value) return 'Канал еще синхронизируется на сервере. Пожалуйста, подождите.'
  return 'Пожалуйста, подождите. Данные обновятся автоматически.'
})

const syncStatusLabel = computed(() => {
  if (syncRefreshInProgress.value) return 'Обновляем данные...'
  if (dashboardSyncInProgress.value) return 'Выполняется синхронизация'
  const formatted = formatSyncDateTime(lastIntegrationSyncAt.value)
  return formatted ? `Синхронизация: ${formatted}` : 'Синхронизация не запускалась'
})

const directionLabelMeta = computed(() => directionLabels[directionStats.value.label_key] || directionLabels.directions)
const directionLabelLower = computed(() => directionLabelMeta.value.lower)
const directionLabelSingular = computed(() => directionLabelMeta.value.singular)
const directionsEnabled = computed(() => Boolean(filters.client_id))
const filteredDirectionPreviewCampaigns = computed(() => {
  const query = directionCampaignQuery.value.trim().toLowerCase()
  const campaigns = directionPreview.value.campaigns || []
  if (!query) return campaigns
  return campaigns.filter((campaign) => {
    const values = [
      campaign.name,
      campaign.platform,
      campaign.status_label,
      campaign.conflict_direction_name,
      campaign.matched_mask
    ]
    return values.some((value) => String(value || '').toLowerCase().includes(query))
  })
})
const unassignedDirection = computed(() => directionStats.value.items?.find((item) => item.is_unassigned) || null)
const selectedDirection = computed(() => directionStats.value.items?.find((item) => item.id === selectedDirectionId.value) || null)
const selectedDirectionLabel = computed(() => selectedDirection.value?.name || `Все ${directionLabelLower.value}`)
const directionNameByCampaignId = computed(() => {
  const map = new Map()
  for (const item of directionStats.value.items || []) {
    for (const campaignId of item.campaign_ids || []) {
      map.set(String(campaignId), item.name)
    }
  }
  return map
})

const platformLabel = (platform) => {
  const value = String(platform || '').toLowerCase()
  if (value.includes('vk')) return 'VK Ads'
  if (value.includes('yandex')) return 'Яндекс Директ'
  return 'Канал'
}

const platformShortLabel = (platform) => {
  const value = String(platform || '').toLowerCase()
  if (value.includes('vk')) return 'VK'
  if (value.includes('yandex')) return 'Я'
  return '—'
}

const fetchDirections = async () => {
  if (!filters.client_id) {
    directions.value = []
    return
  }
  try {
    const { data } = await api.get(`clients/${filters.client_id}/directions/`, {
      params: { platform: filters.channel }
    })
    directions.value = Array.isArray(data) ? data : []
  } catch (err) {
    console.error('[Directions] list failed:', err)
    directions.value = []
  }
}

const fetchDirectionStats = async () => {
  if (!filters.client_id || !filters.start_date || !filters.end_date) {
    directionStats.value = { label: 'Направления', label_key: 'directions', mode: 'cards', total_expenses: 0, items: [] }
    return
  }
  try {
    const { data } = await api.get(`clients/${filters.client_id}/directions/stats`, {
      params: {
        start_date: filters.start_date,
        end_date: filters.end_date,
        platform: filters.channel
      }
    })
    directionStats.value = {
      label: data?.label || 'Направления',
      label_key: data?.label_key || 'directions',
      mode: data?.mode || 'cards',
      total_expenses: Number(data?.total_expenses || 0),
      items: Array.isArray(data?.items) ? data.items : []
    }
    selectedDirectionLabelKey.value = directionStats.value.label_key
    if (selectedDirectionId.value) {
      const current = directionStats.value.items.find((item) => item.id === selectedDirectionId.value)
      if (current) filters.campaign_ids = [...current.campaign_ids]
      else {
        selectedDirectionId.value = null
        filters.campaign_ids = []
      }
    }
  } catch (err) {
    console.error('[Directions] stats failed:', err)
    directionStats.value = { label: 'Направления', label_key: 'directions', mode: 'cards', total_expenses: 0, items: [] }
  }
}

const refreshDirections = async () => {
  await Promise.all([fetchDirections(), fetchDirectionStats()])
}

const saveDirectionLabel = async () => {
  if (!filters.client_id || selectedDirectionLabelKey.value === directionStats.value.label_key) return
  directionLabelSaving.value = true
  try {
    const { data } = await api.put(`clients/${filters.client_id}/directions/label`, {
      label: selectedDirectionLabelKey.value,
    })
    directionStats.value = {
      ...directionStats.value,
      label: data?.label || directionLabels[selectedDirectionLabelKey.value]?.plural || 'Направления',
      label_key: data?.label_key || selectedDirectionLabelKey.value,
    }
    toaster.success('Название блока обновлено')
    await refreshDirections()
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Не удалось обновить название блока')
  } finally {
    directionLabelSaving.value = false
  }
}

const selectDirection = (item) => {
  selectedDirectionId.value = item?.id || null
  filters.campaign_ids = item?.campaign_ids?.length ? [...item.campaign_ids] : []
  closeMenu('directions')
  fetchStats()
}

const openDirectionEditor = (direction = null) => {
  directionManagerOpen.value = false
  directionModalOpen.value = true
  directionMaskInput.value = ''
  directionCampaignQuery.value = ''
  directionPreview.value = { total_campaigns: 0, matched_count: 0, conflict_count: 0, campaigns: [] }
  if (direction) {
    directionEditor.value = {
      id: direction.id,
      name: direction.name,
      masks: direction.masks.map((mask) => mask.mask),
    }
  } else {
    directionEditor.value = { id: null, name: '', masks: [] }
  }
  nextTick(fetchDirectionPreview)
}

const closeDirectionModal = () => {
  directionModalOpen.value = false
  directionEditor.value = { id: null, name: '', masks: [] }
  directionMaskInput.value = ''
  directionCampaignQuery.value = ''
}

const addDirectionMask = () => {
  const mask = directionMaskInput.value.trim().toLowerCase()
  if (!mask || directionEditor.value.masks.includes(mask)) return
  directionEditor.value.masks = [...directionEditor.value.masks, mask]
  directionMaskInput.value = ''
}

const removeDirectionMask = (mask) => {
  directionEditor.value.masks = directionEditor.value.masks.filter((item) => item !== mask)
}

const campaignExactMask = (campaign) => String(campaign?.name || '').trim().toLowerCase()

const toggleDirectionCampaign = (campaign) => {
  const exactMask = campaignExactMask(campaign)
  if (!exactMask) return
  const masks = directionEditor.value.masks || []
  if (masks.includes(exactMask)) {
    directionEditor.value.masks = masks.filter((item) => item !== exactMask)
    return
  }
  if (campaign.selected && campaign.matched_mask && masks.includes(campaign.matched_mask)) {
    directionEditor.value.masks = masks.filter((item) => item !== campaign.matched_mask)
    return
  }
  directionEditor.value.masks = [...masks, exactMask]
}

const fetchDirectionPreview = async () => {
  if (!directionModalOpen.value || !filters.client_id) {
    directionPreview.value = { total_campaigns: allCampaigns.value.length, matched_count: 0, conflict_count: 0, campaigns: [] }
    return
  }
  try {
    const { data } = await api.post(`clients/${filters.client_id}/directions/preview`, {
      name: directionEditor.value.name,
      masks: directionEditor.value.masks,
      exclude_direction_id: directionEditor.value.id || undefined,
      platform: filters.channel,
    })
    directionPreview.value = data || { total_campaigns: 0, matched_count: 0, conflict_count: 0, campaigns: [] }
  } catch {
    directionPreview.value = { total_campaigns: 0, matched_count: 0, conflict_count: 0, campaigns: [] }
  }
}

const saveDirection = async () => {
  if (!filters.client_id || !directionEditor.value.name.trim() || !directionEditor.value.masks.length) return
  directionSaving.value = true
  try {
    const payload = {
      name: directionEditor.value.name.trim(),
      masks: directionEditor.value.masks,
    }
    if (directionEditor.value.id) {
      await api.patch(`clients/${filters.client_id}/directions/${directionEditor.value.id}`, payload)
    } else {
      await api.post(`clients/${filters.client_id}/directions/`, payload)
    }
    toaster.success('Направление сохранено')
    closeDirectionModal()
    await refreshDirections()
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Не удалось сохранить направление')
  } finally {
    directionSaving.value = false
  }
}

const openDirectionManager = async () => {
  closeMenu('directions')
  selectedDirectionLabelKey.value = directionStats.value.label_key || 'directions'
  directionManagerOpen.value = true
  await fetchDirections()
}

const deleteDirection = async (direction) => {
  if (!filters.client_id || !direction?.id) return
  if (!window.confirm(`Удалить направление «${direction.name}»? Кампании перейдут в «Без направления».`)) return
  try {
    await api.delete(`clients/${filters.client_id}/directions/${direction.id}`)
    if (selectedDirectionId.value === direction.id) {
      selectedDirectionId.value = null
      filters.campaign_ids = []
    }
    toaster.success('Направление удалено')
    await refreshDirections()
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Не удалось удалить направление')
  }
}

const moveDirection = async (direction, delta) => {
  const list = directions.value.filter((item) => !item.is_unassigned)
  const index = list.findIndex((item) => item.id === direction.id)
  const next = index + delta
  if (index < 0 || next < 0 || next >= list.length) return
  const reordered = [...list]
  const [item] = reordered.splice(index, 1)
  reordered.splice(next, 0, item)
  try {
    await api.post(`clients/${filters.client_id}/directions/reorder`, {
      direction_ids: reordered.map((row) => row.id)
    })
    await refreshDirections()
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Не удалось изменить порядок')
  }
}

const loadDirectionSuggestions = async (unassignedOnly = false) => {
  if (!filters.client_id) return
  directionSuggestionsLoading.value = true
  try {
    const { data } = await api.get(`clients/${filters.client_id}/directions/suggestions`, {
      params: { platform: filters.channel, unassigned_only: Boolean(unassignedOnly) }
    })
    directionSuggestions.value = Array.isArray(data) ? data : []
    if (!directionSuggestions.value.length) {
      toaster.info(unassignedOnly ? 'Для нераспределённых кампаний автопредложения не найдены' : 'Автопредложения не найдены')
    }
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Не удалось получить предложения')
  } finally {
    directionSuggestionsLoading.value = false
  }
}

const applyDirectionSuggestion = (suggestion) => {
  directionManagerOpen.value = false
  directionModalOpen.value = true
  directionCampaignQuery.value = ''
  directionEditor.value = {
    id: null,
    name: suggestion.name,
    masks: [...suggestion.masks],
  }
  directionSuggestions.value = []
  nextTick(fetchDirectionPreview)
}

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
  selectedDirectionId.value = null
  closeMenu('channels')
}

const pendingCampaignIds = ref([])
const campaignArchiveOpen = ref(false)

const openCampaignMenu = () => {
  pendingCampaignIds.value = [...filters.campaign_ids]
  campaignQuery.value = ''
  campaignArchiveOpen.value = false
  openMenu.value = openMenu.value === 'campaigns' ? '' : 'campaigns'
}

const closeCampaignMenu = () => {
  if (openMenu.value === 'campaigns') openMenu.value = ''
}

const togglePendingCampaign = (id) => {
  const idx = pendingCampaignIds.value.indexOf(id)
  if (idx >= 0) pendingCampaignIds.value.splice(idx, 1)
  else pendingCampaignIds.value.push(id)
}

const campaignSelectAll = () => {
  const visible = filteredCampaigns.value.map(c => c.id)
  const set = new Set(pendingCampaignIds.value)
  visible.forEach(id => set.add(id))
  pendingCampaignIds.value = [...set]
}

const campaignDeselectAll = () => {
  const visible = new Set(filteredCampaigns.value.map(c => c.id))
  pendingCampaignIds.value = pendingCampaignIds.value.filter(id => !visible.has(id))
}

const campaignApply = () => {
  selectedDirectionId.value = null
  filters.campaign_ids = [...pendingCampaignIds.value]
  openMenu.value = ''
  handlePeriodChange()
}

const campaignReset = () => {
  selectedDirectionId.value = null
  pendingCampaignIds.value = []
  filters.campaign_ids = []
  openMenu.value = ''
  handlePeriodChange()
}

// Реальный статус кампании с площадки (display_status), фоллбэк по is_active
const campaignPlatformStatus = (c) => {
  const s = String(c.display_status || '').toLowerCase()
  if (['active', 'paused', 'archived', 'unknown'].includes(s)) return s
  return c.is_active ? 'active' : 'archived'
}
const CAMPAIGN_STATUS_TITLES = {
  active: 'Активна',
  paused: 'Приостановлена',
  archived: 'Архив',
  unknown: 'Статус неизвестен',
}
const campaignStatusTitle = (c) => CAMPAIGN_STATUS_TITLES[campaignPlatformStatus(c)] || 'Статус неизвестен'

const STATUS_ORDER = { active: 0, paused: 1, unknown: 2 }
// unknown — площадка не отдала статус (нет Direct Pro / кампания только в отчётах),
// кампания может реально работать, поэтому держим её в основном списке, не в архиве
const campaignGroupActive = computed(() =>
  filteredCampaigns.value
    .filter(c => ['active', 'paused', 'unknown'].includes(campaignPlatformStatus(c)))
    .sort((a, b) =>
      (STATUS_ORDER[campaignPlatformStatus(a)] - STATUS_ORDER[campaignPlatformStatus(b)])
      || a.name.localeCompare(b.name, 'ru')
    )
)
const campaignGroupArchive = computed(() =>
  filteredCampaigns.value.filter(c => campaignPlatformStatus(c) === 'archived')
)
const campaignArchiveVisible = computed(() => campaignQuery.value.trim() ? true : campaignArchiveOpen.value)

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

const periodLabel = computed(() => {
  if (periodKey.value === 'custom' && customPeriodRange.value.start && customPeriodRange.value.end) {
    const fmt = (v) => { const [y,m,d] = String(v).split('-'); return `${d}.${m}.${y}` }
    return `${fmt(customPeriodRange.value.start)} — ${fmt(customPeriodRange.value.end)}`
  }
  return getProjectPeriodLabel(periodKey.value)
})

const periodPopoverStyle = ref({})

const updatePeriodPopoverPosition = () => {
  if (!periodTriggerRef.value || typeof window === 'undefined') { periodPopoverStyle.value = {}; return }
  const rect = periodTriggerRef.value.getBoundingClientRect()
  const width = Math.max(rect.width, 260)
  const viewportPadding = 12
  const left = Math.min(
    Math.max(viewportPadding, rect.left),
    Math.max(viewportPadding, window.innerWidth - width - viewportPadding)
  )
  periodPopoverStyle.value = { top: `${rect.bottom + 4}px`, left: `${left}px`, minWidth: `${width}px` }
}

let _periodScrollCleanup = null
watch(() => openMenu.value, (val) => {
  if (val === 'period') {
    nextTick(updatePeriodPopoverPosition)
    const handler = () => updatePeriodPopoverPosition()
    window.addEventListener('scroll', handler, true)
    window.addEventListener('resize', handler)
    _periodScrollCleanup = () => {
      window.removeEventListener('scroll', handler, true)
      window.removeEventListener('resize', handler)
    }
  } else if (_periodScrollCleanup) {
    _periodScrollCleanup()
    _periodScrollCleanup = null
  }
})
onBeforeUnmount(() => {
  if (_periodScrollCleanup) _periodScrollCleanup()
  clearSyncJobPolling()
  clearIntegrationStatusPolling()
})

const applyPeriodRange = () => {
  const { startDate, endDate } = getProjectPeriodRange(periodKey.value, customPeriodRange.value)
  filters.start_date = startDate
  filters.end_date = endDate
  filters.period = periodKey.value === 'custom' ? 'custom' : periodKey.value
  fetchStats()
}

const selectPeriodPreset = (value) => {
  periodKey.value = value
  openMenu.value = ''
  applyPeriodRange()
}

const selectCustomDashboardPeriod = (range) => {
  if (!range?.start || !range?.end) return
  customPeriodRange.value = { start: range.start, end: range.end }
  periodKey.value = 'custom'
  openMenu.value = ''
  applyPeriodRange()
}

const closePeriodMenu = (event) => {
  if (periodPopoverRef.value?.contains(event.target)) return
  if (event.target?.closest?.('.calendar-popup')) return
  closeMenu('period')
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
  { name: 'Avito Ads', value: 'avito', color: '#00a871', bg: '#ecfdf5', darkBg: 'rgba(16, 185, 129, 0.14)', asset: avitoAdsIcon, icon: EyeIcon }
]

const balancePlatformMeta = {
  yandex_direct: {
    id: 'yandex_direct',
    name: 'Yandex Direct',
    asset: yandexDirectIcon,
    bg: '#fff2e4',
    color: '#71663e'
  },
  vk_ads: {
    id: 'vk_ads',
    name: 'ВК Ads Manager',
    asset: vkAdsIcon,
    bg: '#f0f7ff',
    color: '#254b78'
  },
  avito_ads: {
    id: 'avito_ads',
    name: 'Avito Ads',
    asset: avitoAdsIcon,
    bg: '#ecfdf5',
    color: '#047857'
  }
}

const reportChannels = [
  { name: 'Telegram', value: 'telegram', bg: '#f3f5f7', darkBg: 'rgba(255, 255, 255, 0.08)', iconClass: 'telegram-icon', linkable: true },
  { name: 'E-mail', value: 'email', bg: '#f3f5f7', darkBg: 'rgba(255, 255, 255, 0.08)', iconClass: 'email-icon' },
  { name: 'Max', value: 'max', bg: '#f3f5f7', darkBg: 'rgba(255, 255, 255, 0.08)', iconClass: 'max-icon', linkable: true }
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

const updateScheduleTime = (event) => {
  const digits = String(event.target.value || '').replace(/\D/g, '').slice(0, 4)
  const value = digits.length > 2 ? `${digits.slice(0, 2)}:${digits.slice(2)}` : digits
  reportSchedule.value = { ...reportSchedule.value, time: value }
}

const setScheduleDay = (day) => {
  reportSchedule.value = { ...reportSchedule.value, day }
}

const parseReportSchedule = (raw) => {
  if (!raw) return { ...defaultReportSchedule }
  if (typeof raw === 'object') return normalizeReportSchedule(raw)
  const value = String(raw)
  if (value.includes('_') && !value.trim().startsWith('{')) {
    const [day, hour] = value.split('_')
    const dayMap = { mon: 'monday', tue: 'tuesday', wed: 'wednesday', thu: 'thursday', fri: 'friday', sat: 'saturday', sun: 'sunday' }
    return normalizeReportSchedule({ day: day === 'daily' ? 'daily' : (dayMap[day] || 'daily'), time: `${String(hour || '10').padStart(2, '0')}:00` })
  }
  try {
    return normalizeReportSchedule(JSON.parse(value))
  } catch {
    return { ...defaultReportSchedule }
  }
}

const saveReportSettings = async ({ silent = false } = {}) => {
  const normalized = normalizeReportSchedule(reportSchedule.value)
  reportSchedule.value = normalized
  userReportSettings.value.report_schedule = JSON.stringify(normalized)
  userReportSettings.value.delivery_channels = [...reportDeliveryChannels.value]
  await api.put('/auth/me', {
    report_schedule: JSON.stringify(normalized),
    report_delivery_channels: reportDeliveryChannels.value,
  })
  if (!silent) toaster.success('Настройки отчётов сохранены')
}

const saveReportSchedule = async () => {
  await saveReportSettings()
  closeMenu('report-schedule')
}

const resetReportSchedule = async () => {
  reportSchedule.value = { ...defaultReportSchedule }
  await saveReportSchedule()
}

const getChipBackground = (item) => (isDarkMode.value ? (item.darkBg ?? item.bg) : item.bg)

const reportLinkChannelLabel = computed(() => {
  if (reportLinkChannel.value === 'max') return 'MAX'
  return 'Telegram'
})

const isReportChannelValueConnected = (channel) => {
  if (channel === 'telegram') return Boolean(userReportSettings.value.telegram_chat_id)
  if (channel === 'max') return Boolean(userReportSettings.value.max_chat_id || userReportSettings.value.max_user_id)
  if (channel === 'email') return Boolean(userReportSettings.value.email_recipients?.length)
  return false
}

const isReportChannelConnected = (item) => {
  return isReportChannelValueConnected(item.value)
}

const isReportChannelEnabled = (item) => reportDeliveryChannels.value.includes(item.value)

const reportLinkConnected = computed(() => isReportChannelValueConnected(reportLinkChannel.value))

const reportLinkEnabled = computed(() => reportDeliveryChannels.value.includes(reportLinkChannel.value))

const reportLinkAccountLabel = computed(() => {
  if (reportLinkChannel.value === 'telegram') {
    const chatId = String(userReportSettings.value.telegram_chat_id || '').trim()
    return chatId ? `Chat ID ${chatId}` : 'Telegram не привязан'
  }
  if (reportLinkChannel.value === 'max') {
    const username = String(userReportSettings.value.max_username || '').trim()
    const userId = String(userReportSettings.value.max_user_id || '').trim()
    const chatId = String(userReportSettings.value.max_chat_id || '').trim()
    if (username) return username.startsWith('@') ? username : `@${username}`
    if (userId) return `MAX ID ${userId}`
    if (chatId) return `MAX Chat ${chatId}`
  }
  return `${reportLinkChannelLabel.value} не привязан`
})

const reportChannelTitle = (item) => {
  if (item.disabled) return 'E-mail будет подключён позже'
  if (item.value === 'email') {
    if (!isReportChannelConnected(item)) return 'Укажите email в настройках профиля'
    return isReportChannelEnabled(item) ? 'Отключить E-mail' : 'Включить E-mail'
  }
  if (!isReportChannelConnected(item)) return `Привязать ${item.name}`
  return `Управлять ${item.name}`
}

const handleReportChannelClick = async (item) => {
  if (item.disabled) {
    toaster.info('E-mail подключим позже через Unisender')
    return
  }
  if (item.linkable) {
    reportLinkChannel.value = item.value
    return
  }
  if (item.value === 'email') {
    if (!isReportChannelConnected(item)) {
      toaster.info('Укажите email для получения отчётов в настройках профиля')
      return
    }
    const idx = reportDeliveryChannels.value.indexOf('email')
    if (idx >= 0) {
      reportDeliveryChannels.value.splice(idx, 1)
    } else {
      reportDeliveryChannels.value.push('email')
    }
    await saveReportSettings({ silent: true })
    return
  }
}

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

const formatBalanceMoney = (value, currency = 'RUB') => {
  if (value === null || value === undefined || value === '') return '—'
  const amount = Number(value)
  if (!Number.isFinite(amount)) return '—'
  const formatted = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 2 }).format(amount)
  const code = String(currency || 'RUB').toUpperCase()
  const symbols = { RUB: '₽', RUR: '₽', USD: '$', EUR: '€' }
  return `${formatted} ${symbols[code] || code}`
}

const normalizeIntegrationPlatform = (platform) =>
  String(platform || '').trim().toLowerCase().replace(/-/g, '_')

const channelBalances = computed(() => {
  const balancesByPlatform = new Map()

  integrations.value.forEach((integration) => {
    const id = normalizeIntegrationPlatform(integration.platform)
    const meta = balancePlatformMeta[id]
    if (!meta || integration.is_connected === false) return

    const amount = integration.balance === null || integration.balance === undefined
      ? null
      : Number(integration.balance)
    const current = balancesByPlatform.get(id)

    if (!current) {
      balancesByPlatform.set(id, {
        ...meta,
        balance: Number.isFinite(amount) ? amount : null,
        currency: integration.currency || 'RUB'
      })
      return
    }

    if (Number.isFinite(amount)) {
      current.balance = current.balance === null ? amount : current.balance + amount
      current.currency = current.currency || integration.currency || 'RUB'
    }
  })

  return Array.from(balancesByPlatform.values()).map((item) => ({
    ...item,
    value: formatBalanceMoney(withVat(item.balance), item.currency)
  }))
})

const withVat = (value) => {
  const num = Number(value) || 0
  return includeVat.value ? num * 1.22 : num
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
  if (selectedDirection.value) return selectedDirection.value.name
  const ids = filters.campaign_ids
  if (!ids?.length) return 'Кампании'
  if (ids.length === 1) {
    const found = allCampaigns.value.find(c => c.id === ids[0])
    return found?.name || 'Кампания'
  }
  if (ids.length <= 3) {
    const names = ids.map(id => allCampaigns.value.find(c => c.id === id)?.name).filter(Boolean)
    return names.join(', ')
  }
  return `Выбрано ${ids.length} кампаний`
})

const dateRangeLabel = computed(() => {
  const format = (date) => {
    if (!date) return ''
    const [year, month, day] = String(date).split('-')
    return day && month && year ? `${day}.${month}.${year}` : date
  }
  return `${format(filters.start_date)} - ${format(filters.end_date)}`
})

const dashboardTitle = computed(() => {
  if (selectedDirection.value) {
    return `Отчет: ${selectedDirection.value.name}`
  }
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
  const leadsAvailable = data.leads_available !== false
  const cpaAvailable = data.cpa_available !== false
  const goalsSyncing = Boolean(data.goals_syncing)
  const values = {
    expenses:    hasData ? formatMoney(withVat(data.expenses))                    : '—',
    impressions: hasData ? formatNumber(data.impressions)                         : '—',
    clicks:      hasData ? formatNumber(data.clicks)                              : '—',
    cpc:         hasData ? formatMoney(withVat(data.cpc))                        : '—',
    leads:       hasData && leadsAvailable ? (goalsSyncing ? 'синхр.' : `${formatNumber(data.leads)} шт.`) : '—',
    cpa:         hasData && cpaAvailable && !goalsSyncing ? formatMoney(withVat(data.cpa)) : '—',
  }
  return METRIC_CONFIG.map((metric) => {
    const rawTrend = Number(trends[metric.key] ?? 0)
    const trendRaw = Number.isFinite(rawTrend) ? rawTrend : 0
    const trendAvailable = !(
      (metric.key === 'leads' && (!leadsAvailable || goalsSyncing))
      || (metric.key === 'cpa' && (!cpaAvailable || goalsSyncing))
    )
    return {
      ...metric,
      value: values[metric.key],
      trend: hasData && trendAvailable ? formatTrend(trendRaw) : null,
      trendUp: trendRaw >= 0,
      negative: metric.costMetric ? trendRaw > 0 : trendRaw < 0,
      icon: metricIcons[metric.icon] || ChartBarIcon
    }
  })
})

const chartMetricChips = [
  { key: 'expenses', label: 'Расход', color: '#3464F3', money: true },
  { key: 'impressions', label: 'Показы', color: '#F0926D', money: false },
  { key: 'clicks', label: 'Клики', color: '#38BDF8', money: false },
  { key: 'cpc', label: 'CPC', color: '#D38CFF', money: true },
  { key: 'cpa', label: 'CPL', color: '#EB8525', money: true },
  { key: 'leads', label: 'Конверсии', color: '#8ADA70', money: false },
]

const CHART_VIEWBOX_WIDTH = 880
const CHART_VIEWBOX_HEIGHT = 300
const CHART_LEFT = 44
const CHART_RIGHT = 868
const CHART_TOP = 10
const CHART_BOTTOM = 264
const CHART_BASELINE = CHART_BOTTOM
const CHART_GRID_LEFT = 34
const CHART_GRID_RIGHT = 876
const CHART_Y_LABEL_X = 30
const CHART_DATE_LABEL_Y = 290
const chartGridLines = [10, 73.5, 137, 200.5, 264]
const chartYTicks = chartGridLines.map((y, index) => ({ y: y + 4, index }))

const chartDynamicsKeyMap = { expenses: 'costs', impressions: 'impressions', clicks: 'clicks', cpc: 'cpc', cpa: 'cpa', leads: 'leads' }
const chartChipByKey = computed(() => Object.fromEntries(chartMetricChips.map((chip) => [chip.key, chip])))

const activeChartMetricKeys = computed(() => {
  const allowed = new Set(chartMetricChips.map((chip) => chip.key))
  const selected = chartSelectedMetricKeys.value.filter((key) => allowed.has(key))
  return selected.length ? selected : ['expenses']
})

const toggleChartMetric = (key) => {
  const active = new Set(chartSelectedMetricKeys.value)
  if (active.has(key)) {
    if (active.size === 1) return
    active.delete(key)
  } else {
    active.add(key)
  }
  chartSelectedMetricKeys.value = chartMetricChips
    .map((chip) => chip.key)
    .filter((metricKey) => active.has(metricKey))
}

const getChartSourceValues = (metricKey) => {
  const dynKey = chartDynamicsKeyMap[metricKey] || 'costs'
  const values = dynamics.value?.[dynKey] || []
  const isMoney = chartChipByKey.value[metricKey]?.money
  return values.map((v) => Math.max(0, isMoney ? withVat(v) : Number(v) || 0))
}

const chartSourceValues = computed(() => getChartSourceValues(activeChartMetricKeys.value[0] || 'expenses'))

const buildChartPoints = (values) => {
  const normalizedValues = values.map((value) => Math.max(0, Number(value) || 0))
  const max = Math.max(...normalizedValues, 1)
  const min = 0
  const span = Math.max(max - min, 1)
  return normalizedValues.map((value, index) => ({
    x: values.length === 1 ? CHART_LEFT : CHART_LEFT + ((CHART_RIGHT - CHART_LEFT) / (values.length - 1)) * index,
    y: CHART_BOTTOM - ((value - min) / span) * (CHART_BOTTOM - CHART_TOP),
    value
  }))
}

const chartPoints = computed(() => chartSeries.value[0]?.points || [])

const clampChartY = (value, min = CHART_TOP, max = CHART_BOTTOM) => Math.min(max, Math.max(min, value))

const buildSmoothChartPath = (pts) => {
  if (!pts.length) return ''
  if (pts.length < 2) return `M ${pts[0].x} ${pts[0].y}`

  const slopes = []
  for (let i = 0; i < pts.length - 1; i++) {
    const dx = pts[i + 1].x - pts[i].x
    slopes[i] = dx === 0 ? 0 : (pts[i + 1].y - pts[i].y) / dx
  }

  const tangents = pts.map((_, index) => {
    if (index === 0) return slopes[0] || 0
    if (index === pts.length - 1) return slopes[slopes.length - 1] || 0
    const prev = slopes[index - 1] || 0
    const next = slopes[index] || 0
    return prev * next <= 0 ? 0 : (prev + next) / 2
  })

  for (let i = 0; i < slopes.length; i++) {
    const slope = slopes[i] || 0
    if (slope === 0) {
      tangents[i] = 0
      tangents[i + 1] = 0
      continue
    }
    const a = tangents[i] / slope
    const b = tangents[i + 1] / slope
    const scale = Math.hypot(a, b)
    if (scale > 3) {
      const limit = 3 / scale
      tangents[i] = limit * a * slope
      tangents[i + 1] = limit * b * slope
    }
  }

  let d = `M ${pts[0].x} ${pts[0].y}`
  for (let i = 0; i < pts.length - 1; i++) {
    const p1 = pts[i]
    const p2 = pts[i + 1]
    const dx = p2.x - p1.x
    const segmentTop = Math.min(p1.y, p2.y)
    const segmentBottom = Math.max(p1.y, p2.y)
    const cp1x = p1.x + dx / 3
    const cp1y = clampChartY(p1.y + (tangents[i] * dx) / 3, segmentTop, segmentBottom)
    const cp2x = p2.x - dx / 3
    const cp2y = clampChartY(p2.y - (tangents[i + 1] * dx) / 3, segmentTop, segmentBottom)
    d += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${p2.x} ${p2.y}`
  }
  return d
}

const buildChartFillPath = (points, path) => {
  if (!points.length || !path) return ''
  const first = points[0] || { x: CHART_LEFT }
  const last = points[points.length - 1] || { x: CHART_RIGHT }
  return `${path} L ${last.x} ${CHART_BASELINE} L ${first.x} ${CHART_BASELINE} Z`
}

const chartSeries = computed(() => {
  return activeChartMetricKeys.value.map((metricKey) => {
    const values = getChartSourceValues(metricKey)
    const points = buildChartPoints(values)
    const path = buildSmoothChartPath(points)
    const chip = chartChipByKey.value[metricKey] || {}
    return {
      key: metricKey,
      label: chip.label || metricKey,
      color: chip.color || '#3464F3',
      money: Boolean(chip.money),
      values,
      points,
      path,
      fillPath: buildChartFillPath(points, path),
    }
  })
})

const chartPath = computed(() => `M ${chartPoints.value.map((point) => `${point.x} ${point.y}`).join(' L ')}`)
const chartFillPath = computed(() => chartSeries.value[0]?.fillPath || '')
const smoothChartPath = computed(() => chartSeries.value[0]?.path || chartPath.value)

const handleChartHover = (e) => {
  if (!chartSvgRef.value || !chartPoints.value.length) { chartHoverIndex.value = -1; return }
  const rect = chartSvgRef.value.getBoundingClientRect()
  const scaleX = CHART_VIEWBOX_WIDTH / rect.width
  const svgX = (e.clientX - rect.left) * scaleX
  let closest = 0
  let minDist = Infinity
  chartPoints.value.forEach((pt, i) => {
    const d = Math.abs(pt.x - svgX)
    if (d < minDist) { minDist = d; closest = i }
  })
  chartHoverIndex.value = minDist < 40 ? closest : -1
}

const formatChartMetricValue = (metricKey, value) => {
  const chip = chartChipByKey.value[metricKey] || {}
  return chip.money ? formatMoney(value) : formatNumber(value)
}

const chartHoverX = computed(() => {
  const idx = chartHoverIndex.value
  if (idx < 0) return null
  return chartPoints.value[idx]?.x ?? null
})

const chartHoverSeries = computed(() => {
  const idx = chartHoverIndex.value
  if (idx < 0) return []
  return chartSeries.value
    .map((series) => ({ ...series, point: series.points[idx] }))
    .filter((series) => series.point)
})

const chartTooltipData = computed(() => {
  const idx = chartHoverIndex.value
  if (idx < 0) return null
  const labels = dateLabels.value
  const date = labels[idx] || ''
  const main = chartSeries.value.map((series) => ({
    key: series.key,
    label: series.label,
    color: series.color,
    value: formatChartMetricValue(series.key, series.values[idx] || 0),
  }))
  const selected = new Set(activeChartMetricKeys.value)
  const context = chartMetricChips
    .filter((chip) => !selected.has(chip.key))
    .slice(0, Math.max(0, 4 - main.length))
    .map((chip) => {
      const values = getChartSourceValues(chip.key)
      return {
        label: chip.label,
        value: formatChartMetricValue(chip.key, values[idx] || 0),
      }
    })
  return { date, main, context }
})

const chartTooltipStyle = computed(() => {
  const idx = chartHoverIndex.value
  if (idx < 0 || !chartSvgRef.value) return {}
  const pt = chartPoints.value[idx]
  if (!pt) return {}
  const rect = chartSvgRef.value.getBoundingClientRect()
  const x = (pt.x / CHART_VIEWBOX_WIDTH) * rect.width
  const y = (pt.y / CHART_VIEWBOX_HEIGHT) * rect.height
  const viewportX = rect.left + x
  const viewportY = rect.top + y
  const leftPx = viewportX + 12
  const tooltipWidth = 220
  const lineCount = (chartTooltipData.value?.main?.length || 1) + (chartTooltipData.value?.context?.length || 0)
  const tooltipHeight = 48 + lineCount * 22
  const flip = leftPx + tooltipWidth > window.innerWidth - 8
  const topPx = viewportY + tooltipHeight + 12 > window.innerHeight
    ? Math.max(8, viewportY - tooltipHeight - 14)
    : Math.max(8, viewportY - 40)
  return {
    top: `${topPx}px`,
    [flip ? 'right' : 'left']: flip ? `${Math.max(8, window.innerWidth - viewportX + 12)}px` : `${leftPx}px`,
  }
})

const dateLabels = computed(() => {
  const start = filters.start_date
  const end = filters.end_date
  if (!start || !end) return dynamics.value?.labels || []
  const startMs = new Date(start + 'T00:00:00').getTime()
  const endMs = new Date(end + 'T00:00:00').getTime()
  const DAY = 86400000
  const labels = []
  for (let ms = startMs; ms <= endMs; ms += DAY) {
    const d = new Date(ms)
    labels.push(d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' }).replace(/\./g, '').trim())
  }
  return labels
})

const chartDateAxisLabels = computed(() => {
  const labels = dateLabels.value
  const points = chartPoints.value
  if (!labels.length || !points.length) return []
  const maxLabels = 8
  const step = Math.max(1, Math.ceil(labels.length / maxLabels))
  return labels
    .map((text, index) => ({ text, index, x: points[index]?.x }))
    .filter((item, index) => item.x !== undefined && (index === 0 || index === labels.length - 1 || index % step === 0))
})

const chartYLabels = computed(() => {
  if (activeChartMetricKeys.value.length > 1) return ['', '', '', '', '']
  const values = chartSourceValues.value
  const rawMax = Math.max(...values, 0)
  if (rawMax === 0) return ['0', '0', '0', '0', '0']
  const fmt = (v) => {
    if (v === 0) return '0'
    if (v >= 1_000_000) return `${+(v / 1_000_000).toFixed(1)}M`
    if (v >= 1_000) return `${+(v / 1_000).toFixed(1)}k`
    return String(Math.round(v))
  }
  return [
    fmt(rawMax),
    fmt(rawMax * 0.75),
    fmt(rawMax * 0.5),
    fmt(rawMax * 0.25),
    '0'
  ]
})
const toRgba = (color, alpha = 0.48) => {
  const hex = String(color || '').replace('#', '')
  if (!/^[0-9a-f]{6}$/i.test(hex)) return color
  const value = Number.parseInt(hex, 16)
  const r = (value >> 16) & 255
  const g = (value >> 8) & 255
  const b = value & 255
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

const parseOptionalNumber = (value) => {
  if (value === null || value === undefined || value === '') return NaN
  const num = Number(value)
  return Number.isFinite(num) ? num : NaN
}

const goals = computed(() => {
  const colors = ['#3f63f6', '#f39a72', '#6ee7b7', '#8ada70', '#d38cff', '#38bdf8', '#facc15', '#fb7185', '#a78bfa', '#14b8a6']
  if (!reportGoals.value.length) return []
  const total = reportGoals.value.reduce((sum, item) => {
    const count = parseOptionalNumber(item.count ?? item.conversions ?? item.value)
    return sum + (Number.isFinite(count) ? count : 0)
  }, 0)
  return reportGoals.value.map((goal, index) => {
    const count = parseOptionalNumber(goal.count ?? goal.conversions ?? goal.value)
    const safeCount = Number.isFinite(count) ? count : 0
    const pct = total > 0 ? (safeCount / total) * 100 : (100 / reportGoals.value.length)
    const color = goal.color || colors[index % colors.length]
    return {
      id: goal.id || goal.goal_id || goal.external_id || `${goal.name || goal.goal_name || 'goal'}-${index}`,
      name: goal.name || goal.goal_name || `Цель ${index + 1}`,
      value: `${formatNumber(safeCount)} шт. (${formatNumber(pct, 1)}%)`,
      color,
      innerColor: goal.innerColor || goal.inner_color || toRgba(color, 0.48),
      pct
    }
  })
})

const buildDonutGradient = (items, colorGetter) => {
  if (!items.length) return 'conic-gradient(from -90deg, #e5e7eb 0 100%)'
  let cursor = 0
  const cssPercent = (value) => Number(value || 0).toFixed(3).replace(/\.?0+$/, '') || '0'
  const segments = items.map((item, index) => {
    const start = cursor
    const end = index === items.length - 1 ? 100 : Math.min(100, cursor + item.pct)
    cursor = end
    return `${colorGetter(item)} ${cssPercent(start)}% ${cssPercent(end)}%`
  })
  return `conic-gradient(from -90deg, ${segments.join(', ')})`
}

const donutGradient = computed(() => {
  return buildDonutGradient(goals.value, (item) => item.color)
})

const innerDonutGradient = computed(() => {
  return buildDonutGradient(goals.value, (item) => item.innerColor || item.color)
})

const goalsTotalLabel = computed(() => {
  const total = reportGoals.value.reduce((sum, item) => {
    const count = parseOptionalNumber(item.count ?? item.conversions ?? item.value)
    return sum + (Number.isFinite(count) ? count : 0)
  }, 0)
  const fallback = summary.value?.leads_available === false ? 0 : (summary.value?.leads || 0)
  return `${formatNumber(total || fallback)} шт.`
})

const goalBars = computed(() => {
  const colors = ['#3f63f6', '#f39a72', '#6ee7b7', '#8ada70', '#d38cff', '#38bdf8', '#facc15', '#fb7185', '#a78bfa', '#14b8a6']
  if (!reportGoals.value.length) return []
  const items = reportGoals.value.map((goal, index) => {
    const count = parseOptionalNumber(goal.count ?? goal.conversions ?? goal.value)
    const safeCount = Number.isFinite(count) ? count : 0
    const trendRaw = parseOptionalNumber(goal.trend ?? goal.trend_pct)
    const trend = Number.isFinite(trendRaw) ? trendRaw : null
    const id = goal.id || goal.goal_id || goal.external_id || `goal-${index}`
    const alert = getAlertForEntity('goal', id)
    return {
      id,
      name: goal.name || goal.goal_name || `Цель ${index + 1}`,
      count: safeCount,
      color: goal.color || colors[index % colors.length],
      trend,
      alert,
      alertClass: alert ? `goals-bar-row--anomaly-${alert.severity}` : '',
      alertTitle: alert ? formatDetectorAlertTitle(alert) : null,
    }
  }).sort((a, b) => b.count - a.count)
  const maxCount = Math.max(...items.map(i => i.count), 1)
  return items.map(item => ({
    ...item,
    pct: (item.count / maxCount) * 100,
    countText: `${formatNumber(item.count)} шт.`,
    trendText: item.trend !== null ? `${item.trend > 0 ? '+' : ''}${formatNumber(item.trend, 1)}%` : null,
    trendClass: item.trend !== null ? (item.trend >= 0 ? 'goals-bar-trend--up' : 'goals-bar-trend--down') : '',
  }))
})

const goalsSummaryCpl = computed(() => {
  const totalGoals = reportGoals.value.reduce((sum, item) => {
    const count = parseOptionalNumber(item.count ?? item.conversions ?? item.value)
    return sum + (Number.isFinite(count) ? count : 0)
  }, 0)
  const expenses = summary.value?.expenses || 0
  if (!totalGoals || !expenses) return '—'
  return formatMoney(withVat(expenses / totalGoals))
})

const campaignRows = computed(() => {
  const rows = campaigns.value?.length ? campaigns.value : []
  if (!rows.length) return []
  const tints = ['orange', 'green', 'blue']
  return rows.slice(0, 5).map((campaign, index) => {
    const alert = getAlertForEntity('campaign', campaign.id)
    return {
      id: campaign.id,
      name: campaign.name || `Кампания ${index + 1}`,
      direction: directionNameByCampaignId.value.get(String(campaign.id)) || '—',
      tint: tints[index % tints.length],
      alert,
      alertClass: alert ? `campaign-row--anomaly-${alert.severity}` : '',
      alertTitle: alert ? formatDetectorAlertTitle(alert) : null,
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
    }
  })
})

const AD_TYPE_TAB_MAP = {
  TEXT_AD: 'search', TEXT_IMAGE_AD: 'rsya_image', IMAGE_AD: 'rsya_image',
  TEXT_AD_BUILDER_AD: 'rsya_image', DYNAMIC_TEXT_AD: 'dynamic',
  SMART_AD: 'smart', SHOPPING_AD: 'smart', LISTING_AD: 'smart',
  MOBILE_APP_AD: 'mobile', MOBILE_APP_IMAGE_AD: 'mobile',
  CPC_VIDEO_AD: 'video', CPM_VIDEO_AD: 'video', CPM_BANNER_AD: 'video',
  CPM_BANNER_AD_BUILDER_AD: 'video', SMART_AD_BUILDER_AD: 'smart',
  CAMPAIGN_FALLBACK: 'other',
}
const AD_TAB_LABELS = {
  search: 'Поиск', rsya_image: 'РСЯ + Графика', dynamic: 'Динамические',
  smart: 'Смарт / Товарные', video: 'Видео', mobile: 'Мобильные', other: 'Прочие',
}
const VIDEO_TABS = new Set(['video'])

const activeCreativeTab = ref('')

const allCreativeCards = computed(() => {
  if (!topAds.value.length) return []
  return topAds.value.map((post, index) => {
    const platform = String(post.platform || '').toLowerCase()
    const adType = post.ad_type || ''
    const tabKey = AD_TYPE_TAB_MAP[adType] || 'other'
    const isVideo = VIDEO_TABS.has(tabKey)
    const isVk = platform.includes('vk')
    const isAvito = platform.includes('avito')
    const platformLabel = post.subtitle || (isAvito ? 'Avito Ads' : isVk ? 'VK Ads' : 'Яндекс.Директ')
    let formatBadge = null
    if (isVideo) formatBadge = 'Видео'
    else if (tabKey === 'smart') formatBadge = 'Смарт'
    else if (tabKey === 'dynamic') formatBadge = 'Динамическое'
    return {
      id: post.id || `ad-${index}`,
      tabKey,
      badge: platformLabel,
      heading: post.title || '—',
      text: post.text || '',
      imageUrl: post.image_url || post.preview_url || '',
      thumbnailUrl: post.thumbnail_url || '',
      platformIcon: isAvito ? avitoAdsIcon : isVk ? vkAdsIcon : yandexDirectIcon,
      platformClass: isAvito ? 'creative-platform--avito' : isVk ? 'creative-platform--vk' : 'creative-platform--yandex',
      isVideo,
      formatBadge,
      cost: post.cost || 0,
    }
  })
})

const creativeTabs = computed(() => {
  const groups = {}
  for (const card of allCreativeCards.value) {
    if (!groups[card.tabKey]) groups[card.tabKey] = { key: card.tabKey, count: 0, totalCost: 0 }
    groups[card.tabKey].count++
    groups[card.tabKey].totalCost += card.cost
  }
  const tabs = Object.values(groups)
    .filter(g => g.count > 0)
    .map(g => ({ ...g, label: AD_TAB_LABELS[g.key] || g.key }))
    .sort((a, b) => b.totalCost - a.totalCost)
  if (tabs.length && (!activeCreativeTab.value || !tabs.find(t => t.key === activeCreativeTab.value))) {
    activeCreativeTab.value = tabs[0].key
  }
  return tabs
})

const activeCreativeCards = computed(() =>
  allCreativeCards.value.filter(c => c.tabKey === activeCreativeTab.value).slice(0, 4)
)
const aiComments = computed(() => {
  if (!reportComment.value) return []
  return reportComment.value
    .split(/\n+|(?<=[.!?])\s+/)
    .map((item) => item.trim())
    .filter(Boolean)
    .slice(0, 4)
})

const parseProgressPercent = (item) => {
  const source = item.percent ?? item.percentage ?? item.share ?? item.rate ?? item.width ?? item.value
  if (source === null || source === undefined || source === '' || source === '—') return 0
  const normalized = String(source).replace(',', '.').replace('%', '').trim()
  const num = Number(normalized)
  if (!Number.isFinite(num)) return 0
  const percent = num > 0 && num <= 1 ? num * 100 : num
  return Math.max(0, Math.min(100, percent))
}

const progressValueLabel = (item, percent) => {
  if (item.value !== null && item.value !== undefined && item.value !== '') {
    const raw = String(item.value).trim()
    if (raw.includes('%') || raw === '—') return item.value
    const num = Number(raw.replace(',', '.'))
    if (Number.isFinite(num) && num >= 0 && num <= 100) return `${formatNumber(num, 1)}%`
    return item.value
  }
  return percent > 0 ? `${formatNumber(percent, 1)}%` : '—'
}

const normalizeProgressItems = (items) =>
  items.map((item) => {
    const percent = parseProgressPercent(item)
    return {
      ...item,
      value: progressValueLabel(item, percent),
      width: `${percent}%`
    }
  })

const deviceStats = computed(() =>
  normalizeProgressItems(deviceStatsRaw.value).map((item) => ({
    ...item,
    icon: statIcons[item.icon] || ComputerDesktopIcon
  }))
)
const placements = computed(() => normalizeProgressItems(placementsRaw.value))

const syncLabel = computed(() => integrations.value.length ? 'Синхронизировать данные' : 'Нет подключенных каналов')

const openCreativeImage = (creative) => {
  selectedCreativeImage.value = creative
}

const closeCreativeImage = () => {
  selectedCreativeImage.value = null
}

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
  topAdsLoading.value = true
  try {
    const params = getStatsParams()
    const { data } = await api.get('dashboard/top-ads', { params })
    topAds.value = Array.isArray(data) ? data : (data?.ads || data?.results || data?.items || [])
  } catch {
    topAds.value = []
  } finally {
    topAdsLoading.value = false
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

const clearSyncJobPolling = () => {
  if (syncJobPollTimer) {
    clearInterval(syncJobPollTimer)
    syncJobPollTimer = null
  }
}

const clearIntegrationStatusPolling = () => {
  if (integrationStatusPollTimer) {
    clearInterval(integrationStatusPollTimer)
    integrationStatusPollTimer = null
  }
}

const refreshDashboardAfterSync = async ({ showToast = false, failedCount = 0 } = {}) => {
  if (syncRefreshInProgress.value) return
  syncRefreshInProgress.value = true
  try {
    await Promise.allSettled([
      fetchStats(),
      fetchCampaignPool(),
      fetchReportGoals(),
      fetchTopAds(),
      refreshDirections(),
      fetchIntegrations(),
      filters.channel === 'vk' ? fetchAllCampaignsForGoalsTab() : Promise.resolve(),
      filters.client_id ? fetchDetectorSummary(filters.client_id) : Promise.resolve()
    ])
    // lastIntegrationSyncAt is already updated by fetchIntegrations() above
    if (showToast) {
      if (failedCount > 0) toaster.warning(`Синхронизация завершена с ошибками: ${failedCount}`)
      else toaster.success('Синхронизация завершена. Данные обновлены')
    }
  } finally {
    syncRefreshInProgress.value = false
  }
}

const pollSyncJobs = async () => {
  const jobIds = [...activeSyncJobIds.value]
  if (!jobIds.length) {
    clearSyncJobPolling()
    manualSyncActive.value = false
    return
  }

  const results = await Promise.allSettled(
    jobIds.map((jobId) => api.get(`integrations/sync/jobs/${jobId}`))
  )
  const nextStatuses = { ...syncJobStatuses.value }
  results.forEach((result, index) => {
    const jobId = jobIds[index]
    if (result.status === 'fulfilled') nextStatuses[jobId] = result.value.data || {}
  })
  syncJobStatuses.value = nextStatuses

  const statuses = jobIds.map((jobId) => normalizeSyncStatus(nextStatuses[jobId]?.status))
  const allKnown = statuses.every(Boolean)
  const allFinished = allKnown && statuses.every((status) => SYNC_TERMINAL_STATUSES.has(status))
  if (!allFinished) return

  const failedCount = statuses.filter((status) => status === 'FAILED').length
  clearSyncJobPolling()
  activeSyncJobIds.value = []
  manualSyncActive.value = false
  await refreshDashboardAfterSync({ showToast: true, failedCount })
}

const startSyncJobPolling = () => {
  clearSyncJobPolling()
  syncJobPollTimer = setInterval(() => {
    pollSyncJobs().catch((err) => console.error('[DashboardSync] job polling failed:', err))
  }, SYNC_JOB_POLL_MS)
  pollSyncJobs().catch((err) => console.error('[DashboardSync] initial job polling failed:', err))
}

const pollIntegrationStatuses = async () => {
  const wasSyncing = dashboardIntegrationsSyncing.value
  await fetchIntegrations()
  if (
    wasSyncing
    && !dashboardIntegrationsSyncing.value
    && !manualSyncActive.value
    && activeSyncJobCount.value === 0
  ) {
    clearIntegrationStatusPolling()
    await refreshDashboardAfterSync()
  }
}

const startIntegrationStatusPolling = () => {
  if (integrationStatusPollTimer) return
  integrationStatusPollTimer = setInterval(() => {
    pollIntegrationStatuses().catch((err) => console.error('[DashboardSync] integration polling failed:', err))
  }, SYNC_INTEGRATION_POLL_MS)
}

const handleSyncIntegrations = async () => {
  if (dashboardSyncInProgress.value) return
  manualSyncActive.value = true
  try {
    const params = filters.client_id ? { client_id: filters.client_id } : {}
    const { data: list } = await api.get('integrations/', { params })
    if (!list?.length) {
      toaster.info('Нет подключенных интеграций для синхронизации')
      return
    }
    const results = await Promise.allSettled(
      list.map((integration) => api.post(`integrations/${integration.id}/sync`, { days: 90, force_full: true }))
    )
    const jobIds = results
      .filter((result) => result.status === 'fulfilled')
      .map((result) => result.value.data?.job_id)
      .filter(Boolean)

    const failedToQueue = results.length - jobIds.length
    if (failedToQueue > 0) {
      toaster.warning(`Не удалось запустить синхронизацию для ${failedToQueue} каналов`)
    }
    if (!jobIds.length) {
      toaster.error('Не удалось запустить синхронизацию')
      return
    }
    activeSyncJobIds.value = [...new Set(jobIds)]
    syncJobStatuses.value = Object.fromEntries(activeSyncJobIds.value.map((jobId) => [jobId, { status: 'QUEUED' }]))
    toaster.info(`Синхронизация запущена для ${activeSyncJobIds.value.length} каналов`)
    await fetchIntegrations()
    startSyncJobPolling()
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Не удалось запустить синхронизацию')
  } finally {
    if (!activeSyncJobIds.value.length) {
      manualSyncActive.value = false
    }
  }
}

watch(dashboardIntegrationsSyncing, (isSyncing, wasSyncing) => {
  if (isSyncing) {
    startIntegrationStatusPolling()
    return
  }
  clearIntegrationStatusPolling()
  if (wasSyncing && !manualSyncActive.value && activeSyncJobCount.value === 0) {
    refreshDashboardAfterSync().catch((err) => console.error('[DashboardSync] post-sync refresh failed:', err))
  }
})

const refreshUserReportSettings = async () => {
  try {
    const { data } = await api.get('/auth/me')
    userReportSettings.value.telegram_chat_id = data.report_telegram_chat_id || ''
    userReportSettings.value.max_chat_id = data.report_max_chat_id || ''
    userReportSettings.value.max_user_id = data.report_max_user_id || ''
    userReportSettings.value.max_username = data.report_max_username || ''
    userReportSettings.value.email_recipients = data.report_email_recipients || []
    userReportSettings.value.report_schedule = data.report_schedule || ''
    userReportSettings.value.delivery_channels = data.report_delivery_channels || []
    reportSchedule.value = parseReportSchedule(data.report_schedule)
    reportDeliveryChannels.value = (data.report_delivery_channels || []).filter((channel) => ['telegram', 'max', 'email'].includes(channel))
    if (!reportDeliveryChannels.value.length) {
      const defaults = []
      if (data.report_telegram_chat_id) defaults.push('telegram')
      if (data.report_max_chat_id || data.report_max_user_id) defaults.push('max')
      if (data.report_email_recipients?.length) defaults.push('email')
      reportDeliveryChannels.value = defaults
    }
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

const triggerAiComment = async () => {
  if (loadingAiComment.value) return
  loadingAiComment.value = true
  try {
    await handleGenerateReport()
    if (reportComment.value && filters.client_id) {
      await api.post('ai/comment', { client_id: filters.client_id, text: reportComment.value }).catch(() => {})
    }
  } finally {
    loadingAiComment.value = false
  }
}

const downloadAiComment = () => {
  if (!reportComment.value) return
  const dateStr = filters.start_date || 'report'
  const blob = new Blob([reportComment.value], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `ai-comment-${dateStr}.txt`
  a.click()
  URL.revokeObjectURL(url)
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
    const screenshot = await captureDashboardScreenshot()
    if (screenshot) {
      const byteChars = atob(screenshot)
      const byteArray = new Uint8Array(byteChars.length)
      for (let i = 0; i < byteChars.length; i++) byteArray[i] = byteChars.charCodeAt(i)
      downloadBlob(new Blob([byteArray], { type: 'image/png' }), `report_${filters.start_date}_${filters.end_date}.png`)
      toaster.success('PNG скачан')
    } else {
      const payload = getReportPayload()
      const response = reportComment.value?.trim()
        ? await api.post('reports/png', payload, { responseType: 'blob' })
        : await api.get('reports/png', { params: payload, responseType: 'blob' })
      downloadBlob(response.data, `report_${filters.start_date}_${filters.end_date}.png`)
      toaster.success('PNG скачан')
    }
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

const captureDashboardScreenshot = async () => {
  const el = dashboardRef.value
  if (!el) return null
  try {
    const canvas = await html2canvas(el, {
      scale: 2,
      useCORS: true,
      allowTaint: true,
      backgroundColor: '#f3f4f8',
      logging: false,
    })
    const dataUrl = canvas.toDataURL('image/png')
    return dataUrl.split(',')[1]
  } catch (err) {
    console.error('html2canvas failed:', err)
    return null
  }
}

const executeReportSend = async () => {
  const channels = reportDeliveryChannels.value.filter((channel) => ['telegram', 'max', 'email'].includes(channel))
  if (!channels.length) {
    toaster.error('Выберите канал доставки отчёта')
    return
  }
  if (channels.includes('telegram') && !userReportSettings.value.telegram_chat_id) {
    reportLinkChannel.value = 'telegram'
    pendingSendAfterLink.value = true
    return
  }
  if (channels.includes('max') && !userReportSettings.value.max_chat_id && !userReportSettings.value.max_user_id) {
    reportLinkChannel.value = 'max'
    pendingSendAfterLink.value = true
    return
  }
  if (channels.includes('email') && !userReportSettings.value.email_recipients?.length) {
    toaster.error('Укажите email для получения отчётов в настройках профиля')
    return
  }

  sendingTg.value = channels.includes('telegram')
  sendingMax.value = channels.includes('max')
  sendingEmail.value = channels.includes('email')
  try {
    const text = await getOrGenerateComment()
    const screenshot = await captureDashboardScreenshot()
    await api.post('reports/send', {
      report_type: 'ai',
      channels,
      telegram_chat_id: userReportSettings.value.telegram_chat_id || undefined,
      max_chat_id: userReportSettings.value.max_chat_id || undefined,
      max_user_id: userReportSettings.value.max_user_id || undefined,
      email_recipients: channels.includes('email') ? userReportSettings.value.email_recipients : undefined,
      client_id: filters.client_id || null,
      start_date: filters.start_date,
      end_date: filters.end_date,
      ...(text ? { comment: text } : {}),
      ...(screenshot ? { screenshot_base64: screenshot } : {}),
    })
    toaster.success('Отчёт отправлен')
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Ошибка отправки')
  } finally {
    sendingTg.value = false
    sendingMax.value = false
    sendingEmail.value = false
  }
}

const openReportBotLink = async () => {
  if (!reportLinkChannel.value) return
  reportLinkOpening.value = true
  try {
    let copiedToClipboard = false
    if (reportLinkChannel.value === 'telegram') {
      const result = await openTelegramBotForLinking()
      copiedToClipboard = Boolean(result?.copied_to_clipboard)
    } else {
      const { data } = await api.post('auth/max-reports/link')
      const url = data?.deep_link
      if (!url) throw new Error('Нет ссылки')
      const w = window.open(url, '_blank', 'noopener,noreferrer')
      if (!w) {
        try {
          await navigator.clipboard?.writeText(url)
          copiedToClipboard = true
        } catch {
          throw new Error('Браузер заблокировал открытие новой вкладки')
        }
      }
    }
    toaster.info(copiedToClipboard ? 'Ссылка скопирована. Откройте её в новой вкладке и нажмите Start' : 'Откройте бота и нажмите Start')
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Не удалось открыть бота')
  } finally {
    reportLinkOpening.value = false
  }
}

const saveReportDeliveryChannels = async (nextChannels) => {
  reportDeliveryChannels.value = nextChannels.filter((channel) => ['telegram', 'max'].includes(channel))
  await saveReportSettings({ silent: true })
}

const toggleReportChannelDelivery = async () => {
  if (!reportLinkChannel.value || !reportLinkConnected.value) return
  reportLinkChecking.value = true
  try {
    const channel = reportLinkChannel.value
    const nextChannels = reportDeliveryChannels.value.includes(channel)
      ? reportDeliveryChannels.value.filter((item) => item !== channel)
      : [...reportDeliveryChannels.value, channel]
    await saveReportDeliveryChannels(nextChannels)
    toaster.success(reportDeliveryChannels.value.includes(channel) ? 'Доставка включена' : 'Доставка выключена')
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Не удалось сохранить канал отчётов')
  } finally {
    reportLinkChecking.value = false
  }
}

const unlinkReportChannel = async () => {
  if (!reportLinkChannel.value || !reportLinkConnected.value) return
  reportLinkChecking.value = true
  const channel = reportLinkChannel.value
  try {
    const payload = {
      report_schedule: JSON.stringify(normalizeReportSchedule(reportSchedule.value)),
      report_delivery_channels: reportDeliveryChannels.value.filter((item) => item !== channel),
    }
    if (channel === 'telegram') {
      payload.report_telegram_chat_id = ''
    } else {
      payload.report_max_chat_id = ''
      payload.report_max_user_id = ''
      payload.report_max_username = ''
    }
    await api.put('/auth/me', payload)
    reportDeliveryChannels.value = payload.report_delivery_channels
    if (channel === 'telegram') {
      userReportSettings.value.telegram_chat_id = ''
    } else {
      userReportSettings.value.max_chat_id = ''
      userReportSettings.value.max_user_id = ''
      userReportSettings.value.max_username = ''
    }
    userReportSettings.value.delivery_channels = [...reportDeliveryChannels.value]
    toaster.success(`${reportLinkChannelLabel.value} отвязан`)
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Не удалось отвязать аккаунт')
  } finally {
    reportLinkChecking.value = false
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

const handleSendSelectedReport = () => executeReportSend()

const refreshReportSettingsFromServer = async () => {
  try {
    const { data } = await api.get('/auth/me')
    userReportSettings.value.telegram_chat_id = data?.report_telegram_chat_id || ''
    userReportSettings.value.max_chat_id = data?.report_max_chat_id || ''
    userReportSettings.value.max_user_id = data?.report_max_user_id || ''
    userReportSettings.value.max_username = data?.report_max_username || ''
  } catch { /* ignore */ }
}

function closeReportLinkModal() {
  reportLinkChannel.value = ''
  pendingSendAfterLink.value = false
}

async function confirmReportChannelLinked() {
  reportLinkChecking.value = true
  try {
    const channel = reportLinkChannel.value
    await refreshReportSettingsFromServer()
    const linked = channel === 'telegram'
      ? Boolean(userReportSettings.value.telegram_chat_id)
      : Boolean(userReportSettings.value.max_chat_id || userReportSettings.value.max_user_id)
    if (!linked) {
      toaster.error(`Сначала нажмите Start в ${reportLinkChannelLabel.value}`)
      return
    }
    if (!reportDeliveryChannels.value.includes(channel)) {
      reportDeliveryChannels.value = [...reportDeliveryChannels.value, channel]
      await saveReportSettings({ silent: true })
    }
    const sendNow = pendingSendAfterLink.value
    pendingSendAfterLink.value = false
    if (sendNow) {
      reportLinkChannel.value = ''
      await executeReportSend()
      return
    }
    toaster.success(`${reportLinkChannelLabel.value} привязан`)
  } finally {
    reportLinkChecking.value = false
  }
}

watch(currentProjectId, (newId) => {
  if (filters.client_id !== newId) filters.client_id = newId
}, { immediate: true })

watch(() => filters.client_id, (newId) => {
  if (currentProjectId.value !== newId) setCurrentProject(newId)
  selectedDirectionId.value = null
  fetchIntegrations()
  refreshDirections()
}, { immediate: true })

watch(() => [filters.start_date, filters.end_date, filters.client_id, filters.channel, filters.campaign_ids, filters.vk_goal_action_ids], () => {
  fetchReportGoals()
  fetchTopAds()
}, { deep: true })

watch(() => [filters.start_date, filters.end_date, filters.client_id, filters.channel], () => {
  if (filters.client_id) refreshDirections()
}, { deep: true })

watch(() => [directionEditor.value.name, directionEditor.value.masks, directionModalOpen.value], () => {
  fetchDirectionPreview()
}, { deep: true })

watch(() => filters.period, (period) => {
  const labelMap = {
    7: 'Неделя',
    14: 'Неделя',
    30: 'Месяц',
    90: 'Квартал',
    365: 'Год',
    last_7_days: 'Неделя',
    last_30_days: 'Месяц',
    last_90_days: 'Квартал',
    last_365_days: 'Год',
    today: 'Неделя',
    yesterday: 'Неделя',
    this_week: 'Неделя',
    last_week: 'Неделя',
    this_month: 'Месяц',
    last_month: 'Месяц',
  }
  selectedChartPeriod.value = labelMap[period] || selectedChartPeriod.value
}, { immediate: true })

watch(() => filters.channel, (channel) => {
  if (channel === 'vk') fetchAllCampaignsForGoalsTab()
})

watch(() => filters.client_id, (clientId) => {
  if (clientId) fetchDetectorSummary(clientId)
}, { immediate: true })

const detectorBannerHypothesis = computed(() => {
  if (!detectorSummary.value?.alerts?.length) return ''
  return detectorSummary.value.alerts[0]?.hypothesis_text || ''
})

const detectorBannerAlert = computed(() => detectorSummary.value?.alerts?.[0] || null)

const formatDetectorAlertTitle = (alert) => {
  if (!alert) return ''
  const deviation = alert.deviation_pct > 0 ? `+${alert.deviation_pct}%` : `${alert.deviation_pct}%`
  const days = alert.consecutive_days || 1
  const hypothesis = alert.hypothesis_text ? `\n${alert.hypothesis_text}` : ''
  const baseline = alert.baseline_value != null && alert.actual_value != null
    ? `\nБаза: ${Number(alert.baseline_value).toLocaleString('ru')}, факт: ${Number(alert.actual_value).toLocaleString('ru')}`
    : ''
  return `Отклонение ${deviation}, ${days} дн. подряд${baseline}${hypothesis}\nСчитает детектор по истории · не AI`
}

const metricAnomalyClass = (key) => {
  const alert = getAlertForMetric(key)
  if (!alert) return ''
  return `metric-card--anomaly-${alert.severity}`
}

const getMetricAnomaly = (key) => getAlertForMetric(key)

const getMetricAnomalyTooltip = (key) => {
  const alert = getAlertForMetric(key)
  if (!alert) return ''
  return `${formatDetectorAlertTitle(alert)}\nКликните чтобы скрыть`
}

const handleDismissAnomaly = async (key) => {
  const alert = getAlertForMetric(key)
  if (!alert) return
  const ok = await dismissDetectorAlert(alert.id)
  if (ok) toaster.success('Алерт скрыт')
}

const handleDismissBanner = async () => {
  if (!detectorBannerAlert.value) return
  const ok = await dismissDetectorAlert(detectorBannerAlert.value.id)
  if (ok) toaster.success('Алерт скрыт')
}

const openAssistantForDetectorAlert = () => {
  const alert = detectorBannerAlert.value
  if (!alert || !filters.client_id) return
  const metric = String(alert.metric || 'метрику').toUpperCase()
  const deviation = Number(alert.deviation_pct || 0)
  const hypothesis = alert.hypothesis_text ? ` Гипотеза: ${alert.hypothesis_text}` : ''
  const question = `Разбери отклонение ${metric} ${deviation > 0 ? '+' : ''}${deviation.toFixed(0)}% за выбранный период.${hypothesis}`
  router.push({
    path: '/ai-analysis',
    query: {
      project: filters.client_id,
      start_date: filters.start_date,
      end_date: filters.end_date,
      question,
    },
  })
}

watch(() => filters.client_id, () => {
  reportComment.value = ''
  loadSavedComment()
})

onMounted(() => {
  refreshUserReportSettings()
  fetchIntegrations()
  fetchReportGoals()
  fetchTopAds()
  loadSavedComment()
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
  border: 1px solid #eef0f2;
  border-radius: 1.4rem;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03), 0 4px 16px rgba(15, 23, 42, 0.02);
}

.top-grid {
  display: grid;
  grid-template-columns: 49.4rem 1fr;
  gap: 2rem;
  align-items: stretch;
}

.panel-channels,
.panel-reports {
  min-height: auto;
  padding: 2.5rem;
}

.panel h2,
.panel-channels h2,
.panel-reports h2 {
  margin: 0;
  font-size: 1.7rem;
  font-weight: 600;
  line-height: 1.2;
  color: #1e293b;
  letter-spacing: -0.01em;
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

.channel-balance-block {
  margin-top: 1.2rem;
}

.channel-balance-title {
  margin: 0 0 0.7rem;
  color: #696969;
  font-size: 0.9028rem;
  font-weight: 400;
  line-height: 1.25;
}

.channel-balance-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.8rem;
}

.analytics-balance-tile {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 0;
  min-height: 2.65rem;
  gap: 0.55rem;
  padding: 0.55rem 0.7rem;
  border-radius: 0.8333rem;
  background: var(--balance-bg);
  color: var(--balance-color);
}

.analytics-balance-icon {
  width: 1.25rem;
  height: 1.25rem;
  flex: 0 0 auto;
  object-fit: contain;
}

.analytics-balance-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.9028rem;
  font-weight: 500;
}

.analytics-balance-value {
  display: inline-flex;
  align-items: center;
  min-height: 1.55rem;
  max-width: 100%;
  flex: 0 0 auto;
  padding: 0 0.55rem;
  border-radius: 6.9444rem;
  background: #fff;
  font-size: 0.9028rem;
  font-weight: 500;
  white-space: nowrap;
}

.channel-balance-empty {
  display: flex;
  align-items: center;
  min-height: 2.65rem;
  padding: 0 0.85rem;
  border-radius: 0.8333rem;
  background: #f7f9ff;
  color: #8a94a6;
  font-size: 0.9028rem;
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

.dashboard-period-select .cs-head {
  min-width: 18rem;
}

.period-popover.period-list {
  position: fixed;
  z-index: 5000;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 0.3rem 0;
  background-color: #fff;
  min-width: 18rem;
  border-radius: 0.8rem;
  box-shadow: 0 0.8rem 2.4rem rgba(15, 23, 42, 0.12), 0 0 0 1px rgba(68, 68, 68, 0.06);
}

.period-list__divider {
  height: 1px;
  margin: 0.2rem 0;
  background: rgba(0, 0, 0, 0.06);
}

.period-option {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 1.2rem;
  align-items: center;
  gap: 1rem;
  width: 100%;
  min-height: 2.8rem;
  padding: 0.5rem 1.2rem;
  border: 0;
  background: transparent;
  color: rgba(0, 0, 0, 0.78);
  cursor: pointer;
  font-size: 1.1rem;
  line-height: 1.2;
  text-align: left;
  white-space: nowrap;
  transition: background-color 0.15s;
}

.period-option:hover,
.period-option.selected {
  background-color: #f5f7f9;
}

.period-option__check {
  width: 1.2rem;
  height: 0.9rem;
  color: #171717;
}

.project-period-custom-picker :deep(.drp-trigger) {
  height: auto;
  min-height: 2.8rem;
  justify-content: flex-start;
  border: 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 0;
  padding: 0.5rem 1.2rem;
  background: transparent;
  box-shadow: none;
  color: #171717;
  font-size: 1.1rem;
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

.sync-btn-ghost {
  background: transparent;
  color: rgba(105, 105, 105, 0.62);
  border-radius: 1.2rem;
  padding: 0 1.4rem;
  border: none;
  font-weight: 500;
}

.sync-btn-ghost:hover:not(:disabled) {
  background: rgba(37, 99, 235, 0.04);
  color: rgba(105, 105, 105, 0.82);
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

.report-icon-btn.unlinked .report-icon-circle,
.report-icon-btn.disabled .report-icon-circle {
  background: #eef1f5;
  color: #b3bccb;
}

.report-icon-btn.disabled {
  cursor: not-allowed;
  opacity: 0.62;
}

.report-icon-btn.disabled:hover {
  transform: none;
}

.report-icon-btn.active .report-icon-circle {
  background: linear-gradient(135deg, #2f6df6 0%, #14b8d5 100%);
  color: #fff;
  box-shadow: none;
}

.report-icon-btn.connected:not(.active) .report-icon-circle {
  background: #e8f0ff;
  color: #2563eb;
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

/* Telegram: gradient bg + white icon when connected or active.
   Uses data-channel attr (not :has) because Vue scoped CSS breaks :has() internals. */
.report-icon-btn[data-channel="telegram"].connected .report-icon-circle,
.report-icon-btn[data-channel="telegram"].active .report-icon-circle {
  background: linear-gradient(135deg, #2f6df6 0%, #14b8d5 100%);
  box-shadow: none;
}
.report-icon-btn[data-channel="telegram"].connected .telegram-icon,
.report-icon-btn[data-channel="telegram"].active .telegram-icon {
  background: #fff;
}

.report-link-overlay {
  position: fixed;
  inset: 0;
  z-index: 99999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.25rem;
  background: rgba(15, 23, 42, 0.56);
  backdrop-filter: blur(0.18rem);
}

.report-link-card {
  position: relative;
  width: min(100%, 31.25rem);
  padding: 1.6rem;
  border: 1px solid rgba(222, 226, 230, 0.95);
  border-radius: 1.35rem;
  background: #fff;
  box-shadow: 0 1.6rem 4rem rgba(15, 23, 42, 0.28);
}

.report-link-card.is-dark {
  border-color: rgba(255, 255, 255, 0.1);
  background: #252838;
  box-shadow: 0 1.6rem 4rem rgba(0, 0, 0, 0.45);
}

.report-link-close {
  position: absolute;
  top: 1rem;
  right: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.15rem;
  height: 2.15rem;
  border: 0;
  border-radius: 999px;
  background: #f3f5f7;
  color: #697586;
  cursor: pointer;
}

.report-link-card.is-dark .report-link-close {
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.72);
}

.report-link-close svg {
  width: 1.1rem;
  height: 1.1rem;
}

.report-link-head {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding-right: 2.4rem;
  margin-bottom: 1.25rem;
}

.report-link-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 3.9rem;
  height: 3.9rem;
  border-radius: 1.2rem;
  background: linear-gradient(135deg, #2f6df6 0%, #14b8d5 100%);
  color: #fff;
  box-shadow: 0 0.75rem 1.8rem rgba(47, 109, 246, 0.28);
}

.report-link-logo .report-mask-icon {
  width: 1.85rem;
  height: 1.85rem;
  transform: none;
}

.report-link-kicker {
  margin: 0 0 0.2rem;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0;
  text-transform: uppercase;
  color: #2f6df6;
}

.report-link-card h3 {
  margin: 0;
  font-size: 1.28rem;
  font-weight: 750;
  color: #111827;
}

.report-link-card.is-dark h3 {
  color: #f8fafc;
}

.report-link-steps {
  display: grid;
  gap: 0.7rem;
  margin-bottom: 1.15rem;
}

.report-link-step {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.8rem 0.9rem;
  border: 1px solid #e5e7eb;
  border-radius: 0.9rem;
  background: #f8fafc;
}

.report-link-card.is-dark .report-link-step {
  border-color: rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.05);
}

.report-link-step span {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.55rem;
  height: 1.55rem;
  flex: 0 0 auto;
  border-radius: 999px;
  background: #e8f0ff;
  color: #2563eb;
  font-size: 0.78rem;
  font-weight: 800;
}

.report-link-step p {
  margin: 0;
  color: #4b5563;
  font-size: 0.92rem;
  line-height: 1.35;
}

.report-link-card.is-dark .report-link-step p {
  color: rgba(255, 255, 255, 0.72);
}

.report-link-connected {
  display: grid;
  gap: 0.85rem;
  margin-bottom: 1.15rem;
}

.report-link-account {
  display: grid;
  gap: 0.25rem;
  padding: 0.95rem 1rem;
  border: 1px solid #d7e5ff;
  border-radius: 0.95rem;
  background: linear-gradient(135deg, rgba(47, 109, 246, 0.08) 0%, rgba(20, 184, 213, 0.08) 100%);
}

.report-link-card.is-dark .report-link-account {
  border-color: rgba(47, 109, 246, 0.32);
  background: linear-gradient(135deg, rgba(47, 109, 246, 0.14) 0%, rgba(20, 184, 213, 0.12) 100%);
}

.report-link-account span {
  color: #697586;
  font-size: 0.78rem;
  font-weight: 700;
}

.report-link-account strong {
  color: #111827;
  font-size: 1rem;
  font-weight: 800;
  overflow-wrap: anywhere;
}

.report-link-card.is-dark .report-link-account span {
  color: rgba(255, 255, 255, 0.55);
}

.report-link-card.is-dark .report-link-account strong {
  color: #f8fafc;
}

.report-link-connected p {
  margin: 0;
  color: #4b5563;
  font-size: 0.92rem;
  line-height: 1.45;
}

.report-link-card.is-dark .report-link-connected p {
  color: rgba(255, 255, 255, 0.72);
}

.report-link-primary,
.report-link-check,
.report-link-cancel,
.report-link-unlink {
  border: 0;
  border-radius: 0.85rem;
  font-size: 0.94rem;
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.18s ease, box-shadow 0.18s ease, opacity 0.18s ease, background 0.18s ease;
}

.report-link-primary {
  width: 100%;
  min-height: 3rem;
  margin-bottom: 0.85rem;
  background: linear-gradient(135deg, #2f6df6 0%, #14b8d5 100%);
  color: #fff;
  box-shadow: 0 0.85rem 1.8rem rgba(47, 109, 246, 0.28);
}

.report-link-primary:hover,
.report-link-check:hover,
.report-link-cancel:hover {
  transform: translateY(-1px);
}

.report-link-primary:disabled,
.report-link-check:disabled {
  opacity: 0.58;
  cursor: wait;
  transform: none;
}

.report-link-actions {
  display: grid;
  grid-template-columns: 0.8fr 1.2fr;
  gap: 0.75rem;
}

.report-link-actions--manage {
  margin-bottom: 0.75rem;
}

.report-link-cancel {
  min-height: 2.75rem;
  background: #f3f5f7;
  color: #374151;
}

.report-link-card.is-dark .report-link-cancel {
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.82);
}

.report-link-check {
  min-height: 2.75rem;
  border: 1px solid #cfe0ff;
  background: #fff;
  color: #2563eb;
}

.report-link-card.is-dark .report-link-check {
  border-color: rgba(47, 109, 246, 0.38);
  background: rgba(47, 109, 246, 0.1);
  color: #8bb4ff;
}

.report-link-unlink {
  width: 100%;
  min-height: 2.75rem;
  border: 1px solid #fecaca;
  background: #fff7f7;
  color: #dc2626;
}

.report-link-card.is-dark .report-link-unlink {
  border-color: rgba(248, 113, 113, 0.26);
  background: rgba(248, 113, 113, 0.08);
  color: #fca5a5;
}

.report-link-unlink:disabled {
  opacity: 0.58;
  cursor: wait;
}

@media (max-width: 420px) {
  .report-link-card {
    padding: 1.25rem;
    border-radius: 1.1rem;
  }

  .report-link-head {
    align-items: flex-start;
  }

  .report-link-logo {
    width: 3.25rem;
    height: 3.25rem;
    border-radius: 1rem;
  }

  .report-link-actions {
    grid-template-columns: 1fr;
  }
}

.sync-btn svg.spinning {
  animation: dashboard-spin 1s linear infinite;
}

@keyframes dashboard-spin {
  to {
    transform: rotate(360deg);
  }
}

.sync-status-label.active {
  color: #2563eb;
  font-weight: 600;
}

.dashboard-sync-banner {
  display: flex;
  align-items: center;
  gap: 1.2rem;
  margin: 1.4rem 0 1.8rem;
  padding: 1.25rem 1.45rem;
  border: 1px solid rgba(37, 99, 235, 0.18);
  border-radius: 1.2rem;
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.08) 0%, rgba(20, 184, 213, 0.08) 100%);
  color: #1e3a8a;
}

.dashboard-sync-banner__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 3rem;
  height: 3rem;
  border-radius: 999px;
  background: #2563eb;
  color: #fff;
  flex: 0 0 auto;
}

.dashboard-sync-banner__icon svg {
  width: 1.45rem;
  height: 1.45rem;
}

.dashboard-sync-banner strong {
  display: block;
  color: #1d4ed8;
  font-size: 1.15rem;
  line-height: 1.2;
  font-weight: 800;
}

.dashboard-sync-banner p {
  margin: 0.25rem 0 0;
  color: rgba(30, 64, 175, 0.72);
  font-size: 0.95rem;
  line-height: 1.35;
  font-weight: 500;
}

.kpi-grid--sync {
  pointer-events: none;
}

.metric-card--skeleton {
  display: grid;
  grid-template-columns: 3.1rem minmax(0, 1fr) 5.4rem;
  align-items: center;
  gap: 1rem;
  overflow: hidden;
  position: relative;
}

.metric-card--skeleton::after,
.sync-panel-overlay i::after {
  content: '';
  position: absolute;
  inset: 0;
  transform: translateX(-100%);
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.64), transparent);
  animation: sync-shimmer 1.35s infinite;
}

.metric-skeleton-icon,
.metric-skeleton-lines span,
.metric-skeleton-lines strong,
.metric-card--skeleton em {
  display: block;
  position: relative;
  overflow: hidden;
  border-radius: 999px;
  background: #eef2f7;
}

.metric-skeleton-icon {
  width: 3.1rem;
  height: 3.1rem;
}

.metric-skeleton-lines {
  display: grid;
  gap: 0.75rem;
}

.metric-skeleton-lines span {
  width: 58%;
  height: 0.8rem;
}

.metric-skeleton-lines strong {
  width: 82%;
  height: 1.55rem;
}

.metric-card--skeleton em {
  width: 5.2rem;
  height: 1.6rem;
}

.panel--syncing {
  position: relative;
  overflow: hidden;
}

.panel--syncing > :not(.sync-panel-overlay) {
  opacity: 0.36;
}

.sync-panel-overlay {
  position: absolute;
  inset: 0.9rem;
  z-index: 8;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  gap: 0.55rem;
  padding: 1.35rem;
  border: 1px solid rgba(37, 99, 235, 0.13);
  border-radius: 1rem;
  background: rgba(255, 255, 255, 0.86);
  backdrop-filter: blur(6px);
  color: #1f2937;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.55);
}

.sync-panel-overlay svg {
  width: 1.65rem;
  height: 1.65rem;
  color: #2563eb;
}

.sync-panel-overlay strong {
  color: #111827;
  font-size: 1.1rem;
  line-height: 1.2;
  font-weight: 800;
}

.sync-panel-overlay span {
  max-width: 26rem;
  color: #6b7280;
  font-size: 0.95rem;
  line-height: 1.35;
  font-weight: 500;
}

.sync-panel-overlay i {
  position: relative;
  overflow: hidden;
  display: block;
  width: min(22rem, 82%);
  height: 0.75rem;
  margin-top: 0.45rem;
  border-radius: 999px;
  background: #eef2f7;
}

.sync-panel-overlay i:nth-of-type(2) {
  width: min(17rem, 64%);
}

.sync-panel-overlay i:nth-of-type(3) {
  width: min(12rem, 46%);
}

.sync-panel-overlay--compact {
  align-items: center;
  text-align: center;
}

.sync-panel-overlay--compact span {
  display: none;
}

.sync-panel-overlay--compact i {
  width: 70%;
}

@keyframes sync-shimmer {
  100% {
    transform: translateX(100%);
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

.directions-menu {
  min-width: 25rem;
}

.direction-option {
  justify-content: space-between;
}

.direction-option small {
  color: #94a3b8;
  font-size: 1.1rem;
}

.directions-menu__divider {
  height: 1px;
  margin: 0.6rem 0;
  background: #eef2f7;
}

.direction-action {
  color: #2563eb !important;
  font-weight: 600;
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
  margin-top: 2.4rem;
}

.directions-panel {
  margin-top: 2rem;
  padding: 2.2rem;
}

.directions-head {
  display: flex;
  justify-content: space-between;
  gap: 1.2rem;
  align-items: center;
  margin-bottom: 1.6rem;
}

.directions-kicker {
  margin: 0 0 0.35rem;
  color: #94a3b8;
  font-size: 1.05rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.directions-head h2 {
  margin: 0;
  font-size: 1.8rem;
  color: #172033;
}

.directions-manage-btn,
.direction-secondary,
.direction-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 3.1944rem;
  border-radius: 0.8333rem;
  padding: 0 1.3889rem;
  font-size: 0.9722rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s, transform 0.2s;
}

.directions-manage-btn,
.direction-secondary {
  border: 1px solid rgba(0,0,0,0.1);
  background: #fff;
  color: rgba(105,105,105,0.75);
}
.directions-manage-btn:hover, .direction-secondary:hover { background: #f5f7f9; }
:global(.dark) .directions-manage-btn, :global(.dark) .direction-secondary { background: rgba(255,255,255,0.05); border-color: rgba(255,255,255,0.15); color: rgba(255,255,255,0.7); }

.direction-primary {
  border: 0;
  background: linear-gradient(270deg, #06b5d4 0.35%, #1f9de4 32.08%, #2563eb 96.51%);
  color: #fff;
}
.direction-primary:hover { transform: scale(1.03); }
.direction-primary:active { transform: scale(0.97); }

.direction-primary:disabled,
.direction-secondary:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  transform: none;
}

.directions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(22rem, 1fr));
  gap: 1.2rem;
}

.direction-card {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  min-height: 13.4rem;
  padding: 1.45rem;
  border: 1px solid #eef2f7;
  border-radius: 1.1rem;
  background: #f8fafc;
  color: #182033;
  text-align: left;
  cursor: pointer;
  transition: transform 0.18s, box-shadow 0.18s, border-color 0.18s;
}

.direction-card:hover,
.direction-table-row:hover {
  transform: translateY(-1px);
  border-color: #bfdbfe;
  box-shadow: 0 1.2rem 2.6rem rgba(37, 99, 235, 0.08);
}

.direction-card--unassigned {
  background: #fff7ed;
  border-color: #fed7aa;
}

.direction-card__top,
.direction-card__bottom {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.direction-card__top strong {
  font-size: 1.45rem;
}

.direction-card__top span,
.direction-card__bottom span {
  color: #94a3b8;
  font-size: 1.1rem;
  white-space: nowrap;
}

.direction-card__money {
  font-size: 2rem;
  font-weight: 800;
}

.direction-share {
  height: 0.55rem;
  border-radius: 999px;
  background: #e8eef7;
  overflow: hidden;
}

.direction-share span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #2563eb, #18b7c8);
}

.direction-card__bottom strong {
  color: #334155;
  font-size: 1.12rem;
  text-align: right;
}

.directions-table {
  display: grid;
  gap: 0.65rem;
}

.direction-table-row {
  display: grid;
  grid-template-columns: minmax(16rem, 1fr) repeat(4, minmax(8rem, auto));
  gap: 1rem;
  align-items: center;
  padding: 1.1rem 1.2rem;
  border: 1px solid #eef2f7;
  border-radius: 0.9rem;
  background: #f8fafc;
  color: #334155;
  cursor: pointer;
}

.direction-table-name {
  color: #111827;
  font-weight: 800;
}

.metric-card {
  position: relative;
  padding: 2.5rem;
  border-radius: 1.5rem;
  background: #fff;
  display: flex;
  align-items: center;
  border: 2px solid transparent;
  overflow: hidden;
  transition: border-color 0.3s, box-shadow 0.3s;
}
.metric-card.metric-card--add {
  background: transparent;
  border-style: dashed;
  border-color: #d1d5db;
  overflow: visible;
}

.metric-card--anomaly-warning {
  border-color: #fcd34d;
  box-shadow: 0 0 0 1px rgba(251, 191, 36, 0.15), 0 0.4rem 1rem rgba(251, 191, 36, 0.08);
}
.metric-card--anomaly-problem {
  border-color: #fca5a5;
  box-shadow: 0 0 0 1px rgba(239, 68, 68, 0.15), 0 0.4rem 1rem rgba(239, 68, 68, 0.08);
}

.anomaly-dot {
  position: absolute;
  top: 0.9rem;
  right: 0.9rem;
  width: 0.625rem;
  height: 0.625rem;
  border-radius: 50%;
  cursor: pointer;
  z-index: 2;
  animation: anomaly-pulse 2s ease-in-out infinite;
}
.anomaly-dot--warning {
  background: #f59e0b;
  box-shadow: 0 0 0 2px #fff, 0 0 0.5rem rgba(245, 158, 11, 0.4);
}
.anomaly-dot--problem {
  background: #ef4444;
  box-shadow: 0 0 0 2px #fff, 0 0 0.5rem rgba(239, 68, 68, 0.4);
}
@keyframes anomaly-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.detector-banner-slot {
  margin-top: 2rem;
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
  grid-template-columns: 1fr 1fr;
  gap: 1.6rem;
  margin-top: 1.6rem;
  align-items: stretch;
  overflow: visible;
}

.chart-panel,
.goals-panel {
  min-height: 40rem;
  padding: 2.4rem;
}

.chart-panel {
  display: flex;
  flex-direction: column;
  overflow: visible;
  position: relative;
  z-index: 2;
}

.goals-panel {
  display: flex;
  flex-direction: column;
  min-width: 0;
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

.chart-metric-chips {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.8rem;
  flex-wrap: wrap;
}

.chart-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.55rem;
  height: 2.6rem;
  padding: 0 1.1rem;
  border: 1px solid #e5e7eb;
  border-radius: 10rem;
  background: #fff;
  color: #6b7280;
  font-size: 1.1rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.18s ease;
  font-family: Inter, system-ui, sans-serif;
}

.chart-chip__dot {
  width: 0.68rem;
  height: 0.68rem;
  border-radius: 50%;
  box-shadow: 0 0 0 0.25rem rgba(255, 255, 255, 0.75);
  flex-shrink: 0;
}

.chart-chip:hover {
  border-color: #93a8f0;
  color: #2563eb;
  background: #f8faff;
}

.chart-chip--active {
  background: #2563eb;
  border-color: #2563eb;
  color: #fff;
}

.chart-chip--active:hover {
  background: #1d4ed8;
  border-color: #1d4ed8;
  color: #fff;
}

.chart-area {
  position: relative;
  margin-top: 0.6rem;
  flex: 1;
  min-height: 30rem;
  overflow: visible;
  z-index: 3;
}

.chart-area svg {
  width: 100%;
  height: 100%;
  overflow: visible;
}

.grid-lines line {
  stroke: rgba(0,0,0,0.05);
  stroke-width: 1;
}

.axis-y-line {
  stroke: rgba(0,0,0,0.08);
  stroke-width: 1;
}

@keyframes chart-draw {
  from { stroke-dashoffset: 5000; }
  to   { stroke-dashoffset: 0; }
}

@keyframes chart-fill-in {
  from { opacity: 0; }
  to   { opacity: 1; }
}

.chart-fill {
  pointer-events: none;
  animation: chart-fill-in 1s cubic-bezier(0.16, 1, 0.3, 1) both;
}

.chart-line {
  fill: none;
  stroke-width: 2.6;
  stroke-linejoin: round;
  stroke-linecap: round;
  filter: drop-shadow(0 2px 6px rgba(37, 99, 235, 0.12));
  stroke-dasharray: 5000;
  animation: chart-draw 1.6s cubic-bezier(0.16, 1, 0.3, 1) both;
}

.chart-area circle {
  fill: #2563eb;
  stroke: #fff;
  stroke-width: 2.5;
}

.axis-labels text {
  fill: rgba(43, 48, 52, 0.45);
  font-size: 1.4rem;
  font-family: Inter, system-ui, sans-serif;
  font-weight: 500;
}

.axis-label--active {
  fill: #2563eb !important;
  font-weight: 600;
}

.chart-hover-line {
  stroke: #94a3b8;
  stroke-width: 1.5;
  stroke-dasharray: 4 4;
  opacity: 0.5;
}

.chart-hover-dot {
  stroke: #fff;
  stroke-width: 3;
  filter: drop-shadow(0 2px 6px rgba(37, 99, 235, 0.35));
}

.chart-tooltip {
  position: fixed;
  z-index: 1000;
  min-width: 17rem;
  max-width: min(24rem, calc(100vw - 2rem));
  padding: 1.1rem 1.4rem;
  border-radius: 1rem;
  background: #1e293b;
  color: #fff;
  font-size: 1.1rem;
  font-family: Inter, system-ui, sans-serif;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2), 0 2px 6px rgba(0, 0, 0, 0.08);
  pointer-events: none;
  white-space: normal;
  backdrop-filter: blur(8px);
}

.chart-tooltip__date {
  font-size: 1rem;
  color: rgba(255, 255, 255, 0.5);
  margin-bottom: 0.5rem;
  font-weight: 400;
}

.chart-tooltip__main {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  font-weight: 600;
  font-size: 1.2rem;
  line-height: 1.3;
  margin-top: 0.35rem;
}

.chart-tooltip__dot {
  width: 0.65rem;
  height: 0.65rem;
  border-radius: 50%;
  background: #60a5fa;
  flex-shrink: 0;
}

.chart-tooltip__divider {
  height: 1px;
  background: rgba(255, 255, 255, 0.1);
  margin: 0.65rem 0;
}

.chart-tooltip__ctx {
  font-size: 1rem;
  color: rgba(255, 255, 255, 0.6);
  line-height: 1.7;
}

.chart-tooltip__ctx strong {
  color: rgba(255, 255, 255, 0.95);
  font-weight: 600;
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
  width: clamp(15.2778rem, calc(10rem + var(--goals-count, 3) * 1.9rem), 27.5rem);
  height: clamp(15.2778rem, calc(10rem + var(--goals-count, 3) * 1.9rem), 27.5rem);
  justify-self: center;
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

.goals-panel__header {
  margin-bottom: 1rem;
}

.goals-panel__header h2 {
  font-size: 1.5rem;
  font-weight: 700;
}

.goals-channel-block {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.goals-channel-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.85rem 1rem;
  background: #f8f9fb;
  border: 1px solid #eef0f3;
  border-radius: 0.9rem;
  margin-bottom: 1.1rem;
}

.goals-channel-icon {
  width: 2rem;
  height: 2rem;
  object-fit: contain;
  border-radius: 0.4rem;
  flex-shrink: 0;
}

.goals-channel-name {
  font-size: 1.1rem;
  font-weight: 600;
  color: #1e293b;
}

.goals-channel-expense {
  margin-left: auto;
  color: #6b7280;
  font-size: 1.05rem;
  font-weight: 500;
}

.goals-bar-list {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  flex: 1;
  min-width: 0;
}

.goals-bar-row {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  min-width: 0;
  padding: 0.8rem 1rem;
  border-radius: 0.75rem;
  background: #fafbfc;
  border: 1px solid #f0f2f5;
  transition: border-color 0.15s, background 0.15s;
}

.goals-bar-row:hover {
  border-color: #dde1e8;
  background: #f5f7fa;
}

.goals-bar-row--anomaly-warning {
  border-color: rgba(245, 158, 11, 0.4);
  background: #fffbeb;
}

.goals-bar-row--anomaly-problem {
  border-color: rgba(239, 68, 68, 0.35);
  background: #fef2f2;
}

.goals-bar-left {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.8rem;
  min-width: 0;
}

.goals-bar-name {
  min-width: 0;
  white-space: normal;
  overflow-wrap: anywhere;
  color: #374151;
  font-size: 1.05rem;
  line-height: 1.35;
  font-weight: 450;
}

.goals-bar-meta {
  display: flex;
  align-items: baseline;
  gap: 0.6rem;
  flex-shrink: 0;
}

.goals-bar-track {
  height: 0.45rem;
  background: #eaecf0;
  border-radius: 10rem;
  overflow: hidden;
}

@keyframes goals-bar-grow {
  from { transform: scaleX(0); }
}

.goals-bar-fill {
  height: 100%;
  border-radius: 10rem;
  transform-origin: left center;
  animation: goals-bar-grow 0.7s cubic-bezier(0.16, 1, 0.3, 1) both;
  transition: width 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

.goals-bar-count {
  font-size: 1.1rem;
  font-weight: 600;
  color: #1e293b;
  white-space: nowrap;
}

.goals-bar-trend {
  font-size: 0.9rem;
  font-weight: 500;
  white-space: nowrap;
}

.goals-bar-trend--up {
  color: #059669;
}

.goals-bar-trend--down {
  color: #dc2626;
}

.goals-bar-empty {
  padding: 3rem 0;
  text-align: center;
  color: #d1d5db;
  font-size: 1.15rem;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.goals-footer {
  margin-top: auto;
  padding-top: 1rem;
}

.goals-summary-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 1.05rem;
  color: #6b7280;
}

.goals-summary-row strong {
  color: #1e293b;
  font-size: 1.15rem;
}

.goals-summary-row--accent {
  background: rgba(37, 99, 235, 0.05);
  border: 1px solid rgba(37, 99, 235, 0.14);
  border-radius: 0.75rem;
  padding: 0.85rem 1.1rem;
  color: #2563eb;
}

.goals-summary-row--accent strong {
  color: #1d4ed8;
  font-weight: 700;
}

.goals-total-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 0.5rem;
  padding: 0 0.2rem;
  font-size: 1rem;
  color: #9ca3af;
}

.goals-total-row strong {
  color: #6b7280;
  font-size: 1rem;
  font-weight: 500;
}

.campaigns-panel {
  margin-top: 1.6rem;
  padding: 2.4rem;
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
  grid-template-columns: minmax(26rem, 2.2fr) minmax(13rem, 0.9fr) repeat(6, minmax(9.5rem, 1fr));
  align-items: center;
  min-width: 138rem;
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

.campaign-row--anomaly-warning {
  box-shadow: inset 0 0 0 1px rgba(245, 158, 11, 0.45);
}

.campaign-row--anomaly-problem {
  box-shadow: inset 0 0 0 1px rgba(239, 68, 68, 0.45);
}

.row-anomaly-dot {
  display: inline-block;
  width: 0.58rem;
  height: 0.58rem;
  margin-left: 0.5rem;
  border-radius: 999px;
  vertical-align: middle;
  box-shadow: 0 0 0 0.22rem currentColor;
  opacity: 0.22;
}

.row-anomaly-dot--warning {
  color: #f59e0b;
  background: #f59e0b;
}

.row-anomaly-dot--problem {
  color: #ef4444;
  background: #ef4444;
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

.campaign-direction-pill {
  display: inline-flex;
  align-items: center;
  max-width: 100%;
  min-height: 2.6rem;
  padding: 0.45rem 0.75rem;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.08);
  color: #2563eb;
  font-style: normal;
  font-size: 1.05rem;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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

/* Creative tabs */
.creative-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-bottom: 1.2rem;
}
.creative-tab {
  padding: 0.4rem 0.9rem;
  border: 1px solid #e5e7eb;
  border-radius: 1.5rem;
  background: transparent;
  color: #6b7280;
  font-size: 0.88rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}
.creative-tab:hover { background: #f5f7fa; color: #374151; }
.creative-tab--active {
  background: #2563eb;
  border-color: #2563eb;
  color: #fff;
}
.creative-tab--active:hover { background: #1d4ed8; }

.creative-card {
  flex: 0 0 19.5rem;
}

.creative-image-wrap {
  position: relative;
  border-radius: 1rem;
  overflow: hidden;
}

.creative-image {
  display: block;
  width: 100%;
  min-height: 14rem;
  border-radius: 1rem;
  overflow: hidden;
  background: #f1f5f9;
  background-position: center;
  background-size: cover;
  object-fit: cover;
}

.creative-image-button {
  width: 100%;
  border: 0;
  cursor: zoom-in;
  min-height: 14rem;
}

.creative-image--placeholder {
  background: linear-gradient(135deg, #e2e8f0, #cbd5e1);
}

.creative-image--cover {
  position: relative;
  z-index: 1;
}

.creative-image--video {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  z-index: 2;
  opacity: 0;
  transition: opacity 0.2s;
}
.creative-card:hover .creative-image--video { opacity: 1; }
.creative-card:hover .creative-play-icon { opacity: 0; }

.creative-play-icon {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 3;
  width: 3rem;
  height: 3rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.45);
  color: #fff;
  font-size: 1.1rem;
  transition: opacity 0.2s;
}

.creative-format-badge {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  z-index: 4;
  padding: 0.2rem 0.6rem;
  border-radius: 0.4rem;
  background: rgba(0, 0, 0, 0.55);
  color: #fff;
  font-size: 0.72rem;
  font-weight: 600;
}

.creative-platform {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  width: max-content;
  max-width: 100%;
  min-height: 2.2rem;
  margin-top: 0.8rem;
  padding: 0 0.7rem;
  border-radius: 69.375rem;
  color: #3f3f3f;
  font-size: 0.88rem;
  font-weight: 600;
}
.creative-platform img {
  width: 1.1rem;
  height: 1.1rem;
  object-fit: contain;
}
.creative-platform--yandex { background: #fff7d8; }
.creative-platform--vk { background: #e8f0ff; }
.creative-platform--avito { background: #ecfdf5; }

.creative-title {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-top: 0.5rem;
  color: #171717;
  font-size: 0.95rem;
  font-style: normal;
  font-weight: 600;
  line-height: 1.3;
}
.creative-text {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-top: 0.3rem;
  color: #9ca3af;
  font-size: 0.85rem;
  font-style: normal;
  line-height: 1.35;
}

.creative-empty,
.ai-empty {
  min-height: 18rem;
  margin-top: 2.4rem;
  border-radius: 1.2rem;
  background: #f8fafc;
}

.creative-card--skeleton {
  pointer-events: none;
}
.creative-skeleton,
.creative-skeleton-line {
  position: relative;
  overflow: hidden;
  background: #eef2f7;
}
.creative-skeleton::after,
.creative-skeleton-line::after {
  content: '';
  position: absolute;
  inset: 0;
  transform: translateX(-100%);
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.72), transparent);
  animation: skeleton-shimmer 1.25s infinite;
}
.creative-skeleton-line {
  height: 1rem;
  margin-top: 1.2rem;
  border-radius: 69.375rem;
}
.creative-skeleton-line--short { width: 64%; }

@keyframes skeleton-shimmer {
  100% {
    transform: translateX(100%);
  }
}

.creative-modal {
  position: fixed;
  inset: 0;
  z-index: 100000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  background: rgba(8, 13, 24, 0.72);
}

.creative-modal__content {
  position: relative;
  max-width: min(92vw, 96rem);
  max-height: 88vh;
}

.creative-modal__content img {
  display: block;
  max-width: 100%;
  max-height: 88vh;
  border-radius: 1.2rem;
  object-fit: contain;
  background: #fff;
}

.creative-modal__close {
  position: absolute;
  top: -1.4rem;
  right: -1.4rem;
  display: grid;
  place-items: center;
  width: 3.6rem;
  height: 3.6rem;
  border: 0;
  border-radius: 69.375rem;
  background: #fff;
  color: #171717;
  cursor: pointer;
}

.creative-modal__close svg {
  width: 1.8rem;
  height: 1.8rem;
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
    min-width: 132rem;
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
  min-height: auto;
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

.sync-btn-ghost {
  border-radius: 0.8333rem;
  padding: 0 0.9722rem;
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
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 1.3889rem;
  margin-top: 1.3889rem;
  align-items: stretch;
}

.chart-panel,
.goals-panel {
  min-height: 28rem;
  padding: 1.7361rem;
}

.chart-panel {
  display: flex;
  min-width: 0;
  flex-direction: column;
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
  height: 24rem;
  margin-top: 0.8rem;
  flex: 1;
  min-height: 24rem;
}

.axis-labels text {
  font-size: 1.15rem;
}

.goals-content {
  grid-template-columns: minmax(12.5rem, min(22rem, calc(8.5rem + var(--goals-count, 3) * 1.65rem))) minmax(0, 1fr);
  gap: 1.6667rem;
  align-items: center;
  margin-top: 1.6667rem;
}

.donut-wrap {
  width: clamp(12.5rem, calc(8.5rem + var(--goals-count, 3) * 1.65rem), 22rem);
  height: clamp(12.5rem, calc(8.5rem + var(--goals-count, 3) * 1.65rem), 22rem);
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
  grid-template-columns: minmax(18.0556rem, 2.1fr) minmax(9.0278rem, 0.9fr) repeat(6, minmax(6.9444rem, 1fr));
  min-width: 86.1111rem;
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

.campaign-direction-pill {
  min-height: 1.8056rem;
  padding: 0.2778rem 0.5208rem;
  font-size: 0.7292rem;
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
  align-items: center;
}

.ai-generate-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  margin-left: auto;
  padding: 0.3611rem 0.8333rem;
  border-radius: 0.5556rem;
  border: 1.5px solid rgba(99, 91, 255, 0.35);
  background: rgba(99, 91, 255, 0.07);
  color: #635bff;
  font-size: 0.7778rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, opacity 0.15s;
  white-space: nowrap;
  flex-shrink: 0;
}
.ai-generate-btn:hover:not(:disabled) {
  background: rgba(99, 91, 255, 0.14);
  border-color: rgba(99, 91, 255, 0.6);
}
.ai-generate-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.ai-generate-btn__icon {
  width: 0.8333rem;
  height: 0.8333rem;
}
.ai-generate-btn__spinner {
  width: 0.8333rem;
  height: 0.8333rem;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

.ai-download-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  flex-shrink: 0;
  border-radius: 0.5rem;
  border: 1.5px solid rgba(99, 91, 255, 0.25);
  background: rgba(99, 91, 255, 0.05);
  color: #635bff;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}
.ai-download-btn:hover {
  background: rgba(99, 91, 255, 0.13);
  border-color: rgba(99, 91, 255, 0.5);
}
.ai-download-btn svg {
  width: 1rem;
  height: 1rem;
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

/* Skeleton */
.ai-skeleton {
  margin-top: 1.3889rem;
  display: flex;
  flex-direction: column;
  gap: 0.6944rem;
}
.ai-skeleton-line {
  height: 0.75rem;
  border-radius: 0.4rem;
  background: linear-gradient(90deg, #eef2f7 25%, #e2e8f0 50%, #eef2f7 75%);
  background-size: 200% 100%;
  animation: ai-shimmer 1.4s infinite;
  width: 75%;
}
.ai-skeleton-line--wide { width: 95%; }
.ai-skeleton-line--medium { width: 60%; }
.ai-skeleton-line--narrow { width: 40%; }
@keyframes ai-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* CTA (no comment yet) */
.ai-cta {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 16rem;
  text-align: center;
  gap: 0.8333rem;
  padding: 1.3889rem;
}
.ai-cta__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 3rem;
  height: 3rem;
  border-radius: 0.8333rem;
  background: linear-gradient(135deg, rgba(99,91,255,0.12), rgba(139,92,246,0.12));
  color: #635bff;
}
.ai-cta__icon svg { width: 1.4rem; height: 1.4rem; }
.ai-cta__title {
  font-size: 1rem;
  font-weight: 600;
  color: #171717;
  margin: 0;
}
.ai-cta__desc {
  font-size: 0.8rem;
  color: #6b7280;
  max-width: 22rem;
  line-height: 1.5;
  margin: 0;
}
.ai-cta__btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.5rem;
  padding: 0.6111rem 1.3889rem;
  border-radius: 0.6667rem;
  border: none;
  background: linear-gradient(135deg, #635bff, #8b5cf6);
  color: #fff;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s, transform 0.1s;
}
.ai-cta__btn svg { width: 1rem; height: 1rem; }
.ai-cta__btn:hover:not(:disabled) { opacity: 0.88; transform: translateY(-1px); }
.ai-cta__btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }

/* Markdown-rendered report */
.ai-report-body {
  margin-top: 1.1111rem;
  max-height: 17rem;
  overflow-y: auto;
  font-size: 0.8rem;
  line-height: 1.65;
  color: #374151;
  scrollbar-width: thin;
}
.ai-report-body :deep(.ai-md-h--1) { font-size: 0.9rem; font-weight: 700; margin: 0.8rem 0 0.3rem; color: #111827; }
.ai-report-body :deep(.ai-md-h) { font-size: 0.8333rem; font-weight: 700; margin: 0.7rem 0 0.25rem; color: #1f2937; }
.ai-report-body :deep(.ai-md-p) { margin: 0 0 0.4rem; }
.ai-report-body :deep(.ai-md-ul),
.ai-report-body :deep(.ai-md-ol) { padding-left: 1.2rem; margin: 0.3rem 0 0.5rem; }
.ai-report-body :deep(li) { margin-bottom: 0.2rem; }
.ai-report-body :deep(.ai-md-table) {
  width: 100%;
  border-collapse: collapse;
  margin: 0.5rem 0;
  font-size: 0.75rem;
}
.ai-report-body :deep(.ai-md-table th) {
  background: #f3f4f6;
  padding: 0.3rem 0.5rem;
  text-align: left;
  font-weight: 600;
  border-bottom: 1.5px solid #e5e7eb;
}
.ai-report-body :deep(.ai-md-table td) {
  padding: 0.28rem 0.5rem;
  border-bottom: 1px solid #f3f4f6;
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
    min-width: 83.3333rem;
  }
}

/* Figma top-panel alignment */
.top-grid {
  grid-template-columns: minmax(25rem, 34.3056rem) minmax(52.7778rem, 1fr);
  gap: 1.3889rem;
  align-items: stretch;
}

.panel-channels {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: auto;
  padding: 1.7361rem;
  overflow: visible;
}

.panel-reports {
  height: 100%;
  min-height: auto;
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

.panel-channels .channel-balance-block {
  margin-top: auto;
}

.panel-channels .channel-balance-title {
  margin-bottom: 0.5556rem;
}

.panel-channels .channel-balance-list {
  gap: 0.6944rem;
}

.panel-channels .analytics-balance-tile {
  min-height: unset;
  height: 3.1944rem;
  padding: 0 1.0417rem;
  border-radius: 0.8333rem;
}

.panel-channels .analytics-balance-icon {
  width: 1.5rem;
  height: 1.5rem;
}

.panel-channels .analytics-balance-name,
.panel-channels .analytics-balance-value,
.panel-channels .channel-balance-empty {
  font-size: 0.9028rem;
}

.panel-channels .analytics-balance-value {
  min-height: 1.5278rem;
  padding: 0 0.5556rem;
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
  align-self: start;
  width: auto;
  height: 3.1944rem;
  margin-top: 2.7778rem;
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

:global(.dark) .channel-balance-title,
:global(.darkmode) .channel-balance-title {
  color: rgba(255, 255, 255, 0.55);
}

:global(.dark) .analytics-balance-tile,
:global(.darkmode) .analytics-balance-tile {
  background: rgba(255, 255, 255, 0.07) !important;
}

:global(.dark) .analytics-balance-value,
:global(.darkmode) .analytics-balance-value {
  background: rgba(255, 255, 255, 0.11);
}

:global(.dark) .channel-balance-empty,
:global(.darkmode) .channel-balance-empty {
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.5);
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
:global(.dark) .ai-panel > p,
:global(.darkmode) .ai-panel > p {
  color: rgba(255, 255, 255, 0.48);
}

:global(.dark) .ai-report-body,
:global(.darkmode) .ai-report-body {
  color: rgba(255, 255, 255, 0.75);
}
:global(.dark) .ai-report-body :deep(.ai-md-table th),
:global(.darkmode) .ai-report-body :deep(.ai-md-table th) {
  background: rgba(255,255,255,0.06);
  border-bottom-color: rgba(255,255,255,0.1);
}
:global(.dark) .ai-report-body :deep(.ai-md-table td),
:global(.darkmode) .ai-report-body :deep(.ai-md-table td) {
  border-bottom-color: rgba(255,255,255,0.05);
}
:global(.dark) .ai-skeleton-line,
:global(.darkmode) .ai-skeleton-line {
  background: linear-gradient(90deg, rgba(255,255,255,0.06) 25%, rgba(255,255,255,0.1) 50%, rgba(255,255,255,0.06) 75%);
  background-size: 200% 100%;
  animation: ai-shimmer 1.4s infinite;
}
:global(.dark) .ai-cta__title,
:global(.darkmode) .ai-cta__title {
  color: rgba(255,255,255,0.9);
}
:global(.dark) .ai-cta__desc,
:global(.darkmode) .ai-cta__desc {
  color: rgba(255,255,255,0.45);
}
:global(.dark) .ai-md-h,
:global(.darkmode) .ai-md-h {
  color: rgba(255,255,255,0.88);
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

:global(.dark) .period-popover.period-list,
:global(.darkmode) .period-popover.period-list {
  background-color: #2a2d3c;
  box-shadow: 0 1.6rem 4rem rgba(0, 0, 0, 0.32), 0 0 0 1px rgba(255, 255, 255, 0.08);
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
:global(.dark) .project-period-custom-picker :deep(.drp-trigger),
:global(.darkmode) .project-period-custom-picker :deep(.drp-trigger) {
  border-bottom-color: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.9);
}
:global(.dark) .project-period-custom-picker :deep(.drp-trigger:hover),
:global(.darkmode) .project-period-custom-picker :deep(.drp-trigger:hover) {
  background: rgba(255, 255, 255, 0.06);
}
:global(.dark) .project-period-custom-picker :deep(.drp-trigger .truncate),
:global(.darkmode) .project-period-custom-picker :deep(.drp-trigger .truncate) {
  color: rgba(255, 255, 255, 0.9);
}

:global(.dark) .sync-btn-ghost,
:global(.darkmode) .sync-btn-ghost {
  color: rgba(255, 255, 255, 0.48);
}
:global(.dark) .sync-btn-ghost:hover:not(:disabled),
:global(.darkmode) .sync-btn-ghost:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.62);
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
    margin-top: 0;
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

  .panel-channels .channel-balance-list {
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
.figma-dashboard.is-dark .metric-card--anomaly-warning {
  border-color: rgba(251, 191, 36, 0.4);
  box-shadow: 0 0 0 1px rgba(251, 191, 36, 0.2);
  background: rgba(251, 191, 36, 0.04);
}
.figma-dashboard.is-dark .metric-card--anomaly-problem {
  border-color: rgba(239, 68, 68, 0.4);
  box-shadow: 0 0 0 1px rgba(239, 68, 68, 0.2);
  background: rgba(239, 68, 68, 0.04);
}
.figma-dashboard.is-dark .anomaly-dot--warning {
  box-shadow: 0 0 0 2px #2a2d3c, 0 0 0.5rem rgba(245, 158, 11, 0.5);
}
.figma-dashboard.is-dark .anomaly-dot--problem {
  box-shadow: 0 0 0 2px #2a2d3c, 0 0 0.5rem rgba(239, 68, 68, 0.5);
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

.figma-dashboard.is-dark .period-popover.period-list {
  background-color: #2a2d3c;
  box-shadow: 0 1.6rem 4rem rgba(0, 0, 0, 0.32), 0 0 0 1px rgba(255, 255, 255, 0.08);
}
.figma-dashboard.is-dark .period-list__divider {
  background: rgba(255, 255, 255, 0.08);
}
.figma-dashboard.is-dark .period-option {
  color: rgba(255, 255, 255, 0.72);
}
.figma-dashboard.is-dark .period-option:hover,
.figma-dashboard.is-dark .period-option.selected {
  background: rgba(255, 255, 255, 0.06);
}
.figma-dashboard.is-dark .period-option__check {
  color: rgba(255, 255, 255, 0.9);
}

.figma-dashboard.is-dark .sync-btn-ghost {
  color: rgba(255, 255, 255, 0.48);
}
.figma-dashboard.is-dark .sync-btn-ghost:hover:not(:disabled) {
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
  stroke: rgba(255, 255, 255, 0.07);
}

.figma-dashboard.is-dark .axis-y-line {
  stroke: rgba(255, 255, 255, 0.1);
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

.figma-dashboard.is-dark .goals-bar-row--anomaly-warning {
  border-color: rgba(245, 158, 11, 0.45);
  background: rgba(245, 158, 11, 0.1);
}

.figma-dashboard.is-dark .goals-bar-row--anomaly-problem {
  border-color: rgba(239, 68, 68, 0.45);
  background: rgba(239, 68, 68, 0.1);
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

.figma-dashboard.is-dark .campaign-row--anomaly-warning {
  box-shadow: inset 0 0 0 1px rgba(245, 158, 11, 0.45);
}

.figma-dashboard.is-dark .campaign-row--anomaly-problem {
  box-shadow: inset 0 0 0 1px rgba(239, 68, 68, 0.45);
}

.figma-dashboard.is-dark .progress-line div {
  background: rgba(255, 255, 255, 0.12);
}

.figma-dashboard.is-dark .see-all {
  color: #4a7aff;
}

.figma-dashboard.is-dark .chart-chip {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.12);
  color: rgba(255, 255, 255, 0.6);
}

.figma-dashboard.is-dark .chart-chip:hover {
  border-color: #4a7aff;
  color: #4a7aff;
}

.figma-dashboard.is-dark .chart-chip--active {
  background: #4a7aff;
  border-color: #4a7aff;
  color: #fff;
}

.figma-dashboard.is-dark .chart-tooltip {
  background: #0f172a;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
}

.figma-dashboard.is-dark .goals-channel-header {
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(255, 255, 255, 0.07);
}

.figma-dashboard.is-dark .goals-channel-name {
  color: rgba(255, 255, 255, 0.88);
}

.figma-dashboard.is-dark .goals-channel-expense {
  color: rgba(255, 255, 255, 0.45);
}

.figma-dashboard.is-dark .goals-bar-row {
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(255, 255, 255, 0.06);
}

.figma-dashboard.is-dark .goals-bar-row:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.1);
}

.figma-dashboard.is-dark .goals-bar-name {
  color: rgba(255, 255, 255, 0.7);
}

.figma-dashboard.is-dark .goals-bar-track {
  background: rgba(255, 255, 255, 0.08);
}

.figma-dashboard.is-dark .goals-bar-count {
  color: rgba(255, 255, 255, 0.9);
}

.figma-dashboard.is-dark .goals-bar-empty {
  color: rgba(255, 255, 255, 0.35);
}

.figma-dashboard.is-dark .goals-summary-row {
  color: rgba(255, 255, 255, 0.5);
}

.figma-dashboard.is-dark .goals-summary-row strong {
  color: rgba(255, 255, 255, 0.9);
}

.figma-dashboard.is-dark .goals-summary-row--accent {
  background: rgba(74, 122, 255, 0.1);
  border-color: rgba(74, 122, 255, 0.22);
  color: #4a7aff;
}

.figma-dashboard.is-dark .goals-summary-row--accent strong {
  color: #6b95ff;
}

.figma-dashboard.is-dark .goals-total-row {
  color: rgba(255, 255, 255, 0.35);
}

.figma-dashboard.is-dark .goals-total-row strong {
  color: rgba(255, 255, 255, 0.5);
}

/* Chart responsiveness pass: keep plots readable instead of squeezing them. */
.chart-goals-grid {
  align-items: stretch;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
}

.chart-panel {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.chart-area {
  display: flex;
  align-items: center;
  width: 100%;
  min-height: 24rem;
  flex: 1;
  aspect-ratio: 880 / 340;
  overflow-x: auto;
  overflow-y: hidden;
  overscroll-behavior-x: contain;
}

.chart-area svg {
  flex: 0 0 auto;
  display: block;
  width: max(50rem, 100%);
  height: auto;
  aspect-ratio: 880 / 300;
  max-height: 100%;
}

.goals-content {
  grid-template-columns: minmax(12.5rem, min(22rem, calc(8.5rem + var(--goals-count, 3) * 1.65rem))) minmax(0, 1fr);
  align-items: center;
  min-width: 0;
}

.donut-wrap {
  width: clamp(12.5rem, calc(8.5rem + var(--goals-count, 3) * 1.65rem), 22rem);
  height: clamp(12.5rem, calc(8.5rem + var(--goals-count, 3) * 1.65rem), 22rem);
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

.creative-image-button {
  appearance: none;
  min-height: 10.4167rem;
  padding: 0;
  outline: none;
}

.creative-image-button:focus-visible {
  box-shadow: 0 0 0 0.2083rem rgba(37, 99, 235, 0.22);
}

.creative-platform {
  min-height: 1.9444rem;
  margin-top: 0.8333rem;
  padding: 0 0.6944rem;
  font-size: 0.7639rem;
}

.creative-platform img {
  width: 0.9722rem;
  height: 0.9722rem;
}


.creative-empty,
.ai-empty {
  min-height: 12.5rem;
  margin-top: 1.6667rem;
  border-radius: 0.8333rem;
}

.creative-skeleton-line {
  height: 0.6944rem;
  margin-top: 0.9722rem;
}

.creative-skeleton-metrics {
  gap: 0.5556rem;
  margin-top: 0.9722rem;
}

.creative-skeleton-metrics span {
  height: 2.2222rem;
  border-radius: 0.5556rem;
}

.figma-dashboard.is-dark .creative-empty,
.figma-dashboard.is-dark .ai-empty,
.figma-dashboard.is-dark .creative-skeleton,
.figma-dashboard.is-dark .creative-skeleton-line {
  background: rgba(255, 255, 255, 0.06);
}
.figma-dashboard.is-dark .creative-title { color: #f3f4f6; }
.figma-dashboard.is-dark .creative-text { color: rgba(255, 255, 255, 0.5); }
.figma-dashboard.is-dark .creative-tab {
  border-color: rgba(255, 255, 255, 0.12);
  color: rgba(255, 255, 255, 0.6);
}
.figma-dashboard.is-dark .creative-tab:hover { background: rgba(255, 255, 255, 0.06); }
.figma-dashboard.is-dark .creative-image--placeholder { background: rgba(255, 255, 255, 0.08); }

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
  .chart-goals-grid {
    grid-template-columns: 1fr;
  }

  .chart-area {
    min-height: 22rem;
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
    min-height: 20rem;
    aspect-ratio: auto;
    margin-top: 1.25rem;
  }

  .chart-area svg {
    width: 47.2222rem;
  }

  .goals-content {
    grid-template-columns: 1fr;
    justify-items: center;
  }

  .goals-list {
    width: 100%;
  }

  .donut-wrap {
    width: min(16.6667rem, 72vw);
    height: min(16.6667rem, 72vw);
  }

  .goals-bar-row {
    grid-template-columns: 1fr;
    gap: 0.4rem;
  }

  .goals-bar-row .goals-bar-track {
    order: -1;
  }

  .chart-metric-chips {
    gap: 0.4rem;
  }

  .chart-chip {
    height: 2.4rem;
    padding: 0 0.8rem;
    font-size: 1.05rem;
  }

  .creative-modal {
    padding: 1.3889rem;
  }

  .creative-modal__close {
    top: 0.6944rem;
    right: 0.6944rem;
  }
}

/* Campaign multiselect filter */
.campaigns-multiselect {
  width: 22rem;
  max-height: 26rem;
  display: flex;
  flex-direction: column;
  padding: 0 !important;
}

.campaigns-multiselect .search-box {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.6rem 0.8rem;
  border-bottom: 1px solid #e5e7eb;
}
.campaigns-multiselect .search-box svg {
  width: 1.1rem;
  height: 1.1rem;
  color: #9ca3af;
  flex-shrink: 0;
}
.campaigns-multiselect .search-box input {
  border: none;
  outline: none;
  background: transparent;
  font-size: 0.9rem;
  width: 100%;
  color: inherit;
}

.cmp-mass-actions {
  display: flex;
  gap: 0.5rem;
  padding: 0.5rem 0.8rem;
  border-bottom: 1px solid #f0f0f0;
}
.cmp-mass-btn {
  font-size: 0.78rem;
  color: #2563eb;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
}
.cmp-mass-btn:hover { text-decoration: underline; }

.cmp-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 0.3rem 0;
}

.cmp-row {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  padding: 0.45rem 0.8rem;
  cursor: pointer;
  transition: background 0.12s;
}
.cmp-row:hover { background: #f5f7fa; }
.cmp-row--archive { opacity: 0.6; }

.cmp-check {
  width: 1rem;
  height: 1rem;
  accent-color: #2563eb;
  cursor: pointer;
  flex-shrink: 0;
}

.cmp-status-dot {
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 50%;
  flex-shrink: 0;
}
.cmp-status-dot--active { background: #22c55e; }
.cmp-status-dot--paused { background: #f59e0b; }
.cmp-status-dot--archive,
.cmp-status-dot--archived { background: #9ca3af; }
.cmp-status-dot--unknown { background: #d1d5db; }

.cmp-name {
  font-size: 0.88rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
}

.cmp-group-header {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  width: 100%;
  padding: 0.45rem 0.8rem;
  font-size: 0.82rem;
  color: #6b7280;
  background: none;
  border: none;
  border-top: 1px solid #f0f0f0;
  cursor: pointer;
}
.cmp-group-header:hover { color: #374151; }
.cmp-group-chevron {
  width: 0.9rem;
  height: 0.9rem;
  transition: transform 0.15s;
}
.cmp-group-chevron--open { transform: rotate(180deg); }

.cmp-empty {
  padding: 1.5rem;
  text-align: center;
  color: #9ca3af;
  font-size: 0.88rem;
}

.cmp-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  padding: 0.6rem 0.8rem;
  border-top: 1px solid #e5e7eb;
}
.cmp-footer-btn {
  font-size: 0.85rem;
  padding: 0.35rem 0.9rem;
  border-radius: 0.4rem;
  border: none;
  cursor: pointer;
  font-weight: 500;
}
.cmp-footer-btn--reset {
  background: transparent;
  color: #6b7280;
}
.cmp-footer-btn--reset:hover { color: #374151; }
.cmp-footer-btn--apply {
  background: #2563eb;
  color: #fff;
}
.cmp-footer-btn--apply:hover { background: #1d4ed8; }

.cs-head--active {
  border-color: #2563eb !important;
  color: #2563eb;
}

.campaign-filter-banner {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.55rem 1.2rem;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 0.5rem;
  font-size: 0.88rem;
  color: #1e40af;
  margin-bottom: 0.5rem;
}
.campaign-filter-banner__reset {
  background: none;
  border: none;
  color: #2563eb;
  cursor: pointer;
  font-size: 0.85rem;
  text-decoration: underline;
  padding: 0;
}
.campaign-filter-banner__reset:hover { color: #1d4ed8; }

.direction-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 9100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.3889rem;
  background: rgba(0, 0, 0, 0.50);
}

.direction-modal {
  position: relative;
  width: min(48.6111rem, 94vw);
  max-height: min(84vh, 55.5556rem);
  overflow: auto;
  padding: 2.0833rem;
  border: 1px solid rgba(0, 0, 0, 0.05);
  border-radius: 1.3889rem;
  background: #fff;
  box-shadow: 0 1.3889rem 3.4722rem rgba(0, 0, 0, 0.12);
}
:global(.dark) .direction-modal { background: #2C2F3D; border-color: rgba(255,255,255,0.08); }

.direction-modal--manager {
  width: min(62.5rem, 96vw);
}

.direction-modal__close {
  position: absolute;
  top: 1.0417rem;
  right: 1.0417rem;
  display: grid;
  place-items: center;
  width: 2.2222rem;
  height: 2.2222rem;
  border: 1px solid rgba(0,0,0,0.08);
  border-radius: 50%;
  background: #f5f7f9;
  color: rgba(105,105,105,0.56);
  cursor: pointer;
  transition: background 0.2s;
}
.direction-modal__close:hover { background: #ecf3fe; color: #2563eb; }
:global(.dark) .direction-modal__close { background: rgba(255,255,255,0.08); border-color: rgba(255,255,255,0.1); color: rgba(255,255,255,0.55); }

.direction-modal__close svg {
  width: 1.0417rem;
  height: 1.0417rem;
}

.direction-modal__head {
  margin-bottom: 1.3889rem;
  padding-right: 2.7778rem;
}

.direction-modal__head p {
  margin: 0 0 0.3472rem;
  color: rgba(105,105,105,0.56);
  font-size: 0.8333rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
:global(.dark) .direction-modal__head p { color: rgba(255,255,255,0.40); }

.direction-modal__head h3 {
  margin: 0;
  color: #171717;
  font-size: 1.6667rem;
  font-weight: 700;
}
:global(.dark) .direction-modal__head h3 { color: #fff; }

.direction-label-setting {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(12.5rem, 15.2778rem) auto;
  gap: 0.8333rem;
  align-items: center;
  margin-bottom: 1.0417rem;
  padding: 0.8333rem 1.0417rem;
  border: 1px solid rgba(0,0,0,0.05);
  border-radius: 0.8333rem;
  background: #f5f7f9;
}
:global(.dark) .direction-label-setting { background: rgba(255,255,255,0.05); border-color: rgba(255,255,255,0.08); }

.direction-label-setting > div {
  display: grid;
  gap: 0.2083rem;
}

.direction-label-setting strong {
  color: #171717;
  font-size: 0.9722rem;
  font-weight: 600;
}
:global(.dark) .direction-label-setting strong { color: rgba(255,255,255,0.85); }

.direction-label-setting span {
  color: rgba(105,105,105,0.56);
  font-size: 0.8333rem;
}

.direction-label-setting select {
  height: 3.1944rem;
  border: 1px solid rgba(0,0,0,0.08);
  border-radius: 0.6944rem;
  padding: 0 0.8333rem;
  background: #fff;
  color: #171717;
  font-size: 0.9028rem;
  font-weight: 600;
  outline: none;
}
:global(.dark) .direction-label-setting select { background: rgba(255,255,255,0.08); color: rgba(255,255,255,0.85); border-color: rgba(255,255,255,0.1); }

.direction-field {
  display: grid;
  gap: 0.4861rem;
  margin-bottom: 0.8333rem;
  color: rgba(105,105,105,0.65);
  font-size: 0.9028rem;
  font-weight: 600;
}
:global(.dark) .direction-field { color: rgba(255,255,255,0.55); }

.direction-field input {
  height: 3.1944rem;
  border: 1px solid rgba(0,0,0,0.08);
  border-radius: 0.6944rem;
  padding: 0 0.8333rem;
  color: #171717;
  font-size: 0.9722rem;
  outline: none;
  background: #f5f7f9;
  transition: border-color 0.2s, box-shadow 0.2s;
}
:global(.dark) .direction-field input { background: rgba(255,255,255,0.08); color: rgba(255,255,255,0.88); border-color: rgba(255,255,255,0.1); }

.direction-field input:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.08);
}

.direction-mask-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4861rem;
  min-height: 1.6667rem;
  margin-bottom: 0.8333rem;
}

.direction-mask-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.3472rem;
  border: 0;
  border-radius: 2.7778rem;
  padding: 0.3472rem 0.6944rem;
  background: #ecf3fe;
  color: #2563eb;
  font-size: 0.8333rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}
.direction-mask-chip:hover { background: #dbe9ff; }
:global(.dark) .direction-mask-chip { background: rgba(37,99,235,0.15); color: #4A7AFF; }

.direction-mask-chip svg {
  width: 0.7639rem;
  height: 0.7639rem;
}

.direction-preview {
  border: 1px solid rgba(0,0,0,0.05);
  border-radius: 0.8333rem;
  background: #f5f7f9;
  padding: 0.8333rem;
}
:global(.dark) .direction-preview { background: rgba(255,255,255,0.05); border-color: rgba(255,255,255,0.08); }

.direction-preview__summary {
  display: flex;
  align-items: baseline;
  gap: 0.4861rem;
  color: rgba(105,105,105,0.56);
  font-size: 0.9028rem;
}

.direction-preview__summary strong {
  color: #171717;
  font-size: 1.3889rem;
  font-weight: 700;
}
:global(.dark) .direction-preview__summary strong { color: #fff; }

.direction-preview__warning {
  margin: 0.4861rem 0 0;
  color: #b45309;
  font-size: 0.8333rem;
  font-weight: 600;
}

.direction-campaign-search {
  display: flex;
  align-items: center;
  gap: 0.4861rem;
  margin-top: 0.6944rem;
  max-width: 32.4074rem;
  height: 2.7778rem;
  border: 1px solid rgba(0,0,0,0.08);
  border-radius: 0.6944rem;
  background: #fff;
  padding: 0 0.8333rem;
  color: rgba(105,105,105,0.4);
}
.direction-campaign-search:focus-within {
  border-color: rgba(37, 99, 235, 0.35);
}
:global(.dark) .direction-campaign-search { background: rgba(255,255,255,0.06); border-color: rgba(255,255,255,0.1); }

.direction-campaign-search svg {
  width: 0.9722rem;
  height: 0.9722rem;
  flex: 0 0 auto;
}

/* Перебиваем легаси base-app.css (.main-layout input[type="text"]: height 4.6rem, padding, box-shadow) */
.direction-preview .direction-campaign-search input[type="text"] {
  width: 100%;
  height: 100%;
  border: 0;
  outline: 0;
  padding: 0;
  background: transparent;
  box-shadow: none;
  border-radius: 0;
  color: #171717;
  font: 400 0.9028rem/130% "Inter", sans-serif;
}
:global(.dark) .direction-preview .direction-campaign-search input[type="text"] { color: rgba(255,255,255,0.88); }

.direction-preview__list {
  display: grid;
  gap: 0.3472rem;
  max-height: 15.2778rem;
  overflow: auto;
  margin-top: 0.6944rem;
}

.direction-preview__row,
.direction-manager-row {
  display: flex;
  justify-content: space-between;
  gap: 0.6944rem;
  align-items: center;
  border-radius: 0.6944rem;
  background: #fff;
  padding: 0.5556rem 0.6944rem;
  color: #444;
  font-size: 0.9028rem;
}
:global(.dark) .direction-preview__row,
:global(.dark) .direction-manager-row { background: rgba(255,255,255,0.06); color: rgba(255,255,255,0.75); }

.direction-campaign-option {
  width: 100%;
  border: 1px solid transparent;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}

.direction-campaign-option:hover {
  border-color: rgba(37,99,235,0.15);
  background: #f8faff;
}
:global(.dark) .direction-campaign-option:hover { background: rgba(255,255,255,0.08); border-color: rgba(74,122,255,0.2); }

.direction-campaign-option--selected {
  border-color: rgba(37,99,235,0.25);
  background: #ecf3fe;
}
:global(.dark) .direction-campaign-option--selected { background: rgba(37,99,235,0.1); border-color: rgba(74,122,255,0.25); }

.direction-campaign-option--conflict {
  border-color: rgba(245,158,11,0.3);
}

.direction-campaign-option__check {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.25rem;
  height: 1.25rem;
  border-radius: 50%;
  background: #ecf3fe;
  color: #2563eb;
  font-size: 0.7639rem;
  font-weight: 700;
  flex: 0 0 auto;
}
:global(.dark) .direction-campaign-option__check { background: rgba(37,99,235,0.15); color: #4A7AFF; }

.direction-campaign-option--selected .direction-campaign-option__check {
  background: #2563eb;
  color: #fff;
}

.direction-campaign-option__body {
  display: grid;
  gap: 0.1389rem;
  min-width: 0;
  flex: 1 1 auto;
}

.direction-campaign-option__body strong {
  overflow: hidden;
  color: #171717;
  font-size: 0.9028rem;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}
:global(.dark) .direction-campaign-option__body strong { color: rgba(255,255,255,0.85); }

.direction-campaign-option__meta {
  display: inline-flex;
  align-items: center;
  gap: 0.3472rem;
  flex: 0 0 auto;
}

.direction-campaign-platform,
.direction-campaign-status {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 2.7778rem;
  padding: 0.2083rem 0.4861rem;
  font-size: 0.7639rem;
  font-weight: 600;
  white-space: nowrap;
}

.direction-campaign-platform {
  background: #f5f7f9;
  color: rgba(105,105,105,0.65);
}
:global(.dark) .direction-campaign-platform { background: rgba(255,255,255,0.08); color: rgba(255,255,255,0.55); }

.direction-campaign-status--active {
  background: rgba(0,255,78,0.10);
  color: #16a34a;
}

.direction-campaign-status--paused {
  background: rgba(245,158,11,0.10);
  color: #92400e;
}

.direction-campaign-status--archived,
.direction-campaign-status--archive,
.direction-campaign-status--unknown {
  background: #f5f7f9;
  color: rgba(105,105,105,0.65);
}

.direction-preview__row small {
  color: rgba(105,105,105,0.56);
  font-size: 0.7639rem;
  font-weight: 500;
}

.direction-preview__row small.direction-preview__conflict {
  color: #b45309;
}

.direction-preview__empty {
  padding: 0.8333rem;
  color: rgba(105,105,105,0.4);
  text-align: center;
  font-size: 0.8333rem;
}

.direction-modal__actions,
.direction-manager-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.6944rem;
  margin-top: 1.0417rem;
  padding-top: 1.0417rem;
  border-top: 1px solid rgba(0,0,0,0.05);
}
:global(.dark) .direction-modal__actions, :global(.dark) .direction-manager-actions { border-top-color: rgba(255,255,255,0.08); }

.direction-modal .direction-secondary,
.direction-modal .direction-primary {
  min-height: 3.1944rem;
  padding: 0 1.3889rem;
  font-size: 0.9722rem;
}

@media (max-width: 640px) {
  .direction-modal-overlay {
    align-items: flex-end;
    padding: 0.8rem;
  }

  .direction-modal {
    width: 100%;
    max-height: 88vh;
    padding: 1.35rem;
    border-radius: 1.1rem;
  }

  .direction-modal__head h3 {
    font-size: 1.35rem;
  }

  .direction-campaign-option {
    align-items: flex-start;
  }

  .direction-campaign-option__meta {
    flex-direction: column;
    align-items: flex-end;
    gap: 0.3rem;
  }

  .direction-preview__list {
    max-height: 42vh;
  }
}

.direction-suggestions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(18rem, 1fr));
  gap: 0.8rem;
  margin-top: 1.2rem;
}

.direction-suggestion {
  display: grid;
  gap: 0.35rem;
  border: 1px solid #dbeafe;
  border-radius: 1rem;
  background: #eff6ff;
  padding: 1rem;
  color: #1e3a8a;
  text-align: left;
}

.direction-suggestion span {
  color: #64748b;
  font-size: 1.05rem;
}

.direction-manager-list {
  display: grid;
  gap: 0.75rem;
  margin-top: 1.4rem;
}

.direction-manager-row > div:first-child {
  display: grid;
  gap: 0.3rem;
}

.direction-manager-row span {
  color: #94a3b8;
  font-size: 1.1rem;
}

.direction-manager-row__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  justify-content: flex-end;
}

.direction-manager-row__actions button {
  min-height: 3rem;
  border: 1px solid #dbe2ee;
  border-radius: 0.75rem;
  background: #fff;
  color: #475569;
  padding: 0 0.85rem;
  font-size: 1.05rem;
  font-weight: 700;
}

.direction-manager-row__actions .danger {
  border-color: #fecaca;
  color: #dc2626;
}

.direction-unassigned-note {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  margin-top: 1.2rem;
  padding: 1rem;
  border-radius: 1rem;
  background: #fff7ed;
  color: #9a3412;
}

.direction-unassigned-note > div {
  display: grid;
  gap: 0.25rem;
}

.direction-unassigned-action {
  min-height: 3.2rem;
  border: 1px solid #fed7aa;
  border-radius: 0.85rem;
  background: #fff;
  color: #c2410c;
  padding: 0 1rem;
  font-size: 1.05rem;
  font-weight: 800;
  cursor: pointer;
}

.direction-unassigned-action:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

/* Dark mode for campaign multiselect */
:global(.dark) .campaigns-multiselect,
:global(.darkmode) .campaigns-multiselect,
.figma-dashboard.is-dark .campaigns-multiselect {
  background: #1f2937;
  border-color: #374151;
}
:global(.dark) .campaigns-multiselect .search-box,
:global(.darkmode) .campaigns-multiselect .search-box,
.figma-dashboard.is-dark .campaigns-multiselect .search-box {
  border-color: #374151;
}
:global(.dark) .cmp-row:hover,
:global(.darkmode) .cmp-row:hover,
.figma-dashboard.is-dark .cmp-row:hover {
  background: #374151;
}
:global(.dark) .cmp-mass-actions,
:global(.darkmode) .cmp-mass-actions,
.figma-dashboard.is-dark .cmp-mass-actions {
  border-color: #374151;
}
:global(.dark) .cmp-group-header,
:global(.darkmode) .cmp-group-header,
.figma-dashboard.is-dark .cmp-group-header {
  color: #9ca3af;
  border-color: #374151;
}
:global(.dark) .cmp-footer,
:global(.darkmode) .cmp-footer,
.figma-dashboard.is-dark .cmp-footer {
  border-color: #374151;
}
:global(.dark) .cmp-footer-btn--reset,
:global(.darkmode) .cmp-footer-btn--reset,
.figma-dashboard.is-dark .cmp-footer-btn--reset {
  color: #9ca3af;
}
:global(.dark) .campaign-filter-banner,
:global(.darkmode) .campaign-filter-banner,
.figma-dashboard.is-dark .campaign-filter-banner {
  background: #1e3a5f;
  border-color: #2563eb40;
  color: #93c5fd;
}
</style>
