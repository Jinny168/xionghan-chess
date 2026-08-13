# 匈汉象棋 v1.4.0 交付说明

## 依赖安装

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm install
```

Android 需要 .NET 9 SDK、Android workload 和 Android SDK；Docker 需要 Docker Desktop 或 Docker Engine。

## 启动

```powershell
.\.venv\Scripts\python.exe -m xionghan_chess.service.app
.\.venv\Scripts\python.exe -m xionghan_chess.desktop.app
docker compose -f deploy/docker-compose.yml up -d --build
```

Web 默认地址：`http://127.0.0.1:8000`。

## 打包

```powershell
powershell -ExecutionPolicy Bypass -File packaging/build_windows.ps1
powershell -ExecutionPolicy Bypass -File packaging/build_web_release.ps1
powershell -ExecutionPolicy Bypass -File packaging/build_android.ps1
```

## 交付内容

`release/v1.4.0-delivery` 包含桌面 EXE、Web 静态包与 ZIP、Android APK、FastAPI/Docker 部署文件、完整源码、依赖清单、构建脚本、QA 报告和操作文档。

## 上线前置校验

确认 `pytest -q` 为 81 passed；JS/JSON/compileall 检查通过；`/api/health` 返回 `status=ok` 且版本 1.4.0；Android 欢迎页可进入棋局页、返回键路由正确且同一棋子只播放一次选择音效；生产环境配置 HTTPS、持久化数据、环境变量和 APK 签名 keystore。
