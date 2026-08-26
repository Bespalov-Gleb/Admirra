<template>
  <div>
    <PageHeader title="Промокоды" description="Скидки на первый платёж тарифа и статистика их использования." eyebrow="Монетизация">
      <button class="button button--secondary" @click="load"><ArrowPathIcon />Обновить</button>
      <button class="button button--primary" @click="openCreate"><PlusIcon />Новый промокод</button>
    </PageHeader>

    <LoadingState v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <template v-else>
      <div class="kpi-grid kpi-grid--4">
        <article class="kpi-card"><div class="kpi-card__top"><span>Всего кодов</span><ReceiptPercentIcon /></div><strong>{{ number(items.length) }}</strong><small class="muted">{{ number(activeCount) }} активных</small></article>
        <article class="kpi-card"><div class="kpi-card__top"><span>Погашений</span><CheckCircleIcon /></div><strong>{{ number(totalRedemptions) }}</strong><small class="muted">оплат со скидкой</small></article>
        <article class="kpi-card"><div class="kpi-card__top"><span>Уникальных пользователей</span><UsersIcon /></div><strong>{{ number(totalUsers) }}</strong><small class="muted">оплатили с промокодом</small></article>
        <article class="kpi-card"><div class="kpi-card__top"><span>Выдано скидок</span><BanknotesIcon /></div><strong>{{ money(totalDiscount) }}</strong><small class="muted">выручка {{ money(totalRevenue) }}</small></article>
      </div>

      <section class="panel">
        <div class="panel__header"><div><p class="eyebrow">Список</p><h2>Промокоды</h2></div></div>
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>Код</th><th>Скидка</th><th>Статус</th><th>Лимиты</th><th>Действует</th>
                <th class="num">Погашений</th><th class="num">Юзеров</th><th class="num">Скидок</th><th class="num">Выручка</th><th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in items" :key="p.id">
                <td>
                  <strong class="promo-code">{{ p.code }}</strong>
                  <small v-if="p.description" class="muted promo-desc">{{ p.description }}</small>
                  <small v-if="p.applies_to_plans?.length" class="muted promo-desc">тарифы: {{ p.applies_to_plans.map(planLabel).join(', ') }}</small>
                  <small v-if="p.monthly_only" class="muted promo-desc">только помесячно</small>
                </td>
                <td><strong>−{{ p.discount_percent }}%</strong></td>
                <td>
                  <UiBadge v-if="p.active" label="Активен" tone="success" dot />
                  <UiBadge v-else label="Выключен" tone="neutral" dot />
                </td>
                <td>
                  <small class="muted">на юзера: {{ p.per_user_limit === 0 ? '∞' : p.per_user_limit }}</small><br />
                  <small class="muted">всего: {{ p.max_redemptions == null ? '∞' : number(p.max_redemptions) }}</small>
                </td>
                <td><small class="muted">{{ validityLabel(p) }}</small></td>
                <td class="num"><button class="linklike" :disabled="!p.redemptions" @click="openRedemptions(p)">{{ number(p.redemptions) }}</button></td>
                <td class="num">{{ number(p.unique_users) }}</td>
                <td class="num">{{ money(p.total_discount) }}</td>
                <td class="num">{{ money(p.total_revenue) }}</td>
                <td class="row-actions">
                  <button class="button button--tiny button--secondary" @click="toggleActive(p)">{{ p.active ? 'Выкл' : 'Вкл' }}</button>
                  <button class="button button--tiny button--secondary" @click="openEdit(p)">Изменить</button>
                  <button class="button button--tiny button--danger" @click="remove(p)">Удалить</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <EmptyState v-if="!items.length" title="Промокодов пока нет" description="Создайте первый промокод кнопкой выше." />
      </section>
    </template>

    <!-- Создание / редактирование -->
    <AppModal :open="formOpen" :title="editing ? 'Редактировать промокод' : 'Новый промокод'" eyebrow="Промокод" @close="formOpen = false">
      <div class="form-grid">
        <label class="field"><span>Код</span><input v-model="form.code" :disabled="editing" type="text" placeholder="WELCOME20" @input="form.code = form.code.toUpperCase()" /></label>
        <label class="field"><span>Скидка, %</span><input v-model.number="form.discount_percent" type="number" min="1" max="100" /></label>
        <label class="field field--wide"><span>Описание (для админов)</span><input v-model="form.description" type="text" placeholder="Приветственная скидка" /></label>
        <label class="field"><span>Лимит на пользователя</span><input v-model.number="form.per_user_limit" type="number" min="0" /><small class="muted">0 — без ограничения</small></label>
        <label class="field"><span>Глобальный лимит</span><input v-model.number="form.max_redemptions" type="number" min="1" placeholder="∞" /></label>
        <label class="field"><span>Действует с</span><input v-model="form.valid_from" type="datetime-local" /></label>
        <label class="field"><span>Действует до</span><input v-model="form.valid_until" type="datetime-local" /></label>
        <label class="field field--check"><input v-model="form.monthly_only" type="checkbox" /><span>Только при помесячной оплате</span></label>
        <label class="field field--check"><input v-model="form.active" type="checkbox" /><span>Активен</span></label>
        <div class="field field--wide">
          <span>Тарифы (пусто — любые)</span>
          <div class="chips">
            <label v-for="pl in PLAN_CODES" :key="pl" class="chip-check">
              <input v-model="form.applies_to_plans" type="checkbox" :value="pl" />{{ planLabel(pl) }}
            </label>
          </div>
        </div>
      </div>
      <template #footer>
        <button class="button button--secondary" @click="formOpen = false">Отмена</button>
        <button class="button button--primary" :disabled="saving" @click="save">{{ editing ? 'Сохранить' : 'Создать' }}</button>
      </template>
    </AppModal>

    <!-- Погашения -->
    <AppModal :open="redemptionsOpen" :title="`Погашения: ${redemptionsCode}`" eyebrow="Кто оплатил" wide @close="redemptionsOpen = false">
      <LoadingState v-if="redemptionsLoading" />
      <div v-else class="table-wrap">
        <table class="data-table">
          <thead><tr><th>Email</th><th>Тариф</th><th class="num">Скидка</th><th class="num">Оплачено</th><th>Дата</th></tr></thead>
          <tbody>
            <tr v-for="(r, i) in redemptions" :key="i">
              <td>{{ r.email }}</td>
              <td>{{ planLabel(r.plan_code) }} · {{ r.billing_period === 'year' ? 'год' : 'мес' }}</td>
              <td class="num">{{ money(r.discount_amount) }}</td>
              <td class="num">{{ money(r.final_amount) }}</td>
              <td>{{ moscowDateTime(r.redeemed_at) }}</td>
            </tr>
          </tbody>
        </table>
        <EmptyState v-if="!redemptions.length" title="Пока нет погашений" />
      </div>
    </AppModal>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ArrowPathIcon, BanknotesIcon, CheckCircleIcon, PlusIcon, ReceiptPercentIcon, UsersIcon } from '@heroicons/vue/24/outline'
