<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

// ---- Types ----
interface Node {
  id: string
  label: string
  type: 'tag' | 'note'
  x: number
  y: number
  vx: number
  vy: number
  fx: number | null
  fy: number | null
  notesCount: number
  noteId?: string
  color: string
  idealAngle?: number
}

interface Link {
  source: string
  target: string
}

interface NoteItem {
  id: string
  title: string
  tags: string[]
  content: string
}

// ---- Themes ----
const isDark = ref(true)

function updateThemeClass() {
  if (isDark.value) {
    document.documentElement.classList.remove('theme-light')
  } else {
    document.documentElement.classList.add('theme-light')
  }
}

function toggleTheme() {
  isDark.value = !isDark.value
  localStorage.setItem('theme', isDark.value ? 'dark' : 'light')
  updateThemeClass()
}

// ---- Data & Mock Database ----
const allNotes = ref<Record<string, NoteItem>>({
  'vue-perf': {
    id: 'vue-perf',
    title: 'Vue 3 性能优化指南',
    tags: ['Vue 3'],
    content: `# Vue 3 性能优化指南\n\nVue 3 的响应式系统 and 编译器已经非常高效，但在复杂场景下，开发者仍需注意以下性能优化实践。\n\n## 1. 避免深层响应式：\`shallowRef\` 与 \`shallowReactive\`\n\nVue 3 默认会将对象深度包装为 Reactive 代理。若数据量极大（如大型表格、地图数据或图表配置），深度包装会带来显著性能开销。\n\n> [!TIP]\n> 对于仅用于展示的大型复杂对象，推荐使用 \`shallowRef\` 代替 \`ref\`。它只代理对象的 \`.value\` 引用本身，避免递归遍历其属性。\n\n\`\`\`typescript\n// 性能优化前\nconst bigData = ref({ ...lotsOfNestedObjects })\n\n// 性能优化后\nconst bigData = shallowRef({ ...lotsOfNestedObjects })\n\`\`\`\n\n## 2. 静态内容优化：\`v-once\` 与 \`v-memo\`\n\n* **\`v-once\`**：仅在组件首次挂载时渲染一次，后续其所在的 DOM 节点将被视为静态节点，跳过所有的 Diff 对比过程。适用于完全不随数据变化的说明性文本。\n* **\`v-memo\`**：显式依赖项缓存。只有当指定的依赖数组发生变化时，才会触发该节点树的重新渲染和 Diff。\n\n| 指令 | 作用 | 推荐场景 |\n| --- | --- | --- |\n| \`v-once\` | 性能优化 | 纯静态文本、版权声明 |\n| \`v-memo\` | 局部重绘 | 超过 1000 行的长列表、热点单元格更新 |\n\n## 3. 组件懒加载与异步加载\n\n使用 \`defineAsyncComponent\` 结合 Webpack/Vite 动态导入来实现组件按需加载：\n\n\`\`\`typescript\nimport { defineAsyncComponent } from 'vue'\n\nconst LazyModal = defineAsyncComponent(() => import('./components/LazyModal.vue'))\n\`\`\`\n\n> [!IMPORTANT]\n> 不要对高频交互的微小组件使用异步加载，这会引起不必要的闪烁和加载阻塞。建议对大型遮罩弹框、PDF 渲染器等重载组件实施异步化。`
  },
  'vite-opt': {
    id: 'vite-opt',
    title: 'Vite 构建打包体积优化',
    tags: ['Vue 3'],
    content: `# Vite 构建打包体积优化\n\nVite 默认的构建配置对于常规中台系统开箱即用，但在生产发布前，进行针对性的包体积控制是极其必要的。\n\n## 1. 拆包策略 (Code Splitting)\n\n利用 Rollup 的 \`manualChunks\` 对第三方模块进行合理分流：\n\n\`\`\`typescript\n// vite.config.ts\nexport default defineConfig({\n  build: {\n    rollupOptions: {\n      output: {\n        manualChunks: {\n          'vendor-vue': ['vue', 'vue-router'],\n          'vendor-ui': ['element-plus', 'lucide-vue-next']\n        }\n      }\n    }\n  }\n})\n\`\`\`\n\n## 2. 按需加载 (Tree Shaking)\n\n* 尽量使用具备 ES Module (ESM) 规范的库模块。\n* 导入工具函数时，不要整体引入，采用解构导入：\n\n\`\`\`javascript\n// ✗ 错误写法：会把整个 lodash 库打包进来\nimport lodash from 'lodash'\nlodash.cloneDeep(obj)\n\n// ✓ 正确写法：只会打包 cloneDeep 相关的部分代码\nimport { cloneDeep } from 'lodash-es'\ncloneDeep(obj)\n\`\`\`\n\n> [!CAUTION]\n> 注意区分 \`lodash\` 与 \`lodash-es\`。前者是 CommonJS 规范，后者是真正的 ESM 规范。使用 \`lodash\` 即使使用解构导入也会导致整包打包入库。`
  },
  'sql-opt': {
    id: 'sql-opt',
    title: 'MySQL / SQL 查询性能优化',
    tags: ['Database'],
    content: `# SQL 查询与性能优化\n\n本文总结了数据库慢查询优化中，最关键的 Explain 执行计划解读以及常规优化方案。\n\n## 1. 使用 \`EXPLAIN\` 分析慢查询\n\n在 SQL 前加上 \`EXPLAIN\` 关键字，执行后可以查看查询优化器的具体执行策略：\n\n\`\`\`sql\nEXPLAIN SELECT * FROM bills WHERE expense_date = '2026-06-25';\n\`\`\`\n\n在分析结果中，着重关注以下三个字段：\n1. **type**（连接类型）：代表查询效率的量级。从好到差依次为：\`system\` > \`const\` > \`eq_ref\` > \`ref\` > \`range\` > \`index\` > \`ALL\`。若出现 \`ALL\` 则意味着发生了全表扫描。\n2. **key**：实际使用的索引。若为 \`NULL\` 则没有利用索引。\n3. **Extra**：额外解析说明。若出现 \`Using filesort\` 或 \`Using temporary\`，说明效率极差，需要建立合适联合索引进行覆盖。\n\n## 2. 经典慢 SQL 场景\n\n### 场景 A：禁止在索引列上做运算\n\n\`\`\`sql\n-- ✗ 错误示例：索引失效，全表扫描\nSELECT * FROM bills WHERE YEAR(expense_date) = 2026;\n\n-- ✓ 优化示例：利用索引\nSELECT * FROM bills WHERE expense_date >= '2026-01-01' AND expense_date <= '2026-12-31';\n\`\`\`\n\n### 场景 B：最左匹配原则\n\n对于联合索引 \`(category_id, subcategory_id)\`，查询条件必须包含首列才能触发索引匹配：\n\n\`\`\`sql\n-- ✓ 走索引\nSELECT * FROM bills WHERE category_id = 5;\nSELECT * FROM bills WHERE category_id = 5 AND subcategory_id = 12;\n\n-- ✗ 不走索引\nSELECT * FROM bills WHERE subcategory_id = 12;\n\`\`\`\n\n> [!NOTE]\n> 定期使用 \`ANALYZE TABLE\` 更新索引统计信息，有助于优化器在复杂查询时做出更好的索引决策。`
  },
  'mysql-idx': {
    id: 'mysql-idx',
    title: 'MySQL 索引设计原则',
    tags: ['Database'],
    content: `# MySQL 索引设计最佳实践\n\n索引对于数据库的高效运行至关重要，但索引也需要占用额外的存储空间，并降低 \`INSERT\` / \`UPDATE\` 的性能。因此，索引设计应遵循“少而精”的原则。\n\n## 1. 哪些列需要建索引？\n\n* **Where 子句** 中高频使用的过滤字段。\n* **Order By / Group By** 中涉及的排序与分组列（可消除 Filesort 物理排序）。\n* **Join 关联列**（外键列）建议一定要建立索引，以加速联表查询。\n\n## 2. 联合索引的排序顺序\n\n联合索引 \`(a, b, c)\` 应该如何排定列的顺序？\n\n1. **高区分度列优先**：区分度越高的字段（即该字段不同值越多）越应该放在联合索引的左侧。\n2. **高频过滤字段优先**：如果在绝大多数查询中都需要过滤字段 \`a\`，那么 \`a\` 应作为首列。\n\n## 3. 覆盖索引 (Covering Index) 带来的极速提升\n\n如果一个索引包含了查询所需要的所有数据列，数据库就可以**直接从索引树中读取结果，而不需要回表**（即不需要根据主键再次去查行记录）。\n\n\`\`\`sql\n-- 创建联合索引\nCREATE INDEX idx_user_bills ON bills(user_id, amount);\n\n-- 查询只需要 user_id 和 amount\nSELECT user_id, amount FROM bills WHERE user_id = 45;\n-- 此时该查询即为覆盖索引查询，效率极高！\n\`\`\``
  },
  'cnn-arch': {
    id: 'cnn-arch',
    title: 'CNN 卷积神经网络架构',
    tags: ['机器学习'],
    content: `# CNN 卷积神经网络核心原理\n\n卷积神经网络（Convolutional Neural Network, CNN）是深度学习中处理网格化数据（如图像、音频频谱图）的标准算法。\n\n## 1. CNN 核心组件\n\n1. **卷积层 (Convolutional Layer)**：使用滑动窗口机制的卷积核（Filter）在输入特征图上滑动，捕捉局部空间特征。卷积操作具备**局部连接**和**权值共享**的特点，大幅减少了模型参数。\n2. **池化层 (Pooling Layer)**：对特征图进行下采样（如 Max Pooling、Average Pooling），减小空间尺度，提供平移不变性，降低计算资源开销。\n3. **全连接层 (Fully Connected Layer)**：将提取出的高维空间特征展平，通过传统线性映射加激活函数输出最终的分类类别或回归数值。\n\n## 2. CNN 的演进路线\n\n* **LeNet-5** (1998)：手写字体识别的经典开端。\n* **AlexNet** (2012)：引入 GPU 训练、ReLU 激活函数和 Dropout，分水岭之作。\n* **VGGNet** (2014)：提倡使用纯粹的小卷积核（3x3）叠深网络。\n* **ResNet** (2015)：核心引入**残差连接 (Skip Connection)**，成功解决了网络层数过深导致的梯度消失和网络退化问题。\n\n\[\nH(x) = F(x) + x\n\]\n\n其中 \(x\) 是层输入，\(F(x)\) 是残差映射，\(H(x)\) 是最终学习输出。`
  },
  'lin-reg': {
    id: 'lin-reg',
    title: '线性回归数学推导',
    tags: ['机器学习'],
    content: `# 线性回归模型精要\n\n线性回归是统计学与机器学习中最基础的回归分析模型，用于建立自变量 \`X\` 与因变量 \`y\` 之间的线性映射关系。\n\n## 1. 损失函数 (Loss Function)\n\n我们使用最小二乘均方误差（Mean Squared Error, MSE）作为线性回归的损失函数，来评估模型预测值与真实值之间的偏离程度：\n\n\[\nJ(\\theta) = \\frac{1}{2m} \\sum_{i=1}^{m} (h_\\theta(x^{(i)}) - y^{(i)})^2\n\]\n\n其中，\(m\) 为样本数，\(h_\\theta(x) = \\theta^T x\) 为假设函数，\(\\theta\) 为权重参数向量。\n\n## 2. 参数求解：梯度下降 (Gradient Descent)\n\n通过对损失函数计算权重向量的梯度偏导，我们使用梯度下降逐步迭代更新参数：\n\n\[\n\\theta_j := \\theta_j - \\alpha \\frac{\\partial}{\\partial \\theta_j} J(\\theta)\n\]\n\nLocking down gradient parameter convergence.\n\n## 3. 解析解求解：正规方程 (Normal Equation)\n\n通过矩阵微积分，直接求导令其为零，可以获得 \(\\theta\) 的全局闭式解析解：\n\n\[\n\\theta = (X^T X)^{-1} X^T y\n\]\n\n> [!CAUTION]\n> 特征数大于 10000 时应优先选用梯度下降法。`
  },
  'docker-dep': {
    id: 'docker-dep',
    title: 'Docker Compose 多容器部署',
    tags: ['DevOps'],
    content: `# Docker Compose 多容器环境部署\n\n使用 Docker Compose 进行服务编排能够确保开发、测试与生产环境的一致性。\n\n## 1. 标准 \`docker-compose.yml\` 编排结构\n\n以下是一个包含 FastAPI 后端、MySQL 数据库及 Nginx 反向代理的三容器经典编排：\n\n\`\`\`yaml\nversion: '3.8'\n\nservices:\n  db:\n    image: mysql:8.0\n    container_name: km-mysql\n    restart: always\n    environment:\n      MYSQL_DATABASE: knowledgemap\n      MYSQL_ROOT_PASSWORD: root\n    ports:\n      - "3306:3306"\n    volumes:\n      - mysql_data:/var/lib/mysql\n\n  backend:\n    build: ./backend\n    container_name: km-backend\n    restart: always\n    depends_on:\n      - db\n    environment:\n      - DATABASE_URL=mysql+pymysql://root:root@db:3306/knowledgemap?charset=utf8mb4\n    ports:\n      - "8000:8000"\n\n  frontend:\n    build: ./frontend\n    container_name: km-frontend\n    ports:\n      - "80:80"\n    depends_on:\n      - backend\n\nvolumes:\n  mysql_data:\n\`\`\`\n\n## 2. 常用部署指令\n\n* **后台启动所有服务**：\`docker compose up -d\`\n* **停止并删除容器与网络**：\`docker compose down\`\n* **重建镜像并启动**：\`docker compose up --build -d\`\n* **查看容器日志**：\`docker compose logs -f [service-name]\``
  },
  'starry-cafe': {
    id: 'starry-cafe',
    title: '《星光咖啡馆与死神之蝶》游戏心得',
    tags: ['个人杂谈'],
    content: `# 《星光咖啡馆与死神之蝶》攻略与体验杂谈\n\n《星光咖啡馆与死神之蝶》（喫茶ステラと死神の蝶）是 YUZUSOFT（柚子社）制作的一款恋爱冒险特征的视觉小说。\n\n## 1. 剧情设定与特色\n\n* **死神契约**：主角因为一次突发事故面临死亡，随后遇到了死神之蝶与死神女孩，通过在一家新建成的咖啡馆工作，来协助收集由于人类心愿破碎而逃逸的灵魂碎屑。\n* **轻度解密与欢快日常**：故事基调保持了柚子社一贯的轻松诙谐风格，穿插咖啡馆经营要素，并在角色路线上逐渐揭示每个少女背后的心结。\n* **精美原画**：こぶいち 和 むりりん 两位当家画师执笔，立绘精致，背景光照感极佳。\n\n## 2. 主线攻略路线顺序建议\n\n为了获得最佳剧情体验，推荐如下攻略次序：\n\n1. **墨染希 (Nozomi)**\n2. **御藤爱衣 (Ai)**\n3. **明月栞那 (Kanna)**\n4. **四季夏目 (Natsume)**（推荐作为压轴路线，故事解密最为详尽，夏目天下第一！）\n\n> [!NOTE]\n> 四季夏目（Natsume）线在揭开死神身世的宏大世界观设定上，有极其感人及深入的情节呈现，非常值得仔细体验。`
  }
})

