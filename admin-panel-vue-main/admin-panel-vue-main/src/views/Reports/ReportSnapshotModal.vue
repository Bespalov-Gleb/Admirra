<template>
  <Teleport to="body">
    <div class="snapshot-backdrop" @click.self="$emit('close')">
      <section class="snapshot-modal" :class="{ 'is-dark': isDarkMode }">
        <header>
          <div>
            <p>Отправленный отчёт · снимок</p>
            <h3>{{ delivery?.scope_label || 'Отчёт' }}</h3>
            <span>{{ formatDate(delivery?.start_date) }} — {{ formatDate(delivery?.end_date) }}</span>
          </div>
          <button type="button" aria-label="Закрыть" @click="$emit('close')">×</button>
        </header>

        <div v-if="delivery?.status === 'cancelled'" class="snapshot-cancelled">Отчёт отменён: клиенту ничего не отправлялось.</div>

        <div class="snapshot-meta">
          <span>Утвердил: <b>{{ delivery?.approved_by_name || 'авто' }}</b></span>
          <span>Отправлен: <b>{{ formatDateTime(delivery?.sent_at || delivery?.approved_at || delivery?.created_at) }}</b></span>
          <span>Шаблон: <b>{{ templateLabel(delivery?.platform) }}</b></span>
        </div>

        <div v-if="badges.length" class="snapshot-badges">
          <button v-for="badge in badges" :key="badge.key" type="button" :class="{ failed: badge.ok === false }" :disabled="badge.ok !== false || retrying" @click.stop="retry(badge)">
            {{ badge.label }} {{ badge.ok === true ? '✓' : badge.ok === false ? '✕ ⟳' : '—' }}
          </button>
        </div>

        <div class="snapshot-body">
          <span v-if="loading">Загружаем неизменяемый снимок…</span>
          <button v-else-if="imageUrl" type="button" class="snapshot-preview-btn" title="Открыть на весь экран" @click="previewFullscreen = true">
            <img :src="imageUrl" alt="Зафиксированный отчёт" />
            <span class="snapshot-preview-zoom" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/></svg>
              На весь экран
            </span>
          </button>
          <span v-else>Снимок PNG недоступен. PDF всё равно можно скачать.</span>
        </div>

        <footer>
          <button type="button" @click="$emit('close')">Закрыть</button>
          <button type="button" class="primary" :disabled="downloading" @click="downloadPng">{{ downloading ? 'Готовим…' : 'Скачать PNG' }}</button>
          <button type="button" class="primary" :disabled="downloading" @click="downloadPdf">Скачать PDF</button>
        </footer>
      </section>

    </div>

    <!-- Полноэкранное превью снимка отчёта с зумом. -->
    <FullscreenImageViewer
      v-if="previewFullscreen && imageUrl"
      :src="imageUrl"
      @close="previewFullscreen = false"
    />
  </Teleport>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import api from '@/api/axios'
import { useToaster } from '@/composables/useToaster'
import { useTheme } from '@/composables/useTheme'
import FullscreenImageViewer from '@/components/ui/FullscreenImageViewer.vue'

const props = defineProps({ delivery: { type: Object, default: null } })
const emit = defineEmits(['close', 'retry'])
const { isDarkMode } = useTheme()
const toaster = useToaster()
const imageUrl = ref('')
const loading = ref(false)
const downloading = ref(false)
const retrying = ref(false)
const previewFullscreen = ref(false)

const releaseImage = () => {
  if (imageUrl.value) URL.revokeObjectURL(imageUrl.value)
  imageUrl.value = ''
}

const download = async (extension, save = false) => {
  if (!props.delivery?.id) return
  downloading.value = save
  try {
    const { data } = await api.get(`reports/deliveries/${props.delivery.id}/snapshot.${extension}`, { responseType: 'blob' })
    if (save) {
      const href = URL.createObjectURL(data)
      const link = document.createElement('a')
      link.href = href
      link.download = `report_${props.delivery.start_date}_${props.delivery.end_date}.${extension}`
      link.click()
      URL.revokeObjectURL(href)
    } else imageUrl.value = URL.createObjectURL(data)
  } catch (err) {
    if (save) toaster.error(err.response?.data?.detail || 'Не удалось скачать снимок')
  } finally {
    downloading.value = false
  }
}

const load = async () => {
  releaseImage()
  if (!props.delivery?.id) return
  loading.value = true
  await download('png')
  loading.value = false
}

watch(() => props.delivery, load, { immediate: true })
onBeforeUnmount(releaseImage)

const badges = computed(() => {
  const delivery = props.delivery || {}
  if (delivery.status === 'cancelled') return []
  const results = delivery.delivery_results || {}
  const out = []
  for (const channel of delivery.channels || []) {
    if (channel === 'email') {
      const targets = results.email_targets || {}
      const emails = delivery.email_recipients || []
      for (const email of emails) {
        const row = targets[email] || {}
        out.push({ key: `email-${email}`, label: `Email · ${email}`, ok: row.ok, email })
      }
    } else {
      out.push({ key: channel, label: channel === 'telegram' ? 'Telegram · мне' : 'MAX · мне', retryChannel: channel, ok: results[channel] })
    }
  }
  for (const target of delivery.chat_target_details || []) {
    if (target.kind === 'email') continue
    const row = (results.targets || {})[target.id] || {}
    out.push({ key: `target-${target.id}`, label: target.title || (target.kind === 'max' ? 'MAX' : 'Telegram'), retryTargetId: String(target.id), ok: row.ok })
  }
  return out
})

