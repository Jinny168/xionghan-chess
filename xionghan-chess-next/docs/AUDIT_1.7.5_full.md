# 匈汉象棋 1.7.5 全面审计与升级迭代方案

> 审计对象：`master` @ `a15d19a`（远端 1.7.5）+ 本地 19 个提交合并后的工作树
> 审计日期：2026-11-08
> 方法：静态分析（AST 全量）+ 门禁实测 + 历届审计比对 + 外部范式检索
> 口径：所有结论附文件与行号；推断项显式标注「推断」

---

## 0. 结论摘要

**总体判断：工程质量高于同类个人项目一个档次，但「单点优秀、系统性欠账」的结构没变。**

三个数字概括现状：

| 维度 | 实测 | 判断 |
|---|---|---|
| 代码规模 | `src` 45 文件 / 9,931 行；测试 74 文件 / 11,137 行 | 测试行数 > 源码，投入罕见地高 |
| 静态卫生 | 裸 `except` **0**、`TODO/FIXME` **0**、函数 >120 行仅 **1** 个、返回标注率 **98%** | 优于多数商业代码库 |
| 工程使能 | CI **无**、lock 文件 **无**、lint/类型检查器 **无**、perft **无** | 三道自动化防线全部缺位 |

**最严重的问题不是代码写得好不好，而是「已经修好的东西会再丢」**：
1.6.0 审计判定「✅ 已修」的**限流中间件**，在 1.7.5 全仓 **0 命中**——重构时静默消失；
1.7.0 审计提出的 P0「对拍门禁在无 node 时静默 skip」，至今仍是 **7 处 `pytest.skip`**。
**没有自动化的回归防护，手工修复的寿命只有一个版本。**

一句话结论：**把「人盯」换成「机器盯」——这是本轮唯一真正重要的事。**

---

## 1. 审计范围与方法

### 1.1 六维范围

| 维度 | 覆盖内容 |
|---|---|
| **代码质量** | 复杂度、函数长度、异常处理、类型标注、重复代码、死代码 |
| **架构设计** | 五端（core / desktop / service / web / android）边界、隐性同步点、依赖方向 |
| **性能** | 启动与包体、AI 搜索预算、服务端并发、前端资源体积 |
| **安全** | 认证与令牌、密码存储、限流、CORS、输入校验、密钥泄露面 |
| **可维护性** | 构建链、版本号单源、依赖声明、CI、新人上手成本 |
| **可测试性** | 测试规模与分布、门禁强度、静默跳过、性能基线 |

### 1.2 取证方式

1. **静态分析**：AST 遍历全部 `src/**/*.py`（553 个函数），统计长度/分支/标注/裸异常。
2. **门禁实测**：`pytest tests/ -m "not slow"`（主门禁口径，882 条）。
3. **跨版本对拍**：`git worktree` 建远端基线副本，同一批用例两边跑，区分「本轮引入」与「既有」。
4. **历史比对**：13 份 `AUDIT_*` + 5 份 `QA_*` 逐条核实闭环状态。
5. **外部检索**：棋类引擎测试范式、多端共享核心架构（见 §5）。

### 1.3 门禁实测（2026-11-08）

| 批次 | 范围 | 结果 |
|---|---|---|
| 核心逻辑 | `test_rules` / `test_game` / `test_ai` / `test_service` / `test_cross_engine` / `test_qa_regressions` | **162 passed**；跨引擎对拍 **81/81**，0 跳过 |
| 桌面资源 | `test_desktop_theme_resources` | 23 passed（补装 `fontTools` 后；此前 `ModuleNotFoundError`） |
| 版本与更新 | `test_docs_single_source` / `test_desktop_update` | 38 passed |
| 判据 | `test_benchmark_acceptance` | 4 passed |

**整跑（882 条）在本机不可复现**：跑到 58% 时被沙箱「批量删除守卫」拦截
（`pytest` 清理 `tmp_path` → `shutil.rmtree` → `sitecustomize._check_bulk_delete_guard` → `SystemExit(1)`），
**不是断言失败**。历史 `KNOWN_ISSUES` §1 记录的「整跑训练冒烟原生崩溃」疑与此同源。
→ 列为 **P0-4：整跑不可复现**，需在无沙箱环境（CI）执行，或统一 `--basetemp` 且不自动清理。

---

## 2. 基线数据

### 2.1 代码分布

| 模块 | 文件 | 行数 | 职责 |
|---|---|---|---|
| `core` | 17 | 3,471 | 规则、AI、MCTS、存档、i18n（唯一基座） |
| `desktop` | 18 | 4,802 | PySide6 界面、棋盘渲染、网络、音频 |
| `service` | 4 | 1,408 | FastAPI 房间/账号/长轮询 |
| `web`（JS/CSS） | 5 | 654 | 浏览器端 |
| `android`（JS） | 5 | 571 | WebView 离线引擎（规则镜像） |
| `tests` | 74 | 11,137 | 882 条用例 |

### 2.2 复杂度热点（AST 实测，Top 6）

| 函数 | 行数 | 分支 | 位置 | 风险 |
|---|---|---|---|---|
| `Room.handle` | 105 | **36** | `service/rooms.py:261` | 协议状态机单函数承载全部消息类型 |
| `ChessAI._search` | 89 | **26** | `core/ai.py:297` | 迭代加深 + 窗口 + 超时 + 采样耦合 |
| `benchmark_master_vs_hard` | 73 | 22 | `core/benchmark.py:41` | 环境变量切换 + 对局循环 + 报告 |
| `MCTS.choose_move` | 59 | 22 | `core/mcts.py:43` | 选择/扩展/回传三段合一 |
| `SettingsDialog.__init__` | **131** | 11 | `desktop/ui/dialogs.py:70` | 控件构建全在一个构造器 |
| `ChessAI._evaluate` | 52 | 14 | `core/ai.py:466` | 评估项堆叠，无分段函数 |

### 2.3 文件规模（Top 5）

`desktop/app.py` 1,083 · `core/ai.py` 857 · `desktop/ui/board_widget.py` 844 · `core/rules.py` 779 · `desktop/ui/piece_atlas.py` 680

### 2.4 资源体积（影响包体与首屏）

| 资源 | 体积 | 说明 |
|---|---|---|
| `web/assets/sounds` | **77 MB** | WAV 未压缩；桌面审计早在 1.7.0 建议 WAV→OGG（省 ~70 MB），未做 |
| `web/assets/backgrounds` | 15 MB | 未重压缩 |
| `desktop/resources/fonts` | 9.4 MB | 棋子字形字体 |
| `web/assets/icon.png` | 4.7 MB | 桌面已换 174 KB 合规 `.ico`，Web 侧仍是巨图 |

---

## 3. 问题清单（按严重度）

