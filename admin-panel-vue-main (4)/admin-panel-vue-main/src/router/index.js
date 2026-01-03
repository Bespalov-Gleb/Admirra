import { createRouter, createWebHistory } from 'vue-router'
import { useAuth } from '../composables/useAuth'

const routes = [
  {
    path: '/',
    redirect: '/login'
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Auth/Login.vue')
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/Auth/Register.vue')
  },
  {
    path: '/forgot-password',
    name: 'ForgotPassword',
    component: () => import('../views/Auth/ForgotPassword.vue')
  },
  {
    path: '/reset-password',
    name: 'ResetPassword',
    component: () => import('../views/Auth/ResetPassword.vue')
  },
  {
    path: '/dashboard/general',
    name: 'GeneralStats',
    component: () => import('../views/GeneralStats/GeneralStats.vue')
  },
  {
    path: '/dashboard/general-2',
    name: 'GeneralStats2',
    component: () => import('../views/GeneralStats2/GeneralStats2.vue')
  },
  {
    path: '/dashboard/general-3',
    name: 'GeneralStats3',
    component: () => import('../views/GeneralStats3/GeneralStats3.vue')
  },
  {
    path: '/products',
    name: 'Products',
    component: () => import('../views/Product/Products.vue')
  },
  {
    path: '/projects',
    name: 'Projects',
    component: () => import('../views/Project/Projects.vue')
  },
  {
    path: '/channels',
    name: 'Channels',
    component: () => import('../views/Channels/Channels.vue')
  },
  {
    path: '/team',
    name: 'Team',
    component: () => import('../views/Team/Team.vue')
  },
  {
    path: '/history',
    name: 'History',
    component: () => import('../views/History/History.vue')
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../views/Settings/Settings.vue')
  },
  {
    path: '/help',
    name: 'Help',
    component: () => import('../views/Help/Help.vue')
  },
  {
    path: '/contact',
    name: 'Contact',
    component: () => import('../views/Contact/Contact.vue')
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('../views/Profile/Profile.vue')
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

// Проверка аутентификации перед переходом
router.beforeEach((to, from, next) => {
  // Проверяем токен напрямую из localStorage
  const token = localStorage.getItem('auth_token')
  const isAuth = !!token
  const isAuthPage = to.path === '/login' || to.path === '/' || to.path === '/register' || to.path === '/forgot-password' || to.path === '/reset-password'

  // Если пользователь не авторизован и пытается зайти не на страницу авторизации
  if (!isAuth && !isAuthPage) {
    next('/login')
  }
  // Если пользователь авторизован и пытается зайти на страницу логина, регистрации или восстановления пароля
  else if (isAuth && (to.path === '/login' || to.path === '/' || to.path === '/register')) {
    next('/dashboard/general')
  }
  // Иначе разрешаем переход
  else {
    next()
  }
})

export default router

