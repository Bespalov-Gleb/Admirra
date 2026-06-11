<template>
  <div class="bg-white dark:bg-[#2A2D3C] rounded-[0.6944rem] p-6 border border-gray-100 dark:border-white/10 shadow-sm flex flex-col min-h-0 font-[Inter]">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-[1.25rem] font-normal text-[#09183F] dark:text-white">Подключенные каналы</h3>
      <button
        type="button"
        @click="$emit('connect')"
        class="text-[1.0417rem] font-normal text-[#2563EB] dark:text-[#4A7AFF] hover:text-[#1d4ed8] dark:hover:text-[#5A8BFF]"
      >
        Добавить +
      </button>
    </div>

    <!-- Заголовки колонок -->
    <div class="grid grid-cols-[1fr_auto_auto] gap-3 px-1 mb-2 text-[0.9028rem] font-normal text-gray-400 dark:text-gray-500">
      <span>Название</span>
      <span>Баланс</span>
      <span>Статус</span>
    </div>

    <div class="space-y-2">
        <div
        v-for="platform in displayPlatforms"
        :key="platform.id"
        class="grid grid-cols-[1fr_auto_auto] gap-3 items-center py-2.5 px-3 rounded-lg transition-colors"
        :class="platform.rowClass"
      >
        <div class="flex items-center gap-3 min-w-0">
          <div class="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 overflow-hidden">
            <img
              v-if="platform.id === 'yandex_direct'"
              :src="yandexDirectIcon"
              alt="Yandex Direct"
              class="w-full h-full object-contain"
            />
            <img
              v-else-if="platform.id === 'vk_ads'"
              :src="vkAdsIcon"
              alt="VK Ads"
              class="w-full h-full object-contain scale-[1.5] origin-center"
            />
            <img
              v-else-if="platform.id === 'avito_ads'"
              :src="avitoAdsIcon"
              alt="Avito Ads"
              class="w-full h-full object-contain"
            />
            <div
              v-else
              class="w-full h-full flex items-center justify-center font-normal text-[0.8333rem] bg-gray-200 text-gray-600"
            >
              ?
            </div>
          </div>
          <span class="text-[1.1111rem] font-normal text-[#2563EB] dark:text-[#4A7AFF] truncate">{{ platform.name }}</span>
        </div>
        <div class="flex items-center justify-end">
          <span
            v-if="platform.connected && platform.balance != null"
            class="inline-flex items-baseline gap-0.5 px-2.5 py-1 rounded-full text-[1.0417rem] font-normal"
            :class="platform.balanceClass"
          >
            {{ formatBalance(platform.balance) }}<span class="text-[0.8333rem] font-normal">₽</span>
          </span>
          <span v-else-if="platform.connected" class="text-[1.0417rem] text-gray-400">—</span>
          <span v-else class="text-[1.0417rem] text-gray-400">—</span>
        </div>
        <div class="flex justify-end">
          <button
            type="button"
            role="switch"
            :aria-checked="platform.connected"
            class="relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent bg-gray-200 dark:bg-gray-600 transition-colors focus:outline-none focus:ring-2 focus:ring-[#2563EB] focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-70"
            :disabled="!platform.connected"
            @click="platform.connected && $emit('toggle-channel', platform.id)"
          >
            <span
              class="pointer-events-none inline-block h-4 w-4 transform rounded-full shadow ring-0 transition"
              :class="platform.connected ? 'translate-x-4 bg-[#B8E986]' : 'translate-x-0.5 bg-white'"
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
import vkAdsIcon from '@/assets/icons/vk-ads.png'
import avitoAdsIcon from '@/assets/icons/avito.svg'

const props = defineProps({
  integrations: {
    type: Array,
    default: () => []
  }
})

defineEmits(['connect', 'toggle-channel'])

const platformRegistry = {
  yandex_direct: {
    name: 'Yandex Direct',
    rowClass: 'bg-orange-50 dark:bg-orange-500/10',
    balanceClass: 'bg-orange-100 text-orange-700',
  },
  vk_ads: {
    name: 'VK Ads Manager',
    rowClass: 'bg-blue-50 dark:bg-blue-500/10',
    balanceClass: 'bg-gray-100 text-gray-700',
  },
  avito_ads: {
    name: 'Avito Ads',
    rowClass: 'bg-emerald-50 dark:bg-emerald-500/10',
    balanceClass: 'bg-emerald-100 text-emerald-700',
  },
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
