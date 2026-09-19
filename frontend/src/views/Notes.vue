<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const router = useRouter()
const route = useRoute()

// ---- Types ----
interface Node {
  id: string
  label: string
  type: 'center' | 'tag' | 'note'
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
  parentId?: string
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
  stage?: number
  prerequisites?: string[]
}

// ---- Data & Mock Database ----
const legacyNotes = ref<Record<string, NoteItem>>({
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

type NotebookId = 'transformer' | 'database' | 'cnn' | 'machine-learning'

interface NotebookConfig {
  id: NotebookId
  path: string
  tabLabel: string
  title: string
  eyebrow: string
  description: string
  columns: [string, string, string, string]
}

const notebooks: NotebookConfig[] = [
  {
    id: 'transformer',
    path: '/Transformer',
    tabLabel: 'Transformer',
    title: 'Transformer 学习笔记',
    eyebrow: 'TRANSFORMER NOTEBOOK',
    description: '从词元表示到注意力机制，一步步理解 Transformer 的结构。',
    columns: ['Transformer 输入层', '注意力机制', '编码器', '解码器与输出层'],
  },
  {
    id: 'database',
    path: '/Database',
    tabLabel: '数据库',
    title: '数据库学习笔记',
    eyebrow: 'DATABASE NOTEBOOK',
    description: '从数据模型到事务实践，建立可用于工程设计的数据库知识路径。',
    columns: ['数据模型', 'SQL 与查询', '索引与优化', '事务与工程实践'],
  },
  {
    id: 'cnn',
    path: '/CNN',
    tabLabel: 'CNN',
    title: 'CNN 学习笔记',
    eyebrow: 'CNN NOTEBOOK',
    description: '从图像张量到网络训练，理解卷积神经网络的关键结构。',
    columns: ['输入与卷积基础', '特征提取', '网络结构', '训练与应用'],
  },
  {
    id: 'machine-learning',
    path: '/MachineLearning',
    tabLabel: '机器学习与神经网络',
    title: '机器学习与神经网络笔记',
    eyebrow: 'MACHINE LEARNING NOTEBOOK',
    description: '把数学基础、经典模型与神经网络组织成连续的学习路线。',
    columns: ['数学基础', '经典机器学习', '神经网络', '训练与评估'],
  },
]

function topicNote(id: string, title: string, stage: number, tags: string[], prerequisites: string[] = [], summary = ''): NoteItem {
  return {
    id,
    title,
    stage,
    tags,
    prerequisites,
    content: `# ${title}\n\n${summary || `${title} 是本专题学习路径中的基础知识点。`}\n\n## 核心目标\n\n理解该知识点的输入、关键计算与输出，并能说明它和前后模块之间的关系。\n\n## 学习检查\n\n* 能用自己的语言解释核心概念。\n* 能写出主要公式或伪代码。\n* 能指出常见误区以及适用场景。`,
  }
}

const transformerNotes: Record<string, NoteItem> = {
  tokenization: topicNote('tokenization', '词元化与词表', 0, ['Transformer', '输入层'], [], '将原始文本切分为可索引的 token，并映射到固定词表。'),
  embedding: topicNote('embedding', 'Token Embedding', 0, ['Transformer', '输入层'], ['tokenization'], '把离散 token 映射为连续向量，形成模型可以处理的表示。'),
  'position-encoding': topicNote('position-encoding', '位置编码', 0, ['Transformer', '输入层'], ['embedding'], '向 token 表示注入顺序信息，使模型能够区分不同位置。'),
  'qkv-projection': topicNote('qkv-projection', 'Q、K、V 投影', 1, ['Transformer', '注意力机制'], ['embedding'], '通过三组线性变换得到 Query、Key 和 Value。'),
  'scaled-attention': topicNote('scaled-attention', '缩放点积注意力', 1, ['Transformer', '注意力机制'], ['qkv-projection', 'position-encoding'], '计算 Query 与 Key 的相似度，并对 Value 做加权汇总。'),
  'multi-head': topicNote('multi-head', '多头注意力', 1, ['Transformer', '注意力机制'], ['scaled-attention'], '并行学习多个注意力子空间，再拼接为统一表示。'),
  'residual-norm': topicNote('residual-norm', '残差连接与层归一化', 2, ['Transformer', '编码器'], ['multi-head'], '稳定深层网络训练，并保留子层输入信息。'),
  ffn: topicNote('ffn', '前馈神经网络', 2, ['Transformer', '编码器'], ['residual-norm'], '对每个位置独立应用两层非线性映射。'),
  'encoder-block': topicNote('encoder-block', '编码器模块', 2, ['Transformer', '编码器'], ['ffn'], '组合自注意力、残差连接、归一化和前馈网络。'),
  'masked-attention': topicNote('masked-attention', '掩码自注意力', 3, ['Transformer', '解码器'], ['multi-head'], '阻止解码位置看到未来 token，保证自回归生成。'),
  'cross-attention': topicNote('cross-attention', '编码器-解码器注意力', 3, ['Transformer', '解码器'], ['encoder-block', 'masked-attention'], '让解码器读取编码器输出并融合输入语义。'),
  'output-softmax': topicNote('output-softmax', '线性层与 Softmax', 3, ['Transformer', '输出层'], ['cross-attention'], '把隐藏状态映射为词表概率分布并选择输出 token。'),
}

const databaseNotes: Record<string, NoteItem> = {
  'db-model': topicNote('db-model', '关系模型与范式', 0, ['数据库', '数据模型'], [], '理解表、主键、外键以及规范化设计。'),
  'db-sql': topicNote('db-sql', 'SQL 查询基础', 1, ['数据库', 'SQL'], ['db-model'], '掌握筛选、连接、聚合和子查询。'),
  'sql-opt': { ...legacyNotes.value['sql-opt'], stage: 2, prerequisites: ['db-sql'] },
  'mysql-idx': { ...legacyNotes.value['mysql-idx'], stage: 2, prerequisites: ['sql-opt'] },
  'db-transaction': topicNote('db-transaction', '事务、锁与隔离级别', 3, ['数据库', '事务'], ['mysql-idx'], '理解 ACID、并发异常以及隔离级别的取舍。'),
}

const cnnNotes: Record<string, NoteItem> = {
  'cnn-input': topicNote('cnn-input', '图像张量与感受野', 0, ['CNN', '输入'], [], '理解通道、空间尺寸以及局部感受野。'),
  'cnn-conv': topicNote('cnn-conv', '卷积核与特征图', 1, ['CNN', '卷积'], ['cnn-input'], '使用共享卷积核提取局部模式。'),
  'cnn-pooling': topicNote('cnn-pooling', '池化与下采样', 1, ['CNN', '池化'], ['cnn-conv'], '降低空间分辨率并增强局部不变性。'),
  'cnn-arch': { ...legacyNotes.value['cnn-arch'], stage: 2, prerequisites: ['cnn-pooling'] },
  'cnn-training': topicNote('cnn-training', '训练、正则化与数据增强', 3, ['CNN', '训练'], ['cnn-arch'], '通过优化、正则化和增强改善泛化能力。'),
}

const machineLearningNotes: Record<string, NoteItem> = {
  'ml-linear-algebra': topicNote('ml-linear-algebra', '线性代数基础', 0, ['机器学习', '数学'], [], '掌握向量、矩阵、线性映射与特征分解。'),
  'lin-reg': { ...legacyNotes.value['lin-reg'], stage: 1, prerequisites: ['ml-linear-algebra'] },
  'ml-neuron': topicNote('ml-neuron', '神经元与激活函数', 2, ['神经网络', '基础'], ['lin-reg'], '从线性组合与非线性激活理解神经元。'),
  'ml-backprop': topicNote('ml-backprop', '反向传播', 2, ['神经网络', '训练'], ['ml-neuron'], '使用链式法则计算梯度并更新网络参数。'),
  'ml-evaluation': topicNote('ml-evaluation', '损失函数与模型评估', 3, ['机器学习', '评估'], ['ml-backprop'], '选择目标函数和评估指标，识别过拟合与欠拟合。'),
}

const notebookNotes = ref<Record<NotebookId, Record<string, NoteItem>>>({
  transformer: transformerNotes,
  database: databaseNotes,
  cnn: cnnNotes,
  'machine-learning': machineLearningNotes,
})

const activeNotebook = computed(() => notebooks.find(notebook => notebook.path.toLowerCase() === route.path.toLowerCase()) ?? notebooks[0])
const allNotes = computed(() => notebookNotes.value[activeNotebook.value.id])
const heroTitle = computed(() => activeNotebook.value.title.replace(/学习笔记$|笔记$/, '可视化学习地图'))

// ---- Graph States ----
const nodes = ref<Node[]>([])
const links = ref<Link[]>([])

const expandedTags = ref<Set<string>>(new Set())
const selectedNodeId = ref<string | null>(null)
const hoveredNodeId = ref<string | null>(null)
const hoveredKnowledgeNodeId = ref<string | null>(null)

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
const width = ref(960)
const height = ref(520)

// Physics loops
const isSimulating = ref(false)
let animationFrameId: number | null = null

// ---- Reader Drawer ----
const activeNoteId = ref<string | null>(null)
const isDrawerOpen = ref(false)
const isEditing = ref(false)
const editTitle = ref('')
const editContent = ref('')
const editTagsString = ref('')
const editStage = ref(0)

function distributeY(index: number, total: number, top = 74, bottom = height.value - 42) {
  if (total <= 1) return (top + bottom) / 2
  return top + (bottom - top) * (index / (total - 1))
}

function layoutGraph() {
  const centerNode = nodes.value.find(node => node.type === 'center')
  if (centerNode) {
    centerNode.x = 138
    centerNode.y = height.value / 2
    centerNode.fx = centerNode.x
    centerNode.fy = centerNode.y
  }

  const tagNodes = nodes.value.filter(node => node.type === 'tag')
  tagNodes.forEach((node, index) => {
    node.x = 448
    node.y = distributeY(index, tagNodes.length, 78, height.value - 48)
    node.fx = null
    node.fy = null
  })

  const tagOrder = new Map(tagNodes.map((node, index) => [node.id, index]))
  const noteNodes = nodes.value
    .filter(node => node.type === 'note')
    .sort((a, b) => {
      const parentDelta = (tagOrder.get(a.parentId ?? '') ?? 0) - (tagOrder.get(b.parentId ?? '') ?? 0)
      return parentDelta || a.label.localeCompare(b.label, 'zh-CN')
    })

  noteNodes.forEach((node, index) => {
    node.x = 766
    node.y = distributeY(index, noteNodes.length, 62, height.value - 34)
    node.fx = null
    node.fy = null
  })
}

function initGraph() {
  const tags = [...new Set(Object.values(allNotes.value).flatMap(note => note.tags))]

  nodes.value = [{
    id: 'center', label: '全部文档', type: 'center', x: 0, y: 0,
    vx: 0, vy: 0, fx: null, fy: null, notesCount: Object.keys(allNotes.value).length,
    color: '#858bff',
  }]
  links.value = []
  expandedTags.value.clear()

  tags.forEach((tag, index) => {
    const tagId = `tag:${tag}`
    const noteItems = Object.values(allNotes.value).filter(note => note.tags.includes(tag))
    nodes.value.push({
      id: tagId, label: tag, type: 'tag', x: 0, y: 0, vx: 0, vy: 0, fx: null, fy: null,
      notesCount: noteItems.length, color: '#7f8ca0', idealAngle: index,
    })
    links.value.push({ source: 'center', target: tagId })
    expandedTags.value.add(tagId)

    noteItems.forEach(note => {
      nodes.value.push({
        id: note.id, label: note.title, type: 'note',
        x: 0, y: 0,
        vx: 0, vy: 0, fx: null, fy: null, notesCount: 0, noteId: note.id,
        color: '#69778d', parentId: tagId,
      })
      links.value.push({ source: tagId, target: note.id })
    })
  })

  layoutGraph()
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

void updatePhysics

function resumeSimulation() {
  isSimulating.value = false
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
  if (node.type === 'center') return
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
  } else if (node.type === 'tag') {
    // Click tag node
    if (node.notesCount === 1) {
      // Small content: directly open the single note
      const singleNote = nodes.value.find(n => n.type === 'note' && n.parentId === node.id)
      if (singleNote?.noteId) openNote(singleNote.noteId)
    } else {
      // Dynamic leaf node expansion/collapsing
      toggleTagExpansion(node)
    }
  }
}

function toggleTagExpansion(tagNode: Node) {
  const tagId = tagNode.id
  if (expandedTags.value.has(tagId)) {
    expandedTags.value.delete(tagId)
    const childIds = new Set(nodes.value.filter(node => node.parentId === tagId).map(node => node.id))
    nodes.value = nodes.value.filter(node => !childIds.has(node.id))
    links.value = links.value.filter(link => !childIds.has(link.target))
  } else {
    expandedTags.value.add(tagId)
    const noteItems = Object.values(allNotes.value).filter(note => note.tags.includes(tagNode.label))
    noteItems.forEach(note => {
      nodes.value.push({
        id: note.id, label: note.title, type: 'note',
        x: tagNode.x, y: tagNode.y,
        vx: 0, vy: 0, fx: null, fy: null, notesCount: 0, noteId: note.id,
        color: '#69778d', parentId: tagId,
      })
      links.value.push({ source: tagId, target: note.id })
    })
  }
  layoutGraph()
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

function linkPath(link: Link) {
  const source = nodes.value.find(node => node.id === link.source)
  const target = nodes.value.find(node => node.id === link.target)
  if (!source || !target) return ''
  const midpointX = (source.x + target.x) / 2
  const midpointY = (source.y + target.y) / 2
  const bend = link.source === 'center' ? 0 : 16
  return `M ${source.x} ${source.y} Q ${midpointX - bend} ${midpointY - bend} ${target.x} ${target.y}`
}

interface KnowledgeMapNode {
  id: string
  label: string
  tag: string
  x: number
  y: number
  role: 'overview' | 'previous' | 'current' | 'next'
}

interface KnowledgeMapRelation {
  source: string
  target: string
}

const learningRelations = computed<KnowledgeMapRelation[]>(() => {
  const notes = Object.values(allNotes.value)
  const noteIds = new Set(notes.map(note => note.id))
  return notes.flatMap(note => (note.prerequisites ?? [])
    .filter(prerequisiteId => noteIds.has(prerequisiteId))
    .map(prerequisiteId => ({ source: prerequisiteId, target: note.id })))
})

const overviewColumns = computed(() => activeNotebook.value.columns.map((label, index) => ({
  label,
  index,
  x: 120 + index * 240,
})))

const overviewKnowledgeNodes = computed<KnowledgeMapNode[]>(() => {
  const notes = Object.values(allNotes.value)
  return overviewColumns.value.flatMap(column => {
    const columnNotes = notes.filter(note => (note.stage ?? 0) === column.index)
    return columnNotes.map((note, index) => ({
      id: note.id,
      label: note.title,
      tag: column.label,
      x: column.x,
      y: focusY(index, columnNotes.length),
      role: 'overview' as const,
    }))
  })
})

function focusY(index: number, total: number) {
  if (total <= 1) return 260
  return 150 + (220 * index) / (total - 1)
}

const selectedIncoming = computed(() => selectedNodeId.value
  ? learningRelations.value.filter(relation => relation.target === selectedNodeId.value)
  : [])
const selectedOutgoing = computed(() => selectedNodeId.value
  ? learningRelations.value.filter(relation => relation.source === selectedNodeId.value)
  : [])

const focusedKnowledgeNodes = computed<KnowledgeMapNode[]>(() => {
  const noteId = selectedNodeId.value
  const current = noteId ? allNotes.value[noteId] : null
  if (!current) return []

  const previousIds = [...new Set(selectedIncoming.value.map(relation => relation.source))]
  const nextIds = [...new Set(selectedOutgoing.value.map(relation => relation.target))]
  const previousNodes = previousIds.map((id, index) => ({
    id,
    label: allNotes.value[id]?.title ?? id,
    tag: allNotes.value[id]?.tags[0] ?? '未分类',
    x: 190,
    y: focusY(index, previousIds.length),
    role: 'previous' as const,
  }))
  const nextNodes = nextIds.map((id, index) => ({
    id,
    label: allNotes.value[id]?.title ?? id,
    tag: allNotes.value[id]?.tags[0] ?? '未分类',
    x: 770,
    y: focusY(index, nextIds.length),
    role: 'next' as const,
  }))

  return [
    ...previousNodes,
    { id: current.id, label: current.title, tag: current.tags[0] ?? '未分类', x: 480, y: 260, role: 'current' },
    ...nextNodes,
  ]
})

const visibleKnowledgeNodes = computed(() => selectedNodeId.value
  ? focusedKnowledgeNodes.value
  : overviewKnowledgeNodes.value)
const visibleKnowledgeRelations = computed(() => selectedNodeId.value
  ? [...selectedIncoming.value, ...selectedOutgoing.value]
  : learningRelations.value)

function knowledgeRoutePoints(relation: KnowledgeMapRelation) {
  const source = visibleKnowledgeNodes.value.find(node => node.id === relation.source)
  const target = visibleKnowledgeNodes.value.find(node => node.id === relation.target)
  if (!source || !target) return []

  const horizontalDistance = target.x - source.x
  if (Math.abs(horizontalDistance) < 1) {
    return [source, target]
  }

  const direction = horizontalDistance > 0 ? 1 : -1
  const sourceLane = source.x + direction * 48
  const targetLane = target.x - direction * 48

  // Adjacent columns can use the gap between them. Long edges use a top channel
  // so they never appear to terminate at a node in an intermediate column.
  if (Math.abs(horizontalDistance) <= 300) {
    const laneX = (source.x + target.x) / 2
    return [source, { x: laneX, y: source.y }, { x: laneX, y: target.y }, target]
  }

  const topChannelY = 76
  return [
    source,
    { x: sourceLane, y: source.y },
    { x: sourceLane, y: topChannelY },
    { x: targetLane, y: topChannelY },
    { x: targetLane, y: target.y },
    target,
  ]
}

function offsetRouteEndpoint(from: { x: number; y: number }, to: { x: number; y: number }, distance: number) {
  const dx = to.x - from.x
  const dy = to.y - from.y
  const length = Math.hypot(dx, dy) || 1
  return { x: from.x + (dx / length) * distance, y: from.y + (dy / length) * distance }
}

function knowledgeRoutePath(points: Array<{ x: number; y: number }>) {
  if (points.length < 2) return ''
  const routedPoints = points.map(point => ({ ...point }))
  routedPoints[0] = offsetRouteEndpoint(routedPoints[0], routedPoints[1], 12)
  routedPoints[routedPoints.length - 1] = offsetRouteEndpoint(
    routedPoints[routedPoints.length - 1],
    routedPoints[routedPoints.length - 2],
    16,
  )
  return routedPoints
    .map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`)
    .join(' ')
}

function knowledgeLinkPath(relation: KnowledgeMapRelation) {
  return knowledgeRoutePath(knowledgeRoutePoints(relation))
}

function relationLabelPosition(relation: KnowledgeMapRelation) {
  const points = knowledgeRoutePoints(relation)
  const source = points[0]
  const target = points[points.length - 1]
  if (!source || !target) return { x: 0, y: 0 }

  if (points.length > 4) {
    const channelStart = points[2]
    const channelEnd = points[3]
    return { x: (channelStart.x + channelEnd.x) / 2, y: channelStart.y - 10 }
  }

  if (Math.abs(source.x - target.x) < 1) {
    return { x: source.x + 18, y: (source.y + target.y) / 2 }
  }

  const lane = points[1]
  const laneTarget = points[2]
  return {
    x: lane.x,
    y: (lane.y + laneTarget.y) / 2 - 10,
  }
}

function isHoveredKnowledgeRelation(relation: KnowledgeMapRelation) {
  const nodeId = hoveredKnowledgeNodeId.value
  return Boolean(nodeId && (relation.source === nodeId || relation.target === nodeId))
}

function knowledgeRelationMarker(relation: KnowledgeMapRelation) {
  return isHoveredKnowledgeRelation(relation)
    ? 'url(#knowledge-arrow-active)'
    : 'url(#knowledge-arrow)'
}

function isRelatedKnowledgeNode(nodeId: string) {
  const hoveredId = hoveredKnowledgeNodeId.value
  if (!hoveredId || nodeId === hoveredId) return false
  return learningRelations.value.some(relation => (
    (relation.source === hoveredId && relation.target === nodeId) ||
    (relation.target === hoveredId && relation.source === nodeId)
  ))
}

// Query-filtered nodes list for highlight search
const searchedNodeIds = computed(() => {
  if (!searchQuery.value.trim()) return new Set<string>()
  const query = searchQuery.value.toLowerCase().trim()
  return new Set(Object.values(allNotes.value)
    .filter(note => note.title.toLowerCase().includes(query) || note.tags.some(tag => tag.toLowerCase().includes(query)))
    .map(note => note.id))
})

const noteCount = computed(() => Object.keys(allNotes.value).length)
const stageCount = computed(() => activeNotebook.value.columns.length)
const relationCount = computed(() => learningRelations.value.length)
const selectedNote = computed(() => selectedNodeId.value ? allNotes.value[selectedNodeId.value] ?? null : null)

const selectedSummary = computed(() => selectedNote.value?.content
  .replace(/^---[\s\S]*?---\s*/m, '')
  .replace(/^#+\s+.*$/m, '')
  .replace(/[\`#>*_\[\]]/g, '')
  .replace(/\s+/g, ' ')
  .trim()
  .slice(0, 118) || '打开笔记查看完整内容。')

function focusKnowledgeNode(noteId: string) {
  selectedNodeId.value = noteId
}

function clearKnowledgeFocus() {
  selectedNodeId.value = null
}

function scrollToKnowledgeMap() {
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  document.getElementById('knowledge-map')?.scrollIntoView({
    behavior: reduceMotion ? 'auto' : 'smooth',
    block: 'start',
  })
}

function switchNotebook(notebook: NotebookConfig) {
  if (notebook.id === activeNotebook.value.id) return
  void router.push(notebook.path)
}

watch(() => activeNotebook.value.id, () => {
  selectedNodeId.value = null
  activeNoteId.value = null
  isDrawerOpen.value = false
  isEditing.value = false
  searchQuery.value = ''
  document.title = `${activeNotebook.value.title} - KnowledgeMap`
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
    editStage.value = note.stage ?? 0
    isEditing.value = true
  }
}

function saveEdit() {
  const id = activeNoteId.value
  if (id && editTitle.value.trim() && editContent.value.trim()) {
    const newTags = editTagsString.value.split(',').map(t => t.trim()).filter(t => t.length > 0)
    const previousStage = allNotes.value[id].stage ?? 0
    
    // Update memory DB
    allNotes.value[id].title = editTitle.value
    allNotes.value[id].content = editContent.value
    allNotes.value[id].tags = newTags
    allNotes.value[id].stage = editStage.value
    if (previousStage !== editStage.value) {
      allNotes.value[id].prerequisites = editStage.value === 0
        ? []
        : Object.values(allNotes.value)
          .filter(note => note.id !== id && (note.stage ?? 0) === editStage.value - 1)
          .map(note => note.id)
    }

    isEditing.value = false
  }
}

function createNewNote() {
  const newId = 'note-' + Date.now()
  const stage = activeNotebook.value.columns.length - 1
  allNotes.value[newId] = {
    id: newId,
    title: '未命名笔记',
    tags: ['未分类'],
    content: '# 未命名笔记\n\n在此输入您的笔记正文...\n\n支持标准的 Markdown 渲染。',
    stage,
    prerequisites: Object.values(allNotes.value)
      .filter(note => (note.stage ?? 0) === stage - 1)
      .map(note => note.id),
  }
  openNote(newId)
  enterEdit()
}

// ---- Delete Note ----
function deleteNote(noteId: string) {
  if (confirm(`确认要删除《${allNotes.value[noteId].title}》吗？`)) {
    delete allNotes.value[noteId]
    
    isDrawerOpen.value = false
    activeNoteId.value = null
    isEditing.value = false
    if (selectedNodeId.value === noteId) selectedNodeId.value = null
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
  const stage = activeNotebook.value.columns.length - 1
  
  // Save to mock DB
  allNotes.value[newId] = {
    id: newId,
    title: title,
    tags: tags,
    content: fileContent,
    stage,
    prerequisites: Object.values(allNotes.value)
      .filter(note => (note.stage ?? 0) === stage - 1)
      .map(note => note.id),
  }

  openNote(newId)
}

// ---- Lifecycles ----
onMounted(() => {
  document.documentElement.classList.remove('theme-light')
  document.title = `${activeNotebook.value.title} - KnowledgeMap`
})

onUnmounted(() => {
  if (animationFrameId) cancelAnimationFrame(animationFrameId)
  document.title = 'Dashboard - KnowledgeMap'
})
</script>

<template>
  <div class="notes-workspace" @dragover.prevent="isDragOver = true">
    <header class="learning-hero">
      <button class="learning-brand" type="button" aria-label="返回仪表盘" @click="router.push('/')">
        <span class="learning-brand__mark" aria-hidden="true"><i></i><i></i><i></i><i></i></span>
        <span>LEARNING MAP</span>
      </button>
      <div class="learning-hero__eyebrow"><span aria-hidden="true"></span>交互式学习路径</div>
      <h1>{{ heroTitle }}</h1>
      <p>{{ activeNotebook.description }}</p>
      <div class="learning-hero__meta">
        <span><strong>{{ noteCount }}</strong> 个知识点</span>
        <span aria-hidden="true">/</span>
        <span><strong>{{ relationCount }}</strong> 条依赖关系</span>
      </div>
      <button class="learning-hero__start" type="button" @click="scrollToKnowledgeMap">
        <span class="learning-hero__start-icon" aria-hidden="true">&darr;</span>
        <span>开始学习</span>
      </button>
    </header>

    <!-- Top bar -->
    <header v-if="false" class="sticky top-0 z-20 bg-surface/80 backdrop-blur-md border-b border-border px-6 py-4 flex items-center gap-4">
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
        <button @click="createNewNote"
          class="flex items-center gap-2 px-4 py-1.5 rounded-lg bg-primary text-white text-sm font-medium hover:bg-primary-dark transition-colors duration-200 active:scale-[0.97]">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          写笔记
        </button>
      </div>
    </header>

    <div v-if="false" class="flex-1 flex flex-col md:flex-row relative">
      <!-- Left Panel: Interactive Graph -->
      <div 
        class="relative z-10 flex-1 cursor-grab bg-transparent select-none"
        :class="{ 'cursor-grabbing': isPanning }"
        @mousedown="handleCanvasMouseDown"
        @mousemove="handleCanvasMouseMove"
        @wheel="handleWheel"
      >
        <div class="absolute top-4 left-6 z-10 bg-surface-card/65 backdrop-blur-sm border border-border px-4 py-3 rounded-2xl max-w-sm pointer-events-none">
          <h2 class="text-xs font-bold text-text mb-1 tracking-wide">星云知识图谱</h2>
          <p class="text-[10px] text-text-muted leading-relaxed">
            标签星团代表知识分类，笔记仅在聚焦时显示标题。<br />
            点击星团可展开或收起，滚轮缩放并可拖动外围节点。<br />
            支持将本地 Markdown 文件拖入画布。
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
          :viewBox="`0 0 ${width} ${height}`"
          preserveAspectRatio="xMidYMid meet"
          @mouseup="handleGlobalMouseUp"
          @mouseleave="handleGlobalMouseUp"
        >
          <!-- Camera transforms -->
          <g :transform="`translate(${panX}, ${panY}) scale(${zoom})`">
            <path
              v-for="link in links" 
              :key="`${link.source}-${link.target}`"
              :d="linkPath(link)"
              fill="none"
              class="graph-link"
              :stroke="
                connectedNodesAndLinks.links.has(`${link.source}-${link.target}`) || 
                connectedNodesAndLinks.links.has(`${link.target}-${link.source}`)
                  ? 'var(--color-primary)' 
                  : 'rgba(148,163,184,0.2)'
              "
              :stroke-width="
                connectedNodesAndLinks.links.has(`${link.source}-${link.target}`) || 
                connectedNodesAndLinks.links.has(`${link.target}-${link.source}`)
                  ? 2 
                  : 1.2
              "
            />

            <path
              v-for="link in links.filter(l => connectedNodesAndLinks.links.has(`${l.source}-${l.target}`) || connectedNodesAndLinks.links.has(`${l.target}-${l.source}`))" 
              :key="`glow-${link.source}-${link.target}`"
              :d="linkPath(link)"
              fill="none"
              stroke="var(--color-primary)"
              stroke-width="5"
              opacity="0.22"
              style="filter: blur(2px);"
            />

            <!-- Graph nodes -->
            <g 
              v-for="node in nodes" 
              :key="node.id"
              :transform="`translate(${node.x}, ${node.y})`"
              class="graph-node cursor-pointer group"
              :class="`graph-node-${node.type}`"
              @mousedown="startDrag($event, node)"
              @click.stop="handleNodeClick(node)"
              @mouseenter="hoveredNodeId = node.id"
              @mouseleave="hoveredNodeId = null"
            >
              <!-- Invisible larger hit area for hover and drag stability -->
              <circle 
                :r="node.type === 'center' ? 42 : node.type === 'tag' ? 31 : 22"
                fill="transparent" 
              />

              <circle
                v-if="hoveredNodeId === node.id || selectedNodeId === node.id"
                :r="node.type === 'center' ? 39 : node.type === 'tag' ? 29 : 19"
                fill="none"
                stroke="var(--color-primary-light)"
                stroke-width="1.2"
                opacity="0.7"
              />

              <!-- Outer glowing ring on active/hovered/searched -->
              <circle 
                :r="node.type === 'center' ? 44 : node.type === 'tag' ? 33 : 23"
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
                :r="node.type === 'center' ? 28 : node.type === 'tag' ? 19 : 9"
                :fill="node.type === 'note' ? 'var(--color-surface-card)' : node.color"
                :stroke="node.type === 'note' ? 'var(--color-border)' : 'transparent'"
                stroke-width="1.8"
                class="transition-all duration-350 shadow-md group-hover:scale-110"
                :class="[
                  selectedNodeId === node.id ? 'stroke-primary stroke-2' : '',
                  searchedNodeIds.has(node.id) ? 'pulse-searched' : ''
                ]"
              />

              <!-- Nodes text label -->
              <text 
                v-if="node.type !== 'note' || hoveredNodeId === node.id || selectedNodeId === node.id || searchedNodeIds.has(node.id)"
                :y="node.type === 'center' ? 48 : node.type === 'tag' ? 38 : 25"
                text-anchor="middle"
                class="text-[10px] pointer-events-none select-none transition-all duration-300"
                :fill="selectedNodeId === node.id || hoveredNodeId === node.id || searchedNodeIds.has(node.id) ? '#f8fafc' : '#aebbd0'"
                :class="selectedNodeId === node.id || hoveredNodeId === node.id || searchedNodeIds.has(node.id) ? 'font-bold text-xs' : ''"
              >
                {{ node.label }}
                <tspan v-if="node.type === 'tag' && node.notesCount > 0" class="opacity-60 text-[9px]">
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

    <header class="notes-header">
      <div class="notes-brand">
        <button class="back-button" type="button" aria-label="返回仪表盘" @click="router.push('/')">&larr;</button>
        <div>
          <p>{{ activeNotebook.eyebrow }}</p>
          <h1>{{ activeNotebook.title }}</h1>
        </div>
      </div>
      <nav class="notebook-switcher" aria-label="专题笔记">
        <button v-for="notebook in notebooks" :key="notebook.id" type="button" :class="{ 'is-active': notebook.id === activeNotebook.id }" @click="switchNotebook(notebook)">{{ notebook.tabLabel }}</button>
      </nav>
      <div class="notes-header__actions">
        <label class="search-control"><span>搜索</span><input v-model="searchQuery" type="search" placeholder="知识点或标签" /><button v-if="searchQuery" type="button" aria-label="清空搜索" @click="searchQuery = ''">x</button></label>
        <button class="create-button" type="button" @click="createNewNote">新建笔记</button>
      </div>
    </header>

    <main id="knowledge-map" class="notes-main">
      <section class="graph-workspace" :aria-label="`${activeNotebook.title}知识图谱`">
        <div class="graph-toolbar">
          <div>
            <span class="live-indicator" aria-hidden="true"></span>
            <strong>{{ selectedNote ? '聚焦关系视图' : '完整知识图谱' }}</strong>
            <span class="toolbar-divider"></span>
            <span class="toolbar-hint">{{ selectedNote ? '仅显示当前知识点的直接前置与后续。' : '移动到圆点上查看知识点，点击圆点探索它与其他知识的关系。' }}</span>
          </div>
          <button v-if="selectedNote" class="continue-button" type="button" @click="clearKnowledgeFocus">返回整体图谱</button>
        </div>

        <div class="graph-body" :class="{ 'is-focused': selectedNote }">
          <div class="graph-canvas">
            <div v-if="selectedNote" class="focus-columns" aria-hidden="true"><span>前置</span><span>当前</span><span>后续</span></div>
            <div v-else class="knowledge-columns" aria-label="知识阶段">
              <span v-for="column in activeNotebook.columns" :key="column">{{ column }}</span>
            </div>
            <svg class="notes-graph-svg" viewBox="0 0 960 520" preserveAspectRatio="xMidYMid meet" role="img" aria-label="基础知识节点关系图">
              <defs>
                <marker id="knowledge-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto" markerUnits="strokeWidth">
                  <path d="M 0 0 L 8 4 L 0 8 z" />
                </marker>
                <marker id="knowledge-arrow-active" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto" markerUnits="strokeWidth">
                  <path d="M 0 0 L 8 4 L 0 8 z" />
                </marker>
              </defs>
              <g class="knowledge-relations">
                <g v-for="relation in visibleKnowledgeRelations" :key="`${relation.source}-${relation.target}`" class="knowledge-relation" :class="{ 'is-related': isHoveredKnowledgeRelation(relation), 'is-dimmed': hoveredKnowledgeNodeId && !isHoveredKnowledgeRelation(relation) }">
                  <path class="knowledge-relation__hit" :d="knowledgeLinkPath(relation)" />
                  <path class="knowledge-relation__line" :d="knowledgeLinkPath(relation)" :marker-end="knowledgeRelationMarker(relation)" />
                  <text class="knowledge-relation__label" :x="relationLabelPosition(relation).x" :y="relationLabelPosition(relation).y" text-anchor="middle">依赖</text>
                </g>
              </g>

              <text v-if="selectedNote && selectedIncoming.length === 0" class="empty-relation" x="190" y="266" text-anchor="middle">暂无直接前置</text>
              <text v-if="selectedNote && selectedOutgoing.length === 0" class="empty-relation" x="770" y="266" text-anchor="middle">暂无直接后续</text>

              <g v-for="node in visibleKnowledgeNodes" :key="node.id" :transform="`translate(${node.x}, ${node.y})`" class="knowledge-node" :class="[`is-${node.role}`, { 'is-search-match': searchedNodeIds.has(node.id), 'is-hovered': hoveredKnowledgeNodeId === node.id, 'is-related': isRelatedKnowledgeNode(node.id), 'is-dimmed': hoveredKnowledgeNodeId && hoveredKnowledgeNodeId !== node.id && !isRelatedKnowledgeNode(node.id) }]" tabindex="0" role="button" :aria-label="`查看知识点 ${node.label}`" @mouseenter="hoveredKnowledgeNodeId = node.id" @mouseleave="hoveredKnowledgeNodeId = null" @focus="hoveredKnowledgeNodeId = node.id" @blur="hoveredKnowledgeNodeId = null" @click="focusKnowledgeNode(node.id)" @keydown.enter.prevent="focusKnowledgeNode(node.id)">
                <circle class="knowledge-node__hit" r="24" />
                <circle class="knowledge-node__ring" r="15" />
                <circle class="knowledge-node__dot" r="7" />
                <text y="29" text-anchor="middle" class="knowledge-node__label">{{ node.label }}</text>
              </g>
            </svg>

            <div class="drop-zone" :class="{ 'is-active': isDragOver }" @dragover.prevent="isDragOver = true" @dragleave.prevent="isDragOver = false" @drop="handleFileDrop"><div><strong>导入 Markdown</strong><span>松开后加入当前知识路径</span></div></div>
          </div>

          <aside v-if="selectedNote" class="focus-inspector" aria-live="polite">
            <span class="node-kind">基础知识节点</span>
            <h2>{{ selectedNote.title }}</h2>
            <p>{{ selectedSummary }}</p>
            <div class="focus-metrics">
              <div><strong>{{ selectedIncoming.length }}</strong><span>直接前置</span></div>
              <div><strong>{{ selectedOutgoing.length }}</strong><span>直接后续</span></div>
            </div>
            <div class="inspector-tags"><span v-for="tag in selectedNote.tags" :key="tag">{{ tag }}</span></div>
            <button class="inspector-action" type="button" @click="openNote(selectedNote.id)">打开笔记</button>
          </aside>
        </div>

        <footer class="graph-footer">
          <div class="graph-legend"><strong>节点类型</strong><span><i class="legend-note"></i>基础知识节点</span><span><i class="legend-current"></i>当前节点</span></div>
          <div class="graph-summary"><span><b>{{ noteCount }}</b> 个知识点</span><span><b>{{ stageCount }}</b> 个阶段</span><span><b>{{ relationCount }}</b> 个依赖关系</span></div>
        </footer>
      </section>
    </main>

    <section v-if="isDrawerOpen" class="note-reader" role="dialog" aria-modal="true" aria-label="完整笔记阅读器">
      <header class="reader-header">
        <div class="reader-heading">
          <button class="back-button" type="button" aria-label="返回知识图谱" @click="closeDrawer">&larr;</button>
          <div><span>基础知识节点</span><strong>{{ allNotes[activeNoteId ?? '']?.title ?? '笔记阅读器' }}</strong></div>
        </div>
        <div class="reader-actions">
          <button v-if="!isEditing" type="button" @click="enterEdit">编辑</button>
          <button v-if="!isEditing" class="danger" type="button" @click="deleteNote(activeNoteId!)">删除</button>
          <button class="create-button" type="button" @click="closeDrawer">返回图谱</button>
        </div>
      </header>
      <main class="reader-main">
        <article v-if="!isEditing" class="reader-document markdown-body">
          <div class="drawer-tags"><span v-for="tag in allNotes[activeNoteId ?? '']?.tags" :key="tag">{{ tag }}</span></div>
          <div v-html="renderedMarkdown"></div>
        </article>
        <div v-else class="reader-editor note-editor">
          <label>笔记标题<input v-model="editTitle" type="text" /></label>
          <label>标签，用英文逗号分隔<input v-model="editTagsString" type="text" /></label>
          <label>
            所属列
            <select v-model.number="editStage">
              <option v-for="(column, index) in activeNotebook.columns" :key="column" :value="index">{{ column }}</option>
            </select>
          </label>
          <label class="editor-body">笔记正文，支持 Markdown<textarea v-model="editContent"></textarea></label>
          <div class="editor-actions"><button type="button" @click="isEditing = false">取消</button><button class="create-button" type="button" @click="saveEdit">保存笔记</button></div>
        </div>
      </main>
    </section>
  </div>
</template>

<style scoped>
.notes-graph-svg {
  background:
    radial-gradient(circle at 50% 48%, rgba(79, 70, 229, 0.14), transparent 20rem),
    rgba(7, 8, 22, 0.3);
  transition: background-color 0.3s ease;
}

circle {
  transition: transform 0.3s cubic-bezier(0.2, 0.8, 0.2, 1), stroke-width 0.2s ease, fill 0.3s ease, stroke 0.3s ease;
}

.graph-link {
  transition: stroke 0.28s ease, stroke-width 0.28s ease;
}

.graph-node {
  transform-box: fill-box;
  transform-origin: center;
}

.graph-node-tag circle,
.graph-node-center circle {
  filter: drop-shadow(0 6px 12px rgba(34, 184, 207, 0.16));
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

.notes-workspace {
  min-height: 100dvh;
  color: var(--text);
  overflow: hidden;
}

.notes-header,
.notes-main,
.note-drawer {
  position: relative;
  z-index: 1;
}

.notes-header {
  min-height: 72px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 12px 24px;
  border-bottom: 1px solid rgb(184 201 222 / 0.15);
  background: rgb(10 15 28 / 0.76);
  backdrop-filter: blur(18px);
}

.notes-brand,
.notes-header__actions,
.graph-toolbar,
.graph-toolbar > div,
.drawer-header,
.drawer-actions,
.editor-actions {
  display: flex;
  align-items: center;
}

.notes-brand { gap: 13px; min-width: 0; }
.notes-brand p,
.eyebrow {
  margin: 0 0 3px;
  color: #8ccdf4;
  font-size: 10px;
  font-weight: 750;
  letter-spacing: .12em;
  text-transform: uppercase;
}
.notes-brand h1 { margin: 0; color: #f5f8ff; font-size: 15px; font-weight: 720; letter-spacing: 0; }

.back-button,
.toolbar-icon {
  display: grid;
  width: 32px;
  height: 32px;
  place-items: center;
  border: 1px solid rgb(184 201 222 / 0.22);
  border-radius: 7px;
  color: #b9c5d8;
  background: rgb(255 255 255 / 0.035);
  cursor: pointer;
  transition: border-color .2s ease, color .2s ease, background .2s ease, transform .15s ease;
}
.back-button:hover,
.toolbar-icon:hover { border-color: #8ccdf4; color: #f5f8ff; background: rgb(140 205 244 / 0.1); }
.back-button:active,
.toolbar-icon:active { transform: scale(.96); }

.notes-header__actions { gap: 10px; }
.search-control {
  display: grid;
  grid-template-columns: auto minmax(140px, 190px) auto;
  align-items: center;
  gap: 8px;
  min-height: 34px;
  padding: 0 9px;
  border: 1px solid rgb(184 201 222 / 0.2);
  border-radius: 7px;
  color: #8492a8;
  background: rgb(2 8 18 / 0.34);
}
.search-control span { font-size: 11px; }
.search-control input { min-width: 0; border: 0; outline: 0; color: #eef5ff; background: transparent; font: inherit; font-size: 12px; }
.search-control input::placeholder { color: #6d7d94; }
.search-control button { padding: 0; border: 0; color: #8e9db4; background: transparent; cursor: pointer; }

.create-button,
.inspector-action {
  min-height: 34px;
  padding: 0 13px;
  border: 1px solid #79c1eb;
  border-radius: 7px;
  color: #06101b;
  background: #9dd7f7;
  box-shadow: 0 8px 24px rgb(103 190 240 / 0.16);
  cursor: pointer;
  font-size: 12px;
  font-weight: 750;
  transition: background .2s ease, transform .15s ease;
}
.create-button:hover,
.inspector-action:hover { background: #c0e8ff; }
.create-button:active,
.inspector-action:active { transform: translateY(1px) scale(.98); }

.notes-main {
  display: grid;
  grid-template-columns: minmax(228px, 270px) minmax(0, 1fr);
  min-height: calc(100dvh - 72px);
}

.inspector-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 23px 20px 18px;
  border-right: 1px solid rgb(184 201 222 / 0.13);
  background: rgb(8 13 25 / 0.56);
  backdrop-filter: blur(14px);
}
.inspector-panel__header { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
.node-kind { color: #8190a7; font-size: 11px; }
.inspector-panel h2 { margin: 15px 0 7px; color: #f4f8ff; font-size: 19px; line-height: 1.25; letter-spacing: 0; }
.inspector-copy { min-height: 68px; margin: 0; color: #9ba9bd; font-size: 12px; line-height: 1.75; }
.node-glyph,
.inspector-empty-mark { width: 30px; height: 30px; margin-top: 30px; border-radius: 50%; }
.node-glyph--center { background: #7ec9f1; box-shadow: 0 0 0 7px rgb(126 201 241 / 0.12); }
.node-glyph--tag { background: #27b8cf; box-shadow: 0 0 0 7px rgb(39 184 207 / 0.1); }
.node-glyph--note { border: 2px solid #9ba9bd; background: #172334; box-shadow: 0 0 0 7px rgb(155 169 189 / 0.08); }
.inspector-empty-mark { position: relative; border: 1px solid #71839d; }
.inspector-empty-mark::after { position: absolute; inset: 8px; border: 1px solid #71839d; border-radius: inherit; content: ''; }

.inspector-metrics,
.workspace-metrics { display: grid; gap: 1px; margin-top: 20px; background: rgb(184 201 222 / 0.12); }
.inspector-metrics { grid-template-columns: 1fr 1fr; }
.inspector-metrics div,
.workspace-metrics div { display: grid; gap: 4px; padding: 10px; background: rgb(14 22 38 / 0.75); }
.inspector-metrics span,
.workspace-metrics span { color: #8998ae; font-size: 10px; }
.inspector-metrics strong { color: #e8f3ff; font-size: 13px; }
.inspector-tags,
.drawer-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 16px; }
.inspector-tags span,
.drawer-tags span { padding: 3px 7px; border: 1px solid rgb(140 205 244 / 0.24); border-radius: 4px; color: #9fdcff; background: rgb(140 205 244 / 0.08); font-size: 10px; }
.inspector-action { width: 100%; margin-top: 17px; }
.workspace-metrics { grid-template-columns: repeat(3, 1fr); margin-top: auto; }
.workspace-metrics div { padding: 10px 6px; text-align: center; }
.workspace-metrics strong { color: #f1f6ff; font-size: 18px; line-height: 1; }

.graph-workspace { display: flex; min-width: 0; flex-direction: column; padding: 18px 20px 20px; }
.graph-toolbar { min-height: 43px; justify-content: space-between; gap: 12px; padding: 0 12px; border: 1px solid rgb(184 201 222 / 0.14); border-bottom: 0; border-radius: 7px 7px 0 0; color: #a7b4c6; background: rgb(16 25 42 / 0.6); font-size: 11px; }
.graph-toolbar > div { gap: 8px; min-width: 0; }
.graph-toolbar strong { color: #e9f3ff; font-size: 12px; }
.live-indicator { width: 7px; height: 7px; border-radius: 50%; background: #58cba5; box-shadow: 0 0 0 3px rgb(88 203 165 / 0.12); }
.toolbar-divider { width: 1px; height: 14px; margin: 0 3px; background: rgb(184 201 222 / 0.22); }
.toolbar-hint { overflow: hidden; color: #8291a6; text-overflow: ellipsis; white-space: nowrap; }
.graph-legend { flex: 0 0 auto; }
.graph-legend span { display: flex; align-items: center; gap: 5px; color: #8f9eb2; }
.graph-legend i { width: 7px; height: 7px; border-radius: 50%; }
.legend-root { background: #7ec9f1; }.legend-tag { background: #27b8cf; }.legend-note { border: 1px solid #94a3b8; background: #172334; }

.graph-canvas { position: relative; flex: 1; min-height: 520px; overflow: hidden; border: 1px solid rgb(184 201 222 / 0.14); border-radius: 0 0 7px 7px; cursor: default; background: rgb(7 12 23 / 0.5); }
.notes-graph-svg { display: block; width: 100%; height: 100%; min-height: 520px; background: radial-gradient(circle at 50% 48%, rgb(79 139 229 / 0.15), transparent 20rem), linear-gradient(90deg, transparent 33.2%, rgb(185 206 234 / 0.04) 33.3%, transparent 33.4%, transparent 66.5%, rgb(185 206 234 / 0.04) 66.6%, transparent 66.7%); }
.canvas-labels { position: absolute; inset: 13px 26px auto; display: grid; grid-template-columns: repeat(3, 1fr); z-index: 1; color: rgb(166 185 207 / 0.38); font-size: 10px; letter-spacing: .08em; pointer-events: none; }.canvas-labels span:nth-child(2) { text-align: center; }.canvas-labels span:last-child { text-align: right; }
.reset-view { position: absolute; z-index: 2; right: 17px; bottom: 16px; padding: 7px 10px; border: 1px solid rgb(184 201 222 / 0.22); border-radius: 6px; color: #c0ccdc; background: rgb(9 15 28 / 0.84); cursor: pointer; font-size: 11px; }
.graph-node { cursor: pointer; }.graph-node circle { transition: r .2s ease, stroke .2s ease, fill .2s ease, opacity .2s ease; }.graph-node-tag circle,.graph-node-center circle { filter: none; }.node-hit { pointer-events: all; }.node-halo { stroke-width: 6px; }.node-ring { fill: none; stroke-width: 1.5px; }.node-dot { filter: drop-shadow(0 2px 4px rgb(4 10 22 / 0.35)); }.graph-node:hover .node-dot { filter: drop-shadow(0 4px 8px rgb(4 10 22 / 0.48)); }.graph-node text { font-family: inherit; font-size: 10px; font-weight: 700; pointer-events: none; user-select: none; }.graph-node text.is-emphasized { font-size: 12px; font-weight: 800; }.node-count { opacity: .58; font-size: 9px; }
.drop-zone { position: absolute; inset: 0; z-index: 3; display: grid; place-items: center; opacity: 0; pointer-events: none; transition: opacity .2s ease; }.drop-zone.is-active { opacity: 1; pointer-events: auto; background: rgb(96 188 237 / 0.1); }.drop-zone div { display: grid; gap: 7px; padding: 24px 30px; border: 1px dashed #9dd7f7; border-radius: 7px; color: #f1f6ff; background: rgb(8 16 30 / 0.88); text-align: center; }.drop-zone span { color: #a9b9ce; font-size: 12px; }

.note-drawer { position: fixed; inset: 0 0 0 auto; z-index: 10; display: flex; width: min(560px, 100%); flex-direction: column; transform: translateX(100%); border-left: 1px solid rgb(184 201 222 / 0.2); background: #111a2b; box-shadow: -20px 0 70px rgb(0 0 0 / 0.32); transition: transform .38s cubic-bezier(.16, 1, .3, 1); }.note-drawer.is-open { transform: translateX(0); }
.drawer-header { justify-content: space-between; gap: 16px; padding: 18px 22px; border-bottom: 1px solid rgb(184 201 222 / 0.14); }.drawer-header > div:first-child { min-width: 0; }.drawer-header .eyebrow { display: block; }.drawer-header strong { display: block; overflow: hidden; color: #eef6ff; font-size: 14px; text-overflow: ellipsis; white-space: nowrap; }.drawer-actions { flex: 0 0 auto; gap: 7px; }.drawer-actions > button:not(.toolbar-icon),.editor-actions > button:not(.create-button) { min-height: 30px; padding: 0 8px; border: 1px solid transparent; border-radius: 5px; color: #aebcd0; background: transparent; cursor: pointer; font-size: 11px; }.drawer-actions > button:not(.toolbar-icon):hover { border-color: rgb(184 201 222 / 0.2); color: #f3f7ff; }.drawer-actions .danger:hover { border-color: rgb(251 113 133 / 0.35); color: #fda4af; }
.drawer-content { flex: 1; overflow-y: auto; padding: 28px 30px 48px; }.drawer-tags { margin: 0 0 22px; }.markdown-body :deep(h1) { margin: 0 0 18px; color: #f4f8ff; font-size: 27px; }.markdown-body :deep(h2) { margin-top: 30px; color: #edf5ff; }.markdown-body :deep(h3) { color: #e3edf9; }.markdown-body :deep(p),.markdown-body :deep(li) { color: #aebbd0; }.markdown-body :deep(pre) { border-color: rgb(184 201 222 / 0.16); border-radius: 6px; background: #0b1220; }.markdown-body :deep(code) { color: #b8e6ff; background: rgb(140 205 244 / 0.08); }
.note-editor { display: flex; min-height: 100%; flex-direction: column; gap: 17px; }.note-editor label { display: grid; gap: 7px; color: #aebbd0; font-size: 11px; }.note-editor input,.note-editor select,.note-editor textarea { width: 100%; border: 1px solid rgb(184 201 222 / 0.18); border-radius: 6px; outline: 0; color: #edf4ff; background: #0c1524; font: inherit; }.note-editor input,.note-editor select { min-height: 38px; padding: 0 10px; font-size: 13px; }.note-editor select { color-scheme: dark; cursor: pointer; }.note-editor input:focus,.note-editor select:focus,.note-editor textarea:focus { border-color: #737bd2; box-shadow: 0 0 0 2px rgb(133 139 255 / 0.12); }.editor-body { flex: 1; }.note-editor textarea { height: 100%; min-height: 310px; padding: 12px; resize: vertical; font-family: ui-monospace, monospace; font-size: 12px; line-height: 1.65; }.editor-actions { justify-content: flex-end; gap: 9px; }.editor-actions .create-button { min-height: 32px; }

.notes-workspace {
  --map-accent: #858bff;
  display: flex;
  height: 100dvh;
  min-height: 100dvh;
  flex-direction: column;
  overflow: hidden;
  background: #0c131f;
}

.notes-header {
  min-height: 64px;
  padding: 10px 26px;
  border-color: #253145;
  background: #0f1724;
  backdrop-filter: none;
}

.notes-brand p,
.eyebrow { color: #969cff; }
.notes-brand h1 { color: #eef2f9; }
.back-button,
.toolbar-icon { border-color: #303c50; background: #141e2d; }
.back-button:hover,
.toolbar-icon:hover { border-color: #69729e; background: #1a2437; }
.search-control { border-color: #2c384b; background: #0b121e; }
.create-button,
.inspector-action { border-color: #7279db; color: #f7f8ff; background: #555dc0; box-shadow: none; }
.create-button:hover,
.inspector-action:hover { background: #646dcc; }

.notes-main {
  position: relative;
  display: block;
  height: calc(100dvh - 64px);
  min-height: 0;
  padding: 18px 26px 26px;
  box-sizing: border-box;
}

.graph-workspace { height: 100%; min-height: 0; padding: 0; }
.graph-toolbar {
  min-height: 56px;
  padding: 0 20px;
  border-color: #334056;
  border-radius: 8px 8px 0 0;
  color: #abb5c6;
  background: #182233;
}
.graph-toolbar strong { color: #d8deea; font-size: 13px; }
.toolbar-hint { color: #9ba6b9; }
.continue-button {
  min-height: 34px;
  padding: 0 14px;
  border: 1px solid #465375;
  border-radius: 7px;
  color: #aeb4ff;
  background: #242f4c;
  cursor: pointer;
  font-size: 12px;
  font-weight: 700;
}
.continue-button:active { transform: translateY(1px); }

.graph-canvas {
  min-height: 0;
  border-color: #334056;
  border-radius: 0;
  background: #111a29;
}
.notes-graph-svg {
  min-height: 0;
  padding-top: 56px;
  background-color: #111a29;
  background-image:
    linear-gradient(90deg, transparent 33.25%, rgb(133 149 176 / 0.17) 33.34%, transparent 33.43%, transparent 66.58%, rgb(133 149 176 / 0.17) 66.67%, transparent 66.76%),
    linear-gradient(rgb(130 146 172 / 0.065) 1px, transparent 1px),
    linear-gradient(90deg, rgb(130 146 172 / 0.065) 1px, transparent 1px);
  background-size: 100% 100%, 48px 48px, 48px 48px;
}
.canvas-labels {
  inset: 0 0 auto;
  height: 56px;
  align-items: center;
  padding: 0 28px;
  border-bottom: 1px solid #334056;
  color: #c4ccda;
  background: #151f2f;
  font-size: 11px;
  font-weight: 750;
  letter-spacing: 0;
}
.graph-link { stroke-linecap: round; }
.node-halo { stroke-width: 5px; }
.node-dot { stroke-width: 2px; filter: drop-shadow(0 2px 3px rgb(4 10 22 / 0.28)); }
.graph-node:hover .node-dot { filter: drop-shadow(0 4px 7px rgb(4 10 22 / 0.38)); }
.graph-node text { font-size: 10px; font-weight: 720; }
.graph-node text.is-emphasized { font-size: 11px; }
.legend-root { background: #858bff; }
.legend-tag { background: #7f8ca0; }
.legend-note { border: 0; background: #69778d; }

.graph-footer {
  display: flex;
  min-height: 62px;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 0 20px;
  border: 1px solid #334056;
  border-top: 0;
  border-radius: 0 0 8px 8px;
  color: #aab4c5;
  background: #151f2f;
  font-size: 12px;
}
.graph-legend,
.graph-summary { display: flex; align-items: center; gap: 18px; }
.graph-legend strong { color: #eef2f8; }
.graph-legend span { display: inline-flex; align-items: center; gap: 6px; }
.graph-summary span { color: #939fb2; }
.graph-summary b { color: #dce2ec; font-family: ui-monospace, monospace; }

.inspector-panel {
  position: absolute;
  right: 48px;
  bottom: 104px;
  z-index: 4;
  display: block;
  width: min(380px, calc(100% - 96px));
  min-height: 0;
  padding: 17px 18px;
  border: 1px solid #3a465b;
  border-radius: 8px;
  background: rgb(20 30 46 / 0.97);
  box-shadow: 0 18px 46px rgb(3 8 16 / 0.34);
  backdrop-filter: blur(12px);
}
.inspector-panel h2 { margin: 11px 0 6px; font-size: 17px; }
.inspector-copy { min-height: 0; line-height: 1.6; }
.node-glyph { display: none; }
.inspector-metrics { margin-top: 13px; }
.inspector-tags { margin-top: 12px; }
.inspector-action { margin-top: 14px; }
.workspace-metrics { display: none; }
.reset-view { bottom: 14px; border-color: #3b475b; background: #172131; }

@media (max-width: 800px) { .notes-workspace { height: auto; overflow: auto; }.notes-header { align-items: flex-start; flex-direction: column; gap: 12px; padding: 14px 16px; }.notes-header__actions { width: 100%; }.search-control { flex: 1; grid-template-columns: auto minmax(0, 1fr) auto; }.notes-main { height: auto; min-height: calc(100dvh - 116px); padding: 12px; }.graph-workspace { height: auto; min-height: 680px; }.graph-toolbar { padding: 0 12px; }.toolbar-hint,.continue-button { display: none; }.graph-canvas,.notes-graph-svg { min-height: 500px; }.canvas-labels { padding: 0 14px; }.graph-footer { align-items: flex-start; flex-direction: column; gap: 10px; padding: 14px; }.graph-summary { flex-wrap: wrap; gap: 10px 16px; }.inspector-panel { right: 24px; bottom: 132px; width: calc(100% - 48px); }.note-drawer { width: 100%; }.drawer-content { padding: 22px 18px 36px; } }

/* Transformer knowledge path */
.graph-body {
  display: grid;
  min-height: 0;
  flex: 1;
  grid-template-columns: minmax(0, 1fr);
}

.graph-body.is-focused {
  grid-template-columns: minmax(0, 3fr) minmax(300px, 1fr);
}

.graph-body .graph-canvas {
  min-height: 0;
  border-color: #334056;
  border-radius: 0;
  cursor: default;
}

.graph-body .notes-graph-svg {
  height: 100%;
  min-height: 0;
  padding: 0;
  background-color: #111a29;
  background-image:
    linear-gradient(90deg, transparent 24.9%, rgb(133 149 176 / 0.14) 25%, transparent 25.1%, transparent 49.9%, rgb(133 149 176 / 0.14) 50%, transparent 50.1%, transparent 74.9%, rgb(133 149 176 / 0.14) 75%, transparent 75.1%),
    linear-gradient(rgb(130 146 172 / 0.06) 1px, transparent 1px),
    linear-gradient(90deg, rgb(130 146 172 / 0.06) 1px, transparent 1px);
  background-size: 100% 100%, 48px 48px, 48px 48px;
}

.focus-columns {
  position: absolute;
  inset: 0 0 auto;
  z-index: 2;
  display: grid;
  height: 56px;
  grid-template-columns: repeat(3, 1fr);
  align-items: center;
  padding: 0 30px;
  border-bottom: 1px solid #334056;
  color: #aeb9ca;
  background: #151f2f;
  font-size: 12px;
  font-weight: 750;
  pointer-events: none;
}

.focus-columns span:nth-child(2) { text-align: center; }
.focus-columns span:last-child { text-align: right; }

.knowledge-columns {
  position: absolute;
  inset: 0 0 auto;
  z-index: 2;
  display: grid;
  height: 56px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  align-items: center;
  padding: 0 14px;
  border-bottom: 1px solid #334056;
  color: #aeb9ca;
  background: #151f2f;
  font-size: 12px;
  font-weight: 750;
  text-align: center;
  pointer-events: none;
}

.knowledge-columns span { min-width: 0; line-height: 1.35; }

.knowledge-relation__hit {
  fill: none;
  stroke: transparent;
  stroke-width: 16;
  stroke-linecap: round;
  pointer-events: stroke;
  cursor: pointer;
}

.knowledge-relation__line {
  fill: none;
  stroke: #596577;
  stroke-width: 1.15;
  stroke-linecap: round;
  stroke-linejoin: round;
  marker-end: url(#knowledge-arrow);
  opacity: 0.72;
  pointer-events: none;
  transition: stroke .16s ease, stroke-width .16s ease, opacity .16s ease;
}

#knowledge-arrow path { fill: #596577; }
#knowledge-arrow-active path { fill: #9299ff; }

.knowledge-relation__label {
  fill: #aeb3ff;
  stroke: #101927;
  stroke-width: 5px;
  stroke-linejoin: round;
  paint-order: stroke;
  font-size: 9px;
  font-weight: 700;
  opacity: 0;
  pointer-events: none;
  transition: opacity .16s ease;
}

.knowledge-relation:hover .knowledge-relation__line {
  stroke: #9299ff;
  stroke-width: 2.5;
  opacity: 1;
  marker-end: url(#knowledge-arrow-active);
}

.knowledge-relation:hover .knowledge-relation__label {
  opacity: 1;
}

.knowledge-relation { transition: opacity .16s ease; }
.knowledge-relation.is-related .knowledge-relation__line {
  stroke: #9299ff;
  stroke-width: 2.5;
  opacity: 1;
  marker-end: url(#knowledge-arrow-active);
}
.knowledge-relation.is-dimmed { opacity: 0.14; }

.knowledge-node {
  cursor: pointer;
  outline: none;
  transition: opacity .16s ease;
}

.knowledge-node__hit { fill: transparent; }
.knowledge-node__ring {
  fill: rgb(133 139 255 / 0.07);
  stroke: transparent;
  stroke-width: 2;
  transition: fill .18s ease, stroke .18s ease;
}
.knowledge-node__dot {
  fill: #758298;
  stroke: #111a29;
  stroke-width: 3;
  transition: fill .18s ease, transform .18s ease;
}
.knowledge-node__label {
  fill: #718096;
  font-size: 8px;
  font-weight: 650;
  pointer-events: none;
  transition: fill .16s ease;
}
.knowledge-node:hover .knowledge-node__ring,
.knowledge-node:focus-visible .knowledge-node__ring,
.knowledge-node.is-search-match .knowledge-node__ring {
  fill: rgb(133 139 255 / 0.14);
  stroke: #9299ff;
}
.knowledge-node:hover .knowledge-node__dot,
.knowledge-node:focus-visible .knowledge-node__dot,
.knowledge-node.is-search-match .knowledge-node__dot { fill: #9299ff; }
.knowledge-node:hover .knowledge-node__label,
.knowledge-node:focus-visible .knowledge-node__label,
.knowledge-node.is-search-match .knowledge-node__label { fill: #aeb9ca; }
.knowledge-node.is-related .knowledge-node__ring {
  fill: rgb(133 139 255 / 0.09);
  stroke: #7d889c;
}
.knowledge-node.is-related .knowledge-node__dot { fill: #909bad; }
.knowledge-node.is-dimmed { opacity: 0.3; }
.knowledge-node.is-current .knowledge-node__ring {
  fill: rgb(133 139 255 / 0.16);
  stroke: #9299ff;
}
.knowledge-node.is-current .knowledge-node__dot { fill: #858bff; }
.knowledge-node.is-current .knowledge-node__label { fill: #cbd0ff; }

.empty-relation {
  fill: #66758b;
  font-size: 11px;
  font-weight: 650;
}

.focus-inspector {
  display: flex;
  min-width: 0;
  flex-direction: column;
  justify-content: center;
  padding: 34px 30px;
  border: 1px solid #334056;
  border-left: 0;
  background: #151e2d;
}

.focus-inspector .node-kind {
  color: #9299ff;
  font-size: 11px;
  font-weight: 750;
}
.focus-inspector h2 {
  margin: 18px 0 12px;
  color: #f2f5fa;
  font-size: clamp(22px, 2.4vw, 34px);
  line-height: 1.2;
  letter-spacing: 0;
}
.focus-inspector > p {
  margin: 0;
  color: #a8b4c7;
  font-size: 13px;
  line-height: 1.8;
}
.focus-metrics {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1px;
  margin-top: 24px;
  background: #303b4e;
}
.focus-metrics div {
  display: grid;
  gap: 5px;
  padding: 14px;
  background: #121b2a;
}
.focus-metrics strong {
  color: #eef2fa;
  font-family: ui-monospace, monospace;
  font-size: 18px;
}
.focus-metrics span { color: #8492a7; font-size: 10px; }
.focus-inspector .inspector-action { margin-top: 24px; }

.legend-current {
  background: #858bff;
  box-shadow: 0 0 0 2px rgb(133 139 255 / 0.18);
}

.note-reader {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  min-height: 100dvh;
  flex-direction: column;
  color: #e8edf5;
  background-color: #0c131f;
  background-image:
    linear-gradient(rgb(130 146 172 / 0.045) 1px, transparent 1px),
    linear-gradient(90deg, rgb(130 146 172 / 0.045) 1px, transparent 1px);
  background-size: 48px 48px;
}

.reader-header {
  display: flex;
  min-height: 72px;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 12px 26px;
  border-bottom: 1px solid #2d394c;
  background: rgb(15 23 36 / 0.95);
}
.reader-heading,
.reader-actions { display: flex; align-items: center; }
.reader-heading { min-width: 0; gap: 14px; }
.reader-heading > div { min-width: 0; }
.reader-heading span {
  display: block;
  margin-bottom: 3px;
  color: #9299ff;
  font-size: 10px;
  font-weight: 750;
}
.reader-heading strong {
  display: block;
  overflow: hidden;
  color: #f1f4fa;
  font-size: 14px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.reader-actions { flex: 0 0 auto; gap: 8px; }
.reader-actions > button:not(.create-button) {
  min-height: 34px;
  padding: 0 11px;
  border: 1px solid #354258;
  border-radius: 7px;
  color: #b7c2d2;
  background: #141e2d;
  cursor: pointer;
  font-size: 11px;
}
.reader-actions .danger:hover { border-color: rgb(251 113 133 / 0.42); color: #fda4af; }

.reader-main {
  flex: 1;
  overflow-y: auto;
  padding: 46px 24px 80px;
}
.reader-document,
.reader-editor {
  width: min(860px, 100%);
  margin: 0 auto;
}
.reader-document .drawer-tags { margin-bottom: 28px; }
.reader-document.markdown-body :deep(h1) { font-size: clamp(30px, 4vw, 46px); }
.reader-document.markdown-body :deep(p),
.reader-document.markdown-body :deep(li) { font-size: 15px; line-height: 1.9; }

/* ---- 防御全局 markdown 样式泄漏（docs/4 的 H1）——兜底用 ----
 * 背景：TradeSimSimulator.vue 与 TradeSimDetail.vue 曾在 import 阶段全局引入
 * `github-markdown-css/github-markdown-light.css`，它给 `.markdown-body` 设了
 * `background-color:#ffffff; color:#1f2328`，并给链接、引用、分隔线、表格行
 * 配了浅色。本页阅读器用的是 `reader-document markdown-body`，于是**只要本次
 * 会话访问过任意 TradeSim 页面**，阅读区就整块变白。
 *
 * 根治已完成（docs/4 §12.1，2026-09-20）：TradeSim 侧那两个全局 import 已移除，
 * 类名改为 `.tradesim-markdown`。本段**保留为兜底**，防止将来再出现同类泄漏。
 *
 * 本段只管"泄漏真的击穿了什么"，逐条核对结果：
 *   · 容器背景 —— 门户从未给 `.markdown-body` 设过 background，**这是唯一被真正
 *     击穿的属性**。白底让门户自己的浅色正文（`#f4f8ff` / `#aebbd0`）看不见。
 *   · 链接 / 引用 / 分隔线 / 表格行 / 单元格边框 —— 门户未定义，泄漏会直接生效。
 *   · 标题、正文、代码块的配色**门户已经定义好了**（见本文件 :1782 的
 *     `#f4f8ff` / `#aebbd0` / `#0b1220` / `#b8e6ff`），且特异性 (0,2,x) 本就
 *     压过泄漏的 (0,1,x)。**所以这里绝不能碰它们**：本段选择器是 (0,3,x)，
 *     一旦声明就会反过来盖掉门户自己的配色。
 *     （初版曾在此声明 `color:inherit` 与代码块底色，属过度覆盖，已删除。）
 *
 * 能压过泄漏的原因：本组件样式块是 `scoped`，选择器编译为
 * `.reader-document.markdown-body[data-v-xxx] ...`，特异性高于全局单类规则，
 * 因此与加载顺序无关。 */
.reader-document.markdown-body {
  background: transparent;
  color: var(--text);
}
.reader-document.markdown-body :deep(a) {
  color: inherit;
  text-decoration: inherit;
}
.reader-document.markdown-body :deep(blockquote) {
  color: inherit;
  border-left-color: var(--border-color);
}
.reader-document.markdown-body :deep(hr) {
  background-color: var(--border-color);
  border-bottom-color: var(--border-color);
}
.reader-document.markdown-body :deep(table) tr {
  background-color: transparent;
  border-top-color: var(--border-color);
}
.reader-document.markdown-body :deep(table) td,
.reader-document.markdown-body :deep(table) th {
  border-color: var(--border-color);
}
.reader-editor { min-height: calc(100dvh - 190px); }

.notebook-switcher {
  display: flex;
  min-width: 0;
  flex: 0 1 auto;
  align-items: center;
  gap: 2px;
  padding: 3px;
  overflow-x: auto;
  border: 1px solid #2d394c;
  border-radius: 7px;
  background: #0b121e;
  scrollbar-width: none;
}
.notebook-switcher::-webkit-scrollbar { display: none; }
.notebook-switcher button {
  min-height: 28px;
  flex: 0 0 auto;
  padding: 0 9px;
  border: 0;
  border-radius: 5px;
  color: #8694a9;
  background: transparent;
  cursor: pointer;
  font-size: 10px;
  font-weight: 700;
  white-space: nowrap;
}
.notebook-switcher button:hover { color: #dce3ef; background: #182234; }
.notebook-switcher button.is-active { color: #f1f3ff; background: #3d467d; }

/* Reference-aligned learning map shell */
.notes-workspace {
  --reference-ink: #edf2ff;
  --reference-muted: #a9b3c7;
  --reference-card: #192232;
  --reference-accent: #8d94ff;
  --reference-divider: rgb(169 179 199 / 0.22);
  height: auto;
  min-height: 100dvh;
  overflow-x: clip;
  overflow-y: visible;
  color: var(--reference-ink);
  background:
    radial-gradient(circle at 10% 2%, rgb(141 148 255 / 0.14), transparent 28rem),
    linear-gradient(180deg, #0c111a 0, #101722 72rem);
  font-family: Inter, "SF Pro Display", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif;
}

.learning-hero {
  position: relative;
  display: flex;
  width: min(1240px, 100%);
  min-height: calc(100dvh - 34px);
  flex-direction: column;
  justify-content: center;
  margin: 0 auto;
  padding: min(8vh, 72px) 28px;
  text-align: center;
}

.learning-hero::before,
.learning-hero::after {
  position: absolute;
  z-index: 0;
  width: 220px;
  height: 220px;
  border: 1px solid rgb(141 148 255 / 0.16);
  border-radius: 50%;
  content: '';
  pointer-events: none;
}
.learning-hero::before { top: -120px; left: 4%; }
.learning-hero::after { right: 1%; bottom: -90px; width: 320px; height: 320px; }
.learning-hero > * { position: relative; z-index: 1; }

.learning-brand {
  display: inline-flex;
  align-self: flex-start;
  align-items: center;
  gap: 10px;
  margin-bottom: 74px;
  padding: 0;
  border: 0;
  color: #c7d0e4;
  background: transparent;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: .18em;
}
.learning-brand__mark {
  display: grid;
  grid-template-columns: repeat(2, 7px);
  gap: 2px;
  transform: rotate(45deg);
}
.learning-brand__mark i {
  width: 7px;
  height: 7px;
  border-radius: 2px;
  background: var(--reference-accent);
}

.learning-hero__eyebrow {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-bottom: 18px;
  color: var(--reference-accent);
  font-size: 11px;
  font-weight: 800;
  letter-spacing: .18em;
}
.learning-hero__eyebrow > span {
  width: 28px;
  height: 2px;
  border-radius: 2px;
  background: var(--reference-accent);
}
.learning-hero h1 {
  max-width: 1120px;
  margin: 0 auto;
  color: #edf2ff;
  font-size: 68px;
  font-weight: 850;
  line-height: 1.08;
  letter-spacing: 0;
  white-space: nowrap;
}
.learning-hero > p {
  margin: 24px auto 0;
  color: #d6deee;
  font-size: 21px;
  letter-spacing: .02em;
}
.learning-hero__meta {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  margin-top: 30px;
  color: #c4cede;
  font-size: 12px;
}
.learning-hero__meta strong { color: #f4f7ff; }

.learning-hero__start {
  position: relative;
  display: inline-flex;
  min-height: 68px;
  align-items: center;
  justify-content: center;
  align-self: center;
  gap: 14px;
  margin-top: 42px;
  padding: 0 36px;
  border: 1px solid rgb(255 255 255 / 0.55);
  border-radius: 999px;
  color: #fff;
  background:
    radial-gradient(circle at 24% 18%, rgb(255 255 255 / 0.34), transparent 30%),
    linear-gradient(135deg, #8d94ff 0%, #747cff 54%, #67d3ff 120%);
  box-shadow: 0 18px 48px rgb(91 92 240 / 0.28), inset 0 1px 0 rgb(255 255 255 / 0.42);
  font-size: 18px;
  font-weight: 850;
  letter-spacing: .04em;
  transition: transform .2s ease, box-shadow .2s ease, filter .2s ease;
}
.learning-hero__start:hover {
  box-shadow: 0 24px 62px rgb(91 92 240 / 0.34), inset 0 1px 0 rgb(255 255 255 / 0.5);
  filter: saturate(1.06);
  transform: translateY(-3px);
}
.learning-hero__start:active { transform: translateY(-1px) scale(.98); }
.learning-hero__start-icon {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border-radius: 50%;
  color: #646bf0;
  background: rgb(255 255 255 / 0.96);
  box-shadow: 0 8px 18px rgb(38 46 88 / 0.18);
  font-size: 20px;
  line-height: 1;
}

.notes-header {
  position: relative;
  z-index: 3;
  display: flex;
  width: min(1280px, calc(100% - 48px));
  min-height: 82px;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin: 0 auto;
  padding: 24px 0 0;
  border: 0;
  border-top: 1px solid var(--reference-divider);
  background: transparent;
}
.notes-brand { display: none; }
.notes-header__actions { gap: 10px; }
.search-control {
  min-height: 38px;
  border-color: rgb(169 179 199 / 0.18);
  border-radius: 10px;
  background: #121b2a;
}
.create-button,
.inspector-action {
  min-height: 38px;
  border-color: rgb(141 148 255 / 0.34);
  border-radius: 10px;
  color: #eef1ff;
  background: #555dc0;
}
.notebook-switcher {
  border-color: rgb(169 179 199 / 0.18);
  border-radius: 11px;
  background: #121b2a;
}
.notebook-switcher button { min-height: 32px; padding: 0 12px; border-radius: 8px; }
.notebook-switcher button.is-active { background: #454e8f; }

.notes-main {
  width: min(1280px, calc(100% - 48px));
  height: auto;
  min-height: 0;
  margin: 0 auto;
  padding: 0 0 34px;
  scroll-margin-top: 12px;
}
.graph-workspace {
  height: calc(100dvh - 58px);
  min-height: 620px;
  overflow: hidden;
  padding: 0;
  border: 1px solid var(--reference-divider);
  border-radius: 24px;
  background: var(--reference-card);
  box-shadow: 0 24px 70px rgb(0 0 0 / 0.28);
}
.graph-toolbar {
  min-height: 58px;
  padding: 0 26px;
  border: 0;
  border-bottom: 1px solid var(--reference-divider);
  border-radius: 0;
  color: #a9b3c7;
  background: var(--reference-card);
  font-size: 14px;
}
.graph-toolbar > div { gap: 11px; }
.graph-toolbar strong { color: #edf2ff; font-size: 14px; }
.live-indicator { background: #4fd1a5; box-shadow: 0 0 0 5px rgb(79 209 165 / 0.12); }
.toolbar-divider { height: 18px; background: var(--reference-divider); }
.toolbar-hint { color: #a9b3c7; }
.continue-button {
  min-height: 38px;
  padding: 0 16px;
  border-color: var(--reference-divider);
  border-radius: 10px;
  color: #b8bdff;
  background: rgb(141 148 255 / 0.12);
}
.graph-body { min-height: 0; flex: 1; }
.graph-body .graph-canvas {
  min-height: 0;
  border: 0;
  border-radius: 0;
  background: #111a29;
}
.graph-body .notes-graph-svg {
  height: 100%;
  min-height: 0;
  background-color: #111a29;
  background-image:
    linear-gradient(90deg, transparent 24.9%, rgb(169 179 199 / 0.18) 25%, transparent 25.1%, transparent 49.9%, rgb(169 179 199 / 0.18) 50%, transparent 50.1%, transparent 74.9%, rgb(169 179 199 / 0.18) 75%, transparent 75.1%),
    linear-gradient(rgb(169 179 199 / 0.055) 1px, transparent 1px),
    linear-gradient(90deg, rgb(169 179 199 / 0.055) 1px, transparent 1px);
  background-size: 100% 100%, 30px 30px, 30px 30px;
}
.knowledge-columns,
.focus-columns {
  height: 48px;
  padding: 0 32px;
  border-bottom-color: var(--reference-divider);
  color: #c8d2e3;
  background: #151e2d;
  font-size: 9px;
  font-weight: 800;
  letter-spacing: .05em;
}
.knowledge-columns span:not(:last-child) { border-right: 1px dashed rgb(169 179 199 / 0.18); }
.knowledge-columns span { display: grid; align-self: stretch; place-items: center; }

.graph-footer {
  min-height: 72px;
  padding: 0 26px;
  border: 0;
  border-top: 1px solid var(--reference-divider);
  border-radius: 0;
  color: #c6cfdf;
  background: var(--reference-card);
}
.graph-legend strong { color: #eef3ff; }
.graph-summary b { color: #f0f4ff; }

.knowledge-relation__line {
  stroke: rgb(143 153 171 / 0.32);
  stroke-width: .82;
  opacity: 1;
  marker-end: url(#knowledge-arrow);
}
.knowledge-relation:hover .knowledge-relation__line {
  stroke: var(--reference-accent);
  stroke-width: 2.2;
  opacity: 1;
  marker-end: url(#knowledge-arrow-active);
}
.knowledge-relation__label {
  fill: #c5c9ff;
  stroke: #111a29;
  font-size: 10px;
}

.knowledge-node__ring {
  fill: transparent;
  stroke-width: 1.5;
}
.knowledge-node__dot {
  fill: #6f7b8f;
  stroke: #111a29;
  stroke-width: 2;
  filter: drop-shadow(0 2px 3px rgb(23 34 55 / 0.28));
}
.knowledge-node__label {
  fill: #c6cfdf;
  font-size: 9px;
  font-weight: 700;
  opacity: .9;
}
.knowledge-node:hover .knowledge-node__dot,
.knowledge-node:focus-visible .knowledge-node__dot { transform: scale(1.28); }
.knowledge-node.is-current .knowledge-node__label { fill: #eef1ff; }
.graph-body.is-focused .knowledge-node__label { font-size: 12px; opacity: 1; }
.graph-body.is-focused .knowledge-node.is-current .knowledge-node__label { font-size: 13px; font-weight: 850; }

.focus-inspector {
  padding: 26px 24px;
  border-color: var(--reference-divider);
  background: linear-gradient(180deg, rgb(25 34 50 / 0.98), rgb(21 30 45 / 0.99));
}
.focus-inspector h2 { font-size: 26px; }
.focus-inspector > p { color: #a9b3c7; font-size: 14px; line-height: 1.7; }
.focus-metrics { background: var(--reference-divider); }
.focus-metrics div { background: #151e2d; }

@media (min-width: 801px) and (max-width: 1180px) {
  .learning-hero h1 { font-size: 56px; white-space: normal; }
  .notes-header { min-height: 122px; flex-wrap: wrap; }
  .notebook-switcher { order: 3; width: 100%; }
}

@media (max-width: 800px) {
  .learning-hero { min-height: calc(100dvh - 24px); padding: 48px 18px; }
  .learning-hero::before { left: -90px; }
  .learning-hero::after { right: -170px; }
  .learning-brand { margin-bottom: 48px; }
  .learning-hero h1 { font-size: 42px; white-space: normal; }
  .learning-hero > p { font-size: 16px; line-height: 1.7; }
  .learning-hero__start { min-height: 58px; margin-top: 34px; padding: 0 28px; font-size: 16px; }
  .notes-header,
  .notes-main { width: min(100% - 28px, 1280px); }
  .notes-header { min-height: 156px; align-items: stretch; flex-direction: column; gap: 10px; padding-top: 18px; }
  .notes-header__actions { width: 100%; }
  .notebook-switcher { width: 100%; }
  .knowledge-columns { padding: 0 5px; font-size: 9px; }
  .graph-body.is-focused { display: flex; flex-direction: column; }
  .graph-toolbar .continue-button { display: inline-flex; align-items: center; white-space: nowrap; }
  .graph-toolbar { padding: 0 16px; }
  .toolbar-hint { display: none; }
  .graph-body .graph-canvas { min-height: 470px; }
  .graph-body .notes-graph-svg { min-height: 470px; }
  .focus-inspector { border-top: 0; border-left: 1px solid #334056; padding: 24px 20px; }
  .graph-workspace { height: auto; min-height: 780px; }
  .graph-footer { min-height: 88px; }
  .reader-header { align-items: flex-start; flex-direction: column; padding: 14px 16px; }
  .reader-actions { width: 100%; justify-content: flex-end; }
  .reader-main { padding: 28px 18px 56px; }
}

@media (prefers-reduced-motion: reduce) {
  .learning-hero__start,
  .knowledge-relation__line,
  .knowledge-relation__label,
  .knowledge-node__ring,
  .knowledge-node__dot { transition: none; }
}
</style>
