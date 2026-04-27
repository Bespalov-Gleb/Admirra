<template>
  <div class="admirra-page-wrapper">
    <section class="main-section">
      <div class="section-header pt-4 mt-1">
        <h3 class="heading-3 mb-2">{{ title }}</h3>
        <p class="section-header__descrp">{{ subtitle }}</p>
      </div>
      <div class="steps-track mb-4">
        <section class="steps-track__section">
          <div class="steps-track__header">
            <div class="steps-track__marker">
              <div class="steps-track__marker-text">1</div>
            </div>
            <div class="steps-track__caption">Проект</div>
          </div>
          <div class="steps-track__content">
            <div class="row g-4">
              <div class="col-sm-6 col-md-5 col-lg-4 col-xxl-3">
                <div class="h-100 p-5 bg-white radius-base d-flex flex-column">
                  <div class="weight-500 gray mb-3">{{ historyDepthLabel }}</div>
                  <select class="select-light wide mb-1" @change="$emit('update:historyDepth', $event.target.value)">
                    <option v-for="opt in historyDepthOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
                  </select>
                  <div class="py-4 mb-2">
                    <div class="weight-500 gray mb-3">{{ autoSyncLabel }}</div>
                    <label class="switches _light _big">
                      <input class="switches__input" type="checkbox" :checked="autoSync" @change="$emit('update:autoSync', $event.target.checked)" />
                      <span class="switches__text">24/7</span>
                      <span class="switches__indicator"></span>
                    </label>
                  </div>
                  <div class="mt-auto">
                    <button class="btn d-flex w-100" @click="$emit('connect')">
                      <div class="btn__inner">
                        <span class="btn__text">{{ connectButtonLabel }}</span>
                      </div>
                    </button>
                  </div>
                </div>
              </div>
              <div class="col-sm-12 col-md col-xl-auto">
                <div class="dark-bg">
                  <div class="dark-bg__inner p-5">
                    <div class="mb-4">
                      <img width="40" :src="platformIcon" alt="#" />
                    </div>
                    <h4 class="heading-4 pe-5 lh-120 weight-500 mb-3">{{ platformTitle }}</h4>
                    <p class="silver weight-300 text-15 lh-135 mb-4" v-html="platformDescription"></p>
                    <div class="mt-auto">
                      <div class="row g-2">
                        <div class="col">
                          <div class="alert-dark">
                            <div class="alert-dark__inner">
                              <div :class="['dotty', apiStatusClass]"></div>
                              <span>API:&nbsp;{{ apiStatusLabel }}</span>
                            </div>
                          </div>
                        </div>
                        <div class="col-auto">
                          <button class="btn _outline" @click="$emit('how-it-works')">
                            <div class="btn__inner">
                              <span class="btn__text">{{ howItWorksLabel }}</span>
                            </div>
                          </button>
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
        <section class="steps-track__section">
          <div class="steps-track__header">
            <div class="steps-track__marker">
              <div class="steps-track__marker-text">2</div>
            </div>
            <div class="steps-track__caption">Профиль</div>
          </div>
          <div class="steps-track__content">
            <div class="p-5 bg-white radius-base mb-4">
              <div class="mb-5">
                <h5 class="heading-5 weight-500">{{ selectCabinetLabel }}</h5>
              </div>
              <div class="row g-4">
                <div v-for="(cabinet, idx) in cabinets" :key="idx" class="col col-sm-auto">
                  <div class="select-card">
                    <input 
                      class="select-card__input" 
                      type="radio" 
                      name="card-ads" 
                      :value="cabinet.id" 
                      :checked="selectedCabinet === cabinet.id"
                      @change="$emit('update:selectedCabinet', cabinet.id)"
                    />
                    <div class="select-card__inner">
                      <div class="select-card__header">
                        <div class="avatar-30x30">
                          <img class="img-cover" :src="cabinet.icon" alt="#" />
                        </div>
                        <div class="select-card__check">
                          <svg><use :href="checkIcon"></use></svg>
                        </div>
                      </div>
                      <div class="select-card__content">
                        <div class="weight-500">
                          <div class="gray500 text-15 mb-1">{{ cabinet.name }}</div>
                          <div class="silver uppercase">{{ cabinet.login }}</div>
                        </div>
                        <div class="mt-auto">
                          <div class="caption">{{ cabinet.type }}</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div class="row g-3 pt-2">
              <div class="col">
                <button class="btn _white" @click="$emit('back')">
                  <div class="btn__inner">
                    <div class="btn__icon-info">
                      <svg class="prev"><use :href="arrowIcon"></use></svg>
                    </div>
                    <span class="btn__text">Назад</span>
                  </div>
                </button>
              </div>
              <div class="col-auto">
                <div class="row">
                  <div class="col-auto">
                    <button class="btn _outline-gray" @click="$emit('cancel')">
                      <div class="btn__inner">
                        <span class="btn__text">Отмена</span>
                      </div>
                    </button>
                  </div>
                  <div class="col-auto">
                    <button class="btn _primary" @click="$emit('next')">
                      <div class="btn__inner">
                        <span class="btn__text">Далее</span>
                        <div class="btn__icon-info">
                          <svg class="next"><use :href="arrowIcon"></use></svg>
                        </div>
                      </div>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
        <section class="steps-track__section">
          <div class="steps-track__header">
            <div class="steps-track__marker">
              <div class="steps-track__marker-text">3</div>
            </div>
            <div class="steps-track__caption">Счетчики и цели</div>
          </div>
        </section>
      </div>
    </section>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'

defineProps({
  title: { type: String, default: 'Новая интеграция' },
  subtitle: { type: String, default: 'Добавление рекламного канала' },
  historyDepthLabel: { type: String, default: 'Глубина истории' },
  historyDepthOptions: {
    type: Array,
    default: () => [
      { value: 'all', label: 'Все' },
      { value: '1', label: 'Вариант 1' }
    ]
  },
  autoSyncLabel: { type: String, default: 'Автосинхронизация' },
  autoSync: { type: Boolean, default: true },
  connectButtonLabel: { type: String, default: 'Подключить Яндекс Директ' },
  platformTitle: { type: String, default: 'Интеграция с Яндекс.Директ' },
  platformDescription: { type: String, default: 'Автоматический сбор кампаний, <br /> ключевых слов и статистики' },
  platformIcon: { type: String, default: '/admirra/img/yandex-direct.png' },
  apiStatusLabel: { type: String, default: 'СОЕДИНЕНО' },
  apiStatusClass: { type: String, default: '_success' },
  howItWorksLabel: { type: String, default: 'Как это работает?' },
  selectCabinetLabel: { type: String, default: 'Выберите рекламный кабинет для интеграции' },
  cabinets: {
    type: Array,
    default: () => [
      { id: 1, name: 'Иван Иванов', login: 'LOGINAKKAUNTA', type: 'Личный', icon: '/admirra/img/icons/yandex-direct.png' }
    ]
  },
  selectedCabinet: { type: [Number, String], default: null },
  arrowIcon: { type: String, default: '/admirra/img/svg/sprite.svg#arrow' },
  checkIcon: { type: String, default: '/admirra/img/svg/sprite.svg#check' }
})

defineEmits(['update:historyDepth', 'update:autoSync', 'connect', 'how-it-works', 'update:selectedCabinet', 'back', 'cancel', 'next'])

onMounted(() => {
  setTimeout(() => {
    if (window.jQuery) {
      window.jQuery('select').niceSelect('destroy')
      window.jQuery('select').niceSelect()
    }
  }, 100)
})
</script>

<style scoped>
.admirra-page-wrapper {
  /* Scoped styles */
}
</style>
