# 匈汉象棋 v1.7.0 桌面版架构与工程审计报告

> **审计对象**：`xionghan-chess-next` 桌面端（`src/xionghan_chess/desktop/` + `packaging/` 构建链）
> **基准 HEAD**：`b124c3d`（v1.7.0；作业期间 HEAD 未变）
> **本机环境（实测）**：Windows 11（10.0.26300）；`.venv` = **PySide6 6.12.0 / Python 3.13.14**；构建时另装 **PyInstaller 6.22.3 + Pillow 13.0.0**（见 §一·C）
> **审计人**：柯桥良（技术架构总监）
> **取证方式**：`Read`/`Grep`/`find`/`du`/`wc`/`git` 命令级取证；**启动性能用 offscreen 探针（`QT_QPA_PLATFORM=offscreen`）连跑两次**；**打包链路用真实 PyInstaller 构建实测**（非推断）
> **只读声明**：审计阶段**未改任何源文件、未 commit**；构建产物落在已忽略目录（`release/`、`build-onefile/`）。新增 PyInstaller/Pillow 仅装入 `.venv`（构建观察所需，不改源码）。

---

## 一、架构与工程审计

### A. `app.py` 1197 行实测拆分（**结论：该拆，且是"按类搬移 + 抽无 Qt 模块"，不是重写**）
按类/函数边界实测归类（行号区间 → 职责 → 规模）：

| 区段 | 行数 | 占比 | 职责细分 |
|---|---|---|---|
| `MainWindow` | **442** | 37% | 上帝类：UI 装配 63 + 对局控制 199（对局流程 89 / 设置外观 36 / 菜单功能 74）+ **联网与账号 151** + 刷新/时钟/关闭 28 |
| `BoardWidget` | **362** | 30% | 棋盘渲染（`paintEvent` + `_draw_*` 11 个绘制子程 ≈227）、动画 ≈21、命中测试/鼠标 ≈40、其余装配/状态 |
| 6 个对话框 | **285** | 24% | `SettingsDialog` 120 / `ReplayDialog` 59 / `HandicapDialog` 37 / `GameLibraryDialog` 35 / `TrainingDialog` 27 / `DocumentDialog` 7 |
| 模块头 + `WorkerSignals` + `AIWorker` + `load_bundled_fonts` | **92** | 8% | AI 线程、字体注册 |
| `run()` | 7 | 1% | 入口 |

**交叉验证**：lead-programmer 的实现层审计（#59）独立测得 `MainWindow` 441 / `BoardWidget` 363 / 6 Dialog 291 / 其他 99，与本表**逐项吻合**（其"对局控制 199" = 本表 89+36+74），互为他证。

**明确结论**：
- **该拆**。但不是"重构"，主体是**按类搬移**——`BoardWidget`、6 个 `QDialog`、`AIWorker` 已是独立类，可整类搬入子模块。
- **真正要动的是 `MainWindow` 的 151 行联网块**（`account_sync`/`request_json`/`server_base`/`create_online`/`join_online`/`spectate_online`/`http_json`/`open_network`/`_connect_network`/`_network_connected`/`_network_disconnected`/`network_message`/`apply_network_state`/`send_network`/`send_chat`/`close_network`）——它与棋盘/对局耦合最少、边界最清。
- **最大收益不在搬 Dialog，而在抽出 4 个无 Qt 依赖的纯模块**（见 §二 阶段 1 分层）。

### B. `core/` 与桌面端边界（**结论：健康，无绕过；一处第 4 份重复**）
- 桌面端**只消费 `core`**：`self.game.rules.in_check`（5 处）/`legal_moves`/`captured_by_move`/`archer_star_points`/`enabled_piece_types`、`self.game.move()`、`core.storage` 的 `game_document`/`game_from_document`。**未发现桌面端自行实现走法/判和/状态逻辑**（实测 grep）。✅ 这是本项目最该守住的线，目前守住。
- **一处重复**：`MainWindow::human_move` 内联复制了升变谓词 `{p.type for p in state.captured[…] if … not in {PAWN,KING} and … in enabled_piece_types}` —— 这是 `rules.promotion_types`/`promotable_types` 的**第 4 份拷贝**（前 3 份已由 `bfea053` 收敛，桌面是漏网的一份）。**P1**。
- 其余桌面模块职责清晰：`audio.py`(58) 音频、`config.py`(57) 配置、`storage.py`(105) 存档/统计（且正确委派 `core.storage`）。✅

