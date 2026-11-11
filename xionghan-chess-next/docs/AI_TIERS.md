# AI 档位（三档）与 S4 重标定

> 生效版本：S4 三档重标定后，HEAD `18e7ddb`。最终 n=64 实测日期 2026-11-11。
> 代码单一来源：`core/ai.py` 的 `PUBLIC_DIFFICULTIES` / `CONFIGS` /
> `LEGACY_DIFFICULTY_ALIASES` / `EXPECTED_MOVE_SECONDS` / `PREFIX_MAX` /
> `WATCHDOG_SECONDS`；`scripts/level_targets.py` 的 `PRODUCT_TIERS`；
> `scripts/calibrate_levels.py` 的门禁与 K 契约。
> 数据基线：`benchmarks/calibration_runs/2026-11-11-bm-final-n64.jsonl` 与同名 `.report.json`。

## 1. 对外三档与最终参数

### 1.1 最终参数表（`CONFIGS`，`ai.py:115-128`）

| 档位 | 枚举 | depth | cap | randomness | q_depth | candidate | branch | root | sample_margin | 看门狗 | 读条分母 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 入门 | `beginner` | 1 | 2.0s | 0.55 | 1 | 4 | 6 | 16 | 150 | 3.08s | 0.7s |
| 中级 | `medium` | 2 | 5.0s | 0.0 | 2 | 1 | 3 | 3 | 90 | 6.53s | 3.0s |
| 高级 | `hard` | 3 | 12.0s | 0.0 | 6 | 1 | 7 | 7 | 90 | 14.58s | 7.0s |

`max_nodes` 三档均为 `None`（不启用节点预算）。结构是**「深度×宽度反向补偿」**：
低档浅而宽、中档深而窄、高级居中；`root_limit` 是关键旋钮，缩宽度把目标深度装进 cap，
而不是抬 cap。

### 1.2 对外文案（`locales/*.json`，行为描述、不含层数与秒数）

| 档 | 中文 | English |
|---|---|---|
| 入门 | 只看眼前这一下，多一步就看不见。 | Sees only the move in front of it. |
| 中级 | 悬着的子会被吃掉，回吃也算得清。 | Hang a piece and it takes it — recapture included. |
| 高级 | 走错一步，它两步之后来收账。 | One loose move and it collects two moves later. |

守卫 `tests/test_desktop_difficulty_labels.py` 已从「文案里的 N 必须等于 `CONFIGS[d].depth`」
**反转**为 `test_label_has_no_numeric_depth_claim`（禁止「看 N 步 / N plies」等数字化深度承诺），
另有 `test_labels_do_not_claim_more_strength` 与 `test_labels_do_not_compare_budgets_across_levels`。
理由：`depth` 是内部参数，写成对外承诺既可被证伪，也会在调参时制造文档漂移。

### 1.3 入门档定位：不是「主动白送子」

`ai.py:361-389` 的 `_sampling_blocked()` 五条闸门（未算完不许取样、被将军不许、
一步制胜不许、最佳着是净赚 ≥ 一个兵的吃子不许）与 `:405-409` 的
`static_exchange_score < -PAWN` 过滤，明确禁止「有子不吃 / 一步制胜不杀 / 白送子」；
`_sample_weaker()` 只在候选窗口里**较差的那一半**取样，且分差受 `sample_margin=150` 限制。
入门档的弱点是 **d1 只看眼前、看不见安静手铺垫之后的两步以上战术链**，以及取样带来的
有限弱化；**不是**「看不见回吃」——`quiescence_depth=1` 已看过一层吃子，早期「入门 q
1→3」对照实测也证明 q1 与 q3 行为一致，写成「看不见回吃」会被证伪。K3-a v2 实测 A 侧
`avoidable_hangs` 5.31/局（见 §8）是「看不见战术链」的结果，不是「故意送」的结果。
旧文档「会漏攻击、白送子」的定位与代码冲突，已废弃。

玩家话术（对外统一口径）：**「它只看眼前这一下，多一步就看不见。」** 不承诺层数、
不承诺秒数、不承诺「它看不见回吃」。

### 1.4 时间线

- **并档阶段**：六档收敛为三档，`easy→beginner`、`expert→hard`、`master→hard`，
  旧枚举保留为同一对象别名；当时**未重标强度**、MCTS 下线。
- **S4 重标定**：`depth` 从「够不到的 d2/d6/d8」改为真实可达 1/2/3，收窄 root/branch，
  改看门狗公式，修零深度结构缺陷，引入 K1–K5 契约，并完成 beginner↔medium 的 n=64 实测。
  当前三档强度**已经重标**，不是并档时的原值。

## 2. 旧名兼容映射

