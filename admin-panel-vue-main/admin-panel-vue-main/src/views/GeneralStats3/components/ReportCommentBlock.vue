<template>
  <div class="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
    <div class="flex items-center justify-between mb-4">
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center">
          <ChatBubbleLeftRightIcon class="w-4 h-4 text-blue-600" />
        </div>
        <div>
          <h3 class="text-base font-bold text-gray-900">Комментарий к отчёту</h3>
          <p class="text-xs text-gray-500">за отчётный период</p>
        </div>
      </div>
      <button
        type="button"
        class="text-sm font-medium text-blue-600 hover:text-blue-700"
        disabled
      >
        Редактировать
      </button>
    </div>

    <div v-if="loading" class="flex items-center gap-3 py-8 text-gray-500">
      <div class="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      <span class="text-sm">Генерация отчёта...</span>
    </div>
    <div v-else-if="error" class="py-6 text-red-500 text-sm">
      {{ error }}
    </div>
    <div v-else class="text-sm text-gray-700 mb-6 min-h-[80px]">
      <p v-if="!comment" class="text-gray-500 italic">
        Нажмите «Сформировать отчёт» на странице AI Анализ или используйте кнопки ниже.
      </p>
      <div v-else class="whitespace-pre-wrap">{{ comment }}</div>
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
  ChatBubbleLeftRightIcon,
  ArrowDownTrayIcon,
  PaperAirplaneIcon,
  EnvelopeIcon
} from '@heroicons/vue/24/outline'

defineProps({
  comment: { type: String, default: '' },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  sendingPdf: { type: Boolean, default: false },
  sendingTg: { type: Boolean, default: false },
  sendingEmail: { type: Boolean, default: false }
})

defineEmits(['download-pdf', 'send-telegram', 'send-email'])
</script>
