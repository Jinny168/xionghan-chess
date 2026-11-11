# 代码审计 2026-10-31（结构 / 内存 / 并发三章）

> 只读，未改代码。尺寸更正：`desktop/app.py` 实为 **1015 行**（任务书">1100 行"不成立）。测不出的标「未验证」。
## 一、代码结构与可维护性

```
[1-1] P2 · 结构
位置：desktop/app.py:107-1007（MainWindow，约 900 行）
成因：UI 构建/事件/AI 调度/网络/存档/统计六类职责同处一类，仅靠方法名前缀区分；`refresh()` 被 250ms 定时器驱动，又串联终局副作用、模态弹窗与 AI 重启。
影响：改动集中在巨型类，任何触碰都可能连带终局与弹窗路径；单类无法单测（必须起 QApplication）。
建议：沿已拆的 `ui/workers.py` 继续切：`GameSession`（self.game+tick+终局哨兵）、`NetSession`（network/revision/sockets 方法）、`SidePanel`（history/captured/chat 构建刷新）；MainWindow 只留装配与信号连线。
```

```
[1-2] P2 · 结构
位置：desktop/app.py:561、:586
成因：桌面键 snake_case（theme/background/piece_style）与云端 camelCase（boardTheme/pageBackground/pieceStyle）的映射表**两处各手写一遍**（拉取/推送）。
影响：新增设置项只改一处时，云端同步静默丢键、不报错；映射与 `config.DEFAULTS` 无编译期联系。
建议：提取 `config.CLOUD_KEYS: dict[str,str]` 单一常量供两处引用，并加测试断言 `set(CLOUD_KEYS.values()) <= set(DEFAULTS)`。
```

```
[1-3] P2 · 结构
位置：docs/ARCHITECTURE.md:12-14；docs/FEATURES.md:13
成因：文档滞后于实现：架构表仍写 desktop_complete “全部 14 类棋子”（实为 11 类/50 枚），档案描述漏「尉」；FEATURES 写“四档 AI”（实为六档，含 expert/master）。
影响：照文档做判断会直接错；ARCHITECTURE 那张表是**错值**，比缺项更有害。
建议：按 `docs/DOCS_PLAN_2026-10-31.md` C1–C4 修正，修完并入项目 README。
```
**否定的怀疑项**（避免重复怀疑）：`config` 键集合闭合——桌面用 32 键、`DEFAULTS` 33 键，**差集为空**（仅 `schema_version` 未在 UI 侧引用）；`TODO/FIXME/if False` 全仓 **0 处**；`_SquareHost`(app.py:87→:170)、`AnalysisWorker`(9 处)、`HttpWorker`(7 处) 均有引用，无孤儿；`web/js/app.js` 内 `pseudoLegal/inCheck/legalMoves` **0 处**，网页是薄客户端、规则仅服务端实现，不存在双份规则引擎。

## 二、内存与资源管理

```
[2-1] P2 · 内存
位置：desktop/app.py:174（创建）、:283/:286（写入）
成因：`self.chat_messages` 是无上限 QListWidget，AI 挑衅与联机聊天都 `addItem`，既无条数上限，`new_game()` 也不清空。
影响：挂机/长会话时 item 线性增长，滚动重排成本随之上升；单会话数百条不致命，长时间累积才显现。
建议：写入处加 `MAX_CHAT_ITEMS=200` 裁剪（超出 `takeItem(0)`），并在 `_reset_ui_cache()` 一并 `clear()`。
```

```
[2-2] P2 · 内存/性能
位置：service/rooms.py:358；desktop/ui/workers.py:48；core/ai.py:196-205
成因：每步 `ChessAI(difficulty)` 新建，`transposition`/`evaluation_cache`/`see_cache` 都是实例属性，且 `choose_move` 每次主动 `clear()` → **跨步零复用**。
影响：非泄漏，而是每次搜索从冷缓存起步；同一局面在长对局中反复出现也无法受益，12s 档前段在重复计算。
建议：三张缓存提为类级（带容量上限）或由调用方持有实例复用；复用前需先改 `ai.py:196` 的无条件清表策略。
```

