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

## 3. Windows asyncio Proactor 连接清理回调噪声（首次修复无效，重修中）

- **现象**：uvicorn 日志中段偶发
  `Exception in callback _ProactorBasePipeTransport._call_connection_lost(None)` →
  `ConnectionResetError: [WinError 10054] 远程主机强迫关闭了一个现有的连接`。
  日志统计 **1 条 Traceback、0 个 5xx**，不影响任何响应。
- **首次修复为何无效（`2f136aa`）**：用的是
  `asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())`。
  但 uvicorn 0.36+ 由 `Server.run()` 显式传 `loop_factory` 给 `asyncio.Runner`
  （见 `uvicorn/server.py`、`uvicorn/_compat.py`），**Runner 拿到显式 factory 后不查全局 policy**；
  而 `uvicorn/loops/asyncio.py` 在 Windows 上直接返回 `asyncio.ProactorEventLoop`。
  ⇒ 那三行是**死代码**。实测三路对照：普通启动 **3 次**噪声 + 1 条 Traceback；
  先设 policy 再 `uvicorn.run()` **同样 3 次 + 1 条（一字不差）**；真 Selector factory **0 次 + 0 条**。
- **正解**：`uvicorn.run(..., loop="xionghan_chess.service.app:_selector_loop_factory")`，
  工厂返回 `asyncio.SelectorEventLoop()`；`Config.get_loop_factory()` 对不在内置表里的值
  会 `import_from_string`，属官方支持路径。
- **复现姿势（重要）**：必须用「客户端 reload / 正常关闭 keep-alive 连接」；
  用 raw socket RST 强断**掐不出**这个噪声（实测 24 次 0 命中）。
- **为何不阻断**：不影响响应、5xx 为 0。
- **状态**：修复待落地——`2f136aa` 的写法已确认无效，**不得当作已修**。
