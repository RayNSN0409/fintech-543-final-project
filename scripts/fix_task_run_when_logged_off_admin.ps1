param(
    [string]$TaskName = "Fintech543DailySimulation",
    [string]$RunTime = "17:30",
    [switch]$IncludeWeekends
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-IsAdministrator)) {
    throw "This script must be run from an elevated PowerShell (Run as Administrator)."
}

$workspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$projectRunner = Join-Path $workspaceRoot "scripts\run_daily_simulation_task.cmd"
$schtasksExe = Join-Path $env:WINDIR "System32\schtasks.exe"

if (-not (Test-Path $projectRunner)) {
    throw "Runner script not found: $projectRunner"
}

if (-not (Test-Path $schtasksExe)) {
    throw "Task Scheduler CLI not found: $schtasksExe"
}

$launcherDir = "C:\ProgramData\Fintech543Task"
$launcherPath = Join-Path $launcherDir "fintech543_daily_simulation.cmd"
if (-not (Test-Path $launcherDir)) {
    New-Item -Path $launcherDir -ItemType Directory -Force | Out-Null
}

$launcherContent = @(
    "@echo off",
    "call `"$projectRunner`""
)
Set-Content -Path $launcherPath -Value $launcherContent -Encoding ASCII

$days = if ($IncludeWeekends) { "MON,TUE,WED,THU,FRI,SAT,SUN" } else { "MON,TUE,WED,THU,FRI" }
$taskAction = "`"$launcherPath`""

Write-Host "Applying one-shot admin fix..."
Write-Host "TaskName: $TaskName"
Write-Host "RunTime: $RunTime"
Write-Host "Days: $days"
Write-Host "RunAs: SYSTEM"
Write-Host "Action: $taskAction"

& $schtasksExe /Create /TN $TaskName /TR $taskAction /SC WEEKLY /D $days /ST $RunTime /RU SYSTEM /RL HIGHEST /F
if ($LASTEXITCODE -ne 0) {
    throw "Failed to create task '$TaskName' as SYSTEM."
}

Write-Host "Task recreated as SYSTEM successfully."
Write-Host "Verifying task configuration..."
& $schtasksExe /Query /TN $TaskName /V /FO LIST

Write-Host "Done. This task can run even when you are logged off."