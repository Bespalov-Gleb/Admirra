<template>
  <div class="max-w-[1215px] py-4 px-0 font-sans text-white">
    <div class="mb-10">
      <h1 class="text-3xl md:text-4xl font-bold mb-3">Тарифы</h1>
      <p class="text-[#94A3B8] text-[15px]">
        Выберите подходящий тариф в зависимости от количества проектов и задач аналитики
      </p>
      <div class="mt-8 flex flex-wrap items-center gap-[10px]">
        <button
          type="button"
          :class="[
            'box-border flex h-[46px] w-[77px] shrink-0 items-center justify-center rounded-[12px] px-[17px] font-sans text-[13px] font-medium leading-[100%] tracking-normal shadow-sm transition-colors',
            billingPeriod === 'month' ? 'bg-[#2563EB] text-white' : 'bg-[#2E3545] text-white hover:bg-[#394154]',
          ]"
          @click="billingPeriod = 'month'"
        >
          Месяц
        </button>
        <button
          type="button"
          :class="[
            'box-border flex h-[46px] min-w-[152px] w-max shrink-0 flex-row items-center gap-[10px] rounded-[12px] px-[17px] py-[15px] shadow-sm transition-colors',
            billingPeriod === 'year' ? 'bg-[#2563EB]' : 'bg-[#2E3545] hover:bg-[#394154]',
          ]"
          @click="billingPeriod = 'year'"
        >
          <span
            class="shrink-0 font-sans text-[13px] font-medium leading-[100%] tracking-normal text-white"
          >Год</span>
          <span
            class="inline-flex h-[18px] min-w-[82px] w-max max-w-none shrink-0 items-center justify-center whitespace-nowrap rounded-[30px] bg-btn-gradient px-[7px] font-sans text-[10px] font-semibold leading-[100%] tracking-normal text-white"
          >
            Экономия 30%
          </span>
        </button>
      </div>
    </div>

    <div class="flex flex-col lg:flex-row gap-[30px] justify-between relative z-10">
      <div
        class="w-full lg:w-[385px] min-h-[626px] bg-[#292E3C] rounded-[24px] p-8 flex flex-col justify-between relative"
      >
        <div>
          <div class="flex items-start gap-2 mb-6">
            <div class="flex items-center mt-1">
              <img :src="iconEll96" class="h-3 w-3" alt="" />
              <img :src="iconEll97" class="relative z-10 -ml-1.5 h-3 w-3" alt="" />
            </div>
            <h3 class="text-[18px] font-bold">{{ plans.start.name }}</h3>
          </div>
          <div class="mb-8">
            <div class="text-[40px] font-bold leading-none mb-1">{{ priceStart }}</div>
            <div class="text-white/90 text-sm">{{ perStart }}</div>
          </div>
          <ul class="space-y-4">
            <li
              v-for="(line, i) in linesStart"
              :key="'s' + i"
              class="flex items-start gap-3 relative pb-4 after:content-[''] after:absolute after:bottom-0 after:left-[-16px] after:right-[-16px] after:h-[1px] after:bg-white/10 last:after:hidden last:pb-0"
            >
              <img :src="iconCheck" class="w-4 h-4 mt-0.5 shrink-0" alt="" />
              <span class="text-white text-[15px]" v-html="line"></span>
            </li>
          </ul>
        </div>
        <div class="mt-auto flex flex-col pt-6">
          <button
            type="button"
            :disabled="!!paying"
            class="w-full bg-btn-gradient text-white py-4 rounded-t-[16px] rounded-b-[4px] font-medium flex justify-center items-center gap-2 hover:opacity-95 transition-opacity z-10 disabled:opacity-50"
            @click="$emit('subscribe', 'start')"
          >
            Перейти на тариф {{ plans.start.name }}
            <img :src="iconHeart" alt="" class="w-[16px] h-[16px]" />
          </button>
          <div class="w-full bg-[#3F4659] py-3 rounded-b-[16px] rounded-t-[4px] mt-1">
            <p class="text-center text-white text-[13px] font-medium">
              {{ trialStart }} — подключение за 5 минут
            </p>
          </div>
        </div>
      </div>

      <div
        class="w-full lg:w-[385px] min-h-[626px] text-white rounded-[24px] p-8 flex flex-col justify-between shadow-card relative overflow-hidden bg-[#2563EB]"
      >
        <img :src="imgBasicBg" alt="" class="absolute inset-0 w-full h-full object-cover pointer-events-none" />
        <img
          :src="iconFox"
          alt=""
          class="absolute pointer-events-none mix-blend-soft-light opacity-90 z-0"
          style="width: 380px; height: auto; top: -50px; right: -180px"
        />
        <div class="relative z-10">
          <div class="flex items-center gap-2 mb-6">
            <div class="flex items-center">
              <img :src="iconEll96Alt" class="w-3 h-3" alt="" />
              <img :src="iconEll97Alt" class="w-3 h-3 -ml-1.5 relative z-10" alt="" />
            </div>
            <h3 class="text-[18px] font-bold">{{ plans.basic.name }}</h3>
          </div>
          <div class="mb-8">
            <div class="text-[40px] font-bold leading-none mb-1">{{ priceBasic }}</div>
            <div class="text-white/90 text-sm">{{ perBasic }}</div>
          </div>
          <ul class="space-y-4">
            <li
              v-for="(line, i) in linesBasic"
              :key="'b' + i"
              class="flex items-start gap-3 relative pb-4 after:content-[''] after:absolute after:bottom-0 after:left-[-16px] after:right-[-16px] after:h-[1px] after:bg-white/10 last:after:hidden last:pb-0"
            >
              <img :src="iconCheck" class="w-4 h-4 mt-0.5 shrink-0" alt="" />
              <span class="text-white text-[15px]" v-html="line"></span>
            </li>
          </ul>
        </div>
        <div class="relative z-10 mt-auto flex flex-col pt-6">
          <button
            type="button"
            :disabled="!!paying"
            class="w-full bg-white text-[#2563EB] py-4 rounded-[16px] font-medium flex justify-center items-center gap-2 hover:bg-gray-50 transition-colors z-10 disabled:opacity-50"
            @click="$emit('subscribe', 'basic')"
          >
            Перейти на тариф {{ plans.basic.name }}
            <img :src="iconHeartOnBlue" alt="" class="w-[16px] h-[16px]" />
          </button>
          <div class="w-full py-3 mt-1">
            <p class="text-center text-blue-100 text-[13px] font-medium">
              {{ trialBasic }} — подключение за 5 минут
            </p>
          </div>
        </div>
      </div>

      <div
        class="w-full lg:w-[385px] min-h-[626px] bg-[#292E3C] rounded-[24px] p-8 flex flex-col justify-between relative"
      >
        <div>
          <div class="flex items-start gap-2 mb-6">
            <div class="flex items-center mt-1">
              <img :src="iconEll96" class="h-3 w-3" alt="" />
              <img :src="iconEll97" class="relative z-10 -ml-1.5 h-3 w-3" alt="" />
            </div>
            <h3 class="text-[18px] font-bold">{{ plans.standard.name }}</h3>
          </div>
          <div class="mb-8">
            <div class="text-[40px] font-bold leading-none mb-1">{{ priceStandard }}</div>
            <div class="text-white/90 text-sm">{{ perStandard }}</div>
          </div>
          <ul class="space-y-4">
            <li
              v-for="(line, i) in linesStandard"
              :key="'st' + i"
              class="flex items-start gap-3 relative pb-4 after:content-[''] after:absolute after:bottom-0 after:left-[-16px] after:right-[-16px] after:h-[1px] after:bg-white/10 last:after:hidden last:pb-0"
            >
              <img :src="iconCheck" class="w-4 h-4 mt-0.5 shrink-0" alt="" />
              <span class="text-white text-[15px]" v-html="line"></span>
            </li>
          </ul>
        </div>
        <div class="mt-auto flex flex-col pt-6">
          <button
            type="button"
            :disabled="!!paying"
            class="w-full bg-btn-gradient text-white py-4 rounded-t-[16px] rounded-b-[4px] font-medium flex justify-center items-center gap-2 hover:opacity-95 transition-opacity z-10 disabled:opacity-50"
            @click="$emit('subscribe', 'standard')"
          >
            Перейти на тариф {{ plans.standard.name }}
            <img :src="iconHeart" alt="" class="w-[16px] h-[16px]" />
          </button>
          <div class="w-full bg-[#3F4659] py-3 rounded-b-[16px] rounded-t-[4px] mt-1">
            <p class="text-center text-white text-[13px] font-medium">
              {{ trialStandard }} — подключение за 5 минут
            </p>
          </div>
        </div>
      </div>
    </div>

    <div
      class="w-full h-auto lg:h-[368px] mt-[30px] rounded-[30px] bg-[#292E3C] p-8 lg:p-12 shadow-card flex flex-col lg:flex-row justify-between relative overflow-hidden"
    >
      <div class="w-full lg:w-[360px] shrink-0 z-10 mb-8 lg:mb-0">
        <div class="flex items-start gap-2 mb-6">
          <div class="flex items-center mt-1">
            <img :src="iconEll96" class="h-3 w-3" alt="" />
            <img :src="iconEll97" class="relative z-10 -ml-1.5 h-3 w-3" alt="" />
          </div>
          <h3 class="text-[18px] font-bold leading-tight">
            White Label -<br />персонализация<br />кабинета и отчетности
          </h3>
        </div>
        <ul class="space-y-4 inline-flex flex-col">
          <li
            v-for="(t, i) in wlLines"
            :key="'wl' + i"
            class="flex items-start gap-3 relative pb-4 after:content-[''] after:absolute after:bottom-0 after:left-0 after:right-0 after:h-[1px] after:bg-white/10 last:after:hidden last:pb-0"
          >
            <img :src="iconCheck" class="w-4 h-4 mt-0.5 shrink-0" alt="" />
            <span class="text-white text-[15px]" v-html="t"></span>
          </li>
        </ul>
      </div>
      <div class="pointer-events-none absolute hidden lg:block" style="left: 380px; top: 42px; width: 345.75px; height: 188.24px">
        <img :src="imgWlBg" alt="" class="absolute inset-0 z-0 h-full w-full object-cover" />
      </div>
      <!-- Передний макет + поверх только «параллелограмм» списка: #24252E 36% + blur (макет Rectangle 1430107297) -->
      <div
        class="pointer-events-none absolute hidden lg:block z-20"
        style="left: 401px; top: 94px; width: 375px; height: 274px"
      >
        <img :src="imgWlFg" alt="" class="absolute inset-0 h-full w-full object-contain object-left-top" />
        <div
          aria-hidden="true"
          class="absolute z-[15] rounded-[10.66px] border border-white/[0.06] bg-[rgb(36_37_46/0.36)] backdrop-blur-[85.7px]"
          style="left: 6.5%; top: 35%; width: 273px; height: 200px; max-width: 74%"
        />
      </div>
      <div class="w-full lg:w-[280px] shrink-0 z-10 flex flex-col justify-center h-full ml-auto relative">
        <div class="mb-6">
          <div class="text-[40px] font-bold leading-none mb-1">25 900 ₽</div>
          <div class="text-[#94A3B8] text-sm">259 руб/проект</div>
        </div>
        <p class="text-[#94A3B8] text-[14px] leading-relaxed mb-8">
          При покупке на год -<br />
          возможны персональные<br />
          скидки. Оставьте заявку,<br />
          чтобы обсудить детали<br />
          использования WL.
        </p>
        <button
          type="button"
          :disabled="!!paying"
          class="w-full bg-btn-gradient text-white py-4 rounded-[12px] font-medium flex justify-center items-center gap-2 hover:opacity-95 transition-opacity disabled:opacity-50"
          @click="$emit('contact-wl')"
        >
          Перейти на тариф WL
          <img :src="iconHeart" alt="" class="w-[16px] h-[16px]" />
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import {
  iconEll96,
  iconEll97,
  iconEll96Alt,
  iconEll97Alt,
  iconCheck,
  iconHeart,
  iconHeartOnBlue,
  iconFox,
  imgBasicBg,
  imgWlBg,
  imgWlFg,
} from '@/utils/pricingAssets'
import {
  formatRub,
  perProjectLine,
  projectBullet,
  channelsBullet,
  usersBullet,
  aiBullet,
  trialPhrase,
  yearlyPriceFromMonthly,
} from '@/utils/pricingPlans'

