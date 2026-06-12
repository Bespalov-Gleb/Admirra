<template>
  <div class="tariffs-page">
    <div v-if="loading" class="tariffs-loading">
      Загрузка тарифов...
    </div>

    <template v-else>
      <div class="tariff-page-head">
        <h4>Тариф и оплата</h4>
        <p>Управляйте текущей подпиской, лимитами и сменой тарифа</p>
      </div>

      <section class="subscription-card">
        <div class="subscription-head">
          <div>
            <div class="subscription-title-row">
              <h5>Тариф «{{ subscription.plan_name || 'Старт' }}»</h5>
              <span class="subscription-status" :class="`subscription-status--${subscriptionStatusKey}`">
                {{ subscriptionStatusLabel }}
              </span>
              <span class="subscription-period">{{ planMetaLine }}</span>
              <span v-if="subscription.whitelabel_available" class="subscription-status" style="background:#e8f4ff;color:#2563eb">White Label</span>
            </div>
            <p class="subscription-renewal">
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M0.5 6.52894C0.5 4.13566 0.5 2.93902 1.24349 2.19552C1.98699 1.45203 3.18363 1.45203 5.57691 1.45203H8.11536C10.5086 1.45203 11.7053 1.45203 12.4488 2.19552C13.1923 2.93902 13.1923 4.13566 13.1923 6.52894V7.79816C13.1923 10.1914 13.1923 11.3881 12.4488 12.1316C11.7053 12.8751 10.5086 12.8751 8.11536 12.8751H5.57691C3.18363 12.8751 1.98699 12.8751 1.24349 12.1316C0.5 11.3881 0.5 10.1914 0.5 7.79816V6.52894Z" stroke="#696969" stroke-opacity="0.56"/><path d="M3.67285 1.45192V0.5" stroke="#696969" stroke-opacity="0.56" stroke-linecap="round"/><path d="M10.0188 1.45192V0.5" stroke="#696969" stroke-opacity="0.56" stroke-linecap="round"/><path d="M0.817139 4.625H12.8748" stroke="#696969" stroke-opacity="0.56" stroke-linecap="round"/><path d="M10.654 9.702C10.654 10.0525 10.3699 10.3366 10.0194 10.3366C9.66888 10.3366 9.38477 10.0525 9.38477 9.702C9.38477 9.3515 9.66888 9.06738 10.0194 9.06738C10.3699 9.06738 10.654 9.3515 10.654 9.702Z" fill="#696969" fill-opacity="0.56"/><path d="M10.654 7.16342C10.654 7.51392 10.3699 7.79804 10.0194 7.79804C9.66888 7.79804 9.38477 7.51392 9.38477 7.16342C9.38477 6.81293 9.66888 6.52881 10.0194 6.52881C10.3699 6.52881 10.654 6.81293 10.654 7.16342Z" fill="#696969" fill-opacity="0.56"/><path d="M7.48016 9.702C7.48016 10.0525 7.19605 10.3366 6.84555 10.3366C6.49505 10.3366 6.21094 10.0525 6.21094 9.702C6.21094 9.3515 6.49505 9.06738 6.84555 9.06738C7.19605 9.06738 7.48016 9.3515 7.48016 9.702Z" fill="#696969" fill-opacity="0.56"/><path d="M7.48016 7.16342C7.48016 7.51392 7.19605 7.79804 6.84555 7.79804C6.49505 7.79804 6.21094 7.51392 6.21094 7.16342C6.21094 6.81293 6.49505 6.52881 6.84555 6.52881C7.19605 6.52881 7.48016 6.81293 7.48016 7.16342Z" fill="#696969" fill-opacity="0.56"/><path d="M4.30731 9.702C4.30731 10.0525 4.02318 10.3366 3.6727 10.3366C3.32222 10.3366 3.03809 10.0525 3.03809 9.702C3.03809 9.3515 3.32222 9.06738 3.6727 9.06738C4.02318 9.06738 4.30731 9.3515 4.30731 9.702Z" fill="#696969" fill-opacity="0.56"/><path d="M4.30731 7.16342C4.30731 7.51392 4.02318 7.79804 3.6727 7.79804C3.32222 7.79804 3.03809 7.51392 3.03809 7.16342C3.03809 6.81293 3.32222 6.52881 3.6727 6.52881C4.02318 6.52881 4.30731 6.81293 4.30731 7.16342Z" fill="#696969" fill-opacity="0.56"/></svg>
              <span v-html="renewalText"></span>
            </p>
          </div>
          <button class="subscription-change-btn" type="button" @click="scrollToPlans">
            Изменить тариф
          </button>
        </div>

        <div class="usage-grid">
          <article
            v-for="item in subscriptionUsageTiles"
            :key="item.key"
            class="usage-tile"
            :class="`usage-tile--${item.key}`"
          >
            <div class="usage-tile__head">
              <span>{{ item.label }}</span>
              <i aria-hidden="true" v-html="item.icon"></i>
            </div>
            <div class="usage-tile__value">
              <strong>{{ item.used }}</strong>
              <span>/ {{ item.limit }}</span>
            </div>
            <div class="usage-tile__bar">
              <i :style="{ width: `${item.percent}%` }"></i>
            </div>
            <p>{{ item.caption }}</p>
          </article>
        </div>

        <div class="subscription-channel-row">
          <span>Доступные каналы:</span>
          <div class="channel-chip-list">
            <span v-for="channel in availableChannels" :key="channel.label" :class="['channel-chip', channel.className]" :style="{ color: channel.color }">
              <img v-if="channel.icon" :src="channel.icon" alt="" />
              {{ channel.label }}
            </span>
          </div>
          <em>{{ currentPlanCode === 'start' ? 'Все каналы от «Базового»' : 'Все каналы доступны' }}</em>
        </div>

        <div class="subscription-footer">
          <div class="payment-line" :class="{ 'payment-line--empty': !hasPaymentMethod }">
            <div class="payment-method">
              <svg width="21" height="11" viewBox="0 0 21 11" fill="none" class="flex-shrink-0"><rect x="0.35" y="0.35" width="20.3" height="10.3" rx="5.15" fill="#F5F7F9" stroke="#CDDAFF" stroke-width="0.7"/><circle v-if="hasPaymentMethod" cx="15.5" cy="5.5" r="5.5" fill="#9AB2FB"/><circle v-else cx="5.5" cy="5.5" r="5.5" fill="#9AB2FB"/></svg>
              <strong>{{ hasPaymentMethod ? 'Карта привязана' : 'Карта не привязана' }}</strong>
              <template v-if="hasPaymentMethod">
                <span class="payment-brand">{{ cardBrandLabel }}</span>
                <span class="payment-mask">**** **** **** {{ paymentLast4 }}</span>
                <span class="payment-exp">{{ paymentExp }}</span>
              </template>
            </div>

            <div v-if="hasPaymentMethod" class="payment-renewal">Автопродление вкл.</div>

            <div class="subscription-footer-actions">
              <button type="button" disabled>{{ hasPaymentMethod ? 'Изменить карту' : 'Добавить карту' }}</button>
              <button v-if="hasPaymentMethod" type="button" disabled>Отменить автопрод.</button>
            </div>
          </div>

          <div class="documents-line" title="Будет позже">
            <span>Документы и оплата по счету</span>
            <strong>Будет позже</strong>
          </div>

          <div class="subscription-note">
            После окончания пробного периода подписка продолжится по выбранному тарифу.
          </div>
        </div>
      </section>

      <section ref="plansAnchor" class="plans-section">
        <div class="tariff-section-head">
          <div>
            <h4>Сменить тариф</h4>
            <p>Годовая подписка дает скидку 30%</p>
          </div>
          <div class="billing-switch">
            <button
              type="button"
              class="billing-switch__btn"
              :class="{ 'billing-switch__btn--active': billingPeriod === 'month' }"
              @click="billingPeriod = 'month'"
            >
              Месяц
            </button>
            <button
              type="button"
              class="billing-switch__btn"
              :class="{ 'billing-switch__btn--active': billingPeriod === 'year' }"
              @click="billingPeriod = 'year'"
            >
              <span>Год</span>
              <small>Экономия 30%</small>
            </button>
          </div>
        </div>

        <Transition name="tab-fade" mode="out-in">
          <div :key="billingPeriod" class="plan-grid">
            <article
              v-for="card in planCards"
              :key="card.code"
              class="plan-card"
              :class="[`plan-card--${card.code}`, { 'plan-card--current': isCurrentPlan(card.plan) }]"
            >
              <div class="plan-title">
                <span class="two-circles" :class="{ 'two-circles--light': card.code === 'basic' }"></span>
                <h5>{{ card.title }}</h5>
              </div>

              <div class="plan-price">
                <strong>{{ card.price }}</strong>
                <span>{{ card.perProject }}</span>
              </div>

              <ul class="plan-features">
                <li v-for="feature in card.features" :key="feature">
                  <span class="feature-dot"></span>
                  <span>{{ feature }}</span>
                </li>
              </ul>

              <div class="plan-card__footer">
                <button
                  type="button"
                  class="plan-btn"
                  :class="{ 'plan-btn--light': card.code === 'basic', 'plan-btn--current': isCurrentPlan(card.plan) }"
                  :disabled="paying === card.code || isCurrentPlan(card.plan)"
                  @click="onSubscribe(card.code, billingPeriod)"
                >
                  {{ planButtonText(card.plan) }}
                  <svg class="button-idea-icon" width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">
                    <path d="M11.6827 2.66752C10.6181 1.74863 9.21766 1.27671 7.74644 1.33866C4.98331 1.45489 2.70483 3.58678 2.66746 6.09098C2.64694 7.49798 3.30472 8.83956 4.47229 9.77174C4.59775 9.87193 4.69572 9.99455 4.76241 10.1297H7.52986V8.50095C7.33907 8.35839 7.15453 8.22223 6.98085 8.09484C5.6843 7.1441 5.01087 6.61191 5.01087 5.78755C5.01087 4.97369 5.66742 4.33609 6.50562 4.33609C6.96027 4.33609 7.32793 4.5057 7.6297 4.85468L8.0004 5.28364L8.37111 4.85468C8.67287 4.50567 9.04054 4.33609 9.49518 4.33609C10.3334 4.33609 10.9899 4.97371 10.9899 5.78755C10.9899 6.61194 10.3165 7.14412 9.02608 8.0904C8.84876 8.22039 8.66259 8.35773 8.47095 8.50093V10.1297H11.2364C11.3015 9.99624 11.397 9.87626 11.519 9.77931C12.6722 8.86306 13.3337 7.54282 13.3337 6.15716C13.3337 4.82613 12.7474 3.58678 11.6827 2.66752Z" fill="currentColor" />
                    <path d="M4.86523 11.0371V11.4908C4.86523 12.0865 5.26678 12.5885 5.82067 12.7725C5.87042 13.2194 6.06465 13.6443 6.38237 13.9788C6.79749 14.4158 7.38789 14.6666 8.00249 14.6666C8.61707 14.6666 9.20743 14.4158 9.62259 13.9788C9.9403 13.6444 10.1345 13.2195 10.1843 12.7725C10.7382 12.5885 11.1397 12.0865 11.1397 11.4908V11.0371H4.86523V11.0371Z" fill="currentColor" />
                  </svg>
                </button>
                <p><strong>{{ trialPhrase(card.plan.trial_days) }}</strong> — подключение за 5 минут</p>
              </div>
            </article>
          </div>
        </Transition>

        <article class="white-label-card">
          <div class="white-label-card__left">
            <div class="plan-title">
              <span class="two-circles"></span>
              <h5>White Label -<br />персонализация<br />кабинета и отчетности</h5>
            </div>
            <ul class="plan-features plan-features--wl">
              <li v-for="feature in wlFeaturesLeft" :key="feature">
                <span class="feature-dot"></span>
                <span>{{ feature }}</span>
              </li>
            </ul>
          </div>

          <div class="white-label-card__preview">
            <img src="/admirra/img/white-label/ui.png" alt="White Label UI" />
          </div>

          <div class="white-label-card__right">
            <div class="plan-price">
              <strong>25&nbsp;900&nbsp;₽</strong>
              <span>259 руб/проект</span>
            </div>
            <p class="white-label-card__copy">
              При покупке на год - возможны персональные скидки. Оставьте заявку, чтобы обсудить детали использования WL.
            </p>
            <button class="plan-btn" type="button" @click="onContactWl">
              {{ subscription.whitelabel_available ? 'Настроить бренд' : 'Перейти на тариф WL' }}
              <svg class="button-idea-icon" width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">
                <path d="M11.6827 2.66752C10.6181 1.74863 9.21766 1.27671 7.74644 1.33866C4.98331 1.45489 2.70483 3.58678 2.66746 6.09098C2.64694 7.49798 3.30472 8.83956 4.47229 9.77174C4.59775 9.87193 4.69572 9.99455 4.76241 10.1297H7.52986V8.50095C7.33907 8.35839 7.15453 8.22223 6.98085 8.09484C5.6843 7.1441 5.01087 6.61191 5.01087 5.78755C5.01087 4.97369 5.66742 4.33609 6.50562 4.33609C6.96027 4.33609 7.32793 4.5057 7.6297 4.85468L8.0004 5.28364L8.37111 4.85468C8.67287 4.50567 9.04054 4.33609 9.49518 4.33609C10.3334 4.33609 10.9899 4.97371 10.9899 5.78755C10.9899 6.61194 10.3165 7.14412 9.02608 8.0904C8.84876 8.22039 8.66259 8.35773 8.47095 8.50093V10.1297H11.2364C11.3015 9.99624 11.397 9.87626 11.519 9.77931C12.6722 8.86306 13.3337 7.54282 13.3337 6.15716C13.3337 4.82613 12.7474 3.58678 11.6827 2.66752Z" fill="currentColor" />
                <path d="M4.86523 11.0371V11.4908C4.86523 12.0865 5.26678 12.5885 5.82067 12.7725C5.87042 13.2194 6.06465 13.6443 6.38237 13.9788C6.79749 14.4158 7.38789 14.6666 8.00249 14.6666C8.61707 14.6666 9.20743 14.4158 9.62259 13.9788C9.9403 13.6444 10.1345 13.2195 10.1843 12.7725C10.7382 12.5885 11.1397 12.0865 11.1397 11.4908V11.0371H4.86523V11.0371Z" fill="currentColor" />
              </svg>
            </button>
          </div>
        </article>
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
  max_ai_requests_per_period: 30,
  ai_requests_used: 0,
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
  active: 'Активно',
  trial: 'Активно',
  past_due: 'Просрочено',
  canceled: 'Отменено',
  expired: 'Истекло',
})[subscriptionStatusKey.value] || 'Активно')

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
  const date = formatDate(subscription.value?.subscription_expires_at) || '11.06.2026'
  const days = daysLeft.value ?? 13
  if (subscriptionStatusKey.value === 'past_due') return 'Не удалось списать оплату. Обновите способ оплаты.'
  if (subscriptionStatusKey.value === 'canceled') return `Доступ сохранится до ${date}`
  return `Продлится ${date} - <span style="color:#171717;font-weight:500">осталось ${days} дней</span>`
})

