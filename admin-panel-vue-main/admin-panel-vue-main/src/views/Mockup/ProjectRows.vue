<template>
  <div class="admirra-page-wrapper">
    <section class="main-section">
      <div class="py-4 mb-3">
        <h3 class="heading-3">{{ title }}</h3>
      </div>
      <div class="row gy-3 mb-5">
        <div class="col-12 col-md">
          <div class="row gy-3">
            <div v-for="(filter, idx) in filters" :key="idx" class="col-auto">
              <select class="wide" @change="$emit('filter-change', { filter, value: $event.target.value })">
                <option v-for="opt in filter.options" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
              </select>
            </div>
            <div class="col-12 col-sm-auto">
              <div class="input-item">
                <input class="input _search-project" type="text" :placeholder="searchPlaceholder" @input="$emit('search', $event.target.value)" />
                <div class="input-icon">
                  <svg class="_stroke"><use :href="searchIcon"></use></svg>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="col-12 col-md-auto">
          <div class="row g-3">
            <div class="col-auto">
              <button class="btn _primary" @click="$emit('bulk-edit')">
                <div class="btn__inner">
                  <span class="btn__text">{{ bulkEditLabel }}</span>
                  <div class="btn__icon">
                    <svg class="_stroke"><use :href="editIcon"></use></svg>
                  </div>
                </div>
              </button>
            </div>
            <div class="col-auto ms-auto">
              <div class="row">
                <div class="col-auto">
                  <button :class="['btn-ico', { _active: viewType === 'grid' }]" @click="$emit('change-view', 'grid')">
                    <svg class="_stroke"><use :href="gridIcon"></use></svg>
                  </button>
                </div>
                <div class="col-auto">
                  <button :class="['btn-ico', { _active: viewType === 'rows' }]" @click="$emit('change-view', 'rows')">
                    <svg class="_stroke"><use :href="rowsIcon"></use></svg>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="bg-white radius-base py-5 mb-5">
        <div class="table-container">
          <table>
            <thead>
              <tr class="gray56">
                <th class="bb-light px-3 pb-3">
                  <div class="ps-4">
                    <label class="choise-checkbox">
                      <input class="choise-checkbox__input" type="checkbox" @change="$emit('select-all', $event.target.checked)" />
                      <span class="choise-checkbox__box">
                        <svg><use :href="checkIcon"></use></svg>
                      </span>
                    </label>
                  </div>
                </th>
                <th v-for="head in tableHeaders" :key="head" class="bb-light px-3 pb-3">{{ head }}</th>
                <th class="bb-light px-3 pb-3">Действия</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="project in projects" :key="project.id">
                <td class="bb-light px-3 py-5">
                  <div class="ps-4">
                    <label class="choise-checkbox">
                      <input class="choise-checkbox__input" type="checkbox" :checked="project.selected" @change="$emit('select-project', { project, selected: $event.target.checked })" />
                      <span class="choise-checkbox__box">
                        <svg><use :href="checkIcon"></use></svg>
                      </span>
                    </label>
                  </div>
                </td>
                <td class="bb-light px-3 py-5">
                  <div class="d-flex">
                    <div class="avatar-30x30 align-self-center">
                      <img class="img-cover" :src="project.avatar" alt="#" />
                    </div>
                    <div class="ps-4 align-self-center">
                      <h4 class="mb-1 gray">{{ project.title }}</h4>
                      <p class="text-11 gray56">ID:&nbsp;{{ project.id }}</p>
                    </div>
                  </div>
                </td>
                <td class="bb-light px-3 py-5">
                  <div class="d-flex">
                    <img v-for="channel in project.channels" :key="channel.id" class="me-2" width="22" :src="channel.icon" alt="#" />
                  </div>
                </td>
                <td class="bb-light px-3 py-5">
                  <div class="text-15 mb-2">{{ project.impressions }}</div>
                  <div v-if="project.trend > 0" class="badge _sm _success">
                    <span class="weight-600">+{{ project.trend }}%</span>
                  </div>
                </td>
                <!-- Другие колонки аналогично -->
                <td class="bb-light px-3 py-5">
                   <div class="text-15 mb-2">{{ project.clicks }}</div>
                </td>
                <td class="bb-light px-3 py-5">
                   <div class="text-15 mb-2"><b>{{ project.expenses }}&nbsp;₽</b></div>
                </td>
                <td class="bb-light px-3 py-5">
                   <div class="text-15 mb-2">{{ project.leads }}</div>
                </td>
                <td class="bb-light px-3 py-5">
                   <div class="text-15 mb-2">{{ project.cpc }}</div>
                </td>
                <td class="bb-light px-3 py-5">
                   <div class="text-15 mb-2">{{ project.cpa }}</div>
                </td>
                <td class="bb-light px-3 py-5">
                  <div class="h-100 bg-orangelight radius p-3">
                    <div class="h-100 d-flex align-items-center justify-content-center">
                      <div class="px-3 c71663e">Баланс</div>
                      <div class="badge-white c71663e">{{ project.budgetRemaining }}₽</div>
                    </div>
                  </div>
                </td>
                <td class="bb-light px-3 py-5">
                  <div :class="['badge', project.statusClass]">
                    <span class="weight-600">{{ project.status }}</span>
                  </div>
                </td>
                <td class="bb-light px-3 py-5">
                  <div class="text-15">{{ project.createdAt }}</div>
                </td>
                <td class="bb-light px-3 py-5">
                  <div class="dropdown">
                    <button class="dropdown-head _no-style" @click="$emit('open-actions', project)">
                      <div class="action-btn-ui">
                        <svg><use :href="dottsIcon"></use></svg>
                      </div>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="row pt-5 px-5 align-items-end">
          <div class="col col-sm-4">
            <div class="row gy-2 align-items-center">
              <div class="col-12">
                <div class="gray weight-500">{{ itemsPerPageLabel }}</div>
              </div>
              <div class="col-auto">
                <select class="select-outline wide _sm _dropdown-bottom" @change="$emit('change-page-size', $event.target.value)">
                  <option v-for="size in pageSizes" :key="size" :value="size">{{ size }}</option>
                </select>
              </div>
            </div>
          </div>
          <div class="col-12 col-sm-4 order-1 order-sm-0">
            <div class="py-4 gray weight-500 text-center">{{ paginationInfo }}</div>
          </div>
          <div class="col-auto col-sm-4 d-flex">
            <div class="ms-auto">
              <button class="btn-nav" @click="$emit('prev-page')">
                <svg><use :href="prevIcon"></use></svg>
              </button>
              <span>&nbsp;</span>
              <button class="btn-nav" @click="$emit('next-page')">
                <svg><use :href="nextIcon"></use></svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { onMounted, nextTick } from 'vue'

