<#
.SYNOPSIS
    KnowledgeMap 开发服务停止 / 状态查看（Windows 11 / PowerShell 7+）。

.DESCRIPTION
    对应文档：docs/15_开发启动脚本方案.md「§4 结束方式（决策 3）」/「§4.5 不杀"看起来不是本项目"的进程」。

    **这是"备选项"，不是日常主线。** 正常结束开发用 dev-start.ps1 那个终端的
    Ctrl+C 就够（它会把前后端一起干净收掉）。本脚本用于两种情况：

      1. 终端窗口被误关 / 进程残留 —— 这时 Ctrl+C 已经没机会按了；
      2. 想知道"现在到底有什么在跑" —— 用 -Status，它**只读**。

    用户 2026-10-08 明确要求：**专门杀端口，不用 PID 文件**。
    理由很实际——PID 会随着进程反复拉起而变个不停，
    基于 PID 的记录（或缓存）很快就会过期，过期后可能杀到无关进程。
    端口是这个项目里更稳定的"身份"。

.PARAMETER Status
    只查看状态，**不结束任何进程**。建议先跑这个。

.PARAMETER BackendPort
    后端端口，默认 8010。与 dev-start.ps1 的默认值一致。

.PARAMETER FrontendPort
    前端端口，默认 3000。

.PARAMETER Force
    对**不属于本项目**的占用者也结束。默认遇到这种情况会跳过并警告——
    因为杀掉一个不相关的程序是事故，而不是"清理"。

.EXAMPLE
    ./dev-stop.ps1 -Status
    看现在什么在跑（最安全，先跑这个）。

.EXAMPLE
    ./dev-stop.ps1
    结束 3000 / 8010 上的服务。

.EXAMPLE
    ./dev-stop.ps1 -BackendPort 8011 -FrontendPort 3001
    结束换过端口的会话。
#>

