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
            <div class="steps-track__caption">{{ step1Title }}</div>
          </div>
          <div class="steps-track__content">
            <div class="row g-4">
              <div class="col-sm-6 col-md-5 col-lg-4 col-xxl-3">
                <div class="h-100 p-5 bg-white radius-base d-flex flex-column">
                  <div class="weight-500 gray mb-3">{{ historyDepthLabel }}</div>
                  <select class="select-light wide mb-1" @change="$emit('update:historyDepth', $event.target.value)">
                    <option v-for="opt in historyOptions" :key="opt.value" :value="opt.value">
                      {{ opt.label }}
                    </option>
                  </select>
                  <div class="py-4 mb-2">
                    <div class="weight-500 gray mb-3">{{ syncLabel }}</div>
                    <label class="switches _light _big">
                      <input 
                        class="switches__input" 
                        type="checkbox" 
                        :checked="autoSync" 
                        @change="$emit('update:autoSync', $event.target.checked)"
                      />
                      <span class="switches__text">{{ syncText }}</span>
                      <span class="switches__indicator"></span>
                    </label>
                  </div>
                  <div class="mt-auto">
                    <button class="btn d-flex" @click="$emit('connect')">
                      <div class="btn__inner">
                        <span class="btn__text">{{ connectButtonText }}</span>
                      </div>
                    </button>
                  </div>
                </div>
              </div>
              <div class="col-sm-12 col-md col-xl-auto">
                <div class="dark-bg">
                  <div class="dark-bg__inner p-5">
                    <div class="mb-4">
                      <img width="40" :src="channelIcon" alt="#" />
                    </div>
                    <h4 class="heading-4 pe-5 lh-120 weight-500 mb-3">{{ channelTitle }}</h4>
                    <p class="silver weight-300 text-15 lh-135 mb-4" v-html="channelDescription"></p>
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
                              <span class="btn__text">{{ howItWorksText }}</span>
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
            <div class="steps-track__caption">{{ step2Title }}</div>
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
  step1Title: { type: String, default: 'Проект' },
  step2Title: { type: String, default: 'Профиль' },
  historyDepthLabel: { type: String, default: 'Глубина истории' },
  historyOptions: {
    type: Array,
    default: () => [
      { value: 'all', label: 'Все' },
      { value: '1', label: '1 месяц' },
      { value: '2', label: '3 месяца' }
    ]
  },
  historyDepth: { type: String, default: 'all' },
  syncLabel: { type: String, default: 'Автосинхронизация' },
  syncText: { type: String, default: '24/7' },
  autoSync: { type: Boolean, default: true },
  connectButtonText: { type: String, default: 'Подключить Яндекс Директ' },
  channelIcon: { type: String, default: '/admirra/img/yandex-direct.png' },
  channelTitle: { type: String, default: 'Интеграция с Яндекс.Директ' },
  channelDescription: { type: String, default: 'Автоматический сбор кампаний, <br /> ключевых слов и статистики' },
  apiStatusLabel: { type: String, default: 'СОЕДИНЕНО' },
  apiStatusClass: { type: String, default: '_success' },
  howItWorksText: { type: String, default: 'Как это работает?' }
})

defineEmits(['update:historyDepth', 'update:autoSync', 'connect', 'how-it-works'])

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
