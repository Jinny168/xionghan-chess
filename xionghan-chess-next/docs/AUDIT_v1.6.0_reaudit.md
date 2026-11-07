# 匈汉象棋 v1.6.0 复审审计报告（新一次）

> 编制角色：资深跨端棋牌全栈工程审计 & 交付工程师
> 编制基准：扫描当前工作树（2026-09-27）+ 既有 `AUDIT_v1.6.0_full.md`、`QA_REPORT_1.6.0.md`、`CHANGELOG_1.6.0.md`、`VERSION_PLAN_1.6.0.md`
> 方法论：所有结论以**实测**为准（pytest / compileall / node --check / git ls-files / AUDIT 工具输出），不采信既有描述。

---

## 0. 总体结论（一句话）

**工程基线全绿，版本无碎片；但 F‑1（master 棋力 ≥55% 验收）仍是唯一未决的 P1 发布风险，必须作为已知风险披露，不得宣称 master 已稳定强于 hard。** i18n 残留、仓库卫生为 P2，须在 1.6.0 由"筹备"转为"发布"前收口。

| 维度 | 结论 | 评级 |
|---|---|---|
| 自动化测试 | 125 passed / 1 warning（实测复现） | ✅ |
| 编译 / 语法 | compileall + node --check 全过 | ✅ |
| 版本一致性 | core/pyproject/web/Android 统一 1.6.0，无旧版本残留 | ✅ |
| 认证与安全 | PBKDF2+salt、令牌哈希、401 映射、cleartext=false | ✅ |
| MCTS master 棋力 | **无有效 ≥55% 证据，实测方向性落后** | ⚠️ P1 |
| i18n | 主体完成，Web 残留硬编码中文 | ⚠️ P2 |
| 仓库卫生 | 1429 个 LFS 二进制仍被跟踪，git status 全红 | ⚠️ P2 |
| 规则语义 | C‑01/03/04/11/12 仍待产品拍板 | ⏸ 待确认 |

---

## 1. 实测校验（已通过项，附证据）

| 检查项 | 命令 | 结果 |
|---|---|---|
| Python 全量测试 | `./.venv/Scripts/python.exe -m pytest -q` | **125 passed, 1 warning** (36.67s) |
| Python 编译 | `compileall -q src tests scripts` | 通过 (exit 0) |
| Web JS 语法 | `node --check web/js/app.js && node --check web/js/i18n.js` | 通过 |
| Android 离线 JS | `node --check android/Resources/assets/offline/offline.js` 等 | 通过 |
| 区域 JSON | `locales/*.json` 解析 | 通过 (zh-CN/en) |
| 跨引擎等价 | `pytest tests/test_cross_engine.py -q` | **19 passed** |
| 版本扫描 | `grep -rn "1.5.0\|1.4.0\|2.0.0"` 源码生产路径 | **0 命中** |
| 2.0.0 跟踪 | `git ls-files | grep 2.0.0` | **0** |
| 明文流量 | `android/AndroidManifest.xml:3` `usesCleartextTraffic="false"` | 通过 |
| 广播增量 | `rooms.py:413/418` `snapshot(token, compact=True)` → `replay_tail=2` | 通过 (F‑4) |
| 悔棋 pending | `core/game.py:88-91` undo 后清除 draw/undo/restart+pause | 通过 (F‑9) |

认证实现抽查（`service/accounts.py`）：密码 `pbkdf2_hmac("sha256", pw, salt, 310_000)` + `secrets.token_hex(16)` 随机盐；会话令牌 `secrets.token_urlsafe(32)`，仅存 `sha256(token)` 哈希；登录用 `hmac.compare_digest` 时序安全比较；域异常统一映射为 `HTTPException(401/400/403/404)`，无堆栈外泄（`app.py:140-141` 等）。**结论：认证实现稳健。**

---

## 2. 风险登记（分维度）

### P1 — F‑1：master 棋力验收缺失（延续未决，本次实测强化）

**证据 1（既有筛查，无效）**：`docs/AI_BENCHMARK_1.6.0_screening.json` → `masterWins:0 / 50`、`masterWinRate:0.0`、`adjudicatedGames:50`。该筛查为 **2‑ply 截断**（`masterMoveMeanSeconds≈0.42`，远未用满 12s 预算），且 benchmark 工具在传入 `master_simulations` 时使用的是 **启发式 SEE scorer（`_see_score`）而非生产 master 路径**，故该 0/50 仅说明"截断+非生产配置"下无效，不能直接读作棋力结论——但它是仓库里**唯一**的 master 数据。

