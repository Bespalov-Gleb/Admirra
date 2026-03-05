<template>
  <div class="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-sm font-bold text-gray-900">Подключенные каналы</h3>
      <button
        type="button"
        @click="$emit('connect')"
        class="text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center gap-1"
      >
        Добавить
        <PlusIcon class="w-3.5 h-3.5" />
      </button>
    </div>

    <div class="space-y-3">
      <div
        v-for="platform in displayPlatforms"
        :key="platform.id"
        class="flex items-center justify-between p-3 rounded-xl border transition-all"
        :class="platform.connected ? 'bg-blue-50/40 border-blue-100' : 'bg-gray-50/50 border-gray-100 opacity-60'"
      >
        <div class="flex items-center gap-3">
          <div
            class="w-9 h-9 rounded-xl flex items-center justify-center"
            :class="platform.connected ? 'bg-white border border-blue-100' : 'bg-gray-100'"
          >
            <component :is="platform.icon" class="w-4 h-4" :class="platform.connected ? 'text-blue-600' : 'text-gray-400'" />
          </div>
          <div class="flex flex-col">
            <span class="text-sm font-semibold text-gray-900">{{ platform.name }}</span>
            <span class="text-[10px] font-medium" :class="platform.connected ? 'text-blue-600' : 'text-gray-400'">
              {{ platform.connected ? 'Активно' : 'Не подключено' }}
            </span>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <span v-if="platform.connected && platform.balance != null" class="text-xs font-bold text-gray-700">
            {{ formatBalance(platform.balance) }} ₽
          </span>
          <span v-else-if="platform.connected" class="text-xs text-gray-400">—</span>
          <span v-else class="w-2 h-2 rounded-full bg-gray-300"></span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { PlusIcon } from '@heroicons/vue/24/solid'
import { GlobeAltIcon, ChatBubbleBottomCenterTextIcon } from '@heroicons/vue/24/outline'

const props = defineProps({
  integrations: {
    type: Array,
    default: () => []
  }
})

defineEmits(['connect'])

const platformRegistry = {
  yandex_direct: { name: 'Yandex Direct', icon: GlobeAltIcon },
  vk_ads: { name: 'VK Ads Manager', icon: ChatBubbleBottomCenterTextIcon }
}

const displayPlatforms = computed(() => {
  return Object.entries(platformRegistry).map(([id, info]) => {
    const item = props.integrations.find(i => {
      const p = String(i.platform || '').toLowerCase().replace(/-/g, '_')
      return p === id
    })
    return {
      id,
      ...info,
      connected: item ? (item.is_connected !== false) : false,
      balance: item?.balance ?? null
    }
  })
})

const formatBalance = (val) => {
  if (val == null) return '—'
  const n = typeof val === 'number' ? val : parseFloat(val)
  return isNaN(n) ? '—' : n.toLocaleString('ru-RU', { maximumFractionDigits: 0 })
}
</script>
