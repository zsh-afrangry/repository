<script setup lang="ts">
/**
 * 「待做」侧拉抽屉 —— 全局可唤出，不卸载当前页面。
 *
 * **为什么是抽屉而不是路由**（docs/14 §11.1）
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
import type { CalendarEvent, CalendarEventTone, CalendarEventUpdatePayload } from '@/types/portal'

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
  completedTotal,
  refresh,
  archiveItem,
  unarchiveItem,
  uncompleteItem,
  updateItem,
  closeDrawer,
} = usePendingTasks()

const drawerEl = ref<HTMLElement | null>(null)
useDialogFocus(isDrawerOpen, drawerEl, closeDrawer)

/** 废纸篓折叠区是否展开。默认收起——它是"需要时才看"的内容。 */
const isArchiveOpen = ref(false)

/**
 * 当前是否在「已完成」标签页。
 *
 * 已完成页与其余页的**行结构不同**：没有勾选框（那些条目已是完成态），
 * 最右侧按钮是「恢复」而不是「作废」。所以多处要按它分支。
 */
const isCompletedTab = computed(() => activeTab.value === 'completed')

/**
 * 当前标签页为空时的提示语。
 *
 * ⚠️ 各页为空**含义不同**，必须分开说：
 *   - 「全部」为空 = 真的没有待做事项；
 *   - 分类页为空 = 只是这页没有，别处还有（否则用户会以为事情做完了）；
 *   - 「已完成」为空 = 还没勾完成过任何事（不是"没有待做"）。
 */
const emptyText = computed(() => {
  if (activeTab.value === 'all') return '没有未完成的事项。'
  if (isCompletedTab.value) return '还没有已完成的事项。勾掉一条就会出现在这里。'
  const label = tabs.value.find((t) => t.key === activeTab.value)?.label ?? ''
  return `「${label}」里没有事项，看看「全部」。`
})

/* ---------- 极速录入 ----------
 *
 * 这是本组件**最重要的功能**（docs/14 §11.2）：待办系统真正会失败的地方是
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

/* ---------- 修改（行内展开，docs/14 §11.3）----------
 *
 * **为什么不弹第二个弹窗**：抽屉本身就是 `role="dialog"` 且已锁 `body` 滚动。
 * 再叠一层会让**两个 `useDialogFocus` 同时生效**——都监听 `document` 的 keydown、
 * 都改 `document.body.style.overflow`，于是 Escape 会同时触发两个关闭，
 * 滚动锁被后关的那个错误地恢复。行内展开完全避开这一类问题。
 */

/** 正在编辑的事项 id；`null` = 没有在编辑。同一时刻只允许一条。 */
const editingId = ref<number | null>(null)
const editError = ref('')
const isEditSaving = ref(false)

/** 表单模型。时间拆成 date / time 两个输入，与后端两列结构对应（§4.2）。 */
const editForm = ref({
  title: '',
  eventDate: '',
  eventTime: '',
  detail: '',
  tone: 'todo' as CalendarEventTone,
})

/**
 * 打开某条的编辑区，并把当前值填进表单。
 *
 * ⚠️ 时间必须**拆成两段**填：`event_time` 是 `HH:MM:SS`，而
 * `<input type="time">` 的值也是 `HH:MM:SS`（带 `step="1"` 时），
 * 所以直接取前 8 位即可，不做换算——避免时区/进位这类无谓的转换错误。
 */
function startEdit(event: CalendarEvent) {
  editingId.value = event.id
  editError.value = ''
  editForm.value = {
    title: event.title,
    eventDate: event.event_date,
    // `event_time` 形如 `22:48:39`；为空表示"未安排"，输入框也留空。
    eventTime: event.event_time ? event.event_time.slice(0, 8) : '',
    detail: event.detail ?? '',
    tone: event.tone,
  }
}

function cancelEdit() {
  editingId.value = null
  editError.value = ''
}