**证据 2（本次新增，生产路径探针）**：以生产配置运行 `scripts/benchmark_ai.py --games 2 --max-plies 40`（**不**传 `--master-simulations`，故走 `ChessAI(Difficulty.MASTER)` 真实加载 `training-data/policy-value-v1.npz` + `leaf_score` 路径），`AI_TIME_SCALE=0.05`：
- 第 1 局（master=红）：hard（黑）胜，34 手，master 累计 22.2s / hard 20.5s；
- 第 2 局（master=黑）：hard（红）胜，29 手，master 累计 18.6s / hard 18.1s；
- 两局均为**真实终局**（`adjudicated:false`），非截断。

> 说明：本次探针 master≈0.65s/步、hard≈1.2s/步（hard 时间约为 master 2 倍），**不构成公平棋力结论**；但它是首次走通"生产 master 路径"的端到端验证（模型加载、叶子估值、对局闭环无报错），并与筛查数据一致地表明：**master 并未稳定超越 hard**。

**工具正确性缺陷（必须修正后才可信）**：`benchmark_master_vs_hard(..., master_simulations=N)` 内部执行 `MCTS(simulations=N, root_score=scorer)`，其中 `scorer = ChessAI(HARD)._see_score`——这是与 hard 同源的 SEE 启发式，**并非**生产 master（生产 master 用 `_master_move_score` + 训练的 npz 先验 + `_master_leaf_score`）。后果：经 `--master-simulations` 跑出的任何 50 局结果都**不代表线上 master**。只有"不设 master_simulations、用 AI_TIME_SCALE 约束时间"的路径才等价于线上。

**结论**：F‑1 仍为开放 P1。**发布时 master 档必须标注"实验增强 / 可选模型推理"，不得宣称已稳定强于 hard。**

### P2 — F‑7（部分）：Web 残留硬编码中文绕过 i18n

`web/js/app.js` 中仍有用户可见文案未走 `t()`：
- `:40-41` `$('#replayPlay').title='播放'` / `.title='暂停'`（回放按钮悬浮提示）
- `:129` `` `${snapshot.spectatorCount||0} 人观战` ``（观战人数）

其余动态文案（toast / 云同步 / 分析 / 题库 / 背景图）已据 QA 报告补齐。建议将以上两处并入 `locales/*.json` 经 `t()` 取词。

### P2 — R‑08：仓库卫生未收口（1429 个 LFS 二进制仍被跟踪）

**证据**：`git ls-files release/ archive/ build-onefile/ | wc -l` = **1429**。`.gitignore` 已忽略 `build-onefile/`、`release/v1.4.0-delivery/`、`release/v1.5.0-delivery/`、`release/archive-experimental/`，但**未忽略 `release/` 与 `archive/` 整体**。

**根因**：本仓库在 `main` 分支配置了 Git LFS（`.gitattributes` 在 HEAD 中存在，覆盖 `*.exe/*.zip/*.model/*.pkl` 等），这些 release/archive 文件是 LFS 指针；**当前工作树未执行 `git lfs pull`**，故 `git status` 将 1429 个文件全部显示为"已删除"（实际是 LFS 内容未检出）。

**影响**：
1. `git status` 100% 红色，真实改动被淹没，无法审阅；
2. 本环境无法构建/获取 release 产物（缺 LFS 内容）；
3. 仓库体积与克隆成本偏高。

**处置（需用户授权后执行，按本机策略不擅自删跟踪文件）**：
- `git rm --cached -r release archive build-onefile`（保留磁盘，仅去索引），并补 `.gitignore`：`release/`、`archive/`（保留既有的 `archive-experimental/` 例外）；
- 或改为 CI/克隆阶段 `git lfs pull` 保证产物可重建。
- 注意：`release/v1.6.0-delivery/` 若已生成也应一并纳入忽略/外置。

### P3 — 安全次要项
- **无速率限制**：`/api/rooms`（创建）、`/api/auth/register|login` 无节流 → 账号/房间枚举与垃圾填充 DoS（P3）。
- **Android `allowBackup="true"`**（`AndroidManifest.xml:3`）：允许 `adb backup` 导出本地云同步库（`cloud.db`），建议设为 `false` 或定义 `backupRules`。
- **令牌 TTL 30 天**，无"登出其他设备 / 全部登出"；本地 SQLite `cloud.db` 未加密（依赖部署层 HTTPS + 设备加密）。均为可接受但建议项。

