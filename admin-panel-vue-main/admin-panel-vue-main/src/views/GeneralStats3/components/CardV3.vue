<template>
  <div
    class="rounded-[0.6944rem] p-6 sm:p-8 border shadow-sm transition-all cursor-pointer hover:shadow-md relative font-[Inter] flex flex-col justify-between min-h-[16.6667rem] bg-white dark:bg-[#2A2D3C] dark:border-white/10"
    :class="[
      isSelected ? 'border-l-4' : 'border-gray-100 dark:border-white/10 hover:border-gray-200 dark:hover:border-white/20'
    ]"
    :style="isSelected && chartColor ? {
      borderLeftColor: chartColor,
      borderLeftWidth: '0.2778rem',
      backgroundColor: hexToRgba(chartColor, 0.04)
    } : {}"
    @click="$emit('click')"
  >
    <!-- Верхняя строка: иконка + название -->
    <div class="flex items-start gap-3 mb-3">
      <div class="w-14 h-14 rounded-full bg-gray-100 dark:bg-white/10 flex items-center justify-center flex-shrink-0">
        <component :is="icon" class="w-7 h-7 text-[#2563EB] dark:text-[#4A7AFF]" />
      </div>
      <div class="min-w-0">
        <h3 class="text-[1.3889rem] font-normal text-[#09183F] dark:text-white leading-snug">{{ title }}</h3>
        <p v-if="subtitle" class="text-[1.0417rem] font-normal text-gray-400 dark:text-gray-500 leading-snug">{{ subtitle }}</p>
      </div>
    </div>

    <!-- Главное число и тренд в одну строку -->
    <div class="flex items-baseline gap-2 flex-nowrap min-w-0">
      <p class="text-[2.2222rem] font-bold text-[#09183F] dark:text-white leading-none shrink-0">{{ value }}</p>
      <span
        class="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-[0.4167rem] text-[0.625rem] font-medium flex-shrink-0"
        :class="changePositive ? 'bg-green-100 dark:bg-green-500/20 text-green-600 dark:text-[#66BB6A]' : 'bg-red-100 dark:bg-red-500/20 text-red-500 dark:text-[#EF5350]'"
      >
        <component :is="changePositive ? ArrowTrendingUpIcon : ArrowTrendingDownIcon" class="w-2.5 h-2.5 flex-shrink-0" />
        {{ trendDisplay }}
      </span>
      <span v-if="trendAbsolute" class="text-[0.625rem] font-medium text-gray-500 dark:text-gray-400 min-w-0 truncate">{{ trendAbsolute }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ArrowTrendingUpIcon, ArrowTrendingDownIcon } from '@heroicons/vue/20/solid'

const props = defineProps({
  title: {
    type: String,
    required: true
  },
  subtitle: {
    type: String,
    default: ''
  },
  value: {
    type: String,
    required: true
  },
  trend: {
    type: Number,
    required: true
  },
  trendDisplay: {
    type: String,
    default: ''
  },
  trendAbsolute: {
    type: String,
    default: ''
  },
  changeText: {
    type: String,
    default: ''
  },
  icon: {
    type: [Object, Function, String],
    required: true
  },
  changePositive: {
    type: Boolean,
    default: false
  },
  iconColor: {
    type: String,
    default: 'blue'
  },
  tooltipText: {
    type: String,
    default: ''
  },
  isSelected: {
    type: Boolean,
    default: false
  },
  chartColor: {
    type: String,
    default: null
  }
})

const trendDisplay = computed(() => props.trendDisplay || `${props.trend}%`)

function hexToRgba(hex, alpha) {
  const m = hex.match(/^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i)
  if (!m) return 'rgba(0,0,0,0.04)'
  const r = parseInt(m[1], 16)
  const g = parseInt(m[2], 16)
  const b = parseInt(m[3], 16)
  return `rgba(${r},${g},${b},${alpha})`
}

defineEmits(['click'])
</script>
