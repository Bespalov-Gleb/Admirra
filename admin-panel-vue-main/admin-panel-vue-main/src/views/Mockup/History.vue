<template>
  <div class="admirra-page-wrapper" @click="closeAllMenus">
    <section class="main-section">
      <div class="section-header pt-4">
        <h3 class="heading-3">История</h3>
      </div>

      <div class="row gy-3 mb-5">
        <div class="col-12 col-sm-auto">
          <select class="wide" v-model="filterProject" @change="onFilterChange">
            <option value="">Все проекты</option>
            <option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</option>
          </select>
        </div>
        <div class="col-12 col-sm-auto">
          <select class="wide" v-model="filterPeriod" @change="onFilterChange">
            <option value="14">Последние 14 дней</option>
            <option value="7">Последние 7 дней</option>
            <option value="30">Последние 30 дней</option>
          </select>
        </div>
      </div>

      <div v-if="isLoading" class="py-5 text-center gray56">Загрузка...</div>

      <div v-else-if="historyItems.length === 0" class="py-5 text-center gray56">
        История действий пуста
      </div>

      <div v-else class="history">
        <div
          v-for="(item, index) in historyItems"
          :key="index"
          :class="['row history-item', variantClasses[index % variantClasses.length]]"
        >
          <!-- Пользователь -->
          <div class="col col-xl-3">
            <div class="d-flex">
              <div class="avatar-36x36 me-4" style="background:#e8eef9;border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0">
                <span style="font-size:13px;font-weight:700;color:#4b6fa0">
                  {{ (item.user_email || '?').slice(0, 2).toUpperCase() }}
                </span>
              </div>
              <div class="weight-500">
                <div class="mb-1 text-15 gray">{{ item.user_email || '—' }}</div>
                <div class="text-13 gray56">{{ item.user_role || 'Пользователь' }}</div>
              </div>
            </div>
          </div>

          <!-- Описание -->
          <div class="history-item__descrp col">{{ formatDescription(item) }}</div>

          <!-- Время -->
          <div class="history-item__time col col-xl-3">
            <time>{{ formatDate(item.created_at) }}</time>
          </div>

          <!-- Меню действий -->
          <div class="col-auto col-xl-1">
            <div class="history-item__more dropdown" :class="{ '_open': openMenuIndex === index }">
              <button
                class="dropdown-head _no-style"
                @click.stop="toggleMenu(index)"
              >
                <div class="action-btn-ui">
                  <svg><use href="/admirra/img/svg/sprite.svg#dotts"></use></svg>
                </div>
              </button>
              <div v-if="openMenuIndex === index" class="dropdown-body _action _right" style="display:block">
                <div class="dropdown-block">
                  <div class="py-3">
                    <button class="dropdown-menu-item" @click.stop="closeAllMenus">
                      <div class="dropdown-menu-item__icon">
                        <svg class="_sm"><use href="/admirra/img/svg/sprite.svg#eye"></use></svg>
                      </div>
                      <span class="pe-3">Просмотр</span>
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
import { ref, onMounted } from 'vue'
import api from '../../api/axios'
import { useProjects } from '../../composables/useProjects'

const { projects, fetchProjects } = useProjects()

const historyItems = ref([])
const isLoading = ref(false)
const openMenuIndex = ref(null)
const filterProject = ref('')
const filterPeriod = ref('14')

const variantClasses = ['_linen', '_oldlace', '_aliceblue', '']

const fetchHistory = async () => {
  isLoading.value = true
  try {
    const params = {}
    if (filterProject.value) params.client_id = filterProject.value
    if (filterPeriod.value) params.days = filterPeriod.value
    const { data } = await api.get('history/', { params })
    historyItems.value = Array.isArray(data) ? data : (data.items || data.results || [])
  } catch (err) {
    // Если API истории нет — показываем пустой список
    console.warn('History API not available:', err?.response?.status)
    historyItems.value = []
  } finally {
    isLoading.value = false
  }
}

const onFilterChange = () => fetchHistory()

const toggleMenu = (index) => {
  openMenuIndex.value = openMenuIndex.value === index ? null : index
}

const closeAllMenus = () => {
  openMenuIndex.value = null
}

const formatDate = (dateStr) => {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  return d.toLocaleString('ru-RU', {
    hour: '2-digit', minute: '2-digit',
    day: '2-digit', month: '2-digit', year: 'numeric'
  })
}

const formatDescription = (item) => {
  if (item.description) return item.description
  if (item.action) return item.action
  if (item.event_type) return item.event_type
  return '—'
}

onMounted(async () => {
  await fetchProjects()
  await fetchHistory()
  setTimeout(() => {
    if (window.jQuery) {
      window.jQuery('select').niceSelect('destroy')
      window.jQuery('select').niceSelect()
    }
  }, 100)
})
</script>

<style scoped>
.admirra-page-wrapper { }
</style>
