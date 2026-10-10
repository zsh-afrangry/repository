<script setup lang="ts">
/**
 * 学习路线图谱组件 (NotesGraph.vue)
 *
 * 对应文档：docs/16_Notes学习模块视觉重构与体验优化方案.md
 */
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import GridDecoration from '../../../components/ui/GridDecoration.vue';
import type { NoteTopic } from '../types';
import { notesAppearance } from '../config/appearance';

const props = defineProps<{
  topic: NoteTopic;
  selected: string;
  matches: string[];
}>();

const emit = defineEmits<{
  select: [id: string];
}>();

const sections = computed(() =>
  [...props.topic.sections].sort((a, b) => a.order - b.order || a.id.localeCompare(b.id))
);

const columns = computed(() =>
  sections.value.map(s => ({
    ...s,
    units: props.topic.units.filter(u => u.sectionId === s.id)
  }))
);

const colWidth = 260;
const rowHeight = 78;
const width = computed(() => Math.max(1, columns.value.length) * colWidth);
const height = computed(() => Math.max(480, 130 + Math.max(0, ...columns.value.map(c => c.units.length)) * rowHeight));

const nodes = computed(() =>
  columns.value.flatMap((s, i) =>
    s.units.map((u, j) => ({
      ...u,
      colIdx: i,
      rowIdx: j,
      idx: j + 1,
      x: 130 + i * colWidth,
      y: 110 + j * rowHeight
    }))
  )
);

// 依赖关系双向解析（前置 Cyan、后置 Violet）
const predecessors = computed(() =>
  new Set(props.topic.edges.filter(e => e.toUnitId === props.selected).map(e => e.fromUnitId))
);

const successors = computed(() =>
  new Set(props.topic.edges.filter(e => e.fromUnitId === props.selected).map(e => e.toUnitId))
);

const hasSelection = computed(() => Boolean(props.selected));

type GraphNode = (typeof nodes.value)[0];

// 节点半宽为 104px (宽 208px)，半高为 24px (高 48px)
const nodeHalfWidth = 104;
const nodeHalfHeight = 24;

function computeEdgePath(a: GraphNode, b: GraphNode): string {
  // 1. 同列连接 (Same Column: a.colIdx === b.colIdx)
  if (a.colIdx === b.colIdx) {
    const isAdjacent = Math.abs(b.rowIdx - a.rowIdx) === 1;
    if (isAdjacent) {
      // 相邻上下节点：笔直垂直连接，消除弯曲失真
      const isDown = b.rowIdx > a.rowIdx;
      const startY = isDown ? a.y + nodeHalfHeight : a.y - nodeHalfHeight;
      const endY = isDown ? b.y - nodeHalfHeight : b.y + nodeHalfHeight;
      return `M ${a.x},${startY} L ${b.x},${endY}`;
    }

    // 跨多行（避开中间阻隔节点）：从右侧端口平滑外绕
    const startX = a.x + nodeHalfWidth;
    const startY = a.y;
    const endX = b.x + nodeHalfWidth;
    const endY = b.y;
    const offset = Math.min(48, 28 + Math.abs(b.rowIdx - a.rowIdx) * 6);
    return `M ${startX},${startY} C ${startX + offset},${startY} ${endX + offset},${endY} ${endX},${endY}`;
  }

  // 2. 从左至右跨列连接 (b.colIdx > a.colIdx)
  if (b.colIdx > a.colIdx) {
    const startX = a.x + nodeHalfWidth;
    const startY = a.y;
    const endX = b.x - nodeHalfWidth;
    const endY = b.y;
    const dx = endX - startX;
    // 相邻列 dx 约 52px，张力保证控制点不交叉，呈现丝滑单调递增 S 曲线
    const tension = Math.min(90, Math.max(24, dx * 0.45));
    return `M ${startX},${startY} C ${startX + tension},${startY} ${endX - tension},${endY} ${endX},${endY}`;
  }

  // 3. 反向/回流连接 (b.colIdx < a.colIdx)
  const startX = a.x - nodeHalfWidth;
  const startY = a.y;
  const endX = b.x + nodeHalfWidth;
  const endY = b.y;
  const dx = Math.abs(startX - endX);
  const tension = Math.min(80, Math.max(28, dx * 0.35));
  return `M ${startX},${startY} C ${startX - tension},${startY} ${endX + tension},${endY} ${endX},${endY}`;
}

