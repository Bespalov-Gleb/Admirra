<template>
  <div>
    <div v-if="loading" class="flex justify-center py-24 text-[rgba(105,105,105,0.56)] text-sm font-medium dark:text-white/55">
      Загрузка тарифов…
    </div>

    <template v-else>
      <div class="mb-[0.6944rem]">
        <h4 class="text-[1.6667rem] font-semibold leading-none text-[#171717] dark:text-white">Тариф и оплата</h4>
      </div>
      <p class="text-[1.0417rem] font-medium text-[rgba(105,105,105,0.56)] dark:text-white/55 mb-[1.7361rem]">
        Управляйте текущей подпиской, лимитами и сменой тарифа
      </p>

      <!-- Subscription state -->
      <section class="subscription-card">
        <div class="subscription-head">
          <div>
            <div class="subscription-eyebrow">Подписка</div>
            <div class="subscription-title-row">
              <h5>{{ subscription.plan_name || 'Старт' }}</h5>
              <span class="subscription-status" :class="`subscription-status--${subscriptionStatusKey}`">{{ subscriptionStatusLabel }}</span>
              <span v-if="subscription.whitelabel_available" class="subscription-status subscription-status--wl">White Label</span>
            </div>
            <p>{{ renewalText }}</p>
          </div>
          <button class="subscription-change-btn" type="button" @click="scrollToPlans">
            Изменить тариф
          </button>
        </div>

        <div class="usage-grid">
          <div v-for="item in subscriptionUsageTiles" :key="item.key" class="usage-tile">
            <div class="usage-tile__top">
              <span>{{ item.label }}</span>
              <strong>{{ item.used }} / {{ item.limit }}</strong>
            </div>
            <div class="usage-tile__bar">
              <i :class="{ 'usage-tile__fill--warn': item.warn }" :style="{ width: item.percent + '%' }"></i>
            </div>
            <p>{{ item.caption }}</p>
          </div>
        </div>

        <div class="subscription-rows">
          <div class="subscription-row">
            <span>Доступные каналы</span>
            <div class="channel-chip-list">
              <span v-for="channel in availableChannels" :key="channel.label" :class="['channel-chip', channel.className]">{{ channel.label }}</span>
              <em v-if="currentPlanCode === 'start'">все каналы — от Базового</em>
            </div>
          </div>
          <div class="subscription-row">
            <span>Способ оплаты</span>
            <div class="subscription-muted-action">
              <strong>Карта не привязана</strong>
              <button type="button" disabled>Изменить карту</button>
            </div>
          </div>
          <div class="subscription-row">
            <span>Автопродление</span>
            <div class="subscription-muted-action">
              <strong>{{ subscription.autorenew ? 'Включено' : 'Отключено' }}</strong>
              <button type="button" disabled>{{ subscription.autorenew ? 'Отключить' : 'Включить' }}</button>
            </div>
          </div>
          <div class="subscription-row subscription-row--disabled" title="Будет позже">
            <span>Документы и оплата по счёту</span>
            <strong>будет позже</strong>
          </div>
        </div>
      </section>

      <div ref="plansAnchor" class="tariff-section-head">
        <div>
          <h4>Сменить тариф</h4>
          <p>Годовая оплата даёт скидку 30%.</p>
        </div>
      </div>

      <!-- Billing period tabs -->
      <div class="flex pb-[2.0833rem]">
        <div class="flex gap-[1.3889rem]">
          <button
            class="tab-btn"
            :class="billingPeriod === 'month'
              ? 'tab-btn--active dark:!bg-[#2563eb] dark:!text-white'
              : 'dark:!bg-[#2C2F3D] dark:!text-white/75 dark:!shadow-[inset_0_0_0_1px_rgba(255,255,255,0.08)] dark:hover:!bg-white/10'"
            @click="billingPeriod = 'month'"
          >
            Месяц
          </button>
          <button
            class="tab-btn"
            :class="billingPeriod === 'year'
              ? 'tab-btn--active dark:!bg-[#2563eb] dark:!text-white'
              : 'dark:!bg-[#2C2F3D] dark:!text-white/75 dark:!shadow-[inset_0_0_0_1px_rgba(255,255,255,0.08)] dark:hover:!bg-white/10'"
            @click="billingPeriod = 'year'"
          >
            <span>Год</span>
            <span class="tab-badge" :class="{ 'tab-badge--active': billingPeriod === 'year' }">
              Экономия 30%
            </span>
          </button>
        </div>
      </div>

      <!-- Tariff cards -->
      <Transition name="tab-fade" mode="out-in">
      <div :key="billingPeriod" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-[2.0833rem]">
        <!-- Старт -->
        <div class="plan-card dark:!bg-[#2C2F3D] dark:!border dark:!border-white/10" :class="{ 'plan-card--current': isCurrentPlan(resolvedPlans.start) }">
          <div class="flex flex-col h-full" style="row-gap:1.7361rem">
            <h4 class="flex items-center gap-[1.0417rem] text-[1.3889rem] font-semibold leading-none text-[#171717] dark:!text-white/90">
              <span class="two-circles"></span>
              Старт
              <span v-if="isCurrentPlan(resolvedPlans.start)" class="plan-badge plan-badge--current">Текущий</span>
            </h4>
            <div>
              <div class="text-[3.4722rem] font-semibold leading-none text-[#171717] mb-[0.6944rem] dark:!text-white/90">
                {{ currentPrice(resolvedPlans.start) }}
              </div>
              <div class="text-[1.0417rem] font-light text-[rgba(105,105,105,0.56)] dark:!text-white/55">
                {{ currentPerProject(resolvedPlans.start) }}
              </div>
            </div>
            <ul class="flex-1">
              <li v-for="item in planBullets(resolvedPlans.start)" :key="item" class="feature-row">
                <span class="feature-dot"></span>
                <span class="text-[1.0417rem] text-[#5f5f5f] leading-[1.12] dark:!text-white/75">{{ item }}</span>
              </li>
            </ul>
            <div>
              <button
                class="plan-btn w-full"
                :class="{ 'plan-btn--current': isCurrentPlan(resolvedPlans.start) }"
                :disabled="paying === resolvedPlans.start.code || isCurrentPlan(resolvedPlans.start)"
                @click="onSubscribe(resolvedPlans.start.code, billingPeriod)"
              >
                <span class="relative z-[1]">
                  {{ planButtonText(resolvedPlans.start) }}
                </span>
              </button>
              <p class="text-[0.8333rem] text-center" style="padding:1.0417rem 0 0.8333rem">
                <span class="gradient-text font-semibold">{{ trialPhrase(resolvedPlans.start.trial_days) }}</span>
                &nbsp;— подключение за&nbsp;5&nbsp;минут
              </p>
            </div>
          </div>
        </div>

        <!-- Базовый (primary) -->
        <div class="plan-card plan-card--primary" :class="{ 'plan-card--current': isCurrentPlan(resolvedPlans.basic) }">
          <div
            class="absolute inset-0 pointer-events-none z-0 opacity-25"
            style="background:url('/admirra/img/pattern.png') center/5.3472rem"
          ></div>
          <div class="relative z-10 flex flex-col h-full" style="row-gap:1.7361rem">
            <h4 class="flex items-center gap-[1.0417rem] text-[1.3889rem] font-semibold leading-none text-white">
              <span class="two-circles two-circles--light"></span>
              Базовый
              <span v-if="isCurrentPlan(resolvedPlans.basic)" class="plan-badge plan-badge--current plan-badge--light">Текущий</span>
              <span v-else class="plan-badge plan-badge--popular">Популярный</span>
            </h4>
            <div>
              <div class="text-[3.4722rem] font-semibold leading-none text-white mb-[0.6944rem]">
                {{ currentPrice(resolvedPlans.basic) }}
              </div>
              <div class="text-[1.0417rem] font-light text-[#fbfbfb]">
                {{ currentPerProject(resolvedPlans.basic) }}
              </div>
            </div>
            <ul class="flex-1">
              <li v-for="item in planBullets(resolvedPlans.basic)" :key="item" class="feature-row feature-row--white">
                <span class="feature-dot feature-dot--white"></span>
                <span class="text-[1.0417rem] text-white leading-[1.12]">{{ item }}</span>
              </li>
            </ul>
            <div>
              <button
                class="plan-btn-white w-full"
                :class="{ 'plan-btn-white--current': isCurrentPlan(resolvedPlans.basic) }"
                :disabled="paying === resolvedPlans.basic.code || isCurrentPlan(resolvedPlans.basic)"
                @click="onSubscribe(resolvedPlans.basic.code, billingPeriod)"
              >
                <span class="gradient-text">
                  {{ planButtonText(resolvedPlans.basic) }}
                </span>
              </button>
              <p class="text-[0.8333rem] text-center text-white font-semibold" style="padding:1.0417rem 0 0.8333rem">
                14 дней бесплатно — подключение за&nbsp;5&nbsp;минут
              </p>
            </div>
          </div>
        </div>

        <!-- Стандартный -->
        <div class="plan-card dark:!bg-[#2C2F3D] dark:!border dark:!border-white/10" :class="{ 'plan-card--current': isCurrentPlan(resolvedPlans.standard) }">
          <div class="flex flex-col h-full" style="row-gap:1.7361rem">
            <h4 class="flex items-center gap-[1.0417rem] text-[1.3889rem] font-semibold leading-none text-[#171717] dark:!text-white/90">
              <span class="two-circles"></span>
              Стандартный
              <span v-if="isCurrentPlan(resolvedPlans.standard)" class="plan-badge plan-badge--current">Текущий</span>
            </h4>
            <div>
              <div class="text-[3.4722rem] font-semibold leading-none text-[#171717] mb-[0.6944rem] dark:!text-white/90">
                {{ currentPrice(resolvedPlans.standard) }}
              </div>
              <div class="text-[1.0417rem] font-light text-[rgba(105,105,105,0.56)] dark:!text-white/55">
                {{ currentPerProject(resolvedPlans.standard) }}
              </div>
            </div>
            <ul class="flex-1">
              <li v-for="item in planBullets(resolvedPlans.standard)" :key="item" class="feature-row">
                <span class="feature-dot"></span>
                <span class="text-[1.0417rem] text-[#5f5f5f] leading-[1.12] dark:!text-white/75">{{ item }}</span>
              </li>
            </ul>
            <div>
              <button
                class="plan-btn w-full"
                :class="{ 'plan-btn--current': isCurrentPlan(resolvedPlans.standard) }"
                :disabled="paying === resolvedPlans.standard.code || isCurrentPlan(resolvedPlans.standard)"
                @click="onSubscribe(resolvedPlans.standard.code, billingPeriod)"
              >
                <span class="relative z-[1]">
                  {{ planButtonText(resolvedPlans.standard) }}
                </span>
              </button>
              <p class="text-[0.8333rem] text-center" style="padding:1.0417rem 0 0.8333rem">
                <span class="gradient-text font-semibold">{{ trialPhrase(resolvedPlans.standard.trial_days) }}</span>
                &nbsp;— подключение за&nbsp;5&nbsp;минут
              </p>
            </div>
          </div>
        </div>
      </div>
      </Transition>

      <section class="wl-card wl-card--premium" :class="{ 'wl-card--locked': !subscription.whitelabel_available }">
        <div class="wl-card__content">
          <div>
            <div class="wl-card__badge">
              <svg v-if="!subscription.whitelabel_available" class="w-[0.8333rem] h-[0.8333rem]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.4"><rect x="3" y="11" width="18" height="10" rx="2"/><path d="M7 11V7a5 5 0 0110 0v4"/></svg>
              {{ subscription.whitelabel_available ? 'Подключено' : 'Премиальная функция' }}
            </div>
            <h4>White Label для агентства</h4>
            <p>
              Логотип, фирменный цвет, подпись PDF и собственный домен для отчётов. Настройка живёт в отдельной вкладке «Бренд / White Label».
            </p>
          </div>
          <ul>
            <li v-for="item in wlFeatures" :key="item">{{ item }}</li>
          </ul>
          <button class="wl-card__button" type="button" @click="router.push('/settings')">
            {{ subscription.whitelabel_available ? 'Настроить бренд' : 'Посмотреть White Label' }}
          </button>
        </div>
      </section>

    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api/axios'