const planMetaLine = computed(() => {
  const period = subscription.value?.billing_period === 'year' ? 'Годовая' : 'Помесячно'
  const price = subscription.value?.billing_period === 'year'
    ? formatRub(yearlyPriceFromMonthly(currentPlan.value?.price_rub))
    : formatRub(currentPlan.value?.price_rub)
  return `${period} ${price}/мес.`
})

const hasPaymentMethod = computed(() => {
  const method = subscription.value?.payment_method || {}
  return Boolean(method.last4 || subscription.value?.payment_last4)
})

const paymentMethod = computed(() => subscription.value?.payment_method || {})
const paymentLast4 = computed(() => paymentMethod.value.last4 || subscription.value?.payment_last4 || '')
const paymentExp = computed(() => paymentMethod.value.exp || paymentMethod.value.expires || subscription.value?.payment_exp || '')
const cardBrandLabel = computed(() => String(paymentMethod.value.brand || subscription.value?.payment_brand || 'МИР').toUpperCase())

const usagePercent = (used, limit) => {
  const safeLimit = Math.max(Number(limit) || 0, 1)
  return Math.min(100, Math.round(((Number(used) || 0) / safeLimit) * 100))
}

const usageIcons = {
  projects: '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M3.36 12.8H4.96C5.048 12.8 5.12 12.728 5.12 12.64V3.36C5.12 3.272 5.048 3.2 4.96 3.2H3.36C3.272 3.2 3.2 3.272 3.2 3.36V12.64C3.2 12.728 3.272 12.8 3.36 12.8ZM7.2 7.2H8.8C8.888 7.2 8.96 7.128 8.96 7.04V3.36C8.96 3.272 8.888 3.2 8.8 3.2H7.2C7.112 3.2 7.04 3.272 7.04 3.36V7.04C7.04 7.128 7.112 7.2 7.2 7.2ZM11.04 8.64H12.64C12.728 8.64 12.8 8.568 12.8 8.48V3.36C12.8 3.272 12.728 3.2 12.64 3.2H11.04C10.952 3.2 10.88 3.272 10.88 3.36V8.48C10.88 8.568 10.952 8.64 11.04 8.64ZM15.36 0H0.64C0.286 0 0 0.286 0 0.64V15.36C0 15.714 0.286 16 0.64 16H15.36C15.714 16 16 15.714 16 15.36V0.64C16 0.286 15.714 0 15.36 0ZM14.56 14.56H1.44V1.44H14.56V14.56Z" fill="#EA9942"/></svg>',
  cabinets: '<svg width="14" height="16" viewBox="0 0 14 16" fill="none"><path d="M11.9778 0H2.02222C0.905956 0.00104918 0.00124444 0.763803 0 1.70492V14.2951C0.00124444 15.2362 0.905956 15.999 2.02222 16H11.9778C13.094 15.9995 13.9994 15.2362 14 14.2951V1.70492C13.9988 0.763803 13.094 0.00104918 11.9778 0ZM2.02222 1.31148H11.9778C12.2341 1.31462 12.4407 1.48879 12.4444 1.70439V7.34426H1.55556V1.70492C1.55929 1.48879 1.76649 1.31462 2.02222 1.31148ZM11.9778 14.6885H2.02222C1.76587 14.6854 1.55929 14.5112 1.55556 14.2956V8.65574H12.4444V14.2951C12.4407 14.5112 12.2335 14.6854 11.9778 14.6885ZM4.82222 5.48931C5.25156 5.48931 5.6 5.19554 5.6 4.83357V4.4779H8.4V4.83357C8.4 5.19554 8.74844 5.48931 9.17778 5.48931C9.60711 5.48931 9.95556 5.19554 9.95556 4.83357V3.82216C9.95556 3.4602 9.60711 3.16643 9.17778 3.16643H4.82222C4.39289 3.16643 4.04444 3.4602 4.04444 3.82216V4.83357C4.04444 5.19554 4.39289 5.48931 4.82222 5.48931ZM9.17778 10.5102H4.82222C4.39289 10.5102 4.04444 10.8039 4.04444 11.1659V12.1784C4.04444 12.5403 4.39289 12.8341 4.82222 12.8341C5.25156 12.8341 5.6 12.5403 5.6 12.1784V11.8216H8.4V12.1784C8.4 12.5403 8.74844 12.8341 9.17778 12.8341C9.60711 12.8341 9.95556 12.5403 9.95556 12.1784V11.1659C9.95493 10.8039 9.60711 10.5107 9.17778 10.5102Z" fill="#7BADE8"/></svg>',
  ai: '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M15.857 6.07273L14.1843 4.69091V2C14.1831 1.93027 14.1619 1.86234 14.1232 1.80432C14.0846 1.74629 14.03 1.70061 13.9661 1.67273L10.3661 0.0363636H10.2206L10.0024 0.109091L8.00244 1.41818L6.00244 0.0727273L5.78426 0H5.6388L2.0388 1.67273C1.97488 1.70061 1.92033 1.74629 1.88164 1.80432C1.84296 1.86234 1.82178 1.93027 1.82062 2V4.69091L0.147893 6.07273C0.0974311 6.10122 0.0566274 6.14413 0.0307123 6.19596C0.00479722 6.24779-0.00504819 6.30617 0.0024381 6.36364V9.63636C-0.00504819 9.69383 0.00479722 9.75221 0.0307123 9.80404C0.0566274 9.85588 0.0974311 9.89878 0.147893 9.92727L1.82062 11.3091V14C1.82178 14.0697 1.84296 14.1377 1.88164 14.1957C1.92033 14.2537 1.97488 14.2994 2.0388 14.3273L5.6388 15.9636H5.78426L6.00244 15.8909L8.00244 14.5818L10.0024 15.9273L10.2206 16H10.3661L13.9661 14.3636C14.03 14.3358 14.0846 14.2901 14.1232 14.232C14.1619 14.174 14.1831 14.1061 14.1843 14.0364V11.3091L15.857 9.92727C15.9016 9.90152 15.9386 9.86439 15.9641 9.81966C15.9897 9.77494 16.0029 9.72423 16.0024 9.67273V6.32727C16.0029 6.27577 15.9897 6.22506 15.9641 6.18034C15.9386 6.13562 15.9016 6.09848 15.857 6.07273ZM14.0024 8.54545H14.5479V9.12727L13.2752 10.1455L13.1297 10.2545L12.9843 10.1818C12.9209 10.1454 12.8504 10.123 12.7776 10.1163C12.7048 10.1095 12.6314 10.1185 12.5624 10.1427C12.4934 10.1668 12.4304 10.2056 12.3777 10.2562C12.325 10.3069 12.2838 10.3684 12.257 10.4364C12.1917 10.5622 12.178 10.7084 12.2188 10.8442C12.2595 10.9799 12.3514 11.0945 12.4752 11.1636L12.7297 11.2727V13.2364L10.3297 14.3636L8.80244 13.3455L8.54789 13.1636V8.54545H9.09335C9.23801 8.54545 9.37675 8.48799 9.47904 8.38569C9.58134 8.2834 9.6388 8.14466 9.6388 8C9.6388 7.85534 9.58134 7.7166 9.47904 7.61431C9.37675 7.51201 9.23801 7.45455 9.09335 7.45455H8.54789V2.8L8.80244 2.61818L10.3297 1.6L12.7297 2.72727V4.69091L12.4752 4.8C12.3514 4.86913 12.2595 4.98369 12.2188 5.11944C12.178 5.25519 12.1917 5.40146 12.257 5.52727C12.2936 5.62311 12.3584 5.70563 12.4427 5.76403C12.5271 5.82243 12.6271 5.85398 12.7297 5.85455L12.9843 5.78182L13.1297 5.70909L13.2752 5.81818L14.5479 6.87273V7.45455H14.0024C13.8578 7.45455 13.719 7.51201 13.6167 7.61431C13.5145 7.7166 13.457 7.85534 13.457 8C13.457 8.14466 13.5145 8.2834 13.6167 8.38569C13.719 8.48799 13.8578 8.54545 14.0024 8.54545ZM6.91153 8.54545H7.45698V13.2L7.20244 13.3818L5.67517 14.4L3.27517 13.2727V11.3091L3.52971 11.2C3.65344 11.1309 3.7454 11.0163 3.78612 10.8806C3.82685 10.7448 3.81314 10.5985 3.74789 10.4727C3.72106 10.4047 3.6799 10.3433 3.6272 10.2926C3.5745 10.2419 3.51151 10.2032 3.4425 10.179C3.37349 10.1549 3.30009 10.1459 3.2273 10.1526C3.1545 10.1594 3.08401 10.1817 3.02062 10.2182L2.87517 10.2909L2.72971 10.1818L1.45698 9.12727V8.54545H2.00244C2.1471 8.54545 2.28584 8.48799 2.38813 8.38569C2.49043 8.2834 2.54789 8.14466 2.54789 8C2.54789 7.85534 2.49043 7.7166 2.38813 7.61431C2.28584 7.51201 2.1471 7.45455 2.00244 7.45455H1.45698V6.87273L2.72971 5.85455L2.87517 5.74545L3.02062 5.81818L3.27517 5.89091C3.37776 5.89035 3.4778 5.8588 3.56215 5.8004C3.64651 5.742 3.71125 5.65947 3.74789 5.56364C3.81314 5.43782 3.82685 5.29155 3.78612 5.1558C3.7454 5.02006 3.65344 4.90549 3.52971 4.83636L3.27517 4.72727V2.72727L5.67517 1.6L7.20244 2.61818L7.45698 2.8V7.45455H6.91153C6.76687 7.45455 6.62813 7.51201 6.52584 7.61431C6.42354 7.7166 6.36608 7.85534 6.36608 8C6.36608 8.14466 6.42354 8.2834 6.52584 8.38569C6.62813 8.48799 6.76687 8.54545 6.91153 8.54545Z" fill="#F08F96"/></svg>',
  users: '<svg width="21" height="17" viewBox="0 0 21 17" fill="none"><path d="M7.26562 7.26562C8.30116 7.26562 9.14062 6.42616 9.14062 5.39062C9.14062 4.35509 8.30116 3.51562 7.26562 3.51562C6.23009 3.51562 5.39062 4.35509 5.39062 5.39062C5.39062 6.42616 6.23009 7.26562 7.26562 7.26562Z" stroke="#A286BB" stroke-width="1.40625"/><path d="M11.0156 11.0156C11.0156 12.0512 11.0156 12.8906 7.26562 12.8906C3.51562 12.8906 3.51562 12.0512 3.51562 11.0156C3.51562 9.98006 5.19456 9.14062 7.26562 9.14062C9.33666 9.14062 11.0156 9.98006 11.0156 11.0156Z" stroke="#A286BB" stroke-width="1.40625"/><path d="M0.703125 8.20312C0.703125 4.66759 0.703125 2.89983 1.80147 1.80147C2.89983 0.703125 4.66759 0.703125 8.20312 0.703125H11.9531C15.4886 0.703125 17.2565 0.703125 18.3547 1.80147C19.4531 2.89983 19.4531 4.66759 19.4531 8.20312C19.4531 11.7386 19.4531 13.5065 18.3547 14.6047C17.2565 15.7031 15.4886 15.7031 11.9531 15.7031H8.20312C4.66759 15.7031 2.89983 15.7031 1.80147 14.6047C0.703125 13.5065 0.703125 11.7386 0.703125 8.20312Z" stroke="#A286BB" stroke-width="1.40625"/><path d="M16.6406 8.20312H12.8906" stroke="#A286BB" stroke-width="1.40625" stroke-linecap="round"/><path d="M16.6406 5.39062H11.9531" stroke="#A286BB" stroke-width="1.40625" stroke-linecap="round"/><path d="M16.6406 11.0156H13.8281" stroke="#A286BB" stroke-width="1.40625" stroke-linecap="round"/></svg>',
}

