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
            placeholder="Название, папка или ID"
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

        <div class="project-sync-meta" v-if="projectSyncStatusText" :title="projectSyncStatusTitle">{{ projectSyncStatusText }}</div>

        <button class="tile-sync-btn" type="button" :disabled="projectsSyncing" @click="handleSyncProjects">
          <svg :class="{ spinning: projectsSyncing }" width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M20 11a8.1 8.1 0 0 0-15.5-2M4 5v4h4M4 13a8.1 8.1 0 0 0 15.5 2M20 19v-4h-4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          {{ projectsSyncing ? 'Обновление...' : 'Обновить данные' }}
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

    <div v-else-if="!hasAnyItems" class="py-16 text-center text-[0.9722rem] text-gray-400">
      {{ search ? 'Проекты не найдены' : 'У вас пока нет проектов' }}
    </div>

    <!-- Projects grid: папки + проекты -->
    <div v-else class="projects-tile-grid mb-[2.0833rem]">
      <template v-for="entry in displayItems" :key="entry.type + (entry.folder?.id || entry.project?.id)">

      <!-- ══ Карточка ПАПКИ ══ -->
      <div
        v-if="entry.type === 'folder'"
        class="project-card project-card--tile folder-card bg-white rounded-[1.0417rem]"
        :class="{ 'folder-card--paused': isFolderPaused(entry.folder), 'folder-card--expanded': expandedFolders[entry.folder.id] }"
        :style="{ '--folder-color': entry.folder.color || '#2563eb' }"
      >
        <div class="folder-card__tab" aria-hidden="true">
          <span></span>
        </div>
        <div class="project-tile-main">
          <div class="project-tile-header folder-card__header">
            <div class="project-tile-identity">
              <span class="project-avatar folder-avatar" :style="{ background: entry.folder.color || '#2563eb' }">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M3 7.5A2.5 2.5 0 0 1 5.5 5h3.6c.7 0 1.36.3 1.83.81l1.04 1.13c.28.31.69.49 1.11.49h5.42A2.5 2.5 0 0 1 21 9.93v6.57A2.5 2.5 0 0 1 18.5 19h-13A2.5 2.5 0 0 1 3 16.5v-9Z" fill="#fff" fill-opacity="0.92"/>
                </svg>
              </span>
              <div class="project-tile-title-block">
                <button type="button" class="project-title-link project-title-link--tile" @click="toggleFolder(entry.folder.id)">
                  {{ entry.folder.name }}
                </button>
                <p class="project-tile-description">
                  <span class="folder-type-label">Папка · {{ entry.folder.projects_count || allFolderProjects(entry.folder.id).length }} {{ branchNoun(entry.folder.projects_count || allFolderProjects(entry.folder.id).length) }} · сводная статистика</span>
                  <span v-if="isFolderPaused(entry.folder)" class="folder-paused-note">· все на паузе</span>
                </p>
              </div>
            </div>
            <div class="project-tile-actions">
              <div class="project-tile-actions__top">
                <button
                  type="button"
                  class="folder-member-cloud"
                  :class="{ 'folder-member-cloud--open': expandedFolders[entry.folder.id] }"
                  @click="toggleFolder(entry.folder.id)"
                  :title="expandedFolders[entry.folder.id] ? 'Свернуть папку' : 'Открыть папку'"
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="M3 7.5A2.5 2.5 0 0 1 5.5 5h3.6c.7 0 1.36.3 1.83.81l1.04 1.13c.28.31.69.49 1.11.49h5.42A2.5 2.5 0 0 1 21 9.93v6.57A2.5 2.5 0 0 1 18.5 19h-13A2.5 2.5 0 0 1 3 16.5v-9Z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>
                  </svg>
                  {{ entry.folder.projects_count || allFolderProjects(entry.folder.id).length }}
                  <svg class="folder-member-cloud__chevron" :class="{ 'folder-member-cloud__chevron--open': expandedFolders[entry.folder.id] }" width="11" height="7" viewBox="0 0 12 8" fill="none" aria-hidden="true">
                    <path d="M1 1.5 6 6.5 11 1.5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                </button>
                <button class="analytics-open-btn flex-shrink-0" @click="openFolderAnalytics(entry.folder)" title="Аналитика по папке">
                  <span>Аналитика</span>
                  <svg width="7" height="7" viewBox="0 0 13 13" fill="none">
                    <path d="M1 12L12 1M12 1H4.5M12 1V8.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                </button>
              </div>
            </div>
          </div>

          <div class="project-tile-stats-wrap" :class="{ 'folder-stats--paused': isFolderPaused(entry.folder) }">
            <div class="project-tile-stats">
              <div v-for="stat in projectStats(folderAsEntity(entry.folder))" :key="stat.label" class="stat-box">
                <div class="iconbox flex-shrink-0">
                  <svg width="12" height="12" fill="#2563eb" aria-hidden="true"><use :href="stat.icon" /></svg>
                </div>
                <div class="stat-box__copy">
                  <h4>{{ stat.label }}</h4>
                  <p>Сумма по проектам</p>
                </div>
                <b class="stat-box__value">{{ stat.value }}</b>
                <span :class="trendBadgeClass(getProjectMetric(entry.folder.id), stat.key)">
                  <svg :class="trendArrowClass(getProjectMetric(entry.folder.id), stat.key)" width="8" height="7" viewBox="0 0 12 9" fill="none" aria-hidden="true">
                    <path d="M1 8L6 2L11 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                  {{ stat.change }}
                </span>
              </div>
            </div>
          </div>

          <div class="project-goals-section">
            <div class="project-goals-title">
              <span class="project-goals-title__label">Целевые действия по каналам · вся сеть</span>
            </div>
            <div v-if="projectChannelSummaries(folderAsEntity(entry.folder)).length" class="project-channel-list">
              <div v-for="channel in projectChannelSummaries(folderAsEntity(entry.folder))" :key="channel.code" class="project-channel-card">
                <div class="project-channel-row">
                  <span class="project-channel-icon" :class="`project-channel-icon--${channel.code}`">
                    <img :src="channel.icon" :alt="channel.name" />
                  </span>
                  <div class="project-channel-main"><strong>{{ channel.name }}</strong></div>
                  <div class="project-channel-metrics">
                    <div class="project-channel-metric">
                      <strong>{{ channel.needsGoalSelection ? '—' : formatNumber(channel.goalTotal) }}
                        <em v-if="leadsDeltaBadge(channel)" class="channel-delta" :class="leadsDeltaBadge(channel).cls" :title="leadsDeltaBadge(channel).title"><svg class="channel-delta__arrow" :class="{ 'channel-delta__arrow--down': leadsDeltaBadge(channel).dir === 'down' }" width="8" height="7" viewBox="0 0 12 9" fill="none" aria-hidden="true"><path d="M1 8L6 2L11 8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>{{ leadsDeltaBadge(channel).text }}</em>
                      </strong>
                      <span :title="channel.goalSelectionTooltip || null">{{ channel.goalLabel }}</span>
                    </div>
                    <div class="project-channel-metric project-channel-metric--cpl">
                      <strong>{{ channel.avgCpl !== null ? formatMoney(withChannelVat(channel.avgCpl, channel.code)) : '—' }}
                        <em v-if="cplDeltaBadge(channel)" class="channel-delta" :class="cplDeltaBadge(channel).cls"><svg class="channel-delta__arrow" :class="{ 'channel-delta__arrow--down': cplDeltaBadge(channel).dir === 'down' }" width="8" height="7" viewBox="0 0 12 9" fill="none" aria-hidden="true"><path d="M1 8L6 2L11 8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>{{ cplDeltaBadge(channel).text }}</em>
                      </strong>
                      <span>Общий CPL</span>
                    </div>
                    <div class="project-channel-metric project-channel-metric--spend">
                      <strong>{{ formatMoney(withChannelVat(channel.expenses, channel.code)) }}</strong>
                      <span>Расход</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div v-else class="project-channel-empty">
              <div class="project-channel-empty__copy">
                <strong>Нет данных по каналам</strong>
                <span>Добавьте в папку проекты с подключёнными кабинетами.</span>
              </div>
            </div>
          </div>
        </div>

        <div class="project-tile-footer">
          <div class="project-balance-area">
            <div class="project-balance-title">Баланс в кабинетах · сводно</div>
            <div v-if="projectBalances(folderAsEntity(entry.folder)).length" class="project-balance-strip">
              <div v-for="balance in projectBalances(folderAsEntity(entry.folder))" :key="balance.code" class="balance-chip" :class="`balance-chip--${balance.code}`">
                <img :src="balance.icon" :alt="balance.name" />
                <strong>{{ balance.value }}</strong>
              </div>
            </div>
            <div v-else class="project-balance-empty">Нет подключённых кабинетов</div>
          </div>
          <div class="project-footer-actions">
            <button type="button" class="settings-btn" @click.stop="openEditFolder(entry.folder)">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z"/>
              </svg>
              Настройки папки
            </button>
          </div>
        </div>
      </div>

      <!-- ══ Пустая папка (раскрыта) ══ -->
      <div v-else-if="entry.type === 'folder-empty'" class="folder-empty-card" :style="{ '--folder-color': entry.folder.color || '#2563eb' }">
        <p>В папке пока нет проектов</p>
        <button type="button" @click="openEditFolder(entry.folder)">Добавить проекты в папку</button>
      </div>

      <!-- ══ Карточка ПРОЕКТА (как раньше; v-for по одному элементу задаёт локальную
           переменную project, чтобы не менять существующую разметку карточки) ══ -->
      <template v-else>
      <div
        v-for="project in [entry.project]"
        :key="project.id"
        class="project-card project-card--tile bg-white rounded-[1.0417rem]"
        :class="{
          'project-card--syncing': isProjectSyncing(project),
          'project-card--infolder': Boolean(entry.inFolder),
          'project-card--paused': isProjectPaused(project),
        }"
        :style="entry.inFolder ? { '--folder-color': entry.inFolder.color || '#2563eb' } : {}"
      >
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
                  <span v-if="entry.folderName" class="in-folder-chip" :title="`Проект лежит в папке «${entry.folderName}»`">
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M3 7.5A2.5 2.5 0 0 1 5.5 5h3.6c.7 0 1.36.3 1.83.81l1.04 1.13c.28.31.69.49 1.11.49h5.42A2.5 2.5 0 0 1 21 9.93v6.57A2.5 2.5 0 0 1 18.5 19h-13A2.5 2.5 0 0 1 3 16.5v-9Z"/></svg>
                    {{ entry.folderName }}
                  </span>
                  <!-- Бейдж «Организация» перенесён в раздел «Интеграции». -->
                  <span v-if="isProjectPaused(project)" class="paused-badge">На паузе</span>
                </button>
                <p class="project-tile-description">{{ project.description || 'Без описания' }}</p>
              </div>
            </div>
            <div class="project-tile-actions">
              <div class="project-tile-actions__top">
                <span v-if="detectorBadge(project)" class="detector-preview-wrap">
                  <button
                    type="button"
                    class="detector-badge detector-badge--pill"
                    :class="`detector-badge--${detectorBadge(project).type}`"
                    :title="detectorBadge(project).text"
                    :disabled="!detectorBadge(project).interactive"
                    @click.stop="detectorBadge(project).interactive && toggleDetectorPreview(project.id)"
                  >
                    <svg v-if="detectorBadge(project).type === 'warmup'" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
                    <svg v-else-if="detectorBadge(project).type === 'sync'" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"><path d="M20 11a8.1 8.1 0 0 0-14.9-3.8L3 10"/><path d="M3 4v6h6"/><path d="M4 13a8.1 8.1 0 0 0 14.9 3.8L21 14"/><path d="M21 20v-6h-6"/></svg>
                    <template v-else>
                      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/></svg>
                      {{ detectorBadge(project).count }}
                    </template>
                  </button>
                  <div v-if="detectorPreviewId === project.id && detectorPreview(project).length" class="detector-preview" @click.stop>
                    <div
                      v-for="al in detectorPreview(project)"
                      :key="al.id"
                      class="detector-preview__row"
                      :class="`detector-preview__row--${al.severity}`"
                    >
                      <span class="detector-preview__dot"></span>
                      <div class="detector-preview__copy">
                        <span v-if="detectorAlertChecks(al).length" class="detector-preview__checks">{{ detectorAlertChecks(al).join(' · ') }}</span>
                        <span class="detector-preview__text">{{ al.hypothesis_text || 'Отклонение' }}</span>
                      </div>
                    </div>
                    <div v-if="detectorPreviewMore(project) > 0" class="detector-preview__more">и ещё {{ detectorPreviewMore(project) }}</div>
                    <div class="detector-preview__actions">
                      <button type="button" @click="openProject(project)">Открыть дашборд</button>
                      <button type="button" class="detector-preview__ai" @click="askAiFromPreview(project)">Спросить AI</button>
                    </div>
                  </div>
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

          <div v-if="isProjectPaused(project)" class="project-paused-block">
            <p class="project-paused-block__text">
              Проект приостановлен<template v-if="projectFrozenDate(project)"> · данные заморожены на {{ projectFrozenDate(project) }}</template>
            </p>
            <button type="button" class="project-paused-block__resume" :disabled="resumingProjectId === project.id" @click="resumeProject(project)">
              {{ resumingProjectId === project.id ? 'Возобновляем…' : 'Возобновить' }}
            </button>
          </div>
          <div v-else class="project-tile-stats-wrap">
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
                  data-tooltip="Стоимость по каждой цели не показывается: расход кампании невозможно честно разделить между разными целевыми действиями одной сессии. Для Яндекса показан сводный CPL по всем конверсиям. Для VK Ads общий CPL считается только по действиям, которые агентство явно отметило как заявки."
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
                      <strong>{{ channel.needsGoalSelection ? '—' : formatNumber(channel.goalTotal) }}
                        <em v-if="leadsDeltaBadge(channel)" class="channel-delta" :class="leadsDeltaBadge(channel).cls" :title="leadsDeltaBadge(channel).title"><svg class="channel-delta__arrow" :class="{ 'channel-delta__arrow--down': leadsDeltaBadge(channel).dir === 'down' }" width="8" height="7" viewBox="0 0 12 9" fill="none" aria-hidden="true"><path d="M1 8L6 2L11 8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>{{ leadsDeltaBadge(channel).text }}</em>
                      </strong>
                      <span :title="channel.goalSelectionTooltip || null">{{ channel.goalLabel }}</span>
                    </div>
                    <div class="project-channel-metric project-channel-metric--cpl">
                      <strong>{{ channel.avgCpl !== null ? formatMoney(withChannelVat(channel.avgCpl, channel.code)) : '—' }}
                        <em v-if="cplDeltaBadge(channel)" class="channel-delta" :class="cplDeltaBadge(channel).cls"><svg class="channel-delta__arrow" :class="{ 'channel-delta__arrow--down': cplDeltaBadge(channel).dir === 'down' }" width="8" height="7" viewBox="0 0 12 9" fill="none" aria-hidden="true"><path d="M1 8L6 2L11 8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>{{ cplDeltaBadge(channel).text }}</em>
                      </strong>
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
                    <strong>{{ formatNumber(goal.count) }} шт
                      <em v-if="goalCountDelta(goal)" class="channel-delta" :class="goalCountDelta(goal).cls" :title="goalCountDelta(goal).title"><svg class="channel-delta__arrow" :class="{ 'channel-delta__arrow--down': goalCountDelta(goal).dir === 'down' }" width="8" height="7" viewBox="0 0 12 9" fill="none" aria-hidden="true"><path d="M1 8L6 2L11 8" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>{{ goalCountDelta(goal).text }}</em>
                    </strong>
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
            <!-- Переместить в папку… -->
            <div class="folder-move-wrap" v-click-outside="() => { if (moveMenuProjectId === project.id) moveMenuProjectId = null }">
              <button
                type="button"
                class="settings-btn folder-move-btn"
                :class="{ 'folder-move-btn--loading': movingProjectId === project.id }"
                :title="project.folder_id ? 'Переместить в другую папку или вынести' : 'Переместить в папку'"
                :disabled="movingProjectId === project.id"
                @click.stop="moveMenuProjectId = moveMenuProjectId === project.id ? null : project.id"
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M3 7.5A2.5 2.5 0 0 1 5.5 5h3.6c.7 0 1.36.3 1.83.81l1.04 1.13c.28.31.69.49 1.11.49h5.42A2.5 2.5 0 0 1 21 9.93v6.57A2.5 2.5 0 0 1 18.5 19h-13A2.5 2.5 0 0 1 3 16.5v-9Z"/>
                </svg>
                {{ movingProjectId === project.id ? 'Перемещаем…' : 'В папку' }}
              </button>
              <div v-if="moveMenuProjectId === project.id" class="folder-move-menu">
                <div class="folder-move-menu__title">Переместить проект</div>
                <button
                  v-for="f in folders"
                  :key="f.id"
                  type="button"
                  class="folder-move-menu__item"
                  :class="{ 'folder-move-menu__item--current': project.folder_id === f.id }"
                  :disabled="project.folder_id === f.id || movingProjectId === project.id"
                  @click.stop="moveProjectToFolder(project, f.id)"
                >
                  <i :style="{ background: f.color || '#2563eb' }"></i>
                  {{ f.name }}
                </button>
                <button v-if="project.folder_id" type="button" class="folder-move-menu__item folder-move-menu__item--out" :disabled="movingProjectId === project.id" @click.stop="moveProjectToFolder(project, null)">
                  Вынести из папки
                </button>
                <button type="button" class="folder-move-menu__item folder-move-menu__item--new" @click.stop="moveMenuProjectId = null; openCreateFolder()">
                  + Новая папка
                </button>
                <div v-if="!folders.length" class="folder-move-menu__empty">Папок пока нет</div>
              </div>
            </div>
          </div>
        </div>
      </div>
      </template>

      </template>
    </div>

    <!-- ══ Модал папки: создание / настройки ══ -->
    <Teleport to="body">
      <div v-if="folderModal" class="folder-modal-backdrop" @click.self="folderModal = null">
        <div class="folder-modal">
          <h4>{{ folderModal.mode === 'create' ? 'Создать папку' : 'Настройки папки' }}</h4>
          <p class="folder-modal__hint">Папка объединяет проекты и показывает сводную статистику. Папка занимает один проект в лимите тарифа, сколько бы проектов в ней ни было.</p>

          <label class="folder-modal__label">Название</label>
          <input v-model="folderForm.name" type="text" class="folder-modal__input" placeholder="Например: Лайк Стор" maxlength="80" />

          <label class="folder-modal__label">Цвет</label>
          <div
            class="folder-color-picker"
            :style="{
              '--folder-color': safeFolderColor,
              '--folder-palette-color': folderPaletteBaseColor,
              '--folder-hue': folderHsl.h,
              '--folder-saturation': `${folderHsl.s}%`,
              '--folder-lightness': `${folderHsl.l}%`,
            }"
          >
            <button
              ref="folderPaletteRef"
              type="button"
              class="folder-color-palette"
              aria-label="Палитра выбора цвета папки"
              @pointerdown="startFolderPalettePick"
            >
              <span
                class="folder-color-palette__marker"
                :style="{ left: `${folderHsl.s}%`, top: `${100 - folderHsl.l}%` }"
              ></span>
            </button>
            <div class="folder-color-picker__main">
              <span class="folder-color-picker__preview">
                <svg viewBox="0 0 20 18" fill="none" aria-hidden="true">
                  <path d="M2.35 3.25C2.35 2.28 3.13 1.5 4.1 1.5h3.27c.56 0 1.08.27 1.4.72l.67.95c.32.45.84.72 1.4.72h5.06c.97 0 1.75.78 1.75 1.75v8.26c0 .97-.78 1.75-1.75 1.75H4.1c-.97 0-1.75-.78-1.75-1.75V3.25Z" fill="currentColor" opacity=".18"/>
                  <path d="M2.35 6.05h15.3v7.85c0 .97-.78 1.75-1.75 1.75H4.1c-.97 0-1.75-.78-1.75-1.75V6.05Z" fill="currentColor" opacity=".34"/>
                  <path d="M2.35 5.62V3.25C2.35 2.28 3.13 1.5 4.1 1.5h3.27c.56 0 1.08.27 1.4.72l.67.95c.32.45.84.72 1.4.72h5.06c.97 0 1.75.78 1.75 1.75v8.26c0 .97-.78 1.75-1.75 1.75H4.1c-.97 0-1.75-.78-1.75-1.75V5.62Z" stroke="currentColor" stroke-width="1.45" stroke-linejoin="round"/>
                </svg>
              </span>
              <span class="folder-color-picker__copy">
                <strong>Цвет папки</strong>
                <small>Слишком светлые оттенки автоматически затемняются</small>
              </span>
              <span class="folder-color-picker__value">{{ safeFolderColor.toUpperCase() }}</span>
            </div>
            <div class="folder-color-sliders">
              <label class="folder-color-slider">
                <span>Тон</span>
                <input
                  class="folder-color-range folder-color-range--hue"
                  type="range"
                  min="0"
                  max="360"
                  :value="folderHsl.h"
                  @input="setFolderColorFromHsl({ h: Number($event.target.value) })"
                />
              </label>
            </div>
            <div class="folder-color-inputs">
              <label class="folder-color-picker__hex" aria-label="HEX цвет папки">
                <span>#</span>
                <input
                  v-model="folderHexDraft"
                  maxlength="6"
                  spellcheck="false"
                  @input="folderHexDraft = folderHexDraft.replace(/[^0-9a-fA-F]/g, '').slice(0, 6).toUpperCase()"
                  @blur="applyFolderHexDraft"
                />
              </label>
              <label class="folder-rgb-input" aria-label="Красный канал">
                <span>R</span>
                <input :value="folderRgb.r" inputmode="numeric" maxlength="3" @input="setFolderRgbChannel('r', $event.target.value)" />
              </label>
              <label class="folder-rgb-input" aria-label="Зелёный канал">
                <span>G</span>
                <input :value="folderRgb.g" inputmode="numeric" maxlength="3" @input="setFolderRgbChannel('g', $event.target.value)" />
              </label>
              <label class="folder-rgb-input" aria-label="Синий канал">
                <span>B</span>
                <input :value="folderRgb.b" inputmode="numeric" maxlength="3" @input="setFolderRgbChannel('b', $event.target.value)" />
              </label>
            </div>
          </div>

          <template v-if="freeProjects.length">
            <label class="folder-modal__label">
              {{ folderModal.mode === 'create' ? 'Добавить проекты' : 'Добавить проекты в папку' }}
              <small>(вне папок: {{ freeProjects.length }})</small>
            </label>
            <div class="folder-modal__projects">
              <label
                v-for="p in freeProjects"
                :key="p.id"
                class="folder-project-check"
                :class="{ 'folder-project-check--on': folderForm.project_ids.includes(p.id) }"
              >
                <input type="checkbox" :checked="folderForm.project_ids.includes(p.id)" @change="toggleFolderFormProject(p.id)" />
                <span class="fp-box"><svg viewBox="0 0 12 10" fill="none"><path d="M1 5.2 4.4 8.6 11 1.4" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"/></svg></span>
                <span class="fp-name">{{ p.name }}</span>
              </label>
            </div>
          </template>

          <div class="folder-modal__footer">
            <button
              v-if="folderModal.mode === 'edit'"
              type="button"
              class="folder-modal__delete"
              @click="folderDeleteTarget = folderModal.folder"
            >Удалить папку</button>
            <span class="flex-1"></span>
            <button type="button" class="folder-modal__cancel" @click="folderModal = null">Отмена</button>
            <button type="button" class="folder-modal__save" :disabled="folderSaving" @click="saveFolderModal">
              {{ folderSaving ? 'Сохраняем…' : (folderModal.mode === 'create' ? 'Создать папку' : 'Сохранить') }}
            </button>
          </div>
        </div>
      </div>

      <!-- Подтверждение удаления папки -->
      <div v-if="folderDeleteTarget" class="folder-modal-backdrop" @click.self="folderDeleteTarget = null">
        <div class="folder-modal folder-modal--confirm">
          <h4>Удалить папку «{{ folderDeleteTarget.name }}»?</h4>
          <p class="folder-modal__hint">
            <strong>Проекты сохранятся</strong> — они просто выйдут из папки и вернутся в общий список отдельными карточками. Удаление самих проектов — отдельное действие в настройках проекта.
          </p>
          <div class="folder-modal__footer">
            <span class="flex-1"></span>
            <button type="button" class="folder-modal__cancel" @click="folderDeleteTarget = null">Отмена</button>
            <button type="button" class="folder-modal__delete folder-modal__delete--solid" @click="confirmDeleteFolder">Удалить папку</button>
          </div>
        </div>
      </div>
    </Teleport>

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
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import api from '../../api/axios'
import { useProjects } from '../../composables/useProjects'
import { useToaster } from '../../composables/useToaster'
import { hasActiveProjectIntegration, hasProjectPlatform } from '../../utils/projectIntegrations'
import { relativeSyncLabel } from '../../utils/relativeTime'
import { getProjectPeriodLabel, getProjectPeriodRange, projectPeriodOptions } from '../../utils/projectPeriods'
import { projectAvatarUrl, projectInitials } from '../../utils/projectAvatar'
import DateRangePicker from '../../components/ui/DateRangePicker.vue'
import ProjectAvatarUploadModal from '../../components/ProjectAvatarUploadModal.vue'
import ProjectSettingsModal from '../../components/ProjectSettingsModal.vue'
import { useDetectorCrossProject } from '../../composables/useDetector'
import { useSyncStatus } from '../../composables/useSyncStatus'

