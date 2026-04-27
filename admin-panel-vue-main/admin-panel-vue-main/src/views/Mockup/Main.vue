<template>
  <div class="admirra-page-wrapper">
  <section class="main-section">
      <div class="section-header pt-4">
        <h6 class="section-header__descrp mb-1">
          <span class="dotty _lime mt-2"></span>
          Общая аналитика по всем активным&nbsp;проектам
        </h6>
        <h3 class="heading-3">Отчет по проекту: Дейтелинг&nbsp;Иркутск</h3>
      </div>
      <div class="row gy-3 mb-5">
        <div class="col-12 col-lg">
          <div class="row gy-3">
            <div class="col-12 col-sm-auto">
              <select class="wide">
                <option value="1">Все каналы</option>
                <option value="2">Каналы 1</option>
                <option value="3">Каналы 2</option>
              </select>
            </div>
            <div class="col-12 col-sm-auto">
              <select class="wide">
                <option value="1">Компании</option>
                <option value="2">Компания 1</option>
                <option value="3">Компания 2</option>
              </select>
            </div>
            <div class="col-12 col-sm-auto">
              <select class="wide">
                <option value="1">Свой период</option>
                <option value="2">Период 1</option>
                <option value="3">Период 2</option>
              </select>
            </div>
            <div class="col-12 col-sm-auto">
              <div class="datepiker-item">
                <input class="datepiker-item__input" id="datepikerProjectReport" type="text" />
                <div class="datepiker-item__icons">
                  <svg class="datepiker-item__calendar"><use href="/admirra/img/svg/sprite.svg#datepiker"></use></svg>
                  <div class="circle-arrow _light _sm">
                    <svg><use href="/admirra/img/svg/sprite.svg#arrow"></use></svg>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="col-12 col-sm-auto">
          <a class="btn _primary w-100" href="#">
            <div class="btn__inner">
              <span class="btn__text">Скачать отчет в&nbsp;PDF</span>
              <div class="btn__icon">
                <svg class="_download"><use href="/admirra/img/svg/sprite.svg#download"></use></svg>
              </div>
            </div>
          </a>
        </div>
        <div class="col-12 col-sm-auto">
          <a class="btn _primary w-100" href="#">
            <div class="btn__inner">
              <span class="btn__text">Скачать отчет в&nbsp;Telegram</span>
              <div class="btn__icon">
                <svg class="_download"><use href="/admirra/img/svg/sprite.svg#download"></use></svg>
              </div>
            </div>
          </a>
        </div>
      </div>
      <div class="row g-4 mb-4">
        <div class="col-12 col-sm-6 col-xxl-4">
          <div class="data-card">
            <div class="data-card__header">
              <div class="d-flex">
                <div class="iconbox _light _lg">
                  <svg class="_wallet"><use href="/admirra/img/svg/sprite.svg#wallet"></use></svg>
                </div>
                <div class="ps-4 align-self-center">
                  <h4 class="data-card__header-title mb-3 text-20 weight-500 gray500">Расходы</h4>
                  <p class="text-15 weight-300 gray56">За период</p>
                </div>
              </div>
              <div class="ms-auto ps-3">
                <a class="circle-btn" href="#">
                  <svg><use href="/admirra/img/svg/sprite.svg#up"></use></svg>
                </a>
              </div>
            </div>
            <span class="data-card__price weight-600">90,190.55&nbsp;₽</span>
            <div class="d-flex align-items-center">
              <div class="me-4 pe-0 pe-md-3">
                <div class="badge _success _xl">
                  <svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
                  +15.6%
                </div>
              </div>
              <div class="data-card__result-info weight-500"><strong>+1.4k</strong> <span class="gray56">за эту неделю</span></div>
            </div>
          </div>
        </div>
        <div class="col-12 col-sm-6 col-xxl-4">
          <div class="data-card">
            <div class="data-card__header">
              <div class="d-flex">
                <div class="iconbox _light _lg">
                  <svg><use href="/admirra/img/svg/sprite.svg#diagrama"></use></svg>
                </div>
                <div class="ps-4 align-self-center">
                  <h4 class="data-card__header-title mb-3 text-20 weight-500 gray500">Показы</h4>
                  <p class="text-15 weight-300 gray56">По всем каналам</p>
                </div>
              </div>
              <div class="ms-auto ps-3">
                <a class="circle-btn" href="#">
                  <svg><use href="/admirra/img/svg/sprite.svg#up"></use></svg>
                </a>
              </div>
            </div>
            <span class="data-card__price weight-600">120,302</span>
            <div class="d-flex align-items-center">
              <div class="me-4 pe-0 pe-md-3">
                <div class="badge _success _xl">
                  <svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
                  +15.6%
                </div>
              </div>
              <div class="data-card__result-info weight-500"><strong>+1.4k</strong> <span class="gray56">за эту неделю</span></div>
            </div>
          </div>
        </div>
        <div class="col-12 col-sm-6 col-xxl-4">
          <div class="data-card">
            <div class="data-card__header">
              <div class="d-flex">
                <div class="iconbox _light _lg">
                  <svg><use href="/admirra/img/svg/sprite.svg#cursore"></use></svg>
                </div>
                <div class="ps-4 align-self-center">
                  <h4 class="data-card__header-title mb-3 text-20 weight-500 gray500">Клики</h4>
                  <p class="text-15 weight-300 gray56">Все переходы</p>
                </div>
              </div>
              <div class="ms-auto ps-3">
                <a class="circle-btn" href="#">
                  <svg><use href="/admirra/img/svg/sprite.svg#up"></use></svg>
                </a>
              </div>
            </div>
            <span class="data-card__price weight-600">967</span>
            <div class="d-flex align-items-center">
              <div class="me-4 pe-0 pe-md-3">
                <div class="badge _success _xl">
                  <svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
                  +15.6%
                </div>
              </div>
              <div class="data-card__result-info weight-500"><strong>-213</strong> <span class="gray56">за эту неделю</span></div>
            </div>
          </div>
        </div>
        <div class="col-12 col-sm-6 col-xxl-4">
          <div class="data-card">
            <div class="data-card__header">
              <div class="d-flex">
                <div class="iconbox _light _lg">
                  <svg><use href="/admirra/img/svg/sprite.svg#diagrama-circle"></use></svg>
                </div>
                <div class="ps-4 align-self-center">
                  <h4 class="data-card__header-title mb-3 text-20 weight-500 gray500">CPC</h4>
                  <p class="text-15 weight-300 gray56">Стоимость клика</p>
                </div>
              </div>
              <div class="ms-auto ps-3">
                <a class="circle-btn" href="#">
                  <svg><use href="/admirra/img/svg/sprite.svg#up"></use></svg>
                </a>
              </div>
            </div>
            <span class="data-card__price weight-600">9,63&nbsp;₽</span>
            <div class="d-flex align-items-center">
              <div class="me-4 pe-0 pe-md-3">
                <div class="badge _success _xl">
                  <svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
                  +15.6%
                </div>
              </div>
              <div class="data-card__result-info weight-500"><strong>+1.4k</strong> <span class="gray56">за эту неделю</span></div>
            </div>
          </div>
        </div>
        <div class="col-12 col-sm-6 col-xxl-4">
          <div class="data-card">
            <div class="data-card__header">
              <div class="d-flex">
                <div class="iconbox _light _lg">
                  <svg><use href="/admirra/img/svg/sprite.svg#calendar"></use></svg>
                </div>
                <div class="ps-4 align-self-center">
                  <h4 class="data-card__header-title mb-3 text-20 weight-500 gray500">Лиды</h4>
                  <p class="text-15 weight-300 gray56">По всем каналам</p>
                </div>
              </div>
              <div class="ms-auto ps-3">
                <a class="circle-btn" href="#">
                  <svg><use href="/admirra/img/svg/sprite.svg#up"></use></svg>
                </a>
              </div>
            </div>
            <span class="data-card__price weight-600">130&nbsp;шт.</span>
            <div class="d-flex align-items-center">
              <div class="me-4 pe-0 pe-md-3">
                <div class="badge _success _xl">
                  <svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
                  +15.6%
                </div>
              </div>
              <div class="data-card__result-info weight-500"><strong>+1.4k</strong> <span class="gray56">за эту неделю</span></div>
            </div>
          </div>
        </div>
        <div class="col-12 col-sm-6 col-xxl-4">
          <div class="data-card">
            <div class="data-card__header">
              <div class="d-flex">
                <div class="iconbox _light _lg">
                  <svg><use href="/admirra/img/svg/sprite.svg#ok"></use></svg>
                </div>
                <div class="ps-4 align-self-center">
                  <h4 class="data-card__header-title mb-3 text-20 weight-500 gray500">CPA</h4>
                  <p class="text-15 weight-300 gray56">Стоимость лида</p>
                </div>
              </div>
              <div class="ms-auto ps-3">
                <a class="circle-btn" href="#">
                  <svg><use href="/admirra/img/svg/sprite.svg#up"></use></svg>
                </a>
              </div>
            </div>
            <span class="data-card__price weight-600">963&nbsp;₽</span>
            <div class="d-flex align-items-center">
              <div class="me-4 pe-0 pe-md-3">
                <div class="badge _danger _xl">
                  <svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-down"></use></svg>
                  -15.6%
                </div>
              </div>
              <div class="data-card__result-info weight-500"><strong>-213</strong> <span class="gray56">за эту неделю</span></div>
            </div>
          </div>
        </div>
        <div class="col-12 col-xxl-8">
          <div class="data-card p-0">
            <div class="row">
              <div class="col-12 col-lg-6">
                <div class="data-card__goals">
                  <div class="data-card__header">
                    <div class="d-flex">
                      <div class="iconbox _light _lg">
                        <svg><use href="/admirra/img/svg/sprite.svg#platforme"></use></svg>
                      </div>
                      <div class="ps-4 align-self-center">
                        <h4 class="data-card__header-title mb-3 text-20 weight-500 gray500">Статистика по ключевым&nbsp;целям</h4>
                        <p class="text-15 weight-300 gray56">За период</p>
                      </div>
                    </div>
                  </div>
                  <div class="info-row">
                    <h6>Звонки:</h6>
                    <div class="info-row__decor-line"></div>
                    <strong class="weight-700">14 шт.</strong>
                    <div class="badge _success _md">
                      <svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
                      +15.6%
                    </div>
                  </div>
                  <div class="info-row">
                    <h6>Лиды с&nbsp;quiz:</h6>
                    <div class="info-row__decor-line"></div>
                    <strong class="weight-700">57 шт.</strong>
                    <div class="badge _success _md">
                      <svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
                      +15.6%
                    </div>
                  </div>
                  <div class="info-row">
                    <h6>Лиды с&nbsp;форм:</h6>
                    <div class="info-row__decor-line"></div>
                    <strong class="weight-700">63 шт.</strong>
                    <div class="badge _success _md">
                      <svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
                      +15.6%
                    </div>
                  </div>
                </div>
              </div>
              <div class="col-12 col-lg-6">
                <div class="total-card">
                  <div class="total-card__inner">
                    <div class="weight-500">Итого:</div>
                    <div class="total-card__units">250 <span class="things">шт.</span></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
  
      <div class="white-block radius-normal mb-4">
        <div class="pt-2">
          <h4 class="mb-3 text-20 weight-500 gray500">Статистика по ключевым&nbsp;целям</h4>
          <p class="text-15 weight-300 gray56">За период</p>
        </div>
        <div class="table-container mt-5 mb-3">
          <table class="table-style text-15">
            <thead>
              <tr>
                <th>Название&nbsp;кампании</th>
                <th>Расход</th>
                <th>Показы</th>
                <th>Клики</th>
                <th>CPC</th>
                <th>Лиды</th>
                <th>CPA</th>
              </tr>
            </thead>
            <tbody>
              <tr class="linen">
                <td>
                  <div class="td">Дейтелинг Про Иркутск</div>
                </td>
                <td>
                  <div class="td">
                    <span class="nowrap-text">90,190.55 ₽</span>
                    <div class="badge _success _sm">
                      <svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
                      +15.6%
                    </div>
                  </div>
                </td>
                <td>
                  <div class="td">
                    <span>120,302</span>
                    <div class="badge _success _sm">
                      <svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
                      +15.6%
                    </div>
                  </div>
                </td>
                <td>
                  <div class="td">
                    <span>967</span>
                    <div class="badge _success _sm">
                      <svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
                      +15.6%
                    </div>
                  </div>
                </td>
                <td>
                  <div class="td">
                    <span class="nowrap-text">9,63 ₽</span>
                    <div class="badge _success _sm">
                      <svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
                      +15.6%
                    </div>
                  </div>
                </td>
                <td>
                  <div class="td">
                    <span class="nowrap-text">130 шт.</span>
                    <div class="badge _success _sm">
                      <svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
                      +15.6%
                    </div>
                  </div>
                </td>
                <td>
                  <div class="td">
                    <span class="nowrap-text">963 ₽</span>
                    <div class="badge _danger _sm">
                      <svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-down"></use></svg>
                      +15.6%
                    </div>
                  </div>
                </td>
              </tr>
              <tr class="lightyellow">
                <td>
                  <div class="td">Дейтелинг Про Иркутск</div>
                </td>
                <td>
                  <div class="td">
                    <span class="nowrap-text">90,190.55 ₽</span>
                    <div class="badge _success _sm">
                      <svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
                      +15.6%
                    </div>
                  </div>
                </td>
                <td>
                  <div class="td">
                    <span>120,302</span>
                    <div class="badge _success _sm">
                      <svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
                      +15.6%
                    </div>
                  </div>
                </td>
                <td>
                  <div class="td">
                    <span>967</span>
                    <div class="badge _success _sm">
                      <svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
                      +15.6%
                    </div>
                  </div>
                </td>
                <td>
                  <div class="td">
                    <span class="nowrap-text">9,63 ₽</span>
                    <div class="badge _success _sm">
                      <svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
                      +15.6%
                    </div>
                  </div>
                </td>
                <td>
                  <div class="td">
                    <span class="nowrap-text">130 шт.</span>
                    <div class="badge _success _sm">
                      <svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
                      +15.6%
                    </div>
                  </div>
                </td>
                <td>
                  <div class="td">
                    <span class="nowrap-text">963 ₽</span>
                    <div class="badge _danger _sm">
                      <svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-down"></use></svg>
                      +15.6%
                    </div>
                  </div>
                </td>
              </tr>
              <tr class="aquamarine">
                <td>
                  <div class="td">Дейтелинг Про Иркутск</div>
                </td>
                <td>
                  <div class="td">
                    <span class="nowrap-text">90,190.55 ₽</span>
                    <div class="badge _success _sm">
                      <svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
                      +15.6%
                    </div>
                  </div>
                </td>
                <td>
                  <div class="td">
                    <span>120,302</span>
                    <div class="badge _success _sm">
                      <svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
                      +15.6%
                    </div>
                  </div>
                </td>
                <td>
                  <div class="td">
                    <span>967</span>
                    <div class="badge _success _sm">
                      <svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
                      +15.6%
                    </div>
                  </div>
                </td>
                <td>
                  <div class="td">
                    <span class="nowrap-text">9,63 ₽</span>
                    <div class="badge _success _sm">
                      <svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
                      +15.6%
                    </div>
                  </div>
                </td>
                <td>
                  <div class="td">
                    <span class="nowrap-text">130 шт.</span>
                    <div class="badge _success _sm">
                      <svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
                      +15.6%
                    </div>
                  </div>
                </td>
                <td>
                  <div class="td">
                    <span class="nowrap-text">963 ₽</span>
                    <div class="badge _danger _sm">
                      <svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-down"></use></svg>
                      +15.6%
                    </div>
                  </div>
                </td>
              </tr>
              <tr class="aliceblue">
                <td>
                  <div class="td">Дейтелинг Про Иркутск</div>
                </td>
                <td>
                  <div class="td">
                    <span class="nowrap-text">90,190.55 ₽</span>
                    <div class="badge _success _sm">
                      <svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
                      +15.6%
                    </div>
                  </div>
                </td>
                <td>
                  <div class="td">
                    <span>120,302</span>
                    <div class="badge _success _sm">
                      <svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
                      +15.6%
                    </div>
                  </div>
                </td>
                <td>
                  <div class="td">
                    <span>967</span>
                    <div class="badge _success _sm">
                      <svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
                      +15.6%
                    </div>
                  </div>
                </td>
                <td>
                  <div class="td">
                    <span class="nowrap-text">9,63 ₽</span>
                    <div class="badge _success _sm">
                      <svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
                      +15.6%
                    </div>
                  </div>
                </td>
                <td>
                  <div class="td">
                    <span class="nowrap-text">130 шт.</span>
                    <div class="badge _success _sm">
                      <svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
                      +15.6%
                    </div>
                  </div>
                </td>
                <td>
                  <div class="td">
                    <span class="nowrap-text">963 ₽</span>
                    <div class="badge _danger _sm">
                      <svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-down"></use></svg>
                      +15.6%
                    </div>
                  </div>
                </td>
              </tr>
              <tr class="lavender">
                <td>
                  <div class="td">Дейтелинг Про Иркутск</div>
                </td>
                <td>
                  <div class="td">
                    <span class="nowrap-text">90,190.55 ₽</span>
                    <div class="badge _success _sm">
                      <svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
                      +15.6%
                    </div>
                  </div>
                </td>
                <td>
                  <div class="td">
                    <span>120,302</span>
                    <div class="badge _success _sm">
                      <svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
                      +15.6%
                    </div>
                  </div>
                </td>
                <td>
                  <div class="td">
                    <span>967</span>
                    <div class="badge _success _sm">
                      <svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
                      +15.6%
                    </div>
                  </div>
                </td>
                <td>
                  <div class="td">
                    <span class="nowrap-text">9,63 ₽</span>
                    <div class="badge _success _sm">
                      <svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
                      +15.6%
                    </div>
                  </div>
                </td>
                <td>
                  <div class="td">
                    <span class="nowrap-text">130 шт.</span>
                    <div class="badge _success _sm">
                      <svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-up"></use></svg>
                      +15.6%
                    </div>
                  </div>
                </td>
                <td>
                  <div class="td">
                    <span class="nowrap-text">963 ₽</span>
                    <div class="badge _danger _sm">
                      <svg class="badge__icon"><use href="/admirra/img/svg/sprite.svg#rating-down"></use></svg>
                      +15.6%
                    </div>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
  
      <div class="white-block radius-normal mb-4">
        <div class="py-2 mb-5">
          <h4 class="mb-3 text-20 weight-500 gray500">Лучшие посты</h4>
          <p class="text-15 weight-300 gray56">По эффективности за период </p>
        </div>
        <div class="best-post">
          <a class="best-post__item" href="#">
            <picture class="best-post__picture">
              <img src="/admirra/img/best-posts/01.jpg" alt="#" />
            </picture>
          </a>
          <a class="best-post__item" href="#">
            <picture class="best-post__picture">
              <img src="/admirra/img/best-posts/02.jpg" alt="#" />
            </picture>
          </a>
          <a class="best-post__item" href="#">
            <picture class="best-post__picture">
              <img src="/admirra/img/best-posts/03.jpg" alt="#" />
            </picture>
          </a>
          <a class="best-post__item" href="#">
            <picture class="best-post__picture">
              <img src="/admirra/img/best-posts/04.jpg" alt="#" />
            </picture>
          </a>
        </div>
      </div>
  
      <div class="white-block radius-normal mb-4">
        <div class="row g-4 mb-5">
          <div class="col-auto pe-5">
            <div class="d-flex">
              <div class="iconbox _light _lg">
                <svg class="_wallet"><use href="/admirra/img/svg/sprite.svg#wallet"></use></svg>
              </div>
              <div class="ps-4 align-self-center">
                <h4 class="data-card__header-title mb-3 text-20 weight-500 gray500">Комментарий к отчету</h4>
                <p class="text-15 weight-300 gray56">за отчетный период</p>
              </div>
            </div>
          </div>
          <div class="col-auto">
            <button class="btn _outline-gray">
              <div class="btn__inner">
                <span class="btn__text">Редактировать</span>
                <div class="btn__icon ms-2">
                  <svg><use href="/admirra/img/svg/sprite.svg#edit-pen"></use></svg>
                </div>
              </div>
            </button>
          </div>
        </div>
        <div class="col-12 col-xl-11 text-15 lh-150 gray500">
          <p class="weight-600 mb-5 pb-3">
            Анализ эффективности услуг показал, что при правильном распределения количества заказов по услугам (при неизменном количестве клиентов, заказов и&nbsp;стоимости услуг), выручку <span class="nowrap-text">с 7 518 180,00</span> рублей можно увеличить до <span class="nowrap-text">8 424 100,00.</span> То есть дополнительная выручка составит <span class="nowrap-text">905 920,00 рублей.</span> Если перераспределение количества услуг выполнить невозможно (или невозможно в полном объёме),
            необходимо изменить тарификацию услуг с максимальным приближением по выручке на 1% заказов.
          </p>
          <p class="mb-5 pb-3">
            Из отчёта видно, что самой объединяющей услугой является Ликвидация последствий. Вместе с этой услугой чаще всего приобретают Анализ состояния, Сосредоточение внимания, Нагнетание тумана и Утепление фасада. Таким образом, клиенты приобретающие услугу Ликвидация последствий без сопутствующих услуг, с наибольшей вероятностью приобретут вышеперечисленные сопутствующие услуги. Исходя из этого необходимо формировать задание отделу продаж, а отделу маркетинга планировать
            соответствующие маркетинговые активности (акции, распродажи и т. д.).
          </p>
          <p class="mb-5 pb-3">
            Когортный анализ выручки позволяет: <br />
            • оценить степень вклада каждого поколения клиентов в общую выручку;<br />
            • определить время жизни каждого поколения покупателей; <br />
            • зафиксировать период массового оттока поколения;<br />
            • определить целесообразность дополнительных исследований в случае явного «вымирания» поколений
          </p>
          <p class="pb-3">
            Из отчёта видно, что самой объединяющей услугой является Ликвидация последствий. Вместе с этой услугой чаще всего приобретают Анализ состояния, Сосредоточение внимания, Нагнетание тумана и Утепление фасада. Таким образом, клиенты приобретающие услугу Ликвидация последствий без сопутствующих услуг, с наибольшей вероятностью приобретут вышеперечисленные сопутствующие услуги. Исходя из этого необходимо формировать задание отделу продаж, а отделу маркетинга планировать
            соответствующие маркетинговые активности (акции, распродажи и т. д.).
          </p>
        </div>
      </div>
  
      <div class="row g-4 py-4">
        <div class="col-12 col-sm m-0"></div>
        <div class="col-12 col-sm-auto">
          <a class="btn _primary w-100" href="#">
            <div class="btn__inner">
              <span class="btn__text">Скачать отчет в&nbsp;PDF</span>
              <div class="btn__icon">
                <svg class="_download"><use href="/admirra/img/svg/sprite.svg#download"></use></svg>
              </div>
            </div>
          </a>
        </div>
        <div class="col-12 col-sm-auto">
          <a class="btn _primary w-100" href="#">
            <div class="btn__inner">
              <span class="btn__text">Скачать отчет в&nbsp;Telegram</span>
              <div class="btn__icon">
                <svg class="_download"><use href="/admirra/img/svg/sprite.svg#download"></use></svg>
              </div>
            </div>
          </a>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useProjects } from '../../composables/useProjects'

