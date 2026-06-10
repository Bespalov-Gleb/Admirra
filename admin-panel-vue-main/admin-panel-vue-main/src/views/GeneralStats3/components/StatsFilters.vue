<template>
  <div class="flex flex-wrap items-center gap-3 lg:gap-4">
    <!-- Main Selections Group -->
    <div class="flex w-full flex-wrap items-center gap-3 lg:w-auto">
      <!-- Project Select -->
      <div class="filter-field flex flex-col gap-1 min-w-[9.7222rem] sm:min-w-[12.5rem]">
        <label class="text-[0.5556rem] font-black text-gray-400 dark:text-gray-500 uppercase tracking-widest ml-2">Проект</label>
        <div class="relative group">
          <select 
            v-model="filters.client_id"
            class="w-full h-9 pl-3 pr-8 bg-white dark:bg-[#232637] border border-gray-100 dark:border-white/10 rounded-[0.9722rem] text-xs font-normal text-gray-500 dark:text-gray-300 outline-none appearance-none transition-all focus:border-blue-500 dark:focus:border-[#4A7AFF] focus:ring-4 focus:ring-blue-500/5 group-hover:border-gray-200 dark:group-hover:border-white/20"
          >
            <option value="">Все проекты</option>
            <option v-for="client in clients" :key="client.id" :value="client.id">
              {{ client.name }}
            </option>
          </select>
          <ChevronDownIcon class="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400 dark:text-gray-500 pointer-events-none group-hover:text-gray-600 dark:group-hover:text-gray-300 transition-colors" />
        </div>
      </div>

      <div class="w-[1px] h-8 bg-gray-200/50 dark:bg-white/10 hidden sm:block"></div>

      <!-- Channel Select -->
      <div class="filter-field flex flex-col gap-1 min-w-[7.6389rem] sm:min-w-[9.7222rem]">
        <label class="text-[0.5556rem] font-black text-gray-400 dark:text-gray-500 uppercase tracking-widest ml-2">Канал</label>
        <div class="relative group">
          <select 
            v-model="filters.channel"
            class="w-full h-9 pl-3 pr-8 bg-white dark:bg-[#232637] border border-gray-100 dark:border-white/10 rounded-[0.9722rem] text-xs font-normal text-gray-500 dark:text-gray-300 outline-none appearance-none transition-all focus:border-blue-500 dark:focus:border-[#4A7AFF] focus:ring-4 focus:ring-blue-500/5 group-hover:border-gray-200 dark:group-hover:border-white/20"
          >
            <option value="all">Все каналы</option>
            <option value="yandex">Yandex Direct</option>
            <option value="vk">VK Ads</option>
            <option value="avito">Avito Ads</option>
          </select>
          <ChevronDownIcon class="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400 dark:text-gray-500 pointer-events-none group-hover:text-gray-600 dark:group-hover:text-gray-300 transition-colors" />
        </div>
      </div>

      <div class="w-[1px] h-8 bg-gray-200/50 dark:bg-white/10 hidden lg:block"></div>

      <!-- Campaign Select -->
      <div class="filter-field flex flex-col gap-1 min-w-[9.7222rem] sm:min-w-[12.5rem]">
        <label class="text-[0.5556rem] font-black text-gray-400 dark:text-gray-500 uppercase tracking-widest ml-2">Кампания</label>
        <div class="relative group">
          <select 
            v-model="selectedCampaignId"
            class="w-full h-9 pl-3 pr-8 bg-white dark:bg-[#232637] border border-gray-100 dark:border-white/10 rounded-[0.9722rem] text-xs font-normal text-gray-500 dark:text-gray-300 outline-none appearance-none transition-all focus:border-blue-500 dark:focus:border-[#4A7AFF] focus:ring-4 focus:ring-blue-500/5 group-hover:border-gray-200 dark:group-hover:border-white/20 disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="loadingCampaigns || !filters.client_id"
          >
            <template v-if="!filters.client_id">
              <option value="">Сначала проект</option>
            </template>
            <template v-else-if="loadingCampaigns">
              <option value="">Загрузка...</option>
            </template>
            <template v-else-if="!allCampaigns.length">
              <option value="">Нет кампаний</option>
            </template>
            <template v-else>
              <option value="">Все кампании ({{ allCampaigns.length }})</option>
              <option v-for="campaign in allCampaigns" :key="campaign.id" :value="campaign.id">
                {{ campaign.name }}
              </option>
            </template>
          </select>
          <div v-if="loadingCampaigns" class="absolute right-8 top-1/2 -translate-y-1/2">
            <div class="w-3 h-3 border-2 border-blue-600/20 border-t-blue-600 rounded-full animate-spin"></div>
          </div>
          <ChevronDownIcon class="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400 dark:text-gray-500 pointer-events-none group-hover:text-gray-600 dark:group-hover:text-gray-300 transition-colors" />
        </div>
      </div>

      <div v-if="filters.channel === 'vk'" ref="vkGoalsContainer" class="filter-field flex flex-col gap-1 min-w-[12.5rem] sm:min-w-[15.2778rem]">
        <label class="text-[0.5556rem] font-black text-gray-400 dark:text-gray-500 uppercase tracking-widest ml-2">Целевое действие</label>
        <div class="relative">
          <button
            ref="goalsButton"
            type="button"
            class="w-full h-9 px-3 bg-white dark:bg-[#232637] border border-gray-100 dark:border-white/10 rounded-[0.9722rem] text-xs font-bold text-gray-700 dark:text-gray-200 flex items-center justify-between transition-all hover:border-gray-200 dark:hover:border-white/20 focus:border-blue-500 dark:focus:border-[#4A7AFF] focus:ring-4 focus:ring-blue-500/5 disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="loadingVkGoalActions"
            @click.stop="toggleGoals"
          >
            <span class="truncate">
              <template v-if="loadingVkGoalActions">Загрузка...</template>
              <template v-else-if="!vkGoalActions.length">Нет действий</template>
              <template v-else-if="allGoalsSelected">Все действия ({{ vkGoalActions.length }})</template>
              <template v-else>Выбрано: {{ selectedGoalIds.length }}</template>
            </span>
            <ChevronDownIcon class="w-3.5 h-3.5 text-gray-400 dark:text-gray-500 transition-transform" :class="{'rotate-180': showGoals}" />
          </button>
        </div>
      </div>
      
      <!-- Dropdown Portal (Fixed Positioning) -->
      <Teleport to="body">
        <div
          v-if="showGoals && vkGoalActions.length && dropdownPosition"
          class="fixed bg-white dark:bg-[#2C2F3D] border border-gray-200 dark:border-white/10 rounded-[0.9722rem] shadow-2xl p-3 max-h-80 overflow-y-auto"
          :style="{
            top: `${dropdownPosition.top}px`,
            left: `${dropdownPosition.left}px`,
            width: `${dropdownPosition.width}px`,
            zIndex: 999999
          }"
          @click.stop
        >
          <label class="flex items-center gap-2 px-2 py-1.5 text-xs font-semibold text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-white/5 rounded-lg cursor-pointer">
            <input
              type="checkbox"
              class="h-3.5 w-3.5 rounded border-gray-300 text-brand-500 focus:ring-brand-500 cursor-pointer"
              :checked="allGoalsSelected"
              @change="toggleAllGoals($event)"
            />
            <span>Выбрать все</span>
          </label>
          <div class="h-px bg-gray-100 dark:bg-white/10 my-1"></div>

          <!-- Группированный список типов ЦД -->
          <div v-for="group in groupedVkGoals" :key="group.key" class="mb-1 last:mb-0">
            <div class="px-2 py-1 text-[0.7639rem] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
              {{ group.name }}
            </div>
            <label
              v-for="goal in group.items"
              :key="goal.id"
              class="flex items-center gap-2 px-2 py-1.5 text-xs text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-white/5 rounded-lg cursor-pointer transition-colors"
            >
              <input
                type="checkbox"
                class="h-3.5 w-3.5 rounded border-gray-300 text-brand-500 focus:ring-brand-500 cursor-pointer"
                :checked="selectedGoalIds.includes(goal.id)"
                @change="toggleGoal(goal.id)"
              />
              <span class="truncate" :title="goal.name">{{ goal.name }}</span>
            </label>
          </div>
        </div>
      </Teleport>
    </div>

    <!-- Time & Action Group -->
    <div class="flex w-full flex-wrap items-center gap-3 lg:ml-auto lg:w-auto">
      <!-- Period Select -->
      <div class="filter-field flex flex-col gap-1 w-[7.6389rem]">
        <label class="text-[0.5556rem] font-black text-gray-400 dark:text-gray-500 uppercase tracking-widest ml-2">Период</label>
        <div class="relative group">
          <select 
            v-model="filters.period"
            @change="$emit('period-change')"
            class="w-full h-9 pl-3 pr-8 bg-white/50 dark:bg-[#232637] border border-gray-100 dark:border-white/10 rounded-[0.9722rem] text-xs font-normal text-gray-500 dark:text-gray-300 outline-none appearance-none transition-all focus:border-blue-500 dark:focus:border-[#4A7AFF] focus:ring-4 focus:ring-blue-500/5 group-hover:border-gray-200 dark:group-hover:border-white/20"
          >
            <option value="7">Последняя неделя</option>
            <option value="14">2 недели</option>
            <option value="30">Месяц</option>
            <option value="90">Квартал</option>
            <option value="180">Полгода</option>
            <option value="365">Год</option>
            <option value="custom">Свой период</option>
          </select>
          <ChevronDownIcon class="absolute right-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400 dark:text-gray-500 pointer-events-none group-hover:text-gray-600 dark:group-hover:text-gray-300 transition-colors" />
        </div>
      </div>

      <!-- Custom Date Range Picker -->
      <div v-if="filters.period === 'custom'" class="filter-field flex flex-col gap-1">
        <label class="text-[0.5556rem] font-black text-gray-400 dark:text-gray-500 uppercase tracking-widest ml-2">Даты</label>
        <DateRangePicker
          :model-value="{ start: filters.start_date, end: filters.end_date }"
          @change="handleCustomDateChange"
        />
      </div>

      <!-- Export Button -->
      <button 
        @click="$emit('export')"
        class="h-9 px-4 bg-gray-900 text-white rounded-[0.9722rem] text-[0.6944rem] font-black uppercase tracking-widest hover:bg-blue-600 hover:shadow-lg hover:shadow-blue-200 transition-all flex items-center gap-2 active:scale-95"
        title="Скачать CSV"
      >
        <ArrowDownTrayIcon class="w-3.5 h-3.5" />
        <span class="hidden sm:inline">CSV</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { ArrowDownTrayIcon, ChevronDownIcon } from '@heroicons/vue/24/solid'
