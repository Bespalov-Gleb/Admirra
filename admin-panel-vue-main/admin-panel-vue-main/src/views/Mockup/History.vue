<template>
  <div class="admirra-page-wrapper">
    <section class="main-section">
      <div class="section-header pt-4">
        <h3 class="heading-3">{{ title }}</h3>
      </div>
      <div class="row gy-3 mb-5">
        <div v-for="(filter, index) in filters" :key="index" class="col-12 col-sm-auto">
          <select class="wide" @change="$emit('filter-change', { filter, value: $event.target.value })">
            <option v-for="option in filter.options" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </div>
      </div>
      <div class="history">
        <div v-for="(item, index) in historyItems" :key="index" :class="['row history-item', item.variantClass]">
          <div class="col col-xl-3">
            <div class="d-flex">
              <div class="avatar-36x36 me-4">
                <img class="img-cover" :src="item.avatar" alt="#" />
              </div>
              <div class="weight-500">
                <div class="mb-1 text-15 gray">{{ item.userName }}</div>
                <div class="text-13 gray56">{{ item.userRole }}</div>
              </div>
            </div>
          </div>
          <div class="history-item__descrp col">{{ item.description }}</div>
          <div class="history-item__time col col-xl-3">
            <time>{{ item.time }}</time>
          </div>
          <div class="col-auto col-xl-1">
            <div class="history-item__more dropdown">
              <button class="dropdown-head _no-style" @click="$emit('toggle-menu', index)">
                <div class="action-btn-ui">
                  <svg><use :href="dottsIcon"></use></svg>
                </div>
              </button>
              <!-- Dropdown body logic should be handled by parent or a separate component, 
                   keeping static for now but emitting actions -->
              <div class="dropdown-body _action _right">
                <div class="dropdown-block">
                  <div class="py-3">
                    <button class="dropdown-menu-item" @click="$emit('view', item)">
                      <div class="dropdown-menu-item__icon">
                        <svg class="_sm"><use :href="eyeIcon"></use></svg>
                      </div>
                      <span class="pe-3">Просмотр</span>
                    </button>
                    <button class="dropdown-menu-item" @click="$emit('edit', item)">
                      <div class="dropdown-menu-item__icon">
                        <svg class="_stroke _lg"><use :href="penIcon"></use></svg>
                      </div>
                      <span class="pe-3">Редактировать</span>
                    </button>
                    <button class="dropdown-menu-item _danger" @click="$emit('delete', item)">
                      <div class="dropdown-menu-item__icon">
                        <svg><use :href="deleteIcon"></use></svg>
                      </div>
                      <span class="pe-3">Удалить</span>
                    </button>
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
import { onMounted } from 'vue'

defineProps({
  title: {
    type: String,
    default: 'История'
  },
  filters: {
    type: Array,
    default: () => [
      { id: 'staff', options: [{ value: '1', label: 'Все сотрудники' }, { value: '2', label: 'подпункт 1' }] },
      { id: 'channels', options: [{ value: '1', label: 'Все каналы' }, { value: '2', label: 'подпункт 1' }] },
      { id: 'period', options: [{ value: '1', label: 'Последние 14 дней' }, { value: '2', label: 'подпункт 1' }] },
      { id: 'project', options: [{ value: '1', label: 'Выбрать проект' }, { value: '2', label: 'подпункт 1' }] }
    ]
  },
  historyItems: {
    type: Array,
    default: () => [
      { variantClass: '_linen', avatar: '/admirra/img/avatars/user2.jpg', userName: 'Петр Петров', userRole: 'Сотрудник', description: 'Сформирован AI отчет | ПРОЕКТ: ПРИОРИТИ | ЯД', time: '15:04 (МСК) - 13.03.2026' },
      { variantClass: '_oldlace', avatar: '/admirra/img/avatars/user1.jpg', userName: 'Петр Петров', userRole: 'Сотрудник', description: 'Сформирован AI отчет | ПРОЕКТ: ПРИОРИТИ | ЯД', time: '15:04 (МСК) - 13.03.2026' },
      { variantClass: '_aliceblue', avatar: '/admirra/img/avatars/user3.jpg', userName: 'Петр Петров', userRole: 'Сотрудник', description: 'Сформирован AI отчет | ПРОЕКТ: ПРИОРИТИ | ЯД', time: '15:04 (МСК) - 13.03.2026' }
    ]
  },
  dottsIcon: { type: String, default: '/admirra/img/svg/sprite.svg#dotts' },
  eyeIcon: { type: String, default: '/admirra/img/svg/sprite.svg#eye' },
  penIcon: { type: String, default: '/admirra/img/svg/sprite.svg#pen' },
  deleteIcon: { type: String, default: '/admirra/img/svg/sprite.svg#delete' }
})

defineEmits(['filter-change', 'toggle-menu', 'view', 'edit', 'delete'])

onMounted(() => {
  setTimeout(() => {
    if (window.jQuery) {
      window.jQuery('select').niceSelect('destroy')
      window.jQuery('select').niceSelect()
    }
  }, 100)
})
</script>

<style scoped>
.admirra-page-wrapper {
  /* Scoped styles */
}
</style>
