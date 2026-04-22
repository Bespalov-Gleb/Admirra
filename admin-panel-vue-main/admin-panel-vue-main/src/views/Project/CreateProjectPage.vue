<template>
  <section class="main-section">
    <div class="welcome-create">
      <div class="dark-bg">
        <div class="dark-bg__inner">
          <div class="welcome-create__container">
            <form class="welcome-create__content" @submit.prevent="handleCreateProject">
              <h3 class="heading-3 lh-120 mb-1">
                <span class="weight-300">Для начала работы,</span> <br />
                необходимо создать проект
              </h3>
              <p class="text-15 lh-135 mb-3">В рамках проекта доступна выгрузка статистики рекламных кампаний и&nbsp;детальный анализ показателей с&nbsp;использованием <strong class="weight-500 accent-gradient">AI-ассистентов</strong></p>
              <div class="d-flex flex-column">
                <input 
                  class="input _dark" 
                  type="text" 
                  name="projectName" 
                  v-model="projectName"
                  placeholder="Название проекта" required 
                />
              </div>
              <div class="d-flex flex-column">
                <button type="submit" class="btn">
                  <div class="btn__inner">
                    <span class="btn__text">Создать проект</span>
                    <div class="btn__icon-plus">+</div>
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
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const projectName = ref('')
const loading = ref(false)
const router = useRouter()

const handleCreateProject = () => {
  if (!projectName.value.trim()) return
  
  loading.value = true
  setTimeout(() => {
    // Очистка формы после успешного создания
    projectName.value = ''
    alert('Проект успешно создан!')
    
    // Перекидываем пользователя на страницу проектов
    router.push('/project-rows')
    loading.value = false
  }, 500)
}
</script>
