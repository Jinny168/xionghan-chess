# 桌面版全面回顾 + 迭代升级计划

> **目标**：把工作重心放到桌面版，对当前工作做全面回顾、执行一次审计，并制定可排期的迭代升级计划。
> **基准**：HEAD `efec83c`（v1.7.0）｜ 编写日期 2026-10-23
> **本机环境**：`.venv` = PySide6 6.12.0 / Python 3.13.14 / PyInstaller 6.22.3 / Pillow 13.0.0
> **测试基线**：`pytest tests/ -q` → **240 passed**

## 参与成员与产出来源

| 成员 | 职责 | 产出 |
|---|---|---|
| 游有方（创意总监） | 桌面版体验审计 | 玩家旅程审计 + 7 处违背「傻瓜式」 + A/B/C 三个升级方向 + 13 个联网佐证 |
| 寇豆码（主程序） | 桌面版实现层 | `app.py` 实测构成 + AI 线程结论 + S0–S11 重构方案（13.5 人日）+ 联网佐证 |
| 柯桥良（技术架构） | 桌面版架构与工程 | 八轴审计 + **EXE 实构建测（163 MB）** + 分阶段方案 + `.spec`/`.qrc`/分层三项裁定 + 12 个联网佐证 |
| 严过关（质量监管） | 桌面版验证面 | 覆盖矩阵 + 「桌面端靠什么保证不坏」结论 + 测试策略 A1–A6 + **手工验收清单 D-01~D-17** |

明细报告：`docs/AUDIT_DESKTOP_1.7.0.md`（柯桥良落盘）；另三位的完整原文见本次会话记录。

---

# 一、全面回顾：桌面版现在是什么状态

## 1.1 做得好的（**全部实测，不是推测**）

| 项 | 实测数据 | 结论 |
|---|---|---|
| **启动性能** | dev 冷 **1.201s** / 温 **0.773s**；onefile EXE **2.726s** | 良好（业内阈值 1–2s）。瓶颈在 import（0.95s），**不在业务逻辑 —— 别重写架构提速，收益微小** |
| **AI 不阻塞 UI** | `AIWorker(QRunnable)` + `QThreadPool` + 跨线程信号 + `AutoConnection` ⇒ slot 在 GUI 线程执行（Qt 官方语义）。实测 HARD 搜索 **1.481s** vs `refresh()` 一个 tick **1.28ms** ⇒ **1154× 余量** | **这条已对，别动**。若改成 GUI 线程同步，250ms 轮询会让整个搜索窗口停摆 |
| **`core/` 边界干净** | 桌面端**只消费** `core`（`in_check`/`legal_moves`/`captured_by_move`/`archer_star_points`/`move()`/`storage`）；走法/判和/状态**无一处自行实现** | 本项目最该守住的线，**目前守住了** |
| **对局内核与手感** | 0 弹窗走棋、合法目标高亮、吃子提示、动画、AI 思考遮罩、暂停遮罩、声音均到位 | **不该乱加玩法**（与「本轮不加内容复杂度」的定调一致） |
| **源码可移植性** | `desktop/*.py` 与 `packaging/*.ps1` 中 `sys.platform`/`darwin`/`win32`/`platform.system` **命中数 = 0** | 无平台分支，源码层理论上可跑 mac/Linux |
| **共享核心的护栏** | `core/` 240 条测试 + 跨引擎对拍 84 条 | 改规则/AI/协议时三端有共同护栏 |

## 1.2 但「能不能交付」这一层是断的

**关键事实（柯桥良实构建测）**：仓库自带的 `build_windows.ps1` **目前造不出可用的 EXE**。163 MB 那个 EXE 是**手动补齐依赖后**才造出来的。

| 断裂点 | 证据 |
|---|---|
| **P0-1 路径拼接缺陷** | `build_windows.ps1:86` 的 `"$ProjectRoot[desktop,build]"` 被 PowerShell 当「通配符展开」吃掉 → 拼成 `…\xionghan-chess-next[desktop,build]`（无分隔符）→ `New-Item -Force` **静默成功** → **PyInstaller 那一行从未被真正执行过** |
| **P0-2 依赖从未装上** | `.venv` 实测 `No module named PyInstaller`；而「装上 PyInstaller」正是那个坏步骤的职责 ⇒ 双重断链。**手动 `pip install pyinstaller pillow` 后才跑通** |
| **P0-3 图标是被改名的 PNG** | `resources/icon.ico` 大小 **4,859,293 B**、头 8 字节 `89 50 4e 47…` = **PNG magic**。PyInstaller 报 *"exists but is not in the correct format… only ('exe','ico') images may be used"*。且与 `web/assets/icon.ico` **逐字节相同**（同一份误命名的 PNG 存了两处） |

