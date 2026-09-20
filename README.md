# KnowledgeMap

KnowledgeMap 的集成版本由一个前端入口和一个后端入口组成。TradeSim 已作为 `/tradesim` 功能模块并入，不再单独启动。

> **接手 / 协作请先读 [`docs/8_交接说明.txt`](docs/8_交接说明.txt)**：怎么跑起来、现在到哪一步、密钥与数据怎么拿、哪些东西千万别动。
> 唯一权威文档是 **[`AGENTS.md`](AGENTS.md)**（`CLAUDE.md` 只是指向它的指针）。

## 统一启动

前置条件：conda 环境 `desheng` 已建好、MySQL 与 MongoDB 都在运行、`backend/.env` 已按
`backend/.env.example` 填好。**`.env` 不在版本控制里，密钥需要单独获取**（见 `docs/8`）。

后端：

```powershell
conda activate desheng
cd backend
python main.py
```

前端：

```powershell
cd frontend
npm run dev
```

⚠ 后端绑定 **`127.0.0.1:8010`**。端口可用 `KM_BACKEND_PORT` 覆盖，**主机是硬编码的**。
本项目**没有任何鉴权**，且包含**付费的 LLM 接口**，因此**不要改回 `0.0.0.0`** —— 确实需要
对外提供时必须先加 API-key 依赖。代价是：手机等同网段设备访问不了，这是刻意选择的。

浏览器访问 `http://localhost:3000/`，从门户进入 TradeSim，或直接访问：

- `/tradesim/simulate`：网格回测
- `/tradesim/dashboard`：回测收藏库
- `/tradesim/detail/:id`：回测详情
- `/tradesim/yearline`：年线策略占位页

前端 `/api` 请求默认代理到 `http://localhost:8010`，可通过 `KM_API_TARGET` 覆盖。TradeSim 集成版将关系型索引表放在现有 `knowledgemap` MySQL 数据库，大体积结果放在 MongoDB 的 `tradesim.simulation_logs` 集合，相关连接及 AI 配置见 `backend/.env.example`。

⚠ **数据不在仓库里。** 仓库只带两份建表 SQL（`表结构/`），账单、标签与回测数据都只存在于作者
本机的 MySQL / MongoDB 中，需要单独导出交接；**MongoDB 的 `tradesim.simulation_logs` 必须一起导**，
否则 TradeSim 的收藏详情页会打不开（那不是代码缺陷）。详见 `docs/8` 第 4 节。

## 自检（改完代码跑这两条）

```powershell
cd frontend
node node_modules/vue-tsc/bin/vue-tsc.js --noEmit
```

```powershell
conda activate desheng
cd backend
python tests/tradesim_grid_strategy_cases.py   # 期望 8 个 PASS
python tests/portal_crud_cases.py              # 期望 9 个 PASS
```

## 独立打包备份

TradeSim 并入本仓库之前的独立打包版保存在**仓库之外**的一个目录里，保留原有的独立启动、前端开发
和 PyInstaller 打包入口。

⚠ 该目录**不在版本控制内，也不会随交接一起转移** —— 在没有它的机器上找不到属于正常情况。
集成版本不依赖它。
