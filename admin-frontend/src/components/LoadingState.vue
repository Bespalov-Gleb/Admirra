<template>
  <div class="loading-state">
    <div v-for="index in rows" :key="index" class="skeleton-row">
      <i /><i /><i /><i />
    </div>
  </div>
</template>

<script setup>
defineProps({ rows: { type: Number, default: 5 } })
</script>
