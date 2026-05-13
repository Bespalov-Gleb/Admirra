<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div
        v-if="modelValue"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/50 backdrop-blur-sm"
        @click.self="close"
      >
        <div class="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden animate-modal-in">
          <!-- Заголовок -->
          <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100 flex-shrink-0">
            <h3 class="text-lg font-bold text-gray-900">Выбор кампаний</h3>
            <button
              @click="close"
              class="p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
            >
              <XMarkIcon class="w-5 h-5" />
            </button>
          </div>

          <!-- Вкладки как в браузере -->
          <div class="flex gap-1 px-4 pt-2 flex-shrink-0 bg-gray-100/50 border-b border-gray-200">
            <button
              type="button"
              class="px-4 py-2.5 text-sm font-medium rounded-t-lg transition-all"
              :class="activeTab === 'campaigns'
                ? 'bg-white text-blue-600 shadow-sm border border-b-0 border-gray-200 -mb-px'
                : 'bg-transparent text-gray-500 hover:text-gray-700 hover:bg-white/50'"
              @click="activeTab = 'campaigns'"
            >
              Кампании
            </button>
            <button
              type="button"
              class="px-4 py-2.5 text-sm font-medium rounded-t-lg transition-all"
              :class="activeTab === 'goals'
                ? 'bg-white text-blue-600 shadow-sm border border-b-0 border-gray-200 -mb-px'
                : 'bg-transparent text-gray-500 hover:text-gray-700 hover:bg-white/50'"
              @click="switchToGoalsTab"
            >
              По целям
            </button>
          </div>

          <!-- Контент вкладки «Кампании» -->
          <template v-if="activeTab === 'campaigns'">
            <div class="px-6 py-4 flex-shrink-0 border-b border-gray-100">
              <div class="relative">
                <MagnifyingGlassIcon class="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  v-model="searchQuery"
                  type="text"
                  placeholder="Поиск по ID или названию кампании..."
                  class="w-full pl-10 pr-4 py-3 bg-gray-50 border border-gray-200 rounded-xl text-sm placeholder-gray-400 focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 outline-none transition-all"
                />
              </div>
            </div>
            <div class="px-6 py-2 flex gap-3 flex-shrink-0">
              <button type="button" @click="selectAll" class="text-xs font-medium text-blue-600 hover:text-blue-700">Выбрать все</button>
              <button type="button" @click="deselectAll" class="text-xs font-medium text-gray-500 hover:text-gray-700">Снять всё</button>
            </div>
            <div class="flex-1 min-h-[13.8889rem] max-h-[50vh] overflow-y-auto overscroll-contain px-6 py-2">
              <div v-if="loading" class="py-16 flex flex-col items-center gap-3">
                <div class="w-10 h-10 border-4 border-gray-200 border-t-blue-600 rounded-full animate-spin" />
                <span class="text-sm text-gray-500">Загрузка кампаний...</span>
              </div>
              <div v-else class="space-y-1 pb-4">
                <button
                  v-for="campaign in filteredCampaigns"
                  :key="campaign.id"
                  type="button"
                  @click="toggle(campaign.id)"
                  class="w-full flex items-start gap-3 px-4 py-3 rounded-xl cursor-pointer hover:bg-gray-50 transition-colors group text-left"
                  :class="{ 'bg-blue-50/50': isSelected(campaign.id) }"
                >
                  <div
                    class="mt-0.5 w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 transition-colors"
                    :class="isSelected(campaign.id) ? 'bg-blue-600 border-blue-600' : 'border-gray-300 group-hover:border-gray-400'"
                  >
                    <CheckIcon v-if="isSelected(campaign.id)" class="w-3.5 h-3.5 text-white" stroke-width="3" />
                  </div>
                  <div class="min-w-0 flex-1">
                    <span class="block text-sm font-medium text-gray-900 truncate">{{ campaign.name }}</span>
                    <span class="text-xs text-gray-400">{{ campaign.external_id ? `ID: ${campaign.external_id}` : '' }}</span>
                  </div>
                </button>
                <div v-if="filteredCampaigns.length === 0" class="py-12 text-center text-sm text-gray-500">Кампании не найдены</div>
              </div>
            </div>
          </template>

          <!-- Контент вкладки «По целям» -->
          <template v-else-if="activeTab === 'goals'">
            <div class="flex-1 min-h-[13.8889rem] max-h-[50vh] overflow-y-auto px-6 py-4">
              <!-- Яндекс: сообщение -->
              <div v-if="channel !== 'vk'" class="py-12 text-center">
                <p class="text-[1.0417rem] font-medium text-gray-700 mb-2">Фильтрация по целям доступна только для VK Ads</p>
                <p class="text-[0.9028rem] text-gray-500">Выберите канал VK Ads в фильтрах, чтобы отфильтровать кампании по типу целевого действия (лид-формы, мини-приложения и др.)</p>
              </div>
              <!-- VK: цели + кампании -->
              <div v-else class="space-y-4">
                <div>
                  <p class="text-xs font-semibold text-gray-600 mb-2">Типы целевых действий</p>
                  <div class="space-y-2">
                    <div
                      v-for="group in groupedVkGoals"
                      :key="group.key"
                      class="border border-gray-200 rounded-xl bg-white"
                    >
                      <div class="px-3 py-1.5 text-[0.7639rem] font-semibold text-gray-500 uppercase tracking-wide border-b border-gray-100">
                        {{ group.name }}
                      </div>
                      <div class="flex flex-wrap gap-2 px-3 py-2">
                        <label
                          v-for="goal in group.items"
                          :key="goal.id"
                          class="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl border cursor-pointer transition-colors"
                          :class="localSelectedGoalIds.includes(goal.id) ? 'border-blue-500 bg-blue-50/50' : 'border-gray-200 hover:border-gray-300'"
                        >
                          <input
                            type="checkbox"
                            class="h-3.5 w-3.5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                            :checked="localSelectedGoalIds.includes(goal.id)"
                            @change="toggleGoal(goal.id)"
                          />
                          <span class="text-sm text-gray-800">{{ goal.name }}</span>
                        </label>
                      </div>
                    </div>
                  </div>
                </div>
                <div v-if="localSelectedGoalIds.length > 0">
                  <div class="flex items-center justify-between gap-2 mb-2">
                    <p class="text-xs font-semibold text-gray-600">Кампании выбранных типов</p>
                    <div class="flex gap-2">
                      <button type="button" @click="selectAll" class="text-xs font-medium text-blue-600 hover:text-blue-700">Выбрать все</button>
                      <button type="button" @click="deselectAll" class="text-xs font-medium text-gray-500 hover:text-gray-700">Снять всё</button>
                    </div>
                  </div>
                  <div class="space-y-1">
                    <button
                      v-for="campaign in campaignsByGoals"
                      :key="campaign.id"
                      type="button"
                      @click="toggle(campaign.id)"
                      class="w-full flex items-start gap-3 px-4 py-3 rounded-xl cursor-pointer hover:bg-gray-50 transition-colors group text-left"
                      :class="{ 'bg-blue-50/50': isSelected(campaign.id) }"
                    >
                      <div
                        class="mt-0.5 w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0"
                        :class="isSelected(campaign.id) ? 'bg-blue-600 border-blue-600' : 'border-gray-300 group-hover:border-gray-400'"
                      >
                        <CheckIcon v-if="isSelected(campaign.id)" class="w-3.5 h-3.5 text-white" stroke-width="3" />
                      </div>
                      <div class="min-w-0 flex-1">
                        <span class="block text-sm font-medium text-gray-900 truncate">{{ campaign.name }}</span>
                        <span class="text-xs text-gray-400">{{ campaign.external_id ? `ID: ${campaign.external_id}` : '' }}</span>
                      </div>
                    </button>
                    <div v-if="campaignsByGoals.length === 0" class="py-8 text-center text-sm text-gray-500">Нет кампаний с выбранными целями</div>
                  </div>
                </div>
              </div>
            </div>
          </template>

          <!-- Футер -->
          <div class="px-6 py-4 border-t border-gray-100 flex-shrink-0 flex items-center justify-between gap-4">
            <span class="text-sm text-gray-500">
              Выбрано: {{ selectedCount }} из {{ totalCount }}
            </span>
            <div class="flex gap-3">
              <button type="button" @click="close" class="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-xl">Отмена</button>
              <button type="button" @click="apply" class="px-5 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl">Применить</button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { XMarkIcon, MagnifyingGlassIcon, CheckIcon } from '@heroicons/vue/24/outline'

