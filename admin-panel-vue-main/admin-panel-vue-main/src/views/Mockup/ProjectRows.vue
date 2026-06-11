<template>
  <div class="relative z-[2] flex min-h-full flex-col overflow-visible px-[1.7361rem] py-[2.0833rem]">

      <div class="pt-[1.0417rem] pb-[1.0417rem] mb-[0.6944rem]">
        <h3 class="text-[2.0833rem] font-semibold leading-none text-[#171717] dark:text-white">Проекты</h3>
      </div>

      <div class="rows-toolbar">
      <div class="flex flex-wrap items-center gap-[0.6944rem]">
        <div class="custom-select" :class="{ open: openSelect === 'project' }" v-click-outside="() => closeSelect('project')">
          <button type="button" class="cs-head dark:!border-white/10 dark:!bg-[#2C2F3D] dark:!text-white/70 dark:!shadow-[inset_0_0_0_1px_rgba(255,255,255,0.08)]" @click="toggleSelect('project')">
            <span class="cs-current">{{ projectFilterLabel }}</span>
            <span class="cs-arrow dark:!bg-white/10">
              <svg width="5" height="4" viewBox="0 0 9 6" fill="none"><path d="M0.5 1L4.5 5L8.5 1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </span>
          </button>
          <div class="cs-list dark:!bg-[#2C2F3D] dark:!shadow-[0_0_0_1px_rgba(255,255,255,0.08)]">
            <button
              v-for="option in projectFilterOptions"
              :key="option.value"
              type="button"
              class="cs-option dark:!text-white/70 dark:hover:!bg-white/5"
              :class="{ selected: projectFilter === option.value }"
              @click="selectProjectFilter(option.value)"
            >{{ option.label }}</button>
          </div>
        </div>

        <div class="custom-select" :class="{ open: openSelect === 'period' }" v-click-outside="closePeriodSelect">
          <button ref="periodTriggerRef" type="button" class="cs-head dark:!border-white/10 dark:!bg-[#2C2F3D] dark:!text-white/70 dark:!shadow-[inset_0_0_0_1px_rgba(255,255,255,0.08)]" @click="toggleSelect('period')">
            <span class="cs-current">{{ periodLabel }}</span>
            <span class="cs-arrow dark:!bg-white/10">
              <svg width="5" height="4" viewBox="0 0 9 6" fill="none"><path d="M0.5 1L4.5 5L8.5 1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </span>
          </button>
          <Teleport to="body">
            <div
              v-if="openSelect === 'period'"
              ref="periodPopoverRef"
              class="period-popover period-list"
              :style="periodPopoverStyle"
            >
              <template v-for="(option, index) in periodOptions" :key="option.value || `${option.type}-${index}`">
                <DateRangePicker
                  v-if="option.type === 'label'"
                  v-model="customPeriodRange"
                  class="project-period-custom-picker"
                  :trigger-text="option.label"
                  @change="selectCustomPeriod"
                />
                <div v-else-if="option.type === 'divider'" class="period-list__divider"></div>
                <button
                  v-else
                  type="button"
                  class="period-option"
                  :class="{ selected: periodKey === option.value }"
                  @click="selectPeriod(option.value)"
                >
                  <span>{{ option.label }}</span>
                  <svg v-if="periodKey === option.value" class="period-option__check" viewBox="0 0 18 14" fill="none" aria-hidden="true">
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

        <button type="button" class="bulk-btn" @click="openMassEdit">
          <span>Массовое редактирование</span>
          <span class="bulk-btn__icon">
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path d="M9.7 3.2 12.8 6.3M2.8 13.2l3.1-.6 7.25-7.25a2.17 2.17 0 0 0-3.07-3.07L2.8 9.55v3.65Z" stroke="currentColor" stroke-width="1.45" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M2.8 13.2h3.4" stroke="currentColor" stroke-width="1.45" stroke-linecap="round"/>
            </svg>
          </span>
        </button>

        <div class="flex">
          <button type="button" class="view-btn dark:!text-white/35 dark:hover:!bg-white/5 dark:hover:!text-[#67a8ff]" @click="router.push('/project-card')" aria-label="Карточки">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <rect x="1" y="1" width="6.5" height="6.5" rx="1.5" stroke="currentColor" stroke-width="1.5"/>
              <rect x="10.5" y="1" width="6.5" height="6.5" rx="1.5" stroke="currentColor" stroke-width="1.5"/>
              <rect x="1" y="10.5" width="6.5" height="6.5" rx="1.5" stroke="currentColor" stroke-width="1.5"/>
              <rect x="10.5" y="10.5" width="6.5" height="6.5" rx="1.5" stroke="currentColor" stroke-width="1.5"/>
            </svg>
          </button>
          <button type="button" class="view-btn _active dark:!bg-[#33405f] dark:!text-[#67a8ff]" aria-label="Строки">
            <svg width="18" height="14" viewBox="0 0 18 14" fill="none">
              <rect x="1" y="1" width="16" height="5" rx="1.5" stroke="currentColor" stroke-width="1.5"/>
              <rect x="1" y="8" width="16" height="5" rx="1.5" stroke="currentColor" stroke-width="1.5"/>
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="py-16 text-center text-[0.9722rem] text-gray-400">Загрузка проектов...</div>

    <!-- Empty -->
    <div v-else-if="filteredProjects.length === 0" class="py-16 text-center text-[0.9722rem] text-gray-400">
      {{ search ? 'Проекты не найдены' : 'У вас пока нет проектов' }}
    </div>

    <div v-else class="mb-[2.0833rem] overflow-visible rounded-[1.0417rem] bg-white py-[2.0833rem] dark:bg-[#2C2F3D] dark:shadow-[0_4px_24px_rgba(0,0,0,0.28),inset_0_1px_0_rgba(255,255,255,0.07)]">
      <div class="overflow-x-auto">
        <table class="project-rows-table w-full table-auto border-collapse">
          <thead>
            <tr class="text-[0.9028rem] font-normal text-[rgba(105,105,105,0.56)] dark:text-white/45">
              <th class="border-b border-[rgba(0,0,0,0.05)] px-[0.6944rem] pb-[0.6944rem] text-left align-middle font-normal dark:border-white/10">
                <label class="ml-[1.0417rem] flex h-5 w-5 cursor-pointer items-center justify-center">
                  <input type="checkbox" class="peer sr-only" :checked="allRowsSelected" @change="toggleSelectAllRows" />
                  <span class="relative inline-block h-5 w-5 rounded-[0.2083rem] border border-[#f5f7f9] bg-[#f5f7f9] transition duration-300 peer-focus:shadow-[0_0_0_1px_rgba(0,123,255,1)] peer-checked:border-[#2563eb] peer-checked:[&>svg]:opacity-100 dark:border-white/15 dark:bg-white/10">
                    <svg class="absolute left-1/2 top-1/2 h-[0.625rem] w-[0.625rem] -translate-x-1/2 -translate-y-1/2 fill-[#2563eb] opacity-0 transition duration-300" viewBox="0 0 12 10">
                      <path d="M4.2 9.2.4 5.4l1.4-1.4 2.4 2.4L10.2.3l1.4 1.4-7.4 7.5Z" />
                    </svg>
                  </span>
                </label>
              </th>
              <th class="border-b border-[rgba(0,0,0,0.05)] px-[0.6944rem] pb-[0.6944rem] text-left align-middle font-normal dark:border-white/10">Проект</th>
              <th class="border-b border-[rgba(0,0,0,0.05)] px-[0.6944rem] pb-[0.6944rem] text-left align-middle font-normal dark:border-white/10">Интеграции</th>
              <th class="border-b border-[rgba(0,0,0,0.05)] px-[0.6944rem] pb-[0.6944rem] text-left align-middle font-normal dark:border-white/10">Показы</th>
              <th class="border-b border-[rgba(0,0,0,0.05)] px-[0.6944rem] pb-[0.6944rem] text-left align-middle font-normal dark:border-white/10">Клики</th>
              <th class="border-b border-[rgba(0,0,0,0.05)] px-[0.6944rem] pb-[0.6944rem] text-left align-middle font-normal dark:border-white/10">Расходы</th>
              <th class="border-b border-[rgba(0,0,0,0.05)] px-[0.6944rem] pb-[0.6944rem] text-left align-middle font-normal dark:border-white/10">Лиды</th>
              <th class="border-b border-[rgba(0,0,0,0.05)] px-[0.6944rem] pb-[0.6944rem] text-left align-middle font-normal dark:border-white/10">CPC</th>
              <th class="border-b border-[rgba(0,0,0,0.05)] px-[0.6944rem] pb-[0.6944rem] text-left align-middle font-normal dark:border-white/10">CPL</th>
              <th class="border-b border-[rgba(0,0,0,0.05)] px-[0.6944rem] pb-[0.6944rem] text-left align-middle font-normal dark:border-white/10">Актуальный баланс&nbsp;в&nbsp;ЛК:</th>
              <th class="border-b border-[rgba(0,0,0,0.05)] px-[0.6944rem] pb-[0.6944rem] text-left align-middle font-normal dark:border-white/10">Статус</th>
              <th class="border-b border-[rgba(0,0,0,0.05)] px-[0.6944rem] pb-[0.6944rem] text-left align-middle font-normal dark:border-white/10">Дата&nbsp;создания</th>
              <th class="border-b border-[rgba(0,0,0,0.05)] px-[0.6944rem] pb-[0.6944rem] text-left align-middle font-normal dark:border-white/10">Действия</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="project in paginatedProjects"
              :key="project.id"
              class="text-[#444] transition hover:bg-[#f8fafc] dark:text-white dark:hover:bg-white/5"
            >
              <td class="border-b border-[rgba(0,0,0,0.05)] px-[0.6944rem] py-[2.0833rem] align-middle dark:border-white/10">
                <label class="ml-[1.0417rem] flex h-5 w-5 cursor-pointer items-center justify-center">
                  <input type="checkbox" class="peer sr-only" :checked="selectedProjectIds.includes(project.id)" @change="toggleProjectRow(project.id)" />
                  <span class="relative inline-block h-5 w-5 rounded-[0.2083rem] border border-[#f5f7f9] bg-[#f5f7f9] transition duration-300 peer-focus:shadow-[0_0_0_1px_rgba(0,123,255,1)] peer-checked:border-[#2563eb] peer-checked:[&>svg]:opacity-100 dark:border-white/15 dark:bg-white/10">
                    <svg class="absolute left-1/2 top-1/2 h-[0.625rem] w-[0.625rem] -translate-x-1/2 -translate-y-1/2 fill-[#2563eb] opacity-0 transition duration-300" viewBox="0 0 12 10">
                      <path d="M4.2 9.2.4 5.4l1.4-1.4 2.4 2.4L10.2.3l1.4 1.4-7.4 7.5Z" />
                    </svg>
                  </span>
                </label>
              </td>
              <td class="border-b border-[rgba(0,0,0,0.05)] px-[0.6944rem] py-[2.0833rem] align-middle dark:border-white/10">
                <div class="flex items-center">
                  <button
                    type="button"
                    class="project-avatar-row"
                    :aria-label="`Загрузить аватарку проекта ${project.name}`"
                    @click.stop="openAvatarModal(project)"
                  >
                    <img v-if="projectAvatarUrl(project)" class="h-full w-full object-cover" :src="projectAvatarUrl(project)" :alt="project.name" />
                    <span v-else>{{ projectInitials(project) }}</span>
                    <span :class="['project-avatar-row__edit', projectAvatarUrl(project) ? 'project-avatar-row__edit--hover' : 'project-avatar-row__edit--default']" aria-hidden="true">
                      <svg viewBox="0 0 16 16" fill="none">
                        <path d="M9.7 3.2 12.8 6.3M2.8 13.2l3.1-.6 7.25-7.25a2.17 2.17 0 0 0-3.07-3.07L2.8 9.55v3.65Z" stroke="currentColor" stroke-width="1.45" stroke-linecap="round" stroke-linejoin="round"/>
                      </svg>
                    </span>
                  </button>
                  <div class="pl-[1.0417rem]">
                    <button
                      type="button"
                      class="project-title-link mb-[0.3472rem] text-[0.9028rem] font-normal leading-[130%] text-[#696969] dark:text-white"
                      @click="openProject(project)"
                    >
                      {{ project.name }}
                    </button>
                    <button type="button" class="project-id-link dark:text-white/45" @click.stop="copyProjectId(project)">ID:&nbsp;{{ projectSupportId(project) }}</button>
                  </div>
                </div>
              </td>
              <td class="border-b border-[rgba(0,0,0,0.05)] px-[0.6944rem] py-[2.0833rem] align-middle dark:border-white/10">
                <div class="flex items-center gap-2">
                  <img
                    v-for="platform in visibleProjectPlatforms(project)"
                    :key="platform"
                    width="22"
                    :src="platformIcon(platform)"
                    :alt="platformLabel(platform)"
                  />
                  <span v-if="!visibleProjectPlatforms(project).length" class="text-[0.9028rem] text-gray-400">—</span>
                </div>
              </td>
              <td
                v-for="cell in metricCells(project)"
                :key="cell.key"
                class="border-b border-[rgba(0,0,0,0.05)] px-[0.6944rem] py-[2.0833rem] align-middle dark:border-white/10"
              >
                <div :class="['mb-[0.3472rem] text-[1.0417rem] leading-[130%]', cell.bold ? 'font-bold' : 'font-normal']">{{ cell.value }}</div>
                <div v-if="cell.trendAvailable !== false" :class="trendBadgeClass(getProjectMetric(project.id), cell.key)">
                  <svg :class="trendArrowClass(getProjectMetric(project.id), cell.key)" width="8" height="7" viewBox="0 0 12 9" fill="none" aria-hidden="true">
                    <path d="M1 8L6 2L11 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                  <span class="font-semibold">{{ trendText(getProjectMetric(project.id), cell.key) }}</span>
                </div>
              </td>
              <td class="border-b border-[rgba(0,0,0,0.05)] px-[0.6944rem] py-[2.0833rem] align-middle dark:border-white/10">
                <div :class="balanceCardClass(project)">
                  <div class="flex h-full items-center justify-center">
                    <img width="18" :src="balancePlatform(project).icon" :alt="balancePlatform(project).label" />
                    <div :class="['px-[0.6944rem] text-[0.9028rem]', balancePlatform(project).textClass]">{{ balancePlatform(project).label }}</div>
                    <div :class="['inline-flex min-h-[1.5278rem] items-center rounded-full bg-white px-[0.5556rem] text-center text-[0.7639rem] dark:bg-white/10', balancePlatform(project).textClass]">
                      {{ formatMoney(withVat(getProjectMetric(project.id).balance)) }}
                    </div>
                  </div>
                </div>
              </td>
              <td class="border-b border-[rgba(0,0,0,0.05)] px-[0.6944rem] py-[2.0833rem] align-middle dark:border-white/10">
                <div class="flex flex-col items-start gap-1">
                  <span :class="statusBadgeClass(project)">
                    {{ hasActiveProjectIntegration(project) ? 'Активен' : 'Неактивен' }}
                  </span>
                  <span
                    v-if="detectorBadge(project)"
                    class="detector-row-badge"
                    :class="`detector-row-badge--${detectorBadge(project).type}`"
                    :title="detectorBadge(project).text"
                  >{{ detectorBadge(project).text }}</span>
                </div>
              </td>
              <td class="border-b border-[rgba(0,0,0,0.05)] px-[0.6944rem] py-[2.0833rem] align-middle dark:border-white/10">
                <div class="text-[1.0417rem] leading-[130%]">{{ formatDate(project.created_at || project.createdAt) }}</div>
              </td>
              <td class="relative border-b border-[rgba(0,0,0,0.05)] px-[0.6944rem] py-[2.0833rem] align-middle dark:border-white/10">
                <button
                  type="button"
                  class="relative h-[1.7361rem] w-[2.2222rem] rounded-[0.2083rem] bg-[#f5f7f9]/60 transition hover:bg-[#ecf3fe] dark:bg-white/10"
                  @click.stop="toggleActionMenu(project, $event)"
                  aria-label="Действия"
                >
                  <svg class="absolute left-1/2 top-1/2 h-[0.3472rem] w-[1.3194rem] -translate-x-1/2 -translate-y-1/2 fill-[#d9d9d9]" viewBox="0 0 19 5">
                    <circle cx="2.5" cy="2.5" r="2.5" />
                    <circle cx="9.5" cy="2.5" r="2.5" />
                    <circle cx="16.5" cy="2.5" r="2.5" />
                  </svg>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="relative flex min-h-[4.8611rem] flex-col gap-3 px-[1.3889rem] pt-[1.6667rem] sm:flex-row sm:items-end sm:px-[2.0833rem] sm:pt-[2.0833rem]">
        <div class="min-w-0 pb-[1.0417rem]">
          <div class="mb-[0.6944rem] text-[0.9028rem] font-medium leading-[130%] text-[#696969] dark:text-white/70">Элементов на&nbsp;странице:</div>
          <div class="relative inline-block">
            <button
              type="button"
              class="inline-flex min-h-[2.0833rem] items-center rounded-[0.4167rem] border border-[rgba(168,169,170,0.32)] bg-transparent px-[0.8333rem] py-[0.3472rem] text-[0.9028rem] font-medium leading-[130%] text-[rgba(105,105,105,0.6)] transition duration-200 focus:border-black/10 focus:outline-none dark:text-white/60"
              @click="toggleSelect('pageSize')"
            >
              <span>{{ itemsPerPage }}</span>
              <span :class="['ml-[0.8333rem] flex shrink-0 items-center justify-center transition-transform duration-300', openSelect === 'pageSize' ? 'rotate-180' : '']">
                <svg class="h-[0.625rem] w-[0.625rem] fill-[rgba(105,105,105,0.6)] dark:fill-white/60" viewBox="0 0 10 6">
                  <path d="M5 6 0 0h10L5 6Z" />
                </svg>
              </span>
            </button>
            <div :class="pageSizeDropdownClass">
              <button
                v-for="option in itemsPerPageOptions"
                :key="option"
                type="button"
                :class="pageSizeOptionClass(itemsPerPage === option)"
                @click="setItemsPerPage(option)"
              >
                {{ option }}
              </button>
            </div>
          </div>
        </div>

        <div class="order-3 py-[0.3472rem] text-center text-[0.9028rem] font-medium leading-[130%] text-[#696969] dark:text-white/70 sm:absolute sm:bottom-0 sm:left-1/2 sm:order-none sm:-translate-x-1/2 sm:py-[1.0417rem]">
          {{ paginationStart }}-{{ paginationEnd }} из {{ filteredProjects.length }}
        </div>

        <div class="flex pb-[1.0417rem] sm:ml-auto">
          <button
            type="button"
            class="inline-flex h-[2.0833rem] w-[2.0833rem] items-center justify-center rounded-[0.4167rem] border border-[rgba(168,169,170,0.32)] text-[rgba(105,105,105,0.56)] transition duration-300 hover:border-[#1f9de4] hover:text-[#1f9de4]"
            aria-label="Предыдущая страница"
            @click="currentPage = Math.max(1, currentPage - 1)"
          >
            <svg class="h-2 w-2 fill-current" viewBox="0 0 8 8">
              <path d="M5.7.7 2.4 4l3.3 3.3-1 1L.4 4 4.7-.3l1 1Z" />
            </svg>
          </button>
          <span class="w-[0.2778rem]"></span>
          <button
            type="button"
            class="inline-flex h-[2.0833rem] w-[2.0833rem] items-center justify-center rounded-[0.4167rem] border border-[rgba(168,169,170,0.32)] text-[rgba(105,105,105,0.56)] transition duration-300 hover:border-[#1f9de4] hover:text-[#1f9de4]"
            aria-label="Следующая страница"
            @click="currentPage = Math.min(totalPages, currentPage + 1)"
          >
            <svg class="h-2 w-2 fill-current" viewBox="0 0 8 8">
              <path d="M2.3.7 5.6 4 2.3 7.3l1 1L7.6 4 3.3-.3l-1 1Z" />
            </svg>
          </button>
        </div>
      </div>
    </div>

    <div
      v-if="activeActionProject"
      class="fixed z-[1200] w-[15.2778rem] rounded-[0.8333rem] bg-white py-3 shadow-[0_0_15px_rgba(0,0,0,.1)] dark:bg-[#2C2F3D] dark:shadow-[0_8px_32px_rgba(0,0,0,0.40),inset_0_1px_0_rgba(255,255,255,0.08)]"
      :style="{ top: `${actionMenuPosition.top}px`, left: `${actionMenuPosition.left}px` }"
      @click.stop
    >
      <button class="flex min-h-[2.9861rem] w-full items-center px-[1.0417rem] text-left text-[0.9722rem] text-[#444] transition hover:bg-[#f5f7f9] dark:text-white dark:hover:bg-white/10" @click="openProject(activeActionProject)">
        <span class="mr-3 flex w-[2.0833rem] justify-center text-[#2563eb]">
          <svg class="h-[0.9722rem] w-[1.25rem] fill-none stroke-current" viewBox="0 0 24 18" stroke-width="1.7"><path d="M1.5 9s3.8-7 10.5-7 10.5 7 10.5 7-3.8 7-10.5 7S1.5 9 1.5 9Z"/><circle cx="12" cy="9" r="3"/></svg>
        </span>
        Просмотр
      </button>
      <button class="flex min-h-[2.9861rem] w-full items-center px-[1.0417rem] text-left text-[0.9722rem] text-[#444] transition hover:bg-[#f5f7f9] dark:text-white dark:hover:bg-white/10" @click="editProject(activeActionProject)">
        <span class="mr-3 flex w-[2.0833rem] justify-center text-[#2563eb]">
          <svg class="h-[1.25rem] w-[1.25rem] fill-none stroke-current" viewBox="0 0 24 24" stroke-width="1.7"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4 11.5-11.5Z"/></svg>
        </span>
        Редактировать
      </button>
      <button class="flex min-h-[2.9861rem] w-full items-center px-[1.0417rem] text-left text-[0.9722rem] text-[#ec3434] transition hover:bg-[#fff0f1] dark:hover:bg-white/10" @click="requestDeleteProject(activeActionProject)">
        <span class="mr-3 flex w-[2.0833rem] justify-center">
          <svg class="h-[1.1806rem] w-[1.1806rem] fill-none stroke-current" viewBox="0 0 24 24" stroke-width="1.7"><path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v5M14 11v5"/></svg>
        </span>
        Удалить
      </button>
    </div>

    <Teleport to="body">
      <!-- MODAL: Mass edit -->
      <div
        v-if="massEditOpen"
        class="fixed inset-0 z-[9000] flex items-center justify-center bg-black/50 p-4"
        @click.self="massEditOpen = false"
      >
        <div class="w-full max-w-[33.3333rem] rounded-2xl border border-black/5 bg-white p-6 dark:border-white/10 dark:bg-[#2C2F3D]">
          <h4 class="text-[1.25rem] font-bold text-gray-800 dark:text-gray-100 mb-2">Массовое редактирование</h4>
          <p class="text-[0.9722rem] text-gray-400 mb-3">Выбрано проектов: {{ selectedProjectIds.length }}</p>

          <!-- Action picker -->
          <div class="mb-4 flex flex-col gap-2">
            <label
              v-for="act in massActions"
              :key="act.value"
              class="flex cursor-pointer items-center gap-3 rounded-xl border px-4 py-3 transition"
              :class="massAction === act.value
                ? 'border-[#2563eb] bg-[#f3f7ff] dark:bg-[#2563eb]/10 dark:border-[#2563eb]/60'
                : 'border-black/10 dark:border-white/15 hover:bg-gray-50 dark:hover:bg-white/5'"
            >
              <input
                v-model="massAction"
                type="radio"
                :value="act.value"
                class="accent-[#2563eb] h-4 w-4"
              />
              <div>
                <div class="text-[0.9722rem] font-medium text-gray-700 dark:text-gray-200">{{ act.label }}</div>
                <div class="text-[0.7639rem] text-gray-400 dark:text-white/45">{{ act.hint }}</div>
              </div>
            </label>
          </div>

          <!-- Selected projects list -->
          <ul class="text-[0.9028rem] text-gray-400 mb-3 pl-4 list-disc max-h-[8rem] overflow-y-auto">
            <li v-for="id in selectedProjectIdList" :key="id">{{ projectNameById(id) }}</li>
          </ul>

          <!-- Action: delete warning -->
          <template v-if="massAction === 'delete'">
            <div class="mb-4 rounded-xl bg-red-50 dark:bg-red-500/10 px-4 py-3 text-[0.9028rem] text-red-600 dark:text-red-300">
              Все выбранные проекты и их данные будут удалены безвозвратно. Это действие нельзя отменить.
            </div>
          </template>

          <!-- Action: unlink integrations -->
          <template v-if="massAction === 'unlink'">
            <div class="mb-4 rounded-xl bg-amber-50 dark:bg-amber-500/10 px-4 py-3 text-[0.9028rem] text-amber-700 dark:text-amber-300">
              У выбранных проектов будут отвязаны все интеграции ({{ massIntegrationsCount }}). Проекты останутся, но перестанут получать данные.
            </div>
          </template>

          <!-- Buttons -->
          <div class="flex flex-wrap gap-3">
            <button
              class="h-[3.0556rem] px-5 rounded-xl text-white text-[0.9722rem] font-medium disabled:opacity-50 transition-colors"
              :class="massAction === 'delete'
                ? 'bg-red-600 hover:bg-red-700'
                : 'bg-[#2563eb] hover:bg-[#1d4ed8]'"
              type="button"
              :disabled="massSaving || (massAction === 'unlink' && massIntegrationsCount === 0)"
              @click="executeMassAction"
            >{{ massSaving ? 'Выполнение...' : massActionButtonLabel }}</button>
            <button
              class="h-[3.0556rem] px-5 rounded-xl border border-black/10 dark:border-white/15 bg-white dark:bg-white/5 text-[0.9722rem] text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-white/10 disabled:opacity-50 transition-colors"
              type="button"
              :disabled="massSaving"
              @click="massEditOpen = false"
            >Закрыть</button>
          </div>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <!-- MODAL: Delete confirm -->
      <div
        v-if="deleteTarget"
        class="fixed inset-0 z-[9000] flex items-center justify-center bg-black/50 p-4"
      >
        <div class="w-full max-w-[27.7778rem] rounded-2xl border border-black/5 bg-white p-6 dark:border-white/10 dark:bg-[#2C2F3D]">
          <h4 class="text-[1.25rem] font-bold text-gray-800 dark:text-gray-100 mb-3">Удалить проект?</h4>
          <p class="text-[0.9722rem] text-gray-400 mb-5">Проект «{{ deleteTarget.name }}» и все его данные будут удалены безвозвратно.</p>
          <div class="flex gap-3">
            <button
              class="h-[3.0556rem] px-5 rounded-xl bg-[#2563eb] text-white text-[0.9722rem] font-medium hover:bg-[#1d4ed8] disabled:opacity-50 transition-colors"
              :disabled="deleting"
              @click="doDelete"
            >{{ deleting ? 'Удаление...' : 'Удалить' }}</button>
            <button
              class="h-[3.0556rem] px-5 rounded-xl border border-black/10 dark:border-white/15 bg-white dark:bg-white/5 text-[0.9722rem] text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-white/10 transition-colors"
              @click="deleteTarget = null"
            >Отмена</button>
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
      v-if="editingProject"
      :project="editingProject"
      @close="editingProject = null"
      @saved="handleEditSaved"
      @avatar-saved="handleAvatarSaved"
      @deleted="handleProjectDeleted"
      @add-channel="handleSettingsAddChannel"
      @configure-channel="handleSettingsConfigureChannel"
    />

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
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
import { useDetectorCrossProject } from '../../composables/useDetector'
import { useSyncStatus } from '../../composables/useSyncStatus'

