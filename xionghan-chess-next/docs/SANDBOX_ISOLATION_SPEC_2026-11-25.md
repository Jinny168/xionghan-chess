# 沙盘构造隔离规格（计划 E-C / C4 无悔棋试走）

> 作者：柯桥良（技术架构总监） · 日期：2026-11-25
> 基线：HEAD `8dfc3f3`，`RULE_VERSION=3`，桌面单端；本轮**只出规格**，不改源码/测试/其它文档/CHANGELOG/版本源
> 证据口径：所有结论均可由 `文件:行`、测试名或本机命令输出核对；不写人工目检
> 范围：复盘关键手 → 一键试走（无悔棋）。不引入联网、账号、外部引擎，不改三端产物链
> **行号口径**：本文所有 `dialogs.py` 行号以基线 `8dfc3f3` 为准。本机工作树在撰写时已有队友未提交的 T1 插入（`dialogs.py` 顶部新增训练主题筛选），使 `ReplayDialog` 段整体后移 43 行；源码一旦继续插行，按下面的**符号定位**复核，不要沿用旧行号。

```
git show 8dfc3f3:src/xionghan_chess/desktop/ui/dialogs.py | nl -ba | sed -n '720,742p'
git grep -n "sandbox._snapshots = \[base.to_dict()\]" -- src/
git grep -n "def _sandbox_source\|def _build_sandbox\|def _sandbox_undo" -- src/xionghan_chess/desktop/ui/dialogs.py
```

---

## 0. 一句话结论

**当前沙盘自己的悔棋不是缺口**：`desktop/sandbox.py:38-39` 已注明 `from_state()` 不重建 `_snapshots`，`:60` 在构造末尾手工补了一格起点快照，`:64-74` 的 `undo_sandbox_move()` 走 `allow_finished=True` 专用路径，UI 按钮与 handler 在 `desktop/ui/dialogs.py:656-663,809-813` 都在，且 `tests/test_desktop_sandbox_isolation.py:115-131` 有红证。

**真正的风险在 C4 的入口改造**：一旦把沙盘起点从"终局快照"改成"复盘历史节点"，若绕开 `build_sandbox_game()` 直接 `Game.from_state(...)`，就会同时失去「字段清零 + 起点快照 + 深拷贝」三重保护。这不等于当前代码有第二条路径——**截至 HEAD 只有一条路径**（见 §5 第 2 条）。

---

## 1. 可核对的调用路径：`build_sandbox_game(game)` 为什么安全

### 1.1 实际调用链（只有这一条）

```
ReplayDialog.__init__                       dialogs.py:621   权威 _snapshots + state.clone() → self.snapshots（独立副本）
  └─ 选中沙盘标签 / 点"进入沙盘"             dialogs.py:744-746,660
      └─ _sandbox_enter()                   dialogs.py:750-769
          └─ _build_sandbox()               dialogs.py:735-742
              ├─ _sandbox_source()          dialogs.py:720-728   snapshots[-1].clone() → Game.from_state(...)
              └─ build_sandbox_game(source) dialogs.py:739       ← 唯一出口，不可绕过
                  └─ sandbox._snapshots = [base.to_dict()]       sandbox.py:60
      └─ board.move_requested → _sandbox_move → self._sandbox_game.move(move)
                                            board_widget.py:421,1342；dialogs.py:763,803-807
      └─ UI 悔棋 → undo_sandbox_move(self._sandbox_game)          dialogs.py:809-813 → sandbox.py:64-74
```

权威 `Game` 在这条链路上**只被读**（`game.state` / `game.options` / `game.profile` / `game.setup`），从未被交给 `board.set_game()`，也从未调用它的 `move()`。`dialogs.py:764` 交给棋盘的是 `self._sandbox_game`。

### 1.2 逐行隔离动作

