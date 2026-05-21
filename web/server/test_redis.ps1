# Redis 完整测试与配置脚本（简化版）
# 用途：验证 Redis 集成、测试游戏功能、监控性能

$redisCli = "C:\Program Files\Redis\redis-cli.exe"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  雄汉象棋 - Redis 集成测试套件" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Redis 连接测试
Write-Host "[1/5] 测试 Redis 连接..." -ForegroundColor Yellow
$result = & $redisCli ping
if ($result -eq "PONG") {
    Write-Host "[OK] Redis 连接成功" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Redis 连接失败: $result" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 2. 查看 Redis 信息
Write-Host "[2/5] 获取 Redis 服务器信息..." -ForegroundColor Yellow
& $redisCli INFO server | Select-String "redis_version|os|tcp_port|uptime_in_seconds"
Write-Host ""

# 3. 清理旧数据
Write-Host "[3/5] 清理测试数据..." -ForegroundColor Yellow
& $redisCli KEYS "xionghan_chess:*" | ForEach-Object {
    & $redisCli DEL $_ | Out-Null
}
Write-Host "[OK] 已清理旧的测试数据" -ForegroundColor Green
Write-Host ""

# 4. 启动 Flask 服务器
Write-Host "[4/5] 启动 Flask 服务器（后台运行）..." -ForegroundColor Yellow
$serverPath = "C:\Users\27415\PycharmProjects\xionghan-chess\web\server\app.py"
Start-Process python -ArgumentList $serverPath -WindowStyle Minimized
Start-Sleep -Seconds 3

# 检查服务器是否启动
try {
    $response = Invoke-WebRequest -Uri "http://localhost:5000" -TimeoutSec 5 -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "[OK] Flask 服务器启动成功" -ForegroundColor Green
    }
} catch {
    Write-Host "[WARN] 服务器可能还在启动中，继续测试..." -ForegroundColor Yellow
}
Write-Host ""

# 5. 功能测试
Write-Host "[5/5] 开始功能测试..." -ForegroundColor Yellow
Write-Host ""

# 5.1 创建房间
Write-Host "  [测试 1] 创建房间..." -ForegroundColor Cyan
try {
    $createResponse = Invoke-RestMethod -Uri "http://localhost:5000/api/create_room" -Method POST -ContentType "application/json" -Body '{"mode":"xionghan"}'
    Write-Host "  [OK] 房间创建成功: $($createResponse.roomId)" -ForegroundColor Green
    $roomId = $createResponse.roomId
} catch {
    Write-Host "  [ERROR] 房间创建失败: $_" -ForegroundColor Red
    $roomId = $null
}
Write-Host ""

# 5.2 查看 Redis 中的房间数据
if ($roomId) {
    Write-Host "  [测试 2] 验证 Redis 数据存储..." -ForegroundColor Cyan
    $roomKey = "xionghan_chess:room:$roomId"
    $roomData = & $redisCli GET $roomKey
    if ($roomData) {
        Write-Host "  [OK] 房间数据已存入 Redis" -ForegroundColor Green
        Write-Host "     键: $roomKey" -ForegroundColor Gray
        # 显示部分数据
        $parsed = $roomData | ConvertFrom-Json
        Write-Host "     模式: $($parsed.mode)" -ForegroundColor Gray
        Write-Host "     玩家数: $($parsed.players.Count)" -ForegroundColor Gray
    } else {
        Write-Host "  [ERROR] 房间数据未在 Redis 中找到" -ForegroundColor Red
    }
    Write-Host ""
    
    # 5.3 查看所有 Redis 键
    Write-Host "  [测试 3] 查看所有 Redis 键..." -ForegroundColor Cyan
    $keys = & $redisCli KEYS "xionghan_chess:*"
    Write-Host "  当前 Redis 键列表:" -ForegroundColor Gray
    foreach ($key in $keys) {
        $type = & $redisCli TYPE $key
        Write-Host "    - $key ($type)" -ForegroundColor Gray
    }
    Write-Host ""
}

