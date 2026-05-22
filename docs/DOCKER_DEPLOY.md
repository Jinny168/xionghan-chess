# 雄汉象棋 Docker 部署指南

## 📋 目录

1. [快速开始](#快速开始)
2. [环境要求](#环境要求)
3. [部署步骤](#部署步骤)
4. [配置说明](#配置说明)
5. [常用命令](#常用命令)
6. [故障排查](#故障排查)

---

## 快速开始

### Windows 用户

```powershell
# 方式 1：使用启动脚本（推荐）
.\docker-start.ps1

# 方式 2：手动部署
docker compose up -d
```

### Linux/Mac 用户

```bash
# 方式 1：使用启动脚本
chmod +x docker-start.sh
./docker-start.sh

# 方式 2：手动部署
docker-compose up -d
```

访问地址：http://localhost:5000

---

## 环境要求

### 必需软件

- **Docker**: 20.10+ 
- **Docker Compose**: 2.0+

### 安装 Docker

#### Windows
1. 下载 Docker Desktop: https://www.docker.com/products/docker-desktop
2. 安装并重启电脑
3. 启动 Docker Desktop

#### Linux (Ubuntu)
```bash
sudo apt-get update
sudo apt-get install docker.io docker-compose-plugin
sudo systemctl enable --now docker
```

#### macOS
```bash
brew install --cask docker
```

### 验证安装

```bash
docker --version
docker compose version
```

---

## 部署步骤

### 1. 克隆项目

```bash
git clone <repository-url>
cd xionghan-chess
```

### 2. 配置环境变量

```bash
# 复制示例配置
cp .env.example .env

# 编辑配置文件（修改 Redis 密码）
nano .env
```

**.env 文件内容：**
```env
# Redis 密码（生产环境务必修改）
REDIS_PASSWORD=YourStrongPassword123!

# Flask 配置
FLASK_ENV=production
FLASK_DEBUG=0

# Redis 配置
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
```

### 3. 选择部署模式

#### 开发模式（仅 Web + Redis）

```bash
docker compose up -d redis web
```

**特点：**
- ✅ 快速启动
- ✅ 适合本地测试
- ❌ 无 Nginx 反向代理
- ❌ 无 HTTPS 支持

#### 生产模式（Web + Redis + Nginx）

```bash
docker compose --profile production up -d
```

**特点：**
- ✅ Nginx 反向代理
- ✅ 静态资源缓存优化
- ✅ WebSocket 支持
- ✅ Gzip 压缩
- ⚠️ 需要配置 SSL 证书（可选）

### 4. 验证部署

```bash
# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f

# 健康检查
curl http://localhost:5000
```

---

## 配置说明

### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `REDIS_PASSWORD` | `XionghanChess2024!Secure@Redis` | Redis 密码 |
| `REDIS_HOST` | `redis` | Redis 主机地址 |
| `REDIS_PORT` | `6379` | Redis 端口 |
| `REDIS_DB` | `0` | Redis 数据库编号 |
| `FLASK_ENV` | `production` | Flask 运行环境 |
| `FLASK_DEBUG` | `0` | 调试模式（0/1） |

### 端口映射

| 服务 | 容器端口 | 宿主机端口 | 说明 |
|------|----------|------------|------|
| Web | 5000 | 5000 | Flask 应用 |
| Redis | 6379 | 6379 | Redis 数据库 |
| Nginx | 80 | 80 | HTTP（生产模式） |
| Nginx | 443 | 443 | HTTPS（生产模式） |

### 数据持久化

Redis 数据存储在 Docker Volume 中：

```bash
# 查看卷
docker volume ls | grep redis-data

# 备份数据
docker run --rm -v xionghan-chess_redis-data:/data -v $(pwd):/backup alpine tar czf /backup/redis-backup.tar.gz /data

# 恢复数据
docker run --rm -v xionghan-chess_redis-data:/data -v $(pwd):/backup alpine tar xzf /backup/redis-backup.tar.gz -C /
```

---

## 常用命令

### 服务管理

```bash
# 启动服务
docker compose up -d

# 停止服务
docker compose down

# 重启服务
docker compose restart

# 查看状态
docker compose ps

# 查看日志
docker compose logs -f
docker compose logs web    # 只看 Web 日志
docker compose logs redis  # 只看 Redis 日志
```

### 代码更新

```bash
# 重新构建并启动
docker compose up -d --build

# 仅重建 Web 服务
docker compose up -d --build web
```

### 进入容器

```bash
# 进入 Web 容器
docker exec -it xionghan-web bash

# 进入 Redis 容器
docker exec -it xionghan-redis sh

# 在 Redis 容器中执行命令
docker exec -it xionghan-redis redis-cli -a $REDIS_PASSWORD
```

### 清理资源

```bash
# 停止并删除容器、网络
docker compose down

# 删除卷（会丢失数据）
docker compose down -v

# 删除镜像
docker compose down --rmi all

# 完全清理
docker system prune -a --volumes
```

---

## 生产环境配置

### 1. 启用 HTTPS

#### 获取 SSL 证书

```bash
# 使用 Let's Encrypt（免费）
docker run -it --rm \
  -v ./docker/config/nginx/ssl:/etc/letsencrypt \
  certbot/certbot certonly \
  --standalone \
  -d your-domain.com
```

#### 配置 Nginx

编辑 `docker/config/nginx/nginx.conf`，取消注释 HTTPS 部分：

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    # ... 其他配置
}
```

### 2. 修改默认密码

编辑 `.env` 文件：

```env
REDIS_PASSWORD=YourVeryStrongPassword!@#$%
```

### 3. 限制资源使用

编辑 `docker-compose.yml`：

```yaml
services:
  web:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
  
  redis:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
```

### 4. 配置日志轮转

创建 `docker-compose.override.yml`：

```yaml
services:
  web:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
  
  redis:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

---

## 故障排查

### 问题 1：容器无法启动

**症状：**
```
ERROR: for xionghan-web  Cannot start service web
```

**解决：**
```bash
# 查看详细日志
docker compose logs web

# 检查端口占用
netstat -ano | findstr :5000

# 删除旧容器重新启动
docker compose down
docker compose up -d
```

### 问题 2：Redis 连接失败

**症状：**
```
⚠️ Redis 连接失败: Error 111 connecting to redis:6379
```

**解决：**
```bash
# 检查 Redis 容器状态
docker compose ps redis

# 查看 Redis 日志
docker compose logs redis

# 测试 Redis 连接
docker exec -it xionghan-redis redis-cli -a $REDIS_PASSWORD ping

# 重启 Redis
docker compose restart redis
```

### 问题 3：WebSocket 连接失败

**症状：**
浏览器控制台显示 `WebSocket connection failed`

**解决：**
```bash
# 检查 Nginx 配置
docker compose logs nginx

# 验证 WebSocket 支持
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" http://localhost/socket.io/

# 重启 Nginx
docker compose restart nginx
```

### 问题 4：静态资源 404

**症状：**
页面加载但 CSS/JS 文件找不到

**解决：**
```bash
# 检查文件挂载
docker exec xionghan-web ls -la /app/web

# 重新构建
docker compose up -d --build web

# 清除浏览器缓存（Ctrl+F5）
```

### 问题 5：性能问题

**症状：**
响应缓慢，内存占用高

**解决：**
```bash
# 查看资源使用
docker stats

# 清理未使用的资源
docker system prune -a

# 增加 Redis 内存限制
docker exec xionghan-redis redis-cli -a $REDIS_PASSWORD CONFIG SET maxmemory 2gb
```

---

## 监控与维护

### 健康检查

```bash
# 查看所有服务健康状态
docker compose ps

# 手动健康检查
curl http://localhost:5000/health
```

### 备份与恢复

```bash
# 备份 Redis 数据
docker exec xionghan-redis redis-cli -a $REDIS_PASSWORD BGSAVE

# 导出 RDB 文件
docker cp xionghan-redis:/data/dump.rdb ./backup/dump.rdb

# 恢复数据
docker cp ./backup/dump.rdb xionghan-redis:/data/dump.rdb
docker compose restart redis
```

### 日志管理

```bash
# 查看最近 100 行日志
docker compose logs --tail=100

# 导出日志到文件
docker compose logs > logs.txt

# 实时跟踪日志
docker compose logs -f | grep ERROR
```

---

## 架构说明

```
┌─────────────┐
│   Client    │
│  (Browser)  │
└──────┬──────┘
       │
       │ HTTP/WebSocket
       ▼
┌─────────────┐
│   Nginx     │ ◄── 反向代理、静态资源、SSL
│  (Optional) │
└──────┬──────┘
       │
       │ Proxy Pass
       ▼
┌─────────────┐
│  Flask Web  │ ◄── 业务逻辑、WebSocket
│   Server    │
└──────┬──────┘
       │
       │ Redis Protocol
       ▼
┌─────────────┐
│   Redis     │ ◄── 房间状态、会话管理
│   Server    │
└─────────────┘
```

---

## 下一步

1. **安全加固**：配置防火墙、 fail2ban
2. **监控告警**：集成 Prometheus + Grafana
3. **自动化部署**：配置 CI/CD 流水线
4. **负载均衡**：多实例部署 + HAProxy
5. **数据库迁移**：PostgreSQL 集成

---

**最后更新**: 2024-05-21  
**维护者**: 雄汉象棋开发团队
