# KnowledgeMap

KnowledgeMap 的集成版本由一个前端入口和一个后端入口组成。TradeSim 已作为 `/tradesim` 功能模块并入，不再单独启动。

## 统一启动

后端：

```powershell
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8010
```

前端：

```powershell
cd frontend
npm run dev
```

浏览器访问 `http://localhost:3000/`，从门户进入 TradeSim，或直接访问：

- `/tradesim/simulate`：网格回测
- `/tradesim/dashboard`：回测收藏库
- `/tradesim/detail/:id`：回测详情
- `/tradesim/yearline`：年线策略占位页

前端 `/api` 请求默认代理到 `http://localhost:8010`，可通过 `KM_API_TARGET` 覆盖。TradeSim 集成版将关系型索引表放在现有 `knowledgemap` MySQL 数据库，大体积结果放在 MongoDB 的 `tradesim.simulation_logs` 集合，相关连接及 AI 配置见 `backend/.env.example`。

## 独立打包备份

独立打包版保存在仓库外：

`C:\Users\afrangry\PycharmProjects\TradeSim-standalone-backup`

该备份保留 TradeSim 原有的独立启动、前端开发和 PyInstaller 打包入口；集成版本不依赖这些入口。