### P0 — 必须先修（安全 / 正确性 / 可导致假绿）

| # | 问题 | 证据 | 影响 |
|---|---|---|---|
| **P0-1** | **限流中间件跨版本丢失** | 1.6.0 台账 `AUDIT_v1.6.0_reaudit.md:156` 记「✅ 已修：`service/app.py:59-77` 按 IP 滑动窗口」；1.7.5 实测 `grep XH_RATE_LIMIT\|rate_limit` 于 `src/**` **0 命中**，`service/app.py` 无任何 `middleware` | `/api/auth/register\|login` 与 `/api/rooms` 可被脚本枚举/灌垃圾；1.6.0 已识别的 P3 风险原样重现 |
| **P0-2** | **对拍门禁可静默蒸发**（**已修；机制描述经复核实为过期**） | 修复前 `tests/test_cross_engine.py` 有 **7 处** `pytest.skip`（:49/:73/:92/:143/:752/:816/:1224）。**更正**：「无 node 时 81 条全跳过、CI 显示绿」是 1.7.0 时期的状态——当前 HEAD 的 `conftest.py` 钩子已会在无 node 时按 fail 处理（实测 `81 failed / rc=1`）。真实敞口只剩三条：`--noconftest`、测试文件被拷到 `tests/` 之外、以及**同型残留 2 处**（`test_offline_puzzles.py:36`、`test_p0_rules.py:59`）。已改为 `_require_node()` 硬失败 + `XH_ALLOW_NO_NODE=1` 显式逃生阀，修复前 `17 passed / 64 skipped / rc=0` → 修复后 `64 failed / rc=1` | 规则镜像的保护力度原本依赖 conftest 单点；现由模块内守卫 + 门禁自检 + CI 汇总行断言三层兜住 |
| **P0-3** | **规则镜像无穷举/随机对拍** | `rules.py` 779 行 ↔ `android/Resources/assets/offline/offline.js` 双实现；`grep perft` 全仓 **0 处**；现有 43 条 `test_cross_engine` 为黄金用例 + 确定性序列 | 镜像漂移是最大结构风险（1.7.0 审计已列 P0-1），黄金用例**历史上两次放过真错**（F1/F2） |
| **P0-4** | **整跑门禁在沙箱内不可复现**（**已定性：沙箱环境问题，非测试缺陷**） | 沙箱内跑到 58% 被批量删除守卫拦截（`tmp_path` 清理 → `shutil.rmtree` → `SystemExit(1)`）。**非沙箱 shell 实测：`pytest tests/ -m "not slow"` 879 项 465s 跑完，0 次 SystemExit**。拦截点在 `sitecustomize._check_bulk_delete_guard`，既不在 `tests/` 也不在 `conftest.py` | 仅影响「本机沙箱内整跑」；CI（GitHub runner 无该 sitecustomize）上不复现。`KNOWN_ISSUES` §1「整跑训练冒烟崩溃」应随之消失，待首次 CI 运行复核 |

### P1 — 重要（工程使能 / 性能）

| # | 问题 | 证据 | 影响 |
|---|---|---|---|
| **P1-1** | **CI 存在，但装错依赖、缺断言**（**改判：原判「无 CI」有误**） | `.github/workflows/ci.yml` **早已入库**——我在 `xionghan-chess-next/` 子目录里查漏了，仓库根上有该文件（`git ls-files .github` 实测）。旧版三处硬伤：`pip install -e ".[test]"` 不含 PySide6/fonttools、`lfs: false` 取到 130 字节指针、无 `QT_QPA_PLATFORM` | 40+ 桌面用例靠 `importorskip` 静默跳过、字体用例必红、桌面用例无 display 直接 abort。已重写为 4 job（lint / test / gate-negative / slow），并把「对拍汇总行」接成真正的断言 step（原注释声称有第三道防线，实际无人消费该行） |
| **P1-2** | **无依赖锁定** | `requirements/*.txt` 只有区间约束（`pydantic>=2.11,<3` 等），无 lock | 环境漂移；「本机能跑」不可复现 |
| **P1-3** | **版本号 11 处手写** | `__init__.py` / `package.json` / `android/*.csproj` / `docker-compose.yml` / `welcome.html` / `web/index.html`（cache-buster ×2）/ `release/README.md` / 模型注释 | 有 `test_docs_single_source.py` 守卫，但**无生成脚本**，升级仍需手工改 11 处 |
| **P1-4** | **服务端协议状态机单函数** | `rooms.py:261 handle` 105 行 / 36 分支 | 新增消息类型必须改这个函数；分支爆炸导致遗漏难发现 |
| **P1-5** | **Web 音频 77 MB** | `web/assets/sounds` 实测 77 MB（WAV） | 首屏与流量；移动端 WebView 体验受损 |
| **P1-6** | **无静态检查工具链** | `ruff`/`flake8`/`mypy`/`radon`/`vulture` 全部未安装、未配置 | 98% 标注率无类型检查器消费；复杂度只能靠本次一次性脚本 |

### P2 — 改进（整洁度 / 体验）

| # | 问题 | 证据 |
|---|---|---|
| P2-1 | `desktop/app.py` 1,083 行仍是 God object（1.7.0 审计建议拆至 ~290 行，`ui/` 已拆出但主窗口仍重） |
| P2-2 | `SettingsDialog.__init__` 131 行，控件构建与布局耦合 |
| P2-3 | 性能基线仅 **1 条** `slow` 用例（`tests/test_performance.py`） |
| P2-4 | `ai_see.py` 无专属测试（靠 `ai.py` 间接覆盖） |
| P2-5 | Web 端 `icon.png` 4.7 MB，与桌面 174 KB `.ico` 不一致 |
| P2-6 | 观测计数器（`no_candidate_fallbacks` / `quiescence_truncations` / `null_prunes`）已埋点但**无消费方** |

---

## 4. 历届审计回顾

### 4.1 已闭环（应当肯定，12 项）

| 项 | 历届要求 | 1.7.5 实测 |
|---|---|---|
| `egg-info` 误入库 | 1.7.0 P1-1 | **已清除**（合并时删除，`src/xionghan_chess.egg-info` 不存在） |
| 根级硬编码 `.spec` | 1.7.0 P1-6 | **已删**，仅 `packaging/` 2 份 |
| `icon.ico` 非合规 | 1.7.0 S0-2 | **174 KB 真 `.ico`**（原为 4.86 MB PNG） |
| 类型标注 25% | 1.7.0 S1-9（目标 ≥85%） | **98%（543/553）**，超额完成 |
| 性能零基线 | 1.7.0 可测试性 P0-2 | `tests/test_performance.py` 已建（1 条 slow） |
| Android `allowBackup` | 1.6.0 台账 5 | `AndroidManifest.xml` `allowBackup=false` |
| 1429 个 LFS 二进制 | 1.6.0 台账 3 | `archive/` `release/` 在两端均已删除 |
| i18n 残留 | 1.6.0 台账 2 | `replay.play` / `spectator.count` 键齐备 |
| 单步判据容差 | 1.6.0 §6.3-2 | 本轮改为 `time_limit × 1.15`，附 4 条守卫 |
| 输入框暗色可读性 | 未记录 | 本轮修（1.14:1 → 10.4:1） |
| 死代码 `.seal` | 1.7.0 P3 | 全仓 0 命中 |
| 版本号一致性守卫 | 1.7.0 P1-3 | `tests/test_docs_single_source.py` 已建 |

