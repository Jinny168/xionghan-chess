# AI 档位（三档）与并档说明

> 生效版本：main（合并 master S3–S5 之后）。代码单一来源：
> `core/ai.py` 的 `PUBLIC_DIFFICULTIES`、`CONFIGS`、`LEGACY_DIFFICULTY_ALIASES`。

## 1. 对外三档

| 档位 | 枚举 | 深度 | 每手预算 | randomness | 定位 |
|---|---|---|---|---|---|
| 入门 | `beginner` | d2 | 0.5s | 0.55（取样弱化） | 会漏攻击、白送子 |
| 中级 | `medium` | d6 | 5.0s | 0.05 | 接近满强度，2.5s 后基本饱和 |
| 高级 | `hard` | d8 | 12.0s | 0 | 最强常规搜索 |

**并档不重标**：三档沿用 main 现值，强度未改；Elo 标定留到下一轮。

## 2. 旧名兼容映射

| 旧名 | 归一结果 | 理由 |
|---|---|---|
| `easy` | `beginner` | easy 是 1.5s/d4/randomness 0.35；medium 是 5s/d6/0.05。抬到 medium 等于**变强**，并入入门才不坑人 |
| `expert` | `hard` | expert 是 hard 的固定 d3 变体；实测选点与 hard 全同，保留独立档只增加维护面 |
| `master` | `hard` | master 对 hard 50 局 **0 胜**（MCTS 在产品时间预算下打不过 d8）；不再作为产品档位 |

- 字符串入口统一走 `normalize_difficulty()`：只做 `strip().lower()` + 查表；未知值原样
  返回，由 `Difficulty(...)` 抛错。
- 旧配置、旧房间快照、旧棋谱里的六个名字都能载入；**不抛错**。
- `EASY / EXPERT / MASTER` 三个枚举成员保留，但 `CONFIGS` 条目是**同一对象别名**
  （`CONFIGS[MASTER] is CONFIGS[HARD]`），不是数值副本——复制会制造两份真相。

## 3. MCTS 下线

`core/mcts.py` 与 `tests/test_mcts_integration.py` 保留（研究/基准路径），但
`ChessAI` **不再按档位分派**到 MCTS：`MASTER` 只是旧配置兼容名。产品链路只剩
alpha-beta 常规搜索；MCTS 只能显式构造 `MCTS(...)` 使用。

## 4. UI / Web

- 桌面设置下拉、Web `#difficultySelect` 均只列 `PUBLIC_DIFFICULTIES`（三项）。
- 旧值不是「未知」：桌面会插入不可选提示「初级（已并入入门）」「专家（已并入高级）」
  「大师（已并入高级）」；真正不认识的值才走「未知档位 + 回落中级」。
- `locales/*.json` 的 `difficulty.easy/expert/master` 文案保留，用于旧档提示；
  三档主文案的秒数与 `CONFIGS` 逐档严格比对（`test_desktop_difficulty_labels.py`）。

## 5. 下一轮 Elo 标定计划

- 目标胜率区间：**65–75%**（相邻档位，高对低）。
- 样本：每对 **n=50**（红黑各半、开局书抽样），报告 Wilson 95% CI；CI 下界 >50%
  才算「档位可分」。
- 重点对：beginner↔medium、medium↔hard；hard 对旧 expert/master 只做回归，不作为档位。
- 若 CI 重叠：优先调 `randomness/sample_margin`（入门）与 `depth/root_limit`（高级），
  不同时动预算与取样，保证归因单一。

## 6. `depth` 语义：上限，不是实际搜索深度（S4 结论）

产品三档的 `SearchConfig.depth` 只作为迭代加深的**外层上限**：

```text
for depth in range(1, cfg.depth + 1):   # cfg.depth 是"最多允许几层"
    _root(... deadline ...)             # 每个节点前 _guard(deadline) → 到点抛 SearchTimeout
```

`completed_depth` 只在某一层 `_root` **完整返回**后才更新；墙钟到点抛 `SearchTimeout`，
`choose_move` 保留 best-so-far 退出。因此：

- **medium 配 d6、hard 配 d8，在产品 cap（5s / 12s）下开局实测都只完成 d2**
  （各一手：medium `completed_depth=2 / nodes=157`、hard `completed_depth=2 / nodes=466`，
  `bound_reason` 均为 `wall`）；
- 档位差异来自**预算/cap 与取样参数**，不是"搜到 d6/d8"；
- **后续若要让 d6/d8 真正生效，必须先提高 cap 或改提前收手策略；否则调 `depth` 是空操作。**

## 7. 标定数据引用口径（product vs target）

- **product**：数据是 **wall-bound**（冒烟 wall 占比 100%）。只引用**胜率与 Wilson CI**，
  **不引用"完成深度"作为强度证据**；`wallClean` 只记录，不作为"不可引用"的硬门。
  硬门只剩：`zeroDepthMoves == 0`、`nodes 截断占比 ≤ 2%`。
- **target**（S4-2b 提案表）：预算是按"能跑完目标深度"给的，`wallClean` 仍是硬门。
- 每局 JSONL 现在带 `a/b_completed_depth`（该方全部着法的 `completed_depth` 均值，
  保留 2 位；MCTS 路径不参与）与 `a/b_wall_moves`，可直接审计"实际完成几层"。
