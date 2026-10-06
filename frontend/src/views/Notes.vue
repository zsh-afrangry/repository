<script setup lang="ts">
import UiButton from '../components/ui/UiButton.vue';
import UiSurface from '../components/ui/UiSurface.vue';
import AmbientGlow from '../components/ui/AmbientGlow.vue';
import NotesDialog from '../features/notes/components/NotesDialog.vue';
import NotesGraph from '../features/notes/components/NotesGraph.vue';
import NotesProse from '../features/notes/components/NotesProse.vue';
import { notesAppearance } from '../features/notes/config/appearance';
import { useNotesWorkspace } from '../features/notes/composables/useNotesWorkspace';
const { route, topics, topic, topicId, unit, loading, saving, error, notice, sections, queryText, sectionFilter, view, selectedId, selected, visibleUnits, visibleTopics, form, editing, editId, draft, draftUnit, tagText, previous, following, modalOpen, modalLabel, peerUnits, markdown, changeQuery, reload, newTopic, editTopic, sectionForm, unitForm, save, removeSection, removeTopic, removeUnit, dependencies, importFile, exportDraft, openUnit, closeModal, acceptDiscard, resetForm, unitPath, workspacePath, rememberWorkspace, switchTopic } = useNotesWorkspace();
</script>

<template>
<div class="notes-workspace notes-page">
  <AmbientGlow v-if="notesAppearance.ambientGlow" />
  <div class="notes-content" :inert="modalOpen">
    <header class="page-header">
      <nav aria-label="面包屑">
        <RouterLink to="/">
          KnowledgeMap
        </RouterLink>
        <span>
          /
        </span>
        <RouterLink to="/notes">
          学习笔记
        </RouterLink>
        <template v-if="topic">
          <span>
            /
          </span>
          <span>
            {{topic.title}}
          </span>
        </template>
      </nav>
      <div class="heading-row">
        <div>
          <p class="eyebrow">
            LEARNING NOTES
          </p>
          <h1>
            {{topicId?(topic?.title||'主题工作区'):'学习总览'}}
          </h1>
          <p class="muted">
            {{topic?.description||'把知识整理成目录，把理解连接成路线。'}}
          </p>
        </div>
        <UiButton v-if="!topicId" variant="primary" @click="newTopic">
          新建主题
        </UiButton>
        <div v-else-if="topic" class="topic-actions">
          <select class="ui-field topic-switch" aria-label="切换主题" :value="topicId" @change="switchTopic(($event.target as HTMLSelectElement).value)">
            <option v-for="t in topics" :key="t.id" :value="t.id">
              {{t.title}}
            </option>
          </select>
          <UiButton @click="editTopic">
            主题设置
          </UiButton>
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
      <label class="overview-search">
        搜索主题
        <input class="ui-field" type="search" :value="queryText" @input="changeQuery('q',($event.target as HTMLInputElement).value)" placeholder="主题名称或简介" />
      </label>
      <div class="topic-grid">
        <UiSurface v-for="t in visibleTopics" :key="t.id" as="article" class="topic-card">
          <span class="eyebrow">
            {{String(t.sortOrder+1).padStart(2,'0')}}
          </span>
          <h2>
            <RouterLink :to="`/notes/${t.id}`">
              {{t.title}}
            </RouterLink>
          </h2>
          <p>
            {{t.description}}
          </p>
          <footer>
            {{t.sectionCount}} 个目录 · {{t.unitCount}} 个单元
            <RouterLink :to="`/notes/${t.id}`">
              进入主题 →
            </RouterLink>
          </footer>
        </UiSurface>
      </div>
      <p v-if="!visibleTopics.length&&!error" class="empty">
        {{queryText?'没有匹配的主题。':'还没有主题，先创建一个。'}}
      </p>
    </template>
    <template v-else-if="topic">
      <p v-if="topic.example" class="example-note">
        初始内容来自旧版示例笔记，学习依赖请结合自己的理解核对。
      </p>
      <div class="workspace-layout">
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
            <RouterLink v-for="u in topic.units.filter(u=>u.sectionId===s.id)" :key="u.id" :to="{path:unitPath(u.id),query:route.query}" @click="rememberWorkspace(u.id)">
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
            <label>
              搜索单元
              <input class="ui-field" type="search" :value="queryText" @input="changeQuery('q',($event.target as HTMLInputElement).value)" placeholder="标题、标签或正文" />
            </label>
            <div class="actions">
              <UiButton :aria-current="view==='directory'?'page':undefined" @click="changeQuery('view','directory')">
                目录视图
              </UiButton>
              <UiButton :aria-current="view==='graph'?'page':undefined" @click="changeQuery('view','graph')">
                学习路线
              </UiButton>
              <UiButton variant="primary" :disabled="!sections.length" @click="unitForm()">
                新建单元
              </UiButton>
              <label class="import-control" :class="{disabled:!sections.length}">
                导入 Markdown
                <input type="file" accept=".md,text/markdown" :disabled="!sections.length" @change="importFile" />
              </label>
            </div>
          </div>
          <template v-if="view==='directory'">
            <div class="unit-grid" :style="{'--preferred-columns':topic.preferredColumns}">
              <UiSurface v-for="u in visibleUnits" :key="u.id" as="article" class="unit-card">
                <p class="eyebrow">
                  {{sections.find(s=>s.id===u.sectionId)?.title}}
                </p>
                <h2>
                  <button :data-unit-id="u.id" @click="openUnit(u.id)">
                    {{u.title}}
                  </button>
                </h2>
                <p>
                  {{u.content.replace(/[#*`]/g,'').slice(0,120) || '尚无正文'}}
                </p>
                <div class="tags">
                  <span v-for="tag in u.tags" :key="tag">
                    {{tag}}
                  </span>
                </div>
                <footer>
                  {{dependencies(u.id,'before').length}} 个前置 · {{dependencies(u.id,'after').length}} 个后续
                </footer>
              </UiSurface>
            </div>
            <p v-if="!visibleUnits.length" class="empty">
              {{topic.units.length?'没有匹配的单元，请调整搜索或目录筛选。':'还没有知识单元。'}}
            </p>
          </template>
          <template v-else>
            <p class="muted">
              箭头 A → B 表示 B 依赖 A；点击节点查看直接关系。筛选外的单元会淡化。
            </p>
            <NotesGraph :topic="topic" :selected="selectedId" :matches="visibleUnits.map(u=>u.id)" @select="changeQuery('selected',$event)" />
            <UiSurface v-if="selected" class="selection">
              <h2>
                {{selected.title}}
              </h2>
              <p>
                前置：{{dependencies(selected.id,'before').map(u=>u.title).join('、')||'无'}}；后续：{{dependencies(selected.id,'after').map(u=>u.title).join('、')||'无'}}
              </p>
              <UiButton variant="primary" :data-unit-id="selected.id" @click="openUnit(selected.id)">
                打开笔记
              </UiButton>
              <UiButton @click="changeQuery('selected','')">
                清除选择
              </UiButton>
            </UiSurface>
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
    <header class="dialog-header">
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
      <nav aria-label="单元面包屑">
        <RouterLink to="/notes">
          学习笔记
        </RouterLink>
        /
        <RouterLink :to="{path:workspacePath(),query:route.query}">
          {{topic?.title}}
        </RouterLink>
        / {{sections.find(s=>s.id===unit?.sectionId)?.title}} / {{unit.title}}
      </nav>
      <div class="actions reader-actions">
        <UiButton @click="unitForm(unit)">
          编辑
        </UiButton>
        <UiButton variant="danger" :disabled="saving" @click="removeUnit">
          删除单元
        </UiButton>
      </div>
      <div class="tags">
        <span v-for="tag in unit.tags" :key="tag">
          {{tag}}
        </span>
      </div>
      <NotesProse :html="markdown" />
      <section class="dependencies">
        <h3>
          学习依赖
        </h3>
        <div v-for="direction in (['before','after'] as const)" :key="direction">
          <strong>
            {{direction==='before'?'前置单元':'后续单元'}}
          </strong>
          <span v-if="!dependencies(unit!.id,direction).length">
            无
          </span>
          <RouterLink v-for="u in dependencies(unit!.id,direction)" :key="u.id" :to="{path:unitPath(u.id),query:route.query}">
            {{u.title}}
          </RouterLink>
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
  background: linear-gradient(180deg,#0c111a,#101722);
  color: var(--text);
}
.notes-content {
  position: relative;
  max-width: var(--notes-page-width);
  margin: 0 auto;
  padding: 40px 28px 80px;
}
.page-header {
  margin-bottom: 32px;
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
  font-size: clamp(30px,4vw,46px);
  font-weight: 750;
  line-height: 1.2;
  margin: 10px 0 14px;
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
  font-size: 13px;
}
.eyebrow {
  font-size: 11px;
  color: var(--notes-accent);
  letter-spacing: .1em;
  margin: 0 0 8px;
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
.topic-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: flex-end;
}
.topic-switch {
  max-width: 180px;
  color-scheme: dark;
  font-size: 12px;
}
.overview-search {
  display: grid;
  gap: 8px;
  max-width: 480px;
  margin-bottom: 24px;
  font-size: 13px;
}
.topic-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit,minmax(min(100%,300px),1fr));
  gap: 20px;
}
.topic-card,.unit-card {
  padding: 24px;
  --ui-surface-bg: var(--notes-surface-raised);
  --ui-surface-border: var(--notes-border);
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.topic-card p,.unit-card p {
  color: var(--notes-text-muted);
  font-size: 13px;
  overflow-wrap: anywhere;
}
.topic-card footer,.unit-card footer {
  margin-top: auto;
  padding-top: 24px;
  font-size: 12px;
  color: var(--text-muted);
}
.topic-card footer {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}
.topic-card h2 {
  font-size: 24px;
}
.topic-card h2 a {
  display: block;
}
.workspace-layout {
  display: grid;
  grid-template-columns: 240px minmax(0,1fr);
  gap: 28px;
  margin-top: 24px;
}
.directory {
  border-right: 1px solid var(--notes-border);
  padding-right: 20px;
}
.directory h2 {
  margin: 0;
}
.directory-title {
  display: flex;
  justify-content: space-between;
  gap: 6px;
  margin-top: 20px;
}
.directory-title button {
  color: var(--text);
  background: none;
  border: 0;
  cursor: pointer;
  text-align: left;
  font-weight: 650;
}
.directory-title button[aria-current] {
  color: var(--ui-focus);
}
.directory-section>a {
  display: block;
  margin: 10px 0 10px 10px;
  font-size: 12px;
  color: var(--text-muted);
  overflow-wrap: anywhere;
}
.workspace-main {
  min-width: 0;
}
.workspace-toolbar {
  display: grid;
  gap: 16px;
  margin-bottom: 24px;
}
.workspace-toolbar>label {
  display: grid;
  gap: 6px;
  font-size: 12px;
  max-width: 480px;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}
.import-control {
  position: relative;
  display: inline-flex;
  align-items: center;
  border: 1px solid var(--ui-control-border);
  border-radius: 10px;
  padding: 9px 12px;
  font-size: 12px;
  overflow: hidden;
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
}
.unit-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit,minmax(min(100%,max(230px,calc((100% - (var(--preferred-columns) - 1)*16px)/var(--preferred-columns)))),1fr));
  gap: 16px;
}
.unit-card h2>button {
  color: var(--text);
  background: none;
  border: 0;
  text-align: left;
  cursor: pointer;
  overflow-wrap: anywhere;
  font: inherit;
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
.selection {
  margin-top: 20px;
  padding: 24px;
}
.selection>button {
  margin-right: 10px;
}
.selection p {
  overflow-wrap: anywhere;
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
  padding: 32px 24px 64px;
  overflow-wrap: anywhere;
}
.reader-actions {
  margin: 20px 0;
}
.dependencies {
  margin-top: 40px;
  border-top: 1px solid var(--notes-border);
  padding-top: 20px;
}
.dependencies>div {
  margin: 14px 0;
  font-size: 13px;
}
.dependencies a {
  display: inline-block;
  color: var(--ui-focus);
  margin: 6px 12px;
}
.reader-document nav {
  font-size: 12px;
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
    padding: 24px 18px 48px;
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