| 旧名 | 归一结果 | 并档理由（括号内的参数是**并档时点历史值**，非现状） |
|---|---|---|
| `easy` | `beginner` | 当时 easy 是 1.5s/d4/0.35、medium 是 5s/d6/0.05；抬到 medium 等于变强，并入入门才不坑人 |
| `expert` | `hard` | 当时 expert 是 hard 的固定 d3 变体，实测选点与 hard 全同 |
| `master` | `hard` | master 对 hard 50 局 0 胜（数据源 `benchmarks/master_vs_hard_50g_scale{0.1,1.0}_2026-11-07.json`；当时 hard 为 d8、MCTS 尚未下线） |

- 字符串入口统一走 `normalize_difficulty()`（`strip().lower()` + 查表）；未知值由
  `Difficulty(...)` 抛错。消费端各自回落：桌面 `desktop/app.py:651-656` 捕获 `ValueError`
  回落 `MEDIUM`；Web `web/js/app.js:37` 用 `legacyDifficulty` 硬编码映射。
- `EASY / EXPERT / MASTER` 三个枚举成员保留，`CONFIGS` 条目是**同一对象别名**
  （`CONFIGS[MASTER] is CONFIGS[HARD]`），不是数值副本——复制会制造两份真相。
- 2026-11-11 实测：带 `ruleVersion: 2` 时 `easy / expert / master / beginner / medium / hard`
  六个名字请求 `POST /api/rooms` 全部返回 200；`bogus` 返回 400。

## 3. MCTS 下线

`core/mcts.py`、`tests/test_mcts_integration.py` 保留作研究/基准路径，但 `ChessAI`
**不再按档位分派**到 MCTS（`ai.py:297-299`）：`MASTER` 只是兼容名。产品链路只剩
alpha-beta 常规搜索。唯一仍可达 MCTS 的入口是 `core/benchmark.py` 中
`benchmark_match(a_simulations=...)` 的显式构造；`calibrate_levels.py` 不触发该路径。
`benchmark.py:18-27` 的 `MASTER_MOVE_CEILING_SECONDS = 13.8` 是基准路径历史常量。

## 4. UI / Web

- 桌面设置下拉遍历 `PUBLIC_DIFFICULTIES`（`desktop/ui/dialogs.py:118-120`）；Web
  `#difficultySelect` 是 `web/index.html:68` 的**三项硬编码**，由
  `tests/test_web_settings_parity.py:28-30` 静态守卫，不是从 Python 常量派生。
- 旧值不按「未知」处理：桌面插入不可选提示，原文来自 `desktop/texts.py:229-232`
  「旧档位「初级」已并入入门 / 旧档位「专家」已并入高级 / 旧档位「大师」已并入高级」；
  真正不认识的值才是 `texts.py:208`「未知档位「{name}」，已回落到默认」，回落 `medium`。
- `locales/*.json` 的 `difficulty.easy/expert/master` 三条文案**当前无代码消费**，属保留残留；
  旧档提示走 `desktop/texts.py` 硬编码，Web 迁移走 `app.js:37`。

## 5. 标定 tooling 与引用口径

- `scripts/level_targets.py` 有两张表：`PRODUCT_TIERS` 从 `CONFIGS` 派生（标定默认），
  `TARGETS` 是 S4-2b 旧提案表，仅用于历史复现。`tests/test_level_targets_product.py`
  逐字段钉住 `PRODUCT_TIERS == CONFIGS`（含 `max_nodes`）。
- `scripts/calibrate_levels.py`：`--tiers product` 为默认；`--initial-minutes` 默认 **180**
  （避免 12s/手在 10 分钟包干内自然超时，**这是标定脚本参数，产品默认仍是 10 分钟**）；
  支持 `--config-a/--config-b` 注入完整 `SearchConfig`（JSON 字符串或 `@file.json`）、
  `--time-scale`、`--resume`（按 checkpoint 行数接续，恒定 `total_games` 保证开局取样等价）。
- **product 口径**：`wallClean` 只记录不判红（`wall_enforced = tiers_name == "target"`），
  `target` 表仍把 `wallClean` 当硬门。最终 n=64 实测 wall 占比 **0.16%**（12/7736 手），
  不是旧文档写的 100%。`wallCleanEnforced=false` 时它不进入 `pass` 与 `failedGates`。
- 硬门共 9 项：`enoughGames`、`wallClean`（仅记录）、`noZeroDepth`、
  `nodesRatioAtMost2Percent`、`zeroDepthEvaluated`（a/b 各 ≥300 手）、
  `zeroDepthRateAtMost1Percent`、`zeroDepthNoConsecutive`、`zeroDepthAtMostOnePerGame`，
  外加 `winRatePass` 判据。最终 n=64 除 `winRatePass` 外全部通过，`failedGates=[]`。
