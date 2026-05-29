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
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9 21h6M12 3a6 6 0 0 1 6 6c0 2.5-1.4 4.7-3.5 5.9V17a1 1 0 0 1-1 1h-3a1 1 0 0 1-1-1v-2.1C7.4 13.7 6 11.5 6 9a6 6 0 0 1 6-6z"/>
          </svg>
        </div>
        <div class="contact-hero__text">
          <h1 class="contact-hero__title">Что допилить?</h1>
          <p class="contact-hero__sub">Идеи, баги, пожелания — всё попадает напрямую в команду</p>
        </div>
        <div class="contact-hero__badges">
          <span class="contact-hero__badge">
            <span class="contact-hero__badge-dot"></span>
            Ответим за 1 день
          </span>
          <span class="contact-hero__badge">
            <span class="contact-hero__badge-dot contact-hero__badge-dot--green"></span>
            Идеи идут в релиз
          </span>
        </div>
      </div>
    </div>

    <!-- Content grid -->
    <div class="contact-grid">

      <!-- Form card -->
      <div class="contact-card">
        <div class="contact-card__header">
          <h2 class="contact-card__title">Ваша идея</h2>
          <p class="contact-card__desc">Опишите подробнее — лучшие идеи попадают в релиз</p>
        </div>

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
              rows="7"
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

          <!-- File attachment -->
          <div class="contact-field">
            <label class="contact-label">
              Скриншоты / файлы
              <span class="contact-label__hint">— до 5 файлов, каждый не более 5 МБ</span>
            </label>
            <div
              class="contact-dropzone"
              :class="{ 'contact-dropzone--over': isDragging }"
              @click="triggerFileInput"
              @dragover.prevent="isDragging = true"
              @dragleave.prevent="isDragging = false"
              @drop.prevent="handleDrop"
            >
              <input
                ref="fileInput"
                type="file"
                multiple
                accept="image/*,.pdf,.doc,.docx,.xls,.xlsx,.txt,.csv,.zip"
                class="contact-dropzone__input"
                @change="handleFileChange"
              />
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" class="contact-dropzone__icon">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
              <span class="contact-dropzone__text">
                Перетащите файлы или <span class="contact-dropzone__link">выберите</span>
              </span>
            </div>

            <!-- Attached files list -->
            <div v-if="attachedFiles.length" class="contact-files">
              <div v-for="(file, idx) in attachedFiles" :key="idx" class="contact-file">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="contact-file__icon">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
                </svg>
                <span class="contact-file__name">{{ file.name }}</span>
                <span class="contact-file__size">{{ formatSize(file.size) }}</span>
                <button type="button" class="contact-file__remove" @click="removeFile(idx)">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                </button>
              </div>
            </div>
            <div v-if="fileError" class="contact-file-error">{{ fileError }}</div>
          </div>

          <!-- Chips -->
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
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;margin-top:0.1rem">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>
            </svg>
            {{ successMsg }}
          </div>
          <div v-if="errorMsg" class="contact-alert contact-alert--error">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;margin-top:0.1rem">
              <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
            </svg>
            {{ errorMsg }}
          </div>

          <button type="submit" class="contact-submit" :disabled="loading">
            <svg v-if="loading" class="contact-submit__spin" width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
              <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
            </svg>
            <svg v-else width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
            </svg>
            {{ loading ? 'Отправка...' : 'Отправить идею' }}
          </button>
        </form>
      </div>

      <!-- Right column -->
      <div class="contact-aside">

        <!-- Email -->
        <div class="contact-info-card">
          <div class="contact-info-card__icon" style="background:#eff6ff;">
            <svg width="19" height="19" viewBox="0 0 24 24" fill="#2563eb">
              <path d="M1.5 8.67v8.58a3 3 0 003 3h15a3 3 0 003-3V8.67l-8.928 5.493a3 3 0 01-3.144 0L1.5 8.67z"/>
              <path d="M22.5 6.908V6.75a3 3 0 00-3-3h-15a3 3 0 00-3 3v.158l9.714 5.978a1.5 1.5 0 001.572 0L22.5 6.908z"/>
            </svg>
          </div>
          <div class="contact-info-card__body">
            <div class="contact-info-card__label">Электронная почта</div>
            <a href="mailto:support@admirra.ru" class="contact-info-card__link">
              support@admirra.ru
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
            </a>
          </div>
        </div>

        <!-- Telegram bot -->
        <div class="contact-info-card">
          <div class="contact-info-card__icon" style="background:#eff6ff;">
            <svg width="19" height="19" viewBox="0 0 32 32" fill="#2563eb">
              <path d="M29.919 6.163l-4.225 19.925c-0.319 1.406-1.15 1.756-2.331 1.094l-6.438-4.744-3.106 2.988c-0.344 0.344-0.631 0.631-1.294 0.631l0.463-6.556 11.931-10.781c0.519-0.462-0.113-0.719-0.806-0.256l-14.75 9.288-6.35-1.988c-1.381-0.431-1.406-1.381 0.288-2.044l24.837-9.569c1.15-0.431 2.156 0.256 1.781 2.013z"/>
            </svg>
          </div>
          <div class="contact-info-card__body">
            <div class="contact-info-card__label">Telegram поддержка</div>
            <a href="https://t.me/admirra_support_bot" target="_blank" class="contact-info-card__link">
              @admirra_support_bot
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
            </a>
          </div>
        </div>

        <!-- Telegram direct -->
        <div class="contact-info-card">
          <div class="contact-info-card__icon" style="background:#eff6ff;">
            <svg width="19" height="19" viewBox="0 0 32 32" fill="#2563eb">
              <path d="M29.919 6.163l-4.225 19.925c-0.319 1.406-1.15 1.756-2.331 1.094l-6.438-4.744-3.106 2.988c-0.344 0.344-0.631 0.631-1.294 0.631l0.463-6.556 11.931-10.781c0.519-0.462-0.113-0.719-0.806-0.256l-14.75 9.288-6.35-1.988c-1.381-0.431-1.406-1.381 0.288-2.044l24.837-9.569c1.15-0.431 2.156 0.256 1.781 2.013z"/>
            </svg>
          </div>
          <div class="contact-info-card__body">
            <div class="contact-info-card__label">Telegram напрямую</div>
            <a href="https://t.me/adreal777" target="_blank" class="contact-info-card__link">
              @adreal777
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
            </a>
          </div>
        </div>

        <!-- Working hours -->
        <div class="contact-info-card">
          <div class="contact-info-card__icon" style="background:#f0fdf4;">
            <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
            </svg>
          </div>
          <div class="contact-info-card__body">
            <div class="contact-info-card__label">Время работы</div>
            <div class="contact-info-card__value">Пн–Пт: 9:00 – 18:00</div>
            <div class="contact-info-card__sub">Сб–Вс: выходной</div>
          </div>
        </div>

        <!-- Promise block -->
        <div class="contact-promise">
          <div class="contact-promise__title">Наши обязательства</div>
          <div class="contact-promise__row">
            <div class="contact-promise__check contact-promise__check--blue">
              <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
            </div>
            <span>Читаем каждое сообщение</span>
          </div>
          <div class="contact-promise__row">
            <div class="contact-promise__check contact-promise__check--green">
              <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
            </div>
            <span>Отвечаем в течение 1 рабочего дня</span>
          </div>
          <div class="contact-promise__row">
            <div class="contact-promise__check contact-promise__check--purple">
              <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
            </div>
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
const isDragging = ref(false)
const attachedFiles = ref([])
const fileError = ref('')
const fileInput = ref(null)

