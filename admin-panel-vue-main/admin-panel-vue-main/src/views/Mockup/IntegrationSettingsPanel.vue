<template>
    <!-- Panel -->
    <div class="ip-panel" ref="panelEl">

      <!-- Content area -->
      <div class="ip-scroll">

        <!-- ── Header ── -->
        <div class="ip-header">
          <div class="flex flex-wrap items-center gap-[0.6944rem] mb-[0.6944rem]">
            <h2 class="ip-title">Настроить цели</h2>
            <div class="ip-sync-chip">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.6"/>
                <path d="M12 7v5.5l3 2" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              Последняя синхронизация: {{ formattedSync }}
            </div>
          </div>
          <p class="ip-subtitle">
            Авторизация и кабинет уже подключены — повторно входить в Яндекс не нужно, меняется только состав целей.
          </p>
        </div>

        <!-- ── Context block ── -->
        <div class="ip-context">
          <div class="ip-context__head">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
              <rect x="3" y="9" width="18" height="13" rx="2" stroke="currentColor" stroke-width="1.6"/>
              <path d="M7 9V7a5 5 0 0110 0v2" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
            </svg>
            Контекст — здесь не меняется
          </div>
          <div class="ip-context__cols">
            <div class="ip-ctx-col">
              <span class="ip-ctx-label">Канал:</span>
              <span class="ip-ctx-val">{{ channelName }}</span>
            </div>
            <div class="ip-ctx-sep" />
            <div class="ip-ctx-col">
              <span class="ip-ctx-label">Проект:</span>
              <span class="ip-ctx-val">{{ projectName }}</span>
            </div>
            <div class="ip-ctx-sep" />
            <div class="ip-ctx-col">
              <span class="ip-ctx-label">Кабинет:</span>
              <span class="ip-ctx-val">{{ cabinetName }}</span>
            </div>
          </div>
        </div>

        <!-- ── New goal notice (only when new goals exist) ── -->
        <div v-if="hasNewGoals" class="ip-notice">
          В Метрике появилась новая цель, ещё не отслеживается. Отметьте, если нужна.
        </div>

        <!-- ── Counter + Goals block ── -->
        <div class="ip-main">

          <!-- Counter row -->
          <div class="ip-counter-row">
            <div>
              <h4 class="ip-section-title">Счётчик метрики</h4>
              <p class="ip-section-sub">{{ counterDomain }} • ID {{ counterId }}</p>
            </div>
            <div v-if="counters.length > 1" class="ip-counter-list" aria-label="Выбор счётчиков">
              <button
                v-for="counter in counters"
                :key="counter.id"
                type="button"
                class="ip-counter-chip"
                :class="{ 'ip-counter-chip--active': selectedCounterIds.includes(String(counter.id)) }"
                @click="toggleCounter(counter.id)"
              >
                {{ counter.site || counter.name || `ID ${counter.id}` }}
              </button>
            </div>
          </div>

          <div class="ip-hr" />

          <!-- Goals heading -->
          <h4 class="ip-section-title mb-[0.4167rem]">Цели и конверсии</h4>
          <p class="ip-goals-hint">
            <span class="ip-star-hint">★</span>
            Звезда — основная цель. Галочка — что отслеживать.
          </p>

          <!-- Goals list -->
          <div v-if="loadingGoals" class="ip-goals-loading">Загрузка целей…</div>
          <div v-else class="ip-goals">
            <div
              v-for="goal in goals"
              :key="goal.id"
              class="ip-goal"
              :class="{
                'ip-goal--checked': goal.state === 'checked',
                'ip-goal--new': goal.state === 'new',
                'ip-goal--error': goal.state === 'error',
                'ip-goal--selected': isGoalSelected(goal.id),
              }"
              @click="toggleGoal(goal.id)"
            >
              <!-- State icon (left) -->
              <button class="ip-goal__icon flex-shrink-0" type="button" @click.stop="toggleGoal(goal.id)">
                <!-- checked -->
                <svg v-if="isGoalSelected(goal.id)" width="22" height="22" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="9.5" stroke="#4b4535" stroke-width="1.5"/>
                  <path d="M7.5 12.5l3 3 6-6" stroke="#4b4535" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                <!-- new -->
                <svg v-else-if="goal.state === 'new'" width="22" height="22" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="9.5" stroke="#2563eb" stroke-width="1.5"/>
                </svg>
                <!-- error -->
                <svg v-else-if="goal.state === 'error'" width="22" height="22" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="9.5" stroke="#ef4444" stroke-width="1.5"/>
                  <path d="M12 7.5v5.5" stroke="#ef4444" stroke-width="1.8" stroke-linecap="round"/>
                  <circle cx="12" cy="16" r="1" fill="#ef4444"/>
                </svg>
              </button>

              <!-- Name + meta (center) -->
              <div class="ip-goal__info min-w-0">
                <span class="ip-goal__name">{{ goal.name }}</span>
                <span class="ip-goal__meta" v-if="goal.type"> · {{ goal.type }} · ID {{ goal.id }}</span>
                <span class="ip-goal__meta" v-else> · ID {{ goal.id }}</span>
              </div>

              <!-- Right: star / badge / error text -->
              <div class="ip-goal__right flex-shrink-0">
                <svg
                  v-if="isGoalSelected(goal.id)"
                  class="ip-goal-star"
                  :class="{ 'ip-goal-star--active': String(goal.id) === String(primaryGoalId) }"
                  @click.stop="selectPrimaryGoal(goal.id)"
                  width="18" height="18" viewBox="0 0 24 24"
                  :fill="String(goal.id) === String(primaryGoalId) ? '#8a7a54' : '#bfb08a'"
                >
                  <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                </svg>
                <span v-else-if="goal.state === 'new'" class="ip-new-badge">Новая</span>
                <span v-else-if="goal.state === 'error'" class="ip-error-text">не приходит из Метрики</span>
              </div>
            </div>
          </div>

          <!-- Warning note -->
          <div class="ip-warning">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" class="flex-shrink-0 mt-[0.1389rem]">
              <circle cx="12" cy="12" r="9.5" stroke="#9ca3af" stroke-width="1.5"/>
              <path d="M12 7.5v5.5" stroke="#9ca3af" stroke-width="1.8" stroke-linecap="round"/>
              <circle cx="12" cy="16" r="1" fill="#9ca3af"/>
            </svg>
            <span>Не отмечайте пересекающиеся цели: если одна уже включает другую, одно действие засчитается дважды и цифры будут выше реальных.</span>
          </div>

        </div>
      </div>

      <!-- ── Footer ── -->
      <div class="ip-footer">
        <button class="ip-delete-btn" @click="deleteConfirmOpen = true">Удалить интеграцию</button>
        <div class="flex items-center gap-[0.6944rem]">
          <button class="ip-cancel-btn" @click="$emit('close')">Отмена</button>
          <button class="ip-save-btn" :disabled="!canSave" @click="emitSave">Сохранить</button>
        </div>
      </div>

      <Teleport to="body">
        <div v-if="deleteConfirmOpen" class="ip-confirm-backdrop" @click.self="deleteConfirmOpen = false">
          <div class="ip-confirm">
            <h3>Удалить интеграцию?</h3>
            <p>
              История и данные канала будут обработаны по текущей серверной логике удаления.
              Для подтверждения введите название интеграции:
              <strong>{{ deleteConfirmPhrase }}</strong>
            </p>
            <input
              v-model="deleteConfirmText"
              class="ip-confirm-input"
              type="text"
              :placeholder="deleteConfirmPhrase"
              autocomplete="off"
            />
            <div class="ip-confirm-actions">
              <button type="button" class="ip-cancel-btn" @click="deleteConfirmOpen = false">Отмена</button>
              <button
                type="button"
                class="ip-delete-btn"
                :disabled="deleteConfirmText.trim() !== deleteConfirmPhrase"
                @click="$emit('delete')"
              >
                Удалить интеграцию
              </button>
            </div>
          </div>
        </div>
      </Teleport>

    </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import api from '../../api/axios'