async function submitEdit(event: CalendarEvent) {
  if (isEditSaving.value) return
  const title = editForm.value.title.trim()
  if (!title) {
    editError.value = '标题不能为空。'
    return
  }
  if (!editForm.value.eventDate) {
    editError.value = '请选择日期。'
    return
  }

  // ⚠️ 这里**每个字段都显式给出**，包括空值——因为后端用
  // `exclude_unset=True`：省略 = 不动，传 null = 清空。
  // 若把空时间序列化成"省略该字段"，用户会发现**时间改得掉却清不掉**
  // （清空 = 回到「未安排」是本功能的核心场景之一）。
  const payload: CalendarEventUpdatePayload = {
    title,
    event_date: editForm.value.eventDate,
    event_time: editForm.value.eventTime || null,
    detail: editForm.value.detail.trim() || null,
    tone: editForm.value.tone,
  }

  isEditSaving.value = true
  editError.value = ''
  try {
    await updateItem(event.id, payload)
    // 改完关闭编辑区。若该条因改时间而换了标签页，刷新后它会自然移走。
    editingId.value = null
  } catch (error) {
    console.error(error)
    editError.value = error instanceof Error ? error.message : '修改失败。'
  } finally {
    isEditSaving.value = false
  }
}

/* ---------- 展示辅助 ---------- */

/**
 * 只格式化**日期**部分（`10/13`）。
 *
 * 时间拆出去单独渲染（见 `formatTime`）——两者的重要性不同：
 * 日期回答"哪天"，时间回答"几点，要不要现在准备"。
 * 挤在一个字符串里就只能用同一种样式，而它们值得不同的视觉权重。
 */
function formatDate(event: CalendarEvent): string {
  const [, m, d] = event.event_date.split('-')
  return `${m}/${d}`
}

