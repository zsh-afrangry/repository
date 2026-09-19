/** 日历日程接口（对应后端 `routers/calendar.py`，路由前缀是 `/calendar-events`）。 */
import { apiFetch } from './client'
import type { CalendarEvent, CalendarEventPayload } from '@/types/portal'

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

  /** `DELETE /calendar-events/{id}` */
  remove(id: number) {
    return apiFetch<null>(`/calendar-events/${id}`, { method: 'DELETE' })
  },
}
