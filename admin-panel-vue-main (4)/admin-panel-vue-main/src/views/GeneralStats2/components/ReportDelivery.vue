<template>
  <div class="!bg-white rounded-[40px] py-6 px-6 shadow-sm">
    <h3 class="text-lg font-semibold text-gray-900 mb-1">Отправка отчетов</h3>
    <p class="text-sm text-gray-500 mb-4">нажмите для отправки отчетов</p>
    
    <div class="flex items-center gap-4 mb-6">
      <!-- Telegram -->
      <div class="relative cursor-pointer" @click="toggleTelegram">
        <div class="min-w-12 min-h-12">
          <img :src="telegramImg" alt="Telegram" class="w-full h-full object-contain" />
        </div>
        <div v-if="isTelegramActive" class="absolute -bottom-1 -right-1 w-5 h-5 bg-green-500 rounded-full flex items-center justify-center border-2 border-white">
          <CheckIcon class="w-3 h-3 text-white" />
        </div>
      </div>
      
      <!-- Email -->
      <div class="relative cursor-pointer" @click="toggleEmail">
        <div class="min-w-12 min-h-12 rounded-full bg-red-500 flex items-center justify-center">
          <img :src="emailImg" alt="Email" class="w-8 h-8 object-contain" />
        </div>
        <div v-if="isEmailActive" class="absolute -bottom-1 -right-1 w-5 h-5 bg-green-500 rounded-full flex items-center justify-center border-2 border-white">
          <CheckIcon class="w-3 h-3 text-white" />
        </div>
      </div>
    </div>
    
    <div class="relative">
      <select class="w-full px-4 py-2.5 border border-gray-300 rounded-[20px] bg-white text-xs text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 appearance-none cursor-pointer pr-10">
        <option>Каждый ПН в 10:00</option>
        <option>Каждый день в 09:00</option>
        <option>Каждую неделю в понедельник</option>
        <option>Каждый месяц 1 числа</option>
      </select>
      <div class="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
        <ChevronDownIcon class="w-5 h-5 text-gray-400" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ChevronDownIcon, CheckIcon } from '@heroicons/vue/24/outline'
import telegramImg from '../../../assets/imgs/TG.png'
import emailImg from '../../../assets/imgs/e-mail.png'

const isTelegramActive = ref(true)
const isEmailActive = ref(false)

const toggleTelegram = () => {
  isTelegramActive.value = !isTelegramActive.value
}

const toggleEmail = () => {
  isEmailActive.value = !isEmailActive.value
}
</script>


