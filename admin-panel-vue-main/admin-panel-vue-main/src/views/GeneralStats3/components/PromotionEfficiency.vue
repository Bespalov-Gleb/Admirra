<template>
  <div class="bg-white w-full rounded-[40px] px-6 sm:px-10 py-8 shadow-sm border border-gray-50">
    <h3 class="text-xl font-bold text-gray-900 mb-8">Эффективность продвижения</h3>
    
    <!-- KPI Row -->
    <div class="grid grid-cols-3 md:grid-cols-6 gap-4 mb-10">
      <div v-for="item in stats" :key="item.label" class="text-center">
        <p class="text-lg sm:text-2xl font-black text-gray-900 mb-1">{{ item.value }}</p>
        <p class="text-[10px] sm:text-xs font-medium text-gray-400 uppercase tracking-wider">{{ item.label }}</p>
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
            d="M0,50 L200,40 L400,60 L600,70 L800,80 L1000,100 L1000,150 L0,150 Z" 
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

const ctr = computed(() => {
  if (!props.summary.impressions) return 0
  return ((props.summary.clicks / props.summary.impressions) * 100).toFixed(2)
})

const cr = computed(() => {
  if (!props.summary.clicks) return 0
  return ((props.summary.leads / props.summary.clicks) * 100).toFixed(2)
})

const stats = computed(() => [
  { label: 'Показы', value: props.summary.impressions.toLocaleString() },
  { label: 'CTR', value: ctr.value + '%' },
  { label: 'Клики', value: props.summary.clicks.toLocaleString() },
  { label: 'Конверсия, % (CR)', value: cr.value + '%' },
  { label: 'Конверсии', value: props.summary.leads.toLocaleString() },
  { label: 'Цена цели', value: props.summary.cpa.toLocaleString() + ' ₽' }
])

// Mocked points for the design's visualization effect
const chartPoints = [
  { x: 100, y: 50, value: '2329' },
  { x: 300, y: 40, value: '1134' },
  { x: 500, y: 60, value: '94' },
  { x: 700, y: 70, value: '5.32%' },
  { x: 900, y: 90, value: '5' }
]
</script>
