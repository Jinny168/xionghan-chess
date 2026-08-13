# 匈汉象棋 1.2.0

这是一个完全独立的新实现。原项目的 `desktop/`、`web/`、`docker/` 等目录不会被导入或覆盖。

Android 安装与构建说明见 [docs/ANDROID.md](docs/ANDROID.md)，Linux 服务器部署见 [docs/LINUX_DEPLOY.md](docs/LINUX_DEPLOY.md)。完整棋子规则见 [docs/PIECE_RULES.md](docs/PIECE_RULES.md)。
本次跨三端扩展的目录、功能、API 和验收结果见 [docs/DELIVERY_1.2.0.md](docs/DELIVERY_1.2.0.md)。
原版 Desktop 功能审阅、关键代码索引和迁移状态见 [docs/DESKTOP_LEGACY_REFERENCE.md](docs/DESKTOP_LEGACY_REFERENCE.md)。
玩家操作、棋谱和常见问题见 [docs/HELP.md](docs/HELP.md)，项目愿景与开发信息见 [docs/ABOUT.md](docs/ABOUT.md)。

```text
xionghan-chess-next/
├── src/xionghan_chess/core/       # 三端共用模型、规则、AI、协议与对局状态
├── src/xionghan_chess/service/    # FastAPI、WebSocket、房间和权威同步
├── src/xionghan_chess/desktop/    # PySide6 原生桌面客户端
├── web/                           # 轻量 Web 客户端
├── tests/                         # 规则、AI 与协议测试
├── packaging/                     # PyInstaller Windows 打包
├── deploy/                        # Docker 与 Compose
└── docs/                          # 完整运行和设计文档
```

模式差异全部由 `RuleProfile` 描述。四套模式可以拥有不同棋子数量、名称、布局和默认开关，
但统一调用 Python 核心规则。

```powershell
cd xionghan-chess-next
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m uvicorn xionghan_chess.service.app:app --reload
```

浏览器访问 `http://127.0.0.1:8000`。