```
[2-3] P2 · 内存 —— 未验证
位置：core/model.py:118（`GameState.clone` = `from_dict(to_dict())`）
成因：`clone()` 全量序列化再反序列化，`to_dict()` 重建整条 `history`（含 notation/timestamp）与 captured 池；每次 AI 起手（workers.py:47-49）与每次服务端落子（rooms.py:357）都克隆。
影响：克隆成本随手数线性增长；300+ 手时每步固定开销从几十 µs 抬到 ms 级（相对 12s 可忽略，但垫高每步成本）。
建议：先测再加 `clone_for_search()`，只拷 pieces/turn/position_counts/captured；或用浅拷贝 + 对 history/pieces 做 `copy.copy`。
未验证：需构造 100/300/600 手局面测 clone 耗时曲线。本轮 `build_position(600)` 约需 220 s，未跑完，故不断言。
```

**否定的怀疑项**：音频无泄漏（`audio.py:63-65` 切包对旧 `QSoundEffect` 逐个 `deleteLater()` 再清 dict）；位图缓存有界（`piece_assets.py` 的 `_RAW`/`_SCALED`/`_MISSING` 键域 = 风格×11 型×2 色，`preload` 只热当前风格）；房间字典有回收（`rooms.py:479-497` cleanup，ai/local 无连接 1800s、终局 3600s，由 `app.py:71-72` lifespan 周期调用）；棋谱列表有界（仅 `history_key` 变化时 `clear+addItems`，长度=当前对局手数）。

## 三、并发与线程安全

```
[3-1] P2 · 并发
位置：desktop/app.py:269、:271-275
成因：`start_ai` 置 `board.locked=True` 后投 worker 到 QThreadPool，仅靠 `finish_ai`/`ai_failed` 两个信号解锁，**无超时兜底**；`cancel` 只作用于搜索内部，管不到“信号没送到”。
影响：worker 若因异常路径未发信号（或线程池饱和未执行），棋盘与"思考读条"永久保持，只能重启。
建议：`start_ai` 同日 `QTimer.singleShot(limit*1000+2000, self._ai_watchdog)`；watchdog 判定"仍在思考且 cancel 未置位"则强制 `cancel.set()` + 解锁 + 提示。
```

```
[3-2] P2 · 并发 —— 未验证
位置：service/rooms.py:151、179、191、202、224、235、250、352（8 处 `async with room.lock`）
成因：房间锁覆盖面广，部分段落可能含 `await`（落子后广播/场景广播）。已确认安全的两处：`_play_ai`（锁内只取快照 :352-357，长任务锁外跑，写回前校验 history+turn :361-366）、`join`（锁内仅改内存 seat）。
影响：若某段在持锁期间 `await broadcast`，慢客户端会阻塞同房间其他请求（含对手走子）。
建议：核对这 8 处，把 `await broadcast/send` 一律移出锁外（先取快照再发）。
未验证：未逐条核完 8 处锁内的 await，只确认了上述两处。
```

**否定的怀疑项**：`_play_ai` 的乐观并发正确（锁内快照→锁外搜索→锁内校验 history+turn，不符即丢弃）；`CONFIGS`（`ai.py:64`）生产代码只读（`grep 'CONFIGS\[' src` 全为取值，无赋值），模块级状态无被改写风险；桌面 `AIWorker.__init__` 已 `Game.from_state(game.state.clone(), ...)`（workers.py:47-49），与服务端一样**不共享可变 GameState**；`cancel` 语义成立（`_guard` 逐节点检查，桌面每条退出路径都 `is_set()` 丢弃结果，app.py:273、:289）。

## 四、边界条件与异常处理