const router = useRouter()
const { projects, isLoading, fetchProjects, setCurrentProject } = useProjects()
const toaster = useToaster()
const { fetchCrossProject, getProjectStatus } = useDetectorCrossProject()
const {
  syncingIntegrations: globalSyncingIntegrations,
  startIntegrationSync,
  waitForSyncJobs,
  fetchSyncStatus,
} = useSyncStatus()

const periodKey = ref('last_7_days')
const customPeriodRange = ref({ start: null, end: null })
const search = ref('')
const projectFilter = ref('all')
const openSelect = ref(null)
const itemsPerPage = ref(10)
const currentPage = ref(1)
const deleting = ref(false)
const deleteTarget = ref(null)
const metricsByProjectId = ref({})
const selectedProjectIds = ref([])
const massEditOpen = ref(false)
const massSaving = ref(false)
const activeActionProjectId = ref(null)
const activeActionProject = ref(null)
const actionMenuPosition = ref({ top: 0, left: 0 })
const periodTriggerRef = ref(null)
const periodPopoverRef = ref(null)
const periodOptions = projectPeriodOptions
const avatarProject = ref(null)
const editingProject = ref(null)

const projectFilterOptions = [
  { value: 'all', label: 'Все' },
  { value: 'active', label: 'Активные' },
  { value: 'inactive', label: 'Неактивные' }
]

