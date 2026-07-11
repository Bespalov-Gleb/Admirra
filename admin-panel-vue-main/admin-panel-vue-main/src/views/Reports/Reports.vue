<template>
  <main class="reports-page" :class="{ 'is-dark': isDarkMode }">
    <header class="reports-head">
      <div>
        <h1>Отчёты</h1>
        <p>Проверка, подтверждение и история отправок по проектам.</p>
      </div>
      <button type="button" class="reports-refresh" :disabled="loading" @click="load">
        <ArrowPathIcon :class="{ spinning: loading }" />
        <span>{{ loading ? 'Обновляем...' : 'Обновить' }}</span>
      </button>
    </header>

    <section class="reports-layout">
      <div class="reports-panel">
        <div class="reports-panel-head">
          <div>
            <h2>Ожидают проверки</h2>
            <p>Автоотправка с проверкой и отчёты, остановленные детектором.</p>
          </div>
          <span>{{ pending.length }}</span>
        </div>
        <div class="reports-list">
          <button
            v-for="item in pending"
            :key="item.id"
            type="button"
            class="report-queue-card"
            :class="{ 'report-queue-card--detector': item.source === 'detector' }"
            @click="activeDelivery = item"
          >
            <span class="report-queue-card__top">
              <span class="report-queue-dot" :class="item.source === 'detector' ? 'report-queue-dot--red' : 'report-queue-dot--amber'"></span>
              <span class="report-status" :class="`report-status--${item.source}`">
                {{ item.source === 'detector' ? 'Детектор' : item.source === 'auto' ? 'Авто' : 'Вручную' }}
              </span>
              <span class="report-queue-card__check">Проверить</span>
            </span>
            <strong>{{ item.scope_label }}</strong>
            <small>{{ formatDate(item.start_date) }} — {{ formatDate(item.end_date) }}</small>
            <em v-if="item.anomaly_reason">{{ item.anomaly_reason }}</em>
          </button>
          <div v-if="!pending.length" class="reports-empty">Очередь проверки пуста</div>
        </div>
      </div>

      <div class="reports-panel">
        <div class="reports-panel-head">
          <div>
            <h2>История отправок</h2>
            <p>Последние отправленные и неуспешные отчёты.</p>
          </div>
          <span>{{ history.length }}</span>
        </div>
        <div class="reports-table">
          <div class="reports-table-row reports-table-row--head">
            <span>Дата</span>
            <span>Проект · период</span>
            <span>Кто утвердил</span>
            <span>Каналы</span>
            <span>Статус</span>
          </div>
          <div v-for="item in history" :key="item.id" class="reports-table-row">
            <span class="history-date">{{ formatDateTime(item.sent_at || item.approved_at || item.created_at) }}</span>
            <span class="history-scope">{{ item.scope_label }} · {{ formatDate(item.start_date) }} — {{ formatDate(item.end_date) }}</span>
            <span class="history-approver">{{ item.approved_by_name || 'авто' }}</span>
            <span class="history-channels">
              <span
                v-for="ch in channelBadges(item)"
                :key="ch.key"
                class="history-channel-ic"
                :class="[ch.cls, { failed: ch.ok === false }]"
                :title="ch.title"
              ><span class="hc-mask" :class="`hc-mask--${ch.cls}`"></span></span>
              <span v-if="!channelBadges(item).length" class="history-channels-empty">—</span>
            </span>
            <span class="history-status-cell">
              <span :class="['history-status', item.status]">{{ statusLabel(item.status) }}</span>
              <button
                v-if="item.status === 'failed' || item.status === 'partial'"
                type="button"
                class="history-retry"
                :disabled="retryingId === item.id"
                :title="'Повторить отправку'"
                @click="retryDelivery(item)"
              >
                <ArrowPathIcon :class="{ spinning: retryingId === item.id }" />
              </button>
            </span>
          </div>
          <div v-if="!history.length" class="reports-empty">Истории пока нет</div>
        </div>
      </div>
    </section>

    <ReportApprovalModal
      v-if="activeDelivery"
      :delivery="activeDelivery"
      @close="activeDelivery = null"
      @sent="handleSent"
    />
  </main>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ArrowPathIcon } from '@heroicons/vue/24/outline'
import api from '@/api/axios'
import { useToaster } from '@/composables/useToaster'
import { useTheme } from '@/composables/useTheme'
import { refreshReportsQueue } from '@/composables/useReportsQueue'
import ReportApprovalModal from '../GeneralStats3/components/ReportApprovalModal.vue'

