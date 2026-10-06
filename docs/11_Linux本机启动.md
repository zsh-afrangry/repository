# Linux 本机开发环境

2026-10-03 在 `/home/afrangry/桌面/KnowledgeMap` 验证。本页描述本次克隆所在的 Ubuntu 22.04；其他文档中的 Windows 路径、原机器数据数量不适用于本机。

## 环境

- Miniconda：`/home/afrangry/miniconda3`。
- `desheng`：Python 3.12.14。其他环境为 base 3.13.13、CalorieCalPose 3.10.20、Transformer 3.11.15，均未修改。
- 后端依赖从 `backend/requirements.txt` 安装，`pip check` 通过；该文件不是版本锁。
- 前端使用系统 Node 26.10.0 / npm 11.19.1，通过 `npm ci` 按现有锁文件安装。
- MySQL 8.0.46 原已安装运行；已用 `.env` 配置创建 `knowledgemap` 库，应用启动建立表和 37 个默认标签。
- MongoDB 8.0.16 从官方发行包安装到 `~/.local/opt/mongodb-linux-x86_64-ubuntu2204-8.0.16`，仅监听 `127.0.0.1:27017`。
- MongoDB 数据：`~/.local/share/knowledgemap/mongodb`，用户服务配置：`~/.config/systemd/user/knowledgemap-mongodb.service`。本次已启动，未设置登录自动启动。
- `backend/.env` 由用户提供，不提交、不记录密钥。

## 一键启动与停止（Tailscale / 局域网）

在项目根目录的终端执行：

```bash
./Start-KnowledgeMap.sh          # 默认 Tailscale HTTPS
./Stop-KnowledgeMap.sh           # 停止独立网页服务及其 Tailscale 转发
```

默认访问 `https://afrangry.tail9edbaa.ts.net:8443/`（以脚本实际输出为准）。访问设备需连接该 Tailnet 并有访问权限；本机服务只监听 `127.0.0.1:8020`。脚本不会改动 DSH 使用的 443 转发，也不启用 Funnel 公网访问。Tailscale 操作没有权限时会在终端请求 `sudo` 密码；不要对整个启动脚本使用 sudo，否则会选错用户环境。

启动器输出可直接点击的鉴权链接，格式为 `https://主机:8443/_km/login#key=口令`。浏览器打开后自动登录、清除地址栏片段并跳转首页，不需要手动填写账号密码。口令不进入HTTP请求URL；登录后使用HttpOnly、SameSite=Strict的会话Cookie，HTTPS下还带Secure属性。除登录引导页外，页面、静态文件、API和API文档仍受保护；保留HTTP Basic兼容方式（用户名`km`）。口令首次随机生成，固定保存在 `~/.local/state/knowledgemap-launcher/web.json`（目录700、文件600），不进入 Git。`--hide-key` 仅输出不带口令的普通地址；需要更换口令时先停止，删除该 JSON，再启动。

局域网选项：

```bash
./Stop-KnowledgeMap.sh
./Start-KnowledgeMap.sh --lan
```

此模式监听 `0.0.0.0:8020`，输出本机网卡地址；本次为 `http://192.168.1.132:8020/`，地址可能变化。其他设备不需要 Tailscale，但需能通过局域网/防火墙访问该端口。同样输出一键鉴权链接。**局域网模式是 HTTP，口令和数据没有 TLS 加密，只用于可信网络；需要 HTTPS 时使用默认 Tailscale 模式。** 脚本不会修改防火墙。

启动器通过 `backend/main.py` 的 `KM_WEB_CONFIG` 模式提供构建后的前端与 API，使用同源路径并支持 SPA 深链接刷新；不对外开放 Vite。每次从停止状态启动都会执行前端类型检查与构建，并复制私有静态快照，所以修改代码后需停止再启动。已运行时重复启动仅检查服务并打印地址，不另开进程；切换模式须先停止。默认解释器为 `~/miniconda3/envs/desheng/bin/python`，可用 `KM_PYTHON` 覆盖。

独立用户服务名为 `knowledgemap-web.service`，关闭终端后继续运行；没有配置开机自启或用户退出后继续运行。启动时确保 Mongo 用户服务运行；MySQL 沿用已有系统服务。停止时保留数据库和手动启动的3000/8010开发进程。服务日志：

```bash
journalctl --user -u knowledgemap-web.service -n 50
```

2026-10-04 验证：构建通过；5组隔离托管测试覆盖未认证拒绝、错误口令、SPA/资源/API边界、跨站写入阻止、SSE响应；局域网绑定后从本机 Chrome 使用局域网 IP 验证首页、账单、回测页登录、刷新及真实标签读取；重复启动、重复停止通过。随后用户提供本机 sudo 凭据，已完成8443转发配置及本机HTTPS证书校验、未认证401、认证后首页/账单/API 200验证；停止脚本只移除8443，DSH 443保留。修复停止后TCP TIME_WAIT造成的端口误报，重新启动成功；重复启动不再重复请求sudo。**另一台设备的实际访问尚未验证**。既有构建大包与第三方注释警告仍在；未调用付费AI或修改业务数据。

