<template>
  <section v-if="card" class="trial-card" aria-label="Пробный период">
    <header><div><strong>{{ card.title }}</strong><span>{{ card.days }}</span></div><img src="/admirra/img/fox/welcome-create.png" alt="" width="40" height="40" /></header>
    <div class="trial-card__progress" aria-hidden="true"><i :style="{ width: `${card.progress}%` }" /></div>
    <p>{{ card.text }}</p>
    <button type="button" @click="$emit('navigate', card)">{{ card.action }}</button>
    <a href="https://t.me/+AoZ2hLbwrHA3N2Ni" target="_blank" rel="noopener noreferrer" @click="$emit('support')">Поможем в Telegram</a>
  </section>
</template>
<script setup>
import { computed } from 'vue'
import { trialCard } from '@/utils/onboarding'
const props = defineProps({ state: { type: Object, required: true } })
defineEmits(['navigate', 'support'])
const card = computed(() => trialCard(props.state))
</script>
<style scoped>
.trial-card { margin:18px 12px 4px; padding:12px 14px; border:1px solid #f6d9c4; border-radius:12px; background:#fff4ec; color:#5e2f0d; font-size:11px; line-height:1.5; overflow-wrap:anywhere }
.trial-card header { display:flex; align-items:flex-start; justify-content:space-between; gap:8px }
.trial-card header div { min-width:0 }
.trial-card strong { display:block; font-size:12px; font-weight:700; line-height:1.4 }
.trial-card header span { color:#8a4b1e; display:block; margin-top:3px }
.trial-card img { flex:none; width:40px; height:40px; border-radius:50%; object-fit:cover; background:#f2decb }
.trial-card__progress { height:3px; background:#f2decb; border-radius:4px; margin:18px 0 10px; overflow:hidden }
.trial-card__progress i { display:block; height:100%; background:#e8843c }
.trial-card p { margin:0 0 9px }
.trial-card button { display:block; width:100%; min-height:32px; border:0; border-radius:7px; background:#2f6bea; color:white; font:inherit; font-weight:600; padding:6px 8px; cursor:pointer }
.trial-card button:hover { background:#245acb }
.trial-card a { display:block; color:#795033; text-align:center; margin-top:9px; text-underline-offset:3px }
.trial-card a:hover { text-decoration:underline }
.trial-card :is(button,a):focus-visible { outline:2px solid #2f6bea; outline-offset:3px }
:global(.dark .trial-card) { background:#302820; border-color:#65503c; color:#ffe0c4 }
:global(.dark .trial-card header span), :global(.dark .trial-card a) { color:#e8bd99 }
@media (max-width:767px) { .trial-card button { min-height:44px } .trial-card a { padding:6px 0 } }
</style>
