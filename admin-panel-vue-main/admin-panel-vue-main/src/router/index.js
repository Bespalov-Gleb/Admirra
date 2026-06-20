import { createRouter, createWebHistory } from 'vue-router'
import { metrikaHit } from '@/utils/metrika'
import { useAuth } from '../composables/useAuth'
import { DEFAULT_DASHBOARD_PATH } from '../constants/config'

const routes = [
  {
    path: '/',
    name: 'Landing',
    component: () => import('../views/Landing/Landing.vue'),
    meta: { layout: 'landing' }
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
  {
    path: '/verify-email',
    name: 'VerifyEmail',
    component: () => import('../views/Auth/VerifyEmail.vue'),
    meta: { layout: 'auth' }
  },
  {
    path: '/pending-email-verification',
    name: 'PendingEmailVerification',
    component: () => import('../views/Auth/PendingEmailVerification.vue'),
    meta: { layout: 'auth' }
  },
  {
    path: '/auth/login/yandex/callback',
    name: 'OAuthLoginYandexCallback',
    component: () => import('../views/Auth/OAuthLoginCallback.vue'),
    meta: { layout: 'auth', oauthProvider: 'yandex' }
  },
  {
    path: '/auth/login/vk/callback',
    name: 'OAuthLoginVkCallback',
    component: () => import('../views/Auth/OAuthLoginCallback.vue'),
    meta: { layout: 'auth', oauthProvider: 'vk' }
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
    path: '/reset-password/confirm',
    name: 'ResetPasswordConfirm',
    component: () => import('../views/Auth/ResetPassword.vue'),
    meta: { layout: 'auth' }
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
    redirect: '/dashboard/general-3'
  },
  {
    path: '/dashboard/general-2',
    redirect: '/dashboard/general-3'
  },
  {
    path: '/products',
    name: 'Products',
    component: () => import('../views/Product/Products.vue')
  },
  {
    path: '/projects',
    redirect: '/project-card'
  },
  {
    path: '/phone-api',
    name: 'PhoneAPI',
    component: () => import('../views/PhoneAPI/PhoneAPI.vue')
  },
  {
    path: '/phone-integration',
    name: 'PhoneIntegration',
    component: () => import('../views/PhoneAPI/PhoneIntegration.vue')
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
    component: () => import('../views/Mockup/Team.vue'),
    meta: { layout: 'mockup' }
  },
  {
    path: '/history',
    name: 'History',
    component: () => import('../views/Mockup/History.vue'),
    meta: { layout: 'mockup' }
  },
  {
    path: '/tariffs',
    redirect: '/settings?tab=tariff'
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../views/Settings/Settings.vue'),
    meta: { layout: 'mockup' }
  },
  {
    path: '/help',
    name: 'Help',
    component: () => import('../views/Help/Help.vue')
  },
  {
    path: '/contact',
    name: 'Contact',
    component: () => import('../views/Contact/Contact.vue'),
    meta: { layout: 'mockup' }
  },
  {
    path: '/dashboard/general-3',
    name: 'GeneralStats3',
    component: () => import('../views/GeneralStats3/GeneralStats3.vue'),
    meta: { layout: 'mockup' }
  },
  {
    path: '/ai-analysis',
    name: 'AIAnalysis',
    component: () => import('../views/AIAnalysis/AIAnalysis.vue'),
    meta: { layout: 'mockup' }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('../views/Profile/Profile.vue'),
    meta: { layout: 'mockup' }
  },
  {
    path: '/integrations',
    name: 'Integrations',
    component: () => import('../views/Mockup/Integrations.vue'),
    meta: { layout: 'mockup' }
  },
  {
    path: '/integrations/wizard',
    name: 'AddIntegration',
    component: () => import('../views/Mockup/IntegrationWizard.vue'),
    meta: { layout: 'mockup' }
  },
  {
    path: '/projects/create',
    redirect: '/create'
  },
  {
    path: '/preview-banner',
    name: 'PreviewBanner',
    component: () => import('../views/Dashboard/components/CreateProjectBanner.vue'),
    meta: { layout: 'auth' }
  },
  {
    path: '/main',
    name: 'MockupMain',
    component: () => import('../views/Mockup/Main.vue'),
    meta: { layout: 'mockup' }
  },
  {
    path: '/create',
    name: 'MockupCreate',
    component: () => import('../views/Mockup/Create.vue'),
    meta: { layout: 'mockup' }
  },
  {
    path: '/project-rows',
    name: 'MockupProjectRows',
    component: () => import('../views/Mockup/ProjectRows.vue'),
    meta: { layout: 'mockup' }
  },
  {
    path: '/project-card',
    name: 'MockupProjectCard',
    component: () => import('../views/Mockup/ProjectCard.vue'),
    meta: { layout: 'mockup' }
  },
  {
    path: '/ads-channel',
    name: 'MockupAdsChannel',
    component: () => import('../views/Mockup/AdsChannel.vue'),
    meta: { layout: 'mockup' }
  },
  {
    path: '/integration-1',
    name: 'MockupIntegration1',
    component: () => import('../views/Mockup/Integration-1.vue'),
    meta: { layout: 'mockup' }
  },
  {
    path: '/integration-2',
    name: 'MockupIntegration2',
    component: () => import('../views/Mockup/Integration-2.vue'),
    meta: { layout: 'mockup' }
  },
  {
    path: '/integration-3',
    name: 'MockupIntegration3',
    component: () => import('../views/Mockup/Integration-3.vue'),
    meta: { layout: 'mockup' }
  },
  {
    path: '/integration-4',
    name: 'MockupIntegration4',
    component: () => import('../views/Mockup/Integration-4.vue'),
    meta: { layout: 'mockup' }
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

// Проверка аутентификации перед переходом
router.beforeEach(async (to, from, next) => {
  const { checkAuth, isAuthenticated, getToken, markAuthIdle } = useAuth()

  // Normalize path
  const normalizedPath = to.path.replace(/\/$/, '') || '/'
  const isOAuthCallback =
    normalizedPath === '/auth/yandex/callback' ||
    normalizedPath === '/auth/vk/callback' ||
    normalizedPath === '/auth/mytarget/callback' ||
    normalizedPath === '/auth/login/yandex/callback' ||
    normalizedPath === '/auth/login/vk/callback'
  const isLoginPage =
    normalizedPath === '/signin' ||
    normalizedPath === '/signup' ||
    normalizedPath === '/reset-password' ||
    normalizedPath === '/reset-password/confirm' ||
    normalizedPath === '/two-step-verification' ||
    normalizedPath === '/verify-email' ||
    normalizedPath === '/pending-email-verification' ||
    normalizedPath === '/login' ||
    normalizedPath === '/register' ||
    normalizedPath === '/forgot-password' ||
    normalizedPath === '/preview-banner'
  const isLandingPage = normalizedPath === '/'

  // OAuth callbacks должны открываться без токена (обмен code → JWT на странице)
  const isPublicPage = isLoginPage || isLandingPage || isOAuthCallback
  const verifyEmailWithToken = normalizedPath === '/verify-email' && to.query.token
  let isAuth = Boolean(isAuthenticated.value && getToken())

  if (isOAuthCallback) {
    if (!verifyEmailWithToken) markAuthIdle()
  } else if (!isAuth) {
    try {
      isAuth = await Promise.race([
        checkAuth(),
        new Promise((resolve) => setTimeout(() => resolve(false), 8000)),
      ])
    } catch {
      isAuth = false
    }
  }

  console.log(`Router: Navigating to ${to.path} (normalized: ${normalizedPath}), Auth: ${isAuth}`)

  if (isAuth && (isLoginPage || isLandingPage)) {
    next(DEFAULT_DASHBOARD_PATH)
    return
  }

  if (!isAuth && !isPublicPage) {
    console.warn('Router: Unauthorized access attempt, redirecting to login...')
    next('/signin')
  } else if (isAuth) {
    const restrictedForMember = new Set(['/team', '/tariffs'])
    const restrictedForClient = new Set(['/team', '/tariffs', '/integrations', '/integrations/wizard', '/history'])
    const token = getToken()
    if (token && (restrictedForMember.has(normalizedPath) || restrictedForClient.has(normalizedPath))) {
      try {
        const resp = await fetch('/api/team/me-context', {
          headers: { Authorization: `Bearer ${token}` }
        })
        if (resp.ok) {
          const ctx = await resp.json()
          const role = ctx.team_role || ctx.teamRole
          const isOwner = ctx.is_owner ?? ctx.isOwner
          if (!isOwner && role) {
            if ((role === 'client' && restrictedForClient.has(normalizedPath)) || (role === 'member' && restrictedForMember.has(normalizedPath))) {
              return next(DEFAULT_DASHBOARD_PATH)
            }
          }
        }
      } catch {
        // ignore and continue
      }
    }
    next()
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

// SPA: счётчик Метрики засчитывает только первую загрузку сам. На клиентских
// переходах шлём hit вручную (первую навигацию пропускаем — она = первая загрузка).
let _ymFirstNav = true
router.afterEach((to) => {
  if (_ymFirstNav) {
    _ymFirstNav = false
    return
  }
  metrikaHit(window.location.href)
})

export default router