const { isDarkMode } = useTheme()
const toaster = useToaster()
const loading = ref(false)
const pending = ref([])
const history = ref([])
const activeDelivery = ref(null)
const retryingId = ref(null)

const load = async () => {
  loading.value = true
  try {
    const [pendingResp, historyResp] = await Promise.all([
      api.get('reports/deliveries', { params: { status: 'pending' } }),
      api.get('reports/deliveries', { params: { status: 'history' } }),
    ])
    pending.value = Array.isArray(pendingResp.data) ? pendingResp.data : []
    history.value = Array.isArray(historyResp.data) ? historyResp.data : []
    refreshReportsQueue()
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Не удалось загрузить отчёты')
  } finally {
    loading.value = false
  }
}

const CHANNEL_META = {
  telegram: { cls: 'tg', label: 'Telegram' },
  max: { cls: 'mx', label: 'MAX' },
  email: { cls: 'em', label: 'Email' },
}

const channelBadges = (item) => {
  const res = item.delivery_results || {}
  const out = []
  for (const ch of (item.channels || [])) {
    const meta = CHANNEL_META[ch]
    if (!meta) continue
    const raw = res[ch]
    const ok = raw == null ? null : Boolean(raw)
    const error = res.errors?.[ch]
    out.push({ key: ch, cls: meta.cls, ok, title: `${meta.label}${ok === false ? ` — ${error || 'ошибка'}` : ''}` })
  }
  const targetResults = res.targets || {}
  for (const targetId of (item.chat_targets || [])) {
    const target = targetResults[String(targetId)] || {}
    const ok = target.ok == null ? null : Boolean(target.ok)
    out.push({
      key: `target-${targetId}`,
      cls: target.kind === 'max' ? 'mx' : 'tg',
      ok,
      title: `${target.title || 'Получатель проекта'}${ok === false ? ` — ${target.error || 'ошибка'}` : ''}`,
    })
  }
  return out
}

const retryDelivery = async (item) => {
  if (!item?.id || retryingId.value) return
  retryingId.value = item.id
  try {
    const { data } = await api.post(`reports/deliveries/${item.id}/approve`, { comment: item.comment })
    if (data?.status === 'sent') toaster.success('Неуспешные маршруты отправлены повторно')
    else if (data?.status === 'partial') toaster.warning('Часть маршрутов по-прежнему недоступна')
    else toaster.error('Повторная отправка не удалась. Проверьте каналы')
    await load()
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Не удалось повторить отправку')
  } finally {
    retryingId.value = null
  }
}

const handleSent = async () => {
  activeDelivery.value = null
  await load()
}

const formatDate = (value) => {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString('ru-RU')
}

const statusLabel = (status) => ({
  sent: 'Отправлен',
  partial: 'Частично отправлен',
  failed: 'Ошибка',
  cancelled: 'Отменён',
}[status] || status)

const formatDateTime = (value) => {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

onMounted(load)
</script>

<style scoped>
.reports-page {
  width: min(110.4167rem, calc(100% - 3rem));
  margin: 0 auto;
  padding: 5rem 0 3rem;
  font-family: Inter, system-ui, sans-serif;
}

.reports-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1.6rem;
  margin-bottom: 2rem;
}

.reports-head h1 {
  margin: 0;
  color: #171717;
  font-size: 2.2rem;
  font-weight: 700;
  letter-spacing: -0.01em;
}

.reports-page.is-dark .reports-head h1 { color: #f8fafc; }

.reports-head p,
.reports-panel-head p {
  margin: 0.45rem 0 0;
  color: #767676;
  font-size: 1.18rem;
}

.reports-page.is-dark .reports-head p,
.reports-page.is-dark .reports-panel-head p { color: rgba(255, 255, 255, 0.5); }

.reports-refresh {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.7rem;
  height: 3.6rem;
  border-radius: 0.95rem;
  padding: 0 1.25rem;
  background: #fff;
  border: 1px solid rgba(105, 105, 105, 0.14);
  color: #334155;
  font-size: 1.12rem;
  font-weight: 650;
  white-space: nowrap;
  cursor: pointer;
  transition: transform 0.18s, border-color 0.18s, background-color 0.18s;
}

.reports-refresh svg {
  width: 1.45rem;
  height: 1.45rem;
}

.reports-refresh:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: rgba(37, 99, 235, 0.32);
  color: #2563eb;
}