const panelEl = ref(null)
const counters = ref([])
const goals = ref([])
const selectedGoalIds = ref([])
const primaryGoalId = ref('')
const selectedCounterIds = ref([])
const loadingGoals = ref(false)
const deleteConfirmOpen = ref(false)
const deleteConfirmText = ref('')

const props = defineProps({
  integration: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['close', 'save', 'delete'])

// ── Helpers ──────────────────────────────────────────────────────────────────

const parseJsonList = (raw) => {
  if (!raw) return []
  if (Array.isArray(raw)) return raw.map(String)
  try { return JSON.parse(raw) } catch { return [] }
}

// ── Context: channel / project / cabinet ─────────────────────────────────────

const platformLabels = {
  yandex: 'Yandex Direct', YANDEX: 'Yandex Direct', YANDEX_DIRECT: 'Yandex Direct',
  vk: 'ВК Ads', VK: 'ВК Ads', VK_ADS: 'ВК Ads',
  avito: 'Avito Ads', AVITO: 'Avito Ads', AVITO_ADS: 'Avito Ads',
  MYTARGET: 'MyTarget',
}

const channelName = computed(() => {
  const p = props.integration?.platform
  return platformLabels[p] || platformLabels[p?.toUpperCase()] || p || '—'
})

const projectName = computed(() =>
  props.integration?.client_name || props.integration?.client?.name || '—'
)

const cabinetName = computed(() => {
  const login = props.integration?.agency_client_login
  const name  = props.integration?.account_name
  const id    = props.integration?.account_id || props.integration?.external_account_id
  if (login && name && login !== name) return `${login} • ${name}`
  return name || login || id || '—'
})

// ── Sync chip ─────────────────────────────────────────────────────────────────

const formattedSync = computed(() => {
  if (!props.integration?.last_sync_at) return '—'
  return new Date(props.integration.last_sync_at).toLocaleString('ru-RU', {
    day: '2-digit', month: 'long', hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Moscow'
  })
})

// ── Counter (from fetched data) ───────────────────────────────────────────────

const counterDomain = computed(() => counters.value[0]?.site || '—')
const counterId = computed(() => selectedCounterIds.value.join(', ') || counters.value[0]?.id || '—')

// ── New-goal notice ───────────────────────────────────────────────────────────

const hasNewGoals = computed(() => goals.value.some(g => g.state === 'new'))
const canSave = computed(() => selectedGoalIds.value.length > 0 && Boolean(primaryGoalId.value))
const deleteConfirmPhrase = computed(() => channelName.value)

const isGoalSelected = (goalId) => selectedGoalIds.value.includes(String(goalId))

const toggleGoal = (goalId) => {
  const id = String(goalId)
  if (selectedGoalIds.value.includes(id)) {
    selectedGoalIds.value = selectedGoalIds.value.filter((item) => item !== id)
    if (String(primaryGoalId.value) === id) primaryGoalId.value = selectedGoalIds.value[0] || ''
  } else {
    selectedGoalIds.value = [...selectedGoalIds.value, id]
    if (!primaryGoalId.value) primaryGoalId.value = id
  }
}

const selectPrimaryGoal = (goalId) => {
  const id = String(goalId)
  if (!selectedGoalIds.value.includes(id)) selectedGoalIds.value = [...selectedGoalIds.value, id]
  primaryGoalId.value = id
}

const toggleCounter = (counterId) => {
  const id = String(counterId)
  if (selectedCounterIds.value.includes(id)) {
    selectedCounterIds.value = selectedCounterIds.value.filter((item) => item !== id)
  } else {
    selectedCounterIds.value = [...selectedCounterIds.value, id]
  }
  loadGoalsForSelectedCounters(props.integration?.id, props.integration?.account_id || null)
}

const emitSave = () => {
  emit('save', {
    selected_goals: selectedGoalIds.value,
    primary_goal_id: primaryGoalId.value,
    selected_counters: selectedCounterIds.value,
  })
}

const loadGoalsForSelectedCounters = async (integrationId, accountId) => {
  if (!integrationId) return
  const counterIds = selectedCounterIds.value.length ? selectedCounterIds.value : counters.value.map(c => c.id)
  const goalParams = {
    with_stats: false,
    ...(accountId && { account_id: accountId }),
    ...(counterIds.length && { counter_ids: counterIds.join(',') }),
  }
  const { data: gData } = await api.get(`integrations/${integrationId}/goals`, { params: goalParams })
  const apiGoals = Array.isArray(gData) ? gData : (gData?.goals ?? [])
  const apiGoalMap = new Map(apiGoals.map(g => [String(g.id), g]))
  const selSet = new Set(selectedGoalIds.value.map(String))

  const result = []

  for (const gid of selectedGoalIds.value) {
    const sid = String(gid)
    const ag = apiGoalMap.get(sid)
    result.push(ag
      ? { id: sid, name: ag.name, type: ag.type && ag.type !== 'Unknown' ? ag.type : null, state: 'checked' }
      : { id: sid, name: `Цель ID ${sid}`, type: null, state: 'error' }
    )
  }

  for (const ag of apiGoals) {
    if (!selSet.has(String(ag.id))) {
      result.push({ id: String(ag.id), name: ag.name, type: ag.type && ag.type !== 'Unknown' ? ag.type : null, state: 'new' })
    }
  }

  goals.value = result
}

// ── Data fetching ─────────────────────────────────────────────────────────────

const fetchData = async () => {
  const integrationId = props.integration?.id
  if (!integrationId) return

  // selected_goals comes as List[str] from the API (already parsed)
  const initialSelectedGoalIds = parseJsonList(props.integration?.selected_goals)
  const initialPrimaryGoalId = String(props.integration?.primary_goal_id || '')
  const initialCounterIds = parseJsonList(props.integration?.selected_counters)
  selectedGoalIds.value = initialSelectedGoalIds
  primaryGoalId.value = initialPrimaryGoalId || initialSelectedGoalIds[0] || ''
  selectedCounterIds.value = initialCounterIds
  // account_id is used to scope Metrika counters to the right profile
  const accountId = props.integration?.account_id || null

  loadingGoals.value = true
  try {
    // 1. Fetch counters scoped to the integration's account
    const counterParams = accountId ? { account_id: accountId } : {}
    const { data: cData } = await api.get(`integrations/${integrationId}/counters`, { params: counterParams })
    counters.value = cData?.counters || (Array.isArray(cData) ? cData : [])
    if (!selectedCounterIds.value.length) {
      selectedCounterIds.value = counters.value.map((counter) => String(counter.id)).filter(Boolean).slice(0, 1)
    }

    // 2. Fetch all available goals — pass account_id + selected counter IDs.
    await loadGoalsForSelectedCounters(integrationId, accountId)
  } catch (err) {
    console.error('[IntegrationSettingsPanel] fetch error:', err)
  } finally {
    loadingGoals.value = false
  }
}

onMounted(() => {
  panelEl.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  fetchData()
})
</script>

<style scoped>
/* ── Panel (inline, appears below cards) ── */
.ip-panel {
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 1.3889rem;
  box-shadow: 0 2px 24px rgba(0, 0, 0, 0.08);
  border: 1px solid #e9e9e9;
  animation: ip-fade-in 0.22s ease both;
}
:global(.dark) .ip-panel,
:global(.darkmode) .ip-panel {
  background: #1e2130;
  border-color: rgba(255, 255, 255, 0.1);
  box-shadow: 0 2px 24px rgba(0, 0, 0, 0.4);
}

@keyframes ip-fade-in {
  from { opacity: 0; transform: translateY(0.8333rem); }
  to   { opacity: 1; transform: translateY(0); }
}

/* ── Content area ── */
.ip-scroll {
  padding: 2.0833rem 2.0833rem 1.3889rem;
}

/* ── Header ── */
.ip-header {
  margin-bottom: 1.6667rem;
}
.ip-title {
  font-size: 1.6667rem;
  font-weight: 600;
  color: #171717;
  line-height: 1;
}
:global(.dark) .ip-title,
:global(.darkmode) .ip-title {
  color: #fff;
}
.ip-sync-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.3472rem;
  padding: 0.3472rem 0.8333rem;
  background: #fef9ec;
  border: 1px solid #f0d88a;
  border-radius: 2rem;
  font-size: 0.7639rem;
  color: #92740a;
  font-weight: 500;
  white-space: nowrap;
}
:global(.dark) .ip-sync-chip,
:global(.darkmode) .ip-sync-chip {
  background: rgba(254, 249, 236, 0.1);
  border-color: rgba(240, 216, 138, 0.35);
  color: #d4b04a;
}
.ip-subtitle {
  font-size: 0.9028rem;
  color: rgba(105, 105, 105, 0.75);
  line-height: 1.5;
}
:global(.dark) .ip-subtitle,
:global(.darkmode) .ip-subtitle {
  color: rgba(255, 255, 255, 0.5);
}

