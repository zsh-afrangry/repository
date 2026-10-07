<script setup lang="ts">
/**
 * 天气地点选择器。
 *
 * 职责边界：只负责"选一个地点并把 Location ID 报出去"，不取天气、不碰 localStorage。
 * 当前选中项由 `currentLabel` 受控传入，持久化留在使用方（Dashboard）。
 *
 * 交互约定：点击触发按钮展开；输入框做 300ms 去抖后搜索；↑↓ 在候选间移动、
 * Enter 选中、Esc 关闭并把焦点还给触发按钮；点击外部关闭。
 */
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { weatherApi } from '@/api/weather'
import type { WeatherLocation } from '@/types/portal'

const props = defineProps<{
  /** 当前地点的展示名，例如「广东省 · 广州市 · 天河区」。 */
  currentLabel: string
  /** 正在读取天气时为 true，按钮显示忙碌态。 */
  busy?: boolean
}>()

const emit = defineEmits<{
  (e: 'select', location: WeatherLocation): void
}>()

/** 常用城市，全部是 QWeather 官方 Location ID，不走搜索、不额外消耗 geo 配额。 */
const PRESETS: WeatherLocation[] = [
  { id: '101280109', name: '天河区', label: '广东省 · 广州市 · 天河区', lat: '23.14', lon: '113.34' },
  { id: '101280101', name: '广州', label: '广东省 · 广州市', lat: '23.13', lon: '113.26' },
  { id: '101280601', name: '深圳', label: '广东省 · 深圳市', lat: '22.55', lon: '114.06' },
  { id: '101010100', name: '北京', label: '北京市', lat: '39.90', lon: '116.41' },
  { id: '101020100', name: '上海', label: '上海市', lat: '31.23', lon: '121.47' },
  { id: '101210101', name: '杭州', label: '浙江省 · 杭州市', lat: '30.29', lon: '120.16' },
]

const root = ref<HTMLElement | null>(null)
const trigger = ref<HTMLButtonElement | null>(null)
const input = ref<HTMLInputElement | null>(null)

const open = ref(false)
const keyword = ref('')
const results = ref<WeatherLocation[]>([])
const searching = ref(false)
const error = ref('')
const activeIndex = ref(-1)

/** 关键词为空时展示预设，否则展示搜索结果。 */
const options = computed<WeatherLocation[]>(() =>
  keyword.value.trim() ? results.value : PRESETS,
)

let debounceTimer: ReturnType<typeof setTimeout> | null = null
let requestTicket = 0

function clearDebounce() {
  if (debounceTimer !== null) {
    clearTimeout(debounceTimer)
    debounceTimer = null
  }
}

async function runSearch(text: string) {
  const ticket = ++requestTicket
  searching.value = true
  error.value = ''
  try {
    const payload = await weatherApi.searchLocations(text)
    if (ticket !== requestTicket) return
    results.value = payload?.locations ?? []
    activeIndex.value = results.value.length ? 0 : -1
    if (!results.value.length) error.value = '没有找到匹配的城市。'
  } catch (e) {
    if (ticket !== requestTicket) return
    results.value = []
    activeIndex.value = -1
    error.value = e instanceof Error ? e.message : '城市搜索失败。'
  } finally {
    if (ticket === requestTicket) searching.value = false
  }
}

watch(keyword, value => {
  clearDebounce()
  requestTicket++
  const text = value.trim()
  if (!text) {
    results.value = []
    error.value = ''
    searching.value = false
    activeIndex.value = -1
    return
  }
  debounceTimer = setTimeout(() => void runSearch(text), 300)
})

function toggle() {
  if (open.value) close()
  else void show()
}

async function show() {
  open.value = true
  await nextTick()
  input.value?.focus()
}

function close(restoreFocus = true) {
  open.value = false
  keyword.value = ''
  results.value = []
  error.value = ''
  activeIndex.value = -1
  clearDebounce()
  // preventScroll 是必须的：默认的 focus() 会调用 scrollIntoView，把触发按钮滚进视野。
  // 这个按钮在卡片右侧，一旦页面存在任何横向可滚动量，就会把页面横向滚走；
  // 表现为"切换地区后整张卡片错位"、刷新即恢复。焦点该给，但滚动不该被它牵动。
  if (restoreFocus) trigger.value?.focus({ preventScroll: true })
}

function choose(location: WeatherLocation) {
  emit('select', location)
  close()
}

function move(delta: number) {
  const total = options.value.length
  if (!total) return
  activeIndex.value = (activeIndex.value + delta + total) % total
}

function confirmActive() {
  const picked = options.value[activeIndex.value]
  if (picked) choose(picked)
}

function onInputKeydown(event: KeyboardEvent) {
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    move(1)
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    move(-1)
  } else if (event.key === 'Enter') {
    event.preventDefault()
    confirmActive()
  } else if (event.key === 'Escape') {
    event.preventDefault()
    close()
  }
}

function onDocumentPointerDown(event: PointerEvent) {
  if (!open.value) return
  const node = root.value
  if (node && event.target instanceof Node && !node.contains(event.target)) close(false)
}

function onDocumentKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && open.value) close()
}