const router = useRouter()
const { projects, currentProject, currentProjectName, fetchProjects, isLoading } = useProjects()

const calendarIcon = '/admirra/img/svg/sprite.svg#datepiker'
const arrowIcon = '/admirra/img/svg/sprite.svg#arrow'
const upIcon = '/admirra/img/svg/sprite.svg#up'

const title = computed(() =>
  currentProject.value
    ? `Обзор проекта: ${currentProject.value.name}`
    : 'Общий обзор'
)
const subtitle = 'Аналитика по активным проектам'
const statsCards = computed(() => [
  {
    title: 'Проектов',
    subtitle: 'Всего в аккаунте',
    value: String(projects.value.length),
    change: '',
    trendValue: '',
    trendLabel: '',
    icon: '/admirra/img/svg/sprite.svg#diagrama',
    iconClass: '_blue',
    badgeClass: '_info',
    badgeIcon: ''
  },
  {
    title: 'Интеграций',
    subtitle: 'Всего подключено',
    value: String(projects.value.reduce((acc, p) => acc + (p.integrations?.length || 0), 0)),
    change: '',
    trendValue: '',
    trendLabel: '',
    icon: '/admirra/img/svg/sprite.svg#wallet',
    iconClass: '_green',
    badgeClass: '_success',
    badgeIcon: ''
  }
])

const tableTitle = 'Проекты'
const tableSubtitle = 'Список всех ваших проектов'
const tableHeaders = ['Название', 'Кол-во интеграций']
const tableData = computed(() =>
  projects.value.map(p => ({
    name: p.name,
    variant: '',
    cells: [{ value: String(p.integrations?.length || 0), change: '', badgeClass: '', badgeIcon: '' }]
  }))
)

onMounted(async () => {
  await fetchProjects()
  if (projects.value.length === 0 && !isLoading.value) {
    router.push('/create')
    return
  }
  setTimeout(() => {
    if (window.jQuery) {
      window.jQuery('select').niceSelect('destroy')
      window.jQuery('select').niceSelect()
    }
    if (window.AirDatepicker) {
      new window.AirDatepicker('#datepikerProjectReport', {
        multipleDates: 2,
        selectedDates: ['2026-04-01', '2026-04-30'],
        range: true,
        multipleDatesSeparator: ' - '
      })
    }
  }, 150)
})
</script>

<style scoped>
.admirra-page-wrapper {
  /* Scoped styles */
}
</style>