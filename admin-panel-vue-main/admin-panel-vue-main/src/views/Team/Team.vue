<template>
  <section class="main-section">
    <div class="section-header pt-4">
      <h3 class="heading-3">Команда</h3>
    </div>
    <div class="row gy-3 mb-5">
      <div class="col">
        <div class="row gy-3">
          <div class="col-auto">
            <a class="btn _primary" href="#">
              <div class="btn__inner">
                <span class="btn__text">Сотрудники</span>
              </div>
            </a>
          </div>
          <div class="col-auto">
            <a class="btn _white" href="#">
              <div class="btn__inner">
                <span class="btn__text gray">Клиенты</span>
              </div>
            </a>
          </div>
        </div>
      </div>
      <div class="col-auto">
        <button class="btn _primary">
          <div class="btn__inner">
            <span class="btn__text">Добавить сотрудника</span>
            <div class="btn__icon-plus">+</div>
          </div>
        </button>
      </div>
    </div>
    <div class="mb-4 pb-2">
      <div class="team-item is-open">
        <div class="row team-item__header">
          <div class="col col-lg-4 col-xl-3">
            <div class="d-flex">
              <div class="avatar-36x36 me-4">
                <img class="img-cover" src="/admirra/img/avatars/user1.jpg" alt="#" />
              </div>
              <div class="weight-500">
                <div class="mb-1 text-15 gray">Петр Петров</div>
                <div class="gray56">testemail@mail.ru</div>
              </div>
            </div>
          </div>
          <div class="col-auto col-lg">
            <button class="team-item__project-toggle">
              <span>Доступ к проектам</span>
              <div class="circle-arrow _light">
                <svg><use href="/admirra/img/svg/sprite.svg#arrow"></use></svg>
              </div>
            </button>
          </div>
          <div class="col-12 col-lg-auto">
            <div class="row">
              <div class="col col-lg-auto">
                <button class="btn _primary">
                  <div class="btn__inner">
                    <span class="btn__text">Добавить доступ к&nbsp;проекту</span>
                    <div class="btn__icon-plus">+</div>
                  </div>
                </button>
              </div>
              <div class="col-auto col-lg-auto">
                <button class="btn-action _danger">
                  <svg><use href="/admirra/img/svg/sprite.svg#basket"></use></svg>
                </button>
              </div>
            </div>
          </div>
        </div>
        <div class="team-item__project-content row g-4">
          <div class="col-12 col-sm-auto">
            <div class="card-base _oldlace">
              <div class="avatar-30x30 mb-2">
                <img class="img-cover" src="/admirra/img/avatars/avatar-36x36.png" alt="#" />
              </div>
              <div class="weight-500 gray500">ЖК Сливки / Яндекс</div>
              <a class="btn _sm _white mt-auto" href="#">
                <div class="btn__inner">
                  <span class="btn__text gray">Отозвать доступ</span>
                </div>
              </a>
            </div>
          </div>
          <div class="col-12 col-sm-auto">
            <div class="card-base _aliceblue">
              <div class="avatar-30x30 mb-2">
                <img class="img-cover" src="/admirra/img/avatars/avatar-36x36.png" alt="#" />
              </div>
              <div class="weight-500 gray500">Дейтелинг Иркутск</div>
              <a class="btn _sm _white mt-auto" href="#">
                <div class="btn__inner">
                  <span class="btn__text gray">Отозвать доступ</span>
                </div>
              </a>
            </div>
          </div>
          <div class="col-12 col-sm-auto">
            <div class="card-base _linen">
              <div class="avatar-30x30 mb-2">
                <img class="img-cover" src="/admirra/img/avatars/avatar-36x36.png" alt="#" />
              </div>
              <div class="weight-500 gray500">Акт Приорити</div>
              <a class="btn _sm _white mt-auto" href="#">
                <div class="btn__inner">
                  <span class="btn__text gray">Отозвать доступ</span>
                </div>
              </a>
            </div>
          </div>
          <div class="col-12 col-sm-auto">
            <div class="card-base _lavender">
              <div class="avatar-30x30 mb-2">
                <img class="img-cover" src="/admirra/img/avatars/avatar-36x36.png" alt="#" />
              </div>
              <div class="weight-500 gray500">Дейтелинг Иркутск</div>
              <a class="btn _sm _white mt-auto" href="#">
                <div class="btn__inner">
                  <span class="btn__text gray">Отозвать доступ</span>
                </div>
              </a>
            </div>
          </div>
          <div class="col-12 col-sm-auto">
            <div class="card-base">
              <div class="avatar-30x30 mb-2">
                <img class="img-cover" src="/admirra/img/avatars/avatar-36x36.png" alt="#" />
              </div>
              <div class="weight-500 gray500">Акт Приорити</div>
              <a class="btn _sm _white mt-auto" href="#">
                <div class="btn__inner">
                  <span class="btn__text gray">Отозвать доступ</span>
                </div>
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div class="mb-4 pb-2">
      <div class="team-item">
        <div class="row team-item__header">
          <div class="col col-lg-4 col-xl-3">
            <div class="d-flex">
              <div class="avatar-36x36 me-4">
                <img class="img-cover" src="/admirra/img/avatars/user2.jpg" alt="#" />
              </div>
              <div class="weight-500">
                <div class="mb-1 text-15 gray">Петр Петров</div>
                <div class="gray56">testemail@mail.ru</div>
              </div>
            </div>
          </div>
          <div class="col-auto col-lg">
            <button class="team-item__project-toggle">
              <span>Доступ к проектам</span>
              <div class="circle-arrow _light">
                <svg><use href="/admirra/img/svg/sprite.svg#arrow"></use></svg>
              </div>
            </button>
          </div>
          <div class="col-12 col-lg-auto">
            <div class="row">
              <div class="col col-lg-auto">
                <button class="btn _primary">
                  <div class="btn__inner">
                    <span class="btn__text">Добавить доступ к&nbsp;проекту</span>
                    <div class="btn__icon-plus">+</div>
                  </div>
                </button>
              </div>
              <div class="col-auto col-lg-auto">
                <button class="btn-action _danger">
                  <svg><use href="/admirra/img/svg/sprite.svg#basket"></use></svg>
                </button>
              </div>
            </div>
          </div>
        </div>
        <div class="team-item__project-content row g-4">
          <div class="col-12 col-sm-auto">
            <div class="card-base _oldlace">
              <div class="avatar-30x30 mb-2">
                <img class="img-cover" src="/admirra/img/avatars/avatar-36x36.png" alt="#" />
              </div>
              <div class="weight-500 gray500">ЖК Сливки / Яндекс</div>
              <a class="btn _sm _white mt-auto" href="#">
                <div class="btn__inner">
                  <span class="btn__text gray">Отозвать доступ</span>
                </div>
              </a>
            </div>
          </div>
          <div class="col-12 col-sm-auto">
            <div class="card-base _aliceblue">
              <div class="avatar-30x30 mb-2">
                <img class="img-cover" src="/admirra/img/avatars/avatar-36x36.png" alt="#" />
              </div>
              <div class="weight-500 gray500">Дейтелинг Иркутск</div>
              <a class="btn _sm _white mt-auto" href="#">
                <div class="btn__inner">
                  <span class="btn__text gray">Отозвать доступ</span>
                </div>
              </a>
            </div>
          </div>
          <div class="col-12 col-sm-auto">
            <div class="card-base _linen">
              <div class="avatar-30x30 mb-2">
                <img class="img-cover" src="/admirra/img/avatars/avatar-36x36.png" alt="#" />
              </div>
              <div class="weight-500 gray500">Акт Приорити</div>
              <a class="btn _sm _white mt-auto" href="#">
                <div class="btn__inner">
                  <span class="btn__text gray">Отозвать доступ</span>
                </div>
              </a>
            </div>
          </div>
          <div class="col-12 col-sm-auto">
            <div class="card-base _lavender">
              <div class="avatar-30x30 mb-2">
                <img class="img-cover" src="/admirra/img/avatars/avatar-36x36.png" alt="#" />
              </div>
              <div class="weight-500 gray500">Дейтелинг Иркутск</div>
              <a class="btn _sm _white mt-auto" href="#">
                <div class="btn__inner">
                  <span class="btn__text gray">Отозвать доступ</span>
                </div>
              </a>
            </div>
          </div>
          <div class="col-12 col-sm-auto">
            <div class="card-base">
              <div class="avatar-30x30 mb-2">
                <img class="img-cover" src="/admirra/img/avatars/avatar-36x36.png" alt="#" />
              </div>
              <div class="weight-500 gray500">Акт Приорити</div>
              <a class="btn _sm _white mt-auto" href="#">
                <div class="btn__inner">
                  <span class="btn__text gray">Отозвать доступ</span>
                </div>
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div class="mb-4 pb-2">
      <div class="team-item">
        <div class="row team-item__header">
          <div class="col col-lg-4 col-xl-3">
            <div class="d-flex">
              <div class="avatar-36x36 me-4">
                <img class="img-cover" src="/admirra/img/avatars/user3.jpg" alt="#" />
              </div>
              <div class="weight-500">
                <div class="mb-1 text-15 gray">Петр Петров</div>
                <div class="gray56">testemail@mail.ru</div>
              </div>
            </div>
          </div>
          <div class="col-auto col-lg">
            <button class="team-item__project-toggle">
              <span>Доступ к проектам</span>
              <div class="circle-arrow _light">
                <svg><use href="/admirra/img/svg/sprite.svg#arrow"></use></svg>
              </div>
            </button>
          </div>
          <div class="col-12 col-lg-auto">
            <div class="row">
              <div class="col col-lg-auto">
                <button class="btn _primary">
                  <div class="btn__inner">
                    <span class="btn__text">Добавить доступ к&nbsp;проекту</span>
                    <div class="btn__icon-plus">+</div>
                  </div>
                </button>
              </div>
              <div class="col-auto col-lg-auto">
                <button class="btn-action _danger">
                  <svg><use href="/admirra/img/svg/sprite.svg#basket"></use></svg>
                </button>
              </div>
            </div>
          </div>
        </div>
        <div class="team-item__project-content row g-4">
          <div class="col-12 col-sm-auto">
            <div class="card-base _oldlace">
              <div class="avatar-30x30 mb-2">
                <img class="img-cover" src="/admirra/img/avatars/avatar-36x36.png" alt="#" />
              </div>
              <div class="weight-500 gray500">ЖК Сливки / Яндекс</div>
              <a class="btn _sm _white mt-auto" href="#">
                <div class="btn__inner">
                  <span class="btn__text gray">Отозвать доступ</span>
                </div>
              </a>
            </div>
          </div>
          <div class="col-12 col-sm-auto">
            <div class="card-base _aliceblue">
              <div class="avatar-30x30 mb-2">
                <img class="img-cover" src="/admirra/img/avatars/avatar-36x36.png" alt="#" />
              </div>
              <div class="weight-500 gray500">Дейтелинг Иркутск</div>
              <a class="btn _sm _white mt-auto" href="#">
                <div class="btn__inner">
                  <span class="btn__text gray">Отозвать доступ</span>
                </div>
              </a>
            </div>
          </div>
          <div class="col-12 col-sm-auto">
            <div class="card-base _linen">
              <div class="avatar-30x30 mb-2">
                <img class="img-cover" src="/admirra/img/avatars/avatar-36x36.png" alt="#" />
              </div>
              <div class="weight-500 gray500">Акт Приорити</div>
              <a class="btn _sm _white mt-auto" href="#">
                <div class="btn__inner">
                  <span class="btn__text gray">Отозвать доступ</span>
                </div>
              </a>
            </div>
          </div>
          <div class="col-12 col-sm-auto">
            <div class="card-base _lavender">
              <div class="avatar-30x30 mb-2">
                <img class="img-cover" src="/admirra/img/avatars/avatar-36x36.png" alt="#" />
              </div>
              <div class="weight-500 gray500">Дейтелинг Иркутск</div>
              <a class="btn _sm _white mt-auto" href="#">
                <div class="btn__inner">
                  <span class="btn__text gray">Отозвать доступ</span>
                </div>
              </a>
            </div>
          </div>
          <div class="col-12 col-sm-auto">
            <div class="card-base">
              <div class="avatar-30x30 mb-2">
                <img class="img-cover" src="/admirra/img/avatars/avatar-36x36.png" alt="#" />
              </div>
              <div class="weight-500 gray500">Акт Приорити</div>
              <a class="btn _sm _white mt-auto" href="#">
                <div class="btn__inner">
                  <span class="btn__text gray">Отозвать доступ</span>
                </div>
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div class="mb-4 pb-2">
      <div class="team-item">
        <div class="row team-item__header">
          <div class="col col-lg-4 col-xl-3">
            <div class="d-flex">
              <div class="avatar-36x36 me-4">
                <img class="img-cover" src="/admirra/img/avatars/user4.jpg" alt="#" />
              </div>
              <div class="weight-500">
                <div class="mb-1 text-15 gray">Петр Петров</div>
                <div class="gray56">testemail@mail.ru</div>
              </div>
            </div>
          </div>
          <div class="col-auto col-lg">
            <button class="team-item__project-toggle">
              <span>Доступ к проектам</span>
              <div class="circle-arrow _light">
                <svg><use href="/admirra/img/svg/sprite.svg#arrow"></use></svg>
              </div>
            </button>
          </div>
          <div class="col-12 col-lg-auto">
            <div class="row">
              <div class="col col-lg-auto">
                <button class="btn _primary">
                  <div class="btn__inner">
                    <span class="btn__text">Добавить доступ к&nbsp;проекту</span>
                    <div class="btn__icon-plus">+</div>
                  </div>
                </button>
              </div>
              <div class="col-auto col-lg-auto">
                <button class="btn-action _danger">
                  <svg><use href="/admirra/img/svg/sprite.svg#basket"></use></svg>
                </button>
              </div>
            </div>
          </div>
        </div>
        <div class="team-item__project-content row g-4">
          <div class="col-12 col-sm-auto">
            <div class="card-base _oldlace">
              <div class="avatar-30x30 mb-2">
                <img class="img-cover" src="/admirra/img/avatars/avatar-36x36.png" alt="#" />
              </div>
              <div class="weight-500 gray500">ЖК Сливки / Яндекс</div>
              <a class="btn _sm _white mt-auto" href="#">
                <div class="btn__inner">
                  <span class="btn__text gray">Отозвать доступ</span>
                </div>
              </a>
            </div>
          </div>
          <div class="col-12 col-sm-auto">
            <div class="card-base _aliceblue">
              <div class="avatar-30x30 mb-2">
                <img class="img-cover" src="/admirra/img/avatars/avatar-36x36.png" alt="#" />
              </div>
              <div class="weight-500 gray500">Дейтелинг Иркутск</div>
              <a class="btn _sm _white mt-auto" href="#">
                <div class="btn__inner">
                  <span class="btn__text gray">Отозвать доступ</span>
                </div>
              </a>
            </div>
          </div>
          <div class="col-12 col-sm-auto">
            <div class="card-base _linen">
              <div class="avatar-30x30 mb-2">
                <img class="img-cover" src="/admirra/img/avatars/avatar-36x36.png" alt="#" />
              </div>
              <div class="weight-500 gray500">Акт Приорити</div>
              <a class="btn _sm _white mt-auto" href="#">
                <div class="btn__inner">
                  <span class="btn__text gray">Отозвать доступ</span>
                </div>
              </a>
            </div>
          </div>
          <div class="col-12 col-sm-auto">
            <div class="card-base _lavender">
              <div class="avatar-30x30 mb-2">
                <img class="img-cover" src="/admirra/img/avatars/avatar-36x36.png" alt="#" />
              </div>
              <div class="weight-500 gray500">Дейтелинг Иркутск</div>
              <a class="btn _sm _white mt-auto" href="#">
                <div class="btn__inner">
                  <span class="btn__text gray">Отозвать доступ</span>
                </div>
              </a>
            </div>
          </div>
          <div class="col-12 col-sm-auto">
            <div class="card-base">
              <div class="avatar-30x30 mb-2">
                <img class="img-cover" src="/admirra/img/avatars/avatar-36x36.png" alt="#" />
              </div>
              <div class="weight-500 gray500">Акт Приорити</div>
              <a class="btn _sm _white mt-auto" href="#">
                <div class="btn__inner">
                  <span class="btn__text gray">Отозвать доступ</span>
                </div>
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { onMounted } from 'vue'

onMounted(() => {
  if (window.jQuery) {
    window.jQuery('.team-item__project-toggle').off('click').on('click', function () {
      const $this = window.jQuery(this)
      const parent = $this.closest('.team-item')
      parent.toggleClass('is-open')
      parent.find('.team-item__project-content').slideToggle()
    })
  }
})
</script>
