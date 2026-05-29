param(
    [ValidateSet("start", "stop", "restart", "status")]
    [string]$Action = "status",

    [ValidateSet("local", "tailscale")]
    [string]$Network = "local"
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$ApiHealthUrl = "http://127.0.0.1:8000/healthz"
$ApiListenHost = if ($Network -eq "tailscale") { "0.0.0.0" } else { "127.0.0.1" }
$WebListenHost = if ($Network -eq "tailscale") { "0.0.0.0" } else { "127.0.0.1" }
$PublicHost = "127.0.0.1"
$ApiUrl = "http://127.0.0.1:8000"
$WebUrl = "http://127.0.0.1:3001"
$ApiOut = Join-Path $Root ".api-dev.log"
$ApiErr = Join-Path $Root ".api-dev.err"
$WebOut = Join-Path $Root ".web-dev.log"
$WebErr = Join-Path $Root ".web-dev.err"

function Import-LocalEnv {
    $envPath = Join-Path $Root ".env.local"
    if (-not (Test-Path $envPath)) {
        return
    }

    Get-Content $envPath | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) {
            return
        }
        $separator = $line.IndexOf("=")
        if ($separator -lt 1) {
            return
        }
        $key = $line.Substring(0, $separator).Trim()
        $value = $line.Substring($separator + 1).Trim().Trim('"').Trim("'")
        if (-not [Environment]::GetEnvironmentVariable($key, "Process")) {
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
}

function Initialize-LlmSettings {
    Import-LocalEnv
    $hasOpenAiKey = -not [string]::IsNullOrWhiteSpace($env:OPENAI_API_KEY)
    if ($hasOpenAiKey -and [string]::IsNullOrWhiteSpace($env:PARADISE_MOCK_LLM)) {
        $env:PARADISE_MOCK_LLM = "0"
    }
    $liveByDefault = $hasOpenAiKey -and $env:PARADISE_MOCK_LLM -eq "0"
    $env:NEXT_PUBLIC_DEFAULT_LIVE_LLM = if ($liveByDefault) { "1" } else { "0" }
}

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

function Test-WebApp([string]$Url) {
    try {
        $response = Invoke-WebRequest -UseBasicParsing $Url -TimeoutSec 5
        return $response.StatusCode -eq 200 -and $response.Content.Contains("Paradise Hearts")
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

function Get-TailscaleCommand {
    $cmd = Get-Command "tailscale" -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }
    $installed = Join-Path $env:ProgramFiles "Tailscale\tailscale.exe"
    if (Test-Path $installed) {
        return $installed
    }
    return $null
}

function Get-TailscaleIPv4 {
    $tailscale = Get-TailscaleCommand
    if (-not $tailscale) {
        Write-Host "Tailscale CLI is not installed. Install Tailscale, sign in, then rerun with -Network tailscale."
        exit 1
    }
    $ip = (& $tailscale ip -4 2>$null | Select-Object -First 1)
    if (-not $ip) {
        Write-Host "Tailscale is installed but not logged in yet."
        Write-Host "Run: `"$tailscale`" up"
        exit 1
    }
    return [string]$ip
}

function Initialize-NetworkSettings {
    if ($Network -ne "tailscale") {
        return
    }
    $script:PublicHost = Get-TailscaleIPv4
    $script:ApiUrl = "http://$($script:PublicHost):8000"
    $script:WebUrl = "http://$($script:PublicHost):3001"
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
        if ($Network -eq "tailscale" -and -not (Test-Url "$ApiUrl/healthz")) {
            Write-Host "API is listening on localhost only; restarting it for Tailscale access."
            Get-ListenerPids 8000 | ForEach-Object {
                Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
            }
            Start-Sleep -Seconds 1
        }
        else {
            Write-Host "API already listening on http://127.0.0.1:8000"
            return
        }
    }
    $process = Start-Process -FilePath "uv" `
        -ArgumentList @("run", "python", "-m", "uvicorn", "src.api.app:app", "--host", $ApiListenHost, "--port", "8000") `
        -WorkingDirectory $Root `
        -RedirectStandardOutput $ApiOut `
        -RedirectStandardError $ApiErr `
        -WindowStyle Hidden `
        -PassThru
    Write-Host "Started API process $($process.Id)"
}

function Start-Web {
    if ((Get-ListenerPids 3001).Count -gt 0) {
        if (Test-WebApp $WebUrl) {
            Write-Host "Web already serving Paradise Hearts on http://127.0.0.1:3001"
            return
        }
        Write-Host "Port 3001 is occupied but is not serving Paradise Hearts. Run scripts/dev-server.ps1 restart after freeing the port, or use Playwright's isolated port 3210."
        exit 1
    }
    $npmCommand = Get-Command "npm.cmd" -ErrorAction SilentlyContinue
    if ($npmCommand) {
        $npm = $npmCommand.Source
    }
    else {
        $npm = (Get-Command "npm" -ErrorAction Stop).Source
    }
    $env:NEXT_DIST_DIR = ".next-dev"
    $env:NEXT_PUBLIC_API_BASE = $ApiUrl
    $process = Start-Process -FilePath $npm `
        -ArgumentList @("run", "dev", "--", "--hostname", $WebListenHost, "--port", "3001") `
        -WorkingDirectory (Join-Path $Root "web") `
        -RedirectStandardOutput $WebOut `
        -RedirectStandardError $WebErr `
        -WindowStyle Hidden `
        -PassThru
    Remove-Item Env:\NEXT_DIST_DIR -ErrorAction SilentlyContinue
    Remove-Item Env:\NEXT_PUBLIC_API_BASE -ErrorAction SilentlyContinue
    Write-Host "Started web process $($process.Id)"
}

function Start-DevServers {
    Initialize-LlmSettings
    Initialize-NetworkSettings
    Start-Api
    if (-not (Wait-Url $ApiHealthUrl 30)) {
        Write-Host "API did not become healthy. See $ApiErr"
        exit 1
    }

    Start-Web
    if (-not (Wait-Url $WebUrl 60) -or -not (Test-WebApp $WebUrl)) {
        Write-Host "Web app did not become ready. See $WebErr"
        exit 1
    }

    Write-Host "Paradise Hearts is running:"
    Write-Host "  UI:  $WebUrl"
    Write-Host "  API: $ApiUrl"
    Write-Host "  Story engine default: $(if ($env:NEXT_PUBLIC_DEFAULT_LIVE_LLM -eq '1') { 'Live LLM' } else { 'Demo/mock' })"
    if ($Network -eq "tailscale") {
        Write-Host "  Local UI: http://127.0.0.1:3001"
        Write-Host "  Local API: http://127.0.0.1:8000"
    }
}

function Show-Status {
    Initialize-LlmSettings
    Initialize-NetworkSettings
    $apiPids = Get-ListenerPids 8000
    $webPids = Get-ListenerPids 3001
    $apiProbe = if ($Network -eq "tailscale") { "$ApiUrl/healthz" } else { $ApiHealthUrl }
    $apiState = if ((Test-Url $apiProbe)) { "healthy" } elseif ($apiPids.Count -gt 0) { "listening, unreachable at $apiProbe" } else { "down" }
    $webState = if ((Test-WebApp $WebUrl)) { "ready" } elseif ((Test-Url $WebUrl)) { "responding, wrong app" } elseif ($webPids.Count -gt 0) { "listening, not ready" } else { "down" }

    Write-Host "Paradise Hearts dev server status"
    Write-Host "  Network: $Network"
    Write-Host "  API 8000: $apiState $ApiUrl $(if ($apiPids.Count -gt 0) { '(pid ' + ($apiPids -join ', ') + ')' })"
    Write-Host "  UI  3001: $webState $WebUrl $(if ($webPids.Count -gt 0) { '(pid ' + ($webPids -join ', ') + ')' })"
    Write-Host "  Story engine default: $(if ($env:NEXT_PUBLIC_DEFAULT_LIVE_LLM -eq '1') { 'Live LLM' } else { 'Demo/mock' })"
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
