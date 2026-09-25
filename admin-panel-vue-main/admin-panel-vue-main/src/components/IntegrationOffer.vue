<template>
  <button v-if="canOffer(state)" class="integration-offer" type="button" @click="clicked">
    Подключите первый кабинет — закрепим <strong>скидку 20% на первую оплату</strong> до {{ trialDate(state.trial_ends_at) }}
  </button>
</template>
<script setup>
import { canOffer, trialDate } from '@/utils/onboarding'
import { markOfferEntry } from '@/utils/onboardingAnalytics'
import { trackFirstMilestone } from '@/utils/metrika'
defineProps({ state: { type: Object, required: true } })
const emit = defineEmits(['activate'])
function clicked() { markOfferEntry(); trackFirstMilestone('signup_offer_click'); emit('activate') }
</script>
<style scoped>
.integration-offer { display:block; width:100%; margin:0 0 20px; padding:12px 16px; border:1px solid #f6d9c4; border-radius:10px; background:#fff4ec; color:#5e2f0d; text-align:left; font:inherit; font-size:13px; line-height:1.6; cursor:pointer }
.integration-offer:focus-visible { outline:2px solid #2f6bea; outline-offset:3px }
:global(.dark .integration-offer) { background:#302820; border-color:#65503c; color:#ffe0c4 }
</style>
