# 三种对弈模式：定义、实现对照与验收清单

> 本文是三种 13×13 模式的**定义文件**。规则细节见 `PIECE_RULES.md`；
> 这里只回答"每种模式有什么棋子、开哪些规则、棋子是什么强度"。
> 实现基线：`src/xionghan_chess/core/profiles.py` 的 `COMPLETE_OPTIONS` / `CLASSIC_OPTIONS` / `WEB_OPTIONS`；
> 验收：`tests/test_rule_matrix.py`（92 条）。

## 1. 设计轴：两个正交维度

| 维度 | 取值 | 说明 |
|---|---|---|
| **棋子构成** | 全子 / 减子 | 全子 = 11 型 25 枚；减子 = 9 型 22 枚（去掉尉、巡） |
| **规则强度** | 全加强 / 传统回退 | 全加强 = 所有自定义规则开启；传统回退 = 士/象/马/兵/将按经典中国象棋 |

两轴正交，因此三种模式各占一格：

| 模式 | 档案 id | 棋子构成 | 规则强度 | 每方枚数 | 兵种数 |
|---|---|---|---|---|---|
| **完整模式** | `desktop_complete` | 全子 | 全加强 | 25 | 11 |
| **经典模式** | `desktop_classic` | 全子 | 传统回退 | 25 | 11 |
| **精简模式** | `web` | 减子 | 全加强 | 22 | 9 |

**完整 vs 经典只差规则，精简 vs 完整只差棋子** —— 换模式时用户只需理解一个变量。

## 2. 棋子属性矩阵（逐型）

"加强"列指完整/精简模式；"经典"列指经典模式。✔=允许，✘=禁止。

| 棋子 | 能力 | 加强（完整/精简） | 经典 | 依据 |
|---|---|---|---|---|
| 汉/汗 | 宫内斜走 | ✔ | ✘ | `king_diagonal_in_palace` |
| 汉/汗 | 出九宫 | ✔ | ✘ | `king_can_leave_palace` |
| 汉/汗 | 入敌九宫获胜 | ✔ | ✔ | `invasion_victory`（胜利条件，非棋子走法） |
| 仕/士 | 出九宫 | ✔ | ✘ | `advisor_can_leave_palace` |
| 仕/士 | 宫外直走一格 | ✔ | ✘ | `advisor_gain_straight_outside_palace` |
| 相/象 | 过长城阴山 | ✔ | ✘ | `elephant_can_cross_river` |
| 相/象 | 敌境横竖两格 | ✔ | ✘ | `elephant_gain_jump_two_enemy_territory` |
| 马 | 别马腿 | ✘（不别腿） | ✔（别腿） | `horse_blocked_by_leg` |
| 马 | 直走三格 | ✔ | ✘ | `horse_straight_three` |
| 马 | 直走三格仅移动 | ✘（可吃） | — | `horse_straight_three_move_only` |
| 车 | — | 无开关 | 同左 | 直线任意距离，两模式一致 |
| 炮 | — | 无开关 | 同左 | 隔一子吃，两模式一致 |
| 兵/卒 | 敌境前快速行军 | ✔ | ✘ | `pawn_fast_move_before_enemy_territory` |
| 兵/卒 | 过阴山横走 | ✔ | ✔ | 无开关（经典象棋本来就有） |
| 兵/卒 | 底线后退一格 | ✘（2.0.0 起默认关） | ✘ | `pawn_backward_at_base` |
| 兵/卒 | 复活 / 升变 | ✔ | ✘ | `pawn_resurrection` / `pawn_promotion` |
| 兵/卒 | 敌阵冲锋（多格不吃子） | ✔ | ✘ | `pawn_charge` |
| 兵/卒 | 三连吃子 | ✔ | ✘ | `pawn_three_line_capture` |
| 尉/卫 | 斜向任意距离 | ✔ | ✔ | 无开关（特色棋子，无经典原型） |
| 射/䠶 | 强化（自由斜走三格） | ✔ | ✘ | `archer_enhanced_mode` |
| 檑/礌 | 相邻吃子 + 孤立判定 | ✔ | ✔ | 无开关 |
| 巡/廵 | 横向偶数格 / 隔两格吃 | ✔ | ✔ | 无开关（竖移禁行是硬规则） |

