export const PLATFORMS = {
  YANDEX_DIRECT: {
    label: 'Яндекс.Директ',
    initials: 'ЯD',
    className: 'bg-red-500 text-white border-red-600',
    tokenLink: 'https://oauth.yandex.ru/authorize?response_type=token&client_id=e2a052c8cac54caeb9b1b05a593be932',
    isDynamic: false
  },
  VK_ADS: {
    label: 'VK Ads',
    initials: 'VK',
    description: 'Для автоматической работы нажмите кнопку ниже. Вы будете перенаправлены на страницу авторизации VK Ads.',
    className: 'bg-blue-600 text-white border-blue-700',
    tokenLink: 'https://ads.vk.com/hq/settings',
    isDynamic: false
  },
  YANDEX_METRIKA: {
    label: 'Яндекс.Метрика',
    initials: 'YM',
    className: 'bg-yellow-400 text-black border-yellow-500',
    tokenLink: 'https://oauth.yandex.ru/authorize?response_type=token&client_id=e2a052c8cac54caeb9b1b05a593be932',
    isDynamic: false,
    accountIdLabel: 'ID Счетчика',
    accountIdPlaceholder: 'Напр: 98765432'
  }
}

export const getPlatformProperty = (platform, prop, defaultValue = '') => {
  return PLATFORMS[platform]?.[prop] || defaultValue
}
