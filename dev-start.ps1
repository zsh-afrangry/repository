<#
.SYNOPSIS
    KnowledgeMap 开发环境一键启动（Windows 11 / PowerShell 7+）。

.DESCRIPTION
    一条命令起后端 + 前端，Ctrl+C 一起停。

    对应文档：docs/15_开发启动脚本方案.md「§3.4 `ensure_database.py` 的边界」/「§5.2 启动流程（两个平台同构）」。

    启动流程（每一步失败都会明确停下并说明原因）：

        1. 解析 Python 解释器
        2. 检查 backend/.env（缺失只提示，不阻止）
        3. 检查后端依赖（-Check 时才查，默认跳过以加快启动）
        4. 检查端口占用（被占用就报错并停，**不自动杀**）
        5. 跑 ensure_database.py（建库 + 报告表/种子/Mongo）
        6. 起后端，**等健康检查通过**才继续
        7. 起前端（Vite）
        8. 前台守候；任一进程退出或 Ctrl+C 就一起收摊

.PARAMETER Check
    启动前额外跑前端类型检查（vue-tsc）与后端依赖检查。默认关闭——开发时要快。

.PARAMETER BackendPort
    后端端口。默认 8010（与 main.py 的 KM_BACKEND_PORT 一致）。

.PARAMETER FrontendPort
    前端 Vite 端口。默认 3000。

.PARAMETER NoFrontend
    只起后端（例如你已单独开了前端）。

.PARAMETER BackendEntry
    后端的启动入口，默认 `backend/main.py`。

    存在的理由有两个：
      1. **可测试**：端到端验证本脚本时，需要一个"能被脚本启动、且能被观测"的入口，
         而不必依赖真实的 main.py 恰好能在当前环境跑起来；
      2. **可替换**：将来若有 `main_dev.py`（例如关掉 TradeSim 以加快启动），
         不必改脚本。

    传相对路径时相对 `backend/` 解析。

.EXAMPLE
    ./dev-start.ps1
    最常用的写法：起前后端。

.EXAMPLE
    ./dev-start.ps1 -Check
    额外做类型检查与依赖检查。

.EXAMPLE
    ./dev-start.ps1 -BackendPort 8011 -FrontendPort 3001
    端口冲突时换一组端口。**前后端会一起跟着换**（见下方"端口"说明）。

.NOTES
    ## 端口由本脚本统一决定

    这是本脚本最重要的设计：**端口只在一个地方决定**，然后注入给两个进程：

        后端  <- $env:KM_BACKEND_PORT   （main.py 读它）
        前端  <- $env:KM_API_TARGET     （vite.config.ts 读它，作为代理目标）

    为什么必须这样：Vite 的代理发生在 **Node 进程内部**，不是浏览器里，
    所以"前端读后端的端口"只能发生在 Vite 启动那一刻。若两边各自决定端口，
    一旦不一致，页面能打开但所有接口 404 —— 那种故障很难定位。

    ## 为什么不自动杀占用端口的进程

    被占用时**报错并停**，而不是替你杀掉。因为那个占用者可能是：

      - 你上一次忘记关的开发服务（→ 用 dev-stop.ps1）
      - 另一个不相关的程序（→ 杀了就是事故）

    脚本无法区分这两者，所以把判断权交回给你，并打印出占用者的 PID 与进程名。
#>

