<template>
  <section ref="pageRef" class="assistant-page" :class="{ 'assistant-page--dark': isDarkMode }">
    <aside class="assistant-rail" :class="{ 'assistant-rail--open': railOpen }" aria-label="История ассистента">
      <div v-if="!railOpen" class="assistant-rail__compact">
        <button class="rail-icon-button" type="button" title="Открыть историю" aria-label="Открыть историю" @click="railOpen = true">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 7h14M5 12h14M5 17h9"/></svg>
        </button>
        <button class="rail-icon-button" type="button" title="Новый диалог" aria-label="Новый диалог" @click="newChat">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>
        </button>
        <button class="rail-icon-button" type="button" title="Поиск по чатам" aria-label="Поиск по чатам" @click="openChatSearch">
          <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.8" cy="10.8" r="5.8"/><path d="m15.2 15.2 4 4"/></svg>
        </button>
      </div>

      <div v-else class="assistant-rail__expanded">
        <div class="rail-heading">
          <span>История</span>
          <button class="rail-icon-button" type="button" title="Свернуть историю" aria-label="Свернуть историю" @click="railOpen = false">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m14.5 6-6 6 6 6"/></svg>
          </button>
        </div>

        <button class="rail-new-chat" type="button" @click="newChat">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>
          <span>Новый диалог</span>
        </button>

        <label class="rail-search">
          <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.8" cy="10.8" r="5.8"/><path d="m15.2 15.2 4 4"/></svg>
          <input ref="historySearchInput" v-model="historySearch" type="search" placeholder="Поиск по чатам" aria-label="Поиск по чатам" />
        </label>

        <div class="rail-history">
          <button
            v-for="conv in filteredConversations"
            :key="conv.id"
            type="button"
            class="rail-history__item"
            :class="{ 'is-active': conv.id === activeConversationId }"
            :title="conv.title"
            @click="selectConversation(conv.id)"
          >
            <span class="rail-history__title">{{ conv.title || 'Без названия' }}</span>
            <span class="rail-history__date">{{ formatChatDate(conv.updated_at) }}</span>
          </button>

          <div v-if="!conversations.length" class="rail-history__empty">Здесь появятся ваши вопросы.</div>
          <div v-else-if="!filteredConversations.length" class="rail-history__empty">Ничего не найдено.</div>
        </div>
      </div>
    </aside>

    <section class="assistant-stage" aria-label="AI-ассистент">
      <div v-if="!hasThread" ref="emptyScroll" class="assistant-empty">
        <div class="assistant-hero">
          <h2 class="assistant-hero__title">Спросите про свою рекламу</h2>
          <p class="assistant-hero__sub">{{ projectContextDescription }}</p>
          <p v-if="!configured" class="assistant-welcome__note">Ассистент скоро будет доступен — подключается модель.</p>

          <div class="assistant-composer">
            <textarea
              ref="textarea"
              v-model="prompt"
              rows="1"
              aria-label="Запрос ассистенту"
              placeholder="Назовите проект и задайте вопрос — например: посчитай CPL по Директу за июль"
              @input="autoGrow"
              @keydown.enter.exact.prevent="sendPrompt"
            ></textarea>
            <div class="assistant-composer__actions">
              <div v-if="selectedModel.reasoning" class="assistant-model" :class="{ 'assistant-model--open': effortMenuOpen }" v-click-outside="() => (effortMenuOpen = false)">
                <button type="button" class="assistant-model__btn" :aria-expanded="effortMenuOpen" aria-haspopup="listbox" @click="effortMenuOpen = !effortMenuOpen">
                  <span>Уровень размышлений · <b>{{ effortLabel }}</b></span>
                  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m7 10 5 5 5-5"/></svg>
                </button>
                <div v-if="effortMenuOpen" class="assistant-model__menu" role="listbox" aria-label="Выбор уровня размышлений">
                  <button v-for="e in selectedModel.efforts" :key="e" type="button" :class="{ 'is-active': e === selectedEffort }" @click="pickEffort(e)">{{ effortName(e) }}</button>
                </div>
              </div>
              <button class="composer-send" type="button" :aria-label="sending ? 'Остановить' : 'Отправить'" :class="{ 'is-active': prompt.trim() && !sending, 'composer-send--stop': sending }" @click="sending ? stopGeneration() : sendPrompt()">
                <svg v-if="!sending" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 18V6m0 0 4.5 4.5M12 6l-4.5 4.5"/></svg>
                <svg v-else viewBox="0 0 24 24" aria-hidden="true"><rect x="7" y="7" width="10" height="10" rx="2"/></svg>
              </button>
            </div>
          </div>

          <div class="assistant-sources-row">
            <span class="assistant-sources-row__label">Откуда беру данные</span>
            <div class="assistant-sources-row__pills">
              <span v-for="s in dataSources" :key="s.id" class="source-pill" :class="{ 'source-pill--off': !s.available }" :title="s.available ? s.description : (s.unavailableLabel || 'скоро')">
                <span class="source-pill__mark">
                  <img v-if="s.icon" :src="s.icon" :alt="s.name" />
                  <svg v-else-if="s.id === 'wordstat'" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 18.5V13m4.7 5.5V9m4.6 9.5V5.5M18.5 18.5v-7" /></svg>
                </span>
                <span class="source-pill__name">{{ s.name }}</span>
                <i class="source-pill__dot" :class="{ 'is-on': s.available }"></i>
              </span>
            </div>
          </div>

        </div>

        <div class="assistant-prompts">
          <h3 class="assistant-prompts__title">Спросите одним кликом</h3>
          <div class="assistant-prompts__grid">
            <div
              v-for="(p, i) in readyPrompts"
              :key="i"
              class="prompt-tile"
              role="button"
              tabindex="0"
              @click="fillPrompt(p.prompt)"
              @keydown.enter.prevent="fillPrompt(p.prompt)"
            >
              <div class="prompt-tile__head">
                <b class="prompt-tile__title">{{ p.title }}</b>
                <button
                  type="button"
                  class="prompt-tile__copy"
                  :class="{ 'is-copied': copiedIndex === i }"
                  :aria-label="copiedIndex === i ? 'Скопировано' : 'Скопировать промпт'"
                  @click.stop="copyPrompt(p.prompt, i)"
                >
                  <svg v-if="copiedIndex !== i" viewBox="0 0 24 24" aria-hidden="true"><rect x="9" y="9" width="11" height="11" rx="2.2"/><path d="M5 15V6.5A2.5 2.5 0 0 1 7.5 4H16"/></svg>
                  <svg v-else viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12.5 4.4 4.4L19 7.2"/></svg>
                </button>
              </div>
              <span class="prompt-tile__desc">{{ p.desc }}</span>
              <span class="prompt-tile__service" :class="`prompt-tile__service--${p.service}`" aria-hidden="true">
                <img v-if="serviceIcon(p.service)" :src="serviceIcon(p.service)" :alt="p.service" />
                <svg v-else viewBox="0 0 24 24"><path d="M5 18.5V13m4.7 5.5V9m4.6 9.5V5.5M18.5 18.5v-7"/></svg>
              </span>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="assistant-thread">
        <div ref="threadInner" class="assistant-thread__inner" @scroll.passive="onThreadScroll">
          <TransitionGroup name="chat-message" tag="div" class="assistant-thread__messages">
            <article v-for="message in activeMessages" :key="message.id" :class="['assistant-message', `assistant-message--${message.role}`]">
              <template v-if="message.role === 'assistant'">
                <span class="assistant-message__avatar" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="m12 3 1.6 5.4L19 10l-5.4 1.6L12 17l-1.6-5.4L5 10l5.4-1.6L12 3Z"/></svg></span>
                <div class="assistant-message__body">
                  <div class="assistant-message__label">AdMirra AI</div>
                  <details v-if="message.reasoning" class="assistant-reasoning" :open="message.pending && !message.content">
                    <summary>
                      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3a6 6 0 0 0-3.5 10.9c.5.4.8 1 .8 1.6v.5h5.4v-.5c0-.6.3-1.2.8-1.6A6 6 0 0 0 12 3Z"/><path d="M9.3 20h5.4M10 17.5h4"/></svg>
                      <span>{{ message.pending && !message.content ? 'Размышляет…' : 'Размышления' }}</span>
                    </summary>
                    <div class="assistant-reasoning__text">{{ message.reasoning }}</div>
                  </details>
                  <div class="assistant-message__bubble">
                    <div v-if="message.content" class="assistant-markdown" v-html="renderMarkdown(message.content)"></div>
                    <div v-else-if="message.pending && !message.reasoning" class="assistant-typing" aria-label="Ассистент готовит ответ"><i></i><i></i><i></i></div>
                    <div v-if="message.pending && toolActivity" class="assistant-tool-note"><span></span>Читаю данные: {{ toolActivity }}</div>
                  </div>
                </div>
              </template>
              <div v-else class="assistant-message__bubble"><p>{{ message.content }}</p></div>
            </article>
          </TransitionGroup>
        </div>

        <div class="assistant-thread__composer">
          <div class="assistant-composer">
            <textarea
              ref="threadTextarea"
              v-model="prompt"
              rows="1"
              aria-label="Уточнить вопрос"
              placeholder="Уточните: «за прошлую неделю», «только по Директу»…"
              @input="autoGrow"
              @keydown.enter.exact.prevent="sendPrompt"
            ></textarea>
            <div class="assistant-composer__actions">
              <div v-if="selectedModel.reasoning" class="assistant-model" :class="{ 'assistant-model--open': effortMenuOpen }" v-click-outside="() => (effortMenuOpen = false)">
                <button type="button" class="assistant-model__btn" :aria-expanded="effortMenuOpen" aria-haspopup="listbox" @click="effortMenuOpen = !effortMenuOpen">
                  <span>Уровень размышлений · <b>{{ effortLabel }}</b></span>
                  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m7 10 5 5 5-5"/></svg>
                </button>
                <div v-if="effortMenuOpen" class="assistant-model__menu assistant-model__menu--up" role="listbox" aria-label="Выбор уровня размышлений">
                  <button v-for="e in selectedModel.efforts" :key="e" type="button" :class="{ 'is-active': e === selectedEffort }" @click="pickEffort(e)">{{ effortName(e) }}</button>
                </div>
              </div>
              <button class="composer-send" type="button" :aria-label="sending ? 'Остановить' : 'Отправить'" :class="{ 'is-active': prompt.trim() && !sending, 'composer-send--stop': sending }" @click="sending ? stopGeneration() : sendPrompt()"><svg v-if="!sending" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 18V6m0 0 4.5 4.5M12 6l-4.5 4.5"/></svg><svg v-else viewBox="0 0 24 24" aria-hidden="true"><rect x="7" y="7" width="10" height="10" rx="2"/></svg></button>
            </div>
          </div>
        </div>
      </div>
    </section>
  </section>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import MarkdownIt from 'markdown-it'
