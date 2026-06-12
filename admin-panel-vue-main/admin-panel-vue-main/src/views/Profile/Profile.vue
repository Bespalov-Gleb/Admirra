<template>
  <div class="profile-page">
    <header class="profile-head">
      <h1>Профиль</h1>
      <p>Личные данные, безопасность и рабочие уведомления пользователя.</p>
    </header>

    <main class="profile-grid">
      <section class="profile-card profile-hero">
        <div class="avatar-wrap">
          <div class="avatar">
            <img v-if="form.avatarUrl" :src="form.avatarUrl" alt="Аватар" />
            <span v-else>{{ initials }}</span>
          </div>
          <label class="avatar-btn" title="Загрузить аватар">
            <CameraIcon class="w-[1.1111rem] h-[1.1111rem]" />
            <input type="file" accept="image/png,image/jpeg,image/webp" @change="uploadAvatar" />
          </label>
          <button v-if="form.avatarUrl" class="avatar-remove-btn" type="button" @click="deleteAvatar">
            Удалить
          </button>
        </div>
        <div class="hero-info">
          <h2>{{ displayName }}</h2>
          <p>{{ form.email }}</p>
          <span class="role-badge">{{ form.isActive ? 'Активно' : 'Неактивно' }}</span>
        </div>
      </section>

      <section class="profile-card profile-card--security">
        <div class="card-head">
          <div>
            <h2>Безопасность</h2>
            <p>Доступ к аккаунту и способы входа.</p>
          </div>
        </div>

        <div class="security-list">
          <div class="security-row">
            <div class="security-copy">
              <strong>Пароль</strong>
              <span>{{ passwordSubtitle }}</span>
            </div>
            <button class="ghost-btn" type="button" @click="passwordOpen = true">
              Изменить
            </button>
          </div>

          <div class="security-row">
            <div class="security-copy">
              <strong>Двухфакторная аутентификация</strong>
              <span>{{ form.twoFactorEnabled ? 'Включена' : 'Отключена' }}. При входе потребуется код из email.</span>
            </div>
            <button
              class="toggle"
              type="button"
              :class="{ 'toggle--on': form.twoFactorEnabled }"
              :disabled="twoFactorLoading"
              @click="toggleTwoFactor"
              :aria-pressed="form.twoFactorEnabled ? 'true' : 'false'"
            >
              <i></i>
            </button>
          </div>

          <div
            v-for="provider in oauthProviders"
            :key="provider.provider"
            class="oauth-row"
            :class="`oauth-row--${provider.provider}`"
          >
            <div class="oauth-mark">
              <img v-if="provider.icon_url" :src="provider.icon_url" :alt="provider.label" />
              <span v-else>{{ provider.short }}</span>
            </div>
            <div class="oauth-main">
              <strong>{{ provider.label }}</strong>
              <span v-if="provider.connected && provider.hint">{{ provider.hint }}</span>
            </div>
            <span class="oauth-status" :class="{ 'oauth-status--connected': provider.connected }">
              {{ provider.connected ? 'Привязано' : 'Не привязан' }}
            </span>
            <button
              class="ghost-btn"
              type="button"
              :disabled="provider.connected && !provider.can_unlink"
              @click="provider.connected ? unlinkProvider(provider.provider) : linkProvider(provider.provider)"
            >
              {{ provider.connected ? 'Отвязать' : 'Привязать' }}
            </button>
          </div>
        </div>
      </section>

      <section class="profile-card profile-card--info">
        <div class="card-head">
          <div>
            <h2>Личная информация</h2>
            <p>Email используется как логин. Смена email будет отдельной процедурой подтверждения.</p>
          </div>
          <button
            v-if="!profileEditOpen"
            class="ghost-btn ghost-btn--compact"
            type="button"
            @click="openProfileEdit"
          >
            Изменить
          </button>
        </div>

        <div class="field-grid">
          <label class="field">
            <span>Имя</span>
            <input v-model.trim="form.firstName" type="text" placeholder="Введите имя" :readonly="!profileEditOpen" />
          </label>
          <label class="field">
            <span>Фамилия</span>
            <input v-model.trim="form.lastName" type="text" placeholder="Введите фамилию" :readonly="!profileEditOpen" />
          </label>
          <label class="field">
            <span>Email он же логин</span>
            <input v-model="form.email" type="email" readonly />
          </label>
          <label class="field">
            <span>Телефон</span>
            <input v-model.trim="form.phone" type="tel" placeholder="+7 999 000-00-00" :readonly="!profileEditOpen" />
          </label>
        </div>

        <div v-if="profileEditOpen" class="actions-row actions-row--split">
          <button class="ghost-btn" type="button" :disabled="savingProfile" @click="cancelProfileEdit">
            Отмена
          </button>
          <button class="primary-btn primary-btn--wide" type="button" :disabled="savingProfile" @click="saveProfile">
            {{ savingProfile ? 'Сохранение...' : 'Сохранить изменения' }}
          </button>
        </div>
      </section>

      <section class="profile-card profile-card--wide">
        <div class="card-head">
          <div>
            <h2>Уведомления</h2>
            <p>Привязать Telegram, чтобы получать уведомления о важных изменениях в проектах.</p>
          </div>
        </div>

        <div class="notifications-grid">
          <div class="notification-box">
            <div class="notification-icon notification-icon--telegram">
              <img src="/admirra/img/icons/telegram.png" alt="Telegram" />
            </div>
            <div class="notification-main">
              <strong>Telegram</strong>
              <span v-if="form.telegramChatId">Подключён. Уведомления будут приходить в привязанный чат.</span>
              <span v-else>Откройте бота и нажмите Start. Chat ID вручную вводить не нужно.</span>
              <div class="notification-actions">
                <button
                  v-if="form.telegramChatId"
                  class="telegram-connected-btn"
                  type="button"
                  disabled
                >
                  Подключен
                </button>
                <button v-else class="telegram-btn" type="button" @click="connectTelegram">
                  Подключить Telegram
                </button>
                <button
                  class="ghost-btn"
                  type="button"
                  :disabled="savingProfile"
                  @click="form.telegramChatId ? disconnectTelegram() : loadProfile()"
                >
                  {{ form.telegramChatId ? 'Отвязать' : 'Обновить статус' }}
                </button>
              </div>
            </div>
          </div>

          <div class="notification-box">
            <div class="notification-icon notification-icon--email">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                <path d="M2.667 4.667C2.667 4.299 2.965 4 3.333 4h9.334c.368 0 .666.299.666.667v6.666a.667.667 0 0 1-.666.667H3.333a.667.667 0 0 1-.666-.667V4.667Z" fill="#2563EB" opacity=".12"/>
                <path d="m3.333 5 4.334 3.25c.237.178.563.178.8 0L12.667 5" stroke="#2563EB" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
            <div class="notification-main">
              <strong>Email для уведомлений</strong>
              <span>Введите вашу почту:</span>
              <div class="email-actions">
                <input v-model.trim="form.notificationEmail" type="email" placeholder="email@example.com" />
                <button class="primary-btn" type="button" :disabled="savingProfile" @click="saveNotifications">
                  Сохранить уведомления
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section class="profile-card profile-card--wide">
        <div class="card-head">
          <div>
            <h2>Детектор аномалий</h2>
            <p>Глобальное включение детектора для всех проектов аккаунта.</p>
          </div>
        </div>
        <div class="security-list">
          <div class="security-row">
            <div class="security-copy">
              <strong>Детектор аномалий</strong>
              <span>{{ form.globalDetectorEnabled ? 'Включён для всех проектов аккаунта.' : 'Выключен глобально — флаги и баннеры не показываются ни в одном проекте.' }}</span>
            </div>
            <button
              class="toggle"
              type="button"
              :class="{ 'toggle--on': form.globalDetectorEnabled }"
              @click="toggleGlobalDetector"
              :aria-pressed="form.globalDetectorEnabled ? 'true' : 'false'"
            >
              <i></i>
            </button>
          </div>
        </div>
      </section>

      <section class="danger-card profile-card--wide">
        <div>
          <h2>Удалить аккаунт</h2>
          <p>Необратимое действие. Будут удалены профиль, проекты и данные агентства.</p>
        </div>
        <button class="danger-outline-btn" type="button" @click="deleteOpen = true">Удалить аккаунт</button>
      </section>
    </main>

    <div v-if="passwordOpen" class="modal-layer" @click.self="closePassword">
      <div class="profile-modal">
        <h3>{{ profile.has_password ? 'Изменить пароль' : 'Задать пароль' }}</h3>
        <label v-if="profile.has_password" class="field">
          <span>Текущий пароль</span>
          <input v-model="passwordForm.current" type="password" autocomplete="current-password" />
        </label>
        <label class="field">
          <span>Новый пароль</span>
          <input v-model="passwordForm.next" type="password" autocomplete="new-password" />
        </label>
        <label class="field">
          <span>Повторите пароль</span>
          <input v-model="passwordForm.repeat" type="password" autocomplete="new-password" />
        </label>
        <div class="modal-actions">
          <button class="ghost-btn" type="button" @click="closePassword">Отмена</button>
          <button class="primary-btn" type="button" :disabled="savingPassword" @click="savePassword">Сохранить</button>
        </div>
      </div>
    </div>

    <div v-if="twoFactorSetupOpen" class="modal-layer" @click.self="closeTwoFactorSetup">
      <div class="profile-modal">
        <h3>Подтвердить 2FA</h3>
        <p class="modal-note">
          Введите 6-значный код из письма<span v-if="twoFactorEmailMasked"> на {{ twoFactorEmailMasked }}</span>.
        </p>
        <label class="field">
          <span>Код подтверждения</span>
          <input
            v-model="twoFactorCode"
            type="text"
            inputmode="numeric"
            maxlength="6"
            placeholder="000000"
            @input="handleTwoFactorCodeInput"
          />
        </label>
        <div class="modal-actions">
          <button class="ghost-btn" type="button" @click="closeTwoFactorSetup">Отмена</button>
          <button
            class="primary-btn"
            type="button"
            :disabled="twoFactorLoading || twoFactorCode.length !== 6"
            @click="confirmTwoFactor"
          >
            {{ twoFactorLoading ? 'Проверка...' : 'Включить 2FA' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="deleteOpen" class="modal-layer" @click.self="deleteOpen = false">
      <div class="profile-modal">
        <h3>Удалить аккаунт?</h3>
        <p class="modal-note">Введите <b>УДАЛИТЬ</b>, чтобы подтвердить действие.</p>
        <label class="field">
          <span>Подтверждение</span>
          <input v-model="deleteConfirmation" type="text" placeholder="УДАЛИТЬ" />
        </label>
        <div class="modal-actions">
          <button class="ghost-btn" type="button" @click="deleteOpen = false">Отмена</button>
          <button class="danger-btn" type="button" @click="deleteAccount">Удалить</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { CameraIcon } from '@heroicons/vue/24/solid'
import api from '../../api/axios'
import { useAuth } from '../../composables/useAuth'
import { useOAuthLogin } from '../../composables/useOAuthLogin'
import { useTelegramReportLink } from '../../composables/useTelegramReportLink'
import { useToaster } from '../../composables/useToaster'
import { clearAccessToken } from '../../utils/authToken'

const router = useRouter()
const toaster = useToaster()
const { fetchCurrentUser } = useAuth()
const { startYandexLogin, startVkLogin, startMaxLogin } = useOAuthLogin()
const { openTelegramBotForLinking } = useTelegramReportLink()

const profile = ref({})
const oauth = ref([])
const savingProfile = ref(false)
const savingPassword = ref(false)
const twoFactorLoading = ref(false)
const twoFactorSetupOpen = ref(false)
const twoFactorChallengeId = ref('')
const twoFactorCode = ref('')
const twoFactorEmailMasked = ref('')
const profileEditOpen = ref(false)
const passwordOpen = ref(false)
const deleteOpen = ref(false)
const deleteConfirmation = ref('')

const form = reactive({
  firstName: '',
  lastName: '',
  email: '',
  phone: '',
  role: '',
  isActive: true,
  avatarUrl: '',
  twoFactorEnabled: false,
  globalDetectorEnabled: true,
  interfaceLanguage: 'ru',
  telegramChatId: '',
  notificationEmail: '',
})

const passwordForm = reactive({
  current: '',
  next: '',
  repeat: '',
})

const oauthProviderDefaults = [
  {
    provider: 'yandex',
    label: 'Яндекс ID',
    short: 'Я',
    icon_url: '/admirra/img/icons/yandex.png',
  },
  {
    provider: 'vk',
    label: 'ВКонтакте',
    short: 'VK',
    icon_url: '/admirra/img/icons/vk.png',
  },
  {
    provider: 'max',
    label: 'Max',
    short: 'M',
    icon_url: '/admirra/img/icons/max.png',
  },
]

const displayName = computed(() => {
  return [form.firstName, form.lastName].filter(Boolean).join(' ').trim() || form.email || 'Пользователь'
})

const initials = computed(() => {
  const base = displayName.value || 'П'
  return base.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join('').toUpperCase()
})

const passwordSubtitle = computed(() => {
  if (!profile.value.has_password) return 'Пароль ещё не задан: вход выполнялся через внешний способ.'
  if (!profile.value.password_updated_at) return 'Пароль задан.'
  return `Последнее изменение: ${new Date(profile.value.password_updated_at).toLocaleDateString('ru-RU')}`
})

const oauthProviders = computed(() => {
  const connectedByProvider = new Map((oauth.value || []).filter((item) => item?.provider).map((item) => [item.provider, item]))
  return oauthProviderDefaults.map((provider) => {
    const connected = connectedByProvider.get(provider.provider)
    return {
      ...provider,
      ...connected,
      connected: Boolean(connected?.connected),
      can_unlink: Boolean(connected?.can_unlink),
    }
  })
})

function fillProfile(data) {
  profile.value = data || {}
  form.firstName = data?.first_name || ''
  form.lastName = data?.last_name || ''
  form.email = data?.email || ''
  form.phone = data?.phone || ''
  form.role = data?.role || ''
  form.isActive = data?.is_active !== false
  form.avatarUrl = data?.avatar_url || ''
  form.twoFactorEnabled = Boolean(data?.two_factor_enabled)
  form.globalDetectorEnabled = data?.global_detector_enabled !== false
  form.interfaceLanguage = data?.interface_language || 'ru'
  form.telegramChatId = data?.report_telegram_chat_id || ''
  form.notificationEmail = data?.notification_email || ''
}

async function loadProfile() {
  const [{ data }, oauthRes] = await Promise.all([
    api.get('auth/me'),
    api.get('auth/me/oauth-identities').catch(() => ({ data: [] })),
  ])
  fillProfile(data)
  oauth.value = oauthRes.data || []
}

function resetProfileForm() {
  fillProfile(profile.value)
}

function openProfileEdit() {
  profileEditOpen.value = true
}

function cancelProfileEdit() {
  resetProfileForm()
  profileEditOpen.value = false
}

async function saveProfile() {
  savingProfile.value = true
  try {
    const { data } = await api.patch('auth/me', {
      first_name: form.firstName || null,
      last_name: form.lastName || null,
      phone: form.phone || null,
    })
    fillProfile(data)
    profileEditOpen.value = false
    await fetchCurrentUser()
    toaster.success('Профиль обновлён')
  } catch (error) {
    toaster.error(error.response?.data?.detail || 'Не удалось сохранить профиль')
  } finally {
    savingProfile.value = false
  }
}

async function saveNotifications() {
  savingProfile.value = true
  try {
    const { data } = await api.patch('auth/me', { notification_email: form.notificationEmail || null })
    fillProfile(data)
    toaster.success('Уведомления сохранены')
  } catch (error) {
    toaster.error(error.response?.data?.detail || 'Не удалось сохранить уведомления')
  } finally {
    savingProfile.value = false
  }
}

async function toggleGlobalDetector() {
  try {
    const next = !form.globalDetectorEnabled
    const { data } = await api.patch('auth/me', { global_detector_enabled: next })
    fillProfile(data)
    toaster.success(next ? 'Детектор включён для всех проектов' : 'Детектор выключен глобально')
  } catch (error) {
    toaster.error(error.response?.data?.detail || 'Не удалось изменить настройку детектора')
  }
}

async function toggleTwoFactor() {
  if (twoFactorLoading.value) return
  if (form.twoFactorEnabled) {
    twoFactorLoading.value = true
    try {
      const { data } = await api.patch('auth/me', { two_factor_enabled: false })
      fillProfile(data)
      toaster.success('2FA отключена')
    } catch (error) {
      toaster.error(error.response?.data?.detail || 'Не удалось отключить 2FA')
    } finally {
      twoFactorLoading.value = false
    }
    return
  }

  twoFactorLoading.value = true
  try {
    const { data } = await api.post('auth/me/2fa/start')
    twoFactorChallengeId.value = data?.challenge_id || ''
    twoFactorEmailMasked.value = data?.email_masked || ''
    twoFactorCode.value = ''
    twoFactorSetupOpen.value = true
    toaster.success('Код подтверждения отправлен на email')
  } catch (error) {
    toaster.error(error.response?.data?.detail || 'Не удалось отправить код 2FA')
  } finally {
    twoFactorLoading.value = false
  }
}

function closeTwoFactorSetup() {
  twoFactorSetupOpen.value = false
  twoFactorChallengeId.value = ''
  twoFactorCode.value = ''
  twoFactorEmailMasked.value = ''
}

function handleTwoFactorCodeInput(event) {
  twoFactorCode.value = event.target.value.replace(/\D/g, '').slice(0, 6)
}

async function confirmTwoFactor() {
  if (twoFactorCode.value.length !== 6 || !twoFactorChallengeId.value) return
  twoFactorLoading.value = true
  try {
    const { data } = await api.post('auth/me/2fa/verify', {
      challenge_id: twoFactorChallengeId.value,
      code: twoFactorCode.value,
    })
    fillProfile(data)
    closeTwoFactorSetup()
    toaster.success('2FA включена')
  } catch (error) {
    toaster.error(error.response?.data?.detail || 'Неверный код подтверждения')
  } finally {
    twoFactorLoading.value = false
  }
}

async function uploadAvatar(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  const body = new FormData()
  body.append('file', file)
  try {
    const { data } = await api.post('auth/me/avatar', body, { headers: { 'Content-Type': 'multipart/form-data' } })
    fillProfile(data)
    await fetchCurrentUser()
    toaster.success('Аватар обновлён')
  } catch (error) {
    toaster.error(error.response?.data?.detail || 'Не удалось загрузить аватар')
  }
}

async function deleteAvatar() {
  try {
    const { data } = await api.delete('auth/me/avatar')
    fillProfile(data)
    await fetchCurrentUser()
    toaster.success('Аватар удалён')
  } catch (error) {
    toaster.error(error.response?.data?.detail || 'Не удалось удалить аватар')
  }
}

function closePassword() {
  passwordOpen.value = false
  passwordForm.current = ''
  passwordForm.next = ''
  passwordForm.repeat = ''
}

async function savePassword() {
  if (passwordForm.next.length < 8) {
    toaster.error('Пароль должен быть не короче 8 символов')
    return
  }
  if (passwordForm.next !== passwordForm.repeat) {
    toaster.error('Пароли не совпадают')
    return
  }
  savingPassword.value = true
  try {
    const { data } = await api.post('auth/me/password', {
      current_password: passwordForm.current || null,
      new_password: passwordForm.next,
    })
    fillProfile(data)
    closePassword()
    await loadProfile()
    toaster.success('Пароль сохранён')
  } catch (error) {
    toaster.error(error.response?.data?.detail || 'Не удалось сохранить пароль')
  } finally {
    savingPassword.value = false
  }
}

async function linkProvider(provider) {
  try {
    sessionStorage.setItem('oauth_profile_link', provider)
    if (provider === 'yandex') return startYandexLogin()
    if (provider === 'vk') return startVkLogin()
    if (provider === 'max') {
      await startMaxLogin()
      sessionStorage.removeItem('oauth_profile_link')
      await loadProfile()
      toaster.success('MAX привязан к профилю')
    }
  } catch (error) {
    sessionStorage.removeItem('oauth_profile_link')
    toaster.error(error.response?.data?.detail || error.message || 'Не удалось привязать способ входа')
  }
}

async function unlinkProvider(provider) {
  try {
    const { data } = await api.delete(`auth/me/oauth-identities/${provider}`)
    oauth.value = data || []
    toaster.success('Способ входа отвязан')
  } catch (error) {
    toaster.error(error.response?.data?.detail || 'Не удалось отвязать способ входа')
  }
}

async function connectTelegram() {
  try {
    await openTelegramBotForLinking()
    toaster.success('В Telegram нажмите Start, затем обновите статус привязки')
  } catch (error) {
    toaster.error(error.response?.data?.detail || error.message || 'Не удалось открыть Telegram')
  }
}

async function disconnectTelegram() {
  savingProfile.value = true
  try {
    const payload = { report_telegram_chat_id: '' }
    if (Array.isArray(profile.value?.report_delivery_channels)) {
      payload.report_delivery_channels = profile.value.report_delivery_channels.filter(
        (channel) => channel !== 'telegram'
      )
    }
    const { data } = await api.patch('auth/me', payload)
    fillProfile(data)
    toaster.success('Telegram отвязан')
  } catch (error) {
    toaster.error(error.response?.data?.detail || 'Не удалось отвязать Telegram')
  } finally {
    savingProfile.value = false
  }
}

async function deleteAccount() {
  try {
    await api.delete('auth/me', { params: { confirmation: deleteConfirmation.value } })
    clearAccessToken()
    router.push('/signin')
  } catch (error) {
    toaster.error(error.response?.data?.detail || 'Не удалось удалить аккаунт')
  }
}

onMounted(loadProfile)
</script>

<style scoped>
.profile-page {
  max-width: 44.4444rem;
  margin: 0 auto;
  padding: 2.0833rem 1.3889rem 3.4722rem;
}
.profile-head {
  margin-bottom: 1.3889rem;
}
.profile-head h1 {
  margin: 0;
  color: #171717;
  font-size: 2.0833rem;
  font-weight: 800;
  line-height: 1.05;
}
.profile-head p,
.card-head p,
.danger-card p,
.modal-note {
  margin: 0.4861rem 0 0;
  color: rgba(105,105,105,0.56);
  font-size: 0.9722rem;
  line-height: 1.45;
}
.profile-stack {
  display: grid;
  gap: 1.0417rem;
}
.profile-card,
.danger-card {
  border: 1px solid rgba(0,0,0,0.05);
  border-radius: 1.0417rem;
  background: #fff;
  padding: 1.5278rem;
  box-shadow: 0 0.6944rem 1.9444rem rgba(15, 23, 42, 0.035);
}
.profile-hero {
  display: flex;
  align-items: center;
  gap: 1.1111rem;
}
.avatar-wrap {
  position: relative;
  flex-shrink: 0;
}
.avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 6.25rem;
  height: 6.25rem;
  border-radius: 50%;
  background: linear-gradient(135deg, #eef4ff, #f5f7f9);
  color: #2563eb;
  font-size: 1.5278rem;
  font-weight: 900;
  overflow: hidden;
}
.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.avatar-btn {
  position: absolute;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.2222rem;
  height: 2.2222rem;
  border-radius: 50%;
  background: #2563eb;
  color: #fff;
  cursor: pointer;
  box-shadow: 0 0.4167rem 1.1111rem rgba(37,99,235,0.22);
}
.avatar-btn input {
  display: none;
}
.hero-info {
  min-width: 0;
  flex: 1;
}
.hero-info h2,
.card-head h2,
.danger-card h2,
.profile-modal h3 {
  margin: 0;
  color: #171717;
  font-size: 1.3889rem;
  font-weight: 800;
}
.hero-info p {
  margin: 0.3472rem 0 0;
  color: rgba(105,105,105,0.62);
  font-size: 0.9722rem;
}
.role-badge {
  display: inline-flex;
  align-items: center;
  min-height: 1.8056rem;
  margin-top: 0.6944rem;
  padding: 0 0.6944rem;
  border-radius: 2.7778rem;
  background: rgba(37,99,235,0.10);
  color: #2563eb;
  font-size: 0.7639rem;
  font-weight: 800;
}
.card-head,
.danger-card {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}
.field-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.8333rem;
}
.field {
  display: grid;
  gap: 0.4167rem;
  margin-top: 0.9028rem;
}
.field span {
  color: #696969;
  font-size: 0.9028rem;
  font-weight: 700;
}
.field em {
  color: rgba(105,105,105,0.45);
  font-style: normal;
  font-weight: 600;
}
.field input,
.field select {
  width: 100%;
  min-height: 2.3611rem;
  padding: 0 0.8333rem;
  border: 1px solid transparent;
  border-radius: 0.6944rem;
  outline: none;
  background: #f5f7f9;
  color: #171717;
  font-size: 0.9028rem;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.field input:focus,
.field select:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37,99,235,0.08);
}
.field input[readonly] {
  color: rgba(105,105,105,0.72);
  cursor: not-allowed;
}
.actions-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 1.25rem;
}
.primary-btn,
.ghost-btn,
.telegram-btn,
.telegram-connected-btn,
.danger-btn,
.danger-outline-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 2.7778rem;
  padding: 0 1.0417rem;
  border-radius: 0.6944rem;
  font-size: 0.9028rem;
  font-weight: 800;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s, opacity 0.2s;
}
.primary-btn {
  border: 0;
  background: linear-gradient(270deg, #06b5d4 0.35%, #1f9de4 32.08%, #2563eb 96.51%);
  color: #fff;
}
.ghost-btn {
  border: 1px solid rgba(0,0,0,0.08);
  background: #fff;
  color: #444;
}
.telegram-btn {
  border: 0;
  background: linear-gradient(135deg, #1f9de4, #06b5d4);
  color: #fff;
  box-shadow: 0 0.4167rem 1.25rem rgba(31,157,228,0.18);
}
.telegram-connected-btn {
  border: 1px solid rgba(34, 197, 94, 0.42);
  background: rgba(34, 197, 94, 0.08);
  color: #16a34a;
  box-shadow: none;
  cursor: default;
}
.telegram-connected-btn:disabled {
  opacity: 1;
  cursor: default;
}
.danger-btn {
  border: 0;
  background: #ef4444;
  color: #fff;
}
.danger-outline-btn {
  flex-shrink: 0;
  border: 1px solid rgba(239,68,68,0.24);
  background: #fff;
  color: #dc2626;
}
.danger-outline-btn:hover {
  border-color: rgba(239,68,68,0.38);
  background: rgba(239,68,68,0.06);
}
button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.security-list,
.oauth-list {
  display: grid;
  gap: 0.6944rem;
}
.security-row,
.oauth-row,
.notification-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.9722rem 1.0417rem;
  border-radius: 0.8333rem;
  background: #f8fafc;
}
.security-row strong,
.oauth-main strong,
.notification-box strong {
  display: block;
  color: #171717;
  font-size: 0.9722rem;
  font-weight: 800;
}
.security-row span,
.oauth-main span,
.notification-box span,
.oauth-main em {
  display: block;
  margin-top: 0.2778rem;
  color: rgba(105,105,105,0.58);
  font-size: 0.8333rem;
  line-height: 1.35;
}
.oauth-row {
  justify-content: flex-start;
}
.oauth-mark {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.6389rem;
  height: 2.6389rem;
  flex-shrink: 0;
  border-radius: 0.6944rem;
  background: #f3f6fb;
  color: #445064;
  font-size: 0.9028rem;
  font-weight: 900;
}
.oauth-mark img,
.notification-icon img {
  width: 1.6667rem;
  height: 1.6667rem;
  object-fit: contain;
}
.oauth-row--vk .oauth-mark,
.oauth-row--max .oauth-mark {
  background: #f3f6fb;
  color: #445064;
}
.oauth-main {
  min-width: 0;
  flex: 1;
}
.toggle {
  width: 3.3333rem;
  height: 1.875rem;
  padding: 0.2083rem;
  border: 0;
  border-radius: 2.7778rem;
  background: #d1d5db;
  cursor: pointer;
}
.toggle i {
  display: block;
  width: 1.4583rem;
  height: 1.4583rem;
  border-radius: 50%;
  background: #fff;
  transition: transform 0.2s;
}
.toggle--on {
  background: #2563eb;
}
.toggle--on i {
  transform: translateX(1.4583rem);
}
.notification-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.5556rem;
}
.notification-box {
  justify-content: flex-start;
}
.notification-box > div:nth-child(2) {
  min-width: 0;
  flex: 1;
}
.notification-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.7778rem;
  height: 2.7778rem;
  flex-shrink: 0;
  border-radius: 0.8333rem;
  background: #eef8ff;
}
.danger-card {
  align-items: center;
  border-color: rgba(239,68,68,0.16);
  background: linear-gradient(180deg, #fff, #fffafa);
}
.danger-card h2 {
  color: #b91c1c;
  font-size: 1.25rem;
}
.danger-card p {
  max-width: 32rem;
}
.modal-layer {
  position: fixed;
  inset: 0;
  z-index: 9000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.1111rem;
  background: rgba(15,23,42,0.42);
}
.profile-modal {
  width: min(100%, 32rem);
  border-radius: 1.1111rem;
  background: #fff;
  padding: 1.3889rem;
  box-shadow: 0 1.3889rem 4.1667rem rgba(15,23,42,0.24);
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.6944rem;
  margin-top: 1.0417rem;
}

:global(.dark) .profile-head h1,
:global(.darkmode) .profile-head h1,
:global(.dark) .hero-info h2,
:global(.darkmode) .hero-info h2,
:global(.dark) .card-head h2,
:global(.darkmode) .card-head h2,
:global(.dark) .profile-modal h3,
:global(.darkmode) .profile-modal h3,
:global(.dark) .security-row strong,
:global(.darkmode) .security-row strong,
:global(.dark) .oauth-main strong,
:global(.darkmode) .oauth-main strong,
:global(.dark) .notification-box strong,
:global(.darkmode) .notification-box strong {
  color: rgba(255,255,255,0.92);
}
:global(.dark) .profile-card,
:global(.darkmode) .profile-card,
:global(.dark) .profile-modal,
:global(.darkmode) .profile-modal {
  background: #2C2F3D;
  border-color: rgba(255,255,255,0.08);
}
:global(.dark) .security-row,
:global(.darkmode) .security-row,
:global(.dark) .oauth-row,
:global(.darkmode) .oauth-row,
:global(.dark) .notification-box {
  background: rgba(255,255,255,0.05);
}
:global(.dark) .field input,
:global(.darkmode) .field input,
:global(.dark) .field select,
:global(.darkmode) .field select {
  background: rgba(255,255,255,0.08);
  color: rgba(255,255,255,0.9);
}
:global(.dark) .ghost-btn,
:global(.darkmode) .ghost-btn {
  background: rgba(255,255,255,0.06);
  border-color: rgba(255,255,255,0.10);
  color: rgba(255,255,255,0.76);
}
:global(.dark) .danger-card,
:global(.darkmode) .danger-card {
  background: rgba(239,68,68,0.08);
  border-color: rgba(239,68,68,0.22);
}
:global(.dark) .danger-outline-btn,
:global(.darkmode) .danger-outline-btn {
  background: rgba(239,68,68,0.08);
  border-color: rgba(239,68,68,0.28);
  color: #fca5a5;
}

@media (max-width: 680px) {
  .profile-page {
    padding-inline: 1rem;
  }
  .profile-hero,
  .card-head,
  .security-row,
  .notification-box,
  .danger-card {
    align-items: stretch;
    flex-direction: column;
  }
  .field-grid {
    grid-template-columns: 1fr;
  }
  .notification-actions {
    justify-content: flex-start;
  }
  .danger-outline-btn,
  .primary-btn,
  .telegram-btn,
  .telegram-connected-btn,
  .ghost-btn {
    width: 100%;
  }
}

/* Figma profile redesign */
.profile-page {
  width: min(100%, 91.6667rem);
  max-width: none;
  margin: 0;
  padding: 2.0833rem 1.875rem 3.3333rem;
}

.profile-head {
  margin-bottom: 1.6667rem;
}

.profile-head h1 {
  margin: 0;
  color: #171717;
  font-size: 1.8056rem;
  font-weight: 700;
  letter-spacing: 0;
  line-height: 1.08;
}

.profile-head p {
  margin: 0.4861rem 0 0;
  color: rgba(105, 105, 105, 0.48);
  font-size: 0.8333rem;
  font-weight: 600;
}

.profile-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  align-items: stretch;
  gap: 1.6667rem;
}

