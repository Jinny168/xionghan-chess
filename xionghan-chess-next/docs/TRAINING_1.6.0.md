# v1.6.0 MCTS 自博弈与神经网络训练

## 设计边界

新版流水线复用 `Game`、`RulesEngine`、`GameState` 和纯 MCTS，不再依赖旧版 Redis、pickle 队列或独立棋盘规则。训练依赖是可选的 NumPy，不进入桌面、Web、服务端和 Android 运行依赖。

稳定协议：

- 样本格式：UTF-8 JSONL，`schema=1`；
- 状态编码：29 × 13 × 13（红黑双方 14 类棋子平面，加当前行棋方平面）；
- 动作空间：`169 × 169 = 28561`，升变类型在推理时由合法走法掩码消歧；
- 监督信号：MCTS 选择的动作和最终胜负值 `-1/0/1`；
- 模型：单隐藏层 NumPy policy/value MLP，模型格式为压缩 NPZ。

## 安装与运行

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements\train.txt
.\.venv\Scripts\python.exe scripts\train_ai.py --games 10 --simulations 64 --epochs 5
```

默认输出：

- `training-data/selfplay.jsonl`
- `training-data/policy-value-v1.npz`

`training-data/` 已加入 `.gitignore`。生产训练应保留数据集、模型、命令参数、Git revision 和评估结果的外部版本记录。

## AI 对弈基准

正式命令：

```powershell
.\.venv\Scripts\python.exe scripts\benchmark_ai.py --games 50 --max-plies 240 --output docs\AI_BENCHMARK_1.6.0_full.json
```

只有 `completedGames >= 50`、大师总胜率不低于 55%，且大师单步最大耗时不超过 12 秒，才满足规划验收。本轮 `AI_BENCHMARK_1.6.0_screening.json` 是 2 ply、2 simulations 的快速筛查，50 局均经截断裁定，只证明批处理链路和耗时采集可用，不代表棋力验收通过。