- 逐局 JSONL 带 `a/b_completed_depth`（该方全部着法的均值）与 `a/b_wall_moves`；
  MCTS 路径不写 depth。`book.used` 逐局还原开局取样，可审计。

### 5.1 v2 判定分层（`judgementVersion == "v2"`）

`summarize()` 输出严格分三层，**测量层逐字段不动**：

| 层 | 字段 | 口径 |
|---|---|---|
| 测量层 | `wins/losses/draws/score/winRate/wilson95/elo/thresholdWins/moveTimes/boundReasons/zeroDepth*/moves/wallPercent/gates` | 与 v1 完全相同；`winRate`、`wilson95` 仍是 **A 方视角**，`elo` 仍是 A 相对 B |
| 判定层 | `winRatePass` / `pass` / `failedGates` | 改按**强档方向**判：`strong=max(point,1-point)`、`strong_low=max(low,1-high)`，门阈 `≥0.60` 且 `≥0.50`；`failedGates` 补 `winRatePass` 项（语义不变，只收参与 `pass` 计算的门） |
| 契约层 | `bandPass` / `contractPass` / `contractFailedGates` | `bandPass` 是 K4 设计带闭区间的**点估计**判定；`contractPass = pass and bandPass`；`contractFailedGates` **只收契约层失败项**，不与 `failedGates` 混用 |

派生键共 8 个：`strongSide` / `strongScore` / `strongLow` / `judgementVersion`（字符串
`"v2"`）/ `bandPass` / `contractPass` / `contractFailedGates` / `thresholdSide`（`"strong"`，
只标语义作用域，**不得解释成「强档最低得分」**；门槛 n=32→22、n=64→40，数值与 v1 相同）。
用 `strongScore` 而非 `strongWinRate`：`score` 是含和棋半分的**得分率**，本轮有 1 和局，
叫「胜率」会与 `wins` 口径冲突。

带宽只在 `BAND_LOW = 0.65` / `BAND_HIGH = 0.75` 定义，判定走纯函数
`band_pass(score_rate)`；`summarize`、展示文本、测试断言一律复用，禁止在别处复制
`0.65/0.75` 字面量（注释/文档例外；测量值如 `0.7891` 允许原样出现）。边界测试输入从
`BAND_LOW/BAND_HIGH` 加独立容差常量派生。`bandPass` 口径固定为点估计，不是 Wilson 区间。

> **`pass=true` 不等于验收通过。** 本轮 v2 报告即 `pass=True`、`failedGates=[]`、
> `contractPass=False`、`contractFailedGates=["band: 0.7891 > 0.75"]`。
> K4 结论只读 `contractPass`。

## 6. `depth` 与 `completed_depth`：上限 = 可达目标

**机制层（仍成立）**：`SearchConfig.depth` 是迭代加深的外层上限
（`for depth in range(1, cfg.depth + 1)`）；`completed_depth` 只在某一层 `_root`
**完整返回**后更新；墙钟到点抛 `SearchTimeout`，`choose_move` 保留 best-so-far 退出。
S4 引擎修复后，`_root` 对 **wall** 超时会保留本层已完成的根着法局部结果并返回 best
（`ai.py:464-478`；nodes/cancel 仍整层作废）；`bound_reason` 非空时主动停止继续加深。

**结论层（S4 已改写）**：并档初版 medium=d6、hard=d8 在 5s/12s cap 下实测都只完成 d2，
「调 `depth` 是空操作」是**那个时代的历史结论**。S4 不抬 cap，改为收窄 root/branch 让
目标深度装进预算，于是 `depth` 变成真实可达的目标：最终 n=64 完成深度均值
**A(beginner) 1.000 / B(medium) 1.999**，wall 仅 0.16%；hard 7/7 的 d3 达标率 83.75%
（`ai.py:126` 的探针结论）。因此当前档位差异来自**真实可达的 depth 1/2/3 + 宽度
（root 16/3/7、branch 6/3/7）+ 取样弱化**，cap 只是兜底；`completed_depth` **可以**作为
强度证据引用。`a/b_completed_depth` 字段就是为此落盘的。

## 7. 看门狗与读条

搜索开始前有一段**不可中断前缀**（`legal_moves` + 两次 `_order` / `_root_bias` 全扫；
`ai.py:317` 是搜索前唯一没有 deadline 检查点的段），架构实测 p50≈0.30s、max=0.78s，
故 `PREFIX_MAX = 0.78`。

> ⚠️ `PREFIX_MAX = 0.78` 是**本机实测值，不是跨平台常数**。低端安卓设备上该段可达 2s 以上；
> **发布前须在目标机型重测并覆写**，否则看门狗会在弱机型上掐掉合法长手（表现为「AI 走了个怪手」）。

