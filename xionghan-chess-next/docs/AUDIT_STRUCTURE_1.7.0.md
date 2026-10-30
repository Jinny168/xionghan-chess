# 匈汉象棋 v1.7.0 结构审计报告（目录 / 命名 / 依赖 / 职责）

> **审计对象**：`xionghan-chess-next`（活体树，298 跟踪文件）+ 仓库根级**遗留树**（单列，见 §五）
> **基准 HEAD**：`3fe7fe7`（作业期间未变；基准之后的变化见 **§七**）
> **审计人**：柯桥良（技术架构总监）
> **审计方法**：`Read`/`Grep`/`find`/`git`/`wc`/`cmp` 命令级取证；**import 方向用 grep 实测，不凭印象**
> **只读声明**：本次审计**未改动任何文件、未提交**。引用以**函数名 / 文件路径**为准（行号仅作定位辅证）。

---

## 一、结论摘要

**总体健康**：分层**干净**——`core` 是唯一基座，`service`/`desktop`/`training` 均只依赖 `core`，**无循环、无跨层反向依赖**（实测 import 全过）。真正的问题不在"层"，而在**"同一个事实被写多份、靠人工同步"**：本项目有 **12 处隐性同步点**（§四），其中**规则引擎镜像**是最大的结构性风险（且已被认知、有对拍护栏）。另有若干**构建/历史产物误入库**（`egg-info`、带硬编码路径的 spec、根级测试数据目录）与**同类多源声明**（版本号、依赖声明多源）。

**一句话判断**：架构骨架合格，**工程化卫生与"单一事实来源"是短板**；建议按 §三 的 P0/P1 清一轮。

---

## 二、七轴逐轴结论

### 轴 1 · 目录划分
- **现象**：活体树顶层 = `src/xionghan_chess/{core,service,desktop,training}` + `web/` + `android/` + `tests/` + `docs/` + `packaging/` + `scripts/` + `deploy/` + `requirements/` + `locales/` + 根配置（`pyproject.toml`/`package.json`/`requirements.txt`/`XionghanChess.spec`/`.dockerignore`/`.gitignore`）。
- **证据（实测）**：跟踪文件分布 `web 95 / src 69 / docs 46 / android 34 / tests 19 / scripts 5 / requirements 5 / packaging 5 / deploy 4 / locales 2 / .workbuddy 2`；`find . -type d -empty` 仅命中 `android/obj/*`（构建产物，已被忽略）→ **无可疑空目录**。
- **层清晰度**：**分层清晰**（见轴 3）。**"一层混多职责"存在**：`scripts/` 同时放 Python（`benchmark_ai.py`/`train_ai.py`）、Node（`offline_rules_probe.cjs`）、PowerShell（`run_server.ps1`/`run_desktop.ps1`）；`docs/` 混放文档 + JSON 数据（`AI_BENCHMARK_1.6.0_*.json`）+ 截图（`docs/assets/qa/*.png` 10 张）。
- **活体树内历史残留**：`src/xionghan_chess.egg-info/`（6 文件，**已入库的构建产物**）；`.desktop-test-data-{2,3,ai,feature,font}/`（5 个隐藏目录、各含 `XionghanChess/settings.json`，**测试夹具却放在仓库根**）；`.workbuddy/`（工具/规格文档 2 文件，混在产物树内）。
- **影响**：误导新人与工具；`egg-info` 与源码混放污染 `src/`。
- **建议**：① `.gitignore` 补 `*.egg-info/` 并 `git rm --cached`；② 测试数据移入 `tests/fixtures/`；③ `docs/assets/qa` 与 benchmark JSON 移出 `docs/` 根（或明确归入 `docs/assets/`、`docs/benchmarks/`）；④ `scripts/` 或按语言/用途拆子目录。
- **优先级**：egg-info **P1**；其余 **P2**。

### 轴 2 · 文件命名规范
- **现象**：Python/JS 主体 **`snake_case` / `camelCase` 各自统一**（`rules.py`/`board_removals` vs `boardRemovals`/`capturableSquares`）——跨语言差异属正常。**问题集中在"文档命名"与"少数同名异义"**。
- **版本化文件名（`AUDIT_1.6.0_full.md`/`VERSION_PLAN_1.6.0.md`/`CHANGELOG_1.6.0.md` 这套）——利弊**：
  - **利**：版本即目录维度，历史可并存、可追溯，删除/归档边界清楚；适合"每版一份正式交付物"的项目（本项目正是）。
  - **弊**：① **无"最新"别名**（读者要自己找最大版本号）；② 一旦改版要**复制整份**（易漂移，见 `docs/ABOUT.md` vs desktop 版**不一致**）；③ 版本号出现**两套写法**（见下）。
