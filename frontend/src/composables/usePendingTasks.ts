/**
 * 待做事项的**全局共享状态**（单例 composable）。
 *
 * **为什么需要它**
 * 待做清单有三个消费方：首页的摘要卡片、全局可唤出的「待做」抽屉，
 * 以及作废后的顶部提示。它们必须看到**同一份**数据——在抽屉里勾掉一条，
 * 首页卡片必须立刻也少一条，否则用户会怀疑哪边是真的。
 *
 * **为什么不用 Pinia**
 * 项目没装状态库（`package.json` 里没有 pinia/vuex），为这一份状态引入一个依赖
 * 不划算。这里用最轻的做法：**模块级 `ref`**——模块只求值一次，
 * 因此所有 `usePendingTasks()` 调用者共享同一批 ref，天然就是单例。
 *
 * ⚠️ **不要在组件里 `ref()` 一份本地副本**。那会让各处各持一份状态，
 * 操作后只有一边更新——这正是本项目 2026-10-07 修掉的"两套窗口"那类问题。
 *
 * 数据的**口径与排序由后端决定**（`GET /dashboard/pending/`，见 docs/14 §2.4）；
 * 本模块只负责取数、缓存，以及**作废/恢复**这两个动作，**不做过滤或重排**。
 */
import { computed, ref } from 'vue'

import { dashboardApi } from '@/api/dashboard'
import { calendarApi } from '@/api/calendar'
import { useToast } from '@/composables/useToast'
import type {
  ArchivedList,
  CalendarEvent,
  CalendarEventUpdatePayload,
  PendingList,
  PendingTab,
  PendingWithArchived,
} from '@/types/portal'

/** 清单数据。`null` = 还没取到或取失败（**不是**"没有事项"，那是 `total: 0`）。 */
const pending = ref<PendingWithArchived | null>(null)
const isLoading = ref(false)
const errorMessage = ref('')
/** 抽屉是否展开。放这里是为了让任何组件都能唤出它（如快捷键、卡片入口）。 */
const isDrawerOpen = ref(false)

/**
 * 当前标签页（全部 / 今天 / 已过期 / 未安排）。
 *
 * 放在共享状态里而不是组件内，是为了**记住上次看的那页**：
 * 关掉抽屉再打开时还停在原处，不用重新点一遍。
 *
 * 过滤**完全依赖后端返回的 `bucket` 字段**，前端不重算判定规则——
 * 否则角标数字（后端算）与列表条数（前端算）会分叉。
 */
const activeTab = ref<PendingTab>('all')

/**
 * 顶部提示（作废后的 5 秒提示 + 「撤销」）。
 *
 * ⚠️ 提示状态**不在本模块**，而是共用 `useToast()`（见那个文件）：
 * 主题按钮的"功能待开发"提示也要显示同一种提示，两处各写一份会导致
 * 时长、计时器、进度条各改一遍。这里只负责"作废后要提示什么"。
 *
 * 渲染由 `AppToast.vue` 负责（挂 `App.vue`）。
 */
const { show: showToast } = useToast()

/** 防止并发请求互相覆盖：只有最后一次请求的结果会被采纳。 */
let requestVersion = 0

