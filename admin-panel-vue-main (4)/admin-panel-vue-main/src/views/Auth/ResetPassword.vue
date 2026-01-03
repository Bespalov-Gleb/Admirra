<template>
  <div class="min-h-screen flex bg-white">
    <!-- Левая секция - Форма установки нового пароля -->
    <div class="w-full lg:w-5/12 bg-white flex items-center justify-center px-4 sm:px-6 lg:px-12 py-12">
      <div class="w-full max-w-md relative">
        <!-- Логотип AdMirra -->
        <div class="mb-8 text-center">
          <img :src="logoAdMirra" alt="AdMirra" class="h-12 mb-6 mx-auto" />
        </div>

        <!-- Заголовок -->
        <h1 class="text-3xl sm:text-4xl font-bold text-gray-900 mb-8 text-center">Новый пароль</h1>

        <!-- Форма -->
        <form @submit.prevent="handleSubmit" class="space-y-5">
          <!-- Пароль -->
          <div class="relative">
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Пароль
            </label>
            <div class="relative">
              <input
                ref="passwordInput"
                v-model="form.password"
                :type="showPassword ? 'text' : 'password'"
                required
                placeholder="Пароль"
                @focus="showTooltip = true"
                @blur="handlePasswordBlur"
                @input="validatePassword"
                class="w-full px-4 py-3 pr-10 border rounded-lg bg-white text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 transition-colors"
                :class="passwordError ? 'border-red-500 focus:ring-red-500 focus:border-red-500' : 'border-gray-300 focus:ring-blue-500 focus:border-blue-500'"
              />
              <button
                type="button"
                @click="showPassword = !showPassword"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                <EyeIcon v-if="!showPassword" class="w-5 h-5" />
                <EyeSlashIcon v-else class="w-5 h-5" />
              </button>
            </div>
            
            <!-- Tooltip с требованиями -->
            <div
              v-if="showTooltip"
              class="absolute lg:left-full lg:ml-4 lg:top-0 lg:-translate-y-2.5 lg:right-auto lg:bottom-auto right-0 top-full mt-2 lg:mt-0 w-64 bg-blue-900 text-white rounded-lg p-4 shadow-xl z-50"
              @mouseenter="keepTooltipOpen = true"
              @mouseleave="keepTooltipOpen = false"
            >
              <h3 
                class="text-sm font-semibold mb-3"
                :class="isAllRequirementsMet ? 'text-white' : 'text-red-400'"
              >
                {{ isAllRequirementsMet ? 'Ваш пароль подходит' : 'Ваш пароль не подходит' }}
              </h3>
              <ul class="space-y-2 text-sm">
                <li class="flex items-center gap-2">
                  <span :class="hasMinLength ? 'text-green-400' : 'text-gray-400'">✓</span>
                  <span :class="hasMinLength ? 'text-white' : 'text-gray-400'">более 6 символов</span>
                </li>
                <li class="mt-3 text-xs text-blue-300 font-medium">Для большей надежности используйте</li>
                <li class="flex items-center gap-2">
                  <span :class="hasNumbers ? 'text-green-400' : 'text-gray-400'">✓</span>
                  <span :class="hasNumbers ? 'text-green-400' : 'text-gray-400'">цифры</span>
                </li>
                <li class="flex items-center gap-2">
                  <span :class="hasMixedCase ? 'text-green-400' : 'text-gray-400'">✓</span>
                  <span :class="hasMixedCase ? 'text-green-400' : 'text-gray-400'">разный регистр букв</span>
                </li>
              </ul>
            </div>
          </div>

          <!-- Подтверждение пароля -->
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Подтверждение пароля
            </label>
            <div class="relative">
              <input
                v-model="form.confirmPassword"
                :type="showConfirmPassword ? 'text' : 'password'"
                required
                placeholder="Подтверждение пароля"
                @input="validatePassword"
                class="w-full px-4 py-3 pr-10 border rounded-lg bg-white text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 transition-colors"
                :class="confirmPasswordError ? 'border-red-500 focus:ring-red-500 focus:border-red-500' : 'border-gray-300 focus:ring-blue-500 focus:border-blue-500'"
              />
              <button
                type="button"
                @click="showConfirmPassword = !showConfirmPassword"
                class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                <EyeIcon v-if="!showConfirmPassword" class="w-5 h-5" />
                <EyeSlashIcon v-else class="w-5 h-5" />
              </button>
            </div>
            <p v-if="confirmPasswordError" class="mt-2 text-sm text-red-600">{{ confirmPasswordError }}</p>
          </div>

          <button
            type="submit"
            :disabled="isLoading || !isFormValid"
            class="w-full py-3 px-4 rounded-lg font-medium text-base transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            :class="isFormValid ? 'bg-blue-600 text-white hover:bg-blue-700' : 'bg-blue-200 text-blue-400'"
          >
            <span v-if="isLoading">Сброс пароля...</span>
            <span v-else>Сбросить пароль</span>
          </button>

          <div class="text-center">
            <button
              type="button"
              @click="goToLogin"
              class="text-sm text-blue-600 hover:text-blue-700"
            >
              Вернуться к входу
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Правая секция - Промо-контент -->
    <div class="hidden lg:flex lg:w-7/12 bg-gradient-to-br from-blue-50 to-blue-100 relative overflow-hidden mt-[60px] mr-[60px] rounded-tl-[40px] rounded-tr-[40px]">
      <!-- Изображение как фон (уменьшено и позиционировано) -->
      <div class="absolute bottom-0 right-0 z-0 flex items-end justify-end">
        <img :src="loginImage" alt="Illustration" class="h-[600px] w-auto max-w-full object-contain scale-110 object-right-bottom" />
      </div>
      
      <!-- Текст поверх изображения -->
      <div class="w-full h-full flex flex-col justify-start px-12 py-16 relative z-10">
        <!-- Заголовок -->
        <h2 class="text-4xl font-bold text-blue-900 mb-6 leading-tight">
          Анализируйте и <br />
          оптимизируйте <br />
          Ваши рекламные кампании
        </h2>

        <!-- Описание -->
        <p class="text-lg text-blue-800 leading-relaxed max-w-lg">
          Онлайн-сервис для маркетологов, который превращает сырые цифры в понятные, сильные отчёты с глубоким AI-анализом.
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import EyeIcon from '../../assets/icons/eye.vue'
import EyeSlashIcon from '../../assets/icons/eye-slash.vue'
import logoAdMirra from '../../assets/imgs/logo/logo-dark.png'
import loginImage from '../../assets/imgs/logo/login.svg'

