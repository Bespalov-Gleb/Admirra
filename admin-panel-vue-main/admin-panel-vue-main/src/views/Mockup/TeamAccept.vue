<template>
  <div class="mx-auto w-full max-w-md rounded-2xl border border-gray-200 bg-white p-8 shadow-sm dark:border-white/10 dark:bg-[#2C2F3D]">
    <h1 class="mb-2 text-2xl font-semibold text-gray-900 dark:text-white">Приглашение в команду</h1>

    <div v-if="loading" class="py-8 text-center text-sm text-gray-500 dark:text-white/55">Проверка приглашения…</div>

    <div v-else-if="!preview?.valid" class="space-y-4">
      <p class="text-sm text-gray-600 dark:text-white/70">
        Ссылка недействительна или срок приглашения истёк. Попросите владельца аккаунта отправить приглашение повторно.
      </p>
      <router-link to="/signin" class="inline-block text-sm font-medium text-blue-600 hover:underline dark:text-blue-400">
        Перейти ко входу
      </router-link>
    </div>

    <div v-else class="space-y-4">
      <p class="text-sm text-gray-600 dark:text-white/70">
        <span v-if="preview.account_name" class="font-medium text-gray-900 dark:text-white">{{ preview.account_name }}</span>
        <span v-else>Команда AdMirra</span>
        приглашает вас
        <span class="font-medium">{{ roleLabel }}</span>
        <span v-if="preview.inviter_email"> (от {{ preview.inviter_email }})</span>.
      </p>
      <p v-if="preview.invite_email" class="text-xs text-gray-500 dark:text-white/50">
        Приглашение для: {{ preview.invite_email }}
      </p>

      <div v-if="isAuth" class="flex flex-col gap-3 pt-2">
        <button
          type="button"
          class="w-full rounded-lg bg-gray-900 py-3 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50 dark:bg-blue-600 dark:hover:bg-blue-500"
          :disabled="accepting"
          @click="acceptInvite"
        >
          {{ accepting ? 'Принимаем…' : 'Принять приглашение' }}
        </button>
        <p v-if="acceptError" class="text-sm text-red-600 dark:text-red-400">{{ acceptError }}</p>
      </div>

      <div v-else class="flex flex-col gap-3 pt-2">
        <router-link
          :to="{ path: '/signin', query: { redirect: acceptRedirect } }"
          class="block w-full rounded-lg bg-gray-900 py-3 text-center text-sm font-medium text-white hover:bg-gray-800 dark:bg-blue-600 dark:hover:bg-blue-500"
        >
          Войти и принять
        </router-link>
        <router-link
          :to="{ path: '/signup', query: { invite: token } }"
          class="block w-full rounded-lg border border-gray-300 py-3 text-center text-sm font-medium text-gray-800 hover:bg-gray-50 dark:border-white/15 dark:text-white/85 dark:hover:bg-white/5"
        >
          Зарегистрироваться
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import api from '../../api/axios'
import { useAuth } from '../../composables/useAuth'
import { DEFAULT_DASHBOARD_PATH } from '../../constants/config'

const route = useRoute()
const router = useRouter()
const { isAuthenticated } = useAuth()

const token = computed(() => String(route.query.token || '').trim())
const acceptRedirect = computed(() => `/team/accept?token=${encodeURIComponent(token.value)}`)
const isAuth = computed(() => isAuthenticated.value)

const loading = ref(true)
const preview = ref(null)
const accepting = ref(false)
const acceptError = ref('')

const roleLabel = computed(() => {
  if (!preview.value?.role) return 'в команду'
  return preview.value.role === 'client' ? 'как клиента' : 'как сотрудника'
})

async function loadPreview() {
  if (!token.value) {
    preview.value = { valid: false }
    loading.value = false
    return
  }
  loading.value = true
  try {
    const { data } = await axios.get('/api/team/invites/preview', { params: { token: token.value } })
    preview.value = data
  } catch {
    preview.value = { valid: false }
  } finally {
    loading.value = false
  }
}

async function acceptInvite() {
  acceptError.value = ''
  accepting.value = true
  try {
    await api.post('/team/invites/accept', { token: token.value })
    router.push(DEFAULT_DASHBOARD_PATH)
  } catch (e) {
    acceptError.value = e?.response?.data?.detail || 'Не удалось принять приглашение'
  } finally {
    accepting.value = false
  }
}

onMounted(loadPreview)
watch(token, loadPreview)
</script>
