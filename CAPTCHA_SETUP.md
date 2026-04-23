# 🛡️ НАСТРОЙКА CAPTCHA ДЛЯ ЗАЩИТЫ ОТ БОТОВ

## ✅ Поддерживаемые провайдеры (по приоритету)

### 1. **Cloudflare Turnstile** ⭐ (Рекомендуется)
- ✅ **Бесплатно** без ограничений
- ✅ **Быстрее** чем reCAPTCHA
- ✅ **Меньше раздражает** пользователей
- ✅ **Privacy-friendly** - не отслеживает пользователей
- 📚 Документация: https://developers.cloudflare.com/turnstile/

### 2. **Google reCAPTCHA v2/v3**
- ⚠️ Бесплатно до 1M запросов/месяц
- ⚠️ Может раздражать пользователей (особенно v2)
- ⚠️ Отслеживает пользователей (проблемы с GDPR)
- 📚 Документация: https://developers.google.com/recaptcha/

### 3. **Yandex SmartCaptcha**
- ⚠️ Только для российских сайтов
- ⚠️ Требует Yandex Cloud аккаунт
- 📚 Документация: https://cloud.yandex.ru/docs/smartcaptcha/

---

## 🚀 БЫСТРЫЙ СТАРТ: Cloudflare Turnstile

### Шаг 1: Получите ключи

1. Зарегистрируйтесь на https://dash.cloudflare.com/
2. Перейдите в **Turnstile** в боковом меню
3. Нажмите **"Add site"**
4. Укажите ваш домен
5. Выберите **"Managed"** (рекомендуется) или **"Non-interactive"**
6. Получите:
   - **Site Key** (для фронтенда)
   - **Secret Key** (для бэкенда)

### Шаг 2: Добавьте ключи в `.env`

```bash
# Cloudflare Turnstile
TURNSTILE_SITE_KEY=0x4AAAAAACZQbyeTmZnHHbSJ
TURNSTILE_SECRET_KEY=0x4AAAAAACZQb9TyMAfz60t0CgdBml1MF-8
```

### Шаг 3: Добавьте виджет на фронтенд

#### HTML:

```html
<!-- В <head> -->
<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" defer></script>

<!-- В форме -->
<form id="leadForm">
  <input type="text" name="name" required>
  <input type="tel" name="phone" required>
  
  <!-- Turnstile виджет -->
  <div 
    class="cf-turnstile"
    data-sitekey="1x00000000000000000000AA"
    data-callback="onTurnstileSuccess"
  ></div>
  
  <button type="submit">Отправить</button>
</form>

<script>
let turnstileToken = null;

function onTurnstileSuccess(token) {
  turnstileToken = token;
  console.log('✅ Turnstile OK');
}

document.getElementById('leadForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  
  if (!turnstileToken) {
    alert('Пожалуйста, пройдите проверку');
    return;
  }
  
  const formData = {
    name: e.target.name.value,
    phone: e.target.phone.value,
    captcha_token: turnstileToken  // ← ВАЖНО!
  };
  
  const response = await fetch('https://your-domain.com/api/lead/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(formData)
  });
  
  const result = await response.json();
  
  if (result.is_valid) {
    alert('✅ Заявка принята!');
    e.target.reset();
    turnstileToken = null;
  } else {
    alert('❌ Ошибка: ' + result.rejection_reason);
    turnstileToken = null;
  }
});
</script>
```

#### Vue.js:

```vue
<template>
  <form @submit.prevent="handleSubmit">
    <input v-model="name" type="text" required>
    <input v-model="phone" type="tel" required>
    
    <div 
      ref="turnstileWidget"
      class="cf-turnstile"
      data-sitekey="1x00000000000000000000AA"
      data-callback="onTurnstileSuccess"
    ></div>
    
    <button type="submit" :disabled="!turnstileToken">
      Отправить
    </button>
  </form>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const name = ref('')
const phone = ref('')
const turnstileToken = ref(null)

// Загрузка скрипта Turnstile
onMounted(() => {
  const script = document.createElement('script')
  script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js'
  script.defer = true
  document.head.appendChild(script)
  
  // Глобальный коллбэк
  window.onTurnstileSuccess = (token) => {
    turnstileToken.value = token
  }
})

const handleSubmit = async () => {
  const response = await fetch('/api/lead/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: name.value,
      phone: phone.value,
      captcha_token: turnstileToken.value
    })
  })
  
  const result = await response.json()
  
  if (result.is_valid) {
    alert('✅ Заявка принята!')
    name.value = ''
    phone.value = ''
    turnstileToken.value = null
  }
}
</script>
```