const subscriptionUsageTiles = computed(() => {
  const s = subscription.value || {}
  const tiles = [
    {
      key: 'projects',
      label: 'Проекты',
      used: s.projects_used ?? 1,
      limit: s.max_projects ?? currentPlan.value?.max_projects ?? 1,
      caption: `${s.projects_used ?? 1} активных  •  ${s.paused_projects ?? 0} на паузе`,
    },
    {
      key: 'cabinets',
      label: 'Кабинеты',
      used: s.cabinets_used ?? 8,
      limit: s.max_cabinets ?? 3,
      caption: 'Реклам. кабинеты и счетчики',
    },
    {
      key: 'ai',
      label: 'AI - запросы',
      used: s.ai_requests_used ?? 0,
      limit: s.max_ai_requests_per_period ?? currentPlan.value?.max_ai_requests_per_period ?? 30,
      caption: s.ai_reset_date ? `Сброс ${s.ai_reset_date}` : 'Сброс 01.07',
    },
    {
      key: 'users',
      label: 'Пользователи',
      used: s.users_used ?? 1,
      limit: s.max_users ?? s.max_staff ?? 1,
      caption: `${s.users_used ?? 1} активный`,
    },
  ]
  return tiles.map((item) => ({
    ...item,
    icon: usageIcons[item.key],
    percent: usagePercent(item.used, item.limit),
  }))
})

