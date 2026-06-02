param(
  [ValidateSet("CurrentUserAllHosts", "CurrentUserCurrentHost")]
  [string]$Scope = "CurrentUserAllHosts",
  [switch]$Revert
)

$ErrorActionPreference = "Stop"

$ProfilePath = if ($Scope -eq "CurrentUserCurrentHost") {
  $PROFILE.CurrentUserCurrentHost
} else {
  $PROFILE.CurrentUserAllHosts
}

$ProfileDir = Split-Path -Parent $ProfilePath
$BackupPath = "$ProfilePath.gaokaollm_utf8_backup"
$BeginMarker = "# >>> gaokaollm utf8 bootstrap >>>"
$EndMarker = "# <<< gaokaollm utf8 bootstrap <<<"
$Block = @"
$BeginMarker
try {
  [Console]::InputEncoding = [System.Text.UTF8Encoding]::new()
  [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
  `$OutputEncoding = [System.Text.UTF8Encoding]::new()
  `$PSDefaultParameterValues['Get-Content:Encoding'] = 'UTF8'
  `$PSDefaultParameterValues['Set-Content:Encoding'] = 'UTF8'
  `$PSDefaultParameterValues['Add-Content:Encoding'] = 'UTF8'
  `$PSDefaultParameterValues['Out-File:Encoding'] = 'UTF8'
  `$PSDefaultParameterValues['Export-Csv:Encoding'] = 'UTF8'
  if (`$Host.Name -eq 'ConsoleHost') {
    chcp 65001 > `$null
  }
} catch {
  Write-Warning "Failed to configure UTF-8 console encoding: `$(`$_.Exception.Message)"
}
$EndMarker
"@

function Remove-ManagedBlock {
  param([string]$Text)
  $Pattern = "(?ms)^$([regex]::Escape($BeginMarker)).*?$([regex]::Escape($EndMarker))\r?\n?"
  return [regex]::Replace($Text, $Pattern, "")
}

if ($Revert) {
  if (Test-Path $ProfilePath) {
    $Current = Get-Content -LiteralPath $ProfilePath -Raw -Encoding UTF8
    $Clean = Remove-ManagedBlock -Text $Current
    Set-Content -LiteralPath $ProfilePath -Value $Clean -Encoding UTF8
    Write-Host "[utf8-profile] Removed managed UTF-8 block: $ProfilePath"
  }
  if (Test-Path $BackupPath) {
    $Backup = Get-Content -LiteralPath $BackupPath -Raw -Encoding UTF8
    if ($Backup -notmatch [regex]::Escape($BeginMarker)) {
      Copy-Item -LiteralPath $BackupPath -Destination $ProfilePath -Force
      Write-Host "[utf8-profile] Restored backup: $BackupPath"
    } else {
      Write-Host "[utf8-profile] Backup contains managed block; skipped restore: $BackupPath"
    }
  }
  exit 0
}

New-Item -ItemType Directory -Force -Path $ProfileDir | Out-Null
if ((Test-Path $ProfilePath) -and -not (Test-Path $BackupPath)) {
  $CurrentForBackup = Get-Content -LiteralPath $ProfilePath -Raw -Encoding UTF8
  $CleanBackup = Remove-ManagedBlock -Text $CurrentForBackup
  Set-Content -LiteralPath $BackupPath -Value $CleanBackup -Encoding UTF8
  Write-Host "[utf8-profile] Backup saved: $BackupPath"
}

$Existing = ""
if (Test-Path $ProfilePath) {
  $Existing = Get-Content -LiteralPath $ProfilePath -Raw -Encoding UTF8
}
$CleanExisting = Remove-ManagedBlock -Text $Existing
$NewContent = ($CleanExisting.TrimEnd() + "`r`n`r`n" + $Block + "`r`n").TrimStart()
Set-Content -LiteralPath $ProfilePath -Value $NewContent -Encoding UTF8

[Console]::InputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [System.Text.UTF8Encoding]::new()
if ($Host.Name -eq "ConsoleHost") {
  chcp 65001 > $null
}

Write-Host "[utf8-profile] UTF-8 block installed: $ProfilePath"
Write-Host "[utf8-profile] Open a new PowerShell terminal for persistent effect."
