# 雄汉象棋服务器启动脚本（PowerShell 版本）
# 用法: .\start_with_redis.ps1 [-Password "your_password"]

param(
    [string]$Password = ""
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  雄汉象棋 - Flask 服务器启动" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 设置 Redis 密码环境变量
if ($Password) {
    Write-Host "[信息] 已配置 Redis 密码认证" -ForegroundColor Green
    $env:REDIS_PASSWORD = $Password
} else {
    Write-Host "[提示] 未提供 Redis 密码，将使用无密码模式" -ForegroundColor Yellow
    Write-Host "[提示] 如需启用密码认证，请运行: .\start_with_redis.ps1 -Password 'your_password'" -ForegroundColor Yellow
    $env:REDIS_PASSWORD = ""
}
Write-Host ""

# [1/3] 检查 Python 环境
Write-Host "[1/3] 检查 Python 环境..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[成功] $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[错误] 未找到 Python，请先安装 Python 3.8+" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}
Write-Host ""

# [2/3] 检查依赖包
Write-Host "[2/3] 检查依赖包..." -ForegroundColor Yellow
$requiredModules = @("flask", "flask_cors", "flask_socketio", "redis")
$missingModules = @()

foreach ($module in $requiredModules) {
    try {
        python -c "import $module" 2>$null
        if ($LASTEXITCODE -ne 0) {
            $missingModules += $module
        }
    } catch {
        $missingModules += $module
    }
}

if ($missingModules.Count -gt 0) {
    Write-Host "[警告] 缺少依赖包: $($missingModules -join ', ')" -ForegroundColor Yellow
    Write-Host "[操作] 正在安装依赖包..." -ForegroundColor Cyan
    pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[错误] 依赖安装失败" -ForegroundColor Red
        Read-Host "按回车键退出"
        exit 1
    }
    Write-Host "[成功] 依赖包安装完成" -ForegroundColor Green
} else {
    Write-Host "[成功] 所有依赖包已就绪" -ForegroundColor Green
}
Write-Host ""

# [3/3] 启动服务器
Write-Host "[3/3] 启动服务器..." -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  服务器地址: http://localhost:5000" -ForegroundColor White
if ($Password) {
    Write-Host "  Redis 模式: 🔒 已启用密码认证" -ForegroundColor Green
} else {
    Write-Host "  Redis 模式: ⚠️  无密码模式" -ForegroundColor Yellow
}
Write-Host "  按 Ctrl+C 停止服务器" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# 启动 Flask 服务器
python app.py