const itemsPerPageOptions = [10, 20, 30]

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

const toggleSelect = (name) => {
  openSelect.value = openSelect.value === name ? null : name
}

const closeSelect = (name) => {
  if (openSelect.value === name) openSelect.value = null
}

const closePeriodSelect = (event) => {
  if (periodPopoverRef.value?.contains(event.target)) return
  if (event.target?.closest?.('.calendar-popup')) return
  closeSelect('period')
}

const selectDropdownClass = (name) => [
  'absolute left-0 top-full z-30 mt-1 flex min-w-[15.9722rem] origin-top flex-col overflow-hidden rounded-[0.5556rem] bg-white p-0 shadow-[0_0_0_1px_rgba(68,68,68,.1)] transition-[opacity,transform] duration-200 ease-[cubic-bezier(.5,0,0,1.25)] dark:bg-[#3a3c49]',
  openSelect.value === name
    ? 'pointer-events-auto scale-100 translate-y-0 opacity-100'
    : 'pointer-events-none scale-75 -translate-y-[1.4583rem] opacity-0'
]

const selectOptionClass = (selected) => [
  'px-[1.1806rem] py-3 text-left text-[0.9028rem] text-[#696969] transition duration-200 hover:bg-[#f5f7f9] dark:text-white/75 dark:hover:bg-white/5',
  selected ? 'bg-[#f5f7f9] font-bold dark:bg-white/5' : 'bg-transparent font-medium'
]

