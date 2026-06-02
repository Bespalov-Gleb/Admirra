<template>
  <div class="integration-edit-page">
    <div class="page-head">
      <div>
        <button class="back-btn" type="button" @click="router.push('/integrations')">← Интеграции</button>
        <h3>Настройка интеграции</h3>
        <p>Правка состава целей без повторной авторизации и смены рекламного кабинета.</p>
      </div>
    </div>

    <div v-if="loading" class="empty-state">Загрузка…</div>
    <div v-else-if="!integration" class="empty-state">Интеграция не найдена.</div>

    <template v-else>
      <section class="locked-context">
        <div class="context-item">
          <span>Канал</span>
          <strong><img :src="platformIcon" alt="" />{{ platformLabel }}</strong>
        </div>
        <div class="context-item">
          <span>Проект</span>
          <strong>{{ integration.client_name || '—' }}</strong>
        </div>
        <div class="context-item">
          <span>Рекламный кабинет</span>
          <strong>{{ integration.account_name || integration.account_id || '—' }}</strong>
        </div>
        <div class="lock-note">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <rect x="4" y="10" width="16" height="10" rx="2" stroke="currentColor" stroke-width="2"/>
            <path d="M8 10V7a4 4 0 1 1 8 0v3" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
          Канал, проект и кабинет не меняются на этом экране.
        </div>
      </section>

      <section v-if="isYandex" class="edit-grid">
        <div class="panel">
          <div class="panel-head">
            <div>
              <h4>Счётчики Метрики</h4>
              <p>При смене счётчика поменяется весь набор доступных целей.</p>
            </div>
            <button class="small-btn" type="button" :disabled="countersLoading || !counters.length" @click="toggleAllCounters">
              {{ allCountersSelected ? 'Снять все' : 'Отметить все' }}
            </button>
          </div>

          <div class="info-note">
            Несколько счётчиков объединяются: цели суммируются по выбранному набору.
          </div>

          <div v-if="countersLoading" class="empty-line">Загрузка счётчиков…</div>
          <div v-else-if="!counters.length" class="empty-line">Счётчики не найдены.</div>
          <div v-else class="counter-list">
            <label v-for="counter in counters" :key="counter.id" class="counter-row" :class="{ active: selectedCounterIds.includes(String(counter.id)) }">
              <input type="checkbox" :checked="selectedCounterIds.includes(String(counter.id))" @change="toggleCounter(counter.id)" />
              <span class="row-check">✓</span>
              <span>
                <strong>{{ counter.name || `Счётчик ${counter.id}` }}</strong>
                <small>ID {{ counter.id }}</small>
              </span>
            </label>
          </div>
        </div>

        <div class="panel">
          <div class="panel-head">
            <div>
              <h4>Цели и основная цель</h4>
              <p>Звезда задаёт основную цель для ключевых метрик и аналитики.</p>
            </div>
            <button class="small-btn" type="button" :disabled="goalsLoading || !visibleGoals.length" @click="toggleAllGoals">
              {{ allGoalsSelected ? 'Снять все' : 'Отметить все' }}
            </button>
          </div>

          <div class="info-note">
            Данные берутся из Яндекс.Метрики как есть. Проверьте, не пересекаются ли выбранные цели, иначе одно действие может засчитаться дважды.
          </div>

          <div v-if="newGoalsCount || missingGoalsCount" class="goal-drift">
            <span v-if="newGoalsCount">В Метрике {{ newGoalsCount }} {{ plural(newGoalsCount, ['новая цель', 'новые цели', 'новых целей']) }}.</span>
            <span v-if="missingGoalsCount">{{ missingGoalsCount }} {{ plural(missingGoalsCount, ['цель не приходит', 'цели не приходят', 'целей не приходит']) }} из Метрики.</span>
          </div>

          <div v-if="goalsLoading" class="empty-line">Загрузка целей…</div>
          <div v-else-if="!visibleGoals.length" class="empty-line">Цели не найдены.</div>

          <div v-else class="goal-list">
            <label
              v-for="goal in visibleGoals"
              :key="goal.key"
              class="goal-row"
              :class="{ active: selectedGoalIds.includes(goal.id), missing: goal.state === 'missing' }"
            >
              <input
                type="checkbox"
                :disabled="goal.state === 'missing'"
                :checked="selectedGoalIds.includes(goal.id)"
                @change="toggleGoal(goal.id)"
              />
              <span class="row-check">✓</span>
              <span class="goal-title">
                <strong>{{ goal.name }}</strong>
                <small>ID {{ goal.id }}<template v-if="goal.counter_id"> · счётчик {{ goal.counter_id }}</template></small>
              </span>
              <span v-if="goal.state === 'new'" class="goal-badge">новая</span>
              <span v-if="goal.state === 'missing'" class="goal-badge goal-badge--danger">не приходит из Метрики</span>
              <button
                type="button"
                class="star-btn"
                :class="{ active: primaryGoalId === goal.id }"
                :disabled="goal.state === 'missing'"
                title="Сделать основной целью"
                @click.prevent="setPrimary(goal.id)"
              >
                ★
              </button>
            </label>
          </div>
        </div>
      </section>

      <section v-else class="panel">
        <h4>VK Ads</h4>
        <p class="vk-note">Для VK Ads цели Метрики не настраиваются. Данные целевых действий приходят из VK Ads по типам кампаний.</p>
      </section>

      <div class="actions-bar">
        <button class="danger-outline" type="button" @click="showArchiveHint = true">Удалить интеграцию</button>
        <div>
          <button class="secondary-btn" type="button" @click="router.push('/integrations')">Отмена</button>
          <button class="primary-btn" type="button" :disabled="saving || (isYandex && !canSave)" @click="save">
            {{ saving ? 'Сохранение…' : 'Сохранить' }}
          </button>
        </div>
      </div>

      <div v-if="showArchiveHint" class="archive-note">
        <span>Интеграция будет скрыта из активных подключений, автосинхронизация остановится, история данных сохранится.</span>
        <button type="button" :disabled="archiving" @click="archiveIntegration">
          {{ archiving ? 'Удаление…' : 'Подтвердить удаление' }}
        </button>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../../api/axios'
