param(
    [Parameter(Mandatory = $true)]
    [string]$WorkspaceRoot,

    [Parameter(Mandatory = $true)]
    [string]$PythonExe,

    [switch]$ForceWeeklyReport
)

$ErrorActionPreference = "Stop"

$workspacePath = Resolve-Path -Path $WorkspaceRoot
$scriptPath = Join-Path $workspacePath "run_daily_simulation.py"
$logDir = Join-Path $workspacePath "outputs\simulation\task_logs"
if (-not (Test-Path $logDir)) {
    New-Item -Path $logDir -ItemType Directory -Force | Out-Null
}

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = Join-Path $logDir "daily_task_$stamp.log"

$args = @($scriptPath)
if ($ForceWeeklyReport) {
    $args += "--force-weekly-report"
}

Push-Location $workspacePath
try {
    "[$(Get-Date -Format s)] Starting daily simulation task" | Tee-Object -FilePath $logFile -Append | Out-Null
    "Workspace: $workspacePath" | Tee-Object -FilePath $logFile -Append | Out-Null
    "Python: $PythonExe" | Tee-Object -FilePath $logFile -Append | Out-Null

    & $PythonExe @args 2>&1 | Tee-Object -FilePath $logFile -Append

    "[$(Get-Date -Format s)] Task completed" | Tee-Object -FilePath $logFile -Append | Out-Null
}
finally {
    Pop-Location
}