```text
WATCHDOG_SECONDS[d] = round(PREFIX_MAX + CONFIGS[d].time_limit * 1.15, 3)
  → beginner 3.08s / medium 6.53s / hard 14.58s
```

旧公式 `cap × 1.15` 会在入门 cap=2.0s 时掐掉 p95≈2.5s 的合法长手，表现为「AI 走了个怪手」。
桌面 QTimer 消费该常量（`desktop/app.py:680-681`），读条分母用
`EXPECTED_MOVE_SECONDS = 0.7 / 3.0 / 7.0`（设计预估 median，不是 cap）。
**看门狗公式与 cap 改动必须同 commit**，否则中间态会把合法手杀掉。

## 8. K1–K5 契约与 n=64 实测

| 契约 | 口径 | n=64 实测 | 判定 |
|---|---|---|---|
| K1 延迟 | 入门 median ≤0.8s、中级 ≤4.0s、高级 ≤10.0s | A median 0.280s / p95 0.700s / max 1.971s；B 0.899s / 2.191s / 4.765s | 达标 |
| K2 零深度 | n≥300 手、点估计 ≤1%、零事件时 95% 上界 `min(1,3/n) ≤2%`、不得连续两手、单局 ≤1 次 | A 0/3858、B 0/3878，95% 上界均 0.1%，连续 0、单局>1 为 0 | 达标 |
| K3-a v1 | 每次走子后 SEE≥300 且被吃子≥450 记送子 | A `raw_hangs` 653、B 497 | 口径虚高，不单用 |
| K3-a v2 | `avoidable_hangs`：同一棋子只首次被攻击计数 + 走前 eval 在 ±300cp 内 + SEE 门槛不变；连送硬线 ≤2 手 | 计数：root16 A 5.31 / B 4.09 次/局；root18 A 5.08 / B 4.33 次/局。**最长连送：root16 A 4 / B 3，root18 A 3 / B 3** | 计数达标（5–6 预授权区间）；**连送条款未达标**（硬线 ≤2） |
| K3-b | 与最佳着分差 p50 ≤100cp、p90 ≤250cp、≥450cp 占比 ≤10% | A/B 均 p50=p90=0cp、≥450cp 占比 0% | 达标（但见下注） |
| K4 | 相邻档高对低得分率点估计落在 `[BAND_LOW, BAND_HIGH]`（即 65–75%），验收读 `contractPass` | B=medium 强档得分率 **0.7891**（A=beginner 0.2109） | **点估计出带、不可认证**（`contractPass=false`） |
| K5-a | 新手前 3 局合计胜率 35–50%（0/3 视为上手曲线断裂） | **未测** | 待人工试玩 |
| K5-b | 第 5 局起胜率 ≥55% | **未测** | 待人工试玩 |

**K1 版本谱系（防三方冲突）**：v1 `median ≤0.6s / p95 ≤2.2s / 硬上限 2.3s`（早期）；
v2 `median ≤2.0s / p95 ≤2.6s / 硬上限 3.1s`（「每手吃满 cap + 0.3–0.8s 不可中断前缀」时代，
**已作废**）；**v3（现行）** `入门 median ≤0.8s / 中级 ≤4.0s / 高级 ≤10.0s`，与
`ai.py:126` 注释「守 K1（高级 median≤10s）」一致。**v2 的 2.0 / 2.6 / 3.1 不得再作为
现行阈值引用**；引用 K1 前先确认是 v3。

**K3-a 注**：连送未达标是**结构性**的，与 root 选择无关（两轮同向：A 4→3、B 均为 3，属单事件量级）。
成因是 d1 在少数局面会连续看不见同一条战术线索（同一子被连续威胁），表现为连送而非散布；
这是比「次数」更贴体感的不达标（玩家会看到「它连着送了三次」）。本轮按预登记不再调参，
列入 S5 观察项。**计数与连送必须分开陈述，不得写「K3-a 全达标」。**

**K3-b 注**：该指标对这两档基本恒达标——`root_scores` 是降序、best 取 `[0]` 正确；
中级 `randomness=0` 必选最佳，入门取样被 `sample_margin=150` 压在 150cp 内，故 p50/p90 为 0。
不能把「全 0」读成「AI 完全没有失误」，也不能用 K3-b 替代 K3-a。

**K2 注**：`zeroDepthEvaluated = a_moves>=300 and b_moves>=300`；样本不足时 K2 三条门禁
自动置 true 并标注「样本 <300 手，K2 未评估」，不得把未评估写成达标。

**K4 与 K5 的关系**：K4 是 AI↔AI 的档间距，K5 是新手上手体验，两条结论必须分别陈述、
不得互相代替。K4 点估计出带、不可认证，**不推翻 K5**。K5 需人工试玩 **3–5 人 × 各 5 局**，
不联网、不埋点；目前**未测**，因此 **K5 出结果前不得宣称「入门档已验收」**。

