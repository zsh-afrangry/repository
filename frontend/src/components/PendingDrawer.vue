<script setup lang="ts">
/**
 * 「待做」侧拉抽屉 —— 全局可唤出，不卸载当前页面。
 *
 * **为什么是抽屉而不是路由**（docs/14 §11.2）
 *
 * 用户对这块的判据是"**随时点击就能看到**、详细且直观"。路由跳转会**卸载当前页面**
 * （看笔记看到一半跳走再回来，滚动位置与草稿可能都没了），恰好破坏"不打断"这一点；
 * 而抽屉盖在页面上、一步可达。日常最高频的动作是"我记一下 / 我看看还剩什么"，
 * 抽屉满足它；低频的"每周整理积压"（批量改期、归档）留给将来的 `/tasks` 全页。
 *
 * **挂载位置**：挂在 `App.vue`（而非某个页面内），这样在 `/bills`、`/notes` 等
 * 任何路由下都能唤出。它靠 `v-if` 控制显示，但**组件本身常驻挂载**——
 * `useDialogFocus` 依赖 `watch(open)`，若把组件一起 `v-if` 掉，焦点逻辑就失效了。
 *
 * **数据来源**：`usePendingTasks()` 单例。与首页摘要卡片共享同一份状态，
 * 所以在这里勾掉一条，首页卡片也会立刻少一条。
 */
import { computed, ref, watch } from 'vue'

import UiButton from '@/components/ui/UiButton.vue'
import { useDialogFocus } from '@/composables/useDialogFocus'
import { usePendingTasks } from '@/composables/usePendingTasks'
import { calendarApi } from '@/api/calendar'
import { todayKey } from '@/utils/date'
import type { CalendarEvent, CalendarEventTone } from '@/types/portal'

const {
  pending,
  isLoading,
  errorMessage,
  isDrawerOpen,
  visibleItems,
  tabs,
  activeTab,
  setActiveTab,
  archivedItems,
  archivedTotal,
  refresh,
  archiveItem,
  unarchiveItem,
  closeDrawer,
} = usePendingTasks()

const drawerEl = ref<HTMLElement | null>(null)
useDialogFocus(isDrawerOpen, drawerEl, closeDrawer)

/** 废纸篓折叠区是否展开。默认收起——它是"需要时才看"的内容。 */
const isArchiveOpen = ref(false)

/**
 * 当前标签页为空时的提示语。
 *
 * ⚠️ 「全部」为空与分类页为空**含义不同**，必须分开说：
 *   - 「全部」为空 = 真的没有待做事项；
 *   - 分类页为空 = 只是这页没有，别处还有（否则用户会以为事情做完了）。
 */
const emptyText = computed(() => {
  if (activeTab.value === 'all') return '没有未完成的事项。'
  const label = tabs.value.find((t) => t.key === activeTab.value)?.label ?? ''
  return `「${label}」里没有事项，看看「全部」。`
})

/* ---------- 极速录入 ----------
 *
 * 这是本组件**最重要的功能**（docs/14 §11.3）：待办系统真正会失败的地方是
 * "记下来"那一步。若记一条需要六步操作，忙的时候就不会记，数据是空的，
 * 后面所有查看功能全部白搭。所以这里：
 *   - 只有一个输入框，**只填标题就能保存**（类型默认 todo、时间默认空）
 *   - Enter 直接提交，不要求点按钮
 *   - 时间可留空 —— 留空即"未安排"，会排在清单最前（§2.4）
 */

const quickTitle = ref('')
const quickTone = ref<CalendarEventTone>('todo')
const isSaving = ref(false)
const saveError = ref('')

const canSubmit = computed(() => quickTitle.value.trim().length > 0 && !isSaving.value)

/**
 * 极速录入默认**不设时间**。
 *
 * 这不是偷懒：用户此刻往往只知道"有这件事"，还不知道什么时候做。
 * 强行要求选时间会让人放弃记录。无时间的事项会被后端排在清单最前
 * （§2.4 的排序规则），并在界面上标为「未安排」——那正是提醒你去安排的信号。
 */
