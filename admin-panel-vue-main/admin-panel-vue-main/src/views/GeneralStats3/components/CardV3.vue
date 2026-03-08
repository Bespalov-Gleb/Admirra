<template>
  <div
    class="rounded-[10px] p-6 sm:p-8 bg-white border shadow-sm transition-all cursor-pointer hover:shadow-md relative font-[Inter] flex flex-col justify-between min-h-[240px]"
    :class="[
      isSelected ? 'ring-2 ring-[#2563EB]/40 border-[#BFDBFE]' : 'border-gray-100 hover:border-gray-200'
    ]"
    @click="$emit('click')"
  >
    <!-- Верхняя строка: иконка + название + кнопка -->
    <div class="flex items-start justify-between gap-2 mb-3">
      <div class="flex items-center gap-3 min-w-0">
        <div class="w-14 h-14 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0">
          <component :is="icon" class="w-7 h-7 text-[#2563EB]" />
        </div>
        <div class="min-w-0">
          <h3 class="text-[20px] font-normal text-[#09183F] leading-snug">{{ title }}</h3>
          <p v-if="subtitle" class="text-[15px] font-normal text-gray-400 leading-snug">{{ subtitle }}</p>
        </div>
      </div>
      <button
        type="button"
        class="w-7 h-7 rounded-full bg-gray-100 flex items-center justify-center text-gray-400 hover:bg-gray-200 hover:text-gray-600 transition-colors flex-shrink-0"
        @click.stop="$emit('click')"
      >
        <ArrowTopRightOnSquareIcon class="w-3.5 h-3.5" />
      </button>
    </div>

    <!-- Главное число и тренд в одну строку -->
    <div class="flex items-baseline gap-2 flex-nowrap min-w-0">
      <p class="text-[32px] font-bold text-[#09183F] leading-none shrink-0">{{ value }}</p>
      <span
        class="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-[6px] text-[9px] font-medium flex-shrink-0"
        :class="changePositive ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-500'"
      >
        <component :is="changePositive ? ArrowTrendingUpIcon : ArrowTrendingDownIcon" class="w-2.5 h-2.5 flex-shrink-0" />
        {{ trendDisplay }}
      </span>
      <span v-if="trendAbsolute" class="text-[9px] font-medium text-gray-500 min-w-0 truncate">{{ trendAbsolute }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ArrowTrendingUpIcon, ArrowTrendingDownIcon } from '@heroicons/vue/20/solid'
import { ArrowTopRightOnSquareIcon } from '@heroicons/vue/24/outline'

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
  }
})

const trendDisplay = computed(() => props.trendDisplay || `${props.trend}%`)

defineEmits(['click'])
</script>
