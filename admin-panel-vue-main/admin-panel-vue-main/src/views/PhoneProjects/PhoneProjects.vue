<template>
  <div class="space-y-6 overflow-x-hidden w-full">
    <!-- Заголовок с кнопкой создания -->
    <div class="flex flex-col xl:flex-row xl:items-center justify-between gap-6 py-5 px-6 sm:px-8 bg-white/60 backdrop-blur-xl rounded-[2.2222rem] border border-white/80 shadow-sm transition-all hover:shadow-md">
      <div class="min-w-0 flex-shrink-0">
        <label class="text-[0.625rem] font-black text-gray-400 uppercase tracking-widest ml-1 opacity-70">
          Телефония
        </label>
        <div class="flex items-center gap-3 mt-0.5">
          <div class="p-2 bg-blue-600 rounded-xl shadow-lg shadow-blue-200 hidden xs:block">
            <PhoneIcon class="w-4 h-4 text-white" />
          </div>
          <div class="flex flex-col min-w-0">
            <h1 class="text-xl sm:text-2xl font-black text-gray-900 tracking-tight truncate">
              Проекты телефонии
            </h1>
            <div class="flex items-center gap-1.5 mt-0.5">
              <div class="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse flex-shrink-0"></div>
              <p class="text-[0.625rem] font-bold text-gray-400 uppercase tracking-wider truncate">
                Управление проектами для валидации телефонов
              </p>
            </div>
          </div>
        </div>
      </div>
      <div class="flex items-center gap-3">
        <button
          @click="showCreateModal = true"
          class="px-4 py-2.5 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-all shadow-sm hover:shadow-md flex items-center gap-2 font-semibold text-sm"
        >
          <PlusIcon class="w-5 h-5" />
          Создать проект
        </button>
      </div>
    </div>

    <!-- Список проектов -->
    <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div v-for="i in 3" :key="i" class="bg-white rounded-[2.7778rem] p-8 animate-pulse">
        <div class="h-6 bg-gray-200 rounded-lg mb-4"></div>
        <div class="h-4 bg-gray-200 rounded-lg mb-6"></div>
        <div class="space-y-3">
          <div class="h-4 bg-gray-200 rounded"></div>
          <div class="h-4 bg-gray-200 rounded"></div>
        </div>
      </div>
    </div>

    <div v-else-if="projects.length === 0" class="text-center py-16 bg-white/60 backdrop-blur-xl rounded-[2.2222rem] border border-white/80 shadow-sm">
      <div class="w-20 h-20 mx-auto mb-6 bg-blue-100 rounded-full flex items-center justify-center">
        <PhoneIcon class="w-10 h-10 text-blue-600" />
      </div>
      <h3 class="text-xl font-bold text-gray-900 mb-2">Нет проектов</h3>
      <p class="text-gray-600 mb-6 max-w-md mx-auto">Создайте первый проект для валидации телефонов и начните получать качественные лиды</p>
      <button
        @click="showCreateModal = true"
        class="px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-all shadow-sm hover:shadow-md font-semibold flex items-center gap-2 mx-auto"
      >
        <PlusIcon class="w-5 h-5" />
        Создать проект
      </button>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div
        v-for="project in projects"
        :key="project.id"
        class="bg-white rounded-[2.7778rem] border border-gray-100 shadow-sm hover:shadow-md transition-all p-8"
      >
        <div class="flex items-start justify-between mb-6">
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-2">
              <div class="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center flex-shrink-0">
                <PhoneIcon class="w-5 h-5 text-blue-600" />
              </div>
              <h3 class="text-lg font-bold text-gray-900 truncate">{{ project.name }}</h3>
            </div>
            <p v-if="project.description" class="text-sm text-gray-600 line-clamp-2">{{ project.description }}</p>
          </div>
          <span
            :class="project.is_active ? 'bg-green-100 text-green-700 border-green-200' : 'bg-gray-100 text-gray-700 border-gray-200'"
            class="px-3 py-1 text-xs font-semibold rounded-full border flex-shrink-0"
          >
            {{ project.is_active ? 'Активен' : 'Неактивен' }}
          </span>
        </div>

        <!-- Настройки проекта -->
        <div class="space-y-3 mb-6">
          <div class="flex items-center gap-2 text-sm text-gray-600 bg-gray-50 rounded-xl p-3">
            <LinkIcon class="w-4 h-4 text-gray-400 flex-shrink-0" />
            <span v-if="project.webhook_url" class="truncate text-xs font-mono">{{ project.webhook_url }}</span>
            <span v-else class="text-gray-400 text-xs">Webhook не настроен</span>
          </div>
          <div class="flex flex-wrap gap-2">
            <span
              v-if="project.enable_social_check"
              class="px-3 py-1 text-xs font-semibold bg-blue-100 text-blue-700 rounded-full"
            >
              Соцсети
            </span>
            <span
              v-if="project.enable_lead_scoring"
              class="px-3 py-1 text-xs font-semibold bg-emerald-100 text-emerald-800 rounded-full"
            >
              Скоринг
            </span>
            <span
              v-if="project.enable_gosuslugi_check"
              class="px-3 py-1 text-xs font-semibold bg-purple-100 text-purple-700 rounded-full"
            >
              Госуслуги
            </span>
            <span
              v-if="project.enable_metrica_export"
              class="px-3 py-1 text-xs font-semibold bg-yellow-100 text-yellow-700 rounded-full"
            >
              Метрика
            </span>
          </div>
        </div>

        <!-- Действия -->
        <div class="flex items-center gap-2 pt-6 border-t border-gray-200">
          <button
            @click="viewProject(project)"
            class="flex-1 px-4 py-2.5 text-sm font-semibold text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-xl transition-all"
          >
            Просмотр
          </button>
          <button
            @click="editProject(project)"
            class="flex-1 px-4 py-2.5 text-sm font-semibold text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-xl transition-all"
          >
            Редактировать
          </button>
          <button
            @click="deleteProject(project)"
            class="px-4 py-2.5 text-sm font-semibold text-red-600 bg-red-50 hover:bg-red-100 rounded-xl transition-all"
          >
            <TrashIcon class="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>

    <!-- Модальное окно создания/редактирования -->
    <div
      v-if="showCreateModal || editingProject"
      class="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      @click.self="closeModal"
    >
      <div class="bg-white rounded-[2.2222rem] shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div class="p-8">
          <div class="flex items-center justify-between mb-6">
            <div>
              <h2 class="text-2xl font-black text-gray-900">
                {{ editingProject ? 'Редактировать проект' : 'Создать проект' }}
              </h2>
              <p class="text-sm text-gray-500 mt-1">
                {{ editingProject ? 'Обновите настройки проекта' : 'Настройте новый проект для валидации лидов' }}
              </p>
            </div>
            <button
              @click="closeModal"
              class="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <XMarkIcon class="w-6 h-6" />
            </button>
          </div>

          <form @submit.prevent="saveProject" class="space-y-6">
            <div>
              <label class="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">
                Название проекта <span class="text-red-500">*</span>
              </label>
              <input
                v-model="projectForm.name"
                type="text"
                required
                placeholder="Введите название проекта"
                class="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
              />
            </div>

            <div>
              <label class="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">
                Описание
              </label>
              <textarea
                v-model="projectForm.description"
                rows="3"
                placeholder="Описание проекта (необязательно)"
                class="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition resize-none"
              ></textarea>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">
                Связать с клиентом (опционально)
              </label>
              <select
                v-model="projectForm.client_id"
                class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option :value="null">Не привязывать</option>
                <option v-for="client in clients" :key="client.id" :value="client.id">
                  {{ client.name }}
                </option>
              </select>
            </div>

            <!-- Настройки выгрузки -->
            <div class="border-t pt-4">
              <h3 class="text-sm font-semibold text-gray-900 mb-3">Настройки выгрузки</h3>
              
              <div class="space-y-3">
                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-1">
                    CRM Webhook URL
                  </label>
                  <input
                    v-model="projectForm.crm_webhook_url"
                    type="url"
                    placeholder="https://example.com/webhook"
                    class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-1">
                    Email получатели (через запятую)
                  </label>
                  <input
                    v-model="emailRecipientsInput"
                    type="text"
                    placeholder="email1@example.com, email2@example.com"
                    class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-1">
                    Telegram Chat ID
                  </label>
                  <input
                    v-model="projectForm.telegram_chat_id"
                    type="text"
                    placeholder="123456789"
                    class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <p class="text-xs text-gray-500 mt-1">Чат, куда бот будет присылать уведомления о новых заявках.</p>
                </div>
              </div>
            </div>

            <!-- Настройки валидации -->
            <div class="border-t pt-4">
              <h3 class="text-sm font-semibold text-gray-900 mb-3">Настройки валидации</h3>
              
              <div class="space-y-2">
                <label class="flex items-center">
                  <input
                    v-model="projectForm.enable_social_check"
                    type="checkbox"
                    class="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <span class="ml-2 text-sm text-gray-700">Проверка соцсетей (TT, WA, MAKC, BK)</span>
                </label>

                <label class="flex items-center">
                  <input
                    v-model="projectForm.enable_lead_scoring"
                    type="checkbox"
                    class="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <span class="ml-2 text-sm text-gray-700">Скоринг лида (0–100, tier low/medium/high)</span>
                </label>

                <label class="flex items-center">
                  <input
                    v-model="projectForm.enable_gosuslugi_check"
                    type="checkbox"
                    class="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <span class="ml-2 text-sm text-gray-700">Проверка регистрации в Госуслугах</span>
                </label>

                <label class="flex items-center">
                  <input
                    v-model="projectForm.enable_spam_check"
                    type="checkbox"
                    class="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <span class="ml-2 text-sm text-gray-700">Проверка спам-баз</span>
                </label>

                <label class="flex items-center">
                  <input
                    v-model="projectForm.enable_bitrix_check"
                    type="checkbox"
                    class="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <span class="ml-2 text-sm text-gray-700">Проверка дубликатов в Bitrix24</span>
                </label>

                <label class="flex items-center">
                  <input
                    v-model="projectForm.enable_metrica_export"
                    type="checkbox"
                    class="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <span class="ml-2 text-sm text-gray-700">Отправка в Яндекс.Метрику</span>
                </label>
              </div>
            </div>

            <div class="flex items-center justify-end gap-3 pt-6 border-t border-gray-200">
              <button
                type="button"
                @click="closeModal"
                class="px-6 py-3 text-gray-700 bg-gray-100 rounded-xl hover:bg-gray-200 transition-all font-semibold"
              >
                Отмена
              </button>
              <button
                type="submit"
                :disabled="saving"
                class="px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-all disabled:opacity-50 font-semibold shadow-sm hover:shadow-md flex items-center gap-2"
              >
                <span v-if="saving" class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                {{ saving ? 'Сохранение...' : (editingProject ? 'Сохранить' : 'Создать') }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Модальное окно просмотра проекта -->
    <div
      v-if="viewingProject"
      class="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      @click.self="viewingProject = null"
    >
      <div class="bg-white rounded-[2.2222rem] shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <div class="p-8">
          <div class="flex items-center justify-between mb-6">
            <div>
              <h2 class="text-2xl font-black text-gray-900">{{ viewingProject.name }}</h2>
              <p v-if="viewingProject.description" class="text-sm text-gray-500 mt-1">{{ viewingProject.description }}</p>
            </div>
            <button
              @click="viewingProject = null"
              class="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <XMarkIcon class="w-6 h-6" />
            </button>
          </div>

          <!-- Вкладки -->
          <div class="border-b border-gray-200 mb-6">
            <div class="flex gap-1">
              <button
                @click="activeTab = 'info'"
                :class="activeTab === 'info' ? 'bg-blue-50 text-blue-700 border-blue-200' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'"
                class="px-4 py-2.5 border-b-2 font-semibold text-sm transition-all rounded-t-xl"
              >
                Информация
              </button>
              <button
                @click="activeTab = 'webhook'"
                :class="activeTab === 'webhook' ? 'bg-blue-50 text-blue-700 border-blue-200' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'"
                class="px-4 py-2.5 border-b-2 font-semibold text-sm transition-all rounded-t-xl"
              >
                Webhook
              </button>
              <button
                @click="activeTab = 'leads'"
                :class="activeTab === 'leads' ? 'bg-blue-50 text-blue-700 border-blue-200' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'"
                class="px-4 py-2.5 border-b-2 font-semibold text-sm transition-all rounded-t-xl"
              >
                Заявки
              </button>
              <button
                @click="activeTab = 'manual'"
                :class="activeTab === 'manual' ? 'bg-blue-50 text-blue-700 border-blue-200' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'"
                class="px-4 py-2.5 border-b-2 font-semibold text-sm transition-all rounded-t-xl"
              >
                Ручной ввод
              </button>
            </div>
          </div>

          <!-- Контент вкладок -->
          <div v-if="activeTab === 'info'" class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Описание</label>
              <p class="text-gray-900">{{ viewingProject.description || 'Не указано' }}</p>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Статус</label>
              <span
                :class="viewingProject.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'"
                class="px-2 py-1 text-xs font-medium rounded"
              >
                {{ viewingProject.is_active ? 'Активен' : 'Неактивен' }}
              </span>
            </div>
          </div>

          <div v-if="activeTab === 'webhook'" class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Webhook URL</label>
              <div class="flex items-center gap-2">
                <input
                  :value="webhookFullUrl"
                  readonly
                  class="flex-1 px-4 py-2 border border-gray-300 rounded-lg bg-gray-50"
                />
                <button
                  @click="copyWebhookUrl"
                  class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Копировать
                </button>
              </div>
              <p class="text-xs text-gray-500 mt-1">Используйте этот URL в Tilda и Marquiz — заявки пойдут в квалификацию этого проекта.</p>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Webhook Secret</label>
              <div class="flex items-center gap-2">
                <input
                  :value="viewingProject?.webhook_secret || ''"
                  readonly
                  class="flex-1 px-4 py-2 border border-gray-300 rounded-lg bg-gray-50"
                />
                <button
                  @click="copyWebhookSecret"
                  class="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-800"
                >
                  Копировать
                </button>
              </div>
              <p class="text-xs text-gray-500 mt-1">Добавьте секрет в заголовок <code class="font-mono">X-Webhook-Secret</code></p>
            </div>

            <!-- Инструкции Tilda и Marquiz -->
            <div class="rounded-lg border border-gray-200 bg-gray-50 p-4 space-y-4">
              <h4 class="font-semibold text-gray-900">Подключение Tilda и Marquiz</h4>
              <div class="grid gap-4 md:grid-cols-2">
                <div class="space-y-2">
                  <p class="text-sm font-medium text-gray-700">Tilda</p>
                  <ol class="list-decimal list-inside text-sm text-gray-600 space-y-1">
                    <li>Настройки сайта → Формы → Webhook (или в блоке с формой: Контент → отметьте Webhook)</li>
                    <li>URL: вставьте скопированный Webhook URL этого проекта</li>
                    <li>Формат: JSON. Метод POST. Добавьте заголовок <code class="text-xs">X-Webhook-Secret</code> со значением секрета выше</li>
                    <li>Переопубликуйте страницу</li>
                  </ol>
                  <p class="text-xs text-gray-500">Подробнее: help-ru.tilda.cc/forms/webhook</p>
                </div>
                <div class="space-y-2">
                  <p class="text-sm font-medium text-gray-700">Marquiz</p>
                  <ol class="list-decimal list-inside text-sm text-gray-600 space-y-1">
                    <li>Редактор квиза → Интеграции → Webhook</li>
                    <li>URL: вставьте скопированный Webhook URL этого проекта</li>
                    <li>Добавьте заголовок <code class="text-xs">X-Webhook-Secret</code> со значением секрета выше</li>
                    <li>Сохраните. Заявки будут уходить в квалификацию этого проекта</li>
                  </ol>
                  <p class="text-xs text-gray-500">В Marquiz передаются name, phone, email, UTM и ответы квиза</p>
                </div>
              </div>
            </div>
          </div>

          <div v-if="activeTab === 'leads'" class="space-y-4">
            <div v-if="leadsLoading" class="text-center py-8 text-gray-500">
              <p>Загрузка заявок...</p>
            </div>
            <div v-else-if="leadsError" class="text-center py-8 text-red-500">
              <p>{{ leadsError }}</p>
            </div>
            <div v-else-if="projectLeads.length === 0" class="text-center py-8 text-gray-500">
              <p>Заявок пока нет</p>
            </div>
            <div v-else class="overflow-x-auto">
              <p class="text-xs text-gray-500 mb-2">Нажмите на строку заявки, чтобы посмотреть полную информацию.</p>
              <table class="w-full text-left border-separate border-spacing-y-2">
                <thead>
                  <tr>
                    <th class="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wide">Дата</th>
                    <th class="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wide">Телефон</th>
                    <th class="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wide">Email</th>
                    <th class="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wide">Имя</th>
                    <th class="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wide">Статус</th>
                    <th class="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wide">Причина</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="lead in projectLeads"
                    :key="lead.id"
                    class="bg-gray-50 hover:bg-blue-50 cursor-pointer transition-colors"
                    @click="openLeadDetails(lead)"
                  >
                    <td class="px-3 py-2 text-sm text-gray-700 rounded-l-lg">{{ formatLeadDate(lead.created_at) }}</td>
                    <td class="px-3 py-2 text-sm text-gray-900 font-medium">{{ lead.phone || '—' }}</td>
                    <td class="px-3 py-2 text-sm text-gray-700">{{ lead.email || '—' }}</td>
                    <td class="px-3 py-2 text-sm text-gray-700">{{ lead.name || '—' }}</td>
                    <td class="px-3 py-2 text-sm">
                      <span
                        :class="lead.is_accepted ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'"
                        class="px-2 py-1 rounded-full text-xs font-semibold"
                      >
                        {{ lead.is_accepted ? 'Принята' : 'Отклонена' }}
                      </span>
                    </td>
                    <td class="px-3 py-2 text-xs text-gray-600 rounded-r-lg">{{ lead.rejection_reason || '—' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div v-if="activeTab === 'manual'" class="space-y-4">
            <form @submit.prevent="submitManualLead" class="space-y-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  Телефон <span class="text-red-500">*</span>
                </label>
                <input
                  v-model="manualLeadForm.phone"
                  type="tel"
                  required
                  placeholder="+79991234567"
                  class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  Email
                </label>
                <input
                  v-model="manualLeadForm.email"
                  type="email"
                  placeholder="email@example.com"
                  class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-1">
                  Имя
                </label>
                <input
                  v-model="manualLeadForm.name"
                  type="text"
                  placeholder="Имя"
                  class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <button
                type="submit"
                :disabled="submittingManualLead"
                class="w-full px-4 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-all disabled:opacity-50 font-semibold shadow-sm hover:shadow-md flex items-center justify-center gap-2"
              >
                <span v-if="submittingManualLead" class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                {{ submittingManualLead ? 'Проверка...' : 'Проверить' }}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>

    <!-- Модальное окно деталей заявки -->
    <div
      v-if="selectedLead"
      class="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-[60] p-4"
      @click.self="closeLeadDetails"
    >
      <div class="bg-white rounded-[1.9444rem] shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
        <div class="p-6 sm:p-8">
          <div class="flex items-center justify-between mb-4">
            <div>
              <h3 class="text-xl font-black text-gray-900">Детали заявки</h3>
              <p class="text-xs text-gray-500 mt-1">ID: {{ selectedLead.id }}</p>
            </div>
            <button
              @click="closeLeadDetails"
              class="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <XMarkIcon class="w-6 h-6" />
            </button>
          </div>

          <div v-if="leadDetailsLoading" class="py-8 text-center text-gray-500">
            <p>Загрузка деталей...</p>
          </div>
          <div v-else class="space-y-4">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div class="rounded-xl border border-gray-200 p-3">
                <p class="text-xs font-semibold text-gray-500 uppercase">Контакт</p>
                <p class="text-sm text-gray-900 mt-1">Телефон: {{ selectedLead.phone || '—' }}</p>
                <p class="text-sm text-gray-900">Email: {{ selectedLead.email || '—' }}</p>
                <p class="text-sm text-gray-900">Имя: {{ selectedLead.name || '—' }} {{ selectedLead.surname || '' }}</p>
                <p class="text-sm text-gray-900">Доп. телефоны: 
                  <template v-if="getItpPhones(selectedLead)">
                    {{ getItpPhones(selectedLead).join(', ') }}
                  </template>
                  <template v-else>—</template>
                </p>
              </div>
              <div class="rounded-xl border border-gray-200 p-3">
                <p class="text-xs font-semibold text-gray-500 uppercase">Статус</p>
                <p class="text-sm text-gray-900 mt-1">Принята: {{ formatBool(selectedLead.is_accepted) }}</p>
                <p class="text-sm text-gray-900">Причина: {{ selectedLead.rejection_reason || '—' }}</p>
                <p class="text-sm text-gray-900">Скоринг: {{ selectedLead.lead_score ?? '—' }} / {{ selectedLead.qualification_tier || '—' }}</p>
              </div>
            </div>

            <div class="rounded-xl border border-gray-200 p-3">
              <p class="text-xs font-semibold text-gray-500 uppercase mb-2">Телефонная информация</p>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm text-gray-900">
                <p>Тип: {{ selectedLead.phone_type || '—' }}</p>
                <p>Оператор: {{ selectedLead.phone_provider || selectedLead.main_operator || '—' }}</p>
                <p>Регион: {{ selectedLead.phone_region || '—' }}</p>
                <p>Город: {{ selectedLead.phone_city || '—' }}</p>
                <p>dadata_qc: {{ selectedLead.dadata_qc ?? '—' }}</p>
              </div>
            </div>

            <div class="rounded-xl border border-gray-200 p-3">
              <p class="text-xs font-semibold text-gray-500 uppercase mb-2">UTM и техданные</p>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm text-gray-900">
                <p>utm_source: {{ selectedLead.utm_source || '—' }}</p>
                <p>utm_medium: {{ selectedLead.utm_medium || '—' }}</p>
                <p>utm_campaign: {{ selectedLead.utm_campaign || '—' }}</p>
                <p>utm_content: {{ selectedLead.utm_content || '—' }}</p>
                <p>utm_term: {{ selectedLead.utm_term || '—' }}</p>
                <p>ym_uid: {{ selectedLead.ym_uid || '—' }}</p>
                <p>IP: {{ selectedLead.client_ip || '—' }}</p>
                <p>Referer: {{ selectedLead.referer || '—' }}</p>
              </div>
            </div>

            <div class="rounded-xl border border-gray-200 p-3">
              <p class="text-xs font-semibold text-gray-500 uppercase mb-2">Проверки</p>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm text-gray-900">
                <p>
                  Telegram:
                  <template v-if="getTelegramLabel(selectedLead)">
                    <a
                      :href="getTelegramUrl(selectedLead)"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="text-blue-600 hover:text-blue-700 underline"
                    >
                      {{ getTelegramLabel(selectedLead) }}
                    </a>
                  </template>
                  <template v-else>{{ formatBool(selectedLead.has_telegram) }}</template>
                </p>
                <p>
                  VK:
                  <template v-if="getVkUrl(selectedLead)">
                    <a
                      :href="getVkUrl(selectedLead)"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="text-blue-600 hover:text-blue-700 underline break-all"
                    >
                      {{ getVkLabel(selectedLead) }}
                    </a>
                  </template>
                  <template v-else>{{ formatBool(selectedLead.has_vk) }}</template>
                </p>
                <p>WhatsApp: {{ formatBool(selectedLead.has_whatsapp) }}</p>
                <p>Viber: {{ formatBool(selectedLead.has_viber) }}</p>
                <p>
                  TikTok:
                  <template v-if="getTikTokUrl(selectedLead)">
                    <a
                      :href="getTikTokUrl(selectedLead)"
                      target="_blank"
                      rel="noopener noreferrer"
                      class="text-blue-600 hover:text-blue-700 underline"
                    >
                      {{ getTikTokLabel(selectedLead) }}
                    </a>
                  </template>
                  <template v-else>{{ formatBool(selectedLead.has_tiktok) }}</template>
                </p>
                <div
                  v-if="getItpSocials(selectedLead) && getItpSocials(selectedLead).length"
                  class="mt-2"
                >
                  <p class="text-xs text-gray-500">ITP соцсети (первые 5):</p>
                  <div class="text-xs text-gray-700 space-y-1">
                    <p
                      v-for="(s, idx) in getItpSocials(selectedLead).slice(0, 5)"
                      :key="idx"
                    >
                      {{ s.title || '—' }}: {{ s.url || '—' }}
                    </p>
                  </div>
                </div>
                <p>Госуслуги: {{ formatBool(selectedLead.has_gosuslugi) }}</p>
              </div>
            </div>

            <div class="rounded-xl border border-gray-200 p-3">
              <p class="text-xs font-semibold text-gray-500 uppercase mb-2">Данные для отправки (raw)</p>
              <pre class="text-xs bg-gray-50 border border-gray-100 rounded-lg p-3 overflow-auto">{{ leadDetailsJson }}</pre>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div
      v-if="deleteTarget"
      class="fixed inset-0 bg-black/45 backdrop-blur-sm flex items-center justify-center z-[70] p-4"
      @click.self="deleteTarget = null"
    >
      <div class="w-full max-w-md rounded-[1.5rem] bg-white border border-gray-100 shadow-2xl p-6">
        <h3 class="text-xl font-black text-gray-900">Удалить проект?</h3>
        <p class="text-sm text-gray-500 mt-2 leading-relaxed">
          Проект «{{ deleteTarget.name }}» будет удален безвозвратно.
        </p>
        <div class="flex justify-end gap-3 mt-6">
          <button
            type="button"
            class="px-5 py-3 rounded-xl border border-gray-200 text-sm font-bold text-gray-600 hover:bg-gray-50 transition-colors"
            @click="deleteTarget = null"
          >
            Отмена
          </button>
          <button
            type="button"
            class="px-5 py-3 rounded-xl bg-red-600 text-white text-sm font-bold hover:bg-red-700 transition-colors"
            @click="confirmDeleteProject"
          >
            Удалить
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useToaster } from '@/composables/useToaster'
import api from '@/api/axios'
import { PhoneIcon, PlusIcon, LinkIcon, TrashIcon, XMarkIcon } from '@heroicons/vue/24/outline'

const toaster = useToaster()
const projects = ref([])
const clients = ref([])
const loading = ref(true)
const saving = ref(false)
const showCreateModal = ref(false)
const editingProject = ref(null)
const viewingProject = ref(null)
const activeTab = ref('info')
const submittingManualLead = ref(false)
const emailRecipientsInput = ref('')
const projectLeads = ref([])
const leadsLoading = ref(false)
const leadsError = ref('')
const selectedLead = ref(null)
const leadDetailsLoading = ref(false)
const deleteTarget = ref(null)

const projectForm = reactive({
  name: '',
  description: '',
  client_id: null,
  crm_webhook_url: '',
  email_recipients: [],
  telegram_chat_id: '',
  enable_social_check: false,
  enable_lead_scoring: false,
  enable_gosuslugi_check: false,
  enable_spam_check: true,
  enable_bitrix_check: false,
  enable_metrica_export: true
})

const manualLeadForm = reactive({
  phone: '',
  email: '',
  name: ''
})
const manualLeadJsToken = ref(generateJsToken())
const manualLeadStartTs = ref(Math.floor(Date.now() / 1000))

// Всегда показываем URL по id проекта (не зависим от webhook_url с бэкенда)
const webhookFullUrl = computed(() => {
  const p = viewingProject.value
  if (!p || p.id == null || p.id === undefined) return ''
  const base = window.location?.origin ?? ''
  if (!base) return ''
  return `${base}/api/webhook/phone/${p.id}`
})

function generateJsToken() {
  if (window?.crypto?.getRandomValues) {
    const bytes = new Uint8Array(16)
    window.crypto.getRandomValues(bytes)
    return Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('')
  }
  return Math.random().toString(36).slice(2) + Math.random().toString(36).slice(2)
}

onMounted(async () => {
  await Promise.all([fetchProjects(), fetchClients()])
})

const fetchProjects = async () => {
  try {
    loading.value = true
    const response = await api.get('phone-projects/')
    projects.value = response.data
  } catch (error) {
    console.error('Error fetching projects:', error)
    toaster.error('Не удалось загрузить проекты')
  } finally {
    loading.value = false
  }
}

const fetchClients = async () => {
  try {
    const response = await api.get('clients/')
    clients.value = response.data
  } catch (error) {
    console.error('Error fetching clients:', error)
  }
}

const saveProject = async () => {
  try {
    saving.value = true
    
    // Преобразуем email_recipients из строки в массив
    const emailRecipients = emailRecipientsInput.value
      .split(',')
      .map(email => email.trim())
      .filter(email => email)
    
    const payload = {
      ...projectForm,
      email_recipients: emailRecipients.length > 0 ? emailRecipients : null
    }

    if (editingProject.value) {
      await api.put(`phone-projects/${editingProject.value.id}`, payload)
      toaster.success('Проект обновлен')
    } else {
      await api.post('phone-projects/', payload)
      toaster.success('Проект создан')
    }

    closeModal()
    await fetchProjects()
  } catch (error) {
    console.error('Error saving project:', error)
    toaster.error(error.response?.data?.detail || 'Не удалось сохранить проект')
  } finally {
    saving.value = false
  }
}

const editProject = (project) => {
  editingProject.value = project
  projectForm.name = project.name
  projectForm.description = project.description || ''
  projectForm.client_id = project.client_id
  projectForm.crm_webhook_url = project.crm_webhook_url || ''
  projectForm.email_recipients = project.email_recipients || []
  emailRecipientsInput.value = project.email_recipients?.join(', ') || ''
  projectForm.telegram_chat_id = project.telegram_chat_id || ''
  projectForm.enable_social_check = project.enable_social_check || false
  projectForm.enable_lead_scoring = project.enable_lead_scoring || false
  projectForm.enable_gosuslugi_check = project.enable_gosuslugi_check || false
  projectForm.enable_spam_check = project.enable_spam_check !== false
  projectForm.enable_bitrix_check = project.enable_bitrix_check || false
  projectForm.enable_metrica_export = project.enable_metrica_export !== false
  showCreateModal.value = true
}

const viewProject = async (project) => {
  if (!project?.id) return
  viewingProject.value = project
  activeTab.value = 'info'
  try {
    const { data } = await api.get(`phone-projects/${project.id}`)
    viewingProject.value = data
  } catch (e) {
    // оставляем данные из списка
  }
}

const fetchProjectLeads = async () => {
  if (!viewingProject.value?.id) return
  try {
    leadsLoading.value = true
    leadsError.value = ''
    const { data } = await api.get('phone-leads/', {
      params: { project_id: viewingProject.value.id }
    })
    projectLeads.value = Array.isArray(data) ? data : []
  } catch (error) {
    console.error('Error fetching project leads:', error)
    leadsError.value = 'Не удалось загрузить заявки'
  } finally {
    leadsLoading.value = false
  }
}

const openLeadDetails = async (lead) => {
  if (!lead?.id) return
  selectedLead.value = { ...lead }
  try {
    leadDetailsLoading.value = true
    const { data } = await api.get(`phone-leads/${lead.id}`)
    selectedLead.value = data || { ...lead }
  } catch (error) {
    console.error('Error fetching lead details:', error)
    toaster.error('Не удалось загрузить детали заявки')
  } finally {
    leadDetailsLoading.value = false
  }
}

const closeLeadDetails = () => {
  selectedLead.value = null
  leadDetailsLoading.value = false
}

const deleteProject = (project) => {
  deleteTarget.value = project
}

const confirmDeleteProject = async () => {
  if (!deleteTarget.value?.id) return
  try {
    await api.delete(`phone-projects/${deleteTarget.value.id}`)
    toaster.success('Проект удален')
    deleteTarget.value = null
    await fetchProjects()
  } catch (error) {
    console.error('Error deleting project:', error)
    toaster.error('Не удалось удалить проект')
  }
}

const closeModal = () => {
  showCreateModal.value = false
  editingProject.value = null
  // Сброс формы
  Object.assign(projectForm, {
    name: '',
    description: '',
    client_id: null,
    crm_webhook_url: '',
    email_recipients: [],
    telegram_chat_id: '',
    enable_social_check: false,
    enable_lead_scoring: false,
    enable_gosuslugi_check: false,
    enable_spam_check: true,
    enable_bitrix_check: false,
    enable_metrica_export: true
  })
  emailRecipientsInput.value = ''
}

const copyWebhookUrl = async () => {
  try {
    await navigator.clipboard.writeText(webhookFullUrl.value)
    toaster.success('Webhook URL скопирован в буфер обмена')
  } catch (error) {
    toaster.error('Не удалось скопировать URL')
  }
}

const copyWebhookSecret = async () => {
  try {
    const secret = viewingProject.value?.webhook_secret || ''
    if (!secret) {
      toaster.error('Webhook secret недоступен')
      return
    }
    await navigator.clipboard.writeText(secret)
    toaster.success('Webhook secret скопирован в буфер обмена')
  } catch (error) {
    toaster.error('Не удалось скопировать secret')
  }
}

const submitManualLead = async () => {
  if (!manualLeadForm.phone) {
    toaster.error('Введите телефон')
    return
  }

  try {
    submittingManualLead.value = true
    
    // Отправляем на webhook проекта
    const webhookUrl = viewingProject.value?.webhook_url
    if (!webhookUrl) {
      toaster.error('Webhook URL не настроен для этого проекта')
      return
    }

    const payload = {
      phone: manualLeadForm.phone,
      email: manualLeadForm.email || undefined,
      name: manualLeadForm.name || undefined,
      js_token: manualLeadJsToken.value,
      timestamp: manualLeadStartTs.value,
      source: 'Ручной ввод'
    }

    const webhookSecret = viewingProject.value?.webhook_secret
    const headers = webhookSecret ? { 'X-Webhook-Secret': webhookSecret } : {}
    // webhookUrl вида "/webhook/phone/{id}" — убираем ведущий слэш для baseURL /api/
    const path = webhookUrl.startsWith('/') ? webhookUrl.slice(1) : webhookUrl
    await api.post(path, payload, { headers })
    toaster.success('Заявка отправлена на проверку')
    if (activeTab.value === 'leads') {
      await fetchProjectLeads()
    }
    
    // Сброс формы
    Object.assign(manualLeadForm, {
      phone: '',
      email: '',
      name: ''
    })
    manualLeadJsToken.value = generateJsToken()
    manualLeadStartTs.value = Math.floor(Date.now() / 1000)
  } catch (error) {
    console.error('Error submitting manual lead:', error)
    toaster.error(error.response?.data?.detail || 'Не удалось отправить заявку')
  } finally {
    submittingManualLead.value = false
  }
}

const formatLeadDate = (value) => {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleString('ru-RU')
}

const formatBool = (v) => {
  if (v === true) return 'Да'
  if (v === false) return 'Нет'
  return '—'
}

const leadDetailsJson = computed(() => {
  if (!selectedLead.value) return '{}'
  try {
    return JSON.stringify(selectedLead.value, null, 2)
  } catch (e) {
    return '{}'
  }
})

const getSocialData = (lead, key) => {
  const root = lead?.social_accounts_data
  if (!root || typeof root !== 'object') return null
  const entry = root[key]
  return entry && typeof entry === 'object' ? entry : null
}

const getItpPhones = (lead) => {
  const root = lead?.social_accounts_data
  if (!root || typeof root !== 'object') return null
  const phones = root?.itp_phones
  if (!Array.isArray(phones) || phones.length === 0) return null
  return phones
}

const getItpSocials = (lead) => {
  const root = lead?.social_accounts_data
  if (!root || typeof root !== 'object') return null
  const socials = root?.itp_socials
  if (!Array.isArray(socials) || socials.length === 0) return null
  return socials
}

const toSafeUrl = (raw, preferredProtocol = 'https') => {
  if (!raw || typeof raw !== 'string') return null
  const value = raw.trim()
  if (!value) return null
  if (value.startsWith('http://') || value.startsWith('https://')) return value
  if (value.startsWith('//')) return `${preferredProtocol}:${value}`
  return `${preferredProtocol}://${value}`
}

const getTelegramUsername = (lead) => {
  const tg = getSocialData(lead, 'telegram')
  if (!tg) return null
  const candidate = (tg.username || tg.from_form || '').toString().trim()
  if (!candidate) return null
  return candidate.replace(/^@/, '').replace(/^https?:\/\/t\.me\//i, '').replace(/\/+$/, '')
}

const getTelegramUrl = (lead) => {
  const username = getTelegramUsername(lead)
  if (!username) return null
  return `https://t.me/${username}`
}

const getTelegramLabel = (lead) => {
  const username = getTelegramUsername(lead)
  return username ? `@${username}` : null
}

const getVkUrl = (lead) => {
  const vk = getSocialData(lead, 'vk')
  if (!vk) return null
  const candidate = (vk.profile_url || vk.from_form || '').toString().trim()
  return toSafeUrl(candidate)
}

const getVkLabel = (lead) => {
  const url = getVkUrl(lead)
  if (!url) return null
  return url.replace(/^https?:\/\//i, '')
}

const getTikTokUsername = (lead) => {
  const tt = getSocialData(lead, 'tiktok')
  if (!tt) return null
  const candidate = (tt.username || tt.from_form || '').toString().trim()
  if (!candidate) return null
  return candidate.replace(/^@/, '').replace(/^https?:\/\/(www\.)?tiktok\.com\/@?/i, '').replace(/\/+$/, '')
}

const getTikTokUrl = (lead) => {
  const username = getTikTokUsername(lead)
  if (!username) return null
  return `https://www.tiktok.com/@${username}`
}

const getTikTokLabel = (lead) => {
  const username = getTikTokUsername(lead)
  return username ? `@${username}` : null
}

watch(activeTab, async (tab) => {
  if (tab === 'leads' && viewingProject.value?.id) {
    await fetchProjectLeads()
  }
})
</script>
