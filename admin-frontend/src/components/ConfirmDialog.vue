<template>
  <AppModal :open="open" :title="title" eyebrow="Подтверждение" @close="$emit('close')">
    <p class="muted modal-copy">{{ description }}</p>
    <label v-if="requireReason" class="field">
      <span>Причина</span>
      <textarea v-model="reason" rows="4" placeholder="Укажите причину действия" />
    </label>
    <template #footer>
      <button class="button button--secondary" @click="$emit('close')">Отмена</button>
      <button class="button" :class="danger ? 'button--danger' : 'button--primary'" :disabled="loading || (requireReason && !reason.trim())" @click="$emit('confirm', reason.trim())">
        {{ loading ? 'Выполняем…' : confirmLabel }}
      </button>
    </template>
  </AppModal>
</template>

<script setup>
import { ref, watch } from 'vue'
import AppModal from './AppModal.vue'
const props = defineProps({ open: Boolean, title: String, description: String, confirmLabel: { type: String, default: 'Подтвердить' }, requireReason: Boolean, danger: Boolean, loading: Boolean })
defineEmits(['close', 'confirm'])
const reason = ref('')
watch(() => props.open, (value) => { if (value) reason.value = '' })
</script>
