<template>
  <div class="relative z-[2] flex min-h-full flex-col overflow-x-hidden px-[1.7361rem] py-[2.0833rem]">
    <div class="pt-[1.0417rem] pb-[1.0417rem] mb-[0.6944rem]">
      <h3 class="text-[2.0833rem] font-semibold leading-none text-[#171717] dark:text-white">Новая интеграция</h3>
      <p class="mt-[0.5556rem] text-[1.0417rem] font-medium leading-[1.35] text-[rgba(105,105,105,0.56)] dark:text-white/55">Добавление рекламного канала</p>
    </div>

    <div v-if="error" class="wizard-alert mb-[1.3889rem] dark:!bg-red-500/10 dark:!text-red-300">
      {{ error }}
    </div>

    <div class="wizard-shell">
      <section class="wizard-step-section" :class="{ 'wizard-step-section--active': step === 1, 'wizard-step-section--done': step > 1 }">
        <button
          type="button"
          class="wizard-step dark:!bg-[#2C2F3D] dark:!text-white/75 dark:!shadow-[inset_0_0_0_1px_rgba(255,255,255,0.08)]"
          :class="{ 'wizard-step--active': step === 1, 'wizard-step--done': step > 1 }"
          @click="goToVisibleStep(1)"
        >
          <span class="wizard-step__number dark:!bg-white/10 dark:!text-white/65">1</span>
          <span class="wizard-step__label">Проект</span>
        </button>

        <Transition name="step-expand">
          <div v-if="isStepVisible(1)" class="wizard-content">
        <div class="wizard-grid">
          <div class="wizard-panel dark:!bg-[#2C2F3D] dark:!border dark:!border-white/10">
            <div class="field-block">
              <div class="field-label dark:!text-white/65">Рекламный канал</div>
              <div class="platform-grid">
                <button
                  type="button"
                  class="platform-choice dark:!border-white/10 dark:!bg-white/5 dark:!text-white/75"
                  :class="{ 'platform-choice--active': form.platform === 'YANDEX_DIRECT' }"
                  @click="form.platform = 'YANDEX_DIRECT'"
                >
                  <img src="/admirra/img/icons/yandex-direct.png" alt="Yandex Direct" />
                  <span>Yandex Direct</span>
                </button>
                <button
                  type="button"
                  class="platform-choice dark:!border-white/10 dark:!bg-white/5 dark:!text-white/75"
                  :class="{ 'platform-choice--active': form.platform === 'VK_ADS' }"
                  @click="form.platform = 'VK_ADS'"
                >
                  <img src="/admirra/img/icons/vk-ads.png" alt="VK Ads" />
                  <span>VK Ads</span>
                </button>
              </div>
            </div>

            <div class="field-block">
              <div class="field-label dark:!text-white/65">Проект</div>
              <div class="custom-select" :class="{ open: openSelect === 'project', disabled: isNewProject }">
                <button
                  type="button"
                  class="cs-head dark:!bg-[#2C2F3D] dark:!text-white/70 dark:!shadow-[inset_0_0_0_1px_rgba(255,255,255,0.1)]"
                  :disabled="isNewProject"
                  @click="toggleProjectSelect"
                >
                  <span class="cs-current">{{ projectSelectLabel }}</span>
                  <span class="cs-arrow dark:!bg-white/10">
                    <svg width="5" height="4" viewBox="0 0 9 6" fill="none">
                      <path d="M0.5 1L4.5 5L8.5 1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                  </span>
                </button>
                <div class="cs-list dark:!bg-[#2C2F3D] dark:!shadow-[0_0_0_1px_rgba(255,255,255,0.08)]">
                  <button
                    type="button"
                    class="cs-option dark:!text-white/70 dark:hover:!bg-white/5"
                    :class="{ selected: !form.client_id }"
                    @click="selectProject('')"
                  >
                    Выберите проект
                  </button>
                  <button
                    v-for="p in projects"
                    :key="p.id"
                    type="button"
                    class="cs-option dark:!text-white/70 dark:hover:!bg-white/5"
                    :class="{ selected: String(form.client_id) === String(p.id) }"
                    @click="selectProject(p.id)"
                  >
                    {{ p.name }}
                  </button>
                </div>
              </div>
            </div>

            <label class="switch-row dark:!text-white/70">
              <input v-model="isNewProject" type="checkbox" />
              <span class="switch-row__control dark:!bg-white/10"></span>
              <span>Создать новый проект</span>
            </label>

            <input
              v-if="isNewProject"
              v-model="form.client_name"
              class="wizard-input dark:!bg-[#2C2F3D] dark:!text-white/90 dark:!shadow-[inset_0_0_0_1px_rgba(255,255,255,0.1)] dark:placeholder:!text-white/40"
              type="text"
              placeholder="Название нового проекта"
            />

            <button
              type="button"
              class="primary-btn mt-auto"
              :class="{ 'primary-btn--vk': form.platform === 'VK_ADS' }"
              :disabled="loadingAuth"
              @click="handleConnectClick"
            >
              <span>{{ loadingAuth ? 'Перенаправление...' : connectButtonText }}</span>
            </button>
          </div>

          <div class="channel-card">
            <div class="channel-card__icon">
              <img :src="platformIcon" :alt="platformName" />
            </div>
            <h4>{{ platformTitle }}</h4>
            <p>Автоматический сбор кампаний, ключевых слов и статистики</p>
            <div class="channel-card__status">
              <span></span>
              API: СОЕДИНЕНО
            </div>
          </div>
          </div>
          </div>
        </Transition>
      </section>

      <section class="wizard-step-section" :class="{ 'wizard-step-section--active': step === 2, 'wizard-step-section--done': step > 2 }">
        <button
          type="button"
          class="wizard-step dark:!bg-[#2C2F3D] dark:!text-white/75 dark:!shadow-[inset_0_0_0_1px_rgba(255,255,255,0.08)]"
          :class="{ 'wizard-step--active': step === 2, 'wizard-step--done': step > 2 }"
          @click="goToVisibleStep(2)"
        >
          <span class="wizard-step__number dark:!bg-white/10 dark:!text-white/65">2</span>
          <span class="wizard-step__label">Профиль</span>
        </button>

        <Transition name="step-expand">
          <div v-if="isStepVisible(2)" class="wizard-content">
        <div class="wizard-panel dark:!bg-[#2C2F3D] dark:!border dark:!border-white/10">
          <div class="panel-head">
            <h4 class="dark:!text-white/90">Выберите рекламный кабинет для интеграции</h4>
            <div class="search-wrap">
              <input
                v-model="profileSearch"
                type="text"
                class="search-input dark:!bg-[#2C2F3D] dark:!text-white/95 dark:!shadow-[inset_0_0_0_1px_rgba(255,255,255,0.12)] dark:placeholder:!text-white/55"
                placeholder="Поиск по кабинетам"
              />
              <div class="search-icon-circle dark:!bg-white/10">
                <svg width="7" height="7" viewBox="0 0 16 16" fill="none">
                  <circle cx="6.5" cy="6.5" r="5.5" stroke="#ababab" stroke-width="1.8"/>
                  <path d="M10.5 10.5L14 14" stroke="#ababab" stroke-width="1.8" stroke-linecap="round"/>
                </svg>
              </div>
            </div>
          </div>

          <div v-if="loadingStates.profiles" class="empty-line dark:!text-white/55">Загрузка профилей...</div>
          <div v-else-if="profiles.length === 0" class="empty-line dark:!text-white/55">Нет доступных профилей. Проверьте авторизацию.</div>
          <div v-else-if="filteredProfiles.length === 0" class="empty-line dark:!text-white/55">Кабинеты не найдены</div>

          <div v-else class="cards-grid">
            <label
              v-for="cabinet in filteredProfiles"
              :key="cabinet.login"
              class="select-tile dark:!border-white/10 dark:!bg-white/5"
              :class="{ 'select-tile--active': form.account_id === cabinet.login }"
            >
              <input
                type="radio"
                name="card-ads"
                :value="cabinet.login"
                :checked="form.account_id === cabinet.login"
                @change="selectProfile(cabinet)"
              />
              <span class="select-tile__top">
                <span class="select-tile__avatar dark:!bg-white/10">
                  <img :src="platformIcon" :alt="platformName" />
                </span>
                <span class="select-tile__check dark:!bg-white/10">✓</span>
              </span>
              <span class="select-tile__title dark:!text-white/85">{{ cabinet.name || cabinet.login }}</span>
              <span class="select-tile__meta dark:!text-white/50">{{ cabinet.login }}</span>
              <span class="select-tile__caption dark:!bg-white/10 dark:!text-white/55">{{ cabinet.type || 'Рекламный кабинет' }}</span>
            </label>
          </div>

          <div class="wizard-actions">
            <button type="button" class="secondary-btn dark:!bg-white/5 dark:!text-white/70 dark:!shadow-[inset_0_0_0_1px_rgba(255,255,255,0.12)]" @click="step = 1">Назад</button>
            <div class="wizard-actions__right">
              <button type="button" class="ghost-btn dark:!bg-white/5 dark:!text-white/70" @click="handleCancel">Отмена</button>
              <button
                type="button"
                class="primary-btn"
                :disabled="!form.account_id || loadingStates.profiles"
                @click="goToStep3"
              >
                Далее
              </button>
            </div>
          </div>
          </div>
          </div>
        </Transition>
      </section>

      <section class="wizard-step-section" :class="{ 'wizard-step-section--active': step === 3, 'wizard-step-section--done': step > 3 }">
        <button
          type="button"
          class="wizard-step dark:!bg-[#2C2F3D] dark:!text-white/75 dark:!shadow-[inset_0_0_0_1px_rgba(255,255,255,0.08)]"
          :class="{ 'wizard-step--active': step === 3, 'wizard-step--done': step > 3 }"
          @click="goToVisibleStep(3)"
        >
          <span class="wizard-step__number dark:!bg-white/10 dark:!text-white/65">3</span>
          <span class="wizard-step__label">Счетчики и цели</span>
        </button>

        <Transition name="step-expand">
          <div v-if="isStepVisible(3)" class="wizard-content">
        <div class="wizard-panel soft-panel dark:!bg-[#2C2F3D] dark:!border dark:!border-white/10">
          <div>
            <h4 class="dark:!text-white/90">Рекламные кампании</h4>
            <p class="dark:!text-white/55">Выбор РК отключен: система автоматически использует все кампании выбранного кабинета.</p>
          </div>
          <div class="status-pill dark:!bg-white/5 dark:!text-white/70">{{ loadingStates.campaigns ? 'Загрузка...' : `Найдено кампаний: ${campaigns.length}` }}</div>
          </div>

        <div v-if="form.platform === 'YANDEX_DIRECT'" class="wizard-panel mt-[1.3889rem] dark:!bg-[#2C2F3D] dark:!border dark:!border-white/10">
          <div class="panel-head">
            <div>
              <h4 class="dark:!text-white/90">Счетчики метрики</h4>
              <p class="dark:!text-white/55">Выберите счетчики для отслеживания целей</p>
            </div>
            <button
              type="button"
              class="small-btn dark:!bg-white/5 dark:!text-white/70 dark:!shadow-[inset_0_0_0_1px_rgba(255,255,255,0.12)]"
              :disabled="loadingStates.counters || counters.length === 0"
              @click="toggleAllCounters"
            >
              {{ allCountersSelected ? 'Снять все' : 'Отметить все' }}
            </button>
          </div>

          <div v-if="loadingStates.counters" class="empty-line dark:!text-white/55">Загрузка счетчиков...</div>
          <div v-else-if="counters.length === 0" class="empty-line dark:!text-white/55">Нет доступных счетчиков.</div>

          <div v-else class="cards-grid">
            <label
              v-for="counter in counters"
              :key="counter.id"
              class="select-tile dark:!border-white/10 dark:!bg-white/5"
              :class="{ 'select-tile--active': selectedCounterIds.includes(counter.id) }"
            >
              <input
                type="checkbox"
                :checked="selectedCounterIds.includes(counter.id)"
                @change="toggleCounterSelection(counter.id)"
              />
              <span class="select-tile__top">
                <span class="select-tile__avatar select-tile__avatar--text dark:!bg-white/10 dark:!text-white/65">{{ (counter.name || '?').slice(0, 2).toUpperCase() }}</span>
                <span class="select-tile__check dark:!bg-white/10">✓</span>
              </span>
              <span class="select-tile__title dark:!text-white/85">{{ counter.name }}</span>
              <span class="select-tile__meta dark:!text-white/50">ID: {{ counter.id }}</span>
            </label>
          </div>
        </div>

        <div v-if="form.platform === 'YANDEX_DIRECT'" class="wizard-panel mt-[1.3889rem] dark:!bg-[#2C2F3D] dark:!border dark:!border-white/10">
          <div class="panel-head">
            <div>
              <h4 class="dark:!text-white/90">Цели и конверсии</h4>
              <p class="dark:!text-white/55">Выберите основную цель и дополнительные цели</p>
            </div>
            <button
              type="button"
              class="small-btn dark:!bg-white/5 dark:!text-white/70 dark:!shadow-[inset_0_0_0_1px_rgba(255,255,255,0.12)]"
              :disabled="loadingStates.goals || goals.length === 0"
              @click="toggleAllGoals"
            >
              {{ allGoalsSelected ? 'Снять все' : 'Отметить все' }}
            </button>
          </div>

          <div v-if="loadingStates.goals" class="empty-line dark:!text-white/55">Загрузка целей...</div>
          <div v-else-if="goals.length === 0" class="empty-line dark:!text-white/55">Нет доступных целей.</div>

          <div v-else class="cards-grid">
            <label
              v-for="goal in goals"
              :key="goal.id"
              class="select-tile dark:!border-white/10 dark:!bg-white/5"
              :class="{ 'select-tile--active': selectedGoalIds.includes(goal.id) }"
            >
              <input
                type="checkbox"
                :checked="selectedGoalIds.includes(goal.id)"
                @change="toggleGoalSelection(goal.id)"
              />
              <span class="select-tile__top">
                <span class="select-tile__avatar select-tile__avatar--text dark:!bg-white/10 dark:!text-white/65">{{ (goal.name || '?').slice(0, 2).toUpperCase() }}</span>
                <span class="select-tile__check dark:!bg-white/10">✓</span>
              </span>
              <span class="select-tile__title dark:!text-white/85">{{ goal.name }}</span>
              <span class="select-tile__meta dark:!text-white/50">ID: {{ goal.id }}</span>
              <span class="select-tile__footer">
                <span class="select-tile__caption dark:!bg-white/10 dark:!text-white/55">{{ goal.type || 'Цель' }}</span>
                <button
                  type="button"
                  class="favorite-btn dark:!bg-white/10 dark:!text-white/45"
                  :class="{ 'favorite-btn--active': form.primary_goal_id === goal.id }"
                  :title="form.primary_goal_id === goal.id ? 'Снять основную цель' : 'Сделать основной'"
                  @click.stop.prevent="selectPrimaryGoal(goal.id)"
                >
                  ★
                </button>
              </span>
            </label>
          </div>
        </div>

        <div class="wizard-actions mt-[1.3889rem]">
          <button type="button" class="secondary-btn dark:!bg-white/5 dark:!text-white/70 dark:!shadow-[inset_0_0_0_1px_rgba(255,255,255,0.12)]" @click="step = 2">Назад</button>
          <div class="wizard-actions__right">
            <button type="button" class="ghost-btn dark:!bg-white/5 dark:!text-white/70" @click="handleCancel">Отмена</button>
            <button type="button" class="primary-btn" @click="goToStep4">Далее</button>
          </div>
        </div>
          </div>
        </Transition>
      </section>

      <section class="wizard-step-section" :class="{ 'wizard-step-section--active': step === 4 }">
        <button
          type="button"
          class="wizard-step dark:!bg-[#2C2F3D] dark:!text-white/75 dark:!shadow-[inset_0_0_0_1px_rgba(255,255,255,0.08)]"
          :class="{ 'wizard-step--active': step === 4 }"
          @click="goToVisibleStep(4)"
        >
          <span class="wizard-step__number dark:!bg-white/10 dark:!text-white/65">4</span>
          <span class="wizard-step__label">Сводка</span>
        </button>

        <Transition name="step-expand">
          <div v-if="isStepVisible(4)" class="wizard-content">
        <div class="wizard-panel dark:!bg-[#2C2F3D] dark:!border dark:!border-white/10">
          <div class="panel-head">
            <div>
              <h4 class="dark:!text-white/90">Сводка интеграции</h4>
              <p class="dark:!text-white/55">Проверьте настройки перед подключением</p>
            </div>
          </div>

          <div class="summary-grid">
            <div class="summary-card summary-card--blue dark:!bg-white/5">
              <span class="summary-card__icon dark:!bg-white/10"><img :src="platformIcon" :alt="platformName" /></span>
              <span class="summary-card__label dark:!text-white/50">Платформа</span>
              <strong class="dark:!text-white/85">{{ platformName }}</strong>
            </div>
            <div class="summary-card summary-card--green dark:!bg-white/5">
              <span class="summary-card__icon dark:!bg-white/10">↻</span>
              <span class="summary-card__label dark:!text-white/50">Кампании</span>
              <strong class="dark:!text-white/85">{{ allFromProfile ? 'Все кампании' : `Выбрано: ${selectedCampaignIds.length}` }}</strong>
            </div>
            <div v-if="form.platform === 'YANDEX_DIRECT'" class="summary-card summary-card--yellow dark:!bg-white/5">
              <span class="summary-card__icon dark:!bg-white/10">#</span>
              <span class="summary-card__label dark:!text-white/50">Счетчики</span>
              <strong class="dark:!text-white/85">Выбрано: {{ selectedCounterIds.length }}</strong>
              <ul v-if="summaryCounterLines.length">
                <li v-for="(line, i) in summaryCounterLines" :key="i">{{ line }}</li>
              </ul>
            </div>
            <div v-if="form.platform === 'YANDEX_DIRECT' && form.primary_goal_id" class="summary-card summary-card--cyan dark:!bg-white/5">
              <span class="summary-card__icon dark:!bg-white/10">★</span>
              <span class="summary-card__label dark:!text-white/50">Основная цель</span>
              <strong class="dark:!text-white/85">{{ goals.find(g => g.id === form.primary_goal_id)?.name || form.primary_goal_id }}</strong>
            </div>
            <div v-if="form.platform === 'YANDEX_DIRECT'" class="summary-card summary-card--violet dark:!bg-white/5">
              <span class="summary-card__icon dark:!bg-white/10">+</span>
              <span class="summary-card__label dark:!text-white/50">Дополнительные цели</span>
              <strong class="dark:!text-white/85">Отмечено: {{ summaryAdditionalGoalLines.length }}</strong>
              <ul v-if="summaryAdditionalGoalLines.length">
                <li v-for="(name, i) in summaryAdditionalGoalLines" :key="i">{{ name }}</li>
              </ul>
            </div>
          </div>
          </div>

        <div class="final-card mt-[1.3889rem]">
          <div>
            <div class="final-card__caption">Автосинхронизация</div>
            <h4>Данные будут обновляться каждые 24 часа</h4>
            <label class="final-switch">
              <input type="checkbox" checked />
              <span></span>
              Включить автосинхронизацию
            </label>
          </div>
          <div class="ready-badge">
            <span></span>
            ГОТОВНОСТЬ 100%
          </div>
        </div>

        <div class="wizard-actions mt-[1.3889rem]">
          <button type="button" class="secondary-btn dark:!bg-white/5 dark:!text-white/70 dark:!shadow-[inset_0_0_0_1px_rgba(255,255,255,0.12)]" @click="step = 3">Назад</button>
          <div class="wizard-actions__right">
            <button type="button" class="ghost-btn dark:!bg-white/5 dark:!text-white/70" @click="handleCancel">Отмена</button>
            <button
              type="button"
              class="primary-btn"
              :disabled="loadingStates.finish"
              @click="doFinish"
            >
              {{ loadingStates.finish ? 'Сохранение...' : 'Подключить' }}
            </button>
          </div>
        </div>
          </div>
        </Transition>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useProjects } from '../../composables/useProjects'
