<template>
  <div class="flex min-h-[calc(100vh-76px)] items-center justify-center p-8">
    <div class="w-full max-w-[1036px]">

      <!-- Тёмная карточка -->
      <div class="relative rounded-[20px] overflow-hidden bg-[#323741] text-white">

        <!-- Паттерн-оверлей (заменяет ::before из CSS) -->
        <div
          class="absolute inset-0 pointer-events-none z-0 opacity-[0.15]"
          style="background: url('/admirra/img/pattern.png') 30px 0 / 70px"
        />

        <!-- Блюр-орбы -->
        <div class="absolute z-0 pointer-events-none" style="left:-150px;top:-260px">
          <div style="width:492px;height:492px;border-radius:50%;background:rgba(37,99,235,0.34);filter:blur(110px)" />
        </div>
        <div class="absolute z-0 pointer-events-none" style="right:-100px;bottom:-290px">
          <div style="width:492px;height:492px;border-radius:50%;background:rgba(37,99,235,0.34);filter:blur(110px)" />
        </div>
        <div class="absolute z-0 pointer-events-none" style="left:calc(50% - 50px);top:-170px">
          <div style="width:222px;height:222px;border-radius:50%;background:rgba(37,99,235,0.38);filter:blur(110px)" />
        </div>

        <!-- Контент поверх орбов -->
        <div class="relative z-10 flex items-end">

          <!-- Форма -->
          <form
            class="flex flex-col flex-1 min-w-0 p-[40px]"
            style="row-gap:17px"
            @submit.prevent="handleSubmit"
          >
            <h3 class="text-[30px] leading-[1.2] font-semibold text-white">
              <span class="font-light">Для начала работы,</span><br />
              необходимо создать проект
            </h3>

            <p class="text-[15px] leading-[1.35] text-white/90">
              В рамках проекта доступна выгрузка статистики рекламных кампаний и&nbsp;детальный анализ показателей с&nbsp;использованием
              <strong class="font-medium bg-[linear-gradient(270deg,#06b5d4_0.35%,#1f9de4_32.08%,#2563eb_96.51%)] bg-clip-text text-transparent">AI-ассистентов</strong>
            </p>

            <div>
              <input
                v-model="projectName"
                type="text"
                placeholder="Название проекта"
                required
                class="create-input"
              />
            </div>

            <p v-if="errorMsg" class="text-[13px] text-red-300">{{ errorMsg }}</p>

            <div>
              <button type="submit" :disabled="loading" class="create-btn">
                <span class="relative z-[1] flex items-center gap-[10px]">
                  {{ loading ? 'Создание...' : 'Создать проект' }}
                  <span
                    v-if="!loading"
                    class="grid h-[15px] w-[15px] place-items-center rounded-full bg-black/20 text-[10px] font-medium leading-none"
                  ><span class="-translate-y-px">+</span></span>
                </span>
              </button>
            </div>
          </form>

          <!-- Иллюстрация (лиса) -->
          <div class="w-[407px] flex-shrink-0">
            <img
              src="/admirra/img/fox/welcome-create.png"
              alt="Создание проекта"
              class="block w-full h-auto"
            />
          </div>

        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api/axios'
import { useProjects } from '../../composables/useProjects'

const router = useRouter()
const { fetchProjects, setCurrentProject } = useProjects()

const projectName = ref('')
const loading = ref(false)
const errorMsg = ref('')

const handleSubmit = async () => {
  if (!projectName.value.trim() || loading.value) return
  loading.value = true
  errorMsg.value = ''
  try {
    const { data } = await api.post('clients/', { name: projectName.value.trim() })
    await fetchProjects()
    setCurrentProject(data.id)
    router.push('/dashboard/general-3')
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || 'Не удалось создать проект'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* Тёмный инпут — градиентный фон + свечение при фокусе */
.create-input {
  display: block;
  width: 100%;
  height: 46px;
  padding: 0 17px;
  font-size: 13px;
  color: #fff;
  caret-color: #fff;
  border: none;
  border-radius: 12px;
  outline: none;
  background: linear-gradient(to right, #3c465c, #3e3f44);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.12);
  transition: box-shadow 0.2s;
}
.create-input::placeholder {
  color: rgba(255, 255, 255, 0.6);
}
.create-input:focus {
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.35),
              0 0 10px rgba(37, 99, 235, 0.5);
}
.create-input:focus::placeholder {
  color: rgba(255, 255, 255, 0.2);
}

/* Кнопка с градиентом и hover-overlay через ::after */
.create-btn {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: center;
  height: 46px;
  padding: 0 17px;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.1;
  color: #fff;
  border: none;
  border-radius: 12px;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  background: linear-gradient(270deg, #06b5d4 0.35%, #1f9de4 32.08%, #2563eb 96.51%);
  transition: transform 0.75s;
}
.create-btn::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 12px;
  background: linear-gradient(270deg, #38e1ff 0.35%, #4abeff 32.08%, #5187ff 96.51%);
  opacity: 0;
  transition: opacity 1s;
}
.create-btn:hover {
  transform: scale(1.03);
}
.create-btn:hover::after {
  opacity: 1;
}
.create-btn:active {
  transform: scale(0.97);
  transition: transform 0s;
}
.create-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
  transform: none;
}
</style>