### C. 打包链路（**结论：仓库自带脚本当前无法产出 EXE；本次由手动装依赖后构建成功**）

`packaging/build_windows.ps1` 全过程（实测）：
1. 定位 `.venv\Scripts\python.exe`（缺则 `py -3.11 -m venv` 建）；
2. **`pip install -e "$ProjectRoot[desktop,build]"` ← 🔴 P0-1 缺陷**；
3. PyInstaller `--onefile --windowed --icon …\icon.ico` + 三份 `--add-data`（`desktop/resources`、`core/data`、`locales`）+ `--paths src` + `--distpath release` + `--workpath/--specpath build-onefile`，入口 `packaging/desktop_entry.py`；
4. 产物复制为 `匈汉象棋-桌面版.exe`。

**🔴 P0-1｜`pip install` 行路径拼接缺陷（PowerShell 实测复现）**
`"$ProjectRoot[desktop,build]"` → `…\xionghan-chess-next[desktop,build]`（**无分隔符**）；正确应为 `Join-Path $ProjectRoot "[desktop,build]"` → `…\xionghan-chess-next\[desktop,build]`。同脚本其余路径**全部**用 `Join-Path`，仅此行例外 ⇒ 明确笔误。后果：该步必然失败，后续 PyInstaller 永不执行。

**🔴 P0-2｜依赖装不上（双重后果）**
`.venv` 原本**未装 PyInstaller**（实测 `No module named PyInstaller`）——而装它正是 P0-1 那步的职责。本机 pip 默认指向**清华镜像且不可达**；须显式 `--index-url https://pypi.org/simple`，且须 `env -u PYTHONPATH`（否则 WorkBuddy 注入的 `sitecustomize` 垫片会让 pip 删文件时被 safe-delete 守卫打断）。⇒ **"按 README/脚本一条命令构建"在本机不成立**。

**🔴 P0-4｜`icon.ico` 实为 PNG（4.86 MB），PyInstaller 拒收（实测）**
`src/xionghan_chess/desktop/resources/icon.ico` 大小 **4,859,293 B**，头 8 字节 `89 50 4e 47 0d 0a 1a 0a` = **PNG magic** ⇒ 它是**被改名成 `.ico` 的 PNG**。PyInstaller 报错：*"Received icon image … which exists but is not in the correct format. On this platform, only ('exe','ico') images may be used as icons. If Pillow is installed, automatic conversion will be attempted."* 且它与 `web/assets/icon.ico` **逐字节相同**（同一个 PNG 在两处误命名）。⇒ **即使修好 P0-1/P0-2，构建仍会在此失败，除非装 Pillow（`build` extra 成员）做自动转换。一个 4.86 MB 的 PNG 当图标也本身不合理（合规多尺寸 `.ico` 通常 100–300 KB）。**

**✅ 实测构建成功（在手动补齐依赖后）**
我按脚本第 3 步的等价命令（**绝对路径**，原因见下）实跑：
```
PyInstaller --noconfirm --clean --onefile --name "匈汉象棋-1.7.0-桌面版" --windowed \
  --icon <abs>/src/xionghan_chess/desktop/resources/icon.ico \
  --add-data <abs>/src/xionghan_chess/desktop/resources;xionghan_chess/desktop/resources \
  --add-data <abs>/src/xionghan_chess/core/data;xionghan_chess/core/data \
  --add-data <abs>/locales;locales \
  --paths <abs>/src --distpath release --workpath build-onefile --specpath build-onefile \
  packaging/desktop_entry.py
```
**实测结果**：
- **EXE 体积 = `163,006,226` B ≈ 163.0 MB（155.4 MiB）**（`release/匈汉象棋-1.7.0-桌面版.exe`）。
- **构建耗时 ≈ 73 s**。
- **EXE 可启动**：`QT_QPA_PLATFORM=offscreen` 下运行 20 s 超时**仍在运行**（未崩溃）；启动日志显示它把载荷解压到 `%TEMP%\_MEI000080c02\…` 并解析了 45 MB 的 `qq_background_sound.wav`。
- **三份 `--add-data` 全部在包内并正确解出（实测）**：在 EXE 归档中检索到 `zh-CN.json`/`en.json`/`puzzles.json`/`icon.ico`/`qq_background_sound.wav`/`PIECE_RULES.md`；运行中实测 `_MEI…/locales/{en,zh-CN}.json`、`_MEI…/xionghan_chess/core/data/puzzles.json`、`_MEI…/xionghan_chess/desktop/resources/sounds/*.wav` 均存在。