const lines = computed(() => {
  const result = props.topic.edges.flatMap(e => {
    const a = nodes.value.find(n => n.id === e.fromUnitId);
    const b = nodes.value.find(n => n.id === e.toUnitId);
    if (!a || !b) return [];

    const path = computeEdgePath(a, b);
    const isIncoming = e.toUnitId === props.selected;
    const isOutgoing = e.fromUnitId === props.selected;
    const isDimmed = hasSelection.value && !isIncoming && !isOutgoing;

    return [
      {
        ...e,
        path,
        isIncoming,
        isOutgoing,
        isDimmed,
        active: isIncoming || isOutgoing
      }
    ];
  });

  // 激活的高亮流光线置于最顶层，不被暗色连线压盖
  return result.sort((a, b) => (a.active ? 1 : 0) - (b.active ? 1 : 0));
});

// --- 画布自由平移 (Pan) 与 缩放 (Zoom) ---
const graphScrollRef = ref<HTMLElement | null>(null);
const zoom = ref(1.0);
const panX = ref(0);
const panY = ref(0);
const isDragging = ref(false);
let startX = 0;
let startY = 0;
let initialPanX = 0;
let initialPanY = 0;

function handleWheel(e: WheelEvent) {
  if (e.ctrlKey || e.metaKey) {
    e.preventDefault();
    const delta = e.deltaY < 0 ? 0.1 : -0.1;
    zoom.value = Math.min(2.0, Math.max(0.6, Number((zoom.value + delta).toFixed(2))));
  }
}

function zoomIn() {
  zoom.value = Math.min(2.0, Number((zoom.value + 0.15).toFixed(2)));
}

function zoomOut() {
  zoom.value = Math.max(0.6, Number((zoom.value - 0.15).toFixed(2)));
}

function resetViewport() {
  zoom.value = 1.0;
  panX.value = 0;
  panY.value = 0;
}

function fitCanvas() {
  if (!graphScrollRef.value) return;
  const containerWidth = graphScrollRef.value.clientWidth;
  if (!containerWidth) return;
  const targetWidth = width.value;
  // 留出两侧 32px 边距
  const available = containerWidth - 36;
  const scale = Math.min(1.0, Math.max(0.6, Number((available / targetWidth).toFixed(2))));
  zoom.value = scale;
  if (targetWidth * scale < containerWidth) {
    panX.value = Math.round((containerWidth - targetWidth * scale) / 2);
  } else {
    panX.value = 16;
  }
  panY.value = 16;
}

function handleMouseDown(e: MouseEvent) {
  if ((e.target as HTMLElement).closest('.graph-node') || (e.target as HTMLElement).closest('.graph-controls')) return;
  isDragging.value = true;
  startX = e.clientX;
  startY = e.clientY;
  initialPanX = panX.value;
  initialPanY = panY.value;
  window.addEventListener('mousemove', handleMouseMove);
  window.addEventListener('mouseup', handleMouseUp);
}

function handleMouseMove(e: MouseEvent) {
  if (!isDragging.value) return;
  panX.value = initialPanX + (e.clientX - startX);
  panY.value = initialPanY + (e.clientY - startY);
}

function handleMouseUp() {
  isDragging.value = false;
  window.removeEventListener('mousemove', handleMouseMove);
  window.removeEventListener('mouseup', handleMouseUp);
}

