<template>
  <Teleport to="body">
    <div class="psm-overlay" @click.self="close">
      <div class="psm-container" ref="containerRef">
        <!-- Header -->
        <div class="psm-header">
          <h2 class="psm-title">Настройки проекта</h2>
          <button type="button" class="psm-close" aria-label="Закрыть" @click="close">
            <svg class="w-4 h-4" viewBox="0 0 16 16" fill="none">
              <path d="M3.5 3.5 12.5 12.5M12.5 3.5 3.5 12.5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
            </svg>
          </button>
        </div>

        <div class="psm-body">
          <!-- ===== Block 1: Основное ===== -->
          <section class="psm-card">
            <div class="psm-card__header">
              <h3 class="psm-card__title">Основное</h3>
              <div class="psm-card__id">
                <span class="psm-card__id-text">ID {{ projectDisplayId }}</span>
                <button type="button" class="psm-card__id-copy" @click="copyProjectId" title="Копировать ID">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                  </svg>
                </button>
              </div>
            </div>

            <div class="psm-card__body">
              <!-- Avatar + Name row -->
              <div class="flex items-start gap-5">
                <div class="flex flex-col items-center gap-2 shrink-0">
                  <button type="button" class="psm-avatar" @click="avatarModalOpen = true">
                    <img v-if="currentAvatarUrl" :src="currentAvatarUrl" alt="" class="w-full h-full object-cover rounded-full" />
                    <span v-else class="psm-avatar__initials">{{ initials }}</span>
                    <span class="psm-avatar__hover">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4 11.5-11.5Z"/>
                      </svg>
                    </span>
                  </button>
                  <button type="button" class="psm-avatar__btn" @click="avatarModalOpen = true">Загрузить</button>
                </div>

                <div class="flex-1 min-w-0 space-y-4">
                  <div>
                    <label class="psm-label">Название проекта</label>
                    <input v-model="form.name" type="text" class="psm-input" placeholder="Название проекта" />
                  </div>
                  <div>
                    <label class="psm-label">Описание проекта</label>
                    <textarea v-model="form.description" rows="2" class="psm-input psm-textarea" placeholder="Краткое описание для команды агентства..."></textarea>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <!-- ===== Block 2: Подключённые каналы ===== -->
          <section class="psm-card">
            <div class="psm-card__header">
              <h3 class="psm-card__title">Подключённые каналы</h3>
              <button type="button" class="psm-btn-accent" @click="$emit('add-channel')">
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M6 1v10M1 6h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
                Добавить канал
              </button>
            </div>

            <div class="psm-card__body">
              <div v-if="projectChannels.length === 0" class="psm-empty">
                Нет подключённых рекламных кабинетов
              </div>
              <div v-else class="space-y-2">
                <div v-for="ch in projectChannels" :key="ch.id" class="psm-channel-row">
                  <div class="flex items-center gap-3 min-w-0">
                    <PlatformIcon :platform="ch.platform" size="md" />
                    <div class="min-w-0">
                      <div class="psm-channel-name">{{ ch.name }}</div>
                      <div class="psm-channel-status">
                        <span class="psm-channel-dot" :class="ch.statusClass"></span>
                        {{ ch.statusText }}
                      </div>
                    </div>
                  </div>
                  <div class="flex items-center gap-2 shrink-0">
                    <button type="button" class="psm-btn-outline-sm" @click="$emit('configure-channel', ch)">Настроить</button>
                    <button type="button" class="psm-btn-outline-sm psm-btn-outline-sm--warn" @click="confirmDeleteChannel(ch)">Удалить</button>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <!-- ===== Block 3: Сайт проекта ===== -->
          <section class="psm-card">
            <div class="psm-card__header">
              <h3 class="psm-card__title">Сайт проекта</h3>
            </div>
            <div class="psm-card__body">
              <p class="psm-hint mb-3">Используется для AI-аудита — оценка скорости, мобильной версии, посадочных.</p>
              <input v-model="form.site_url" type="url" class="psm-input" placeholder="https://example.com" />
            </div>
          </section>

          <!-- ===== Block 4: Детектор и цели ===== -->
          <section class="psm-card">
            <div class="psm-card__header">
              <h3 class="psm-card__title">
                Детектор и цели
                <span class="psm-optional-tag">необязательно</span>
              </h3>
              <label class="psm-toggle">
                <input type="checkbox" v-model="form.detector_enabled" class="sr-only" />
                <span class="psm-toggle__track" :class="{ 'psm-toggle__track--on': form.detector_enabled }">
                  <span class="psm-toggle__thumb" :class="{ 'psm-toggle__thumb--on': form.detector_enabled }"></span>
                </span>
                <span class="psm-toggle__label">Детектор аномалий</span>
              </label>
            </div>

            <div class="psm-card__body">
              <!-- State A: no integrations -->
              <div v-if="integrationState === 'A'" class="psm-detector-stub">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/>
                </svg>
                <p>Подключите рекламный кабинет, чтобы настроить цели и бюджеты</p>
                <button type="button" class="psm-btn-accent" @click="$emit('add-channel')">Подключить интеграцию</button>
              </div>

              <!-- State B: syncing -->
              <div v-else-if="integrationState === 'B'" class="psm-detector-stub">
                <div class="psm-skeleton w-full h-4 mb-3"></div>
                <div class="psm-skeleton w-3/4 h-4 mb-3"></div>
                <div class="psm-skeleton w-1/2 h-4"></div>
                <p class="mt-4 text-center">Загружаем данные кабинета...</p>
              </div>

              <!-- State C: data available -->
              <div v-else>
                <!-- Collapsed when detector is off -->
                <div v-if="!form.detector_enabled && !detectorFieldsExpanded" class="psm-detector-collapsed">
                  <span class="psm-detector-collapsed__text">Бюджеты и цели</span>
                  <span class="psm-detector-collapsed__hint">скрыты — детектор выключен</span>
                  <button type="button" class="psm-detector-collapsed__link" @click="detectorFieldsExpanded = true">Развернуть</button>
                </div>

                <!-- Expanded fields -->
                <div v-if="form.detector_enabled || detectorFieldsExpanded">
                  <!-- Budgets per channel -->
                  <div class="mb-6">
                    <h4 class="psm-subsection-title">Бюджет на период — по каналам</h4>
                    <p class="psm-hint mb-3">Версионный: задаётся на период с датами. Смена бюджета — новый период, не аномалия.</p>

                    <div class="flex flex-wrap gap-4">
                      <div v-for="ch in projectChannels" :key="'budget-' + ch.id" class="psm-budget-card">
                        <div class="flex items-center gap-2 mb-2">
                          <PlatformIcon :platform="ch.platform" size="sm" />
                          <span class="text-[0.9028rem] font-medium text-[#171717] dark:text-white">{{ ch.name }}</span>
                        </div>
                        <input type="text" class="psm-input psm-input--compact" :placeholder="'Сумма, ₽'" v-model="budgets[ch.id]" />
                        <div class="psm-hint mt-1">период: {{ currentPeriodLabel }}</div>
                      </div>
                    </div>
                  </div>

                  <!-- Target CPA table -->
                  <div>
                    <h4 class="psm-subsection-title">Целевая стоимость действия (CPA)</h4>
                    <p class="psm-hint mb-3">Заполняйте только цели с KPI от клиента. Контроль включается тумблером по каждой строке.</p>

                    <div v-if="goalRows.length === 0" class="psm-empty">Цели не найдены. Подключите счётчик Метрики или настройте цели ВК.</div>
                    <div v-else class="psm-goals-table">
                      <div class="psm-goals-table__header">
                        <span>Канал</span>
                        <span>Цель</span>
                        <span>Целевой CPA</span>
                        <span>Контроль</span>
                      </div>
                      <div
                        v-for="goal in goalRows"
                        :key="goal.id"
                        class="psm-goals-table__row"
                        :class="{ 'psm-goals-table__row--summary': goal.isSummary }"
                      >
                        <div class="flex items-center gap-2">
                          <PlatformIcon :platform="goal.platform" size="sm" />
                        </div>
                        <div class="min-w-0">
                          <div class="psm-goal-name truncate">{{ goal.name }}</div>
                          <div v-if="goal.hint" class="psm-hint">{{ goal.hint }}</div>
                        </div>
                        <div>
                          <input
                            type="text"
                            class="psm-input psm-input--compact"
                            :placeholder="'не задано'"
                            v-model="goal.targetCpa"
                          />
                        </div>
                        <div class="flex justify-center">
                          <label class="psm-toggle psm-toggle--sm">
                            <input type="checkbox" v-model="goal.controlEnabled" class="sr-only" />
                            <span class="psm-toggle__track" :class="{ 'psm-toggle__track--on': goal.controlEnabled }">
                              <span class="psm-toggle__thumb" :class="{ 'psm-toggle__thumb--on': goal.controlEnabled }"></span>
                            </span>
                          </label>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <!-- ===== Block 5: Управление проектом ===== -->
          <section class="psm-card">
            <div class="psm-card__header">
              <h3 class="psm-card__title">Управление проектом</h3>
            </div>
            <div class="psm-card__body space-y-3">
              <!-- Pause/Resume -->
              <div class="psm-manage-row">
                <div class="min-w-0">
                  <div class="psm-manage-row__title">{{ form.status === 'paused' ? 'Возобновить проект' : 'Приостановить проект' }}</div>
                  <div class="psm-hint">Синхронизация и детектор останавливаются. Обратимо.</div>
                </div>
                <button
                  type="button"
                  class="psm-btn-outline"
                  @click="togglePause"
                >
                  {{ form.status === 'paused' ? 'Возобновить' : 'Приостановить' }}
                </button>
              </div>

              <!-- Delete -->
              <div class="psm-manage-row psm-manage-row--danger">
                <div class="min-w-0">
                  <div class="psm-manage-row__title psm-manage-row__title--danger">Удалить проект</div>
                  <div class="psm-hint">Необратимо. Потребуется подтверждение вводом названия проекта.</div>
                </div>
                <button type="button" class="psm-btn-danger" @click="showDeleteConfirm = true">Удалить</button>
              </div>
            </div>
          </section>
        </div>

        <!-- Footer -->
        <div class="psm-footer">
          <button type="button" class="psm-btn-primary" :disabled="saving || !form.name?.trim()" @click="save">
            {{ saving ? 'Сохранение...' : 'Сохранить' }}
          </button>
          <button type="button" class="psm-btn-secondary" :disabled="saving" @click="close">Отмена</button>
        </div>

        <!-- Delete confirmation modal -->
        <div v-if="showDeleteConfirm" class="psm-confirm-overlay" @click.self="showDeleteConfirm = false">
          <div class="psm-confirm-box">
            <h4 class="psm-confirm-title">Удалить проект?</h4>
            <p class="psm-hint mb-4">Это действие необратимо. Введите название проекта <strong>{{ form.name }}</strong> для подтверждения.</p>
            <input v-model="deleteConfirmText" type="text" class="psm-input mb-4" placeholder="Введите название проекта" />
            <div class="flex gap-3">
              <button
                type="button"
                class="psm-btn-danger"
                :disabled="deleteConfirmText.trim() !== form.name?.trim()"
                @click="deleteProject"
              >
                Удалить навсегда
              </button>
              <button type="button" class="psm-btn-secondary" @click="showDeleteConfirm = false; deleteConfirmText = ''">Отмена</button>
            </div>
          </div>
        </div>

        <!-- Channel delete confirmation -->
        <div v-if="channelToDelete" class="psm-confirm-overlay" @click.self="channelToDelete = null">
          <div class="psm-confirm-box">
            <h4 class="psm-confirm-title">Удалить интеграцию?</h4>
            <p class="psm-hint mb-4">Канал <strong>{{ channelToDelete.name }}</strong> будет отключён от проекта.</p>
            <div class="flex gap-3">
              <button type="button" class="psm-btn-outline-sm psm-btn-outline-sm--warn" @click="deleteChannel">Удалить</button>
              <button type="button" class="psm-btn-secondary" @click="channelToDelete = null">Отмена</button>
            </div>
          </div>
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
import { computed, reactive, ref, watch, onMounted, onUnmounted } from 'vue'
import api from '@/api/axios'
import { projectAvatarUrl, projectInitials } from '@/utils/projectAvatar'
import { useToaster } from '@/composables/useToaster'
import PlatformIcon from '@/components/ui/PlatformIcon.vue'
import ProjectAvatarUploadModal from './ProjectAvatarUploadModal.vue'

