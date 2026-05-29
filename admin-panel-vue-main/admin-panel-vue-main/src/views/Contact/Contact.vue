<template>
  <div class="contact-root">

    <!-- Hero header -->
    <div class="contact-hero">
      <div class="contact-hero__bg" aria-hidden="true">
        <div class="contact-hero__blob contact-hero__blob--1"></div>
        <div class="contact-hero__blob contact-hero__blob--2"></div>
      </div>
      <div class="contact-hero__inner">
        <div class="contact-hero__icon-wrap">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 2a5 5 0 0 1 5 5c0 2.4-1.4 4.5-3.5 5.4L15 22H9l1.5-9.6C8.4 11.5 7 9.4 7 7a5 5 0 0 1 5-5z"/>
          </svg>
        </div>
        <div>
          <h1 class="contact-hero__title">Что допилить?</h1>
          <p class="contact-hero__sub">Расскажите, что можно улучшить — мы читаем каждое сообщение и отвечаем лично</p>
        </div>
      </div>
    </div>

    <!-- Content grid -->
    <div class="contact-grid">

      <!-- Form card -->
      <div class="contact-card">
        <form @submit.prevent="handleSubmit" novalidate>
          <div class="contact-field">
            <label class="contact-label">Тема</label>
            <input
              v-model="form.subject"
              type="text"
              class="contact-input"
              placeholder="Например: добавить новый источник данных"
              required
            />
          </div>

          <div class="contact-field">
            <label class="contact-label">Сообщение</label>
            <textarea
              v-model="form.message"
              class="contact-input contact-textarea"
              rows="6"
              placeholder="Опишите вашу идею подробнее — чем конкретнее, тем лучше"
              required
            ></textarea>
          </div>

          <div class="contact-field">
            <label class="contact-label">
              Ваш email
              <span class="contact-label__hint">— чтобы мы могли ответить</span>
            </label>
            <input
              v-model="form.email"
              type="email"
              class="contact-input"
              placeholder="name@example.com"
              required
              autocomplete="email"
            />
          </div>

          <!-- Chips — быстрый выбор темы -->
          <div class="contact-chips">
            <span class="contact-chips__label">Быстрый выбор:</span>
            <button
              v-for="chip in chips"
              :key="chip"
              type="button"
              class="contact-chip"
              :class="{ 'contact-chip--active': form.subject === chip }"
              @click="form.subject = form.subject === chip ? '' : chip"
            >{{ chip }}</button>
          </div>

          <div v-if="successMsg" class="contact-alert contact-alert--success">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
            </svg>
            {{ successMsg }}
          </div>
          <div v-if="errorMsg" class="contact-alert contact-alert--error">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
            </svg>
            {{ errorMsg }}
          </div>

          <button type="submit" class="contact-submit" :disabled="loading">
            <svg v-if="loading" class="contact-submit__spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
              <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
            </svg>
            <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
            </svg>
            {{ loading ? 'Отправка...' : 'Отправить' }}
          </button>
        </form>
      </div>

      <!-- Right column -->
      <div class="contact-aside">

        <!-- Contact info cards -->
        <div class="contact-info-card">
          <div class="contact-info-card__icon" style="background: #eff6ff;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/>
            </svg>
          </div>
          <div>
            <div class="contact-info-card__label">Электронная почта</div>
            <a href="mailto:support@admirra.ru" class="contact-info-card__value contact-info-card__value--link">
              support@admirra.ru
            </a>
          </div>
        </div>

        <div class="contact-info-card">
          <div class="contact-info-card__icon" style="background: #f0fdf4;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
            </svg>
          </div>
          <div>
            <div class="contact-info-card__label">Время работы</div>
            <div class="contact-info-card__value">Пн–Пт: 9:00 – 18:00</div>
            <div class="contact-info-card__sub">Сб–Вс: выходной</div>
          </div>
        </div>

        <div class="contact-info-card">
          <div class="contact-info-card__icon" style="background: #eff6ff;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21.198 2.433a2.242 2.242 0 0 0-1.022.215l-16.5 7.5a2.25 2.25 0 0 0 .126 4.073l4.98 1.995 2.246 5.621a2.25 2.25 0 0 0 4.078.132l7.5-17.25a2.242 2.242 0 0 0-1.408-2.286z"/>
            </svg>
          </div>
          <div>
            <div class="contact-info-card__label">Telegram-бот</div>
            <a href="https://t.me/admirra_support_bot" target="_blank" class="contact-info-card__value contact-info-card__value--link">
              @admirra_support_bot
            </a>
          </div>
        </div>

        <!-- Promise block -->
        <div class="contact-promise">
          <div class="contact-promise__row">
            <div class="contact-promise__dot contact-promise__dot--blue"></div>
            <span>Читаем каждое сообщение</span>
          </div>
          <div class="contact-promise__row">
            <div class="contact-promise__dot contact-promise__dot--green"></div>
            <span>Отвечаем в течение 1 рабочего дня</span>
          </div>
          <div class="contact-promise__row">
            <div class="contact-promise__dot contact-promise__dot--purple"></div>
            <span>Лучшие идеи попадают в релиз</span>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import api from '../../api/axios'

