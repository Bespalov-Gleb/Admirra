<template>
  <div class="relative z-[2] flex min-h-full flex-col overflow-hidden px-[25px] py-[30px]">
    <div v-if="loading" class="flex justify-center py-24 text-[rgba(105,105,105,0.56)] text-sm font-medium dark:text-white/55">
      Загрузка тарифов…
    </div>

    <template v-else>
      <!-- Section header -->
      <div class="pt-[15px] pb-[15px] mb-[10px]">
        <h3 class="text-[30px] font-semibold leading-none text-[#171717] dark:text-white">Тарифы</h3>
      </div>
      <p class="text-[15px] font-medium text-[rgba(105,105,105,0.56)] dark:text-white/55 mb-[25px]">
        Выберите подходящий тариф в зависимости от количества проектов и задач аналитики
      </p>

      <!-- Billing period tabs -->
      <div class="flex pb-[30px]">
        <div class="flex gap-[20px]">
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
      <div :key="billingPeriod" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-[30px]">
        <!-- Старт -->
        <div class="plan-card dark:!bg-[#2C2F3D] dark:!border dark:!border-white/10">
          <div class="flex flex-col h-full" style="row-gap:25px">
            <h4 class="flex items-center gap-[15px] text-[20px] font-semibold leading-none text-[#171717] dark:!text-white/90">
              <span class="two-circles"></span>
              Старт
            </h4>
            <div>
              <div class="text-[50px] font-semibold leading-none text-[#171717] mb-[10px] dark:!text-white/90">
                {{ currentPrice(resolvedPlans.start) }}
              </div>
              <div class="text-[15px] font-light text-[rgba(105,105,105,0.56)] dark:!text-white/55">
                {{ currentPerProject(resolvedPlans.start) }}
              </div>
            </div>
            <ul class="flex-1">
              <li v-for="item in planBullets(resolvedPlans.start)" :key="item" class="feature-row">
                <span class="feature-dot"></span>
                <span class="text-[15px] text-[#5f5f5f] leading-[1.12] dark:!text-white/75">{{ item }}</span>
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
              <p class="text-[12px] text-center" style="padding:15px 0 12px">
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
            style="background:url('/admirra/img/pattern.png') center/77px"
          ></div>
          <div class="relative z-10 flex flex-col h-full" style="row-gap:25px">
            <h4 class="flex items-center gap-[15px] text-[20px] font-semibold leading-none text-white">
              <span class="two-circles two-circles--light"></span>
              Базовый
            </h4>
            <div>
              <div class="text-[50px] font-semibold leading-none text-white mb-[10px]">
                {{ currentPrice(resolvedPlans.basic) }}
              </div>
              <div class="text-[15px] font-light text-[#fbfbfb]">
                {{ currentPerProject(resolvedPlans.basic) }}
              </div>
            </div>
            <ul class="flex-1">
              <li v-for="item in planBullets(resolvedPlans.basic)" :key="item" class="feature-row feature-row--white">
                <span class="feature-dot feature-dot--white"></span>
                <span class="text-[15px] text-white leading-[1.12]">{{ item }}</span>
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
              <p class="text-[12px] text-center text-white font-semibold" style="padding:15px 0 12px">
                14 дней бесплатно — подключение за&nbsp;5&nbsp;минут
              </p>
            </div>
          </div>
        </div>

        <!-- Стандартный -->
        <div class="plan-card dark:!bg-[#2C2F3D] dark:!border dark:!border-white/10">
          <div class="flex flex-col h-full" style="row-gap:25px">
            <h4 class="flex items-center gap-[15px] text-[20px] font-semibold leading-none text-[#171717] dark:!text-white/90">
              <span class="two-circles"></span>
              Стандартный
            </h4>
            <div>
              <div class="text-[50px] font-semibold leading-none text-[#171717] mb-[10px] dark:!text-white/90">
                {{ currentPrice(resolvedPlans.standard) }}
              </div>
              <div class="text-[15px] font-light text-[rgba(105,105,105,0.56)] dark:!text-white/55">
                {{ currentPerProject(resolvedPlans.standard) }}
              </div>
            </div>
            <ul class="flex-1">
              <li v-for="item in planBullets(resolvedPlans.standard)" :key="item" class="feature-row">
                <span class="feature-dot"></span>
                <span class="text-[15px] text-[#5f5f5f] leading-[1.12] dark:!text-white/75">{{ item }}</span>
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
              <p class="text-[12px] text-center" style="padding:15px 0 12px">
                <span class="gradient-text font-semibold">{{ trialPhrase(resolvedPlans.standard.trial_days) }}</span>
                &nbsp;— подключение за&nbsp;5&nbsp;минут
              </p>
            </div>
          </div>
        </div>
      </div>
      </Transition>

      <!-- White Label -->
      <div class="wl-card bg-white rounded-[30px] p-[30px] dark:!bg-[#2C2F3D] dark:!border dark:!border-white/10">
        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          <!-- About -->
          <div class="pr-[30px] flex flex-col gap-[20px]">
            <div class="flex items-start gap-[17px]">
              <span class="two-circles" style="margin-top:4px"></span>
              <h4 class="text-[20px] font-semibold leading-[1.3] text-[#171717] dark:!text-white/90">
                White Label —<br />
                персонализация<br />
                кабинета и&nbsp;отчетности
              </h4>
            </div>
            <ul class="font-medium">
              <li v-for="item in wlFeatures" :key="item" class="feature-row">
                <span class="feature-dot"></span>
                <span class="text-[15px] text-[#5f5f5f] leading-[1.12] dark:!text-white/75">{{ item }}</span>
              </li>
            </ul>
          </div>

          <!-- UI preview -->
          <div class="flex items-center justify-center" style="margin:-10px 0 0 -20px">
            <img
              src="/admirra/img/white-label/ui.png"
              alt="White Label UI"
              class="block"
              style="width:400px;height:350px;object-fit:contain"
            />
          </div>

          <!-- Action -->
          <div class="flex flex-col" style="padding:8px 0 0 40px">
            <div class="mb-[16px]">
              <div class="text-[50px] font-semibold leading-none text-[#171717] mb-[10px] dark:!text-white/90">25&nbsp;900&nbsp;₽</div>
              <div class="text-[15px] font-light text-[rgba(105,105,105,0.56)] dark:!text-white/55">259 руб/проект</div>
            </div>
            <p class="text-[15px] text-[rgba(105,105,105,0.56)] max-w-[200px] pt-[10px] mb-[45px] dark:!text-white/55">
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

