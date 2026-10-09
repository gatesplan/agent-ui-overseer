# Overseer 서버를 다시 띄운다. 패널 탭 안의 에이전트도 쓸 수 있다
#   pwsh scripts/restart_server.ps1           재시작을 예약하고 바로 끝난다. 진행은 ~/.overseer/logs/restart.log
#   pwsh scripts/restart_server.ps1 -DryRun   멈추지 않고 탭, 서버 프로세스, 시작 방식만 점검해 기록한다
#   pwsh scripts/restart_server.ps1 -WhileStopped scripts/migrate_item_ids.py   멈춘 동안 그 파이썬 스크립트를 돌린다(DB 이전 등)
#
# 패널 탭 안에서 부른 프로세스는 서버를 멈출 때 같이 죽는다. 그래서 WMI 로 서버와 무관한 프로세스를 띄워 거기서 한다(-Detached)
# 순서: 모든 탭이 working/attention 이 아닐 때까지 기다린다(최대 10분) → 멈춘다 → 다시 띄운다 → 떠 있던 탭을 이어서 띄운다
# 작업 스케줄러에 Overseer 작업이 있으면 그것으로 멈추고 띄운다. 없으면 프로세스를 끝내고 `uv run overseer` 를 창 없이 띄운다
# WMI 로 띄운 프로세스에서는 CIM 호출이 실패하므로 그쪽에서는 CIM 을 쓰지 않는다(netstat, Get-Process, schtasks)
param([switch]$DryRun, [switch]$Detached, [int]$Port = 47310, [string]$WhileStopped = '')
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
# 이 컴퓨터의 패널 기록 폴더. 서버 기본값과 같다(OVERSEER_DATA, 없으면 ~/.overseer). WMI 로 띄운 쪽은 환경변수를 물려받지 않아 ~/.overseer
$data = if ($env:OVERSEER_DATA) { $env:OVERSEER_DATA } else { Join-Path $HOME '.overseer' }
New-Item -ItemType Directory -Force (Join-Path $data 'logs') | Out-Null
$log = Join-Path $data 'logs\restart.log'
$api = "http://127.0.0.1:$Port/api/tabs"
$task = 'Overseer'

