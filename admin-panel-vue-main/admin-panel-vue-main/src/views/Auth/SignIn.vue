<template>
  <FullScreenLayout>
    <div class="auth-page bg-white text-[#102a55]">
      <main class="auth-main">
        <section class="auth-form-side">
          <router-link to="/" class="auth-logo-link">
            <img src="/admirra/img/logo.png" alt="AdMirra" />
          </router-link>

          <div class="auth-form-box">
            <h1 class="auth-title">
              <span>Добро пожаловать!</span>
              <strong>Войдите в систему</strong>
            </h1>

            <div class="auth-social-row">
            <button
              type="button"
              :disabled="oauthLoading"
              class="auth-social-btn auth-social-btn--yandex"
              @click="handleYandexLogin"
            >
              <img src="/admirra/img/icons/yandex.png" alt="" class="h-[1.1111rem] w-[1.1111rem] object-contain" />
              Войти с Яндекс ID
            </button>
            <button
              type="button"
              :disabled="oauthLoading"
              class="auth-social-btn auth-social-btn--vk"
              @click="handleVkLogin"
            >
              <img src="/admirra/img/icons/vk.png" alt="" class="h-[1.1111rem] w-[1.1111rem] object-contain" />
              Войти через ВК
            </button>
            <button type="button" class="auth-social-btn auth-social-btn--max">
              <img src="/admirra/img/icons/max.png" alt="" class="h-[1.1111rem] w-[1.1111rem] object-contain" />
              Войти через Max
            </button>
          </div>

            <div class="auth-divider">
              <span></span>
              <strong>или</strong>
              <span></span>
            </div>

            <div v-if="errorMessage" class="mb-4 rounded-[0.8333rem] border border-red-200 bg-red-50 px-4 py-3 text-[0.9028rem] font-medium text-red-600">
              {{ errorMessage }}
            </div>

            <form class="auth-fields" @submit.prevent="handleLogin">
              <div>
                <label for="email" class="auth-label">
                  E-mail <span>*</span>
                </label>
                <input
                  v-model="loginForm.email"
                  type="email"
                  id="email"
                  name="email"
                  placeholder="Введите ваш email"
                  class="auth-input"
                />
              </div>

              <div>
                <label for="password" class="auth-label">
                  Пароль <span>*</span>
                </label>
                <div class="relative">
                  <input
                    v-model="loginForm.password"
                    :type="showPassword ? 'text' : 'password'"
                    id="password"
                    placeholder="Введите пароль"
                    class="auth-input pr-14"
                  />
                  <button
                    type="button"
                    class="absolute right-[1.1806rem] top-1/2 flex h-8 w-8 -translate-y-1/2 items-center justify-center text-[#a6a9ad] transition hover:text-[#102a55]"
                    @click="togglePasswordVisibility"
                  >
                    <svg v-if="!showPassword" width="22" height="22" viewBox="0 0 20 20" fill="none">
                      <path fill-rule="evenodd" clip-rule="evenodd" d="M10.0002 13.8619C7.23361 13.8619 4.86803 12.1372 3.92328 9.70241C4.86804 7.26761 7.23361 5.54297 10.0002 5.54297C12.7667 5.54297 15.1323 7.26762 16.0771 9.70243C15.1323 12.1372 12.7667 13.8619 10.0002 13.8619ZM10.0002 4.04297C6.48191 4.04297 3.49489 6.30917 2.4155 9.4593C2.3615 9.61687 2.3615 9.78794 2.41549 9.94552C3.49488 13.0957 6.48191 15.3619 10.0002 15.3619C13.5184 15.3619 16.5055 13.0957 17.5849 9.94555C17.6389 9.78797 17.6389 9.6169 17.5849 9.45932C16.5055 6.30919 13.5184 4.04297 10.0002 4.04297ZM9.99151 7.84413C8.96527 7.84413 8.13333 8.67606 8.13333 9.70231C8.13333 10.7286 8.96527 11.5605 9.99151 11.5605H10.0064C11.0326 11.5605 11.8646 10.7286 11.8646 9.70231C11.8646 8.67606 11.0326 7.84413 10.0064 7.84413H9.99151Z" fill="currentColor"/>
                    </svg>
                    <svg v-else width="22" height="22" viewBox="0 0 20 20" fill="none">
                      <path fill-rule="evenodd" clip-rule="evenodd" d="M4.63803 3.57709C4.34513 3.2842 3.87026 3.2842 3.57737 3.57709C3.28447 3.86999 3.28447 4.34486 3.57737 4.63775L4.85323 5.91362C3.74609 6.84199 2.89363 8.06395 2.4155 9.45936C2.3615 9.61694 2.3615 9.78801 2.41549 9.94558C3.49488 13.0957 6.48191 15.3619 10.0002 15.3619C11.255 15.3619 12.4422 15.0737 13.4994 14.5598L15.3625 16.4229C15.6554 16.7158 16.1302 16.7158 16.4231 16.4229C16.716 16.13 16.716 15.6551 16.4231 15.3622L4.63803 3.57709ZM12.3608 13.4212L10.4475 11.5079C10.3061 11.5423 10.1584 11.5606 10.0064 11.5606H9.99151C8.96527 11.5606 8.13333 10.7286 8.13333 9.70237C8.13333 9.5461 8.15262 9.39434 8.18895 9.24933L5.91885 6.97923C5.03505 7.69015 4.34057 8.62704 3.92328 9.70247C4.86803 12.1373 7.23361 13.8619 10.0002 13.8619C10.8326 13.8619 11.6287 13.7058 12.3608 13.4212ZM16.0771 9.70249C15.7843 10.4569 15.3552 11.1432 14.8199 11.7311L15.8813 12.7925C16.6329 11.9813 17.2187 11.0143 17.5849 9.94561C17.6389 9.78803 17.6389 9.61696 17.5849 9.45938C16.5055 6.30925 13.5184 4.04303 10.0002 4.04303C9.13525 4.04303 8.30244 4.17999 7.52218 4.43338L8.75139 5.66259C9.1556 5.58413 9.57311 5.54303 10.0002 5.54303C12.7667 5.54303 15.1323 7.26768 16.0771 9.70249Z" fill="currentColor"/>
                    </svg>
                  </button>
                </div>
              </div>

              <div class="auth-row">
                <label for="keepLoggedIn" class="auth-checkbox">
                  <input v-model="keepLoggedIn" type="checkbox" id="keepLoggedIn" class="sr-only" />
                  <span :class="keepLoggedIn ? 'border-[#2874ff] bg-[#2874ff]' : 'border-[#aeb7c7] bg-[#f8fafc]'">
                    <svg v-if="keepLoggedIn" width="12" height="12" viewBox="0 0 14 14" fill="none">
                      <path d="M11.6666 3.5L5.24992 9.91667L2.33325 7" stroke="white" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" />
                    </svg>
                  </span>
                  Запомнить меня
                </label>
                <router-link to="/reset-password" class="auth-forgot">
                  Забыли пароль?
                </router-link>
              </div>

              <button type="submit" :disabled="loading" class="auth-submit">
                <span v-if="loading" class="mr-2 h-5 w-5 animate-spin rounded-full border-2 border-white/35 border-t-white"></span>
                {{ loading ? 'Вход...' : 'ВОЙТИ В ЛИЧНЫЙ КАБИНЕТ' }}
              </button>
            </form>

            <p class="auth-alt">
              У вас нет аккаунта ?
              <router-link to="/signup">Зарегистрироваться</router-link>
            </p>
          </div>
        </section>

        <section class="auth-hero-side">
          <div class="auth-hero-card">
            <img :src="authHero" alt="" class="h-full w-full object-cover object-center" fetchpriority="high" />
          </div>
        </section>
      </main>

      <footer class="auth-footer">
        <div class="auth-subscribe">
          <div class="auth-footer-brand">
            <img src="/admirra/img/logo.png" alt="AdMirra" />
            <div class="auth-footer-socials">
              <span><img src="/admirra/img/icons/max.png" alt="" /></span>
              <span><img src="/admirra/img/icons/telegram.png" alt="" /></span>
              <span><img src="/admirra/img/icons/vk.png" alt="" /></span>
            </div>
          </div>
          <form class="auth-subscribe-form" @submit.prevent>
            <label>Подпишитесь на новости</label>
            <div>
              <input type="email" placeholder="Введите ваш email" />
              <button type="submit">ПОДПИСАТЬСЯ</button>
            </div>
          </form>
        </div>

        <div class="auth-footer-bottom">
          <div>
            <h3>Ресурсы</h3>
            <a href="#">Документация</a>
            <a href="#">Блог</a>
            <a href="#">FAQ</a>
          </div>
          <div>
            <h3>Контакты</h3>
            <a href="#">Email</a>
            <a href="#">Telegram</a>
            <a href="#">Поддержка</a>
          </div>
          <div class="auth-footer-center">
            <h3>АдМирра</h3>
            <p>Автоматические отчёты и маркетинговые дашборды</p>
            <img :src="payMethods" alt="Способы оплаты" />
            <small>© 2026 Все права защищены</small>
          </div>
          <div>
            <h3>Документы</h3>
            <a href="#">Договор оферты</a>
            <a href="#">Политика конфиденциальности</a>
            <a href="#">Согласие на обработку персональных данных</a>
          </div>
        </div>
      </footer>
    </div>
  </FullScreenLayout>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import FullScreenLayout from '@/layouts/FullScreenLayout.vue'