const router = useRouter()
const route = useRoute()

// Сплит-кнопка хедера «Добавить → Папку» ведёт сюда с ?create=folder.
// Начальный query обрабатываем в onMounted: с immediate-watch openCreateFolder
// вызывался до инициализации folderModal (TDZ) и ломал setup при заходе извне.
const consumeCreateFolderFlag = () => {
  let flag = false
  try {
    flag = sessionStorage.getItem('admirra_create_folder') === '1'
    if (flag) sessionStorage.removeItem('admirra_create_folder')
  } catch { /* приватный режим */ }
  return flag
}
const openFolderFromQuery = () => {
  openCreateFolder()
  if (route.query.create) router.replace({ query: { ...route.query, create: undefined } })
}
watch(() => route.query.create, (val) => {
  if (val === 'folder') openFolderFromQuery()
})
onMounted(() => {
  if (route.query.create === 'folder' || consumeCreateFolderFlag()) openFolderFromQuery()
})
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

const projectFilter = ref('active')
const periodKey = ref('last_7_days')
const customPeriodRange = ref({ start: null, end: null })
const search = ref('')
const openSelect = ref(null)
const metricsByProjectId = ref({})
const projectInsightsById = ref({})
const expandedGoalsByProjectId = ref({})
let projectMetricsRequestId = 0
const PROJECT_INSIGHT_CONCURRENCY = 3