# 6. 性能监控
Write-Host "[6/5] Redis 性能统计..." -ForegroundColor Yellow
Write-Host ""

Write-Host "  内存使用情况:" -ForegroundColor Cyan
& $redisCli INFO memory | Select-String "used_memory_human|used_memory_peak_human|maxmemory_human"
Write-Host ""

Write-Host "  客户端连接:" -ForegroundColor Cyan
& $redisCli INFO clients | Select-String "connected_clients|blocked_clients"
Write-Host ""

Write-Host "  命令统计 (最近):" -ForegroundColor Cyan
& $redisCli INFO stats | Select-String "total_commands_processed|instantaneous_ops_per_sec"
Write-Host ""

# 7. 生产环境配置建议
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  生产环境配置建议" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "配置文件位置: C:\Program Files\Redis\redis.windows.conf" -ForegroundColor Yellow
Write-Host ""

Write-Host "1. 密码认证（必需）:" -ForegroundColor White
Write-Host "   在配置文件中添加或修改:" -ForegroundColor Gray
Write-Host "   requirepass YourStrongPassword123!" -ForegroundColor Green
Write-Host ""

Write-Host "2. 持久化策略（推荐）:" -ForegroundColor White
Write-Host "   RDB 快照（默认启用）:" -ForegroundColor Gray
Write-Host "   save 900 1" -ForegroundColor Green
Write-Host "   save 300 10" -ForegroundColor Green
Write-Host "   save 60 10000" -ForegroundColor Green
Write-Host ""
Write-Host "   AOF 日志（更可靠）:" -ForegroundColor Gray
Write-Host "   appendonly yes" -ForegroundColor Green
Write-Host "   appendfsync everysec" -ForegroundColor Green
Write-Host ""

Write-Host "3. 内存限制（防止OOM）:" -ForegroundColor White
Write-Host "   maxmemory 2gb" -ForegroundColor Green
Write-Host "   maxmemory-policy allkeys-lru" -ForegroundColor Green
Write-Host ""

Write-Host "4. 网络绑定（安全）:" -ForegroundColor White
Write-Host "   bind 127.0.0.1  # 仅本地访问" -ForegroundColor Green
Write-Host "   # 或者指定具体IP: bind 192.168.1.100" -ForegroundColor Gray
Write-Host ""

Write-Host "5. 修改代码以支持密码:" -ForegroundColor White
Write-Host "   在 app.py 中修改 Redis 连接:" -ForegroundColor Gray
Write-Host "   redis_client = redis.Redis(" -ForegroundColor Green
Write-Host "       host='localhost'," -ForegroundColor Green
Write-Host "       port=6379," -ForegroundColor Green
Write-Host "       password='YourStrongPassword123!',  # 添加密码" -ForegroundColor Green
Write-Host "       db=0," -ForegroundColor Green
Write-Host "       decode_responses=True" -ForegroundColor Green
Write-Host "   )" -ForegroundColor Green
Write-Host ""

# 8. 停止服务器
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  清理与总结" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "是否停止 Flask 服务器？(Y/N): " -ForegroundColor Yellow -NoNewline
$stopServer = Read-Host
if ($stopServer -eq 'Y' -or $stopServer -eq 'y') {
    Get-Process python | Where-Object {$_.MainWindowTitle -like "*app.py*"} | Stop-Process -Force
    Write-Host "[OK] 服务器已停止" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  测试完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "下一步操作:" -ForegroundColor Yellow
Write-Host "  1. 打开浏览器访问: http://localhost:5000" -ForegroundColor White
Write-Host "  2. 创建房间并测试联机对战功能" -ForegroundColor White
Write-Host "  3. 使用 redis-cli monitor 实时监控命令" -ForegroundColor White
Write-Host "  4. 查看完整统计: redis-cli INFO" -ForegroundColor White
Write-Host ""
