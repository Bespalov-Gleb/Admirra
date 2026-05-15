<template>
  <FullScreenLayout>
    <div class="auth-page bg-white text-[#102a55]">
      <main class="auth-main">
        <section class="auth-form-side">
          <router-link to="/" class="auth-logo-link">
            <img src="/admirra/img/logo.png" alt="AdMirra" />
          </router-link>

          <div class="auth-form-box auth-form-box--signup">
            <h1 class="auth-title">
              <span>Добро пожаловать!</span>
              <strong>Зарегистрируйтесь</strong>
            </h1>

            <div class="auth-social-row">
              <button
                type="button"
                :disabled="oauthLoading"
                class="auth-social-btn auth-social-btn--yandex"
                @click="handleYandexLogin"
              >
                <img src="/admirra/img/icons/yandex.png" alt="" class="h-[16px] w-[16px] object-contain" />
                Яндекс ID
              </button>
              <button
                type="button"
                :disabled="oauthLoading"
                class="auth-social-btn auth-social-btn--vk"
                @click="handleVkLogin"
              >
                <img src="/admirra/img/icons/vk.png" alt="" class="h-[16px] w-[16px] object-contain" />
                ВКонтакте
              </button>
              <button
                type="button"
                :disabled="oauthLoading"
                class="auth-social-btn auth-social-btn--max"
                @click="handleMaxLogin"
              >
                <img src="/admirra/img/icons/max.png" alt="" class="h-[16px] w-[16px] object-contain" />
                Max
              </button>
            </div>

            <div class="auth-divider">
              <span></span>
              <strong>или</strong>
              <span></span>
            </div>

            <div v-if="errorMessage" class="mb-4 rounded-[12px] border border-red-200 bg-red-50 px-4 py-3 text-[13px] font-medium text-red-600">
              {{ errorMessage }}
            </div>
            <div v-if="maxLoginMessage" class="mb-4 rounded-[12px] border border-blue-100 bg-blue-50 px-4 py-3 text-[13px] font-medium text-blue-700">
              {{ maxLoginMessage }}
            </div>

            <form class="auth-fields" @submit.prevent="handleRegister">
              <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label for="fname" class="auth-label">
                    Имя <span>*</span>
                  </label>
                  <input
                    v-model="registerForm.username"
                    type="text"
                    id="fname"
                    name="fname"
                    placeholder="Введите имя"
                    class="auth-input"
                  />
                </div>
                <div>
                  <label for="lname" class="auth-label">
                    Фамилия <span>*</span>
                  </label>
                  <input
                    v-model="registerForm.lastName"
                    type="text"
                    id="lname"
                    name="lname"
                    placeholder="Введите фамилию"
                    class="auth-input"
                  />
                </div>
              </div>

              <div>
                <label for="email" class="auth-label">
                  E-mail <span>*</span>
                </label>
                <input
                  v-model="registerForm.email"
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
                    v-model="registerForm.password"
                    :type="showPassword ? 'text' : 'password'"
                    id="password"
                    placeholder="Введите пароль"
                    class="auth-input pr-14"
                  />
                  <button
                    type="button"
                    class="absolute right-[17px] top-1/2 flex h-8 w-8 -translate-y-1/2 items-center justify-center text-[#a6a9ad] transition hover:text-[#102a55]"
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

              <label for="checkboxLabelOne" class="auth-checkbox auth-checkbox--terms">
                <input v-model="registerForm.agree" type="checkbox" id="checkboxLabelOne" class="sr-only" />
                <span :class="registerForm.agree ? 'border-[#2874ff] bg-[#2874ff]' : 'border-[#aeb7c7] bg-[#f8fafc]'">
                  <svg v-if="registerForm.agree" width="12" height="12" viewBox="0 0 14 14" fill="none">
                    <path d="M11.6666 3.5L5.24992 9.91667L2.33325 7" stroke="white" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" />
                  </svg>
                </span>
                <em>
                  Создавая аккаунт, вы соглашаетесь с условиями использования и политикой конфиденциальности
                </em>
              </label>

              <button type="submit" :disabled="loading" class="auth-submit">
                <span v-if="loading" class="mr-2 h-5 w-5 animate-spin rounded-full border-2 border-white/35 border-t-white"></span>
                {{ loading ? 'Регистрация...' : 'ЗАРЕГИСТРИРОВАТЬСЯ' }}
              </button>
            </form>

            <p class="auth-alt">
              Уже есть аккаунт?
              <router-link to="/signin">Войти</router-link>
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
import FullScreenLayout from '@/layouts/FullScreenLayout.vue'
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuth } from '@/composables/useAuth'
import { useOAuthLogin } from '@/composables/useOAuthLogin'
import { DEFAULT_DASHBOARD_PATH } from '@/constants/config'
import { getAuthProvider, setAuthProvider } from '@/utils/authToken'
import authHero from '@/assets/imgs/auth/auth.webp'
import payMethods from '@/assets/imgs/auth/pay.png'

