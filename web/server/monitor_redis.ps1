# Redis 实时监控脚本
# 用途：监控雄汉象棋服务器的 Redis 性能指标

$redisCli = "C:\Program Files\Redis\redis-cli.exe"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Redis 实时监控面板" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 测试连接
$result = & $redisCli ping
if ($result -ne "PONG") {
    Write-Host "❌ Redis 连接失败" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Redis 连接成功" -ForegroundColor Green
Write-Host ""

# 持续监控
Write-Host "开始实时监控（按 Ctrl+C 停止）..." -ForegroundColor Yellow
Write-Host ""

while ($true) {
    Clear-Host
    
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  Redis 监控数据 - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    
    # 1. 服务器信息
    Write-Host "📊 服务器信息:" -ForegroundColor Yellow
    $serverInfo = & $redisCli INFO server
    $version = ($serverInfo | Select-String "redis_version:(.+)").Matches.Groups[1].Value
    $uptime = ($serverInfo | Select-String "uptime_in_seconds:(.+)").Matches.Groups[1].Value
    $uptimeDays = [math]::Floor([int]$uptime / 86400)
    $uptimeHours = [math]::Floor(([int]$uptime % 86400) / 3600)
    Write-Host "  版本: $version" -ForegroundColor White
    Write-Host "  运行时间: ${uptimeDays}天 ${uptimeHours}小时" -ForegroundColor White
    Write-Host ""
    
    # 2. 内存使用
    Write-Host "💾 内存使用:" -ForegroundColor Yellow
    $memoryInfo = & $redisCli INFO memory
    $usedMemory = ($memoryInfo | Select-String "used_memory_human:(.+)").Matches.Groups[1].Value
    $usedMemoryPeak = ($memoryInfo | Select-String "used_memory_peak_human:(.+)").Matches.Groups[1].Value
    $maxMemory = ($memoryInfo | Select-String "maxmemory_human:(.+)").Matches.Groups[1].Value
    Write-Host "  当前使用: $usedMemory" -ForegroundColor Green
    Write-Host "  峰值使用: $usedMemoryPeak" -ForegroundColor Yellow
    Write-Host "  最大限制: $maxMemory" -ForegroundColor White
    Write-Host ""
    
    # 3. 客户端连接
    Write-Host "👥 客户端连接:" -ForegroundColor Yellow
    $clientsInfo = & $redisCli INFO clients
    $connectedClients = ($clientsInfo | Select-String "connected_clients:(.+)").Matches.Groups[1].Value
    $blockedClients = ($clientsInfo | Select-String "blocked_clients:(.+)").Matches.Groups[1].Value
    Write-Host "  活跃连接: $connectedClients" -ForegroundColor White
    Write-Host "  阻塞连接: $blockedClients" -ForegroundColor White
    Write-Host ""
    
    # 4. 操作统计
    Write-Host "⚡ 操作统计:" -ForegroundColor Yellow
    $statsInfo = & $redisCli INFO stats
    $totalCommands = ($statsInfo | Select-String "total_commands_processed:(.+)").Matches.Groups[1].Value
    $opsPerSec = ($statsInfo | Select-String "instantaneous_ops_per_sec:(.+)").Matches.Groups[1].Value
    $keyspaceHits = ($statsInfo | Select-String "keyspace_hits:(.+)").Matches.Groups[1].Value
    $keyspaceMisses = ($statsInfo | Select-String "keyspace_misses:(.+)").Matches.Groups[1].Value
    
    if ([int]$keyspaceHits + [int]$keyspaceMisses -gt 0) {
        $hitRate = [math]::Round([int]$keyspaceHits / ([int]$keyspaceHits + [int]$keyspaceMisses) * 100, 2)
    } else {
        $hitRate = 0
    }
    
    Write-Host "  总命令数: $totalCommands" -ForegroundColor White
    Write-Host "  每秒操作: $opsPerSec ops/sec" -ForegroundColor Green
    Write-Host "  缓存命中率: ${hitRate}%" -ForegroundColor $(if ($hitRate -gt 80) { "Green" } elseif ($hitRate -gt 50) { "Yellow" } else { "Red" })
    Write-Host ""
    
    # 5. 键空间
    Write-Host "🗂️  键空间:" -ForegroundColor Yellow
    $keyspaceInfo = & $redisCli INFO keyspace
    if ($keyspaceInfo -match "db0:(.+)") {
        $keysInfo = $matches[1]
        Write-Host "  db0: $keysInfo" -ForegroundColor White
    } else {
        Write-Host "  db0: 无数据" -ForegroundColor Gray
    }
    Write-Host ""
    
    # 6. 雄汉象棋专用统计
    Write-Host "♟️  雄汉象棋数据:" -ForegroundColor Yellow
    $roomKeys = & $redisCli KEYS "xionghan_chess:room:*"
    $playerKeys = & $redisCli KEYS "xionghan_chess:player_room:*"
    Write-Host "  活跃房间数: $($roomKeys.Count)" -ForegroundColor Green
    Write-Host "  在线玩家数: $($playerKeys.Count)" -ForegroundColor Green
    Write-Host ""
    
    # 7. 持久化状态
    Write-Host "💿 持久化状态:" -ForegroundColor Yellow
    $persistenceInfo = & $redisCli INFO persistence
    $rdbLastStatus = ($persistenceInfo | Select-String "rdb_last_bgsave_status:(.+)").Matches.Groups[1].Value
    $aofEnabled = ($persistenceInfo | Select-String "aof_enabled:(.+)").Matches.Groups[1].Value
    Write-Host "  RDB 最后状态: $rdbLastStatus" -ForegroundColor $(if ($rdbLastStatus -eq "ok") { "Green" } else { "Red" })
    Write-Host "  AOF 启用: $(if ($aofEnabled -eq "1") { "是" } else { "否" })" -ForegroundColor White
    Write-Host ""
    
    # 等待 5 秒后刷新
    Start-Sleep -Seconds 5
}
