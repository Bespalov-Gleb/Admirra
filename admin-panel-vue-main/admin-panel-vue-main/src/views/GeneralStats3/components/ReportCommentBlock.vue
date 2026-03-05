<template>
  <div class="bg-white rounded-2xl p-6 border border-gray-100 shadow-md">
    <div class="flex items-center gap-2 mb-4">
      <div class="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center">
        <DocumentTextIcon class="w-4 h-4 text-blue-600" />
      </div>
      <div>
        <h3 class="text-base font-bold text-gray-900">Получить отчёт</h3>
        <p class="text-xs text-gray-500">за отчётный период</p>
      </div>
    </div>

    <div class="flex flex-wrap gap-3">
      <button
        type="button"
        class="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-blue-500 text-white text-sm font-semibold hover:bg-blue-600 transition-colors shadow-md disabled:opacity-50"
        :disabled="sendingPdf"
        @click="$emit('download-pdf')"
      >
        <ArrowDownTrayIcon class="w-4 h-4" />
        {{ sendingPdf ? 'Скачивание...' : 'Скачать отчёт в PDF' }}
      </button>
      <button
        type="button"
        class="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-blue-500 text-white text-sm font-semibold hover:bg-blue-600 transition-colors shadow-md disabled:opacity-50"
        :disabled="sendingTg"
        @click="$emit('send-telegram')"
      >
        <PaperAirplaneIcon class="w-4 h-4" />
        {{ sendingTg ? 'Отправка...' : 'Скачать отчёт в Telegram' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import {
  DocumentTextIcon,
  ArrowDownTrayIcon,
  PaperAirplaneIcon
} from '@heroicons/vue/24/outline'

defineProps({
  sendingPdf: { type: Boolean, default: false },
  sendingTg: { type: Boolean, default: false },
  sendingEmail: { type: Boolean, default: false }
})

defineEmits(['download-pdf', 'send-telegram', 'send-email'])
</script>