| 字段 | 源码 | 动作 | 隔离效果 |
|---|---|---|---|
| 局面本体 | `desktop/sandbox.py:41` `base = game.state.clone()` | `clone()` = `to_dict()` → `from_dict()`（`model.py:145-146,148-184,187-203`）；`pieces` / `captured` / `history` / `clocks_ms`（`:172,182,200`）/`position_counts`（`:183,202`）均重建为新容器 | 与权威 state **无对象别名**；后续原地写不会落到权威 |
| `winner` / `result_reason` / `draw` | `sandbox.py:42-44` | 置 `None` / `None` / `False` | `finished` 属性（`model.py:131-133`）变 False，`Game.move()` 的终局守卫（`game.py:69-70`）不拦试走 |
| `paused` / `paused_by` | `sandbox.py:45-46` | 清零 | 不会命中 `game.py:71-72` 的暂停守卫 |
| `pending_draw_offer` / `pending_undo_offer` / `pending_restart_offer` | `sandbox.py:47-49` | 置 `None` | 权威的协商痕迹不进沙盘；沙盘第一步也不会误触发 `game.py:177` 的 undo 应答 |
| `position_counts` | `sandbox.py:50` | 整字典替换为 `{}` | 沙盘不继承权威的三次重复账本；试走判和只按沙盘自己的步数走（`game.py:301-303,331-337`） |
| `history` | `sandbox.py:51` | 置 `[]` | 沙盘着法不进权威棋谱；`_no_progress_plies()`（`game.py:341-347`）从零起算 |
| `clocks_ms` | `sandbox.py:52`（常量 `:28`） | 双方各 `86_400_000`（24h 哨兵） | `tick()`（`game.py:247-257`）只扣沙盘自己的钟，慢速试走不会超时；理由见 `sandbox.py:13-15` |
| `turn_started_at` | `sandbox.py:53` | 重置为 `time.monotonic()` | 避免权威的上一次思考时间被计入沙盘第一步 |
| 规则配置 / 开局设置 | `sandbox.py:57-58` | `asdict(game.options)` 生成新 dict；`GameSetup.from_dict(..., game.setup.to_dict())` 生成新实例（`setup.py:48-49,101-118` 为 frozen dataclass + tuple） | 选项/布局不共享可变容器 |
| 沙盘实例 | `sandbox.py:55-59` → `game.py:53-63` | `Game.from_state()` 内部 `cls(...)` 新建 `Game`（`:61`），再 `game.state = state`（`:62`） | 新的 `RulesEngine` / 新的 `_snapshots` 列表；权威 `Game` 对象没有被复用 |
| 起点快照 | `sandbox.py:60` | `sandbox._snapshots = [base.to_dict()]` | `from_state()` 之后 `_snapshots` 实为 `[]`（`game.py:49,53-63`），必须手工补一格；补完 `len==1`，`undo_sandbox_move()` 在起点返回 False（`:71-72`） |

### 1.3 为什么 `from_state()` 这一跳本身不带入权威

- `Game.from_state()` 只做两件事：`cls(...)` 与 `game.state = state`（`game.py:61-62`）。它不写回传入的 `Game`，也不持有它。
- `build_sandbox_game()` 传入的是 `base`（`clone()` 产物）而不是 `game.state`，所以 `game.py:62` 的按引用赋值指向的是副本。
- `undo_sandbox_move()` 的 `allow_finished=True`（`sandbox.py:73`）只作用于沙盘实例：`Game.undo()` 从 `self._snapshots` 取快照并替换 `self.state`（`game.py:115-118`），不触碰权威。
- 控制面互斥由 `dialogs.py:766-768,896-900,928-929` 保证：沙盘态禁用滑块/着法表/自动播放，`set_step()` 与 `next_step()` 直接返回；退出时 `dialogs.py:788-789` 强制 `set_step` + `show_step` 恢复复盘棋盘。

本机行为探针（2026-11-25，`./.venv/Scripts/python.exe -c ...`）：

```
bare_snapshots=0            # Game.from_state(state, ...) 后 _snapshots 为空
sandbox_snapshots=1         # build_sandbox_game 后恰好一格起点快照
base_counts={}              # 沙盘不继承权威 position_counts
state_is_same_before_move=True / after_move=False   # from_state 按引用持有传入 state；move() 后换成 clone
replay_len_at_start=2, replay_entries_equal=True    # public_state(replay=True) = [起点] + [当前]
```

`./.venv/Scripts/python.exe -m pytest tests/test_desktop_sandbox_isolation.py -q --color=no -p no:cacheprovider` → **`7 passed in 13.54s`**。

---

## 2. 禁止项（从历史局面另建沙盘时）

