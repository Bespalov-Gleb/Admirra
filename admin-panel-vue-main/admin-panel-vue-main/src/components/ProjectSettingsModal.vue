<template>
  <Teleport to="body">
    <div class="psm-overlay" @mousedown.self="close">
      <div class="psm-container" ref="containerRef">
        <!-- Header -->
        <div class="psm-header">
          <div>
            <h2 class="psm-title">Настройки проекта</h2>
            <p class="psm-subtitle">{{ form.name || 'Без названия' }}</p>
          </div>
          <button type="button" class="psm-close" aria-label="Закрыть" @click="close">
            <svg class="w-4 h-4" viewBox="0 0 16 16" fill="none">
              <path d="M3.5 3.5 12.5 12.5M12.5 3.5 3.5 12.5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
            </svg>
          </button>
        </div>

        <div class="psm-body" ref="bodyRef">
          <!-- Error banner -->
          <div v-if="error" class="psm-error">{{ error }}</div>

          <!-- ===== Block 1: Основное ===== -->
          <section class="psm-card">
            <div class="psm-card__header">
              <h3 class="psm-card__title">Основное</h3>
              <div class="psm-card__id">
                <span class="psm-card__id-text">ID {{ projectDisplayId }}</span>
                <button type="button" class="psm-card__id-copy" :class="{ 'psm-card__id-copy--done': idCopied }" @click="copyProjectId" title="Копировать ID">
                  <svg v-if="!idCopied" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                  </svg>
                  <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M20 6 9 17l-5-5"/>
                  </svg>
                </button>
              </div>
            </div>

            <div class="psm-card__body">
              <div class="psm-basic-grid">
                <div class="psm-basic-grid__avatar">
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
                  <span class="psm-hint text-center">По умолчанию — инициалы</span>
                </div>

                <div class="psm-basic-grid__fields">
                  <div>
                    <label class="psm-label">Название проекта <span class="psm-label--req">*</span></label>
                    <input v-model="form.name" type="text" class="psm-input" placeholder="Название проекта" />
                  </div>
                  <div>
                    <label class="psm-label">Описание проекта</label>
                    <textarea v-model="form.description" rows="2" class="psm-input psm-textarea" placeholder="Краткое описание для команды агентства..." maxlength="500"></textarea>
                    <div class="psm-char-count">{{ (form.description || '').length }} / 500</div>
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
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="rgba(105,105,105,0.3)" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round" class="mb-2">
                  <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
                </svg>
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
                <p class="psm-hint mt-1">«Настроить» — состав счётчиков и целей (визард). «Удалить» — отключить канал, с подтверждением.</p>
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
              <input v-model="form.site_url" type="url" class="psm-input" placeholder="https://example.com" @blur="validateUrl" />
              <p v-if="urlError" class="psm-field-error mt-1">{{ urlError }}</p>
            </div>
          </section>

          <!-- ===== Block 4: Google Sheets ===== -->
          <section class="psm-card">
            <div class="psm-card__header">
              <h3 class="psm-card__title">
                Google Sheets
                <span class="psm-optional-tag">отчёты</span>
              </h3>
            </div>
            <div class="psm-card__body">
              <p class="psm-hint mb-3">Таблица проекта для выгрузки сырых данных, недельных и месячных отчётов, а также целей Метрики.</p>

              <div class="psm-sheets-card">
                <div class="psm-sheets-card__icon">
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
                    <path d="M7 2h7l5 5v15H7a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2Z" fill="#1e8e3e"/>
                    <path d="M14 2v5h5" fill="#9ad6aa"/>
                    <path d="M8.5 10h7M8.5 13h7M8.5 16h7M10.5 10v6M13.5 10v6" stroke="#fff" stroke-width="1.1" stroke-linecap="round"/>
                  </svg>
                </div>
                <div class="psm-sheets-card__content">
                  <label class="psm-label">Ссылка или ID Google таблицы</label>
                  <input
                    v-model="form.spreadsheet_id"
                    type="text"
                    class="psm-input"
                    placeholder="https://docs.google.com/spreadsheets/d/..."
                  />
                  <p class="psm-hint mt-2">
                    Листы создаются автоматически: Raw Data, Weekly Reports, Monthly Report, Goals.
                  </p>
                </div>
              </div>

              <div class="psm-sheets-instruction">
                <span class="psm-sheets-instruction__label">Доступ</span>
                <span v-if="sheetsServiceEmail" class="psm-code-pill">{{ sheetsServiceEmail }}</span>
                <span v-else class="psm-hint">service account не настроен на сервере</span>
                <span class="psm-hint">Расшарьте таблицу на этот email с правом «Редактор».</span>
              </div>

              <div
                class="psm-sheets-status"
                :class="{ 'psm-sheets-status--ok': sheetsConnected, 'psm-sheets-status--warn': !sheetsConnected }"
              >
                <span class="psm-channel-dot" :class="sheetsConnected ? 'psm-channel-dot--active' : 'psm-channel-dot--sync'"></span>
                {{ sheetsStatusText }}
              </div>

              <div class="psm-sheets-actions">
                <button type="button" class="psm-btn-accent" :disabled="sheetsBusy" @click="connectGoogleSheets">
                  {{ sheetsChecking ? 'Проверяем...' : sheetsConnected ? 'Проверить доступ' : 'Проверить и подключить' }}
                </button>
                <button type="button" class="psm-btn-outline" :disabled="sheetsBusy || !sheetsConnected" @click="exportGoogleSheetsNow">
                  {{ sheetsExporting ? 'Выгружаем...' : 'Выгрузить сейчас' }}
                </button>
                <button type="button" class="psm-btn-outline psm-btn-outline--warn" :disabled="sheetsBusy || !sheetsConnected" @click="disconnectGoogleSheets">
                  {{ sheetsDisconnecting ? 'Отключаем...' : 'Отключить' }}
                </button>
              </div>
            </div>
          </section>

          <!-- ===== Block 4: Детектор и цели ===== -->
          <section class="psm-card">
            <div class="psm-card__header">
              <h3 class="psm-card__title">
                Детектор и цели
                <span class="psm-optional-tag">необязательно</span>
              </h3>
              <button
                type="button"
                class="psm-toggle"
                role="switch"
                :aria-checked="form.detector_enabled"
                @click.stop="handleDetectorToggle"
              >
                <span class="psm-toggle__track" :class="{ 'psm-toggle__track--on': form.detector_enabled }">
                  <span class="psm-toggle__thumb" :class="{ 'psm-toggle__thumb--on': form.detector_enabled }"></span>
                </span>
                <span class="psm-toggle__label">Детектор аномалий</span>
              </button>
            </div>

            <div class="psm-card__body">
              <p class="psm-hint mb-4">Детектор по истории работает и без заполнения — поля ниже добавляют план-факт.</p>

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
                  <button type="button" class="psm-detector-collapsed__link" @click="detectorFieldsExpanded = true">
                    Развернуть
                    <svg width="10" height="10" viewBox="0 0 12 12" fill="none"><path d="M3 4.5l3 3 3-3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
                  </button>
                </div>

                <!-- Expanded fields -->
                <div v-show="form.detector_enabled || detectorFieldsExpanded">
                  <div v-if="!form.detector_enabled" class="psm-detector-expanded-toolbar">
                    <div>
                      <div class="psm-detector-expanded-toolbar__title">Бюджеты и цели раскрыты</div>
                      <div class="psm-detector-expanded-toolbar__hint">Детектор выключен, но плановые значения можно редактировать.</div>
                    </div>
                    <button type="button" class="psm-detector-collapsed__link" @click="detectorFieldsExpanded = false">
                      Свернуть
                      <svg width="10" height="10" viewBox="0 0 12 12" fill="none"><path d="M3 7.5l3-3 3 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
                    </button>
                  </div>

                  <div class="psm-period-row">
                    <div>
                      <label class="psm-label">Период с</label>
                      <input v-model="form.period_start" type="date" class="psm-input psm-input--compact" />
                    </div>
                    <div>
                      <label class="psm-label">Период по</label>
                      <input v-model="form.period_end" type="date" class="psm-input psm-input--compact" />
                    </div>
                  </div>
                  <p v-if="periodError" class="psm-field-error mb-4">{{ periodError }}</p>

                  <!-- Budgets per channel -->
                  <div class="mb-6">
                    <h4 class="psm-subsection-title">Бюджет на период — по каналам</h4>
                    <p class="psm-hint mb-3">Версионный: задаётся на период с датами. Смена бюджета — новый период, не аномалия.</p>

                    <div class="psm-budget-grid">
                      <div v-for="ch in projectChannels" :key="'budget-' + ch.id" class="psm-budget-card">
                        <div class="flex items-center gap-2 mb-2">
                          <PlatformIcon :platform="ch.platform" size="sm" />
                          <span class="psm-budget-card__name">{{ ch.name }}</span>
                        </div>
                        <div class="psm-input-with-suffix">
                          <input type="text" class="psm-input psm-input--compact psm-input--has-suffix" placeholder="0" v-model="budgets[ch.id]" @input="formatBudgetInput(ch.id)" />
                          <span class="psm-input-suffix">₽</span>
                        </div>
                        <div class="psm-hint mt-1.5">период: {{ currentPeriodLabel }}</div>
                      </div>
                    </div>
                  </div>

                  <!-- Target CPA table -->
                  <div>
                    <h4 class="psm-subsection-title">Целевая стоимость действия (CPA)</h4>
                    <p class="psm-hint mb-3">Заполняйте только цели с KPI от клиента. Контроль включается тумблером по каждой строке.</p>

                    <div v-if="goalRows.length === 0" class="psm-empty">
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="rgba(105,105,105,0.3)" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round" class="mb-2">
                        <circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/>
                      </svg>
                      Цели не найдены. Подключите счётчик Метрики или настройте цели ВК.
                    </div>
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
                          <div v-if="goal.goalId && goal.goalId !== '__summary__'" class="psm-hint" style="font-size:0.7639rem;color:rgba(105,105,105,0.4)">ID: {{ goal.goalId }}</div>
                          <div v-else-if="goal.hint" class="psm-hint">{{ goal.hint }}</div>
                        </div>
                        <div>
                          <div class="psm-input-with-suffix">
                            <input
                              type="text"
                              class="psm-input psm-input--compact psm-input--has-suffix"
                              placeholder="не задано"
                              v-model="goal.targetCpa"
                            />
                            <span class="psm-input-suffix">₽</span>
                          </div>
                        </div>
                        <div class="flex justify-center">
                          <label class="psm-toggle psm-toggle--sm">
                            <input type="checkbox" v-model="goal.controlEnabled" class="sr-only" :disabled="!goal.targetCpa" />
                            <span class="psm-toggle__track" :class="{ 'psm-toggle__track--on': goal.controlEnabled && goal.targetCpa, 'psm-toggle__track--disabled': !goal.targetCpa }">
                              <span class="psm-toggle__thumb" :class="{ 'psm-toggle__thumb--on': goal.controlEnabled && goal.targetCpa }"></span>
                            </span>
                          </label>
                        </div>
                      </div>
                    </div>
                    <p v-if="hasVkChannels" class="psm-hint mt-2">ВК: типы кампаний разнородны — сводной строки «общий CPL» нет, только по каждой цели.</p>
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
              <div class="psm-manage-row" :class="{ 'psm-manage-row--paused': form.status === 'paused' }">
                <div class="min-w-0">
                  <div class="psm-manage-row__title">{{ form.status === 'paused' ? 'Возобновить проект' : 'Приостановить проект' }}</div>
                  <div class="psm-hint">{{ form.status === 'paused' ? 'Проект на паузе. Синхронизация и детектор остановлены.' : 'Синхронизация и детектор останавливаются. Обратимо.' }}</div>
                </div>
                <button
                  type="button"
                  :class="form.status === 'paused' ? 'psm-btn-accent' : 'psm-btn-outline'"
                  @click="requestTogglePause"
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
          <button type="button" class="psm-btn-primary" :disabled="saving || !canSave" @click="save">
            <svg v-if="saving" class="psm-spinner" width="16" height="16" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="2" stroke-dasharray="28" stroke-dashoffset="8" stroke-linecap="round"/></svg>
            {{ saving ? 'Сохранение...' : 'Сохранить изменения' }}
          </button>
          <button type="button" class="psm-btn-secondary" :disabled="saving" @click="close">Отмена</button>
          <div v-if="hasUnsavedChanges" class="psm-unsaved-dot" title="Есть несохранённые изменения"></div>
        </div>
      </div>
    </div>

    <!-- Pause/resume confirmation -->
    <div v-if="showPauseConfirm" class="psm-confirm-overlay" @mousedown.self="showPauseConfirm = false">
      <div class="psm-confirm-box">
        <h4 class="psm-confirm-title">{{ pauseConfirmTitle }}</h4>
        <p class="psm-hint mb-4">{{ pauseConfirmText }}</p>
        <div class="flex gap-3">
          <button type="button" :class="pauseTargetStatus === 'active' ? 'psm-btn-accent' : 'psm-btn-outline'" @click="confirmTogglePause">
            {{ pauseTargetStatus === 'active' ? 'Возобновить' : 'Приостановить' }}
          </button>
          <button type="button" class="psm-btn-secondary" @click="showPauseConfirm = false">Отмена</button>
        </div>
      </div>
    </div>

    <!-- Delete confirmation modal -->
    <div v-if="showDeleteConfirm" class="psm-confirm-overlay" @mousedown.self="showDeleteConfirm = false">
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
    <div v-if="channelToDelete" class="psm-confirm-overlay" @mousedown.self="channelToDelete = null">
      <div class="psm-confirm-box">
        <h4 class="psm-confirm-title">Удалить интеграцию?</h4>
        <p class="psm-hint mb-4">Канал <strong>{{ channelToDelete.name }}</strong> будет отключён от проекта.</p>
        <div class="flex gap-3">
          <button type="button" class="psm-btn-danger" @click="deleteChannel">Удалить</button>
          <button type="button" class="psm-btn-secondary" @click="channelToDelete = null">Отмена</button>
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

