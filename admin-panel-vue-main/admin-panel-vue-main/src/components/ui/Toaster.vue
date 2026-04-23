<template>
  <div class="fixed top-6 right-6 z-[9999] flex flex-col gap-3 pointer-events-none max-w-sm w-full">
    <TransitionGroup name="toast">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        class="pointer-events-auto flex items-start gap-4 p-4 rounded-2xl border backdrop-blur-md shadow-2xl transition-all duration-300 group"
        :class="containerClasses(toast.type)"
      >
        <!-- Icon -->
        <div class="flex-shrink-0 w-6 h-6 rounded-lg flex items-center justify-center shadow-sm" :class="iconClasses(toast.type)">
          <svg v-if="toast.type === 'success'" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7" />
          </svg>
          <svg v-else-if="toast.type === 'error'" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12" />
          </svg>
          <svg v-else-if="toast.type === 'warning'" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>

        <!-- Content -->
        <div class="flex-1 pt-0.5">
          <p class="text-[13px] font-black uppercase tracking-tight leading-snug" :class="textClasses(toast.type)">
            {{ toast.message }}
          </p>
        </div>

        <!-- Close -->
        <button
          @click="removeToast(toast.id)"
          class="flex-shrink-0 p-1 rounded-full opacity-0 group-hover:opacity-100 transition-opacity hover:bg-black/5"
        >
          <svg class="w-3.5 h-3.5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup>
import { useToaster } from '../../composables/useToaster'

const { toasts, removeToast } = useToaster()

const containerClasses = (type) => {
  switch (type) {
    case 'success': return 'bg-white/90 border-green-100/50'
    case 'error': return 'bg-white/90 border-red-100/50'
    case 'warning': return 'bg-white/90 border-yellow-100/50'
    default: return 'bg-white/90 border-blue-100/50'
  }
}

const iconClasses = (type) => {
  switch (type) {
    case 'success': return 'bg-green-500 text-white'
    case 'error': return 'bg-red-500 text-white'
    case 'warning': return 'bg-yellow-400 text-black'
    default: return 'bg-blue-500 text-white'
  }
}

const textClasses = (type) => {
  switch (type) {
    case 'success': return 'text-gray-900'
    case 'error': return 'text-red-700'
    case 'warning': return 'text-gray-900'
    default: return 'text-blue-700'
  }
}
</script>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(100%) scale(0.9);
}

.toast-leave-to {
  opacity: 0;
  transform: scale(0.9);
}

/* Ensure toasts stack from the top */
.toast-move {
  transition: transform 0.4s ease;
}
</style>