async function submitQuick() {
  if (!canSubmit.value) return
  const title = quickTitle.value.trim()
  isSaving.value = true
  saveError.value = ''
  try {
    // ⚠️ 必须用 `todayKey()` 而不是 `toISOString().slice(0,10)`——
    // 后者是 UTC，在东八区凌晨 0–8 点会给出**昨天**（`utils/date.ts` 有完整说明）。
    // 无时间事项的日期只用于排序与"是否过期"，但错一天仍会让它提前变欠账。
    await calendarApi.create({
      event_date: todayKey(),
      event_time: null,
      title,
      detail: null,
      tone: quickTone.value,
    })
    quickTitle.value = ''
    // 保存后刷新清单：新事项会由后端排在最前（未安排组内最新的在前，§2.4）。
    // 这里刻意**不手工往列表里塞**——那会与后端排序打架，也让"谁负责排序"
    // 这件事变得含糊。排序是后端的职责。
    await refresh({ silent: true })
    // 若刷新失败（清单为 null），退回非静默刷新，让用户看到错误而不是"没记上"。
    if (!pending.value) {
      await refresh()
    }
  } catch (error) {
    console.error(error)
    saveError.value = error instanceof Error ? error.message : '保存失败。'
  } finally {
    isSaving.value = false
  }
}

/* ---------- 勾选 / 取消 ---------- */

const togglingIds = ref<Set<number>>(new Set())

async function toggleDone(event: CalendarEvent) {
  if (togglingIds.value.has(event.id)) return
  const nextDone = !event.completed_at
  togglingIds.value = new Set(togglingIds.value).add(event.id)
  try {
    await calendarApi.setCompletion(event.id, nextDone)
    // 清单只含未完成项：勾选完成后刷新会让它消失；取消勾选则重新出现。
    await refresh({ silent: true })
  } catch (error) {
    console.error(error)
  } finally {
    const next = new Set(togglingIds.value)
    next.delete(event.id)
    togglingIds.value = next
  }
}

/* ---------- 展示辅助 ---------- */

function formatDate(event: CalendarEvent): string {
  const [, m, d] = event.event_date.split('-')
  const time = event.event_time ? ` ${event.event_time.slice(0, 5)}` : ''
  return `${m}/${d}${time}`
}

function isOverdue(event: CalendarEvent): boolean {
  if (event.completed_at) return false
  const [y, m, d] = event.event_date.split('-').map(Number)
  let due: Date
  if (event.event_time) {
    const [hh, mm, ss] = event.event_time.split(':').map(Number)
    due = new Date(y, m - 1, d, hh, mm, ss || 0)
  } else {
    due = new Date(y, m - 1, d, 23, 59, 59)
  }
  return due.getTime() < Date.now()
}

function toneLabel(tone: CalendarEventTone): string {
  return tone === 'meeting' ? '安排' : '待做'
}

/** 打开时刷新一次，保证看到的是最新的（其它页面可能刚改过）。 */
watch(isDrawerOpen, (open) => {
  if (open) void refresh({ silent: !!pending.value })
})

/** 打开时聚焦输入框——极速录入要"打开就能打字"。 */
watch(isDrawerOpen, async (open) => {
  if (!open) return
  await new Promise((r) => setTimeout(r, 60)) // 等过渡开始，元素已渲染
  const input = drawerEl.value?.querySelector<HTMLInputElement>('.drawer-quick-input')
  input?.focus()
})
</script>

