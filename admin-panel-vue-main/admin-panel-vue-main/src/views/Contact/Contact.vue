<template>
  <div class="contact-page px-8 pt-8 pb-10" style="max-width: 62.5rem">
    <div class="mb-8">
      <h1 class="text-28 weight-700 mb-1">Предложить идею</h1>
      <p class="text-14 gray75">Расскажите нам, что можно улучшить в сервисе — мы читаем каждое сообщение</p>
    </div>

    <div class="row gy-4">
      <!-- Форма -->
      <div class="col-12 col-lg-7">
        <div class="card p-5 contact-card" :style="cardStyle">
          <form @submit.prevent="handleSubmit">
            <div class="mb-4">
              <label class="d-block text-13 weight-500 mb-2" :style="labelStyle">Тема</label>
              <input
                v-model="form.subject"
                type="text"
                class="form-control contact-input"
                placeholder="Например: добавить новый источник данных"
                required
                :style="inputStyle"
              />
            </div>
            <div class="mb-4">
              <label class="d-block text-13 weight-500 mb-2" :style="labelStyle">Сообщение</label>
              <textarea
                v-model="form.message"
                class="form-control contact-input"
                rows="6"
                placeholder="Опишите вашу идею подробнее..."
                required
                :style="`${inputStyle}; resize:vertical`"
              ></textarea>
            </div>
            <div class="mb-4">
              <label class="d-block text-13 weight-500 mb-2" :style="labelStyle">Ваш email <span :style="metaStyle">(обязательно — чтобы мы могли ответить)</span></label>
              <input
                v-model="form.email"
                type="email"
                class="form-control contact-input"
                placeholder="name@example.com"
                required
                autocomplete="email"
                :style="inputStyle"
              />
            </div>

            <div v-if="successMsg" class="mb-3 px-4 py-3 text-14 weight-500" :style="successAlertStyle">
              {{ successMsg }}
            </div>
            <div v-if="errorMsg" class="mb-3 px-4 py-3 text-14 weight-500" :style="errorAlertStyle">
              {{ errorMsg }}
            </div>

            <button type="submit" class="btn _primary" :disabled="loading">
              <div class="btn__inner">
                <span class="btn__text" style="color:#fff">{{ loading ? 'Отправка...' : 'Отправить идею' }}</span>
                <div class="btn__icon"><svg><use href="/admirra/img/svg/sprite.svg#idea"></use></svg></div>
              </div>
            </button>
          </form>
        </div>
      </div>

      <!-- Контакты -->
      <div class="col-12 col-lg-5">
        <div class="d-flex flex-column gap-3">
          <div class="p-4 contact-card" :style="cardStyle">
            <div class="text-12 uppercase weight-600 mb-2" :style="metaStyle">Электронная почта</div>
            <a href="mailto:support@admirra.ru" class="text-15 weight-500" style="color:#2E6BFF; text-decoration:none">
              support@admirra.ru
            </a>
          </div>
          <div class="p-4 contact-card" :style="cardStyle">
            <div class="text-12 uppercase weight-600 mb-2" :style="metaStyle">Время работы</div>
            <div class="text-14" :style="textStyle">Пн–Пт: 9:00 – 18:00</div>
            <div class="text-14" :style="textStyle">Сб–Вс: Выходной</div>
          </div>
          <div class="p-4 contact-card" :style="cardStyle">
            <div class="text-12 uppercase weight-600 mb-2" :style="metaStyle">Telegram-бот</div>
            <a href="https://t.me/admirra_support_bot" target="_blank" class="text-14 weight-500"
              style="color:#2E6BFF; text-decoration:none">
              @admirra_support_bot
            </a>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import api from '../../api/axios'
import { useTheme } from '../../composables/useTheme'

const form = ref({ subject: '', message: '', email: '' })
const loading = ref(false)
const successMsg = ref('')
const errorMsg = ref('')
const { isDarkMode } = useTheme()

const cardStyle = computed(() => isDarkMode.value
  ? 'background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.1); border-radius:1.1111rem; box-shadow:none'
  : 'background:#fff; border-radius:1.1111rem; box-shadow:0 2px 12px rgba(0,0,0,.06)')