/* ── Context block ── */
.ip-context {
  background: #f7f8fa;
  border-radius: 0.8333rem;
  padding: 1.0417rem 1.3889rem;
  margin-bottom: 1.1111rem;
}
:global(.dark) .ip-context,
:global(.darkmode) .ip-context {
  background: rgba(255, 255, 255, 0.05);
}
.ip-context__head {
  display: flex;
  align-items: center;
  gap: 0.4167rem;
  font-size: 0.9028rem;
  font-weight: 500;
  color: rgba(105, 105, 105, 0.8);
  margin-bottom: 0.8333rem;
}
:global(.dark) .ip-context__head,
:global(.darkmode) .ip-context__head {
  color: rgba(255, 255, 255, 0.55);
}
.ip-context__cols {
  display: flex;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 0.6944rem;
}
.ip-ctx-sep {
  width: 1px;
  height: 2.2222rem;
  background: rgba(105, 105, 105, 0.15);
  flex-shrink: 0;
}
:global(.dark) .ip-ctx-sep,
:global(.darkmode) .ip-ctx-sep {
  background: rgba(255, 255, 255, 0.12);
}
.ip-ctx-col {
  display: flex;
  flex-direction: column;
  gap: 0.2778rem;
  min-width: 0;
  padding: 0 0.6944rem;
}
.ip-ctx-col:first-child { padding-left: 0; }
.ip-ctx-label {
  font-size: 0.7639rem;
  color: rgba(105, 105, 105, 0.6);
  font-weight: 500;
}
:global(.dark) .ip-ctx-label,
:global(.darkmode) .ip-ctx-label {
  color: rgba(255, 255, 255, 0.4);
}
.ip-ctx-val {
  font-size: 0.9722rem;
  font-weight: 600;
  color: #171717;
}
:global(.dark) .ip-ctx-val,
:global(.darkmode) .ip-ctx-val {
  color: rgba(255, 255, 255, 0.9);
}