> **"全加强"的准确含义**：不是把每个开关都拨到 True，而是把**每个棋子的能力上限**打开。
> 因此 `horse_blocked_by_leg=False`（去掉限制）与 `horse_straight_three_move_only=False`（保留吃子）
> 都属于"加强"，而 `horse_straight_three=True` 则是新增能力。

## 3. 规则依赖（`OPTION_DEPENDS_ON`）

下游开关只有在上游开启时才有意义。引擎侧本来就被 `and` 守卫，UI 据此置灰：

| 下游 | 依赖上游 | 引擎里的守卫 |
|---|---|---|
| `king_lose_diagonal_outside_palace` | `king_can_leave_palace` | 不出去就到不了"宫外" |
| `advisor_gain_straight_outside_palace` | `advisor_can_leave_palace` | `straight and 出宫 and 直走` |
| `elephant_gain_jump_two_enemy_territory` | `elephant_can_cross_river` | `过河 and 跳两格 and 敌境` |
| `horse_straight_three_move_only` | `horse_straight_three` | 只存在于三格分支 |

## 4. 本次核对发现的实现偏差

| # | 偏差 | 严重度 | 现状 |
|---|---|---|---|
| D1 | **兵冲锋吞掉相邻一格吃子**：`_pawn` 里"落点有子 → `return False`"，导致开启冲锋后过河兵连正前方吃子都非法；升变位的兵无法吃子，连带 `in_check` 漏判 | **高** | 已修（Python + `offline.js` 同步）；回归用例 `test_pawn_charge_never_swallows_adjacent_capture` |
| D2 | **经典模式没有"经典化"**：`desktop_classic` 的 `RuleOptions()` 与完整模式完全相同，传统棋子仍是加强版 | **高** | 已修：新增 `CLASSIC_OPTIONS` |
| D3 | **经典模式少一枚尉**：用 `xionghan_side(complete=False)` 布局，每方 24 枚、10 型，与"同样部署全部棋子"不符 | 中 | 已修：改用完整布局，25 枚 11 型 |
| D4 | **精简模式规则与完整不一致**：额外关掉复活/升变，使"只减子"的正交设计被破坏 | 中 | 已修：`WEB_OPTIONS = COMPLETE_OPTIONS` |
| D5 | **三端开局布局分歧**：`offline.js` 与 Python 的初始摆位不同（尉/士位置），对拍只比着法不比布局，长期未暴露 | 中 | 已修：两端统一为"尉在将正后方、士在将两侧" |
| D6 | **冻结快照指纹随默认值漂移**：`tests/fixtures/positions/*.json` 只存 `pieces/legal` 两个数，不存选项，默认值一变就红，且无法判断是"规则改了"还是"实现错了" | 低 | 已更新指纹；建议后续把 `options` 一并写进快照（未做） |

未发现偏差的部分（本轮逐条核对通过）：车的直线/挡子/吃子、炮的隔子吃、象的塞眼、士的宫内斜走、
尉的斜向任意距离与不可直走、射的星轨与强化差异、檑的相邻吃与孤立判定、巡的偶数格与隔两格吃、
三连吃子的"移动兵必须参与"、将的照面判负、越界与己子落点拦截。

## 5. 验收清单（`tests/test_rule_matrix.py`，92 条）