const pageSizeDropdownClass = computed(() => [
  'absolute left-0 top-full z-30 mt-1 flex min-w-full origin-top flex-col overflow-hidden rounded-[0.5556rem] bg-white p-0 shadow-[0_0_0_1px_rgba(68,68,68,.1)] transition-[opacity,transform] duration-200 ease-[cubic-bezier(.5,0,0,1.25)] dark:bg-[#3a3c49]',
  openSelect.value === 'pageSize'
    ? 'pointer-events-auto scale-100 translate-y-0 opacity-100'
    : 'pointer-events-none scale-75 -translate-y-[1.4583rem] opacity-0'
])

const pageSizeOptionClass = (selected) => [
  'px-[0.8333rem] py-2 text-left text-[0.9028rem] text-[rgba(105,105,105,0.6)] transition duration-200 hover:bg-[#f5f7f9] dark:text-white/60 dark:hover:bg-white/5',
  selected ? 'bg-[#f5f7f9] font-bold dark:bg-white/5' : 'bg-transparent font-medium'
]

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

const selectProjectFilter = (value) => {
  projectFilter.value = value
  openSelect.value = null
}

const selectPeriod = async (value) => {
  periodKey.value = value
  openSelect.value = null
  await reloadMetrics()
}

const selectCustomPeriod = async (range) => {
  if (!range?.start || !range?.end) return
  customPeriodRange.value = { start: range.start, end: range.end }
  periodKey.value = 'custom'
  openSelect.value = null
  await reloadMetrics()
}

