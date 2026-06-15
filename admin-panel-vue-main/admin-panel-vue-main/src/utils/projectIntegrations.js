const normalizePlatformCode = (value) => {
  const raw = String(value || '').trim().toUpperCase()
  if (!raw) return ''
  if (raw.includes('METRIKA') || raw.includes('МЕТРИК')) return ''
  if (raw.includes('YANDEX') || raw.includes('ЯНДЕКС') || raw.includes('DIRECT') || raw.includes('ДИРЕКТ')) return 'YANDEX'
  if (raw.includes('VK') || raw.includes('ВК')) return 'VK'
  if (raw.includes('AVITO') || raw.includes('АВИТО')) return 'AVITO'
  return raw
}

const normalizeIntegrationItem = (item) => {
  if (!item) return null
  if (typeof item === 'string') return { platform: item, connected: true }
  if (typeof item === 'object') return item
  return null
}

const normalizeIntegrationList = (value) => {
  if (!value) return []
  if (Array.isArray(value)) return value.map(normalizeIntegrationItem).filter(Boolean)
  if (typeof value === 'string') {
    return value
      .split(/[,\s]+/)
      .map(normalizeIntegrationItem)
      .filter(Boolean)
  }
  if (typeof value === 'object') {
    return Object.entries(value).map(([platform, state]) => {
      if (state && typeof state === 'object') return { platform, ...state }
      return { platform, connected: Boolean(state) }
    })
  }
  return []
}

const projectIntegrations = (project) => {
  return [
    ...normalizeIntegrationList(project?.integrations),
    ...normalizeIntegrationList(project?.channels),
    ...normalizeIntegrationList(project?.connected_channels),
    ...normalizeIntegrationList(project?.connectedChannels),
    ...normalizeIntegrationList(project?.platforms),
    ...normalizeIntegrationList(project?.ad_platforms),
  ]
}

export const projectPlatforms = (project) => {
  const platforms = [
    ...projectIntegrations(project)
      .map((integration) => normalizePlatformCode(integration.platform || integration.type || integration.name || integration.provider || integration.channel)),
    normalizePlatformCode(project?.platform),
    normalizePlatformCode(project?.provider),
    normalizePlatformCode(project?.channel),
  ]
    .filter(Boolean)
  return Array.from(new Set(platforms))
}

export const hasProjectPlatform = (project, platform) => {
  return projectPlatforms(project).includes(normalizePlatformCode(platform))
}

export const isIntegrationActive = (integration) => {
  const boolKeys = ['is_active', 'active', 'enabled', 'connected']
  const boolValues = boolKeys
    .filter((key) => typeof integration?.[key] === 'boolean')
    .map((key) => integration[key])

  if (boolValues.includes(true)) return true

  const status = String(integration?.status || integration?.state || '').trim().toLowerCase()
  if (status) {
    if (/(active|connected|enabled|success|ok|актив|подключ)/.test(status)) return true
    if (/(inactive|disabled|disconnect|failed|error|неактив|отключ|ошиб)/.test(status)) return false
  }

  if (boolValues.includes(false)) return false
  return true
}

export const hasActiveProjectIntegration = (project) => {
  const projectActive = ['is_active', 'active', 'enabled']
    .some((key) => project?.[key] === true)
  if (projectActive) return true
  return projectIntegrations(project).some(isIntegrationActive)
}
