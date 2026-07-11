<template>
  <Teleport to="body">
    <div class="report-approval-backdrop" @click.self="$emit('close')">
      <section class="report-approval-modal" :class="{ 'is-dark': isDarkMode }">
        <header class="report-approval-head">
          <div>
            <p class="report-approval-kicker">Проверка и утверждение</p>
            <h3>{{ delivery?.scope_label || 'Отчёт' }}</h3>
            <span>{{ formatDate(delivery?.start_date) }} — {{ formatDate(delivery?.end_date) }}</span>
          </div>
          <button type="button" class="report-approval-close" @click="$emit('close')">×</button>
        </header>

        <div v-if="delivery?.anomaly_reason" class="report-approval-alert">
          <span class="report-approval-alert__dot"></span>
          {{ delivery.anomaly_reason }}
        </div>

        <div class="report-approval-body">
          <!-- Левая колонка: отчёт глазами клиента -->
          <div class="report-approval-preview">
            <div class="report-approval-preview__head">
              <strong>Отчёт · {{ formatDate(delivery?.start_date) }} — {{ formatDate(delivery?.end_date) }}</strong>
              <span class="report-status-badge" :class="`report-status-badge--${commentStatus}`">
                {{ statusLabel }}
              </span>
            </div>

            <div class="report-approval-kpi">
              <div class="report-approval-kpi__cell">
                <span>Расходы</span>
                <strong>{{ loadingPreview ? '…' : formatMoney(preview.kpi.cost) }}</strong>
              </div>
              <div class="report-approval-kpi__cell">
                <span>Лиды</span>
                <strong>{{ loadingPreview ? '…' : `${preview.kpi.leads} шт.` }}</strong>
              </div>
              <div class="report-approval-kpi__cell">
                <span>CPL</span>
                <strong>{{ loadingPreview ? '…' : formatMoney(preview.kpi.cpl) }}</strong>
              </div>
            </div>

            <div class="report-approval-chart">
              <span v-if="loadingPreview">Загружаем данные отчёта…</span>
              <template v-else>
                <span class="report-approval-chart__icon">📊</span>
                <span>Графики и разбивка по кампаниям — во вложении отчёта</span>
                <ul v-if="preview.top_campaigns.length" class="report-approval-chart__list">
                  <li v-for="c in preview.top_campaigns.slice(0, 3)" :key="c.name">
                    <span class="report-approval-chart__name">{{ c.name }}</span>
                    <span class="report-approval-chart__val">{{ c.leads }} лид. · {{ formatMoney(c.cost) }}</span>
                  </li>
                </ul>
              </template>
            </div>

            <!-- AI-комментарий — единственная редактируемая зона -->
            <div class="report-approval-ai">
              <div class="report-approval-ai__label">✦ AI-комментарий — единственная редактируемая зона</div>
              <textarea
                v-if="editing"
                v-model="comment"
                rows="6"
                placeholder="Комментарий будет добавлен в отчёт"
                @input="markEdited"
              ></textarea>
              <p v-else class="report-approval-ai__text">{{ comment || 'Комментарий не задан.' }}</p>
              <div class="report-approval-ai__actions">
                <button type="button" class="report-approval-chip" @click="editing = !editing">
                  {{ editing ? 'Готово' : '✎ Править' }}
                </button>
                <button type="button" class="report-approval-chip" :disabled="regenerating" @click="regenerate">
                  {{ regenerating ? 'Генерируем…' : '⟳ Сгенерировать заново' }}
                </button>
              </div>
            </div>
            <p class="report-approval-hint">Статусы: Черновик AI → Отредактировано → Утверждён. Один комментарий уходит во все каналы.</p>
          </div>

          <!-- Правая колонка: как увидит клиент + куда уходит -->
          <aside class="report-approval-side">
            <p class="report-approval-side__label">Как увидит клиент</p>
            <div class="report-approval-tabs">
              <button
                v-for="tab in channelTabs"
                :key="tab.value"
                type="button"
                :class="{ active: activeTab === tab.value, muted: !tab.used }"
                @click="activeTab = tab.value"
              >{{ tab.label }}</button>
            </div>
            <p class="report-approval-channelhint">{{ activeChannelHint }}</p>

            <p class="report-approval-side__label">Куда уходит</p>
            <div class="report-approval-targets">
              <div v-for="t in deliveryTargets" :key="t.key" class="report-approval-target" :class="{ muted: !t.used }">
                <span class="report-approval-target__ic" :class="t.icon">{{ t.glyph }}</span>
                <span>{{ t.text }}</span>
              </div>
              <div v-if="!deliveryTargets.length" class="report-approval-target muted">Каналы не выбраны</div>
            </div>

            <div class="report-approval-side__spacer"></div>

            <button type="button" class="report-approval-secondary" :disabled="savingDraft || sending || cancelling" @click="saveDraft">
              {{ savingDraft ? 'Сохраняем…' : 'Сохранить черновик' }}
            </button>
            <button type="button" class="report-approval-primary" :disabled="sending || savingDraft || cancelling" @click="approve">
              {{ sending ? 'Отправляем…' : '✓ Утвердить и отправить' }}
            </button>
            <button type="button" class="report-approval-cancel" :disabled="sending || savingDraft || cancelling" @click="cancelReport">
              {{ cancelling ? 'Отменяем…' : 'Отменить отчёт' }}
            </button>
          </aside>
        </div>
      </section>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import api from '@/api/axios'