[CmdletBinding()]
param(
    [switch]$Check,
    [int]$BackendPort = 8010,
    [int]$FrontendPort = 3000,
    [switch]$NoFrontend,
    [string]$BackendEntry = 'main.py'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------- 常量与路径

$Root      = Split-Path -Parent $MyInvocation.MyCommand.Path
$Backend   = Join-Path $Root 'backend'
$Frontend  = Join-Path $Root 'frontend'
$PythonExe = if ($env:KM_PYTHON) { $env:KM_PYTHON }
             else { 'C:\Users\afrangry\anaconda3\envs\desheng\python.exe' }

# 前端 Node 可执行文件（npm 是 .ps1 包装，直接调 node 更可控）
$NodeExe = (Get-Command node -ErrorAction SilentlyContinue)?.Source

function Write-Step  { param([string]$Text) Write-Host "`n==> $Text" -ForegroundColor Cyan }
function Write-Ok    { param([string]$Text) Write-Host "  [OK] $Text" -ForegroundColor Green }
function Write-Warn2 { param([string]$Text) Write-Host "  [--] $Text" -ForegroundColor Yellow }
function Write-Err   { param([string]$Text) Write-Host "  [!!] $Text" -ForegroundColor Red }

# 子进程句柄。放在脚本作用域，供 finally 统一清理。
$script:Children = @()
# 退出码：0 = 正常（含用户 Ctrl+C），1 = 失败。在 catch/finally 里决定。
$script:ExitCode = 0

# ---------------------------------------------------------------- 工具函数

function Test-PortFree {
    <#
      用"能否真正绑定"来判断端口是否空闲——这是权威判据。

      ⚠️ 不用 Get-NetTCPConnection 作为唯一依据：TIME_WAIT 状态的连接
      仍会出现在那里，但服务其实可以正常绑定（docs/11 记过这个误报）。
    #>
    param([int]$Port)
    $listener = $null
    try {
        $listener = [System.Net.Sockets.TcpListener]::new(
            [System.Net.IPAddress]::Loopback, $Port)
        $listener.Start()
        return $true
    } catch {
        return $false
    } finally {
        if ($listener) { $listener.Stop() }
    }
}

function Get-PortOwner {
    <# 返回占用某个端口的进程信息，用于给出可读的报错。 #>
    param([int]$Port)
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
            Select-Object -First 1
    if (-not $conn) { return $null }
    $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
    return [pscustomobject]@{
        Pid  = $conn.OwningProcess
        Name = if ($proc) { $proc.ProcessName } else { '(已退出)' }
    }
}

function Start-Child {
    <#
      起一个子进程并登记，便于统一收摊。

      ⚠️ 刻意**不隐藏窗口**、不重定向输出：开发时要能看见后端日志与 Vite 输出。
      两个进程的输出会交织在同一个终端——这是我们接受的代价，
      换来"一个终端窗口 = 一次开发会话"这个简单的心理模型。
    #>
    param(
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$WorkingDirectory,
        [string]$Label
    )
    Write-Ok "启动 $Label"
    $proc = Start-Process -FilePath $FilePath -ArgumentList $Arguments `
        -WorkingDirectory $WorkingDirectory -PassThru -NoNewWindow
    $script:Children += [pscustomobject]@{ Label = $Label; Process = $proc }
    return $proc
}

function Stop-AllChildren {
    <#
      收摊：先关前端，再关后端。

      顺序有讲究：反过来的话 Vite 会看到后端断开，在终端刷一屏 ECONNREFUSED，
      日志很脏。先关前端，后端静静退出。

      ⚠️ Windows 上必须用 taskkill /T（整棵进程树）：
      npm/vite 与 uvicorn --reload 都会再 spawn 子进程，
      只杀父进程会留下孤儿，端口一直被占着。
    #>
    if ($script:Children.Count -eq 0) { return }

    # 反序：前端先关
    for ($i = $script:Children.Count - 1; $i -ge 0; $i--) {
        $child = $script:Children[$i]
        $proc = $child.Process
        if ($proc.HasExited) { continue }
        Write-Host "  停止 $($child.Label)（PID $($proc.Id)）" -ForegroundColor DarkGray
        # /T 连子进程一起，/F 强制（开发进程没有需要优雅保存的状态）
        & taskkill /PID $proc.Id /T /F 2>&1 | Out-Null
    }
    $script:Children = @()
}

function Wait-Health {
    <# 轮询 /api/health，直到通过或超时。 #>
    param([int]$Port, [int]$TimeoutSeconds = 40)
    $healthUrl = "http://127.0.0.1:$Port/api/health"
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        # 后端进程若已死，不必等满超时
        $backendProc = $script:Children | Where-Object { $_.Label -like '后端*' } |
                       Select-Object -First 1
        if ($backendProc -and $backendProc.Process.HasExited) {
            throw "后端进程已退出（退出码 $($backendProc.Process.ExitCode)）。请看上方日志。"
        }
        try {
            $resp = Invoke-WebRequest -Uri $healthUrl -TimeoutSec 2 -UseBasicParsing
            if ($resp.StatusCode -eq 200) { return }
        } catch {
            # 还没起来，继续等
        }
        Start-Sleep -Milliseconds 500
    }
    throw "后端未在 $TimeoutSeconds 秒内就绪。健康检查地址：$healthUrl"
}

# ---------------------------------------------------------------- 主流程

Write-Host "KnowledgeMap 开发启动" -ForegroundColor White
Write-Host "  项目根目录：$Root"

try {
    # ---- 1. Python ----
    Write-Step '检查 Python'
    if (-not (Test-Path $PythonExe)) {
        Write-Err "找不到 Python：$PythonExe"
        Write-Host '     设置环境变量 KM_PYTHON 指向解释器绝对路径后重试。' -ForegroundColor DarkGray
        exit 1
    }
    Write-Ok "解释器：$PythonExe"

    # ---- 2. .env ----
    Write-Step '检查 backend/.env'
    $envFile = Join-Path $Backend '.env'
    if (-not (Test-Path $envFile)) {
        Write-Warn2 '缺少 backend/.env —— 将使用默认值（root:root@127.0.0.1:3306/knowledgemap）'
        Write-Host '     可复制 backend/.env.example 为 backend/.env 并填写密钥。' -ForegroundColor DarkGray
    } else {
        Write-Ok 'backend/.env 存在'
    }

    # ---- 3. 依赖（仅 -Check）----
    if ($Check) {
        Write-Step '检查依赖（-Check）'
        $missing = & $PythonExe -c @'
import importlib.util, sys
need = ["fastapi", "uvicorn", "sqlalchemy", "pymysql", "dotenv", "pymongo"]
missing = [n for n in need if importlib.util.find_spec(n) is None]
print(" ".join(missing))
'@ 2>&1
        if ($missing) {
            Write-Err "后端缺少依赖：$missing"
            Write-Host '     pip install -r backend/requirements.txt' -ForegroundColor DarkGray
            exit 1
        }
        Write-Ok '后端依赖齐全'

        if (-not $NoFrontend) {
            if (-not (Test-Path (Join-Path $Frontend 'node_modules'))) {
                Write-Err '前端依赖未安装'
                Write-Host '     cd frontend; npm ci' -ForegroundColor DarkGray
                exit 1
            }
            Write-Ok '前端依赖已安装'
            Write-Host '  运行 vue-tsc 类型检查（可能需要十几秒）...' -ForegroundColor DarkGray
            Push-Location $Frontend
            try {
                & $NodeExe 'node_modules/vue-tsc/bin/vue-tsc.js' '--noEmit'
                if ($LASTEXITCODE -ne 0) { Write-Err '类型检查未通过'; exit 1 }
                Write-Ok '类型检查通过'
            } finally { Pop-Location }
        }
    }

    # ---- 4. 端口占用 ----
    Write-Step '检查端口'
    $ports = @()
    $ports += [pscustomobject]@{ Port = $BackendPort; What = '后端' }
    if (-not $NoFrontend) { $ports += [pscustomobject]@{ Port = $FrontendPort; What = '前端' } }

    $conflicts = @()
    foreach ($p in $ports) {
        if (Test-PortFree -Port $p.Port) {
            Write-Ok "$($p.What)端口 $($p.Port) 空闲"
        } else {
            $owner = Get-PortOwner -Port $p.Port
            $desc = if ($owner) { "PID $($owner.Pid)（$($owner.Name)）" } else { '未知进程' }
            Write-Err "$($p.What)端口 $($p.Port) 已被占用：$desc"
            $conflicts += $p
        }
    }
    if ($conflicts.Count -gt 0) {
        Write-Host ''
        Write-Host '  本脚本不会自动结束占用者——因为它可能是别的程序。请二选一：' -ForegroundColor Yellow
        Write-Host '    1) 如果是上次遗留的开发服务：  ./dev-stop.ps1' -ForegroundColor DarkGray
        Write-Host '    2) 换个端口：                  ./dev-start.ps1 -BackendPort 8011 -FrontendPort 3001' -ForegroundColor DarkGray
        exit 1
    }

    # ---- 5. 环境自检（建库 / 报告表 / 报告 Mongo）----
    Write-Step '环境自检（MySQL 数据库 / 表 / MongoDB）'
    # ⚠️ 必须设 UTF-8，否则 Python 输出的中文在 PowerShell 里是乱码
    # （Python 默认按控制台代码页 GBK 编码输出，而 pwsh 按 UTF-8 解码）。
    # 只在本次调用内生效，不影响其他步骤。
    $prevEncoding = $env:PYTHONIOENCODING
    $env:PYTHONIOENCODING = 'utf-8'
    try {
        & $PythonExe (Join-Path $Backend 'scripts/ensure_database.py')
        $selfCheck = $LASTEXITCODE
    } finally {
        $env:PYTHONIOENCODING = $prevEncoding
    }
    if ($selfCheck -ne 0) {
        Write-Err '环境自检未通过，已停止启动。'
        exit 1
    }

    # ---- 6/7. 注入端口并启动 ----
    # ⚠️ 端口只在这里决定一次。后端读 KM_BACKEND_PORT，前端读 KM_API_TARGET，
    #    两边同源，不可能不一致。
    $env:KM_BACKEND_PORT = "$BackendPort"
    $env:KM_API_TARGET   = "http://127.0.0.1:$BackendPort"

    Write-Step "启动后端（端口 $BackendPort）"
    # 相对路径按 backend/ 解析，便于 `-BackendEntry main_dev.py` 这类写法。
    $entryPath = if ([System.IO.Path]::IsPathRooted($BackendEntry)) { $BackendEntry }
                 else { Join-Path $Backend $BackendEntry }
    if (-not (Test-Path $entryPath)) {
        Write-Err "后端入口不存在：$entryPath"
        exit 1
    }
    Start-Child -FilePath $PythonExe -Arguments @($entryPath) `
        -WorkingDirectory $Backend -Label "后端(:$BackendPort)" | Out-Null

    Write-Host '  等待后端就绪...' -ForegroundColor DarkGray
    Wait-Health -Port $BackendPort
    Write-Ok "后端就绪：http://127.0.0.1:$BackendPort/docs"

    if (-not $NoFrontend) {
        Write-Step "启动前端（端口 $FrontendPort，代理 → $env:KM_API_TARGET）"
        Start-Child -FilePath $NodeExe `
            -Arguments @('node_modules/vite/bin/vite.js', '--port', "$FrontendPort", '--host', '127.0.0.1') `
            -WorkingDirectory $Frontend -Label "前端(:$FrontendPort)" | Out-Null
    }

    # ---- 8. 前台守候 ----
    Write-Host ''
    Write-Host '──────────────────────────────────────────────' -ForegroundColor DarkGray
    if (-not $NoFrontend) {
        Write-Host "  页面：  http://127.0.0.1:$FrontendPort/" -ForegroundColor White
    }
    Write-Host "  接口：  http://127.0.0.1:$BackendPort/docs" -ForegroundColor White
    Write-Host '  停止：  在本终端按 Ctrl+C（前后端会一起停）' -ForegroundColor White
    Write-Host '──────────────────────────────────────────────' -ForegroundColor DarkGray
    Write-Host ''

    # 守候循环：任一子进程退出就结束（例如后端崩了），不必让你盯着一个半死的会话。
    while ($true) {
        Start-Sleep -Milliseconds 700
        foreach ($child in $script:Children) {
            if ($child.Process.HasExited) {
                Write-Warn2 "$($child.Label) 已退出（退出码 $($child.Process.ExitCode)），正在停止其余进程。"
                return   # 走 finally 统一收摊
            }
        }
    }
}
catch {
    # ⚠️ 统一在这里把异常变成**一句可读的话**，而不是让 PowerShell 打出
    # 一大段 Exception 堆栈——那种输出对排障没有帮助，只让人以为脚本坏了。
    # 真正的诊断信息（后端日志等）已经在上面正常打印过了。
    Write-Host ''
    Write-Err $_.Exception.Message
    $script:ExitCode = 1
}
finally {
    Write-Host ''
    Write-Step '收摊'
    Stop-AllChildren
    Write-Ok '已停止'
}

exit $script:ExitCode