---

# 二、审计结论（四份合并去重，按 P0/P1/P2）

> 每条标注来源成员；重复发现的合并为一条并注明「双源印证」。

## P0（必修 —— 不修则「能构建 / 可体验 / 有护栏」三件事都不成立）

| # | 问题 | 证据 | 来源 |
|---|---|---|---|
| **P0-A** | **构建链断裂**（P0-1 + P0-2） | 见 §1.2 | 柯桥良 |
| **P0-B** | **`icon.ico` 是被改名成 `.ico` 的 PNG（4.86 MB）** | 头 8 字节 PNG magic；与 `web/assets/icon.ico` 逐字节相同；PyInstaller 直接拒收 | 柯桥良 |
| **P0-C** | **两处 UI 真冻结**（AI 不冻结，这两处冻结） | ① `ReplayDialog::show_analysis` 在 GUI 线程同步跑 `analyze_game(..., 40)`；② `request_json`/`http_json` 同步 `urllib`（timeout **15s**/8s）—— 服务器不可达时窗口"未响应"最长 15 秒 | 寇豆码 + 柯桥良（双源） |
| **P0-D** | **桌面端零自动化护栏，且 CI 结构上覆盖不了** | `tests/` 对 `desktop.app\|MainWindow\|BoardWidget\|QApplication\|PySide6\|qtbot` **grep 0 命中**；`pyproject` 的 `test` extra 只有 `pytest`+`httpx`（**不含 PySide6**）⇒ 即便写了 GUI 测试 CI 也 import 不了 | 严过关 |
| **P0-E** | **EXE 零验证** | `release/` 此前**不存在**；无启动冒烟、无资源完整性检查；打包是否成功只在有人手动跑脚本的那一刻被知道 | 严过关 |
| **P0-F** | **认输无二次确认，且与 Web 端行为不一致** | `app.py:876-878` `resign_game` 直接 `game.resign(color)`；**同文件** `:879-882` `draw_game` **有** `QMessageBox.question` —— 同文件内行为不对称，可 falsify | 游有方发现 + 严过关复核 |
| **P0-G** | **包体 163 MB，其中约 62% 花在默认关闭的 BGM 上** | `desktop/resources` 126 MB；`sounds/` 77 MB = `qq_background_sound.wav` **45.0 MB** + `welcome_background_sound.wav` **33.5 MB**（未压缩 PCM）；而 `config.py` DEFAULTS `"music": False`。**EXE 实测 163,006,226 B** | 柯桥良（实测） |

## P1（结构性 / 可维护性 / 跨端一致性）

