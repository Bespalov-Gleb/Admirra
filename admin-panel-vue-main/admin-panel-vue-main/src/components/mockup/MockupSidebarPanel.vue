<template>
  <div class="sidebar-panel">
    <div class="sidebar-panel__aside">
      <div class="p-4 pb-0 d-xl-none">
        <div class="dropdown d-block">
          <button class="dropdown-head w-100" @click="$emit('toggle-project-select')">
            <div class="avatar-36x36"><img class="img-cover" :src="userAvatar" alt="#" /></div>
            <div class="dropdown-head__info">
              <div>{{ agencyName }}</div>
              <div class="_subtext">{{ agencyDescription }}</div>
            </div>
            <div class="circle-arrow">
              <svg><use :href="arrowIcon"></use></svg>
            </div>
          </button>
        </div>
      </div>
      <nav class="navigation">
        <div v-for="(item, idx) in navItems" :key="idx" :class="['navigation-item', { subMenu: item.subItems }]">
          <button v-if="item.subItems" class="navigation-link w-100" @click="$emit('toggle-submenu', item)">
            <i class="navigation-icon">
              <svg :class="{ _stroke: item.isStroke }"><use :href="item.icon"></use></svg>
            </i>
            <span class="navigation-text">{{ item.label }}</span>
            <div class="circle-arrow">
              <svg><use :href="arrowIcon"></use></svg>
            </div>
          </button>
          <router-link v-else-if="item.route" class="navigation-link w-100" :to="item.route" @click="$emit('close')">
            <i class="navigation-icon">
              <svg :class="{ _stroke: item.isStroke }"><use :href="item.icon"></use></svg>
            </i>
            <span class="navigation-text">{{ item.label }}</span>
          </router-link>
          <button v-else class="navigation-link w-100" @click="$emit('navigate', item)">
            <i class="navigation-icon">
              <svg :class="{ _stroke: item.isStroke }"><use :href="item.icon"></use></svg>
            </i>
            <span class="navigation-text">{{ item.label }}</span>
          </button>
        </div>
      </nav>
      <div class="mt-auto">
        <hr class="hr-line" />
        <div class="px-4 py-5">
          <div class="row g-3">
            <div class="col-12">
              <button class="btn _primary d-flex w-100" @click="$emit('upgrade-tariff')">
                <div class="btn__inner">
                  <span class="btn__text">{{ upgradeLabel }}</span>
                  <div class="btn__icon-plus">+</div>
                </div>
              </button>
            </div>
          </div>
        </div>
        <hr class="hr-line" />
        <div class="navigation my-2">
          <div class="navigation-item mb-0">
            <button class="navigation-link w-100" @click="$emit('support')">
              <i class="navigation-icon">
                <svg><use :href="questionIcon"></use></svg>
              </i>
              <span class="navigation-text">Поддержка</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  userAvatar: { type: String, default: '/admirra/img/avatars/avatar-36x36.png' },
  agencyName: { type: String, default: 'Трафик агентство' },
  agencyDescription: { type: String, default: 'Отчеты агентства в одном месте' },
  upgradeLabel: { type: String, default: 'Перейти на тариф Старт' },
  navItems: {
    type: Array,
    default: () => [
      { label: 'Аналитика', icon: '/admirra/img/svg/sprite.svg#grid', isStroke: true, subItems: true },
      { label: 'Проекты', icon: '/admirra/img/svg/sprite.svg#layers', route: '/project-rows' },
      { label: 'Интеграции', icon: '/admirra/img/svg/sprite.svg#setting', route: '/integrations' }
    ]
  },
  arrowIcon: { type: String, default: '/admirra/img/svg/sprite.svg#arrow' },
  questionIcon: { type: String, default: '/admirra/img/svg/sprite.svg#question' }
})

defineEmits(['toggle-project-select', 'toggle-submenu', 'navigate', 'upgrade-tariff', 'support'])
</script>

<style scoped>
.sidebar-panel {
  /* Scoped styles */
}
.navigation-link {
  background: none;
  border: none;
  text-align: left;
  display: flex;
  align-items: center;
}
</style>
