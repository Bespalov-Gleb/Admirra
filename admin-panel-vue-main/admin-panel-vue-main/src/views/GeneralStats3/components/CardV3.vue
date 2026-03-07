<template>
  <div
    class="rounded-[10px] p-5 sm:p-6 bg-white border shadow-sm transition-all cursor-pointer hover:shadow-md relative font-[Inter]"
    :class="[
      isSelected ? 'ring-2 ring-[#2563EB]/40 border-[#BFDBFE]' : 'border-gray-100 hover:border-gray-200'
    ]"
    @click="$emit('click')"
  >
    <!-- Кнопка стрелки в правом верхнем углу -->
    <button
      type="button"
      class="absolute top-3 right-3 w-7 h-7 rounded-full bg-gray-100 flex items-center justify-center text-gray-400 hover:bg-gray-200 hover:text-gray-600 transition-colors"
      @click.stop="$emit('click')"
    >
      <ArrowTopRightOnSquareIcon class="w-3.5 h-3.5" />
    </button>

    <!-- Заголовок: иконка + название + подзаголовок -->
    <div class="flex items-center gap-3 pr-8 mb-4">
      <div class="w-10 h-10 rounded-full bg-[#EFF6FF] flex items-center justify-center flex-shrink-0">
        <component :is="icon" class="w-5 h-5 text-[#2563EB]" />
      </div>
      <div class="min-w-0">
        <h3 class="text-[15px] font-normal text-[#09183F] leading-tight">{{ title }}</h3>
        <p v-if="subtitle" class="text-[12px] font-normal text-gray-400 leading-tight">{{ subtitle }}</p>
      </div>
    </div>

    <!-- Главное значение -->
    <p class="text-[40px] font-normal text-[#09183F] leading-none mb-4">{{ value }}</p>

    <!-- Тренд: бейдж + абсолютное изменение -->
    <div class="flex items-center gap-2 flex-wrap">
      <span
        class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[13px] font-normal text-white"
        :class="changePositive ? 'bg-[#82d944]' : 'bg-red-500'"
      >
        <component :is="changePositive ? ArrowTrendingUpIcon : ArrowTrendingDownIcon" class="w-3.5 h-3.5 flex-shrink-0" />
        {{ trendDisplay }}
      </span>
      <span v-if="trendAbsolute" class="text-[13px] font-normal text-gray-500">{{ trendAbsolute }}</span>
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