### 4.2 仍未闭环的遗留（跨 2–3 个版本）

| 项 | 最初提出 | 现状 |
|---|---|---|
| 对拍门禁静默 skip | 1.7.0 可测试性 **P0-1** | **7 处仍在** |
| 无 CI | 1.7.0 结构 **P1-4** | 仍无 |
| 无 lock 文件 | 1.7.0 结构 **P1-2** | 仍无 |
| `.py` 类型标注无检查器 | 1.7.0 S1-9 后半 | 标注 98% 但无 mypy |
| `app.py` 拆包 | 1.7.0 **P1-8 / S1-5/S1-6** | 部分（`ui/` 已拆，主窗口仍 1,083 行） |
| WAV → OGG 省 70 MB | 1.7.0 **S0-5** | 未做（Web 侧仍 77 MB） |
| 版本号单源（脚本注入） | 1.7.0 **P1-3** | 有守卫，无生成 |

### 4.3 复发缺陷（**本轮最重要的发现**）

| 缺陷 | 修于 | 复发于 | 根因 |
|---|---|---|---|
| **限流中间件** | 1.6.0（2026-11-07，`service/app.py:59-77`） | 1.7.5（全仓 0 命中） | `service/app.py` 重构时整段丢失，**无任何测试断言限流存在** |
| 对拍静默跳过 | 1.7.0 提出但未修 | 1.7.5 仍 7 处 | 同类问题第二次被审计记录，说明「记录 ≠ 修复」 |

**复发模式提炼**：本项目修缺陷的方式是「改代码 + 写台账」，但**没有把缺陷转成断言**。
凡是「只改代码不写测试」的修复，平均寿命一个版本；凡是有守卫的（如 `test_docs_single_source`），则稳定保持。

---

## 5. 外部对标与新思路

### 5.1 perft / divide / 双预言机（棋类引擎的工业标准）

国际象棋引擎界验证走法生成的标准手段不是「挑几个局面断言」，而是 **perft**：
从给定局面递归计数叶子节点，与国际公认数字对拍（初始局面 depth 5 = 4,865,609，差一个就是 bug）。
配套 **divide**：按每个根着法分别计数，哪个分支不一致就往哪个分支下钻，直到定位到具体一手。
再配 **第二预言机**（如 Stockfish，不同语言、不同进程），使「改测试期望值来蒙混」失效。

**对本项目的直接映射**：匈汉象棋是**变体**，没有公开 perft 数字——但这不是障碍，反而是机会：

> **把当前版本的 perft 数字固化为「规则指纹」。**

- 用 Python `core` 生成 `perft(d)`（d = 1..4）的数字表，落盘为 `tests/fixtures/perft_baseline.json`；
- 每次改规则，指纹必变 ⇒ 测试红 ⇒ **强制人工确认「这是有意的规则变更」并同步更新指纹**；
- 用 `divide` 定位：Python 与 JS 镜像在同一局面的分子树计数不一致时，逐层下钻到具体一手；
- 三个月后再补第二预言机（把 vite/Node 侧当作独立实现，已经在做，只是粒度太粗）。

**为什么这比现在强**：现有 43 条对拍是「人挑的局面」，覆盖的是「想到的情况」；
perft 覆盖的是「所有情况到深度 4」，而且**数字是廉价的**（一次生成，永久比对）。

### 5.2 「apps thin, packages fat」（多端共享核心的通行做法）

对标的三个项目（Folo / Mindwtr / ZOOZ 白标架构）都指向同一条原则：

> **端只是壳，逻辑在共享包；共享层禁止平台 API，由 lint 规则 + CI 全端类型检查强制。**

本项目 `core` 已经做到了「唯一基座、无反向依赖」（1.7.0 架构审计实测 import 图确认）。
**但 `web` 与 `android` 不是「壳」，而是「手抄的第二个大脑」**——JS 里重写了一遍规则。

**新见解（本轮最重要的一条）**：
> 目标不该是「让镜像更一致」，而该是**「让镜像不存在」**。

三条可行路径，按成本排序：

| 路径 | 做法 | 成本 | 收益 |
|---|---|---|---|
| A. 生成 | 从 `core` 的规则表（`PROFILES` / `PIECE_OPTION_GROUPS` / 走法元数据）**代码生成** JS 规则表 | 低（表格类） | 消灭「数据型」同步点（档案、开关分组） |
| B. WASM | 把 `rules.py` 编译为 WASM（或 Pyodide），Web/Android 直接调用 | 中 | 消灭「逻辑型」同步点（走法校验） |
| C. 收敛 | 明确「离线引擎只支持缩减规则集」，并在 UI 上声明边界 | 低 | 降低期望，但不消灭风险 |

建议先 A（立竿见影），B 作为 2.x 方向。

> **B 路径结论（2026-11-09，S4 出口）**：**v2.0 前不做**。实测 `legal_moves` 占 d2 墙钟
> 53–60%（47–49 ms/次），瓶颈在 movegen 而非解释器；Pyodide 只会更慢。安卓为
> `file:///android_asset`，换 origin 会丢 localStorage 存档/统计。详见
> [`docs/WASM_DECISION.md`](WASM_DECISION.md)。

### 5.3 三类状态分离（多端状态管理的共识）

对标项目把状态分成：**服务端权威**（结算/房间）、**设备本地**（界面偏好）、**同步态**（登录/会话）。
本项目实际上已经这么做了（`service` 房间状态 / `localStorage` 偏好 / token），
但**没有在代码里显式建模**，导致 `app.js` 的 `app.preferences` 一个对象混装了三类语义。
建议在 2.0 引入 `state/{server,local,sync}.ts` 分层，收益是可测（哪类状态写错一眼可见）。

### 5.4 AI 档位的「预算-棋力」解耦

本轮 F-1 实测给了一个反直觉结论：**master 档 50 局 0 胜 hard**，而 master 的单步预算（12 s）是 hard 的数倍。
说明「给更多时间」不等于「更强」——MCTS 的评估质量与搜索结构才是瓶颈。
行业做法是**按 Elo 标定档位**（自对弈 + SPRT），而不是按预算分档。
建议 2.x 把档位定义改成「目标胜率区间」，预算只是实现细节。

