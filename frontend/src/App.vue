<script setup lang="ts">
import { onMounted, onBeforeUnmount } from 'vue'
import Lenis from 'lenis'
import PendingDrawer from '@/components/PendingDrawer.vue'
import AppToast from '@/components/AppToast.vue'
import { usePendingTasks } from '@/composables/usePendingTasks'

const { toggleDrawer } = usePendingTasks()

/**
 * 全局快捷键：`Ctrl/Cmd + K` 唤出待做抽屉。
 *
 * 为什么放在 App 层：抽屉的判据是"**随时**点击就能看到"（docs/14 §11.1），
 * 所以唤出入口必须与路由无关。放这里后在任何页面都能用。
 *
 * 刻意不用单键（如 `t`）：那会在输入框里打字时误触。
 * 也刻意跳过"已打开其它对话框"的情况——抽屉自身靠 useDialogFocus 处理 Escape。
 */
function onGlobalKeydown(event: KeyboardEvent) {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault()
    toggleDrawer()
  }
}

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

  window.addEventListener('keydown', onGlobalKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onGlobalKeydown)
  if (motionQuery && onMotionChange) {
    motionQuery.removeEventListener('change', onMotionChange)
  }
  motionQuery = null
  onMotionChange = null
  stopLenis()
})
</script>

<template>
  <!-- 根容器不再挂 bg-surface：它与 index.html 的 <body class="bg-[#0f0f14]"> 是同一个
       #0f0f14，属重复的一层页面底色；各页面要么自带不透明背景（Bills 的星空画布、
       Notes 自己的渐变），要么透出 body 的底色。文字色仍在这里统一。 -->
  <div class="min-h-screen text-text">
    <router-view v-slot="{ Component }">
      <transition name="fade" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>

    <!-- 待做事项抽屉：挂在根组件上，因此在任何路由下都能唤出（Ctrl/Cmd+K）。
         它常驻挂载、由**组件内部**的 v-if 控制面板显示——
         `useDialogFocus` 依赖 watch(open)，若连组件一起 v-if 掉，焦点陷阱与 Escape 就会失效。 -->
    <PendingDrawer />

    <!-- 全站顶部提示（含倒计时进度条）：作废提示、主题"待开发"提示都用它。
         挂根组件是因为提示显示在页面顶部，而触发点可能在抽屉内或某个页面里。 -->
    <AppToast />
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