/** 只格式化**时间**部分（`21:06`），秒不显示（它是记录精度，不是决策依据）。 */
function formatTime(event: CalendarEvent): string {
  return event.event_time ? event.event_time.slice(0, 5) : ''
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

/** 格式化星期（例如 `周一`、`周六`）。 */
function formatWeekday(event: CalendarEvent): string {
  const [y, m, d] = event.event_date.split('-').map(Number)
  const dt = new Date(y, m - 1, d)
  const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  return weekdays[dt.getDay()]
}

/** 是否是当天事项。 */
function isToday(event: CalendarEvent): boolean {
  return event.event_date === todayKey()
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

        <!-- 标签页（§11.1 的「L2 的标签页」）：全部 / 今天 / 已过期 / 未安排 / 已完成。
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
            <!-- 角标数字来自后端，与列表过滤同源（后端 pending_bucket） -->
            <span v-if="tab.count > 0" class="drawer-tab-count">{{ tab.count }}</span>
          </button>
        </div>

        <!-- 列表 -->
        <div class="drawer-body">
          <p v-if="isLoading && !pending" class="drawer-status">正在读取…</p>
          <p v-else-if="errorMessage" class="drawer-error">{{ errorMessage }}</p>
          <template v-else-if="visibleItems.length">
            <p class="drawer-count">
              {{ isCompletedTab ? `共 ${completedTotal} 条已完成` : `共 ${pending?.total} 条未完成` }}
            </p>
            <ul class="drawer-list">
              <li
                v-for="event in visibleItems"
                :key="event.id"
                class="drawer-item"
                :class="{
                  'is-toggling': togglingIds.has(event.id),
                  'is-completed': isCompletedTab,
                  'is-editing': editingId === event.id,
                }"
              >
                <!-- ===== 编辑态：整行变成表单（docs/14 §11.3）=====
                     刻意**替换整行**，而不是"在行下方插入编辑区"：
                     后者会让同一条事项**同时出现两份**——上面一行显示旧值、
                     下面表单显示编辑中的新值。用户改了还没保存时，两份值不一致，
                     而界面上没有任何东西说明哪份是真的。
                     代价是下方条目仍会位移（表单比一行高），这是不可避免的；
                     但至少不会制造"同一条两个版本"这种更糟的歧义。 -->
                <form
                  v-if="editingId === event.id"
                  class="drawer-edit"
                  @submit.prevent="submitEdit(event)"
                >
                  <label class="drawer-edit-field">
                    <span class="drawer-edit-label">标题</span>
                    <input
                      v-model="editForm.title"
                      class="drawer-edit-input"
                      type="text"
                      required
                      :disabled="isEditSaving"
                      aria-label="事项标题"
                    />
                  </label>

                  <div class="drawer-edit-row">
                    <label class="drawer-edit-field">
                      <span class="drawer-edit-label">日期</span>
                      <input
                        v-model="editForm.eventDate"
                        class="drawer-edit-input"
                        type="date"
                        required
                        :disabled="isEditSaving"
                        aria-label="事项日期"
                      />
                    </label>
                    <label class="drawer-edit-field">
                      <span class="drawer-edit-label">时间</span>
                      <!-- ⚠️ `step="1"` 是必需的：不带它时浏览器只给到分钟，
                           秒会被截成 00 —— 改一次时间就悄悄丢掉原来的秒
                           （例如 22:48:39 变成 22:48:00）。 -->
                      <input
                        v-model="editForm.eventTime"
                        class="drawer-edit-input"
                        type="time"
                        step="1"
                        :disabled="isEditSaving"
                        aria-label="事项时间（留空表示未安排）"
                      />
                    </label>
                    <label class="drawer-edit-field">
                      <span class="drawer-edit-label">类型</span>
                      <select
                        v-model="editForm.tone"
                        class="drawer-edit-input"
                        :disabled="isEditSaving"
                        aria-label="事项类型"
                      >
                        <option value="todo">待做</option>
                        <option value="meeting">安排</option>
                      </select>
                    </label>
                  </div>

                  <label class="drawer-edit-field">
                    <span class="drawer-edit-label">备注</span>
                    <textarea
                      v-model="editForm.detail"
                      class="drawer-edit-input drawer-edit-textarea"
                      rows="2"
                      :disabled="isEditSaving"
                      aria-label="事项备注"
                    ></textarea>
                  </label>

                  <p class="drawer-edit-hint">时间留空 = 未安排，会排在清单最前。</p>
                  <p v-if="editError" class="drawer-error">{{ editError }}</p>

                  <div class="drawer-edit-actions">
                    <UiButton variant="primary" type="submit" :disabled="isEditSaving">
                      {{ isEditSaving ? '保存中' : '保存' }}
                    </UiButton>
                    <button
                      type="button"
                      class="drawer-item-action is-always-visible"
                      :disabled="isEditSaving"
                      @click="cancelEdit"
                    >
                      取消
                    </button>
                  </div>
                </form>

                <!-- ===== 常态 ===== -->
                <template v-else>
                  <!-- 已完成页不显示勾选框：那些条目已经是完成态，
                       再给一个"勾选"按钮只会让人以为能勾成"未完成"。
                       要退回待做清单请用右侧的「恢复」。 -->
                  <button
                    v-if="!isCompletedTab"
                    type="button"
                    class="drawer-check"
                    :class="{ checked: !!event.completed_at }"
                    :aria-label="`标记「${event.title}」为已完成`"
                    @click="toggleDone(event)"
                  >
                    <svg v-if="event.completed_at" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7" />
                    </svg>
                  </button>
                  <!-- 已完成页用一个静态的对勾图标代替，保留视觉对齐 -->
                  <span v-else class="drawer-check is-static" aria-hidden="true">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7" />
                    </svg>
                  </span>

                  <div class="drawer-item-body">
                    <span class="drawer-item-title">{{ event.title }}</span>
                    <span class="drawer-item-meta">
                      <!-- 时间日期封装为独立「微光时间胶囊」（2026-10-08 优化）。
                           日期回答"哪天/周几"，时间回答"几点"，通过胶囊包装与状态高亮呈现极佳的扫读可读性。 -->
                      <template v-if="event.event_time">
                        <span
                          class="drawer-item-datetime"
                          :class="{
                            'is-overdue': isOverdue(event),
                            'is-today': isToday(event),
                          }"
                        >
                          <svg class="drawer-datetime-icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" aria-hidden="true">
                            <circle cx="8" cy="8" r="6.25" stroke-width="1.5" />
                            <polyline points="8 4.5 8 8 10.5 9.5" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
                          </svg>
                          <span class="drawer-item-date">{{ formatDate(event) }}</span>
                          <span class="drawer-item-weekday">{{ isToday(event) ? '今天' : formatWeekday(event) }}</span>
                          <span
                            class="drawer-item-time"
                            :class="{ 'is-overdue': isOverdue(event) }"
                          >{{ formatTime(event) }}</span>
                        </span>
                      </template>
                      <span v-else class="drawer-tag tag-unscheduled">未安排</span>
                      <span class="drawer-tag" :class="`tag-${event.tone}`">{{ toneLabel(event.tone) }}</span>
                      <span v-if="isCompletedTab" class="drawer-tag tag-done">已完成</span>
                      <span v-else-if="isOverdue(event)" class="drawer-tag tag-overdue">已过期</span>

                    </span>
                    <span v-if="event.detail" class="drawer-item-detail">{{ event.detail }}</span>
                  </div>

                  <!-- 操作区。顺序：修改 在前（高频、破坏性低），
                       恢复/作废 在后（改变该条的去留）。
                       「修改」在「已完成」页也给——完成态不是"冻结"，
                       记错了内容仍要能改。 -->
                  <div class="drawer-item-actions">
                    <button
                      type="button"
                      class="drawer-item-action"
                      :aria-label="`修改「${event.title}」`"
                      title="修改"
                      @click="startEdit(event)"
                    >
                      修改
                    </button>
                    <!-- 已完成页：恢复到待做清单（= 取消完成）。 -->
                    <button
                      v-if="isCompletedTab"
                      type="button"
                      class="drawer-item-action"
                      :aria-label="`把「${event.title}」恢复为待做`"
                      title="恢复为待做"
                      @click="uncompleteItem(event.id)"
                    >
                      恢复
                    </button>
                    <!-- 其余页：作废。无二次确认（可撤销，见 usePendingTasks.archiveItem）。 -->
                    <button
                      v-else
                      type="button"
                      class="drawer-item-action"
                      :aria-label="`作废「${event.title}」`"
                      title="作废（可撤销）"
                      @click="archiveItem(event)"
                    >
                      作废
                    </button>
                  </div>
                </template>
              </li>
            </ul>
            <p v-if="!isCompletedTab && pending?.truncated" class="drawer-status">
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
                    <!-- 与主列表保持同一套渲染（日期 + 加重的时间）。
                         废纸篓的条目降了对比度（`.is-archived`），
                         时间的加重色会被那条规则整体压低——这是对的：
                         已作废的事项不再需要提醒。 -->
                    <template v-if="event.event_time">
                      <span class="drawer-item-datetime">
                        <svg class="drawer-datetime-icon" viewBox="0 0 16 16" fill="none" stroke="currentColor" aria-hidden="true">
                          <circle cx="8" cy="8" r="6.25" stroke-width="1.5" />
                          <polyline points="8 4.5 8 8 10.5 9.5" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
                        </svg>
                        <span class="drawer-item-date">{{ formatDate(event) }}</span>
                        <span class="drawer-item-weekday">{{ isToday(event) ? '今天' : formatWeekday(event) }}</span>
                        <span class="drawer-item-time">{{ formatTime(event) }}</span>
                      </span>
                    </template>

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
  gap: 0.4rem;
  font-size: 0.68rem;
  color: var(--text-secondary);
}

