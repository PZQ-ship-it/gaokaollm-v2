$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$PgBin = "C:\ProgramData\Anaconda3\envs\gaokao_pg\Library\bin"
$DataDir = Join-Path $Root "postgres\data"
$RunPidFile = Join-Path $Root "postgres\postgres.pid"

$PgCtl = Join-Path $PgBin "pg_ctl.exe"

& $PgCtl -D $DataDir stop
if ($LASTEXITCODE -eq 0) {
  if (Test-Path $RunPidFile) {
    Remove-Item -Force $RunPidFile
  }
  Write-Host "PostgreSQL stopped with pg_ctl."
  exit 0
}

if (Test-Path $RunPidFile) {
  $PidText = Get-Content $RunPidFile -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($PidText) {
    $PostgresPid = [int]$PidText
    $Process = Get-Process -Id $PostgresPid -ErrorAction SilentlyContinue
    if ($Process) {
      Stop-Process -Id $PostgresPid -Force
      Remove-Item -Force $RunPidFile
      Write-Host "PostgreSQL direct process stopped. PID: $PostgresPid"
      exit 0
    }
  }
}

Write-Host "No running PostgreSQL process found for this project."
