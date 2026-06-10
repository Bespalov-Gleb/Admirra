<template>
  <div v-if="normalizedPlatform === 'YANDEX_DIRECT'" :class="sizeClass" class="rounded-full flex items-center justify-center overflow-hidden">
    <img :src="yandexDirectIcon" alt="Яндекс Директ" class="w-full h-full object-contain" />
  </div>
  <div v-else-if="normalizedPlatform === 'VK_ADS'" :class="sizeClass" class="rounded-xl flex items-center justify-center overflow-hidden">
    <img :src="vkAdsIcon" alt="VK Ads" class="w-full h-full object-contain" />
  </div>
  <div v-else-if="normalizedPlatform === 'AVITO_ADS'" :class="sizeClass" class="rounded-xl flex items-center justify-center overflow-hidden">
    <img :src="avitoIcon" alt="Avito Ads" class="w-full h-full object-contain" />
  </div>
  <div v-else :class="sizeClass" class="bg-gray-100 rounded-xl flex items-center justify-center text-[0.6944rem] font-black text-gray-400 uppercase border border-gray-200">
    ?
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  platform: String,
  size: {
    type: String,
    default: 'md' // sm, md, lg
  }
})

const yandexDirectIcon = '/admirra/img/icons/yandex-direct.png'
const vkAdsIcon = '/admirra/img/icons/vk-ads.png'
const avitoIcon = '/admirra/img/icons/avito.svg'

const normalizedPlatform = computed(() => {
  const code = String(props.platform || '').toUpperCase()
  if (code.includes('YANDEX') || code.includes('DIRECT')) return 'YANDEX_DIRECT'
  if (code.includes('VK')) return 'VK_ADS'
  if (code.includes('AVITO')) return 'AVITO_ADS'
  return code
})

const sizeClass = computed(() => {
  switch (props.size) {
    case 'sm': return 'w-6 h-6'
    case 'lg': return 'w-12 h-12'
    default: return 'w-10 h-10'
  }
})
</script>
