<template>
  <div class="empty-state">
    <div class="empty-state__icon"><InboxIcon /></div>
    <h3>{{ title }}</h3>
    <p>{{ description }}</p>
    <slot />
  </div>
</template>

<script setup>
import { InboxIcon } from '@heroicons/vue/24/outline'
defineProps({ title: { type: String, default: 'Здесь пока пусто' }, description: { type: String, default: 'Данные появятся после первых событий.' } })
</script>
