// Request-local batches only: never retain statistics across dates or accounts.
export async function loadProjectSummaries(api, projectIds, params, isCurrent = () => true) {
  const ids = [...new Set(projectIds)]
  const result = {}
  for (let offset = 0; offset < ids.length; offset += 64) {
    if (!isCurrent()) return null
    const page = ids.slice(offset, offset + 64)
    const { data } = await api.get('dashboard/project-summaries', {
      params: { ...params, client_ids: page },
    })
    if (!isCurrent()) return null
    for (const id of page) {
      if (!data?.[id] || ['all', 'yandex', 'vk', 'avito'].some(channel => !data[id][channel])) {
        throw new Error('Incomplete project summary batch')
      }
      result[id] = data[id]
    }
  }
  return result
}
