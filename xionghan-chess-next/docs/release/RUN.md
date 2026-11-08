# 运行与部署

> 由 `RUN_DESKTOP.md` / `RUN_WEB.md` / `DOCKER_DEPLOY.md` 合并（2026-10-31），内容未改写。

## 桌面端

```powershell
cd xionghan-chess-next
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[desktop]"
.\.venv\Scripts\python.exe -m xionghan_chess.desktop.app
```

局域网联机前，在一台机器启动 Web 服务，然后在桌面端工具栏创建或加入房间，输入例如
`http://192.168.1.20:8000`。

```powershell
powershell -ExecutionPolicy Bypass -File packaging/build_windows.ps1
```

带版本的打包输出位于 `release/匈漢象棋-1.1.0-桌面版.exe`，同时生成 `release/匈漢象棋-桌面版.exe` 作为最新版别名。这是单文件可执行程序，不需要携带旁边的 `_internal` 目录；配置保存在
`%APPDATA%/XionghanChess/settings.json`。

## 网页端

```powershell
cd xionghan-chess-next
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m uvicorn xionghan_chess.service.app:app --host 0.0.0.0 --port 8000 --reload
```

访问 `http://127.0.0.1:8000`。同一局域网设备访问服务器局域网 IP。浏览器人机对战的 AI
运行于同一 Python 服务，不复制 JavaScript 规则引擎。

## Docker 部署

完整的 Linux、systemd、Nginx、HTTPS 和更新维护说明见 [LINUX_DEPLOY.md](LINUX_DEPLOY.md)。

```bash
cd xionghan-chess-next
cp deploy/.env.example deploy/.env
docker compose --env-file deploy/.env -f deploy/docker-compose.yml build
docker compose --env-file deploy/.env -f deploy/docker-compose.yml up -d
docker compose --env-file deploy/.env -f deploy/docker-compose.yml logs -f
```

默认访问 `http://服务器IP:8000`。停止：

```bash
docker compose --env-file deploy/.env -f deploy/docker-compose.yml down
```

公网部署需开放 TCP 端口，反向代理需允许 WebSocket Upgrade。当前为单实例内存房间方案；多副本
部署前需增加 Redis 房间存储和跨进程广播。

`AI_DEFAULT_DIFFICULTY` 设置默认难度，`AI_TIME_SCALE` 按比例调整各档思考时间，
`MAX_ONLINE_GAMES` 限制同时存在的房间数量。
