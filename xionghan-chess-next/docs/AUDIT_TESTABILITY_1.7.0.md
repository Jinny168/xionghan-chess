# 可验证性审计报告（v1.7.0）

| 项 | 值 |
|---|---|
| 审计对象 | 活体树 `xionghan-chess-next/`（`src/` · `tests/` · `web/` · `android/` · `scripts/`） |
| 基准 HEAD | `3fe7fe7`（审计时实测；基准之后仓库已前进，见 §8） |
| 审计角度 | 可验证性：代码与测试的对应关系、测试强度、冗余与死代码、缺失的验证面 |
| 审计人 | qa-lead（质量监管负责人） |
| 审计方法 | 只读静态审计 + 一次全量 `pytest` 运行 + `grep`/`glob`/`diff`/`git ls-files` 取证 |
| 声 明 | **只读**：审计期间未修改任何文件、未 commit；本报告的结论与证据均来自实测或明确标注的推断 |

> 与 `AUDIT_STRUCTURE_1.7.0.md`（结构审计）同族、角度互补：结构审计看目录/命名/依赖/职责，本报告看**"这些东西有没有被验证过"**。

---

## 一、结论摘要

1. **测试是绿的、且数量健康**：实测 `pytest tests/ --collect-only` = **202 用例**，全量跑**零 F/E**（仅 `.`）。分文件：cross_engine 51、rules 31、qa_regressions 12、capture_specs 12、game 11、ai_pool_blindness 11、ai_optimization 11、service 9、ai 9、extensions 8、desktop_storage 8、profiles 6、p0_rules 5、protocol 4、mcts_integration 4、training 3、i18n 3、taunts 2、mcts 2。
2. **"通道太弱"确认仍是主病根，但已有一条明确分界**：套件里**真正的黄金值断言**（`test_p0_rules` / `test_capture_specs` g1–g12 / `test_game._settle` / `test_ai_pool_blindness`）是强的；**纯 `_assert_parity` 的一批则只防"两侧漂移"，防不住"两侧同错"** —— 本报告给出 **10 条「绿了但没证明」候选**（§3，本报告最看重的产出）。
3. **F1/F2 的 fixture 短板已补**（不是当前的隐患）：当前 `test_position_key_matches_offline_byte_for_byte` 已含 `ROOK(2,0)`/`ROOK(10,0)` 跨界对子；G5 已含升变线并改名 `..._result_is_independent_of_the_capture_pool`。**上游交接给我的两条描述对"修前"成立、对当前 HEAD 已过期**（见附录 A 采信矩阵）。
4. **最大结构敞口有两条**：(1) **`node` 缺席时 `test_cross_engine` 51 例静默 skip，套件照样全绿**（对拍门禁整体蒸发）；(2) **性能/耗时零基线**，而 `benchmark.py` 里现成的 `acceptance` 判据（≤12s 等）**没有任何测试消费**。
5. **文档漂移三处**：审计文档的"内联升变集待办"在**基准时确未收敛**（现已收敛中，见 §8）；`docs/ABOUT.md` 与 desktop 副本曾**版本+内容双 drift**（版本已对齐、正文仍不一致，见 §8）；`web/js/core/game-rules.js`"第三套引擎"**只存在于仓库根旧树，活体树里没有**（文档未标路径归属）。

---

## 二、模块 ↔ 测试 对应表

### 2.1 零测试模块（实测：全仓 import 反查）

| 模块 | 行数 | 状态 |
|---|---|---|
| `core/benchmark.py` | 95 | **无测试**（仅被 `scripts/benchmark_ai.py` 手动脚本使用） |
| `desktop/app.py` | 1170+ | **无测试**（PySide6 GUI，可接受为手工验收面） |
| `desktop/audio.py` | 59 | **无测试** |
| `desktop/config.py` | 58 | **无测试** |
| `web/js/app.js` | 290 | **无行为测试**（仅 5 条源码字符串存在性断言） |
| `scripts/*` | — | 无直接测试（`offline_rules_probe.cjs` 被对拍间接驱动） |

### 2.2 有对应测试的模块

- `core.ai` ← {ai, ai_optimization, ai_pool_blindness, mcts_integration}
- `core.analysis` / `core.avatars` / `core.puzzles` / `core.setup` ← `extensions`
- `core.legacy` ← `desktop_storage`
- `core.mcts` ← {mcts, mcts_integration}
- `core.profiles` ← `profiles`
- `core.protocol` ← {protocol, qa_regressions}
- `core.rules` ← {rules, p0_rules, capture_specs, cross_engine}
- `core.storage` ← {game, extensions, service}
- `core.taunts` ← `taunts`
- `core.game` ← {game, rules}
- `service.{accounts,app,rooms}` ← {extensions, service, qa_regressions, taunts}
- `training.*` ← `training_pipeline`
- `i18n` ← `i18n`