.profile-card,
.danger-card {
  border: 0;
  border-radius: 1.1111rem;
  background: #fff;
  padding: 1.6667rem;
  box-shadow: none;
}

.profile-card--wide,
.danger-card.profile-card--wide {
  grid-column: 1 / -1;
}

.profile-card--security {
  grid-row: span 2;
}

.profile-hero {
  min-height: 7.7083rem;
  display: flex;
  align-items: center;
  gap: 1.5972rem;
  padding: 1.6667rem;
}

.avatar {
  width: 4.8611rem;
  height: 4.8611rem;
  background: #eef4ff;
  color: #2563eb;
  font-size: 1.8056rem;
  font-weight: 700;
}

.avatar-btn {
  right: -0.2083rem;
  bottom: 0.2083rem;
  width: 1.7361rem;
  height: 1.7361rem;
  background: #2563eb;
  box-shadow: 0 0.4167rem 0.9028rem rgba(37, 99, 235, 0.28);
}

.avatar-btn svg {
  width: 0.8333rem;
  height: 0.8333rem;
}

.avatar-remove-btn {
  margin-top: 0.4861rem;
  border: 0;
  background: transparent;
  color: rgba(105, 105, 105, 0.58);
  font-size: 0.6944rem;
  font-weight: 700;
  line-height: 1;
}