| # | 问题 | 来源 |
|---|---|---|
| P1-A | `app.py` **1197 行单文件混职责**（`MainWindow` 441 / `BoardWidget` 363 / 6 Dialog 291 / 头+Worker 92）。**结论：该拆，但按职责不按屏幕**；Dialog 拆开收益有限，真正值钱的是抽无 Qt 依赖的纯模块 | 寇豆码 + 柯桥良（双源，构成数据完全对得上） |
| P1-B | `refresh()` 是 250ms「god-poll」：每 tick `in_check` + `history.clear()+addItems()` 全量重建 + 重建阵亡文本 + 全盘重绘，并把**统计落盘/自动存档/模态弹窗**三个副作用藏在定时器里 ⇒ 4 个隐性同步点 | 寇豆码 |
| P1-C | `human_move` 的**内联升变集 = `promotion_types` 的第 4 份拷贝**（前 3 份已在 `bfea053` 收敛） | 寇豆码 + 柯桥良（双源） |
| P1-D | 类型标注缺口 **100% 集中在 `app.py`**：实测 **25%**（111 def / 28 有返回标注）；`audio`/`config`/`storage` 均 100%，`core/rules` 98% | 寇豆码（AST 实测，已修正柯桥良 grep 的 33%） |
| P1-E | 资源不走 Qt 资源系统，靠 **`package-data` 与 `--add-data` 两处手工同步**；新增资源目录极易漏 | 柯桥良 |
| P1-F | `config_path` 用 **Windows-only 的 `APPDATA` 约定**（mac 应为 `~/Library/Application Support`，Linux 应为 `~/.config`） | 柯桥良 |
| P1-G | **两份 `.spec` 都是孤儿**：根 `XionghanChess.spec` 硬编码 `C:\Users\27415\PycharmProjects\...`（仅原机可解析）；`packaging/xionghan_chess.spec` 从未被任何脚本引用，且缺 `core/data` 与 `locales` 两个 `--add-data` | 柯桥良 |
| P1-H | **无任何更新机制**（`grep update/version` 于 `desktop/` 只命中 Qt 的 `self.update()` 重绘） | 柯桥良 |
| P1-I | **i18n 有一个真实盲区**：`test_locale_keys_are_paired` 只保证 zh/en 成对，**不保证「桌面/web 实际用到的 key 存在」** ⇒ 「两边都缺同一个 key」这类缺陷无人发现 | 严过关 |
| P1-J | **英文半翻译**：`app.py` 93 行含中文（严过关口径=含 Han 的行数）/ 177 条中文字面量（游有方位口径）；`self._t(` 0 命中，大量文案走 `'中文' if lang!='en' else 'English'` 内联三元 ⇒ 英文只覆盖约一半 | 游有方 + 严过关（双源，口径已并列注明） |
| P1-K | `import_puzzles` 是**空壳**（选了 JSON 只弹一句提示，什么都没导入）—— 虚假功能 | 游有方 |
| P1-L | 做训练题会**偷偷改全局 profile**（`show_training` 里 `self.config["profile"]=self.game.profile.id`）—— 做了个 traditional 题，主对局静默变 10×9 | 游有方 |
| P1-M | 「残局与排局训练」**名不副实**：`puzzles.json` 9 条全是「开局第一步」drill，**0 条残局**；特色子只覆盖 4 种，**甲/刺/楯 零覆盖** | 游有方 |
| P1-N | **改设置 = 丢对局 + 全窗口重建**（`settings()` 里 `menuBar().clear()` + `centralWidget().deleteLater()` + `_build()` + `new_game()`） | 游有方（寇豆码的 S0–S11 未单列此项，**汇编时并入 S4**） |
| P1-O | `msyh.ttc`/`simkai.ttf` 是**微软授权字体**，随包分发有许可风险（未查证授权文本） | 柯桥良 |
| P1-P | 无代码签名/公证（Win SmartScreen 警告、mac Gatekeeper 拦截） | 柯桥良 |
| P1-Q | `load_bundled_fonts()` 依赖 `QApplication.instance()` 非空 ⇒ 单测里直接 `MainWindow()` 会 `AttributeError`（可测试性障碍之一） | 寇豆码 |
| P1-R | `config.py` 无 schema 版本，浅合并 `{**DEFAULTS, **data}`，删键/改类型无迁移路径 | 寇豆码 |
| P1-S | `DesktopAudio` 未订阅 `QSoundEffect.statusChanged` ⇒ 文件缺失/格式不支持时**静默无声**；且构造时即解析 45 MB WAV（**即使 `music=False`**） | 寇豆码 + 柯桥良（双源） |

## P2（可选优化 / 长期）

| # | 问题 | 来源 |
|---|---|---|
| P2-A | 200%+ DPI + 最小窗 760×560 下 13×13 可读性**未确证**（需体验侧实测） | 寇豆码 |
| P2-B | mac/Linux 无构建路径（源码可移植，但只有 `build_windows.ps1`） | 柯桥良 |
| P2-C | `--exclude-module` 裁未用 Qt 模块 / 评估 Nuitka（进一步瘦身与启动） | 柯桥良 |
| P2-D | 无安装器（用户自己找 exe）；Inno Setup 商业用途需购许可、WiX v6 对年收入 >$10k 公司收维护费（选型需注意） | 柯桥良 |

---

# 三、迭代升级计划

**依赖顺序的总原则**（柯桥良裁定，汇编采纳）：
> 先 **P0 止血**（让「能构建、能验证」成立）—— 因为后续所有重构都需要一个**可复现的构建**来验证；
> 再 **P1 结构**（拆包/资源/平台目录）—— 它们互相独立但都依赖「构建可用」；
> 最后 **长期**（跨平台分发/安装器/更新）—— 依赖前面全部就绪。
> **每一步都可独立回归（全量 pytest + 桌面冒烟）。**

## 阶段 0｜止血（**2–2.5 人日**）

