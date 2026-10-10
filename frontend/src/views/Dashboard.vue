<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useDialogFocus } from '@/composables/useDialogFocus'
import { usePendingTasks } from '@/composables/usePendingTasks'
import { useScrollReveal } from '@/composables/useScrollReveal'
import { useToast } from '@/composables/useToast'
import KnowledgeMapBackground from '@/components/KnowledgeMapBackground.vue'
import WeatherLocationPicker from '@/components/ui/WeatherLocationPicker.vue'
import { calendarApi } from '@/api/calendar'
import { dashboardApi } from '@/api/dashboard'
import { weatherApi } from '@/api/weather'
import { dateToKey } from '@/utils/date'
import type {
  CalendarEvent,
  CalendarEventTone,
  DashboardOverview,
  WeatherInfo,
  WeatherLocation,
  WeekProgress,
} from '@/types/portal'

/* Calendar logic */
const now = new Date()
const calendarYear = ref(now.getFullYear())
const calendarMonth = ref(now.getMonth()) // 0-indexed
const selectedDate = ref(new Date(now.getFullYear(), now.getMonth(), now.getDate()))
const activeDate = ref<Date | null>(null)
const isCalendarModalOpen = ref(false)
const calendarDialog = ref<HTMLElement | null>(null)
useDialogFocus(isCalendarModalOpen, calendarDialog, closeCalendarModal)
let calendarLoadVersion = 0
let disposed = false

// CalendarEventTone / CalendarEvent 是接口类型，已抽到 @/types/portal（与 api/ 层共用）

type CalendarDay = {
  day: number
  current: boolean
  today: boolean
  date: Date
  dateKey: string
  hasEvents: boolean
  eventCount: number
  offset: -1 | 0 | 1
}

const calendarEvents = ref<Record<string, CalendarEvent[]>>({})

const newEventTime = ref('09:00')
const newEventTitle = ref('')
const newEventDetail = ref('')
const newEventTone = ref<CalendarEventTone>('todo')
const eventFormError = ref('')
const calendarLoadError = ref('')
const isCalendarLoading = ref(false)
const isEventSaving = ref(false)
const deletingEventId = ref<number | null>(null)

const calendarTitle = computed(() => {
  const d = new Date(calendarYear.value, calendarMonth.value)
  return d.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long' })
})

const weekdays = ['一', '二', '三', '四', '五', '六', '日']

// padDatePart / dateToKey 已抽到 @/utils/date（Bills.vue 也用它，且那边原先误用了 UTC 取日）

function normalizeEventTime(value: string | null) {
  if (!value) return '全天'
  return value.slice(0, 5)
}

function normalizeCalendarEvent(event: CalendarEvent): CalendarEvent {
  return {
    ...event,
    detail: event.detail || '暂无补充说明。',
    time: normalizeEventTime(event.event_time),
  }
}

function groupCalendarEvents(events: CalendarEvent[]) {
  return events.reduce<Record<string, CalendarEvent[]>>((groups, event) => {
    const normalized = normalizeCalendarEvent(event)
    const items = groups[normalized.event_date] ?? []
    groups[normalized.event_date] = [...items, normalized]
    return groups
  }, {})
}

// apiFetch 已抽到 @/api/client（原先这里与 Bills.vue 各有一份逐字符相同的实现）

function getVisibleCalendarRange() {
  const year = calendarYear.value
  const month = calendarMonth.value
  const firstDay = new Date(year, month, 1)
  const lastDay = new Date(year, month + 1, 0)
  let startOffset = firstDay.getDay() - 1
  if (startOffset < 0) startOffset = 6

  const startDate = new Date(year, month, 1 - startOffset)
  const totalCurrentCells = startOffset + lastDay.getDate()
  const trailingCells = totalCurrentCells % 7 === 0 ? 0 : 7 - (totalCurrentCells % 7)
  const endDate = new Date(year, month + 1, trailingCells)

  return {
    dateFrom: dateToKey(startDate),
    dateTo: dateToKey(endDate),
  }
}

async function loadCalendarEvents() {
  const version = ++calendarLoadVersion
  const { dateFrom, dateTo } = getVisibleCalendarRange()
  isCalendarLoading.value = true
  calendarLoadError.value = ''
  try {
    const events: CalendarEvent[] = await calendarApi.listByRange(dateFrom, dateTo)
    if (disposed || version !== calendarLoadVersion) return
    calendarEvents.value = groupCalendarEvents(events)
  } catch (error) {
    console.error(error)
    if (disposed || version !== calendarLoadVersion) return
    calendarEvents.value = {}
    calendarLoadError.value = error instanceof Error ? error.message : '日历事项加载失败。'
  } finally {
    if (!disposed && version === calendarLoadVersion) isCalendarLoading.value = false
  }
}

function formatDateTitle(date: Date | null) {
  if (!date) return ''
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'long',
  })
}

const selectedDateKey = computed(() => dateToKey(selectedDate.value))
const activeDateTitle = computed(() => formatDateTitle(activeDate.value))
const activeDateEvents = computed(() => {
  if (!activeDate.value) return []
  return calendarEvents.value[dateToKey(activeDate.value)] ?? []
})

const calendarDays = computed(() => {
  const year = calendarYear.value
  const month = calendarMonth.value
  const firstDay = new Date(year, month, 1)
  const lastDay = new Date(year, month + 1, 0)
  // Monday=0 based offset
  let startOffset = firstDay.getDay() - 1
  if (startOffset < 0) startOffset = 6

  const days: CalendarDay[] = []
  const buildDay = (date: Date, current: boolean, offset: -1 | 0 | 1): CalendarDay => {
    const todayDate = new Date()
    const dateKey = dateToKey(date)
    const isToday =
      date.getDate() === todayDate.getDate() &&
      date.getMonth() === todayDate.getMonth() &&
      date.getFullYear() === todayDate.getFullYear()

    return {
      day: date.getDate(),
      current,
      today: isToday,
      date,
      dateKey,
      hasEvents: Boolean(calendarEvents.value[dateKey]?.length),
      eventCount: calendarEvents.value[dateKey]?.length ?? 0,
      offset,
    }
  }

  // Previous month trailing days
  const prevLastDay = new Date(year, month, 0).getDate()
  for (let i = startOffset - 1; i >= 0; i--) {
    days.push(buildDay(new Date(year, month - 1, prevLastDay - i), false, -1))
  }
  // Current month
  for (let d = 1; d <= lastDay.getDate(); d++) {
    days.push(buildDay(new Date(year, month, d), true, 0))
  }
  // Next month leading days to fill grid (6 rows max)
  const remainder = days.length % 7
  if (remainder > 0) {
    for (let i = 1; i <= 7 - remainder; i++) {
      days.push(buildDay(new Date(year, month + 1, i), false, 1))
    }
  }
  return days
})

function prevMonth() {
  if (calendarMonth.value === 0) {
    calendarMonth.value = 11
    calendarYear.value--
  } else {
    calendarMonth.value--
  }
}

function nextMonth() {
  if (calendarMonth.value === 11) {
    calendarMonth.value = 0
    calendarYear.value++
  } else {
    calendarMonth.value++
  }
}

function selectCalendarDay(cell: CalendarDay) {
  selectedDate.value = new Date(cell.date)
  activeDate.value = new Date(cell.date)
  isCalendarModalOpen.value = true

  if (cell.offset !== 0) {
    calendarYear.value = cell.date.getFullYear()
    calendarMonth.value = cell.date.getMonth()
  }
}

function openTodaySchedule() {
  const today = new Date()
  selectedDate.value = today
  activeDate.value = today
  calendarYear.value = today.getFullYear()
  calendarMonth.value = today.getMonth()
  isCalendarModalOpen.value = true
}

function closeCalendarModal() {
  if (isEventSaving.value || deletingEventId.value !== null) return
  isCalendarModalOpen.value = false
  eventFormError.value = ''
}

/* ---------- 加号弹窗：新建事项（2026-10-06 新增） ----------
 *
 * 设计约定（用户第 11 条）：
 *  - **复用现有样式**：容器与表单沿用 `.calendar-modal-layer` / `.calendar-modal` /
 *    `.calendar-form-*`，不新增样式类。所以外观与日历弹窗一致。
 *  - 类型下拉只有 `todo` / `meeting` 两项（与收敛后的 DB 枚举一致）。
 *  - 时间选择器可选**年月日时分秒**，默认值为**当前电脑时间**；这个时间是 DDL，
 *    超过即视为过期。
 *
 * 为什么单独开一个弹窗、而不是复用日历弹窗：
 *  - 日历弹窗的日期来自"点击的格子"，而这里要能自由选日期+时间；
 *  - 日历弹窗的时间输入是 `type="time"`（只有时分），这里需要秒级。
 *  两者的**表单语义不同**，但**视觉完全复用**。
 */

const isAddEventModalOpen = ref(false)
const addEventDialog = ref<HTMLElement | null>(null)
useDialogFocus(isAddEventModalOpen, addEventDialog, closeAddEventModal)

const addEventForm = ref({
  title: '',
  detail: '',
  tone: 'todo' as CalendarEventTone,
  /** `datetime-local` 的值，形如 `2026-10-06T14:30:00`。 */
  dueAt: '',
})
const addEventError = ref('')
const isAddEventSaving = ref(false)

