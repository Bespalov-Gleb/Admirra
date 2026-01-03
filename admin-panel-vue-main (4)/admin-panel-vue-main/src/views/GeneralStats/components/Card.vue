<template>
  <div
    :class="[
      'rounded-[40px] p-10 cursor-pointer transition-all ',
      isDark ? 'main-bg-color' : '!bg-white shadow-sm'
    ]"
  >
    <div class="flex items-start justify-between mb-4">
      <div
        :class="[
          'w-12 h-12 rounded-2xl flex items-center justify-center flex-shrink-0',
          isDark ? 'bg-slate-500 ' : 'bg-gray-100'
        ]"
      >
        <component :is="icon" :class="['w-6 h-6', isDark ? 'text-white ' : 'text-gray-600']" />
      </div>
      <div>
      <p :class="['text-3xl font-bold mb-3', isDark ? 'text-white' : 'text-gray-900']">
        {{ value }}
      </p>
      <div class="flex items-center gap-1.5">
        <component 
          :is="trend > 0 ? ArrowTrendingUpIcon : ArrowTrendingDownIcon" 
          :class="[
            'w-4 h-4',
            trend > 0 
              ? (isDark ? 'text-green-400' : 'text-green-600') 
              : (isDark ? 'text-red-400' : 'text-red-600')
          ]" 
        />
        <span
          :class="[
            'text-sm font-semibold',
            trend > 0 
              ? (isDark ? 'text-green-400' : 'text-green-600') 
              : (isDark ? 'text-red-400' : 'text-red-600')
          ]"
        >
          {{ trend > 0 ? '+' : '' }}{{ trend }}%
        </span>
        <span :class="['text-xs', isDark ? 'text-gray-400' : 'text-gray-500']">
          {{ changeText }}
        </span>
      </div>
    </div>
    </div>
    <div class="">
      <h3 :class="['text-sm font-medium mb-0.5', isDark ? 'text-gray-200 ' : 'text-gray-700']">
        {{ title }}
      </h3>
      <p :class="['text-xs', isDark ? 'text-gray-400' : 'text-gray-500']">
        {{ subtitle }}
      </p>
    </div>
    
  </div>
</template>

<script setup>
import { 
  ChevronRightIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon
} from '@heroicons/vue/24/outline'

defineProps({
  title: {
    type: String,
    required: true
  },
  subtitle: {
    type: String,
    required: true
  },
  value: {
    type: String,
    required: true
  },
  trend: {
    type: Number,
    required: true
  },
  changeText: {
    type: String,
    required: true
  },
  icon: {
    type: [Object, Function],
    required: true
  },
  isDark: {
    type: Boolean,
    default: false
  }
})
</script>