| # | 禁止的具体调用 | 源码依据 | 后果 | 正确替代 |
|---|---|---|---|---|
| N1 | 把**权威 `Game` 对象**塞给沙盘棋盘，并让 `board.move_requested` 直接调它的 `move()` | `board_widget.py:421,1342`；`dialogs.py:763,803-807`；`game.py:68-102` | 这就是普通权威落子：`tick()` 原地扣权威时钟（`:76,247-257`），`_snapshots.append`（`:81`）、`history.append`（`:94`）、`_record_position()`（`:100,301-303`）全部写进权威；棋谱与判和账本被污染 | `dialogs.py:764` 只 `set_game(self._sandbox_game, ...)`；沙盘实例必须来自 `build_sandbox_game()` |
| N2 | `Game.from_state(shared_state, ...)` 时传入**未 clone 的历史 state**（例如 `ReplayDialog.snapshots[k]` 本体） | `game.py:62` 按引用赋值；`dialogs.py:621,905` 的快照对象会被 `show_step()` 再次 clone 使用 | `from_state` 后 `bare.state is shared_state == True`（本机探针）。沙盘第一步 `move()` 的 `tick()`（`game.py:76,247-257`）**原地**改 `shared_state.clocks_ms` / `turn_started_at`，超时时还改 `winner` / `result_reason`；复盘再跳回该节点时会看到被试走改过的时钟 | `dialogs.py:728` 的 `self.snapshots[-1].clone()` 写法；历史节点同样必须 `.clone()` 后再传给 `build_sandbox_game()` |
| N3 | 以为 `move()` 的 `_record_position()` 会原地改**共享的旧 state** | `game.py:100,301-303`；`rules.py:255-261,272`；`model.py:183,202` | 精确化：`apply_unchecked()` 先 `state.clone()`，`:99` 把 `self.state` 换成新对象，`_record_position()` 写的是新对象——**旧 state 的 `position_counts` 不被 `move()` 原地改**（本机探针 `counts_changed=False`）。真正原地写共享 state 的是 `tick()`（N2）。但沙盘侧仍得到一条**与权威不同的重复计数账本**，其结论不得回写权威 | 把 `_record_position()` 理解为"沙盘自己的账本"；任何试走判和结论不进权威、不进存档 |
| N4 | 在共享 state 的沙盘上调用 `resurrect_pawn()` | `game.py:220-222,223-230,244` | 与 `move()` 不同，复活全程原地改 `self.state`（`captured` / `pieces` / `turn` / `pending_*`），并在 `:244` 原地 `_record_position()`。本机探针：共享 `raw.to_dict()` 前后字节**不同**，`position_counts` 从 `{}` 变成 2 条。这是对 N3 的补充——并非只有时钟会被污染 | 同样先 `clone()`；复活能力若不在 C4 范围内也应随沙盘只读配置关掉，但**不得**因此放宽拷贝要求 |
| N5 | 复用/拼接权威 `_snapshots` 当沙盘快照，例如 `sandbox._snapshots = list(game._snapshots)` 或把网络 replay 的 dict 列表直接搬来（`app.py:2397` 的写法） | `game.py:113-117,298`；`sandbox.py:60,71-72` | `undo()` 会从权威时间线取快照（`:115`），恢复到沙盘**从未到达**的局面；下一步 `public_state(include_replay=True)`（`:298`）或存档会把这段"不存在历史"发布出去。若起点是历史节点 `k`，复用前缀会让 `undo_sandbox_move()` 把玩家送回 `k-1` 而不是在起点返回 False | 起点快照只允许 `sandbox._snapshots = [base.to_dict()]`；C4 无悔棋首版应把 `len==1` 当硬不变量 |
| N6 | `Game.from_state(base, ...)` 之后**不补**起点快照就当沙盘用 | `game.py:49,53-63`；`sandbox.py:38-39,60` | `_snapshots == []` → `undo_sandbox_move()` 恒返回 False（UI 静默禁用），`Game.undo(1)` 抛 `GameError("no_undo")`（`game.py:113-114`）；`public_state(replay=True)` 只剩当前局面一格，起点丢失 | 必须调 `build_sandbox_game()`，不要手写 `from_state()` 沙盘 |
| N7 | 把沙盘 `Game` 交给存档、权威广播或 AI 分析入口 | `core/storage.py:97-116`（`game_document` 写 `_snapshots`）、`desktop/storage.py:22-36`（`save_game` / `autosave_game`）；`dialogs.py:846-848` | 沙盘的清空字段（history/counts/clocks）与单格 `_snapshots` 会被写成棋谱或发给别人，等于用试走覆盖权威记录 | 沙盘只在内存里活到关闭（`dialogs.py:771-790`）；分析路径 `dialogs.py:846-847` 是另一条专用副本，不要与沙盘混用 |
| N8 | 手工复制 `build_sandbox_game()` 的清零语句到新入口，复制不全（漏 `pending_undo_offer` / `position_counts` / `turn_started_at` 之一） | `sandbox.py:42-53` 共 12 个字段/容器 | 漏 `pending_undo_offer` → 首步可能触发协商撤销（`game.py:177`）；漏 `position_counts` → 继承权威判和账本；漏 `turn_started_at` → 时钟计算带着旧时间 | 单一工厂：所有入口调 `build_sandbox_game()` 或将来新增的 `build_sandbox_from_state()`；禁止第二份清零代码 |

