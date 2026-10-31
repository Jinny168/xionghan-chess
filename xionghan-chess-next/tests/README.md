# tests/ 说明

两个门禁口径（CI 主 job 与独立 slow job 都用这两条）：

```bash
python -m pytest tests/ -m "not slow"   # 默认门禁，约 85–95s
python -m pytest tests/ -m "slow"       # 专家档 14 条深度用例 + 性能护栏
```

改**评估 / 走法排序 / 搜索参数 / 难度参数**之后必须跑全量（`-m slow`）。

## 对拍用例变更记录

`tests/test_cross_engine.py` 的条数不是"越多越好"，但**每一次减少都要能解释**。
下面按时间倒序记录，判据一律是函数名 diff（可复算）：

```bash
git show <old>:./tests/test_cross_engine.py | grep -oE "^def (test_[a-z0-9_]+)" | sort > /tmp/old.txt
grep -oE "^def (test_[a-z0-9_]+)" tests/test_cross_engine.py | sort > /tmp/new.txt
comm -23 /tmp/old.txt /tmp/new.txt   # 删除
comm -13 /tmp/old.txt /tmp/new.txt   # 新增
```

### B 阶段（改色）的判据口径

**B 允许像素变化，但必须能指出变化落在哪个区域。** 一个"总共 N 个像素变了"的数字不足以判断改对了没有——
可能是改的那处，也可能是别处被带崩了。所以 B 的验收是：

```bash
python scripts/theme_pixel_baseline.py --diff-report
# classic  合计   1234 px | 横幅 1200  棋盘 34
```

判据：
1. 预期改动的区域**有**差异（改了半天 0 差异 = 没生效）；
2. 非预期区域**为 0**（或只落在噪声底内）；
3. 只影响该改动覆盖的主题（如只改 `classic` 的键，则 green/blue/purple/dark 必须全 0）。

区域由运行时控件几何切分：`标题栏/横幅` / `棋盘` / `侧栏` / `其它`（棋盘外阴影与留白）。

### 2026-10-31 · 定向 removals 对拍（79 ⇒ 81）

批量门禁只比 `legalAll` + `inCheck`。**三连吃子这类"只改变移走哪些子、不改变合法着集合"的规则，
批量对拍一条都不会红** —— 所以补了 2 条**定向**对拍，用探针已有的 `capturedByMove` 支路
（一次请求只算指定的一步，不改批量契约、不变慢）：

1. `test_three_line_capture_parity_when_the_moved_pawn_joins_the_line`：移动兵参与成线 → 两侧都吃那枚士；
2. `test_three_line_capture_parity_ignores_a_far_line`：走无关兵、远处已成线 → 两侧都为空。

两条都**先断言"非空 / 为空"再比相等** —— 只比相等的话两边都返回 `[]` 也会绿。

### 2026-10-31 · 甲/楯/刺硬删除 → 87 ⇒ **79**

净减 8（删 9、新增 1）。**不是被削弱**：删掉的 9 条全部是专测这三个兵种的用例，
兵种从枚举里删掉后它们已无对象。

删除（9 条）：

| node id | 原因 |
|---|---|
| `test_armor_parity_sliding_then_line_capture` | 甲删除 |
| `test_armor_line_squeeze_capture_parity` | 甲的成线吃删除（机制只留兵三连 `three_line`） |
| `test_shield_parity_jump_one_piece_orthogonal_only` | 楯删除 |
| `test_shield_blocks_capture_of_protected_piece_parity` | 楯的保护机制删除 |
| `test_assassin_parity_slide_and_drag` | 刺删除 |
| `test_assassin_parity_when_soft_delete_is_lifted` | 同上（原来靠 `assassin_appear=True` 回滚触发） |
| `test_capture_kinds_match_across_engines` | 它枚举 capture kind 全集，含已删的 `armor_line` / `assassin_drag` |
| `test_all_piece_types_present_in_complete_profile_parity` | 断言"完整档 14 型"，现为 **11 型** |
| `test_promotion_never_offers_a_soft_deleted_type` | 造"池里只有已删兵种"的前提已不存在 |

新增（1 条）：

| node id | 作用 |
|---|---|
| `test_promotion_candidates_are_subset_of_enabled_types` | 接替上一条的**升变护栏**：改成人为关掉一个**在用**类型（`thunder_appear=False`），断言升变候选 ⊆ 启用集且两引擎一致 |

> 教训：跨端删方法/改名时，`grep` 必须用 `-i` 且同时搜 snake_case 与 camelCase。
> 本轮 70 条对拍红就是因为 `protectedByShield`（camelCase 大 S）没被 `SHIELD` / `shield` 匹配到，
> 方法定义行删了、调用还在 —— **静态搜索只能初筛，必须再真跑一次**（探针或 `node --check`）。
