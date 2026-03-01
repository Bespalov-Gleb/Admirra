<template>
  <div class="space-y-6 overflow-x-hidden w-full">
    <!-- Заголовок -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
      <div>
        <h1 class="text-2xl sm:text-3xl font-bold text-gray-900">AI Анализ</h1>
        <p class="text-sm text-gray-500 mt-1">Аналитика и рекомендации на основе данных рекламных кампаний</p>
      </div>
    </div>

    <!-- Кнопки действий -->
    <div class="flex flex-wrap gap-4">
      <button
        class="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-violet-500 to-purple-600 text-white font-medium rounded-2xl shadow-lg shadow-violet-500/25 hover:shadow-violet-500/40 transition-all hover:scale-[1.02] active:scale-[0.98]"
      >
        <DocumentTextIcon class="w-5 h-5" />
        Сформировать отчёт
      </button>
      <button
        class="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-500 to-cyan-500 text-white font-medium rounded-2xl shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40 transition-all hover:scale-[1.02] active:scale-[0.98]"
      >
        <LightBulbIcon class="w-5 h-5" />
        Получить рекомендации
      </button>
    </div>

    <!-- Чат -->
    <div class="bg-white/80 backdrop-blur-xl rounded-[32px] border border-white/80 shadow-lg overflow-hidden flex flex-col min-h-[400px]">
      <!-- Шапка чата -->
      <div class="px-6 py-4 border-b border-gray-100 bg-gradient-to-r from-gray-50/80 to-white/80">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center">
            <SparklesIcon class="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 class="font-bold text-gray-900">AI Ассистент</h3>
            <p class="text-xs text-gray-500">Задайте вопрос или выберите действие выше</p>
          </div>
        </div>
      </div>

      <!-- Область сообщений -->
      <div class="flex-1 p-6 overflow-y-auto min-h-[320px]">
        <div class="flex flex-col items-center justify-center py-16 text-center">
          <div class="w-16 h-16 rounded-2xl bg-gray-100 flex items-center justify-center mb-4">
            <ChatBubbleLeftRightIcon class="w-8 h-8 text-gray-400" />
          </div>
          <p class="text-gray-500 text-sm max-w-xs">
            Чат пока не активен. Используйте кнопки выше для формирования отчёта или получения рекомендаций.
          </p>
        </div>
      </div>

      <!-- Поле ввода -->
      <div class="p-4 border-t border-gray-100 bg-gray-50/50">
        <div class="flex gap-3">
          <input
            type="text"
            placeholder="Введите сообщение..."
            disabled
            class="flex-1 px-4 py-3 rounded-xl border border-gray-200 bg-white text-gray-400 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500/20 cursor-not-allowed"
          />
          <button
            disabled
            class="px-5 py-3 rounded-xl bg-gray-200 text-gray-400 font-medium text-sm cursor-not-allowed"
          >
            Отправить
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import {
  DocumentTextIcon,
  LightBulbIcon,
  SparklesIcon,
  ChatBubbleLeftRightIcon
} from '@heroicons/vue/24/outline'
</script>
