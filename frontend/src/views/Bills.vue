<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const isDark = ref(true)

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

// ---- Types ----
interface TagOut {
  id: number
  name: string
  type: string
  parent_id: number | null
  sort_order: number
  children: TagOut[]
}

interface BillItem {
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
}

interface DayGroup {
  date: string
  dateLabel: string
  weekDay: string
  items: BillItem[]
  totalExpense: number
  totalIncome: number
  expanded: boolean
}

// ---- State ----
const now = new Date()
const currentYear = ref(now.getFullYear())
const currentMonth = ref(now.getMonth() + 1)

const bills = ref<BillItem[]>([])
const loading = ref(false)
const loadError = ref('')
const bootstrapping = ref(true)
const monthlySummary = ref({ income: 0, expense: 0, net: 0 })

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
  expense_date: new Date().toISOString().slice(0, 10),
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

async function loadTags() {
  const all: TagOut[] = await apiFetch('/tags/')
  categoryTags.value = all.filter(t => t.type === 'category')
  platformTags.value = await apiFetch('/tags/all?tag_type=payment_platform')
  channelTags.value = await apiFetch('/tags/all?tag_type=payment_channel')
  fundTags.value = await apiFetch('/tags/all?tag_type=fund_type')
}

async function loadBills() {
  loading.value = true
  loadError.value = ''
  try {
    const y = currentYear.value
    const m = currentMonth.value
    const dFrom = `${y}-${String(m).padStart(2, '0')}-01`
    const lastDay = new Date(y, m, 0).getDate()
    const dTo = `${y}-${String(m).padStart(2, '0')}-${lastDay}`
    const data = await apiFetch(`/bills/?date_from=${dFrom}&date_to=${dTo}&limit=200`)
    bills.value = data.items
    const summary = await apiFetch(`/bills/summary/monthly?year=${y}&month=${m}`)
    monthlySummary.value = {
      income: parseFloat(summary.income),
      expense: parseFloat(summary.expense),
      net: parseFloat(summary.net),
    }
  } catch (e) {
    console.error(e)
    loadError.value = (e as Error).message
    bills.value = []
  } finally {
    loading.value = false
  }
}

async function syncMonthToLatestBill() {
  try {
    const data = await apiFetch('/bills/?limit=1')
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

// ---- Computed: subcategories for selected category ----
const subcategoryOptions = computed<TagOut[]>(() => {
  if (!form.value.category_id) return []
  const cat = categoryTags.value.find(t => t.id === form.value.category_id)
  return cat?.children ?? []
})

// Reset subcategory when category changes
watch(() => form.value.category_id, () => { form.value.subcategory_id = null })

// ---- Computed: group by day ----
const dayGroups = computed<DayGroup[]>(() => {
  const map = new Map<string, BillItem[]>()
  for (const bill of bills.value) {
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
        expanded: true,
      }
    })
})

// ---- Month navigation ----
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

watch([currentYear, currentMonth], () => {
  if (!bootstrapping.value) void loadBills()
})

// ---- Modal actions ----
function openCreate() {
  editingBill.value = null
  form.value = emptyForm()
  form.value.expense_date = new Date().toISOString().slice(0, 10)
  showModal.value = true
}

function openEdit(bill: BillItem) {
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
  showModal.value = false
  editingBill.value = null
}

async function saveForm() {
  if (!form.value.amount || !form.value.expense_date) return
  saving.value = true
  try {
    const payload = {
      ...form.value,
      expense_time: form.value.expense_time ? form.value.expense_time + ':00' : null,
      amount: parseFloat(form.value.amount),
      note: form.value.note || null,
    }
    if (editingBill.value) {
      await apiFetch(`/bills/${editingBill.value.id}`, { method: 'PATCH', body: JSON.stringify(payload) })
    } else {
      await apiFetch('/bills/', { method: 'POST', body: JSON.stringify(payload) })
    }
    closeModal()
    await loadBills()
  } catch (e) {
    alert((e as Error).message)
  } finally {
    saving.value = false
  }
}

