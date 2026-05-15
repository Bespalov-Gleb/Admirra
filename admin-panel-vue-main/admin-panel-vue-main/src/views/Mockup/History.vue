<template>
  <div
    class="relative z-[2] flex min-h-full flex-col overflow-hidden px-4 py-6 sm:px-[1.7361rem] sm:py-[2.0833rem]"
    @click="closeAllMenus"
  >
    <!-- Heading -->
    <div class="pt-[1.0417rem] pb-[1.0417rem] mb-[0.6944rem]">
      <h3 class="text-[1.8056rem] font-semibold leading-none text-[#171717] dark:text-white sm:text-[2.0833rem]">История</h3>
    </div>

    <!-- Filters -->
    <div class="flex flex-wrap items-center gap-[0.6944rem] mb-[2.0833rem]" @click.stop>
      <!-- Проект -->
      <div
        class="custom-select"
        :class="{ open: openSelect === 'project' }"
        v-click-outside="() => closeSelect('project')"
      >
        <button class="cs-head dark:!border-white/10 dark:!bg-[#2C2F3D] dark:!text-white/70 dark:!shadow-[inset_0_0_0_1px_rgba(255,255,255,0.08)]" @click="toggleSelect('project')">
          <span class="cs-current">{{ projectLabel }}</span>
          <span class="cs-arrow dark:!bg-white/10">
            <svg width="5" height="4" viewBox="0 0 9 6" fill="none">
              <path d="M0.5 1L4.5 5L8.5 1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </span>
        </button>
        <div class="cs-list dark:!bg-[#2C2F3D] dark:!shadow-[0_0_0_1px_rgba(255,255,255,0.08)]">
          <div class="cs-option dark:!text-white/70 dark:hover:!bg-white/5" :class="{ selected: filterProject === '' }" @click="selectProject('')">Все проекты</div>
          <div
            v-for="p in projects"
            :key="p.id"
            class="cs-option dark:!text-white/70 dark:hover:!bg-white/5"
            :class="{ selected: filterProject === p.id }"
            @click="selectProject(p.id)"
          >{{ p.name }}</div>
        </div>
      </div>

      <!-- Период -->
      <div
        class="custom-select"
        :class="{ open: openSelect === 'period' }"
        v-click-outside="() => closeSelect('period')"
      >
        <button class="cs-head dark:!border-white/10 dark:!bg-[#2C2F3D] dark:!text-white/70 dark:!shadow-[inset_0_0_0_1px_rgba(255,255,255,0.08)]" @click="toggleSelect('period')">
          <span class="cs-current">{{ periodLabel }}</span>
          <span class="cs-arrow dark:!bg-white/10">
            <svg width="5" height="4" viewBox="0 0 9 6" fill="none">
              <path d="M0.5 1L4.5 5L8.5 1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </span>
        </button>
        <div class="cs-list dark:!bg-[#2C2F3D] dark:!shadow-[0_0_0_1px_rgba(255,255,255,0.08)]">
          <div
            v-for="opt in periodOptions"
            :key="opt.value"
            class="cs-option dark:!text-white/70 dark:hover:!bg-white/5"
            :class="{ selected: filterPeriod === opt.value }"
            @click="selectPeriod(opt.value)"
          >{{ opt.label }}</div>
        </div>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="flex items-center justify-center py-[4.1667rem] text-[0.9028rem] text-[rgba(105,105,105,0.56)] dark:text-white/55">
      Загрузка…
    </div>

    <!-- Empty -->
    <div v-else-if="historyItems.length === 0" class="flex items-center justify-center py-[4.1667rem] text-[0.9028rem] text-[rgba(105,105,105,0.56)] dark:text-white/55">
      История действий пуста
    </div>

    <!-- History list -->
    <div v-else class="history-list">
      <div
        v-for="(item, index) in historyItems"
        :key="index"
        class="history-row"
        :style="{ backgroundColor: rowColors[index % rowColors.length] }"
      >
        <!-- Пользователь -->
        <div class="flex items-center gap-[1.0417rem] min-w-0">
          <div class="user-avatar flex-shrink-0">
            <span>{{ (item.actor_name || item.actor_email || '?').slice(0, 2).toUpperCase() }}</span>
          </div>
          <div class="min-w-0">
            <div class="text-[1.0417rem] text-[#696969] font-medium leading-none mb-[0.2778rem] truncate">
              {{ item.actor_name || item.actor_email || '—' }}
            </div>
            <div class="text-[0.9028rem] text-[rgba(105,105,105,0.56)] leading-none">
              {{ item.actor_role || 'Пользователь' }}
            </div>
          </div>
        </div>

        <!-- Описание -->
        <div class="text-[1.0417rem] text-[#2c2c2c] leading-[1.3] min-w-0">
          {{ formatDescription(item) }}
        </div>

        <!-- Время -->
        <div class="text-[0.9028rem] text-[#696969] text-center whitespace-nowrap">
          <time>{{ formatDate(item.created_at) }}</time>
        </div>

        <!-- Меню действий -->
        <div class="relative flex-shrink-0" @click.stop>
          <button class="action-dots-btn" @click="toggleMenu(index)">
            <svg width="19" height="5" viewBox="0 0 19 5" fill="none">
              <circle cx="2.5" cy="2.5" r="2.5" fill="#d9d9d9"/>
              <circle cx="9.5" cy="2.5" r="2.5" fill="#d9d9d9"/>
              <circle cx="16.5" cy="2.5" r="2.5" fill="#d9d9d9"/>
            </svg>
          </button>

          <!-- Dropdown -->
          <Transition name="menu-drop">
            <div v-if="openMenuIndex === index" class="action-menu">
              <div class="action-menu__arrow"></div>
              <button class="action-menu-item" @click="closeAllMenus">
                <span class="action-menu-item__icon">
                  <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
                    <ellipse cx="10" cy="10" rx="9" ry="6" stroke="#696969" stroke-width="1.5"/>
                    <circle cx="10" cy="10" r="2.5" stroke="#696969" stroke-width="1.5"/>
                  </svg>
                </span>
                <span>Просмотр</span>
              </button>
            </div>
          </Transition>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import api from '../../api/axios'
