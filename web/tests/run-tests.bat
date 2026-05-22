@echo off
chcp 65001 >nul
echo ============================================================
echo 🧪 运行匈汉象棋控制器测试
echo ============================================================
echo.

REM 检查node_modules是否存在
if not exist "node_modules" (
    echo ⚠️ 未检测到依赖，先安装依赖...
    echo.
    call install-and-test.bat
    if %errorlevel% neq 0 exit /b 1
)

echo 开始运行测试...
echo.

node test-controllers-node.js

echo.
echo ============================================================
pause
