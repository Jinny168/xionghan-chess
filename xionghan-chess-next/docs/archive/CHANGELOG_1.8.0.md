# 匈汉象棋 v1.8.0 更新日志

> 本版本主线为「两轮审计的可施工部分」：两条 P0（端点必 500、僵尸房占满配额）、座位 token 移出 query
> （**破坏性变更**）、广播去 replay，以及网页 CSS 令牌化与桌面危险色校正。
> 下列条目均可回溯到提交 hash；未落地的事项统一列在最后一节，不做「已修」表述。

## 破坏性变更：座位 token 移出 query string

- **凭据不再走 URL（`58143aa`，审计 S5）**：token 放 query 会被写进 access log、浏览器历史与 Referer，
  属**持续**泄露，刷新页面也摆脱不掉。改法：
  - REST：`room_state` / `legal_moves` 读请求头 `X-Room-Token`；query 里带 token **显式拒绝** →
    `400 token 请放请求头 X-Room-Token`；
  - WS：`/ws/{room_id}` 与 `/ws/{room_id}/spectate` 不再收 query token（带了 → accept 后立刻 `close(4401)`）；
    正常流程是 accept 后读**首帧** `{"type":"auth","token":...}`，5 秒内没收到 / 非法 JSON / 字段不对
    一律 `close(4401)`，不留半连接；
  - `RoomManager.connect()` / `connect_spectator()` 加 `accepted=True` 形参 —— 握手已做过，不能二次 accept。
- **三个客户端同笔同步**：`web/js/app.js`（`api()` 注入头、`socket.onopen` 首发 auth 帧）、
  `desktop/net.py`（`ws_url` 去掉 token，新增 `encode_auth`）、`desktop/app.py`（`_network_connected`）。
- **不做兼容期**：留一条兼容路径等于留着泄露渠道。**旧版 EXE 无法连接 1.8.0 服务端**，需重打包。
- 自证与回归：`grep -rn "?token=" web src --include=*.js --include=*.py` **0 命中**
  （测试里那处字面量是**故意**用来验证「拒绝」的）；新增 `tests/test_token_transport.py` 6 条
  （REST 拒 query / 收 header、WS 拒 query token、首帧 auth 接通、非法首帧 4401、超时 4401），
  另把 5 个既有测试文件改到新握手。
- WS 未用 `Sec-WebSocket-Protocol`：部分代理会剥掉该头，浏览器兼容参差；首帧方案在三端是同一套代码。

## 服务端：两条 P0 与边界加固

- **`game_from_document` 未导入（`e619bfe`，S1，P0）**：`/api/me/games` 与 `/api/analysis` 调的是这个名字，
  实际只导入了 `game_from_content` → `NameError` 不被 `except (ValueError, KeyError, TypeError)` 捕获 → **必 500**。
  云存档保存与分析此前**全废而单测全绿**（core 覆盖很全，端点一次没打过）。补导入一行，
  并加两条「端点不为 500」的冒烟用例。
- **匿名建房占满配额（`e619bfe`，S2，P0）**：`cleanup()` 的 `expired` 要求 `disconnected_at` 非空、
  `abandoned` 只覆盖 ai/local → **从未建立 socket 的 online 房永不回收**，200 次 POST 即可让全站无法开局。
  新增 `ZOMBIE_ROOM_SECONDS = 600`：online + 无 socket + 创建超 10 分钟 → 回收。
- **options 无类型校验（`e619bfe`，S3）**：新增 `validate_rule_options()` 按 `RuleOptions` 字段逐键校验——
  布尔只收 `bool`、整数只收 `int`（`no_progress_draw_plies` 限 10–500）、**未知键直接 400 并点名**。
  否则 `{"pawn_promotion": "yes"}` 会被当成 truthy 悄悄开一条规则，对手界面显示与真实规则不一致。