export function usePendingTasks() {
  /**
   * 取回清单（含废纸篓）。
   *
   * `silent: true` 用于"已有数据、只想刷新"的场景（如勾选后）——
   * 此时不显示 loading，避免列表闪烁。
   */
  async function refresh({ silent = false }: { silent?: boolean } = {}) {
    const version = ++requestVersion
    if (!silent) isLoading.value = true
    errorMessage.value = ''
    try {
      const data = await dashboardApi.pending()
      // 版本不一致说明有更新的请求在飞，丢弃这次结果（乱序返回时不能覆盖新数据）。
      if (version !== requestVersion) return
      pending.value = data
    } catch (error) {
      if (version !== requestVersion) return
      console.error(error)
      errorMessage.value = error instanceof Error ? error.message : '待做清单加载失败。'
      // 置 null 而不是空列表：空列表会被误读成"没有待做事项"。
      pending.value = null
    } finally {
      if (version === requestVersion) isLoading.value = false
    }
  }

  /**
   * 用聚合端点的结果直接填充，省掉一次额外请求（首屏 `Dashboard` 调 `overview` 时用）。
   *
   * ⚠️ 要连同 `archived` 与 `completed` 一起传，否则抽屉的标签页/折叠区会一直空着——
   * `overview` 里三者都有，别在这里只挑 `pending`。
   */
  function hydrate(list: PendingList, archived: ArchivedList, completed: ArchivedList) {
    pending.value = { ...list, archived, completed }
    errorMessage.value = ''
  }

  /**
   * 作废一条（**无二次确认**，用户 2026-10-07 明确要求）。
   *
   * 之所以敢不做确认：作废是可逆的，而且**立刻给出带「撤销」的提示**
   * （5 秒）。确认框对高频操作是负担，而可撤销的即时操作体验更好。
   */
  async function archiveItem(event: CalendarEvent) {
    // 乐观更新：先从列表移除，避免等待网络导致的迟滞。
    const before = pending.value
    if (before) {
      pending.value = {
        ...before,
        items: before.items.filter((e) => e.id !== event.id),
        shown: Math.max(0, before.shown - 1),
        total: Math.max(0, before.total - 1),
      }
    }
    try {
      const saved = await calendarApi.setArchived(event.id, true)
      // 刷新以获得后端排序与真实计数（乐观那步只是为了让界面立刻响应）。
      await refresh({ silent: true })
      // 「撤销」作为提示上的操作按钮——点击后恢复该条。
      // 用闭包捕获 id，所以不需要"提示里存 undoId"这种间接做法。
      showToast({
        text: `已作废「${event.title}」`,
        action: { label: '撤销', run: () => unarchiveItem(event.id) },
      })
      return saved
    } catch (error) {
      console.error(error)
      pending.value = before // 回滚
      showToast({ text: '作废失败，请重试' })
      throw error
    }
  }

  /** 撤销作废（提示里的「撤销」按钮，以及折叠区里的「恢复」）。 */
  async function unarchiveItem(id: number) {
    try {
      await calendarApi.setArchived(id, false)
      await refresh({ silent: true })
      showToast({ text: '已恢复' })
    } catch (error) {
      console.error(error)
      showToast({ text: '恢复失败，请重试' })
      throw error
    }
  }

  /**
   * 取消完成（「已完成」标签页里的「恢复」按钮）。
   *
   * 与 `unarchiveItem` 是**两件不同的事**：
   *   - 取消完成 = 这条还没做完，退回待做清单；
   *   - 恢复作废 = 这条要做，退出废纸篓。
   * 都叫「恢复」是因为对用户而言都是"把这条弄回来"。
   */
  async function uncompleteItem(id: number) {
    try {
      await calendarApi.setCompletion(id, false)
      await refresh({ silent: true })
      showToast({ text: '已恢复为待做' })
    } catch (error) {
      console.error(error)
      showToast({ text: '恢复失败，请重试' })
      throw error
    }
  }

  /**
   * 修改一条事项（docs/14 §11.3）。
   *
   * ⚠️ **改完必须 `refresh()`，不能只改本地对象**。原因：
   * 排序（§2.4）与分桶（§11.1）都由**后端**派生，本地改完不刷新会让
   * **角标数字与该页实际条数分叉**——那正是"两套数据源"那类缺陷的翻版。
   * 例如把一条过期的改到下周，它应当从「已过期」页移到「全部」页；
   * 这个位移只有刷新后才正确。
   *
   * 与其他动作不同，这里**不做乐观更新**：修改涉及"旧值→新值"的多字段，
   * 本地模拟后端的排序/分桶逻辑等于把规则抄第二遍。改完等一次刷新更可靠。
   *
   * 提示文案刻意**不叫「已保存」**：用户改的是"这条的什么"，
   * 说清楚比笼统的"成功"更有用（且此时列表可能已经把它移走了）。
   */
  async function updateItem(id: number, payload: CalendarEventUpdatePayload) {
    try {
      const saved = await calendarApi.update(id, payload)
      await refresh({ silent: true })
      showToast({ text: `已修改「${saved.title}」` })
      return saved
    } catch (error) {
      console.error(error)
      showToast({ text: '修改失败，请重试' })
      throw error
    }
  }

  function openDrawer() {
    isDrawerOpen.value = true
    // 打开时若还没有数据，顺手取一次；有数据则不打扰（由调用方决定是否 refresh）。
    if (!pending.value && !isLoading.value) void refresh()
  }

  function closeDrawer() {
    isDrawerOpen.value = false
  }

  function toggleDrawer() {
    if (isDrawerOpen.value) closeDrawer()
    else openDrawer()
  }

  return {
    // 状态
    pending: computed(() => pending.value),
    isLoading: computed(() => isLoading.value),
    errorMessage: computed(() => errorMessage.value),
    isDrawerOpen: computed(() => isDrawerOpen.value),
    /** 未完成总数；数据未到时为 `null`（与真实的 0 区分）。 */
    total: computed(() => pending.value?.total ?? null),
    items: computed<CalendarEvent[]>(() => pending.value?.items ?? []),

    // ---- 标签页（§11.1）----
    activeTab: computed(() => activeTab.value),
    /**
     * 当前标签页要显示的事项。
     *
     * - `all` 显示全部**未完成**的（用户决定：「全部」不含已完成，
     *   否则主视图会随时间被已完成的事淹没）；
     * - 分类页按后端给的 `bucket` 过滤；
     * - `completed` 用后端单独返回的已完成列表（它不在 `items` 里）。
     */
    visibleItems: computed(() => {
      if (activeTab.value === 'completed') return pending.value?.completed?.items ?? []
      const all = pending.value?.items ?? []
      if (activeTab.value === 'all') return all
      return all.filter((item) => item.bucket === activeTab.value)
    }),
    /**
     * 每个标签页的角标数字。
     *
     * ⚠️ 数字**全部来自后端**，不是前端数出来的——
     * 后端保证 `counts[x]` 与 `bucket === x` 的条数相等（有用例固化这条不变量）。
     * 「全部」用 `total`（真实总数，可能大于已加载的条数）；「已完成」用后端总数。
     *
     * ⚠️ 「全部」的角标**不等于**其余各页之和：它不含已完成项（用户决定）。
     * 别"顺手修正"成相加，那会把已完成的事混进主视图。
     */
    tabs: computed(() => {
      const counts = pending.value?.counts
      return [
        { key: 'all' as const, label: '全部', count: pending.value?.total ?? 0 },
        { key: 'today' as const, label: '今天', count: counts?.today ?? 0 },
        { key: 'overdue' as const, label: '已过期', count: counts?.overdue ?? 0 },
        { key: 'unscheduled' as const, label: '未安排', count: counts?.unscheduled ?? 0 },
        { key: 'completed' as const, label: '已完成', count: pending.value?.completed?.total ?? 0 },
      ]
    }),
    /** 废纸篓内容（按作废时间倒序，后端定序）。 */
    archivedItems: computed<CalendarEvent[]>(() => pending.value?.archived?.items ?? []),
    archivedTotal: computed(() => pending.value?.archived?.total ?? 0),
    /** 已完成内容（按完成时间倒序，后端定序）。 */
    completedItems: computed<CalendarEvent[]>(() => pending.value?.completed?.items ?? []),
    completedTotal: computed(() => pending.value?.completed?.total ?? 0),
    // 动作
    setActiveTab(tab: PendingTab) {
      activeTab.value = tab
    },
    refresh,
    hydrate,
    archiveItem,
    unarchiveItem,
    uncompleteItem,
    updateItem,
    openDrawer,
    closeDrawer,
    toggleDrawer,
    /** 仅测试/热重载用：把模块状态复位。 */
    __reset() {
      requestVersion = 0
      pending.value = null
      isLoading.value = false
      errorMessage.value = ''
      isDrawerOpen.value = false
      activeTab.value = 'all'
    },
  }
}