import { useToaster } from '../../composables/useToaster'

const route = useRoute()
const router = useRouter()
const toaster = useToaster()

const integration = ref(null)
const loading = ref(true)
const countersLoading = ref(false)
const goalsLoading = ref(false)
const saving = ref(false)
const archiving = ref(false)
const counters = ref([])
const goals = ref([])
const selectedCounterIds = ref([])
const selectedGoalIds = ref([])
const primaryGoalId = ref(null)
const showArchiveHint = ref(false)

const isYandex = computed(() => normalizePlatform(integration.value?.platform) === 'YANDEX_DIRECT')
const platformLabel = computed(() => isYandex.value ? 'Yandex Direct' : 'VK Ads')
const platformIcon = computed(() => isYandex.value ? '/admirra/img/icons/yandex-direct.png' : '/admirra/img/icons/vk-ads.png')
const allCountersSelected = computed(() => counters.value.length > 0 && selectedCounterIds.value.length === counters.value.length)
const allGoalsSelected = computed(() => availableGoalIds.value.length > 0 && availableGoalIds.value.every((id) => selectedGoalIds.value.includes(id)))
const availableGoalIds = computed(() => visibleGoals.value.filter((goal) => goal.state !== 'missing').map((goal) => String(goal.id)))
const newGoalsCount = computed(() => visibleGoals.value.filter((goal) => goal.state === 'new').length)
const missingGoalsCount = computed(() => visibleGoals.value.filter((goal) => goal.state === 'missing').length)
const canSave = computed(() => selectedCounterIds.value.length > 0 && selectedGoalIds.value.length > 0 && primaryGoalId.value)

const visibleGoals = computed(() => {
  return goals.value.map((goal) => ({
    ...goal,
    id: String(goal.id),
    key: `${goal.counter_id || 'goal'}:${goal.id}`,
    state: goal.state || (selectedGoalIds.value.includes(String(goal.id)) ? 'tracked' : 'available'),
  }))
})