const form = ref({ subject: '', message: '', email: '' })
const loading = ref(false)
const successMsg = ref('')
const errorMsg = ref('')

const chips = ['Новый источник данных', 'Улучшить отчёты', 'Баг / ошибка', 'Интеграция', 'Другое']

const formatApiError = (err) => {
  const d = err.response?.data?.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d)) return d.map((e) => e.msg || e.message || JSON.stringify(e)).join('; ')
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
      email,
    })
    successMsg.value = 'Спасибо! Идея отправлена команде. Мы свяжемся с вами при необходимости.'
    form.value = { subject: '', message: '', email: '' }
  } catch (err) {
    errorMsg.value = formatApiError(err)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* ===== Root ===== */
.contact-root {
  min-height: 100%;
  padding: 2.0833rem 1.7361rem;
  max-width: 64rem;
}

/* ===== Hero ===== */
.contact-hero {
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 55%, #1e40af 100%);
  border-radius: 1.25rem;
  padding: 2rem 2.5rem;
  margin-bottom: 1.6667rem;
  box-shadow: 0 4px 20px rgba(37, 99, 235, 0.28);
}

.contact-hero__bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.contact-hero__blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(40px);
  opacity: 0.25;
}

.contact-hero__blob--1 {
  width: 18rem;
  height: 18rem;
  background: #60a5fa;
  top: -6rem;
  right: 4rem;
}

.contact-hero__blob--2 {
  width: 12rem;
  height: 12rem;
  background: #818cf8;
  bottom: -4rem;
  left: 8rem;
}

.contact-hero__inner {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 1.25rem;
}

.contact-hero__icon-wrap {
  flex-shrink: 0;
  width: 3.5rem;
  height: 3.5rem;
  border-radius: 1rem;
  background: rgba(255, 255, 255, 0.18);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  backdrop-filter: blur(6px);
}

.contact-hero__title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #fff;
  line-height: 1.2;
  margin: 0 0 0.375rem;
  letter-spacing: -0.02em;
}

.contact-hero__sub {
  font-size: 0.9028rem;
  color: rgba(255, 255, 255, 0.82);
  margin: 0;
  line-height: 1.5;
}

/* ===== Grid ===== */
.contact-grid {
  display: grid;
  grid-template-columns: 1fr 21rem;
  gap: 1.25rem;
  align-items: start;
}

@media (max-width: 860px) {
  .contact-grid { grid-template-columns: 1fr; }
}

