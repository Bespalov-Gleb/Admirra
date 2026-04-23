<template>
  <div class="min-h-[200px]">
    <div v-if="loading" class="flex justify-center py-24 text-gray-500 dark:text-gray-400 text-sm font-medium">
      Загрузка тарифов…
    </div>
    <template v-else>
      <PricingDark
        v-if="isDarkMode"
        :plans="resolvedPlans"
        :paying="paying"
        @subscribe="onSubscribe"
        @contact-wl="onContactWl"
      />
      <PricingLight
        v-else
        :plans="resolvedPlans"
        :paying="paying"
        @subscribe="onSubscribe"
        @contact-wl="onContactWl"
      />
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api/axios'
import { useAuth } from '@/composables/useAuth'
import { useTheme } from '@/composables/useTheme'
import { useToaster } from '@/composables/useToaster'
import { payWithCloudPayments } from '@/composables/useBillingCloudPayments'
import { normalizePlansFromApi } from '@/utils/pricingPlans'
import PricingLight from '@/components/pricing/PricingLight.vue'
import PricingDark from '@/components/pricing/PricingDark.vue'

const router = useRouter()
const { isDarkMode } = useTheme()
const toaster = useToaster()
const { fetchCurrentUser } = useAuth()

const loading = ref(true)
const plans = ref(null)
const paying = ref(null)

const resolvedPlans = computed(() => plans.value || normalizePlansFromApi([]))

onMounted(async () => {
  try {
    const { data } = await api.get('billing/plans')
    plans.value = normalizePlansFromApi(data)
  } catch (e) {
    const d = e?.response?.data?.detail
    toaster.error(typeof d === 'string' ? d : 'Не удалось загрузить тарифы')
    plans.value = normalizePlansFromApi([])
  } finally {
    loading.value = false
  }
})

async function onSubscribe(planCode, billingPeriod = 'month') {
  paying.value = planCode
  try {
    const { data } = await api.post('billing/subscribe', {
      plan_code: planCode,
      billing_period: billingPeriod,
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
      billing_period: data.billing_period || billingPeriod,
      recurrent: data.recurrent || null,
    })
    if (result.status === 'cancelled') {
      return
    }
    toaster.success('Оплата успешно выполнена')
    await fetchCurrentUser()
  } catch (e) {
    const d = e?.response?.data?.detail
    const msg = typeof d === 'string' ? d : e?.message
    if (msg) {
      toaster.error(msg || 'Не удалось начать оплату')
    }
  } finally {
    paying.value = null
  }
}

function onContactWl() {
  router.push('/contact')
}
</script>
