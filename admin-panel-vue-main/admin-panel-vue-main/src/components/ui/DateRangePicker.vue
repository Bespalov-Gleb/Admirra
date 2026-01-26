<template>
  <div class="relative">
    <!-- Trigger Button -->
    <button
      @click="isOpen = !isOpen"
      class="flex items-center gap-2 px-3 py-2 bg-white border border-gray-200 rounded-lg text-xs font-bold text-gray-700 hover:border-blue-500 hover:bg-blue-50/50 transition-all min-w-[200px] justify-between"
    >
      <div class="flex items-center gap-2">
        <CalendarIcon class="w-4 h-4 text-gray-500" />
        <span>{{ displayText }}</span>
      </div>
      <ChevronDownIcon class="w-3 h-3 text-gray-400 flex-shrink-0" :class="{ 'rotate-180': isOpen }" />
    </button>

    <!-- Calendar Popup -->
    <Transition name="fade-scale">
      <div
        v-if="isOpen"
        v-click-outside="close"
        class="absolute top-full left-0 mt-2 bg-white rounded-xl shadow-xl border border-gray-200 p-4 z-50 min-w-[640px]"
      >
        <!-- Quick Period Buttons -->
        <div class="flex items-center gap-2 mb-4 pb-4 border-b border-gray-100">
          <button
            v-for="period in quickPeriods"
            :key="period.value"
            @click="selectQuickPeriod(period.value)"
            class="px-3 py-1.5 text-[11px] font-bold text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-all"
            :class="{ 'text-blue-600 bg-blue-50': selectedQuickPeriod === period.value }"
          >
            {{ period.label }}
          </button>
        </div>

        <!-- Calendar Grid -->
        <div class="grid grid-cols-2 gap-6">
          <!-- Left Calendar -->
          <div>
            <div class="flex items-center justify-between mb-3">
              <button
                @click="previousMonth"
                class="p-1.5 rounded-full hover:bg-gray-100 transition-colors"
              >
                <ChevronLeftIcon class="w-4 h-4 text-gray-600" />
              </button>
              <h3 class="text-sm font-bold text-gray-900">{{ leftMonthLabel }}</h3>
              <div class="w-6"></div>
            </div>
            <div class="grid grid-cols-7 gap-1 mb-2">
              <div
                v-for="day in weekDays"
                :key="day"
                class="text-[10px] font-bold text-center py-1"
                :class="day === 'СБ' || day === 'ВС' ? 'text-red-500' : 'text-gray-500'"
              >
                {{ day }}
              </div>
            </div>
            <div class="grid grid-cols-7 gap-1">
              <button
                v-for="(day, index) in leftCalendarDays"
                :key="`left-${index}`"
                @click="selectDate(day.date)"
                class="relative h-8 w-8 rounded-lg text-xs font-bold transition-all"
                :class="getDayClasses(day)"
                :disabled="!day.inMonth"
              >
                {{ day.day }}
              </button>
            </div>
          </div>

          <!-- Right Calendar -->
          <div>
            <div class="flex items-center justify-between mb-3">
              <div class="w-6"></div>
              <h3 class="text-sm font-bold text-gray-900">{{ rightMonthLabel }}</h3>
              <button
                @click="nextMonth"
                class="p-1.5 rounded-full hover:bg-gray-100 transition-colors"
              >
                <ChevronRightIcon class="w-4 h-4 text-gray-600" />
              </button>
            </div>
            <div class="grid grid-cols-7 gap-1 mb-2">
              <div
                v-for="day in weekDays"
                :key="day"
                class="text-[10px] font-bold text-center py-1"
                :class="day === 'СБ' || day === 'ВС' ? 'text-red-500' : 'text-gray-500'"
              >
                {{ day }}
              </div>
            </div>
            <div class="grid grid-cols-7 gap-1">
              <button
                v-for="(day, index) in rightCalendarDays"
                :key="`right-${index}`"
                @click="selectDate(day.date)"
                class="relative h-8 w-8 rounded-lg text-xs font-bold transition-all"
                :class="getDayClasses(day)"
                :disabled="!day.inMonth"
              >
                {{ day.day }}
              </button>
            </div>
          </div>
        </div>

        <!-- Date Input Fields -->
        <div class="mt-4 pt-4 border-t border-gray-100 flex items-center gap-3">
          <div class="flex-1">
            <label class="text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-1 block">От</label>
            <input
              type="text"
              v-model="startDateInput"
              @blur="parseStartDate"
              @keyup.enter="parseStartDate"
              placeholder="ДД.ММ.ГГГГ"
              class="w-full px-3 py-2 border border-gray-200 rounded-lg text-xs font-bold text-gray-700 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 outline-none"
            />
          </div>
          <div class="pt-5 text-gray-400">—</div>
          <div class="flex-1">
            <label class="text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-1 block">До</label>
            <input
              type="text"
              v-model="endDateInput"
              @blur="parseEndDate"
              @keyup.enter="parseEndDate"
              placeholder="ДД.ММ.ГГГГ"
              class="w-full px-3 py-2 border border-gray-200 rounded-lg text-xs font-bold text-gray-700 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 outline-none"
            />
          </div>
          <button
            @click="applyDates"
            class="px-4 py-2 bg-blue-600 text-white rounded-lg text-xs font-bold hover:bg-blue-700 transition-colors mt-5"
          >
            Применить
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { CalendarIcon } from '@heroicons/vue/24/outline'
import { ChevronDownIcon, ChevronLeftIcon, ChevronRightIcon } from '@heroicons/vue/24/solid'

