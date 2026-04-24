<template>
  <div class="admirra-page-wrapper">
    <section class="main-section">
      <div class="px-0 px-xxl-5 my-auto">
        <div class="row g-4 text-15">
          <div class="col-12 col-xxl-7">
            <div class="h-100 bg-white radius-base p-5">
              <h3 class="heading-3 lh-125 mb-4" v-html="title"></h3>
              <p class="weight-500 gray56 mb-5" v-html="description"></p>
              <div class="row gy-3">
                <div class="col-12 col-md">
                  <div class="h-100 bg-white border-gray10 radius-base">
                    <div class="p-5 weight-500 lh-135 dark80" v-html="yandexInfo"></div>
                  </div>
                </div>
                <div class="col-12 col-md">
                  <div class="h-100 bg-white border-gray10 radius-base ps-2">
                    <div class="p-5 weight-500 lh-135 dark80" v-html="vkInfo"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="col-12 col-md-6 col-xxl">
            <div class="yadirect-card radius-base">
              <div class="mb-4">
                <img width="47" :src="yandexIcon" alt="yandex direct" />
              </div>
              <div class="mt-auto d-flex flex-column">
                <div class="yadirect-card__title">{{ yandexTitle }}</div>
                <button class="btn _white _lagre" @click="$emit('auth-yandex')">
                  <div class="btn__inner">
                    <span class="btn__text beige">{{ authButtonText }}</span>
                  </div>
                </button>
              </div>
            </div>
          </div>
          <div class="col-12 col-md-6 col-xxl">
            <div class="vkads-card radius-base">
              <div class="mb-4">
                <img width="47" :src="vkIcon" alt="vk ads" />
              </div>
              <div class="mt-auto d-flex flex-column">
                <div class="yadirect-card__title">{{ vkTitle }}</div>
                <button class="btn _white _lagre" @click="$emit('auth-vk')">
                  <div class="btn__inner">
                    <span class="btn__text lavender">{{ authButtonText }}</span>
                  </div>
                </button>
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
  title: {
    type: String,
    default: 'Выберите рекламный канал <br /> <span class="accent-gradient">для сбора всей статистики</span>'
  },
  description: {
    type: String,
    default: 'Если у вас несколько рекламных каналов в разных системах, <br /> дополнительные рекламные системы Вы сможете подключить уже&nbsp;в&nbsp;панели отчета'
  },
  yandexInfo: {
    type: String,
    default: '<span class="beige">Для подключения Яндекс.Директ</span> <br /> Вы должны иметь доступ к&nbsp;рекламному кабинету Яндекс.Директа и Яндекс.Метрики'
  },
  vkInfo: {
    type: String,
    default: '<span class="slategray">Для подключения VK ADS</span> <br /> у вас должен быть агентский или личный доступ к рекламному кабинету'
  },
  yandexTitle: {
    type: String,
    default: 'Яндекс.Директ'
  },
  yandexIcon: {
    type: String,
    default: '/admirra/img/icons/yandex-direct.png'
  },
  vkTitle: {
    type: String,
    default: 'ВК Ads Manager'
  },
  vkIcon: {
    type: String,
    default: '/admirra/img/icons/vk-ads.png'
  },
  authButtonText: {
    type: String,
    default: 'Авторизоваться'
  }
})

defineEmits(['auth-yandex', 'auth-vk'])
</script>

<style scoped>
/* Стили страницы теперь изолированы */
.admirra-page-wrapper :deep(a),
.admirra-page-wrapper :deep(button),
.admirra-page-wrapper :deep(input) {
  /* Сюда можно перенести глобальные сбросы, если они нужны только для этих страниц */
}
</style>
