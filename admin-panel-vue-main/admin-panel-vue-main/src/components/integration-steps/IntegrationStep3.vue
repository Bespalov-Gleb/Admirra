<template>
  <div class="pr-1 pb-4 space-y-6">
    <!-- Campaign Selection Trigger -->
    <div class="relative">
      <label class="block text-[9px] font-black text-gray-400 uppercase tracking-[0.2em] mb-3 px-1">РЕКЛАМНАЯ КАМПАНИЯ</label>
      
      <div class="relative">
        <button 
          type="button"
          @click="$emit('openCampaignSelector')"
          class="w-full px-5 py-4 bg-white border border-gray-200 rounded-[1.25rem] focus:border-blue-500 transition-all flex items-center justify-between shadow-sm group hover:border-gray-300 disabled:opacity-50 disabled:bg-gray-50"
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
              <span v-if="loading" class="flex items-center gap-2 text-[14px] font-black text-gray-400">
                <svg class="animate-spin h-3.5 w-3.5 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Поиск кампаний...
              </span>
              <span v-else class="block text-[14px] font-black text-black leading-none truncate max-w-[200px]">
                {{ displayText }}
              </span>
            </div>
          </div>
          <ChevronDownIcon class="w-5 h-5 text-gray-400 group-hover:text-black transition-all duration-300" />
        </button>
      </div>
    </div>

    <!-- All Campaigns Checkbox -->
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
        <span class="text-[14px] font-bold text-gray-700 tracking-tight">Все кампании из профиля</span>
      </label>
    </div>

  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ChevronDownIcon } from '@heroicons/vue/20/solid'
import { CheckIcon } from '@heroicons/vue/24/outline'

const props = defineProps({
  campaigns: Array,
  selectedIds: Array,
  loading: Boolean,
  platform: String,
  allFromProfile: Boolean
})

const emit = defineEmits(['openCampaignSelector', 'toggleAll', 'next'])

const displayText = computed(() => {
  if (props.allFromProfile) return 'Все кампании'
  if (props.selectedIds.length === 0) return 'Выберите кампании'
  if (props.selectedIds.length === 1) {
    const campaign = props.campaigns.find(c => c.id === props.selectedIds[0])
    return campaign ? `${campaign.external_id} ${campaign.name}` : 'Выбрана 1 кампания'
  }
  return `Выбрано ${props.selectedIds.length} камп.`
})
</script>
