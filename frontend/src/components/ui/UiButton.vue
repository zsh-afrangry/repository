<script setup lang="ts">
withDefaults(defineProps<{
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  type?: 'button' | 'submit' | 'reset'
  disabled?: boolean
}>(), { variant: 'secondary', type: 'button', disabled: false })
</script>

<template>
  <button :type="type" :disabled="disabled" class="ui-button" :class="`ui-button--${variant}`"><slot /></button>
</template>

<style scoped>
.ui-button {
  display: inline-flex;
  min-height: var(--ui-control-height, 38px);
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 0 13px;
  border: 1px solid var(--button-border, var(--ui-control-border, var(--border)));
  border-radius: var(--ui-control-radius, 10px);
  color: var(--button-text, var(--text));
  background: var(--button-bg, var(--ui-control-bg, var(--surface-light)));
  font: inherit;
  font-size: var(--ui-control-font-size, 12px);
  font-weight: 650;
  line-height: 1.4;
  cursor: pointer;
  transition: background-color .16s ease, border-color .16s ease, color .16s ease;
}
.ui-button--primary {
  --button-bg: var(--ui-primary-bg, var(--primary));
  --button-text: var(--ui-primary-text, #fff);
  --button-border: var(--ui-primary-border, var(--primary-light));
}
.ui-button--ghost { --button-bg: transparent; --button-border: transparent; }
.ui-button--danger { --button-text: var(--ui-danger-text, var(--expense)); }
.ui-button:hover:not(:disabled) {
  border-color: var(--ui-focus, var(--primary-light));
  background: var(--ui-control-hover, var(--surface-card));
}
.ui-button--primary:hover:not(:disabled) { background: var(--ui-primary-hover, var(--primary-dark)); }
.ui-button--danger:hover:not(:disabled) { border-color: var(--ui-danger-text, var(--expense)); }
.ui-button[aria-current="page"] {
  --button-bg: var(--ui-selected-bg, var(--primary-dark));
  --button-text: var(--ui-primary-text, #fff);
}
.ui-button:active:not(:disabled) { box-shadow: inset 0 0 0 1px currentColor; }
.ui-button:focus-visible { outline: 2px solid var(--ui-focus, var(--primary-light)); outline-offset: 3px; }
.ui-button:disabled { opacity: .45; cursor: not-allowed; }
@media (prefers-reduced-motion: reduce) { .ui-button { transition: none; } }
</style>