import { useToaster } from '@/composables/useToaster'
import { useTheme } from '@/composables/useTheme'

const props = defineProps({
  delivery: { type: Object, default: null },
})

const emit = defineEmits(['close', 'sent'])
const { isDarkMode } = useTheme()
const toaster = useToaster()

const comment = ref('')
const editing = ref(false)
const sending = ref(false)
const savingDraft = ref(false)
const regenerating = ref(false)
const cancelling = ref(false)
const loadingPreview = ref(false)
const commentStatus = ref('draft') // draft | edited | approved
const activeTab = ref('telegram')

const preview = reactive({
  kpi: { cost: 0, leads: 0, cpl: 0, impressions: 0, clicks: 0 },
  top_campaigns: [],
})

const channelNames = { telegram: 'Telegram', max: 'MAX', email: 'Email' }

const statusLabel = computed(() => ({
  draft: 'Черновик AI',
  edited: 'Отредактировано',
  approved: 'Утверждён',
}[commentStatus.value] || 'Черновик AI'))

const channelTabs = computed(() => {
  const used = new Set(Array.isArray(props.delivery?.channels) ? props.delivery.channels : [])
  const targets = Array.isArray(props.delivery?.chat_target_details) ? props.delivery.chat_target_details : []
  return [
    { value: 'telegram', label: 'Telegram', used: used.has('telegram') || targets.some((target) => target.kind === 'telegram') },
    { value: 'max', label: 'MAX', used: used.has('max') || targets.some((target) => target.kind === 'max') },
    { value: 'email', label: 'Email', used: used.has('email') },
  ]
})

const activeChannelHint = computed(() => {
  if (activeTab.value === 'email') return 'Письмо клиенту: выжимка отчёта в теле + PDF во вложении.'
  if (activeTab.value === 'max') return 'Сообщение в MAX: выжимка показателей + PDF во вложении.'
  return 'Сообщение в Telegram: выжимка 4–6 строк + PNG-превью и ссылка на PDF.'
})

const deliveryTargets = computed(() => {
  const channels = Array.isArray(props.delivery?.channels) ? props.delivery.channels : []
  const targets = Array.isArray(props.delivery?.chat_target_details) ? props.delivery.chat_target_details : []
  const rows = []
  if (channels.includes('telegram')) rows.push({ key: 'tg', icon: 'tg', glyph: 'T', text: 'Telegram — мне лично', used: true })
  if (channels.includes('max')) rows.push({ key: 'mx', icon: 'mx', glyph: 'M', text: 'MAX — мне лично', used: true })
  if (channels.includes('email')) {
    const emails = Array.isArray(props.delivery?.email_recipients) ? props.delivery.email_recipients : []
    rows.push({ key: 'em', icon: 'em', glyph: '@', text: emails.join(', ') || 'Email проекта', used: true })
  }
  for (const target of targets) {
    const isMax = target.kind === 'max'
    rows.push({
      key: `target-${target.id}`,
      icon: isMax ? 'mx' : 'tg',
      glyph: isMax ? 'M' : 'T',
      text: target.title || (target.target_type === 'client' ? 'Личный чат клиента' : 'Группа проекта'),
      used: true,
    })
  }
  return rows
})

