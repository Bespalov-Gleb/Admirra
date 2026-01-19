<template>
  <div class="pr-1 pb-4 space-y-6">
    <div v-if="error" class="p-4 bg-red-50 border border-red-100 text-red-600 text-[12px] rounded-xl flex items-start gap-3 animate-shake shadow-sm">
      <svg class="w-5 h-5 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path></svg>
      <span class="font-bold">{{ error }}</span>
    </div>

    <form @submit.prevent="$emit('next')" class="space-y-6">
      <!-- Platform Info & Health -->
      <div class="bg-gradient-to-br from-blue-600 to-indigo-700 rounded-[2rem] p-6 text-white shadow-xl relative overflow-hidden group mb-4">
        <div class="absolute -right-10 -bottom-10 w-48 h-48 bg-white/10 rounded-full blur-3xl group-hover:scale-110 transition-transform duration-700"></div>
        <div class="relative z-10 flex items-center gap-6">
          <div class="w-16 h-16 bg-white/20 backdrop-blur-md rounded-2xl flex items-center justify-center border border-white/30 shadow-inner">
             <PlatformIcon :platform="modelValue.platform" class="w-10 h-10 brightness-0 invert" />
          </div>
          <div class="flex-grow">
            <h2 class="text-xl font-black mb-1 tracking-tight">Интеграция с {{ PLATFORMS[modelValue.platform]?.label }}</h2>
            <p class="text-blue-100 text-[11px] font-bold max-w-lg leading-relaxed">
              Автоматический сбор кампаний, ключевых слов и статистики.
              <a href="#" class="text-white underline underline-offset-4 decoration-white/30 hover:decoration-white transition-all ml-1">Как это работает?</a>
            </p>
          </div>
          <div class="hidden md:flex flex-col items-center gap-2">
            <div class="flex items-center gap-2 px-3 py-1.5 bg-white/10 backdrop-blur-sm rounded-xl border border-white/20">
              <div class="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse shadow-[0_0_8px_#4ade80]"></div>
              <span class="text-[9px] font-black uppercase tracking-widest text-white/90">API: СОЕДИНЕНО</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Platform Selection Grid -->
      <div class="space-y-4">
        <label class="block text-[9px] font-black text-gray-400 uppercase tracking-[0.2em] mb-3 px-1">ВЫБЕРИТЕ РЕКЛАМНЫЙ КАНАЛ</label>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div 
            v-for="(config, key) in PLATFORMS" 
            :key="key"
            @click="!config.comingSoon && updateForm({ platform: key })"
            class="relative group p-4 bg-white border-2 rounded-[1.5rem] transition-all duration-300 cursor-pointer overflow-hidden shadow-sm hover:shadow-xl hover:-translate-y-1"
            :class="[
              modelValue.platform === key ? 'border-blue-600 ring-4 ring-blue-50' : 'border-gray-50 hover:border-blue-200',
              config.comingSoon ? 'opacity-50 cursor-not-allowed filter grayscale' : ''
            ]"
          >
            <!-- Selection Checkmark -->
            <div 
              class="absolute top-4 right-4 w-6 h-6 rounded-full bg-blue-600 flex items-center justify-center transition-all duration-300 scale-0"
              :class="{ 'scale-100': modelValue.platform === key }"
            >
              <CheckIcon class="w-4 h-4 text-white" stroke-width="4" />
            </div>

            <div class="flex flex-col h-full">
              <div class="mb-4">
                <div 
                  class="w-12 h-12 rounded-2xl flex items-center justify-center text-[14px] font-black transition-all group-hover:scale-110 shadow-inner"
                  :class="config.className"
                >
                  {{ config.initials }}
                </div>
              </div>
              
              <div class="space-y-1">
                <h3 class="text-[13px] font-black text-black uppercase tracking-tight">{{ config.label }}</h3>
                <p class="text-[10px] font-bold text-gray-400 leading-tight pr-4">
                  {{ config.comingSoon ? 'СКОРО БУДЕТ' : config.description }}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6 pt-4">
        <!-- Project Selection & Creation -->
        <div class="space-y-4">
          <label class="block text-[9px] font-black text-gray-400 uppercase tracking-[0.2em] mb-3 px-1">ВЫБЕРИТЕ ПРОЕКТ (КЛИЕНТА)</label>
          
          <div class="relative" ref="projectSelectorRef">
            <div class="relative group">
              <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                <MagnifyingGlassIcon class="h-4 w-4 text-gray-400 group-focus-within:text-blue-500 transition-colors" />
              </div>
              <input 
                type="text"
                v-model="projectSearchQuery"
                @focus="isDropdownOpen = true"
                placeholder="Поиск проекта..."
                class="w-full pl-11 pr-12 py-4 bg-white border border-gray-100 rounded-[1.25rem] focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all font-bold text-[14px] text-gray-900 shadow-sm"
              >
              <div class="absolute inset-y-0 right-0 pr-4 flex items-center">
                <button 
                  type="button"
                  @click.stop="toggleDropdown"
                  class="p-1 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <ChevronDownIcon class="h-5 w-5 text-gray-400" :class="{ 'rotate-180': isDropdownOpen }" />
                </button>
              </div>
            </div>

            <Transition name="fade-scale">
              <div 
                v-if="isDropdownOpen" 
                class="absolute z-50 left-0 right-0 mt-2 bg-white border border-gray-100 rounded-[1.5rem] shadow-[0_20px_50px_rgba(0,0,0,0.1)] overflow-hidden animate-modal-in"
              >
                <div class="max-h-[280px] overflow-y-auto py-2 custom-scrollbar">
                  <div 
                    @click="handleCreateNewAction"
                    class="px-4 py-3 mx-2 rounded-xl flex items-center gap-3 cursor-pointer transition-all hover:bg-blue-50 group border border-transparent hover:border-blue-100"
                  >
                    <div class="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center group-hover:bg-blue-600 transition-colors">
                      <PlusIcon class="w-4 h-4 text-blue-600 group-hover:text-white" />
                    </div>
                    <div>
                      <span class="block text-[12px] font-black text-blue-600 uppercase tracking-tighter">СОЗДАТЬ НОВЫЙ ПРОЕКТ</span>
                    </div>
                  </div>
                  <div class="h-px bg-gray-50 my-2"></div>
                  <div 
                    v-for="project in filteredProjects" 
                    :key="project.id"
                    @click="selectProject(project)"
                    class="px-3 py-2.5 mx-2 mb-1 rounded-xl flex items-center justify-between cursor-pointer transition-all hover:bg-gray-50 group"
                    :class="{ 'bg-blue-50/50': modelValue.client_id === project.id }"
                  >
                    <div class="flex items-center gap-3 flex-1 min-w-0">
                      <div class="w-8 h-8 rounded-lg bg-gray-50 flex items-center justify-center text-[10px] font-black text-gray-400 group-hover:bg-blue-50 group-hover:text-blue-600 transition-colors flex-shrink-0">
                        {{ project.name.substring(0, 2).toUpperCase() }}
                      </div>
                      <span class="text-[13px] font-bold text-gray-700 group-hover:text-blue-600 transition-colors truncate" :title="project.name">{{ project.name }}</span>
                    </div>
                    <CheckIcon v-if="modelValue.client_id === project.id" class="w-4 h-4 text-blue-600 flex-shrink-0 ml-2" />
                  </div>
                </div>
              </div>
            </Transition>
          </div>

          <div v-if="isCreatingNewProject" class="pt-2 animate-fade-in">
            <Input
              :modelValue="modelValue.client_name"
              @update:modelValue="updateForm({ client_name: $event })"
              label="НАЗВАНИЕ НОВОГО ПРОЕКТА"
              labelClass="text-[9px] font-black text-gray-400 uppercase tracking-[0.2em] mb-3 px-1"
              inputClass="rounded-2xl py-4 font-black text-black shadow-sm border-gray-100 focus:border-blue-500"
              placeholder="Например: Мой Магазин"
              required
            />
          </div>
        </div>

        <!-- Sync Settings -->
        <div class="space-y-4">
          <label class="block text-[9px] font-black text-gray-400 uppercase tracking-[0.2em] mb-3 px-1">ПАРАМЕТРЫ СИНХРОНИЗАЦИИ</label>
          <div class="bg-gray-50/50 border border-gray-100 rounded-[2rem] p-6 space-y-5">
            <div class="flex items-center justify-between">
              <div class="flex flex-col">
                <span class="text-[12px] font-black text-gray-800 tracking-tight leading-none mb-1">Глубина истории</span>
                <span class="text-[9px] text-gray-400 font-bold uppercase tracking-wider">Начальный импорт</span>
              </div>
              <select 
                :value="modelValue.sync_depth || 90"
                @change="updateForm({ sync_depth: parseInt($event.target.value) })"
                class="bg-white border border-gray-100 rounded-xl px-3 py-2 text-[11px] font-black text-blue-600 focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 outline-none shadow-sm cursor-pointer"
              >
                <option :value="30">30 дней</option>
                <option :value="90">3 месяца</option>
                <option :value="180">6 месяцев</option>
                <option :value="365">1 год</option>
              </select>
            </div>

            <div class="flex items-center justify-between pt-4 border-t border-gray-200/50">
              <div class="flex flex-col">
                <span class="text-[12px] font-black text-gray-800 tracking-tight leading-none mb-1">Авто-синхронизация</span>
                <span class="text-[9px] text-gray-400 font-bold uppercase tracking-wider">Ежедневное обновление</span>
              </div>
              <button 
                type="button"
                @click="updateForm({ auto_sync: !modelValue.auto_sync })"
                class="w-11 h-6 rounded-full transition-all relative outline-none"
                :class="modelValue.auto_sync ? 'bg-blue-600 shadow-[0_4px_12px_rgba(37,99,235,0.3)]' : 'bg-gray-200'"
              >
                <div class="absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-all shadow-sm" :class="{ 'translate-x-5': modelValue.auto_sync }"></div>
              </button>
            </div>
          </div>
        </div>
      </div>

    </form>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { ChevronDownIcon, MagnifyingGlassIcon } from '@heroicons/vue/20/solid'
