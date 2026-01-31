<template>
  <div class="space-y-6">
    <!-- Loading Banner -->
    <div v-if="loading" class="bg-blue-50 border border-blue-200 rounded-2xl p-4 flex items-center gap-3">
      <div class="w-8 h-8 border-3 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
      <div>
        <p class="text-sm font-bold text-blue-900">Загрузка целей...</p>
        <p class="text-xs text-blue-600">Получаем цели из Яндекс.Метрики</p>
      </div>
    </div>

    <!-- Header & Search -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 px-1">
      <div>
        <label class="block text-[9px] font-black text-gray-400 uppercase tracking-[0.2em] mb-1">ЦЕЛИ И КОНВЕРСИИ</label>
        <p class="text-[11px] text-gray-500 font-bold">Выберите основную цель (звездочка) и дополнительные цели для отслеживания</p>
      </div>
      
      <div class="relative group w-full md:w-64">
        <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
          <MagnifyingGlassIcon class="h-4 w-4 text-gray-400 group-focus-within:text-blue-500 transition-colors" />
        </div>
        <input 
          type="text" 
          v-model="searchQuery"
          placeholder="Поиск цели..."
          class="block w-full pl-11 pr-4 py-3 bg-white border border-gray-100 rounded-2xl text-[12px] font-bold text-gray-900 placeholder-gray-400 focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all shadow-sm"
        >
      </div>
    </div>

    <!-- Goals Power Table -->
    <div class="bg-white border border-gray-100 rounded-[2rem] overflow-hidden shadow-sm">
      <table class="w-full text-left border-collapse">
        <thead>
          <tr class="bg-gray-50/50 border-b border-gray-100">
            <th class="w-12 px-5 py-4 text-center">
              <StarIcon class="w-4 h-4 mx-auto text-gray-300" />
            </th>
            <th class="w-10 px-2 py-4">
              <div 
                @click="toggleSelectAllFiltered"
                class="w-5 h-5 mx-auto rounded-md border-2 flex items-center justify-center transition-all bg-white cursor-pointer" 
                :class="isAllFilteredSelected ? 'bg-blue-600 border-blue-600' : 'border-gray-200 hover:border-blue-400'"
              >
                <CheckIcon v-if="isAllFilteredSelected" class="w-3.5 h-3.5 text-white" stroke-width="4" />
                <div v-else-if="isAnyFilteredSelected" class="w-2 h-0.5 bg-gray-400 rounded-full"></div>
              </div>
            </th>
            <th class="px-4 py-4 text-[10px] font-black text-gray-400 uppercase tracking-widest">Тип цели</th>
            <th class="px-4 py-4 text-[10px] font-black text-gray-400 uppercase tracking-widest">Название цели</th>
          </tr>
        </thead>
        <tbody>
          <!-- Loading State -->
          <template v-if="loading">
            <tr v-for="i in 5" :key="i" class="border-b border-gray-50">
              <td class="px-5 py-5 text-center"><Skeleton width="4" height="4" rounded="full" /></td>
              <td class="px-2 py-5"><Skeleton width="5" height="5" rounded="md" class="mx-auto" /></td>
              <td class="px-4 py-5"><Skeleton width="20" height="3" /></td>
              <td class="px-4 py-5"><Skeleton width="48" height="4" /></td>
            </tr>
          </template>

          <tr 
            v-else
            v-for="goal in sortedGoals" 
            :key="goal.id"
            class="border-b border-gray-50 last:border-none group hover:bg-blue-50/30 transition-all cursor-pointer"
            :class="{ 'bg-blue-50/50': selectedGoalIds.includes(goal.id) || primaryGoalId === goal.id }"
          >
            <!-- Primary Star -->
            <td class="px-5 py-4 text-center" @click.stop="$emit('selectPrimary', goal.id)">
              <button class="transition-all hover:scale-125 focus:outline-none">
                <StarIcon 
                   class="w-6 h-6 transition-colors duration-300" 
                  :class="primaryGoalId === goal.id ? 'text-yellow-400 fill-yellow-400 drop-shadow-[0_0_8px_rgba(250,204,21,0.4)]' : 'text-gray-200 group-hover:text-gray-300'"
                />
              </button>
            </td>

            <!-- Secondary Checkbox -->
            <td class="px-2 py-4" @click.stop="$emit('toggleSecondary', goal.id)">
              <div 
                class="w-5 h-5 mx-auto rounded-md border-2 flex items-center justify-center transition-all bg-white" 
                :class="selectedGoalIds.includes(goal.id) ? 'bg-blue-600 border-blue-600' : 'border-gray-200 group-hover:border-gray-400'"
              >
                <CheckIcon v-if="selectedGoalIds.includes(goal.id)" class="w-3.5 h-3.5 text-white" stroke-width="4" />
              </div>
            </td>

            <td class="px-4 py-4">
              <span 
                class="px-2.5 py-1 rounded-full text-[8px] font-black uppercase tracking-widest border"
                :class="getGoalTypeClass(goal.type)"
              >
                {{ formatGoalType(goal.type) }}
              </span>
            </td>

            <td class="px-4 py-4">
              <div class="flex flex-col">
                <div class="flex items-center gap-2 mb-0.5">
                  <span class="text-[13px] font-black text-gray-800 leading-tight group-hover:text-blue-600 transition-colors">
                    {{ goal.name }}
                  </span>
                  
                  <!-- IMPROVED: Recommendation Badge with Icon -->
                  <span 
                    v-if="goal.id === recommendedGoalId" 
                    class="inline-flex items-center gap-1 px-2 py-0.5 bg-gradient-to-r from-yellow-50 to-orange-50 text-orange-600 text-[8px] font-black uppercase rounded-md border border-orange-200 shadow-sm animate-pulse"
                  >
                    <StarIcon class="w-2.5 h-2.5 fill-orange-500" />
                    РЕКОМЕНДУЕМАЯ
                  </span>
                </div>
                <span class="text-[9px] text-gray-400 font-bold uppercase tracking-wider">ID: {{ goal.id }}</span>
              </div>
            </td>
          </tr>

          <tr v-if="!loading && filteredGoals.length === 0">
            <td colspan="5" class="py-20 text-center">
              <div class="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg class="w-8 h-8 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                </svg>
              </div>
              <p class="text-sm font-bold text-gray-600 mb-2" v-if="platform === 'VK_ADS'">
                Цели Метрики не требуются
              </p>
              <p class="text-sm font-bold text-gray-600 mb-2" v-else>
                Цели не найдены
              </p>
              <p class="text-xs text-gray-400" v-if="platform === 'VK_ADS'">
                Для VK Ads цели Яндекс.Метрики не используются. Вы можете продолжить без выбора целей.
              </p>
              <p class="text-xs text-gray-400" v-else>
                Данные синхронизируются в фоне. Если цели есть в Яндекс.Метрике,<br/>они появятся через несколько секунд.
              </p>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Error Hint -->
    <div v-if="showValidationError && !primaryGoalId && platform !== 'VK_ADS'" class="p-4 bg-red-50 border border-red-100 rounded-2xl flex items-center gap-3 animate-shake">
      <ExclamationTriangleIcon class="w-5 h-5 text-red-500" />
      <span class="text-[12px] font-bold text-red-600">Пожалуйста, выберите основную цель (нажмите на звездочку)</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { 
  MagnifyingGlassIcon,
  StarIcon
} from '@heroicons/vue/20/solid'
import { 
  CheckIcon,
  ExclamationTriangleIcon
} from '@heroicons/vue/24/outline'
import Skeleton from '../ui/Skeleton.vue'