- **实测不一致**：① `AUDIT_v1.3.0_*.md`（有 `v`）vs `AUDIT_1.4.0_full.md`（无 `v`）；② `QA_v1.3.0.md` vs `QA_REPORT_1.4.0.md`（两套 QA 命名）；③ `UNIFIED_UI_OPTIMIZATION_1.1.md`（**两段版本**）vs 其余三段；④ `i18n-language-switch.md`（**全树唯一 kebab-case 文档**）；⑤ `AI_v1.3.0.md` vs `AI_FIXES.md` vs `AI_BENCHMARK_1.6.0_*.json`（有/无版本混用）。
- **同名异义（实测）**：`_guard` 在 `core/ai.py`（超时回调闭包）与 `core/rules.py`（「尉」走法校验器）**语义完全无关**；`initial_pieces` 在 `core/profiles.py`（按 options 生成）与 `core/setup.py`（按 profile 生成）**两份、签名不同**；`choose_move` 在 `core/ai.py` 与 `core/mcts.py` 各一份（**同名同类接口的两套搜索器**，属有意互换但读者易混）。
- **资源命名**：`avatar-01.webp`（kebab+序数，成套）vs `backgrounds/1.jpg…5.jpg`（**裸数字**）——不成体系；棋子图 `pieces/{cartoon,modern,traditional}/{hong,hei}{bing,che,...}.png` **成套且一致**（好）。
- **大小写**：PyInstaller spec `XionghanChess.spec`（PascalCase）vs `packaging/xionghan_chess.spec`（snake_case）**不一致**。
- **影响**：检索/归档/自动化（按名匹配）易错；同名异义是隐性阅读陷阱。
- **建议**：统一"版本化文档"为**单一写法**（建议 `NAME_vX.Y.Z.md`，全树一致），并引入 `docs/INDEX.md` 指向"当前版"；`_guard`/`initial_pieces` 等改名消歧；spec 命名统一。
- **优先级**：P2。

### 轴 3 · 依赖关系（实测 import 图）
- **模块级方向（grep 实测，非印象）**：
  - `core/*` → 仅 `core` 内部（相对 import）+ `xionghan_chess.i18n`。**无任何 `service/desktop/training` 反向引用**（实测通过）。
  - `service/*`（`app.py`/`rooms.py`/`accounts.py`）→ `core.*` + `i18n` + 同层 `.rooms`/`.accounts`。**不 import `desktop`/`training`**。
  - `desktop/*` → `core.*` + `i18n` + 同层。**不 import `service`/`training`**。
  - `training/*` → `..core.*` + 同层。不 import `i18n`。
  - **结论：单向依赖 DAG，`core` 为汇；无循环、无跨层反向依赖。**（实测）
- **唯一可议点**：`core/game.py`、`core/profiles.py` **import `xionghan_chess.i18n`**（i18n 位于包根、非 `core` 内）→ `core` 依赖了一个**根级横切工具**。虽非"跨层反向"，但严格分层里 i18n 应属 `core`（或独立 `shared`）。**P2**。
- **镜像同步机制（本轴重点）**：`android/Resources/assets/offline/offline.js` 是 `rules.py` 的**人工镜像**；同步靠 `scripts/offline_rules_probe.cjs`（Node 子进程）+ `tests/test_cross_engine.py`（对拍 moves/check/capturedByMove/capturableSquares/**positionKey**/resurrect）。**web 侧不走镜像**——`web/js/app.js` 实测调用服务端 `fetch('/legal')`/WebSocket（10 处），**复用 Python 引擎**（实测）。⇒ **真镜像只有 1 处（offline.js），但它是全项目最大的结构性风险**：把"规则语义"这一**单一事实**变成两份，且**对拍只能抓"两端不一致"，抓不到"两端一致地错"**（历史上 F1/F2 正是被弱 fixture 放过）。**缓解已存在（对拍门禁），但覆盖面依赖 fixture 质量。**
- **隐式耦合**：`i18n.py::_locale_dir()` 用**4 个候选路径**猜 `locales/`（`parents[1..3]` + `cwd`）→ 依赖运行时目录结构（实测）；`web/js/i18n.js` 用 **HTTP 路径** `/locales/*.json` 取目录（实测）；offline 用**内嵌** `offline-locales.js`（完全另一路）。同一份文案三种加载路径。
- **外部依赖一致性**：**三处声明**（见 §四·7），且**无 lock 文件**（无 `*.lock`/`poetry.lock`/`uv.lock`）。`requirements.txt` = `-e .[desktop,build,test]`，与 `requirements/*.txt`（`core`/`desktop`/`server`/`dev`/`train`）**分组口径不同**。
- **影响**：镜像 + 无锁 = "改一处、忘一处"与"环境漂移"两类历史病根。
- **建议**：① 给"对拍门禁"补**端到端随机/穷举对拍**（不止黄金用例）；② 引入 **lock**（`pip-compile`/`uv` 任一）并把 `requirements/*.txt` 设为**生成物**；③ i18n 三条加载路径收敛为"一源 + 生成"。
- **优先级**：镜像风险 **P0**（已在管，需加固）；lock/依赖收敛 **P1**。