watch(selectedCounterIds, () => {
  if (!loading.value && isYandex.value) fetchGoals()
}, { deep: true })

onMounted(async () => {
  await fetchIntegration()
})

async function fetchIntegration() {
  loading.value = true
  try {
    const { data } = await api.get(`integrations/${route.params.id}`)
    integration.value = data
    selectedCounterIds.value = Array.isArray(data.selected_counters) ? data.selected_counters.map(String) : []
    selectedGoalIds.value = Array.isArray(data.selected_goals) ? data.selected_goals.map(String) : []
    primaryGoalId.value = data.primary_goal_id ? String(data.primary_goal_id) : (selectedGoalIds.value[0] || null)
    if (isYandex.value) {
      await fetchCounters()
      if (!selectedCounterIds.value.length && counters.value.length) {
        selectedCounterIds.value = counters.value.map((counter) => String(counter.id))
      }
      await fetchGoals()
    }
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Не удалось загрузить интеграцию.')
  } finally {
    loading.value = false
  }
}

async function fetchCounters() {
  countersLoading.value = true
  try {
    const account = integration.value?.agency_client_login || integration.value?.account_id || ''
    const accountParam = account ? `?account_id=${encodeURIComponent(account)}` : ''
    const { data } = await api.get(`integrations/${route.params.id}/counters${accountParam}`)
    counters.value = (data.counters || []).map((counter) => ({ ...counter, id: String(counter.id) }))
  } catch (err) {
    counters.value = []
    toaster.warning('Не удалось загрузить счётчики.')
  } finally {
    countersLoading.value = false
  }
}

async function fetchGoals() {
  goalsLoading.value = true
  try {
    const now = new Date()
    const from = new Date(now)
    from.setDate(now.getDate() - 7)
    const dateFrom = formatApiDate(from)
    const dateTo = formatApiDate(now)
    const account = integration.value?.agency_client_login || integration.value?.account_id || ''
    const params = new URLSearchParams({
      date_from: dateFrom,
      date_to: dateTo,
      with_stats: 'false',
    })
    if (account) params.set('account_id', account)
    if (selectedCounterIds.value.length) params.set('counter_ids', selectedCounterIds.value.join(','))
    const { data } = await api.get(`integrations/${route.params.id}/goals?${params.toString()}`)
    const list = Array.isArray(data) ? data : (Array.isArray(data?.goals) ? data.goals : [])
    goals.value = list.map((goal) => ({
      ...goal,
      id: String(goal.id),
      counter_id: goal.counter_id != null ? String(goal.counter_id) : goal.counter_id,
      state: goal.state || 'available',
    }))
  } catch (err) {
    goals.value = []
    toaster.warning('Не удалось загрузить цели.')
  } finally {
    goalsLoading.value = false
  }
}

function toggleCounter(id) {
  const value = String(id)
  selectedCounterIds.value = selectedCounterIds.value.includes(value)
    ? selectedCounterIds.value.filter((item) => item !== value)
    : [...selectedCounterIds.value, value]
}

function toggleAllCounters() {
  selectedCounterIds.value = allCountersSelected.value ? [] : counters.value.map((counter) => String(counter.id))
}

function toggleGoal(id) {
  const value = String(id)
  selectedGoalIds.value = selectedGoalIds.value.includes(value)
    ? selectedGoalIds.value.filter((item) => item !== value)
    : [...selectedGoalIds.value, value]
  if (!selectedGoalIds.value.includes(primaryGoalId.value)) {
    primaryGoalId.value = selectedGoalIds.value[0] || null
  }
}

function toggleAllGoals() {
  selectedGoalIds.value = allGoalsSelected.value ? [] : [...availableGoalIds.value]
  if (!selectedGoalIds.value.includes(primaryGoalId.value)) {
    primaryGoalId.value = selectedGoalIds.value[0] || null
  }
}

function setPrimary(id) {
  const value = String(id)
  if (!selectedGoalIds.value.includes(value)) {
    selectedGoalIds.value = [...selectedGoalIds.value, value]
  }
  primaryGoalId.value = value
}