import { useTheme } from '../../composables/useTheme'
import api from '../../api/axios'
import { getAccessToken } from '../../utils/authToken'
import yandexMetrikaIcon from '../../assets/icons/yandex-metrika.png'

const { isDarkMode } = useTheme()

const railOpen = ref(false)
const prompt = ref('')
const pageRef = ref(null)
const textarea = ref(null)
const threadTextarea = ref(null)
const threadInner = ref(null)
const historySearchInput = ref(null)
const sending = ref(false)
const toolActivity = ref('')
const wordstatConfigured = ref(false)
let abortController = null
let messageSequence = 0

// raw HTML в ответах модели выключен: MarkdownIt безопасно экранирует его.
// Так сохраняются заголовки, списки, таблицы, ссылки и кодовые блоки без XSS.
const markdown = new MarkdownIt({ html: false, breaks: true, linkify: true, typographer: true })
const renderMarkdown = (value) => markdown.render(String(value || ''))
const nextMessageId = (prefix = 'local') => `${prefix}-${Date.now()}-${++messageSequence}`

// ── Модели и режим размышлений (из GET /assistant/models) ────────────────────
const models = ref([])
const configured = ref(true)
const selectedModelId = ref('')
const modelMenuOpen = ref(false)
const effortMenuOpen = ref(false)
const selectedEffort = ref('medium')
const FALLBACK_MODEL = { id: '', label: '—', description: '', reasoning: false, efforts: [], default_effort: null }
const selectedModel = computed(() => models.value.find((m) => m.id === selectedModelId.value) || models.value[0] || FALLBACK_MODEL)
const EFFORT_LABELS = { none: 'Выкл', low: 'Низкая', medium: 'Средняя', high: 'Высокая' }
const effortName = (e) => EFFORT_LABELS[e] || e
const effortLabel = computed(() => effortName(selectedEffort.value))

const syncEffortToModel = () => {
  const m = selectedModel.value
  if (!m.reasoning) { selectedEffort.value = 'none'; return }
  if (!m.efforts.includes(selectedEffort.value)) selectedEffort.value = m.default_effort || 'medium'
}
const pickModel = (id) => { selectedModelId.value = id; modelMenuOpen.value = false; syncEffortToModel() }
const pickEffort = (e) => { selectedEffort.value = e; effortMenuOpen.value = false }

// Локальная директива v-click-outside (глобально в проекте не зарегистрирована).
const vClickOutside = {
  mounted(el, binding) {
    el._outsideHandler = (event) => { if (!el.contains(event.target)) binding.value(event) }
    document.addEventListener('mousedown', el._outsideHandler)
  },
  unmounted(el) { document.removeEventListener('mousedown', el._outsideHandler) },
}

const projectContextDescription = 'Назовите проект или спросите, какие доступны — и я проанализирую его рекламу: расход, лиды, CPL, цели Метрики. Ещё умею Wordstat.'

// ── Экран приветствия: источники данных и готовые промпты ────────────────────
const dataSources = computed(() => [
  { id: 'yandex-direct', name: 'Яндекс Директ', description: 'Расход и кампании', icon: '/admirra/img/icons/yandex-direct.png', available: true },
  { id: 'metrika', name: 'Яндекс Метрика', description: 'Цели и конверсии', icon: yandexMetrikaIcon, available: true },
  { id: 'wordstat', name: 'Wordstat', description: 'Спрос и семантика', icon: '/admirra/img/icons/wordstat.webp', available: wordstatConfigured.value, unavailableLabel: 'не подключён' },
  { id: 'avito', name: 'Avito Ads', description: 'Кампании и расход', icon: '/admirra/img/icons/avito.svg', available: true },
  { id: 'vk', name: 'VK Реклама', description: 'Кампании и расход', icon: '/admirra/img/icons/vk-ads.png', available: true },
])

// Макетные готовые промпты (реальные добавим позже). Клик по плитке — вставить
// в поле ввода, кнопка копирования — скопировать текст промпта.
// Иконки сервисов для плиток промптов (реюз ассетов источников).
const SERVICE_ICON = {
  direct: '/admirra/img/icons/yandex-direct.png',
  metrika: yandexMetrikaIcon,
  vk: '/admirra/img/icons/vk-ads.png',
  avito: '/admirra/img/icons/avito.svg',
  wordstat: '/admirra/img/icons/wordstat.webp',
}
const serviceIcon = (service) => SERVICE_ICON[service] || null