const props = defineProps({
  project: { type: Object, required: true },
})

const emit = defineEmits(['close', 'saved', 'deleted', 'add-channel', 'configure-channel'])

const toaster = useToaster()

const form = reactive({
  name: '',
  description: '',
  site_url: '',
  detector_enabled: false,
  status: 'active',
})

const saving = ref(false)
const error = ref('')
const avatarModalOpen = ref(false)
const updatedAvatarUrl = ref(null)
const detectorFieldsExpanded = ref(false)
const showDeleteConfirm = ref(false)
const deleteConfirmText = ref('')
const channelToDelete = ref(null)
const budgets = reactive({})
const containerRef = ref(null)

const goalRows = ref([])

const projectDisplayId = computed(() => props.project?.display_id || String(props.project?.id || '').substring(0, 8).toUpperCase())

const initials = computed(() => projectInitials({ name: form.name || props.project?.name }))

const currentAvatarUrl = computed(() => {
  if (updatedAvatarUrl.value !== null) return updatedAvatarUrl.value
  return projectAvatarUrl(props.project)
})

const avatarProjectData = computed(() => ({
  id: props.project?.id,
  name: form.name || props.project?.name,
  avatar_url: updatedAvatarUrl.value ?? props.project?.avatar_url,
}))

const platformName = (platform) => {
  const code = String(platform || '').toUpperCase()
  if (code.includes('YANDEX') || code.includes('DIRECT')) return 'Яндекс Директ'
  if (code.includes('VK')) return 'VK Реклама'
  return platform || 'Канал'
}

