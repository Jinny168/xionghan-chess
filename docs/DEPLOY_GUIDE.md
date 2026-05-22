# 雄汉象棋部署指南

> 🎯 **目标**：3分钟内完成部署，30分钟掌握全部功能

## 📋 目录

- [快速开始](#快速开始) - 3分钟部署
- [Docker 部署详解](#docker-部署详解) - 完整配置说明
- [Linux 环境准备](#linux-环境准备) - 虚拟机安装教程
- [配置说明](#配置说明) - 环境变量和端口
- [常用命令](#常用命令) - 日常管理
- [故障排查](#故障排查) - 常见问题解决
- [生产环境优化](#生产环境优化) - HTTPS、安全加固

---

## 快速开始

### 前置要求

- ✅ Docker 20.10+
- ✅ Docker Compose 2.0+

**没有 Docker？** → [安装 Docker](#安装-docker)

### Windows 用户（推荐）

```powershell
# 进入 docker 目录
cd docker/scripts/windows

# 一键启动
.\docker-start.ps1
```

### Linux/Mac 用户

```bash
# 进入 docker 目录
cd docker/scripts/linux

# 一键部署
chmod +x deploy.sh
sudo ./deploy.sh
```

### 验证部署

访问：http://localhost:5000

看到游戏首页即成功！🎉

---

## Docker 部署详解

### 部署模式选择

#### 开发模式（推荐新手）

```bash
# 仅启动 Web + Redis
docker-compose -f docker/config/docker-compose.yml up -d redis web
```

**特点**：
- ✅ 快速启动（30秒）
- ✅ 适合本地测试
- ❌ 无 Nginx 反向代理

#### 生产模式（推荐上线）

```bash
# 启动 Web + Redis + Nginx
docker-compose -f docker/config/docker-compose.yml --profile production up -d
```

**特点**：
- ✅ Nginx 反向代理
- ✅ 静态资源缓存
- ✅ WebSocket 优化
- ✅ Gzip 压缩

### 手动部署步骤

#### 1. 配置环境变量

```bash
# 复制配置模板
cp docker/config/.env.example docker/config/.env

# 编辑配置
nano docker/config/.env
```

**.env 文件内容**：

```env
# Redis 密码（生产环境务必修改）
REDIS_PASSWORD=YourStrongPassword123!

# Flask 配置
FLASK_ENV=production
FLASK_DEBUG=0

# Redis 配置（无需修改）
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
```

#### 2. 启动服务

```bash
# 开发模式
docker-compose -f docker/config/docker-compose.yml up -d redis web

# 生产模式
docker-compose -f docker/config/docker-compose.yml --profile production up -d
```

#### 3. 查看状态

```bash
# 查看容器状态
docker-compose -f docker/config/docker-compose.yml ps

# 查看日志
docker-compose -f docker/config/docker-compose.yml logs -f
```

---

## Linux 环境准备

### 虚拟机配置建议

| 配置项 | 最低要求 | 推荐配置 |
|--------|----------|----------|
| CPU | 2 核 | 4 核 |
| 内存 | 2 GB | 4 GB |
| 硬盘 | 20 GB | 40 GB |
| 网络 | NAT/桥接 | 桥接模式 |

### 安装 Ubuntu 虚拟机

#### 方法一：VirtualBox（免费）

1. **下载软件**
   - VirtualBox: https://www.virtualbox.org/wiki/Downloads
   - Ubuntu 22.04 LTS: https://ubuntu.com/download/desktop

2. **创建虚拟机**
   ```
   1. 打开 VirtualBox，点击"新建"
   2. 名称：XionghanChess
   3. 类型：Linux，版本：Ubuntu (64-bit)
   4. 内存：4096 MB
   5. 硬盘：40GB
   6. 网络：桥接网卡
   ```

3. **安装 Ubuntu**
   - 加载 ISO 文件，按提示安装
   - 设置用户名和密码

#### 方法二：VMware Workstation（付费）

步骤类似，界面更友好。

### 获取 Linux IP 地址

```bash
ip addr show
```

找到类似输出：
```
inet 192.168.1.100/24 brd 192.168.1.255 scope global dynamic noprefixroute eth0
```

记住 IP：**192.168.1.100**

### 从 Windows 连接 Linux

#### 使用 MobaXterm（推荐）

1. 下载：https://mobaxterm.mobatek.net/
2. 创建 SSH 会话：
   - Remote host: Linux IP
   - Username: Linux 用户名
   - 输入密码

3. 测试连接：
   ```bash
   pwd
   ls -la
   ```

### 安装 Docker

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装依赖
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

# 添加 Docker GPG 密钥
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# 添加 Docker 仓库
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装 Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io

# 验证安装
docker --version
```

### 安装 Docker Compose

```bash
# 下载 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# 添加执行权限
sudo chmod +x /usr/local/bin/docker-compose

# 验证安装
docker-compose --version
```

### 配置 Docker 权限

```bash
# 将当前用户添加到 docker 组
sudo usermod -aG docker $USER

# 刷新权限
newgrp docker

# 测试
docker run hello-world
```

### 上传项目文件

#### 方法一：Git（推荐）

```bash
cd ~
git clone <repository-url>
cd xionghan-chess
```

#### 方法二：MobaXterm 文件传输

1. 在 MobaXterm 左侧找到项目文件夹
2. 拖拽到右侧 Linux 文件浏览器
3. 等待上传完成

#### 方法三：scp 命令

在 **Windows PowerShell** 中执行：

```powershell
scp -r C:\Users\27415\PycharmProjects\xionghan-chess username@192.168.1.100:~/
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
docker-compose -f docker/config/docker-compose.yml up -d

# 停止服务
docker-compose -f docker/config/docker-compose.yml down

# 重启服务
docker-compose -f docker/config/docker-compose.yml restart

# 查看状态
docker-compose -f docker/config/docker-compose.yml ps

# 查看日志
docker-compose -f docker/config/docker-compose.yml logs -f
docker-compose -f docker/config/docker-compose.yml logs web    # 只看 Web
docker-compose -f docker/config/docker-compose.yml logs redis  # 只看 Redis
```

### 代码更新

```bash
# 重新构建并启动
docker-compose -f docker/config/docker-compose.yml up -d --build

# 仅重建 Web 服务
docker-compose -f docker/config/docker-compose.yml up -d --build web
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
docker-compose -f docker/config/docker-compose.yml down

# 删除卷（会丢失数据）
docker-compose -f docker/config/docker-compose.yml down -v

# 删除镜像
docker-compose -f docker/config/docker-compose.yml down --rmi all

# 完全清理
docker system prune -a --volumes
```

---

## 故障排查

### 问题 1：容器无法启动

**症状**：
```
ERROR: for xionghan-web  Cannot start service web
```

**解决**：
```bash
# 查看详细日志
docker-compose -f docker/config/docker-compose.yml logs web

# 检查端口占用
netstat -ano | findstr :5000

# 删除旧容器重新启动
docker-compose -f docker/config/docker-compose.yml down
docker-compose -f docker/config/docker-compose.yml up -d
```

### 问题 2：Redis 连接失败

**症状**：
```
⚠️ Redis 连接失败: Error 111 connecting to redis:6379
```

**解决**：
```bash
# 检查 Redis 容器状态
docker-compose -f docker/config/docker-compose.yml ps redis

# 查看 Redis 日志
docker-compose -f docker/config/docker-compose.yml logs redis

# 测试 Redis 连接
docker exec -it xionghan-redis redis-cli -a $REDIS_PASSWORD ping

# 重启 Redis
docker-compose -f docker/config/docker-compose.yml restart redis
```

### 问题 3：WebSocket 连接失败

**症状**：
浏览器控制台显示 `WebSocket connection failed`

**解决**：
```bash
# 检查 Nginx 配置
docker-compose -f docker/config/docker-compose.yml logs nginx

# 验证 WebSocket 支持
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" http://localhost/socket.io/

# 重启 Nginx
docker-compose -f docker/config/docker-compose.yml restart nginx
```

### 问题 4：静态资源 404

**症状**：
页面加载但 CSS/JS 文件找不到

**解决**：
```bash
# 检查文件挂载
docker exec xionghan-web ls -la /app/web

# 重新构建
docker-compose -f docker/config/docker-compose.yml up -d --build web

# 清除浏览器缓存（Ctrl+F5）
```

### 问题 5：性能问题

**症状**：
响应缓慢，内存占用高

**解决**：
```bash
# 查看资源使用
docker stats

# 清理未使用的资源
docker system prune -a

# 增加 Redis 内存限制
docker exec xionghan-redis redis-cli -a $REDIS_PASSWORD CONFIG SET maxmemory 2gb
```

### 问题 6：无法从 Windows 访问

**症状**：
浏览器显示 "无法访问此网站"

**解决**：

1. **检查 Linux IP 是否正确**
   ```bash
   ip addr show
   ```

2. **检查防火墙**
   ```bash
   sudo ufw status
   sudo ufw allow 80/tcp
   sudo ufw allow 5000/tcp
   ```

3. **检查容器是否运行**
   ```bash
   docker-compose -f docker/config/docker-compose.yml ps
   ```

4. **在 Linux 本机测试**
   ```bash
   curl http://localhost
   ```
   如果本机可以访问，说明是网络问题。

5. **检查虚拟机网络设置**
   - VirtualBox：确保使用"桥接网卡"
   - VMware：确保使用"桥接模式"

---

## 生产环境优化

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

编辑 `docker/config/.env` 文件：

```env
REDIS_PASSWORD=YourVeryStrongPassword!@#$%
```

重启服务：

```bash
docker-compose -f docker/config/docker-compose.yml down
docker-compose -f docker/config/docker-compose.yml up -d
```

### 3. 限制资源使用

编辑 `docker/config/docker-compose.yml`：

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

创建 `docker/config/docker-compose.override.yml`：

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

### 5. 配置防火墙

```bash
# 启用防火墙
sudo ufw enable

# 只开放必要端口
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS

# 拒绝其他所有连接
sudo ufw default deny incoming

# 查看规则
sudo ufw status verbose
```

### 6. 开机自启动

```bash
# 启用 Docker 服务开机自启
sudo systemctl enable docker

# 容器已配置 restart: unless-stopped，无需额外配置
```

---

## 监控与维护

### 健康检查

```bash
# 查看所有服务健康状态
docker-compose -f docker/config/docker-compose.yml ps

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
docker-compose -f docker/config/docker-compose.yml restart redis
```

### 日志管理

```bash
# 查看最近 100 行日志
docker-compose -f docker/config/docker-compose.yml logs --tail=100

# 导出日志到文件
docker-compose -f docker/config/docker-compose.yml logs > logs.txt

# 实时跟踪日志
docker-compose -f docker/config/docker-compose.yml logs -f | grep ERROR
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

## 下一步学习

1. **HTTPS 配置** - 使用 Let's Encrypt 免费证书
2. **域名绑定** - 购买域名并解析到你的服务器
3. **监控告警** - 集成 Prometheus + Grafana
4. **自动化部署** - 配置 CI/CD 流水线
5. **负载均衡** - 多服务器部署

---

## 获取帮助

如果遇到问题：

1. **查看日志**：`docker-compose -f docker/config/docker-compose.yml logs -f`
2. **查阅文档**：[docs/README.md](README.md)
3. **搜索错误信息**：将错误信息复制到搜索引擎
4. **检查社区**：GitHub Issues、Stack Overflow

---

**最后更新**: 2024-05-22  
**维护者**: 雄汉象棋开发团队
