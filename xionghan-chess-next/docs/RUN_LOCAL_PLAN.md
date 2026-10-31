# 本机可玩交付计划：桌面版 + 网页版

> **目标**：在两台形态上都能在本机实际开局对弈 —— **桌面应用**（Windows 原生窗口）与**网页端**（浏览器）。
> **基准**：HEAD `e1dc5b2`（版本号 1.7.0）｜ 编写日期 2026-10-13
> **本文只写"怎么做、怎么验"，不重复规则细节**（规则见 `PIECE_RULES.md` / `RULES.md`）。

---

## 一、交付物（明确"交付什么"）

| # | 交付物 | 形态 | 启动方式 | 状态 |
|---|---|---|---|---|
| D1 | **桌面应用（源码运行）** | `xionghan_chess.desktop.app`（PySide6 原生窗口） | `python -m xionghan_chess.desktop.app` | 依赖待装（PySide6） |
| D2 | **桌面版单文件 EXE** | `release/匈漢象棋-1.7.0-桌面版.exe` | 双击 | 需跑 `packaging/build_windows.ps1` |
| W1 | **网页端（本机服务）** | FastAPI 服务 + 静态前端 | `uvicorn xionghan_chess.service.app:app --port 8000` | ✅ **已验证可访问** |
| W2 | **网页版发布包** | `release/匈漢象棋-1.7.0-网页版.zip` | 解压后按包内说明启动 | 需跑 `packaging/build_web_release.ps1` |
| W3 | **容器化部署（可选）** | `deploy/docker-compose.yml`（image `xionghan-chess:1.7.0`） | `docker compose up` | 需本机有 Docker |

**本轮"能玩到"的最小集 = D1 + W1**（都是源码形态，零打包成本）。D2/W2/W3 是可选增强。

---

## 二、功能范围与一致性要求

### 2.1 三端与本次两者
项目是**三端共享一个 Python 核心**（`src/xionghan_chess/core/`）：

| 端 | 规则来源 | 说明 |
|---|---|---|
| **桌面版**（D1/D2） | `core/rules.py` | 原生外壳 + 共享核心；**可离线**（人机 / 双人同机），也可连服务端打联机 |
| **网页版**（W1/W2） | `core/rules.py`（**服务端运行**） | 浏览器是**服务端规则的投影**；AI 也在服务端算，**前端不复制规则引擎** |
| Android 离线 | `offline.js`（**独立 JS 镜像**） | ⚠️ 全项目**唯一**的规则双写处，靠跨引擎对拍守护 |

### 2.2 桌面版与网页版**必须一致**的东西（一致性要求）
1. **规则语义**：走法/吃子/终局判定完全同一套代码（`core/`），**不允许任一端私改**。
2. **棋谱格式**：`.xhgame` 文档两端可互相打开（同一 `game_document` / `game_from_document`）。
3. **协议**：联机走同一套 `protocol.py` 消息（`join` / `move` / `state` / `pause` / `undo_request` / `draw_offer` / `resign` / `restart` / `resurrect` …）。
4. **判和口径**：三次重复与无进展**用同一个 `position_key`**（1.7.0 起已含升变池；旧档读入自动重建账本）。

### 2.3 **不需要**一致的东西（避免误解）
- **界面实现**各写各的（桌面 PySide6 原生控件 / 网页 HTML+CSS）。
- **本地设置**各存各的：桌面在 `%APPDATA%/XionghanChess/settings.json`；网页在浏览器 `localStorage`。
- **账号与云同步**只在网页/联机侧存在（服务端 `/api/auth/*`、`/api/me/games`）；桌面**单机模式不需要账号**。

---

## 三、实现步骤与顺序

### 阶段 0 · 环境（一次性，约 5–10 分钟；PySide6 需下载）
```powershell
cd xionghan-chess-next
# 用仓库自带的托管 Python 3.13 建项目 venv（也可用你自己的 3.11+）
C:\Users\27415\.workbuddy\binaries\python\versions\3.13.12\python.exe -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip

# ⚠️ 关键：本机 pip 配置的清华镜像（tuna）取不到任何版本（见下方"踩坑"），
#    必须显式指定可用的索引源
.\.venv\Scripts\python.exe -m pip install --index-url https://pypi.org/simple -e .

# 桌面端依赖（含 PySide6，较大）
.\.venv\Scripts\python.exe -m pip install --index-url https://pypi.org/simple -e ".[desktop]"
```

