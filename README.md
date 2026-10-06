# KnowledgeMap

> **Linux 克隆环境（2026-10-03）：** 本机已建立 Python 3.12 的 desheng、MySQL 开发库和用户级 MongoDB；启动与验证见 [docs/11_Linux本机启动.md](docs/11_Linux本机启动.md)。下文“本机已有”及 Windows 历史说明需按机器区分。

KnowledgeMap 的集成版本由一个前端入口和一个后端入口组成。TradeSim 已作为 `/tradesim` 功能模块并入，不再单独启动。

> **文档导航：[`docs/0_README.md`](docs/0_README.md)**。接手请读 [`docs/8_交接说明.txt`](docs/8_交接说明.txt)，当前任务见 [`todolist.txt`](todolist.txt)。
> 技术约定看 **[`AGENTS.md`](AGENTS.md)**；历史迁移、冻结审计和旧时间线见 [`已归档/0_README.md`](已归档/0_README.md)。文档声明需要结合代码与验证范围判断。

## 一键访问（Linux）

在项目根目录运行 `./Start-KnowledgeMap.sh`，通过 Tailscale HTTPS 访问；运行 `./Stop-KnowledgeMap.sh` 停止。需要局域网访问时，停止后使用 `./Start-KnowledgeMap.sh --lan`。启动脚本输出包含鉴权的一键访问链接，打开即可登录；Tailscale 操作可能要求输入 sudo 密码。端口、日志、口令和验证边界见 [Linux 启动说明](docs/11_Linux本机启动.md)。

## 手动开发启动（仅本机）

前置条件：conda 环境 `desheng` 已建好、MySQL 与 MongoDB 都在运行、`backend/.env` 已按
`backend/.env.example` 填好。**`.env` 不在版本控制里，本机上它已经存在**；只有换机器时才需要
重新填值和单独获取密钥（见 `docs/8`）。

后端：

```bash
conda activate desheng
cd backend
python main.py
```

前端：

```bash
cd frontend
npm run dev
```

手动开发后端绑定 **`127.0.0.1:8010`**，此模式没有鉴权；端口可用 `KM_BACKEND_PORT` 覆盖。
其他设备访问请使用上方带口令保护的一键启动器（独立8020端口），不要直接对外开放开发端口。

浏览器访问 `http://localhost:3000/`，从门户进入 TradeSim，或直接访问：

- `/tradesim/simulate`：网格回测
- `/tradesim/dashboard`：回测收藏库
- `/tradesim/detail/:id`：回测详情
- `/tradesim/yearline`：年线策略占位页

前端 `/api` 请求默认代理到 `http://localhost:8010`，可通过 `KM_API_TARGET` 覆盖。TradeSim 集成版将关系型索引表放在现有 `knowledgemap` MySQL 数据库，大体积结果放在 MongoDB 的 `tradesim.simulation_logs` 集合，相关连接及 AI 配置见 `backend/.env.example`。

**数据不在 Git 里。** Ubuntu 使用新建开发库，只有默认标签和测试回测，未迁移 Windows 的真实账单与历史收藏。这是当前开发基线，不是数据丢失。需要迁移时必须同时迁移 MySQL 和 MongoDB 并验证关联；`表结构/` 仅是历史建表脚本，不能当备份恢复。

## 自检（改完代码跑这两条）

```bash
cd frontend
node node_modules/vue-tsc/bin/vue-tsc.js --noEmit
```

```bash
conda activate desheng
cd backend
python tests/tradesim_grid_strategy_cases.py   # 期望 8 个 PASS
python tests/portal_crud_cases.py              # 期望 13 个 PASS
```

## 独立打包备份

TradeSim 并入本仓库之前的独立打包版保存在**仓库之外**的一个目录里，保留原有的独立启动、前端开发
和 PyInstaller 打包入口。

⚠ 该目录**不在版本控制内，也不会随交接一起转移** —— 在没有它的机器上找不到属于正常情况。
集成版本不依赖它。

当前开发阶段：首页与账单收尾结果见 [docs/12_首页与账单收尾验收.md](docs/12_首页与账单收尾验收.md)。TradeSim 暂不修改，等待完整需求确认；Notes 学习模块已完成本轮开发验收，功能范围、复跑命令及人工验收见 [docs/13](docs/13_Notes学习模块功能与视觉开发方案.md)。