---

## 3. C4 首版约束（无悔棋试走）

### 3.1 可接受的最小集

首版锁定为：**"复用 `build_sandbox_game()` + 起点取指定历史节点的 `clone()` + 不提供沙盘内悔棋 + 结果不落盘"**。理由：

1. **隔离不靠新机制**：`build_sandbox_game()` 已把 12 处字段/容器处理完（`sandbox.py:42-53`），新增入口只需换"源快照下标"，不需要碰 `core/`。换源不是换构造路径。
2. **无悔棋与现有快照模型自洽**：`build_sandbox_game()` 只补一格起点快照（`sandbox.py:60`），`undo_sandbox_move()` 在起点返回 False（`:71-72`）。首版不暴露悔棋，正好避免把"只有一格"误包装成可悔棋历史。
3. **语义代价明确且可接受**：`position_counts={}`（`:50`）与 `history=[]`（`:51`）意味着沙盘**不复现**权威的三次重复与无进展判和前提；试走得出的"将死/判和"仅是局部演示，不得回写权威结论。这是隔离的代价，不是 bug。
4. **运维成本最低**：桌面单端、无新文件、无新权限、无平台合规新增项（仍遵守纯本地/零采集/零账号）。

若 C4 复用 `ReplayDialog`，需在入口层禁用 `sandbox_undo` 按钮（`dialogs.py:657,661,819`）；不禁用也不会污染（起点返回 False 并给提示，`:812-813`），但会违背"无悔棋"的产品承诺。若 C4 用独立面板，**不得复制** `_sandbox_undo` 逻辑（`:809-813`）到新面板。

### 3.2 将来要支持"历史局面悔棋"时，先补什么

按依赖顺序，缺一项都不要开：

1. **新工厂 API**：在 `desktop/sandbox.py` 增加 `build_sandbox_from_state(state, options, setup)`，把 `build_sandbox_game()` 的 `:41-60` 抽成共用实现；`build_sandbox_game(game)` 保留为薄封装。这样"字段清零 + 深拷贝 + 起点快照"仍只有一个实现点（对应 N8）。
2. **起点选择 API**：`ReplayDialog._sandbox_source()`（`dialogs.py:720-728`）增加显式 `index` 参数，仍强制 `self.snapshots[index].clone()`；沙盘态禁用滑块的现有约束（`dialogs.py:766,896-900`）保留，否则"试走中的起点"会漂移。
3. **快照策略必须显式定义**：若只允许"从新起点悔回本局试走"，`_snapshots` 仍只能是 `[起点]`；若要支持"沿历史前缀悔棋"，必须新增带 `snapshots` 参数的 API，且快照序列要与所选节点的 `position_counts` / `clocks_ms` / `turn` / `history` 自洽（不能整段复制权威列表，见 N5），并先定义"历史时钟在沙盘里按什么值算"——当前 24h 哨兵与真实余量不同（`sandbox.py:13-15`）。
4. **测试先行**：补齐 §4 的历史节点变体（k=0/中/末）与"悔棋不越过起点"断言，再放开 UI 按钮。

---

## 4. 验收判据（全部可自动核对）

### 4.1 隔离门禁表

