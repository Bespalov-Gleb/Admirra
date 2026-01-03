<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="isOpen"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-50"
        @click.self="handleBackdropClick"
      >
        <div class="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
          <h3 class="text-lg font-semibold text-gray-900 mb-2">
            {{ title }}
          </h3>
          <p class="text-gray-600 mb-6">
            {{ message }}
          </p>
          <div class="flex gap-3 justify-end">
            <button
              @click="handleCancel"
              class="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
            >
              Отмена
            </button>
            <button
              @click="handleConfirm"
              class="px-4 py-2 text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
            >
              Подтвердить
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { watch } from 'vue'
import { Teleport } from 'vue'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: 'Подтверждение'
  },
  message: {
    type: String,
    required: true
  },
  closeOnBackdrop: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['update:isOpen', 'confirm', 'cancel'])

const handleConfirm = () => {
  emit('confirm')
  emit('update:isOpen', false)
}

const handleCancel = () => {
  emit('cancel')
  emit('update:isOpen', false)
}

const handleBackdropClick = () => {
  if (props.closeOnBackdrop) {
    emit('update:isOpen', false)
  }
}

// Закрытие по Escape
watch(() => props.isOpen, (isOpen) => {
  if (isOpen) {
    const handleEscape = (e) => {
      if (e.key === 'Escape') {
        emit('update:isOpen', false)
      }
    }
    document.addEventListener('keydown', handleEscape)
    return () => {
      document.removeEventListener('keydown', handleEscape)
    }
  }
})
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