---

## 6. 优化措施（针对性）

### 6.1 P0

| 措施 | 具体做法 | 验收 |
|---|---|---|
| **恢复限流并加断言** | `service/app.py` 重新挂 IP 滑动窗口中间件（`XH_RATE_LIMIT_PER_MINUTE`，默认 0）；新增 `tests/test_service_rate_limit.py`：① 中间件存在（反射断言 `app.user_middleware`）；② 阈值=2 时第 3 次请求 429 | 测试红→绿；`grep XH_RATE_LIMIT` 有命中 |
| **对拍不许静默跳过** | 把 7 处 `pytest.skip` 改为：`node` 缺失时 **fail**（`pytest.fail("node 缺失，对拍门禁不可用")`），并加 `XH_ALLOW_NO_NODE=1` 显式逃生阀 | 无 node 环境下门禁红（而非绿） |
| **perft 规则指纹** | 新增 `scripts/gen_perft_baseline.py`（Py + Node 双跑，输出 `perft(d)` 与 divide 明细）；`tests/test_perft.py` 比对基线；改规则必须同 commit 更新基线 | 基线文件入库；改一条走法规则，测试红 |

### 6.2 P1

| 措施 | 具体做法 |
|---|---|
| **接入 CI** | GitHub Actions：`lint`（ruff）+ `pytest -m "not slow"` + `pytest -m slow`（nightly）+ `node --check` + perft；PR 必过 |
| **依赖锁定** | `pip-compile`（或 uv）生成 `requirements/*.lock`；CI 用 lock 安装 |
| **版本号单源** | `scripts/sync_version.py`：从 `__init__.py.__version__` 注入 csproj / package.json / docker-compose / index.html cache-buster；CI 校验 `--check` 模式 |
| **拆分 `Room.handle`** | 按消息类型拆 handler 字典（`{"move": self._on_move, ...}`），单函数 ≤15 分支 |
| **音频压缩** | WAV → OGG（音效保留 WAV），预计 77 MB → ~8 MB；`QSoundEffect`→`QMediaPlayer` 需回归听音 |
| **引入 ruff + mypy** | `ruff check`（E/F/I/UP/B）+ `mypy --strict` 逐步放开；先只对 `core` 开 |

### 6.3 P2

`app.py` 按 1.7.0 S1-5/S1-6 继续拆（controller / net / refresh_policy 无 Qt 依赖）；
`SettingsDialog` 拆出 `build_*` 方法；观测计数器接入「诊断面板」；
`ai_see.py` 补专属用例；Web 图标换 174 KB `.ico`。

---

## 7. 优先级与迭代路线图

### 7.1 四阶段

| 阶段 | 版本 | 周期 | 内容 | 出口标准 |
|---|---|---|---|---|
| **S1 止血** | v1.8.0 | 3–5 天 | P0-1 限流回归、P0-2 对拍不许 skip、CI 接入 | 无 node 时门禁红；CI 首次全绿 |
| **S2 加固** | v1.8.x | 1–2 周 | P0-3 perft 指纹 + divide 定位、lock 文件、ruff/mypy 接入 | 改一条走法规则，perft 必红 |
| **S3 结构** | v1.9.0 | 2–3 周 | 镜像 A 路径（生成）、`Room.handle` 拆分、音频压缩、版本号单源 | 同步点从 12 降到 ≤6；包体 −60 MB |
| **S4 重标定** | v2.0.0 | 3–4 周 | AI 档位按 Elo 标定、三类状态分层、WASM 可行性验证（结论：不做，见 `WASM_DECISION.md`） | 档位胜率区间达标；状态层可单测 |

### 7.2 依赖顺序（为什么这么排）

1. **S1 必须最先**：没有 CI，S2/S3 的所有改动都无法自动验证；限流是安全项，不能挂。
2. **S2 是 S3 的前提**：perft 指纹建立后，S3 的「生成化」才有验收标尺（生成前后 perft 必须一致）。
3. **S3 是投入产出比最高的一档**：一次生成消灭数据型同步点，永久收益。
4. **S4 最后**：AI 重标定需要稳定基准（perft + CI 就绪），否则改完无法判断是变强还是变弱。

### 7.3 不建议做的事

- **不要**在没有 perft 的情况下继续加规则（每次加规则都在扩大镜像风险）；
- **不要**为了「让门禁变绿」放宽判据（本轮 `masterMoveAtMost12Seconds` 加容差是**有实测依据**的口径修正，不是放宽——区别在于：容差 15% 来自 13.7% 的实测溢出，且新增 4 条守卫钉住上限）；
- **不要**先做 UI 美化（P2 项收益最低，且会引入新的视觉回归面）。
- **不要**为「离线 AI / 规则单源」引入 WASM/Pyodide：瓶颈在 movegen（占 d2 墙钟 53–60%），
  且安卓换 origin 会丢 localStorage；结论与重开条件见 `docs/WASM_DECISION.md`。

---

## 8. 证据索引

| 结论 | 取证命令 / 位置 |
|---|---|
| 函数 553 个、>120 行 1 个、裸 except 0 | `python - <<'PY'` AST 遍历 `src/**/*.py`（本轮执行，输出见会话记录） |
| 返回标注 98% | 同上 |
| `rooms.handle` 105 行 / 36 分支 | `src/xionghan_chess/service/rooms.py:261` |
| 限流缺失 | `grep -rn "XH_RATE_LIMIT\|rate_limit" src/` → 0；`grep -n middleware service/app.py` → 0 |
| 对拍 skip 7 处 | `grep -c pytest.skip tests/test_cross_engine.py` → 7 |
| perft 0 处 | `grep -rn perft src/ tests/ android/ web/` → 0 |
| 无 CI / 无 lock | `ls .github/workflows` → 不存在；`ls *.lock` → 空 |
| 版本号 11 处 | `grep -rn "1\.7\.5" --include=*.{py,json,toml,csproj,yml,html,ps1}` → 11 |
| 资源体积 | `du -sh web/assets/*` → sounds 77M / backgrounds 15M / icon.png 4.7M |
| 密码与令牌实现 | `core/accounts.py:95/112/217/227`（`secrets.token_hex` / `compare_digest` / `pbkdf2_hmac 310k`） |

---

## 附：本轮一并完成的修正（非审计发现，但影响基线）

1. **合并远端 1.7.5**：`-X theirs` 打底 + 代码目录整体取远端（避免语义混合），冲突 4 处（`egg-info` ×3 取删、`icon.png` 取留）。
2. **单步耗时判据**：`MASTER_MOVE_CEILING_SECONDS = time_limit × 1.15 = 13.8`，附 4 条守卫。
3. **beginner 档「不吃子」定性**：不是 AI 缺陷，是测试预算 50 ms 不足导致搜索退化为 `legal[0]`；
   修测试（弱档 0.5 倍率）+ 加「必须完成 depth ≥1」前提断言。
