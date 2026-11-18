# 匈汉象棋 · 项目长期记忆（2026-11-12 收口）

> 本文件是跨会话的策展记忆，只放长期有效的结论与纪律。逐日过程见同目录 `2026-*.md`，30 天前的日志已移入 `archive/`。

## 一、仓库与环境

- git 根在上级 `xionghan-chess/`；远端 SSH `git@github.com:Jinny168/xionghan-chess.git`；主分支 `master`，同时推 `main`（两次 `git ls-remote` 核验两端同 SHA）。
- `git ls-remote` 会被全局 `remote.origin.uploadpack=true` 打断 → 用 `GIT_CONFIG_GLOBAL=$TEMP/xh-gitconfig`（含 `core.sshCommand` 与 `user.*`）。push 本身走 SSH 正常。另 `http.lfs.proxy=socks5://127.0.0.1:7890` 也会让裸 `git ls-remote` 报 `Invalid command: true`，临时 gitconfig 一并隔离。
- `mypy` 必须**无参**跑（`mypy src` 会带出 217 个 PySide6 类型噪音）；`npm` 走 `node .../npm-cli.js`；不要从 Bash 调 PowerShell（安全策略会拦）。
- 后台 python 会被降频；长标定用 `--resume` 分批、**恒定 `--n`**（`total_games` 决定 `book_index`，递增会破坏开局取样等价）。
- **2 个 python PID ≠ 并发**：`.venv/Scripts/python.exe` 是 launcher，会拉起 `C:\Python312\python.exe` 作子进程并原样传参。判定要看 `ParentProcessId`、CPU 时间、`sys._base_executable`，不能只数进程名或比命令行。

## 二、数据纪律（踩过的坑）

1. 引用胜率 / 配置前**先核 checkpoint 文件与样本量**；没核到手上的数只写方向、不写幅度。
2. 等价 / 差异判断**逐手或逐项比对**，不用聚合比分（root3 与 root5 同为 2–7–1，但逐手路径不同）。
3. 一次采样不写定律；结论必须带样本量 + CI + 覆盖面。n=10 的曲线只能写趋势。
4. **脚本门禁标记 ≠ 设计契约**：K4 验收读 `contractPass`，不读 `pass`；`pass=true` 只代表档位可分。
5. `--config-a/b` 只注入实例 config、**不改 `CONFIGS`**；扫候选与改全局必须分开。
6. **跨成员转述必须贴原文块，禁止重写数字 / 符号**（2026-11-09 曾把 536 行重写成 69 行，误伤成员并污染结论）。
7. 「上次全量全绿」不能当当前基线，先跑再下结论；共享工作树每个小单元做完即 commit，不留未提交在途改动。
8. **「只改移除集合」的规则改动**（三连的位移 / 恰好三子 / 不吃王），合法着法集合不变 → `legal`/`check`/perft 护栏一条都验不出，必须逐 `move_key` 比 `removals` 四元组 `(type,color,row,col)`。
9. **条件性期望不可当硬判据**：如「`_armorCaptures==0`（若 profiles 重生后已移除甲/楯/刺）」，前提不成立就判「本轮不适用」，用等价判据收，不删代码、不列未闭环项。**「不适用」≠「未闭环」**（T19 R3 同理），别混进欠账让验收误判。
10. **既有债要有差分证据**：拿「既有红 / 既有失败」当放行理由，必须在干净 HEAD worktree 上单独复现同样失败（本轮 T12 三条版本常量红用 `git worktree add --detach … 87aa774` 证既存）；且 skips 要逐个点名，别让静默跳过随「既有债」一起被豁免。

## 三、架构契约