import { useIntegrationWizard } from '../../composables/useIntegrationWizard'
import { useToaster } from '../../composables/useToaster'
import api from '../../api/axios'

const router = useRouter()
const { projects, fetchProjects } = useProjects()
const toaster = useToaster()

const {
  error,
  form,
  loadingStates,
  campaigns,
  selectedCampaignIds,
  allFromProfile,
  counters,
  selectedCounterIds,
  goals,
  selectedGoalIds,
  profiles,
  lastIntegrationId,
  fetchProfiles,
  fetchCampaigns,
  fetchCounters,
  fetchGoals,
  fetchIntegration,
  resetStore,
  toggleCounterSelection,
  selectPrimaryGoal
} = useIntegrationWizard()

const step = ref(1)
const isNewProject = ref(false)
const loadingAuth = ref(false)
const openSelect = ref(null)
const profileSearch = ref('')
const platformName = computed(() => form.platform === 'YANDEX_DIRECT' ? 'Yandex Direct' : 'VK Ads')
const platformTitle = computed(() => form.platform === 'YANDEX_DIRECT' ? 'Интеграция с Яндекс.Директ' : 'Интеграция с VK Ads')
const platformIcon = computed(() => form.platform === 'YANDEX_DIRECT' ? '/admirra/img/icons/yandex-direct.png' : '/admirra/img/icons/vk-ads.png')
const connectButtonText = computed(() =>
  form.platform === 'YANDEX_DIRECT' ? 'Подключить Яндекс Директ' : 'Подключить VK Ads'
)
const projectSelectLabel = computed(() => {
  if (!form.client_id) return 'Выберите проект'
  return projects.value.find((p) => String(p.id) === String(form.client_id))?.name || 'Выберите проект'
})
const allCountersSelected = computed(() =>
  counters.value.length > 0 && selectedCounterIds.value.length === counters.value.length
)
const allGoalsSelected = computed(() =>
  goals.value.length > 0 && selectedGoalIds.value.length === goals.value.length
)

