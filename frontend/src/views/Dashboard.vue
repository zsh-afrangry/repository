<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useScrollReveal } from '@/composables/useScrollReveal'

type Project = {
  name: string
  desc: string
  label: string
  status: string
  route: string | null
  tone: string
}

const router = useRouter()

const projects = ref<Project[]>([
  {
    name: '记账',
    desc: '收支记录、标签体系和月度统计，当前主力可用模块。',
    label: 'Billing',
    status: '可进入',
    route: '/bills',
    tone: 'cyan',
  },
  {
    name: 'KnowledgeMap',
    desc: '个人项目入口与知识关系视图，作为门户持续扩展。',
    label: 'Portal',
    status: '规划中',
    route: null,
    tone: 'violet',
  },
  {
    name: 'AutoML',
    desc: '实验记录、模型训练和自动化评估的后续工作台。',
    label: 'Machine Learning',
    status: '预留',
    route: null,
    tone: 'emerald',
  },
  {
    name: 'DevOps Hub',
    desc: '部署、监控和运行状态聚合，未来用于统一运维。',
    label: 'Operations',
    status: '预留',
    route: null,
    tone: 'amber',
  },
  {
    name: 'API Gateway',
    desc: '统一 API 管理和服务入口，承接后续多模块通信。',
    label: 'Services',
    status: '预留',
    route: null,
    tone: 'rose',
  },
  {
    name: 'Doc Center',
    desc: '项目文档、计划、验收记录和长期知识库。',
    label: 'Documents',
    status: '预留',
    route: null,
    tone: 'slate',
  },
])

const availableProjects = computed(() => projects.value.filter((project) => project.route).length)

function handleCardClick(route: string | null) {
  if (route) router.push(route)
}