<template>
  <Transition name="drawer">
    <div
      v-if="isDrawerOpen"
      class="drawer-layer"
      role="presentation"
      @click.self="closeDrawer"
    >
      <aside
        ref="drawerEl"
        class="drawer-panel"
        tabindex="-1"
        data-lenis-prevent
        role="dialog"
        aria-modal="true"
        aria-labelledby="pending-drawer-title"
      >
        <header class="drawer-header">
          <div>
            <p class="drawer-kicker">Pending</p>
            <h2 id="pending-drawer-title">待做事项</h2>
          </div>
          <button type="button" class="drawer-close" aria-label="关闭待做抽屉" @click="closeDrawer">×</button>
        </header>

        <!-- 极速录入：只填标题即可保存（Enter 提交） -->
        <form class="drawer-quick" @submit.prevent="submitQuick">
          <div class="drawer-quick-row">
            <input
              v-model="quickTitle"
              class="drawer-quick-input"
              type="text"
              placeholder="记一件事，回车即可（时间可后补）"
              aria-label="快速添加待做事项"
              :disabled="isSaving"
            />
            <select v-model="quickTone" class="drawer-quick-tone" aria-label="事项类型" :disabled="isSaving">
              <option value="todo">待做</option>
              <option value="meeting">安排</option>
            </select>
            <UiButton variant="primary" type="submit" :disabled="!canSubmit">
              {{ isSaving ? '保存中' : '添加' }}
            </UiButton>
          </div>
          <p v-if="saveError" class="drawer-error">{{ saveError }}</p>
          <p class="drawer-hint">不填时间 = 未安排，会排在清单最前，提醒你之后安排。</p>
        </form>

        <!-- 标签页（§11.6）：全部 / 今天 / 已过期 / 未安排。
             「全部」必须存在且默认选中——三个分类不构成完整划分，
             有时间的未来事项只在「全部」里出现。 -->
        <div class="drawer-tabs" role="tablist" aria-label="待做事项分组">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            type="button"
            role="tab"
            class="drawer-tab"
            :class="{ active: activeTab === tab.key }"
            :aria-selected="activeTab === tab.key"
            @click="setActiveTab(tab.key)"
          >
            {{ tab.label }}
            <!-- 角标数字来自后端的 counts，与列表过滤同源（后端 pending_bucket） -->
            <span v-if="tab.count > 0" class="drawer-tab-count">{{ tab.count }}</span>
          </button>
        </div>

        <!-- 列表 -->
        <div class="drawer-body">
          <p v-if="isLoading && !pending" class="drawer-status">正在读取…</p>
          <p v-else-if="errorMessage" class="drawer-error">{{ errorMessage }}</p>
          <template v-else-if="visibleItems.length">
            <p class="drawer-count">共 {{ pending?.total }} 条未完成</p>
            <ul class="drawer-list">
              <li
                v-for="event in visibleItems"
                :key="event.id"
                class="drawer-item"
                :class="{ 'is-toggling': togglingIds.has(event.id) }"
              >
                <button
                  type="button"
                  class="drawer-check"
                  :class="{ checked: !!event.completed_at }"
                  :aria-label="`标记「${event.title}」为${event.completed_at ? '未完成' : '已完成'}`"
                  @click="toggleDone(event)"
                >
                  <svg v-if="event.completed_at" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7" />
                  </svg>
                </button>
                <div class="drawer-item-body">
                  <span class="drawer-item-title">{{ event.title }}</span>
                  <span class="drawer-item-meta">
                    <span v-if="event.event_time" class="drawer-item-date">{{ formatDate(event) }}</span>
                    <span v-else class="drawer-tag tag-unscheduled">未安排</span>
                    <span class="drawer-tag" :class="`tag-${event.tone}`">{{ toneLabel(event.tone) }}</span>
                    <span v-if="isOverdue(event)" class="drawer-tag tag-overdue">已过期</span>
                  </span>
                  <span v-if="event.detail" class="drawer-item-detail">{{ event.detail }}</span>
                </div>
                <!-- 作废：无二次确认（可撤销，见 usePendingTasks.archiveItem）。
                     放在最右侧，将来还会加"删除"等按钮（用户 2026-10-07 提到，本轮不做）。 -->
                <button
                  type="button"
                  class="drawer-item-action"
                  :aria-label="`作废「${event.title}」`"
                  title="作废（可撤销）"
                  @click="archiveItem(event)"
                >
                  作废
                </button>
              </li>
            </ul>
            <p v-if="pending?.truncated" class="drawer-status">
              只显示了前 {{ pending.shown }} 条，共 {{ pending.total }} 条。
            </p>
          </template>
          <p v-else class="drawer-status">{{ emptyText }}</p>

          <!-- 废纸篓：折叠区。后续会改成 4 个 tab（用户 2026-10-07 提到）——
               那时这里会变成其中一个 tab 的内容，所以先把内容与"折叠"这个外壳分开写。 -->
          <section v-if="archivedTotal > 0" class="drawer-archive">
            <button
              type="button"
              class="drawer-archive-toggle"
              :aria-expanded="isArchiveOpen"
              @click="isArchiveOpen = !isArchiveOpen"
            >
              <span class="drawer-archive-caret" :class="{ open: isArchiveOpen }">▸</span>
              已作废 ({{ archivedTotal }})
            </button>
            <ul v-if="isArchiveOpen" class="drawer-list">
              <li v-for="event in archivedItems" :key="event.id" class="drawer-item is-archived">
                <div class="drawer-item-body">
                  <span class="drawer-item-title">{{ event.title }}</span>
                  <span class="drawer-item-meta">
                    <span v-if="event.event_time" class="drawer-item-date">{{ formatDate(event) }}</span>
                    <span v-else class="drawer-tag tag-unscheduled">未安排</span>
                    <span class="drawer-tag" :class="`tag-${event.tone}`">{{ toneLabel(event.tone) }}</span>
                    <span class="drawer-tag tag-archived">已作废</span>
                  </span>
                </div>
                <button
                  type="button"
                  class="drawer-item-action"
                  :aria-label="`恢复「${event.title}」`"
                  title="恢复为待做"
                  @click="unarchiveItem(event.id)"
                >
                  恢复
                </button>
              </li>
            </ul>
          </section>
        </div>
      </aside>
    </div>
  </Transition>
