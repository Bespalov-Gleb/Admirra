<template>
  <Modal
    :is-open="isOpen"
    @update:is-open="$emit('update:isOpen', $event)"
    title="Добавить новый проект"
    :show-close-button="true"
    :close-on-backdrop="true"
    size="lg"
  >
    <div class="space-y-4">
      <Input
        v-model="form.name"
        label="Название проекта"
        placeholder="Введите название проекта"
        :error="errors.name"
      />
      <Input
        v-model="form.description"
        label="Описание"
        placeholder="Введите описание проекта"
        :error="errors.description"
      />
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">Каналы</label>
        <div class="space-y-4">
          <div v-for="channel in availableChannels" :key="channel.value" class="space-y-2">
            <label 
              v-if="channel.value === 'divider' || channel.value === 'in-development'"
              class="flex items-center cursor-default"
            >
              <span class="text-sm text-gray-400">{{ channel.label }}</span>
            </label>
            <label 
              v-else
              class="flex items-center"
            >
              <input
                v-model="form.channels"
                type="checkbox"
                :value="channel.value"
                :disabled="!channel.enabled"
                class="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              />
              <span :class="['ml-2 text-sm', channel.enabled ? 'text-gray-700' : 'text-gray-400']">{{ channel.label }}</span>
              <div v-if="channel.enabled" class="relative ml-2 group">
                <InformationCircleIcon class="w-5 h-5 text-slate-400 hover:text-gray-800 transition-colors" />
                <div class="absolute left-0 bottom-full mb-2 hidden group-hover:block z-10 w-64 p-2 bg-gray-900 text-white text-xs rounded-lg shadow-lg">
                  <div class="mb-1 font-semibold">{{ channel.label }}</div>
                  <div>Введите токен доступа для интеграции с {{ channel.label }}</div>
                  <div class="absolute top-full left-4 -mt-1 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-900"></div>
                </div>
              </div>
            </label>
            <div v-if="form.channels.includes(channel.value) && channel.enabled" class="ml-6 mt-2">
              <Input
                v-model="form.tokens[channel.value]"
                placeholder="Введите токен"
                :error="errors.tokens?.[channel.value]"
              />
            </div>
          </div>
        </div>
        <p v-if="errors.channels" class="text-sm text-red-600 mt-1">{{ errors.channels }}</p>
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
          class="px-4 py-2 text-white bg-gray-900 rounded-lg hover:bg-gray-800 transition-colors"
        >
          Добавить проект
        </button>
      </div>
    </template>
  </Modal>
</template>

<script setup>
import { reactive } from 'vue'
import { InformationCircleIcon } from '@heroicons/vue/24/outline'
import Modal from './Modal.vue'
import Input from '../views/Settings/components/Input.vue'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:isOpen', 'submit'])

const availableChannels = [
  { value: 'yandex-direct', label: 'Яндекс Директ', enabled: true },
  { value: 'vk-ads', label: 'Вконтакте Ads', enabled: true },
  { value: 'divider', label: '──────────', enabled: false },
  { value: 'in-development', label: 'Пока в разработке', enabled: false },
  { value: 'google-ads', label: 'Google Ads', enabled: false },
  { value: 'facebook-ads', label: 'Facebook Ads', enabled: false }
]

const form = reactive({
  name: '',
  description: '',
  channels: [],
  tokens: {}
})

const errors = reactive({
  name: '',
  description: '',
  channels: '',
  tokens: {}
})

const validate = () => {
  let isValid = true
  errors.name = ''
  errors.description = ''
  errors.channels = ''
  errors.tokens = {}

  if (!form.name.trim()) {
    errors.name = 'Введите название проекта'
    isValid = false
  }

  if (!form.description.trim()) {
    errors.description = 'Введите описание проекта'
    isValid = false
  }

  if (form.channels.length === 0) {
    errors.channels = 'Выберите хотя бы один канал'
    isValid = false
  }

  // Валидация токенов для каналов (опционально, можно убрать если токены не обязательны)
  // Если нужна обязательная валидация токенов, раскомментируйте:
  // for (const channel of form.channels) {
  //   if (!form.tokens[channel]?.trim()) {
  //     if (!errors.tokens) {
  //       errors.tokens = {}
  //     }
  //     errors.tokens[channel] = 'Введите токен'
  //     isValid = false
  //   }
  // }

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
  form.description = ''
  form.channels = []
  form.tokens = {}
  errors.name = ''
  errors.description = ''
  errors.channels = ''
  errors.tokens = {}
  emit('update:isOpen', false)
}
</script>

