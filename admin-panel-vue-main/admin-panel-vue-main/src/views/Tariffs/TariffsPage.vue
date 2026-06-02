<template>
  <div>
    <div v-if="loading" class="flex justify-center py-24 text-[rgba(105,105,105,0.56)] text-sm font-medium dark:text-white/55">
      Загрузка тарифов…
    </div>

    <template v-else>
      <div class="tariff-page-head">
        <h4 class="text-[1.6667rem] font-semibold leading-none text-[#171717] dark:text-white">Тариф и оплата</h4>
        <p class="text-[1.0417rem] font-medium text-[rgba(105,105,105,0.56)] dark:text-white/55">
          Управляйте текущей подпиской, лимитами и сменой тарифа
        </p>
      </div>

      <!-- Subscription state -->
      <section class="subscription-card">
        <div class="subscription-head">
          <div>
            <div class="subscription-title-row">
              <h5>Тариф «{{ subscription.plan_name || 'Старт' }}»</h5>
              <span class="subscription-status" :class="`subscription-status--${subscriptionStatusKey}`">{{ subscriptionStatusLabel }}</span>
              <span class="subscription-period">{{ planMetaLine }}</span>
              <span v-if="subscription.whitelabel_available" class="subscription-status subscription-status--wl">White Label</span>
            </div>
            <p class="subscription-renewal">
              <svg class="w-[1.0417rem] h-[1.0417rem]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 7V3m8 4V3M4 11h16M5 5h14a1 1 0 011 1v14a1 1 0 01-1 1H5a1 1 0 01-1-1V6a1 1 0 011-1Z"/></svg>
              {{ renewalText }}
            </p>
          </div>
          <button class="subscription-change-btn" type="button" @click="scrollToPlans">
            Изменить тариф
          </button>
        </div>

        <div class="usage-grid">
          <div v-for="item in subscriptionUsageTiles" :key="item.key" class="usage-tile" :class="`usage-tile--${item.theme}`">
            <div class="usage-tile__head">
              <span>{{ item.label }}</span>
              <i aria-hidden="true">{{ item.icon }}</i>
            </div>
            <div class="usage-tile__value">
              <strong>{{ item.used }}</strong>
              <span>/ {{ item.limit }}</span>
            </div>
            <div class="usage-tile__bar">
              <i :class="{ 'usage-tile__fill--warn': item.warn }" :style="{ width: item.percent + '%' }"></i>
            </div>
            <p>{{ item.caption }}</p>
          </div>
        </div>

        <div class="subscription-channel-row">
          <span>Доступные каналы:</span>
          <div class="channel-chip-list">
            <span v-for="channel in availableChannels" :key="channel.label" :class="['channel-chip', channel.className]">
              <img v-if="channel.icon" :src="channel.icon" alt="" />
              {{ channel.label }}
            </span>
          </div>
          <em>{{ currentPlanCode === 'start' ? 'Все каналы — от «Базового»' : 'Все каналы доступны' }}</em>
        </div>

        <div class="subscription-footer">
          <div class="payment-line" :class="{ 'payment-line--empty': !hasPaymentMethod }">
            <div class="payment-method">
              <span class="payment-card-icon"></span>
              <strong>{{ paymentMethodLabel }}</strong>
              <template v-if="hasPaymentMethod">
                <span>·</span>
                <span>{{ subscription.autorenew ? 'автопродление вкл.' : 'автопродление выкл.' }}</span>
              </template>
              <span v-else>· для автопродления</span>
            </div>
            <div class="subscription-footer-actions">
              <button type="button" disabled>{{ hasPaymentMethod ? 'Изменить карту' : 'Добавить карту' }}</button>
              <button v-if="hasPaymentMethod" type="button" disabled>{{ subscription.autorenew ? 'Отменить автопрод.' : 'Включить автопрод.' }}</button>
            </div>
          </div>
          <div class="documents-line" title="Будет позже">
            <span>Документы и оплата по счёту</span>
            <strong>Будет позже</strong>
          </div>
        </div>

        <div v-if="subscriptionStatusKey === 'past_due'" class="subscription-warning">
          Не удалось списать оплату. Обновите карту, чтобы сохранить доступ после грейс-периода.
        </div>
        <div v-else-if="subscriptionStatusKey === 'trial' || !hasPaymentMethod" class="subscription-note">
          После окончания пробного периода подписка продолжится по выбранному тарифу.
        </div>
        <div v-else-if="subscription.autorenew" class="subscription-note">
          {{ autorenewHint }}
        </div>

      </section>

      <div ref="plansAnchor" class="tariff-section-head">
        <div>
          <h4>Сменить тариф</h4>
          <p>Годовая подписка дает скидку 30%.</p>
        </div>
        <div class="billing-switch">
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
        <div :key="billingPeriod" class="figma-plan-grid">
          <article class="figma-plan-card figma-plan-card--start" :class="{ 'figma-plan-card--current': isCurrentPlan(resolvedPlans.start) }">
            <img src="/admirra/img/tariffs/tariff-start.png" alt="Тариф Старт" loading="lazy" />
            <button
              class="figma-plan-hotspot figma-plan-hotspot--default"
              type="button"
              :aria-label="planButtonText(resolvedPlans.start)"
              :disabled="paying === resolvedPlans.start.code || isCurrentPlan(resolvedPlans.start)"
              @click="onSubscribe(resolvedPlans.start.code, billingPeriod)"
            ></button>
          </article>

          <article class="figma-plan-card figma-plan-card--basic" :class="{ 'figma-plan-card--current': isCurrentPlan(resolvedPlans.basic) }">
            <img src="/admirra/img/tariffs/tariff-basic.png" alt="Тариф Базовый" loading="lazy" />
            <button
              class="figma-plan-hotspot figma-plan-hotspot--basic"
              type="button"
              :aria-label="planButtonText(resolvedPlans.basic)"
              :disabled="paying === resolvedPlans.basic.code || isCurrentPlan(resolvedPlans.basic)"
              @click="onSubscribe(resolvedPlans.basic.code, billingPeriod)"
            ></button>
          </article>

          <article class="figma-plan-card figma-plan-card--standard" :class="{ 'figma-plan-card--current': isCurrentPlan(resolvedPlans.standard) }">
            <img src="/admirra/img/tariffs/tariff-standard.png" alt="Тариф Стандартный" loading="lazy" />
            <button
              class="figma-plan-hotspot figma-plan-hotspot--default"
              type="button"
              :aria-label="planButtonText(resolvedPlans.standard)"
              :disabled="paying === resolvedPlans.standard.code || isCurrentPlan(resolvedPlans.standard)"
              @click="onSubscribe(resolvedPlans.standard.code, billingPeriod)"
            ></button>
          </article>
        </div>
      </Transition>

      <!-- White Label -->
      <article class="figma-wl-card">
        <img src="/admirra/img/tariffs/tariff-whitelabel.png" alt="Тариф White Label" loading="lazy" />
        <button
          class="figma-wl-hotspot"
          type="button"
          :aria-label="subscription.whitelabel_available ? 'Настроить бренд' : 'Перейти на тариф WL'"
          @click="onContactWl"
        ></button>
      </article>

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
  max_users: 1,
  users_used: 1,
  max_staff: 1,
  max_clients: 0,
  max_ai_requests_per_period: 30,
  ai_requests_used: 0,
  ai_requests_remaining: 30,
  ai_reset_date: '',
  autorenew: true,
  whitelabel_available: false,
  payment_method: null,
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
  const suffix = days !== null ? ` · осталось ${days} дн.` : ''
  if (subscriptionStatusKey.value === 'trial') return date ? `Продлится ${date}${suffix}` : 'Триал активен'
  if (subscriptionStatusKey.value === 'canceled') return date ? `Доступ сохранится до ${date}` : 'Автопродление отключено'
  if (subscriptionStatusKey.value === 'past_due') return 'Не удалось списать оплату. Обновите способ оплаты.'
  return date ? `Продлится ${date}${suffix}` : 'Подписка активна'
})