## 9. 最终 n=64 结果（root16 主表 + root18 对照）

来源：`benchmarks/calibration_runs/2026-11-11-bm-final-n64.report.json`（root16）与
`2026-11-11-bm-root18-final-n64.report.json`（root18 注入配置），各带同名 `.jsonl`。
条件：`--tiers product`、`beginner(A) vs medium(B)`、64 局开局书（每开局红黑各一）、
`--max-plies 200`、`--initial-minutes 180`。

### 9.1 两轮对照（root16 主表 / root18 预登记调整）

| 轮次 | root_limit | W/L/D | 得分 | A(入门) 得分率 | B(中级) 得分率 | Wilson 95%(A) | Elo | pass | bandPass | contractPass | contractFailedGates | wall 占比 | 完成深度均值 A / B |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **主表** root16 | 16 | 13 / 50 / 1 | 13.5 / 64 | **0.2109** | 0.7891 | [12.89%, 32.58%] | −229.2 | True | False | **False** | `["band: 0.7891 > 0.75"]` | 0.16% | **1.0000 / 1.9991** |
| 对照 root18 | 18 | 12 / 49 / 3 | 13.5 / 64 | **0.2109** | 0.7891 | [12.89%, 32.58%] | −229.2 | True | False | **False** | `["band: 0.7891 > 0.75"]` | 0.09% | **1.0000 / 1.9998** |

- 两轮**得分率、Wilson、Elo 三项完全相同**（13.5/64 = 0.2109）：胜负分布 `13-50-1 → 12-49-3`
  的变化没有改变得分。
- 合并两轮（n=128，`25/4/99`，得分 27.0）：点估计仍 **0.2109**，Wilson `[14.92%, 28.95%]`
  （宽 14.03pt）——**上界仍 > 25%，「出带」是点估计陈述，不是被证明的出带**。
- `pass=True` 是 v2 口径下「强档显著强于弱档」（下界 67.42% > 50%）；K4 以
  `contractPass=false` / `contractFailedGates` 为准。
- 对局长度均值 128.9 / 134.1 手；判定局 8 / 7 局；B 完成深度 1.9991 / 1.9998
  （非精确 2，因各轮 5 / 2 手被 wall 截断）。

### 9.2 root16 主表（`CONFIGS` 定稿配置）

| 项 | 值 |
|---|---|
| W / L / D（A 视角） | 13 / 50 / 1 |
| A 得分率 / B 得分率 | **0.2109** / 0.7891 |
| Wilson 95% CI（A） | [0.1289, 0.3258] |
| Elo（A 相对 B） | −229.2 |
| `thresholdWins` / `thresholdSide` | 40 / `"strong"` |
| 判定层（v2） | `winRatePass=True`、`pass=True`、`failedGates=[]` |
| 契约层（v2） | `bandPass=False`、`contractPass=False`、`contractFailedGates=["band: 0.7891 > 0.75"]` |
| 派生键 | `strongSide="b"`、`strongScore=0.7891`、`strongLow=0.6742`、`judgementVersion="v2"` |
| moveTimes A | n=3851, median 0.280s, p95 0.700s, max 1.971s |
| moveTimes B | n=3873, median 0.899s, p95 2.191s, max 4.765s |
| 手数 A / B | 3858 / 3878 |
| boundReasons | A wall 7 / nodes 0 / cancel 0；B wall 5 / 0 / 0（合计 0.16%） |
| 完成深度均值 | A 1.000 / B 1.999 |
| `adjudicated` / 平均手数 | 8 局 / 128.9 |

### 9.3 报告版本：v1 的方向错配与 v2 修订

**v1（原始报告）**：`calibrate_levels.py` 旧 `:218` 判据
`point >= 0.60 and low >= 0.50` 要求 **A 方得分率 ≥60%**，而 docstring 推荐用法
都是 A=弱档，方向相反 → `winRatePass=false` 恒成立；`pass=false` 却 `failedGates=[]`
的根因是旧 `failedGates` 列表漏了 `winRatePass`。因此 **v1 的 `pass=false` 既不是
K4 未达成的证据，也不是任何验收结论**。该文件已备份为
`2026-11-11-bm-final-n64.v1.report.json`。

**v2（当前报告）**：按 §5.1 修判定后，用同一份 64 行 JSONL 重算（`--resume` 直接汇总，
**不重跑对局**），得 `pass=True`、`failedGates=[]`，但 `contractPass=False`、
`contractFailedGates=["band: 0.7891 > 0.75"]`。测量层 20 组字段经
`_verify_n64_recompute.py` 独立复算逐项一致（`ALL CHECKED FIELDS MATCH`）。
历史扫频报告（c1/c2/n10 等 12 份）保留 v1 语义、**不重生成**——它们格式不同
（gates 仅 5 项、无 `failedGates`），重生成会连格式一起变，也会抹掉旧口径证据。