- **WS 非法 JSON 打穿连接（`3df2a4a`，B-02）**：`receive_envelope` 只捕 pydantic 的 `ValidationError`，
  而 `receive_json()` 对非法 JSON 抛 `JSONDecodeError` —— 它直接穿透，既不回错误帧，也不进
  `manager.disconnect()`，结果「连接断了但座位仍显示在线」。新增 `_reject_protocol()`
  （先回 ERROR 帧、失败即吞掉，再 `close(1002)`），两类异常都走**与正常断开同一条清理路径**。
- **WS 单帧无体积上限（`13f418c`，B-05）**：改为**先收文本、判 UTF-8 字节数、再解析**
  （`receive_json()` 不暴露原始长度）。`MAX_FRAME_BYTES = 64 * 1024` 定为**常量而非配置**：
  正常消息都在 1 KB 量级，64 KB 已有两个数量级余量；做成可配置只会让人调大而不是调对。
- **玩家名无上限（`5ce3111`，S4）**：实测 1 MB 名字建房成功，快照从 **13 KB 涨到 1.01 MB（77×）**，
  而快照每 5 秒广播一次。`MAX_PLAYER_NAME = 24`（pydantic 的 `max_length` 按**码点**计，不是字节），
  **不静默截断**（截断会让两个名字撞成一个）；新增 `RequestValidationError` 处理器 → **400**
  （FastAPI 默认 422，客户端只看到 "unprocessable"），提示点名字段。
- **local 房 revision 可绕过（`6fc4a41`，Y1）**：原判断 `revision is not None and revision != room.revision`
  —— **不填就整段跳过**。online 房还有 `turn is seat.color` 兜底，local 房没有。改为 local 房缺 revision
  直接拒；online 房行为完全不变。

## 性能：广播快照去掉 replay

- **`public_state()` 加 `include_replay` 开关（`a9633a4`，审计 P1）**：原来每次广播都携带**每手一个完整局面快照**
  （`MAX_SNAPSHOTS=512`）。实测开局 13 KB → 60 手 2.29 MB（77×），理论上限 512 手约 19 MB/次，
  且**每个 socket 单独序列化**、5 秒一次。
- **只把 replay 从常规广播里摘掉**：`broadcast()` 两处传 `False`；默认值仍是 `True`（存档/导入依赖它）。
  复盘改由入房/重连**单独下发**——`Room.fresh_tokens` 记录刚接入的 socket，其第一条 STATE 带完整 replay，发完即清空。
- **为什么不是「connect 里额外发一帧」**：先试过，**5 条 service 用例立刻红**——那些用例依赖「一问一答」的
  消息计数，多一帧会读到上一条。改成「首帧带 replay、之后不带」，消息条数与顺序都不变。
- 实测（同一 60 手局面）：带 replay **319,631 B** → 不带 **7,848 B**，降幅 **40.7×**；
  入房 replay 长度 **61**（60 手 + 当前局面）。
- 前端**不依赖** `snapshot.replay`：网页复盘走 `history`（`replayGame()`），全仓 grep `.replay` 只命中前端
  自己的 `replaySource / replayIndex / replayDialog`，故网页端零影响、未改任何前端逻辑。

## 判和口径：选项摘要并入 `position_key`

- **key 加 `||opt:` 段（`eb13a4c`，L-07）**：`position_key` 只含局面 + 池，而 `positionCounts` 会随存档/导入/网络
  被带进**选项不同**的新对局——那些计数按旧选项算，于是「两种规则下的同一盘面」共用一份计数。
  末尾追加 `p3l<0|1>-promo<0|1>-self<0|1>`（三连吃子 / 升变 / 自将过滤，三项都直接影响合法着法）。
- **`POSITION_KEY_VERSION` 2 → 3**：旧存档 counts 作废，key 不匹配即从 0 计，最坏是「已重复 2 次的局面重新计」，
  **不会误判和**。离线端 `positionKey` 同构追加，题库数据随之重生成（否则 `test_generated_data_is_up_to_date` 红）。
