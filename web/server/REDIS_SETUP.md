# Redis 集成安装指南

## 1. 安装 Redis

### Windows 系统
1. 下载并安装 Redis for Windows：
   - 推荐方式：使用 WSL2 (Windows Subsystem for Linux)
   - 或使用 Chocolatey：`choco install redis`
   
2. 启动 Redis 服务：
   ```powershell
   redis-server
   ```

### Linux / macOS
```bash
# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# macOS
brew install redis
brew services start redis
```

## 2. 安装 Python 依赖

```bash
cd web/server
pip install -r requirements.txt
```

## 3. 验证 Redis 连接

```bash
redis-cli ping
# 应该返回 PONG
```

## 4. 启动服务器

```bash
cd web/server
python app.py
```

启动时应该看到：
```
✅ Redis 连接成功
```

如果 Redis 未运行，系统会自动回退到内存模式：
```
⚠️ Redis 连接失败，回退到内存模式
```

## 5. Redis 键说明

系统使用以下 Redis 键结构：

- `xionghan_chess:room:<room_id>` - 房间数据（JSON格式）
- `xionghan_chess:player_room:<player_sid>` - 玩家到房间的映射
- `xionghan_chess:ip_connections` - IP 连接计数（Hash）
- `xionghan_chess:move_times` - 移动时间戳（Hash，用于频率限制）

## 6. 监控 Redis

```bash
# 查看所有键
redis-cli keys "xionghan_chess:*"

# 查看房间数据
redis-cli get "xionghan_chess:room:EEAA3F3A"

# 查看内存使用
redis-cli info memory

# 清空所有数据（谨慎使用）
redis-cli flushdb
```

## 7. 生产环境配置

### 7.1 启用 Redis 认证

编辑 `redis.conf`：
```
requirepass your_strong_password
```

修改 `app.py` 中的 Redis 连接：
```python
redis_client = redis.Redis(
    host='localhost', 
    port=6379, 
    db=0, 
    password='your_strong_password',
    decode_responses=True
)
```

### 7.2 配置 Socket.IO Redis 适配器

```python
socketio_kwargs['client_manager'] = socketio.RedisManager(
    'redis://:your_strong_password@localhost:6379/0'
)
```

### 7.3 多服务器部署

使用 Nginx 作为负载均衡器，多个 Flask 实例共享同一个 Redis：

```nginx
upstream xionghan_chess {
    server 127.0.0.1:5001;
    server 127.0.0.1:5002;
    server 127.0.0.1:5003;
}

server {
    listen 80;
    location / {
        proxy_pass http://xionghan_chess;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## 8. 性能优化建议

1. **Redis 配置优化**：
   ```
   maxmemory 256mb
   maxmemory-policy allkeys-lru
   ```

2. **启用持久化**（RDB + AOF）：
   ```
   save 900 1
   save 300 10
   save 60 10000
   appendonly yes
   ```

3. **监控告警**：
   - 使用 Redis Commander 或 RedisInsight 进行可视化监控
   - 配置 Prometheus + Grafana 监控 Redis 性能指标

## 9. 故障排查

### 问题：Redis 连接失败
```bash
# 检查 Redis 是否运行
redis-cli ping

# 检查端口是否被占用
netstat -ano | findstr 6379

# 查看 Redis 日志
tail -f /var/log/redis/redis-server.log
```

### 问题：内存使用过高
```bash
# 查看内存使用详情
redis-cli info memory

# 查看大键
redis-cli --bigkeys

# 手动清理过期键
redis-cli --scan --pattern "xionghan_chess:*" | xargs redis-cli expireat 1
```

## 10. 备份与恢复

```bash
# 备份
redis-cli BGSAVE

# 恢复
# 将 dump.rdb 文件复制到 Redis 数据目录
# 重启 Redis 服务
```
