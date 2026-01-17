export const PLATFORMS = {
  YANDEX_DIRECT: {
    label: 'Яндекс.Директ',
    description: 'Рекламная сеть Яндекса, поиск и ретаргетинг.',
    initials: 'ЯD',
    className: 'bg-red-500 text-white border-red-600',
    iconColor: 'text-red-500',
    tokenLink: 'https://oauth.yandex.ru/authorize?response_type=token&client_id=e2a052c8cac54caeb9b1b05a593be932',
    isDynamic: false
  },
  VK_ADS: {
    label: 'VK Реклама',
    description: 'Таргетированная реклама в соцсетях и проектах VK.',
    initials: 'VK',
    className: 'bg-blue-600 text-white border-blue-700',
    iconColor: 'text-blue-500',
    tokenLink: 'https://ads.vk.com/hq/settings',
    isDynamic: false
  },
  GOOGLE_ADS: {
    label: 'Google Ads',
    description: 'Контекстная реклама в поиске и на сайтах партнеров.',
    initials: 'G',
    className: 'bg-gray-100 text-gray-400 border-gray-200 grayscale',
    iconColor: 'text-gray-300',
    comingSoon: true
  }
}

export const getPlatformProperty = (platform, prop, defaultValue = '') => {
  return PLATFORMS[platform]?.[prop] || defaultValue
}
