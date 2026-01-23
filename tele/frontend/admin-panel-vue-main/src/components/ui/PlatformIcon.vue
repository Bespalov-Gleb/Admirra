<template>
  <div v-if="platform === 'YANDEX_DIRECT'" :class="sizeClass" class="rounded-full flex items-center justify-center overflow-hidden">
    <svg viewBox="0 0 100 100" class="w-full h-full">
      <circle cx="50" cy="50" r="50" fill="#FFCC00"/>
      <path d="M65 25C58 25 52 30 52 38C52 46 58 51 65 51C72 51 78 46 78 38C78 30 72 25 65 25ZM65 41C63 41 62 39 62 38C62 37 63 35 65 35C67 35 68 37 68 38C68 39 67 41 65 41Z" fill="#000"/>
      <path d="M25 75L45 25H55L75 75H65L60 62H40L35 75H25ZM43 54H57L50 36L43 54Z" fill="#000"/>
    </svg>
  </div>
  <div v-else-if="platform === 'VK_ADS'" :class="[sizeClass, 'bg-[#0077FF]']" class="rounded-xl flex items-center justify-center text-[11px] font-black text-white shadow-sm border border-[#0066EE]">
    VK
  </div>
  <div v-else :class="sizeClass" class="bg-gray-100 rounded-xl flex items-center justify-center text-[10px] font-black text-gray-400 uppercase border border-gray-200">
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

const sizeClass = computed(() => {
  switch (props.size) {
    case 'sm': return 'w-6 h-6'
    case 'lg': return 'w-12 h-12'
    default: return 'w-10 h-10'
  }
})
</script>