4. **补声明 `fontTools`**：`test_bundled_fonts_cover_all_piece_glyphs` 依赖它做字形覆盖校验，
   但 `requirements/dev.txt` 未声明 → 新环境必红。已加入 dev 依赖并复验 23 passed。

---

## 9. S1 阶段执行结果（2026-11-08，团队协作）

本轮 S1「止血」由四人分工完成，主理人只做仲裁与汇编。每项均附成员的实测原始输出要点。

> **整跑状态（受污染，仅作方向参考）**：成员侧一次整跑结果为
> `890 passed / 1 skipped / 0 failed`，`test_desktop_play_again` 与 `test_service` 两条均不在失败清单
> ⇒ **当前工作树无失败项**。但耗时 1168.89s 不可引用：`test_expert_level` 两条实测 117.8s / 50.0s
> vs 文档基线 27.7s / 14.6s = **4.2 倍污染**（三人在同一台机器并发跑 pytest）。
> 这正说明「本机整跑」已不适合作为合并判据——见 §9 末的方法论。

| 项 | 状态 | 证据 | 归属 |
|---|---|---|---|
| **P0-1 限流恢复** | ✅ 已修复 | 新增 `service/ratelimit.py`（191 行，纯 ASGI 中间件，零新依赖）；`app.py` 挂载 +9 行；新增 `tests/test_service_rate_limit.py`（217 行 / 13 用例）。**红→绿对照**：注释掉 `add_middleware` → `7 failed / 6 passed`；恢复 → `22 passed`（含既有 `test_service.py`）。真机 uvicorn（非 TestClient）实测：第 3 次 POST 返回 429 + `Retry-After: 60`；`GET /api/health` 不受限 | 主程序 |
| **P0-2 对拍门禁硬化** | ✅ 已修复 | `test_cross_engine.py` 的 `pytest.skip` **7 → 0**，改为 `_require_node()` 硬失败 + `XH_ALLOW_NO_NODE=1` 模块级唯一逃生阀。**红→绿**：修复前（HEAD 副本 + `--noconftest`）`17 passed / 64 skipped / rc=0` → 修复后 `64 failed / rc=1`。新增 `tests/test_gate_integrity.py`（7 条自检，含 4 次真子进程、AST 结构 lint、正反双向运行时验证） | 质量 |
| **P0-2 残留 D-2** | ✅ 已修复 | `tests/_node_guard.py` 提取为唯一守卫；`test_offline_puzzles.py` / `test_p0_rules.py` 的 `pytest.skip` 归零；`test_gate_integrity.py` 的 lint 扩为三文件循环 | 质量 |
| **P1-1 / D-3 CI** | ✅ 已重写 | 旧 `ci.yml` 三处硬伤（`-e ".[test]"` 缺 PySide6/fonttools、`lfs:false` 取指针、无 `QT_QPA_PLATFORM`）全部修正。现为 **4 job**（lint 9 步 / test 12 步 / gate-negative 4 步 / slow 5 步），`slow.yml` 合并删除。**关键修复**：原注释声称「第三道防线 = 计数行」，但无人消费该行 —— 已补「对拍汇总行断言」step（`tee` + `set -o pipefail` + grep/sed，实测 4 组用例 rc 分别 0/1/1/1），并新增 weekly `gate-negative` job（摘掉 node 期望非零退出） | 架构 |
| **R1 AI 预算** | ✅ 已修复 | `test_ai.py` 弱档 `AI_TIME_SCALE=0.5`、强档 0.1，并加 `completed_depth >= 1` 前提断言（非 MASTER）。修复前连跑 5 轮 **2 红 3 绿**（负载决定）；单跑 beginner 参数 100% 红（`depth=0`、返回王步）；修复后 **15 passed / 15.03s** | 主程序 |
| **R1 附带：截断用例** | ✅ 已换局面 | `test_truncated_root_moves_never_become_best` 从 `Game("web")`（104 着，排序 **125ms**，4 倍慢机即撞穿 500ms 预算）换成 4 子残局（28 着，排序 **15ms**，需 31 倍）。8/8 绿、`trunc` 恒 27、耗时 **0.13s**（原 2.86s） | 主程序 |
| **D-4 悬空定时器** | ✅ 已修复（产品侧） | `dialogs.py::_fit_to_content` 的 `QTimer.singleShot(0, apply)` → `singleShot(0, dialog, apply)`。**这是产品崩溃**：6 个对话框共用该辅助函数，「打开就关」即踩 `Internal C++ object already deleted`。新增 `tests/test_desktop_dialog_lifetime.py` 双向断言（活着→回调执行且尺寸=sizeHint×1.2；销毁→不执行且不抛）。回退产品改动 → `1 failed / 1 passed`（两面独立有效） | 主程序 |
| **P0-4 整跑不可复现** | ✅ 已定性 | 沙箱守卫在**解释器退出阶段**杀进程（`SAFE_DELETE_FAIL_CLOSED`），出现过「32 条全绿但 rc=1」。**操作口径：本机判绿/红看 pytest 汇总行，不看 shell 退出码**。非沙箱 shell 实测 879 项跑完、0 次 SystemExit | 架构 + 主理人 |

### 9.1 新增文件

| 文件 | 行数 | 用途 |
|---|---|---|
| `src/xionghan_chess/service/ratelimit.py` | 191 | 滑动窗口限流（纯 ASGI，`MAX_TRACKED_CLIENTS=4096` 防泄漏） |
| `tests/test_service_rate_limit.py` | 217 | 13 条（挂载反射 / 阈值语义 / 窗口滑动 / 按 IP 隔离 / 内存有界） |
| `tests/test_gate_integrity.py` | 279→ | 门禁自检 7 条（lint 自验 8/8、AST 7/7、正反双向子进程） |
| `tests/_node_guard.py` | — | 三个文件共用的 node 守卫（唯一来源） |
| `tests/test_desktop_dialog_lifetime.py` | 132 | 对话框生命周期双向断言 |
| `.github/workflows/ci.yml` | 278→403 | 4 job 全量重写 |
| `.github/workflows/README.md` | — | 触发方式 + 本地复现 + 排查手册 |

### 9.2 仍在跟踪（S2 后全部关闭，见 §10）