// ---- Graph States ----
const nodes = ref<Node[]>([])
const links = ref<Link[]>([])

const expandedTags = ref<Set<string>>(new Set())
const selectedNodeId = ref<string | null>(null)
const hoveredNodeId = ref<string | null>(null)

// Search query
const searchQuery = ref('')

// Pan & Zoom
const panX = ref(0)
const panY = ref(0)
const zoom = ref(1.0)
const isPanning = ref(false)
let panStartX = 0
let panStartY = 0

// Dragging
const activeDragNode = ref<Node | null>(null)

// Graph configuration
const width = ref(800)
const height = ref(600)

// Physics loops
const isSimulating = ref(true)
let animationFrameId: number | null = null

// ---- Reader Drawer ----
const activeNoteId = ref<string | null>(null)
const isDrawerOpen = ref(false)
const isEditing = ref(false)
const editTitle = ref('')
const editContent = ref('')
const editTagsString = ref('')

// ---- Helper for Non-crossing Fan-out Angles ----
function getIdealAngle(hubId: string, index: number, totalCount: number = 3) {
  if (hubId === 'hub1') {
    const centerAngle = 5 * Math.PI / 6 // 150 degrees, pointing bottom-left away from center
    const spacing = 50 * Math.PI / 180
    return centerAngle + (index - 1) * spacing
  } else if (hubId === 'hub2') {
    const centerAngle = Math.PI / 6 // 30 degrees, pointing bottom-right away from center
    const spacing = 40 * Math.PI / 180
    return centerAngle + (index - 1.5) * spacing
  } else if (hubId === 'hub3') {
    const centerAngle = -Math.PI / 2 // -90 degrees, pointing straight up away from center
    const spacing = 35 * Math.PI / 180
    return centerAngle + (index - 2) * spacing
  } else {
    // Fallback for custom nodes
    return index * (2 * Math.PI / totalCount) - Math.PI / 2
  }
}