### 2.3 弱覆盖 / 孤儿

- **弱覆盖**：`core/ai_see.py`（77 行）无专属测试文件，仅经 `test_ai` 的 `_see_score` 间接覆盖（3 例）。
- **孤儿测试**：无严格孤儿。但存在**两个 grab-bag 文件**：`test_extensions.py`（analysis+avatars+puzzles+setup+storage+service 混杂）、`test_qa_regressions.py`（协议/rooms/accounts + 5 条源码字符串断言）。

### 2.4 实测 vs 推断

模块↔测试映射来自 `grep "from xionghan_chess"` 全量扫描（**实测**）；"零行为测试"对 JS 是**阅读 + 断言清单判断**（**推断**）。

---

## 三、「绿了但没证明」候选清单（B-1 … B-10）

> 每条的"弱在哪" = 断言的**结构**证明不了它**名字/注释所声称的语义**。"两侧同错也绿"是基于**断言结构的逻辑推断**（未 mutate 代码制造反例）。

先立**分界线**（避免一刀切）：

- **强（钉期望值，两侧同错也拦得住）**：`test_p0_rules.py`（5 例，钉 `in_check` 为 True/False 并用 `apply_unchecked` 反算）、`test_capture_specs.py` g1–g12（钉 `kind/origin/landing/victim_id`）、`test_game.py` 的 `_settle` 链（钉 `result_reason` 等级序）、`test_ai_pool_blindness.py`（钉池价值差 1350、缓存项数=2、`pool_signature` 不等）、`test_cross_engine` 中所有用 `_assert_targets` 的用例（含精确目标集，如 horse/elephant/shield/patrol/diagonal_pinch 的 toggle 用例）。
- **弱候选见下表**（10 条，按 P 分级）。

| # | 用例（文件:行） | 弱在哪 | 建议补强 | 级别 |
|---|---|---|---|---|
| B-1 | `test_pawn_base_full_movement_toggle_parity` (`test_cross_engine.py:442`) | 三种 option 各跑 `_assert_parity`，**从不互相比较**；若两侧都忽略该 option，三条照绿 | 断言三组目标集**互不相等**；或改用 `_assert_targets` 精确集（照抄 `test_horse_straight_three_toggle_parity` 的写法） | **P0** |
| B-2 | `test_no_progress_plies_option_parity` (`test_cross_engine.py:927`) | 设 `no_progress_draw_plies=4` 走 4 步，**只对拍**，从不断言"和棋确实触发" | 补 `state.draw is True and result_reason == "no_progress"` | **P0** |
| B-3 | `test_thunder_parity_line_diagonal_and_isolated_capture` (`test_cross_engine.py:533`) | 摆了"孤立可吃 / 带盾不可吃"，**只有对拍**；`PIECE_RULES.md` 的孤立判定**无期望值**（两侧同错即绿） | `_assert_targets`：`(4,4)` 可吃、`(7,4)` 不可吃 | **P1** |
| B-4 | `test_kings_facing_parity` (`test_cross_engine.py:665`) | `assert _assert_parity(game)`（真值集）＋**无照面限制期望值**；名字承诺"照面"，只证两侧一致 | 断言"会导致继续照面"的位移不在合法集内 | **P1** |
| B-5 | `test_elephant_parity_eye_and_two_step_crossing` (`test_cross_engine.py:349`) | 注释明写"象眼被占 -> 阻挡对角跳"，**只有对拍**；象眼阻挡未钉 | `_assert_targets` | **P1** |
| B-6 | `test_pawn_parity_forward_sideways_and_two_step` (`test_cross_engine.py:433`) | 名字列三种行为，**只有对拍** | `_assert_targets` | **P1** |
| B-7 | `test_threefold_repetition_boundary_parity` (`test_cross_engine.py:743`) | docstring 自认 offline.js 无重复概念；**无"第三次判和"断言**，"boundary"未钉 | 补第三次后的 `draw` / `result_reason` 断言（黄金值在 `test_game.py`，此处至少断言触发） | **P1** |
| B-8 | `test_i18n.py::test_game_error_and_notation_can_use_english` | `try/except`：**若无异常则零断言通过**（软断言） | 改 `with pytest.raises(GameError, match="Illegal move")` | **P1** |
| B-9 | `test_armor_parity_sliding_then_line_capture` (`test_cross_engine.py:544`) / `test_assassin_parity_slide_and_drag` (`:578`) | 名字含 "line capture" / "drag"，实际**只有一条否定断言** | 补一次正向 `captured_by_move` 断言（语义已在 g11 / p0_rules 覆盖，故仅 P2） | **P2** |
| B-10 | `test_qa_regressions.py` 的 5 条**源码字符串存在性**断言 | 断言"某字面串出现在文件里"，**证明不了行为**（如 `no_progress_draw_plies:120` 在文件里 != 阈值生效） | 定位为"防误删结构护栏"，**必须与行为测试成对**；另见 §8 的版本耦合 | **P1（认知）** |