.avatar-remove-btn:hover {
  color: #ff5d62;
}

.hero-info h2,
.card-head h2,
.danger-card h2,
.profile-modal h3 {
  margin: 0;
  color: #171717;
  font-size: 1.25rem;
  font-weight: 700;
  line-height: 1.18;
}

.hero-info p {
  margin: 0.2778rem 0 0;
  color: rgba(105, 105, 105, 0.58);
  font-size: 0.8333rem;
  font-weight: 600;
}

.role-badge {
  min-height: 1.3889rem;
  margin-top: 0.5556rem;
  padding: 0 0.6944rem;
  border-radius: 0.2083rem;
  background: #e8fff0;
  color: #2abd58;
  font-size: 0.7639rem;
  font-weight: 700;
}

.card-head,
.danger-card {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1.1111rem;
}

.card-head p,
.danger-card p,
.modal-note {
  margin: 0.625rem 0 0;
  color: rgba(105, 105, 105, 0.48);
  font-size: 0.9028rem;
  font-weight: 600;
  line-height: 1.25;
}

.profile-card--info {
  padding: 1.6667rem;
}

.field-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1.3194rem 1.1111rem;
  margin-top: 1.5972rem;
}

.field {
  display: grid;
  gap: 0.625rem;
  margin: 0;
}