onMounted(() => {
  // 视口初次挂载时，若容器空间受限，自动触发一次适应画布
  if (graphScrollRef.value && graphScrollRef.value.clientWidth < width.value) {
    fitCanvas();
  }
});

onBeforeUnmount(() => {
  window.removeEventListener('mousemove', handleMouseMove);
  window.removeEventListener('mouseup', handleMouseUp);
});

defineExpose({
  fitCanvas,
  zoomIn,
  zoomOut,
  resetViewport,
  zoom
});
</script>

<template>
<div
  ref="graphScrollRef"
  class="graph-scroll"
  tabindex="0"
  role="region"
  aria-label="学习路线图，可拖拽平移与滚轮缩放"
  data-lenis-prevent
  :class="{ 'is-grabbing': isDragging }"
  @mousedown="handleMouseDown"
  @wheel="handleWheel"
>
  <!-- 视口操作浮动控制栏 -->
  <div class="graph-controls">
    <button type="button" class="ctrl-btn" title="放大 (Ctrl+滚轮)" @click="zoomIn">+</button>
    <span class="zoom-text">{{ Math.round(zoom * 100) }}%</span>
    <button type="button" class="ctrl-btn" title="缩小" @click="zoomOut">-</button>
    <button type="button" class="ctrl-btn fit-btn" title="自动适应画布宽度" @click="fitCanvas">⤢ 适应画布</button>
    <button type="button" class="ctrl-btn reset-btn" title="重置画布 100%" @click="resetViewport">1:1 复位</button>
  </div>

  <div
    class="graph-viewport-stage"
    :style="{
      transform: `translate(${panX}px, ${panY}px) scale(${zoom})`,
      transformOrigin: 'top left'
    }"
  >
    <div class="graph" :style="{ width: `${width}px`, height: `${height}px` }">
      <GridDecoration v-if="notesAppearance.graphGrid" />

      <!-- 分层阶段底带 (Layer Bands) -->
      <div
        class="layer-bands"
        aria-hidden="true"
        :style="{ gridTemplateColumns: `repeat(${Math.max(1, columns.length)}, ${colWidth}px)` }"
      >
        <div v-for="s in columns" :key="s.id" class="band-column" />
      </div>

      <!-- 分类标题 -->
      <div
        class="graph-heading"
        :style="{ gridTemplateColumns: `repeat(${Math.max(1, columns.length)}, ${colWidth}px)` }"
      >
        <span v-for="s in columns" :key="s.id" :title="s.title">
          {{ s.title }}
        </span>
      </div>

      <!-- SVG 贝塞尔流光连线 -->
      <svg :viewBox="`0 0 ${width} ${height}`" preserveAspectRatio="none" aria-hidden="true">
        <defs>
          <!-- 默认箭头 -->
          <marker id="arrow-default" markerWidth="9" markerHeight="7" refX="8" refY="3.5" orient="auto" markerUnits="userSpaceOnUse">
            <path d="M0,0 L9,3.5 L0,7 Z" fill="rgba(148, 163, 184, 0.45)" />
          </marker>
          <!-- 前置连线箭头（青色） -->
          <marker id="arrow-incoming" markerWidth="9" markerHeight="7" refX="8" refY="3.5" orient="auto" markerUnits="userSpaceOnUse">
            <path d="M0,0 L9,3.5 L0,7 Z" fill="#06b6d4" />
          </marker>
          <!-- 后置连线箭头（紫色） -->
          <marker id="arrow-outgoing" markerWidth="9" markerHeight="7" refX="8" refY="3.5" orient="auto" markerUnits="userSpaceOnUse">
            <path d="M0,0 L9,3.5 L0,7 Z" fill="#c084fc" />
          </marker>
        </defs>

        <path
          v-for="edge in lines"
          :key="`${edge.fromUnitId}-${edge.toUnitId}`"
          :d="edge.path"
          class="edge-path"
          :class="{
            'edge-incoming': edge.isIncoming,
            'edge-outgoing': edge.isOutgoing,
            'edge-dimmed': edge.isDimmed
          }"
          :marker-end="
            edge.isIncoming
              ? 'url(#arrow-incoming)'
              : edge.isOutgoing
                ? 'url(#arrow-outgoing)'
                : 'url(#arrow-default)'
          "
        />
      </svg>

      <!-- 科技胶囊节点 (Capsule Nodes) -->
      <button
        v-for="node in nodes"
        :key="node.id"
        class="graph-node"
        :class="{
          'selected': selected === node.id,
          'is-predecessor': predecessors.has(node.id),
          'is-successor': successors.has(node.id),
          'is-dimmed': hasSelection && selected !== node.id && !predecessors.has(node.id) && !successors.has(node.id),
          'dim': !matches.includes(node.id)
        }"
        :style="{ left: `${node.x}px`, top: `${node.y}px` }"
        :title="node.title"
        :aria-pressed="selected === node.id"
        @click="emit('select', node.id)"
      >
        <span class="node-badge">{{ String(node.idx).padStart(2, '0') }}</span>
        <span class="node-title">{{ node.title }}</span>
        <span class="node-indicator" aria-hidden="true" />
      </button>

      <p v-if="!nodes.length" class="empty">
        这个主题还没有知识单元。
      </p>
    </div>
  </div>