---

## 🔧 АЛЬТЕРНАТИВА: Google reCAPTCHA v3

### Шаг 1: Получите ключи

1. Зайдите на https://www.google.com/recaptcha/admin/create
2. Выберите **reCAPTCHA v3**
3. Укажите домены
4. Получите:
   - **Site Key** (для фронтенда)
   - **Secret Key** (для бэкенда)

### Шаг 2: `.env`

```bash
# Google reCAPTCHA v3
RECAPTCHA_SITE_KEY=6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI
RECAPTCHA_SECRET_KEY=6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe
RECAPTCHA_MIN_SCORE=0.5  # Минимальный score (0.0-1.0)
```

### Шаг 3: Фронтенд

```html
<script src="https://www.google.com/recaptcha/api.js?render=6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI"></script>

<script>
document.getElementById('leadForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  
  // Получаем токен от reCAPTCHA
  const token = await grecaptcha.execute('6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI', {
    action: 'submit'
  });
  
  const formData = {
    name: e.target.name.value,
    phone: e.target.phone.value,
    captcha_token: token
  };
  
  // Отправка...
});
</script>
```

---

## 📊 Сравнение провайдеров

| Критерий | Turnstile | reCAPTCHA v3 | reCAPTCHA v2 | SmartCaptcha |
|----------|-----------|--------------|--------------|--------------|
| **Цена** | ✅ Бесплатно | ⚠️ До 1M/мес | ⚠️ До 1M/мес | ⚠️ Яндекс Cloud |
| **UX** | ✅ Отлично | ✅ Невидимый | ❌ Раздражает | ✅ Хорошо |
| **Privacy** | ✅ Да | ❌ Нет | ❌ Нет | ⚠️ Средне |
| **Скорость** | ✅ Быстро | ⚠️ Средне | ❌ Медленно | ✅ Быстро |
| **Интеграция** | ✅ Простая | ⚠️ Средняя | ✅ Простая | ⚠️ Сложная |
| **Рекомендация** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |

---

## 🎯 Автоматический выбор провайдера

Бэкенд автоматически определяет, какой провайдер использовать:

1. Если установлен `TURNSTILE_SECRET_KEY` → используется **Turnstile**
2. Иначе, если установлен `RECAPTCHA_SECRET_KEY` → используется **reCAPTCHA**
3. Иначе, если установлен `SMARTCAPTCHA_SERVER_KEY` → используется **SmartCaptcha**
4. Иначе → капча отключена (если `FAIL_OPEN_MODE=true`)

---

## 🧪 Тестовые ключи

### Cloudflare Turnstile (всегда проходит):
```
Site Key: 1x00000000000000000000AA
Secret Key: 1x0000000000000000000000000000000AA
```

### Google reCAPTCHA (всегда проходит):
```
Site Key: 6LeIxAcTAAAAAJcZVRqyHh71UMIEGNQ_MXjiZKhI
Secret Key: 6LeIxAcTAAAAAGG-vFI1TnRWxMZNFuojJ4WifJWe
```

---

## ⚙️ Дополнительные настройки

### `.env` параметры:

```bash
# Режим fail-open (пропускать при недоступности API)
FAIL_OPEN_MODE=true

# Минимальный score для reCAPTCHA v3 (0.0-1.0)
# 0.0 = определённо бот, 1.0 = определённо человек
# Рекомендуется: 0.5
RECAPTCHA_MIN_SCORE=0.5
```

---

## 🔍 Логирование

Бэкенд логирует все проверки капчи:

```
[INFO] Using Cloudflare Turnstile
[DEBUG] Turnstile response: {"success": true, "challenge_ts": "..."}
[INFO] Turnstile validation passed
```

При ошибках:

```
[WARNING] Turnstile validation failed: timeout-or-duplicate
[ERROR] Turnstile API timeout
```

---

## 📝 Поддерживаемые поля токена

Фронтенд может отправлять токен в одном из полей:

- `captcha_token` (рекомендуется)
- `turnstile_token`
- `recaptcha_token`
- `smart_token`

Бэкенд автоматически проверит все поля.

---

**Готово! Теперь система поддерживает все популярные CAPTCHA провайдеры согласно ТЗ.** 🎉
