# 新旧版本功能差异审计：缺失功能清单与补全方案

> 版本：v1.4.0 基线 | 日期：2026-08-13 | 范围：根目录旧版（`desktop/` Pygame + `web/` Flask-SocketIO） vs 新版 `xionghan-chess-next`（共享核心 + FastAPI/WebSocket + PySide6 桌面 + Web + Android）
>
> 方法：逐模块审阅旧版 `desktop/ui|controllers|core|ai|lan`、`web/js|server|sounds|images`，与新版 `src/xionghan_chess/*`、`web/index.html|js/app.js`、`android/Resources/assets/offline/*` 横向对照；已覆盖项以 `docs/DESKTOP_LEGACY_REFERENCE.md` 为基础复核。

---

## 1. 结论摘要

新版在**架构、联机协议、功能广度上全面超越旧版**（新增观战、提和协商、残局训练、棋谱库、账号云同步、让子、复盘分析、三端共享核心等）。真正的"缺失"集中在 **8 项**，按性质分三档：

| 级别 | 数量 | 性质 |
| --- | --- | --- |
| **A 完全缺失** | 3 项 | 旧版有完整实现，新版无对应能力 |
| **B 能力缩水** | 3 项 | 新版有替代实现，但丢失了旧版部分能力 |
| **C 表现待增强** | 2 项 | 新版功能已存在，视觉/交互表现弱于旧版 |

另有 4 项属于"新版有意为之的架构取舍/建议新增"，一并列出供决策。

---

## 2. 缺失功能清单（A 级：完全缺失）

### A-1 MCTS 强化学习训练与推理

- **旧版位置**：`desktop/ai/mcts/`（`mcts.py`、`mcts_pure.py`、`mcts_game.py`、`collect.py`、`init_training.py`、`load_pkl.py`、`mcts_config.py`）+ `desktop/ai/xionghan_chess_mcts_ai.py`
- **依赖**：Redis 样本存储、PyTorch/PaddlePaddle、旧棋盘编码与旧规则函数
- **新版现状**：仅迁移 Negamax/Alpha-Beta 搜索 AI（四档难度），无任何 MCTS/神经网络代码；`DESKTOP_LEGACY_REFERENCE.md` §5 明确"原 MCTS 模型未直接迁移"
- **影响**：AI 上限受限于启发式搜索，无自学习/离线强化训练能力
- **补全方案**（分期）：
  1. **前置（必须先做）**：在共享核心定义稳定训练编码——固定 `PieceType` 枚举值、`RuleOptions` 序列化 schema、局面张量布局（含 14 类棋子 + 复活/升变等动态状态）。写进 `docs/PIECE_RULES.md` 与 `core/protocol.py` 的版本化约定。
  2. **P1**：实现 `core/ai/mcts.py`——纯 MCTS + UCB1 推理，不依赖神经网络，作为"大师"档位；用 `core/rules.py` 的合法走子生成器驱动，复用现有 `Game` 状态。
  3. **P2**：训练流水线 `core/ai/train/`——自对弈采样（`collect.py` 重写）、样本落盘（去掉 Redis 硬依赖，改本地 JSON/parquet）、监督/策略梯度训练（框架可选，先用轻量 numpy，再评估 PyTorch 引入）。
  4. **验收**：与现有高级 AI 对弈 100 局，胜率 ≥55% 且单步耗时可控；新增 pytest 覆盖 MCTS 合法性与回退。

### A-2 旧 `.fen` 棋谱兼容导入

- **旧版位置**：`desktop/controllers/game_io_controller.py`（文件后缀 `.fen`，实际为含历史/阵亡子力/时间/局面的 JSON）
- **新版现状**：仅支持版本化 `.xhgame`（`core/storage.py` + `desktop/storage.py`），导入校验格式版本
- **影响**：老用户棋谱无法导入新版，历史资产失效
- **补全方案**：
  1. **P1**：写 `.fen` → 新版 `GameDocument` 迁移器 `core/legacy.py`——旧棋子类名（`HanKing`/`Xun`/`She` 等）映射到 `PieceType`，旧规则字段映射到 `RuleOptions`；缺省字段给默认值并记录 `source: "legacy-fen"` 与 `convertedAt`。
  2. 迁移器输出先经 `pytest` 快照对比（旧局面 → 新版 `Game` 走子结果一致）再放行。
  3. 在桌面 `文件 -> 导入棋局` 与 Web `loadGameButton` 中按扩展名分流（`.xhgame` 直读，`.fen`/`.json` 走迁移器）。
  4. **验收**：旧版保存的棋谱文件逐一导入成功，复盘步数与旧版一致。