- 新旧 key 样例（同一开局局面）：

  ```
  旧 v2: red|black:king:0:10;red:king:11:6;…||pool:
  新 v3: red|black:king:0:10;red:king:11:6;…||pool:||opt:p3l0-promo1-self1
  ```
- **判和只看当前局面（`393f5ec`，L-06）**：`max(counts.values()) >= 3` 会让「历史上任何局面重复三次」触发判和，
  注入一个 stale key 就能误判。改为 `counts.get(rules.position_key(state), 0) >= 3`。
  同笔删掉只写 `position_counts = {"whatever": n}`、**一步棋都没走**的假构造器，换成真走棋的 `CYCLE`
  （红车 `(9,9)↔(9,10)`、黑王 `(0,4)↔(0,5)`，4 拍一轮回到同一局面）；两条「同时满足时谁优先」的用例
  改为给**当前 key** 注入 3 次并标注为白盒。直接证据写进 docstring（`5291c88`）。

## 规则内核与终局判定

- **三连吃子只结算移动兵参与的线（`36bfe2f` / `ffac627`，L-05）**：原实现是**全盘扫描**——走一步无关的兵，
  远处「移动前就已存在」的线也会被收割（实测红兵 `(8,4)→(7,4)`，把 `(2,10)` 的黑士带走）。
  改为只检查含落点的 4 向 × 3 偏移 = **12 个窗口**，窗口内三子紧挨、两我一敌（顺序不限）、至少一枚兵、
  **移动兵必须在窗口内**。`offline.js::threeLineCaptures` 同构替换。
  单拆一笔先统一签名与调用点（`ffac627`，行为不变），再换实现，便于二分。
- 配套：6 条用例矩阵 + 「`capturable_squares` 的 three_line 项 == 真走一步实际移除的子」不变量（`a0e1761`）；
  2 条**定向对拍**（79 ⇒ 81，`6d8cc53`）——批量门禁只比 `legalAll` + `inCheck`，三连吃子改的是 removals，
  **这条规则再被改坏，79 条对拍一条都不会红**。三处文案（两份 `PIECE_RULES.md` 逐字节相同 + `piece_rule.pawn_long`）
  同笔同步。
- **终局守卫与 `elapsed_ms`（`17c92a6`）**：
  - L-01：终局后认输会把 `winner` 从 draw 翻成对手胜、且 `draw=True` 与 `winner=red` 并存 → `state.finished`
    为真时抛 `GameError`，`winner/draw` 一律不动；
  - L-02：认输/被将死后 `undo(1)` 会把 `finished=False, winner=None`（同一局记两次结果）→ 默认拒绝；
    题目/训练「重来一题」这类**有意允许**的路径必须显式传 `allow_finished=True`；
  - L-03：`tick()` 在未超时时把 `turn_started_at` 重置为 now，之后再拿它算 elapsed 必然是 0
    （实测睡 350 ms 记 0，而钟已扣 413 ms）→ 改为在 `tick()` **之前**取 `started_at` 快照。
- **读档按 profile 校验坐标（`2232cc4`，B-01）**：王在 `(-1,-1)` 的存档能静默载入，`piece_at` 取不到 →
  「无王可食、无人被将」的僵尸局。新增 `_assert_in_bounds(profile, state, where)`，**上下界都查**，
  当前局面与每一步复盘都查，抛 `UnsupportedSaveError` 并给人话（`row=-1, col=-1（棋盘 13×13）`）。
- **一处与规格不同，必须说明**：规格要求在 `Position.__post_init__` 校验非负。按规格做完后**实测 63 条测试红**
  ——AI/规则引擎用 `Position(row + dr, col + dc)` **探测越界格**，靠 `get()` 返回 None 判出界。
  改成「值对象可构造任意整数，越界防线放在唯一外部入口 `game_from_document`」，并加
  `test_position_itself_allows_out_of_board_probes` 钉住「不要在值对象里加范围校验」。

## 题库

