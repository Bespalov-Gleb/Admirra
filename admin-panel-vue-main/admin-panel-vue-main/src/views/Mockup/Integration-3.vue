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
          <div class="steps-track__content">
            <div class="p-5 bg-white radius-base mb-5">
              <div class="mb-5">
                <h5 class="heading-5 weight-500">Счетчики метрики</h5>
                <p class="pt-3 text-15 weight-500 gray56">Выберите счетчики, для которых нужно отслеживать цели</p>
              </div>
              <div class="row g-4">
                <div class="col-12 col-sm-6 col-md-auto">
                  <div class="select-card">
                    <input class="select-card__input" type="checkbox" name="metric" checked />
                    <div class="select-card__inner">
                      <div class="select-card__header">
                        <div class="avatar-30x30">
                          <div class="avatar-text">ДИ</div>
                        </div>
                        <div class="select-card__check">
                          <svg><use href="/admirra/img/svg/sprite.svg#check"></use></svg>
                        </div>
                      </div>
                      <div class="select-card__content _width-normal">
                        <div class="weight-500">
                          <div class="gray500 text-15 mb-1">Дейтелинг Иркутск</div>
                          <div class="silver uppercase">ID: 098409843080980</div>
                        </div>
                        <div>
                          <a class="select-card__link" href="#" target="_blank">
                            <svg><use href="/admirra/img/svg/sprite.svg#world"></use></svg>
                            <span>sandblasting-msk.ru</span>
                          </a>
                        </div>
                        <div class="mt-auto">
                          <div class="caption"><span class="light-text">Источник:</span> из&nbsp;компании</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
                <div class="col-12 col-sm-6 col-md-auto">
                  <div class="select-card">
                    <input class="select-card__input" type="checkbox" name="metric" />
                    <div class="select-card__inner">
                      <div class="select-card__header">
                        <div class="avatar-30x30">
                          <div class="avatar-text">ДИ</div>
                        </div>
                        <div class="select-card__check">
                          <svg><use href="/admirra/img/svg/sprite.svg#check"></use></svg>
                        </div>
                      </div>
                      <div class="select-card__content _width-normal">
                        <div class="weight-500">
                          <div class="gray500 text-15 mb-1">Дейтелинг Иркутск</div>
                          <div class="silver uppercase">ID: 098409843080980</div>
                        </div>
                        <div>
                          <a class="select-card__link" href="#" target="_blank">
                            <svg><use href="/admirra/img/svg/sprite.svg#world"></use></svg>
                            <span>sandblasting-msk.ru</span>
                          </a>
                        </div>
                        <div class="mt-auto">
                          <div class="caption"><span class="light-text">Источник:</span> из&nbsp;компании</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
                <div class="col-12 col-sm-6 col-md-auto">
                  <div class="select-card">
                    <input class="select-card__input" type="checkbox" name="metric" />
                    <div class="select-card__inner">
                      <div class="select-card__header">
                        <div class="avatar-30x30">
                          <div class="avatar-text">ДИ</div>
                        </div>
                        <div class="select-card__check">
                          <svg><use href="/admirra/img/svg/sprite.svg#check"></use></svg>
                        </div>
                      </div>
                      <div class="select-card__content _width-normal">
                        <div class="weight-500">
                          <div class="gray500 text-15 mb-1">Дейтелинг Иркутск</div>
                          <div class="silver uppercase">ID: 098409843080980</div>
                        </div>
                        <div>
                          <a class="select-card__link" href="#" target="_blank">
                            <svg><use href="/admirra/img/svg/sprite.svg#world"></use></svg>
                            <span>sandblasting-msk.ru</span>
                          </a>
                        </div>
                        <div class="mt-auto">
                          <div class="caption"><span class="light-text">Источник:</span> из&nbsp;компании</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
                <div class="col-12 col-sm-6 col-md-auto">
                  <div class="select-card">
                    <input class="select-card__input" type="checkbox" name="metric" />
                    <div class="select-card__inner">
                      <div class="select-card__header">
                        <div class="avatar-30x30">
                          <div class="avatar-text">ДИ</div>
                        </div>
                        <div class="select-card__check">
                          <svg><use href="/admirra/img/svg/sprite.svg#check"></use></svg>
                        </div>
                      </div>
                      <div class="select-card__content _width-normal">
                        <div class="weight-500">
                          <div class="gray500 text-15 mb-1">Дейтелинг Иркутск</div>
                          <div class="silver uppercase">ID: 098409843080980</div>
                        </div>
                        <div>
                          <a class="select-card__link" href="#" target="_blank">
                            <svg><use href="/admirra/img/svg/sprite.svg#world"></use></svg>
                            <span>sandblasting-msk.ru</span>
                          </a>
                        </div>
                        <div class="mt-auto">
                          <div class="caption"><span class="light-text">Источник:</span> из&nbsp;компании</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div class="p-5 bg-white radius-base mb-5">
              <div class="row g-4 mb-5">
                <div class="col-12 col-md">
                  <h5 class="heading-5 weight-500">Цели и конверсии</h5>
                  <p class="pt-3 text-15 weight-500 gray56">Выберите основную цель (звездочка) и&nbsp;дополнительные цели для&nbsp;отслеживания</p>
                </div>
                <div class="col-12 col-md-auto">
                  <div class="input-item">
                    <input class="input w-100" type="text" placeholder="Поиск цели" />
                    <div class="input-icon">
                      <svg class="_stroke"><use href="/admirra/img/svg/sprite.svg#search"></use></svg>
                    </div>
                  </div>
                </div>
              </div>
              <div class="row g-4 pt-5">
                <div class="col-12 col-sm-6 col-md-auto">
                  <div class="select-card">
                    <div class="select-card__note">
                      <svg><use href="/admirra/img/svg/sprite.svg#star"></use></svg>
                      <span>рекомендуемая</span>
                    </div>
                    <input class="select-card__input" type="checkbox" name="goals" checked />
                    <div class="select-card__inner">
                      <div class="select-card__header">
                        <div class="avatar-30x30">
                          <div class="avatar-text">ДИ</div>
                        </div>
                        <div class="select-card__check">
                          <svg><use href="/admirra/img/svg/sprite.svg#check"></use></svg>
                        </div>
                      </div>
                      <div class="select-card__content _width-normal">
                        <div class="weight-500">
                          <div class="gray500 text-15 mb-1">Цель на посещение</div>
                          <div class="silver uppercase">ID: 542695813</div>
                        </div>
                      </div>
                      <div class="row align-items-end mt-auto">
                        <div class="col">
                          <div class="caption"><span class="light-text">Тип цели:</span> URL</div>
                        </div>
                        <div class="col-auto mt-auto">
                          <div class="select-card__favorites">
                            <svg><use href="/admirra/img/svg/sprite.svg#star"></use></svg>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
                <div class="col-12 col-sm-6 col-md-auto">
                  <div class="select-card">
                    <input class="select-card__input" type="checkbox" name="goals" checked />
                    <div class="select-card__inner">
                      <div class="select-card__header">
                        <div class="avatar-30x30">
                          <div class="avatar-text">ДИ</div>
                        </div>
                        <div class="select-card__check">
                          <svg><use href="/admirra/img/svg/sprite.svg#check"></use></svg>
                        </div>
                      </div>
                      <div class="select-card__content _width-normal">
                        <div class="weight-500">
                          <div class="gray500 text-15 mb-1">Цель на посещение</div>
                          <div class="silver uppercase">ID: 542695813</div>
                        </div>
                      </div>
                      <div class="row align-items-end mt-auto">
                        <div class="col">
                          <div class="caption"><span class="light-text">Тип цели:</span> URL</div>
                        </div>
                        <div class="col-auto mt-auto">
                          <div class="select-card__favorites">
                            <svg><use href="/admirra/img/svg/sprite.svg#star"></use></svg>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
                <div class="col-12 col-sm-6 col-md-auto">
                  <div class="select-card">
                    <input class="select-card__input" type="checkbox" name="goals" />
                    <div class="select-card__inner">
                      <div class="select-card__header">
                        <div class="avatar-30x30">
                          <div class="avatar-text">ДИ</div>
                        </div>
                        <div class="select-card__check">
                          <svg><use href="/admirra/img/svg/sprite.svg#check"></use></svg>
                        </div>
                      </div>
                      <div class="select-card__content _width-normal">
                        <div class="weight-500">
                          <div class="gray500 text-15 mb-1">Цель на посещение</div>
                          <div class="silver uppercase">ID: 542695813</div>
                        </div>
                      </div>
                      <div class="row align-items-end mt-auto">
                        <div class="col">
                          <div class="caption"><span class="light-text">Тип цели:</span> URL</div>
                        </div>
                        <div class="col-auto mt-auto">
                          <div class="select-card__favorites">
                            <svg><use href="/admirra/img/svg/sprite.svg#star"></use></svg>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
                <div class="col-12 col-sm-6 col-md-auto">
                  <div class="select-card">
                    <input class="select-card__input" type="checkbox" name="goals" />
                    <div class="select-card__inner">
                      <div class="select-card__header">
                        <div class="avatar-30x30">
                          <div class="avatar-text">ДИ</div>
                        </div>
                        <div class="select-card__check">
                          <svg><use href="/admirra/img/svg/sprite.svg#check"></use></svg>
                        </div>
                      </div>
                      <div class="select-card__content _width-normal">
                        <div class="weight-500">
                          <div class="gray500 text-15 mb-1">Цель на посещение</div>
                          <div class="silver uppercase">ID: 542695813</div>
                        </div>
                      </div>
                      <div class="row align-items-end mt-auto">
                        <div class="col">
                          <div class="caption"><span class="light-text">Тип цели:</span> URL</div>
                        </div>
                        <div class="col-auto mt-auto">
                          <div class="select-card__favorites">
                            <svg><use href="/admirra/img/svg/sprite.svg#star"></use></svg>
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
              <div class="steps-track__marker-text">4</div>
            </div>
            <div class="steps-track__caption">Сводка</div>
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
  countersTitle: { type: String, default: 'Счетчики метрики' },
  countersSubtitle: { type: String, default: 'Выберите счетчики, для которых нужно отслеживать цели' },
  counters: {
    type: Array,
    default: () => [
      { id: '098409843080980', name: 'Дейтелинг Иркутск', shortName: 'ДИ', domain: 'sandblasting-msk.ru', url: '#', source: 'из компании', selected: true }
    ]
  },
  goalsTitle: { type: String, default: 'Цели и конверсии' },
  goalsSubtitle: { type: String, default: 'Выберите основную цель (звездочка) и дополнительные цели для отслеживания' },
  searchPlaceholder: { type: String, default: 'Поиск цели' },
  goals: {
    type: Array,
    default: () => [
      { id: '542695813', name: 'Цель на посещение', shortName: 'ДИ', type: 'URL', selected: true, isRecommended: true, isFavorite: false }
    ]
  },
  checkIcon: { type: String, default: '/admirra/img/svg/sprite.svg#check' },
  worldIcon: { type: String, default: '/admirra/img/svg/sprite.svg#world' },
  searchIcon: { type: String, default: '/admirra/img/svg/sprite.svg#search' },
  starIcon: { type: String, default: '/admirra/img/svg/sprite.svg#star' },
  arrowIcon: { type: String, default: '/admirra/img/svg/sprite.svg#arrow' }
})

defineEmits(['update:counter', 'update:goal', 'search-goals', 'toggle-favorite', 'back', 'cancel', 'next'])
</script>

<style scoped>
.admirra-page-wrapper {
  /* Scoped styles */
}
</style>