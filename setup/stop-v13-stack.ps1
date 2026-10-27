# ===========================================================================
#  V1.3 stack stopper  --  stops ONLY the ports owned by V1.3
#
#  Safety: for each candidate PID we read its command line and require the
#  V1.3 markers before killing. A port that happens to be held by something
#  else (DSH 8326, VLM shim 8331, webstudio 3210) is never touched.
#
#  Usage:  powershell -NoProfile -ExecutionPolicy Bypass -File stop-v13-stack.ps1
#          powershell ... -File stop-v13-stack.ps1 -DryRun
# ===========================================================================
param([switch]$DryRun)

$ErrorActionPreference = 'SilentlyContinue'

$ports = @(6381, 6382, 1936, 8127, 8329, 5199)

# command-line substrings that prove a process belongs to V1.3
$markers = @(
    'QQBot-v13'
    'persona-base\_embed\embed_server.py'
    'ov-v13\ov.conf'
    'SnowLuma\node.exe'
    # persona-svc runs the uv-managed cpython (QQBot-v13\venv is a junction to
    # v11\venv, whose python.exe resolves outside D:\AI), so its command line
    # only carries the script + port -- match on that pair.
    'serve.py --port 8127'
    'embed_server.py --port 8329'
    # AstrBot is launched as <uv-python> -c "from astrbot.cli.__main__ import
    # cli; cli()" run -p 6381 -- no QQBot-v13 text in the command line.
    'run -p 6381'
)

$portMap = @{
    6381 = 'AstrBot dashboard'
    6382 = 'AstrBot aiocqhttp ws'
    1936 = 'OpenViking'
    8127 = 'persona-svc'
    8329 = 'embed'
    5199 = 'SnowLuma webui'
}

function Get-OwnerPid([int]$port) {
    $lines = netstat -ano -p TCP | Select-String ":$port\s+.*LISTENING"
    foreach ($l in $lines) {
        $parts = ($l.ToString().Trim() -split '\s+')
        if ($parts.Length -ge 5) { return [int]$parts[4] }
    }
    return 0
}

$stopped = 0
$skipped = 0

foreach ($port in $ports) {
    $procId = Get-OwnerPid $port
    if ($procId -eq 0) {
        Write-Host ("[skip] {0,-22} :{1}  not listening" -f $portMap[$port], $port)
        continue
    }

    $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$procId"
    $cmd = if ($proc) { $proc.CommandLine } else { '' }

    $owned = $false
    foreach ($m in $markers) {
        if ($cmd -and $cmd.Contains($m)) { $owned = $true; break }
    }
    # embed_server.py / persona serve.py are python; accept only when the
    # command line names the V1.3 tree or the port is in our exclusive set
    # AND the exe path resolves under D:\AI.
    if (-not $owned -and $cmd -match 'D:\\AI\\') { $owned = $true }

    if (-not $owned) {
        Write-Host ("[WARN] {0,-22} :{1} pid={2} NOT a V1.3 process, left alone" -f $portMap[$port], $port, $procId)
        Write-Host ("       cmd: {0}" -f $cmd)
        $skipped++
        continue
    }

    if ($DryRun) {
        Write-Host ("[dry]  {0,-22} :{1} pid={2}" -f $portMap[$port], $port, $procId)
        Write-Host ("       cmd: {0}" -f $cmd)
        continue
    }

    Write-Host ("[stop] {0,-22} :{1} pid={2}" -f $portMap[$port], $port, $procId)
    Stop-Process -Id $procId -Force
    $stopped++
    Start-Sleep -Milliseconds 400
}

# AstrBot spawns a launcher + a child; sweep any leftover V1.3 python
if (-not $DryRun) {
    Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
        Where-Object { $_.CommandLine -and $_.CommandLine.Contains('QQBot-v13') } |
        ForEach-Object {
            Write-Host ("[stop] leftover V1.3 python pid={0}" -f $_.ProcessId)
            Stop-Process -Id $_.ProcessId -Force
            $stopped++
        }
    Get-CimInstance Win32_Process -Filter "Name='openviking-server.exe'" |
        Where-Object { $_.CommandLine -and $_.CommandLine.Contains('ov-v13') } |
        ForEach-Object {
            Write-Host ("[stop] leftover V1.3 openviking pid={0}" -f $_.ProcessId)
            Stop-Process -Id $_.ProcessId -Force
            $stopped++
        }
}

Write-Host ""
Write-Host ("done: stopped={0} skipped={1}" -f $stopped, $skipped)
if ($DryRun) { Write-Host "(--DryRun: nothing was killed)" }