**参数化短路**：`test_capturable_squares_full_enumeration_parity`（4 profile 参数化）与 `test_all_piece_types_present_in_complete_profile_parity` 的 **for 内 assert 会在首个失败处短路**，后续 profile / 棋子未被验。pytest 会分项报，危害有限。**P2**。

**跨用例共享可变全局**：`test_cross_engine._SEEN_IDS`（模块级 set）跨用例累积——**只做 id 去重，不影响断言**，顺序无关。**P2 观察**。

**未用 monkeypatch 却改全局**：**实测未发现违规**。唯一直接改全局的是产品代码 `benchmark.py` 的 `os.environ["AI_TIME_SCALE"]`，且自带 `try/finally` 还原。测试侧 `monkeypatch`（打桩 `game.time.monotonic` / `rooms_module` / `service_app.accounts`、`setenv AI_TIME_SCALE`）与 `tmp_path` 用法**规范**。

---

## 四、冗余与死代码

- **TODO / FIXME / XXX / HACK = 0**（实测，与既有审计文档记载一致）；未见注释掉的代码块。
- **零引用公开符号（实测）**：`i18n.py:10 SUPPORTED_LANGUAGES` —— 全仓 grep **仅定义处 1 命中**，无任何消费者。-> 死常量。**P2**。
- **测试内死代码（实测）**：`test_rules.py:292` 的 `target = piece(HORSE, BLACK, 6, 0)` 被 `:296` 同名覆盖，**首值从未使用**。**P2**。
- **非死但无验证**：`core/benchmark.py`（仅手动脚本用）——其返回的 `acceptance{enoughGames, winRateAtLeast55Percent, masterMoveAtMost12Seconds}` 是**现成验收基线却无人断言**。**P1**（并入 §5）。
- **重复 fixture builder 盘点（实测，跨文件）**：
  - `piece(kind, color, row, col)`：**6 份**（`test_ai.py:11`、`test_ai_optimization.py:11`、`test_game.py:46`、`test_rules.py:11`、`test_ai_pool_blindness.py:48`、`test_capture_specs.py:23`）
  - `kings()`：**3 份**（`test_rules.py:15`、`test_ai.py:15`、`test_ai_optimization.py:15`，坐标一致）
  - `state()` / `board()`：**3 份**（`test_rules.py:7`、`test_p0_rules.py:32`、`test_capture_specs.py:27`）
  - `_sparse(...)`：`test_cross_engine.py:241` 一份（跨引擎专用，与 `board()` 概念重叠）
  - 建议：提取 `tests/conftest.py`（或 `tests/_fixtures.py`）。**P1**，收益 = 消除"两份 fixture 悄悄分叉"的**同型隐患**（F1/F2 的病根就是 fixture 与断言不对齐）。
- **保留项（非冗余）**：`test_ai_pool_blindness._expected_pool_value` 是**故意的独立重写**（注释"独立写一遍防止自证"），**不应合并**。

---

## 五、缺失的验证面