const emit = defineEmits(['close', 'saved', 'deleted', 'add-channel', 'configure-channel', 'avatar-saved'])

const toaster = useToaster()

const form = reactive({
  name: '',
  description: '',
  site_url: '',
  spreadsheet_id: '',
  detector_enabled: false,
  status: 'active',
  period_start: '',
  period_end: '',
})

const saving = ref(false)
const error = ref('')
const urlError = ref('')
const bodyRef = ref(null)
const avatarModalOpen = ref(false)
const updatedAvatarUrl = ref(null)
const detectorFieldsExpanded = ref(false)
const showPauseConfirm = ref(false)
const pauseTargetStatus = ref('')
const showDeleteConfirm = ref(false)
const deleteConfirmText = ref('')
const channelToDelete = ref(null)
const channelDeleting = ref(false)
const budgets = reactive({})
const containerRef = ref(null)
const idCopied = ref(false)
const initialFormSnapshot = ref('')
const sheetsStatus = ref(null)
const sheetsChecking = ref(false)
const sheetsExporting = ref(false)
const sheetsDisconnecting = ref(false)

const goalRows = ref([])
const isInitializing = ref(false)

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

const periodError = computed(() => {
  if (!form.period_start || !form.period_end) return 'Укажите период для бюджетов и целей'
  if (form.period_end < form.period_start) return 'Дата окончания периода не может быть раньше даты начала'
  return ''
})