/* ===== Form card ===== */
.contact-card {
  background: #fff;
  border-radius: 1.0417rem;
  padding: 1.6667rem 2rem;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.contact-field {
  margin-bottom: 1.1111rem;
}

.contact-label {
  display: block;
  font-size: 0.8333rem;
  font-weight: 600;
  color: #515151;
  margin-bottom: 0.4167rem;
}

.contact-label__hint {
  font-weight: 400;
  color: rgba(105, 105, 105, 0.65);
  margin-left: 0.25rem;
}

.contact-input {
  width: 100%;
  padding: 0.6944rem 0.9722rem;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 0.6944rem;
  font-size: 0.9028rem;
  color: #171717;
  background: #f8f9fb;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s, background 0.2s;
  font-family: inherit;
  box-sizing: border-box;
}

.contact-input:focus {
  border-color: #2563eb;
  background: #fff;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.contact-textarea {
  resize: vertical;
  min-height: 9rem;
}

/* Chips */
.contact-chips {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4167rem;
  margin-bottom: 1.25rem;
}

.contact-chips__label {
  font-size: 0.75rem;
  color: rgba(105, 105, 105, 0.56);
  font-weight: 500;
  flex-shrink: 0;
}

.contact-chip {
  padding: 0.2778rem 0.6944rem;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 6.25rem;
  font-size: 0.7778rem;
  font-weight: 500;
  color: #515151;
  background: #f5f7f9;
  cursor: pointer;
  transition: all 0.18s;
  white-space: nowrap;
}

.contact-chip:hover {
  border-color: #2563eb;
  color: #2563eb;
  background: #eff6ff;
}

.contact-chip--active {
  border-color: #2563eb;
  color: #2563eb;
  background: #eff6ff;
}

/* Alerts */
.contact-alert {
  display: flex;
  align-items: flex-start;
  gap: 0.5556rem;
  padding: 0.75rem 1rem;
  border-radius: 0.6944rem;
  font-size: 0.8611rem;
  font-weight: 500;
  line-height: 1.5;
  margin-bottom: 1rem;
}

.contact-alert--success {
  background: #f0fdf4;
  color: #15803d;
  border: 1px solid #bbf7d0;
}

.contact-alert--error {
  background: #fef2f2;
  color: #dc2626;
  border: 1px solid #fecaca;
}

.contact-alert svg { flex-shrink: 0; margin-top: 0.1rem; }

/* Submit button */
.contact-submit {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.7222rem 1.5rem;
  border: none;
  border-radius: 0.8333rem;
  background: linear-gradient(270deg, #ff8a2a 0%, #ff6a3d 48%, #f25b2a 100%);
  color: #fff;
  font-size: 0.9028rem;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s, transform 0.15s, box-shadow 0.2s;
  box-shadow: 0 3px 12px rgba(242, 91, 42, 0.3);
}

.contact-submit:hover:not(:disabled) {
  opacity: 0.92;
  transform: translateY(-1px);
  box-shadow: 0 5px 16px rgba(242, 91, 42, 0.38);
}

.contact-submit:active:not(:disabled) { transform: translateY(0); }

.contact-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.contact-submit__spin {
  animation: spin 0.9s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* ===== Aside ===== */
.contact-aside {
  display: flex;
  flex-direction: column;
  gap: 0.8333rem;
}

/* Info cards */
.contact-info-card {
  background: #fff;
  border-radius: 1.0417rem;
  padding: 1rem 1.25rem;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  display: flex;
  align-items: flex-start;
  gap: 0.8333rem;
}

.contact-info-card__icon {
  flex-shrink: 0;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 0.6944rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.contact-info-card__label {
  font-size: 0.7222rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: rgba(105, 105, 105, 0.56);
  margin-bottom: 0.25rem;
}

.contact-info-card__value {
  font-size: 0.9028rem;
  font-weight: 500;
  color: #171717;
}

.contact-info-card__value--link {
  color: #2563eb;
  text-decoration: none;
  transition: color 0.15s;
}

.contact-info-card__value--link:hover { color: #1d4ed8; text-decoration: underline; }

.contact-info-card__sub {
  font-size: 0.8rem;
  color: rgba(105, 105, 105, 0.56);
  margin-top: 0.1667rem;
}

/* Promise block */
.contact-promise {
  background: #fff;
  border-radius: 1.0417rem;
  padding: 1.1111rem 1.25rem;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  display: flex;
  flex-direction: column;
  gap: 0.6944rem;
}

.contact-promise__row {
  display: flex;
  align-items: center;
  gap: 0.6944rem;
  font-size: 0.8611rem;
  color: #515151;
  font-weight: 500;
}

.contact-promise__dot {
  width: 0.4167rem;
  height: 0.4167rem;
  border-radius: 50%;
  flex-shrink: 0;
}

.contact-promise__dot--blue   { background: #2563eb; }
.contact-promise__dot--green  { background: #16a34a; }
.contact-promise__dot--purple { background: #7c3aed; }

/* ===== Dark mode ===== */
:global(.dark) .contact-card,
:global(.darkmode) .contact-card,
:global(.dark) .contact-info-card,
:global(.darkmode) .contact-info-card,
:global(.dark) .contact-promise,
:global(.darkmode) .contact-promise {
  background: #2C2F3D;
  box-shadow: 0 4px 24px rgba(0,0,0,0.28), inset 0 1px 0 rgba(255,255,255,0.07);
}

:global(.dark) .contact-hero__title,
:global(.darkmode) .contact-hero__title { color: #fff; }

:global(.dark) .contact-label,
:global(.darkmode) .contact-label { color: rgba(255,255,255,0.85); }

:global(.dark) .contact-label__hint,
:global(.darkmode) .contact-label__hint { color: rgba(255,255,255,0.4); }

:global(.dark) .contact-input,
:global(.darkmode) .contact-input {
  background: rgba(255,255,255,0.07);
  border-color: rgba(255,255,255,0.12);
  color: #fff;
}

:global(.dark) .contact-input::placeholder,
:global(.darkmode) .contact-input::placeholder { color: rgba(255,255,255,0.35); }

:global(.dark) .contact-input:focus,
:global(.darkmode) .contact-input:focus {
  background: rgba(255,255,255,0.10);
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59,130,246,0.15);
}

:global(.dark) .contact-chip,
:global(.darkmode) .contact-chip {
  background: rgba(255,255,255,0.07);
  border-color: rgba(255,255,255,0.12);
  color: rgba(255,255,255,0.65);
}

:global(.dark) .contact-chip:hover,
:global(.darkmode) .contact-chip:hover,
:global(.dark) .contact-chip--active,
:global(.darkmode) .contact-chip--active {
  border-color: #3b82f6;
  color: #60a5fa;
  background: rgba(59,130,246,0.12);
}

:global(.dark) .contact-chips__label,
:global(.darkmode) .contact-chips__label { color: rgba(255,255,255,0.35); }

:global(.dark) .contact-info-card__label,
:global(.darkmode) .contact-info-card__label { color: rgba(255,255,255,0.4); }

:global(.dark) .contact-info-card__value,
:global(.darkmode) .contact-info-card__value { color: rgba(255,255,255,0.9); }

:global(.dark) .contact-info-card__sub,
:global(.darkmode) .contact-info-card__sub { color: rgba(255,255,255,0.4); }

:global(.dark) .contact-promise__row,
:global(.darkmode) .contact-promise__row { color: rgba(255,255,255,0.75); }

:global(.dark) .contact-alert--success,
:global(.darkmode) .contact-alert--success {
  background: rgba(34,197,94,0.12);
  color: #86efac;
  border-color: rgba(34,197,94,0.25);
}

:global(.dark) .contact-alert--error,
:global(.darkmode) .contact-alert--error {
  background: rgba(248,113,113,0.12);
  color: #fca5a5;
  border-color: rgba(248,113,113,0.25);
}
</style>