/** 把 `Date` 转成 `<input type="datetime-local">` 需要的本地时间字符串（含秒）。 */
function toDatetimeLocalValue(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
    + `T${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

function openAddEventModal() {
  // 默认值 = 当前电脑时间（用户第 11 条）
  addEventForm.value = {
    title: '',
    detail: '',
    tone: 'todo',
    dueAt: toDatetimeLocalValue(new Date()),
  }
  addEventError.value = ''
  isAddEventModalOpen.value = true
}

function closeAddEventModal() {
  if (isAddEventSaving.value) return
  isAddEventModalOpen.value = false
  addEventError.value = ''
}

async function submitAddEvent() {
  if (isAddEventSaving.value) return
  const title = addEventForm.value.title.trim()
  if (!title) {
    addEventError.value = '请先填写标题。'
    return
  }
  if (!addEventForm.value.dueAt) {
    addEventError.value = '请选择时间。'
    return
  }

  // 后端把日期与时间存成两列（决策见 docs/14 §4.2），这里拆开传。
  const [datePart, timePart = '00:00:00'] = addEventForm.value.dueAt.split('T')

  isAddEventSaving.value = true
  addEventError.value = ''
  try {
    const saved = await calendarApi.create({
      event_date: datePart,
      event_time: timePart,
      title,
      detail: addEventForm.value.detail.trim() || null,
      tone: addEventForm.value.tone,
    })
    mergeEventIntoState(saved)
    isAddEventModalOpen.value = false
    // 新增会同时改变待做清单与周进度，两者都在 /overview/ 里，刷一次即可。
    await refreshOverview()
  } catch (error) {
    console.error(error)
    addEventError.value = error instanceof Error ? error.message : '保存失败。'
  } finally {
    isAddEventSaving.value = false
  }
}

/**
 * 把一条事项并入本地 `calendarEvents`（按日期分槽、同 id 去重）。
 *
 * 新增与勾选共用它，避免两处各写一份合并逻辑而漏掉去重。
 * 日期可能不在当前日历可视月份内（例如从加号弹窗选了别的月份），
 * 那样它不会显示在网格里，但周卡片仍能通过日期比较看到它。
 */
function mergeEventIntoState(event: CalendarEvent) {
  const dateKey = event.event_date
  const bucket = calendarEvents.value[dateKey] ?? []
  const without = bucket.filter((e) => e.id !== event.id)
  calendarEvents.value = {
    ...calendarEvents.value,
    [dateKey]: [...without, normalizeCalendarEvent(event)],
  }
}

/** 事项列表里的短日期，形如 `10/06`。 */
function formatShortDate(dateKey: string): string {
  const [, month, day] = dateKey.split('-')
  return `${month}/${day}`
}

function resetEventForm() {
  newEventTime.value = '09:00'
  newEventTitle.value = ''
  newEventDetail.value = ''
  newEventTone.value = 'todo'
  eventFormError.value = ''
}

async function addCalendarEvent() {
  if (!activeDate.value || isEventSaving.value || isCalendarLoading.value) return
  const title = newEventTitle.value.trim()
  const detail = newEventDetail.value.trim()

  if (!title) {
    eventFormError.value = '请先填写事项标题。'
    return
  }

  const dateKey = dateToKey(activeDate.value)
  isEventSaving.value = true
  eventFormError.value = ''
  try {
    const savedEvent: CalendarEvent = await calendarApi.create({
      event_date: dateKey,
      event_time: newEventTime.value || null,
      title,
      detail: detail || null,
      tone: newEventTone.value,
    })

    const nextEvent = normalizeCalendarEvent(savedEvent)
    calendarEvents.value = {
      ...calendarEvents.value,
      [dateKey]: [...(calendarEvents.value[dateKey] ?? []), nextEvent],
    }
    resetEventForm()
  } catch (error) {
    console.error(error)
    eventFormError.value = error instanceof Error ? error.message : '事项保存失败。'
  } finally {
    isEventSaving.value = false
  }
}

async function deleteCalendarEvent(eventId: number) {
  if (!activeDate.value || deletingEventId.value !== null) return
  const dateKey = dateToKey(activeDate.value)
  deletingEventId.value = eventId
  try {
    await calendarApi.remove(eventId)
    const remainingEvents = (calendarEvents.value[dateKey] ?? []).filter((event) => event.id !== eventId)
    const nextEvents = { ...calendarEvents.value }

    if (remainingEvents.length) {
      nextEvents[dateKey] = remainingEvents
    } else {
      delete nextEvents[dateKey]
    }

    calendarEvents.value = nextEvents
  } catch (error) {
    console.error(error)
    eventFormError.value = error instanceof Error ? error.message : '事项删除失败。'
  } finally {
    deletingEventId.value = null
  }
}

interface RichProject {
  name: string
  desc: string
  label: string
  status: '可进入' | '进行中' | '预留' | '等待接入'
  route: string | null
  tone: string
  idCode: string
  stats: { label: string; value: string | number }[]
  progress?: number
  tags?: string[]
}

const router = useRouter()
const isDark = ref(true)

const searchQuery = ref('')
const statusFilter = ref('all')
const viewType = ref('grid')

const projects = ref<RichProject[]>([
  {
    name: '记账',
    desc: '收支记录、标签体系和月度统计，当前主力可用模块。',
    label: 'BILLING',
    status: '可进入',
    route: '/bills',
    tone: 'cyan',
    idCode: '01',
    stats: [
      { label: '本月记录', value: '236 条' },
      { label: '本月支出', value: '¥8,962' },
      { label: '分类标签', value: '36 个' }
    ]
  },
  {
    name: '知识图谱',
    desc: '按前置与后续关系组织基础知识，聚焦查看每条学习路径。',
    label: 'LEARNING MAP',
    status: '可进入',
    route: '/notes',
    tone: 'violet',
    idCode: '02',
    progress: 72,
    stats: [
      { label: '节点数', value: '1,248' },
      { label: '关联关系', value: '3,672' },
      { label: '待处理', value: '28' }
    ]
  },
  {
    name: 'TradeSim',
    desc: '行情回测、策略参数实验与温冷分离的量化组合档案。',
    label: 'QUANT RESEARCH',
    status: '可进入',
    route: '/tradesim',
    tone: 'rose',
    idCode: '07',
    progress: 64,
    stats: [
      { label: '策略流派', value: '1 套' },
      { label: '数据层', value: 'MySQL + Mongo' },
      { label: '回测入口', value: '已接入' }
    ]
  },
  {
    name: 'AutoML',
    desc: '实验记录、模型训练和自动化评估的后续工作台。',
    label: 'MACHINE LEARNING',
    status: '进行中',
    route: null,
    tone: 'emerald',
    idCode: '03',
    stats: [
      { label: '实验运行', value: '18 / 25' },
      { label: '模型训练', value: '124 / 160' },
      { label: '数据集', value: '6 / 10' }
    ]
  },
  {
    name: '运维中心',
    desc: '系统监控、告警、日志与资源管理中心。',
    label: 'OPERATIONS',
    status: '预留',
    route: null,
    tone: 'amber',
    idCode: '04',
    stats: [
      { label: '告警', value: '2 个' },
      { label: '日志量', value: '24.6 GB' },
      { label: '在线节点', value: '8 台' }
    ]
  },
  {
    name: '服务集成',
    desc: '第三方服务接入、API 网关与密钥管理。',
    label: 'SERVICES',
    status: '等待接入',
    route: null,
    tone: 'rose',
    idCode: '05',
    tags: ['API 网关', 'OAuth 2.0', 'Webhook'],
    stats: []
  },
  {
    name: '文档资料库',
    desc: '项目文档、设计方案与知识沉淀库。',
    label: 'DOCUMENTS',
    // A5 修复（2026-09-20，已获批准 — 卡片状态约定）：这张卡原本是
    // status: '可进入' + route: null，自相矛盾（说可进入却点不进去）。
    // 与 05「服务集成」对齐为「等待接入」。纯显示修正，**不改变任何可点性**；
    // 真给它一个路由属于新功能，不在本次整理范围。
    status: '等待接入',
    route: null,
    tone: 'slate',
    idCode: '06',
    stats: [
      { label: '文档数', value: '156' },
      { label: '最近更新', value: '今天 09:42' },
      { label: '成员协作', value: '6 人' }
    ]
  },
  {
    // 储物间：存放从主界面撤下的静态界面草稿（原落地页的 journal / newsletter / 作者区）。
    // 纯归档页，不接任何后端数据，见 views/Vault.vue。
    name: '储物间',
    desc: '存放已从主界面撤下的静态界面草稿，仅作归档与日后取用。',
    label: 'ARCHIVE',
    status: '可进入',
    route: '/vault',
    tone: 'slate',
    idCode: '08',
    stats: [
      { label: '归档界面', value: '3 块' },
      { label: '图片资源', value: '6 个' },
      { label: '数据接入', value: '无' }
    ]
  }
])

const filteredProjects = computed(() => {
  return projects.value.filter(p => {
    const matchesSearch = p.name.toLowerCase().includes(searchQuery.value.toLowerCase()) || 
                          p.desc.toLowerCase().includes(searchQuery.value.toLowerCase())
    const matchesStatus = statusFilter.value === 'all' || p.status === statusFilter.value
    return matchesSearch && matchesStatus
  })
})

// WeatherForecast / WeatherInfo 是接口类型，已抽到 @/types/portal

// 加载完成前的地点占位。**不要再写具体城市名**：地点现在由用户选择并持久化，
// 这里若写死「广州天河」，上次选了别的城市时会先闪一下错误的地点。
const weatherInfo = ref<WeatherInfo>({
  location: '正在读取…',
  temp: 0,
  condition: '等待天气数据',
  icon: '🌤️',
  feel: 0,
  humidity: 0,
  wind: '--',
  precip: '0',
  aqi: '--',
  forecast: [
    { day: '--', icon: '🌤️', tempHigh: 0, tempLow: 0 },
    { day: '--', icon: '🌤️', tempHigh: 0, tempLow: 0 },
    { day: '--', icon: '🌤️', tempHigh: 0, tempLow: 0 },
    { day: '--', icon: '🌤️', tempHigh: 0, tempLow: 0 },
    { day: '--', icon: '🌤️', tempHigh: 0, tempLow: 0 }
  ]
})
const weatherLoadError = ref('')
const weatherLoading = ref(false)

/* 天气地点：选中的是 QWeather Location ID，展示名由后端返回。
 * 持久化只用 localStorage（纯本机偏好，不涉及后端存储）；读不到就回落到后端默认城市。 */
const WEATHER_LOCATION_KEY = 'km.weather.locationId'
const weatherLocationId = ref<string>(readStoredLocationId())

function readStoredLocationId(): string {
  try {
    return window.localStorage.getItem(WEATHER_LOCATION_KEY) || ''
  } catch {
    // 隐私模式等场景下 localStorage 可能直接抛错，静默回落到默认城市
    return ''
  }
}

async function loadWeather(locationId = weatherLocationId.value) {
  weatherLoadError.value = ''
  weatherLoading.value = true
  try {
    const info = await weatherApi.current(locationId || undefined)
    weatherInfo.value = info
    // 后端解析失败时会把 id 当展示名回传，那种情况不写回，避免把坏值持久化
    if (info?.locationId) weatherLocationId.value = info.locationId
  } catch (error) {
    console.error(error)
    weatherLoadError.value = error instanceof Error ? error.message : '天气数据加载失败。'
  } finally {
    weatherLoading.value = false
  }
}

function changeWeatherLocation(location: WeatherLocation) {
  weatherLocationId.value = location.id
  try {
    window.localStorage.setItem(WEATHER_LOCATION_KEY, location.id)
  } catch {
    // 存不下不影响本次切换，只是刷新后会回到默认城市
  }
  void loadWeather(location.id)
}

function formatWeatherUpdatedAt(value?: string | null) {
  if (!value) return '刚刚'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '刚刚'
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

/* 待做事项卡片（第二轮，2026-10-07 改造）
 *
 * **数据源不再用 `calendarEvents`**。原因：那份数据只装了日历当前可见月份
 * （`getVisibleCalendarRange()`）的事件，于是——
 *   1. "下周一交作业"如果不在当前月份范围内，根本不在数据里；
 *   2. 点日历的「下个月」会让卡片变空，而进度数字不变（两套窗口）。
 * 现在改为消费后端 `GET /dashboard/pending/`：它返回**所有未完成的事项，不限日期**，
 * 排序与分类也由后端定（口径集中在 `crud/calendar.pending_events()` 一处）。
 *
 * 呈现规则（docs/14 §2.4）：
 *   - 摘要只显示前 3 条 —— 卡片是"扫一眼"，全量交给将来的侧拉抽屉
 *   - **必须同时显示分类计数**，否则被截掉的事项会变成新的"隐身"
 */

/** 后端返回的待做清单。 */
const {
  pending,
  errorMessage: pendingError,
  hydrate: hydratePending,
  openDrawer,
  refresh: refreshPending,
} = usePendingTasks()

/** 全站共享的顶部提示（主题按钮的"功能待开发"用它，见 notifyThemePending）。 */
const { show: showToast } = useToast()

/** 摘要显示几条。超出部分靠计数体现，不靠列表。 */
const PENDING_PREVIEW = 3

/** 摘要里要显示的事项（后端已排好序，前端只截断，不重排）。 */
const pendingPreview = computed<CalendarEvent[]>(
  () => (pending.value?.items ?? []).slice(0, PENDING_PREVIEW),
)

/** 分类计数的展示用数组（值为 0 的不显示，避免占位噪声）。 */
const pendingCounts = computed(() => {
  const counts = pending.value?.counts
  if (!counts) return []
  const rows = [
    { key: 'overdue', label: '过期', value: counts.overdue, tone: 'overdue' },
    { key: 'today', label: '今天', value: counts.today, tone: 'today' },
    { key: 'unscheduled', label: '未安排', value: counts.unscheduled, tone: 'unscheduled' },
  ]
  return rows.filter((r) => r.value > 0)
})

/**
 * 日历卡片底部「今日安排」列表的数据。
 *
 * 用**今天**（而不是日历里选中的那天）：这个块的标题就是"今日安排"。
 * 数据与日期弹窗共用 `calendarEvents`，所以两边永远一致。
 */
const todayScheduleEvents = computed<CalendarEvent[]>(() => {
  const events = calendarEvents.value[dateToKey(new Date())] ?? []
  return [...events].sort((a, b) =>
    (a.event_time ?? '99:99').localeCompare(b.event_time ?? '99:99'))
})

/** tone 的中文名。收敛为两值后只剩这两种（docs/14 §4.1）。 */
function toneLabel(tone: CalendarEventTone): string {
  return tone === 'meeting' ? '安排' : '待做'
}

/**
 * 本周进度：直接消费后端的 `week` 段。
 *
 * ⚠️ 不在前端重算分子/分母。原因（docs/14 §5.2）：口径里有两处易错逻辑——
 * `todo` 与 `meeting` 的"达成"规则相反、以及跨天过期比较。
 * 放前端算等于把这套规则抄一遍，两边迟早不一致。
 */
const weekProgressData = ref<WeekProgress | null>(null)

/**
 * 判断某事项当前是否"已过期"。
 *
 * 与后端 `crud/calendar.counts_as_progress()` **刻意不一致**，别试图统一：
 *  - 后端那个函数回答"算不算达成"（`todo` 过期=失败，`meeting` 过期=完成）；
 *  - 这里回答"要不要显示「过期」标记"（两类都显示，因为对用户来说
 *    "这件事的时间已经过了"是同一个事实）。
 *
 * 空 `event_time` 兜底当天 23:59:59，与后端 `event_due_at()` 一致。
 */
function isEventOverdue(event: CalendarEvent): boolean {
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

/** 勾选 / 取消勾选完成。乐观更新 + 失败回滚。 */
const togglingEventIds = ref<Set<number>>(new Set())

async function toggleEventCompletion(event: CalendarEvent) {
  if (togglingEventIds.value.has(event.id)) return
  const nextDone = !event.completed_at

  // 乐观更新：先改本地，让点击立刻有反馈。
  const previous = event.completed_at ?? null
  event.completed_at = nextDone ? new Date().toISOString() : null
  togglingEventIds.value = new Set(togglingEventIds.value).add(event.id)

  try {
    const saved = await calendarApi.setCompletion(event.id, nextDone)
    // 用服务端返回的时间戳覆盖本地猜测值，避免依赖客户端时钟。
    event.completed_at = saved.completed_at ?? null
    // 勾选同时改变「待做清单」与「本周进度」，两者都在 `/overview/` 里，
    // 所以刷一次就够——不必分别请求（那会多打一次 git 统计）。
    await refreshOverview()
  } catch (error) {
    console.error(error)
    event.completed_at = previous // 回滚
  } finally {    const next = new Set(togglingEventIds.value)
    next.delete(event.id)
    togglingEventIds.value = next
  }
}

/**
 * 重新取一遍首页聚合数据（周进度 + 三个统计 + 待做清单）。
 *
 * 勾选、新增、删除事项之后调用它。名字刻意不叫 `loadWeekProgress`——
 * 它取的不只是周进度，叫错了会让人以为这里可以只刷一部分。
 *
 * 失败时**保持原值**，不清零：宁可显示旧数据，也不要把进度归零误导用户。
 */
async function refreshOverview() {
  try {
    const data = await dashboardApi.overview()
    weekProgressData.value = data.week
    applyStats(data.stats)
    // 用聚合结果直接填充共享状态，省掉一次 `/pending/` 请求。
    hydratePending(data.pending, data.archived, data.completed)
  } catch (error) {
    console.error(error)
    // 保持原值，见上方说明。
  }
}

/* Weekly Progress —— 2026-10-06 起接真实数据 */
/**
 * 三个统计的展示值。
 *
 * ⚠️ `null` 与 `0` 必须区分（用户第 13 条）：
 *  - `null` → 接口失败或代码 bug → 显示 `--`
 *  - `0`    → 真实情况就是零   → 显示 `0`
 * 所以这里存 `number | null`，而不是用 `?? 0` 抹平。
 */
const stats = ref<DashboardOverview['stats'] | null>(null)
const statsError = ref('')

function applyStats(next: DashboardOverview['stats']) {
  stats.value = next
}

/** 展示用格式化：`null`/`undefined` → `--`。 */
function formatStat(value: number | null | undefined): string {
  if (value === null || value === undefined) return '--'
  return value.toLocaleString('zh-CN')
}

/** 代码量净变化带正负号：`+551` / `-120`。 */
function formatNetLines(value: number | null | undefined): string {
  if (value === null || value === undefined) return '--'
  const sign = value > 0 ? '+' : ''
  return sign + value.toLocaleString('zh-CN')
}

/** 甜甜圈的百分比文案。分母为 0（ratio 为 null）时显示 `--`。 */
const weekRatioText = computed(() => {
  const ratio = weekProgressData.value?.ratio
  return ratio === null || ratio === undefined ? '--' : `${ratio}%`
})

/** 甜甜圈画多少。`ratio` 为 null 时画 0，**绝不画 NaN**（否则 SVG 整条失效）。 */
const weekRatioArc = computed(() => {
  const ratio = weekProgressData.value?.ratio
  return ratio === null || ratio === undefined ? 0 : ratio
})

/**
 * 甜甜圈下方的说明文案。
 *
 * 由真实进度决定，原先写死成"进度良好 ▴"——那会在 0% 时也说"良好"。
 */
const weekRatioLabel = computed(() => {
  const ratio = weekProgressData.value?.ratio
  if (ratio === null || ratio === undefined) return '本周暂无事项'
  if (ratio >= 80) return '进度良好 ▴'
  if (ratio >= 50) return '稳步推进 ▸'
  if (ratio > 0) return '仍需努力 ▾'
  return '尚未开始'
})

async function loadOverview() {
  try {
    const data = await dashboardApi.overview()
    weekProgressData.value = data.week
    applyStats(data.stats)
    hydratePending(data.pending, data.archived, data.completed)
    statsError.value = ''
  } catch (error) {
    console.error(error)
    statsError.value = error instanceof Error ? error.message : '统计数据加载失败。'
    // 失败时置 null 而不是 0 —— 前端据此显示 `--`（用户第 13 条）。
    stats.value = { code_lines: null, notes_units: null, git_commits: null }
    weekProgressData.value = null
    // 清单也交给共享状态去取（它会自行把失败表现为 null，而不是空列表）。
    void refreshPending()
  }
}

function handleCardClick(route: string | null) {
  if (route) router.push(route)
}

function handleCardMouseMove(event: MouseEvent) {
  const card = event.currentTarget as HTMLElement
  if (!card) return
  const rect = card.getBoundingClientRect()
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top
  card.style.setProperty('--mouse-x', `${x}px`)
  card.style.setProperty('--mouse-y', `${y}px`)
}


/* --- Constellation Background Logic --- */
interface Particle {
  x: number
  y: number
  vx: number
  vy: number
  radius: number
  baseOpacity: number
}

const constellationCanvas = ref<HTMLCanvasElement | null>(null)
let bgParticles: Particle[] = []
let canvasAnimationId = 0
let reducedMotionQuery: MediaQueryList | null = null
// 滚动揭示的观察器：必须由本组件持有并在卸载时断开。
// useScrollReveal() 是在 onMounted 里调用的，那时没有活动的 effect scope，
// 所以组合式函数内部无法用 onScopeDispose 自动清理——清理责任在调用方。
let revealObserver: IntersectionObserver | null = null
const bgMouse = { x: -9999, y: -9999 }

function handleCanvasMouseMove(event: MouseEvent) {
  if (!constellationCanvas.value) return
  const rect = constellationCanvas.value.getBoundingClientRect()
  bgMouse.x = event.clientX - rect.left
  bgMouse.y = event.clientY - rect.top
}

function handleCanvasMouseLeave() {
  bgMouse.x = -9999
  bgMouse.y = -9999
}

function initBgParticles() {
  const canvas = constellationCanvas.value
  if (!canvas) return
  bgParticles = []
  const count = Math.min(45, Math.floor((canvas.width * canvas.height) / 18000))
  for (let i = 0; i < count; i++) {
    bgParticles.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      vx: (Math.random() - 0.5) * 0.45,
      vy: (Math.random() - 0.5) * 0.45,
      radius: Math.random() * 1.5 + 0.8,
      baseOpacity: Math.random() * 0.3 + 0.12
    })
  }
}

function resizeBgCanvas() {
  const canvas = constellationCanvas.value
  if (!canvas) return
  canvas.width = canvas.parentElement?.clientWidth ?? window.innerWidth
  canvas.height = canvas.parentElement?.clientHeight ?? window.innerHeight
  initBgParticles()
}

function animateBgConstellation() {
  if (reducedMotionQuery?.matches) {
    canvasAnimationId = 0
    return
  }

  const canvas = constellationCanvas.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  ctx.clearRect(0, 0, canvas.width, canvas.height)

  const maxDistance = 115
  // Cyan (103, 232, 249) in dark mode, Violet (124, 58, 237) in light mode
  const rgbStr = isDark.value ? '103, 232, 249' : '124, 58, 237'

  for (let i = 0; i < bgParticles.length; i++) {
    const p1 = bgParticles[i]

    p1.x += p1.vx
    p1.y += p1.vy

    if (p1.x < 0 || p1.x > canvas.width) p1.vx *= -1
    if (p1.y < 0 || p1.y > canvas.height) p1.vy *= -1

    // Gently attract to mouse
    if (bgMouse.x !== -9999 && bgMouse.y !== -9999) {
      const dx = bgMouse.x - p1.x
      const dy = bgMouse.y - p1.y
      const dist = Math.sqrt(dx * dx + dy * dy)
      if (dist < 180) {
        p1.x += dx * 0.005
        p1.y += dy * 0.005
      }
    }

    ctx.beginPath()
    ctx.arc(p1.x, p1.y, p1.radius, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(${rgbStr}, ${p1.baseOpacity})`
    ctx.fill()

    for (let j = i + 1; j < bgParticles.length; j++) {
      const p2 = bgParticles[j]
      const dx = p1.x - p2.x
      const dy = p1.y - p2.y
      const dist = Math.sqrt(dx * dx + dy * dy)

      if (dist < maxDistance) {
        const opacity = (1 - dist / maxDistance) * 0.16
        ctx.beginPath()
        ctx.moveTo(p1.x, p1.y)
        ctx.lineTo(p2.x, p2.y)
        ctx.strokeStyle = `rgba(${rgbStr}, ${opacity})`
        ctx.lineWidth = 0.55
        ctx.stroke()
      }
    }

    if (bgMouse.x !== -9999 && bgMouse.y !== -9999) {
      const dx = p1.x - bgMouse.x
      const dy = p1.y - bgMouse.y
      const dist = Math.sqrt(dx * dx + dy * dy)
      if (dist < 135) {
        const opacity = (1 - dist / 135) * 0.26
        ctx.beginPath()
        ctx.moveTo(p1.x, p1.y)
        ctx.lineTo(bgMouse.x, bgMouse.y)
        ctx.strokeStyle = `rgba(${rgbStr}, ${opacity})`
        ctx.lineWidth = 0.75
        ctx.stroke()
      }
    }
  }

  canvasAnimationId = requestAnimationFrame(animateBgConstellation)
}

