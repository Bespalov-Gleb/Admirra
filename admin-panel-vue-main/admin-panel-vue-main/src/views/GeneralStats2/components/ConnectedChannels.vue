<script setup>
import { ArrowPathIcon } from '@heroicons/vue/24/outline'

const props = defineProps({
  integrations: {
    type: Array,
    default: () => []
  }
})

const getStatus = (platform) => {
  const integration = props.integrations.find(i => i.platform === platform)
  return integration ? integration.is_connected : false
}
</script>

<template>
  <div class="bg-white rounded-[40px] p-8 ">
    <h3 class="text-lg font-semibold text-gray-900 mb-1">Подключенные каналы</h3>
    <p class="text-sm text-gray-500 mb-4">рекламные источники</p>
    
    <div class="flex items-center gap-4 mb-6">
      <!-- Яндекс.Директ -->
      <div 
        class="min-w-12 min-h-12 rounded-full flex items-center justify-center transition-opacity"
        :class="getStatus('yandex_direct') ? 'bg-yellow-400' : 'bg-gray-200 opacity-50'"
      >
        <svg class="w-6 h-6 text-blue-600" fill="currentColor" viewBox="0 0 24 24">
          <path d="M12 2L2 7v10l10 5 10-5V7L12 2z"/>
        </svg>
      </div>
      
      <!-- VK -->
      <div 
        class="min-w-12 min-h-12 rounded-full flex items-center justify-center transition-opacity"
        :class="getStatus('vk_ads') ? 'bg-blue-600' : 'bg-gray-200 opacity-50'"
      >
        <div class="flex gap-0.5">
          <div class="w-1 h-4 bg-white rounded"></div>
          <div class="w-1 h-4 bg-white/50 rounded"></div>
        </div>
      </div>

      <!-- Google Ads (Example of how to handle more) -->
      <div 
        class="min-w-12 min-h-12 rounded-full flex items-center justify-center transition-opacity"
        :class="getStatus('google_ads') ? 'bg-blue-500' : 'bg-gray-200 opacity-50'"
      >
        <span class="text-white font-bold text-lg">G</span>
      </div>
    </div>
    
    <button class="w-full flex items-center justify-center gap-2 px-4 sm:px-6 py-2.5 sm:py-3 border border-gray-300 rounded-lg bg-white text-sm text-gray-700 hover:bg-gray-50 transition-colors">
      <ArrowPathIcon class="w-4 h-4 sm:w-5 sm:h-5 flex-shrink-0" />
      <span class="text-center">Подключить или отключить канал</span>
    </button>
  </div>
</template>