| 面 | 现状 | 缺口 | 级别 |
|---|---|---|---|
| 性能 / 耗时 | **零基线** | `benchmark.py` 的 `acceptance` 判据无测试消费；`position_key` / `_evaluate` 等热路径无耗时回归 | **P0** |
| 并发 / 协议 | 有：换 socket 不断线、ping 不广播、暂停同步、restart 需对方接受、超时只加 1 次 revision、chat 不推进 revision | **缺**：`client_stale`（revision 过期拒绝）、`RECONNECT_GRACE_SECONDS` 断线宽限 / 清理、乱序·重复消息、`revision_independent` 集合完整性穷举 | **P1** |
| JS 独立于对拍 | `web/js/app.js` **无行为测试**；`offline.js` 仅靠对拍 | 对拍防不住"两侧同错"——需给 `offline.js` 关键规则加**纯 JS 期望值断言**（node 内直断，不依赖 Python） | **P1** |
| 降级路径 | 无 | web `restore()` 服务不可达 -> `catch{} createGame()`；Android offline 兜底 | **P1** |
| UI / 文案 | 仅 i18n 键配对 + 回退 | 缺"值非空 / 未漏译"的最弱校验（键配对已能抓漏键，抓不到空值） | **P2** |
| `node` 缺席 | `test_cross_engine` 用 `shutil.which("node")` 否则 **skip** | **无 node 时 51 例静默跳过，套件仍全绿** -> 对拍门禁整体蒸发 | **P0（认知 / CI）** |

---

## 六、分级建议 P0 / P1 / P2

**P0**
1. **对拍门禁在无 `node` 时静默蒸发** —— 证据：`test_cross_engine.py` 中 `:46/:70/:90/:140/:761/:825` 均为 `pytest.skip`。补法：CI 断言 `node` 存在，或对 skip 计数设阈值 fail。
2. **性能零基线** —— 证据：无任何耗时类断言；`benchmark.acceptance` 无人消费。补法：新增 `tests/test_performance.py`（`@pytest.mark.slow`），断言 `_evaluate` / `position_key` 在给定规模下的**上界**，并复用 `benchmark.acceptance`。
3. **B-1 / B-2 两个 toggle 用例"只对拍、不复核 toggle 生效"** —— 补精确目标集 / 触发断言。

**P1**
4. B-3 / B-4 / B-5 / B-6 / B-7 / B-8 / B-10；
5. fixture 去重（`conftest.py`）；
6. 协议缺口（`client_stale` / 重连宽限 / 乱序）；
7. JS 独立期望值测试；
8. 降级路径；
9. 文档漂移（ABOUT/HELP 正文、`game-rules.js` 路径归属、升变待办口径）。

**P2**
10. `i18n.SUPPORTED_LANGUAGES` 死常量；
11. `test_rules.py:292` 死局部；
12. grab-bag 文件拆分；
13. `_SEEN_IDS` 共享可变全局标注；
14. 参数化 for 内 assert 短路。

---

## 七、实测 / 推断 / 未确证 声明 + 工具自验记录

### 7.1 实测

`pytest` 202 收集 + 全量零 F/E；分文件计数；`grep` TODO=0；`SUPPORTED_LANGUAGES` 零引用；`Glob web/**`；`git ls-files`；`diff` 三组文档副本；版本串；`rules.py` / `game.py` / `ai.py` / `app.js` 源码区位；`wc -l`。

### 7.2 推断（未做反例构造）

- §3 全部"两侧同错即绿"的判断基于**断言结构**（未 mutate 代码制造反例）。
- §5 的"未覆盖"基于测试名 + 断言清单的**阅读**，**可能漏**（无法穷举断言内部）。

### 7.3 未确证（工具未覆盖）

- **JS / C# 的零引用符号未做**（本次零引用工具仅覆盖 Python）——如实标注，**不当结论用**。

### 7.4 工具自验记录（对他人下结论前先自验）

"零引用判定"用"全仓符号 grep"，**自测 4 组对照**：

| 样本 | 期望 | 实测命中数 | 结论 |
|---|---|---|---|
| `normalize_language` | 命中（多引用） | 多命中 | 通过 |
| `avatar_asset_name` | 命中（含测试） | 多命中 | 通过 |
| `static_exchange_score` | 命中 | `ai.py:666` | 通过 |
| `SUPPORTED_LANGUAGES` | **不命中**（死符号） | 仅定义行 1 命中 | 通过 |

并**抽 3 个命中回原文人工复核**：`static_exchange_score` -> `ai.py:666`；`profile_slots` -> `service/app.py:177` + `desktop/app.py:581`；`promotable_types` -> `rules.py:155` / `:367`。

---

## 八、基准与后续变化

### 8.1 基准 sha 与基准之后的提交

- **基准 HEAD**：`3fe7fe7`（"docs(audit): 记 F1/F2 已知边界/观察项 + 待办项口径；G5 改名（result-independent）"）。
- **基准之后的提交（本报告落盘时实测，共 5 个）**：