const props = defineProps({
  plans: { type: Object, required: true },
  paying: { type: String, default: null },
})

defineEmits(['subscribe', 'contact-wl'])

const billingPeriod = ref('month')

function billingPriceRub(plan) {
  const monthly = Number(plan.price_rub)
  if (Number.isNaN(monthly)) return 0
  if (billingPeriod.value === 'year') return yearlyPriceFromMonthly(monthly)
  return Math.round(monthly)
}

const priceStart = computed(() => formatRub(billingPriceRub(props.plans.start)))
const priceBasic = computed(() => formatRub(billingPriceRub(props.plans.basic)))
const priceStandard = computed(() => formatRub(billingPriceRub(props.plans.standard)))

const perStart = computed(() => perProjectLine(billingPriceRub(props.plans.start), props.plans.start.max_projects))
const perBasic = computed(() => perProjectLine(billingPriceRub(props.plans.basic), props.plans.basic.max_projects))
const perStandard = computed(() =>
  perProjectLine(billingPriceRub(props.plans.standard), props.plans.standard.max_projects)
)

function bulletLines(plan) {
  const code = plan.code
  return [
    projectBullet(plan),
    channelsBullet(code),
    usersBullet(code),
    aiBullet(plan),
    'Экспорт отчетов,<br>отправка по расписанию',
  ].filter(Boolean)
}

const linesStart = computed(() => bulletLines(props.plans.start))
const linesBasic = computed(() => bulletLines(props.plans.basic))
const linesStandard = computed(() => bulletLines(props.plans.standard))

const trialStart = computed(() => trialPhrase(props.plans.start.trial_days))
const trialBasic = computed(() => trialPhrase(props.plans.basic.trial_days))
const trialStandard = computed(() => trialPhrase(props.plans.standard.trial_days))

const wlLines = [
  'Отчеты без логотипа сервиса',
  'Брендирование отчетов',
  'Использование платформы<br>как собственной системы аналитики',
  'Собственный домен',
]
</script>
