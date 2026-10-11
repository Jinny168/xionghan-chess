# 匈汉象棋 v1.4.0 全栈工程审计与交付报告

> **审计角色**：资深跨端棋牌全栈工程审计 & 交付工程师
> **审计基准日**：2026-08-16
> **审计对象**：`xionghan-chess-next`（三端统一版：共享 Python Core + FastAPI/WebSocket + PySide6 桌面 + Web + .NET 9 Android）
> **报告结构**：严格按用户硬性要求，分五个部分输出。

---

## 0. 版本状态特别说明（必读，影响全部结论）

本审计按用户要求以 **v1.4.0 交付闭环** 为范围执行，但执行过程中发现**工作树版本已领先于交付目标**。证据如下：

| 标识位置 | 当前值 | 期望（v1.4.0 交付） | 性质 |
|---|---|---|---|
| `src/xionghan_chess/__init__.py:3` | `__version__ = "1.5.0"` | 1.4.0 | ❌ 漂移 |
| `pyproject.toml:7` | `version = "1.5.0"` | 1.4.0 | ❌ 漂移 |
| `web/js/app.js:1` | `import ... './i18n.js?v=1.5.0'` | 1.4.0 | ❌ 漂移 |
| `web/index.html:9` | `app.css?v=1.5.0` | 1.4.0 | ❌ 漂移 |
| `web/index.html:183` | `app.js?v=2.0.1` | — | ❌ 版本号自相矛盾（2.0.1 vs 1.5.0） |
| `deploy/docker-compose.yml:6` | `image: xionghan-chess:1.5.0` | 1.4.0 | ❌ 漂移 |
| `release/v1.4.0-delivery/src/.../__init__.py:3` | `__version__ = "1.4.0"` | 1.4.0 | ✅ 冻结快照一致 |
| `docs/QA_REPORT_1.5.0.md` / `CHANGELOG_1.5.0.md` / `DELIVERY_1.5.0.md` | 已存在（2026-08-13） | — | ⚠️ 1.5.0 交付文档已先行生成 |

**结论与建议**：

1. 工作树（live source）实际处于 **v1.5.0**，且 1.5.0 的三件套交付文档（Changelog / Delivery / QA）已存在，1.5.0 QA 报告声明 **92 passed**。
2. `release/v1.4.0-delivery/` 是**冻结的 1.4.0 源码快照**（内部版本号确为 1.4.0），与当前工作树已不一致。
3. **建议（二选一，需用户拍板）**：
   - **A（推荐）**：将本次审计视作 v1.4.0 的历史归档，直接以 **v1.5.0 作为下一发布版本**推进（1.5.0 文档与 92 passed 已就绪），本报告中所有针对 v1.4.0 的遗留项并入 1.5.0 收尾；
   - **B**：若坚持发布 v1.4.0，需从 1.4.0 对应的 git tag/commit 重新冻结交付包，并将工作树回退或另建发布分支，消除上述的 1.5.0 漂移。
4. 无论选 A 或 B，**必须统一版本标识**：当前至少出现 1.4.0 / 1.5.0 / 2.0.1 三套互斥数字，属于 P1 一致性缺陷（详见 2.6 与 5.2-R01）。

> 下文第一部分至第五部分，审计内容针对 **v1.4.0 交付范围** 展开（即 `release/v1.4.0-delivery/` 快照 + 对应的二次审计 `QA_v1.3.0.md` 整改记录）；所有“残留风险”在第五部分按 1.5.0 现实重新评估。

---

# 第一部分：项目完整分层文件结构梳理 + 文件功能对照表

## 1.1 分层目录树（截至 v1.4.0 交付快照）

