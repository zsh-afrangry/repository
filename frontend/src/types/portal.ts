/**
 * 门户（记账 / 标签 / 日历 / 天气 / Dashboard）的前后端数据契约。
 *
 * 这些类型原先散落在 `Bills.vue` 与 `Dashboard.vue` 的 `<script>` 里——只有视图自己能看见，
 * `api/` 层无从复用。2026-09-20 抽出，与 TradeSim 侧的 `types/tradesim.ts` 对齐。
 *
 * ⚠ 这里**只放接口响应与领域类型**。视图私有的展示类型（`DayGroup`、`CalendarDay`、
 *   `Project` 之类）留在各自视图里，不要往里塞。
 * ⚠ 字段是否必然有值，以**后端 OpenAPI** 为准。本项目的类型文件历史上出现过
 *   "声明得比现实更严格"的毛病（见 `types/tradesim.ts` 顶部注释），别凭印象加必填。
 */

// ---------- 标签 ----------

/**
 * `tags` 表的一行。
 *
 * 两个查询接口返回的东西**不像名字听起来那么简单**，实测：
 *
 * | 接口 | 数量 | 含义 |
 * |---|---|---|
 * | `GET /tags/` | **25** 条根标签 | 其中 4 条是带 `children` 的 category；**根标签里不只含 category**，还含 payment_platform / payment_channel / fund_type |
 * | `GET /tags/all` | **39** 条 | 25 个根 + 14 个小类的"成员全集"，**不是**纯扁平结构——category 项同样带 `children` |
 *
 * 所以：① 用 `/tags/` 时必须按 `type` 过滤，那句 filter 不是冗余代码；
 * ② 用 `/tags/all` 时按 `type` 分组与服务端 `?tag_type=` 过滤**完全等价**（ID 集合逐一对上，
 * 见 当前标签加载契约），不要写成"因为它扁平所以没有 children"。
 */
export interface TagOut {
  id: number
  name: string
  type: string
  parent_id: number | null
  sort_order: number
  children: TagOut[]
}

// ---------- 账单 ----------

/**
 * `bills` 表的一行（含后端预载的 5 个标签关系）。
 *
 * ⚠ `amount` 是**字符串**：后端列是 `Numeric(12,2)`，实测返回 `"12.00"`。而**写入**时传的是
 * 数字（见 `BillPayload.amount`）。两边不一样是正常的，不要"统一"它们。
 */
export interface BillItem {
  id: number
  record_type: '支出' | '收入'
  expense_date: string
  expense_time: string | null
  amount: string
  category_id: number | null
  subcategory_id: number | null
  payment_platform_id: number | null
  payment_channel_id: number | null
  fund_type_id: number | null
  category: TagOut | null
  subcategory: TagOut | null
  payment_platform: TagOut | null
  payment_channel: TagOut | null
  fund_type: TagOut | null
  reimbursement_status: string
  reimbursement_amount: string | null
  transaction_id: string | null
  note: string | null
  /** 后端会返回，界面暂未使用。 */
  created_at: string
  updated_at: string
}

/** `GET /bills/` 的分页信封。 */
export interface BillListResponse {
  total: number
  items: BillItem[]
}

/**
 * `GET /bills/summary/monthly`。
 *
 * 三个金额都是 `number`：后端在 2026-09-20 补上了 `response_model`（详见 当前月汇总契约）。
 * 在此之前它走 `jsonable_encoder`，同一个字段会在 int `0` 与 float `644.71` 之间摇摆类型。
 * 所以这里可以放心当数字用，**不需要** `parseFloat`。
 */
export interface MonthlySummary {
  year: number
  month: number
  income: number
  expense: number
  net: number
}

/** 新建 / 修改账单的请求体（字段与 `Bills.vue` 的表单一致）。 */
export interface BillPayload {
  record_type: '支出' | '收入'
  expense_date: string
  expense_time: string | null
  /** 写入用数字。响应里的 `BillItem.amount` 是字符串，两者刻意不同。 */
  amount: number
  category_id: number | null
  subcategory_id: number | null
  payment_platform_id: number | null
  payment_channel_id: number | null
  fund_type_id: number | null
  reimbursement_status: string
  note: string | null
}

// ---------- 日历 ----------

/**
 * 与后端 `CalendarEventTone` 枚举一致。
 *
 * **2026-10-06 收敛为两值**（见 docs/14 §4.1）：原 `plan`（计划）语义并入 `meeting`，
 * 原 `bill`（账单提醒）弃用——它与账单页的 `bills` 表职责重叠且从无数据。
 * 收敛时该表 0 行，因此零数据迁移。
 */