.field span {
  color: #4d4d4d;
  font-size: 0.8333rem;
  font-weight: 700;
}

.field em {
  display: block;
  margin-top: 0.3472rem;
  color: rgba(105, 105, 105, 0.45);
  font-size: 0.7639rem;
  font-style: normal;
  font-weight: 600;
}

.field input,
.field select {
  width: 100%;
  min-height: 2.6389rem;
  padding: 0 0.9722rem;
  border: 0;
  border-radius: 0.5556rem;
  outline: none;
  background: #f5f7f9;
  color: #171717;
  font-size: 0.8333rem;
  font-weight: 600;
}

.email-actions input {
  width: 100%;
  min-height: 2.7778rem;
  padding: 0 1.1111rem;
  border: 0;
  border-radius: 0.625rem;
  outline: none;
  background: #fff;
  color: #171717;
  font-size: 0.9028rem;
  font-weight: 600;
}

.profile-page input[type="email"],
.profile-page input[type="password"],
.profile-page input[type="tel"],
.profile-page input[type="text"],
.profile-page textarea {
  height: 3rem;
}

.field input::placeholder,
.email-actions input::placeholder {
  color: rgba(105, 105, 105, 0.42);
}

.field input[readonly] {
  color: rgba(105, 105, 105, 0.52);
  cursor: not-allowed;
}