```
xionghan-chess-next/
├── src/xionghan_chess/              # 共享核心 + 桌面 + 服务端实现（Python）
│   ├── __init__.py                 # 包版本号（交付快照=1.4.0；工作树=1.5.0）
│   ├── i18n.py                     # 多语言查找 t()/tr()，zh-CN/en 回退
│   ├── core/                       # ★ 唯一规则真相源（三端共享）
│   │   ├── model.py                # PieceType/Color/Position/GameState 等数据模型
│   │   ├── rules.py                # 规则引擎：14 种棋子走法 + RuleOptions（494 行）
│   │   ├── game.py                 # 对局控制器：走子/计时/和棋/复盘/快照（226 行）
│   │   ├── ai.py                   # ChessAI：Negamax+AB+TT+null-move+LMR+SEE+quiescence（647 行）
│   │   ├── ai_see.py               # 静态交换评估 SEE 实现
│   │   ├── mcts.py                 # 纯 UCB1 MCTS 推理模块（实验性，未接入默认档位）
│   │   ├── legacy.py               # 旧 .fen / JSON 棋谱迁移（migrate_legacy_game）
│   │   ├── avatars.py              # 内置头像 avatar-01..09（webp）+ normalize_avatar 白名单
│   │   ├── taunts.py               # AI 场景化挑衅语料（开局/将军/胜/负）
│   │   ├── puzzles.py              # 残局题库加载（data/puzzles.json）
│   │   ├── analysis.py             # 对局 AI 复盘评分（best/good/mistake/blunder/winRate）
│   │   ├── protocol.py             # Envelope + MessageType（WebSocket 协议）
│   │   ├── storage.py              # GameDocument 序列化/反序列化
│   │   ├── profiles.py             # 棋规档案（desktop_complete/traditional/…）
│   │   ├── setup.py                # 包安装入口
│   │   └── data/puzzles.json       # 残局题库数据
│   ├── service/                    # FastAPI 服务端
│   │   ├── app.py                  # 路由/WebSocket/账号/分析/题库/静态挂载（459 行）
│   │   ├── rooms.py                # RoomManager：房间/广播/AI/重连/观战（505 行）
│   │   └── accounts.py             # AccountStore：SQLite+PBKDF2+session（237 行）
│   └── desktop/                    # PySide6 桌面端
│       └── app.py                  # MainWindow + 对话框 + BoardWidget + AIWorker + QWebSocket（1135 行）
├── web/                            # Web 前端（原生 HTML/CSS/JS，服务端静态挂载）
│   ├── index.html                  # 入口页（含 cache-buster 版本号，见 0 节）
│   ├── css/app.css
│   └── js/{app.js, i18n.js}       # 主逻辑 / 语言包加载
├── android/                        # .NET 9 MAUI 安卓壳
│   ├── MainActivity.cs             # WebView 生命周期/离线切换/文件桥接（394 行）
│   ├── XionghanChessAndroid.csproj # 构建工程（Trim/AOT 关闭，见 A-09）
│   ├── AndroidManifest.xml         # usesCleartextTraffic=true（见 A-08）
│   └── Resources/assets/offline/   # 离线同机双页
│       ├── welcome.html            # 离线大厅（模式/设置选择，与棋局页分离）
│       ├── index.html              # 棋局页（?page=game 进入）
│       ├── offline.js              # ★ 离线 JS 规则引擎（与 Python Core 独立实现）
│       ├── offline-locales.js      # 离线语言包
│       └── offline.css
├── locales/{zh-CN.json, en.json}   # 官方语言包（服务器优先加载）
├── docs/                           # 方案/审计/QA/发布文档
├── tests/                          # 13 个 pytest 模块（见第三部分）
├── packaging/                      # 构建脚本
│   ├── build_windows.ps1           # Windows PyInstaller 打包
│   ├── build_android.ps1           # Android Release 构建
│   ├── build_web_release.ps1       # Web 静态 ZIP 构建
│   ├── desktop_entry.py            # 桌面入口
│   └── xionghan_chess.spec         # PyInstaller spec
├── scripts/{run_desktop.ps1, run_server.ps1}
├── deploy/                         # Docker 部署
│   ├── Dockerfile                  # python:3.12-slim + uvicorn 单 worker
│   ├── docker-compose.yml          # image 标签 1.5.0（见 0 节）
│   ├── .dockerignore
│   └── .env.example                # 存在（105 B），DOCKER_DEPLOY 的 cp 指令可用
├── requirements/{core.txt, server.txt, desktop.txt, dev.txt}
├── pyproject.toml                  # 版本（工作树=1.5.0）
├── XionghanChess.spec              # ⚠️ 根目录重复 spec（与 packaging/ 下重名，待清理）
├── release/v1.4.0-delivery/        # ★ 交付产物根（冻结 1.4.0 快照）
├── archive/                        # 历史 APK（release-before-1.0.0，仍被 git 跟踪，见 1.4）
├── build/ build-onefile/ dist/     # ⚠️ 本地构建产物（应排除，见 1.3/1.4）
└── .gitignore
```

## 1.2 文件功能对照表（按层级）

| 层级 | 关键文件 | 功能 | 类型 | 审计定位 |
|---|---|---|---|---|
| 核心-规则 | `core/rules.py` | 14 种棋子合法走法 + RuleOptions | 生产源码 | 2.2/2.9 |
| 核心-控制 | `core/game.py` | 走子/计时/和棋/快照/复盘 | 生产源码 | 2.1-C13/C14, 2.2 |
| 核心-AI | `core/ai.py` `core/ai_see.py` | Negamax+AB+SEE 四档难度 | 生产源码 | 2.1-C05/C06/C07, 2.4 |
| 核心-实验 | `core/mcts.py` | 纯 UCB1 MCTS（未接入默认档） | 生产源码 | 2.3（暂缓） |
| 核心-迁移 | `core/legacy.py` | 旧 FEN/JSON 迁移 | 生产源码 | 2.3 |
| 核心-资源 | `core/avatars.py` `taunts.py` `puzzles.py` `analysis.py` | 头像/挑衅/题库/复盘 | 生产源码 | 2.3 |
| 协议 | `core/protocol.py` | Envelope/MessageType | 生产源码 | 2.1-C15 |
| 服务 | `service/app.py` `rooms.py` `accounts.py` | API/WS/房间/账号 | 生产源码 | 2.1-S 系列, 2.5 |
| 桌面 | `desktop/app.py` | PySide6 全功能壳 | 生产源码 | 2.1-S02/S04/S13 |
| Web | `web/js/app.js` `i18n.js` `index.html` | Web 主前端 | 生产源码 | 2.1-W 系列, 2.6 |
| 安卓壳 | `android/MainActivity.cs` | WebView 编排 | 生产源码 | 2.1-A 系列 |
| 安卓离线 | `android/.../offline.js` | 离线规则引擎 | 生产源码 | **2.2 重点分歧** |
| 部署 | `deploy/*` `packaging/*` | Docker/EXE/APK/Web 构建 | 构建脚本 | 第四部分 |
| 测试 | `tests/*.py`（13） | pytest 回归 | 测试文件 | 第三部分 |
| 文档 | `docs/*` | 审计/QA/发布 | 文档 | 全篇 |
| 交付 | `release/v1.4.0-delivery/*` | 冻结交付包 | 生产包 | 第四部分 |