// Готовые промпты по всем сервисам. Клик — полный структурированный запрос
// уходит в поле ввода. Тексты адаптированы под наш ассистент (live-инструменты).
const readyPrompts = [
  // ── Яндекс Директ ──
  { service: 'direct', title: 'Аудит Директа', desc: 'Проверяет кампании, расходы, конверсии и явные проблемы.',
    prompt: 'Сделай аудит Яндекс.Директа: кампании, группы, объявления, ключевые фразы, бюджеты и отчёты. Найди перерасход, низкую конверсию, дорогие лиды, резкие изменения и странную структуру. Период по умолчанию — последние 30 дней (если в данных доступен другой — используй его и укажи это). Покажи: какие данные проверял (аккаунт, период); таблицу проблем (объект, показатель, что не так, возможная причина, приоритет, рекомендация); короткую сводку по главным показателям; 3–5 первых действий для ручной проверки. Если данных не хватает — прямо напиши это и предложи ближайшую полезную проверку.' },
  { service: 'direct', title: 'Контроль бюджета Директа', desc: 'Где бюджет расходуется слишком быстро или почти не работает.',
    prompt: 'Проверь бюджеты и темп расхода Яндекс.Директа: какие кампании расходуют бюджет быстрее плана, какие почти не получают трафик, где расход есть, а результата нет. Период — текущий месяц и последние 7 дней. Покажи таблицу (кампания, расход, результат, средний дневной расход, риск, рекомендация), отдельный список кампаний для срочной ручной проверки и 3–5 первых действий для улучшения бюджета. Если данных не хватает — напиши прямо.' },
  { service: 'direct', title: 'Поиск лишних расходов', desc: 'Ищет фразы и группы, где расход есть, а результата мало.',
    prompt: 'Найди лишние расходы в Яндекс.Директе: сравни расход, клики, заявки/продажи и стоимость результата. Период — последние 30 дней. Покажи таблицу (кампания/группа/фраза, расход, клики, результат, стоимость результата, проблема, ручная проверка), сегменты сгруппируй по приоритету, добавь список первых ручных проверок. Если данных не хватает — напиши прямо.' },
  { service: 'direct', title: 'Качество заявок из Директа', desc: 'Показывает, какие кампании дают больше полезных заявок.',
    prompt: 'Проанализируй качество заявок из Яндекс.Директа: сравни кампании и группы по лидам, стоимости лида и доступным признакам качества. Период — последние 30 дней. Конверсии считай по отслеживаемым целям проекта. Покажи таблицу по кампаниям (лиды, стоимость лида, признаки качества, проблемы, рекомендации), список данных, которых не хватает для точной оценки, и общие выводы по группам заявок. Если данных не хватает — напиши прямо.' },
  { service: 'direct', title: 'Месячный отчёт Директа', desc: 'Собирает большой управленческий отчёт за месяц.',
    prompt: 'Подготовь месячный отчёт по Яндекс.Директу для руководителя и маркетолога за последний полный календарный месяц. Начни с executive summary (5–7 пунктов): общий расход, результат, стоимость заявки, изменение к прошлому периоду, кампании-драйверы, источники потерь, вывод по месяцу. Дай таблицу кампаний (расход, клики, конверсии/лиды, CPA/CPL, доля бюджета, динамика, статус, проблема/точка роста, действие); выдели кампании с высоким расходом и малым результатом, с просадкой и с потенциалом масштабирования. Собери блок рекомендаций (срочные, плановые, гипотезы) с ожидаемым эффектом и финальный чек-лист из 7–10 действий. Цифры не выдумывай: пробелы отмечай явно.' },
  // ── Wordstat / семантика ──
  { service: 'wordstat', title: 'Семантическое ядро', desc: 'Собирает базовые фразы, кластеры и минус-темы по продукту и региону.',
    prompt: 'Собери семантическое ядро для продукта или услуги проекта через Wordstat. Если регион не указан — сделай аккуратное допущение и явно подпиши его. Покажи кластеры (коммерческие, информационные, брендовые, конкуренты, минус-темы), для каждого — примеры фраз и приоритет, и список уточнений, если не хватает региона или тематики.' },
  { service: 'wordstat', title: 'Минус-темы', desc: 'Находит нерелевантные темы и мусорные запросы для ручной проверки.',
    prompt: 'Подбери минус-темы и мусорные запросы для тематики через Wordstat. Группируй только то, что есть в данных или явно следует из контекста. Покажи таблицу (минус-тема, примеры фраз, причина исключения, риск ошибки, приоритет ручной проверки), отдельный список спорных тем и список первых ручных проверок.' },
  { service: 'wordstat', title: 'Спрос по регионам', desc: 'Сравнивает спрос по регионам для рекламы или поиска.',
    prompt: 'Оцени спрос по регионам для тематики через Wordstat. Если список регионов не задан — предложи разумный набор крупных регионов и отметь это как допущение. Покажи таблицу (регион, уровень спроса, сильные темы, слабые темы, риск нерелевантности, рекомендация), список регионов для глубокой проверки и допущения по географии.' },
  { service: 'wordstat', title: 'Расширение кластеров', desc: 'Находит новые кластеры спроса вокруг текущей тематики.',
    prompt: 'Найди новые кластеры спроса вокруг текущей тематики через Wordstat. Раздели их на быстрый рекламный запуск, поиск/контент, спорные гипотезы и нерелевантные темы. Покажи таблицу кластеров (приоритет, примеры фраз, намерение пользователя, риски, следующие шаги), отдельный список спорных гипотез и что можно оценить только после дополнительной проверки.' },
  // ── Яндекс Метрика ──
  { service: 'metrika', title: 'Аудит трафика и целей', desc: 'Проверяет каналы, цели и просадки в Яндекс.Метрике.',
    prompt: 'Сделай аудит трафика и целей в Яндекс.Метрике: источники трафика, цели, конверсия, отказы, резкие изменения и сегменты с потерями. Период — последние 30 дней. Конверсии считай по отслеживаемым целям проекта. Покажи таблицу (канал/сегмент, трафик, конверсия, проблема, возможная причина, рекомендация), список подозрительных целей, использованный период и счётчик. Если данных не хватает — напиши прямо.' },
  { service: 'metrika', title: 'Страницы с потерей конверсии', desc: 'Находит страницы, где много трафика, но слабый результат.',
    prompt: 'Найди страницы сайта, где много визитов, но низкая конверсия или высокая доля отказов (Яндекс.Метрика). Период — последние 30 дней. Сравни страницы между собой. Покажи таблицу (страница, визиты, конверсия, отказы, проблема, рекомендация), топ страниц для первичной ручной проверки и ограничения по выбранным целям.' },
  { service: 'metrika', title: 'Сравнение каналов', desc: 'Сравнивает каналы трафика по целям и качеству визитов.',
    prompt: 'Сравни каналы трафика в Метрике по визитам, целям, конверсии и отказам. Период — последние 30 дней. Покажи таблицу (канал, визиты, цели, конверсия, качество, вывод), какие каналы усиливать, а какие проверить, и какие цели использовались. Если данных не хватает — напиши прямо.' },
  { service: 'metrika', title: 'Посадочные страницы', desc: 'Откуда трафик и какие страницы конвертят лучше.',
    prompt: 'Проанализируй посадочные страницы (Яндекс.Метрика): откуда приходит трафик, какие страницы конвертируют лучше, где есть трафик без результата. Период — последние 30 дней. Покажи таблицу (посадочная, канал, визиты, цель, конверсия, проблема, рекомендация), страницы, где стоит вручную сравнить варианты, и ограничения по данным.' },
  // ── VK Реклама ──
  { service: 'vk', title: 'Аудит VK Рекламы', desc: 'Проверяет кампании, группы, баннеры и показатели.',
    prompt: 'Сделай аудит VK Рекламы: кампании, группы, баннеры, показы, клики, лиды и другие доступные показатели результата. Период — последние 30 дней. Покажи таблицу (кампания/группа/баннер, показатели, проблема, причина, рекомендация), приоритеты ручной проверки и что проверить перед изменением ставок, бюджетов и объявлений. Если данных не хватает — напиши прямо.' },
  { service: 'vk', title: 'Лид-формы VK', desc: 'Сравнивает формы по объёму, качеству и стоимости заявок.',
    prompt: 'Проанализируй лид-формы VK Рекламы: сравни формы по объёму лидов, качеству, стоимости или доступным признакам результата. Период — последние 30 дней. Покажи таблицу (форма, заявки, стоимость/качество если доступно, проблема, рекомендация), что нужно из системы продаж для точной оценки и общие выводы по формам заявок.' },
  { service: 'vk', title: 'Креативы VK', desc: 'CTR, расход без результата и что стоит обновить.',
    prompt: 'Сравни баннеры и креативы VK Рекламы: найди низкий CTR (долю кликов от показов), высокий расход без результата, резкую просадку и хороший потенциал роста. Период — последние 30 дней. Покажи таблицу (баннер/группа, показы, клики, CTR, результат, вывод, рекомендация), креативы для обновления и что проверить перед обновлением.' },
  { service: 'vk', title: 'Обзор аккаунта VK', desc: 'Что в кабинете, какая статистика и что требует внимания.',
    prompt: 'Подготовь обзор аккаунта VK Рекламы: какие кампании, группы и баннеры есть в кабинете, какая по ним статистика и что требует внимания. Период статистики — последние 30 дней. Покажи, какие данные удалось посмотреть, краткий обзор кампаний/групп/баннеров и что важно проверить вручную.' },
  // ── Avito Реклама ──
  { service: 'avito', title: 'Аудит Avito Рекламы', desc: 'Проверяет кампании, расходы, клики и точки роста.',
    prompt: 'Сделай аудит Avito Рекламы: кампании, группы, объявления, расходы, показы, клики и доступные показатели результата. Период — последние 30 дней. Покажи таблицу (кампания/группа, показатели, проблема, причина, рекомендация), приоритеты ручной оптимизации и что проверить перед изменением рекламы. Если данных не хватает — напиши прямо.' },
  { service: 'avito', title: 'Креативы Avito', desc: 'Сравнивает объявления по показам, кликам и обращениям.',
    prompt: 'Сравни объявления и креативы Avito Рекламы по показам, кликам, доле кликов от показов, обращениям и расходам (если данные доступны). Период — последние 30 дней. Покажи таблицу (объявление, показы, клики, CTR, результат, вывод, рекомендация), объявления, которые стоит обновить, и что проверить перед обновлением.' },
  { service: 'avito', title: 'Расходы Avito', desc: 'Находит кампании, где бюджет уходит без результата.',
    prompt: 'Проверь расходы Avito Рекламы: найди кампании, где бюджет расходуется без результата или слишком быстро. Период — текущий месяц и последние 7 дней. Покажи таблицу (кампания, расход, результат, риск, рекомендация), сигналы для ручной проверки бюджета и что проверить перед изменением бюджета.' },
  { service: 'avito', title: 'Краткий отчёт Avito', desc: 'Активные кампании, показатели, изменения и риски.',
    prompt: 'Подготовь краткий отчёт по Avito Рекламе: активные кампании, основные показатели, изменения, риски и рекомендации. Период — последние 7 дней. Покажи сводку в 5–7 пунктов, таблицу основных кампаний и что проверить вручную на следующей неделе.' },
]

