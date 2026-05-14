const DAY_MS = 24 * 60 * 60 * 1000

const toDateParam = (date) => {
  const local = new Date(date)
  local.setMinutes(local.getMinutes() - local.getTimezoneOffset())
  return local.toISOString().slice(0, 10)
}

const startOfWeek = (date) => {
  const copy = new Date(date)
  copy.setHours(0, 0, 0, 0)
  const day = copy.getDay() || 7
  copy.setDate(copy.getDate() - day + 1)
  return copy
}

export const projectPeriodOptions = [
  { type: 'label', label: 'Указать период' },
  { value: 'today', label: 'Сегодня' },
  { value: 'yesterday', label: 'Вчера' },
  { value: 'last_week', label: 'Прошлая неделя' },
  { value: 'last_month', label: 'Прошлый месяц' },
  { type: 'divider' },
  { value: 'this_week', label: 'Эта неделя' },
  { value: 'this_month', label: 'Этот месяц' },
  { value: 'last_7_days', label: 'Последние 7 дней' },
  { value: 'last_30_days', label: 'Последние 30 дней' },
  { value: 'last_90_days', label: 'Последние 90 дней' },
  { value: 'last_365_days', label: 'Последние 365 дней' }
]

export const selectableProjectPeriodOptions = projectPeriodOptions.filter((option) => option.value)

export const getProjectPeriodLabel = (value) => {
  if (value === 'custom') return 'Указать период'
  return selectableProjectPeriodOptions.find((option) => option.value === value)?.label || 'Последние 7 дней'
}

export const getProjectPeriodRange = (value, customRange = null) => {
  if (value === 'custom' && customRange?.start && customRange?.end) {
    return { startDate: customRange.start, endDate: customRange.end }
  }

  const today = new Date()
  today.setHours(0, 0, 0, 0)

  if (value === 'today') {
    return { startDate: toDateParam(today), endDate: toDateParam(today) }
  }

  if (value === 'yesterday') {
    const yesterday = new Date(today.getTime() - DAY_MS)
    return { startDate: toDateParam(yesterday), endDate: toDateParam(yesterday) }
  }

  if (value === 'last_week') {
    const thisWeekStart = startOfWeek(today)
    const end = new Date(thisWeekStart.getTime() - DAY_MS)
    const start = new Date(end.getTime() - 6 * DAY_MS)
    return { startDate: toDateParam(start), endDate: toDateParam(end) }
  }

  if (value === 'last_month') {
    const start = new Date(today.getFullYear(), today.getMonth() - 1, 1)
    const end = new Date(today.getFullYear(), today.getMonth(), 0)
    return { startDate: toDateParam(start), endDate: toDateParam(end) }
  }

  if (value === 'this_week') {
    return { startDate: toDateParam(startOfWeek(today)), endDate: toDateParam(today) }
  }

  if (value === 'this_month') {
    const start = new Date(today.getFullYear(), today.getMonth(), 1)
    return { startDate: toDateParam(start), endDate: toDateParam(today) }
  }

  const daysMap = {
    last_7_days: 7,
    last_30_days: 30,
    last_90_days: 90,
    last_365_days: 365
  }
  const days = daysMap[value] || 7
  const start = new Date(today.getTime() - (days - 1) * DAY_MS)
  return { startDate: toDateParam(start), endDate: toDateParam(today) }
}
