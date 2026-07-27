<template>
  <div>
    <PageHeader title="Состояние сервиса" description="Главные показатели AdMirra за последние 30 дней." eyebrow="Super Admin">
      <button class="button button--secondary" :disabled="loading" @click="load"><ArrowPathIcon />Обновить</button>
    </PageHeader>

    <ErrorState v-if="error" :message="error" @retry="load" />
    <template v-else>
      <div class="kpi-grid">
        <article class="kpi-card kpi-card--accent">
          <div class="kpi-card__top"><span>Пользователи</span><UsersIcon /></div>
          <strong>{{ number(data.users_total) }}</strong>
          <small :class="deltaTone(data.users_new_delta_vs_prev_period)"><ArrowTrendingUpIcon />{{ signed(data.users_new_delta_vs_prev_period) }} новых к прошлому периоду</small>
        </article>
        <article class="kpi-card">
          <div class="kpi-card__top"><span>MRR</span><BanknotesIcon /></div>
          <strong>{{ money(data.mrr_rub) }}</strong>
          <small class="muted">Активная регулярная выручка</small>
        </article>
        <article class="kpi-card">
          <div class="kpi-card__top"><span>AI-запросы</span><SparklesIcon /></div>
          <strong>{{ number(data.ai_requests_total) }}</strong>
          <small class="muted">{{ usd(data.openai_cost_usd_month) }} расходов за период</small>
        </article>
        <article class="kpi-card">
          <div class="kpi-card__top"><span>Churn</span><ArrowTrendingDownIcon /></div>
          <strong>{{ percent(data.churn_rate_percent) }}</strong>
          <small :class="Number(data.churn_rate_percent) > 5 ? 'negative' : 'positive'">{{ Number(data.churn_rate_percent) > 5 ? 'Требует внимания' : 'В рабочем диапазоне' }}</small>
        </article>
      </div>

      <LoadingState v-if="loading" :rows="4" />
      <div v-else class="dashboard-grid">
        <section class="panel panel--span-2">
          <div class="panel__header"><div><p class="eyebrow">Привлечение</p><h2>Источники регистраций</h2></div><UiBadge :label="`${number(utmTotal)} регистраций`" tone="info" /></div>
          <div v-if="data.utm_sources?.length" class="source-list">
            <div v-for="source in data.utm_sources" :key="source.source" class="source-row">
              <div><strong>{{ source.source }}</strong><small>{{ number(source.count) }} пользователей</small></div>
              <div class="source-bar"><span :style="{ width: `${source.percent}%` }" /></div>
              <b>{{ percent(source.percent) }}</b>
            </div>
          </div>
          <EmptyState v-else title="Нет UTM-данных" description="Источники появятся после новых регистраций с UTM-метками." />
        </section>

        <section class="panel">
          <div class="panel__header"><div><p class="eyebrow">Подписки</p><h2>Тарифы</h2></div></div>
          <div class="distribution-list">
            <div v-for="(item, index) in data.tariffs || []" :key="item.plan_code">
              <span class="legend-dot" :style="{ background: palette[index % palette.length] }" />
              <span>{{ planLabel(item.plan_code) }}</span><strong>{{ number(item.count) }}</strong>
            </div>
          </div>
          <EmptyState v-if="!data.tariffs?.length" title="Нет активных тарифов" description="Распределение появится после первых подписок." />
        </section>

        <section class="panel panel--span-3">
          <div class="panel__header"><div><p class="eyebrow">Экосистема</p><h2>Подключения по каналам</h2></div></div>
          <div class="integration-strip">
            <article v-for="integration in data.integrations || []" :key="integration.platform">
              <span class="integration-icon">{{ platformInitial(integration.platform) }}</span>
              <div><strong>{{ platformLabel(integration.platform) }}</strong><small>подключено кабинетов</small></div>
              <b>{{ number(integration.count) }}</b>
            </article>
          </div>
          <EmptyState v-if="!data.integrations?.length" title="Нет подключений" description="Подключённые рекламные кабинеты появятся здесь." />
        </section>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ArrowPathIcon, ArrowTrendingDownIcon, ArrowTrendingUpIcon, BanknotesIcon, SparklesIcon, UsersIcon } from '@heroicons/vue/24/outline'
import api, { apiError } from '../api/client'
import { money, number, percent, planLabel, platformLabel, usd } from '../utils/formatters'
import PageHeader from '../components/PageHeader.vue'
import UiBadge from '../components/UiBadge.vue'
import LoadingState from '../components/LoadingState.vue'
import ErrorState from '../components/ErrorState.vue'
import EmptyState from '../components/EmptyState.vue'

const data = ref({})
const loading = ref(true)
const error = ref('')
const palette = ['#4263eb', '#7c5ce7', '#20a474', '#f59f00']
const utmTotal = computed(() => (data.value.utm_sources || []).reduce((sum, item) => sum + Number(item.count || 0), 0))
const signed = (value) => `${Number(value) > 0 ? '+' : ''}${number(value || 0)}`
const deltaTone = (value) => Number(value) >= 0 ? 'positive' : 'negative'
const platformInitial = (value) => ({ YANDEX_DIRECT: 'Я', VK_ADS: 'VK', AVITO_ADS: 'A' })[value] || '?'

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data: response } = await api.get('/admin/dashboard/overview')
    data.value = response
  } catch (err) {
    error.value = apiError(err)
  } finally {
    loading.value = false
  }
}
onMounted(load)
</script>