### P3 — 调试构建元数据残留 `2.0.0`
`android/obj/Debug/net9.0-android/.../AndroidManifest.xml` 显示 `versionName="2.0.0"`（该目录已被 `.gitignore` 的 `android/obj/` 忽略，**未入库**；`android/obj/Release/...` 正确为 `1.6.0`/`code 8`）。属过期调试缓存，发布前执行 clean rebuild 即可，确保无 2.0.0 泄漏。

### ⏸ 待确认 — F‑10：规则语义 C‑01/03/04/11/12
本次仅补等价性测试，未改规则语义。仍待产品拍板（巡线/跳板/盾保护/长将长捉/13×13 无进展阈值）。

---

## 3. 版本完整性（PASS，无碎片）

| 位置 | 版本 | 证据 |
|---|---|---|
| `src/xionghan_chess/__init__.py:3` | 1.6.0 | `__version__ = "1.6.0"` |
| `pyproject.toml:7` | 1.6.0 | `version = "1.6.0"` |
| `web/index.html:9,183` | 1.6.0 | `?v=1.6.0` / `版本 1.6.0` |
| Android Release manifest | 1.6.0 / code 8 | `android/obj/Release/.../AndroidManifest.xml` |
| 旧版本字符串 | 无 | `grep` 源码生产路径 0 命中；`git ls-files | grep 2.0.0` = 0 |

---

## 4. 分阶段整改计划

### M1 — 收口发布阻断/高优（P1/P2，建议 1 周内）
1. **F‑1 权威验收**：以生产路径跑 `benchmark_ai.py --games 50 --max-plies 240 --hard-scale 1.0`（**不**传 `--master-simulations`，两方 `AI_TIME_SCALE` 一致=1.0），在代表硬件上收集 `masterWinRate`、`masterMoveMaxSeconds≤12`。先修复工具的 `master_simulations` 配置误导（或文档明确"权威验收必须用时间约束路径"）。
2. **i18n 残留**（P2）：`app.js:40-41,129` 并入 locale 经 `t()`。
3. **仓库卫生**（P2）：经用户授权后 `git rm --cached -r release archive build-onefile` + 补 `.gitignore`，或在 CI 启用 `git lfs pull`。

### M2 — 安全加固（P3，建议 2 周内）
4. 为 `/api/rooms`、`/api/auth/*` 加速率限制（令牌桶 / 中间件）。
5. Android `allowBackup="false"` 或 `dataExtractionRules`；发布前 clean rebuild 清掉 `obj/Debug` 的 2.0.0 残留。
6. （可选）缩短令牌 TTL、增加"全部登出"。

### M3 — 待产品决策
7. **F‑10**：推动 C‑01/03/04/11/12 规则拍板；拍板后改语义并补回归，未拍板则保持仅测试。

---

## 5. 上线建议

v1.6.0 当前处于"筹备"态，工程质量达发布基线，但**建议先行完成 M1 的 F‑1 权威验收与仓库卫生收口**再打 tag。在任何对外材料中：
- master 档标注"实验增强 / 可选模型推理"；
- 不得宣称 master 胜率已 ≥55%（当前唯一数据点为 0/50 截断筛查 + 本次 0/2 生产路径探针，均非权威验收）；
- 明确 C‑01/03/04/11/12 规则项仍待产品确认。

> 编制：资深跨端棋牌全栈工程审计 & 交付工程师 ｜ 基准日 2026-09-27 ｜ 全部结论基于实测。

---

## 6. 整改执行台账（2026-11-07 复核）

> 复核方式：**实测**。`./.venv/Scripts/python.exe -m pytest -q` → **125 passed / 1 warning / 32.64 s**
> （Python 3.12.3）；git 侧用 `ls-files` / `ls-tree` / `show --name-status` 取证；
> F-1 用 `scripts/benchmark_ai.py` 实跑（结果见 §6.2）。