同日一键鉴权链接验证：本机 Chrome 分别通过回环HTTP与Tailscale HTTPS打开完整链接，无需手填凭据即可进入首页；URL片段清除，标签API和账单页刷新通过，HTTPS Cookie的Secure/HttpOnly/SameSite属性正确。错误链接显示失败信息，不弹Basic登录框。验证后恢复为停止状态。

隔离验证命令：`~/miniconda3/envs/desheng/bin/python backend/tests/web_host_cases.py`。

## 手动开发启动（仅本机）

先启动 MongoDB（重复执行安全）：

```bash
systemctl --user start knowledgemap-mongodb
systemctl --user status knowledgemap-mongodb
```

后端终端：

```bash
conda activate desheng
cd /home/afrangry/桌面/KnowledgeMap/backend
python main.py
```

前端终端：

```bash
cd /home/afrangry/桌面/KnowledgeMap/frontend
npm run dev -- --host localhost
```

浏览器访问 <http://localhost:3000/>；后端为 <http://127.0.0.1:8010/docs>。若当前已有开发进程，无需重复启动。前后端终端使用 Ctrl+C 停止；MongoDB 使用 `systemctl --user stop knowledgemap-mongodb` 停止。

MongoDB 日志：`journalctl --user -u knowledgemap-mongodb -n 50`。MySQL 沿用系统已有服务。

## 2026-10-03 初次启动验证

- 前端类型检查及生产构建通过；仍有大包和第三方注释警告。安装审计报告 5 项依赖漏洞（1 low、4 high），未自动升级锁文件。
- 策略 8/8、账单 9/9 测试通过，后端依赖一致性检查通过。
- 前端代理后的健康、账单、标签、日历、收藏列表接口正常；MongoDB ping 成功；天气接口 HTTP 200。
- 真实行情回测：000400，2024-01-01 至 2024-12-31，日线，等比网格 20–30 / 5%，本金 100000、底仓 0.5、每格金额 10000、佣金 0.00025、滑点 0.01。返回 242 个净值点、62 条成交流水。
- 该回测已保留为测试收藏 ID 1，保存及详情读取均成功，验证 MySQL 索引与 MongoDB 大对象的正常读写路径。
- 未调用付费 AI；这不代表所有外部服务或异常路径已验收。已有 D1–D8 等任务保持原状态。

本机使用新建开发库，没有迁移其他机器数据。

## 2026-10-04 正式开发前核查

- Ubuntu 22.04.5；Python 3.12.14、Node 26.10.0、npm 11.19.1 与上述环境一致；desheng 的 `pip check` 通过。
- `npm run build`（含 vue-tsc）通过；策略 8/8、账单 9/9 隔离回归通过。构建仍提示第三方 PURE 注释位置与超过 500 kB 的包，不影响本次构建；按需加载仍属 E7。
- MySQL 只读计数：bills=0、tags=37、calendar_events=0、simulation_records=1；Mongo simulation_logs=1，唯一 SQL 引用可解析。用户确认仅为默认/测试数据，不要求迁移 Windows 业务数据。
- 检查开始时前后端未运行。临时启动回环地址后，经 Vite 代理验证 health、bills、tags、calendar-events、git-stats、`/api/tradesim/v1/records/list` 和 `records/detail/1` 全部 HTTP 200；首页、`/bills`、`/tradesim/simulate` HTTP 200。随后关闭本次启动的两个进程；数据库服务保持原状。
- Mongo 用户服务 active，但 disabled（未启用登录自动启动）。重启或重新登录后按前述命令启动；这不是数据库故障。
- 代码扫描未发现应用 Python/TS 对 Windows shell 或绝对盘符路径的依赖；Git 统计使用参数数组调用系统 Git。构建和接口验证未发现 Ubuntu 迁移阻断项。
- 当前跟踪文本为 LF，`core.autocrlf` 未设置。`.env`、node_modules、dist 正确忽略；没有将本机密钥或数据库数据纳入提交。
- `frontend_example/`、`tp.md`、`tp2.txt` 是已跟踪的原型/草稿；`repository/` 是空目录；均不参与应用运行，保留不删除。原 Windows 的 UI预览图、tmp_screenshots、.pnpm-store、.npm-cache 在本机不存在。历史 SQL 含破坏性建表语句，继续只作参考，不执行。
- 修正文档中的 Windows 默认命令、旧库数量、CRLF、IPv6-only 与 tp.md 未跟踪等旧结论；归档、设计原稿和历史审计证据保持原文。

验证边界：未进行浏览器视觉/交互验收，未重跑外部行情或付费 AI，未迁移真实业务数据、升级依赖或修复 D/E/V/P 项。当前可作为 Ubuntu 开发基线，不能称为全功能无缺陷或生产验收通过。