| # | 做什么 | 对应问题 | 验收标准 | 工时 |
|---|---|---|---|---|
| **S0-A** | 修 `build_windows.ps1` 的路径缺陷（`Join-Path`）+ 补装 `[build]` extra（PyInstaller + Pillow）+ 脚本显式声明权威归属 | P0-A | **在干净 `.venv` 上跑一次脚本即产出 EXE**，无需手动补依赖 | 0.5d |
| **S0-B** | 修 `icon.ico`：换成真 `.ico`（或构建期用 Pillow 转）；同步删 `web/assets/icon.ico` 那份重复 | P0-B | PyInstaller 不再报格式错；**全仓 `.ico` 计数 = 1** | 0.5d |
| **S0-C** | 修两处 UI 冻结：`http_json`/`request_json` 移到 `QThreadPool`；`show_analysis` 改异步 + 进度提示 | P0-C | 服务不可达时窗口**不再冻结 15s**；分析时 UI 仍响应 | 1.0d |
| **S0-D** | 认输加二次确认，**与 Web 端行为对齐**（保留「提和」的确认作对照） | P0-F | 见验收清单 **D-07** | 0.25d |
| **S0-E** | CI 加桌面 offscreen 冒烟 job（**建议单独 job + 仅 Windows runner** —— PySide6 安装态 ~656 MB，会显著拉长 CI；若嫌重可退为「仅发版前跑 + CI 只加资源断言」） | P0-D/E | CI 红 = 桌面 import 失败；**探活用副作用而非日志**：`%APPDATA%\XionghanChess\` 被创建 + `settings.json` 落盘 | 0.5d |

## 阶段 1｜结构与瘦身（**6–8 人日**，依赖 S0-A/S0-B）

| # | 做什么 | 对应问题 | 工时 |
|---|---|---|---|
| S1-1 | **先拆无 Qt 依赖的纯模块**：`theme.py` → `appcfg/`（`config`+`storage`，并修 `config_path` 平台化）→ `net/`（`http_client` 可注入 transport + `reconnect` 纯策略 + `session`）→ `game/`（`controller` + `refresh_policy` + `ai_service` + `sound_cues`） | P1-A/B/I | 3.0d |
| S1-2 | **再拆 Qt 模块**：`ui/board_geometry.py`（纯函数，坐标换算）→ `ui/board_widget.py`（原样搬）→ `ui/dialogs/`（6 个 QDialog 逐个搬）→ `ui/fonts.py` | P1-A/Q | 2.0d |
| S1-3 | `human_move` 内联升变集改调 `rules.promotion_types`（消除第 4 份拷贝） | P1-C | 0.25d |
| S1-4 | 类型标注补齐（`app.py` 25% → ≥85%；优先级：吃网络 JSON 的 `human_move`/`finish_ai`/`network_message`/`apply_network_state`/`refresh` 先行） | P1-D | 1.0d |
| S1-5 | **BGM 格式转换**：两首 WAV → OGG（`QMediaPlayer` 播放，`QSoundEffect` 保留给短音效） | **P0-G（省 ~70 MB）** | 1.0d |
| S1-6 | 背景 JPG 重压缩（质量 ~75） | **P0-G（省 ~13 MB）** | 0.25d |
| S1-7 | **构建期资源断言**（优先于 qrc 化）：构建时校验三份 `--add-data` 目标都存在且非空 | P1-E | 0.5d |
| S1-8 | i18n key 用例（A5）：扫 `app.py` 里 `t("…")` 字面量集合，断言 ⊆ `locales/zh-CN.json` 扁平键集 | P1-I | 0.25d |
| S1-9 | 并入「改设置不重开对局」（P1-N） | P1-N | 0.5d |

## 阶段 2｜长期（**8–12 人日**，依赖阶段 1）

| # | 做什么 | 对应问题 |
|---|---|---|
| S2-1 | Windows 安装器（Inno Setup / MSIX）+ 代码签名 | P1-P / P2-D |
| S2-2 | mac/Linux 构建（`.app`+dmg；AppImage/Flatpak） | P2-B |
| S2-3 | 版本检查 + 「打开下载页」式更新（**先不做静默自更新**） | P1-H |
| S2-4 | 微软授权字体换开源思源宋体（规避分发风险） | P1-O |
| S2-5 | `.qrc` 分层资源化：**小件进**（icon/avatars/docs，把「静默丢图标」变成显性 ImportError）；**大件绝不进**（两首 33.5/45.0 MB WAV、15 MB 背景 —— 会变成 45 MB 的 Python 字面量） | P1-E |
| S2-6 | `--exclude-module` 裁 Qt 模块 / 评估 Nuitka | P2-C |
| S2-7 | 补「残局与排局训练」的真实内容（甲/刺/楯零覆盖、9 条全是开局 drill） | P1-M |

---

# 四、验收与回归（严过关的验证面产出）

## 4.1 三层验收
1. **自动化**：全量 `pytest`（当前 240）+ 阶段 0 起的桌面 offscreen 冒烟 + S1-8 的 i18n key 用例
2. **打包产物冒烟**（Windows runner 可行）：构建 EXE → 启动 → **用副作用探活**（`%APPDATA%\XionghanChess\` 创建 + 关窗时 `settings.json` 落盘）→ 关闭。建议只在 push master / 手动触发时跑（PyInstaller 单文件构建 2–5 分钟）
3. **手工验收**：**`D-01 ~ D-17` 清单**（含前置/操作/可观测期望/优先级），其中 **D-07（认输二次确认）、D-09（英文无残留）、D-12（棋谱导出导入往返）、D-17（干净机跑 EXE）为 P0**

## 4.2 测试策略 ROI 排序（严过关）
| # | 测什么 | 收益 |
|---|---|---|
| A3 | `play_sound` 五路音效选择 | **高**（音效选错今天纯靠耳朵，没人验） |
| A4 | 棋盘坐标映射 `_view_position`/`_position`（含 `flipped`，双向断言） | **高**（点错格子是最刺眼的用户可见缺陷） |
| A5 | 桌面用到的 i18n key 是否都存在 | **高**（一次挡住一类「用户看到裸 key」） |
| A6 | `resign_game`/`draw_game` 的确认语义 | 高（正是 P0-F） |
| A2 | `config.py` 读写合并（`tmp_path` + monkeypatch，已有先例） | 中 |
| A1 | `_clock(ms)` → `mm:ss` | 低但顺手 |

## 4.3 GUI 自动化的边界（**别承诺测不了的**）
- **测得**（需装 `pytest-qt` + PySide6）：自有 widget 的模拟点击/键盘、`QMessageBox.question` 可 monkeypatch 并记录返回值、列表/标签文本、`qtbot.waitSignal`
- **测不了**：真实音频输出（只能断言 `DesktopAudio.play` 被调用）、真实渲染像素、原生窗口行为（最小化/全屏/DPI/多显示器/原生文件对话框）、`QWebSocket` 联机（降为手工）、PyInstaller EXE 本体

## 4.4 回归门槛
| 改了什么 | 必须跑 |
|---|---|
| `desktop/` | 全量 `pytest`（240 条） |
| `locales/` 或 `i18n.py` | 全量 + **A5**（i18n key 用例） |
| `core/` | 全量 + 跨引擎对拍 84 条（三端共同护栏） |

---

# 五、未决与风险（如实记录，不当成已解决）

| # | 事项 | 状态 |
|---|---|---|
| 1 | **主程序（寇豆码）在阶段 0 授权后调度失败**（429 队列限流，`Duration: 1s`） | 若阶段 0 要由它实施，**需重新派单**；当前无人实施阶段 0 |
| 2 | `msyh.ttc`/`simkai.ttf` 授权条款 | **未查证** —— 建议换开源思源宋体（S2-4） |
| 3 | mac/Linux 可运行性 | **未实测**（源码无平台分支是事实，但无对应机器验证） |
| 4 | 200%+ DPI 下 13×13 可读性 | **未确证**，需体验侧实测 |
| 5 | EXE 在「干净无 Python 机器」上的表现 | **未验证**（本机 `.venv` 有 PySide6；D-17 尚未跑） |
| 6 | onefile 启动惩罚 **+1.5–2.0s**（2.726s vs dev 1.201s） | 已实测；若在意可评估 onedir 分发 |

---

## 附：一句话总结

> **桌面版的「对局内核」是好的（AI 1154× 余量不卡界面、core 边界干净、启动 0.8–1.2s），
> 「交付层」是断的（构建链两个 P0 + 图标是假 ico ⇒ 仓库脚本造不出 EXE），
> 「护栏层」是空的（桌面 ~1300 行零自动化，坏了只能靠用户第一个发现）。
> 阶段 0（2–2.5 人日）把「能构建 + 能验证 + 两个体验硬伤」补上，是投入产出比最高的一步。**