</div>
</template>

<style scoped>
.graph-scroll {
  position: relative;
  max-width: 100%;
  min-height: 480px;
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 18px;
  background: rgba(10, 15, 29, 0.7);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  cursor: grab;
  user-select: none;
  box-shadow: 0 12px 36px rgba(0, 0, 0, 0.35);
}
.graph-scroll.is-grabbing {
  cursor: grabbing;
}
.graph-scroll:focus-visible {
  outline: 2px solid #8b5cf6;
  outline-offset: -2px;
}

/* 浮动缩放控制面板 */
.graph-controls {
  position: absolute;
  top: 16px;
  right: 16px;
  z-index: 20;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px;
  border-radius: 10px;
  background: rgba(15, 23, 42, 0.85);
  border: 1px solid rgba(148, 163, 184, 0.2);
  backdrop-filter: blur(14px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
}
.ctrl-btn {
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  border: none;
  background: transparent;
  color: #94a3b8;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.18s ease;
}
.ctrl-btn:hover {
  background: rgba(148, 163, 184, 0.15);
  color: #f8fafc;
}
.zoom-text {
  font-size: 11.5px;
  font-family: ui-monospace, SFMono-Regular, monospace;
  color: #67e8f9;
  padding: 0 6px;
  min-width: 44px;
  text-align: center;
}
.fit-btn {
  width: auto;
  padding: 0 8px;
  font-size: 11px;
  color: #67e8f9;
}
.fit-btn:hover {
  background: rgba(6, 182, 212, 0.16);
  color: #a5f3fc;
}
.reset-btn {
  width: auto;
  padding: 0 8px;
  font-size: 11px;
}

.graph-viewport-stage {
  will-change: transform;
  transition: transform 0.05s linear;
}

.graph {
  position: relative;
}

/* 阶段背景带 (Layer Bands) */
.layer-bands {
  position: absolute;
  inset: 0;
  display: grid;
  pointer-events: none;
}
.band-column {
  border-right: 1px dashed rgba(148, 163, 184, 0.08);
  background: linear-gradient(180deg, rgba(30, 41, 59, 0.08) 0%, transparent 100%);
}
.band-column:last-child {
  border-right: none;
}

/* 分类标题栏 */
.graph-heading {
  display: grid;
  position: relative;
  padding-top: 24px;
  color: #94a3b8;
  font-size: 13px;
  font-weight: 700;
  text-align: center;
  z-index: 2;
}
.graph-heading span {
  padding: 0 16px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.45;
  letter-spacing: 0.02em;
}

/* SVG 连线 */
svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 1;
}
.edge-path {
  fill: none;
  stroke: rgba(148, 163, 184, 0.25);
  stroke-width: 1.6;
  transition: stroke 0.25s ease, stroke-width 0.25s ease, opacity 0.25s ease;
}
.edge-incoming {
  stroke: #06b6d4;
  stroke-width: 2.5;
  filter: drop-shadow(0 0 6px rgba(6, 182, 212, 0.5));
}
.edge-outgoing {
  stroke: #c084fc;
  stroke-width: 2.5;
  filter: drop-shadow(0 0 6px rgba(192, 132, 252, 0.5));
}
.edge-dimmed {
  opacity: 0.15;
}