// ---- Initialize Default Graph ----
function initGraph() {
  const parentX = 400
  const parentY = 300
  const radius = 110

  // 3 hubs positioned in a stable triangle
  const h1x = parentX - radius * Math.cos(Math.PI / 6)
  const h1y = parentY + radius * Math.sin(Math.PI / 6)
  const h2x = parentX + radius * Math.cos(Math.PI / 6)
  const h2y = parentY + radius * Math.sin(Math.PI / 6)
  const h3x = parentX
  const h3y = parentY - radius

  nodes.value = [
    { id: 'hub1', label: '中枢 1', type: 'tag', x: h1x, y: h1y, vx: 0, vy: 0, fx: null, fy: null, notesCount: 3, color: 'var(--color-primary)' },
    { id: 'hub2', label: '中枢 2', type: 'tag', x: h2x, y: h2y, vx: 0, vy: 0, fx: null, fy: null, notesCount: 4, color: 'var(--color-accent)' },
    { id: 'hub3', label: '中枢 3', type: 'tag', x: h3x, y: h3y, vx: 0, vy: 0, fx: null, fy: null, notesCount: 5, color: '#10b981' }
  ]

  links.value = [
    { source: 'hub1', target: 'hub2' },
    { source: 'hub2', target: 'hub3' },
    { source: 'hub3', target: 'hub1' }
  ]

  // Pre-expand all 3 hubs at startup to show the neural network radial structure
  expandedTags.value.clear()
  expandedTags.value.add('hub1')
  expandedTags.value.add('hub2')
  expandedTags.value.add('hub3')

  const hubConfigs = [
    { id: 'hub1', x: h1x, y: h1y, count: 3, startNum: 1 },
    { id: 'hub2', x: h2x, y: h2y, count: 4, startNum: 4 },
    { id: 'hub3', x: h3x, y: h3y, count: 5, startNum: 8 }
  ]

  const childRadius = 95
  for (const config of hubConfigs) {
    for (let i = 0; i < config.count; i++) {
      const childId = `${config.id}-node${i+1}`
      const num = config.startNum + i
      const noteInDb = allNotes.value[childId]
      const childLabel = noteInDb ? noteInDb.title : `节点 ${num}`
      
      const angle = getIdealAngle(config.id, i, config.count)
      const spawnX = config.x + Math.cos(angle) * childRadius
      const spawnY = config.y + Math.sin(angle) * childRadius

      nodes.value.push({
        id: childId,
        label: childLabel,
        type: 'note',
        x: spawnX,
        y: spawnY,
        vx: 0, vy: 0,
        fx: null, fy: null,
        notesCount: 0,
        noteId: childId,
        color: 'var(--color-text-muted)',
        idealAngle: angle
      })

      links.value.push({
        source: config.id,
        target: childId
      })
    }
  }

  isSimulating.value = true
  resumeSimulation()
}

