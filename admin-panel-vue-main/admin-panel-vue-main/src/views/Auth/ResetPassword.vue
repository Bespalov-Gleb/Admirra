<template>
  <FullScreenLayout>
    <div class="relative p-6 bg-white z-1 sm:p-0">
      <div
        class="relative flex flex-col justify-center w-full min-h-screen lg:min-h-screen lg:flex-row bg-white"
      >
        <!-- Левая колонка: как на SignIn / SignUp -->
        <div class="flex flex-col flex-1 w-full lg:w-1/2 bg-white">
          <div class="flex flex-col justify-center flex-1 w-full max-w-lg mx-auto pt-16 pb-10 px-0 sm:px-4">
            <div class="mb-8 sm:mb-10">
              <h1
                class="mb-3 font-semibold text-gray-900 text-3xl sm:text-4xl"
              >
                Восстановление пароля
              </h1>
              <p class="text-base text-gray-600">
                Введите ваш email — отправим ссылку для сброса пароля
              </p>
            </div>
            <div>
              <form @submit.prevent="handleResetPassword">
                <div class="space-y-5">
                  <div>
                    <label
                      for="email"
                      class="mb-2 block text-sm font-medium text-gray-700"
                    >
                      E-mail<span class="text-red-500">*</span>
                    </label>
                    <input
                      v-model="resetForm.email"
                      type="email"
                      id="email"
                      name="email"
                      placeholder="Введите email"
                      autocomplete="email"
                      class="h-16 w-full rounded-lg border border-gray-300 bg-white px-5 py-4 text-base text-gray-900 shadow-sm placeholder:text-gray-400 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20"
                    />
                  </div>
                  <div class="pt-1">
                    <button
                      type="submit"
                      :disabled="loading || emailSent"
                      class="flex items-center justify-center w-full px-4 py-4 text-base font-semibold text-white transition rounded-lg bg-brand-500 shadow-md hover:bg-brand-600 hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <span
                        v-if="loading"
                        class="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"
                      ></span>
                      {{
                        loading
                          ? 'Отправка...'
                          : emailSent
                            ? 'Письмо отправлено'
                            : 'Отправить ссылку для сброса'
                      }}
                    </button>
                  </div>
                </div>
              </form>
              <div
                v-if="emailSent"
                class="mt-5 p-4 rounded-lg bg-green-50 border border-green-200"
              >
                <p class="text-sm text-green-800">
                  Мы отправили ссылку для сброса пароля на {{ resetForm.email }}
                </p>
              </div>
              <div class="mt-5">
                <p
                  class="text-sm font-normal text-center text-gray-700 sm:text-start"
                >
                  Вспомнили пароль?
                  <router-link
                    to="/signin"
                    class="text-brand-500 hover:text-brand-600 font-medium"
                    >Войти</router-link
                  >
                </p>
              </div>
            </div>
          </div>
        </div>

        <!-- Правая колонка: как на SignIn / SignUp (тёмный фон, логотип, без большой иллюстрации) -->
        <div
          class="relative items-center hidden w-full min-h-[280px] lg:min-h-0 lg:h-auto lg:w-1/2 bg-[#1B2B5B] lg:flex overflow-hidden"
        >
          <CommonGridShape class="opacity-25" />
          <div
            class="relative z-10 flex flex-col items-center justify-center w-full h-full px-12 py-16 text-center"
          >
            <img :src="logoAuth" alt="AdMirra" class="h-24 mb-4" />
            <p
              class="max-w-sm text-sm font-medium leading-relaxed text-white/85"
            >
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
import FullScreenLayout from '@/layouts/FullScreenLayout.vue'
import CommonGridShape from '@/components/common/CommonGridShape.vue'
import logoAuth from '@/assets/imgs/logo/AdMirra.png'

const loading = ref(false)
const emailSent = ref(false)

const resetForm = reactive({
  email: ''
})

const isValidEmail = (email) => {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
}

const handleResetPassword = async () => {
  if (!resetForm.email) return
  if (!isValidEmail(resetForm.email)) return

  loading.value = true

  try {
    // TODO: Реализовать API endpoint для сброса пароля
    // await api.post('auth/reset-password', { email: resetForm.email })

    await new Promise((resolve) => setTimeout(resolve, 1000))

    emailSent.value = true
  } catch (error) {
    console.error('Ошибка при отправке письма:', error)
  } finally {
    loading.value = false
  }
}
</script>
