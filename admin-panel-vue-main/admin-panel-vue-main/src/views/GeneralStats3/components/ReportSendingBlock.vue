<template>
  <div class="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm">
    <h3 class="text-sm font-bold text-gray-900 mb-1">Отправка отчётов</h3>
    <p class="text-xs text-gray-500 mb-4">Нажмите для отправки отчёта</p>

    <div class="flex items-center gap-3 mb-4">
      <button
        type="button"
        class="w-11 h-11 rounded-full bg-blue-500 flex items-center justify-center text-white hover:bg-blue-600 transition-colors shadow-md"
        :disabled="sendingTg"
        :title="sendingTg ? 'Отправка...' : 'Отправить в Telegram'"
        @click="$emit('send-telegram')"
      >
        <PaperAirplaneIcon class="w-5 h-5" />
      </button>
      <button
        type="button"
        class="w-11 h-11 rounded-full bg-slate-200 flex items-center justify-center text-slate-600 hover:bg-slate-300 transition-colors"
        :disabled="sendingEmail"
        :title="sendingEmail ? 'Отправка...' : 'Отправить на Email'"
        @click="$emit('send-email')"
      >
        <EnvelopeIcon class="w-5 h-5" />
      </button>
      <div class="w-11 h-11 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 cursor-not-allowed" title="Скоро">
        <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/></svg>
      </div>
      <div class="w-11 h-11 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 cursor-not-allowed" title="Скоро">
        <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/></svg>
      </div>
    </div>

    <select
      class="w-full px-3 py-2.5 border border-gray-200 rounded-xl text-xs font-medium text-gray-700 bg-white focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none"
      disabled
    >
      <option>Каждый ПН в 10:00</option>
    </select>

    <button
      type="button"
      class="mt-4 w-full py-2.5 rounded-xl bg-blue-500 text-white text-sm font-semibold hover:bg-blue-600 transition-colors disabled:opacity-50"
      disabled
    >
      Сохранить
    </button>
  </div>
</template>

<script setup>
import { PaperAirplaneIcon, EnvelopeIcon } from '@heroicons/vue/24/outline'

defineProps({
  sendingTg: { type: Boolean, default: false },
  sendingEmail: { type: Boolean, default: false }
})

defineEmits(['send-telegram', 'send-email'])
</script>
