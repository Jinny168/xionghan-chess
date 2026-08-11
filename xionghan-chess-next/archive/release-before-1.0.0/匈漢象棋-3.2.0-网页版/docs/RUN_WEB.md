# Web 前后端

```powershell
cd xionghan-chess-next
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m uvicorn xionghan_chess.service.app:app --host 0.0.0.0 --port 8000 --reload
```

访问 `http://127.0.0.1:8000`。同一局域网设备访问服务器局域网 IP。浏览器人机对战的 AI
运行于同一 Python 服务，不复制 JavaScript 规则引擎。

