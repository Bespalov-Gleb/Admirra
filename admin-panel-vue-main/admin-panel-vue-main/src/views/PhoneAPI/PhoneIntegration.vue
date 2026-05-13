<template>
  <div class="space-y-6 overflow-x-hidden w-full">
    <!-- Header -->
    <div class="py-5 px-6 sm:px-8 bg-white/60 backdrop-blur-xl rounded-[2.2222rem] border border-white/80 shadow-sm">
      <label class="text-[0.625rem] font-black text-gray-400 uppercase tracking-widest ml-1 opacity-70">
        Интеграция
      </label>
      <div class="flex items-center gap-3 mt-0.5">
        <div class="p-2 bg-purple-600 rounded-xl shadow-lg shadow-purple-200 hidden xs:block">
          <CodeBracketIcon class="w-4 h-4 text-white" />
        </div>
        <div class="flex flex-col min-w-0">
          <h1 class="text-xl sm:text-2xl font-black text-gray-900 tracking-tight truncate">
            Интеграция квалификатора
          </h1>
          <div class="flex items-center gap-1.5 mt-0.5">
            <div class="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse flex-shrink-0"></div>
            <p class="text-[0.625rem] font-bold text-gray-400 uppercase tracking-wider truncate">
              Подключите проверку лидов на ваш сайт
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="grid grid-cols-1 xl:grid-cols-3 gap-6">
      <!-- Left Column: Project Selection & Settings -->
      <div class="xl:col-span-1 space-y-6">
        <!-- Project Selection -->
        <div class="bg-white rounded-[2.2222rem] p-6 shadow-sm border border-gray-100">
          <h2 class="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
            <FolderIcon class="w-5 h-5 text-gray-600" />
            Выберите проект
          </h2>
          
          <select
            v-model="selectedProjectId"
            @change="loadProjectDetails"
            class="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition"
          >
            <option value="">Выберите проект...</option>
            <option v-for="project in projects" :key="project.id" :value="project.id">
              {{ project.name }}
            </option>
          </select>
          
          <p class="text-xs text-gray-500 mt-2">
            Выберите проект для получения кода интеграции
          </p>
        </div>

        <!-- Project Settings -->
        <div v-if="selectedProject" class="bg-white rounded-[2.2222rem] p-6 shadow-sm border border-gray-100">
          <h2 class="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
            <Cog6ToothIcon class="w-5 h-5 text-gray-600" />
            Настройки проекта
          </h2>
          
          <div class="space-y-4">
            <!-- Webhook URL -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">
                Webhook URL для CRM
              </label>
              <input
                v-model="settings.crm_webhook_url"
                type="url"
                placeholder="https://your-crm.com/webhook"
                class="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent text-sm"
              >
              <p class="text-xs text-gray-500 mt-1">
                Валидные лиды будут отправляться на этот URL
              </p>
            </div>

            <!-- CAPTCHA Settings -->
            <div class="border-t pt-4">
              <h3 class="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <ShieldCheckIcon class="w-4 h-4 text-purple-600" />
                Настройки CAPTCHA
              </h3>
              
              <!-- Provider Selection -->
              <div class="mb-3">
                <label class="block text-sm font-medium text-gray-700 mb-2">
                  Провайдер CAPTCHA
                </label>
                <select
                  v-model="settings.captcha_provider"
                  class="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-purple-500 text-sm"
                >
                  <option value="none">Без CAPTCHA</option>
                  <option value="turnstile">Cloudflare Turnstile (рекомендуется)</option>
                  <option value="recaptcha">Google reCAPTCHA</option>
                  <option value="smartcaptcha">Yandex SmartCaptcha</option>
                </select>
              </div>

              <!-- CAPTCHA Keys (only if provider is not 'none') -->
              <template v-if="settings.captcha_provider !== 'none'">
                <div class="mb-3">
                  <label class="block text-sm font-medium text-gray-700 mb-2">
                    Site Key (публичный)
                  </label>
                  <input
                    v-model="settings.captcha_site_key"
                    type="text"
                    placeholder="0x4AAA..."
                    class="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-purple-500 text-sm font-mono"
                  >
                  <p class="text-xs text-gray-500 mt-1">
                    Будет показан в коде интеграции
                  </p>
                </div>

                <div class="mb-3">
                  <label class="block text-sm font-medium text-gray-700 mb-2">
                    Secret Key (секретный)
                  </label>
                  <input
                    v-model="settings.captcha_secret_key"
                    type="password"
                    placeholder="0x4AAA..."
                    class="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-purple-500 text-sm font-mono"
                  >
                  <p class="text-xs text-gray-500 mt-1">
                    Хранится на сервере, не показывается клиенту
                  </p>
                </div>

                <div class="bg-blue-50 border border-blue-200 rounded-lg p-3">
                  <p class="text-xs text-blue-800">
                    💡 <strong>Как получить ключи:</strong><br>
                    <template v-if="settings.captcha_provider === 'turnstile'">
                      1. Зайдите на <a href="https://dash.cloudflare.com/" target="_blank" class="underline">Cloudflare Dashboard</a><br>
                      2. Turnstile → Create Widget<br>
                      3. Добавьте ваш домен<br>
                      4. Скопируйте Site Key и Secret Key
                    </template>
                    <template v-else-if="settings.captcha_provider === 'recaptcha'">
                      1. Зайдите на <a href="https://www.google.com/recaptcha/admin" target="_blank" class="underline">Google reCAPTCHA</a><br>
                      2. Зарегистрируйте новый сайт<br>
                      3. Выберите reCAPTCHA v2 (галочка)<br>
                      4. Скопируйте ключи
                    </template>
                    <template v-else-if="settings.captcha_provider === 'smartcaptcha'">
                      1. Зайдите в <a href="https://console.cloud.yandex.ru/folders" target="_blank" class="underline">Yandex Cloud</a><br>
                      2. SmartCaptcha → Создать капчу<br>
                      3. Укажите домены<br>
                      4. Скопируйте ключи
                    </template>
                  </p>
                </div>
              </template>
            </div>

            <!-- Validation Options -->
            <div class="space-y-2">
              <label class="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" v-model="settings.enable_social_check" class="rounded text-purple-600">
                <span class="text-sm text-gray-700">Проверка в соцсетях</span>
              </label>
              <label class="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" v-model="settings.enable_lead_scoring" class="rounded text-purple-600">
                <span class="text-sm text-gray-700">Скоринг лида (0–100)</span>
              </label>
              <label class="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" v-model="settings.enable_spam_check" class="rounded text-purple-600">
                <span class="text-sm text-gray-700">Проверка спам-баз</span>
              </label>
              <label class="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" v-model="settings.enable_bitrix_check" class="rounded text-purple-600">
                <span class="text-sm text-gray-700">Проверка дубликатов в Bitrix24</span>
              </label>
            </div>

            <!-- Save Button -->
            <button
              @click="saveSettings"
              :disabled="savingSettings"
              class="w-full bg-purple-600 text-white py-2 px-4 rounded-lg hover:bg-purple-700 transition disabled:opacity-50 text-sm font-medium"
            >
              {{ savingSettings ? 'Сохранение...' : 'Сохранить настройки' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Right Column: Integration Code & Instructions -->
      <div class="xl:col-span-2 space-y-6">
        <div v-if="!selectedProject" class="bg-gradient-to-br from-purple-50 to-blue-50 rounded-[2.2222rem] p-12 text-center border border-purple-100">
          <div class="w-16 h-16 bg-purple-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <ArrowLeftIcon class="w-8 h-8 text-purple-600" />
          </div>
          <h3 class="text-xl font-bold text-gray-900 mb-2">Выберите проект</h3>
          <p class="text-gray-600">
            Выберите проект слева, чтобы получить код для интеграции
          </p>
        </div>

        <template v-else>
          <!-- Platform Selection Tabs -->
          <div class="bg-white rounded-[2.2222rem] p-6 shadow-sm border border-gray-100">
            <h2 class="text-lg font-bold text-gray-900 mb-4">Выберите платформу</h2>
            
            <div class="flex flex-wrap gap-2">
              <button
                v-for="platform in platforms"
                :key="platform.id"
                @click="selectedPlatform = platform.id"
                :class="[
                  'px-4 py-2 rounded-lg font-medium text-sm transition',
                  selectedPlatform === platform.id
                    ? 'bg-purple-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                ]"
              >
                {{ platform.name }}
              </button>
            </div>
          </div>

          <!-- Integration Code -->
          <div class="bg-white rounded-[2.2222rem] p-6 shadow-sm border border-gray-100">
            <div class="flex items-center justify-between mb-4">
              <h2 class="text-lg font-bold text-gray-900">Код интеграции</h2>
              <button
                @click="copyCode"
                class="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm font-medium transition flex items-center gap-2"
              >
                <ClipboardDocumentIcon class="w-4 h-4" />
                {{ copied ? 'Скопировано!' : 'Копировать' }}
              </button>
            </div>

            <div class="relative">
              <pre class="bg-gray-900 text-gray-100 p-4 rounded-xl overflow-x-auto text-xs leading-relaxed"><code>{{ generatedCode }}</code></pre>
            </div>
          </div>

          <!-- Instructions -->
          <div class="bg-white rounded-[2.2222rem] p-6 shadow-sm border border-gray-100">
            <h2 class="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
              <DocumentTextIcon class="w-5 h-5 text-gray-600" />
              Инструкция по установке
            </h2>
            
            <div class="prose prose-sm max-w-none">
              <!-- HTML Instructions -->
              <div v-if="selectedPlatform === 'html'" class="space-y-3">
                <h4 class="font-bold text-gray-900">Шаги установки:</h4>
                <ol class="list-decimal list-inside space-y-2 text-sm text-gray-700">
                  <li>Скопируйте код выше</li>
                  <li>Вставьте его на вашу страницу</li>
                  <li>Настройте стили формы под ваш дизайн</li>
                  <li>Проверьте работу, отправив тестовую заявку</li>
                </ol>
                <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-sm">
                  <p class="text-yellow-800">
                    ⚠️ <strong>Важно:</strong> Убедитесь, что домен вашего сайта добавлен в настройки Turnstile.
                  </p>
                </div>
              </div>

              <!-- Tilda Instructions -->
              <div v-else-if="selectedPlatform === 'tilda'" class="space-y-3">
                <h4 class="font-bold text-gray-900">Шаги установки в Tilda:</h4>
                <ol class="list-decimal list-inside space-y-2 text-sm text-gray-700">
                  <li>Откройте настройки страницы (Settings)</li>
                  <li>Перейдите в "HTML код для вставки"</li>
                  <li>Вставьте код в секцию "Head"</li>
                  <li>Добавьте HTML-блок с виджетом капчи перед кнопкой</li>
                  <li>Вставьте JavaScript код в секцию "Body"</li>
                  <li>Сохраните и опубликуйте страницу</li>
                </ol>
              </div>

              <!-- WordPress Instructions -->
              <div v-else-if="selectedPlatform === 'wordpress'" class="space-y-3">
                <h4 class="font-bold text-gray-900">Установка в WordPress:</h4>
                <ol class="list-decimal list-inside space-y-2 text-sm text-gray-700">
                  <li>Установите плагин Contact Form 7</li>
                  <li>Добавьте код в functions.php вашей темы</li>
                  <li>Создайте форму с полями из примера</li>
                  <li>Вставьте shortcode формы на страницу</li>
                </ol>
                <div class="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm">
                  <p class="text-blue-800">
                    💡 <strong>Совет:</strong> Используйте дочернюю тему для безопасного редактирования functions.php
                  </p>
                </div>
              </div>

              <!-- Vue Instructions -->
              <div v-else-if="selectedPlatform === 'vue'" class="space-y-3">
                <h4 class="font-bold text-gray-900">Установка в Vue.js:</h4>
                <ol class="list-decimal list-inside space-y-2 text-sm text-gray-700">
                  <li>Скопируйте компонент выше</li>
                  <li>Создайте файл LeadForm.vue в вашем проекте</li>
                  <li>Импортируйте и используйте компонент</li>
                  <li>Настройте стили под ваш дизайн</li>
                </ol>
              </div>
            </div>
          </div>

        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import {
  CodeBracketIcon,
  FolderIcon,
  Cog6ToothIcon,
  ClipboardDocumentIcon,
  DocumentTextIcon,
  ShieldCheckIcon,
  ArrowLeftIcon
} from '@heroicons/vue/24/outline'
import api from '../../api/axios'
import { useToaster } from '../../composables/useToaster'

const toaster = useToaster()

// Projects
const projects = ref([])
const selectedProjectId = ref('')
const selectedProject = ref(null)

// Settings
const settings = ref({
  crm_webhook_url: '',
  enable_social_check: false,
  enable_lead_scoring: false,
  enable_spam_check: false,
  enable_bitrix_check: false,
  captcha_provider: 'none',
  captcha_site_key: '',
  captcha_secret_key: ''
})
const savingSettings = ref(false)

// Platform selection
const selectedPlatform = ref('html')
const platforms = [
  { id: 'html', name: 'HTML' },
  { id: 'tilda', name: 'Tilda' },
  { id: 'wordpress', name: 'WordPress' },
  { id: 'vue', name: 'Vue.js' }
]

// Copy functionality
const copied = ref(false)

// Load projects
const loadProjects = async () => {
  try {
    const response = await api.get('/phone-projects/')
    projects.value = response.data
  } catch (error) {
    console.error('Error loading projects:', error)
    toaster.error('Не удалось загрузить проекты')
  }
}

// Load project details
const loadProjectDetails = async () => {
  if (!selectedProjectId.value) {
    selectedProject.value = null
    return
  }

  try {
    const response = await api.get(`/phone-projects/${selectedProjectId.value}`)
    selectedProject.value = response.data
    
    // Load settings
    settings.value = {
      crm_webhook_url: response.data.crm_webhook_url || '',
      enable_social_check: response.data.enable_social_check || false,
      enable_lead_scoring: response.data.enable_lead_scoring || false,
      enable_spam_check: response.data.enable_spam_check || false,
      enable_bitrix_check: response.data.enable_bitrix_check || false,
      captcha_provider: response.data.captcha_provider || 'none',
      captcha_site_key: response.data.captcha_site_key || '',
      captcha_secret_key: response.data.captcha_secret_key || ''
    }
  } catch (error) {
    console.error('Error loading project:', error)
    toaster.error('Не удалось загрузить данные проекта')
  }
}

// Save settings
const saveSettings = async () => {
  savingSettings.value = true
  try {
    await api.put(`/phone-projects/${selectedProjectId.value}`, settings.value)
    toaster.success('Настройки сохранены')
  } catch (error) {
    console.error('Error saving settings:', error)
    toaster.error('Не удалось сохранить настройки')
  } finally {
    savingSettings.value = false
  }
}

// Generate integration code
const generatedCode = computed(() => {
  if (!selectedProject.value) return ''
  
  const apiUrl = window.location.origin
  const projectKey = selectedProject.value.api_key
  const scriptOpen = '<' + 'script'
  const scriptClose = '<' + '/script>'
  const siteKey = settings.value.captcha_site_key || 'YOUR_SITE_KEY'
  const provider = settings.value.captcha_provider || 'none'
  
  if (selectedPlatform.value === 'html') {
    return `<!DOCTYPE html>
<html>
<head>
    <title>Форма обратной связи</title>
    <!-- Cloudflare Turnstile -->
    ${scriptOpen} src="https://challenges.cloudflare.com/turnstile/v0/api.js" defer>${scriptClose}>
</head>
<body>
    <form id="leadForm">
        <input type="text" name="name" placeholder="Имя" required>
        <input type="tel" name="phone" placeholder="Телефон" required>
        <input type="email" name="email" placeholder="Email">
        
        <!-- Cloudflare Turnstile Widget -->
        <div class="cf-turnstile" 
             data-sitekey="${siteKey}"
             data-callback="onTurnstileSuccess"></div>
        
        <button type="submit">Отправить</button>
    </form>

    ${scriptOpen}>
    let captchaToken = null;
    
    function onTurnstileSuccess(token) {
        captchaToken = token;
    }
    
    document.getElementById('leadForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        if (!captchaToken) {
            alert('Пожалуйста, пройдите проверку');
            return;
        }
        
        const formData = {
            name: e.target.name.value,
            phone: e.target.phone.value,
            email: e.target.email.value,
            captcha_token: captchaToken,
            project_key: '${projectKey}'
        };
        
        try {
            const response = await fetch('${apiUrl}/api/lead/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });
            
            const result = await response.json();
            
            if (result.is_valid) {
                alert('Заявка принята!');
                e.target.reset();
            } else {
                alert('Ошибка: ' + result.rejection_reason);
            }
        } catch (error) {
            alert('Ошибка отправки');
        }
    });
    ${scriptClose}>
</body>
</html>`
  } else if (selectedPlatform.value === 'tilda') {
    return `<!-- В настройках формы Tilda добавьте в "Код для вставки в head": -->
${scriptOpen} src="https://challenges.cloudflare.com/turnstile/v0/api.js" defer>${scriptClose}>

<!-- В настройках формы добавьте HTML-блок ПЕРЕД кнопкой отправки: -->
<div class="cf-turnstile" 
     data-sitekey="${siteKey}"
     data-callback="onTurnstileSuccess"></div>

<!-- В настройки формы добавьте JavaScript (в "Код для вставки перед ${scriptClose}>"): -->
${scriptOpen}>
let captchaToken = null;

function onTurnstileSuccess(token) {
    captchaToken = token;
}

// Перехватываем отправку формы Tilda
$(document).on('tildaform:aftersuccess', function(e, form) {
    if (!captchaToken) return;
    
    // Отправляем данные на ваш API
    fetch('${apiUrl}/api/lead/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            name: form.find('[name="name"]').val(),
            phone: form.find('[name="phone"]').val(),
            email: form.find('[name="email"]').val(),
            captcha_token: captchaToken,
            project_key: '${projectKey}'
        })
    });
});
${scriptClose}>`
  } else if (selectedPlatform.value === 'wordpress') {
    return `<?php
// Добавьте в functions.php вашей темы:

// 1. Подключить Turnstile скрипт
function add_turnstile_script() {
    wp_enqueue_script('turnstile', 'https://challenges.cloudflare.com/turnstile/v0/api.js', array(), null, true);
}
add_action('wp_enqueue_scripts', 'add_turnstile_script');

// 2. Добавьте виджет в форму Contact Form 7:
// [text* your-name placeholder "Имя"]
// [tel* your-phone placeholder "Телефон"]
// [email your-email placeholder "Email"]
// <div class="cf-turnstile" data-sitekey="${siteKey}"></div>
// [submit "Отправить"]

// 3. Обработка отправки (ajax):
add_action('wp_ajax_submit_lead', 'submit_lead_handler');
add_action('wp_ajax_nopriv_submit_lead', 'submit_lead_handler');

function submit_lead_handler() {
    $response = wp_remote_post('${apiUrl}/api/lead/', array(
        'headers' => array('Content-Type' => 'application/json'),
        'body' => json_encode(array(
            'name' => $_POST['name'],
            'phone' => $_POST['phone'],
            'email' => $_POST['email'],
            'captcha_token' => $_POST['captcha_token'],
            'project_key' => '${projectKey}'
        ))
    ));
    
    wp_send_json($response);
}
?>`
  } else if (selectedPlatform.value === 'vue') {
    return `<template>
  <form @submit.prevent="submitLead">
    <input v-model="form.name" placeholder="Имя" required>
    <input v-model="form.phone" type="tel" placeholder="Телефон" required>
    <input v-model="form.email" type="email" placeholder="Email">
    
    <!-- Cloudflare Turnstile -->
    <div 
      class="cf-turnstile" 
      :data-sitekey="turnstileSiteKey"
      data-callback="onTurnstileSuccess"
    ></div>
    
    <button type="submit">Отправить</button>
  </form>
</template>

${scriptOpen} setup>
import { ref, onMounted } from 'vue'

const form = ref({ name: '', phone: '', email: '' })
const turnstileSiteKey = '${siteKey}'
let captchaToken = null

// Подключаем Turnstile скрипт
onMounted(() => {
  const script = document.createElement('script')
  script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js'
  script.defer = true
  document.head.appendChild(script)
  
  // Глобальный callback для Turnstile
  window.onTurnstileSuccess = (token) => {
    captchaToken = token
  }
})

const submitLead = async () => {
  if (!captchaToken) {
    alert('Пожалуйста, пройдите проверку')
    return
  }
  
  try {
    const response = await fetch('${apiUrl}/api/lead/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...form.value,
        captcha_token: captchaToken,
        project_key: '${projectKey}'
      })
    })
    
    const result = await response.json()
    
    if (result.is_valid) {
      alert('Заявка принята!')
      form.value = { name: '', phone: '', email: '' }
    } else {
      alert('Ошибка: ' + result.rejection_reason)
    }
  } catch (error) {
    alert('Ошибка отправки')
  }
}
${scriptClose}>`
  }
  
  return ''
})

// Copy code to clipboard
const copyCode = async () => {
  try {
    await navigator.clipboard.writeText(generatedCode.value)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
    toaster.success('Код скопирован')
  } catch (error) {
    toaster.error('Не удалось скопировать')
  }
}

onMounted(() => {
  loadProjects()
})
</script>

<style scoped>
.prose {
  @apply text-gray-700;
}
.prose h4 {
  @apply text-gray-900 font-bold mb-2;
}
.prose ol {
  @apply space-y-2;
}
.prose li {
  @apply text-sm;
}
</style>