const filteredProfiles = computed(() => {
  const q = profileSearch.value.trim().toLowerCase()
  if (!q) return profiles.value
  return profiles.value.filter((cabinet) =>
    String(cabinet.name || '').toLowerCase().includes(q) ||
    String(cabinet.login || '').toLowerCase().includes(q) ||
    String(cabinet.type || '').toLowerCase().includes(q)
  )
})

const summaryCounterLines = computed(() =>
  selectedCounterIds.value
    .map((id) => counters.value.find((c) => c.id === id))
    .filter(Boolean)
    .map((c) => `${c.name || 'Счётчик'} · ID ${c.id}`)
)

const summaryAdditionalGoalLines = computed(() => {
  const primary = form.primary_goal_id
  return selectedGoalIds.value
    .filter((id) => id !== primary)
    .map((id) => goals.value.find((g) => g.id === id)?.name || String(id))
})

let counterGoalsDebounce = null
watch(
  selectedCounterIds,
  () => {
    if (step.value !== 3 || !lastIntegrationId.value || form.platform !== 'YANDEX_DIRECT') return
    clearTimeout(counterGoalsDebounce)
    counterGoalsDebounce = setTimeout(() => {
      fetchGoals(lastIntegrationId.value)
    }, 400)
  },
  { deep: true }
)