.profile-card--info .field input[readonly] {
  background: #f5f7f9;
}

.field input:focus,
.field select:focus,
.email-actions input:focus {
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.08);
}

.actions-row {
  margin-top: 1.9444rem;
}

.actions-row--split {
  display: grid;
  grid-template-columns: minmax(7.5rem, 0.34fr) minmax(0, 1fr);
  gap: 0.8333rem;
}

.primary-btn,
.ghost-btn,
.telegram-btn,
.telegram-connected-btn,
.danger-btn,
.danger-outline-btn {
  min-height: 2.7778rem;
  padding: 0 1.3889rem;
  border-radius: 0.625rem;
  font-size: 0.8333rem;
  font-weight: 700;
}

.primary-btn,
.telegram-btn {
  border: 0;
  background: linear-gradient(270deg, #06b5d4 0.35%, #1f9de4 32.08%, #2563eb 96.51%);
  color: #fff;
}

.telegram-connected-btn {
  border: 1px solid rgba(34, 197, 94, 0.42);
  background: rgba(34, 197, 94, 0.08);
  color: #16a34a;
  box-shadow: none;
  cursor: default;
}

.telegram-connected-btn:disabled {
  opacity: 1;
  cursor: default;
}

.primary-btn--wide {
  width: 100%;
  min-height: 3.2639rem;
}

.profile-card--info .primary-btn--wide {
  background: #2563eb;
}

.ghost-btn {
  border: 1px solid rgba(23, 23, 23, 0.09);
  background: #fff;
  color: #2563eb;
}

.ghost-btn--compact {
  min-width: 6.7361rem;
  min-height: 2.8472rem;
}

.security-list {
  display: grid;
  gap: 0.9722rem;
  margin-top: 1.5972rem;
}

.security-row,
.oauth-row,
.notification-box {
  display: flex;
  align-items: center;
  gap: 1rem;
  min-height: 4.5139rem;
  padding: 0.9722rem 1.25rem;
  border-radius: 0.625rem;
  background: #f5f7f9;
}

.security-row {
  justify-content: space-between;
}

.security-copy {
  min-width: 0;
}

.security-copy strong,
.oauth-main strong,
.notification-box strong {
  display: block;
  color: #696969;
  font-size: 0.8333rem;
  font-weight: 700;
}

.security-copy span,
.oauth-main span,
.notification-box span {
  display: block;
  margin-top: 0.2778rem;
  color: rgba(105, 105, 105, 0.48);
  font-size: 0.8333rem;
  font-weight: 600;
  line-height: 1.2;
}

.oauth-row {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) minmax(6.6667rem, auto) minmax(6.9444rem, auto);
  min-height: 4.5139rem;
}

