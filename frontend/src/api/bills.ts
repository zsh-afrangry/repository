/** 账单接口（对应后端 `routers/bill.py`）。 */
import { apiFetch } from './client'
import type { BillItem, BillListResponse, BillPayload, MonthlySummary } from '@/types/portal'

export const billsApi = {
  /** `GET /bills/` —— 指定日期区间内的账单。 */
  listByRange(dateFrom: string, dateTo: string, limit = 200) {
    return apiFetch<BillListResponse>(
      `/bills/?date_from=${dateFrom}&date_to=${dateTo}&limit=${limit}`,
    )
  },

  /** `GET /bills/` —— 只取最新一条，用于把当前月份同步到"最近有账单的那个月"。 */
  listLatest(limit = 1) {
    return apiFetch<BillListResponse>(`/bills/?limit=${limit}`)
  },

  /** `GET /bills/summary/monthly` —— 月度收支。金额已是 number，无需 `parseFloat`。 */
  monthlySummary(year: number, month: number) {
    return apiFetch<MonthlySummary>(`/bills/summary/monthly?year=${year}&month=${month}`)
  },

  /** `POST /bills/` */
  create(payload: BillPayload) {
    return apiFetch<BillItem>('/bills/', { method: 'POST', body: JSON.stringify(payload) })
  },

  /** `PATCH /bills/{id}` */
  update(id: number, payload: BillPayload) {
    return apiFetch<BillItem>(`/bills/${id}`, { method: 'PATCH', body: JSON.stringify(payload) })
  },

  /** `DELETE /bills/{id}` —— 后端返回 204，`apiFetch` 会给出 `null`。 */
  remove(id: number) {
    return apiFetch<null>(`/bills/${id}`, { method: 'DELETE' })
  },
}