const formatPeriodDate = (value) => {
  const [year, month, day] = String(value).split('-')
  if (!year || !month || !day) return value
  return `${day}.${month}.${year}`
}

const setItemsPerPage = (value) => {
  itemsPerPage.value = value
  currentPage.value = 1
  openSelect.value = null
}

const filteredProjects = computed(() => {
  let list = projects.value
  if (projectFilter.value === 'active') {
    list = list.filter(hasActiveProjectIntegration)
  } else if (projectFilter.value === 'inactive') {
    list = list.filter((p) => !hasActiveProjectIntegration(p))
  }
  if (search.value.trim()) {
    const q = search.value.toLowerCase()
    list = list.filter(p =>
      p.name?.toLowerCase().includes(q) ||
      String(p.display_id || '').toLowerCase().includes(q) ||
      String(p.id || '').toLowerCase().includes(q)
    )
  }
  return [...list].sort((a, b) => (a.name || '').localeCompare(b.name || '', 'ru'))
})

const allRowsSelected = computed(() => {
  const list = paginatedProjects.value
  if (!list.length) return false
  return list.every((p) => selectedProjectIds.value.includes(p.id))
})

const totalPages = computed(() => Math.max(1, Math.ceil(filteredProjects.value.length / itemsPerPage.value)))

const paginatedProjects = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage.value
  return filteredProjects.value.slice(start, start + itemsPerPage.value)
})

const paginationStart = computed(() => {
  if (!filteredProjects.value.length) return 0
  return (currentPage.value - 1) * itemsPerPage.value + 1
})

const paginationEnd = computed(() => Math.min(currentPage.value * itemsPerPage.value, filteredProjects.value.length))

const selectedProjectIdList = computed(() => [...selectedProjectIds.value])

const projectNameById = (id) => projects.value.find((p) => p.id === id)?.name || String(id)

const toggleProjectRow = (id) => {
  const idx = selectedProjectIds.value.indexOf(id)
  if (idx > -1) selectedProjectIds.value.splice(idx, 1)
  else selectedProjectIds.value.push(id)
}

const toggleSelectAllRows = () => {
  const ids = paginatedProjects.value.map((p) => p.id)
  if (allRowsSelected.value) {
    selectedProjectIds.value = selectedProjectIds.value.filter((id) => !ids.includes(id))
  } else {
    const set = new Set([...selectedProjectIds.value, ...ids])
    selectedProjectIds.value = Array.from(set)
  }
}

const massAction = ref('delete')

const massActions = [
  { value: 'delete', label: 'Удалить выбранные', hint: 'Безвозвратно удалить проекты и все их данные' },
  { value: 'unlink', label: 'Отвязать интеграции', hint: 'Удалить все интеграции у выбранных проектов' },
]

const massIntegrationsCount = computed(() => {
  return selectedProjectIds.value.reduce((sum, id) => {
    const project = projects.value.find((p) => p.id === id)
    return sum + (project?.integrations?.length || 0)
  }, 0)
})

const massActionButtonLabel = computed(() => {
  if (massAction.value === 'delete') return `Удалить (${selectedProjectIds.value.length})`
  if (massAction.value === 'unlink') return `Отвязать (${massIntegrationsCount.value})`
  return 'Выполнить'
})

const openMassEdit = () => {
  if (!selectedProjectIds.value.length) {
    toaster.warning('Отметьте один или несколько проектов в таблице.')
    return
  }
  massAction.value = 'delete'
  massEditOpen.value = true
}

const executeMassAction = async () => {
  if (massAction.value === 'delete') return applyMassDelete()
  if (massAction.value === 'unlink') return applyMassUnlink()
}

const failedBulkResult = (results) => results.find((result) => result.status === 'rejected')

