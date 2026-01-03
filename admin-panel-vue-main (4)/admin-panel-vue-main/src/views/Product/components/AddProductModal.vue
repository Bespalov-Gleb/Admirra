<template>
  <Modal
    :is-open="isOpen"
    @update:is-open="$emit('update:isOpen', $event)"
    title="Добавить продукт"
    :show-close-button="true"
    :close-on-backdrop="true"
  >
    <div class="space-y-4">
      <Input
        v-model="form.name"
        label="Название"
        placeholder="Введите название продукта"
        :error="errors.name"
      />
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">Статус</label>
        <div class="relative">
            <select
              v-model="form.status"
              class="w-full px-4 py-2.5 border border-gray-300 rounded-lg bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors appearance-none cursor-pointer pr-10"
              :class="errors.status ? 'border-red-500' : ''"
            >
              <option value="Available">Available</option>
              <option value="In Review">In Review</option>
              <option value="Sold Out">Sold Out</option>
              <option value="Preorder">Preorder</option>
            </select>
          <div class="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
            <svg class="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </div>
        <p v-if="errors.status" class="text-sm text-red-600 mt-1">{{ errors.status }}</p>
      </div>
      <Input
        v-model="form.category"
        label="Категория"
        placeholder="Введите категорию"
        :error="errors.category"
      />
      <Input
        v-model="form.price"
        label="Цена"
        type="number"
        placeholder="Введите цену"
        :error="errors.price"
      />
      <Input
        v-model="form.date"
        label="Дата"
        type="date"
        :error="errors.date"
      />
      <Input
        v-model="form.id"
        label="ID"
        placeholder="Введите ID"
        :error="errors.id"
      />
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">Платформа</label>
        <div class="relative">
          <select
            v-model="form.platform"
            class="w-full px-4 py-2.5 border border-gray-300 rounded-lg bg-white text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors appearance-none cursor-pointer pr-10"
            :class="errors.platform ? 'border-red-500' : ''"
          >
            <option value="">Выберите платформу</option>
            <option value="yandex-direct">Яндекс Директ</option>
            <option value="vk-ads">Вконтакте Ads</option>
            <option value="" disabled>──────────</option>
            <option value="" disabled>Пока в разработке</option>
            <option value="google-ads" disabled>Google Ads</option>
            <option value="facebook-ads" disabled>Facebook Ads</option>
          </select>
          <div class="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
            <svg class="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </div>
        <p v-if="errors.platform" class="text-sm text-red-600 mt-1">{{ errors.platform }}</p>
      </div>
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
          Добавить
        </button>
      </div>
    </template>
  </Modal>
</template>

<script setup>
import { ref, reactive } from 'vue'
import Modal from '../../../components/Modal.vue'
import Input from '../../Settings/components/Input.vue'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:isOpen', 'submit'])

const form = reactive({
  name: '',
  status: 'Available',
  category: '',
  price: '',
  date: '',
  id: '',
  platform: ''
})

const errors = reactive({
  name: '',
  status: '',
  category: '',
  price: '',
  date: '',
  id: '',
  platform: ''
})

const validate = () => {
  let isValid = true
  errors.name = ''
  errors.status = ''
  errors.category = ''
  errors.price = ''
  errors.date = ''
  errors.id = ''
  errors.platform = ''

  if (!form.name.trim()) {
    errors.name = 'Введите название продукта'
    isValid = false
  }

  if (!form.status) {
    errors.status = 'Выберите статус'
    isValid = false
  }

  if (!form.category.trim()) {
    errors.category = 'Введите категорию'
    isValid = false
  }

  if (!form.price) {
    errors.price = 'Введите цену'
    isValid = false
  }

  if (!form.date) {
    errors.date = 'Выберите дату'
    isValid = false
  }

  if (!form.id.trim()) {
    errors.id = 'Введите ID'
    isValid = false
  }

  if (!form.platform) {
    errors.platform = 'Выберите платформу'
    isValid = false
  }

  return isValid
}

const handleSubmit = () => {
  if (validate()) {
    emit('submit', { ...form })
    handleCancel()
  }
}

const handleCancel = () => {
  form.name = ''
  form.status = 'Available'
  form.category = ''
  form.price = ''
  form.date = ''
  form.id = ''
  form.platform = ''
  errors.name = ''
  errors.status = ''
  errors.category = ''
  errors.price = ''
  errors.date = ''
  errors.id = ''
  errors.platform = ''
  emit('update:isOpen', false)
}
</script>

<style scoped>
select option:disabled {
  color: #9ca3af;
  cursor: not-allowed;
  background-color: #f3f4f6;
}
</style>

