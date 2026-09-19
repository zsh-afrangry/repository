/** Dashboard 卡片用的统计接口（对应后端 `routers/dashboard.py`）。 */
import { apiFetch } from './client'
import type { GitStats } from '@/types/portal'

export const dashboardApi = {
  /**
   * `GET /dashboard/git-stats/` —— 提交计数。
   *
   * 实测响应：`{"month_commits":21,"total_commits":30,"month_start":"2026-09-01"}`。
   */
  gitStats() {
    return apiFetch<GitStats>('/dashboard/git-stats/')
  },
}
