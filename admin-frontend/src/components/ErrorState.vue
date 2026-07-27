<template>
  <div class="error-state">
    <ExclamationTriangleIcon />
    <div><strong>Не удалось загрузить данные</strong><p>{{ message }}</p></div>
    <button class="button button--secondary" @click="$emit('retry')">Повторить</button>
  </div>
</template>

<script setup>
import { ExclamationTriangleIcon } from '@heroicons/vue/24/outline'
defineProps({ message: { type: String, default: 'Проверьте соединение и попробуйте ещё раз.' } })
defineEmits(['retry'])
</script>