export type CalendarEventTone = 'todo' | 'meeting'

export interface CalendarEvent {
  id: number
  event_date: string
  event_time: string | null
  /** 前端补出来的展示字段（`HH:MM` 或「全天」），**不是**接口字段。 */
  time?: string
  title: string
  detail: string | null
  tone: CalendarEventTone
  /**
   * 完成时间戳；`null` = 未完成。
   *
   * 后端为可空字段，但**新建时一定没有**，所以标成可选而非必填——
   * 本文件顶部有约定：字段是否必然有值以后端 OpenAPI 为准，别声明得比现实更严格。
   */
  completed_at?: string | null
  /**
   * 作废时间戳；`null` = 未作废（2026-10-07 新增）。
   *
   * 语义是"**我决定不做了**"——主动放弃，可恢复（废纸篓）。
   * 与 `completed_at` **互不影响**：一条已完成的事项也可以被作废。
   *
   * ⚠️ 作废 ≠ 删除：记录仍在，日历照常显示它，抽屉的折叠区里能查看并恢复。
   */
  archived_at?: string | null
}

/** 新建日程的请求体。 */
export interface CalendarEventPayload {
  event_date: string
  event_time: string | null
  title: string
  detail: string | null
  tone: CalendarEventTone
}

// ---------- Dashboard ----------

/**
 * `GET /dashboard/git-stats/`。
 *
 * 原先前端只内联声明了 `{ month_commits: number }` 并靠 `as` 断言，另外两个字段被丢掉了；
 * 实测真实响应是三个字段。
 *
 * ⚠️ 新代码请优先用 `DashboardOverview`；本类型只为兼容既有 `gitStats()` 调用而保留。
 */
export interface GitStats {
  month_commits: number
  total_commits: number
  month_start: string
}

/**
 * `GET /dashboard/overview/` 的「本周进度」段。
 *
 * ⚠️ `ratio` 为 `null` 表示**分母为 0**（例如周一早上还没任何事项），
 * 前端必须显示 `--` 而不是 `0%`——`0%` 会被误读成"一项都没完成"。
 */
export interface WeekProgress {
  /** 本周周一，`YYYY-MM-DD`。 */
  start: string
  /** 本周周日，`YYYY-MM-DD`。 */
  end: string
  /** 分母：本周事项总数（todo + meeting）。 */
  total: number
  /** 其中手动完成的条数。 */
  done: number
  /** 其中时间已过且未完成的条数（仅供展示，不等于分子贡献）。 */
  overdue: number
  /** 分子：算作达成的事项数。 */
  numerator: number
  /** 百分比，保留 1 位小数；分母为 0 时为 `null`。 */
  ratio: number | null
}

/**
 * 本月代码量（口径④：只算源码后缀，`docs/14 §6.1`）。
 *
 * 接口不可用时整个对象为 `null`（前端显示 `--`），而不是返回 0——
 * `0` 表示"确实没改代码"，两者语义必须区分。
 */
export interface CodeLines {
  period: 'month'
  month_start: string
  added: number
  deleted: number
  /** 新增 − 删除，**可能为负**（项目收缩也是事实）。 */
  net: number
  binary_files: number
}

/** Notes 汇总。数据源在 `notes_topics`，由后端 `app/notes/aggregates.py` 计算。 */
export interface NotesUnits {
  topics: number
  sections: number
  units: number
}

export interface GitCommits {
  month: number
  total: number
}

/**
 * 待做清单的分类计数。
 *
 * ⚠️ 三个数字**互不重叠**，按优先级判定：`overdue` > `unscheduled` > `today`。
 * 未来的事项（有时间、不是今天、也没过期）**不占任何分类**，
 * 所以三者之和 **≤ `total`**，前端不要假设它们相加等于总数。
 */
export interface PendingCounts {
  /** 已过时间点且未完成——欠账，最需要处理。 */
  overdue: number
  /** 今天到期且未过期。 */
  today: number
  /** 没有具体时间（极速录入的产物）——需要被安排。 */
  unscheduled: number
}

/**
 * 待做事项的标签页分组（docs/14 §11.6）。
 *
 * 由后端 `pending_bucket()` 判定，随每条事项一起返回。
 * **前端不要自己重算**——角标数字与列表过滤都从同一个后端字段派生，
 * 自己算等于把规则抄一遍（§12.5 的教训）。
 */
