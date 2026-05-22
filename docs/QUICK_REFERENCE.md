# 雄汉象棋 - 快速参考卡片

> ⚡ 常用命令速查，3秒找到答案

## 🚀 一键部署

### Windows
```powershell
cd docker/scripts/windows
.\docker-start.ps1
```

### Linux/Mac
```bash
cd docker/scripts/linux
chmod +x deploy.sh
sudo ./deploy.sh
```

访问：http://localhost:5000

---

## 📦 核心命令

```bash
# 启动服务
docker-compose -f docker/config/docker-compose.yml up -d

# 停止服务
docker-compose -f docker/config/docker-compose.yml down

# 重启服务
docker-compose -f docker/config/docker-compose.yml restart

# 查看状态
docker-compose -f docker/config/docker-compose.yml ps

# 查看日志
docker-compose -f docker/config/docker-compose.yml logs -f

# 更新代码
docker-compose -f docker/config/docker-compose.yml up -d --build
```

---

## 🔧 配置管理

```bash
# 复制配置模板
cp docker/config/.env.example docker/config/.env

# 编辑配置
nano docker/config/.env

# 修改 Redis 密码
REDIS_PASSWORD=YourStrongPassword123!
```

---

## 🐛 故障排查

### 容器无法启动
```bash
docker-compose -f docker/config/docker-compose.yml logs web
docker-compose -f docker/config/docker-compose.yml down
docker-compose -f docker/config/docker-compose.yml up -d
```

### Redis 连接失败
```bash
docker-compose -f docker/config/docker-compose.yml logs redis
docker exec -it xionghan-redis redis-cli -a $REDIS_PASSWORD ping
docker-compose -f docker/config/docker-compose.yml restart redis
```

### WebSocket 失败
```bash
docker-compose -f docker/config/docker-compose.yml logs nginx
docker-compose -f docker/config/docker-compose.yml restart nginx
```

### 无法访问
```bash
# 检查防火墙
sudo ufw allow 80/tcp
sudo ufw allow 5000/tcp

# 检查 IP
ip addr show

# 本机测试
curl http://localhost
```

---

## 💾 数据备份

```bash
# 备份 Redis
docker exec xionghan-redis redis-cli -a $REDIS_PASSWORD BGSAVE
docker cp xionghan-redis:/data/dump.rdb ./backup.rdb

# 恢复数据
docker cp ./backup.rdb xionghan-redis:/data/dump.rdb
docker-compose -f docker/config/docker-compose.yml restart redis
```

---

## 🔍 调试命令

```bash
# 进入 Web 容器
docker exec -it xionghan-web bash

# 进入 Redis 容器
docker exec -it xionghan-redis sh

# 查看资源使用
docker stats

# 清理未使用资源
docker system prune -a --volumes
```

---

## 📊 服务说明

| 服务 | 端口 | 说明 |
|------|------|------|
| Web | 5000 | Flask 应用服务器 |
| Redis | 6379 | Redis 数据库 |
| Nginx | 80/443 | 反向代理（生产模式） |

---

## 📖 详细文档

完整指南请查看：[DEPLOY_GUIDE.md](DEPLOY_GUIDE.md)

---

**提示**：将本文档加入书签，随时查阅！🔖