- **加载期校验解步合法性（`bc2864c`，B-06）**：`Puzzle.exercise()` 里 `except ValueError: break` 把非法解步吞掉，
  题目照常进列表、玩家点进去永远解不出且没有信号。新增 `_validate_solution()`：用
  `game_from_document(puzzle.document)` 重放一遍解法，任何一步走不通就
  `ValueError: 题目 P-xx《标题》第 N 步无法走：…`，**坏题让加载失败**（不跳过）。
  选「启动失败」而非「跳过 + 告警」的理由：内置题库是随代码发布的产物，坏题属构建期缺陷；
  「跳过」正是当前缺陷的形态。实测加载 13 题 **0.31 s**，代价可忽略。
- **题目数 16 → 13（`e7bd2ce`）**：审计原文的 16 是笔误，实测逐条数出 13 条。

## 桌面端交互缺陷

- **AI 思考看门狗（`dfcda35`，3-1）**：解锁只靠 worker 的 `finished/failed` 两个信号，worker 崩在原生代码里
  或卡死时**棋盘永久锁死**。`start_ai` 改排 `QTimer.singleShot(预算 + 5 s)`；用世代号 `_ai_generation`
  区分局次（上一局的看门狗到点发现编号不符即什么都不做）；新增 `_release_ai()` 作为 AI 收尾**唯一出口**
  （成功 / 失败 / 超时三条路都走它）；超时先 `cancel.set()`，迟到的结果会在 `finish_ai` 里被丢弃。
- **一处必须保留的细节**：`_end_thinking()` 仍在 `cancel.is_set()` **之前**——取消路径不进解锁分支，
  少了它会出现「取消后读条还在爬」，`test_cancel_exit_also_stops_the_timer` 正是盯这个的。
- **聊天记录有界（`2985d54`，2-1）**：`chat_messages` 只追加不清空。新增 `CHAT_HISTORY_LIMIT = 200`，
  `_append_chat()` 作为**唯一**追加入口（超限 `takeItem(0)`），两处 `addItem` 全部改走它；
  `new_game()` 里 `chat_messages.clear()`；**悔棋不清空**（聊天是历史，不该被悔棋回滚）。
- **对话框按内容收缩（`0ef4ab8`）**：`_fit_to_content()` 在事件循环**第一拍**收到 `sizeHint() * 1.2`
  且不低于 `minimumSize()`（`__init__` 阶段字体还没加载，量出来偏小）。Document 空白 87% → **55%**、
  Library 73% → **54%**；再小就违反几何审计定的下限，故停在 54–55% 并如实登记。

## 桌面配色：危险色与将军横幅

- **将军横幅文字改成 `banner_fg`（`668f42e`，B-1）**：先取证——临时把文字改哨兵色后渲染取色，
  横幅内 4,865 点主色是 `#7f1d1d`（**底色本来就是 danger-surface**），错的是**文字也被写成深红 `#b21f1f`**：
  classic/green/blue/purple **1.48:1** → **10.02:1**，dark **3.96:1** → **10.03:1**。
  取值走 `theme.THEMES[当前主题]["banner_fg"]`（U-15 落地时已有的键），**不新增颜色键、不写字面量兜底**
  （写了会给裸色禁令记新账）。
- **时钟告警改用 `danger`（`61bbd4d`，B-1b）**：`#b21f1f` 压在**侧栏面板底**上，dark 主题只有 **2.28:1**。
  `theme.py` 新增 `_DANGER = {"light": "#7f1d1d", "dark": "#f2b8b5"}` 挂到 `danger` 键，注释写明它只用于
  压在面板/卡片底上的警示文字，**不要压品牌色横幅**（横幅有自己的 `banner_fg`）。dark **2.28 → 9.00**，
  其余四主题 6.3 → 9.3 以上。
- 验收判据是**落点**而不是总数：初始态 5 主题 `--check` 全 0；将军态差异 classic/green/blue/purple 各 860 px、
  dark 850 px **全部落在横幅**；新增 lowtime 夹具后差异 865 / 868 px **全部落在侧栏**，棋盘/横幅/标题栏 0。

