<template>
  <Teleport to="body">
    <div class="fixed inset-0 z-[9000] flex items-center justify-center bg-black/50 p-4" @click.self="close">
      <div class="w-full max-w-[32rem] rounded-[1.25rem] border border-black/5 bg-white p-6 shadow-[0_24px_70px_rgba(15,23,42,0.22)] dark:border-white/10 dark:bg-[#2C2F3D]">
        <div class="mb-5 flex items-start justify-between gap-4">
          <div class="min-w-0">
            <h4 class="text-[1.25rem] font-bold leading-tight text-[#171717] dark:text-white">Редактирование проекта</h4>
            <p class="mt-2 text-[0.9028rem] leading-[1.35] text-[#696969]/70 dark:text-white/50">ID: {{ projectDisplayId }}</p>
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

        <!-- Avatar -->
        <div class="mb-5 flex items-center gap-4">
          <button
            type="button"
            class="group relative flex h-[4.5rem] w-[4.5rem] shrink-0 items-center justify-center overflow-hidden rounded-full bg-[#e8eef9] text-[1.1rem] font-semibold text-[#2563eb] ring-4 ring-white transition hover:ring-[#2563eb]/20 dark:bg-white/10 dark:ring-white/5"
            @click="avatarModalOpen = true"
          >
            <img v-if="currentAvatarUrl" :src="currentAvatarUrl" alt="" class="h-full w-full object-cover" />
            <span v-else>{{ initials }}</span>
            <span class="absolute inset-0 flex items-center justify-center rounded-full bg-black/0 transition hover:bg-black/20">
              <svg class="h-5 w-5 text-white opacity-0 transition group-hover:opacity-100" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
                <path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4 11.5-11.5Z"/>
              </svg>
            </span>
          </button>
          <div class="min-w-0">
            <button
              type="button"
              class="text-[0.9028rem] font-medium text-[#2563eb] transition hover:text-[#1d4ed8]"
              @click="avatarModalOpen = true"
            >
              Изменить аватарку
            </button>
            <p class="mt-1 text-[0.7639rem] text-[#696969]/50 dark:text-white/35">JPG, PNG или WebP до 5 МБ</p>
          </div>
        </div>

        <!-- Name -->
        <div class="mb-4">
          <label class="mb-1.5 block text-[0.9028rem] font-medium text-[#171717] dark:text-white/80">Название проекта</label>
          <input
            v-model="form.name"
            type="text"
            class="w-full rounded-xl border border-black/10 bg-transparent px-4 py-3 text-[0.9722rem] text-gray-700 outline-none transition placeholder:text-gray-400 focus:border-[#2563eb] focus:ring-2 focus:ring-[#2563eb]/15 dark:border-white/15 dark:text-gray-200 dark:placeholder:text-white/40"
            placeholder="Название"
          />
        </div>

        <!-- Description -->
        <div class="mb-5">
          <label class="mb-1.5 block text-[0.9028rem] font-medium text-[#171717] dark:text-white/80">Описание</label>
          <textarea
            v-model="form.description"
            rows="3"
            class="w-full resize-y rounded-xl border border-black/10 bg-transparent px-4 py-3 text-[0.9722rem] text-gray-700 outline-none transition placeholder:text-gray-400 focus:border-[#2563eb] focus:ring-2 focus:ring-[#2563eb]/15 dark:border-white/15 dark:text-gray-200 dark:placeholder:text-white/40"
            placeholder="Описание проекта"
          />
        </div>

        <!-- Error -->
        <div v-if="error" class="mb-4 rounded-[0.75rem] bg-red-50 px-4 py-3 text-[0.9028rem] text-red-600 dark:bg-red-500/10 dark:text-red-300">
          {{ error }}
        </div>

        <!-- Actions -->
        <div class="flex flex-wrap gap-3">
          <button
            type="button"
            class="h-[3.0556rem] rounded-xl bg-[#2563eb] px-5 text-[0.9722rem] font-medium text-white transition hover:bg-[#1d4ed8] disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="saving || !form.name?.trim()"
            @click="save"
          >
            {{ saving ? 'Сохранение...' : 'Сохранить' }}
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

    <ProjectAvatarUploadModal
      v-if="avatarModalOpen"
      :project="avatarProjectData"
      @close="avatarModalOpen = false"
      @saved="handleAvatarSaved"
    />
  </Teleport>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import api from '@/api/axios'
import { projectAvatarUrl, projectInitials } from '@/utils/projectAvatar'
import ProjectAvatarUploadModal from './ProjectAvatarUploadModal.vue'

const props = defineProps({
  project: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['close', 'saved'])

const form = reactive({
  name: '',
  description: '',
})

const saving = ref(false)
const error = ref('')
const avatarModalOpen = ref(false)
const updatedAvatarUrl = ref(null)

const projectName = computed(() => props.project?.name || props.project?.title || '')
const projectDisplayId = computed(() => props.project?.display_id || String(props.project?.id || '').substring(0, 8).toUpperCase())
const initials = computed(() => projectInitials({ name: form.name || projectName.value }))

const currentAvatarUrl = computed(() => {
  if (updatedAvatarUrl.value !== null) return updatedAvatarUrl.value
  return projectAvatarUrl(props.project)
})

const avatarProjectData = computed(() => ({
  id: props.project?.id,
  name: form.name || projectName.value,
  avatar_url: updatedAvatarUrl.value ?? props.project?.avatar_url,
}))

watch(
  () => props.project?.id,
  () => {
    if (props.project) {
      form.name = projectName.value
      form.description = props.project.description || ''
      updatedAvatarUrl.value = null
      error.value = ''
    }
  },
  { immediate: true }
)

async function save() {
  if (!props.project?.id || !form.name?.trim()) return
  saving.value = true
  error.value = ''
  try {
    const { data } = await api.put(`clients/${props.project.id}`, {
      name: form.name.trim(),
      description: form.description.trim() || null,
    })
    emit('saved', data)
    close()
  } catch (err) {
    error.value = err.response?.data?.detail || 'Не удалось сохранить изменения.'
  } finally {
    saving.value = false
  }
}

function handleAvatarSaved(updatedProject) {
  updatedAvatarUrl.value = projectAvatarUrl(updatedProject) || null
  emit('saved', updatedProject)
}

function close() {
  emit('close')
}
</script>
