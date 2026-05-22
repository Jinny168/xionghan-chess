# 雄汉象棋 Docker 一键部署脚本（PowerShell）

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  雄汉象棋 - Docker 一键部署" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Docker
try {
    $dockerVersion = docker --version 2>&1
    Write-Host "[成功] Docker 已安装: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "[错误] Docker 未安装，请先安装 Docker Desktop" -ForegroundColor Red
    Write-Host "下载地址: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    Read-Host "按回车键退出"
    exit 1
}

# 检查 Docker Compose
try {
    $composeVersion = docker compose version 2>&1
    Write-Host "[成功] Docker Compose 已安装" -ForegroundColor Green
} catch {
    Write-Host "[错误] Docker Compose 未安装" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}
Write-Host ""

# 检查 .env 文件
if (-Not (Test-Path "../config/.env")) {
    Write-Host "[警告] 未找到 .env 文件，正在从 .env.example 复制..." -ForegroundColor Yellow
    Copy-Item "../config/.env.example" "../config/.env"
    Write-Host "[提示] 请编辑 config/.env 文件修改密码配置" -ForegroundColor Cyan
    Write-Host ""
}

# 选择部署模式
Write-Host "请选择部署模式:" -ForegroundColor White
Write-Host "  1. 开发模式（仅 Web + Redis）" -ForegroundColor White
Write-Host "  2. 生产模式（Web + Redis + Nginx）" -ForegroundColor White
Write-Host ""
$mode = Read-Host "请输入选项 (1/2)"

if ($mode -eq "1") {
    Write-Host ""
    Write-Host "[信息] 启动开发模式..." -ForegroundColor Cyan
    docker compose -f ../config/docker-compose.yml up -d redis web
} elseif ($mode -eq "2") {
    Write-Host ""
    Write-Host "[信息] 启动生产模式..." -ForegroundColor Cyan
    docker compose -f ../config/docker-compose.yml --profile production up -d
} else {
    Write-Host "[错误] 无效选项" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  部署完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# 显示服务状态
Write-Host "服务状态:" -ForegroundColor Yellow
docker compose -f ../config/docker-compose.yml ps
Write-Host ""

# 显示访问地址
Write-Host "访问地址:" -ForegroundColor Yellow
Write-Host "  - 直接访问: http://localhost:5000" -ForegroundColor White
Write-Host "  - 通过 Nginx: http://localhost (生产模式)" -ForegroundColor White
Write-Host ""

# 显示常用命令
Write-Host "常用命令:" -ForegroundColor Yellow
Write-Host "  - 查看日志: docker compose logs -f" -ForegroundColor Gray
Write-Host "  - 停止服务: docker compose down" -ForegroundColor Gray
Write-Host "  - 重启服务: docker compose restart" -ForegroundColor Gray
Write-Host "  - 更新代码: docker compose up -d --build" -ForegroundColor Gray
Write-Host ""

Read-Host "按回车键退出"
