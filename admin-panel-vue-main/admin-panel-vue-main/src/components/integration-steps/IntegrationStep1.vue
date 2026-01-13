<template>
  <div class="pr-1 pb-4 space-y-6">
    <div v-if="error" class="p-4 bg-red-50 border border-red-100 text-red-600 text-[12px] rounded-xl flex items-start gap-3 animate-shake shadow-sm">
      <svg class="w-5 h-5 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path></svg>
      <span class="font-bold">{{ error }}</span>
    </div>

    <form @submit.prevent="$emit('next')" class="space-y-6">
      <!-- Platform Selection -->
      <div class="relative">
        <label class="block text-[9px] font-black text-gray-400 uppercase tracking-[0.2em] mb-3 px-1">Платформа</label>
        <div class="relative">
          <button 
            type="button"
            @click="$emit('openPlatformSelector')"
            class="w-full px-5 py-4 bg-white border border-gray-200 rounded-[1.25rem] focus:border-blue-500 transition-all flex items-center justify-between shadow-sm group hover:border-gray-300"
          >
            <div class="flex items-center gap-4">
              <div v-if="modelValue.platform === 'YANDEX_DIRECT'" class="w-10 h-10 rounded-full flex items-center justify-center overflow-hidden">
                <svg viewBox="0 0 100 100" class="w-full h-full">
                  <circle cx="50" cy="50" r="50" fill="#FFCC00"/>
                  <path d="M65 25C58 25 52 30 52 38C52 46 58 51 65 51C72 51 78 46 78 38C78 30 72 25 65 25ZM65 41C63 41 62 39 62 38C62 37 63 35 65 35C67 35 68 37 68 38C68 39 67 41 65 41Z" fill="#000"/>
                  <path d="M25 75L45 25H55L75 75H65L60 62H40L35 75H25ZM43 54H57L50 36L43 54Z" fill="#000"/>
                </svg>
              </div>
              <div v-else class="w-10 h-10 rounded-xl flex items-center justify-center text-[11px] font-black shadow-sm border" :class="currentPlatform.className">
                {{ currentPlatform.initials }}
              </div>
              <div class="text-left">
                <span class="block text-[14px] font-black text-black leading-none">{{ currentPlatform.label }}</span>
              </div>
            </div>
            <ChevronDownIcon class="w-5 h-5 text-gray-400 group-hover:text-black transition-all duration-300" />
          </button>
        </div>
      </div>

      <!-- Project Selection -->
      <div class="relative">
        <label class="block text-[9px] font-black text-gray-400 uppercase tracking-[0.2em] mb-3 px-1">Проект</label>
        <div class="relative">
          <button 
            type="button"
            @click="$emit('openProjectSelector')"
            class="w-full px-5 py-4 bg-white border border-gray-200 rounded-[1.25rem] focus:border-blue-500 transition-all flex items-center justify-between shadow-sm group hover:border-gray-300"
          >
            <div class="flex items-center gap-3">
              <div class="text-left">
                <span class="block text-[14px] font-black text-black leading-none">
                  {{ modelValue.client_name || 'Выберите проект' }}
                </span>
              </div>
            </div>
            <ChevronDownIcon class="w-5 h-5 text-gray-400 group-hover:text-black transition-all duration-300" />
          </button>
        </div>
      </div>

      <!-- New Project Name Input (Only if explicitly creating new) -->
      <div v-if="isCreatingNewProject" class="animate-modal-in pt-2">
        <Input
          :modelValue="modelValue.client_name"
          @update:modelValue="updateForm({ client_name: $event })"
          label="Название нового проекта"
          labelClass="text-[9px] font-black text-gray-400 uppercase tracking-[0.2em] mb-3 px-1"
          inputClass="rounded-[1.25rem] py-4 font-black text-black shadow-sm border-gray-200 focus:border-blue-500"
          placeholder="Например: Проект Альфа"
          required
        />
      </div>

    </form>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ChevronDownIcon } from '@heroicons/vue/20/solid'
import { PLATFORMS } from '../../constants/platformConfig'
import Input from '../../views/Settings/components/Input.vue'

const props = defineProps({
  modelValue: Object,
  projects: Array,
  isCreatingNewProject: Boolean,
  error: String,
  showToken: Boolean
})

const emit = defineEmits(['update:modelValue', 'update:isCreatingNewProject', 'next', 'openProjectSelector', 'openPlatformSelector'])

const currentPlatform = computed(() => PLATFORMS[props.modelValue.platform])

const updateForm = (updates) => {
  emit('update:modelValue', { ...props.modelValue, ...updates })
}
</script>
