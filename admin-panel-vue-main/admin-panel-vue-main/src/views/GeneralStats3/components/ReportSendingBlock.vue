<template>
  <div class="bg-white dark:bg-[#2A2D3C] rounded-[0.6944rem] p-6 border border-gray-100 dark:border-white/10 shadow-sm flex flex-col min-h-0 font-[Inter]">
    <h3 class="text-[1.25rem] font-normal text-[#09183F] dark:text-white mb-0.5">Отправка отчетов</h3>
    <p class="text-[0.9028rem] font-normal text-gray-400 dark:text-gray-500 mb-5">Нажмите, для отправки отчета</p>

    <div class="flex justify-around items-start w-full mb-5">
      <button
        type="button"
        class="flex flex-col items-center gap-2"
        :disabled="sendingTg"
        :title="sendingTg ? 'Отправка...' : 'Отправить в Telegram'"
        @click="$emit('send-telegram')"
      >
        <span
          class="relative w-[4.0278rem] h-[4.0278rem] rounded-full flex items-center justify-center transition-colors shadow-sm"
          :class="telegramConfigured ? 'bg-[#2563EB] hover:bg-[#1d4ed8]' : 'bg-[#2563EB]/80 hover:bg-[#2563EB]'"
        >
          <svg class="w-7 h-7 text-white" viewBox="0 0 32 32" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
            <path d="M29.919 6.163l-4.225 19.925c-0.319 1.406-1.15 1.756-2.331 1.094l-6.438-4.744-3.106 2.988c-0.344 0.344-0.631 0.631-1.294 0.631l0.463-6.556 11.931-10.781c0.519-0.462-0.113-0.719-0.806-0.256l-14.75 9.288-6.35-1.988c-1.381-0.431-1.406-1.381 0.288-2.044l24.837-9.569c1.15-0.431 2.156 0.256 1.781 2.013z"/>
          </svg>
          <span v-if="telegramConfigured" class="absolute -bottom-0.5 -right-0.5 w-5 h-5 rounded-full bg-[#82d944] flex items-center justify-center">
            <CheckIcon class="w-3 h-3 text-white" />
          </span>
        </span>
        <span class="text-[0.9028rem] text-gray-500 dark:text-gray-400">Telegram</span>
      </button>
      <button
        type="button"
        class="flex flex-col items-center gap-2"
        :disabled="sendingEmail"
        :title="sendingEmail ? 'Отправка...' : 'Отправить на Email'"
        @click="$emit('send-email')"
      >
        <span
          class="relative w-[4.0278rem] h-[4.0278rem] rounded-full flex items-center justify-center transition-colors shadow-sm"
          :class="emailConfigured ? 'bg-[#374151] dark:bg-[#3B5998] hover:bg-[#1f2937] dark:hover:bg-[#2d4373]' : 'bg-[#6B7280] dark:bg-[#4A7AFF] hover:bg-[#4B5563] dark:hover:bg-[#5A8BFF]'"
        >
          <EnvelopeIcon class="w-7 h-7 text-white" />
          <span v-if="emailConfigured" class="absolute -bottom-0.5 -right-0.5 w-5 h-5 rounded-full bg-[#82d944] flex items-center justify-center">
            <CheckIcon class="w-3 h-3 text-white" />
          </span>
        </span>
        <span class="text-[0.9028rem] text-gray-500 dark:text-gray-400">E-mail</span>
      </button>
    </div>

    <div class="flex items-center gap-3">
      <div class="flex-1 relative">
        <select
          v-model="schedule"
          class="w-full h-[2.6389rem] pl-3 pr-9 border border-gray-200 dark:border-white/20 rounded-[0.6944rem] text-[0.8333rem] font-normal text-gray-700 dark:text-gray-200 bg-white dark:bg-[#232637] focus:ring-2 focus:ring-[#2563EB]/20 dark:focus:ring-[#4A7AFF]/20 focus:border-[#2563EB] dark:focus:border-[#4A7AFF] outline-none appearance-none"
        @change="$emit('schedule-change', schedule)"
      >
          <option v-for="opt in scheduleOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
        </select>
        <ChevronDownIcon class="absolute right-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
      </div>
      <button
        type="button"
        class="h-[2.6389rem] px-4 rounded-[0.6944rem] bg-[#2563EB] dark:bg-[#4A7AFF] text-white text-[0.8333rem] font-normal hover:bg-[#1d4ed8] dark:hover:bg-[#5A8BFF] transition-colors disabled:opacity-50 flex-shrink-0"
      :disabled="saving"
      @click="$emit('save', schedule)"
    >
      {{ saving ? 'Сохранение...' : 'Сохранить' }}
    </button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { EnvelopeIcon } from '@heroicons/vue/24/solid'
import { CheckIcon, ChevronDownIcon } from '@heroicons/vue/24/solid'

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
