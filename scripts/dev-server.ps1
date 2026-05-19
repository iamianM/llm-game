param(
    [ValidateSet("start", "stop", "restart", "status")]
    [string]$Action = "status"
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$ApiUrl = "http://127.0.0.1:8000/healthz"
$WebUrl = "http://127.0.0.1:3001"
$ApiOut = Join-Path $Root ".api-dev.log"
$ApiErr = Join-Path $Root ".api-dev.err"
$WebOut = Join-Path $Root ".web-dev.log"
$WebErr = Join-Path $Root ".web-dev.err"

function Get-ListenerPids([int]$Port) {
    @(Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
        Where-Object { $_.State -eq "Listen" } |
        Select-Object -ExpandProperty OwningProcess -Unique)
}

function Test-Url([string]$Url) {
    try {
        $null = Invoke-WebRequest -UseBasicParsing $Url -TimeoutSec 5
        return $true
    }
    catch {
        return $false
    }
}

function Wait-Url([string]$Url, [int]$Seconds) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-Url $Url) {
            return $true
        }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

function Get-ManagedProcesses {
    $rootText = [string]$Root
    @(Get-CimInstance Win32_Process |
        Where-Object {
            $_.ProcessId -ne $PID -and
            $_.CommandLine -and
            $_.CommandLine.Contains($rootText) -and
            ($_.CommandLine -match "uvicorn src\.api\.app:app|npm.*run dev|next.*dev|start-server\.js")
        })
}

function Stop-DevServers {
    $pids = @()
    $pids += Get-ListenerPids 3001
    $pids += Get-ListenerPids 8000
    $pids += Get-ManagedProcesses | Select-Object -ExpandProperty ProcessId
    $pids = @($pids | Where-Object { $_ -and $_ -ne $PID } | Sort-Object -Unique)

    if ($pids.Count -eq 0) {
        Write-Host "No Paradise Hearts dev servers are running."
        return
    }

    foreach ($processId in $pids) {
        try {
            Stop-Process -Id $processId -Force -ErrorAction Stop
            Write-Host "Stopped process $processId"
        }
        catch {
            Write-Host "Process $processId was already stopped."
        }
    }
}

function Start-Api {
    if ((Get-ListenerPids 8000).Count -gt 0) {
        Write-Host "API already listening on http://127.0.0.1:8000"
        return
    }
    $process = Start-Process -FilePath "uv" `
        -ArgumentList @("run", "python", "-m", "uvicorn", "src.api.app:app", "--host", "127.0.0.1", "--port", "8000") `
        -WorkingDirectory $Root `
        -RedirectStandardOutput $ApiOut `
        -RedirectStandardError $ApiErr `
        -WindowStyle Hidden `
        -PassThru
    Write-Host "Started API process $($process.Id)"
}

function Start-Web {
    if ((Get-ListenerPids 3001).Count -gt 0) {
        Write-Host "Web already listening on http://127.0.0.1:3001"
        return
    }
    $npmCommand = Get-Command "npm.cmd" -ErrorAction SilentlyContinue
    if ($npmCommand) {
        $npm = $npmCommand.Source
    }
    else {
        $npm = (Get-Command "npm" -ErrorAction Stop).Source
    }
    $process = Start-Process -FilePath $npm `
        -ArgumentList @("run", "dev", "--", "--hostname", "127.0.0.1", "--port", "3001") `
        -WorkingDirectory (Join-Path $Root "web") `
        -RedirectStandardOutput $WebOut `
        -RedirectStandardError $WebErr `
        -WindowStyle Hidden `
        -PassThru
    Write-Host "Started web process $($process.Id)"
}

function Start-DevServers {
    Start-Api
    if (-not (Wait-Url $ApiUrl 30)) {
        Write-Host "API did not become healthy. See $ApiErr"
        exit 1
    }

    Start-Web
    if (-not (Wait-Url $WebUrl 60)) {
        Write-Host "Web app did not become ready. See $WebErr"
        exit 1
    }

    Write-Host "Paradise Hearts is running:"
    Write-Host "  UI:  $WebUrl"
    Write-Host "  API: http://127.0.0.1:8000"
}

function Show-Status {
    $apiPids = Get-ListenerPids 8000
    $webPids = Get-ListenerPids 3001
    $apiState = if ((Test-Url $ApiUrl)) { "healthy" } elseif ($apiPids.Count -gt 0) { "listening, unhealthy" } else { "down" }
    $webState = if ((Test-Url $WebUrl)) { "ready" } elseif ($webPids.Count -gt 0) { "listening, not ready" } else { "down" }

    Write-Host "Paradise Hearts dev server status"
    Write-Host "  API 8000: $apiState $(if ($apiPids.Count -gt 0) { '(pid ' + ($apiPids -join ', ') + ')' })"
    Write-Host "  UI  3001: $webState $(if ($webPids.Count -gt 0) { '(pid ' + ($webPids -join ', ') + ')' })"
}

switch ($Action) {
    "start" { Start-DevServers }
    "stop" { Stop-DevServers }
    "restart" {
        Stop-DevServers
        Start-Sleep -Seconds 2
        Start-DevServers
    }
    "status" { Show-Status }
}
