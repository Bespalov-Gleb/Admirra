<template>
  <div class="bg-white w-full rounded-[40px] px-6 sm:px-10 py-8 shadow-sm border border-gray-50">
    <div class="flex items-center justify-between mb-8">
      <h3 class="text-xl font-bold text-gray-900">Эффективность продвижения</h3>
    </div>
    
    <!-- Labels Row -->
    <div class="flex justify-between px-4 sm:px-12 mb-2 text-center">
      <div v-for="label in funnelLabels" :key="label.text" class="flex flex-col items-center flex-1">
        <span class="text-sm font-black text-gray-900">{{ label.value }}</span>
        <span class="text-[10px] font-bold text-gray-400 uppercase tracking-tighter">{{ label.text }}</span>
      </div>
    </div>

    <!-- Funnel Chart Area -->
    <div class="relative h-32 mb-10 px-4 sm:px-12">
      <svg viewBox="0 0 1080 120" preserveAspectRatio="none" class="w-full h-full">
        <defs>
          <filter id="shadow">
            <feDropShadow dx="0" dy="2" stdDeviation="3" flood-opacity="0.1"/>
          </filter>
        </defs>
        
        <!-- Funnel Polygons -->
        <!-- Stage 1 to 2 -->
        <polygon :points="funnelPoints.stage1" fill="#82d944" />
        <!-- Transition 1 (Trapezoid) -->
        <polygon :points="funnelPoints.trans1" fill="#82d944" opacity="0.9" />
        <!-- Stage 2 to 3 -->
        <polygon :points="funnelPoints.stage2" fill="#82d944" />
        <!-- Transition 2 (Trapezoid) -->
        <polygon :points="funnelPoints.trans2" fill="#82d944" opacity="0.9" />
        <!-- Stage 3 (End) -->
        <polygon :points="funnelPoints.stage3" fill="#82d944" />

        <!-- Metric Badges -->
        <!-- 1. Показы -->
        <g transform="translate(100, 60)">
          <rect x="-40" y="-12" width="80" height="24" rx="12" fill="white" filter="url(#shadow)" />
          <text text-anchor="middle" y="5" font-size="10" font-weight="black" fill="#82d944">{{ funnelLabels[0].value }}</text>
        </g>

        <!-- 2. CTR -->
        <g v-if="funnelLabels[1].value" transform="translate(300, 60)">
          <rect x="-35" y="-12" width="70" height="24" rx="12" fill="white" filter="url(#shadow)" />
          <text text-anchor="middle" y="5" font-size="10" font-weight="black" fill="#82d944">{{ funnelLabels[1].value }}</text>
        </g>
        
        <!-- 3. Клики -->
        <g transform="translate(500, 60)">
          <rect x="-40" y="-12" width="80" height="24" rx="12" fill="white" filter="url(#shadow)" />
          <text text-anchor="middle" y="5" font-size="10" font-weight="black" fill="#82d944">{{ funnelLabels[2].value }}</text>
        </g>

        <!-- 4. Конверсии, % (CR) -->
        <g v-if="funnelLabels[3].value" transform="translate(700, 60)">
          <rect x="-35" y="-12" width="70" height="24" rx="12" fill="white" filter="url(#shadow)" />
          <text text-anchor="middle" y="5" font-size="10" font-weight="black" fill="#82d944">{{ funnelLabels[3].value }}</text>
        </g>

        <!-- 5. Конверсии -->
        <g transform="translate(900, 60)">
          <rect x="-40" y="-12" width="80" height="24" rx="12" fill="white" filter="url(#shadow)" />
          <text text-anchor="middle" y="5" font-size="10" font-weight="black" fill="#82d944">{{ funnelLabels[4].value }}</text>
        </g>

        <!-- 6. Цена цели -->
        <g transform="translate(1000, 60)">
          <rect x="-40" y="-12" width="80" height="24" rx="12" fill="white" filter="url(#shadow)" />
          <text text-anchor="middle" y="5" font-size="10" font-weight="black" fill="#82d944">{{ funnelLabels[5].value }}</text>
        </g>
      </svg>
    </div>

    <!-- Stats Table Section -->
    <div class="mt-8">
      <div class="flex justify-center mb-6">
        <button 
          @click="isTableVisible = !isTableVisible"
          class="text-[11px] font-black text-blue-500 uppercase tracking-widest flex items-center gap-2 hover:opacity-80 transition-opacity"
        >
          <svg 
            class="w-3.5 h-3.5 transition-transform duration-300" 
            :class="{ 'rotate-180': !isTableVisible }"
            fill="none" stroke="currentColor" viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M19 9l-7 7-7-7"/>
          </svg>
          {{ isTableVisible ? 'Скрыть таблицу' : 'Подробнее' }}
        </button>
      </div>

      <div v-if="isTableVisible" class="overflow-x-auto transition-all duration-500">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="text-[10px] font-black text-gray-400 uppercase tracking-widest border-b border-gray-100">
              <th class="pb-4 pr-4">Кампании</th>
              <th class="pb-4 px-2 text-right">Показы</th>
              <th class="pb-4 px-2 text-right">Клики</th>
              <th class="pb-4 px-2 text-right">CTR</th>
              <th class="pb-4 px-2 text-right">Ср. стоимость клика</th>
              <th class="pb-4 px-2 text-right">Конверсии</th>
              <th class="pb-4 px-2 text-right">Конверсии (CR)</th>
              <th class="pb-4 px-2 text-right">Цена цели</th>
              <th class="pb-4 px-2 text-right">Расход ↑</th>
              <th class="pb-4 px-2 text-right">Доходы</th>
              <th class="pb-4 px-2 text-right">Прибыль</th>
              <th class="pb-4 px-2 text-right text-nowrap">Рентабельность</th>
            </tr>
          </thead>
          <tbody>
            <!-- Total Row -->
            <tr class="group">
              <td class="py-4 pr-4 font-bold text-sm text-gray-900">Итого</td>
              <td class="py-4 px-2 text-right text-sm font-bold text-gray-700">{{ (summary.impressions || 0).toLocaleString() }}</td>
              <td class="py-4 px-2 text-right text-sm font-bold text-gray-700">{{ (summary.clicks || 0).toLocaleString() }}</td>
              <td class="py-4 px-2 text-right text-sm font-bold text-gray-700">{{ (summary.ctr || 0).toFixed(2) }}%</td>
              <td class="py-4 px-2 text-right text-sm font-bold text-gray-700">{{ (summary.cpc || 0).toFixed(2) }} ₽</td>
              <td class="py-4 px-2 text-right text-sm font-bold text-gray-700">{{ (summary.leads || 0).toLocaleString() }}</td>
              <td class="py-4 px-2 text-right text-sm font-bold text-gray-700">{{ (summary.cr || 0).toFixed(2) }}%</td>
              <td class="py-4 px-2 text-right text-sm font-bold text-gray-700">{{ summary.cpa ? summary.cpa.toFixed(2) + ' ₽' : '—' }}</td>
              <td class="py-4 px-2 text-right text-sm font-black text-gray-900">{{ (summary.expenses || 0).toLocaleString() }} ₽</td>
              <td class="py-4 px-2 text-right text-sm font-bold text-gray-700">{{ (summary.revenue || 0).toLocaleString() }} ₽</td>
              <td class="py-4 px-2 text-right text-sm font-bold text-gray-700" :class="(summary.profit || 0) >= 0 ? 'text-green-600' : 'text-red-500'">
                {{ (summary.profit || 0).toLocaleString() }} ₽
              </td>
              <td class="py-4 px-2 text-right text-sm font-bold text-gray-700">{{ (summary.roi || 0).toFixed(0) }}%</td>
            </tr>
            <!-- Campaign Rows -->
            <tr v-for="cmp in campaigns" :key="cmp.id" class="border-t border-gray-50/50 hover:bg-gray-50/30 transition-colors">
              <td class="py-4 pr-4 text-sm font-bold text-gray-500 truncate max-w-[200px]" :title="cmp.name">
                {{ cmp.name }}
              </td>
              <td class="py-4 px-2 text-right text-sm font-bold text-gray-500">{{ (cmp.impressions || 0).toLocaleString() }}</td>
              <td class="py-4 px-2 text-right text-sm font-bold text-gray-500">{{ (cmp.clicks || 0).toLocaleString() }}</td>
              <td class="py-4 px-2 text-right text-sm font-bold text-gray-500">
                {{ cmp.impressions > 0 ? ((cmp.clicks/cmp.impressions)*100).toFixed(2) : '0.00' }}%
              </td>
              <td class="py-4 px-2 text-right text-sm font-bold text-gray-500">{{ (cmp.cpc || 0).toFixed(2) }} ₽</td>
              <td class="py-4 px-2 text-right text-sm font-bold text-gray-500">{{ (cmp.conversions || 0).toLocaleString() }}</td>
              <td class="py-4 px-2 text-right text-sm font-bold text-gray-500">
                {{ cmp.clicks > 0 ? ((cmp.conversions/cmp.clicks)*100).toFixed(2) : '0.00' }}%
              </td>
              <td class="py-4 px-2 text-right text-sm font-bold text-gray-500">
                {{ cmp.cpa ? cmp.cpa.toFixed(2) + ' ₽' : '—' }}
              </td>
              <td class="py-4 px-2 text-right text-sm font-bold text-gray-500">{{ (cmp.cost || 0).toLocaleString() }} ₽</td>
              <td class="py-4 px-2 text-right text-sm font-bold text-gray-500">0 ₽</td>
              <td class="py-4 px-2 text-right text-sm font-bold text-red-400">-{{ (cmp.cost || 0).toLocaleString() }} ₽</td>
              <td class="py-4 px-2 text-right text-sm font-bold text-red-400">-100%</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  summary: {
    type: Object,
    required: true
  },
  campaigns: {
    type: Array,
    default: () => []
  }
})

