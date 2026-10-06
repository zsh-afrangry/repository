<script setup lang="ts">
import { computed } from 'vue';
import GridDecoration from '../../../components/ui/GridDecoration.vue';
import type { NoteTopic } from '../types';
import { notesAppearance } from '../config/appearance';
const props = defineProps<{
    topic: NoteTopic;
    selected: string;
    matches: string[];
}>();
const emit = defineEmits<{
    select: [
        id: string
    ];
}>();
const sections = computed(() => [...props.topic.sections].sort((a, b) => a.order - b.order || a.id.localeCompare(b.id)));
const columns = computed(() => sections.value.map(s => ({ ...s, units: props.topic.units.filter(u => u.sectionId === s.id) })));
const width = computed(() => Math.max(1, columns.value.length) * 240);
const height = computed(() => Math.max(280, 100 + Math.max(0, ...columns.value.map(c => c.units.length)) * 90));
const nodes = computed(() => columns.value.flatMap((s, i) => s.units.map((u, j) => ({ ...u, x: 120 + i * 240, y: 110 + j * 90 }))));
const related = computed(() => new Set(props.topic.edges.filter(e => e.fromUnitId === props.selected || e.toUnitId === props.selected).flatMap(e => [e.fromUnitId, e.toUnitId])));
const lines = computed(() => props.topic.edges.flatMap(e => {
    const a = nodes.value.find(n => n.id === e.fromUnitId), b = nodes.value.find(n => n.id === e.toUnitId);
    if (!a || !b)
        return [];
    const direction = b.x >= a.x ? 1 : -1;
    const vertical = b.y >= a.y ? 1 : -1;
    // End at the node edge so arrowheads remain visible instead of hiding under cards.
    const path = a.x === b.x
        ? `M${a.x},${a.y + vertical * 36} C${a.x + 70},${a.y + vertical * 55} ${b.x + 70},${b.y - vertical * 55} ${b.x},${b.y - vertical * 36}`
        : `M${a.x + direction * 94},${a.y} C${a.x + direction * 120},${a.y} ${b.x - direction * 120},${b.y} ${b.x - direction * 94},${b.y}`;
    return [{ ...e, path, active: e.fromUnitId === props.selected || e.toUnitId === props.selected }];
}));
</script>
<template>
<div class="graph-scroll" tabindex="0" role="region" aria-label="学习路线图，可横向滚动" data-lenis-prevent>
  <div class="graph" :style="{width: `${width}px`, height: `${height}px`}">
    <GridDecoration v-if="notesAppearance.graphGrid" />
    <div class="graph-heading" :style="{gridTemplateColumns:`repeat(${Math.max(1,columns.length)}, 240px)`}">
      <span v-for="s in columns" :key="s.id" :title="s.title">
        {{ s.title }}
      </span>
    </div>
    <svg :viewBox="`0 0 ${width} ${height}`" aria-hidden="true">
      <defs>
        <marker id="notes-dependency-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
          <path d="M0,0 L8,4 L0,8 Z" fill="currentColor" />
        </marker>
      </defs>
      <path v-for="edge in lines" :key="`${edge.fromUnitId}-${edge.toUnitId}`" :d="edge.path" :class="{active:edge.active}" marker-end="url(#notes-dependency-arrow)" />
    </svg>
    <button v-for="node in nodes" :key="node.id" class="graph-node" :class="{selected:selected===node.id,related:related.has(node.id),dim:!matches.includes(node.id)}" :style="{left:`${node.x}px`,top:`${node.y}px`}" :title="node.title" :aria-pressed="selected===node.id" @click="emit('select',node.id)">
      <span aria-hidden="true" class="dot">
      </span>
      <span class="node-title">
        {{node.title}}
      </span>
    </button>
    <p v-if="!nodes.length" class="empty">
      这个主题还没有知识单元。
    </p>
  </div>
</div>
</template>
<style scoped>
.graph-scroll {
  max-width: 100%;
  overflow: auto;
  border: 1px solid var(--notes-border);
  border-radius: 12px;
}
.graph-scroll:focus-visible,.graph-node:focus-visible {
  outline: 2px solid var(--ui-focus);
  outline-offset: -3px;
}
.graph {
  position: relative;
  background: var(--notes-canvas);
}
.graph-heading {
  display: grid;
  position: relative;
  padding-top: 18px;
  color: var(--notes-text-muted);
  font-size: 12px;
  text-align: center;
}
.graph-heading span {
  padding: 0 12px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.5;
}
svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  color: var(--notes-accent-highlight);
}
svg>path {
  fill: none;
  stroke: var(--notes-border-strong);
  stroke-width: 1.5;
}
svg>path.active {
  stroke: var(--notes-accent-highlight);
  stroke-width: 2.5;
}
.graph-node {
  position: absolute;
  width: 184px;
  height: 68px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  transform: translate(-50%,-50%);
  padding: 10px;
  border: 1px solid var(--notes-border);
  border-radius: 10px;
  background: var(--notes-surface-inset);
  color: var(--text);
  font-size: 12px;
  cursor: pointer;
  overflow-wrap: anywhere;
}
.graph-node.selected,.graph-node.related {
  border-color: var(--notes-accent-highlight);
}
.graph-node.selected {
  background: var(--ui-selected-bg);
}
.graph-node.dim {
  opacity: .4;
}
.node-title {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.5;
}
.dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  margin-right: 6px;
  border-radius: 50%;
  background: var(--notes-accent);
}
.empty {
  position: relative;
  padding: 80px 24px;
  text-align: center;
  color: var(--text-muted);
}

</style>
