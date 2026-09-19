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
 * 见 docs/5 §2.18），不要写成"因为它扁平所以没有 children"。
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
 * 三个金额都是 `number`：后端在 2026-09-20 补上了 `response_model`（详见 docs/5 §2.14）。
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

/** 与后端 `CalendarEventTone` 枚举一致。 */
export type CalendarEventTone = 'todo' | 'plan' | 'meeting' | 'bill'

export interface CalendarEvent {
  id: number
  event_date: string
  event_time: string | null
  /** 前端补出来的展示字段（`HH:MM` 或「全天」），**不是**接口字段。 */
  time?: string
  title: string
  detail: string | null
  tone: CalendarEventTone
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
 */
export interface GitStats {
  month_commits: number
  total_commits: number
  month_start: string
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
  location: string
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
