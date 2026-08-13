<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

type Star = { x: number; y: number; vx: number; vy: number; radius: number; opacity: number }

const canvas = ref<HTMLCanvasElement | null>(null)
let stars: Star[] = []
let animationFrame = 0

function resize() {
  if (!canvas.value) return
  canvas.value.width = window.innerWidth
  canvas.value.height = window.innerHeight
  const count = Math.min(42, Math.max(20, Math.floor((canvas.value.width * canvas.value.height) / 22000)))
  stars = Array.from({ length: count }, () => ({
    x: Math.random() * canvas.value!.width,
    y: Math.random() * canvas.value!.height,
    vx: (Math.random() - 0.5) * 0.16,
    vy: (Math.random() - 0.5) * 0.16,
    radius: Math.random() * 1.25 + 0.45,
    opacity: Math.random() * 0.22 + 0.08,
  }))
}

function draw() {
  const context = canvas.value?.getContext('2d')
  if (!canvas.value || !context) return
  context.clearRect(0, 0, canvas.value.width, canvas.value.height)

  for (let i = 0; i < stars.length; i++) {
    const star = stars[i]
    star.x += star.vx
    star.y += star.vy
    if (star.x < 0 || star.x > canvas.value.width) star.vx *= -1
    if (star.y < 0 || star.y > canvas.value.height) star.vy *= -1

    context.beginPath()
    context.arc(star.x, star.y, star.radius, 0, Math.PI * 2)
    context.fillStyle = `rgba(103, 232, 249, ${star.opacity})`
    context.fill()

    for (let j = i + 1; j < stars.length; j++) {
      const neighbour = stars[j]
      const distance = Math.hypot(star.x - neighbour.x, star.y - neighbour.y)
      if (distance > 110) continue
      context.beginPath()
      context.moveTo(star.x, star.y)
      context.lineTo(neighbour.x, neighbour.y)
      context.strokeStyle = `rgba(103, 232, 249, ${(1 - distance / 110) * 0.11})`
      context.lineWidth = 0.5
      context.stroke()
    }
  }
  animationFrame = requestAnimationFrame(draw)
}

onMounted(() => {
  resize()
  window.addEventListener('resize', resize)
  draw()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  cancelAnimationFrame(animationFrame)
})
</script>

<template>
  <canvas ref="canvas" class="starfield-background" aria-hidden="true"></canvas>
</template>

<style scoped>
:global(.starry-workspace) {
  position: relative;
  isolation: isolate;
  background: rgba(7, 8, 22, 0.78);
  --primary: #7c3aed;
  --primary-light: #a78bfa;
  --primary-dark: #5b21b6;
  --surface: #0f0f14;
  --surface-light: #1a1a24;
  --surface-card: #1e1e2a;
  --text: #e2e8f0;
  --text-muted: #94a3b8;
  --border: #2e2e3a;
}

.starfield-background {
  position: fixed;
  inset: 0;
  z-index: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  background:
    radial-gradient(circle at 22% 26%, rgba(79, 70, 229, 0.19), transparent 31rem),
    radial-gradient(circle at 76% 74%, rgba(6, 182, 212, 0.12), transparent 28rem),
    #070816;
}
</style>
