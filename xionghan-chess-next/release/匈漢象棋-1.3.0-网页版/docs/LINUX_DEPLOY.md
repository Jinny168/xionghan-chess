# Linux 服务器部署

生产环境推荐使用 Docker Compose，并通过 Nginx 提供 HTTPS。当前房间和 WebSocket 会话保存在单个进程的内存中，因此服务端必须保持单实例运行；不要设置多个 Uvicorn worker，也不要直接横向扩容。若需多实例，需要先接入共享房间存储和跨进程消息广播。

## Docker Compose（推荐）

以下命令适用于 Ubuntu 22.04/24.04 或 Debian 12。先安装 Docker：

```bash
sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo \"$VERSION_CODENAME\") stable" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Debian 用户将上面仓库地址中的 `ubuntu` 改为 `debian`。上传并解压 `匈漢象棋-1.1.0-网页版.zip` 后执行：

```bash
cd 匈漢象棋-1.1.0-网页版
cp deploy/.env.example deploy/.env
nano deploy/.env
sudo docker compose --env-file deploy/.env -f deploy/docker-compose.yml build
sudo docker compose --env-file deploy/.env -f deploy/docker-compose.yml up -d
sudo docker compose --env-file deploy/.env -f deploy/docker-compose.yml ps
curl http://127.0.0.1:8000/api/health
```

如需直接开放 8000 端口：

```bash
sudo ufw allow 8000/tcp
```

查看日志、停止和更新：

```bash
sudo docker compose --env-file deploy/.env -f deploy/docker-compose.yml logs -f
sudo docker compose --env-file deploy/.env -f deploy/docker-compose.yml down

# 更新时替换程序文件，然后执行：
sudo docker compose --env-file deploy/.env -f deploy/docker-compose.yml build --pull
sudo docker compose --env-file deploy/.env -f deploy/docker-compose.yml up -d
```

## systemd 与 Python 虚拟环境

不使用 Docker 时，可由 systemd 管理单进程 Uvicorn：

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
sudo useradd --system --create-home --home-dir /opt/xionghan-chess --shell /usr/sbin/nologin xionghan
sudo mkdir -p /opt/xionghan-chess/app
sudo chown -R xionghan:xionghan /opt/xionghan-chess
```

将 Web 发布包解压至 `/opt/xionghan-chess/app`，然后安装：

```bash
sudo -u xionghan python3 -m venv /opt/xionghan-chess/venv
sudo -u xionghan /opt/xionghan-chess/venv/bin/pip install --upgrade pip
sudo -u xionghan /opt/xionghan-chess/venv/bin/pip install /opt/xionghan-chess/app
```

创建 `/etc/systemd/system/xionghan-chess.service`：

```ini
[Unit]
Description=Xionghan Chess Server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=xionghan
Group=xionghan
WorkingDirectory=/opt/xionghan-chess/app
Environment=PYTHONUNBUFFERED=1
Environment=AI_DEFAULT_DIFFICULTY=normal
Environment=AI_TIME_SCALE=1.0
Environment=MAX_ONLINE_GAMES=100
ExecStart=/opt/xionghan-chess/venv/bin/python -m uvicorn xionghan_chess.service.app:app --host 127.0.0.1 --port 8000 --workers 1
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
```

启动并检查：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now xionghan-chess
sudo systemctl status xionghan-chess
sudo journalctl -u xionghan-chess -f
curl http://127.0.0.1:8000/api/health
```

## Nginx、HTTPS 与 WebSocket

安装 Nginx，并创建 `/etc/nginx/sites-available/xionghan-chess`：

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name chess.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 3600s;
    }
}
```

启用配置：

```bash
sudo ln -s /etc/nginx/sites-available/xionghan-chess /etc/nginx/sites-enabled/xionghan-chess
sudo nginx -t
sudo systemctl reload nginx
sudo ufw allow 'Nginx Full'
```

域名解析到服务器后，用 Certbot 启用 HTTPS：

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d chess.example.com
curl https://chess.example.com/api/health
```

Android 公网连接建议只使用 HTTPS。在应用的“服务器设置”中填写 `https://chess.example.com/`；健康检查成功后，应用会自动从离线同机页面切换到完整在线页面，人机与联网模式随即恢复。

## 备份与故障检查

当前对局只存在于内存中，服务重启会清除未导出的房间。需要长期保留的棋局应由客户端导出 `.xhgame` 文件并另行备份。常用检查命令：

```bash
curl -i http://127.0.0.1:8000/api/health
sudo ss -lntp | grep 8000
sudo journalctl -u xionghan-chess -n 200 --no-pager
sudo nginx -t
```

若网页可打开但房间连接失败，重点检查反向代理是否保留 `Upgrade` 和 `Connection` 请求头，以及防火墙是否允许 80/443 端口。