/* 科技紧凑圆角矩形节点 */
.graph-node {
  position: absolute;
  width: 208px;
  height: 48px;
  display: flex;
  align-items: center;
  gap: 8px;
  transform: translate(-50%, -50%);
  padding: 0 12px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.85);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  color: #e2e8f0;
  font-size: 13px;
  cursor: pointer;
  z-index: 5;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.3);
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1),
              border-color 0.2s ease,
              box-shadow 0.2s ease,
              opacity 0.2s ease,
              background 0.2s ease;
}
.graph-node:hover {
  transform: translate(-50%, -52%) scale(1.025);
  border-color: rgba(139, 92, 246, 0.6);
  background: rgba(30, 41, 59, 0.9);
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.4), 0 0 16px rgba(124, 58, 237, 0.25);
  color: #ffffff;
}
.graph-node:focus-visible {
  outline: 2px solid #8b5cf6;
  outline-offset: 3px;
}

/* 序号等宽徽章 */
.node-badge {
  font-family: ui-monospace, SFMono-Regular, monospace;
  font-size: 11px;
  font-weight: 750;
  color: #67e8f9;
  background: rgba(6, 182, 212, 0.14);
  border: 1px solid rgba(6, 182, 212, 0.28);
  border-radius: 6px;
  padding: 1px 5px;
  flex-shrink: 0;
}

.node-title {
  flex: 1;
  text-align: left;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  font-size: 12.5px;
  line-height: 1.35;
  font-weight: 600;
  word-break: break-word;
}

.node-indicator {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #64748b;
  flex-shrink: 0;
  transition: background 0.2s ease;
}

/* 选中与双向关系状态 */
.graph-node.selected {
  border-color: #f8fafc;
  background: rgba(30, 27, 75, 0.95);
  box-shadow: 0 0 0 2px #a855f7, 0 0 0 4px rgba(6, 182, 212, 0.35), 0 0 28px rgba(168, 85, 247, 0.6);
  color: #ffffff;
}
.graph-node.selected .node-indicator {
  background: #a855f7;
  box-shadow: 0 0 8px #a855f7;
}

.graph-node.is-predecessor {
  border-color: #06b6d4;
  background: rgba(8, 47, 73, 0.85);
  box-shadow: 0 0 0 1.5px rgba(6, 182, 212, 0.6), 0 0 20px rgba(6, 182, 212, 0.45);
}
.graph-node.is-predecessor .node-indicator {
  background: #06b6d4;
  box-shadow: 0 0 8px #06b6d4;
}

.graph-node.is-successor {
  border-color: #c084fc;
  background: rgba(59, 7, 100, 0.85);
  box-shadow: 0 0 0 1.5px rgba(192, 132, 252, 0.6), 0 0 20px rgba(192, 132, 252, 0.45);
}
.graph-node.is-successor .node-indicator {
  background: #c084fc;
  box-shadow: 0 0 8px #c084fc;
}

.graph-node.is-dimmed {
  opacity: 0.22;
}
.graph-node.dim {
  opacity: 0.35;
}

.empty {
  position: relative;
  padding: 100px 24px;
  text-align: center;
  color: #64748b;
  font-size: 14px;
}
</style>