[B-01] P1｜边界｜core/model.py:36-38、:200-209
成因：`Position` 是裸 frozen dataclass，无 `__post_init__` 范围校验；存档 row/col 直接 `int()` 入对象，不校验 `0 ≤ v < rows/cols`。
影响：坐标写坏的 .xhgame 静默载入。实测红王改 (-1,-1)：载入成功、`in_check(red)=False`、红方仍有 106 合法着法、该王**永久不能动**（`pseudo_legal` 先查 `inside(source)`）→ 出现"无王可吃、无人被将"的僵尸局，胜负判定整体失真。
建议：在 `GameState.from_dict`/`piece_from_dict` 入口按 `profile.rows/cols` 校验并抛 `ValueError`；`game_from_document` 补"每方恰一王、无重叠格"断言。复现：`GameState.from_dict({"profileId":"x","pieces":[{"id":"a","type":"king","color":"red","row":-1,"col":-1}]})` 不报错。

[B-02] P1｜边界｜service/app.py:336-341、:291-305
成因：`receive_envelope` 只 catch `ValidationError`，而 `receive_json()` 对非法 JSON 抛 `JSONDecodeError`；外层只 catch `WebSocketDisconnect/GameError`。
影响：客户端发一段非 JSON 即打穿连接，且**跳过** `manager.disconnect` → 座位 `connected=True` 残留，对手看到"在线"，重连/回收判定被污染。
建议：`except (ValidationError, JSONDecodeError, UnicodeDecodeError)` 统一 close(1002)；`finally` 无条件 `await manager.disconnect(...)`。复现：连上后 `send("not json")`，看服务端 Traceback 与 seats 状态。

[B-03] P2｜边界｜core/model.py:149-150、core/storage.py:78-104
成因：`from_dict` 用 `data["profileId"]`/`data["pieces"]` 硬取，缺字段抛 `KeyError`；对外契约却是"坏档 → ValueError"。
影响：只 catch ValueError 的调用方会漏；桌面 `app.py:491` 用 `except Exception` 兜住，但弹窗变成裸 `'pieces'`。题库/归档路径无兜底。
建议：统一 `_require(data,key)` 包成 `ValueError("棋谱缺少字段 pieces")`。

[B-04] P2｜边界｜core/model.py:208-209
成因：`int(data["row"])` 接受 `3.7→3`、`"3"→3`、`True→1`。
影响：坐标类型错误的存档被"就近修正"到另一格，位置悄悄改变，比报错更难查。
建议：先 `isinstance(v,int) and not isinstance(v,bool)`，再判范围；字符串一律拒。

[B-05] P2｜边界｜service/app.py:336-338、service/rooms.py:258-266
成因：WS 读帧无体积上限（uvicorn 16MB 才拒），chat 的 80 字限制在**解析后**；`payload: dict[str,Any]` 其余类型不看体积。
影响：数 MB 单帧被完整解析进内存再丢弃，多连接下可做廉价内存放大。
建议：`receive_json()` 前 `receive()` 判 `len(text)>N` 直接 close，或校验 payload 序列化长度。

[B-06] P1｜边界｜core/puzzles.py:88、:71-73
成因：加载对 `item["solution"]` 硬取；`Puzzle.exercise()` 遇非法解步 `except ValueError: break` 静默终止。
影响：**题库出错时静默降级**。解法写错/规则改动后题目照常进列表，玩家按"正解"走却被 `Game.move` 抛错吞掉 → **表现为"题目走不动、永远解不掉，且没有任何提示"**；随包 **13 题**（实测逐条数出，原文写 16 是笔误）无加载期校验门禁。这类"看着正常但数据不对"比崩溃更难排查。
建议：加载时逐题 `game_from_document` + 逐步 `is_legal` 全量校验，失败抛 `ValueError(f"puzzle {id} illegal at step {i}")`；`exercise()` 的 break 至少 `warnings.warn`。

## 五、潜在逻辑缺陷

