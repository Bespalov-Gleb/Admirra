<template>
  <div 
    class="min-w-[250px] rounded-2xl p-5 sm:p-6 shadow-sm transition-all cursor-pointer"
    :class="[
      !isSelected ? 'bg-white hover:shadow-md' : '',
      iconColor === 'blue' && isSelected ? 'bg-blue-50' : '',
      iconColor === 'orange' && isSelected ? 'bg-orange-50' : '',
      iconColor === 'green' && isSelected ? 'bg-green-50' : '',
      iconColor === 'red' && isSelected ? 'bg-red-50' : '',
      iconColor === 'purple' && isSelected ? 'bg-purple-50' : '',
      iconColor === 'pink' && isSelected ? 'bg-pink-50' : ''
    ]"
    @click="$emit('click')"
  >
    <div class="flex items-start gap-4">
      <!-- Иконка слева -->
      <div :class="[
        'w-14 h-14 rounded-2xl flex items-center justify-center flex-shrink-0 shadow-sm',
        iconColor === 'orange' ? 'bg-orange-100' : '',
        iconColor === 'blue' ? 'bg-blue-100' : '',
        iconColor === 'green' ? 'bg-green-100' : '',
        iconColor === 'red' ? 'bg-red-100' : '',
        iconColor === 'purple' ? 'bg-purple-100' : '',
        iconColor === 'pink' ? 'bg-pink-100' : ''
      ]">
        <!-- Если icon - это строка (путь к изображению) -->
        <img 
          v-if="typeof icon === 'string'" 
          :src="icon" 
          :class="[
            'w-6 h-6 sm:w-7 sm:h-7',
            iconColor === 'orange' ? 'icon-orange' : '',
            iconColor === 'blue' ? 'icon-blue' : '',
            iconColor === 'green' ? 'icon-green' : '',
            iconColor === 'red' ? 'icon-red' : '',
            iconColor === 'purple' ? 'icon-purple' : '',
            iconColor === 'pink' ? 'icon-pink' : ''
          ]" 
        />
        <!-- Если icon - это компонент -->
        <component 
          v-else
          :is="icon" 
          :class="[
            'w-6 h-6 sm:w-7 sm:h-7',
            iconColor === 'orange' ? 'text-orange-600' : '',
            iconColor === 'blue' ? 'text-blue-600' : '',
            iconColor === 'green' ? 'text-green-600' : '',
            iconColor === 'red' ? 'text-red-600' : '',
            iconColor === 'purple' ? 'text-purple-600' : '',
            iconColor === 'pink' ? 'text-pink-600' : ''
          ]" 
        />
      </div>
      
      <!-- Контент справа -->
      <div class="flex-1 min-w-0">
        <!-- Заголовок с иконкой информации -->
        <div class="flex items-center gap-1.5 mb-4">
          <h3 class="text-sm font-semibold text-gray-700">{{ title }}</h3>
          <div class="relative group">
            <InformationCircleIcon class="w-4 h-4 text-gray-500 hover:text-gray-700 flex-shrink-0 cursor-help transition-colors" />
            <!-- Tooltip -->
            <div class="absolute left-0 top-full mt-1.5 px-2 py-1.5 bg-gray-800 text-white text-[11px] rounded whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-[9999] shadow-lg">
              {{ tooltipText || 'Дополнительная информация' }}
            </div>
          </div>
        </div>
        
        <!-- Основное значение и абсолютное изменение -->
        <div class="flex items-baseline gap-2 sm:gap-3 flex-wrap">
          <p class="text-lg font-bold text-gray-800 leading-tight">{{ value }}</p>
          <span 
            :class="[
              'text-xs sm:text-sm font-semibold whitespace-nowrap',
              changePositive ? 'text-green-600' : 'text-red-600'
            ]"
          >
            {{ changeText }}
          </span>
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
} from '@heroicons/vue/24/outline'

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
