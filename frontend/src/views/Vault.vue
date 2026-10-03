<script setup lang="ts">
/**
 * 储物间 (Vault) — 静态界面归档页
 *
 * 这里存放从主界面（Dashboard）上撤下来的、不再适合放在门户首页的静态界面草稿。
 * 它们原本是第一版落地页设计的一部分，用户希望保留而不删除（2026-09-20 决定）。
 *
 * 归档原则：
 * -  markup 与样式从 Dashboard.vue 原样搬迁，视觉保持一致；
 * -  不接任何后端数据，全部为静态内容（newsletter 表单的 submit 已被阻止）；
 * -  Does not use Dashboard scroll-reveal classes because this route owns its own static layout;
 * -  与主界面共享的样式（.section-block / .section-heading / .outline-button）在下方
 *    复制了一份，使本页可以独立渲染，不依赖 Dashboard.vue 的 scoped 样式。
 *    这些共享规则在 Dashboard.vue 中仍保留（hero 与项目区还在用）。
 *
 * 相关资源：public/images/pic1.png、pic2.png、pic3.png、pic4.gif、pic5.jpg（均在本页被引用）。
 * Unused historical assets are kept out of this route.
 */
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <div class="vault-shell">
    <header class="vault-nav">
      <button type="button" class="outline-button btn-tactile" @click="router.push('/')">
        ← 返回门户
      </button>
      <div class="vault-heading">
        <h1>储物间</h1>
        <p>
          这里存放已从主界面撤下的静态界面草稿。内容原样保留、不接数据，
          仅作归档，方便日后重新取用。
        </p>
      </div>
    </header>

    <main class="vault-main">
      <section id="journal" class="section-block journal-section">
        <div class="section-heading centered-heading">
          <p>Art & Design</p>
          <h2>《星光咖啡馆与死神之蝶》</h2>
          <span>
            这一段照参考页的三栏展示节奏迁移：大图面、分类标签、标题、摘要和作者信息。
          </span>
        </div>

        <div class="journal-grid">
          <article
            v-for="(post, index) in [
              { title: '四季夏目天下第一！', desc: '四季夏目', category: 'Art & Design', tone: 'cyan', image: '/images/pic1.png' },
              { title: '明月栞那天下第一！', desc: '明月栞那', category: 'Travel', tone: 'violet', image: '/images/pic2.png' },
              { title: '墨染希天下第一！', desc: '墨染希', category: 'Lifestyle', tone: 'amber', image: '/images/pic3.png' },
            ]"
            :key="post.title"
            class="journal-card"
            :class="`tone-${post.tone}`"
            :style="{ transitionDelay: `${index * 70}ms` }"
          >
            <div class="journal-image" aria-hidden="true">
              <img :src="post.image" :alt="post.title" class="journal-img-content" />
              <span>{{ String(index + 1).padStart(2, '0') }}</span>
            </div>
            <p class="journal-category">{{ post.category }}</p>
            <h3>{{ post.title }}</h3>
            <p class="journal-excerpt">{{ post.desc }}</p>
            <div class="journal-meta">
              <img src="/images/pic4.gif" alt="张斯涵" class="author-avatar" />
              <span>张斯涵</span>
              <span>2025</span>
            </div>
          </article>
        </div>
      </section>

      <section class="newsletter-band">
        <div class="newsletter-inner">
          <h2>加入我们吧！</h2>
          <p>留下您的联系方式，与我们一同在 AI 时代赋能智慧医疗，用大模型帮助更多需要帮助的人们。</p>
          <form class="newsletter-form" @submit.prevent>
            <input type="email" placeholder="Your email address" aria-label="Email address" />
            <button type="submit">Subscribe</button>
          </form>
        </div>
      </section>

      <section id="about" class="section-block about-section">
        <div class="about-visual" aria-hidden="true"></div>
        <div class="about-content">
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
/* 本页自身的布局骨架（不随归档内容搬迁） */
.vault-shell {
  min-height: 100vh;
  color: var(--text);
  background: var(--surface);
}

