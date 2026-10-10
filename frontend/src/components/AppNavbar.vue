<script setup lang="ts">
/**
 * 全站统一顶部导航栏 (AppNavbar)
 *
 * 对应文档：docs/16_Notes学习模块视觉重构与体验优化方案.md
 *
 * 统一承载 Brand Mark（个人开发中枢）、跨系统一级导航、主题切换与头像。
 * 在主页、Notes、Vault 等页面保持一致的视觉节奏与交互。
 */
import { useRouter } from 'vue-router'
import { useToast } from '@/composables/useToast'

const props = withDefaults(
  defineProps<{
    active?: 'dashboard' | 'notes' | 'vault' | 'bills'
  }>(),
  {
    active: 'dashboard',
  }
)

const router = useRouter()
const { show: showToast } = useToast()

function notifyThemePending() {
  showToast({
    text: '主题切换功能待开发',
    detail: '浅色主题的样式与变量都已保留，接入后会在这里切换。',
    durationMs: 3000,
  })
}

function handleProjectsClick(e: MouseEvent) {
  if (router.currentRoute.value.path === '/') {
    e.preventDefault()
    const target = document.querySelector<HTMLElement>('#projects')
    target?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  } else {
    // 跨页面跳转到首页项目总览
    router.push('/#projects')
  }
}

function handleBrandClick(e: MouseEvent) {
  if (router.currentRoute.value.path === '/') {
    e.preventDefault()
    const target = document.querySelector<HTMLElement>('#top')
    target?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  } else {
    router.push('/')
  }
}
</script>

<template>
  <header class="dashboard-nav app-navbar">
    <a
      class="brand-mark"
      href="/"
      aria-label="KnowledgeMap home"
      @click="handleBrandClick"
    >
      <span class="brand-letter">K</span>
      <span>
        <strong>KNOWLEDGEMAP</strong>
        <small>个人开发中枢</small>
      </span>
    </a>

    <nav class="nav-links" aria-label="Global sections">
      <a
        href="/#projects"
        :class="{ active: props.active === 'dashboard' }"
        @click="handleProjectsClick"
      >
        项目总览
      </a>
      <RouterLink
        to="/notes"
        :class="{ active: props.active === 'notes' }"
      >
        知识图谱
      </RouterLink>
      <a
        href="#lab"
        aria-disabled="true"
        title="功能待开发"
        @click.prevent="void(0)"
      >
        实验室
      </a>
      <a
        href="#docs"
        aria-disabled="true"
        title="功能待开发"
        @click.prevent="void(0)"
      >
        文档库
      </a>
      <RouterLink
        to="/vault"
        :class="{ active: props.active === 'vault' }"
      >
        储物间
      </RouterLink>
      <button
        type="button"
        class="theme-toggle btn-tactile"
        aria-label="切换主题（功能待开发）"
        title="切换主题（功能待开发）"
        @click="notifyThemePending"
      >
        <span aria-hidden="true">🌙</span>
      </button>
      <div class="user-avatar" aria-label="User Profile">K</div>
    </nav>
  </header>
</template>

<style scoped>
.dashboard-nav {
  position: sticky;
  top: 0;
  z-index: 30;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 2rem;
  min-height: 5.5rem;
  padding: 1.25rem clamp(2rem, 4vw, 4.5rem);
  background: rgba(4, 8, 18, 0.85);
  border-bottom: 1px solid rgba(148, 163, 184, 0.12);
  box-shadow: 0 14px 50px rgba(0, 0, 0, 0.18);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
}

.brand-mark {
  display: flex;
  align-items: center;
  gap: 1.05rem;
  text-decoration: none;
  color: inherit;
  cursor: pointer;
}

.brand-letter {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 3rem;
  height: 3rem;
  border: 1px solid rgba(103, 232, 249, 0.32);
  border-radius: 0.55rem;
  background:
    linear-gradient(145deg, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.72)),
    radial-gradient(circle at 35% 18%, rgba(124, 58, 237, 0.55), transparent 58%);
  box-shadow: 0 0 24px rgba(124, 58, 237, 0.24);
  font-size: 1.45rem;
  font-weight: 800;
  color: #67e8f9;
}

.brand-mark strong {
  display: block;
  font-size: 1.02rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  color: #ffffff;
}

.brand-mark small {
  display: block;
  margin-top: 0.18rem;
  color: #9aa7bd;
  font-size: 0.78rem;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: clamp(1.6rem, 2.6vw, 2.8rem);
  color: #a7b2c7;
  font-size: 0.9rem;
  font-weight: 650;
  letter-spacing: 0;
  text-transform: none;
}

.nav-links a {
  position: relative;
  text-decoration: none;
  color: inherit;
  transition: color 0.2s ease;
  cursor: pointer;
}

.nav-links a:hover {
  color: #f8fafc;
}

.nav-links a.active {
  color: #f8fafc;
}

.nav-links a.active::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: -0.7rem;
  height: 0.15rem;
  border-radius: 999px;
  background: linear-gradient(90deg, #8b5cf6, #a78bfa);
}

.nav-links a[aria-disabled="true"] {
  opacity: 0.45;
  cursor: not-allowed;
}

.theme-toggle {
  background: none;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 0.55rem;
  width: 2.65rem;
  height: 2.65rem;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #e2e8f0;
  cursor: pointer;
  font-size: 1rem;
  transition: all 0.2s ease;
}

.theme-toggle:hover {
  border-color: rgba(139, 92, 246, 0.5);
  background: rgba(139, 92, 246, 0.15);
}

.user-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.35rem;
  height: 2.35rem;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 999px;
  background: linear-gradient(135deg, #4752ff, #7c3aed);
  font-weight: 700;
  color: #ffffff;
}

@media (max-width: 720px) {
  .dashboard-nav {
    align-items: flex-start;
    flex-direction: column;
    padding: 1rem;
    gap: 1rem;
  }
  .nav-links {
    flex-wrap: wrap;
    width: 100%;
    justify-content: space-between;
    gap: 0.75rem;
  }
}
</style>
