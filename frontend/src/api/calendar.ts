/** 日历日程接口（对应后端 `routers/calendar.py`，路由前缀是 `/calendar-events`）。 */
import { apiFetch } from './client'
import type { CalendarEvent, CalendarEventPayload, CalendarEventUpdatePayload } from '@/types/portal'

export const calendarApi = {
  /** `GET /calendar-events/` —— 指定日期区间的日程。 */
  listByRange(dateFrom: string, dateTo: string) {
    return apiFetch<CalendarEvent[]>(`/calendar-events/?date_from=${dateFrom}&date_to=${dateTo}`)
  },

  /** `POST /calendar-events/` —— 返回被保存的那条（含后端生成的 id）。 */
  create(payload: CalendarEventPayload) {
    return apiFetch<CalendarEvent>('/calendar-events/', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  /**
   * `PATCH /calendar-events/{id}` —— 修改已有事项（docs/14 §11.3）。
   *
   * ⚠️ **清空字段要显式传 `null`，不能省略**。后端用 `exclude_unset=True`：
   * 不传 = 不动该字段，传 `null` = 清空。所以"把时间改回未安排"必须传
   * `{ event_time: null }`——若序列化时把它省略掉，用户会发现时间改得掉却清不掉。
   * 调用方（`PendingDrawer.vue`）负责构造完整载荷，见那里的说明。
   */
  update(id: number, payload: CalendarEventUpdatePayload) {
    return apiFetch<CalendarEvent>(`/calendar-events/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
  },

  /**
   * `PATCH /calendar-events/{id}/completion` —— 勾选 / 取消勾选完成。
   *
   * 刻意不走通用 `PATCH /{id}`：勾选是高频单一意图，若由前端传时间戳，
   * 客户端时钟与服务端不一致时会写进错误时间。这里只传布尔值，**时间由服务端取**。
   */
  setCompletion(id: number, done: boolean) {
    return apiFetch<CalendarEvent>(`/calendar-events/${id}/completion`, {
      method: 'PATCH',
      body: JSON.stringify({ done }),
    })
  },

  /**
   * `PATCH /calendar-events/{id}/archive` —— 作废 / 恢复（废纸篓）。
   *
   * 与 `setCompletion` 同样的设计：只传布尔意图，时间戳由服务端填。
   * 这也让「撤销」变得简单——把 `archived: false` 再传一次即可，
   * 前端不必记住原来的值。
   */
  setArchived(id: number, archived: boolean) {
    return apiFetch<CalendarEvent>(`/calendar-events/${id}/archive`, {
      method: 'PATCH',
      body: JSON.stringify({ archived }),
    })
  },

  /** `DELETE /calendar-events/{id}` */
  remove(id: number) {
    return apiFetch<null>(`/calendar-events/${id}`, { method: 'DELETE' })
  },
}
