<template>
  <div>
    <PageHeader title="Профиль сотрудника" description="Личные данные и второй фактор входа." eyebrow="Аккаунт" />
    <div class="profile-grid">
      <section class="panel">
        <div class="profile-card">
          <span class="avatar avatar--xl">{{ initials }}</span>
          <div><h2>{{ auth.user?.full_name || auth.user?.email }}</h2><p>{{ auth.user?.email }}</p><UiBadge :label="roleLabel(auth.role)" tone="info" /></div>
        </div>
        <dl class="info-list"><div><dt>ID сотрудника</dt><dd>{{ auth.user?.id }}</dd></div><div><dt>Роль</dt><dd>{{ auth.user?.role_label }}</dd></div><div><dt>Контур</dt><dd>Internal Admin</dd></div></dl>
      </section>
      <section class="panel">
        <div class="panel__header"><div><p class="eyebrow">Безопасность</p><h2>Двухфакторная аутентификация</h2></div><ShieldCheckIcon /></div>
        <p class="muted">Подключите приложение-аутентификатор. При следующем входе после пароля потребуется одноразовый код.</p>
        <div v-if="!setup" class="row-actions row-actions--left">
          <button class="button button--primary" @click="begin2fa"><QrCodeIcon />Настроить 2FA</button>
          <button class="button button--secondary" @click="disableOpen = true">Отключить существующую 2FA</button>
        </div>
        <div v-else class="twofa-setup">
          <img v-if="qrDataUrl" :src="qrDataUrl" alt="QR-код для 2FA" />
          <div><strong>Отсканируйте QR-код</strong><p>Или введите секрет вручную:</p><code>{{ setup.secret }}</code></div>
          <label class="field"><span>Код из приложения</span><input v-model.trim="verifyCode" inputmode="numeric" maxlength="6" placeholder="000000" /></label>
          <button class="button button--primary" :disabled="verifyCode.length !== 6" @click="confirm2fa">Подтвердить</button>
        </div>
      </section>
    </div>
    <AppModal :open="recoveryCodes.length > 0" title="Сохраните recovery-коды" eyebrow="Важно" @close="recoveryCodes = []">
      <div class="alert-banner alert-banner--warning"><ExclamationTriangleIcon /><div><strong>Коды показываются один раз</strong><p>Сохраните их в менеджере паролей. Каждый код работает только один раз.</p></div></div>
      <div class="recovery-grid"><code v-for="code in recoveryCodes" :key="code">{{ code }}</code></div>
      <template #footer><button class="button button--secondary" @click="copyCodes">Скопировать</button><button class="button button--primary" @click="recoveryCodes = []">Я сохранил коды</button></template>
    </AppModal>
    <AppModal :open="disableOpen" title="Отключить 2FA" eyebrow="Подтверждение" @close="disableOpen = false">
      <p class="muted modal-copy">Введите пароль и текущий TOTP-код или recovery-код.</p>
      <div class="form-grid">
        <label class="field field--wide"><span>Пароль</span><input v-model="disableForm.password" type="password" autocomplete="current-password" /></label>
        <label class="field"><span>TOTP-код</span><input v-model.trim="disableForm.code" inputmode="numeric" maxlength="6" /></label>
        <label class="field"><span>Или recovery-код</span><input v-model.trim="disableForm.recovery_code" /></label>
      </div>
      <template #footer><button class="button button--secondary" @click="disableOpen = false">Отмена</button><button class="button button--danger" :disabled="!disableForm.password || (!disableForm.code && !disableForm.recovery_code)" @click="disable2fa">Отключить 2FA</button></template>
    </AppModal>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import QRCode from 'qrcode'
import { ExclamationTriangleIcon, QrCodeIcon, ShieldCheckIcon } from '@heroicons/vue/24/outline'
import api, { apiError } from '../api/client'
import { roleLabel } from '../utils/formatters'
import { useAuthStore } from '../stores/auth'
import { useToast } from '../composables/useToast'
import PageHeader from '../components/PageHeader.vue'
import UiBadge from '../components/UiBadge.vue'
import AppModal from '../components/AppModal.vue'
const auth = useAuthStore(); const toast = useToast(); const setup = ref(null); const qrDataUrl = ref(''); const verifyCode = ref(''); const recoveryCodes = ref([]); const disableOpen = ref(false)
const disableForm = reactive({ password: '', code: '', recovery_code: '' })
const initials = computed(() => (auth.user?.full_name || auth.user?.email || '?').split(/\s|@/).filter(Boolean).slice(0, 2).map((x) => x[0]).join('').toUpperCase())
async function begin2fa() { try { setup.value = (await api.post('/auth/2fa/enable')).data; qrDataUrl.value = await QRCode.toDataURL(setup.value.provisioning_uri, { width: 220, margin: 1, color: { dark: '#172033', light: '#ffffff' } }) } catch (err) { toast.error(apiError(err)) } }
async function confirm2fa() { try { const { data } = await api.post('/auth/2fa/verify', { code: verifyCode.value, setup_confirm: true }); recoveryCodes.value = data.recovery_codes || []; setup.value = null; verifyCode.value = ''; toast.success('2FA включена') } catch (err) { toast.error(apiError(err)) } }
async function disable2fa() { try { await api.post('/auth/2fa/disable', { password: disableForm.password, code: disableForm.code || null, recovery_code: disableForm.recovery_code || null }); disableOpen.value = false; Object.assign(disableForm, { password: '', code: '', recovery_code: '' }); toast.success('2FA отключена') } catch (err) { toast.error(apiError(err)) } }
async function copyCodes() { await navigator.clipboard.writeText(recoveryCodes.value.join('\n')); toast.success('Коды скопированы') }
</script>
