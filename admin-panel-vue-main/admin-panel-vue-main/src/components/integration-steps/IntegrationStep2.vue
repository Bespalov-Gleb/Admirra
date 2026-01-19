<template>
  <div class="space-y-6">
    <!-- Header & Search -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
      <label class="block text-[9px] font-black text-gray-400 uppercase tracking-[0.2em] px-1">ВЫБЕРИТЕ ПРОФИЛЬ ДЛЯ ИНТЕГРАЦИИ</label>
      
      <div v-if="profiles.length > 5 || searchQuery" class="relative group w-full md:w-64">
        <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
          <MagnifyingGlassIcon class="h-4 w-4 text-gray-400 group-focus-within:text-blue-500 transition-colors" />
        </div>
        <input 
          type="text" 
          v-model="searchQuery"
          placeholder="Поиск аккаунта..."
          class="block w-full pl-11 pr-4 py-3 bg-white border border-gray-100 rounded-2xl text-[12px] font-bold text-gray-900 placeholder-gray-400 focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 transition-all shadow-sm"
        >
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-4">
      <div v-for="i in 4" :key="i" class="p-6 bg-white border border-gray-100 rounded-[2rem] shadow-sm flex items-center gap-4 animate-pulse">
        <div class="w-12 h-12 rounded-2xl bg-gray-50"></div>
        <div class="flex-grow space-y-2">
          <div class="h-4 bg-gray-50 rounded-full w-3/4"></div>
          <div class="h-3 bg-gray-50 rounded-full w-1/2"></div>
        </div>
      </div>
    </div>
    
    <!-- Account List / Grid -->
    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-4">
      <div 
        v-for="profile in filteredProfiles" 
        :key="profile.login"
        @click="selectProfile(profile)"
        class="relative group p-6 bg-white border-2 rounded-[2rem] transition-all duration-300 cursor-pointer overflow-hidden shadow-sm hover:shadow-xl hover:-translate-y-1"
        :class="[
          selectedProfile === profile.login ? 'border-blue-600 ring-4 ring-blue-50' : 'border-gray-50 hover:border-blue-200'
        ]"
      >
        <!-- Selection Checkmark -->
        <div 
          class="absolute top-4 right-4 w-6 h-6 rounded-full bg-blue-600 flex items-center justify-center transition-all duration-300 scale-0"
          :class="{ 'scale-100': selectedProfile === profile.login }"
        >
          <CheckIcon class="w-4 h-4 text-white" stroke-width="4" />
        </div>

        <div class="flex items-start gap-4 mb-4">
          <!-- Avatar/Icon -->
          <div 
            class="w-14 h-14 rounded-2xl flex items-center justify-center text-[16px] font-black transition-all group-hover:scale-110 shadow-inner"
            :class="[
              profile.type === 'personal' ? 'bg-orange-50 text-orange-600' : 
              profile.type === 'agency_client' ? 'bg-blue-50 text-blue-600' :
              'bg-gray-50 text-gray-600'
            ]"
          >
            {{ profile.login.substring(0, 2).toUpperCase() }}
          </div>
          
          <div class="flex-grow pt-1">
            <h3 class="text-[14px] font-black text-gray-900 group-hover:text-blue-600 transition-colors leading-tight mb-1">
              {{ profile.name || profile.login }}
            </h3>
            <p class="text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-2">
              {{ profile.login }}
            </p>
            
            <!-- Type Tag & Balance -->
            <div class="flex items-center flex-wrap gap-2">
              <span 
                class="px-2.5 py-1 rounded-full text-[8px] font-black uppercase tracking-widest border"
                :class="[
                  profile.type === 'personal' ? 'bg-orange-50/50 text-orange-600 border-orange-100' : 
                  profile.type === 'agency_client' ? 'bg-blue-50/50 text-blue-600 border-blue-100' :
                  'bg-gray-50 text-gray-500 border-gray-100'
                ]"
              >
                {{ 
                  profile.type === 'personal' ? 'Личный' : 
                  profile.type === 'agency_client' ? 'Клиент агентства' : 
                  profile.type === 'managed' ? 'Редактор' : 'Аккаунт'
                }}
              </span>
              
              <div v-if="profile.currency" class="flex items-center gap-1.5 px-2.5 py-1 bg-green-50 rounded-full border border-green-100/50">
                <span class="text-[9px] font-black text-green-600 uppercase tracking-wider">{{ profile.currency }}</span>
                <span v-if="profile.balance !== undefined" class="text-[10px] font-black text-green-700">
                  {{ formatMoney(profile.balance, profile.currency) }}
                </span>
              </div>

              <span v-if="profile.description" class="text-[10px] text-gray-400 font-medium italic overflow-hidden text-ellipsis whitespace-nowrap max-w-[150px]">
                {{ profile.description }}
              </span>
            </div>
          </div>
        </div>
        
        <!-- NEW: Campaign Statistics Grid -->
        <div v-if="profile.campaigns_count !== undefined" class="grid grid-cols-3 gap-3 pt-4 border-t border-gray-100">
          <div class="text-center">
            <p class="text-lg font-black text-blue-600">{{ profile.campaigns_count || 0 }}</p>
            <p class="text-[9px] text-gray-400 uppercase tracking-wider font-bold">Кампаний</p>
          </div>
          <div class="text-center">
            <p class="text-lg font-black text-green-600">{{ profile.active_campaigns || 0 }}</p>
            <p class="text-[9px] text-gray-400 uppercase tracking-wider font-bold">Активных</p>
          </div>
          <div class="text-center">
            <p class="text-sm font-black text-gray-700">{{ formatMoney(profile.monthly_spend || 0, profile.currency) }}</p>
            <p class="text-[9px] text-gray-400 uppercase tracking-wider font-bold">Расход/мес</p>
          </div>
        </div>
      </div>

      <!-- Empty Result -->
      <div v-if="filteredProfiles.length === 0" class="col-span-full py-16 flex flex-col items-center justify-center bg-gray-50/50 rounded-[3rem] border border-dashed border-gray-200">
        <div class="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
          <MagnifyingGlassIcon class="w-8 h-8 text-gray-300" />
        </div>
        <p class="text-[13px] font-black text-gray-400 uppercase tracking-widest">Профили не найдены</p>
        <p class="text-[10px] text-gray-400 mt-2">Попробуйте изменить запрос поиска</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { MagnifyingGlassIcon } from '@heroicons/vue/20/solid'
import { CheckIcon } from '@heroicons/vue/24/outline'

const props = defineProps({
  profiles: Array,
  selectedProfile: String,
  loading: Boolean,
  platform: String
})

const emit = defineEmits(['select', 'next'])

const searchQuery = ref('')

const formatMoney = (val, currency = 'RUB') => {
  try {
    return new Intl.NumberFormat('ru-RU', { 
      style: 'currency', 
      currency: currency === 'RUB' ? 'RUB' : (currency || 'RUB'), 
      maximumFractionDigits: 0 
    }).format(val)
  } catch (e) {
    return `${val} ${currency}`
  }
}

const filteredProfiles = computed(() => {
  if (!props.profiles) return []
  if (!searchQuery.value) return props.profiles
  const q = searchQuery.value.toLowerCase()
  return props.profiles.filter(p => 
    (p.name && p.name.toLowerCase().includes(q)) || 
    (p.login && p.login.toLowerCase().includes(q))
  )
})

const selectProfile = (profile) => {
  emit('select', profile)
}
</script>