function handleMotionPreferenceChange() {
  if (!reducedMotionQuery) return

  if (reducedMotionQuery.matches) {
    cancelAnimationFrame(canvasAnimationId)
    canvasAnimationId = 0
    return
  }

  if (!canvasAnimationId) {
    animateBgConstellation()
  }
}

function scrollToSection(id: string) {
  const target = document.querySelector<HTMLElement>(id)
  target?.scrollIntoView({ behavior: reducedMotionQuery?.matches ? 'auto' : 'smooth', block: 'start' })
}

/**
 * Dark-theme lock (RETAINED INTENTIONALLY — see main.css `.theme-light`).
 *
 * History: the first version of the portal had a day/night toggle. It was
 * removed once the starfield background became the only design, and this
 * function was left behind to pin the dark class. `isDark` is initialised to
 * `true` and never set to `false` anywhere, so the `else` branch below is
 * currently unreachable and `.theme-light` can never be applied.
 *
 * Owner's decision (2026-09-20): keep the light palette and this plumbing so
 * the theme can be revived later — do NOT delete either one. The nav theme
 * button now exists, but it deliberately does NOT switch the theme: it only
 * calls notifyThemePending() below, which shows a transient
 * "feature not implemented yet" notice that fades out after 3s.
 * When the theme is actually revived, wire the button to flip `isDark` and then
 * call this function.
 */
function updateThemeClass() {
  if (isDark.value) {
    document.documentElement.classList.remove('theme-light')
  } else {
    document.documentElement.classList.add('theme-light')
  }
}

/**
 * 主题按钮的占位行为（用户 2026-09-20 要求）。
 *
 * 当前不切换主题：浅色主题的配色与 CSS 变量都已保留（main.css 的
 * `.theme-light`），但功能本身尚未接入，因此点击只弹出一条"功能待开发"提示。
 * 日后真正接入时，把这里替换为：
 *   isDark.value = !isDark.value
 *   updateThemeClass()
 *
 * 提示改用全站共享的 `useToast()`（原先在本组件内联实现）：
 * 它与作废提示是**同一种东西**，各写一份会让时长、倒计时、进度条各改一遍。
 * 顺带的好处是提示现在挂在 `App.vue` 上，因此在任何路由都能显示——
 * 原先内联在这里，只有首页能看到。
 */
function notifyThemePending() {
  showToast({
    text: '主题切换功能待开发',
    detail: '浅色主题的样式与变量都已保留，接入后会在这里切换。',
    durationMs: 3000,
  })
}

onMounted(() => {
  isDark.value = true
  updateThemeClass()
  loadCalendarEvents()
  loadWeather()
  // 一次拿全四张卡需要的统计（聚合端点，见 docs/14 §5.2）。
  // 原先是分开调 loadGitStats()，现在合并成一个请求。
  loadOverview()
  revealObserver = useScrollReveal()

  // Initialize and run constellation background
  window.addEventListener('resize', resizeBgCanvas)
  resizeBgCanvas()
  reducedMotionQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
  reducedMotionQuery.addEventListener('change', handleMotionPreferenceChange)
  if (!reducedMotionQuery.matches) {
    animateBgConstellation()
  }
})

watch([calendarYear, calendarMonth], () => {
  loadCalendarEvents()
})

onBeforeUnmount(() => {
  disposed = true
  calendarLoadVersion++
  window.removeEventListener('resize', resizeBgCanvas)
  cancelAnimationFrame(canvasAnimationId)
  // 断开滚动揭示观察器。原实现丢弃了 useScrollReveal() 的返回值，观察器会一直
  // 持有这些 DOM 节点（组件已卸载但节点无法回收），并继续对脱离文档的元素写 class。
  revealObserver?.disconnect()
  revealObserver = null
  reducedMotionQuery?.removeEventListener('change', handleMotionPreferenceChange)
  reducedMotionQuery = null
  // 主题提示的定时器不用在这里清了：它已移到全站共享的 useToast（模块级单例，
  // 没有"组件卸载后写状态"的问题——提示本来就该跨页面存活）。
})
</script>