- 三端共享 Python 核心：桌面 PySide6 / Web（服务端算棋，`web/` 无独立规则引擎）/ Android WebView。
- 对外三档 `beginner / medium / hard`；旧名 `easy→beginner`、`expert→hard`、`master→hard` 是**同一对象别名**，不是数值副本。
- `CONFIGS`（`src/xionghan_chess/core/ai.py`）是唯一来源；`PRODUCT_TIERS` 从它派生，`tests/test_level_targets_product.py` 逐字段钉死。
- `depth` 是迭代加深上限；S4 后真实可达 1/2/3（实测完成深度 A 1.000 / B 1.999）。
- 看门狗 = `PREFIX_MAX(0.78) + cap × 1.15` → 3.08 / 6.53 / 14.58s；**与 cap 改动必须同 commit**。
- `wallClean` 在 product 只记录、在 target 才是硬门；硬门是零深度 + nodes≤2% + K2 三条。
- 零深度 = `completed_depth == 0`；`_root` 对 wall 超时保留已完成根着法，nodes/cancel 仍整层作废。
- MCTS 已从产品链路下线，只剩 `benchmark_match(a_simulations=...)` 显式入口。

### 三端规则同源（2026-11-12，commit `57b9584`，`RULE_VERSION=3` 不 bump）

- **唯一源 + 产物链**：`webapp/js/core/` 是源；`scripts/gen_web_profiles.py`（照抄 `gen_offline_data.py` 的 `--write`/`--check`）从 Python `PROFILES`/`RuleOptions` 生成 `profiles.js`；`scripts/build_webapp_bundle.py` 同步 5 类产物（`webapp/dist/`、`online/public/index.html`、`online/core/`、`.edgeone/assets/js/core/`、`.edgeone` fixtures）。统一 `newline="\n"`（Windows CRLF 让 `--check` 常红）。`online/public/index.html` 内嵌**两份**引擎快照（`__WORKER_SRC` 1 + 主 inline 1），只改源文件不重跑 bundle = 线上仍跑旧引擎。
- **生成顺序唯一合法 S1–S6**：profiles `--write` → `--check` → bundle → `--check` → fixtures `--write` → verifier。fixtures 头部 `sourceDigest = sha256(5 文件字节序拼 + str(RULE_VERSION))`，verifier 启动重算、不等即拒；bundle 必须在 fixtures 前（digest 纳入 `online/public/index.html`）。
- **CI**：test job `A --check → B 重建 → C --check → D pytest → E 5 条 node`；重建排在主 pytest 前（新 pytest 读产物）；唯一源**只 `--check` 不 `--write`**（否则自己给自己发证）；lint 只查 tracked `webapp/js/core/*.js`；55s 完整重生成放 slow job。
- **护栏**：`removals` 四元组逐 `move_key` 比对；13 条 `rem:tl:*` + 2 条 `opt:tl:exact3*` 确定性变体（**不用 rng**，`option_variant_cases` 的 `random_position` 不保证三连形状）；防空跑三断言 `threeLineCases≥1` / variant 存在 / `removalsCompared≥1`；selftest 24/24。
- **`positionKey` 契约**：`rs${RULE_VERSION}-p3l{0|1}-promo{0|1}-self{0|1}` 引用生成的 JS `RULE_VERSION` 常量，**禁止写死 `rs3-`**（`offline.js:91` 硬编码是升位漏同步的病根）；五端 6 处逐字全等；文本哨兵只作记录、运行时判据优先。
- **性能重排不对称**：Python `rules.py` 与 Android `offline.js` 的两端外侧判据**后置**（`get()` 是线性扫描）；网页 `get()` 是 `state._grid` O(1) 查表，**不后移**（会改 `_grid` 失效时机）。AND 关系顺序不影响语义。
- **fixtures 体积**：两份各 24,768,257 B 入库；`= cases 5,569,175 + transitions 19,197,323 + 顶层包裹 1,759`；膨胀 49.83% 全在 `before.positionCounts`（新 positionKey 单 key ~800 B 的连带放大），不是 `removals`（347,477 B）。不压缩；折叠 positionCounts 属改回放语义，前置条件＝先跑 848 transitions 验 settle 集合不变。
- **生成非确定性**：`Piece.create()` 的 `uuid.uuid4()`、`MoveRecord` 的 `timestamp`/`elapsedMs`/`clocksMs` 都是隐性随机/时间源；codegen 必须固定种子流 + 序列化前规范化。

### 三端视觉对齐清单（2026-11-18，P1-8）

