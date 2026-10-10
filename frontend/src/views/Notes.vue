<script setup lang="ts">
/**
 * 学习笔记模块 (Notes.vue)
 *
 * 对应文档：docs/16_Notes学习模块视觉重构与体验优化方案.md
 */
import { ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import UiButton from '../components/ui/UiButton.vue';
import UiSurface from '../components/ui/UiSurface.vue';
import AmbientGlow from '../components/ui/AmbientGlow.vue';
import KnowledgeMapBackground from '../components/KnowledgeMapBackground.vue';
import StarfieldBackground from '../components/StarfieldBackground.vue';
import AppNavbar from '../components/AppNavbar.vue';
import NotesDialog from '../features/notes/components/NotesDialog.vue';
import NotesGraph from '../features/notes/components/NotesGraph.vue';
import NotesProse from '../features/notes/components/NotesProse.vue';
import { notesAppearance } from '../features/notes/config/appearance';
import { useNotesWorkspace } from '../features/notes/composables/useNotesWorkspace';
const router = useRouter();
const { route, topics, topic, topicId, unit, loading, saving, error, notice, sections, queryText, sectionFilter, view, selectedId, selected, visibleUnits, visibleTopics, form, editing, editId, draft, draftUnit, tagText, previous, following, modalOpen, modalLabel, peerUnits, markdown, changeQuery, reload, newTopic, editTopic, sectionForm, unitForm, save, removeSection, removeTopic, removeUnit, dependencies, importFile, exportDraft, openUnit, closeModal, acceptDiscard, resetForm, unitPath, workspacePath, rememberWorkspace, switchTopic } = useNotesWorkspace();

const isDirectoryCollapsed = ref(false);
try {
  const saved = localStorage.getItem('km_notes_sidebar_collapsed');
  if (saved !== null) {
    isDirectoryCollapsed.value = saved === 'true';
  } else if (typeof window !== 'undefined' && window.innerWidth < 800) {
    isDirectoryCollapsed.value = true;
  }
} catch {}
watch(isDirectoryCollapsed, (val) => {
  try {
    localStorage.setItem('km_notes_sidebar_collapsed', String(val));
  } catch {}
});

function openTopic(id: string) {
  router.push(`/notes/${id}`);
}

function handleCardMouseMove(event: MouseEvent) {
  const card = event.currentTarget as HTMLElement;
  if (!card) return;
  const rect = card.getBoundingClientRect();
  card.style.setProperty('--mouse-x', `${event.clientX - rect.left}px`);
  card.style.setProperty('--mouse-y', `${event.clientY - rect.top}px`);
}

function getUnitSummary(content: string, title?: string): string {
  if (!content) return '尚无正文描述';
  // 移除 YAML Frontmatter
  const clean = content.replace(/^---\n[\s\S]*?\n---\n/, '');
  // 按段落切分寻找实质性摘要内容
  const paragraphs = clean.split(/\n\s*\n/);
  for (const rawPara of paragraphs) {
    const trimmed = rawPara.trim();
    if (!trimmed) continue;
    // 忽略 Markdown 标题 (#, ## 等)
    if (/^#{1,6}\s+/.test(trimmed)) continue;
    // 忽略通用模版段首标题字样
    if (/^(核心目标|学习检查|参考资料|常见误区|代码示例)/.test(trimmed)) continue;
    // 清除 Markdown 格式符号
    const cleanText = trimmed
      .replace(/[#*`_~]/g, '')
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
      .replace(/\n+/g, ' ')
      .trim();
    if (cleanText && cleanText !== title && cleanText.length > 4) {
      return cleanText.length > 95 ? cleanText.slice(0, 92) + '...' : cleanText;
    }
  }
  const fallback = clean.replace(/[#*`_~]/g, '').replace(/\n+/g, ' ').trim();
  return fallback ? (fallback.length > 95 ? fallback.slice(0, 92) + '...' : fallback) : '尚无正文描述';
}
</script>

<template>
<div class="notes-workspace notes-page">
  <KnowledgeMapBackground />
  <StarfieldBackground />
  <AppNavbar active="notes" />
  <AmbientGlow v-if="notesAppearance.ambientGlow" />
  <div class="notes-content" :inert="modalOpen">
    <header class="page-header">
      <nav aria-label="面包屑" class="notes-breadcrumb">
        <RouterLink to="/" class="crumb-link">
          首页
        </RouterLink>
        <span class="crumb-separator">/</span>
        <RouterLink to="/notes" :class="{ 'crumb-current': !topicId, 'crumb-link': topicId }">
          学习笔记
        </RouterLink>
        <template v-if="topic">
          <span class="crumb-separator">/</span>
          <span class="crumb-current">
            {{topic.title}}
          </span>
        </template>
      </nav>
      <div class="heading-row topic-header-row">
        <div>
          <template v-if="topicId && topic">
            <div class="topic-title-inline-group">
              <h1 class="topic-title-h1">
                <span>{{ topic.title }}</span>
                <span class="topic-switch-chevron" aria-hidden="true">⌵</span>
              </h1>
              <select
                class="topic-switch-select"
                aria-label="切换主题"
                :value="topicId"
                @change="switchTopic(($event.target as HTMLSelectElement).value)"
              >
                <option v-for="t in topics" :key="t.id" :value="t.id">
                  {{ t.title }}
                </option>
              </select>
            </div>
            <p class="topic-desc-compact">
              {{ topic.description || '把知识整理成目录，把理解连接成路线。' }}
            </p>
          </template>
          <template v-else>
            <p class="eyebrow">
              LEARNING NOTES
            </p>
            <h1>
              学习总览
            </h1>
            <p class="muted">
              把知识整理成目录，把理解连接成路线。
            </p>
          </template>
        </div>
        <UiButton v-if="!topicId" variant="primary" class="new-topic-btn" @click="newTopic">
          + 新建主题
        </UiButton>
        <div v-else-if="topic" class="topic-actions-row">
          <UiButton
            variant="primary"
            class="header-primary-btn"
            :disabled="!sections.length"
            @click="unitForm()"
          >
            + 新建单元
          </UiButton>
          <UiButton class="header-action-btn" @click="editTopic">
            主题设置
          </UiButton>
          <label class="import-control header-action-btn" :class="{ disabled: !sections.length }">
            导入 Markdown
            <input type="file" accept=".md,text/markdown" :disabled="!sections.length" @change="importFile" />
          </label>
        </div>
      </div>
    </header>
    <p v-if="notice" class="notice" role="status">
      {{notice}}
    </p>
    <div v-if="error" class="error" role="alert">
      {{error}}
      <UiButton @click="reload">
        重新载入
      </UiButton>
    </div>
    <p v-if="loading" class="empty" role="status">
      正在读取学习笔记…
    </p>
    <template v-else-if="!topicId">
      <div class="overview-toolbar">
        <label class="overview-search">
          <span class="search-label-text">搜索主题</span>
          <div class="search-box-wrapper">
            <svg class="search-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input class="ui-field search-input" type="search" :value="queryText" @input="changeQuery('q',($event.target as HTMLInputElement).value)" placeholder="搜索主题名称或简介…" />
          </div>
        </label>
      </div>
      <div class="topic-grid">
        <UiSurface
          v-for="t in visibleTopics"
          :key="t.id"
          as="article"
          class="topic-card"
          role="link"
          :tabindex="0"
          @click="openTopic(t.id)"
          @keydown.enter.prevent="openTopic(t.id)"
          @mousemove="handleCardMouseMove"
        >
          <div class="topic-card-top">
            <span class="topic-badge">
              {{String(t.sortOrder+1).padStart(2,'0')}}
            </span>
          </div>
          <h2>
            <RouterLink :to="`/notes/${t.id}`" @click.stop>
              {{t.title}}
            </RouterLink>
          </h2>
          <p>
            {{t.description}}
          </p>
          <footer>
            <span class="topic-stats">
              {{t.sectionCount}} 个目录 · {{t.unitCount}} 个单元
            </span>
            <span class="topic-enter-btn">
              进入主题 <span class="arrow" aria-hidden="true">→</span>
            </span>
          </footer>
        </UiSurface>
      </div>
      <p v-if="!visibleTopics.length&&!error" class="empty">
        {{queryText?'没有匹配的主题。':'还没有主题，先创建一个。'}}
      </p>
    </template>
    <template v-else-if="topic">
      <div v-if="topic.example" class="example-note-compact">
        <span class="example-icon" aria-hidden="true">💡</span>
        <span>初始内容来自旧版示例笔记，学习依赖请结合自己的理解核对。</span>
      </div>
      <div class="workspace-layout" :class="{ 'is-sidebar-collapsed': isDirectoryCollapsed }">
        <aside class="directory">
          <div class="heading-row">
            <h2>
              目录
            </h2>
            <UiButton @click="sectionForm()">
              新增
            </UiButton>
          </div>
          <UiButton variant="ghost" :aria-current="!sectionFilter?'page':undefined" @click="changeQuery('section','')">
            全部单元 · {{topic.units.length}}
          </UiButton>
          <div v-for="s in sections" :key="s.id" class="directory-section">
            <div class="directory-title">
              <button :aria-current="sectionFilter===s.id?'page':undefined" @click="changeQuery('section',s.id)">
                {{s.title}}
              </button>
              <button :aria-label="`设置目录 ${s.title}`" @click="sectionForm(s.id)">
                ···
              </button>
            </div>
            <RouterLink
              v-for="u in topic.units.filter(u=>u.sectionId===s.id)"
              :key="u.id"
              :to="{path:unitPath(u.id),query:route.query}"
              class="directory-unit-link"
              :class="{ 'is-active-unit': u.id === selectedId }"
              @click="rememberWorkspace(u.id)"
            >
              {{u.title}}
            </RouterLink>
            <span v-if="!topic.units.some(u=>u.sectionId===s.id)" class="muted">
              暂无单元
            </span>
          </div>
          <p v-if="!sections.length" class="muted">
            创建目录后即可添加单元。
          </p>
        </aside>
        <main class="workspace-main">
          <div class="workspace-toolbar">
            <div class="toolbar-left">
              <button
                type="button"
                class="sidebar-toggle-btn"
                :title="isDirectoryCollapsed ? '展开目录' : '收起目录'"
                :aria-label="isDirectoryCollapsed ? '展开目录' : '收起目录'"
                @click="isDirectoryCollapsed = !isDirectoryCollapsed"
              >
                <svg class="toggle-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <rect x="3" y="3" width="18" height="18" rx="2" stroke-width="2" />
                  <path d="M9 3v18" stroke-width="2" />
                  <path v-if="isDirectoryCollapsed" d="M14 10l2 2-2 2" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                  <path v-else d="M16 10l-2 2 2 2" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                </svg>
                <span class="toggle-text">{{ isDirectoryCollapsed ? '展开目录' : '收起目录' }}</span>
              </button>
              <div class="view-switch-segmented">
                <button
                  type="button"
                  class="segmented-btn"
                  :class="{ active: view === 'directory' }"
                  :aria-current="view === 'directory' ? 'page' : undefined"
                  aria-label="目录视图"
                  title="目录视图（按卡片浏览单元）"
                  @click="changeQuery('view', 'directory')"
                >
                  <svg class="segmented-icon" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M2 4.75A.75.75 0 012.75 4h14.5a.75.75 0 010 1.5H2.75A.75.75 0 012 4.75zM2 10a.75.75 0 01.75-.75h14.5a.75.75 0 010 1.5H2.75A.75.75 0 012 10zm0 5.25a.75.75 0 01.75-.75h14.5a.75.75 0 010 1.5H2.75a.75.75 0 01-.75-.75z" clip-rule="evenodd" />
                  </svg>
                  <span>单元</span>
                </button>
                <button
                  type="button"
                  class="segmented-btn"
                  :class="{ active: view === 'graph' }"
                  :aria-current="view === 'graph' ? 'page' : undefined"
                  aria-label="学习路线"
                  title="学习路线（图谱依赖关系）"
                  @click="changeQuery('view', 'graph')"
                >
                  <svg class="segmented-icon" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M10 2a.75.75 0 01.75.75v1.5a.75.75 0 01-1.5 0v-1.5A.75.75 0 0110 2zM10 15a.75.75 0 01.75.75v1.5a.75.75 0 01-1.5 0v-1.5A.75.75 0 0110 15zM2 10a.75.75 0 01.75-.75h1.5a.75.75 0 010 1.5h-1.5A.75.75 0 012 10zM15 10a.75.75 0 01.75-.75h1.5a.75.75 0 010 1.5h-1.5A.75.75 0 0115 10z" />
                    <path fill-rule="evenodd" d="M12.5 10a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z" clip-rule="evenodd" />
                  </svg>
                  <span>依赖图</span>
                </button>
              </div>
              <div class="workspace-search-box">
                <svg class="search-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <input
                  class="ui-field workspace-search-input"
                  type="search"
                  :value="queryText"
                  @input="changeQuery('q',($event.target as HTMLInputElement).value)"
                  placeholder="搜索单元标题、标签或正文…"
                  aria-label="搜索单元"
                />
              </div>
            </div>
          </div>
          <template v-if="view==='directory'">
            <div class="unit-grid" :style="{'--preferred-columns':topic.preferredColumns}">
              <UiSurface
                v-for="u in visibleUnits"
                :key="u.id"
                as="article"
                class="unit-card"
                role="link"
                :tabindex="0"
                @click="openUnit(u.id)"
                @keydown.enter.prevent="openUnit(u.id)"
                @mousemove="handleCardMouseMove"
              >
                <div class="unit-card-header">
                  <span class="unit-section-badge">
                    {{ sections.find(s=>s.id===u.sectionId)?.title || '未分类' }}
                  </span>
                  <span class="unit-index-badge">
                    {{ String((topic.units.findIndex(unit => unit.id === u.id) + 1)).padStart(2, '0') }}
                  </span>
                </div>
                <h2 class="unit-card-title">
                  <button :data-unit-id="u.id" @click.stop="openUnit(u.id)">
                    {{ u.title }}
                  </button>
                </h2>
                <p class="unit-card-summary">
                  {{ getUnitSummary(u.content, u.title) }}
                </p>
                <footer class="unit-card-footer">
                  <span class="unit-deps-count">
                    {{ dependencies(u.id, 'before').length }} 个前置 · {{ dependencies(u.id, 'after').length }} 个后续
                  </span>
                  <span class="unit-read-cta">
                    阅读笔记 <span class="arrow" aria-hidden="true">→</span>
                  </span>
                </footer>
              </UiSurface>
            </div>
            <p v-if="!visibleUnits.length" class="empty">
              {{topic.units.length?'没有匹配的单元，请调整搜索或目录筛选。':'还没有知识单元。'}}
            </p>
          </template>
          <template v-else>
            <div class="workspace-graph-container">
              <NotesGraph
                :topic="topic"
                :selected="selectedId"
                :matches="visibleUnits.map(u=>u.id)"
                @select="changeQuery('selected',$event)"
              />

              <!-- 底部停靠详情与快速操作栏 (Docked Bottom Inspector) -->
              <Transition name="inspector-slide">
                <div v-if="selected" class="docked-bottom-inspector">
                  <div class="inspector-left">
                    <span class="inspector-badge">
                      {{ String((topic.units.findIndex(u => u.id === selectedId) + 1)).padStart(2, '0') }}
                    </span>
                    <div class="inspector-meta">
                      <div class="inspector-title-row">
                        <h3 class="inspector-title">{{ selected.title }}</h3>
                        <span class="inspector-section-tag">
                          {{ sections.find(s => s.id === selected?.sectionId)?.title }}
                        </span>
                      </div>
                      <p class="inspector-excerpt">
                        {{ selected.content.replace(/[#*`\n]/g, ' ').trim().slice(0, 85) || '尚无正文描述' }}
                      </p>
                    </div>
                  </div>

                  <div class="inspector-center">
                    <div class="inspector-dep-group">
                      <span class="dep-pill before">前置</span>
                      <div class="dep-chips-wrap">
                        <button
                          v-for="u in dependencies(selected.id, 'before')"
                          :key="u.id"
                          type="button"
                          class="dep-chip before"
                          :title="`选中前置单元：${u.title}`"
                          @click="changeQuery('selected', u.id)"
                        >
                          {{ u.title }}
                        </button>
                        <span v-if="!dependencies(selected.id, 'before').length" class="dep-none">无</span>
                      </div>
                    </div>
                    <div class="inspector-dep-group">
                      <span class="dep-pill after">后续</span>
                      <div class="dep-chips-wrap">
                        <button
                          v-for="u in dependencies(selected.id, 'after')"
                          :key="u.id"
                          type="button"
                          class="dep-chip after"
                          :title="`选中后续单元：${u.title}`"
                          @click="changeQuery('selected', u.id)"
                        >
                          {{ u.title }}
                        </button>
                        <span v-if="!dependencies(selected.id, 'after').length" class="dep-none">无</span>
                      </div>
                    </div>
                  </div>

                  <div class="inspector-right">
                    <UiButton
                      variant="primary"
                      class="open-note-action-btn"
                      :data-unit-id="selected.id"
                      aria-label="打开笔记"
                      @click="openUnit(selected.id)"
                    >
                      📖 阅读笔记
                    </UiButton>
                    <button
                      type="button"
                      class="close-inspector-btn"
                      aria-label="关闭选择"
                      title="关闭选择"
                      @click="changeQuery('selected', '')"
                    >
                      ✕
                    </button>
                  </div>
                </div>
              </Transition>
            </div>
          </template>
        </main>
      </div>
    </template>
    <p v-else-if="!error" class="empty">
      主题不存在。
      <RouterLink to="/notes">
        返回学习总览
      </RouterLink>
    </p>
  </div>
  <NotesDialog v-if="modalOpen" :label="modalLabel" @close="closeModal">
    <header v-if="unit && form !== 'unit' && !editing" class="dialog-header reader-dialog-header">
      <div class="reader-header-meta">
        <nav aria-label="单元面包屑" class="reader-breadcrumb">
          <RouterLink to="/notes" class="crumb-link">
            学习笔记
          </RouterLink>
          <span class="crumb-sep">/</span>
          <RouterLink :to="{path:workspacePath(),query:route.query}" class="crumb-link">
            {{topic?.title}}
          </RouterLink>
          <span class="crumb-sep">/</span>
          <span class="crumb-section">
            {{sections.find(s=>s.id===unit?.sectionId)?.title}}
          </span>
        </nav>
        <h2 class="reader-article-title">
          {{unit.title}}
        </h2>
      </div>
      <div class="reader-header-actions">
        <UiButton class="reader-action-btn edit-btn" @click="unitForm(unit)">
          编辑
        </UiButton>
        <UiButton variant="danger" class="reader-action-btn delete-btn" :disabled="saving" @click="removeUnit">
          删除单元
        </UiButton>
        <button
          type="button"
          class="reader-close-btn"
          aria-label="关闭窗口"
          title="关闭窗口 (Esc)"
          @click="closeModal"
        >
          ✕
        </button>
      </div>
    </header>
    <header v-else class="dialog-header">
      <div>
        <p class="eyebrow">
          {{topic?.title||'学习笔记'}}
        </p>
        <h2>
          {{modalLabel}}
        </h2>
      </div>
      <UiButton :disabled="saving" aria-label="关闭窗口" @click="closeModal">
        关闭
      </UiButton>
    </header>
    <div v-if="error" class="error" role="alert">
      {{error}}
      <UiButton :disabled="saving" @click="reload">
        重新载入
      </UiButton>
    </div>
    <p v-if="notice" class="notice" role="status">
      {{notice}}
    </p>
    <p v-if="loading" class="empty">
      正在读取…
    </p>
    <form v-else-if="form==='topic'||form==='section'" class="editor" @submit.prevent="save">
      <label>
        {{form==='topic'?'主题名称':'目录名称'}}
        <input v-model="draft.title" class="ui-field" required maxlength="120" :disabled="saving" />
      </label>
      <label v-if="form==='topic'">
        简介
        <textarea v-model="draft.description" class="ui-field" maxlength="2000" :disabled="saving">
        </textarea>
      </label>
      <div class="form-columns">
        <label>
          排序位置（数字越小越靠前）
          <input v-model.number="draft.sortOrder" class="ui-field" type="number" min="0" max="100000" required :disabled="saving" />
        </label>
        <label v-if="form==='topic'">
          工作区偏好列数
          <input v-model.number="draft.preferredColumns" class="ui-field" type="number" min="1" max="6" required :disabled="saving" />
        </label>
      </div>
      <p v-if="form==='topic'" class="muted">
        列数控制目录卡片布局偏好；窄屏自动减少可见列数，学习路线按实际目录数量分列。
      </p>
      <footer class="actions">
        <UiButton type="submit" variant="primary" :disabled="saving">
          {{saving?'保存中…':'保存设置'}}
        </UiButton>
        <UiButton :disabled="saving" @click="closeModal">
          取消
        </UiButton>
        <UiButton v-if="editId" variant="danger" :disabled="saving" @click="form==='topic'?removeTopic():removeSection(editId)">
          删除{{form==='topic'?'主题':'目录'}}
        </UiButton>
      </footer>
    </form>
    <form v-else-if="form==='unit'||editing" class="editor" @submit.prevent="save">
      <label>
        笔记标题
        <input v-model="draftUnit.title" class="ui-field" required maxlength="200" :disabled="saving" />
      </label>
      <div class="form-columns">
        <label>
          目录归属
          <select v-model="draftUnit.sectionId" class="ui-field" aria-label="目录归属" required :disabled="saving">
            <option value="" disabled>
              请选择目录
            </option>
            <option v-for="s in sections" :key="s.id" :value="s.id">
              {{s.title}}
            </option>
          </select>
        </label>
        <label>
          标签（逗号分隔）
          <input v-model="tagText" class="ui-field" :disabled="saving" />
        </label>
      </div>
      <label>
        Markdown 正文
        <textarea v-model="draftUnit.content" class="ui-field body-editor" :disabled="saving" spellcheck="false">
        </textarea>
      </label>
      <div class="form-columns">
        <fieldset :disabled="saving">
          <legend>
            前节点 · 它依赖的单元
          </legend>
          <p v-if="!previous.length" class="muted">
            无前置依赖
          </p>
          <label v-for="u in peerUnits" :key="u.id" class="check">
            <input v-model="previous" type="checkbox" :value="u.id" />
            {{u.title}}
          </label>
        </fieldset>
        <fieldset :disabled="saving">
          <legend>
            后节点 · 依赖它的单元
          </legend>
          <p v-if="!following.length" class="muted">
            无后续依赖
          </p>
          <label v-for="u in peerUnits" :key="u.id" class="check">
            <input v-model="following" type="checkbox" :value="u.id" />
            {{u.title}}
          </label>
        </fieldset>
      </div>
      <p class="muted">
        关系仅限本主题，可多选或不选。循环关系将拒绝保存；改变目录不会自动添加或删除依赖。
      </p>
      <footer class="actions">
        <UiButton type="submit" variant="primary" :disabled="saving">
          {{saving?'保存中…':'保存笔记'}}
        </UiButton>
        <UiButton :disabled="saving" @click="editing&&unit? (acceptDiscard()&&resetForm()):closeModal()">
          取消
        </UiButton>
        <UiButton v-if="error" @click="exportDraft">
          导出草稿 JSON
        </UiButton>
      </footer>
    </form>
    <article v-else-if="unit" class="reader-document">
      <div v-if="unit.tags && unit.tags.length" class="tags reader-tags">
        <span v-for="tag in unit.tags" :key="tag">
          {{tag}}
        </span>
      </div>
      <NotesProse :html="markdown" />
      <section class="dependencies reader-dependencies">
        <div class="dependencies-header">
          <h3>
            学习依赖
          </h3>
          <span class="deps-tip">探索前置与后续知识单元</span>
        </div>
        <div class="dependencies-grid">
          <div v-for="direction in (['before','after'] as const)" :key="direction" class="dep-direction-box">
            <span class="dep-direction-label" :class="direction">
              {{direction==='before'?'前置单元':'后续单元'}}
            </span>
            <span v-if="!dependencies(unit!.id,direction).length" class="dep-direction-empty">
              无
            </span>
            <div v-else class="dep-direction-list">
              <RouterLink
                v-for="u in dependencies(unit!.id,direction)"
                :key="u.id"
                :to="{path:unitPath(u.id),query:route.query}"
                class="dep-direction-link"
              >
                {{u.title}} <span class="arrow" aria-hidden="true">→</span>
              </RouterLink>
            </div>
          </div>
        </div>
      </section>
    </article>
    <div v-else class="empty">
      知识单元不存在或已删除。
      <UiButton @click="closeModal">
        返回工作区
      </UiButton>
    </div>
  </NotesDialog>
</div>
</template>

<style scoped src="../features/notes/styles/theme.css"></style>
<style scoped src="../components/ui/controls.css"></style>
<style scoped>
.notes-page {
  position: relative;
  min-height: 100dvh;
  isolation: isolate;
  background: transparent;
  color: var(--text);
}
.notes-content {
  position: relative;
  z-index: 1;
  max-width: var(--notes-page-width);
  margin: 0 auto;
  padding: clamp(2rem, 3.5vw, 3.5rem) clamp(1.5rem, 4vw, 4.5rem) 5rem;
}
.page-header {
  margin-bottom: 20px;
}
.notes-breadcrumb {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #64748b;
  font-size: 13px;
  margin-bottom: 12px;
}
.notes-breadcrumb a.crumb-link {
  color: #94a3b8;
  text-decoration: none;
  transition: color 0.16s ease;
}
.notes-breadcrumb a.crumb-link:hover {
  color: #f8fafc;
  text-decoration: none;
}
.notes-breadcrumb .crumb-current {
  color: #e2e8f0;
  font-weight: 600;
}
.notes-breadcrumb .crumb-separator {
  color: #475569;
}
nav {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  color: var(--text-muted);
  font-size: 13px;
}
a {
  color: inherit;
  text-decoration: none;
}
a:hover {
  text-decoration: underline;
}
button:focus-visible,a:focus-visible,input:focus-visible {
  outline: 2px solid var(--ui-focus);
  outline-offset: 3px;
}
h1,h2 {
  overflow-wrap: anywhere;
}
h1 {
  font-size: clamp(28px, 3.5vw, 36px);
  font-weight: 850;
  line-height: 1.2;
  margin: 4px 0 8px;
  color: #ffffff;
  letter-spacing: -0.02em;
}
h2 {
  font-size: 19px;
  font-weight: 700;
  margin: 0 0 12px;
}
h3 {
  font-size: 17px;
  font-weight: 650;
}
p {
  line-height: 1.7;
}
.muted,.example-note {
  color: var(--text-muted);
  font-size: 14px;
}
.eyebrow {
  display: inline-block;
  font-size: 11px;
  font-weight: 700;
  color: #06b6d4;
  letter-spacing: .12em;
  margin: 0 0 6px;
}
.heading-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}
.heading-row>div {
  min-width: 0;
}
.heading-row>button {
  flex-shrink: 0;
}
.new-topic-btn {
  font-size: 13px;
  font-weight: 700;
  padding: 0 18px;
  min-height: 40px;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(124, 58, 237, 0.28);
}
.topic-title-inline-group {
  position: relative;
  display: inline-flex;
  align-items: center;
  margin: 0 0 4px;
  cursor: pointer;
}
.topic-title-h1 {
  margin: 0;
  font-size: clamp(25px, 3vw, 30px);
  font-weight: 850;
  color: #ffffff;
  letter-spacing: -0.02em;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  line-height: 1.2;
}
.topic-switch-chevron {
  font-size: 15px;
  color: #67e8f9;
  transition: transform 0.2s ease;
}
.topic-title-inline-group:hover .topic-switch-chevron {
  transform: translateY(2px);
}
.topic-switch-select {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  cursor: pointer;
  color-scheme: dark;
}
.topic-desc-compact {
  color: #94a3b8;
  font-size: 13px;
  margin: 0;
  line-height: 1.5;
  max-width: 650px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.topic-actions-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}
.header-primary-btn {
  height: 38px;
  padding: 0 16px;
  font-size: 13px;
  font-weight: 700;
  border-radius: 10px;
  box-shadow: 0 4px 18px rgba(124, 58, 237, 0.35);
}
.header-action-btn {
  height: 38px;
  padding: 0 14px;
  font-size: 12.5px;
  font-weight: 600;
  border-radius: 10px;
  background: rgba(15, 23, 42, 0.65);
  border: 1px solid rgba(148, 163, 184, 0.2);
  color: #94a3b8;
  backdrop-filter: blur(12px);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-sizing: border-box;
  transition: all 0.2s ease;
}
.header-action-btn:hover:not(.disabled) {
  background: rgba(30, 41, 59, 0.85);
  color: #f8fafc;
  border-color: rgba(148, 163, 184, 0.35);
  transform: translateY(-1px);
}
.example-note-compact {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-radius: 8px;
  background: rgba(234, 179, 8, 0.08);
  border: 1px solid rgba(234, 179, 8, 0.2);
  color: #fde047;
  font-size: 12px;
  margin-bottom: 16px;
}
.example-icon {
  font-size: 13px;
}
.overview-toolbar {
  margin-bottom: 28px;
  max-width: 520px;
}
.overview-search {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.search-label-text {
  font-size: 12px;
  font-weight: 650;
  color: #94a3b8;
  letter-spacing: 0.04em;
}
.search-box-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  width: 100%;
}
.search-icon {
  position: absolute;
  left: 14px;
  width: 18px;
  height: 18px;
  color: #64748b;
  pointer-events: none;
  transition: color 0.2s ease;
}
.search-input {
  width: 100%;
  height: 44px;
  padding-left: 42px !important;
  padding-right: 16px;
  border-radius: 12px !important;
  background: rgba(15, 23, 42, 0.65) !important;
  border: 1px solid rgba(148, 163, 184, 0.2) !important;
  color: #f8fafc;
  font-size: 14px;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  transition: all 0.2s ease;
}
.search-input:focus {
  border-color: #8b5cf6 !important;
  box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.2), 0 0 24px rgba(124, 58, 237, 0.18) !important;
  outline: none;
}
.search-box-wrapper:focus-within .search-icon {
  color: #a78bfa;
}
.topic-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 350px), 1fr));
  gap: 24px;
}
.topic-card {
  position: relative;
  cursor: pointer;
  padding: 28px;
  --ui-surface-bg: rgba(15, 23, 42, 0.62);
  --ui-surface-border: rgba(148, 163, 184, 0.16);
  --ui-surface-radius: 18px;
  display: flex;
  flex-direction: column;
  min-width: 0;
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.28);
  border-radius: 18px;
  overflow: hidden;
  outline: none;
  transition: transform 0.25s cubic-bezier(0.2, 0.8, 0.2, 1),
              border-color 0.25s ease,
              box-shadow 0.25s ease;
}
.topic-card::before {
  content: "";
  position: absolute;
  inset: 0;
  background: radial-gradient(
    220px circle at var(--mouse-x, 0) var(--mouse-y, 0),
    rgba(6, 182, 212, 0.18),
    rgba(124, 58, 237, 0.08) 55%,
    transparent 80%
  );
  opacity: 0;
  transition: opacity 0.3s ease;
  pointer-events: none;
  z-index: 1;
}
.topic-card:hover::before {
  opacity: 1;
}
.topic-card > * {
  position: relative;
  z-index: 2;
}
.topic-card:focus-visible {
  outline: 2px solid #8b5cf6;
  outline-offset: 3px;
}
.topic-card:hover {
  transform: translateY(-5px);
  --ui-surface-border: rgba(6, 182, 212, 0.45);
  box-shadow: 0 20px 48px rgba(0, 0, 0, 0.42),
              0 0 32px rgba(6, 182, 212, 0.16);
}
.topic-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.topic-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  font-weight: 750;
  letter-spacing: 0.06em;
  color: #67e8f9;
  background: rgba(6, 182, 212, 0.12);
  border: 1px solid rgba(6, 182, 212, 0.28);
  border-radius: 7px;
  padding: 2px 9px;
}
.topic-card h2 {
  font-size: 22px;
  font-weight: 750;
  margin: 0 0 10px;
  line-height: 1.3;
}
.topic-card h2 a {
  color: #f8fafc;
  text-decoration: none;
  transition: color 0.2s ease;
  display: block;
}
.topic-card:hover h2 a {
  color: #c084fc;
}
.topic-card p {
  color: #94a3b8;
  font-size: 13.5px;
  line-height: 1.65;
  margin: 0;
  overflow-wrap: anywhere;
}
.topic-card footer {
  margin-top: auto;
  padding-top: 24px;
  font-size: 12.5px;
  color: #718096;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-top: 1px solid rgba(148, 163, 184, 0.1);
}
.topic-stats {
  color: #94a3b8;
}
.topic-enter-btn {
  color: #818cf8;
  font-weight: 650;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  text-decoration: none;
  transition: color 0.2s ease;
}
.topic-enter-btn .arrow {
  display: inline-block;
  transition: transform 0.2s ease;
}
.topic-card:hover .topic-enter-btn {
  color: #c084fc;
}
.topic-card:hover .topic-enter-btn .arrow {
  transform: translateX(4px);
}
.unit-card {
  position: relative;
  cursor: pointer;
  padding: 22px;
  --ui-surface-bg: rgba(15, 23, 42, 0.65);
  --ui-surface-border: rgba(148, 163, 184, 0.16);
  --ui-surface-radius: 16px;
  display: flex;
  flex-direction: column;
  min-width: 0;
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.28);
  border-radius: 16px;
  overflow: hidden;
  outline: none;
  transition: transform 0.22s cubic-bezier(0.2, 0.8, 0.2, 1),
              border-color 0.22s ease,
              box-shadow 0.22s ease;
}
.unit-card::before {
  content: "";
  position: absolute;
  inset: 0;
  background: radial-gradient(
    200px circle at var(--mouse-x, 0) var(--mouse-y, 0),
    rgba(124, 58, 237, 0.18),
    rgba(6, 182, 212, 0.08) 55%,
    transparent 80%
  );
  opacity: 0;
  transition: opacity 0.3s ease;
  pointer-events: none;
  z-index: 1;
}
.unit-card:hover::before {
  opacity: 1;
}
.unit-card > * {
  position: relative;
  z-index: 2;
}
.unit-card:hover {
  transform: translateY(-4px);
  --ui-surface-border: rgba(139, 92, 246, 0.45);
  box-shadow: 0 16px 36px rgba(0, 0, 0, 0.38),
              0 0 24px rgba(124, 58, 237, 0.18);
}
.unit-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.unit-section-badge {
  font-size: 11.5px;
  font-weight: 650;
  color: #67e8f9;
  background: rgba(6, 182, 212, 0.12);
  border: 1px solid rgba(6, 182, 212, 0.25);
  border-radius: 6px;
  padding: 2px 8px;
  letter-spacing: 0.02em;
}
.unit-index-badge {
  font-family: ui-monospace, SFMono-Regular, monospace;
  font-size: 11.5px;
  font-weight: 700;
  color: #94a3b8;
}
.unit-card-title {
  margin: 0 0 8px;
  font-size: 17px;
  font-weight: 750;
  line-height: 1.35;
}
.unit-card-title button {
  color: #ffffff;
  background: none;
  border: 0;
  text-align: left;
  cursor: pointer;
  padding: 0;
  font: inherit;
  transition: color 0.18s ease;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.unit-card:hover .unit-card-title button {
  color: #c084fc;
}
.unit-card-summary {
  color: #94a3b8;
  font-size: 13px;
  line-height: 1.6;
  margin: 0 0 16px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.unit-card-footer {
  margin-top: auto;
  padding-top: 14px;
  border-top: 1px solid rgba(148, 163, 184, 0.1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
  color: #718096;
}
.unit-deps-count {
  color: #94a3b8;
}
.unit-read-cta {
  color: #818cf8;
  font-weight: 650;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  transition: color 0.18s ease;
}
.unit-read-cta .arrow {
  display: inline-block;
  transition: transform 0.18s ease;
}
.unit-card:hover .unit-read-cta {
  color: #c084fc;
}
.unit-card:hover .unit-read-cta .arrow {
  transform: translateX(4px);
}
.workspace-layout {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  gap: 28px;
  margin-top: 24px;
  align-items: start;
  transition: grid-template-columns 0.28s cubic-bezier(0.16, 1, 0.3, 1), gap 0.28s ease;
}
.workspace-layout.is-sidebar-collapsed {
  grid-template-columns: 0px minmax(0, 1fr);
  gap: 0px;
}
.directory {
  position: relative;
  background: rgba(15, 23, 42, 0.55);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 16px;
  padding: 20px;
  min-height: 400px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.25);
  transition: opacity 0.24s ease, transform 0.28s ease, padding 0.28s ease;
  overflow: hidden;
}
.workspace-layout.is-sidebar-collapsed .directory {
  opacity: 0;
  pointer-events: none;
  transform: translateX(-16px);
  padding: 0;
  border-width: 0;
}
.directory h2 {
  margin: 0;
  font-size: 16px;
}
.directory-title {
  display: flex;
  justify-content: space-between;
  gap: 6px;
  margin-top: 16px;
}
.directory-title button {
  color: #e2e8f0;
  background: none;
  border: 0;
  cursor: pointer;
  text-align: left;
  font-weight: 650;
  font-size: 13.5px;
  transition: color 0.18s ease;
}
.directory-title button:hover {
  color: #a78bfa;
}
.directory-title button[aria-current] {
  color: #67e8f9;
}
.directory-unit-link {
  display: block;
  margin: 4px 0 4px 8px;
  padding: 5px 10px;
  font-size: 13px;
  color: #94a3b8;
  border-radius: 7px;
  text-decoration: none;
  transition: all 0.18s ease;
  overflow-wrap: anywhere;
}
.directory-unit-link:hover {
  color: #f8fafc;
  background: rgba(148, 163, 184, 0.08);
}
.directory-unit-link.is-active-unit {
  color: #c084fc;
  background: rgba(168, 85, 247, 0.14);
  border-left: 3px solid #a855f7;
  font-weight: 650;
  padding-left: 9px;
  border-radius: 0 7px 7px 0;
}

.workspace-main {
  min-width: 0;
}
.workspace-toolbar {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
  min-height: 42px;
}
.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  max-width: 620px;
}
.sidebar-toggle-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 40px;
  padding: 0 12px;
  border-radius: 10px;
  background: rgba(15, 23, 42, 0.65);
  border: 1px solid rgba(148, 163, 184, 0.18);
  color: #94a3b8;
  font-size: 12.5px;
  font-weight: 650;
  cursor: pointer;
  backdrop-filter: blur(12px);
  transition: all 0.2s ease;
  flex-shrink: 0;
}
.sidebar-toggle-btn:hover {
  background: rgba(30, 41, 59, 0.8);
  color: #f8fafc;
  border-color: rgba(139, 92, 246, 0.45);
}
.toggle-icon {
  width: 16px;
  height: 16px;
}
.workspace-search-box {
  position: relative;
  display: flex;
  align-items: center;
  width: 100%;
}
.workspace-search-input {
  width: 100%;
  height: 40px;
  padding-left: 38px !important;
  padding-right: 14px;
  border-radius: 10px !important;
  background: rgba(15, 23, 42, 0.65) !important;
  border: 1px solid rgba(148, 163, 184, 0.18) !important;
  color: #f8fafc;
  font-size: 13.5px;
  backdrop-filter: blur(12px);
  transition: all 0.2s ease;
}
.workspace-search-input:focus {
  border-color: #8b5cf6 !important;
  box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.2) !important;
  outline: none;
}
.workspace-search-box .search-icon {
  position: absolute;
  left: 12px;
  width: 16px;
  height: 16px;
  color: #64748b;
  pointer-events: none;
}
.workspace-search-box:focus-within .search-icon {
  color: #a78bfa;
}

