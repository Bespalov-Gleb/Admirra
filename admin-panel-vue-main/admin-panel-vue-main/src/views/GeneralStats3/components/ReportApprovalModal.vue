<template>
  <Teleport to="body">
    <div class="report-approval-backdrop" @click.self="$emit('close')">
      <section class="report-approval-modal">
        <header class="report-approval-head">
          <div>
            <p class="report-approval-kicker">Предпросмотр отчёта</p>
            <h3>{{ delivery?.scope_label || 'Отчёт' }}</h3>
            <span>{{ formatDate(delivery?.start_date) }} — {{ formatDate(delivery?.end_date) }}</span>
          </div>
          <button type="button" class="report-approval-close" @click="$emit('close')">×</button>
        </header>

        <div v-if="delivery?.anomaly_reason" class="report-approval-alert">
          {{ delivery.anomaly_reason }}
        </div>

        <div class="report-approval-grid">
          <div class="report-approval-card">
            <span>Каналы доставки</span>
            <strong>{{ channelLabel }}</strong>
          </div>
          <div class="report-approval-card">
            <span>Рекламный канал</span>
            <strong>{{ platformLabel(delivery?.platform) }}</strong>
          </div>
          <div class="report-approval-card">
            <span>Формат</span>
            <strong>{{ delivery?.report_format === 'mobile' ? 'Мобильный' : 'Десктоп' }}</strong>
          </div>
        </div>

        <label class="report-approval-comment">
          <span>AI-комментарий перед отправкой</span>
          <textarea v-model="comment" rows="8" placeholder="Комментарий будет добавлен в отчёт"></textarea>
        </label>

        <footer class="report-approval-actions">
          <button type="button" class="report-approval-secondary" @click="$emit('close')">Отмена</button>
          <button type="button" class="report-approval-primary" :disabled="sending" @click="approve">
            {{ sending ? 'Отправляем...' : 'Подтвердить и отправить' }}
          </button>
        </footer>
      </section>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import api from '@/api/axios'
import { useToaster } from '@/composables/useToaster'

const props = defineProps({
  delivery: { type: Object, default: null },
})

const emit = defineEmits(['close', 'sent'])
const toaster = useToaster()
const comment = ref('')
const sending = ref(false)

watch(() => props.delivery, (value) => {
  comment.value = value?.comment || ''
}, { immediate: true })

const channelNames = {
  telegram: 'Telegram',
  max: 'MAX',
  email: 'Email',
}

const channelLabel = computed(() => {
  const channels = Array.isArray(props.delivery?.channels) ? props.delivery.channels : []
  const targets = Array.isArray(props.delivery?.chat_targets) ? props.delivery.chat_targets : []
  const labels = channels.map((item) => channelNames[item] || item)
  if (targets.length) labels.push(`${targets.length} групп.`)
  return labels.length ? labels.join(', ') : 'Не выбраны'
})

const formatDate = (value) => {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString('ru-RU')
}

const platformLabel = (value) => ({
  all: 'Все каналы',
  yandex: 'Яндекс Директ',
  vk: 'VK Реклама',
  avito: 'Avito Ads',
}[value || 'all'] || value)

const approve = async () => {
  if (!props.delivery?.id || sending.value) return
  sending.value = true
  try {
    const { data } = await api.post(`reports/deliveries/${props.delivery.id}/approve`, {
      comment: comment.value,
    })
    if (data?.status === 'sent') {
      toaster.success('Отчёт отправлен')
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
.report-approval-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(15, 23, 42, 0.34);
  backdrop-filter: blur(10px);
}

.report-approval-modal {
  width: min(760px, 100%);
  max-height: min(860px, calc(100vh - 48px));
  overflow: auto;
  border-radius: 24px;
  background: #fff;
  border: 1px solid rgba(148, 163, 184, 0.22);
  box-shadow: 0 28px 80px rgba(15, 23, 42, 0.2);
  padding: 26px;
}

.report-approval-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 18px;
}

.report-approval-kicker {
  margin: 0 0 4px;
  color: #2563eb;
  font-size: 0.82rem;
  font-weight: 700;
}

.report-approval-head h3 {
  margin: 0;
  color: #172033;
  font-size: 1.35rem;
  font-weight: 800;
}

.report-approval-head span {
  display: block;
  margin-top: 6px;
  color: #8a93a3;
  font-size: 0.92rem;
}

.report-approval-close {
  width: 36px;
  height: 36px;
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-radius: 12px;
  background: #fff;
  color: #64748b;
  font-size: 24px;
  line-height: 1;
}

.report-approval-alert {
  margin-bottom: 16px;
  padding: 13px 15px;
  border-radius: 16px;
  background: #fff7ed;
  border: 1px solid #fed7aa;
  color: #9a3412;
  font-weight: 650;
}

.report-approval-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 18px;
}

.report-approval-card {
  padding: 14px;
  border-radius: 18px;
  background: #f7f9fc;
  border: 1px solid rgba(148, 163, 184, 0.12);
}

.report-approval-card span,
.report-approval-comment span {
  display: block;
  color: #8a93a3;
  font-size: 0.82rem;
  font-weight: 700;
  margin-bottom: 5px;
}

.report-approval-card strong {
  color: #172033;
  font-size: 0.98rem;
}

.report-approval-comment textarea {
  width: 100%;
  resize: vertical;
  min-height: 170px;
  border: 1px solid rgba(148, 163, 184, 0.25);
  border-radius: 18px;
  padding: 15px;
  color: #172033;
  background: #fff;
  outline: none;
}

.report-approval-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
}

.report-approval-secondary,
.report-approval-primary {
  min-height: 46px;
  border-radius: 14px;
  padding: 0 20px;
  font-weight: 750;
}

.report-approval-secondary {
  background: #fff;
  border: 1px solid rgba(148, 163, 184, 0.28);
  color: #64748b;
}

.report-approval-primary {
  background: linear-gradient(135deg, #2563eb, #10b8c9);
  color: #fff;
}

.report-approval-primary:disabled {
  opacity: 0.65;
}

@media (max-width: 720px) {
  .report-approval-grid {
    grid-template-columns: 1fr;
  }
}
</style>