import { useAuth } from '@/composables/useAuth'
import { useOAuthLogin } from '@/composables/useOAuthLogin'
import { DEFAULT_DASHBOARD_PATH } from '@/constants/config'
import authHero from '@/assets/imgs/auth/auth.webp'
import payMethods from '@/assets/imgs/auth/pay.png'

const router = useRouter()
const { login, getErrorMessage } = useAuth()
const { startYandexLogin, startVkLogin } = useOAuthLogin()
const showPassword = ref(false)
const keepLoggedIn = ref(false)
const loading = ref(false)
const oauthLoading = ref(false)
const errorMessage = ref('')

const handleYandexLogin = async () => {
  errorMessage.value = ''
  oauthLoading.value = true
  try {
    await startYandexLogin()
  } catch (e) {
    oauthLoading.value = false
    errorMessage.value = getErrorMessage(e, 'Не удалось начать вход через Яндекс')
  }
}

const handleVkLogin = async () => {
  errorMessage.value = ''
  oauthLoading.value = true
  try {
    await startVkLogin()
  } catch (e) {
    oauthLoading.value = false
    errorMessage.value = getErrorMessage(e, 'Не удалось начать вход через ВКонтакте')
  }
}

const loginForm = reactive({
  email: '',
  password: '',
  remember: false
})

