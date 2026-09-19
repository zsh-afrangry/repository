/**
 * 日期工具（全部走**本地时区**）。
 *
 * ⚠ 这个文件存在的直接原因，是修掉一个真实的日期错误：
 *
 *   **不要用 `new Date().toISOString().slice(0, 10)` 取"今天"。**
 *
 * `toISOString()` 永远返回 UTC。在东八区，当地 00:00–07:59 对应的 UTC 还在前一天，于是
 * 这 8 小时里"今天"会被算成"昨天"。实测（`TZ=Asia/Shanghai`，当地日期为 2026-09-21）：
 *
 * | 当地时刻 | `dateToKey()` | `toISOString().slice(0,10)` |
 * |---|---|---|
 * | 00:30 | 2026-09-21 | **2026-09-20** |
 * | 03:30 | 2026-09-21 | **2026-09-20** |
 * | 07:30 | 2026-09-21 | **2026-09-20** |
 * | 08:30 | 2026-09-21 | 2026-09-21 |
 *
 * 记账表单的新建默认日期就踩了这个坑：凌晨记账时日期会默认成昨天。现在两处都改用
 * `todayKey()`（见 `Bills.vue`）。
 *
 * 这三个函数刻意写成**普通函数而不是 composable**：它们是纯函数、不涉及响应式状态，
 * 放进 `composables/` 只会让人误以为要用在 setup 作用域里。
 */

export function padDatePart(value: number) {
  return String(value).padStart(2, '0')
}

/** 把 `Date` 格式化成 `YYYY-MM-DD`（本地时区）。 */
export function dateToKey(date: Date) {
  return `${date.getFullYear()}-${padDatePart(date.getMonth() + 1)}-${padDatePart(date.getDate())}`
}

/**
 * 今天的 `YYYY-MM-DD`（本地时区）。
 *
 * 用它替代 `new Date().toISOString().slice(0, 10)` —— 两者在东八区凌晨 0–8 点**结果不同**，
 * 后者会给出昨天。
 */
export function todayKey() {
  return dateToKey(new Date())
}
