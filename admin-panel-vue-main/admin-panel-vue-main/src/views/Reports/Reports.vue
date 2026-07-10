<template>
  <main class="reports-page" :class="{ 'is-dark': isDarkMode }">
    <header class="reports-head">
      <div>
        <h1>Отчёты</h1>
        <p>Проверка, подтверждение и история отправок по проектам.</p>
      </div>
      <button type="button" class="reports-refresh" :disabled="loading" @click="load">
        {{ loading ? 'Обновляем...' : 'Обновить' }}
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
              <span class="report-queue-card__check">Проверить →</span>
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
              >{{ ch.glyph }}</span>
              <span v-if="!channelBadges(item).length" class="history-channels-empty">—</span>
            </span>
            <span class="history-status-cell">
              <span :class="['history-status', item.status]">{{ item.status === 'sent' ? 'Доставлен' : 'Ошибка' }}</span>
              <button
                v-if="item.status === 'failed'"
                type="button"
                class="history-retry"
                :disabled="retryingId === item.id"
                :title="'Повторить отправку'"
                @click="retryDelivery(item)"
              >⟳</button>
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
  telegram: { glyph: 'T', cls: 'tg', label: 'Telegram' },
  max: { glyph: 'M', cls: 'mx', label: 'MAX' },
  email: { glyph: '@', cls: 'em', label: 'Email' },
}

const channelBadges = (item) => {
  const res = item.delivery_results || {}
  const out = []
  for (const ch of (item.channels || [])) {
    const meta = CHANNEL_META[ch]
    if (!meta) continue
    const raw = res[ch]
    const ok = raw == null ? null : Boolean(raw)
    out.push({ key: ch, glyph: meta.glyph, cls: meta.cls, ok, title: `${meta.label}${ok === false ? ' — ошибка' : ''}` })
  }
  if ((item.chat_targets || []).length) {
    let ok = null
    if (typeof res.groups === 'string') ok = parseInt(res.groups.split('/')[0], 10) > 0
    out.push({ key: 'groups', glyph: 'G', cls: 'tg', ok, title: `Группы${ok === false ? ' — ошибка' : ''}` })
  }
  return out
}

const retryDelivery = async (item) => {
  if (!item?.id || retryingId.value) return
  retryingId.value = item.id
  try {
    const { data } = await api.post(`reports/deliveries/${item.id}/approve`, { comment: item.comment })
    if (data?.status === 'sent') toaster.success('Отчёт отправлен повторно')
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
  width: min(112rem, calc(100% - 4rem));
  margin: 0 auto;
  padding: 4rem 0;
  font-family: Inter, system-ui, sans-serif;
}

.reports-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 2rem;
  margin-bottom: 2.4rem;
}

.reports-head h1 {
  margin: 0;
  color: #171717;
  font-size: 2.4rem;
  font-weight: 700;
  letter-spacing: -0.01em;
}

.reports-page.is-dark .reports-head h1 { color: #f8fafc; }

.reports-head p,
.reports-panel-head p {
  margin: 0.5rem 0 0;
  color: #767676;
  font-size: 1.3rem;
}

.reports-page.is-dark .reports-head p,
.reports-page.is-dark .reports-panel-head p { color: rgba(255, 255, 255, 0.5); }

.reports-refresh {
  height: 4rem;
  border-radius: 1.2rem;
  padding: 0 1.8rem;
  background: #fff;
  border: 1px solid #e5e7eb;
  color: #2563eb;
  font-size: 1.3rem;
  font-weight: 650;
  white-space: nowrap;
}

.reports-refresh:disabled { opacity: 0.6; }

.reports-page.is-dark .reports-refresh {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.1);
  color: #6f9bff;
}

.reports-layout {
  display: grid;
  grid-template-columns: minmax(32rem, 0.85fr) minmax(0, 1.15fr);
  gap: 1.8rem;
}

.reports-panel {
  background: #fff;
  border: 1px solid #ececf2;
  border-radius: 2rem;
  padding: 2rem;
  box-shadow: 0 0.8rem 2.4rem rgba(15, 23, 42, 0.04);
}

.reports-page.is-dark .reports-panel {
  background: #252838;
  border-color: rgba(255, 255, 255, 0.08);
  box-shadow: 0 1rem 3rem rgba(0, 0, 0, 0.32);
}

.reports-panel-head {
  display: flex;
  justify-content: space-between;
  gap: 1.4rem;
  margin-bottom: 1.6rem;
}

.reports-panel-head h2 {
  margin: 0;
  color: #171717;
  font-size: 1.6rem;
  font-weight: 700;
}