[L-01] P1｜逻辑｜core/game.py:109-111
成因：`resign()` 只写 `winner/result_reason`，不判 `state.finished`，不校验 `color` 是否为在局方。
影响：实测①和棋后 resign → `draw=True` 且 `winner=red` 同时成立（结果二义，统计/文案取值分叉）；②终局后任一方再认输可**翻转** winner。
建议：`if state.finished: raise GameError`；`draw` 与 `winner` 写入前互斥清空。复现：`g.state.draw=True; g.resign(Color.BLACK)` → `winner=red, draw=True`。

[L-02] P1｜逻辑｜core/game.py:85-91
成因：`undo()` 只判 `plies` 与快照数，不判终局；快照不含 `winner/draw`，恢复即"复活"。
影响：实测认输/被将死后 `undo(1)` → `finished=False, winner=None` 继续可下。桌面 `undo_move`（app.py:302）无终局守卫 → 已计入统计的一局在棋盘上复活再分胜负，**同一局记两次结果**。
建议：`undo` 加 `allow_after_finish=False` 默认拦；终局后禁用悔棋入口或走"重开"。

[L-03] P1｜逻辑｜core/game.py:59 与 :69，配合 :198-208
成因：`move()` 先 `tick()`，而 `tick()` 在未超时时把 `turn_started_at` 重置为 now（:208）；:69 再用重置后的值算 `elapsed`。
影响：实测 sleep 350ms 落子 → `elapsed_ms=0`，同时钟已扣 413ms。所有 `elapsedMs`（棋谱/复盘/每手用时统计）恒为 0。
建议：`tick()` 返回本次扣减毫秒，`move()` 直接用它；或 `move()` 开头取一次 `now`，先算 elapsed 再 tick。

[L-04] P2｜逻辑｜core/ai.py:666-670
成因：`_activity_score` 用 `pseudo_legal` 判攻击关系，未过自将过滤（`is_legal`）。
影响：把"走完自己就被将"的着法计为有效攻击/压力，估值偏高；只影响权重不影响出着合法（根节点仍走 `legal_moves`）。
建议：若为性能保留 pseudo_legal，则对被己王牵制的攻击打 0 折；`in_check` 时切 `is_legal`。

[L-05] P1（已实测坐实；设计歧义待确认）｜逻辑｜core/rules.py:723-745、:266-272
成因：三连吃子对**全盘**扫描，只要"己方两子（至少一枚兵）+ 敌方一子"成直线即吃，与"移动的那枚兵"无关；`dict` 按 id 去重、按扫描序返回，多组连线一次全吃。
影响：**任一兵移动都会收割全盘所有既成三连线**。实测（`pawn_three_line_capture=True`）：红方走合法兵步 (8,4)→(7,4)，棋盘另一端 (2,8)红车+(2,9)红兵+(2,10)黑士 早已成线 → **黑士被带走**；该线在移动前就存在，不是本手形成的。玩家观感是"走一步无关的兵，远处突然少了个子"。
建议：扫描限制在移动兵所在行/列/两对角（与 `_three_line_mover` 的"移动触发"语义一致）；若确要全局被动效果，须在 `PIECE_RULES.md` 写清并在 UI 提示。
最小复现：`Game("desktop_complete", {"pawn_three_line_capture": True})` + 手工 `GameState`（红王12,6／黑王0,4／红车2,8／红兵2,9／黑士2,10／红兵8,4，红先）→ `board_removals(state, Move((8,4),(7,4)))` = `[advisor@(2,10)]`。