.oauth-mark {
  width: 1.5278rem;
  height: 1.5278rem;
  border-radius: 50%;
  background: transparent;
}

.oauth-mark img,
.notification-icon img {
  width: 1.5278rem;
  height: 1.5278rem;
}

.oauth-main strong {
  color: #696969;
}

.oauth-status {
  min-width: 6.1111rem;
  padding: 0.2778rem 0.625rem;
  border-radius: 0.1389rem;
  background: #fff;
  color: rgba(105, 105, 105, 0.44);
  font-size: 0.8333rem;
  font-weight: 700;
  text-align: center;
}

.security-row .ghost-btn,
.oauth-row .ghost-btn {
  min-width: 6.6667rem;
  min-height: 2.7778rem;
}

.oauth-status--connected {
  background: #e8fff0;
  color: #2abd58;
}

.toggle {
  width: 3.125rem;
  height: 1.7361rem;
  padding: 0.2083rem;
  border: 0;
  border-radius: 99rem;
  background: #fff;
  box-shadow: inset 0 0 0 1px rgba(23, 23, 23, 0.1);
}

.toggle--on {
  background: #fff;
}

.toggle i {
  display: block;
  width: 1.3194rem;
  height: 1.3194rem;
  border-radius: 50%;
  background: #d1d5db;
  transition: transform 0.2s, background 0.2s;
}

