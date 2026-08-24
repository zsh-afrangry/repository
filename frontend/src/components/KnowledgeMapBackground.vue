<template>
  <div class="knowledge-map-background" aria-hidden="true" />
</template>

<style scoped>
.knowledge-map-background {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background:
    radial-gradient(circle at 18% 28%, rgba(66, 82, 255, 0.22), transparent 32rem),
    radial-gradient(circle at 76% 18%, rgba(6, 182, 212, 0.11), transparent 28rem),
    linear-gradient(135deg, #070816 0%, #0a1122 48%, #07101d 100%);
}
</style>
