<template>
  <Modal
    :is-open="isOpen"
    @update:is-open="$emit('update:isOpen', $event)"
    title="Смена пароля"
    :show-close-button="true"
    :close-on-backdrop="true"
  >
    <div class="space-y-4">
      <Input
        v-model="form.currentPassword"
        label="Текущий пароль"
        type="password"
        placeholder="Введите текущий пароль"
        :error="errors.currentPassword"
      />
      <Input
        v-model="form.newPassword"
        label="Новый пароль"
        type="password"
        placeholder="Введите новый пароль"
        :error="errors.newPassword"
      />
      <Input
        v-model="form.confirmPassword"
        label="Подтвердите пароль"
        type="password"
        placeholder="Подтвердите новый пароль"
        :error="errors.confirmPassword"
      />
    </div>

    <template #footer>
      <div class="flex gap-3 justify-end flex-col sm:flex-row">
        <button
          @click="handleCancel"
          class="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
        >
          Отмена
        </button>
        <button
          @click="handleSubmit"
          class="px-4 py-2 text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
        >
          Сохранить
        </button>
      </div>
    </template>
  </Modal>
</template>

<script setup>
import { ref, reactive } from 'vue'
import Modal from '../../../components/Modal.vue'
import Input from './Input.vue'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:isOpen', 'submit'])

const form = reactive({
  currentPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const errors = reactive({
  currentPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const validate = () => {
  let isValid = true
  errors.currentPassword = ''
  errors.newPassword = ''
  errors.confirmPassword = ''

  if (!form.currentPassword) {
    errors.currentPassword = 'Введите текущий пароль'
    isValid = false
  }

  if (!form.newPassword) {
    errors.newPassword = 'Введите новый пароль'
    isValid = false
  } else if (form.newPassword.length < 6) {
    errors.newPassword = 'Пароль должен содержать минимум 6 символов'
    isValid = false
  }

  if (!form.confirmPassword) {
    errors.confirmPassword = 'Подтвердите пароль'
    isValid = false
  } else if (form.newPassword !== form.confirmPassword) {
    errors.confirmPassword = 'Пароли не совпадают'
    isValid = false
  }

  return isValid
}

const handleSubmit = () => {
  if (validate()) {
    emit('submit', {
      currentPassword: form.currentPassword,
      newPassword: form.newPassword
    })
    handleCancel()
  }
}

const handleCancel = () => {
  form.currentPassword = ''
  form.newPassword = ''
  form.confirmPassword = ''
  errors.currentPassword = ''
  errors.newPassword = ''
  errors.confirmPassword = ''
  emit('update:isOpen', false)
}
</script>