import DateRangePicker from '../../../components/ui/DateRangePicker.vue'

const props = defineProps({
  filters: {
    type: Object,
    required: true
  },
  clients: {
    type: Array,
    default: () => []
  },
  allCampaigns: {
    type: Array,
    default: () => []
  },
  loadingCampaigns: {
    type: Boolean,
    default: false
  },
  vkGoalActions: {
    type: Array,
    default: () => []
  },
  loadingVkGoalActions: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['period-change', 'export', 'update:campaign-ids', 'update:goal-action-ids', 'date-change'])

const selectedCampaignId = computed({
  get: () => {
    const ids = props.filters.campaign_ids
    return (ids && ids.length > 0) ? ids[0] : ''
  },
  set: (val) => {
    if (val === undefined || val === null) return
    const current = (props.filters.campaign_ids && props.filters.campaign_ids.length > 0) ? props.filters.campaign_ids[0] : ''
    if (val !== current) {
      emit('update:campaign-ids', val ? [val] : [])
    }
  }
})

const showGoals = ref(false)
const vkGoalsContainer = ref(null)
const goalsButton = ref(null)
const dropdownPosition = ref(null)

const selectedGoalIds = computed(() => props.filters.vk_goal_action_ids || [])
const allGoalsSelected = computed(() => {
  if (!props.vkGoalActions.length) return false
  return selectedGoalIds.value.length === props.vkGoalActions.length
})

// Конфигурация групп ЦД VK: какие коды относятся к какой группе
const VK_GOAL_GROUPS = [
  {
    key: 'lead_forms',
    name: 'Лид-формы',
    groupIds: ['leadads', 'lead_forms', 'leadforms'],
    childIds: ['evt_51_lead_forms']
  },
  {
    key: 'social_engagement',
    name: 'Действия в социальных сетях',
    groupIds: ['socialengagement', 'social_engagement'],
    childIds: ['evt_41_community_actions']
  },
  {
    key: 'mini_apps',
    name: 'Мини-приложения',
    groupIds: ['mini_app'],
    childIds: ['evt_43_miniapp_events']
  }
]

// Группируем плоский список vkGoalActions во вложенную структуру для UI
const groupedVkGoals = computed(() => {
  if (!props.vkGoalActions || !props.vkGoalActions.length) return []

  const byId = new Map(props.vkGoalActions.map(g => [g.id, g]))
  const usedIds = new Set()
  const groups = []

  VK_GOAL_GROUPS.forEach(def => {
    const items = def.childIds
      .map(id => byId.get(id))
      .filter(Boolean)

    if (!items.length) {
      return
    }

    def.groupIds.forEach(id => usedIds.add(id))
    def.childIds.forEach(id => usedIds.add(id))

    groups.push({
      key: def.key,
      name: def.name,
      items
    })
  })

  // Остальные цели, не попавшие ни в одну группу
  const others = props.vkGoalActions.filter(g => !usedIds.has(g.id))
  if (others.length) {
    groups.push({
      key: 'other',
      name: 'Другие действия',
      items: others
    })
  }

  return groups
})

const updateDropdownPosition = () => {
  if (!goalsButton.value) return
  const rect = goalsButton.value.getBoundingClientRect()
  dropdownPosition.value = {
    top: rect.bottom + 8,
    left: rect.left,
    width: rect.width
  }
}

const toggleGoals = () => {
  if (!props.vkGoalActions.length) return
  if (!showGoals.value) {
    updateDropdownPosition()
  }
  showGoals.value = !showGoals.value
}

const toggleAllGoals = (event) => {
  const checked = event.target.checked
  const allIds = props.vkGoalActions.map(g => g.id)
  emit('update:goal-action-ids', checked ? allIds : [])
}

const toggleGoal = (goalId) => {
  const current = new Set(selectedGoalIds.value)
  if (current.has(goalId)) {
    current.delete(goalId)
  } else {
    current.add(goalId)
  }
  emit('update:goal-action-ids', Array.from(current))
}

// Закрыть выпадающий список при клике вне его
const handleClickOutside = (event) => {
  if (showGoals.value && vkGoalsContainer.value && !vkGoalsContainer.value.contains(event.target)) {
    showGoals.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})

const handleCustomDateChange = (dates) => {
  if (dates.start) {
    props.filters.start_date = dates.start
  }
  if (dates.end) {
    props.filters.end_date = dates.end
  }
  emit('date-change', dates)
  emit('period-change')
}
</script>

<style scoped>
@media (max-width: 479.25px) {
  .filter-field {
    min-width: 100%;
    width: 100%;
  }
}
</style>