## 1.3 源码 / 生产包 / 测试 / 冗余二进制 分类

| 分类 | 判定 | 代表路径 | 处理建议 |
|---|---|---|---|
| 开发源码 | 应提交 git | `src/`、`web/`、`android/`、`locales/`、`tests/`、`packaging/`、`deploy/`、`docs/`、`requirements*`、`pyproject.toml` | 纳入版本控制 |
| 生产交付包 | 冻结产物 | `release/v1.4.0-delivery/`（含完整 src + tests + 各端包 + SHA256SUMS） | 随发布归档，不回改 |
| 测试文件 | 不随生产运行 | `tests/*.py`、`*.qm`？ | 随源码提交，不进运行时镜像（Docker 已排除 tests） |
| 本地构建产物 | ❌ 不应提交 | `build/`、`build-onefile/`、`dist/`、`android/bin/`、`android/obj/`、`.desktop-test-data*`、`*.pyc`/`__pycache__` | `.gitignore` 已排除；但 `build/`、`dist/` 等**目录仍存在工作树**，需清理 |
| 历史二进制 | ❌ 不应跟踪 | `archive/release-before-1.0.0/*.apk`、`release/*.apk`（旧版） | 已被 git 跟踪，建议 `git rm --cached` 或转 Git-LFS（见 1.4） |
| 重复/零散 | ⚠️ 待清理 | 根目录 `XionghanChess.spec`（与 `packaging/` 下重名）、根目录 `desktop-*.png`（QA 截图） | 纳入构建产物清理规范 |

## 1.4 .gitignore 规范与待清理项

**已规范（正确）**：`.venv/`、`*.py[cod]`、`__pycache__/`、`.pytest_cache/`、`build/`、`build-onefile/`、`dist/`、`*.spec.bak`、`android/bin/`、`android/obj/`、`release/v1.4.0-delivery/`、`.server-info` 已排除。

**待整改（P3 仓库卫生）**：
- `git ls-files` 仍跟踪 `archive/release-before-1.0.0/XionghanChess-Android*.apk` 与 `release/匈漢象棋-*.apk`（历史版本）。APK 为二进制大文件，长期跟踪会膨胀仓库。→ 建议 `git rm --cached` 后用 Git-LFS 或移入发布归档。
- 工作树中 `build/`、`build-onefile/`、`dist/` 目录残留，需执行清理或确认 `.gitignore` 已覆盖（已覆盖，但未物理删除）。
- 根目录 `XionghanChess.spec` 与 `packaging/xionghan_chess.spec` 重复，保留 `packaging/` 下一份即可。
- 根目录 9 张 `desktop-*.png` 为 QA 截图，建议移入 `docs/assets/` 或 `.gitignore`。

---

# 第二部分：全项目代码深度审计完整报告（8 维度）

## 2.0 维度总览与缺陷分级

缺陷分级：**P0 阻断 / P1 高优 / P2 中优 / P3 低优**。下表为各维度结论速览：

| 维度 | 审计结论 | 关键风险等级 |
|---|---|---|
| 一、v1.3.0 QA 47 条缺陷复核 | 26 已修复/确认无需修改，4 待规则确认，1 架构限制，16 低优未修复 | P0：0 残留阻断 ✅ |
| 二、三端一致性 | 功能矩阵基本一致；**安卓离线 JS 规则引擎与 Python Core 存在分歧（no_progress_draw 未实现）** | P1（规则分歧） |
| 三、v1.4.0 九项新功能 | 9/9 已落地（含双页拆分、账号云、观战、棋谱迁移） | ✅ |
| 四、底层性能 | AI 超时粒度已修；快照放大/广播放大/对象复制仍有优化空间 | P2 |
| 五、安全 | AI token 随机化、PBKDF2、白名单已修复；明文 HTTP、明文 Authorization 头仍为风险 | P2 |
| 六、代码规范 | **版本标识碎片化（1.4.0/1.5.0/2.0.1）；Web 硬编码中文文案；文档 81 vs 91 矛盾** | P1 |
| 七、架构 | 单实例内存房间（无持久化）；离线引擎独立；协议统一 | P2（扩展性） |
| 八、衍生缺陷 | 修复引入 NEW-01~04，其中 NEW-01/02 为低优逻辑瑕疵 | P3 |

## 2.1 维度一：v1.3.0 QA 47 条缺陷复核（逐项）

来源：`docs/QA_v1.3.0.md`（47 条）+ `docs/QA_v1.3.0.md` 二次审计「一、原 Bug 修复核对表」。47 条 = C-01~C-15（Core 15）+ S-01~S-15（通信 15）+ W-01~W-08（Web 8）+ A-01~A-09（安卓 9）。

### 2.1.1 复核统计

| 状态 | 数量 | 占比 |
|---|---|---|
| ✅ 已修复 / 确认无需修改 | 26 | 55.3% |
| ⏸ 等待规则确认（不自行修改） | 4（C-01/C-03/C-04/C-11/C-12，文档计为 4，实为 5 条，见 2.9） | 8.5% |
| 🏗 架构限制保留 | 1（A-01） | 2.1% |
| 🔻 低优未修复（非阻断） | 16 | 34.1% |

