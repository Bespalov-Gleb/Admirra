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
          <div class="steps-track__content">
            <div class="p-5 bg-white radius-base mb-5">
              <div class="mb-5">
                <h5 class="heading-5 weight-500">Просмотр настроек</h5>
                <p class="pt-3 text-15 weight-500 gray56">Пожалуйста, проверьте выбранные параметры перед окончательным подключением интеграции.</p>
              </div>
              <div class="row g-4">
                <div class="col-12 col-sm-6 col-xl-3">
                  <div class="card-info">
                    <div class="card-info__header">
                      <div class="iconbox _md _radius">
                        <svg><use href="/admirra/img/svg/sprite.svg#platforme"></use></svg>
                      </div>
                      <div class="text-15 weight-500">
                        <h6 class="card-info__title">Проект и платформа</h6>
                        <p class="gray500 pt-2">Yandex Direct</p>
                      </div>
                    </div>
                    <div class="card-info__content">
                      <p class="mb-4 weight-500 gray">Счетчики Метрики</p>
                      <ul class="caption-list">
                        <li>
                          <div class="caption-item">
                            <div class="caption-item__icon">
                              <img class="img-cover" src="/admirra/img/icons/yandex-direct.png" alt="yandex" />
                            </div>
                            <span class="c71663e">Yandex Direct</span>
                          </div>
                        </li>
                      </ul>
                    </div>
                  </div>
                </div>
                <div class="col-12 col-sm-6 col-xl-3">
                  <div class="card-info _lavender">
                    <div class="card-info__header">
                      <div class="iconbox _md _radius">
                        <svg><use href="/admirra/img/svg/sprite.svg#platforme"></use></svg>
                      </div>
                      <div class="text-15 weight-500">
                        <h6 class="card-info__title">Счетчики Метрики</h6>
                        <p class="gray500 pt-2">Выбрано: 4</p>
                      </div>
                    </div>
                    <div class="card-info__content">
                      <ul class="caption-list">
                        <li>
                          <div class="caption-item">
                            <div class="caption-item__icon">
                              <svg><use href="/admirra/img/svg/sprite.svg#check"></use></svg>
                            </div>
                            <span>Пескоструй</span>
                          </div>
                        </li>
                        <li>
                          <div class="caption-item">
                            <div class="caption-item__icon">
                              <svg><use href="/admirra/img/svg/sprite.svg#check"></use></svg>
                            </div>
                            <span>Пескоструйная обработка металла</span>
                          </div>
                        </li>
                        <li>
                          <div class="caption-item">
                            <div class="caption-item__icon">
                              <svg><use href="/admirra/img/svg/sprite.svg#check"></use></svg>
                            </div>
                            <span>рся</span>
                          </div>
                        </li>
                        <li>
                          <div class="caption-item">
                            <div class="caption-item__icon">
                              <svg><use href="/admirra/img/svg/sprite.svg#check"></use></svg>
                            </div>
                            <span>Рся металл</span>
                          </div>
                        </li>
                      </ul>
                    </div>
                  </div>
                </div>
                <div class="col-12 col-sm-6 col-xl-3">
                  <div class="card-info _linen">
                    <div class="card-info__header">
                      <div class="iconbox _md _radius">
                        <svg><use href="/admirra/img/svg/sprite.svg#platforme"></use></svg>
                      </div>
                      <div class="text-15 weight-500">
                        <h6 class="card-info__title">Счетчики Метрики</h6>
                        <p class="gray500 pt-2">Выбрано: 4</p>
                      </div>
                    </div>
                    <div class="card-info__content">
                      <ul class="caption-list">
                        <li>
                          <div class="caption-item">
                            <div class="caption-item__icon">
                              <svg><use href="/admirra/img/svg/sprite.svg#check"></use></svg>
                            </div>
                            <span>Пескоструй</span>
                          </div>
                        </li>
                        <li>
                          <div class="caption-item">
                            <div class="caption-item__icon">
                              <svg><use href="/admirra/img/svg/sprite.svg#check"></use></svg>
                            </div>
                            <span>Пескоструйная обработка металла</span>
                          </div>
                        </li>
                        <li>
                          <div class="caption-item">
                            <div class="caption-item__icon">
                              <svg><use href="/admirra/img/svg/sprite.svg#check"></use></svg>
                            </div>
                            <span>рся</span>
                          </div>
                        </li>
                        <li>
                          <div class="caption-item">
                            <div class="caption-item__icon">
                              <svg><use href="/admirra/img/svg/sprite.svg#check"></use></svg>
                            </div>
                            <span>Рся металл</span>
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
                          <svg><use href="/admirra/img/svg/sprite.svg#reload"></use></svg>
                        </div>
                      </div>
                      <div class="col">
                        <div class="silver weight-300 text-15 mb-3">Глубина и автосинхрон</div>
                        <h4 class="heading-4 weight-600">Синхронизация за 30 дней</h4>
                      </div>
                    </div>
                    <div class="row align-items-center">
                      <div class="col-auto">
                        <label class="switches _white _normal">
                          <input class="switches__input" type="checkbox" name="automaticSynchronization" id="sdad7y34bds" checked="" />
                          <span class="switches__indicator"></span>
                        </label>
                      </div>
                      <div class="col">
                        <label class="text-15 weight-500" for="sdad7y34bds">Автоматическая синхронизация включена</label>
                      </div>
                    </div>
                  </div>
                  <div class="col-12 col-lg-auto align-self-end">
                    <div class="py-3 mb-2">
                      <div class="silver weight-300 text-15">Нажмите кнопку ниже для старта</div>
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
                        <span class="btn__text">Подключить</span>
                        <div class="btn__icon">
                          <svg><use href="/admirra/img/svg/sprite.svg#refresh"></use></svg>
                        </div>
                      </div>
                    </a>
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