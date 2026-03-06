<template>
  <div class="bg-white rounded-2xl p-6 border border-gray-100 shadow-md">
    <h3 class="text-sm font-bold text-gray-900 mb-1">Отправка отчётов</h3>
    <p class="text-xs text-gray-500 mb-4">Нажмите, для отправки отчета</p>

    <div class="flex items-center gap-3 mb-4">
      <button
        type="button"
        class="relative w-11 h-11 rounded-full flex items-center justify-center transition-colors shadow-md overflow-hidden"
        :class="telegramConfigured ? 'bg-[#0088cc] text-white hover:bg-[#0077b5]' : 'bg-slate-200 text-slate-600 hover:bg-slate-300'"
        :disabled="sendingTg"
        :title="sendingTg ? 'Отправка...' : 'Отправить в Telegram'"
        @click="$emit('send-telegram')"
      >
        <svg class="w-5 h-5 flex-shrink-0" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
          <path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.359-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-1.491-.197-.39-.345-.853-.345-1.375 0-1.323.673-1.85.673-1.85s8.423-5.006 11.2-6.623c.55-.402 1.049-.573 1.049-.573z"/>
        </svg>
        <span v-if="telegramConfigured" class="absolute -bottom-0.5 -right-0.5 w-4 h-4 rounded-full bg-green-500 flex items-center justify-center">
          <CheckIcon class="w-2.5 h-2.5 text-white" />
        </span>
      </button>
      <button
        type="button"
        class="relative w-11 h-11 rounded-full flex items-center justify-center transition-colors shadow-md"
        :class="emailConfigured ? 'bg-slate-700 text-white hover:bg-slate-800' : 'bg-slate-600 text-white hover:bg-slate-700'"
        :disabled="sendingEmail"
        :title="sendingEmail ? 'Отправка...' : 'Отправить на Email'"
        @click="$emit('send-email')"
      >
        <EnvelopeIcon class="w-5 h-5 text-white" />
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
import { ref, watch } from 'vue'
import { EnvelopeIcon } from '@heroicons/vue/24/outline'
import { CheckIcon } from '@heroicons/vue/24/solid'

const props = defineProps({
  sendingTg: { type: Boolean, default: false },
  sendingEmail: { type: Boolean, default: false },
  initialSchedule: { type: String, default: 'mon_10' },
  telegramConfigured: { type: Boolean, default: false },
  emailConfigured: { type: Boolean, default: false },
  saving: { type: Boolean, default: false }
})

defineEmits(['send-telegram', 'send-email', 'schedule-change', 'save'])

const scheduleOptions = [
  { value: 'mon_10', label: 'Каждый ПН в 10:00' },
  { value: 'tue_10', label: 'Каждый ВТ в 10:00' },
  { value: 'wed_10', label: 'Каждую СР в 10:00' },
  { value: 'thu_10', label: 'Каждый ЧТ в 10:00' },
  { value: 'fri_10', label: 'Каждую ПТ в 10:00' },
  { value: 'daily_10', label: 'Ежедневно в 10:00' }
]
const validSchedules = new Set(scheduleOptions.map(o => o.value))
const schedule = ref(validSchedules.has(props.initialSchedule) ? props.initialSchedule : 'mon_10')
watch(() => props.initialSchedule, (v) => {
  if (v && validSchedules.has(v)) schedule.value = v
})
</script>