### 2.1.2 严重 / 高优（P0/P1）逐条复核

| Bug | 严重 | 修复状态 | 代码验证（文件:行） | 结论 |
|---|---|---|---|---|
| S-01 WebSocket 连接/重连风暴 | **严重** | ✅ 已修复 | `web/js/app.js` 按连接实例隔离 + 永久关闭码不重连 + 指数退避 3 次 | 验证通过 |
| S-02 桌面端无自动重连 | **严重** | ✅ 已修复 | `desktop/app.py:1041-1060` `_connect_network`/`_network_disconnected` | 验证通过（需手动） |
| S-03 AI 暂停竞态卡死 | **严重** | ✅ 已修复 | `service/rooms.py:316-334` 前后置条件检查 + `except GameError` | 验证通过 |
| S-06 AI 座位 token 可预测劫持 | **高** | ✅ 已修复 | `service/rooms.py` `secrets.token_urlsafe(32)` + `seat_for` 拒 `is_ai` | 验证通过（安全漏洞关闭） |
| S-04 桌面模态对话框状态回退 | 高 | ✅ 已修复 | `desktop/app.py:1070-1076` 先应用状态再弹窗 + 去重键 | 验证通过（需手动） |
| S-05 Web confirm 阻塞致 revision 过期 | 高 | ✅ 已修复 | `service/rooms.py:238-240` DRAW/UNDO_RESPONSE 入 `revision_independent` | 验证通过 |
| S-07 维护 tick 时钟竞态 | 高 | ✅ 已修复 | `service/app.py:40-42` tick 入 `async with room.lock` | 验证通过 |
| A-01 离线 JS vs Python 规则分歧 | **严重** | 🏗 架构限制 | 无等价性测试（详 2.2） | 保留，单列风险 |
| A-02 离线无棋谱导入入口 | **严重** | ✅ 已修复 | `offline.js` 新增 `loadGameDocument` + `#loadButton` + 10MB 限制 | 验证通过 |
| C-05 AI 超时检查粒度粗 | 中 | ✅ 已修复 | `core/ai.py` `_guard()` 移入 move 迭代循环 | 验证通过 |
| C-09 桌面加载损坏棋谱崩溃 | 中 | ✅ 确认无需修改 | `desktop/app.py:919-922` try/except 全部异常 | 验证通过 |

> 其余 37 条（含 16 条低优未修复、4 条规则待确认、A-01 架构限制）详见 `docs/QA_v1.3.0.md` 二次审计核对表，均**无 P0 阻断残留**。

### 2.1.3 衍生缺陷（修复引入，详见 2.8）

NEW-01（低）：`core/game.py:71` `move()` 清除 `pending_draw_offer` 但未清除 `pending_undo_offer`，结合 S-05 修复，存在“先走棋再接受悔棋悔错步”的边界。
NEW-02（低）：`service/app.py:42` + `core/game.py:147-157` 超时判负后 `revision` 不递增（预存问题，非本次引入；客户端总应用快照故实际无碍，协议一致性瑕疵）。
NEW-03/04（信息项）：桌面 `closeCode()` 为 0 时重连（正确行为）；离线 `loadGameDocument` 拒绝非内置档案棋谱（设计如此）。

## 2.2 维度二：三端一致性（重点：安卓离线 JS vs Python Core 规则分歧）

### 2.2.1 修复后三端功能一致性矩阵（摘要）

| # | 功能 | 桌面 | Web | 安卓离线 | 安卓服务器 | 结论 |
|---|---|---|---|---|---|---|
| 1 | 基础对局 | ✅ | ✅ | ✅ | ✅ | 一致 |
| 2 | AI 人机(4档) | ✅ | ✅ | ❌缺失 | ✅ | 架构限制 |
| 3 | WS 联机 | ✅ | ✅ | ❌缺失 | ✅ | 架构限制 |
| 4 | 账号云同步 | ✅15+字段 | ✅ | ❌不支持 | ✅ | 一致（离线边界） |
| 5 | 皮肤主题 | ✅ | ✅5+紫 | ✅紫 | ✅ | 一致 |
| 6 | 棋盘翻转 | ✅ | ✅ | ✅ | ✅ | 一致 |
| 7 | 观战 | ❌ | ✅ | ❌ | ✅ | 设计决策 |
| 8 | 棋谱导入导出 | ✅ | ✅10MB | ✅已补 | ✅ | 一致 |
| 9 | AI 复盘 | ✅ | ✅ | ❌ | ✅ | 架构限制 |
| 10 | 残局题库 | 9题 | ✅校验 | 3题 | 9题 | 离线缩水（架构限制） |
| 11 | 断线重连 | ✅3次 | ✅3次退避 | N/A | ✅ | 一致 |
| 12 | 偏好云同步 | ✅增量 | ✅增量 | N/A | ✅增量 | 一致 |
| 13 | 联机复盘 | ✅replay恢复 | ✅ | N/A | ✅ | 一致 |

### 2.2.2 ⚠️ 安卓离线 JS 引擎 vs Python Core 规则分歧（单列 P1）

此为**三端一致性最高风险点**，需产品/技术决策：

