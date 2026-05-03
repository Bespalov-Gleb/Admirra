<template>
  <div class="relative z-[2] flex min-h-full flex-col overflow-hidden px-[25px] py-[30px]">
    <div class="pt-[15px] pb-[15px] mb-[10px]">
      <h3 class="text-[30px] font-semibold leading-none text-[#171717] dark:text-white">Проекты</h3>
    </div>

    <div class="mb-[30px] flex flex-wrap items-center justify-between gap-[10px]">
      <div class="flex flex-wrap items-center gap-[10px]">
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

        <div class="custom-select" :class="{ open: openSelect === 'period' }" v-click-outside="() => closeSelect('period')">
          <button type="button" class="cs-head dark:!border-white/10 dark:!bg-[#2C2F3D] dark:!text-white/70 dark:!shadow-[inset_0_0_0_1px_rgba(255,255,255,0.08)]" @click="toggleSelect('period')">
            <span class="cs-current">{{ periodLabel }}</span>
            <span class="cs-arrow dark:!bg-white/10">
              <svg width="5" height="4" viewBox="0 0 9 6" fill="none"><path d="M0.5 1L4.5 5L8.5 1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </span>
          </button>
          <div class="cs-list dark:!bg-[#2C2F3D] dark:!shadow-[0_0_0_1px_rgba(255,255,255,0.08)]">
            <button
              v-for="option in periodOptions"
              :key="option.value"
              type="button"
              class="cs-option dark:!text-white/70 dark:hover:!bg-white/5"
              :class="{ selected: periodDays === option.value }"
              @click="selectPeriod(option.value)"
            >{{ option.label }}</button>
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

      <div class="flex items-center gap-[10px]">
        <button type="button" class="bulk-btn" @click="openMassEdit">
          <span>Массовое редактирование</span>
          <span class="bulk-btn__icon">
            <svg width="12" height="12" viewBox="0 0 14 14" fill="none">
              <path d="M1 13L5.5 8.5M13 1L8.5 5.5M5.5 8.5L8.5 5.5" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M2 12L1 13" stroke="white" stroke-width="1.5" stroke-linecap="round"/>
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
    <div v-if="isLoading" class="py-16 text-center text-[14px] text-gray-400">Загрузка проектов...</div>

    <!-- Empty -->
    <div v-else-if="filteredProjects.length === 0" class="py-16 text-center text-[14px] text-gray-400">
      {{ search ? 'Проекты не найдены' : 'У вас пока нет проектов' }}
    </div>

    <div v-else class="mb-[30px] overflow-visible rounded-[15px] bg-white py-[30px] dark:bg-[#2C2F3D]">
      <div class="overflow-x-auto">
        <table class="project-rows-table w-full table-auto border-collapse">
          <thead>
            <tr class="text-[13px] font-normal text-[rgba(105,105,105,0.56)] dark:text-white/45">
              <th class="border-b border-[rgba(0,0,0,0.05)] px-[10px] pb-[10px] text-left align-middle font-normal dark:border-white/10">
                <label class="ml-[15px] flex h-5 w-5 cursor-pointer items-center justify-center">
                  <input type="checkbox" class="peer sr-only" :checked="allRowsSelected" @change="toggleSelectAllRows" />
                  <span class="relative inline-block h-5 w-5 rounded-[3px] border border-[#f5f7f9] bg-[#f5f7f9] transition duration-300 peer-focus:shadow-[0_0_0_1px_rgba(0,123,255,1)] peer-checked:border-[#2563eb] peer-checked:[&>svg]:opacity-100 dark:border-white/15 dark:bg-white/10">
                    <svg class="absolute left-1/2 top-1/2 h-[9px] w-[9px] -translate-x-1/2 -translate-y-1/2 fill-[#2563eb] opacity-0 transition duration-300" viewBox="0 0 12 10">
                      <path d="M4.2 9.2.4 5.4l1.4-1.4 2.4 2.4L10.2.3l1.4 1.4-7.4 7.5Z" />
                    </svg>
                  </span>
                </label>
              </th>
              <th class="border-b border-[rgba(0,0,0,0.05)] px-[10px] pb-[10px] text-left align-middle font-normal dark:border-white/10">Проект</th>
              <th class="border-b border-[rgba(0,0,0,0.05)] px-[10px] pb-[10px] text-left align-middle font-normal dark:border-white/10">Интеграции</th>
              <th class="border-b border-[rgba(0,0,0,0.05)] px-[10px] pb-[10px] text-left align-middle font-normal dark:border-white/10">Показы</th>
              <th class="border-b border-[rgba(0,0,0,0.05)] px-[10px] pb-[10px] text-left align-middle font-normal dark:border-white/10">Клики</th>
              <th class="border-b border-[rgba(0,0,0,0.05)] px-[10px] pb-[10px] text-left align-middle font-normal dark:border-white/10">Расходы</th>
              <th class="border-b border-[rgba(0,0,0,0.05)] px-[10px] pb-[10px] text-left align-middle font-normal dark:border-white/10">Лиды</th>
              <th class="border-b border-[rgba(0,0,0,0.05)] px-[10px] pb-[10px] text-left align-middle font-normal dark:border-white/10">CPC</th>
              <th class="border-b border-[rgba(0,0,0,0.05)] px-[10px] pb-[10px] text-left align-middle font-normal dark:border-white/10">CPA</th>
              <th class="border-b border-[rgba(0,0,0,0.05)] px-[10px] pb-[10px] text-left align-middle font-normal dark:border-white/10">Актуальный баланс&nbsp;в&nbsp;ЛК:</th>
              <th class="border-b border-[rgba(0,0,0,0.05)] px-[10px] pb-[10px] text-left align-middle font-normal dark:border-white/10">Статус</th>
              <th class="border-b border-[rgba(0,0,0,0.05)] px-[10px] pb-[10px] text-left align-middle font-normal dark:border-white/10">Дата&nbsp;создания</th>
              <th class="border-b border-[rgba(0,0,0,0.05)] px-[10px] pb-[10px] text-left align-middle font-normal dark:border-white/10">Действия</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="project in paginatedProjects"
              :key="project.id"
              class="text-[#444] transition hover:bg-[#f8fafc] dark:text-white dark:hover:bg-white/5"
            >
              <td class="border-b border-[rgba(0,0,0,0.05)] px-[10px] py-[30px] align-middle dark:border-white/10">
                <label class="ml-[15px] flex h-5 w-5 cursor-pointer items-center justify-center">
                  <input type="checkbox" class="peer sr-only" :checked="selectedProjectIds.includes(project.id)" @change="toggleProjectRow(project.id)" />
                  <span class="relative inline-block h-5 w-5 rounded-[3px] border border-[#f5f7f9] bg-[#f5f7f9] transition duration-300 peer-focus:shadow-[0_0_0_1px_rgba(0,123,255,1)] peer-checked:border-[#2563eb] peer-checked:[&>svg]:opacity-100 dark:border-white/15 dark:bg-white/10">
                    <svg class="absolute left-1/2 top-1/2 h-[9px] w-[9px] -translate-x-1/2 -translate-y-1/2 fill-[#2563eb] opacity-0 transition duration-300" viewBox="0 0 12 10">
                      <path d="M4.2 9.2.4 5.4l1.4-1.4 2.4 2.4L10.2.3l1.4 1.4-7.4 7.5Z" />
                    </svg>
                  </span>
                </label>
              </td>
              <td class="border-b border-[rgba(0,0,0,0.05)] px-[10px] py-[30px] align-middle dark:border-white/10">
                <div class="flex items-center">
                  <div class="flex h-[30px] w-[30px] shrink-0 items-center justify-center overflow-hidden rounded-full bg-[#e8eef9]">
                    <img class="h-full w-full object-cover" src="/admirra/img/avatars/avatar-40x40.png" alt="" />
                  </div>
                  <div class="pl-[15px]">
                    <h4 class="mb-[5px] text-[13px] font-normal leading-[130%] text-[#696969] dark:text-white">{{ project.name }}</h4>
                    <p class="text-[11px] leading-none text-[rgba(105,105,105,0.56)] dark:text-white/45">ID:&nbsp;{{ shortId(project.id) }}</p>
                  </div>
                </div>
              </td>
              <td class="border-b border-[rgba(0,0,0,0.05)] px-[10px] py-[30px] align-middle dark:border-white/10">
                <div class="flex items-center gap-2">
                  <img v-if="hasPlatform(project, 'YANDEX')" width="22" src="/admirra/img/icons/yandex-direct.png" alt="Yandex" />
                  <img v-if="hasPlatform(project, 'VK')" width="22" src="/admirra/img/icons/vk-ads.png" alt="VK" />
                  <span v-if="!project.integrations?.length" class="text-[13px] text-gray-400">—</span>
                </div>
              </td>
              <td
                v-for="cell in metricCells(project)"
                :key="cell.key"
                class="border-b border-[rgba(0,0,0,0.05)] px-[10px] py-[30px] align-middle dark:border-white/10"
              >
                <div :class="['mb-[5px] text-[15px] leading-[130%]', cell.bold ? 'font-bold' : 'font-normal']">{{ cell.value }}</div>
                <div :class="trendBadgeClass(getProjectMetric(project.id), cell.key)">
                  <span class="font-semibold">{{ trendText(getProjectMetric(project.id), cell.key) }}</span>
                </div>
              </td>
              <td class="border-b border-[rgba(0,0,0,0.05)] px-[10px] py-[30px] align-middle dark:border-white/10">
                <div :class="balanceCardClass(project)">
                  <div class="flex h-full items-center justify-center">
                    <img width="18" :src="balancePlatform(project).icon" :alt="balancePlatform(project).label" />
                    <div :class="['px-[10px] text-[13px]', balancePlatform(project).textClass]">{{ balancePlatform(project).label }}</div>
                    <div :class="['inline-flex min-h-[22px] items-center rounded-full bg-white px-[8px] text-center text-[11px] dark:bg-white/10', balancePlatform(project).textClass]">
                      {{ formatMoney(getProjectMetric(project.id).balance) }}
                    </div>
                  </div>
                </div>
              </td>
              <td class="border-b border-[rgba(0,0,0,0.05)] px-[10px] py-[30px] align-middle dark:border-white/10">
                <span :class="statusBadgeClass(project)">
                  {{ project.integrations?.some(i => i.is_active) ? 'Активен' : 'Неактивен' }}
                </span>
              </td>
              <td class="border-b border-[rgba(0,0,0,0.05)] px-[10px] py-[30px] align-middle dark:border-white/10">
                <div class="text-[15px] leading-[130%]">{{ formatDate(project.created_at || project.createdAt) }}</div>
              </td>
              <td class="relative border-b border-[rgba(0,0,0,0.05)] px-[10px] py-[30px] align-middle dark:border-white/10">
                <button
                  type="button"
                  class="relative h-[25px] w-[32px] rounded-[3px] bg-[#f5f7f9]/60 transition hover:bg-[#ecf3fe] dark:bg-white/10"
                  @click.stop="toggleActionMenu(project, $event)"
                  aria-label="Действия"
                >
                  <svg class="absolute left-1/2 top-1/2 h-[5px] w-[19px] -translate-x-1/2 -translate-y-1/2 fill-[#d9d9d9]" viewBox="0 0 19 5">
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
      <div class="relative flex min-h-[70px] items-end px-[30px] pt-[30px]">
        <div class="min-w-0 pb-[15px]">
          <div class="mb-[10px] text-[13px] font-medium leading-[130%] text-[#696969] dark:text-white/70">Элементов на&nbsp;странице:</div>
          <div class="relative inline-block">
            <button
              type="button"
              class="inline-flex min-h-[30px] items-center rounded-[6px] border border-[rgba(168,169,170,0.32)] bg-transparent px-[12px] py-[5px] text-[13px] font-medium leading-[130%] text-[rgba(105,105,105,0.6)] transition duration-200 focus:border-black/10 focus:outline-none dark:text-white/60"
              @click="toggleSelect('pageSize')"
            >
              <span>{{ itemsPerPage }}</span>
              <span :class="['ml-[12px] flex shrink-0 items-center justify-center transition-transform duration-300', openSelect === 'pageSize' ? 'rotate-180' : '']">
                <svg class="h-[9px] w-[9px] fill-[rgba(105,105,105,0.6)] dark:fill-white/60" viewBox="0 0 10 6">
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

        <div class="absolute bottom-0 left-1/2 -translate-x-1/2 py-[15px] text-center text-[13px] font-medium leading-[130%] text-[#696969] dark:text-white/70">
          {{ paginationStart }}-{{ paginationEnd }} из {{ filteredProjects.length }}
        </div>

        <div class="ml-auto flex pb-[15px]">
          <button
            type="button"
            class="inline-flex h-[30px] w-[30px] items-center justify-center rounded-[6px] border border-[rgba(168,169,170,0.32)] text-[rgba(105,105,105,0.56)] transition duration-300 hover:border-[#1f9de4] hover:text-[#1f9de4]"
            aria-label="Предыдущая страница"
            @click="currentPage = Math.max(1, currentPage - 1)"
          >
            <svg class="h-2 w-2 fill-current" viewBox="0 0 8 8">
              <path d="M5.7.7 2.4 4l3.3 3.3-1 1L.4 4 4.7-.3l1 1Z" />
            </svg>
          </button>
          <span class="w-[4px]"></span>
          <button
            type="button"
            class="inline-flex h-[30px] w-[30px] items-center justify-center rounded-[6px] border border-[rgba(168,169,170,0.32)] text-[rgba(105,105,105,0.56)] transition duration-300 hover:border-[#1f9de4] hover:text-[#1f9de4]"
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
      class="fixed z-[1200] w-[220px] rounded-[12px] bg-white py-3 shadow-[0_0_15px_rgba(0,0,0,.1)] dark:bg-[#2C2F3D]"
      :style="{ top: `${actionMenuPosition.top}px`, left: `${actionMenuPosition.left}px` }"
      @click.stop
    >
      <button class="flex min-h-[43px] w-full items-center px-[15px] text-left text-[14px] text-[#444] transition hover:bg-[#f5f7f9] dark:text-white dark:hover:bg-white/10" @click="openProject(activeActionProject)">
        <span class="mr-3 flex w-[30px] justify-center text-[#2563eb]">
          <svg class="h-[14px] w-[18px] fill-none stroke-current" viewBox="0 0 24 18" stroke-width="1.7"><path d="M1.5 9s3.8-7 10.5-7 10.5 7 10.5 7-3.8 7-10.5 7S1.5 9 1.5 9Z"/><circle cx="12" cy="9" r="3"/></svg>
        </span>
        Просмотр
      </button>
      <button class="flex min-h-[43px] w-full items-center px-[15px] text-left text-[14px] text-[#444] transition hover:bg-[#f5f7f9] dark:text-white dark:hover:bg-white/10" @click="editProject(activeActionProject)">
        <span class="mr-3 flex w-[30px] justify-center text-[#2563eb]">
          <svg class="h-[18px] w-[18px] fill-none stroke-current" viewBox="0 0 24 24" stroke-width="1.7"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4 11.5-11.5Z"/></svg>
        </span>
        Редактировать
      </button>
      <button class="flex min-h-[43px] w-full items-center px-[15px] text-left text-[14px] text-[#ec3434] transition hover:bg-[#fff0f1] dark:hover:bg-white/10" @click="requestDeleteProject(activeActionProject)">
        <span class="mr-3 flex w-[30px] justify-center">
          <svg class="h-[17px] w-[17px] fill-none stroke-current" viewBox="0 0 24 24" stroke-width="1.7"><path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v5M14 11v5"/></svg>
        </span>
        Удалить
      </button>
    </div>

    <!-- MODAL: Mass edit -->
    <div
      v-if="massEditOpen"
      class="fixed inset-0 bg-black/50 z-[1000] flex items-center justify-center p-4"
      @click.self="massEditOpen = false"
    >
      <div class="bg-white dark:bg-[#2C2F3D] rounded-2xl p-6 w-full max-w-[480px] border border-black/5 dark:border-white/10">
        <h4 class="text-[18px] font-bold text-gray-800 dark:text-gray-100 mb-2">Массовое редактирование</h4>
        <p class="text-[14px] text-gray-400 mb-3">Выбрано проектов: {{ selectedProjectIds.length }}. Укажите новое описание — оно будет записано во все отмеченные проекты.</p>
        <ul class="text-[13px] text-gray-400 mb-3 pl-4 list-disc">
          <li v-for="id in selectedProjectIdList" :key="id">{{ projectNameById(id) }}</li>
        </ul>
        <textarea
          v-model="massEditDescription"
          class="w-full min-h-[96px] px-4 py-3 rounded-xl border border-black/10 dark:border-white/15 bg-transparent text-[14px] text-gray-700 dark:text-gray-200 placeholder-gray-400 resize-y outline-none focus:border-[#2563eb] focus:ring-2 focus:ring-[#2563eb]/15 mb-4"
          rows="4"
          placeholder="Описание проекта"
        />
        <div class="flex flex-wrap gap-3">
          <button
            class="h-[44px] px-5 rounded-xl bg-[#2563eb] text-white text-[14px] font-medium hover:bg-[#1d4ed8] disabled:opacity-50 transition-colors"
            type="button"
            :disabled="massSaving"
            @click="applyMassDescription"
          >{{ massSaving ? 'Сохранение...' : 'Применить описание' }}</button>
          <button
            class="h-[44px] px-5 rounded-xl border border-black/10 dark:border-white/15 bg-white dark:bg-white/5 text-[14px] text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-white/10 disabled:opacity-50 transition-colors"
            type="button"
            :disabled="massSaving"
            @click="massEditOpen = false"
          >Закрыть</button>
        </div>
      </div>
    </div>

    <!-- MODAL: Delete confirm -->
    <div
      v-if="deleteTarget"
      class="fixed inset-0 bg-black/50 z-[1000] flex items-center justify-center p-4"
    >
      <div class="bg-white dark:bg-[#2C2F3D] rounded-2xl p-6 w-full max-w-[400px] border border-black/5 dark:border-white/10">
        <h4 class="text-[18px] font-bold text-gray-800 dark:text-gray-100 mb-3">Удалить проект?</h4>
        <p class="text-[14px] text-gray-400 mb-5">Проект «{{ deleteTarget.name }}» и все его данные будут удалены безвозвратно.</p>
        <div class="flex gap-3">
          <button
            class="h-[44px] px-5 rounded-xl bg-[#2563eb] text-white text-[14px] font-medium hover:bg-[#1d4ed8] disabled:opacity-50 transition-colors"
            :disabled="deleting"
            @click="doDelete"
          >{{ deleting ? 'Удаление...' : 'Удалить' }}</button>
          <button
            class="h-[44px] px-5 rounded-xl border border-black/10 dark:border-white/15 bg-white dark:bg-white/5 text-[14px] text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-white/10 transition-colors"
            @click="deleteTarget = null"
          >Отмена</button>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api/axios'
