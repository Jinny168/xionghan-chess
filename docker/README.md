# Docker 部署配置

本目录包含雄汉象棋的 Docker 部署相关文件和脚本。

## 📁 文件说明

### 核心配置文件
- `Dockerfile` - Flask 应用容器镜像定义
- `docker-compose.yml` - 多服务编排配置
- `.env.example` - 环境变量模板
- `.dockerignore` - Docker 构建忽略文件

### Nginx 配置
- `nginx/nginx.conf` - Nginx 反向代理配置

### 部署脚本
- `docker-start.bat` - Windows 批处理启动脚本
- `docker-start.ps1` - PowerShell 启动脚本（推荐）
- `deploy.sh` - Linux 一键部署脚本
- `check_deploy.sh` - Linux 环境检查脚本

## 🚀 快速开始

### Windows 用户

```powershell
# 复制环境变量配置
copy .env.example .env

# 编辑配置（修改密码）
notepad .env

# 一键启动
.\docker-start.ps1
```

### Linux 用户

```bash
# 复制环境变量配置
cp .env.example .env

# 编辑配置（修改密码）
nano .env

# 运行环境检查
chmod +x check_deploy.sh
./check_deploy.sh

# 一键部署
chmod +x deploy.sh
sudo ./deploy.sh
```

## 📖 详细文档

完整的部署指南请查看项目根目录的文档：

- [DOCKER_DEPLOY.md](../docs/DOCKER_DEPLOY.md) - Docker 完整部署指南
- [LINUX_DEPLOY_GUIDE.md](../docs/LINUX_DEPLOY_GUIDE.md) - Linux 虚拟机部署教程（小白版）
- [README_DOCKER.md](../docs/README_DOCKER.md) - Docker 快速参考

## 🔧 常用命令

```bash
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 更新代码
docker-compose up -d --build

# 查看状态
docker-compose ps
```

## ⚙️ 架构说明

```
┌─────────────┐
│   Client    │  浏览器
└──────┬──────┘
       │ HTTP/WebSocket
       ▼
┌─────────────┐
│   Nginx     │  反向代理、静态资源、SSL
└──────┬──────┘
       │ Proxy Pass
       ▼
┌─────────────┐
│  Flask Web  │  游戏后端、WebSocket
└──────┬──────┘
       │ Redis Protocol
       ▼
┌─────────────┐
│   Redis     │  房间状态、会话管理
└─────────────┘
```

## 📋 服务说明

| 服务 | 端口 | 说明 |
|------|------|------|
| web | 5000 | Flask 应用服务器 |
| redis | 6379 | Redis 数据库 |
| nginx | 80/443 | Nginx 反向代理（生产模式） |

## 🔒 安全提示

1. **务必修改默认密码** - 编辑 `.env` 文件中的 `REDIS_PASSWORD`
2. **生产环境启用 HTTPS** - 配置 SSL 证书
3. **定期更新镜像** - `docker-compose pull && docker-compose up -d`
4. **备份重要数据** - Redis 数据卷需要定期备份

---

**最后更新**: 2024-05-21