// ── Папки проектов ──
const folders = ref([])
const expandedFolders = ref({})
const folderModal = ref(null) // { mode: 'create' | 'edit', folder? }
const folderDeleteTarget = ref(null)
const moveMenuProjectId = ref(null)
const movingProjectId = ref(null)
const folderForm = ref({ name: '', color: '#2563eb', project_ids: [] })
const folderHexDraft = ref('2563EB')
const folderHsl = ref({ h: 217, s: 91, l: 55 })
const folderPaletteRef = ref(null)
const folderPaletteDragging = ref(false)
const folderSaving = ref(false)

const DEFAULT_FOLDER_COLOR = '#2563eb'
const MAX_FOLDER_LIGHTNESS = 76

const clamp = (value, min, max) => Math.min(max, Math.max(min, Number(value) || 0))

const normalizeFolderHex = (value) => {
  const raw = String(value || '').trim()
  const hex = raw.startsWith('#') ? raw : `#${raw}`
  if (/^#[0-9a-fA-F]{6}$/.test(hex)) return hex.toLowerCase()
  if (/^#[0-9a-fA-F]{3}$/.test(hex)) {
    return `#${hex[1]}${hex[1]}${hex[2]}${hex[2]}${hex[3]}${hex[3]}`.toLowerCase()
  }
  return DEFAULT_FOLDER_COLOR
}

const hexToRgb = (hex) => {
  const normalized = normalizeFolderHex(hex).replace('#', '')
  const value = Number.parseInt(normalized, 16)
  return {
    r: (value >> 16) & 255,
    g: (value >> 8) & 255,
    b: value & 255,
  }
}

const rgbToHex = ({ r, g, b }) =>
  `#${[r, g, b].map((part) => Math.round(clamp(part, 0, 255)).toString(16).padStart(2, '0')).join('')}`.toLowerCase()

const rgbToHsl = ({ r, g, b }) => {
  const nr = r / 255
  const ng = g / 255
  const nb = b / 255
  const max = Math.max(nr, ng, nb)
  const min = Math.min(nr, ng, nb)
  let h = 0
  let s = 0
  const l = (max + min) / 2
  if (max !== min) {
    const delta = max - min
    s = l > 0.5 ? delta / (2 - max - min) : delta / (max + min)
    if (max === nr) h = (ng - nb) / delta + (ng < nb ? 6 : 0)
    else if (max === ng) h = (nb - nr) / delta + 2
    else h = (nr - ng) / delta + 4
    h /= 6
  }
  return {
    h: Math.round(h * 360),
    s: Math.round(s * 100),
    l: Math.round(l * 100),
  }
}

const hslToRgb = ({ h, s, l }) => {
  const nh = ((Number(h) % 360) + 360) % 360 / 360
  const ns = clamp(s, 0, 100) / 100
  const nl = clamp(l, 0, 100) / 100
  if (ns === 0) {
    const gray = nl * 255
    return { r: gray, g: gray, b: gray }
  }
  const hue2rgb = (p, q, t) => {
    let nt = t
    if (nt < 0) nt += 1
    if (nt > 1) nt -= 1
    if (nt < 1 / 6) return p + (q - p) * 6 * nt
    if (nt < 1 / 2) return q
    if (nt < 2 / 3) return p + (q - p) * (2 / 3 - nt) * 6
    return p
  }
  const q = nl < 0.5 ? nl * (1 + ns) : nl + ns - nl * ns
  const p = 2 * nl - q
  return {
    r: hue2rgb(p, q, nh + 1 / 3) * 255,
    g: hue2rgb(p, q, nh) * 255,
    b: hue2rgb(p, q, nh - 1 / 3) * 255,
  }
}

const constrainFolderColor = (value) => {
  const hsl = rgbToHsl(hexToRgb(value))
  const next = {
    h: hsl.h,
    s: hsl.s,
    l: Math.min(hsl.l, MAX_FOLDER_LIGHTNESS),
  }
  if (next.s < 8 && next.l > 64) next.l = 64
  return rgbToHex(hslToRgb(next))
}

const syncFolderColorState = (value) => {
  const color = constrainFolderColor(value)
  folderForm.value.color = color
  folderHexDraft.value = color.replace('#', '').toUpperCase()
  folderHsl.value = rgbToHsl(hexToRgb(color))
}

const safeFolderColor = computed(() => constrainFolderColor(folderForm.value.color))
const folderRgb = computed(() => hexToRgb(safeFolderColor.value))
const folderPaletteBaseColor = computed(() => rgbToHex(hslToRgb({ h: folderHsl.value.h, s: 100, l: 50 })))
const setFolderColor = (value) => {
  syncFolderColorState(value)
}
const normalizeFolderColor = () => {
  syncFolderColorState(folderForm.value.color)
}
const setFolderColorFromHsl = (partial) => {
  const next = {
    ...folderHsl.value,
    ...partial,
  }
  next.h = Math.round(clamp(next.h, 0, 360))
  next.s = Math.round(clamp(next.s, 0, 100))
  next.l = Math.round(clamp(next.l, 18, MAX_FOLDER_LIGHTNESS))
  syncFolderColorState(rgbToHex(hslToRgb(next)))
}
const applyFolderHexDraft = () => {
  if (/^[0-9a-fA-F]{6}$/.test(folderHexDraft.value)) {
    syncFolderColorState(`#${folderHexDraft.value}`)
    return
  }
  syncFolderColorState(folderForm.value.color)
}
const setFolderRgbChannel = (channel, value) => {
  const rgb = { ...folderRgb.value }
  rgb[channel] = Math.round(clamp(String(value).replace(/\D/g, ''), 0, 255))
  syncFolderColorState(rgbToHex(rgb))
}
const pickFolderColorFromPalette = (event) => {
  const rect = folderPaletteRef.value?.getBoundingClientRect()
  if (!rect) return
  const x = clamp((event.clientX - rect.left) / rect.width, 0, 1)
  const y = clamp((event.clientY - rect.top) / rect.height, 0, 1)
  setFolderColorFromHsl({
    s: Math.round(x * 100),
    l: Math.round(MAX_FOLDER_LIGHTNESS - y * (MAX_FOLDER_LIGHTNESS - 18)),
  })
}
const stopFolderPalettePick = () => {
  folderPaletteDragging.value = false
  if (typeof window === 'undefined') return
  window.removeEventListener('pointermove', pickFolderColorFromPalette)
  window.removeEventListener('pointerup', stopFolderPalettePick)
  window.removeEventListener('pointercancel', stopFolderPalettePick)
}
const startFolderPalettePick = (event) => {
  event.preventDefault()
  folderPaletteDragging.value = true
  pickFolderColorFromPalette(event)
  if (typeof window === 'undefined') return
  window.addEventListener('pointermove', pickFolderColorFromPalette)
  window.addEventListener('pointerup', stopFolderPalettePick)
  window.addEventListener('pointercancel', stopFolderPalettePick)
}
onUnmounted(stopFolderPalettePick)
const periodTriggerRef = ref(null)
const periodPopoverRef = ref(null)
const periodOptions = projectPeriodOptions
const avatarProject = ref(null)
const settingsProject = ref(null)
const openSettingsFromQuery = () => {
  const id = String(route.query.settings || '')
  if (!id) return
  const project = projects.value.find((item) => String(item.id) === id)
  if (!project) return
  settingsProject.value = project
  router.replace({ query: { ...route.query, settings: undefined } })
}
watch(() => route.query.settings, () => openSettingsFromQuery())
const includeVat = ref(true)
const syncingIntegrations = ref(false)
const projectsSyncing = computed(() => syncingIntegrations.value || globalSyncingIntegrations.value.length > 0)

const isProjectPaused = (p) => String(p?.status || '').toLowerCase() === 'paused'
// Проект-организация: есть кабинет Яндекса, подключённый через приложение
// «AdMirra для организаций» (oauth_app='org'); порг-логин — запасной признак.
const isOrganizationProject = (p) => (p?.integrations || []).some((i) =>
  i?.oauth_app === 'org' || String(i?.account_id || '').toLowerCase().startsWith('porg-'),
)
// Счётчик считает карточки с паузой, включая проекты внутри папок (реком. ТЗ п.7)
const pausedProjectsCount = computed(() => projects.value.filter(isProjectPaused).length)
const projectFilterOptions = computed(() => [
  { value: 'all', label: 'Все' },
  { value: 'active', label: 'Активные' },
  { value: 'paused', label: `На паузе (${pausedProjectsCount.value})` },
])

const filteredProjects = computed(() => {
  let list = projects.value
  const q = search.value.trim().toLowerCase()
  if (q) {
    // ТЗ п.6: поиск игнорирует фильтр статусов и матчится шире плейсхолдера:
    // название, ID, описание/домен, название папки проекта
    const folderNameById = Object.fromEntries(folders.value.map((fl) => [fl.id, (fl.name || '').toLowerCase()]))
    list = list.filter((p) =>
      p.name?.toLowerCase().includes(q) ||
      String(p.display_id || '').toLowerCase().includes(q) ||
      String(p.id || '').toLowerCase().includes(q) ||
      p.description?.toLowerCase().includes(q) ||
      (p.folder_id && folderNameById[p.folder_id]?.includes(q))
    )
  } else if (projectFilter.value === 'active') {
    list = list.filter((p) => !isProjectPaused(p))
  } else if (projectFilter.value === 'paused') {
    list = list.filter(isProjectPaused)
  }
  return [...list].sort((a, b) => (a.name || '').localeCompare(b.name || '', 'ru'))
})

// ТЗ п.6: результат в папке — разворачиваем папку, чтобы карточка была видна
watch(search, (val) => {
  const q = String(val || '').trim().toLowerCase()
  if (!q) return
  for (const fl of folders.value) {
    const hasMatch = filteredProjects.value.some((p) => p.folder_id === fl.id)
    if (hasMatch) expandedFolders.value[fl.id] = true
  }
})

// ── Папки: дерево списка ──
const folderById = computed(() => Object.fromEntries(folders.value.map((f) => [f.id, f])))
const folderProjects = (folderId) => filteredProjects.value.filter((p) => p.folder_id === folderId)
const allFolderProjects = (folderId) => projects.value.filter((p) => p.folder_id === folderId)

const shouldDisplayFolder = (folder) => {
  if (projectFilter.value === 'paused') return false
  // В «Активных» не оставляем папки, внутри которых есть только проекты на
  // паузе. Пустая папка остаётся самостоятельной сущностью.
  return projectFilter.value !== 'active' || !allFolderProjects(folder.id).length || folderProjects(folder.id).length > 0
}

// Папка как «сущность карточки»: integrations собираются из вложенных проектов,
// поэтому существующие функции карточки (статы/каналы/балансы) работают без изменений —
// метрики папки лежат в тех же metricsByProjectId/projectInsightsById под folder.id.
const folderAsEntity = (folder) => ({
  ...folder,
  __isFolder: true,
  integrations: allFolderProjects(folder.id).flatMap((p) => p.integrations || []),
})

const isFolderPaused = (folder) => {
  const members = allFolderProjects(folder.id)
  return members.length > 0 && members.every((p) => String(p.status || '').toLowerCase() === 'paused')
}

// Корневой список: папки (по sort_order) + проекты вне папок. При поиске — плоские
// совпадения: проекты из папок показываются с подсветкой «в какой папке».
const displayItems = computed(() => {
  const q = search.value.trim().toLowerCase()
  const items = []
  if (q) {
    for (const f of folders.value) {
      if (f.name?.toLowerCase().includes(q)) items.push({ type: 'folder', folder: f })
    }
    for (const p of filteredProjects.value) {
      const folderName = p.folder_id ? folderById.value[p.folder_id]?.name : null
      items.push({ type: 'project', project: p, folderName })
    }
    return items
  }
  if (projectFilter.value === 'paused') {
    // Папка — не «проект на паузе». Паузы выводятся плоским списком, при этом
    // в карточке остаётся подпись исходной папки.
    for (const p of filteredProjects.value) {
      const folderName = p.folder_id ? folderById.value[p.folder_id]?.name : null
      items.push({ type: 'project', project: p, folderName })
    }
    return items
  }
  for (const f of [...folders.value].sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0))) {
    if (!shouldDisplayFolder(f)) continue
    items.push({ type: 'folder', folder: f })
    if (expandedFolders.value[f.id]) {
      for (const p of folderProjects(f.id)) {
        items.push({ type: 'project', project: p, inFolder: f })
      }
      if (!allFolderProjects(f.id).length) {
        items.push({ type: 'folder-empty', folder: f })
      }
    }
  }
  for (const p of filteredProjects.value.filter((p) => !p.folder_id || !folderById.value[p.folder_id])) {
    items.push({ type: 'project', project: p })
  }
  return items
})

