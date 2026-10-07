/** Dashboard 卡片用的统计接口（对应后端 `routers/dashboard.py`）。 */
import { apiFetch } from './client'
import type { DashboardOverview, GitStats, PendingWithArchived } from '@/types/portal'

export const dashboardApi = {
  /**
   * `GET /dashboard/overview/` —— 首页四张卡的全部数据，一次请求拿全。
   *
   * 为什么是一个聚合端点而不是几个单卡端点：首屏一次请求避免各卡分别 loading
   * 造成布局跳动；"本周"边界、除零、时区等逻辑集中在后端一处（见 docs/14 §5.1）。
   *
   * ⚠️ 失败时**不要**退回成 0：该端点在 git 不可用时会把对应字段设为 `null` 并仍返回 200，
   * 前端据此显示 `--`。`0` 的语义是"确实是零"，两者不能混。
   */
  overview() {
    return apiFetch<DashboardOverview>('/dashboard/overview/')
  },

  /**
   * `GET /dashboard/pending/` —— 待做清单 + 废纸篓（所有未完成事项，不限日期）。
   *
   * 单独一个端点而不是复用 `overview()`：勾选完成、新增或作废后只需刷新清单，
   * 不必重取 git 统计与 Notes 汇总（那两项开销大，且不会因勾选而变）。
   *
   * ⚠️ 它同时返回 `archived`（废纸篓），因为抽屉里"待做列表"与"已作废折叠区"
   * 是同一屏；分两次请求会在作废/恢复时产生中间态。
   */
  pending() {
    return apiFetch<PendingWithArchived>('/dashboard/pending/')
  },

  /**
   * `GET /dashboard/git-stats/` —— 提交计数（旧端点，保留兼容）。
   *
   * 实测响应：`{"month_commits":21,"total_commits":30,"month_start":"2026-09-01"}`。
   * 新代码请用 `overview()`。
   */
  gitStats() {
    return apiFetch<GitStats>('/dashboard/git-stats/')
  },
}