**📌 一个构建陷阱（实测踩到，脚本本身是对的）**：我第一次用**相对路径** `--add-data src/...` 失败——因为 `--specpath build-onefile` 会让 PyInstaller 把相对路径解析到 `build-onefile/` 下（报 `Unable to find …\build-onefile\src\…`）。**这正是 `build_windows.ps1` 用 `Join-Path $ProjectRoot` 绝对路径的原因**——脚本在这点上正确，不要"简化"成相对路径。

**单文件 EXE 优劣（PyInstaller 官方，见 §三）**：分发简单；但**启动更慢**（每次解压到 `_MEIxxxxxx`）、崩溃/被杀不留清理、Linux `/tmp noexec` 不兼容、官方明确建议"先确保 onedir 能跑再打 onefile"。本项目**只有 onefile、没有 onedir 回退路径**。

**两份 `.spec` 均不被消费（实测）**：全仓 grep（`packaging/*.ps1`、`scripts/`、`docs/`）**无任何脚本引用它们**；构建走 CLI（`--specpath build-onefile` 把生成的 spec 丢进已忽略目录）。且二者**不是重复，是两种构建模式**：根 `XionghanChess.spec` 是 PyInstaller **生成物**且**硬编码** `C:\Users\27415\PycharmProjects\...` 绝对路径（仅本机可解析）；`packaging/xionghan_chess.spec` 用相对路径且是 **onedir**（`EXE(..., exclude_binaries=True)` + `COLLECT(...)`），**但它缺 `core/data` 与 `locales` 两个 `--add-data`**（谁用它构建会缺题库与语言文件，且属静默降级）。**P1**。