[L-06] P1（已实测坐实）｜逻辑｜core/game.py:267
成因：判和取 `max(state.position_counts.values())`，不是**当前局面**的 key 计数。
影响：实测把账本改成 `{"stale-key": 5, 当前key: 1}` 后调 `_settle` → `draw=True / threefold_repetition`，**当前局面只出现过 1 次却被判三次重复**。正常对局每手都结算、`max≥3` 只在计到 3 那手成立，故日常不可达；但 `from_state`／存档／导入／网络注入历史 `positionCounts` 后，**之后每手都会立刻判和**。
建议：改为 `position_counts.get(self.rules.position_key(self.state), 0) >= 3`；`from_dict`/`from_state` 侧统一用 `_rebuild_position_counts` 重建账本（storage 已有，网络路径未走）。

[L-07] P2｜逻辑｜core/rules.py:433-454
成因：`position_key` 格式为 `turn|board||pool:`，**不含 `rule_options`**；`position_counts` 却随 `Game.from_state(state, options)` 被带进**选项不同**的新对局。
影响：实测同开局、三种不同 options（`pawn_three_line_capture` / `enforce_self_check` 各异）的 key **完全相同**。出现"同一份账本 + 换了规则选项"的路径（联机 `rooms._play_ai` 的 `Game.from_state`、导入后改选项、跨档载入）时，重复判定按旧选项的历史计数生效。`positionKeyVersion` 只标 key 格式版本，不校验 options 变化。
建议：key 加入影响合法着法/吃子的选项摘要（至少 `enabled_piece_types` + `pawn_three_line_capture` + `pawn_promotion`）；`from_state` 时 options 与账本来源不一致则重建。理由与 `position_key` 注释里"pool 影响合法着法故入 key"同源。

## 六、安全漏洞与作弊风险

（实测环境：`TestClient(app, raise_server_exceptions=False)`，2026-10-31；每条都注明是否跑通）
[S1] P0 · 安全（未捕获异常，任何人都能触发）
位置：src/xionghan_chess/service/app.py:410、:446（`game_from_document` 未 import；文件头只导入 `game_from_content`/`game_document`，app.py:24-25）
成因：调用了不存在的名字 → `NameError`，而 except 只捕 `(ValueError, KeyError, TypeError)`，NameError 直接冒到 500
影响：`POST /api/analysis` 与 `POST /api/me/games`（云存档保存）**必 500**；实测 register 200 → `POST /api/me/games` 500，`/api/analysis` 500 → 分析与云存档两个功能全废
建议：补 `from xionghan_chess.core.storage import game_from_document`（storage.py:57 已存在）；两个端点各加一条冒烟用例，防止再次"测试全绿但端点 500"
[S2] P0 · 安全（可用性耗尽，匿名可打）
位置：src/xionghan_chess/service/rooms.py:106-122（建房无鉴权，仅 `max_rooms=200`）+ rooms.py:475-497（cleanup）
成因：online 房创建后 `connected=False` 且 `disconnected_at=None`；`expired` 要求 `disconnected_at` 非空、`abandoned` 只覆盖 ai/local → **该房永不回收**
影响：实测匿名循环建房：前 200 个 200，第 201 个 400「在线对局数量已达上限」；`manager.cleanup()` 后房间仍在（True）→ 任何人 1 分钟即可让**全站无法开局**，直到进程重启
建议：对"从未建立 socket"的房加 `created_at` TTL（如 10 分钟）；建房按 IP 限流；上线前把建房改为需登录或需人机校验
[S3] P1 · 安全（规则篡改）
位置：src/xionghan_chess/service/app.py:89（`options: dict[str, object]`）→ rooms.py:110 `Game(profile_id, options, …)`
成因：options 无白名单、无类型转换，原样进 `RuleOptions`；实测传 `{"pawn_promotion":"yes"}` 后 `room.game.options.pawn_promotion == 'yes'`（str，truthy）
影响：建房者可预置开关（强制升变/复活/送将等），对手加入时界面显示与真实规则不一致 → 直接构成作弊面，且对手难以察觉
建议：options 用显式 pydantic 模型（键白名单 + `bool`/`int` 严格类型）；`RuleOptions` 构造处 `bool()`/`int()` 归一，拒绝未知键
[S4] P1 · 安全（资源放大）
位置：src/xionghan_chess/service/app.py:85（`player_name`）、:100（Join）、:145（`SpectateRequest.display_name`）——均无 `max_length`
成因：名字长度不限，直接进 snapshot 并在每次广播时整体复制
影响：实测 1 MB 名字建房成功（13 ms），snapshot 13,172 B → **1,013,171 B（77×）**；配合 5 s 广播 × 每 socket 序列化 → 内存与带宽放大，多房并发可拖垮事件循环
建议：`Field(max_length=32)`（与 `ProfileRequest` 对齐）；写入前 strip + 截断
[S5] P1 · 安全（凭据经 URL 泄露）
位置：src/xionghan_chess/service/app.py:245（`GET /api/rooms/{id}?token=`）、:288、:310（WebSocket `?token=`）
成因：座位 token 走 query string
影响：uvicorn/反代 access log、浏览器历史、Referer 全部留存；拿到 token 即可以该座位走子/认输/暂停（`seat_for` 只比对 token）。利用步骤：读一条 access log → `wss://…/ws/ROOM?token=…` → 接管该座位
建议：HTTP 改 `Authorization: Bearer`；WS 改首帧 AUTH 消息或 `Sec-WebSocket-Protocol`；access log 关闭 query 记录
[S6] P2 · 安全（信息泄露）
位置：src/xionghan_chess/service/app.py:244-249（`room_state(token: str | None = None)`）
成因：不传 token 也返回完整 `public_state` + `chatHistory`
影响：实测无 token 直接 200，响应 13,172 B（含 62 子、双方名字、最近 20 条聊天）；房间号 36^6≈2.2e9 难枚举，但链接一旦外泄（群/截图）即可静默围观并读聊天
建议：无 token 只返回 `{roomId, mode, revision, players}` 精简体，完整局面要求 token
[S7] P2 · 安全（导入不校验可达性）
位置：src/xionghan_chess/core/storage.py:76-80（`if snapshots and len(snapshots) != len(history)`）
成因：`snapshots` 为空时整段一致性校验被跳过，`state` 直接采纳，不按 `history` 重放
影响：可导入"棋盘与棋谱不符"的局面（如对手已被吃光）进 ai/local 房骗 AI；online 已被 app.py:212 禁止，不跨用户传播，故 P2
建议：`snapshots` 改必填；或导入时从初始局面重放 history 并与 state 比对