if (-not $Detached) {
    $pwsh = (Get-Process -Id $PID).Path
    $run = if ($WhileStopped) { " -WhileStopped `"$WhileStopped`"" } else { '' }
    $cmd = "`"$pwsh`" -NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$PSCommandPath`" -Detached -Port $Port$(if ($DryRun) { ' -DryRun' })$run"
    $r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $root }
    if ($r.ReturnValue -ne 0) { Write-Error "재시작 프로세스를 띄우지 못함: $($r.ReturnValue)"; exit 1 }
    Write-Output "$(if ($DryRun) { '점검' } else { '재시작' }) 예약됨(PID $($r.ProcessId)). 진행: $log"
    exit 0
}

function Log($m) { Add-Content -Path $log -Value "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $(if ($DryRun) { '[점검] ' })$m" -Encoding utf8 }

function Tabs {
    $raw = (Invoke-WebRequest $api -UseBasicParsing -TimeoutSec 5).Content
    $tabs = @($raw | ConvertFrom-Json)
    if ($tabs.Count -and -not $tabs[0].id) { throw "탭 목록을 읽지 못함: $($raw.Substring(0, [Math]::Min(200, $raw.Length)))" }
    return $tabs
}

function Up { try { Invoke-WebRequest $api -UseBasicParsing -TimeoutSec 3 | Out-Null; return $true } catch { return $false } }

function ServerPid {
    $line = netstat -ano | Select-String "127\.0\.0\.1:$Port\s+\S+\s+LISTENING\s+(\d+)" | Select-Object -First 1
    if ($line) { return [int]$line.Matches[0].Groups[1].Value }
}

# 서버를 띄운 맨 위 프로세스. uv run 이면 uv → overseer → python, 작업 스케줄러면 pythonw → pythonw
function ServerRoot($id) {
    $p = Get-Process -Id $id
    while ($p.Parent -and $p.Parent.ProcessName -match '^(python|pythonw|overseer|uv)$') { $p = $p.Parent }
    return $p.Id
}

function Descendants($top) {
    $all = Get-Process | ForEach-Object { [pscustomobject]@{ Id = $_.Id; Parent = $_.Parent.Id } }
    $ids = @($top); $i = 0
    while ($i -lt $ids.Count) { $ids += @($all | Where-Object { $_.Parent -eq $ids[$i] } | ForEach-Object Id); $i++ }
    return $ids
}

function HasTask { schtasks /Query /TN $task 2>$null | Out-Null; return $LASTEXITCODE -eq 0 }

function StartServer {
    if (HasTask) { schtasks /Run /TN $task | Out-Null }
    else { Start-Process -FilePath 'uv' -ArgumentList 'run', 'overseer', '--port', $Port -WorkingDirectory $root -WindowStyle Hidden }
}

try {
    Log '재시작 대기 시작'
    $deadline = (Get-Date).AddMinutes(10)
    while (-not $DryRun) {
        Start-Sleep 3
        $busy = @(Tabs | Where-Object { $_.status -in 'working', 'attention' })
        if (-not $busy.Count) { break }
        if ((Get-Date) -gt $deadline) { Log "작업 중인 탭이 있어 그만둠: $(($busy | ForEach-Object { $_.id }) -join ',')"; exit 1 }
    }
    # 부른 에이전트의 마지막 응답 카드가 화면에 그려질 틈
    if (-not $DryRun) { Start-Sleep 5 }
    $tabs = Tabs
    $alive = @($tabs | Where-Object { $_.alive } | ForEach-Object { $_.id })
    Log "탭: $(($tabs | ForEach-Object { "$($_.id)=$($_.status)" }) -join ', ') / 떠 있던 탭: $($alive -join ',')"

    $server = ServerPid
    if (-not $server) { throw "포트 $Port 에 서버가 없다" }
    $top = ServerRoot $server
    $tree = Descendants $top
    $byTask = HasTask
    Log "서버 $server, 맨 위 프로세스 $top, 정리 대상 $($tree.Count)개, 시작 방식 $(if ($byTask) { "작업 스케줄러 $task" } else { 'uv run overseer' })"
    if ($DryRun) { Log '점검 끝'; exit 0 }

    if ($byTask) { schtasks /End /TN $task | Out-Null; Start-Sleep 3 }
    foreach ($id in $tree) { if (Get-Process -Id $id -ErrorAction SilentlyContinue) { Stop-Process -Id $id -Force -ErrorAction SilentlyContinue } }
    for ($i = 0; $i -lt 15 -and (ServerPid); $i++) { Start-Sleep 1 }
    Log '멈춤'
    # 실패해도 서버는 다시 띄운다. 결과는 로그로 본다
    if ($WhileStopped) {
        $out = (& uv run --project $root python (Join-Path $root $WhileStopped) 2>&1 | Out-String).Trim()
        Log "$WhileStopped 실행(종료코드 $LASTEXITCODE): $out"
    }

    for ($try = 1; $try -le 3; $try++) {
        StartServer
        for ($i = 0; $i -lt 30 -and -not (Up); $i++) { Start-Sleep 2 }
        if (Up) { break }
        Log "시작 응답 없음 ($try)"
        if ($byTask) { schtasks /End /TN $task | Out-Null }
        Start-Sleep 3
    }
    if (-not (Up)) { Log '시작 실패'; exit 2 }
    Log "시작됨 (서버 $(ServerPid))"

    foreach ($id in $alive) {
        try { Invoke-WebRequest -Method Post "$api/$id/resume" -ContentType 'application/json' -Body '{}' -UseBasicParsing -TimeoutSec 30 | Out-Null; Log "이어서 띄움: $id" }
        catch { Log "이어서 띄우기 실패: $id $_" }
    }
    Log '완료'
} catch {
    Log "오류: $_"
    # 멈춘 뒤 오류가 났으면 서버만이라도 다시 띄운다
    if (-not $DryRun -and -not (Up)) { StartServer; Log '오류 뒤 시작 시도' }
}
