<template>
  <div class="custom-scroll-container h-full w-full overflow-y-auto overflow-x-hidden">
    <slot></slot>
  </div>
</template>

<script setup>
// No specialized logic needed for now, mainly for styling encapsulation
</script>

<style scoped>
.custom-scroll-container {
  /* For Firefox */
  scrollbar-width: thin;
  scrollbar-color: #E2E8F0 transparent;
}

/* For Chrome, Edge, and Safari */
.custom-scroll-container::-webkit-scrollbar {
  width: 0.4167rem;
}

.custom-scroll-container::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scroll-container::-webkit-scrollbar-thumb {
  background-color: #E2E8F0;
  border-radius: 1.3889rem;
  border: 2px solid transparent;
  background-clip: content-box;
}

.custom-scroll-container::-webkit-scrollbar-thumb:hover {
  background-color: #CBD5E1;
}

/* Optional: Add a subtle fade on edges to indicate more content */
.custom-scroll-container {
  mask-image: linear-gradient(to bottom, 
    transparent, 
    black 1.3889rem, 
    black calc(100% - 1.3889rem), 
    transparent
  );
  -webkit-mask-image: linear-gradient(to bottom, 
    transparent, 
    black 1.3889rem, 
    black calc(100% - 1.3889rem), 
    transparent
  );
}
</style>
