<template>
  <div class="admirra-page-wrapper">
    <section class="main-section">
      <div class="section-header pt-4 mt-1">
        <h3 class="heading-3">{{ title }}</h3>
        <p class="section-header__descrp">{{ subtitle }}</p>
      </div>
      <div class="tariff">
        <div class="tariff-tabs">
          <div class="tariff-tabs__nav">
            <div class="tariff-tabs__inner">
              <div v-for="period in periods" :key="period.id" :class="['tariff-tabs__item', { active: currentPeriod === period.id }]">
                <button @click="$emit('change-period', period.id)">
                  <span>{{ period.label }}</span>
                  <span v-if="period.badge" class="badge-text">{{ period.badge }}</span>
                </button>
              </div>
            </div>
          </div>
          
          <div class="row gy-4 justify-content-center">
            <div v-for="plan in currentPlans" :key="plan.id" class="col-12 col-md-6 col-lg-4">
              <div :class="['tariff-card', { _primary: plan.isPrimary }]">
                <div class="tariff-card__content">
                  <h4 class="tariff-card__caption">
                    <i class="icon-twocircle"></i>
                    <strong>{{ plan.name }}</strong>
                  </h4>
                  <div class="ui-price">
                    <div class="_current">{{ plan.price }}</div>
                    <small class="_old">{{ plan.subPrice }}</small>
                  </div>
                  <ul class="list _style-one">
                    <li v-for="(feature, fIdx) in plan.features" :key="fIdx" class="list__item">
                      <div class="list__plus">
                        <svg><use :href="plusIcon"></use></svg>
                      </div>
                      <span v-html="feature"></span>
                    </li>
                  </ul>
                  <div class="to-action">
                    <div>
                      <button :class="['btn', plan.buttonClass]" @click="$emit('select-plan', plan)">
                        <div class="btn__inner">
                          <span :class="['btn__text', plan.btnTextClass]">{{ plan.buttonText }}</span>
                          <div class="btn__icon">
                            <svg><use :href="ideaIcon"></use></svg>
                          </div>
                        </div>
                      </button>
                    </div>
                    <div>
                      <div :class="['to-action__info', plan.infoClass]" v-html="plan.trialInfo"></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="white-label">
          <div class="row g-5">
            <div class="col-12 col-md-6 col-xl-4">
              <div class="white-label__about">
                <div class="white-label__about-header">
                  <i class="icon-twocircle"></i>
                  <h4 class="heading-5" v-html="wlTitle"></h4>
                </div>
                <ul class="list _style-one weight-500">
                  <li v-for="(feat, idx) in wlFeatures" :key="idx" class="list__item">
                    <div class="list__plus">
                      <svg><use :href="plusIcon"></use></svg>
                    </div>
                    <span>{{ feat }}</span>
                  </li>
                </ul>
              </div>
            </div>
            <div class="col-12 col-md-6 col-xl-4">
              <div class="white-label__ui"></div>
            </div>
            <div class="col-12 col-md-12 col-xl-4">
              <div class="white-label__action">
                <div class="ui-price mb-4 pb-2">
                  <div class="_current">{{ wlPrice }}</div>
                  <small class="_old">{{ wlSubPrice }}</small>
                </div>
                <p class="white-label__action-text">{{ wlDescription }}</p>
                <div class="mt-auto pt-3">
                  <button class="btn d-flex" @click="$emit('select-wl')">
                    <div class="btn__inner">
                      <span class="btn__text">{{ wlButtonText }}</span>
                      <div class="btn__icon">
                        <svg><use :href="ideaIcon"></use></svg>
                      </div>
                    </div>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, default: 'Тарифы' },
  subtitle: { type: String, default: 'Выберите подходящий тариф в зависимости от количества проектов и задач аналитики' },
  periods: {
    type: Array,
    default: () => [
      { id: 'month', label: 'Месяц' },
      { id: 'year', label: 'Год', badge: 'Экономия 30%' }
    ]
  },
  currentPeriod: { type: String, default: 'month' },
  currentPlans: {
    type: Array,
    default: () => [
      {
        id: 'start',
        name: 'Старт',
        price: '1 590 ₽',
        subPrice: '1590 руб/проект',
        features: ['1 проект', 'Каналы: Яндекс.Директ, ВК', '1 пользователь', '30 запросов AI'],
        buttonText: 'Перейти на тариф Старт',
        trialInfo: '<span class="accent-gradient">14 дней бесплатно</span> — подключение за&nbsp;5&nbsp;минут'
      }
    ]
  },
  wlTitle: { type: String, default: 'White Label - <br /> персонализация <br /> кабинета и&nbsp;отчетности' },
  wlFeatures: {
    type: Array,
    default: () => [
      'Отчеты без логотипа сервиса',
      'Брендирование отчетов',
      'Использование платформы как собственной системы аналитики',
      'Собственный домен'
    ]
  },
  wlPrice: { type: String, default: '25 900 ₽' },
  wlSubPrice: { type: String, default: '259 руб/проект' },
  wlDescription: { type: String, default: 'При покупке на год - возможны персональные скидки. Оставьте заявку, чтобы обсудить детали использования WL.' },
  wlButtonText: { type: String, default: 'Перейти на тариф WL' },
  plusIcon: { type: String, default: '/admirra/img/svg/sprite.svg#plus' },
  ideaIcon: { type: String, default: '/admirra/img/svg/sprite.svg#idea' }
})

defineEmits(['change-period', 'select-plan', 'select-wl'])
</script>

<style scoped>
.admirra-page-wrapper {
  /* Scoped styles */
}
/* Стили для вкладок, если они не в глобальном CSS */
.tariff-tabs__item button {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.6944rem 1.3889rem;
}
.tariff-tabs__item.active button {
  font-weight: bold;
}
</style>