function scrollToSection(id: string) {
  const target = document.querySelector<HTMLElement>(id)
  target?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

onMounted(() => {
  useScrollReveal()
})
</script>

<template>
  <div class="dashboard-shell">
    <header class="dashboard-nav">
      <a class="brand-mark" href="#top" aria-label="KnowledgeMap home" @click.prevent="scrollToSection('#top')">
        <span class="brand-letter">K</span>
        <span>
          <strong>KnowledgeMap</strong>
          <small>Project Portal</small>
        </span>
      </a>

      <nav class="nav-links" aria-label="Dashboard sections">
        <a href="#projects" @click.prevent="scrollToSection('#projects')">Projects</a>
        <a href="#journal" @click.prevent="scrollToSection('#journal')">Journal</a>
        <a href="#about" @click.prevent="scrollToSection('#about')">About</a>
        <button type="button" class="nav-action" @click="router.push('/bills')">Open Bills</button>
      </nav>
    </header>

    <main id="top">
      <section class="hero-panel">
        <div class="hero-backdrop" aria-hidden="true">
          <span class="grid-plane"></span>
          <span class="ink-line ink-line-one"></span>
          <span class="ink-line ink-line-two"></span>
        </div>

        <div class="hero-content">
          <p class="hero-kicker reveal-item">统一入口 / 项目中枢</p>
          <h1 class="hero-title reveal-item">所有侧项目，在一个安静的入口汇合。</h1>
          <p class="hero-copy reveal-item">
            KnowledgeMap 负责收纳你的工具、实验和长期计划。当前先把记账模块稳定放进主入口，后续模块按节奏接入。
          </p>

          <div class="hero-actions reveal-item">
            <button type="button" class="primary-button" @click="router.push('/bills')">
              进入记账模块
            </button>
            <a class="text-link" href="#projects" @click.prevent="scrollToSection('#projects')">查看项目总览</a>
          </div>
        </div>

        <aside class="hero-status reveal-item" aria-label="Portal summary">
          <div>
            <span>{{ projects.length }}</span>
            <p>收纳项目</p>
          </div>
          <div>
            <span>{{ availableProjects }}</span>
            <p>可用入口</p>
          </div>
          <div>
            <span>Dark</span>
            <p>界面模式</p>
          </div>
        </aside>
      </section>

      <section id="projects" class="section-block">
        <div class="section-heading reveal-item">
          <p>Project Index</p>
          <h2>项目总览</h2>
          <span>参考示例的展示型节奏，保留当前门户的暗色产品气质。</span>
        </div>

        <div class="project-grid">
          <article
            v-for="(project, index) in projects"
            :key="project.name"
            class="project-card reveal-item"
            :class="[`tone-${project.tone}`, { 'is-clickable': project.route }]"
            :style="{ transitionDelay: `${index * 80}ms` }"
            @click="handleCardClick(project.route)"
          >
            <div class="project-media">
              <span class="project-label">{{ project.label }}</span>
              <span class="project-number">{{ String(index + 1).padStart(2, '0') }}</span>
            </div>

            <div class="project-body">
              <p>{{ project.status }}</p>
              <h3>{{ project.name }}</h3>
              <span>{{ project.desc }}</span>
            </div>

            <div class="project-footer">
              <span>{{ project.route ? '进入模块' : '等待接入' }}</span>
              <span class="project-arrow" aria-hidden="true">→</span>
            </div>
          </article>
        </div>
      </section>

      <section id="journal" class="section-block journal-section">
        <div class="section-heading centered-heading reveal-item">
          <p>Art & Design</p>
          <h2>《星光咖啡馆与死神之蝶》</h2>
          <span>
            这一段照参考页的三栏展示节奏迁移：大图面、分类标签、标题、摘要和作者信息。
          </span>
        </div>

        <div class="journal-grid">
          <article
            v-for="(post, index) in [
              { title: '四季夏目天下第一！', desc: '四季夏目', category: 'Art & Design', tone: 'cyan' },
              { title: '明月栞那天下第一！', desc: '明月栞那', category: 'Travel', tone: 'violet' },
              { title: '墨染希天下第一！', desc: '墨染希', category: 'Lifestyle', tone: 'amber' },
            ]"
            :key="post.title"
            class="journal-card reveal-item"
            :class="`tone-${post.tone}`"
            :style="{ transitionDelay: `${index * 70}ms` }"
          >
            <div class="journal-image" aria-hidden="true">
              <span>{{ String(index + 1).padStart(2, '0') }}</span>
            </div>
            <p class="journal-category">{{ post.category }}</p>
            <h3>{{ post.title }}</h3>
            <p class="journal-excerpt">{{ post.desc }}</p>
            <div class="journal-meta">
              <span class="author-dot"></span>
              <span>张斯涵</span>
              <span>2025</span>
            </div>
          </article>
        </div>
      </section>

      <section class="newsletter-band">
        <div class="newsletter-inner reveal-item">
          <h2>加入我们吧！</h2>
          <p>留下您的联系方式，与我们一同在 AI 时代赋能智慧医疗，用大模型帮助更多需要帮助的人们。</p>
          <form class="newsletter-form" @submit.prevent>
            <input type="email" placeholder="Your email address" aria-label="Email address" />
            <button type="submit">Subscribe</button>
          </form>
        </div>
      </section>

      <section id="about" class="section-block about-section">
        <div class="about-visual reveal-item" aria-hidden="true"></div>
        <div class="about-content reveal-item">
          <p>About the Author</p>
          <h2>张斯涵</h2>
          <span>
            Writer, photographer, and perpetual wanderer with a deep appreciation for quiet moments and meaningful conversations.
          </span>
          <span>
            After years in fast-paced creative industries, this section follows the reference layout as a quiet author panel.
          </span>
          <button type="button" class="outline-button">Read My Story</button>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