const availableChannels = computed(() => [
  { label: 'Yandex Direct', className: 'channel-chip--yd', icon: '/admirra/img/icons/yandex-direct.png', color: '#c7a44d' },
  { label: 'VK Ads Manager', className: 'channel-chip--vk', icon: '/admirra/img/icons/vk-ads.png', color: '#2563eb' },
])

const landingTariffDisplay = {
  month: {
    start: {
      price: '1\u00A0590\u00A0₽',
      perProject: '1590 руб/проект',
      features: ['1 Проект', 'Каналы: Яндекс.Директ, ВК', '1 пользователь', '30 запросов AI', 'Экспорт отчетов,\nотправка по расписанию'],
    },
    basic: {
      price: '3\u00A0990\u00A0₽',
      perProject: '498 руб/проект',
      features: ['До 8 Проектов', 'Все доступные подключения', 'До 5 пользователей', '120 запросов AI', 'Экспорт отчетов,\nотправка по расписанию'],
    },
    standard: {
      price: '9\u00A0990\u00A0₽',
      perProject: '333 руб/проект',
      features: ['До 30 Проектов', 'Все доступные подключения', 'До 10 пользователей', '450 запросов AI', 'Экспорт отчетов,\nотправка по расписанию'],
    },
  },
  year: {
    start: {
      price: '11\u00A0590\u00A0₽',
      perProject: '1590 руб/проект',
      features: ['1 Проект', 'Каналы: Яндекс.Директ, ВК', '1 пользователь', '30 запросов AI', 'Экспорт отчетов,\nотправка по расписанию'],
    },
    basic: {
      price: '31\u00A0990\u00A0₽',
      perProject: '498 руб/проект',
      features: ['До 8 Проектов', 'Все доступные подключения', 'До 5 пользователей', '120 запросов AI', 'Экспорт отчетов,\nотправка по расписанию'],
    },
    standard: {
      price: '69\u00A0990\u00A0₽',
      perProject: '333 руб/проект',
      features: ['До 30 Проектов', 'Все доступные подключения', 'До 10 пользователей', '450 запросов AI', 'Экспорт отчетов,\nотправка по расписанию'],
    },
  },
}