门禁类归类依据：前六项是**结构性不变量**——运行中一旦检测到权威 `state` 被写入，已无安全恢复点（权威数据已被改动，无法从沙盘侧回滚），因此**没有运行时降级动作**。clone 延迟也是门禁而非降级项：C4 每个起点只有一次 clone、没有可切换的慢路径，超阈意味着 `to_dict/from_dict` 回归；用"少拷一次"换速度恰好会破坏前六项。因此全表只能卡在 CI/合并环节，触发点与责任人写在"超阈处置"列，不写"后续优化"。

| 项 | 数值目标 | 测量方式 | 超阈处置 |
|---|---|---|---|
| 权威 state 逐字节一致 | 差异字节数 = 0（试走 N 步、复活、悔棋之后） | `json.dumps(state.to_dict(), sort_keys=True, separators=(",",":"))` 前后比较（`tests/test_desktop_sandbox_isolation.py:58-59,83`） | **门禁**：CI 执行 `tests/test_desktop_sandbox_isolation.py`，任一断言失败即红灯阻断合并；判定人=CI，后果=不得合并；责任人=改动 `sandbox.py`/`dialogs.py` 的作者 |
| 沙盘起点快照 | `len(sandbox._snapshots) == 1` | 构造后直接断言（现有测试 `:119` 写的是 `>=1`，C4 需收紧为 `==1`） | **门禁**：同上一行；红灯即阻断，需在入口恢复 `build_sandbox_game()`，不得改断言放宽 |
| 起点不可悔 | `undo_sandbox_move(sandbox) is False` | 构造后调用一次（现有测试 `:120`） | **门禁**：红灯即阻断；若返回 True 说明复用了历史快照（N5），必须回到 `sandbox.py:60` 的单快照语义 |
| 沙盘时钟哨兵 | 初始两方各 `86_400_000`；任一步后 `0 < v <= 86_400_000`；权威 `clocks_ms` 差异 = 0 | 常量 `SANDBOX_CLOCK_MS`（`sandbox.py:28`）+ 断言（现有测试 `:89-99`） | **门禁**：红灯即阻断；不得把真实余量传进沙盘（会超时） |
| 起点深拷贝 | `sandbox.state is not source.state` 且两者的 `position_counts` / `clocks_ms` 容器 `id` 不同 | 构造后 `is not` + `id()` 断言；对应 `model.py:182-183,200-202` | **门禁**：红灯即阻断；恢复 `GameState.clone()`，不得用 `from_state()` 直接接权威 state |
| 终局起点可用 | 起点设 `winner` 后 `not sandbox.state.finished`，`move()` 不抛 `GameError` | 现有测试 `:102-112` | **门禁**：红灯即阻断；检查 `sandbox.py:42-44` 三字段是否仍清零 |
| clone 延迟（性能预算） | 100 ply 局面、`state.clone()` 2000 次：中位数 ≤ 2.0 ms，p95 ≤ 3.5 ms | 现有测试 `:190-204`（`time.perf_counter()`） | **门禁**：红灯即阻断合并；C4 每节点只多一次 clone，超阈说明 `to_dict/from_dict` 有回归，不得通过删 clone 换速度 |

### 4.2 C4 需要新增的自动探针（本轮不写测试，只给可执行判据）

- **P1 历史节点源**：`ReplayDialog.snapshots` 长度 `n`；对 `k ∈ {0, n//2, n-1}`，`_sandbox_source(k)` 返回值 `is not dialog.snapshots[k]` 且 `is not authoritative_game.state`，且 `state.to_dict()` 等于 `snapshots[k].to_dict()`。
- **P2 历史节点不污染**：对同样三个 `k`，先 `before = json.dumps(dialog.snapshots[k].to_dict(), sort_keys=True)`，进入沙盘 → 试走 1 步 → 退出；断言 `json.dumps(dialog.snapshots[k].to_dict(), sort_keys=True) == before`，且 `authoritative.state.to_dict()` 逐字节不变。
- **P3 单快照不变量**：对同样三个 `k`，进入后断言 `len(dialog._sandbox_game._snapshots) == 1` 且 `undo_sandbox_move(dialog._sandbox_game) is False`。
- **P4 构造出口唯一**：AST/源码断言——`ReplayDialog._build_sandbox()` 函数体内存在 `build_sandbox_game(...)` 调用，且不存在 `Game.from_state(...)`、不存在 `._snapshots =` 赋值；`_sandbox_source()` 函数体内存在 `.clone()`。构造失败时 `QMessageBox.warning` 被调用且 `_sandbox_game is None`（现有测试 `:159-187` 已覆盖）。
- **P5 无写盘/无进谱**：monkeypatch `desktop/storage.py:22,33` 的 `save_game` / `autosave_game` 与权威 `game.move` 为抛异常函数，完成"进入试走→落子→退出"，断言三者均未被调用；权威 `history` 长度不变。
- **P6 控制面互斥**：沙盘态 `slider.isEnabled() is False`、`moves.isEnabled() is False`、`board.game is dialog._sandbox_game`；`slider.setValue(0)` 后 `board.game` 仍是沙盘（现有测试 `:134-156` 已覆盖）。

