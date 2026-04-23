<template>
  <div class="relative w-full max-w-4xl mx-auto overflow-hidden rounded-[24px] bg-gradient-to-br from-[#1e40af] via-[#1d4ed8] to-[#1e3a8a] px-5 sm:px-10 pt-4 sm:pt-6 pb-0 shadow-2xl border border-white/10 group">
    <!-- Декоративные геометрические элементы -->
    <div class="absolute inset-0 opacity-20 pointer-events-none overflow-hidden">
      <div class="absolute top-0 right-0 w-full h-full transform translate-x-1/3 -translate-y-1/3">
        <svg viewBox="0 0 400 400" fill="none" class="w-full h-full text-white">
          <path d="M400 0L0 400L400 400V0Z" fill="currentColor" fill-opacity="0.05" />
          <path d="M0 0L400 400V0H0Z" fill="currentColor" fill-opacity="0.03" />
        </svg>
      </div>
    </div>
    
    <div class="absolute top-[5%] left-[5%] w-24 h-24 bg-blue-300 rounded-full opacity-10 blur-[60px]"></div>
    <div class="absolute bottom-[5%] right-[5%] w-48 h-48 bg-blue-400 rounded-full opacity-10 blur-[80px]"></div>

    <!-- Изображение Логотипа (Absolute positioning - камтар майдатар) -->
    <div class="absolute bottom-0 left-0 w-56 h-56 sm:w-[320px] sm:h-[320px] pointer-events-none overflow-hidden hidden md:block">
      <div class="absolute bottom-0 w-full h-[150%] transform translate-y-[35%]">
        <img 
          :src="LogoImg" 
          alt="AdMirra Logo" 
          class="w-full h-full object-contain"
        />
      </div>
    </div>

    <!-- Контент (бо фосилаи танзимшуда аз чап) -->
    <div class="relative z-10 md:ml-[260px] text-center md:text-left space-y-4 pb-8 sm:pb-12">
      <div class="space-y-1.5">
        <h2 class="text-xl sm:text-2xl lg:text-[26px] font-black text-white leading-[1.2] tracking-tight uppercase drop-shadow-md max-w-[480px] mx-auto md:mx-0">
          ДЛЯ НАЧАЛА РАБОТЫ, НЕОБХОДИМО СОЗДАТЬ ПРОЕКТ
        </h2>
        <p class="text-blue-50/90 text-[12px] sm:text-[13px] leading-relaxed max-w-[460px] mx-auto md:mx-0">
          В рамках проекта доступна выгрузка статистики рекламных кампаний и детальный анализ показателей с использованием 
          <span class="bg-yellow-400 text-blue-900 px-1.5 py-0.5 rounded font-bold shadow-sm">AI-ассистентов</span>.
        </p>
      </div>

      <!-- Форма создания -->
      <form @submit.prevent="handleCreate" class="space-y-4 max-w-[400px] mx-auto md:mx-0">
        <div class="relative group/input">
          <input
            v-model="projectName"
            type="text"
            placeholder="Название проекта"
            required
            class="w-full px-5 py-3 bg-white border-2 border-transparent rounded-[14px] text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-400/30 focus:border-blue-300 transition-all text-sm shadow-md"
          />
        </div>
        
        <button
          type="submit"
          :disabled="!projectName || loading"
          class="w-full md:w-40 px-8 py-3 bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 disabled:opacity-50 disabled:cursor-not-allowed text-white font-black rounded-[14px] shadow-[0_6px_20px_rgba(0,0,0,0.25)] transition-all hover:-translate-y-0.5 active:translate-y-0 text-sm uppercase tracking-wider"
        >
          <span v-if="loading">...</span>
          <span v-else>Создать</span>
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import LogoImg from '../../../assets/imgs/logo/img_geen.png'

const props = defineProps({
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['create'])

const projectName = ref('')

const handleCreate = () => {
  if (projectName.value.trim()) {
    emit('create', projectName.value.trim())
    projectName.value = ''
  }
}
</script>

<style scoped>
.font-black {
  font-weight: 900;
}
</style>