const isTableVisible = ref(true)

const funnelLabels = computed(() => [
  { text: 'Показы', value: (props.summary.impressions || 0).toLocaleString() },
  { text: 'CTR', value: (props.summary.ctr || 0).toFixed(2) + '%' },
  { text: 'Клики', value: (props.summary.clicks || 0).toLocaleString() },
  { text: 'Конверсии, % (CR)', value: (props.summary.cr || 0).toFixed(2) + '%' },
  { text: 'Конверсии', value: (props.summary.leads || 0).toLocaleString() },
  { text: 'Цена цели', value: props.summary.cpa ? props.summary.cpa.toFixed(2) + ' ₽' : '0,00 ₽' }
])

const funnelPoints = computed(() => {
  const h1 = 100 // Height of first stage (highest)
  const h2 = Math.max(80, h1 * 0.8) // Height of second stage
  const h3 = 10 // Height of end line (conversions)
  
  const yCenter = 60
  
  return {
    // Rect for Stage 1 (Impressions)
    stage1: `0,${yCenter - h1/2} 200,${yCenter - h1/2} 200,${yCenter + h1/2} 0,${yCenter + h1/2}`,
    // Trapezoid Transition 1
    trans1: `200,${yCenter - h1/2} 400,${yCenter - h2/2} 400,${yCenter + h2/2} 200,${yCenter + h1/2}`,
    // Rect for Stage 2 (Clicks)
    stage2: `400,${yCenter - h2/2} 600,${yCenter - h2/2} 600,${yCenter + h2/2} 400,${yCenter + h2/2}`,
    // Trapezoid Transition 2
    trans2: `600,${yCenter - h2/2} 800,${yCenter - h3/2} 800,${yCenter + h3/2} 600,${yCenter + h2/2}`,
    // Rect for Stage 3 (Conversions)
    stage3: `800,${yCenter - h3/2} 1000,${yCenter - h3/2} 1000,${yCenter + h3/2} 800,${yCenter + h3/2}`
  }
})
</script>

<style scoped>
.text-nowrap {
  white-space: nowrap;
}
</style>
