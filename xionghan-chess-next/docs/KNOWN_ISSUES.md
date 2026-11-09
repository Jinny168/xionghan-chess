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

## 2. S4 档位重标定的两项未完成实测（不阻塞当前版本）

- **hard 中局耗时已实测（2026-11-09）**：hard vs medium 40 手 × 2 局，
  `n=40, median 15.47 / p95 31.79 / max 40.54 s`，cap 120 s 未绑定（wall/nodes 均为 0）；
  `EXPECTED_MOVE_SECONDS[hard]` 已回填 **15.5 s**，报告见
  `benchmarks/hard_probe_40ply_2026-11-09.json`。
- **`max_nodes` 三档全关**：中局节点数没有可靠分布，半成品值会确定性截断；
  工具 `scripts/measure_node_budget.py` 保留，回填时需同步 `level_targets` 与 `CONFIGS`（T6 会红）。
- **n=32/64 胜率验收未跑**：单侧判据已定（点估计 ≥0.60 且 Wilson 下界 ≥0.50；n=32 ≥22 胜、
  n=64 ≥40 胜），但 1.7 h+ 的机时未占用；在跑完前，任何文档不得写"档位胜率已验证"。

处置：等一次大机时窗口跑 `beginner vs medium` n=32；跑完把本条目删除。
