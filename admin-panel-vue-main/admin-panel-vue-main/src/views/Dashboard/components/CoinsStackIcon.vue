<template>
  <svg 
    :width="size" 
    :height="size" 
    viewBox="0 0 24 24" 
    fill="none" 
    xmlns="http://www.w3.org/2000/svg"
    :class="className"
  >
    <!-- Левая стопка монет -->
    <circle cx="8" cy="12" r="3" :stroke="color" stroke-width="1.5" fill="none"/>
    <line x1="5" y1="12" x2="11" y2="12" :stroke="color" stroke-width="1.5"/>
    <line x1="5" y1="10" x2="11" y2="10" :stroke="color" stroke-width="1.5"/>
    <line x1="5" y1="14" x2="11" y2="14" :stroke="color" stroke-width="1.5"/>
    
    <!-- Правая стопка монет -->
    <circle cx="16" cy="12" r="3" :stroke="color" stroke-width="1.5" fill="none"/>
    <line x1="13" y1="12" x2="19" y2="12" :stroke="color" stroke-width="1.5"/>
    <line x1="13" y1="10" x2="19" y2="10" :stroke="color" stroke-width="1.5"/>
    <line x1="13" y1="14" x2="19" y2="14" :stroke="color" stroke-width="1.5"/>
  </svg>
</template>

<script setup>
defineProps({
  size: {
    type: [String, Number],
    default: 24
  },
  color: {
    type: String,
    default: 'currentColor'
  },
  className: {
    type: String,
    default: ''
  }
})
</script>


