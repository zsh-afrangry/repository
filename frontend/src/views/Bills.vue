<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useDialogFocus } from '@/composables/useDialogFocus'
import DeepSpaceBackground from '@/components/DeepSpaceBackground.vue'
import AppNavbar from '@/components/AppNavbar.vue'
import { billsApi } from '@/api/bills'
import { tagsApi } from '@/api/tags'
import { todayKey } from '@/utils/date'
import type { BillItem, BillPayload, TagOut } from '@/types/portal'

// ---- Types ----
interface FinancialCalendarDay {
  day: number
  current: boolean
  today: boolean
  date: Date
  dateKey: string
  dateLabel: string
  weekDay: string
  items: BillItem[]
  totalExpense: number
  totalIncome: number
  netAmount: number
  hasPendingReimburse: boolean
  categoryIcons: string[]
  offset: -1 | 0 | 1
}

interface DayGroup {
  date: string
  dateLabel: string
  weekDay: string
  items: BillItem[]
  totalExpense: number
  totalIncome: number
}

// ---- State ----
const now = new Date()
const currentYear = ref(now.getFullYear())
const currentMonth = ref(now.getMonth() + 1)

const bills = ref<BillItem[]>([])
const loading = ref(false)
const loadError = ref('')
const tagError = ref('')
const formError = ref('')
const deleteError = ref('')
let loadVersion = 0
let disposed = false
const bootstrapping = ref(true)
const monthlySummary = ref({ income: 0, expense: 0, net: 0 })

// Calendar & Inspection selection state
const selectedDateKey = ref('')
const showFullStreamDrawer = ref(false)

// Stream Filters
const activeFilterTab = ref<'all' | 'expense' | 'income' | 'pending'>('all')
const selectedCategoryFilterId = ref<number | null>(null)
const searchQuery = ref('')
const collapsedDays = ref(new Set<string>())

// Tags
const categoryTags = ref<TagOut[]>([])
const platformTags = ref<TagOut[]>([])
const channelTags = ref<TagOut[]>([])
const fundTags = ref<TagOut[]>([])

// Modal
const showModal = ref(false)
const editingBill = ref<BillItem | null>(null)
const saving = ref(false)

const emptyForm = () => ({
  record_type: '支出' as '支出' | '收入',
  expense_date: todayKey(),
  expense_time: '',
  amount: '',
  category_id: null as number | null,
  subcategory_id: null as number | null,
  payment_platform_id: null as number | null,
  payment_channel_id: null as number | null,
  fund_type_id: null as number | null,
  reimbursement_status: '无需报销',
  note: '',
})

const form = ref(emptyForm())

// Delete confirm
const deleteTarget = ref<BillItem | null>(null)
const showDeleteConfirm = ref(false)
const deleting = ref(false)

// ---- API helpers ----
async function retryTags() {
  try { await loadTags() }
  catch (e) { tagError.value = (e as Error).message }
}

async function loadTags() {
  tagError.value = ''
  const [tree, all] = await Promise.all([tagsApi.tree(), tagsApi.all()])
  categoryTags.value = tree.filter(t => t.type === 'category')
  platformTags.value = all.filter(t => t.type === 'payment_platform')
  channelTags.value = all.filter(t => t.type === 'payment_channel')
  fundTags.value = all.filter(t => t.type === 'fund_type')
}

async function loadBills() {
  const version = ++loadVersion
  loading.value = true
  loadError.value = ''
  bills.value = []
  monthlySummary.value = { income: 0, expense: 0, net: 0 }
  try {
    const y = currentYear.value
    const m = currentMonth.value
    const dFrom = `${y}-${String(m).padStart(2, '0')}-01`
    const dTo = `${y}-${String(m).padStart(2, '0')}-${new Date(y, m, 0).getDate()}`
    const [items, summary] = await Promise.all([
      billsApi.listAllByRange(dFrom, dTo),
      billsApi.monthlySummary(y, m),
    ])
    if (disposed || version !== loadVersion) return
    bills.value = items
    monthlySummary.value = { income: summary.income, expense: summary.expense, net: summary.net }

    // Auto-select latest active date in this month if any
    if (items.length > 0) {
      selectedDateKey.value = items[0].expense_date
    } else {
      selectedDateKey.value = ''
    }
  } catch (e) {
    if (disposed || version !== loadVersion) return
    loadError.value = (e as Error).message
  } finally {
    if (!disposed && version === loadVersion) loading.value = false
  }
}

async function syncMonthToLatestBill() {
  try {
    const data = await billsApi.listLatest()
    const latestDate = data.items?.[0]?.expense_date
    if (!latestDate) return
    const [year, month] = latestDate.split('-').map(Number)
    if (year && month) {
      currentYear.value = year
      currentMonth.value = month
    }
  } catch (e) {
    console.error(e)
    loadError.value = (e as Error).message
  }
}

// Subcategories for form
const subcategoryOptions = computed<TagOut[]>(() => {
  if (!form.value.category_id) return []
  const cat = categoryTags.value.find(t => t.id === form.value.category_id)
  return cat?.children ?? []
})

watch(() => form.value.category_id, () => {
  if (!subcategoryOptions.value.some(tag => tag.id === form.value.subcategory_id)) {
    form.value.subcategory_id = null
  }
})

// Visual representation for category
function getCategoryVisual(name?: string, recordType: '支出' | '收入' = '支出') {
  if (recordType === '收入') {
    return {
      icon: '💰',
      badgeClass: 'bg-emerald-500/15 border-emerald-500/30 text-emerald-400',
      color: '#10b981',
    }
  }
  const n = name || ''
  if (/餐|食|饭|外卖|饮|吃|早|午|晚|奶茶|咖啡/.test(n)) {
    return { icon: '🍴', badgeClass: 'bg-amber-500/15 border-amber-500/30 text-amber-400', color: '#f59e0b' }
  }
  if (/行|交通|车|地铁|打车|公交|加油|机|铁/.test(n)) {
    return { icon: '🚗', badgeClass: 'bg-cyan-500/15 border-cyan-500/30 text-cyan-400', color: '#06b6d4' }
  }
  if (/购|买|服饰|鞋|衣|超|日用|商/.test(n)) {
    return { icon: '🛍️', badgeClass: 'bg-purple-500/15 border-purple-500/30 text-purple-400', color: '#a855f7' }
  }
  if (/玩|乐|娱|游|影|歌|会员/.test(n)) {
    return { icon: '🎮', badgeClass: 'bg-rose-500/15 border-rose-500/30 text-rose-400', color: '#f43f5e' }
  }
  if (/房|居|家|水|电|物业|燃气|网/.test(n)) {
    return { icon: '🏠', badgeClass: 'bg-teal-500/15 border-teal-500/30 text-teal-400', color: '#14b8a6' }
  }
  if (/医|药|看病|体检|齿|健/.test(n)) {
    return { icon: '💊', badgeClass: 'bg-red-500/15 border-red-500/30 text-red-400', color: '#ef4444' }
  }
  if (/学|书|课|培|考/.test(n)) {
    return { icon: '📚', badgeClass: 'bg-indigo-500/15 border-indigo-500/30 text-indigo-400', color: '#6366f1' }
  }
  if (/投|理财|股|基|险/.test(n)) {
    return { icon: '📈', badgeClass: 'bg-sky-500/15 border-sky-500/30 text-sky-400', color: '#0284c7' }
  }
  return { icon: '🏷️', badgeClass: 'bg-slate-500/15 border-slate-500/30 text-slate-400', color: '#94a3b8' }
}

// Map bills by date for quick calendar lookups
const billsByDateMap = computed(() => {
  const map = new Map<string, BillItem[]>()
  for (const b of bills.value) {
    const list = map.get(b.expense_date) ?? []
    list.push(b)
    map.set(b.expense_date, list)
  }
  return map
})