import api, { apiError } from '../api/client'
import { money, number, planLabel, moscowDateTime } from '../utils/formatters'
import PageHeader from '../components/PageHeader.vue'
import LoadingState from '../components/LoadingState.vue'
import ErrorState from '../components/ErrorState.vue'
import EmptyState from '../components/EmptyState.vue'
import UiBadge from '../components/UiBadge.vue'
import AppModal from '../components/AppModal.vue'
import { useToast } from '../composables/useToast'

const toast = useToast()
const PLAN_CODES = ['start', 'agency', 'pro']

const loading = ref(true)
const error = ref('')
const items = ref([])

const activeCount = computed(() => items.value.filter((p) => p.active).length)
const totalRedemptions = computed(() => items.value.reduce((s, p) => s + (p.redemptions || 0), 0))
const totalUsers = computed(() => items.value.reduce((s, p) => s + (p.unique_users || 0), 0))
const totalDiscount = computed(() => items.value.reduce((s, p) => s + (p.total_discount || 0), 0))
const totalRevenue = computed(() => items.value.reduce((s, p) => s + (p.total_revenue || 0), 0))

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await api.get('/admin/promo-codes')
    items.value = data.items || []
  } catch (e) {
    error.value = apiError(e)
  } finally {
    loading.value = false
  }
}

function validityLabel(p) {
  const from = p.valid_from ? moscowDateTime(p.valid_from) : null
  const until = p.valid_until ? moscowDateTime(p.valid_until) : null
  if (!from && !until) return 'бессрочно'
  return `${from || '…'} — ${until || '…'}`
}

// ── Форма ────────────────────────────────────────────────────────────────
const formOpen = ref(false)
const editing = ref(null)
const saving = ref(false)
const form = ref(blankForm())

function blankForm() {
  return {
    code: '', description: '', discount_percent: 20, active: true,
    per_user_limit: 1, max_redemptions: null, valid_from: '', valid_until: '',
    monthly_only: false, applies_to_plans: [],
  }
}

function openCreate() {
  editing.value = null
  form.value = blankForm()
  formOpen.value = true
}