<template>
  <div class="dashboard-shell">
    <KnowledgeMapBackground />
    <header class="dashboard-nav">
      <a class="brand-mark" href="#top" aria-label="KnowledgeMap home" @click.prevent="scrollToSection('#top')">
        <span class="brand-letter">K</span>
        <span>
          <strong>KNOWLEDGEMAP</strong>
          <small>个人开发中枢</small>
        </span>
      </a>

      <nav class="nav-links" aria-label="Dashboard sections">
        <a href="#projects" class="active" @click.prevent="scrollToSection('#projects')">项目总览</a>
        <a href="#transformer" @click.prevent="router.push('/notes')">知识图谱</a>
        <a href="#lab" aria-disabled="true" title="功能待开发" @click.prevent="void(0)">实验室</a>
        <a href="#docs" aria-disabled="true" title="功能待开发" @click.prevent="void(0)">文档库</a>
        <a href="/vault" @click.prevent="router.push('/vault')">储物间</a>
        <button
          type="button"
          class="theme-toggle btn-tactile"
          aria-label="切换主题（功能待开发）"
          title="切换主题（功能待开发）"
          @click="notifyThemePending"
        >
          <span aria-hidden="true">🌙</span>
        </button>
        <div class="user-avatar" aria-label="User Profile">K</div>
      </nav>
    </header>

    <!-- 主题切换的"功能待开发"提示已改用全站共享的 AppToast（见 notifyThemePending）：
         浅色主题的配色与变量都保留着，但功能尚未接入。 -->

    <main id="top">
      <section class="hero-panel" @mousemove="handleCanvasMouseMove" @mouseleave="handleCanvasMouseLeave">
        <div class="hero-backdrop" aria-hidden="true">
          <canvas ref="constellationCanvas" class="constellation-canvas"></canvas>
        </div>

        <div class="hero-content">
          <p class="hero-kicker fade-in">
            <span>统一入口 · 项目中枢</span>
          </p>
          <h1 class="hero-title fade-in delay-1">个人开发中枢</h1>
          <p class="hero-copy fade-in delay-2">
            KnowledgeMap 汇聚你的工具、实验与知识资产，让每一次构建都可追踪、可复用、可进化。
          </p>

          <div class="hero-actions fade-in delay-3">
            <button type="button" class="primary-button btn-tactile" @click="scrollToSection('#projects')">
              <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" style="display: inline-block; vertical-align: middle;">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
              进入项目总览
            </button>
            <button type="button" class="outline-button btn-tactile" @click="router.push('/notes')">
              <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" style="display: inline-block; vertical-align: middle;">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 20l-5.447-2.724A2 2 0 013 15.485V6.757a2 2 0 011.556-1.954l8-2a2 2 0 011.888 0l8 2A2 2 0 0121 6.757v8.728a2 2 0 01-1.556 1.955L14 20a2 2 0 01-2 0z" />
              </svg>
              探索知识图谱
            </button>
          </div>

          <div class="hero-stats-row fade-in delay-3">
            <div class="stat-glass-card">
              <div class="stat-icon-wrapper cyan">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                </svg>
              </div>
              <div class="stat-data">
                <div class="stat-num">{{ formatNetLines(stats?.code_lines?.net) }}</div>
                <div class="stat-desc">代码量（本月）</div>
              </div>
            </div>
            <div class="stat-glass-card">
              <div class="stat-icon-wrapper violet">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <div class="stat-data">
                <div class="stat-num">{{ formatStat(stats?.notes_units?.units) }}</div>
                <div class="stat-desc">笔记与文档</div>
              </div>
            </div>
            <div class="stat-glass-card">
              <div class="stat-icon-wrapper emerald">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M1.5 12h6.5m8 0h6.5" />
                  <circle cx="12" cy="12" r="4" stroke-width="2" />
                </svg>
              </div>
              <div class="stat-data">
                <div class="stat-num">{{ formatStat(stats?.git_commits?.month) }}</div>
                <div class="stat-desc">Git 提交（本月）</div>
              </div>
            </div>
          </div>
        </div>

        <div class="hero-widgets-grid fade-in delay-4">
          <!-- Card 1: Weather Widget -->
          <div class="widget-card weather-widget">
            <div class="widget-header">
              <span class="widget-title">今天天气</span>
              <span class="widget-meta">
                <WeatherLocationPicker
                  :current-label="weatherInfo.location"
                  :busy="weatherLoading"
                  @select="changeWeatherLocation"
                />
              </span>
            </div>
            <div class="weather-main">
              <div class="weather-temp-block">
                <span class="weather-temp-icon">{{ weatherInfo.icon }}</span>
                <span class="weather-temp-num">{{ weatherInfo.temp }}</span>
                <span class="weather-temp-unit">°C</span>
              </div>
              <div class="weather-info-block">
                <div class="weather-status">{{ weatherInfo.condition }}</div>
                <div class="weather-details">体感 {{ weatherInfo.feel }}°C | 空气 AQI {{ weatherInfo.aqi }}</div>
              </div>
            </div>
            <div class="weather-metrics" aria-label="天气详情">
              <div class="weather-metric">
                <span class="weather-metric-label">湿度</span>
                <strong class="weather-metric-value">{{ weatherInfo.humidity }}%</strong>
              </div>
              <div class="weather-metric">
                <span class="weather-metric-label">风况</span>
                <strong class="weather-metric-value">{{ weatherInfo.wind }}</strong>
              </div>
              <div class="weather-metric">
                <span class="weather-metric-label">降水</span>
                <strong class="weather-metric-value">{{ weatherInfo.precip }} mm</strong>
              </div>
            </div>
            <div class="weather-forecast">
              <div v-for="f in weatherInfo.forecast" :key="f.day" class="forecast-col">
                <span class="forecast-day">{{ f.day }}</span>
                <span class="forecast-icon">{{ f.icon }}</span>
                <span class="forecast-temp-range">
                  <span class="forecast-temp-high">{{ f.tempHigh }}°</span>
                  <span class="forecast-temp-low">{{ f.tempLow }}°</span>
                </span>
              </div>
            </div>
            <div class="weather-footer">
              <span>更新于 {{ formatWeatherUpdatedAt(weatherInfo.updatedAt) }}</span>
              <span>数据源：和风天气</span>
            </div>
            <p v-if="weatherLoadError" class="weather-error">{{ weatherLoadError }}</p>
          </div>

          <!-- Card 2: Calendar & Events Widget -->
          <div class="widget-card calendar-widget">
            <div class="widget-header">
              <span class="widget-title">日历</span>
              <div class="cal-nav-wrapper">
                <span class="cal-title-small">{{ calendarTitle }}</span>
                <button type="button" class="cal-arrow" aria-label="日历上个月" @click="prevMonth">‹</button>
                <button type="button" class="cal-arrow" aria-label="日历下个月" @click="nextMonth">›</button>
              </div>
            </div>
            <div class="cal-weekdays">
              <span v-for="w in weekdays" :key="w">{{ w }}</span>
            </div>
            <div class="cal-grid">
              <button
                v-for="(cell, i) in calendarDays"
                :key="i"
                type="button"
                class="cal-day"
                :class="{
                  'is-other': !cell.current,
                  'is-today': cell.today,
                  'is-selected': cell.dateKey === selectedDateKey,
                  'has-events': cell.hasEvents,
                }"
                :aria-label="`${cell.dateKey}${cell.hasEvents ? `，${cell.eventCount}项安排` : ''}`"
                @click="selectCalendarDay(cell)"
              >
                <span class="cal-day-number">{{ cell.day }}</span>
                <span v-if="cell.hasEvents" class="cal-event-dot"></span>
              </button>
            </div>
            
            <!-- Today's Schedule -->
            <!--
              2026-10-06：原先这里是 3 条写死的假数据（项目站会 / AutoML 模型评估 /
              阅读：向量数据库原理），与日历网格、弹窗用的真实数据不一致。
              现改为消费 `activeDateEvents`（与弹窗同一份数据），
              这样从「本周待做」的＋新建的 meeting 会立刻出现在这里。
            -->
            <div class="today-schedule">
              <div class="schedule-header">
                <span>今日安排</span>
                <a href="#" class="view-all-link" @click.prevent="openTodaySchedule">查看全部</a>
              </div>
              <div v-if="todayScheduleEvents.length" class="schedule-list">
                <div v-for="event in todayScheduleEvents" :key="event.id" class="schedule-item">
                  <span class="sch-time">{{ event.event_time ? event.event_time.slice(0, 5) : '全天' }}</span>
                  <span class="sch-dot" :class="`dot-${event.tone}`"></span>
                  <span class="sch-title">{{ event.title }}</span>
                  <span class="sch-type">{{ toneLabel(event.tone) }}</span>
                </div>
              </div>
              <p v-else class="schedule-empty">今天没有安排。</p>
            </div>
          </div>

          <!-- Card 3: 待做事项（摘要） -->
          <!--
            第二轮改造（2026-10-07）：数据源从 `calendarEvents` 改为后端待做清单，
            修掉两个缺陷：固定周窗让"下周一交作业"看不到；翻月后卡片变空。
            摘要只显示 3 条，全量交给侧拉抽屉（docs/14 §11.1）。
          -->
          <div class="widget-card focus-widget">
            <div class="widget-header">
              <span class="widget-title">待做事项</span>
              <button
                type="button"
                class="widget-add-btn"
                aria-label="添加事项"
                title="添加待做或安排"
                @click="openAddEventModal"
              >
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" style="display: block;">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 5v14M5 12h14" />
                </svg>
              </button>
            </div>

            <!-- 分类计数：摘要只显示 3 条，这些数字保证"看不到的"仍然可见 -->
            <div v-if="pendingCounts.length" class="pending-counts">
              <span
                v-for="row in pendingCounts"
                :key="row.key"
                class="pending-count"
                :class="`count-${row.tone}`"
              >{{ row.label }} <strong>{{ row.value }}</strong></span>
            </div>

            <div v-if="pendingPreview.length" class="focus-checklist">
              <div
                v-for="event in pendingPreview"
                :key="event.id"
                class="focus-item"
                :class="{
                  'is-done': !!event.completed_at,
                  'is-overdue': isEventOverdue(event),
                  'is-toggling': togglingEventIds.has(event.id),
                }"
                role="checkbox"
                :aria-checked="!!event.completed_at"
                :aria-label="`${event.title}，${event.event_date}，${event.completed_at ? '已完成' : '未完成'}`"
                tabindex="0"
                @click="toggleEventCompletion(event)"
                @keydown.enter.prevent="toggleEventCompletion(event)"
                @keydown.space.prevent="toggleEventCompletion(event)"
              >
                <div class="checkbox-circle" :class="{ checked: !!event.completed_at }">
                  <svg v-if="event.completed_at" class="w-2.5 h-2.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" style="display: block;">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <div class="focus-body">
                  <span class="focus-text">{{ event.title }}</span>
                  <span class="focus-meta">
                    <span v-if="event.event_time" class="focus-date">{{ formatShortDate(event.event_date) }}</span>
                    <span v-else class="focus-unscheduled-tag">未安排</span>
                    <span class="focus-tone-tag" :class="`tag-${event.tone}`">{{ toneLabel(event.tone) }}</span>
                    <span v-if="isEventOverdue(event)" class="focus-overdue-tag">已过期</span>
                  </span>
                </div>
              </div>
            </div>
            <p v-else-if="pendingError" class="focus-empty">{{ pendingError }}</p>
            <p v-else-if="pending" class="focus-empty">没有未完成的事项。</p>

            <div class="focus-progress-block">
              <div class="progress-info">
                <span v-if="pending">
                  共 {{ pending.total }} 条未完成<template v-if="pending.truncated">（仅显示前 {{ pending.shown }} 条）</template>
                </span>
                <span v-else>--</span>
                <!-- 全量清单在抽屉里（本卡片是摘要，只显示 3 条，见 docs/14 §2.4） -->
                <button type="button" class="focus-view-all" @click="openDrawer">
                  查看全部 →
                </button>
              </div>
            </div>
          </div>

          <!-- Card 4: Weekly Progress Widget -->
          <!-- 2026-10-06：分子/分母改为后端计算（口径见 docs/14 §2） -->
          <div class="widget-card progress-widget">
            <div class="widget-header">
              <span class="widget-title">本周进度</span>
            </div>
            <div class="progress-content">
              <div class="donut-chart-container">
                <svg class="donut-chart" viewBox="0 0 36 36">
                  <path
                    class="donut-ring"
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    fill="none"
                    stroke="var(--border)"
                    stroke-width="3"
                  />
                  <path
                    class="donut-segment"
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    fill="none"
                    stroke="url(#progress-gradient)"
                    stroke-width="3.5"
                    stroke-linecap="round"
                    :stroke-dasharray="`${weekRatioArc}, 100`"
                  />
                  <defs>
                    <linearGradient id="progress-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stop-color="#7c3aed" />
                      <stop offset="100%" stop-color="#06b6d4" />
                    </linearGradient>
                  </defs>
                </svg>
                <div class="donut-text">
                  <span class="donut-percentage">{{ weekRatioText }}</span>
                  <span class="donut-label">{{ weekRatioLabel }}</span>
                </div>
              </div>
              <div class="stats-indicators">
                <div class="stat-indicator-row">
                  <span class="indicator-marker check-mark">✓</span>
                  <span class="indicator-label">事项完成</span>
                  <span class="indicator-value">
                    {{ weekProgressData ? `${weekProgressData.numerator} / ${weekProgressData.total}` : '--' }}
                  </span>
                </div>
                <div class="stat-indicator-row">
                  <span class="indicator-marker code-mark">⌨</span>
                  <span class="indicator-label">代码提交（本月）</span>
                  <span class="indicator-value">{{ formatStat(stats?.git_commits?.month) }}</span>
                </div>
                <div class="stat-indicator-row">
                  <span class="indicator-marker doc-mark">目</span>
                  <span class="indicator-label">笔记单元</span>
                  <span class="indicator-value">{{ formatStat(stats?.notes_units?.units) }}</span>
                </div>
                <div class="stat-indicator-row">
                  <span class="indicator-marker code-mark">行</span>
                  <span class="indicator-label">代码量（本月）</span>
                  <span class="indicator-value">{{ formatNetLines(stats?.code_lines?.net) }}</span>
                </div>
                <div v-if="weekProgressData" class="progress-updated-time">
                  本周 {{ formatShortDate(weekProgressData.start) }} – {{ formatShortDate(weekProgressData.end) }}
                </div>
                <p v-if="statsError" class="progress-updated-time">{{ statsError }}</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="projects" class="section-block">
        <div class="section-heading reveal-item">
          <p>PROJECT INDEX</p>
          <h2>项目总览</h2>
          <span>参考示例的展示型节奏，保留当前门户的暗色产品气质。</span>
        </div>

        <!-- Filter & Stats Bar -->
        <div class="filter-stats-bar reveal-item">
          <div class="stats-pills">
            <span class="pill-badge all">项目总数 <strong>18</strong> 个</span>
            <span class="pill-badge active-pill">进行中 <strong>6</strong> 个</span>
            <span class="pill-badge reserve-pill">预留 <strong>5</strong> 个</span>
            <span class="pill-badge waiting-pill">等待接入 <strong>7</strong> 个</span>
          </div>
          <div class="filter-controls">
            <div class="search-input-wrapper">
              <svg class="search-icon w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input v-model="searchQuery" type="text" placeholder="搜索项目名称或关键词..." class="search-box" />
            </div>
            <select v-model="statusFilter" class="filter-select" aria-label="筛选项目状态">
              <option value="all">全部状态</option>
              <option value="可进入">可进入</option>
              <option value="进行中">进行中</option>
              <option value="预留">预留</option>
              <option value="等待接入">等待接入</option>
            </select>
            <div class="view-toggle">
              <span>视图: </span>
              <select v-model="viewType" class="view-select" aria-label="切换视图方式">
                <option value="grid">品</option>
                <option value="list">行</option>
              </select>
            </div>
          </div>
        </div>

        <p v-if="!filteredProjects.length" role="status" class="text-text-muted py-8">没有匹配的项目，请调整搜索或筛选条件。</p>
        <div class="project-grid-v2" :class="{ 'is-list': viewType === 'list' }">
          <article
            v-for="(project, index) in projects"
            v-show="filteredProjects.includes(project)"
            :key="project.name"
            class="project-card-v2 reveal-item"
            :class="[`tone-${project.tone}`, { 'is-clickable': project.route }]"
            :style="{ transitionDelay: `${index * 60}ms` }"
            @click="handleCardClick(project.route)"
            :role="project.route ? 'link' : undefined"
            :tabindex="project.route ? 0 : undefined"
            :aria-label="project.route ? `进入${project.name}` : undefined"
            @keydown.enter="handleCardClick(project.route)"
            @keydown.space.prevent="handleCardClick(project.route)"
            @mousemove="handleCardMouseMove"
          >
            <!-- Status Badge -->
            <div class="card-status-badge" :class="`badge-${project.tone}`">
              <span class="status-indicator"></span>
              {{ project.status }}
            </div>

            <div class="card-main-content">
              <!-- Circular Icon Container -->
              <div class="project-circle-icon" :class="`bg-circle-${project.tone}`">
                <svg v-if="project.tone === 'cyan'" class="w-5.5 h-5.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                </svg>
                <svg v-else-if="project.tone === 'violet'" class="w-5.5 h-5.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 5.636l-3.536 3.536m0 5.656l3.536 3.536M9.172 9.172L5.636 5.636m3.536 9.192l-3.536 3.536M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-5 0a4 4 0 11-8 0 4 4 0 018 0z" />
                </svg>
                <svg v-else-if="project.tone === 'emerald'" class="w-5.5 h-5.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.364l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
                <svg v-else-if="project.tone === 'amber'" class="w-5.5 h-5.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
                </svg>
                <svg v-else-if="project.tone === 'rose'" class="w-5.5 h-5.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
                </svg>
                <svg v-else class="w-5.5 h-5.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h5.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2" />
                </svg>
              </div>

              <!-- Content Info -->
              <div class="project-info-block">
                <div class="project-kicker-row">
                  <span class="project-kicker-lbl">{{ project.label }}</span>
                  <span class="project-num-lbl">{{ project.idCode }}</span>
                </div>
                <h3 class="project-title-v2">{{ project.name }}</h3>
                <p class="project-desc-v2">{{ project.desc }}</p>

                <!-- Progress bar for Portal/KnowledgeMap -->
                <div v-if="project.progress" class="project-progress-container">
                  <div class="progress-label-v2">
                    <span>进度</span>
                    <span>{{ project.progress }}%</span>
                  </div>
                  <div class="progress-bar-v2">
                    <div class="progress-bar-fill-v2" :style="{ width: `${project.progress}%` }"></div>
                  </div>
                </div>

                <!-- Tags for Services -->
                <div v-if="project.tags" class="project-tags-container">
                  <span v-for="tag in project.tags" :key="tag" class="tag-pill">{{ tag }}</span>
                </div>

                <!-- Row metrics -->
                <div v-if="project.stats && project.stats.length > 0" class="project-stats-grid">
                  <div v-for="stat in project.stats" :key="stat.label" class="project-stat-item">
                    <span class="stat-lbl">{{ stat.label }}</span>
                    <span class="stat-val">{{ stat.value }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Card Footer -->
            <div class="card-footer-v2">
              <span class="footer-update-time">
                ⏱ 最近更新 30分钟前
              </span>
              <span class="footer-action-link" :class="{ 'opacity-40': !project.route }">
                {{ project.status === '进行中' ? '继续工作' : (project.status === '等待接入' ? '查看详情' : (project.status === '预留' ? '查看规划' : '进入模块')) }} ➔
              </span>
            </div>
          </article>
        </div>
      </section>

      <!-- Floating Action Button Stack (FAB) -->
      <div class="floating-fab-container">
        <button type="button" disabled title="功能待开发" class="fab-btn main-fab btn-tactile" aria-label="Add project">+</button>
        <button type="button" disabled title="功能待开发" class="fab-btn sub-fab btn-tactile" aria-label="Dashboard views">⊞</button>
        <button type="button" disabled title="功能待开发" class="fab-btn sub-fab btn-tactile" aria-label="Notifications">🔔</button>
        <button type="button" disabled title="功能待开发" class="fab-btn sub-fab btn-tactile" aria-label="Quick launch">🚀</button>
      </div>

    </main>

    <Transition name="calendar-modal">
      <div
        v-if="isCalendarModalOpen"
        class="calendar-modal-layer"
        role="presentation"
        @click.self="closeCalendarModal"
      >
        <section
          class="calendar-modal"
          ref="calendarDialog"
          tabindex="-1"
          data-lenis-prevent
          role="dialog"
          aria-modal="true"
          aria-labelledby="calendar-modal-title"
        >
          <button type="button" class="calendar-modal-close" aria-label="关闭日程弹窗" @click="closeCalendarModal">
            ×
          </button>
          <p class="calendar-modal-kicker">Daily Plan</p>
          <h2 id="calendar-modal-title">{{ activeDateTitle }}</h2>
          <p v-if="isCalendarLoading" class="calendar-inline-status">正在读取数据库中的安排...</p>
          <p v-else-if="calendarLoadError" class="calendar-form-error">{{ calendarLoadError }}</p>
          <form class="calendar-event-form" @submit.prevent="addCalendarEvent">
            <fieldset :disabled="isEventSaving || isCalendarLoading" class="calendar-form-fields">
            <div class="calendar-form-row">
              <label>
                <span>时间</span>
                <input v-model="newEventTime" type="time" aria-label="事项时间" />
              </label>
              <label>
                <span>类型</span>
                <select v-model="newEventTone" aria-label="事项类型">
                  <!-- 2026-10-06 收敛为两值：plan 并入 meeting，bill 弃用（docs/14 §4.1） -->
                  <option value="todo">待做</option>
                  <option value="meeting">安排</option>
                </select>
              </label>
            </div>
            <label>
              <span>标题</span>
              <input v-model="newEventTitle" type="text" placeholder="例如：整理今日计划" aria-label="事项标题" />
            </label>
            <label>
              <span>说明</span>
              <textarea v-model="newEventDetail" rows="2" placeholder="补充时间、地点或上下文" aria-label="事项说明"></textarea>
            </label>
            <div class="calendar-form-actions">
              <p v-if="eventFormError" class="calendar-form-error">{{ eventFormError }}</p>
              <button type="submit" :disabled="isEventSaving">{{ isEventSaving ? '保存中' : '增加' }}</button>
            </div>
            </fieldset>
          </form>
          <div v-if="activeDateEvents.length" class="calendar-event-list">
            <article
              v-for="event in activeDateEvents"
              :key="event.id"
              class="calendar-event-item"
              :class="`tone-${event.tone}`"
            >
              <time>{{ event.time }}</time>
              <div>
                <h3>{{ event.title }}</h3>
                <p>{{ event.detail }}</p>
              </div>
              <button
                type="button"
                class="calendar-event-delete"
                :aria-label="`删除 ${event.title}`"
                :disabled="deletingEventId !== null"
                @click="deleteCalendarEvent(event.id)"
              >
                {{ deletingEventId === event.id ? '删除中' : '删除' }}
              </button>
            </article>
          </div>
          <div v-else class="calendar-empty">
            <span>暂无安排</span>
            <p>这一天还没有安排，可在上方添加待办、计划或会议。</p>
          </div>
        </section>
      </div>
    </Transition>

    <!-- 加号弹窗：新建事项（2026-10-06）
         容器与表单刻意复用日历弹窗的类名，外观完全一致（用户第 11 条要求"复用现有样式"）。 -->
    <Transition name="calendar-modal">
      <div
        v-if="isAddEventModalOpen"
        class="calendar-modal-layer"
        role="presentation"
        @click.self="closeAddEventModal"
      >
        <section
          class="calendar-modal"
          ref="addEventDialog"
          tabindex="-1"
          data-lenis-prevent
          role="dialog"
          aria-modal="true"
          aria-labelledby="add-event-modal-title"
        >
          <button type="button" class="calendar-modal-close" aria-label="关闭新增事项弹窗" @click="closeAddEventModal">
            ×
          </button>
          <p class="calendar-modal-kicker">New Item</p>
          <h2 id="add-event-modal-title">添加事项</h2>
          <form class="calendar-event-form" @submit.prevent="submitAddEvent">
            <fieldset :disabled="isAddEventSaving" class="calendar-form-fields">
              <label>
                <span>类型</span>
                <select v-model="addEventForm.tone" aria-label="事项类型">
                  <option value="todo">待做（作业 / 研究 / 开发）</option>
                  <option value="meeting">安排（会议 / 日程）</option>
                </select>
              </label>
              <label>
                <span>时间（截止）</span>
                <!--
                  step="1" 让原生控件显示秒。默认 step 是 60（只到分钟），
                  而用户要求精确到秒、且"过期按秒计"。
                -->
                <input
                  v-model="addEventForm.dueAt"
                  type="datetime-local"
                  step="1"
                  aria-label="事项时间"
                />
              </label>
              <label>
                <span>标题</span>
                <input v-model="addEventForm.title" type="text" placeholder="例如：下周三交作业" aria-label="事项标题" />
              </label>
              <label>
                <span>说明</span>
                <textarea v-model="addEventForm.detail" rows="2" placeholder="补充上下文（可选）" aria-label="事项说明"></textarea>
              </label>
              <div class="calendar-form-actions">
                <p v-if="addEventError" class="calendar-form-error">{{ addEventError }}</p>
                <button type="submit" :disabled="isAddEventSaving">{{ isAddEventSaving ? '保存中' : '添加' }}</button>
              </div>
            </fieldset>
          </form>
        </section>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.dashboard-shell {
  min-height: 100dvh;
  position: relative;
  isolation: isolate;
  overflow-x: hidden;
  background: transparent;
  color: var(--text-primary);
  font-family: var(--font-sans), sans-serif;
  transition: color 0.3s ease, border-color 0.3s ease;
}

/* Light Mode Card Tone Overrides for High Contrast & Premium Look */
.theme-light .tone-cyan {
  --project-accent: #0891b2;
  --project-glow: rgba(6, 182, 212, 0.15);
}
.theme-light .tone-violet {
  --project-accent: #7c3aed;
  --project-glow: rgba(124, 58, 237, 0.15);
}
.theme-light .tone-emerald {
  --project-accent: #059669;
  --project-glow: rgba(16, 185, 129, 0.12);
}
.theme-light .tone-amber {
  --project-accent: #d97706;
  --project-glow: rgba(245, 158, 11, 0.12);
}
.theme-light .tone-rose {
  --project-accent: #e11d48;
  --project-glow: rgba(244, 63, 94, 0.12);
}
.theme-light .tone-slate {
  --project-accent: #475569;
  --project-glow: rgba(148, 163, 184, 0.1);
}

.dashboard-nav {
  position: sticky;
  top: 0;
  z-index: 30;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 2rem;
  padding: 1.1rem clamp(1.25rem, 3vw, 3rem);
  border-bottom: 1px solid var(--border-color);
  background: var(--nav-bg);
  backdrop-filter: blur(18px);
  transition: background 0.3s ease, border-color 0.3s ease;
}

.brand-mark {
  display: inline-flex;
  align-items: center;
  gap: 0.85rem;
}

.brand-letter {
  display: grid;
  width: 2.5rem;
  height: 2.5rem;
  place-items: center;
  border: 1px solid var(--border-color);
  background: var(--brand-bg);
  font-family: var(--font-serif), inherit;
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--text-title);
  transition: background 0.3s ease, border-color 0.3s ease, color 0.3s ease;
}

