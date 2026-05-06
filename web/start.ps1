# 匈汉象棋 Web 版 - PowerShell 启动脚本

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "匈汉象棋 Web 版 - 启动脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Python 是否安装
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[信息] Python 版本: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[错误] 未检测到 Python，请先安装 Python 3.8+" -ForegroundColor Red
    Write-Host "下载地址: https://www.python.org/downloads/" -ForegroundColor Yellow
    Read-Host "按回车键退出"
    exit 1
}

Write-Host "[信息] 正在检查依赖..." -ForegroundColor Yellow
Set-Location server

# 检查虚拟环境
if (-Not (Test-Path "venv")) {
    Write-Host "[信息] 创建虚拟环境..." -ForegroundColor Yellow
    python -m venv venv
}

# 激活虚拟环境
& .\venv\Scripts\Activate.ps1

# 安装依赖（包括性能优化包）
Write-Host "[信息] 安装/更新依赖..." -ForegroundColor Yellow
pip install -r requirements.txt | Out-Null

# 检查是否安装gevent（性能优化）
try {
    python -c "import gevent" 2>$null
} catch {
    Write-Host "" 
    Write-Host "[提示] 未检测到 gevent，建议安装以提升性能:" -ForegroundColor Yellow
    Write-Host "       pip install gevent gunicorn" -ForegroundColor Cyan
    Write-Host ""
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "服务器启动中..." -ForegroundColor Green
Write-Host "访问地址: http://localhost:5000" -ForegroundColor Green
Write-Host "按 Ctrl+C 停止服务器" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 启动 Flask 应用
python app.py
