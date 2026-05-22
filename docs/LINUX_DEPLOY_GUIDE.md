# 雄汉象棋 Linux 虚拟机部署教程（小白版）

## 📋 目录

1. [准备工作](#准备工作)
2. [Linux 系统准备](#linux-系统准备)
3. [安装 Docker](#安装-docker)
4. [上传项目文件](#上传项目文件)
5. [配置环境变量](#配置环境变量)
6. [启动服务](#启动服务)
7. [访问测试](#访问测试)
8. [常见问题](#常见问题)

---

## 准备工作

### 你需要准备的东西

1. ✅ **Windows 电脑** - 开发环境
2. ✅ **Linux 虚拟机** - 推荐使用 Ubuntu 22.04 LTS
3. ✅ **网络连接** - Windows 和 Linux 能互相访问
4. ✅ **SSH 客户端** - 推荐使用 MobaXterm 或 Xshell

### 虚拟机配置建议

| 配置项 | 最低要求 | 推荐配置 |
|--------|----------|----------|
| CPU | 2 核 | 4 核 |
| 内存 | 2 GB | 4 GB |
| 硬盘 | 20 GB | 40 GB |
| 网络 | NAT/桥接 | 桥接模式 |

---

## Linux 系统准备

### 步骤 1：安装 Ubuntu 虚拟机

#### 方法一：使用 VirtualBox（免费）

1. **下载 VirtualBox**
   - 访问：https://www.virtualbox.org/wiki/Downloads
   - 下载 Windows 版本并安装

2. **下载 Ubuntu 镜像**
   - 访问：https://ubuntu.com/download/desktop
   - 推荐：Ubuntu 22.04 LTS

3. **创建虚拟机**
   ```
   1. 打开 VirtualBox，点击"新建"
   2. 名称：XionghanChess
   3. 类型：Linux
   4. 版本：Ubuntu (64-bit)
   5. 内存：4096 MB (4GB)
   6. 硬盘：创建虚拟硬盘，40GB
   7. 网络：选择"桥接网卡"
   ```

4. **安装 Ubuntu**
   ```
   1. 选中虚拟机，点击"启动"
   2. 选择下载的 Ubuntu ISO 文件
   3. 按照提示安装（选择中文、设置用户名密码）
   4. 安装完成后重启
   ```

#### 方法二：使用 VMware Workstation（付费但更好用）

步骤类似 VirtualBox，界面更友好。

---

### 步骤 2：获取 Linux IP 地址

在 Linux 虚拟机中打开终端，执行：

```bash
ip addr show
```

找到类似这样的输出：
```
inet 192.168.1.100/24 brd 192.168.1.255 scope global dynamic noprefixroute eth0
```

记住这个 IP 地址：**192.168.1.100**（你的可能不同）

---

### 步骤 3：从 Windows 连接到 Linux

#### 使用 MobaXterm（推荐新手）

1. **下载 MobaXterm**
   - 访问：https://mobaxterm.mobatek.net/
   - 下载 Home Edition（免费版）

2. **创建 SSH 会话**
   ```
   1. 打开 MobaXterm
   2. 点击 "Session"
   3. 选择 "SSH"
   4. Remote host: 输入 Linux 的 IP 地址
   5. Specify username: 输入你的 Linux 用户名
   6. 点击 "OK"
   7. 输入密码
   ```

3. **测试连接**
   ```bash
   # 在 MobaXterm 中输入
   pwd
   ls -la
   ```

如果能看到文件列表，说明连接成功！

---

## 安装 Docker

### 步骤 1：更新系统

在 MobaXterm 中执行：

```bash
# 更新软件包列表
sudo apt update

# 升级已安装的软件
sudo apt upgrade -y
```

等待完成（可能需要几分钟）。

---

### 步骤 2：安装 Docker

复制以下命令，在 MobaXterm 中一次性粘贴执行：

```bash
# 安装必要的依赖
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

# 添加 Docker 官方 GPG 密钥
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# 添加 Docker 仓库
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 更新软件包列表
sudo apt update

# 安装 Docker
sudo apt install -y docker-ce docker-ce-cli containerd.io

# 验证安装
docker --version
```

应该看到类似输出：
```
Docker version 24.0.7, build afdd53b
```

---

### 步骤 3：安装 Docker Compose

```bash
# 下载 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# 添加执行权限
sudo chmod +x /usr/local/bin/docker-compose

# 验证安装
docker-compose --version
```

应该看到类似输出：
```
Docker Compose version v2.23.0
```

---

### 步骤 4：配置当前用户使用 Docker

```bash
# 将当前用户添加到 docker 组
sudo usermod -aG docker $USER

# 刷新组权限（需要重新登录才能生效）
newgrp docker

# 测试是否可以不用 sudo 运行 docker
docker run hello-world
```

如果看到 "Hello from Docker!" 消息，说明配置成功！

---

## 上传项目文件

### 方法一：使用 Git（推荐）

#### 在 Linux 上克隆项目

```bash


```

如果没有 Git 仓库，使用方法二。

---

### 方法二：使用 MobaXterm 文件传输

1. **在 MobaXterm 左侧找到 SFTP 面板**
   - 通常会自动显示
   - 如果没有，点击 "Start local terminal" 旁边的 SFTP 标签

2. **上传文件**
   ```
   1. 在 MobaXterm 左侧本地文件浏览器中找到项目文件夹
   2. 选中所有文件
   3. 拖拽到右侧的 Linux 文件浏览器中
   4. 等待上传完成
   ```

3. **验证上传**
   ```bash
   cd ~/xionghan-chess
   ls -la
   ```

应该能看到项目文件。

---

### 方法三：使用 scp 命令（命令行方式）

在 **Windows PowerShell** 中执行：

```powershell
# 上传整个项目文件夹
scp -r C:\Users\27415\PycharmProjects\xionghan-chess username@192.168.1.100:~/

# 替换 username 为你的 Linux 用户名
# 替换 192.168.1.100 为你的 Linux IP
```

---

## 配置环境变量

### 步骤 1：复制配置文件

在 MobaXterm 中执行：

```bash
# 进入项目目录
cd ~/xionghan-chess

# 复制环境变量模板
cp .env.example .env
```

---

### 步骤 2：编辑配置文件

#### 方法一：使用 nano 编辑器（简单）

```bash
# 打开配置文件
nano .env
```

修改以下内容：

```env
# Redis 密码（改成你自己的强密码）
REDIS_PASSWORD=MySecurePassword123!

# Flask 配置
FLASK_ENV=production
FLASK_DEBUG=0

# Redis 配置（不需要修改）
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
```

保存退出：
```
1. 按 Ctrl + O（字母O）
2. 按 Enter 确认
3. 按 Ctrl + X 退出
```

#### 方法二：使用 MobaXterm 内置编辑器

1. 在 MobaXterm 右侧文件浏览器中找到 `.env` 文件
2. 双击打开
3. 修改密码
4. 保存（Ctrl + S）

---

## 启动服务

### 步骤 1：首次启动

在 MobaXterm 中执行：

```bash
# 确保在项目目录
cd ~/xionghan-chess

# 启动所有服务（后台运行）
docker-compose up -d
```

首次启动会下载镜像，可能需要 5-10 分钟。

你会看到类似输出：
```
[+] Running 3/3
 ✔ Container xionghan-redis   Started
 ✔ Container xionghan-web     Started
 ✔ Container xionghan-nginx   Started
```

---

### 步骤 2：查看服务状态

```bash
# 查看所有容器状态
docker-compose ps

# 应该看到三个容器都是 "Up" 状态
```

示例输出：
```
NAME               STATUS         PORTS
xionghan-redis     Up 2 minutes   0.0.0.0:6379->6379/tcp
xionghan-web       Up 2 minutes   0.0.0.0:5000->5000/tcp
xionghan-nginx     Up 2 minutes   0.0.0.0:80->80/tcp
```

---

### 步骤 3：查看日志

```bash
# 实时查看所有日志
docker-compose logs -f

# 只看 Web 服务日志
docker-compose logs -f web

# 只看 Redis 日志
docker-compose logs -f redis

# 按 Ctrl + C 退出日志查看
```

---

## 访问测试

### 步骤 1：在 Windows 浏览器中访问

打开 Windows 上的浏览器（Chrome、Edge 等），访问：

```
http://192.168.1.100
```

**注意**：将 `192.168.1.100` 替换为你的 Linux IP 地址

你应该能看到雄汉象棋的首页！

---

### 步骤 2：测试游戏功能

1. **创建房间**
   - 点击"在线对战"
   - 点击"创建房间"
   - 记录房间号

2. **加入房间**
   - 打开另一个浏览器窗口（或无痕模式）
   - 访问相同地址
   - 点击"加入房间"
   - 输入房间号

3. **测试走棋**
   - 在第一个窗口走一步棋
   - 第二个窗口应该同步显示

---

### 步骤 3：检查防火墙（如果无法访问）

如果在 Windows 上无法访问，可能是 Linux 防火墙阻止了连接。

在 MobaXterm 中执行：

```bash
# 查看防火墙状态
sudo ufw status

# 如果防火墙是 active，需要开放端口
sudo ufw allow 80/tcp
sudo ufw allow 5000/tcp
sudo ufw reload

# 或者临时关闭防火墙测试（不推荐生产环境）
sudo ufw disable
```

再次尝试访问。

---

## 常用管理命令

### 查看服务状态

```bash
# 查看所有容器
docker-compose ps

# 查看资源使用
docker stats

# 查看磁盘使用
docker system df
```

---

### 停止服务

```bash
# 停止所有服务
docker-compose down

# 停止并删除数据卷（会丢失数据）
docker-compose down -v
```

---

### 重启服务

```bash
# 重启所有服务
docker-compose restart

# 只重启 Web 服务
docker-compose restart web
```

---

### 更新代码

当你修改了 Windows 上的代码后：

```bash
# 方法 1：重新上传文件后重建
docker-compose up -d --build

# 方法 2：如果使用 Git
cd ~/xionghan-chess
git pull
docker-compose up -d --build
```

---

### 查看日志

```bash
# 实时日志
docker-compose logs -f

# 最近 100 行日志
docker-compose logs --tail=100

# 导出日志到文件
docker-compose logs > logs.txt
```

---

### 进入容器调试

```bash
# 进入 Web 容器
docker exec -it xionghan-web bash

# 在容器内可以执行命令
ls -la
python --version

# 退出容器
exit
```

---

## 常见问题

### 问题 1：Docker 命令找不到

**症状：**
```
command not found: docker-compose
```

**解决：**
```bash
# 检查是否安装
which docker
which docker-compose

# 如果没安装，重新安装
# 参考前面的"安装 Docker"步骤
```

---

### 问题 2：权限不足

**症状：**
```
Got permission denied while trying to connect to the Docker daemon socket
```

**解决：**
```bash
# 将用户添加到 docker 组
sudo usermod -aG docker $USER

# 重新登录或执行
newgrp docker

# 测试
docker ps
```

---

### 问题 3：端口被占用

**症状：**
```
Error starting userland proxy: listen tcp 0.0.0.0:80: bind: address already in use
```

**解决：**
```bash
# 查看哪个进程占用了端口
sudo lsof -i :80
sudo netstat -tlnp | grep 80

# 停止占用端口的服务
sudo systemctl stop apache2  # 如果是 Apache
sudo systemctl stop nginx    # 如果是其他 Nginx

# 或者修改 docker-compose.yml 中的端口映射
# 将 80:80 改为 8080:80
```

---

### 问题 4：容器启动失败

**症状：**
```
Container xionghan-web exited with code 1
```

**解决：**
```bash
# 查看详细日志
docker-compose logs web

# 常见原因：
# 1. Redis 连接失败 - 检查 REDIS_HOST 配置
# 2. 端口冲突 - 检查端口占用
# 3. 依赖缺失 - 重新构建
docker-compose up -d --build
```

---

### 问题 5：无法从 Windows 访问

**症状：**
浏览器显示 "无法访问此网站"

**解决：**

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
   docker-compose ps
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

### 问题 6：Redis 连接失败

**症状：**
```
⚠️ Redis 连接失败: Error 111 connecting to redis:6379
```

**解决：**
```bash
# 检查 Redis 容器状态
docker-compose ps redis

# 查看 Redis 日志
docker-compose logs redis

# 测试 Redis 连接
docker exec xionghan-redis redis-cli ping

# 重启 Redis
docker-compose restart redis
```

---

### 问题 7：WebSocket 连接失败

**症状：**
浏览器控制台显示 "WebSocket connection failed"

**解决：**
```bash
# 检查 Nginx 配置
docker-compose logs nginx

# 重启 Nginx
docker-compose restart nginx

# 验证 WebSocket 支持
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" http://localhost/socket.io/
```

---

### 问题 8：磁盘空间不足

**症状：**
```
no space left on device
```

**解决：**
```bash
# 查看磁盘使用
df -h

# 清理 Docker 未使用的资源
docker system prune -a --volumes

# 查看 Docker 占用
docker system df
```

---

## 开机自启动

### 设置 Docker 开机自启

```bash
# 启用 Docker 服务开机自启
sudo systemctl enable docker

# 启用容器开机自启（docker-compose 已配置 restart: unless-stopped）
# 无需额外配置
```

### 设置项目开机自启

创建一个 systemd 服务文件：

```bash
sudo nano /etc/systemd/system/xionghan-chess.service
```

添加以下内容：

```ini
[Unit]
Description=Xionghan Chess Docker Compose Service
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/username/xionghan-chess
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
User=username

[Install]
WantedBy=multi-user.target
```

**注意**：将 `username` 替换为你的实际用户名

启用服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable xionghan-chess
sudo systemctl start xionghan-chess
```

---

## 备份与恢复

### 备份 Redis 数据

```bash
# 触发 Redis 保存
docker exec xionghan-redis redis-cli -a MySecurePassword123! BGSAVE

# 复制数据文件
docker cp xionghan-redis:/data/dump.rdb ./backup-$(date +%Y%m%d).rdb
```

### 恢复数据

```bash
# 停止服务
docker-compose down

# 恢复数据文件
docker cp ./backup-20240521.rdb xionghan-redis:/data/dump.rdb

# 启动服务
docker-compose up -d
```

---

## 性能优化

### 限制容器资源

编辑 `docker-compose.yml`，添加资源限制：

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

应用更改：

```bash
docker-compose up -d
```

---

## 安全加固

### 1. 修改默认密码

编辑 `.env` 文件，设置强密码：

```env
REDIS_PASSWORD=VeryStrongPassword!@#$%^&*()
```

重启服务：

```bash
docker-compose down
docker-compose up -d
```

---

### 2. 配置防火墙

```bash
# 启用防火墙
sudo ufw enable

# 只开放必要端口
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS（如果启用）

# 拒绝其他所有连接
sudo ufw default deny incoming

# 查看规则
sudo ufw status verbose
```

---

### 3. 定期更新

```bash
# 每月执行一次
sudo apt update && sudo apt upgrade -y

# 更新 Docker 镜像
docker-compose pull
docker-compose up -d
```

---

## 监控与维护

### 查看系统资源

```bash
# CPU 和内存使用
htop

# 磁盘使用
df -h

# Docker 资源使用
docker stats
```

---

### 日志轮转

防止日志文件过大：

```bash
# 创建 docker-compose.override.yml
nano docker-compose.override.yml
```

添加：

```yaml
version: '3.8'

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
  
  nginx:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

重启服务：

```bash
docker-compose up -d
```

---

## 下一步学习

恭喜你完成了部署！接下来可以学习：

1. **HTTPS 配置** - 使用 Let's Encrypt 免费证书
2. **域名绑定** - 购买域名并解析到你的服务器
3. **监控告警** - 集成 Prometheus + Grafana
4. **自动化部署** - 配置 CI/CD 流水线
5. **负载均衡** - 多服务器部署

---

## 快速参考卡片

```bash
# 启动服务
cd ~/xionghan-chess && docker-compose up -d

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 更新代码
git pull && docker-compose up -d --build

# 重启服务
docker-compose restart

# 进入容器
docker exec -it xionghan-web bash

# 备份数据
docker exec xionghan-redis redis-cli -a $REDIS_PASSWORD BGSAVE
```

---

## 获取帮助

如果遇到问题：

1. **查看日志**：`docker-compose logs -f`
2. **查阅文档**：[DOCKER_DEPLOY.md](DOCKER_DEPLOY.md)
3. **搜索错误信息**：将错误信息复制到搜索引擎
4. **检查社区**：GitHub Issues、Stack Overflow

---

**祝你部署顺利！** 🎉

如有问题，欢迎随时提问。
