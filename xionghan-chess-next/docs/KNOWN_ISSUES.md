# 已知问题

只记**还没修、但已有明确处置**的问题；修好后把对应条目删掉，不要在这里堆历史。

## 1. 整跑 pytest 时训练冒烟触发原生崩溃

- **现象**：`pytest tests/` 跑到最后一个文件 `tests/test_training_pipeline.py` 的
  `test_numpy_policy_value_training_smoke` 时，进程在原生层直接退出（无 traceback、无汇总行）。
- **复现条件**：整跑 `pytest tests/`（约 790 条）且该用例排在最后；`git stash` 回到 `512cb56` 仍复现。
  逐文件跑、分段跑、或把该用例排到最前跑都通过 —— 因此不是断言逻辑问题，
  疑似长期累积的进程状态（Qt 对象 / 棋子位图缓存）与随后一次大块 numpy 分配的内存交互，**根因未定**。
- **当前处置**：把冒烟体抽到 `tests/_smoke_training_impl.py`，由 `subprocess` 起干净解释器执行，
  断言退出码与 `TRAINING_SMOKE_OK` 标记。**覆盖保留**，不跳过、不摘出门禁。
  若换机器后连子进程也崩，说明是机器内存/驱动层，届时再单独定位。

## 2. S4 档位重标定：n=64 已跑完，剩余未做项

- **胜率验收已完成（2026-11-11，两轮 n=64）**：beginner vs medium 为 root16 `13-50-1`、
  root18 `12-49-3`；A 得分率两轮均 **0.2109**、强档 **0.7891**；K4 点估计出带、
  **不可认证**（`contractPass=false`）。详见 `docs/AI_TIERS.md` §9 / §11。
  **准确表述是「已跑、出带、不可认证」**——不要写「未跑」，也不要写「档位胜率已验证」。
- **`medium↔hard` n=64 明确不做（2026-11-11 用户裁定）**：按历史 `2026-11-09-hard-vs-medium.jsonl`
  （2 局、46 手/局、431s/局）估算，64 局约 **7.7 小时**；按真实手数（约 129 手/局）外推更可能
  **10–15 小时**，与 `beginner↔medium`（约 100 分钟）不是一个量级。**这是「不做」，不是「待做」**：
  属成本过高且非阻断，档间距若需验收应另开机时窗口，不应与收尾混在一起。
  （hard 的 K1 已有实测：median 8.46s，见 `docs/AI_TIERS.md` §13。）
- **`max_nodes` 三档全关**：中局节点数没有可靠分布，半成品值会确定性截断；
  工具 `scripts/measure_node_budget.py` 保留，回填时需同步 `level_targets` 与 `CONFIGS`。
- **`EXPECTED_MOVE_SECONDS` 现为 0.7 / 3.0 / 7.0**（S4 设计预估；hard 实测 median 8.46s，
  见 `docs/AI_TIERS.md` §13）。旧的 `15.5s` 是 2026-11-09 旧配置的实测，已不适用。
- **K3-a 连送未达标**：A 最长 3–4 手、B 两轮均 3 手，硬线 ≤2；按预登记本轮不调参，
  列入 S5 观察项（详见 `docs/AI_TIERS.md` §8 的 K3-a 注）。

## 3. 跨端 fixtures 体积 24.8 MB / 份（不压缩，方案 1 为后续可选优化）

2026-11-12 兵三连 v3 三端对齐（commit `57b9584`）后，两份跨端 fixtures
`webapp/tests/fixtures/rules.json` 与 `webapp/.edgeone/assets/tests/fixtures/rules.json`
各 **24,768,257 B**（md5 相同），合计约 48 MB 入库。与实施前预估 5,618,631 B 差 4.4×。

**逐字段拆分（实测，闭合差 0 B）**：
```
24,768,257 = cases 5,569,175 + transitions 19,197,323 + 顶层包裹/manifest 1,759
transitions 19,197,323 = positionCounts 12,342,963 + 其余 transitions[] 6,854,360
```
- `removals`（本轮新增护栏）仅 347,477 B，印证了估算的 332,827 B；**不是膨胀源**。
- 49.83% 集中在 `transitions[].before.positionCounts`：本轮 `positionKey` 契约补齐
  `||pool:` + `||opt:rs3-p3l1-promo1-self1` 后，单个 key 从旧短串涨到约 800 B，
  848 个 transition × 平均 29 个 key（最多 50）≈ 12.3 MB。是**账本同源正确落地的连带放大**，
  不是 bug；删/折叠它会削弱 transitions 回放对三次重复判和的覆盖。

**当前处置：不压缩**（单文件远低于 GitHub 100 MB 上限；55s 完整重生成放 slow job，
不阻塞 PR；保留 positionCounts 以维持账本覆盖）。**方案 1（折叠 positionCounts 为 digest
或只留当前 key 的计数值）列为后续可选优化**，可省约 12.3 MB / 份。
前置条件（必须满足才动）：先另跑 848 个 transition 验证 `settle` 集合不变 —— `Game.move`
经 `stateFromDict(item.before)` 重建状态，若 before 缺 `positionCounts` 会走默认 `{}`，
**可能影响三次重复判和**，属规则回放语义改动，不是纯序列化优化，不可顺手做。
方案 2（bulk/probe 拆分）只省约 300 KB 且会破坏「removals 键集合恒等于 legal」契约，不采纳。

## 4. CI pytest 失败注解漏报用例名（不阻断，非本轮引入）

`ci.yml` 的 pytest step 用 `grep -E "^(FAILED|ERROR) "` 把失败用例转成 `::error::` 注解。
当 pytest 输出带 ANSI 颜色码时（CI runner 上可能发生），FAILED 行首不是字面 `FAILED`，
该 grep 匹配不到 → 注解只剩「Process completed with exit code 1」，根因在匿名日志里不可见。
2026-11-12 的 run #176 即此形态：test job 42s exit 1 却无 FAILED 注解。
**当前处置**：靠本地同口径复现定位（当时为版本源不一致，三条红，已在 commit `76de99b` 修掉，
本地复现 `1442 passed / 0 failed`）。**待改进**：改用 `pytest --color=no`，或让正则容忍
ANSI 转义码；未改，因为不影响判定本身（exit code 仍正确非零），只影响日志可读性。
