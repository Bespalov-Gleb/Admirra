<template>
  <div class="space-y-8 py-2">
    <!-- Header -->
    <div class="text-center space-y-2">
      <div class="inline-flex items-center justify-center w-16 h-16 bg-blue-50 rounded-full mb-2">
        <ClipboardDocumentCheckIcon class="w-8 h-8 text-blue-600" />
      </div>
      <h2 class="text-xl font-black text-gray-900 uppercase tracking-tight">Просмотр настроек</h2>
      <p class="text-[13px] text-gray-500 font-bold max-w-sm mx-auto">
        Пожалуйста, проверьте выбранные параметры перед окончательным подключением интеграции.
      </p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <!-- Left Column: Basics & Campaigns -->
      <div class="space-y-6">
        <!-- Project & Platform -->
        <div class="bg-white border border-gray-100 rounded-3xl p-6 shadow-sm hover:shadow-md transition-shadow">
          <div class="flex items-center gap-3 mb-4">
            <div class="w-10 h-10 bg-blue-50 rounded-2xl flex items-center justify-center">
              <BuildingOfficeIcon class="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p class="text-[9px] font-black text-gray-400 uppercase tracking-widest">Проект и платформа</p>
              <h3 class="text-[14px] font-black text-gray-900">{{ projectName || 'Не выбран' }}</h3>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <span class="px-3 py-1 bg-orange-50 text-orange-600 rounded-full text-[10px] font-black uppercase tracking-wider border border-orange-100">Яндекс Директ</span>
            <span class="text-[11px] font-bold text-gray-400 italic">Активный проект</span>
          </div>
        </div>

        <!-- Selected Campaigns -->
        <div class="bg-white border border-gray-100 rounded-3xl p-6 shadow-sm hover:shadow-md transition-shadow">
          <div class="flex items-center gap-3 mb-4">
            <div class="w-10 h-10 bg-indigo-50 rounded-2xl flex items-center justify-center">
              <MegaphoneIcon class="w-5 h-5 text-indigo-600" />
            </div>
            <div>
              <p class="text-[9px] font-black text-gray-400 uppercase tracking-widest">Кампании</p>
              <h3 class="text-[14px] font-black text-gray-900">Выбрано: {{ selectedCampaigns.length }}</h3>
            </div>
          </div>
          <div class="max-h-40 overflow-y-auto space-y-2 pr-2 custom-scrollbar">
            <div 
              v-for="campaign in selectedCampaigns" 
              :key="campaign.id"
              class="flex items-center gap-2 p-2 bg-gray-50 rounded-xl border border-gray-100/50"
            >
              <div class="w-1.5 h-1.5 rounded-full bg-green-500"></div>
              <span class="text-[11px] font-bold text-gray-700 truncate">{{ campaign.name }}</span>
            </div>
          </div>
        </div>

        <!-- Selected Counters -->
        <div class="bg-white border border-gray-100 rounded-3xl p-6 shadow-sm hover:shadow-md transition-shadow">
          <div class="flex items-center gap-3 mb-4">
            <div class="w-10 h-10 bg-purple-50 rounded-2xl flex items-center justify-center">
              <ChartBarIcon class="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <p class="text-[9px] font-black text-gray-400 uppercase tracking-widest">Счетчики Метрики</p>
              <h3 class="text-[14px] font-black text-gray-900">Выбрано: {{ selectedCounters.length }}</h3>
            </div>
          </div>
          <div class="max-h-40 overflow-y-auto space-y-2 pr-2 custom-scrollbar">
            <div 
              v-for="counter in selectedCounters" 
              :key="counter.id"
              class="flex items-center gap-2 p-2 bg-gray-50 rounded-xl border border-gray-100/50"
            >
              <div class="w-1.5 h-1.5 rounded-full bg-purple-500"></div>
              <span class="text-[11px] font-bold text-gray-700 truncate">{{ counter.name }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Right Column: Profile & Goals -->
      <div class="space-y-6">
        <!-- Selected Goals -->
        <div class="bg-white border border-gray-100 rounded-3xl p-6 shadow-sm hover:shadow-md transition-shadow">
          <div class="flex items-center gap-3 mb-4">
            <div class="w-10 h-10 bg-orange-50 rounded-2xl flex items-center justify-center">
              <PresentationChartLineIcon class="w-5 h-5 text-orange-600" />
            </div>
            <div>
              <p class="text-[9px] font-black text-gray-400 uppercase tracking-widest">Настройка целей</p>
              <h3 class="text-[14px] font-black text-gray-900">Основная: {{ primaryGoalName || 'Не выбрана' }}</h3>
            </div>
          </div>
          <div class="space-y-3">
             <div v-if="primaryGoalName" class="flex items-center gap-2 p-2.5 bg-orange-50/50 rounded-xl border border-orange-100">
              <StarIcon class="w-4 h-4 text-orange-400 fill-orange-400" />
              <span class="text-[11px] font-black text-orange-900 truncate">{{ primaryGoalName }}</span>
            </div>
            <p v-if="secondaryGoals.length > 0" class="text-[9px] font-black text-gray-400 uppercase tracking-widest pl-1 mt-4">Дополнительные цели ({{ secondaryGoals.length }}):</p>
            <div class="max-h-24 overflow-y-auto space-y-2 pr-2 custom-scrollbar">
              <div 
                v-for="goal in secondaryGoals" 
                :key="goal.id"
                class="flex items-center gap-2 p-2 bg-blue-50/30 rounded-xl border border-blue-50"
              >
                <CheckIcon class="w-3 h-3 text-blue-500" stroke-width="3" />
                <span class="text-[11px] font-bold text-gray-600 truncate">{{ goal.name }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Final Checkbox & Settings -->
    <div class="bg-blue-600 rounded-[2rem] p-8 text-white shadow-xl relative overflow-hidden group">
      <!-- Decorative circles -->
      <div class="absolute -top-12 -right-12 w-48 h-48 bg-white/10 rounded-full transition-transform group-hover:scale-110"></div>
      <div class="absolute -bottom-8 -left-8 w-24 h-24 bg-white/10 rounded-full transition-transform group-hover:scale-125"></div>
      
      <div class="relative z-10 flex flex-col md:flex-row items-center justify-between gap-6">
        <div class="space-y-4">
          <div class="flex items-center gap-4">
             <div class="w-12 h-12 bg-white/20 rounded-2xl flex items-center justify-center backdrop-blur-sm">
                <ArrowPathRoundedSquareIcon class="w-6 h-6 text-white" />
             </div>
             <div>
               <p class="text-[10px] font-black text-blue-100 uppercase tracking-widest leading-none mb-1">Глубина и Автосинхрон</p>
               <h3 class="text-[17px] font-black">Синхронизация за 30 дней</h3>
             </div>
          </div>
          <div class="flex items-center gap-3">
            <div 
              class="w-10 h-5 bg-white/20 rounded-full p-1 cursor-not-allowed flex shadow-inner opacity-100"
            >
              <div class="w-3 h-3 bg-white rounded-full shadow-md ml-auto"></div>
            </div>
            <span class="text-[12px] font-black uppercase tracking-wider text-blue-50">Автоматическая синхронизация включена</span>
          </div>
        </div>
        
        <div class="text-center md:text-right">
          <p class="text-[10px] font-black text-blue-100 uppercase tracking-widest mb-2">Нажмите кнопку ниже для старта</p>
          <div class="flex items-center gap-2 justify-center md:justify-end">
            <SparklesIcon class="w-5 h-5 text-yellow-300 animate-pulse" />
            <span class="text-lg font-black italic">Готовность 100%</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { 
  ClipboardDocumentCheckIcon, 
  BuildingOfficeIcon,
  MegaphoneIcon,
  ChartBarIcon,
  PresentationChartLineIcon,
  StarIcon,
  SparklesIcon,
  ArrowPathRoundedSquareIcon
} from '@heroicons/vue/24/solid'
import { CheckIcon } from '@heroicons/vue/24/outline'

const props = defineProps({
  projectName: String,
  selectedCampaigns: {
    type: Array,
    default: () => []
  },
  selectedCounters: {
    type: Array,
    default: () => []
  },
  selectedGoals: {
    type: Array,
    default: () => []
  },
  primaryGoalId: [String, Number]
})

const primaryGoalName = computed(() => {
  if (!props.primaryGoalId) return null
  const goal = props.selectedGoals.find(g => g.id === props.primaryGoalId)
  return goal?.name || null
})

const secondaryGoals = computed(() => {
  return props.selectedGoals.filter(g => g.id !== props.primaryGoalId)
})
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #e5e7eb;
  border-radius: 10px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: #d1d5db;
}
</style>

