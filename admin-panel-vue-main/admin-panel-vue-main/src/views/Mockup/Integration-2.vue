<template>
  <div class="admirra-page-wrapper">
  <section class="main-section">
      <div class="section-header pt-4 mt-1">
        <h3 class="heading-3 mb-2">Новая интеграция</h3>
        <p class="section-header__descrp">Добавление рекламного канала</p>
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
                  <div class="weight-500 gray mb-3">Глубина истории</div>
                  <select class="select-light wide mb-1">
                    <option>Все</option>
                    <option value="1">Some option</option>
                    <option value="2">Another option</option>
                    <option value="3" disabled>A disabled option</option>
                    <option value="4">Potato option</option>
                  </select>
                  <div class="py-4 mb-2">
                    <div class="weight-500 gray mb-3">Автосинхронизация</div>
                    <label class="switches _light _big">
                      <input class="switches__input" type="checkbox" name="switches" checked />
                      <span class="switches__text">24/7</span>
                      <span class="switches__indicator"></span>
                    </label>
                  </div>
                  <div class="mt-auto">
                    <a class="btn d-flex" href="#">
                      <div class="btn__inner">
                        <span class="btn__text">Подключить Яндекс&nbsp;Директ</span>
                      </div>
                    </a>
                  </div>
                </div>
              </div>
              <div class="col-sm-12 col-md col-xl-auto">
                <div class="dark-bg">
                  <div class="dark-bg__inner p-5">
                    <div class="mb-4">
                      <img width="40" src="/admirra/img/yandex-direct.png" alt="#" />
                    </div>
                    <h4 class="heading-4 pe-5 lh-120 weight-500 mb-3">Интеграция с Яндекс.Директ</h4>
                    <p class="silver weight-300 text-15 lh-135 mb-4">
                      Автоматический сбор кампаний, <br />
                      ключевых слов и статистики
                    </p>
                    <div class="mt-auto">
                      <div class="row g-2">
                        <div class="col">
                          <div class="alert-dark">
                            <div class="alert-dark__inner">
                              <div class="dotty _success"></div>
                              <span>API:&nbsp;СОЕДИНЕНО</span>
                            </div>
                          </div>
                        </div>
                        <div class="col-auto">
                          <a class="btn _outline" href="#">
                            <div class="btn__inner">
                              <span class="btn__text">Как это работает?</span>
                            </div>
                          </a>
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
                <h5 class="heading-5 weight-500">Выберите рекламный кабинет для интеграции</h5>
              </div>
              <div class="row g-4">
                <div class="col col-sm-auto">
                  <div class="select-card">
                    <input class="select-card__input" type="radio" name="card-ads" />
                    <div class="select-card__inner">
                      <div class="select-card__header">
                        <div class="avatar-30x30">
                          <img class="img-cover" src="/admirra/img/icons/yandex-direct.png" alt="#" />
                        </div>
                        <div class="select-card__check">
                          <svg><use href="/admirra/img/svg/sprite.svg#check"></use></svg>
                        </div>
                      </div>
                      <div class="select-card__content">
                        <div class="weight-500">
                          <div class="gray500 text-15 mb-1">Иван Иванов</div>
                          <div class="silver uppercase">LOGINAKKAUNTA</div>
                        </div>
                        <div class="mt-auto">
                          <div class="caption">Личный</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
                <div class="col col-sm-auto">
                  <div class="select-card">
                    <input class="select-card__input" type="radio" name="card-ads" />
                    <div class="select-card__inner">
                      <div class="select-card__header">
                        <div class="avatar-30x30">
                          <img class="img-cover" src="/admirra/img/icons/yandex-direct.png" alt="#" />
                        </div>
                        <div class="select-card__check">
                          <svg><use href="/admirra/img/svg/sprite.svg#check"></use></svg>
                        </div>
                      </div>
                      <div class="select-card__content">
                        <div class="weight-500">
                          <div class="gray500 text-15 mb-1">Иван Иванов</div>
                          <div class="silver uppercase">LOGINAKKAUNTA</div>
                        </div>
                        <div class="mt-auto">
                          <div class="caption">Личный</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
                <div class="col col-sm-auto">
                  <div class="select-card">
                    <input class="select-card__input" type="radio" name="card-ads" />
                    <div class="select-card__inner">
                      <div class="select-card__header">
                        <div class="avatar-30x30">
                          <img class="img-cover" src="/admirra/img/icons/yandex-direct.png" alt="#" />
                        </div>
                        <div class="select-card__check">
                          <svg><use href="/admirra/img/svg/sprite.svg#check"></use></svg>
                        </div>
                      </div>
                      <div class="select-card__content">
                        <div class="weight-500">
                          <div class="gray500 text-15 mb-1">Иван Иванов</div>
                          <div class="silver uppercase">LOGINAKKAUNTA</div>
                        </div>
                        <div class="mt-auto">
                          <div class="caption">Личный</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div class="row g-3 pt-2">
              <div class="col">
                <a class="btn _white" href="#">
                  <div class="btn__inner">
                    <div class="btn__icon-info">
                      <svg class="prev"><use href="/admirra/img/svg/sprite.svg#arrow"></use></svg>
                    </div>
                    <span class="btn__text">Назад</span>
                  </div>
                </a>
              </div>
              <div class="col-auto">
                <div class="row">
                  <div class="col-auto">
                    <button class="btn _outline-gray">
                      <div class="btn__inner">
                        <span class="btn__text">Отмена</span>
                      </div>
                    </button>
                  </div>
                  <div class="col-auto">
                    <a class="btn _primary" href="#">
                      <div class="btn__inner">
                        <span class="btn__text">Далее</span>
                        <div class="btn__icon-info">
                          <svg class="next"><use href="/admirra/img/svg/sprite.svg#arrow"></use></svg>
                        </div>
                      </div>
                    </a>
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