<script setup lang="ts">
import { onMounted, onBeforeUnmount } from 'vue'
import Lenis from 'lenis'

let lenis: Lenis | null = null
// Keep the RAF handle so teardown can stop the loop cleanly.
let rafId: number | null = null

// Follow the system reduced-motion preference.
let motionQuery: MediaQueryList | null = null
let onMotionChange: (() => void) | null = null

function startLenis() {
  if (lenis) return
  lenis = new Lenis({
    duration: 1.2,
    easing: (t: number) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
    smoothWheel: true,
  })

  function raf(time: number) {
    // 守卫：lenis 已被销毁/置空时不再续帧，避免卸载后空转
    if (!lenis) return
    lenis.raf(time)
    rafId = requestAnimationFrame(raf)
  }
  rafId = requestAnimationFrame(raf)
}

function stopLenis() {
  if (rafId !== null) {
    cancelAnimationFrame(rafId)
    rafId = null
  }
  lenis?.destroy()
  lenis = null
}

onMounted(() => {
  // A6：开启"减少动态效果"的用户**根本不创建 Lenis 实例**，完全交回浏览器原生滚动。
  // 注意这里不是"把 duration 调小"：Lenis 会接管滚轮事件，只要它活着，
  // 滚动就仍然是"被平滑过的"，与用户的系统偏好相悖。
  motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
  onMotionChange = () => {
    if (motionQuery?.matches) stopLenis()
    else startLenis()
  }
  motionQuery.addEventListener('change', onMotionChange)

  if (!motionQuery.matches) startLenis()
})

onBeforeUnmount(() => {
  if (motionQuery && onMotionChange) {
    motionQuery.removeEventListener('change', onMotionChange)
  }
  motionQuery = null
  onMotionChange = null
  stopLenis()
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
