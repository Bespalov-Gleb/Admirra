import { createRouter, createWebHistory } from 'vue-router'
import { useAuth } from '../composables/useAuth'

const routes = [
  {
    path: '/',
    redirect: '/signin'
  },
  {
    path: '/signin',
    name: 'SignIn',
    component: () => import('../views/Auth/SignIn.vue'),
    meta: { layout: 'auth' }
  },
  {
    path: '/signup',
    name: 'SignUp',
    component: () => import('../views/Auth/SignUp.vue'),
    meta: { layout: 'auth' }
  },
  {
    path: '/reset-password',
    name: 'ResetPassword',
    component: () => import('../views/Auth/ResetPassword.vue'),
    meta: { layout: 'auth' }
  },
  {
    path: '/two-step-verification',
    name: 'TwoStepVerification',
    component: () => import('../views/Auth/TwoStepVerification.vue'),
    meta: { layout: 'auth' }
  },
  // Старые пути для обратной совместимости
  {
    path: '/login',
    redirect: '/signin'
  },
  {
    path: '/register',
    redirect: '/signup'
  },
  {
    path: '/forgot-password',
    redirect: '/reset-password'
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
    path: '/auth/mytarget/callback',
    name: 'MyTargetCallback',
    component: () => import('../views/Auth/MyTargetCallback.vue'),
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
    path: '/phone-api',
    name: 'PhoneAPI',
    component: () => import('../views/PhoneAPI/PhoneAPI.vue')
  },
  {
    path: '/phone-projects',
    name: 'PhoneProjects',
    component: () => import('../views/PhoneProjects/PhoneProjects.vue')
  },
  {
    path: '/phone-leads',
    name: 'PhoneLeads',
    component: () => import('../views/PhoneLeads/PhoneLeads.vue')
  },
  {
    path: '/phone-stats',
    name: 'PhoneStats',
    component: () => import('../views/PhoneStats/PhoneStats.vue')
  },
  {
    path: '/phone-reports',
    name: 'PhoneReports',
    component: () => import('../views/PhoneReports/PhoneReports.vue')
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
    path: '/integrations/wizard',
    name: 'AddIntegration',
    component: () => import('../views/Integrations/AddIntegrationPage.vue')
    // Using MainLayout (with sidebar) to match screen 2
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
  const isLoginPage = normalizedPath === '/signin' || normalizedPath === '/signup' || normalizedPath === '/reset-password' || normalizedPath === '/two-step-verification' || normalizedPath === '/login' || normalizedPath === '/' || normalizedPath === '/register' || normalizedPath === '/forgot-password' || normalizedPath === '/preview-banner'

  console.log(`Router: Navigating to ${to.path} (normalized: ${normalizedPath}), Auth: ${isAuth}`)

  // Если пользователь не авторизован и пытается зайти не на страницу логина
  if (!isAuth && !isLoginPage) {
    console.warn('Router: Unauthorized access attempt, redirecting to login...')
    next('/signin')
  }
  // Если пользователь авторизован и пытается зайти на страницу логина
  else if (isAuth && isLoginPage) {
    console.log('Router: Already authenticated, redirecting to dashboard...')
    next({ name: 'CreateProject' })
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

