<template>
  <div class="space-y-1.5">
    <div v-if="label || $slots.label" class="flex items-center justify-between">
      <label :class="['block transition-all', labelClass || 'text-sm font-medium text-gray-700']">
        <slot name="label">{{ label }}</slot>
      </label>
      <slot name="label-right"></slot>
    </div>
    <div class="relative group">
      <input
        v-bind="$attrs"
        :type="type"
        :value="modelValue"
        :placeholder="placeholder"
        :readonly="readonly"
        :disabled="disabled"
        @input="handleInput"
        @blur="$emit('blur')"
        :class="[
          'w-full px-4 py-3 border transition-all outline-none focus:ring-2',
          error ? 'border-red-500 focus:ring-red-100' : 'border-gray-300 focus:border-blue-500 focus:ring-blue-100',
          readonly || disabled ? 'bg-gray-100 cursor-not-allowed' : 'bg-white',
          (showEditButton || hasSlot) && 'pr-12',
          inputClass || 'rounded-xl'
        ]"
      />
      <button
        v-if="showEditButton"
        @click="$emit('edit')"
        class="absolute right-2 top-1/2 -translate-y-1/2 px-3 py-1.5 text-sm bg-gray-800 text-white rounded hover:bg-gray-900 transition-colors font-medium z-10"
      >
        {{ isEditing ? 'Сохранить' : 'Редактировать' }}
      </button>
      <slot></slot>
    </div>
    <p v-if="error" class="text-[11px] text-red-600 font-bold ml-1 animate-shake">{{ error }}</p>
    <p v-if="hint && !error" class="text-[10px] text-gray-400 font-medium ml-1">{{ hint }}</p>
  </div>
</template>

<script>
export default {
  inheritAttrs: false
}
</script>

<script setup>
import { useSlots, computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: [String, Number],
    default: ''
  },
  label: {
    type: String,
    default: ''
  },
  type: {
    type: String,
    default: 'text'
  },
  placeholder: {
    type: String,
    default: ''
  },
  readonly: {
    type: Boolean,
    default: false
  },
  disabled: {
    type: Boolean,
    default: false
  },
  error: {
    type: String,
    default: ''
  },
  hint: {
    type: String,
    default: ''
  },
  showEditButton: {
    type: Boolean,
    default: false
  },
  isEditing: {
    type: Boolean,
    default: false
  },
  inputClass: {
    type: String,
    default: ''
  },
  labelClass: {
    type: String,
    default: ''
  }
})

const slots = useSlots()
const hasSlot = computed(() => !!slots.default)

const emit = defineEmits(['update:modelValue', 'edit', 'blur'])

const handleInput = (event) => {
  if (!props.readonly && !props.disabled) {
    emit('update:modelValue', event.target.value)
  }
}
</script>

<style scoped>
.animate-shake {
  animation: shake 0.5s cubic-bezier(.36,.07,.19,.97) both;
}

@keyframes shake {
  10%, 90% { transform: translate3d(-1px, 0, 0); }
  20%, 80% { transform: translate3d(2px, 0, 0); }
  30%, 50%, 70% { transform: translate3d(-4px, 0, 0); }
  40%, 60% { transform: translate3d(4px, 0, 0); }
}
</style>

