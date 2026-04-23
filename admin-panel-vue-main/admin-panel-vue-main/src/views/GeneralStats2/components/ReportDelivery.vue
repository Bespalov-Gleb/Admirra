<template>
  <div class="bg-white rounded-[40px] p-8">
    <h3 class="text-lg font-semibold text-gray-900 mb-1">Отправка отчетов</h3>
    <p class="text-sm text-gray-500 mb-4">нажмите для отправки отчетов</p>
    
    <div class="flex items-center gap-4 mb-6">
      <!-- Telegram (активен) -->
      <div class="relative">
        <div class="min-w-12 min-h-12 rounded-full bg-blue-500 flex items-center justify-center">
          <svg class="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.54-.37-.62-.2-1.11-.31-1.07-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z"/>
          </svg>
        </div>
        <div class="absolute -bottom-1 -right-1 w-5 h-5 bg-green-500 rounded-full flex items-center justify-center border-2 border-white">
          <svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
          </svg>
        </div>
      </div>
      
      <!-- Email (неактивен) -->
      <div class="relative">
        <div class="min-w-12 min-h-12 rounded-full bg-red-500 flex items-center justify-center">
          <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
          </svg>
        </div>
        <div class="absolute -bottom-1 -right-1 w-5 h-5 bg-red-500 rounded-full flex items-center justify-center border-2 border-white">
          <svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </div>
      </div>
      
      <!-- VK -->
      <div class="min-w-12 min-h-12 rounded-full bg-yellow-400 flex items-center justify-center">
        <div class="flex gap-0.5">
          <div class="w-1 h-4 bg-red-500 rounded"></div>
          <div class="w-1 h-4 bg-blue-500 rounded"></div>
        </div>
      </div>
    </div>
    
    <select class="w-full px-4 py-2.5 border border-gray-300 rounded-lg bg-white text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 appearance-none cursor-pointer pr-10">
      <option>Каждый ПН в 10:00</option>
      <option>Каждый день в 09:00</option>
      <option>Каждую неделю в понедельник</option>
      <option>Каждый месяц 1 числа</option>
    </select>
  </div>
</template>

<script setup>
</script>