import { useProjects } from '../../composables/useProjects'
import { useToaster } from '../../composables/useToaster'

const router = useRouter()
const { projects, isLoading, fetchProjects, setCurrentProject } = useProjects()
const toaster = useToaster()

const periodDays = ref(14)
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
const massEditDescription = ref('')
const massSaving = ref(false)
const activeActionProjectId = ref(null)
const activeActionProject = ref(null)
const actionMenuPosition = ref({ top: 0, left: 0 })

const projectFilterOptions = [
  { value: 'all', label: 'Все' },
  { value: 'active', label: 'Активные' },
  { value: 'inactive', label: 'Неактивные' }
]

const periodOptions = [
  { value: 14, label: '2 недели' },
  { value: 21, label: '3 недели' },
  { value: 28, label: '4 недели' },
  { value: 35, label: '5 недель' }
]

const itemsPerPageOptions = [10, 20, 30]

const projectFilterLabel = computed(() => {
  return projectFilterOptions.find((option) => option.value === projectFilter.value)?.label || 'Все'
})

const periodLabel = computed(() => {
  return periodOptions.find((option) => option.value === periodDays.value)?.label || '2 недели'
})

const toggleSelect = (name) => {
  openSelect.value = openSelect.value === name ? null : name
}

const closeSelect = (name) => {
  if (openSelect.value === name) openSelect.value = null
}

