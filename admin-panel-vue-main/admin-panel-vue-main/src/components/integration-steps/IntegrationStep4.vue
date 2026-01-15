<template>
  <div class="pr-1 pb-4 space-y-6">
    <!-- Primary Goal Selection Trigger -->
    <div class="relative">
      <label class="block text-[9px] font-black text-gray-400 uppercase tracking-[0.2em] mb-3 px-1">ОСНОВНАЯ ЦЕЛЬ :</label>
      
      <div class="relative">
        <button 
          type="button"
          @click="$emit('openGoalSelector')"
          class="w-full px-5 py-4 bg-white border border-gray-200 rounded-[1.25rem] focus:border-blue-500 transition-all flex items-center justify-between shadow-sm group hover:border-gray-300"
          :class="{ 'border-red-300 bg-red-50/10': showValidationError && !primaryGoalId }"
        >
          <div class="flex items-center gap-4">
            <div v-if="platform === 'YANDEX_DIRECT'" class="w-10 h-10 rounded-full flex items-center justify-center overflow-hidden">
              <svg viewBox="0 0 100 100" class="w-full h-full">
                <circle cx="50" cy="50" r="50" fill="#FFCC00"/>
                <path d="M65 25C58 25 52 30 52 38C52 46 58 51 65 51C72 51 78 46 78 38C78 30 72 25 65 25ZM65 41C63 41 62 39 62 38C62 37 63 35 65 35C67 35 68 37 68 38C68 39 67 41 65 41Z" fill="#000"/>
                <path d="M25 75L45 25H55L75 75H65L60 62H40L35 75H25ZM43 54H57L50 36L43 54Z" fill="#000"/>
              </svg>
            </div>
            <div class="text-left overflow-hidden">
              <span class="block text-[14px] font-black text-black leading-none truncate max-w-[200px]">
                {{ primaryGoalName || 'Выберите основную цель' }}
              </span>
            </div>
          </div>
          <ChevronDownIcon class="w-5 h-5 text-gray-400 group-hover:text-black transition-all duration-300" />
        </button>
      </div>
    </div>

    <!-- Secondary Goals Section -->
    <div class="space-y-4">
      <div class="flex items-center justify-between">
        <h4 class="text-[14px] font-bold text-gray-700 tracking-tight">Цели для блока с конверсиями:</h4>
      </div>

      <!-- Search Input -->
      <div class="relative group">
        <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
          <MagnifyingGlassIcon class="h-4 w-4 text-gray-400 group-focus-within:text-blue-500 transition-colors" />
        </div>
        <input 
          type="text" 
          v-model="searchQuery"
          placeholder="Поиск по названию или ID..."
          class="block w-full pl-11 pr-4 py-3 bg-gray-50 border-none rounded-2xl text-[13px] font-bold text-gray-900 placeholder-gray-400 focus:ring-2 focus:ring-blue-500/20 transition-all"
        >
      </div>

      <!-- All Goals Checkbox -->
      <div class="flex items-center px-1">
        <label class="flex items-center gap-3 cursor-pointer group">
          <div class="relative w-5 h-5">
            <input 
              type="checkbox" 
              :checked="allFromProfile"
              @change="$emit('toggleAll')"
              class="peer sr-only"
            >
            <div class="w-5 h-5 bg-white border-2 border-gray-200 rounded-md transition-all peer-checked:bg-blue-600 peer-checked:border-blue-600 group-hover:border-gray-300"></div>
            <CheckIcon class="absolute inset-0 w-5 h-5 text-white scale-0 transition-all peer-checked:scale-100" stroke-width="4" />
          </div>
          <span class="text-[14px] font-bold text-gray-700 tracking-tight">Все цели из профиля</span>
        </label>
      </div>

      <!-- Goals Table -->
      <div class="bg-white border border-gray-200 rounded-2xl overflow-hidden shadow-sm">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-gray-50 border-b border-gray-100">
              <th class="w-10 px-4 py-3"></th>
              <th class="px-3 py-3 text-[10px] font-black text-gray-400 uppercase tracking-widest">Тип</th>
              <th class="px-3 py-3 text-[10px] font-black text-gray-400 uppercase tracking-widest">Номер</th>
              <th class="px-3 py-3 text-[10px] font-black text-gray-400 uppercase tracking-widest">Название</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading" v-for="i in 3" :key="i" class="animate-pulse border-b border-gray-50">
               <td colspan="4" class="px-4 py-4 h-12 bg-gray-50/50"></td>
            </tr>
            <tr 
              v-else
              v-for="goal in filteredGoals" 
              :key="goal.id"
              class="border-b border-gray-50 last:border-none group hover:bg-blue-50/30 transition-all cursor-pointer"
              :class="{ 'bg-blue-50/50': selectedGoalIds.includes(goal.id) }"
              @click="$emit('toggleSecondary', goal.id)"
            >
              <td class="px-4 py-3">
                <div class="w-5 h-5 rounded-md border-2 flex items-center justify-center transition-all bg-white" :class="selectedGoalIds.includes(goal.id) ? 'bg-blue-600 border-blue-600' : 'border-gray-200 group-hover:border-gray-400'">
                  <CheckIcon v-if="selectedGoalIds.includes(goal.id)" class="w-3.5 h-3.5 text-white" stroke-width="4" />
                </div>
              </td>
              <td class="px-3 py-3 text-[11px] font-medium text-gray-600 truncate max-w-[80px]" :title="goal.type">{{ goal.type }}</td>
              <td class="px-3 py-3 text-[11px] font-bold text-gray-400 uppercase">{{ goal.id }}</td>
              <td class="px-3 py-3 text-[11px] font-black text-gray-800">{{ goal.name }}</td>
            </tr>
            <tr v-if="!loading && filteredGoals.length === 0">
              <td colspan="4" class="py-12 text-center text-[11px] font-black text-gray-300 uppercase tracking-widest">Цели не найдены</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ChevronDownIcon, MagnifyingGlassIcon } from '@heroicons/vue/20/solid'
import { CheckIcon } from '@heroicons/vue/24/outline'

const props = defineProps({
  goals: Array,
  primaryGoalId: [String, Number],
  selectedGoalIds: Array,
  loading: Boolean,
  platform: String,
  allFromProfile: Boolean,
  showValidationError: Boolean
})

const emit = defineEmits(['openGoalSelector', 'toggleAll', 'toggleSecondary', 'finish'])


const searchQuery = ref('')

const filteredGoals = computed(() => {
  if (!searchQuery.value) return props.goals
  const q = searchQuery.value.toLowerCase()
  return props.goals.filter(g => 
    (g.name && g.name.toLowerCase().includes(q)) || 
    (g.id && g.id.toString().includes(q))
  )
})

const primaryGoalName = computed(() => {
  if (!props.primaryGoalId) return null
  const goal = props.goals.find(g => g.id === props.primaryGoalId)
  return goal ? `${goal.name} (${goal.id})` : props.primaryGoalId
})
</script>