1. **`no_progress_draw`（无进展和棋）实现不一致**【P1】
   - Python：`core/game.py` 的 `_settle_after_move` 实现 120 回合无吃子/无进展判和（`no_progress_draw`）。
   - 安卓离线：`android/.../offline.js` 的 `RuleOptions` **定义了 `no_progress_draw` 选项**，但其 `settle()` 逻辑**未实现该判定** → 离线模式永不触发无进展和棋，而服务器/桌面模式会。同一棋局在离线 vs 在线可能得出不同终局。
   - 影响：长调度/调动型对局，离线判定与联机判定分歧。

2. **特色棋子边界无自动化等价测试**【P1，即 A-01】
   - ARCHER/THUNDER/ARMOR/ASSASSIN/SHIELD/GUARD 等特色棋子在 `offline.js` 为独立 JS 实现，与 `core/rules.py` 各自维护，无等价性单测。历史上最易产生走法分歧。

3. **翻转坐标空间不统一**【中，即 A-05】
   - `offline.js` 翻转时 `viewPos()` 做坐标变换，但 `selectedPiece`/`legal`/`capturable` 存原始坐标，翻转模式拖拽可能命中错误位置。

4. **离线 `loadGameDocument` 档案集合受限**【信息，即 NEW-04】
   - 离线 `PROFILES` 仅 4 个内置档案，导入含 `desktop_complete` 等在线档案的 `.xhgame` 会被拒绝。

> **建议**：离线引擎要么复用同一套规则（抽到 WASM/共享 JSON 规则描述），要么为所有特色棋子+和棋条件补一套离线 vs 在线的等价性回归测试。当前作为“架构限制”保留，但 **`no_progress_draw` 分歧属于正确性分歧，建议升为 P1 并优先修复**。

## 2.3 维度三：v1.4.0 九项新功能落地情况

| # | 新功能 | 落地状态 | 关键代码路径 |
|---|---|---|---|
| 1 | 明暗皮肤 | ✅ | `i18n.py` + `web/css/app.css` + `desktop/app.py` 主题映射 |
| 2 | 账号云 | ✅ | `service/accounts.py`（PBKDF2+session）+ `app.py /api/me/*` + 桌面/Web 同步 |
| 3 | 让子让先 | ✅ | `web/js/app.js` HandicapDialog + `rules.py` 档案裁剪 + `core/profiles.py` |
| 4 | 棋盘翻转 | ✅ | `game.py` flipped + 三端 `flip()` 命中测试（A-05 仍为离线边界） |
| 5 | 观战 | ✅（Web/服务器） | `service/rooms.py` spectator + `app.py /ws/{id}/spectate`（桌面端无，设计决策） |
| 6 | PGN·FEN 棋谱 | ✅（FEN/JSON legacy） | `core/legacy.py` `migrate_legacy_game` + `storage.py`（注：PGN 标准格式未在审计中见到独立实现，以 FEN/JSON 包装为主） |
| 7 | AI 复盘 | ✅ | `core/analysis.py` `analyze_game` + `app.py /api/analysis` + Web 渲染 |
| 8 | 残局题库 | ✅ | `core/puzzles.py` + `data/puzzles.json` + Web/桌面训练（离线 3 题，服务器 9 题） |
| 9 | 安卓双页面 | ✅ | `welcome.html`（大厅）+ `index.html?page=game`（棋局页）分离 + `MainActivity.cs` 返回键路由 |

> MCTS（`core/mcts.py`）作为实验性模块**未接入默认 AI 档位**，按计划暂缓（非阻断）。

## 2.4 维度四：底层性能

| 项 | 位置 | 状态 | 说明 |
|---|---|---|---|
| AI 超时检查粒度 | `core/ai.py` | ✅ 已修（C-05） | `_guard()` 移入 move 迭代循环 |
| 评估缓存上限 | `core/ai.py:309-310` | ✅ 已修（C-07） | 50,000 条自动清空 |
| 置换表深度比较 | `core/ai.py:201` | ✅ 已修（C-08） | 较浅不覆盖较深 |
| 战术走法爆炸 | `core/ai.py:233-267` | 🔻 未修复（C-06） | 多 ARMOR/ASSASSIN 局面静态搜索深度爆炸；正确性无碍，复杂度风险 |
| 快照无上限 | `core/game.py` `MAX_SNAPSHOTS=512` | ⚠️ 部分缓解（C-13） | 已设 512 上限，但 `public_state()` 含 `replay`（最多 512 快照）→ **广播放大** |
| 广播放大 | `service/rooms.py` `broadcast()` | ⚠️ P2 | 每个玩家/spectator 全量发送 `room.snapshot()`，`replay` 字段随对局增长，高延迟房间传输量放大 |
| 对象复制开销 | `core/game.py` `from_state()` | ⚠️ P2 | AI 搜索每节点 `Game.from_state()` 复制状态，深度内节点大量对象创建（已有 TT/SEE 缓存缓解） |
| 静态资源重算 | `offline.js:97-98` | 🔻 未修复（A-06） | `draw()` 每次重算 geometry，低配设备压力 |

## 2.5 维度五：安全