const selectDropdownClass = (name) => [
  'absolute left-0 top-full z-30 mt-1 flex min-w-[230px] origin-top flex-col overflow-hidden rounded-[8px] bg-white p-0 shadow-[0_0_0_1px_rgba(68,68,68,.1)] transition-[opacity,transform] duration-200 ease-[cubic-bezier(.5,0,0,1.25)] dark:bg-[#3a3c49]',
  openSelect.value === name
    ? 'pointer-events-auto scale-100 translate-y-0 opacity-100'
    : 'pointer-events-none scale-75 -translate-y-[21px] opacity-0'
]

const selectOptionClass = (selected) => [
  'px-[17px] py-3 text-left text-[13px] text-[#696969] transition duration-200 hover:bg-[#f5f7f9] dark:text-white/75 dark:hover:bg-white/5',
  selected ? 'bg-[#f5f7f9] font-bold dark:bg-white/5' : 'bg-transparent font-medium'
]

const pageSizeDropdownClass = computed(() => [
  'absolute left-0 top-full z-30 mt-1 flex min-w-full origin-top flex-col overflow-hidden rounded-[8px] bg-white p-0 shadow-[0_0_0_1px_rgba(68,68,68,.1)] transition-[opacity,transform] duration-200 ease-[cubic-bezier(.5,0,0,1.25)] dark:bg-[#3a3c49]',
  openSelect.value === 'pageSize'
    ? 'pointer-events-auto scale-100 translate-y-0 opacity-100'
    : 'pointer-events-none scale-75 -translate-y-[21px] opacity-0'
])