onMounted(async () => {
  const platformQuery = router.currentRoute.value.query.platform
  if (platformQuery === 'YANDEX_DIRECT' || platformQuery === 'VK_ADS') {
    form.platform = platformQuery
  }

  await fetchProjects()

  const clientIdQuery = router.currentRoute.value.query.client_id
  if (clientIdQuery && projects.value.some((project) => String(project.id) === String(clientIdQuery))) {
    form.client_id = String(clientIdQuery)
    isNewProject.value = false
  }

  // Проверяем, есть ли resumption после OAuth-редиректа
  const resumeId = router.currentRoute.value.query.resume_integration_id
  const startStep = router.currentRoute.value.query.initial_step

  if (resumeId) {
    lastIntegrationId.value = resumeId
    const s = parseInt(startStep) || 2
    await fetchIntegration(resumeId)

    if (s >= 2) {
      step.value = 2
      fetchProfiles(resumeId)
    }
  }

})

watch(isNewProject, (val) => {
  if (val) {
    form.client_id = ''
    openSelect.value = null
  } else {
    form.client_name = ''
  }
})

const goToVisibleStep = (idx) => {
  if (idx <= step.value) {
    error.value = null
    step.value = idx
  }
}

const toggleProjectSelect = () => {
  if (isNewProject.value) return
  openSelect.value = openSelect.value === 'project' ? null : 'project'
}

const selectProject = (id) => {
  form.client_id = id
  openSelect.value = null
}

const isStepVisible = (idx) => step.value >= idx

const selectProfile = (cabinet) => {
  form.account_id = cabinet.login
  form.agency_client_login = cabinet.login
}

const goToStep3 = async () => {
  if (!form.account_id) return
  try {
    await api.patch(`/integrations/${lastIntegrationId.value}`, {
      account_id: form.account_id,
      agency_client_login: form.agency_client_login || form.account_id
    })
    await new Promise(r => setTimeout(r, 100))
  } catch (err) {
    console.error('Failed to save profile:', err)
    error.value = 'Ошибка при сохранении профиля'
    return
  }
  step.value = 3
  await fetchCampaigns(lastIntegrationId.value)
  allFromProfile.value = true
  if (form.platform === 'YANDEX_DIRECT') {
    await fetchCounters(lastIntegrationId.value)
    await fetchGoals(lastIntegrationId.value)
  }
}

const goToStep4 = async () => {
  // РК теперь выбираются автоматически (all_campaigns=true), поэтому валидация по кампаниям не нужна.
  if (form.platform === 'YANDEX_DIRECT') {
    if (!selectedCounterIds.value.length) {
      error.value = 'Выберите хотя бы один счетчик'
      return
    }
    await fetchGoals(lastIntegrationId.value)
  }
  error.value = null
  step.value = 4
}

const handleCancel = async () => {
  try {
    if (lastIntegrationId.value) {
      await api.delete(`/integrations/${lastIntegrationId.value}`)
    }
  } catch (e) {
    console.error(e)
  } finally {
    resetStore()
    router.push('/integrations')
  }
}