const props = defineProps({
  modelValue: Boolean,
  campaigns: { type: Array, default: () => [] },
  /** Все VK кампании без фильтра (для вкладки «По целям») */
  campaignsForGoals: { type: Array, default: () => [] },
  selectedIds: { type: Array, default: () => [] },
  /** yandex | vk | all */
  channel: { type: String, default: 'all' },
  /** Типы целей VK из campaigns/vk-goal-actions */
  vkGoalActions: { type: Array, default: () => [] },
  selectedGoalIds: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'apply', 'apply-goals'])

const activeTab = ref('campaigns')
const searchQuery = ref('')
const localSelected = ref([])
const localSelectedGoalIds = ref([])

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

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      searchQuery.value = ''
      activeTab.value = 'campaigns'
      localSelected.value = [...(props.selectedIds || [])]
      localSelectedGoalIds.value = [...(props.selectedGoalIds || [])]
    }
  },
  { immediate: true }
)

watch(
  () => props.selectedIds,
  (ids) => {
    if (props.modelValue) localSelected.value = [...(ids || [])]
  },
  { deep: true }
)

watch(
  () => props.selectedGoalIds,
  (ids) => {
    if (props.modelValue) localSelectedGoalIds.value = [...(ids || [])]
  },
  { deep: true }
)

