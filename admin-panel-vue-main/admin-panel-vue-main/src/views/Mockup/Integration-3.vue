<template>
  <div class="admirra-page-wrapper">
    <section class="main-section">
      <div class="section-header pt-4 mt-1">
        <h3 class="heading-3 mb-2">{{ title }}</h3>
        <p class="section-header__descrp">{{ subtitle }}</p>
      </div>
      <div class="steps-track mb-4">
        <!-- Секции 1 и 2 (сокращенно, принцип тот же) -->
        <section class="steps-track__section _completed">
          <div class="steps-track__header">
            <div class="steps-track__marker"><div class="steps-track__marker-text">1</div></div>
            <div class="steps-track__caption">Проект</div>
          </div>
        </section>
        <section class="steps-track__section _completed">
          <div class="steps-track__header">
            <div class="steps-track__marker"><div class="steps-track__marker-text">2</div></div>
            <div class="steps-track__caption">Профиль</div>
          </div>
        </section>

        <section class="steps-track__section">
          <div class="steps-track__header">
            <div class="steps-track__marker">
              <div class="steps-track__marker-text">3</div>
            </div>
            <div class="steps-track__caption">Счетчики и цели</div>
          </div>
          <div class="steps-track__content">
            <div class="p-5 bg-white radius-base mb-5">
              <div class="mb-5">
                <h5 class="heading-5 weight-500">{{ countersTitle }}</h5>
                <p class="pt-3 text-15 weight-500 gray56">{{ countersSubtitle }}</p>
              </div>
              <div class="row g-4">
                <div v-for="(counter, idx) in counters" :key="idx" class="col-12 col-sm-6 col-md-auto">
                  <div class="select-card">
                    <input 
                      class="select-card__input" 
                      type="checkbox" 
                      :checked="counter.selected" 
                      @change="$emit('update:counter', { counter, selected: $event.target.checked })" 
                    />
                    <div class="select-card__inner">
                      <div class="select-card__header">
                        <div class="avatar-30x30">
                          <div class="avatar-text">{{ counter.shortName }}</div>
                        </div>
                        <div class="select-card__check">
                          <svg><use :href="checkIcon"></use></svg>
                        </div>
                      </div>
                      <div class="select-card__content _width-normal">
                        <div class="weight-500">
                          <div class="gray500 text-15 mb-1">{{ counter.name }}</div>
                          <div class="silver uppercase">ID: {{ counter.id }}</div>
                        </div>
                        <div>
                          <a class="select-card__link" :href="counter.url" target="_blank">
                            <svg><use :href="worldIcon"></use></svg>
                            <span>{{ counter.domain }}</span>
                          </a>
                        </div>
                        <div class="mt-auto">
                          <div class="caption"><span class="light-text">Источник:</span> {{ counter.source }}</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            <div class="p-5 bg-white radius-base mb-5">
              <div class="row g-4 mb-5">
                <div class="col-12 col-md">
                  <h5 class="heading-5 weight-500">{{ goalsTitle }}</h5>
                  <p class="pt-3 text-15 weight-500 gray56">{{ goalsSubtitle }}</p>
                </div>
                <div class="col-12 col-md-auto">
                  <div class="input-item">
                    <input class="input w-100" type="text" :placeholder="searchPlaceholder" @input="$emit('search-goals', $event.target.value)" />
                    <div class="input-icon">
                      <svg class="_stroke"><use :href="searchIcon"></use></svg>
                    </div>
                  </div>
                </div>
              </div>
              <div class="row g-4 pt-5">
                <div v-for="(goal, idx) in goals" :key="idx" class="col-12 col-sm-6 col-md-auto">
                  <div class="select-card">
                    <div v-if="goal.isRecommended" class="select-card__note">
                      <svg><use :href="starIcon"></use></svg>
                      <span>рекомендуемая</span>
                    </div>
                    <input 
                      class="select-card__input" 
                      type="checkbox" 
                      :checked="goal.selected" 
                      @change="$emit('update:goal', { goal, selected: $event.target.checked })" 
                    />
                    <div class="select-card__inner">
                      <div class="select-card__header">
                        <div class="avatar-30x30">
                          <div class="avatar-text">{{ goal.shortName }}</div>
                        </div>
                        <div class="select-card__check">
                          <svg><use :href="checkIcon"></use></svg>
                        </div>
                      </div>
                      <div class="select-card__content _width-normal">
                        <div class="weight-500">
                          <div class="gray500 text-15 mb-1">{{ goal.name }}</div>
                          <div class="silver uppercase">ID: {{ goal.id }}</div>
                        </div>
                      </div>
                      <div class="row align-items-end mt-auto">
                        <div class="col">
                          <div class="caption"><span class="light-text">Тип цели:</span> {{ goal.type }}</div>
                        </div>
                        <div class="col-auto mt-auto">
                          <button class="select-card__favorites" @click.stop="$emit('toggle-favorite', goal)">
                            <svg :class="{ active: goal.isFavorite }"><use :href="starIcon"></use></svg>
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            <div class="row g-3">
              <div class="col">
                <button class="btn _white" @click="$emit('back')">
                  <div class="btn__inner">
                    <div class="btn__icon-info">
                      <svg class="prev"><use :href="arrowIcon"></use></svg>
                    </div>
                    <span class="btn__text">Назад</span>
                  </div>
                </button>
              </div>
              <div class="col-auto">
                <div class="row">
                  <div class="col-auto">
                    <button class="btn _outline-gray" @click="$emit('cancel')">
                      <div class="btn__inner">
                        <span class="btn__text">Отмена</span>
                      </div>
                    </button>
                  </div>
                  <div class="col-auto">
                    <button class="btn _primary" @click="$emit('next')">
                      <div class="btn__inner">
                        <span class="btn__text">Далее</span>
                        <div class="btn__icon-info">
                          <svg class="next"><use :href="arrowIcon"></use></svg>
                        </div>
                      </div>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
        <section class="steps-track__section">
          <div class="steps-track__header">
            <div class="steps-track__marker"><div class="steps-track__marker-text">4</div></div>
            <div class="steps-track__caption">Сводка</div>
          </div>
        </section>
      </div>
    </section>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, default: 'Новая интеграция' },
  subtitle: { type: String, default: 'Добавление рекламного канала' },
  countersTitle: { type: String, default: 'Счетчики метрики' },
  countersSubtitle: { type: String, default: 'Выберите счетчики, для которых нужно отслеживать цели' },
  counters: {
    type: Array,
    default: () => [
      { id: '098409843080980', name: 'Дейтелинг Иркутск', shortName: 'ДИ', domain: 'sandblasting-msk.ru', url: '#', source: 'из компании', selected: true }
    ]
  },
  goalsTitle: { type: String, default: 'Цели и конверсии' },
  goalsSubtitle: { type: String, default: 'Выберите основную цель (звездочка) и дополнительные цели для отслеживания' },
  searchPlaceholder: { type: String, default: 'Поиск цели' },
  goals: {
    type: Array,
    default: () => [
      { id: '542695813', name: 'Цель на посещение', shortName: 'ДИ', type: 'URL', selected: true, isRecommended: true, isFavorite: false }
    ]
  },
  checkIcon: { type: String, default: '/admirra/img/svg/sprite.svg#check' },
  worldIcon: { type: String, default: '/admirra/img/svg/sprite.svg#world' },
  searchIcon: { type: String, default: '/admirra/img/svg/sprite.svg#search' },
  starIcon: { type: String, default: '/admirra/img/svg/sprite.svg#star' },
  arrowIcon: { type: String, default: '/admirra/img/svg/sprite.svg#arrow' }
})

defineEmits(['update:counter', 'update:goal', 'search-goals', 'toggle-favorite', 'back', 'cancel', 'next'])
</script>

<style scoped>
.admirra-page-wrapper {
  /* Scoped styles */
}
</style>
