<template>
  <Teleport to="body">
    <Transition name="alert">
      <div
        v-if="show"
        class="fixed top-4 right-4 z-50 max-w-md w-full mx-4"
      >
        <div
          :class="[
            'rounded-lg shadow-lg p-4 flex items-start gap-3',
            typeClasses[type]
          ]"
        >
          <component :is="iconComponent" class="w-5 h-5 flex-shrink-0 mt-0.5" />
          <div class="flex-1">
            <h4 v-if="title" class="font-semibold mb-1">{{ title }}</h4>
            <p class="text-sm">{{ message }}</p>
          </div>
          <button
            @click="handleClose"
            class="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { Teleport } from 'vue'
import {
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon
} from '@heroicons/vue/24/outline'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  type: {
    type: String,
    default: 'success',
    validator: (value) => ['success', 'error', 'warning', 'info'].includes(value)
  },
  title: {
    type: String,
    default: ''
  },
  message: {
    type: String,
    required: true
  },
  duration: {
    type: Number,
    default: 3000
  }
})

const emit = defineEmits(['update:show', 'close'])

const typeClasses = {
  success: 'bg-green-50 border border-green-200 text-green-800',
  error: 'bg-red-50 border border-red-200 text-red-800',
  warning: 'bg-yellow-50 border border-yellow-200 text-yellow-800',
  info: 'bg-blue-50 border border-blue-200 text-blue-800'
}

const iconComponent = computed(() => {
  const icons = {
    success: CheckCircleIcon,
    error: XCircleIcon,
    warning: ExclamationTriangleIcon,
    info: InformationCircleIcon
  }
  return icons[props.type] || CheckCircleIcon
})

let timeoutId = null

const handleClose = () => {
  emit('update:show', false)
  emit('close')
  if (timeoutId) {
    clearTimeout(timeoutId)
    timeoutId = null
  }
}

watch(() => props.show, (isShow) => {
  if (isShow && props.duration > 0) {
    if (timeoutId) {
      clearTimeout(timeoutId)
    }
    timeoutId = setTimeout(() => {
      handleClose()
    }, props.duration)
  }
})

onMounted(() => {
  if (props.show && props.duration > 0) {
    timeoutId = setTimeout(() => {
      handleClose()
    }, props.duration)
  }
})
</script>

<style scoped>
.alert-enter-active {
  transition: all 0.3s ease-out;
}

.alert-leave-active {
  transition: all 0.3s ease-in;
}

.alert-enter-from {
  transform: translateX(100%);
  opacity: 0;
}

.alert-leave-to {
  transform: translateX(100%);
  opacity: 0;
}
</style>

