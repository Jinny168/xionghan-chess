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
