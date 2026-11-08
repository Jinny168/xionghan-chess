# 匈汉象棋 v1.6.0 更新日志（已收尾）

## AI 与训练

- 新增第五档 AI 难度 `master`，以共享规则引擎驱动混合 MCTS。
- MCTS 已接入对手节点最小化、根节点安全吃子过滤、叶子局面估值和可选训练模型策略先验。
- 新增本地 JSONL 自博弈采样、29×13×13 状态编码、28561 动作协议和 NumPy policy/value 训练脚本。
- 训练模型可通过 `XH_MCTS_MODEL` 或默认 `training-data/policy-value-v1.npz` 被 master 档可选加载；无模型或无 NumPy 时自动退回启发式推理。

## 一致性与安全

- Android 离线规则探针直接执行生产 `offline.js`，与 Python Core 对比四配置初始局面、确定性局面和 14 类棋子局面。
- 服务端 WebSocket 状态广播改为 compact replay tail；入房和 HTTP 快照仍保留完整 replay，Web/桌面客户端可续接增量。
- Android Release manifest 关闭 `usesCleartextTraffic`，部署文档要求生产环境使用 HTTPS 反向代理。
- Web 动态 toast、云同步、分析、题库、背景图等路径补齐 i18n。
- 悔棋恢复快照后会清除提和、悔棋、重开协商状态并解除暂停。

## 工程

- 生产版本统一为 `1.6.0`，Android 为 `versionCode=8` / `versionName=1.6.0`。
- 误命名的 2.0.0 发布树已废止，当前 `git ls-files` 中无 2.0.0 路径。
- 自动化基线提升至 `125 passed, 1 warning`。

## 已知风险

- `master vs hard` 的 50 局非截断完整对弈胜率验收未在本轮交付窗口内完成；不得宣称 master 胜率已达到 55%。
- C-01/03/04/11/12 规则项仍待产品拍板，本版只补一致性测试，不擅自改变规则语义。