const switchToGoalsTab = () => {
  activeTab.value = 'goals'
}

const filteredCampaigns = computed(() => {
  const list = activeTab.value === 'campaigns' ? props.campaigns : campaignsByGoals.value
  if (!searchQuery.value.trim()) return list
  const q = searchQuery.value.toLowerCase().trim()
  return list.filter((c) => {
    const nameMatch = c.name && c.name.toLowerCase().includes(q)
    const idMatch = c.id && String(c.id).toLowerCase().includes(q)
    const extIdMatch = c.external_id && String(c.external_id).toLowerCase().includes(q)
    return nameMatch || idMatch || extIdMatch
  })
})

const campaignsByGoals = computed(() => {
  if (props.channel !== 'vk' || localSelectedGoalIds.value.length === 0) return []
  const ids = new Set(localSelectedGoalIds.value)
  return (props.campaignsForGoals || props.campaigns || []).filter(
    (c) => c.vk_goal_action_id && ids.has(c.vk_goal_action_id)
  )
})

const selectedCount = computed(() => localSelected.value.length)
const totalCount = computed(() => {
  if (activeTab.value === 'campaigns') return props.campaigns.length
  return campaignsByGoals.value.length
})

const isSelected = (id) => localSelected.value.some((x) => String(x) === String(id))

const toggle = (id) => {
  const idx = localSelected.value.findIndex((x) => String(x) === String(id))
  if (idx > -1) {
    localSelected.value = localSelected.value.filter((x) => String(x) !== String(id))
  } else {
    localSelected.value = [...localSelected.value, id]
  }
}

const toggleGoal = (id) => {
  const idx = localSelectedGoalIds.value.indexOf(id)
  if (idx > -1) {
    localSelectedGoalIds.value = localSelectedGoalIds.value.filter((x) => x !== id)
  } else {
    localSelectedGoalIds.value = [...localSelectedGoalIds.value, id]
  }
}

const selectAll = () => {
  const list = activeTab.value === 'campaigns' ? props.campaigns : campaignsByGoals.value
  localSelected.value = list.map((c) => c.id)
}

const deselectAll = () => {
  localSelected.value = []
}

const close = () => {
  emit('update:modelValue', false)
}

const apply = () => {
  if (activeTab.value === 'goals' && props.channel === 'vk') {
    emit('apply-goals', { campaignIds: localSelected.value, goalActionIds: localSelectedGoalIds.value })
  } else {
    emit('apply', localSelected.value)
  }
  emit('update:modelValue', false)
}
</script>

<style scoped>
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.2s ease;
}
.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}
.animate-modal-in {
  animation: modalIn 0.25s ease-out;
}
@keyframes modalIn {
  from {
    opacity: 0;
    transform: scale(0.97) translateY(0.5556rem);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}
</style>