.reports-page.is-dark .reports-panel-head h2 { color: #f1f5f9; }

.reports-panel-head span {
  display: grid;
  place-items: center;
  min-width: 3.6rem;
  height: 3rem;
  padding: 0 0.9rem;
  border-radius: 999px;
  background: #eef4ff;
  color: #2563eb;
  font-size: 1.25rem;
  font-weight: 750;
}

.reports-page.is-dark .reports-panel-head span {
  background: rgba(74, 122, 255, 0.16);
  color: #6f9bff;
}

.reports-list { display: grid; gap: 1rem; }

.report-queue-card {
  display: grid;
  justify-items: start;
  gap: 0.5rem;
  text-align: left;
  padding: 1.3rem 1.4rem;
  border-radius: 1.5rem;
  background: #f8fafc;
  border: 1px solid #eef1f6;
  transition: border-color 0.15s, background 0.15s, box-shadow 0.15s;
}

.report-queue-card:hover {
  border-color: rgba(37, 99, 235, 0.4);
  background: #fff;
  box-shadow: 0 0.6rem 1.8rem rgba(37, 99, 235, 0.08);
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
  background: #fef5f5;
  border-color: rgba(226, 75, 74, 0.22);
}

.reports-page.is-dark .report-queue-card--detector {
  background: rgba(226, 75, 74, 0.1);
  border-color: rgba(226, 75, 74, 0.32);
}

.report-queue-card__top {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  width: 100%;
}

.report-queue-card__check {
  margin-left: auto;
  color: #2563eb;
  font-size: 1.2rem;
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
  font-size: 1.35rem;
  font-weight: 650;
}

.reports-page.is-dark .report-queue-card strong { color: #f1f5f9; }

.report-queue-card small,
.report-queue-card em {
  color: #8a93a3;
  font-style: normal;
  font-size: 1.2rem;
}

.reports-page.is-dark .report-queue-card small { color: rgba(255, 255, 255, 0.45); }

.report-queue-card--detector em { color: #c23a3a; }
.reports-page.is-dark .report-queue-card--detector em { color: #ff8a87; }

.report-status,
.history-status {
  display: inline-flex;
  align-items: center;
  min-height: 2.2rem;
  padding: 0 0.9rem;
  border-radius: 999px;
  font-size: 1.1rem;
  font-weight: 700;
}

.report-status--detector { background: #fceaea; color: #c23a3a; }
.report-status--auto { background: #eaf0fe; color: #1e4fc0; }
.report-status--manual { background: #e6f6ed; color: #188a4c; }
.reports-page.is-dark .report-status--detector { background: rgba(226, 75, 74, 0.18); color: #ff8a87; }
.reports-page.is-dark .report-status--auto { background: rgba(74, 122, 255, 0.18); color: #6f9bff; }
.reports-page.is-dark .report-status--manual { background: rgba(24, 138, 76, 0.2); color: #6cd39a; }

.reports-table { display: grid; gap: 0.7rem; }

.reports-table-row {
  display: grid;
  grid-template-columns: 11rem minmax(14rem, 1fr) 10rem 7.5rem 11rem;
  gap: 1.2rem;
  align-items: center;
  min-height: 4.4rem;
  padding: 0 1.2rem;
  border-radius: 1.2rem;
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
  font-size: 1.05rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  min-height: 0;
}

.reports-page.is-dark .reports-table-row--head { color: rgba(255, 255, 255, 0.4); background: transparent; }

.history-date { color: #5c6b84; font-size: 1.2rem; }
.history-scope { font-size: 1.3rem; color: #171717; }
.history-approver { color: #5c6b84; font-size: 1.2rem; }
.reports-page.is-dark .history-date,
.reports-page.is-dark .history-approver { color: rgba(255, 255, 255, 0.5); }
.reports-page.is-dark .history-scope { color: #e6ebf3; }

.history-channels { display: inline-flex; align-items: center; gap: 0.4rem; }

.history-channel-ic {
  width: 1.7rem;
  height: 1.7rem;
  border-radius: 0.5rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.95rem;
  font-weight: 700;
  color: #fff;
}

.history-channel-ic.tg { background: #2aa5e0; }
.history-channel-ic.mx { background: #6c5ce7; }
.history-channel-ic.em { background: #8896ac; }
.history-channel-ic.failed { opacity: 0.35; }

.history-channels-empty { color: #c0c8d6; }

.history-status-cell { display: inline-flex; align-items: center; gap: 0.6rem; }

.history-status.sent { background: #e6f6ed; color: #188a4c; }
.history-status.failed { background: #fceaea; color: #c23a3a; }
.reports-page.is-dark .history-status.sent { background: rgba(24, 138, 76, 0.2); color: #6cd39a; }
.reports-page.is-dark .history-status.failed { background: rgba(226, 75, 74, 0.18); color: #ff8a87; }

.history-retry {
  width: 2.4rem;
  height: 2.4rem;
  border-radius: 0.8rem;
  border: 1px solid rgba(226, 75, 74, 0.3);
  background: #fff;
  color: #e11d48;
  font-size: 1.3rem;
  line-height: 1;
  flex-shrink: 0;
}

.history-retry:disabled { opacity: 0.5; }

.reports-page.is-dark .history-retry {
  background: rgba(226, 75, 74, 0.12);
  border-color: rgba(226, 75, 74, 0.3);
  color: #ff8a87;
}

.reports-empty {
  padding: 2rem;
  border-radius: 1.5rem;
  background: #f8fafc;
  color: #94a3b8;
  font-size: 1.25rem;
}

.reports-page.is-dark .reports-empty {
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.4);
}

@media (max-width: 960px) {
  .reports-layout { grid-template-columns: 1fr; }
  .reports-table-row {
    grid-template-columns: 1fr;
    gap: 0.5rem;
    padding: 1.2rem;
    min-height: 0;
  }
  .reports-table-row--head { display: none; }
}
</style>