/* ── New goal notice ── */
.ip-notice {
  padding: 0.9722rem 1.2500rem;
  background: #eff6ff;
  border: 1px dashed #93c5fd;
  border-radius: 0.8333rem;
  font-size: 0.9028rem;
  color: #1d4ed8;
  margin-bottom: 1.3889rem;
  line-height: 1.5;
}
:global(.dark) .ip-notice,
:global(.darkmode) .ip-notice {
  background: rgba(37, 99, 235, 0.1);
  border-color: rgba(37, 99, 235, 0.3);
  color: #93c5fd;
}

/* ── Main block ── */
.ip-main {
  background: #fff;
  border: 1px solid #e9e9e9;
  border-radius: 0.8333rem;
  padding: 1.3889rem;
}
:global(.dark) .ip-main,
:global(.darkmode) .ip-main {
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(255, 255, 255, 0.1);
}

/* ── Counter row ── */
.ip-counter-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.1111rem;
}
.ip-section-title {
  font-size: 1.0417rem;
  font-weight: 600;
  color: #171717;
  margin-bottom: 0.2778rem;
  line-height: 1.3;
}
:global(.dark) .ip-section-title,
:global(.darkmode) .ip-section-title {
  color: rgba(255, 255, 255, 0.9);
}
.ip-section-sub {
  font-size: 0.8333rem;
  color: rgba(105, 105, 105, 0.7);
}
:global(.dark) .ip-section-sub,
:global(.darkmode) .ip-section-sub {
  color: rgba(255, 255, 255, 0.45);
}
.ip-tariff-btn {
  flex-shrink: 0;
  padding: 0.4861rem 0.9722rem;
  border: 1px solid rgba(105, 105, 105, 0.2);
  border-radius: 0.5556rem;
  background: #fff;
  font-size: 0.8333rem;
  font-weight: 500;
  color: #696969;
  cursor: pointer;
  transition: border-color 0.3s, color 0.3s;
}
.ip-tariff-btn:hover { border-color: #2563eb; color: #2563eb; }
:global(.dark) .ip-tariff-btn,
:global(.darkmode) .ip-tariff-btn {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.15);
  color: rgba(255, 255, 255, 0.65);
}