import { useAuth } from '@/composables/useAuth'
import { useToaster } from '@/composables/useToaster'
import { payWithCloudPayments } from '@/composables/useBillingCloudPayments'
import { getAccessToken } from '@/utils/authToken'
import {
  normalizePlansFromApi,
  yearlyPriceFromMonthly,
  formatRub,
  perProjectLine,
  projectBullet,
  channelsBullet,
  usersBullet,
  aiBullet,
  trialPhrase,
} from '@/utils/pricingPlans'

const router = useRouter()
const toaster = useToaster()
const { fetchCurrentUser } = useAuth()

const loading = ref(true)
const plans = ref(normalizePlansFromApi([]))
const paying = ref(null)
const billingPeriod = ref('month')
const plansAnchor = ref(null)
const subscription = ref({
  plan_code: 'start',
  plan_name: 'Старт',
  status: 'trial',
  billing_period: 'month',
  subscription_expires_at: null,
  max_projects: 1,
  projects_used: 0,
  paused_projects: 0,
  max_cabinets: 3,
  cabinets_used: 0,
  max_ai_requests_per_period: 30,
  ai_requests_used: 0,
  ai_requests_remaining: 30,
  ai_reset_date: '',
  autorenew: true,
  whitelabel_available: false,
})

const resolvedPlans = computed(() => plans.value)
const currentPlanCode = computed(() => String(subscription.value?.plan_code || 'start').toLowerCase())
const currentPlan = computed(() => resolvedPlans.value[currentPlanCode.value] || resolvedPlans.value.start)
const subscriptionStatusKey = computed(() => String(subscription.value?.status || 'trial').toLowerCase())
const subscriptionStatusLabel = computed(() => ({
  active: 'Активна',
  trial: 'Пробная',
  past_due: 'Просрочена',
  canceled: 'Отменена',
  expired: 'Истекла',
})[subscriptionStatusKey.value] || 'Пробная')