## 网页 UI 令牌化（A 阶段：只搬值，零视觉变化）

- **先有基线（`0cf0d61`，A-0）**：`scripts/css_snapshot.py` 把 `app.css` 摊平成 `选择器|属性|值`，
  **`var()` 按 `:root`/暗色作用域展开成字面色**（不展开的话令牌化必然让快照变，验收就退化成文字比对）。
  基线 **845 行**。
- **口径修正两次**：① sha 改按**文件字节**（stdout 一致而文件被改写会漏），亮/暗两份分别比、并加
  「两份必须不同」防脚本退化成单表；同笔把 `.gitattributes` 里的 `benchmarks/*.txt` 标 `-text`
  并加 `test_snapshot_has_no_cr`（`350a94e`）；② CLI 改走 `sys.stdout.buffer.write` —— Windows 上
  `sys.stdout.write` 会把 LF 转 CRLF，曾造成「845 行全不同」的假警报（`447a0aa`）。
- **改名对齐规范（`a4141fe`）**：`--green → --brand`（4 处）、`--paper → --surface-2`（2 处）、
  `--panel → --surface`（2 处）；`var()` 展开值相同，两份基线字节未变。
- **收编 11 处裸值（`7403634`）**：只收「暗色作用域没覆盖同名变量」的令牌——`--surface-2` 4 处、
  新建 `--line-soft` 4 处、新建 `--line-strong` 2 处、新建 `--danger-surface` 1 处；裸 hex **151 → 146**。
  清单里的 `#211b17→--ink`、`#fffaf0→--surface`、`#315c48→--brand` 共 7 处**被暗色覆盖**，替换即改色，留到 B。
- **两条（后补第 4 条）硬口径写进审计文档（`a1ff70e` / `771e364`）**：① 只搬「值完全相同」的令牌，
  判据是 `var()` 展开后逐字节相同；② 暗色块覆盖过的令牌不得用于替换亮色字面量；
  ③ 一个可被替换的字面量，必须**在它生效的所有主题下**都与令牌解析结果相同——`THEMES` 的 6 个键在 5 个主题里
  取值各异，而 QSS 字面量全主题共用，所以这类替换在「像素 diff = 0」下一律不可做（桌面因此有 6 处 `A 阶段豁免：属 B`）。
- **裸色禁令 + 生成式 allowlist（`85d740d`，A-3）**：`tests/test_no_raw_colors.py` 扫 `web/css/app.css` +
  `desktop/app.py` + `desktop/ui/*.py`，三条豁免——`--name: #hex` 令牌定义、allowlist 登记项、**注释里的 hex**
  （单独计数、**不进 allowlist**，防止把颜色藏进注释绕过检查）。allowlist 由 `scripts/gen_color_allowlist.py`
  生成，测试断言「与生成结果一致」「两次生成逐字节一致」「实际条目数 ≤ allowlist 条数」。
  反向验证：临时插 `outline-color:#123456` → 立即 1 failed 且点名该值。
- **桌面像素基线（`ae080a8` / `ec65c3c` / `e0e1595` / `e506035`）**：5 主题 × 1260×850 × 初始局面逐像素比；
  `--diff-report` 把差异按 `标题栏/横幅 · 棋盘 · 侧栏 · 其它` 聚合（只给总数无法判断改对没有）；
  将军态单独一套 `<theme>_check.png` 夹具（该样式只在将军时渲染，拿初始局面比会得到 0 差异的假绿）。
  噪声底**曾被我调成 260，是错的**——206 px 不是抖动，是侧栏时钟随时间变化；改为
  `_freeze_clock()`（停 `QTimer` + `game.tick` 打空 + 钉死 `clocks_ms`）后 `--noise` **全 0**。