import { useProjects } from '../../composables/useProjects'

const { projects, fetchProjects } = useProjects()

const historyItems = ref([])
const isLoading    = ref(false)
const openMenuIndex = ref(null)
const openSelect    = ref(null)
const filterProject = ref('')
const filterPeriod  = ref('14')

const rowColors = ['#fff2f2', '#fff9f2', '#f2f8ff', '#f2f2ff']

const periodOptions = [
  { value: '7',  label: 'Последние 7 дней' },
  { value: '14', label: 'Последние 14 дней' },
  { value: '30', label: 'Последние 30 дней' },
]

const projectLabel = computed(() => {
  if (!filterProject.value) return 'Все проекты'
  return projects.value.find(p => String(p.id) === String(filterProject.value))?.name ?? 'Все проекты'
})
const periodLabel = computed(() =>
  periodOptions.find(o => o.value === filterPeriod.value)?.label ?? ''
)

// ── Custom selects ──
function toggleSelect(name) {
  openSelect.value = openSelect.value === name ? null : name
}
function closeSelect(name) {
  if (openSelect.value === name) openSelect.value = null
}
function selectProject(id) {
  filterProject.value = id
  openSelect.value = null
  fetchHistory()
}
function selectPeriod(val) {
  filterPeriod.value = val
  openSelect.value = null
  fetchHistory()
}

// ── Action menus ──
function toggleMenu(index) {
  openMenuIndex.value = openMenuIndex.value === index ? null : index
}
function closeAllMenus() {
  openMenuIndex.value = null
}

// ── API ──
const fetchHistory = async () => {
  isLoading.value = true
  try {
    const params = {}
    if (filterProject.value) params.client_id = filterProject.value
    if (filterPeriod.value)  params.days = filterPeriod.value
    const { data } = await api.get('history/', { params })
    historyItems.value = Array.isArray(data) ? data : (data.items || data.results || [])
  } catch (err) {
    console.warn('History API not available:', err?.response?.status)
    historyItems.value = []
  } finally {
    isLoading.value = false
  }
}

