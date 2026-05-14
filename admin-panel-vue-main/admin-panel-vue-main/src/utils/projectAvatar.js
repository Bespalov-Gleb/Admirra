export function projectAvatarUrl(project) {
  const url = project?.avatar_url || project?.avatarUrl || ''
  if (!url) return ''
  if (/^(https?:)?\/\//.test(url) || url.startsWith('data:') || url.startsWith('blob:')) return url
  return url.startsWith('/') ? url : `/${url}`
}

export function projectInitials(project) {
  const name = String(project?.name || '').trim()
  if (!name) return 'PR'
  const parts = name.split(/\s+/).filter(Boolean)
  const letters = parts.length > 1
    ? `${parts[0][0] || ''}${parts[1][0] || ''}`
    : name.slice(0, 2)
  return letters.toUpperCase()
}
