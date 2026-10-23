# 匈汉象棋 v1.6.0 交付说明

## 产物目录

- 完整交付目录：`release/v1.6.0-delivery`
- Windows：`release/匈漢象棋-1.6.0-桌面版.exe`
- Web：`release/匈漢象棋-1.6.0-网页版.zip`
- Android：`release/匈漢象棋-1.6.0-安卓版.apk`
- 校验：`release/v1.6.0-delivery/SHA256SUMS-1.6.0.txt`

## 启动命令

```powershell
cd "C:/Users/27415/PycharmProjects/xionghan-chess/xionghan-chess-next"
./.venv/Scripts/python.exe -m xionghan_chess.service.app
powershell -ExecutionPolicy Bypass -File scripts/run_desktop.ps1
```

Web 健康检查：`http://127.0.0.1:8000/api/health`

## 打包命令

```powershell
cd "C:/Users/27415/PycharmProjects/xionghan-chess/xionghan-chess-next"
powershell -ExecutionPolicy Bypass -File packaging/build_web_release.ps1
powershell -ExecutionPolicy Bypass -File packaging/build_android.ps1
powershell -ExecutionPolicy Bypass -File packaging/build_windows.ps1
```

## Docker

```powershell
cd "C:/Users/27415/PycharmProjects/xionghan-chess/xionghan-chess-next/deploy"
docker compose up -d --build
```

生产环境必须在 Docker/FastAPI 前配置 HTTPS 反向代理。Android v1.6.0 Release 已关闭明文 HTTP，测试环境如需 HTTP 需使用调试构建或显式安装本地证书/代理配置。

## 验收命令

```powershell
cd "C:/Users/27415/PycharmProjects/xionghan-chess/xionghan-chess-next"
./.venv/Scripts/python.exe -m pytest -q --durations=10
./.venv/Scripts/python.exe -m compileall -q src tests scripts
node --check web/js/app.js
node --check web/js/i18n.js
node --check android/Resources/assets/offline/offline.js
node --check android/Resources/assets/offline/offline-locales.js
```

## 已知风险

master 档已可用并接入 MCTS/可选训练模型推理，但 50 局非截断完整对弈胜率 >=55% 未完成有效验收。建议 v1.7.0 将模型训练质量、完整棋力评测和生产 policy/value 推理调优列为首要任务。
