<template>
  <div class="ambient-glow" aria-hidden="true" />
</template>

<style scoped>
/* Mount inside a positioned container; no layout or palette rules for the host. */
.ambient-glow {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: radial-gradient(
    circle at var(--glow-position, 15% 0%),
    var(--glow-color, rgb(124 58 237 / 0.12)),
    transparent var(--glow-radius, 28rem)
  );
}
</style>
