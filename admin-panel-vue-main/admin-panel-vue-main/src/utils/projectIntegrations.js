const normalizePlatformCode = (value) => {
  const raw = String(value || '').trim().toUpperCase()
  if (!raw) return ''
  if (raw.includes('YANDEX') || raw.includes('ЯНДЕКС') || raw.includes('DIRECT') || raw.includes('ДИРЕКТ')) return 'YANDEX'
  if (raw.includes('VK') || raw.includes('ВК')) return 'VK'
  return raw
}

const projectIntegrations = (project) => {
  return Array.isArray(project?.integrations) ? project.integrations : []
}

export const projectPlatforms = (project) => {
  const platforms = projectIntegrations(project)
    .map((integration) => normalizePlatformCode(integration.platform || integration.type || integration.name || integration.provider))
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