const formatDate = (iso) => {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleDateString('ru-RU')
}

const daysLeft = computed(() => {
  if (!subscription.value?.subscription_expires_at) return null
  const end = new Date(subscription.value.subscription_expires_at)
  if (Number.isNaN(end.getTime())) return null
  return Math.max(0, Math.ceil((end.getTime() - Date.now()) / 86400000))
})

const renewalText = computed(() => {
  const date = formatDate(subscription.value?.subscription_expires_at)
  const days = daysLeft.value
  const suffix = days !== null ? `, осталось ${days} дн.` : ''
  if (subscriptionStatusKey.value === 'trial') return date ? `Триал до ${date}${suffix}` : 'Триал активен'
  if (subscriptionStatusKey.value === 'canceled') return date ? `Доступ сохранится до ${date}` : 'Автопродление отключено'
  if (subscriptionStatusKey.value === 'past_due') return 'Не удалось списать оплату. Обновите способ оплаты.'
  return date ? `Следующее продление ${date}${suffix}` : 'Подписка активна'
})

const usagePercent = (used, limit) => {
  const safeLimit = Math.max(Number(limit) || 0, 1)
  return Math.min(100, Math.round(((Number(used) || 0) / safeLimit) * 100))
}

const subscriptionUsageTiles = computed(() => {
  const s = subscription.value || {}
  return [
    {
      key: 'projects',
      label: 'Проекты',
      used: s.projects_used ?? 0,
      limit: s.max_projects ?? currentPlan.value?.max_projects ?? 1,
      caption: `${s.projects_used ?? 0} активных · ${s.paused_projects ?? 0} на паузе`,
    },
    {
      key: 'cabinets',
      label: 'Кабинеты',
      used: s.cabinets_used ?? 0,
      limit: s.max_cabinets ?? 3,
      caption: 'Рекламные кабинеты и счётчики',
    },
    {
      key: 'ai',
      label: 'AI-запросы',
      used: s.ai_requests_used ?? 0,
      limit: s.max_ai_requests_per_period ?? currentPlan.value?.max_ai_requests_per_period ?? 30,
      caption: s.ai_reset_date ? `Сброс ${s.ai_reset_date}` : 'Обновляется каждый период',
    },
  ].map((item) => {
    const percent = usagePercent(item.used, item.limit)
    return { ...item, percent, warn: percent >= 85 }
  })
})