import { CheckIcon, PlusIcon } from '@heroicons/vue/24/outline'
import { PLATFORMS } from '../../constants/platformConfig'
import Input from '../../views/Settings/components/Input.vue'
import PlatformIcon from '../ui/PlatformIcon.vue'

const props = defineProps({
  modelValue: Object,
  projects: Array,
  isCreatingNewProject: Boolean,
  error: String,
  showToken: Boolean
})

const emit = defineEmits(['update:modelValue', 'update:isCreatingNewProject', 'next', 'openProjectSelector', 'openPlatformSelector'])

const projectSelectorRef = ref(null)
const projectSearchQuery = ref(props.modelValue.client_name || '')
const isDropdownOpen = ref(false)

// Close dropdown when clicking outside the entire project selector container
const handleClickOutside = (event) => {
  if (projectSelectorRef.value && !projectSelectorRef.value.contains(event.target)) {
    isDropdownOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside)
})

const filteredProjects = computed(() => {
  if (!projectSearchQuery.value) return props.projects
  const q = projectSearchQuery.value.toLowerCase()
  return props.projects.filter(p => p.name.toLowerCase().includes(q))
})

const toggleDropdown = () => {
  isDropdownOpen.value = !isDropdownOpen.value
}

const selectProject = (project) => {
  emit('update:isCreatingNewProject', false)
  updateForm({ client_id: project.id, client_name: project.name })
  projectSearchQuery.value = project.name
  isDropdownOpen.value = false
}

const handleCreateNewAction = () => {
  emit('update:isCreatingNewProject', true)
  updateForm({ client_id: null, client_name: '' })
  projectSearchQuery.value = ''
  isDropdownOpen.value = false
}

const updateForm = (updates) => {
  emit('update:modelValue', { ...props.modelValue, ...updates })
}
</script>

<style scoped>
/* Custom scrollbar styling */
.custom-scrollbar {
  scrollbar-width: thin;
  scrollbar-color: #e5e7eb #f9fafb;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 8px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: #f9fafb;
  border-radius: 10px;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: #e5e7eb;
  border-radius: 10px;
  transition: background 0.2s;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: #d1d5db;
}
</style>
