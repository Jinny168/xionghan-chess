# AI 基线 `2026-10-31`（54 子布局 · 12 型棋子）

本目录是**测量快照**，不是配置、不是阈值。

> **与 `baseline_2026-10-30` 不可跨版本比较。** 那一轮是 62 子 / 14 型（含甲、楯），本轮是 54 子 / 12 型；局面、语料、`position_key` 全变。任何"比上轮快了多少/命中多少"的算法都是跨口径相减。

---

## 1. 取自哪个 commit

| 项 | 值 |
|---|---|
| 提交 | **`fd541b1`**（`docs: 清理残留旧规则（QA 图鉴数字、RULES 摘要、设计标记）`） |
| 运行环境 | `git archive fd541b1` 解出的干净副本，**未在脏工作树上采样** |
| 本轮规则差异 | ① 每方 27 / 全场 54 / **12 型**（甲、楯已软删）；② **射**吃子可越子（位移仍要求路径空）；③ 兵新增 `pawn_charge`、`pawn_three_line_capture`，**默认关，基线用默认配置** |

---

## 2. 口径（与 2026-10-30 轮逐条一致，便于纵向对齐）

### 2.1 语料 16（`base3_corpus16.json`）
`desktop_complete` seed 700–703 × plies {4,8,12} = 12，`web` 700–701 p8 = 2，`traditional` 700–701 p8 = 2。每条记 `id = sha1(position_key)[:16]` 与 `pieces/legal`。**16/16 互异。**

### 2.2 评估 200（`base3_eval200.json`）
4 profile × seed 700–709 × `build_position(profile,seed,12)`，取 `states[2,4,6,8,10]` = 200 条；`red`/`black` 记 6 位小数。

- **重放历史必须用 `game.move()`**，不得用 `rules.apply_unchecked`（后者在吃子线上会漂）。
- 比对前必须 `round(x, 6)`，否则会把落盘舍入误报成行为变化。

### 2.3 含将军 20（`base3_check20.json`）
从 2.2 的 200 个局面枚举**一层合法后继**，筛「`black` 被将且 `red` 未被将」，按 `(profile 顺序, seed, 状态索引, 走法排序)` 取前 20。A 段 = seed 700–709；不足 20 才启动 B 段（710–729）。每条记 `pass` 与 `src{profile,seed,stateIndex,move}`。

### 2.4 `t_d2` 16（`base3_td2_16.json`）
`hard` / `root_limit=18` / `randomness=0`；`AI_TIME_SCALE=2.5` → 30s 预算，**d2 一完成立即 abort**；每局面 3 次。

### 2.5 深参照与 12s 选点（`base3_ref8.json` / `base3_sel8.json`）
corpus16 前 8（`desktop_complete` seed 700–703 × plies 4,8）+ 附加 `c5e21ca3`（plies 12，文件内 `in_eight=false`）。深参照 `AI_TIME_SCALE=4` → 48s ×1；12s 选点 ×3。

### 2.6 机动性 12 型（`base3_mobility.json`）
各子单独置于空盘 `(6,6)`、两王置红 `(12,6)` / 黑 `(0,0)`（不同行列，不构成照面）；兵另测 `(5,6)`。另记初始局面红方首着各子着数。

### 2.7 开局快照（`base3_opening_snapshot.json`）
初始局面每方 27 子的**完整位置清单** + 各型数量。用于文档与后续基线引用，避免"27/54/12 靠口头传"。

---

## 3. 关键数字

| 项 | 值 |
|---|---|
| 语料 | 16/16 互异；`desktop_complete` 多为 54 子（少数 53 子 = 已有吃子） |
| 评估 200 | 零和 **200/200**；`sha256(json,sort_keys)=12655bc918b3c70e` |
| 将军 20 | `sum=−60` **20/20**；A 段出 20、B 段 0 |
| `t_d2` | 中位 **3.271s**，均值 3.099s，范围 0.388–5.358s；**16/16 均完成 d2** |
| 12s 深度分布 | **d2×8、d3×1**（`47901cf39ffcc18e` 在 12s 内到 d3） |
| 深参照深度 | **d3×8、d4×1**（同一局面 `47901cf3` 48s 到 **d4**） |
| 与深参照同手（前 8） | **2/8** |

`t_d2` 分档中位：`desktop_complete` 3.679s（12 个）、`web` 2.190s（2 个）、`traditional` 0.489s（2 个）。

---

## 4. 已知局限

1. **`check20` 分布偏斜**：`desktop_classic 12 / desktop_complete 8 / web 0 / traditional 0`。按固定顺序取前 20 所致；用途是**覆盖 `in_check` 分支**，不代表各档比例。
2. **`web` 档 0 条**：4 档案 × 10 seed × 12 状态、枚举全部一层着法，未出现「`black` 被将且 `red` 未被将」——web 档局面特性的客观结果，不是筛选 bug。
3. **本轮没有「12s 只到 d1」的局面**：9 条全部 ≥d2，其中 1 条到 d3。上一轮（62 子）有两个局面卡在 d1（`c54bc97a`、`9d4dda34`），**那是另一套布局，不能据此说"性能改善了"**——局面本身不同。
4. 样本量小：语料 16、评估 200、将军 20、`t_d2` 16、参照 8(+1)。**用于回归比对，不用于统计推断。**
5. 与深参照同手只有 2/8，**这不是"棋力差"**：深参照本身是 48s 内到 d3/d4，而 12s 多数只到 d2；层差本身就足以改手。

---

## 5. 用途声明

**本目录是"将来任何评估/排序/规则改动"的对照组，不是"棋力合格线"。**

- 改动后用**同一批 `id16`、同一口径**重跑，逐位对比是否漂移；
- 它**不表达**"命中 2/8 不合格"或"t_d2 3.27s 合格"；
- **换规则、换布局或换语料后本目录整体作废**；严禁与其它版本数字相减。

---

## 文件清单

| 文件 | 内容 |
|---|---|
| `base3_corpus16.json` | 语料 16 局面（id16 + 指纹） |
| `base3_eval200.json` | 评估 200 条（6 位小数） |
| `base3_check20.json` | 将军 20 条（`sum=−60`） |
| `base3_td2_16.json` | 16 局面 `t_d2` ×3 |
| `base3_ref8.json` | 9 条 48s 深参照 |
| `base3_sel8.json` | 9 条 12s 选点 ×3 |
| `base3_mobility.json` | 12 型机动性 + 初始首着 |
| `base3_opening_snapshot.json` | 初始 54 子阵型快照 |
| `scripts/stage1_baseline.py` | 语料/评估/将军/机动性/开局快照 |
| `scripts/stage2_td2.py` | `t_d2` |
| `scripts/stage3.py` | 深参照 + 12s 选点 |

### 复跑方式

```bash
mkdir -p /tmp/b && git -C <repo> archive fd541b1 | tar -x -C /tmp/b
python .../scripts/stage1_baseline.py /tmp/b/xionghan-chess-next <out_dir>
python .../scripts/stage2_td2.py       /tmp/b/xionghan-chess-next <out_dir>/base3_td2_16.json
python .../scripts/stage3.py           /tmp/b/xionghan-chess-next <out_dir>/base3_ref8.json <out_dir>/base3_sel8.json
```

> **2026-10-31 起刺移除**：当前布局为 **50 子 / 11 型**；本目录语料仍基于 54 子，**不可与当前布局跨版本比较**（数据保留作历史对照）。