const channelStatusInfo = (integration) => {
  const syncStatus = String(integration.sync_status || '').toUpperCase()
  const lastSync = integration.last_sync_at

  if (syncStatus === 'SUCCESS') {
    const timeStr = lastSync ? new Date(lastSync).toLocaleString('ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : ''
    return { text: `активно · синхронизация ${timeStr}`, cls: 'psm-channel-dot--active' }
  }
  if (syncStatus === 'PENDING' || syncStatus === 'NEVER') {
    return { text: 'синхронизируется...', cls: 'psm-channel-dot--sync' }
  }
  if (syncStatus === 'FAILED') {
    return { text: 'ошибка синхронизации', cls: 'psm-channel-dot--error' }
  }
  return { text: 'неизвестно', cls: '' }
}

const projectChannels = computed(() => {
  const integrations = props.project?.integrations || []
  return integrations.map((intg) => {
    const status = channelStatusInfo(intg)
    return {
      id: intg.id,
      platform: intg.platform,
      name: intg.account_name || platformName(intg.platform),
      statusText: status.text,
      statusClass: status.cls,
    }
  })
})

const integrationState = computed(() => {
  const integrations = props.project?.integrations || []
  if (integrations.length === 0) return 'A'
  const allSyncing = integrations.every((i) => {
    const s = String(i.sync_status || '').toUpperCase()
    return s === 'PENDING' || s === 'NEVER'
  })
  if (allSyncing) return 'B'
  return 'C'
})

const currentPeriodLabel = computed(() => {
  const now = new Date()
  const start = `01.${String(now.getMonth() + 1).padStart(2, '0')}`;
  const end = new Date(now.getFullYear(), now.getMonth() + 1, 0)
  return `${start} — ${String(end.getDate()).padStart(2, '0')}.${String(end.getMonth() + 1).padStart(2, '0')}.${end.getFullYear()}`
})

watch(
  () => props.project?.id,
  () => {
    if (props.project) {
      form.name = props.project.name || ''
      form.description = props.project.description || ''
      form.site_url = props.project.site_url || ''
      form.detector_enabled = props.project.detector_enabled || false
      form.status = props.project.status || 'active'
      updatedAvatarUrl.value = null
      error.value = ''
      detectorFieldsExpanded.value = false
      deleteConfirmText.value = ''
      loadGoals()
    }
  },
  { immediate: true }
)

watch(() => form.detector_enabled, (val) => {
  if (val) detectorFieldsExpanded.value = false
})

async function loadGoals() {
  const integrations = props.project?.integrations || []
  const rows = []

  for (const intg of integrations) {
    const platform = String(intg.platform || '').toUpperCase()
    let goals = []
    try {
      const selectedGoals = intg.selected_goals ? JSON.parse(intg.selected_goals) : []
      if (selectedGoals.length) {
        goals = selectedGoals.map((g) => (typeof g === 'object' ? g : { id: g, name: `Цель ${g}` }))
      }
    } catch { /* ignore */ }

    for (const g of goals) {
      rows.push({
        id: `${intg.id}-${g.id || g}`,
        platform: intg.platform,
        name: g.name || g.goal_name || `Цель ${g.id || g}`,
        hint: '',
        targetCpa: '',
        controlEnabled: false,
        isSummary: false,
      })
    }

    if (platform.includes('YANDEX') && goals.length > 0) {
      rows.push({
        id: `${intg.id}-summary`,
        platform: intg.platform,
        name: 'Все конверсии — общий CPL',
        hint: 'сводный план по всем конверсионным целям Яндекса (суммирование корректно)',
        targetCpa: '',
        controlEnabled: false,
        isSummary: true,
      })
    }
  }

  goalRows.value = rows
}

async function copyProjectId() {
  const value = String(props.project?.display_id || props.project?.id || '')
  if (!value) return
  try {
    await navigator.clipboard.writeText(value)
    toaster.success('ID проекта скопирован')
  } catch {
    toaster.error('Не удалось скопировать ID')
  }
}

function handleAvatarSaved(updatedProject) {
  updatedAvatarUrl.value = projectAvatarUrl(updatedProject) || null
  emit('saved', updatedProject)
}

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
    toaster.success('Настройки сохранены')
    close()
  } catch (err) {
    error.value = err.response?.data?.detail || 'Не удалось сохранить изменения.'
    toaster.error(error.value)
  } finally {
    saving.value = false
  }
}

