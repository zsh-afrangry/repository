<script setup lang="ts">
import { onMounted, onBeforeUnmount } from 'vue'
import Lenis from 'lenis'

let lenis: Lenis | null = null
// 必须持有 RAF 句柄：原实现只调用 requestAnimationFrame(raf) 而丢弃返回值，
// 循环体又无条件排下一帧，于是 destroy() 之后循环仍在跑（开发态每次 HMR 都会
// 再叠一层，旧的永远不停）。详见 docs/4 的动效审计。
let rafId: number | null = null

// A6（2026-09-20 已获批准 — docs/5 §16 A6）：跟随系统的"减少动态效果"。
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