const emptyScroll = ref(null)
const copiedIndex = ref(-1)
let _copyTimer = null

const copyPrompt = async (text, i) => {
  try { await navigator.clipboard.writeText(text) } catch { /* clipboard может быть недоступен */ }
  copiedIndex.value = i
  clearTimeout(_copyTimer)
  _copyTimer = setTimeout(() => { copiedIndex.value = -1 }, 1600)
}

const fillPrompt = async (text) => {
  prompt.value = text
  emptyScroll.value?.scrollTo({ top: 0, behavior: 'smooth' })
  await nextTick(); autoGrow()
  textarea.value?.focus()
}

// ── Диалоги (серверная история) ──────────────────────────────────────────────
const conversations = ref([])
const historySearch = ref('')
const activeConversationId = ref(null)
const activeMessages = ref([])
const hasThread = computed(() => activeMessages.value.length > 0)
const filteredConversations = computed(() => {
  const query = historySearch.value.trim().toLocaleLowerCase('ru-RU')
  if (!query) return conversations.value
  return conversations.value.filter((conversation) => String(conversation.title || '').toLocaleLowerCase('ru-RU').includes(query))
})

const openChatSearch = async () => {
  railOpen.value = true
  await nextTick()
  historySearchInput.value?.focus()
}

const formatChatDate = (value) => {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const today = new Date()
  if (date.toDateString() === today.toDateString()) return 'сегодня'
  return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })
}

const loadModels = async () => {
  try {
    const { data } = await api.get('assistant/models')
    models.value = Array.isArray(data.models) ? data.models : []
    configured.value = !!data.configured
    wordstatConfigured.value = !!data.wordstat_configured
    selectedModelId.value = data.default_model || models.value[0]?.id || ''
    syncEffortToModel()
  } catch { /* пустой каталог — покажем недоступность */ }
}

const loadConversations = async () => {
  try {
    const { data } = await api.get('assistant/conversations')
    conversations.value = Array.isArray(data) ? data : []
  } catch { /* ignore */ }
}

const newChat = async () => {
  activeConversationId.value = null
  activeMessages.value = []
  prompt.value = ''
  railOpen.value = false
  await nextTick()
  textarea.value?.focus()
}

const selectConversation = async (id) => {
  railOpen.value = false
  try {
    const { data } = await api.get(`assistant/conversations/${id}`)
    activeConversationId.value = data.id
    activeMessages.value = (data.messages || []).map((m) => ({ id: m.id || nextMessageId('saved'), role: m.role, content: m.content || '' }))
    threadPinnedToBottom.value = true
    await scrollThread(true)
  } catch { /* ignore */ }
}

const autoGrow = () => {
  const element = hasThread.value ? threadTextarea.value : textarea.value
  if (!element) return
  element.style.height = 'auto'
  element.style.height = `${Math.min(element.scrollHeight, 104)}px`
  // После вставки готового промпта браузер иногда оставляет textarea
  // горизонтально проскролленной к каретке — начало фразы визуально обрезается.
  element.scrollLeft = 0
}

const threadPinnedToBottom = ref(true)
let threadScrollFrame = null

const onThreadScroll = (event) => {
  const element = event.currentTarget
  threadPinnedToBottom.value = element.scrollHeight - element.scrollTop - element.clientHeight < 72
}

const scrollThread = async (force = false) => {
  if (!force && !threadPinnedToBottom.value) return
  await nextTick()
  cancelAnimationFrame(threadScrollFrame)
  threadScrollFrame = requestAnimationFrame(() => {
    const element = threadInner.value
    if (!element || (!force && !threadPinnedToBottom.value)) return
    element.scrollTop = element.scrollHeight
  })
}

const TOOL_LABELS = {
  list_projects: 'список проектов',
  use_project: 'выбор проекта',
  direct_get_campaigns: 'кампании Директа',
  direct_get_statistics: 'статистика Директа',
  direct_get_adgroups: 'группы объявлений',
  direct_get_ads: 'объявления Директа',
  direct_get_keywords: 'ключевые слова',
  metrika_get_counters: 'счётчики Метрики',
  metrika_get_goals: 'цели Метрики',
  metrika_get_report: 'отчёт Метрики',
  metrika_get_report_by_time: 'динамика Метрики',
  wordstat_top_requests: 'Wordstat: спрос',
  wordstat_dynamics: 'Wordstat: динамика',
  wordstat_regions: 'Wordstat: регионы',
  vk_get_campaigns: 'кампании VK',
  vk_get_statistics: 'статистика VK',
  vk_get_balance: 'баланс VK',
  avito_get_campaigns: 'кампании Avito',
  avito_get_statistics: 'статистика Avito',
  avito_get_balance: 'баланс Avito',
}
const toolLabel = (name) => TOOL_LABELS[name] || name

const handleEvent = (ev, assistantMsg) => {
  switch (ev.type) {
    case 'meta':
      if (ev.conversation_id) activeConversationId.value = ev.conversation_id
      break
    case 'reasoning':
      assistantMsg.reasoning = (assistantMsg.reasoning || '') + (ev.delta || '')
      scrollThread()
      break
    case 'text':
      assistantMsg.content += ev.delta || ''
      scrollThread()
      break
    case 'tool':
      if (ev.status === 'start') toolActivity.value = toolLabel(ev.name)
      break
    case 'done':
      if (!assistantMsg.content && ev.content) assistantMsg.content = ev.content
      toolActivity.value = ''
      break
    case 'error':
      assistantMsg.content += (assistantMsg.content ? '\n\n' : '') + `⚠️ ${ev.error || 'Ошибка'}`
      toolActivity.value = ''
      break
    default:
      break
  }
}