### 轴 4 · 模块职责（一句话 + 边界）
| 模块 | 一句话职责 | 边界判断 |
|---|---|---|
| `core/rules.py`（**768** 行） | 权威、无副作用的走法校验与吃子求解 | **偏大**，但职责单一（规则）。**建议**：把"吃子规格"族（`CaptureKind`/`CaptureSpec`/`Removal`/`capturable_squares`/`_capture_removals`/`moves_to_target`/`promotion_types`/`promotable_types` + `_removal_order`）抽成 `core/capture.py`，`rules.py` 保留走法校验 |
| `core/ai.py`（**717** 行） | 主搜索 AI（negamax + 估值 + SEE 接线） | 偏大；`VALUES`/估值/搜索/缓存混合。可拆 `ai_eval.py` |
| `core/mcts.py`（113 行） | MCTS 搜索器 | 清晰；与 `ai.py` 同为"搜索器"，`choose_move` 同名（见轴 2） |
| `core/ai_see.py`（77 行） | 静态交换（SEE）估值 | 清晰 |
| `core/game.py`（278 行） | 对局状态机 + 判和账本 + 悔棋/认输/复活编排 | 清晰，但**同时管"对局流程"与"判和记账"**（`_record_position`），与 `storage.py` 有边界交叠 |
| `core/storage.py`（104 行） | 棋谱文档序列化/迁移 | 清晰 |
| `core/profiles.py`（256 行） | 规则档案 + 开关 + 初始摆位 | 清晰；`initial_pieces` 与 `setup.py` 同名（见轴 2） |
| `core/model.py`（187 行） | 数据结构（`Piece`/`GameState`/`Move`） | 清晰 |
| `service/`（`app.py` **487** + `rooms.py` **504**） | FastAPI 路由 + 房间编排 | 偏大；`rooms.py` 含计时/广播/重连/复活编排 |
| `desktop/app.py`（**1197 行**） | PySide6 单文件 UI | **全树最大单文件**；UI/交互/网络/渲染混合。**建议拆包** |
| `training/`（`encoding`/`network`/`selfplay`） | 训练管线 | 清晰 |
- **两模块干同一件事**：**两处 `initial_pieces`**（`profiles.py`/`setup.py`）、**两套搜索器 `choose_move`**（`ai.py`/`mcts.py`）——后者是"可换搜索器"的有意设计，前者疑似历史冗余（**推断，未确证**）。
- **优先级**：`desktop/app.py` 拆包 **P1**；其余 **P2**。