const planCards = computed(() => ['start', 'basic', 'standard'].map((code) => {
  const plan = resolvedPlans.value[code]
  const display = landingTariffDisplay[billingPeriod.value]?.[code]
  return {
    code,
    plan,
    title: code === 'start' ? 'Старт' : code === 'basic' ? 'Базовый' : 'Стандартный',
    price: display?.price || formatRub(plan?.price_rub),
    perProject: display?.perProject || '',
    features: display?.features || [],
  }
}))

const wlFeaturesLeft = [
  'Отчеты без логотипа сервиса',
  'Брендирование отчетов',
  'Использование платформы\nкак собственной системы аналитики',
  'Собственный домен',
]

const isCurrentPlan = (plan) => String(plan?.code || '').toLowerCase() === currentPlanCode.value
const planButtonText = (plan) => {
  if (paying.value === plan?.code) return 'Подождите...'
  return `Перейти на тариф ${plan?.name || ''}`.trim()
}

const scrollToPlans = () => {
  plansAnchor.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

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
.tariffs-page {
  width: 100%;
}

.tariffs-loading {
  display: flex;
  justify-content: center;
  padding: 6rem 0;
  color: rgba(105, 105, 105, 0.56);
  font-size: 0.9028rem;
  font-weight: 600;
}

.tariff-page-head {
  margin: 0 0 1.875rem;
}

.tariff-page-head h4 {
  margin: 0;
  color: #2563eb;
  font-size: 2.0833rem;
  font-weight: 700;
  line-height: 1;
}

.tariff-page-head p {
  margin: 0.8333rem 0 0;
  color: rgba(105, 105, 105, 0.56);
  font-size: 1.0417rem;
  font-weight: 500;
}

.subscription-card {
  margin-bottom: 5.5556rem;
  overflow: hidden;
  border-radius: 1.25rem;
  background: #fff;
  box-shadow: inset 0 0 0 1px rgba(15, 23, 42, 0.03);
}

.subscription-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1.5rem;
  padding: 1.875rem 1.875rem 0;
}