const canSave = computed(() => {
  return form.name?.trim() && !urlError.value && !periodError.value
})

const hasUnsavedChanges = computed(() => {
  return JSON.stringify({
    name: form.name,
    description: form.description,
    site_url: form.site_url,
    detector_enabled: form.detector_enabled,
    status: form.status,
  }) !== initialFormSnapshot.value
})

const sheetsBusy = computed(() => sheetsChecking.value || sheetsExporting.value || sheetsDisconnecting.value)

const sheetsConnected = computed(() => Boolean(
  sheetsStatus.value?.connected &&
  sheetsStatus.value?.spreadsheet_id &&
  form.spreadsheet_id?.trim() === sheetsStatus.value.spreadsheet_id
))

const sheetsServiceEmail = computed(() => sheetsStatus.value?.service_account_email || '')

const sheetsStatusText = computed(() => {
  if (form.spreadsheet_id?.trim() && form.spreadsheet_id.trim() !== sheetsStatus.value?.spreadsheet_id) {
    return 'Нажмите «Проверить и подключить», чтобы сохранить новую таблицу'
  }
  if (sheetsStatus.value?.message) return sheetsStatus.value.message
  if (sheetsConnected.value) {
    return sheetsStatus.value?.spreadsheet_title
      ? `Подключена таблица: ${sheetsStatus.value.spreadsheet_title}`
      : 'Google таблица подключена'
  }
  return 'Google таблица не подключена'
})