const props = defineProps({
  modelValue: {
    type: Object,
    required: true,
    default: () => ({ start: null, end: null })
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const isOpen = ref(false)
const currentDate = ref(new Date())
const selectedStart = ref(null)
const selectedEnd = ref(null)
const selectedQuickPeriod = ref(null)
const startDateInput = ref('')
const endDateInput = ref('')

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
    return 'text-gray-300 cursor-not-allowed'
  }
  
  if (!selectedStart.value) {
    return 'text-gray-700 hover:bg-gray-100'
  }
  
  // Ensure day.date is a Date object
  const dayDate = day.date instanceof Date ? day.date : new Date(day.date)
  if (isNaN(dayDate.getTime())) {
    return 'text-gray-700 hover:bg-gray-100'
  }
  
  const dateStr = formatDate(dayDate)
  const startStr = formatDate(selectedStart.value)
  const isStart = startStr === dateStr
  const isEnd = selectedEnd.value && formatDate(selectedEnd.value) === dateStr
  
  // Check if date is in range (between start and end)
  let isInRange = false
  if (selectedStart.value && selectedEnd.value) {
    const dayTime = dayDate.getTime()
    const startTime = selectedStart.value instanceof Date ? selectedStart.value.getTime() : new Date(selectedStart.value).getTime()
    const endTime = selectedEnd.value instanceof Date ? selectedEnd.value.getTime() : new Date(selectedEnd.value).getTime()
    isInRange = dayTime > startTime && dayTime < endTime
  }
  
  if (isStart) {
    return 'bg-blue-600 text-white rounded-full hover:bg-blue-700'
  }
  if (isEnd) {
    return 'bg-red-500 text-white rounded-full hover:bg-red-600'
  }
  if (isInRange) {
    return 'bg-blue-100 text-blue-700'
  }
  
  return 'text-gray-700 hover:bg-gray-100'
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

function close() {
  isOpen.value = false
}

// Click outside directive
const vClickOutside = {
  mounted(el, binding) {
    el.clickOutsideEvent = (event) => {
      if (!(el === event.target || el.contains(event.target))) {
        binding.value()
      }
    }
    document.addEventListener('click', el.clickOutsideEvent)
  },
  unmounted(el) {
    document.removeEventListener('click', el.clickOutsideEvent)
  }
}

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
  transform: scale(0.95) translateY(-10px);
}
</style>

