<template>
  <div class="toast-stack" aria-live="polite">
    <TransitionGroup name="toast">
      <button
        v-for="toast in toasts"
        :key="toast.id"
        class="toast"
        :class="`toast--${toast.type}`"
        @click="remove(toast.id)"
      >
        <CheckCircleIcon v-if="toast.type === 'success'" />
        <ExclamationCircleIcon v-else-if="toast.type === 'error'" />
        <InformationCircleIcon v-else />
        <span>{{ toast.message }}</span>
      </button>
    </TransitionGroup>
  </div>
</template>

<script setup>
import { CheckCircleIcon, ExclamationCircleIcon, InformationCircleIcon } from '@heroicons/vue/24/outline'
import { useToast } from '../composables/useToast'
const { toasts, remove } = useToast()
</script>
