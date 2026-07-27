<template>
  <div>
    <PageHeader title="AI-лимиты" description="Использование запросов и расходы OpenAI за текущий период." eyebrow="Контроль расходов">
      <button class="button button--secondary" @click="load"><ArrowPathIcon />Обновить</button>
    </PageHeader>
    <LoadingState v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <template v-else>
      <div class="alert-banner" :class="{ 'alert-banner--warning': data.close_to_limit?.length }">
        <ExclamationTriangleIcon v-if="data.close_to_limit?.length" /><CheckCircleIcon v-else />
        <div><strong>{{ data.close_to_limit?.length ? `${data.close_to_limit.length} пользователей близки к лимиту` : 'Критических лимитов нет' }}</strong><p>{{ data.close_to_limit?.length ? 'Использовано 85% или больше доступных AI-запросов.' : 'Все пользователи находятся в безопасном диапазоне.' }}</p></div>
      </div>
      <div class="kpi-grid kpi-grid--3">
        <article class="kpi-card"><div class="kpi-card__top"><span>Расход за месяц</span><BanknotesIcon /></div><strong>{{ usd(data.openai_cost_usd_month) }}</strong><small :class="Number(data.openai_cost_delta_usd) > 0 ? 'negative' : 'positive'">{{ signedUsd(data.openai_cost_delta_usd) }} к прошлому периоду</small></article>
        <article class="kpi-card"><div class="kpi-card__top"><span>Баланс OpenAI</span><WalletIcon /></div><strong>{{ data.openai_balance_usd == null ? 'Не задан' : usd(data.openai_balance_usd) }}</strong><small class="muted">Порог: {{ data.openai_alert_threshold_usd == null ? 'не задан' : usd(data.openai_alert_threshold_usd) }}</small></article>
        <article class="kpi-card"><div class="kpi-card__top"><span>Пользователи ≥85%</span><BoltIcon /></div><strong>{{ number(data.close_to_limit?.length || 0) }}</strong><small class="muted">из {{ number(data.items?.length || 0) }} аккаунтов</small></article>
      </div>
      <section class="panel">
        <div class="panel__header"><div><p class="eyebrow">По пользователям</p><h2>Использование AI</h2></div><select v-model="threshold" @change="load"><option :value="70">Порог 70%</option><option :value="85">Порог 85%</option><option :value="90">Порог 90%</option></select></div>
        <div class="ai-list">
          <article v-for="item in data.items || []" :key="item.user_id">
            <div class="user-cell"><span class="avatar avatar--small">{{ initials(item) }}</span><span><strong>{{ item.full_name || 'Без имени' }}</strong><small>{{ item.email }} · {{ planLabel(item.plan_code) }}</small></span></div>
            <ProgressBar :value="item.used_percent" :label="`${number(item.used)} / ${number(item.limit)}`" />
            <UiBadge v-if="item.close_to_limit" label="Требует внимания" tone="warning" dot />
            <UiBadge v-else label="Норма" tone="success" dot />
            <button class="button button--tiny button--secondary" @click="selected = item; newLimit = item.limit">Изменить</button>
          </article>
        </div>
        <EmptyState v-if="!data.items?.length" title="Нет данных об использовании" />
      </section>
      <AppModal :open="Boolean(selected)" title="Персональный AI-лимит" eyebrow="Пользователь" @close="selected = null">
        <p class="muted modal-copy">{{ selected?.full_name }} · {{ selected?.email }}</p>
        <label class="field"><span>Новый лимит запросов</span><input v-model.number="newLimit" type="number" min="0" max="100000" /></label>
        <template #footer><button class="button button--secondary" @click="selected = null">Отмена</button><button class="button button--primary" @click="saveLimit">Сохранить</button></template>
      </AppModal>
      <section class="panel">
        <div class="panel__header"><div><p class="eyebrow">Справочник</p><h2>Лимиты по тарифам</h2></div></div>
        <div class="limit-cards">
          <article v-for="(limit, plan) in data.plan_limits || {}" :key="plan"><span>{{ planLabel(plan) }}</span><strong>{{ number(limit) }}</strong><small>запросов / период</small></article>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ArrowPathIcon, BanknotesIcon, BoltIcon, CheckCircleIcon, ExclamationTriangleIcon, WalletIcon } from '@heroicons/vue/24/outline'
import api, { apiError } from '../api/client'
import { number, planLabel, usd } from '../utils/formatters'
import PageHeader from '../components/PageHeader.vue'
import LoadingState from '../components/LoadingState.vue'
import ErrorState from '../components/ErrorState.vue'
import EmptyState from '../components/EmptyState.vue'
import ProgressBar from '../components/ProgressBar.vue'
import UiBadge from '../components/UiBadge.vue'
import AppModal from '../components/AppModal.vue'
import { useToast } from '../composables/useToast'
const toast = useToast()
const data = ref({})
const loading = ref(true)
const error = ref('')
const threshold = ref(85)
const selected = ref(null)
const newLimit = ref(0)
const initials = (item) => (item.full_name || item.email || '?').split(/\s|@/).filter(Boolean).slice(0, 2).map((x) => x[0]).join('').toUpperCase()
const signedUsd = (value) => `${Number(value) > 0 ? '+' : ''}${usd(value || 0)}`
async function load() {
  loading.value = true; error.value = ''
  try { data.value = (await api.get('/admin/ai-limits/usage', { params: { threshold: threshold.value } })).data }
  catch (err) { error.value = apiError(err) }
  finally { loading.value = false }
}
async function saveLimit() {
  try {
    await api.patch(`/admin/users/${selected.value.user_id}/ai-limit`, null, { params: { limit: newLimit.value } })
    toast.success('Команда изменения лимита отправлена')
    selected.value = null
    await load()
  } catch (err) { toast.error(apiError(err)) }
}
onMounted(load)
</script>
