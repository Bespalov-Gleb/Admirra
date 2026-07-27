<template>
  <main class="auth-page">
    <section class="auth-aside">
      <div class="auth-aside__brand"><span class="brand__mark">A</span><strong>AdMirra</strong></div>
      <div class="auth-aside__copy">
        <span class="eyebrow eyebrow--light">Internal operations</span>
        <h1>Всё важное о сервисе — в одном месте.</h1>
        <p>Пользователи, поддержка, AI-лимиты, интеграции и контент. Доступ только для внутренней команды.</p>
      </div>
      <div class="auth-aside__security"><ShieldCheckIcon /><span><strong>Изолированный контур</strong><small>Отдельная авторизация и роли сотрудников</small></span></div>
    </section>

    <section class="auth-form-wrap">
      <form class="auth-card" @submit.prevent="submit">
        <div class="auth-card__heading">
          <span class="auth-card__icon"><LockClosedIcon /></span>
          <div><p class="eyebrow">Внутренняя панель</p><h2>{{ mfaToken ? 'Подтверждение входа' : 'Войти в AdMirra' }}</h2></div>
        </div>

        <template v-if="!mfaToken">
          <label class="field">
            <span>Рабочая почта</span>
            <input v-model.trim="form.email" type="email" autocomplete="username" placeholder="name@admirra.ru" required />
          </label>
          <label class="field">
            <span>Пароль</span>
            <div class="password-input">
              <input v-model="form.password" :type="showPassword ? 'text' : 'password'" autocomplete="current-password" placeholder="Введите пароль" required />
              <button type="button" @click="showPassword = !showPassword"><EyeSlashIcon v-if="showPassword" /><EyeIcon v-else /></button>
            </div>
          </label>
        </template>

        <template v-else>
          <p class="auth-help">Введите код из приложения-аутентификатора. Если доступа к нему нет, используйте один из recovery-кодов.</p>
          <div class="segmented">
            <button type="button" :class="{ active: mfaMode === 'totp' }" @click="mfaMode = 'totp'">Код TOTP</button>
            <button type="button" :class="{ active: mfaMode === 'recovery' }" @click="mfaMode = 'recovery'">Recovery-код</button>
          </div>
          <label class="field">
            <span>{{ mfaMode === 'totp' ? 'Шестизначный код' : 'Recovery-код' }}</span>
            <input v-model.trim="mfaCode" :inputmode="mfaMode === 'totp' ? 'numeric' : 'text'" :maxlength="mfaMode === 'totp' ? 6 : 64" autofocus required />
          </label>
        </template>

        <div v-if="error" class="form-error"><ExclamationCircleIcon />{{ error }}</div>
        <button class="button button--primary button--large button--full" :disabled="loading">
          <span v-if="loading" class="spinner" />{{ loading ? 'Проверяем…' : mfaToken ? 'Подтвердить вход' : 'Продолжить' }}
        </button>
        <button v-if="mfaToken" type="button" class="button button--ghost button--full" @click="resetMfa">Вернуться назад</button>
        <p class="auth-notice">Вход и действия сотрудников записываются в журнал аудита.</p>
      </form>
    </section>
  </main>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ExclamationCircleIcon, EyeIcon, EyeSlashIcon, LockClosedIcon, ShieldCheckIcon } from '@heroicons/vue/24/outline'
import { useAuthStore } from '../stores/auth'
import { apiError } from '../api/client'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const form = reactive({ email: '', password: '' })
const loading = ref(false)
const error = ref('')
const showPassword = ref(false)
const mfaToken = ref('')
const mfaCode = ref('')
const mfaMode = ref('totp')

async function submit() {
  error.value = ''
  loading.value = true
  try {
    const payload = mfaToken.value
      ? { email: form.email, password: form.password, mfa_token: mfaToken.value, [mfaMode.value === 'totp' ? 'totp_code' : 'recovery_code']: mfaCode.value }
      : form
    const data = await auth.login(payload)
    if (data.requires_2fa) {
      mfaToken.value = data.mfa_token
      mfaCode.value = ''
      return
    }
    await auth.fetchMe()
    router.replace(route.query.next || auth.homeRoute)
  } catch (err) {
    error.value = apiError(err)
  } finally {
    loading.value = false
  }
}

function resetMfa() {
  mfaToken.value = ''
  mfaCode.value = ''
  error.value = ''
}
</script>