.vault-nav {
  display: flex;
  align-items: flex-start;
  gap: 1.5rem;
  padding: clamp(1.5rem, 4vw, 2.5rem) clamp(1.25rem, 5vw, 5rem) 0;
}

.vault-heading h1 {
  color: var(--text-title);
  font-family: var(--font-serif), inherit;
  font-size: clamp(1.8rem, 3.5vw, 2.6rem);
  font-weight: 800;
  line-height: 1.1;
}

.vault-heading p {
  max-width: 46rem;
  margin-top: 0.6rem;
  color: var(--text-secondary);
  font-size: 0.92rem;
  line-height: 1.7;
}

.vault-main {
  padding-bottom: 4rem;
}

@media (max-width: 720px) {
  .vault-nav {
    flex-direction: column;
  }
}

/* ==== 以下为从 Dashboard.vue 原样搬迁的归档样式 ==== */
/* ---- 共享基础样式 ----
   以下 4 条在 Dashboard.vue 中与项目区/hero 共用，因此 Dashboard 侧保留不动，
   这里只是复制一份，让储物间页面能独立渲染。 */
.section-block {
  padding: clamp(4rem, 8vw, 7rem) clamp(1.25rem, 5vw, 5rem);
}

.section-heading {
  display: grid;
  gap: 0.8rem;
  max-width: 46rem;
  margin-bottom: clamp(2rem, 5vw, 4rem);
}

/* .centered-heading 只被 journal 使用，已从 Dashboard 移除 */
.centered-heading {
  max-width: 48rem;
  margin-right: auto;
  margin-left: auto;
  text-align: center;
}

.section-heading h2,
.about-content h2,
.newsletter-inner h2 {
  color: var(--text-title);
  font-family: var(--font-serif), inherit;
  font-size: clamp(2.3rem, 5vw, 4.5rem);
  font-weight: 800;
  letter-spacing: 0;
  line-height: 1;
  transition: color 0.3s ease;
}

.section-heading span {
  color: var(--text-secondary);
  line-height: 1.75;
  transition: color 0.3s ease;
}

/* 色调变量（journal 卡片使用 cyan / violet / amber） */
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

/* ---- journal / newsletter / about 三块归档内容 ---- */
.journal-section {
  border-top: 1px solid var(--border-color);
  transition: border-color 0.3s ease;
}

.journal-section .section-heading h2 {
  font-size: clamp(1.8rem, 4.2vw, 3.6rem);
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
  height: clamp(18rem, 34vw, 26rem);
  margin-bottom: 1.5rem;
  overflow: hidden;
  border: 1px solid var(--card-border);
  background: var(--card-bg);
  filter: grayscale(18%);
  transition: filter 0.3s ease, transform 0.3s ease, border-color 0.3s ease, background 0.3s ease;
}

.journal-image::after {
  content: "";
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 28% 22%, var(--project-glow), transparent 54%);
  opacity: 0.65;
  pointer-events: none;
  z-index: 1;
  transition: opacity 0.3s ease;
}

.journal-card:hover .journal-image {
  filter: grayscale(0);
  transform: scale(1.015);
}

.journal-img-content {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  z-index: 0;
  transition: transform 0.4s ease;
}

.journal-card:hover .journal-img-content {
  transform: scale(1.045);
}

.journal-image span {
  position: absolute;
  top: 0;
  right: 0;
  padding: 1.1rem;
  color: var(--text-secondary);
  opacity: 0.7;
  font-size: 3rem;
  font-weight: 800;
  z-index: 2;
  transition: color 0.3s ease;
}

.journal-category,
.about-content p {
  color: var(--hero-kicker-color);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  transition: color 0.3s ease;
}

