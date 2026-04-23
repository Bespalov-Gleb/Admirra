<template>
  <div v-if="isOpen" class="fixed inset-0 flex items-center justify-center p-4 z-[200] animate-fade-in" @click.self="$emit('close')">
    <div class="bg-white rounded-[2rem] p-0.5 w-full max-w-sm shadow-[0_20px_50px_rgba(0,0,0,0.25)] transform transition-all animate-modal-in border border-gray-100 relative overflow-hidden">
      <div class="relative z-10 flex flex-col max-h-[70vh] p-6">
        <div class="flex items-center justify-between mb-6">
          <h3 class="text-lg font-black text-black tracking-tight uppercase">Выберите платформу</h3>
          <button @click="$emit('close')" class="p-2 bg-gray-50 text-gray-400 hover:text-black transition-all rounded-full">
            <XMarkIcon class="w-5 h-5" />
          </button>
        </div>

        <CustomScroll class="flex-grow">
          <div class="space-y-3 pr-1">
            <button 
              v-for="(config, key) in PLATFORMS" 
              :key="key"
              @click="selectPlatform(key)"
              class="w-full px-5 py-4 text-left flex items-center justify-between hover:bg-gray-50 rounded-2xl transition-all border border-transparent hover:border-gray-100 group"
              :class="{ 'bg-blue-50 border-blue-100': selectedKey === key }"
            >
              <div class="flex items-center gap-4">
                <div class="w-10 h-10 rounded-xl flex items-center justify-center text-[11px] font-black shadow-sm border" :class="config.className">
                  {{ config.initials }}
                </div>
                <span class="text-[14px] font-black" :class="selectedKey === key ? 'text-blue-600' : 'text-gray-700 group-hover:text-black'">
                  {{ config.label }}
                </span>
              </div>
              <CheckIcon v-if="selectedKey === key" class="w-5 h-5 text-blue-600" />
            </button>
          </div>
        </CustomScroll>
      </div>
    </div>
  </div>
</template>

<script setup>
import { XMarkIcon, CheckIcon } from '@heroicons/vue/24/outline'
import CustomScroll from './ui/CustomScroll.vue'
import { PLATFORMS } from '../constants/platformConfig'

const props = defineProps({
  isOpen: Boolean,
  selectedKey: String
})

const emit = defineEmits(['close', 'select'])

const selectPlatform = (key) => {
  emit('select', key)
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
