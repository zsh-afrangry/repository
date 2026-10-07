/**
 * 全站顶部提示的**共享状态**（单例 composable）。
 *
 * **为什么要抽这一层**
 * 有两处需要"顶部弹一条、几秒后自动消失"的提示：
 *   1. 作废后的提示（5 秒 + 「撤销」）
 *   2. 主题按钮的"功能待开发"提示（3 秒，无可操作项）
 * 它们原先各写一份（一个在 `Dashboard.vue` 内联、一个在 `usePendingTasks` 里），
 * 时长、计时器、定位都要各改一遍。现在倒计时与进度条只有**这一份实现**。
 *
 * **为什么不用现成的 toast 库**（如 vue-toastification / react-toastify）：
 *   1. 门户是纯自定义深色设计系统，库自带的浅色 Material 样式要全部覆盖；
 *      Element Plus 就是因此被隔离在 TradeSim 模块里的。
 *   2. 需要的功能（文字 + 可选按钮 + 倒计时条 + 悬停暂停）总共不到 100 行，
 *      为它引入依赖并把已跑通的组件换掉不划算。
 *   3. 进度条与倒计时要**共用一个时长常量**，自己写才能保证这一点。
 *
 * **一次只显示一条**：新提示替换旧的（与作废连续操作的体验一致）。
 */
import { computed, ref } from 'vue'

/** 提示上的可选操作按钮（如「撤销」）。 */
export interface ToastAction {
  label: string
  run: () => void | Promise<void>
}

export interface ToastOptions {
  /** 主文案。 */
  text: string
  /** 次要说明（可省略）。 */
  detail?: string
  /** 停留时长（毫秒）。默认 5 秒。 */
  durationMs?: number
  /** 可选的按钮，如「撤销」。 */
  action?: ToastAction
}

interface ToastState {
  /** 每次显示都递增：既用作 Vue 的 `:key`（强制重建 → 进度条动画重新开始），
   *  也让旧的定时器能识别出"我已经过期了"，不会误关掉新提示。 */
  key: number
  text: string
  detail: string
  durationMs: number
  action: ToastAction | null
  /** 正在执行 action（如撤销请求在飞）——此时禁用按钮，避免重复点击。 */
  actionBusy: boolean
}

/** 默认停留时长。作废提示用 5 秒（用户要求"5 秒左右"）。 */
export const TOAST_DEFAULT_MS = 5000

const toast = ref<ToastState | null>(null)
let seq = 0
let timer: ReturnType<typeof setTimeout> | null = null
/** 剩余毫秒。暂停时把已过的部分扣掉，恢复时用剩下的重新计时。 */
let remainingMs = 0
/** 本轮计时的起点（`Date.now()`）。 */
let startedAt = 0
/** 是否处于暂停（悬停 / 键盘聚焦）。进度条靠它同步暂停动画。 */
const isPaused = ref(false)

function clearTimer() {
  if (timer !== null) {
    clearTimeout(timer)
    timer = null
  }
}

function hide() {
  clearTimer()
  isPaused.value = false
  remainingMs = 0
  toast.value = null
}

function schedule(key: number) {
  startedAt = Date.now()
  timer = setTimeout(() => {
    // 只有"我还是当前那条"时才关闭：连续提示时旧定时器不该关掉新提示。
    if (toast.value?.key === key) hide()
  }, remainingMs)
}

export function useToast() {
  /**
   * 显示一条提示。重复调用会**替换**当前提示并重新计时。
   *
   * `durationMs` 同时驱动两件事：JS 计时器（决定何时关闭）与 CSS 进度条动画
   * （决定视觉上还剩多少）。两者共用同一个值，改时长不会只改一半。
   */
  function show(options: ToastOptions) {
    const durationMs = options.durationMs ?? TOAST_DEFAULT_MS
    clearTimer()
    remainingMs = durationMs
    isPaused.value = false
    toast.value = {
      key: ++seq,
      text: options.text,
      detail: options.detail ?? '',
      durationMs,
      action: options.action ?? null,
      actionBusy: false,
    }
    schedule(toast.value.key)
  }

  /** 手动关闭（关闭按钮）。 */
  function dismiss() {
    hide()
  }

  /**
   * 暂停倒计时——**悬停或键盘聚焦时调用**。
   *
   * 为什么必须有：提示里可能有「撤销」按钮。若倒计时照走，
   * 用户正要点的时候弹窗先消失了，就点空了。键盘用户更明显：
   * Tab 到按钮上时弹窗消失，等于这个按钮不可达。
   */
  function pause() {
    if (!toast.value || timer === null) return
    remainingMs = Math.max(0, remainingMs - (Date.now() - startedAt))
    clearTimer()
    isPaused.value = true
  }

  /** 恢复倒计时（鼠标移开 / 焦点离开）。用剩余时间继续，不是重新计时。 */
  function resume() {
    if (!toast.value || timer !== null) return
    isPaused.value = false
    schedule(toast.value.key)
  }

  /** 执行提示上的操作（如撤销），期间禁用按钮。 */
  async function runAction() {
    const current = toast.value
    if (!current?.action || current.actionBusy) return
    current.actionBusy = true
    try {
      await current.action.run()
    } finally {
      // 操作本身通常会再弹一条结果提示（替换本条），所以只在**本条仍在**时收起。
      if (toast.value?.key === current.key) hide()
    }
  }

  return {
    toast: computed(() => toast.value),
    isPaused: computed(() => isPaused.value),
    show,
    dismiss,
    pause,
    resume,
    runAction,
  }
}
