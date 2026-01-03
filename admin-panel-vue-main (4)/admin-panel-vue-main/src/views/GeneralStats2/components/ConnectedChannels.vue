<template>
  <div class="!bg-white rounded-[40px] py-6 px-6 shadow-sm">
    <h3 class="text-lg font-semibold text-gray-900 mb-1">Подключенные каналы</h3>
    <p class="text-sm text-gray-500 mb-4">рекламные источники</p>
    
    <div class="flex items-center gap-2 mb-6">
      <!-- Яндекс.Директ -->
      <img 
        :src="yandexDirectImg" 
        alt="Яндекс Директ" 
        class="w-[50px] h-[50px] object-contain"
      />
      
      <!-- VK Ads -->
      <img 
        :src="vkAdsImg" 
        alt="VK Ads" 
        class="w-[65px] h-[65px] object-contain"
      />

      <!-- Metrika -->
      <img 
        :src="metrikaImg" 
        alt="Metrika" 
        class="w-[50px] h-[50px] object-contain"
      />
    </div>
    
    <button class="w-full flex items-center justify-center gap-2 px-4 sm:px-6 py-2.5 sm:py-3 border border-gray-300 rounded-[30px] bg-white text-sm text-gray-700 hover:bg-gray-50 transition-colors">
      <span class="text-center text-[11px]">Подключить или отключить канал</span>
      <ArrowPathIcon class="w-4 h-4 sm:w-5 sm:h-5 flex-shrink-0" />
    </button>
  </div>
</template>

<script setup>
import { ArrowPathIcon } from '@heroicons/vue/24/outline'
import yandexDirectImg from '../../../assets/imgs/yandexmetrika.png'
import vkAdsImg from '../../../assets/imgs/vk-ads.png'
import metrikaImg from '../../../assets/imgs/Metrika.png'
</script>


