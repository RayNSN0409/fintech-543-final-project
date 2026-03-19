@echo off
setlocal

set "ROOT=%~dp0.."
set "LOGDIR=%ROOT%\outputs\simulation\task_logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

pushd "%ROOT%"
"D:/Programming/Python/Conda/python.exe" "run_daily_simulation.py" >> "%LOGDIR%\scheduled_stdout.log" 2>&1
popd

endlocal