const availableChannels = computed(() => {
  const base = [
    { label: 'Яндекс Директ', className: 'channel-chip--yd' },
    { label: 'VK Реклама', className: 'channel-chip--vk' },
  ]
  if (currentPlanCode.value !== 'start') {
    base.push({ label: 'Метрика', className: 'channel-chip--yd' })
    base.push({ label: 'MyTarget', className: 'channel-chip--mt' })
  }
  return base
})

const isCurrentPlan = (plan) => String(plan?.code || '').toLowerCase() === currentPlanCode.value
const planButtonText = (plan) => {
  if (isCurrentPlan(plan)) return 'Подключён'
  if (paying.value === plan?.code) return 'Подождите…'
  return `Перейти на тариф ${plan?.name || ''}`.trim()
}

const scrollToPlans = () => {
  plansAnchor.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const landingTariffDisplay = {
  month: {
    start: { price: '1\u00A0590\u00A0₽', perProject: '1590 руб/проект', projects: '1 проект', ai: '30 запросов AI' },
    basic: { price: '3\u00A0990\u00A0₽', perProject: '798 руб/проект', projects: '5 проектов', ai: '120 запросов AI' },
    standard: { price: '9\u00A0990\u00A0₽', perProject: '660 руб/проект', projects: '15 проектов', ai: '450 запросов AI' },
  },
  year: {
    start: { price: '11\u00A0590\u00A0₽', perProject: '1590 руб/проект', projects: '1 проект', ai: '30 запросов AI' },
    basic: { price: '31\u00A0990\u00A0₽', perProject: '498 руб/проект', projects: 'До 8 проектов', ai: '120 запросов AI' },
    standard: { price: '69\u00A0990\u00A0₽', perProject: '333 руб/проект', projects: 'До 30 проектов', ai: '450 запросов AI' },
  },
}

function landingDisplay(plan) {
  const code = String(plan?.code || '').toLowerCase()
  return landingTariffDisplay[billingPeriod.value]?.[code] || null
}

function currentPrice(plan) {
  const display = landingDisplay(plan)
  if (display?.price) return display.price
  const p = billingPeriod.value === 'year'
    ? yearlyPriceFromMonthly(plan.price_rub)
    : plan.price_rub
  return formatRub(p)
}

function currentPerProject(plan) {
  const display = landingDisplay(plan)
  if (display?.perProject) return display.perProject
  const p = billingPeriod.value === 'year'
    ? yearlyPriceFromMonthly(plan.price_rub)
    : plan.price_rub
  return perProjectLine(p, plan.max_projects)
}

function planBullets(plan) {
  const display = landingDisplay(plan)
  const code = String(plan?.code || '').toLowerCase()
  const bullets = [
    display?.projects || projectBullet(plan),
    channelsBullet(plan.code),
    usersBullet(plan.code),
    display?.ai || aiBullet(plan),
    'Экспорт отчетов, отправка по расписанию',
  ]
  if (code === 'standard') {
    bullets.push('White Label (бренд в отчётах)')
  }
  return bullets
}

const wlFeatures = [
  'Логотип агентства в отчётах',
  'Фирменный цвет и подпись PDF',
  'Собственный домен для ссылок',
  'Премиальный вид клиентских материалов',
]

onMounted(async () => {
  if (!getAccessToken()) {
    loading.value = false
    return
  }
  loading.value = true
  try {
    const [plansRes, subscriptionRes] = await Promise.allSettled([
      api.get('billing/plans'),
      api.get('billing/subscription'),
    ])
    if (plansRes.status === 'fulfilled') {
      plans.value = normalizePlansFromApi(plansRes.value.data)
    }
    if (subscriptionRes.status === 'fulfilled') {
      subscription.value = { ...subscription.value, ...subscriptionRes.value.data }
      billingPeriod.value = subscription.value.billing_period === 'year' ? 'year' : 'month'
    }
  } catch (e) {
    // keep fallback plans already set
  } finally {
    loading.value = false
  }
})

async function onSubscribe(planCode, bp = 'month') {
  paying.value = planCode
  try {
    const { data } = await api.post('billing/subscribe', {
      plan_code: planCode,
      billing_period: bp,
      success_url: `${window.location.origin}/settings?tab=tariff`,
      fail_url: `${window.location.origin}/settings?tab=tariff`,
    })
    const result = await payWithCloudPayments({
      public_id: data.public_id,
      description: data.description,
      amount: data.amount,
      currency: data.currency,
      account_id: data.account_id,
      email: data.email,
      plan_code: data.plan_code,
      billing_period: data.billing_period || bp,
      recurrent: data.recurrent || null,
    })
    if (result.status === 'cancelled') return
    toaster.success('Оплата успешно выполнена')
    await fetchCurrentUser()
  } catch (e) {
    const d = e?.response?.data?.detail
    const msg = typeof d === 'string' ? d : e?.message
    if (msg) toaster.error(msg || 'Не удалось начать оплату')
  } finally {
    paying.value = null
  }
}

</script>

<style scoped>
.subscription-card {
  margin-bottom: 2.0833rem;
  padding: 1.7361rem;
  border: 1px solid rgba(0,0,0,0.05);
  border-radius: 1.3889rem;
  background: #fff;
  box-shadow: 0 0.6944rem 2.0833rem rgba(15, 23, 42, 0.035);
}
:global(.dark) .subscription-card,
:global(.darkmode) .subscription-card {
  background: #2C2F3D;
  border-color: rgba(255,255,255,0.08);
  box-shadow: 0 4px 24px rgba(0,0,0,0.28), inset 0 1px 0 rgba(255,255,255,0.07);
}

.subscription-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1.3889rem;
  margin-bottom: 1.3889rem;
}