const router = useRouter()
const { register, checkAuth, fetchCurrentUser, setToken, getErrorMessage } = useAuth()
const { startYandexLogin, startVkLogin, startMaxLogin } = useOAuthLogin()
const showPassword = ref(false)
const loading = ref(false)
const oauthLoading = ref(false)
const maxLoginMessage = ref('')

const registerForm = reactive({
  username: '',
  lastName: '',
  email: '',
  password: '',
  agree: false
})

const errorMessage = ref('')

const reuseProviderSession = async (provider) => {
  if (getAuthProvider() !== provider) return false
  const isAuth = await checkAuth()
  if (!isAuth) return false
  router.push(DEFAULT_DASHBOARD_PATH)
  return true
}

const handleYandexLogin = async () => {
  errorMessage.value = ''
  oauthLoading.value = true
  try {
    if (await reuseProviderSession('yandex')) return
    await startYandexLogin()
  } catch (e) {
    oauthLoading.value = false
    errorMessage.value = getErrorMessage(e, 'Не удалось начать регистрацию через Яндекс')
  }
}

const handleVkLogin = async () => {
  errorMessage.value = ''
  oauthLoading.value = true
  try {
    if (await reuseProviderSession('vk')) return
    await startVkLogin()
  } catch (e) {
    oauthLoading.value = false
    errorMessage.value = getErrorMessage(e, 'Не удалось начать регистрацию через ВКонтакте')
  }
}

const handleMaxLogin = async () => {
  errorMessage.value = ''
  maxLoginMessage.value = 'Откройте чат MAX в новом окне и нажмите Start. Страница сама завершит регистрацию.'
  oauthLoading.value = true
  try {
    if (await reuseProviderSession('max')) return
    const data = await startMaxLogin()
    setToken(data.access_token)
    setAuthProvider('max')
    const userResult = await fetchCurrentUser()
    if (!userResult.success) {
      throw new Error('Не удалось загрузить профиль')
    }
    router.push(DEFAULT_DASHBOARD_PATH)
  } catch (e) {
    errorMessage.value = getErrorMessage(e, e?.message || 'Не удалось зарегистрироваться через MAX')
  } finally {
    oauthLoading.value = false
    maxLoginMessage.value = ''
  }
}

const togglePasswordVisibility = () => {
  showPassword.value = !showPassword.value
}

const isValidEmail = (email) => {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
}

const triggerError = (message) => {
  errorMessage.value = message
  setTimeout(() => {
    errorMessage.value = ''
  }, 5000)
}

const handleRegister = async () => {
  // Валидация
  if (!registerForm.username) {
    triggerError('Введите ваше имя')
    return
  }
  if (!registerForm.email) {
    triggerError('Введите Email')
    return
  }
  if (!isValidEmail(registerForm.email)) {
    triggerError('Введите корректный Email')
    return
  }
  if (!registerForm.password) {
    triggerError('Введите пароль')
    return
  }
  if (registerForm.password.length < 6) {
    triggerError('Пароль должен быть не менее 6 символов')
    return
  }
  if (!registerForm.agree) {
    triggerError('Вы должны согласиться с условиями')
    return
  }

  loading.value = true
  errorMessage.value = ''
  
  try {
    const result = await register(
      registerForm.email, 
      registerForm.password, 
      registerForm.username,
      registerForm.username, // first_name
      registerForm.lastName  // last_name
    )
    
    if (result.success) {
      router.push({
        path: '/pending-email-verification',
        query: { email: result.email || registerForm.email }
      })
    } else {
      triggerError(result.message || 'Ошибка регистрации')
    }
  } catch (error) {
    console.error('Registration error:', error)
    triggerError('Произошла ошибка при регистрации')
  } finally {
    loading.value = false
  }
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
  grid-template-columns: minmax(500px, 0.96fr) minmax(610px, 1.04fr);
  gap: 22px;
  min-height: min(100vh, 782px);
  padding: 20px 0 18px 0;
}