| 组 | 用例 | 覆盖 |
|---|---|---|
| 汉/汗 | `test_king_inside_palace[3]` | 宫内 8 向 vs 4 向 |
| | `test_king_may_not_leave_palace_in_classic[3]` | 宫外可动性 |
| | `test_kings_facing_counts_as_check` | 照面计入被将 + 插子解除 |
| 车 | `test_rook_lines_blocking_and_capture[3]` | 直线/挡子/吃子/不斜走 |
| 马 | `test_horse_leg_blocking_by_mode[3]` | 别腿 8 vs 6 着 |
| | `test_horse_straight_three_by_mode[3]` | 三格直线开关 |
| | `test_horse_straight_three_requires_clear_path[3]` | 路径有子不可走 |
| | `test_horse_move_only_is_explicit_and_blocks_capture` | 仅移动：吃子禁、空格可 |
| 相/象 | `test_elephant_eye_blocks_in_every_mode[3]` | 塞象眼 |
| | `test_elephant_river_by_mode[3]` | 过河 |
| | `test_elephant_two_step_in_enemy_territory_by_mode[3]` | 敌境横竖两格 |
| | `test_elephant_jump_two_needs_cross_river` | 依赖：过河关→死开关 |
| 仕/士 | `test_advisor_inside_palace_is_diagonal_only[3]` | 宫内只斜走 |
| | `test_advisor_palace_exit_by_mode[3]` | 出宫 |
| | `test_advisor_straight_outside_palace_by_mode[3]` | 宫外直走 |
| | `test_advisor_straight_needs_palace_exit` | 依赖：出宫关→死开关 |
| 炮 | `test_cannon_move_and_capture[3]` | 平移/隔子吃/不吃己方/不越第二子 |
| | `test_cannon_without_screen_cannot_capture[3]` | 无屏不可吃 |
| 兵/卒 | `test_pawn_fast_move_by_mode[3]` | 快速行军 |
| | `test_pawn_sideways_after_river[3]` | 过河横走 |
| | `test_pawn_on_river_line_cannot_move_sideways[3]` | 阴山行不算敌境 |
| | `test_pawn_charge_never_swallows_adjacent_capture[3]` | **D1 回归** |
| | `test_pawn_charge_stops_before_piece[3]` | 冲锋遇子即停、不吃子 |
| | `test_pawn_three_line_capture_is_on_in_complete_off_in_classic` | 三连吃子按模式 |
| | `test_pawn_at_enemy_base_by_mode[3]` | 底线后退 |
| 尉/卫 | `test_guard_diagonal_any_distance_but_never_straight[2]` | 斜向任意 + 禁直线 |
| | `test_guard_stops_at_first_piece` | 吃到第一枚即停 |
| 射/䠶 | `test_archer_reach_by_mode[3]` | 星轨 vs 自由三格 |
| 檑/礌 | `test_thunder_captures_only_adjacent[3]` | 仅相邻可吃 |
| | `test_thunder_cannot_capture_protected_piece[3]` | 有保护子不可吃 |
| 巡/廵 | `test_patrol_even_steps_only[2]` | 偶数格 |
| | `test_patrol_capture_only_at_distance_two[2]` | 隔两格才可吃 |
| 结构 | `test_classic_targets_are_subset_of_complete[5]` | 经典只会更严 |
| | `test_no_two_pieces_share_a_square_in_any_mode` | 开局无重叠 |
| | `test_every_piece_is_inside_the_board` | 不越界 |
| | `test_opening_position_has_no_side_in_check` | 开局无被将 |
| | `test_opening_moves_exist_for_the_side_to_move` | 开局可动 |
| | `test_each_mode_can_play_a_deterministic_sequence` | 每模式连走 24 手不崩 |
| | `test_piece_roster_matches_the_declared_mode` | 兵种数/枚数/有无尉巡 |

跨引擎一致性另由 `tests/test_cross_engine.py` 覆盖（83 条，含开局布局与各开关对拍）。

## 6. 复现

```bash
./.venv/Scripts/python.exe -m pytest tests/test_rule_matrix.py -q
./.venv/Scripts/python.exe -m pytest tests/ -q -m "not slow"
```