**K4 验收结论只读 `contractPass`，不读 `pass`；`pass=true` 不代表验收通过。**

## 10. 宽度实测与参数选型（n=10，仅趋势）

来源：`benchmarks/calibration_runs/2026-11-11-bm-mroot{3,5,7,9}-n10.report.json`
与 `...-aroot18-n10.report.json`。`winRate` 为 A（入门）得分率，`b_med` 为中级 median 延迟。

| 扫描 | W/L/D | A 得分率 | Wilson 95% | b median |
|---|---|---:|---|---:|
| B 侧 root3 | 2/7/1 | 0.25 | [0.0809, 0.5578] | 1.06s |
| B 侧 root5 | 2/7/1 | 0.25 | [0.0809, 0.5578] | 1.65s |
| B 侧 root7 | 2/8/0 | 0.20 | [0.0567, 0.5098] | 2.38s |
| B 侧 root9 | 0/10/0 | 0.00 | [0.0000, 0.2775] | 2.60s |
| A 侧 root18 | 4/6/0 | 0.40 | [0.1682, 0.6873] | 1.06s |

**读法约束（数据纪律）**：这五行全是 n=10，Wilson 宽达 48pt，**只能写趋势，不能拟合斜率、
不能据以定「最优值」**。root3 与 root5 聚合比分同为 2–7–1、胜率同为 0.25，但逐手比对
`a_move_times` / `b_move_times` 与 winners 序列后路径不同，**不得据此断言「宽度饱和」**；
最终取 `root16`（入门）/ `root3`（中级）是取 14 与 18 的中点以避开两端，不是拟合极值。

## 11. K4 判读与预登记的一次调整

### 11.1 K4 正式结论（root16 定稿配置，n=64）

高档（中级）对低档（入门）的得分率**点估计 0.7891**，落在设计带
`[BAND_LOW, BAND_HIGH] = [0.65, 0.75]` **之外**（超出上界 3.91pt）。
强档 Wilson 95% CI 为 **[0.6742, 0.8711]**，**仅与设计带部分重叠**
（交集 `[0.6742, 0.75]` = **7.58pt**），且上界 0.8711 超出带上界 **12.11pt**；
n=64 的 CI 全宽 **19.69pt**，大于设计带宽度 10pt。

结论：**点估计出带、CI 仅与带部分重叠且上界远超 0.75，不可认证**。
n=64 能证明的只有「中级显著强于入门」（强档得分率 Wilson 下界 0.6742 > 0.50），
既不能认证点估计落在带内，也不能否证。这是样本量问题，不是换一个 `root_limit`
能消除的。旧表述「CI 覆盖带内」已作废（CI 并未覆盖整条带，只是部分重叠）。

要在 p≈0.70 附近把 CI 全宽压到 10pt 以内，需 n≈320（约 10 小时机时）；
**本轮明确不做**，也不以扩 n 作为第二次调整。

**两轮独立样本复现**：root18（预登记唯一一次调整）点估计同为 0.2109，Wilson 与 Elo
逐位一致；合并 n=128 后点估计仍 0.2109、Wilson `[14.92%, 28.95%]`。⇒ **出带结论稳定**，
「换 `root_limit` 不改变结果」成立；但「出带」仍是点估计陈述，不是被证明的出带。

### 11.2 预登记规则与本次终验的目的

**预登记判读规则**（S4 标定前约定，至多一次调整）：

1. 点估计落在 25–35% → 定稿、写文档；
2. 点估计 <25% → 只做一次调整「入门 `root_limit` 16→18」，终验 n=64，**不再循环**；
3. 终验仍出带 → 如实写「观测值 + CI + 不可认证」，**不允许第二次调整**。

n=64 实测 21.09% < 25%，触发第 2 条。调整采用 `--config-a` **注入实例配置**，
不改 `CONFIGS`、不重标预算；config 逐字段与 `CONFIGS[BEGINNER]` 一致，仅
`root_limit=18`。

**本次终验的目的不是认证「带内」**——按 §11.1，n=64 在统计上做不到。它是给
「K4 出带是结构性的（d1→d2 从看不见战术链到看得见回吃的质变），不是选错
`root_limit`」提供**第二个独立样本**：若 root18 同样出带，可排除单一参数误选；
若落带，则如实记录，但同样不构成认证。这是**最后一次调整**，不循环、不扩 n、
不再调参。

### 11.3 产品定稿：保留 `root_limit=16`

**无论 root18 终验结果如何，产品最终定稿保留 root16**，三条依据：