.auth-form-side {
  position: relative;
  padding-left: clamp(68px, 9vw, 144px);
  padding-right: 30px;
}

.auth-logo-link {
  display: inline-flex;
  margin-top: 35px;
}

.auth-logo-link img {
  width: 136px;
  height: auto;
  opacity: 1;
}

.auth-form-box {
  width: 100%;
  max-width: 386px;
  margin-top: clamp(58px, 8vh, 88px);
}

.auth-form-box--signup {
  margin-top: clamp(43px, 6.4vh, 66px);
}

.auth-title {
  margin: 0 0 22px;
  color: #102a55;
  font-size: clamp(27px, 2vw, 38px);
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
  gap: 6px;
  margin-bottom: 19px;
}

.auth-social-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 34px;
  border: 0;
  border-radius: 11px;
  padding: 0 13px;
  color: rgba(16, 42, 85, 0.68);
  font-size: 11px;
  font-weight: 400;
  white-space: nowrap;
  transition: transform 0.18s ease, filter 0.18s ease;
}

.auth-social-btn img {
  width: 13px;
  height: 13px;
}

.auth-social-btn:hover {
  transform: translateY(-1px);
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
  gap: 14px;
  margin-bottom: 13px;
}

.auth-divider span {
  height: 1px;
  background: #edf0f5;
}

.auth-divider strong {
  color: #c4c7ce;
  font-size: 10px;
  font-weight: 400;
}

.auth-fields {
  display: flex;
  flex-direction: column;
  gap: 11px;
}

.auth-label {
  display: block;
  margin-bottom: 6px;
  color: #102a55;
  font-size: 11px;
  font-weight: 400;
}

.auth-label span {
  color: #ff4a4a;
}

.auth-input {
  height: 43px;
  width: 100%;
  border-radius: 10px;
  border: 1px solid #d9dce2;
  background: #ffffff;
  padding: 0 14px;
  color: #102a55;
  font-size: 12px;
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
  right: 12px;
  width: 26px;
  height: 26px;
}

.auth-fields .relative > button svg {
  width: 18px;
  height: 18px;
}

.auth-checkbox {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: #102a55;
  font-size: 11px;
  font-weight: 400;
  user-select: none;
}

.auth-checkbox--terms {
  align-items: flex-start;
  line-height: 1.45;
}

.auth-checkbox span {
  display: flex;
  width: 13px;
  height: 13px;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  border-radius: 3px;
  border-width: 1.7px;
  box-shadow: inset 0 0 0 1px rgba(16, 42, 85, 0.04);
  transition: border-color 0.18s ease, background-color 0.18s ease, box-shadow 0.18s ease;
}

.auth-checkbox:hover span {
  border-color: #7f8da3;
  box-shadow: 0 0 0 3px rgba(40, 116, 255, 0.08), inset 0 0 0 1px rgba(16, 42, 85, 0.05);
}

.auth-checkbox--terms span {
  margin-top: 2px;
}

.auth-checkbox em {
  font-style: normal;
}

.auth-submit {
  margin-top: 1px;
  display: flex;
  height: 45px;
  width: 100%;
  align-items: center;
  justify-content: center;
  border-radius: 9px;
  background: linear-gradient(90deg, #2c66f6 0%, #12bdd0 100%);
  color: #ffffff;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  transition: filter 0.18s ease, transform 0.18s ease;
}

.auth-submit:hover {
  filter: brightness(1.03);
  transform: translateY(-1px);
}

.auth-submit:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}

.auth-alt {
  margin-top: 13px;
  color: #102a55;
  font-size: 11px;
  font-weight: 600;
}

.auth-alt a {
  color: #0084ff;
  font-weight: 600;
  transition: color 0.18s ease;
}

.auth-alt a:hover {
  color: #006be0;
}

.auth-hero-side {
  padding-right: 0;
}