const chips = ['Новый источник данных', 'Улучшить отчёты', 'Баг / ошибка', 'Интеграция', 'Другое']

const MAX_FILES = 5
const MAX_SIZE = 5 * 1024 * 1024

const formatSize = (bytes) => {
  if (bytes < 1024) return bytes + ' Б'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(0) + ' КБ'
  return (bytes / (1024 * 1024)).toFixed(1) + ' МБ'
}

const addFiles = (newFiles) => {
  fileError.value = ''
  for (const f of newFiles) {
    if (attachedFiles.value.length >= MAX_FILES) {
      fileError.value = `Максимум ${MAX_FILES} файлов`
      break
    }
    if (f.size > MAX_SIZE) {
      fileError.value = `Файл «${f.name}» превышает 5 МБ`
      continue
    }
    if (!attachedFiles.value.find(x => x.name === f.name && x.size === f.size)) {
      attachedFiles.value.push(f)
    }
  }
}

const triggerFileInput = () => fileInput.value?.click()

const handleFileChange = (e) => {
  addFiles(Array.from(e.target.files || []))
  e.target.value = ''
}

const handleDrop = (e) => {
  isDragging.value = false
  addFiles(Array.from(e.dataTransfer?.files || []))
}

const removeFile = (idx) => {
  attachedFiles.value.splice(idx, 1)
  fileError.value = ''
}

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
    const fd = new FormData()
    fd.append('subject', form.value.subject.trim())
    fd.append('message', form.value.message.trim())
    fd.append('email', email)
    attachedFiles.value.forEach(f => fd.append('files', f))

    await api.post('support/idea', fd)
    successMsg.value = 'Спасибо! Идея отправлена команде. Мы свяжемся с вами при необходимости.'
    form.value = { subject: '', message: '', email: '' }
    attachedFiles.value = []
    fileError.value = ''
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
  max-width: 72rem;
}

