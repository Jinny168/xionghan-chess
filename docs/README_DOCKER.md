# 雄汉象棋 - Docker 一键部署

## 🚀 快速开始（3步部署）

### Windows 用户

```powershell
# 1. 复制环境配置
copy .env.example .env

# 2. 编辑 .env 文件修改密码（可选）
notepad .env

# 3. 一键启动
.\docker-start.ps1
```

### Linux/Mac 用户

```bash
# 1. 复制环境配置
cp .env.example .env

# 2. 编辑 .env 文件修改密码（可选）
nano .env

# 3. 一键启动
chmod +x docker-start.sh
./docker-start.sh
```

访问：http://localhost:5000

---

## 📦 包含的服务

- ✅ **Flask Web 服务器** - 游戏后端
- ✅ **Redis** - 房间状态管理
- ✅ **Nginx** - 反向代理（生产模式）

---

## 🔧 常用命令

```bash
# 启动服务
docker compose up -d

# 查看日志
docker compose logs -f

# 停止服务
docker compose down

# 更新代码
docker compose up -d --build
```

---

## 📖 详细文档

完整部署指南请查看：[DOCKER_DEPLOY.md](DOCKER_DEPLOY.md)

---

## ❓ 常见问题

**Q: Docker 未安装？**  
A: 下载 Docker Desktop: https://www.docker.com/products/docker-desktop

**Q: 端口被占用？**  
A: 修改 `docker-compose.yml` 中的端口映射

**Q: 如何修改 Redis 密码？**  
A: 编辑 `.env` 文件中的 `REDIS_PASSWORD`

---

**状态**: ✅ 已就绪，可以部署