### 轴 5 · 冗余（具体到文件/函数）
- **重复实现**：① `capturable_squares`/`board_removals`/`moves_to_target`/`_apply_move` **在 Python 侧确为单点**（实测：读取走 `capturable_squares`，写侧走 `board_removals`→`_apply_move`，升变变体走 `moves_to_target`）；**升变子集的内联三处**（`ai.py::_tactical_moves`、`rules.py::pseudo_legal`、`rules.py::legal_moves`）——**⚠️ 基后已收敛 `bfea053`**（见 §七①），现为单一来源 `rules.py::promotable_types`。② **Python↔JS 镜像**（`rules.py`↔`offline.js`）天然双份（= §四·1）。
- **重复文件**：`docs/PIECE_RULES.md` ≡ `desktop/resources/docs/PIECE_RULES.md`（**逐字节相同**，实测 `cmp`）；`docs/ABOUT.md`(9 行) **≠** `desktop/.../ABOUT.md`(25 行)、`docs/HELP.md`(14) **≠** desktop(59)——**同名不同内容**；`web/assets/{sounds,avatars,backgrounds}` ≡ `desktop/resources/{...}`（**sounds 10/10、avatars 9/9、backgrounds 5/5 逐字节相同**，实测）；**两个 spec**（根 `XionghanChess.spec` vs `packaging/xionghan_chess.spec`）；**两处 docker**（遗留 `docker/` vs 活体 `deploy/`）。
- **零引用/死代码**：`TODO/FIXME/XXX/HACK` 实测 = **0**（代码干净）；`web/js/core/game-rules.js`（"第三套引擎"）**在遗留根树 `../web/`，不在活体树、且 HTTP 不可达**——属遗留树，非活体冗余。
- **`.gitignore` 覆盖**：**漏网** `*.egg-info/`、`.desktop-test-data-*/`（实测 `git check-ignore` 均未命中）；**过度**：无明显过度（`release/`、`archive/`、`build-onefile/`、`desktop-*.png` 等都是有意的历史隔离）。
- **优先级**：ABOUT/HELP 分叉 **P1**；其余 **P2**。

### 轴 6 · 缺失
- **CI**：**无**（无 `.github/`、`.gitlab-ci.yml`、`.circleci`，实测）。→ 204 条测试全靠本地手跑。**P1**。
- **`CONTRIBUTING` / 入门文档**：**无**（实测）。新人上手只有 `README.md`（落地页）+ `docs/*`，缺"开发环境怎么搭 / 怎么跑测试 / 目录导览"。**P1**。
- **依赖锁定**：**无 lock 文件**（实测）。**P1**。
- **代码质量基建**：**无 linter/formatter/type-checker 配置**（`pyproject.toml` 无 `[tool.ruff/black/mypy]`，无 `.flake8`/`.ruff.toml`/`setup.cfg`，实测）。类型标注覆盖（`def … ->` / `def`）：`core` 142/163≈**87%**、`service` 27/30≈**90%**、`desktop` **42/127≈33%**（UI 层基本无标注）、`training` 4/7。**P1/P2**。
- **测试结构性缺口**（只指结构，不深挖）：`tests/` 19 文件覆盖 core/service/desktop/training/protocol/i18n 均有对应；**无**针对 `web/js/app.js`、`android/` 的自动化测试（前端/壳层零测试，属结构缺口）。**P2**。

### 轴 7 · 结构不合理之处（含"隐性多处同步点"指向）
- **过大单文件**：`desktop/app.py` **1197**、`rules.py` **768**、`ai.py` **717**、`rooms.py` **504**、`service/app.py` **487**；`web/js/app.js` 仅 290 行但 **68883 字节（≈237 字符/行）**——**可读性差、diff 难审**。
- **源码与产物混放**：`src/…/egg-info`（产物入 `src/`）；`android/obj`、`bin`（已被 `.gitignore` 覆盖，**未入库**，OK）。
- **文档与代码混放**：`desktop/resources/docs/*.md`（3 份）与 `docs/` 重复；`docs/assets/qa/*.png`（QA 截图入库）；`.workbuddy/*`（工具/规格文档）混在活体树。
- **隐性多处同步点**：见 **§四**（12 条）。

---

## 三、分级优化建议清单

### P0（结构性高风险，先处理）
| # | 改什么 | 为什么 | 影响面 | 风险 |
|---|---|---|---|---|
| P0-1 | 加固**镜像对拍门禁**：`test_cross_engine.py` 增设"随机/穷举局面"对拍（覆盖 `positionKey`、`capturableSquares`、profile 定义），并把对拍纳入**发布前必过** | 镜像=最大结构风险；黄金用例太弱已两次放过真错（F1/F2） | `tests/`+`scripts/`，不动生产语义 | 低（只增测试） |