const props = defineProps({
  goals: Array,
  primaryGoalId: [String, Number],
  selectedGoalIds: Array,
  loading: Boolean,
  platform: String,
  allFromProfile: Boolean,
  showValidationError: Boolean
})

const emit = defineEmits(['selectPrimary', 'toggleSecondary', 'bulkSelect', 'bulkDeselect'])

const searchQuery = ref('')

const recommendedGoalId = computed(() => {
  if (!props.goals || props.goals.length === 0) return null
  
  // Logic: Best CR/Reaches balance. For now, highest CR is a good surrogate.
  // Select first goal as recommended
  return props.goals[0]?.id
})

const filteredGoals = computed(() => {
  if (!props.goals) return []
  let list = props.goals
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(g => 
      (g.name && g.name.toLowerCase().includes(q)) || 
      (g.id && g.id.toString().includes(q))
    )
  }
  return list
})

const sortedGoals = computed(() => {
  return [...filteredGoals.value].sort((a, b) => {
    // Recommended goal always first
    if (a.id === recommendedGoalId.value) return -1
    if (b.id === recommendedGoalId.value) return 1
    return 0
  })
})

const isAllFilteredSelected = computed(() => {
  if (filteredGoals.value.length === 0) return false
  return filteredGoals.value.every(g => props.selectedGoalIds.includes(g.id))
})

const isAnyFilteredSelected = computed(() => {
  return filteredGoals.value.some(g => props.selectedGoalIds.includes(g.id))
})

const toggleSelectAllFiltered = () => {
  const ids = filteredGoals.value.map(g => g.id)
  if (isAllFilteredSelected.value) {
    emit('bulkDeselect', ids)
  } else {
    emit('bulkSelect', ids)
  }
}

const formatGoalType = (type) => {
  if (!type) return 'ЦЕЛЬ'
  const labels = {
    'AVERAGE_CPA': 'ЦЕНА КОНВЕРСИИ',
    'METRICA_GOAL': 'ЦЕЛЬ МЕТРИКИ',
    'AUTO': 'АВТОЦЕЛЬ',
    'YANDEX_METRICA': 'ЯНДЕКС МЕТРИКА'
  }
  return labels[type] || type.replace(/_/g, ' ')
}

const getGoalTypeClass = (type) => {
  if (type === 'METRICA_GOAL' || type === 'YANDEX_METRICA') return 'bg-orange-50 text-orange-600 border-orange-100'
  if (type === 'AUTO') return 'bg-blue-50 text-blue-600 border-blue-100'
  return 'bg-gray-50 text-gray-500 border-gray-100'
}
</script>

<style scoped>
@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-4px); }
  75% { transform: translateX(4px); }
}
.animate-shake {
  animation: shake 0.4s cubic-bezier(.36,.07,.19,.97) both;
}
</style>