const inputStyle = computed(() => isDarkMode.value
  ? 'border-radius:0.6944rem; font-size:0.9722rem; background:rgba(255,255,255,0.07); border:1px solid rgba(255,255,255,0.15); color:#fff'
  : 'border-radius:0.6944rem; font-size:0.9722rem')

const labelStyle = computed(() => isDarkMode.value ? 'color:rgba(255,255,255,0.85)' : 'color:#515151')
const metaStyle = computed(() => isDarkMode.value ? 'color:rgba(255,255,255,0.55)' : 'color:rgba(105,105,105,0.56)')
const textStyle = computed(() => isDarkMode.value ? 'color:rgba(255,255,255,0.85)' : 'color:#515151')

const successAlertStyle = computed(() => isDarkMode.value
  ? 'background:rgba(34,197,94,0.18); border-radius:0.6944rem; color:#86efac; border:1px solid rgba(34,197,94,0.35)'
  : 'background:#f0fdf4; border-radius:0.6944rem; color:#16a34a')

const errorAlertStyle = computed(() => isDarkMode.value
  ? 'background:rgba(248,113,113,0.15); border-radius:0.6944rem; color:#fca5a5; border:1px solid rgba(248,113,113,0.35)'
  : 'background:#fef2f2; border-radius:0.6944rem; color:#dc2626')

const formatApiError = (err) => {
  const d = err.response?.data?.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d)) {
    return d.map((e) => e.msg || e.message || JSON.stringify(e)).join('; ')
  }
  if (d && typeof d === 'object') return d.message || JSON.stringify(d)
  return err.message || 'Не удалось отправить. Попробуйте позже.'
}

const handleSubmit = async () => {
  loading.value = true
  successMsg.value = ''
  errorMsg.value = ''
  const email = (form.value.email || '').trim()
  if (!email) {
    errorMsg.value = 'Укажите email — без него мы не сможем ответить.'
    loading.value = false
    return
  }
  try {
    await api.post('support/idea', {
      subject: form.value.subject.trim(),
      message: form.value.message.trim(),
      email
    })
    successMsg.value = 'Спасибо! Идея отправлена на почту команды. Мы свяжемся с вами при необходимости.'
    form.value = { subject: '', message: '', email: '' }
  } catch (err) {
    errorMsg.value = formatApiError(err)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
:global(html.darkmode) .contact-page,
:global(body.darkmode) .contact-page,
:global(html.dark) .contact-page,
:global(body.dark) .contact-page {
  color: #fff;
}

:global(html.darkmode) .contact-card,
:global(body.darkmode) .contact-card,
:global(html.dark) .contact-card,
:global(body.dark) .contact-card {
  background: rgba(255, 255, 255, 0.06) !important;
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: none !important;
}

:global(html.darkmode) .contact-page .gray75,
:global(body.darkmode) .contact-page .gray75,
:global(html.dark) .contact-page .gray75,
:global(body.dark) .contact-page .gray75 {
  color: rgba(255, 255, 255, 0.65) !important;
}

:global(html.darkmode) .contact-page .gray500,
:global(body.darkmode) .contact-page .gray500,
:global(html.dark) .contact-page .gray500,
:global(body.dark) .contact-page .gray500 {
  color: rgba(255, 255, 255, 0.85) !important;
}

:global(html.darkmode) .contact-page .gray56,
:global(body.darkmode) .contact-page .gray56,
:global(html.dark) .contact-page .gray56,
:global(body.dark) .contact-page .gray56 {
  color: rgba(255, 255, 255, 0.55) !important;
}

:global(html.darkmode) .contact-input,
:global(body.darkmode) .contact-input,
:global(html.dark) .contact-input,
:global(body.dark) .contact-input {
  background: rgba(255, 255, 255, 0.07) !important;
  border-color: rgba(255, 255, 255, 0.15) !important;
  color: #fff !important;
}

:global(html.darkmode) .contact-input::placeholder,
:global(body.darkmode) .contact-input::placeholder,
:global(html.dark) .contact-input::placeholder,
:global(body.dark) .contact-input::placeholder {
  color: rgba(255, 255, 255, 0.5);
}
</style>
