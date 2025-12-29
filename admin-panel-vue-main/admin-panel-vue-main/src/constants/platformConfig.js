export const PLATFORMS = {
  YANDEX_DIRECT: {
    label: 'Яндекс.Директ',
    initials: 'ЯD',
    className: 'bg-red-500 text-white border-red-600',
    tokenLink: 'https://oauth.yandex.ru/authorize?response_type=token&client_id=3febb68881204d9380089f718e5251b1',
    isDynamic: false
  },
  VK_ADS: {
    label: 'VK Ads',
    initials: 'VK',
    description: 'Для подключения перейдите в <b>Настройки -> Доступ</b> и создайте API ключ (Client ID и Client Secret).',
    className: 'bg-blue-600 text-white border-blue-700',
    tokenLink: 'https://ads.vk.com/hq/settings',
    isDynamic: true,
    dynamicFields: [
      {
        key: 'client_id',
        label: 'Client ID',
        placeholder: 'Введите Client ID из настроек VK',
        type: 'text',
        required: true,
        helpLink: 'https://ads.vk.com/hq/settings'
      },
      {
        key: 'client_secret',
        label: 'Client Secret',
        placeholder: '••••••••••••••••••••',
        type: 'password',
        required: true
      }
    ],
    accountIdLabel: 'ID Кабинета/Аккаунта',
    accountIdPlaceholder: 'Напр: 1234567'
  },
  YANDEX_METRIKA: {
    label: 'Яндекс.Метрика',
    initials: 'YM',
    className: 'bg-yellow-400 text-black border-yellow-500',
    tokenLink: 'https://oauth.yandex.ru/authorize?response_type=token&client_id=3febb68881204d9380089f718e5251b1',
    isDynamic: false,
    accountIdLabel: 'ID Счетчика',
    accountIdPlaceholder: 'Напр: 98765432'
  }
}

export const getPlatformProperty = (platform, prop, defaultValue = '') => {
  return PLATFORMS[platform]?.[prop] || defaultValue
}
