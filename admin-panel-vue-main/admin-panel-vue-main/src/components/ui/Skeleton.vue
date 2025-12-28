<template>
  <div 
    :class="[
      'animate-pulse bg-gray-200 dark:bg-gray-700',
      variant === 'circle' ? 'rounded-full' : 'rounded-lg',
      customClass
    ]"
    :style="{ width, height }"
  ></div>
</template>

<script setup>
defineProps({
  width: {
    type: String,
    default: '100%'
  },
  height: {
    type: String,
    default: '20px'
  },
  variant: {
    type: String,
    default: 'rect' // 'rect' or 'circle'
  },
  customClass: {
    type: String,
    default: ''
  }
})
</script>
