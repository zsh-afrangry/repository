你当前会话中加载的 **Skill、Rule、插件、Tool 以及系统内置提示词模块** 的详细统计清单如下：

---

### 📊 总体概览

| 类别 | 数量 | 构成简述 |
| :--- | :--- | :--- |
| **Skills (技能)** | **32 个** | 全局 29 个 + 内置 2 个 + 项目级 1 个 |
| **Rules (规则)** | **1 个** | 项目级规则文件 ([AGENTS.md](file:///c:/Users/afrangry/PycharmProjects/KnowdegeMap/.agents/AGENTS.md)) |
| **Plugins (插件)** | **1 个** | 全局遥测扩展插件 |
| **MCP Servers** | **3 个** | `data-agent-kit`、`notebooks`、`visualization` |
| **Tools (可用工具)** | **33 个** | 17 个原生工具 + 16 个 MCP 工具 |
| **系统内置规范模块** | **9 大模块** | Web开发、Planning模式、Artifact格式、KI知识库等 |

---

### 一、Skills 详细清单（共 32 个）

1. **内置 Skills（2 个）**：
   - `agy-customizations`：Antigravity 自定义系统配置与扩展说明
   - `antigravity-guide`：CLI 与 IDE 使用全指南
2. **项目级 Skills（1 个）**：
   - `design-taste-frontend`（位于项目 `.agents/skills/`）：前端去模板化与 UI 设计指导
3. **全局 Skills（29 个，位于 `C:\Users\afrangry\.gemini\config\skills`）**：
   - **GCP / BigQuery 相关（18 个）**：`bigquery-ai-ml`, `bigquery-bigframes`, `bigquery-data-transfer-service`, `bigquery-graph`, `bigquery-sql`, `data-autocleaning`, `dataform-bigquery`, `dbt-bigquery`, `discovering-gcp-data-assets`, `enforcing-resource-attribution`, `federate-lakehouse-catalog`, `gcloud-auth-verification`, `gcp-composer-troubleshooting`, `gcp-data-pipelines`, `gcp-dataflow`, `gcp-managed-airflow-dag-authoring`, `gcp-managed-airflow-migrations`, `gcp-managed-airflow-recommendations`, `gcp-pipeline-orchestration`, `gcp-pipeline-resource-provisioning`, `gcp-spark`, `google-cloud-storage-basics`, `gcs-security-assessment`
   - **数据与应用开发（4 个）**：`building-data-apps`, `managing-python-dependencies`, `ml-best-practices`, `notebook-guidance`
   - **安全与系统修复（2 个）**：`accidental-data-loss-prevention`, `skill-repair`

---

### 二、Rules 规则清单（共 1 个）

- **项目规则**：[AGENTS.md](file:///c:/Users/afrangry/PycharmProjects/KnowdegeMap/.agents/AGENTS.md)
  - 核心要求：代码修改与下一步设计/规划需记录归档到 [todolist.txt](file:///c:/Users/afrangry/PycharmProjects/KnowdegeMap/todolist.txt)。

---

### 三、Plugins 插件（共 1 个）

- `googlecloudtools.datacloud_telemetry`（全局数据云遥测插件）

---

### 四、Tools 工具清单（共 33 个）

#### 1. 原生 IDE/系统工具（17 个）
- **文件与搜索**：`view_file`, `write_to_file`, `replace_file_content`, `multi_replace_file_content`, `list_dir`, `grep_search`
- **执行与终端**：`run_command`, `manage_task`, `schedule`
- **浏览器与搜索**：`search_web`, `read_url_content`, `browser_subagent`
- **交互与生成**：`ask_question`, `generate_image`, `call_mcp_tool`, `read_resource`, `list_resources`

#### 2. MCP 扩展工具（3 个 Server，共 16 个）
- **`notebooks` (11 个)**：`create_notebook`, `insert_markdown_cell`, `insert_code_cell`, `replace_cell`, `delete_cell`, `get_notebook_info`, `read_cell`, `list_cells`, `search_cells`, `get_cell_range`, `get_cell_outputs`
- **`data-agent-kit` (4 个)**：`get_active_editor_context`, `get_active_gcp_connection`, `list_resource_templates`, `read_resource`
- **`visualization` (1 个)**：`render_chart`

---

### 五、系统预置提示词 / 规则模块（9 大类）

1. `<identity>` & `<user_information>`：助手身份定位、Windows/PowerShell 环境、工作区映射。
2. `<web_application_development>`：前端应用构建标准、高级审美规范（抗模板化/玻璃拟态/无默认配色）、SEO 规则。
3. `<planning_mode>` & `<planning_mode_artifacts>`：深度规划模式逻辑（何时写 `implementation_plan.md`，执行流程与验证）。
4. `<artifacts>`：交互产物格式体系（支持 Alert 提示框、Mermaid 图表、Diff 对比、轮播组件 Carousel 等）。
5. `<knowledge_items>`：项目局部知识库 (KI) 检索与引用约束。
6. `<slash_commands>`：`/goal`, `/schedule`, `/grill-me`, `/learn` 推荐规则。
7. `<conversation_transcript>`：多轮对话与子 Agent 日志追溯机制。
8. `<messaging>`：异步任务消息推送与唤醒机制。
9. `<guidelines>` & `<communication_style>`：代码保留完整性、文件超链接语法与精简沟通风格。