const consumeSSE = async (stream, assistantMsg) => {
  const reader = stream.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    let idx
    while ((idx = buffer.indexOf('\n\n')) >= 0) {
      const chunk = buffer.slice(0, idx)
      buffer = buffer.slice(idx + 2)
      const line = chunk.split('\n').find((l) => l.startsWith('data:'))
      if (!line) continue
      let ev
      try { ev = JSON.parse(line.slice(5).trim()) } catch { continue }
      handleEvent(ev, assistantMsg)
    }
  }
}

const sendPrompt = async () => {
  const question = prompt.value.trim()
  if (!question || sending.value) return
  sending.value = true
  toolActivity.value = ''
  threadPinnedToBottom.value = true

  activeMessages.value.push({ id: nextMessageId('user'), role: 'user', content: question })
  // Берём реактивный прокси из массива — иначе мутации при стриме не обновят UI.
  activeMessages.value.push({ id: nextMessageId('assistant'), role: 'assistant', content: '', reasoning: '', pending: true })
  const assistantMsg = activeMessages.value[activeMessages.value.length - 1]
  prompt.value = ''
  await nextTick(); autoGrow(); scrollThread(true)

  const token = getAccessToken()
  const body = {
    message: question,
    conversation_id: activeConversationId.value || undefined,
    model: selectedModelId.value || undefined,
    effort: selectedModel.value.reasoning ? selectedEffort.value : undefined,
  }
  abortController = new AbortController()
  let stopped = false
  try {
    const resp = await fetch('/api/assistant/chat', {
      method: 'POST',
      credentials: 'include',
      signal: abortController.signal,
      headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: JSON.stringify(body),
    })
    if (!resp.ok || !resp.body) throw new Error(`HTTP ${resp.status}`)
    await consumeSSE(resp.body, assistantMsg)
  } catch (e) {
    if (e?.name === 'AbortError') {
      stopped = true
      assistantMsg.content += (assistantMsg.content ? '\n\n' : '') + '_Остановлено._'
    } else if (!assistantMsg.content) {
      assistantMsg.content = 'Не удалось получить ответ. Попробуйте ещё раз.'
    }
  } finally {
    abortController = null
    assistantMsg.pending = false
    sending.value = false
    toolActivity.value = ''
    if (!stopped) loadConversations()
    await nextTick(); scrollThread(); threadTextarea.value?.focus()
  }
}

// Остановить генерацию: обрываем запрос (бэкенд отменит агент-луп).
const stopGeneration = () => {
  try { abortController?.abort() } catch { /* уже завершён */ }
}

onMounted(() => {
  loadModels()
  loadConversations()
})

onUnmounted(() => {
  clearTimeout(_copyTimer)
  cancelAnimationFrame(threadScrollFrame)
})
</script>

<style scoped>
.assistant-page {
  --assistant-bg: #ffffff;
  --assistant-panel: #ffffff;
  --assistant-muted: #8d99ad;
  --assistant-text: #1b2437;
  --assistant-sub: #5c6b84;
  --assistant-line: #e6ebf2;
  --assistant-strong-line: #d8e0eb;
  --assistant-soft: #f5f7fa;
  --assistant-blue: #2f6bea;
  --assistant-blue-soft: #eaf0fe;
  --assistant-violet: #7c6ff0;
  --assistant-amber: #bd7d16;
  --assistant-amber-soft: #fff5df;
  --assistant-green: #1fa55b;
  --assistant-green-soft: rgba(31, 165, 91, .13);
  display: flex;
  width: 100%;
  margin: 0;
  flex: 1 1 auto;
  align-self: stretch;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  isolation: isolate;
  background: var(--assistant-bg);
  color: var(--assistant-text);
}

.assistant-page--dark {
  --assistant-bg: #202332;
  --assistant-panel: #1a1d29;
  --assistant-muted: #9ca6ba;
  --assistant-text: #f2f4fb;
  --assistant-sub: #c1c9d8;
  --assistant-line: rgba(255,255,255,.09);
  --assistant-strong-line: rgba(255,255,255,.16);
  --assistant-soft: #282c3d;
  --assistant-blue-soft: rgba(74, 122, 255, .17);
  --assistant-amber-soft: rgba(187, 125, 22, .16);
  --assistant-green: #34c37d;
  --assistant-green-soft: rgba(52, 195, 125, .16);
}

.assistant-rail {
  width: 4.4rem;
  flex: 0 0 4.4rem;
  min-width: 0;
  overflow: hidden;
  border-right: 1px solid var(--assistant-line);
  background: var(--assistant-panel);
  transition: width .18s ease, flex-basis .18s ease;
}

.assistant-rail--open { width: 20rem; flex-basis: 20rem; }
.assistant-rail__compact { display: flex; flex-direction: column; align-items: center; gap: .55rem; padding-top: 1.1rem; }
.assistant-rail__expanded { display: flex; flex-direction: column; height: 100%; padding: 1rem .85rem .85rem; }

.rail-icon-button,
.composer-icon,
.composer-send,
.assistant-depth button,
.assistant-info-card button,
.assistant-suggestion,
.assistant-message__actions button {
  border: 0;
  font: inherit;
  cursor: pointer;
}

.rail-icon-button { display: grid; width: 2.8rem; height: 2.8rem; place-items: center; border-radius: .78rem; background: transparent; color: var(--assistant-sub); }
.rail-icon-button:hover { background: var(--assistant-soft); color: var(--assistant-text); }
.rail-icon-button svg, .rail-new-chat svg, .assistant-info-card svg, .composer-icon svg, .composer-send svg, .assistant-limit svg, .assistant-suggestion__icon :deep(svg), .assistant-message__avatar svg { width: 1.1rem; height: 1.1rem; fill: none; stroke: currentColor; stroke-width: 1.65; stroke-linecap: round; stroke-linejoin: round; }

/* Выбор модели в композере */
.assistant-model { position: relative; z-index: 1; margin-left: auto; }
.assistant-model--open { z-index: 30; }
.assistant-model__btn { display: inline-flex; align-items: center; gap: .45rem; height: 2.68rem; padding: 0 .72rem 0 .94rem; border: 1px solid var(--assistant-line); border-radius: .78rem; background: var(--assistant-soft); color: var(--assistant-sub); font: 500 .98rem/1 Inter, sans-serif; cursor: pointer; }
.assistant-model__btn:hover { border-color: var(--assistant-strong-line); }
.assistant-model__btn b { color: var(--assistant-text); font-weight: 600; }
.assistant-model__btn svg { width: 1rem; height: 1rem; flex-shrink: 0; fill: none; stroke: currentColor; stroke-width: 1.7; stroke-linecap: round; stroke-linejoin: round; }
.assistant-model__menu { position: absolute; right: 0; top: calc(100% + .48rem); min-width: 13.25rem; padding: .4rem; border: 1px solid var(--assistant-strong-line); border-radius: .82rem; background: var(--assistant-panel); box-shadow: 0 .7rem 2rem rgba(27,36,55,.18); z-index: 40; display: flex; flex-direction: column; gap: .16rem; transform-origin: top right; animation: assistant-model-menu-in .16s cubic-bezier(.2,.8,.2,1); }
.assistant-model__menu--up { top: auto; bottom: calc(100% + .48rem); transform-origin: bottom right; }
.assistant-model__menu button { display: flex; width: 100%; min-height: 2.45rem; padding: .58rem .72rem; border: 0; border-radius: .6rem; background: transparent; color: var(--assistant-text); font: 500 .92rem/1.25 Inter, sans-serif; text-align: left; cursor: pointer; }
.assistant-model__menu button:hover { background: var(--assistant-soft); }
.assistant-model__menu button.is-active { background: var(--assistant-blue-soft); color: var(--assistant-blue); font-weight: 600; }
@keyframes assistant-model-menu-in { from { opacity: 0; transform: translateY(-.28rem) scale(.98); } to { opacity: 1; transform: translateY(0) scale(1); } }
/* Второй селектор (глубина) стоит вплотную к первому — auto только у первого. */
.assistant-model + .assistant-model { margin-left: .42rem; }
.composer-send:disabled { opacity: .55; cursor: default; }