.subscription-eyebrow {
  margin-bottom: 0.4861rem;
  color: rgba(105,105,105,0.58);
  font-size: 0.8333rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}

.subscription-title-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.625rem;
}

.subscription-title-row h5 {
  margin: 0;
  color: #171717;
  font-size: 1.5278rem;
  font-weight: 700;
  line-height: 1.1;
}
:global(.dark) .subscription-title-row h5,
:global(.darkmode) .subscription-title-row h5 { color: rgba(255,255,255,0.92); }

.subscription-head p,
.tariff-section-head p {
  margin: 0.4861rem 0 0;
  color: rgba(105,105,105,0.62);
  font-size: 0.9722rem;
  font-weight: 500;
}
:global(.dark) .subscription-head p,
:global(.darkmode) .subscription-head p,
:global(.dark) .tariff-section-head p,
:global(.darkmode) .tariff-section-head p { color: rgba(255,255,255,0.55); }

.subscription-status,
.plan-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.3472rem;
  min-height: 1.7361rem;
  padding: 0 0.6944rem;
  border-radius: 2.7778rem;
  font-size: 0.7639rem;
  font-weight: 700;
  white-space: nowrap;
}
.subscription-status--active,
.subscription-status--trial,
.subscription-status--wl,
.plan-badge--current {
  background: rgba(37,99,235,0.10);
  color: #2563eb;
}
.subscription-status--past_due,
.subscription-status--canceled,
.subscription-status--expired {
  background: rgba(245,158,11,0.14);
  color: #b45309;
}
.plan-badge--popular {
  background: rgba(255,255,255,0.20);
  color: #fff;
}
.plan-badge--light {
  background: rgba(255,255,255,0.22);
  color: #fff;
}

