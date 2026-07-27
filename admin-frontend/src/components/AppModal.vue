<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="open" class="modal-backdrop" @mousedown.self="$emit('close')">
        <section class="modal-card" :class="{ 'modal-card--wide': wide }" role="dialog" aria-modal="true">
          <header>
            <div><span v-if="eyebrow" class="eyebrow">{{ eyebrow }}</span><h2>{{ title }}</h2></div>
            <button class="icon-button" aria-label="Закрыть" @click="$emit('close')"><XMarkIcon /></button>
          </header>
          <div class="modal-body"><slot /></div>
          <footer v-if="$slots.footer"><slot name="footer" /></footer>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { XMarkIcon } from '@heroicons/vue/24/outline'
defineProps({ open: Boolean, title: { type: String, default: '' }, eyebrow: String, wide: Boolean })
defineEmits(['close'])
</script>
