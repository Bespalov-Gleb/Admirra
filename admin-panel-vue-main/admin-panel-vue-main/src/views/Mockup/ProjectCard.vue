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
                <input 
                  class="input _search-project" 
                  type="text" 
                  :placeholder="searchPlaceholder" 
                  @input="$emit('search', $event.target.value)"
                />
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
      <div class="row gy-4 mb-5">
        <div v-for="(project, idx) in projects" :key="idx" class="col-12 col-xxl-6">
          <div class="h-100 bg-white radius-base">
            <div class="p-5">
              <div class="row pb-3 mb-4">
                <div class="col">
                  <div class="d-flex">
                    <div class="avatar-40x40 align-self-center">
                      <img class="img-cover" :src="project.avatar" alt="#" />
                    </div>
                    <div class="ps-4 align-self-center">
                      <h4 class="mb-1 text-15 gray">{{ project.name }}</h4>
                      <p class="gray56">{{ project.description }}</p>
                    </div>
                  </div>
                </div>
                <div class="col-auto">
                  <button class="circle-btn" @click="$emit('open-project', project)">
                    <svg><use :href="upIcon"></use></svg>
                  </button>
                </div>
              </div>
              <div class="row g-4">
                <div v-for="(stat, sIdx) in project.stats" :key="sIdx" class="col-12 col-sm-6 col-md-4">
                  <div class="d-flex flex-column h-100 p-4 bg-azurelight radius lh-110">
                    <div class="d-flex pb-2 mb-4">
                      <div class="iconbox">
                        <svg><use :href="stat.icon"></use></svg>
                      </div>
                      <div class="ps-3 align-self-center">
                        <h4 class="mb-1 gray">{{ stat.label }}</h4>
                        <p class="text-12 gray56">{{ stat.subtitle }}</p>
                      </div>
                    </div>
                    <div class="d-flex align-items-center mt-auto">
                      <b class="text-20 me-3">{{ stat.value }}</b>
                      <div :class="['badge', stat.badgeClass]">
                        <svg class="badge__icon"><use :href="stat.badgeIcon"></use></svg>
                        {{ stat.change }}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <hr class="hr-line" />
            <div class="p-5">
              <div class="gray mb-3">{{ balanceLabel }}</div>
              <div class="row g-4">
                <div v-for="(balance, bIdx) in project.balances" :key="bIdx" class="col-12 col-sm-6 col-md-4">
                  <div :class="['h-100 radius p-3', balance.bgClass]">
                    <div class="h-100 d-flex align-items-center justify-content-center">
                      <img width="18" :src="balance.icon" alt="#" />
                      <div :class="['px-3', balance.textClass]">{{ balance.name }}</div>
                      <div :class="['badge-white', balance.textClass]">{{ balance.value }}</div>
                    </div>
                  </div>
                </div>
              </div>
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
  balanceLabel: { type: String, default: 'Актуальный баланс в ЛК:' },
  viewType: { type: String, default: 'grid' },
  filters: {
    type: Array,
    default: () => [
      { id: 'type', options: [{ value: 'all', label: 'Все' }, { value: '1', label: 'Вариант 1' }] },
      { id: 'period', options: [{ value: '1', label: '2 недели' }, { value: '2', label: '3 недели' }] }
    ]
  },
  projects: {
    type: Array,
    default: () => [
      {
        id: 1,
        name: 'Дейтелинг Иркутск',
        description: 'Описание проекта краткое',
        avatar: '/admirra/img/avatars/avatar-40x40.png',
        stats: [
          { label: 'Показы', subtitle: 'По всем каналам', value: '120,302', change: '+15.6%', icon: '/admirra/img/svg/sprite.svg#diagrama', badgeClass: '_success', badgeIcon: '/admirra/img/svg/sprite.svg#rating-up' }
        ],
        balances: [
          { name: 'Yandex Direct', value: '10 200₽', icon: '/admirra/img/icons/yandex-direct.png', bgClass: 'bg-orangelight', textClass: 'c71663e' }
        ]
      }
    ]
  },
  searchIcon: { type: String, default: '/admirra/img/svg/sprite.svg#search' },
  editIcon: { type: String, default: '/admirra/img/svg/sprite.svg#edit' },
  gridIcon: { type: String, default: '/admirra/img/svg/sprite.svg#grid' },
  rowsIcon: { type: String, default: '/admirra/img/svg/sprite.svg#rows' },
  upIcon: { type: String, default: '/admirra/img/svg/sprite.svg#up' }
})

defineEmits(['filter-change', 'search', 'bulk-edit', 'change-view', 'open-project'])

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
</style>
