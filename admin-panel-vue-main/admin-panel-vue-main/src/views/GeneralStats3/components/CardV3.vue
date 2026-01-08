<template>
  <div 
    class="min-w-[240px] rounded-3xl p-4 sm:p-5 shadow-sm border border-gray-100 transition-all cursor-pointer"
    :class="[
      !isSelected ? 'bg-white hover:border-blue-200 hover:shadow-md' : '',
      iconColor === 'blue' && isSelected ? 'bg-blue-50 border-blue-200' : '',
      iconColor === 'orange' && isSelected ? 'bg-orange-50 border-orange-200' : '',
      iconColor === 'green' && isSelected ? 'bg-green-50 border-green-200' : '',
      iconColor === 'red' && isSelected ? 'bg-red-50 border-red-200' : '',
      iconColor === 'purple' && isSelected ? 'bg-purple-50 border-purple-200' : '',
      iconColor === 'pink' && isSelected ? 'bg-pink-50 border-pink-200' : ''
    ]"
    @click="$emit('click')"
  >
    <div class="flex items-center gap-3">
      <!-- Иконка слева -->
      <div :class="[
        'w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0',
        iconColor === 'orange' ? 'bg-orange-50' : '',
        iconColor === 'blue' ? 'bg-blue-50' : '',
        iconColor === 'green' ? 'bg-green-50' : '',
        iconColor === 'red' ? 'bg-red-50' : '',
        iconColor === 'purple' ? 'bg-purple-50' : '',
        iconColor === 'pink' ? 'bg-pink-50' : ''
      ]">
        <component 
          :is="icon" 
          :class="[
            'w-6 h-6',
            iconColor === 'orange' ? 'text-orange-500' : '',
            iconColor === 'blue' ? 'text-blue-500' : '',
            iconColor === 'green' ? 'text-green-500' : '',
            iconColor === 'red' ? 'text-red-500' : '',
            iconColor === 'purple' ? 'text-purple-500' : '',
            iconColor === 'pink' ? 'text-pink-500' : ''
          ]" 
        />
      </div>
      
      <!-- Контент справа -->
      <div class="flex-1 min-w-0">
        <!-- Заголовок -->
        <div class="flex items-center gap-1 mb-1">
          <h3 class="text-xs sm:text-sm font-medium text-gray-500 truncate">{{ title }}</h3>
          <InformationCircleIcon class="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
        </div>
        
        <!-- Значение и тренд -->
        <div class="flex items-center justify-between gap-2">
          <p class="text-lg sm:text-xl font-bold text-gray-900">{{ value }}</p>
          
          <!-- Тренд badge -->
          <div 
            :class="[
              'flex items-center gap-0.5 px-2 py-0.5 rounded-full text-[10px] sm:text-xs font-bold leading-none',
              changePositive ? 'bg-green-50 text-green-600' : 'bg-red-50 text-red-600'
            ]"
          >
            <component 
              :is="changePositive ? ArrowTrendingUpIcon : ArrowTrendingDownIcon" 
              class="w-3 h-3"
            />
            <span>{{ trend }}%</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { 
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  InformationCircleIcon
} from '@heroicons/vue/20/solid'

defineProps({
  title: {
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