1. root16 是唯一有完整、无污染 n=64 数据的配置；
2. K1 / K2 / K3 全部在 root16 下验过，换 root 等于把已验过的契约作废；
3. root18 只是 `--config-a` 注入扫候选，从未进入 `CONFIGS`。

root18 终验结果作为**标定证据**归档，不作为产品档位发布；若终值落带，
也只写「该候选在另一次 n=64 采样中落带」，不改产品定稿。

> 状态（2026-11-11）：root18 终验**已完成**（`12-49-3`，与 root16 同分 0.2109、
> `contractPass=false`），已回填 §9.1 / §11.1。此前一次尝试因 lead 对 venv 进程树的
> 误判被隔离作废（**非数据污染**，见 §12.1），随后用全新 checkpoint 单进程重跑完成。

## 12. 标定纪律

### 12.1 一次误判与纠正（2026-11-11，保留以免重犯）

**误判**：root18 终验第一次尝试时，进程快照出现两个 `python.exe` 且命令行完全相同，
一度被判为「两条并发标定链」，据此把前 7 局整批作废、停掉 worker 并重启。

**验证与纠正**：`.venv/Scripts/python.exe`（274712 B）是 venv launcher，
`sys._base_executable = C:\Python312\python.exe`，它会拉起 base python 作为**子进程**并原样传参。
CPU 时间实测：父进程（venv launcher）`UserModeTime ≈ 0s` / `KernelModeTime ≈ 0.02s`，
子进程（base python）`UserModeTime ≈ 364.9s`；`14924.ParentProcessId = 23128`，
内存差（launcher ≈9MB / 实算 ≈46MB）亦吻合。因此「两个 python.exe + 相同命令行」是
**一条进程链的两层，不是两条并发标定链**；「CPU 争抢令 K1 延迟与 wall 手数系统性失真」
缺乏证据，不能作为判废理由。

**处置修订**：原 7 局经复核 1..7 连续、dup=0、坏行 0，无污染证据。但隔离已完成、
全新 checkpoint 重跑已启动，为避免两份 checkpoint 混用造成审计口径不清，维持整批作废并
归档为 `.POLLUTED-dual-process.jsonl.bak`（**文件名保留以免破坏既有引用，含义是
「因误判隔离」，不是「数据污染」**），不并入正式数据，后续判读以新 checkpoint 为准。
代价约 7 局 / 10 分钟，换取单一来源。

**可复用识别法**：判定并发必须看 `ParentProcessId`、CPU 时间与 `sys._base_executable`，
不能只看进程名与命令行；`timeout.exe` / `env.exe` / venv launcher / base python 是同一条
命令的正常四层包装。另外 `scripts/calibrate_levels.py:340` 以 `open("a")` 追加、`:343-344`
每局 `flush()`，小行追加下「文件看起来干净（局号连续、无 dup、无坏行）」既不能证单进程
也不能证双进程，同样不是有效判据。

### 12.2 数据纪律（七条）

1. **引用胜率 / 配置前核 checkpoint 文件与样本量**；没核到手上的数只写方向、不写幅度。
2. **等价性 / 差异判断必须逐手或逐项比对**，不得用聚合比分代替（root3 与 root5 同为
   2–7–1 但逐手路径不同，不能断言饱和）。
3. **一次采样不写定律**：n=10 的宽度曲线只能写趋势，不能拟合斜率或据以定「最优值」。
4. **脚本门禁标记 ≠ 设计契约**：`pass=true` 只代表档位可分，K4 验收结论只读
   `contractPass`；两者不得混用，也不得把 `contractPass=false` 写成「已验证失败」。
5. **`--config-a/b` 只注入实例 config、不改 `CONFIGS`**；扫候选与改全局必须分开。
6. **「不动测量层」必须逐字段列出清单**（见 §5.1 表格），不能用一句口号代替；
   改动汇总逻辑时，测量层不变式要有逐夹具断言兜底。
7. **区分「带宽定义」与「待测输入值」**：带宽只在 `BAND_LOW` / `BAND_HIGH` 定义，
   判定逻辑、展示文本、测试断言一律复用常量；测试输入从常量派生，测量值
   （如 `0.7891`）允许原样出现。

### 12.3 可复用门禁、复算工具与追溯性

