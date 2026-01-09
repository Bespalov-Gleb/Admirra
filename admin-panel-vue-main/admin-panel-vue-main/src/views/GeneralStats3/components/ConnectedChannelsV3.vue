<template>
  <div class="bg-white rounded-[40px] px-8 py-8 shadow-sm border border-gray-50 h-full flex flex-col">
    <div class="flex items-center justify-between mb-8">
      <h3 class="text-xs font-black text-gray-400 uppercase tracking-[0.2em]">Подключенные каналы</h3>
      <button 
        @click="$emit('connect')"
        class="text-[10px] font-black uppercase text-blue-600 hover:text-blue-700 tracking-wider flex items-center gap-1 group"
      >
        Добавить
        <PlusIcon class="w-3 h-3 group-hover:rotate-90 transition-transform" />
      </button>
    </div>

    <div class="space-y-4 flex-grow">
      <div 
        v-for="platform in displayPlatforms" 
        :key="platform.id"
        class="flex items-center justify-between p-4 rounded-3xl border transition-all"
        :class="platform.connected ? 'bg-blue-50/30 border-blue-100 shadow-sm' : 'bg-gray-50/50 border-gray-100 opacity-60'"
      >
        <div class="flex items-center gap-4">
          <div 
             class="w-10 h-10 rounded-2xl flex items-center justify-center border shadow-sm"
             :class="platform.connected ? 'bg-white border-blue-100' : 'bg-gray-100 border-gray-200'"
          >
            <component :is="platform.icon" class="w-5 h-5" :class="platform.connected ? 'text-blue-600' : 'text-gray-400'" />
          </div>
          <div class="flex flex-col">
            <span class="text-sm font-black text-gray-900 leading-tight">{{ platform.name }}</span>
            <span class="text-[10px] font-bold" :class="platform.connected ? 'text-blue-500' : 'text-gray-400'">
              {{ platform.connected ? 'Активно' : 'Не подключено' }}
            </span>
          </div>
        </div>
        
        <div v-if="platform.connected" class="w-2 h-2 rounded-full bg-blue-500 animate-pulse"></div>
        <PlusIcon v-else @click="$emit('connect')" class="w-4 h-4 text-gray-300 cursor-pointer hover:text-gray-500" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { PlusIcon } from '@heroicons/vue/24/solid'
import { 
  GlobeAltIcon, 
  ChatBubbleBottomCenterTextIcon,
  PlayCircleIcon
} from '@heroicons/vue/24/outline'

const props = defineProps({
  integrations: {
    type: Array,
    default: () => []
  }
})

defineEmits(['connect'])

const platformRegistry = {
  yandex_direct: { name: 'Яндекс.Директ', icon: GlobeAltIcon },
  vk_ads: { name: 'VK Ads', icon: ChatBubbleBottomCenterTextIcon },
  google_ads: { name: 'Google Ads', icon: PlayCircleIcon },
  facebook_ads: { name: 'Facebook Ads', icon: PlayCircleIcon },
  instagram: { name: 'Instagram', icon: PlayCircleIcon },
  telegram: { name: 'Telegram Ads', icon: ChatBubbleBottomCenterTextIcon }
}

const displayPlatforms = computed(() => {
  return Object.entries(platformRegistry).map(([id, info]) => {
    const integration = props.integrations.find(i => i.platform === id)
    return {
      id,
      ...info,
      connected: integration ? integration.is_connected : false
    }
  })
})
</script>