const hasVkChannels = computed(() => {
  return projectChannels.value.some((ch) => String(ch.platform || '').toUpperCase().includes('VK'))
})

const pauseConfirmTitle = computed(() => (
  pauseTargetStatus.value === 'active' ? 'Возобновить проект?' : 'Приостановить проект?'
))

const pauseConfirmText = computed(() => (
  pauseTargetStatus.value === 'active'
    ? 'Проект снова станет активным и будет занимать слот тарифа. Если лимит заполнен, сервер не даст сохранить возобновление.'
    : 'Проект освободит слот тарифа. Интеграции, история, бюджеты и цели сохранятся, но синхронизация и детектор будут остановлены после сохранения.'
))

const platformName = (platform) => {
  const code = String(platform || '').toUpperCase()
  if (code.includes('YANDEX') || code.includes('DIRECT')) return 'Яндекс Директ'
  if (code.includes('VK')) return 'VK Реклама'
  return platform || 'Канал'
}

const samePlatform = (a, b) => String(a || '').toUpperCase() === String(b || '').toUpperCase()

const toDateInput = (date) => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const defaultPeriod = () => {
  const now = new Date()
  const start = new Date(now.getFullYear(), now.getMonth(), 1)
  const end = new Date(now.getFullYear(), now.getMonth() + 1, 0)
  return { start: toDateInput(start), end: toDateInput(end) }
}

const samePeriod = (row) => row?.period_start === form.period_start && row?.period_end === form.period_end

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
  const format = (value) => {
    if (!value) return ''
    const [year, month, day] = value.split('-')
    return `${day}.${month}.${year}`
  }
  return `${format(form.period_start)} — ${format(form.period_end)}`
})

function snapshotForm() {
  initialFormSnapshot.value = JSON.stringify({
    name: form.name,
    description: form.description,
    site_url: form.site_url,
    detector_enabled: form.detector_enabled,
    status: form.status,
  })
}

watch(
  () => props.project?.id,
  async () => {
    if (props.project) {
      form.name = props.project.name || ''
      form.description = props.project.description || ''
      form.site_url = props.project.site_url || ''
      form.spreadsheet_id = props.project.spreadsheet_id || ''
      form.detector_enabled = props.project.detector_enabled || false
      form.status = props.project.status || 'active'
      updatedAvatarUrl.value = null
      error.value = ''
      urlError.value = ''
      detectorFieldsExpanded.value = false
      showPauseConfirm.value = false
      pauseTargetStatus.value = ''
      deleteConfirmText.value = ''
      sheetsStatus.value = null
      isInitializing.value = true
      // Период берём из последних сохранённых данных детектора (если есть),
      // иначе — текущий месяц. Иначе при повторном заходе колонки пустые,
      // т.к. defaultPeriod() не совпадал с периодом сохранённых бюджетов/CPA.
      await resolveActivePeriod()
      await loadGoals()
      await loadBudgets()
      isInitializing.value = false
      loadGoogleSheetsStatus()
      snapshotForm()
    }
  },
  { immediate: true }
)

watch(() => form.detector_enabled, (val) => {
  if (val) detectorFieldsExpanded.value = false
})

function handleDetectorToggle() {
  form.detector_enabled = !form.detector_enabled
}

watch(
  () => [form.period_start, form.period_end],
  () => {
    if (!props.project?.id || periodError.value || isInitializing.value) return
    loadGoals()
    loadBudgets()
  }
)