export type PendingBucket = 'overdue' | 'today' | 'unscheduled'

/** 抽屉标签页的标识。`all` 是兜底页，`archived` 不在标签页里（它是底部折叠区）。 */
export type PendingTab = 'all' | PendingBucket

/**
 * 待做事项条目 = 事件本身 + 后端判定的标签页分组。
 *
 * `bucket` 为 `null` 表示"有时间的未来事项"，它**不属于任何分类标签页**，
 * 只在「全部」页出现。这不是遗漏：三个分类不构成完整划分，
 * 所以「全部」页是必需的兜底（否则这类事项会在每个标签页里都看不见）。
 */
export interface PendingItem extends CalendarEvent {
  bucket: PendingBucket | null
}

/**
 * `GET /dashboard/pending/`（以及 `overview.pending`）的响应。
 *
 * 口径：**所有未完成的事项，不限日期**。刻意不用固定窗口（本周/本月），
 * 因为固定窗口会让边界事项"隐身"——周五记"下周一交"，当天看不到。
 *
 * `items` 已由后端排好序（无时间的排最前，其余按日期+时刻升序），
 * **前端不要再排序**：排序规则是产品决策，改它应该改后端一处。
 */
export interface PendingList {
  /** 未完成事项的**真实总数**（可能大于 `items.length`）。 */
  total: number
  /** 本次实际返回的条数。 */
  shown: number
  counts: PendingCounts
  /** `true` 表示因超过上限被截断——前端必须提示，不能静默。 */
  truncated: boolean
  items: PendingItem[]
}

/**
 * 废纸篓（`archived` 段）。
 *
 * 语义（docs/14 §2.5）：作废 = "**我决定不做了**"，与"完成"是两件事。
 * 可查看、可恢复——不是删除。所以它**没有** `counts`：
 * 「过期/今天/未安排」那套分类是给待办优先级用的，废纸篓不需要。
 */
export interface ArchivedList {
  total: number
  shown: number
  truncated: boolean
  /** 按**作废时间倒序**（最近作废的在前）——它是回顾用的。 */
  items: CalendarEvent[]
}

/** `GET /dashboard/pending/` 的完整响应：待做清单 + 废纸篓。 */
export interface PendingWithArchived extends PendingList {
  archived: ArchivedList
}

/** `GET /dashboard/overview/` 的完整响应。 */
export interface DashboardOverview {
  week: WeekProgress
  stats: {
    /** 接口取不到时为 `null` → 前端显示 `--`。 */
    code_lines: CodeLines | null
    /** 只依赖数据库，正常不会为 null；仍标可空以防后端降级。 */
    notes_units: NotesUnits | null
    /** 接口取不到时为 `null` → 前端显示 `--`。 */
    git_commits: GitCommits | null
  }
  /** 待做清单（与 `/pending/` 同一份口径）。 */
  pending: PendingList
  /** 废纸篓。 */
  archived: ArchivedList
}

// ---------- 天气 ----------

export interface WeatherForecast {
  day: string
  icon: string
  tempHigh: number
  tempLow: number
}

/**
 * `GET /weather/`（后端代理 QWeather，依赖后端配置的 API key）。
 *
 * `updatedAt` **是接口字段**：`routers/weather.py` 手工拼 JSON，键名故意用 camelCase，
 * 值取 QWeather 的 `obsTime`，实测形如 `"2026-09-20T05:48+08:00"`；模板上的"更新于"
 * 就是拿它渲染的。这里标成可选，只是因为初始的占位对象里没有它。
 */
export interface WeatherInfo {
  /** 后端解析出的展示名，形如「广东省 · 广州市 · 天河区」。 */
  location: string
  /** 实际使用的 QWeather Location ID；后端在解析失败时会回退成 id 本身。 */
  locationId?: string
  temp: number
  condition: string
  icon: string
  feel: number
  humidity: number
  wind: string
  precip: string
  aqi: string
  forecast: WeatherForecast[]
  updatedAt?: string | null
}

/**
 * `GET /weather/locations?q=` 的单项结果。
 *
 * `id` 是 QWeather 的 Location ID，切城市时真正要传回去的就是它；
 * `label` 是后端按 adm1/adm2/name 拼好的展示名，前端不要自己再拼一遍。
 */
export interface WeatherLocation {
  id: string
  name: string
  label: string
  lat: string
  lon: string
}