function openEdit(p) {
  editing.value = p
  form.value = {
    code: p.code, description: p.description || '', discount_percent: p.discount_percent,
    active: p.active, per_user_limit: p.per_user_limit, max_redemptions: p.max_redemptions,
    valid_from: toLocalInput(p.valid_from), valid_until: toLocalInput(p.valid_until),
    monthly_only: p.monthly_only, applies_to_plans: [...(p.applies_to_plans || [])],
  }
  formOpen.value = true
}

function toLocalInput(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function payload() {
  return {
    code: form.value.code.trim().toUpperCase(),
    description: form.value.description.trim() || null,
    discount_percent: Number(form.value.discount_percent),
    active: form.value.active,
    per_user_limit: Number(form.value.per_user_limit),
    max_redemptions: form.value.max_redemptions ? Number(form.value.max_redemptions) : null,
    valid_from: form.value.valid_from ? new Date(form.value.valid_from).toISOString() : null,
    valid_until: form.value.valid_until ? new Date(form.value.valid_until).toISOString() : null,
    monthly_only: form.value.monthly_only,
    applies_to_plans: form.value.applies_to_plans.length ? form.value.applies_to_plans : null,
  }
}

async function save() {
  saving.value = true
  try {
    if (editing.value) {
      const { code, ...body } = payload()
      await api.patch(`/admin/promo-codes/${editing.value.id}`, body)
      toast.success('Промокод обновлён')
    } else {
      await api.post('/admin/promo-codes', payload())
      toast.success('Промокод создан')
    }
    formOpen.value = false
    await load()
  } catch (e) {
    toast.error(apiError(e))
  } finally {
    saving.value = false
  }
}

async function toggleActive(p) {
  try {
    await api.patch(`/admin/promo-codes/${p.id}`, { active: !p.active })
    await load()
  } catch (e) {
    toast.error(apiError(e))
  }
}

async function remove(p) {
  if (!window.confirm(`Удалить промокод ${p.code}?`)) return
  try {
    await api.delete(`/admin/promo-codes/${p.id}`)
    toast.success('Промокод удалён')
    await load()
  } catch (e) {
    // 409 — код использовался, он деактивирован сервером
    toast.error(apiError(e))
    await load()
  }
}

// ── Погашения ────────────────────────────────────────────────────────────
const redemptionsOpen = ref(false)
const redemptionsLoading = ref(false)
const redemptions = ref([])
const redemptionsCode = ref('')

async function openRedemptions(p) {
  redemptionsCode.value = p.code
  redemptionsOpen.value = true
  redemptionsLoading.value = true
  redemptions.value = []
  try {
    const { data } = await api.get(`/admin/promo-codes/${p.id}/redemptions`)
    redemptions.value = data.items || []
  } catch (e) {
    toast.error(apiError(e))
  } finally {
    redemptionsLoading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: 0.86rem; }
.data-table th, .data-table td { padding: 0.6rem 0.7rem; text-align: left; border-bottom: 1px solid var(--border, #e6ebf2); vertical-align: top; }
.data-table th { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted, #8d99ad); font-weight: 700; }
.data-table th.num, .data-table td.num { text-align: right; font-variant-numeric: tabular-nums; }
.promo-code { font-family: 'SFMono-Regular', ui-monospace, monospace; letter-spacing: 0.02em; }
.promo-desc { display: block; margin-top: 0.15rem; }
.row-actions { display: flex; gap: 0.3rem; white-space: nowrap; }
.linklike { border: 0; background: none; color: var(--accent, #2f6bea); cursor: pointer; font: inherit; font-variant-numeric: tabular-nums; }
.linklike:disabled { color: inherit; cursor: default; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.85rem; }
.field { display: flex; flex-direction: column; gap: 0.3rem; }
.field--wide { grid-column: 1 / -1; }
.field--check { flex-direction: row; align-items: center; gap: 0.5rem; }
.field input[type="text"], .field input[type="number"], .field input[type="datetime-local"] { padding: 0.5rem 0.6rem; border: 1px solid var(--border, #e6ebf2); border-radius: 0.5rem; font: inherit; }
.field > span { font-size: 0.78rem; color: var(--muted, #8d99ad); font-weight: 600; }
.chips { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.chip-check { display: inline-flex; align-items: center; gap: 0.35rem; padding: 0.3rem 0.6rem; border: 1px solid var(--border, #e6ebf2); border-radius: 0.6rem; font-size: 0.85rem; cursor: pointer; }
.button--danger { background: #fdecec; color: #c0392b; }
</style>
