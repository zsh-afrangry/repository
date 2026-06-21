<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useScrollReveal } from '@/composables/useScrollReveal'

const router = useRouter()

const projects = ref([
  { name: 'KnowledgeMap', desc: '知识图谱可视化', icon: '🧠', color: 'from-purple-500 to-indigo-600', route: null },
  { name: '记账', desc: '收支记录与月度统计', icon: '💰', color: 'from-cyan-500 to-blue-600', route: '/bills' },
  { name: 'AutoML', desc: '自动化机器学习', icon: '🤖', color: 'from-emerald-500 to-teal-600', route: null },
  { name: 'DevOps Hub', desc: '部署与监控中心', icon: '🚀', color: 'from-orange-500 to-red-600', route: null },
  { name: 'API Gateway', desc: '统一 API 网关', icon: '🌐', color: 'from-pink-500 to-rose-600', route: null },
  { name: 'Doc Center', desc: '文档与知识库', icon: '📚', color: 'from-amber-500 to-yellow-600', route: null },
])

function handleCardClick(route: string | null) {
  if (route) router.push(route)
}

const heroRef = ref<HTMLElement>()

onMounted(() => {
  useScrollReveal()
})
</script>

<template>
  <div class="relative">
    <!-- Hero Section -->
    <section
      ref="heroRef"
      class="relative min-h-screen flex flex-col items-center justify-center px-6 overflow-hidden"
    >
      <!-- Gradient background -->
      <div class="absolute inset-0 bg-gradient-to-br from-surface via-surface-light to-surface"></div>
      <!-- Animated gradient orbs -->
      <div class="absolute top-1/4 -left-32 w-96 h-96 bg-primary/20 rounded-full blur-3xl animate-pulse"></div>
      <div class="absolute bottom-1/4 -right-32 w-96 h-96 bg-accent/15 rounded-full blur-3xl animate-pulse delay-1000"></div>

      <!-- Hero content -->
      <div class="relative z-10 text-center max-w-3xl">
        <h1 class="text-5xl md:text-7xl font-bold tracking-tight mb-6 bg-gradient-to-r from-primary-light via-white to-accent-light bg-clip-text text-transparent">
          Dashboard
        </h1>
        <p class="text-lg md:text-xl text-text-muted leading-relaxed">
          统一门户 — 你的所有项目，在这里汇合
        </p>
        <!-- Scroll hint -->
        <div class="mt-16 animate-bounce">
          <svg class="w-6 h-6 mx-auto text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
          </svg>
        </div>
      </div>
    </section>

    <!-- Projects Section -->
    <section ref="cardsRef" class="relative px-6 py-24 max-w-6xl mx-auto">
      <h2 class="text-3xl font-semibold text-center mb-16 reveal-item">项目总览</h2>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div
          v-for="(project, index) in projects"
          :key="project.name"
          class="reveal-item group relative rounded-2xl border bg-surface-card p-6
                 transition-all duration-300 ease-out
                 hover:scale-[1.03] hover:shadow-[0_0_30px_rgba(124,58,237,0.15)]
                 active:scale-[0.98]"
          :class="[
            project.route
              ? 'border-primary/40 cursor-pointer hover:border-primary/70'
              : 'border-border cursor-default hover:border-primary/50',
          ]"
          :style="{ transitionDelay: `${index * 80}ms` }"
          @click="handleCardClick(project.route)"
        >
          <!-- Card glow on hover -->
          <div class="absolute inset-0 rounded-2xl bg-gradient-to-br opacity-0 group-hover:opacity-10 transition-opacity duration-300"
               :class="project.color"></div>

          <div class="relative z-10">
            <div class="text-4xl mb-4">{{ project.icon }}</div>
            <h3 class="text-xl font-semibold text-text mb-2">{{ project.name }}</h3>
            <p class="text-text-muted text-sm">{{ project.desc }}</p>
          </div>

          <!-- Arrow indicator (only for linked cards) -->
          <div
            v-if="project.route"
            class="absolute top-6 right-6 opacity-0 group-hover:opacity-100 transition-all duration-300 translate-x-[-4px] group-hover:translate-x-0"
          >
            <svg class="w-5 h-5 text-primary-light" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3" />
            </svg>
          </div>
        </div>
      </div>
    </section>

    <!-- Stats Section -->
    <section class="px-6 py-24 border-t border-border">
      <div class="max-w-4xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-8">
        <div class="reveal-item text-center" v-for="stat in [
          { value: '6', label: '活跃项目' },
          { value: '99.9%', label: '可用率' },
          { value: '< 50ms', label: '响应延迟' },
          { value: '24/7', label: '持续运行' },
        ]" :key="stat.label">
          <div class="text-3xl font-bold text-primary-light mb-1">{{ stat.value }}</div>
          <div class="text-sm text-text-muted">{{ stat.label }}</div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.delay-1000 {
  animation-delay: 1s;
}

/* Scroll reveal base state */
.reveal-item {
  opacity: 0;
  transform: translateY(24px);
  transition: opacity 0.6s ease-out, transform 0.6s ease-out;
}
.reveal-item.revealed {
  opacity: 1;
  transform: translateY(0);
}
</style>