### A-3 头像系统

- **旧版位置**：
  - 桌面 `desktop/ui/avatar.py`（头像绘制）
  - Web `web/js/controllers/avatar-manager.js`（默认头像绘制 + 自定义 URL + 随机头像 + 缓存）+ `web/images/avatars/`（红/黑玩家 4 张图）
- **新版现状**：桌面侧栏仅"文字阵营面板"；Web 有账号（`accountButton`/`accountDisplayName`）但无头像字段；`web/assets/` 无 `avatars/` 目录
- **影响**：联机对局缺少身份感，观战/聊天时辨识度低
- **补全方案**：
  1. **P1（轻量）**：账号模型加 `avatarUrl` 字段（`service/accounts.py` + 前端账号弹窗上传/粘贴 URL）；联机快照与聊天消息携带头像 URL，Web/桌面/安卓三端渲染。
  2. **P2**：内置头像库（复用旧版 4 张 + 新增若干），未登录用户按房间号/名字哈希取默认头像（`avatar-manager.js` 的 `getRandomAvatar(seed)` 思路）。
  3. 桌面侧栏与 Web 玩家区改为头像 + 名字组件，观战列表同享。
  4. **验收**：三端创建/加入房间后双方头像可见；聊天消息带发送者头像。

---

## 3. 缺失功能清单（B 级：能力缩水）

### B-1 挑衅/嘲讽系统（20 条 → 6 条快捷短语，且无自动触发）

- **旧版位置**：`desktop/controllers/taunts_manager.py` + `web/docs/taunts.json`（20 条挑衅语）+ `web/js/controllers/taunt-manager.js`
- **新版现状**：仅桌面/Web 聊天面板内置 6 条快捷短语（请多指教/好棋/承让/稍等一下/再来一局/挑衅），无 AI 主动挑衅、无胜负触发、无随机选择
- **影响**：旧版的趣味性（AI 胜利时嘲讽、人类劣势时挑衅）丢失
- **补全方案**：
  1. **P1**：把 `taunts.json` 20 条按场景归类（胜利/失败/将军/开局/随机）并入 i18n 语言包（`i18n.py` 与 `offline-locales.js`、`web/js/i18n.js` 三端同步），"挑衅"从聊天短语中独立出来。
  2. AI 模式下按事件触发：将军时低概率播报、AI 胜利播一条胜利嘲讽、玩家长考超时提醒；可配置开关（默认开，桌面 `settings`、Web `assistSettings`）。
  3. **验收**：三端 PVC 对局中可复现触发，语言切换后文案正确。

### B-2 联机重新开局双方确认流程

- **旧版位置**：`web/server/app.py` 的 `restart_request` / `restart_response` 双消息协商（`desktop/lan/network_game.py` 同样支持重开协商）
- **新版现状**：`core/protocol.py` 只有单向 `RESTART` 消息，一方发起即重开，无对方确认；`DESKTOP_LEGACY_REFERENCE.md` §9 已注明"后续可继续补充双方确认流程"
- **影响**：对局中一方可强行重开，体验粗糙
- **补全方案**：
  1. **P1**：协议层新增 `RESTART_REQUEST`/`RESTART_RESPONSE`（对齐既有 `DRAW_OFFER/DRAW_RESPONSE` 与 `UNDO_REQUEST/UNDO_RESPONSE` 模式）；`rooms.py` `handle()` 增加分支与 `pendingRestartOffer` 状态。
  2. 三端 UI：发起方弹"请求重新开局"，对方弹确认框；服务端广播合并后的新 `GameDocument`。
  3. 顺带补**房间级聊天开关**（房主可关闭聊天，`create` 时传 `chatEnabled`，`CHAT` 处理前置校验）。
  4. **验收**：pytest 覆盖重开协商的接受/拒绝/超时；三端手动联机验证。

