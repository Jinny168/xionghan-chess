# AI 基线 `2026-10-30`（规则五项改动后）

本目录是**测量快照**，不是配置、不是阈值。它记录"某一份代码 + 某一批局面"下的三组事实：
48s 深预算会选什么、12s 实际选什么、各层搜索到多深。

**换规则或换语料后，本目录整体作废，不得跨版本比较。**（见文末「用途声明」）

---

## 1. 取自哪个 commit

| 项 | 值 |
|---|---|
| 规范提交 | **`9c8d0bf`**（`fix(rules): 刺题覆盖改用 xfail(strict)`） |
| 基线实测提交 | `f513494`（`fix(rules): 删除失效题库题、夹具改名 62/120、楯不保护楯`） |
| 二者关系 | **`src/` 逐字节相同**，仅测试文件不同 |

证据：

```
$ git diff --stat f513494..9c8d0bf -- xionghan-chess-next/src
（无输出 = 零差异）

$ git diff --name-only f513494..9c8d0bf
xionghan-chess-next/tests/test_puzzle_coverage.py
```

两者只差一个测试文件（刺题覆盖改用 `xfail(strict)`），**不影响任何测量数值**。所有产物均在 `git archive f513494` 解出的干净副本中运行，**未在工作树上采样**。

---

## 2. 口径

### 2.1 语料 16（`base2_corpus16.json`）

`bench_roots.build_position` 确定性生成，`12 + 2 + 2`：

- `desktop_complete` seed 700–703 × plies {4, 8, 12} = 12
- `web` seed 700–701，plies 8 = 2
- `traditional` seed 700–701，plies 8 = 2

每条记 `id = sha1(position_key)[:16]` 与 `pieces/legal` 指纹。**要求并已确认 16/16 互异。**

### 2.2 评估 200（`base2_eval200.json`）

```
for profile in (desktop_complete, desktop_classic, web, traditional):
    for seed in 700..709:
        build_position(profile, seed, 12) → 取 states[2, 4, 6, 8, 10]
```

共 4 × 10 × 5 = 200 条，每条记 `red` / `black`（**6 位小数**，与历史基线精度一致）、`id`、`fp`、`src{profile,seed,stateIndex}`。

- **重放历史必须用 `game.move()`，不得用 `rules.apply_unchecked`**——后者在发生吃子的线上会漂（实测 seed 707 的 `states[6]/[8]/[10]` 与基线不符）。
- 值比较前必须 `round(x, 6)`，否则会把"落盘舍入"误报成"行为变化"。

### 2.3 含将军 20（`base2_check20.json`）

**筛法（可复算）**：从 2.2 那 200 个局面出发，逐个枚举**一层合法后继**，筛「`black` 被将且 `red` 未被将」；按 `(profile 顺序, seed, 状态索引, 走法排序)` 取前 20。

- **A 段** = seed 700–709（与 eval200 同批）；**B 段** = 不足 20 才启动，扩展 seed 710–729。
- 每条记 `id` / `fp` / `red` / `black` / `sum` / `pass`(`A:seed700-709` | `B:seed710-729`) / `src{profile,seed,stateIndex,move}`。
- 本批 **A 段出 20 条、B 段 0 条**（未动用兜底）。

### 2.4 `t_d2` 16 局面（`base2_td2_16.json`）

- 配置：`hard` / `root_limit=18` / `randomness=0`
- 预算：`AI_TIME_SCALE=2.5` → 30s；**d2 一完成立即 abort**（不白等满 30s）
- 每局面 3 次，记 `d1`、`d2` 完成时刻与中位

### 2.5 深参照与 12s 选点（`base2_ref8.json` / `base2_sel8.json`）

- 深参照：`AI_TIME_SCALE=4` → 48s，1 次
- 12s 选点：`AI_TIME_SCALE=1` → 12s，3 次
- 覆盖面：corpus16 **前 8**（`desktop_complete` seed 700–703 × plies 4, 8），**另附加 `9d4dda34`（plies 12）**以便给出它的深度差；文件内用 `in_eight` 标记区分。

### 2.6 机动性（`base2_mobility.json`）

13 枚非王子各单独置于空盘中心 `(6,6)`，两王置于红 `(12,6)` / 黑 `(0,0)`（不同行不同列，不构成照面），数该子 `legal_moves` 数；兵另测 `(5,6)`。另记"A 完整初始局面下红方首着各子着数"。

---

## 3. 已知取舍（非缺陷，用户已确认保留）

刺（纯前进一格）在 20 局 median-move 样本里，**A 翼 10/20、B 翼 9/20 到 50 手仍不可动**（物理上走不了，不只是没被选用）；实际被策略走出 2/20、1/20。**该取舍已由用户确认保留**，不作为缺陷登记。

三张口径并列，勿混用：

| 子 | ①可动过（策略无关） | ②真走出（policy） | ③被吃 |
|---|---|---|---|
| 甲 A (12,2) | 20/20，中位 17 | 11/20，中位 25 | 0 |
| 甲 B (12,10) | 17/20，中位 30 | 2/20，中位 24 | 0 |
| 刺 A (12,3) | 10/20，中位 23 | 2/20，中位 34 | 0 |
| 刺 B (12,9) | 11/20，中位 20 | 1/20，中位 11 | 0 |