.subscription-title-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.6944rem;
}

.subscription-title-row h5 {
  margin: 0;
  color: #171717;
  font-size: 1.4583rem;
  font-weight: 500;
  line-height: 1.15;
}

.subscription-status,
.subscription-period {
  display: inline-flex;
  align-items: center;
  min-height: 1.875rem;
  padding: 0 0.9028rem;
  border-radius: 0.2083rem;
  font-size: 0.9028rem;
  font-weight: 600;
  white-space: nowrap;
}

.subscription-status {
  background: #eaffef;
  color: #13a548;
}

.subscription-status--past_due,
.subscription-status--canceled,
.subscription-status--expired {
  background: #fff1d9;
  color: #b45309;
}

.subscription-period {
  background: #f4f6f8;
  color: rgba(105, 105, 105, 0.64);
}

.subscription-renewal {
  display: inline-flex;
  align-items: center;
  gap: 0.4167rem;
  margin: 0.9028rem 0 0;
  color: rgba(105, 105, 105, 0.62);
  font-size: 1.0417rem;
  font-weight: 600;
}

.subscription-renewal svg {
  width: 1.0417rem;
  height: 1.0417rem;
}

.subscription-change-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 3.2639rem;
  padding: 0 1.4583rem;
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 0.8333rem;
  background: #fff;
  color: #2563eb;
  font-size: 0.9722rem;
  font-weight: 600;
  cursor: pointer;
}

.usage-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.8333rem;
  padding: 1.8056rem 1.875rem 1.5972rem;
}

.usage-tile {
  min-height: 9.0278rem;
  padding: 1.25rem 1.25rem;
  border-radius: 1.1111rem;
}