// ---- Verlet Physics Engine ----
function updatePhysics() {
  const currentNodes = nodes.value
  const currentLinks = links.value
  const cx = width.value / 2
  const cy = height.value / 2

  // 1. Repulsion between all nodes (prevent overlaps & implement elastic collisions)
  for (let i = 0; i < currentNodes.length; i++) {
    for (let j = i + 1; j < currentNodes.length; j++) {
      const n1 = currentNodes[i]
      const n2 = currentNodes[j]
      const dx = n2.x - n1.x
      const dy = n2.y - n1.y
      const distSq = dx * dx + dy * dy + 0.1
      const dist = Math.sqrt(distSq)
      
      // Magnetic-like long-range repulsion
      if (dist < 260) {
        const force = 3200 / distSq
        const fx = force * (dx / dist)
        const fy = force * (dy / dist)
        n1.vx -= fx
        n1.vy -= fy
        n2.vx += fx
        n2.vy += fy
      }

      // Hard elastic collision resolver (prevents overlapping completely)
      const r1 = n1.type === 'tag' ? 22 : 15
      const r2 = n2.type === 'tag' ? 22 : 15
      const minDist = r1 + r2 + 12 // Collision boundaries based on node sizes + padding
      if (dist < minDist) {
        const overlap = minDist - dist
        const pushX = (dx / dist) * overlap * 0.5
        const pushY = (dy / dist) * overlap * 0.5

        if (n1.fx === null) {
          n1.x -= pushX
          n1.vx -= pushX * 0.15
        }
        if (n2.fx === null) {
          n2.x += pushX
          n2.vx += pushX * 0.15
        }
        if (n1.fy === null) {
          n1.y -= pushY
          n1.vy -= pushY * 0.15
        }
        if (n2.fy === null) {
          n2.y += pushY
          n2.vy += pushY * 0.15
        }
      }
    }
  }

  // 2. Attraction along links (spring force with dynamic stretchy rest lengths)
  for (const link of currentLinks) {
    const n1 = currentNodes.find(n => n.id === link.source)
    const n2 = currentNodes.find(n => n.id === link.target)
    if (n1 && n2) {
      const dx = n2.x - n1.x
      const dy = n2.y - n1.y
      const dist = Math.sqrt(dx * dx + dy * dy) + 0.1
      
      // Dynamic rest length & stiffness based on link types
      let restLength = 110
      let k = 0.05
      if (n1.type === 'tag' && n2.type === 'tag') {
        // Hub to Hub: keep them further apart to prevent cluster overlap
        restLength = 160
        k = 0.06
      } else {
        // Hub to Child Node: soft, stretchier spring for organic breathing movement
        restLength = 95
        k = 0.025
      }

      const force = k * (dist - restLength)
      const fx = force * (dx / dist)
      const fy = force * (dy / dist)
      n1.vx += fx
      n1.vy += fy
      n2.vx -= fx
      n2.vy -= fy
    }
  }

  // 3. Ideal angle restoring force (keeps leaf nodes fanned outward, preventing crossings)
  for (const n of currentNodes) {
    if (n.type === 'note' && n.idealAngle !== undefined) {
      const parentId = n.id.split('-')[0]
      const parent = currentNodes.find(p => p.id === parentId)
      if (parent) {
        const idealX = parent.x + Math.cos(n.idealAngle) * 95
        const idealY = parent.y + Math.sin(n.idealAngle) * 95
        // Softly pull toward ideal outward angular sector
        n.vx += (idealX - n.x) * 0.03
        n.vy += (idealY - n.y) * 0.03
      }
    }
  }

  // 4. Gravity pulling toward center
  const gravity = 0.015
  for (const n of currentNodes) {
    n.vx += (cx - n.x) * gravity
    n.vy += (cy - n.y) * gravity
  }

  // 5. Update positions with damping & slow random drift
  const damping = 0.82
  for (const n of currentNodes) {
    const isHovered = n.id === hoveredNodeId.value
    const isSelected = n.id === selectedNodeId.value
    const isDragged = activeDragNode.value && activeDragNode.value.id === n.id

    // If the node is hovered, selected, or actively dragged, it must be completely static/frozen in place
    if (isHovered || isSelected || isDragged) {
      n.vx = 0
      n.vy = 0
      
      // If it is dragged, update its position to the drag anchor directly
      if (isDragged && n.fx !== null && n.fy !== null) {
        n.x = n.fx
        n.y = n.fy
      }
      
      // Prevent any further drift, gravity, or spring movement for this node
      continue
    }

    // Apply slow random drift to normal unpinned/unhovered nodes to make them feel alive
    if (n.id !== 'center') {
      const time = Date.now() * 0.001
      const hash = n.label.charCodeAt(0) + (n.label.charCodeAt(n.label.length - 1) || 0)
      
      // Use multi-frequency waves to produce a gentle sway/drift rather than simple rotation
      const dx = Math.sin(time * 0.35 + hash) + Math.cos(time * 0.12 + hash * 1.5)
      const dy = Math.cos(time * 0.28 - hash * 0.7) + Math.sin(time * 0.18 + hash * 2.1)
      
      const driftSpeed = 0.12 // Gentle and subtle drift speed
      n.vx += dx * driftSpeed
      n.vy += dy * driftSpeed
    }

    if (n.fx !== null) {
      n.x = n.fx
      n.vx = 0
    } else {
      n.vx *= damping
      n.x += n.vx
    }
    if (n.fy !== null) {
      n.y = n.fy
      n.vy = 0
    } else {
      n.vy *= damping
      n.y += n.vy
    }

    // Boundary constraints
    n.x = Math.max(40, Math.min(width.value - 40, n.x))
    n.y = Math.max(40, Math.min(height.value - 40, n.y))
  }

  // Keep simulating to support continuous slow random drift
  animationFrameId = requestAnimationFrame(updatePhysics)
}

function resumeSimulation() {
  if (!isSimulating.value || !animationFrameId) {
    isSimulating.value = true
    animationFrameId = requestAnimationFrame(updatePhysics)
  }
}

// ---- Canvas Panning & Zooming ----
function handleCanvasMouseDown(event: MouseEvent) {
  // Only pan when clicking empty area of SVG canvas
  if (event.target && (event.target as SVGElement).tagName === 'svg') {
    isPanning.value = true
    panStartX = event.clientX - panX.value
    panStartY = event.clientY - panY.value
  }
}

function handleCanvasMouseMove(event: MouseEvent) {
  if (activeDragNode.value) {
    // Handle dragging node
    const svgElement = document.querySelector('.notes-graph-svg')
    if (svgElement) {
      const rect = svgElement.getBoundingClientRect()
      const localX = event.clientX - rect.left
      const localY = event.clientY - rect.top
      // Apply inverse matrix (zoom and pan) to find exact local SVG position
      activeDragNode.value.fx = (localX - panX.value) / zoom.value
      activeDragNode.value.fy = (localY - panY.value) / zoom.value
    }
  } else if (isPanning.value) {
    // Handle panning canvas
    panX.value = event.clientX - panStartX
    panY.value = event.clientY - panStartY
  }
}

function handleGlobalMouseUp() {
  if (activeDragNode.value) {
    activeDragNode.value.fx = null
    activeDragNode.value.fy = null
    activeDragNode.value = null
  }
  isPanning.value = false
}

function handleWheel(event: WheelEvent) {
  event.preventDefault()
  const zoomFactor = 1.05
  if (event.deltaY < 0) {
    zoom.value = Math.min(2.5, zoom.value * zoomFactor)
  } else {
    zoom.value = Math.max(0.4, zoom.value / zoomFactor)
  }
}

function resetZoom() {
  panX.value = 0
  panY.value = 0
  zoom.value = 1.0
  resumeSimulation()
}

// ---- Dragging Nodes ----
function startDrag(event: MouseEvent, node: Node) {
  event.stopPropagation()
  activeDragNode.value = node
  node.fx = node.x
  node.fy = node.y
  resumeSimulation()
}

// ---- Graph Node Clicking (Expansion Logic) ----
function handleNodeClick(node: Node) {
  selectedNodeId.value = node.id

  if (node.type === 'note' && node.noteId) {
    // Opening a note node
    openNote(node.noteId)
  } else if (node.type === 'tag' && node.id !== 'center') {
    // Click tag node
    if (node.notesCount === 1) {
      // Small content: directly open the single note
      const singleNote = Object.values(allNotes.value).find(n => n.tags.includes(node.id))
      if (singleNote) openNote(singleNote.id)
    } else {
      // Dynamic leaf node expansion/collapsing
      toggleTagExpansion(node)
    }
  }
}

function toggleTagExpansion(tagNode: Node) {
  const tagName = tagNode.id
  if (expandedTags.value.has(tagName)) {
    // Collapse: remove note nodes of this hub
    expandedTags.value.delete(tagName)
    nodes.value = nodes.value.filter(n => !(n.type === 'note' && n.id.startsWith(tagName + '-')))
    links.value = links.value.filter(l => !(l.source === tagName && l.target.startsWith(tagName + '-')))
  } else {
    // Expand: spawn child nodes radially
    expandedTags.value.add(tagName)
    
    let childrenCount = 3
    let startNum = 1
    if (tagName === 'hub2') {
      childrenCount = 4
      startNum = 4
    } else if (tagName === 'hub3') {
      childrenCount = 5
      startNum = 8
    }

    const radius = 95
    for (let i = 0; i < childrenCount; i++) {
      const childId = `${tagName}-node${i+1}`
      const num = startNum + i
      const noteInDb = allNotes.value[childId]
      const childLabel = noteInDb ? noteInDb.title : `节点 ${num}`
      
      const angle = getIdealAngle(tagName, i, childrenCount)
      const spawnX = tagNode.x + Math.cos(angle) * radius
      const spawnY = tagNode.y + Math.sin(angle) * radius

      nodes.value.push({
        id: childId,
        label: childLabel,
        type: 'note',
        x: spawnX,
        y: spawnY,
        vx: 0, vy: 0,
        fx: null, fy: null,
        notesCount: 0,
        noteId: childId,
        color: 'var(--color-text-muted)',
        idealAngle: angle
      })

      links.value.push({
        source: tagName,
        target: childId
      })
    }
  }
  resumeSimulation()
}

