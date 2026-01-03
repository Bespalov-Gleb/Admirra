<template>
  <div
    v-if="isActive"
    class="absolute right-0 -top-1 h-[calc(100%+8px)] w-1.5 rounded-l-md z-10 bg-active-menu"
  ></div>
</template>

<script setup>
defineProps({
  isActive: {
    type: Boolean,
    required: true
  }
})
</script>