① 标定启动前确认无遗留 `calibrate_levels.py` 进程（按进程树判断，不按进程名计数）；
② 任何时刻只允许一条标定命令在飞；③ `timeout` 包装层退出不等于整条进程链退出，
收尾须验活句柄；④ 受不可排除系统性干扰的样本整批隔离并保留 `.bak` 作证据；
⑤ 异常判定的依据（进程快照、CPU 时间、命令行、父子关系）必须当场固化；
⑥ 汇总结果必须经**独立复算**核对：`benchmarks/calibration_runs/_verify_n64_recompute.py
<checkpoint> [report] [n]` 从 JSONL 逐行重算 20 组字段并与 `.report.json` 逐项比对
（2026-11-11 在 root16 数据上验证为 `ALL CHECKED FIELDS MATCH`），不调用 `summarize`；
⑦ 边界态结论（如「d2 是否达成」）必须在**独占的干净进程**里测：`scripts/bench_roots.py`
实测前序负载可让 depth 从 2 掉到 1、nodes 差约 25% 并改变选点；同批局面须在同一次
进程启动内连续测完，且局面须冻结为 FEN/JSON 快照，不能只靠 `seed + plies`。

2026-11-11 对 root18 重跑前 9 局做过负载核查：纯对局 **87.4s/局** vs root16 的 83.8s/局
（+4.3%），但平均 **159.2 手** vs 124.7 手（+27.7%）；每手 A 0.247s vs 0.273s、
B 0.790s vs 0.942s，wall 手 1 vs 5 —— **无系统性变慢，K1 数据可引用**。

本次误判与纠正的依据来自进程层观测与终端记录，**未落在版本库 commit 中**
（`benchmarks/calibration_runs/` 整目录 untracked、无相关提交），故以本节文字固化供后续审计。

## 13. 门禁（2026-11-11）

### 13.1 v2 判定改动前的全量基线（HEAD `18e7ddb`）

| 门禁 | 结果 |
|---|---|
| `pytest -q` | **1345 passed, 2 skipped, 1 warning**（364.9s） |
| 跨引擎对拍 | 收集 88 条 / 通过 88 / 失败 0 / 跳过 0 / 报错 0 |
| `ruff check src tests scripts` | All checks passed |
| `ruff format --check` | 217 files already formatted |
| 无参 `mypy`（按 `pyproject.toml` 的 `files=`） | Success: no issues found in 24 source files |
| `scripts/desktop_smoke.py` | `DESKTOP_SMOKE_OK` |
| Web 旧名兼容（TestClient） | 6 个合法档名均 200，`bogus` 400 |

`mypy` 必须**无参**运行；带路径参数会把 PySide6 类型噪音算进来（历史上误报 217 项）。

### 13.2 v2 判定落地后的针对性门禁

| 门禁 | 结果 |
|---|---|
| `pytest -q tests/test_calibrate_summary.py` | **25 passed**（原 11 条零改动 + 新增 14 条：边界六例、纯函数复用、真值表四格、对称双夹具、测量层四夹具、v2 schema） |
| `ruff check scripts/calibrate_levels.py tests/test_calibrate_summary.py` | All checks passed |
| `ruff format --check` 同上两文件 | 2 files already formatted |
| `_verify_n64_recompute.py` 对 v2 报告 | `ALL CHECKED FIELDS MATCH (共 20 组字段)` |

**全量 `pytest -q` 需在 root18 标定跑完后重跑**：v2 改动了 `summarize`，且全量测试
耗时约 6 分钟，与长标定并发会争 CPU、污染 K1 计时。历史 12 份报告保留 v1 不重生成，
故不受本次判定改动影响。

## 14. 待办

1. **root18 终验已完成并回填** §9.1 / §11.1（两轮同为 0.2109、`contractPass=false`）；
   结果只作为标定证据归档，**产品定稿保留 root16**（§11.3）。
2. root18 跑完后**重跑全量 `pytest -q`**（v2 改动后尚未在全量上验过），并复核
   ruff / mypy / desktop_smoke；期间不得与标定并发。
3. 中级 root3 下 d2 达成率（16 局面 × 5 手）尚未实测；须在**独占干净进程**跑
   （见 §12.3 ⑦），局面冻结为 FEN/JSON 快照。
4. `medium↔hard` 未做 n=64 最终验收（仅有早期
   `2026-11-09-hard-vs-medium.jsonl`），不得把 §10 的趋势写成既成事实。
5. **K5 人工试玩 3–5 人 × 各 5 局未测**；K4 点估计出带、不可认证，不推翻 K5；
   两条结论分别陈述，K5 出结果前不得宣称「入门档已验收」。
6. 复核全部标定相关 commit 后决定是否 push（截至本文撰写时均未 push）；
   `benchmarks/calibration_runs/` 下的报告与 checkpoint 不进版本库，
   但门禁工具 `_verify_n64_recompute.py` 已入库；数据证据链靠本文 §9 / §12 固化。
7. **K3-a 连送未达标**（A 最长 3–4 手、B 两轮均 3 手，硬线 ≤2）：本轮按预登记不再调参，列入 S5 观察项；汇报时必须与「计数达标」分开陈述，**不得写「K3-a 全达标」**。