async function save() {
  if (isYandex.value && !canSave.value) {
    toaster.warning('Выберите счётчик, хотя бы одну цель и основную цель.')
    return
  }
  saving.value = true
  try {
    await api.patch(`integrations/${route.params.id}`, {
      selected_counters: [...selectedCounterIds.value],
      selected_goals: [...selectedGoalIds.value],
      known_goal_ids: availableGoalIds.value,
      primary_goal_id: primaryGoalId.value,
    })
    toaster.success('Интеграция обновлена.')
    router.push('/integrations')
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Не удалось сохранить настройки.')
  } finally {
    saving.value = false
  }
}

async function archiveIntegration() {
  archiving.value = true
  try {
    await api.delete(`integrations/${route.params.id}`)
    toaster.success('Интеграция удалена, история сохранена.')
    router.push('/integrations')
  } catch (err) {
    toaster.error(err.response?.data?.detail || 'Не удалось удалить интеграцию.')
  } finally {
    archiving.value = false
  }
}

function normalizePlatform(platform) {
  const key = String(platform || '').toUpperCase()
  return ({ YANDEX: 'YANDEX_DIRECT', VK: 'VK_ADS' }[key]) || key
}

function formatApiDate(date) {
  return date.toISOString().slice(0, 10)
}

function plural(n, forms) {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return forms[0]
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return forms[1]
  return forms[2]
}
</script>