### P1（工程化卫生，影响发布与协作）
| # | 改什么 | 为什么 | 风险 |
|---|---|---|---|
| P1-1 | `git rm --cached` 掉 `src/…egg-info/` + `.gitignore` 补 `*.egg-info/`、`.desktop-test-data-*/` | 产物/夹具误入库 | 低（可逆） |
| P1-2 | 引入 **lock 文件**；把 `requirements/*.txt` 定为**生成物**；收敛依赖声明到**单一来源**（`pyproject.toml`） | 三处声明 + 无锁 = 环境漂移 | 低 |
| P1-3 | 版本号**单源化**（从 `__init__.py`/`pyproject` 派生，脚本注入 csproj/package.json/ABOUT） | 现多处手改（实测 19 处，见 §七②） | 低 |
| P1-4 | 上 **CI**（跑 `pytest` + `node --check` + 对拍） | 测试无自动化 | 低 |
| P1-5 | 加 **CONTRIBUTING/入门文档**（环境+测试+目录导览） | 新人上手缺口 | 低 |
| P1-6 | 删根级 `XionghanChess.spec`（**硬编码 `C:\Users\27415\PycharmProjects\...` 绝对路径**，仅本机可用）；统一保留 `packaging/` 版本 | 误导性失效产物 | 低 |
| P1-7 | 消解 `docs/ABOUT.md`/`HELP.md` 与 desktop 版**分叉**：定**单源**（建议 desktop 资源从 `docs/` 生成或反之） | 同名两义 | 低 |
| P1-8 | `desktop/app.py` 拆包（UI/网络/渲染分层） | 1197 行单文件 | 中（仅结构，需回归） |

### P2（整洁度/体验）
- P2-1 `docs/` 命名统一（消除 `v`/无 `v`、`QA_v`/`QA_REPORT`、kebab 特例）+ 加 `docs/INDEX.md`。
- P2-2 QA 截图与 benchmark JSON 移出 `docs/` 根。
- P2-3 `i18n` 三加载路径收敛为"一源+生成"；`i18n.py` 路径猜测改显式配置/打包资源定位。
- P2-4 静态资源 `web/assets` 与 `desktop/resources` 去重（符号链接/构建期拷贝）。
- P2-5 `_guard`/`initial_pieces` 改名消歧；spec 命名统一。
- P2-6 补前端/壳层测试骨架；`desktop` 类型标注补齐。
- P2-7 `scripts/` 按语言/用途拆子目录。

---

## 四、隐性多处同步点清单（12 条）
> 格式：**A ↔ B**（同步机制 / 有无护栏 / 状态 / 优先级）
1. **`core/rules.py` ↔ `android/.../offline.js`**（走法校验**两套实现**）——机制：`offline_rules_probe.cjs` + `test_cross_engine.py` 对拍；**有护栏但仅黄金用例**；**P0**。
2. **`core/profiles.py::PROFILES` ↔ `offline.js::PROFILES`**（4 个档案逐字段重定义）——**无专门对拍**（probe 按 `profileId` 跑，但档案"定义"本身不对拍）；**P1**。
3. **`rules.py::position_key` ↔ `offline.js::positionKey`**（须逐字符相等）——有对拍；**F1 已修**（元组序）；**P0 已加固**。
4. **`game.py::move` ↔ `offline.js::move`**（`board_removals`/`boardRemovals` 写侧）——有对拍腿；**P1**。
5. **i18n**：`locales/*.json`(源) ↔ `web/js/i18n.js`(HTTP fetch，**共享源**) ∪ `android/.../offline-locales.js`(**内嵌 5KB 子集**) ∪ `i18n.py`(Python)——**offline 子集无对拍**；**P1**。
6. **版本号（多源）**：`pyproject.toml` / `package.json` / `android/*.csproj` / `src/…/__init__.py::__version__` / `service/app.py`(FastAPI `version=`) / `deploy/docker-compose.yml`(image tag) / `web/index.html`(About + 2 cache-buster) / `web/js/app.js`(cache-buster) / `android/.../welcome.html` / `packaging/*.ps1` ×3 / `README.md` / `docs/ABOUT.md` / `desktop/resources/docs/ABOUT.md` / `locales/{en,zh-CN}.json` ——**纯人工同步**；**实测 19 处 + 1 测试耦合**（见 §七②）；**P1**。
7. **依赖声明（多源）**：`pyproject [project].dependencies` + `[project.optional-dependencies]` + `requirements/*.txt`（+ 根 `requirements.txt`）——**人工同步，且分组口径不同**；**P1**。
8. **前端 UI 双份**：`web/{index.html,js/app.js,js/i18n.js,css/app.css}` ↔ `android/.../offline/{index.html,welcome.html,offline.js,offline-locales.js,offline.css}`——**两套 UI**，无对拍；**P1**。
9. **文档重复**：`docs/PIECE_RULES.md` ≡ `desktop/.../PIECE_RULES.md`（**逐字节相同**）；`docs/ABOUT.md`/`HELP.md` 与 desktop 版**不一致**；**P1**。
10. **静态资源双份**：`web/assets/{sounds,avatars,backgrounds}` ≡ `desktop/resources/{...}`（**逐字节相同**）；**P2**（低 churn）。
11. **PyInstaller spec 双份**：根 `XionghanChess.spec`（**坏**，硬编码路径） vs `packaging/xionghan_chess.spec`（**对**）；**P1**。
12. **Docker 配置双份**：遗留根 `docker/` vs 活体 `deploy/`；**P1**（随遗留树处置）。

