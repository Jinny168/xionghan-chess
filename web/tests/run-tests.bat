@echo off
chcp 65001 >nul
echo ========================================
echo   控制器架构测试 - 快速启动
echo ========================================
echo.

echo [1/2] 检查Node.js环境...
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ 未检测到Node.js，请先安装Node.js
    pause
    exit /b 1
)
echo ✅ Node.js已安装
echo.

echo [2/2] 运行单元测试...
cd /d "%~dp0"
node test-controllers-node.js

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo   ✅ 所有测试通过！
    echo ========================================
    echo.
    echo 提示: 如需查看可视化测试界面，请运行:
    echo   start test-controllers.html
    echo.
) else (
    echo.
    echo ========================================
    echo   ❌ 部分测试失败，请检查错误信息
    echo ========================================
    echo.
)

pause
