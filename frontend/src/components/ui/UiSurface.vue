<script setup lang="ts">
withDefaults(defineProps<{ as?: 'div' | 'section' | 'article' | 'aside' }>(), { as: 'div' })
</script>

<template>
  <component :is="as" class="ui-surface"><slot /></component>
</template>

<style scoped>
/* Surface owns appearance only; its consumer owns dimensions and layout. */
.ui-surface {
  border: 1px solid var(--ui-surface-border, var(--border));
  border-radius: var(--ui-surface-radius, 12px);
  background: var(--ui-surface-bg, var(--card-bg));
  box-shadow: var(--ui-surface-shadow, none);
}
</style>