function togglePause() {
  form.status = form.status === 'paused' ? 'active' : 'paused'
  toaster.info(form.status === 'paused' ? 'Проект будет приостановлен при сохранении' : 'Проект будет возобновлён при сохранении')
}

function confirmDeleteChannel(ch) {
  channelToDelete.value = ch
}

async function deleteChannel() {
  if (!channelToDelete.value) return
  try {
    await api.delete(`integrations/${channelToDelete.value.id}`)
    toaster.success('Интеграция удалена')
    channelToDelete.value = null
    emit('saved', props.project)
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Не удалось удалить интеграцию')
  }
}

async function deleteProject() {
  if (!props.project?.id) return
  try {
    await api.delete(`clients/${props.project.id}`)
    toaster.success('Проект удалён')
    emit('deleted', props.project.id)
    close()
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Не удалось удалить проект')
  }
}

function close() {
  emit('close')
}

function onEscape(e) {
  if (e.key === 'Escape') {
    if (showDeleteConfirm.value) { showDeleteConfirm.value = false; return }
    if (channelToDelete.value) { channelToDelete.value = null; return }
    if (avatarModalOpen.value) return
    close()
  }
}

onMounted(() => document.addEventListener('keydown', onEscape))
onUnmounted(() => document.removeEventListener('keydown', onEscape))
</script>