const planMetaLine = computed(() => {
  const currentPeriod = subscription.value?.billing_period === 'year' ? 'year' : 'month'
  const period = currentPeriod === 'year' ? 'годовая' : 'помесячно'
  const price = currentPeriod === 'year'
    ? formatRub(yearlyPriceFromMonthly(currentPlan.value?.price_rub))
    : formatRub(currentPlan.value?.price_rub)
  return `${period} · ${price}/${currentPeriod === 'year' ? 'год' : 'мес'}`
})

const paymentMethodLabel = computed(() => {
  const method = subscription.value?.payment_method || {}
  const last4 = method.last4 || subscription.value?.payment_last4
  const exp = method.exp || method.expires || subscription.value?.payment_exp
  if (last4 && exp) return `•• ${last4} ${exp}`
  if (last4) return `•• ${last4}`
  return 'Карта не привязана'
})

const hasPaymentMethod = computed(() => {
  const method = subscription.value?.payment_method || {}
  return Boolean(method.last4 || subscription.value?.payment_last4)
})

const autorenewHint = computed(() => {
  const date = formatDate(subscription.value?.subscription_expires_at)
  const amount = currentPrice(currentPlan.value)
  if (!date) return 'Автопродление включено.'
  return `${date} спишется ${amount}.`
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
      theme: 'projects',
      icon: '▣',
      used: s.projects_used ?? 0,
      limit: s.max_projects ?? currentPlan.value?.max_projects ?? 1,
      caption: `${s.projects_used ?? 0} активных · ${s.paused_projects ?? 0} на паузе`,
    },
    {
      key: 'cabinets',
      label: 'Кабинеты',
      theme: 'cabinets',
      icon: '▤',
      used: s.cabinets_used ?? 0,
      limit: s.max_cabinets ?? 3,
      caption: 'Рекламные кабинеты и счётчики',
    },
    {
      key: 'ai',
      label: 'AI-запросы',
      theme: 'ai',
      icon: '✺',
      used: s.ai_requests_used ?? 0,
      limit: s.max_ai_requests_per_period ?? currentPlan.value?.max_ai_requests_per_period ?? 30,
      caption: s.ai_reset_date ? `Сброс ${s.ai_reset_date}` : 'Обновляется каждый период',
    },
    {
      key: 'users',
      label: 'Пользователи',
      theme: 'users',
      icon: '☷',
      used: s.users_used ?? 1,
      limit: s.max_users ?? s.max_staff ?? currentPlan.value?.max_users ?? currentPlan.value?.max_staff ?? 1,
      caption: `${s.users_used ?? 1} активный`,
    },
  ].map((item) => {
    const percent = usagePercent(item.used, item.limit)
    return { ...item, percent, warn: percent >= 85 }
  })
})