.journal-card h3 {
  margin-top: 0.45rem;
  color: var(--text-title);
  font-family: var(--font-serif), inherit;
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
  color: var(--text-secondary);
  transition: color 0.3s ease;
}

.journal-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.9rem;
  align-items: center;
  margin-top: 1.4rem;
  color: var(--text-secondary);
  font-size: 0.82rem;
  transition: color 0.3s ease;
}

.author-avatar {
  width: 1.8rem;
  height: 1.8rem;
  border: 1px solid var(--border-color);
  border-radius: 999px;
  object-fit: cover;
  transition: border-color 0.3s ease;
}

.newsletter-band {
  padding: clamp(4rem, 8vw, 7rem) clamp(1.25rem, 5vw, 5rem);
  background: var(--newsletter-bg);
  border-top: 1px solid var(--border-color);
  border-bottom: 1px solid var(--border-color);
  transition: background 0.3s ease, border-color 0.3s ease;
}

.newsletter-inner {
  max-width: 46rem;
  margin: 0 auto;
  text-align: center;
}

.newsletter-inner p {
  max-width: 40rem;
  margin: 1rem auto 2rem;
  color: var(--card-text);
  line-height: 1.8;
  transition: color 0.3s ease;
}

.newsletter-form {
  display: flex;
  max-width: 42rem;
  margin: 0 auto;
}

.newsletter-form input {
  min-width: 0;
  flex: 1;
  border: 1px solid var(--newsletter-input-border);
  background: var(--newsletter-input-bg);
  padding: 1rem 1.2rem;
  color: var(--text-primary);
  outline: none;
  transition: border-color 0.3s ease, background 0.3s ease, color 0.3s ease;
}

.newsletter-form input:focus {
  border-color: var(--primary-btn-border);
}

.newsletter-form button {
  border: 1px solid var(--primary-btn-border);
  background: transparent;
  color: var(--primary-btn-text);
  padding: 0 2rem;
  font-size: 0.8rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  position: relative;
  overflow: hidden;
  z-index: 1;
  transition: color 0.35s ease, border-color 0.35s ease;
  cursor: pointer;
}

.newsletter-form button::before {
  content: "";
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background-color: var(--primary-btn-sweep);
  transition: left 0.35s cubic-bezier(0.25, 0.1, 0.25, 1);
  z-index: -1;
}

.newsletter-form button:hover::before {
  left: 0;
}

.newsletter-form button:hover {
  color: var(--primary-btn-sweep-text);
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
  border: 1px solid var(--card-border);
  background: url('/images/pic5.jpg') no-repeat center center;
  background-size: cover;
  transition: border-color 0.3s ease;
}

.about-visual::before {
  position: absolute;
  inset: -1.6rem 1.6rem 1.6rem -1.6rem;
  z-index: -1;
  border: 1px solid var(--primary-btn-border);
  content: "";
  transition: border-color 0.3s ease;
}

.about-content {
  display: grid;
  gap: 1.2rem;
}

.about-content span {
  color: var(--text-secondary);
  line-height: 1.85;
  transition: color 0.3s ease;
}

/* ---- .outline-button 同样是共享类（hero 的入口按钮也在用），此处为副本 ---- */
.outline-button {
  justify-self: start;
  border: 1px solid var(--outline-btn-border);
  padding: 0 1.4rem;
  color: var(--outline-btn-text);
  font-size: 0.82rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  background: transparent;
  --sweep-color: var(--outline-btn-sweep);
  --sweep-text-color: var(--outline-btn-sweep-text);
  min-height: 2.85rem;
}

/* ---- 响应式：以下规则原本散落在 Dashboard 的共享 @media 块里，且只服务本页内容 ---- */
@media (max-width: 1024px) {
  .journal-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .newsletter-form {
    flex-direction: column;
  }

  .newsletter-form button {
    min-height: 3rem;
    padding: 1rem 0;
  }

  .about-visual::before {
    display: none;
  }
}
</style>
