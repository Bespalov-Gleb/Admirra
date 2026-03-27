/**
 * Публичный домен из сборки (VITE_*). prod → admirra.ru, dev → admirra.online.
 * Опционально: VITE_ADMIRRA_PUBLIC_HOST — явный хост без схемы.
 */
const deploy = (import.meta.env.VITE_ADMIRRA_DEPLOY_ENV || 'prod').toString().toLowerCase()

const host =
  import.meta.env.VITE_ADMIRRA_PUBLIC_HOST ||
  (deploy === 'dev' ? 'admirra.online' : 'admirra.ru')

export const ADMIRRA_PUBLIC_HOST = host
export const ADMIRRA_PUBLIC_ORIGIN = `https://${host}`
