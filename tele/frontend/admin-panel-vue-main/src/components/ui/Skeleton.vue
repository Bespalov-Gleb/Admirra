<template>
  <div 
    class="bg-gray-100 animate-pulse rounded-xl"
    :class="[widthClass, heightClass, roundedClass]"
  ></div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  width: { type: String, default: 'full' },
  height: { type: String, default: '4' },
  rounded: { type: String, default: 'xl' }
})

const widthClass = computed(() => `w-${props.width}`)
const heightClass = computed(() => `h-${props.height}`)
const roundedClass = computed(() => `rounded-${props.rounded}`)
</script>