const availableChannels = computed(() => {
  const base = [
    { label: 'Yandex Direct', className: 'channel-chip--yd', icon: '/admirra/img/icons/yandex-direct.png' },
    { label: 'VK Ads Manager', className: 'channel-chip--vk', icon: '/admirra/img/icons/vk-ads.png' },
  ]
  if (currentPlanCode.value !== 'start') {
    base.push({ label: 'Метрика', className: 'channel-chip--yd', icon: '/admirra/img/integrations/yandex-metrika.png' })
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
    standard: { price: '9\u00A0990\u00A0₽', perProject: '333 руб/проект', projects: 'До 30 проектов', ai: '450 запросов AI' },
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
  'Отчёты без логотипа сервиса',
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

function onContactWl() {
  if (subscription.value?.whitelabel_available) {
    router.push('/settings?tab=brand')
    return
  }
  router.push('/contact')
}

</script>

<style scoped>
.tariff-page-head {
  margin: 0 0 1.5278rem;
}
.tariff-page-head p {
  margin: 0.6944rem 0 0;
}

.subscription-card {
  margin-bottom: 5.9722rem;
  padding: 1.6667rem 1.6667rem 1.4583rem;
  border: 1px solid rgba(0,0,0,0.05);
  border-radius: 1.25rem;
  background: rgba(255,255,255,0.92);
  box-shadow: 0 0.6944rem 2.0833rem rgba(15, 23, 42, 0.025), inset 0 0 0 1px rgba(255,255,255,0.75);
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
  margin-bottom: 1.5972rem;
}

.subscription-title-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.625rem;
}

.subscription-title-row h5 {
  margin: 0;
  color: #1f2937;
  font-size: 1.25rem;
  font-weight: 700;
  line-height: 1.1;
}
:global(.dark) .subscription-title-row h5,
:global(.darkmode) .subscription-title-row h5 { color: rgba(255,255,255,0.92); }

.subscription-renewal,
.tariff-section-head p {
  display: inline-flex;
  align-items: center;
  gap: 0.3472rem;
  margin: 0.6944rem 0 0;
  color: rgba(105,105,105,0.62);
  font-size: 0.9028rem;
  font-weight: 600;
}
:global(.dark) .subscription-renewal,
:global(.darkmode) .subscription-renewal,
:global(.dark) .tariff-section-head p,
:global(.darkmode) .tariff-section-head p { color: rgba(255,255,255,0.55); }

.subscription-status,
.plan-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.3472rem;
  min-height: 1.5972rem;
  padding: 0 0.7639rem;
  border-radius: 0.3472rem;
  font-size: 0.7639rem;
  font-weight: 700;
  white-space: nowrap;
}
.subscription-period {
  display: inline-flex;
  align-items: center;
  min-height: 1.5972rem;
  padding: 0 0.7639rem;
  border-radius: 0.3472rem;
  background: #f4f5f7;
  color: #9ca3af;
  font-size: 0.9028rem;
  font-weight: 700;
}
.subscription-status--active,
.subscription-status--wl,
.plan-badge--current {
  background: rgba(22, 163, 74, 0.12);
  color: #15803d;
}
.subscription-status--trial {
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
  border: 1px solid rgba(37, 99, 235, 0.22);
  border-radius: 0.8333rem;
  background: #fff;
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
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1.25rem;
  margin-bottom: 1.25rem;
}
.usage-tile {
  min-width: 0;
  min-height: 8.2639rem;
  padding: 1.3194rem 1.5278rem;
  border-radius: 1rem;
  background: #f5f7f9;
}
:global(.dark) .usage-tile,
:global(.darkmode) .usage-tile { background: rgba(255,255,255,0.06); }
.usage-tile--projects { background: #fff3df; }
.usage-tile--cabinets { background: #edf5ff; }
.usage-tile--ai { background: #fff0f2; }
.usage-tile--users { background: #f4e9ff; }
.usage-tile__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.6944rem;
  color: #64748b;
  font-size: 0.9722rem;
  font-weight: 700;
}
.usage-tile__head i {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.0833rem;
  height: 2.0833rem;
  border-radius: 0.3472rem;
  background: rgba(255, 255, 255, 0.56);
  color: #2563eb;
  font-size: 0.8333rem;
  font-style: normal;
  line-height: 1;
}
.usage-tile--projects .usage-tile__head i { color: #d97706; }
.usage-tile--cabinets .usage-tile__head i { color: #3b82f6; }
.usage-tile--ai .usage-tile__head i { color: #e2546d; }
.usage-tile--users .usage-tile__head i { color: #9b6ed3; }
.usage-tile__value {
  display: flex;
  align-items: baseline;
  gap: 0.4167rem;
  margin-top: 0.3472rem;
}
.usage-tile__value strong {
  color: #171717;
  font-size: 1.9444rem;
  line-height: 1;
}
.usage-tile__value span {
  color: #9ca3af;
  font-size: 1.1111rem;
  font-weight: 700;
}
:global(.dark) .usage-tile__head,
:global(.darkmode) .usage-tile__head { color: rgba(255,255,255,0.56); }
:global(.dark) .usage-tile__value strong,
:global(.darkmode) .usage-tile__value strong { color: rgba(255,255,255,0.9); }
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
.usage-tile--projects .usage-tile__bar i { background: #f7b267; }
.usage-tile--cabinets .usage-tile__bar i { background: #70a8e8; }
.usage-tile--ai .usage-tile__bar i { background: #e9a1ad; }
.usage-tile--users .usage-tile__bar i { background: #b49ad2; }
.usage-tile__fill--warn { background: #f59e0b !important; }
.usage-tile p {
  margin: 0.4861rem 0 0;
  color: rgba(105,105,105,0.58);
  font-size: 0.8333rem;
  font-weight: 700;
}
:global(.dark) .usage-tile p,
:global(.darkmode) .usage-tile p { color: rgba(255,255,255,0.42); }

.subscription-channel-row {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 0.9722rem;
  min-height: 2.9167rem;
  margin-bottom: 1.25rem;
  padding: 0.625rem 1.5278rem;
  border-radius: 0.8333rem;
  background: #f4f6f8;
}
:global(.dark) .subscription-channel-row,
:global(.darkmode) .subscription-channel-row { background: rgba(255,255,255,0.05); }
.subscription-channel-row > span {
  color: #696969;
  font-size: 0.9028rem;
  font-weight: 700;
}
.subscription-channel-row em {
  color: #9ca3af;
  font-size: 0.8333rem;
  font-style: normal;
  font-weight: 700;
  text-align: right;
}

.subscription-footer {
  display: grid;
  gap: 0.7639rem;
  padding-top: 1.25rem;
  border-top: 1px solid rgba(15,23,42,0.06);
}
:global(.dark) .subscription-footer,
:global(.darkmode) .subscription-footer { border-top-color: rgba(255,255,255,0.08); }
.payment-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  min-height: 3.6111rem;
}
.payment-line--empty .payment-card-icon {
  background: linear-gradient(90deg, #e5e7eb 0 35%, #f5f7f9 35% 100%);
}
.payment-line--empty .payment-method strong {
  color: #9ca3af;
}
.payment-method {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: 0.4167rem;
  color: #4b5563;
  font-size: 0.9028rem;
  font-weight: 700;
}
.payment-method strong {
  color: #1f2937;
  font-weight: 800;
}
.payment-card-icon {
  width: 1.1806rem;
  height: 0.625rem;
  border-radius: 2rem;
  background: linear-gradient(90deg, #7fa0f0 0 42%, #dce6ff 42% 100%);
  box-shadow: inset 0 0 0 1px rgba(37,99,235,0.12);
  flex-shrink: 0;
}
.subscription-footer-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.625rem;
  flex-wrap: wrap;
}
.subscription-footer-actions button {
  min-height: 3.3333rem;
  padding: 0 1.25rem;
  border: none;
  border-radius: 0.8333rem;
  background: #2563eb;
  color: #fff;
  font-size: 0.9028rem;
  font-weight: 800;
  cursor: not-allowed;
}
.documents-line {
  display: flex;
  align-items: center;
  gap: 0.6944rem;
  color: #c7ced8;
  font-size: 0.9028rem;
  font-weight: 700;
  opacity: 0.72;
  cursor: not-allowed;
}
.documents-line strong {
  padding: 0.3472rem 0.8333rem;
  border-radius: 2.7778rem;
  background: rgba(245,247,249,0.85);
  color: #d1d5db;
  font-size: 0.7639rem;
}
.subscription-note,
.subscription-warning {
  margin-top: 0.1389rem;
  padding: 0.9028rem 1.5278rem;
  border-radius: 0.8333rem;
  color: #64748b;
  background: #f4f6f8;
  font-size: 0.9028rem;
  font-weight: 700;
}
.subscription-warning {
  color: #b45309;
  background: rgba(245,158,11,0.12);
}
:global(.dark) .payment-method,
:global(.darkmode) .payment-method,
:global(.dark) .subscription-channel-row > span,
:global(.darkmode) .subscription-channel-row > span { color: rgba(255,255,255,0.64); }
:global(.dark) .payment-method strong,
:global(.darkmode) .payment-method strong { color: rgba(255,255,255,0.9); }
:global(.dark) .subscription-footer-actions button,
:global(.darkmode) .subscription-footer-actions button {
  border-color: rgba(255,255,255,0.10);
  background: rgba(255,255,255,0.06);
  color: rgba(255,255,255,0.7);
}
:global(.dark) .subscription-note,
:global(.darkmode) .subscription-note { background: rgba(255,255,255,0.05); color: rgba(255,255,255,0.54); }

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
  gap: 0.3472rem;
  min-height: 1.8056rem;
  padding: 0 0.625rem;
  border-radius: 0.5556rem;
  font-size: 0.7639rem;
  font-weight: 700;
}
.channel-chip img {
  width: 0.9722rem;
  height: 0.9722rem;
  object-fit: contain;
  flex-shrink: 0;
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
  margin-bottom: 1.7361rem;
}
.tariff-section-head h4 {
  margin: 0;
  color: #171717;
  font-size: 1.6667rem;
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

.billing-switch {
  display: inline-flex;
  align-items: center;
  gap: 0.5556rem;
  min-height: 3.1944rem;
  padding: 0.2778rem;
  border-radius: 1rem;
  background: rgba(255,255,255,0.86);
  box-shadow: inset 0 0 0 1px rgba(15,23,42,0.05);
}
:global(.dark) .billing-switch,
:global(.darkmode) .billing-switch {
  background: rgba(255,255,255,0.06);
  box-shadow: inset 0 0 0 1px rgba(255,255,255,0.08);
}

/* ── Tab switcher ── */
.tab-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  column-gap: 0.6944rem;
  min-height: 2.6389rem;
  padding: 0.5556rem 1.0417rem;
  font-size: 0.9028rem;
  font-weight: 600;
  border: none;
  border-radius: 0.7639rem;
  background-color: transparent;
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

/* Figma tariff cards */
.figma-plan-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1.7361rem;
  align-items: start;
  margin-bottom: 1.6667rem;
  overflow: visible;
}
.figma-plan-card {
  position: relative;
  display: flex;
  justify-content: center;
  height: clamp(34rem, 35vw, 43.6111rem);
  overflow: visible;
}
.figma-plan-card img {
  display: block;
  width: auto;
  height: 100%;
  max-width: none;
  object-fit: contain;
  pointer-events: none;
  user-select: none;
}
.figma-plan-card--basic {
  z-index: 1;
}
.figma-plan-card--basic img {
  transform: translateX(-0.9722rem);
}
.figma-plan-hotspot,
.figma-wl-hotspot {
  position: absolute;
  border: 0;
  padding: 0;
  background: transparent;
  cursor: pointer;
  border-radius: 0.8333rem;
}
.figma-plan-hotspot:focus-visible,
.figma-wl-hotspot:focus-visible {
  outline: 3px solid rgba(37, 99, 235, 0.45);
  outline-offset: 2px;
}
.figma-plan-hotspot:disabled {
  cursor: default;
}
.figma-plan-hotspot--default {
  left: 7.5%;
  right: 7.5%;
  bottom: 5.7%;
  height: 8.1%;
}
.figma-plan-hotspot--basic {
  left: 5.2%;
  width: 55.8%;
  bottom: 5.2%;
  height: 7.9%;
}
.figma-wl-card {
  position: relative;
  display: block;
  width: 100%;
  margin: 0;
  border-radius: 2rem;
  overflow: hidden;
  background: #fff;
}
.figma-wl-card img {
  display: block;
  width: 100%;
  height: auto;
  pointer-events: none;
  user-select: none;
}
.figma-wl-hotspot {
  right: 2.5%;
  bottom: 10.6%;
  width: 28.3%;
  height: 12.7%;
}

/* ── Plan cards ── */
.plan-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 2.0833rem;
  margin-bottom: 2.0833rem;
}
.plan-card {
  height: 100%;
  background-color: #fff;
  min-height: 43.6111rem;
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
  min-height: 3.6806rem;
  padding: 1.1111rem 0;
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

.wl-card__badge {
  display: inline-flex;
  align-items: center;
  min-height: 1.8056rem;
  padding: 0 0.6944rem;
  border-radius: 2.7778rem;
  background: rgba(37,99,235,0.08);
  color: #2563eb;
  font-size: 0.7639rem;
  font-weight: 800;
  margin-bottom: 0.6944rem;
}

.wl-card {
  overflow: hidden;
}
.wl-card__grid {
  display: grid;
  grid-template-columns: minmax(17rem, 1.05fr) minmax(18rem, 1fr) minmax(16rem, 0.86fr);
  gap: 2.0833rem;
  align-items: stretch;
}
.wl-card__content {
  display: flex;
  flex-direction: column;
  gap: 1.3889rem;
  min-width: 0;
}
.wl-card__preview {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 20.8333rem;
  margin: -0.6944rem 0;
  border-radius: 1.3889rem;
  background: linear-gradient(180deg, rgba(245,247,249,0.85), rgba(236,243,254,0.35));
}
.wl-card__preview img {
  display: block;
  width: min(100%, 27.7778rem);
  height: 24.3056rem;
  object-fit: contain;
}
.wl-card__aside {
  display: flex;
  flex-direction: column;
  min-width: 0;
  padding: 0.5556rem 0 0;
}
.wl-card__badge--active {
  background: rgba(0,255,78,0.10);
  color: #16a34a;
}
:global(.dark) .wl-card__badge,
:global(.darkmode) .wl-card__badge {
  background: rgba(74,122,255,0.14);
  color: #8fb0ff;
}
:global(.dark) .wl-card__badge--active,
:global(.darkmode) .wl-card__badge--active {
  background: rgba(0,255,78,0.13);
  color: #5ee886;
}

@media (max-width: 1024px) {
  .usage-grid,
  .figma-plan-grid,
  .plan-grid,
  .wl-card__grid { grid-template-columns: 1fr; }
  .subscription-card {
    margin-bottom: 3.125rem;
  }
  .subscription-head,
  .subscription-row,
  .payment-line,
  .subscription-channel-row {
    align-items: flex-start;
    flex-direction: column;
  }
  .subscription-channel-row {
    display: flex;
  }
  .channel-chip-list,
  .subscription-muted-action,
  .subscription-footer-actions {
    justify-content: flex-start;
  }
  .tariff-section-head {
    align-items: flex-start;
    flex-direction: column;
  }
  .billing-switch {
    width: 100%;
    justify-content: space-between;
  }
  .tab-btn {
    flex: 1;
  }
  .plan-card {
    min-height: auto;
  }
  .figma-plan-card {
    height: auto;
    min-height: 0;
  }
  .figma-plan-card img {
    width: min(100%, 28rem);
    height: auto;
  }
  .figma-plan-card--basic img {
    width: min(100%, 32rem);
    transform: none;
  }
  .figma-plan-hotspot--default {
    left: 11%;
    right: 11%;
  }
  .figma-plan-hotspot--basic {
    left: 15%;
    width: 70%;
  }
  .figma-wl-card {
    border-radius: 1.25rem;
    overflow-x: auto;
  }
  .figma-wl-card img {
    min-width: 48rem;
  }
  .wl-card__preview {
    min-height: 15.2778rem;
  }
  .wl-card__preview img {
    height: 17.3611rem;
  }
}

@media (min-width: 1025px) and (max-width: 1480px) {
  .usage-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .plan-grid {
    gap: 1.0417rem;
  }
  .figma-plan-grid {
    gap: 1rem;
  }
  .figma-plan-card {
    height: clamp(30rem, 34vw, 38.5rem);
  }
  .wl-card__grid {
    grid-template-columns: minmax(16rem, 1fr) minmax(15rem, 0.9fr);
  }
  .wl-card__aside {
    grid-column: 1 / -1;
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(16rem, 0.7fr);
    align-items: end;
    gap: 1.3889rem;
  }
}
</style>
