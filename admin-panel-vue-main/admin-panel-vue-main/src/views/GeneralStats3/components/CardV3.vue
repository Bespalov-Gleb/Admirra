<template>
  <div
    class="rounded-2xl p-8 bg-white border border-gray-100 shadow-md transition-all cursor-pointer hover:border-blue-200 hover:shadow-lg"
    :class="[
      isSelected && 'ring-2 ring-blue-500/30 border-blue-200'
    ]"
    @click="$emit('click')"
  >
    <div class="flex items-start gap-5">
      <div class="w-14 h-14 rounded-xl bg-blue-100 flex items-center justify-center flex-shrink-0">
        <component :is="icon" class="w-7 h-7 text-blue-600" />
      </div>
      <div class="flex-1 min-w-0">
        <h3 class="text-base font-medium text-gray-500 mb-1.5">{{ title }}</h3>
        <p v-if="subtitle" class="text-sm text-gray-400 mb-2">{{ subtitle }}</p>
        <p class="text-2xl font-bold text-gray-900 leading-tight">{{ value }}</p>
        <div
          :class="[
            'inline-flex flex-wrap items-center gap-1.5 mt-2 px-2.5 py-1 rounded-lg text-xs font-semibold',
            changePositive ? 'bg-green-50 text-green-600' : 'bg-red-50 text-red-600'
          ]"
        >
          <component :is="changePositive ? ArrowTrendingUpIcon : ArrowTrendingDownIcon" class="w-4 h-4 flex-shrink-0" />
          <span>{{ trendDisplay }}</span>
          <span v-if="trendAbsolute" class="font-normal opacity-90">{{ trendAbsolute }}</span>
        </div>
      </div>
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
    default: 'orange' // orange, blue, green, red, purple, pink
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

<style scoped>
/* Фильтры для изменения цвета SVG иконок */
.icon-orange {
  filter: brightness(0) saturate(100%) invert(67%) sepia(93%) saturate(1352%) hue-rotate(346deg) brightness(101%) contrast(101%);
}

.icon-blue {
  filter: brightness(0) saturate(100%) invert(40%) sepia(99%) saturate(2476%) hue-rotate(212deg) brightness(102%) contrast(101%);
}

.icon-green {
  filter: brightness(0) saturate(100%) invert(65%) sepia(94%) saturate(1352%) hue-rotate(87deg) brightness(101%) contrast(101%);
}

.icon-red {
  filter: brightness(0) saturate(100%) invert(27%) sepia(95%) saturate(1352%) hue-rotate(346deg) brightness(101%) contrast(101%);
}

.icon-purple {
  filter: brightness(0) saturate(100%) invert(48%) sepia(93%) saturate(1352%) hue-rotate(250deg) brightness(101%) contrast(101%);
}

.icon-pink {
  filter: brightness(0) saturate(100%) invert(60%) sepia(93%) saturate(1352%) hue-rotate(300deg) brightness(101%) contrast(101%);
}
</style>