- **清单即数据**：`docs/visual_alignment_ledger.json` 是权威（13 行 × 桌面/web/webapp 三端），`docs/VISUAL_ALIGNMENT_TRIAD.md` 是叙述，`tests/test_visual_alignment_triad.py` 是门禁。三者**必须成对更新**，守卫会查「每个 id 与名称都出现在叙述文档里」。
- **门禁判档**：三端数值极差 ≤0.005 → `aligned`、≤0.02 → `minor`，否则 `drift`；不可比记 `form`。记的是**现状快照**，把三端对齐了同样会红 —— 改值必须先改清单再改代码。
- **片段模板口径**：`lit` 恰好一个 `{}`，`{}` 要紧贴数字起点（源码大量 `*.5` 省略前导零；写成 `*.{}` 会抠成 `5`）；正则由 `re.escape` 生成，允许以点开头；同一 minified 文件里同名片段多处时用 `index` 指名第几处（`VA-02` web=3、`VA-08` web=1、`VA-09/10/11` webapp=0/3/2、`VA-13` webapp=1）。
- **已知真漂移（不是缺陷记录就完事，是待裁决项）**：VA-07 webapp 上一步仍是圆盘 + 固定金色（第一优先）；VA-10 可走点 0.13/0.10/0.145；VA-12 动画 460/900/190ms（web 旧树 900ms 是历史包袱）；VA-02 盘半径 0.39/0.39/0.42。
- **不做像素基线**：webapp canvas 无基线，无头浏览器要处理字体/DPR/抗锯齿三处非确定 → 渲染结果层标「仅人工验收」（M-1…M-7）。
- **两条线纪律（星轨 vs 文字提示）**：星轨几何层按「有没有在答题」屏蔽（三端判据 `app.puzzleSession` / `!app.puzzle` / `puzzle_session is None`）；文字提示层按 `scored` 分流。**判据不许合并**，合并即回退（2026-11-18 已在工作树抓到一次 `!app.puzzle.scored`，常规对局会 TypeError 且章节闯关会放出星轨）。

## 四、S4 标定终局（2026-11-11）

- root16：`13-50-1`；root18（唯一一次预登记调整，仅注入、未进 `CONFIGS`）：`12-49-3`。**两轮 score 都是 13.5，A 得分率均 0.2109**，Wilson `[0.1289, 0.3258]`，Elo −229.2。
- ⇒ K4 出带是**结构性**的（d1→d2 的质变），不是选错 `root_limit`；两轮都 `contractPass=false`、`contractFailedGates=["band: 0.7891 > 0.75"]`；按预登记不再调参、不扩 n。
- 认证 10pt 宽的设计带需 n≈320（约 10 小时机时），明确不做；**K4 结论是「不可认证」**，不是「已验证失败」。
- 产品定稿 **root16**（唯一有完整无污染 n=64 数据，且 K1/K2/K3 都在该配置下验过）。
- K5（新手前 3 局合计 35–50%、第 5 局起 ≥55%，人工试玩 3–5 人 × 各 5 局）**未测**；出结果前不得宣称「入门档已验收」。

## 五、协作纪律

- 主理人只做编排 / 仲裁 / 汇编，**不代写专业产出**；迭代需求同样要调度，不因「改动小」自己动手。
- 大分叉合并：**取远端树 + 重放本地增量**，比 `-X theirs` 自动合并可靠。
- 动 `docs/` 前先备份；曾 `git rm -r docs` 误删整个目录（已用 `git checkout HEAD -- docs/` 还原）。
- **长 turn 不读 mailbox**：worker 连续干活的 turn 里发的调度消息（顺序改判、裁决 A、行号更正）不会被吸收，阶段回报仍用旧指令。解法：`TaskStop` + 发**自包含**重启消息（不依赖翻历史），要求先回执确认再开工。
- **规则判据冲突的通用原则**：不写死常量、运行时判据优先于文本计数（HTML 里 `rs3-` 2 次全在注释、`pawn_full_movement_at_base` 1 次在 UI 文案 → 整页字符串计数会把非代码信号当证据）。
