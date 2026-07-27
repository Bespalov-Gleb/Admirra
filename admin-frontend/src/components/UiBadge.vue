<template>
  <span class="badge" :class="`badge--${tone}`"><span v-if="dot" class="badge__dot" />{{ label }}</span>
</template>

<script setup>
defineProps({ label: { type: [String, Number], default: '' }, tone: { type: String, default: 'neutral' }, dot: Boolean })
</script>
