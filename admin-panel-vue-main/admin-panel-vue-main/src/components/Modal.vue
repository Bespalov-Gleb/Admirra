<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="isOpen"
        class="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 md:p-6 bg-black bg-opacity-50"
        @click.self="handleBackdropClick"
      >
        <div :class="[
          'bg-white rounded-lg shadow-xl w-full max-h-[95vh] overflow-hidden flex flex-col mx-2 sm:mx-4',
          {
            'max-w-sm': props.size === 'sm',
            'max-w-md': props.size === 'md',
            'max-w-lg': props.size === 'lg',
            'max-w-xl': props.size === 'xl',
            'max-w-2xl': props.size === '2xl'
          }
        ]">
          <!-- Заголовок -->
          <div class="flex items-center justify-between p-4 sm:p-6 border-b border-gray-200 flex-shrink-0 sticky top-0 bg-white z-10">
            <h3 class="text-lg font-semibold text-gray-900">{{ title }}</h3>
            <button
              v-if="showCloseButton"
              @click="handleClose"
              class="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <!-- Контент -->
          <div class="flex-1 overflow-y-auto p-4 sm:p-6">
            <slot></slot>
          </div>

          <!-- Футер -->
          <div v-if="$slots.footer" class="border-t border-gray-200 p-4 sm:p-6 flex-shrink-0 sticky bottom-0 bg-white z-10">
            <slot name="footer"></slot>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { Teleport } from 'vue'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: 'Модальное окно'
  },
  showCloseButton: {
    type: Boolean,
    default: true
  },
  closeOnBackdrop: {
    type: Boolean,
    default: true
  },
  size: {
    type: String,
    default: 'md',
    validator: (value) => ['sm', 'md', 'lg', 'xl', '2xl'].includes(value)
  }
})

const emit = defineEmits(['update:isOpen', 'close'])

const handleClose = () => {
  emit('update:isOpen', false)
  emit('close')
}

const handleBackdropClick = () => {
  if (props.closeOnBackdrop) {
    handleClose()
  }
}
</script>

<style scoped>
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .bg-white,
.modal-leave-active .bg-white {
  transition: transform 0.3s ease, opacity 0.3s ease;
}

.modal-enter-from .bg-white,
.modal-leave-to .bg-white {
  transform: scale(0.9);
  opacity: 0;
}
</style>

