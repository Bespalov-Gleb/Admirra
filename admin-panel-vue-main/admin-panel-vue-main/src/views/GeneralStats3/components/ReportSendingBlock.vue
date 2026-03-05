<template>
  <div class="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
    <h3 class="text-sm font-bold text-gray-900 mb-1">Отправка отчётов</h3>
    <p class="text-xs text-gray-500 mb-4">Нажмите, для отправки отчета</p>

    <div class="flex items-center gap-3 mb-4">
      <button
        type="button"
        class="relative w-11 h-11 rounded-full flex items-center justify-center transition-colors shadow-md"
        :class="telegramConfigured ? 'bg-blue-500 text-white hover:bg-blue-600' : 'bg-slate-200 text-slate-600 hover:bg-slate-300'"
        :disabled="sendingTg"
        :title="sendingTg ? 'Отправка...' : 'Отправить в Telegram'"
        @click="$emit('send-telegram')"
      >
        <PaperAirplaneIcon class="w-5 h-5" />
        <span v-if="telegramConfigured" class="absolute -bottom-0.5 -right-0.5 w-4 h-4 rounded-full bg-green-500 flex items-center justify-center">
          <CheckIcon class="w-2.5 h-2.5 text-white" />
        </span>
      </button>
      <button
        type="button"
        class="relative w-11 h-11 rounded-full flex items-center justify-center transition-colors"
        :class="emailConfigured ? 'bg-blue-500 text-white hover:bg-blue-600 shadow-md' : 'bg-slate-200 text-slate-600 hover:bg-slate-300'"
        :disabled="sendingEmail"
        :title="sendingEmail ? 'Отправка...' : 'Отправить на Email'"
        @click="$emit('send-email')"
      >
        <EnvelopeIcon class="w-5 h-5" />
        <span v-if="emailConfigured" class="absolute -bottom-0.5 -right-0.5 w-4 h-4 rounded-full bg-green-500 flex items-center justify-center">
          <CheckIcon class="w-2.5 h-2.5 text-white" />
        </span>
      </button>
    </div>

    <select
      v-model="schedule"
      class="w-full px-3 py-2.5 border border-gray-200 rounded-xl text-xs font-medium text-gray-700 bg-white focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none"
      @change="$emit('schedule-change', schedule)"
    >
      <option v-for="opt in scheduleOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
    </select>

    <button
      type="button"
      class="mt-4 w-full py-2.5 rounded-xl bg-blue-500 text-white text-sm font-semibold hover:bg-blue-600 transition-colors disabled:opacity-50"
      :disabled="saving"
      @click="$emit('save', schedule)"
    >
      {{ saving ? 'Сохранение...' : 'Сохранить' }}
    </button>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { PaperAirplaneIcon, EnvelopeIcon } from '@heroicons/vue/24/outline'
import { CheckIcon } from '@heroicons/vue/24/solid'

defineProps({
  sendingTg: { type: Boolean, default: false },
  sendingEmail: { type: Boolean, default: false },
  telegramConfigured: { type: Boolean, default: false },
  emailConfigured: { type: Boolean, default: false },
  saving: { type: Boolean, default: false }
})

defineEmits(['send-telegram', 'send-email', 'schedule-change', 'save'])

const schedule = ref('mon_10')
const scheduleOptions = [
  { value: 'mon_10', label: 'Каждый ПН в 10:00' },
  { value: 'tue_10', label: 'Каждый ВТ в 10:00' },
  { value: 'wed_10', label: 'Каждую СР в 10:00' },
  { value: 'thu_10', label: 'Каждый ЧТ в 10:00' },
  { value: 'fri_10', label: 'Каждую ПТ в 10:00' },
  { value: 'daily_10', label: 'Ежедневно в 10:00' }
]
</script>
