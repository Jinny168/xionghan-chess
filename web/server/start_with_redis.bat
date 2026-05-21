@echo off
REM 雄汉象棋服务器启动脚本（支持 Redis 密码）
REM 用法: start_with_redis.bat [redis_password]

echo ========================================
echo   雄汉象棋 - Flask 服务器启动
echo ========================================
echo.

REM 检查是否提供了密码参数
if "%1"=="" (
    echo [提示] 未提供 Redis 密码，将使用无密码模式
    echo [提示] 如需启用密码认证，请运行: start_with_redis.bat your_password
    echo.
    set REDIS_PASSWORD=
) else (
    echo [信息] 已配置 Redis 密码认证
    set REDIS_PASSWORD=%1
)

REM 设置环境变量
set REDIS_PASSWORD=%REDIS_PASSWORD%

echo [1/3] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)
echo [成功] Python 环境正常

echo.
echo [2/3] 检查依赖包...
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo [警告] 缺少依赖包，正在安装...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
)
echo [成功] 依赖包完整

echo.
echo [3/3] 启动服务器...
echo.
echo ========================================
echo   服务器地址: http://localhost:5000
echo   Redis 模式: %IF% DEFINED REDIS_PASSWORD (已启用密码) ELSE (无密码) %ENDIF%
echo   按 Ctrl+C 停止服务器
echo ========================================
echo.

REM 启动 Flask 服务器
python app.py

pause