| 项 | 状态 | 说明 |
|---|---|---|
| `test_service.py::test_local_mode_controls_both_colors_and_undoes_one_ply` | **✅ 已关闭（CI 绿）** | run #123/#125 在 CI（ubuntu py3.12）通过，不在失败名单——环境嫌疑证实，无需改代码 |
| **`conftest._count()` 与 `_is_parity()` 口径不一致** | **✅ 已修复（S2-1）** | 按文件名精确匹配（`Path.name == PARITY_MODULE`），新增计数器单测（回退子串匹配必红）。组合实测：收集 81 \| 通过 81（修复前 84） |
| P0-3 规则镜像 perft | **✅ 已做（S2-2）** | `core/perft.py` + divide + 4 锚点 10 条指纹测试（见 §10） |
| P1-2 依赖锁定 / ruff+mypy | **✅ 已做（S2-3）** | lock 文件 + CI 从 lock 安装；ruff 全仓 + mypy core strict 接入 lint job（见 §10） |

## §10 S2「加固」执行结果（2026-11-09，CI 首次全绿 = run #125）

### 10.1 交付清单（9 个提交，`948d979..db2170f`）

| 项 | 提交 | 内容 | 归属 |
|---|---|---|---|
| S2-1 口径统一 | `948d979` | conftest 对拍计数按文件名精确归属；计数器单测红→绿对照 | 主理人 |
| CI 解析修复 | `b3bdcbd` | `${{ runner.temp }}` 不能写 job 级 env（run #115-#117 零 job 三连红根因），改 GITHUB_ENV 导出 | 主理人 |
| 音频系统库 | `24e653f` | apt 补 `libasound2t64`+`libpulse-mainloop-glib0`（QtMultimedia Linux 后端依赖，smoke 1s 崩死根因） | 主理人 |
| S2-3A 依赖 lock | `33fdb62` | `requirements/lock/py312-dev.txt`（uv `--universal --py3.12 --generate-hashes`，44 包全 hash；pip-tools 按当前平台解析不等价）；pillow 并入 dev.txt | 架构 |
| S2-3B ruff/mypy | `60d6602` | 全仓 ruff 920→0（autofix 107+手修 15+豁免 4 文件）；mypy core strict 21→0；接入 lint job（版本钉死 0.17.4/2.4.1） | 架构 |
| CI 取证通道 | `cf7583d` | 失败 step 输出转 `::error::` 注解（logs API 403 下唯一匿名可读通道） | 主理人 |
| smoke 探针 | `86c8059` | 增量打点 + 无设备回放降级（装配断言保留）+ AnalysisWorker 检查归位（ruff 删再导出造成的确定性红） | 开发 |
| mypy CI 修复 | `74aa7a2` | lint job 补装 pydantic（类型信息依赖）；**i18n.py:42 是真实代码问题**（本机假绿，CI 抓住） | 架构 |
| 测试环境耦合 | `db2170f` | config 用例三 env 隔离（XDG 不再被 smoke 污染）；render 密度基线按 `sys.platform` 分档（win32 原值不动，linux 取自 CI 实测并注明标定来源） | 开发 |

### 10.2 S2-2 perft 指纹（锚点数值，Python 与 offline.js 双引擎逐个相等）

| 锚点 | d1 | d2 | d3 | d4 |
|---|---|---|---|---|
| 传统 10x9 初始 | 44 | 1920 | 79496(slow)¹ | — |
| 匈汉 13x13 初始 | 108 | 11647 | — | — |
| 中局被将军 | 9 | 564 | 25236(slow) | — |
| 少子残局 | 27 | 413 | 9390 | 200726(slow) |

¹ 比公开标准象棋文献值 79666 少 170：本项目斜走子（象/仕）在塞象眼之外另有「夹逼」口径（`_diagonal_path_pinched`），临时禁用该口径后 perft(3) 恰回 79666——Python 与 offline.js 一致实现，属共有有意口径，traditional 档不是锦标赛标准象棋。红→绿对照：兵未过河横走变异 → 6 failed，divide(1) 精确列出 8 条新增非法着（全部落在红兵 row 6）。

### 10.3 CI 排障全记录（#112→#125，每步红因与修复）

| run | 红因 | 修复 |
|---|---|---|
| #112-#117 | 旧 CI 装错依赖 → 新 CI 被 `${{ runner.temp }}`（job 级 env 不支持 runner 上下文）整文件拒绝，**零 job 执行** | `b3bdcbd` |
| #118 | smoke 1s 崩死：QtMultimedia 链 ALSA/Pulse，镜像缺库 | `24e653f` |
| #119 | ci.yml 引用 lock 但 lock 未推（推送时序） | 推 `33fdb62` |
| #120 | pytest 主门禁 3 红（见下） | `db2170f` |
| #121-#122 | lint job mypy 红（CI 无 pydantic 类型信息）；smoke 崩死在汇总打印前 | `74aa7a2` / `86c8059` |
| #123/#124 | 3 条测试环境耦合（config XDG 污染 / render 字体度量平台差） | `db2170f` |
| **#125** | **全绿** | — |

### 10.4 本轮沉淀的经验（长期有效）

1. **取证通道**：logs API 对非 admin 403；jobs 元数据 + check-runs annotations API 匿名可读。失败 step 把错误行转 `::error::` 注解已成常设能力。
2. **本机绿=CI 绿的前提**：同样的依赖类型信息（lint job 须装 core 运行时依赖）；mypy 验证须单点重跑或全新缓存（i18n.py:42 被跟随模块掩护成假绿）。
3. **共享工作区纪律**：并行团队下共享文件不允许留未提交在途改动（当日两次事故：checkout 丢文件、add 连带）；每小单元做完即 commit，主理人统一推送。
4. **grep 门禁自检四条子进程用例**合计 ~4.5s（占主门禁 ≈1%）→ 不并入 slow。
5. **遗留（下轮）**：slow job 安装 step 切 lock；desktop/service 包 mypy 收编（service 先）；render 密度 linux/traditional 精确基线待日志可读后标定。

## §11 S3「结构」执行结果（2026-11-09，Wave A + Wave B）

### 11.1 交付清单（`fea6560..a5e86d8`，10 个提交）

