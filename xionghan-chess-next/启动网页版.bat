@echo off
chcp 65001 >nul
setlocal
rem ============================================================
rem  匈汉象棋 · 网页版一键启动
rem  网页端是薄客户端：规则在服务端，必须先起 Python 服务。
rem  放在仓库根目录，因为要相对定位 .venv\ 与 src\。
rem  关闭弹出的“服务”窗口即停止服务。
rem ============================================================
set "ROOT=%~dp0"
set "PORT=8765"
set "URL=http://127.0.0.1:%PORT%/"

if not exist "%ROOT%.venv\Scripts\python.exe" (
  echo [错误] 未找到 .venv\Scripts\python.exe
  echo        请在仓库根目录执行：python -m venv .venv ^&^& .venv\Scripts\python -m pip install -e .
  pause
  exit /b 1
)

set "PYTHONPATH=%ROOT%src"
echo 正在启动服务：%URL%
echo （服务窗口最小化在任务栏；关闭该窗口即停止服务）
start "匈汉象棋 网页版服务" /min "%ROOT%.venv\Scripts\python.exe" -m uvicorn xionghan_chess.service.app:app --host 127.0.0.1 --port %PORT%

rem 给 uvicorn 两秒把端口监听起来，再开浏览器
timeout /t 2 /nobreak >nul
start "" "%URL%"
endlocal