限定：驱动策略是 median-move **机械策略**，不代表人类或强 AI；50 手截断。③ 全为 0，故 ② 未被"被吃"污染，无需打折。

---

## 4. 已知局限

1. **`check20` 分布偏斜**：`desktop_complete 15 / desktop_classic 5 / web 0 / traditional 0`。抽样按固定顺序取前 20 所致；其用途是**覆盖 `in_check` 分支**，不代表各档比例。
2. **`web` 档 0 条**：4 档案 × 10 seed × 12 状态、枚举全部一层着法，未出现「`black` 被将且 `red` 未被将」——这是 web 档局面特性的客观结果，不是筛选 bug。`base2_check20_side_balanced.json`（每档案上限 5 条，共 15 条）作为"`−60` 不依赖档案"的旁证保留，**不进主基线**。
3. **2 个局面对 12s 只到 d1**：

   | 局面 | 12s | 48s | 深度差 |
   |---|---|---|---|
   | `c54bc97a7adbff20`（62/103） | d1 `7,12-5,12` | d2 `5,10-4,10` | 1 |
   | `9d4dda3433f85239`（62/89） | d1 `7,12-5,12` | d3 `11,10-6,10` | 2 |

   两者在 12s 下 3 次都选同一手，**不是抖动，是"只搜到 d1"这一事实本身决定选点**。引用一致性类指标时必须单独标注，不要让它们混进分母解释。`c54bc97a` 在 48s 也只到 d2（该局面本身极慢）。
4. **生成脚本已随目录入仓**（`scripts/`），但它们依赖 `git archive` 解出的代码根；直接在工作树上跑会拿到不同规则。
5. 样本量小：语料 16、评估 200、将军 20、`t_d2` 16、参照 8(+1)。**这些数字用于回归比对，不用于统计推断。**

---

## 5. 用途声明

**本目录是"将来任何评估/排序改动"的对照组，不是"棋力合格线"。**

- 它记录的是客观事实：48s 选什么、12s 选什么、深度到哪一层、评估值是多少。
- 改动后，用**同一批 `id16`、同一口径**重跑，逐位对比是否漂移即可。
- 它**不表达**"命中 7/8 合格"或"2 个未命中不合格"——那是性质完全不同的判断。
- **换规则或换语料后本目录整体作废；严禁把本目录的数字与其它版本/其它语料相减或相比。**

---

## 文件清单

| 文件 | 内容 | 关键数字 |
|---|---|---|
| `base2_corpus16.json` | 语料 16 局面 | 16/16 互异 |
| `base2_eval200.json` | 评估 200 条 | 零和 200/200；`sha256=3b1c779222743c7b` |
| `base2_check20.json` | 将军 20 条 | `sum=−60` 20/20 |
| `base2_check20_side_balanced.json` | 均衡版将军 15 条（旁证） | `sum=−60` 15/15，web 0 条 |
| `base2_td2_16.json` | 16 局面 `t_d2` ×3 | 中位-of-中位 **4.458s**；分档 4.815 / 2.521 / 0.675s |
| `base2_ref8.json` | 9 条深参照（48s） | 8 条 d3、`c54bc97a` 为 d2 |
| `base2_sel8.json` | 9 条 12s 选点 ×3 | 9 局面 ×3 次全部一致；前 8 中 7 个与参照同手 |
| `base2_mobility.json` | 14 型机动性 + 初始首着 | 檑 46 / 俥 23 / 炮 23 / 尉 0 / 楯 0 |
| `base2_unfreeze_side.json` | 甲/刺 可动性原始逐局 | 见 §3 ① |
| `base2_unfreeze_nocapture_side.json` | 按 piece id 追踪的主动走出 | 见 §3 ②③ |
| `base2_first_move_side.json` | 按走棋记录统计的首次出动 | 见 §3 ② |
| `scripts/stage1_baseline.py` | 语料/评估/将军/机动性 | — |
| `scripts/stage2_td2.py` | `t_d2` | — |
| `scripts/stage3.py` | 深参照 + 12s 选点 | — |
| `scripts/stage{1,2,3}_run.log` | 三段原始运行日志 | — |

### 复跑方式

```bash
cd /tmp && mkdir -p base2 && git -C <repo> archive 9c8d0bf | tar -x -C base2
python benchmarks/baseline_2026-10-30/scripts/stage1_baseline.py \
       /tmp/base2/xionghan-chess-next  /tmp/out
python benchmarks/baseline_2026-10-30/scripts/stage2_td2.py \
       /tmp/base2/xionghan-chess-next  /tmp/out/base2_td2_16.json
python benchmarks/baseline_2026-10-30/scripts/stage3.py \
       /tmp/base2/xionghan-chess-next  /tmp/out/base2_ref8.json /tmp/out/base2_sel8.json
```

> `stage1_baseline.py` 的 `--smoke` 只跑 1 个 seed，用于验证管线，**产出不能当基线**。