| sha | 提交 | 影响本报告的条目 |
|---|---|---|
| `abaf1a8` | i18n(version): About 版本号 1.6.0 -> 1.7.0（中英） | 附录 B 的 ABOUT 版本漂移 |
| `747dd28` | docs(version): README 版本表述 + CHANGELOG 1.7.0 | 版本口径 |
| `02788fd` | docs(version): 两份 ABOUT 版本号 -> 1.7.0 | 附录 B 的 ABOUT 版本漂移 |
| `bfea053` | refactor(rules): 三处内联升变集收敛到单一来源（①，无行为变更） | 附录 A 的"内联升变集"条目 |
| `2a7cc30` | docs(android): BUILD_REQUIREMENTS 标题去掉版本号 | 无 |

### 8.2 由此已失效 / 需重新定性的条目

1. **附录 A「内联升变集三处未复用 `promotion_types`」**：统一改述为 **"基准 `3fe7fe7` 时未复用；`bfea053` 起正在收敛（该提交自述'无行为变更'）；本报告未验证最终态"**。**不写"已确认修好"。**
2. **方法论风险声明（重要）**：本报告其中部分源码区位（`rules.py:155/:195`、`ai.py:367`）是在工作树**可能已被他人推进后**读取的。因此原文中"三处已复用"这一观察**可能反映的是 `bfea053` 之后的状态，而非基准态**。按上述统一口径，该条**不作为已核实结论**，仅作"收敛中"记录。
3. **附录 B「ABOUT 双副本版本 1.4.0 vs 1.6.0」**：`02788fd` 之后**两份 ABOUT 的版本号均已对齐为 1.7.0**（实测）；但两文件**正文仍不一致**（`diff` 仍非空），`docs/HELP.md` 与 desktop 副本**亦仍不一致**。故该条**部分失效**：**版本已修、正文未合**。

### 8.3 版本耦合（交主程序的 bump 耦合点）

`tests/test_qa_regressions.py::test_release_cache_busters_match_package_version` 断言 `app.css?v=1.6.0` / `app.js?v=1.6.0` / `i18n.js?v=1.6.0`。**实测**：`web/index.html` 与 `web/js/app.js` **当前仍是 `?v=1.6.0`**。=> 版本号 bump 到 1.7.0 时，**此测试将变红**，须与 cache-buster 同 commit 修改。

> **状态更新：该耦合点已消除（已根治）—— `71330e1` + `3baae61`**
>
> 上句中的用例名是**基准 `3fe7fe7` 时的历史快照，予以保留**（记录"当时叫什么"）。该用例**已被替换**为 **`test_release_version_sources_agree`**（`tests/test_qa_regressions.py:189`；旧名在代码中**已不存在**，实测 `grep -c` = 0）。
>
> 新用例**不再硬编码任何版本字面量**：它以 **`package.json:version` 为单一来源**，把其余 **7 处**逐一**解析后比对**——`pyproject.toml:[project].version`、`xionghan_chess.__version__`、`android/XionghanChessAndroid.csproj:ApplicationDisplayVersion`、`web/index.html` 的 `app.css?v=`、`web/index.html` 的 `app.js?v=`、`web/js/app.js` 的 `i18n.js?v=`、`deploy/docker-compose.yml` 的 image tag —— 不一致时报出**全部**错配文件名。
>
> **因此"bump 会让该测试变红"这一耦合今后不再存在**：未来的版本 bump 只需改各版本字段，不会再因该测试失败。
>
> 附（对本节基准时观察的更正）：基准时我观察到"`web/index.html` / `web/js/app.js` 仍为 `?v=1.6.0`"；该状态随后由 `88a68bd`（"版本号 1.6.0 → 1.7.0 余项（A 类 7 文件）+ web 缓存戳测试耦合"）改为 **`?v=1.7.0`**。实测当前各面版本一致为 `1.7.0`（`package.json` / `web/index.html` / `web/js/app.js` / `deploy/docker-compose.yml` image tag / csproj `ApplicationDisplayVersion`），且 csproj `ApplicationVersion=9`。

### 8.4 影响范围判定

上述 5 个提交**只动文档与版本**（`bfea053` 自述"无行为变更"重构），故：

- **规则 / 测试强度类结论（§3、§4、§5、§6）不受影响**，仍然有效。
- **受影响的仅两条**（"内联升变集"与"ABOUT 版本漂移"），已按 §8.2 重新定性。
- **建议**：主程序完成 bump / 收敛后，以新 HEAD **复跑 `pytest` 并复核上述两条**，再据以更新本报告状态。

---

## 附录 A：采信矩阵（上游结论逐条复算，事实 / 归因分格）