const hasAnyItems = computed(() => displayItems.value.length > 0)

const toggleFolder = (folderId) => {
  expandedFolders.value = { ...expandedFolders.value, [folderId]: !expandedFolders.value[folderId] }
}

async function fetchFolders() {
  try {
    const { data } = await api.get('folders/')
    folders.value = data || []
  } catch {
    folders.value = []
  }
}

const branchNoun = (n) => {
  const v = Math.abs(Number(n || 0)); const l2 = v % 100; const l = v % 10
  if (l2 >= 11 && l2 <= 14) return 'проектов'
  if (l === 1) return 'проект'
  if (l >= 2 && l <= 4) return 'проекта'
  return 'проектов'
}

// ── Папки: создание/редактирование/удаление ──
// ТЗ п.7: дата «заморозки» данных = последняя синхронизация проекта
const projectFrozenDate = (project) => {
  const ts = (project.integrations || [])
    .map((i) => Date.parse(i.last_sync_at || ''))
    .filter(Number.isFinite)
  if (!ts.length) return ''
  return new Intl.DateTimeFormat('ru-RU', { timeZone: 'Europe/Moscow', day: '2-digit', month: '2-digit' }).format(new Date(Math.max(...ts)))
}

const resumingProjectId = ref(null)
async function resumeProject(project) {
  if (resumingProjectId.value) return
  resumingProjectId.value = project.id
  try {
    await api.put(`clients/${project.id}`, { status: 'active' })
    project.status = 'active'
    toaster.success(`Проект «${project.name}» возобновлён`)
  } catch (e) {
    toaster.error(e?.response?.data?.detail || 'Не удалось возобновить проект')
  } finally {
    resumingProjectId.value = null
  }
}

function openCreateFolder() {
  folderForm.value = { name: '', color: DEFAULT_FOLDER_COLOR, project_ids: [] }
  syncFolderColorState(DEFAULT_FOLDER_COLOR)
  folderModal.value = { mode: 'create' }
}

function openEditFolder(folder) {
  folderForm.value = { name: folder.name, color: normalizeFolderHex(folder.color || DEFAULT_FOLDER_COLOR), project_ids: [] }
  syncFolderColorState(folderForm.value.color)
  folderModal.value = { mode: 'edit', folder }
}

const freeProjects = computed(() => projects.value.filter((p) => !p.folder_id))

function toggleFolderFormProject(projectId) {
  const list = folderForm.value.project_ids
  const idx = list.indexOf(projectId)
  if (idx === -1) list.push(projectId)
  else list.splice(idx, 1)
}

async function saveFolderModal() {
  const name = (folderForm.value.name || '').trim()
  if (!name) { toaster.error('Укажите название папки'); return }
  const color = constrainFolderColor(folderForm.value.color)
  folderForm.value.color = color
  folderSaving.value = true
  try {
    if (folderModal.value?.mode === 'create') {
      await api.post('folders/', {
        name,
        color,
        project_ids: folderForm.value.project_ids,
      })
      toaster.success(`Папка «${name}» создана`)
    } else if (folderModal.value?.folder) {
      const folder = folderModal.value.folder
      await api.put(`folders/${folder.id}`, { name, color })
      if (folderForm.value.project_ids.length) {
        await api.post(`folders/${folder.id}/assign`, { project_ids: folderForm.value.project_ids })
      }
      toaster.success('Папка обновлена')
    }
    folderModal.value = null
    await Promise.all([fetchFolders(), fetchProjects()])
    await loadProjectMetrics()
  } catch (e) {
    const d = e?.response?.data?.detail
    toaster.error(typeof d === 'string' ? d : 'Не удалось сохранить папку')
  } finally {
    folderSaving.value = false
  }
}

async function confirmDeleteFolder() {
  const folder = folderDeleteTarget.value
  if (!folder) return
  try {
    await api.delete(`folders/${folder.id}`)
    toaster.success(`Папка «${folder.name}» удалена, проекты сохранены и возвращены в список`)
    folderDeleteTarget.value = null
    folderModal.value = null
    await Promise.all([fetchFolders(), fetchProjects()])
  } catch (e) {
    const d = e?.response?.data?.detail
    toaster.error(typeof d === 'string' ? d : 'Не удалось удалить папку')
  }
}

// ── Перемещение проекта в папку / из папки ──
async function moveProjectToFolder(project, folderId) {
  moveMenuProjectId.value = null
  if (movingProjectId.value) return
  const previousFolderId = project.folder_id || null
  movingProjectId.value = project.id
  project.folder_id = folderId || null
  if (folderId) {
    expandedFolders.value = { ...expandedFolders.value, [folderId]: true }
  }
  toaster.info(folderId ? 'Добавляем проект в папку…' : 'Выносим проект из папки…')
  try {
    if (folderId) {
      await api.post(`folders/${folderId}/assign`, { project_ids: [project.id] })
      toaster.success(`«${project.name}» перемещён в папку «${folderById.value[folderId]?.name || ''}»`)
    } else {
      await api.post('folders/unassign', { project_ids: [project.id] })
      toaster.success(`«${project.name}» вынесен из папки`)
    }
    await Promise.all([fetchFolders(), fetchProjects()])
    await loadProjectMetrics()
  } catch (e) {
    project.folder_id = previousFolderId
    const d = e?.response?.data?.detail
    toaster.error(typeof d === 'string' ? d : 'Не удалось переместить проект')
  } finally {
    movingProjectId.value = null
  }
}

const openFolderAnalytics = (folder) => {
  router.push({ path: '/dashboard/general-3', query: { folder_id: folder.id, folder_name: folder.name } })
}

