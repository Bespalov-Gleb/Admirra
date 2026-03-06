<template>
  <div class="bg-white rounded-2xl p-6 border border-gray-100 shadow-md">
    <h3 class="text-sm font-bold text-gray-900 mb-1">Отправка отчётов</h3>
    <p class="text-xs text-gray-500 mb-4">Нажмите, для отправки отчета</p>

    <div class="flex items-center gap-3 mb-4">
      <button
        type="button"
        class="relative w-11 h-11 rounded-full flex items-center justify-center transition-colors shadow-md overflow-hidden"
        :class="telegramConfigured ? 'bg-[#0088cc] hover:bg-[#0077b5]' : 'bg-[#0088cc]/70 hover:bg-[#0088cc]'"
        :disabled="sendingTg"
        :title="sendingTg ? 'Отправка...' : 'Отправить в Telegram'"
        @click="$emit('send-telegram')"
      >
        <svg class="w-6 h-6 flex-shrink-0 text-white" viewBox="0 0 32 32" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
          <path d="M29.919 6.163l-4.225 19.925c-0.319 1.406-1.15 1.756-2.331 1.094l-6.438-4.744-3.106 2.988c-0.344 0.344-0.631 0.631-1.294 0.631l0.463-6.556 11.931-10.781c0.519-0.462-0.113-0.719-0.806-0.256l-14.75 9.288-6.35-1.988c-1.381-0.431-1.406-1.381 0.288-2.044l24.837-9.569c1.15-0.431 2.156 0.256 1.781 2.013z"/>
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
