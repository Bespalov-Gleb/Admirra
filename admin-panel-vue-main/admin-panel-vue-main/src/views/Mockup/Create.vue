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
                <div class="d-flex flex-column">
                  <input 
                    class="input _dark" 
                    type="text" 
                    :value="modelValue"
                    @input="$emit('update:modelValue', $event.target.value)"
                    :placeholder="inputPlaceholder" 
                    required 
                  />
                </div>
                <div class="d-flex flex-column">
                  <button type="submit" class="btn" :disabled="loading">
                    <div class="btn__inner">
                      <span class="btn__text">{{ loading ? loadingText : buttonText }}</span>
                      <div v-if="!loading" class="btn__icon-plus">+</div>
                    </div>
                  </button>
                </div>
              </form>
              <div class="welcome-create__fox">
                <img class="img-cover" :src="imageSrc" alt="welcome" />
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
const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  title: {
    type: String,
    default: '<span class="weight-300">Для начала работы,</span> <br /> необходимо создать проект'
  },
  description: {
    type: String,
    default: 'В рамках проекта доступна выгрузка статистики рекламных кампаний и&nbsp;детальный анализ показателей с&nbsp;использованием <strong class="weight-500 accent-gradient">AI-ассистентов</strong>'
  },
  inputPlaceholder: {
    type: String,
    default: 'Название проекта'
  },
  buttonText: {
    type: String,
    default: 'Создать проект'
  },
  loadingText: {
    type: String,
    default: 'Создание...'
  },
  loading: {
    type: Boolean,
    default: false
  },
  imageSrc: {
    type: String,
    default: '/admirra/img/fox/welcome-create.png'
  }
})

const emit = defineEmits(['update:modelValue', 'create'])

const handleSubmit = () => {
  if (props.modelValue.trim()) {
    emit('create', props.modelValue)
  }
}
</script>

<style scoped>
.admirra-page-wrapper {
  /* Изоляция стилей */
}
</style>
