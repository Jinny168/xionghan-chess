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