// Financial stats
const financialStats = computed(() => {
  const expenseBills = bills.value.filter(b => b.record_type === '支出')
  const incomeBills = bills.value.filter(b => b.record_type === '收入')
  const pendingBills = bills.value.filter(b => b.reimbursement_status === '待报销')
  const doneBills = bills.value.filter(b => b.reimbursement_status === '已报销')

  const pendingAmount = pendingBills.reduce((s, b) => s + parseFloat(b.amount || '0'), 0)
  const doneAmount = doneBills.reduce((s, b) => s + parseFloat(b.amount || '0'), 0)

  const y = currentYear.value
  const m = currentMonth.value
  const daysInMonth = new Date(y, m, 0).getDate()
  const isThisMonth = currentYear.value === now.getFullYear() && currentMonth.value === now.getMonth() + 1
  const daysElapsed = isThisMonth ? Math.max(1, Math.min(now.getDate(), daysInMonth)) : daysInMonth
  const dailyAverage = monthlySummary.value.expense > 0 ? monthlySummary.value.expense / daysElapsed : 0

  const catMap = new Map<number, { id: number; name: string; total: number }>()
  for (const b of expenseBills) {
    const catId = b.category_id ?? 0
    const catName = b.category?.name ?? '其他'
    const amt = parseFloat(b.amount || '0')
    const existing = catMap.get(catId) ?? { id: catId, name: catName, total: 0 }
    existing.total += amt
    catMap.set(catId, existing)
  }

  const categoryBreakdown = Array.from(catMap.values())
    .sort((a, b) => b.total - a.total)
    .map(c => ({
      ...c,
      percent: monthlySummary.value.expense > 0 ? Math.round((c.total / monthlySummary.value.expense) * 100) : 0,
      visual: getCategoryVisual(c.name, '支出'),
    }))

  return {
    expenseCount: expenseBills.length,
    incomeCount: incomeBills.length,
    pendingCount: pendingBills.length,
    pendingAmount,
    doneCount: doneBills.length,
    doneAmount,
    dailyAverage,
    activeDays: new Set(bills.value.map(b => b.expense_date)).size,
    categoryBreakdown,
  }
})

// Calendar Grid computation (7 columns: Mon -> Sun)
const calendarGridDays = computed<FinancialCalendarDay[]>(() => {
  const year = currentYear.value
  const month = currentMonth.value - 1
  const firstDay = new Date(year, month, 1)
  const lastDay = new Date(year, month + 1, 0)

  let startOffset = firstDay.getDay() - 1
  if (startOffset < 0) startOffset = 6

  const days: FinancialCalendarDay[] = []
  const todayStr = todayKey()
  const weekDays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']

  const buildDay = (d: Date, current: boolean, offset: -1 | 0 | 1): FinancialCalendarDay => {
    const yStr = d.getFullYear()
    const mStr = String(d.getMonth() + 1).padStart(2, '0')
    const dStr = String(d.getDate()).padStart(2, '0')
    const dateKey = `${yStr}-${mStr}-${dStr}`
    const dateLabel = `${mStr}/${dStr}`
    const rawItems = billsByDateMap.value.get(dateKey) ?? []
    const items = rawItems.slice().sort((a, b) => (b.expense_time ?? '').localeCompare(a.expense_time ?? ''))

    let totalExpense = 0
    let totalIncome = 0
    let hasPendingReimburse = false
    const catIconsSet = new Set<string>()

    for (const item of items) {
      const amt = parseFloat(item.amount || '0')
      if (item.record_type === '支出') {
        totalExpense += amt
      } else {
        totalIncome += amt
      }
      if (item.reimbursement_status === '待报销') {
        hasPendingReimburse = true
      }
      const vis = getCategoryVisual(item.category?.name, item.record_type)
      catIconsSet.add(vis.icon)
    }

    return {
      day: d.getDate(),
      current,
      today: dateKey === todayStr,
      date: d,
      dateKey,
      dateLabel,
      weekDay: weekDays[d.getDay()],
      items,
      totalExpense,
      totalIncome,
      netAmount: totalIncome - totalExpense,
      hasPendingReimburse,
      categoryIcons: Array.from(catIconsSet).slice(0, 3),
      offset,
    }
  }

  // Prev month padding
  for (let i = startOffset - 1; i >= 0; i--) {
    const d = new Date(year, month, -i)
    days.push(buildDay(d, false, -1))
  }

  // Current month days
  for (let i = 1; i <= lastDay.getDate(); i++) {
    const d = new Date(year, month, i)
    days.push(buildDay(d, true, 0))
  }

  // Next month padding to fill 35 or 42 cells
  const remaining = (7 - (days.length % 7)) % 7
  const targetTotal = days.length + remaining <= 35 ? 35 : 42
  const padNext = targetTotal - days.length
  for (let i = 1; i <= padNext; i++) {
    const d = new Date(year, month + 1, i)
    days.push(buildDay(d, false, 1))
  }

  return days
})

// Selected day details for side inspection
const selectedDay = computed<FinancialCalendarDay | null>(() => {
  if (!selectedDateKey.value) return null
  return calendarGridDays.value.find(d => d.dateKey === selectedDateKey.value) ?? null
})

// Toggle day selection (click on calendar cell)
function toggleDaySelection(cell: FinancialCalendarDay) {
  if (selectedDateKey.value === cell.dateKey) {
    selectedDateKey.value = ''
  } else {
    selectedDateKey.value = cell.dateKey
    if (cell.offset !== 0) {
      currentYear.value = cell.date.getFullYear()
      currentMonth.value = cell.date.getMonth() + 1
    }
  }
}

function clearDaySelection() {
  selectedDateKey.value = ''
}

// Waterfall stream grouped by day
const filteredBills = computed(() => {
  let list = bills.value
  if (activeFilterTab.value === 'expense') {
    list = list.filter(b => b.record_type === '支出')
  } else if (activeFilterTab.value === 'income') {
    list = list.filter(b => b.record_type === '收入')
  } else if (activeFilterTab.value === 'pending') {
    list = list.filter(b => b.reimbursement_status === '待报销')
  }

  if (selectedCategoryFilterId.value !== null) {
    list = list.filter(b => b.category_id === selectedCategoryFilterId.value)
  }

  const query = searchQuery.value.trim().toLowerCase()
  if (query) {
    list = list.filter(b => {
      const matchNote = (b.note || '').toLowerCase().includes(query)
      const matchCat = (b.category?.name || '').toLowerCase().includes(query)
      const matchSub = (b.subcategory?.name || '').toLowerCase().includes(query)
      const matchAmt = String(b.amount).includes(query)
      return matchNote || matchCat || matchSub || matchAmt
    })
  }
  return list
})

const dayGroups = computed<DayGroup[]>(() => {
  const map = new Map<string, BillItem[]>()
  for (const bill of filteredBills.value) {
    const items = map.get(bill.expense_date) ?? []
    items.push(bill)
    map.set(bill.expense_date, items)
  }
  const weekDays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  return Array.from(map.entries())
    .sort(([a], [b]) => b.localeCompare(a))
    .map(([date, items]) => {
      const d = new Date(date + 'T00:00:00')
      return {
        date,
        dateLabel: `${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')}`,
        weekDay: weekDays[d.getDay()],
        items: items.sort((a, b) => (b.expense_time ?? '').localeCompare(a.expense_time ?? '')),
        totalExpense: items.filter(i => i.record_type === '支出').reduce((s, i) => s + parseFloat(i.amount), 0),
        totalIncome: items.filter(i => i.record_type === '收入').reduce((s, i) => s + parseFloat(i.amount), 0),
      }
    })
})

