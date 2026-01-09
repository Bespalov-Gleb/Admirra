<template>
  <div class="bg-white w-full rounded-[40px] px-6 sm:px-10 py-8 shadow-sm border border-gray-50">
    <h3 class="text-xl font-bold text-gray-900 mb-8">Эффективность продвижения</h3>
    
    <!-- KPI Row -->
    <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-10">
      <div v-for="item in stats" :key="item.label" class="text-center p-4 bg-gray-50/50 rounded-2xl border border-gray-100/50">
        <p class="text-lg sm:text-2xl font-black text-gray-900 mb-1 leading-none">{{ item.value }}</p>
        <p class="text-[10px] sm:text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-2">{{ item.label }}</p>
        
        <!-- Trend indicator -->
        <div v-if="item.trend !== undefined" class="flex items-center justify-center gap-1">
          <span 
            :class="[
              'text-[10px] font-black px-2 py-0.5 rounded-full',
              item.trend >= 0 ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'
            ]"
          >
            {{ item.trend > 0 ? '+' : '' }}{{ item.trend }}%
          </span>
        </div>
      </div>
    </div>

    <!-- Funnel Chart Area -->
    <div class="relative h-48 mb-8">
      <div class="absolute inset-0 flex items-end justify-between px-4 sm:px-12">
        <!-- We'll use a simple SVG or a specialized chart for this "funnel" area -->
        <svg viewBox="0 0 1000 150" preserveAspectRatio="none" class="w-full h-full">
          <defs>
            <linearGradient id="funnelGradient" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" style="stop-color:#22c55e;stop-opacity:0.8" />
              <stop offset="100%" style="stop-color:#3b82f6;stop-opacity:1" />
            </linearGradient>
          </defs>
          <path 
            :d="funnelPath" 
            fill="url(#funnelGradient)"
          />
          <!-- Data points with values -->
          <g v-for="(point, index) in chartPoints" :key="index">
            <circle :cx="point.x" :cy="point.y" r="5" fill="#3b82f6" stroke="white" stroke-width="2" />
            <rect :x="point.x - 20" :y="point.y - 30" width="40" height="20" rx="10" fill="#3b82f6" />
            <text :x="point.x" :y="point.y - 17" text-anchor="middle" fill="white" font-size="10" font-weight="bold">{{ point.value }}</text>
          </g>
        </svg>
      </div>
    </div>

    <!-- Formulas -->
    <div class="flex flex-col sm:flex-row items-center justify-center gap-6 sm:gap-20 pt-6 border-t border-gray-100">
      <div class="flex items-center gap-3">
        <span class="text-sm font-bold text-gray-900">CTR = (Переходы/Показы) * 100%</span>
      </div>
      <div class="flex items-center gap-3">
        <span class="text-sm font-bold text-gray-900">Конверсия = (Лиды/Переходы) * 100%</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  summary: {
    type: Object,
    required: true
  }
})

const ctr = computed(() => props.summary.ctr || 0)
const cr = computed(() => props.summary.cr || 0)

const stats = computed(() => [
  { label: 'Показы', value: props.summary.impressions.toLocaleString(), trend: props.summary.trends?.impressions },
  { label: 'CTR', value: ctr.value.toFixed(2) + '%', trend: props.summary.trends?.ctr },
  { label: 'Клики', value: props.summary.clicks.toLocaleString(), trend: props.summary.trends?.clicks },
  { label: 'Конверсия, % (CR)', value: cr.value.toFixed(2) + '%', trend: props.summary.trends?.cr },
  { label: 'Конверсии', value: props.summary.leads.toLocaleString(), trend: props.summary.trends?.leads },
  { label: 'Цена цели', value: props.summary.cpa.toLocaleString() + ' ₽', trend: props.summary.trends?.cpa }
])

// Dynamic points for the funnel visualization
const chartPoints = computed(() => {
  return [
    { x: 100, y: 55, value: props.summary.impressions.toLocaleString() },
    { x: 300, y: 45, value: props.summary.clicks.toLocaleString() },
    { x: 500, y: 55, value: (props.summary.leads || 0).toLocaleString() },
    { x: 700, y: 75, value: ctr.value.toFixed(2) + '%' },
    { x: 900, y: 95, value: props.summary.cpa.toLocaleString() }
  ]
})

// Dynamic Funnel Path using Cubic Bezier for smooth curves
const funnelPath = computed(() => {
  // We'll create a smooth "mountain/wave" path that feels premium
  // Points (x, y): (0, 60), (200, 40), (400, 50), (600, 70), (800, 90), (1000, 110)
  return `M0,60 
          C100,60 100,40 200,40 
          C300,40 300,50 400,50 
          C500,50 500,70 600,70 
          C700,70 700,90 800,90 
          C900,90 900,110 1000,110 
          L1000,150 L0,150 Z`
})
</script>
