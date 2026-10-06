<template>
  <div class="grid-decoration" aria-hidden="true" />
</template>

<style scoped>
.grid-decoration {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background-image:
    linear-gradient(var(--grid-color, rgb(148 163 184 / 0.06)) 1px, transparent 1px),
    linear-gradient(90deg, var(--grid-color, rgb(148 163 184 / 0.06)) 1px, transparent 1px);
  background-size: var(--grid-size, 30px) var(--grid-size, 30px);
}
</style>