const togglePasswordVisibility = () => {
  showPassword.value = !showPassword.value
}

const isValidEmail = (email) => {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
}

const handleLogin = async () => {
  if (!loginForm.email) return
  if (!isValidEmail(loginForm.email)) return
  if (!loginForm.password) return

  loading.value = true
  errorMessage.value = ''

  const result = await login(loginForm.email, loginForm.password)

  loading.value = false

  if (result.success) {
    router.push(DEFAULT_DASHBOARD_PATH)
    return
  }

  if (result.needsEmailVerification) {
    router.push({
      path: '/pending-email-verification',
      query: { email: result.email || loginForm.email }
    })
    return
  }
  if (result.needsOtp) {
    router.push({
      path: '/two-step-verification',
      query: {
        mode: 'otp',
        challenge_id: result.challenge_id,
        email_masked: result.email_masked || ''
      }
    })
    return
  }
  errorMessage.value = result.message || 'Ошибка входа'
}
</script>

<style scoped>
@font-face {
  font-family: "Gilroy";
  src: url("/admirra/fonts/Gilroy/Gilroy-Light.woff2") format("woff2");
  font-weight: 300;
  font-style: normal;
  font-display: swap;
}

@font-face {
  font-family: "Gilroy";
  src: url("/admirra/fonts/Gilroy/Gilroy-Regular.woff2") format("woff2");
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}

