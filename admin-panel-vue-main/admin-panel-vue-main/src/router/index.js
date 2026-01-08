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
    component: () => import('../views/Auth/Login.vue'),
    meta: { layout: 'auth' }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/Auth/Register.vue'),
    meta: { layout: 'auth' }
  },
  {
    path: '/auth/yandex/callback',
    name: 'YandexCallback',
    component: () => import('../views/Auth/YandexCallback.vue'),
    meta: { layout: 'auth' }
  },
  {
    path: '/auth/vk/callback',
    name: 'VKCallback',
    component: () => import('../views/Auth/VKCallback.vue'),
    meta: { layout: 'auth' }
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
    path: '/dashboard/general-3',
    name: 'GeneralStats3',
    component: () => import('../views/GeneralStats3/GeneralStats3.vue')
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('../views/Profile/Profile.vue')
  },
  {
    path: '/projects/create',
    name: 'CreateProject',
    component: () => import('../views/Project/CreateProjectPage.vue')
  },
  {
    path: '/preview-banner',
    name: 'PreviewBanner',
    component: () => import('../views/Dashboard/components/CreateProjectBanner.vue'),
    meta: { layout: 'auth' } // Using auth layout for a clean centered look
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

// Проверка аутентификации перед переходом
router.beforeEach(async (to, from, next) => {
  const { checkAuth } = useAuth()
  const isAuth = await checkAuth()
  
  // Normalize path
  const normalizedPath = to.path.replace(/\/$/, '') || '/'
  const isLoginPage = normalizedPath === '/login' || normalizedPath === '/' || normalizedPath === '/register' || normalizedPath === '/preview-banner'

  console.log(`Router: Navigating to ${to.path} (normalized: ${normalizedPath}), Auth: ${isAuth}`)

  // Если пользователь не авторизован и пытается зайти не на страницу логина
  if (!isAuth && !isLoginPage) {
    console.warn('Router: Unauthorized access attempt, redirecting to login...')
    next('/login')
  }
  // Если пользователь авторизован и пытается зайти на страницу логина
  else if (isAuth && isLoginPage) {
    console.log('Router: Already authenticated, redirecting to dashboard...')
    next({ name: 'GeneralStats3' })
  }
  // Иначе разрешаем переход
  else {
    next()
  }
})

// Обработка ошибок при загрузке компонентов (например, ChunkLoadError)
router.onError((error, to) => {
  if (error.message.includes('Failed to fetch dynamically imported module') || error.message.includes('chunk')) {
    console.error('Critical: Chunk load error detected for path:', to.path, error)
    console.warn('Attempting page refresh to recover from chunk error...')
    window.location.reload()
  } else {
    console.error('Router error:', error)
  }
})

export default router

