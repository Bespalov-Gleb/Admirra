export const dashboardMockData = {
  reportTemplateOptions: ['Шаблон: Яндекс', 'Шаблон: VK Ads'],
  scheduleOptions: ['Ежедневно в 10:00', 'Каждый ПН в 10:00', 'Каждую ПТ в 18:00'],
  chartPeriodOptions: ['Неделя', 'Месяц', 'Квартал', 'Год'],
  campaigns: [
    '[ВД] РСЯ | Вездеходы | 18.12.25 / правки офис',
    '[ВД] Поиск | Вездеходы | Брендовые запросы',
    '[ВД] VK | Вездеходы | Ретаргетинг'
  ],
  metrics: [
    { key: 'expenses', title: 'Расходы', subtitle: 'За период', value: '90,190.55 ₽', icon: 'wallet', trend: 15.6, delta: '+1.4k за эту неделю' },
    { key: 'impressions', title: 'Показы', subtitle: 'По всем каналам', value: '120,302', icon: 'chart', trend: 15.6, delta: '+1.4k за эту неделю' },
    { key: 'clicks', title: 'Клики', subtitle: 'Все переходы', value: '967', icon: 'cursor', trend: 15.6, delta: '+1.4k за эту неделю' },
    { key: 'cpc', title: 'CPC', subtitle: 'Стоимость клика', value: '9,63 ₽', icon: 'play', trend: 15.6, delta: '+1.4k за эту неделю' },
    { key: 'leads', title: 'Лиды', subtitle: 'По всем каналам', value: '130 шт.', icon: 'calendar', trend: 15.6, delta: '+1.4k за эту неделю' },
    { key: 'cpa', title: 'CPA', subtitle: 'Стоимость лида', value: '963 ₽', icon: 'badge', trend: 15.6, delta: '+1.4k за эту неделю' }
  ],
  chart: {
    labels: ['01 Feb', '02 Feb', '03 Feb', '04 Feb', '05 Feb', '06 Feb', '07 Feb', '08 Feb', '09 Feb', '10 Feb', '11 Feb', '12 Feb', '13 Feb', '14 Feb'],
    previewPoints: [
      { x: 56, y: 224 },
      { x: 116, y: 198 },
      { x: 176, y: 175 },
      { x: 236, y: 167 },
      { x: 296, y: 139 },
      { x: 356, y: 86 },
      { x: 416, y: 35 },
      { x: 476, y: 78 },
      { x: 536, y: 82 },
      { x: 596, y: 68 },
      { x: 656, y: 56 },
      { x: 716, y: 62 },
      { x: 776, y: 78 },
      { x: 846, y: 45 }
    ]
  },
  goals: [
    { name: 'Заявки с сайта', value: '40 шт. (51.7%)', color: '#3f63f6' },
    { name: 'Телефонный звонок', value: '20 шт. (28.6%)', color: '#f39a72' },
    { name: 'Форма обратной связи', value: '10 шт. (14.3%)', color: '#dff9e7' }
  ],
  campaignRows: [
    { name: '[ВД] РСЯ | Вездеходы | 18.12.25 / правки о...', tint: 'green', cost: '90,190.55 ₽', impressions: '120,302', clicks: '967', cpc: '9,63 ₽', leads: '130 шт.', cpa: '963 ₽', trendCost: '+15.6%', trendImpressions: '+15.6%', trendClicks: '+15.6%', trendCpc: '+15.6%', trendLeads: '+15.6%', trendCpa: '+15.6%' },
    { name: '[ВД] РСЯ | Вездеходы | 18.12.25 / правки о...', tint: 'green', cost: '90,190.55 ₽', impressions: '120,302', clicks: '967', cpc: '9,63 ₽', leads: '130 шт.', cpa: '963 ₽', trendCost: '+15.6%', trendImpressions: '+15.6%', trendClicks: '+15.6%', trendCpc: '+15.6%', trendLeads: '+15.6%', trendCpa: '+15.6%' },
    { name: '[ВД] РСЯ | Вездеходы | 18.12.25 / правки о...', tint: 'blue', cost: '90,190.55 ₽', impressions: '120,302', clicks: '967', cpc: '9,63 ₽', leads: '130 шт.', cpa: '963 ₽', trendCost: '+15.6%', trendImpressions: '+15.6%', trendClicks: '+15.6%', trendCpc: '+15.6%', trendLeads: '+15.6%', trendCpa: '+15.6%' }
  ],
  creatives: [
    { badge: 'Специальные предложения', title: 'СКИДКИ ДО 4 000 000 РУБЛЕЙ', class: 'city' },
    { badge: 'ЖК Академический', title: 'РАССРОЧКА КОМУ ЭТО ВЫГОДНО?', class: 'blue' },
    { badge: 'Предложения декабря', title: 'СКИДКИ ДО 670 000 РУБЛЕЙ', class: 'house' }
  ],
  aiComments: [
    'Расходы снизились на 15,34% по сравнению с прошлой неделей, при этом количество показов увеличилось на 58,85%, что говорит об улучшении эффективности закупки трафика.',
    'Количество кликов увеличилось на 67,53%, что положительно сказалось на объеме лидов - рост на 30,31%.',
    'Стоимость клика (CPC) снизилась на 10,14%, а стоимость лида (CPA) осталась почти на том же уровне, что является хорошим признаком.',
    'Рекомендуем масштабировать кампании в РСЯ, так как они показали лучшую эффективность по доле лидов.'
  ],
  deviceStats: [
    { name: 'Мобильные', value: '68.3%', width: '71%', icon: 'mobile' },
    { name: 'Десктоп', value: '68.3%', width: '35%', icon: 'desktop' },
    { name: 'Планшеты', value: '68.3%', width: '15%', icon: 'desktop' }
  ],
  placements: [
    { name: 'Поиск', value: '68.3%', width: '71%' },
    { name: 'РСЯ', value: '68.3%', width: '35%' }
  ]
}