.ip-counter-list {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 0.4167rem;
  max-width: 60%;
}
.ip-counter-chip {
  min-height: 2.0833rem;
  padding: 0.4167rem 0.7639rem;
  border: 1px solid rgba(105, 105, 105, 0.2);
  border-radius: 0.5556rem;
  background: #fff;
  color: rgba(23, 23, 23, 0.72);
  font-size: 0.7639rem;
  font-weight: 600;
  cursor: pointer;
}
.ip-counter-chip--active {
  border-color: rgba(37, 99, 235, 0.4);
  background: #eff6ff;
  color: #1d4ed8;
}

/* ── HR ── */
.ip-hr {
  height: 1px;
  background: #e9e9e9;
  margin-bottom: 1.1111rem;
}
:global(.dark) .ip-hr,
:global(.darkmode) .ip-hr {
  background: rgba(255, 255, 255, 0.1);
}

/* ── Goals hint ── */
.ip-goals-hint {
  font-size: 0.8333rem;
  color: #b07d1a;
  margin-bottom: 0.8333rem;
  display: flex;
  align-items: center;
  gap: 0.3472rem;
}
:global(.dark) .ip-goals-hint,
:global(.darkmode) .ip-goals-hint {
  color: #d4a843;
}
.ip-star-hint {
  color: #b07d1a;
}

