@echo off
echo 启动多个匈汉象棋数据收集进程...

set NUM_PROCESSES=4

if not "%1"=="" (
    set NUM_PROCESSES=%1
)

echo 启动 %NUM_PROCESSES% 个数据收集进程...

for /L %%i in (1,1,%NUM_PROCESSES%) do (
    echo 启动进程 %%i...
    start "Collect_Process_%%i" /MIN python collect.py
    timeout /t 2 /nobreak >nul
)

echo 所有收集进程已启动！
pause