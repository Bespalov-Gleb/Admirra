// Axios preserves responseType=blob for JSON error responses too.
export async function reportExportError(error, fallback) {
  let data = error?.response?.data
  if (typeof Blob !== 'undefined' && data instanceof Blob) {
    if (data.size > 16384) return fallback
    try { data = JSON.parse(await data.text()) } catch { return fallback }
  }
  return typeof data?.detail === 'string' && data.detail.length <= 2000 ? data.detail : fallback
}
