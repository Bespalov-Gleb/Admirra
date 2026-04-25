<template>
  <div class="admirra-page-wrapper">
    <section class="main-section">

      <div class="section-header pt-4 mt-1">
        <h3 class="heading-3 mb-2">Новая интеграция</h3>
        <p class="section-header__descrp">Добавление рекламного канала</p>
      </div>

      <!-- Ошибка -->
      <div v-if="error" class="alert _danger mb-4">
        <div class="alert__inner">{{ error }}</div>
      </div>

      <div class="steps-track mb-4">

        <!-- ===== ШАГ 1: ПРОЕКТ ===== -->
        <section :class="['steps-track__section', { '_active': step === 1 }]">
          <div class="steps-track__header">
            <div class="steps-track__marker" :style="markerStyle(1)">
              <div class="steps-track__marker-text" :style="markerTextStyle(1)">1</div>
            </div>
            <div class="steps-track__caption" :style="captionStyle(1)">Проект</div>
          </div>

          <div v-if="step === 1" class="steps-track__content">
            <div class="row g-4">
              <!-- Настройки -->
              <div class="col-sm-6 col-md-5 col-lg-4 col-xxl-3">
                <div class="h-100 p-5 bg-white radius-base d-flex flex-column">

                  <!-- Выбор платформы -->
                  <div class="weight-500 gray mb-3">Рекламный канал</div>
                  <div class="row g-3 mb-4">
                    <div class="col-12">
                      <button
                        :class="['btn w-100', form.platform === 'YANDEX_DIRECT' ? '_primary' : '_white']"
                        @click="form.platform = 'YANDEX_DIRECT'"
                      >
                        <div class="btn__inner">
                          <img width="20" src="/admirra/img/icons/yandex-direct.png" alt="Yandex" class="me-2" />
                          <span class="btn__text">Yandex Direct</span>
                        </div>
                      </button>
                    </div>
                    <div class="col-12">
                      <button
                        :class="['btn w-100', form.platform === 'VK_ADS' ? '_primary' : '_white']"
                        @click="form.platform = 'VK_ADS'"
                      >
                        <div class="btn__inner">
                          <img width="20" src="/admirra/img/icons/vk-ads.png" alt="VK" class="me-2" />
                          <span class="btn__text">VK Ads</span>
                        </div>
                      </button>
                    </div>
                  </div>

                  <!-- Выбор проекта -->
                  <div class="weight-500 gray mb-2">Проект</div>
                  <select
                    class="select-light wide mb-3 integration-select"
                    v-model="form.client_id"
                  >
                    <option value="">— Выберите проект —</option>
                    <option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</option>
                  </select>

                  <!-- Или создать новый -->
                  <div class="py-3">
                    <label class="switches _light _big">
                      <input
                        class="switches__input"
                        type="checkbox"
                        v-model="isNewProject"
                      />
                      <span class="switches__text">Создать новый проект</span>
                      <span class="switches__indicator"></span>
                    </label>
                  </div>
                  <input
                    v-if="isNewProject"
                    class="input mb-3"
                    type="text"
                    placeholder="Название нового проекта"
                    v-model="form.client_name"
                  />

                  <div class="mt-auto">
                    <button
                      :class="['btn d-flex w-100', form.platform === 'YANDEX_DIRECT' ? '' : '_vk']"
                      :disabled="loadingAuth"
                      @click="handleConnectClick"
                    >
                      <div class="btn__inner">
                        <span class="btn__text">
                          {{ loadingAuth ? 'Перенаправление...' : (form.platform === 'YANDEX_DIRECT' ? 'Подключить Яндекс Директ' : 'Подключить VK Ads') }}
                        </span>
                      </div>
                    </button>
                  </div>
                </div>
              </div>

              <!-- Инфо-карточка платформы -->
              <div class="col-sm-12 col-md col-xl-auto">
                <div class="dark-bg">
                  <div class="dark-bg__inner p-5">
                    <div class="mb-4">
                      <img
                        width="40"
                        :src="form.platform === 'YANDEX_DIRECT' ? '/admirra/img/icons/yandex-direct.png' : '/admirra/img/icons/vk-ads.png'"
                        alt="#"
                      />
                    </div>
                    <h4 class="heading-4 pe-5 lh-120 weight-500 mb-3">
                      {{ form.platform === 'YANDEX_DIRECT' ? 'Интеграция с Яндекс.Директ' : 'Интеграция с VK Ads' }}
                    </h4>
                    <p class="silver weight-300 text-15 lh-135 mb-4">
                      Автоматический сбор кампаний,<br />ключевых слов и статистики
                    </p>
                    <div class="mt-auto">
                      <div class="row g-2">
                        <div class="col">
                          <div class="alert-dark">
                            <div class="alert-dark__inner">
                              <div class="dotty _success"></div>
                              <span>API: СОЕДИНЕНО</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div class="dark-bg__light _pos1"><div class="lightBlurBg _xl"></div></div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- ===== ШАГ 2: ПРОФИЛЬ ===== -->
        <section :class="['steps-track__section', { '_active': step === 2 }]">
          <div class="steps-track__header">
            <div class="steps-track__marker" :style="markerStyle(2)">
              <div class="steps-track__marker-text" :style="markerTextStyle(2)">2</div>
            </div>
            <div class="steps-track__caption" :style="captionStyle(2)">Профиль</div>
          </div>

          <div v-if="step === 2" class="steps-track__content">
            <div class="p-5 bg-white radius-base mb-4">
              <div class="mb-5">
                <h5 class="heading-5 weight-500">Выберите рекламный кабинет для интеграции</h5>
              </div>

              <div v-if="loadingStates.profiles" class="py-4 gray56">Загрузка профилей...</div>

              <div v-else-if="profiles.length === 0" class="py-4 gray56">
                Нет доступных профилей. Проверьте авторизацию.
              </div>

              <div v-else class="row g-4">
                <div v-for="cabinet in profiles" :key="cabinet.login" class="col col-sm-auto">
                  <div class="select-card">
                    <input
                      class="select-card__input"
                      type="radio"
                      name="card-ads"
                      :value="cabinet.login"
                      :checked="form.account_id === cabinet.login"
                      @change="selectProfile(cabinet)"
                    />
                    <div class="select-card__inner">
                      <div class="select-card__header">
                        <div class="avatar-30x30">
                          <img
                            class="img-cover"
                            :src="form.platform === 'YANDEX_DIRECT' ? '/admirra/img/icons/yandex-direct.png' : '/admirra/img/icons/vk-ads.png'"
                            alt="#"
                          />
                        </div>
                        <div class="select-card__check">
                          <svg><use href="/admirra/img/svg/sprite.svg#check"></use></svg>
                        </div>
                      </div>
                      <div class="select-card__content">
                        <div class="weight-500">
                          <div class="gray500 text-15 mb-1">{{ cabinet.name || cabinet.login }}</div>
                          <div class="silver uppercase">{{ cabinet.login }}</div>
                        </div>
                        <div class="mt-auto">
                          <div class="caption">{{ cabinet.type || 'Рекламный кабинет' }}</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div class="row g-3 pt-2">
              <div class="col">
                <button class="btn _white" @click="step = 1">
                  <div class="btn__inner">
                    <div class="btn__icon-info">
                      <svg class="prev"><use href="/admirra/img/svg/sprite.svg#arrow"></use></svg>
                    </div>
                    <span class="btn__text">Назад</span>
                  </div>
                </button>
              </div>
              <div class="col-auto">
                <div class="row">
                  <div class="col-auto">
                    <button class="btn _outline-gray" @click="handleCancel">
                      <div class="btn__inner"><span class="btn__text">Отмена</span></div>
                    </button>
                  </div>
                  <div class="col-auto">
                    <button
                      class="btn _primary"
                      :disabled="!form.account_id || loadingStates.profiles"
                      @click="goToStep3"
                    >
                      <div class="btn__inner">
                        <span class="btn__text">Далее</span>
                        <div class="btn__icon-info">
                          <svg class="next"><use href="/admirra/img/svg/sprite.svg#arrow"></use></svg>
                        </div>
                      </div>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- ===== ШАГ 3: СЧЕТЧИКИ И ЦЕЛИ ===== -->
        <section :class="['steps-track__section', { '_active': step === 3 }]">
          <div class="steps-track__header">
            <div class="steps-track__marker" :style="markerStyle(3)">
              <div class="steps-track__marker-text" :style="markerTextStyle(3)">3</div>
            </div>
            <div class="steps-track__caption" :style="captionStyle(3)">Счетчики и цели</div>
          </div>

          <div v-if="step === 3" class="steps-track__content">

            <!-- Кампании -->
            <div class="p-5 bg-white radius-base mb-5">
              <div class="mb-5">
                <h5 class="heading-5 weight-500">Рекламные кампании</h5>
                <p class="pt-3 text-15 weight-500 gray56">Выберите кампании для отслеживания</p>
              </div>
              <div v-if="loadingStates.campaigns" class="py-4 gray56">Загрузка кампаний...</div>
              <div v-else-if="campaigns.length === 0" class="py-4 gray56">Нет доступных кампаний.</div>
              <div v-else class="row g-3">
                <div class="col-12">
                  <label class="choise-checkbox">
                    <input
                      class="choise-checkbox__input"
                      type="checkbox"
                      :checked="allFromProfile"
                      @change="allFromProfile = $event.target.checked; selectedCampaignIds = $event.target.checked ? campaigns.map(c => c.id) : []"
                    />
                    <span class="choise-checkbox__box">
                      <svg><use href="/admirra/img/svg/sprite.svg#check"></use></svg>
                    </span>
                    <span class="ps-2 weight-500 gray">Выбрать все</span>
                  </label>
                </div>
                <div
                  v-for="campaign in campaigns"
                  :key="campaign.id"
                  class="col-12 col-sm-6 col-md-4"
                >
                  <label class="choise-checkbox d-flex align-items-center">
                    <input
                      class="choise-checkbox__input"
                      type="checkbox"
                      :checked="selectedCampaignIds.includes(campaign.id)"
                      @change="toggleCampaignSelection(campaign.id)"
                    />
                    <span class="choise-checkbox__box">
                      <svg><use href="/admirra/img/svg/sprite.svg#check"></use></svg>
                    </span>
                    <span class="ps-2 text-13 gray">{{ campaign.name || campaign.external_id }}</span>
                  </label>
                </div>
              </div>
            </div>

            <!-- Счетчики метрики (только для Яндекс) -->
            <div v-if="form.platform === 'YANDEX_DIRECT'" class="p-5 bg-white radius-base mb-5">
              <div class="mb-5">
                <h5 class="heading-5 weight-500">Счетчики метрики</h5>
                <p class="pt-3 text-15 weight-500 gray56">Выберите счетчики для отслеживания целей</p>
              </div>
              <div v-if="loadingStates.counters" class="py-4 gray56">Загрузка счетчиков...</div>
              <div v-else-if="counters.length === 0" class="py-4 gray56">Нет доступных счетчиков.</div>
              <div v-else class="row g-4">
                <div
                  v-for="counter in counters"
                  :key="counter.id"
                  class="col-12 col-sm-6 col-md-auto"
                >
                  <div class="select-card">
                    <input
                      class="select-card__input"
                      type="checkbox"
                      :checked="selectedCounterIds.includes(counter.id)"
                      @change="toggleCounterSelection(counter.id)"
                    />
                    <div class="select-card__inner">
                      <div class="select-card__header">
                        <div class="avatar-30x30">
                          <div class="avatar-text">{{ (counter.name || '?').slice(0,2).toUpperCase() }}</div>
                        </div>
                        <div class="select-card__check">
                          <svg><use href="/admirra/img/svg/sprite.svg#check"></use></svg>
                        </div>
                      </div>
                      <div class="select-card__content _width-normal">
                        <div class="weight-500">
                          <div class="gray500 text-15 mb-1">{{ counter.name }}</div>
                          <div class="silver uppercase">ID: {{ counter.id }}</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Цели (только для Яндекс) -->
            <div v-if="form.platform === 'YANDEX_DIRECT'" class="p-5 bg-white radius-base mb-5">
              <div class="mb-5">
                <h5 class="heading-5 weight-500">Цели и конверсии</h5>
                <p class="pt-3 text-15 weight-500 gray56">Выберите основную цель (★) и дополнительные</p>
              </div>
              <div v-if="loadingStates.goals" class="py-4 gray56">Загрузка целей...</div>
              <div v-else-if="goals.length === 0" class="py-4 gray56">Нет доступных целей.</div>
              <div v-else class="row g-4">
                <div
                  v-for="goal in goals"
                  :key="goal.id"
                  class="col-12 col-sm-6 col-md-auto"
                >
                  <div :class="['select-card', form.primary_goal_id === goal.id ? '_selected' : '']">
                    <input
                      class="select-card__input"
                      type="checkbox"
                      :checked="selectedGoalIds.includes(goal.id) || form.primary_goal_id === goal.id"
                      @change="toggleGoalSelection(goal.id)"
                    />
                    <div class="select-card__inner">
                      <div class="select-card__header">
                        <div class="avatar-30x30">
                          <div class="avatar-text">{{ (goal.name || '?').slice(0,2).toUpperCase() }}</div>
                        </div>
                        <div class="select-card__check">
                          <svg><use href="/admirra/img/svg/sprite.svg#check"></use></svg>
                        </div>
                      </div>
                      <div class="select-card__content _width-normal">
                        <div class="weight-500">
                          <div class="gray500 text-15 mb-1">{{ goal.name }}</div>
                          <div class="silver uppercase">ID: {{ goal.id }}</div>
                        </div>
                        <div class="row align-items-end mt-auto">
                          <div class="col">
                            <div class="caption">{{ goal.type || '' }}</div>
                          </div>
                          <div class="col-auto">
                            <button
                              type="button"
                              class="select-card__favorites"
                              @click.stop="selectPrimaryGoal(goal.id)"
                              :title="form.primary_goal_id === goal.id ? 'Основная цель' : 'Сделать основной'"
                            >
                              <svg :class="{ active: form.primary_goal_id === goal.id }">
                                <use href="/admirra/img/svg/sprite.svg#star"></use>
                              </svg>
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div class="row g-3">
              <div class="col">
                <button class="btn _white" @click="step = 2">
                  <div class="btn__inner">
                    <div class="btn__icon-info">
                      <svg class="prev"><use href="/admirra/img/svg/sprite.svg#arrow"></use></svg>
                    </div>
                    <span class="btn__text">Назад</span>
                  </div>
                </button>
              </div>
              <div class="col-auto">
                <div class="row">
                  <div class="col-auto">
                    <button class="btn _outline-gray" @click="handleCancel">
                      <div class="btn__inner"><span class="btn__text">Отмена</span></div>
                    </button>
                  </div>
                  <div class="col-auto">
                    <button class="btn _primary" @click="goToStep4">
                      <div class="btn__inner">
                        <span class="btn__text">Далее</span>
                        <div class="btn__icon-info">
                          <svg class="next"><use href="/admirra/img/svg/sprite.svg#arrow"></use></svg>
                        </div>
                      </div>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- ===== ШАГ 4: СВОДКА ===== -->
        <section :class="['steps-track__section', { '_active': step === 4 }]">
          <div class="steps-track__header">
            <div class="steps-track__marker" :style="markerStyle(4)">
              <div class="steps-track__marker-text" :style="markerTextStyle(4)">4</div>
            </div>
            <div class="steps-track__caption" :style="captionStyle(4)">Сводка</div>
          </div>

          <div v-if="step === 4" class="steps-track__content">
            <div class="p-5 bg-white radius-base mb-5">
              <div class="mb-5">
                <h5 class="heading-5 weight-500">Сводка интеграции</h5>
                <p class="pt-3 text-15 weight-500 gray56">Проверьте настройки перед подключением</p>
              </div>
              <div class="row g-4">
                <div class="col-12 col-md-6">
                  <div class="card-info _blue">
                    <div class="card-info__header">
                      <div class="iconbox _md _radius">
                        <img
                          width="24"
                          :src="form.platform === 'YANDEX_DIRECT' ? '/admirra/img/icons/yandex-direct.png' : '/admirra/img/icons/vk-ads.png'"
                          alt="#"
                        />
                      </div>
                      <div class="text-15 weight-500">
                        <h6 class="card-info__title">Платформа</h6>
                        <p class="gray500 pt-2">{{ form.platform === 'YANDEX_DIRECT' ? 'Yandex Direct' : 'VK Ads' }}</p>
                      </div>
                    </div>
                  </div>
                </div>
                <div class="col-12 col-md-6">
                  <div class="card-info _green">
                    <div class="card-info__header">
                      <div class="iconbox _md _radius">
                        <svg><use href="/admirra/img/svg/sprite.svg#diagrama"></use></svg>
                      </div>
                      <div class="text-15 weight-500">
                        <h6 class="card-info__title">Кампании</h6>
                        <p class="gray500 pt-2">
                          {{ allFromProfile ? 'Все кампании' : `Выбрано: ${selectedCampaignIds.length}` }}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
                <div v-if="form.platform === 'YANDEX_DIRECT'" class="col-12 col-md-6">
                  <div class="card-info _oldlace">
                    <div class="card-info__header">
                      <div class="iconbox _md _radius">
                        <svg><use href="/admirra/img/svg/sprite.svg#wallet"></use></svg>
                      </div>
                      <div class="text-15 weight-500">
                        <h6 class="card-info__title">Счетчики</h6>
                        <p class="gray500 pt-2">Выбрано: {{ selectedCounterIds.length }}</p>
                      </div>
                    </div>
                  </div>
                </div>
                <div v-if="form.platform === 'YANDEX_DIRECT' && form.primary_goal_id" class="col-12 col-md-6">
                  <div class="card-info _aliceblue">
                    <div class="card-info__header">
                      <div class="iconbox _md _radius">
                        <svg><use href="/admirra/img/svg/sprite.svg#star"></use></svg>
                      </div>
                      <div class="text-15 weight-500">
                        <h6 class="card-info__title">Основная цель</h6>
                        <p class="gray500 pt-2">
                          {{ goals.find(g => g.id === form.primary_goal_id)?.name || form.primary_goal_id }}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Дарк-блок финала -->
            <div class="dark-bg mb-5">
              <div class="dark-bg__inner p-5">
                <div class="row g-4">
                  <div class="col-12 col-lg">
                    <div class="row mb-5">
                      <div class="col-auto">
                        <div class="iconbox _white _lg">
                          <svg><use href="/admirra/img/svg/sprite.svg#refresh-line"></use></svg>
                        </div>
                      </div>
                      <div class="col">
                        <div class="silver weight-300 text-15 mb-3">Автосинхронизация</div>
                        <h4 class="heading-4 weight-600">Данные будут обновляться каждые 24 часа</h4>
                      </div>
                    </div>
                    <div class="row align-items-center">
                      <div class="col-auto">
                        <label class="switches _white _normal">
                          <input class="switches__input" type="checkbox" checked />
                          <span class="switches__indicator"></span>
                        </label>
                      </div>
                      <div class="col">
                        <label class="text-15 weight-500">Включить автосинхронизацию</label>
                      </div>
                    </div>
                  </div>
                  <div class="col-12 col-lg-auto align-self-end">
                    <div class="py-3 mb-2">
                      <div class="silver weight-300 text-15">Готово к подключению</div>
                    </div>
                    <div class="alert-dark _md w-100">
                      <div class="alert-dark__inner">
                        <div class="dotty _success"></div>
                        <span class="weight-700 uppercase">Готовность 100%</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div class="dark-bg__light _pos1"><div class="lightBlurBg _xl"></div></div>
            </div>

            <div class="row g-3">
              <div class="col">
                <button class="btn _white" @click="step = 3">
                  <div class="btn__inner">
                    <div class="btn__icon-info">
                      <svg class="prev"><use href="/admirra/img/svg/sprite.svg#arrow"></use></svg>
                    </div>
                    <span class="btn__text">Назад</span>
                  </div>
                </button>
              </div>
              <div class="col-auto">
                <div class="row">
                  <div class="col-auto">
                    <button class="btn _outline-gray" @click="handleCancel">
                      <div class="btn__inner"><span class="btn__text">Отмена</span></div>
                    </button>
                  </div>
                  <div class="col-auto">
                    <button
                      class="btn _primary"
                      :disabled="loadingStates.finish"
                      @click="doFinish"
                    >
                      <div class="btn__inner">
                        <span class="btn__text">{{ loadingStates.finish ? 'Сохранение...' : 'Подключить' }}</span>
                        <div class="btn__icon">
                          <svg><use href="/admirra/img/svg/sprite.svg#refresh-line"></use></svg>
                        </div>
                      </div>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
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
  toggleCampaignSelection,
  toggleCounterSelection,
  selectPrimaryGoal
} = useIntegrationWizard()