.dashboard-shell {
  min-height: 100vh;
  background:
    radial-gradient(circle at 15% 10%, rgb(124 58 237 / 0.18), transparent 26rem),
    radial-gradient(circle at 85% 30%, rgb(6 182 212 / 0.12), transparent 24rem),
    linear-gradient(180deg, #0f0f14 0%, #111118 46%, #0b0b10 100%);
  color: #e2e8f0;
}

.dashboard-nav {
  position: sticky;
  top: 0;
  z-index: 30;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 2rem;
  padding: 1.1rem clamp(1.25rem, 3vw, 3rem);
  border-bottom: 1px solid rgb(255 255 255 / 0.08);
  background: rgb(15 15 20 / 0.78);
  backdrop-filter: blur(18px);
}

.brand-mark {
  display: inline-flex;
  align-items: center;
  gap: 0.85rem;
}

.brand-letter {
  display: grid;
  width: 2.5rem;
  height: 2.5rem;
  place-items: center;
  border: 1px solid rgb(255 255 255 / 0.16);
  background: linear-gradient(135deg, rgb(124 58 237 / 0.28), rgb(6 182 212 / 0.16));
  font-size: 1.1rem;
  font-weight: 700;
}

.brand-mark strong,
.brand-mark small {
  display: block;
}

.brand-mark strong {
  font-size: 0.92rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.brand-mark small {
  color: #94a3b8;
  font-size: 0.72rem;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: clamp(1rem, 2.5vw, 2rem);
  color: #94a3b8;
  font-size: 0.78rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.nav-links a {
  position: relative;
}

.nav-links a::after {
  position: absolute;
  left: 0;
  bottom: -0.35rem;
  width: 0;
  height: 1px;
  background: #67e8f9;
  content: "";
  transition: width 0.3s ease;
}

.nav-links a:hover::after {
  width: 100%;
}

.nav-action {
  border: 1px solid rgb(103 232 249 / 0.45);
  padding: 0.62rem 1rem;
  color: #e2e8f0;
  transition: border-color 0.25s ease, background 0.25s ease, transform 0.25s ease;
}

.nav-action:hover {
  border-color: #67e8f9;
  background: rgb(103 232 249 / 0.08);
  transform: translateY(-1px);
}

.hero-panel {
  position: relative;
  display: grid;
  min-height: calc(100dvh - 4.8rem);
  grid-template-columns: minmax(0, 1fr) minmax(17rem, 23rem);
  gap: clamp(2rem, 5vw, 5rem);
  align-items: center;
  overflow: hidden;
  padding: clamp(4rem, 9vw, 8rem) clamp(1.25rem, 5vw, 5rem);
}

.hero-backdrop {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
}

.grid-plane {
  position: absolute;
  inset: 7rem 3rem 5rem;
  border: 1px solid rgb(255 255 255 / 0.06);
  background-image:
    linear-gradient(rgb(255 255 255 / 0.045) 1px, transparent 1px),
    linear-gradient(90deg, rgb(255 255 255 / 0.045) 1px, transparent 1px);
  background-size: 46px 46px;
  mask-image: linear-gradient(90deg, transparent, black 16%, black 84%, transparent);
}

.ink-line {
  position: absolute;
  width: 32rem;
  height: 32rem;
  border: 1px solid rgb(103 232 249 / 0.2);
  border-radius: 999px;
  transform: rotate(-18deg);
  animation: drift 12s ease-in-out infinite;
}

.ink-line-one {
  top: 12%;
  right: 8%;
}

.ink-line-two {
  bottom: 0;
  left: -8%;
  border-color: rgb(167 139 250 / 0.18);
  animation-delay: -4s;
}

.hero-content,
.hero-status {
  position: relative;
  z-index: 1;
}

.hero-kicker,
.section-heading p,
.pulse-copy p {
  color: #67e8f9;
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.22em;
  text-transform: uppercase;
}

.hero-title {
  max-width: 15ch;
  margin-top: 1.5rem;
  color: #f8fafc;
  font-size: clamp(2.8rem, 6vw, 5.5rem);
  font-weight: 800;
  letter-spacing: 0;
  line-height: 1;
}

.hero-copy {
  max-width: 44rem;
  margin-top: 1.7rem;
  color: #a8b3c7;
  font-size: clamp(1rem, 1.55vw, 1.25rem);
  line-height: 1.85;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  align-items: center;
  margin-top: 2.4rem;
}

.primary-button,
.text-link {
  display: inline-flex;
  min-height: 2.85rem;
  align-items: center;
  justify-content: center;
  padding: 0 1.3rem;
  font-size: 0.84rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.primary-button {
  border: 1px solid #67e8f9;
  background: #67e8f9;
  color: #071116;
  transition: transform 0.25s ease, box-shadow 0.25s ease;
}

.primary-button:hover {
  box-shadow: 0 18px 45px rgb(6 182 212 / 0.18);
  transform: translateY(-2px);
}

.text-link {
  color: #94a3b8;
}

.text-link:hover {
  color: #e2e8f0;
}

.hero-status {
  display: grid;
  gap: 1px;
  border: 1px solid rgb(255 255 255 / 0.1);
  background: rgb(255 255 255 / 0.08);
}

.hero-status div {
  padding: 1.6rem;
  background: rgb(15 15 20 / 0.68);
}

.hero-status span {
  display: block;
  color: #f8fafc;
  font-size: clamp(2rem, 4vw, 3.2rem);
  font-weight: 800;
}

.hero-status p {
  margin-top: 0.25rem;
  color: #94a3b8;
  font-size: 0.85rem;
}

.section-block {
  padding: clamp(4rem, 8vw, 7rem) clamp(1.25rem, 5vw, 5rem);
}

.section-heading {
  display: grid;
  gap: 0.8rem;
  max-width: 46rem;
  margin-bottom: clamp(2rem, 5vw, 4rem);
}

.centered-heading {
  max-width: 48rem;
  margin-right: auto;
  margin-left: auto;
  text-align: center;
}

.section-heading h2,
.about-content h2,
.newsletter-inner h2 {
  color: #f8fafc;
  font-size: clamp(2.3rem, 5vw, 4.5rem);
  font-weight: 800;
  letter-spacing: 0;
  line-height: 1;
}

.section-heading span {
  color: #94a3b8;
  line-height: 1.75;
}

.project-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1.2rem;
}

.project-card {
  position: relative;
  min-height: 25rem;
  overflow: hidden;
  border: 1px solid rgb(255 255 255 / 0.1);
  background:
    linear-gradient(180deg, rgb(255 255 255 / 0.075), rgb(255 255 255 / 0.025)),
    #16161e;
  transition: transform 0.35s ease, border-color 0.35s ease, box-shadow 0.35s ease;
}

.project-card.is-clickable {
  cursor: pointer;
}

.project-card:hover {
  border-color: rgb(103 232 249 / 0.45);
  box-shadow: 0 24px 80px rgb(0 0 0 / 0.28);
  transform: translateY(-0.45rem);
}

.project-media {
  display: flex;
  min-height: 11rem;
  align-items: flex-start;
  justify-content: space-between;
  padding: 1.35rem;
  background:
    radial-gradient(circle at 28% 18%, var(--project-glow), transparent 58%),
    linear-gradient(135deg, rgb(255 255 255 / 0.08), transparent);
}

.project-label,
.project-number,
.project-body p,
.project-footer {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.project-label,
.project-number {
  color: rgb(255 255 255 / 0.72);
}

.project-body {
  padding: 1.5rem;
}

.project-body p {
  color: var(--project-accent);
}

.project-body h3 {
  margin-top: 0.75rem;
  color: #f8fafc;
  font-size: 1.9rem;
  font-weight: 800;
}

.project-body span {
  display: block;
  margin-top: 1rem;
  color: #9ca8bb;
  line-height: 1.7;
}

.project-footer {
  position: absolute;
  right: 1.5rem;
  bottom: 1.35rem;
  left: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: #94a3b8;
}

.project-arrow {
  color: var(--project-accent);
  font-size: 1.25rem;
  transform: translateX(-0.25rem);
  transition: transform 0.3s ease;
}

.project-card:hover .project-arrow {
  transform: translateX(0.2rem);
}

.tone-cyan {
  --project-accent: #67e8f9;
  --project-glow: rgb(6 182 212 / 0.34);
}

.tone-violet {
  --project-accent: #a78bfa;
  --project-glow: rgb(124 58 237 / 0.35);
}

.tone-emerald {
  --project-accent: #6ee7b7;
  --project-glow: rgb(16 185 129 / 0.28);
}

.tone-amber {
  --project-accent: #fbbf24;
  --project-glow: rgb(245 158 11 / 0.28);
}

.tone-rose {
  --project-accent: #fb7185;
  --project-glow: rgb(244 63 94 / 0.28);
}

.tone-slate {
  --project-accent: #cbd5e1;
  --project-glow: rgb(148 163 184 / 0.22);
}

.journal-section {
  border-top: 1px solid rgb(255 255 255 / 0.08);
}

.journal-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: clamp(1.4rem, 3vw, 3rem);
}

.journal-card {
  transition: transform 0.35s ease;
}

.journal-card:hover {
  transform: translateY(-0.4rem);
}

.journal-image {
  position: relative;
  display: grid;
  height: clamp(18rem, 34vw, 26rem);
  place-items: start end;
  margin-bottom: 1.5rem;
  overflow: hidden;
  border: 1px solid rgb(255 255 255 / 0.1);
  background:
    radial-gradient(circle at 28% 22%, var(--project-glow), transparent 54%),
    linear-gradient(145deg, rgb(255 255 255 / 0.1), rgb(255 255 255 / 0.02)),
    #171720;
  filter: grayscale(18%);
  transition: filter 0.3s ease, transform 0.3s ease;
}

.journal-card:hover .journal-image {
  filter: grayscale(0);
  transform: scale(1.015);
}

.journal-image span {
  padding: 1.1rem;
  color: rgb(255 255 255 / 0.55);
  font-size: 3rem;
  font-weight: 800;
}

.journal-category,
.about-content p {
  color: #67e8f9;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.journal-card h3 {
  margin-top: 0.45rem;
  color: #f8fafc;
  font-size: clamp(1.55rem, 2.2vw, 2rem);
  font-weight: 800;
  line-height: 1.25;
  transition: color 0.3s ease;
}

.journal-card:hover h3 {
  color: var(--project-accent);
}

.journal-excerpt {
  margin-top: 0.9rem;
  color: #94a3b8;
}

.journal-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.9rem;
  align-items: center;
  margin-top: 1.4rem;
  color: #94a3b8;
  font-size: 0.82rem;
}

.author-dot {
  width: 1.8rem;
  height: 1.8rem;
  border: 1px solid rgb(255 255 255 / 0.14);
  border-radius: 999px;
  background: radial-gradient(circle at 35% 28%, #67e8f9, #7c3aed 62%, #101018);
}

.newsletter-band {
  padding: clamp(4rem, 8vw, 7rem) clamp(1.25rem, 5vw, 5rem);
  background: #050508;
  border-top: 1px solid rgb(255 255 255 / 0.08);
  border-bottom: 1px solid rgb(255 255 255 / 0.08);
}

.newsletter-inner {
  max-width: 46rem;
  margin: 0 auto;
  text-align: center;
}

.newsletter-inner p {
  max-width: 40rem;
  margin: 1rem auto 2rem;
  color: #9ca8bb;
  line-height: 1.8;
}

.newsletter-form {
  display: flex;
  max-width: 42rem;
  margin: 0 auto;
}

.newsletter-form input {
  min-width: 0;
  flex: 1;
  border: 1px solid rgb(255 255 255 / 0.12);
  background: rgb(255 255 255 / 0.06);
  padding: 1rem 1.2rem;
  color: #f8fafc;
  outline: none;
}

.newsletter-form input:focus {
  border-color: rgb(103 232 249 / 0.7);
}

.newsletter-form button {
  border: 0;
  background: #67e8f9;
  padding: 0 1.5rem;
  color: #071116;
  font-size: 0.8rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.about-section {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 0.9fr);
  gap: clamp(2rem, 6vw, 5rem);
  align-items: center;
}

.about-visual {
  position: relative;
  min-height: clamp(28rem, 45vw, 38rem);
  border: 1px solid rgb(255 255 255 / 0.1);
  background:
    radial-gradient(circle at 36% 24%, rgb(103 232 249 / 0.24), transparent 30%),
    radial-gradient(circle at 72% 66%, rgb(167 139 250 / 0.24), transparent 34%),
    linear-gradient(135deg, rgb(255 255 255 / 0.08), rgb(255 255 255 / 0.02)),
    #16161e;
}

.about-visual::before {
  position: absolute;
  inset: -1.6rem 1.6rem 1.6rem -1.6rem;
  z-index: -1;
  border: 1px solid rgb(103 232 249 / 0.35);
  content: "";
}

.about-content {
  display: grid;
  gap: 1.2rem;
}

.about-content span {
  color: #9ca8bb;
  line-height: 1.85;
}

.outline-button {
  justify-self: start;
  margin-top: 0.8rem;
  border: 1px solid rgb(255 255 255 / 0.28);
  padding: 0.85rem 1.4rem;
  color: #f8fafc;
  font-size: 0.82rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  transition: border-color 0.25s ease, background 0.25s ease;
}

.outline-button:hover {
  border-color: #67e8f9;
  background: rgb(103 232 249 / 0.08);
}

.reveal-item {
  opacity: 0;
  transform: translateY(24px);
  transition: opacity 0.75s cubic-bezier(0.22, 1, 0.36, 1), transform 0.75s cubic-bezier(0.22, 1, 0.36, 1);
}

.reveal-item.revealed {
  opacity: 1;
  transform: translateY(0);
}

@keyframes drift {
  0%,
  100% {
    transform: translate3d(0, 0, 0) rotate(-18deg);
  }
  50% {
    transform: translate3d(1rem, -1.2rem, 0) rotate(-12deg);
  }
}

@media (max-width: 1024px) {
  .hero-panel,
  .about-section {
    grid-template-columns: 1fr;
  }

  .hero-title {
    max-width: 13ch;
  }

  .hero-status {
    grid-template-columns: repeat(3, 1fr);
  }

  .project-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .journal-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .dashboard-nav {
    align-items: flex-start;
    flex-direction: column;
  }

  .nav-links {
    width: 100%;
    justify-content: space-between;
    gap: 0.75rem;
  }

  .hero-panel {
    padding-top: 3rem;
  }

  .hero-status,
  .project-grid,
  .journal-grid {
    grid-template-columns: 1fr;
  }

  .project-card {
    min-height: 22rem;
  }

  .newsletter-form {
    flex-direction: column;
  }

  .newsletter-form button {
    min-height: 3rem;
  }

  .about-visual::before {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .ink-line,
  .project-card,
  .primary-button,
  .reveal-item {
    animation: none;
    transition: none;
  }
}
</style>
