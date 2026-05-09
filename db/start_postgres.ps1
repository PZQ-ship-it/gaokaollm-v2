$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$PgBin = "C:\ProgramData\Anaconda3\envs\gaokao_pg\Library\bin"
$DataDir = Join-Path $Root "postgres\data"
$LogFile = Join-Path $Root "postgres\postgres.log"
$ErrLogFile = Join-Path $Root "postgres\postgres.err.log"
$PidFile = Join-Path $DataDir "postmaster.pid"
$RunPidFile = Join-Path $Root "postgres\postgres.pid"

if (-not (Test-Path (Join-Path $DataDir "PG_VERSION"))) {
  throw "PostgreSQL data directory not found: $DataDir"
}

if (Test-Path $PidFile) {
  Write-Host "Removing stale postmaster.pid before startup: $PidFile"
  Remove-Item -Force $PidFile
}

$PgCtl = Join-Path $PgBin "pg_ctl.exe"
$Postgres = Join-Path $PgBin "postgres.exe"

& $PgCtl -D $DataDir -l $LogFile -o "-p 55432" start
if ($LASTEXITCODE -eq 0) {
  Write-Host "PostgreSQL started with pg_ctl on port 55432."
  exit 0
}

Write-Host "pg_ctl startup failed with exit code $LASTEXITCODE; falling back to postgres.exe."
$Process = Start-Process `
  -FilePath $Postgres `
  -ArgumentList @("-D", $DataDir, "-p", "55432") `
  -RedirectStandardOutput $LogFile `
  -RedirectStandardError $ErrLogFile `
  -WindowStyle Hidden `
  -PassThru

$Process.Id | Set-Content -Path $RunPidFile -Encoding ASCII
Write-Host "PostgreSQL started directly on port 55432. PID: $($Process.Id)"
