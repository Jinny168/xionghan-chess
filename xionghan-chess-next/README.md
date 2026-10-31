# 匈汉象棋 (Xionghan Chess)

在 13×13 扩展棋盘上展开、融合匈奴与东汉历史文化元素的中国象棋变体。Windows 桌面端、Web 端与 Android 端共享同一套 Python 规则、AI、联机协议和 `.xhgame` 棋谱格式；对局既可以在本机单机进行，也可以连接自建的 FastAPI 服务进行在线对战。

- **当前版本**：1.7.0
- 棋子行棋规则：[docs/PIECE_RULES.md](docs/PIECE_RULES.md)；对局与胜负规则：[docs/RULES.md](docs/RULES.md)
- 玩家操作与常见问题：[HELP.md](src/xionghan_chess/desktop/resources/docs/HELP.md)

> 本目录 `xionghan-chess-next/` 是当前唯一的正式实现。仓库根目录下的 `desktop/`、`web/`、`docker/` 属于旧的 2.0 代码线，已退出维护，不在本项目的构建与运行范围内。

## 一、快速开始

### 环境要求

- Python 3.11 或更高版本
- 运行 Windows 桌面端额外需要 PySide6（随 `.[desktop]` 一并安装）

### 服务端 + Web 端

```powershell
cd xionghan-chess-next
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m uvicorn xionghan_chess.service.app:app --host 0.0.0.0 --port 8000 --reload
```

浏览器打开 `http://127.0.0.1:8000` 即进入 Web 客户端；同一局域网的其他设备用服务器的局域网 IP 访问。人机对战的 AI 在同一 Python 服务内运行，Web 端不复制一套 JavaScript 规则引擎。

### Windows 桌面端

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[desktop]"
.\.venv\Scripts\python.exe -m xionghan_chess.desktop.app
```

桌面端工具栏可创建或加入房间，填入局域网内已启动的 Web 服务地址（例如 `http://192.168.1.20:8000`）即可联机。