.view-switch-segmented {
  display: inline-flex;
  align-items: center;
  padding: 3px;
  background: rgba(15, 23, 42, 0.65);
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 10px;
  backdrop-filter: blur(12px);
  gap: 2px;
  flex-shrink: 0;
}
.segmented-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 32px;
  padding: 0 12px;
  font-size: 12.5px;
  font-weight: 650;
  color: #94a3b8;
  background: transparent;
  border: none;
  border-radius: 7px;
  cursor: pointer;
  transition: all 0.18s ease;
}
.segmented-btn:hover {
  color: #f8fafc;
  background: rgba(148, 163, 184, 0.1);
}
.segmented-btn.active {
  color: #ffffff;
  background: #7c3aed;
  box-shadow: 0 2px 10px rgba(124, 58, 237, 0.4);
}
.segmented-icon {
  width: 14px;
  height: 14px;
}

.import-control.rail-btn {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 10px;
  height: 36px;
  font-size: 12.5px;
  font-weight: 600;
  background: rgba(15, 23, 42, 0.65);
  color: #94a3b8;
  backdrop-filter: blur(12px);
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s ease;
}
.import-control.rail-btn:hover:not(.disabled) {
  background: rgba(30, 41, 59, 0.85);
  color: #f8fafc;
  border-color: rgba(148, 163, 184, 0.35);
  transform: translateY(-1px);
}
.import-control input {
  position: absolute;
  inset: 0;
  width: 100%;
  opacity: 0;
  cursor: pointer;
}
.import-control:focus-within {
  outline: 2px solid var(--ui-focus);
  outline-offset: 3px;
}
.import-control.disabled {
  opacity: .45;
  cursor: not-allowed;
  pointer-events: none;
}

