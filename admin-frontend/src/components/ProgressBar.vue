<template>
  <div class="progress-wrap">
    <div class="progress-meta">
      <span>{{ label }}</span>
      <strong>{{ Math.round(normalized) }}%</strong>
    </div>
    <div class="progress"><span :class="tone" :style="{ width: `${Math.min(normalized, 100)}%` }" /></div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({ value: { type: Number, default: 0 }, label: { type: String, default: '' } })
const normalized = computed(() => Math.max(0, Number(props.value) || 0))
const tone = computed(() => (normalized.value > 85 ? 'danger' : normalized.value >= 70 ? 'warning' : 'success'))
</script>