### D. 资源管理（**结论：散列文件路径、无 qrc —— 今天不会漏，但靠两处手工同步**）
- 全部走 `Path(__file__).resolve().parent / "resources" / ...`：`load_bundled_fonts`(fonts)、`MainWindow::_build`/`run`(icon.ico)、`set_appearance`(backgrounds)、`show_rules`/`show_help`/`show_about`(docs/*.md)、`audio.py::DesktopAudio.__init__`(sounds)、`refresh`(avatars)。**无 `.qrc`、无 `QResource`、无 `:/`**。
- **打包后会不会漏？今天不会**——`pyproject` `[tool.setuptools.package-data]` 覆盖 `resources/{icon.ico,fonts,sounds,backgrounds,avatars,docs}`，构建脚本 `--add-data` 又显式加了三份 ⇒ **双保险**，本次实测三份数据全部正确解出也印证了这一点。**但这是两套手工同步**，新增资源目录时极易漏一边。**P1**。
- **附带（实测）**：`DesktopAudio.__init__` 无条件构造 7 个 `QSoundEffect` + `QMediaPlayer`，并在构造时解析那首 45 MB WAV（启动日志有 ffmpeg 解析输出）——**即使 `config.py` DEFAULTS 里 `"music": False`**。**P2**。

### E. 依赖与体积（**EXE 体积已由推断改为实测**）
| 项 | 实测 |
|---|---|
| **onefile EXE** | **163,006,226 B ≈ 163.0 MB（155.4 MiB）** |
| PySide6 安装态（EXE 主体来源） | 656 MB |
| `desktop/resources` | **126 MB** |
| ├ `sounds/` | **77 MB**（`qq_background_sound.wav` **45.0 MB** + `fc_background_sound.wav` **33.5 MB**；其余 8 个音效合计仅 0.9 MB） |
| ├ `fonts/` | **31 MB**（`msyh.ttc` + `simkai.ttf`） |
| ├ `backgrounds/` | **15 MB**（5×JPG ≈3 MB/张） |
| ├ `avatars/` | 152 KB |
| `core/data` / `locales` | 4 KB / 48 KB |

**判断**：实测 163 MB 比我此前推断的 170–190 MB **低约 10%**（PySide6 的 Qt 库压缩比预期好）。**压缩空间仍然极大**：两首 WAV 是**未压缩 48 kHz/16-bit/立体声 PCM**（前者时长 3:24、码率 1536 kbit/s，由运行时 ffmpeg 日志实测），且是**默认关闭**项（`"music": False`）却占包体 ~48%；转 OGG/MP3（64–128 kbps）每首约 3–6 MB，**可省 ~70 MB**。背景 JPG 可压至 ~0.3 MB/张（省 ~13 MB）。**`icon.ico` 那个 4.86 MB PNG 换成合规多尺寸 `.ico` 可再省 ~4.7 MB。**

### F. 跨平台现状（**结论：源码可移植、分发层 Windows-only；mac/Linux 未实测**）
- **源码层**：`desktop/*.py` 与 `packaging/*.ps1` 中 `sys.platform`/`darwin`/`win32`/`platform.system` **命中数为 0** ⇒ **无平台分支**，理论上可跑 mac/Linux（PySide6 官方支持 Linux/macOS/Windows）。
- **分发层缺口（实测/推断）**：
  1. `config.py::config_path` = `Path(os.getenv("APPDATA", Path.home())) / "XionghanChess"` ⇒ **Windows 约定**；mac 应为 `~/Library/Application Support`、Linux 应为 `~/.config`（`APPDATA` 缺失时回退 `~/XionghanChess`，不合任一平台惯例）。**P1**。
  2. 图标仅 `.ico`（且实为 PNG）；mac 需 `.icns`。**P1**。
  3. `msyh.ttc`/`simkai.ttf` 为**微软授权字体**，随包分发有许可风险（未查证授权文本），且非 Windows 用户通常不需要。**P1/P2**。
  4. 打包脚本**只有** `build_windows.ps1`（PowerShell）⇒ 无 mac/Linux 构建路径。
  5. **无代码签名/公证**（Win SmartScreen 警告、mac Gatekeeper 拦截）。**P1**。
  6. PyInstaller **不支持交叉编译**（官方），⇒ 每平台必须在对应 OS 上构建。

### G. 启动性能（**dev 模式与 onefile EXE 双实测**）
**dev 模式（offscreen 探针，连跑两次）**：
| 阶段 | 冷启 | 温启 |
|---|---|---|
| `import PySide6.QtWidgets` | 0.397s | — |
| `QApplication([])` | 0.041s | — |
| `import xionghan_chess.desktop.app` | 0.553s | — |
| `load_bundled_fonts()` | 0.006s | — |
| `MainWindow()` | 0.203s | — |
| **TOTAL 到可见窗口** | **1.201s** | **0.773s** |

**onefile EXE（实测，"启动→首次 stderr 输出"≈到 `MainWindow` 构造）**：**2726 ms**。
⇒ **onefile 惩罚 ≈ +1.5～2.0 s**（对齐 PyInstaller 官方"onefile 启动比 one-folder 慢，因每次解压载荷"的说明；本例还要多解压 126 MB 资源并解析 45 MB WAV）。

**判断**：dev 模式 0.8–1.2 s 对照业内"time-to-first-window >1–2 s 即被感知"属**良好**；但 **onefile 2.7 s 已进入"可感知"区间**，是瘦身（少解压 78.5 MB WAV）与改 onedir 的直接理由。**瓶颈在 import 与解压，不在业务逻辑。**

### H. 升级/自更新（**结论：完全没有**）
实测 `grep update|version` 于 `desktop/*.py` **只命中 Qt 的 `self.update()`（重绘）**；无版本检查、无更新渠道、无 changelog 展示（About 弹窗静态读 `resources/docs/ABOUT.md`）。**P1**（长期项）。

### I. 阻塞 UI 的病灶不在 AI（**独立复核实测，采信 #59 并由我复核**）
- `MainWindow::request_json` / `http_json`：`urllib.request.urlopen(request, timeout=15/8)` **在 UI 线程同步执行**（`account_sync`/`create_online`/`join_online`/`spectate_online` 等路径）。
- `ReplayDialog::show_analysis`：`analyze_game(game, Difficulty.BEGINNER, 40)` **同步跑完后** `DocumentDialog(...).exec()` 模态。
- 对照：AI 侧 `AIWorker(QRunnable)` + `QThreadPool.globalInstance()` + `WorkerSignals(QObject)` **不阻塞**（#59 实测 HARD 搜索 1.481 s vs `refresh()` 单 tick 1.28 ms = **1154×**）。
⇒ **"卡住"的真实来源是这两处同步 IO/分析，而非 AI。** 列为 **P1（行为修正，非纯搬移）**。

---

## 二、分阶段升级方案（含依赖顺序与工时量级）

**依赖顺序与理由**：先 **P0（让"能构建、能瘦身"成立）**——后续所有重构都需要一个**可复现的构建**来验证；再 **P1 结构**（拆包/资源/平台目录）——彼此独立但都依赖"构建可用"；最后 **长期（跨平台分发/自动更新）**——依赖前面全部就绪。**每一步都可独立回归（全量 pytest + 桌面冒烟）。**

### 阶段 0｜P0 止血（**先做，2–2.5 人日**）
| # | 做什么 | 为什么 | 影响面 | 风险 | 工时 |
|---|---|---|---|---|---|
| S0-1 | 修 `build_windows.ps1` 的 `pip install -e` 路径为 `Join-Path` | 构建链当前**断裂**（实测） | 仅打包脚本 | 极低 | 0.25d |
| S0-2 | **把 `icon.ico` 换成合规多尺寸 `.ico`**（现为 4.86 MB PNG，PyInstaller 拒收）；`web/assets/icon.ico` 同步 | 不换则必须依赖 Pillow 自动转换，且白背 4.7 MB | 资源 ×2 + 打包 | 低 | 0.25d |
| S0-3 | 在 `pyproject` 的 `build` extra 中**确保 Pillow 在列**（已在），并在脚本中**断言装得上**（显式 `--index-url`，或文档写明本机构换源） | 本机清华镜像不可达导致"按脚本装不上" | 打包脚本 + 文档 | 低 | 0.25d |
| S0-4 | 补 `packaging/xionghan_chess.spec` 缺失的 `core/data` + `locales` 两个 datas，并在 `build_windows.ps1` 头部**显式声明权威归属**（release=CLI onefile / QA 基线=spec onedir）+「全仓 `.spec` 计数=1」守卫 | 两份 spec 均无人引用；spec 版缺数据会静默降级 | 打包 | 低 | 0.5d |
| S0-5 | **两首背景音乐 WAV → OGG**（音效 wav 不动），`music` 默认仍关 | **省 ~70 MB**，并直接降低 onefile 启动解压量 | 资源 + `audio.py`（`QSoundEffect` 播 ogg 需改 `QMediaPlayer`） | 中（需回归听音） | 1.0d |
| S0-6 | 背景 JPG 重压缩（质量 ~75） | 省 ~13 MB | 资源 | 低 | 0.25d |

### 阶段 1｜P1 结构与资源（**依赖阶段 0 的可用构建**，6–8 人日）
| # | 做什么 | 为什么 | 影响面 | 风险 | 工时 |
|---|---|---|---|---|---|
| S1-1 | **修两处 UI 冻结**：`request_json`/`http_json` 改 `QNetworkAccessManager`（或 QRunnable+信号回主线程）；`show_analysis` 移出 UI 线程 + loading 态 | 用户可感知的卡死（15 s/8 s 无提示阻塞） | `app.py` + 新 `net/` | 中（行为变更） | 1.5d |
| S1-2 | **`MainWindow` 151 行联网块 → `desktop/net/`**（http + reconnect + session），与 S1-1 同批 | 边界最清、收益/风险比最高 | `app.py` + 新模块 | 低 | 1.0d |
| S1-3 | 抽 `desktop/theme.py`（外观/主题/资源定位，横切 `BoardWidget` 与 `SettingsDialog`） | 横切点；也是 qrc/路径唯一收口处 | `app.py` + 新模块 | 低 | 0.5d |
| S1-4 | 抽 `desktop/appcfg/`（`config.py` + `storage.py`），并把 `config_path` 改为**平台目录**（Win `APPDATA` / mac `~/Library/Application Support` / Linux `~/.config`） | 跨平台前置 | `config.py`+`storage.py`+既有配置迁移 | 低 | 0.5d |
| S1-5 | 抽 `desktop/game/`（`controller` + `refresh_policy` + `ai_service`，**无 Qt 依赖**）；`refresh_policy` 按官方 `QAbstractListModel` 范式改掉 `history.clear()+addItems()` 反模式 | 把对局控制逻辑变成可单测的纯模块 | `app.py` + 新模块 | 中 | 2.0d |
| S1-6 | 搬 `BoardWidget` → `desktop/ui/board.py`；6 个 `QDialog` → `desktop/ui/dialogs/`；`AIWorker` → `desktop/ui/ai_worker.py`；`load_bundled_fonts` → `desktop/ui/fonts.py` | `app.py` 1197 → ~290 行纯编排 | 多文件 | 中（纯搬移，需逐类回归） | 1.5d |
| S1-7 | **资源分层**：小件（`icon.ico`/`avatars`/`docs/*.md`）经 `pyside6-rcc` 进 `resources_rc.py`（`:/` 引用）；大件（sounds/backgrounds）保持文件路径 | 把"漏包=静默丢图标"变成"漏包=ImportError" | `app.py`/`audio.py` + 新 `resources_rc.py` | 中 | 1.0d |
| S1-8 | **加资源断言**（构建后/冒烟时断言 `locales/zh-CN.json`、`core/data/puzzles.json`、`:/` 资源存在） | 比 qrc 更通用的防漏包闸（当前 `--add-data`×3 与 `package-data` 是两套手工同步） | 打包/CI | 低 | 0.5d |
| S1-9 | `app.py` 类型标注补齐（AST 实测 **25%**，111 def / 28 有返回标注 → ≥85%） | 可维护性；缺口 100% 集中在 `app.py` | `app.py` | 低 | 1.0d |
| S1-10 | `MainWindow::human_move` 内联升变集改调 `rules.promotion_types` | 消除第 4 份拷贝 | 1 行 | 极低 | 0.25d |

### 阶段 2｜长期（**依赖阶段 1**，8–12 人日）
| # | 做什么 | 为什么 | 影响面 | 风险 | 工时 |
|---|---|---|---|---|---|
| S2-1 | Windows 安装器（Inno Setup / MSIX）+ 代码签名 | 无安装器=用户自己找 exe；无签名=SmartScreen 红牌 | 新增安装器工程 | 中（证书/法务；注意 Inno Setup 商业许可、WiX v6 >$10k 收费） | 3d |
| S2-2 | mac/Linux 构建（PyInstaller `--windowed` 出 `.app`+dmg；Linux AppImage/Flatpak）；`config_path` 已平台化是前置 | 源码无平台分支，缺的只是构建与约定 | 新增脚本 | 中（PyInstaller 不支持交叉编译，须各 OS 自建） | 3d |
| S2-3 | 版本检查 + "打开下载页"式更新（先不做静默自更新） | 现无任何更新机制 | `app.py` + 服务端 | 低 | 1.5d |
| S2-4 | 桌面冒烟入 CI（`QT_QPA_PLATFORM=offscreen` 构造 `MainWindow` + 资源断言 + `closeEvent` 不抛）；**建议单独 job + 仅 Windows runner**（PySide6 安装 ~656 MB 会显著拉长 CI） | 现 CI 只跑 pytest，桌面零自动化 | CI | 低 | 1.5d |
| S2-5 | `--exclude-module` 裁未用 Qt 模块 / 评估 Nuitka / 评估 onedir 分发 | 进一步瘦身与启动 | 打包 | 中 | 2d |

---

## 三、互联网检索佐证（来源 + 检索日期）

> **检索日期：2026-10-23**（WebSearch 工具返回值）。均标注可核对来源；未编造。本机跑不了的（mac/Linux 打包）已标"未能确证"。

**1. 大型 PySide6 应用组织方式**
- **Qt 官方**：PySide6 官方支持 Linux/macOS/Windows/Android/iOS/WebAssembly，Python 3.10+ —— https://www.pyside.org/
- **Qt 官方工具 `pyside6-project`**（https://doc.qt.io/qtforpython-6.10/tools/pyside-project.html）：官方工程化入口；`.qrc` → rcc 生成 `rc_.py`、`.ui` → `ui_.py`，并提供 `pyside6-deploy` 做部署。⇒ 支持 S1-7 的 qrc 化路线。
- **社区范式（pythonguis.com）**《Structuring a Large PyQt Application》：推荐 `myapp/{main.py, ui/{main_window.py, widgets/, resources/}, utils/}`，**"main.py 只做 QApplication + 显示主窗口，保持最小"**、UI 代码与资产归 `ui/`、非 GUI 辅助归 `utils/` —— 与本报告 §二 的职责分层同构。

**2. PyInstaller 单文件 vs 目录模式（官方）**
- **PyInstaller 官方手册**（https://pyinstaller.org/en/v5.5/operating-mode.html，现行文档同）：
  - onefile 优势=用户拿到一个可执行文件；**劣势="启动比 one-folder 稍慢"**（bootloader 每次把内嵌归档解压到 `_MEIxxxxxx` 临时目录）。
  - **官方明确建议："Before you attempt to bundle to one file, make sure your app works correctly when bundled to one folder. It is much easier to diagnose problems in one-folder mode."**
  - **known issues（官方列举）**：`_MEIxxxxxx` 在崩溃/被杀时不清理（长期跑会泄漏磁盘）；Linux `/tmp` 若挂 `noexec` 与 onefile **不兼容**（`--runtime-tmpdir` 可规避）；**不要给 onefile exe 管理员权限**；多开实例不共享任何东西（磁盘翻倍）。
- **PyInstaller 参考手册**（https://pydevtools.com/handbook/reference/pyinstaller）：**无内置代码签名**（Windows 需 signtool、macOS 需 codesign+notarize）；**杀软误报**是已知问题；**不支持交叉编译**；`--exclude-module` 可裁体积。⇒ 支撑 S2-1/S2-2 必须"每平台各自构建"。
- **本次实测与之对齐**：onefile EXE 启动 2726 ms vs dev 1201/773 ms；运行中确实解压到 `%TEMP%\_MEI000080c02\…`。

**3. 跨平台 Python 桌面分发**
- **thelinuxcode.com（2026）**《Building Desktop Applications in Python (2026)》：工具矩阵 —— 快速出可执行用 **PyInstaller**；要"原生感"用 **Briefcase**；要性能/混淆用 **Nuitka**。分发路径：**Windows MSI/MSIX（企业 Intune；公开 winget）**、**macOS 公证后的 .app 打进 .dmg（MDM/Homebrew cask/直下）**、**Linux Flatpak（桌面友好）/AppImage（便携）**。并强调两条常被晚发现的坑：**"Data files: icons/templates/embedded DB —— 尽早决定它们放哪、打包怎么带"**；**"Writable paths: never write into the install directory. Use per-user app data directories"**（⇒ 直接支撑 S1-4）。另：**"Time-to-first-window: people feel anything over ~1–2 seconds"**（⇒ 与实测 0.8–1.2s dev / 2.7s onefile 对照）。
- **devlune.in《Installers》术语表**（2026-09 核价）：Windows = NSIS/Inno Setup 生成 .exe setup、WiX 生成 MSI、MSIX 最新；macOS = .dmg 拖拽或 .pkg；Linux = deb/rpm + AppImage/Flatpak/Snap；渠道 winget/Homebrew cask/Flathub。**许可提示：Inno Setup 商业用途需购买许可；WiX v6 对年收入 >$10k 的公司收维护费**（⇒ S2-1 选型需注意）。
- **BeeWare Briefcase**（https://pydevtools.com/handbook/reference/briefcase）：单 `pyproject.toml` 的 `[tool.briefcase]` 产出 macOS `.app`/DMG、Windows MSI、Linux deb/rpm/AppImage/Flatpak；**仍是 pre-1.0**，桌面端面对 PyInstaller/Nuitka/cx_Freeze 等更成熟竞品（⇒ 建议 S2-2 继续用 PyInstaller）。
- **pyappdist**（https://github.com/atsuoishimoto/pyappdist/）：用 python-build-standalone 打完整运行时再做成 MSI/MSIX/DMG/AppImage/Flatpak；文中指出"**典型 Python 运行时额外增加约 100–150 MB**"，与 PyInstaller"挑最小文件换小体积"是相反取舍（⇒ 我们体积敏感，不宜选）。

**4. Qt 资源系统（.qrc）vs 散列文件路径**
- **Qt Wiki《QtResources》**（https://wiki.qt.io/QtResources）：qrc 是**平台无关**的"把任意二进制数据编进可执行体"机制；`:` 前缀路径由 Qt 资源系统查找（只读）；`rcc -compressed` 可用 zlib 压缩；静态库场景需 `Q_INIT_RESOURCE`。⇒ 说明 qrc 解决的是"路径不存在/平台差异"类问题，正是散列 `Path(__file__)` 的痛点。
- **pythonguis.com《Using Qt Resource Files (.qrc) with PyInstaller and PyQt》**：**关键结论——"编译出的 `resources_rc.py` 已把全部图片/图标以数据形式嵌在内，你**不需要**再把原始 `.qrc` 或原始图片文件放进 PyInstaller 包"**；PySide6 用 `pyside6-rcc` 编译（PyQt6 已移除 pyrcc6）。同时给出**常见打包事故**："忘了把 `resources_rc.py` 打进包 → 应用能启动但图标全缺，且往往没有明显报错"（⇒ 需配 `QFile.exists(":/…")` 断言）。
- **pythonguis.com《Using Icons from Qt Resources with PyInstaller》**：**PyInstaller 的 `--icon` 与 Qt 资源系统是两套世界**——`--icon` 需要磁盘上真实 `.ico`；**两者可并存、不冲突**（⇒ 现有 `--icon …\icon.ico` 与将来 qrc 化不矛盾）。**这也解释了本次 P0-4：`--icon` 要的是真 `.ico`，而仓库里那个是 PNG。**
- **pythonguis.com / pytutorials.net（打包排错）**：PyInstaller 后图片不显示的三大根因 = 硬编码相对路径未考虑 `_MEIxxxxxx`、资源未入包、`.qrc` 未编译；调试手段 `pyi-archive_viewer`、`QT_LOGGING_RULES=qt.resource.*=true`。

---

## 四、实测 / 推断 / 未能确证

**实测（命令级取证，可复现）**
- `app.py` 类/函数行号区间与占比（并与 #59 交叉验证一致）；
- `desktop` 层**无平台分支**（`sys.platform`/`darwin`/`win32` 命中 0）；
- `core` 边界**无绕过**（但 `app.py::human_move` 有第 4 份内联升变集）；
- **`build_windows.ps1` 的 PowerShell 字符串缺陷复现**（`"$ProjectRoot[desktop,build]"` → 无分隔符）；
- `.venv` 原本 **PySide6 6.12.0 / Python 3.13.14、无 PyInstaller**；本机 pip 清华镜像不可达（须 `--index-url https://pypi.org/simple` + `env -u PYTHONPATH`）；
- **`icon.ico` = 4,859,293 B、头 8 字节为 PNG magic（`89 50 4e 47 0d 0a 1a 0a`）**，与 `web/assets/icon.ico` 逐字节相同；
- **真实构建成功并实测**：EXE **163,006,226 B**；构建耗时 **≈73 s**；EXE 以 offscreen 运行 20 s 未崩溃；三份 `--add-data` 全部在归档内且运行中正确解出（`locales/{en,zh-CN}.json`、`core/data/puzzles.json`、`resources/sounds/*.wav`）；解压目标 `%TEMP%\_MEI…`；
- **启动耗时**：dev 冷 1201 ms / 温 773 ms（offscreen 探针连跑两次，含分阶段分解）；**onefile EXE 2726 ms**；
- **两处 UI 冻结已由我独立复核实测**（`urllib.request.urlopen(..., timeout=15/8)`；`analyze_game(game, Difficulty.BEGINNER, 40)` + 模态 `exec()`）；
- `du -sh` 各资源体积、两首 WAV 精确字节数、WAV 时长/码率（运行时 ffmpeg 日志）；
- 两份 `.spec` 全仓零引用；`config.py` 用 `APPDATA`；无更新机制（`grep update|version` 仅命中 Qt 重绘）；
- 相对 `--add-data` + `--specpath` 导致解析到 `build-onefile/` 的失败复现。

**推断（有依据，未验证）**
- ~~EXE ≈170–190 MB~~ **已由实测取代为 163,006,226 B**（原推断高约 10%，因 PySide6 压缩比预期好）；
- mac/Linux 可运行性（源码无平台分支，但**未在 mac/Linux 实测**）；
- 字体 `msyh.ttc`/`simkai.ttf` 的授权风险（**未查证授权文本**）；
- onedir 模式实际体积（未构建 onedir）。

**未能确证**
- **mac/Linux 实跑与打包**（无对应 OS 与构建链）；
- **`msyh.ttc`/`simkai.ttf` 授权条款**；
- onedir 实际体积；`--exclude-module` 可裁掉多少；
- EXE 在**真实显示器**（非 offscreen）下的首屏时间（沙箱无显示设备，offscreen 数值仅供相对比较）。

---

> **报告完**。本报告为只读审计 + 构建观察；**未修改任何源文件、未 commit**。实施按 §二 分阶段另开任务。
