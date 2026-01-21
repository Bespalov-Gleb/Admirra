<template>
  <div v-if="isOpen" class="fixed inset-0 flex items-center justify-center p-4 z-[200] animate-fade-in" @click.self="$emit('close')">
    <div class="bg-white rounded-[2rem] p-0.5 w-full max-w-sm shadow-[0_20px_50px_rgba(0,0,0,0.25)] transform transition-all animate-modal-in border border-gray-100 relative overflow-hidden">
      <div class="relative z-10 flex flex-col max-h-[70vh] p-6 overflow-hidden">
        <div class="flex items-center justify-between mb-6 flex-shrink-0">
          <h3 class="text-lg font-black text-black tracking-tight uppercase">Выберите проект</h3>
          <button @click="$emit('close')" class="p-2 bg-gray-50 text-gray-400 hover:text-black transition-all rounded-full">
            <XMarkIcon class="w-5 h-5" />
          </button>
        </div>

        <div class="mb-4 relative group flex-shrink-0">
          <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
            <MagnifyingGlassIcon class="h-4 w-4 text-gray-400 group-focus-within:text-blue-500 transition-colors" />
          </div>
          <input 
            type="text" 
            v-model="searchQuery"
            placeholder="Поиск проекта..."
            class="block w-full pl-11 pr-4 py-3 bg-gray-50 border-none rounded-2xl text-[13px] font-bold text-gray-900 placeholder-gray-400 focus:ring-2 focus:ring-blue-500/20 transition-all"
          >
        </div>

        <CustomScroll class="flex-1 min-h-0">
          <div class="space-y-2 pr-1">
            <button 
              v-for="project in filteredProjects" 
              :key="project.id"
              @click="selectProject(project)"
              class="w-full px-4 py-3 text-left flex items-center justify-between hover:bg-gray-50 rounded-xl transition-all border border-transparent hover:border-gray-100 group"
              :class="{ 'bg-blue-50 border-blue-100': selectedId === project.id }"
            >
              <span class="text-sm font-bold text-gray-700 group-hover:text-black" :class="{ 'text-blue-600': selectedId === project.id }">
                {{ project.name }}
              </span>
              <CheckIcon v-if="selectedId === project.id" class="w-4 h-4 text-blue-600" />
            </button>

            <button 
              @click="handleCreateNew"
              class="w-full px-4 py-3 text-left flex items-center gap-3 hover:bg-blue-50 rounded-xl transition-all border border-dashed border-gray-200 hover:border-blue-200 mt-4 group"
            >
              <div class="w-6 h-6 rounded-lg bg-blue-100 flex items-center justify-center text-blue-600 group-hover:bg-blue-600 group-hover:text-white transition-all">
                <PlusIcon class="w-4 h-4" />
              </div>
              <span class="text-sm font-black text-blue-600">Создать новый проект</span>
            </button>
          </div>
        </CustomScroll>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { 
  XMarkIcon, 
  PlusIcon,
  CheckIcon,
  MagnifyingGlassIcon
} from '@heroicons/vue/24/outline'
import CustomScroll from './ui/CustomScroll.vue'

const props = defineProps({
  isOpen: Boolean,
  projects: Array,
  selectedId: [String, Number]
})

const emit = defineEmits(['close', 'select', 'create'])

const searchQuery = ref('')

const filteredProjects = computed(() => {
  if (!searchQuery.value) return props.projects
  const q = searchQuery.value.toLowerCase()
  return props.projects.filter(p => p.name && p.name.toLowerCase().includes(q))
})

const selectProject = (project) => {
  emit('select', project)
  emit('close')
}

const handleCreateNew = () => {
  emit('create')
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
