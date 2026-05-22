@echo off
chcp 65001 >nul
echo ============================================================
echo 🚀 匈汉象棋 Node.js 测试环境安装脚本
echo ============================================================
echo.

REM 检查Node.js是否已安装
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ 未检测到Node.js
    echo.
    echo 请先安装Node.js:
    echo 1. 访问 https://nodejs.org/
    echo 2. 下载并安装LTS版本
    echo 3. 重新运行此脚本
    echo.
    pause
    exit /b 1
)

echo ✅ 检测到Node.js
node --version
npm --version
echo.

REM 检查是否在正确的目录
if not exist "package.json" (
    echo ❌ 错误: 未找到package.json
    echo 请确保在 web/tests 目录下运行此脚本
    echo.
    pause
    exit /b 1
)

echo 📦 开始安装依赖...
echo.

npm install

if %errorlevel% neq 0 (
    echo.
    echo ❌ 依赖安装失败
    echo 请检查网络连接或尝试切换淘宝镜像:
    echo npm config set registry https://registry.npmmirror.com
    echo.
    pause
    exit /b 1
)

echo.
echo ✅ 依赖安装完成!
echo.
echo ============================================================
echo 🎉 环境准备就绪!
echo ============================================================
echo.
echo 现在可以运行测试:
echo   npm test
echo.
echo 或使用监听模式:
echo   npm run test:watch
echo.
pause