const filterTabs = computed(() => [
  { key: 'all' as const, label: '全部', count: bills.value.length },
  { key: 'expense' as const, label: '仅支出', count: financialStats.value.expenseCount },
  { key: 'income' as const, label: '仅收入', count: financialStats.value.incomeCount },
  { key: 'pending' as const, label: '待报销', count: financialStats.value.pendingCount },
])

const quickCategories = computed(() => {
  return categoryTags.value.slice(0, 8).map(c => ({
    id: c.id,
    name: c.name,
    icon: getCategoryVisual(c.name, form.value.record_type).icon,
  }))
})

// Month navigation
const monthLabel = computed(() => {
  const months = ['一月', '二月', '三月', '四月', '五月', '六月', '七月', '八月', '九月', '十月', '十一月', '十二月']
  return `${currentYear.value} · ${months[currentMonth.value - 1]}`
})

const isCurrentMonth = computed(() =>
  currentYear.value === now.getFullYear() && currentMonth.value === now.getMonth() + 1
)

function prevMonth() {
  if (currentMonth.value === 1) { currentMonth.value = 12; currentYear.value-- }
  else currentMonth.value--
}
function nextMonth() {
  if (isCurrentMonth.value) return
  if (currentMonth.value === 12) { currentMonth.value = 1; currentYear.value++ }
  else currentMonth.value++
}

function jumpToCurrentMonth() {
  currentYear.value = now.getFullYear()
  currentMonth.value = now.getMonth() + 1
}

watch([currentYear, currentMonth], () => {
  collapsedDays.value.clear()
  selectedCategoryFilterId.value = null
  selectedDateKey.value = ''
  if (!bootstrapping.value) void loadBills()
})

// Modal actions
function openCreate(dateKey?: string) {
  formError.value = ''
  editingBill.value = null
  form.value = emptyForm()
  form.value.expense_date = dateKey || todayKey()
  showModal.value = true
}

function openEdit(bill: BillItem) {
  formError.value = ''
  editingBill.value = bill
  form.value = {
    record_type: bill.record_type,
    expense_date: bill.expense_date,
    expense_time: bill.expense_time?.slice(0, 5) ?? '',
    amount: bill.amount,
    category_id: bill.category_id,
    subcategory_id: bill.subcategory_id,
    payment_platform_id: bill.payment_platform_id,
    payment_channel_id: bill.payment_channel_id,
    fund_type_id: bill.fund_type_id,
    reimbursement_status: bill.reimbursement_status,
    note: bill.note ?? '',
  }
  showModal.value = true
}

function closeModal() {
  if (saving.value) return
  showModal.value = false
  editingBill.value = null
}

async function saveForm() {
  if (saving.value) return
  if (!Number.isFinite(Number(form.value.amount)) || Number(form.value.amount) <= 0 || !form.value.expense_date) {
    formError.value = '请填写日期和大于 0 的金额。'
    return
  }
  formError.value = ''
  saving.value = true
  try {
    const payload: BillPayload = {
      ...form.value,
      expense_time: form.value.expense_time ? form.value.expense_time + ':00' : null,
      amount: parseFloat(form.value.amount),
      note: form.value.note || null,
    }
    if (editingBill.value) {
      await billsApi.update(editingBill.value.id, payload, editingBill.value.version)
    } else {
      await billsApi.create(payload)
    }
    showModal.value = false
    editingBill.value = null
    const [year, month] = payload.expense_date.split('-').map(Number)
    if (currentYear.value !== year || currentMonth.value !== month) {
      currentYear.value = year
      currentMonth.value = month
    } else {
      await loadBills()
      selectedDateKey.value = payload.expense_date
    }
  } catch (e) {
    formError.value = (e as Error).message
  } finally {
    saving.value = false
  }
}

// Delete actions
function confirmDelete(bill: BillItem) {
  deleteError.value = ''
  deleteTarget.value = bill
  showDeleteConfirm.value = true
}

async function doDelete() {
  if (!deleteTarget.value || deleting.value) return
  deleting.value = true
  try {
    await billsApi.remove(deleteTarget.value.id, deleteTarget.value.version)
    showDeleteConfirm.value = false
    deleteTarget.value = null
    await loadBills()
  } catch (e) {
    deleteError.value = (e as Error).message
  } finally {
    deleting.value = false
  }
}

function fmt(n: number) { return n.toFixed(2) }

function toggleDay(group: DayGroup) {
  if (collapsedDays.value.has(group.date)) collapsedDays.value.delete(group.date)
  else collapsedDays.value.add(group.date)
}

function closeDelete() {
  if (!deleting.value) showDeleteConfirm.value = false
}

const editDialog = ref<HTMLElement | null>(null)
const deleteDialog = ref<HTMLElement | null>(null)
useDialogFocus(showModal, editDialog, closeModal)
useDialogFocus(showDeleteConfirm, deleteDialog, closeDelete)

onBeforeUnmount(() => { disposed = true; loadVersion++ })

onMounted(async () => {
  document.documentElement.classList.remove('theme-light')
  try {
    await loadTags()
  } catch (e) {
    console.error(e)
    tagError.value = (e as Error).message
  }
  if (disposed) return
  await syncMonthToLatestBill()
  if (disposed) return
  await loadBills()
  bootstrapping.value = false
})
</script>