[CmdletBinding()]
param(
    [switch]$Status,
    [int]$BackendPort = 8010,
    [int]$FrontendPort = 3000,
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

function Write-Ok    { param([string]$T) Write-Host "  [OK] $T" -ForegroundColor Green }
function Write-Warn2 { param([string]$T) Write-Host "  [--] $T" -ForegroundColor Yellow }
function Write-Err   { param([string]$T) Write-Host "  [!!] $T" -ForegroundColor Red }
function Write-Step  { param([string]$T) Write-Host "`n==> $T" -ForegroundColor Cyan }

function Get-PortListener {
    <# 返回监听某端口的进程；没有则 $null。 #>
    param([int]$Port)
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
            Select-Object -First 1
    if (-not $conn) { return $null }
    $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue

    # ⚠️ 进程可能**刚刚退出**（TCP 连接还没被 OS 回收，Get-Process 已拿不到）。
    # 这时它不是"别人的进程"，只是正在消失——必须单独识别，
    # 否则会打印"已跳过：不属于本项目"这种**误导性警告**
    # （实测踩到：dev-start 的 finally 已在关前端，dev-stop 随后看到它的残留连接）。
    if (-not $proc) {
        return [pscustomobject]@{
            Port = $Port; Pid = $conn.OwningProcess; Name = '(正在退出)'
            Command = $null; IsOurs = $true; Vanishing = $true
        }
    }

    # 命令行用于判断"它是不是本项目的进程"——只靠进程名（node/python）不够，
    # 因为机器上可能同时跑着别的 Node/Python 项目。
    $cmdline = $null
    try {
        $cmdline = (Get-CimInstance Win32_Process -Filter "ProcessId = $($conn.OwningProcess)" `
                    -ErrorAction SilentlyContinue).CommandLine
    } catch { }

    # ⚠️ 判断"是不是我们启的"只看**命令行**，因为 `dev-start.ps1` 启动前端时用的是
    # 相对路径（`node_modules/vite/bin/vite.js`），命令行里没有项目根目录——
    # 一开始只匹配项目路径，结果把**自己刚启的前端认成别人的**（实测踩到）。
    # 因此按入口特征匹配：
    #   后端 → python 跑 `main.py`；前端 → node 跑 `node_modules/vite/bin/vite.js`
    $isOurs = $false
    if ($cmdline) {
        if ($cmdline -like "*$Root*") { $isOurs = $true }          # 绝对路径启动
        elseif ($cmdline -like '*main.py*') { $isOurs = $true }     # 后端入口
        elseif ($cmdline -like '*vite*') { $isOurs = $true }        # 前端 dev server
    }
    return [pscustomobject]@{
        Port    = $Port
        Pid     = $conn.OwningProcess
        Name    = if ($proc) { $proc.ProcessName } else { '(已退出)' }
        Command = $cmdline
        IsOurs  = $isOurs
        Vanishing = $false
    }
}

function Show-Status {
    param([int[]]$Ports)
    Write-Step '当前状态'
    $any = $false
    foreach ($port in $Ports) {
        $owner = Get-PortListener -Port $port
        if (-not $owner) {
            Write-Host "  端口 $port ：空闲" -ForegroundColor DarkGray
            continue
        }
        $any = $true
        if ($owner.Vanishing) {
            Write-Host "  端口 $port ：进程正在退出（PID $($owner.Pid)）" -ForegroundColor DarkGray
            continue
        }
        $tag = if ($owner.IsOurs) { '本项目' } else { '**非本项目**' }
        Write-Host "  端口 $port ：PID $($owner.Pid)  $($owner.Name)  [$tag]"
        if ($owner.Command) {
            # 命令行可能很长，截断显示
            $short = if ($owner.Command.Length -gt 110) {
                $owner.Command.Substring(0, 110) + '...'
            } else { $owner.Command }
            Write-Host "               $short" -ForegroundColor DarkGray
        }
    }

    # Mongo 与 MySQL 只报告，不碰（它们是系统服务，不属于本脚本管）
    Write-Host ''
    $mongo = Get-Service -Name 'MongoDB' -ErrorAction SilentlyContinue
    if ($mongo) {
        $color = if ($mongo.Status -eq 'Running') { 'DarkGray' } else { 'Yellow' }
        Write-Host "  MongoDB 服务：$($mongo.Status)（$($mongo.StartType)）" -ForegroundColor $color
    } else {
        Write-Host '  MongoDB 服务：未安装' -ForegroundColor DarkGray
    }
    $mysql = Get-Service | Where-Object { $_.Name -match '^MySQL' } | Select-Object -First 1
    if ($mysql) {
        Write-Host "  MySQL 服务：$($mysql.Name) - $($mysql.Status)" -ForegroundColor DarkGray
    }

    if (-not $any) { Write-Host ''; Write-Ok '没有本项目的开发服务在运行。' }
    return $any
}

# ---------------------------------------------------------------- 主流程

$ports = @($BackendPort, $FrontendPort)

if ($Status) {
    Show-Status -Ports $ports | Out-Null
    exit 0
}

Write-Host 'KnowledgeMap 开发服务停止' -ForegroundColor White
$running = Show-Status -Ports $ports
if (-not $running) { exit 0 }

Write-Step '结束进程'
$killed = 0
$skipped = 0

foreach ($port in $ports) {
    $owner = Get-PortListener -Port $port
    if (-not $owner) { continue }

    if ($owner.Vanishing) {
        # 进程正在退出、只是 TCP 连接还没被回收：不是"别人的进程"，也不是需要杀的目标。
        Write-Host "  端口 $port 上的进程正在退出，无需处理" -ForegroundColor DarkGray
        continue
    }

    if (-not $owner.IsOurs -and -not $Force) {
        # ⚠️ 默认不杀"看起来不是本项目"的进程。
        # 进程命令行里不含项目特征，说明它多半是别的程序——
        # 杀掉它是事故，不是清理。
        Write-Warn2 "端口 $port 上的 PID $($owner.Pid)（$($owner.Name)）命令行不含本项目特征，已跳过"
        Write-Host "       确认要结束它请加 -Force" -ForegroundColor DarkGray
        $skipped++
        continue
    }

    Write-Host "  结束端口 $port 上的 PID $($owner.Pid)（$($owner.Name)）" -ForegroundColor DarkGray
    # /T 连子进程一起杀：Vite 与 uvicorn --reload 都会再 spawn 子进程，
    # 只杀父进程会留下孤儿，端口一直被占着（这是 Windows 上最常见的"杀不干净"）。
    & taskkill /PID $owner.Pid /T /F 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) { $killed++ } else { Write-Err "结束 PID $($owner.Pid) 失败" }
}

Start-Sleep -Milliseconds 800   # 给 OS 一点时间释放端口

Write-Host ''
if ($killed -gt 0) { Write-Ok "已结束 $killed 个进程" }
if ($skipped -gt 0) {
    Write-Warn2 "跳过 $skipped 个（不属于本项目；如确需结束请加 -Force）"
}

# 复核：端口真的空了吗（TIME_WAIT 不算占用，所以用绑定测试）
Write-Step '复核'
foreach ($port in $ports) {
    $listener = $null
    $free = $false
    try {
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $port)
        $listener.Start()
        $free = $true
    } catch {
        $free = $false
    } finally {
        if ($listener) { $listener.Stop() }
    }
    if ($free) { Write-Ok "端口 $port 已释放" } else { Write-Warn2 "端口 $port 仍被占用" }
}