onBeforeUnmount(() => {
  clearDebounce()
  document.removeEventListener('pointerdown', onDocumentPointerDown)
  document.removeEventListener('keydown', onDocumentKeydown)
})

watch(open, value => {
  if (value) {
    document.addEventListener('pointerdown', onDocumentPointerDown)
    document.addEventListener('keydown', onDocumentKeydown)
  } else {
    document.removeEventListener('pointerdown', onDocumentPointerDown)
    document.removeEventListener('keydown', onDocumentKeydown)
  }
})
</script>

<template>
  <div ref="root" class="weather-location">
    <button
      ref="trigger"
      type="button"
      class="weather-location-trigger"
      :aria-expanded="open"
      aria-haspopup="dialog"
      :title="`当前地点：${props.currentLabel}（点击切换）`"
      @click="toggle"
      @keydown.esc="close()"
    >
      <span aria-hidden="true">📍</span>
      <span class="weather-location-label">{{ props.currentLabel }}</span>
      <span v-if="props.busy" class="weather-location-busy" aria-hidden="true">…</span>
      <span class="weather-location-caret" aria-hidden="true">▾</span>
    </button>

    <div v-if="open" class="weather-location-menu" role="dialog" aria-label="切换天气地点">
      <label class="weather-location-search">
        <span class="visually-hidden">搜索城市</span>
        <input
          ref="input"
          v-model="keyword"
          type="search"
          placeholder="搜索城市，例如 成都 / 三亚"
          autocomplete="off"
          @keydown="onInputKeydown"
        />
      </label>

      <p v-if="searching" class="weather-location-status" role="status">正在搜索…</p>
      <p v-else-if="error" class="weather-location-status is-error" role="alert">{{ error }}</p>

      <ul v-if="options.length" class="weather-location-list" role="listbox">
        <li v-for="(place, index) in options" :key="place.id">
          <button
            type="button"
            role="option"
            :aria-selected="index === activeIndex"
            :class="{ 'is-active': index === activeIndex }"
            @click="choose(place)"
            @mousemove="activeIndex = index"
          >
            <span class="weather-location-option-label">{{ place.label }}</span>
            <span class="weather-location-option-id">{{ place.id }}</span>
          </button>
        </li>
      </ul>
      <p v-else-if="!searching && !error" class="weather-location-status">
        直接点上面的常用城市，或输入关键词搜索。
      </p>
    </div>
  </div>
</template>

<style scoped>
.weather-location {
  position: relative;
  display: inline-block;
  max-width: 100%;
  /* flex 子项默认 min-width:auto，长地名会把父容器顶宽；显式归零让它按 ellipsis 收缩。 */
  min-width: 0;
}

.weather-location-trigger {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  max-width: 100%;
  min-width: 0;
  padding: 2px 6px;
  border: 1px solid transparent;
  border-radius: 6px;
  background: transparent;
  color: inherit;
  font: inherit;
  cursor: pointer;
  transition: border-color 0.16s ease, background-color 0.16s ease;
}

.weather-location-trigger:hover {
  border-color: rgba(148, 163, 184, 0.35);
  background: rgba(148, 163, 184, 0.1);
}

.weather-location-trigger:focus-visible {
  outline: 2px solid var(--primary-btn-border, #67e8f9);
  outline-offset: 2px;
}

.weather-location-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.weather-location-caret {
  font-size: 0.7em;
  opacity: 0.7;
}

.weather-location-busy {
  opacity: 0.7;
}

.weather-location-menu {
  position: absolute;
  top: calc(100% + 6px);
  /* 右对齐：触发按钮在卡片/页头的右侧，菜单若从 left:0 向右铺开，会顶到视口右边。
     锚定右边缘后无论多宽都往左展开，不与视口争空间。 */
  right: 0;
  z-index: 40;
  width: min(22rem, calc(100vw - 2.5rem));
  padding: 10px;
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-radius: 10px;
  background: #0f172a;
  box-shadow: 0 18px 45px rgb(0 0 0 / 0.45);
  text-align: left;
}

.weather-location-search input {
  width: 100%;
  padding: 7px 9px;
  border: 1px solid rgba(148, 163, 184, 0.3);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.85);
  color: inherit;
  font: inherit;
}

.weather-location-search input:focus-visible {
  outline: 2px solid var(--primary-btn-border, #67e8f9);
  outline-offset: 1px;
}

.weather-location-status {
  margin: 8px 2px 2px;
  color: #9aa7bd;
  font-size: 0.78rem;
  line-height: 1.5;
}

.weather-location-status.is-error {
  color: #fda4af;
}

.weather-location-list {
  max-height: 15rem;
  margin: 8px 0 0;
  padding: 0;
  overflow-y: auto;
  list-style: none;
}

.weather-location-list button {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 7px 8px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.weather-location-list button.is-active {
  background: rgba(148, 163, 184, 0.16);
}

.weather-location-list button:focus-visible {
  outline: 2px solid var(--primary-btn-border, #67e8f9);
  outline-offset: -2px;
}

.weather-location-option-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.weather-location-option-id {
  flex-shrink: 0;
  color: #7c8aa3;
  font-size: 0.72rem;
}

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  padding: 0;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
  border: 0;
}

@media (prefers-reduced-motion: reduce) {
  .weather-location-trigger {
    transition: none;
  }
}
</style>