const syncSelectedProjects = () => {
  const existingIds = new Set(projects.value.map((project) => project.id))
  selectedProjectIds.value = selectedProjectIds.value.filter((id) => existingIds.has(id))
}

const applyMassDelete = async () => {
  if (!selectedProjectIds.value.length) return
  massSaving.value = true
  const ids = [...selectedProjectIds.value]
  try {
    const results = await Promise.allSettled(ids.map((id) => api.delete(`clients/${id}`)))
    const failed = failedBulkResult(results)
    const successCount = results.length - results.filter((result) => result.status === 'rejected').length
    if (failed) {
      toaster.error(failed.reason?.response?.data?.detail || `Удалено частично: ${successCount} из ${ids.length}.`)
    } else {
      toaster.success(`Удалено проектов: ${ids.length}`)
      selectedProjectIds.value = []
      massEditOpen.value = false
    }
  } catch (err) {
    console.error(err)
    toaster.error(err.response?.data?.detail || 'Не удалось удалить некоторые проекты.')
  } finally {
    await fetchProjects()
    syncSelectedProjects()
    await loadProjectMetrics()
    massSaving.value = false
  }
}

const applyMassUnlink = async () => {
  if (!selectedProjectIds.value.length) return
  massSaving.value = true
  const integrationIds = selectedProjectIds.value.flatMap((id) => {
    const project = projects.value.find((p) => p.id === id)
    return (project?.integrations || []).map((i) => i.id)
  })
  if (!integrationIds.length) {
    toaster.warning('У выбранных проектов нет интеграций.')
    massSaving.value = false
    return
  }
  try {
    const results = await Promise.allSettled(integrationIds.map((id) => api.delete(`integrations/${id}`)))
    const failed = failedBulkResult(results)
    const successCount = results.length - results.filter((result) => result.status === 'rejected').length
    if (failed) {
      toaster.error(failed.reason?.response?.data?.detail || `Отвязано частично: ${successCount} из ${integrationIds.length}.`)
    } else {
      toaster.success(`Отвязано интеграций: ${integrationIds.length}`)
      massEditOpen.value = false
    }
  } catch (err) {
    console.error(err)
    toaster.error(err.response?.data?.detail || 'Не удалось отвязать некоторые интеграции.')
  } finally {
    await fetchProjects()
    await loadProjectMetrics()
    massSaving.value = false
  }
}

const emptyMetric = () => ({
  expenses: 0,
  impressions: 0,
  clicks: 0,
  leads: 0,
  cpc: 0,
  cpa: 0,
  balance: 0,
  trends: null
})

const getProjectMetric = (projectId) => metricsByProjectId.value[projectId] || emptyMetric()

const hasPlatform = (project, platform) => hasProjectPlatform(project, platform)
const visibleProjectPlatforms = (project) => projectPlatforms(project).filter((platform) => ['YANDEX', 'VK', 'AVITO'].includes(platform))
const platformIcon = (platform) => {
  if (platform === 'VK') return '/admirra/img/icons/vk-ads.png'
  if (platform === 'AVITO') return '/admirra/img/icons/avito.svg'
  return '/admirra/img/icons/yandex-direct.png'
}
const platformLabel = (platform) => {
  if (platform === 'VK') return 'VK Ads'
  if (platform === 'AVITO') return 'Avito Ads'
  return 'Yandex Direct'
}

const VAT_RATE = 1.22
const includeVat = ref(true)
const syncingIntegrations = ref(false)
const projectsSyncing = computed(() => syncingIntegrations.value || globalSyncingIntegrations.value.length > 0)
const formatNumber = (num) => new Intl.NumberFormat('ru-RU').format(Number(num || 0))
const formatMoney = (num) => `${new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 2 }).format(Number(num || 0))} ₽`
const withVat = (num) => (Number(num) || 0) * (includeVat.value ? VAT_RATE : 1)

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

const projectSyncStatusText = computed(() => {
  if (projectsSyncing.value) return 'Выполняется синхронизация, пожалуйста подождите'
  const formatted = formatMoscowSyncDate(lastProjectSyncAt.value)
  return formatted ? `Последняя синхронизация: ${formatted} МСК` : ''
})

