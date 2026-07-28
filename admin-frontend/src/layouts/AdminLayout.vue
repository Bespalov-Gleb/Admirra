<template>
  <div class="admin-shell">
    <aside class="sidebar">
      <RouterLink class="brand" :to="auth.homeRoute">
        <span><strong>AdMirra</strong><small>внутренняя панель</small></span>
      </RouterLink>

      <nav class="sidebar__nav">
        <template v-for="group in menu" :key="group.label">
          <p class="sidebar__label">{{ group.label }}</p>
          <RouterLink v-for="item in group.items" :key="item.to" :to="item.to">
            <component :is="item.icon" />
            <span>{{ item.label }}</span>
          </RouterLink>
        </template>
      </nav>

      <div class="sidebar__account">
        <RouterLink to="/profile" class="account-card">
          <span class="avatar">{{ initials }}</span>
          <span class="account-card__copy">
            <strong>{{ auth.user?.full_name || auth.user?.email }}</strong>
            <small>{{ roleLabel(auth.role) }}</small>
          </span>
          <ChevronRightIcon />
        </RouterLink>
        <button class="sidebar__logout" @click="logout"><ArrowRightStartOnRectangleIcon />Выйти</button>
      </div>
    </aside>

    <main class="content">
      <header class="topbar">
        <div>
          <span class="topbar__status"><i /> защищённый контур</span>
          <strong>{{ route.meta.title }}</strong>
        </div>
        <div class="topbar__right">
          <span>Москва · {{ currentTime }}</span>
          <button class="icon-button" title="Обновить страницу" @click="router.go(0)"><ArrowPathIcon /></button>
        </div>
      </header>
      <div class="content__inner"><RouterView /></div>
    </main>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  AcademicCapIcon,
  ArrowPathIcon,
  ArrowRightStartOnRectangleIcon,
  BoltIcon,
  ChartBarSquareIcon,
  ChevronRightIcon,
  CircleStackIcon,
  ClockIcon,
  Cog6ToothIcon,
  DocumentTextIcon,
  FingerPrintIcon,
  KeyIcon,
  RectangleStackIcon,
  ShieldCheckIcon,
  UserGroupIcon,
  UsersIcon,
} from '@heroicons/vue/24/outline'
import { useAuthStore } from '../stores/auth'
import { roleLabel } from '../utils/formatters'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const now = ref(new Date())
const timer = window.setInterval(() => { now.value = new Date() }, 30000)
onBeforeUnmount(() => window.clearInterval(timer))

const currentTime = computed(() => new Intl.DateTimeFormat('ru-RU', {
  timeZone: 'Europe/Moscow',
  hour: '2-digit',
  minute: '2-digit',
}).format(now.value))

const initials = computed(() => {
  const value = auth.user?.full_name || auth.user?.email || 'A'
  return value.split(/\s|@/).filter(Boolean).slice(0, 2).map((part) => part[0]).join('').toUpperCase()
})

const menu = computed(() => {
  if (auth.isManager) return [
    { label: 'Работа с клиентами', items: [
      { to: '/manager', label: 'Клиенты', icon: UsersIcon },
      { to: '/manager/events', label: 'История действий', icon: ClockIcon },
    ] },
  ]
  if (auth.isSeo) return [
    { label: 'Контент', items: [
      { to: '/seo/blog', label: 'Блог', icon: DocumentTextIcon },
      { to: '/seo/pages', label: 'Мета-страницы', icon: RectangleStackIcon },
    ] },
  ]
  return [
    { label: 'Обзор', items: [
      { to: '/dashboard', label: 'Дашборд', icon: ChartBarSquareIcon },
      { to: '/users', label: 'Пользователи', icon: UsersIcon },
      { to: '/ai-limits', label: 'AI-лимиты', icon: BoltIcon },
      { to: '/activity', label: 'Активность', icon: ClockIcon },
    ] },
    { label: 'Управление', items: [
      { to: '/staff', label: 'Сотрудники', icon: UserGroupIcon },
      { to: '/integrations', label: 'Интеграции', icon: CircleStackIcon },
      { to: '/security', label: 'Безопасность', icon: ShieldCheckIcon },
    ] },
    { label: 'Контент', items: [
      { to: '/seo/blog', label: 'Блог', icon: DocumentTextIcon },
      { to: '/seo/pages', label: 'Мета-страницы', icon: AcademicCapIcon },
    ] },
  ]
})

async function logout() {
  await auth.logout()
  router.replace('/login')
}
</script>
