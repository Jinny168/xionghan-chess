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
# 不要用 `uvicorn` CLI 直接起：CLI 不经过 `run()`，拿不到 Windows 上的 Selector 事件循环修复
# （uvicorn 0.36+ 用 loop_factory，全局 policy 已无效），会重新出现
# `_ProactorBasePipeTransport._call_connection_lost` 噪声。
.\.venv\Scripts\python.exe -m xionghan_chess.service.app
```

访问 `http://127.0.0.1:8000`。同一局域网设备访问服务器局域网 IP。浏览器人机对战的 AI
运行于同一 Python 服务，不复制 JavaScript 规则引擎。

> 端口用环境变量 `PORT`（默认 `8000`），绑定 `0.0.0.0`。**不要用 `uvicorn` CLI 直接起** ——
> CLI 不经过 `run()`，拿不到 Windows 上的 Selector 事件循环修复（uvicorn 0.36+ 用 `loop_factory`，
> 全局 policy 无效），会重新出现 `_ProactorBasePipeTransport._call_connection_lost` 噪声。
> 若必须保留 CLI 形态（systemd / docker exec），写成
> `python -m uvicorn xionghan_chess.service.app:app --host 0.0.0.0 --port 8000 --loop xionghan_chess.service.app:_selector_loop_factory`
> —— `--loop` 只在 Windows 需要，Linux/macOS 默认即 Selector；已实测 Windows 上
> `Config(loop="auto")` → `ProactorEventLoop`、加 `--loop` → `_WindowsSelectorEventLoop`。

> **可复现 / 离线部署请用 `requirements/lock/py312-server.txt`**（19 个包的精确锁定）；
> `requirements/server.txt` 只是**范围约束**（如 `fastapi>=0.116,<1`），实际解析版本会随时间前移
> —— 2026-11-11 实测干净环境解析到 fastapi 0.162.4 / starlette 1.10.0，与本仓库开发环境不同。
> 离线机器先用 `pip download -r requirements/lock/py312-server.txt -d wheels/` 备好 wheel，
> 再 `pip install --no-index --find-links wheels/ -r requirements/lock/py312-server.txt`。
> 桌面端另需 `requirements/desktop.txt`（PySide6），服务端不需要。

## Docker 部署

完整的 Linux、systemd、Nginx、HTTPS 和更新维护说明见 [LINUX_DEPLOY.md](../LINUX_DEPLOY.md)。

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
