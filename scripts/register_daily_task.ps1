param(
    [string]$TaskName = "Fintech543DailySimulation",
    [string]$RunTime = "17:30",
    [switch]$IncludeWeekends,
    [switch]$Force,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

$workspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runnerScript = (Join-Path $workspaceRoot "scripts\run_daily_simulation_task.ps1")
$runnerCmd = (Join-Path $workspaceRoot "scripts\run_daily_simulation_task.cmd")
$schtasksExe = Join-Path $env:WINDIR "System32\schtasks.exe"
$taskLauncher = Join-Path $env:USERPROFILE "fintech543_daily_simulation.cmd"

if (-not (Test-Path $runnerCmd)) {
    throw "Runner command script not found: $runnerCmd"
}

if (-not (Test-Path $schtasksExe)) {
    throw "Task Scheduler CLI not found: $schtasksExe"
}

$days = if ($IncludeWeekends) { "MON,TUE,WED,THU,FRI,SAT,SUN" } else { "MON,TUE,WED,THU,FRI" }

# Task Scheduler in some Windows setups misparses /TR when the executable path includes spaces.
# Use a launcher script in the user profile (no spaces) that calls the project runner.
$launcherContent = @(
    "@echo off",
    "call `"$runnerCmd`""
)
Set-Content -Path $taskLauncher -Value $launcherContent -Encoding ASCII

$taskAction = "`"$taskLauncher`""

Write-Host "Registering Windows Task Scheduler task..."
Write-Host "TaskName: $TaskName"
Write-Host "RunTime: $RunTime"
Write-Host "Days: $days"
Write-Host "Command: $taskAction"
Write-Host "Launcher: $taskLauncher"
if ($Force) {
    Write-Host "Force mode: existing task will be overwritten if present."
}

if ($DryRun) {
    Write-Host "Dry run mode: task was not created."
    exit 0
}

if ($Force) {
    & $schtasksExe /Create /TN $TaskName /TR $taskAction /SC WEEKLY /D $days /ST $RunTime /RL LIMITED /F
} else {
    & $schtasksExe /Create /TN $TaskName /TR $taskAction /SC WEEKLY /D $days /ST $RunTime /RL LIMITED
}

if ($LASTEXITCODE -ne 0) {
    throw "Failed to create task '$TaskName'."
}

Write-Host "Task created successfully."
Write-Host "Use this command to verify: schtasks /Query /TN $TaskName /V /FO LIST"
