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
            <img :src="authHero" alt="" class="h-full w-full object-cover object-center" />
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
import authHero from '@/assets/imgs/auth/auth.png'
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
  max-width: 482px;
  margin-top: clamp(102px, 15vh, 158px);
}

.auth-title {
  margin: 0 0 18px;
  color: #102a55;
  font-size: clamp(36px, 2.7vw, 50px);
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
  max-width: 420px;
  margin: 0 0 28px;
  color: rgba(16, 42, 85, 0.62);
  font-size: 15px;
  font-weight: 400;
  line-height: 1.45;
}

.auth-fields {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.auth-label {
  display: block;
  margin-bottom: 9px;
  color: #102a55;
  font-size: 13px;
  font-weight: 400;
}

.auth-label span {
  color: #ff4a4a;
}

.auth-input {
  height: 58px;
  width: 100%;
  border-radius: 12px;
  border: 1px solid #d9dce2;
  background: #ffffff;
  padding: 0 17px;
  color: #102a55;
  font-size: 15px;
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
  height: 58px;
  width: 100%;
  align-items: center;
  justify-content: center;
  border-radius: 11px;
  background: linear-gradient(90deg, #2c66f6 0%, #12bdd0 100%);
  color: #ffffff;
  font-size: 13px;
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
  margin-top: 18px;
  color: #102a55;
  font-size: 13px;
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
  margin-bottom: 18px;
  border-radius: 12px;
  padding: 13px 16px;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.35;
}

.auth-alert--error {
  border: 1px solid #fecaca;
  background: #fef2f2;
  color: #dc2626;
}

.auth-alert--success {
  margin-top: 18px;
  margin-bottom: 0;
  border: 1px solid #bbf7d0;
  background: #f0fdf4;
  color: #15803d;
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

  .auth-form-box {
    margin-top: 120px;
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

  .auth-form-box {
    max-width: 560px;
    margin: 80px auto 60px;
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
    font-size: 36px;
  }

  .auth-title span {
    white-space: normal;
  }

  .auth-form-box {
    margin-top: 58px;
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