.toggle--on i {
  background: #6bdd62;
  transform: translateX(1.3889rem);
}

.profile-card--wide {
  padding: 1.6667rem;
}

.notifications-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1.1111rem;
  margin-top: 1.5278rem;
}

.notification-box {
  align-items: flex-start;
  min-height: 6.6667rem;
  padding: 1.3194rem 1.5278rem;
}

.notification-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.5278rem;
  height: 1.5278rem;
  flex-shrink: 0;
  border-radius: 50%;
  background: #fff;
}

.notification-icon--telegram {
  background: #e7f6ff;
}

.notification-icon--email {
  background: #fff;
}

.notification-main {
  min-width: 0;
  flex: 1;
}

.notification-actions,
.email-actions {
  display: grid;
  gap: 1.1111rem;
  margin-top: 1.25rem;
}

.notification-actions {
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
}

.email-actions {
  grid-template-columns: minmax(13.3333rem, 1fr) minmax(11.8056rem, 0.85fr);
}

.email-actions input {
  background: #fff;
  min-height: 2.7778rem;
}

.danger-card {
  align-items: center;
  min-height: 5.8333rem;
  border: 1px solid rgba(255, 98, 98, 0.3);
  background: #fff0f0;
  padding: 1.6667rem;
}

.danger-card h2 {
  color: #ff5d62;
  font-size: 1.25rem;
}

