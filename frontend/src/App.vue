<script setup lang="ts">
import { onMounted, onBeforeUnmount } from 'vue'
import Lenis from 'lenis'

let lenis: Lenis | null = null

onMounted(() => {
  lenis = new Lenis({
    duration: 1.2,
    easing: (t: number) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
    smoothWheel: true,
  })

  function raf(time: number) {
    lenis?.raf(time)
    requestAnimationFrame(raf)
  }
  requestAnimationFrame(raf)
})

onBeforeUnmount(() => {
  lenis?.destroy()
})
</script>

<template>
  <div class="min-h-screen bg-surface text-text">
    <router-view v-slot="{ Component }">
      <transition name="fade" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
  </div>
</template>

<style>
html {
  scroll-behavior: auto; /* Lenis handles smooth scroll */
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