### 运行测试

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe -m pytest
```

## 二、三端构建

打包脚本都在 `packaging/` 下，产物统一输出到 `release/`。

| 目标 | 命令 | 前置条件 |
|---|---|---|
| Windows 桌面端 | `powershell -ExecutionPolicy Bypass -File packaging/build_windows.ps1` | Windows + PyInstaller（脚本会自动安装 `.[desktop,build]`） |
| Web 发布包 | `powershell -ExecutionPolicy Bypass -File packaging/build_web_release.ps1` | 无（纯文件打包） |
| Android APK | `powershell -ExecutionPolicy Bypass -File packaging/build_android.ps1` | .NET 9 + Android workload |

- 桌面端为 PyInstaller 单文件可执行程序，不需要携带旁边的 `_internal` 目录；配置保存在 `%APPDATA%/XionghanChess/settings.json`。
- Web 发布包内含 `web/`、`locales/`、`src/xionghan_chess/{core,service}` 等运行所需文件，解压后在服务器上启动 uvicorn 即可对外提供服务。
- Android 为 .NET 9 原生客户端，签名 APK 由 `android/XionghanChessAndroid.csproj` 生成，详细步骤见 [docs/ANDROID.md](docs/ANDROID.md)。
- 每个脚本在输出带版本号文件的同时，会另生成一份不带版本号的别名文件，便于“最新版”分发。

## 三、目录结构

```text
xionghan-chess-next/
├── src/xionghan_chess/
│   ├── core/          # 三端共用：棋盘模型、规则引擎、AI、对局状态、棋谱与题解
│   ├── service/       # FastAPI + WebSocket 服务端：房间、权威同步、账号
│   ├── desktop/       # PySide6 原生桌面客户端
│   ├── training/      # 自博弈采样与训练流水线（可选，需 NumPy）
│   └── i18n.py        # 语言目录加载
├── web/               # 轻量 Web 客户端（服务端规则的投影）
├── android/           # .NET 9 Android 客户端（含离线同机用的 offline.js 规则镜像）
├── locales/           # en.json / zh-CN.json 文案目录
├── tests/             # 规则、AI、协议、跨引擎与回归测试
├── packaging/         # 三端打包脚本
├── deploy/            # Dockerfile 与 docker-compose
├── scripts/           # 运行、基准与训练辅助脚本
└── docs/              # 规则、部署、架构与版本文档
```

棋盘尺寸、棋子数量与名称、初始布局、各行为开关的默认值等差异，统一由 `core/profiles.py` 里的 `RuleProfile` 描述。四套内置模式（`desktop_complete` / `desktop_classic` / `web` / `traditional`）全部调用同一份 Python 核心规则。

## 四、规则要点

- **棋盘**：主模式为 13×13，同时保留传统 10×9 的「传统」模式。
- **棋子**：除传统七种（帥/將、俥/車、馬、相/象、仕/士、炮、兵/卒）外，扩展了**四种**特色棋子：尉、射、檑、巡（每方 25 枚、全场 50 枚、共 11 种棋子）。
  > 甲/胄、楯/碷、刺/伺 **已于 2026-10-31 移除**（软删：枚举与规则分支保留，默认不出场；图鉴里以灰态「未登场」列出）。
  - **尉**：**斜向任意距离**移动与吃子，路径必须无子；不能走直线（标准主教）。
  - **射**：沿斜线移动；默认（弱化）模式下只能沿交错的星点轨道走，强化模式可自由斜走最多三格。
  - **檑**：可横、竖、斜移动；吃子时只能吃相邻八方向内、且四正交方向无同色保护的孤立敌子。
  - **巡**：横竖同规则（不限行），走偶数格，只有隔两格时才能吃子。
- **可配置规则**：复活、升变、底线兵、快速行军、将军提示等行为开关集中在 `RuleOptions`，不同模式给出不同默认值。
- 完整逐子规则与判定边界见 [docs/PIECE_RULES.md](docs/PIECE_RULES.md)，胜负与终局判定见 [docs/RULES.md](docs/RULES.md)。

## 五、已知限制

- **离线同机 vs 在线需服务端**：
  - “双人同机 / 人机对战”在本机即可完成，不需要服务器。
  - “网络房间、聊天、暂停计时、观战同步”等在线功能依赖一个已启动的 FastAPI 服务；服务不可达时这些入口保持禁用。
- **Web 端不独立承载规则**：浏览器端是服务端规则的投影，合法走法、AI 与终局判定都发生在 Python 服务内，因此 Web 端必须连着服务端才能下棋。
- **Android 端内置离线规则镜像**：APK 内置一份 `offline.js` 规则，用于“双人同机”离线对局；该镜像需要与 Python 核心规则保持一致（由跨引擎对拍测试守护）。
- **master（大师）难度**：第五档 AI 已接入，但其“正式棋力”尚未完成 50 局非截断完整对弈验收，暂不作为强度承诺。
- **内置题解规模有限**：题解集尚小，仍在补充中。

## 六、相关文档

- 架构与技术选型：[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- WebSocket 协议：[docs/WEBSOCKET_PROTOCOL.md](docs/WEBSOCKET_PROTOCOL.md)
- Android 构建与连服：[docs/ANDROID.md](docs/ANDROID.md)
- Linux 服务器部署：[docs/LINUX_DEPLOY.md](docs/LINUX_DEPLOY.md)、Docker 部署：[docs/DOCKER_DEPLOY.md](docs/DOCKER_DEPLOY.md)
- 玩家帮助与 FAQ：[HELP.md](src/xionghan_chess/desktop/resources/docs/HELP.md)（**仓库内唯一一份**：桌面端运行期加载并随包分发，`docs/HELP.md` 旧副本已删除）
- 项目愿景：[ABOUT.md](src/xionghan_chess/desktop/resources/docs/ABOUT.md)（**仓库内唯一一份**：桌面端运行期加载并随包分发的权威副本，`docs/ABOUT.md` 旧副本已删除）
- 变更记录：[docs/CHANGELOG_1.6.0.md](docs/CHANGELOG_1.6.0.md)；当前版本计划：[docs/VERSION_PLAN_1.6.0.md](docs/VERSION_PLAN_1.6.0.md)
- 排障：[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

## 许可证

MIT 许可证，详见仓库根目录 [LICENSE](../LICENSE)。
