<template>
  <div class="bg-white rounded-[40px] px-6 sm:px-10 py-8 shadow-sm border border-gray-50 overflow-hidden">
    <div class="flex items-center justify-between mb-8">
      <h3 class="text-xl font-bold text-gray-900">Детальная статистика по кампаниям</h3>
      <div class="relative">
        <input 
          v-model="searchQuery" 
          type="text" 
          placeholder="Поиск кампании..." 
          class="pl-10 pr-4 py-2 text-sm border border-gray-100 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 bg-gray-50/50 transition-all w-64"
        />
        <MagnifyingGlassIcon class="absolute left-3 top-2.5 w-4 h-4 text-gray-400" />
      </div>
    </div>
    
    <div class="overflow-x-auto -mx-2">
      <table class="w-full text-left border-separate border-spacing-y-2">
        <thead>
          <tr class="text-[10px] font-black text-gray-400 uppercase tracking-widest">
            <th class="px-6 py-2">Название кампании</th>
            <th class="px-4 py-2 text-right">Показы</th>
            <th class="px-4 py-2 text-right">Клики</th>
            <th class="px-4 py-2 text-right">Расход, ₽</th>
            <th class="px-4 py-2 text-right">Лиды</th>
            <th class="px-4 py-2 text-right">CPC</th>
            <th class="px-6 py-2 text-right">CPA</th>
          </tr>
        </thead>
        <tbody class="divide-y-0">
          <tr v-if="loading" v-for="i in 3" :key="i">
            <td colspan="7" class="px-2">
              <div class="h-16 bg-gray-50/50 rounded-2xl animate-pulse"></div>
            </td>
          </tr>
          
          <tr v-else-if="filteredCampaigns.length === 0">
            <td colspan="7" class="px-6 py-10 text-center text-gray-400 font-medium">
              Кампании не найдены
            </td>
          </tr>

          <tr 
            v-for="campaign in filteredCampaigns" 
            :key="campaign.name" 
            class="group hover:bg-blue-50/30 transition-all cursor-default"
          >
            <td class="px-6 py-4 rounded-l-2xl">
              <div class="flex flex-col">
                <span class="text-sm font-bold text-gray-900 line-clamp-1" :title="campaign.name">
                  {{ campaign.name }}
                </span>
                <span class="text-[10px] font-bold text-gray-400 uppercase tracking-tighter">
                  {{ campaign.name.includes('[VK]') ? 'ВКонтакте Ads' : 'Яндекс.Директ' }}
                </span>
              </div>
            </td>
            <td class="px-4 py-4 text-right">
              <span class="text-sm font-bold text-gray-600">
                {{ (campaign.impressions || 0).toLocaleString() }}
              </span>
            </td>
            <td class="px-4 py-4 text-right">
              <span class="text-sm font-bold text-gray-600">
                {{ (campaign.clicks || 0).toLocaleString() }}
              </span>
            </td>
            <td class="px-4 py-4 text-right">
              <span class="text-sm font-black text-gray-900 bg-gray-50 group-hover:bg-white px-2 py-1 rounded-lg transition-colors">
                {{ (campaign.cost || 0).toLocaleString() }} ₽
              </span>
            </td>
            <td class="px-4 py-4 text-right">
              <span class="text-sm font-bold text-gray-600">
                {{ (campaign.conversions || 0).toLocaleString() }}
              </span>
            </td>
            <td class="px-4 py-4 text-right">
              <span class="text-sm font-bold text-gray-500">
                {{ (campaign.cpc || 0).toFixed(2) }}
              </span>
            </td>
            <td class="px-6 py-4 text-right rounded-r-2xl">
              <div class="flex items-center justify-end gap-3">
                <span class="text-sm font-bold text-gray-900">
                  {{ (campaign.cpa || 0).toFixed(2) }} ₽
                </span>
                <button 
                  @click="$emit('select-campaign', campaign)"
                  class="p-2 hover:bg-white rounded-xl text-blue-600 transition-all opacity-0 group-hover:opacity-100 shadow-sm border border-transparent hover:border-blue-100"
                  title="Подробнее по этой кампании"
                >
                  <ArrowTopRightOnSquareIcon class="w-4 h-4" />
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { MagnifyingGlassIcon, ArrowTopRightOnSquareIcon } from '@heroicons/vue/24/outline'

const props = defineProps({
  campaigns: {
    type: Array,
    required: true,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  }
})

defineEmits(['select-campaign'])

const searchQuery = ref('')

const filteredCampaigns = computed(() => {
  if (!searchQuery.value) return props.campaigns
  const query = searchQuery.value.toLowerCase()
  return props.campaigns.filter(c => 
    c.name.toLowerCase().includes(query)
  )
})
</script>
