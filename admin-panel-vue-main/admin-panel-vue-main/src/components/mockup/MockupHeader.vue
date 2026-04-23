<template>
  <header class="header">
    <div class="header__inner">
      <div class="header__aside">
        <router-link class="logo" :to="logoLink">AdMirra</router-link>
        <button class="header__aside-btn d-none d-xxxl-block" @click="$emit('toggle-sidebar-size')">
          <div class="circle-arrow _light">
            <svg><use :href="arrowIcon"></use></svg>
          </div>
        </button>
      </div>
      <div class="header__content">
        <div class="row gy-2">
          <div class="col-auto">
            <div class="row gy-2 align-items-center">
              <div class="col-auto d-none d-xl-block">
                <div class="dropdown">
                  <button class="dropdown-head" @click="$emit('toggle-project-menu')">
                    <div class="avatar-36x36"><img class="img-cover" :src="currentProjectAvatar" alt="#" /></div>
                    <div class="dropdown-head__info">
                      <div>{{ currentProjectName }}</div>
                      <div class="_subtext">{{ currentProjectSubtitle }}</div>
                    </div>
                    <div class="circle-arrow">
                      <svg><use :href="arrowIcon"></use></svg>
                    </div>
                  </button>
                  <div class="dropdown-body" v-if="projectMenuOpen">
                    <div class="dropdown-block pt-4 pb-2 weight-500">
                      <h6 class="text-12 uppercase gray56 px-4 py-2">Мои проекты</h6>
                      <ul class="dropdown-menu text-14 mb-2">
                        <li v-for="project in projects" :key="project.id">
                          <button class="dropdown-menu__link" :class="{ active: project.active }" @click="$emit('select-project', project)">
                            <span>{{ project.name }}</span>
                          </button>
                        </li>
                      </ul>
                      <button class="dropdown-link" @click="$emit('create-project')">
                        <svg class="dropdown-link__icon _stroke"><use :href="plusIcon"></use></svg>
                        <span>Создать новый проект</span>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
              <div class="col-auto d-none d-xxl-block">
                <div class="d-flex align-items-center">
                  <div class="px-4">
                    <div class="mb-1 weight-500 gray500">Ваш тариф: <b class="weight-700">{{ tariffName }}</b></div>
                    <div class="text-10 gray60">Действует до {{ tariffExpiry }}</div>
                  </div>
                  <div class="ps-2 ms-1">
                    <button class="btn _outline-primary" @click="$emit('renew-tariff')">
                      <div class="btn__inner">
                        <span class="btn__text">Продлить</span>
                      </div>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="col-auto align-self-center ms-auto">
            <div class="row gy-2 align-items-center">
              <div class="col-auto d-none d-lg-block">
                <button class="btn" @click="$emit('suggest-idea')">
                  <div class="btn__inner">
                    <span class="btn__text">Предложить идею</span>
                    <div class="btn__icon">
                      <svg><use :href="ideaIcon"></use></svg>
                    </div>
                  </div>
                </button>
              </div>
              <div class="col-auto">
                <div class="dropdown">
                  <button class="dropdown-head _no-style" @click="$emit('toggle-notifications')">
                    <div class="btn-ui">
                      <div class="btn-ui__icon">
                        <svg><use :href="bellIcon"></use></svg>
                      </div>
                      <div v-if="unreadCount > 0" class="btn-ui__helper">{{ unreadCount }}</div>
                    </div>
                  </button>
                </div>
              </div>
              <div class="col-auto">
                <div class="dropdown _normal">
                  <button class="dropdown-head" @click="$emit('toggle-profile-menu')">
                    <div class="avatar-30x30"><img class="img-cover" :src="userAvatar" alt="#" /></div>
                    <div class="dropdown-head__info d-none d-md-flex">{{ userName }}</div>
                    <div class="circle-arrow">
                      <svg><use :href="arrowIcon"></use></svg>
                    </div>
                  </button>
                </div>
              </div>
              <div class="col-auto d-xxxl-none">
                <div class="burger" @click="$emit('toggle-mobile-menu')">
                  <div class="burger__icon">
                    <div class="_top"></div>
                    <div class="_center"></div>
                    <div class="_bottom"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup>
defineProps({
  logoLink: { type: String, default: '/' },
  currentProjectName: { type: String, default: 'Трафик агентство' },
  currentProjectSubtitle: { type: String, default: 'Отчеты агентства в одном месте' },
  currentProjectAvatar: { type: String, default: '/admirra/img/avatars/avatar-36x36.png' },
  projectMenuOpen: { type: Boolean, default: false },
  projects: {
    type: Array,
    default: () => [
      { id: 'all', name: 'Все проекты', active: false },
      { id: 1, name: 'Admirra', active: false },
      { id: 2, name: 'Fisherman', active: true }
    ]
  },
  tariffName: { type: String, default: 'Старт' },
  tariffExpiry: { type: String, default: '31.05.2026' },
  unreadCount: { type: Number, default: 2 },
  userName: { type: String, default: 'Дмитрий Степанов' },
  userAvatar: { type: String, default: '/admirra/img/avatars/avatar-30x30.png' },
  arrowIcon: { type: String, default: '/admirra/img/svg/sprite.svg#arrow' },
  plusIcon: { type: String, default: '/admirra/img/svg/sprite.svg#plus' },
  ideaIcon: { type: String, default: '/admirra/img/svg/sprite.svg#idea' },
  bellIcon: { type: String, default: '/admirra/img/svg/sprite.svg#bell' }
})

defineEmits([
  'toggle-sidebar-size', 
  'toggle-project-menu', 
  'select-project', 
  'create-project', 
  'renew-tariff', 
  'suggest-idea', 
  'toggle-notifications', 
  'toggle-profile-menu', 
  'toggle-mobile-menu'
])
</script>

<style scoped>
/* Scoped styles */
.dropdown-menu__link {
  background: none;
  border: none;
  width: 100%;
  text-align: left;
  cursor: pointer;
}
.dropdown-link {
  background: none;
  border: none;
  width: 100%;
  text-align: left;
  cursor: pointer;
  display: flex;
  align-items: center;
}
</style>