<style scoped>
/* ===== Overlay & Container ===== */
.psm-overlay {
  position: fixed;
  inset: 0;
  z-index: 9000;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 2.0833rem 1.3889rem;
  background: rgba(0, 0, 0, 0.5);
  overflow-y: auto;
}

.psm-container {
  width: 100%;
  max-width: 52.0833rem;
  background: #f5f7f9;
  border-radius: 1.25rem;
  box-shadow: 0 1.6667rem 4.8611rem rgba(15, 23, 42, 0.22);
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 4.1667rem);
}

/* ===== Header ===== */
.psm-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.6667rem 2.0833rem 1.25rem;
  flex-shrink: 0;
}

.psm-title {
  font-size: 1.5278rem;
  font-weight: 700;
  color: #171717;
  line-height: 1.15;
}

.psm-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 50%;
  border: 0;
  background: rgba(0, 0, 0, 0.05);
  color: #696969;
  cursor: pointer;
  transition: background-color 0.2s, color 0.2s;
  flex-shrink: 0;
}
.psm-close:hover { background: #edf3ff; color: #2563eb; }

/* ===== Body (scrollable) ===== */
.psm-body {
  flex: 1;
  overflow-y: auto;
  padding: 0 2.0833rem 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1.0417rem;
}

/* ===== Card blocks ===== */
.psm-card {
  background: #fff;
  border-radius: 1.0417rem;
  border: 1px solid rgba(0, 0, 0, 0.06);
  overflow: hidden;
}

.psm-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1.25rem 1.6667rem 0;
}