---

## 五、遗留根树（`master-588c86fc/` 级，与活体树分开评）
- **性质**：迁移前遗留树。内容 = `desktop/`、`docker/`、`docs/`、`web/`、`handoff.md`、`DEPLOYMENT.md`、`README.md`（已改写为落地页）、`LICENSE`、`requirements.txt`。
- **关键点**：`../web/js/core/game-rules.js`（"第三套引擎"）**在此树**，且 HTTP 不可达（活体 `service` 只挂内层 `web/`）——**属遗留，非活体风险**。
- **处置建议**：**去/留/归档三选一** —— 建议 **归档**（`git mv` 到 `legacy/` 或打 tag 后删工作副本），保留可追溯性；`README` 已声明"两棵树"，但**物理上仍并存**，建议归档时同步更新 README 的"追溯指引路径"。**P2**。
- **现状（2026-10-30 更新）**：本节所列遗留树（`desktop/`、`web/`、`docker/`、`docs/`、`handoff.md`、`DEPLOYMENT.md`）**已随根遗留树删除**；仓库根现仅保留 `README.md`、`LICENSE`、`.github/`、`.gitignore`、`.gitattributes`、`.workbuddy/`、`requirements.txt` 与活体子树 `xionghan-chess-next/`。

---

## 六、实测 / 推断 / 未确证声明
- **实测（有命令/文件证据）**：所有 import 方向与"无循环"；文件分布与计数；行数与字节数；`PIECE_RULES`/assets 逐字节相同；ABOUT/HELP 不一致；`egg-info`/测试数据未忽略；无 CI/无 linter/无 lock/无 CONTRIBUTING；版本号多源定位（§七②含完整普查）；`_guard`/`initial_pieces`/`choose_move` 同名定位；`.gitignore` 命中项；空目录仅 `android/obj`；offline/web 的同步机制（probe+对拍 / web 调服务端）。
- **推断（未逐一确证）**：`profiles.py::initial_pieces` 与 `setup.py::initial_pieces` 是否为"历史冗余"（两者可能职责不同，需读实现定）；`desktop/app.py` 拆包的具体切分线；镜像"随机对拍"的可行性需与主程序确认性能。
- **未确证/未能测**：`egg-info` 是否被某构建脚本**读取**（若被读则不能直接删，需改脚本）；`docs/` 与 `desktop/resources/docs/` 谁是**权威源**（需产品/文档负责人确认）；遗留树各子目录是否仍被脚本引用。

---

## 七、基准与后续变化

### (a) 基准 sha
本报告结论基于 **基准 `HEAD = 3fe7fe7`**（作业期间未变）。

### (b) 基准之后已发生的提交（实测 `git log`，截至本次落盘复测）
| commit | 说明 |
|---|---|
| `abaf1a8` | i18n(version)：About 版本号 1.6.0 → 1.7.0（中英） |
| `747dd28` | docs(version)：README 版本表述 + CHANGELOG 1.7.0 |
| `02788fd` | docs(version)：两份 ABOUT 版本号 → 1.7.0 |
| `bfea053` | refactor(rules)：**三处内联升变集收敛到单一来源**（无行为变更） |
| `2a7cc30` | docs(android)：BUILD_REQUIREMENTS 标题去掉版本号 |
（本次落盘时 `HEAD = 2a7cc30`。）