const markEdited = () => {
  if (commentStatus.value !== 'edited') commentStatus.value = 'edited'
}

const loadPreview = async () => {
  if (!props.delivery?.id) return
  loadingPreview.value = true
  try {
    const { data } = await api.get(`reports/deliveries/${props.delivery.id}/preview`)
    preview.kpi = data?.kpi || preview.kpi
    preview.top_campaigns = Array.isArray(data?.top_campaigns) ? data.top_campaigns : []
    if (data?.comment && !comment.value) comment.value = data.comment
  } catch {
    // данные превью не критичны — оставляем нули
  } finally {
    loadingPreview.value = false
  }
}

watch(() => props.delivery, (value) => {
  comment.value = value?.comment || ''
  editing.value = false
  commentStatus.value = 'draft'
  const firstUsed = channelTabs.value.find((t) => t.used)
  activeTab.value = firstUsed ? firstUsed.value : 'telegram'
  preview.kpi = { cost: 0, leads: 0, cpl: 0, impressions: 0, clicks: 0 }
  preview.top_campaigns = []
  loadPreview()
}, { immediate: true })

const regenerate = async () => {
  if (!props.delivery?.id || regenerating.value) return
  regenerating.value = true
  try {
    const { data } = await api.post(`reports/deliveries/${props.delivery.id}/regenerate-comment`)
    comment.value = data?.comment || ''
    commentStatus.value = 'draft'
    toaster.success('AI-комментарий обновлён')
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Не удалось сгенерировать комментарий')
  } finally {
    regenerating.value = false
  }
}

// Отмена неотправленного отчёта: клиенту ничего не уходило, подтверждение
// не требуется; запись попадает в историю со статусом «Отменён»
const cancelReport = async () => {
  if (!props.delivery?.id || cancelling.value) return
  cancelling.value = true
  try {
    const { data } = await api.post(`reports/deliveries/${props.delivery.id}/cancel`)
    toaster.success('Отчёт отменён')
    emit('sent', data)
    emit('close')
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Не удалось отменить отчёт')
  } finally {
    cancelling.value = false
  }
}

const saveDraft = async () => {
  if (!props.delivery?.id || savingDraft.value) return
  savingDraft.value = true
  try {
    await api.put(`reports/deliveries/${props.delivery.id}`, { comment: comment.value })
    commentStatus.value = 'edited'
    toaster.success('Черновик сохранён')
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Не удалось сохранить черновик')
  } finally {
    savingDraft.value = false
  }
}

const formatDate = (value) => {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString('ru-RU')
}

const formatMoney = (value) => {
  const num = Number(value || 0)
  return `${new Intl.NumberFormat('ru-RU').format(Math.round(num))} ₽`
}

const approve = async () => {
  if (!props.delivery?.id || sending.value) return
  sending.value = true
  try {
    const { data } = await api.post(`reports/deliveries/${props.delivery.id}/approve`, {
      comment: comment.value,
    })
    if (data?.status === 'sent') {
      commentStatus.value = 'approved'
      toaster.success('Отчёт отправлен')
      emit('sent', data)
      emit('close')
    } else if (data?.status === 'partial') {
      commentStatus.value = 'approved'
      toaster.warning('Отчёт отправлен частично. Неуспешные маршруты можно повторить в истории')
      emit('sent', data)
      emit('close')
    } else {
      toaster.error('Отчёт не удалось отправить. Проверьте каналы доставки')
      emit('sent', data)
    }
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Не удалось отправить отчёт')
  } finally {
    sending.value = false
  }
}
</script>

<style scoped>
/* Компактная шкала модалки папок (ProjectCard.vue) */
.report-approval-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: grid;
  place-items: center;
  padding: 1rem;
  background: rgba(15, 23, 42, 0.45);
}

.report-approval-modal {
  width: min(58rem, 94vw);
  max-height: 90vh;
  overflow: auto;
  border-radius: 1.3rem;
  background: #fff;
  box-shadow: 0 32px 80px rgba(9, 24, 63, 0.32);
  padding: 1.7rem 1.8rem 1.6rem;
}

