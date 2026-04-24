<template>
  <div class="admirra-page-wrapper">
    <section class="main-section">
      <div class="welcome-create">
        <div class="dark-bg">
          <div class="dark-bg__inner">
            <div class="welcome-create__container">
              <form class="welcome-create__content" @submit.prevent="handleSubmit">
                <h3 class="heading-3 lh-120 mb-1" v-html="title"></h3>
                <p class="text-15 lh-135 mb-3" v-html="description"></p>
                <div class="d-flex flex-column mb-3">
                  <input
                    class="input _dark"
                    type="text"
                    v-model="projectName"
                    :placeholder="inputPlaceholder"
                    required
                  />
                </div>

                <div v-if="errorMsg" class="mb-3 text-13" style="color:#fca5a5">{{ errorMsg }}</div>

                <div class="d-flex flex-column">
                  <button type="submit" class="btn" :disabled="loading">
                    <div class="btn__inner">
                      <span class="btn__text">{{ loading ? 'Создание...' : 'Создать проект' }}</span>
                      <div v-if="!loading" class="btn__icon-plus">+</div>
                    </div>
                  </button>
                </div>
              </form>
              <div class="welcome-create__fox">
                <img class="img-cover" src="/admirra/img/fox/welcome-create.png" alt="welcome" />
              </div>
            </div>
          </div>
          <div class="dark-bg__light _pos1"><div class="lightBlurBg _xl"></div></div>
          <div class="dark-bg__light _pos2"><div class="lightBlurBg _xl"></div></div>
          <div class="dark-bg__light _pos3"><div class="lightBlurBg _sm"></div></div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api/axios'
import { useProjects } from '../../composables/useProjects'

const title = '<span class="weight-300">Для начала работы,</span> <br /> необходимо создать проект'
const description = 'В рамках проекта доступна выгрузка статистики рекламных кампаний и&nbsp;детальный анализ показателей с&nbsp;использованием <strong class="weight-500 accent-gradient">AI-ассистентов</strong>'
const inputPlaceholder = 'Название проекта'

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
.admirra-page-wrapper {
  /* Изоляция стилей */
}

/* Форсируем белый текст внутри тёмной карточки */
:deep(.dark-bg) h3,
:deep(.dark-bg) p,
:deep(.dark-bg) span,
:deep(.dark-bg) .heading-3 {
  color: #fff !important;
}

:deep(.dark-bg strong),
:deep(.dark-bg b) {
  color: #fff !important;
}

:deep(.dark-bg) .input,
:deep(.dark-bg) input {
  color: #fff !important;
  caret-color: #fff;
}
</style>
