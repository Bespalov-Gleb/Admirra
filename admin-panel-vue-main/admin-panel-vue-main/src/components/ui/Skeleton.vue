<template>
  <div 
    :class="[
      'animate-pulse bg-gray-200',
      roundedClass,
      customClass
    ]"
    :style="customStyle"
  ></div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  width: {
    type: String,
    default: '100%'
  },
  height: {
    type: String,
    default: '20px'
  },
  rounded: {
    type: String,
    default: 'md'
  },
  customClass: {
    type: String,
    default: ''
  }
})

const roundedClass = computed(() => {
  const maps = {
    'sm': 'rounded-sm',
    'md': 'rounded-md',
    'lg': 'rounded-lg',
    'xl': 'rounded-xl',
    '2xl': 'rounded-2xl',
    'full': 'rounded-full'
  }
  return maps[props.rounded] || 'rounded-md'
})

const customStyle = computed(() => ({
  width: props.width,
  height: props.height
}))
</script>

<style scoped>
@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: .5;
  }
}
.animate-pulse {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}
</style>