.brand-mark strong,
.brand-mark small {
  display: block;
}

.brand-mark strong {
  font-family: var(--font-serif), inherit;
  font-size: 0.92rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-title);
  transition: color 0.3s ease;
}

.brand-mark small {
  color: var(--text-secondary);
  font-size: 0.72rem;
  transition: color 0.3s ease;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: clamp(1rem, 2.5vw, 2rem);
  color: var(--text-secondary);
  font-size: 0.78rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  transition: color 0.3s ease;
}

.nav-links a {
  position: relative;
}

.nav-links a::after {
  position: absolute;
  left: 0;
  bottom: -0.35rem;
  width: 0;
  height: 1px;
  background: var(--nav-link-hover-border);
  content: "";
  transition: width 0.3s ease, background 0.3s ease;
}

.nav-links a:hover::after {
  width: 100%;
}

/* Base button and hover sweep definitions */
.primary-button,
.outline-button,
.nav-action {
  position: relative;
  overflow: hidden;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: color 0.35s ease, border-color 0.35s ease, transform 0.25s ease, box-shadow 0.25s ease;
  cursor: pointer;
}

.primary-button::before,
.outline-button::before,
.nav-action::before {
  content: "";
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background-color: var(--sweep-color);
  transition: left 0.35s cubic-bezier(0.25, 0.1, 0.25, 1);
  z-index: -1;
}

.primary-button:hover::before,
.outline-button:hover::before,
.nav-action:hover::before {
  left: 0;
}

.primary-button:hover,
.outline-button:hover,
.nav-action:hover {
  color: var(--sweep-text-color) !important;
  border-color: var(--sweep-color);
}

.nav-action {
  border: 1px solid var(--nav-action-border);
  padding: 0.62rem 1rem;
  color: var(--nav-action-text);
  background: transparent;
  --sweep-color: var(--nav-action-sweep);
  --sweep-text-color: var(--nav-action-sweep-text);
}

.nav-action:hover {
  transform: translateY(-1px);
}

.hero-panel {
  position: relative;
  display: grid;
  min-height: calc(100dvh - 4.8rem);
  grid-template-columns: minmax(0, 1.1fr) minmax(35rem, 1.3fr);
  gap: clamp(2rem, 4vw, 4rem);
  align-items: center;
  overflow: hidden;
  padding: clamp(3rem, 6vw, 5rem) clamp(1.25rem, 4vw, 4rem);
}

.hero-backdrop {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
}


.constellation-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.hero-content,
.hero-calendar {
  position: relative;
  z-index: 1;
}

.hero-kicker,
.section-heading p,
.pulse-copy p {
  color: var(--hero-kicker-color);
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  transition: color 0.3s ease;
}

.hero-title {
  max-width: 15ch;
  margin-top: 1.5rem;
  color: var(--text-title);
  font-family: var(--font-serif), inherit;
  font-size: clamp(2.8rem, 6vw, 5.5rem);
  font-weight: 800;
  letter-spacing: 0;
  line-height: 1;
  transition: color 0.3s ease;
}

.hero-copy {
  max-width: 44rem;
  margin-top: 1.7rem;
  color: var(--text-secondary);
  font-size: clamp(1rem, 1.55vw, 1.25rem);
  line-height: 1.85;
  transition: color 0.3s ease;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  align-items: center;
  margin-top: 2.4rem;
}

.primary-button,
.text-link {
  display: inline-flex;
  min-height: 2.85rem;
  align-items: center;
  justify-content: center;
  padding: 0 1.3rem;
  font-size: 0.84rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.primary-button {
  border: 1px solid var(--primary-btn-border);
  color: var(--primary-btn-text);
  background: transparent;
  --sweep-color: var(--primary-btn-sweep);
  --sweep-text-color: var(--primary-btn-sweep-text);
}

.primary-button:hover {
  box-shadow: var(--primary-btn-hover-shadow);
  transform: translateY(-2px);
}

.text-link {
  color: var(--text-secondary);
  transition: color 0.3s ease;
}

.text-link:hover {
  color: var(--text-title);
}

.hero-calendar {
  position: relative;
  z-index: 1;
  overflow: hidden;
  border: 1px solid color-mix(in srgb, var(--primary-btn-border) 24%, var(--status-border));
  background:
    linear-gradient(145deg, rgb(255 255 255 / 0.075), rgb(255 255 255 / 0.025)),
    color-mix(in srgb, var(--surface-card) 72%, transparent);
  box-shadow: 0 24px 70px rgb(0 0 0 / 0.18);
  padding: 1.5rem;
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  transition: border-color 0.3s ease, background 0.3s ease, box-shadow 0.3s ease;
}

.theme-light .hero-calendar {
  border-color: rgba(26, 26, 26, 0.12);
  background:
    linear-gradient(145deg, rgba(255, 255, 255, 0.58), rgba(255, 255, 255, 0.24)),
    rgba(248, 245, 242, 0.56);
  box-shadow: 0 24px 55px rgba(71, 58, 45, 0.12);
}

.cal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.2rem;
}

.cal-title {
  color: var(--text-title);
  font-family: var(--font-serif), inherit;
  font-size: 1.05rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  transition: color 0.3s ease;
}

.cal-nav {
  display: grid;
  width: 2rem;
  height: 2rem;
  place-items: center;
  border: 1px solid var(--border-color);
  background: transparent;
  color: var(--text-secondary);
  font-size: 1.1rem;
  cursor: pointer;
  transition: color 0.25s ease, border-color 0.25s ease, background 0.25s ease;
}

.cal-nav:hover {
  color: var(--text-title);
  border-color: var(--primary-btn-border);
  background: color-mix(in srgb, var(--primary-btn-border) 10%, transparent);
}

.cal-nav:active {
  transform: translateY(1px);
}

.cal-weekdays {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 0;
  margin-bottom: 0.5rem;
}

.cal-weekdays span {
  text-align: center;
  color: var(--text-secondary);
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 0.3rem 0;
  transition: color 0.3s ease;
}

.cal-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 0.28rem;
}

.cal-day {
  position: relative;
  display: grid;
  min-width: 0;
  place-items: center;
  border: 1px solid transparent;
  aspect-ratio: 1;
  background: transparent;
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--text-primary);
  border-radius: 8px;
  cursor: pointer;
  outline: none;
  transition: color 0.2s ease, background 0.2s ease, border-color 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease;
}

.cal-day:hover,
.cal-day:focus-visible {
  color: var(--text-title);
  border-color: color-mix(in srgb, var(--primary-btn-border) 38%, transparent);
  background: color-mix(in srgb, var(--primary-btn-border) 9%, transparent);
}

.cal-day:active {
  transform: translateY(1px);
}

.cal-day-number {
  position: relative;
  z-index: 1;
}

.cal-day.is-other {
  color: var(--text-secondary);
  opacity: 0.48;
}

.cal-day.is-today {
  border-color: var(--primary-btn-border);
  background: color-mix(in srgb, var(--primary-btn-border) 16%, transparent);
  color: var(--text-title);
  font-weight: 800;
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--primary-btn-border) 45%, transparent);
}

.cal-day.is-selected {
  border-color: var(--text-title);
  background: var(--text-title);
  color: var(--surface);
  font-weight: 800;
  box-shadow: 0 14px 34px color-mix(in srgb, var(--text-title) 18%, transparent);
}

.theme-light .cal-day.is-selected {
  color: #f8f5f2;
}

.cal-day.is-selected.is-today {
  box-shadow:
    0 14px 34px color-mix(in srgb, var(--text-title) 18%, transparent),
    0 0 0 3px color-mix(in srgb, var(--primary-btn-border) 18%, transparent);
}

@keyframes cal-dot-pulse {
  0% {
    box-shadow: 0 0 0 0 color-mix(in srgb, var(--primary-btn-border) 68%, transparent);
  }
  70% {
    box-shadow: 0 0 0 4px transparent;
  }
  100% {
    box-shadow: 0 0 0 0 transparent;
  }
}

.cal-event-dot {
  position: absolute;
  bottom: 0.32rem;
  left: 50%;
  width: 0.28rem;
  height: 0.28rem;
  border-radius: 999px;
  background: var(--primary-btn-border);
  transform: translateX(-50%);
  box-shadow: 0 0 0 0 color-mix(in srgb, var(--primary-btn-border) 50%, transparent);
  animation: cal-dot-pulse 2s infinite;
}

.cal-day.is-selected .cal-event-dot {
  background: var(--surface);
}

.theme-light .cal-day.is-selected .cal-event-dot {
  background: #f8f5f2;
}

.calendar-modal-layer {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: grid;
  place-items: center;
  padding: clamp(1rem, 4vw, 2rem);
  background: rgb(5 5 8 / 0.58);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
}

.theme-light .calendar-modal-layer {
  background: rgba(26, 26, 26, 0.28);
}

.calendar-modal {
  position: relative;
  width: min(100%, 31rem);
  max-height: min(38rem, calc(100dvh - 2rem));
  overflow: auto;
  border: 1px solid color-mix(in srgb, var(--primary-btn-border) 26%, var(--border-color));
  background:
    linear-gradient(145deg, rgb(255 255 255 / 0.08), rgb(255 255 255 / 0.03)),
    var(--surface-card);
  box-shadow: 0 30px 90px rgb(0 0 0 / 0.42);
  padding: clamp(1.35rem, 4vw, 2rem);
  color: var(--text-primary);
}

.theme-light .calendar-modal {
  background:
    linear-gradient(145deg, rgba(255, 255, 255, 0.92), rgba(248, 245, 242, 0.82)),
    #f8f5f2;
  box-shadow: 0 30px 80px rgba(71, 58, 45, 0.22);
}

.calendar-modal-close {
  position: absolute;
  top: 0.9rem;
  right: 0.9rem;
  display: grid;
  width: 2.15rem;
  height: 2.15rem;
  place-items: center;
  border: 1px solid var(--border-color);
  background: transparent;
  color: var(--text-secondary);
  font-size: 1.35rem;
  line-height: 1;
  cursor: pointer;
  transition: color 0.2s ease, border-color 0.2s ease, background 0.2s ease;
}

.calendar-modal-close:hover,
.calendar-modal-close:focus-visible {
  color: var(--text-title);
  border-color: var(--primary-btn-border);
  background: color-mix(in srgb, var(--primary-btn-border) 9%, transparent);
}