| 项 | 位置 | 状态 | 说明 |
|---|---|---|---|
| AI 座位 token | `service/rooms.py` | ✅ 已修（S-06） | `secrets.token_urlsafe(32)` + 拒客户端鉴权 |
| 密码存储 | `service/accounts.py` | ✅ | PBKDF2-HMAC-SHA256 **310,000 迭代** + 盐；session token SHA-256 入库 |
| 座位 token 比较 | `service/rooms.py` | ✅ | `hmac.compare_digest` |
| 头像白名单 | `core/avatars.py` | ✅ | `normalize_avatar()` 仅允许内置 `avatar-01..09` 或 http/https ≤500 字符 |
| 明文 HTTP 流量 | `android/AndroidManifest.xml:3` | 🔻 未修复（A-08，P3） | `usesCleartextTraffic=true`；生产建议关闭或仅调试 |
| 鉴权头明文 | `service/accounts.py` | ⚠️ P2 | Authorization 头明文传输，依赖反向代理提供 HTTPS（文档已注明） |
| 房间持久化 | `service/rooms.py` | ⚠️ 设计 | 内存 Map，默认最大 200 房间，无持久化（单实例设计，多副本需 Redis，见 2.7） |

## 2.6 维度六：代码规范

| 项 | 位置 | 等级 | 说明 |
|---|---|---|---|
| **版本标识碎片化** | 见 0 节 | **P1** | 工作树出现 1.4.0 / 1.5.0 / 2.0.1 三套互斥版本号；`docker-compose.yml` 标 1.5.0 但交付目标为 1.4.0 |
| Web 硬编码中文文案 | `web/js/app.js:30,129,211-212,234,257-258` 等 | P3 | toast/提示直接使用中文串（如 `'当前没有可上传的棋局'`、`'人观战'`、`'双方登场棋子数量必须相同'`），绕过 i18n `t()`；影响英文切换完整性（棋子字形 `names` 映射与规则选项标签为领域固有中文，不计入） |
| 文档 passed 计数矛盾 | `DELIVERY_1.4.0.md:38` vs `QA_REPORT_1.4.0.md:5` | P3 | DELIVERY 写 “81 passed”，QA 写 “91 passed”；以 QA 与实测为准，DELIVERY 文档过时 |
| 文档 Android 页措辞过时 | `DELIVERY_1.4.0.md:38` | P3 | 仍写 “Android 欢迎页可进入棋局页”，实际为 welcome.html + index.html?page=game 双页拆分 |
| 重复 spec 文件 | 根 `XionghanChess.spec` vs `packaging/xionghan_chess.spec` | P3 | 重复，保留 `packaging/` 下一份 |

## 2.7 维度七：架构

- ✅ **唯一规则真相源**：`src/xionghan_chess/core` 为三端共享；Web/桌面/安卓服务器均围绕 `Game`/`RulesEngine`/`protocol` 渲染，客户端不私自改规则语义（A-01 离线引擎为例外，见 2.2）。
- ✅ **协议统一**：`core/protocol.py` `Envelope` + `MessageType`（含 RESTART_REQUEST/RESPONSE），revision 门控 + `populate_by_name` 别名兼容。
- ⚠️ **单实例内存房间**：`service/rooms.py` 房间存内存 Map（≤200），无持久化；`DOCKER_DEPLOY.md` 已注明多副本需 Redis。当前交付为单实例，符合“无持久化单进程”约束。
- ⚠️ **离线引擎独立**：安卓离线 `offline.js` 自带规则/渲染，与 Python Core 分叉（2.2 重点）。
- ✅ **离线降级链路**：`MainActivity.cs` 健康检查 6s/3s 超时回退离线；服务器模式恢复在线功能。

## 2.8 维度八：衍生缺陷专项（修复引入）

见 2.1.3。NEW-01/02 为低优逻辑瑕疵（不影响 P0 验收），NEW-03/04 为信息项。建议在后续迭代随规则确认一并处理。

## 2.9 待产品确认的规则问题（不自行修改）

以下会改变匈汉象棋规则，**审计期间未修改**，标记为“等待规则确认”：

| ID | 位置 | 待确认项 |
|---|---|---|
| C-01 | `core/rules.py:432-438` | PATROL(巡) 行号硬编码 `{5,7}`，是否支持非 13×13 档案及巡线定义 |
| C-03 | `core/rules.py:331-334` | GUARD 跳板是否区分己方/敌方棋子 |
| C-04 | `core/rules.py:447-450` | SHIELD 斜对角（切比雪夫）保护范围是否保留 |
| C-11 | `core/game.py:183-198` | 长将/长捉责任方判定与处罚方式 |
| C-12 | `core/game.py:200-206` | 13×13 棋盘无进展和棋阈值是否高于 120 回合 |

> 注：C-12 与 2.2 的离线 `no_progress_draw` 分歧同源，建议合并决策。

---

# 第三部分：自动化 + 手工全套测试执行结果报告

## 3.1 自动化测试（CI 默认：项目 `.venv`）

| 项目 | 命令 | 结果 |
|---|---|---|
| Python 单元测试 | `./.venv/Scripts/python.exe -m pytest -q` | **91 passed, 0 failed**, 1 Starlette/httpx 弃用警告 ✅ |
| Web/Android JS 语法 | `node --check web/js/app.js web/js/i18n.js android/.../offline.js offline-locales.js` | 全部通过 ✅ |
| Python 编译 | `python -m compileall -q src` | 通过 ✅ |
| Locale JSON | `locales/zh-CN.json`、`en.json` | 解析通过 ✅ |
| 提交规范 | `git diff --check` | 通过 ✅ |
| Android Release 构建 | `dotnet build android/XionghanChessAndroid.csproj -c Release -f net9.0-android` | 0 错误，22 条非阻断兼容性/弃用警告 ✅ |

