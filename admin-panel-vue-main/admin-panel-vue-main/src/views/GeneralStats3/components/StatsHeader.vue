<template>
  <div class="flex flex-col gap-0.5 min-w-0">
    <!-- Top Label to match Filter labels height and alignment -->
    <label class="text-[0.625rem] font-black text-gray-400 dark:text-gray-500 uppercase tracking-widest ml-1 opacity-70">
      {{ label }}
    </label>
    
    <div class="flex items-center gap-3">
      <div class="p-2 bg-blue-600 dark:bg-[#4A7AFF] rounded-xl shadow-lg shadow-blue-200 dark:shadow-none hidden xs:block">
        <ChartBarIcon class="w-4 h-4 text-white" />
      </div>
      
      <div class="flex flex-col min-w-0">
        <div class="flex items-center gap-2">
          <h1 class="text-[1.6667rem] font-normal text-gray-900 dark:text-white truncate sm:text-[2.0833rem]">
            {{ title }}
          </h1>
          
          <button 
            v-if="showReset" 
            @click="$emit('reset')"
            class="flex-shrink-0 px-2 py-0.5 bg-blue-50 dark:bg-[#4A7AFF]/15 text-blue-600 dark:text-[#8BB7FF] text-[0.625rem] font-black uppercase rounded-full hover:bg-blue-600 dark:hover:bg-[#4A7AFF] hover:text-white transition-all duration-300 flex items-center gap-1 shadow-sm border border-blue-100/50 dark:border-[#4A7AFF]/20 group"
          >
            <span>Сбросить</span>
            <ArrowPathIcon class="w-2.5 h-2.5 group-hover:rotate-180 transition-transform duration-500" />
          </button>
        </div>
        
        <div class="flex items-center gap-1.5 mt-0.5">
          <div class="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse flex-shrink-0"></div>
          <p class="text-[1.0417rem] font-normal text-gray-400 dark:text-gray-500 truncate">
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
