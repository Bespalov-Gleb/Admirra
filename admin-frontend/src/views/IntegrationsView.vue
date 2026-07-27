<template>
  <div>
    <PageHeader title="Интеграции" description="Состояние внешних сервисов и подключений клиентов." eyebrow="Инфраструктура">
      <button class="button button--secondary" @click="load"><ArrowPathIcon />Обновить</button>
    </PageHeader>
    <LoadingState v-if="loading" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <div v-else class="provider-grid">
      <article v-for="provider in providers" :key="provider.id" class="provider-card">
        <div class="provider-card__top">
          <span class="provider-logo">{{ providerInitial(provider) }}</span>
          <UiBadge :label="statusLabel(provider.status)" :tone="provider.status === 'connected' ? 'success' : provider.status === 'coming_soon' ? 'neutral' : 'danger'" dot />
        </div>
        <div><h2>{{ provider.name }}</h2><p>{{ provider.category || category(provider.id) }}</p></div>
        <dl>
          <template v-if="masked(provider)"><dt>Ключ</dt><dd>{{ masked(provider) }}</dd></template>
          <template v-if="provider.connections"><dt>Подключено</dt><dd>{{ number(provider.connections.total_connected || 0) }}</dd></template>
          <template v-if="provider.connections?.failed_sync_count"><dt>Ошибки синхронизации</dt><dd class="negative">{{ number(provider.connections.failed_sync_count) }}</dd></template>
          <template v-if="provider.spend_usd_month != null"><dt>Расход за месяц</dt><dd>{{ usd(provider.spend_usd_month) }}</dd></template>
          <template v-for="(value, key) in provider.stats || {}" :key="key"><dt>{{ statLabel(key) }}</dt><dd>{{ typeof value === 'number' ? number(value) : value }}</dd></template>
        </dl>
        <footer>
          <button class="button button--secondary" :disabled="provider.status === 'coming_soon' || testing === provider.id" @click="test(provider)"><BeakerIcon />{{ testing === provider.id ? 'Проверяем…' : 'Проверить' }}</button>
          <button class="button button--ghost" :disabled="provider.status === 'coming_soon'" @click="editProvider = provider; secret = ''"><KeyIcon />Сменить ключ</button>
        </footer>
      </article>
    </div>
    <AppModal :open="Boolean(editProvider)" :title="`Обновить ${editProvider?.name || ''}`" eyebrow="Секретный ключ" @close="editProvider = null">
      <div class="alert-banner alert-banner--warning"><ExclamationTriangleIcon /><div><strong>Осторожно</strong><p>Backend сохранит ключ в защищённом хранилище, но часть интеграций пока не переключает runtime-конфигурацию автоматически.</p></div></div>
      <label class="field"><span>Новый ключ или токен</span><textarea v-model="secret" rows="4" autocomplete="off" placeholder="Вставьте значение" /></label>
      <template #footer><button class="button button--secondary" @click="editProvider = null">Отмена</button><button class="button button--primary" :disabled="!secret.trim() || saving" @click="save">{{ saving ? 'Сохраняем…' : 'Сохранить и проверить' }}</button></template>
    </AppModal>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ArrowPathIcon, BeakerIcon, ExclamationTriangleIcon, KeyIcon } from '@heroicons/vue/24/outline'
import api, { apiError } from '../api/client'
import { number, usd } from '../utils/formatters'
import { useToast } from '../composables/useToast'
import PageHeader from '../components/PageHeader.vue'
import UiBadge from '../components/UiBadge.vue'
import LoadingState from '../components/LoadingState.vue'
import ErrorState from '../components/ErrorState.vue'
import AppModal from '../components/AppModal.vue'
const toast = useToast()
const providers = ref([]); const loading = ref(true); const error = ref(''); const testing = ref(''); const editProvider = ref(null); const secret = ref(''); const saving = ref(false)
const providerInitial = (provider) => ({ openai: 'AI', yandex_direct: 'Я', vk_ads: 'VK', unisender: 'U', telegram: 'TG', cloudpayments: 'CP', max_messenger: 'M' })[provider.id] || provider.name?.[0]
const statusLabel = (status) => ({ connected: 'Подключено', disconnected: 'Не подключено', coming_soon: 'Скоро' })[status] || status
const category = (id) => ({ yandex_direct: 'Рекламная аналитика', vk_ads: 'Рекламная аналитика', unisender: 'Email-рассылки', telegram: 'Доставка отчётов', cloudpayments: 'Платежи', max_messenger: 'Доставка отчётов' })[id] || 'Внешний сервис'
const masked = (p) => p.secret_masked || p.client_id_masked || p.app_id_masked || p.token_masked || p.public_id_masked
const statLabel = (key) => ({ sent_month: 'Отправлено за месяц', open_rate_percent: 'Open rate', errors: 'Ошибки', chats: 'Чаты', transactions_month: 'Транзакции', successful: 'Успешно', declined: 'Отклонено' })[key] || key
async function load() { loading.value = true; error.value = ''; try { providers.value = (await api.get('/admin/integrations')).data.providers || [] } catch (err) { error.value = apiError(err) } finally { loading.value = false } }
async function test(provider) { testing.value = provider.id; try { const { data } = await api.post(`/admin/integrations/${provider.id}/test`); data.ok === false ? toast.error(data.message || 'Проверка не пройдена') : toast.success('Проверка выполнена') } catch (err) { toast.error(apiError(err)) } finally { testing.value = '' } }
async function save() { saving.value = true; try { await api.put(`/admin/integrations/${editProvider.value.id}`, { secret: secret.value }); toast.success('Ключ сохранён'); editProvider.value = null; await load() } catch (err) { toast.error(apiError(err)) } finally { saving.value = false } }
onMounted(load)
</script>
