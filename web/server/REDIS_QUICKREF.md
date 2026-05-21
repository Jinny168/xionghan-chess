# Redis 快速参考卡片

## 🔗 连接测试
```powershell
& "C:\Program Files\Redis\redis-cli.exe" ping
```

## 🚀 启动服务器

### 无密码模式
```powershell
cd web/server
python app.py
```

### 带密码模式
```powershell
$env:REDIS_PASSWORD = "YourPassword"
python app.py

# 或使用脚本
.\start_with_redis.ps1 -Password "YourPassword"
```

## 📊 监控命令

```powershell
$redisCli = "C:\Program Files\Redis\redis-cli.exe"

# 实时监控
.\monitor_redis.ps1

# 完整测试
.\test_redis.ps1

# 查看房间数
(& $redisCli KEYS "xionghan_chess:room:*").Count

# 查看玩家数
(& $redisCli KEYS "xionghan_chess:player_room:*").Count

# 查看内存
& $redisCli INFO memory | Select-String "used_memory_human"

# 实时监视
& $redisCli MONITOR
```

## 🔧 常用操作

```powershell
# 重启 Redis 服务
Restart-Service Redis

# 查看所有键
& $redisCli KEYS "xionghan_chess:*"

# 删除所有测试数据
& $redisCli KEYS "xionghan_chess:*" | ForEach-Object { & $redisCli DEL $_ }

# 手动保存
& $redisCli BGSAVE

# 查看慢查询
& $redisCli SLOWLOG GET 10
```

## 🔒 生产配置要点

1. **密码认证**：`requirepass YourStrongPassword`
2. **持久化**：`appendonly yes` + `appendfsync everysec`
3. **内存限制**：`maxmemory 2gb`
4. **网络绑定**：`bind 127.0.0.1`

详细配置见：`redis.production.conf`

## 📁 重要文件

- `app.py` - 主服务器（已集成 Redis）
- `start_with_redis.ps1` - 启动脚本
- `monitor_redis.ps1` - 监控工具
- `REDIS_GUIDE.md` - 完整指南
- `redis.production.conf` - 生产配置示例

---

**提示**: 遇到问题先查看 `REDIS_GUIDE.md` 的故障排查章节
