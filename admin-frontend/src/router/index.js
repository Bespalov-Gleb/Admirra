import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  { path: '/login', name: 'login', component: () => import('../views/LoginView.vue'), meta: { public: true, title: 'Вход' } },
  { path: '/invite/:token', name: 'invite', component: () => import('../views/InviteView.vue'), meta: { public: true, title: 'Активация' } },
  {
    path: '/',
    component: () => import('../layouts/AdminLayout.vue'),
    children: [
      { path: '', redirect: '/dashboard' },
      { path: 'dashboard', component: () => import('../views/DashboardView.vue'), meta: { roles: ['SUPERADMIN', 'ADMIN'], title: 'Дашборд' } },
      { path: 'users', component: () => import('../views/UsersView.vue'), meta: { roles: ['SUPERADMIN', 'ADMIN'], title: 'Пользователи' } },
      { path: 'users/:id', component: () => import('../views/UserDetailView.vue'), meta: { roles: ['SUPERADMIN', 'ADMIN'], title: 'Карточка пользователя' } },
      { path: 'ai-limits', component: () => import('../views/AiLimitsView.vue'), meta: { roles: ['SUPERADMIN', 'ADMIN'], title: 'AI-лимиты' } },
      { path: 'staff', component: () => import('../views/StaffView.vue'), meta: { roles: ['SUPERADMIN', 'ADMIN'], title: 'Сотрудники' } },
      { path: 'activity', component: () => import('../views/ActivityView.vue'), meta: { roles: ['SUPERADMIN', 'ADMIN'], title: 'Активность' } },
      { path: 'integrations', component: () => import('../views/IntegrationsView.vue'), meta: { roles: ['SUPERADMIN', 'ADMIN'], title: 'Интеграции' } },
      { path: 'promo-codes', component: () => import('../views/PromoView.vue'), meta: { roles: ['SUPERADMIN', 'ADMIN'], title: 'Промокоды' } },
      { path: 'security', component: () => import('../views/SecurityView.vue'), meta: { roles: ['SUPERADMIN', 'ADMIN'], title: 'Безопасность и настройки' } },
      { path: 'manager', component: () => import('../views/ManagerView.vue'), meta: { roles: ['STAFF_MANAGER', 'SUPPORT'], title: 'Клиенты' } },
      { path: 'manager/users/:id', component: () => import('../views/UserDetailView.vue'), meta: { roles: ['STAFF_MANAGER', 'SUPPORT'], manager: true, title: 'Карточка клиента' } },
      { path: 'manager/events', component: () => import('../views/ManagerEventsView.vue'), meta: { roles: ['STAFF_MANAGER', 'SUPPORT'], title: 'История действий' } },
      { path: 'seo/blog', component: () => import('../views/SeoBlogView.vue'), meta: { roles: ['SEO', 'SUPERADMIN', 'ADMIN'], title: 'Блог' } },
      { path: 'seo/blog/:id', component: () => import('../views/SeoEditorView.vue'), meta: { roles: ['SEO', 'SUPERADMIN', 'ADMIN'], title: 'Редактор статьи' } },
      { path: 'seo/pages', component: () => import('../views/SeoPagesView.vue'), meta: { roles: ['SEO', 'SUPERADMIN', 'ADMIN'], title: 'Мета-страницы' } },
      { path: 'profile', component: () => import('../views/ProfileView.vue'), meta: { title: 'Профиль и 2FA' } },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.initialized) await auth.fetchMe()

  if (to.meta.public) {
    if (to.name === 'login' && auth.isAuthenticated) return auth.homeRoute
    return true
  }

  if (!auth.isAuthenticated) return { name: 'login', query: { next: to.fullPath } }

  const allowed = to.meta.roles
  if (allowed && !allowed.includes(auth.role)) return auth.homeRoute

  document.title = `${to.meta.title || 'Панель'} · AdMirra`
  return true
})

export default router