/* Потоковый ответ */
.assistant-message__body { min-width: 0; }
.assistant-tool-note { display: inline-flex; align-items: center; gap: .42rem; margin-top: .8rem; padding: .42rem .58rem; border: 1px solid var(--assistant-line); border-radius: .58rem; background: var(--assistant-soft); color: var(--assistant-sub); font-size: .78rem; line-height: 1.25; }
.assistant-tool-note span { width: .55rem; height: .55rem; border: 1.5px solid var(--assistant-blue); border-right-color: transparent; border-radius: 50%; animation: assistant-spin .72s linear infinite; }
@keyframes assistant-spin { to { transform: rotate(360deg); } }
.assistant-welcome__note { margin-top: .65rem; color: var(--assistant-amber); font-size: .88rem; }

/* Блок размышлений — сворачиваемый, одним куском (как в нативном Клоде) */
.assistant-reasoning { margin-bottom: .5rem; border: 1px solid var(--assistant-line); border-radius: .7rem; background: var(--assistant-soft); overflow: hidden; }
.assistant-reasoning > summary { display: flex; align-items: center; gap: .4rem; padding: .5rem .7rem; color: var(--assistant-sub); font-size: .8rem; font-weight: 600; cursor: pointer; list-style: none; user-select: none; }
.assistant-reasoning > summary::-webkit-details-marker { display: none; }
.assistant-reasoning > summary svg { width: .95rem; height: .95rem; flex-shrink: 0; fill: none; stroke: currentColor; stroke-width: 1.7; stroke-linecap: round; stroke-linejoin: round; }
.assistant-reasoning[open] > summary { border-bottom: 1px solid var(--assistant-line); }
.assistant-reasoning__text { max-height: 22rem; overflow-y: auto; padding: .6rem .75rem; color: var(--assistant-muted); font-size: .82rem; line-height: 1.5; white-space: pre-wrap; overflow-wrap: anywhere; }

