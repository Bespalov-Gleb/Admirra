<template>
  <div class="pr-1 pb-4 space-y-6">
    <!-- Loading Banner -->
    <div v-if="loading" class="bg-blue-50 border border-blue-200 rounded-2xl p-4 flex items-center gap-3">
      <div class="w-8 h-8 border-3 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
      <div>
        <p class="text-sm font-bold text-blue-900">Загрузка счетчиков...</p>
        <p class="text-xs text-blue-600">Получаем счетчики Метрики для выбранных кампаний</p>
      </div>
    </div>

    <div class="space-y-4">
      <!-- Header -->
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 px-1">
        <div>
          <label class="block text-[9px] font-black text-gray-400 uppercase tracking-[0.2em] mb-1">СЧЕТЧИКИ МЕТРИКИ</label>
          <p class="text-[11px] text-gray-500 font-bold">Выберите счетчики, для которых нужно отслеживать цели</p>
        </div>
      </div>

      <!-- Counters Table -->
      <div class="bg-white border border-gray-100 rounded-[2rem] overflow-hidden shadow-sm">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-gray-50/50 border-b border-gray-100">
              <th class="w-10 px-2 py-4">
                <div 
                  @click="toggleSelectAll"
                  class="w-5 h-5 mx-auto rounded-md border-2 flex items-center justify-center transition-all bg-white cursor-pointer" 
                  :class="isAllSelected ? 'bg-blue-600 border-blue-600' : 'border-gray-200 hover:border-blue-400'"
                >
                  <CheckIcon v-if="isAllSelected" class="w-3.5 h-3.5 text-white" stroke-width="4" />
                  <div v-else-if="isAnySelected" class="w-2 h-0.5 bg-gray-400 rounded-full"></div>
                </div>
              </th>
              <th class="px-4 py-4 text-[10px] font-black text-gray-400 uppercase tracking-widest">Название счетчика</th>
              <th class="px-4 py-4 text-[10px] font-black text-gray-400 uppercase tracking-widest">Сайт</th>
              <th class="px-4 py-4 text-[10px] font-black text-gray-400 uppercase tracking-widest">Источник</th>
            </tr>
          </thead>
          <tbody>
            <!-- Loading State -->
            <template v-if="loading">
              <tr v-for="i in 5" :key="i" class="border-b border-gray-50">
                <td class="px-2 py-5"><Skeleton width="5" height="5" rounded="md" class="mx-auto" /></td>
                <td class="px-4 py-5"><Skeleton width="48" height="4" /></td>
                <td class="px-4 py-5"><Skeleton width="32" height="3" /></td>
                <td class="px-4 py-5"><Skeleton width="20" height="3" /></td>
              </tr>
            </template>

            <tr 
              v-else
              v-for="counter in counters" 
              :key="counter.id"
              class="border-b border-gray-50 last:border-none group hover:bg-blue-50/30 transition-all cursor-pointer"
              :class="{ 'bg-blue-50/50': selectedIds.includes(counter.id) }"
            >
              <!-- Checkbox -->
              <td class="px-2 py-4" @click.stop="$emit('toggle', counter.id)">
                <div 
                  class="w-5 h-5 mx-auto rounded-md border-2 flex items-center justify-center transition-all bg-white" 
                  :class="selectedIds.includes(counter.id) ? 'bg-blue-600 border-blue-600' : 'border-gray-200 group-hover:border-gray-400'"
                >
                  <CheckIcon v-if="selectedIds.includes(counter.id)" class="w-3.5 h-3.5 text-white" stroke-width="4" />
                </div>
              </td>

              <td class="px-4 py-4">
                <div class="flex flex-col">
                  <span class="text-[13px] font-black text-gray-800 leading-tight group-hover:text-blue-600 transition-colors">
                    {{ counter.name }}
                  </span>
                  <span class="text-[9px] text-gray-400 font-bold uppercase tracking-wider">ID: {{ counter.id }}</span>
                </div>
              </td>

              <td class="px-4 py-4">
                <span class="text-[11px] font-bold text-gray-600">{{ counter.site || '—' }}</span>
              </td>

              <td class="px-4 py-4">
                <span 
                  class="px-2.5 py-1 rounded-full text-[8px] font-black uppercase tracking-widest border"
                  :class="getSourceClass(counter.source)"
                >
                  {{ formatSource(counter.source) }}
                </span>
              </td>
            </tr>

            <tr v-if="!loading && counters.length === 0">
              <td colspan="4" class="py-20 text-center">
                <div class="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg class="w-8 h-8 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                </div>
                <p class="text-sm font-bold text-gray-600 mb-2">Счетчики не найдены</p>
                <p class="text-xs text-gray-400">Проверьте, что у выбранных кампаний есть привязанные счетчики Метрики</p>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { CheckIcon } from '@heroicons/vue/24/outline'
import Skeleton from '../ui/Skeleton.vue'

const props = defineProps({
  counters: Array,
  selectedIds: Array,
  loading: Boolean
})

const emit = defineEmits(['toggle', 'bulkSelect', 'bulkDeselect', 'next'])

const isAllSelected = computed(() => {
  if (props.counters.length === 0) return false
  return props.counters.every(c => props.selectedIds.includes(c.id))
})

const isAnySelected = computed(() => {
  return props.counters.some(c => props.selectedIds.includes(c.id))
})

const toggleSelectAll = () => {
  const ids = props.counters.map(c => c.id)
  if (isAllSelected.value) {
    emit('bulkDeselect', ids)
  } else {
    emit('bulkSelect', ids)
  }
}

const formatSource = (source) => {
  const labels = {
    'campaign': 'ИЗ КАМПАНИЙ',
    'profile': 'ИЗ ПРОФИЛЯ',
    'profile_fallback': 'ИЗ ПРОФИЛЯ'
  }
  return labels[source] || source?.toUpperCase() || 'НЕИЗВЕСТНО'
}

const getSourceClass = (source) => {
  if (source === 'campaign') return 'bg-green-50 text-green-600 border-green-100'
  if (source === 'profile' || source === 'profile_fallback') return 'bg-blue-50 text-blue-600 border-blue-100'
  return 'bg-gray-50 text-gray-500 border-gray-100'
}
</script>