## 七、网络同步与状态一致性
[Y1] P1 · 同步（乱序/重放保护可被绕过）
位置：src/xionghan_chess/service/rooms.py:255-257
成因：校验条件为 `envelope.revision is not None and envelope.revision != room.revision` —— **客户端不填 revision 即跳过**
影响：可发送乱序 MOVE/PAUSE/UNDO；online 靠 `turn is seat.color`（rooms.py:273）兜底，但 `local` 房任何持 token 者可走双方、无兜底 → 乱序消息直接生效
建议：状态变更类（MOVE/PAUSE/RESIGN/UNDO_*/RESTART_*/RESURRECT）强制要求 revision，缺失即拒
[Y2] P2 · 同步（无幂等键）
位置：src/xionghan_chess/service/rooms.py:249-337（`requestId` 仅回显，不参与去重）
成因：没有消息序号/去重表
影响：弱网重发同一 MOVE 在 online 被 turn 挡住；但 `DRAW_OFFER`/`RESTART_REQUEST`/`PAUSE` 重发会重复改状态（重复弹窗、pending 被覆盖）
建议：每座位单调 `seq` + 最近 N 条 `requestId` 去重
[Y3] P2 · 同步（同一 socket 上广播可能乱序）
位置：src/xionghan_chess/service/rooms.py:406-436（锁内构造 payload、**锁外** send）
成因：`maintenance()` 与 `handle()` 是两个协程，都可能在锁外并发发送
影响：同一连接上后构造的快照可能先到达，前端若不按 revision 单调过滤会"闪回"一步
建议：每 socket 一条 `asyncio.Queue` 串行发送；或前端 `if (rev <= lastRev) return`
[Y4] P2 · 同步（判负与回收口径不一致）
位置：src/xionghan_chess/service/rooms.py:481-492
成因：`expired` 依赖 `disconnected_at`（只有连过才有），`abandoned` 只覆盖 ai/local
影响：从未连过的 online 房既不判负也不回收（与 S2 同源）；已连过且双方断开的房 90 s 判负后仍要 1 h 才删，期间占名额、仍参与 5 s tick
建议：统一 TTL（`created_at`/`last_activity` 双阈值），判负后立即进入待删队列