const initYandexAuth = async () => {
  if (loadingAuth.value) return
  loadingAuth.value = true
  error.value = null
  let redirected = false
  try {
    if (form.client_id) localStorage.setItem('yandex_auth_client_id', form.client_id)
    if (form.client_name) localStorage.setItem('yandex_auth_client_name', form.client_name)
    if (isNewProject.value) localStorage.setItem('yandex_auth_is_new_project', 'true')

    const redirectUri = `${window.location.origin}/auth/yandex/callback`
    const { data } = await api.get(`integrations/yandex/auth-url?redirect_uri=${encodeURIComponent(redirectUri)}`)
    if (data?.url) {
      redirected = true
      toaster.info('Переходим в Яндекс OAuth...')
      window.location.assign(data.url)
      return
    }
    throw new Error('OAuth URL не получен')
  } catch (err) {
    error.value = err.response?.data?.detail || 'Не удалось инициализировать авторизацию Яндекс'
  } finally {
    if (!redirected) loadingAuth.value = false
  }
}

const initVKAuth = async () => {
  if (loadingAuth.value) return
  loadingAuth.value = true
  error.value = null
  let redirected = false
  try {
    if (form.client_id) localStorage.setItem('vk_auth_client_id', form.client_id)
    if (form.client_name) localStorage.setItem('vk_auth_client_name', form.client_name)
    if (isNewProject.value) localStorage.setItem('vk_auth_is_new_project', 'true')

    const redirectUri = `${window.location.origin}/auth/vk/callback`
    const { data } = await api.get(`integrations/vk/auth-url?redirect_uri=${encodeURIComponent(redirectUri)}`)
    if (data?.state) localStorage.setItem('vk_auth_state', data.state)
    if (data?.url) {
      redirected = true
      toaster.info('Переходим в VK OAuth...')
      window.location.assign(data.url)
      return
    }
    throw new Error('OAuth URL не получен')
  } catch (err) {
    error.value = err.response?.data?.detail || 'Не удалось инициализировать авторизацию VK'
  } finally {
    if (!redirected) loadingAuth.value = false
  }
}

const doFinish = async () => {
  if (!lastIntegrationId.value) return
  loadingStates.finish = true
  error.value = null
  try {
    await api.patch(`/integrations/${lastIntegrationId.value}`, {
      selected_campaign_ids: [...selectedCampaignIds.value],
      all_campaigns: true,
      selected_counters: [...selectedCounterIds.value],
      primary_goal_id: form.primary_goal_id,
      selected_goals: [...selectedGoalIds.value],
      is_active: true
    })
    toaster.success('Интеграция успешно настроена!')
    resetStore()
    router.push('/integrations')
  } catch (err) {
    error.value = err.response?.data?.detail || 'Ошибка при завершении настройки'
  } finally {
    loadingStates.finish = false
  }
}

const handleConnectClick = async () => {
  if (!form.client_id && !form.client_name) {
    error.value = 'Выберите проект или включите "Создать новый проект"'
    toaster.warning('Сначала выберите проект')
    return
  }
  if (form.platform === 'YANDEX_DIRECT') {
    await initYandexAuth()
  } else {
    await initVKAuth()
  }
}

const toggleAllCounters = () => {
  if (!counters.value.length) return
  if (allCountersSelected.value) {
    selectedCounterIds.value = []
  } else {
    selectedCounterIds.value = counters.value.map(c => c.id)
  }
}

const toggleAllGoals = () => {
  if (!goals.value.length) return
  if (allGoalsSelected.value) {
    selectedGoalIds.value = []
  } else {
    selectedGoalIds.value = goals.value.map(g => g.id)
  }
}

const toggleGoalSelection = (id) => {
  const idx = selectedGoalIds.value.indexOf(id)
  if (idx > -1) selectedGoalIds.value.splice(idx, 1)
  else selectedGoalIds.value.push(id)
}
</script>