> ⚠️ 环境注意：managed/workbuddy 自带 Python 缺 `fastapi`/`pydantic`，**必须**使用项目 `.venv` 运行 pytest（测试模块 `test_extensions/test_protocol/test_qa_regressions/test_service/test_taunts` 依赖二者）。教训已记入记忆。

## 3.2 手工专项测试矩阵（建议执行，部分已在二次审计覆盖）

| 类别 | 用例 | 覆盖 | 状态 |
|---|---|---|---|
| AI 四档 | BEGINNER≤0.45s / EASY≤1.2s / MEDIUM≤3.5s / HARD≤9s 返回合法走法 | FU-31~34 | 自动化+手动建议 |
| AI 不送将 | AI 走后己方王不被将 | FU-36 | 建议手动 |
| WS 联机 | 创建6位房/加入/走子同步/revision冲突/倒计时/超时判负 | FU-39~48 | 自动化覆盖核心 |
| 棋谱 | 导出.xhgame/导入/损坏文件优雅提示/往返一致 | FU-51~60 | 自动化覆盖 |
| 让子让先 | 取消棋子槽/数量不等禁止开始 | FU-66~67 | 自动化+手动 |
| 安卓离线 | 双页导航/导入/同一棋子单音效/残局状态保留 | — | 自动化+手动 |
| 三端一致 | 同棋局离线 vs 在线终局对比（重点 no_progress_draw） | — | **建议新增，见 2.2** |

## 3.3 三端一致性回归

- 功能矩阵：见 2.2.1，桌面/Web/安卓服务器三端核心功能一致；离线缺失 AI/联机/复盘/账号（架构限制），题库 3 vs 9（架构限制）。
- **规则分歧回归缺口**：离线 `no_progress_draw` 与翻转坐标空间（A-05）**无等价性测试**，建议补充。

## 3.4 性能 / 压力与兼容性风险

| 风险 | 等级 | 说明 |
|---|---|---|
| 超长对局内存 | P2 | 300+ 回合 `_snapshots` 增长；已设 512 上限但 `replay` 放大广播 |
| 并发 AI 房间 | P2 | 单实例 uvicorn `--workers 1`，AI 计算在线程池；多房间并发受 CPU 限制 |
| 大棋谱导入 | P3 | Web 已限 10MB；离线同限；服务器模式 JSON 解析需关注 |
| 兼容性 | P3 | Android 22 条 API/弃用警告；`usesCleartextTraffic` 明文；低配设备渲染（A-06） |

---

# 第四部分：v1.4.0 全套可交付产物清单 + 各端打包/部署操作步骤

## 4.1 交付产物清单（`release/v1.4.0-delivery/`）

```
release/v1.4.0-delivery/
├── SHA256SUMS.txt            # 全部产物哈希校验
├── package.json              # web 包元数据（version 1.4.0）✅
├── pyproject.toml            # Python 包（version 1.4.0）✅
├── requirements.txt          # 依赖入口
├── android/                  # 签名 APK（Release，依赖项目 keystore）
├── desktop/                  # Windows EXE（PyInstaller 产物）
├── docker/                   # FastAPI/Docker 部署文件
├── docs/                     # 操作文档 + QA 报告
├── locales/                  # zh-CN.json / en.json
├── packaging/                # 构建脚本（build_windows/android/web_release）
├── requirements/             # core/server/desktop/dev.txt
├── src/                      # 完整源码（冻结 1.4.0）✅
├── tests/                    # 13 个 pytest 模块（91 passed 对应）
└── web/                      # 静态前端包
```

> ⚠️ 该交付包内部版本为 **1.4.0**；与当前工作树 **1.5.0** 不一致（见 0 节）。若以 1.4.0 发布，需确认此冻结包即最终产物；若以 1.5.0 发布，应重新构建交付包。

## 4.2 各端打包 / 部署完整操作步骤

### 4.2.1 Windows 桌面 EXE
```powershell
cd xionghan-chess-next
.\.venv\Scripts\Activate.ps1            # 或直接使用 .venv/Scripts/python.exe
pip install -r requirements/desktop.txt
pyinstaller packaging/xionghan_chess.spec   # 生成 dist/ 下 EXE
# 校验：.\dist\xionghan-chess\*.exe 可启动，运行 build_windows.ps1 亦可
```

### 4.2.2 Web 静态前端包
```powershell
cd xionghan-chess-next
node --check web/js/app.js && node --check web/js/i18n.js   # 语法检查
pwsh packaging/build_web_release.ps1    # 产出 Web ZIP（含 9 张头像/共享头像模块）
```

### 4.2.3 Android 签名 APK
```powershell
#  prerequisites: .NET 9 SDK + Android workload + Android SDK
dotnet build android/XionghanChessAndroid.csproj -c Release -f net9.0-android
# 签名：使用项目 keystore（生产 APK 签名仍依赖项目 keystore，本地构建为可安装 Release APK）
# 见 android/BUILD_REQUIREMENTS.md
```

### 4.2.4 Docker / 服务端部署
```bash
cd xionghan-chess-next
cp deploy/.env.example deploy/.env          # .env.example 存在（105 B）✅
docker compose --env-file deploy/.env -f deploy/docker-compose.yml build
docker compose --env-file deploy/.env -f deploy/docker-compose.yml up -d
docker compose --env-file deploy/.env -f deploy/docker-compose.yml logs -f
# 默认 http://服务器IP:8000 ；公网部署需反向代理允许 WebSocket Upgrade 并提供 HTTPS
# 多副本前需增加 Redis 房间存储（当前单实例内存房间）
```