.danger-card p {
  color: rgba(255, 93, 98, 0.62);
}

.danger-outline-btn {
  min-width: 13.8889rem;
  min-height: 2.8472rem;
  border: 1px solid #ff5d62;
  background: transparent;
  color: #ff5d62;
}

.danger-outline-btn:hover {
  background: rgba(255, 93, 98, 0.06);
}

@media (max-width: 980px) {
  .profile-grid {
    grid-template-columns: 1fr;
  }

  .profile-card--security,
  .profile-card--wide,
  .danger-card.profile-card--wide {
    grid-column: auto;
    grid-row: auto;
  }

  .notifications-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 680px) {
  .profile-page {
    padding: 1.5rem 1rem 2.5rem;
  }

  .profile-hero,
  .card-head,
  .security-row,
  .danger-card {
    align-items: stretch;
    flex-direction: column;
  }

  .field-grid,
  .notification-actions,
  .email-actions,
  .actions-row--split {
    grid-template-columns: 1fr;
  }

  .oauth-row {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .oauth-status,
  .oauth-row .ghost-btn {
    grid-column: 1 / -1;
    width: 100%;
  }

  .danger-outline-btn,
  .primary-btn,
  .telegram-btn,
  .telegram-connected-btn,
  .ghost-btn {
    width: 100%;
  }
}
</style>
