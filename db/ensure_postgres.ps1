param(
  [string]$HostName = "127.0.0.1",
  [int]$Port = 55432,
  [string]$DatabaseUrl = "postgresql://postgres@127.0.0.1:55432/gaokao_recommendation",
  [int]$TimeoutSeconds = 30
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$PgBin = "C:\ProgramData\Anaconda3\envs\gaokao_pg\Library\bin"
$Psql = Join-Path $PgBin "psql.exe"
$StartScript = Join-Path $Root "db\start_postgres.ps1"

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

function Test-DatabaseReady {
  if (-not (Test-PortOpen -TargetHost $HostName -TargetPort $Port)) {
    return $false
  }
  if (-not (Test-Path $Psql)) {
    throw "psql.exe not found: $Psql"
  }
  & $Psql $DatabaseUrl -qAt -c "select 1;" | Out-Null
  return ($LASTEXITCODE -eq 0)
}

if (Test-DatabaseReady) {
  Write-Host "PostgreSQL is already ready on $HostName`:$Port."
  exit 0
}

Write-Host "PostgreSQL is not ready on $HostName`:$Port; starting project database..."
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $StartScript

$Deadline = (Get-Date).AddSeconds($TimeoutSeconds)
while ((Get-Date) -lt $Deadline) {
  Start-Sleep -Seconds 1
  if (Test-DatabaseReady) {
    Write-Host "PostgreSQL is ready on $HostName`:$Port."
    exit 0
  }
}

throw "PostgreSQL did not become ready within $TimeoutSeconds seconds."