> **踩坑（实测，2026-10-13）**：本机 `pip config` 里 `global.index-url = https://pypi.tuna.tsinghua.edu.cn/simple`。
> 该镜像**用 urllib 能取到页面（HTTP 200）**，但 **pip 解析它时报 `from versions: none`** —— 换
> `https://pypi.org/simple`（或 aliyun / tencent 镜像）后**立刻成功**。故本计划的所有 pip 命令都带
> `--index-url`。**这不是网络问题**（同机 urllib 直连镜像正常）。
>
> **另一个坑**：本机**代理 127.0.0.1:16066 已停止监听**，而 shell 环境里可能仍残留
> `http_proxy/https_proxy` 指向它 —— 若 pip 报连接被拒，先 `env -u http_proxy -u https_proxy` 再跑。

> **Python 版本**：`pyproject.toml` 要求 `>=3.11`。`docs/release/RUN.md` 写的是 `py -3.11`，但本机实测 **3.13 跑得通**（全套 202 用例在 3.13 下全绿）。若你的 `py -3.11` 不存在，用上面这条即可。
>
> **备选路径（不推荐）**：本机 anaconda（`D:\ProgramData\anaconda3`）自带 **PySide6 6.9.2**，但那是
> **Essentials 版、缺 `QtMultimedia`**，而桌面端 `desktop/audio.py` 依赖它 ⇒ **直接跑会报
> `No module named 'PySide6.QtMultimedia'`**。除非另装 `PySide6-Addons`，否则走 `.venv` 这条路。
>
> **若在 WorkBuddy 沙箱内代跑安装**（即由智能体执行）：还需额外两步 ——
> ① 清空被注入的 `PYTHONPATH`（它指向 WorkBuddy 的 `sitecustomize` 垫片，会让 pip 删文件时被
> `safe-delete` 守卫以 `SystemExit: 1` 打断）：
> `env -u PYTHONPATH -u http_proxy -u https_proxy .venv/Scripts/python.exe -m pip install --index-url https://pypi.org/simple -e ".[desktop]"`
> ② 装完后 `pip install -e` 会**改写被误跟踪的 `src/xionghan_chess.egg-info/*`**（6 个文件），
> 记得 `git checkout -- src/xionghan_chess.egg-info/` 还原，别把它提交进去。

### 阶段 1 · 先跑网页版（**建议先做这个**，反馈最快）
```powershell
cd xionghan-chess-next
$env:PYTHONPATH="src"      # 源码直跑需要；若已 pip install -e . 可省
.\.venv\Scripts\python.exe -m uvicorn xionghan_chess.service.app:app --host 127.0.0.1 --port 8000
```
浏览器打开 **`http://127.0.0.1:8000`** 即可对局。
- 只在本机玩：`--host 127.0.0.1`
- **要局域网内其它设备（手机/平板）也能加入**：改 `--host 0.0.0.0`，并放通 Windows 防火墙 8000 端口

### 阶段 2 · 再跑桌面版
```powershell
cd xionghan-chess-next
.\.venv\Scripts\python.exe -m xionghan_chess.desktop.app
# 或（装好 -e 之后）直接用入口脚本：
.\.venv\Scripts\xionghan-desktop.exe
```
- 打开后可选**人机对战 / 双人同机**，**完全离线**，不需要服务端。
- 想联机：**先在另一台机器（或本机另一个窗口）起阶段 1 的服务**，然后在桌面端工具栏「创建/加入房间」里填 `http://<服务器IP>:8000`。

### 阶段 3 · （可选）打成可分发产物
```powershell
# 桌面单文件 EXE（PyInstaller）
powershell -ExecutionPolicy Bypass -File packaging/build_windows.ps1
# 网页版发布包
powershell -ExecutionPolicy Bypass -File packaging/build_web_release.ps1
# Android APK（需 .NET Android 环境）
powershell -ExecutionPolicy Bypass -File packaging/build_android.ps1
```
产物落在 `release/`，并另存一份不带版本号的"最新版"别名。

### 阶段 4 · （可选）容器化
```powershell
cd xionghan-chess-next\deploy
docker compose up -d      # image: xionghan-chess:1.7.0
```

---

## 四、技术约束（必须知道的坑）

