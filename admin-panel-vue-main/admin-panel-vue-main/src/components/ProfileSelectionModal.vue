<template>
  <div v-if="isOpen" class="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4 z-[200] animate-fade-in" @click.self="$emit('close')">
    <div class="bg-white rounded-[2rem] p-0.5 w-full max-w-sm shadow-[0_20px_50px_rgba(0,0,0,0.25)] transform transition-all animate-modal-in border border-gray-100 relative overflow-hidden">
      <div class="relative z-10 flex flex-col max-h-[70vh] p-6">
        <div class="flex items-center justify-between mb-6">
          <h3 class="text-lg font-black text-black tracking-tight uppercase">Выберите профиль</h3>
          <button @click="$emit('close')" class="p-2 bg-gray-50 text-gray-400 hover:text-black transition-all rounded-full">
            <XMarkIcon class="w-5 h-5" />
          </button>
        </div>

        <div v-if="loading" class="py-12 flex flex-col items-center justify-center gap-4">
          <div class="w-10 h-10 border-4 border-gray-100 border-t-blue-600 rounded-full animate-spin"></div>
          <span class="text-[10px] font-black text-gray-400 uppercase tracking-widest">Загрузка профилей...</span>
        </div>

        <CustomScroll v-else class="flex-grow">
          <div class="space-y-2 pr-1">
            <button 
              v-for="profile in profiles" 
              :key="profile.login"
              @click="selectProfile(profile)"
              class="w-full px-5 py-4 text-left flex items-center justify-between hover:bg-gray-50 rounded-2xl transition-all border border-transparent hover:border-gray-100 group"
              :class="{ 'bg-blue-50 border-blue-100': selectedAccountId === profile.login }"
            >
              <div class="flex items-center gap-3">
                <div class="w-9 h-9 rounded-full bg-gray-100 flex items-center justify-center text-[11px] font-black text-gray-500 uppercase">
                  {{ profile.login.substring(0, 2) }}
                </div>
                <div class="text-left">
                  <span class="block text-[14px] font-black group-hover:text-black" :class="{ 'text-blue-600': selectedAccountId === profile.login }">
                    {{ profile.name || profile.login }}
                  </span>
                  <span class="block text-[10px] text-gray-400 font-bold uppercase tracking-wider">{{ profile.login }}</span>
                </div>
              </div>
              <CheckIcon v-if="selectedAccountId === profile.login" class="w-5 h-5 text-blue-600" />
            </button>

            <div v-if="profiles.length === 0" class="py-12 text-center">
              <p class="text-[11px] font-black text-gray-400 uppercase tracking-widest">Профили не найдены</p>
            </div>
          </div>
        </CustomScroll>
      </div>
    </div>
  </div>
</template>

<script setup>
import { 
  XMarkIcon, 
  CheckIcon 
} from '@heroicons/vue/24/outline'
import CustomScroll from './ui/CustomScroll.vue'

const props = defineProps({
  isOpen: Boolean,
  profiles: Array,
  selectedAccountId: String,
  loading: Boolean
})

const emit = defineEmits(['close', 'select'])

const selectProfile = (profile) => {
  emit('select', profile)
  emit('close')
}
</script>

<style scoped>
.animate-fade-in {
  animation: fadeIn 0.3s ease-out;
}
.animate-modal-in {
  animation: modalIn 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}
@keyframes fadeIn {
  from { opacity: 0; backdrop-filter: blur(0); }
  to { opacity: 1; backdrop-filter: blur(4px); }
}
@keyframes modalIn {
  from { opacity: 0; transform: scale(0.95) translateY(20px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}
</style>