.report-approval-modal.is-dark {
  background: #252838;
  box-shadow: 0 32px 80px rgba(0, 0, 0, 0.5);
}

.report-approval-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1.2rem;
  margin-bottom: 1.1rem;
}

.report-approval-kicker {
  margin: 0 0 0.3rem;
  color: #2563eb;
  font-size: 0.82rem;
  font-weight: 750;
}

.report-approval-modal.is-dark .report-approval-kicker { color: #8fb0ff; }

.report-approval-head h3 {
  margin: 0;
  color: #171717;
  font-size: 1.4rem;
  font-weight: 800;
  letter-spacing: -0.01em;
}

.report-approval-modal.is-dark .report-approval-head h3 { color: #f8fafc; }

.report-approval-head span {
  display: block;
  margin-top: 0.3rem;
  color: rgba(105, 105, 105, 0.75);
  font-size: 0.92rem;
}

.report-approval-modal.is-dark .report-approval-head span { color: rgba(255, 255, 255, 0.5); }

.report-approval-close {
  width: 2rem;
  height: 2rem;
  border: 0;
  border-radius: 999px;
  background: #f3f5f7;
  color: #697586;
  font-size: 1.3rem;
  line-height: 1;
  flex-shrink: 0;
  cursor: pointer;
}

.report-approval-modal.is-dark .report-approval-close {
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.72);
}

.report-approval-alert {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-bottom: 1rem;
  padding: 0.75rem 0.95rem;
  border-radius: 0.85rem;
  background: #fceaea;
  border: 1px solid rgba(226, 75, 74, 0.26);
  color: #c23a3a;
  font-size: 0.9rem;
  font-weight: 600;
}

.report-approval-modal.is-dark .report-approval-alert {
  background: rgba(226, 75, 74, 0.14);
  border-color: rgba(226, 75, 74, 0.32);
  color: #ff8a87;
}

.report-approval-alert__dot {
  width: 0.55rem;
  height: 0.55rem;
  border-radius: 50%;
  background: #e24b4a;
  flex-shrink: 0;
}

.report-approval-body {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(16rem, 0.9fr);
  gap: 0.9rem;
  align-items: stretch;
}

.report-approval-preview {
  background: #f8fafc;
  border: 1px solid rgba(15, 23, 42, 0.06);
  border-radius: 1rem;
  padding: 1.05rem;
}

.report-approval-modal.is-dark .report-approval-preview {
  background: rgba(255, 255, 255, 0.03);
  border-color: rgba(255, 255, 255, 0.07);
}

.report-approval-preview__head {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  margin-bottom: 0.8rem;
}

.report-approval-preview__head strong {
  flex: 1;
  color: #171717;
  font-size: 0.98rem;
  font-weight: 750;
}

.report-approval-modal.is-dark .report-approval-preview__head strong { color: #f1f5f9; }

.report-status-badge {
  display: inline-flex;
  align-items: center;
  min-height: 1.6rem;
  padding: 0 0.7rem;
  border-radius: 0.55rem;
  font-size: 0.76rem;
  font-weight: 750;
  white-space: nowrap;
}

.report-status-badge--draft { background: #eaf0fe; color: #1e4fc0; }
.report-status-badge--edited { background: #fcf1dc; color: #9a6a12; }
.report-status-badge--approved { background: #e6f6ed; color: #188a4c; }
.report-approval-modal.is-dark .report-status-badge--draft { background: rgba(74, 122, 255, 0.18); color: #8fb0ff; }
.report-approval-modal.is-dark .report-status-badge--edited { background: rgba(239, 168, 39, 0.18); color: #f0b74e; }
.report-approval-modal.is-dark .report-status-badge--approved { background: rgba(24, 138, 76, 0.2); color: #6cd39a; }

.report-approval-kpi {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.55rem;
  margin-bottom: 0.65rem;
}

.report-approval-kpi__cell {
  background: #fff;
  border-radius: 0.75rem;
  padding: 0.7rem 0.8rem;
}

.report-approval-modal.is-dark .report-approval-kpi__cell { background: rgba(255, 255, 255, 0.06); }

.report-approval-kpi__cell span {
  display: block;
  color: #98a2b6;
  font-size: 0.76rem;
  margin-bottom: 0.15rem;
}

.report-approval-kpi__cell strong {
  color: #171717;
  font-size: 1.08rem;
  font-weight: 780;
}

.report-approval-modal.is-dark .report-approval-kpi__cell strong { color: #f1f5f9; }

.report-approval-chart {
  background: #fff;
  border-radius: 0.75rem;
  padding: 0.8rem;
  margin-bottom: 0.65rem;
  color: #98a2b6;
  font-size: 0.86rem;
}

.report-approval-modal.is-dark .report-approval-chart {
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.5);
}

.report-approval-chart__icon { margin-right: 0.4rem; }

.report-approval-chart__list {
  list-style: none;
  margin: 0.65rem 0 0;
  padding: 0;
  display: grid;
  gap: 0.4rem;
}

.report-approval-chart__list li {
  display: flex;
  gap: 0.7rem;
  align-items: center;
  font-size: 0.86rem;
  color: #4b5563;
}

.report-approval-modal.is-dark .report-approval-chart__list li { color: rgba(255, 255, 255, 0.6); }

.report-approval-chart__name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.report-approval-chart__val {
  color: #8a93a3;
  white-space: nowrap;
}

.report-approval-ai {
  border: 1.5px dashed rgba(37, 99, 235, 0.65);
  background: rgba(37, 99, 235, 0.06);
  border-radius: 0.85rem;
  padding: 0.8rem 0.9rem;
}

.report-approval-modal.is-dark .report-approval-ai {
  border-color: rgba(74, 122, 255, 0.7);
  background: rgba(74, 122, 255, 0.1);
}

.report-approval-ai__label {
  font-size: 0.78rem;
  font-weight: 750;
  color: #1e4fc0;
  margin-bottom: 0.45rem;
}

.report-approval-modal.is-dark .report-approval-ai__label { color: #8fb0ff; }

.report-approval-ai__text {
  margin: 0;
  color: #1e4fc0;
  font-size: 0.92rem;
  line-height: 1.55;
  white-space: pre-wrap;
}

.report-approval-modal.is-dark .report-approval-ai__text { color: #c3d4ff; }

.report-approval-ai textarea {
  width: 100%;
  resize: vertical;
  min-height: 8.5rem;
  border: 1px solid rgba(37, 99, 235, 0.35);
  border-radius: 0.7rem;
  padding: 0.7rem 0.85rem;
  color: #171717;
  background: #fff;
  outline: none;
  font: inherit;
  font-size: 0.92rem;
  transition: border-color 0.13s ease, box-shadow 0.13s ease;
}

.report-approval-ai textarea:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.report-approval-modal.is-dark .report-approval-ai textarea {
  background: rgba(0, 0, 0, 0.2);
  border-color: rgba(74, 122, 255, 0.4);
  color: #f1f5f9;
}

.report-approval-ai__actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.6rem;
}

.report-approval-chip {
  min-height: 2.15rem;
  padding: 0 0.85rem;
  border-radius: 0.6rem;
  border: 1px solid rgba(37, 99, 235, 0.28);
  background: #fff;
  color: #2563eb;
  font-size: 0.85rem;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.13s;
}

.report-approval-chip:hover:not(:disabled) { background: rgba(37, 99, 235, 0.06); }

.report-approval-modal.is-dark .report-approval-chip {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(111, 155, 255, 0.4);
  color: #8fb0ff;
}

.report-approval-chip:disabled { opacity: 0.6; cursor: default; }

.report-approval-hint {
  margin: 0.6rem 0.1rem 0;
  color: #98a2b6;
  font-size: 0.78rem;
}

.report-approval-side {
  display: flex;
  flex-direction: column;
  background: #fff;
  border: 1px solid rgba(15, 23, 42, 0.06);
  border-radius: 1rem;
  padding: 1.05rem;
}

.report-approval-modal.is-dark .report-approval-side {
  background: rgba(255, 255, 255, 0.03);
  border-color: rgba(255, 255, 255, 0.07);
}

.report-approval-side__label {
  margin: 0 0 0.55rem;
  font-size: 0.72rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #98a2b6;
  font-weight: 750;
}

.report-approval-side__label + .report-approval-side__label,
.report-approval-channelhint + .report-approval-side__label {
  margin-top: 1rem;
}

.report-approval-tabs {
  display: inline-flex;
  background: #f2f5f9;
  border-radius: 0.7rem;
  padding: 0.22rem;
  gap: 0.15rem;
  margin-bottom: 0.55rem;
}

.report-approval-modal.is-dark .report-approval-tabs { background: rgba(255, 255, 255, 0.06); }

.report-approval-tabs button {
  font-size: 0.85rem;
  padding: 0.38rem 0.85rem;
  border-radius: 0.55rem;
  border: 0;
  background: transparent;
  color: #5c6b84;
  font-weight: 700;
  cursor: pointer;
}

.report-approval-tabs button.active {
  background: #fff;
  color: #2563eb;
  box-shadow: 0 1px 3px rgba(20, 30, 55, 0.12);
}

.report-approval-modal.is-dark .report-approval-tabs button { color: rgba(255, 255, 255, 0.6); }
.report-approval-modal.is-dark .report-approval-tabs button.active {
  background: rgba(74, 122, 255, 0.22);
  color: #8fb0ff;
  box-shadow: none;
}

.report-approval-tabs button.muted { color: #c0c8d6; }
.report-approval-modal.is-dark .report-approval-tabs button.muted { color: rgba(255, 255, 255, 0.28); }

.report-approval-channelhint {
  margin: 0;
  color: #8a93a3;
  font-size: 0.85rem;
  line-height: 1.5;
}

.report-approval-modal.is-dark .report-approval-channelhint { color: rgba(255, 255, 255, 0.5); }

.report-approval-targets {
  display: grid;
  gap: 0.45rem;
}

.report-approval-target {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  font-size: 0.9rem;
  font-weight: 600;
  color: #171717;
}

.report-approval-modal.is-dark .report-approval-target { color: #e6ebf3; }

.report-approval-target.muted { color: #98a2b6; }
.report-approval-modal.is-dark .report-approval-target.muted { color: rgba(255, 255, 255, 0.4); }

.report-approval-target__ic {
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 0.45rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.72rem;
  font-weight: 750;
  color: #fff;
  flex-shrink: 0;
}

.report-approval-target__ic.tg { background: #2aa5e0; }
.report-approval-target__ic.mx { background: #6c5ce7; }
.report-approval-target__ic.em { background: #8896ac; }

.report-approval-side__spacer {
  flex: 1;
  min-height: 0.9rem;
}

.report-approval-secondary,
.report-approval-primary {
  min-height: 2.7rem;
  border-radius: 0.75rem;
  padding: 0 1.1rem;
  font-size: 0.95rem;
  font-weight: 700;
  width: 100%;
  cursor: pointer;
}

.report-approval-secondary {
  background: rgba(15, 23, 42, 0.06);
  border: 0;
  color: #444;
  margin-bottom: 0.5rem;
  transition: background 0.13s;
}

.report-approval-secondary:hover:not(:disabled) { background: rgba(15, 23, 42, 0.1); }

.report-approval-modal.is-dark .report-approval-secondary {
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.75);
}

.report-approval-primary {
  background: #2563eb;
  color: #fff;
  border: 0;
  transition: background 0.13s ease, box-shadow 0.13s ease;
}

.report-approval-primary:hover:not(:disabled) {
  background: #1d4ed8;
  box-shadow: 0 6px 18px rgba(37, 99, 235, 0.35);
}

.report-approval-secondary:disabled,
.report-approval-primary:disabled {
  opacity: 0.6;
  cursor: default;
}

/* Тихая отмена под основными действиями: текстовая, без визуального веса */
.report-approval-cancel {
  margin-top: 0.5rem;
  border: 0;
  background: transparent;
  color: #c23a3a;
  font-size: 0.88rem;
  font-weight: 700;
  cursor: pointer;
  opacity: 0.75;
}

.report-approval-cancel:hover:not(:disabled) { opacity: 1; }
.report-approval-cancel:disabled { opacity: 0.4; cursor: default; }

.report-approval-modal.is-dark .report-approval-cancel { color: #ff8a87; }

@media (max-width: 720px) {
  .report-approval-body {
    grid-template-columns: 1fr;
  }
  .report-approval-side__spacer {
    display: none;
  }
}
</style>