// ---- Delete ----
function confirmDelete(bill: BillItem) {
  deleteTarget.value = bill
  showDeleteConfirm.value = true
}

async function doDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    await apiFetch(`/bills/${deleteTarget.value.id}`, { method: 'DELETE' })
    showDeleteConfirm.value = false
    deleteTarget.value = null
    await loadBills()
  } catch (e) {
    alert((e as Error).message)
  } finally {
    deleting.value = false
  }
}

// ---- Misc ----
function fmt(n: number) { return n.toFixed(2) }

function toggleDay(group: DayGroup) { group.expanded = !group.expanded }

onMounted(async () => {
  const savedTheme = localStorage.getItem('theme')
  if (savedTheme) {
    isDark.value = savedTheme === 'dark'
  } else {
    isDark.value = !document.documentElement.classList.contains('theme-light')
  }
  updateThemeClass()

  try {
    await loadTags()
  } catch (e) {
    console.error(e)
    loadError.value = (e as Error).message
  }
  await syncMonthToLatestBill()
  await loadBills()
  bootstrapping.value = false
})
</script>

<template>
  <div class="min-h-screen bg-surface pb-24">
    <!-- Top bar -->
    <header class="sticky top-0 z-20 bg-surface/80 backdrop-blur-md border-b border-border px-6 py-4 flex items-center gap-4">
      <button @click="router.push('/')" class="flex items-center gap-2 text-text-muted hover:text-text transition-colors duration-200">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
        </svg>
        <span class="text-sm">Dashboard</span>
      </button>
      <span class="text-border">|</span>
      <h1 class="text-sm font-medium text-text">记账</h1>
      <div class="ml-auto flex items-center gap-3">
        <button @click="toggleTheme" type="button"
          class="flex items-center justify-center w-8 h-8 rounded-lg border border-border text-text-muted hover:text-text hover:border-primary/50 transition-colors duration-200 btn-tactile"
          aria-label="Toggle theme">
          <span class="text-base leading-none">{{ isDark ? '☾' : '☼' }}</span>
        </button>
        <button @click="openCreate"
          class="flex items-center gap-2 px-4 py-1.5 rounded-lg bg-primary text-white text-sm font-medium
                 hover:bg-primary-dark transition-colors duration-200 btn-tactile">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          新增记录
        </button>
      </div>
    </header>

    <div class="max-w-2xl mx-auto px-4 pt-8">
      <!-- Month navigator -->
      <div class="flex items-center justify-between mb-6">
        <button @click="prevMonth"
          class="w-9 h-9 rounded-xl border border-border flex items-center justify-center text-text-muted
                 hover:border-primary/50 hover:text-text transition-all duration-200 btn-tactile">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <span class="text-lg font-semibold text-text tracking-wide">{{ monthLabel }}</span>
        <button @click="nextMonth" :disabled="isCurrentMonth"
          class="w-9 h-9 rounded-xl border border-border flex items-center justify-center text-text-muted
                 hover:border-primary/50 hover:text-text transition-all duration-200 btn-tactile
                 disabled:opacity-30 disabled:cursor-not-allowed">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
          </svg>
        </button>
      </div>

      <!-- Monthly summary card -->
      <div class="rounded-2xl border border-border bg-surface-card p-5 mb-8">
        <div class="grid grid-cols-3 gap-4">
          <div class="text-center">
            <div class="text-xs text-text-muted mb-1">收入</div>
            <div class="text-xl font-bold text-income">+{{ fmt(monthlySummary.income) }}</div>
          </div>
          <div class="text-center border-x border-border">
            <div class="text-xs text-text-muted mb-1">结余</div>
            <div class="text-xl font-bold" :class="monthlySummary.net >= 0 ? 'text-income' : 'text-expense'">
              {{ monthlySummary.net >= 0 ? '+' : '' }}{{ fmt(monthlySummary.net) }}
            </div>
          </div>
          <div class="text-center">
            <div class="text-xs text-text-muted mb-1">支出</div>
            <div class="text-xl font-bold text-expense">-{{ fmt(monthlySummary.expense) }}</div>
          </div>
        </div>
        <div v-if="monthlySummary.income > 0" class="mt-4">
          <div class="h-1.5 rounded-full bg-surface-light overflow-hidden">
            <div class="h-full rounded-full bg-gradient-to-r from-rose-500 to-rose-400 transition-all duration-500"
              :style="{ width: Math.min(100, (monthlySummary.expense / monthlySummary.income) * 100) + '%' }"></div>
          </div>
          <div class="flex justify-between mt-1 text-xs text-text-muted">
            <span>支出占收入 {{ Math.round((monthlySummary.expense / monthlySummary.income) * 100) }}%</span>
            <span>本月收入 {{ fmt(monthlySummary.income) }}</span>
          </div>
        </div>
      </div>

      <div v-if="loadError" class="mb-4 rounded-2xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
        数据读取失败：{{ loadError }}
      </div>

      <!-- Loading -->
      <div v-if="loading" class="text-center text-text-muted py-20 text-sm">加载中...</div>

      <!-- Empty -->
      <div v-else-if="dayGroups.length === 0" class="text-center text-text-muted py-20 text-sm">本月暂无记录</div>

      <!-- Day cards -->
      <div v-else class="space-y-3">
        <div v-for="(group, index) in dayGroups" :key="group.date"
          class="rounded-2xl border border-border bg-surface-card overflow-hidden transition-all duration-200 hover:border-primary/30 waterfall-item"
          :style="{ animationDelay: `${index * 45}ms` }">
          <!-- Day header -->
          <button class="w-full flex items-center gap-4 px-5 py-4 hover:bg-surface-light/50 transition-colors duration-150"
            @click="toggleDay(group)">
            <div class="flex-shrink-0 w-12 text-center">
              <div class="text-base font-bold text-text leading-none">{{ group.dateLabel }}</div>
              <div class="text-xs text-text-muted mt-0.5">{{ group.weekDay }}</div>
            </div>
            <div class="flex-1 flex items-center justify-end gap-4">
              <span v-if="group.totalIncome > 0" class="text-sm text-income font-medium">+{{ fmt(group.totalIncome) }}</span>
              <span v-if="group.totalExpense > 0" class="text-sm text-expense font-medium">-{{ fmt(group.totalExpense) }}</span>
              <svg class="w-4 h-4 text-text-muted transition-transform duration-300" :class="group.expanded ? 'rotate-180' : ''"
                fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </button>

          <!-- Bill items -->
          <div v-show="group.expanded" class="border-t border-border divide-y divide-border/60">
            <div v-for="item in group.items" :key="item.id"
              class="flex items-center gap-3 px-5 py-3 hover:bg-surface-light/30 transition-colors duration-150 group/row">
              <div class="w-2 h-2 rounded-full flex-shrink-0"
                :class="item.record_type === '收入' ? 'bg-income' : 'bg-expense'"></div>
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                  <span class="text-sm font-medium text-text truncate">
                    {{ item.subcategory?.name ?? item.category?.name ?? '-' }}
                  </span>
                  <span v-if="item.subcategory" class="text-xs text-text-muted bg-surface-light px-1.5 py-0.5 rounded-md flex-shrink-0">
                    {{ item.category?.name }}
                  </span>
                </div>
                <div class="text-xs text-text-muted mt-0.5 truncate">
                  {{ item.note ?? '' }}
                  <span v-if="item.payment_platform" class="opacity-60">{{ item.note ? ' · ' : '' }}{{ item.payment_platform.name }}</span>
                </div>
              </div>
              <div class="text-right flex-shrink-0">
                <div class="text-sm font-semibold tabular-nums" :class="item.record_type === '收入' ? 'text-income' : 'text-text'">
                  {{ item.record_type === '收入' ? '+' : '-' }}{{ fmt(parseFloat(item.amount)) }}
                </div>
                <div class="text-xs text-text-muted mt-0.5">{{ item.expense_time?.slice(0, 5) ?? '' }}</div>
              </div>
              <!-- Row actions (shown on hover) -->
              <div class="flex-shrink-0 flex gap-1 opacity-0 group-hover/row:opacity-100 transition-opacity duration-150">
                <button @click="openEdit(item)"
                  class="w-7 h-7 rounded-lg flex items-center justify-center text-text-muted hover:text-primary hover:bg-primary/10 transition-colors duration-150">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                </button>
                <button @click="confirmDelete(item)"
                  class="w-7 h-7 rounded-lg flex items-center justify-center text-text-muted hover:text-expense hover:bg-expense-bg transition-colors duration-150">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Add/Edit Modal -->
    <Teleport to="body">
      <div v-if="showModal" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="closeModal"></div>
        <div class="relative w-full max-w-md bg-surface-card rounded-2xl border border-border shadow-2xl overflow-hidden">
          <div class="flex items-center justify-between px-6 py-4 border-b border-border">
            <h2 class="font-semibold text-text">{{ editingBill ? '编辑记录' : '新增记录' }}</h2>
            <button @click="closeModal" class="text-text-muted hover:text-text transition-colors">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <form @submit.prevent="saveForm" class="px-6 py-5 space-y-4 overflow-y-auto max-h-[70vh]">
            <!-- Record type -->
            <div class="flex gap-2">
              <button type="button" v-for="t in ['支出', '收入']" :key="t"
                @click="form.record_type = t as '支出' | '收入'"
                class="flex-1 py-2 rounded-xl text-sm font-medium border transition-all duration-150"
                :class="form.record_type === t
                  ? (t === '支出' ? 'bg-expense-bg border-expense-border text-expense-text-btn' : 'bg-income-bg border-income-border text-income-text-btn')
                  : 'border-border text-text-muted hover:border-primary/30'">
                {{ t }}
              </button>
            </div>

            <!-- Date & Time -->
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-xs text-text-muted mb-1.5">日期</label>
                <input v-model="form.expense_date" type="date" required
                  class="w-full bg-surface-light border border-border rounded-xl px-3 py-2 text-sm text-text
                         focus:outline-none focus:border-primary/50 transition-colors" />
              </div>
              <div>
                <label class="block text-xs text-text-muted mb-1.5">时间（选填）</label>
                <input v-model="form.expense_time" type="time"
                  class="w-full bg-surface-light border border-border rounded-xl px-3 py-2 text-sm text-text
                         focus:outline-none focus:border-primary/50 transition-colors" />
              </div>
            </div>

            <!-- Amount -->
            <div>
              <label class="block text-xs text-text-muted mb-1.5">金额</label>
              <input v-model="form.amount" type="number" step="0.01" min="0.01" required placeholder="0.00"
                class="w-full bg-surface-light border border-border rounded-xl px-3 py-2 text-sm text-text
                       focus:outline-none focus:border-primary/50 transition-colors" />
            </div>

            <!-- Category -->
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-xs text-text-muted mb-1.5">大类</label>
                <select v-model="form.category_id"
                  class="w-full bg-surface-light border border-border rounded-xl px-3 py-2 text-sm text-text
                         focus:outline-none focus:border-primary/50 transition-colors">
                  <option :value="null">-- 选择 --</option>
                  <option v-for="t in categoryTags" :key="t.id" :value="t.id">{{ t.name }}</option>
                </select>
              </div>
              <div>
                <label class="block text-xs text-text-muted mb-1.5">小类（选填）</label>
                <select v-model="form.subcategory_id" :disabled="!subcategoryOptions.length"
                  class="w-full bg-surface-light border border-border rounded-xl px-3 py-2 text-sm text-text
                         focus:outline-none focus:border-primary/50 transition-colors disabled:opacity-40">
                  <option :value="null">-- 选择 --</option>
                  <option v-for="t in subcategoryOptions" :key="t.id" :value="t.id">{{ t.name }}</option>
                </select>
              </div>
            </div>

            <!-- Payment info (only for expense) -->
            <template v-if="form.record_type === '支出'">
              <div>
                <label class="block text-xs text-text-muted mb-1.5">支付平台（选填）</label>
                <select v-model="form.payment_platform_id"
                  class="w-full bg-surface-light border border-border rounded-xl px-3 py-2 text-sm text-text
                         focus:outline-none focus:border-primary/50 transition-colors">
                  <option :value="null">-- 选择 --</option>
                  <option v-for="t in platformTags" :key="t.id" :value="t.id">{{ t.name }}</option>
                </select>
              </div>
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="block text-xs text-text-muted mb-1.5">支付通道（选填）</label>
                  <select v-model="form.payment_channel_id"
                    class="w-full bg-surface-light border border-border rounded-xl px-3 py-2 text-sm text-text
                           focus:outline-none focus:border-primary/50 transition-colors">
                    <option :value="null">-- 选择 --</option>
                    <option v-for="t in channelTags" :key="t.id" :value="t.id">{{ t.name }}</option>
                  </select>
                </div>
                <div>
                  <label class="block text-xs text-text-muted mb-1.5">资金类型（选填）</label>
                  <select v-model="form.fund_type_id"
                    class="w-full bg-surface-light border border-border rounded-xl px-3 py-2 text-sm text-text
                           focus:outline-none focus:border-primary/50 transition-colors">
                    <option :value="null">-- 选择 --</option>
                    <option v-for="t in fundTags" :key="t.id" :value="t.id">{{ t.name }}</option>
                  </select>
                </div>
              </div>
            </template>

            <!-- Note -->
            <div>
              <label class="block text-xs text-text-muted mb-1.5">备注（选填）</label>
              <input v-model="form.note" type="text" placeholder="买了什么、去哪里..."
                class="w-full bg-surface-light border border-border rounded-xl px-3 py-2 text-sm text-text
                       focus:outline-none focus:border-primary/50 transition-colors" />
            </div>

            <button type="submit" :disabled="saving"
              class="w-full py-2.5 rounded-xl bg-primary text-white text-sm font-medium
                     hover:bg-primary-dark transition-colors duration-200 btn-tactile
                     disabled:opacity-50 disabled:cursor-not-allowed">
              {{ saving ? '保存中...' : (editingBill ? '保存修改' : '添加记录') }}
            </button>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Delete confirm -->
    <Teleport to="body">
      <div v-if="showDeleteConfirm" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="showDeleteConfirm = false"></div>
        <div class="relative w-full max-w-sm bg-surface-card rounded-2xl border border-border shadow-2xl p-6">
          <h3 class="font-semibold text-text mb-2">确认删除</h3>
          <p class="text-sm text-text-muted mb-6">
             删除
            <span class="text-text font-medium">
              {{ deleteTarget?.subcategory?.name ?? deleteTarget?.category?.name ?? '该记录' }}
            </span>
             ，金额
            <span class="text-expense font-medium tabular-nums">
              {{ deleteTarget ? fmt(parseFloat(deleteTarget.amount)) : '' }}
            </span>
             ，此操作不可撤销。
          </p>
          <div class="flex gap-3">
            <button @click="showDeleteConfirm = false"
              class="flex-1 py-2 rounded-xl border border-border text-text-muted text-sm hover:border-primary/30 transition-colors btn-tactile">
              取消
            </button>
            <button @click="doDelete" :disabled="deleting"
              class="flex-1 py-2 rounded-xl bg-rose-500 text-white text-sm font-medium
                     hover:bg-rose-600 transition-colors disabled:opacity-50 btn-tactile">
              {{ deleting ? '删除中...' : '确认删除' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
select option {
  background-color: var(--surface-card);
  color: var(--text);
}
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
</style>
