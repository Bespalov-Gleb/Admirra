<template>
  <div class="admirra-page-wrapper">
    <section class="main-section">
      <div class="row gy-3 pb-5">
        <div v-for="platform in availablePlatforms" :key="platform.id" class="col-auto">
          <button class="btn _sm _white _radius" @click="$emit('add-platform', platform)">
            <div class="btn__inner">
              <div class="btn__icon-img">
                <img class="img-cover" :src="platform.icon" alt="#" />
              </div>
              <span :class="['btn__text weight-400', platform.textClass]">{{ platform.name }}</span>
              <div class="btn__icon-info ms-2">
                <svg><use :href="plusBoldIcon"></use></svg>
              </div>
            </div>
          </button>
        </div>
      </div>
      <div class="section-header pt-4">
        <h3 class="heading-3">{{ activeTitle }}</h3>
      </div>
      <div class="row gy-4 mb-5">
        <div class="col-auto">
          <button class="btn _primary" @click="$emit('add-connection')">
            <div class="btn__inner">
              <span class="btn__text">{{ addButtonLabel }}</span>
              <div class="btn__icon-plus">+</div>
            </div>
          </button>
        </div>
        <div class="col-12 col-sm-auto">
          <div class="input-item">
            <input class="input w-100" type="text" :placeholder="searchPlaceholder" @input="$emit('search', $event.target.value)" />
            <div class="input-icon">
              <svg class="_stroke"><use :href="searchIcon"></use></svg>
            </div>
          </div>
        </div>
      </div>
      <div class="row g-4">
        <div v-for="(integration, idx) in activeIntegrations" :key="idx" class="col-12 col-sm-11 col-md-9 col-lg-8 col-xl-6">
          <div class="integration-card">
            <div class="integration-card__header">
              <div class="row weight-500">
                <div class="col-auto">
                  <div class="avatar-36x36">
                    <img class="img-cover" :src="integration.projectAvatar" alt="#" />
                  </div>
                </div>
                <div class="col">
                  <div class="mb-1 gray56">Проект</div>
                  <div class="text-15 gray">{{ integration.projectName }}</div>
                </div>
              </div>
              <div class="ms-sm-auto">
                <div class="caption _light _md">{{ integration.channelCount }} КАНАЛ</div>
              </div>
            </div>
            <div class="integration-card__content">
              <div class="row gy-3 mb-3">
                <div class="col-12 col-sm">
                  <div class="row">
                    <div class="col-auto">
                      <div class="avatar-33x33">
                        <img class="img-cover" :src="integration.platformIcon" alt="#" />
                      </div>
                    </div>
                    <div class="col">
                      <div class="text-15 gray mb-1">{{ integration.platformName }}</div>
                      <div class="d-flex flex-wrap">
                        <span :class="['dotty align-self-center me-2', integration.statusClass]"></span>
                        <span class="gray56 uppercase">{{ integration.statusLabel }}</span>
                        <span class="px-1 gray56 text-10">|</span>
                        <time class="gray30">{{ integration.lastUpdate }}</time>
                      </div>
                    </div>
                  </div>
                </div>
                <div class="col-auto">
                  <div class="badge-text _md">
                    <span class="weight-500">{{ integration.refreshPeriod }}</span>
                    <svg class="badge-text__icon _stroke"><use :href="refreshIcon"></use></svg>
                  </div>
                </div>
              </div>
              <div class="row gy-3 align-items-end">
                <div class="col-12 col-sm-auto">
                  <div class="caption w-100">ID: {{ integration.externalId }}</div>
                </div>
                <div class="col-12 col-sm-auto ms-auto">
                  <button class="btn _sm _white w-100" @click="$emit('configure', integration)">
                    <div class="btn__inner px-4">
                      <span class="btn__text weight-400 c71663e">Настроить</span>
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
  availablePlatforms: {
    type: Array,
    default: () => [
      { id: 'yandex', name: 'Yandex Direct', icon: '/admirra/img/icons/yandex-direct.png', textClass: 'c71663e' },
      { id: 'vk', name: 'ВК Ads', icon: '/admirra/img/icons/vk-ads.png', textClass: 'c254b78' }
    ]
  },
  activeTitle: { type: String, default: 'Активные интеграции' },
  addButtonLabel: { type: String, default: 'Добавить подключение' },
  searchPlaceholder: { type: String, default: 'Поиск цели' },
  activeIntegrations: {
    type: Array,
    default: () => [
      { 
        projectName: 'ЖК Сливки / Яндекс', 
        projectAvatar: '/admirra/img/avatars/user.jpg', 
        channelCount: 1, 
        platformName: 'Yandex Direct', 
        platformIcon: '/admirra/img/icons/yandex-direct.png', 
        statusLabel: 'Активно', 
        statusClass: '_success', 
        lastUpdate: 'Последняя: 00:10, 11 мар.', 
        refreshPeriod: '24 часа', 
        externalId: 'SLIVKI-ASA-3830-GUPG' 
      }
    ]
  },
  plusBoldIcon: { type: String, default: '/admirra/img/svg/sprite.svg#plus-bold' },
  searchIcon: { type: String, default: '/admirra/img/svg/sprite.svg#search' },
  refreshIcon: { type: String, default: '/admirra/img/svg/sprite.svg#refresh-line' }
})

defineEmits(['add-platform', 'add-connection', 'search', 'configure'])
</script>

<style scoped>
.admirra-page-wrapper {
  /* Scoped styles */
}
</style>
