<template>
  <div class="relative z-[2] flex min-h-full flex-col overflow-x-hidden px-[1.7361rem] py-[2.0833rem]">
    <div v-if="loading" class="flex justify-center py-24 text-[rgba(105,105,105,0.56)] text-sm font-medium dark:text-white/55">
      Загрузка тарифов…
    </div>

    <template v-else>
      <!-- Section header -->
      <div class="pt-[1.0417rem] pb-[1.0417rem] mb-[0.6944rem]">
        <h3 class="text-[2.0833rem] font-semibold leading-none text-[#171717] dark:text-white">Тарифы</h3>
      </div>
      <p class="text-[1.0417rem] font-medium text-[rgba(105,105,105,0.56)] dark:text-white/55 mb-[1.7361rem]">
        Выберите подходящий тариф в зависимости от количества проектов и задач аналитики
      </p>

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
        <div class="plan-card dark:!bg-[#2C2F3D] dark:!border dark:!border-white/10">
          <div class="flex flex-col h-full" style="row-gap:1.7361rem">
            <h4 class="flex items-center gap-[1.0417rem] text-[1.3889rem] font-semibold leading-none text-[#171717] dark:!text-white/90">
              <span class="two-circles"></span>
              Старт
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
                :disabled="paying === resolvedPlans.start.code"
                @click="onSubscribe(resolvedPlans.start.code, billingPeriod)"
              >
                <span class="relative z-[1]">
                  {{ paying === resolvedPlans.start.code ? 'Подождите…' : 'Перейти на тариф Старт' }}
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
        <div class="plan-card plan-card--primary">
          <div
            class="absolute inset-0 pointer-events-none z-0 opacity-25"
            style="background:url('/admirra/img/pattern.png') center/5.3472rem"
          ></div>
          <div class="relative z-10 flex flex-col h-full" style="row-gap:1.7361rem">
            <h4 class="flex items-center gap-[1.0417rem] text-[1.3889rem] font-semibold leading-none text-white">
              <span class="two-circles two-circles--light"></span>
              Базовый
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
                :disabled="paying === resolvedPlans.basic.code"
                @click="onSubscribe(resolvedPlans.basic.code, billingPeriod)"
              >
                <span class="gradient-text">
                  {{ paying === resolvedPlans.basic.code ? 'Подождите…' : 'Перейти на тариф Базовый' }}
                </span>
              </button>
              <p class="text-[0.8333rem] text-center text-white font-semibold" style="padding:1.0417rem 0 0.8333rem">
                14 дней бесплатно — подключение за&nbsp;5&nbsp;минут
              </p>
            </div>
          </div>
        </div>

        <!-- Стандартный -->
        <div class="plan-card dark:!bg-[#2C2F3D] dark:!border dark:!border-white/10">
          <div class="flex flex-col h-full" style="row-gap:1.7361rem">
            <h4 class="flex items-center gap-[1.0417rem] text-[1.3889rem] font-semibold leading-none text-[#171717] dark:!text-white/90">
              <span class="two-circles"></span>
              Стандартный
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
                :disabled="paying === resolvedPlans.standard.code"
                @click="onSubscribe(resolvedPlans.standard.code, billingPeriod)"
              >
                <span class="relative z-[1]">
                  {{ paying === resolvedPlans.standard.code ? 'Подождите…' : 'Перейти на тариф Стандарт' }}
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

      <!-- White Label -->
      <div class="wl-card bg-white rounded-[2.0833rem] p-[2.0833rem] dark:!bg-[#2C2F3D] dark:!border dark:!border-white/10">
        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          <!-- About -->
          <div class="pr-[2.0833rem] flex flex-col gap-[1.3889rem]">
            <div class="flex items-start gap-[1.1806rem]">
              <span class="two-circles" style="margin-top:0.2778rem"></span>
              <h4 class="text-[1.3889rem] font-semibold leading-[1.3] text-[#171717] dark:!text-white/90">
                White Label —<br />
                персонализация<br />
                кабинета и&nbsp;отчетности
              </h4>
            </div>
            <ul class="font-medium">
              <li v-for="item in wlFeatures" :key="item" class="feature-row">
                <span class="feature-dot"></span>
                <span class="text-[1.0417rem] text-[#5f5f5f] leading-[1.12] dark:!text-white/75">{{ item }}</span>
              </li>
            </ul>
          </div>

          <!-- UI preview -->
          <div class="flex items-center justify-center" style="margin:-0.6944rem 0 0 -1.3889rem">
            <img
              src="/admirra/img/white-label/ui.png"
              alt="White Label UI"
              class="block"
              style="width:27.7778rem;height:24.3056rem;object-fit:contain"
            />
          </div>

          <!-- Action -->
          <div class="flex flex-col" style="padding:0.5556rem 0 0 2.7778rem">
            <div class="mb-[1.1111rem]">
              <div class="text-[3.4722rem] font-semibold leading-none text-[#171717] mb-[0.6944rem] dark:!text-white/90">25&nbsp;900&nbsp;₽</div>
              <div class="text-[1.0417rem] font-light text-[rgba(105,105,105,0.56)] dark:!text-white/55">259 руб/проект</div>
            </div>
            <p class="text-[1.0417rem] text-[rgba(105,105,105,0.56)] max-w-[13.8889rem] pt-[0.6944rem] mb-[3.125rem] dark:!text-white/55">
              При покупке на год — возможны&nbsp;персональные скидки.
              Оставьте заявку, чтобы обсудить детали использования WL.
            </p>
            <div class="mt-auto">
              <button class="plan-btn w-full" @click="onContactWl">
                <span class="relative z-[1]">Перейти на тариф WL</span>
              </button>
            </div>
          </div>
        </div>
      </div>
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

const loading = ref(false)
const plans = ref(normalizePlansFromApi([]))
const paying = ref(null)
const billingPeriod = ref('month')

const resolvedPlans = computed(() => plans.value)

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
  return [
    display?.projects || projectBullet(plan),
    channelsBullet(plan.code),
    usersBullet(plan.code),
    display?.ai || aiBullet(plan),
    'Экспорт отчетов, отправка по расписанию',
  ]
}

const wlFeatures = [
  'Отчеты без логотипа сервиса',
  'Брендирование отчетов',
  'Использование платформы как собственной системы аналитики',
  'Собственный домен',
]

onMounted(async () => {
  if (!getAccessToken()) return
  try {
    const { data } = await api.get('billing/plans')
    plans.value = normalizePlansFromApi(data)
  } catch (e) {
    // keep fallback plans already set
  }
})

async function onSubscribe(planCode, bp = 'month') {
  paying.value = planCode
  try {
    const { data } = await api.post('billing/subscribe', {
      plan_code: planCode,
      billing_period: bp,
      success_url: `${window.location.origin}/tariffs`,
      fail_url: `${window.location.origin}/tariffs`,
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
  router.push('/contact')
}
</script>

<style scoped>
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
:global(.dark) .plan-btn-white,
:global(.darkmode) .plan-btn-white {
  background-color: rgba(255,255,255,0.92);
}
</style>