// ---- Node Styling & Highlights ----
const connectedNodesAndLinks = computed(() => {
  const activeId = hoveredNodeId.value || selectedNodeId.value
  if (!activeId) return { nodes: new Set<string>(), links: new Set<string>() }

  const connectedNodes = new Set<string>([activeId])
  const connectedLinks = new Set<string>()

  links.value.forEach(l => {
    if (l.source === activeId) {
      connectedNodes.add(l.target)
      connectedLinks.add(`${l.source}-${l.target}`)
    } else if (l.target === activeId) {
      connectedNodes.add(l.source)
      connectedLinks.add(`${l.source}-${l.target}`)
    }
  })

  return { nodes: connectedNodes, links: connectedLinks }
})

// Query-filtered nodes list for highlight search
const searchedNodeIds = computed(() => {
  if (!searchQuery.value.trim()) return new Set<string>()
  const q = searchQuery.value.toLowerCase().trim()
  const matching = new Set<string>()
  
  nodes.value.forEach(n => {
    if (n.label.toLowerCase().includes(q)) {
      matching.add(n.id)
    }
  })
  return matching
})

// ---- Note Open & Reader Logic ----
function openNote(noteId: string) {
  let note = allNotes.value[noteId]
  if (!note) {
    const nodeObj = nodes.value.find(n => n.id === noteId)
    const displayName = nodeObj ? nodeObj.label : `节点`
    const hubIndex = noteId.includes('hub1') ? '1' : (noteId.includes('hub2') ? '2' : '3')
    
    note = {
      id: noteId,
      title: displayName,
      tags: [`中枢 ${hubIndex}`],
      content: `# ${displayName} 学习笔记\n\n这是关于 **${displayName}** 的学习笔记静态演示正文。\n\n## 1. 概念与基础\n\n在知识图谱的构建中，每个节点代表一个独特的实体或概念。通过建立节点之间的关联，我们可以形成多维度的信息网格。\n\n* **高内聚**：节点与其直接关联的中枢之间应具备强关联性。\n* **低耦合**：中枢与中枢之间通过主连线连接，减少网络复杂度。\n\n## 2. 实践代码\n\n这里我们可以放置一些测试代码：\n\n\`\`\`python\ndef calculate_relationship(node_a, node_b):\n    # 计算两个知识节点之间的拉力\n    distance = get_distance(node_a, node_b)\n    return k * (distance - rest_length)\n\`\`\`\n\n> [!NOTE]\n> 点击关系图上的其他节点，或者双击空白处，可以探索更多知识拓扑神经元。`
    }
    allNotes.value[noteId] = note
  }
  activeNoteId.value = noteId
  isDrawerOpen.value = true
  isEditing.value = false
  // Synchronize selection node highlight
  selectedNodeId.value = noteId
}

function closeDrawer() {
  isDrawerOpen.value = false
  activeNoteId.value = null
  isEditing.value = false
}