const projectFilterLabel = computed(() => {
  return projectFilterOptions.value.find((option) => option.value === projectFilter.value)?.label || 'Все'
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

// ТЗ «Правки UI» п.5: в тулбаре — относительное время, полная дата — в тултипе.
// nowTick пересчитывает метку раз в минуту и при возврате фокуса на вкладку.
const nowTick = ref(Date.now())
let syncLabelTimer = null
const refreshNowTick = () => { nowTick.value = Date.now() }
onMounted(() => {
  syncLabelTimer = setInterval(refreshNowTick, 60 * 1000)
  document.addEventListener('visibilitychange', refreshNowTick)
})
onUnmounted(() => {
  if (syncLabelTimer) clearInterval(syncLabelTimer)
  document.removeEventListener('visibilitychange', refreshNowTick)
})

const projectSyncStatusText = computed(() => {
  if (projectsSyncing.value) return 'Выполняется синхронизация, пожалуйста подождите'
  const rel = relativeSyncLabel(lastProjectSyncAt.value, nowTick.value)
  return rel ? `Обновлено ${rel}` : ''
})

const projectSyncStatusTitle = computed(() => {
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
    avito: [],
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

const normalizeBalancePlatformCode = (value) => {
  const raw = String(value || '').trim().toUpperCase()
  if (!raw || raw.includes('METRIKA') || raw.includes('МЕТРИК')) return ''
  if (raw.includes('YANDEX') || raw.includes('DIRECT') || raw.includes('ЯНДЕКС') || raw.includes('ДИРЕКТ')) return 'yandex'
  if (raw.includes('VK') || raw.includes('ВК')) return 'vk'
  if (raw.includes('AVITO') || raw.includes('АВИТО')) return 'avito'
  return ''
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
      // ТЗ «Дельта по заявкам» §4/§7: пустота ≠ ноль. null = данных за прошлый
      // период нет — никаких `prev ?? 0`, чип дельты в этом случае не рендерится.
      prev_count: goal.prev_count == null ? null : Number(goal.prev_count),
      trend: Number(goal.trend || 0),
      hasCost,
      cost,
      cpl: hasCost && count > 0 ? cost / count : null,
      // Для VK бэкенд явно помечает действия, выбранные агентством для
      // расчёта заявок/CPL. Не выбранные типы по-прежнему доступны в развороте,
      // но не должны искажать итог на карточке.
      summable: goal.summable !== false,
      syncing: Boolean(goal.syncing),
      missingInMetrika: Boolean(goal.missing_in_metrika),
    }
  })

// Сумма prev по целям: null, только если НИ У ОДНОЙ цели нет данных за P′
// (бэк отдаёт null на весь канал при отсутствии покрытия статистикой).
const sumPrevCounts = (goals = []) => {
  const known = goals.map((goal) => goal.prev_count).filter((value) => value != null)
  if (!known.length) return null
  return known.reduce((sum, value) => sum + Number(value || 0), 0)
}

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

const vkGoalSelectionTooltip = (selectedGoals) => {
  if (!selectedGoals.length) return 'Выберите действия, которые нужно считать заявками. Пока они не выбраны, общий CPL для VK не рассчитывается.'
  return `В заявках и общем CPL учитываются: ${selectedGoals.map((goal) => goal.name).join(', ')}.`
}

const topGoalSummary = (goals, platformCode, expenses) => {
  const countedGoals = goals.filter((goal) => goal.summable !== false)
  if (countedGoals.some((goal) => goal.syncing)) {
    return {
      total: 0,
      noun: 'заявок',
      avgCpl: null,
      text: 'цели синхронизируются',
    }
  }
  const total = countedGoals.reduce((sum, goal) => sum + Number(goal.count || 0), 0)
  const noun = goalNoun(total)
  // VK Ads: расход площадки и число действий, отмеченных агентством как
  // заявки. Для невыбранных типов (охват, трафик и т.п.) CPL не считаем.
  const avgCpl = total > 0 ? Number(expenses || 0) / total : null
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

const metricLeadExpenses = (metric, platformCode) => {
  const breakdown = metric?.lead_cost_by_platform
  return (breakdown && breakdown[platformCode] != null)
    ? Number(breakdown[platformCode])
    : Number(metric?.expenses || 0)
}

const projectChannelSummaries = (project) => {
  if (project.__isFolder) return folderChannelSummaries(project)
  const insights = getProjectInsights(project.id)
  return projectPlatformCards(project).map((platform) => {
    const metric = insights[platform.code] || emptyMetric()
    const goals = normalizeGoalRows(insights.goals?.[platform.code] || [])
    // CPL — от лидового расхода канала (ТЗ VK п.3): для VK берём расход лидовых
    // кампаний (lead_cost_by_platform), а не весь расход канала.
    const leadExpenses = metricLeadExpenses(metric, platform.code)
    const summary = topGoalSummary(goals, platform.code, leadExpenses)
    // ТЗ «Дельта по заявкам» §4: prev = null (нет данных за P′) → дельты нет.
    // База сравнения — предыдущий сопоставимый период, его считает бэк (§6).
    const prevLeadExpenses = metricLeadExpenses(metric.prev, platform.code)
    const countedGoals = goals.filter((goal) => goal.summable !== false)
    const isVk = platform.code === 'vk'
    const prevTotal = sumPrevCounts(countedGoals)
    const leadsDelta = prevTotal == null ? null : summary.total - prevTotal
    // CPL канала считается как расход/цели — та же формула для прошлого периода.
    // §6: cpl_prev = null при leads_prev ∈ {0, null} — деление на ноль не маскируем.
    const prevAvgCpl = (prevTotal != null && prevTotal > 0)
      ? prevLeadExpenses / prevTotal
      : null
    let cplDeltaPct = null
    if (summary.avgCpl !== null && summary.avgCpl > 0 && prevAvgCpl !== null && prevAvgCpl > 0) {
      cplDeltaPct = Math.round(((summary.avgCpl - prevAvgCpl) / prevAvgCpl) * 100)
    }
    return {
      ...platform,
      expenses: Number(metric.expenses || 0),
      goals,
      goalTotal: summary.total,
      goalNoun: summary.noun,
      goalLabel: isVk ? (countedGoals.length ? 'Заявки · по выбранным' : 'Выберите действия') : capitalizeFirst(summary.noun),
      goalSelectionTooltip: isVk ? vkGoalSelectionTooltip(countedGoals) : '',
      needsGoalSelection: isVk && goals.length > 0 && countedGoals.length === 0,
      avgCpl: summary.avgCpl,
      summaryText: summary.text,
      prevGoalTotal: prevTotal,
      leadsDelta,
      cplDeltaPct,
    }
  })
}

const folderChannelSummaries = (folder) => {
  const members = allFolderProjects(folder.id)
  return projectPlatformCards(folder).map((platform) => {
    const goalMap = new Map()
    let expenses = 0
    let leadExpenses = 0
    let prevLeadExpenses = 0

    for (const member of members) {
      const insights = getProjectInsights(member.id)
      const metric = insights[platform.code] || emptyMetric()
      expenses += Number(metric.expenses || 0)
      leadExpenses += metricLeadExpenses(metric, platform.code)
      prevLeadExpenses += metricLeadExpenses(metric.prev, platform.code)

      for (const goal of normalizeGoalRows(insights.goals?.[platform.code] || [])) {
        // В одной папке у разных проектов один и тот же тип VK-действия может
        // быть выбран как заявка только в части интеграций. Не смешиваем такие
        // строки, иначе невыбранные действия попадут в суммарный CPL.
        const key = `${String(goal.id || goal.name || 'goal')}:${goal.summable !== false ? 'selected' : 'other'}`
        const current = goalMap.get(key) || {
          ...goal,
          count: 0,
          prev_count: null,
          cost: goal.hasCost ? 0 : null,
          syncing: false,
          missingInMetrika: false,
        }
        current.count += Number(goal.count || 0)
        // null + null = null (нет данных ни у одного проекта папки);
        // число + null = число (частичное покрытие — суммируем известное)
        if (goal.prev_count != null) {
          current.prev_count = Number(current.prev_count || 0) + Number(goal.prev_count)
        }
        current.syncing = current.syncing || Boolean(goal.syncing)
        current.missingInMetrika = current.missingInMetrika || Boolean(goal.missingInMetrika)
        if (goal.hasCost) current.cost = Number(current.cost || 0) + Number(goal.cost || 0)
        current.cpl = current.hasCost && current.count > 0 ? Number(current.cost || 0) / current.count : null
        goalMap.set(key, current)
      }
    }

    const goals = Array.from(goalMap.values())
    const countedGoals = goals.filter((goal) => goal.summable !== false)
    const goalTotal = countedGoals.reduce((sum, goal) => sum + Number(goal.count || 0), 0)
    const isVk = platform.code === 'vk'
    // §4: null, если данных за P′ нет ни по одной цели папки
    const prevGoalTotal = sumPrevCounts(countedGoals)
    const goalNounValue = goalNoun(goalTotal)
    const avgCpl = goalTotal > 0 ? leadExpenses / goalTotal : null
    const prevAvgCpl = prevGoalTotal != null && prevGoalTotal > 0 ? prevLeadExpenses / prevGoalTotal : null
    let cplDeltaPct = null
    if (avgCpl !== null && avgCpl > 0 && prevAvgCpl !== null && prevAvgCpl > 0) {
      cplDeltaPct = Math.round(((avgCpl - prevAvgCpl) / prevAvgCpl) * 100)
    }

    return {
      ...platform,
      expenses,
      goals,
      goalTotal,
      goalNoun: goalNounValue,
      goalLabel: isVk ? (countedGoals.length ? 'Заявки · по выбранным' : 'Выберите действия') : capitalizeFirst(goalNounValue),
      goalSelectionTooltip: isVk ? vkGoalSelectionTooltip(countedGoals) : '',
      needsGoalSelection: isVk && goals.length > 0 && countedGoals.length === 0,
      avgCpl,
      summaryText: avgCpl
        ? `${formatNumber(goalTotal)} ${goalNounValue} · CPL ${formatMoney(withChannelVat(avgCpl, platform.code))}`
        : (goalTotal ? `${formatNumber(goalTotal)} ${goalNounValue}` : 'нет целей за период'),
      prevGoalTotal,
      leadsDelta: prevGoalTotal == null ? null : goalTotal - prevGoalTotal,
      cplDeltaPct,
    }
  })
}

// ТЗ «Дельта по заявкам» §5: тултип чипа — «за период: N, за предыдущий: M»,
// при prev = 0 — «0 → N», для неполных пресетов — пометка «сравнение к дате».
const INCOMPLETE_PERIOD_PRESETS = new Set(['today', 'this_week', 'this_month'])

const deltaTooltip = (cur, prev) => {
  const toDate = INCOMPLETE_PERIOD_PRESETS.has(periodKey.value) ? ' · сравнение к дате' : ''
  if (prev === 0) return `0 → ${formatNumber(cur)} за период${toDate}`
  return `За период: ${formatNumber(cur)} · за предыдущий: ${formatNumber(prev)}${toDate}`
}

// ТЗ «Дельта по заявкам» §4: prev=null → чипа нет (пустота ≠ ноль);
// Δ=0 — без пилюли (консистентно с остальными чипами); prev=0 → честный «+N» с тултипом «0 → N»
const goalCountDelta = (goal) => {
  const prev = goal.prev_count
  if (prev == null) return null
  const cur = Number(goal.count || 0)
  const d = cur - Number(prev)
  if (d === 0) return null
  return {
    text: d > 0 ? `+${formatNumber(d)}` : `−${formatNumber(Math.abs(d))}`,
    dir: d > 0 ? 'up' : 'down',
    cls: d > 0 ? 'channel-delta--up' : 'channel-delta--down',
    title: deltaTooltip(cur, Number(prev)),
  }
}

const leadsDeltaBadge = (channel) => {
  if (channel.prevGoalTotal == null || channel.leadsDelta == null) return null
  const d = Number(channel.leadsDelta || 0)
  if (d === 0) return null
  return {
    text: d > 0 ? `+${formatNumber(d)}` : `−${formatNumber(Math.abs(d))}`,
    dir: d > 0 ? 'up' : 'down',
    cls: d > 0 ? 'channel-delta--up' : 'channel-delta--down',
    title: deltaTooltip(Number(channel.goalTotal || 0), Number(channel.prevGoalTotal)),
  }
}

// CPL: окраска инвертирована — снизился (лучше) = зелёный, вырос = красный.
// Стрелка (dir) показывает фактическое движение, цвет (cls) — хорошо/плохо.
const cplDeltaBadge = (channel) => {
  const pct = channel.cplDeltaPct
  if (pct === null || pct === undefined || pct === 0) return null
  return {
    text: pct > 0 ? `+${pct}%` : `${pct}%`,
    dir: pct > 0 ? 'up' : 'down',
    cls: pct < 0 ? 'channel-delta--up' : 'channel-delta--down',
  }
}

const projectBalances = (project) => {
  if (project.__isFolder) {
    const balancesByPlatform = new Map()
    for (const integration of project.integrations || []) {
      if (integration?.is_connected === false || integration?.connected === false) continue
      const code = normalizeBalancePlatformCode(integration.platform || integration.type || integration.name || integration.provider || integration.channel)
      const platform = platformConfig[code]
      if (!platform) continue
      const rawBalance = integration.balance === null || integration.balance === undefined ? 0 : Number(integration.balance)
      const amount = Number.isFinite(rawBalance) ? rawBalance : 0
      balancesByPlatform.set(code, (balancesByPlatform.get(code) || 0) + amount)
    }

    return projectPlatformCards(project).map((platform) => ({
      ...platform,
      name: platform.balanceName,
      value: formatMoney(withChannelVat(balancesByPlatform.get(platform.code) || 0, platform.code)),
    }))
  }

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
  const requestId = ++projectMetricsRequestId
  const { startDate, endDate } = getProjectPeriodRange(periodKey.value, customPeriodRange.value)
  const entries = [
    ...projects.value.map((project) => ({ id: project.id, projectId: project.id })),
    // Сводки папок: те же инсайты, но со скоупом folder_id — лежат под folder.id,
    // поэтому карточка папки использует те же функции, что и карточка проекта.
    ...folders.value.map((folder) => ({ id: folder.id, folderId: folder.id })),
  ]

  // Раньше при 17 проектах браузер отправлял 119 запросов одновременно
  // (7 на карточку) и заполнял интерфейс только после самого последнего.
  // Теперь карточки получают данные по мере готовности, а бэкенд получает
  // ограниченный поток запросов вместо лавины.
  let nextIndex = 0
  const loadNext = async () => {
    while (nextIndex < entries.length) {
      const entry = entries[nextIndex]
      nextIndex += 1
      let data
      try {
        data = await loadProjectInsight(entry.projectId || null, startDate, endDate, entry.folderId || null, periodKey.value)
      } catch {
        data = emptyProjectInsights()
      }
      if (requestId !== projectMetricsRequestId) return
      projectInsightsById.value = { ...projectInsightsById.value, [entry.id]: data }
      metricsByProjectId.value = { ...metricsByProjectId.value, [entry.id]: data.all || emptyMetric() }
    }
  }

  await Promise.all(Array.from(
    { length: Math.min(PROJECT_INSIGHT_CONCURRENCY, entries.length) },
    () => loadNext(),
  ))
}

const loadProjectInsight = async (projectId, startDate, endDate, folderId = null, periodPreset = null) => {
  // Скоуп: конкретный проект (client_id) или папка (folder_id — сводка по вложенным)
  const scope = folderId ? { folder_id: folderId } : { client_id: projectId }
  const summaryParams = (platform) => ({
    ...scope,
    platform,
    start_date: startDate,
    end_date: endDate,
  })
  // period_preset задаёт бэку базу сравнения дельты (ТЗ «Дельта по заявкам» §3):
  // «эта неделя/этот месяц» сравниваются «к дате», а не встык.
  const goalParams = (platform) => ({
    ...scope,
    platform,
    date_from: startDate,
    date_to: endDate,
    ...(periodPreset ? { period_preset: periodPreset } : {}),
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

async function handleProjectDeleted(projectId) {
  projects.value = projects.value.filter((p) => p.id !== projectId)
  settingsProject.value = null
  // Проект мог лежать в папке: без обновления папок карточка покажет устаревшее
  // «N проектов» и старую сводную статистику/KPI (балансы и каналы самопочинятся,
  // т.к. считаются из projects.value, а вот projects_count и метрики папки под
  // folder.id — с бэка, поэтому перезагружаем их как в остальных хендлерах папок).
  await Promise.all([fetchFolders(), fetchProjects()])
  await loadProjectMetrics()
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

// ТЗ «Детектор ит.2» п.2.4: поповер-превью на пилюле кросс-обзора — только чтение
const detectorPreviewId = ref(null)
const toggleDetectorPreview = (projectId) => {
  detectorPreviewId.value = detectorPreviewId.value === projectId ? null : projectId
}
const closeDetectorPreview = (event) => {
  if (!detectorPreviewId.value) return
  if (event.target.closest && event.target.closest('.detector-preview-wrap')) return
  detectorPreviewId.value = null
}
onMounted(() => document.addEventListener('mousedown', closeDetectorPreview))
onUnmounted(() => document.removeEventListener('mousedown', closeDetectorPreview))

const detectorPreview = (project) => getProjectStatus(project.id)?.top_alerts || []
const detectorAlertChecks = (alert) => {
  const labels = {
    'P-1': 'Темп расхода',
    'P-2': 'Стоимость заявки',
    'P-3': 'Темп заявок',
  }
  return (alert?.checks || []).map((check) => labels[check]).filter(Boolean)
}
const detectorPreviewMore = (project) => {
  const status = getProjectStatus(project.id)
  if (!status) return 0
  const total = (status.warning_count || 0) + (status.problem_count || 0)
  return Math.max(0, total - (status.top_alerts?.length || 0))
}
const askAiFromPreview = (project) => {
  const top = detectorPreview(project)[0]
  try {
    if (top?.id) sessionStorage.setItem('admirra_ai_alert', String(top.id))
  } catch { /* приватный режим */ }
  openProject(project)
}

const detectorBadge = (project) => {
  const status = getProjectStatus(project.id)
  if (!status) return null
  if (status.warmup_status === 'paused' || status.warmup_status === 'disabled') return null
  if (status.sync_issue_count) return { type: 'sync', text: 'Нет свежих данных', interactive: false }
  if (status.warmup_status === 'warming_up') return { type: 'warmup', text: 'Детектор накапливает данные', interactive: false }
  const total = (status.warning_count || 0) + (status.problem_count || 0)
  const hidden = status.hidden_count || 0
  if (!total && !hidden) return null
  if (!total && hidden) return {
    type: 'muted',
    text: `Скрыто ${hidden} ${hidden === 1 ? 'отклонение' : hidden < 5 ? 'отклонения' : 'отклонений'}`,
    count: hidden,
    interactive: true,
  }
  return {
    type: status.max_severity || 'warning',
    text: `${total} ${total === 1 ? 'отклонение' : total < 5 ? 'отклонения' : 'отклонений'}${hidden ? ` · скрыто ${hidden}` : ''}`,
    count: total,
    interactive: true,
  }
}

onMounted(async () => {
  await Promise.all([fetchProjects({ preferCache: true }), fetchFolders()])
  openSettingsFromQuery()
  // Не задерживаем отрисовку страницы ожиданием статистики всех карточек:
  // видимые данные подгружаются последовательно, а структура уже интерактивна.
  void loadProjectMetrics()
  void fetchCrossProject()
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
  /* ТЗ «Правки UI» п.11: у контролов, где значение есть всегда, текст — основной тёмный */
  color: #171717;
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

/* «Обновить данные» — как капсула на дашборде (белая, с рамкой). */
.tile-sync-btn {
  gap: 0.6rem;
  padding: 0 1.0417rem;
  border: 1px solid #ebebeb;
  border-radius: 0.8333rem;
  background: #fff;
  color: #171717;
  cursor: pointer;
  font-size: 0.9028rem;
  font-weight: 500;
  transition: border-color 0.2s, box-shadow 0.2s, background 0.2s, color 0.2s;
}

.tile-sync-btn:hover:not(:disabled) {
  border-color: #c9d3e6;
  box-shadow: 0 0.2rem 0.7rem rgba(37, 99, 235, 0.1);
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
  color: #767676;
  cursor: default;
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
  grid-template-columns: 2.2222rem minmax(8.5rem, 0.85fr) minmax(22.75rem, 1fr);
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
  grid-template-columns: minmax(6.75rem, 0.9fr) minmax(7.75rem, 1.05fr) minmax(8.25rem, 1.15fr);
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
  color: #171717;
  font-size: clamp(0.9rem, 1.25vw, 1.1111rem);
  font-weight: 800;
  line-height: 1.05;
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
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
    min-width: 0;
    border-top: 1px solid rgba(245, 158, 11, 0.13);
    border-left: 0;
    padding-top: 0.5556rem;
  }

  .project-channel-metric:first-child {
    border-left: 0;
  }

  .project-channel-metric--spend {
    grid-column: 1 / -1;
    border-top: 1px solid rgba(245, 158, 11, 0.13);
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
  color: rgba(255, 255, 255, 0.72);
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.1);
}

:global(.dark) .tile-sync-btn:hover:not(:disabled),
:global(.darkmode) .tile-sync-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.18);
  color: rgba(255, 255, 255, 0.9);
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

/* ══════════ Папки проектов ══════════ */
/* Folder card should read as a container at a glance, while staying the same visual weight as project cards. */
.folder-card {
  position: relative;
  overflow: visible;
  margin-top: 0.7rem;
  border: 1px solid color-mix(in srgb, var(--folder-color, #2563eb) 24%, rgba(15, 23, 42, 0.08));
  background:
    linear-gradient(180deg, color-mix(in srgb, var(--folder-color, #2563eb) 4%, #fff) 0%, #fff 42%),
    #fff;
  box-shadow:
    0 1px 0 rgba(15, 23, 42, 0.02),
    inset 0 0 0 1px color-mix(in srgb, var(--folder-color, #2563eb) 8%, transparent);
}

.folder-card::before {
  content: '';
  position: absolute;
  inset: 0.55rem 0.55rem auto auto;
  width: 5.8rem;
  height: 3.1rem;
  border-radius: 0.9rem;
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--folder-color, #2563eb) 13%, transparent), transparent 72%);
  opacity: 0.8;
  pointer-events: none;
}

.folder-card::after {
  content: '';
  position: absolute;
  left: 1.25rem;
  right: 1.25rem;
  bottom: -0.28rem;
  height: 0.28rem;
  border-radius: 0 0 0.8rem 0.8rem;
  background: color-mix(in srgb, var(--folder-color, #2563eb) 24%, transparent);
  opacity: 0;
  transform: translateY(-0.15rem);
  transition: opacity 0.16s ease, transform 0.16s ease;
  pointer-events: none;
}

.folder-card--expanded {
  border-color: color-mix(in srgb, var(--folder-color, #2563eb) 42%, rgba(15, 23, 42, 0.08));
  box-shadow:
    0 10px 26px rgba(37, 99, 235, 0.07),
    inset 0 0 0 1px color-mix(in srgb, var(--folder-color, #2563eb) 18%, transparent);
}

.folder-card--expanded::after {
  opacity: 1;
  transform: translateY(0);
}

.folder-card__tab {
  position: absolute;
  left: 1.22rem;
  top: -0.7rem;
  z-index: 0;
  width: min(10.2rem, 38%);
  height: 1.15rem;
  border: 1px solid color-mix(in srgb, var(--folder-color, #2563eb) 23%, rgba(15, 23, 42, 0.04));
  border-bottom: 0;
  border-radius: 0.72rem 1.15rem 0 0;
  background:
    linear-gradient(180deg, color-mix(in srgb, var(--folder-color, #2563eb) 14%, #fff), color-mix(in srgb, var(--folder-color, #2563eb) 7%, #fff));
  box-shadow: 0 -1px 0 rgba(255, 255, 255, 0.9) inset;
  pointer-events: none;
}

.folder-card__tab span {
  position: absolute;
  left: 0.72rem;
  right: 1.55rem;
  top: 0.38rem;
  height: 0.18rem;
  border-radius: 99rem;
  background: color-mix(in srgb, var(--folder-color, #2563eb) 34%, transparent);
  opacity: 0.45;
}

.folder-card__header {
  position: relative;
  z-index: 1;
  min-height: 5.65rem;
  margin: -1.7361rem -1.7361rem 1.15rem;
  padding: 1.35rem 1.7361rem 1.1rem;
  border-radius: 1.0417rem 1.0417rem 0 0;
  border-bottom: 1px solid color-mix(in srgb, var(--folder-color, #2563eb) 14%, rgba(15, 23, 42, 0.06));
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--folder-color, #2563eb) 12%, #fff) 0%, #fff 78%),
    #fff;
}

.folder-card__header::after {
  content: '';
  position: absolute;
  left: 1.7361rem;
  right: 1.7361rem;
  bottom: -1px;
  height: 2px;
  border-radius: 99rem;
  background: color-mix(in srgb, var(--folder-color, #2563eb) 36%, transparent);
  opacity: 0.5;
}

.folder-card--paused .project-tile-stats-wrap,
.folder-card--paused .project-goals-section {
  opacity: 0.55;
}

.folder-avatar {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 3.25rem !important;
  height: 3.25rem !important;
  cursor: default;
  border-radius: 0.92rem !important;
  box-shadow:
    0 0 0 0.28rem rgba(255, 255, 255, 0.78),
    0 0.5rem 1.1rem color-mix(in srgb, var(--folder-color, #2563eb) 24%, transparent);
}

.folder-type-label {
  display: inline-flex;
  align-items: center;
  color: #6b7280;
  font-size: 0.72rem;
  font-weight: 600;
}

.folder-member-cloud {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.32rem;
  min-width: 2.55rem;
  height: 2rem;
  padding: 0 0.62rem;
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 0.5rem;
  background: #fff;
  color: #696969;
  font-size: 0.82rem;
  font-weight: 900;
  box-shadow: 0 0.35rem 1rem rgba(15, 23, 42, 0.05);
  cursor: pointer;
  transition: border-color 0.14s ease, background 0.14s ease, color 0.14s ease;
}
.folder-member-cloud:hover {
  border-color: rgba(37, 99, 235, 0.28);
  background: rgba(37, 99, 235, 0.04);
  color: #2563eb;
  box-shadow: 0 0.3472rem 1.0417rem rgba(37, 99, 235, 0.08);
}
.folder-member-cloud--open {
  background: rgba(15, 23, 42, 0.04);
  border-color: rgba(15, 23, 42, 0.14);
  color: #696969;
}
.folder-member-cloud__chevron { transition: transform 0.18s ease; }
.folder-member-cloud__chevron--open { transform: rotate(180deg); }

/* ТЗ п.7: карточка на паузе — приглушение + бейдж + строка вместо нулевых KPI */
.detector-preview-wrap { position: relative; display: inline-flex; }
.detector-badge--pill {
  display: inline-flex;
  align-items: center;
  gap: 0.28rem;
  border: none;
  cursor: pointer;
  border-radius: 999px;
  padding: 0.18rem 0.55rem;
  font-weight: 800;
}
.detector-badge--pill:disabled { cursor: default; }
.detector-badge--sync,
.detector-badge--muted {
  background: #f4f6f9;
  color: #6b7280;
  border: 1px solid #dce3ed;
}
.detector-preview {
  position: absolute;
  top: calc(100% + 0.55rem);
  right: 0;
  z-index: 40;
  width: 22rem;
  max-width: min(22rem, 86vw);
  background: #fff;
  border-radius: 1rem;
  padding: 0.85rem;
  box-shadow: 0 18px 48px rgba(9, 24, 63, 0.2), 0 0 0 1px rgba(15, 23, 42, 0.06);
  cursor: default;
}
.detector-preview__row {
  display: flex;
  gap: 0.55rem;
  align-items: flex-start;
  padding: 0.55rem 0.6rem;
  border-radius: 0.65rem;
  background: rgba(245, 158, 11, 0.08);
}
.detector-preview__row + .detector-preview__row { margin-top: 0.4rem; }
.detector-preview__row--problem { background: rgba(239, 68, 68, 0.08); }
.detector-preview__dot {
  width: 0.55rem; height: 0.55rem; border-radius: 50%;
  margin-top: 0.42rem; flex-shrink: 0;
  background: #f59e0b;
}
.detector-preview__row--problem .detector-preview__dot { background: #ef4444; }
.detector-preview__text {
  display: block;
  font-size: 0.83rem;
  line-height: 1.45;
  color: #1f2937;
  font-weight: 600;
}
.detector-preview__copy { min-width: 0; }
.detector-preview__checks {
  display: block;
  margin-bottom: 0.22rem;
  color: #7c2d12;
  font-size: 0.7rem;
  font-weight: 850;
  line-height: 1.2;
  text-transform: uppercase;
}
.detector-preview__more { font-size: 0.77rem; color: #94a3b8; font-weight: 600; padding: 0.5rem 0.25rem 0.15rem; }
.detector-preview__actions { display: flex; gap: 0.5rem; margin-top: 0.75rem; }
.detector-preview__actions button {
  flex: 1;
  height: 2.25rem;
  border: 1px solid rgba(15, 23, 42, 0.12);
  background: #fff;
  border-radius: 0.6rem;
  padding: 0 0.65rem;
  font-size: 0.79rem;
  font-weight: 700;
  color: #171717;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: border-color 0.14s ease, background 0.14s ease;
}
.detector-preview__actions button:hover { border-color: rgba(37, 99, 235, 0.4); background: rgba(37, 99, 235, 0.04); }
.detector-preview__ai { background: #2563eb !important; border-color: #2563eb !important; color: #fff !important; }
.detector-preview__ai:hover { background: #1d4ed8 !important; }

:global(.dark) .detector-preview,
:global(.darkmode) .detector-preview {
  background: #202632;
  box-shadow: 0 18px 48px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.08);
}
:global(.dark) .detector-preview__text,
:global(.darkmode) .detector-preview__text { color: #e5e7eb; }
:global(.dark) .detector-preview__row,
:global(.darkmode) .detector-preview__row { background: rgba(245, 158, 11, 0.14); }
:global(.dark) .detector-preview__row--problem,
:global(.darkmode) .detector-preview__row--problem { background: rgba(239, 68, 68, 0.14); }
:global(.dark) .detector-preview__actions button,
:global(.darkmode) .detector-preview__actions button {
  background: rgba(255, 255, 255, 0.05);
  color: #e5e7eb;
  border-color: rgba(255, 255, 255, 0.12);
}
:global(.dark) .detector-preview__ai,
:global(.darkmode) .detector-preview__ai { color: #fff !important; }

.channel-delta {
  display: inline-flex;
  align-items: center;
  gap: 0.12rem;
  margin-left: 0.3rem;
  padding: 0.08rem 0.4rem;
  border-radius: 999px;
  font-size: 0.62rem;
  font-weight: 700;
  font-style: normal;
  vertical-align: middle;
  white-space: nowrap;
}
.channel-delta__arrow { transition: transform 0.18s ease; }
.channel-delta__arrow--down { transform: rotate(180deg); }
.channel-delta--up { background: rgba(34, 197, 94, 0.12); color: #15803d; }
.channel-delta--down { background: rgba(239, 68, 68, 0.1); color: #b91c1c; }

.paused-badge {
  display: inline-flex;
  align-items: center;
  margin-left: 0.45rem;
  padding: 0.14rem 0.55rem;
  border-radius: 999px;
  background: #fef3c7;
  color: #b45309;
  font-size: 0.66rem;
  font-weight: 700;
  vertical-align: middle;
  white-space: nowrap;
}
.project-card--paused {
  background: #fafbfc;
}
.project-card--paused .project-avatar {
  filter: grayscale(0.55);
  opacity: 0.8;
}
.project-card--paused .project-tile-description {
  opacity: 0.75;
}
.project-paused-block {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-top: 0.3rem;
  padding: 1rem 1.15rem;
  border: 1px dashed rgba(180, 83, 9, 0.35);
  border-radius: 0.85rem;
  background: rgba(254, 243, 199, 0.35);
}
.project-paused-block__text {
  color: #92600a;
  font-size: 0.82rem;
  font-weight: 600;
  margin: 0;
}
.project-paused-block__resume {
  border: none;
  background: #2563eb;
  color: #fff;
  padding: 0.5rem 1rem;
  border-radius: 0.65rem;
  font-size: 0.8rem;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.13s ease;
}
.project-paused-block__resume:hover:not(:disabled) { background: #1d4ed8; }
.project-paused-block__resume:disabled { opacity: 0.6; cursor: default; }

.folder-count-badge {
  display: inline-block;
  padding: 0.1rem 0.45rem;
  border-radius: 99rem;
  background: color-mix(in srgb, var(--folder-color, #2563eb) 14%, transparent);
  color: var(--folder-color, #2563eb);
  font-size: 0.72rem;
  font-weight: 800;
}

.folder-paused-note { color: #b45309; font-weight: 600; }
.folder-summary-note { color: rgba(105, 105, 105, 0.6); }

:global(.dark) .folder-card,
:global(.darkmode) .folder-card {
  border-color: color-mix(in srgb, var(--folder-color, #2563eb) 34%, rgba(255, 255, 255, 0.1));
  background:
    linear-gradient(180deg, color-mix(in srgb, var(--folder-color, #2563eb) 13%, #202632) 0%, #202632 46%),
    #202632;
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.02),
    inset 0 0 0 1px color-mix(in srgb, var(--folder-color, #2563eb) 16%, transparent);
}

:global(.dark) .folder-card::before,
:global(.darkmode) .folder-card::before {
  background: linear-gradient(135deg, color-mix(in srgb, var(--folder-color, #2563eb) 20%, transparent), transparent 72%);
}

:global(.dark) .folder-card__tab,
:global(.darkmode) .folder-card__tab {
  border-color: color-mix(in srgb, var(--folder-color, #2563eb) 36%, rgba(255, 255, 255, 0.08));
  background:
    linear-gradient(180deg, color-mix(in srgb, var(--folder-color, #2563eb) 26%, #202632), color-mix(in srgb, var(--folder-color, #2563eb) 14%, #202632));
  box-shadow: none;
}

:global(.dark) .folder-card__header,
:global(.darkmode) .folder-card__header {
  border-bottom-color: color-mix(in srgb, var(--folder-color, #2563eb) 26%, rgba(255, 255, 255, 0.08));
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--folder-color, #2563eb) 20%, #202632) 0%, #202632 80%),
    #202632;
}

:global(.dark) .folder-avatar,
:global(.darkmode) .folder-avatar {
  box-shadow:
    0 0 0 0.28rem rgba(32, 38, 50, 0.88),
    0 0.5rem 1.1rem color-mix(in srgb, var(--folder-color, #2563eb) 30%, transparent);
}

:global(.dark) .folder-type-label,
:global(.darkmode) .folder-type-label {
  color: rgba(255, 255, 255, 0.5);
}

:global(.dark) .folder-summary-note,
:global(.darkmode) .folder-summary-note {
  color: rgba(255, 255, 255, 0.52);
}

:global(.dark) .folder-member-cloud,
:global(.darkmode) .folder-member-cloud {
  border-color: rgba(255, 255, 255, 0.18);
  background: rgba(255, 255, 255, 0.06);
  color: #67a8ff;
}

:global(.dark) .folder-member-cloud:hover,
:global(.darkmode) .folder-member-cloud:hover {
  border-color: rgba(103, 168, 255, 0.32);
  background: rgba(103, 168, 255, 0.1);
}

:global(.dark) .folder-member-cloud--open,
:global(.darkmode) .folder-member-cloud--open {
  background: rgba(103, 168, 255, 0.15);
  border-color: rgba(103, 168, 255, 0.4);
  color: #8ec1ff;
}

/* Вложенный проект в развёрнутой папке: рамка цвета папки + лёгкий сдвиг */
.project-card--infolder {
  box-shadow: inset 0 0 0 1.5px color-mix(in srgb, var(--folder-color, #2563eb) 35%, transparent);
  position: relative;
}

.project-card--infolder::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0.9rem;
  bottom: 0.9rem;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: var(--folder-color, #2563eb);
}

/* Пустая папка (раскрыта) */
.folder-empty-card {
  grid-column: 1 / -1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1.4rem;
  border-radius: 0.9rem;
  border: 1.5px dashed color-mix(in srgb, var(--folder-color, #2563eb) 45%, transparent);
  color: rgba(105, 105, 105, 0.75);
  font-size: 0.9rem;
}

.folder-empty-card button {
  border: none;
  background: color-mix(in srgb, var(--folder-color, #2563eb) 12%, transparent);
  color: var(--folder-color, #2563eb);
  font-weight: 700;
  font-size: 0.82rem;
  padding: 0.45rem 0.9rem;
  border-radius: 0.55rem;
  cursor: pointer;
}

/* Бейдж «в папке …» при поиске */
.in-folder-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  margin-left: 0.4rem;
  padding: 0.12rem 0.5rem;
  border-radius: 99rem;
  background: rgba(37, 99, 235, 0.1);
  color: #2563eb;
  font-size: 0.7rem;
  font-weight: 700;
  vertical-align: middle;
}

/* Бейдж «Организация» — кабинет Яндекса, подключённый как организация */
.org-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.28rem;
  margin-left: 0.4rem;
  padding: 0.12rem 0.5rem;
  border-radius: 99rem;
  background: rgba(139, 92, 246, 0.12);
  color: #7c3aed;
  font-size: 0.7rem;
  font-weight: 700;
  vertical-align: middle;
}
.org-badge svg { opacity: 0.85; }
:global(.darkmode) .org-badge {
  background: rgba(167, 139, 250, 0.18);
  color: #c4b5fd;
}

/* Кнопка и меню «В папку» */
.folder-move-wrap { position: relative; }

.folder-move-btn:disabled,
.folder-move-btn--loading {
  opacity: 0.72;
  cursor: wait;
}

.folder-move-menu {
  position: absolute;
  right: 0;
  bottom: calc(100% + 0.4rem);
  z-index: 30;
  min-width: 15rem;
  padding: 0.4rem;
  border-radius: 0.7rem;
  background: #fff;
  box-shadow: 0 12px 34px rgba(15, 23, 42, 0.16), 0 0 0 1px rgba(15, 23, 42, 0.05);
}

.folder-move-menu__title {
  padding: 0.35rem 0.6rem;
  font-size: 0.72rem;
  font-weight: 700;
  color: rgba(105, 105, 105, 0.6);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.folder-move-menu__item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.5rem 0.6rem;
  border: none;
  background: none;
  border-radius: 0.5rem;
  color: #171717;
  font-size: 0.85rem;
  font-weight: 600;
  text-align: left;
  cursor: pointer;
}

.folder-move-menu__item:hover:not(:disabled) { background: rgba(37, 99, 235, 0.07); }
.folder-move-menu__item:disabled { opacity: 0.45; cursor: default; }

.folder-move-menu__item i {
  width: 0.7rem;
  height: 0.7rem;
  border-radius: 0.22rem;
  flex-shrink: 0;
}

.folder-move-menu__item--out { color: #b45309; }
.folder-move-menu__item--new { color: #2563eb; }
.folder-move-menu__empty { padding: 0.4rem 0.6rem; color: rgba(105,105,105,0.6); font-size: 0.8rem; }

/* Модал папки */
.folder-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 90;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(15, 23, 42, 0.45);
  padding: 1rem;
}

.folder-modal {
  width: min(36rem, 94vw);
  max-height: 90vh;
  overflow-y: auto;
  background: #fff;
  border-radius: 1.3rem;
  padding: 1.8rem 1.9rem 1.6rem;
  box-shadow: 0 32px 80px rgba(9, 24, 63, 0.32);
}

.folder-modal h4 { margin: 0 0 0.45rem; font-size: 1.45rem; font-weight: 800; color: #171717; letter-spacing: -0.01em; }
.folder-modal__hint { margin: 0 0 1.15rem; font-size: 0.95rem; color: rgba(105, 105, 105, 0.75); line-height: 1.5; }
.folder-modal__label { display: block; margin: 1.1rem 0 0.45rem; font-size: 0.9rem; font-weight: 800; color: #333; }
.folder-modal__label small { font-weight: 500; color: rgba(105,105,105,0.6); font-size: 0.78rem; }

.folder-modal__input {
  width: 100%;
  height: 2.9rem;
  padding: 0 0.95rem;
  border-radius: 0.75rem;
  border: 1px solid rgba(15, 23, 42, 0.12);
  font-size: 0.98rem;
  font-weight: 600;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.13s ease, box-shadow 0.13s ease;
}
.folder-modal__input::placeholder { font-weight: 500; color: #b3bcc9; }
.folder-modal__input:focus { border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37,99,235,0.12); }

.folder-color-picker {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 0.7rem;
  align-items: stretch;
  padding: 0.75rem;
  border: 1px solid color-mix(in srgb, var(--folder-color, #2563eb) 18%, rgba(15, 23, 42, 0.1));
  border-radius: 1rem;
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--folder-color, #2563eb) 7%, #fff), #fff 70%);
}
.folder-color-palette {
  position: relative;
  width: 100%;
  height: 7.7rem;
  border: 1px solid color-mix(in srgb, var(--folder-color, #2563eb) 18%, rgba(15, 23, 42, 0.1));
  border-radius: 0.92rem;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0) 0%, rgba(0, 0, 0, 0.68) 100%),
    linear-gradient(90deg, #ffffff 0%, rgba(255, 255, 255, 0) 100%),
    var(--folder-palette-color, #2563eb);
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.5),
    0 0.5rem 1.25rem color-mix(in srgb, var(--folder-color, #2563eb) 12%, transparent);
  cursor: crosshair;
  overflow: hidden;
}
.folder-color-palette__marker {
  position: absolute;
  width: 1.05rem;
  height: 1.05rem;
  border: 0.18rem solid #ffffff;
  border-radius: 999px;
  background: var(--folder-color, #2563eb);
  box-shadow:
    0 0 0 1px rgba(15, 23, 42, 0.18),
    0 0.22rem 0.72rem rgba(15, 23, 42, 0.28);
  transform: translate(-50%, -50%);
  pointer-events: none;
}
.folder-color-picker__main {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.8rem;
  min-height: 3.25rem;
  padding: 0.55rem 0.7rem;
  border: 1px solid color-mix(in srgb, var(--folder-color, #2563eb) 18%, rgba(15, 23, 42, 0.1));
  border-radius: 0.85rem;
  background: rgba(255, 255, 255, 0.78);
}
.folder-color-picker__preview {
  width: 2.15rem;
  height: 2.15rem;
  border-radius: 0.72rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: var(--folder-color, #2563eb);
  background: color-mix(in srgb, var(--folder-color, #2563eb) 13%, #fff);
  box-shadow:
    inset 0 0 0 1px color-mix(in srgb, var(--folder-color, #2563eb) 18%, transparent),
    0 0.35rem 0.9rem color-mix(in srgb, var(--folder-color, #2563eb) 18%, transparent);
}
.folder-color-picker__preview svg {
  width: 1.2rem;
  height: 1.08rem;
}
.folder-color-picker__copy {
  min-width: 0;
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  gap: 0.14rem;
}
.folder-color-picker__copy strong {
  font-size: 0.92rem;
  line-height: 1.15;
  color: #171717;
}
.folder-color-picker__copy small {
  font-size: 0.76rem;
  line-height: 1.15;
  font-weight: 600;
  color: rgba(105, 105, 105, 0.58);
}
.folder-color-picker__value {
  flex-shrink: 0;
  padding: 0.42rem 0.58rem;
  border-radius: 0.58rem;
  background: color-mix(in srgb, var(--folder-color, #2563eb) 10%, #fff);
  color: color-mix(in srgb, var(--folder-color, #2563eb) 78%, #171717);
  font-size: 0.78rem;
  font-weight: 900;
  letter-spacing: 0.02em;
}
.folder-color-sliders {
  display: grid;
  gap: 0.55rem;
  padding: 0.05rem 0.08rem 0.05rem;
}
.folder-color-slider {
  display: grid;
  grid-template-columns: 7.4rem minmax(0, 1fr);
  align-items: center;
  gap: 0.7rem;
  color: rgba(105, 105, 105, 0.68);
  font-size: 0.78rem;
  font-weight: 800;
}
.folder-color-range {
  width: 100%;
  height: 0.62rem;
  appearance: none;
  border-radius: 999px;
  outline: none;
  cursor: pointer;
  box-shadow: inset 0 0 0 1px rgba(15, 23, 42, 0.08);
}
.folder-color-range::-webkit-slider-thumb {
  appearance: none;
  width: 1.18rem;
  height: 1.18rem;
  border: 0.18rem solid #ffffff;
  border-radius: 999px;
  background: var(--folder-color, #2563eb);
  box-shadow: 0 0.22rem 0.72rem rgba(15, 23, 42, 0.22);
}
.folder-color-range::-moz-range-thumb {
  width: 0.88rem;
  height: 0.88rem;
  border: 0.18rem solid #ffffff;
  border-radius: 999px;
  background: var(--folder-color, #2563eb);
  box-shadow: 0 0.22rem 0.72rem rgba(15, 23, 42, 0.22);
}
.folder-color-range--hue {
  background: linear-gradient(90deg, #ef4444, #f59e0b, #eab308, #22c55e, #06b6d4, #2563eb, #8b5cf6, #ec4899, #ef4444);
}
.folder-color-range--saturation {
  background: linear-gradient(90deg, hsl(var(--folder-hue) 0% 55%), hsl(var(--folder-hue) 100% 55%));
}
.folder-color-range--lightness {
  background: linear-gradient(90deg, #171717, hsl(var(--folder-hue) var(--folder-saturation) 48%), #d8dee8);
}
.folder-color-inputs {
  display: grid;
  grid-template-columns: minmax(7.8rem, 1.15fr) repeat(3, minmax(3.45rem, 0.55fr));
  gap: 0.55rem;
}
.folder-color-picker__hex {
  display: flex;
  align-items: center;
  min-height: 2.95rem;
  border: 1px solid rgba(15, 23, 42, 0.1);
  border-radius: 0.85rem;
  background: #f8fafc;
  padding: 0 0.72rem;
  transition: border-color 0.14s ease, box-shadow 0.14s ease;
}
.folder-color-picker__hex:focus-within {
  border-color: color-mix(in srgb, var(--folder-color, #2563eb) 48%, #2563eb);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--folder-color, #2563eb) 12%, transparent);
}
.folder-color-picker__hex span {
  color: rgba(105, 105, 105, 0.58);
  font-size: 0.95rem;
  font-weight: 800;
}
.folder-color-picker__hex input {
  width: 100%;
  min-width: 0;
  border: none;
  outline: none;
  background: transparent;
  color: #171717;
  font-size: 0.95rem;
  font-weight: 800;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}
.folder-rgb-input {
  display: flex;
  align-items: center;
  min-height: 2.95rem;
  border: 1px solid rgba(15, 23, 42, 0.1);
  border-radius: 0.85rem;
  background: #f8fafc;
  padding: 0 0.58rem;
  transition: border-color 0.14s ease, box-shadow 0.14s ease;
}
.folder-rgb-input:focus-within {
  border-color: color-mix(in srgb, var(--folder-color, #2563eb) 48%, #2563eb);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--folder-color, #2563eb) 12%, transparent);
}
.folder-rgb-input span {
  color: rgba(105, 105, 105, 0.58);
  font-size: 0.76rem;
  font-weight: 900;
}
.folder-rgb-input input {
  width: 100%;
  min-width: 0;
  border: none;
  outline: none;
  background: transparent;
  color: #171717;
  font-size: 0.9rem;
  font-weight: 800;
  text-align: right;
}
@media (max-width: 560px) {
  .folder-color-picker { grid-template-columns: 1fr; }
  .folder-color-slider { grid-template-columns: 1fr; gap: 0.35rem; }
  .folder-color-inputs { grid-template-columns: 1fr 1fr; }
}

.folder-modal__projects {
  max-height: 14.5rem;
  overflow-y: auto;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 0.8rem;
  padding: 0.4rem;
  display: flex; flex-direction: column; gap: 0.15rem;
}

.folder-project-check {
  display: flex; align-items: center; gap: 0.65rem;
  padding: 0.6rem 0.7rem; border-radius: 0.6rem;
  font-size: 0.95rem; font-weight: 600; color: #171717; cursor: pointer;
  transition: background 0.12s ease;
}
.folder-project-check:hover { background: rgba(37, 99, 235, 0.06); }
.folder-project-check--on { background: rgba(37, 99, 235, 0.07); }
.folder-project-check input { display: none; }
.fp-box {
  width: 1.15rem; height: 1.15rem; border-radius: 0.35rem;
  border: 1.5px solid rgba(15,23,42,0.25); background: #fff;
  display: inline-flex; align-items: center; justify-content: center;
  color: #fff; flex-shrink: 0;
  transition: background 0.13s ease, border-color 0.13s ease;
}
.fp-box svg { width: 0.7rem; height: 0.6rem; opacity: 0; }
.folder-project-check--on .fp-box { background: #2563eb; border-color: #2563eb; }
.folder-project-check--on .fp-box svg { opacity: 1; }
.fp-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.folder-modal__footer { display: flex; align-items: center; gap: 0.7rem; margin-top: 1.5rem; }
.folder-modal__cancel {
  border: none; background: rgba(15,23,42,0.06); color: #444;
  padding: 0.65rem 1.2rem; border-radius: 0.75rem; font-weight: 700; font-size: 0.95rem; cursor: pointer;
}
.folder-modal__cancel:hover { background: rgba(15,23,42,0.1); }
.folder-modal__save {
  border: none; background: #2563eb; color: #fff;
  padding: 0.65rem 1.35rem; border-radius: 0.75rem; font-weight: 700; font-size: 0.95rem; cursor: pointer;
  transition: background 0.13s ease, box-shadow 0.13s ease;
}
.folder-modal__save:hover:not(:disabled) { background: #1d4ed8; box-shadow: 0 6px 18px rgba(37,99,235,0.35); }
.folder-modal__save:disabled { opacity: 0.6; cursor: default; }
.folder-modal__delete {
  border: none; background: none; color: #dc2626;
  font-weight: 700; font-size: 0.92rem; cursor: pointer; padding: 0.65rem 0;
}
.folder-modal__delete--solid {
  background: #dc2626; color: #fff; padding: 0.65rem 1.35rem; border-radius: 0.75rem;
}
.folder-modal__delete--solid:hover { background: #b91c1c; }
.flex-1 { flex: 1; }
</style>