const formatDate = (dateStr) => {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  return d.toLocaleString('ru-RU', {
    hour: '2-digit', minute: '2-digit',
    day: '2-digit', month: '2-digit', year: 'numeric',
  })
}
const formatDescription = (item) =>
  item.description || item.action || item.event_type || '—'

// ── v-click-outside ──
const vClickOutside = {
  mounted(el, binding) {
    el._outsideHandler = (e) => { if (!el.contains(e.target)) binding.value(e) }
    document.addEventListener('mousedown', el._outsideHandler)
  },
  unmounted(el) {
    document.removeEventListener('mousedown', el._outsideHandler)
  },
}

import { onMounted } from 'vue'
onMounted(async () => {
  await fetchProjects()
  await fetchHistory()
})
</script>

<style scoped>
/* ── Custom Select ── */
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
  color: rgba(0, 0, 0, 0.4);
  border: 1px solid transparent;
  cursor: pointer;
  outline: none;
  transition: border-color 0.2s;
  white-space: nowrap;
}
.custom-select.open .cs-head { border-color: rgba(0, 0, 0, 0.1); }
:global(.dark) .cs-head,
:global(.darkmode) .cs-head {
  background-color: #2C2F3D;
  color: rgba(255,255,255,0.62);
  border-color: rgba(255,255,255,0.08);
}
:global(.dark) .custom-select.open .cs-head,
:global(.darkmode) .custom-select.open .cs-head {
  border-color: rgba(255,255,255,0.14);
}
.cs-current { margin-right: 1.7361rem; }
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
.custom-select.open .cs-arrow { transform: rotate(180deg); }
:global(.dark) .cs-arrow,
:global(.darkmode) .cs-arrow {
  background-color: rgba(255,255,255,0.08);
}
.cs-list {
  position: absolute;
  top: calc(100% + 0.2778rem);
  left: 0;
  min-width: 100%;
  background-color: #fff;
  border-radius: 0.5556rem;
  box-shadow: 0 0 0 1px rgba(68, 68, 68, 0.1);
  z-index: 99;
  overflow: hidden;
  opacity: 0;
  pointer-events: none;
  transform-origin: 50% 0;
  transform: scale(0.75) translateY(-1.4583rem);
  transition: transform 0.2s cubic-bezier(0.5, 0, 0, 1.25), opacity 0.15s ease-out;
}
:global(.dark) .cs-list,
:global(.darkmode) .cs-list {
  background-color: #3a3c49;
  box-shadow: 0 0 0 1px rgba(255,255,255,0.08);
}
.custom-select.open .cs-list {
  opacity: 1;
  pointer-events: auto;
  transform: scale(1) translateY(0);
}
.cs-option {
  padding: 0.8333rem 1.7361rem 0.8333rem 1.1806rem;
  font-size: 0.9028rem;
  color: rgba(0, 0, 0, 0.7);
  cursor: pointer;
  transition: background-color 0.2s;
  white-space: nowrap;
}
.cs-option:hover { background-color: #f5f7f9; }
.cs-option.selected { font-weight: 600; }
:global(.dark) .cs-option,
:global(.darkmode) .cs-option {
  color: rgba(255,255,255,0.74);
}
:global(.dark) .cs-option:hover,
:global(.darkmode) .cs-option:hover,
:global(.dark) .cs-option.selected,
:global(.darkmode) .cs-option.selected {
  background-color: rgba(255,255,255,0.07);
}

/* ── History list ── */
.history-list {
  display: flex;
  flex-direction: column;
  gap: 1.3889rem;
  background-color: #fff;
  border-radius: 0.8333rem;
  padding: 2.0833rem;
}

@media (max-width: 479.25px) {
  .custom-select,
  .cs-head {
    width: 100%;
  }

  .cs-current {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .history-list {
    gap: 0.9722rem;
    padding: 1.25rem;
  }
}
:global(.dark) .history-list,
:global(.darkmode) .history-list {
  background-color: #2C2F3D;
  border: 1px solid rgba(255,255,255,0.08);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.28), inset 0 1px 0 rgba(255, 255, 255, 0.07);
}
.history-row {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.0417rem;
  align-items: center;
  padding: 1.3889rem 1.5278rem;
  border-radius: 1.0417rem;
  font-size: 1.0417rem;
}

@media (max-width: 479.25px) {
  .history-row {
    padding: 1.1111rem;
  }
}
:global(.dark) .history-row,
:global(.darkmode) .history-row {
  background-color: rgba(255,255,255,0.04) !important;
  border: 1px solid rgba(255,255,255,0.08);
}
:global(.dark) .history-row .text-\[\#696969\],
:global(.darkmode) .history-row .text-\[\#696969\],
:global(.dark) .history-row .text-\[\#2c2c2c\],
:global(.darkmode) .history-row .text-\[\#2c2c2c\] {
  color: rgba(255,255,255,0.82) !important;
}
:global(.dark) .history-row .text-\[rgba\(105\,105\,105\,0\.56\)\],
:global(.darkmode) .history-row .text-\[rgba\(105\,105\,105\,0\.56\)\] {
  color: rgba(255,255,255,0.55) !important;
}
@media (min-width: 960px) {
  .history-row {
    grid-template-columns: 3fr 5fr 3fr auto;
  }
}

/* ── User avatar ── */
.user-avatar {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 50%;
  background: #e8eef9;
  display: flex;
  align-items: center;
  justify-content: center;
}
.user-avatar span {
  font-size: 0.8333rem;
  font-weight: 700;
  color: #4b6fa0;
  line-height: 1;
}

/* ── Action dots button ── */
.action-dots-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.2222rem;
  height: 1.7361rem;
  border-radius: 0.2083rem;
  background-color: #fff;
  border: none;
  cursor: pointer;
  transition: background-color 0.2s;
}
.action-dots-btn:hover { background-color: #f5f7f9; }
:global(.dark) .action-dots-btn,
:global(.darkmode) .action-dots-btn {
  background-color: rgba(255,255,255,0.06);
}
:global(.dark) .action-dots-btn:hover,
:global(.darkmode) .action-dots-btn:hover {
  background-color: rgba(255,255,255,0.12);
}

/* ── Action dropdown menu ── */
.action-menu {
  position: absolute;
  top: calc(100% + 0.5556rem);
  right: -0.6944rem;
  min-width: 12.5rem;
  background: #fff;
  border-radius: 0.8333rem;
  box-shadow: 0 0 15px rgba(0, 0, 0, 0.1);
  z-index: 100;
  padding: 0.5556rem 0;
}
:global(.dark) .action-menu,
:global(.darkmode) .action-menu {
  background-color: #2C2F3D;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.40), inset 0 1px 0 rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.08);
}
.action-menu__arrow {
  position: absolute;
  bottom: 100%;
  right: 1.25rem;
  width: 0;
  height: 0;
  border-left: 7px solid transparent;
  border-right: 7px solid transparent;
  border-bottom: 7px solid #fff;
  filter: drop-shadow(0 -0.1389rem 0.1389rem rgba(0,0,0,0.06));
}
:global(.dark) .action-menu__arrow,
:global(.darkmode) .action-menu__arrow {
  border-bottom-color: #3a3c49;
}
.action-menu-item {
  display: flex;
  align-items: center;
  width: 100%;
  padding: 0.5556rem 0;
  font-size: 0.9028rem;
  color: #696969;
  background: transparent;
  border: none;
  cursor: pointer;
  transition: color 0.2s;
}
.action-menu-item:hover { color: #2563eb; }
:global(.dark) .action-menu-item,
:global(.darkmode) .action-menu-item {
  color: rgba(255,255,255,0.72);
}
:global(.dark) .action-menu-item:hover,
:global(.darkmode) .action-menu-item:hover {
  color: #4A7AFF;
}
.action-menu-item__icon {
  width: 3.125rem;
  display: flex;
  justify-content: center;
  align-items: center;
  flex-shrink: 0;
}

/* ── Dropdown animation ── */
.menu-drop-enter-active { transition: opacity 0.15s ease-out, transform 0.15s ease-out; }
.menu-drop-leave-active { transition: opacity 0.1s ease-in, transform 0.1s ease-in; }
.menu-drop-enter-from, .menu-drop-leave-to {
  opacity: 0;
  transform: scale(0.9) translateY(-0.4167rem);
}
</style>