### (c) 由此**已失效 / 需订正**的条目
**① 轴 5「三处内联升变集 · 处理中」→ 已收敛（订正）**
`bfea053` 后实测：新增 **`rules.py::promotable_types`**（谓词**单一来源**），`rules.py::promotion_types` 为其排序包装；`rules.py::pseudo_legal`、`rules.py::legal_moves`、`rules.py::moves_to_target`、`ai.py::_tactical_moves` **全部改走单一来源**。⇒ §二·轴 5、§四·7 相关表述中"处理中"**应改为"已收敛"**。
**附注**：`ai.py::POOL_PROMOTION_TYPES` 仍在，但**仅**用于 `ai.py::_pool_value`（池估值），**不再**是"内联升变候选集"——不构成残留重复。

**② 版本号「×5」→ 严重低估，复测订正为「19 处 + 1 测试耦合」**
> **本条为我**自己**复跑全仓普查的实测结果（`grep -rn "1\.6\.0\|1\.7\.0"`，排除 `.git`/`node_modules`/`obj`/`bin`/`__pycache__`/`.pytest_cache`，并剔除"版本号在文件名/正文描述历史版本"的归档文档）。**未照抄任何外部转述。**

**已 bump 至 1.7.0（5 处）**：
| 位置 | 现状 |
|---|---|
| `README.md` | 当前版本 1.7.0 |
| `docs/ABOUT.md` | 匈汉象棋 1.7.0 |
| `src/xionghan_chess/desktop/resources/docs/ABOUT.md` | 版本：1.7.0 |
| `locales/en.json`（`about` 段） | Version 1.7.0 |
| `locales/zh-CN.json`（`about` 段） | 版本 1.7.0 |

**仍为 1.6.0（14 处，待 bump）**：
| # | 位置 | 形态 |
|---|---|---|
| 1 | `pyproject.toml` | `version = "1.6.0"` |
| 2 | `package.json` | `"version": "1.6.0"` |
| 3 | `src/xionghan_chess/__init__.py` | `__version__ = "1.6.0"` |
| 4 | `src/xionghan_chess/service/app.py` | `FastAPI(title=…, version="1.6.0", …)` |
| 5 | `android/XionghanChessAndroid.csproj` | `<ApplicationDisplayVersion>1.6.0</…>` |
| 6 | `deploy/docker-compose.yml` | `image: xionghan-chess:1.6.0` |
| 7 | `web/index.html` | About 对话框 `<strong>版本 1.6.0</strong>` |
| 8 | `web/index.html` | `<link … app.css?v=1.6.0>`（cache-buster） |
| 9 | `web/index.html` | `<script … app.js?v=1.6.0>`（cache-buster） |
| 10 | `web/js/app.js` | `import … './i18n.js?v=1.6.0'`（cache-buster） |
| 11 | `android/Resources/assets/offline/welcome.html` | 大厅 · v1.6.0 |
| 12 | `packaging/build_android.ps1` | `…-1.6.0-….apk` |
| 13 | `packaging/build_web_release.ps1` | `…-1.6.0-…` |
| 14 | `packaging/build_windows.ps1` | `…-1.6.0-…` |

**测试耦合（1 处）**：
- `tests/test_qa_regressions.py` —— 断言 `'app.css?v=1.6.0'` / `'app.js?v=1.6.0'` / `"i18n.js?v=1.6.0"`（3 条断言，1 个文件）。**bump 时须同步改此断言**，否则测试转红。

**合计：19 处运行时/产物字面量（5 已 bump / 14 待 bump）+ 1 处测试耦合。**
> **口径说明（供对齐）**：team-lead 转述为"13 处运行时/产物位置 + 1 处测试耦合"。我的普查为 **19 处**，**以本表逐条为准**；差额源于计数口径——例如是否把 `packaging/*.ps1` ×3、`deploy/docker-compose.yml` 的 image tag、以及 3 个 cache-buster 分别计。**建议按"是否须随版本号改动"逐条复核后定稿。**
> **现状提示**：bump **尚未完成**（`pyproject`/`package.json`/`__init__`/`csproj`/`service/app.py`/`docker-compose`/cache-buster/packaging 仍为 1.6.0），因此当前处于**过渡态不一致**；`docs/VERSION_PLAN_1.6.0.md` 的 M4 要求"三端版本一致"目前**不满足**。

**③ 未受影响**：§五 遗留根树处置建议、§三 P0/P1/P2 清单、其余各轴结论——基后提交**未触及**其证据。
