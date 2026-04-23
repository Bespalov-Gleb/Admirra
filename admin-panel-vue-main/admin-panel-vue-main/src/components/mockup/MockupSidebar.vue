<template>
  <aside :class="['main-aside d-none d-xxxl-flex', { '_collapsed': isCollapsed }]">
    <nav class="navigation">
      <div v-for="item in navItems" :key="item.id" :class="['navigation-item', { subMenu: item.children }]">
        <button 
          v-if="!item.route" 
          class="navigation-link" 
          @click="$emit('nav-click', item)"
        >
          <i class="navigation-icon">
            <svg :class="item.iconClass"><use :href="item.icon"></use></svg>
            <span v-if="item.emoji">{{ item.emoji }}</span>
          </i>
          <span class="navigation-text">{{ item.label }}</span>
          <div v-if="item.children" class="circle-arrow">
            <svg><use :href="arrowIcon"></use></svg>
          </div>
        </button>
        <router-link 
          v-else 
          class="navigation-link" 
          :to="item.route"
        >
          <i class="navigation-icon">
            <svg :class="item.iconClass"><use :href="item.icon"></use></svg>
            <span v-if="item.emoji">{{ item.emoji }}</span>
          </i>
          <span class="navigation-text">{{ item.label }}</span>
        </router-link>

        <div v-if="item.children" class="navigation-submenu">
          <div v-for="child in item.children" :key="child.id" class="navigation-subitem">
            <router-link v-if="child.route" class="navigation-sublink" :to="child.route">{{ child.label }}</router-link>
            <button v-else class="navigation-sublink" @click="$emit('nav-click', child)">{{ child.label }}</button>
          </div>
        </div>
      </div>
    </nav>
    <div class="mt-auto">
      <hr class="hr-line" />
      <nav class="navigation my-2">
        <div class="navigation-item mb-0">
          <button class="navigation-link" @click="$emit('support')">
            <i class="navigation-icon">
              <svg><use :href="questionIcon"></use></svg>
            </i>
            <span class="navigation-text">{{ supportLabel }}</span>
          </button>
        </div>
      </nav>
    </div>
  </aside>
</template>

<script setup>
defineProps({
  isCollapsed: { type: Boolean, default: false },
  navItems: {
    type: Array,
    default: () => [
      { 
        id: 'analytics', 
        label: 'Аналитика', 
        icon: '/admirra/img/svg/sprite.svg#grid', 
        iconClass: '_stroke',
        children: [
          { id: 'analytics-project', label: 'Аналитика проекта', route: '/main' },
          { id: 'analytics-ai', label: 'AI отчет по проекту' }
        ]
      },
      { id: 'projects', label: 'Проекты', icon: '/admirra/img/svg/sprite.svg#layers', route: '/project-rows' },
      { id: 'integrations', label: 'Интеграции', icon: '/admirra/img/svg/sprite.svg#setting', route: '/integrations' },
      { id: 'team', label: 'Команда', icon: '/admirra/img/svg/sprite.svg#group' },
      { id: 'history', label: 'История', icon: '/admirra/img/svg/sprite.svg#clock' },
      { id: 'tariffs', label: 'Тарифы', emoji: '👑', route: '/tariffs' }
    ]
  },
  supportLabel: { type: String, default: 'Поддержка' },
  arrowIcon: { type: String, default: '/admirra/img/svg/sprite.svg#arrow' },
  questionIcon: { type: String, default: '/admirra/img/svg/sprite.svg#question' }
})

defineEmits(['nav-click', 'support'])
</script>

<style scoped>
/* Scoped styles */
.navigation-link, .navigation-sublink {
  background: none;
  border: none;
  width: 100%;
  text-align: left;
  cursor: pointer;
  display: flex;
  align-items: center;
}
</style>