.usage-tile--projects { background: #FFF2E4; color: #71663E; }
.usage-tile--cabinets { background: #F0F7FF; color: #254B78; }
.usage-tile--ai { background: #FFF0F1; color: #662529; }
.usage-tile--users { background: #F6ECFF; color: #643D87; }

.usage-tile__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  font-size: 1.0417rem;
  font-weight: 700;
}

.usage-tile__head i {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 0.3472rem;
}

.usage-tile--projects .usage-tile__head i { background: #FFE9D1; }
.usage-tile--cabinets .usage-tile__head i { background: #E3F0FF; }
.usage-tile--ai .usage-tile__head i { background: #FFDEE0; }
.usage-tile--users .usage-tile__head i { background: #F0DEFF; }

.usage-tile__head svg {
  width: 1.25rem;
  height: 1.25rem;
}

.usage-tile__value {
  display: flex;
  align-items: baseline;
  gap: 0.4167rem;
  margin-top: 0.6944rem;
}

.usage-tile__value strong {
  color: currentColor;
  font-size: 2.0833rem;
  font-weight: 700;
  line-height: 1;
}

.usage-tile__value span {
  color: rgba(105, 105, 105, 0.55);
  font-size: 1.25rem;
  font-weight: 600;
}

.usage-tile__bar {
  height: 0.625rem;
  margin-top: 1.1111rem;
  overflow: hidden;
  border-radius: 99rem;
  background: rgba(255, 255, 255, 0.68);
}

.usage-tile__bar i {
  display: block;
  height: 100%;
  min-width: 0.625rem;
  border-radius: inherit;
}

.usage-tile--projects .usage-tile__bar i { background: #FFC07B; }
.usage-tile--cabinets .usage-tile__bar i { background: #7BADE8; }
.usage-tile--ai .usage-tile__bar i { background: #ECB2B6; }
.usage-tile--users .usage-tile__bar i { background: #BCA6CE; }

.usage-tile p {
  margin: 1.1111rem 0 0;
  color: currentColor;
  font-size: 0.9722rem;
  font-weight: 500;
  opacity: 0.74;
}

.usage-tile--projects p { color: #C0A86E; opacity: 1; }
.usage-tile--projects .usage-tile__value span { color: #C0A86E; }
.usage-tile--cabinets p { color: #71A0D7; opacity: 1; }
.usage-tile--cabinets .usage-tile__value span { color: #71A0D7; }
.usage-tile--ai p { color: #D69397; opacity: 1; }
.usage-tile--ai .usage-tile__value span { color: #D69397; }
.usage-tile--users p { color: #A987C7; opacity: 1; }
.usage-tile--users .usage-tile__value span { color: #A987C7; }

.subscription-channel-row {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 1.0417rem;
  min-height: 3.4722rem;
  margin: 0 1.875rem 1.5972rem;
  padding: 0.5556rem 1.4583rem;
  border-radius: 0.8333rem;
  background: #f4f6f8;
}

.subscription-channel-row > span,
.subscription-channel-row em {
  color: rgba(105, 105, 105, 0.58);
  font-size: 1.0417rem;
  font-style: normal;
  font-weight: 600;
}

.subscription-channel-row em {
  text-align: right;
}

.channel-chip-list {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.8333rem;
}

.channel-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.3472rem;
  min-height: 1.8056rem;
  padding: 0 0.6944rem;
  border-radius: 99rem;
  background: #fff;
  color: #174a7a;
  font-size: 0.8333rem;
  font-weight: 500;
}

.channel-chip img {
  width: 1.0417rem;
  height: 1.0417rem;
  object-fit: contain;
}

.subscription-footer {
  display: grid;
  gap: 0.6944rem;
  padding: 1.25rem 1.875rem 1.6667rem;
  border-top: 1px solid rgba(15, 23, 42, 0.06);
}

.payment-line {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 1.25rem;
  min-height: 3.4722rem;
}

.payment-line--empty {
  grid-template-columns: minmax(0, 1fr) auto;
}

.payment-line--empty .payment-renewal {
  display: none;
}

.payment-method {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: 0.6944rem;
  color: rgba(105, 105, 105, 0.62);
  font-size: 1.0417rem;
  font-weight: 600;
}

.payment-method strong {
  color: #5f6368;
  font-weight: 700;
}

.payment-toggle {
  width: 1.25rem;
  height: 0.7639rem;
  border-radius: 99rem;
  background: linear-gradient(90deg, #bfcfff 0 45%, #6f8be8 45% 100%);
  flex-shrink: 0;
}

.payment-brand {
  display: inline-flex;
  align-items: center;
  min-height: 1.25rem;
  padding: 0 0.2778rem;
  border-radius: 0.1389rem;
  color: #149f62;
  font-size: 0.7639rem;
  font-weight: 900;
}

.payment-mask,
.payment-exp,
.payment-renewal {
  color: rgba(105, 105, 105, 0.5);
  font-size: 1.0417rem;
  font-weight: 500;
}

.subscription-footer-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 1.0417rem;
}

.subscription-footer-actions button {
  min-height: 3.3333rem;
  padding: 0 1.3889rem;
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 0.8333rem;
  background: #fff;
  color: #2563eb;
  font-size: 0.9722rem;
  font-weight: 600;
  cursor: not-allowed;
}

.payment-line--empty .subscription-footer-actions button {
  border-color: #2563eb;
  background: #2563eb;
  color: #fff;
}

.documents-line {
  display: flex;
  align-items: center;
  gap: 1.25rem;
  color: rgba(105, 105, 105, 0.22);
  font-size: 1.0417rem;
  font-weight: 600;
}

.documents-line strong {
  display: inline-flex;
  align-items: center;
  min-height: 2.0139rem;
  padding: 0 1.0417rem;
  border-radius: 0.3472rem;
  background: rgba(245, 247, 249, 0.58);
  color: rgba(105, 105, 105, 0.18);
  font-size: 0.9028rem;
  font-weight: 600;
}

.subscription-note {
  min-height: 3.4722rem;
  display: flex;
  align-items: center;
  padding: 0 1.4583rem;
  border-radius: 0.8333rem;
  background: #f4f6f8;
  color: rgba(105, 105, 105, 0.58);
  font-size: 1.0417rem;
  font-weight: 500;
}

.plans-section {
  width: 100%;
}

.tariff-section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 2rem;
  margin-bottom: 2.2222rem;
}

.tariff-section-head h4 {
  margin: 0;
  color: #171717;
  font-size: 2.0833rem;
  font-weight: 700;
  line-height: 1.1;
}

.tariff-section-head p {
  margin: 0.6944rem 0 0;
  color: rgba(105, 105, 105, 0.56);
  font-size: 1.0417rem;
  font-weight: 500;
}

.billing-switch {
  display: inline-flex;
  align-items: center;
  gap: 1.0417rem;
}

.billing-switch__btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5556rem;
  min-height: 3.4722rem;
  padding: 0 1.5278rem;
  border: 0;
  border-radius: 0.8333rem;
  background: #fff;
  color: #5f6368;
  font-size: 0.9722rem;
  font-weight: 600;
  cursor: pointer;
}

.billing-switch__btn--active {
  background: #2563eb;
  color: #fff;
}

.billing-switch__btn small {
  display: inline-flex;
  align-items: center;
  min-height: 1.1111rem;
  padding: 0 0.4861rem;
  border-radius: 99rem;
  background: linear-gradient(270deg, #06b5d4 0.35%, #1f9de4 32.08%, #2563eb 96.51%);
  color: #fff;
  font-size: 0.625rem;
  font-weight: 700;
}

.plan-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(14rem, 1fr));
  gap: 1.6667rem;
  align-items: stretch;
}

.plan-card {
  position: relative;
  display: flex;
  min-height: 47.9167rem;
  flex-direction: column;
  overflow: hidden;
  padding: 2.4306rem 2.2222rem 1.9444rem;
  border-radius: 2.0833rem;
  background: #fff;
}

.plan-card--basic {
  background: #2563eb;
  color: #fff;
}

.plan-card--basic::before {
  content: '';
  position: absolute;
  inset: 0;
  opacity: 0.2;
  background-image:
    radial-gradient(circle, rgba(255, 255, 255, 0.8) 0 1px, transparent 1px);
  background-size: 1.0417rem 1.0417rem;
}


.plan-title {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: flex-start;
  gap: 1.0417rem;
}

.plan-title h5 {
  margin: 0;
  color: inherit;
  font-size: 1.5278rem;
  font-weight: 700;
  line-height: 1.15;
}

.two-circles {
  display: inline-block;
  width: 1.25rem;
  height: 0.8333rem;
  position: relative;
  flex-shrink: 0;
  margin-top: 0.2778rem;
}

.two-circles::before,
.two-circles::after {
  content: '';
  position: absolute;
  top: 0;
  width: 0.8333rem;
  height: 0.8333rem;
  border-radius: 50%;
}

.two-circles::before { left: 0; background: #a8bbf2; }
.two-circles::after { right: 0; background: #5e7fd8; }
.two-circles--light::before { background: rgba(255, 255, 255, 0.55); }
.two-circles--light::after { background: #fff; }

.plan-price {
  position: relative;
  z-index: 1;
  display: grid;
  gap: 0.625rem;
  margin-top: 2.4306rem;
}

.plan-price strong {
  color: inherit;
  font-size: 3.4722rem;
  font-weight: 500;
  line-height: 1;
  letter-spacing: 0;
}

.plan-price span {
  color: rgba(105, 105, 105, 0.52);
  font-size: 1.0417rem;
  font-weight: 400;
}

.plan-card--basic .plan-price span,
.plan-card--basic .plan-features,
.plan-card--basic .plan-card__footer p {
  color: rgba(255, 255, 255, 0.92);
}

.plan-features {
  position: relative;
  z-index: 1;
  display: grid;
  margin: 2.7083rem 0 0;
  padding: 0;
  list-style: none;
}

.plan-features li {
  display: flex;
  align-items: flex-start;
  gap: 1.0417rem;
  min-height: 3.75rem;
  padding: 1.0417rem 0;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
  color: #5f6368;
  font-size: 1.0417rem;
  font-weight: 500;
  line-height: 1.28;
  white-space: pre-line;
}

.plan-card--basic .plan-features li {
  border-bottom-color: rgba(255, 255, 255, 0.12);
  color: #fff;
}

.feature-dot {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 0.625rem;
  height: 0.625rem;
  margin: 0.2778rem;
  border-radius: 50%;
  background: #5e7fd8;
  box-shadow: 0 0 0 3px #edf3ff;
  flex-shrink: 0;
}

.plan-card--basic .feature-dot {
  background: #fff;
  box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.25);
}

.feature-dot::before,
.feature-dot::after {
  content: '';
  position: absolute;
  left: 50%;
  top: 50%;
  background: #fff;
  border-radius: 99rem;
  transform: translate(-50%, -50%);
}

.feature-dot::before { width: 0.2778rem; height: 1px; }
.feature-dot::after { width: 1px; height: 0.2778rem; }
.plan-card--basic .feature-dot::before,
.plan-card--basic .feature-dot::after { background: #2563eb; }

.plan-card__footer {
  position: relative;
  z-index: 1;
  margin-top: auto;
  padding-top: 2.0833rem;
}

.plan-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.6944rem;
  width: 100%;
  min-height: 3.4722rem;
  padding: 0 1.3889rem;
  border: 0;
  border-radius: 0.8333rem;
  background: linear-gradient(270deg, #06b5d4 0.35%, #1f9de4 32.08%, #2563eb 96.51%);
  color: #fff;
  font-size: 0.9028rem;
  font-weight: 600;
  cursor: pointer;
}

.plan-btn--light {
  background: #fff;
  color: #2563eb;
}

.plan-btn--current {
  cursor: not-allowed;
}

.button-idea-icon {
  display: inline-flex;
  width: 1rem;
  height: 1rem;
  flex-shrink: 0;
}

.plan-card__footer p {
  margin: 1.0417rem 0 0;
  color: #0c2b60;
  text-align: center;
  font-size: 0.8333rem;
  font-weight: 600;
}

.plan-card__footer p strong {
  color: #2563eb;
}

.plan-card--basic .plan-card__footer p strong {
  color: #fff;
}

.white-label-card {
  display: grid;
  grid-template-columns: minmax(15rem, 1fr) minmax(28rem, 1.2fr) minmax(18rem, 0.9fr);
  gap: 2.2222rem;
  align-items: stretch;
  margin-top: 2.0833rem;
  padding: 2.4306rem 2.2222rem;
  border-radius: 2.0833rem;
  background: #fff;
}

.white-label-card__left,
.white-label-card__right {
  display: flex;
  min-width: 0;
  flex-direction: column;
}

.white-label-card__right {
  padding-left: 1rem;
}

.white-label-card__preview {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 22rem;
}

.white-label-card__preview img {
  width: 100%;
  max-width: 31.25rem;
  object-fit: contain;
  opacity: 0.9;
}

.plan-features--wl {
  margin-top: 2.3611rem;
}

.white-label-card__copy {
  margin: 2.7778rem 0 auto;
  max-width: 16.6667rem;
  color: rgba(105, 105, 105, 0.66);
  font-size: 1.0417rem;
  font-weight: 500;
  line-height: 1.32;
}

.tab-fade-enter-active { transition: opacity 0.35s ease; }
.tab-fade-leave-active { transition: opacity 0.2s ease; }
.tab-fade-enter-from,
.tab-fade-leave-to { opacity: 0; }

@media (max-width: 1100px) {
  .usage-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .plan-grid {
    gap: 1.25rem;
  }
}

@media (max-width: 1180px) {
  .plan-grid,
  .white-label-card {
    grid-template-columns: 1fr;
  }

  .plan-card {
    min-height: auto;
  }

  .white-label-card__right {
    padding-left: 0;
  }
}

@media (max-width: 760px) {
  .subscription-head,
  .tariff-section-head,
  .payment-line,
  .subscription-channel-row {
    display: flex;
    align-items: flex-start;
    flex-direction: column;
  }

  .usage-grid {
    grid-template-columns: 1fr;
  }

  .subscription-footer-actions {
    justify-content: flex-start;
  }

  .billing-switch {
    width: 100%;
  }

  .billing-switch__btn {
    flex: 1;
  }
}
</style>
