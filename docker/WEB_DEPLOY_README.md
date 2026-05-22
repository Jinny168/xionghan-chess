# Web 版本快速部署指南

本指南仅针对 Web 版本的 Docker 部署。

## 📦 部署包内容

```
xionghan-chess-web/
├── web/                  # Web 应用代码
│   ├── css/             # 样式文件
│   ├── js/              # JavaScript 代码
│   ├── server/          # Flask 后端
│   │   ├── app.py       # 主应用
│   │   └── requirements.txt
│   ├── images/          # 图片资源
│   ├── sounds/          # 音效文件
│   ├── index.html       # 主页
│   └── game.html        # 游戏页面
├── docker/              # Docker 配置
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── .env.example
│   ├── .dockerignore
│   ├── nginx/
│   │   └── nginx.conf
│   ├── deploy.sh        # Linux 一键部署
│   └── check_deploy.sh  # 环境检查
└── docs/                # 文档
    ├── DOCKER_DEPLOY.md
    └── LINUX_DEPLOY_GUIDE.md
```

## 🚀 快速部署（3步）

### 步骤 1：上传到 Linux

```bash
# 在 Linux 上
cd ~/projects
unzip xionghan-chess-web.zip
cd xionghan-chess-web
```

### 步骤 2：配置环境变量

```bash
# 复制配置模板
cp docker/.env.example docker/.env

# 编辑密码（可选，有默认值）
nano docker/.env
```

### 步骤 3：一键部署

```bash
# 添加执行权限
chmod +x docker/deploy.sh

# 运行部署
sudo ./docker/deploy.sh
```

访问：`http://你的LinuxIP`

---

## 📋 详细步骤

### 1. 环境准备

确保已安装 Docker 和 Docker Compose：

```bash
# 检查 Docker
docker --version
docker-compose --version

# 如果未安装，运行检查脚本
chmod +x docker/check_deploy.sh
./docker/check_deploy.shsud
```

### 2. 配置文件说明

#### docker/.env

```env
# Redis 密码（生产环境务必修改）
REDIS_PASSWORD=XionghanChess2024!Secure@Redis

# Flask 配置
FLASK_ENV=production
FLASK_DEBUG=0

# Redis 配置（无需修改）
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
```

### 3. 启动服务

```bash
# 开发模式（仅 Web + Redis）
docker-compose -f docker/docker-compose.yml up -d redis web

# 生产模式（Web + Redis + Nginx）
docker-compose -f docker/docker-compose.yml --profile production up -d
```

### 4. 验证部署

```bash
# 查看服务状态
docker-compose -f docker/docker-compose.yml ps

# 查看日志
docker-compose -f docker/docker-compose.yml logs -f

# 测试访问
curl http://localhost
```

---

## 🔧 常用命令

```bash
# 停止服务
docker-compose -f docker/docker-compose.yml down

# 重启服务
docker-compose -f docker/docker-compose.yml restart

# 查看日志
docker-compose -f docker/docker-compose.yml logs -f web

# 更新代码后重新部署
docker-compose -f docker/docker-compose.yml up -d --build

# 进入容器
docker exec -it xionghan-web bash
```

---

## 📊 服务说明

| 服务 | 端口 | 说明 |
|------|------|------|
| web | 5000 | Flask 应用服务器 |
| redis | 6379 | Redis 数据库（房间状态） |
| nginx | 80/443 | Nginx 反向代理（生产模式） |

---

## ❓ 常见问题

### Q: 无法访问网站？

```bash
# 检查防火墙
sudo ufw allow 80/tcp
sudo ufw allow 5000/tcp

# 检查服务状态
docker-compose -f docker/docker-compose.yml ps

# 查看日志
docker-compose -f docker/docker-compose.yml logs web
```

### Q: Redis 连接失败？

```bash
# 检查 Redis 容器
docker-compose -f docker/docker-compose.yml logs redis

# 重启 Redis
docker-compose -f docker/docker-compose.yml restart redis
```

### Q: 如何备份数据？

```bash
# 备份 Redis 数据
docker exec xionghan-redis redis-cli -a $REDIS_PASSWORD BGSAVE
docker cp xionghan-redis:/data/dump.rdb ./backup.rdb
```

---

## 📖 更多文档

- [DOCKER_DEPLOY.md](../docs/DOCKER_DEPLOY.md) - 完整 Docker 部署指南
- [LINUX_DEPLOY_GUIDE.md](../docs/LINUX_DEPLOY_GUIDE.md) - Linux 虚拟机部署教程

---

**最后更新**: 2024-05-21
