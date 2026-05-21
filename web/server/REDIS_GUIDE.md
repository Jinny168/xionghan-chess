# Redis 集成完整指南

## 📋 目录

1. [快速开始](#快速开始)
2. [安装 Redis](#安装-redis)
3. [测试连接](#测试连接)
4. [启动服务器](#启动服务器)
5. [功能验证](#功能验证)
6. [性能监控](#性能监控)
7. [生产环境配置](#生产环境配置)
8. [故障排查](#故障排查)

---

## 快速开始

### 无密码模式（开发环境）

```powershell
# 1. 确保 Redis 服务正在运行
Get-Service Redis

# 2. 启动测试脚本
cd C:\Users\27415\PycharmProjects\xionghan-chess\web\server
.\test_redis.ps1

# 3. 启动服务器
python app.py
```

### 密码认证模式（生产环境）

```powershell
# 1. 设置 Redis 密码（在 redis.windows.conf 中添加）
# requirepass YourStrongPassword123!

# 2. 重启 Redis 服务
Restart-Service Redis

# 3. 使用密码启动服务器
.\start_with_redis.ps1 -Password "YourStrongPassword123!"

# 或者设置环境变量
$env:REDIS_PASSWORD = "YourStrongPassword123!"
python app.py
```

---

## 安装 Redis

### Windows 系统

#### 方法一：使用 Chocolatey（推荐）

```powershell
# 安装 Chocolatey（如果还没有）
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# 安装 Redis
choco install redis-64

# 启动服务
redis-server --service-install
redis-server --service-start
```

#### 方法二：手动安装

1. 下载 Redis for Windows: https://github.com/microsoftarchive/redis/releases
2. 解压到 `C:\Program Files\Redis`
3. 安装为服务：
   ```powershell
   cd "C:\Program Files\Redis"
   .\redis-server.exe --service-install
   .\redis-server.exe --service-start
   ```

### 验证安装

```powershell
& "C:\Program Files\Redis\redis-cli.exe" ping
# 应该返回: PONG
```

---

## 测试连接

### 基本连接测试

```powershell
# 测试 Redis 连接
& "C:\Program Files\Redis\redis-cli.exe" ping

# 查看服务器信息
& "C:\Program Files\Redis\redis-cli.exe" INFO server

# 查看内存使用
& "C:\Program Files\Redis\redis-cli.exe" INFO memory
```

### 运行完整测试套件

```powershell
cd C:\Users\27415\PycharmProjects\xionghan-chess\web\server
.\test_redis.ps1
```

测试内容包括：
- ✅ Redis 连接测试
- ✅ 服务器信息获取
- ✅ 清理旧数据
- ✅ 启动 Flask 服务器
- ✅ 创建房间并验证 Redis 存储
- ✅ 查看所有 Redis 键
- ✅ 性能统计
- ✅ 生产环境配置建议

---

## 启动服务器

### 开发模式（无密码）

```powershell
cd web/server
python app.py
```

### 生产模式（带密码）

#### 方式一：使用启动脚本

```powershell
.\start_with_redis.ps1 -Password "YourStrongPassword123!"
```

#### 方式二：设置环境变量

```powershell
$env:REDIS_PASSWORD = "YourStrongPassword123!"
python app.py
```

#### 方式三：永久设置环境变量

```powershell
# 系统级别（需要管理员权限）
[Environment]::SetEnvironmentVariable("REDIS_PASSWORD", "YourStrongPassword123!", "Machine")

# 用户级别
[Environment]::SetEnvironmentVariable("REDIS_PASSWORD", "YourStrongPassword123!", "User")
```

---

## 功能验证

### 1. 创建房间

```powershell
# 使用 PowerShell
$response = Invoke-RestMethod -Uri "http://localhost:5000/api/create_room" -Method POST -ContentType "application/json" -Body '{"mode":"xionghan"}'
Write-Host "房间ID: $($response.roomId)"
```

### 2. 验证 Redis 存储

```powershell
# 查看房间数据
$roomId = "你的房间ID"
& "C:\Program Files\Redis\redis-cli.exe" GET "xionghan_chess:room:$roomId"

# 查看所有房间
& "C:\Program Files\Redis\redis-cli.exe" KEYS "xionghan_chess:room:*"

# 查看玩家映射
& "C:\Program Files\Redis\redis-cli.exe" KEYS "xionghan_chess:player_room:*"
```

### 3. 联机对战测试

1. 打开两个浏览器窗口
2. 访问 `http://localhost:5000/game.html`
3. 第一个窗口：创建房间
4. 第二个窗口：加入房间（输入房间号）
5. 测试走棋同步
6. 观察服务器日志中的移动广播

### 4. 断线重连测试

1. 在游戏中断开一个客户端的网络
2. 等待 10 秒
3. 重新连接网络
4. 刷新页面，使用相同的房间号加入
5. 验证游戏状态是否恢复

---

## 性能监控

### 实时监控脚本

```powershell
cd web/server
.\monitor_redis.ps1
```

监控指标包括：
- 📊 服务器版本和运行时间
- 💾 内存使用情况
- 👥 客户端连接数
- ⚡ 每秒操作数和缓存命中率
- 🗂️ 键空间统计
- ♟️ 雄汉象棋专用数据（房间数、玩家数）
- 💿 持久化状态

### 手动查询命令

```powershell
$redisCli = "C:\Program Files\Redis\redis-cli.exe"

# 实时监视所有命令
& $redisCli MONITOR

# 查看慢查询
& $redisCli SLOWLOG GET 10

# 查看当前连接的客户端
& $redisCli CLIENT LIST

# 查看特定键的 TTL
& $redisCli TTL "xionghan_chess:room:abc12345"

# 删除所有测试数据
& $redisCli KEYS "xionghan_chess:*" | ForEach-Object { & $redisCli DEL $_ }
```

---

## 生产环境配置

### 1. 密码认证（必需）

编辑 `C:\Program Files\Redis\redis.windows.conf`：

```conf
# 设置强密码
requirepass XionghanChess2024!Secure@Redis

# 重命名危险命令
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command CONFIG ""
rename-command DEBUG ""
```

重启 Redis 服务：

```powershell
Restart-Service Redis
```

### 2. 持久化策略

#### RDB 快照（默认启用）

```conf
save 900 1      # 900秒内至少1个键变化
save 300 10     # 300秒内至少10个键变化
save 60 10000   # 60秒内至少10000个键变化

dbfilename dump.rdb
dir "C:/Program Files/Redis/Data/"
```

#### AOF 日志（更可靠）

```conf
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec  # 每秒同步（推荐）
```

### 3. 内存限制

```conf
maxmemory 2gb
maxmemory-policy allkeys-lru  # LRU 淘汰策略
```

### 4. 网络绑定

```conf
# 仅本地访问
bind 127.0.0.1

# 或指定内网 IP
bind 192.168.1.100
```

### 5. 使用生产配置文件

```powershell
# 停止当前服务
Stop-Service Redis

# 使用生产配置启动
& "C:\Program Files\Redis\redis-server.exe" "C:\Users\27415\PycharmProjects\xionghan-chess\web\server\redis.production.conf"
```

---

## 故障排查

### 问题 1：Redis 连接失败

**症状：**
```
⚠️ Redis 连接失败: Error 10061 connecting to localhost:6379
```

**解决方案：**
```powershell
# 检查服务状态
Get-Service Redis

# 启动服务
Start-Service Redis

# 检查端口占用
netstat -ano | findstr :6379
```

### 问题 2：密码认证失败

**症状：**
```
⚠️ Redis 连接失败: ERR Client sent AUTH, but no password is set
```

**解决方案：**
```powershell
# 确认配置文件中已设置密码
Select-String -Path "C:\Program Files\Redis\redis.windows.conf" -Pattern "requirepass"

# 重启 Redis 服务
Restart-Service Redis

# 测试密码连接
& "C:\Program Files\Redis\redis-cli.exe" -a "YourPassword" ping
```

### 问题 3：房间数据未持久化

**症状：**
重启服务器后，房间数据丢失

**解决方案：**
```powershell
# 检查 AOF 是否启用
& "C:\Program Files\Redis\redis-cli.exe" CONFIG GET appendonly

# 检查 RDB 文件位置
& "C:\Program Files\Redis\redis-cli.exe" CONFIG GET dir

# 手动触发保存
& "C:\Program Files\Redis\redis-cli.exe" BGSAVE

# 查看保存状态
& "C:\Program Files\Redis\redis-cli.exe" LASTSAVE
```

### 问题 4：内存溢出

**症状：**
```
OOM command not allowed when used memory > 'maxmemory'
```

**解决方案：**
```powershell
# 查看当前内存使用
& "C:\Program Files\Redis\redis-cli.exe" INFO memory

# 增加内存限制
& "C:\Program Files\Redis\redis-cli.exe" CONFIG SET maxmemory 4gb

# 清理过期键
& "C:\Program Files\Redis\redis-cli.exe" MEMORY PURGE
```

### 问题 5：Socket.IO Redis Adapter 连接失败

**症状：**
```
Error: Redis connection to localhost:6379 failed
```

**解决方案：**
```python
# 在 app.py 中确认 Redis URL 格式正确
if redis_password:
    redis_url = f'redis://:{redis_password}@localhost:6379/0'
else:
    redis_url = 'redis://localhost:6379/0'
```

---

## Redis 键说明

### 数据结构

```
xionghan_chess:room:<room_id>        → Hash (房间完整数据)
xionghan_chess:player_room:<sid>     → String (玩家所在房间ID)
xionghan_chess:ip_connections        → Hash (IP连接计数)
xionghan_chess:move_times            → Hash (移动时间戳)
```

### 示例数据

```json
// xionghan_chess:room:abc12345
{
  "room_id": "abc12345",
  "mode": "xionghan",
  "players": [
    {"sid": "socket_id_1", "camp": "red", "ready": true},
    {"sid": "socket_id_2", "camp": "black", "ready": true}
  ],
  "created_at": "2024-05-21T10:30:00",
  "last_activity": 1716256200,
  "game_started": true,
  "move_history": [],
  "current_turn": "red"
}
```

---

## 下一步

1. **安全加固**：实现服务器端走法合法性验证
2. **性能优化**：配置 Gunicorn + Eventlet 提升并发
3. **监控告警**：集成 Prometheus + Grafana
4. **高可用**：部署 Redis Sentinel 或 Cluster
5. **CDN 加速**：静态资源托管到 CDN

---

## 参考资料

- [Redis 官方文档](https://redis.io/documentation)
- [Flask-SocketIO 文档](https://flask-socketio.readthedocs.io/)
- [Redis 最佳实践](https://redis.io/topics/lru-cache)

---

**最后更新**: 2024-05-21  
**维护者**: 雄汉象棋开发团队
