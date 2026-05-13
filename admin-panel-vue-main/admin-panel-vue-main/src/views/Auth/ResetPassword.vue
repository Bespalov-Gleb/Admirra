<template>
  <FullScreenLayout>
    <div class="auth-page bg-white text-[#102a55]">
      <main class="auth-main">
        <section class="auth-form-side">
          <router-link to="/" class="auth-logo-link">
            <img src="/admirra/img/logo.png" alt="AdMirra" />
          </router-link>

          <div class="auth-form-box auth-form-box--reset">
            <template v-if="!isConfirmMode">
              <h1 class="auth-title">
                <span>Восстановление пароля</span>
                <strong>Верните доступ</strong>
              </h1>

              <p class="auth-lead">
                Введите email, указанный при регистрации. Мы отправим ссылку для сброса пароля.
              </p>

              <div v-if="errorMsg" class="auth-alert auth-alert--error">
                {{ errorMsg }}
              </div>

              <form class="auth-fields" @submit.prevent="handleResetPassword">
                <div>
                  <label for="email" class="auth-label">
                    E-mail <span>*</span>
                  </label>
                  <input
                    v-model="resetForm.email"
                    type="email"
                    id="email"
                    name="email"
                    placeholder="Введите ваш email"
                    autocomplete="email"
                    class="auth-input"
                  />
                </div>

                <button type="submit" :disabled="loading || emailSent" class="auth-submit">
                  <span v-if="loading" class="mr-2 h-5 w-5 animate-spin rounded-full border-2 border-white/35 border-t-white"></span>
                  {{ loading ? 'ОТПРАВКА...' : emailSent ? 'ПИСЬМО ОТПРАВЛЕНО' : 'ОТПРАВИТЬ ССЫЛКУ ДЛЯ СБРОСА' }}
                </button>
              </form>

              <div v-if="emailSent" class="auth-alert auth-alert--success">
                Если email зарегистрирован, ссылка для сброса пароля отправлена на {{ resetForm.email }}
              </div>

              <p class="auth-alt">
                Вспомнили пароль?
                <router-link to="/signin">Войти</router-link>
              </p>
            </template>

            <template v-else>
              <h1 class="auth-title">
                <span>Новый пароль</span>
                <strong>Защитите аккаунт</strong>
              </h1>

              <p class="auth-lead">
                Придумайте надежный пароль. Он должен содержать минимум 8 символов.
              </p>

              <div v-if="errorMsg" class="auth-alert auth-alert--error">
                {{ errorMsg }}
              </div>

              <form class="auth-fields" @submit.prevent="handleConfirmPassword">
                <div>
                  <label for="password" class="auth-label">
                    Новый пароль <span>*</span>
                  </label>
                  <input
                    v-model="confirmForm.password"
                    type="password"
                    id="password"
                    placeholder="Введите новый пароль"
                    class="auth-input"
                  />
                </div>

                <div>
                  <label for="password-repeat" class="auth-label">
                    Повторите пароль <span>*</span>
                  </label>
                  <input
                    v-model="confirmForm.passwordRepeat"
                    type="password"
                    id="password-repeat"
                    placeholder="Повторите пароль"
                    class="auth-input"
                  />
                </div>

                <button type="submit" :disabled="loading" class="auth-submit">
                  <span v-if="loading" class="mr-2 h-5 w-5 animate-spin rounded-full border-2 border-white/35 border-t-white"></span>
                  {{ loading ? 'СОХРАНЕНИЕ...' : 'УСТАНОВИТЬ НОВЫЙ ПАРОЛЬ' }}
                </button>
              </form>
            </template>
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
import { ref, reactive, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import FullScreenLayout from '@/layouts/FullScreenLayout.vue'
import authHero from '@/assets/imgs/auth/auth.webp'
import payMethods from '@/assets/imgs/auth/pay.png'
import api from '@/api/axios'
import { useAuth } from '@/composables/useAuth'

const route = useRoute()
const router = useRouter()
const { setToken, fetchCurrentUser } = useAuth()

const loading = ref(false)
const emailSent = ref(false)
const errorMsg = ref('')

// Определяем, в каком режиме мы находимся
const confirmToken = computed(() => route.query.token || '')
const isConfirmMode = computed(() => !!confirmToken.value)

const resetForm = reactive({ email: '' })
const confirmForm = reactive({ password: '', passwordRepeat: '' })

const isValidEmail = (email) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)

const handleResetPassword = async () => {
  if (!resetForm.email || !isValidEmail(resetForm.email)) return
  loading.value = true
  errorMsg.value = ''
  try {
    await api.post('auth/reset-password/request', { email: resetForm.email })
    emailSent.value = true
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || 'Не удалось отправить запрос'
  } finally {
    loading.value = false
  }
}

const handleConfirmPassword = async () => {
  if (confirmForm.password.length < 8) {
    errorMsg.value = 'Пароль должен быть не менее 8 символов'
    return
  }
  if (confirmForm.password !== confirmForm.passwordRepeat) {
    errorMsg.value = 'Пароли не совпадают'
    return
  }
  loading.value = true
  errorMsg.value = ''
  try {
    const { data } = await api.post('auth/reset-password/confirm', {
      token: confirmToken.value,
      new_password: confirmForm.password,
    })
    setToken(data.access_token)
    await fetchCurrentUser()
    router.push('/')
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || 'Ссылка недействительна или срок действия истёк'
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
  max-width: 33.4722rem;
  margin-top: clamp(7.0833rem, 15vh, 10.9722rem);
}

.auth-title {
  margin: 0 0 1.25rem;
  color: #102a55;
  font-size: clamp(2.5rem, 2.7vw, 3.4722rem);
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

.auth-lead {
  max-width: 29.1667rem;
  margin: 0 0 1.9444rem;
  color: rgba(16, 42, 85, 0.62);
  font-size: 1.0417rem;
  font-weight: 400;
  line-height: 1.45;
}

.auth-fields {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.auth-label {
  display: block;
  margin-bottom: 0.625rem;
  color: #102a55;
  font-size: 0.9028rem;
  font-weight: 400;
}

.auth-label span {
  color: #ff4a4a;
}

.auth-input {
  height: 4.0278rem;
  width: 100%;
  border-radius: 0.8333rem;
  border: 1px solid #d9dce2;
  background: #ffffff;
  padding: 0 1.1806rem;
  color: #102a55;
  font-size: 1.0417rem;
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

.auth-submit {
  margin-top: 1px;
  display: flex;
  height: 4.0278rem;
  width: 100%;
  align-items: center;
  justify-content: center;
  border-radius: 0.7639rem;
  background: linear-gradient(90deg, #2c66f6 0%, #12bdd0 100%);
  color: #ffffff;
  font-size: 0.9028rem;
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
  margin-top: 1.25rem;
  color: #102a55;
  font-size: 0.9028rem;
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

.auth-alert {
  margin-bottom: 1.25rem;
  border-radius: 0.8333rem;
  padding: 0.9028rem 1.1111rem;
  font-size: 0.9028rem;
  font-weight: 500;
  line-height: 1.35;
}

.auth-alert--error {
  border: 1px solid #fecaca;
  background: #fef2f2;
  color: #dc2626;
}

.auth-alert--success {
  margin-top: 1.25rem;
  margin-bottom: 0;
  border: 1px solid #bbf7d0;
  background: #f0fdf4;
  color: #15803d;
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

  .auth-title span {
    white-space: normal;
  }

  .auth-form-box {
    margin-top: 4.0278rem;
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