@font-face {
  font-family: "Gilroy";
  src: url("/admirra/fonts/Gilroy/Gilroy-Medium.woff2") format("woff2");
  font-weight: 500;
  font-style: normal;
  font-display: swap;
}

@font-face {
  font-family: "Gilroy";
  src: url("/admirra/fonts/Gilroy/Gilroy-Semibold.woff2") format("woff2");
  font-weight: 600;
  font-style: normal;
  font-display: swap;
}

.auth-page {
  font-family: "Gilroy", system-ui, sans-serif;
}

.auth-main {
  display: grid;
  grid-template-columns: minmax(34.7222rem, 0.96fr) minmax(42.3611rem, 1.04fr);
  gap: 1.5278rem;
  min-height: min(100vh, 54.3056rem);
  padding: 1.3889rem 0 1.25rem 0;
}

.auth-form-side {
  position: relative;
  padding-left: clamp(4.7222rem, 9vw, 10rem);
  padding-right: 2.0833rem;
}

.auth-logo-link {
  display: inline-flex;
  margin-top: 2.4306rem;
}

.auth-logo-link img {
  width: 9.4444rem;
  height: auto;
  opacity: 1;
}

.auth-form-box {
  width: 100%;
  max-width: 26.8056rem;
  margin-top: clamp(4.5833rem, 10vh, 7.7778rem);
}

.auth-title {
  margin: 0 0 1.875rem;
  color: #102a55;
  font-size: clamp(2.0139rem, 2.16vw, 2.7778rem);
  font-weight: 300;
  line-height: 1.08;
  letter-spacing: 0;
}

.auth-title span,
.auth-title strong {
  display: block;
}

.auth-title span {
  white-space: nowrap;
  font-weight: 300;
}

.auth-title strong {
  font-weight: 500;
}

.auth-social-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.4167rem;
  margin-bottom: 1.5278rem;
}

.auth-social-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5556rem;
  height: 2.3611rem;
  border: 0;
  border-radius: 0.7639rem;
  padding: 0 0.9028rem;
  color: rgba(16, 42, 85, 0.68);
  font-size: 0.7639rem;
  font-weight: 400;
  white-space: nowrap;
  transition: transform 0.18s ease, filter 0.18s ease;
}

.auth-social-btn img {
  width: 0.9028rem;
  height: 0.9028rem;
}

.auth-social-btn:hover {
  transform: translateY(-0.0694rem);
  filter: saturate(1.05);
}

.auth-social-btn:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.auth-social-btn--yandex {
  background: #fff0e8;
}

.auth-social-btn--vk {
  background: #eaf6ff;
}

.auth-social-btn--max {
  background: #edeaff;
}

.auth-divider {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 0.9722rem;
  margin-bottom: 0.9722rem;
}

.auth-divider span {
  height: 1px;
  background: #edf0f5;
}

.auth-divider strong {
  color: #c4c7ce;
  font-size: 0.6944rem;
  font-weight: 400;
}

.auth-fields {
  display: flex;
  flex-direction: column;
  gap: 0.9722rem;
}

.auth-label {
  display: block;
  margin-bottom: 0.4861rem;
  color: #102a55;
  font-size: 0.7639rem;
  font-weight: 400;
}

.auth-label span {
  color: #ff4a4a;
}