// Simple Custom Markdown Parser (Safe and reactive inside Vue template)
function parseMarkdown(md: string): string {
  let html = md
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  // GFM style Alert parsing
  html = html.replace(/&gt;\s*\[!(IMPORTANT|WARNING|CAUTION|TIP|NOTE)\]\r?\n&gt;\s*(.+)/g, (_match, type, text) => {
    const alerts = {
      IMPORTANT: 'border-l-4 border-violet-500 bg-violet-500/10 text-violet-300 p-3.5 rounded-r-xl my-4 text-xs tracking-wide',
      WARNING: 'border-l-4 border-amber-500 bg-amber-500/10 text-amber-300 p-3.5 rounded-r-xl my-4 text-xs tracking-wide',
      CAUTION: 'border-l-4 border-rose-500 bg-rose-500/10 text-rose-300 p-3.5 rounded-r-xl my-4 text-xs tracking-wide',
      TIP: 'border-l-4 border-emerald-500 bg-emerald-500/10 text-emerald-300 p-3.5 rounded-r-xl my-4 text-xs tracking-wide',
      NOTE: 'border-l-4 border-slate-500 bg-slate-500/10 text-slate-300 p-3.5 rounded-r-xl my-4 text-xs tracking-wide',
    }
    const cls = alerts[type as keyof typeof alerts] || ''
    return `<div class="${cls}"><strong>${type}</strong>: ${text}</div>`
  })

  // Headings
  html = html.replace(/^#\s+(.+)$/gm, '<h1 class="text-2xl font-extrabold text-text font-serif mt-6 mb-4 leading-snug">$1</h1>')
  html = html.replace(/^##\s+(.+)$/gm, '<h2 class="text-xl font-bold text-text font-serif mt-5 mb-3 border-b border-border pb-1">$1</h2>')
  html = html.replace(/^###\s+(.+)$/gm, '<h3 class="text-lg font-bold text-text font-serif mt-4 mb-2">$1</h3>')

  // Code Block
  html = html.replace(/```(\w*)\r?\n([\s\S]+?)\r?\n```/g, '<pre class="bg-surface-light border border-border p-4 rounded-xl font-mono text-xs text-text overflow-x-auto my-4"><code class="language-$1">$2</code></pre>')

  // Inline Code
  html = html.replace(/`([^`]+)`/g, '<code class="bg-surface-light text-primary-light px-1.5 py-0.5 rounded font-mono text-xs">$1</code>')

  // Quotes
  html = html.replace(/^&gt;\s+(.+)$/gm, '<blockquote class="border-l-4 border-primary pl-4 italic text-text-muted my-4">$1</blockquote>')

  // Table support
  const lines = html.split('\n')
  let inTable = false
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim()
    if (line.startsWith('|') && line.endsWith('|')) {
      if (!inTable) {
        inTable = true
        lines[i] = '<div class="overflow-x-auto my-6"><table class="w-full text-left text-xs border-collapse"><thead class="bg-surface-light border-b border-border text-text-muted"><tr>' + 
          line.split('|').slice(1, -1).map(c => `<th class="px-4 py-3 font-semibold">${c.trim()}</th>`).join('') + 
          '</tr></thead><tbody class="divide-y divide-border/50">'
      } else if (line.includes('---')) {
        lines[i] = ''
      } else {
        lines[i] = '<tr class="hover:bg-surface-light/30 transition-colors">' + 
          line.split('|').slice(1, -1).map(c => `<td class="px-4 py-3 text-text">${c.trim()}</td>`).join('') + 
          '</tr>'
      }
    } else {
      if (inTable) {
        inTable = false
        lines[i] = '</tbody></table></div>' + lines[i]
      }
    }
  }
  html = lines.join('\n')

  // Bold & Italic
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>')
  
  // Math Block / Inline Math
  html = html.replace(/\$\$([\s\S]+?)\$\$/g, '<div class="text-center my-6 py-3 bg-surface-light border border-border rounded-xl font-mono text-xs text-text overflow-x-auto">$1</div>')
  html = html.replace(/\\\((.+?)\\\)/g, '<span class="font-mono text-primary-light bg-surface-light px-1 py-0.5 rounded text-xs">$1</span>')

  // Lists
  html = html.replace(/^\*\s+(.+)$/gm, '<li class="list-disc list-inside ml-4 text-text-muted my-1.5">$1</li>')
  html = html.replace(/^\d+\.\s+(.+)$/gm, '<li class="list-decimal list-inside ml-4 text-text-muted my-1.5">$1</li>')

  // Paragraph wrapper
  const paragraphs = html.split(/\n{2,}/)
  for (let i = 0; i < paragraphs.length; i++) {
    const p = paragraphs[i].trim()
    if (p && !p.startsWith('<h') && !p.startsWith('<div') && !p.startsWith('<pre') && !p.startsWith('<table') && !p.startsWith('<blockquote') && !p.startsWith('<li') && !p.startsWith('<ul') && !p.startsWith('<ol')) {
      paragraphs[i] = `<p class="leading-relaxed text-text-muted my-4 text-sm">${p}</p>`
    }
  }
  html = paragraphs.join('\n')

  return html
}

const renderedMarkdown = computed(() => {
  const note = allNotes.value[activeNoteId.value ?? '']
  return note ? parseMarkdown(note.content) : ''
})

// ---- Edit & Save Note ----
function enterEdit() {
  const note = allNotes.value[activeNoteId.value ?? '']
  if (note) {
    editTitle.value = note.title
    editContent.value = note.content
    editTagsString.value = note.tags.join(', ')
    isEditing.value = true
  }
}

function saveEdit() {
  const id = activeNoteId.value
  if (id && editTitle.value.trim() && editContent.value.trim()) {
    const newTags = editTagsString.value.split(',').map(t => t.trim()).filter(t => t.length > 0)
    
    // Update memory DB
    allNotes.value[id].title = editTitle.value
    allNotes.value[id].content = editContent.value
    allNotes.value[id].tags = newTags

    // Update node label
    const node = nodes.value.find(n => n.id === id)
    if (node) node.label = editTitle.value

    isEditing.value = false
    
    // Refresh UI graph structure
    initGraph()
  }
}

function createNewNote() {
  const newId = 'note-' + Date.now()
  allNotes.value[newId] = {
    id: newId,
    title: '未命名笔记',
    tags: ['未分类'],
    content: '# 未命名笔记\n\n在此输入您的笔记正文...\n\n支持标准的 Markdown 渲染。'
  }
  // Initialize newly created tag if it doesn't exist on graph
  if (!nodes.value.some(n => n.id === '未分类')) {
    nodes.value.push({
      id: '未分类',
      label: '未分类',
      type: 'tag',
      x: 350 + (Math.random() - 0.5) * 80,
      y: 350 + (Math.random() - 0.5) * 80,
      vx: 0, vy: 0,
      fx: null, fy: null,
      notesCount: 1,
      color: 'var(--color-primary)'
    })
    links.value.push({ source: 'center', target: '未分类' })
  } else {
    const uncatTag = nodes.value.find(n => n.id === '未分类')
    if (uncatTag) uncatTag.notesCount++
  }
  
  openNote(newId)
  enterEdit()
  resumeSimulation()
}

// ---- Delete Note ----
function deleteNote(noteId: string) {
  if (confirm(`确认要删除《${allNotes.value[noteId].title}》吗？`)) {
    const noteTags = allNotes.value[noteId].tags
    delete allNotes.value[noteId]
    
    // Remove note node and links from graph
    nodes.value = nodes.value.filter(n => n.id !== noteId)
    links.value = links.value.filter(l => l.target !== noteId)

    // Decrement tags count
    noteTags.forEach(tagName => {
      const tagNode = nodes.value.find(n => n.id === tagName)
      if (tagNode) {
        tagNode.notesCount = Math.max(0, tagNode.notesCount - 1)
      }
    })

    isDrawerOpen.value = false
    activeNoteId.value = null
    isEditing.value = false
    resumeSimulation()
  }
}

// ---- File Drop & Markdown parsing ----
const isDragOver = ref(false)

function handleFileDrop(event: DragEvent) {
  event.preventDefault()
  isDragOver.value = false
  
  if (event.dataTransfer?.files && event.dataTransfer.files.length > 0) {
    const file = event.dataTransfer.files[0]
    if (file.name.endsWith('.md')) {
      const reader = new FileReader()
      reader.onload = (e) => {
        const text = e.target?.result as string
        parseAndInjectUploadedMarkdown(file.name, text)
      }
      reader.readAsText(file)
    } else {
      alert('请上传以 .md 结尾的 Markdown 格式文件')
    }
  }
}

function parseAndInjectUploadedMarkdown(filename: string, fileContent: string) {
  // Extract Frontmatter metadata
  const frontmatterMatch = fileContent.match(/^---\r?\n([\s\S]+?)\r?\n---/)
  let title = filename.replace(/\.md$/, '')
  let tags = ['导入笔记']

  if (frontmatterMatch) {
    const yaml = frontmatterMatch[1]
    const titleMatch = yaml.match(/title:\s*(.+)/)
    if (titleMatch) title = titleMatch[1].replace(/['"]/g, '').trim()
    const tagsMatch = yaml.match(/tags:\s*\[?([^\]\n]+)\]?/)
    if (tagsMatch) {
      tags = tagsMatch[1].split(',').map(t => t.trim().replace(/['"]/g, ''))
    }
  }

  const newId = 'uploaded-' + Date.now()
  
  // Save to mock DB
  allNotes.value[newId] = {
    id: newId,
    title: title,
    tags: tags,
    content: fileContent
  }

  // Inject Tags nodes if they don't exist
  tags.forEach(tag => {
    if (!nodes.value.some(n => n.id === tag)) {
      nodes.value.push({
        id: tag,
        label: tag,
        type: 'tag',
        x: 400 + (Math.random() - 0.5) * 150,
        y: 300 + (Math.random() - 0.5) * 150,
        vx: 0, vy: 0,
        fx: null, fy: null,
        notesCount: 1,
        color: '#a78bfa'
      })
      links.value.push({ source: 'center', target: tag })
    } else {
      const existingTag = nodes.value.find(n => n.id === tag)
      if (existingTag) existingTag.notesCount++
    }
  })

  // Pop up tag expansion automatically and spawn note
  tags.forEach(tag => {
    expandedTags.value.add(tag)
    const tagNode = nodes.value.find(n => n.id === tag)
    if (tagNode) {
      nodes.value.push({
        id: newId,
        label: title,
        type: 'note',
        x: tagNode.x + (Math.random() - 0.5) * 50,
        y: tagNode.y + (Math.random() - 0.5) * 50,
        vx: 0, vy: 0,
        fx: null, fy: null,
        notesCount: 0,
        noteId: newId,
        color: 'var(--color-text-muted)'
      })
      links.value.push({ source: tag, target: newId })
    }
  })

  // Select and view
  openNote(newId)
  resumeSimulation()
}

// ---- Lifecycles ----
onMounted(() => {
  // Sync global theme
  const savedTheme = localStorage.getItem('theme')
  if (savedTheme) {
    isDark.value = savedTheme === 'dark'
  } else {
    isDark.value = !document.documentElement.classList.contains('theme-light')
  }
  updateThemeClass()

  // Initialize nodes & physics
  initGraph()
  
  // Bind global drag release
  window.addEventListener('mouseup', handleGlobalMouseUp)
})

onUnmounted(() => {
  if (animationFrameId) cancelAnimationFrame(animationFrameId)
  window.removeEventListener('mouseup', handleGlobalMouseUp)
})
</script>

<template>
  <div class="min-h-screen bg-surface pb-12 flex flex-col font-sans select-none overflow-hidden"
    @dragover.prevent="isDragOver = true">
    <!-- Top bar -->
    <header class="sticky top-0 z-20 bg-surface/80 backdrop-blur-md border-b border-border px-6 py-4 flex items-center gap-4">
      <button @click="router.push('/')" class="flex items-center gap-2 text-text-muted hover:text-text transition-colors duration-200">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
        </svg>
        <span class="text-sm">Dashboard</span>
      </button>
      <span class="text-border">|</span>
      <h1 class="text-sm font-medium text-text">KnowledgeMap · 笔记与知识拓扑</h1>

      <div class="ml-auto flex items-center gap-3">
        <!-- Search bar -->
        <div class="relative w-48 md:w-64">
          <input
            v-model="searchQuery"
            type="text"
            placeholder="搜索标签/笔记..."
            class="w-full bg-surface-light border border-border rounded-xl px-3 py-1.5 text-xs text-text focus:outline-none focus:border-primary/50 transition-colors"
          />
          <span v-if="searchQuery" @click="searchQuery = ''" class="absolute right-3 top-2 text-text-muted text-xs cursor-pointer hover:text-text">✕</span>
        </div>

        <button @click="initGraph" type="button"
          class="flex items-center justify-center w-8 h-8 rounded-lg border border-border text-text-muted hover:text-text hover:border-primary/50 transition-colors duration-200"
          title="重置网络结构">
          <span class="text-base leading-none">⟳</span>
        </button>
        <button @click="toggleTheme" type="button"
          class="flex items-center justify-center w-8 h-8 rounded-lg border border-border text-text-muted hover:text-text hover:border-primary/50 transition-colors duration-200 active:scale-95"
          aria-label="Toggle theme">
          <span class="text-base leading-none">{{ isDark ? '☾' : '☼' }}</span>
        </button>
        <button @click="createNewNote"
          class="flex items-center gap-2 px-4 py-1.5 rounded-lg bg-primary text-white text-sm font-medium hover:bg-primary-dark transition-colors duration-200 active:scale-[0.97]">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          写笔记
        </button>
      </div>
    </header>

    <div class="flex-1 flex flex-col md:flex-row relative">
      <!-- Left Panel: Interactive Graph -->
      <div 
        class="flex-1 relative cursor-grab bg-surface select-none"
        :class="{ 'cursor-grabbing': isPanning }"
        @mousedown="handleCanvasMouseDown"
        @mousemove="handleCanvasMouseMove"
        @wheel="handleWheel"
      >
        <div class="absolute top-4 left-6 z-10 bg-surface-card/65 backdrop-blur-sm border border-border px-4 py-3 rounded-2xl max-w-sm pointer-events-none">
          <h2 class="text-xs font-bold text-text mb-1 tracking-wide">力导向神经元网络拓扑图</h2>
          <p class="text-[10px] text-text-muted leading-relaxed">
            • 标签节点支持点击展开二级笔记<br />
            • 拖动任意节点重置布局结构；滚轮缩放/平移画布<br />
            • 尝试拖拽本地 Markdown (.md) 文件至界面上传！
          </p>
        </div>

        <button 
          v-if="zoom !== 1.0 || panX !== 0 || panY !== 0" 
          @click="resetZoom"
          class="absolute bottom-4 left-6 z-10 px-3 py-1.5 bg-surface-card border border-border rounded-xl text-xs text-text-muted hover:text-text hover:border-primary/50 transition-all active:scale-95"
        >
          重设视图 (x: {{ Math.round(panX) }}, y: {{ Math.round(panY) }}, {{ Math.round(zoom * 100) }}%)
        </button>

        <svg 
          class="w-full h-full notes-graph-svg min-h-[70vh] md:min-h-0" 
          @mouseup="handleGlobalMouseUp"
          @mouseleave="handleGlobalMouseUp"
        >
          <!-- Grid backdrop (only in dark mode) -->
          <defs v-if="isDark">
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255,255,255,0.03)" stroke-width="1" />
            </pattern>
          </defs>
          <rect v-if="isDark" width="100%" height="100%" fill="url(#grid)" />

          <!-- Camera transforms -->
          <g :transform="`translate(${panX}, ${panY}) scale(${zoom})`">
            <!-- Connection lines -->
            <line 
              v-for="link in links" 
              :key="`${link.source}-${link.target}`"
              :x1="nodes.find(n => n.id === link.source)?.x ?? 0"
              :y1="nodes.find(n => n.id === link.source)?.y ?? 0"
              :x2="nodes.find(n => n.id === link.target)?.x ?? 0"
              :y2="nodes.find(n => n.id === link.target)?.y ?? 0"
              class="transition-all duration-200"
              :stroke="
                connectedNodesAndLinks.links.has(`${link.source}-${link.target}`) || 
                connectedNodesAndLinks.links.has(`${link.target}-${link.source}`)
                  ? 'var(--color-primary)' 
                  : (isDark ? 'rgba(255,255,255,0.075)' : 'rgba(90,80,75,0.12)')
              "
              :stroke-width="
                connectedNodesAndLinks.links.has(`${link.source}-${link.target}`) || 
                connectedNodesAndLinks.links.has(`${link.target}-${link.source}`)
                  ? 2 
                  : 1.2
              "
            />

            <!-- Connection lines highlights (glow effect) -->
            <line 
              v-if="isDark"
              v-for="link in links.filter(l => connectedNodesAndLinks.links.has(`${l.source}-${l.target}`) || connectedNodesAndLinks.links.has(`${l.target}-${l.source}`))" 
              :key="`glow-${link.source}-${link.target}`"
              :x1="nodes.find(n => n.id === link.source)?.x ?? 0"
              :y1="nodes.find(n => n.id === link.source)?.y ?? 0"
              :x2="nodes.find(n => n.id === link.target)?.x ?? 0"
              :y2="nodes.find(n => n.id === link.target)?.y ?? 0"
              stroke="var(--color-primary)"
              stroke-width="5"
              opacity="0.22"
              style="filter: blur(2px);"
            />

            <!-- SVG Dashed flowing data stream line -->
            <line 
              v-for="link in links" 
              :key="`flow-${link.source}-${link.target}`"
              :x1="nodes.find(n => n.id === link.source)?.x ?? 0"
              :y1="nodes.find(n => n.id === link.source)?.y ?? 0"
              :x2="nodes.find(n => n.id === link.target)?.x ?? 0"
              :y2="nodes.find(n => n.id === link.target)?.y ?? 0"
              class="flow-line pointer-events-none"
              :stroke="
                connectedNodesAndLinks.links.has(`${link.source}-${link.target}`) || 
                connectedNodesAndLinks.links.has(`${link.target}-${link.source}`)
                  ? 'var(--color-primary-light)' 
                  : (isDark ? 'rgba(255,255,255,0.06)' : 'rgba(90,80,75,0.08)')
              "
              :stroke-width="
                connectedNodesAndLinks.links.has(`${link.source}-${link.target}`) || 
                connectedNodesAndLinks.links.has(`${link.target}-${link.source}`)
                  ? 2
                  : 1
              "
              :style="{
                animationDuration: 
                  connectedNodesAndLinks.links.has(`${link.source}-${link.target}`) || 
                  connectedNodesAndLinks.links.has(`${link.target}-${link.source}`)
                    ? '1.2s' 
                    : '4.5s'
              }"
            />

            <!-- Graph nodes -->
            <g 
              v-for="node in nodes" 
              :key="node.id"
              :transform="`translate(${node.x}, ${node.y})`"
              class="cursor-pointer group"
              @mousedown="startDrag($event, node)"
              @click.stop="handleNodeClick(node)"
              @mouseenter="hoveredNodeId = node.id"
              @mouseleave="hoveredNodeId = null"
            >
              <!-- Invisible larger hit area for hover and drag stability -->
              <circle 
                r="32" 
                fill="transparent" 
              />

              <!-- Locked state indicator (dashed spinning ring) -->
              <circle
                v-if="hoveredNodeId === node.id || selectedNodeId === node.id"
                r="24"
                fill="none"
                stroke="var(--color-primary-light)"
                stroke-width="1.2"
                stroke-dasharray="3, 4"
                class="node-lock-ring"
              />

              <!-- Outer glowing ring on active/hovered/searched -->
              <circle 
                r="30" 
                fill="none"
                class="transition-all duration-300"
                :stroke="node.color"
                :stroke-width="
                  selectedNodeId === node.id || hoveredNodeId === node.id
                    ? 3
                    : (searchedNodeIds.has(node.id) ? 2 : 0)
                "
                :opacity="selectedNodeId === node.id || hoveredNodeId === node.id ? 0.35 : (searchedNodeIds.has(node.id) ? 0.7 : 0)"
                :class="selectedNodeId === node.id || hoveredNodeId === node.id || searchedNodeIds.has(node.id) ? 'scale-110' : ''"
              />

              <!-- Inner filled node -->
              <circle 
                :r="node.type === 'tag' ? (node.id === 'center' ? 18 : 15) : 10" 
                :fill="node.type === 'tag' ? node.color : 'var(--color-surface-card)'"
                :stroke="node.type === 'tag' ? 'transparent' : 'var(--color-border)'"
                stroke-width="1.8"
                class="transition-all duration-350 shadow-md group-hover:scale-110"
                :class="[
                  selectedNodeId === node.id ? 'stroke-primary stroke-2' : '',
                  searchedNodeIds.has(node.id) ? 'pulse-searched' : ''
                ]"
              />

              <!-- Nodes text label -->
              <text 
                y="24"
                text-anchor="middle"
                class="text-[10px] pointer-events-none select-none transition-all duration-300"
                :class="[
                  selectedNodeId === node.id || hoveredNodeId === node.id || searchedNodeIds.has(node.id)
                    ? 'fill-text font-bold text-xs' 
                    : 'fill-text-muted'
                ]"
              >
                {{ node.label }}
                <tspan v-if="node.type === 'tag' && node.notesCount > 0" class="opacity-60 text-[9px] fill-text-muted">
                  ({{ node.notesCount }})
                </tspan>
              </text>
            </g>
          </g>
        </svg>
      </div>

      <!-- Drag & Drop Uploader Overlay -->
      <div 
        class="absolute inset-0 z-10 flex items-center justify-center p-8 transition-all duration-300"
        :class="isDragOver ? 'bg-primary/10 opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'"
        @dragover.prevent="isDragOver = true"
        @dragleave.prevent="isDragOver = false"
        @drop="handleFileDrop"
      >
        <div class="border-3 border-dashed border-primary rounded-3xl bg-surface-card/90 backdrop-blur-md p-10 text-center max-w-sm pointer-events-none shadow-2xl">
          <svg class="w-12 h-12 text-primary mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
          <h3 class="font-bold text-text mb-2">拖拽上传 Markdown</h3>
          <p class="text-xs text-text-muted">松开鼠标即可自动解析 yaml 头部的标题与标签，并生成动态拓扑节点关联关系图</p>
        </div>
      </div>

      <!-- Right Panel: Collapsible Reader Drawer -->
      <div 
        class="fixed top-0 right-0 h-full w-full md:w-[480px] bg-surface-card border-l border-border z-30 shadow-2xl note-drawer-transition flex flex-col"
        :class="isDrawerOpen ? 'translate-x-0' : 'translate-x-full'"
      >
        <div class="flex items-center justify-between px-6 py-4 border-b border-border bg-surface/50">
          <span class="text-xs text-text-muted uppercase tracking-wider font-mono">Note Reader</span>
          <div class="flex gap-2">
            <button v-if="!isEditing" @click="enterEdit"
              class="w-7 h-7 rounded-lg flex items-center justify-center text-text-muted hover:text-primary hover:bg-primary/10 transition-colors">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
            </button>
            <button v-if="!isEditing" @click="deleteNote(activeNoteId!)"
              class="w-7 h-7 rounded-lg flex items-center justify-center text-text-muted hover:text-rose-400 hover:bg-rose-400/10 transition-colors">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
            <button @click="closeDrawer" class="w-7 h-7 rounded-lg flex items-center justify-center text-text-muted hover:text-text hover:bg-surface-light transition-colors">
              ✕
            </button>
          </div>
        </div>

        <!-- Scrollable content -->
        <div class="flex-1 overflow-y-auto px-6 py-8">
          <!-- Normal markdown read view -->
          <div v-if="!isEditing" class="prose prose-sm max-w-none text-text">
            <div class="flex flex-wrap gap-2 mb-4">
              <span 
                v-for="tag in allNotes[activeNoteId ?? '']?.tags" 
                :key="tag"
                class="px-2 py-0.5 rounded-md text-[10px] font-semibold bg-primary/10 text-primary-light border border-primary/20"
              >
                {{ tag }}
              </span>
            </div>
            
            <div v-html="renderedMarkdown" class="markdown-body"></div>
          </div>

          <!-- Edit markdown editor view -->
          <div v-else class="flex flex-col h-full space-y-4">
            <div>
              <label class="block text-xs text-text-muted mb-1">笔记标题</label>
              <input v-model="editTitle" type="text"
                class="w-full bg-surface-light border border-border rounded-xl px-3 py-2 text-sm text-text focus:outline-none focus:border-primary/50 transition-colors" />
            </div>
            <div>
              <label class="block text-xs text-text-muted mb-1">笔记分类标签（英文逗号分隔）</label>
              <input v-model="editTagsString" type="text"
                class="w-full bg-surface-light border border-border rounded-xl px-3 py-2 text-sm text-text focus:outline-none focus:border-primary/50 transition-colors" />
            </div>
            <div class="flex-1 flex flex-col min-h-[300px]">
              <label class="block text-xs text-text-muted mb-1">笔记正文 (Markdown)</label>
              <textarea v-model="editContent"
                class="flex-1 w-full bg-surface-light border border-border rounded-xl p-3 text-xs text-text font-mono focus:outline-none focus:border-primary/50 transition-colors resize-none"></textarea>
            </div>
            <div class="flex gap-3">
              <button @click="isEditing = false"
                class="flex-1 py-2.5 rounded-xl border border-border text-text-muted text-xs hover:border-primary/30 transition-colors">
                取消
              </button>
              <button @click="saveEdit"
                class="flex-1 py-2.5 rounded-xl bg-primary text-white text-xs font-medium hover:bg-primary-dark transition-colors active:scale-[0.98]">
                保存笔记
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.notes-graph-svg {
  background-color: var(--surface);
  transition: background-color 0.3s ease;
}

circle {
  transition: transform 0.3s cubic-bezier(0.2, 0.8, 0.2, 1), stroke-width 0.2s ease, fill 0.3s ease, stroke 0.3s ease;
}

text {
  font-family: inherit;
  user-select: none;
}

/* Pulsing outline animation for node search matching */
@keyframes pulse {
  0% { stroke-width: 2px; opacity: 0.7; }
  50% { stroke-width: 5px; opacity: 0.9; }
  100% { stroke-width: 2px; opacity: 0.7; }
}

.pulse-searched {
  animation: pulse 1.8s infinite ease-in-out;
  stroke: var(--color-primary);
}

/* Rotating dashed lock ring for selected/hovered nodes */
@keyframes spin-clockwise {
  to {
    transform: rotate(360deg);
  }
}
.node-lock-ring {
  transform-origin: 0px 0px;
  animation: spin-clockwise 14s linear infinite;
  pointer-events: none;
}

/* Smooth cubic-bezier drawer transition */
.note-drawer-transition {
  transition: transform 0.48s cubic-bezier(0.16, 1, 0.3, 1) !important;
}

/* Markdown typography rendering custom styling */
.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3) {
  font-family: var(--font-serif), inherit;
}

.markdown-body :deep(table) {
  border-spacing: 0;
  width: 100%;
}

.markdown-body :deep(table th) {
  border-bottom: 1px solid var(--border);
}

.markdown-body :deep(table td) {
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.theme-light .markdown-body :deep(table td) {
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}
</style>