.reports-refresh:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  transform: none;
}

.reports-page.is-dark .reports-refresh {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.1);
  color: #6f9bff;
}

.reports-layout {
  display: grid;
  grid-template-columns: minmax(28rem, 0.78fr) minmax(0, 1.22fr);
  gap: 1.6rem;
}

.reports-panel {
  background: #fff;
  border: 1px solid #eef0f2;
  border-radius: 1.4rem;
  padding: 1.6rem;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03), 0 4px 16px rgba(15, 23, 42, 0.02);
}

.reports-page.is-dark .reports-panel {
  background: #252838;
  border-color: rgba(255, 255, 255, 0.08);
  box-shadow: 0 1rem 3rem rgba(0, 0, 0, 0.32);
}

.reports-panel-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1.2rem;
  margin-bottom: 1.3rem;
}

.reports-panel-head h2 {
  margin: 0;
  color: #171717;
  font-size: 1.42rem;
  font-weight: 650;
}

.reports-page.is-dark .reports-panel-head h2 { color: #f1f5f9; }

.reports-panel-head span {
  display: grid;
  place-items: center;
  min-width: 3rem;
  height: 2.6rem;
  padding: 0 0.75rem;
  border-radius: 999px;
  background: #eef4ff;
  color: #2563eb;
  font-size: 1.05rem;
  font-weight: 750;
}

.reports-page.is-dark .reports-panel-head span {
  background: rgba(74, 122, 255, 0.16);
  color: #6f9bff;
}

.reports-list { display: grid; gap: 0.75rem; }

.report-queue-card {
  display: grid;
  justify-items: start;
  gap: 0.45rem;
  text-align: left;
  padding: 1.05rem 1.1rem;
  border-radius: 1rem;
  background: #f8fafc;
  border: 1px solid rgba(105, 105, 105, 0.08);
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s, transform 0.15s;
}

.report-queue-card:hover {
  transform: translateY(-1px);
  border-color: rgba(37, 99, 235, 0.26);
  background: #fff;
}

.reports-page.is-dark .report-queue-card {
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(255, 255, 255, 0.07);
}

.reports-page.is-dark .report-queue-card:hover {
  background: rgba(255, 255, 255, 0.07);
  border-color: rgba(111, 155, 255, 0.5);
  box-shadow: none;
}

.report-queue-card--detector {
  background: #fff7f7;
  border-color: rgba(226, 75, 74, 0.22);
}

.reports-page.is-dark .report-queue-card--detector {
  background: rgba(226, 75, 74, 0.1);
  border-color: rgba(226, 75, 74, 0.32);
}

.report-queue-card__top {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  width: 100%;
}

.report-queue-card__check {
  margin-left: auto;
  color: #2563eb;
  font-size: 1.05rem;
  font-weight: 700;
}

.reports-page.is-dark .report-queue-card__check { color: #6f9bff; }

.report-queue-dot {
  width: 0.8rem;
  height: 0.8rem;
  border-radius: 50%;
  flex-shrink: 0;
}

.report-queue-dot--amber { background: #efa827; }
.report-queue-dot--red { background: #e24b4a; }

.report-queue-card strong {
  color: #171717;
  font-size: 1.2rem;
  font-weight: 650;
  line-height: 1.25;
}

.reports-page.is-dark .report-queue-card strong { color: #f1f5f9; }

.report-queue-card small,
.report-queue-card em {
  color: #8a93a3;
  font-style: normal;
  font-size: 1.05rem;
  line-height: 1.35;
}

.reports-page.is-dark .report-queue-card small { color: rgba(255, 255, 255, 0.45); }

.report-queue-card--detector em { color: #c23a3a; }
.reports-page.is-dark .report-queue-card--detector em { color: #ff8a87; }

.report-status,
.history-status {
  display: inline-flex;
  align-items: center;
  min-height: 2.2rem;
  padding: 0 0.75rem;
  border-radius: 999px;
  font-size: 0.98rem;
  font-weight: 700;
}

.report-status--detector { background: #fceaea; color: #c23a3a; }
.report-status--auto { background: #eaf0fe; color: #1e4fc0; }
.report-status--manual { background: #e6f6ed; color: #188a4c; }
.reports-page.is-dark .report-status--detector { background: rgba(226, 75, 74, 0.18); color: #ff8a87; }
.reports-page.is-dark .report-status--auto { background: rgba(74, 122, 255, 0.18); color: #6f9bff; }
.reports-page.is-dark .report-status--manual { background: rgba(24, 138, 76, 0.2); color: #6cd39a; }

.reports-table { display: grid; gap: 0.45rem; }

.reports-table-row {
  display: grid;
  grid-template-columns: 10rem minmax(18rem, 1fr) 9rem 7.2rem 10rem;
  gap: 1rem;
  align-items: center;
  min-height: 3.8rem;
  padding: 0 1rem;
  border-radius: 0.9rem;
  background: #f8fafc;
  color: #4b5563;
}

.reports-page.is-dark .reports-table-row {
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.6);
}

.reports-table-row--head {
  background: transparent;
  color: #98a2b6;
  font-size: 0.92rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  min-height: 0;
  padding-top: 0;
  padding-bottom: 0.25rem;
}

.reports-page.is-dark .reports-table-row--head { color: rgba(255, 255, 255, 0.4); background: transparent; }

.history-date { color: #5c6b84; font-size: 1.05rem; }
.history-scope {
  min-width: 0;
  overflow: hidden;
  color: #171717;
  font-size: 1.12rem;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.history-approver { color: #5c6b84; font-size: 1.05rem; }
.reports-page.is-dark .history-date,
.reports-page.is-dark .history-approver { color: rgba(255, 255, 255, 0.5); }
.reports-page.is-dark .history-scope { color: #e6ebf3; }

.history-channels { display: inline-flex; align-items: center; flex-wrap: wrap; gap: 0.4rem; }

.history-channel-ic {
  width: 1.85rem;
  height: 1.85rem;
  border-radius: 0.55rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

/* Фирменные градиентные подложки — как у капсул каналов на дашборде */
.history-channel-ic.tg { background: linear-gradient(135deg, #2f6df6 0%, #14b8d5 100%); }
.history-channel-ic.mx { background: linear-gradient(135deg, #6d3df5 0%, #a45cf0 100%); }
.history-channel-ic.em { background: linear-gradient(135deg, #64748b 0%, #94a3b8 100%); }
.history-channel-ic.failed { opacity: 0.35; }

/* Фирменные mask-иконки каналов (те же, что на дашборде и в настройках отчётов) */
.hc-mask {
  display: block;
  background: #fff;
  flex: 0 0 auto;
}

.hc-mask--tg {
  width: 1rem;
  height: 1rem;
  transform: translateX(-0.06rem);
  -webkit-mask: url("data:image/svg+xml,%3Csvg width='21' height='21' viewBox='0 0 21 21' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M18.42 3.05 2.54 9.17c-1.08.43-1.07 1.03-.2 1.3l4.08 1.27 1.56 4.79c.2.55.1.77.68.77.45 0 .65-.2.9-.45l2.16-2.1 4.5 3.32c.83.46 1.43.22 1.64-.77l2.97-13.98c.3-1.22-.47-1.77-1.41-1.27ZM6.95 11.45l9.47-5.97c.47-.28.9-.13.55.18l-8.1 7.3-.31 3.31-1.61-4.82Z' fill='black'/%3E%3C/svg%3E") center / contain no-repeat;
  mask: url("data:image/svg+xml,%3Csvg width='21' height='21' viewBox='0 0 21 21' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M18.42 3.05 2.54 9.17c-1.08.43-1.07 1.03-.2 1.3l4.08 1.27 1.56 4.79c.2.55.1.77.68.77.45 0 .65-.2.9-.45l2.16-2.1 4.5 3.32c.83.46 1.43.22 1.64-.77l2.97-13.98c.3-1.22-.47-1.77-1.41-1.27ZM6.95 11.45l9.47-5.97c.47-.28.9-.13.55.18l-8.1 7.3-.31 3.31-1.61-4.82Z' fill='black'/%3E%3C/svg%3E") center / contain no-repeat;
}

.hc-mask--mx {
  width: 1.15rem;
  height: 1.15rem;
  -webkit-mask: url("data:image/svg+xml,%3Csvg width='23' height='23' viewBox='0 0 23 23' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath fill-rule='evenodd' clip-rule='evenodd' d='M11.3262 0.526703C9.97595 0.644538 9.03042 0.858842 7.96223 1.28911C4.58971 2.64757 2.17288 5.63667 1.5882 9.17233C1.46913 9.89246 1.44765 10.1918 1.45045 11.0932C1.45635 13.0195 1.63889 14.1725 2.40714 17.1368C2.76373 18.5127 2.9304 19.5394 2.9304 20.3602C2.9304 20.9016 3.20825 21.2516 3.73877 21.3784C4.01264 21.4438 4.54202 21.4188 4.92334 21.3224C5.78836 21.1037 6.61078 20.6623 7.15586 20.1242C7.29619 19.9857 7.41359 19.8723 7.41673 19.8723C7.41989 19.8722 7.5789 19.9796 7.77008 20.111C9.10923 21.0308 9.9351 21.2986 11.5948 21.3512C14.4847 21.4427 17.1617 20.3757 19.1852 18.3258C21.6244 15.8548 22.6485 12.3498 21.9555 8.84481C21.5449 6.76834 20.5412 4.89959 19.0401 3.41648C17.4445 1.83999 15.5146 0.897223 13.2626 0.59407C12.8572 0.539506 11.6576 0.497774 11.3262 0.526703ZM11.3121 5.65698C10.2161 5.75895 9.1042 6.28998 8.31739 7.08719C7.04926 8.37209 6.45516 10.2727 6.57709 12.6546C6.64454 13.9728 6.86458 15.0956 7.19728 15.8193C7.32036 16.087 7.42922 16.2273 7.55541 16.2807C7.68149 16.3341 7.8597 16.2766 8.13184 16.0949C8.35149 15.9482 8.82063 15.5607 8.96161 15.4096L9.04223 15.3231L9.21603 15.4376C9.47259 15.6068 10.0304 15.8764 10.3364 15.9792C11.3635 16.3241 12.443 16.3182 13.4976 15.9618C14.3646 15.6688 15.2018 15.1074 15.7963 14.4203C16.7195 13.3535 17.208 11.9255 17.0986 10.6135C17.0368 9.87193 16.8818 9.29636 16.5722 8.65863C15.7542 6.97365 14.1951 5.87211 12.3379 5.66715C12.0796 5.63862 11.5643 5.63352 11.3121 5.65698Z' fill='black'/%3E%3C/svg%3E") center / contain no-repeat;
  mask: url("data:image/svg+xml,%3Csvg width='23' height='23' viewBox='0 0 23 23' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath fill-rule='evenodd' clip-rule='evenodd' d='M11.3262 0.526703C9.97595 0.644538 9.03042 0.858842 7.96223 1.28911C4.58971 2.64757 2.17288 5.63667 1.5882 9.17233C1.46913 9.89246 1.44765 10.1918 1.45045 11.0932C1.45635 13.0195 1.63889 14.1725 2.40714 17.1368C2.76373 18.5127 2.9304 19.5394 2.9304 20.3602C2.9304 20.9016 3.20825 21.2516 3.73877 21.3784C4.01264 21.4438 4.54202 21.4188 4.92334 21.3224C5.78836 21.1037 6.61078 20.6623 7.15586 20.1242C7.29619 19.9857 7.41359 19.8723 7.41673 19.8723C7.41989 19.8722 7.5789 19.9796 7.77008 20.111C9.10923 21.0308 9.9351 21.2986 11.5948 21.3512C14.4847 21.4427 17.1617 20.3757 19.1852 18.3258C21.6244 15.8548 22.6485 12.3498 21.9555 8.84481C21.5449 6.76834 20.5412 4.89959 19.0401 3.41648C17.4445 1.83999 15.5146 0.897223 13.2626 0.59407C12.8572 0.539506 11.6576 0.497774 11.3262 0.526703ZM11.3121 5.65698C10.2161 5.75895 9.1042 6.28998 8.31739 7.08719C7.04926 8.37209 6.45516 10.2727 6.57709 12.6546C6.64454 13.9728 6.86458 15.0956 7.19728 15.8193C7.32036 16.087 7.42922 16.2273 7.55541 16.2807C7.68149 16.3341 7.8597 16.2766 8.13184 16.0949C8.35149 15.9482 8.82063 15.5607 8.96161 15.4096L9.04223 15.3231L9.21603 15.4376C9.47259 15.6068 10.0304 15.8764 10.3364 15.9792C11.3635 16.3241 12.443 16.3182 13.4976 15.9618C14.3646 15.6688 15.2018 15.1074 15.7963 14.4203C16.7195 13.3535 17.208 11.9255 17.0986 10.6135C17.0368 9.87193 16.8818 9.29636 16.5722 8.65863C15.7542 6.97365 14.1951 5.87211 12.3379 5.66715C12.0796 5.63862 11.5643 5.63352 11.3121 5.65698Z' fill='black'/%3E%3C/svg%3E") center / contain no-repeat;
}

.hc-mask--em {
  width: 1.05rem;
  height: 0.78rem;
  -webkit-mask: url("data:image/svg+xml,%3Csvg width='26' height='19' viewBox='0 0 26 19' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M2.25 0H23.14C24.38 0 25.39 1.01 25.39 2.25V16.56C25.39 17.8 24.38 18.81 23.14 18.81H2.25C1.01 18.81 0 17.8 0 16.56V2.25C0 1.01 1.01 0 2.25 0ZM2.12 2.52V16.3C2.12 16.55 2.32 16.75 2.57 16.75H22.82C23.07 16.75 23.27 16.55 23.27 16.3V2.52L13.56 10.4C13.06 10.81 12.33 10.81 11.83 10.4L2.12 2.52ZM21.02 2.06H4.36L12.69 8.8L21.02 2.06Z' fill='black'/%3E%3C/svg%3E") center / contain no-repeat;
  mask: url("data:image/svg+xml,%3Csvg width='26' height='19' viewBox='0 0 26 19' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M2.25 0H23.14C24.38 0 25.39 1.01 25.39 2.25V16.56C25.39 17.8 24.38 18.81 23.14 18.81H2.25C1.01 18.81 0 17.8 0 16.56V2.25C0 1.01 1.01 0 2.25 0ZM2.12 2.52V16.3C2.12 16.55 2.32 16.75 2.57 16.75H22.82C23.07 16.75 23.27 16.55 23.27 16.3V2.52L13.56 10.4C13.06 10.81 12.33 10.81 11.83 10.4L2.12 2.52ZM21.02 2.06H4.36L12.69 8.8L21.02 2.06Z' fill='black'/%3E%3C/svg%3E") center / contain no-repeat;
}

.history-channels-empty { color: #c0c8d6; }

.history-status-cell { display: inline-flex; align-items: center; gap: 0.6rem; }

.history-status.sent { background: #e6f6ed; color: #188a4c; }
.history-status.partial { background: #fff4db; color: #9a6700; }
.history-status.failed { background: #fceaea; color: #c23a3a; }
.history-status.cancelled { background: #eef1f5; color: #69758a; }
.reports-page.is-dark .history-status.sent { background: rgba(24, 138, 76, 0.2); color: #6cd39a; }
.reports-page.is-dark .history-status.partial { background: rgba(239, 168, 39, 0.18); color: #f6c768; }
.reports-page.is-dark .history-status.failed { background: rgba(226, 75, 74, 0.18); color: #ff8a87; }

.history-retry {
  display: inline-grid;
  place-items: center;
  width: 2.35rem;
  height: 2.35rem;
  border-radius: 0.8rem;
  border: 1px solid rgba(226, 75, 74, 0.3);
  background: #fff;
  color: #e11d48;
  flex-shrink: 0;
  cursor: pointer;
}

.history-retry svg {
  width: 1.25rem;
  height: 1.25rem;
}

.history-retry:disabled { opacity: 0.5; }

.reports-page.is-dark .history-retry {
  background: rgba(226, 75, 74, 0.12);
  border-color: rgba(226, 75, 74, 0.3);
  color: #ff8a87;
}

.reports-empty {
  padding: 1.5rem;
  border-radius: 1rem;
  background: #f8fafc;
  color: #94a3b8;
  font-size: 1.12rem;
  text-align: center;
}

.reports-page.is-dark .reports-empty {
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.4);
}

@media (max-width: 960px) {
  .reports-layout { grid-template-columns: 1fr; }
  .reports-head {
    align-items: stretch;
    flex-direction: column;
  }
  .reports-refresh {
    align-self: flex-start;
  }
  .reports-table-row {
    grid-template-columns: 1fr;
    gap: 0.5rem;
    padding: 1rem;
    min-height: 0;
  }
  .reports-table-row--head { display: none; }
  .history-scope {
    white-space: normal;
  }
}

.spinning {
  animation: reports-spin 0.9s linear infinite;
}

@keyframes reports-spin {
  to { transform: rotate(360deg); }
}
</style>