.auth-input {
  height: 3.1944rem;
  width: 100%;
  border-radius: 0.6944rem;
  border: 1px solid #d9dce2;
  background: #ffffff;
  padding: 0 0.9722rem;
  color: #102a55;
  font-size: 0.8333rem;
  font-weight: 400;
  outline: none;
  transition: border-color 0.18s ease, background-color 0.18s ease, box-shadow 0.18s ease;
}

.auth-input::placeholder {
  color: #aaaeb6;
  font-weight: 400;
}

.auth-input:focus {
  border-color: #6da8ff;
  box-shadow: 0 0 0 4px rgba(37, 116, 255, 0.08);
}

.auth-fields .relative > button {
  right: 0.8333rem;
  width: 1.8056rem;
  height: 1.8056rem;
}

.auth-fields .relative > button svg {
  width: 1.25rem;
  height: 1.25rem;
}

.auth-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.9722rem;
  margin-top: 0.1389rem;
}

.auth-checkbox {
  display: inline-flex;
  align-items: center;
  gap: 0.5556rem;
  cursor: pointer;
  color: #102a55;
  font-size: 0.7639rem;
  font-weight: 400;
  user-select: none;
}

.auth-checkbox span {
  display: flex;
  width: 0.9028rem;
  height: 0.9028rem;
  align-items: center;
  justify-content: center;
  border-radius: 0.2083rem;
  border-width: 1.7px;
  box-shadow: inset 0 0 0 1px rgba(16, 42, 85, 0.04);
  transition: border-color 0.18s ease, background-color 0.18s ease, box-shadow 0.18s ease;
}

.auth-checkbox:hover span {
  border-color: #7f8da3;
  box-shadow: 0 0 0 3px rgba(40, 116, 255, 0.08), inset 0 0 0 1px rgba(16, 42, 85, 0.05);
}

.auth-forgot,
.auth-alt a {
  color: #0084ff;
  font-weight: 600;
  transition: color 0.18s ease;
}

.auth-forgot:hover,
.auth-alt a:hover {
  color: #006be0;
}

.auth-forgot {
  font-size: 0.7639rem;
}

.auth-submit {
  margin-top: 1px;
  display: flex;
  height: 3.1944rem;
  width: 100%;
  align-items: center;
  justify-content: center;
  border-radius: 0.625rem;
  background: linear-gradient(90deg, #2c66f6 0%, #12bdd0 100%);
  color: #ffffff;
  font-size: 0.7639rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  transition: filter 0.18s ease, transform 0.18s ease;
}

.auth-submit:hover {
  filter: brightness(1.03);
  transform: translateY(-0.0694rem);
}

.auth-submit:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}

.auth-alt {
  margin-top: 0.9722rem;
  color: #102a55;
  font-size: 0.7639rem;
  font-weight: 600;
}

.auth-hero-side {
  padding-right: 0;
}

.auth-hero-card {
  height: calc(100vh - 2.6389rem);
  min-height: 47.9167rem;
  max-height: 58.8889rem;
  overflow: hidden;
  border-radius: 1.1111rem 0 0 1.1111rem;
  background: #dfe7fb;
}

.auth-footer {
  background: #ffffff;
  color: #102a55;
}

.auth-subscribe {
  display: flex;
  min-height: 6.6667rem;
  align-items: center;
  justify-content: center;
  gap: clamp(8.3333rem, 18vw, 22.9167rem);
  border-top: 1px solid #edf1f7;
  border-bottom: 1px solid #e4e8ef;
  background: #eef3f9;
  padding: 1.6667rem 2.7778rem;
}

.auth-footer-brand,
.auth-footer-socials,
.auth-subscribe-form,
.auth-subscribe-form div {
  display: flex;
  align-items: center;
}

.auth-footer-brand {
  gap: 1.8056rem;
}

.auth-footer-brand > img {
  width: 9.4444rem;
  height: auto;
  opacity: 1;
}

.auth-footer-socials {
  gap: 0.3472rem;
}

.auth-footer-socials span {
  display: flex;
  width: 1.5972rem;
  height: 1.5972rem;
  align-items: center;
  justify-content: center;
  border-radius: 69.375rem;
  background: #1689f8;
}

