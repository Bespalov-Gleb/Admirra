<template>
  <div ref="containerRef" class="relative date-range-picker-container">
    <!-- Trigger Button -->
    <button
      ref="buttonRef"
      @click.stop="toggleCalendar"
      class="drp-trigger flex w-full items-center justify-between gap-3 px-[1.0417rem] h-[3.1944rem] bg-white dark:bg-[#2C2F3D] border border-[#ebebeb] dark:border-white/10 rounded-xl text-[0.9028rem] font-medium hover:border-[#d9dee6] dark:hover:border-white/20 hover:shadow-[0_8px_18px_rgba(15,23,42,0.04)] dark:shadow-[inset_0_1px_0_rgba(255,255,255,0.07)] transition-all"
    >
      <div class="flex items-center gap-[0.6944rem] min-w-0">
        <CalendarIcon class="w-4 h-4 text-[#6b7280] dark:text-white/55 flex-shrink-0" />
        <span
          class="truncate font-semibold"
          :class="selectedStart ? 'text-[#374151] dark:text-white/90' : 'text-[#b3b3b3] dark:text-white/35'"
        >{{ displayText }}</span>
      </div>
      <span
        class="flex items-center justify-center w-6 h-6 rounded-full bg-[#f5f7f9] dark:bg-white/8 text-[#b3b3b3] dark:text-white/55 flex-shrink-0 transition-transform duration-300"
        :class="{ 'rotate-180': isOpen }"
      >
        <ChevronDownIcon class="w-[0.9722rem] h-[0.9722rem]" />
      </span>
    </button>

    <!-- Calendar Popup -->
    <Teleport to="body">
      <Transition name="fade-scale">
        <div
          v-if="isOpen"
          class="calendar-popup drp-popup fixed bg-white dark:bg-[#2C2F3D] rounded-xl shadow-2xl border border-gray-200 dark:border-white/10 p-4 z-[99999] w-[min(44.4444rem,calc(100vw-1.6667rem))]"
          :style="calendarPosition"
          @click.stop
        >
        <!-- Quick Period Buttons -->
        <div class="drp-quick-row flex flex-wrap items-center gap-2 mb-4 pb-4 border-b border-gray-100 dark:border-white/10">
          <button
            v-for="period in quickPeriods"
            :key="period.value"
            @click="selectQuickPeriod(period.value)"
            class="drp-quick px-3 py-1.5 text-[0.7639rem] font-bold text-gray-600 dark:text-white/75 hover:text-blue-600 dark:hover:text-[#4A7AFF] hover:bg-blue-50 dark:hover:bg-white/5 rounded-lg transition-all"
            :class="{ 'text-blue-600 dark:text-[#4A7AFF] bg-blue-50 dark:bg-white/10': selectedQuickPeriod === period.value }"
          >
            {{ period.label }}
          </button>
        </div>

        <!-- Calendar Grid -->
        <div class="drp-month-grid grid grid-cols-1 sm:grid-cols-2 gap-6">
          <!-- Left Calendar -->
          <div>
            <div class="drp-month-head flex items-center justify-between mb-3">
              <button
                @click="previousMonth"
                class="drp-nav p-1.5 rounded-full hover:bg-gray-100 dark:hover:bg-white/5 transition-colors"
              >
                <ChevronLeftIcon class="w-4 h-4 text-gray-600 dark:text-white/75" />
              </button>
              <h3 class="text-sm font-bold text-gray-900 dark:text-gray-100">{{ leftMonthLabel }}</h3>
              <div class="w-6"></div>
            </div>
            <div class="drp-weekdays grid grid-cols-7 gap-1 mb-2">
              <div
                v-for="day in weekDays"
                :key="day"
                class="drp-weekday text-[0.6944rem] font-bold text-center py-1"
                :class="day === 'СБ' || day === 'ВС' ? 'text-red-500' : 'text-gray-500'"
              >
                {{ day }}
              </div>
            </div>
            <div class="drp-days grid grid-cols-7 gap-1">
              <button
                v-for="(day, index) in leftCalendarDays"
                :key="`left-${index}`"
                @click="selectDate(day.date)"
                class="drp-day relative h-8 w-8 rounded-lg text-xs font-bold transition-all"
                :class="getDayClasses(day)"
                :disabled="!day.inMonth"
              >
                {{ day.day }}
              </button>
            </div>
          </div>

          <!-- Right Calendar -->
          <div>
            <div class="drp-month-head flex items-center justify-between mb-3">
              <div class="w-6"></div>
              <h3 class="text-sm font-bold text-gray-900 dark:text-gray-100">{{ rightMonthLabel }}</h3>
              <button
                @click="nextMonth"
                class="drp-nav p-1.5 rounded-full hover:bg-gray-100 dark:hover:bg-white/5 transition-colors"
              >
                <ChevronRightIcon class="w-4 h-4 text-gray-600 dark:text-white/75" />
              </button>
            </div>
            <div class="drp-weekdays grid grid-cols-7 gap-1 mb-2">
              <div
                v-for="day in weekDays"
                :key="day"
                class="drp-weekday text-[0.6944rem] font-bold text-center py-1"
                :class="day === 'СБ' || day === 'ВС' ? 'text-red-500' : 'text-gray-500'"
              >
                {{ day }}
              </div>
            </div>
            <div class="drp-days grid grid-cols-7 gap-1">
              <button
                v-for="(day, index) in rightCalendarDays"
                :key="`right-${index}`"
                @click="selectDate(day.date)"
                class="drp-day relative h-8 w-8 rounded-lg text-xs font-bold transition-all"
                :class="getDayClasses(day)"
                :disabled="!day.inMonth"
              >
                {{ day.day }}
              </button>
            </div>
          </div>
        </div>

        <!-- Date Input Fields -->
        <div class="drp-fields mt-4 pt-4 border-t border-gray-100 dark:border-white/10 flex flex-wrap items-center gap-3">
          <div class="flex-1">
            <label class="drp-label text-[0.6944rem] font-bold text-gray-500 dark:text-white/55 tracking-wider mb-1 block">От</label>
            <input
              type="text"
              v-model="startDateInput"
              @blur="parseStartDate"
              @keyup.enter="parseStartDate"
              placeholder="ДД.ММ.ГГГГ"
              class="drp-input w-full px-3 py-2 border border-gray-200 dark:border-white/10 bg-white dark:bg-[#232637] rounded-lg text-xs font-bold text-gray-700 dark:text-gray-200 focus:border-blue-500 dark:focus:border-[#4A7AFF] focus:ring-2 focus:ring-blue-500/20 outline-none"
            />
          </div>
          <div class="pt-5 text-gray-400 dark:text-gray-500">—</div>
          <div class="flex-1">
            <label class="drp-label text-[0.6944rem] font-bold text-gray-500 dark:text-white/55 tracking-wider mb-1 block">До</label>
            <input
              type="text"
              v-model="endDateInput"
              @blur="parseEndDate"
              @keyup.enter="parseEndDate"
              placeholder="ДД.ММ.ГГГГ"
              class="drp-input w-full px-3 py-2 border border-gray-200 dark:border-white/10 bg-white dark:bg-[#232637] rounded-lg text-xs font-bold text-gray-700 dark:text-gray-200 focus:border-blue-500 dark:focus:border-[#4A7AFF] focus:ring-2 focus:ring-blue-500/20 outline-none"
            />
          </div>
          <button
            @click="applyDates"
            class="drp-apply px-4 py-2 bg-blue-600 text-white rounded-lg text-xs font-bold hover:bg-blue-700 transition-colors mt-5"
          >
            Применить
          </button>
        </div>
      </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { Teleport } from 'vue'