const handleSyncProjects = async () => {
  if (syncingIntegrations.value) return
  const integrations = projects.value.flatMap((project) => project.integrations || [])
  const uniqueIntegrations = Array.from(
    new Map(integrations.filter((i) => i?.id).map((i) => [i.id, i])).values()
  )
  if (!uniqueIntegrations.length) {
    toaster.info('Нет подключённых каналов для синхронизации.')
    return
  }
  syncingIntegrations.value = true
  try {
    const results = await Promise.allSettled(uniqueIntegrations.map((i) => startIntegrationSync(i.id, { days: 90 })))
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

const trendText = (metric, key) => {
  const trend = Number(metric?.trends?.[key] || 0)
  const sign = trend >= 0 ? '+' : ''
  return `${sign}${trend.toFixed(1)}%`
}

const metricCells = (project) => {
  const m = getProjectMetric(project.id)
  const leadsAvailable = m.leads_available !== false
  const cpaAvailable = m.cpa_available !== false
  const goalsSyncing = Boolean(m.goals_syncing)
  return [
    { key: 'impressions', value: formatNumber(m.impressions) },
    { key: 'clicks', value: formatNumber(m.clicks) },
    { key: 'expenses', value: formatMoney(withVat(m.expenses)), bold: true },
    { key: 'leads', value: leadsAvailable ? (goalsSyncing ? 'синхр.' : formatNumber(m.leads)) : '—', trendAvailable: leadsAvailable && !goalsSyncing },
    { key: 'cpc', value: formatMoney(withVat(m.cpc)) },
    { key: 'cpa', value: cpaAvailable && !goalsSyncing ? formatMoney(withVat(m.cpa)) : '—', trendAvailable: cpaAvailable && !goalsSyncing }
  ]
}

const shortId = (id) => {
  const v = String(id || '')
  return v.length > 12 ? `${v.slice(0, 8)}...${v.slice(-4)}` : v || '—'
}

const projectSupportId = (project) => project?.display_id || shortId(project?.id)

const copyProjectId = async (project) => {
  const value = String(project?.display_id || project?.id || '')
  if (!value) return
  try {
    await navigator.clipboard.writeText(value)
    toaster.success('ID проекта скопирован')
  } catch {
    toaster.error('Не удалось скопировать ID')
  }
}

const trendBadgeClass = (metric, key) => {
  const trend = Number(metric?.trends?.[key] || 0)
  const costTrendKeys = new Set(['cpc', 'cpa'])
  const negative = costTrendKeys.has(key) ? trend > 0 : trend < 0
  return [
    'inline-flex items-center gap-1 rounded-[0.2083rem] px-[0.4167rem] py-0 text-[0.7639rem] font-bold leading-[130%]',
    negative
      ? 'bg-red-500/10 text-red-600 dark:bg-red-500/15 dark:text-red-300'
      : 'bg-[#00ff4e]/10 text-[#16a34a] dark:bg-[#00ff4e]/15 dark:text-[#5ee886]'
  ]
}

const trendArrowClass = (metric, key) => [
  'h-[0.4861rem] w-[0.5556rem] shrink-0 transition-transform',
  Number(metric?.trends?.[key] || 0) < 0 ? 'rotate-180' : ''
]

const statusBadgeClass = (project) => [
  'inline-flex min-h-[1.3889rem] items-center rounded-[0.2083rem] px-[0.4167rem] py-[0.4167rem] text-[0.7639rem] font-bold leading-[130%]',
  hasActiveProjectIntegration(project)
    ? 'bg-[#00ff4e]/10 text-[#16a34a] dark:bg-[#00ff4e]/15 dark:text-[#5ee886]'
    : 'bg-red-500/10 text-red-600 dark:bg-red-500/15 dark:text-red-300'
]

const balancePlatform = (project) => {
  if (hasPlatform(project, 'YANDEX')) {
    return {
      label: 'Yandex Direct',
      icon: '/admirra/img/icons/yandex-direct.png',
      cardClass: 'bg-[#fff2e4]',
      darkCardClass: 'dark:bg-[#3a3128]',
      textClass: 'text-[#71663e] dark:text-[#f0d99a]'
    }
  }
  if (hasPlatform(project, 'VK')) {
    return {
      label: 'VK Ads',
      icon: '/admirra/img/icons/vk-ads.png',
      cardClass: 'bg-[#f0f7ff]',
      darkCardClass: 'dark:bg-[#213652]',
      textClass: 'text-[#2563eb] dark:text-[#8bb7ff]'
    }
  }
  if (hasPlatform(project, 'AVITO')) {
    return {
      label: 'Avito Ads',
      icon: '/admirra/img/icons/avito.svg',
      cardClass: 'bg-[#ecfdf5]',
      darkCardClass: 'dark:bg-[#183629]',
      textClass: 'text-[#047857] dark:text-[#7dd3a8]'
    }
  }
  return {
    label: 'Yandex Direct',
    icon: '/admirra/img/icons/yandex-direct.png',
    cardClass: 'bg-[#fff2e4]',
    darkCardClass: 'dark:bg-[#3a3128]',
    textClass: 'text-[#71663e] dark:text-[#f0d99a]'
  }
}

const balanceCardClass = (project) => {
  const platform = balancePlatform(project)
  return ['h-full rounded-[0.8333rem] p-[0.6944rem]', platform.cardClass, platform.darkCardClass]
}

const formatDate = (value) => {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat('ru-RU').format(date)
}

const closeActionMenu = () => {
  activeActionProjectId.value = null
  activeActionProject.value = null
}

const toggleActionMenu = (project, event) => {
  if (activeActionProjectId.value === project.id) {
    closeActionMenu()
    return
  }

  const rect = event.currentTarget.getBoundingClientRect()
  const menuWidth = 220
  const menuHeight = 153
  const gap = 8
  const viewportPadding = 12
  const left = Math.min(
    window.innerWidth - menuWidth - viewportPadding,
    Math.max(viewportPadding, rect.right - menuWidth)
  )
  let top = rect.bottom + gap

  if (top + menuHeight > window.innerHeight - viewportPadding) {
    top = Math.max(viewportPadding, rect.top - menuHeight - gap)
  }

  activeActionProjectId.value = project.id
  activeActionProject.value = project
  actionMenuPosition.value = { top, left }
}

const editProject = (project) => {
  closeActionMenu()
  editingProject.value = project
}

const handleEditSaved = (updatedProject) => {
  updateProjectInList(updatedProject)
  editingProject.value = null
}

const handleProjectDeleted = (projectId) => {
  projects.value = projects.value.filter((p) => p.id !== projectId)
  editingProject.value = null
}

const handleSettingsAddChannel = () => {
  const projectId = editingProject.value?.id
  editingProject.value = null
  router.push({ path: '/integrations/wizard', query: projectId ? { client_id: projectId } : {} })
}

const handleSettingsConfigureChannel = (channel) => {
  editingProject.value = null
  router.push({
    path: '/integrations/wizard',
    query: { resume_integration_id: channel.id, initial_step: 2 },
  })
}

const requestDeleteProject = (project) => {
  deleteTarget.value = project
  closeActionMenu()
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
            end_date: endDate
          }
        })
        return [project.id, data || emptyMetric()]
      } catch {
        return [project.id, emptyMetric()]
      }
    })
  )

  metricsByProjectId.value = Object.fromEntries(entries)
}

const reloadMetrics = async () => {
  await loadProjectMetrics()
}

const openAvatarModal = (project) => {
  avatarProject.value = project
}

const updateProjectInList = (updatedProject) => {
  const index = projects.value.findIndex((project) => project.id === updatedProject.id)
  if (index !== -1) {
    projects.value[index] = { ...projects.value[index], ...updatedProject }
  }
}

const handleAvatarSaved = (updatedProject) => {
  updateProjectInList(updatedProject)
  toaster.success('Аватарка проекта обновлена.')
}

const openProject = (project) => {
  closeActionMenu()
  setCurrentProject(project.id)
  router.push('/dashboard/general-3')
}

const doDelete = async () => {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    await api.delete(`clients/${deleteTarget.value.id}`)
    deleteTarget.value = null
    await fetchProjects()
    await loadProjectMetrics()
  } catch (err) {
    console.error('Delete project error:', err)
  } finally {
    deleting.value = false
  }
}

watch([filteredProjects, itemsPerPage], () => {
  currentPage.value = Math.min(currentPage.value, totalPages.value)
})

const detectorBadge = (project) => {
  const status = getProjectStatus(project.id)
  if (!status) return null
  if (status.warmup_status === 'warming_up') return { type: 'warmup', text: 'Накопление' }
  const total = (status.warning_count || 0) + (status.problem_count || 0)
  if (!total) return null
  return {
    type: status.max_severity || 'warning',
    text: `${total} ${total === 1 ? 'отклонение' : total < 5 ? 'отклонения' : 'отклонений'}`,
    count: total,
  }
}

onMounted(async () => {
  document.addEventListener('click', closeActionMenu)
  await fetchProjects()
  await Promise.all([loadProjectMetrics(), fetchCrossProject()])
})

onUnmounted(() => {
  document.removeEventListener('click', closeActionMenu)
})
</script>

<style scoped>
.rows-toolbar {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.6944rem;
  margin-bottom: 1.4rem;
  padding: 0.9rem 1.7361rem;
  margin-left: -1.7361rem;
  margin-right: -1.7361rem;
  background: rgba(245, 247, 249, 0.95);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid transparent;
  transition: border-color 0.15s;
}

:global(.dark) .rows-toolbar {
  background: rgba(35, 38, 55, 0.95);
  border-bottom-color: transparent;
}

.custom-select {
  position: relative;
  display: inline-flex;
  flex-direction: column;
}

.cs-head {
  display: inline-flex;
  align-items: center;
  min-height: 3.1944rem;
  padding: 0.5556rem 1.1806rem;
  font-size: 0.9028rem;
  font-weight: 500;
  color: rgba(0, 0, 0, 0.4);
  background-color: #fff;
  border: 1px solid transparent;
  border-radius: 1.0417rem;
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
  z-index: 99;
  display: flex;
  min-width: 100%;
  flex-direction: column;
  overflow: visible;
  padding: 0;
  background-color: #fff;
  border-radius: 0.5556rem;
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

.cs-option {
  padding: 0.8333rem 1.7361rem 0.8333rem 1.1806rem;
  font-size: 0.9028rem;
  font-weight: 400;
  color: rgba(0, 0, 0, 0.7);
  text-align: left;
  white-space: nowrap;
  cursor: pointer;
  transition: background-color 0.2s;
}

.cs-option:hover {
  background-color: #f5f7f9;
}

.cs-option.selected {
  font-weight: 600;
}

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

.search-wrap {
  position: relative;
}

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

.search-input:focus {
  box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.24), 0 0 0.6944rem rgba(37, 99, 235, 0.15);
}