async function loadGoals() {
  const integrations = props.project?.integrations || []
  const rows = []

  const goalNameCache = {}
  await Promise.all(integrations.map(async (intg) => {
    try {
      const { data } = await api.get(`integrations/${intg.id}/goal-names`)
      if (data && typeof data === 'object') {
        for (const [gid, gname] of Object.entries(data)) {
          goalNameCache[`${intg.id}-${String(gid)}`] = gname
        }
      }
    } catch { /* ignore — will fall back to ID */ }
  }))

  for (const intg of integrations) {
    const platform = String(intg.platform || '').toUpperCase()
    const goals = normalizeSelectedGoals(intg.selected_goals)

    for (const g of goals) {
      const gid = String(g.id || g)
      rows.push({
        id: `${intg.id}-${gid}`,
        integrationId: intg.id,
        goalId: gid,
        platform: intg.platform,
        name: g.name || g.goal_name || goalNameCache[`${intg.id}-${gid}`] || `Цель ${gid}`,
        hint: '',
        targetCpa: '',
        controlEnabled: false,
        isSummary: false,
      })
    }

    if (platform.includes('YANDEX') && goals.length > 0) {
      rows.push({
        id: `${intg.id}-summary`,
        integrationId: intg.id,
        goalId: '__summary__',
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

  // Load saved CPA values from backend when API is ready
  try {
    const { data } = await api.get(`clients/${props.project.id}/target-cpa`)
    if (Array.isArray(data)) {
      for (const saved of data) {
        const row = rows.find((r) => (
          samePeriod(saved) &&
          samePlatform(r.platform, saved.channel) &&
          Boolean(r.isSummary) === Boolean(saved.is_summary) &&
          (r.isSummary || String(r.goalId) === String(saved.goal_id))
        ))
        if (row) {
          row.targetCpa = saved.target_cpa != null ? String(saved.target_cpa) : ''
          row.controlEnabled = saved.control_enabled || false
        }
      }
    }
  } catch { /* API not ready yet — use empty defaults */ }
}

async function loadBudgets() {
  Object.keys(budgets).forEach((key) => { delete budgets[key] })
  try {
    const { data } = await api.get(`clients/${props.project.id}/budgets`)
    if (Array.isArray(data)) {
      for (const b of data) {
        const ch = projectChannels.value.find((c) => samePlatform(c.platform, b.channel))
        if (ch && samePeriod(b)) budgets[ch.id] = b.amount != null ? String(b.amount) : ''
      }
    }
  } catch { /* API not ready yet */ }
}

// Определяет рабочий период детектора при открытии: берём период последних
// сохранённых бюджетов/целевых CPA, чтобы текущие данные сразу были видны.
// Если ничего не сохранено — текущий месяц.
async function resolveActivePeriod() {
  let latest = null
  try {
    const [budgetsRes, cpaRes] = await Promise.all([
      api.get(`clients/${props.project.id}/budgets`).catch(() => ({ data: [] })),
      api.get(`clients/${props.project.id}/target-cpa`).catch(() => ({ data: [] })),
    ])
    const records = [
      ...(Array.isArray(budgetsRes.data) ? budgetsRes.data : []),
      ...(Array.isArray(cpaRes.data) ? cpaRes.data : []),
    ].filter((r) => r && r.period_start && r.period_end)
    for (const r of records) {
      if (!latest || String(r.period_start) > String(latest.period_start)) latest = r
    }
  } catch { /* fall back to default */ }

  if (latest) {
    form.period_start = latest.period_start
    form.period_end = latest.period_end
  } else {
    const period = defaultPeriod()
    form.period_start = period.start
    form.period_end = period.end
  }
}

async function loadGoogleSheetsStatus() {
  if (!props.project?.id) return
  try {
    const { data } = await api.get(`clients/${props.project.id}/google-sheets/status`)
    sheetsStatus.value = data
    if (data?.spreadsheet_id) {
      form.spreadsheet_id = data.spreadsheet_id
      snapshotForm()
    }
  } catch {
    sheetsStatus.value = {
      connected: false,
      configured: false,
      message: 'Не удалось получить статус Google Sheets',
    }
  }
}

async function connectGoogleSheets() {
  const value = form.spreadsheet_id?.trim()
  if (!value) {
    toaster.warning('Вставьте ссылку или ID Google таблицы')
    return
  }
  sheetsChecking.value = true
  try {
    const { data } = await api.put(`clients/${props.project.id}/google-sheets`, { spreadsheet_id: value })
    sheetsStatus.value = data
    form.spreadsheet_id = data.spreadsheet_id || value
    snapshotForm()
    emit('saved', { ...props.project, spreadsheet_id: form.spreadsheet_id })
    toaster.success('Google таблица подключена')
  } catch (err) {
    const message = err.response?.data?.detail || 'Не удалось подключить Google таблицу'
    sheetsStatus.value = { ...(sheetsStatus.value || {}), connected: false, message }
    toaster.error(message)
  } finally {
    sheetsChecking.value = false
  }
}

async function exportGoogleSheetsNow() {
  if (!sheetsConnected.value) return
  sheetsExporting.value = true
  try {
    const { data } = await api.post(`clients/${props.project.id}/google-sheets/export`)
    sheetsStatus.value = data
    toaster.success('Данные выгружены в Google Sheets')
  } catch (err) {
    const message = err.response?.data?.detail || 'Не удалось выгрузить данные'
    sheetsStatus.value = { ...(sheetsStatus.value || {}), message }
    toaster.error(message)
  } finally {
    sheetsExporting.value = false
  }
}

async function disconnectGoogleSheets() {
  if (!sheetsConnected.value) return
  sheetsDisconnecting.value = true
  try {
    const { data } = await api.delete(`clients/${props.project.id}/google-sheets`)
    sheetsStatus.value = data
    form.spreadsheet_id = ''
    snapshotForm()
    emit('saved', { ...props.project, spreadsheet_id: null })
    toaster.success('Google таблица отключена')
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Не удалось отключить Google таблицу')
  } finally {
    sheetsDisconnecting.value = false
  }
}

function formatBudgetInput(chId) {
  const raw = String(budgets[chId] || '').replace(/[^\d]/g, '')
  budgets[chId] = raw ? Number(raw).toLocaleString('ru-RU') : ''
}

function normalizeSelectedGoals(value) {
  let selectedGoals = []
  if (Array.isArray(value)) {
    selectedGoals = value
  } else if (typeof value === 'string' && value.trim()) {
    try {
      const parsed = JSON.parse(value)
      selectedGoals = Array.isArray(parsed) ? parsed : []
    } catch {
      selectedGoals = []
    }
  }
  return selectedGoals.map((g) => (typeof g === 'object' ? g : { id: g, name: null }))
}

function validateUrl() {
  const url = (form.site_url || '').trim()
  if (!url) { urlError.value = ''; return }
  try {
    new URL(url.startsWith('http') ? url : `https://${url}`)
    urlError.value = ''
  } catch {
    urlError.value = 'Некорректный формат URL'
  }
}

async function copyProjectId() {
  const value = String(props.project?.display_id || props.project?.id || '')
  if (!value) return
  try {
    await navigator.clipboard.writeText(value)
    idCopied.value = true
    setTimeout(() => { idCopied.value = false }, 2000)
  } catch {
    toaster.error('Не удалось скопировать ID')
  }
}

function handleAvatarSaved(updatedProject) {
  updatedAvatarUrl.value = projectAvatarUrl(updatedProject) || null
  emit('avatar-saved', updatedProject)
}

async function save() {
  if (!props.project?.id || !canSave.value) return
  saving.value = true
  error.value = ''

  try {
    // 1. Save basic project fields
    const payload = {
      name: form.name.trim(),
      description: form.description.trim() || null,
      site_url: form.site_url.trim() || null,
      detector_enabled: form.detector_enabled,
      status: form.status,
    }

    const { data } = await api.put(`clients/${props.project.id}`, payload)

    // 2. Save budgets
    const budgetPayload = projectChannels.value
      .map((ch) => ({
        integration_id: ch.id,
        amount: Number(String(budgets[ch.id]).replace(/\s/g, '').replace(/,/g, '.')) || 0,
        period_start: form.period_start,
        period_end: form.period_end,
      }))

    if (projectChannels.value.length) {
      await api.put(`clients/${props.project.id}/budgets`, budgetPayload)
    }

    // 3. Save target CPAs
    const cpaPayload = goalRows.value
      .map((g) => ({
        integration_id: g.integrationId,
        goal_id: g.goalId,
        goal_name: g.name,
        target_cpa: g.targetCpa ? Number(String(g.targetCpa).replace(/\s/g, '').replace(/,/g, '.')) : null,
        control_enabled: Boolean(g.controlEnabled && g.targetCpa),
        is_summary: g.isSummary,
        period_start: form.period_start,
        period_end: form.period_end,
      }))

    if (goalRows.value.length) {
      await api.put(`clients/${props.project.id}/target-cpa`, cpaPayload)
    }

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

function requestTogglePause() {
  pauseTargetStatus.value = form.status === 'paused' ? 'active' : 'paused'
  showPauseConfirm.value = true
}

function confirmTogglePause() {
  if (!pauseTargetStatus.value) return
  form.status = pauseTargetStatus.value
  showPauseConfirm.value = false
  pauseTargetStatus.value = ''
}

function confirmDeleteChannel(ch) {
  channelToDelete.value = ch
}

async function deleteChannel() {
  if (!channelToDelete.value || channelDeleting.value) return
  channelDeleting.value = true
  try {
    await api.delete(`integrations/${channelToDelete.value.id}`)
    const { data } = await api.get(`clients/${props.project.id}`)
    toaster.success('Интеграция удалена')
    channelToDelete.value = null
    emit('saved', data)
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Не удалось удалить интеграцию')
  } finally {
    channelDeleting.value = false
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
    if (showPauseConfirm.value) { showPauseConfirm.value = false; return }
    if (showDeleteConfirm.value) { showDeleteConfirm.value = false; return }
    if (channelToDelete.value) { channelToDelete.value = null; return }
    if (avatarModalOpen.value) return
    close()
  }
}

let savedOverflow = ''

onMounted(() => {
  document.addEventListener('keydown', onEscape)
  savedOverflow = document.documentElement.style.overflow
  document.documentElement.style.overflow = 'hidden'
  document.body.style.overflow = 'hidden'
})

onUnmounted(() => {
  document.removeEventListener('keydown', onEscape)
  document.documentElement.style.overflow = savedOverflow
  document.body.style.overflow = ''
})
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
  overflow: hidden;
  overscroll-behavior: none;
}

.psm-container {
  width: 100%;
  max-width: 52.0833rem;
  height: calc(100vh - 4.1666rem);
  height: calc(100dvh - 4.1666rem);
  max-height: calc(100vh - 4.1666rem);
  max-height: calc(100dvh - 4.1666rem);
  background: #f5f7f9;
  border-radius: 1.25rem;
  box-shadow: 0 1.6667rem 4.8611rem rgba(15, 23, 42, 0.22);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  min-width: 0;
  overflow: hidden;
  overscroll-behavior: contain;
}

/* ===== Header ===== */
.psm-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.6667rem 2.0833rem 1.25rem;
  flex-shrink: 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.psm-title {
  font-size: 1.5278rem;
  font-weight: 700;
  color: #171717;
  line-height: 1.15;
}

.psm-subtitle {
  font-size: 0.8333rem;
  color: rgba(105, 105, 105, 0.56);
  margin-top: 0.2083rem;
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

/* ===== Body ===== */
.psm-body {
  padding: 1.25rem 2.0833rem 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1.0417rem;
  flex: 1 1 auto;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
  overflow-anchor: none;
}

/* ===== Error banner ===== */
.psm-error {
  padding: 0.8333rem 1.0417rem;
  background: #fef2f2;
  border: 1px solid rgba(220, 38, 38, 0.15);
  border-radius: 0.6944rem;
  color: #dc2626;
  font-size: 0.9028rem;
}

/* ===== Card blocks ===== */
.psm-card {
  background: #fff;
  border-radius: 1.0417rem;
  border: 1px solid rgba(0, 0, 0, 0.06);
  flex: 0 0 auto;
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
.psm-card__id-copy--done { color: #22c55e !important; }

/* ===== Avatar & basic grid ===== */
.psm-basic-grid {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 1.6667rem;
}

.psm-basic-grid__avatar {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.4167rem;
}

.psm-basic-grid__fields {
  display: flex;
  flex-direction: column;
  gap: 1.0417rem;
}

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
  transition: box-shadow 0.2s;
}
.psm-avatar:hover { box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15); }

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

.psm-label--req {
  color: #dc2626;
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

.psm-input--has-suffix {
  padding-right: 2.2222rem;
}

.psm-input-with-suffix {
  position: relative;
}

.psm-input-suffix {
  position: absolute;
  right: 0.8333rem;
  top: 50%;
  transform: translateY(-50%);
  font-size: 0.9028rem;
  color: rgba(105, 105, 105, 0.4);
  pointer-events: none;
}

.psm-textarea {
  height: auto;
  padding: 0.8333rem 1.0417rem;
  resize: vertical;
  min-height: 3.4722rem;
}

.psm-char-count {
  margin-top: 0.2778rem;
  text-align: right;
  font-size: 0.6944rem;
  color: rgba(105, 105, 105, 0.35);
}

.psm-field-error {
  font-size: 0.7639rem;
  color: #dc2626;
}

.psm-hint {
  font-size: 0.7639rem;
  color: rgba(105, 105, 105, 0.56);
  line-height: 1.4;
}

.psm-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
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
  gap: 0.5rem;
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
.psm-btn-accent:disabled { opacity: 0.5; cursor: not-allowed; }

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
.psm-btn-outline:disabled { opacity: 0.5; cursor: not-allowed; }

.psm-btn-outline--warn {
  color: #dc6b2f;
  border-color: rgba(220, 107, 47, 0.25);
}
.psm-btn-outline--warn:hover { background: #fff7f0; border-color: rgba(220, 107, 47, 0.4); color: #c0501d; }

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

/* ===== Spinner ===== */
.psm-spinner {
  animation: psm-spin 0.8s linear infinite;
}
@keyframes psm-spin {
  to { transform: rotate(360deg); }
}

/* ===== Toggle switch ===== */
.psm-toggle {
  /* relative — якорим sr-only чекбокс внутри тумблера, иначе при клике
     фокус на нём заставляет браузер скроллить модалку вверх */
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 0.5556rem;
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
  font: inherit;
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
.psm-toggle__track--disabled { opacity: 0.4; cursor: not-allowed; }

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
  transition: background 0.15s;
}
.psm-channel-row:hover { background: #f0f4f8; }

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
.psm-channel-dot--sync { background: #f59e0b; animation: psm-pulse 1.5s ease-in-out infinite; }
.psm-channel-dot--error { background: #ef4444; }

@keyframes psm-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

/* ===== Google Sheets ===== */
.psm-sheets-card {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 1rem;
  padding: 1.0417rem;
  background: linear-gradient(135deg, #f8fafb 0%, #eff6ff 100%);
  border: 1px solid rgba(37, 99, 235, 0.08);
  border-radius: 0.8333rem;
}

.psm-sheets-card__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.6389rem;
  height: 2.6389rem;
  border-radius: 0.6944rem;
  background: #fff;
  box-shadow: 0 0.3472rem 1.0417rem rgba(15, 23, 42, 0.06);
}

.psm-sheets-card__content {
  min-width: 0;
}

.psm-sheets-instruction {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5556rem;
  margin-top: 0.8333rem;
  padding: 0.7639rem 0.8333rem;
  background: #fff;
  border: 1px dashed rgba(105, 105, 105, 0.2);
  border-radius: 0.6944rem;
}

.psm-sheets-instruction__label {
  font-size: 0.7639rem;
  font-weight: 600;
  color: rgba(105, 105, 105, 0.72);
  text-transform: uppercase;
}

.psm-code-pill {
  display: inline-flex;
  align-items: center;
  max-width: 100%;
  padding: 0.2083rem 0.5556rem;
  font-size: 0.7639rem;
  font-weight: 500;
  color: #1f2937;
  background: #f3f4f6;
  border-radius: 0.4167rem;
  overflow-wrap: anywhere;
}

.psm-sheets-status {
  display: flex;
  align-items: center;
  gap: 0.4861rem;
  margin-top: 0.8333rem;
  padding: 0.6944rem 0.8333rem;
  font-size: 0.8333rem;
  font-weight: 500;
  color: #92400e;
  background: #fffbeb;
  border: 1px solid rgba(245, 158, 11, 0.16);
  border-radius: 0.6944rem;
}

.psm-sheets-status--ok {
  color: #166534;
  background: #f0fdf4;
  border-color: rgba(34, 197, 94, 0.16);
}

.psm-sheets-status--warn {
  color: #92400e;
}

.psm-sheets-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.6944rem;
  margin-top: 0.8333rem;
}

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
  display: inline-flex;
  align-items: center;
  gap: 0.2778rem;
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

.psm-detector-expanded-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.8333rem 1.0417rem;
  margin-bottom: 1.1111rem;
  background: #f8fafb;
  border-radius: 0.6944rem;
}

.psm-detector-expanded-toolbar__title {
  font-size: 0.9028rem;
  font-weight: 500;
  color: #171717;
}

.psm-detector-expanded-toolbar__hint {
  margin-top: 0.1389rem;
  font-size: 0.8333rem;
  color: rgba(105, 105, 105, 0.5);
}

/* ===== Budget cards ===== */
.psm-period-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 11.1111rem));
  gap: 0.8333rem;
  margin-bottom: 1.1111rem;
}

.psm-budget-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(14.5833rem, 1fr));
  gap: 1.0417rem;
}

.psm-budget-card {
  padding: 1.0417rem;
  background: #f8fafb;
  border-radius: 0.8333rem;
  border: 1px solid rgba(0, 0, 0, 0.04);
}

.psm-budget-card__name {
  font-size: 0.9028rem;
  font-weight: 500;
  color: #171717;
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
  transition: background 0.15s;
}
.psm-goals-table__row:last-child { border-bottom: 0; }
.psm-goals-table__row:hover { background: rgba(0, 0, 0, 0.015); }

.psm-goals-table__row--summary {
  background: #fefce8;
}
.psm-goals-table__row--summary:hover { background: #fef9c3; }

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
  transition: background 0.15s;
}

.psm-manage-row--paused {
  background: #eff6ff;
  border: 1px solid rgba(37, 99, 235, 0.1);
}

.psm-manage-row--danger {
  background: #fef2f2;
  border: 1px solid rgba(220, 38, 38, 0.08);
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
  align-items: center;
  gap: 0.8333rem;
  padding: 1.25rem 2.0833rem;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
  flex-shrink: 0;
  background: #f5f7f9;
  border-radius: 0 0 1.25rem 1.25rem;
  box-shadow: 0 -0.4167rem 1.25rem rgba(15, 23, 42, 0.035);
}

.psm-unsaved-dot {
  width: 0.5556rem;
  height: 0.5556rem;
  border-radius: 50%;
  background: #f59e0b;
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
.dark .psm-container { background: #1e2130; }

:root.dark .psm-card,
.dark .psm-card { background: #2C2F3D; border-color: rgba(255, 255, 255, 0.08); }

:root.dark .psm-title, .dark .psm-title,
:root.dark .psm-card__title, .dark .psm-card__title,
:root.dark .psm-channel-name, .dark .psm-channel-name,
:root.dark .psm-goal-name, .dark .psm-goal-name,
:root.dark .psm-manage-row__title, .dark .psm-manage-row__title,
:root.dark .psm-detector-collapsed__text, .dark .psm-detector-collapsed__text,
:root.dark .psm-subsection-title, .dark .psm-subsection-title,
:root.dark .psm-confirm-title, .dark .psm-confirm-title,
:root.dark .psm-toggle__label, .dark .psm-toggle__label,
:root.dark .psm-budget-card__name, .dark .psm-budget-card__name { color: #fff; }

:root.dark .psm-input, .dark .psm-input {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.12);
  color: #e5e7eb;
}

:root.dark .psm-channel-row, .dark .psm-channel-row,
:root.dark .psm-manage-row, .dark .psm-manage-row,
:root.dark .psm-budget-card, .dark .psm-budget-card,
:root.dark .psm-sheets-card, .dark .psm-sheets-card,
:root.dark .psm-detector-collapsed, .dark .psm-detector-collapsed,
:root.dark .psm-goals-table__header, .dark .psm-goals-table__header,
:root.dark .psm-empty, .dark .psm-empty { background: rgba(255, 255, 255, 0.04); }

:root.dark .psm-manage-row--danger, .dark .psm-manage-row--danger { background: rgba(220, 38, 38, 0.08); }
:root.dark .psm-manage-row--paused, .dark .psm-manage-row--paused { background: rgba(37, 99, 235, 0.08); border-color: rgba(37, 99, 235, 0.12); }

:root.dark .psm-goals-table, .dark .psm-goals-table { border-color: rgba(255, 255, 255, 0.06); }
:root.dark .psm-goals-table__row, .dark .psm-goals-table__row { border-bottom-color: rgba(255, 255, 255, 0.04); }
:root.dark .psm-goals-table__row--summary, .dark .psm-goals-table__row--summary { background: rgba(250, 204, 21, 0.06); }

:root.dark .psm-close, .dark .psm-close { background: rgba(255, 255, 255, 0.08); color: #9ca3af; }
:root.dark .psm-close:hover, .dark .psm-close:hover { background: rgba(37, 99, 235, 0.15); color: #60a5fa; }

:root.dark .psm-btn-secondary, .dark .psm-btn-secondary { background: rgba(255, 255, 255, 0.06); border-color: rgba(255, 255, 255, 0.1); color: #9ca3af; }
:root.dark .psm-btn-outline, .dark .psm-btn-outline,
:root.dark .psm-btn-outline-sm, .dark .psm-btn-outline-sm { background: rgba(255, 255, 255, 0.06); border-color: rgba(255, 255, 255, 0.1); color: #9ca3af; }

:root.dark .psm-sheets-card__icon, .dark .psm-sheets-card__icon,
:root.dark .psm-sheets-instruction, .dark .psm-sheets-instruction,
:root.dark .psm-code-pill, .dark .psm-code-pill { background: rgba(255, 255, 255, 0.06); color: #e5e7eb; }

:root.dark .psm-sheets-status, .dark .psm-sheets-status { background: rgba(245, 158, 11, 0.08); border-color: rgba(245, 158, 11, 0.12); }
:root.dark .psm-sheets-status--ok, .dark .psm-sheets-status--ok { background: rgba(34, 197, 94, 0.08); border-color: rgba(34, 197, 94, 0.12); color: #86efac; }

:root.dark .psm-footer, .dark .psm-footer { border-top-color: rgba(255, 255, 255, 0.06); background: #1e2130; }
:root.dark .psm-header, .dark .psm-header { border-bottom-color: rgba(255, 255, 255, 0.06); }
:root.dark .psm-confirm-box, .dark .psm-confirm-box { background: #2C2F3D; }
:root.dark .psm-error, .dark .psm-error { background: rgba(220, 38, 38, 0.1); border-color: rgba(220, 38, 38, 0.2); }
</style>
