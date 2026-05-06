@echo off
chcp 65001 >nul
echo ========================================
echo 匈汉象棋 Web 版 - 启动脚本
echo ========================================
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [信息] 正在检查依赖...
cd server

REM 检查虚拟环境
if not exist "venv" (
    echo [信息] 创建虚拟环境...
    python -m venv venv
)

REM 激活虚拟环境
call venv\Scripts\activate.bat

REM 安装依赖（包括性能优化包）
echo [信息] 安装/更新依赖...
pip install -r requirements.txt >nul 2>&1

REM 检查是否安装gevent（性能优化）
python -c "import gevent" >nul 2>&1
if errorlevel 1 (
    echo.
    echo [提示] 未检测到 gevent，建议安装以提升性能:
    echo        pip install gevent gunicorn
    echo.
)

echo.
echo ========================================
echo 服务器启动中...
echo 访问地址: http://localhost:5000
echo 按 Ctrl+C 停止服务器
echo ========================================
echo.

REM 启动 Flask 应用
python app.py

pause
