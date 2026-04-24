<template>
  <div class="admirra-page-wrapper">
    <section class="main-section">
      <!-- Кнопки добавления платформ -->
      <div class="row gy-3 pb-5">
        <div class="col-auto">
          <button class="btn _sm _white _radius" @click="$router.push('/integrations/wizard')">
            <div class="btn__inner">
              <div class="btn__icon-img">
                <img class="img-cover" src="/admirra/img/icons/yandex-direct.png" alt="Yandex" />
              </div>
              <span class="btn__text weight-400" style="color:#cc3300">Yandex Direct</span>
              <div class="btn__icon-info ms-2">
                <svg><use href="/admirra/img/svg/sprite.svg#plus-bold"></use></svg>
              </div>
            </div>
          </button>
        </div>
        <div class="col-auto">
          <button class="btn _sm _white _radius" @click="$router.push('/integrations/wizard')">
            <div class="btn__inner">
              <div class="btn__icon-img">
                <img class="img-cover" src="/admirra/img/icons/vk-ads.png" alt="VK" />
              </div>
              <span class="btn__text weight-400" style="color:#0077ff">ВК Ads</span>
              <div class="btn__icon-info ms-2">
                <svg><use href="/admirra/img/svg/sprite.svg#plus-bold"></use></svg>
              </div>
            </div>
          </button>
        </div>
      </div>

      <div class="section-header pt-4">
        <h3 class="heading-3">Активные интеграции</h3>
      </div>

      <div class="row gy-4 mb-5">
        <div class="col-auto">
          <button class="btn _primary" @click="$router.push('/integrations/wizard')">
            <div class="btn__inner">
              <span class="btn__text">Добавить подключение</span>
              <div class="btn__icon-plus">+</div>
            </div>
          </button>
        </div>
        <div class="col-12 col-sm-auto">
          <div class="input-item">
            <input class="input w-100" type="text" placeholder="Поиск интеграций" v-model="search" />
            <div class="input-icon">
              <svg class="_stroke"><use href="/admirra/img/svg/sprite.svg#search"></use></svg>
            </div>
          </div>
        </div>
      </div>

      <div v-if="isLoading" class="py-5 text-center gray56">Загрузка...</div>

      <div v-else-if="filteredIntegrations.length === 0" class="py-5 text-center gray56">
        {{ search ? 'Ничего не найдено' : 'Нет активных интеграций. Добавьте первое подключение.' }}
      </div>

      <div v-else class="row g-4">
        <div
          v-for="integration in filteredIntegrations"
          :key="integration.id"
          class="col-12 col-sm-11 col-md-9 col-lg-8 col-xl-6"
        >
          <div class="integration-card">
            <div class="integration-card__header">
              <div class="row weight-500">
                <div class="col-auto">
                  <div class="avatar-36x36" style="background:#e8eef9;border-radius:50%;display:flex;align-items:center;justify-content:center">
                    <span style="font-size:13px;font-weight:700;color:#4b6fa0">
                      {{ (integration.client_name || '?').slice(0, 2).toUpperCase() }}
                    </span>
                  </div>
                </div>
                <div class="col">
                  <div class="mb-1 gray56">Проект</div>
                  <div class="text-15 gray">{{ integration.client_name || '—' }}</div>
                </div>
              </div>
              <div class="ms-sm-auto">
                <div class="caption _light _md">{{ platformLabel(integration.platform) }}</div>
              </div>
            </div>

            <div class="integration-card__content">
              <div class="row gy-3 mb-3">
                <div class="col-12 col-sm">
                  <div class="row">
                    <div class="col-auto">
                      <div class="avatar-33x33">
                        <img class="img-cover" :src="platformIcon(integration.platform)" :alt="integration.platform" />
                      </div>
                    </div>
                    <div class="col">
                      <div class="text-15 gray mb-1">{{ platformLabel(integration.platform) }}</div>
                      <div class="d-flex flex-wrap align-items-center">
                        <span :class="['dotty align-self-center me-2', syncStatusClass(integration.sync_status)]"></span>
                        <span class="gray56 uppercase">{{ syncStatusLabel(integration.sync_status) }}</span>
                        <template v-if="integration.last_sync_at">
                          <span class="px-1 gray56 text-10">|</span>
                          <time class="gray30">{{ formatDate(integration.last_sync_at) }}</time>
                        </template>
                      </div>
                    </div>
                  </div>
                </div>
                <div class="col-auto">
                  <div class="badge-text _md">
                    <span class="weight-500">24 часа</span>
                    <svg class="badge-text__icon _stroke"><use href="/admirra/img/svg/sprite.svg#refresh-line"></use></svg>
                  </div>
                </div>
              </div>

              <div class="row gy-3 align-items-end">
                <div class="col-12 col-sm-auto">
                  <div class="caption w-100">ID: {{ integration.external_account_id || integration.id }}</div>
                </div>
                <div class="col-12 col-sm-auto ms-auto">
                  <button class="btn _sm _white w-100" @click="$router.push('/integrations/wizard')">
                    <div class="btn__inner px-4">
                      <span class="btn__text weight-400 c71663e">Настроить</span>
                    </div>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../../api/axios'
import { useProjects } from '../../composables/useProjects'

const { currentProjectId } = useProjects()

const integrations = ref([])
const isLoading = ref(false)
const search = ref('')

const fetchIntegrations = async () => {
  isLoading.value = true
  try {
    const params = {}
    if (currentProjectId.value) params.client_id = currentProjectId.value
    const { data } = await api.get('integrations/', { params })
    integrations.value = data
  } catch (err) {
    console.error('Failed to load integrations:', err)
  } finally {
    isLoading.value = false
  }
}

onMounted(fetchIntegrations)

const filteredIntegrations = computed(() => {
  if (!search.value.trim()) return integrations.value
  const q = search.value.toLowerCase()
  return integrations.value.filter(i =>
    i.client_name?.toLowerCase().includes(q) ||
    i.platform?.toLowerCase().includes(q)
  )
})

const platformLabel = (platform) => {
  const map = { YANDEX: 'Yandex Direct', VK: 'VK Ads', MYTARGET: 'MyTarget' }
  return map[platform?.toUpperCase()] || platform || '—'
}

const platformIcon = (platform) => {
  const map = {
    YANDEX: '/admirra/img/icons/yandex-direct.png',
    VK: '/admirra/img/icons/vk-ads.png',
    MYTARGET: '/admirra/img/icons/mytarget.png'
  }
  return map[platform?.toUpperCase()] || '/admirra/img/icons/yandex-direct.png'
}

const syncStatusClass = (status) => {
  const map = { SUCCESS: '_success', FAILED: '_danger', PENDING: '_warning', NEVER: '' }
  return map[status] || ''
}

const syncStatusLabel = (status) => {
  const map = { SUCCESS: 'Синхронизировано', FAILED: 'Ошибка', PENDING: 'В процессе', NEVER: 'Не синхронизировано' }
  return map[status] || status || 'Неизвестно'
}

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleString('ru-RU', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
.admirra-page-wrapper { }
</style>