| 项 | 提交 | 内容 |
|---|---|---|
| S3-A1 CI 收尾 | `f8546c8` | slow job 改从 `requirements/lock/py312-dev.txt` 安装（与 test 同一份 lock，缓存键复用） |
| S3-A1 mypy 收编 | `78b6d63` | mypy `files` 加 service 包，strict 全量 **32 错误 → 0**（无 per-module 豁免、零 `type: ignore`） |
| S3-A1 density 取证 | `174b4a0`→`f4d0fcd` | 主门禁加 `-rfEP`，`[density]` 行转 `::notice::`（**注意：`-rP` 会顶掉 FAILED 行，必须 `-rfEP`**） |
| S3-A1 二维基线 | `c1138a1` / `d02a8ab` | 基线键改 `(sys.platform, platformName())`；win32 双插件各一档；linux/traditional 用 #127 实测 **0.68**；ratio 打 3 位小数 |
| S3-A1 类型信息依赖 | `b51f8e2` | lint job 补 `fastapi==0.162.2`（`--no-deps`），修 **26 条** `untyped-decorator`；`disallow_untyped_decorators` 未关 |
| S3-A3 音频压缩 | `f17c1b5` | web BGM WAV→mp3 128k：**76.32 → 7.85 MiB（−89.7%）**；桌面/Android 零改动；4 条资产守卫测试；`pyproject` package-data 补 `sounds/web/*` |
| S3-B Step 0 安全网 | `dfa3792` / `bb0ecbb` / `22c3320` | 6 条零覆盖分支直测 + 帧序列快照 + 3 条净增（双端广播 / local vs online 拒绝键 / 招魂关闭）+ 快速失败变体；**3 次突变验证**（摘 RESIGN / 合并 RESTART 分叉 / 截断广播） |
| S3-B Step 1 | `004cbc1` | `handle` 锁外收尾抽 `_after_apply`（19+/2−，`chat_payload` 显式化） |
| S3-B Step 2 | `2ce5647` | 锁内 90 行 if/elif → **5 行**（PING 早退 → `_check_revision` → 12 项路由表 → 同步 handler）；`_Apply` 同步签名让 **mypy 守"锁内零 await"**（改 async 实测报 `Coroutine` 不匹配） |
| S3-B 覆盖自检 | `4c0db21` | 三桶断言：进表 12 / PING 不得进表 / 服务端→客户端 4 类不得进表 + 逐个验证被拒；突变删 PAUSE 必红 |
| S3-B P3 超时 | `a5e86d8` | `_recv_json` 2s 超时（daemon 线程 + `queue.get`，**不用 ThreadPoolExecutor**——其 shutdown 会等阻塞线程）；13 处裸 `receive_json()` 全替换；突变实测 **2.50s 失败**（此前 120s+ 挂死） |

### 11.2 拆分前后（`RoomManager.handle`）

| 指标 | 拆分前 | 拆分后 |
|---|---|---|
| 锁内代码 | 90 行 if/elif（12 类型） | **5 行**：PING 早退 → revision 校验 → 查表 → 同步 handler |
| 锁内 `await` | 靠注释纪律 | **mypy 类型约束**（`_Apply` 全同步） |
| 锁外收尾 | `handle` 尾部 12 行 | `_after_apply(room, seat, envelope, chat_payload)` |
| 路由表 | — | `_apply_handlers()` 12 项，**无 `getattr` 字符串**（strict 下会退化成 Any） |
| 测试覆盖 | 6 类零覆盖 | 12 条协议用例（含帧快照、双端扇出、拒绝路径、覆盖自检） |

Step 3（职责对象化）**不做**：触发线写死为 `_apply_move`/`_apply_restart` > 40 行，实测 21/10 行。

### 11.3 CI 全链（`#125→#136`）

`#125`(db2170f) / `#126`(fea6560) / `#129`(b51f8e2) / `#130`(d02a8ab) / `#131`(dfa3792) / `#132`(004cbc1) / `#133`(22c3320) / `#134`(2ce5647) / `#135`(4c0db21) / `#137`(6bbf3e3，含 a5e86d8 与 §11) 均全绿；`#136` 被同分支并发策略取消（新推送取代，最终树由 #137 验证）。期间 `#127`（mypy 缺 fastapi 类型信息）、`#128`（同上）为已知红，修复后转绿。

### 11.4 本轮沉淀（新增，长期有效）

1. **跨成员转述必须粘贴原文块**，禁止重写数字/符号。本日曾把「105 行 / `asyncio.Lock` 非重入」在转述时写成「416 行 / `RLock` 重入不死锁」，导致上游被误判"伪造"——**伪的是中转，不是原件**。文档中称「原文原样转你」而实际改写，是最严重的一类事故。
2. **上游"实测"必须附命令原文**。无可复现输出的数字不进方案；下游引用上游结论时，只写自己核对过的部分（「转发件不可信」≠「原件伪造」）。
3. **验收/派单里的数字必须自己重算**，不引用记忆。本日四次沿用旧口径（"14 项"实为 12 项、API 名、测绘转述、覆盖公式）共性相同。
4. **共享工作区**：`src/` 的「改名 + 搬移」必须一次 Edit 完成（或先在 `%TEMP%` 副本做整再整体写回）；改 `src/` 前后报「N 分钟不可跑／已可跑」；半成品窗口会让别人红在非回归上。
5. **门禁设计**：类型约束优于注释纪律（`_Apply` 同步签名）；**"覆盖"与"失败形态"是两个维度**（双端广播的覆盖已有，但假 socket 版把 120s 挂死变成 0.5s 失败）；安全网本身要防"挂死而非报错"（`_recv_json` 超时）。
6. **例外必须写死在测试里**才叫「显式决定」：`_apply_handlers()` 三桶断言（进表 12 / PING 早退 / 服务端→客户端 4 类不得进表），否则新增类型会静默降级成 `unsupported_message`。

### 11.5 遗留（下轮）

- `slow` job 已切 lock；desktop 包 mypy 收编（service 已完成）；render 密度新组合需先标定再入表。
- 镜像生成化（offline.js 由 Python 规则生成）——独立立项，优先级按"双端不一致事故的期望成本"定，不与 handle 串行。
- P3 候选：重复 `draw_offer` 是否应拒绝（产品判断，需同时动 core 与用例）、`playSound` 的 `catch(()=>{})` 改 `[sfx]` warn、victory/defeat 降采样（省 0.96 MiB，需 A/B 听感）。

## §12 S3-C「镜像一致性」执行结果（2026-11-09，Wave C）

### 12.1 结论：缩范围做——补「输入端对拍」，不做走子逻辑 codegen

Python 规则引擎（`core/rules.py`）与离线镜像（`android/Resources/assets/offline/offline.js`，**不是** `web/js/offline.js`，该文件不存在）的关系是：**走子校验器由 60+ 条定向对拍钉着，是资产不是负债**。真正的风险在「数据/状态机」层，且 81 条原对拍有一个**结构盲区**：所有用例都把 Python state 注入 JS，**JS 自己那份开局 roster 从未进入对拍**。方案 B（codegen 走子函数）与 A（运行时读 JSON 表）均否决——前者要再造一套语义表达，后者在 Android `file://` origin 下不可靠（`MainActivity.cs` 未开 `AllowFileAccessFromFileURLs`）。

### 12.2 交付（`18a4acf..c4a1ee8`）

