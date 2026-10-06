<script setup lang="ts">
// Accept only the sanitized HTML produced by Notes' Markdown renderer.
// This component owns typography, not parsing, sanitization or persistence.
defineProps<{ html: string }>()
</script>

<template>
  <div class="notes-prose markdown-body" v-html="html" />
</template>

<style scoped>
.notes-prose {
  min-width: 0;
  color: var(--text);
  background: transparent;
  font-size: 16px;
  line-height: 1.85;
  overflow-wrap: anywhere;
}
.notes-prose :deep(h1),
.notes-prose :deep(h2),
.notes-prose :deep(h3) {
  color: var(--text-title);
  font-family: inherit;
  font-weight: 750;
  line-height: 1.35;
  text-wrap: pretty;
}
.notes-prose :deep(h1) { margin: 0 0 28px; font-size: clamp(28px, 3.2vw, 40px); }
.notes-prose :deep(h2) { margin: 40px 0 16px; padding-bottom: 10px; border-bottom: 1px solid var(--border); font-size: 24px; }
.notes-prose :deep(h3) { margin: 28px 0 12px; font-size: 19px; }
.notes-prose :deep(p),
.notes-prose :deep(li) { color: var(--notes-prose-text, var(--text)); font-size: inherit; line-height: inherit; }
.notes-prose :deep(p) { margin: 0 0 20px; }
.notes-prose :deep(li) { margin: 8px 0; list-style-position: outside; }
.notes-prose :deep(strong) { color: var(--text-title); font-weight: 700; }
.notes-prose :deep(code) {
  padding: 2px 5px;
  border-radius: 4px;
  color: var(--notes-code-text, var(--primary-light));
  background: var(--surface-light);
  font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
  font-size: .875em;
}
.notes-prose :deep(pre) {
  max-width: 100%;
  margin: 24px 0;
  padding: 18px 20px;
  overflow-x: auto;
  border: 1px solid var(--border);
  border-radius: 10px;
  color: var(--text);
  background: var(--notes-code-bg, var(--surface));
  font-size: 13px;
  line-height: 1.7;
  white-space: pre;
  overflow-wrap: normal;
  tab-size: 2;
}
.notes-prose :deep(pre code) { padding: 0; border-radius: 0; color: inherit; background: transparent; font-size: inherit; }
.notes-prose :deep(blockquote) {
  margin: 24px 0;
  padding: 4px 0 4px 18px;
  border-left: 3px solid var(--ui-focus, var(--primary-light));
  color: var(--text-muted);
  font-style: normal;
}
.notes-prose :deep(.prose-table-scroll) { max-width: 100%; overflow-x: auto; margin: 24px 0; }
.notes-prose :deep(.prose-table-scroll:focus-visible),
.notes-prose :deep(pre:focus-visible) { outline: 2px solid var(--ui-focus); outline-offset: -2px; }
.notes-prose :deep(ul) { list-style-type: disc; padding-left: 1.5em; margin: 16px 0; }
.notes-prose :deep(ol) { list-style-type: decimal; padding-left: 1.5em; margin: 16px 0; }
.notes-prose :deep(table) { width: 100%; border-collapse: collapse; border-spacing: 0; font-size: 14px; line-height: 1.65; }
.notes-prose :deep(th),
.notes-prose :deep(td) { min-width: 8rem; padding: 12px 16px; border-bottom: 1px solid var(--border); color: var(--text); text-align: left; vertical-align: top; }
.notes-prose :deep(th) { color: var(--text-title); font-weight: 650; }
.notes-prose :deep(thead) { background: var(--surface-light); }
/* Explicit scoped surfaces preserve the old defense against global markdown leakage. */
.notes-prose.markdown-body :deep(tr) { background: transparent; border-top-color: var(--border); }
.notes-prose.markdown-body :deep(a) { color: var(--ui-focus, var(--primary-light)); text-decoration: underline; text-underline-offset: 3px; }
.notes-prose.markdown-body :deep(a:focus-visible) { outline: 2px solid var(--ui-focus, var(--primary-light)); outline-offset: 3px; }
.notes-prose.markdown-body :deep(hr) { height: 1px; margin: 32px 0; border: 0; background: var(--border); }
/* Retained light-theme boundary; the switch remains intentionally unavailable. */
.theme-light .notes-prose :deep(td) { border-bottom-color: rgba(0, 0, 0, .05); }
@media (max-width: 600px) {
  .notes-prose { font-size: 15px; }
  .notes-prose :deep(h2) { font-size: 22px; }
  .notes-prose :deep(pre) { padding: 14px; }
}
</style>