</template>

<style scoped>
/* 遮罩层：与 `.calendar-modal-layer` 同一套视觉（深色 + 模糊），保持全站一致。
   抽屉与居中弹窗的区别只在面板的定位方式。 */
.drawer-layer {
  position: fixed;
  inset: 0;
  z-index: 90;
  background: rgb(5 5 8 / 0.58);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
}

.theme-light .drawer-layer {
  background: rgba(26, 26, 26, 0.28);
}

.drawer-panel {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  display: flex;
  width: min(100%, 27rem);
  flex-direction: column;
  border-left: 1px solid color-mix(in srgb, var(--primary-btn-border) 26%, var(--border-color));
  background:
    linear-gradient(145deg, rgb(255 255 255 / 0.08), rgb(255 255 255 / 0.03)),
    var(--surface-card);
  box-shadow: -30px 0 90px rgb(0 0 0 / 0.42);
  color: var(--text-primary);
}

.theme-light .drawer-panel {
  background:
    linear-gradient(145deg, rgba(255, 255, 255, 0.92), rgba(248, 245, 242, 0.82)),
    #f8f5f2;
}

.drawer-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  padding: 1.35rem 1.5rem 0.9rem;
}

.drawer-kicker {
  margin: 0;
  color: var(--text-secondary);
  font-size: 0.66rem;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.drawer-header h2 {
  margin: 0.2rem 0 0;
  font-size: 1.2rem;
  font-weight: 800;
}

.drawer-close {
  display: grid;
  width: 1.9rem;
  height: 1.9rem;
  place-items: center;
  border: 1px solid var(--border-color);
  border-radius: 0.6rem;
  background: rgb(255 255 255 / 0.04);
  color: var(--text-secondary);
  font-size: 1.15rem;
  line-height: 1;
  cursor: pointer;
}
.drawer-close:hover,
.drawer-close:focus-visible {
  border-color: var(--primary-btn-border);
  color: var(--text-title);
}

/* ---- 极速录入 ---- */
.drawer-quick {
  padding: 0 1.5rem 1rem;
  border-bottom: 1px solid var(--border-color);
}
.drawer-quick-row {
  display: flex;
  gap: 0.5rem;
}
.drawer-quick-input {
  flex: 1;
  min-width: 0;
  padding: 0.5rem 0.7rem;
  border: 1px solid var(--border-color);
  border-radius: 0.6rem;
  background: rgb(255 255 255 / 0.04);
  color: var(--text-primary);
  font: inherit;
  font-size: 0.85rem;
}
.drawer-quick-input::placeholder {
  color: var(--text-secondary);
  opacity: 0.7;
}
.drawer-quick-input:focus-visible {
  outline: 2px solid var(--primary-btn-border);
  outline-offset: 2px;
}
.drawer-quick-tone {
  padding: 0.5rem 0.4rem;
  border: 1px solid var(--border-color);
  border-radius: 0.6rem;
  background: rgb(255 255 255 / 0.04);
  color: var(--text-primary);
  font: inherit;
  font-size: 0.8rem;
}
.drawer-hint {
  margin: 0.45rem 0 0;
  color: var(--text-secondary);
  font-size: 0.66rem;
  opacity: 0.75;
}

/* ---- 标签页 ---- */
.drawer-tabs {
  display: flex;
  gap: 0.25rem;
  padding: 0 1.5rem;
  border-bottom: 1px solid var(--border-color);
  overflow-x: auto;
  scrollbar-width: none;
}
.drawer-tabs::-webkit-scrollbar {
  display: none;
}
.drawer-tab {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  flex-shrink: 0;
  padding: 0.5rem 0.6rem;
  border: 0;
  /* 选中态用底部 2px 线表示，不用背景块——与全站"轻量、不抢注意力"一致 */
  border-bottom: 2px solid transparent;
  background: transparent;
  color: var(--text-secondary);
  font: inherit;
  font-size: 0.76rem;
  font-weight: 700;
  cursor: pointer;
  transition: color 0.15s ease, border-color 0.15s ease;
}
.drawer-tab:hover {
  color: var(--text-title);
}
.drawer-tab.active {
  border-bottom-color: var(--project-accent, #67e8f9);
  color: var(--text-title);
}
.drawer-tab:focus-visible {
  outline: 2px solid var(--project-accent, #67e8f9);
  outline-offset: -2px;
  border-radius: 0.3rem;
}
.drawer-tab-count {
  padding: 0 0.3rem;
  border-radius: 999px;
  background: rgb(255 255 255 / 0.08);
  font-size: 0.62rem;
  font-weight: 800;
}
.drawer-tab.active .drawer-tab-count {
  background: color-mix(in srgb, var(--project-accent, #67e8f9) 22%, transparent);
}
@media (prefers-reduced-motion: reduce) {
  .drawer-tab { transition: none; }
}

/* ---- 列表 ---- */
.drawer-body {
  flex: 1;
  overflow-y: auto;
  padding: 1rem 1.5rem 1.5rem;
}
.drawer-count {
  margin: 0 0 0.6rem;
  color: var(--text-secondary);
  font-size: 0.72rem;
  font-weight: 700;
}
.drawer-list {
  display: grid;
  gap: 0.5rem;
  margin: 0;
  padding: 0;
  list-style: none;
}
.drawer-item {
  display: flex;
  align-items: flex-start;
  gap: 0.65rem;
  padding: 0.55rem 0.6rem;
  border: 1px solid transparent;
  border-radius: 0.6rem;
  background: rgb(255 255 255 / 0.03);
}
.drawer-item.is-toggling {
  opacity: 0.5;
  pointer-events: none;
}
.drawer-check {
  display: grid;
  width: 1.15rem;
  height: 1.15rem;
  flex-shrink: 0;
  place-items: center;
  margin-top: 0.1rem;
  border: 1.5px solid rgba(255, 255, 255, 0.25);
  border-radius: 999px;
  background: transparent;
  color: #fff;
  cursor: pointer;
}
.drawer-check svg {
  width: 0.7rem;
  height: 0.7rem;
}
.drawer-check.checked {
  border-color: #7c3aed;
  background-color: #7c3aed;
}
.drawer-check:focus-visible {
  outline: 2px solid var(--primary-btn-border);
  outline-offset: 2px;
}
.drawer-item-body {
  display: grid;
  gap: 0.2rem;
  min-width: 0;
  flex: 1;
}
.drawer-item-title {
  font-size: 0.85rem;
  overflow-wrap: anywhere;
}
.drawer-item-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.62rem;
  color: var(--text-secondary);
}
.drawer-item-date {
  font-family: var(--font-mono), monospace;
}
.drawer-item-detail {
  color: var(--text-secondary);
  font-size: 0.7rem;
  opacity: 0.8;
  overflow-wrap: anywhere;
}
.drawer-tag {
  padding: 0.05rem 0.3rem;
  border: 1px solid transparent;
  border-radius: 0.3rem;
}
.drawer-tag.tag-todo { border-color: rgb(6 182 212 / 0.4); color: #67e8f9; }
.drawer-tag.tag-meeting { border-color: rgb(236 72 153 / 0.4); color: #f9a8d4; }
.drawer-tag.tag-overdue { border-color: rgb(251 191 36 / 0.45); color: #fbbf24; }
.drawer-tag.tag-unscheduled { border-color: rgb(148 163 184 / 0.4); }
.drawer-tag.tag-archived { border-color: rgb(148 163 184 / 0.35); color: var(--text-secondary); }

/* 每条记录最右侧的操作按钮（作废 / 恢复）。
   默认低对比度，hover 才变明显——避免整列按钮喧宾夺主，
   同时保证它始终可发现（不像右键菜单那样藏起来）。 */
.drawer-item-action {
  flex-shrink: 0;
  align-self: center;
  padding: 0.2rem 0.5rem;
  border: 1px solid transparent;
  border-radius: 0.45rem;
  background: transparent;
  color: var(--text-secondary);
  font: inherit;
  font-size: 0.68rem;
  font-weight: 700;
  cursor: pointer;
  opacity: 0.55;
  transition: opacity 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}
.drawer-item:hover .drawer-item-action,
.drawer-item-action:focus-visible {
  opacity: 1;
  border-color: var(--border-color);
  color: var(--text-title);
}
.drawer-item-action:focus-visible {
  outline: 2px solid var(--project-accent, #67e8f9);
  outline-offset: 2px;
}
@media (hover: none) {
  /* 触屏没有 hover，按钮必须始终可见，否则等于不存在。 */
  .drawer-item-action { opacity: 1; }
}

/* 已作废的条目整体降对比度：它还在，但不该跟待做抢注意力。 */
.drawer-item.is-archived {
  background: transparent;
  opacity: 0.75;
}
.drawer-item.is-archived .drawer-item-title {
  text-decoration: line-through;
  text-decoration-color: rgb(255 255 255 / 0.25);
}

/* 废纸篓折叠区 */
.drawer-archive {
  margin-top: 1.2rem;
  padding-top: 0.8rem;
  border-top: 1px solid var(--border-color);
}
.drawer-archive-toggle {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  width: 100%;
  padding: 0.3rem 0.2rem;
  border: 0;
  background: transparent;
  color: var(--text-secondary);
  font: inherit;
  font-size: 0.74rem;
  font-weight: 700;
  text-align: left;
  cursor: pointer;
}
.drawer-archive-toggle:hover,
.drawer-archive-toggle:focus-visible {
  color: var(--text-title);
}
.drawer-archive-toggle:focus-visible {
  outline: 2px solid var(--project-accent, #67e8f9);
  outline-offset: 2px;
  border-radius: 0.3rem;
}
.drawer-archive-caret {
  display: inline-block;
  transition: transform 0.18s ease;
}
.drawer-archive-caret.open {
  transform: rotate(90deg);
}
@media (prefers-reduced-motion: reduce) {
  .drawer-archive-caret { transition: none; }
}

.drawer-status {
  margin: 0.5rem 0;
  color: var(--text-secondary);
  font-size: 0.75rem;
  opacity: 0.8;
}
.drawer-error {
  margin: 0.45rem 0 0;
  color: var(--expense, #fb7185);
  font-size: 0.72rem;
}

/* ---- 过渡 ---- */
.drawer-enter-active,
.drawer-leave-active {
  transition: opacity 0.24s ease;
}
.drawer-enter-active .drawer-panel,
.drawer-leave-active .drawer-panel {
  transition: transform 0.28s cubic-bezier(0.25, 1, 0.5, 1);
}
.drawer-enter-from,
.drawer-leave-to {
  opacity: 0;
}
.drawer-enter-from .drawer-panel,
.drawer-leave-to .drawer-panel {
  transform: translateX(100%);
}

@media (prefers-reduced-motion: reduce) {
  .drawer-enter-active,
  .drawer-leave-active,
  .drawer-enter-active .drawer-panel,
  .drawer-leave-active .drawer-panel {
    transition: none;
  }
}
</style>