.auth-footer-socials img {
  width: 0.9722rem;
  height: 0.9722rem;
  object-fit: contain;
}

.auth-subscribe-form {
  gap: 1.6667rem;
}

.auth-subscribe-form label {
  font-size: 0.9722rem;
  font-weight: 500;
}

.auth-subscribe-form div {
  position: relative;
  width: 21.25rem;
  height: 3.2639rem;
  overflow: hidden;
  border: 1px solid #d4d9e3;
  border-radius: 69.375rem;
  background: #ffffff;
  box-shadow: none;
}

.auth-subscribe-form input {
  min-width: 0;
  flex: 1;
  height: 100%;
  padding: 0 1.1806rem;
  border: 0;
  color: #102a55;
  font-size: 0.8333rem;
  outline: none;
}

.auth-subscribe-form input::placeholder {
  color: #b6bac2;
}

.auth-subscribe-form button {
  height: calc(100% + 0.1389rem);
  min-width: 11.25rem;
  margin: -0.0694rem -0.0694rem -0.0694rem 0;
  border-radius: 69.375rem;
  background: linear-gradient(90deg, #2c66f6 0%, #12bdd0 100%);
  color: #ffffff;
  font-size: 0.8333rem;
  font-weight: 700;
  letter-spacing: 0.07em;
}

.auth-footer-bottom {
  display: grid;
  grid-template-columns: 11.1111rem 10.4167rem minmax(22.9167rem, 1fr) minmax(18.0556rem, 24.3056rem);
  gap: 3.0556rem;
  max-width: 74.0278rem;
  margin: 0 auto;
  padding: 1.5278rem 0 1.8056rem;
}

.auth-footer-bottom h3 {
  margin: 0 0 1.25rem;
  color: #102a55;
  font-size: 0.9028rem;
  font-weight: 700;
}

.auth-footer-bottom a,
.auth-footer-bottom p,
.auth-footer-bottom small {
  display: block;
  margin: 0 0 1.0417rem;
  color: #102a55;
  font-size: 0.9028rem;
  font-weight: 400;
}

.auth-footer-center {
  text-align: center;
}

.auth-footer-center img {
  width: 4.5139rem;
  height: auto;
  margin: 0.8333rem auto 1.25rem;
}

@media (max-width: 960px) {
  .auth-main {
    grid-template-columns: minmax(34.7222rem, 0.9fr) minmax(36.1111rem, 1.1fr);
  }

  .auth-form-side {
    padding-left: 3.8889rem;
  }

  .auth-form-box {
    margin-top: 8.3333rem;
  }

  .auth-social-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 767.25px) {
  .auth-main {
    display: block;
    min-height: auto;
    padding: 1.6667rem;
  }

  .auth-form-side {
    padding: 0;
  }

  .auth-logo-link {
    margin-top: 1.6667rem;
  }

  .auth-form-box {
    max-width: 38.8889rem;
    margin: 5.5556rem auto 4.1667rem;
  }

  .auth-hero-side {
    display: none;
  }

  .auth-subscribe,
  .auth-subscribe-form {
    flex-direction: column;
    gap: 1.25rem;
  }

  .auth-footer-bottom {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    padding: 1.9444rem 1.6667rem;
  }
}

@media (max-width: 480px) {
  .auth-main {
    padding: 1.25rem;
  }

  .auth-title {
    font-size: 2.5rem;
  }

  .auth-form-box {
    margin-top: 4.0278rem;
  }

  .auth-social-row {
    grid-template-columns: 1fr;
  }

  .auth-row {
    align-items: flex-start;
    flex-direction: column;
    gap: 0.8333rem;
  }

  .auth-subscribe-form div {
    width: min(100%, 21.25rem);
  }

  .auth-footer-bottom {
    grid-template-columns: 1fr;
    text-align: center;
  }
}
</style>