<style scoped>
.wizard-alert {
  padding: 0.9722rem 1.25rem;
  border-radius: 0.8333rem;
  background: #fff1f1;
  color: #ef4444;
  font-size: 0.9028rem;
  font-weight: 500;
}
.wizard-shell {
  display: flex;
  flex-direction: column;
  gap: 1.0417rem;
}
.wizard-step-section {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 1.0417rem;
}
.wizard-step-section::before {
  content: "";
  position: absolute;
  left: 1.5278rem;
  top: 3.1944rem;
  bottom: -1.0417rem;
  width: 1px;
  background: rgba(105, 105, 105, 0.12);
}
.wizard-step-section:last-child::before {
  display: none;
}
.wizard-step-section--active::before {
  background: linear-gradient(180deg, rgba(37, 99, 235, 0.32), rgba(105, 105, 105, 0.12));
}
.wizard-step {
  width: max-content;
  min-width: 15.2778rem;
  display: flex;
  align-items: center;
  gap: 0.6944rem;
  min-height: 3.1944rem;
  padding: 0.5556rem 1.1806rem 0.5556rem 0.6944rem;
  border: 0;
  border-radius: 1.0417rem;
  background: #fff;
  color: rgba(105, 105, 105, 0.75);
  font-size: 0.9028rem;
  font-weight: 500;
  cursor: pointer;
  transition: color 0.3s, transform 0.3s;
}
.wizard-step:hover {
  transform: translateX(0.1389rem);
}
.wizard-step__number {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.7361rem;
  height: 1.7361rem;
  border-radius: 50%;
  background: #f5f7f9;
  color: rgba(105, 105, 105, 0.56);
  flex-shrink: 0;
}
.wizard-step--active {
  color: #2563eb;
}
.wizard-step--active .wizard-step__number,
.wizard-step--done .wizard-step__number {
  background: linear-gradient(270deg, #06b5d4 0.35%, #1f9de4 32.08%, #2563eb 96.51%);
  color: #fff;
}
.wizard-content {
  min-width: 0;
  padding-left: 4.2361rem;
}
.step-expand-enter-active,
.step-expand-leave-active {
  transition:
    opacity 0.28s ease,
    transform 0.32s cubic-bezier(0.4, 0, 0.2, 1),
    max-height 0.42s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}
.step-expand-enter-from,
.step-expand-leave-to {
  max-height: 0;
  opacity: 0;
  transform: translateY(-0.5556rem);
}
.step-expand-enter-to,
.step-expand-leave-from {
  max-height: 125rem;
  opacity: 1;
  transform: translateY(0);
}
.wizard-grid {
  display: grid;
  grid-template-columns: minmax(19.4444rem, 22.9167rem) minmax(22.2222rem, 29.8611rem);
  align-items: stretch;
  gap: 1.3889rem;
}
.wizard-panel {
  display: flex;
  flex-direction: column;
  gap: 1.3889rem;
  padding: 2.0833rem;
  border-radius: 1.0417rem;
  background: #fff;
}
.field-block {
  display: flex;
  flex-direction: column;
  gap: 0.6944rem;
}
.field-label {
  color: #696969;
  font-size: 0.9028rem;
  font-weight: 500;
}
.platform-grid {
  display: grid;
  gap: 0.6944rem;
}
.platform-choice {
  display: flex;
  align-items: center;
  gap: 0.6944rem;
  min-height: 3.1944rem;
  padding: 0.5556rem 1.1806rem;
  border: 1px solid rgba(105, 105, 105, 0.12);
  border-radius: 1.0417rem;
  background: #fff;
  color: #696969;
  font-size: 0.9028rem;
  font-weight: 500;
  transition: transform 0.4s, border-color 0.3s, background-color 0.3s, color 0.3s;
}
.platform-choice img {
  width: 1.3889rem;
  height: 1.3889rem;
  border-radius: 50%;
}
.platform-choice--active {
  border-color: transparent;
  background: linear-gradient(270deg, #06b5d4 0.35%, #1f9de4 32.08%, #2563eb 96.51%);
  color: #fff;
}
.platform-choice:hover {
  transform: scale(1.01);
}
.custom-select {
  position: relative;
  display: inline-flex;
  flex-direction: column;
  width: 100%;
}
.custom-select.disabled {
  opacity: 0.55;
  pointer-events: none;
}
.cs-head {
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  height: 3.1944rem;
  padding: 0.5556rem 1.1806rem;
  border: 0;
  border-radius: 1.0417rem;
  background-color: #fff;
  color: rgba(0, 0, 0, 0.4);
  font-size: 0.9028rem;
  font-weight: 500;
  box-shadow: inset 0 0 0 1px transparent;
  cursor: pointer;
  outline: none;
  transition: box-shadow 0.2s;
}
.custom-select.open .cs-head {
  box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.1);
}
.cs-current {
  min-width: 0;
  margin-right: 1.3889rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cs-arrow {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.1111rem;
  height: 1.1111rem;
  border-radius: 50%;
  background-color: #f5f7f9;
  flex-shrink: 0;
  transition: transform 0.3s;
}
.custom-select.open .cs-arrow {
  transform: rotate(180deg);
}
.cs-list {
  position: absolute;
  top: calc(100% + 0.2778rem);
  left: 0;
  min-width: 100%;
  max-height: 15.9722rem;
  overflow-y: auto;
  background-color: #fff;
  border-radius: 0.5556rem;
  box-shadow: 0 0 0 1px rgba(68, 68, 68, 0.1);
  z-index: 30;
  opacity: 0;
  pointer-events: none;
  transform-origin: 50% 0;
  transform: scale(0.75) translateY(-1.4583rem);
  transition: transform 0.2s cubic-bezier(0.5, 0, 0, 1.25), opacity 0.15s ease-out;
}
.custom-select.open .cs-list {
  opacity: 1;
  pointer-events: auto;
  transform: scale(1) translateY(0);
}
.cs-option {
  display: block;
  width: 100%;
  padding: 0.8333rem 1.7361rem 0.8333rem 1.1806rem;
  border: 0;
  background: transparent;
  color: rgba(0, 0, 0, 0.68);
  font-size: 0.9028rem;
  text-align: left;
  cursor: pointer;
  white-space: nowrap;
  transition: background-color 0.2s;
}
.cs-option:hover {
  background-color: #f5f7f9;
}
.cs-option.selected {
  font-weight: 600;
}
.wizard-input {
  width: 100%;
  height: 3.1944rem;
  padding: 0 1.1806rem;
  border: 0;
  border-radius: 0.8333rem;
  outline: none;
  background: #f9fcff;
  box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.08);
  color: #2c2c2c;
  font-size: 0.9028rem;
  font-weight: 500;
}
.switch-row,
.final-switch {
  display: inline-flex;
  align-items: center;
  gap: 0.6944rem;
  color: #696969;
  font-size: 0.9028rem;
  font-weight: 500;
  cursor: pointer;
}
.switch-row input,
.final-switch input,
.select-tile input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}
.switch-row__control,
.final-switch span {
  width: 2.6389rem;
  height: 1.5278rem;
  border-radius: 69.375rem;
  background: #e8eef9;
  position: relative;
  flex-shrink: 0;
  transition: background-color 0.3s;
}
.switch-row__control::after,
.final-switch span::after {
  content: "";
  position: absolute;
  top: 0.2083rem;
  left: 0.2083rem;
  width: 1.1111rem;
  height: 1.1111rem;
  border-radius: 50%;
  background: #fff;
  transition: transform 0.3s;
}
.switch-row input:checked + .switch-row__control,
.final-switch input:checked + span {
  background: #2563eb;
}
.switch-row input:checked + .switch-row__control::after,
.final-switch input:checked + span::after {
  transform: translateX(1.1111rem);
}
.primary-btn,
.secondary-btn,
.ghost-btn,
.small-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 3.1944rem;
  padding: 0.5556rem 1.5278rem;
  border: 0;
  border-radius: 1.0417rem;
  font-size: 0.9028rem;
  font-weight: 500;
  white-space: nowrap;
  cursor: pointer;
  transition: transform 0.4s, background-color 0.3s, color 0.3s, opacity 0.3s;
}
.primary-btn {
  background: linear-gradient(270deg, #06b5d4 0.35%, #1f9de4 32.08%, #2563eb 96.51%);
  color: #fff;
}
.primary-btn--vk {
  background: linear-gradient(135deg, #0077ff, #005fcc);
}
.secondary-btn,
.small-btn {
  background: #fff;
  color: #696969;
  box-shadow: inset 0 0 0 1px rgba(105, 105, 105, 0.14);
}
.ghost-btn {
  background: #f5f7f9;
  color: #696969;
}
.small-btn {
  min-height: 2.5rem;
  padding: 0.4167rem 1.0417rem;
  border-radius: 0.8333rem;
}
.primary-btn:hover,
.secondary-btn:hover,
.ghost-btn:hover,
.small-btn:hover {
  transform: scale(1.02);
}
.primary-btn:disabled,
.small-btn:disabled {
  opacity: 0.5;
  transform: none;
  cursor: not-allowed;
}
.channel-card {
  width: min(100%, 29.8611rem);
  min-height: 22.9167rem;
  display: flex;
  flex-direction: column;
  padding: 2.0833rem;
  border-radius: 1.0417rem;
  color: #fff;
  background:
    radial-gradient(circle at 85% 18%, rgba(6, 181, 212, 0.38), transparent 26%),
    linear-gradient(135deg, #181f2f 0%, #26324a 100%);
  overflow: hidden;
}
.channel-card__icon {
  width: 2.7778rem;
  height: 2.7778rem;
  margin-bottom: 1.6667rem;
}
.channel-card__icon img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.channel-card h4,
.final-card h4 {
  max-width: 22.9167rem;
  color: inherit;
  font-size: 1.6667rem;
  line-height: 1.2;
  font-weight: 600;
}
.channel-card p {
  max-width: 22.9167rem;
  margin-top: 0.9028rem;
  color: rgba(255, 255, 255, 0.58);
  font-size: 1.0417rem;
  line-height: 1.35;
}
.channel-card__status,
.ready-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5556rem;
  align-self: flex-start;
  margin-top: auto;
  min-height: 2.9167rem;
  padding: 0.5556rem 1.25rem;
  border-radius: 1.0417rem;
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
  font-size: 0.8333rem;
  font-weight: 700;
  letter-spacing: 0.04em;
}
.channel-card__status span,
.ready-badge span {
  width: 0.4861rem;
  height: 0.4861rem;
  border-radius: 50%;
  background: #5bff7c;
}
.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1.25rem;
}
.panel-head h4,
.soft-panel h4 {
  color: #2c2c2c;
  font-size: 1.25rem;
  font-weight: 600;
  line-height: 1.2;
}
.panel-head p,
.soft-panel p {
  margin-top: 0.5556rem;
  color: rgba(105, 105, 105, 0.56);
  font-size: 0.9722rem;
  font-weight: 500;
  line-height: 1.35;
}
.search-wrap {
  position: relative;
  flex: 0 0 auto;
}
.search-input {
  width: 24.5833rem;
  height: 3.1944rem;
  padding: 0 3.125rem 0 1.1806rem;
  border: none;
  border-radius: 0.8333rem;
  outline: none;
  background-color: #fff;
  box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.08);
  color: #2c2c2c;
  font-size: 0.9028rem;
  transition: box-shadow 0.5s;
}
.search-input:focus {
  box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.24), 0 0 0.6944rem rgba(37, 99, 235, 0.15);
}
.search-input::placeholder {
  color: rgba(0, 0, 0, 0.3);
}
.search-icon-circle {
  position: absolute;
  right: 1.1806rem;
  top: 50%;
  display: flex;
  width: 1.1111rem;
  height: 1.1111rem;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background-color: #f5f7f9;
  transform: translateY(-50%);
  pointer-events: none;
}
.empty-line {
  padding: 1.3889rem 0;
  color: rgba(105, 105, 105, 0.56);
  font-size: 0.9028rem;
}
.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(12.3611rem, 1fr));
  gap: 1.0417rem;
}
.select-tile {
  min-height: 12.3611rem;
  display: flex;
  flex-direction: column;
  gap: 0.6944rem;
  padding: 1.0417rem;
  border-radius: 0.8333rem;
  background: #f9fcff;
  border: 1px solid rgba(105, 105, 105, 0.08);
  cursor: pointer;
  transition: border-color 0.3s, box-shadow 0.3s, transform 0.3s;
}
.select-tile:hover {
  transform: translateY(-0.0694rem);
}
.select-tile--active {
  border-color: rgba(37, 99, 235, 0.35);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.08);
}
.select-tile__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.select-tile__avatar {
  width: 2.0833rem;
  height: 2.0833rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: #e8eef9;
  color: #4b6fa0;
  font-size: 0.6944rem;
  font-weight: 700;
}
.select-tile__avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.select-tile__check {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.5278rem;
  height: 1.5278rem;
  border-radius: 50%;
  background: #e8eef9;
  color: transparent;
  font-size: 0.8333rem;
  font-weight: 700;
}
.select-tile--active .select-tile__check {
  background: #2563eb;
  color: #fff;
}
.select-tile__title {
  color: #515151;
  font-size: 0.9722rem;
  font-weight: 600;
  line-height: 1.25;
}
.select-tile__meta {
  color: rgba(105, 105, 105, 0.56);
  font-size: 0.7639rem;
  text-transform: uppercase;
  overflow-wrap: anywhere;
}
.select-tile__caption {
  align-self: flex-start;
  margin-top: auto;
  padding: 0.5556rem 0.9722rem;
  border-radius: 0.5556rem;
  background: #fff;
  color: #c2c2c2;
  font-size: 0.7639rem;
}
.select-tile__footer {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 0.8333rem;
  margin-top: auto;
}
.favorite-btn {
  width: 2.2222rem;
  height: 2.2222rem;
  border: 0;
  border-radius: 50%;
  background: #e8eef9;
  color: #c2c2c2;
  font-size: 1.1111rem;
}
.favorite-btn--active {
  background: #fa812e;
  color: #fff;
}
.soft-panel {
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: 1.3889rem;
}
.status-pill {
  display: inline-flex;
  align-items: center;
  min-height: 2.6389rem;
  padding: 0.5556rem 1.0417rem;
  border-radius: 0.8333rem;
  background: #f9fcff;
  color: rgba(105, 105, 105, 0.7);
  font-size: 0.9028rem;
  font-weight: 500;
  white-space: nowrap;
}
.wizard-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.8333rem;
}
.wizard-actions__right {
  display: flex;
  align-items: center;
  gap: 0.6944rem;
}
.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1.0417rem;
}
.summary-card {
  display: flex;
  flex-direction: column;
  gap: 0.5556rem;
  min-height: 9.5833rem;
  padding: 1.3889rem;
  border-radius: 1.0417rem;
  color: #515151;
}
.summary-card--blue { background: #f0f7ff; }
.summary-card--green { background: #f0fff5; }
.summary-card--yellow { background: #fff9f1; }
.summary-card--cyan { background: #effbff; }
.summary-card--violet { background: #f2f2ff; }
.summary-card__icon {
  width: 2.3611rem;
  height: 2.3611rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.6944rem;
  background: #fff;
  color: #2563eb;
  font-weight: 700;
}
.summary-card__icon img {
  width: 1.6667rem;
  height: 1.6667rem;
}
.summary-card__label {
  color: rgba(105, 105, 105, 0.56);
  font-size: 0.8333rem;
  font-weight: 500;
}
.summary-card strong {
  color: #515151;
  font-size: 0.9722rem;
  font-weight: 600;
}
.summary-card ul {
  max-height: 7.5rem;
  margin: 0.1389rem 0 0;
  padding-left: 1.1111rem;
  overflow-y: auto;
  color: rgba(81, 81, 81, 0.75);
  font-size: 0.8333rem;
  line-height: 1.35;
}
.final-card {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 1.9444rem;
  padding: 2.3611rem;
  border-radius: 1.0417rem;
  color: #fff;
  background:
    radial-gradient(circle at 90% 12%, rgba(6, 181, 212, 0.34), transparent 28%),
    linear-gradient(135deg, #181f2f 0%, #26324a 100%);
}
.final-card__caption {
  margin-bottom: 0.8333rem;
  color: rgba(255, 255, 255, 0.58);
  font-size: 1.0417rem;
}
.final-switch {
  margin-top: 1.9444rem;
  color: #fff;
}
:global(.dark) .wizard-alert,
:global(.darkmode) .wizard-alert {
  background: rgba(239, 68, 68, 0.12);
  color: #fca5a5;
}
:global(.dark) .wizard-step-section::before,
:global(.darkmode) .wizard-step-section::before {
  background: rgba(255, 255, 255, 0.1);
}
:global(.dark) .wizard-step,
:global(.darkmode) .wizard-step,
:global(.dark) .wizard-panel,
:global(.darkmode) .wizard-panel {
  background: #2c2f3d;
}
:global(.dark) .wizard-step,
:global(.darkmode) .wizard-step {
  color: rgba(255, 255, 255, 0.7);
}
:global(.dark) .wizard-step__number,
:global(.darkmode) .wizard-step__number,
:global(.dark) .cs-arrow,
:global(.darkmode) .cs-arrow,
:global(.dark) .switch-row__control,
:global(.darkmode) .switch-row__control,
:global(.dark) .final-switch span,
:global(.darkmode) .final-switch span,
:global(.dark) .favorite-btn,
:global(.darkmode) .favorite-btn {
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.5);
}
:global(.dark) .wizard-step--active,
:global(.darkmode) .wizard-step--active {
  color: #67a8ff;
}
:global(.dark) .field-label,
:global(.darkmode) .field-label,
:global(.dark) .switch-row,
:global(.darkmode) .switch-row {
  color: rgba(255, 255, 255, 0.66);
}
:global(.dark) .platform-choice,
:global(.darkmode) .platform-choice,
:global(.dark) .cs-head,
:global(.darkmode) .cs-head,
:global(.dark) .cs-list,
:global(.darkmode) .cs-list,
:global(.dark) .wizard-input,
:global(.darkmode) .wizard-input,
:global(.dark) .secondary-btn,
:global(.darkmode) .secondary-btn,
:global(.dark) .small-btn,
:global(.darkmode) .small-btn {
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.72);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.1);
}
:global(.dark) .platform-choice:not(.platform-choice--active),
:global(.darkmode) .platform-choice:not(.platform-choice--active) {
  border-color: rgba(255, 255, 255, 0.1);
}
:global(.dark) .custom-select.open .cs-head,
:global(.darkmode) .custom-select.open .cs-head {
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.16);
}
:global(.dark) .cs-arrow path,
:global(.darkmode) .cs-arrow path {
  stroke: rgba(255, 255, 255, 0.65);
}
:global(.dark) .cs-option,
:global(.darkmode) .cs-option {
  color: rgba(255, 255, 255, 0.72);
}
:global(.dark) .cs-option:hover,
:global(.darkmode) .cs-option:hover {
  background: rgba(255, 255, 255, 0.06);
}
:global(.dark) .cs-option.selected,
:global(.darkmode) .cs-option.selected {
  background: rgba(255, 255, 255, 0.06);
}
:global(.dark) .wizard-input::placeholder,
:global(.darkmode) .wizard-input::placeholder {
  color: rgba(255, 255, 255, 0.35);
}
:global(.dark) .search-icon-circle,
:global(.darkmode) .search-icon-circle {
  background-color: rgba(255, 255, 255, 0.08);
}
:global(.dark) .search-input,
:global(.darkmode) .search-input {
  background-color: #2C2F3D;
  color: rgba(255, 255, 255, 0.95);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.12);
}
:global(.dark) .search-input::placeholder,
:global(.darkmode) .search-input::placeholder {
  color: rgba(255, 255, 255, 0.55);
}
:global(.dark) .ghost-btn,
:global(.darkmode) .ghost-btn,
:global(.dark) .status-pill,
:global(.darkmode) .status-pill,
:global(.dark) .select-tile,
:global(.darkmode) .select-tile {
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.68);
}
:global(.dark) .select-tile,
:global(.darkmode) .select-tile {
  border-color: rgba(255, 255, 255, 0.1);
}
:global(.dark) .panel-head h4,
:global(.darkmode) .panel-head h4,
:global(.dark) .soft-panel h4,
:global(.darkmode) .soft-panel h4,
:global(.dark) .select-tile__title,
:global(.darkmode) .select-tile__title {
  color: rgba(255, 255, 255, 0.86);
}
:global(.dark) .panel-head p,
:global(.darkmode) .panel-head p,
:global(.dark) .soft-panel p,
:global(.darkmode) .soft-panel p,
:global(.dark) .empty-line,
:global(.darkmode) .empty-line,
:global(.dark) .select-tile__meta,
:global(.darkmode) .select-tile__meta,
:global(.dark) .summary-card__label,
:global(.darkmode) .summary-card__label {
  color: rgba(255, 255, 255, 0.5);
}
:global(.dark) .select-tile__avatar,
:global(.darkmode) .select-tile__avatar,
:global(.dark) .select-tile__check,
:global(.darkmode) .select-tile__check,
:global(.dark) .select-tile__caption,
:global(.darkmode) .select-tile__caption,
:global(.dark) .summary-card__icon,
:global(.darkmode) .summary-card__icon {
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.65);
}
:global(.dark) .select-tile--active,
:global(.darkmode) .select-tile--active {
  border-color: rgba(103, 168, 255, 0.42);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.16);
}
:global(.dark) .platform-choice--active,
:global(.darkmode) .platform-choice--active {
  background: linear-gradient(270deg, #06b5d4 0.35%, #1f9de4 32.08%, #2563eb 96.51%) !important;
  color: #fff !important;
}
:global(.dark) .wizard-step--active .wizard-step__number,
:global(.darkmode) .wizard-step--active .wizard-step__number,
:global(.dark) .wizard-step--done .wizard-step__number,
:global(.darkmode) .wizard-step--done .wizard-step__number,
:global(.dark) .select-tile--active .select-tile__check,
:global(.darkmode) .select-tile--active .select-tile__check {
  background: #2563eb !important;
  color: #fff !important;
}
:global(.dark) .favorite-btn--active,
:global(.darkmode) .favorite-btn--active {
  background: #fa812e !important;
  color: #fff !important;
}
:global(.dark) .summary-card,
:global(.darkmode) .summary-card {
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.76);
}
:global(.dark) .summary-card strong,
:global(.darkmode) .summary-card strong {
  color: rgba(255, 255, 255, 0.88);
}
:global(.dark) .summary-card ul,
:global(.darkmode) .summary-card ul {
  color: rgba(255, 255, 255, 0.58);
}
@media (max-width: 767.25px) {
  .wizard-grid,
  .summary-grid {
    grid-template-columns: 1fr;
  }
  .panel-head {
    align-items: flex-start;
    flex-direction: column;
  }
  .search-wrap,
  .search-input {
    width: 100%;
  }
  .soft-panel,
  .final-card,
  .wizard-actions {
    align-items: stretch;
    flex-direction: column;
  }
  .wizard-actions__right {
    justify-content: flex-end;
  }
}
@media (max-width: 480px) {
  .wizard-step {
    width: 100%;
    min-width: 0;
  }
  .wizard-content {
    padding-left: 0;
  }
  .wizard-step-section::before {
    display: none;
  }
  .wizard-panel,
  .channel-card,
  .final-card {
    padding: 1.5278rem;
  }
  .wizard-actions__right {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