.subscription-change-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 3.0556rem;
  padding: 0 1.1806rem;
  border: 1px solid #dbe5ff;
  border-radius: 0.8333rem;
  background: #f8fbff;
  color: #2563eb;
  font-size: 0.9028rem;
  font-weight: 700;
  white-space: nowrap;
  cursor: pointer;
}
.subscription-change-btn:hover { background: #ecf3fe; }
:global(.dark) .subscription-change-btn,
:global(.darkmode) .subscription-change-btn {
  border-color: rgba(74,122,255,0.3);
  background: rgba(74,122,255,0.12);
  color: #8fb0ff;
}

.usage-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.8333rem;
  margin-bottom: 1.0417rem;
}
.usage-tile {
  min-width: 0;
  padding: 1.0417rem;
  border-radius: 1.0417rem;
  background: #f5f7f9;
}
:global(.dark) .usage-tile,
:global(.darkmode) .usage-tile { background: rgba(255,255,255,0.06); }
.usage-tile__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.6944rem;
  color: #696969;
  font-size: 0.9028rem;
  font-weight: 600;
}
.usage-tile__top strong {
  color: #171717;
  font-size: 1.1111rem;
}
:global(.dark) .usage-tile__top,
:global(.darkmode) .usage-tile__top { color: rgba(255,255,255,0.56); }
:global(.dark) .usage-tile__top strong,
:global(.darkmode) .usage-tile__top strong { color: rgba(255,255,255,0.9); }
.usage-tile__bar {
  height: 0.4167rem;
  margin-top: 0.7639rem;
  overflow: hidden;
  border-radius: 1rem;
  background: rgba(37,99,235,0.10);
}
.usage-tile__bar i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(270deg, #06b5d4 0.35%, #1f9de4 32.08%, #2563eb 96.51%);
}
.usage-tile__bar .usage-tile__fill--warn { background: #f59e0b; }
.usage-tile p {
  margin: 0.5556rem 0 0;
  color: rgba(105,105,105,0.58);
  font-size: 0.8333rem;
}
:global(.dark) .usage-tile p,
:global(.darkmode) .usage-tile p { color: rgba(255,255,255,0.42); }

.subscription-rows {
  display: grid;
  gap: 0.625rem;
}
.subscription-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  min-height: 3.3333rem;
  padding: 0.625rem 0.8333rem;
  border-radius: 0.8333rem;
  background: #fafbfc;
}
:global(.dark) .subscription-row,
:global(.darkmode) .subscription-row { background: rgba(255,255,255,0.04); }
.subscription-row > span {
  color: #696969;
  font-size: 0.9028rem;
  font-weight: 600;
}
:global(.dark) .subscription-row > span,
:global(.darkmode) .subscription-row > span { color: rgba(255,255,255,0.62); }
.subscription-row--disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.channel-chip-list,
.subscription-muted-action {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 0.4861rem;
  min-width: 0;
}
.channel-chip-list em {
  color: rgba(105,105,105,0.48);
  font-size: 0.7639rem;
  font-style: normal;
}
.channel-chip {
  display: inline-flex;
  align-items: center;
  min-height: 1.8056rem;
  padding: 0 0.625rem;
  border-radius: 0.5556rem;
  font-size: 0.7639rem;
  font-weight: 700;
}
.channel-chip--yd { background: #fff3db; color: #9a5a0a; }
.channel-chip--vk { background: #e6f2ff; color: #1f5f9f; }
.channel-chip--mt { background: #edf7f1; color: #167147; }
.subscription-muted-action strong,
.subscription-row strong {
  color: #171717;
  font-size: 0.9028rem;
}
:global(.dark) .subscription-muted-action strong,
:global(.darkmode) .subscription-muted-action strong,
:global(.dark) .subscription-row strong,
:global(.darkmode) .subscription-row strong { color: rgba(255,255,255,0.82); }
.subscription-muted-action button {
  min-height: 2.0833rem;
  padding: 0 0.6944rem;
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: 0.5556rem;
  background: #fff;
  color: rgba(105,105,105,0.48);
  font-size: 0.7639rem;
  cursor: not-allowed;
}

.tariff-section-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.25rem;
}
.tariff-section-head h4 {
  margin: 0;
  color: #171717;
  font-size: 1.3889rem;
  font-weight: 700;
}
:global(.dark) .tariff-section-head h4,
:global(.darkmode) .tariff-section-head h4 { color: rgba(255,255,255,0.92); }

/* ── Tab content fade transition ── */
.tab-fade-enter-active {
  transition: opacity 0.5s ease-in;
}
.tab-fade-leave-active {
  transition: opacity 0.3s ease-out;
}
.tab-fade-enter-from,
.tab-fade-leave-to {
  opacity: 0;
}

/* ── Tab switcher ── */
.tab-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  column-gap: 0.6944rem;
  min-height: 3.1944rem;
  padding: 0.6944rem 1.25rem;
  font-size: 0.9028rem;
  font-weight: 600;
  border: none;
  border-radius: 0.8333rem;
  background-color: #fff;
  color: #5f5f5f;
  cursor: pointer;
  transition: color 0.3s, background-color 0.3s;
}
.tab-btn:hover { color: #2563eb; }
:global(.dark) .tab-btn {
  background-color: rgba(255,255,255,0.08);
  color: rgba(255,255,255,0.72);
}
:global(.dark) .tab-btn:hover {
  color: #4A7AFF;
}
.tab-btn--active {
  background-color: #2563eb;
  color: #fff;
}
.tab-btn--active:hover { color: #fff; }
:global(.dark) .tab-btn--active {
  background-color: #2563eb;
  color: #fff;
}

.tab-badge {
  font-size: 0.6944rem;
  line-height: 1.1;
  background: linear-gradient(270deg, #06b5d4 0.35%, #1f9de4 32.08%, #2563eb 96.51%);
  padding: 0.3472rem 0.6944rem;
  border-radius: 2.7778rem;
  color: #fff;
  transition: background 0.3s, color 0.3s;
}
.tab-badge--active {
  background: #fff;
  color: #2563eb;
}

/* ── Plan cards ── */
.plan-card {
  height: 100%;
  background-color: #fff;
  padding: 2.2222rem 2.0833rem;
  border-radius: 2.0833rem;
  position: relative;
  overflow: hidden;
  border: 1px solid transparent;
}
:global(.dark) .plan-card:not(.plan-card--primary),
:global(.darkmode) .plan-card:not(.plan-card--primary),
:global(.dark) .wl-card,
:global(.darkmode) .wl-card {
  background-color: #2C2F3D;
  border: 1px solid rgba(255,255,255,0.08);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.28), inset 0 1px 0 rgba(255, 255, 255, 0.07);
}
:global(.dark) .plan-card:not(.plan-card--primary) :not(.gradient-text),
:global(.darkmode) .plan-card:not(.plan-card--primary) :not(.gradient-text),
:global(.dark) .wl-card :not(.gradient-text),
:global(.darkmode) .wl-card :not(.gradient-text) {
  color: rgba(255,255,255,0.84) !important;
}
:global(.dark) .plan-card:not(.plan-card--primary) .text-\[rgba\(105\,105\,105\,0\.56\)\],
:global(.darkmode) .plan-card:not(.plan-card--primary) .text-\[rgba\(105\,105\,105\,0\.56\)\],
:global(.dark) .wl-card .text-\[rgba\(105\,105\,105\,0\.56\)\],
:global(.darkmode) .wl-card .text-\[rgba\(105\,105\,105\,0\.56\)\] {
  color: rgba(255,255,255,0.55) !important;
}
.plan-card--primary {
  background: linear-gradient(270deg, #06b5d4 0.35%, #1f9de4 32.08%, #2563eb 96.51%);
}
.plan-card--current {
  border-color: rgba(37,99,235,0.42) !important;
  box-shadow: 0 0 0 0.2083rem rgba(37,99,235,0.08), 0 1rem 2.5rem rgba(15,23,42,0.06);
}

/* ── Two-circles icon ── */
.two-circles {
  display: inline-block;
  width: 1.25rem;
  height: 0.8333rem;
  position: relative;
  flex-shrink: 0;
}
.two-circles::before,
.two-circles::after {
  content: '';
  width: 0.8333rem;
  height: 0.8333rem;
  border-radius: 50%;
  position: absolute;
  top: 0;
}
.two-circles::before { background-color: #bccbf7; left: 0; }
.two-circles::after  { background-color: #5171d0; right: 0; }
.two-circles--light::before { background-color: rgba(255, 255, 255, 0.5); }
.two-circles--light::after  { background-color: #fff; }

/* ── Feature list ── */
.feature-row {
  display: flex;
  align-items: flex-start;
  column-gap: 0.6944rem;
  padding: 1.1806rem 0 1.25rem;
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
  list-style: none;
}
:global(.dark) .plan-card:not(.plan-card--primary) .feature-row,
:global(.darkmode) .plan-card:not(.plan-card--primary) .feature-row,
:global(.dark) .wl-card .feature-row,
:global(.darkmode) .wl-card .feature-row {
  border-bottom-color: rgba(255,255,255,0.10);
}
.feature-row:last-child { border-bottom: 0; }
.feature-row--white { border-bottom-color: rgba(255, 255, 255, 0.13); }

/* ── Feature dot (circle with + ) ── */
.feature-dot {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 0.6944rem;
  height: 0.6944rem;
  border-radius: 50%;
  background-color: #2563eb;
  box-shadow: 0 0 0 3px #f5f7f9;
  flex-shrink: 0;
  margin: 0.2778rem;
  position: relative;
}
:global(.dark) .plan-card:not(.plan-card--primary) .feature-dot,
:global(.darkmode) .plan-card:not(.plan-card--primary) .feature-dot,
:global(.dark) .wl-card .feature-dot,
:global(.darkmode) .wl-card .feature-dot {
  box-shadow: 0 0 0 3px rgba(255,255,255,0.08);
}
.feature-dot::before,
.feature-dot::after {
  content: '';
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  background: #fff;
  border-radius: 1px;
}
.feature-dot::before { width: 0.2778rem; height: 1px; }
.feature-dot::after  { width: 1px; height: 0.2778rem; }
.feature-dot--white  { box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.25); }

/* ── Gradient text ── */
.gradient-text {
  background: linear-gradient(270deg, #06b5d4 0.35%, #1f9de4 32.08%, #2563eb 96.51%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* ── Plan button (gradient) ── */
.plan-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 3.1944rem;
  padding: 0 1.1806rem;
  font-size: 0.9028rem;
  font-weight: 500;
  line-height: 1.1;
  color: #fff;
  border: none;
  border-radius: 0.8333rem;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  background: linear-gradient(270deg, #06b5d4 0.35%, #1f9de4 32.08%, #2563eb 96.51%);
  transition: transform 0.75s;
}
.plan-btn::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 0.8333rem;
  background: linear-gradient(270deg, #38e1ff 0.35%, #4abeff 32.08%, #5187ff 96.51%);
  opacity: 0;
  transition: opacity 1s;
}
.plan-btn:hover { transform: scale(1.03); }
.plan-btn:hover::after { opacity: 1; }
.plan-btn:active { transform: scale(0.97); transition: transform 0s; }
.plan-btn:disabled { opacity: 0.7; cursor: not-allowed; transform: none; }
.plan-btn--current {
  background: #eef4ff;
  color: #2563eb;
}
.plan-btn--current::after { display: none; }
:global(.dark) .plan-btn--current,
:global(.darkmode) .plan-btn--current {
  background: rgba(74,122,255,0.12);
  color: #8fb0ff;
}

/* ── Plan button white (for primary card) ── */
.plan-btn-white {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 3.1944rem;
  padding: 0 1.1806rem;
  font-size: 0.9028rem;
  font-weight: 500;
  line-height: 1.1;
  border: none;
  border-radius: 0.8333rem;
  cursor: pointer;
  background: #fff;
  transition: background-color 0.5s, transform 0.75s;
}
.plan-btn-white:hover {
  background-color: #5187ff;
  transform: scale(1.03);
}
.plan-btn-white:hover .gradient-text {
  background: none;
  -webkit-text-fill-color: #fff;
}
.plan-btn-white:active { transform: scale(0.97); transition: transform 0s; }
.plan-btn-white:disabled { opacity: 0.7; cursor: not-allowed; transform: none; }
.plan-btn-white--current .gradient-text {
  background: none;
  -webkit-text-fill-color: #2563eb;
  color: #2563eb;
}
:global(.dark) .plan-btn-white,
:global(.darkmode) .plan-btn-white {
  background-color: rgba(255,255,255,0.92);
}

.wl-card--premium {
  padding: 1.7361rem;
  border-radius: 1.3889rem;
  border: 1px solid rgba(37,99,235,0.14);
  background:
    radial-gradient(circle at 12% 20%, rgba(6,181,212,0.18), transparent 28%),
    linear-gradient(135deg, #ffffff 0%, #f7fbff 58%, #eef5ff 100%);
}
:global(.dark) .wl-card--premium,
:global(.darkmode) .wl-card--premium {
  border-color: rgba(74,122,255,0.18);
  background:
    radial-gradient(circle at 12% 20%, rgba(74,122,255,0.20), transparent 28%),
    #2C2F3D;
}
.wl-card--locked {
  box-shadow: inset 0 0 0 1px rgba(255,255,255,0.4), 0 1rem 2.5rem rgba(15,23,42,0.04);
}
.wl-card__content {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(14rem, 0.85fr) auto;
  align-items: center;
  gap: 1.3889rem;
}
.wl-card__badge {
  display: inline-flex;
  align-items: center;
  gap: 0.4167rem;
  min-height: 1.9444rem;
  padding: 0 0.7639rem;
  border-radius: 2.7778rem;
  background: rgba(37,99,235,0.10);
  color: #2563eb;
  font-size: 0.7639rem;
  font-weight: 800;
  margin-bottom: 0.6944rem;
}
.wl-card__content h4 {
  margin: 0;
  color: #171717;
  font-size: 1.5278rem;
  font-weight: 800;
}
.wl-card__content p {
  margin: 0.5556rem 0 0;
  color: rgba(105,105,105,0.66);
  font-size: 0.9722rem;
  line-height: 1.45;
}
.wl-card__content ul {
  display: grid;
  gap: 0.4861rem;
  margin: 0;
  padding: 0;
  list-style: none;
}
.wl-card__content li {
  position: relative;
  padding-left: 1.1111rem;
  color: #4b5563;
  font-size: 0.9028rem;
  font-weight: 600;
}
.wl-card__content li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0.45em;
  width: 0.4167rem;
  height: 0.4167rem;
  border-radius: 50%;
  background: #2563eb;
}
.wl-card__button {
  min-height: 3.0556rem;
  padding: 0 1.25rem;
  border: 0;
  border-radius: 0.8333rem;
  background: linear-gradient(270deg, #06b5d4 0.35%, #1f9de4 32.08%, #2563eb 96.51%);
  color: #fff;
  font-size: 0.9028rem;
  font-weight: 800;
  white-space: nowrap;
  cursor: pointer;
}
.wl-card__button:hover { transform: translateY(-1px); }
:global(.dark) .wl-card__content h4,
:global(.darkmode) .wl-card__content h4 { color: rgba(255,255,255,0.92); }
:global(.dark) .wl-card__content p,
:global(.darkmode) .wl-card__content p { color: rgba(255,255,255,0.56); }
:global(.dark) .wl-card__content li,
:global(.darkmode) .wl-card__content li { color: rgba(255,255,255,0.74); }

@media (max-width: 1024px) {
  .usage-grid,
  .wl-card__content {
    grid-template-columns: 1fr;
  }
  .subscription-head,
  .subscription-row {
    align-items: flex-start;
    flex-direction: column;
  }
  .channel-chip-list,
  .subscription-muted-action {
    justify-content: flex-start;
  }
}
</style>