- **`--line` 改值项作废（`d5f7d64` / `5da4cdc`）**：`--line` 定义 2 处、`var(--line)` 引用 **0** 处，
  改它的值渲染一个像素都不会变；且目标值 `#d5bea0` 在面板/窗口/次级底上只有 **1.72 / 1.08 / 1.37**，属面底色。
  两处定义旁加注释标记，审计 §3.3 该行标作废。顺带记一条：`--board-line` 在 CSS 里也是 0 引用，
  但 `web/js/app.js` 用 `getPropertyValue('--board-line')` 读它——**0 引用 ≠ 未使用**。

## 边框令牌收编与改色（B 阶段第一批）

- **收编 20 处（`784081e`，零视觉变化）**：按「值 → 用途」分组，**只在 `border*` / `outline` / `box-shadow`
  声明内**替换——`#d9cab2→--divider-row`（6）、`#b5a184→--border-field`（5）、`#ddc9a9→--divider-section`（5）、
  `#d7c5a8→--border-panel-soft`（2）、`#c8ad84→--border-board-frame`（2）。
  这 5 个值还各有 1 处出现在**背景**属性里（共 5 处）**未替换**——把 `--divider-row` 用在背景上会把命名语义弄脏；
  所以是 20 处而不是 25 处。allowlist **119 条 / 176 处 → 114 条 / 156 处**（条目 −5、处数 −20，完全对应）。
- **改值（`277ec30` → 定稿 `a15d19a`）**：按「达标是下限，不是目标」落地，**20 处引用一行未动**：

  | 令牌 | 原值 | 新值 | 面板底 | 棋盘底 |
  |---|---|---|---|---|
  | `--divider-row` | `#d9cab2` | `#c2aa84` | 1.55 → **2.15** | 1.39 |
  | `--divider-section` | `#ddc9a9` | `#c09c62` | 1.55 → **2.47** | 1.60 |
  | `--border-panel-soft` | `#d7c5a8` | `#b5935e` | 1.62 → **2.77** | 1.79 |
  | `--border-field` | `#b5a184` | `#a38b66` | 2.40 → **3.13** | 2.02 |
  | `--border-board-frame` | `#c8ad84` | `#8a6b3e` | 2.07 → 4.75 | 1.34 → **3.07** |

- 只有**可交互控件**的边框（`--border-field`）按 WCAG 1.4.11 的 3:1 硬要求；**分隔线三档 2.15 / 2.47 / 2.77
  全部 < 3**，刻意不抢控件边框的视觉权重；`--border-board-frame` 的实际底是**棋盘色 `#e7c88d`**，按该底取 3.07。
  色阶单调（L = 64 / 57 / 54 / 52 / 39，不倒挂），色相固定 H = 36–37°、**只调 L 未动 S 与 H**，暖褐族不变。
- `--border-board-frame` 比 `--border-field` 更深**不是层级倒挂**：它包的是棋盘，棋盘本身是深色块，底越暗线要越深
  才拉得开 3:1。已在定义旁写明注释，避免后来人当成倒挂去「修」。
- 验证：快照**删 20 / 增 20（正好是那 20 处声明）**，无新增无删除；桌面 5 主题 `--check` 全 0；
  allowlist 数量不变（换的是值不是数量）。

## 桌面几何

- **图谱三栏不再挤压（`680af51`）**：左清单从 `setFixedWidth(188)` 改 `200–280`，中演示 stretch 3 → 1 + 盘 `minWidth 320`，
  右详情 `QScrollArea` 加 `minWidth 300`，最小尺寸从 `760×560` 收到 `max(900, hint.w) × max(640, hint.h)`。
- **侧栏按钮改单列（`cba73be`）**：两列需要 `182×2 + 间距 = 364`，而侧栏可用宽只有 ~296–388 ——
  实测内容宽 388、视口 289/221/195，**横溢 99 / 167 / 193 px**，第二列只露出 50%。改单列后三档横溢全 **0**。
  `182` 不降：那是为「未来语言不截断」留的结构性余量（英文实测只需 95 px）。