const router = useRouter()
const passwordInput = ref(null)
const showPassword = ref(false)
const showConfirmPassword = ref(false)
const showTooltip = ref(false)
const keepTooltipOpen = ref(false)
const isLoading = ref(false)
const passwordError = ref('')
const confirmPasswordError = ref('')

const form = reactive({
  password: '',
  confirmPassword: ''
})

// Проверка требований к паролю
const hasMinLength = computed(() => form.password.length > 6)
const hasNumbers = computed(() => /\d/.test(form.password))
const hasMixedCase = computed(() => {
  const hasLower = /[a-zа-яё]/.test(form.password)
  const hasUpper = /[A-ZА-ЯЁ]/.test(form.password)
  return hasLower && hasUpper
})
const isAllRequirementsMet = computed(() => {
  return hasMinLength.value && hasNumbers.value && hasMixedCase.value
})

const validatePassword = () => {
  passwordError.value = ''
  confirmPasswordError.value = ''

  // Проверка длины пароля
  if (form.password.length > 0 && form.password.length < 6) {
    passwordError.value = 'Пароль должен содержать более 6 символов'
  }

  // Проверка совпадения паролей
  if (form.confirmPassword.length > 0 && form.password !== form.confirmPassword) {
    confirmPasswordError.value = 'Пароли не совпадают'
  }
}

const handlePasswordBlur = () => {
  // Закрываем tooltip с небольшой задержкой, чтобы можно было кликнуть на tooltip
  setTimeout(() => {
    if (!keepTooltipOpen.value && document.activeElement !== passwordInput.value) {
      showTooltip = false
    }
  }, 200)
}

const isFormValid = computed(() => {
  return form.password.length >= 6 && 
         form.password === form.confirmPassword && 
         form.password.length > 0 && 
         form.confirmPassword.length > 0
})

const handleSubmit = async () => {
  passwordError.value = ''
  confirmPasswordError.value = ''
  
  if (!isFormValid.value) {
    if (form.password.length < 6) {
      passwordError.value = 'Пароль должен содержать более 6 символов'
    }
    if (form.password !== form.confirmPassword) {
      confirmPasswordError.value = 'Пароли не совпадают'
    }
    return
  }

  isLoading.value = true

  try {
    // Здесь должна быть логика установки нового пароля
    // В реальном приложении это будет API вызов
    await new Promise(resolve => setTimeout(resolve, 1500)) // Имитация запроса
    
    // Перенаправляем на страницу входа после успешной установки пароля
    router.push('/login')
  } catch (err) {
    passwordError.value = 'Произошла ошибка. Пожалуйста, попробуйте еще раз.'
  } finally {
    isLoading.value = false
  }
}

const goToLogin = () => {
  router.push('/login')
}
</script>