.auth-hero-card {
  height: calc(100vh - 38px);
  min-height: 690px;
  max-height: 848px;
  overflow: hidden;
  border-radius: 16px 0 0 16px;
  background: #dfe7fb;
}

.auth-footer {
  background: #ffffff;
  color: #102a55;
}

.auth-subscribe {
  display: flex;
  min-height: 96px;
  align-items: center;
  justify-content: center;
  gap: clamp(120px, 18vw, 330px);
  border-top: 1px solid #edf1f7;
  border-bottom: 1px solid #e4e8ef;
  background: #eef3f9;
  padding: 24px 40px;
}

.auth-footer-brand,
.auth-footer-socials,
.auth-subscribe-form,
.auth-subscribe-form div {
  display: flex;
  align-items: center;
}

.auth-footer-brand {
  gap: 26px;
}

.auth-footer-brand > img {
  width: 136px;
  height: auto;
  opacity: 1;
}

.auth-footer-socials {
  gap: 5px;
}

.auth-footer-socials span {
  display: flex;
  width: 23px;
  height: 23px;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: #1689f8;
}

.auth-footer-socials img {
  width: 14px;
  height: 14px;
  object-fit: contain;
}

.auth-subscribe-form {
  gap: 24px;
}

.auth-subscribe-form label {
  font-size: 14px;
  font-weight: 500;
}

.auth-subscribe-form div {
  position: relative;
  width: 306px;
  height: 47px;
  overflow: hidden;
  border: 1px solid #d4d9e3;
  border-radius: 999px;
  background: #ffffff;
  box-shadow: none;
}

.auth-subscribe-form input {
  min-width: 0;
  flex: 1;
  height: 100%;
  padding: 0 17px;
  border: 0;
  color: #102a55;
  font-size: 12px;
  outline: none;
}

.auth-subscribe-form input::placeholder {
  color: #b6bac2;
}

.auth-subscribe-form button {
  height: calc(100% + 2px);
  min-width: 162px;
  margin: -1px -1px -1px 0;
  border-radius: 999px;
  background: linear-gradient(90deg, #2c66f6 0%, #12bdd0 100%);
  color: #ffffff;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.07em;
}

.auth-footer-bottom {
  display: grid;
  grid-template-columns: 160px 150px minmax(330px, 1fr) minmax(260px, 350px);
  gap: 44px;
  max-width: 1066px;
  margin: 0 auto;
  padding: 22px 0 26px;
}

.auth-footer-bottom h3 {
  margin: 0 0 18px;
  color: #102a55;
  font-size: 13px;
  font-weight: 700;
}

.auth-footer-bottom a,
.auth-footer-bottom p,
.auth-footer-bottom small {
  display: block;
  margin: 0 0 15px;
  color: #102a55;
  font-size: 13px;
  font-weight: 400;
}

.auth-footer-center {
  text-align: center;
}

.auth-footer-center img {
  width: 65px;
  height: auto;
  margin: 12px auto 18px;
}

@media (max-width: 1280px) {
  .auth-main {
    grid-template-columns: minmax(500px, 0.9fr) minmax(520px, 1.1fr);
  }

  .auth-form-side {
    padding-left: 56px;
  }

  .auth-social-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 1023px) {
  .auth-main {
    display: block;
    min-height: auto;
    padding: 24px;
  }

  .auth-form-side {
    padding: 0;
  }

  .auth-logo-link {
    margin-top: 24px;
  }

  .auth-form-box,
  .auth-form-box--signup {
    max-width: 560px;
    margin: 70px auto 60px;
  }

  .auth-hero-side {
    display: none;
  }

  .auth-subscribe,
  .auth-subscribe-form {
    flex-direction: column;
    gap: 18px;
  }

  .auth-footer-bottom {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    padding: 28px 24px;
  }
}

@media (max-width: 640px) {
  .auth-main {
    padding: 18px;
  }

  .auth-title {
    font-size: 34px;
  }

  .auth-form-box,
  .auth-form-box--signup {
    margin-top: 48px;
  }

  .auth-social-row {
    grid-template-columns: 1fr;
  }

  .auth-subscribe-form div {
    width: min(100%, 306px);
  }

  .auth-footer-bottom {
    grid-template-columns: 1fr;
    text-align: center;
  }
}
</style>
