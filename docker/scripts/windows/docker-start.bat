@echo off
REM 雄汉象棋 Docker 一键部署脚本（Windows）

echo ========================================
echo   雄汉象棋 - Docker 一键部署
echo ========================================
echo.

REM 检查 Docker 是否安装
docker --version >nul 2>&1
if errorlevel 1 (
    echo [错误] Docker 未安装，请先安装 Docker Desktop
    echo 下载地址: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)
echo [成功] Docker 已安装

REM 检查 Docker Compose
docker compose version >nul 2>&1
if errorlevel 1 (
    echo [错误] Docker Compose 未安装
    pause
    exit /b 1
)
echo [成功] Docker Compose 已安装
echo.

REM 检查 .env 文件
if not exist ..\config\.env (
    echo [警告] 未找到 .env 文件，正在从 .env.example 复制...
    copy ..\config\.env.example ..\config\.env
    echo [提示] 请编辑 config\.env 文件修改密码配置
    echo.
)

REM 选择部署模式
echo 请选择部署模式:
echo   1. 开发模式（仅 Web + Redis）
echo   2. 生产模式（Web + Redis + Nginx）
echo.
set /p MODE="请输入选项 (1/2): "

if "%MODE%"=="1" (
    echo.
    echo [信息] 启动开发模式...
    docker compose -f ../config/docker-compose.yml up -d redis web
) else if "%MODE%"=="2" (
    echo.
    echo [信息] 启动生产模式...
    docker compose -f ../config/docker-compose.yml --profile production up -d
) else (
    echo [错误] 无效选项
    pause
    exit /b 1
)

echo.
echo ========================================
echo   部署完成！
echo ========================================
echo.
echo 服务状态:
docker compose -f ../config/docker-compose.yml ps
echo.
echo 访问地址:
echo   - 直接访问: http://localhost:5000
echo   - 通过 Nginx: http://localhost (生产模式)
echo.
echo 常用命令:
echo   - 查看日志: docker compose logs -f
echo   - 停止服务: docker compose down
echo   - 重启服务: docker compose restart
echo   - 更新代码: docker compose up -d --build
echo.

pause
