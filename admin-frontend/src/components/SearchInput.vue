<template>
  <label class="search-input">
    <MagnifyingGlassIcon />
    <input :value="modelValue" :placeholder="placeholder" @input="onInput" />
    <button v-if="modelValue" type="button" @click="$emit('update:modelValue', '')"><XMarkIcon /></button>
  </label>
</template>

<script setup>
import { onBeforeUnmount } from 'vue'
import { MagnifyingGlassIcon, XMarkIcon } from '@heroicons/vue/24/outline'
const props = defineProps({ modelValue: String, placeholder: { type: String, default: 'Поиск' }, debounce: { type: Number, default: 300 } })
const emit = defineEmits(['update:modelValue', 'search'])
let timer
const onInput = (event) => {
  const value = event.target.value
  emit('update:modelValue', value)
  clearTimeout(timer)
  timer = setTimeout(() => emit('search', value), props.debounce)
}
onBeforeUnmount(() => clearTimeout(timer))
</script>
