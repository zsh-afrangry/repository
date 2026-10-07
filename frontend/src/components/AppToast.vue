<script setup lang="ts">
/**
 * 全站顶部提示（含倒计时进度条）。挂 `App.vue`，任何页面都可用。
 *
 * **进度条**：底部一条从 100% 缩到 0 的线，走完提示即消失。
 * 它与 JS 计时器**共用同一个 `durationMs`**（见 `useToast`），所以两者不会各走各的。
 *
 * **暂停**：鼠标悬停或键盘聚焦时暂停——提示里可能有「撤销」按钮，
 * 若倒计时照走，用户正要点时弹窗先没了。键盘用户更明显：
 * Tab 到按钮上时弹窗消失，等于这个按钮不可达。
 *
 * ⚠️ **进度条是"信息"不是"装饰"**（它告诉你还剩多久），
 * 所以 `prefers-reduced-motion` 下**保留**进度条本体、只去掉动画的过渡感，
 * 而不是像页面滚动那样整个关掉。
 */
import { computed } from 'vue'

import { useToast } from '@/composables/useToast'

const { toast, isPaused, pause, resume, dismiss, runAction } = useToast()

/**
 * 进度条的动画时长。
 *
 * ⚠️ 必须是"当前这条的时长"，而 `:key` 变化会重建元素 → 动画重新开始。
 * 两者配合才能保证：连续弹两条不同时长的提示时，第二条的进度条按自己的节奏走。
 */
const barDuration = computed(() => `${toast.value?.durationMs ?? 5000}ms`)
</script>

<template>
  <Transition name="app-toast">
    <div
      v-if="toast"
      :key="toast.key"
      class="app-toast"
      role="status"
      aria-live="polite"
      @mouseenter="pause()"
      @mouseleave="resume()"
      @focusin="pause()"
      @focusout="resume()"
    >
      <div class="app-toast-row">
        <div class="app-toast-body">
          <strong class="app-toast-text">{{ toast.text }}</strong>
          <span v-if="toast.detail" class="app-toast-detail">{{ toast.detail }}</span>
        </div>
        <button
          v-if="toast.action"
          type="button"
          class="app-toast-action"
          :disabled="toast.actionBusy"
          @click="runAction()"
        >
          {{ toast.action.label }}
        </button>
        <button
          type="button"
          class="app-toast-close"
          aria-label="关闭提示"
          @click="dismiss()"
        >
          ×
        </button>
      </div>

      <!-- 倒计时进度条：宽度 100% → 0%。暂停时用 animation-play-state 同步停住。 -->
      <div
        class="app-toast-progress"
        :class="{ paused: isPaused }"
        :style="{ animationDuration: barDuration }"
        aria-hidden="true"
      ></div>
    </div>
  </Transition>
</template>

<style scoped>
.app-toast {
  position: fixed;
  /* 位置：**中间偏上**。与原先 `.theme-toast` 完全一致：
     桌面 10%、窄屏 8%。用 left:50% + translateX(-50%) 水平居中，
     top 用百分比以便随视口高度走。
     ⚠️ 因为基类已占用 transform 做水平居中，进/出场动画必须写成
     translate(-50%, …)，否则会丢掉居中、从视口左侧滑入。 */
  top: 10%;
  left: 50%;
  transform: translateX(-50%);
  z-index: 95;
  width: max-content;
  max-width: min(24rem, calc(100vw - 2rem));
  /* 进度条要贴底，所以本体不加内边距，由内层控制 */
  padding: 0;
  overflow: hidden;
  border: 1px solid var(--border-color);
  border-radius: 0.9rem;
  background: var(--card-bg);
  box-shadow: 0 18px 45px rgb(0 0 0 / 0.45);
}

.app-toast-row {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  padding: 0.7rem 0.85rem 0.7rem 1rem;
}

.app-toast-body {
  display: grid;
  gap: 0.15rem;
  min-width: 0;
}

.app-toast-text {
  color: var(--text-title);
  font-size: 0.82rem;
  font-weight: 700;
  overflow-wrap: anywhere;
}

.app-toast-detail {
  color: var(--text-secondary);
  font-size: 0.72rem;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.app-toast-action {
  flex-shrink: 0;
  padding: 0.25rem 0.6rem;
  border: 1px solid var(--primary-btn-border, var(--border-color));
  border-radius: 0.5rem;
  background: transparent;
  color: var(--project-accent, #67e8f9);
  font: inherit;
  font-size: 0.76rem;
  font-weight: 800;
  cursor: pointer;
}
.app-toast-action:hover:not(:disabled),
.app-toast-action:focus-visible {
  background: rgb(255 255 255 / 0.08);
}
.app-toast-action:focus-visible {
  outline: 2px solid var(--project-accent, #67e8f9);
  outline-offset: 2px;
}
.app-toast-action:disabled {
  opacity: 0.5;
  cursor: default;
}

.app-toast-close {
  display: grid;
  width: 1.4rem;
  height: 1.4rem;
  flex-shrink: 0;
  place-items: center;
  border: 0;
  border-radius: 0.4rem;
  background: transparent;
  color: var(--text-secondary);
  font-size: 1rem;
  line-height: 1;
  cursor: pointer;
}
.app-toast-close:hover,
.app-toast-close:focus-visible {
  color: var(--text-title);
}

/* ---- 倒计时进度条 ---- */
.app-toast-progress {
  height: 2px;
  width: 100%;
  background: linear-gradient(
    90deg,
    var(--project-accent, #67e8f9),
    color-mix(in srgb, var(--project-accent, #67e8f9) 55%, transparent)
  );
  /* animationDuration 由内联样式给（= 当前这条的时长），这里只定行为 */
  animation-name: app-toast-countdown;
  animation-timing-function: linear;
  animation-fill-mode: forwards;
  transform-origin: left center;
}
.app-toast-progress.paused {
  animation-play-state: paused;
}

@keyframes app-toast-countdown {
  from { width: 100%; }
  to { width: 0%; }
}

/* ---- 进出场 ---- */
.app-toast-enter-active {
  transition: opacity 0.26s ease, transform 0.26s cubic-bezier(0.25, 1, 0.5, 1);
}
.app-toast-leave-active {
  transition: opacity 0.4s ease, transform 0.4s ease;
}
.app-toast-enter-from,
.app-toast-leave-to {
  opacity: 0;
  /* 竖直滑入/滑出，水平方向保留 -50% 居中（见 .app-toast 注释） */
  transform: translate(-50%, -14px);
}

@media (max-width: 720px) {
  .app-toast {
    top: 8%;
  }
}

@media (prefers-reduced-motion: reduce) {
  /* 保留进度条本体（它是"还剩多久"的信息，不是装饰），
     但去掉进出场动画——那部分是纯装饰。 */
  .app-toast-enter-active,
  .app-toast-leave-active {
    transition: none;
  }
}
</style>