<template>
  <div class="starry-workspace min-h-screen pb-24">
    <!-- Reusable DeepSpaceBackground Suite -->
    <DeepSpaceBackground :interactive="true" :glow="true" />
    <AppNavbar active="bills" />

    <div class="relative z-10 max-w-[1400px] w-full mx-auto px-4 sm:px-6 lg:px-8 pt-6">
      <!-- Breadcrumb & Header Banner -->
      <header class="mb-6 space-y-4">
        <!-- Breadcrumb -->
        <nav aria-label="面包屑" class="flex items-center gap-2 text-xs font-medium text-text-muted">
          <RouterLink to="/" class="hover:text-text transition-colors duration-150">首页</RouterLink>
          <span class="text-border">/</span>
          <span class="text-text">财务账单</span>
        </nav>

        <!-- Main Banner -->
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 p-5 sm:p-6 rounded-2xl border border-white/10 bg-surface-card/85 backdrop-blur-md shadow-2xl">
          <div class="space-y-1">
            <div class="flex items-center gap-2.5">
              <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold tracking-wider uppercase bg-primary/20 text-primary-light border border-primary/30">
                <span class="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse"></span>
                FINANCIAL CALENDAR
              </span>
              <span class="text-xs text-text-muted font-medium">日历看板 · 每日收支全景</span>
            </div>
            <h1 class="text-2xl sm:text-3xl font-extrabold tracking-tight text-text">
              财务账单
            </h1>
          </div>

          <!-- Controls: Month Switcher, Stream Drawer & Add Record -->
          <div class="flex flex-wrap items-center gap-3">
            <!-- Month Navigator Capsule -->
            <div class="flex items-center bg-surface-light/80 border border-border/80 rounded-xl p-1 shadow-sm">
              <button
                @click="prevMonth"
                aria-label="上个月"
                :disabled="bootstrapping || currentYear <= 2000 && currentMonth === 1"
                class="w-8 h-8 rounded-lg flex items-center justify-center text-text-muted hover:text-text hover:bg-white/[0.06] transition-colors btn-tactile disabled:opacity-30 disabled:cursor-not-allowed"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <span class="px-3 text-sm font-semibold text-text tracking-wide tabular-nums select-none">
                {{ monthLabel }}
              </span>
              <button
                @click="nextMonth"
                aria-label="下个月"
                :disabled="bootstrapping || isCurrentMonth || currentYear >= 2100 && currentMonth === 12"
                class="w-8 h-8 rounded-lg flex items-center justify-center text-text-muted hover:text-text hover:bg-white/[0.06] transition-colors btn-tactile disabled:opacity-30 disabled:cursor-not-allowed"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </div>

            <!-- Return to current month -->
            <button
              v-if="!isCurrentMonth"
              @click="jumpToCurrentMonth"
              class="px-3 py-1.5 rounded-xl border border-border/80 bg-surface-light text-xs font-medium text-text-muted hover:text-text hover:border-primary/40 transition-all btn-tactile"
            >
              回到本月
            </button>

            <!-- Stream Drawer Toggle Button -->
            <button
              @click="showFullStreamDrawer = true"
              class="flex items-center gap-1.5 px-3.5 py-2 rounded-xl border border-border/80 bg-surface-light text-xs font-semibold text-text hover:border-primary/50 hover:bg-surface-light/90 transition-all btn-tactile"
            >
              <span>📜 全月流水清单</span>
              <span class="px-1.5 py-0.2 rounded-md bg-white/[0.08] text-[11px] tabular-nums text-text-muted">
                {{ bills.length }}
              </span>
            </button>

            <!-- Add record CTA -->
            <button
              @click="openCreate()"
              :disabled="bootstrapping || !!tagError"
              class="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-primary to-primary-dark text-white text-sm font-semibold shadow-lg shadow-primary/25 hover:shadow-primary/40 hover:brightness-110 transition-all duration-200 btn-tactile disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
              </svg>
              <span>新增记录</span>
            </button>
          </div>
        </div>
      </header>

      <!-- Global alerts -->
      <div v-if="loadError" class="mb-6 rounded-2xl border border-rose-500/30 bg-rose-500/10 px-5 py-4 text-sm text-rose-200 shadow-lg">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="text-rose-400 font-bold">⚠️</span>
            <span>数据读取失败：{{ loadError }}</span>
          </div>
          <button @click="loadBills" class="px-3 py-1 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 font-medium transition-colors">重试</button>
        </div>
      </div>

      <div v-if="tagError" role="alert" class="mb-6 rounded-2xl border border-rose-500/30 bg-rose-500/10 px-5 py-4 text-sm text-rose-200 shadow-lg">
        <div class="flex items-center justify-between">
          <span>标签读取失败：{{ tagError }}</span>
          <button @click="retryTags" class="px-3 py-1 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 font-medium transition-colors">重新加载标签</button>
        </div>
      </div>

      <!-- Monthly Summary KPI Bar (data-testid="monthly-summary") -->
      <div
        v-if="!loading && !loadError"
        class="rounded-2xl border border-white/10 bg-surface-card/85 backdrop-blur-md p-4 sm:p-5 shadow-xl mb-6"
        data-testid="monthly-summary"
      >
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-4 items-center">
          <!-- Left: 3 Core Stats (6 cols on lg) -->
          <div class="lg:col-span-6 grid grid-cols-3 gap-2 sm:gap-3 text-center">
            <div class="p-2.5 rounded-xl bg-surface-light/60 border border-border/60">
              <div class="text-[11px] text-text-muted mb-0.5 font-medium">收入</div>
              <div class="text-sm sm:text-base font-bold text-income tabular-nums break-all">
                +{{ fmt(monthlySummary.income) }}
              </div>
            </div>
            <div class="p-2.5 rounded-xl bg-surface-light/60 border border-border/60">
              <div class="text-[11px] text-text-muted mb-0.5 font-medium">结余</div>
              <div
                class="text-sm sm:text-base font-bold tabular-nums break-all"
                :class="monthlySummary.net >= 0 ? 'text-income' : 'text-expense'"
              >
                {{ monthlySummary.net >= 0 ? '+' : '' }}{{ fmt(monthlySummary.net) }}
              </div>
            </div>
            <div class="p-2.5 rounded-xl bg-surface-light/60 border border-border/60">
              <div class="text-[11px] text-text-muted mb-0.5 font-medium">支出</div>
              <div class="text-sm sm:text-base font-bold text-expense tabular-nums break-all">
                -{{ fmt(monthlySummary.expense) }}
              </div>
            </div>
          </div>

          <!-- Right: Ratio Bar & Intelligent Metrics (6 cols on lg) -->
          <div class="lg:col-span-6 flex flex-col justify-between gap-2.5">
            <!-- Progress Bar (if income > 0) -->
            <div v-if="monthlySummary.income > 0" class="p-2 rounded-xl bg-surface-light/40 border border-border/40">
              <div class="flex justify-between items-center text-xs text-text-muted mb-1 font-medium">
                <span>支出占收入 {{ Math.round((monthlySummary.expense / monthlySummary.income) * 100) }}%</span>
                <span>本月收入 {{ fmt(monthlySummary.income) }}</span>
              </div>
              <div class="h-1.5 rounded-full bg-surface-light overflow-hidden">
                <div
                  class="h-full rounded-full bg-gradient-to-r from-rose-500 to-rose-400 transition-all duration-500"
                  :style="{ width: Math.min(100, (monthlySummary.expense / monthlySummary.income) * 100) + '%' }"
                ></div>
              </div>
            </div>

            <!-- Metrics Pills -->
            <div class="flex flex-wrap items-center justify-between gap-2 text-xs">
              <span class="text-text-muted">
                日均支出 <strong class="text-text tabular-nums font-semibold">¥{{ fmt(financialStats.dailyAverage) }}</strong>
              </span>
              <span class="text-text-muted">
                记账天数 <strong class="text-text tabular-nums font-semibold">{{ financialStats.activeDays }} 天</strong>
              </span>
              <span v-if="financialStats.pendingCount > 0" class="text-amber-300 font-medium">
                {{ financialStats.pendingCount }} 笔待报销 (¥{{ fmt(financialStats.pendingAmount) }})
              </span>
              <span class="text-text-muted">
                总流水 <strong class="text-text tabular-nums font-semibold">{{ bills.length }} 笔</strong>
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Loading state -->
      <div v-if="loading" class="text-center text-text-muted py-24 text-sm font-medium">
        <div class="inline-block w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin mb-3"></div>
        <div>加载中...</div>
      </div>

      <!-- Empty state when no bills in month -->
      <div v-else-if="!loadError && bills.length === 0" class="text-center text-text-muted py-20 text-sm rounded-2xl border border-dashed border-border/60 bg-surface-card/40 mb-8">
        <div class="text-3xl mb-2 opacity-50">📑</div>
        <div class="font-medium text-text text-base">本月暂无记录</div>
        <p class="text-xs text-text-muted mt-1">在日历任意单元格上点击或点击右上角“新增记录”开启记账</p>
      </div>

      <!-- Side-by-Side: Core Calendar Board (Left 7-8 cols) + Day Detail / Month Overview (Right 4-5 cols) -->
      <div v-if="!loading && !loadError" class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start mb-10">
        <!-- Calendar Board (lg:col-span-8) -->
        <section aria-label="账单日历看板" class="lg:col-span-8 min-w-0">
          <div class="rounded-2xl border border-white/10 bg-surface-card/85 backdrop-blur-md p-3 sm:p-5 shadow-2xl overflow-hidden">
            <!-- Weekday Headers (周一 ~ 周日) -->
            <div class="grid grid-cols-7 gap-1 sm:gap-2 mb-2 text-center text-xs font-semibold text-text-muted select-none">
              <div v-for="w in ['周一', '周二', '周三', '周四', '周五', '周六', '周日']" :key="w" class="py-1">
                {{ w }}
              </div>
            </div>

            <!-- 7-Column Calendar Grid -->
            <div class="grid grid-cols-7 gap-1 sm:gap-2">
              <button
                v-for="cell in calendarGridDays"
                :key="cell.dateKey"
                type="button"
                class="cal-day-cell text-left transition-all duration-200 rounded-xl border relative flex flex-col justify-between overflow-hidden cursor-pointer"
                :class="[
                  cell.current ? 'bg-surface-light/40 border-white/[0.07]' : 'bg-surface-light/10 border-transparent opacity-35',
                  cell.today ? 'border-cyan-400/50 bg-cyan-500/10 shadow-[0_0_15px_rgba(6,182,212,0.15)] ring-1 ring-cyan-400/40' : '',
                  selectedDateKey === cell.dateKey ? 'border-primary bg-primary/20 shadow-[0_0_20px_rgba(124,58,237,0.3)] ring-2 ring-primary' : 'hover:border-primary/40 hover:bg-surface-light/70',
                ]"
                :aria-label="`${cell.dateLabel} ${cell.weekDay}${cell.items.length ? `，${cell.items.length}笔账单` : ''}`"
                @click="toggleDaySelection(cell)"
              >
                <!-- Cell Top Row: Date number, Today badge, Pending indicator -->
                <div class="flex items-center justify-between w-full mb-1">
                  <span
                    class="text-xs sm:text-sm font-bold tabular-nums"
                    :class="cell.current ? (cell.today ? 'text-cyan-300' : 'text-text') : 'text-text-muted/40'"
                  >
                    {{ cell.day }}
                  </span>
                  <div class="flex items-center gap-1">
                    <span v-if="cell.today" class="today-micro-badge">今天</span>
                    <span
                      v-if="cell.hasPendingReimburse"
                      class="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse"
                      title="有待报销款项"
                    ></span>
                    <span
                      v-if="cell.items.length > 0"
                      class="text-[10px] text-text-muted font-medium tabular-nums opacity-75 hidden sm:inline"
                    >
                      {{ cell.items.length }}笔
                    </span>
                  </div>
                </div>

                <!-- Cell Middle Row: Amounts (Expense & Income) -->
                <div class="w-full space-y-0.5 text-left mb-1 min-h-[26px] sm:min-h-[32px]">
                  <div
                    v-if="cell.totalExpense > 0"
                    class="text-[10px] sm:text-xs font-bold text-expense tabular-nums truncate leading-tight"
                  >
                    -{{ fmt(cell.totalExpense) }}
                  </div>
                  <div
                    v-if="cell.totalIncome > 0"
                    class="text-[10px] sm:text-xs font-bold text-income tabular-nums truncate leading-tight"
                  >
                    +{{ fmt(cell.totalIncome) }}
                  </div>
                </div>

                <!-- Cell Bottom Row: Category icons -->
                <div class="w-full flex items-center justify-between pt-0.5 border-t border-white/[0.04] min-h-[16px]">
                  <div class="flex items-center gap-1 overflow-hidden">
                    <span
                      v-for="(icon, idx) in cell.categoryIcons"
                      :key="idx"
                      class="text-[10px] sm:text-[11px] select-none leading-none"
                    >
                      {{ icon }}
                    </span>
                  </div>
                  <!-- Quick add button on hover -->
                  <button
                    type="button"
                    @click.stop="openCreate(cell.dateKey)"
                    class="w-4 h-4 rounded flex items-center justify-center text-text-muted/50 hover:text-white hover:bg-primary/40 opacity-0 group-hover:opacity-100 transition-opacity"
                    title="在该日记一笔"
                  >
                    +
                  </button>
                </div>
              </button>
            </div>
          </div>
        </section>

        <!-- Right Side Inspector: Day Detail (when date selected) OR Monthly Analytics (when no date selected) -->
        <aside class="lg:col-span-4 min-w-0 space-y-6 lg:sticky lg:top-24">
          <!-- Day Detail Inspector Panel (shown when a day is selected) -->
          <div
            v-if="selectedDay"
            class="rounded-2xl border border-primary/30 bg-surface-card/90 backdrop-blur-md p-5 shadow-2xl space-y-4"
          >
            <!-- Inspector Header -->
            <div class="flex items-center justify-between pb-3 border-b border-border/80">
              <div class="space-y-1">
                <div class="flex items-center gap-2">
                  <div class="day-time-capsule" :class="{ 'is-today': selectedDay.today }">
                    <span class="day-date-text">{{ selectedDay.dateLabel }}</span>
                    <span class="day-divider">·</span>
                    <span class="day-weekday-text">{{ selectedDay.weekDay }}</span>
                    <span v-if="selectedDay.today" class="today-micro-badge">今天</span>
                  </div>
                  <span class="text-xs text-text-muted">
                    {{ selectedDay.items.length }} 笔明细
                  </span>
                </div>
                <div class="flex items-center gap-3 text-xs font-semibold tabular-nums pt-1">
                  <span v-if="selectedDay.totalExpense > 0" class="text-expense">
                    支出 -{{ fmt(selectedDay.totalExpense) }}
                  </span>
                  <span v-if="selectedDay.totalIncome > 0" class="text-income">
                    收入 +{{ fmt(selectedDay.totalIncome) }}
                  </span>
                </div>
              </div>

              <button
                @click="clearDaySelection"
                aria-label="关闭当日明细"
                class="w-7 h-7 rounded-lg flex items-center justify-center text-text-muted hover:text-text hover:bg-white/[0.06] transition-colors"
                title="关闭明细"
              >
                ✕
              </button>
            </div>

            <!-- List of items for selected day -->
            <div class="space-y-2.5 max-h-[460px] overflow-y-auto pr-1">
              <div v-if="selectedDay.items.length === 0" class="text-center py-10 text-text-muted space-y-2">
                <div class="text-2xl opacity-40">☕</div>
                <div class="text-xs">这一天还没有记账</div>
                <button
                  @click="openCreate(selectedDay.dateKey)"
                  class="mt-1 px-3 py-1 rounded-lg bg-primary/20 text-primary-light hover:bg-primary/30 text-xs font-semibold transition-colors"
                >
                  + 记一笔
                </button>
              </div>

              <div
                v-for="item in selectedDay.items"
                :key="item.id"
                class="p-3.5 rounded-xl border border-white/[0.08] bg-surface-light/40 hover:bg-surface-light/70 transition-all space-y-2 group/inspector-row"
              >
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-2 min-w-0">
                    <span class="text-base shrink-0 select-none">{{ getCategoryVisual(item.category?.name, item.record_type).icon }}</span>
                    <div class="min-w-0">
                      <div class="flex items-center gap-1.5">
                        <span class="text-xs sm:text-sm font-bold text-text truncate">
                          {{ item.subcategory?.name ?? item.category?.name ?? '-' }}
                        </span>
                        <span
                          v-if="item.subcategory"
                          class="text-[10px] text-text-muted bg-surface-card px-1.5 py-0.2 rounded border border-border/50 shrink-0"
                        >
                          {{ item.category?.name }}
                        </span>
                      </div>
                      <div class="text-[10px] text-text-muted tabular-nums">
                        {{ item.expense_time?.slice(0, 5) || '未记录时间' }}
                      </div>
                    </div>
                  </div>

                  <!-- Amount -->
                  <div class="text-right shrink-0">
                    <div
                      class="text-sm sm:text-base font-extrabold tabular-nums"
                      :class="item.record_type === '收入' ? 'text-income' : 'text-text'"
                    >
                      {{ item.record_type === '收入' ? '+' : '-' }}{{ fmt(parseFloat(item.amount)) }}
                    </div>
                  </div>
                </div>

                <!-- Note -->
                <div v-if="item.note" class="text-xs text-text/85 bg-black/20 p-2 rounded-lg break-words">
                  {{ item.note }}
                </div>

                <!-- Meta Pills & Actions -->
                <div class="flex items-center justify-between pt-1 border-t border-white/[0.04]">
                  <div class="flex flex-wrap items-center gap-1.5 text-[10px] text-text-muted">
                    <span v-if="item.payment_platform" class="px-1.5 py-0.2 rounded bg-surface-card border border-border/40">
                      {{ item.payment_platform.name }}
                    </span>
                    <span
                      v-if="item.reimbursement_status === '待报销'"
                      class="px-1.5 py-0.2 rounded bg-amber-500/15 border border-amber-500/30 text-amber-300 font-semibold"
                    >
                      待报销
                    </span>
                    <span
                      v-else-if="item.reimbursement_status === '已报销'"
                      class="px-1.5 py-0.2 rounded bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 font-semibold"
                    >
                      已报销
                    </span>
                  </div>

                  <!-- Actions -->
                  <div class="flex items-center gap-1">
                    <button
                      @click="openEdit(item)"
                      :disabled="!!tagError"
                      :aria-label="`编辑记录 ${item.note || item.id}`"
                      class="w-6 h-6 rounded flex items-center justify-center text-text-muted hover:text-primary hover:bg-primary/10 transition-colors btn-tactile text-xs"
                      title="编辑"
                    >
                      ✎
                    </button>
                    <button
                      @click="confirmDelete(item)"
                      :aria-label="`删除记录 ${item.note || item.id}`"
                      class="w-6 h-6 rounded flex items-center justify-center text-text-muted hover:text-expense hover:bg-expense-bg transition-colors btn-tactile text-xs"
                      title="删除"
                    >
                      🗑
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <!-- Inspector Footer: Quick Add for date -->
            <button
              @click="openCreate(selectedDay.dateKey)"
              class="w-full py-2.5 rounded-xl bg-gradient-to-r from-primary to-primary-dark text-white text-xs font-bold shadow-md shadow-primary/25 hover:shadow-primary/40 transition-all btn-tactile flex items-center justify-center gap-2"
            >
              <span>+ 在该日新增记录</span>
            </button>
          </div>

          <!-- Monthly Analytics Overview (shown when NO day is selected) -->
          <template v-else>
            <!-- Top Expense Categories Breakdown -->
            <div
              v-if="financialStats.categoryBreakdown.length > 0"
              class="rounded-2xl border border-white/10 bg-surface-card/85 backdrop-blur-md p-5 shadow-xl space-y-4"
            >
              <div class="flex items-center justify-between">
                <h3 class="text-sm font-bold text-text">支出分类排行</h3>
                <span class="text-xs text-text-muted">Top 5 构成</span>
              </div>

              <div class="space-y-3">
                <div
                  v-for="cat in financialStats.categoryBreakdown.slice(0, 5)"
                  :key="cat.id"
                  class="p-2.5 rounded-xl border border-border/50 bg-surface-light/40 space-y-1.5"
                >
                  <div class="flex items-center justify-between text-xs">
                    <div class="flex items-center gap-2">
                      <span class="text-sm">{{ cat.visual.icon }}</span>
                      <span class="font-semibold text-text">{{ cat.name }}</span>
                    </div>
                    <div class="tabular-nums font-semibold text-text">
                      ¥{{ fmt(cat.total) }}
                      <span class="text-[11px] text-text-muted font-normal ml-1">({{ cat.percent }}%)</span>
                    </div>
                  </div>
                  <div class="h-1.5 rounded-full bg-surface-light overflow-hidden">
                    <div
                      class="h-full rounded-full transition-all duration-500"
                      :style="{
                        width: Math.min(100, cat.percent) + '%',
                        backgroundColor: cat.visual.color,
                      }"
                    ></div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Reimbursement Tracker -->
            <div
              v-if="financialStats.pendingCount > 0 || financialStats.doneCount > 0"
              class="rounded-2xl border border-white/10 bg-surface-card/85 backdrop-blur-md p-5 shadow-xl space-y-3"
            >
              <h3 class="text-sm font-bold text-text">报销状态追踪</h3>
              <div class="grid grid-cols-2 gap-3">
                <div class="p-3 rounded-xl border border-amber-500/25 bg-amber-500/10">
                  <div class="text-[11px] text-amber-300 font-semibold mb-1">待报销</div>
                  <div class="text-base font-bold text-amber-200 tabular-nums">
                    ¥{{ fmt(financialStats.pendingAmount) }}
                  </div>
                  <div class="text-[11px] text-amber-300/70 mt-0.5">{{ financialStats.pendingCount }} 笔待处理</div>
                </div>

                <div class="p-3 rounded-xl border border-emerald-500/25 bg-emerald-500/10">
                  <div class="text-[11px] text-emerald-300 font-semibold mb-1">已报销</div>
                  <div class="text-base font-bold text-emerald-200 tabular-nums">
                    ¥{{ fmt(financialStats.doneAmount) }}
                  </div>
                  <div class="text-[11px] text-emerald-300/70 mt-0.5">{{ financialStats.doneCount }} 笔已结算</div>
                </div>
              </div>
            </div>
          </template>
        </aside>
      </div>
    </div>

    <!-- Slide-over Full Stream Drawer (全月流水抽屉) -->
    <Teleport to="body">
      <div v-if="showFullStreamDrawer" class="fixed inset-0 z-40 overflow-hidden">
        <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="showFullStreamDrawer = false"></div>
        <div class="fixed inset-y-0 right-0 max-w-full flex pl-6 sm:pl-10">
          <aside class="w-screen max-w-xl bg-surface-card/95 backdrop-blur-2xl border-l border-white/15 shadow-2xl flex flex-col z-50 text-text">
            <!-- Header -->
            <div class="p-5 sm:p-6 border-b border-border/80 flex items-center justify-between bg-surface-card/90">
              <div>
                <h2 class="text-base font-bold text-text">全月账单流水明细</h2>
                <div class="text-xs text-text-muted mt-0.5">{{ monthLabel }} · 共 {{ bills.length }} 笔记录</div>
              </div>
              <button
                @click="showFullStreamDrawer = false"
                class="w-8 h-8 rounded-lg flex items-center justify-center text-text-muted hover:text-text hover:bg-white/[0.06] transition-colors"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <!-- Stream Filter Toolbar -->
            <div class="p-4 border-b border-border/60 bg-surface-light/30 space-y-3">
              <div class="flex items-center gap-1 overflow-x-auto py-0.5 no-scrollbar">
                <button
                  v-for="tab in filterTabs"
                  :key="tab.key"
                  type="button"
                  @click="activeFilterTab = tab.key"
                  class="px-2.5 py-1 rounded-lg text-xs font-semibold transition-all shrink-0"
                  :class="activeFilterTab === tab.key ? 'bg-primary text-white shadow-sm' : 'text-text-muted hover:text-text'"
                >
                  {{ tab.label }} ({{ tab.count }})
                </button>
              </div>

              <div class="relative">
                <input
                  v-model="searchQuery"
                  type="text"
                  placeholder="搜索备注、金额、分类..."
                  class="w-full bg-surface-light border border-border/80 rounded-xl pl-8 pr-3 py-1.5 text-xs text-text placeholder-text-muted/60 focus:outline-none focus:border-primary/50 transition-colors"
                />
                <svg class="w-3.5 h-3.5 text-text-muted absolute left-2.5 top-1/2 -translate-y-1/2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
            </div>

            <!-- Stream List Content -->
            <div class="flex-1 overflow-y-auto p-4 space-y-4">
              <div v-if="dayGroups.length === 0" class="text-center py-16 text-text-muted text-sm">
                没有匹配的记录
              </div>

              <div
                v-for="group in dayGroups"
                :key="group.date"
                class="rounded-xl border border-white/[0.08] bg-surface-light/30 overflow-hidden"
              >
                <!-- Day Header -->
                <button
                  @click="toggleDay(group)"
                  class="w-full flex items-center justify-between px-4 py-3 bg-white/[0.02] hover:bg-white/[0.05] transition-colors text-left"
                >
                  <div class="flex items-center gap-2">
                    <span class="text-xs font-bold text-text">{{ group.dateLabel }}</span>
                    <span class="text-xs text-text-muted">{{ group.weekDay }}</span>
                    <span class="text-[11px] text-text-muted/70">({{ group.items.length }}笔)</span>
                  </div>
                  <div class="text-xs font-bold tabular-nums">
                    <span v-if="group.totalExpense > 0" class="text-expense mr-2">-{{ fmt(group.totalExpense) }}</span>
                    <span v-if="group.totalIncome > 0" class="text-income">+{{ fmt(group.totalIncome) }}</span>
                  </div>
                </button>

                <!-- Items -->
                <div v-show="!collapsedDays.has(group.date)" class="divide-y divide-border/40">
                  <div
                    v-for="item in group.items"
                    :key="item.id"
                    class="p-3 flex items-center justify-between hover:bg-white/[0.02] transition-colors"
                  >
                    <div class="flex items-center gap-2.5 min-w-0">
                      <span class="text-base select-none">{{ getCategoryVisual(item.category?.name, item.record_type).icon }}</span>
                      <div class="min-w-0">
                        <div class="text-xs font-bold text-text truncate">
                          {{ item.subcategory?.name ?? item.category?.name ?? '-' }}
                        </div>
                        <div v-if="item.note" class="text-[11px] text-text-muted truncate max-w-[200px]">
                          {{ item.note }}
                        </div>
                      </div>
                    </div>

                    <div class="flex items-center gap-3">
                      <div class="text-right">
                        <div
                          class="text-xs font-bold tabular-nums"
                          :class="item.record_type === '收入' ? 'text-income' : 'text-text'"
                        >
                          {{ item.record_type === '收入' ? '+' : '-' }}{{ fmt(parseFloat(item.amount)) }}
                        </div>
                        <div class="text-[10px] text-text-muted tabular-nums">
                          {{ item.expense_time?.slice(0, 5) ?? '' }}
                        </div>
                      </div>

                      <div class="flex items-center gap-1">
                        <button
                          @click="openEdit(item)"
                          class="w-6 h-6 rounded flex items-center justify-center text-text-muted hover:text-primary"
                        >
                          ✎
                        </button>
                        <button
                          @click="confirmDelete(item)"
                          class="w-6 h-6 rounded flex items-center justify-center text-text-muted hover:text-expense"
                        >
                          🗑
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </Teleport>

    <!-- Add/Edit Modal -->
    <Teleport to="body">
      <div v-if="showModal" class="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4">
        <div class="absolute inset-0 bg-black/70 backdrop-blur-sm" @click="closeModal"></div>
        <div
          ref="editDialog"
          role="dialog"
          aria-modal="true"
          aria-labelledby="bill-dialog-title"
          tabindex="-1"
          data-lenis-prevent
          class="relative w-full max-w-lg bg-surface-card rounded-2xl border border-white/15 shadow-2xl overflow-hidden"
        >
          <!-- Header -->
          <div class="flex items-center justify-between px-5 sm:px-6 py-4 border-b border-border/80 bg-surface-card/90">
            <h2 id="bill-dialog-title" class="font-bold text-lg text-text">
              {{ editingBill ? '编辑记录' : '新增记录' }}
            </h2>
            <button
              @click="closeModal"
              aria-label="关闭编辑窗口"
              :disabled="saving"
              class="w-8 h-8 rounded-lg flex items-center justify-center text-text-muted hover:text-text hover:bg-white/[0.06] transition-colors"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <!-- Form Body -->
          <form @submit.prevent="saveForm" class="px-5 sm:px-6 py-5 space-y-4 overflow-y-auto max-h-[75vh]">
            <p v-if="formError" role="alert" class="text-sm text-rose-300 bg-rose-500/10 border border-rose-500/30 p-2.5 rounded-xl">
              {{ formError }}
            </p>

            <fieldset :disabled="saving" class="space-y-4">
              <!-- Record Type Segmented Switch -->
              <div class="flex gap-2 p-1 rounded-xl bg-surface-light border border-border/80">
                <button
                  type="button"
                  v-for="t in ['支出', '收入']"
                  :key="t"
                  @click="form.record_type = t as '支出' | '收入'"
                  class="flex-1 py-2 rounded-lg text-sm font-bold border transition-all duration-150"
                  :class="form.record_type === t
                    ? (t === '支出' ? 'bg-expense-bg border-expense-border text-expense-text-btn shadow-sm' : 'bg-income-bg border-income-border text-income-text-btn shadow-sm')
                    : 'border-transparent text-text-muted hover:text-text'"
                >
                  {{ t }}
                </button>
              </div>

              <!-- Big Immersive Amount Input -->
              <div>
                <label for="bill-amount" class="block text-xs font-semibold text-text-muted mb-1.5">金额</label>
                <div class="relative flex items-center">
                  <span class="absolute left-4 text-2xl font-bold text-text-muted/60 select-none">¥</span>
                  <input
                    id="bill-amount"
                    v-model="form.amount"
                    type="number"
                    step="0.01"
                    min="0.01"
                    required
                    placeholder="0.00"
                    class="w-full bg-surface-light border border-border rounded-xl pl-10 pr-4 py-3 text-2xl font-extrabold tabular-nums text-text placeholder-text-muted/40 focus:outline-none focus:border-primary/60 transition-colors"
                  />
                </div>
              </div>

              <!-- Frequent Category Chips (Quick Select) -->
              <div v-if="quickCategories.length" class="space-y-1.5">
                <span class="block text-xs text-text-muted font-medium">常用大类快捷选择</span>
                <div class="flex flex-wrap gap-1.5">
                  <button
                    v-for="cat in quickCategories"
                    :key="cat.id"
                    type="button"
                    @click="form.category_id = cat.id"
                    class="px-2.5 py-1 rounded-lg text-xs font-medium border transition-all duration-150"
                    :class="form.category_id === cat.id
                      ? 'bg-primary/20 border-primary text-primary-light shadow-sm'
                      : 'bg-surface-light border-border/80 text-text-muted hover:border-primary/40 hover:text-text'"
                  >
                    {{ cat.icon }} {{ cat.name }}
                  </button>
                </div>
              </div>

              <!-- Category & Subcategory Selectors -->
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label for="bill-category_id" class="block text-xs font-semibold text-text-muted mb-1.5">大类</label>
                  <select
                    id="bill-category_id"
                    v-model="form.category_id"
                    class="w-full bg-surface-light border border-border rounded-xl px-3 py-2 text-sm text-text focus:outline-none focus:border-primary/50 transition-colors"
                  >
                    <option :value="null">-- 选择 --</option>
                    <option v-for="t in categoryTags" :key="t.id" :value="t.id">{{ t.name }}</option>
                  </select>
                </div>
                <div>
                  <label for="bill-subcategory_id" class="block text-xs font-semibold text-text-muted mb-1.5">小类（选填）</label>
                  <select
                    id="bill-subcategory_id"
                    v-model="form.subcategory_id"
                    :disabled="!subcategoryOptions.length"
                    class="w-full bg-surface-light border border-border rounded-xl px-3 py-2 text-sm text-text focus:outline-none focus:border-primary/50 transition-colors disabled:opacity-40"
                  >
                    <option :value="null">-- 选择 --</option>
                    <option v-for="t in subcategoryOptions" :key="t.id" :value="t.id">{{ t.name }}</option>
                  </select>
                </div>
              </div>

              <!-- Date & Time -->
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label for="bill-expense_date" class="block text-xs font-semibold text-text-muted mb-1.5">日期</label>
                  <input
                    id="bill-expense_date"
                    v-model="form.expense_date"
                    type="date"
                    required
                    class="w-full bg-surface-light border border-border rounded-xl px-3 py-2 text-sm text-text focus:outline-none focus:border-primary/50 transition-colors"
                  />
                </div>
                <div>
                  <label for="bill-expense_time" class="block text-xs font-semibold text-text-muted mb-1.5">时间（选填）</label>
                  <input
                    id="bill-expense_time"
                    v-model="form.expense_time"
                    type="time"
                    class="w-full bg-surface-light border border-border rounded-xl px-3 py-2 text-sm text-text focus:outline-none focus:border-primary/50 transition-colors"
                  />
                </div>
              </div>

              <!-- Payment details & Reimbursement status (only for expense) -->
              <template v-if="form.record_type === '支出'">
                <div>
                  <label for="bill-payment_platform_id" class="block text-xs font-semibold text-text-muted mb-1.5">支付平台（选填）</label>
                  <select
                    id="bill-payment_platform_id"
                    v-model="form.payment_platform_id"
                    class="w-full bg-surface-light border border-border rounded-xl px-3 py-2 text-sm text-text focus:outline-none focus:border-primary/50 transition-colors"
                  >
                    <option :value="null">-- 选择 --</option>
                    <option v-for="t in platformTags" :key="t.id" :value="t.id">{{ t.name }}</option>
                  </select>
                </div>

                <div class="grid grid-cols-2 gap-3">
                  <div>
                    <label for="bill-payment_channel_id" class="block text-xs font-semibold text-text-muted mb-1.5">支付通道（选填）</label>
                    <select
                      id="bill-payment_channel_id"
                      v-model="form.payment_channel_id"
                      class="w-full bg-surface-light border border-border rounded-xl px-3 py-2 text-sm text-text focus:outline-none focus:border-primary/50 transition-colors"
                    >
                      <option :value="null">-- 选择 --</option>
                      <option v-for="t in channelTags" :key="t.id" :value="t.id">{{ t.name }}</option>
                    </select>
                  </div>
                  <div>
                    <label for="bill-fund_type_id" class="block text-xs font-semibold text-text-muted mb-1.5">资金类型（选填）</label>
                    <select
                      id="bill-fund_type_id"
                      v-model="form.fund_type_id"
                      class="w-full bg-surface-light border border-border rounded-xl px-3 py-2 text-sm text-text focus:outline-none focus:border-primary/50 transition-colors"
                    >
                      <option :value="null">-- 选择 --</option>
                      <option v-for="t in fundTags" :key="t.id" :value="t.id">{{ t.name }}</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label for="bill-reimbursement_status" class="block text-xs font-semibold text-text-muted mb-1.5">报销状态</label>
                  <select
                    id="bill-reimbursement_status"
                    v-model="form.reimbursement_status"
                    class="w-full bg-surface-light border border-border rounded-xl px-3 py-2 text-sm text-text focus:outline-none focus:border-primary/50 transition-colors"
                  >
                    <option value="无需报销">无需报销</option>
                    <option value="待报销">待报销</option>
                    <option value="已报销">已报销</option>
                  </select>
                </div>
              </template>

              <!-- Note -->
              <div>
                <label for="bill-note" class="block text-xs font-semibold text-text-muted mb-1.5">备注（选填）</label>
                <input
                  id="bill-note"
                  v-model="form.note"
                  type="text"
                  placeholder="买了什么、去哪里..."
                  class="w-full bg-surface-light border border-border rounded-xl px-3 py-2.5 text-sm text-text focus:outline-none focus:border-primary/50 transition-colors"
                />
              </div>

              <!-- Submit button -->
              <button
                type="submit"
                :disabled="saving"
                class="w-full py-3 rounded-xl bg-gradient-to-r from-primary to-primary-dark text-white text-sm font-bold shadow-lg shadow-primary/25 hover:shadow-primary/40 transition-all duration-200 btn-tactile disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {{ saving ? '保存中...' : (editingBill ? '保存修改' : '添加记录') }}
              </button>
            </fieldset>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Delete Confirm Modal -->
    <Teleport to="body">
      <div v-if="showDeleteConfirm" class="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4">
        <div class="absolute inset-0 bg-black/70 backdrop-blur-sm" @click="closeDelete"></div>
        <div
          ref="deleteDialog"
          role="dialog"
          aria-modal="true"
          aria-labelledby="bill-delete-title"
          tabindex="-1"
          data-lenis-prevent
          class="relative w-full max-w-sm bg-surface-card rounded-2xl border border-white/15 shadow-2xl p-6"
        >
          <h3 id="bill-delete-title" class="font-bold text-lg text-text mb-2">确认删除</h3>
          <p class="text-sm text-text-muted mb-6 leading-relaxed">
            删除
            <span class="text-text font-semibold">
              {{ deleteTarget?.subcategory?.name ?? deleteTarget?.category?.name ?? '该记录' }}
            </span>
            ，金额
            <span class="text-expense font-semibold tabular-nums">
              {{ deleteTarget ? fmt(parseFloat(deleteTarget.amount)) : '' }}
            </span>
            ，此操作不可撤销。
          </p>
          <p v-if="deleteError" role="alert" class="text-sm text-rose-300 mb-3">{{ deleteError }}</p>
          <div class="flex gap-3">
            <button
              @click="closeDelete"
              class="flex-1 py-2.5 rounded-xl border border-border text-text-muted text-sm font-semibold hover:border-primary/30 hover:text-text transition-colors btn-tactile"
            >
              取消
            </button>
            <button
              @click="doDelete"
              :disabled="deleting"
              class="flex-1 py-2.5 rounded-xl bg-rose-500 text-white text-sm font-semibold hover:bg-rose-600 transition-colors disabled:opacity-50 btn-tactile shadow-lg shadow-rose-500/25"
            >
              {{ deleting ? '删除中...' : '确认删除' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.starry-workspace {
  position: relative;
  isolation: isolate;
}

/* Calendar Day Cell */
.cal-day-cell {
  min-height: 80px;
  padding: 0.45rem;
}
@media (min-width: 640px) {
  .cal-day-cell {
    min-height: 105px;
    padding: 0.6rem;
  }
}

/* Micro-glow Time Capsule */
.day-time-capsule {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.28rem 0.75rem;
  border-radius: 9999px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--text);
  transition: all 0.2s ease;
}

.day-time-capsule.is-today {
  background: rgba(6, 182, 212, 0.15);
  border-color: rgba(6, 182, 212, 0.4);
  box-shadow: 0 0 16px rgba(6, 182, 212, 0.18);
}

.day-time-capsule.is-today .day-date-text {
  color: #67e8f9;
}

.day-divider {
  color: rgba(148, 163, 184, 0.5);
  font-size: 0.7rem;
}

.today-micro-badge {
  font-size: 0.62rem;
  padding: 0.08rem 0.35rem;
  border-radius: 9999px;
  background: rgba(6, 182, 212, 0.25);
  color: #67e8f9;
  font-weight: 700;
  letter-spacing: 0.02em;
}

/* Select options */
select option {
  background-color: var(--surface-card);
  color: var(--text);
}

/* Date/time picker styling */
input[type="date"]::-webkit-calendar-picker-indicator,
input[type="time"]::-webkit-calendar-picker-indicator {
  filter: invert(0.7);
  cursor: pointer;
  transition: filter 0.3s ease;
}

.theme-light input[type="date"]::-webkit-calendar-picker-indicator,
.theme-light input[type="time"]::-webkit-calendar-picker-indicator {
  filter: none;
}

/* Hide scrollbar helper */
.no-scrollbar::-webkit-scrollbar {
  display: none;
}
.no-scrollbar {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
</style>