/* ── Goals loading ── */
.ip-goals-loading {
  font-size: 0.8333rem;
  color: rgba(105, 105, 105, 0.6);
  padding: 0.6944rem 0;
  margin-bottom: 1.0417rem;
}

/* ── Goals list ── */
.ip-goals {
  display: flex;
  flex-direction: column;
  gap: 0.4167rem;
  margin-bottom: 1.0417rem;
  max-height: 18rem;
  overflow-y: auto;
  padding-right: 0.2778rem;
}
.ip-goals::-webkit-scrollbar {
  width: 4px;
}
.ip-goals::-webkit-scrollbar-track {
  background: transparent;
}
.ip-goals::-webkit-scrollbar-thumb {
  background: rgba(105, 105, 105, 0.2);
  border-radius: 2px;
}
.ip-goals::-webkit-scrollbar-thumb:hover {
  background: rgba(105, 105, 105, 0.4);
}
.ip-goal {
  display: flex;
  align-items: center;
  gap: 0.8333rem;
  padding: 0.7639rem 1.0417rem;
  border-radius: 0.6944rem;
  border: 1px solid transparent;
}
.ip-goal--checked {
  background: rgba(230, 210, 160, 0.18);
  border-color: rgba(180, 155, 90, 0.2);
}
.ip-goal--selected {
  cursor: pointer;
}
.ip-goal--new {
  background: rgba(37, 99, 235, 0.06);
  border-color: rgba(37, 99, 235, 0.18);
}
.ip-goal--error {
  background: rgba(239, 68, 68, 0.05);
  border-color: rgba(239, 68, 68, 0.15);
}
:global(.dark) .ip-goal--checked,
:global(.darkmode) .ip-goal--checked {
  background: rgba(230, 210, 160, 0.08);
  border-color: rgba(180, 155, 90, 0.2);
}
:global(.dark) .ip-goal--new,
:global(.darkmode) .ip-goal--new {
  background: rgba(37, 99, 235, 0.12);
  border-color: rgba(37, 99, 235, 0.25);
}
:global(.dark) .ip-goal--error,
:global(.darkmode) .ip-goal--error {
  background: rgba(239, 68, 68, 0.08);
  border-color: rgba(239, 68, 68, 0.2);
}

