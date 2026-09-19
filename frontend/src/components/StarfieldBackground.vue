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
/* 本组件只负责自己这一个 canvas，不碰任何外部元素。
 *
 * 这里原先还有一个 `:global(.starry-workspace)` 块：它用 `:global()` 逃出 scoped 作用域，
 * 反向给「使用本组件的页面」定义布局和整套设计变量。其中 9 个变量与 `main.css` 的 `:root`
 * **取值逐条相同**（纯冗余副本），而 `.starry-workspace` 这个类名全仓只出现在 `Bills.vue`。
 * 2026-09-20 已把那 3 条真正生效的声明移回 `Bills.vue` 自己的 scoped 样式。
 *
 * 这样本组件才是 `docs/1` §4.2 期望的那种「可以挂到任何页面上的共享背景层」；
 * 原先的写法会让它一旦被别的页面复用，就顺手改掉那个页面的配色变量。详见 docs/5 §2.21。
 */

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