/* 时间日期封装：微光独立胶囊（2026-10-08 优化）
 * 将分散的日期、星期与时间打包为一个清晰易读的整体胶囊。
 * 1. 对比度与字阶：日期 0.72rem/500 (#94a3b8 对比度 6.43)，时间 0.82rem/800 (极白 #f8fafc 对比度 16.43)；
 * 2. 状态特征：今天事项散发青色微光，过期事项散发琥珀黄警示微光。
 */
.drawer-item-datetime {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.15rem 0.45rem;
  border-radius: 0.35rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.13);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
  line-height: 1;
  transition: all 0.15s ease;
}
.drawer-datetime-icon {
  width: 0.72rem;
  height: 0.72rem;
  flex-shrink: 0;
  color: var(--text-secondary);
  opacity: 0.85;
}
.drawer-item-date {
  font-family: var(--font-mono), monospace;
  font-size: 0.72rem;
  font-weight: 500;
  color: var(--text-secondary);
  letter-spacing: 0.01em;
}
.drawer-item-weekday {
  font-size: 0.68rem;
  font-weight: 500;
  color: var(--text-secondary);
  opacity: 0.9;
}
.drawer-item-time {
  color: var(--text-title);
  font-family: var(--font-mono), monospace;
  font-size: 0.82rem;
  font-weight: 800;
  letter-spacing: 0.02em;
}

/* 当天任务（Today）：青色微光与边框强化 */
.drawer-item-datetime.is-today {
  background: rgba(6, 182, 212, 0.12);
  border-color: rgba(6, 182, 212, 0.35);
}
.drawer-item-datetime.is-today .drawer-datetime-icon {
  color: #67e8f9;
  opacity: 1;
}
.drawer-item-datetime.is-today .drawer-item-weekday {
  color: #67e8f9;
  font-weight: 700;
}