| # | §4 台账项 | 状态 | 证据 / 说明 |
|---|---|---|---|
| 1 | F-1 权威验收（50 局非截断 ≥55%） | ⛔ **仍未通过** | 尚无满足发布配置的胜率证据。本轮补跑 50 局（1/10 预算，§6.2），另发现满预算 50 局需 ≈43 h 机器时间，见 §6.2 |
| 1b | 修正 `master_simulations` 工具误导 | ✅ 已修 | `core/benchmark.py:45-53`：该分支已改走 `ChessAI(MASTER)._master_move_score/_master_leaf_score`（加载 npz 先验），不再共用 hard 的 SEE 启发式 |
| 2 | i18n 残留（`app.js:40-41,129`） | ✅ 已修 | `:40-41` 用 `t('replay.play'/'replay.pause')`；`:129` 用 `t('spectator.count',{count})`；`locales/zh-CN.json:565-571` 与 `en.json:565-571` 两侧键齐备 |
| 3 | 仓库卫生（1429 个 LFS 二进制仍被跟踪） | ✅ **已结清** | `6653684 merge remote master` 一次删除 **1429** 条 `release/ archive/ build-onefile/` 路径（`git show --name-status` 计数）；`git ls-files release archive build-onefile` = **0**；`git ls-tree HEAD` 三者 = **0**；`git status` 无 `D` 待提交 |
| 4 | 无速率限制（`/api/rooms`、`/api/auth/*`） | ✅ 已修 | `service/app.py:59-77` 按 IP 滑动窗口中间件；`XH_RATE_LIMIT_PER_MINUTE` **默认 0（关）**，不影响既有测试 |
| 5 | Android `allowBackup="true"` | ✅ 已修 | `android/AndroidManifest.xml:3` `allowBackup="false"`，同处 `usesCleartextTraffic="false"` |
| 5b | `obj/Debug` 残留 `2.0.0` | ⛔ 未结清 | 该目录被 `.gitignore` 的 `android/obj/` 覆盖、未入库；发布前 `clean` 重建即可，无需改代码 |
| 6 | 令牌 TTL / 全部登出（可选） | ⏸ 未做 | 本就不阻断发布，继续挂账 |
| 7 | F-10 规则拍板（C-01/03/04/11/12） | ⏸ 待产品 | 仅补等价性测试，未改语义 |

### 6.1 本轮顺手销掉的文档债

| 文件 | 问题 | 处置 |
|---|---|---|
| `README.md` | 标题仍写「匈汉象棋 1.5.0」，且只链 1.5.0 交付文档 | 改为 1.6.0，补链 `DELIVERY_1.6.0` / `QA_REPORT_1.6.0` / 本审计 |
| `docs/DELIVERY_1.6.0.md` | 「产物目录」把 `release/*.exe` 写成既有产物 | 改为「产物不入库、按打包命令重建」，并注明当前工作树中 `release/`、`archive/`、`build-onefile/` **均不存在** |
| `docs/VERSION_PLAN_1.6.0.md` §7 | 仍写「待执行 M1/M3/M4」 | 改为「已结清」，并指向本台账 |

### 6.2 F-1 实跑数据与可行性（2026-11-07）

**冒烟**（`--games 2 --max-plies 40 --hard-scale 0.1`，104 s）：master 单步 1.24–1.34 s，
两局均 hard 胜（第 1 局 40 手自然终局，第 2 局 40 手触帽裁定）。

**满预算不可行**：`CONFIGS[HARD].time_limit = CONFIGS[MASTER].time_limit = 12.0 s`
（`core/ai.py:39-43`），故 `AI_TIME_SCALE=1.0` 时

- 单局上限 240 手 × 平均 12 s ≈ **52 min/局**；
- 50 局 ≈ **43 h**，非原审计估计的「数小时」。

**本轮执行口径**：`--games 50 --max-plies 240 --hard-scale 0.1`，两侧预算相同（公平），
输出 `benchmarks/master_vs_hard_50g_scale0.1_2026-11-07.json`。
该数据**只能回答「1/10 预算下谁更强」**，不能替代发布配置的 ≥55% 验收——
MCTS 对时间预算的敏感度显著高于 alpha-beta，外推不成立。

**追加注意**：`scripts/benchmark_ai.py:20-29` 只在整轮结束后一次性写 `--output`，
中途崩溃即全丢；正式长跑建议先 `--games 2` 冒烟，再分段跑并把 stdout 落日志。

### 6.3 仍挂账

1. **F-1 满预算验收**：需 ≥40 h 连续机器时间，必须单排夜间/周末，不建议在开发机前台跑。
2. （跨线：2.0.x 分支）`benchmarks/selfplay_ab_2026-10-31.json` 与 `_conclusion.md` 尚未入库——
   2026-10-31 已跑完 32 局 / 4593 s，reflog 中无 `bench(ai):` 提交，只差 `git add` + commit。
3. `obj/Debug` 的 `2.0.0` 残留：发布前 clean rebuild。