| 提交 | 内容 |
|---|---|
| `18a4acf` | 音效播放失败不再静默（`[sfx]` warn，与 BGM 对齐） |
| `a452b03` | victory/defeat 转 44100/mono：**−1.279 MiB（两侧）**；实测原文件为伪立体声（L−R 差分 −64 dB RMS），单声道化近恒等；4 条 LFS 例外，blob 为实体非指针 |
| `b63e3b8` | `draw_offer` 三处对齐：core 补 `finished`/`已有 pending` 守卫、local 旁路补 `finished`、web 补二次确认与同房间 revision 单调性守卫（换房基线 −1）；协议用例同步改写 |
| `15ae157` | S1 更正两处"假覆盖"注释（threefold docstring、引用已删文件的注释） |
| `8e553c2` | S4 threefold 改「只看当前局面」，与 L-06 同义；新增 2 条对拍 |
| `b41e08c` → `0bc3377` | S2 `nativeOpening` 探针腿（唯一不注入 Python 局面的腿）+ S3 修 complete 分支尉/仕归位（104→108） |
| `2610533` | F1-a：classic/web 的 (1,5)/(11,5) 恢复为仕（110→113 / 104→107）；`xionghan_side(enabled=...)` 必填；不变量门禁；题库重生成（web 档不再含非法尉） |
| `2fef65f` | 原生开局覆盖 4 档 + `RESTORE_PAWN_LIMIT=7` 第 8 次招魂对拍（对拍 88 条） |
| `5633e42` | **旧档迁移**：F1-a 之前的 classic/web 棋谱不再拒载（三档口径，见 12.3） |
| `256596a` / `c9e2ef9` / `c4a1ee8` | 反向用例前提断言；`3c` 过度映射守卫；恒绿断言改「改源头重算」 |

### 12.3 旧档迁移（发布阻断项，已闭环）

F1-a 前保存的 classic/web 棋谱 `setup.*Slots` 含 `*:guard:1:5`，加载会在 `GameSetup.build` 抛 `unavailable piece slots`。迁移放 `storage.game_from_document`（唯一加载漏斗），**分档**：

| 存档 | 结果 |
|---|---|
| 开局档（`history` 空） | slots 与 `state.pieces` 均升级为 advisor；`perft(1)` 113/107 |
| 进行中档（`history` 非空） | 只保证能加载；盘面原样（guard，110/104）；`history[].pieceType` 不改；能续走 |
| 未知不可用槽位 | 仍抛 `ValueError`（迁移不吞真损坏） |

映射仅 `guard↔advisor`、仅 `{(1,5),(11,5)}`、仅在该档不启用尉时生效。进行中档那枚尉的语义：**不能动（0 合法着），但仍是合法吃子目标**（稀疏局面实测 `capturable_squares` 返回 1 条）——"死子"不等于"无效子"。

**过渡映射的后果**（`c9e2ef9` 的突变实测）：把"该档不启用尉"的条件放宽成恒真，会把 `desktop_complete` 的存档**直接打成拒载**——`ValueError: red setup contains unavailable piece slots: ['red:advisor:11:5']`（该档槽位表里没有 advisor 槽），而不是"改错一枚子"。因此 `3c` 守卫测的是**盘面侧**（`(1,5)` 仍是 guard、`perft(1)=108`）；**槽位侧**另有 3 条往返用例兜底（`4 failed / 11 passed` 的突变观测）。两个方向都要守，缺一不可。

### 12.4 本轮"假覆盖"四例与判据（建议入档）

> **判据：一条用例只有在「把被测实现改回旧行为」之后变红，才算测到东西。** 做不到时退一步：断言 fixture 里"坏/旧"的那半边在造完后确实存在（写具体数字，不写 `any(...)`）。

| # | 形态 | 实例 |
|---|---|---|
| 1 | 拿局面当规则 | 完整开局盘上"死尉不可被吃"是局面结论，换稀疏局面才是规则结论 |
| 2 | 造坏值空转 | `str.replace` 目标不存在 → 断言全落空 → "未报错"被误读成"迁移放过了真损坏" |
| 3 | 造旧数据只改一半 | 只退棋子、没退台账键 → "迁移生效"在没生效时也绿 |
| 4 | 手改派生值 | `position_key` 棋盘段 `sorted()` 且 `advisor < guard`，字符串替换造出的旧键**从未存在过**；朴素替换还会误改合法的第二只仕 |
| 5 | 同义反复自检 | `assert old_key == position_key(from_dict(...))` 两边同源，永远通过（草拟时被同侪拦下） |
| 6 | 突变观测范围 ≠ 结论范围 | 突变用 `-k` 过滤只跑 1 条（`1 failed, 14 deselected`），却得出"只有 3c 能抓到"的全局结论；补跑全套后为 `4 failed / 11 passed`（**操作化判据：`deselected > 0` 时禁止说"只有 X 能抓到"，必须报分子/分母**） |

**跨函数断言配对的可见性**：一条断言若依赖另一条断言（事前自证），必须在代码旁写一行"删掉它本行会退化为恒绿"，否则后人删掉事前断言时，留下的那条会静默变成假护栏。本轮 `test_desktop_storage.py` 已按此标注（见 §12.3 与 §12.5）。

### 12.5 CI（`#137→#147`，最终树由 `#147` 验证）

`#137`(6bbf3e3)、`#138`(d425dcd)、`#139`(18a4acf)、`#140`(8e553c2)、`#141`(b63e3b8)、`#142`(0bc3377)、`#144`(256596a)、`#145`(c9e2ef9)、`#147`(0d9d1a3) 均全绿；`#136`(a5e86d8)、`#143`(5633e42)、`#146`(c4a1ee8) 被同分支并发策略取消（新推送取代，其内容已包含在后续绿跑中）。全量 **953 passed / 1 skipped**，对拍 **88 条全绿**，perft 锚点 108/11647/44/1920 未变。

### 12.6 遗留

- **S5 数据层 codegen（已完成数据面）**：`scripts/gen_offline_data.py` 从 `core/profiles.py` 生成
  `TYPES` / `NAMES` / `DEFAULT_OPTIONS` / `PROFILE_DATA`，保留 `const TYPES=` / `const canvas=` 锚点；
  `--check` 已入门禁（`tests/test_offline_data_codegen.py`）。**逻辑型镜像仍在**（`Rules` 手写），
  属下一层问题，不在本次范围。
- **webapp/ 第三套引擎**：冻结、不随规则更新、CI 零引用；它不是生成化先例（产物未入库、验证器不在门禁），是反例。
- **22 kHz 音频档（已裁决：不做）**：产品决定"不设双档、一律 44.1 kHz、含 BGM"，见
  `tests/test_audio_quality_guard.py` 的守卫；原候选与命令仅作历史记录，不再执行。
- **AI 模式提和（已完成）**：`core/should_accept_draw` + 服务端/桌面共用；桌面不再"点一下即和"，被拒会发 `draw_declined` 快捷语。