| 上游结论 | (1) 我实际执行的命令/动作 | (2) 本机原始输出（摘要） | (3) 采信判定 |
|---|---|---|---|
| HEAD = `3fe7fe7` | `git rev-parse HEAD` + `git status --porcelain` | `3fe7fe702430…`；status 空 | **采信·复现** |
| "F1 对拍 fixture 只有 1 颗车、无同型成对子" | 读 `test_cross_engine.py:785-798` | 现含 `ROOK(2,0)` + `ROOK(10,0)` 跨界对子（F1 症结） | **采信·推断修正**：对"修前"真，对当前 HEAD **已过期** |
| "F2 G5 fixture 用 rook/horse、不经升变线" | 读 `test_capture_specs.py:95-124` | 现含 `PAWN(1,6)` + `HORSE(0,6)` 升变线，且改名 `..._result_is_independent_of_the_capture_pool` | **采信·推断修正**：同上，已补 |
| 审计文档「TODO / FIXME / XXX / HACK = 0」 | `grep -rn "TODO\|FIXME\|XXX\|HACK"` 全仓 | 0 命中 | **采信·复现** |
| 审计文档「第三套引擎 `web/js/core/game-rules.js`」 | `Glob web/**` + `git ls-files web` | **活体树无**该文件；**仓库根旧树有**（`web/game.html`、`web/js/core/game-rules.js` 均被 git 跟踪） | **采信·推断修正**：存在性真，**路径归属未标**致误读 |
| 审计文档「内联升变集未复用 `promotion_types`」= 待办 | 读 `rules.py:155 / :195`、`ai.py:367` | 三处**均已复用** `promotable_types` / `promotion_types` | **采信·推断修正 + 已重新定性**：基准时未复用，`bfea053` 起收敛**中**；**未验最终态**（见 §8.2） |
| （历史）"测试基线 169 passed" | `pytest --collect-only -q` | `202 tests collected` | **采信·推断修正**：数字已前移 |

## 附录 B：文档一致性抽检（基准时口径；受影响项见 §8.2）

| # | 抽检项 | 基准时实测 | 判定 |
|---|---|---|---|
| 1 | 审计文档"内联升变集未复用 `promotion_types`"= 待办 | 基准时未收敛 -> 现已收敛中（§8.2） | **待办口径已过期** |
| 2 | F1 观察项"建议补同型跨界对子" | 对拍 fixture **已补**（ROOK 2/10） | 文档可改"已补" |
| 3 | F2 观察项"G5 恒绿" | G5 已含升变线并改名 | 文档已记录处置 |
| 4 | `web/js/core/game-rules.js`"第三套引擎" | **活体树无**；存在于**仓库根旧树** | **路径归属未标** |
| 5 | 版本口径 | cache-buster **仍 1.6.0**；`docs/CHANGELOG_1.7.0.md` 已存在；bump 任务 pending | **1.7.0 迁移未完成**；见 §8.3 耦合点 |
| 6 | 重复文档副本 | `docs/PIECE_RULES.md` == desktop 副本（`diff` 无差异）；`docs/ABOUT.md` 与 desktop 副本曾版本+内容双 drift（版本已对齐、正文仍不一致）；`docs/HELP.md` 与 desktop 副本不一致 | **ABOUT/HELP 正文漂移** |
| 7 | PIECE_RULES 规则 <-> 代码（源码级抽 3） | 巡（行 5/7 + 偶格 + 距 2 吃）`_patrol:718` 一致；射 13 星点 `archer_star_points:51` 一致；楯不可吃 `pseudo_legal:141` 一致；檑孤立 `_thunder:703` + `_isolated:726` 一致**但无黄金值测试** | 文档与代码**一致**（此处无漂移） |

## 附录 C：结构规范性（轴四）

- 命名大体统一（`test_<行为>`；跨引擎 `test_<棋子>_parity_<条件>`），**但 5 个用例"名字承诺 > 实际断言"**（§3 的 B-3/4/5/6/9）。
- 分组问题：`test_extensions.py` / `test_qa_regressions.py` 属**多不相干层次混装**，建议按模块拆分。**P2**。
- 依赖面：`test_service` / `test_extensions` 用 `TestClient`（ASGI 内存，**无真实网络**）；`test_cross_engine` **依赖 `node` 可执行**（见 §5 的静默 skip 风险）。

---

## 附：本轮为"首轮验收审计"

无上轮缺陷 -> 「上轮每条缺陷当前状态」一项 **N/A**（不伪造）。本报告即"逐条实测证据 + 缺陷分级 + 可交付判定"三块的承载。