import { CalendarIcon } from '@heroicons/vue/24/outline'
import { ChevronDownIcon, ChevronLeftIcon, ChevronRightIcon } from '@heroicons/vue/24/solid'

const props = defineProps({
  modelValue: {
    type: Object,
    required: true,
    default: () => ({ start: null, end: null })
  },
  triggerText: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const containerRef = ref(null)
const buttonRef = ref(null)
const isOpen = ref(false)
const currentDate = ref(new Date())
const selectedStart = ref(null)
const selectedEnd = ref(null)
const selectedQuickPeriod = ref(null)
const startDateInput = ref('')
const endDateInput = ref('')
const calendarPosition = ref({ top: '0px', left: '0px' })

const weekDays = ['ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ', 'ВС']

const quickPeriods = [
  { label: 'Последняя неделя', value: 'week' },
  { label: '2 недели', value: '2weeks' },
  { label: 'Месяц', value: 'month' },
  { label: 'Квартал', value: 'quarter' },
  { label: 'Полгода', value: 'halfyear' },
  { label: 'Год', value: 'year' },
  { label: 'За все время', value: 'all' }
]

const displayText = computed(() => {
  if (props.triggerText) return props.triggerText
  if (selectedStart.value && selectedEnd.value) {
    return `${formatDateForDisplay(selectedStart.value)} — ${formatDateForDisplay(selectedEnd.value)}`
  }
  if (selectedStart.value) {
    return `${formatDateForDisplay(selectedStart.value)} — ...`
  }
  return 'Выберите период'
})

const leftMonth = computed(() => {
  const date = new Date(currentDate.value.getFullYear(), currentDate.value.getMonth(), 1)
  return date
})

const rightMonth = computed(() => {
  const date = new Date(currentDate.value.getFullYear(), currentDate.value.getMonth() + 1, 1)
  return date
})

const leftMonthLabel = computed(() => {
  return formatMonthYear(leftMonth.value)
})

const rightMonthLabel = computed(() => {
  return formatMonthYear(rightMonth.value)
})

const leftCalendarDays = computed(() => {
  return getCalendarDays(leftMonth.value)
})

const rightCalendarDays = computed(() => {
  return getCalendarDays(rightMonth.value)
})

function formatMonthYear(date) {
  const months = [
    'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
    'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
  ]
  return `${months[date.getMonth()]} ${date.getFullYear()}`
}

function getCalendarDays(monthDate) {
  const year = monthDate.getFullYear()
  const month = monthDate.getMonth()
  
  const firstDay = new Date(year, month, 1)
  const lastDay = new Date(year, month + 1, 0)
  const firstDayOfWeek = (firstDay.getDay() + 6) % 7 // Convert Sunday=0 to Monday=0
  
  const days = []
  
  // Previous month days
  const prevMonthLastDay = new Date(year, month, 0).getDate()
  for (let i = firstDayOfWeek - 1; i >= 0; i--) {
    const day = prevMonthLastDay - i
    const date = new Date(year, month - 1, day)
    days.push({
      day,
      date: new Date(date),
      inMonth: false
    })
  }
  
  // Current month days
  for (let day = 1; day <= lastDay.getDate(); day++) {
    const date = new Date(year, month, day)
    days.push({
      day,
      date: new Date(date),
      inMonth: true
    })
  }
  
  // Next month days
  const remainingDays = 42 - days.length // 6 rows * 7 days
  for (let day = 1; day <= remainingDays; day++) {
    const date = new Date(year, month + 1, day)
    days.push({
      day,
      date: new Date(date),
      inMonth: false
    })
  }
  
  return days
}

function getDayClasses(day) {
  if (!day.inMonth) {
    return 'text-gray-300 dark:text-gray-600 cursor-not-allowed'
  }

  const dayDate = day.date instanceof Date ? day.date : new Date(day.date)
  if (isNaN(dayDate.getTime())) {
    return 'text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-white/5'
  }

  const now = new Date()
  const isToday = dayDate.getDate() === now.getDate() && dayDate.getMonth() === now.getMonth() && dayDate.getFullYear() === now.getFullYear()
  const todayRing = isToday ? ' ring-2 ring-blue-400 dark:ring-[#4A7AFF] ring-offset-1 dark:ring-offset-[#2C2F3D]' : ''

  if (!selectedStart.value) {
    return 'text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-white/5' + todayRing
  }

  const dateStr = formatDate(dayDate)
  const startStr = formatDate(selectedStart.value)
  const isStart = startStr === dateStr
  const isEnd = selectedEnd.value && formatDate(selectedEnd.value) === dateStr

  let isInRange = false
  if (selectedStart.value && selectedEnd.value) {
    const dayTime = dayDate.getTime()
    const startTime = selectedStart.value instanceof Date ? selectedStart.value.getTime() : new Date(selectedStart.value).getTime()
    const endTime = selectedEnd.value instanceof Date ? selectedEnd.value.getTime() : new Date(selectedEnd.value).getTime()
    isInRange = dayTime > startTime && dayTime < endTime
  }

  if (isStart) {
    return 'bg-blue-600 text-white rounded-full hover:bg-blue-700' + todayRing
  }
  if (isEnd) {
    return 'bg-red-500 text-white rounded-full hover:bg-red-600' + todayRing
  }
  if (isInRange) {
    return 'bg-blue-100 dark:bg-[#4A7AFF]/15 text-blue-700 dark:text-[#8BB7FF]' + todayRing
  }

  return 'text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-white/5' + todayRing
}

function selectDate(date) {
  if (!date) return
  
  // Ensure date is a Date object
  const dateObj = date instanceof Date ? date : new Date(date)
  if (isNaN(dateObj.getTime())) return
  
  const dateStr = formatDate(dateObj)
  
  if (!selectedStart.value || (selectedStart.value && selectedEnd.value)) {
    // Start new selection
    selectedStart.value = new Date(dateObj)
    selectedEnd.value = null
    selectedQuickPeriod.value = null
  } else if (selectedStart.value && !selectedEnd.value) {
    // Complete selection
    const startDate = selectedStart.value instanceof Date ? selectedStart.value : new Date(selectedStart.value)
    if (dateObj < startDate) {
      // If clicked date is before start, swap them
      selectedEnd.value = new Date(startDate)
      selectedStart.value = new Date(dateObj)
    } else {
      selectedEnd.value = new Date(dateObj)
    }
    updateInputs()
  }
}

function selectQuickPeriod(period) {
  selectedQuickPeriod.value = period
  const end = new Date()
  let start = new Date()
  
  switch (period) {
    case 'week':
      start.setDate(end.getDate() - 6)
      break
    case '2weeks':
      start.setDate(end.getDate() - 13)
      break
    case 'month':
      start.setMonth(end.getMonth() - 1)
      break
    case 'quarter':
      start.setMonth(end.getMonth() - 3)
      break
    case 'halfyear':
      start.setMonth(end.getMonth() - 6)
      break
    case 'year':
      start.setFullYear(end.getFullYear() - 1)
      break
    case 'all':
      start = new Date(2020, 0, 1) // Arbitrary old date
      break
  }
  
  selectedStart.value = start
  selectedEnd.value = end
  updateInputs()
  applyDates()
}

function previousMonth() {
  currentDate.value = new Date(currentDate.value.getFullYear(), currentDate.value.getMonth() - 1, 1)
}

function nextMonth() {
  currentDate.value = new Date(currentDate.value.getFullYear(), currentDate.value.getMonth() + 1, 1)
}

function formatDate(date) {
  if (!date) return ''
  // Ensure date is a Date object
  const dateObj = date instanceof Date ? date : new Date(date)
  if (isNaN(dateObj.getTime())) return ''
  const year = dateObj.getFullYear()
  const month = String(dateObj.getMonth() + 1).padStart(2, '0')
  const day = String(dateObj.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function formatDateForDisplay(date) {
  if (!date) return ''
  // Ensure date is a Date object
  const dateObj = date instanceof Date ? date : new Date(date)
  if (isNaN(dateObj.getTime())) return ''
  const day = String(dateObj.getDate()).padStart(2, '0')
  const month = String(dateObj.getMonth() + 1).padStart(2, '0')
  const year = dateObj.getFullYear()
  return `${day}.${month}.${year}`
}

function parseDateInput(input) {
  // Parse DD.MM.YYYY format
  const parts = input.trim().split('.')
  if (parts.length !== 3) return null
  
  const day = parseInt(parts[0], 10)
  const month = parseInt(parts[1], 10) - 1
  const year = parseInt(parts[2], 10)
  
  if (isNaN(day) || isNaN(month) || isNaN(year)) return null
  if (month < 0 || month > 11) return null
  if (day < 1 || day > 31) return null
  
  const date = new Date(year, month, day)
  if (date.getDate() !== day || date.getMonth() !== month || date.getFullYear() !== year) {
    return null // Invalid date
  }
  
  return date
}

function parseStartDate() {
  const date = parseDateInput(startDateInput.value)
  if (date) {
    selectedStart.value = date
    if (selectedEnd.value) {
      const endDate = selectedEnd.value instanceof Date ? selectedEnd.value : new Date(selectedEnd.value)
      if (date > endDate) {
        selectedEnd.value = null
      }
    }
    updateInputs()
  } else {
    updateInputs() // Reset to current value
  }
}

function parseEndDate() {
  const date = parseDateInput(endDateInput.value)
  if (date) {
    if (selectedStart.value) {
      const startDate = selectedStart.value instanceof Date ? selectedStart.value : new Date(selectedStart.value)
      if (date < startDate) {
        selectedEnd.value = new Date(startDate)
        selectedStart.value = date
      } else {
        selectedEnd.value = date
      }
    } else {
      selectedEnd.value = date
    }
    updateInputs()
  } else {
    updateInputs() // Reset to current value
  }
}

function updateInputs() {
  if (selectedStart.value) {
    startDateInput.value = formatDateForDisplay(selectedStart.value)
  }
  if (selectedEnd.value) {
    endDateInput.value = formatDateForDisplay(selectedEnd.value)
  }
}

function applyDates() {
  if (selectedStart.value && selectedEnd.value) {
    emit('update:modelValue', {
      start: formatDate(selectedStart.value),
      end: formatDate(selectedEnd.value)
    })
    emit('change', {
      start: formatDate(selectedStart.value),
      end: formatDate(selectedEnd.value)
    })
    isOpen.value = false
  }
}

function updateCalendarPosition() {
  if (!buttonRef.value || !isOpen.value) return
  
  nextTick(() => {
    const rect = buttonRef.value.getBoundingClientRect()
    const popup = document.querySelector('.calendar-popup.drp-popup')
    const calendarWidth = popup?.getBoundingClientRect().width
      || Math.min(window.innerWidth < 700 ? 320 : 420, window.innerWidth - 24)
    const padding = 16
    
    let left = rect.left
    
    // Ensure calendar doesn't go off the left edge
    if (left < padding) {
      left = padding
    }
    
    // Ensure calendar doesn't go off the right edge
    if (left + calendarWidth > window.innerWidth - padding) {
      left = window.innerWidth - calendarWidth - padding
    }
    left = Math.max(12, left)
    
    // Position below button
    const top = rect.bottom + 8
    
    calendarPosition.value = {
      top: `${top}px`,
      left: `${left}px`
    }
  })
}

function toggleCalendar() {
  isOpen.value = !isOpen.value
  if (isOpen.value) {
    updateCalendarPosition()
  }
}

function close() {
  isOpen.value = false
}

// Click outside handler
const handleClickOutside = (event) => {
  if (!isOpen.value || !containerRef.value) return
  
  const button = containerRef.value.querySelector('button')
  const popup = document.querySelector('.calendar-popup.drp-popup')
  if (popup && !popup.contains(event.target) && button && !button.contains(event.target)) {
    close()
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  window.addEventListener('resize', updateCalendarPosition)
  window.addEventListener('scroll', updateCalendarPosition, true)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  window.removeEventListener('resize', updateCalendarPosition)
  window.removeEventListener('scroll', updateCalendarPosition, true)
})

// Initialize from props
watch(() => props.modelValue, (newValue) => {
  if (newValue?.start) {
    const startDate = new Date(newValue.start)
    if (!isNaN(startDate.getTime())) {
      selectedStart.value = startDate
    }
  } else {
    selectedStart.value = null
  }
  if (newValue?.end) {
    const endDate = new Date(newValue.end)
    if (!isNaN(endDate.getTime())) {
      selectedEnd.value = endDate
    }
  } else {
    selectedEnd.value = null
  }
  updateInputs()
}, { immediate: true })

onMounted(() => {
  if (props.modelValue?.start) {
    const startDate = new Date(props.modelValue.start)
    if (!isNaN(startDate.getTime())) {
      selectedStart.value = startDate
    }
  }
  if (props.modelValue?.end) {
    const endDate = new Date(props.modelValue.end)
    if (!isNaN(endDate.getTime())) {
      selectedEnd.value = endDate
    }
  }
  updateInputs()
})
</script>

<style scoped>
.fade-scale-enter-active,
.fade-scale-leave-active {
  transition: all 0.2s ease;
}

.fade-scale-enter-from,
.fade-scale-leave-to {
  opacity: 0;
  transform: scale(0.95) translateY(-0.6944rem);
}

:global(.calendar-popup) {
  width: min(38.8889rem, calc(100vw - 1.6667rem)) !important;
  max-height: min(36.1111rem, calc(100vh - 1.6667rem));
  overflow: auto;
  padding: 1.1111rem !important;
  border: 1px solid #ebebeb !important;
  border-radius: 0.9722rem !important;
  background: #fff !important;
  box-shadow: 0 18px 48px rgba(15, 23, 42, 0.12) !important;
}

:global(.calendar-popup .drp-quick-row) {
  gap: 0.4167rem !important;
  margin: 0 0 0.9722rem !important;
  padding: 0 0 0.8333rem !important;
  border-bottom: 1px solid #eef0f3 !important;
  align-items: center !important;
}

:global(.calendar-popup .drp-quick) {
  height: 1.9444rem !important;
  min-height: 0 !important;
  padding: 0 0.6944rem !important;
  border: 1px solid #eef0f3 !important;
  border-radius: 0.625rem !important;
  background: #f7f8fa !important;
  color: #4b5563 !important;
  font-size: 0.8333rem !important;
  line-height: 1 !important;
  font-weight: 600 !important;
  letter-spacing: 0 !important;
}

:global(.calendar-popup .drp-quick:hover),
:global(.calendar-popup .drp-quick.text-blue-600) {
  color: #2563eb !important;
  border-color: #dbeafe !important;
  background: #eff6ff !important;
}

:global(.calendar-popup .drp-month-grid) {
  gap: 1.5278rem !important;
}

:global(.calendar-popup .drp-month-head) {
  margin-bottom: 0.6944rem !important;
}

:global(.calendar-popup .drp-month-head h3) {
  color: #111827 !important;
  font-size: 1.0417rem !important;
  line-height: 1.2 !important;
  font-weight: 700 !important;
  letter-spacing: 0 !important;
}

:global(.calendar-popup .drp-nav) {
  width: 1.6667rem !important;
  height: 1.6667rem !important;
  min-height: 1.6667rem !important;
  padding: 0 !important;
  border-radius: 69.375rem !important;
  color: #4b5563 !important;
  background: transparent !important;
}

:global(.calendar-popup .drp-nav:hover) {
  background: #f3f6fb !important;
}

:global(.calendar-popup .drp-nav svg) {
  width: 0.9722rem !important;
  height: 0.9722rem !important;
  color: currentColor !important;
}

:global(.calendar-popup .drp-weekdays) {
  gap: 0.2778rem !important;
  margin-bottom: 0.2778rem !important;
}

:global(.calendar-popup .drp-weekday) {
  padding: 0 !important;
  color: #6b7280 !important;
  font-size: 0.6944rem !important;
  line-height: 1.3889rem !important;
  font-weight: 600 !important;
  letter-spacing: 0 !important;
  text-transform: lowercase !important;
}

:global(.calendar-popup .drp-weekday.text-red-500) {
  color: #ef4444 !important;
}

:global(.calendar-popup .drp-days) {
  gap: 0.2778rem !important;
}

:global(.calendar-popup .drp-day) {
  width: 2.0833rem !important;
  height: 2.0833rem !important;
  min-height: 2.0833rem !important;
  padding: 0 !important;
  border-radius: 0.5556rem !important;
  border: 0 !important;
  font-size: 0.8333rem !important;
  line-height: 1 !important;
  font-weight: 600 !important;
  letter-spacing: 0 !important;
}

:global(.calendar-popup .drp-day:hover:not(:disabled)) {
  background: #edf4ff !important;
  color: #2563eb !important;
}

:global(.calendar-popup .drp-day.bg-blue-600),
:global(.calendar-popup .drp-day.bg-red-500) {
  color: #fff !important;
  background: #2563eb !important;
  border-radius: 0.5556rem !important;
}

:global(.calendar-popup .drp-day.bg-red-500) {
  background: #ef4444 !important;
}

:global(.calendar-popup .drp-day.bg-blue-100) {
  background: #dbeafe !important;
  color: #2563eb !important;
}

:global(.calendar-popup .drp-day.text-gray-300) {
  color: #c9cfd8 !important;
}

:global(.calendar-popup .drp-fields) {
  gap: 0.6944rem !important;
  margin-top: 1.1111rem !important;
  padding-top: 0.8333rem !important;
  border-top: 1px solid #eef0f3 !important;
  align-items: end !important;
}

:global(.calendar-popup .drp-label) {
  margin: 0 0 0.4167rem !important;
  color: #6b7280 !important;
  font-size: 0.7639rem !important;
  line-height: 1 !important;
  font-weight: 600 !important;
  letter-spacing: 0 !important;
  text-transform: none !important;
}

:global(.calendar-popup .drp-input) {
  height: 2.6389rem !important;
  padding: 0 0.8333rem !important;
  border: 1px solid #d9dee6 !important;
  border-radius: 0.6944rem !important;
  background: #fff !important;
  color: #374151 !important;
  font-size: 0.8333rem !important;
  line-height: 1 !important;
  font-weight: 600 !important;
  letter-spacing: 0 !important;
  box-shadow: none !important;
}

:global(.calendar-popup .drp-input:focus) {
  border-color: #2563eb !important;
  box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.1) !important;
}

:global(.calendar-popup .drp-fields > .text-gray-400) {
  padding-bottom: 0.6944rem !important;
  color: #9ca3af !important;
  font-size: 1.1111rem !important;
}

:global(.calendar-popup .drp-apply) {
  height: 2.6389rem !important;
  min-height: 2.6389rem !important;
  margin: 0 !important;
  padding: 0 1.25rem !important;
  border-radius: 0.625rem !important;
  background: #2563eb !important;
  color: #fff !important;
  font-size: 0.8333rem !important;
  line-height: 1 !important;
  font-weight: 600 !important;
}

:global(.calendar-popup .drp-apply:hover) {
  background: #1d4ed8 !important;
}

:global(html.dark .calendar-popup),
:global(html.darkmode .calendar-popup) {
  border-color: rgba(255, 255, 255, 0.1) !important;
  background: #2c2f3d !important;
  box-shadow: 0 20px 54px rgba(0, 0, 0, 0.34) !important;
}

:global(html.dark .calendar-popup .drp-quick-row),
:global(html.darkmode .calendar-popup .drp-quick-row),
:global(html.dark .calendar-popup .drp-fields),
:global(html.darkmode .calendar-popup .drp-fields) {
  border-color: rgba(255, 255, 255, 0.1) !important;
}

:global(html.dark .calendar-popup .drp-quick),
:global(html.darkmode .calendar-popup .drp-quick) {
  background: rgba(255, 255, 255, 0.06) !important;
  color: rgba(255, 255, 255, 0.72) !important;
}

:global(html.dark .calendar-popup .drp-quick:hover),
:global(html.darkmode .calendar-popup .drp-quick:hover),
:global(html.dark .calendar-popup .drp-quick.text-blue-600),
:global(html.darkmode .calendar-popup .drp-quick.text-blue-600) {
  border-color: rgba(74, 122, 255, 0.28) !important;
  background: rgba(74, 122, 255, 0.14) !important;
  color: #8fb0ff !important;
}

:global(html.dark .calendar-popup .drp-month-head h3),
:global(html.darkmode .calendar-popup .drp-month-head h3) {
  color: #f8fafc !important;
}

:global(html.dark .calendar-popup .drp-nav),
:global(html.darkmode .calendar-popup .drp-nav),
:global(html.dark .calendar-popup .drp-weekday),
:global(html.darkmode .calendar-popup .drp-weekday),
:global(html.dark .calendar-popup .drp-label),
:global(html.darkmode .calendar-popup .drp-label),
:global(html.dark .calendar-popup .drp-fields > .text-gray-400),
:global(html.darkmode .calendar-popup .drp-fields > .text-gray-400) {
  color: rgba(255, 255, 255, 0.58) !important;
}

:global(html.dark .calendar-popup .drp-nav:hover),
:global(html.darkmode .calendar-popup .drp-nav:hover),
:global(html.dark .calendar-popup .drp-day:hover:not(:disabled)),
:global(html.darkmode .calendar-popup .drp-day:hover:not(:disabled)) {
  background: rgba(74, 122, 255, 0.14) !important;
  color: #8fb0ff !important;
}

:global(html.dark .calendar-popup .drp-day),
:global(html.darkmode .calendar-popup .drp-day) {
  color: rgba(255, 255, 255, 0.82) !important;
}

:global(html.dark .calendar-popup .drp-day.text-gray-300),
:global(html.darkmode .calendar-popup .drp-day.text-gray-300) {
  color: rgba(255, 255, 255, 0.24) !important;
}

:global(html.dark .calendar-popup .drp-day.bg-blue-100),
:global(html.darkmode .calendar-popup .drp-day.bg-blue-100) {
  background: rgba(74, 122, 255, 0.18) !important;
  color: #8fb0ff !important;
}

:global(html.dark .calendar-popup .drp-input),
:global(html.darkmode .calendar-popup .drp-input) {
  border-color: rgba(255, 255, 255, 0.12) !important;
  background: #232637 !important;
  color: rgba(255, 255, 255, 0.84) !important;
}

@media (max-width: 480px) {
  :global(.calendar-popup) {
    width: min(22.2222rem, calc(100vw - 1.1111rem)) !important;
    max-height: calc(100vh - 1.1111rem);
    padding: 0.9722rem !important;
  }

  :global(.calendar-popup .drp-quick-row) {
    gap: 0.4167rem !important;
    margin-bottom: 0.8333rem !important;
    padding-bottom: 0.6944rem !important;
  }

  :global(.calendar-popup .drp-quick) {
    height: 1.9444rem !important;
    padding: 0 0.5556rem !important;
    font-size: 0.7639rem !important;
  }

  :global(.calendar-popup .drp-month-grid) {
    grid-template-columns: 1fr !important;
    gap: 1.1111rem !important;
  }

  :global(.calendar-popup .drp-month-head h3) {
    font-size: 1.0417rem !important;
  }

  :global(.calendar-popup .drp-weekdays),
  :global(.calendar-popup .drp-days) {
    gap: 0.2778rem !important;
  }

  :global(.calendar-popup .drp-day) {
    width: 2.3611rem !important;
    height: 2.3611rem !important;
    min-height: 2.3611rem !important;
    font-size: 0.8333rem !important;
    border-radius: 0.5556rem !important;
  }

  :global(.calendar-popup .drp-weekday) {
    font-size: 0.6944rem !important;
    line-height: 1.3889rem !important;
  }

  :global(.calendar-popup .drp-fields) {
    display: grid !important;
    grid-template-columns: 1fr !important;
    gap: 0.5556rem !important;
    margin-top: 0.9722rem !important;
    padding-top: 0.8333rem !important;
  }

  :global(.calendar-popup .drp-fields > .text-gray-400) {
    display: none !important;
  }

  :global(.calendar-popup .drp-label) {
    font-size: 0.7639rem !important;
  }

  :global(.calendar-popup .drp-input) {
    height: 2.6389rem !important;
    font-size: 0.8333rem !important;
  }

  :global(.calendar-popup .drp-apply) {
    width: 100% !important;
    height: 2.6389rem !important;
    margin-top: 0.2778rem !important;
    font-size: 0.8333rem !important;
  }
}
</style>