## 八、性能瓶颈

（`PYTHONPATH=src`，本机实测，2026-10-31；均为中位数）
[P1] P0 · 性能（广播载荷随步数线性膨胀）
位置：src/xionghan_chess/core/game.py:239 `data["replay"] = [...snapshots] + [state.to_dict()]`（随 `public_state()` 下发）+ service/rooms.py:411-415（每 socket 单独 `json` 序列化）
成因：每次广播都携带**每手一个完整局面快照**（`MAX_SNAPSHOTS=512`，game.py:24）
影响：实测开局 **13,172 B** → 60 手 **2,289,176 B**（+174×，其中 `replay` 占 2,218,806 B）；理论上限 512 手 ≈ **19 MB/次**；2 人房 5 s 一次 ≈ 0.9 MB/s，观战者线性叠加
建议：广播只发 `state` + `revision`，复盘改按需 `GET /rooms/{id}/replay`；或只带最近 K 步快照
[P2] P1 · 性能（legal 端点放大）
位置：src/xionghan_chess/service/app.py:262-282
成因：每请求全量 `legal_moves`（实测 72 ms）后，再对**每个**着法调 `captured_by_move`（内部 `_apply_move` 克隆整盘状态）
影响：实测 **84 ms/次**（18 个着法）；前端 `pointerdown` 即触发；无缓存、无限流 → 单客户端 ~12 req/s 打满一个核，200 房并发时同归于尽
建议：按 `(position_key, source)` 缓存到 `room`；同一 token 60 ms 内合并；加每 token 频率上限
[P3] P2 · 性能（搜索节点成本高）
位置：src/xionghan_chess/core/rules.py:187-207（`_iter_legal` 全量枚举）、core/ai.py:186-206
成因：每个搜索节点都做"62 子 × 169 目标格"的双重循环 + 逐着法 `is_legal` 克隆
影响：实测 `legal_moves` **72 ms**、`has_any_legal_move` **1.8 ms**（已短路）；`choose_move` medium **5,033 ms**、hard **12,003 ms** 全部**撞满预算**（5 s/12 s）→ 所谓"更强"是烧完预算，不是算法更快；13×13 深度 2 仅 119 节点即 6.5 s
建议：`legal_moves` 改"按子生成 + 目标格预筛"（或缓存每子的可达集）；`_evaluate` 实测 2.77 ms 已可接受，不必动
[P4] P2 · 性能（前端每帧全量重绘）
位置：web/js/app.js:142 `draw()`、:173 `animate()`（`requestAnimationFrame` 每帧 `draw()`）、drawPiece 内 `shadowBlur=5`
成因：每帧清屏重绘棋盘线+62 枚棋子，且每枚棋子都开 Canvas 阴影（软件合成，逐枚付代价）
影响：动画期间 60 fps × 62 次阴影绘制；叠加 `pointerdown` 的 84 ms legal 请求，低端设备明显掉帧
建议：静态层（网格/星位/底纹）离屏缓存成一张位图；动画只重绘变动矩形；阴影改预渲染或去掉
补充（未发现问题）：事件监听仅在 app.js:208-210 绑定一次，`draw()` 内不重复绑定，无监听泄漏