.psm-card__title {
  font-size: 1.1111rem;
  font-weight: 600;
  color: #171717;
  line-height: 1.2;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.psm-card__body {
  padding: 1.25rem 1.6667rem 1.6667rem;
}

/* ===== ID badge ===== */
.psm-card__id {
  display: flex;
  align-items: center;
  gap: 0.4167rem;
}

.psm-card__id-text {
  font-size: 0.8333rem;
  color: rgba(105, 105, 105, 0.56);
  font-weight: 500;
}

.psm-card__id-copy {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.6667rem;
  height: 1.6667rem;
  border-radius: 0.3472rem;
  border: 0;
  background: transparent;
  color: rgba(105, 105, 105, 0.56);
  cursor: pointer;
  transition: color 0.2s, background 0.2s;
}
.psm-card__id-copy:hover { color: #2563eb; background: rgba(37, 99, 235, 0.08); }

/* ===== Avatar ===== */
.psm-avatar {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 4.8611rem;
  height: 4.8611rem;
  border-radius: 50%;
  background: #e8eef9;
  color: #2563eb;
  border: 0;
  cursor: pointer;
  overflow: hidden;
  flex-shrink: 0;
}

.psm-avatar__initials {
  font-size: 1.25rem;
  font-weight: 700;
  line-height: 1;
}

.psm-avatar__hover {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.25);
  color: #fff;
  opacity: 0;
  transition: opacity 0.2s;
  border-radius: 50%;
}
.psm-avatar:hover .psm-avatar__hover { opacity: 1; }

.psm-avatar__btn {
  font-size: 0.7639rem;
  font-weight: 500;
  color: #2563eb;
  background: transparent;
  border: 0;
  cursor: pointer;
  padding: 0;
  transition: color 0.2s;
}
.psm-avatar__btn:hover { color: #1d4ed8; }

/* ===== Form elements ===== */
.psm-label {
  display: block;
  margin-bottom: 0.3472rem;
  font-size: 0.8333rem;
  font-weight: 500;
  color: rgba(105, 105, 105, 0.72);
}

.psm-input {
  width: 100%;
  height: 3.0556rem;
  padding: 0 1.0417rem;
  font-size: 0.9722rem;
  color: #171717;
  background: #fff;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 0.8333rem;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.psm-input:focus {
  border-color: rgba(37, 99, 235, 0.4);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.08);
}
.psm-input::placeholder { color: rgba(0, 0, 0, 0.25); }

.psm-input--compact {
  height: 2.5rem;
  font-size: 0.9028rem;
  padding: 0 0.8333rem;
  border-radius: 0.6944rem;
}

.psm-textarea {
  height: auto;
  padding: 0.8333rem 1.0417rem;
  resize: vertical;
  min-height: 3.4722rem;
}

.psm-hint {
  font-size: 0.7639rem;
  color: rgba(105, 105, 105, 0.56);
  line-height: 1.4;
}

.psm-empty {
  padding: 1.6667rem;
  text-align: center;
  font-size: 0.9028rem;
  color: rgba(105, 105, 105, 0.56);
  background: #f8fafb;
  border-radius: 0.6944rem;
}

/* ===== Buttons ===== */
.psm-btn-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 3.0556rem;
  padding: 0 1.6667rem;
  font-size: 0.9722rem;
  font-weight: 500;
  color: #fff;
  background: #2563eb;
  border: 0;
  border-radius: 0.8333rem;
  cursor: pointer;
  transition: background 0.2s, transform 0.1s;
  white-space: nowrap;
}
.psm-btn-primary:hover { background: #1d4ed8; }
.psm-btn-primary:active { transform: scale(0.98); }
.psm-btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.psm-btn-secondary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 3.0556rem;
  padding: 0 1.6667rem;
  font-size: 0.9722rem;
  font-weight: 500;
  color: #696969;
  background: #fff;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 0.8333rem;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s;
  white-space: nowrap;
}
.psm-btn-secondary:hover { background: #f5f7f9; border-color: rgba(0, 0, 0, 0.15); }
.psm-btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }

.psm-btn-accent {
  display: inline-flex;
  align-items: center;
  gap: 0.4167rem;
  min-height: 2.5rem;
  padding: 0 1.0417rem;
  font-size: 0.9028rem;
  font-weight: 500;
  color: #fff;
  background: #2563eb;
  border: 0;
  border-radius: 0.6944rem;
  cursor: pointer;
  transition: background 0.2s;
  white-space: nowrap;
}
.psm-btn-accent:hover { background: #1d4ed8; }

.psm-btn-outline {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 2.5rem;
  padding: 0 1.0417rem;
  font-size: 0.9028rem;
  font-weight: 500;
  color: #696969;
  background: #fff;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 0.6944rem;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s;
  white-space: nowrap;
}
.psm-btn-outline:hover { background: #f5f7f9; }

.psm-btn-outline-sm {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 2.0833rem;
  padding: 0 0.8333rem;
  font-size: 0.8333rem;
  font-weight: 500;
  color: #696969;
  background: #fff;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 0.5556rem;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s, color 0.2s;
  white-space: nowrap;
}
.psm-btn-outline-sm:hover { background: #f5f7f9; }

.psm-btn-outline-sm--warn {
  color: #dc6b2f;
  border-color: rgba(220, 107, 47, 0.25);
}
.psm-btn-outline-sm--warn:hover { background: #fff7f0; border-color: rgba(220, 107, 47, 0.4); color: #c0501d; }

.psm-btn-danger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 2.5rem;
  padding: 0 1.0417rem;
  font-size: 0.9028rem;
  font-weight: 500;
  color: #fff;
  background: #dc2626;
  border: 0;
  border-radius: 0.6944rem;
  cursor: pointer;
  transition: background 0.2s;
  white-space: nowrap;
}
.psm-btn-danger:hover { background: #b91c1c; }
.psm-btn-danger:disabled { opacity: 0.4; cursor: not-allowed; }

/* ===== Toggle switch ===== */
.psm-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.5556rem;
  cursor: pointer;
  user-select: none;
}

.psm-toggle__track {
  position: relative;
  display: inline-flex;
  width: 2.6389rem;
  height: 1.5278rem;
  background: #d1d5db;
  border-radius: 6.9444rem;
  transition: background 0.2s;
  flex-shrink: 0;
}
.psm-toggle__track--on { background: #2563eb; }

.psm-toggle__thumb {
  position: absolute;
  top: 0.1736rem;
  left: 0.1736rem;
  width: 1.1806rem;
  height: 1.1806rem;
  background: #fff;
  border-radius: 50%;
  transition: transform 0.2s;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
}
.psm-toggle__thumb--on { transform: translateX(1.1111rem); }

.psm-toggle__label {
  font-size: 0.9028rem;
  font-weight: 500;
  color: #171717;
}

.psm-toggle--sm .psm-toggle__track {
  width: 2.0833rem;
  height: 1.1806rem;
}
.psm-toggle--sm .psm-toggle__thumb {
  top: 0.1389rem;
  left: 0.1389rem;
  width: 0.9028rem;
  height: 0.9028rem;
}
.psm-toggle--sm .psm-toggle__thumb--on { transform: translateX(0.8333rem); }

/* ===== Optional tag ===== */
.psm-optional-tag {
  display: inline-flex;
  align-items: center;
  padding: 0.1389rem 0.5556rem;
  font-size: 0.6944rem;
  font-weight: 500;
  color: rgba(105, 105, 105, 0.56);
  background: rgba(0, 0, 0, 0.04);
  border-radius: 6.9444rem;
  text-transform: lowercase;
}

/* ===== Channels list ===== */
.psm-channel-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.8333rem 1.0417rem;
  background: #f8fafb;
  border-radius: 0.6944rem;
}

.psm-channel-name {
  font-size: 0.9722rem;
  font-weight: 500;
  color: #171717;
  line-height: 1.2;
}

.psm-channel-status {
  display: flex;
  align-items: center;
  gap: 0.3472rem;
  font-size: 0.7639rem;
  color: rgba(105, 105, 105, 0.56);
  margin-top: 0.1389rem;
}

.psm-channel-dot {
  width: 0.4861rem;
  height: 0.4861rem;
  border-radius: 50%;
  background: #d1d5db;
  flex-shrink: 0;
}
.psm-channel-dot--active { background: #22c55e; }
.psm-channel-dot--sync { background: #f59e0b; }
.psm-channel-dot--error { background: #ef4444; }

/* ===== Detector stub ===== */
.psm-detector-stub {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.8333rem;
  padding: 2.0833rem 1.6667rem;
  text-align: center;
  color: rgba(105, 105, 105, 0.56);
  font-size: 0.9028rem;
}

.psm-detector-collapsed {
  display: flex;
  align-items: center;
  gap: 0.6944rem;
  padding: 0.8333rem 1.0417rem;
  background: #f8fafb;
  border-radius: 0.6944rem;
}

.psm-detector-collapsed__text {
  font-size: 0.9028rem;
  font-weight: 500;
  color: #171717;
}

.psm-detector-collapsed__hint {
  font-size: 0.8333rem;
  color: rgba(105, 105, 105, 0.45);
}

.psm-detector-collapsed__link {
  margin-left: auto;
  font-size: 0.8333rem;
  font-weight: 500;
  color: #2563eb;
  background: transparent;
  border: 0;
  cursor: pointer;
  padding: 0;
  transition: color 0.2s;
}
.psm-detector-collapsed__link:hover { color: #1d4ed8; }

/* ===== Budget cards ===== */
.psm-budget-card {
  flex: 1;
  min-width: 14.5833rem;
  padding: 1.0417rem;
  background: #f8fafb;
  border-radius: 0.8333rem;
  border: 1px solid rgba(0, 0, 0, 0.04);
}

/* ===== Goals table ===== */
.psm-goals-table {
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 0.6944rem;
  overflow: hidden;
}

.psm-goals-table__header {
  display: grid;
  grid-template-columns: 3.4722rem 1fr 9.7222rem 5.5556rem;
  gap: 0.6944rem;
  padding: 0.6944rem 1.0417rem;
  font-size: 0.7639rem;
  font-weight: 500;
  color: rgba(105, 105, 105, 0.56);
  background: #f8fafb;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.psm-goals-table__row {
  display: grid;
  grid-template-columns: 3.4722rem 1fr 9.7222rem 5.5556rem;
  gap: 0.6944rem;
  align-items: center;
  padding: 0.6944rem 1.0417rem;
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);
}
.psm-goals-table__row:last-child { border-bottom: 0; }

.psm-goals-table__row--summary {
  background: #fefce8;
}

.psm-goal-name {
  font-size: 0.9028rem;
  font-weight: 500;
  color: #171717;
}

/* ===== Subsections ===== */
.psm-subsection-title {
  font-size: 0.9722rem;
  font-weight: 600;
  color: #171717;
  margin-bottom: 0.3472rem;
}

/* ===== Manage rows ===== */
.psm-manage-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.6667rem;
  padding: 1.0417rem 1.25rem;
  background: #f8fafb;
  border-radius: 0.6944rem;
}

.psm-manage-row--danger {
  background: #fef2f2;
}

.psm-manage-row__title {
  font-size: 0.9722rem;
  font-weight: 500;
  color: #171717;
}
.psm-manage-row__title--danger { color: #dc2626; }

/* ===== Footer ===== */
.psm-footer {
  display: flex;
  gap: 0.8333rem;
  padding: 1.25rem 2.0833rem;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  flex-shrink: 0;
}

/* ===== Confirm overlay ===== */
.psm-confirm-overlay {
  position: fixed;
  inset: 0;
  z-index: 9500;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.4);
  padding: 1.3889rem;
}

.psm-confirm-box {
  width: 100%;
  max-width: 26.3889rem;
  background: #fff;
  border-radius: 1.0417rem;
  padding: 1.6667rem;
  box-shadow: 0 1.3889rem 3.4722rem rgba(15, 23, 42, 0.18);
}

.psm-confirm-title {
  font-size: 1.1111rem;
  font-weight: 600;
  color: #171717;
  margin-bottom: 0.6944rem;
}

/* ===== Skeleton loader ===== */
.psm-skeleton {
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: psm-shimmer 1.5s infinite;
  border-radius: 0.4167rem;
}

@keyframes psm-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* ===== Dark mode ===== */
:root.dark .psm-container,
.dark .psm-container {
  background: #1e2130;
}

:root.dark .psm-card,
.dark .psm-card {
  background: #2C2F3D;
  border-color: rgba(255, 255, 255, 0.08);
}

:root.dark .psm-title,
.dark .psm-title,
:root.dark .psm-card__title,
.dark .psm-card__title,
:root.dark .psm-channel-name,
.dark .psm-channel-name,
:root.dark .psm-goal-name,
.dark .psm-goal-name,
:root.dark .psm-manage-row__title,
.dark .psm-manage-row__title,
:root.dark .psm-detector-collapsed__text,
.dark .psm-detector-collapsed__text,
:root.dark .psm-subsection-title,
.dark .psm-subsection-title,
:root.dark .psm-confirm-title,
.dark .psm-confirm-title,
:root.dark .psm-toggle__label,
.dark .psm-toggle__label {
  color: #fff;
}

:root.dark .psm-input,
.dark .psm-input {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.12);
  color: #e5e7eb;
}

:root.dark .psm-channel-row,
.dark .psm-channel-row,
:root.dark .psm-manage-row,
.dark .psm-manage-row,
:root.dark .psm-budget-card,
.dark .psm-budget-card,
:root.dark .psm-detector-collapsed,
.dark .psm-detector-collapsed,
:root.dark .psm-goals-table__header,
.dark .psm-goals-table__header,
:root.dark .psm-empty,
.dark .psm-empty {
  background: rgba(255, 255, 255, 0.04);
}

:root.dark .psm-manage-row--danger,
.dark .psm-manage-row--danger {
  background: rgba(220, 38, 38, 0.08);
}

:root.dark .psm-goals-table,
.dark .psm-goals-table {
  border-color: rgba(255, 255, 255, 0.06);
}

:root.dark .psm-goals-table__row,
.dark .psm-goals-table__row {
  border-bottom-color: rgba(255, 255, 255, 0.04);
}

:root.dark .psm-goals-table__row--summary,
.dark .psm-goals-table__row--summary {
  background: rgba(250, 204, 21, 0.06);
}

:root.dark .psm-close,
.dark .psm-close {
  background: rgba(255, 255, 255, 0.08);
  color: #9ca3af;
}
:root.dark .psm-close:hover,
.dark .psm-close:hover { background: rgba(37, 99, 235, 0.15); color: #60a5fa; }

:root.dark .psm-btn-secondary,
.dark .psm-btn-secondary {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.1);
  color: #9ca3af;
}

:root.dark .psm-btn-outline,
.dark .psm-btn-outline,
:root.dark .psm-btn-outline-sm,
.dark .psm-btn-outline-sm {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.1);
  color: #9ca3af;
}

:root.dark .psm-footer,
.dark .psm-footer {
  border-top-color: rgba(255, 255, 255, 0.06);
}

:root.dark .psm-confirm-box,
.dark .psm-confirm-box {
  background: #2C2F3D;
}
</style>