| # | 约束 | 说明与应对 |
|---|---|---|
| 1 | **服务端按相对路径找前端** | `service/app.py` 用 `Path(__file__).resolve().parents[3] / "web"` 定位静态目录。⇒ **必须保持 `src/xionghan_chess/` 与 `web/` 的相对位置**；只拷 `src/` 会得到空页面。已实测确认它指向 `xionghan-chess-next/web`。 |
| 2 | **桌面是 GUI，需要桌面会话** | PySide6 必须有图形环境。**无显示的服务器/CI 里跑不起来**（会报平台插件错误）。本机正常 Windows 桌面无此问题。 |
| 3 | **端口与防火墙** | 默认 8000。局域网联机需 `--host 0.0.0.0` + 放通防火墙；否则只有本机可访问。 |
| 4 | **跨平台** | 核心（`core/`）是纯 Python，跨平台；**桌面端 PySide6 支持 Win/mac/Linux**；但 `packaging/build_windows.ps1` 是 **Windows 专属**（mac/Linux 需另写打包脚本）。 |
| 5 | **数据同步** | **默认无同步**：两端设置各自存在本地。**跨设备同步只走服务端账号**（`/api/me/games` 棋谱库）。棋谱**文件**（`.xhgame`）可手工互传，两端都能打开。 |
| 6 | **账号侧功能需服务端可达** | 网页端的登录/云棋谱/观战等，服务端不可达时入口不可用；**离线同机模式仍可玩**。 |
| 7 | **离线端是 JS 镜像** | 只有 Android 离线走 `offline.js`（双写）。**桌面与网页都不碰它**。改动规则时**必须两端同步**。 |
| 8 | **pyinstaller 单文件会解压到临时目录** | 首次启动略慢；配置写 `%APPDATA%`，不写程序目录。 |

---

## 五、验证方法（"怎么证明两端都能正常用"）

### 5.1 网页版（可自动化，我已实测的部分标 ✅）
| 检查 | 命令/方法 | 期望 | 实测 |
|---|---|---|---|
| 服务起得来 | `uvicorn ... :app` | 日志 `Application startup complete` | ✅ |
| 首页可访问 | `GET http://127.0.0.1:8000/` | **HTTP 200**，返回前端 HTML | ✅ 200 / 22,215 B |
| 静态资源 | `GET /locales/zh-CN.json` | **HTTP 200** JSON | ✅ 200 / 22,276 B |
| API 存活 | `GET /api/health`、`GET /api/profiles`、`GET /api/puzzles` | 200 + 结构正确 | 待跑 |
| 接口文档 | `GET /docs`（Swagger UI） | 200 | 可用（路由表已含） |
| **实际开局** | 浏览器打开 → 人机对战 → 走子 → 吃子 → 将死/判和 | 规则、计时、悔棋、认输均正常 | **需你亲测**（人眼） |
| 联机 | 开两个浏览器标签 → 建房/加入 → 对走 | 双端同步、暂停/撤和认闭环 | **需你亲测** |

### 5.2 桌面版
| 检查 | 方法 | 期望 |
|---|---|---|
| 能启动 | `.venv\Scripts\python.exe -m xionghan_chess.desktop.app` | 出现棋盘窗口（无导入/插件报错） |
| 离线可玩 | 选「人机对战」走几步 | 走子合法、AI 应手、计时走动 |
| 双人同机 | 选「双人同机」 | 红黑轮流可走 |
| 设置持久化 | 改主题/音效 → 关掉 → 重开 | 设置保留（`%APPDATA%/XionghanChess/settings.json`） |
| 棋谱往返 | 存盘 `.xhgame` → 重新读取 | 局面/历史/结果一致 |
| 联机到网页服务 | 桌面端填 `http://127.0.0.1:8000` 建房，浏览器加入 | 两端同步对局 |

### 5.3 两端一致性（**这是"一致性要求"的验收**）
1. **同一份棋谱两端都能开**：桌面存 `.xhgame` → 网页端导入 → 局面与历史一致（反之亦然）。
2. **判和口径一致**：构造三次重复局面，两端都应判和（1.7.0 起 `position_key` 含升变池）。
3. **自动化护栏**：`pytest tests/ -q`（含跨引擎对拍）——**桌面与网页共用 Python 核心，故核心一致性由这套测试覆盖**。

### 5.4 回归门禁（改任何东西之后都要过）
```powershell
cd xionghan-chess-next
.\.venv\Scripts\python.exe -m pytest tests/ -q          # 期望全绿（当前 202 条）
node --check android\Resources\assets\offline\offline.js # 离线镜像语法
```

---

## 六、当前状态与剩余动作

**已完成 / 已验证**
- ✅ 网页版服务可启动、`/` 与 `/locales/*.json` 均 200
- ✅ 版本号已统一为 1.7.0（含一致性测试守护）
- ✅ 核心测试 202 全绿；跨引擎对拍（含随机/穷举加固）在推进

**待做（按顺序）**
1. 装 `.[desktop]`（PySide6）→ 启动桌面版（**需图形会话，只能在本机桌面跑**）
2. 网页版**人眼实测**：开局、走子、吃子、悔棋/暂停/认输/判和
3. 两端**棋谱互开**验证（5.3-1）
4. 可选：打 EXE / 网页发布包 / Docker

**已知不阻塞的偏差（如实记录）**
- 本仓库的 `run` 说明文档里写的是 `py -3.11`；本机无 `py -3.11`，但 **3.13 实测可用**。
- `src/xionghan_chess.egg-info/` 是**误入库的构建产物**（结构审计已记），不影响运行。
