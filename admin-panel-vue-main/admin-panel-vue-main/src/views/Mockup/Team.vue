<template>
  <div class="admirra-page-wrapper">
    <section class="main-section">
      <div class="section-header pt-4">
        <h3 class="heading-3">{{ title }}</h3>
      </div>
      <div class="row gy-3 mb-5">
        <div class="col">
          <div class="row gy-3">
            <div v-for="tab in tabs" :key="tab.id" class="col-auto">
              <button 
                :class="['btn', currentTab === tab.id ? '_primary' : '_white']" 
                @click="$emit('change-tab', tab.id)"
              >
                <div class="btn__inner">
                  <span :class="['btn__text', { gray: currentTab !== tab.id }]">{{ tab.label }}</span>
                </div>
              </button>
            </div>
          </div>
        </div>
        <div class="col-auto">
          <button class="btn _primary" @click="$emit('add-member')">
            <div class="btn__inner">
              <span class="btn__text">{{ addButtonLabel }}</span>
              <div class="btn__icon-plus">+</div>
            </div>
          </button>
        </div>
      </div>
      
      <div v-for="(member, mIdx) in members" :key="mIdx" class="mb-4 pb-2">
        <div :class="['team-item', { 'is-open': member.isOpen }]">
          <div class="row team-item__header">
            <div class="col col-lg-4 col-xl-3">
              <div class="d-flex">
                <div class="avatar-36x36 me-4">
                  <img class="img-cover" :src="member.avatar" alt="#" />
                </div>
                <div class="weight-500">
                  <div class="mb-1 text-15 gray">{{ member.name }}</div>
                  <div class="gray56">{{ member.email }}</div>
                </div>
              </div>
            </div>
            <div class="col-auto col-lg">
              <button class="team-item__project-toggle" @click="$emit('toggle-member', member)">
                <span>{{ projectsToggleLabel }}</span>
                <div class="circle-arrow _light">
                  <svg><use :href="arrowIcon"></use></svg>
                </div>
              </button>
            </div>
            <div class="col-12 col-lg-auto">
              <div class="row">
                <div class="col col-lg-auto">
                  <button class="btn _primary" @click="$emit('add-access', member)">
                    <div class="btn__inner">
                      <span class="btn__text">{{ addAccessLabel }}</span>
                      <div class="btn__icon-plus">+</div>
                    </div>
                  </button>
                </div>
                <div class="col-auto col-lg-auto">
                  <button class="btn-action _danger" @click="$emit('delete-member', member)">
                    <svg><use :href="basketIcon"></use></svg>
                  </button>
                </div>
              </div>
            </div>
          </div>
          <div v-if="member.isOpen" class="team-item__project-content row g-4" style="display: flex;">
            <div v-for="(project, pIdx) in member.projects" :key="pIdx" class="col-12 col-sm-auto">
              <div :class="['card-base', project.variantClass]">
                <div class="avatar-30x30 mb-2">
                  <img class="img-cover" :src="project.icon" alt="#" />
                </div>
                <div class="weight-500 gray500">{{ project.name }}</div>
                <button class="btn _sm _white mt-auto" @click="$emit('revoke-access', { member, project })">
                  <div class="btn__inner">
                    <span class="btn__text gray">{{ revokeAccessLabel }}</span>
                  </div>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, default: 'Команда' },
  addButtonLabel: { type: String, default: 'Добавить сотрудника' },
  projectsToggleLabel: { type: String, default: 'Доступ к проектам' },
  addAccessLabel: { type: String, default: 'Добавить доступ к проекту' },
  revokeAccessLabel: { type: String, default: 'Отозвать доступ' },
  tabs: {
    type: Array,
    default: () => [
      { id: 'staff', label: 'Сотрудники' },
      { id: 'clients', label: 'Клиенты' }
    ]
  },
  currentTab: { type: String, default: 'staff' },
  members: {
    type: Array,
    default: () => [
      {
        id: 1,
        name: 'Петр Петров',
        email: 'testemail@mail.ru',
        avatar: '/admirra/img/avatars/user1.jpg',
        isOpen: true,
        projects: [
          { name: 'ЖК Сливки / Яндекс', icon: '/admirra/img/avatars/avatar-36x36.png', variantClass: '_oldlace' },
          { name: 'Дейтелинг Иркутск', icon: '/admirra/img/avatars/avatar-36x36.png', variantClass: '_aliceblue' }
        ]
      }
    ]
  },
  arrowIcon: { type: String, default: '/admirra/img/svg/sprite.svg#arrow' },
  basketIcon: { type: String, default: '/admirra/img/svg/sprite.svg#basket' }
})

defineEmits(['change-tab', 'add-member', 'toggle-member', 'add-access', 'delete-member', 'revoke-access'])
</script>

<style scoped>
.admirra-page-wrapper {
  /* Scoped styles */
}
/* Ensure project content handles visibility correctly if not using jQuery slideToggle */
.team-item__project-content {
  transition: all 0.3s ease;
}
</style>
