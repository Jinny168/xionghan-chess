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
- **`medium↔hard` 未做 n=64 最终验收**：仅有早期 `2026-11-09-hard-vs-medium.jsonl`。
- **`max_nodes` 三档全关**：中局节点数没有可靠分布，半成品值会确定性截断；
  工具 `scripts/measure_node_budget.py` 保留，回填时需同步 `level_targets` 与 `CONFIGS`。
- **`EXPECTED_MOVE_SECONDS` 现为 0.7 / 3.0 / 7.0**（S4 设计预估；hard 实测 median 8.46s，
  见 `docs/AI_TIERS.md` §13）。旧的 `15.5s` 是 2026-11-09 旧配置的实测，已不适用。
- **K3-a 连送未达标**：A 最长 3–4 手、B 两轮均 3 手，硬线 ≤2；按预登记本轮不调参，
  列入 S5 观察项（详见 `docs/AI_TIERS.md` §8 的 K3-a 注）。

## 3. 400 文案暴露 6 个旧档位名（D-2，建议级）

- **现象**：`POST /api/rooms` 传非法难度时，FastAPI 默认文案列出
  `'beginner','easy','medium','hard','expert' or 'master'` 六个值。
- **影响**：旧档名本应只是兼容层，对外暴露等于把「六个档位」重新教给玩家，与三档口径不一致。
- **建议处理**：兼容层保留 6 值（旧存档需要），但对外报错只说三档，或改用自定义枚举校验文案。
- **为何不阻断**：仅影响报错文案，不影响任何正常路径；本轮交付不处理。

## 4. 建房路径未 normalize，`room.ai_difficulty` 可能保留旧枚举（D-3，建议级）

- **现象**：`service/app.py` 建房时直接传 `request.difficulty`，未调用
  `desktop/app.py:654` 那条 `normalize_difficulty`；因此 `room.ai_difficulty` 可能是
  `Difficulty.EASY`。当前行为等价，靠 `core/ai.py:131` 的 `CONFIGS[EASY] = CONFIGS[BEGINNER]`
  **同一对象别名**兜住。
- **影响**：若日后有人写 `if room.ai_difficulty is Difficulty.BEGINNER` 之类的 identity 比较，
  会误判。当前全库无此类比较点。
- **建议处理**：在 `manager.create` 入口做一次 `Difficulty(normalize_difficulty(...))`，
  把「别名等价」升级为「值等价」。
- **为何不阻断**：行为当前完全一致，属潜伏雷而非现行缺陷。