---

## 5. 与调度方判断不一致（逐条如实写）

1. **T6 原句需要更正，调度方的纠正成立**。`ARCH_GAP_2026-11-25.md:137` 我写的"沙盘悔棋是 API 缺口"**作为当前状态描述是错的**：`sandbox.py:38-39,60,64-74` 已补起点快照与专用悔棋，`dialogs.py:656-663,809-813` 有 UI 与 handler，测试 `:115-131` 绿。准确说法是：**若新开一条从历史局面构造沙盘的路径，则必须补等价的 `build_sandbox_from_state()` API**；现有 API 对既有路径并不缺。
2. **"从复盘的历史局面构造沙盘会走另一条路径，未必经过这套快照重建"——方向对，但当前 HEAD 不成立**。截至 HEAD，`dialogs.py:720-728` 的 `_sandbox_source()` **固定取 `snapshots[-1]`**（终局），`dialogs.py:735-742` 的 `_build_sandbox()` **固定调用 `build_sandbox_game()`**（`:739`），测试 `:159-187` 通过 monkeypatch 该函数证明这是唯一出口。仓库里没有第二条沙盘构造路径。这是**C4 改造后的前瞻风险**，不是现存缺陷；P4 探针就是为锁住这一点。
3. **`sandbox.py:10` 的注释与当前行为不符**：注释写"从'当前回看节点'取一个真实局面起步"，但 `dialogs.py:726-728` 固定取末节点，且沙盘态禁用滑块（`:766,896-900`）。本轮不改源码，仅记录：C4 若引入历史节点起点，应以此注释描述的语义为准，而不是以当前 `[-1]` 实现为准。
4. **`move()` 的 `_record_position()` 污染对象需精确化**（对应 N3）：调度方把它与 `tick()` 并列为"写回权威"路径。准确表述是——若被误用的是**权威 Game 对象**，两者都在权威链路上发生（N1）；若被误用的是**共享的 GameState**（`from_state` 未 clone），原地写共享对象的是 `tick()`（`game.py:247-257`）与 `resurrect_pawn()`（`:220-230,244`），`move()` 的 `_record_position()` 写在 `apply_unchecked()` 产生的新 state 上（`rules.py:255-261,272`）。本机探针：`clocks_changed=True`、`counts_changed=False`、复活路径 `shared_raw_changed=True`。这不减轻风险，只是把处置点对准正确的函数。

---

## 6. 前提假设与重估条件

- 假设 C4 只在桌面端、复用现有 `ReplayDialog` 沙盘面板、不新增网络/存档/AI 链路；任一变化（尤其要做 Web 端或对局中沙盘）需重估 §1.1 调用链与 §4 全部探针。
- 假设首版"无悔棋"= 不暴露沙盘内悔棋入口，而非删除 `sandbox.py:64-74` 的既有能力；若将来要移除该函数，需连带改 `dialogs.py:68,657,661,809-813` 与测试 `:115-131`。
- 假设 `Game.from_state()` 的"按引用持有 state、不重建 `_snapshots`"语义不变（`game.py:53-63`）；若 core 侧改动它，N5/N6 与 §3.2 的 API 设计需重估。
- 性能预算以本机 100 ply / 2000 次 clone 样本为准；换机器或 `GameState` 字段结构变化后须重跑 `tests/test_desktop_sandbox_isolation.py:190-204` 再引用数值。
- 平台规则（Steam/主机/移动商店）本轮不涉；若未来进入发布阶段，以官方文档为准重新核对。