.unit-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit,minmax(min(100%,max(230px,calc((100% - (var(--preferred-columns) - 1)*16px)/var(--preferred-columns)))),1fr));
  gap: 16px;
}
.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 12px 0 24px;
}
.tags span {
  padding: 3px 8px;
  font-size: 11px;
  border: 1px solid var(--notes-border);
  border-radius: 5px;
  color: var(--notes-code-text);
}

.workspace-graph-container {
  position: relative;
}

/* 底部停靠详情与快速操作栏 (Docked Bottom Inspector) */
.docked-bottom-inspector {
  position: sticky;
  bottom: 16px;
  z-index: 30;
  margin-top: 14px;
  padding: 12px 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  background: rgba(15, 23, 42, 0.9);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 14px;
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.45);
}

.inspector-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex: 1;
  max-width: 440px;
}

.inspector-badge {
  font-family: ui-monospace, SFMono-Regular, monospace;
  font-size: 11px;
  font-weight: 750;
  color: #67e8f9;
  background: rgba(6, 182, 212, 0.14);
  border: 1px solid rgba(6, 182, 212, 0.28);
  border-radius: 6px;
  padding: 2px 6px;
  flex-shrink: 0;
}

.inspector-meta {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.inspector-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.inspector-title {
  margin: 0;
  font-size: 14.5px;
  font-weight: 750;
  color: #ffffff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.inspector-section-tag {
  font-size: 11px;
  color: #94a3b8;
  background: rgba(148, 163, 184, 0.12);
  padding: 1px 6px;
  border-radius: 4px;
  flex-shrink: 0;
}

.inspector-excerpt {
  margin: 0;
  font-size: 12px;
  color: #94a3b8;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.4;
}

.inspector-center {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-shrink: 0;
}

.inspector-dep-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.dep-pill {
  font-size: 10.5px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 4px;
  font-family: ui-monospace, SFMono-Regular, monospace;
}
.dep-pill.before {
  color: #67e8f9;
  background: rgba(6, 182, 212, 0.14);
  border: 1px solid rgba(6, 182, 212, 0.28);
}
.dep-pill.after {
  color: #c084fc;
  background: rgba(168, 85, 247, 0.14);
  border: 1px solid rgba(168, 85, 247, 0.28);
}

.dep-chips-wrap {
  display: flex;
  align-items: center;
  gap: 5px;
  flex-wrap: wrap;
  max-width: 260px;
}

.dep-chip {
  height: 24px;
  padding: 0 8px;
  font-size: 11.5px;
  font-weight: 600;
  border-radius: 6px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  background: rgba(30, 41, 59, 0.6);
  color: #e2e8f0;
  cursor: pointer;
  transition: all 0.18s ease;
  white-space: nowrap;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.dep-chip.before:hover {
  border-color: #06b6d4;
  background: rgba(6, 182, 212, 0.18);
  color: #67e8f9;
}
.dep-chip.after:hover {
  border-color: #c084fc;
  background: rgba(168, 85, 247, 0.18);
  color: #e9d5ff;
}

.dep-none {
  font-size: 11.5px;
  color: #64748b;
}

.inspector-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.open-note-action-btn {
  height: 36px;
  padding: 0 16px;
  font-size: 12.5px;
  font-weight: 700;
  border-radius: 9px;
}

.close-inspector-btn {
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: #64748b;
  font-size: 14px;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.18s ease;
}
.close-inspector-btn:hover {
  color: #f8fafc;
  background: rgba(148, 163, 184, 0.15);
}

.inspector-slide-enter-active,
.inspector-slide-leave-active {
  transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1);
}
.inspector-slide-enter-from,
.inspector-slide-leave-to {
  opacity: 0;
  transform: translateY(14px);
}
.empty {
  padding: 40px 16px;
  color: var(--text-muted);
  text-align: center;
}
.error,.notice {
  padding: 12px 16px;
  margin: 16px 0;
  border: 1px solid var(--notes-border);
  border-radius: 10px;
  overflow-wrap: anywhere;
}
.error {
  color: #fda4af;
}
.notice {
  color: #6ee7b7;
}
.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 20px 28px;
  border-bottom: 1px solid var(--notes-border);
}
.dialog-header h2 {
  margin: 0;
}
.reader-dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 18px 28px;
  border-bottom: 1px solid var(--notes-border);
  background: rgba(15, 23, 42, 0.4);
}
.reader-header-meta {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.reader-breadcrumb {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #64748b;
  margin: 0;
}
.reader-breadcrumb a.crumb-link {
  color: #94a3b8;
  text-decoration: none;
  transition: color 0.16s ease;
}
.reader-breadcrumb a.crumb-link:hover {
  color: #f8fafc;
}
.crumb-sep {
  color: #475569;
}
.crumb-section {
  color: #67e8f9;
  font-weight: 600;
}
.reader-article-title {
  margin: 0;
  font-size: clamp(20px, 2.6vw, 24px);
  font-weight: 800;
  color: #ffffff;
  letter-spacing: -0.01em;
  line-height: 1.3;
}
.reader-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.reader-action-btn {
  height: 34px;
  padding: 0 14px;
  font-size: 12.5px;
  font-weight: 600;
  border-radius: 8px;
}
.reader-action-btn.delete-btn {
  background: rgba(239, 68, 68, 0.12);
  border: 1px solid rgba(239, 68, 68, 0.28);
  color: #f87171;
}
.reader-action-btn.delete-btn:hover {
  background: rgba(239, 68, 68, 0.22);
  color: #fca5a5;
}
.reader-close-btn {
  width: 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: #64748b;
  font-size: 15px;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.18s ease;
}
.reader-close-btn:hover {
  color: #f8fafc;
  background: rgba(148, 163, 184, 0.15);
}
.editor {
  padding: 24px 28px;
  display: grid;
  gap: 20px;
}
.editor>label,.form-columns>label {
  display: grid;
  gap: 8px;
  font-size: 13px;
}
.form-columns {
  display: grid;
  grid-template-columns: repeat(2,minmax(0,1fr));
  gap: 20px;
}
.body-editor {
  min-height: 360px;
  resize: vertical;
  font-family: ui-monospace,monospace;
  line-height: 1.7;
}
.editor textarea:not(.body-editor) {
  min-height: 100px;
}
.editor select {
  color-scheme: dark;
}
fieldset {
  border: 1px solid var(--notes-border);
  border-radius: 10px;
  padding: 12px;
  max-height: 260px;
  overflow: auto;
}
legend {
  font-size: 13px;
  padding: 0 6px;
}
.check {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 12px;
  margin: 10px 0;
  overflow-wrap: anywhere;
}
.check input {
  margin-top: 3px;
  accent-color: var(--notes-accent);
}
.reader-document {
  max-width: var(--notes-reading-width);
  margin: auto;
  padding: 24px 28px 64px;
  overflow-wrap: anywhere;
}
.reader-tags {
  margin: 0 0 16px;
}
.reader-dependencies {
  margin-top: 48px;
  border-top: 1px solid var(--notes-border);
  padding-top: 24px;
}
.dependencies-header {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 16px;
}
.dependencies-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #f8fafc;
}
.deps-tip {
  font-size: 12px;
  color: #64748b;
}
.dependencies-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}
.dep-direction-box {
  background: rgba(15, 23, 42, 0.5);
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 12px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.dep-direction-label {
  display: inline-block;
  align-self: flex-start;
  font-size: 11px;
  font-weight: 750;
  padding: 2px 8px;
  border-radius: 5px;
  font-family: ui-monospace, SFMono-Regular, monospace;
}
.dep-direction-label.before {
  color: #67e8f9;
  background: rgba(6, 182, 212, 0.12);
  border: 1px solid rgba(6, 182, 212, 0.28);
}
.dep-direction-label.after {
  color: #c084fc;
  background: rgba(168, 85, 247, 0.12);
  border: 1px solid rgba(168, 85, 247, 0.28);
}
.dep-direction-empty {
  font-size: 12.5px;
  color: #64748b;
}
.dep-direction-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.dep-direction-link {
  font-size: 13px;
  color: #94a3b8;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 6px;
  border-radius: 6px;
  transition: all 0.18s ease;
}
.dep-direction-link:hover {
  color: #f8fafc;
  background: rgba(148, 163, 184, 0.1);
}
.dep-direction-link .arrow {
  color: #818cf8;
  font-size: 12px;
  transition: transform 0.18s ease;
}
.dep-direction-link:hover .arrow {
  transform: translateX(3px);
  color: #c084fc;
}
@media(max-width:800px) {
  .notes-content {
    padding: 28px 16px 56px;
  }
  .workspace-layout {
    grid-template-columns: 1fr;
  }
  .directory {
    border: 1px solid var(--notes-border);
    border-radius: 12px;
    padding: 16px;
    max-height: 240px;
    overflow: auto;
  }
  .heading-row {
    align-items: flex-start;
  }
  .topic-header-row {
    flex-direction: column;
    align-items: stretch;
    gap: 14px;
  }
  .topic-actions-row {
    flex-wrap: wrap;
    gap: 8px;
  }
  .workspace-toolbar {
    flex-wrap: wrap;
    gap: 10px;
  }
  .toolbar-left {
    flex-wrap: wrap;
    max-width: none;
    gap: 8px;
  }
  .docked-bottom-inspector {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
    padding: 14px;
  }
  .inspector-left,
  .inspector-center,
  .inspector-right {
    width: 100%;
    max-width: none;
  }
  .inspector-right {
    justify-content: space-between;
  }
  .reader-dialog-header {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
    padding: 16px;
  }
  .reader-header-actions {
    justify-content: flex-end;
  }
  .dependencies-grid {
    grid-template-columns: 1fr;
  }
  .topic-card {
    padding: 20px;
  }
  .form-columns {
    grid-template-columns: 1fr;
  }
  .dialog-header {
    padding: 16px;
  }
  .editor {
    padding: 20px 16px;
  }
  .reader-document {
    padding: 18px 16px 48px;
  }
  .unit-grid {
    grid-template-columns: 1fr;
  }
  .notes-content nav {
    gap: 6px;
  }
}
@media(prefers-reduced-motion:reduce) {
  * {
    scroll-behavior: auto;
  }
}

</style>