<style scoped>
.integration-edit-page {
  position: relative;
  z-index: 2;
  display: flex;
  min-height: 100%;
  flex-direction: column;
  gap: 1.3889rem;
  overflow: hidden;
  padding: 2.0833rem 1.7361rem;
}
.page-head {
  padding-top: 1.0417rem;
}
.back-btn {
  margin-bottom: 0.8333rem;
  border: 0;
  background: transparent;
  color: rgba(105, 105, 105, 0.56);
  font-size: 0.9028rem;
  font-weight: 600;
  cursor: pointer;
}
.page-head h3 {
  margin: 0;
  color: #171717;
  font-size: 2.0833rem;
  font-weight: 600;
  line-height: 1;
}
.page-head p {
  margin: 0.6944rem 0 0;
  color: rgba(105, 105, 105, 0.56);
  font-size: 1.0417rem;
  font-weight: 500;
}
.empty-state,
.empty-line {
  display: flex;
  min-height: 8rem;
  align-items: center;
  justify-content: center;
  color: rgba(105, 105, 105, 0.56);
  font-size: 0.9028rem;
}
.locked-context,
.panel {
  border-radius: 1.25rem;
  background: #fff;
}
.locked-context {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1.0417rem;
  padding: 1.3889rem;
}
.context-item {
  display: grid;
  gap: 0.4167rem;
  min-height: 4.1667rem;
  padding: 0.8333rem 1.0417rem;
  border-radius: 0.8333rem;
  background: #f8fafc;
}
.context-item span {
  color: rgba(105, 105, 105, 0.48);
  font-size: 0.7639rem;
  font-weight: 700;
  text-transform: uppercase;
}
.context-item strong {
  display: flex;
  align-items: center;
  gap: 0.5556rem;
  color: #171717;
  font-size: 0.9722rem;
  font-weight: 700;
}
.context-item img {
  width: 1.6667rem;
  height: 1.6667rem;
  object-fit: contain;
}
.lock-note {
  display: flex;
  align-items: center;
  gap: 0.5556rem;
  color: rgba(105, 105, 105, 0.56);
  font-size: 0.8333rem;
  font-weight: 600;
}
.edit-grid {
  display: grid;
  grid-template-columns: minmax(22rem, 0.8fr) minmax(30rem, 1.2fr);
  gap: 1.3889rem;
}
.panel {
  display: flex;
  flex-direction: column;
  gap: 1.0417rem;
  padding: 1.3889rem;
}
.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}
.panel h4,
.panel-head h4 {
  margin: 0;
  color: #171717;
  font-size: 1.25rem;
  font-weight: 700;
}
.panel p,
.panel-head p {
  margin: 0.4167rem 0 0;
  color: rgba(105, 105, 105, 0.56);
  font-size: 0.9028rem;
  font-weight: 500;
  line-height: 1.35;
}
.info-note,
.goal-drift,
.archive-note {
  padding: 0.8333rem 1.0417rem;
  border-radius: 0.8333rem;
  background: #f4f8ff;
  color: #3463a8;
  font-size: 0.8333rem;
  font-weight: 600;
  line-height: 1.4;
}
.goal-drift {
  display: grid;
  gap: 0.2778rem;
  background: #fff7dd;
  color: #a16207;
}
.archive-note {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  background: #fff1f1;
  color: #b91c1c;
}
.archive-note button {
  min-height: 2.5rem;
  flex: 0 0 auto;
  padding: 0 1rem;
  border: 0;
  border-radius: 0.6944rem;
  background: #ef4444;
  color: #fff;
  font-size: 0.8333rem;
  font-weight: 800;
  cursor: pointer;
}
.archive-note button:disabled {
  opacity: 0.6;
  cursor: wait;
}
.counter-list,
.goal-list {
  display: grid;
  gap: 0.6944rem;
}
.counter-row,
.goal-row {
  display: grid;
  grid-template-columns: auto auto minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 0.6944rem;
  min-height: 4.1667rem;
  padding: 0.8333rem 1.0417rem;
  border-radius: 0.8333rem;
  background: #f8fafc;
  color: #2c2c2c;
}
.counter-row {
  grid-template-columns: auto auto minmax(0, 1fr);
}
.counter-row input,
.goal-row input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}
.row-check {
  display: flex;
  width: 1.3889rem;
  height: 1.3889rem;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #e8eef9;
  color: transparent;
  font-size: 0.7639rem;
  font-weight: 900;
}
.counter-row.active .row-check,
.goal-row.active .row-check {
  background: #2563eb;
  color: #fff;
}
.counter-row strong,
.goal-row strong {
  display: block;
  color: #171717;
  font-size: 0.9028rem;
  font-weight: 700;
}
.counter-row small,
.goal-row small {
  display: block;
  margin-top: 0.2778rem;
  color: rgba(105, 105, 105, 0.52);
  font-size: 0.7639rem;
  font-weight: 500;
}
.goal-title {
  min-width: 0;
}
.goal-badge {
  display: inline-flex;
  align-items: center;
  min-height: 1.6667rem;
  padding: 0 0.5556rem;
  border-radius: 99rem;
  background: #e9fbf0;
  color: #13a548;
  font-size: 0.6944rem;
  font-weight: 800;
}
.goal-badge--danger {
  background: #fff1f1;
  color: #ef4444;
}
.goal-row.missing {
  opacity: 0.78;
}
.star-btn {
  display: flex;
  width: 2.0833rem;
  height: 2.0833rem;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: 50%;
  background: #fff;
  color: rgba(105, 105, 105, 0.34);
  cursor: pointer;
}
.star-btn.active {
  background: #fff7dd;
  color: #f59e0b;
}
.actions-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1.0417rem;
  border-radius: 1.25rem;
  background: #fff;
}
.actions-bar > div {
  display: flex;
  gap: 0.6944rem;
}
.primary-btn,
.secondary-btn,
.danger-outline,
.small-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 3.1944rem;
  padding: 0.5556rem 1.3889rem;
  border: 0;
  border-radius: 1.0417rem;
  font-size: 0.9028rem;
  font-weight: 600;
  cursor: pointer;
}
.primary-btn {
  background: linear-gradient(270deg, #06b5d4 0.35%, #1f9de4 32.08%, #2563eb 96.51%);
  color: #fff;
}
.primary-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.secondary-btn,
.small-btn {
  background: #f5f7f9;
  color: #696969;
}
.small-btn {
  min-height: 2.5rem;
  border-radius: 0.8333rem;
}
.danger-outline {
  border: 1px solid rgba(239, 68, 68, 0.3);
  background: #fff;
  color: #ef4444;
}
.vk-note {
  max-width: 42rem;
}
@media (max-width: 1180px) {
  .locked-context,
  .edit-grid {
    grid-template-columns: 1fr;
  }
}
</style>
