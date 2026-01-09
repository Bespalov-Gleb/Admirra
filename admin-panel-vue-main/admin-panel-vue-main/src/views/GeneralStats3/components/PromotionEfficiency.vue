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
  { label: 'Показы', value: (props.summary.impressions || 0).toLocaleString(), trend: props.summary.trends?.impressions },
  { label: 'CTR', value: ctr.value.toFixed(2) + '%', trend: props.summary.trends?.ctr },
  { label: 'Клики', value: (props.summary.clicks || 0).toLocaleString(), trend: props.summary.trends?.clicks },
  { label: 'Конверсия, % (CR)', value: cr.value.toFixed(2) + '%', trend: props.summary.trends?.cr },
  { label: 'Конверсии', value: (props.summary.leads || 0).toLocaleString(), trend: props.summary.trends?.leads },
  { label: 'Цена цели', value: (props.summary.cpa || 0).toLocaleString() + ' ₽', trend: props.summary.trends?.cpa }
])

// Dynamic points for the funnel visualization
const chartPoints = computed(() => {
  // Baseline max value for scaling. We take the max of absolute values to determine peak.
  const vals = [
    props.summary.impressions || 0,
    props.summary.clicks || 0,
    props.summary.leads || 0,
    (props.summary.cpa || 0) / 10 // CPA is usually larger, scale it down for visual balance
  ]
  const maxVal = Math.max(...vals, 1) // Avoid division by zero
  
  // Formulas for dynamic Y coordinates (between 30 and 130)
  const getY = (val) => {
    if (!val) return 130 // Bottom line for zero values
    // Logarithmic-like scaling to show difference even between small and large non-zero numbers
    const ratio = Math.min(Math.log10(val + 1) / Math.log10(maxVal + 1), 1)
    return 130 - (ratio * 100) // Height range is 100 units
  }

  // Percentage scaling (CTR/CR)
  const getYRate = (val) => {
    if (!val) return 130
    const ratio = Math.min(val / 10, 1) // 10% is considered high for this visual
    return 130 - (ratio * 90)
  }

  return [
    { x: 100, y: getY(props.summary.impressions), value: (props.summary.impressions || 0).toLocaleString() },
    { x: 300, y: getYRate(ctr.value), value: ctr.value.toFixed(2) + '%' },
    { x: 500, y: getY(props.summary.clicks), value: (props.summary.clicks || 0).toLocaleString() },
    { x: 700, y: getYRate(cr.value), value: cr.value.toFixed(2) + '%' },
    { x: 900, y: getY(props.summary.leads), value: (props.summary.leads || 0).toLocaleString() }
  ]
})

// Dynamic Funnel Path using Cubic Bezier for smooth curves based on points
const funnelPath = computed(() => {
  const p = chartPoints.value
  const baseline = 150
  
  // We construct a path that passes smoothly through each of our 5 points
  return `M0,${p[0].y + 20} 
          C100,${p[0].y + 20} 50,${p[0].y} ${p[0].x},${p[0].y} 
          C${(p[0].x + p[1].x) / 2},${p[0].y} ${(p[0].x + p[1].x) / 2},${p[1].y} ${p[1].x},${p[1].y} 
          C${(p[1].x + p[2].x) / 2},${p[1].y} ${(p[1].x + p[2].x) / 2},${p[2].y} ${p[2].x},${p[2].y} 
          C${(p[2].x + p[3].x) / 2},${p[2].y} ${(p[2].x + p[3].x) / 2},${p[3].y} ${p[3].x},${p[3].y} 
          C${(p[3].x + p[4].x) / 2},${p[3].y} ${(p[3].x + p[4].x) / 2},${p[4].y} ${p[4].x},${p[4].y} 
          C950,${p[4].y} 1000,${p[4].y + 10} 1000,${p[4].y + 20} 
          L1000,${baseline} L0,${baseline} Z`
})
</script>
