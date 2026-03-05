<template>
  <div
    v-if="isActive"
    class="absolute left-0 top-0 bottom-0 w-1 rounded-r z-10 bg-[#3b82f6]"
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