/* 已过期任务（Overdue）：琥珀黄色警示微光 */
.drawer-item-datetime.is-overdue {
  background: rgba(251, 191, 36, 0.12);
  border-color: rgba(251, 191, 36, 0.38);
}
.drawer-item-datetime.is-overdue .drawer-datetime-icon {
  color: #fbbf24;
  opacity: 1;
}
.drawer-item-datetime.is-overdue .drawer-item-weekday {
  color: #fbbf24;
}
.drawer-item-time.is-overdue {
  color: #fbbf24;
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
.drawer-tag.tag-done { border-color: rgb(124 58 237 / 0.5); color: #c4b5fd; }

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

/* ---- 修改：行内编辑区（docs/14 §11.3）---- */

/* 一条事项现在有「修改」+「作废/恢复」两个按钮。
   横排、靠右、不换行——按钮多了以后若让它自动换行，
   行高会在不同条目间不一致，列表看起来会参差。 */
.drawer-item-actions {
  display: flex;
  flex-shrink: 0;
  gap: 0.1rem;
  align-self: center;
}

/* 编辑态：整行变成表单，不再参与 `display: flex` 的行布局。 */
.drawer-item.is-editing {
  display: block;
  padding: 0.7rem 0.7rem 0.8rem;
  border-color: color-mix(in srgb, var(--project-accent, #67e8f9) 35%, var(--border-color));
  background: rgb(255 255 255 / 0.05);
}

.drawer-edit {
  display: grid;
  gap: 0.55rem;
}

.drawer-edit-field {
  display: grid;
  gap: 0.2rem;
  min-width: 0;
}

/* 标签用极小号大写风格，与抽屉其它元信息一致（.drawer-kicker 那套）。 */
.drawer-edit-label {
  color: var(--text-secondary);
  font-size: 0.6rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  opacity: 0.85;
}

.drawer-edit-input {
  width: 100%;
  min-width: 0;
  padding: 0.35rem 0.5rem;
  border: 1px solid var(--border-color);
  border-radius: 0.45rem;
  background: rgb(255 255 255 / 0.04);
  color: var(--text-primary);
  font: inherit;
  font-size: 0.78rem;
}
.drawer-edit-input:focus-visible {
  outline: 2px solid var(--project-accent, #67e8f9);
  outline-offset: 1px;
}
.drawer-edit-input:disabled {
  opacity: 0.6;
}

/* 日期 / 时间 / 类型 三列并排。窄屏下退成两列再退成一列——
   27rem 的抽屉在手机上是全宽，三列会把日期输入挤到看不清。 */
.drawer-edit-row {
  display: grid;
  grid-template-columns: 1.4fr 1fr 1fr;
  gap: 0.45rem;
}
@media (max-width: 420px) {
  .drawer-edit-row { grid-template-columns: 1fr 1fr; }
}

.drawer-edit-textarea {
  resize: vertical;
  font-size: 0.74rem;
}

.drawer-edit-hint {
  margin: 0;
  color: var(--text-secondary);
  font-size: 0.63rem;
  opacity: 0.75;
}

.drawer-edit-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

/* 「取消」是编辑区里的次要动作，不跟随 `.drawer-item:hover` 的显隐规则
   （那个规则依赖 `.drawer-item` 的 hover，而编辑态下鼠标可能不在行内，
   按钮会半透明到几乎看不见）。 */
.drawer-item-action.is-always-visible {
  opacity: 1;
  border-color: var(--border-color);
}
.drawer-item-action:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

/* 已完成的条目整体降对比度（与 `is-archived` 同一处理）：它还在，但不该跟待做抢注意力。 */
.drawer-item.is-completed {
  background: transparent;
  opacity: 0.75;
}

/* 已完成页的静态对勾：不是按钮，只是为了与其它页的文字左对齐。
   `cursor: default` 避免看起来可点。 */
.drawer-check.is-static {
  display: grid;
  place-items: center;
  border-color: rgb(124 58 237 / 0.55);
  background-color: rgb(124 58 237 / 0.35);
  cursor: default;
}
.drawer-check.is-static svg {
  width: 0.7rem;
  height: 0.7rem;
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
