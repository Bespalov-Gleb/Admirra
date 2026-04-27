<template>
  <div class="admirra-page-wrapper">
    <section class="main-section">
      <div class="section-header pt-4 mt-1">
        <h3 class="heading-3 mb-2">{{ title }}</h3>
        <p class="section-header__descrp">{{ subtitle }}</p>
      </div>
      <div class="steps-track mb-4">
        <!-- Секции 1, 2, 3 (сокращенно) -->
        <section class="steps-track__section _completed">
          <div class="steps-track__header">
            <div class="steps-track__marker"><div class="steps-track__marker-text">1</div></div>
            <div class="steps-track__caption">Проект</div>
          </div>
        </section>
        <section class="steps-track__section _completed">
          <div class="steps-track__header">
            <div class="steps-track__marker"><div class="steps-track__marker-text">2</div></div>
            <div class="steps-track__caption">Профиль</div>
          </div>
        </section>
        <section class="steps-track__section _completed">
          <div class="steps-track__header">
            <div class="steps-track__marker"><div class="steps-track__marker-text">3</div></div>
            <div class="steps-track__caption">Счетчики и цели</div>
          </div>
        </section>

        <section class="steps-track__section">
          <div class="steps-track__header">
            <div class="steps-track__marker">
              <div class="steps-track__marker-text">4</div>
            </div>
            <div class="steps-track__caption">Сводка</div>
          </div>
          <div class="steps-track__content">
            <div class="p-5 bg-white radius-base mb-5">
              <div class="mb-5">
                <h5 class="heading-5 weight-500">{{ summaryTitle }}</h5>
                <p class="pt-3 text-15 weight-500 gray56">{{ summarySubtitle }}</p>
              </div>
              <div class="row g-4">
                <div v-for="(info, idx) in summaryCards" :key="idx" class="col-12 col-sm-6 col-xl-3">
                  <div :class="['card-info', info.variantClass]">
                    <div class="card-info__header">
                      <div class="iconbox _md _radius">
                        <svg><use :href="info.icon"></use></svg>
                      </div>
                      <div class="text-15 weight-500">
                        <h6 class="card-info__title">{{ info.title }}</h6>
                        <p class="gray500 pt-2">{{ info.subtitle }}</p>
                      </div>
                    </div>
                    <div class="card-info__content">
                      <p v-if="info.contentTitle" class="mb-4 weight-500 gray">{{ info.contentTitle }}</p>
                      <ul class="caption-list">
                        <li v-for="(item, iIdx) in info.items" :key="iIdx">
                          <div class="caption-item">
                            <div class="caption-item__icon">
                              <img v-if="item.img" class="img-cover" :src="item.img" alt="#" />
                              <svg v-else><use :href="checkIcon"></use></svg>
                            </div>
                            <span>{{ item.label }}</span>
                          </div>
                        </li>
                      </ul>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            <div class="dark-bg mb-5">
              <div class="dark-bg__inner p-5">
                <div class="row g-4">
                  <div class="col-12 col-lg">
                    <div class="row mb-5">
                      <div class="col-auto">
                        <div class="iconbox _white _lg">
                          <svg><use :href="reloadIcon"></use></svg>
                        </div>
                      </div>
                      <div class="col">
                        <div class="silver weight-300 text-15 mb-3">{{ syncLabel }}</div>
                        <h4 class="heading-4 weight-600">{{ syncInfo }}</h4>
                      </div>
                    </div>
                    <div class="row align-items-center">
                      <div class="col-auto">
                        <label class="switches _white _normal">
                          <input class="switches__input" type="checkbox" :checked="autoSync" @change="$emit('update:autoSync', $event.target.checked)" />
                          <span class="switches__indicator"></span>
                        </label>
                      </div>
                      <div class="col">
                        <label class="text-15 weight-500">{{ autoSyncText }}</label>
                      </div>
                    </div>
                  </div>
                  <div class="col-12 col-lg-auto align-self-end">
                    <div class="py-3 mb-2">
                      <div class="silver weight-300 text-15">{{ startInstruction }}</div>
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
                    <button class="btn _primary" @click="$emit('finish')">
                      <div class="btn__inner">
                        <span class="btn__text">Подключить</span>
                        <div class="btn__icon">
                          <svg><use :href="reloadIcon"></use></svg>
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
defineProps({
  title: { type: String, default: 'Новая интеграция' },
  subtitle: { type: String, default: 'Добавление рекламного канала' },
  summaryTitle: { type: String, default: 'Просмотр настроек' },
  summarySubtitle: { type: String, default: 'Пожалуйста, проверьте выбранные параметры перед окончательным подключением интеграции.' },
  summaryCards: {
    type: Array,
    default: () => [
      { 
        title: 'Проект и платформа', 
        subtitle: 'Yandex Direct', 
        icon: '/admirra/img/svg/sprite.svg#platforme',
        contentTitle: 'Счетчики Метрики',
        items: [{ label: 'Yandex Direct', img: '/admirra/img/icons/yandex-direct.png' }]
      }
    ]
  },
  syncLabel: { type: String, default: 'Глубина и автосинхрон' },
  syncInfo: { type: String, default: 'Синхронизация за 30 дней' },
  autoSync: { type: Boolean, default: true },
  autoSyncText: { type: String, default: 'Автоматическая синхронизация включена' },
  startInstruction: { type: String, default: 'Нажмите кнопку ниже для старта' },
  checkIcon: { type: String, default: '/admirra/img/svg/sprite.svg#check' },
  reloadIcon: { type: String, default: '/admirra/img/svg/sprite.svg#reload' },
  arrowIcon: { type: String, default: '/admirra/img/svg/sprite.svg#arrow' }
})

defineEmits(['update:autoSync', 'back', 'cancel', 'finish'])
</script>

<style scoped>
.admirra-page-wrapper {
  /* Scoped styles */
}
</style>