.search-input::placeholder {
  color: rgba(0, 0, 0, 0.3);
}

.search-icon-circle {
  position: absolute;
  right: 1.1806rem;
  top: 50%;
  display: flex;
  width: 1.1111rem;
  height: 1.1111rem;
  align-items: center;
  justify-content: center;
  background-color: #f5f7f9;
  border-radius: 50%;
  transform: translateY(-50%);
  pointer-events: none;
}

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

.project-sync-meta {
  color: rgba(105, 105, 105, 0.72);
  font-size: 0.7639rem;
  font-weight: 600;
  white-space: nowrap;
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
  animation: rows-spin 0.9s linear infinite;
}

@keyframes rows-spin {
  to { transform: rotate(360deg); }
}

.bulk-btn {
  display: inline-flex;
  min-height: 3.1944rem;
  align-items: center;
  gap: 0.6944rem;
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

.bulk-btn:hover {
  transform: scale(1.02);
}

.bulk-btn:active {
  transform: scale(0.97);
  transition: transform 0s;
}

.bulk-btn__icon {
  display: flex;
  width: 1.5278rem;
  height: 1.5278rem;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 0.4167rem;
  color: #fff;
}

.bulk-btn__icon svg {
  display: block;
  width: 0.9722rem;
  height: 0.9722rem;
}

.view-btn {
  display: flex;
  width: 3.1944rem;
  height: 3.1944rem;
  align-items: center;
  justify-content: center;
  color: #c9c9c9;
  background-color: transparent;
  border: 0;
  border-radius: 0.8333rem;
  cursor: pointer;
  transition: color 0.3s, background-color 0.3s;
}

.view-btn._active {
  color: #5187ff;
  background-color: #fff;
}

.view-btn:not(._active):hover {
  color: #5187ff;
}

.project-title-link {
  display: block;
  max-width: 12rem;
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
  font-size: 0.7639rem;
  line-height: 1;
  text-align: left;
  transition: color 0.2s;
}

.project-id-link:hover {
  color: #2563eb;
}

.project-avatar-row {
  position: relative;
  display: flex;
  width: 2.0833rem;
  height: 2.0833rem;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  overflow: visible;
  border: 0;
  border-radius: 50%;
  background: #e8eef9;
  color: #2563eb;
  cursor: pointer;
  font-size: 0.7639rem;
  font-weight: 700;
  line-height: 1;
  transition: box-shadow 0.2s, transform 0.2s;
}

.project-avatar-row img {
  border-radius: 50%;
  transition: filter 0.2s;
}

.project-avatar-row:hover {
  box-shadow: 0 0 0 0.2083rem rgba(37, 99, 235, 0.12);
  transform: translateY(-1px);
}

.project-avatar-row__edit {
  position: absolute;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  pointer-events: none;
  transition: opacity 0.2s, background-color 0.2s, border-color 0.2s;
}

.project-avatar-row__edit--default {
  right: -0.0694rem;
  bottom: -0.0694rem;
  width: 0.9028rem;
  height: 0.9028rem;
  background: #2563eb;
  color: #fff;
  box-shadow: 0 0 0 0.1042rem #fff;
}

.project-avatar-row__edit--hover {
  inset: 0;
  width: 100%;
  height: 100%;
  border: 1px dashed rgba(107, 114, 128, 0.72);
  background: rgba(243, 244, 246, 0.72);
  color: #6b7280;
  opacity: 0;
  backdrop-filter: blur(1px);
}

.project-avatar-row:hover .project-avatar-row__edit--hover {
  opacity: 1;
}

.project-avatar-row:hover img {
  filter: grayscale(0.12) brightness(0.96);
}

.project-avatar-row__edit svg {
  width: 0.4861rem;
  height: 0.4861rem;
}

.project-avatar-row__edit--hover svg {
  width: 0.8333rem;
  height: 0.8333rem;
}

:global(.dark) .cs-head,
:global(.darkmode) .cs-head,
:global(.dark) .cs-list,
:global(.darkmode) .cs-list {
  background-color: #2c2f3d;
  color: rgba(255, 255, 255, 0.66);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.08);
}

:global(.dark) .custom-select.open .cs-head,
:global(.darkmode) .custom-select.open .cs-head {
  border-color: rgba(255, 255, 255, 0.14);
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
  stroke: rgba(255, 255, 255, 0.68);
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

:global(.dark) .search-input:focus,
:global(.darkmode) .search-input:focus {
  box-shadow: inset 0 0 0 1px rgba(74, 122, 255, 0.34), 0 0 0.6944rem rgba(37, 99, 235, 0.18);
}

:global(.dark) .view-btn,
:global(.darkmode) .view-btn {
  color: rgba(255, 255, 255, 0.34);
}

:global(.dark) .view-btn._active,
:global(.darkmode) .view-btn._active {
  color: #67a8ff;
  background-color: rgba(74, 122, 255, 0.14);
}

:global(.dark) .view-btn:not(._active):hover,
:global(.darkmode) .view-btn:not(._active):hover {
  color: #67a8ff;
  background-color: rgba(255, 255, 255, 0.06);
}

.project-search::placeholder {
  color: #ababab !important;
  -webkit-text-fill-color: #ababab !important;
  font: 400 0.9028rem/130% Inter, sans-serif;
  opacity: 1;
  transition: color 0.5s;
}

.project-search:focus::placeholder {
  color: rgba(171, 171, 171, 0.45) !important;
  -webkit-text-fill-color: rgba(171, 171, 171, 0.45) !important;
}

.dark .project-search::placeholder {
  color: rgba(255, 255, 255, 0.4);
}

.project-rows-table th,
.project-rows-table td {
  border-bottom: 1px solid #eceff3 !important;
}

.dark .project-rows-table th,
.dark .project-rows-table td {
  border-bottom-color: rgba(255, 255, 255, 0.12) !important;
}

.detector-row-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.1389rem 0.4167rem;
  border-radius: 0.2083rem;
  font-size: 0.7639rem;
  font-weight: 600;
  white-space: nowrap;
}
.detector-row-badge--warning {
  background: rgba(251, 191, 36, 0.12);
  color: #92400e;
}
.detector-row-badge--problem {
  background: rgba(239, 68, 68, 0.12);
  color: #dc2626;
}
.detector-row-badge--warmup {
  background: rgba(59, 130, 246, 0.1);
  color: #1e40af;
}

:global(.dark) .detector-row-badge--warning,
:global(.darkmode) .detector-row-badge--warning {
  background: rgba(251, 191, 36, 0.15);
  color: #fbbf24;
}
:global(.dark) .detector-row-badge--problem,
:global(.darkmode) .detector-row-badge--problem {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}
:global(.dark) .detector-row-badge--warmup,
:global(.darkmode) .detector-row-badge--warmup {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
}
</style>
