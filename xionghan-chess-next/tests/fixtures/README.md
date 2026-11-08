# 测试夹具（局面快照）

## 为什么要有这个目录

自动生成的基准局面**不能只靠 `seed + plies` 复现**：自对弈路径依赖 `CONFIGS`，
参数一变走的就不是同一个局面（实例：同名 `L6` 从 62/129 变成 62/85）。
把局面固化成快照放进版本库，本身就是测量纪律的一部分。

## 测量纪律 / 正负对照用法

见 [`positions/README.md`](positions/README.md)（单一来源，避免两处维护同一段纪律）。

## 后续：软上限验收样例（供「硬结算点」实现时使用）

```
medium time_limit=5.0s，旧快照 L6(62/129)：实测 t_d2=5.45s 仍返回 completed_depth=2。
机制：deadline 在 choose_move 里设定；_guard 只在 _search/_quiescence 入口与 _root
      每个子节点前检查，故最后一个根着法可越过 deadline 跑完整棵子树才退出，
      越界量 ≈ 一个根着法的静态搜索耗时（实测 0.1–0.5s）。
判据：硬检查上线后，同一局面同一配置的 t_d2 必须 ≤ 5.0s，否则不算通过。
```

## 文件格式

`positions/*.json`：`{ "fingerprint": {"pieces": 62, "legal": 85}, "note": "...", "state": { GameState.to_dict() } }`
加载方式见 `tests/test_fixture_positions.py`（只校验能加载与指纹，**不跑搜索**）。