/* ===== Hero ===== */
.contact-hero {
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, #1e40af 0%, #2563eb 50%, #3b82f6 100%);
  border-radius: 1.25rem;
  padding: 1.5rem 2.5rem;
  margin-bottom: 1.6667rem;
  box-shadow: 0 4px 20px rgba(37, 99, 235, 0.28);
}

.contact-hero__bg { position: absolute; inset: 0; pointer-events: none; }

.contact-hero__blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(48px);
  opacity: 0.2;
}

.contact-hero__blob--1 { width: 20rem; height: 20rem; background: #93c5fd; top: -8rem; right: 4rem; }
.contact-hero__blob--2 { width: 12rem; height: 12rem; background: #818cf8; bottom: -5rem; left: 8rem; }

.contact-hero__inner {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 1.25rem;
  flex-wrap: wrap;
}

.contact-hero__icon-wrap {
  flex-shrink: 0;
  width: 3.5rem;
  height: 3.5rem;
  border-radius: 0.9rem;
  background: rgba(255, 255, 255, 0.18);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  backdrop-filter: blur(6px);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.contact-hero__text { flex: 1; min-width: 0; }

.contact-hero__title {
  font-size: 1.625rem;
  font-weight: 700;
  color: #fff;
  line-height: 1.15;
  margin: 0 0 0.3rem;
  letter-spacing: -0.025em;
}

.contact-hero__sub {
  font-size: 0.9167rem;
  color: rgba(255, 255, 255, 0.75);
  margin: 0;
}

.contact-hero__badges {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  flex-shrink: 0;
}

.contact-hero__badge {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.375rem 0.875rem;
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 6.25rem;
  font-size: 0.8rem;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(4px);
  white-space: nowrap;
}

.contact-hero__badge-dot {
  width: 0.375rem;
  height: 0.375rem;
  border-radius: 50%;
  background: #60a5fa;
  flex-shrink: 0;
}

.contact-hero__badge-dot--green { background: #86efac; }

@media (max-width: 860px) {
  .contact-hero__badges { display: none; }
}

/* ===== Grid ===== */
.contact-grid {
  display: grid;
  grid-template-columns: 1fr 23rem;
  gap: 1.5rem;
  align-items: start;
}

@media (max-width: 900px) {
  .contact-grid { grid-template-columns: 1fr; }
}

/* ===== Form card ===== */
.contact-card {
  background: #fff;
  border-radius: 1.0417rem;
  padding: 2rem 2.5rem;
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.07);
}

.contact-card__header {
  margin-bottom: 1.5rem;
  padding-bottom: 1.1111rem;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}

.contact-card__title {
  font-size: 1.125rem;
  font-weight: 700;
  color: #171717;
  margin: 0 0 0.3rem;
}

.contact-card__desc {
  font-size: 0.875rem;
  color: rgba(105, 105, 105, 0.68);
  margin: 0;
}

.contact-field { margin-bottom: 1.1667rem; }

.contact-label {
  display: block;
  font-size: 0.8333rem;
  font-weight: 600;
  color: #515151;
  margin-bottom: 0.4444rem;
}

.contact-label__hint {
  font-weight: 400;
  color: rgba(105, 105, 105, 0.58);
  margin-left: 0.25rem;
}

.contact-input {
  width: 100%;
  padding: 0.75rem 1rem;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 0.6944rem;
  font-size: 0.9167rem;
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

.contact-textarea { resize: vertical; min-height: 10rem; line-height: 1.6; }

/* Dropzone */
.contact-dropzone {
  border: 1.5px dashed rgba(0, 0, 0, 0.14);
  border-radius: 0.6944rem;
  padding: 1.1111rem;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.6rem;
  cursor: pointer;
  background: #f8f9fb;
  transition: border-color 0.2s, background 0.2s;
  user-select: none;
}

.contact-dropzone:hover,
.contact-dropzone--over {
  border-color: #2563eb;
  background: #eff6ff;
}

.contact-dropzone__input {
  display: none;
}

.contact-dropzone__icon {
  color: rgba(105, 105, 105, 0.5);
  flex-shrink: 0;
}

.contact-dropzone--over .contact-dropzone__icon,
.contact-dropzone:hover .contact-dropzone__icon {
  color: #2563eb;
}

.contact-dropzone__text {
  font-size: 0.8611rem;
  color: rgba(105, 105, 105, 0.7);
}

.contact-dropzone__link {
  color: #2563eb;
  font-weight: 600;
  text-decoration: underline;
  text-underline-offset: 2px;
}

/* Files list */
.contact-files {
  display: flex;
  flex-direction: column;
  gap: 0.3333rem;
  margin-top: 0.5556rem;
}

.contact-file {
  display: flex;
  align-items: center;
  gap: 0.4444rem;
  padding: 0.4167rem 0.6944rem;
  background: #f0f4ff;
  border-radius: 0.5rem;
  border: 1px solid rgba(37, 99, 235, 0.12);
}

.contact-file__icon { color: #2563eb; flex-shrink: 0; }

.contact-file__name {
  font-size: 0.8rem;
  font-weight: 500;
  color: #171717;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.contact-file__size {
  font-size: 0.75rem;
  color: rgba(105, 105, 105, 0.6);
  flex-shrink: 0;
}

.contact-file__remove {
  flex-shrink: 0;
  width: 1.25rem;
  height: 1.25rem;
  border-radius: 50%;
  border: none;
  background: rgba(0, 0, 0, 0.08);
  color: rgba(105, 105, 105, 0.7);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s, color 0.15s;
}

.contact-file__remove:hover { background: #fecaca; color: #dc2626; }

.contact-file-error {
  margin-top: 0.3333rem;
  font-size: 0.7917rem;
  color: #dc2626;
  font-weight: 500;
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
  color: rgba(105, 105, 105, 0.52);
  font-weight: 500;
  flex-shrink: 0;
}

.contact-chip {
  padding: 0.3333rem 0.7778rem;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 6.25rem;
  font-size: 0.8rem;
  font-weight: 500;
  color: #515151;
  background: #f5f7f9;
  cursor: pointer;
  transition: all 0.18s;
  white-space: nowrap;
  font-family: inherit;
}

.contact-chip:hover { border-color: #2563eb; color: #2563eb; background: #eff6ff; }
.contact-chip--active { border-color: #2563eb; color: #2563eb; background: #eff6ff; }

/* Alerts */
.contact-alert {
  display: flex;
  align-items: flex-start;
  gap: 0.5556rem;
  padding: 0.8333rem 1rem;
  border-radius: 0.6944rem;
  font-size: 0.875rem;
  font-weight: 500;
  line-height: 1.5;
  margin-bottom: 1rem;
}

.contact-alert--success { background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }
.contact-alert--error { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }

/* Submit */
.contact-submit {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.8333rem 1.5rem;
  border: none;
  border-radius: 0.8333rem;
  background: linear-gradient(270deg, #ff8a2a 0%, #ff6a3d 48%, #f25b2a 100%);
  color: #fff;
  font-size: 0.9722rem;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s, transform 0.15s, box-shadow 0.2s;
  box-shadow: 0 4px 14px rgba(242, 91, 42, 0.3);
  font-family: inherit;
}

.contact-submit:hover:not(:disabled) { opacity: 0.92; transform: translateY(-1px); box-shadow: 0 6px 18px rgba(242, 91, 42, 0.38); }
.contact-submit:active:not(:disabled) { transform: translateY(0); }
.contact-submit:disabled { opacity: 0.6; cursor: not-allowed; }

.contact-submit__spin { animation: spin 0.9s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* ===== Aside ===== */
.contact-aside { display: flex; flex-direction: column; gap: 0.6944rem; }

/* Info cards */
.contact-info-card {
  background: #fff;
  border-radius: 1.0417rem;
  padding: 1rem 1.25rem;
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.07);
  display: flex;
  align-items: center;
  gap: 0.8333rem;
}

.contact-info-card__icon {
  flex-shrink: 0;
  width: 2.6667rem;
  height: 2.6667rem;
  border-radius: 0.6944rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.contact-info-card__body { flex: 1; min-width: 0; }

.contact-info-card__label {
  font-size: 0.6944rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: rgba(105, 105, 105, 0.52);
  margin-bottom: 0.1667rem;
}

/* Links in info cards — dark by default, blue only on hover */
.contact-info-card__link {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.9028rem;
  font-weight: 600;
  color: #1a1a2a;
  text-decoration: none;
  transition: color 0.15s;
}

.contact-info-card__link:hover { color: #2563eb; }
.contact-info-card__link svg { opacity: 0.35; transition: opacity 0.15s; flex-shrink: 0; }
.contact-info-card__link:hover svg { opacity: 0.8; }

.contact-info-card__value { font-size: 0.9028rem; font-weight: 600; color: #1a1a2a; }
.contact-info-card__sub { font-size: 0.7917rem; color: rgba(105, 105, 105, 0.52); margin-top: 0.0833rem; }

/* Promise block */
.contact-promise {
  background: #fff;
  border-radius: 1.0417rem;
  padding: 1.1111rem 1.25rem;
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.07);
  display: flex;
  flex-direction: column;
  gap: 0.6111rem;
}

.contact-promise__title {
  font-size: 0.6944rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: rgba(105, 105, 105, 0.52);
  margin-bottom: 0.1111rem;
}

.contact-promise__row {
  display: flex;
  align-items: center;
  gap: 0.6111rem;
  font-size: 0.8611rem;
  color: #515151;
  font-weight: 500;
}

.contact-promise__check {
  width: 1.1667rem;
  height: 1.1667rem;
  border-radius: 50%;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.contact-promise__check--blue   { background: #2563eb; }
.contact-promise__check--green  { background: #16a34a; }
.contact-promise__check--purple { background: #7c3aed; }

/* ===== Dark mode ===== */
:global(.dark) .contact-card,
:global(.darkmode) .contact-card,
:global(.dark) .contact-info-card,
:global(.darkmode) .contact-info-card,
:global(.dark) .contact-promise,
:global(.darkmode) .contact-promise {
  background: #2C2F3D;
  box-shadow: 0 4px 24px rgba(0,0,0,0.28), inset 0 1px 0 rgba(255,255,255,0.06);
}

:global(.dark) .contact-card__header,
:global(.darkmode) .contact-card__header { border-bottom-color: rgba(255,255,255,0.08); }

:global(.dark) .contact-card__title,
:global(.darkmode) .contact-card__title { color: rgba(255,255,255,0.92); }

:global(.dark) .contact-card__desc,
:global(.darkmode) .contact-card__desc { color: rgba(255,255,255,0.4); }

:global(.dark) .contact-label,
:global(.darkmode) .contact-label { color: rgba(255,255,255,0.82); }

:global(.dark) .contact-label__hint,
:global(.darkmode) .contact-label__hint { color: rgba(255,255,255,0.36); }

:global(.dark) .contact-input,
:global(.darkmode) .contact-input {
  background: rgba(255,255,255,0.07);
  border-color: rgba(255,255,255,0.12);
  color: #fff;
}

:global(.dark) .contact-input::placeholder,
:global(.darkmode) .contact-input::placeholder { color: rgba(255,255,255,0.3); }

:global(.dark) .contact-input:focus,
:global(.darkmode) .contact-input:focus {
  background: rgba(255,255,255,0.10);
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59,130,246,0.15);
}

:global(.dark) .contact-dropzone,
:global(.darkmode) .contact-dropzone {
  background: rgba(255,255,255,0.05);
  border-color: rgba(255,255,255,0.14);
}

:global(.dark) .contact-dropzone:hover,
:global(.darkmode) .contact-dropzone:hover,
:global(.dark) .contact-dropzone--over,
:global(.darkmode) .contact-dropzone--over {
  border-color: #3b82f6;
  background: rgba(59,130,246,0.1);
}

:global(.dark) .contact-dropzone__text,
:global(.darkmode) .contact-dropzone__text { color: rgba(255,255,255,0.45); }

:global(.dark) .contact-file,
:global(.darkmode) .contact-file {
  background: rgba(59,130,246,0.1);
  border-color: rgba(59,130,246,0.2);
}

:global(.dark) .contact-file__name,
:global(.darkmode) .contact-file__name { color: rgba(255,255,255,0.88); }

:global(.dark) .contact-file__size,
:global(.darkmode) .contact-file__size { color: rgba(255,255,255,0.38); }

:global(.dark) .contact-chip,
:global(.darkmode) .contact-chip {
  background: rgba(255,255,255,0.07);
  border-color: rgba(255,255,255,0.12);
  color: rgba(255,255,255,0.6);
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
:global(.darkmode) .contact-chips__label { color: rgba(255,255,255,0.3); }

:global(.dark) .contact-info-card__label,
:global(.darkmode) .contact-info-card__label { color: rgba(255,255,255,0.38); }

:global(.dark) .contact-info-card__link,
:global(.darkmode) .contact-info-card__link { color: rgba(255,255,255,0.88); }

:global(.dark) .contact-info-card__link:hover,
:global(.darkmode) .contact-info-card__link:hover { color: #60a5fa; }

:global(.dark) .contact-info-card__value,
:global(.darkmode) .contact-info-card__value { color: rgba(255,255,255,0.88); }

:global(.dark) .contact-info-card__sub,
:global(.darkmode) .contact-info-card__sub { color: rgba(255,255,255,0.38); }

:global(.dark) .contact-promise__title,
:global(.darkmode) .contact-promise__title { color: rgba(255,255,255,0.36); }

:global(.dark) .contact-promise__row,
:global(.darkmode) .contact-promise__row { color: rgba(255,255,255,0.72); }

:global(.dark) .contact-alert--success,
:global(.darkmode) .contact-alert--success {
  background: rgba(34,197,94,0.12); color: #86efac; border-color: rgba(34,197,94,0.25);
}

:global(.dark) .contact-alert--error,
:global(.darkmode) .contact-alert--error {
  background: rgba(248,113,113,0.12); color: #fca5a5; border-color: rgba(248,113,113,0.25);
}

:global(.dark) .contact-info-card__icon[style*='background:#eff6ff'],
:global(.darkmode) .contact-info-card__icon[style*='background:#eff6ff'] {
  background: rgba(59,130,246,0.15) !important;
}

:global(.dark) .contact-info-card__icon[style*='background:#f0fdf4'],
:global(.darkmode) .contact-info-card__icon[style*='background:#f0fdf4'] {
  background: rgba(22,163,74,0.15) !important;
}
</style>
