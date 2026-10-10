# 16 · Notes 学习模块视觉重构与体验优化方案

日期：2026-10-08 起。作用域：**学习笔记模块（`/notes`、`/notes/:topicId`、`/notes/:topicId/units/:unitId`）**。
前序功能基线：[13_Notes学习模块功能与视觉开发方案.md](13_Notes学习模块功能与视觉开发方案.md)。
执行总账：根目录 [todolist.txt](../todolist.txt) 为全局执行唯一入口，本文档顶部的 Todo 为本模块微观进度看板。

> **关于编号 16**：因 `docs/15` 已分配给已交付的 [15_开发启动脚本方案.md](15_开发启动脚本方案.md)，为严格遵守文档编号唯一性与历史引用安全，本轮新需求启用编号 16。

---

## ⏭ 现在应该从哪里继续

**当前处于【第 2 阶段：总览页视觉与交互已完成微调收尾，准备进入 T4 主题工作区】**。
已针对用户实测反馈完成全套细节升级：
1. **搜索图标归位**：修复 `.search-box-wrapper` 样式类名错位，使搜索图标精准嵌套并垂直居中在搜索框左侧留白处；
2. **星轨粒子交互升级**：在 [StarfieldBackground.vue](file:///c:/Users/afrangry/PycharmProjects/KnowdegeMap/frontend/src/components/StarfieldBackground.vue) 中封装了与主页 Hero 一致的光标引力聚拢（Mouse Attraction）与光标连线（Connect to Mouse），成为全站即插即用的可拆卸交互背景组件；
3. **卡片全域点击优化**：修复原先卡片仅标题文字和按钮可点击的缺陷，将整个卡片升级为整体可点击区域（`cursor: pointer` + 键盘回车无障碍）；
4. **卡片光标聚光灯光圈（Spotlight）**：将主页核心项目卡片的跟随光圈算法对齐至 Notes 主题卡片，卡片随光标位置投射出青紫流动光圈（`radial-gradient` 伪元素）。
前端类型检查 `vue-tsc` 与生产构建 `npm run build` 均已通过。

**下一步**：全面开展 **T4（主题工作区 `/notes/:topicId` 与阅读器联动微调）**，重构目录树面板、学习路线 DAG 图谱（NotesGraph）及阅读器弹窗（NotesDialog / NotesProse）的暗黑玻璃拟态质感，随后推进 **T5（自动化回归验证）**。

---

## 📋 本文档 Todo 清单（随时维护与更新）

- [x] **T0. 设计磨合与决策敲定**（2026-10-08 已确认）
  - [x] T0.1 页面现状底层代码深度探查（边距、组件、背景、堆叠）
  - [x] T0.2 确定全局顶栏（Nav Header）统一方案与路由面包屑关系（采用方案 1-A：统一全站导航顶栏）
  - [x] T0.3 确定版心最大宽度与流式响应式边界（采用方案 2-A：全屏自适应流式版心）
  - [x] T0.4 确定背景视觉基调（采用方案 3-A：深空暗夜底色 + 层次柔和光晕）
  - [x] T0.5 确定卡片与控件设计语言（采用玻璃拟态 + 光泽悬浮动效）
- [x] **T1. 基础布局与版心对齐重构**（已落地）
  - [x] T1.1 创建全站共享顶栏 [AppNavbar.vue](file:///c:/Users/afrangry/PycharmProjects/KnowdegeMap/frontend/src/components/AppNavbar.vue)，在 Notes 挂载并设置 `active="notes"`
  - [x] T1.2 重构 `.notes-content` 版心边距为 `clamp(2rem, 3.5vw, 3.5rem) clamp(1.5rem, 4vw, 4.5rem) 5rem`，最大宽放宽至 `min(1560px, 94vw)`
  - [x] T1.3 页面面包屑退居二级导航，标题与顶部节奏舒展
- [x] **T2. 背景视觉与品质感升级**（已落地）
  - [x] T2.1 背景层移除独立冷蓝偏色渐变，挂载 [KnowledgeMapBackground.vue](file:///c:/Users/afrangry/PycharmProjects/KnowdegeMap/frontend/src/components/KnowledgeMapBackground.vue)
  - [x] T2.2 将 [StarfieldBackground.vue](file:///c:/Users/afrangry/PycharmProjects/KnowdegeMap/frontend/src/components/StarfieldBackground.vue) 升级为全站通用交互背景，实现光标引力聚拢与动态星座连线
  - [x] T2.3 `<AmbientGlow />` 光晕色调收敛为紫蓝冷光（`rgb(124 58 237 / 0.16)`），消除生硬暗灰
  - [x] T2.4 验证多图层堆叠无死图层
- [x] **T3. 学习总览与主题卡片质感重构**（已落地并经反馈微调）
  - [x] T3.1 主题卡片升级为毛玻璃拟态（`backdrop-filter: blur(16px)` + 微光边框 + 悬停微抬浮动）
  - [x] T3.2 卡片添加精致的青色等宽数字角标（`01`、`02` 等），进入按钮增加悬停箭头位移
  - [x] T3.3 卡片整卡支持点击与键盘导航，消除边缘不可点击的死区
  - [x] T3.4 搜索框修复图标位置错位，输入框具有毛玻璃圆角、搜索图标与呼吸光圈
  - [x] T3.5 主题卡片对齐主页核心项目卡片的光标聚光灯（Spotlight）随动光圈效果
- [ ] **T4. 主题工作区与阅读器联动微调**（进行中）
  - [ ] T4.1 工作区目录侧边栏与工具栏暗黑玻璃拟态适配
  - [ ] T4.2 学习路线图谱（NotesGraph）SVG 与卡片节点视觉细节适配
  - [ ] T4.3 阅读器弹窗（NotesDialog）与 Prose 正文排版细节适配
- [ ] **T5. 全流程回归与自动化验证**（待开展）
  - [ ] T5.1 编写/更新专用前端浏览器回归用例（Playwright 拦截）
  - [ ] T5.2 验证各断点（1920/1440/1024/768/390）视觉与交互
  - [ ] T5.3 检查代码规范、构建与文档双向引用

---

## 1. 背景与现状深度探查

在进行设计方案前，对 `http://localhost:3000/notes` 进行了全方位的源码审计：

### 1.1 边距与版心断层（与主页完全脱节）
* **主页（[Dashboard.vue](file:///c:/Users/afrangry/PycharmProjects/KnowdegeMap/frontend/src/views/Dashboard.vue)）**：
  * 采用**全屏流式响应设计（Fluid Grid）**，未将内容锁死在固定像素宽度内。
  * 左右留白随视口宽度弹性伸缩（如 `.hero-panel` 边距 `clamp(2.4rem, 5vw, 5.4rem)`，卡片区 `clamp(1.25rem, 5vw, 5rem)`）。
* **Notes 页面（[Notes.vue](file:///c:/Users/afrangry/PycharmProjects/KnowdegeMap/frontend/src/views/Notes.vue)）**：
  * [theme.css](file:///c:/Users/afrangry/PycharmProjects/KnowdegeMap/frontend/src/features/notes/styles/theme.css) 中将 `--notes-page-width` **硬编码为 1280px**。
  * 外层容器 `.notes-content` 采用 `margin: 0 auto; padding: 40px 28px 80px;`。
  * **后果**：在常见的宽屏（1440px / 1920px）全屏视口下，主体内容被拘束在中央 1280px 狭长框中，两侧露出大量无意义黑边，显得单薄且空旷。

### 1.2 组件与样式复用度为零
* 主页拥有一套完整的暗黑玻璃拟态卡片（`.widget-card`、`.project-card-v2`）、按钮（`.primary-button`、`.btn-tactile`）和搜索框。
* Notes 页面通过 [components/ui/](file:///c:/Users/afrangry/PycharmProjects/KnowdegeMap/frontend/src/components/ui/) 引入了抽象的 `UiButton`、`UiSurface`、`AmbientGlow` 等原子组件，**但主页自身完全没有接入这套组件**。
* 结果导致 Notes 页面的卡片像纯色扁平色块（`--notes-surface-raised: #192232`），缺少主页卡片的光晕投影、细微渐变和触感动效。

### 1.3 存在孤立的独有背景与色系
* **底色偏色**：全站基准底色为 `#0f0f14`（深紫黑夜色），而 [Notes.vue#L411](file:///c:/Users/afrangry/PycharmProjects/KnowdegeMap/frontend/src/views/Notes.vue#L411) 自定义了垂直线性渐变 `linear-gradient(180deg, #0c111a, #101722)`，偏向冷青蓝色调。
* **孤立的强调色**：Notes 模块定义了 `--notes-accent: #8d94ff`（长春花蓝），脱离了主站核心的高饱和主紫 `--color-primary: #7c3aed` 与副青 `--color-accent: #06b6d4`。
* **背景氛围**：主页有深空微光与星空连线粒子，而 Notes 仅有一个静态微弱的左上角 `<AmbientGlow />`，背景略显沉闷。

### 1.4 图层堆叠与 Overdraw 分析
* **渲染层级**：
  1. 底层：`index.html` 的 `<body class="bg-[#0f0f14]">`；
  2. 页面层：`.notes-page` 的 `linear-gradient(180deg, #0c111a, #101722)`（100% 不透明，完全遮盖 body 底色）；
  3. 装饰层：`<AmbientGlow />`（绝对定位半透明光斑）；
  4. 实体卡片层：`.topic-card`（`UiSurface` 实体背景）。
* **结论**：当前没有发生像早期版本那样“底下挂着 Canvas 粒子画布却被上面不透明层遮挡”的死图层浪费，但当前 Notes 内部的背景层缺乏深度感与层次感。

---

## 2. 需求与核心目标

1. **统一全站视觉基因**：
   * 让 Notes 页面融入 KnowledgeMap 门户的统一设计语言，不再有“孤岛测试页面”的感觉。
   * 补齐全局顶部导航（保持主站 Brand Mark 与跨页面跳转通道）。
2. **重塑开阔的版心体系**：
   * 移除 `1280px` 硬顶板，改为主页一致的响应式弹性伸缩或自适应最大宽度（如 1600px+ 动态 clamp）。
   * 优化页面大标题与搜索栏的排布节奏。
3. **质感升维（卡片与背景）**：
   * 吸收主站的深邃深空背景与精致光晕层；
   * 主题卡片引入轻度玻璃拟态、渐变边框描边、精致悬浮状态，提升信息可读性与高级感。
4. **保持功能与契约完好**：
   * 维持 [docs/13](13_Notes学习模块功能与视觉开发方案.md) 已交付的所有功能（主题总览、工作区、DAG 依赖、深链接、单元阅读与编辑）不受任何破坏。

---

## 3. 设计方案探讨（第 1 轮方案磨合）

> 依据协作约定，本节记录：用户基础诉求 + 补充设计建议 + 提问与推荐。

### 3.1 顶栏（Nav Header）设计
* **现状问题**：Notes 顶部仅有 `KnowledgeMap / 学习笔记` 面包屑文本，点击不能方便切回主页仪表盘、记账等模块。
* **补充设计方向**：
  * **选项 A（推荐：全站统一顶栏组件化）**：将主页的 `dashboard-nav` 提炼为通用或同构的顶部导航栏，展示统一的 `K` 字 Logo、KnowledgeMap 标题，以及直达「主页仪表盘」「记账」「学习笔记」「储物间」的全局导航，当前处于“知识图谱/学习笔记”激活态。左下方保留或融入当前主题的小面包屑。
  * **选项 B（紧凑型子页面导航）**：类似 `Bills.vue` 的顶栏，左侧一个“← Dashboard”返回按钮 + “学习笔记”大字，右侧放置“新建主题”等核心按钮。
* **推荐**：**选项 A**。作为中枢门户，Notes 是核心子系统，统一的顶栏能极大提升系统完整度。

### 3.2 版心宽度与边距（Layout & Padding）
* **现状问题**：1280px 锁死，大屏两侧极宽黑边，顶部 40px 偏挤。
* **补充设计方向**：
  * **选项 A（推荐：动态流式宽屏版心）**：
    * 将 `--notes-page-width` 扩展为自适应流式，最大宽度放宽到 `1600px`（或随屏幕 `clamp(1200px, 90vw, 1680px)`）；
    * 边距改为 `padding: clamp(2rem, 3.5vw, 3.5rem) clamp(1.5rem, 4vw, 4rem)`；
    * 卡片网格（`.topic-grid`）从目前大屏固定的 3 列，在超宽屏下自然自适应为优雅的 3~4 列。
  * **选项 B（固定居中适度放宽）**：仅将 `1280px` 调整为 `1440px`。
* **推荐**：**选项 A**。流式布局在大显示器和笔记本上都能呈现最佳视觉平衡。

### 3.3 背景视觉（Background & Atmosphere）
* **现状问题**：静态冷蓝双色渐变，略显呆板单调。
* **补充设计方向**：
  * **选项 A（推荐：复用全站深空渐变 + 局部专属星芒/光斑）**：
    * 移除偏色的 `#0c111a` 渐变，接入 [KnowledgeMapBackground.vue](file:///c:/Users/afrangry/PycharmProjects/KnowdegeMap/frontend/src/components/KnowledgeMapBackground.vue) 的深邃紫蓝暗夜底图（或同款渐变色调）；
    * 保留并优化 `<AmbientGlow />`，使其光晕色与主站的 Purple/Cyan 体系更贴合，甚至可以加入 subtle 的点状网格或连接光点，体现“知识连接”的氛围。
  * **选项 B（引入与主页完全一致的 Canvas 粒子连线背景）**：
    * 完整挂载主页的连线星座背景。
* **推荐**：**选项 A**。学习笔记是高频沉浸式阅读与整理空间，背景既需要与主站融合，又不宜有过多频繁运动的粒子分散注意力，深邃渐变 + 层次光晕是最佳搭配。

### 3.4 主题卡片（Topic Cards）质感
* **现状问题**：卡片为单调的深暗蓝灰底色（`#192232`），文字对比度稍硬，hover 状态较平淡。
* **补充设计方向**：
  * **卡片底色**：改为微透的半透明深空质感 `rgba(15, 23, 42, 0.65)` + `backdrop-filter: blur(12px)`；
  * **边框质感**：细微半透明边缘描边 `border: 1px solid rgba(148, 163, 184, 0.16)`，悬停时边框渐变发光（如紫色/青色柔光）；
  * **角标与数据**：
    * 左上角的序号（01, 02...）采用发光的等宽字体或高亮药丸角标；
    * 底部的“X 个目录 · Y 个单元”使用更精致的图标/徽章指示；
    * 右下角的“进入主题 →”悬停时平滑位移。

---

## 4. 实施阶段与测试规划（双向引用）

* **涉及修改的文件**：
  * [frontend/src/views/Notes.vue](file:///c:/Users/afrangry/PycharmProjects/KnowdegeMap/frontend/src/views/Notes.vue)（视图整合）
  * [frontend/src/features/notes/styles/theme.css](file:///c:/Users/afrangry/PycharmProjects/KnowdegeMap/frontend/src/features/notes/styles/theme.css)（模块令牌与覆盖）
  * [frontend/src/components/ui/UiSurface.vue](file:///c:/Users/afrangry/PycharmProjects/KnowdegeMap/frontend/src/components/ui/UiSurface.vue)（表面组件质感强化）
* **测试与验证入口**：
  * 浏览器自动化回归：[frontend/tests/notes-browser.cjs](file:///c:/Users/afrangry/PycharmProjects/KnowdegeMap/frontend/tests/notes-browser.cjs)、[frontend/tests/notes-layout.cjs](file:///c:/Users/afrangry/PycharmProjects/KnowdegeMap/frontend/tests/notes-layout.cjs)
  * 后端 API/契约回归：[backend/tests/notes_cases.py](file:///c:/Users/afrangry/PycharmProjects/KnowdegeMap/backend/tests/notes_cases.py)
* **代码内双向引用约定**：
  * 修改涉及的 CSS/Vue 文件和测试脚本头部必须标明：`/* 对应文档：docs/16_Notes学习模块视觉重构与体验优化方案.md */`。

---

## 5. T4 主题工作区与学习路线图谱重构探讨（方案磨合阶段）

基于用户反馈与 `frontend_example` 原型对比分析，梳理 `/notes/:topicId` 的现状痛点与重构规划：

### 5.1 现状核心痛点剖析
1. **工作区被固定边栏挤压（视野严重不足）**：
   * 原代码固定分配 `240px` 给目录列表（`aside.directory`），右侧主视图被压迫在剩余空间；
   * 在常见 1080p/笔记本视口下，学习路线图谱被横向裁断，只能反复拖动底部难看的原生滚动条。
2. **工具栏占据高位且布局凌乱**：
   * 搜索框单占一整行，视图切换、新建、导入等操作散落在第二行；
   * 侵占了主工作区宝贵的纵向高度（垂直推挤约 120px）。
3. **学习路线（view=graph）视觉粗糙且死板**：
   * **机械网格坐标**：使用 `120 + i*240` 和 `110 + j*90` 的简单行列矩阵，未考虑 DAG 依赖长短链，缺少层级视觉张力；
   * **节点外形笨拙**：单一的 184×68 灰暗大框，无发光边框与动态反馈；
   * **连线凌乱**：生硬的灰色贝塞尔线，跨列和同列反向连接互相重叠遮挡；
   * **交互缺失**：无画布拖拽平移（Pan）、无滚轮缩放（Zoom），点选单元后底部弹出割裂生硬的大面板。

### 5.2 对照原型（frontend_example）的启示与取舍
* **原型优势**：
  * 采用分层带状背景（`layer-bands`），阶段感清晰；
  * 节点采用带有序号角标和状态指示的精致胶囊/发光圆点；
  * 悬浮/选中时支持**双向关系链高亮**（前置绿色/青色、后置紫色、无关节点变暗褪色）；
  * 右侧具备悬浮式检查器面板（Inspector），展示前置/后置数量与摘要。
* **现行系统特有业务需保留**：
  * 支持用户自由创建目录、新增单元、编辑/删除前后置依赖（动态增删改，非原型静态 JSON）；
  * 必须同时支持「目录视图（网格）」与「学习路线（图谱）」双视图平滑切换。

### 5.3 四大重构维度（产品经理建议）
1. **侧边栏折叠机制（Collapsible Sidebar）**：
   * 默认展开 260px，一键可平滑收起到 0，完全释放 100% 版心给图谱和单元网格；
   * 本地记忆收起状态，折叠后工具栏左侧保留展开入口。
2. **工具栏单行流式整合（Top-Right Action Bar）**：
   * **左侧**：[侧边栏开关] + [紧凑搜索输入框（胶囊毛玻璃）]；
   * **右侧**：[视图切换 Segmented 胶囊: ⊞ 目录视图 | ☊ 学习路线] + [＋ 新建单元 CTA] + [⤓ 导入 Markdown]；
   * 高度压缩到单行 46px，彻底释放上方视野。
3. **图谱沉浸体验升级（NotesGraph 蜕变）**：
   * **节点**：升级为带青色等宽序号、状态点、微光边框的发光科技胶囊节点；
   * **连线**：S 形平滑渐变流光连线（青色到紫色），选中时箭头和光轨高亮流动；
   * **双向链聚焦**：选中节点时，前置依赖亮青、后置依赖亮紫、无关节点优雅淡化；
   * **视口画布增强**：支持画布鼠标拖拽平移（Pan）、滚轮缩放（Zoom: 0.5x~2.0x）及右上角控制小部件（`+` / `-` / `重置`）；
   * **悬浮检查器（Float Inspector）**：选中节点后在右侧滑出悬浮毛玻璃面板，展示依赖关系链并直达阅读器。
4. **视觉质感一体化**：
   * 继承全站深空暗夜星轨动态粒子，消除纯黑死板背景。

### 5.4 第一批实现记录与验证证据（2026-10-08）

1. **落地代码清单**：
   * [frontend/src/views/Notes.vue](file:///c:/Users/afrangry/PycharmProjects/KnowdegeMap/frontend/src/views/Notes.vue)：
     - 新增 `isDirectoryCollapsed` 响应式状态与 `localStorage` 本地偏好记忆；
     - 整合单行紧凑工具栏 `.workspace-toolbar`（左侧侧边栏折叠按钮 + 搜索框；右侧视图切换胶囊 + 新建单元 + 导入 Markdown）；
     - 实现侧边栏平滑折叠（`260px` 到 `0px`，`opacity` 与 `visibility` 联动过渡），完全让渡版心宽度；
     - 优化选中有序检查器 `.graph-float-inspector` 为浮动毛玻璃卡片（双向依赖标签、打开笔记 CTA）。
   * [frontend/src/features/notes/components/NotesGraph.vue](file:///c:/Users/afrangry/PycharmProjects/KnowdegeMap/frontend/src/features/notes/components/NotesGraph.vue)：
     - 实现 **Pan & Zoom 交互视口**：鼠标拖拽平移、滚轮 0.6x~2.0x 无级缩放，右上角快捷控制按钮组（放大/缩小/复位）；
     - 阶段背景分层带（`.layer-bands`）；
     - 科技发光胶囊节点（高 44px 紧凑圆角胶囊、等宽青色序号角标、微光描边，严格满足 `< 90px` 布局约束）；
     - **双向高亮与焦点聚焦**：选中节点时，前置依赖高亮青色（Cyan `#06b6d4`）、后置依赖高亮紫色（Violet `#c084fc`）、非关联节点柔和褪色至 `0.22`；
     - **S 曲线流光连接线**：平滑三次贝塞尔曲线、双向光晕滤镜与专用箭头 Marker。

2. **验证与构建证据**：
   * **前端构建与类型检查**：`npm run build`（`vue-tsc && vite build`）通过，Exit Code 0，无任何 TypeScript 报错与打包告警。
   * **后端测试套件回归**：`conda run -n desheng python backend/tests/notes_cases.py` 通过，全部 28 个用例（包括原子事务、DAG 循环拒绝、单边集合一致性等）100% PASS。

### 5.5 顶部右侧 5 按钮直列控制面板（Vertical Action Rail）落地

根据用户体验反馈与交互意图对齐，对工作区控制体系进行了更纯粹的层级收口：

1. **顶部 Header 右侧竖排列控制面板（Vertical Action Rail）**：
   * 将散落在下方工具栏的全局/主题级操作全部收拢到顶部 Header 右侧等宽（180px）纵向控制列中，自上而下包含 5 项：
     1. **主题下拉选择框**（`select.topic-switch`：切换 Transformer / CNN / 数据库等）；
     2. **主题设置**（`[主题设置]` 按钮，调整主题名称、描述及偏好列数）；
     3. **新建单元**（`[+ 新建单元]` 高亮渐变紫 CTA 按钮）；
     4. **导入 Markdown**（`[导入 Markdown]` 文件上传组件）；
     5. **视图切换胶囊**（`[⊞ 目录视图 | ☊ 学习路线]` 等分无缝切换 Segmented 控制器）。
   * 视觉对齐：左侧大标题、英文眉题与长描述高度（~160px）与右侧 5 按钮等高平衡，解决原设计右侧空旷、下方拥挤失衡的问题。

2. **工作区工具栏彻底净化为纯粹过滤栏（Filter Bar）**：
   * 下方 `.workspace-toolbar` 移除全部右侧操作，仅保留左侧 **`[◨ 收起/展开目录]`** 与宽幅 **`[搜索单元标题、标签或正文...]`**；
   * 释放主画布与目录区域的垂直空间，使视口聚焦于内容过滤与知识图谱浏览。

3. **构建与验证**：
   * `npm run build`（`vue-tsc && vite build`）：Exit Code 0（`✓ built in 1.51s`），零报错；
   * 后端隔离用例 `notes_cases.py` 28 checks 100% PASS。

### 5.6 图谱连线算法与端口锚点专项修复（Edges & Ports Fix）

针对用户截图反馈中“同列钩子回弯怪异”、“跨列斜穿走线生硬”、“连线进入角度歪斜”等连线几何与算法问题，进行了系统性重构：

1. **同列垂直上下连线直连化（Vertical Colinear Straight Edges）**：
   * **相邻行直接垂直相连**：若 `a.colIdx === b.colIdx && Math.abs(b.rowIdx - a.rowIdx) === 1`，连接路径彻底重构为 `M a.x, a.y+22 L b.x, b.y-22`，从上方节点底缘中央笔直连向下节点顶缘中央；
   * 彻底根除原代码向右突增 60px 绕圈形成的畸形“鱼钩”弯弧；
   * 针对同列跨多行（阻隔节点）：改走右侧平滑外绕通道（右侧端口出发平滑 C 弯绕过中间节点）。

2. **跨列水平平滑 S 曲线（Monotonic Smooth S-Curve）**：
   * 起点从左节点右端极值点 `(a.x + 95, a.y)` 水平射出；
   * 终点进入右节点左端极值点 `(b.x - 95, b.y)` 水平接入；
   * 控制点张力自适应为 `tension = Math.min(90, Math.max(26, dx * 0.45))`，严格杜绝控制点重叠交叉，保证 X 轴严格单调递增，形成自然物理丝滑的 S 曲线；
   * 跨多列（如第 1 阶段到第 3 阶段）长连接保持大弧度平缓滑行，避免斜切中间层卡片。

3. **SVG 箭头 Marker 精准化与微空间吸附**：
   * `<marker>` 引入 `markerUnits="userSpaceOnUse"`，使箭头大小固定为 9px×7px 精致锐利尺寸，不随 `stroke-width` 膨胀失真；
   * 利用 SVG `orient="auto"` 机制，垂直连线箭头 100% 笔直向下，水平连线箭头 100% 水平向右，完美贴合胶囊外边缘；
   * DOM 排序优化：激活的高亮线（前置青 / 后置紫）在 SVG 中自动排在未激活暗线后方，永远置顶渲染，不被灰色暗线遮挡。

4. **节点焦点环与高亮层级强化**：
   * **选中节点**：由原先单一紫色升级为白银描边 + 紫外青双层流光光环（`selected`），区分度极高；
   * **前置依赖**：亮电光青色（`#06b6d4`）；
   * **后置依赖**：薰衣草紫色（`#c084fc`）；
   * **未关联节点与连线**：优雅暗化至 `0.18` 透明度。

5. **右侧面板「+ 新建单元」视觉统一化**：
   * 将「+ 新建单元」按钮由原本跳跃的亮紫背景改为与「主题设置」、「导入 Markdown」完全一致的深空暗夜毛玻璃质感（`.rail-btn`）；
   * 全面保证控制列仅保留「目录视图 / 学习路线」当前被选中的一项为紫色高亮，界面秩序更加高级沉稳。

6. **构建与验证**：
   * `npm run build`（`vue-tsc && vite build`）：`✓ built in 2.02s`，Exit Code 0，类型检查与资源打包全部通过；
   * `conda run -n desheng python backend/tests/notes_cases.py`：全部 28 个用例 100% PASS。

### 5.7 根除连线纵向偏移失真（SVG ViewBox 纵向居中陷阱修复）

1. **根因定位（58px 幽灵下沉偏移）**：
   * 观察用户第二次截图发现：同列垂直箭头本应在 01 与 02 之间，却下沉出现在 02 与 03 之间甚至 03 底边空旷处；跨列线本应在卡片右侧正中，却下沉 58px 从卡片底部向下兜底呈 U 形。
   * **代码病根**：
     - `height` 动态计算为 `364px`，而 `.graph` 的 CSS 样式曾残留 `min-height: 480px`；
     - SVG `<svg>` 尺寸被拉大为 480px，但 `viewBox="0 0 1040 364"`；
     - SVG 规范默认 `preserveAspectRatio="xMidYMid meet"`，浏览器自动将 364px 的内容在 480px 的容器中**垂直居中**：$(480 - 364) / 2 = 58\text{px}$！
     - 导致整张 SVG 的所有线条相对于定位在 CSS 像素 `top` 的卡片按钮**整体向下平移了整整 58px**！

2. **系统性修复**：
   * **彻底清除 CSS 冲突**：移除 `.graph` 上的 `min-height: 480px`，使其尺寸严格受 `:style="{ height: `${height}px` }"` 控制；
   * **视口底限统一**：将 `height` 的计算下限基准统一提高至 `480px`，使画布始终具备充裕操作高；
   * **解除纵向对齐扭曲**：在 `<svg>` 显式添加 `preserveAspectRatio="none"`，确保 SVG 坐标系点位 $(x, y)$ 与 HTML 卡片绝对定位 $(left, top)$ 形成 1:1 绝对像素对齐。

3. **构建与测试验证**：
   * `npm run build`（`vue-tsc && vite build`）：`✓ built in 1.87s`，Exit Code 0；
   * `conda run -n desheng python backend/tests/notes_cases.py`：28 checks 100% PASS。

### 5.8 桌面高保真工作区第一阶段落地（首屏压缩、内联切换、停靠详情栏与可读性增强）

根据产品经理评审意见与高保真设计概念图，完成主题工作区第一阶段核心改造：

1. **首屏空间大幅释放（工作区画布由 ~565px 提升至 ~185px 开始）**：
   * **Header 扁平化压缩**：原右侧纵向堆叠 5 个按钮导致的 210px+ 垂直大空白彻底清除；
   * **内联主题切换**：大标题区升级为内联下拉触发器（`h1` + 青色微光 `⌵` + 覆盖式透明 `<select aria-label="切换主题">`），点击标题即可无缝切换主题；
   * **紧凑副标题**：单行文本展示主题描述，超出优雅截断；
   * **主次操作水平排布**：右侧仅保留单行 38px 操作（`+ 新建单元` 极光紫高亮 CTA，配合毛玻璃次级操作 `[主题设置]` 与 `[导入 Markdown]`）。

2. **工作区工具栏与职责语义清晰化**：
   * **视图切换下移至工具栏**：将视图控制器并入工作区工具栏，紧邻目录展开收起按钮与搜索框，重构为精致的双段式 Segmented 胶囊；
   * **语义名称重塑**：原「目录视图」更名为「单元」（保留 `aria-label="目录视图"`），原「学习路线」更名为「依赖图」（保留 `aria-label="学习路线"`），语义与认知更精准，且对既有自动化测试脚本 100% 保持无缝兼容。

3. **节点可读性与无截断展示（NotesGraph）**：
   * **紧凑圆角矩形**：节点由 190px 窄胶囊升级为 208px×48px 紧凑圆角矩形（`border-radius: 12px`）；
   * **两行完整排版**：概念标题由单行强制省略改为最多两行折行（`-webkit-line-clamp: 2`），彻底解决“Token Embedding”、“残差连接与层归一化”等长名称被裁断截断的问题；
   * **连接端口重新校准**：端口半宽由 95px 调整为 104px、半高由 22px 调整为 24px，笔直垂直连线与横向 S 曲线依然保持零缝隙精准吸附；
   * **画布视口自适应（Fit Canvas）**：新增 `fitCanvas` 算法与控制按钮 `[⤢ 适应画布]`，能根据容器真实宽度动态计算缩放比例并居中，确保 4~6 列知识图谱首次加载或视口收窄时全局一览无余。

4. **底部停靠详情栏（Docked Bottom Inspector）**：
   * 移除原本被推挤到画布外部的生硬大卡片，改为工作区底部吸附的毛玻璃操作条（`docked-bottom-inspector`）；
   * **左侧**：展示序号徽章、概念全称、章节标签与正文摘要；
   * **中间**：分类展示前置与后续依赖胶囊 Chip，点击任一 Chip 即可即时切换聚焦至对应节点；
   * **右侧**：固定展示「📖 阅读笔记」主操作按钮与「✕」清除选择按钮；
   * **侧边栏联动**：左侧目录树对当前选中的单元实时高亮紫色焦点背景（`.is-active-unit`），强化“目录”与“图谱”的一致性心智。

5. **构建与验证**：
   * `npm run build`（`vue-tsc && vite build`）：`✓ built in 3.91s`，Exit Code 0，类型检查与打包通过；
   * `conda run -n desheng python backend/tests/notes_cases.py`：全部 28 个契约/事务用例 100% PASS。

### 5.9 桌面与移动端高保真工作区第二阶段落地（单元卡片降噪净化、阅读器顶层强化与窄屏响应式打磨）

根据产品经理评审规划，完成第二阶段体验与信息降噪重构：

1. **单元卡片信息纯化与降噪（目录/单元视图）**：
   - **智能提取高质量摘要（`getUnitSummary`）**：精准滤除 Markdown 各级标题、YAML frontmatter、旧模版占位标记（如 `## 核心目标`、`## 学习检查`）及冗余的大标题行，提取最具辨识度的 1~2 行概念正文（字符截断约 95 字符），消除多张卡片因模板通用描述造成的千篇一律与生硬截断；
   - **剔除重复冗余标签**：移除卡片底部与顶部重复的所属章节标签（tag pills），顶部保留章节徽章与两位数序号（`01`, `02`...）；
   - **卡片底部关系聚焦**：底部精简为 `X 个前置 · Y 个后续` 关系计数与极光紫高亮 `阅读笔记 →` 交互入口；
   - **全卡光标聚光灯微光**：卡片支持光标移动位置追踪（`--mouse-x`, `--mouse-y`），悬浮时带有微光聚光灯与轻量上浮微动效。

2. **阅读弹窗顶层提权与沉浸式阅读体验（NotesDialog）**：
   - **标题与章节提至顶层（`reader-dialog-header`）**：弹窗 Header 直接呈现文章概念大标题（`h2.reader-article-title`）与章节面包屑，移除原本占位但无信息量的“知识单元阅读器”副容器名；
   - **正文即刻呈现**：移除了正文内部重复冗余的面包屑导航与重复操作栏，让用户点进笔记即可立刻进入文章阅读，无多余视觉噪音；
   - **依赖关系双列网格重构（`dependencies-grid`）**：将文末前置与后续依赖重构为青色（前置依赖）与紫色（后续单元）的双列对照卡片网格，支持直接点击跳转其他单元；
   - **测试契约与管理操作保全**：右上角保留 `[编辑]`、`[删除单元]`、`[✕ 关闭窗口]` 以及 `:data-unit-id` 等语义与自动化测试属性，删除操作降级为温和暗色边框。

3. **窄屏移动端体验打磨（≤800px / 390px 视口适配）**：
   - **窄屏默认收起目录**：当屏幕宽度 `< 800px` 且无显式保存偏好时，侧边栏目录默认折叠，将宝贵的屏幕空间直接让渡给单元列表或依赖图；
   - **阅读弹窗自适应单列流**：在 390px 窄屏视口下，阅读器头部元信息与操作按钮自适应为竖向紧凑流，依赖卡片由双列平滑切为单列堆叠；
   - **坚守全站横向零溢出契约**：确保 390px/320px 下 `document.documentElement.scrollWidth <= innerWidth`。

4. **构建与测试验证**：
   - `npm run build`（`vue-tsc && vite build`）：`✓ built in 3.70s`，Exit Code 0，类型检查与静态打包通过；
   - `conda run -n desheng python backend/tests/notes_cases.py`：全部 28 个契约/事务用例 100% PASS。

