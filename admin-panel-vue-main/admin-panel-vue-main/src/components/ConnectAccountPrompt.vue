<template>
  <section class="connect-account-prompt">
    <img src="/admirra/img/fox/welcome-create.png" alt="" width="48" height="48" />
    <div><h3>Остался один шаг — подключите кабинет</h3>
      <p>Данные появятся здесь через несколько минут.<template v-if="offer"> До {{ trialDate(state.trial_ends_at) }} всё бесплатно, а за первый кабинет закрепим <strong>скидку 20% на первую оплату</strong></template></p>
    </div>
    <button type="button" @click="connect">Подключить кабинет</button>
  </section>
</template>
<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { canOffer, trialDate } from '@/utils/onboarding'
import { markOfferEntry } from '@/utils/onboardingAnalytics'
import { trackFirstMilestone } from '@/utils/metrika'
const props = defineProps({ clientId: { type: String, required: true }, state: { type: Object, required: true } })
const router = useRouter(), offer = computed(() => canOffer(props.state))
function connect() {
  if (offer.value) { markOfferEntry(); trackFirstMilestone('signup_offer_click') }
  router.push({ path: '/integrations/wizard', query: { client_id: props.clientId } })
}
</script>
<style scoped>
.connect-account-prompt { display:flex; align-items:center; gap:14px; padding:14px 16px; border:1px solid #f6d9c4; border-radius:12px; background:#fff4ec; color:#5e2f0d }
.connect-account-prompt img { width:48px; height:48px; flex:none; border-radius:50%; object-fit:cover; background:#f2decb }
.connect-account-prompt div { flex:1; min-width:0 }
.connect-account-prompt h3 { margin:0 0 5px; font-size:15px; font-weight:700; line-height:1.4 }
.connect-account-prompt p { margin:0; font-size:12px; line-height:1.6 }
.connect-account-prompt button { border:0; background:#2f6bea; color:white; font-size:12px; font-weight:600; border-radius:8px; padding:12px 18px; flex:none; cursor:pointer }
.connect-account-prompt button:hover { background:#245acb }
.connect-account-prompt button:focus-visible { outline:2px solid #2f6bea; outline-offset:3px }
:global(.dark .connect-account-prompt) { background:#302820; border-color:#65503c; color:#ffe0c4 }
@media(max-width:640px) { .connect-account-prompt { flex-wrap:wrap; gap:10px } .connect-account-prompt img { width:40px; height:40px } .connect-account-prompt button { width:100%; min-height:44px } }
</style>