const retry = async (badge) => {
  if (!props.delivery?.id || badge.ok !== false) return
  retrying.value = true
  try {
    const { data } = await api.post(`reports/deliveries/${props.delivery.id}/approve`, {
      ...(badge.email ? { retry_email: badge.email } : {}),
      ...(badge.retryChannel ? { retry_channel: badge.retryChannel } : {}),
      ...(badge.retryTargetId ? { retry_chat_target_id: badge.retryTargetId } : {}),
    })
    emit('retry', data)
    toaster.success('Неуспешный маршрут отправлен повторно')
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Не удалось повторить отправку')
  } finally {
    retrying.value = false
  }
}

const downloadPng = () => download('png', true)
const downloadPdf = () => download('pdf', true)
const formatDate = (value) => value ? new Date(value).toLocaleDateString('ru-RU') : '—'
const formatDateTime = (value) => {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}
const templateLabel = (value) => ({ all: 'Сводный', yandex: 'Яндекс Директ', vk: 'VK Реклама', avito: 'Avito Ads' }[value] || 'Сводный')
</script>

<style scoped>
.snapshot-backdrop { position: fixed; inset: 0; z-index: 1300; display: grid; place-items: center; padding: 1rem; background: rgba(15,23,42,.5); }
.snapshot-modal { width: min(65rem, 96vw); max-height: 93vh; overflow: auto; padding: 1.35rem; border-radius: 1.1rem; background: #fff; box-shadow: 0 2rem 5rem rgba(0,0,0,.36); }
.snapshot-modal.is-dark { background: #252838; color: #f8fafc; }
.snapshot-modal header { display:flex; justify-content:space-between; gap:1rem; align-items:flex-start; }
.snapshot-modal header p { margin:0 0 .25rem; color:#2563eb; font-size:.78rem; font-weight:800; text-transform:uppercase; letter-spacing:.04em; }
.snapshot-modal h3 { margin:0; font-size:1.25rem; }.snapshot-modal header span { color:#64748b; font-size:.85rem; }.snapshot-modal header button { border:0; border-radius:50%; width:2rem; height:2rem; font-size:1.3rem; cursor:pointer; }
.snapshot-meta,.snapshot-badges { display:flex; flex-wrap:wrap; gap:.5rem; margin-top:1rem; color:#64748b; font-size:.8rem; }.snapshot-meta span,.snapshot-badges button { padding:.35rem .55rem; border-radius:.5rem; background:#f1f5f9; border:0; color:#334155; }.snapshot-badges button.failed { color:#b91c1c; background:#fef2f2; cursor:pointer; }.snapshot-badges button:disabled { cursor:default; }
.snapshot-cancelled { margin-top:1rem; padding:.7rem .8rem; border-radius:.7rem; background:#fff7ed; color:#9a3412; font-size:.86rem; }
.snapshot-body { display:grid; min-height:10rem; place-items:center; margin:1rem 0; padding:.8rem; overflow:hidden; border:1px solid #e5e7eb; border-radius:.8rem; background:#f8fafc; color:#64748b; }
.snapshot-preview-btn { position:relative; display:block; max-width:100%; padding:0; border:0; background:none; cursor:zoom-in; border-radius:.55rem; overflow:hidden; }
.snapshot-preview-btn img { display:block; width:auto; max-width:100%; max-height:22rem; object-fit:contain; border-radius:.55rem; }
.snapshot-preview-btn:hover img { opacity:.94; }
.snapshot-preview-zoom { position:absolute; top:.5rem; right:.5rem; display:inline-flex; align-items:center; gap:.3rem; padding:.3rem .5rem; border-radius:.5rem; background:rgba(15,23,42,.72); color:#fff; font-size:.72rem; font-weight:600; opacity:0; transition:opacity .16s ease; pointer-events:none; }
.snapshot-preview-zoom svg { width:.9rem; height:.9rem; }
.snapshot-preview-btn:hover .snapshot-preview-zoom { opacity:1; }
.snapshot-modal footer { display:flex; justify-content:flex-end; flex-wrap:wrap; gap:.55rem; }.snapshot-modal footer button { border:1px solid #dbe2ea; border-radius:.6rem; padding:.55rem .75rem; background:#fff; color:#334155; font:inherit; font-size:.84rem; cursor:pointer; }.snapshot-modal footer .primary { background:#2563eb; border-color:#2563eb; color:#fff; }.snapshot-modal.is-dark .snapshot-body,.snapshot-modal.is-dark .snapshot-meta span,.snapshot-modal.is-dark .snapshot-badges button { background:rgba(255,255,255,.05); border-color:rgba(255,255,255,.1); color:rgba(255,255,255,.78); }.snapshot-modal.is-dark .snapshot-body { border-color:rgba(255,255,255,.1); }
</style>