function currentPrice(plan) {
  const p = billingPeriod.value === 'year'
    ? yearlyPriceFromMonthly(plan.price_rub)
    : plan.price_rub
  return formatRub(p)
}

function currentPerProject(plan) {
  const p = billingPeriod.value === 'year'
    ? yearlyPriceFromMonthly(plan.price_rub)
    : plan.price_rub
  return perProjectLine(p, plan.max_projects)
}

function planBullets(plan) {
  return [
    projectBullet(plan),
    channelsBullet(plan.code),
    usersBullet(plan.code),
    aiBullet(plan),
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
  if (!localStorage.getItem('auth_token')) return
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
  column-gap: 10px;
  min-height: 46px;
  padding: 10px 18px;
  font-size: 13px;
  font-weight: 600;
  border: none;
  border-radius: 12px;
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
  font-size: 10px;
  line-height: 1.1;
  background: linear-gradient(270deg, #06b5d4 0.35%, #1f9de4 32.08%, #2563eb 96.51%);
  padding: 5px 10px;
  border-radius: 40px;
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
  padding: 32px 30px;
  border-radius: 30px;
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
  width: 18px;
  height: 12px;
  position: relative;
  flex-shrink: 0;
}
.two-circles::before,
.two-circles::after {
  content: '';
  width: 12px;
  height: 12px;
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
  column-gap: 10px;
  padding: 17px 0 18px;
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
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background-color: #2563eb;
  box-shadow: 0 0 0 3px #f5f7f9;
  flex-shrink: 0;
  margin: 4px;
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
  background: #fff;
  border-radius: 1px;
}
.feature-dot::before { width: 4px; height: 1px; }
.feature-dot::after  { width: 1px; height: 4px; }
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
  min-height: 46px;
  padding: 0 17px;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.1;
  color: #fff;
  border: none;
  border-radius: 12px;
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
  border-radius: 12px;
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
  min-height: 46px;
  padding: 0 17px;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.1;
  border: none;
  border-radius: 12px;
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
