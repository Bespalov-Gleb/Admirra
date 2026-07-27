<template>
  <main class="centered-page">
    <section class="auth-card auth-card--invite">
      <span class="auth-card__icon"><UserPlusIcon /></span>
      <p class="eyebrow">Приглашение в команду</p>
      <h1>Создайте пароль</h1>
      <p class="muted">После активации вы войдёте во внутреннюю панель. Пароль должен содержать не менее 8 символов.</p>
      <form v-if="!completed" @submit.prevent="activate">
        <label class="field"><span>Новый пароль</span><input v-model="password" type="password" minlength="8" autocomplete="new-password" required /></label>
        <label class="field"><span>Повторите пароль</span><input v-model="confirmPassword" type="password" minlength="8" autocomplete="new-password" required /></label>
        <div v-if="error" class="form-error"><ExclamationCircleIcon />{{ error }}</div>
        <button class="button button--primary button--large button--full" :disabled="loading">{{ loading ? 'Активируем…' : 'Активировать аккаунт' }}</button>
      </form>
      <div v-else class="success-panel">
        <CheckCircleIcon /><strong>Аккаунт активирован</strong><p>Теперь можно перейти в панель.</p>
        <div class="row-actions">
          <button class="button button--secondary" @click="finish('/profile')">Настроить 2FA</button>
          <button class="button button--primary" @click="finish()">Открыть панель</button>
        </div>
      </div>
    </section>
  </main>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { CheckCircleIcon, ExclamationCircleIcon, UserPlusIcon } from '@heroicons/vue/24/outline'
import api, { apiError } from '../api/client'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const password = ref('')
const confirmPassword = ref('')
const loading = ref(false)
const completed = ref(false)
const error = ref('')

async function activate() {
  error.value = ''
  if (password.value !== confirmPassword.value) {
    error.value = 'Пароли не совпадают'
    return
  }
  loading.value = true
  try {
    const { data } = await api.post('/auth/invite/accept', { token: route.params.token, password: password.value })
    auth.setToken(data.access_token)
    completed.value = true
  } catch (err) {
    const message = apiError(err)
    error.value = /expired|invalid|not found/i.test(message) ? 'Ссылка устарела или уже была использована' : message
  } finally {
    loading.value = false
  }
}

async function finish(target = '') {
  await auth.fetchMe()
  router.replace(target || auth.homeRoute)
}
</script>