### B-3 统计细分（时长 / 连胜 / 最快胜利 / 分色胜率）

- **旧版位置**：桌面 `desktop/controllers/statistics_manager.py`（总局数、胜负和、对局时长、吃子数量、总步数）；Web `web/js/controllers/statistics-manager.js`（`gamesPlayed`、`gamesWon`、`totalTimePlayed`、`fastestWin`、`winStreak`、分色 `winRate`）
- **新版现状**：桌面 `desktop/storage.py` + Web `app.js loadStatistics()` 仅记录 `games / redWins / blackWins / draws / moves`，展示总局数、胜负和、走子数、红方胜率
- **影响**：丢失总对局时长、最快胜利、连胜记录、分色胜率等维度
- **补全方案**：
  1. **P1**：`core` 或各端 `storage` 扩展统计 schema（向后兼容旧字段）：`totalTimeMs`、`fastestWinMs`、`winStreak{current,max}`、`perColor`；对局结束时由 `state.clocksMs` 累计时长（新版已有倒计时数据，直接可算）。
  2. 桌面 `show_statistics` 与 Web `showStatistics` 补展示卡片（总时长/最快胜利/连胜/红黑分色胜率）。
  3. **P2**：按模式维度拆分（AI/本地/联机/残局）与吃子分类统计（每类棋子吃子数，数据源 `state.captured` 已有）。
  4. **验收**：pytest 校验统计落盘与旧数据兼容；三端统计面板字段齐全。

---

## 4. 缺失功能清单（C 级：表现待增强）

### C-1 最近一步轨迹动画

- **旧版位置**：`desktop/ui/chess_board.py`（最近一步起止轨迹绘制，棋盘绘制能力清单第 3 节）
- **新版现状**：桌面 `BoardWidget.animate_move()` 只有落子波纹；Web `drawAnimation()` 同（360ms 波纹）；安卓离线版无轨迹
- **补全方案**：统一实现"起止点轨迹"——落子后从源格到目标格画高亮连线/箭头（1.2s 淡出），复用现有动画帧循环（桌面 `_advance_animation`、Web `animate`）；三端视觉一致，可随 `animation` 设置开关。
- **验收**：走子后轨迹可见，复盘跳步时同步更新。

### C-2 将军/将死脉冲提示

- **旧版位置**：`desktop/controllers/check_checkmate_tip_manager.py`（将军脉冲文字动画）+ Web `check-alert` 元素
- **新版现状**：仅被将军一方的王有红色高亮环（`drawHighlights`），无脉冲文字/音效强化
- **补全方案**：将军时将"将军"（或 en "Check"）以脉冲缩放文字叠加在棋盘中央/王位上方 1.5s，配合现有 `check` 音效；将死沿用结果弹窗。三端同实现，文案走 i18n。
- **验收**：将军局面三端均有文字脉冲 + 音效，无重复播报（沿用双击音修复的守卫逻辑）。

---

## 5. 架构取舍与建议新增（非缺失，供决策）

| 项 | 旧版 | 新版 | 结论 |
| --- | --- | --- | --- |
| 房间号位数 | Web README 称 8 位 | 6 位大写字母+数字（`rooms.py:_room_id`） | 有意设计（6 位更短、防误读），非缺失；如需 8 位仅改一行 |
| 本地 PVP | 桌面 PVP 模式 | 桌面 `local_full` + Web/安卓 `local` 模式 | 已覆盖 |
| 暗黑模式 | Web `btn-dark-mode` 持久化 | `systemTheme`（light/dark/auto）+ 页面/棋盘背景自定义 | 已增强 |
| 倒计时 | Web 倒计时 | `initialMinutes` + `countdownSeconds` + 双色时钟 | 已增强 |
| 观战 / 提和 / 账号云同步 / 残局 / 让子 / 复盘分析 | 旧版无 | 新版全有 | 新版新增，非缺失 |
| 性能基准 | `desktop/tests/performance_benchmark.py` | 无对应基准 | 建议新增：改测共享核心与 AI（对搜索 AI 迭代有价值） |
| 规则阅读/关于/主题/音效管理 | 桌面完整 | 三端均有等价入口 | 已覆盖 |

