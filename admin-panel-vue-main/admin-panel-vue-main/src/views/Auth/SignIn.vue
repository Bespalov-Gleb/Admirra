<template>
  <FullScreenLayout>
    <div class="relative p-6 bg-white z-1 sm:p-0">
      <div
        class="relative flex flex-col justify-center w-full h-screen lg:flex-row bg-white"
      >
        <div class="flex flex-col flex-1 w-full lg:w-1/2 bg-white">
          <div class="flex flex-col justify-center flex-1 w-full max-w-lg mx-auto pt-16">
            <div>
              <div class="mb-8 sm:mb-10">
                <h1
                  class="mb-3 font-semibold text-gray-900 text-3xl sm:text-4xl"
                >
                  Вход в систему
                </h1>
                <p class="text-base text-gray-600">
                  Введите свой e-mail и пароль для входа в систему!
                </p>
              </div>
              <div>
                <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-5">
                  <button
                    class="inline-flex items-center justify-center gap-3 py-4 text-base font-normal text-gray-700 transition-colors bg-gray-100 rounded-lg px-8 hover:bg-gray-200 hover:text-gray-800"
                  >
                    Войти с Яндекс ID
                  </button>
                  <button
                    class="inline-flex items-center justify-center gap-3 py-4 text-base font-normal text-gray-700 transition-colors bg-gray-100 rounded-lg px-8 hover:bg-gray-200 hover:text-gray-800"
                  >
                    Войти через Вконтакте
                  </button>
                </div>
                <div class="relative py-4 sm:py-6">
                  <div class="absolute inset-0 flex items-center">
                    <div class="w-full border-t border-gray-200"></div>
                  </div>
                  <div class="relative flex justify-center text-sm">
                    <span class="p-2 text-gray-400 bg-white sm:px-5 sm:py-2"
                      >или</span
                    >
                  </div>
                </div>
                <form @submit.prevent="handleLogin">
                  <div class="space-y-5">
                    <!-- Email -->
                    <div>
                      <label
                        for="email"
                        class="mb-2 block text-sm font-medium text-gray-700"
                      >
                        E-mail<span class="text-red-500">*</span>
                      </label>
                      <input
                        v-model="loginForm.email"
                        type="email"
                        id="email"
                        name="email"
                        placeholder="Введите email"
                        class="h-16 w-full rounded-lg border border-gray-300 bg-white px-5 py-4 text-base text-gray-900 shadow-sm placeholder:text-gray-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                      />
                    </div>
                    <!-- Password -->
                    <div>
                      <label
                        for="password"
                        class="mb-2 block text-sm font-medium text-gray-700"
                      >
                        Пароль<span class="text-red-500">*</span>
                      </label>
                      <div class="relative">
                        <input
                          v-model="loginForm.password"
                          :type="showPassword ? 'text' : 'password'"
                          id="password"
                          placeholder="Введите пароль"
                        class="h-16 w-full rounded-lg border border-gray-300 bg-white py-4 pl-5 pr-12 text-base text-gray-900 shadow-sm placeholder:text-gray-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                        />
                        <span
                          @click="togglePasswordVisibility"
                          class="absolute z-30 text-gray-500 hover:text-gray-700 -translate-y-1/2 cursor-pointer right-4 top-1/2"
                        >
                          <svg
                            v-if="!showPassword"
                            class="fill-current"
                            width="20"
                            height="20"
                            viewBox="0 0 20 20"
                            fill="none"
                            xmlns="http://www.w3.org/2000/svg"
                          >
                            <path
                              fill-rule="evenodd"
                              clip-rule="evenodd"
                              d="M10.0002 13.8619C7.23361 13.8619 4.86803 12.1372 3.92328 9.70241C4.86804 7.26761 7.23361 5.54297 10.0002 5.54297C12.7667 5.54297 15.1323 7.26762 16.0771 9.70243C15.1323 12.1372 12.7667 13.8619 10.0002 13.8619ZM10.0002 4.04297C6.48191 4.04297 3.49489 6.30917 2.4155 9.4593C2.3615 9.61687 2.3615 9.78794 2.41549 9.94552C3.49488 13.0957 6.48191 15.3619 10.0002 15.3619C13.5184 15.3619 16.5055 13.0957 17.5849 9.94555C17.6389 9.78797 17.6389 9.6169 17.5849 9.45932C16.5055 6.30919 13.5184 4.04297 10.0002 4.04297ZM9.99151 7.84413C8.96527 7.84413 8.13333 8.67606 8.13333 9.70231C8.13333 10.7286 8.96527 11.5605 9.99151 11.5605H10.0064C11.0326 11.5605 11.8646 10.7286 11.8646 9.70231C11.8646 8.67606 11.0326 7.84413 10.0064 7.84413H9.99151Z"
                              fill="#98A2B3"
                            />
                          </svg>
                          <svg
                            v-else
                            class="fill-current"
                            width="20"
                            height="20"
                            viewBox="0 0 20 20"
                            fill="none"
                            xmlns="http://www.w3.org/2000/svg"
                          >
                            <path
                              fill-rule="evenodd"
                              clip-rule="evenodd"
                              d="M4.63803 3.57709C4.34513 3.2842 3.87026 3.2842 3.57737 3.57709C3.28447 3.86999 3.28447 4.34486 3.57737 4.63775L4.85323 5.91362C3.74609 6.84199 2.89363 8.06395 2.4155 9.45936C2.3615 9.61694 2.3615 9.78801 2.41549 9.94558C3.49488 13.0957 6.48191 15.3619 10.0002 15.3619C11.255 15.3619 12.4422 15.0737 13.4994 14.5598L15.3625 16.4229C15.6554 16.7158 16.1302 16.7158 16.4231 16.4229C16.716 16.13 16.716 15.6551 16.4231 15.3622L4.63803 3.57709ZM12.3608 13.4212L10.4475 11.5079C10.3061 11.5423 10.1584 11.5606 10.0064 11.5606H9.99151C8.96527 11.5606 8.13333 10.7286 8.13333 9.70237C8.13333 9.5461 8.15262 9.39434 8.18895 9.24933L5.91885 6.97923C5.03505 7.69015 4.34057 8.62704 3.92328 9.70247C4.86803 12.1373 7.23361 13.8619 10.0002 13.8619C10.8326 13.8619 11.6287 13.7058 12.3608 13.4212ZM16.0771 9.70249C15.7843 10.4569 15.3552 11.1432 14.8199 11.7311L15.8813 12.7925C16.6329 11.9813 17.2187 11.0143 17.5849 9.94561C17.6389 9.78803 17.6389 9.61696 17.5849 9.45938C16.5055 6.30925 13.5184 4.04303 10.0002 4.04303C9.13525 4.04303 8.30244 4.17999 7.52218 4.43338L8.75139 5.66259C9.1556 5.58413 9.57311 5.54303 10.0002 5.54303C12.7667 5.54303 15.1323 7.26768 16.0771 9.70249Z"
                              fill="#98A2B3"
                            />
                          </svg>
                        </span>
                      </div>
                    </div>
                    <!-- Checkbox -->
                    <div class="flex items-center justify-between pt-1">
                      <div>
                        <label
                          for="keepLoggedIn"
                        class="flex items-center text-sm font-normal text-gray-700 cursor-pointer select-none"
                        >
                          <div class="relative">
                            <input
                              v-model="keepLoggedIn"
                              type="checkbox"
                              id="keepLoggedIn"
                              class="sr-only"
                            />
                            <div
                              :class="
                                keepLoggedIn
                                  ? 'border-brand-500 bg-brand-500'
                                  : 'bg-white border-gray-300'
                              "
                              class="mr-3 flex h-5 w-5 items-center justify-center rounded border"
                            >
                              <span :class="keepLoggedIn ? '' : 'opacity-0'">
                                <svg
                                  width="14"
                                  height="14"
                                  viewBox="0 0 14 14"
                                  fill="none"
                                  xmlns="http://www.w3.org/2000/svg"
                                >
                                  <path
                                    d="M11.6666 3.5L5.24992 9.91667L2.33325 7"
                                    stroke="white"
                                    stroke-width="1.94437"
                                    stroke-linecap="round"
                                    stroke-linejoin="round"
                                  />
                                </svg>
                              </span>
                            </div>
                          </div>
                          Запомните меня
                        </label>
                      </div>
                      <router-link
                        to="/reset-password"
                        class="text-sm text-brand-500 hover:text-brand-600 font-medium"
                        >Забыли пароль?</router-link
                      >
                    </div>
                    <!-- Button -->
                    <div class="pt-1">
                      <button
                        type="submit"
                        :disabled="loading"
                        class="flex items-center justify-center w-full px-4 py-4 text-base font-semibold text-white transition rounded-lg bg-brand-500 shadow-md hover:bg-brand-600 hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <span v-if="loading" class="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></span>
                        {{ loading ? 'Вход...' : 'Войти' }}
                      </button>
                    </div>
                  </div>
                </form>
                <div class="mt-5">
                  <p class="text-sm font-normal text-center text-gray-700 sm:text-start">
                    У вас нет аккаунта ?
                    <router-link
                      to="/signup"
                      class="text-brand-500 hover:text-brand-600 font-medium"
                      >Зарегистрироваться</router-link
                    >
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div
          class="relative items-center hidden w-full h-full lg:w-1/2 bg-[#1B2B5B] lg:flex overflow-hidden"
        >
          <CommonGridShape class="opacity-25" />
          <div class="relative z-10 flex flex-col items-center justify-center w-full h-full px-12 py-16 text-center">
            <img :src="logoAuth" alt="AdMirra" class="h-24 mb-4" />
            <p class="max-w-sm text-sm font-medium leading-relaxed text-white/85">
              Анализируйте и оптимизируйте ваши рекламные кампании
            </p>
          </div>
        </div>
      </div>
    </div>
  </FullScreenLayout>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import FullScreenLayout from '@/layouts/FullScreenLayout.vue'
import CommonGridShape from '@/components/common/CommonGridShape.vue'
import { useAuth } from '@/composables/useAuth'
import { DEFAULT_DASHBOARD_PATH } from '@/constants/config'
import logoAuth from '@/assets/imgs/logo/AdMirra.png'

const router = useRouter()
const { login } = useAuth()
const showPassword = ref(false)
const keepLoggedIn = ref(false)
const loading = ref(false)

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
  
  const result = await login(loginForm.email, loginForm.password)
  
  loading.value = false
  if (result.success) {
    router.push(DEFAULT_DASHBOARD_PATH)
  }
}
</script>
