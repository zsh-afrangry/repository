<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useScrollReveal } from '@/composables/useScrollReveal'

/* Calendar logic */
const now = new Date()
const calendarYear = ref(now.getFullYear())
const calendarMonth = ref(now.getMonth()) // 0-indexed
const selectedDate = ref(new Date(now.getFullYear(), now.getMonth(), now.getDate()))
const activeDate = ref<Date | null>(null)
const isCalendarModalOpen = ref(false)

type CalendarEventTone = 'todo' | 'plan' | 'meeting' | 'bill'

type CalendarEvent = {
  id: number
  event_date: string
  event_time: string | null
  time?: string
  title: string
  detail: string | null
  tone: CalendarEventTone
}

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

function padDatePart(value: number) {
  return String(value).padStart(2, '0')
}

function dateToKey(date: Date) {
  return `${date.getFullYear()}-${padDatePart(date.getMonth() + 1)}-${padDatePart(date.getDate())}`
}

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

async function apiFetch(path: string, init?: RequestInit) {
  const res = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? `HTTP ${res.status}`)
  }
  if (res.status === 204) return null
  return res.json()
}

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
  const { dateFrom, dateTo } = getVisibleCalendarRange()
  isCalendarLoading.value = true
  calendarLoadError.value = ''
  try {
    const events: CalendarEvent[] = await apiFetch(`/calendar-events/?date_from=${dateFrom}&date_to=${dateTo}`)
    calendarEvents.value = groupCalendarEvents(events)
  } catch (error) {
    console.error(error)
    calendarLoadError.value = error instanceof Error ? error.message : '日历事项加载失败。'
  } finally {
    isCalendarLoading.value = false
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

function closeCalendarModal() {
  isCalendarModalOpen.value = false
  eventFormError.value = ''
}

function handleCalendarKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && isCalendarModalOpen.value) {
    closeCalendarModal()
  }
}

function resetEventForm() {
  newEventTime.value = '09:00'
  newEventTitle.value = ''
  newEventDetail.value = ''
  newEventTone.value = 'todo'
  eventFormError.value = ''
}