.calendar-modal-kicker {
  color: var(--hero-kicker-color);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.calendar-modal h2 {
  margin-top: 0.55rem;
  padding-right: 2.6rem;
  color: var(--text-title);
  font-family: var(--font-serif), inherit;
  font-size: clamp(1.75rem, 4vw, 2.45rem);
  font-weight: 800;
  letter-spacing: 0;
  line-height: 1.15;
}

.calendar-event-form {
  display: grid;
  gap: 0.8rem;
  margin-top: 1.25rem;
  border: 1px solid var(--border-color);
  background: color-mix(in srgb, var(--surface-card) 58%, transparent);
  padding: 1rem;
}

.theme-light .calendar-event-form {
  background: rgba(255, 255, 255, 0.48);
}

.calendar-event-form label {
  display: grid;
  gap: 0.38rem;
}

.calendar-event-form label span {
  color: var(--text-secondary);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.calendar-form-fields { display: grid; gap: 0.8rem; min-width: 0; }

.calendar-form-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 0.75rem;
}

.calendar-event-form input,
.calendar-event-form select,
.calendar-event-form textarea {
  width: 100%;
  border: 1px solid var(--border-color);
  background: color-mix(in srgb, var(--surface) 72%, transparent);
  color: var(--text-primary);
  font: inherit;
  font-size: 0.88rem;
  outline: none;
  padding: 0.72rem 0.8rem;
  transition: border-color 0.2s ease, background 0.2s ease;
}

.theme-light .calendar-event-form input,
.theme-light .calendar-event-form select,
.theme-light .calendar-event-form textarea {
  background: rgba(255, 255, 255, 0.78);
}

.calendar-event-form textarea {
  resize: vertical;
}

.calendar-event-form input:focus,
.calendar-event-form select:focus,
.calendar-event-form textarea:focus {
  border-color: var(--primary-btn-border);
  background: color-mix(in srgb, var(--primary-btn-border) 8%, transparent);
}

.calendar-form-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.8rem;
}

.calendar-form-actions button,
.calendar-event-delete {
  border: 1px solid var(--primary-btn-border);
  background: transparent;
  color: var(--primary-btn-text);
  cursor: pointer;
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  padding: 0.62rem 0.9rem;
  transition: color 0.2s ease, border-color 0.2s ease, background 0.2s ease, transform 0.2s ease;
}

.calendar-form-actions button:hover,
.calendar-form-actions button:focus-visible {
  background: var(--primary-btn-sweep);
  color: var(--primary-btn-sweep-text);
}

.calendar-form-actions button:disabled,
.calendar-event-delete:disabled {
  cursor: wait;
  opacity: 0.55;
}

.calendar-form-actions button:active,
.calendar-event-delete:active {
  transform: translateY(1px);
}

.calendar-inline-status,
.calendar-form-error {
  font-size: 0.82rem;
}

.calendar-inline-status {
  margin-top: 0.8rem;
  color: var(--text-secondary);
}

.calendar-form-error {
  color: #fb7185;
}

.calendar-event-list {
  display: grid;
  gap: 0.8rem;
  margin-top: 1.35rem;
}

.calendar-event-item {
  position: relative;
  display: grid;
  grid-template-columns: 4rem 1fr auto;
  gap: 1rem;
  align-items: start;
  border: 1px solid var(--border-color);
  background: color-mix(in srgb, var(--project-accent, var(--primary-btn-border)) 8%, transparent);
  padding: 1rem;
}

.calendar-event-item time {
  color: var(--project-accent, var(--primary-btn-border));
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.08em;
}

.calendar-event-item h3 {
  color: var(--text-title);
  font-size: 0.98rem;
  font-weight: 800;
}

.calendar-event-item p {
  margin-top: 0.35rem;
  color: var(--text-secondary);
  font-size: 0.88rem;
  line-height: 1.65;
}

.calendar-event-delete {
  border-color: color-mix(in srgb, #fb7185 48%, var(--border-color));
  color: #fb7185;
  padding: 0.52rem 0.7rem;
}

.calendar-event-delete:hover,
.calendar-event-delete:focus-visible {
  background: rgb(251 113 133 / 0.12);
  border-color: #fb7185;
}

/* 事项色调：2026-10-06 随 tone 收敛为两值，已删除 .tone-plan / .tone-bill
   （对应枚举值已从后端与 DB 移除，留着就是死代码。决策见 docs/14 §4.1）。
   配色刻意保持**原有取值**，只删条目、不改色，避免视觉回归。 */

.calendar-event-item.tone-todo {
  --project-accent: #67e8f9;
}

.calendar-event-item.tone-meeting {
  --project-accent: #6ee7b7;
}

.theme-light .calendar-event-item.tone-todo {
  --project-accent: #0891b2;
}

.theme-light .calendar-event-item.tone-meeting {
  --project-accent: #059669;
}

.calendar-empty {
  margin-top: 1.35rem;
  border: 1px dashed var(--border-color);
  padding: 1.15rem;
}

.calendar-empty span {
  display: block;
  color: var(--text-title);
  font-weight: 800;
}

.calendar-empty p {
  margin-top: 0.5rem;
  color: var(--text-secondary);
  line-height: 1.7;
}

.calendar-modal-enter-active,
.calendar-modal-leave-active {
  transition: opacity 0.38s cubic-bezier(0.16, 1, 0.3, 1);
}

.calendar-modal-enter-active .calendar-modal {
  transition: transform 0.45s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.45s ease;
}

.calendar-modal-leave-active .calendar-modal {
  transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.25s ease;
}

.calendar-modal-enter-from,
.calendar-modal-leave-to {
  opacity: 0;
}

.calendar-modal-enter-from .calendar-modal {
  opacity: 0;
  transform: scale(0.94) translateY(12px);
}

.calendar-modal-leave-to .calendar-modal {
  opacity: 0;
  transform: scale(0.96) translateY(8px);
}

.section-block {
  padding: clamp(4rem, 8vw, 7rem) clamp(1.25rem, 5vw, 5rem);
}

.section-heading {
  display: grid;
  gap: 0.8rem;
  max-width: 46rem;
  margin-bottom: clamp(2rem, 5vw, 4rem);
}


.section-heading h2,
.about-content h2,
.newsletter-inner h2 {
  color: var(--text-title);
  font-family: var(--font-serif), inherit;
  font-size: clamp(2.3rem, 5vw, 4.5rem);
  font-weight: 800;
  letter-spacing: 0;
  line-height: 1;
  transition: color 0.3s ease;
}

.section-heading span {
  color: var(--text-secondary);
  line-height: 1.75;
  transition: color 0.3s ease;
}

.tone-cyan {
  --project-accent: #67e8f9;
  --project-glow: rgb(6 182 212 / 0.34);
}

.tone-violet {
  --project-accent: #a78bfa;
  --project-glow: rgb(124 58 237 / 0.35);
}

.tone-emerald {
  --project-accent: #6ee7b7;
  --project-glow: rgb(16 185 129 / 0.28);
}

.tone-amber {
  --project-accent: #fbbf24;
  --project-glow: rgb(245 158 11 / 0.28);
}

.tone-rose {
  --project-accent: #fb7185;
  --project-glow: rgb(244 63 94 / 0.28);
}

.tone-slate {
  --project-accent: #cbd5e1;
  --project-glow: rgb(148 163 184 / 0.22);
}


.outline-button {
  justify-self: start;
  border: 1px solid var(--outline-btn-border);
  padding: 0 1.4rem;
  color: var(--outline-btn-text);
  font-size: 0.82rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  background: transparent;
  --sweep-color: var(--outline-btn-sweep);
  --sweep-text-color: var(--outline-btn-sweep-text);
  min-height: 2.85rem;
}

.primary-button {
  background: linear-gradient(135deg, #7c3aed, #06b6d4) !important;
  color: #ffffff !important;
  border: none !important;
}

.primary-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 25px rgba(124, 58, 237, 0.35) !important;
}

/* User Avatar & Nav Link Active Indicator */
.user-avatar {
  display: grid;
  width: 2.2rem;
  height: 2.2rem;
  place-items: center;
  border-radius: 999px;
  background: linear-gradient(135deg, #7c3aed, #06b6d4);
  color: #ffffff;
  font-weight: 700;
  font-size: 0.85rem;
  box-shadow: 0 4px 12px rgba(124, 58, 237, 0.25);
  cursor: pointer;
  transition: transform 0.2s ease;
  margin-left: 0.5rem;
}
.user-avatar:hover {
  transform: scale(1.05);
}

.nav-links a.active::after {
  width: 100%;
  background: #a78bfa;
}

/* Hero Stats Row & Stat Glass Card */
.hero-stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  margin-top: 3rem;
}
.stat-glass-card {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  padding: 1rem;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.05);
  background: rgba(255, 255, 255, 0.02);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
  transition: transform 0.25s ease, border-color 0.25s ease;
}
.stat-glass-card:hover {
  transform: translateY(-2px);
  border-color: rgba(255, 255, 255, 0.12);
}
.stat-icon-wrapper {
  display: grid;
  width: 2.2rem;
  height: 2.2rem;
  place-items: center;
  border-radius: 12px;
  flex-shrink: 0;
}
.stat-icon-wrapper.cyan {
  background: rgba(6, 182, 212, 0.12);
  color: #06b6d4;
}
.stat-icon-wrapper.violet {
  background: rgba(124, 58, 237, 0.12);
  color: #a78bfa;
}
.stat-icon-wrapper.emerald {
  background: rgba(16, 185, 129, 0.12);
  color: #10b981;
}
.stat-data {
  display: flex;
  flex-direction: column;
}
.stat-num {
  font-size: 1.3rem;
  font-weight: 800;
  color: var(--text-title);
  line-height: 1.15;
}
.stat-desc {
  font-size: 0.62rem;
  color: var(--text-secondary);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  white-space: nowrap;
}

/* Hero Widgets Grid (2x2 Widget Cards Layout) */
.hero-widgets-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.2rem;
  width: 100%;
  align-items: stretch;
}
.widget-card {
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.04), rgba(255, 255, 255, 0.01));
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.2);
  padding: 1.25rem;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  display: flex;
  flex-direction: column;
  transition: transform 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease;
}
.widget-card:hover {
  border-color: rgba(103, 232, 249, 0.25);
  box-shadow: 0 25px 60px rgba(6, 182, 212, 0.08);
}
.widget-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}
.widget-title {
  font-size: 0.85rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: var(--text-title);
  opacity: 0.9;
}
.widget-meta {
  font-size: 0.72rem;
  color: var(--text-secondary);
}

/* Weather Widget Sub-styles */
.weather-main {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin: auto 0;
}
.weather-temp-block {
  display: flex;
  align-items: flex-start;
  color: var(--text-title);
}
.weather-temp-icon {
  font-size: 1.8rem;
  margin-right: 0.3rem;
}
.weather-temp-num {
  font-size: 2.2rem;
  font-weight: 800;
  line-height: 0.9;
}
.weather-temp-unit {
  font-size: 0.95rem;
  font-weight: 600;
  margin-top: 0.1rem;
}
.weather-info-block {
  display: flex;
  flex-direction: column;
}
.weather-status {
  font-size: 0.9rem;
  font-weight: 700;
  color: var(--text-title);
}
.weather-details {
  font-size: 0.68rem;
  color: var(--text-secondary);
  margin-top: 0.1rem;
}
.weather-error {
  margin: 0.65rem 0 0;
  color: #fbbf24;
  font-size: 0.68rem;
  line-height: 1.4;
}
.weather-forecast {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 0.4rem;
  padding-top: 0.8rem;
  border-top: 1px solid rgba(255, 255, 255, 0.04);
  margin-top: auto;
}
.forecast-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}
.forecast-day {
  font-size: 0.62rem;
  color: var(--text-secondary);
  font-weight: 600;
}
.forecast-icon {
  font-size: 0.9rem;
  margin: 0.3rem 0;
}
.forecast-temp-range {
  font-size: 0.58rem;
  font-weight: 700;
  display: flex;
  gap: 0.2rem;
}
.forecast-temp-high {
  color: var(--text-primary);
}
.forecast-temp-low {
  color: var(--text-secondary);
  opacity: 0.6;
}

