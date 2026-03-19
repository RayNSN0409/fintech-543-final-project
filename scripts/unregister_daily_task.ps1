param(
    [string]$TaskName = "Fintech543DailySimulation"
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $false

$schtasksExe = Join-Path $env:WINDIR "System32\schtasks.exe"
$taskLauncher = Join-Path $env:USERPROFILE "fintech543_daily_simulation.cmd"
if (-not (Test-Path $schtasksExe)) {
    throw "Task Scheduler CLI not found: $schtasksExe"
}

function Invoke-Schtasks {
    param(
        [string[]]$Arguments
    )

    $process = Start-Process -FilePath $schtasksExe -ArgumentList $Arguments -NoNewWindow -Wait -PassThru
    return $process.ExitCode
}

$queryCode = Invoke-Schtasks -Arguments @("/Query", "/TN", $TaskName)
if ($queryCode -ne 0) {
    Write-Host "Task '$TaskName' does not exist. Nothing to remove."
    exit 0
}

$deleteCode = Invoke-Schtasks -Arguments @("/Delete", "/TN", $TaskName, "/F")
if ($deleteCode -ne 0) {
    throw "Failed to delete task '$TaskName'."
}

if (Test-Path $taskLauncher) {
    Remove-Item -Path $taskLauncher -Force
    Write-Host "Removed launcher file: $taskLauncher"
}

Write-Host "Task '$TaskName' deleted successfully."
