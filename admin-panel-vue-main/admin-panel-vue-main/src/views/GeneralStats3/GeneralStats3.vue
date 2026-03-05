<template>
  <div class="space-y-6 overflow-x-hidden w-full">
    <!-- Сообщение при синхронизации: данные скрыты -->
    <div v-if="dataHiddenBySync" class="flex items-center justify-center min-h-[50vh] px-4">
      <div class="max-w-md w-full text-center py-12 px-8 bg-white/80 backdrop-blur-sm rounded-3xl border border-gray-100 shadow-lg">
        <div class="w-14 h-14 mx-auto mb-4 rounded-2xl bg-blue-50 flex items-center justify-center">
          <svg class="w-7 h-7 text-blue-500 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        </div>
        <h3 class="text-base font-bold text-gray-800 mb-2">Идёт синхронизация</h3>
        <p class="text-sm text-gray-500">Данные обновляются. Статистика появится через несколько минут.</p>
      </div>
    </div>

    <!-- Основной контент -->
    <div v-else class="space-y-6">
      <div v-if="statsError" class="p-4 bg-red-50 border border-red-200 text-red-600 rounded-xl text-sm font-medium">
        {{ statsError }}
      </div>

      <!-- Шапка: заголовок + фильтры -->
      <div class="flex flex-col gap-4 mb-6">
        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <StatsHeader
            :label="headerLabel"
            :title="dashboardTitle"
            :subtitle="dynamicSubtitle"
            :show-reset="filters.campaign_ids && filters.campaign_ids.length > 0"
            @reset="filters.campaign_ids = []"
          />
          <div class="flex flex-wrap items-center gap-3 min-h-[36px]">
            <StatsFilters
              :filters="filters"
              :clients="clients"
              :all-campaigns="allCampaigns"
              :loading-campaigns="loadingCampaigns"
              :vk-goal-actions="vkGoalActions"
              :loading-vk-goal-actions="loadingVkGoalActions"
              @period-change="handlePeriodChange"
              @date-change="handleDateChange"
              @export="handleExport"
              @update:campaign-ids="(ids) => filters.campaign_ids = ids"
              @update:goal-action-ids="(ids) => filters.vk_goal_action_ids = ids"
            />
            <label class="inline-flex items-center gap-2 text-xs font-medium text-gray-600 select-none h-9">
              <input v-model="includeVat" type="checkbox" class="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500" />
              <span>Учитывать НДС</span>
            </label>
          </div>
        </div>
      </div>

      <!-- График + сайдбар бок о бок (по макету) -->
      <div class="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <!-- График слева (2/3) -->
        <div class="xl:col-span-2 relative">
          <div v-if="loading" class="absolute inset-0 bg-white/50 backdrop-blur-[1px] z-10 flex items-center justify-center rounded-2xl">
            <div class="flex flex-col items-center gap-2">
              <div class="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
              <span class="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Обновление...</span>
            </div>
          </div>
          <StatisticsChart
            :dynamics="dynamics"
            :selected-metrics="selectedMetrics"
            :period="filters.period"
            @update:period="(p) => { filters.period = p; handlePeriodChange(); }"
          />
        </div>
        <!-- Сайдбар справа (1/3) -->
        <div class="xl:col-span-1 space-y-4">
          <ConnectedChannelsV3
            :integrations="integrations"
            @connect="() => $router.push('/integrations/wizard')"
          />
          <ReportSendingBlock
            :sending-tg="sendingTg"
            :sending-email="sendingEmail"
            :saving="reportSaving"
            :telegram-configured="!!userReportSettings.telegram_chat_id"
            :email-configured="(userReportSettings.email_recipients?.length ?? 0) > 0"
            @send-telegram="handleSendTelegram"
            @send-email="handleSendEmail"
            @save="handleReportSave"
            @schedule-change="handleScheduleChange"
          />
        </div>
      </div>

      <!-- KPI карточки (внизу по макету) -->
      <div class="w-full">
        <div v-if="loading && !summary.expenses" class="grid grid-cols-2 md:grid-cols-3 gap-4">
          <Skeleton v-for="i in 6" :key="i" class="h-28 rounded-2xl" />
        </div>
        <KPIOverview
          v-else-if="summary && summary.expenses !== undefined"
          :summary="summary"
          :selected-metrics="selectedMetrics"
          :loading="loading"
          :include-vat="includeVat"
          @toggle-metric="toggleMetric"
        />
      </div>

      <!-- Основной контент: цели, эффективность, кампании, посты, активность -->
      <div class="space-y-6">
          <!-- Статистика по ключевым целям (3 колонки по макету) -->
          <KeyGoalsStatsV3
            v-if="filters.client_id"
            :client-id="filters.client_id"
            :start-date="filters.start_date"
            :end-date="filters.end_date"
            :total-leads="summary?.leads"
          />

          <!-- Лучшие рекламные кампании (таблица) -->
          <CampaignTableV3
            :campaigns="campaigns"
            :loading="loading"
          />

          <!-- Лучшие посты -->
          <BestPosts
            :client-id="filters.client_id || ''"
            :start-date="filters.start_date"
            :end-date="filters.end_date"
            :platform="filters.channel"
            :campaign-ids="filters.campaign_ids || []"
            :goal-action-ids="filters.vk_goal_action_ids || []"
          />

          <!-- Активность по дням + Возраст аудитории -->
          <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div class="lg:col-span-2">
              <ActivityByWeekday
                :client-id="filters.client_id || ''"
                :start-date="filters.start_date"
                :end-date="filters.end_date"
                :platform="filters.channel"
                :campaign-ids="filters.campaign_ids || []"
                :goal-action-ids="filters.vk_goal_action_ids || []"
              />
            </div>
            <div>
              <AudienceAge
                :client-id="filters.client_id || ''"
                :start-date="filters.start_date"
                :end-date="filters.end_date"
              />
            </div>
          </div>

          <!-- Комментарий к отчёту -->
          <ReportCommentBlock
            :comment="reportComment"
            :loading="reportLoading"
            :error="reportError"
            :sending-pdf="sendingPdf"
            :sending-tg="sendingTg"
            :sending-email="sendingEmail"
            @download-pdf="handleDownloadPdf"
            @send-telegram="handleSendTelegram"
            @send-email="handleSendEmail"
          />
      </div>

    <!-- Модальное окно Telegram -->
    <Teleport to="body">
      <div v-if="showTgModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" @click.self="showTgModal = false">
        <div class="bg-white rounded-2xl p-6 max-w-md w-full mx-4 shadow-xl">
          <h3 class="text-lg font-semibold text-gray-900 mb-3">Отправить в Telegram</h3>
          <p class="text-sm text-gray-500 mb-4">Введите Chat ID получателя (например, -1001234567890)</p>
          <input
            v-model="tgChatId"
            type="text"
            placeholder="Chat ID"
            class="w-full px-4 py-3 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-violet-500 focus:border-violet-500 mb-4"
          />
          <div class="flex justify-end gap-2">
            <button class="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-xl" @click="showTgModal = false">Отмена</button>
            <button
              class="px-4 py-2 bg-violet-600 text-white rounded-xl hover:bg-violet-700 disabled:opacity-50"
              :disabled="sendingTg"
              @click="submitTelegram"
            >
              {{ sendingTg ? 'Отправка...' : 'Отправить' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Модальное окно Email -->
    <Teleport to="body">
      <div v-if="showEmailModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" @click.self="showEmailModal = false">
        <div class="bg-white rounded-2xl p-6 max-w-md w-full mx-4 shadow-xl">
          <h3 class="text-lg font-semibold text-gray-900 mb-3">Отправить на Email</h3>
          <p class="text-sm text-gray-500 mb-4">Введите email получателей через запятую</p>
          <input
            v-model="emailRecipients"
            type="text"
            placeholder="email1@example.com, email2@example.com"
            class="w-full px-4 py-3 border border-gray-300 rounded-xl text-sm focus:ring-2 focus:ring-violet-500 focus:border-violet-500 mb-4"
          />
          <div class="flex justify-end gap-2">
            <button class="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-xl" @click="showEmailModal = false">Отмена</button>
            <button
              class="px-4 py-2 bg-violet-600 text-white rounded-xl hover:bg-violet-700 disabled:opacity-50"
              :disabled="sendingEmail"
              @click="submitEmail"
            >
              {{ sendingEmail ? 'Отправка...' : 'Отправить' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

  </div>
</div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ArrowPathIcon } from '@heroicons/vue/24/solid'
// Components
import StatisticsChart from './components/StatisticsChart.vue'
import KeyGoalsStatsV3 from './components/KeyGoalsStatsV3.vue'
import CampaignTableV3 from './components/CampaignTableV3.vue'
import KPIOverview from './components/KPIOverview.vue'
import StatsFilters from './components/StatsFilters.vue'
import StatsHeader from './components/StatsHeader.vue'
import BestPosts from './components/BestPosts.vue'
import ActivityByWeekday from './components/ActivityByWeekday.vue'
import AudienceAge from './components/AudienceAge.vue'
import ReportCommentBlock from './components/ReportCommentBlock.vue'
import ConnectedChannelsV3 from './components/ConnectedChannelsV3.vue'
import ReportSendingBlock from './components/ReportSendingBlock.vue'
import Skeleton from '../../components/ui/Skeleton.vue'

// Logic
import { useDashboardStats } from '../../composables/useDashboardStats'
import { useSyncStatus } from '../../composables/useSyncStatus'
import { useRoute, useRouter } from 'vue-router'
import { useToaster } from '../../composables/useToaster'
import { useProjects } from '../../composables/useProjects'
import api from '../../api/axios'

const { isSyncingForProject } = useSyncStatus()

const {
  summary,
  dynamics,
  clients,
  allCampaigns,
  loading,
  error: statsError,
  filters,
  handlePeriodChange,
  fetchStats,
  loadingCampaigns,
  vkGoalActions,
  loadingVkGoalActions
} = useDashboardStats()

const dataHiddenBySync = computed(() => isSyncingForProject(filters.client_id || null))

const { currentProjectId, setCurrentProject } = useProjects()
const toaster = useToaster()
const route = useRoute()
const router = useRouter()

const includeVat = ref(true)
const integrations = ref([])

// Fetch integrations for selected client (dashboard endpoint — без чувствительных данных)
const fetchIntegrations = async () => {
  try {
    const params = filters.client_id ? { client_id: filters.client_id } : {}
    const { data } = await api.get('dashboard/integrations', { params })
    integrations.value = data || []
  } catch {
    integrations.value = []
  }
}

watch(() => filters.client_id, fetchIntegrations, { immediate: true })

// Auto-sync stats when VAT checkbox changes
watch(includeVat, () => {
  // Reuse existing fetch logic so both KPI и графики обновляются
  fetchStats()
})

// --- Project Synchronization ---

// Sync Global -> Local
watch(currentProjectId, (newId) => {
  if (filters.client_id !== newId) {
    filters.client_id = newId
  }
}, { immediate: true })

// Sync Local -> Global
watch(() => filters.client_id, (newId) => {
  if (currentProjectId.value !== newId) {
    setCurrentProject(newId)
  }
})

// --- State & UI Logic ---

const selectedMetrics = ref([]) // Array of selected metrics

const toggleMetric = (metric) => {
  const index = selectedMetrics.value.indexOf(metric)
  if (index > -1) {
    // Remove if already selected
    selectedMetrics.value.splice(index, 1)
  } else {
    // Add if not selected
    selectedMetrics.value.push(metric)
  }
}

const headerLabel = computed(() => 'Общая аналитика по всем активным проектам')

const dynamicSubtitle = computed(() => {
  if (filters.campaign_ids?.length > 0) return 'Детальная статистика выбранной кампании'
  if (filters.client_id) return 'Аналитика и показатели эффективности проекта'
  if (filters.channel !== 'all') return 'Статистика по конкретному рекламному каналу'
  return 'Общая аналитика по всем активным проектам'
})

const dashboardTitle = computed(() => {
  if (filters.campaign_ids?.length > 0) {
    const campaignId = filters.campaign_ids[0]
    const campaign = allCampaigns.value.find(c => c.id === campaignId)
    return campaign ? `Отчет по кампании: ${campaign.name}` : `Отчет по кампаниям (${filters.campaign_ids.length})`
  }
  if (filters.client_id) {
    const client = clients.value.find(c => c.id === filters.client_id)
    return client ? `Отчет по проекту: ${client.name}` : 'Отчет по проекту'
  }
  if (filters.channel !== 'all') {
    const channelMap = { yandex: 'Яндекс.Директ', vk: 'VK Ads' }
    return `Отчет: ${channelMap[filters.channel] || filters.channel}`
  }
  return 'Отчет по всем проектам'
})

// --- Handlers ---

const handleDateChange = () => {
  // When custom dates are changed, fetch stats
  fetchStats()
}

const handleExport = async () => {
  try {
    const params = {
      start_date: filters.start_date,
      end_date: filters.end_date,
      platform: filters.channel,
      client_id: filters.client_id || undefined,
      campaign_ids: filters.campaign_ids.length > 0 ? filters.campaign_ids : undefined,
      goal_action_ids: (filters.channel === 'vk' && filters.vk_goal_action_ids.length > 0)
        ? filters.vk_goal_action_ids
        : undefined
    }

    const response = await api.get('dashboard/export/csv', {
      params,
      responseType: 'blob'
    })
    
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `report_${filters.start_date}_${filters.end_date}.csv`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    
    toaster.success('Отчет успешно сформирован')
  } catch (err) {
    console.error('Export error:', err)
    toaster.error('Не удалось скачать отчет')
  }
}

// --- Report Comment Block ---
const reportComment = ref('')
const reportLoading = ref(false)
const reportError = ref('')
const sendingPdf = ref(false)
const sendingTg = ref(false)
const sendingEmail = ref(false)

const handleDownloadPdf = async () => {
  sendingPdf.value = true
  try {
    const params = {
      start_date: filters.start_date,
      end_date: filters.end_date,
      client_id: filters.client_id || undefined
    }
    const response = await api.get('reports/pdf', { params, responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `report_${filters.start_date}_${filters.end_date}.pdf`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    toaster.success('PDF отчёт скачан')
  } catch (err) {
    toaster.error('Не удалось скачать PDF')
  } finally {
    sendingPdf.value = false
  }
}

const showTgModal = ref(false)
const showEmailModal = ref(false)
const tgChatId = ref('')
const emailRecipients = ref('')

const userReportSettings = ref({ telegram_chat_id: '', email_recipients: [] })

onMounted(async () => {
  try {
    const { data } = await api.get('/auth/me')
    userReportSettings.value.telegram_chat_id = data.report_telegram_chat_id || ''
    userReportSettings.value.email_recipients = data.report_email_recipients || []
  } catch {
    // ignore
  }
})

const handleSendTelegram = () => {
  tgChatId.value = userReportSettings.value.telegram_chat_id
  showTgModal.value = true
}

const handleSendEmail = () => {
  emailRecipients.value = userReportSettings.value.email_recipients.join(', ')
  showEmailModal.value = true
}

const reportSaving = ref(false)
const handleReportSave = async (schedule) => {
  reportSaving.value = true
  try {
    await api.patch('/auth/me', { report_schedule: schedule })
    toaster.success('Расписание сохранено')
  } catch {
    toaster.error('Не удалось сохранить расписание')
  } finally {
    reportSaving.value = false
  }
}
const handleScheduleChange = () => { /* опционально: предпросмотр */ }

const submitTelegram = async () => {
  const chatId = tgChatId.value.trim()
  if (!chatId) {
    toaster.error('Введите Chat ID')
    return
  }
  sendingTg.value = true
  try {
    await api.post('reports/send', {
      report_type: 'pdf',
      channels: ['telegram'],
      telegram_chat_id: chatId,
      client_id: filters.client_id || null,
      start_date: filters.start_date,
      end_date: filters.end_date
    })
    toaster.success('Отчёт отправлен в Telegram')
    showTgModal.value = false
    tgChatId.value = ''
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Ошибка отправки')
  } finally {
    sendingTg.value = false
  }
}

const submitEmail = async () => {
  const emails = emailRecipients.value.split(/[,;\s]+/).map(e => e.trim()).filter(Boolean)
  if (!emails.length) {
    toaster.error('Введите хотя бы один email')
    return
  }
  sendingEmail.value = true
  try {
    await api.post('reports/send', {
      report_type: 'pdf',
      channels: ['email'],
      email_recipients: emails,
      client_id: filters.client_id || null,
      start_date: filters.start_date,
      end_date: filters.end_date
    })
    toaster.success('Отчёт отправлен на email')
    showEmailModal.value = false
    emailRecipients.value = ''
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Ошибка отправки')
  } finally {
    sendingEmail.value = false
  }
}

// React to post-callback redirect (integrations)
watch(() => route.query.new_integration_id, (id) => {
  if (id) {
    router.push({
      path: '/integrations/wizard',
      query: {
        resume_integration_id: id,
        initial_step: 2
      }
    })
    window.history.replaceState({}, '', window.location.pathname)
  }
}, { immediate: true })

</script>
