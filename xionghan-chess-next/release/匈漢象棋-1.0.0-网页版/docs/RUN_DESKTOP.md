# Python 桌面端

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

带版本的打包输出位于 `release/匈漢象棋-1.0.0-桌面版.exe`，同时生成 `release/匈漢象棋-桌面版.exe` 作为最新版别名。这是单文件可执行程序，不需要携带旁边的 `_internal` 目录；配置保存在
`%APPDATA%/XionghanChess/settings.json`。