async function addCalendarEvent() {
  if (!activeDate.value) return
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
    const savedEvent: CalendarEvent = await apiFetch('/calendar-events/', {
      method: 'POST',
      body: JSON.stringify({
        event_date: dateKey,
        event_time: newEventTime.value || null,
        title,
        detail: detail || null,
        tone: newEventTone.value,
      }),
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
  if (!activeDate.value) return
  const dateKey = dateToKey(activeDate.value)
  deletingEventId.value = eventId
  try {
    await apiFetch(`/calendar-events/${eventId}`, { method: 'DELETE' })
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
    name: 'KnowledgeMap',
    desc: '个人项目入口与知识关系视图，作为门户持续扩展。',
    label: 'PORTAL',
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
    status: '可进入',
    route: null,
    tone: 'slate',
    idCode: '06',
    stats: [
      { label: '文档数', value: '156' },
      { label: '最近更新', value: '今天 09:42' },
      { label: '成员协作', value: '6 人' }
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

type WeatherForecast = {
  day: string
  icon: string
  tempHigh: number
  tempLow: number
}

type WeatherInfo = {
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

const weatherInfo = ref<WeatherInfo>({
  location: '广东省 · 广州市 · 天河区',
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

async function loadWeather() {
  weatherLoadError.value = ''
  try {
    weatherInfo.value = await apiFetch('/weather/') as WeatherInfo
  } catch (error) {
    console.error(error)
    weatherLoadError.value = error instanceof Error ? error.message : '天气数据加载失败。'
  }
}

function formatWeatherUpdatedAt(value?: string | null) {
  if (!value) return '刚刚'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '刚刚'
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

/* Focus Tasks */
interface FocusTask {
  id: number
  text: string
  done: boolean
}
const focusTasks = ref<FocusTask[]>([
  { id: 1, text: '完善 KnowledgeMap 用户权限模块', done: false },
  { id: 2, text: '整理 AutoML 实验结果', done: true },
  { id: 3, text: '更新项目文档与里程碑', done: false }
])

function toggleFocusTask(task: FocusTask) {
  task.done = !task.done
}

const completedFocusCount = computed(() => focusTasks.value.filter(t => t.done).length)

/* Weekly Progress */
const weeklyProgress = ref({
  ratio: 72,
  tasks: { done: 18, total: 25 },
  commits: { done: 124, total: 160 },
  docs: { done: 6, total: 10 },
  updatedTime: '10:30'
})

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

function scrollToSection(id: string) {
  const target = document.querySelector<HTMLElement>(id)
  target?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function updateThemeClass() {
  if (isDark.value) {
    document.documentElement.classList.remove('theme-light')
  } else {
    document.documentElement.classList.add('theme-light')
  }
}

function toggleTheme() {
  isDark.value = !isDark.value
  localStorage.setItem('theme', isDark.value ? 'dark' : 'light')
  updateThemeClass()
}

onMounted(() => {
  const savedTheme = localStorage.getItem('theme')
  if (savedTheme) {
    isDark.value = savedTheme === 'dark'
  } else {
    isDark.value = !window.matchMedia('(prefers-color-scheme: light)').matches
  }
  updateThemeClass()
  window.addEventListener('keydown', handleCalendarKeydown)
  loadCalendarEvents()
  loadWeather()
  useScrollReveal()

  // Initialize and run constellation background
  window.addEventListener('resize', resizeBgCanvas)
  resizeBgCanvas()
  animateBgConstellation()
})

watch([calendarYear, calendarMonth], () => {
  loadCalendarEvents()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleCalendarKeydown)
  window.removeEventListener('resize', resizeBgCanvas)
  cancelAnimationFrame(canvasAnimationId)
})
</script>

<template>
  <div class="dashboard-shell">
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
        <a href="#notes" @click.prevent="router.push('/notes')">知识图谱</a>
        <a href="#lab" @click.prevent="void(0)">实验室</a>
        <a href="#docs" @click.prevent="void(0)">文档库</a>
        <a href="#about" @click.prevent="scrollToSection('#about')">关于我</a>
        <button type="button" class="nav-action theme-toggle-btn" @click="toggleTheme" aria-label="Toggle theme">
          <span class="theme-icon" style="font-size: 1.1rem; line-height: 1;">{{ isDark ? '☾' : '☼' }}</span>
        </button>
        <div class="user-avatar" aria-label="User Profile">K</div>
      </nav>
    </header>

    <main id="top">
      <section class="hero-panel">
        <div class="hero-backdrop" aria-hidden="true" @mousemove="handleCanvasMouseMove" @mouseleave="handleCanvasMouseLeave">
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
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                </svg>
              </div>
              <div class="stat-data">
                <div class="stat-num">18</div>
                <div class="stat-desc">活跃项目</div>
              </div>
            </div>
            <div class="stat-glass-card">
              <div class="stat-icon-wrapper violet">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <div class="stat-data">
                <div class="stat-num">236</div>
                <div class="stat-desc">笔记与文档</div>
              </div>
            </div>
            <div class="stat-glass-card">
              <div class="stat-icon-wrapper emerald">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                </svg>
              </div>
              <div class="stat-data">
                <div class="stat-num">1,248</div>
                <div class="stat-desc">代码提交（本月）</div>
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
                <span class="location-pin">📍</span> {{ weatherInfo.location }}
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
                <button type="button" class="cal-arrow" @click="prevMonth">‹</button>
                <button type="button" class="cal-arrow" @click="nextMonth">›</button>
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
                @click="selectCalendarDay(cell)"
              >
                <span class="cal-day-number">{{ cell.day }}</span>
                <span v-if="cell.hasEvents" class="cal-event-dot"></span>
              </button>
            </div>
            
            <!-- Today's Schedule -->
            <div class="today-schedule">
              <div class="schedule-header">
                <span>今日安排</span>
                <a href="#" class="view-all-link" @click.prevent="isCalendarModalOpen = true">查看全部</a>
              </div>
              <div class="schedule-list">
                <div class="schedule-item">
                  <span class="sch-time">10:00</span>
                  <span class="sch-dot dot-todo"></span>
                  <span class="sch-title">项目站会</span>
                  <span class="sch-type">线上会议</span>
                </div>
                <div class="schedule-item">
                  <span class="sch-time">14:00</span>
                  <span class="sch-dot dot-plan"></span>
                  <span class="sch-title">AutoML 模型评估</span>
                  <span class="sch-type">实验室任务</span>
                </div>
                <div class="schedule-item">
                  <span class="sch-time">16:30</span>
                  <span class="sch-dot dot-meeting"></span>
                  <span class="sch-title">阅读：向量数据库原理</span>
                  <span class="sch-type">个人学习</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Card 3: Today's Focus Checklist Widget -->
          <div class="widget-card focus-widget">
            <div class="widget-header">
              <span class="widget-title">今日重点</span>
            </div>
            <div class="focus-checklist">
              <div v-for="task in focusTasks" :key="task.id" 
                   class="focus-item" :class="{ 'is-done': task.done }"
                   @click="toggleFocusTask(task)">
                <div class="checkbox-circle" :class="{ 'checked': task.done }">
                  <svg v-if="task.done" class="w-2.5 h-2.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" style="display: block;">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <span class="focus-text">{{ task.text }}</span>
              </div>
            </div>
            <div class="focus-progress-block">
              <div class="progress-info">
                <span>{{ completedFocusCount }}/{{ focusTasks.length }} 完成</span>
              </div>
              <div class="progress-bar-track">
                <div class="progress-bar-fill" :style="{ width: `${(completedFocusCount / focusTasks.length) * 100}%` }"></div>
              </div>
            </div>
          </div>

          <!-- Card 4: Weekly Progress Widget -->
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
                    :stroke-dasharray="`${weeklyProgress.ratio}, 100`"
                  />
                  <defs>
                    <linearGradient id="progress-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stop-color="#7c3aed" />
                      <stop offset="100%" stop-color="#06b6d4" />
                    </linearGradient>
                  </defs>
                </svg>
                <div class="donut-text">
                  <span class="donut-percentage">{{ weeklyProgress.ratio }}%</span>
                  <span class="donut-label">进度良好 ▴</span>
                </div>
              </div>
              <div class="stats-indicators">
                <div class="stat-indicator-row">
                  <span class="indicator-marker check-mark">✓</span>
                  <span class="indicator-label">任务完成</span>
                  <span class="indicator-value">{{ weeklyProgress.tasks.done }} / {{ weeklyProgress.tasks.total }}</span>
                </div>
                <div class="stat-indicator-row">
                  <span class="indicator-marker code-mark">⌨</span>
                  <span class="indicator-label">代码提交</span>
                  <span class="indicator-value">{{ weeklyProgress.commits.done }} / {{ weeklyProgress.commits.total }}</span>
                </div>
                <div class="stat-indicator-row">
                  <span class="indicator-marker doc-mark">目</span>
                  <span class="indicator-label">文档更新</span>
                  <span class="indicator-value">{{ weeklyProgress.docs.done }} / {{ weeklyProgress.docs.total }}</span>
                </div>
                <div class="progress-updated-time">
                  数据更新于 {{ weeklyProgress.updatedTime }}
                </div>
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

        <div class="project-grid-v2">
          <article
            v-for="(project, index) in filteredProjects"
            :key="project.name"
            class="project-card-v2 reveal-item"
            :class="[`tone-${project.tone}`, { 'is-clickable': project.route }]"
            :style="{ transitionDelay: `${index * 60}ms` }"
            @click="handleCardClick(project.route)"
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
        <button type="button" class="fab-btn main-fab btn-tactile" aria-label="Add project">+</button>
        <button type="button" class="fab-btn sub-fab btn-tactile" aria-label="Dashboard views">⊞</button>
        <button type="button" class="fab-btn sub-fab btn-tactile" aria-label="Notifications">🔔</button>
        <button type="button" class="fab-btn sub-fab btn-tactile" aria-label="Quick launch">🚀</button>
      </div>

      <section id="journal" class="section-block journal-section">
        <div class="section-heading centered-heading reveal-item">
          <p>Art & Design</p>
          <h2>《星光咖啡馆与死神之蝶》</h2>
          <span>
            这一段照参考页的三栏展示节奏迁移：大图面、分类标签、标题、摘要和作者信息。
          </span>
        </div>

        <div class="journal-grid">
          <article
            v-for="(post, index) in [
              { title: '四季夏目天下第一！', desc: '四季夏目', category: 'Art & Design', tone: 'cyan', image: '/images/pic1.png' },
              { title: '明月栞那天下第一！', desc: '明月栞那', category: 'Travel', tone: 'violet', image: '/images/pic2.png' },
              { title: '墨染希天下第一！', desc: '墨染希', category: 'Lifestyle', tone: 'amber', image: '/images/pic3.png' },
            ]"
            :key="post.title"
            class="journal-card reveal-item"
            :class="`tone-${post.tone}`"
            :style="{ transitionDelay: `${index * 70}ms` }"
          >
            <div class="journal-image" aria-hidden="true">
              <img :src="post.image" :alt="post.title" class="journal-img-content" />
              <span>{{ String(index + 1).padStart(2, '0') }}</span>
            </div>
            <p class="journal-category">{{ post.category }}</p>
            <h3>{{ post.title }}</h3>
            <p class="journal-excerpt">{{ post.desc }}</p>
            <div class="journal-meta">
              <img src="/images/pic4.gif" alt="张斯涵" class="author-avatar" />
              <span>张斯涵</span>
              <span>2025</span>
            </div>
          </article>
        </div>
      </section>

      <section class="newsletter-band">
        <div class="newsletter-inner reveal-item">
          <h2>加入我们吧！</h2>
          <p>留下您的联系方式，与我们一同在 AI 时代赋能智慧医疗，用大模型帮助更多需要帮助的人们。</p>
          <form class="newsletter-form" @submit.prevent>
            <input type="email" placeholder="Your email address" aria-label="Email address" />
            <button type="submit">Subscribe</button>
          </form>
        </div>
      </section>

      <section id="about" class="section-block about-section">
        <div class="about-visual reveal-item" aria-hidden="true"></div>
        <div class="about-content reveal-item">
          <p>About the Author</p>
          <h2>张斯涵</h2>
          <span>
            Writer, photographer, and perpetual wanderer with a deep appreciation for quiet moments and meaningful conversations.
          </span>
          <span>
            After years in fast-paced creative industries, this section follows the reference layout as a quiet author panel.
          </span>
          <button type="button" class="outline-button">Read My Story</button>
        </div>
      </section>
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
            <div class="calendar-form-row">
              <label>
                <span>时间</span>
                <input v-model="newEventTime" type="time" aria-label="事项时间" />
              </label>
              <label>
                <span>类型</span>
                <select v-model="newEventTone" aria-label="事项类型">
                  <option value="todo">待办</option>
                  <option value="plan">计划</option>
                  <option value="meeting">会议</option>
                  <option value="bill">账单</option>
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
                :disabled="deletingEventId === event.id"
                @click="deleteCalendarEvent(event.id)"
              >
                {{ deletingEventId === event.id ? '删除中' : '删除' }}
              </button>
            </article>
          </div>
          <div v-else class="calendar-empty">
            <span>暂无安排</span>
            <p>这一天还没有 todolist、计划或会议记录，可以作为后续接入真实数据的空状态。</p>
          </div>
        </section>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.dashboard-shell {
  min-height: 100vh;
  background:
    radial-gradient(circle at 15% 10%, var(--bg-glow-1), transparent 26rem),
    radial-gradient(circle at 85% 30%, var(--bg-glow-2), transparent 24rem),
    var(--bg-gradient);
  background-image: var(--bg-image), radial-gradient(circle at 15% 10%, var(--bg-glow-1), transparent 26rem), radial-gradient(circle at 85% 30%, var(--bg-glow-2), transparent 24rem), var(--bg-gradient);
  background-size: var(--bg-image-size), auto, auto, auto;
  background-repeat: var(--bg-image-repeat), no-repeat, no-repeat, no-repeat;
  background-position: var(--bg-image-position), center center, center center, center center;
  background-attachment: fixed;
  color: var(--text-primary);
  font-family: var(--font-sans), sans-serif;
  transition: background 0.3s ease, color 0.3s ease, border-color 0.3s ease;
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

.calendar-event-item.tone-todo {
  --project-accent: #67e8f9;
}

.calendar-event-item.tone-plan {
  --project-accent: #a78bfa;
}

.calendar-event-item.tone-meeting {
  --project-accent: #6ee7b7;
}

.calendar-event-item.tone-bill {
  --project-accent: #fbbf24;
}

.theme-light .calendar-event-item.tone-todo {
  --project-accent: #0891b2;
}

.theme-light .calendar-event-item.tone-plan {
  --project-accent: #7c3aed;
}

.theme-light .calendar-event-item.tone-meeting {
  --project-accent: #059669;
}

.theme-light .calendar-event-item.tone-bill {
  --project-accent: #d97706;
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

.centered-heading {
  max-width: 48rem;
  margin-right: auto;
  margin-left: auto;
  text-align: center;
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

.project-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1.2rem;
}

.project-card {
  position: relative;
  min-height: 25rem;
  overflow: hidden;
  border: 1px solid var(--card-border);
  background: var(--card-bg-gradient), var(--card-bg);
  transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.35s ease, box-shadow 0.35s ease, background 0.3s ease;
}

.project-card::before {
  content: "";
  position: absolute;
  inset: 0;
  background: radial-gradient(
    220px circle at var(--mouse-x, 0) var(--mouse-y, 0),
    var(--project-glow),
    transparent 80%
  );
  opacity: 0;
  transition: opacity 0.3s ease;
  pointer-events: none;
  z-index: 1;
}

.project-card:hover::before {
  opacity: 1;
}

.project-media,
.project-body,
.project-footer {
  position: relative;
  z-index: 2;
}

.project-card.is-clickable {
  cursor: pointer;
}

.project-card:hover {
  border-color: var(--card-hover-border);
  box-shadow: var(--card-shadow);
  transform: translateY(-0.45rem);
}

.project-media {
  display: flex;
  min-height: 11rem;
  align-items: flex-start;
  justify-content: space-between;
  padding: 1.35rem;
  background:
    radial-gradient(circle at 28% 18%, var(--project-glow), transparent 58%),
    linear-gradient(135deg, var(--card-border), transparent);
  transition: background 0.3s ease;
}

.project-label,
.project-number,
.project-body p,
.project-footer {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.project-label,
.project-number {
  color: var(--text-primary);
  opacity: 0.82;
  transition: color 0.3s ease;
}

.project-body {
  padding: 1.5rem;
}

.project-body p {
  color: var(--project-accent);
  transition: color 0.3s ease;
}

.project-body h3 {
  margin-top: 0.75rem;
  color: var(--text-title);
  font-family: var(--font-serif), inherit;
  font-size: 1.9rem;
  font-weight: 800;
  transition: color 0.3s ease;
}

.project-body span {
  display: block;
  margin-top: 1rem;
  color: var(--card-text);
  line-height: 1.7;
  transition: color 0.3s ease;
}

.project-footer {
  position: absolute;
  right: 1.5rem;
  bottom: 1.35rem;
  left: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: var(--card-footer-text);
  transition: color 0.3s ease;
}

.project-arrow {
  color: var(--project-accent);
  font-size: 1.25rem;
  transform: translateX(-0.25rem);
  transition: transform 0.3s ease, color 0.3s ease;
}

.project-card:hover .project-arrow {
  transform: translateX(0.2rem);
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

.journal-section {
  border-top: 1px solid var(--border-color);
  transition: border-color 0.3s ease;
}

.journal-section .section-heading h2 {
  font-size: clamp(1.8rem, 4.2vw, 3.6rem);
}

.journal-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: clamp(1.4rem, 3vw, 3rem);
}

.journal-card {
  transition: transform 0.35s ease;
}

.journal-card:hover {
  transform: translateY(-0.4rem);
}

.journal-image {
  position: relative;
  height: clamp(18rem, 34vw, 26rem);
  margin-bottom: 1.5rem;
  overflow: hidden;
  border: 1px solid var(--card-border);
  background: var(--card-bg);
  filter: grayscale(18%);
  transition: filter 0.3s ease, transform 0.3s ease, border-color 0.3s ease, background 0.3s ease;
}

.journal-image::after {
  content: "";
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 28% 22%, var(--project-glow), transparent 54%);
  opacity: 0.65;
  pointer-events: none;
  z-index: 1;
  transition: opacity 0.3s ease;
}

.journal-card:hover .journal-image {
  filter: grayscale(0);
  transform: scale(1.015);
}

.journal-img-content {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  z-index: 0;
  transition: transform 0.4s ease;
}

.journal-card:hover .journal-img-content {
  transform: scale(1.045);
}

.journal-image span {
  position: absolute;
  top: 0;
  right: 0;
  padding: 1.1rem;
  color: var(--text-secondary);
  opacity: 0.7;
  font-size: 3rem;
  font-weight: 800;
  z-index: 2;
  transition: color 0.3s ease;
}

.journal-category,
.about-content p {
  color: var(--hero-kicker-color);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  transition: color 0.3s ease;
}

.journal-card h3 {
  margin-top: 0.45rem;
  color: var(--text-title);
  font-family: var(--font-serif), inherit;
  font-size: clamp(1.55rem, 2.2vw, 2rem);
  font-weight: 800;
  line-height: 1.25;
  transition: color 0.3s ease;
}

.journal-card:hover h3 {
  color: var(--project-accent);
}

.journal-excerpt {
  margin-top: 0.9rem;
  color: var(--text-secondary);
  transition: color 0.3s ease;
}

.journal-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.9rem;
  align-items: center;
  margin-top: 1.4rem;
  color: var(--text-secondary);
  font-size: 0.82rem;
  transition: color 0.3s ease;
}

.author-avatar {
  width: 1.8rem;
  height: 1.8rem;
  border: 1px solid var(--border-color);
  border-radius: 999px;
  object-fit: cover;
  transition: border-color 0.3s ease;
}

.newsletter-band {
  padding: clamp(4rem, 8vw, 7rem) clamp(1.25rem, 5vw, 5rem);
  background: var(--newsletter-bg);
  border-top: 1px solid var(--border-color);
  border-bottom: 1px solid var(--border-color);
  transition: background 0.3s ease, border-color 0.3s ease;
}

.newsletter-inner {
  max-width: 46rem;
  margin: 0 auto;
  text-align: center;
}

.newsletter-inner p {
  max-width: 40rem;
  margin: 1rem auto 2rem;
  color: var(--card-text);
  line-height: 1.8;
  transition: color 0.3s ease;
}

.newsletter-form {
  display: flex;
  max-width: 42rem;
  margin: 0 auto;
}

.newsletter-form input {
  min-width: 0;
  flex: 1;
  border: 1px solid var(--newsletter-input-border);
  background: var(--newsletter-input-bg);
  padding: 1rem 1.2rem;
  color: var(--text-primary);
  outline: none;
  transition: border-color 0.3s ease, background 0.3s ease, color 0.3s ease;
}

.newsletter-form input:focus {
  border-color: var(--primary-btn-border);
}

.newsletter-form button {
  border: 1px solid var(--primary-btn-border);
  background: transparent;
  color: var(--primary-btn-text);
  padding: 0 2rem;
  font-size: 0.8rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  position: relative;
  overflow: hidden;
  z-index: 1;
  transition: color 0.35s ease, border-color 0.35s ease;
  cursor: pointer;
}

.newsletter-form button::before {
  content: "";
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background-color: var(--primary-btn-sweep);
  transition: left 0.35s cubic-bezier(0.25, 0.1, 0.25, 1);
  z-index: -1;
}

.newsletter-form button:hover::before {
  left: 0;
}

.newsletter-form button:hover {
  color: var(--primary-btn-sweep-text);
}

.about-section {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 0.9fr);
  gap: clamp(2rem, 6vw, 5rem);
  align-items: center;
}

.about-visual {
  position: relative;
  min-height: clamp(28rem, 45vw, 38rem);
  border: 1px solid var(--card-border);
  background: url('/images/pic5.jpg') no-repeat center center;
  background-size: cover;
  transition: border-color 0.3s ease;
}

.about-visual::before {
  position: absolute;
  inset: -1.6rem 1.6rem 1.6rem -1.6rem;
  z-index: -1;
  border: 1px solid var(--primary-btn-border);
  content: "";
  transition: border-color 0.3s ease;
}

.about-content {
  display: grid;
  gap: 1.2rem;
}

.about-content span {
  color: var(--text-secondary);
  line-height: 1.85;
  transition: color 0.3s ease;
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
.sch-dot.dot-plan { background-color: #7c3aed; }
.sch-dot.dot-meeting { background-color: #ec4899; }
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
.dashboard-shell {
  min-height: 100dvh;
  overflow-x: hidden;
  background:
    radial-gradient(circle at 18% 28%, rgba(66, 82, 255, 0.22), transparent 32rem),
    radial-gradient(circle at 76% 18%, rgba(6, 182, 212, 0.11), transparent 28rem),
    linear-gradient(135deg, #070816 0%, #0a1122 48%, #07101d 100%);
}

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
  grid-template-columns: minmax(38rem, 0.96fr) minmax(48rem, 1.04fr);
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
    radial-gradient(ellipse at 70% 95%, rgba(6, 182, 212, 0.2), transparent 48%),
    repeating-linear-gradient(0deg, rgba(96, 165, 250, 0.13) 0 1px, transparent 1px 26px),
    repeating-linear-gradient(90deg, rgba(96, 165, 250, 0.12) 0 1px, transparent 1px 42px);
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
  font-size: clamp(4.55rem, 6.35vw, 6.9rem);
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
  grid-template-rows: minmax(26rem, 1.7fr) minmax(15rem, 0.9fr);
  gap: 1rem;
  align-self: start;
  height: min(43.5rem, calc(100dvh - 7.1rem));
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
  font-size: 1.85rem;
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


@media (max-width: 1024px) {
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
    height: auto;
    margin-top: 2rem;
  }

  .project-grid-v2 {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .journal-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .dashboard-nav {
    align-items: flex-start;
    flex-direction: column;
  }

  .nav-links {
    width: 100%;
    justify-content: space-between;
    gap: 0.75rem;
  }

  .hero-panel {
    padding-top: 3rem;
  }

  .hero-widgets-grid {
    grid-template-columns: 1fr;
  }

  .hero-stats-row {
    grid-template-columns: 1fr;
    gap: 0.8rem;
  }

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

  .newsletter-form {
    flex-direction: column;
  }

  .newsletter-form button {
    min-height: 3rem;
    padding: 1rem 0;
  }

  .about-visual::before {
    display: none;
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
</style>
