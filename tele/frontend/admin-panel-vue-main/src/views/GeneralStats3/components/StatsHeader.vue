<template>
  <div class="flex flex-col gap-0.5 min-w-0">
    <!-- Top Label to match Filter labels height and alignment -->
    <label class="text-[9px] font-black text-gray-400 uppercase tracking-widest ml-1 opacity-70">
      {{ label }}
    </label>
    
    <div class="flex items-center gap-3">
      <div class="p-2 bg-blue-600 rounded-xl shadow-lg shadow-blue-200 hidden xs:block">
        <ChartBarIcon class="w-4 h-4 text-white" />
      </div>
      
      <div class="flex flex-col min-w-0">
        <div class="flex items-center gap-2">
          <h1 class="text-xl sm:text-2xl font-black text-gray-900 tracking-tight truncate">
            {{ title }}
          </h1>
          
          <button 
            v-if="showReset" 
            @click="$emit('reset')"
            class="flex-shrink-0 px-2 py-0.5 bg-blue-50 text-blue-600 text-[9px] font-black uppercase rounded-full hover:bg-blue-600 hover:text-white transition-all duration-300 flex items-center gap-1 shadow-sm border border-blue-100/50 group"
          >
            <span>Сбросить</span>
            <ArrowPathIcon class="w-2.5 h-2.5 group-hover:rotate-180 transition-transform duration-500" />
          </button>
        </div>
        
        <div class="flex items-center gap-1.5 mt-0.5">
          <div class="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse flex-shrink-0"></div>
          <p class="text-[9px] font-bold text-gray-400 uppercase tracking-wider truncate">
            {{ subtitle }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ChartBarIcon, ArrowPathIcon } from '@heroicons/vue/24/solid'

defineProps({
  label: {
    type: String,
    default: 'Аналитика'
  },
  title: {
    type: String,
    required: true
  },
  subtitle: {
    type: String,
    default: 'Общая аналитика и управление'
  },
  showReset: {
    type: Boolean,
    default: false
  }
})

defineEmits(['reset'])
</script>
