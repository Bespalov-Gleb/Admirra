<template>
  <div class="min-h-screen main-bg-color">
    <Header />
    <main class="main-bg-color">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import Header from '../components/Header.vue'
</script>

