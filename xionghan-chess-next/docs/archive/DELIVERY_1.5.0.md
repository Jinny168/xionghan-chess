# 匈汉象棋 v1.5.0 交付说明

## 产物

- Windows：`release/匈漢象棋-1.5.0-桌面版.exe`
- Web：`release/匈漢象棋-1.5.0-网页版.zip`
- Android：`release/匈漢象棋-1.5.0-安卓版.apk`
- 完整交付目录：`release/v1.5.0-delivery`

## 启动

- 服务端：`powershell -ExecutionPolicy Bypass -File scripts/run_server.ps1`
- 桌面端：`powershell -ExecutionPolicy Bypass -File scripts/run_desktop.ps1`
- Docker：`docker compose -f deploy/docker-compose.yml up -d --build`

## 上线校验

- `/api/health` 返回版本 `1.5.0`。
- 九张头像在 Web、桌面安装包和 Android APK 中均存在。
- Web CSS/JS 缓存参数、Python 包、API、Docker、Android 和三端产物版本均为 1.5.0。
- Android 离线长局达到 120 ply 无进展阈值时判定 `no_progress`，与 Python Core 一致。
- 全量 pytest、JavaScript 语法、Python compileall 和 SHA256 校验通过。
