param(
  [string]$HostName = "127.0.0.1",
  [int]$Port = 8000,
  [string]$DatabaseUrl = "postgresql://postgres@127.0.0.1:55432/gaokao_recommendation",
  [string]$Python = "C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe",
  [switch]$SmokeTrace,
  [switch]$FullTrace,
  [switch]$DiagnoseTrace,
  [switch]$NoApi,
  [int]$SmokeTraceTurns = 1,
  [int]$FullTraceTurns = 6,
  [int]$TurnTimeoutSeconds = 120
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$EnsurePostgres = Join-Path $Root "db\ensure_postgres.ps1"
$Outputs = Join-Path $Root "outputs\demo_trace"
$SmokeTraceOutput = Join-Path $Outputs "startup_smoke_trace_latest.json"
$FullTraceOutput = Join-Path $Outputs "startup_full_trace_latest.json"
$DiagnosisOutput = Join-Path $Outputs "startup_agent_diagnosis_latest.json"
$DiagnosisMarkdownOutput = Join-Path $Outputs "startup_agent_diagnosis_latest.md"

function Test-HttpReady {
  param([string]$Url)
  try {
    $Response = Invoke-RestMethod -Uri $Url -TimeoutSec 3
    return ($Response.status -eq "ok")
  } catch {
    return $false
  }
}

function Test-PortOpen {
  param([string]$TargetHost, [int]$TargetPort)
  try {
    $Client = New-Object System.Net.Sockets.TcpClient
    $Async = $Client.BeginConnect($TargetHost, $TargetPort, $null, $null)
    $Ready = $Async.AsyncWaitHandle.WaitOne(1000, $false)
    if (-not $Ready) {
      $Client.Close()
      return $false
    }
    $Client.EndConnect($Async)
    $Client.Close()
    return $true
  } catch {
    return $false
  }
}

Set-Location $Root

if (-not (Test-Path $Python)) {
  throw "Python not found: $Python"
}

$env:DATABASE_URL = $DatabaseUrl
Remove-Item Env:\GAOKAOLLM_OFFLINE_DETERMINISTIC -ErrorAction SilentlyContinue
Remove-Item Env:\GAOKAOLLM_SKIP_LLM_PARETO_QUESTION -ErrorAction SilentlyContinue
if (-not $env:OPENAI_TIMEOUT) {
  $env:OPENAI_TIMEOUT = "120"
}
if (-not $env:OPENAI_STRUCTURED_TIMEOUT) {
  $env:OPENAI_STRUCTURED_TIMEOUT = "120"
}
if (-not $env:OPENAI_REASONING_TIMEOUT) {
  $env:OPENAI_REASONING_TIMEOUT = "180"
}

Write-Host "[demo-start] Ensuring PostgreSQL..."
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $EnsurePostgres -DatabaseUrl $DatabaseUrl

Write-Host "[demo-start] Checking Python environment..."
& $Python -c "import main; print(main.app.title)"
if ($LASTEXITCODE -ne 0) {
  throw "Python environment check failed."
}

if ($SmokeTrace) {
  New-Item -ItemType Directory -Force -Path $Outputs | Out-Null
  Write-Host "[demo-start] Running real LLM smoke trace..."
  & $Python scripts\run_demo_trace.py `
    --max-turns $SmokeTraceTurns `
    --turn-timeout-seconds $TurnTimeoutSeconds `
    --db-query-timeout-seconds 12 `
    --output $SmokeTraceOutput
  if ($LASTEXITCODE -ne 0) {
    throw "Smoke trace failed. See $SmokeTraceOutput"
  }
  Write-Host "[demo-start] Smoke trace saved: $SmokeTraceOutput"
}

if ($FullTrace) {
  New-Item -ItemType Directory -Force -Path $Outputs | Out-Null
  Write-Host "[demo-start] Running real LLM full demo trace..."
  & $Python scripts\run_demo_trace.py `
    --max-turns $FullTraceTurns `
    --turn-timeout-seconds $TurnTimeoutSeconds `
    --db-query-timeout-seconds 12 `
    --output $FullTraceOutput
  if ($LASTEXITCODE -ne 0) {
    throw "Full trace failed. See $FullTraceOutput"
  }
  Write-Host "[demo-start] Full trace saved: $FullTraceOutput"
}

if ($DiagnoseTrace -or $FullTrace) {
  New-Item -ItemType Directory -Force -Path $Outputs | Out-Null
  $TraceInputs = @()
  if (Test-Path $FullTraceOutput) {
    $TraceInputs += $FullTraceOutput
  }
  if (Test-Path $SmokeTraceOutput) {
    $TraceInputs += $SmokeTraceOutput
  }
  if ($TraceInputs.Count -eq 0) {
    throw "No startup trace is available for diagnosis. Run with -SmokeTrace or -FullTrace."
  }
  Write-Host "[demo-start] Diagnosing startup trace..."
  & $Python scripts\diagnose_agent_runs.py @TraceInputs `
    --output $DiagnosisOutput `
    --markdown-output $DiagnosisMarkdownOutput
  if ($LASTEXITCODE -ne 0) {
    throw "Trace diagnosis failed. See $DiagnosisOutput"
  }
  Write-Host "[demo-start] Diagnosis saved: $DiagnosisOutput"
}

if ($NoApi) {
  Write-Host "[demo-start] Preflight complete; API start skipped by -NoApi."
  exit 0
}

$HealthUrl = "http://$HostName`:$Port/health"
if (Test-HttpReady -Url $HealthUrl) {
  Write-Host "[demo-start] API is already ready: $HealthUrl"
  Write-Host "[demo-start] Demo URL: http://$HostName`:$Port/demo"
  exit 0
}

if (Test-PortOpen -TargetHost $HostName -TargetPort $Port) {
  throw "Port $HostName`:$Port is already in use, but $HealthUrl is not healthy. Use another port with -Port."
}

Write-Host "[demo-start] Starting API on http://$HostName`:$Port ..."
Write-Host "[demo-start] Demo URL: http://$HostName`:$Port/demo"
& $Python -m uvicorn main:app --host $HostName --port $Port
