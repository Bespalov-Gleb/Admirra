<template>
  <div class="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
    <div class="px-6 py-4 border-b border-gray-100 flex items-center justify-between bg-gray-50/50">
      <h3 class="font-bold text-gray-900">Детальная статистика по кампаниям</h3>
      <div class="flex items-center gap-2">
        <input 
          v-model="searchQuery" 
          type="text" 
          placeholder="Поиск кампании..." 
          class="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>
    </div>
    
    <div class="overflow-x-auto">
      <table class="w-full text-left border-collapse">
        <thead>
          <tr class="bg-gray-50 text-[11px] font-bold text-gray-500 uppercase tracking-wider">
            <th class="px-6 py-3 border-b border-gray-100">Название кампании</th>
            <th class="px-4 py-3 border-b border-gray-100 text-right">Показы</th>
            <th class="px-4 py-3 border-b border-gray-100 text-right">Клики</th>
            <th class="px-4 py-3 border-b border-gray-100 text-right">Расходы (Р)</th>
            <th class="px-4 py-3 border-b border-gray-100 text-right">Лиды</th>
            <th class="px-4 py-3 border-b border-gray-100 text-right">CPC</th>
            <th class="px-6 py-3 border-b border-gray-100 text-right">CPA</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-50">
          <tr v-if="loading" v-for="i in 3" :key="i" class="animate-pulse">
            <td class="px-6 py-4"><div class="h-4 bg-gray-200 rounded w-3/4"></div></td>
            <td class="px-4 py-4"><div class="h-4 bg-gray-200 rounded w-1/2 ml-auto"></div></td>
            <td class="px-4 py-4"><div class="h-4 bg-gray-200 rounded w-1/2 ml-auto"></div></td>
            <td class="px-4 py-4"><div class="h-4 bg-gray-200 rounded w-1/2 ml-auto"></div></td>
            <td class="px-4 py-4"><div class="h-4 bg-gray-200 rounded w-1/2 ml-auto"></div></td>
            <td class="px-4 py-4"><div class="h-4 bg-gray-200 rounded w-1/2 ml-auto"></div></td>
            <td class="px-6 py-4"><div class="h-4 bg-gray-200 rounded w-1/2 ml-auto"></div></td>
          </tr>
          
          <tr v-else-if="filteredCampaigns.length === 0">
            <td colspan="7" class="px-6 py-10 text-center text-gray-500">
              Данные не найдены
            </td>
          </tr>

          <tr 
            v-for="campaign in filteredCampaigns" 
            :key="campaign.name" 
            class="hover:bg-gray-50/80 transition-colors"
          >
            <td class="px-6 py-4 text-sm font-medium text-gray-900 max-w-xs truncate" :title="campaign.name">
              {{ campaign.name }}
            </td>
            <td class="px-4 py-4 text-sm text-gray-600 text-right">
              {{ campaign.impressions.toLocaleString() }}
            </td>
            <td class="px-4 py-4 text-sm text-gray-600 text-right">
              {{ campaign.clicks.toLocaleString() }}
            </td>
            <td class="px-4 py-4 text-sm font-semibold text-gray-900 text-right">
              {{ campaign.cost.toLocaleString() }}
            </td>
            <td class="px-4 py-4 text-sm text-gray-600 text-right">
              {{ campaign.conversions.toLocaleString() }}
            </td>
            <td class="px-4 py-4 text-sm text-gray-600 text-right">
              {{ campaign.cpc.toFixed(2) }}
            </td>
            <td class="px-6 py-4 text-sm text-gray-600 text-right">
              {{ campaign.cpa.toFixed(2) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

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

const searchQuery = ref('')

const filteredCampaigns = computed(() => {
  if (!searchQuery.value) return props.campaigns
  const query = searchQuery.value.toLowerCase()
  return props.campaigns.filter(c => 
    c.name.toLowerCase().includes(query)
  )
})
</script>
