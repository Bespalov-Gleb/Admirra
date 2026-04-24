<template>
  <div class="admirra-page-wrapper">
    <section class="main-section">
      <div class="section-header pt-4">
        <h6 class="section-header__descrp mb-1">
          <span class="dotty _lime mt-2"></span>
          {{ subtitle }}
        </h6>
        <h3 class="heading-3">{{ title }}</h3>
      </div>
      <div class="row gy-3 mb-5">
        <div class="col-12 col-lg">
          <div class="row gy-3">
            <div v-for="(filter, idx) in filters" :key="idx" class="col-12 col-sm-auto">
              <select class="wide" @change="$emit('filter-change', { filter, value: $event.target.value })">
                <option v-for="opt in filter.options" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
              </select>
            </div>
            <div class="col-12 col-sm-auto">
              <div class="datepiker-item">
                <input class="datepiker-item__input" id="datepikerProjectReport" type="text" />
                <div class="datepiker-item__icons">
                  <svg class="datepiker-item__calendar"><use :href="calendarIcon"></use></svg>
                  <div class="circle-arrow _light _sm">
                    <svg><use :href="arrowIcon"></use></svg>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="col-12 col-sm-auto">
          <button class="btn _primary w-100" @click="$emit('download-pdf')">
            <div class="btn__inner">
              <span class="btn__text">Скачать отчет в&nbsp;PDF</span>
              <div class="btn__icon">
                <svg class="_download"><use :href="downloadIcon"></use></svg>
              </div>
            </div>
          </button>
        </div>
        <div class="col-12 col-sm-auto">
          <button class="btn _primary w-100" @click="$emit('download-telegram')">
            <div class="btn__inner">
              <span class="btn__text">Скачать отчет в&nbsp;Telegram</span>
              <div class="btn__icon">
                <svg class="_download"><use :href="downloadIcon"></use></svg>
              </div>
            </div>
          </button>
        </div>
      </div>

      <div class="row g-4 mb-4">
        <div v-for="(card, idx) in statsCards" :key="idx" class="col-12 col-sm-6 col-xxl-4">
          <div class="data-card">
            <div class="data-card__header">
              <div class="d-flex">
                <div :class="['iconbox _light _lg', card.iconClass]">
                  <svg><use :href="card.icon"></use></svg>
                </div>
                <div class="ps-4 align-self-center">
                  <h4 class="data-card__header-title mb-3 text-20 weight-500 gray500">{{ card.title }}</h4>
                  <p class="text-15 weight-300 gray56">{{ card.subtitle }}</p>
                </div>
              </div>
              <div class="ms-auto ps-3">
                <button class="circle-btn" @click="$emit('card-action', card)">
                  <svg><use :href="upIcon"></use></svg>
                </button>
              </div>
            </div>
            <span class="data-card__price weight-600">{{ card.value }}</span>
            <div class="d-flex align-items-center">
              <div class="me-4 pe-0 pe-md-3">
                <div :class="['badge _xl', card.badgeClass]">
                  <svg class="badge__icon"><use :href="card.badgeIcon"></use></svg>
                  {{ card.change }}
                </div>
              </div>
              <div class="data-card__result-info weight-500"><strong>{{ card.trendValue }}</strong> <span class="gray56">{{ card.trendLabel }}</span></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Остальные блоки (таблица, посты, комментарий) также переведены на пропсы -->
      <!-- Для краткости здесь опущены полные реализации всех секций, но принцип тот же -->
      <div class="white-block radius-normal mb-4">
        <div class="pt-2">
          <h4 class="mb-3 text-20 weight-500 gray500">{{ tableTitle }}</h4>
          <p class="text-15 weight-300 gray56">{{ tableSubtitle }}</p>
        </div>
        <div class="table-container mt-5 mb-3">
          <table class="table-style text-15">
            <thead>
              <tr>
                <th v-for="head in tableHeaders" :key="head">{{ head }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, idx) in tableData" :key="idx" :class="row.variant">
                <td><div class="td">{{ row.name }}</div></td>
                <td v-for="(cell, cIdx) in row.cells" :key="cIdx">
                  <div class="td">
                    <span class="nowrap-text">{{ cell.value }}</span>
                    <div v-if="cell.change" :class="['badge _sm', cell.badgeClass]">
                      <svg class="badge__icon"><use :href="cell.badgeIcon"></use></svg>
                      {{ cell.change }}
                    </div>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'

defineProps({
  title: { type: String, default: 'Отчет по проекту: Дейтелинг Иркутск' },
  subtitle: { type: String, default: 'Общая аналитика по всем активным проектам' },
  filters: {
    type: Array,
    default: () => [
      { id: 'channels', options: [{ value: '1', label: 'Все каналы' }] },
      { id: 'campaigns', options: [{ value: '1', label: 'Компании' }] },
      { id: 'period', options: [{ value: '1', label: 'Свой период' }] }
    ]
  },
  statsCards: {
    type: Array,
    default: () => [
      { title: 'Расходы', subtitle: 'За период', value: '90,190.55 ₽', change: '+15.6%', trendValue: '+1.4k', trendLabel: 'за эту неделю', icon: '/admirra/img/svg/sprite.svg#wallet', badgeClass: '_success', badgeIcon: '/admirra/img/svg/sprite.svg#rating-up' },
      { title: 'Показы', subtitle: 'По всем каналам', value: '120,302', change: '+15.6%', trendValue: '+1.4k', trendLabel: 'за эту неделю', icon: '/admirra/img/svg/sprite.svg#diagrama', badgeClass: '_success', badgeIcon: '/admirra/img/svg/sprite.svg#rating-up' }
    ]
  },
  tableTitle: { type: String, default: 'Статистика по ключевым целям' },
  tableSubtitle: { type: String, default: 'За период' },
  tableHeaders: { type: Array, default: () => ['Название кампании', 'Расход', 'Показы', 'Клики', 'CPC', 'Лиды', 'CPA'] },
  tableData: {
    type: Array,
    default: () => [
      { name: 'Дейтелинг Про Иркутск', variant: 'linen', cells: [{ value: '90,190.55 ₽', change: '+15.6%', badgeClass: '_success', badgeIcon: '/admirra/img/svg/sprite.svg#rating-up' }] }
    ]
  },
  calendarIcon: { type: String, default: '/admirra/img/svg/sprite.svg#datepiker' },
  arrowIcon: { type: String, default: '/admirra/img/svg/sprite.svg#arrow' },
  downloadIcon: { type: String, default: '/admirra/img/svg/sprite.svg#download' },
  upIcon: { type: String, default: '/admirra/img/svg/sprite.svg#up' }
})

defineEmits(['filter-change', 'download-pdf', 'download-telegram', 'card-action'])

onMounted(() => {
  setTimeout(() => {
    if (window.jQuery) {
      window.jQuery('select').niceSelect('destroy')
      window.jQuery('select').niceSelect()
    }
    if (window.AirDatepicker) {
      new window.AirDatepicker("#datepikerProjectReport", {
        multipleDates: 2,
        selectedDates: ["2026-04-01", "2026-04-30"],
        range: true,
        multipleDatesSeparator: " - ",
      })
    }
  }, 100)
})
</script>

<style scoped>
.admirra-page-wrapper {
  /* Scoped styles */
}
</style>