/* Кнопка «Остановить» (во время генерации) */
.composer-send--stop { background: #fdecec !important; color: #d9463f !important; }
.composer-send--stop:hover { background: #fbdcdc !important; }
.composer-send--stop svg { fill: currentColor; stroke: none; }

.rail-heading { display: flex; align-items: center; justify-content: space-between; padding: 0 .25rem; margin-bottom: .7rem; font-size: .9rem; font-weight: 700; }
.rail-new-chat { display: flex; align-items: center; gap: .58rem; width: 100%; height: 2.85rem; padding: 0 .8rem; border: 1.5px dashed var(--assistant-strong-line); border-radius: .72rem; background: transparent; color: var(--assistant-sub); font: 500 .9rem/1 Inter, sans-serif; cursor: pointer; }
.rail-new-chat:hover { border-color: var(--assistant-blue); color: var(--assistant-blue); }
.rail-search { display: flex; align-items: center; gap: .48rem; height: 2.55rem; margin-top: .72rem; padding: 0 .7rem; border: 1px solid var(--assistant-line); border-radius: .72rem; background: var(--assistant-soft); color: var(--assistant-muted); }
.rail-search:focus-within { border-color: var(--assistant-blue); box-shadow: 0 0 0 .18rem var(--assistant-blue-soft); }
.rail-search svg { width: .95rem; height: .95rem; flex: 0 0 auto; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
.rail-search input { width: 100%; min-width: 0; border: 0; outline: 0; background: transparent; color: var(--assistant-text); font: 400 .82rem/1 Inter, sans-serif; }
.rail-search input::placeholder { color: var(--assistant-muted); }
.rail-history { display: flex; flex: 1; flex-direction: column; min-height: 0; gap: .25rem; margin-top: .8rem; overflow-y: auto; scrollbar-width: none; }
.rail-history::-webkit-scrollbar { width: 0; }
.rail-history__item { display: flex; flex-direction: column; gap: .2rem; width: 100%; padding: .66rem .72rem; border: 0; border-radius: .7rem; background: transparent; color: var(--assistant-text); text-align: left; cursor: pointer; }
.rail-history__item:hover, .rail-history__item.is-active { background: var(--assistant-soft); }
.rail-history__title { overflow: hidden; font-size: .85rem; font-weight: 500; line-height: 1.25; text-overflow: ellipsis; white-space: nowrap; }
.rail-history__date, .rail-history__empty { color: var(--assistant-muted); font-size: .74rem; }
.rail-history__empty { padding: .6rem; line-height: 1.4; }

.assistant-projects-label { padding: .7rem .58rem .4rem; color: var(--assistant-muted); font-size: .8rem; font-weight: 600; }
.assistant-info-card { padding: .48rem; border: 1px solid var(--assistant-strong-line); border-radius: 1rem; background: var(--assistant-soft); box-shadow: 0 .12rem .35rem rgba(27,36,55,.06); }
.assistant-info-card button { display: flex; align-items: center; gap: .56rem; width: 100%; height: 2.5rem; padding: 0 .52rem; border-radius: .6rem; background: transparent; color: var(--assistant-text); font-size: .86rem; text-align: left; }
.assistant-info-card button:hover { background: var(--assistant-panel); }
.assistant-info-card__icon { display: grid; width: 1rem; height: 1rem; place-items: center; color: var(--assistant-sub); }
.assistant-info-card__icon svg { width: 1rem; height: 1rem; }
.assistant-info-card__chevron { width: .9rem !important; height: .9rem !important; margin-left: auto; color: var(--assistant-muted); }

.assistant-stage { display: flex; flex: 1; flex-direction: column; min-width: 0; min-height: 0; background: var(--assistant-bg); }
.assistant-limit { display: inline-flex; align-items: center; gap: .48rem; margin-left: auto; padding: .58rem .92rem; border-radius: .78rem; background: linear-gradient(105deg, #5b8def, #7c6ff0); color: #fff; font-size: .85rem; }
.assistant-limit svg { width: 1rem; height: 1rem; stroke-width: 1.9; }
.assistant-limit b { font-size: .92rem; }.assistant-limit span { opacity: .88; }

/* Экран приветствия: колонка со скроллом — герой на первый экран, промпты ниже */
.assistant-empty { display: flex; flex: 1 1 auto; flex-direction: column; align-items: center; justify-content: flex-start; min-height: 0; padding: 0; overflow-y: scroll; overscroll-behavior-y: contain; scroll-behavior: smooth; scrollbar-gutter: stable; }
.assistant-hero { box-sizing: border-box; display: flex; flex: 0 0 auto; flex-direction: column; align-items: center; justify-content: center; width: 100%; max-width: 72rem; min-height: min(44rem, 78vh); padding: 2.4rem 2.75rem 2rem; text-align: center; }
.assistant-hero__title { margin: 0; font-size: clamp(2.15rem, 2.65vw, 2.6rem); font-weight: 700; letter-spacing: -.04em; text-wrap: balance; }
.assistant-hero__sub { margin: .72rem auto 0; max-width: 42rem; color: var(--assistant-sub); font-size: 1.12rem; line-height: 1.55; text-wrap: balance; }
.assistant-hero .assistant-composer { width: min(70.6rem, 100%); margin-top: 1.9rem; text-align: left; }

/* Источники данных — компактный ряд пилюль */
.assistant-sources-row { display: flex; align-items: center; flex-wrap: wrap; gap: .6rem .8rem; width: min(70.6rem, 100%); margin-top: 1.5rem; text-align: left; }
.assistant-sources-row__label { color: var(--assistant-muted); font-size: .68rem; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; white-space: nowrap; }
.assistant-sources-row__pills { display: flex; flex-wrap: wrap; gap: .5rem; }
.source-pill { display: inline-flex; align-items: center; gap: .48rem; padding: .34rem .7rem .34rem .38rem; border: 1px solid var(--assistant-line); border-radius: 999px; background: var(--assistant-panel); box-shadow: 0 .1rem .3rem rgba(27,36,55,.03); }
.source-pill__mark { display: grid; width: 1.7rem; height: 1.7rem; flex: 0 0 1.7rem; place-items: center; overflow: hidden; border-radius: .5rem; background: #f1f5ff; color: #7563e7; }
.source-pill__mark img { width: 1.15rem; height: 1.15rem; object-fit: contain; }
.source-pill__mark svg { width: 1rem; height: 1rem; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; }
.source-pill__name { color: var(--assistant-text); font-size: .84rem; font-weight: 700; white-space: nowrap; }
.source-pill__dot { width: .42rem; height: .42rem; border-radius: 50%; background: var(--assistant-muted); }
.source-pill__dot.is-on { background: var(--assistant-green); box-shadow: 0 0 0 .16rem rgba(31,165,91,.14); }
.source-pill--off { opacity: .62; }
.source-pill--off .source-pill__mark { filter: saturate(.7); }

/* Готовые промпты */
.assistant-prompts { width: 100%; max-width: 72rem; padding: 1.4rem 2.75rem 3.5rem; }
.assistant-prompts__title { margin: 0 0 1rem; color: var(--assistant-muted); font-size: .72rem; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; }
.assistant-prompts__grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: .75rem; }
.prompt-tile { position: relative; display: flex; flex-direction: column; min-height: 7.7rem; gap: .38rem; padding: 1rem 1.08rem 3rem; border: 1px solid var(--assistant-line); border-radius: 1rem; background: var(--assistant-panel); text-align: left; cursor: pointer; transition: border-color .15s ease, box-shadow .15s ease; }
.prompt-tile__service { position: absolute; right: .9rem; bottom: .82rem; display: grid; width: 2.5rem; height: 2.5rem; place-items: center; overflow: hidden; border-radius: .7rem; background: #f1f5ff; color: #7563e7; }
.prompt-tile__service img { width: 1.75rem; height: 1.75rem; object-fit: contain; }
.prompt-tile__service svg { width: 1.35rem; height: 1.35rem; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; }
.prompt-tile__service--direct { background: #fff8e7; }
.prompt-tile__service--metrika { background: #fff0f0; }
.prompt-tile__service--vk { background: #edf4ff; }
.prompt-tile__service--avito { background: #eafaf6; }
.prompt-tile__service--wordstat { background: #f2efff; }
.prompt-tile:hover { border-color: var(--assistant-blue); box-shadow: 0 .4rem 1.1rem rgba(47,107,234,.09); }
.prompt-tile:focus-visible { outline: 2px solid var(--assistant-blue); outline-offset: 2px; }
.prompt-tile__head { display: flex; align-items: flex-start; justify-content: space-between; gap: .6rem; }
.prompt-tile__title { font-size: .95rem; font-weight: 700; color: var(--assistant-text); line-height: 1.3; }
.prompt-tile__desc { color: var(--assistant-sub); font-size: .83rem; line-height: 1.4; }
.prompt-tile__copy { flex-shrink: 0; display: grid; width: 2rem; height: 2rem; place-items: center; border: 0; border-radius: .6rem; background: var(--assistant-soft); color: var(--assistant-muted); cursor: pointer; transition: background .25s ease, color .25s ease, transform .2s ease; }
.prompt-tile__copy:hover { color: var(--assistant-sub); background: var(--assistant-strong-line); }
.prompt-tile__copy svg { width: 1.05rem; height: 1.05rem; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
.prompt-tile__copy.is-copied { background: var(--assistant-green-soft); color: var(--assistant-green); animation: copy-pop .32s ease; }
@keyframes copy-pop { 0% { transform: scale(.7); } 55% { transform: scale(1.14); } 100% { transform: scale(1); } }
.assistant-context { display: flex; justify-content: center; gap: .6rem; flex-wrap: wrap; max-width: 68rem; margin: 1.2rem 0; }
.assistant-context__chip { display: inline-flex; align-items: center; gap: .45rem; padding: .48rem .78rem; border: 1px solid var(--assistant-strong-line); border-radius: 1rem; background: var(--assistant-panel); color: var(--assistant-sub); font-size: .85rem; }
.assistant-context__chip b { color: var(--assistant-text); font-weight: 600; }.assistant-context__chip i { width: .42rem; height: .42rem; border-radius: 50%; background: #1fa55b; }

.assistant-composer { position: relative; z-index: 2; box-sizing: border-box; width: min(83.5rem, 100%); overflow: visible; isolation: isolate; padding: 1.41rem 1.55rem 1.07rem; border: 1px solid var(--assistant-strong-line); border-radius: 1.48rem; background: var(--assistant-panel); box-shadow: 0 .5rem 1.9rem rgba(27,36,55,.075); }
.assistant-composer textarea { box-sizing: border-box; display: block; width: 100%; min-width: 0; min-height: 5.62rem; max-height: 8.82rem; padding: 0; border: 0; border-radius: 0; outline: 0; resize: none; overflow-x: hidden; overflow-y: auto; appearance: none; background: transparent; box-shadow: none; color: var(--assistant-text); font: 400 1.21rem/1.5 Inter, sans-serif; white-space: pre-wrap; overflow-wrap: anywhere; word-break: break-word; }
.assistant-composer textarea::placeholder { color: var(--assistant-muted); }
.assistant-composer__actions { display: flex; align-items: center; gap: .52rem; margin-top: .84rem; }
.composer-icon { display: grid; width: 2.35rem; height: 2.35rem; place-items: center; border-radius: .65rem; background: transparent; color: var(--assistant-muted); }.composer-icon:hover { background: var(--assistant-soft); color: var(--assistant-sub); }
.composer-icon svg { width: 1.18rem; height: 1.18rem; }
.assistant-composer__hint { margin-left: .12rem; margin-right: auto; color: var(--assistant-muted); font-size: .72rem; white-space: nowrap; }
.assistant-depth { display: inline-flex; gap: .12rem; margin-left: auto; padding: .2rem; border-radius: .65rem; background: var(--assistant-soft); }
.assistant-depth button { padding: .42rem .72rem; border-radius: .5rem; background: transparent; color: var(--assistant-sub); font-size: .77rem; white-space: nowrap; }.assistant-depth button.is-active { background: var(--assistant-panel); color: var(--assistant-text); font-weight: 600; box-shadow: 0 .06rem .18rem rgba(27,36,55,.12); }
.composer-send { display: grid; width: 3.35rem; height: 3.08rem; margin-left: .28rem; place-items: center; border-radius: .85rem; background: var(--assistant-soft); color: var(--assistant-muted); transition: background .16s ease, color .16s ease; }.composer-send.is-active { background: var(--assistant-blue); color: #fff; box-shadow: none; }.composer-send.is-active:hover { background: #1f5fd8; }.composer-send:disabled { opacity: .5; cursor: default; }.composer-send svg { width: 1.55rem; height: 1.55rem; }

.assistant-suggestions { width: min(68rem, 100%); margin-top: 1.25rem; }.assistant-suggestions__label { margin: 1rem .2rem .55rem; color: var(--assistant-muted); font-size: .73rem; font-weight: 700; letter-spacing: .09em; }.assistant-suggestions__label:first-child { margin-top: 0; }
.assistant-suggestions__grid { display: grid; grid-template-columns: 1fr 1fr; gap: .65rem; }
.assistant-suggestion { display: flex; align-items: flex-start; gap: .8rem; width: 100%; padding: .95rem 1rem; border: 1px solid var(--assistant-line); border-radius: .95rem; background: var(--assistant-panel); color: var(--assistant-text); text-align: left; transition: border-color .15s ease, box-shadow .15s ease; }.assistant-suggestion:hover { border-color: var(--assistant-blue); box-shadow: 0 .25rem .85rem rgba(47,107,234,.1); }
.assistant-suggestion--alert { border-color: #f2dfb8; background: var(--assistant-amber-soft); }.assistant-suggestion--alert:hover { border-color: #e7ad46; box-shadow: 0 .25rem .85rem rgba(239,168,39,.15); }
.assistant-suggestion__icon { display: grid; width: 2.25rem; height: 2.25rem; flex: 0 0 2.25rem; place-items: center; border-radius: .7rem; background: var(--assistant-blue-soft); color: var(--assistant-blue); }.assistant-suggestion--alert .assistant-suggestion__icon { background: var(--assistant-panel); color: var(--assistant-amber); }
.assistant-suggestion b, .assistant-suggestion small { display: block; }.assistant-suggestion b { font-size: .9rem; line-height: 1.3; }.assistant-suggestion small { margin-top: .18rem; color: var(--assistant-muted); font-size: .78rem; line-height: 1.3; }.assistant-suggestion--alert small { color: var(--assistant-amber); }.assistant-suggestion em { align-self: center; margin-left: auto; color: var(--assistant-blue); font-size: .8rem; font-style: normal; font-weight: 600; white-space: nowrap; }.assistant-suggestion--alert em { color: var(--assistant-amber); }

.assistant-thread { display: flex; flex: 1 1 auto; flex-direction: column; min-height: 0; overflow: hidden; }
.assistant-thread__inner { box-sizing: border-box; flex: 1 1 auto; min-height: 0; overflow-y: auto; overscroll-behavior-y: contain; }
.assistant-thread__messages { display: flex; flex-direction: column; gap: 1.55rem; width: min(70.6rem, 100%); min-height: 100%; margin: 0 auto; padding: 2.56rem 2.68rem 3.85rem; }
.assistant-message { display: flex; gap: .88rem; min-width: 0; }
.assistant-message--user { justify-content: flex-end; }
.assistant-message--user .assistant-message__bubble { max-width: min(47rem, 78%); padding: .88rem 1.07rem; border: 1px solid transparent; border-radius: 1.22rem 1.22rem .45rem 1.22rem; background: linear-gradient(135deg, #3276ed, #2864dc); color: #fff; box-shadow: 0 .45rem 1.1rem rgba(40,100,220,.16); }
.assistant-message--user .assistant-message__bubble p { margin: 0; color: inherit; white-space: pre-wrap; overflow-wrap: anywhere; }
.assistant-message--assistant { max-width: min(62rem, 94%); align-items: flex-start; }
.assistant-message__avatar { display: grid; width: 2.68rem; height: 2.68rem; flex: 0 0 2.68rem; margin-top: .12rem; place-items: center; border: 1px solid rgba(47,107,234,.12); border-radius: .88rem; background: var(--assistant-blue-soft); color: var(--assistant-blue); }
.assistant-message__avatar svg { width: 1.16rem; height: 1.16rem; stroke-width: 1.85; }
.assistant-message__label { margin: .18rem 0 .46rem; color: var(--assistant-muted); font-size: .74rem; font-weight: 700; letter-spacing: .01em; }
.assistant-message__bubble { padding: 1.15rem 1.26rem; border: 1px solid var(--assistant-line); border-radius: .41rem 1.2rem 1.2rem 1.2rem; background: var(--assistant-panel); box-shadow: 0 .16rem .54rem rgba(27,36,55,.035); font-size: 1.05rem; line-height: 1.62; }
.assistant-markdown { color: var(--assistant-sub); overflow-wrap: anywhere; }
.assistant-markdown :deep(p) { margin: 0 0 .82rem; }
.assistant-markdown :deep(p:last-child) { margin-bottom: 0; }
.assistant-markdown :deep(h1), .assistant-markdown :deep(h2), .assistant-markdown :deep(h3), .assistant-markdown :deep(h4) { margin: 1.15rem 0 .62rem; color: var(--assistant-text); font-weight: 700; letter-spacing: -.02em; line-height: 1.25; }
.assistant-markdown :deep(h1) { font-size: 1.25rem; }.assistant-markdown :deep(h2) { font-size: 1.14rem; }.assistant-markdown :deep(h3), .assistant-markdown :deep(h4) { font-size: 1.02rem; }
.assistant-markdown :deep(h1:first-child), .assistant-markdown :deep(h2:first-child), .assistant-markdown :deep(h3:first-child), .assistant-markdown :deep(h4:first-child) { margin-top: 0; }
.assistant-markdown :deep(ul), .assistant-markdown :deep(ol) { margin: .76rem 0; padding-left: 1.25rem; }.assistant-markdown :deep(li + li) { margin-top: .3rem; }
.assistant-markdown :deep(blockquote) { margin: .9rem 0; padding: .1rem 0 .1rem .85rem; border-left: .18rem solid var(--assistant-blue); color: var(--assistant-sub); }
.assistant-markdown :deep(code) { padding: .1rem .32rem; border-radius: .32rem; background: var(--assistant-soft); color: var(--assistant-text); font: .88em/1.4 ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
.assistant-markdown :deep(pre) { margin: .88rem 0; padding: .85rem 1rem; overflow-x: auto; border: 1px solid var(--assistant-line); border-radius: .72rem; background: var(--assistant-soft); }.assistant-markdown :deep(pre code) { padding: 0; background: transparent; }
.assistant-markdown :deep(a) { color: var(--assistant-blue); text-decoration: underline; text-decoration-color: rgba(47,107,234,.35); text-underline-offset: .14em; }
.assistant-markdown :deep(table) { display: block; width: 100%; margin: .9rem 0; overflow-x: auto; border-collapse: collapse; font-size: .9em; }.assistant-markdown :deep(th), .assistant-markdown :deep(td) { padding: .48rem .6rem; border: 1px solid var(--assistant-line); text-align: left; white-space: nowrap; }.assistant-markdown :deep(th) { background: var(--assistant-soft); color: var(--assistant-text); font-weight: 700; }
.assistant-typing { display: inline-flex; align-items: center; min-height: 1.65rem; gap: .32rem; padding: .1rem .05rem; }.assistant-typing i { width: .38rem; height: .38rem; border-radius: 50%; background: var(--assistant-blue); opacity: .32; animation: typing-pulse 1.12s ease-in-out infinite; }.assistant-typing i:nth-child(2) { animation-delay: .14s; }.assistant-typing i:nth-child(3) { animation-delay: .28s; }@keyframes typing-pulse { 0%, 100% { transform: translateY(0); opacity: .24; } 45% { transform: translateY(-.2rem); opacity: 1; } }
.chat-message-enter-active { transition: opacity .28s ease, transform .28s cubic-bezier(.2,.8,.2,1); }.chat-message-enter-from { opacity: 0; transform: translateY(.5rem); }
.assistant-message__actions { display: flex; gap: .42rem; margin-top: .75rem; }.assistant-message__actions button { padding: .38rem .62rem; border-radius: .5rem; background: var(--assistant-soft); color: var(--assistant-sub); font-size: .75rem; }.assistant-message__actions button:hover { color: var(--assistant-blue); }
.assistant-thread__composer { position: relative; z-index: 10; flex: 0 0 auto; overflow: visible; padding: 1.07rem 2.68rem 1.45rem; border-top: 0; background: color-mix(in srgb, var(--assistant-bg) 94%, transparent); backdrop-filter: blur(12px); }.assistant-thread__composer .assistant-composer { width: min(70.6rem, 100%); margin: 0 auto; box-shadow: 0 .35rem 1.35rem rgba(27,36,55,.055); }.assistant-thread__composer p { width: min(70.6rem, 100%); margin: .48rem auto 0; color: var(--assistant-muted); font-size: .8rem; }

@media (max-width: 1180px) {
  .assistant-rail:not(.assistant-rail--open) { width: 3.5rem; flex-basis: 3.5rem; }
  .assistant-depth button:last-child { display: none; }
  .assistant-hero, .assistant-prompts { max-width: 52rem; }
}
@media (max-width: 980px) { .assistant-prompts__grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 820px) {
  .assistant-stage__head { padding-inline: 1rem; }
  .assistant-hero { padding-inline: 1.1rem; }
  .assistant-prompts { padding-inline: 1.1rem; }
  .assistant-thread__inner, .assistant-thread__composer { padding-inline: 1rem; }
}
@media (max-width: 640px) {
  .assistant-prompts__grid { grid-template-columns: 1fr; }
  .assistant-composer__hint { display: none; }
  .assistant-model__btn { padding-inline: .55rem; }
}
@media (max-width: 560px) { .assistant-rail { display: none; }.assistant-hero__title { font-size: 1.4rem; } }
@media (prefers-reduced-motion: reduce) { .assistant-tool-note span, .assistant-typing i { animation: none; }.prompt-tile { transition: opacity .2s ease; transform: none; }.prompt-tile__copy.is-copied { animation: none; }.chat-message-enter-active { transition: none; } }
@media (prefers-reduced-motion: reduce) { .assistant-rail, .assistant-suggestion { transition: none; } }
</style>