- **棋盘锁定正方形（`fab5bcc`）**：新增 `_SquareHost`，按 `min(w,h)` 居中摆放，`board_geometry.py` 的格子算法一行没动；
  1260×850 档 `903×737 → 737×737`。同笔把五个对话框最小尺寸按几何审计表上调。
- **守卫（`268766c` / `d39fb16`）**：侧栏不横溢、棋盘正方（`abs(w-h) ≤ 1`）、对话框最小尺寸与审计表一致；
  棋盘空带的判据改成**不变量**「棋盘边长 == min(容器宽, 容器高)」，比 72 px 这类拍出来的阈值稳
  （1260×850 档水平空带必为 76.5，旧阈值 72 作废）。

## 文档与版本号

- **合并与索引（`5742cb7`）**：`RUN_DESKTOP.md` + `RUN_WEB.md` + `DOCKER_DEPLOY.md` → `docs/release/RUN.md`（内容未改写）；
  `FEATURES.md` 并入 `ARCHITECTURE.md`；删前先 grep 引用并改链接，0 命中才删；`docs/README.md` 收录
  41 份文档分五组，history 组逐条标「历史快照，只读不改」。
- **修错值与版本单一来源（`07b8d22`）**：`desktop_complete` 11 类 / 50 子、`desktop_classic` 48 / 每方 24、
  `web` 10 类 / 44、AI 四档 → **六档**；`pyproject.toml` 删 `version` 改 `dynamic` + `attr = xionghan_chess.__version__`，
  并把其余版本面同步（否则既有 `test_release_version_sources_agree` 会红）；新增副本一致性守卫
  （`docs/` 与 `resources/docs/` 的 `PIECE_RULES.md` / `ABOUT.md` / `HELP.md` 逐字节比）。
- **三处硬编码 1.7.0（`0b6e38c`）**：关于对话框、`atlas.js` 的 `i18n.js?v=`、安卓壳 `welcome.html`；
  新增 `test_web_version_strings_match`（两种正则，且要求至少命中 4 处防正则失效）。红/绿验证各一次。

## 工程与版本线

- **版本号 1.7.5 → 1.8.0（`53aa536`）**，单一来源仍是 `xionghan_chess.__version__`，其余 7 个文件由测试反查：
  `web/index.html` 3 处缓存号、`web/js/app.js` 展示串、`web/js/atlas.js`、`welcome.html`、`package.json`、
  Android `DisplayVersion`（**`ApplicationVersion` 9 → 10**）、`deploy/docker-compose.yml` 镜像 tag。
  其中 csproj 与 docker-compose 两处是 `test_qa_regressions::test_release_version_sources_agree` 扫出来的，
  **不在人工清单里**——先跑测试让它报，不靠记忆逐个找。
- **桌面 EXE**：`release/匈漢象棋-1.8.0-桌面版.exe`，55,793,887 B，sha256 `9bd8124c1582f9c3…`；
  `scripts/probe_exe.py` 冒活通过（数据目录已创建 + 启动后仍存活）。EXE 不入库（`.gitignore` 有 `*.exe`）。
- 门禁：`pytest tests/ -q` 全量（含 `slow`）**875 passed / 1 skipped / 0 failed，315.41 s**；
  `-m "not slow"` 口径 **855 passed / 1 skipped / 20 deselected**；跨引擎对拍 **81/81**。

## 未纳入本版本（审计中未施工的条目）

按编号列出，避免把「没做」读成「已修」：`1-1`、`1-2`、`2-2`、`2-3`、`3-2`（未逐条核完 8 处锁内 `await`）、
`B-03`、`B-04`、`L-04`、`S6`、`S7`、`Y2`、`Y3`、`Y4`、`P2`、`P3`、`P4`。
UI 审计 29 条本版本只做了边框色（`U-04`）与将军横幅配色（`U-15`），字阶、间距、图标、状态矩阵、禁用态等未施工。