defineProps({
  title: { type: String, default: 'Проекты' },
  searchPlaceholder: { type: String, default: 'Поиск по проектам, номерам или доменам' },
  bulkEditLabel: { type: String, default: 'Массовое редактирование' },
  itemsPerPageLabel: { type: String, default: 'Элементов на странице:' },
  paginationInfo: { type: String, default: '1-3 из 3' },
  viewType: { type: String, default: 'rows' },
  filters: {
    type: Array,
    default: () => [
      { id: 'type', options: [{ value: 'all', label: 'Все' }] },
      { id: 'period', options: [{ value: '2w', label: '2 недели' }] }
    ]
  },
  tableHeaders: {
    type: Array,
    default: () => ['Проект', 'Интеграции', 'Показы', 'Клики', 'Расходы', 'Лиды', 'CPC', 'CPA', 'Актуальный баланс в ЛК:', 'Статус', 'Дата создания']
  },
  projects: {
    type: Array,
    default: () => []
  },
  pageSizes: { type: Array, default: () => [10, 20, 30] },
  searchIcon: { type: String, default: '/admirra/img/svg/sprite.svg#search' },
  editIcon: { type: String, default: '/admirra/img/svg/sprite.svg#edit' },
  gridIcon: { type: String, default: '/admirra/img/svg/sprite.svg#grid' },
  rowsIcon: { type: String, default: '/admirra/img/svg/sprite.svg#rows' },
  checkIcon: { type: String, default: '/admirra/img/svg/sprite.svg#check' },
  dottsIcon: { type: String, default: '/admirra/img/svg/sprite.svg#dotts' },
  prevIcon: { type: String, default: '/admirra/img/svg/sprite.svg#prev' },
  nextIcon: { type: String, default: '/admirra/img/svg/sprite.svg#next' }
})

defineEmits(['filter-change', 'search', 'bulk-edit', 'change-view', 'select-all', 'select-project', 'open-actions', 'change-page-size', 'prev-page', 'next-page'])

onMounted(() => {
  nextTick(() => {
    if (window.jQuery) {
      window.jQuery('select').niceSelect()
    }
  })
})
</script>

<style scoped>
.admirra-page-wrapper {
  /* Scoped styles */
}
.btn-nav {
  background: none;
  border: none;
  cursor: pointer;
}
</style>