const step = ref(1)
const isNewProject = ref(false)
const loadingAuth = ref(false)

onMounted(async () => {
  await fetchProjects()

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
  } else {
    form.client_name = ''
  }
})

const markerStyle = (idx) => (
  step.value === idx
    ? 'background:#cfdef9 !important; border:0.4rem solid #e1eaf9 !important;'
    : 'background:#edeff1 !important; border:0.4rem solid #f1f3f5 !important;'
)

const markerTextStyle = (idx) => (
  step.value === idx
    ? 'background:#2e6bff !important; color:#fff !important; opacity:1 !important;'
    : 'background:#fff !important; color:rgba(105,105,105,.56) !important; opacity:1 !important;'
)

const captionStyle = (idx) => (
  step.value === idx
    ? 'color:#2e6bff !important;'
    : 'color:rgba(105,105,105,.75) !important;'
)

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
  fetchCampaigns(lastIntegrationId.value)
  if (form.platform === 'YANDEX_DIRECT') {
    fetchCounters(lastIntegrationId.value)
  }
}

const goToStep4 = () => {
  if (selectedCampaignIds.value.length === 0 && !allFromProfile.value) {
    error.value = 'Выберите хотя бы одну кампанию'
    return
  }
  if (form.platform === 'YANDEX_DIRECT') {
    fetchGoals(lastIntegrationId.value)
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
      all_campaigns: allFromProfile.value,
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

const toggleGoalSelection = (id) => {
  const idx = selectedGoalIds.value.indexOf(id)
  if (idx > -1) selectedGoalIds.value.splice(idx, 1)
  else selectedGoalIds.value.push(id)
}
</script>

<style scoped>
.admirra-page-wrapper { }
.btn._vk { background: linear-gradient(135deg, #0077ff, #005fcc); color: #fff; }

/* Селект проекта в стиле интерфейса */
.integration-select {
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
  width: 100%;
  height: 44px;
  padding: 0 38px 0 14px;
  border-radius: 12px;
  border: 1px solid rgba(44, 44, 44, 0.12);
  background-color: #ffffff;
  color: #2c2c2c;
  font-size: 14px;
  font-weight: 500;
  line-height: 1;
  outline: none;
  transition: border-color .2s ease, box-shadow .2s ease, background-color .2s ease;
  background-image:
    linear-gradient(45deg, transparent 50%, #7c8597 50%),
    linear-gradient(135deg, #7c8597 50%, transparent 50%);
  background-position:
    calc(100% - 18px) calc(50% - 2px),
    calc(100% - 13px) calc(50% - 2px);
  background-size: 5px 5px, 5px 5px;
  background-repeat: no-repeat;
}

.integration-select:hover {
  border-color: rgba(46, 107, 255, 0.35);
}

.integration-select:focus {
  border-color: #2e6bff;
  box-shadow: 0 0 0 3px rgba(46, 107, 255, 0.15);
}

.integration-select option {
  color: #2c2c2c;
  background: #ffffff;
}

/* В треке шагов подсвечиваем только активный шаг */
:deep(.steps-track__section .steps-track__marker) {
  background: rgba(167, 179, 198, 0.2) !important;
}

:deep(.steps-track__section .steps-track__marker-text) {
  color: rgba(88, 102, 126, 0.95) !important;
  opacity: 1 !important;
}

:deep(.steps-track__section .steps-track__caption) {
  color: rgba(105, 105, 105, 0.75) !important;
}

/* Даже если где-то остается _completed, делаем его визуально неактивным */
:deep(.steps-track__section._completed .steps-track__marker) {
  background: rgba(167, 179, 198, 0.2) !important;
}

:deep(.steps-track__section._completed .steps-track__marker-text) {
  color: rgba(88, 102, 126, 0.95) !important;
  opacity: 1 !important;
}

:deep(.steps-track__section._completed .steps-track__caption) {
  color: rgba(105, 105, 105, 0.75) !important;
}

:deep(.steps-track__section._active .steps-track__marker) {
  background: linear-gradient(135deg, #2e6bff, #06b5d4);
}

:deep(.steps-track__section._active .steps-track__marker-text) {
  color: #fff;
}

:deep(.steps-track__section._active .steps-track__caption) {
  color: #2e6bff;
}
</style>
