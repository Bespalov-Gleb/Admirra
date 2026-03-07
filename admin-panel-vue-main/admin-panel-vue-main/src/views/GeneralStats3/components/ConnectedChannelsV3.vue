<template>
  <div class="bg-white rounded-[10px] p-6 border border-gray-100 shadow-sm flex flex-col min-h-0 font-[Inter]">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-[18px] font-bold text-[#09183F]">Подключенные каналы</h3>
      <button
        type="button"
        @click="$emit('connect')"
        class="text-[15px] font-semibold text-[#2563EB] hover:text-[#1d4ed8]"
      >
        Добавить +
      </button>
    </div>

    <!-- Заголовки колонок -->
    <div class="grid grid-cols-[1fr_auto_auto] gap-3 px-1 mb-2 text-[13px] font-medium text-gray-400">
      <span>Название</span>
      <span>Баланс</span>
      <span>Статус</span>
    </div>

    <div class="space-y-2">
      <div
        v-for="platform in displayPlatforms"
        :key="platform.id"
        class="grid grid-cols-[1fr_auto_auto] gap-3 items-center py-2.5 px-1 rounded-lg transition-colors hover:bg-gray-50/50"
      >
        <div class="flex items-center gap-3 min-w-0">
          <div class="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 overflow-hidden">
            <img
              v-if="platform.id === 'yandex_direct'"
              :src="yandexDirectIcon"
              alt="Yandex Direct"
              class="w-full h-full object-contain"
            />
            <div
              v-else
              class="w-full h-full flex items-center justify-center font-bold text-[12px] bg-[#2787F5] text-white"
            >
              VK
            </div>
          </div>
          <span class="text-[16px] font-medium text-[#09183F] truncate">{{ platform.name }}</span>
        </div>
        <div class="flex items-center justify-end">
          <span
            v-if="platform.connected && platform.balance != null"
            class="inline-flex items-baseline gap-0.5 px-2.5 py-1 rounded-full text-[15px] font-semibold"
            :class="platform.id === 'yandex_direct' ? 'bg-orange-100 text-orange-700' : 'bg-gray-100 text-gray-700'"
          >
            {{ formatBalance(platform.balance) }}<span class="text-[12px] font-medium">₽</span>
          </span>
          <span v-else-if="platform.connected" class="text-[15px] text-gray-400">—</span>
          <span v-else class="text-[15px] text-gray-400">—</span>
        </div>
        <div class="flex justify-end">
          <button
            type="button"
            role="switch"
            :aria-checked="platform.connected"
            class="relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus:outline-none focus:ring-2 focus:ring-[#2563EB] focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-70"
            :class="platform.connected ? 'bg-[#82d944]' : 'bg-gray-200'"
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
import yandexDirectIcon from '@/assets/icons/yandex-direct.svg'

const props = defineProps({
  integrations: {
    type: Array,
    default: () => []
  }
})

defineEmits(['connect', 'toggle-channel'])

const platformRegistry = {
  yandex_direct: { name: 'Yandex Direct' },
  vk_ads: { name: 'VK Ads Manager' }
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
