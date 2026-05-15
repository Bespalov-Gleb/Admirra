<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-[9000] flex items-center justify-center bg-black/50 p-4" @click.self="close">
      <div class="w-full max-w-[32rem] rounded-[1.25rem] border border-black/5 bg-white p-6 shadow-[0_24px_70px_rgba(15,23,42,0.22)] dark:border-white/10 dark:bg-[#2C2F3D]">
        <div class="mb-5 flex items-start justify-between gap-4">
          <div class="min-w-0">
            <h4 class="text-[1.25rem] font-bold leading-tight text-[#171717] dark:text-white">Аватарка проекта</h4>
            <p class="mt-2 text-[0.9028rem] leading-[1.35] text-[#696969]/70 dark:text-white/50">{{ project?.name }}</p>
          </div>
          <button
            type="button"
            class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#f5f7f9] text-[#696969] transition hover:bg-[#edf3ff] hover:text-[#2563eb] dark:bg-white/10 dark:text-white/70"
            aria-label="Закрыть"
            @click="close"
          >
            <svg class="h-4 w-4" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path d="M3.5 3.5 12.5 12.5M12.5 3.5 3.5 12.5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
            </svg>
          </button>
        </div>

        <label
          class="group flex min-h-[14rem] cursor-pointer flex-col items-center justify-center rounded-[1rem] border border-dashed border-[#cbd5e1] bg-[#f8fafc] px-6 py-7 text-center transition hover:border-[#2563eb]/45 hover:bg-[#f3f7ff] dark:border-white/15 dark:bg-white/5 dark:hover:bg-white/8"
          @dragover.prevent
          @drop.prevent="onDrop"
        >
          <input type="file" class="sr-only" accept="image/jpeg,image/png,image/webp" @change="onFileChange" />
          <div class="mb-4 flex h-[5.5rem] w-[5.5rem] items-center justify-center overflow-hidden rounded-full bg-[#e8eef9] text-[1.35rem] font-semibold text-[#2563eb] ring-4 ring-white dark:bg-white/10 dark:ring-white/5">
            <img v-if="previewUrl" :src="previewUrl" alt="" class="h-full w-full object-cover" />
            <span v-else>{{ projectInitials(project) }}</span>
          </div>
          <div class="mb-1 text-[1rem] font-semibold text-[#171717] dark:text-white">Перетащите изображение или выберите файл</div>
          <div class="text-[0.875rem] text-[#696969]/65 dark:text-white/45">JPG, PNG или WebP до 5 МБ. Изображение будет обрезано до квадрата.</div>
        </label>

        <div v-if="error" class="mt-3 rounded-[0.75rem] bg-red-50 px-4 py-3 text-[0.9028rem] text-red-600 dark:bg-red-500/10 dark:text-red-300">
          {{ error }}
        </div>

        <div class="mt-5 flex flex-wrap gap-3">
          <button
            type="button"
            class="h-[3.0556rem] rounded-xl bg-[#2563eb] px-5 text-[0.9722rem] font-medium text-white transition hover:bg-[#1d4ed8] disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="saving || !selectedFile"
            @click="save"
          >
            {{ saving ? 'Сохранение...' : 'Сохранить аватарку' }}
          </button>
          <button
            type="button"
            class="h-[3.0556rem] rounded-xl border border-black/10 bg-white px-5 text-[0.9722rem] text-gray-600 transition hover:bg-gray-50 disabled:opacity-50 dark:border-white/15 dark:bg-white/5 dark:text-gray-300 dark:hover:bg-white/10"
            :disabled="saving"
            @click="close"
          >
            Отмена
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import api from '@/api/axios'
import { projectAvatarUrl, projectInitials } from '@/utils/projectAvatar'

const props = defineProps({
  project: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['close', 'saved'])

const selectedFile = ref(null)
const objectUrl = ref('')
const saving = ref(false)
const error = ref('')

const previewUrl = computed(() => objectUrl.value || projectAvatarUrl(props.project))

function revokeObjectUrl() {
  if (objectUrl.value) {
    URL.revokeObjectURL(objectUrl.value)
    objectUrl.value = ''
  }
}

function selectFile(file) {
  error.value = ''
  if (!file) return
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
    error.value = 'Поддерживаются только JPG, PNG и WebP.'
    return
  }
  if (file.size > 5 * 1024 * 1024) {
    error.value = 'Размер файла не должен превышать 5 МБ.'
    return
  }
  revokeObjectUrl()
  selectedFile.value = file
  objectUrl.value = URL.createObjectURL(file)
}

function onFileChange(event) {
  selectFile(event.target.files?.[0])
  event.target.value = ''
}

function onDrop(event) {
  selectFile(event.dataTransfer?.files?.[0])
}

async function save() {
  if (!props.project?.id || !selectedFile.value) return
  saving.value = true
  error.value = ''
  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    const { data } = await api.post(`clients/${props.project.id}/avatar`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    emit('saved', data)
    close()
  } catch (err) {
    error.value = err.response?.data?.detail || 'Не удалось загрузить аватарку.'
  } finally {
    saving.value = false
  }
}

function close() {
  emit('close')
}

watch(
  () => props.project?.id,
  () => {
    selectedFile.value = null
    error.value = ''
    revokeObjectUrl()
  }
)

onBeforeUnmount(revokeObjectUrl)
</script>
