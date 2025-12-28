<template>
  <div class="bg-white rounded-[40px] p-8 ">
    <!-- Заголовок -->
    <div class="flex items-start gap-3 mb-4">
      <div class="w-6 h-6 text-gray-600 flex-shrink-0 mt-1">
        <ChatBubbleLeftRightIcon class="w-6 h-6" />
      </div>
      <div>
        <h3 class="text-lg font-semibold text-gray-900 mb-1">Комментарии к отчету</h3>
        <p class="text-sm text-gray-500">за отчетный период</p>
      </div>
    </div>

    <!-- Содержимое комментариев -->
    <div class="space-y-4 text-sm text-gray-700 mb-6">
      <p>
        KPI все еще выше, но уже на 1100 ниже, чем на прошлой неделе.
      </p>
      
      <ul class="space-y-2 list-disc list-inside ml-2">
        <li>
          На этой неделе ничего не запускали, только корректировали бюджеты для получения из конвертящих кампаний больше лидов (но это не сработало, просто потратилось больше бюджета, а количество лидов осталось ровно на том же уровне, в одной кампании только на 1 больше)
        </li>
        <li>
          Проводилась чистка площадок (около 300).
        </li>
      </ul>

      <div>
        <p class="font-medium mb-2">По инструментам, которые принесли лиды и за сколько:</p>
        <ul class="space-y-1 list-disc list-inside ml-2">
          <li>МК общий на 2 оффера - 1 звонок, СРА 13 990 руб</li>
          <li>РСЯ по интересам - 1 заявка, СРА 9 788 руб</li>
          <li>РСЯ по ключам - 1 заявка, СРА 9 202 руб</li>
          <li>Поиск по ключам - 2 заявк и 1 звонок, СРА 4 837 руб.</li>
        </ul>
      </div>

      <div>
        <p class="font-medium mb-2">Чтобы снизить цену лида:</p>
        <ul class="space-y-1 list-disc list-inside ml-2">
          <li>Скорректировать бюджеты</li>
          <li>Отключить все кампании на ОЗК, из которых не было лидов ни разу</li>
          <li>Чистка трафика и площадок, как всегда</li>
        </ul>
      </div>

      <p>
        Инструменты в принципе протестированы все, которые могли быть протестированы, нужно оптимизировать рабочие.
      </p>
    </div>
  </div>
  <div class="flex flex-wrap justify-end gap-2">
    <button class="flex items-center gap-2 px-5 sm:px-6 md:px-8 py-4 sm:py-4 md:py-6 border border-slate-200 rounded-[40px] bg-white text-xs sm:text-sm text-gray-700 hover:bg-gray-50 transition-colors">
      <div class="w-8 h-8 sm:w-10 sm:h-10 rounded-lg bg-gray-100 flex items-center justify-center flex-shrink-0">
        <ArrowDownTrayIcon class="w-4 h-4 sm:w-5 sm:h-5 text-gray-600" />
      </div>
      <span>Скачать отчет в PDF</span>
    </button>
    <button class="flex items-center gap-2 px-5 sm:px-6 md:px-8 py-4 sm:py-4 md:py-6 border border-slate-200 rounded-[40px] bg-white text-xs sm:text-sm text-gray-700 hover:bg-gray-50 transition-colors">
      <div class="w-8 h-8 sm:w-10 sm:h-10 rounded-lg bg-gray-100 flex items-center justify-center flex-shrink-0">
        <PaperAirplaneIcon class="w-4 h-4 sm:w-5 sm:h-5 text-gray-600" />
      </div>
      <span>Отправить отчет в Telegram</span>
    </button>
  </div>
</template>

<script setup>
import { 
  ChatBubbleLeftRightIcon,
  ArrowDownTrayIcon,
  PaperAirplaneIcon
} from '@heroicons/vue/24/outline'
</script>


