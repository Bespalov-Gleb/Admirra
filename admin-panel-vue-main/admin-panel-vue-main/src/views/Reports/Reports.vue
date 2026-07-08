<template>
  <main class="reports-page">
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
            @click="activeDelivery = item"
          >
            <span class="report-status" :class="`report-status--${item.source}`">
              {{ item.source === 'detector' ? 'Детектор' : item.source === 'auto' ? 'Авто' : 'Вручную' }}
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
            <span>Статус</span>
            <span>Скоуп</span>
            <span>Период</span>
            <span>Отправлен</span>
          </div>
          <div v-for="item in history" :key="item.id" class="reports-table-row">
            <span :class="['history-status', item.status]">{{ item.status === 'sent' ? 'Отправлен' : 'Ошибка' }}</span>
            <span>{{ item.scope_label }}</span>
            <span>{{ formatDate(item.start_date) }} — {{ formatDate(item.end_date) }}</span>
            <span>{{ formatDateTime(item.sent_at || item.approved_at || item.created_at) }}</span>
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
import ReportApprovalModal from '../GeneralStats3/components/ReportApprovalModal.vue'

const toaster = useToaster()
const loading = ref(false)
const pending = ref([])
const history = ref([])
const activeDelivery = ref(null)

const load = async () => {
  loading.value = true
  try {
    const [pendingResp, historyResp] = await Promise.all([
      api.get('reports/deliveries', { params: { status: 'pending' } }),
      api.get('reports/deliveries', { params: { status: 'history' } }),
    ])
    pending.value = Array.isArray(pendingResp.data) ? pendingResp.data : []
    history.value = Array.isArray(historyResp.data) ? historyResp.data : []
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Не удалось загрузить отчёты')
  } finally {
    loading.value = false
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
  width: min(1180px, calc(100% - 48px));
  margin: 0 auto;
  padding: 5rem 0 3rem;
  font-family: Inter, system-ui, sans-serif;
}

.reports-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 24px;
  margin-bottom: 26px;
}

.reports-head h1 {
  margin: 0;
  color: #172033;
  font-size: 2rem;
  font-weight: 860;
}

.reports-head p,
.reports-panel-head p {
  margin: 6px 0 0;
  color: #9aa3b2;
}

.reports-refresh {
  min-height: 46px;
  border-radius: 15px;
  padding: 0 20px;
  background: #fff;
  border: 1px solid rgba(148, 163, 184, 0.28);
  color: #2563eb;
  font-weight: 780;
}

.reports-layout {
  display: grid;
  grid-template-columns: minmax(340px, 0.8fr) minmax(0, 1.2fr);
  gap: 20px;
}

.reports-panel {
  background: #fff;
  border: 1px solid #edf0f5;
  border-radius: 24px;
  padding: 22px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.035);
}

.reports-panel-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.reports-panel-head h2 {
  margin: 0;
  color: #172033;
  font-size: 1.18rem;
  font-weight: 840;
}

.reports-panel-head span {
  display: grid;
  place-items: center;
  min-width: 42px;
  height: 34px;
  border-radius: 999px;
  background: #eef4ff;
  color: #2563eb;
  font-weight: 850;
}

.reports-list {
  display: grid;
  gap: 12px;
}

.report-queue-card {
  display: grid;
  justify-items: start;
  gap: 5px;
  text-align: left;
  padding: 15px;
  border-radius: 18px;
  background: #f8fafc;
  border: 1px solid rgba(148, 163, 184, 0.16);
}

.report-queue-card strong {
  color: #172033;
}

.report-queue-card small,
.report-queue-card em {
  color: #8a93a3;
  font-style: normal;
}

.report-status,
.history-status {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 9px;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 780;
}

.report-status--detector {
  background: #fff1f2;
  color: #e11d48;
}

.report-status--auto {
  background: #eff6ff;
  color: #2563eb;
}

.report-status--manual {
  background: #ecfdf5;
  color: #059669;
}

.reports-table {
  display: grid;
  gap: 8px;
}

.reports-table-row {
  display: grid;
  grid-template-columns: 110px minmax(140px, 1fr) 180px 120px;
  gap: 12px;
  align-items: center;
  min-height: 48px;
  padding: 0 12px;
  border-radius: 14px;
  background: #f8fafc;
  color: #4b5563;
}

.reports-table-row--head {
  background: transparent;
  color: #9aa3b2;
  font-size: 0.8rem;
  font-weight: 780;
}

.history-status.sent {
  background: #ecfdf5;
  color: #059669;
}

.history-status.failed {
  background: #fff1f2;
  color: #e11d48;
}

.reports-empty {
  padding: 22px;
  border-radius: 18px;
  background: #f8fafc;
  color: #94a3b8;
}

@media (max-width: 960px) {
  .reports-layout {
    grid-template-columns: 1fr;
  }
  .reports-table-row {
    grid-template-columns: 1fr;
    padding: 12px;
  }
}
</style>
