<template>
  <aside :class="['main-aside d-none d-xxxl-flex', { '_collapsed': isCollapsed }]">
    <nav class="navigation">
      <div
        v-for="item in navItems"
        :key="item.id"
        :class="['navigation-item', { subMenu: item.children, 'is-open': openItems.includes(item.id) }]"
      >
        <!-- Пункт с подменю -->
        <button
          v-if="item.children"
          class="navigation-link"
          @click="toggleItem(item.id)"
        >
          <i class="navigation-icon">
            <svg :class="item.iconClass"><use :href="item.icon"></use></svg>
            <span v-if="item.emoji">{{ item.emoji }}</span>
          </i>
          <span class="navigation-text">{{ item.label }}</span>
          <div class="circle-arrow">
            <svg><use :href="arrowIcon"></use></svg>
          </div>
        </button>

        <!-- Пункт-ссылка -->
        <router-link
          v-else
          class="navigation-link"
          :to="item.route"
        >
          <i class="navigation-icon">
            <svg v-if="item.icon" :class="item.iconClass"><use :href="item.icon"></use></svg>
            <span v-if="item.emoji">{{ item.emoji }}</span>
          </i>
          <span class="navigation-text">{{ item.label }}</span>
        </router-link>

        <!-- Подменю -->
        <div v-if="item.children" class="navigation-submenu">
          <div v-for="child in item.children" :key="child.id" class="navigation-subitem">
            <router-link v-if="child.route" class="navigation-sublink" :to="child.route">
              {{ child.label }}
            </router-link>
            <button v-else class="navigation-sublink" @click="$emit('nav-click', child)">
              {{ child.label }}
            </button>
          </div>
        </div>
      </div>
    </nav>

    <div class="mt-auto">
      <hr class="hr-line" />
      <nav class="navigation my-2">
        <div class="navigation-item mb-0">
          <router-link class="navigation-link" to="/contact">
            <i class="navigation-icon">
              <svg><use :href="questionIcon"></use></svg>
            </i>
            <span class="navigation-text">{{ supportLabel }}</span>
          </router-link>
        </div>
      </nav>
    </div>
  </aside>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const props = defineProps({
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
          { id: 'analytics-project', label: 'Аналитика проекта', route: '/dashboard/general-3' },
          { id: 'analytics-ai', label: 'AI отчет по проекту', route: '/ai-analysis' }
        ]
      },
      { id: 'projects', label: 'Проекты', icon: '/admirra/img/svg/sprite.svg#layers', route: '/project-rows' },
      { id: 'integrations', label: 'Интеграции', icon: '/admirra/img/svg/sprite.svg#setting', route: '/integrations' },
      { id: 'team', label: 'Команда', icon: '/admirra/img/svg/sprite.svg#group', route: '/team' },
      { id: 'history', label: 'История', icon: '/admirra/img/svg/sprite.svg#clock', route: '/history' },
      { id: 'tariffs', label: 'Тарифы', icon: '/admirra/img/svg/sprite.svg#wallet', route: '/tariffs' }
    ]
  },
  supportLabel: { type: String, default: 'Поддержка' },
  arrowIcon: { type: String, default: '/admirra/img/svg/sprite.svg#arrow' },
  questionIcon: { type: String, default: '/admirra/img/svg/sprite.svg#question' }
})

defineEmits(['nav-click'])

// Раскрытые группы
const openItems = ref([])

// Автоматически раскрываем группу, если текущий маршрут — дочерний элемент
const initOpenItems = () => {
  props.navItems.forEach(item => {
    if (item.children) {
      const isActive = item.children.some(child => child.route && route.path.startsWith(child.route))
      if (isActive && !openItems.value.includes(item.id)) {
        openItems.value.push(item.id)
      }
    }
  })
}
initOpenItems()

const toggleItem = (id) => {
  const idx = openItems.value.indexOf(id)
  if (idx > -1) {
    openItems.value.splice(idx, 1)
  } else {
    openItems.value.push(id)
  }
}
</script>

<style scoped>
.navigation-link,
.navigation-sublink {
  background: none;
  border: none;
  width: 100%;
  text-align: left;
  cursor: pointer;
  display: flex;
  align-items: center;
}

/* Скрываем подменю когда группа не открыта */
.navigation-item:not(.is-open) .navigation-submenu {
  display: none !important;
}

/* Показываем подменю когда группа открыта */
.navigation-item.is-open .navigation-submenu {
  display: flex !important;
  flex-direction: column;
}
</style>
