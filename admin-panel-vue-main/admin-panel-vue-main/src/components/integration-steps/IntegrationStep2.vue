<template>
  <div class="pr-1 pb-4 space-y-6">
    <div class="relative">
      <label class="block text-[9px] font-black text-gray-400 uppercase tracking-[0.2em] mb-3 px-1">ПРОФИЛЬ РЕКЛАМНОЙ КАМПАНИИ</label>
      
      <div class="relative">
        <button 
          type="button"
          @click="$emit('openProfileSelector')"
          class="w-full px-5 py-4 bg-white border border-gray-200 rounded-[1.25rem] focus:border-blue-500 transition-all flex items-center justify-between shadow-sm group hover:border-gray-300"
        >
          <div class="flex items-center gap-4">
            <div v-if="platform === 'YANDEX_DIRECT'" class="w-10 h-10 rounded-full flex items-center justify-center overflow-hidden">
              <svg viewBox="0 0 100 100" class="w-full h-full">
                <circle cx="50" cy="50" r="50" fill="#FFCC00"/>
                <path d="M65 25C58 25 52 30 52 38C52 46 58 51 65 51C72 51 78 46 78 38C78 30 72 25 65 25ZM65 41C63 41 62 39 62 38C62 37 63 35 65 35C67 35 68 37 68 38C68 39 67 41 65 41Z" fill="#000"/>
                <path d="M25 75L45 25H55L75 75H65L60 62H40L35 75H25ZM43 54H57L50 36L43 54Z" fill="#000"/>
              </svg>
            </div>
            <div class="text-left">
              <span class="block text-[14px] font-black text-black leading-none">
                {{ selectedAccountId || 'Выберите профиль' }}
              </span>
            </div>
          </div>
          <ChevronDownIcon class="w-5 h-5 text-gray-400 group-hover:text-black transition-all duration-300" />
        </button>
      </div>
    </div>

    <!-- Big Orange Next Button from Screenshot -->
    <div class="pt-2">
      <button 
        type="button"
        @click="$emit('next')"
        :disabled="!selectedAccountId || loading"
        class="w-full py-5 bg-[#FF4B21] hover:bg-[#ff3d0d] text-white rounded-[1.25rem] font-black text-[12px] uppercase tracking-widest transition-all shadow-lg hover:-translate-y-0.5 active:translate-y-0 disabled:opacity-50 disabled:translate-y-0"
      >
        ДАЛЕЕ
      </button>
    </div>
  </div>
</template>

<script setup>
import { ChevronDownIcon } from '@heroicons/vue/20/solid'

const props = defineProps({
  profiles: Array,
  selectedAccountId: String,
  loading: Boolean,
  platform: String
})

defineEmits(['openProfileSelector', 'next'])
</script>