---

## 6. 已覆盖功能对照（确认无缺失）

桌面：PVP/PVC/网络联机（创建/加入/观战）、四档 AI、阵营选择、四种规则档案（web/传统/经典/完整）、14 类棋子登场开关、兵卒复活/升变、悔棋/提和/认输/复活、复盘（含分析）、棋谱导入导出（.xhgame）、棋谱库、残局训练、全屏/面板开关/翻转、FC/QQ 背景音乐 + 独立音量、统计、账号云同步、规则阅读、关于。

Web：本地/联机/AI/观战、聊天（含快捷短语）、悔棋/提和/认输协商闭环、让子、残局训练、复盘 + 棋谱库 + 云同步、IndexedDB 自定义背景、i18n、主题/字体/棋子样式/棋盘配色、倒计时、落子波纹动画、将军高亮、吃子提示。

安卓离线：单页引擎 + i18n（zh/en）+ 残局 + 翻转 + 棋谱导入 + 音效（10 个与旧版完全一致）+ 自动保存。

音效清单逐一对齐：`button / check / choose / drop / eat / fc_background / fc_defeat / fc_victory / qq_background / warn`，旧版 10 个 = 新版 10 个，无缺失。

---

## 7. 跟进方案（分期路线图）

> 依赖关系：A-1 需先完成稳定编码定义；B/C 各项相互独立可并行；i18n 语言包（`i18n.py`/`web/js/i18n.js`/`offline-locales.js`）是三端 B-1/C-2 文案的公共前置。

### P0（已规划，与本清单并行）
- 安卓双页拆分（welcome/game.html）与残局字符串 i18n 落地（`'解题成功'`/`'再想一想：'` 等硬编码中文）
- `offline.js` 编码修复补交 git；构建产物（bin/obj ×19 项）从 git 移除并补 `.gitignore`
- Web/Desktop i18n 语言切换全面铺开

### P1（本清单高优，建议 2 周内）
1. B-2 联机重开协商 + 房间级聊天开关（协议层 + 三端 UI + pytest）
2. A-2 `.fen` 兼容迁移器（核心映射 + 桌面/Web 入口分流）
3. B-3 统计扩展（时长/连胜/最快胜利/分色胜率）
4. C-1 + C-2 轨迹动画与将军脉冲（三端一致 + i18n 文案）
5. B-1 挑衅系统 20 条入语言包 + AI 触发
6. A-3 头像（P1 轻量版：账号头像 URL + 三端渲染）

### P2（后续）
7. A-1 MCTS：稳定编码定义 → 纯 MCTS 推理档 → 自对弈训练流水线
8. 性能基准测试（共享核心 + AI）
9. 统计模式维度与吃子分类

### 验收门槛
- 每项合并 pytest 增量用例；三端（桌面/Web/安卓）手动冒烟；
- 任何规则相关改动先更新 `RuleOptions`、`PIECE_RULES.md` 与规则测试，再改客户端表现（沿用 `DESKTOP_LEGACY_REFERENCE.md` §11 约定）；
- 新增文案全部走 i18n 语言包，杜绝硬编码中文字符串。

---

## 8. 与既有文档衔接

- 本清单为 `DESKTOP_LEGACY_REFERENCE.md` §10/§11"待增强项"的展开细化（新增统计字段、挑衅明细、头像、重开协商的具体方案）。
- 交付验收基线沿用 `DELIVERY_1.4.0.md`；QA 待规则确认项（C-01/C-03/C-04/C-11/C-12）不阻塞本清单 P1 各项。
- 三端一致性校验标准见 `AUDIT_v1.3.0_analysis.md`；i18n 分层方案见 `i18n-language-switch.md`。