### 4.2.5 运行（开发）
```powershell
pwsh scripts/run_server.ps1     # 启动 FastAPI/uvicorn
pwsh scripts/run_desktop.ps1    # 启动 PySide6 桌面端
```

## 4.3 操作命令速查

| 动作 | 命令 |
|---|---|
| 跑测试 | `.venv/Scripts/python.exe -m pytest -q` |
| JS 检查 | `node --check web/js/app.js web/js/i18n.js` |
| 编译检查 | `python -m compileall -q src` |
| 健康检查 | `GET /api/health` → `{"status":"ok","version":"1.4.0"}` |

---

# 第五部分：最终版本上线验收结论与遗留风险汇总

## 5.1 上线验收结论

**P0 阻断级**：✅ **0 项**（v1.3.0 的 5 条严重 + 4 条高优缺陷均已修复或确认为架构限制/非阻断；v1.4.0 二次审计 47 条复核无 P0 残留）。

**P1 高优级**：⚠️ **2 项需决策/收尾**：
1. **版本标识碎片化**（1.4.0 / 1.5.0 / 2.0.1 共存，docker 标 1.5.0）→ 必须统一后发布。
2. **安卓离线 `no_progress_draw` 规则分歧**（vs Python Core）→ 建议升 P1 修复或明确为已知限制并公告。

**新功能落地**：✅ **9/9 全部落地**（见 2.3）。

**三端核心一致性**：✅ 桌面/Web/安卓服务器一致；离线受架构限制缺 AI/联机/复盘，属设计边界。

**测试**：✅ pytest **91 passed**（v1.4.0 交付快照），JS/JSON/compileall/git-diff 全通过；Android Release 0 错误。

**部署脚本**：✅ Windows EXE / Web ZIP / Android APK / Docker 四套构建链路均可执行（需在具备 Docker CLI / .NET9 / PyInstaller 的环境运行）。

> **总体判定**：v1.4.0 交付包**满足自动化验收条件、无 P0 阻断**；但因工作树已前进至 1.5.0，建议以 **1.5.0 作为实际发布版本**（其 92 passed 与三件套文档已就绪），将本审计的 P1 项并入 1.5.0 收尾。详见 0 节 A/B 选项。

## 5.2 遗留风险登记（R 系列）

| 编号 | 等级 | 风险 | 关联 | 建议处理 |
|---|---|---|---|---|
| **R-01** | **P1** | 版本标识碎片化（1.4.0/1.5.0/2.0.1，docker 标 1.5.0） | 0 节, 2.6 | 发布前统一为单一版本号；`index.html` 的 `app.js?v=2.0.1` 改为与包版本一致 |
| **R-02** | **P1** | 安卓离线 `no_progress_draw` 与 Python Core 分歧 | 2.2.2 | 离线 `settle()` 补实现，或公告为已知限制 |
| R-03 | P2 | 广播放大（replay 最多 512 快照全量推送） | 2.4 | 大房间分页/增量快照推送 |
| R-04 | P2 | 战术走法爆炸（多 ARMOR/ASSASSIN） | C-06 | 位置裁剪 |
| R-05 | P2 | 明文鉴权头 / Android 明文 HTTP（A-08） | 2.5 | 强制 HTTPS 反向代理；生产关 cleartext |
| R-06 | P3 | Web 硬编码中文文案绕过 i18n | 2.6 | 抽取为 locale 键 |
| R-07 | P3 | 文档 81 vs 91 passed 矛盾 + Android 页措辞过时 | 2.6 | 修正 DELIVERY_1.4.0.md |
| R-08 | P3 | 仓库卫生：历史 APK 被跟踪 / build/dist 残留 / 重复 spec / QA 截图 | 1.4 | git rm --cached + .gitignore + 清理 |
| R-09 | P3 | 衍生 NEW-01/02 逻辑瑕疵 | 2.8 | 随规则确认一并修 |
| R-10 | ⏸ | 规则待确认 C-01/03/04/11/12 | 2.9 | 产品拍板后修改 |

## 5.3 行动项清单（按优先级）

| 优先级 | 行动 |
|---|---|
| **P0（发布前必须）** | 无阻断项；但需先解决版本走向（0 节 A/B） |
| **P1** | 1) 统一版本号（R-01）；2) 决策安卓离线 `no_progress_draw`（R-02） |
| **P2** | 广播/AI 性能优化（R-03/04）、安全加固 HTTPS（R-05） |
| **P3** | i18n 补全（R-06）、文档修正（R-07）、仓库清理（R-08）、衍生缺陷（R-09） |
| **待确认** | 规则问题 C-01/03/04/11/12（R-10） |

---

> **交付物索引**：本报告为 `docs/AUDIT_v1.4.0_full.md`；配套依据：`docs/QA_v1.3.0.md`（47 条 + 二次审计）、`docs/QA_REPORT_1.4.0.md`、`docs/DELIVERY_1.4.0.md`、`docs/GAP_ANALYSIS_vs_legacy.md`、`release/v1.4.0-delivery/`。
>
> **审计师签字**：资深跨端棋牌全栈工程审计 & 交付工程师 ｜ 基准日 2026-08-16