/* Calendar & Events Widget Sub-styles */
.cal-nav-wrapper {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}
.cal-title-small {
  font-size: 0.78rem;
  font-weight: 700;
  margin-right: 0.4rem;
  color: var(--text-title);
}
.cal-arrow {
  display: grid;
  width: 1.25rem;
  height: 1.25rem;
  place-items: center;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 0.85rem;
  line-height: 1;
}
.cal-arrow:hover {
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-title);
}
.today-schedule {
  margin-top: 1rem;
  padding-top: 0.8rem;
  border-top: 1px solid rgba(255, 255, 255, 0.04);
}
.schedule-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.6rem;
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-secondary);
}
.view-all-link {
  color: #a78bfa;
  text-transform: none;
  font-weight: 600;
  letter-spacing: 0;
}
.schedule-list {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}
.schedule-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.7rem;
}
.sch-time {
  font-family: var(--font-mono), monospace;
  color: var(--text-secondary);
  width: 2.2rem;
  flex-shrink: 0;
}
.sch-dot {
  width: 5px;
  height: 5px;
  border-radius: 99px;
  flex-shrink: 0;
}
.sch-dot.dot-todo { background-color: #06b6d4; }
.sch-dot.dot-meeting { background-color: #ec4899; }
/* .dot-plan 已随 tone 收敛删除（docs/14 §4.1） */

.schedule-empty {
  margin: 0.5rem 0 0;
  color: var(--text-secondary);
  font-size: 0.72rem;
  opacity: 0.7;
}
.sch-title {
  color: var(--text-primary);
  flex-grow: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sch-type {
  color: var(--text-secondary);
  font-size: 0.65rem;
  opacity: 0.6;
  flex-shrink: 0;
}

/* Focus Checklist Widget Sub-styles */
.focus-checklist {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  margin: auto 0;
  flex-grow: 1;
}
.focus-item {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  cursor: pointer;
  padding: 0.2rem 0;
}
.checkbox-circle {
  display: grid;
  width: 1.1rem;
  height: 1.1rem;
  place-items: center;
  border-radius: 999px;
  border: 1.5px solid rgba(255, 255, 255, 0.25);
  transition: all 0.2s ease;
  flex-shrink: 0;
}
.checkbox-circle.checked {
  background-color: #7c3aed;
  border-color: #7c3aed;
  box-shadow: 0 0 8px rgba(124, 58, 237, 0.35);
}
.focus-text {
  font-size: 0.75rem;
  color: var(--text-primary);
  transition: all 0.2s ease;
}
.focus-item.is-done .focus-text {
  color: var(--text-secondary);
  text-decoration: line-through;
  opacity: 0.55;
}

/* ---------- 2026-10-06 新增：本周待做卡片 ----------
   仅新增"卡片右侧 ＋ 按钮"与"事项的两行布局（标题 + 日期/类型/过期标记）"这两处样式。
   其余（勾选圆、进度条、卡片外观）沿用既有类，不重复定义。 */

/* 卡片头右侧的添加按钮。尺寸与视觉参照日历卡已有的 `.cal-arrow`，
   避免长出一个与全站不一致的新按钮样式。 */
.widget-add-btn {
  display: grid;
  width: 1.5rem;
  height: 1.5rem;
  place-items: center;
  border: 1px solid var(--border-color);
  border-radius: 0.5rem;
  background: rgb(255 255 255 / 0.04);
  color: var(--text-secondary);
  cursor: pointer;
  transition: border-color 0.3s ease, background 0.3s ease, color 0.3s ease;
}
.widget-add-btn:hover {
  border-color: var(--project-accent, #67e8f9);
  background: rgb(255 255 255 / 0.09);
  color: var(--text-title);
}
.widget-add-btn:focus-visible {
  outline: 2px solid var(--project-accent, #67e8f9);
  outline-offset: 2px;
}

/* 事项改为两行：上行标题，下行日期 + 类型 + 过期标记。
   原来只有一行标题，现在需要容纳元信息。 */
.focus-item {
  align-items: flex-start;
}
.focus-body {
  display: grid;
  gap: 0.15rem;
  min-width: 0; /* 允许长标题在 flex 容器里正常省略，而不是把卡片顶宽 */
  flex-grow: 1;
}
.focus-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.focus-meta {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.62rem;
  color: var(--text-secondary);
  opacity: 0.75;
}
.focus-date {
  font-family: var(--font-mono), monospace;
}
.focus-tone-tag,
.focus-overdue-tag {
  padding: 0.05rem 0.3rem;
  border-radius: 0.3rem;
  border: 1px solid transparent;
  font-size: 0.58rem;
}
.focus-tone-tag.tag-todo {
  border-color: rgb(6 182 212 / 0.4);
  color: #67e8f9;
}
.focus-tone-tag.tag-meeting {
  border-color: rgb(236 72 153 / 0.4);
  color: #f9a8d4;
}
/* 过期标记：只标记、不隐藏、不自动标灰（用户第 12 条）。
   标灰仅用于"手动清理（勾选完成）"的项，见上面 `.is-done` 规则。 */
.focus-overdue-tag {
  border-color: rgb(251 191 36 / 0.45);
  color: #fbbf24;
}

/* 「未安排」标记：该事项没有具体时间（极速录入的产物）。
   与「已过期」刻意用不同颜色——它是"待规划"，不是"欠账"。 */
.focus-unscheduled-tag {
  padding: 0.05rem 0.3rem;
  border-radius: 0.3rem;
  border: 1px solid rgb(148 163 184 / 0.4);
  color: var(--text-secondary);
  font-size: 0.58rem;
}

/* 分类计数行（2026-10-07 新增）。
   摘要只显示 3 条，被截掉的事项靠这行数字保持可见——
   没有它，列表截断就会变成新的"隐身"。 */
.pending-counts {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-bottom: 0.6rem;
}
.pending-count {
  padding: 0.1rem 0.4rem;
  border-radius: 0.35rem;
  border: 1px solid transparent;
  background: rgb(255 255 255 / 0.04);
  font-size: 0.62rem;
  color: var(--text-secondary);
}
.pending-count strong {
  font-weight: 800;
}
/* 过期最醒目：它代表需要处理的欠账 */
.pending-count.count-overdue {
  border-color: rgb(251 191 36 / 0.45);
  color: #fbbf24;
}
.pending-count.count-today {
  border-color: rgb(6 182 212 / 0.4);
  color: #67e8f9;
}
.pending-count.count-unscheduled {
  border-color: rgb(148 163 184 / 0.4);
}

/* 勾选请求进行中：降低不透明度，避免用户重复点击。 */
.focus-item.is-toggling {
  opacity: 0.55;
  pointer-events: none;
}

.focus-empty {
  margin: 0.5rem 0 0;
  color: var(--text-secondary);
  font-size: 0.72rem;
  opacity: 0.7;
}

/* 「查看全部」入口：打开全局待做抽屉（快捷键 Ctrl/Cmd+K 等效）。
   卡片是摘要，全量在抽屉里——这个入口是两者的连接点。 */
.focus-view-all {
  border: 0;
  background: transparent;
  color: var(--project-accent, #67e8f9);
  font: inherit;
  font-size: 0.68rem;
  font-weight: 700;
  cursor: pointer;
  padding: 0;
}
.focus-view-all:hover {
  text-decoration: underline;
}
.focus-view-all:focus-visible {
  outline: 2px solid var(--project-accent, #67e8f9);
  outline-offset: 2px;
  border-radius: 0.2rem;
}
.focus-progress-block {
  padding-top: 0.8rem;
  border-top: 1px solid rgba(255, 255, 255, 0.04);
  margin-top: auto;
}
.progress-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.68rem;
  color: var(--text-secondary);
  font-weight: 700;
  margin-bottom: 0.4rem;
}
.progress-bar-track {
  height: 5px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 99px;
  overflow: hidden;
}
.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #7c3aed, #06b6d4);
  border-radius: 99px;
  transition: width 0.4s ease;
}

/* Weekly Progress Widget Sub-styles (SVG Doughnut Chart) */
.progress-content {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 1.2rem;
  margin: auto 0;
  flex-grow: 1;
}
.donut-chart-container {
  position: relative;
  width: 5.2rem;
  height: 5.2rem;
  flex-shrink: 0;
}
.donut-chart {
  width: 100%;
  height: 100%;
}
.donut-ring {
  stroke: rgba(255, 255, 255, 0.06);
}
.donut-segment {
  transform: rotate(-90deg);
  transform-origin: 50% 50%;
  transition: stroke-dasharray 0.5s ease;
}
.donut-text {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}
.donut-percentage {
  font-size: 1.15rem;
  font-weight: 800;
  color: var(--text-title);
  line-height: 1;
}
.donut-label {
  font-size: 0.52rem;
  color: #10b981;
  font-weight: 700;
  margin-top: 0.15rem;
}
.stats-indicators {
  min-width: 10rem;
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  flex-grow: 1;
}
.stat-indicator-row {
  display: flex;
  align-items: center;
  font-size: 0.7rem;
  line-height: 1.2;
}
.indicator-marker {
  width: 0.95rem;
  font-weight: 800;
  font-size: 0.78rem;
  flex-shrink: 0;
}
.indicator-marker.check-mark { color: #34d399; }
.indicator-marker.code-mark { color: #a78bfa; }
.indicator-marker.doc-mark { color: #67e8f9; }
.indicator-label {
  color: var(--text-secondary);
  flex-grow: 1;
}
.indicator-value {
  font-weight: 700;
  color: var(--text-primary);
  font-family: var(--font-mono), monospace;
}
.progress-updated-time {
  font-size: 0.58rem;
  color: var(--text-secondary);
  opacity: 0.5;
  margin-top: 0.2rem;
  text-align: right;
}

/* Filter & Stats Bar (Below Project Heading) */
.filter-stats-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 2rem;
  padding: 0.75rem 1.1rem;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}
.stats-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
}
.pill-badge {
  font-size: 0.68rem;
  padding: 0.35rem 0.7rem;
  border-radius: 99px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
  color: var(--text-secondary);
}
.pill-badge strong {
  color: var(--text-title);
  margin: 0 0.15rem;
}
.pill-badge.active-pill { border-color: rgba(124, 58, 237, 0.24); background: rgba(124, 58, 237, 0.04); }
.pill-badge.reserve-pill { border-color: rgba(245, 158, 11, 0.24); background: rgba(245, 158, 11, 0.04); }
.pill-badge.waiting-pill { border-color: rgba(244, 63, 94, 0.24); background: rgba(244, 63, 94, 0.04); }

.filter-controls {
  display: flex;
  align-items: center;
  gap: 0.8rem;
}
.search-input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}
.search-icon {
  position: absolute;
  left: 0.75rem;
  color: var(--text-secondary);
  opacity: 0.7;
}
.search-box {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  padding: 0.38rem 0.8rem 0.38rem 2rem;
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 0.75rem;
  width: 14rem;
  outline: none;
  transition: border-color 0.2s ease, background 0.2s ease;
}
.search-box:focus {
  border-color: rgba(6, 182, 212, 0.4);
  background: rgba(255, 255, 255, 0.05);
}
.filter-select, .view-select {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  padding: 0.38rem 0.6rem;
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 0.75rem;
  outline: none;
  cursor: pointer;
}
.view-toggle {
  font-size: 0.72rem;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 0.3rem;
}

/* Redesigned Project Grid & Cards */
.project-grid-v2 {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1.25rem;
}
.project-grid-v2.is-list {
  grid-template-columns: 1fr;
}
.project-grid-v2.is-list .project-card-v2 {
  min-height: auto;
}
.project-card-v2:focus-visible {
  outline: 2px solid var(--primary-light);
  outline-offset: 4px;
}
.project-card-v2 {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  border-radius: 20px;
  border: 1px solid var(--card-border);
  background: var(--card-bg-gradient), var(--card-bg);
  box-shadow: var(--card-shadow);
  padding: 1.35rem;
  overflow: hidden;
  transition: transform 0.35s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.35s ease, box-shadow 0.35s ease;
  min-height: 18.5rem;
}
.project-card-v2::before {
  content: "";
  position: absolute;
  inset: 0;
  background: radial-gradient(
    200px circle at var(--mouse-x, 0) var(--mouse-y, 0),
    var(--project-glow),
    transparent 80%
  );
  opacity: 0;
  transition: opacity 0.3s ease;
  pointer-events: none;
  z-index: 1;
}
.project-card-v2:hover::before {
  opacity: 1;
}
.project-card-v2.is-clickable {
  cursor: pointer;
}
.project-card-v2:hover {
  transform: translateY(-0.45rem);
  border-color: var(--card-hover-border);
  box-shadow: 0 25px 60px rgba(0, 0, 0, 0.35);
}
.card-status-badge {
  position: absolute;
  top: 1.35rem;
  right: 1.35rem;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.65rem;
  font-weight: 700;
  padding: 0.25rem 0.55rem;
  border-radius: 99px;
  border: 1px solid rgba(255, 255, 255, 0.05);
  background: rgba(255, 255, 255, 0.03);
  color: var(--text-secondary);
  z-index: 2;
}
.status-indicator {
  width: 5px;
  height: 5px;
  border-radius: 99px;
}
.badge-cyan .status-indicator { background-color: #06b6d4; }
.badge-violet .status-indicator { background-color: #7c3aed; }
.badge-emerald .status-indicator { background-color: #10b981; }
.badge-amber .status-indicator { background-color: #f59e0b; }
.badge-rose .status-indicator { background-color: #f43f5e; }
.badge-slate .status-indicator { background-color: #94a3b8; }

/* Status pill border accent overrides */
.card-status-badge.badge-cyan { border-color: rgba(6, 182, 212, 0.25); color: #67e8f9; }
.card-status-badge.badge-violet { border-color: rgba(124, 58, 237, 0.25); color: #c084fc; }
.card-status-badge.badge-emerald { border-color: rgba(16, 185, 129, 0.25); color: #34d399; }
.card-status-badge.badge-amber { border-color: rgba(245, 158, 11, 0.25); color: #fbbf24; }
.card-status-badge.badge-rose { border-color: rgba(244, 63, 94, 0.25); color: #fda4af; }
.card-status-badge.badge-slate { border-color: rgba(148, 163, 184, 0.25); color: #cbd5e1; }

.card-main-content {
  display: flex;
  gap: 1rem;
  z-index: 2;
}
.project-circle-icon {
  display: grid;
  width: 2.85rem;
  height: 2.85rem;
  place-items: center;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.05);
  flex-shrink: 0;
}
.bg-circle-cyan { background: rgba(6, 182, 212, 0.08); color: #06b6d4; }
.bg-circle-violet { background: rgba(124, 58, 237, 0.08); color: #7c3aed; }
.bg-circle-emerald { background: rgba(16, 185, 129, 0.08); color: #10b981; }
.bg-circle-amber { background: rgba(245, 158, 11, 0.08); color: #f59e0b; }
.bg-circle-rose { background: rgba(244, 63, 94, 0.08); color: #f43f5e; }
.bg-circle-slate { background: rgba(148, 163, 184, 0.08); color: #64748b; }

.project-info-block {
  display: flex;
  flex-direction: column;
  flex-grow: 1;
  width: 0; /* allows text truncation if needed */
}
.project-kicker-row {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: var(--text-secondary);
  line-height: 1.2;
  margin-top: 0.2rem;
}
.project-kicker-lbl {
  opacity: 0.8;
}
.project-num-lbl {
  font-family: var(--font-mono), monospace;
  opacity: 0.4;
}
.project-title-v2 {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--text-title);
  margin: 0.35rem 0 0.5rem 0;
}
.project-desc-v2 {
  font-size: 0.75rem;
  color: var(--card-text);
  line-height: 1.65;
  margin-bottom: 0.95rem;
}

/* Progress bar for list card */
.project-progress-container {
  margin-bottom: 0.8rem;
}
.progress-label-v2 {
  display: flex;
  justify-content: space-between;
  font-size: 0.68rem;
  font-weight: 700;
  color: var(--text-secondary);
  margin-bottom: 0.25rem;
}
.progress-bar-v2 {
  height: 4px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 99px;
  overflow: hidden;
}
.progress-bar-fill-v2 {
  height: 100%;
  background: linear-gradient(90deg, #7c3aed, #06b6d4);
  border-radius: 99px;
}

/* Tags for Services */
.project-tags-container {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-bottom: 0.8rem;
}
.tag-pill {
  font-size: 0.62rem;
  font-weight: 700;
  padding: 0.2rem 0.5rem;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
  color: var(--text-secondary);
}

/* Grid metrics rows inside card */
.project-stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.5rem;
  padding: 0.7rem 0;
  border-top: 1px solid rgba(255, 255, 255, 0.04);
}
.project-stat-item {
  display: flex;
  flex-direction: column;
}
.stat-lbl {
  font-size: 0.58rem;
  font-weight: 600;
  color: var(--text-secondary);
  opacity: 0.6;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}
.stat-val {
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-top: 0.15rem;
  white-space: nowrap;
}

.card-footer-v2 {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 0.85rem;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  font-size: 0.68rem;
  font-weight: 700;
  color: var(--text-secondary);
  z-index: 2;
  margin-top: auto;
}
.footer-update-time {
  opacity: 0.6;
}
.footer-action-link {
  color: var(--project-accent);
  transition: transform 0.2s ease;
}
.project-card-v2:hover .footer-action-link {
  transform: translateX(3px);
}

/* Floating Action Button Stack (FAB) */
.floating-fab-container {
  position: fixed;
  bottom: 2rem;
  right: 2rem;
  display: flex;
  flex-direction: column-reverse;
  gap: 0.65rem;
  z-index: 50;
}
.fab-btn {
  display: grid;
  place-items: center;
  border-radius: 999px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
  cursor: pointer;
  border: 1px solid rgba(255, 255, 255, 0.08);
}
.main-fab {
  width: 3.2rem;
  height: 3.2rem;
  background: linear-gradient(135deg, #7c3aed, #06b6d4);
  color: #ffffff;
  font-size: 1.6rem;
  font-weight: 300;
  box-shadow: 0 10px 30px rgba(124, 58, 237, 0.3);
  border: none;
}
.sub-fab {
  width: 2.5rem;
  height: 2.5rem;
  background: #1e1e2a;
  color: var(--text-primary);
  font-size: 0.95rem;
  opacity: 0.85;
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.sub-fab:hover {
  opacity: 1;
  background: #252535;
}
.floating-fab-container:hover .sub-fab {
  transform: translateY(-2px);
}

/* Static preview pass: match the compact dark workspace mockup. */

.dashboard-nav {
  min-height: 5.5rem;
  padding: 1.25rem clamp(2rem, 4vw, 4.5rem);
  background: rgba(4, 8, 18, 0.82);
  border-bottom-color: rgba(148, 163, 184, 0.12);
  box-shadow: 0 14px 50px rgba(0, 0, 0, 0.18);
}

.brand-mark {
  gap: 1.05rem;
}

.brand-letter {
  width: 3rem;
  height: 3rem;
  border-color: rgba(103, 232, 249, 0.32);
  border-radius: 0.55rem;
  background:
    linear-gradient(145deg, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.72)),
    radial-gradient(circle at 35% 18%, rgba(124, 58, 237, 0.55), transparent 58%);
  box-shadow: 0 0 24px rgba(124, 58, 237, 0.24);
  font-size: 1.45rem;
}

.brand-mark strong {
  font-size: 1.02rem;
  letter-spacing: 0.12em;
}

.brand-mark small {
  margin-top: 0.18rem;
  color: #9aa7bd;
  font-size: 0.78rem;
}

.nav-links {
  gap: clamp(1.6rem, 2.6vw, 2.8rem);
  color: #a7b2c7;
  font-size: 0.9rem;
  font-weight: 650;
  letter-spacing: 0;
  text-transform: none;
}

.nav-links a.active {
  color: #f8fafc;
}

.nav-links a::after {
  bottom: -0.7rem;
  height: 0.15rem;
  border-radius: 999px;
  background: linear-gradient(90deg, #8b5cf6, #a78bfa);
}

.nav-action {
  width: 2.65rem;
  height: 2.65rem;
  padding: 0;
  border-color: rgba(148, 163, 184, 0.22);
  border-radius: 0.55rem;
  background: rgba(15, 23, 42, 0.66);
}

.user-avatar {
  width: 2.35rem;
  height: 2.35rem;
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: linear-gradient(135deg, #4752ff, #7c3aed);
}

.hero-panel {
  min-height: calc(100dvh - 5.5rem);
  grid-template-columns: minmax(0, 0.85fr) minmax(0, 1.15fr);
  gap: clamp(2rem, 3.2vw, 4rem);
  align-items: start;
  padding: clamp(1.2rem, 2.2vw, 2rem) clamp(2.4rem, 5vw, 5.4rem) clamp(2.5rem, 4vw, 3.8rem);
}

.hero-panel::before {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    radial-gradient(circle at 23% 38%, rgba(124, 58, 237, 0.2), transparent 26rem),
    radial-gradient(circle at 78% 45%, rgba(6, 182, 212, 0.12), transparent 24rem);
  z-index: 0;
}

.hero-panel::after {
  content: "";
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  height: 31%;
  pointer-events: none;
  background:
    radial-gradient(ellipse at 45% 100%, rgba(124, 58, 237, 0.32), transparent 52%),
    radial-gradient(ellipse at 70% 95%, rgba(6, 182, 212, 0.2), transparent 48%);
  mask-image: linear-gradient(to top, black 0%, rgba(0, 0, 0, 0.72) 44%, transparent 100%);
  opacity: 0.78;
  transform: perspective(720px) rotateX(58deg) translateY(35%);
  transform-origin: bottom;
  z-index: 0;
}

.hero-backdrop {
  z-index: 0;
  opacity: 0.85;
}

.hero-content,
.hero-widgets-grid {
  position: relative;
  z-index: 1;
}

.hero-content {
  min-width: 0;
  align-self: start;
  padding-top: clamp(5.9rem, 10vh, 8.4rem);
}

.hero-kicker {
  display: inline-flex;
  width: auto;
  padding: 0.52rem 1.05rem;
  border: 1px solid rgba(124, 58, 237, 0.32);
  border-radius: 999px;
  background: rgba(67, 56, 202, 0.18);
  color: #67e8f9;
  font-size: 0.86rem;
  font-weight: 800;
  letter-spacing: 0.08em;
}

.hero-title {
  max-width: none;
  margin-top: 1.45rem;
  color: #ffffff;
  font-size: clamp(3.3rem, 5.2vw, 6.9rem);
  font-weight: 900;
  letter-spacing: 0;
  line-height: 0.98;
  white-space: nowrap;
  text-shadow: 0 18px 70px rgba(124, 58, 237, 0.18);
}

.hero-copy {
  max-width: 46rem;
  margin-top: 1.65rem;
  color: #a8b3cc;
  font-size: clamp(1.04rem, 1.32vw, 1.24rem);
  line-height: 1.72;
}

.hero-actions {
  gap: 1.4rem;
  margin-top: 2.35rem;
}

.primary-button,
.outline-button {
  min-height: 3.5rem;
  padding: 0 1.85rem;
  border-radius: 0.55rem;
  font-size: 0.93rem;
  letter-spacing: 0.02em;
  text-transform: none;
}

.primary-button {
  background: linear-gradient(135deg, #5b7cfa 0%, #8b35f6 100%) !important;
  box-shadow: 0 16px 40px rgba(91, 124, 250, 0.28) !important;
}

.outline-button {
  border-color: rgba(148, 163, 184, 0.35);
  background: rgba(15, 23, 42, 0.25);
  color: #f8fafc;
}

.hero-stats-row {
  max-width: 51rem;
  margin-top: clamp(7.4rem, 15vh, 10.2rem);
  gap: 1.2rem;
}

.stat-glass-card {
  min-height: 5.25rem;
  border-color: rgba(148, 163, 184, 0.15);
  border-radius: 0.9rem;
  background: rgba(15, 23, 42, 0.42);
  box-shadow: 0 16px 42px rgba(0, 0, 0, 0.22);
}

.stat-icon-wrapper {
  width: 3rem;
  height: 3rem;
  border: 1px solid currentColor;
  border-radius: 0.65rem;
}

.stat-num {
  font-size: 1.62rem;
}

.stat-desc {
  margin-top: 0.18rem;
  color: #9aa7bd;
  font-size: 0.75rem;
  letter-spacing: 0;
  text-transform: none;
}

.hero-widgets-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  grid-template-rows: minmax(26rem, auto) minmax(15rem, auto);
  gap: 1rem;
  align-self: start;
  height: auto;
  margin-top: clamp(1.2rem, 2vw, 1.8rem);
}

.widget-card {
  border-color: rgba(148, 163, 184, 0.24);
  border-radius: 0.75rem;
  background:
    linear-gradient(145deg, rgba(30, 41, 59, 0.74), rgba(15, 23, 42, 0.45)),
    radial-gradient(circle at 15% 0%, rgba(124, 58, 237, 0.15), transparent 48%);
  box-shadow: 0 20px 70px rgba(0, 0, 0, 0.34);
  padding: 1.42rem 1.45rem;
}

.widget-header {
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.widget-title {
  color: #f8fafc;
  font-size: 1.05rem;
  letter-spacing: 0;
}

.widget-meta {
  color: #9aa7bd;
  font-size: 0.82rem;
}

.weather-main {
  align-items: center;
  margin: 2.2rem 0 1.9rem;
}

.weather-temp-icon {
  font-size: 2.55rem;
}

.weather-temp-num {
  font-size: 3.35rem;
}

.weather-temp-unit {
  margin-top: 0.35rem;
  font-size: 1.35rem;
}

.weather-status {
  font-size: 1rem;
}

.weather-details {
  font-size: 0.82rem;
}

.weather-forecast {
  gap: 0.65rem;
  padding-top: 1rem;
  border-top-color: rgba(148, 163, 184, 0.12);
}

.forecast-day,
.forecast-temp-range {
  font-size: 0.78rem;
}

.forecast-icon {
  font-size: 1.25rem;
}

.weather-widget {
  position: relative;
  isolation: isolate;
  overflow: hidden;
}

.weather-widget::before {
  position: absolute;
  inset: -6rem -3rem auto auto;
  z-index: -1;
  width: 15rem;
  height: 15rem;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(251, 191, 36, 0.12), rgba(251, 191, 36, 0) 68%);
  content: '';
  pointer-events: none;
}

.weather-main {
  flex-wrap: wrap;
  gap: 1.35rem;
  margin: 1.35rem 0 1.2rem;
}

.weather-temp-block {
  min-width: 10.6rem;
  color: #f8fafc;
}

.weather-widget .weather-status,
.weather-widget .forecast-temp-high {
  color: #f8fafc;
}

.weather-widget .weather-details,
.weather-widget .forecast-day,
.weather-widget .forecast-temp-low {
  color: #aebbd0;
}

.weather-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  padding: 0.85rem 0;
  border-top: 1px solid rgba(148, 163, 184, 0.14);
  border-bottom: 1px solid rgba(148, 163, 184, 0.14);
}

.weather-metric {
  display: grid;
  gap: 0.28rem;
  min-width: 0;
  padding: 0 0.75rem;
}

.weather-metric:first-child {
  padding-left: 0;
}

.weather-metric + .weather-metric {
  border-left: 1px solid rgba(148, 163, 184, 0.13);
}

.weather-metric-label {
  color: #8c99af;
  font-size: 0.66rem;
  font-weight: 650;
}

.weather-metric-value {
  overflow: hidden;
  color: #eaf1fa;
  font-size: 0.79rem;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.weather-footer {
  display: flex;
  justify-content: space-between;
  gap: 0.8rem;
  margin-top: 0.75rem;
  color: #7e8ba2;
  font-size: 0.64rem;
}

@media (max-width: 640px) {
  .weather-metric {
    padding: 0 0.45rem;
  }

  .weather-temp-block {
    min-width: 0;
  }
}

.calendar-widget .cal-weekdays span {
  padding: 0.28rem 0;
  color: #8c99af;
  font-size: 0.76rem;
}

.calendar-widget .cal-grid {
  gap: 0.28rem 0.34rem;
}

.calendar-widget .cal-day {
  min-height: 0;
  height: 2.08rem;
  aspect-ratio: auto;
  border-radius: 0.48rem;
  color: #e5edf8;
  font-size: 0.82rem;
}

.calendar-widget .cal-day.is-other {
  color: #68768c;
  opacity: 0.72;
}

.calendar-widget .cal-day.is-today,
.calendar-widget .cal-day.is-selected {
  border-color: rgba(139, 92, 246, 0.78);
  background: linear-gradient(135deg, #5867ff, #8b3df4);
  color: #ffffff;
  box-shadow: 0 10px 24px rgba(124, 58, 237, 0.36);
}

.today-schedule {
  margin-top: 1.02rem;
  padding-top: 1rem;
  border-top-color: rgba(148, 163, 184, 0.13);
}

.schedule-header {
  color: #d7deea;
  font-size: 0.78rem;
  letter-spacing: 0;
  text-transform: none;
}

.schedule-item {
  min-height: 1.55rem;
  font-size: 0.78rem;
}

.sch-time {
  width: 3rem;
}

.focus-widget,
.progress-widget {
  min-height: 0;
}

.focus-checklist {
  gap: 0.9rem;
}

.focus-text {
  color: #dbe4f0;
  font-size: 0.9rem;
}

.focus-progress-block {
  border-top-color: rgba(148, 163, 184, 0.12);
}

.progress-content {
  gap: 1.7rem;
}

.donut-chart-container {
  width: 7rem;
  height: 7rem;
}

.donut-percentage {
  font-size: 1.4rem;
  letter-spacing: -0.02em;
}

.donut-label {
  font-size: 0.72rem;
}

.stat-indicator-row {
  font-size: 0.86rem;
}

.indicator-value {
  color: #f8fafc;
}

.progress-updated-time {
  font-size: 0.72rem;
}

.floating-fab-container {
  right: 1.55rem;
  bottom: 6.2rem;
}

.section-block {
  position: relative;
  z-index: 1;
}

#projects {
  padding-top: clamp(3.8rem, 6vw, 5rem);
}

/* Scroll and load animations */
.reveal-item {
  opacity: 0;
  transform: translateY(20px);
  transition: opacity 0.6s cubic-bezier(0.25, 1, 0.5, 1), transform 0.6s cubic-bezier(0.25, 1, 0.5, 1);
}

.reveal-item.revealed {
  opacity: 1;
  transform: translateY(0);
}

@keyframes fadeIn {
  from {
    opacity: 1;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.fade-in {
  opacity: 1;
  animation: fadeIn 0.62s cubic-bezier(0.25, 1, 0.5, 1) both;
}

.delay-1 {
  animation-delay: 0.15s;
}

.delay-2 {
  animation-delay: 0.3s;
}

.delay-3 {
  animation-delay: 0.45s;
}

.delay-4 {
  animation-delay: 0.6s;
}


@media (max-width: 1200px) {
  .hero-panel,
  .about-section {
    grid-template-columns: 1fr;
  }

  .hero-content {
    padding-top: 3rem;
  }

  .hero-title {
    max-width: 13ch;
    white-space: normal;
  }

  .hero-widgets-grid {
    grid-template-columns: repeat(2, 1fr);
    max-width: 100%;
    grid-template-rows: auto;
    height: auto;
    margin-top: 2rem;
  }

  .project-grid-v2 {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

}

@media (max-width: 720px) {
  .dashboard-nav {
    align-items: flex-start;
    flex-direction: column;
  }

  .nav-links {
    flex-wrap: wrap;
    width: 100%;
    justify-content: space-between;
    gap: 0.75rem;
  }

  .hero-panel {
    padding: 2rem 1.25rem;
  }

  .hero-widgets-grid {
    grid-template-columns: 1fr;
  }

  .hero-stats-row {
    margin-top: 2rem;
    grid-template-columns: 1fr;
    gap: 0.8rem;
  }

  .filter-controls { flex-wrap: wrap; width: 100%; }
  .search-input-wrapper { width: 100%; }
  .search-box { width: 100%; min-width: 0; }
  .widget-card { min-width: 0; padding: 1rem; }
  .weather-temp-block { min-width: 0; }
  .hero-widgets-grid { grid-template-rows: auto; }

  .project-grid-v2,
  .journal-grid {
    grid-template-columns: 1fr;
  }

  .calendar-form-row,
  .calendar-event-item {
    grid-template-columns: 1fr;
  }

  .calendar-form-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .calendar-event-delete {
    justify-self: start;
  }

  .project-card-v2 {
    min-height: 20rem;
  }


}

@media (prefers-reduced-motion: reduce) {
  .project-card-v2,
  .primary-button,
  .reveal-item {
    animation: none;
    transition: none;
  }
}
/* ---- 主题切换按钮（用户 2026-09-20 要求） ----
   按钮视觉上与 .nav-links a 保持一致；它不切换主题，只弹一条"功能待开发"提示。
   提示的样式已移到全站共享的 AppToast.vue（位置、圆角、阴影、进度条都在那里）——
   原先这里有 40 余行 .theme-toast 规则，与作废提示各写一份，现已合并。 */
.theme-toggle {
  display: inline-grid;
  place-items: center;
  width: 2.1rem;
  height: 2.1rem;
  border: 1px solid var(--nav-link-hover-border);
  border-radius: 999px;
  color: var(--text);
  font-size: 0.95rem;
  line-height: 1;
  background: rgb(255 255 255 / 0.04);
  cursor: pointer;
  transition: border-color 0.3s ease, background 0.3s ease, transform 0.2s ease;
}

.theme-toggle:hover {
  border-color: var(--project-accent, #67e8f9);
  background: rgb(255 255 255 / 0.09);
}
</style>
