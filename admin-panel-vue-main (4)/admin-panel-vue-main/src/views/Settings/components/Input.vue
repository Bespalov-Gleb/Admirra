<template>
  <div class="space-y-2">
    <label v-if="label" class="block text-sm font-medium text-gray-700">
      {{ label }}
    </label>
    <div class="relative">
      <input
        :type="type"
        :value="modelValue"
        :placeholder="placeholder"
        :readonly="readonly"
        :disabled="disabled"
        @input="handleInput"
        @blur="$emit('blur')"
        :class="[
          'w-full px-4 py-2.5 border rounded-lg focus:outline-none focus:ring-2 transition-colors',
          error ? 'border-red-500 focus:ring-red-500' : 'border-gray-300 focus:ring-blue-500 focus:border-blue-500',
          readonly || disabled ? 'bg-gray-100 cursor-not-allowed' : 'bg-white',
          showEditButton && 'pr-12'
        ]"
      />
      <button
        v-if="showEditButton"
        @click="$emit('edit')"
        class="absolute right-2 top-1/2 -translate-y-1/2 px-3 py-1.5 text-sm bg-gray-800 text-white rounded hover:bg-gray-900 transition-colors font-medium"
      >
        {{ isEditing ? 'Сохранить' : 'Редактировать' }}
      </button>
    </div>
    <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
    <p v-if="hint && !error" class="text-sm text-gray-500">{{ hint }}</p>
  </div>
</template>

<script setup>
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
  }
})

const emit = defineEmits(['update:modelValue', 'edit', 'blur'])

const handleInput = (event) => {
  if (!props.readonly && !props.disabled) {
    emit('update:modelValue', event.target.value)
  }
}
</script>