const pageSizeOptionClass = (selected) => [
  'px-[12px] py-2 text-left text-[13px] text-[rgba(105,105,105,0.6)] transition duration-200 hover:bg-[#f5f7f9] dark:text-white/60 dark:hover:bg-white/5',
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
  periodDays.value = value
  openSelect.value = null
  await reloadMetrics()
}

const setItemsPerPage = (value) => {
  itemsPerPage.value = value
  currentPage.value = 1
  openSelect.value = null
}

const filteredProjects = computed(() => {
  let list = projects.value
  if (projectFilter.value === 'active') {
    list = list.filter((p) => p.integrations?.some((i) => i.is_active))
  } else if (projectFilter.value === 'inactive') {
    list = list.filter((p) => !p.integrations?.some((i) => i.is_active))
  }
  if (!search.value.trim()) return list
  const q = search.value.toLowerCase()
  return list.filter(p =>
    p.name?.toLowerCase().includes(q) ||
    String(p.id || '').toLowerCase().includes(q)
  )
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

const openMassEdit = () => {
  if (!selectedProjectIds.value.length) {
    toaster.warning('Отметьте один или несколько проектов в таблице.')
    return
  }
  massEditDescription.value = ''
  massEditOpen.value = true
}

const applyMassDescription = async () => {
  if (!selectedProjectIds.value.length) return
  const desc = massEditDescription.value.trim()
  if (!desc) {
    toaster.warning('Введите текст описания — он будет записан во все выбранные проекты.')
    return
  }
  massSaving.value = true
  try {
    await Promise.all(
      selectedProjectIds.value.map((id) =>
        api.put(`clients/${id}`, { description: desc })
      )
    )
    toaster.success(`Описание обновлено для ${selectedProjectIds.value.length} проектов.`)
    massEditOpen.value = false
    await fetchProjects()
    await loadProjectMetrics()
  } catch (err) {
    console.error(err)
    toaster.error(err.response?.data?.detail || 'Не удалось сохранить изменения.')
  } finally {
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

const integrationPlatforms = (project) => {
  const list = (project.integrations || []).map(i => i.platform?.toUpperCase()).filter(Boolean)
  return Array.from(new Set(list))
}

const hasPlatform = (project, platform) => integrationPlatforms(project).includes(platform)

const formatNumber = (num) => new Intl.NumberFormat('ru-RU').format(Number(num || 0))
const formatMoney = (num) => `${new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 2 }).format(Number(num || 0))} ₽`

const trendText = (metric, key) => {
  const trend = Number(metric?.trends?.[key] || 0)
  const sign = trend >= 0 ? '+' : ''
  return `${sign}${trend.toFixed(1)}%`
}

const metricCells = (project) => {
  const m = getProjectMetric(project.id)
  return [
    { key: 'impressions', value: formatNumber(m.impressions) },
    { key: 'clicks', value: formatNumber(m.clicks) },
    { key: 'expenses', value: formatMoney(m.expenses), bold: true },
    { key: 'leads', value: formatNumber(m.leads) },
    { key: 'cpc', value: formatMoney(m.cpc) },
    { key: 'cpa', value: formatMoney(m.cpa) }
  ]
}

const shortId = (id) => {
  const v = String(id || '')
  return v.length > 12 ? `${v.slice(0, 8)}...${v.slice(-4)}` : v || '—'
}

const trendBadgeClass = (metric, key) => {
  const trend = Number(metric?.trends?.[key] || 0)
  return [
    'inline-flex items-center gap-1 rounded-[3px] px-[6px] py-0 text-[11px] font-bold leading-[130%]',
    trend < 0
      ? 'bg-red-500/10 text-red-600 dark:bg-red-500/15 dark:text-red-300'
      : 'bg-[#00ff4e]/10 text-[#16a34a] dark:bg-[#00ff4e]/15 dark:text-[#5ee886]'
  ]
}

const statusBadgeClass = (project) => [
  'inline-flex min-h-[20px] items-center rounded-[3px] px-[6px] py-[6px] text-[11px] font-bold leading-[130%]',
  project.integrations?.some(i => i.is_active)
    ? 'bg-[#00ff4e]/10 text-[#16a34a] dark:bg-[#00ff4e]/15 dark:text-[#5ee886]'
    : 'bg-red-500/10 text-red-600 dark:bg-red-500/15 dark:text-red-300'
]

const balancePlatform = (project) => {
  if (hasPlatform(project, 'VK')) {
    return {
      label: 'VK Ads',
      icon: '/admirra/img/icons/vk-ads.png',
      cardClass: 'bg-[#f0f7ff]',
      darkCardClass: 'dark:bg-[#213652]',
      textClass: 'text-[#2563eb] dark:text-[#8bb7ff]'
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
  return ['h-full rounded-[12px] p-[10px]', platform.cardClass, platform.darkCardClass]
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

const editProject = () => {
  closeActionMenu()
  router.push('/project-card')
}

const requestDeleteProject = (project) => {
  deleteTarget.value = project
  closeActionMenu()
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

onMounted(async () => {
  document.addEventListener('click', closeActionMenu)
  await fetchProjects()
  await loadProjectMetrics()
})

onUnmounted(() => {
  document.removeEventListener('click', closeActionMenu)
})
</script>

<style scoped>
.custom-select {
  position: relative;
  display: inline-flex;
  flex-direction: column;
}

.cs-head {
  display: inline-flex;
  align-items: center;
  min-height: 46px;
  padding: 8px 17px;
  font-size: 13px;
  font-weight: 500;
  color: rgba(0, 0, 0, 0.4);
  background-color: #fff;
  border: 1px solid transparent;
  border-radius: 15px;
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
  z-index: 99;
  display: flex;
  min-width: 100%;
  flex-direction: column;
  overflow: hidden;
  padding: 0;
  background-color: #fff;
  border-radius: 8px;
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

.cs-option {
  padding: 12px 25px 12px 17px;
  font-size: 13px;
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

.search-wrap {
  position: relative;
}

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

.search-input:focus {
  box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.24), 0 0 10px rgba(37, 99, 235, 0.15);
}

.search-input::placeholder {
  color: rgba(0, 0, 0, 0.3);
}

.search-icon-circle {
  position: absolute;
  right: 17px;
  top: 50%;
  display: flex;
  width: 16px;
  height: 16px;
  align-items: center;
  justify-content: center;
  background-color: #f5f7f9;
  border-radius: 50%;
  transform: translateY(-50%);
  pointer-events: none;
}

.bulk-btn {
  display: inline-flex;
  min-height: 46px;
  align-items: center;
  gap: 10px;
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

.bulk-btn:hover {
  transform: scale(1.02);
}

.bulk-btn:active {
  transform: scale(0.97);
  transition: transform 0s;
}

.bulk-btn__icon {
  display: flex;
  width: 22px;
  height: 22px;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 6px;
}

.view-btn {
  display: flex;
  width: 46px;
  height: 46px;
  align-items: center;
  justify-content: center;
  color: #c9c9c9;
  background-color: transparent;
  border: 0;
  border-radius: 12px;
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
  box-shadow: inset 0 0 0 1px rgba(74, 122, 255, 0.34), 0 0 10px rgba(37, 99, 235, 0.18);
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
  font: 400 13px/130% Inter, sans-serif;
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
</style>
