param(
    [int]$Port = 8000,
    [int]$MaxPort = 8010,
    [switch]$NoBrowser,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Get-AppContext {
    param([int]$CheckPort)

    try {
        return Invoke-RestMethod -Uri "http://127.0.0.1:$CheckPort/api/context" -TimeoutSec 2
    }
    catch {
        return $null
    }
}

function Test-PortBusy {
    param([int]$CheckPort)

    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $connect = $client.BeginConnect("127.0.0.1", $CheckPort, $null, $null)
        $connected = $connect.AsyncWaitHandle.WaitOne(300, $false)
        if ($connected) {
            $client.EndConnect($connect)
            return $true
        }
        return $false
    }
    catch {
        return $false
    }
    finally {
        $client.Close()
    }
}

function Find-FreePort {
    param(
        [int]$StartPort,
        [int]$EndPort
    )

    for ($candidate = $StartPort; $candidate -le $EndPort; $candidate++) {
        if (-not (Test-PortBusy -CheckPort $candidate)) {
            return $candidate
        }
    }
    return $null
}

function Open-Dashboard {
    param([string]$Url)

    if (-not $NoBrowser) {
        Start-Process $Url
    }
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

$selectedPort = $Port
$existingContext = Get-AppContext -CheckPort $selectedPort

if ($existingContext -and $existingContext.runtime -and $existingContext.agent_operations) {
    $url = "http://127.0.0.1:$selectedPort"
    Write-Host "AI Project Manager is already running on $url"
    Write-Host "Runtime version: $($existingContext.runtime.version)"
    Open-Dashboard -Url $url
    exit 0
}

if (Test-PortBusy -CheckPort $selectedPort) {
    Write-Host "Port $selectedPort is in use, but it does not look like AI Project Manager."
    $nextPort = Find-FreePort -StartPort ($selectedPort + 1) -EndPort $MaxPort

    if ($nextPort) {
        Write-Host "Using available port $nextPort instead."
        $selectedPort = $nextPort
    }
    else {
        $answer = Read-Host "Ports $Port-$MaxPort are busy. Enter another port, or press Enter to quit"
        if ([string]::IsNullOrWhiteSpace($answer)) {
            exit 1
        }
        [int]$enteredPort = 0
        if (-not [int]::TryParse($answer, [ref]$enteredPort)) {
            Write-Error "Invalid port: $answer"
        }
        $selectedPort = $enteredPort
        if (Test-PortBusy -CheckPort $selectedPort) {
            Write-Error "Port $selectedPort is also busy."
        }
    }
}

$url = "http://127.0.0.1:$selectedPort"
Write-Host "Starting AI Project Manager on $url"

if ($DryRun) {
    Write-Host "Dry run only. Command:"
    Write-Host ".venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port $selectedPort"
    Write-Host "Fallback: uv run python -m uvicorn app.main:app --host 127.0.0.1 --port $selectedPort"
    exit 0
}

if (-not $NoBrowser) {
    $openCommand = @"
for (`$attempt = 1; `$attempt -le 40; `$attempt++) {
    try {
        Invoke-RestMethod -Uri '$url/api/context' -TimeoutSec 2 | Out-Null
        Start-Process '$url'
        exit 0
    }
    catch {
        Start-Sleep -Milliseconds 500
    }
}
Start-Process '$url'
"@
    $encodedOpenCommand = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($openCommand))
    Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-EncodedCommand",
        $encodedOpenCommand
    ) -WindowStyle Hidden | Out-Null
}

if ($NoBrowser) {
    Write-Host "Open $url in your browser when the service is ready."
}
else {
    Write-Host "A browser tab will open when the dashboard is ready."
}
Write-Host "Keep this window open while using the dashboard. Press Ctrl+C here to stop the service."

$env:UV_LINK_MODE = "copy"
for ($runAttempt = 1; $runAttempt -le 2; $runAttempt++) {
    $venvUvicorn = Join-Path $repoRoot ".venv\Scripts\uvicorn.exe"
    if (Test-Path $venvUvicorn) {
        & $venvUvicorn app.main:app --host 127.0.0.1 --port $selectedPort
    }
    else {
        uv run python -m uvicorn app.main:app --host 127.0.0.1 --port $selectedPort
    }
    $exitCode = $LASTEXITCODE
    if ($exitCode -eq 0) {
        exit 0
    }
    if ((Test-Path $venvUvicorn) -and ($runAttempt -eq 1)) {
        Write-Warning "The virtualenv launcher exited with code $exitCode. Falling back to uv run..."
        uv run python -m uvicorn app.main:app --host 127.0.0.1 --port $selectedPort
        $exitCode = $LASTEXITCODE
        if ($exitCode -eq 0) {
            exit 0
        }
    }
    if ($runAttempt -lt 2) {
        Write-Warning "Service command exited with code $exitCode. Retrying once..."
        Start-Sleep -Seconds 1
    }
}

exit $exitCode