.ip-goal__info {
  flex: 1;
  min-width: 0;
}
.ip-goal__name {
  font-size: 0.9028rem;
  font-weight: 500;
  color: #171717;
}
.ip-goal--new .ip-goal__name { color: #1d4ed8; }
.ip-goal--error .ip-goal__name { color: #dc2626; }
:global(.dark) .ip-goal__name,
:global(.darkmode) .ip-goal__name { color: rgba(255,255,255,0.9); }
:global(.dark) .ip-goal--new .ip-goal__name,
:global(.darkmode) .ip-goal--new .ip-goal__name { color: #93c5fd; }
:global(.dark) .ip-goal--error .ip-goal__name,
:global(.darkmode) .ip-goal--error .ip-goal__name { color: #f87171; }

.ip-goal__meta {
  font-size: 0.8333rem;
  color: rgba(105, 105, 105, 0.65);
}
.ip-goal--new .ip-goal__meta { color: rgba(37, 99, 235, 0.65); }
.ip-goal--error .ip-goal__meta { color: rgba(220, 38, 38, 0.65); }
:global(.dark) .ip-goal__meta,
:global(.darkmode) .ip-goal__meta { color: rgba(255,255,255,0.4); }

.ip-goal__right {
  display: flex;
  align-items: center;
}
.ip-goal__icon {
  border: 0;
  background: transparent;
  padding: 0;
  cursor: pointer;
}
.ip-goal-star {
  cursor: pointer;
  opacity: 0.6;
  transition: transform 0.2s, opacity 0.2s;
}
.ip-goal-star:hover,
.ip-goal-star--active {
  opacity: 1;
  transform: scale(1.08);
}
.ip-new-badge {
  display: inline-block;
  padding: 0.2083rem 0.5556rem;
  border: 1px solid #2563eb;
  border-radius: 0.3472rem;
  font-size: 0.7639rem;
  font-weight: 600;
  color: #2563eb;
  white-space: nowrap;
}
:global(.dark) .ip-new-badge,
:global(.darkmode) .ip-new-badge {
  border-color: #93c5fd;
  color: #93c5fd;
}
.ip-error-text {
  font-size: 0.8333rem;
  font-weight: 500;
  color: #dc2626;
  white-space: nowrap;
}
:global(.dark) .ip-error-text,
:global(.darkmode) .ip-error-text { color: #f87171; }

/* ── Warning note ── */
.ip-warning {
  display: flex;
  align-items: flex-start;
  gap: 0.5556rem;
  padding: 0.8333rem 1.0417rem;
  background: rgba(105, 105, 105, 0.05);
  border-radius: 0.5556rem;
  font-size: 0.8333rem;
  color: rgba(105, 105, 105, 0.75);
  line-height: 1.5;
}
:global(.dark) .ip-warning,
:global(.darkmode) .ip-warning {
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.4);
}

/* ── Footer ── */
.ip-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.6944rem;
  padding: 1.1111rem 2.0833rem 1.6667rem;
  border-top: 1px solid #e9e9e9;
  border-radius: 0 0 1.3889rem 1.3889rem;
}
:global(.dark) .ip-footer,
:global(.darkmode) .ip-footer {
  border-top-color: rgba(255, 255, 255, 0.1);
}
.ip-delete-btn {
  padding: 0.6944rem 1.1806rem;
  border: 1px solid rgba(239, 68, 68, 0.45);
  border-radius: 0.6944rem;
  background: #fff;
  font-size: 0.9028rem;
  font-weight: 500;
  color: #dc2626;
  cursor: pointer;
  transition: background 0.3s, border-color 0.3s;
  white-space: nowrap;
}
.ip-delete-btn:hover { background: #fef2f2; border-color: #dc2626; }
:global(.dark) .ip-delete-btn,
:global(.darkmode) .ip-delete-btn {
  background: transparent;
  border-color: rgba(239, 68, 68, 0.4);
  color: #f87171;
}
.ip-cancel-btn {
  padding: 0.6944rem 1.3889rem;
  border: 1px solid rgba(105, 105, 105, 0.2);
  border-radius: 0.6944rem;
  background: #fff;
  font-size: 0.9028rem;
  font-weight: 500;
  color: #696969;
  cursor: pointer;
  transition: border-color 0.3s;
  white-space: nowrap;
}
.ip-cancel-btn:hover { border-color: #696969; }
:global(.dark) .ip-cancel-btn,
:global(.darkmode) .ip-cancel-btn {
  background: transparent;
  border-color: rgba(255, 255, 255, 0.15);
  color: rgba(255, 255, 255, 0.65);
}
.ip-save-btn {
  padding: 0.6944rem 1.6667rem;
  border-radius: 0.6944rem;
  background: #2563eb;
  border: none;
  font-size: 0.9028rem;
  font-weight: 600;
  color: #fff;
  cursor: pointer;
  transition: opacity 0.3s, transform 0.2s;
  white-space: nowrap;
}
.ip-save-btn:hover { opacity: 0.9; }
.ip-save-btn:active { transform: scale(0.97); }
.ip-save-btn:disabled,
.ip-delete-btn:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.ip-confirm-backdrop {
  position: fixed;
  inset: 0;
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
  background: rgba(17, 24, 39, 0.38);
  backdrop-filter: blur(6px);
}
.ip-confirm {
  width: min(32rem, 100%);
  border-radius: 1.1111rem;
  background: #fff;
  border: 1px solid rgba(239, 68, 68, 0.18);
  box-shadow: 0 1.5rem 4rem rgba(17, 24, 39, 0.22);
  padding: 1.5rem;
}
.ip-confirm h3 {
  margin: 0 0 0.625rem;
  font-size: 1.25rem;
  font-weight: 700;
  color: #171717;
}
.ip-confirm p {
  margin: 0 0 1rem;
  color: rgba(105, 105, 105, 0.82);
  line-height: 1.45;
}
.ip-confirm-input {
  width: 100%;
  height: 3rem;
  border-radius: 0.6944rem;
  border: 1px solid rgba(105, 105, 105, 0.18);
  background: #f7f8fa;
  padding: 0 1rem;
  font-size: 0.9722rem;
  outline: none;
}
.ip-confirm-input:focus {
  border-color: rgba(37, 99, 235, 0.55);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}
.ip-confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.6944rem;
  margin-top: 1rem;
}

@media (max-width: 600px) {
  .ip-scroll { padding: 1.3889rem 1.3889rem 1.0417rem; }
  .ip-footer { padding: 0.8333rem 1.3889rem 1.0417rem; flex-wrap: wrap; }
  .ip-context__cols { flex-direction: column; }
  .ip-ctx-sep { width: 100%; height: 1px; }
  .ip-ctx-col { padding: 0; }
  .ip-counter-row { flex-direction: column; gap: 0.6944rem; }
  .ip-counter-list { max-width: 100%; justify-content: flex-start; }
}
</style>
