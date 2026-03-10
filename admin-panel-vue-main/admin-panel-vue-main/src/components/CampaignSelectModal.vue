<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div
        v-if="modelValue"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/50 backdrop-blur-sm"
        @click.self="close"
      >
        <div class="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden animate-modal-in">
          <!-- Заголовок -->
          <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100 flex-shrink-0">
            <h3 class="text-lg font-bold text-gray-900">Выбор кампаний</h3>
            <button
              @click="close"
              class="p-2 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
            >
              <XMarkIcon class="w-5 h-5" />
            </button>
          </div>

          <!-- Поиск -->
          <div class="px-6 py-4 flex-shrink-0 border-b border-gray-100">
            <div class="relative">
              <MagnifyingGlassIcon class="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                v-model="searchQuery"
                type="text"
                placeholder="Поиск по ID или названию кампании..."
                class="w-full pl-10 pr-4 py-3 bg-gray-50 border border-gray-200 rounded-xl text-sm placeholder-gray-400 focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400 outline-none transition-all"
              />
            </div>
          </div>

          <!-- Выбрать всё / Снять всё -->
          <div class="px-6 py-2 flex gap-3 flex-shrink-0">
            <button
              type="button"
              @click="selectAll"
              class="text-xs font-medium text-blue-600 hover:text-blue-700"
            >
              Выбрать все
            </button>
            <button
              type="button"
              @click="deselectAll"
              class="text-xs font-medium text-gray-500 hover:text-gray-700"
            >
              Снять всё
            </button>
          </div>

          <!-- Список кампаний (скроллируемая зона) -->
          <div class="flex-1 min-h-[200px] max-h-[50vh] overflow-y-auto overscroll-contain px-6 py-2">
            <div v-if="loading" class="py-16 flex flex-col items-center gap-3">
              <div class="w-10 h-10 border-4 border-gray-200 border-t-blue-600 rounded-full animate-spin" />
              <span class="text-sm text-gray-500">Загрузка кампаний...</span>
            </div>
            <div v-else class="space-y-1 pb-4">
              <button
                v-for="campaign in filteredCampaigns"
                :key="campaign.id"
                type="button"
                @click="toggle(campaign.id)"
                class="w-full flex items-start gap-3 px-4 py-3 rounded-xl cursor-pointer hover:bg-gray-50 transition-colors group text-left"
                :class="{ 'bg-blue-50/50': isSelected(campaign.id) }"
              >
                <div
                  class="mt-0.5 w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 transition-colors"
                  :class="isSelected(campaign.id) ? 'bg-blue-600 border-blue-600' : 'border-gray-300 group-hover:border-gray-400'"
                >
                  <CheckIcon v-if="isSelected(campaign.id)" class="w-3.5 h-3.5 text-white" stroke-width="3" />
                </div>
                <div class="min-w-0 flex-1">
                  <span class="block text-sm font-medium text-gray-900 truncate">{{ campaign.name }}</span>
                  <span class="text-xs text-gray-400">{{ campaign.external_id ? `ID: ${campaign.external_id}` : '' }}</span>
                </div>
              </button>
              <div v-if="filteredCampaigns.length === 0" class="py-12 text-center text-sm text-gray-500">
                Кампании не найдены
              </div>
            </div>
          </div>

          <!-- Футер -->
          <div class="px-6 py-4 border-t border-gray-100 flex-shrink-0 flex items-center justify-between gap-4">
            <span class="text-sm text-gray-500">
              Выбрано: {{ selectedIds.length }} из {{ campaigns.length }}
            </span>
            <div class="flex gap-3">
              <button
                type="button"
                @click="close"
                class="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-xl transition-colors"
              >
                Отмена
              </button>
              <button
                type="button"
                @click="apply"
                class="px-5 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-xl transition-colors"
              >
                Применить
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { XMarkIcon, MagnifyingGlassIcon, CheckIcon } from '@heroicons/vue/24/outline'

const props = defineProps({
  modelValue: Boolean,
  campaigns: { type: Array, default: () => [] },
  selectedIds: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'apply'])

const searchQuery = ref('')
const localSelected = ref([])

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      searchQuery.value = ''
      localSelected.value = [...(props.selectedIds || [])]
    }
  },
  { immediate: true }
)

watch(
  () => props.selectedIds,
  (ids) => {
    if (props.modelValue) {
      localSelected.value = [...(ids || [])]
    }
  },
  { deep: true }
)

const filteredCampaigns = computed(() => {
  if (!searchQuery.value.trim()) return props.campaigns
  const q = searchQuery.value.toLowerCase().trim()
  return props.campaigns.filter((c) => {
    const nameMatch = c.name && c.name.toLowerCase().includes(q)
    const idMatch = c.id && String(c.id).toLowerCase().includes(q)
    const extIdMatch = c.external_id && String(c.external_id).toLowerCase().includes(q)
    return nameMatch || idMatch || extIdMatch
  })
})

const isSelected = (id) => localSelected.value.some((x) => String(x) === String(id))

const toggle = (id) => {
  const idx = localSelected.value.findIndex((x) => String(x) === String(id))
  if (idx > -1) {
    localSelected.value = localSelected.value.filter((x) => String(x) !== String(id))
  } else {
    localSelected.value = [...localSelected.value, id]
  }
}

const selectAll = () => {
  localSelected.value = filteredCampaigns.value.map((c) => c.id)
}

const deselectAll = () => {
  localSelected.value = []
}

const close = () => {
  emit('update:modelValue', false)
}

const apply = () => {
  emit('apply', localSelected.value)
  emit('update:modelValue', false)
}
</script>

<style scoped>
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.2s ease;
}
.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}
.animate-modal-in {
  animation: modalIn 0.25s ease-out;
}
@keyframes modalIn {
  from {
    opacity: 0;
    transform: scale(0.97) translateY(8px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}
</style>
