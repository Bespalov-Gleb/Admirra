<template>
  <div class="bg-white rounded-2xl p-6 border border-gray-100 shadow-md">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-sm font-bold text-gray-900">Подключенные каналы</h3>
      <button
        type="button"
        @click="$emit('connect')"
        class="text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center gap-1"
      >
        Добавить +
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
        <div class="flex items-center gap-3">
          <span v-if="platform.connected && platform.balance != null" class="text-xs font-bold text-gray-700">
            {{ formatBalance(platform.balance) }}P
          </span>
          <span v-else-if="platform.connected" class="text-xs text-gray-400">—</span>
          <button
            type="button"
            role="switch"
            :aria-checked="platform.connected"
            class="relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-70"
            :class="platform.connected ? 'bg-green-500' : 'bg-gray-200'"
            :disabled="!platform.connected"
            @click="platform.connected && $emit('toggle-channel', platform.id)"
          >
            <span
              class="pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition"
              :class="platform.connected ? 'translate-x-4' : 'translate-x-0.5'"
            />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { GlobeAltIcon, ChatBubbleBottomCenterTextIcon } from '@heroicons/vue/24/outline'

const props = defineProps({
  integrations: {
    type: Array,
    default: () => []
  }
})

defineEmits(['connect', 'toggle-channel'])

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
